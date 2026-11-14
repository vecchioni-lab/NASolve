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
