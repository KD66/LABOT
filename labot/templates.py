"""Default process skeletons for common workflows.

A template only fills in sources / targets / steps that the customer spec does
not give explicitly; volumes come from `params` (uL).
"""


def _ngs_library_prep(p):
    sample_v = p.get("sample_ul", 10)
    return dict(
        sources=[
            dict(name="samples", labware="tube_rack_1p5ml_96"),
            dict(name="frag_mm", labware="reagent_auto", role="reagent"),
            dict(name="index_plate", labware="plate96_pcr"),
            dict(name="pcr_mm", labware="reagent_auto", role="reagent"),
        ],
        targets=[dict(name="lib_plate", labware="plate96_pcr")],
        steps=[
            # master mix first, then samples are mixed in with the same tips that dispense them
            dict(name="frag_ligation_mm", source="frag_mm", target="lib_plate", mode="distribute",
                 volume_ul=p.get("frag_mm_ul", 15), tip="reuse"),
            dict(name="sample_to_plate", source="samples", target="lib_plate", volume_ul=sample_v, mix_cycles=5),
            dict(name="incubate_1", type="manual", target="lib_plate", duration_s=p.get("incubate_s", 1800),
                 message="Seal plate, run fragmentation/ligation on thermocycler, unseal, return to deck"),
            dict(name="indexes", source="index_plate", target="lib_plate", volume_ul=p.get("index_ul", 5), mix_cycles=3),
            dict(name="pcr_mix", source="pcr_mm", target="lib_plate", mode="distribute",
                 volume_ul=p.get("pcr_mm_ul", 25), tip="reuse"),
            dict(name="seal_and_pcr", type="manual", target="lib_plate", duration_s=p.get("seal_s", 120),
                 message="Seal, vortex, spin down, move to thermocycler"),
        ],
    )


def _lcms_sample_prep(p):
    return dict(
        sources=[
            dict(name="samples", labware="tube_rack_2ml_96"),
            dict(name="internal_std", labware="reagent_auto", role="reagent"),
            dict(name="precip_solvent", labware="reagent_auto", role="reagent"),
        ],
        targets=[dict(name="prep_plate", labware="plate96_dw_2ml"),
                 dict(name="vial_plate", labware="plate96_lcms_350")],
        steps=[
            dict(name="sample_to_plate", source="samples", target="prep_plate", volume_ul=p.get("sample_ul", 50)),
            dict(name="add_is", source="internal_std", target="prep_plate", mode="distribute",
                 volume_ul=p.get("is_ul", 10), tip="reuse"),
            dict(name="add_solvent", source="precip_solvent", target="prep_plate", mode="distribute",
                 volume_ul=p.get("solvent_ul", 150), tip="new", mix_cycles=3),
            dict(name="centrifuge", type="manual", target="prep_plate", duration_s=p.get("spin_s", 900),
                 message="Seal, vortex, centrifuge 15 min, unseal, return to deck"),
            dict(name="supernatant_to_vials", source="prep_plate", target="vial_plate",
                 volume_ul=p.get("transfer_ul", 100)),
        ],
    )


TEMPLATES = {"ngs_library_prep": _ngs_library_prep, "lcms_sample_prep": _lcms_sample_prep}


def expand(d: dict) -> dict:
    proc = d.get("process", "custom")
    if proc == "custom":
        return d
    if proc not in TEMPLATES:
        raise ValueError(f"unknown process '{proc}'; known: custom, {', '.join(TEMPLATES)}")
    base = TEMPLATES[proc](d.get("params", {}))
    for key in ("sources", "targets", "steps"):
        d.setdefault(key, base[key])
    return d
