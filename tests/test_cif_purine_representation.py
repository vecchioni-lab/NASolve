"""Bounded declared purine representation; no aromaticity or tautomer invention."""
from copy import deepcopy

import pytest

from nasolve.cif_generation import inspect_component_generation
from nasolve.cif_candidate_usability import reassess_complete_candidate, qualify_candidate_native
from tests.test_cif_aromatic_representation import add_angles, pair as six_pair
from tests.test_cif_stereochemistry_audit import write

POLICY = "cif-source-declared-neutral-purine-aromatic-v1"
A, B = "_chem_comp_atom.", "_chem_comp_bond."


def pair(code="Q17"):
    ring = ["N1", "C2", "N3", "C4", "C5", "C6", "N7", "C8", "N9"]
    names = ring + ["N6", "R", "H2", "H8", "H61", "H62", "HR1", "HR2", "HR3"]
    edges = [("N1", "C2"), ("C2", "N3"), ("N3", "C4"), ("C4", "C5"),
             ("C5", "C6"), ("C6", "N1"), ("C5", "N7"), ("N7", "C8"),
             ("C8", "N9"), ("N9", "C4"), ("C6", "N6"), ("N9", "R"),
             ("C2", "H2"), ("C8", "H8"), ("N6", "H61"), ("N6", "H62"),
             ("R", "HR1"), ("R", "HR2"), ("R", "HR3")]
    elements = ["N" if n.startswith("N") else "H" if n.startswith("H") else "C" for n in names]
    v = {"data_": "comp_" + code, "_chem_comp.id": [code], A + "comp_id": [code] * len(names),
         A + "atom_id": names, A + "type_symbol": elements, A + "charge": ["0"] * len(names),
         A + "pdbx_stereo_config": ["N"] * len(names), B + "comp_id": [code] * len(edges),
         B + "atom_id_1": [a for a, b in edges], B + "atom_id_2": [b for a, b in edges],
         B + "value_order": ["DOUB" if i in {0, 2, 4, 7} else "SING" for i in range(len(edges))],
         B + "pdbx_aromatic_flag": ["Y"] * 10 + ["N"] * 9}
    g = deepcopy(v)
    g[B + "type"] = ["aromatic"] * 10 + ["single"] * 9
    g.pop(B + "value_order"); g.pop(B + "pdbx_aromatic_flag")
    g[A + "type_energy"] = elements[:]
    g[B + "value_dist"] = ["1.4"] * len(edges); g[B + "value_dist_esd"] = ["0.02"] * len(edges)
    add_angles(g)
    return v, g


def inspect(tmp_path, v, g):
    source, candidate = write(tmp_path / "source.cif", v), write(tmp_path / "candidate.cif", g)
    before = source.read_bytes(), candidate.read_bytes()
    old = inspect_component_generation(source, candidate, v["_chem_comp.id"][0])
    new = inspect_component_generation(source, candidate, v["_chem_comp.id"][0], bond_representation_policy=POLICY)
    assert old == inspect_component_generation(source, candidate, v["_chem_comp.id"][0])
    assert before == (source.read_bytes(), candidate.read_bytes())
    return old, new


