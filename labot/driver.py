"""DryRunDriver: replays a command list, tracks well volumes and tip state."""


class DryRunError(RuntimeError):
    pass


class DryRunDriver:
    def __init__(self, module):
        self.m = module
        self.vol = {i: dict(w) for i, w in module.INITIAL_VOLUMES_UL.items()}
        self.tip = None
        self.picked = set()
        self.log = []
        self.dispensed_in_air = 0

    def _lw(self, inst):
        return self.m.LABWARE[self.m.INSTANCES[inst]["labware"]]

    def comment(self, step, message):
        self.log.append(message)

    def pick_up_tip(self, step, tip_type, n_channels, labware, wells):
        if self.tip is not None:
            raise DryRunError("pick_up_tip with tip already attached")
        key = [(labware, w) for w in wells]
        if self.picked & set(key):
            raise DryRunError(f"tips {key} used twice")
        self.picked |= set(key)
        self.tip = dict(cap=tip_type, held=0.0, n=n_channels)

    def drop_tip(self, step, to):
        self.tip = None

    def aspirate(self, step, labware, wells, n_channels, volume_ul):
        if not self.tip:
            raise DryRunError("aspirate without tip")
        per_well = n_channels / len(wells)
        for w in wells:
            v = self.vol[labware].get(w, 0.0) - volume_ul * per_well
            if v < self._lw(labware)["dead_ul"] - 1e-6:
                raise DryRunError(f"{labware}/{w} below dead volume ({v:.1f} uL)")
            self.vol[labware][w] = v
        self.tip["held"] += volume_ul
        if self.tip["held"] > self.tip["cap"] + 1e-6:
            raise DryRunError(f"tip overfilled: {self.tip['held']:.1f} > {self.tip['cap']}")

    def dispense(self, step, labware, wells, n_channels, volume_ul, touch=True, blow_out=False):
        if not self.tip or self.tip["held"] + 1e-6 < volume_ul:
            raise DryRunError("dispense more than held")
        self.tip["held"] = 0.0 if blow_out else self.tip["held"] - volume_ul
        lw = self._lw(labware)
        for w in wells:
            v = self.vol[labware].get(w, 0.0) + volume_ul
            if v > lw["max_ul"] + 1e-6:
                raise DryRunError(f"{labware}/{w} overfilled ({v:.1f} uL)")
            self.vol[labware][w] = v

    def mix(self, step, labware, wells, n_channels, volume_ul, cycles):
        if not self.tip:
            raise DryRunError("mix without tip")
        if volume_ul > self.tip["cap"]:
            raise DryRunError("mix volume exceeds tip")
        for w in wells:
            if self.vol[labware].get(w, 0.0) + 1e-6 < volume_ul:
                raise DryRunError(f"{labware}/{w}: mix volume {volume_ul} > liquid present")

    def manual(self, step, message, duration_s):
        self.log.append(f"MANUAL {message} ({duration_s:g}s)")

    def pause(self, step, reason, duration_s, message):
        self.log.append(f"PAUSE {message}")
