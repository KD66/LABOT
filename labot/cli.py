import argparse
import json
import sys

from .emit import emit_python
from .planner import optimize
from .spec import ProcessSpec


def describe(plan):
    s = plan.summary
    lines = [f"== {plan.spec.name}: {plan.channels} channel(s) =="]
    lines += [f"ERROR   {e}" for e in plan.errors] + [f"warning {w}" for w in plan.warnings]
    if not s:
        return "\n".join(lines)
    lines += [
        f"run time {s['run_time_min']} min (+{s['changeover_s'] / 60:g} min changeover); "
        f"max {s['max_runs_per_day']} runs/day, requested {s['runs_per_day']} (utilisation {s['utilization']:.0%})",
        f"tips/run {s['tips_per_run']}  racks/run {s['tip_racks_per_run']}  reloads {s['tip_reloads_per_run']}",
        f"labware/day {s['labware_per_day']}",
        f"reagent uL/day {s['reagent_ul_per_day']}",
        "deck:"] + [f"  {slot}: {', '.join(v)}" for slot, v in sorted(plan.deck.items())]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="labot", description="Plan a liquid-handling run and emit a Python run file")
    ap.add_argument("spec", help="process spec (YAML)")
    ap.add_argument("-o", "--output", help="write run module here (best feasible plan)")
    ap.add_argument("--channels", type=int, help="force one channel count")
    ap.add_argument("--json", action="store_true", help="print summary of best plan as JSON")
    a = ap.parse_args(argv)
    spec = ProcessSpec.from_yaml(a.spec)
    if a.channels:
        spec.channels = [a.channels]
    plans = optimize(spec)
    best = plans[0]
    print(describe(best), end="\n\n")
    print("alternatives (channels / tips / ok / reloads / run min):")
    for p in plans[1:]:
        s = p.summary
        print(f"  {p.channels:>2} ch  tips {s.get('tip_types')}  {'ok' if p.ok else 'INFEASIBLE'}  "
              f"reloads {s.get('tip_reloads_per_run', '-')}  {s.get('run_time_min', '-')} min")
    print()
    if a.json:
        print(json.dumps(best.summary, indent=2))
    if not best.ok:
        print("no feasible plan", file=sys.stderr)
        return 2
    if a.output:
        with open(a.output, "w") as f:
            f.write(emit_python(best))
        print(f"wrote {a.output} ({best.channels} channels)")
    return 0 if best.meets_throughput else 3


if __name__ == "__main__":
    sys.exit(main())
