"""Turns a ProcessSpec into a deck layout + flat command list + budget."""
import math
from dataclasses import dataclass, field

from . import catalog
from .catalog import ROW_NAMES
from .deck import place

TIP_FILL = 0.95          # usable fraction of nominal tip volume
MIN_PRECISION = 0.05     # prefer tips where volume >= 5 % of capacity

DEFAULT_TIMING = dict(   # seconds; calibrate against the real instrument
    pick_up_s=3.0, drop_s=2.0, move_s=1.5, base_s=1.0, flow_ul_s=100.0, operator_s=180.0,
)


@dataclass
class Group:
    name: str
    lw: catalog.Labware
    role: str                       # per_sample | reagent | target
    instances: list = field(default_factory=list)
    consumed_ul: float = 0.0        # per well, per-sample sources
    vol_ul: float = 0.0             # running per-well volume, targets
    wells_used: int = 0             # reagents
    fill_per_well: list = field(default_factory=list)
    spec_fill: float = None
    pin: str = None
    count: int = 0


@dataclass
class Plan:
    spec: object
    channels: int
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    commands: list = field(default_factory=list)
    instances: dict = field(default_factory=dict)   # id -> dict(labware, role, name, slots)
    deck: dict = field(default_factory=dict)        # slot -> [instance ids]
    initial_volumes: dict = field(default_factory=dict)
    reagents: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

    @property
    def ok(self):
        return not self.errors

    @property
    def meets_throughput(self):
        return self.ok and self.summary.get("max_runs_per_day", 0) >= self.spec.runs_per_day


def well_name(rows, idx):
    col, row = divmod(idx, rows)
    return f"{ROW_NAMES[row]}{col + 1}"


