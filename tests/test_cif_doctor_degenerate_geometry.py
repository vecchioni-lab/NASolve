"""Supplier-coordinate degeneracy is a general, read-only numerical check."""
import hashlib
import json

import pytest

from nasolve.cif_doctor import assess_dictionaries
from nasolve.ligand_profiles import _emit


def _component(*, code="QXZ", numerical=True, coordinate_set="atom_xyz"):
    names = ["C5", "C5'", "N3", "H1"]
    values = {"data_": "comp_" + code,
              "_chem_comp.id": [code],
              "_chem_comp_atom.comp_id": [code] * 4,
              "_chem_comp_atom.atom_id": names,
              "_chem_comp_atom.type_symbol": ["C", "C", "N", "H"],
              "_chem_comp_bond.comp_id": [code] * 3,
              "_chem_comp_bond.atom_id_1": ["C5", "C5'", "N3"],
              "_chem_comp_bond.atom_id_2": ["C5'", "N3", "H1"],
              "_chem_comp_bond.value_order": ["SING"] * 3}
    if numerical:
        values.update({"_chem_comp_atom.type_energy": ["C", "C", "N", "H"],
                       "_chem_comp_bond.value_dist": ["1.50", "1.40", "1.00"],
                       "_chem_comp_bond.value_dist_esd": ["0.02"] * 3,
                       "_chem_comp_angle.comp_id": [code] * 2,
                       "_chem_comp_angle.atom_id_1": ["C5", "C5'"],
                       "_chem_comp_angle.atom_id_2": ["C5'", "N3"],
                       "_chem_comp_angle.atom_id_3": ["N3", "H1"],
                       "_chem_comp_angle.value_angle": ["110", "110"],
                       "_chem_comp_angle.value_angle_esd": ["2", "2"]})
    if coordinate_set:
        fields = ("x", "y", "z") if coordinate_set == "atom_xyz" else tuple(
            "pdbx_model_Cartn_" + axis + "_ideal" for axis in "xyz")
        for field, data in zip(fields, (["0", "1.5", "1.5", "2.5"],
                                       ["0"] * 4, ["0"] * 4)):
            values["_chem_comp_atom." + field] = data
    return values


def _audit(tmp_path, values, *, stage="postmr-effective"):
    path = tmp_path / "supplier.cif"
    path.write_text(_emit(values), encoding="utf-8")
    before = path.read_bytes()
    report = assess_dictionaries([path], stage=stage)
    assert path.read_bytes() == before
    assert report["input_integrity"] == "UNCHANGED"
    assert report["inputs"][0]["sha256"] == hashlib.sha256(before).hexdigest()
    assert json.loads(json.dumps(report)) == report
    return report


def _findings(report, code):
    return [finding for finding in report["findings"] if finding["code"] == code]


@pytest.mark.parametrize("code", ["QXZ", "OTHER", "IGU_RENAMED"])
@pytest.mark.parametrize("coordinate_set", ["atom_xyz", "supplier_ideal"])
@pytest.mark.parametrize("distance", ["0.000", "1.400"])
def test_exact_collision_invalidates_whole_numerical_component_even_with_positive_target(
        tmp_path, code, coordinate_set, distance):
    values = _component(code=code, coordinate_set=coordinate_set)
    values["_chem_comp_bond.value_dist"][1] = distance
    report = _audit(tmp_path, values)
    assert report["status"] == "INVALID"
    component = report["components"][0]
    assert component["component_id"] == code
    assert component["verdicts"]["graph"] == "PASS"
    assert component["verdicts"]["numerical"] == "INVALID"
    assert component["verdicts"]["dictionary_geometry"] == "INVALID"
    assert component["verdicts"]["geometry"] == "NOT_RUN"
    assert component["verdicts"]["chemical_identity"] == "UNASSESSED"
    collision, = _findings(report, "coincident-bonded-heavy-atoms")
    assert collision["component_id"] == code
    assert collision["rule_id"] == "NUM-01"
    assert collision["status"] == "FAIL"
    details = collision["measurements"]
    assert details["atoms"] == ["C5'", "N3"]
    assert details["row"] == 1
    assert details["coordinate_set"] == coordinate_set
    assert details["coordinates"] == [1.5, 0.0, 0.0]
    assert details["comparison"] == "exact-coordinate-equality"
    assert details["distance"] == 0.0
    if distance == "0.000":
        numeric, = _findings(report, "numeric-domain-violation")
        assert numeric["measurements"]["atoms"] == ["C5'", "N3"]


@pytest.mark.parametrize("target", ["nan", "bad", "0", "-1"])
def test_numerical_bond_failure_identifies_exact_atoms_without_coordinates(tmp_path, target):
    values = _component(coordinate_set=None)
    values["_chem_comp_bond.value_dist"][1] = target
    report = _audit(tmp_path, values)
    assert report["status"] == "INVALID"
    failures = [finding for finding in report["findings"]
                if finding["code"] in {"invalid-numeric-value", "numeric-domain-violation"}]
    assert len(failures) == 1
    assert failures[0]["measurements"]["atoms"] == ["C5'", "N3"]
    assert failures[0]["measurements"]["field"] == "value_dist"
    assert report["components"][0]["verdicts"]["dictionary_geometry"] == "UNASSESSED"


@pytest.mark.parametrize("coordinate_set", ["atom_xyz", "supplier_ideal"])
def test_graph_only_source_placeholder_coordinates_remain_unassessed(tmp_path, coordinate_set):
    report = _audit(tmp_path, _component(numerical=False, coordinate_set=coordinate_set),
                    stage="postmr-source")
    assert report["status"] == "PASS"
    assert report["components"][0]["inventory"]["graph_only"]
    assert report["components"][0]["verdicts"]["numerical"] == "UNASSESSED"
    assert report["components"][0]["verdicts"]["dictionary_geometry"] == "UNASSESSED"
    assert not _findings(report, "coincident-bonded-heavy-atoms")


