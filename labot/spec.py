"""Customer process description (input).  Load from YAML/dict."""
from dataclasses import dataclass, field, fields
from typing import Optional

from . import catalog
from .deck import DeckLayout


@dataclass
class Source:
    name: str
    labware: str
    role: str = "per_sample"        # per_sample: one well per sample | reagent: shared liquid
    count_per_run: Optional[int] = None   # labware pieces per run (auto when omitted)
    fill_ul: Optional[float] = None       # per-well fill (auto = consumption + dead volume)
    slot: Optional[str] = None            # optional pin, e.g. "M1"


@dataclass
class Target:
    name: str
    labware: str
    count_per_run: Optional[int] = None
    slot: Optional[str] = None


@dataclass
class Step:
    name: str
    type: str = "transfer"          # transfer | mix | manual
    source: Optional[str] = None
    target: Optional[str] = None
    volume_ul: float = 0.0          # per well
    mode: str = "one_to_one"        # one_to_one | distribute (one reagent -> every target well)
    tip: str = "new"                # new: fresh tips per head movement | reuse: one tip set, multi-dispense in air
    mix_cycles: int = 0
    mix_volume_ul: Optional[float] = None
    duration_s: float = 0.0         # manual steps (incubation, centrifuge, seal ...)
    message: str = ""


@dataclass
class ProcessSpec:
    name: str
    samples_per_run: int
    runs_per_day: int
    channels: list = field(default_factory=lambda: [8])   # one value = fixed; several = optimise
    sources: list = field(default_factory=list)
    targets: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    process: str = "custom"
    tip_types: list = field(default_factory=lambda: [50, 200, 1000])
    hours_per_day: float = 8.0
    changeover_s: float = 600.0     # unload/load deck between runs
    excess_ul: float = 5.0          # per-channel over-aspiration for multi-dispense
    deck: DeckLayout = field(default_factory=DeckLayout)
    timing: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "ProcessSpec":
        from .templates import expand
        d = expand(dict(d))
        ch = d.get("channels", [8])
        d["channels"] = [ch] if isinstance(ch, int) else list(ch)
        d["sources"] = [Source(**s) for s in d.get("sources", [])]
        d["targets"] = [Target(**t) for t in d.get("targets", [])]
        d["steps"] = [Step(**s) for s in d.get("steps", [])]
        if "deck" in d:
            d["deck"] = DeckLayout(**d["deck"])
        d.pop("params", None)
        known = {f.name for f in fields(cls)}
        extra = set(d) - known
        if extra:
            raise ValueError(f"unknown spec keys: {sorted(extra)}")
        spec = cls(**d)
        spec.validate()
        return spec

    @classmethod
    def from_yaml(cls, path: str) -> "ProcessSpec":
        import yaml
        with open(path) as f:
            return cls.from_dict(yaml.safe_load(f))

    def validate(self):
        names = [s.name for s in self.sources] + [t.name for t in self.targets]
        if len(names) != len(set(names)):
            raise ValueError("source/target names must be unique")
        for s in self.sources + self.targets:
            catalog.get(s.labware)
        for s in self.sources:
            if s.role not in ("per_sample", "reagent"):
                raise ValueError(f"source {s.name}: role must be per_sample or reagent")
        for c in self.channels:
            if c not in (1, 2, 4, 8, 96):
                raise ValueError("channels must be one of 1, 2, 4, 8, 96")
        for st in self.steps:
            if st.type not in ("transfer", "mix", "manual"):
                raise ValueError(f"step {st.name}: bad type {st.type}")
            if st.type == "transfer" and st.mode not in ("one_to_one", "distribute"):
                raise ValueError(f"step {st.name}: bad mode {st.mode}")
            if st.tip not in ("new", "reuse"):
                raise ValueError(f"step {st.name}: tip must be new or reuse")
            if st.type != "manual":
                for ref in ([st.source] if st.type == "transfer" else []) + [st.target]:
                    if ref not in names:
                        raise ValueError(f"step {st.name}: unknown source/target '{ref}'")
