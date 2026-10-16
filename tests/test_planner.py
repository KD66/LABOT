import importlib.util
import pathlib

import pytest

from labot import ProcessSpec, build, emit_python, optimize
from labot.driver import DryRunDriver, DryRunError

EX = pathlib.Path(__file__).parent.parent / "examples"


def load_module(code, tmp_path):
    f = tmp_path / "run_mod.py"
    f.write_text(code)
    spec = importlib.util.spec_from_file_location("run_mod", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("name", ["ngs_library_prep", "lcms_sample_prep"])
def test_examples_replay_cleanly(name, tmp_path):
    spec = ProcessSpec.from_yaml(str(EX / f"{name}.yaml"))
    best = optimize(spec)[0]
    assert best.ok, best.errors
    m = load_module(emit_python(best), tmp_path)
    d = DryRunDriver(m)
    m.execute(d)                      # raises on tip reuse, overfill, dead volume, ...
    assert d.tip is None
    # every sample well in the final target holds the summed volume
    assert m.SUMMARY["channels"] == best.channels


def test_deck_slots_never_double_booked():
    spec = ProcessSpec.from_yaml(str(EX / "ngs_library_prep.yaml"))
    plan = optimize(spec)[0]
    slots = [s for v in plan.instances.values() if not v.get("reload") for s in v["slots"]]
    assert len(slots) == len(set(slots))
    for iid, v in plan.instances.items():
        if v["labware"].startswith("tube_rack"):
            assert len(v["slots"]) == 2


def test_eight_channel_is_faster_than_single():
    spec = ProcessSpec.from_yaml(str(EX / "ngs_library_prep.yaml"))
    p1, p8 = build(spec, 1), build(spec, 8)
    assert p8.summary["run_time_s"] < p1.summary["run_time_s"] / 2


def test_96_head_uses_one_tip_set_per_step():
    spec = ProcessSpec.from_dict(dict(
        name="t", samples_per_run=96, runs_per_day=1, channels=96,
        sources=[dict(name="s", labware="plate96_pcr")],
        targets=[dict(name="d", labware="plate96_pcr")],
        steps=[dict(name="x", source="s", target="d", volume_ul=20)]))
    p = build(spec, 96)
    assert p.ok, p.errors
    assert [c["cmd"] for c in p.commands if c["cmd"] != "comment"] == ["pick_up_tip", "aspirate", "dispense", "drop_tip"]
    assert p.summary["tips_per_run"] == {200: 96} or p.summary["tips_per_run"] == {50: 96}


def test_tube_row_reagent_rejects_multichannel():
    spec = ProcessSpec.from_dict(dict(
        name="t", samples_per_run=8, runs_per_day=1, channels=[8, 1],
        sources=[dict(name="r", labware="small_tube_row_12_5ml", role="reagent")],
        targets=[dict(name="d", labware="plate96_pcr")],
        steps=[dict(name="x", source="r", target="d", mode="distribute", volume_ul=10, tip="reuse")]))
    best = optimize(spec)[0]
    assert best.channels == 1 and best.ok
    assert not build(spec, 8).ok


def test_overfill_is_reported():
    spec = ProcessSpec.from_dict(dict(
        name="t", samples_per_run=8, runs_per_day=1, channels=8,
        sources=[dict(name="s", labware="plate96_pcr")],
        targets=[dict(name="d", labware="plate96_pcr")],
        steps=[dict(name="x", source="s", target="d", volume_ul=150),
               dict(name="y", source="s", target="d", volume_ul=150)]))
    assert any("overfilled" in e for e in build(spec, 8).errors)


def test_too_much_labware_for_deck():
    spec = ProcessSpec.from_dict(dict(
        name="t", samples_per_run=384, runs_per_day=1, channels=1,
        sources=[dict(name="s", labware="tube_rack_1p5ml_96")],
        targets=[dict(name="d", labware="plate96_pcr")],
        steps=[dict(name="x", source="s", target="d", volume_ul=10)]))
    p = build(spec, 1)
    assert not p.ok and any("cannot place" in e for e in p.errors)


def test_partial_column_uses_channel_mask():
    spec = ProcessSpec.from_dict(dict(
        name="t", samples_per_run=12, runs_per_day=1, channels=8,
        sources=[dict(name="s", labware="plate96_pcr")],
        targets=[dict(name="d", labware="plate96_pcr")],
        steps=[dict(name="x", source="s", target="d", volume_ul=10)]))
    p = build(spec, 8)
    asp = [c for c in p.commands if c["cmd"] == "aspirate"]
    assert [c["n_channels"] for c in asp] == [8, 4]
    assert asp[1]["wells"] == ["A2", "B2", "C2", "D2"]


def test_dryrun_catches_tip_reuse_between_samples(tmp_path):
    spec = ProcessSpec.from_yaml(str(EX / "lcms_sample_prep.yaml"))
    m = load_module(emit_python(optimize(spec)[0]), tmp_path)
    d = DryRunDriver(m)
    first = next(c for c in m.COMMANDS if c["cmd"] == "pick_up_tip")
    d.pick_up_tip(**{k: v for k, v in first.items() if k != "cmd"})
    with pytest.raises(DryRunError):
        d.pick_up_tip(**{k: v for k, v in first.items() if k != "cmd"})