def make_units(n, rows, npos, c):
    """Group sample indices into head movements of up to c channels."""
    units, last = [], None
    for i in range(n):
        p = i % npos
        key = (i // npos,) if c == 96 else (i // npos, p // rows, (p % rows) // c)
        if key != last:
            units.append([])
            last = key
        units[-1].append(i)
    return units


class Builder:
    def __init__(self, spec, channels):
        self.spec, self.c = spec, channels
        self.plan = Plan(spec, channels)
        self.t = {**DEFAULT_TIMING, **spec.timing}
        self.groups = {}
        self.cmds = []
        self.n = spec.samples_per_run
        self.tip_types = sorted(spec.tip_types)

    # ---------------------------------------------------------------- helpers
    def err(self, m):
        if m not in self.plan.errors:
            self.plan.errors.append(m)

    def warn(self, m):
        if m not in self.plan.warnings:
            self.plan.warnings.append(m)

    def emit(self, step, cmd, **kw):
        self.cmds.append({"step": step, "cmd": cmd, **kw})

    # ----------------------------------------------------------------- groups
    def make_groups(self):
        for s in self.spec.sources:
            lw = catalog.get(s.labware)
            g = Group(s.name, lw, s.role, spec_fill=s.fill_ul, pin=s.slot)
            if s.role == "per_sample":
                g.count = s.count_per_run or math.ceil(self.n / lw.positions)
                if g.count * lw.positions < self.n:
                    self.err(f"{s.name}: {g.count} x {lw.key} holds {g.count * lw.positions} < {self.n} samples")
                g.instances = [f"{s.name}#{i}" for i in range(g.count)]
            self.groups[s.name] = g
        for t in self.spec.targets:
            lw = catalog.get(t.labware)
            g = Group(t.name, lw, "target", pin=t.slot)
            g.count = t.count_per_run or math.ceil(self.n / lw.positions)
            if g.count * lw.positions < self.n:
                self.err(f"{t.name}: {g.count} x {lw.key} holds {g.count * lw.positions} < {self.n} samples")
            g.instances = [f"{t.name}#{i}" for i in range(g.count)]
            self.groups[t.name] = g

    def indexed_wells(self, g, unit):
        """-> (instance id, [wells]) for sample indices in unit."""
        inst = g.instances[unit[0] // g.lw.positions]
        return inst, [well_name(g.lw.rows, i % g.lw.positions) for i in unit]

    def check_multichannel(self, g, step):
        c = self.c
        if c == 1:
            return True
        if not g.lw.multichannel:
            self.err(f"{step.name}: {g.name} ({g.lw.key}) is single-channel only, run uses {c} channels")
            return False
        if g.role != "reagent" and (g.lw.rows != 8 or g.lw.positions != 96):
            self.err(f"{step.name}: {g.name} ({g.lw.key}) not usable with {c} channels")
            return False
        if g.role == "reagent":
            if g.lw.kind != "trough":
                self.err(f"{step.name}: reagent {g.name} must sit in a trough for {c} channels")
                return False
            if c == 96 and g.lw.positions != 1:
                self.err(f"{step.name}: 96-head needs a 1-well reservoir for {g.name}")
                return False
        return True

    # ------------------------------------------------------------------ tips
    def choose_tip(self, v, n_units, reuse, mix_vol=0.0):
        best = None
        for cap in self.tip_types:
            usable = cap * TIP_FILL
            if mix_vol > usable:
                continue
            ex = self.spec.excess_ul
            if reuse and v + ex <= usable:
                k = int((usable - ex) // v)
                cost, pieces = math.ceil(n_units / k), 1
            else:
                pieces = max(1, math.ceil(v / usable - 1e-9))
                cost = n_units * pieces
            key = (v / pieces < MIN_PRECISION * cap, cost, cap)
            if best is None or key < best[0]:
                best = (key, cap, pieces)
        if best is None:
            cap = self.tip_types[-1]
            self.warn(f"mix volume {mix_vol:g} uL exceeds largest tip; clipped")
            return cap, max(1, math.ceil(v / (cap * TIP_FILL))), cap * TIP_FILL
        return best[1], best[2], None

    def pick(self, step, cap, nch):
        self.emit(step, "pick_up_tip", tip_type=cap, n_channels=nch, labware=None, wells=None)

    def drop(self, step):
        self.emit(step, "drop_tip", to="waste")

    def mix_cmd(self, step, g, unit, cycles, vol):
        inst, wells = self.indexed_wells(g, unit)
        self.emit(step, "mix", labware=inst, wells=wells, n_channels=len(wells),
                  volume_ul=round(vol, 2), cycles=cycles)

    def mix_volume(self, st, g):
        return st.mix_volume_ul if st.mix_volume_ul else max(1.0, round(0.5 * g.vol_ul, 1))

    # ----------------------------------------------------------------- steps
    def run_steps(self):
        for i, st in enumerate(self.spec.steps):
            self.emit(i, "comment", message=f"STEP {i}: {st.name}")
            if st.type == "manual":
                self.emit(i, "manual", message=st.message or st.name, duration_s=st.duration_s)
            elif st.type == "mix":
                self.step_mix(i, st)
            elif st.mode == "one_to_one":
                self.step_one_to_one(i, st)
            else:
                self.step_distribute(i, st)

    def add_volume(self, dst, v, st):
        dst.vol_ul += v
        if dst.vol_ul > dst.lw.max_ul + 1e-9:
            self.err(f"{st.name}: {dst.name} overfilled ({dst.vol_ul:g} > {dst.lw.max_ul:g} uL)")

    def step_mix(self, i, st):
        g = self.groups[st.target]
        if not self.check_multichannel(g, st):
            return
        vol = self.mix_volume(st, g)
        cap, _, clip = self.choose_tip(vol, 1, False, mix_vol=vol)
        vol = min(vol, clip) if clip else vol
        for u in make_units(self.n, g.lw.rows, g.lw.positions, self.c):
            self.pick(i, cap, len(u))
            self.mix_cmd(i, g, u, st.mix_cycles or 3, vol)
            self.drop(i)

    def step_one_to_one(self, i, st):
        src, dst = self.groups[st.source], self.groups[st.target]
        if src.role == "reagent":
            self.err(f"{st.name}: one_to_one needs a per-sample source, '{src.name}' is a reagent")
            return
        if not (self.check_multichannel(src, st) and self.check_multichannel(dst, st)):
            return
        if st.tip == "reuse":
            self.err(f"{st.name}: tip reuse in one_to_one transfer would cross-contaminate samples")
            return
        v = st.volume_ul
        if src.role == "target":
            src.vol_ul -= v
            if src.vol_ul < -1e-9:
                self.err(f"{st.name}: {src.name} has only {src.vol_ul + v:g} uL per well, step takes {v:g}")
        else:
            src.consumed_ul += v
        self.add_volume(dst, v, st)
        mvol = self.mix_volume(st, dst) if st.mix_cycles else 0.0
        cap, pieces, clip = self.choose_tip(v, 1, False, mvol)
        mvol = min(mvol, clip) if clip else mvol
        for u in make_units(self.n, dst.lw.rows, dst.lw.positions, self.c):
            self.pick(i, cap, len(u))
            for _ in range(pieces):
                si, sw = self.indexed_wells(src, u)
                di, dw = self.indexed_wells(dst, u)
                self.emit(i, "aspirate", labware=si, wells=sw, n_channels=len(sw), volume_ul=round(v / pieces, 3))
                self.emit(i, "dispense", labware=di, wells=dw, n_channels=len(dw), volume_ul=round(v / pieces, 3), touch=True)
            if st.mix_cycles:
                self.mix_cmd(i, dst, u, st.mix_cycles, mvol)
            self.drop(i)

    def step_distribute(self, i, st):
        src, dst = self.groups[st.source], self.groups[st.target]
        if src.role != "reagent":
            self.err(f"{st.name}: distribute needs a reagent source, '{src.name}' is {src.role}")
            return
        if not (self.check_multichannel(src, st) and self.check_multichannel(dst, st)):
            return
        if st.tip == "reuse" and st.mix_cycles:
            self.err(f"{st.name}: cannot mix with reused tips")
            return
        v = st.volume_ul
        self.add_volume(dst, v, st)
        units = make_units(self.n, dst.lw.rows, dst.lw.positions, self.c)
        mvol = self.mix_volume(st, dst) if st.mix_cycles else 0.0
        reuse = st.tip == "reuse"
        cap, pieces, clip = self.choose_tip(v, len(units), reuse, mvol)
        mvol = min(mvol, clip) if clip else mvol
        usable, ex = cap * TIP_FILL, self.spec.excess_ul

        def asp(vol, nch):
            self.emit(i, "aspirate", labware=None, wells=None, n_channels=nch,
                      volume_ul=round(vol, 3), _reagent=src.name)

        if reuse and pieces == 1:
            k = int((usable - ex) // v)
            self.pick(i, cap, self.c)
            for s in range(0, len(units), k):
                chunk = units[s:s + k]
                asp(len(chunk) * v + ex, max(len(u) for u in chunk))
                for j, u in enumerate(chunk):
                    di, dw = self.indexed_wells(dst, u)
                    self.emit(i, "dispense", labware=di, wells=dw, n_channels=len(dw),
                              volume_ul=round(v, 3), touch=False, blow_out=(j == len(chunk) - 1))
            self.drop(i)
            return
        # one tip set per head movement, or one set for the whole step when reused
        if reuse:
            self.pick(i, cap, self.c)
        for u in units:
            if not reuse:
                self.pick(i, cap, len(u))
            for _ in range(pieces):
                asp(v / pieces, len(u))
                di, dw = self.indexed_wells(dst, u)
                self.emit(i, "dispense", labware=di, wells=dw, n_channels=len(dw),
                          volume_ul=round(v / pieces, 3), touch=not reuse)
            if st.mix_cycles:
                self.mix_cmd(i, dst, u, st.mix_cycles, mvol)
            if not reuse:
                self.drop(i)
        if reuse:
            self.drop(i)

    # -------------------------------------------------------------- reagents
    def well_capacity(self, g, lw=None):
        lw = lw or g.lw
        cap = lw.max_ul - lw.dead_ul
        return min(cap, g.spec_fill) if g.spec_fill else cap

    def simulate_wells(self, g, asps, record=False, lw=None):
        """Greedy depletion of reagent wells; returns consumption per well."""
        usable = self.well_capacity(g, lw)
        j, rem, cons = 0, usable, [0.0]
        for cmd in asps:
            tot = cmd["volume_ul"] * cmd["n_channels"]
            if tot > usable + 1e-9:
                if record:
                    self.err(f"{g.name}: one aspiration needs {tot:g} uL > well capacity {usable:g} uL")
                continue
            if tot > rem + 1e-9:
                j, rem = j + 1, usable
                cons.append(0.0)
            rem -= tot
            cons[j] += tot
            if record:
                cmd["_rel"] = j
        return cons

    def pick_reagent_labware(self, g, asps, small_slot_free):
        """Smallest footprint that holds the reagent: narrow trough > shared 12-well > 1-well."""
        for key in ("small_trough_1well", "reservoir_12well_sbs", "reservoir_1well_sbs"):
            lw = catalog.get(key)
            if key == "small_trough_1well" and not small_slot_free:
                continue
            n = len(self.simulate_wells(g, asps, lw=lw))
            if n <= (1 if lw.positions == 1 else lw.positions):
                return lw
        return catalog.get("reservoir_1well_sbs")

    def assign_reagents(self):
        pools = {}
        for cmd in self.cmds:
            if cmd["cmd"] == "aspirate" and "_reagent" in cmd:
                pools.setdefault(cmd["_reagent"], []).append(cmd)
        for g in self.groups.values():
            if g.role == "reagent" and g.name not in pools:
                self.warn(f"reagent {g.name} is never used")
        order = []
        small_used = sum(len(g.instances) for g in self.groups.values() if g.lw.footprint == "small" and g.role != "reagent")
        small_used += sum(1 for g in self.groups.values() if g.role == "reagent" and g.lw.footprint == "small" and g.lw.key != "reagent_auto")
        for name, asps in pools.items():
            g = self.groups[name]
            if g.lw.key == "reagent_auto":
                g.lw = self.pick_reagent_labware(g, asps, small_used < len(self.spec.deck.small))
                small_used += g.lw.footprint == "small"
            cons = self.simulate_wells(g, asps, record=True)
            g.wells_used = len(cons)
            g.fill_per_well = [round(x + g.lw.dead_ul, 1) for x in cons]
            order.append(g)
        # pack reagent wells into shared labware, per labware type
        streams = {}
        for g in sorted(order, key=lambda g: -g.wells_used):
            key = g.lw.key
            s = streams.setdefault(key, {"n": 0, "free": []})
            g.well_map = []
            for _ in range(g.wells_used):
                if not s["free"]:
                    iid = f"reagents_{key}#{s['n']}"
                    s["n"] += 1
                    self.plan.instances[iid] = dict(labware=key, role="reagent", name=iid, slots=[])
                    s["free"] = [(iid, w) for w in g.lw.wells()]
                g.well_map.append(s["free"].pop(0))
        for g in order:
            self.plan.reagents[g.name] = dict(
                labware=g.lw.key,
                wells=[dict(instance=iid, well=w, fill_ul=f) for (iid, w), f in zip(g.well_map, g.fill_per_well)],
                total_ul=round(sum(g.fill_per_well) - g.lw.dead_ul * g.wells_used, 1))
            for (iid, w), f in zip(g.well_map, g.fill_per_well):
                self.plan.initial_volumes.setdefault(iid, {})[w] = f

    def finalise_reagent_cmds(self):
        for cmd in self.cmds:
            if "_reagent" in cmd:
                g = self.groups[cmd.pop("_reagent")]
                rel = cmd.pop("_rel", 0)
                iid, w = g.well_map[rel]
                cmd["labware"], cmd["wells"] = iid, [w]

    # ------------------------------------------------------------- instances
    def register_sample_instances(self):
        for g in self.groups.values():
            if g.role == "reagent":
                continue
            for k, iid in enumerate(g.instances):
                self.plan.instances[iid] = dict(labware=g.lw.key, role=g.role, name=g.name, slots=[], pin=g.pin if k == 0 else None)
            if g.role == "per_sample":
                need = g.consumed_ul
                if g.spec_fill and g.spec_fill + 1e-9 < need:
                    self.err(f"{g.name}: fill_ul {g.spec_fill:g} < consumption {need:g} uL per well")
                fill = g.spec_fill or round(need + g.lw.dead_ul, 1)
                if fill > g.lw.max_ul + 1e-9:
                    self.err(f"{g.name}: needs {fill:g} uL per well but {g.lw.key} holds {g.lw.max_ul:g}")
                if need > 0:
                    for k, iid in enumerate(g.instances):
                        cnt = min(self.n - k * g.lw.positions, g.lw.positions)
                        self.plan.initial_volumes[iid] = {well_name(g.lw.rows, j): fill for j in range(cnt)}
            else:   # target: starts empty
                for iid in g.instances:
                    self.plan.initial_volumes[iid] = {}

    # ------------------------------------------------------------------ deck
    def place_deck(self):
        p = self.plan
        items = [(iid, catalog.get(v["labware"]).footprint, v.get("pin")) for iid, v in p.instances.items()]
        res = place(items, self.spec.deck)
        if res[0] is None:
            self.err(res[1])
            return None
        assign, free_main, _ = res
        for iid, slots in assign.items():
            p.instances[iid]["slots"] = slots
        return free_main

    def tip_units_per_rack(self):
        return 1 if self.c == 96 else (8 // self.c) * 12

    def assign_tips(self, free_main):
        p, upr = self.plan, self.tip_units_per_rack()
        need = {}
        for cmd in self.cmds:
            if cmd["cmd"] == "pick_up_tip":
                need[cmd["tip_type"]] = need.get(cmd["tip_type"], 0) + 1
        racks = {cap: math.ceil(u / upr) for cap, u in need.items()}
        if not racks:
            return racks, {}, 0
        if len(free_main) < len(racks):
            self.err(f"{len(racks)} tip types need {len(racks)} main slots, only {len(free_main)} free")
            return racks, {}, 0
        on_deck = {cap: 1 for cap in racks}
        spare = len(free_main) - len(racks)
        while spare > 0:
            cap = max((c for c in racks if on_deck[c] < racks[c]), key=lambda c: racks[c] - on_deck[c], default=None)
            if cap is None:
                break
            on_deck[cap] += 1
            spare -= 1
        slots, it = {}, iter(free_main)
        for cap in sorted(racks):
            slots[cap] = [next(it) for _ in range(on_deck[cap])]
        for cap in sorted(racks):
            for k in range(racks[cap]):
                iid = f"tips_{cap}#{k}"
                p.instances[iid] = dict(labware=f"tips_{cap}", role="tips", name=iid,
                                        slots=[slots[cap][k % on_deck[cap]]], reload=k >= on_deck[cap])
        out, counter, seen = [], {cap: 0 for cap in racks}, set()
        for cmd in self.cmds:
            if cmd["cmd"] == "pick_up_tip":
                cap = cmd["tip_type"]
                idx = counter[cap]
                counter[cap] += 1
                k, u = divmod(idx, upr)
                iid = f"tips_{cap}#{k}"
                if p.instances[iid]["reload"] and iid not in seen:
                    seen.add(iid)
                    sl = p.instances[iid]["slots"][0]
                    out.append(dict(step=cmd["step"], cmd="pause", reason="tip_reload", duration_s=self.t["operator_s"],
                                    message=f"Replace tip rack in slot {sl} with a fresh {cap} uL rack ({iid})"))
                n = cmd["n_channels"]
                if self.c == 96:
                    wells = catalog.get(f"tips_{cap}").wells()[:n]
                else:
                    per_col = 8 // self.c
                    col, chunk = divmod(u, per_col)
                    wells = [f"{ROW_NAMES[chunk * self.c + r]}{col + 1}" for r in range(n)]
                cmd = {**cmd, "labware": iid, "wells": wells}
            out.append(cmd)
        self.cmds = out
        reloads = sum(1 for v in p.instances.values() if v.get("reload"))
        return racks, need, reloads

    # ---------------------------------------------------------------- timing
    def estimate_time(self):
        t, tot = self.t, 0.0
        for c in self.cmds:
            k = c["cmd"]
            if k == "pick_up_tip":
                tot += t["pick_up_s"] + t["move_s"]
            elif k == "drop_tip":
                tot += t["drop_s"]
            elif k in ("aspirate", "dispense"):
                tot += t["move_s"] + t["base_s"] + c["volume_ul"] / t["flow_ul_s"]
            elif k == "mix":
                tot += t["move_s"] + c["cycles"] * (2 * t["base_s"] + 2 * c["volume_ul"] / t["flow_ul_s"])
            elif k in ("manual", "pause"):
                tot += c.get("duration_s", 0.0)
        return tot

    # ------------------------------------------------------------------ main
    def build(self):
        self.make_groups()
        if self.plan.errors:
            return self.plan
        self.run_steps()
        self.assign_reagents()
        self.finalise_reagent_cmds()
        self.register_sample_instances()
        free_main = self.place_deck() if not self.plan.errors else None
        racks, tips, reloads = ({}, {}, 0)
        if free_main is not None:
            racks, tips, reloads = self.assign_tips(free_main)
        p = self.plan
        p.commands = self.cmds
        for iid, v in p.instances.items():
            for s in v["slots"]:
                if not v.get("reload"):
                    p.deck.setdefault(s, []).append(iid)
        run_s = self.estimate_time()
        low_prec, cap = 0, 0
        for c in self.cmds:
            if c["cmd"] == "pick_up_tip":
                cap = c["tip_type"]
            elif c["cmd"] in ("aspirate", "dispense") and c["volume_ul"] < MIN_PRECISION * cap:
                low_prec += 1
        spec = self.spec
        day_s = spec.hours_per_day * 3600
        cycle = run_s + spec.changeover_s
        max_runs = int(day_s // cycle) if cycle else 0
        per_run = {}
        for v in p.instances.values():
            per_run[v["labware"]] = per_run.get(v["labware"], 0) + 1
        p.summary = dict(
            channels=self.c, tip_types=self.tip_types, low_precision_ops=low_prec, samples_per_run=self.n, runs_per_day=spec.runs_per_day,
            run_time_s=round(run_s), run_time_min=round(run_s / 60, 1), changeover_s=spec.changeover_s,
            max_runs_per_day=max_runs, utilization=round(spec.runs_per_day * cycle / day_s, 3),
            tips_per_run={cap: u * self.c for cap, u in tips.items()},
            tip_racks_per_run=racks, tip_reloads_per_run=reloads,
            operator_interventions_per_run=sum(1 for c in self.cmds if c["cmd"] in ("manual", "pause")),
            labware_per_run=per_run,
            labware_per_day={k: v * spec.runs_per_day for k, v in per_run.items()},
            reagent_ul_per_run={k: v["total_ul"] for k, v in p.reagents.items()},
            reagent_ul_per_day={k: round(v["total_ul"] * spec.runs_per_day, 1) for k, v in p.reagents.items()},
        )
        if spec.runs_per_day > max_runs:
            self.warn(f"{spec.runs_per_day} runs/day need {spec.runs_per_day * cycle / 3600:.1f} h, "
                      f"only {spec.hours_per_day:g} h available (max {max_runs} runs)")
        if reloads:
            self.warn(f"{reloads} tip-rack reload(s) per run (operator pause)")
        return p


def build(spec, channels=None) -> Plan:
    return Builder(spec, channels or spec.channels[0]).build()


def optimize(spec):
    """Try every allowed channel count x (all tip types | single tip type); best first."""
    from dataclasses import replace
    plans = []
    variants = [list(spec.tip_types)] + [[t] for t in spec.tip_types] if len(spec.tip_types) > 1 else [list(spec.tip_types)]
    for c in spec.channels:
        for tips in variants:
            plans.append(build(replace(spec, tip_types=tips), c))

    def key(p):
        s = p.summary
        return (not p.ok, not p.meets_throughput, s.get("tip_reloads_per_run", 9),
                s.get("low_precision_ops", 0), s.get("run_time_s", 1e9))
    return sorted(plans, key=key)