@pytest.mark.parametrize("coordinate_set", ["atom_xyz", "supplier_ideal"])
def test_graph_only_effective_candidate_is_review_not_coordinate_failure(tmp_path, coordinate_set):
    report = _audit(tmp_path, _component(numerical=False, coordinate_set=coordinate_set))
    assert report["status"] == "REVIEW"
    assert not _findings(report, "coincident-bonded-heavy-atoms")


def test_energy_labels_without_numerical_bond_targets_do_not_promote_placeholder_coordinates(tmp_path):
    values = _component(numerical=False)
    values["_chem_comp_atom.type_energy"] = ["C", "C", "N", "H"]
    report = _audit(tmp_path, values, stage="postmr-source")
    assert report["status"] == "REVIEW"
    assert report["components"][0]["verdicts"]["dictionary_geometry"] == "UNASSESSED"
    assert not _findings(report, "coincident-bonded-heavy-atoms")


def test_coordinate_scan_has_an_explicit_component_size_bound(tmp_path):
    values = _component()
    for key, rows in values.items():
        if key.startswith("_chem_comp_atom."):
            rows.extend([rows[-1]] * (10001 - len(rows)))
    values["_chem_comp_atom.atom_id"][4:] = ["EXTRA" + str(index) for index in range(9997)]
    report = _audit(tmp_path, values)
    assert report["status"] == "PASS"
    assert report["components"][0]["verdicts"]["dictionary_geometry"] == "UNASSESSED"
    bound, = _findings(report, "dictionary-coordinate-assessment-bounded")
    assert bound["measurements"]["atom_count"] == 10001
    assert not _findings(report, "coincident-bonded-heavy-atoms")


@pytest.mark.parametrize("defect", ["absent", "partial", "missing", "nonfinite", "unsupported"])
def test_unavailable_coordinate_triplets_are_explicitly_unassessed(tmp_path, defect):
    values = _component(coordinate_set=None if defect in {"absent", "unsupported"} else "atom_xyz")
    if defect == "partial":
        values.pop("_chem_comp_atom.z")
    elif defect == "missing":
        values["_chem_comp_atom.z"][0] = "?"
    elif defect == "nonfinite":
        values["_chem_comp_atom.x"][0] = "nan"
    elif defect == "unsupported":
        values["_chem_comp_atom.model_Cartn_x"] = ["0"] * 4
        values["_chem_comp_atom.model_Cartn_y"] = ["0"] * 4
        values["_chem_comp_atom.model_Cartn_z"] = ["0"] * 4
    report = _audit(tmp_path, values)
    assert report["status"] == "PASS"
    assert report["components"][0]["verdicts"]["dictionary_geometry"] == "UNASSESSED"
    event, = _findings(report, "dictionary-coordinates-unassessed")
    assert event["status"] == ("NOT_RUN" if defect == "absent" else "UNSUPPORTED")
    assert not _findings(report, "coincident-bonded-heavy-atoms")


@pytest.mark.parametrize("element", ["H", "D"])
def test_hydrogen_coincidence_and_missing_hydrogen_coordinates_do_not_trigger_heavy_check(tmp_path, element):
    values = _component()
    values["_chem_comp_atom.x"][2] = "2.9"
    values["_chem_comp_atom.type_symbol"][3] = element
    values["_chem_comp_atom.x"][3] = "2.9"
    assert _audit(tmp_path, values)["status"] == "PASS"
    for axis in "xyz":
        values["_chem_comp_atom." + axis][3] = "?"
    report = _audit(tmp_path, values)
    assert report["status"] == "PASS"
    assert report["components"][0]["verdicts"]["dictionary_geometry"] == "PASS"


def test_nonbonded_coincidence_does_not_invent_a_bond(tmp_path):
    values = _component()
    values["_chem_comp_atom.x"][2] = "0"
    report = _audit(tmp_path, values)
    assert report["status"] == "PASS"
    assert not _findings(report, "coincident-bonded-heavy-atoms")


def test_canonical_numeric_equality_preserves_primes_and_has_no_rounding_threshold(tmp_path):
    values = _component()
    values["_chem_comp_atom.x"][1:3] = ["1.5000(2)", "15e-1"]
    assert _findings(_audit(tmp_path, values), "coincident-bonded-heavy-atoms")
    values["_chem_comp_atom.x"][1:3] = ["1.5000000000000001", "1.5000000000000002"]
    report = _audit(tmp_path, values)
    assert report["status"] == "PASS"
    assert not _findings(report, "coincident-bonded-heavy-atoms")


def test_decimal_underflow_does_not_create_false_exact_coincidence(tmp_path):
    values = _component()
    values["_chem_comp_atom.x"][1:3] = ["1e-400", "2e-400"]
    report = _audit(tmp_path, values)
    assert report["status"] == "PASS"
    assert not _findings(report, "coincident-bonded-heavy-atoms")


def test_both_explicit_coordinate_sets_are_assessed_without_silent_precedence(tmp_path):
    values = _component()
    for axis in "xyz":
        values["_chem_comp_atom.pdbx_model_Cartn_" + axis + "_ideal"] = ["0"] * 4
    report = _audit(tmp_path, values)
    collisions = _findings(report, "coincident-bonded-heavy-atoms")
    assert {finding["measurements"]["coordinate_set"] for finding in collisions} == {
        "atom_xyz", "supplier_ideal"}
    assert report["components"][0]["inventory"]["dictionary_geometry"]["checked_heavy_bonds"] == 4
