"""Quarantine generic ReadySet numerical failures without rewriting chemistry."""
import hashlib
import json

import pytest

from nasolve.ligand_profiles import _emit, _parameterized_codes
from nasolve.postmr import PostMRPreparationError, _require_generic_parameterization


def _dictionary(tmp_path, *, code="VWX", target="1.4", coincident=False):
    values = {"data_": "comp_" + code, "_chem_comp.id": [code],
              "_chem_comp_atom.comp_id": [code] * 3,
              "_chem_comp_atom.atom_id": ["C5'", "N9", "H9"],
              "_chem_comp_atom.type_symbol": ["C", "N", "H"],
              "_chem_comp_atom.type_energy": ["C", "N", "H"],
              "_chem_comp_atom.x": ["0", "0" if coincident else "1.4", "2.4"],
              "_chem_comp_atom.y": ["0"] * 3, "_chem_comp_atom.z": ["0"] * 3,
              "_chem_comp_bond.comp_id": [code] * 2,
              "_chem_comp_bond.atom_id_1": ["C5'", "N9"],
              "_chem_comp_bond.atom_id_2": ["N9", "H9"],
              "_chem_comp_bond.value_order": ["SING"] * 2,
              "_chem_comp_bond.value_dist": [target, "1.0"],
              "_chem_comp_bond.value_dist_esd": ["0.02"] * 2,
              "_chem_comp_angle.comp_id": [code],
              "_chem_comp_angle.atom_id_1": ["C5'"],
              "_chem_comp_angle.atom_id_2": ["N9"],
              "_chem_comp_angle.atom_id_3": ["H9"],
              "_chem_comp_angle.value_angle": ["110"],
              "_chem_comp_angle.value_angle_esd": ["2"]}
    path = tmp_path / "generated.cif"
    path.write_text(_emit(values), encoding="utf-8")
    return path


