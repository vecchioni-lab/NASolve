"""Read-only structural invariants; these tests do not execute Phenix."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from nasolve.cif_doctor import assess_dictionaries, compare_dictionaries
from nasolve.ligand_profiles import _emit

ROOT = Path(__file__).parents[1]


def component(*, numeric=True, torsion=False):
    names = ["C5", "C5'", "O4'", "C1'"]
    rows = [(names[0], names[1]), (names[1], names[2]), (names[2], names[3])]
    values = {"data_": "comp_X", "_chem_comp.id": ["X"],
              "_chem_comp_atom.comp_id": ["X"] * 4,
              "_chem_comp_atom.atom_id": names,
              "_chem_comp_atom.type_symbol": ["C", "C", "O", "C"],
              "_chem_comp_bond.comp_id": ["X"] * 3,
              "_chem_comp_bond.atom_id_1": [row[0] for row in rows],
              "_chem_comp_bond.atom_id_2": [row[1] for row in rows],
              "_chem_comp_bond.value_order": ["SING"] * 3}
    if numeric:
        values.update({"_chem_comp_atom.type_energy": ["C", "C", "O", "C"],
                       "_chem_comp_bond.value_dist": ["1.5"] * 3,
                       "_chem_comp_bond.value_dist_esd": ["0.02"] * 3,
                       "_chem_comp_angle.comp_id": ["X"] * 2,
                       "_chem_comp_angle.atom_id_1": ["C5", "C5'"],
                       "_chem_comp_angle.atom_id_2": ["C5'", "O4'"],
                       "_chem_comp_angle.atom_id_3": ["O4'", "C1'"],
                       "_chem_comp_angle.value_angle": ["110"] * 2,
                       "_chem_comp_angle.value_angle_esd": ["2"] * 2})
    if torsion:
        values.update({"_chem_comp_tor.comp_id": ["X"], "_chem_comp_tor.id": ["alpha"],
                       **{"_chem_comp_tor.atom_id_" + str(i): [name]
                          for i, name in enumerate(names, 1)},
                       "_chem_comp_tor.value_angle": ["32"],
                       "_chem_comp_tor.value_angle_esd": ["5"],
                       "_chem_comp_tor.period": ["1"]})
    return values


def write(tmp_path, values, name="dictionary.cif"):
    path = tmp_path / name
    path.write_text(_emit(values))
    return path


def findings(report, code):
    return [finding for finding in report["findings"] if finding["code"] == code]


def test_valid_minimal_numerical_graph_has_scoped_pass_and_no_writes(tmp_path):
    path = write(tmp_path, component())
    before = path.read_bytes()
    report = assess_dictionaries([path], stage="effective")
    assert report["status"] == "PASS"
    assert report["components"][0]["verdicts"]["numerical"] == "PASS"
    assert report["components"][0]["verdicts"]["chemical_identity"] == "UNASSESSED"
    assert report["components"][0]["verdicts"]["native"] == "NOT_RUN"
    assert report["inputs"] == [{"input_index": 0, "name": path.name, "role": "dictionary",
                                 "sha256": hashlib.sha256(before).hexdigest(), "size": len(before)}]
    assert path.read_bytes() == before
    assert report["input_integrity"] == "UNCHANGED"
    assert report == assess_dictionaries([path], stage="effective")
    assert json.loads(json.dumps(report)) == report


def test_ccd_bond_order_is_not_a_numerical_target(tmp_path):
    path = write(tmp_path, component(numeric=False))
    source = assess_dictionaries([path], stage="postmr-source")
    assert source["status"] == "PASS"
    assert source["components"][0]["inventory"]["graph_only"]
    assert source["components"][0]["verdicts"]["numerical"] == "UNASSESSED"
    assert findings(source, "graph-only-source")[0]["status"] == "NOT_RUN"
    effective = assess_dictionaries([path], stage="postmr-effective")
    assert effective["status"] == "REVIEW"
    assert findings(effective, "incomplete-numerical-parameterization")


def test_exact_primes_are_preserved_without_merging_names(tmp_path):
    path = write(tmp_path, component(torsion=True))
    report = assess_dictionaries([path])
    assert report["status"] == "PASS"
    inventory = report["components"][0]["inventory"]
    assert [atom["atom_id"] for atom in inventory["atoms"]][:2] == ["C5", "C5'"]
    assert inventory["torsions"][0]["atoms"] == ["C5", "C5'", "O4'", "C1'"]


@pytest.mark.parametrize("defect", ["duplicate", "dangling", "selfbond", "duplicatebond"])
def test_corrupt_identity_is_invalid_without_mutating_source(tmp_path, defect):
    values = component()
    if defect == "duplicate":
        values["_chem_comp_atom.atom_id"][1] = "C5"
    elif defect == "dangling":
        values["_chem_comp_bond.atom_id_2"][1] = "NO_ATOM"
    elif defect == "selfbond":
        values["_chem_comp_bond.atom_id_2"][0] = "C5"
    else:
        values["_chem_comp_bond.atom_id_1"][1] = "C5'"
        values["_chem_comp_bond.atom_id_2"][1] = "C5"
    path = write(tmp_path, values)
    before = path.read_bytes()
    assert assess_dictionaries([path])["status"] == "INVALID"
    assert path.read_bytes() == before


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "bad"])
def test_invalid_bond_esd_is_distinct_from_missing(tmp_path, value):
    values = component()
    values["_chem_comp_bond.value_dist_esd"][0] = value
    report = assess_dictionaries([write(tmp_path, values)])
    assert report["status"] == "INVALID"


@pytest.mark.parametrize("value", ["?", "."])
def test_missing_bond_esd_is_review_not_numeric_zero(tmp_path, value):
    values = component()
    values["_chem_comp_bond.value_dist_esd"][0] = value
    report = assess_dictionaries([write(tmp_path, values)], stage="effective")
    assert report["status"] == "REVIEW"
    assert not findings(report, "numeric-domain-violation")


def test_cif_numeric_standard_uncertainty_is_accepted_without_inventing_esd(tmp_path):
    values = component()
    values["_chem_comp_bond.value_dist"][0] = "1.50(2)"
    assert assess_dictionaries([write(tmp_path, values)])["status"] == "PASS"


def test_aromatic_kekule_orders_are_allowed_but_bridge_is_flagged(tmp_path):
    values = component()
    values["_chem_comp_bond.pdbx_aromatic_flag"] = ["Y", "N", "N"]
    path = write(tmp_path, values)
    report = assess_dictionaries([path])
    assert findings(report, "aromatic-bridge-bond")
    values["_chem_comp_bond.atom_id_1"].append("O4'")
    values["_chem_comp_bond.atom_id_2"].append("C5")
    for field, value in (("comp_id", "X"), ("value_order", "DOUB"),
                         ("value_dist", "1.4"), ("value_dist_esd", ".02"),
                         ("pdbx_aromatic_flag", "Y")):
        values["_chem_comp_bond." + field].append(value)
    report = assess_dictionaries([write(tmp_path, values, "cycle.cif")])
    assert not findings(report, "aromatic-bridge-bond")
    assert report["status"] == "PASS"


@pytest.mark.parametrize("kind,expected", [("proper", "INVALID"), ("improper", "PASS"), ("?", "REVIEW")])
def test_improper_does_not_need_a_bonded_quartet(tmp_path, kind, expected):
    values = component(torsion=True)
    values["_chem_comp_bond.atom_id_1"][2] = "C5'"
    values["_chem_comp_angle.atom_id_1"][1] = "O4'"
    values["_chem_comp_angle.atom_id_2"][1] = "C5'"
    values["_chem_comp_tor.type"] = [kind]
    report = assess_dictionaries([write(tmp_path, values)])
    assert report["status"] == expected


def test_const_name_alone_does_not_set_zero_weight(tmp_path):
    values = component(torsion=True)
    values["_chem_comp_tor.id"] = ["const_1"]
    values["_chem_comp_tor.value_angle_esd"] = ["-1"]
    path = write(tmp_path, values)
    assert assess_dictionaries([path])["status"] == "INVALID"
    values["_chem_comp_tor.value_angle_esd"] = ["0"]
    values["_chem_comp_tor.weight"] = ["0"]
    values["_chem_comp_tor.period"] = ["0"]
    report = assess_dictionaries([write(tmp_path, values, "constant.cif")])
    assert report["status"] == "PASS"
    assert report["components"][0]["inventory"]["torsions"][0]["activity"] == "constant"


def test_native_zero_sigma_and_signed_period_are_not_numeric_failures(tmp_path):
    values = component(torsion=True)
    values["_chem_comp_tor.value_angle_esd"] = ["0"]
    values["_chem_comp_tor.period"] = ["0"]
    report = assess_dictionaries([write(tmp_path, values)])
    assert report["status"] == "PASS"
    assert report["components"][0]["inventory"]["torsions"][0]["activity"] == "native-inactive-convention"
    values["_chem_comp_tor.value_angle_esd"] = ["5"]
    values["_chem_comp_tor.period"] = ["-3"]
    report = assess_dictionaries([write(tmp_path, values, "signed.cif")])
    assert report["status"] == "PASS"
    assert report["components"][0]["inventory"]["torsions"][0]["period"] == "-3"
    de = assess_dictionaries([ROOT / "src/nasolve/data/ligands/DE.cif"])
    assert de["status"] != "INVALID"
    assert sum(row["activity"] == "native-inactive-convention"
               for row in de["components"][0]["inventory"]["torsions"]) == 18


def test_absent_angle_category_does_not_claim_numerical_coverage(tmp_path):
    values = {key: value for key, value in component().items() if not key.startswith("_chem_comp_angle.")}
    report = assess_dictionaries([write(tmp_path, values)], stage="effective")
    assert report["status"] == "REVIEW"
    assert findings(report, "missing-angle-category")
    assert report["components"][0]["verdicts"]["numerical"] == "REVIEW"


def test_torsion_reversal_is_supported_but_permutation_and_different_periods_are_not(tmp_path):
    values = component(torsion=True)
    fields = [key for key in values if key.startswith("_chem_comp_tor.")]
    for field in fields:
        values[field] *= 2
    values["_chem_comp_tor.id"] = ["C2e-nyu0", "C3e-nyu0"]
    values["_chem_comp_tor.value_angle"] = ["340.7", "2.8"]
    values["_chem_comp_tor.value_angle_esd"] = ["6.3", "6.1"]
    names = [values["_chem_comp_tor.atom_id_" + str(i)][0] for i in range(1, 5)]
    for i, name in enumerate(reversed(names), 1):
        values["_chem_comp_tor.atom_id_" + str(i)][1] = name
    report = assess_dictionaries([write(tmp_path, values)])
    event = findings(report, "supported-torsion-alternates")[0]["measurements"]["compatibility_event"]
    assert event["source_uncertainties_differ"]
    assert event["effective_sigma"] == "6.3"
    values["_chem_comp_tor.period"][1] = "3"
    report = assess_dictionaries([write(tmp_path, values, "periods.cif")])
    assert findings(report, "competing-torsion-terms")
    values["_chem_comp_tor.period"][1] = "1"
    values["_chem_comp_tor.atom_id_2"][1], values["_chem_comp_tor.atom_id_3"][1] = (
        values["_chem_comp_tor.atom_id_3"][1], values["_chem_comp_tor.atom_id_2"][1])
    report = assess_dictionaries([write(tmp_path, values, "permuted.cif")])
    assert not findings(report, "supported-torsion-alternates")
    assert findings(report, "torsion-unbonded-path")


def planar(angles):
    names = ["O", "A", "B", "C"]
    return {"data_": "comp_X", "_chem_comp.id": ["X"],
            "_chem_comp_atom.comp_id": ["X"] * 4,
            "_chem_comp_atom.atom_id": names,
            "_chem_comp_atom.type_symbol": ["C"] * 4,
            "_chem_comp_atom.type_energy": ["C"] * 4,
            "_chem_comp_bond.comp_id": ["X"] * 3,
            "_chem_comp_bond.atom_id_1": ["O"] * 3,
            "_chem_comp_bond.atom_id_2": ["A", "B", "C"],
            "_chem_comp_bond.type": ["SINGLE"] * 3,
            "_chem_comp_bond.value_dist": ["1.5"] * 3,
            "_chem_comp_bond.value_dist_esd": [".02"] * 3,
            "_chem_comp_angle.comp_id": ["X"] * 3,
            "_chem_comp_angle.atom_id_1": ["A", "A", "B"],
            "_chem_comp_angle.atom_id_2": ["O"] * 3,
            "_chem_comp_angle.atom_id_3": ["B", "C", "C"],
            "_chem_comp_angle.value_angle": [str(angle) for angle in angles],
            "_chem_comp_angle.value_angle_esd": ["1.5"] * 3,
            "_chem_comp_plane_atom.comp_id": ["X"] * 4,
            "_chem_comp_plane_atom.plane_id": ["base"] * 4,
            "_chem_comp_plane_atom.atom_id": names,
            "_chem_comp_plane_atom.dist_esd": [".02"] * 4}


@pytest.mark.parametrize("angles", [(120, 120, 120), (30, 50, 80), (119.999, 120.000, 120.000)])
def test_valid_planar_interior_exterior_and_rounding_controls(tmp_path, angles):
    report = assess_dictionaries([write(tmp_path, planar(angles))])
    check = findings(report, "plane-angle-compatibility")[0]
    assert check["status"] == "PASS"
    assert check["measurements"]["rounded_planar_compatible"]
    assert report["status"] == "PASS"


def test_pyramidal_and_unrealizable_angle_targets_report_algebra_without_chemical_fix(tmp_path):
    report = assess_dictionaries([write(tmp_path, planar((109.471, 120.772, 109.471)))])
    check = findings(report, "plane-angle-compatibility")[0]
    assert check["status"] == "REVIEW"
    assert check["measurements"]["positive_semidefinite"]
    assert check["measurements"]["rank"] == 3
    assert check["measurements"]["determinant"] == pytest.approx(.40233, abs=1e-5)
    impossible = assess_dictionaries([write(tmp_path, planar((10, 10, 100)), "impossible.cif")])
    assert not findings(impossible, "plane-angle-compatibility")[0]["measurements"]["positive_semidefinite"]
    assert report["transformations"] == []


def test_packaged_known_cases_use_generic_rules(tmp_path):
    five_cm = ROOT / "src/nasolve/data/ligands/5CM.cif"
    before = five_cm.read_bytes()
    report = assess_dictionaries([five_cm])
    bad = findings(report, "torsion-unbonded-path")
    assert any(f["measurements"]["atoms"] == ["C4'", "O4'", "C1'", "C2"] for f in bad)
    assert five_cm.read_bytes() == before
    dp = assess_dictionaries([ROOT / "src/nasolve/data/ligands/DP.cif"])
    assert any(f["measurements"]["centre"] == "N5" and f["status"] == "REVIEW"
               for f in findings(dp, "plane-angle-compatibility"))
    assert assess_dictionaries([ROOT / "src/nasolve/data/ligands/DZ.cif"])["status"] == "PASS"


def test_signed_chirality_inventory_preserves_order_and_both_is_unassessed(tmp_path):
    values = planar((120, 120, 120))
    values.update({"_chem_comp_chir.comp_id": ["X"], "_chem_comp_chir.id": ["centre"],
                   "_chem_comp_chir.atom_id_centre": ["O"], "_chem_comp_chir.atom_id_1": ["A"],
                   "_chem_comp_chir.atom_id_2": ["C"], "_chem_comp_chir.atom_id_3": ["B"],
                   "_chem_comp_chir.volume_sign": ["both"]})
    report = assess_dictionaries([write(tmp_path, values)])
    stereo = report["components"][0]["inventory"]["chirality"][0]
    assert stereo["atoms"] == ["O", "A", "C", "B"]
    assert stereo["volume_sign"] == "both"
    assert stereo["absolute_stereochemistry"] == "UNASSESSED"


def test_unknown_charge_is_not_assigned_zero_or_changed_by_hydrogen_inventory(tmp_path):
    values = component(numeric=False)
    values["_chem_comp_atom.charge"] = ["?", "0", "-1", "."]
    values["_chem_comp_atom.partial_charge"] = [".12", ".24", "-.7", "0"]
    report = assess_dictionaries([write(tmp_path, values)], stage="source")
    atoms = report["components"][0]["inventory"]["atoms"]
    assert atoms[0]["declared_charge_fields"] == {"charge": "?", "partial_charge": ".12"}
    assert atoms[1]["declared_charge_fields"]["charge"] == "0"
    assert atoms[3]["declared_charge_fields"]["charge"] == "."


def test_multiple_identical_graphs_and_ancillary_mod_inputs_are_visible(tmp_path):
    first = write(tmp_path, component())
    second = write(tmp_path, component(), "second.cif")
    mod = tmp_path / "mod.cif"
    mod.write_text("data_mod_X\n_chem_mod.id X\n")
    phil = tmp_path / "pair.phil"
    phil.write_text("geometry_restraints.edits {}\n")
    report = assess_dictionaries([first, second, mod, phil])
    assert len(report["inputs"]) == 4
    assert findings(report, "multiple-component-definitions")[0]["measurements"]["identical_graphs"]
    assert findings(report, "noncomponent-block-not-interpreted")
    assert findings(report, "ancillary-not-interpreted")
    assert report["status"] == "PASS"


def test_different_same_code_graphs_are_ambiguity_not_winner_selection(tmp_path):
    first = write(tmp_path, component())
    values = component()
    values["_chem_comp_bond.value_order"][0] = "DOUB"
    second = write(tmp_path, values, "second.cif")
    report = assess_dictionaries([first, second])
    assert report["status"] == "REVIEW"
    assert not findings(report, "multiple-component-definitions")[0]["measurements"]["identical_graphs"]


@pytest.mark.parametrize("field,new", [("_chem_comp_bond.value_dist", "1.7"), ("_chem_comp_atom.charge", "1")])
def test_identical_graphs_with_different_targets_or_charge_are_ambiguous(tmp_path, field, new):
    values = component()
    if field not in values:
        values[field] = ["0"] * 4
    first = write(tmp_path, values)
    changed = deepcopy(values)
    changed[field][0] = new
    second = write(tmp_path, changed, "second.cif")
    report = assess_dictionaries([first, second], stage="effective")
    assert report["status"] == "REVIEW"
    ambiguity = findings(report, "multiple-component-definitions")[0]
    assert ambiguity["measurements"]["identical_graphs"]
    assert not ambiguity["measurements"]["identical_definitions"]


@pytest.mark.parametrize("kind", ["scalar", "loop"])
def test_duplicate_cif_tags_do_not_silently_discard_definitions(tmp_path, kind):
    text = _emit(component())
    if kind == "scalar":
        text = text.replace("data_comp_X\n", "data_comp_X\n_chem_comp.id WRONG\n")
    else:
        text += "\nloop_\n_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n_chem_comp_atom.type_symbol\nX LOST C\n"
    path = tmp_path / "duplicate.cif"
    path.write_text(text)
    report = assess_dictionaries([path])
    assert report["status"] == "INVALID"
    assert findings(report, "duplicate-cif-tags")


def test_quoted_and_semicolon_values_that_look_like_tags_are_not_duplicates(tmp_path):
    values = component()
    values["_chem_comp.name"] = ["_chem_comp.id"]
    values["_chem_comp.description"] = ["_chem_comp.id\n_chem_comp.id\n"]
    assert assess_dictionaries([write(tmp_path, values)])["status"] == "PASS"


def test_component_metadata_disagreement_is_not_silently_ignored(tmp_path):
    values = component()
    values["_chem_comp.id"] = ["WRONG"]
    report = assess_dictionaries([write(tmp_path, values)])
    assert report["status"] == "INVALID"
    assert findings(report, "component-identity-conflict")


def test_model_changed_during_assessment_is_caught(tmp_path, monkeypatch):
    import nasolve.cif_doctor as doctor
    path = write(tmp_path, component())
    model = tmp_path / "model.pdb"
    model.write_text("END\n")
    original = doctor._model_audit

    def change_after_read(*args):
        descriptor, model_findings = original(*args)
        model.write_text("REMARK changed\nEND\n")
        return descriptor, model_findings

    monkeypatch.setattr(doctor, "_model_audit", change_after_read)
    report = assess_dictionaries([path], model=model)
    assert report["status"] == "INVALID"
    assert report["input_integrity"] == "CHANGED_DURING_ASSESSMENT"
    assert findings(report, "model-changed-during-assessment")


def test_comparison_detects_source_changed_during_second_assessment(tmp_path, monkeypatch):
    import nasolve.cif_doctor as doctor
    first = write(tmp_path, component())
    second = write(tmp_path, component(), "effective.cif")
    original = doctor.assess_dictionaries
    count = 0

    def mutate_on_second(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            first.write_text(first.read_text() + "\n# external mutation\n")
        return original(*args, **kwargs)

    monkeypatch.setattr(doctor, "assess_dictionaries", mutate_on_second)
    report = doctor.compare_dictionaries([first], [second])
    assert report["status"] == "INVALID"
    assert report["input_integrity"] == "CHANGED_DURING_ASSESSMENT"
    assert findings(report, "comparison-input-changed")


def test_full_semantic_definition_hash_includes_component_group(tmp_path):
    values = component()
    values["_chem_comp.group"] = ["DNA"]
    first = write(tmp_path, values)
    values["_chem_comp.group"] = ["RNA"]
    second = write(tmp_path, values, "group.cif")
    report = assess_dictionaries([first, second])
    assert report["status"] == "REVIEW"
    ambiguity = findings(report, "multiple-component-definitions")[0]["measurements"]
    assert ambiguity["identical_graphs"]
    assert not ambiguity["identical_definitions"]


def test_component_restraints_without_atom_definitions_are_invalid(tmp_path):
    values = {key: value for key, value in component().items() if not key.startswith("_chem_comp_atom.")}
    report = assess_dictionaries([write(tmp_path, values)])
    assert report["status"] == "INVALID"
    assert findings(report, "restraints-without-atom-definition")


def test_provenance_records_exact_assessor_and_reader_versions(tmp_path):
    import nasolve.cif_doctor as doctor
    report = assess_dictionaries([write(tmp_path, component())])
    assert report["provenance"]["assessor_source_sha256"] == hashlib.sha256(Path(doctor.__file__).read_bytes()).hexdigest()
    assert {tool["name"] for tool in report["provenance"]["tools"]} == {"Python", "Biopython MMCIF2Dict"}
    assert report["provenance"]["installed_consumer_validation"] == "NOT_RUN"


def test_unscoped_atoms_are_not_duplicated_across_multiple_metadata_ids(tmp_path):
    values = component()
    values["_chem_comp.id"] = ["X", "Y"]
    for key in list(values):
        if key.endswith(".comp_id"):
            del values[key]
    report = assess_dictionaries([write(tmp_path, values)])
    assert report["status"] == "INVALID"
    assert findings(report, "ambiguous-unscoped-component-atoms")
    assert len(report["components"]) == 1


def test_same_identity_comparison_exposes_changes_without_choosing_chemistry(tmp_path):
    values = component()
    values["_chem_comp_atom.charge"] = ["?", "0", "0", "0"]
    values["_chem_comp_bond.pdbx_aromatic_flag"] = ["N"] * 3
    first = write(tmp_path, values)
    changed = deepcopy(values)
    changed["_chem_comp_bond.value_order"][0] = "DOUB"
    changed["_chem_comp_bond.pdbx_aromatic_flag"][0] = "Y"
    changed["_chem_comp_atom.charge"][0] = "0"
    second = write(tmp_path, changed, "effective.cif")
    report = compare_dictionaries([first], [second])
    assert report["status"] == "REVIEW"
    assert {difference["field"] for difference in report["differences"]} == {
        "bond_orders", "bond_aromatic_declarations", "declared_charge_fields"}
    charge = next(difference for difference in report["differences"] if difference["field"] == "declared_charge_fields")
    assert charge["source"]["C5"]["charge"] is None
    assert charge["effective"]["C5"]["charge"] == "0"
    assert report["source_assessment"]["inputs"][0]["sha256"]
    assert report["effective_assessment"]["inputs"][0]["sha256"]


def test_labels_are_not_alias_mapped_by_comparison(tmp_path):
    first = write(tmp_path, component())
    values = component()
    for key in values:
        if key == "_chem_comp.id" or key.endswith(".comp_id"):
            values[key] = ["DE" for value in values[key]]
    second = write(tmp_path, values, "different_identity.cif")
    report = compare_dictionaries([first], [second])
    assert report["status"] == "UNASSESSED"
    assert report["compared_components"] == []
    assert len(findings(report, "component-unpaired")) == 2


def test_chirality_comparison_accounts_for_neighbor_parity(tmp_path):
    values = planar((120, 120, 120))
    values.update({"_chem_comp_chir.comp_id": ["X"], "_chem_comp_chir.id": ["centre"],
                   "_chem_comp_chir.atom_id_centre": ["O"], "_chem_comp_chir.atom_id_1": ["A"],
                   "_chem_comp_chir.atom_id_2": ["B"], "_chem_comp_chir.atom_id_3": ["C"],
                   "_chem_comp_chir.volume_sign": ["positive"]})
    first = write(tmp_path, values)
    swapped = deepcopy(values)
    swapped["_chem_comp_chir.atom_id_1"] = ["B"]
    swapped["_chem_comp_chir.atom_id_2"] = ["A"]
    swapped["_chem_comp_chir.volume_sign"] = ["negative"]
    second = write(tmp_path, swapped, "swapped.cif")
    assert compare_dictionaries([first], [second])["status"] == "PASS"
    swapped["_chem_comp_chir.volume_sign"] = ["positive"]
    third = write(tmp_path, swapped, "inverted.cif")
    report = compare_dictionaries([first], [third])
    assert report["status"] == "REVIEW"
    assert {difference["field"] for difference in report["differences"]} == {"signed_chirality"}


def test_unreadable_and_malformed_cif_have_error_findings(tmp_path):
    missing = assess_dictionaries([tmp_path / "absent.cif"])
    assert missing["status"] == "INVALID"
    assert missing["inputs"][0]["sha256"] is None
    path = tmp_path / "broken.cif"
    path.write_text("not a CIF\n")
    invalid = assess_dictionaries([path])
    assert invalid["status"] == "INVALID"
    assert findings(invalid, "cif-parse-error")[0]["status"] == "ERROR"


def test_portable_descriptor_is_deterministic_after_relocation_original_gone(tmp_path):
    old = tmp_path / "old"
    old.mkdir()
    path = write(old, component())
    report = assess_dictionaries([path], stage="effective")
    new = tmp_path / "new"
    shutil.copytree(old, new)
    shutil.rmtree(old)
    moved = assess_dictionaries([new / path.name], stage="effective")
    assert moved == report
    assert str(tmp_path) not in json.dumps(moved)


def test_model_correspondence_retains_complete_pdb_site_identity(tmp_path):
    path = write(tmp_path, component())
    model = tmp_path / "model.pdb"
    model.write_text("MODEL        2\nHETATM    1  C5  X   A  12B      0.000   0.000   0.000  1.00 10.00           C\n"
                     "HETATM    2  C5' X   A  12B      0.000   0.000   0.000  1.00 10.00           C\nENDMDL\n")
    report = assess_dictionaries([path], model=model)
    site = report["model"]["component_sites"][0]
    assert {key: site[key] for key in ("model_id", "chain_id", "residue_id", "insertion_code", "component_id")} == {
        "model_id": "2", "chain_id": "A", "residue_id": "12", "insertion_code": "B", "component_id": "X"}
    assert site["atoms"] == [{"atom_id": "C5", "alternate_id": " "}, {"atom_id": "C5'", "alternate_id": " "}]
    assert report["status"] == "PASS"
    model.write_text(model.read_text().replace(" C5'", " BAD"))
    assert findings(assess_dictionaries([path], model=model), "model-dictionary-identity-mismatch")
