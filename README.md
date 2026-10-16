# LABOT – run planner for a 3×2 SBS deck

Customer process description in → deck layout, tip/consumable budget, timing and a
**Python module with the complete run** out.

```
python -m labot examples/ngs_library_prep.yaml -o runs/ngs_run.py
python -m labot examples/lcms_sample_prep.yaml --channels 8 -o runs/lcms_run.py
python -m pytest
```
Exit code: 0 ok, 2 no feasible plan, 3 feasible but runs/day does not fit in `hours_per_day`.

## Deck model (`labot/deck.py`)
| ids | what |
|---|---|
| `M1–M3` front, `M4–M6` back | 6 main SBS slots (3×2) |
| `F1–F3`, `B1–B3` | 3 narrow single-row slots in front / back |
| two-slot item | 96 Eppendorf rack = 2 neighbouring main slots (`deck.two_slot_orientation`: horizontal/vertical/any) |

Tip racks take main slots too, so they compete with labware; the planner gives tips
whatever is free and inserts an operator `pause` for every rack that must be swapped.

## Input (YAML or `ProcessSpec.from_dict`)
```yaml
name: my_run
process: custom | ngs_library_prep | lcms_sample_prep   # templates fill missing sources/targets/steps
samples_per_run: 96
runs_per_day: 4
channels: [1, 8]        # fixed (one value) or candidates to optimise; 1,2,4,8,96
hours_per_day: 8        # changeover_s, excess_ul, tip_types, timing: optional
sources:                # per_sample = one well per sample, reagent = shared liquid
  - {name: samples, labware: tube_rack_1p5ml_96}
  - {name: mm, labware: reagent_auto, role: reagent}    # auto = narrow trough > 12-well > 1-well
targets:
  - {name: plate, labware: plate96_pcr}
steps:
  - {name: add_mm, source: mm, target: plate, mode: distribute, volume_ul: 15, tip: reuse}
  - {name: add_sample, source: samples, target: plate, volume_ul: 10, mix_cycles: 5}
  - {name: incubate, type: manual, duration_s: 600, message: "..."}
```
Labware keys: `labot/catalog.py` (plates, 1.5/2 mL racks, reservoirs, narrow-slot items, tips).
Step `mode`: `one_to_one` (sample i → well i, new tips) or `distribute` (one reagent → every
target well; `tip: reuse` = one tip set, multi-dispense in air). `type: mix` and `manual` also exist.

## What the planner decides
* units per head movement (column of 8, partial columns via channel mask, whole plate for 96-head)
* tip size per step (fewest aspirations, ≥5 % of capacity if possible), multi-dispense counts, splitting of volumes larger than a tip
* reagent wells, fill volumes (consumption + dead volume), packing of reagents into shared reservoirs
* slot assignment, tip racks, reloads, run time, max runs/day, per-day consumables and reagent volumes
* `optimize()` compares every channel count × (all tip types | single tip type) and ranks by
  feasibility → throughput → tip reloads → low-precision pipetting → run time.

## Output module (`COMMANDS` is the run)
Constants: `RUN_NAME, PROCESS, CHANNELS, SAMPLES_PER_RUN, RUNS_PER_DAY, DECK_LAYOUT, LABWARE,
INSTANCES, DECK, REAGENTS, INITIAL_VOLUMES_UL, STEPS, SUMMARY, WARNINGS, COMMANDS` and
`execute(driver)`, which calls `driver.<cmd>(**args)` for `pick_up_tip, aspirate, dispense, mix,
drop_tip, manual, pause, comment`. `labot.driver.DryRunDriver` replays a run and fails on tip
reuse, tip/well overfill, aspiration below dead volume or mixing dry wells.

## Assumptions to confirm / calibrate
* timing constants (`DEFAULT_TIMING`), 5 µL excess for multi-dispense, 95 % tip fill
* 384 plates and narrow tube rows are single-channel only; 96-head needs a 1-well reservoir for reagents
* tip waste is off-deck; a partly used tip column is discarded
* no replicates, cherry-picking or pooling yet; no liquid-class / height parameters