def _receipt(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["audit_kind"] == "readyset_generic_generation_failure"
    assert data["status"] == "QUARANTINED"
    assert data["action"] == "regenerate-whole-component-from-frozen-chemical-source"
    return data


@pytest.mark.parametrize("code", ["VWX", "RENAMED_COMPONENT"])
@pytest.mark.parametrize("target,word", [("0.000", "zero"), ("nan", "non-finite"),
                                        ("inf", "non-finite"), ("broken", "unusable")])
def test_failed_numerical_targets_have_exact_general_diagnostics_and_preserved_inputs(
        tmp_path, code, target, word):
    generated = _dictionary(tmp_path, code=code, target=target)
    before = generated.read_bytes()
    failure = tmp_path / "generation_failure.json"
    with pytest.raises(PostMRPreparationError) as raised:
        _require_generic_parameterization({code: {"parameterized": False}}, generated,
                                          tmp_path / "ready_set.log", failure_report=failure)
    assert f"parameterized ligand restraints for {code}" in str(raised.value)
    assert f"{word} numerical parameter C5'–N9 value_dist={target}" in str(raised.value)
    assert "whole component dictionary" in str(raised.value)
    assert "do not patch individual target numbers" in str(raised.value)
    report = _receipt(failure)
    assert report["affected_components"][0]["component_id"] == code
    assert not report["affected_components"][0]["legacy_parameterization_passed"]
    reasons = report["affected_components"][0]["reasons"]
    failure_reason, = [reason for reason in reasons
                       if reason["code"] in {"numeric-domain-violation", "invalid-numeric-value"}]
    assert failure_reason["measurements"]["atoms"] == ["C5'", "N9"]
    assert failure_reason["measurements"]["value"] == target
    assert report["assessment"]["inputs"][0]["sha256"] == hashlib.sha256(before).hexdigest()
    assert generated.read_bytes() == before


def test_strictly_positive_target_cannot_hide_degenerate_supplier_coordinates(tmp_path):
    generated = _dictionary(tmp_path, coincident=True)
    before = generated.read_bytes()
    assert _parameterized_codes(generated) == {"VWX"}
    failure = tmp_path / "generation_failure.json"
    with pytest.raises(PostMRPreparationError, match="coincident bonded heavy atoms C5'–N9"):
        _require_generic_parameterization({"VWX": {"parameterized": False}}, generated,
                                          tmp_path / "ready_set.log", failure_report=failure)
    item, = _receipt(failure)["affected_components"]
    assert item["legacy_parameterization_passed"]
    collision, = item["reasons"]
    assert collision["code"] == "coincident-bonded-heavy-atoms"
    assert collision["measurements"]["atoms"] == ["C5'", "N9"]
    assert generated.read_bytes() == before


@pytest.mark.parametrize("supplied_missing_path", [False, True])
def test_absent_generated_output_is_reported_without_claiming_a_bad_bond(tmp_path, supplied_missing_path):
    failure = tmp_path / "generation_failure.json"
    generated = tmp_path / "absent.cif" if supplied_missing_path else None
    with pytest.raises(PostMRPreparationError, match="numerical output dictionary is absent"):
        _require_generic_parameterization({"VWX": {"parameterized": False}}, generated,
                                          tmp_path / "ready_set.log", failure_report=failure)
    item, = _receipt(failure)["affected_components"]
    assert item["reasons"][0]["code"] == "missing-generated-dictionary"
    assert not any(reason["code"] == "coincident-bonded-heavy-atoms" for reason in item["reasons"])


def test_missing_generated_component_cannot_borrow_another_code_numerics(tmp_path):
    generated = _dictionary(tmp_path, code="OTHER")
    failure = tmp_path / "generation_failure.json"
    with pytest.raises(PostMRPreparationError, match="generated dictionary omits the component"):
        _require_generic_parameterization({"VWX": {"parameterized": False}}, generated,
                                          tmp_path / "ready_set.log", failure_report=failure)
    item, = _receipt(failure)["affected_components"]
    assert item["component_id"] == "VWX"
    assert item["reasons"][0]["code"] == "missing-generated-component"


@pytest.mark.parametrize("source", [{"VWX": {"parameterized": True}},
                                   {"1AP": {"parameterized": False}}])
def test_trusted_numeric_inputs_and_curated_precedence_do_not_adopt_bad_generated_rows(tmp_path, source):
    code = next(iter(source))
    generated = _dictionary(tmp_path, code=code, target="0", coincident=True)
    before = generated.read_bytes()
    failure = tmp_path / "generation_failure.json"
    _require_generic_parameterization(source, generated, tmp_path / "ready_set.log",
                                      failure_report=failure)
    assert not failure.exists()
    assert generated.read_bytes() == before


def test_bad_readyset_rows_for_trusted_input_do_not_block_unrelated_usable_generic_component(tmp_path):
    first = _dictionary(tmp_path, code="VWX")
    good = first.read_bytes()
    _dictionary(tmp_path, code="TRUSTED", target="0", coincident=True)
    first.write_bytes(good + first.read_bytes())
    before = first.read_bytes()
    failure = tmp_path / "generation_failure.json"
    _require_generic_parameterization({"VWX": {"parameterized": False},
                                       "TRUSTED": {"parameterized": True}}, first,
                                      tmp_path / "ready_set.log", failure_report=failure)
    assert not failure.exists()
    assert first.read_bytes() == before


def test_unusable_generic_numeric_receipt_is_optional_for_existing_api_callers(tmp_path):
    generated = _dictionary(tmp_path, target="0")
    before = generated.read_bytes()
    with pytest.raises(PostMRPreparationError, match="parameterized ligand restraints for VWX"):
        _require_generic_parameterization({"VWX": {"parameterized": False}}, generated,
                                          tmp_path / "ready_set.log")
    assert sorted(path.name for path in tmp_path.iterdir()) == ["generated.cif"]
    assert generated.read_bytes() == before


def test_existing_generation_receipt_is_never_overwritten(tmp_path):
    generated = _dictionary(tmp_path, target="0")
    before = generated.read_bytes()
    failure = tmp_path / "generation_failure.json"
    failure.write_bytes(b"previous immutable evidence\n")
    with pytest.raises(PostMRPreparationError, match="exclusive generation-failure receipt"):
        _require_generic_parameterization({"VWX": {"parameterized": False}}, generated,
                                          tmp_path / "ready_set.log", failure_report=failure)
    assert failure.read_bytes() == b"previous immutable evidence\n"
    assert generated.read_bytes() == before


def test_usable_generated_generic_component_never_writes_failure_receipt(tmp_path):
    generated = _dictionary(tmp_path)
    failure = tmp_path / "generation_failure.json"
    _require_generic_parameterization({"VWX": {"parameterized": False}}, generated,
                                      tmp_path / "ready_set.log", failure_report=failure)
    assert not failure.exists()


def _source_plane_case(tmp_path, *, code="XYZ", hand="R", variant=None):
    from tests.test_cif_stereochemistry_audit import tetrahedron, write
    source, candidate = tetrahedron(code)
    atom, bond, plane = "_chem_comp_atom.", "_chem_comp_bond.", "_chem_comp_plane_atom."
    source[atom + "pdbx_stereo_config"][0] = hand
    candidate[atom + "type_energy"] = list(candidate[atom + "type_symbol"])
    candidate[bond + "value_dist"] = ["1.5"] * 4
    candidate[bond + "value_dist_esd"] = ["0.02"] * 4
    members = ["CTR", "C", "N", "O"]
    if variant == "two-heavy-neighbors":
        members[3] = "H"
    elif variant == "missing-centre":
        members[0] = "H"
    elif variant == "changed-element":
        candidate[atom + "type_symbol"][1] = "S"
    elif variant == "disconnected-neighbor":
        candidate[bond + "atom_id_1"][0] = "H"
    elif variant == "non-carbon":
        source[atom + "type_symbol"][0] = candidate[atom + "type_symbol"][0] = "P"
    elif variant == "unsaturated-source":
        source[bond + "value_order"][0] = "DOUB"
    elif variant == "source-aromatic-flag":
        source[bond + "pdbx_aromatic_flag"] = ["Y", "N", "N", "N"]
    elif variant == "missing-effective-H":
        for key in tuple(candidate):
            if key.startswith((atom, bond)):
                candidate[key] = candidate[key][:-1]
    candidate[plane + "comp_id"] = [code] * 4
    candidate[plane + "plane_id"] = ["p"] * 4
    candidate[plane + "atom_id"] = members
    central_esd = {"missing-esd": "?", "weak-plane": "1.0"}.get(variant, "0.02")
    candidate[plane + "dist_esd"] = [central_esd,
                                    "0.02", "0.02", "0.02"]
    if variant in {"aromatic-bond", "uncertain-order", "conflicting-aromatic-flags", "non-aromatic-bond"}:
        candidate = {k: v for k, v in candidate.items() if not k.startswith(plane)}
        candidate[bond + "value_order"][0] = {"aromatic-bond":"AROM", "uncertain-order":"COVAL",
            "conflicting-aromatic-flags":"AROM", "non-aromatic-bond":"SING"}[variant]
        if variant == "conflicting-aromatic-flags":
            candidate[bond + "pdbx_aromatic_flag"] = ["N"] * 4
    return write(tmp_path / "source.cif", source), write(tmp_path / "candidate.cif", candidate)


@pytest.mark.parametrize("code,hand,variant", [("XYZ","R",None),("Z89","S","missing-effective-H")])
def test_generated_plane_conflicting_with_source_hand_is_caught_before_refinement(tmp_path, code, hand, variant):
    from nasolve.cif_doctor import assess_dictionaries, compare_dictionaries
    source, effective = _source_plane_case(tmp_path, code=code, hand=hand, variant=variant)
    receipt = tmp_path / "failure.json"
    inputs = [p.read_bytes() for p in (source, effective)]
    source_components = assess_dictionaries([source])["components"]
    with pytest.raises(PostMRPreparationError, match="tetrahedral CTR"):
        _require_generic_parameterization({code: {"parameterized": False}}, effective,
            tmp_path / "ready_set.log", failure_report=receipt, source_components=source_components)
    conflict = _receipt(receipt)["affected_components"][0]["reasons"][0]
    assert conflict["code"] == "plane-through-source-stereocentre"
    assert conflict["measurements"]["bonded_heavy_neighbors"] == ["C", "N", "O"]
    assert conflict["measurements"]["source_hand"] == hand
    assert conflict["measurements"]["source_definition_sha256"] == source_components[0]["definition_sha256"]
    assert conflict["measurements"]["effective_definition_sha256"] != conflict["measurements"]["source_definition_sha256"]
    new = compare_dictionaries([source], [effective], compare_stereo_planes=True)
    assert conflict in new["findings"]
    assert all(f["code"] != conflict["code"] for f in compare_dictionaries([source],[effective])["findings"])
    assert [p.read_bytes() for p in (source, effective)] == inputs


@pytest.mark.parametrize("hand,variant", [("R","two-heavy-neighbors"),("R","missing-centre"),
    ("R","missing-esd"),("N",None),("R","non-carbon"),("S","changed-element"),
    ("R","disconnected-neighbor"),("S","unsaturated-source"),("R","source-aromatic-flag")])
def test_source_plane_check_requires_matching_local_evidence(tmp_path, hand, variant):
    from nasolve.cif_doctor import compare_dictionaries
    source, effective = _source_plane_case(tmp_path, hand=hand, variant=variant)
    report = compare_dictionaries([source], [effective], compare_stereo_planes=True)
    assert all(f["code"] != "plane-through-source-stereocentre" for f in report["findings"])



@pytest.mark.parametrize("hand,code", [("R","XYZ"),("S","RAR")])
def test_specific_aromatic_declaration_at_handed_carbon_needs_no_plane(tmp_path, hand, code):
    from nasolve.cif_doctor import assess_dictionaries, compare_dictionaries
    source, effective = _source_plane_case(tmp_path, variant="aromatic-bond", hand=hand, code=code)
    review = compare_dictionaries([source], [effective], compare_stereo_bonds=True)
    hits = [f for f in review["findings"] if f["code"] == "aromatic-bond-at-source-stereocentre"]
    assert len(hits) == 1
    assert hits[0]["measurements"]["atoms"] == ["CTR","O"]
    assert hits[0]["measurements"]["source_stereocentres"] == {"CTR":hand}
    with pytest.raises(PostMRPreparationError, match="aromatic bond"):
        _require_generic_parameterization({code: {"parameterized": False}}, effective,
            tmp_path/"ready_set.log", source_components=assess_dictionaries([source])["components"])
    assert not any(f["rule_id"]=="PLANE-02" for f in review["findings"])


@pytest.mark.parametrize("variant,hand", [("aromatic-bond","N"),("uncertain-order","R"),
    ("conflicting-aromatic-flags","S"), ("non-aromatic-bond","R")])
def test_aromatic_sugar_check_needs_local_handedness_and_an_unambiguous_aromatic_assignment(tmp_path, variant, hand):
    from nasolve.cif_doctor import compare_dictionaries
    source, effective = _source_plane_case(tmp_path, variant=variant, hand=hand)
    result = compare_dictionaries([source], [effective], compare_stereo_bonds=True)
    assert not any(f["code"] == "aromatic-bond-at-source-stereocentre" for f in result["findings"])


def test_loose_plane_is_reported_without_quarantining_the_generated_dictionary(tmp_path):
    from nasolve.cif_doctor import assess_dictionaries, compare_dictionaries
    source, effective = _source_plane_case(tmp_path, variant="weak-plane")
    report = compare_dictionaries([source], [effective], compare_stereo_planes=True)
    conflicts = [f for f in report["findings"] if f["code"] == "plane-through-source-stereocentre"]
    assert len(conflicts) == 1
    assert conflicts[0]["measurements"]["plane_as_tight_as_local_bonds"] is False
    _require_generic_parameterization({"XYZ": {"parameterized": False}}, effective,
        tmp_path / "ready_set.log", source_components=assess_dictionaries([source])["components"])


def test_compare_cli_shows_plane_finding_for_both_dictionary_inputs(tmp_path, capsys):
    from nasolve.cli import main
    source, effective = _source_plane_case(tmp_path)
    assert main(["cif-doctor", "compare", str(source), str(effective)]) == 2
    assert "Plane p restrains source tetrahedral CTR" in capsys.readouterr().out


def test_conflicting_sources_are_not_used_to_call_a_tetrahedral_plane(tmp_path):
    from nasolve.cif_doctor import compare_dictionaries
    source, effective = _source_plane_case(tmp_path / "first", hand="R")
    other, _ = _source_plane_case(tmp_path / "second", hand="S")
    report = compare_dictionaries([source, other], [effective], compare_stereo_planes=True)
    assert "ambiguous-comparison-definition" in {f["code"] for f in report["findings"]}
    assert all(f["code"] != "plane-through-source-stereocentre" for f in report["findings"])