@pytest.mark.parametrize("variant", ["plain", "renamed", "permuted", "alternate_kekule", "charged_side", "other_pyrrolic_N", "deuterated"])
def test_complete_neutral_purine_is_explicit_opt_in_without_rewriting_legacy(tmp_path, variant):
    v, g = pair("X83")
    if variant == "alternate_kekule":
        v[B + "value_order"][:6] = ["SING", "DOUB", "SING", "DOUB", "SING", "DOUB"]
    if variant == "charged_side":
        # N9-CH2-NH3+ retains the remote charge without charging the ring.
        for d in (v, g):
            d[A + "atom_id"][-1] = "NT"; d[A + "type_symbol"][-1] = "N"
            d[A + "charge"][-1] = "1"; d[B + "atom_id_2"][-1] = "NT"
            if A + "type_energy" in d: d[A + "type_energy"][-1] = "N"
            for k in list(d):
                if k.startswith(A):
                    suffix = k[len(A):]
                    d[k].extend(["HT1", "HT2", "HT3"] if suffix == "atom_id" else
                        ["X83"] * 3 if suffix == "comp_id" else ["0"] * 3 if suffix == "charge" else
                        ["N"] * 3 if suffix == "pdbx_stereo_config" else ["H"] * 3)
                if k.startswith(B):
                    suffix = k[len(B):]
                    d[k].extend(["HT1", "HT2", "HT3"] if suffix == "atom_id_2" else
                        ["NT"] * 3 if suffix == "atom_id_1" else ["X83"] * 3 if suffix == "comp_id" else
                        ["1.0"] * 3 if suffix == "value_dist" else ["0.02"] * 3 if suffix == "value_dist_esd" else
                        ["N"] * 3 if suffix == "pdbx_aromatic_flag" else ["SING"] * 3)
        add_angles(g)
    if variant == "other_pyrrolic_N":
        v[B + "value_order"][7:9] = ["SING", "DOUB"]
        for d in (v, g): d[B + "atom_id_1"][11] = "N7"
        add_angles(g)
    if variant == "deuterated":
        for d in (v, g): d[A + "type_symbol"][11] = "D"
        g[A + "type_energy"][11] = "D"
    if variant == "renamed":
        mapping = {n: "Z" + str(i) for i, n in enumerate(v[A + "atom_id"])}
        for d in (v, g):
            for k in d:
                if k.split(".")[-1].startswith("atom_id"): d[k] = [mapping.get(x, x) for x in d[k]]
    if variant == "permuted":
        for d in (v, g):
            for k in d:
                if k.startswith((A, B)): d[k] = list(reversed(d[k]))
    old, new = inspect(tmp_path, v, g)
    assert old["status"] == "REJECTED" and new["status"] == "CANDIDATE_REVIEW"
    r = new["bond_representation"]
    assert r["policy_id"] == POLICY and r["status"] == "SOURCE_DECLARED_EQUIVALENT"
    assert len(r["equivalent_fused_systems"]) == 1 and not r["unresolved_bonds"]
    assert r["equivalent_fused_systems"][0]["cycle_sizes"] == [5, 6]
    assert any(x["field"] == "bond_orders" for x in new["chemical_changes"])
    assert new["automatic_adoption"] is False
    q = reassess_complete_candidate(tmp_path / "source.cif", tmp_path / "candidate.cif", "X83", bond_representation_policy=POLICY)
    assert q["candidate_status"] == "CANDIDATE_REVIEW" and q["native_usability"] == "NOT_RUN"


@pytest.mark.parametrize("defect", ["missing_flag", "conflicting_flag", "candidate_flag_N", "partial",
    "generic_delocalized", "ring_charge", "missing_charge", "charge_alias_conflict", "outside_charge",
    "hydrogen_move", "isotope_change", "atom_change", "outside_order", "exocyclic_double", "unfilled_valence",
    "overfilled_valence", "ring_stereo", "bond_stereo", "wrong_N_pattern", "fusion_N", "extra_edge", "source_charge_missing", "source_charge_conflict", "new_fusion"])
