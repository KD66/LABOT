"""Labware catalogue.  Volumes in uL.  Edit / extend to match the real hardware.

footprint: "sbs"   one SBS slot (main deck)
           "sbs2"  two adjacent SBS slots (96 Eppendorf tube rack)
           "small" one of the 3+3 narrow slots (front/back), single row only
kind     : plate | tubes | trough | tips
multichannel: True if 8 channels can work the labware at 9 mm pitch (or all
              dip into one well for troughs).  Narrow-slot tube rows are
              single-channel only.
"""
from dataclasses import dataclass

ROW_NAMES = "ABCDEFGHIJKLMNOP"


@dataclass(frozen=True)
class Labware:
    key: str
    description: str
    kind: str
    rows: int
    cols: int
    footprint: str
    max_ul: float = 0.0
    dead_ul: float = 0.0
    tip_cap_ul: float = 0.0
    multichannel: bool = True

    @property
    def positions(self) -> int:
        return self.rows * self.cols

    def wells(self):
        """Well names, column-major (A1, B1 ... H1, A2 ...)."""
        return [f"{ROW_NAMES[r]}{c + 1}" for c in range(self.cols) for r in range(self.rows)]


def _lw(*a, **k):
    x = Labware(*a, **k)
    return x.key, x


CATALOG = dict([
    _lw("plate96_pcr", "96w PCR plate 0.2 mL", "plate", 8, 12, "sbs", 200, 5),
    _lw("plate96_dw_2ml", "96 deepwell plate 2 mL", "plate", 8, 12, "sbs", 2000, 30),
    _lw("plate96_lcms_350", "96w LC-MS vial plate 350 uL", "plate", 8, 12, "sbs", 350, 10),
    _lw("plate384_pcr", "384w PCR plate (single channel only)", "plate", 16, 24, "sbs", 50, 2, multichannel=False),
    _lw("tube_rack_1p5ml_96", "96 Eppendorf 1.5 mL tubes (2 slots)", "tubes", 8, 12, "sbs2", 1500, 30),
    _lw("tube_rack_2ml_96", "96 Eppendorf 2.0 mL tubes (2 slots)", "tubes", 8, 12, "sbs2", 2000, 30),
    _lw("reservoir_1well_sbs", "1-well reservoir 150 mL", "trough", 1, 1, "sbs", 150000, 5000),
    _lw("reservoir_12well_sbs", "12-well reservoir 20 mL/well", "trough", 1, 12, "sbs", 20000, 1500),
    _lw("small_trough_1well", "narrow-slot trough 25 mL", "trough", 1, 1, "small", 25000, 2000),
    _lw("small_tube_row_12_5ml", "narrow-slot row of 12 x 5 mL tubes (1 channel)", "tubes", 1, 12, "small", 5000, 300, multichannel=False),
    _lw("small_strip_12_0p2ml", "narrow-slot row of 12 x 0.2 mL strip tubes (1 channel)", "tubes", 1, 12, "small", 200, 10, multichannel=False),
    _lw("reagent_auto", "reagent trough - planner picks narrow-slot / 12-well / 1-well", "trough", 1, 1, "small", 25000, 2000),
    _lw("tips_50", "50 uL tips, 96", "tips", 8, 12, "sbs", tip_cap_ul=50),
    _lw("tips_200", "200 uL tips, 96", "tips", 8, 12, "sbs", tip_cap_ul=200),
    _lw("tips_1000", "1000 uL tips, 96", "tips", 8, 12, "sbs", tip_cap_ul=1000),
])


def get(key: str) -> Labware:
    try:
        return CATALOG[key]
    except KeyError:
        raise KeyError(f"unknown labware '{key}'; known: {', '.join(CATALOG)}") from None
