"""Phase-use reporting must describe this refinement, not a default option."""
from copy import deepcopy

import pytest

from nasolve.anomalous_expectations import iodine_refinement_audit

HL = ["HLAM", "HLBM", "HLCM", "HLDM"]


def refinement_report(option=True, file=None, labels=None, anomalous=False):
    return {
        "refinement": {
            "use_experimental_phases": option,
            "anomalous": anomalous,
        },
        "inputs": {
            "phase_file": file,
            "phase_labels": [] if labels is None else labels,
            "observation_labels": ["IMEAN", "SIGIMEAN"],
        },
    }


@pytest.mark.parametrize("name,option,file,labels,anomalous,used", [
    ("DiU", True, "overall_best_refine_data.mtz", HL, True, True),
    ("EA", True, None, [], False, False),
    ("Q5cm", True, None, [], False, False),
    ("QiC/refine-002", False, None, [], True, False),
])
def test_returned_live_report_field_combinations(name, option, file, labels, anomalous, used):
    # Synthetic reports reproduce Simon's returned fields; no native rerun.
    report = refinement_report(option, file, labels, anomalous)
    audit = iodine_refinement_audit({}, report)
    assert audit["experimental_phases_used"] is used, name
    assert audit["experimental_phases_requested"] is option
    assert audit["anomalous_refinement"] is anomalous
    assert audit["phase_usage_basis"] == "reported-refinement-inputs-v1"


@pytest.mark.parametrize("file,labels", [
    (None, HL), ("", HL), ("  ", HL), (False, HL), (12, HL),
    ("phases.mtz", []), ("phases.mtz", HL[:3]),
    ("phases.mtz", HL + ["EXTRA"]),
    ("phases.mtz", ["HLAM", "HLBM", "HLCM", "HLCM"]),
    ("phases.mtz", ["HLAM", "HLBM", "HLCM", " "]),
    ("phases.mtz", ["HLAM", "HLBM", "HLCM", None]),
    ("phases.mtz", ",".join(HL)),
])
def test_option_alone_or_incomplete_reported_inputs_do_not_assert_use(file, labels):
    audit = iodine_refinement_audit({}, refinement_report(True, file, labels))
    assert audit["experimental_phases_requested"] is True
    assert audit["experimental_phase_inputs_present"] is False
    assert audit["experimental_phases_used"] is False
    # Missing optional phase inputs are not a new scientific stop or warning.
    assert audit["warnings"] == []


@pytest.mark.parametrize("option", [False, None, "true", 1])
def test_inputs_without_explicit_boolean_permission_do_not_assert_use(option):
    audit = iodine_refinement_audit({}, refinement_report(option, "phases.mtz", HL))
    assert audit["experimental_phase_inputs_present"] is True
    assert audit["experimental_phases_requested"] is False
    assert audit["experimental_phases_used"] is False


@pytest.mark.parametrize("labels", [HL, ["HLA", "HLB", "HLC", "HLD"],
                                    ["HL_A", "HL_B", "HL_C", "HL_D"]])
def test_complete_reported_quartets_are_supported_without_reopening_data(tmp_path, labels):
    # Historical absolute paths can be absent after relocation. This reporting
    # layer must not redo file/chemistry/integrity checks or mutate old receipts.
    missing = tmp_path / "gone" / "phases.mtz"
    audit = iodine_refinement_audit({}, refinement_report(True, str(missing), labels))
    assert not missing.exists()
    assert audit["experimental_phases_used"] is True
    assert audit["phase_labels"] == labels
    assert audit["phase_file"] == str(missing)


def test_autosol_acceptance_and_parent_settings_are_not_branch_phase_evidence():
    run = {
        "autosol": {"status": "AUTOSOL_READY", "use_for_refinement": True},
        "autorefine": refinement_report(True, "parent_phases.mtz", HL, True),
    }
    branch = refinement_report(False, None, [], True)
    audit = iodine_refinement_audit(run, branch)
    assert audit["autosol_status"] == "AUTOSOL_READY"
    assert audit["anomalous_refinement"] is True
    assert audit["experimental_phases_used"] is False


def test_input_reports_are_unchanged_and_audit_label_list_is_independent():
    run = {"autosol": {"status": "AUTOSOL_READY"}}
    report = refinement_report(True, "phases.mtz", list(HL), True)
    original = deepcopy((run, report))
    audit = iodine_refinement_audit(run, report)
    assert (run, report) == original
    audit["phase_labels"].append("not-source-data")
    assert (run, report) == original


def test_missing_legacy_inputs_do_not_turn_permission_into_proof():
    report = {"refinement": {"use_experimental_phases": True}}
    audit = iodine_refinement_audit({}, report)
    assert audit["experimental_phases_requested"] is True
    assert audit["experimental_phases_used"] is False
    assert audit["phase_file"] is None
    assert audit["phase_labels"] == []


def test_anomalous_and_phase_axes_remain_independent():
    report = refinement_report(True, "phases.mtz", HL, False)
    run = {"postmr": {"anomalous": {"candidates": [
        {"element": "I", "site": "B:4", "atom_name": "I5"},
    ]}}}
    audit = iodine_refinement_audit(run, report)
    assert audit["experimental_phases_used"] is True
    assert audit["anomalous_refinement"] is False
    assert len(audit["warnings"]) == 1