def test_aromatic_flags_never_authorize_other_chemical_changes(tmp_path, defect):
    v, g = pair()
    if defect == "missing_flag": v.pop(B + "pdbx_aromatic_flag")
    if defect == "conflicting_flag": v[B + "aromatic"] = ["N"] * 19
    if defect == "candidate_flag_N": g[B + "pdbx_aromatic_flag"] = ["N"] * 19
    if defect == "partial": g[B + "type"][0] = "double"
    if defect == "generic_delocalized": g[B + "type"][:10] = ["deloc"] * 10
    if defect == "ring_charge":
        for d in (v, g): d[A + "charge"][0] = "1"
    if defect == "missing_charge": g[A + "charge"][0] = "?"
    if defect == "charge_alias_conflict": g[A + "pdbx_formal_charge"] = ["1"] + ["0"] * 17
    if defect == "outside_charge": g[A + "charge"][-1] = "1"
    if defect == "hydrogen_move": g[B + "atom_id_1"][12] = "C8"; add_angles(g)
    if defect == "isotope_change": g[A + "type_symbol"][-1] = "D"
    if defect == "atom_change": g[A + "type_symbol"][0] = "C"
    if defect == "outside_order": g[B + "type"][-1] = "double"
    if defect == "exocyclic_double": v[B + "value_order"][10] = "DOUB"; g[B + "type"][10] = "double"
    if defect == "unfilled_valence": v[B + "value_order"][0] = "SING"
    if defect == "overfilled_valence": v[B + "value_order"][1] = "DOUB"
    if defect == "ring_stereo":
        for d in (v, g): d[A + "pdbx_stereo_config"][0] = "R"
    if defect == "bond_stereo": v[B + "pdbx_stereo_config"] = ["E"] + ["N"] * 18
    if defect == "wrong_N_pattern":
        for d in (v, g): d[A + "type_symbol"][0:2] = ["C", "N"]
    if defect == "fusion_N":
        for d in (v, g): d[A + "type_symbol"][3] = "N"
    if defect == "source_charge_missing": v[A + "charge"][0] = "?"
    if defect == "source_charge_conflict": v[A + "pdbx_formal_charge"] = ["1"] + ["0"] * 17
    if defect == "new_fusion":
        # Close a substituent ring without changing the candidate connectivity.
        for d in (v, g):
            for k in list(d):
                if k.startswith(B): d[k].append("Q17" if k.endswith("comp_id") else "R" if k.endswith("atom_id_1") else "N6" if k.endswith("atom_id_2") else "1.4" if k.endswith("value_dist") else "0.02" if k.endswith("value_dist_esd") else "N" if k.endswith("pdbx_aromatic_flag") else "SING")
        add_angles(g)
    if defect == "extra_edge":
        for k in list(g):
            if k.startswith(B): g[k].append("Q17" if k.endswith("comp_id") else "N1" if k.endswith("atom_id_1") else "N9" if k.endswith("atom_id_2") else "single" if k.endswith("type") else "1.4" if k.endswith("value_dist") else "0.02")
        add_angles(g)
    old, new = inspect(tmp_path, v, g)
    assert new["status"] == "REJECTED"
    assert new["bond_representation"]["status"] == "UNSUPPORTED_DIFFERENCE"
    assert not new["automatic_adoption"]


def test_isolated_six_ring_and_exact_legacy_results_stay_available(tmp_path):
    v, g = six_pair()
    old, new = inspect(tmp_path, v, g)
    assert new["status"] == old["status"] == "CANDIDATE_REVIEW"
    assert new["bond_representation"]["equivalent_rings"] == old["bond_representation"]["equivalent_rings"]
    assert not new["bond_representation"]["equivalent_fused_systems"]


@pytest.mark.parametrize("api", ["inspect", "reassess", "qualify"])
def test_unknown_representation_policy_cannot_fall_back_silently(tmp_path, api):
    source, candidate = write(tmp_path / "s.cif", pair()[0]), write(tmp_path / "c.cif", pair()[1])
    with pytest.raises(ValueError, match="representation policy"):
        if api == "inspect": inspect_component_generation(source, candidate, "Q17", bond_representation_policy="guess")
        elif api == "reassess": reassess_complete_candidate(source, candidate, "Q17", bond_representation_policy="guess")
        else: qualify_candidate_native(source, candidate, tmp_path / "absent.pdb", "Q17", {}, bond_representation_policy="guess")


def test_native_qualifier_threads_policy_but_keeps_all_other_checks(tmp_path):
    from tests.test_cif_candidate_usability import native_case
    source, candidate, model, native = native_case(tmp_path)
    old = qualify_candidate_native(source, candidate, model, "Q17", native)
    new = qualify_candidate_native(source, candidate, model, "Q17", native, bond_representation_policy=POLICY)
    assert old["checks"] == new["checks"] and new["native_usable"]
    native["geometry"]["proxy_details"]["bond_simple"][0]["distance_ideal"] += 0.1
    bad = qualify_candidate_native(source, candidate, model, "Q17", native, bond_representation_policy=POLICY)
    assert not bad["native_usable"] and not bad["checks"]["exact_active_bonds"]
