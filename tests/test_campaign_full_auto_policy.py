"""Pure policy/diagnostic checks, independently runnable without native tools."""
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from nasolve.campaign_policy import (
    workflow_policy, default_endpoint, continuation_warning,
    record_runtime_policy, select_provisional_recommendation,
)
from nasolve.anomalous_expectations import audit_iodine_targets, iodine_refinement_audit

FULL = {"schema_version": 2, "id": "test", "version": "1",
        "workflow": {"mode": "full-auto"},
        "autosol": {"policy": "when-anomalous", "on_unaccepted": "continue-without-phases"}}


def test_legacy_recipe_is_not_promoted():
    old = {"schema_version": 1}
    assert default_endpoint(old) == "autorefine"
    assert workflow_policy(old)["select_recommendation"] is False
    assert continuation_warning(old, "phaser", {"status": "MR_REVIEW", "tfz": 7.6}) is None
    assert "workflow" not in old


def test_full_auto_defaults_and_explicit_doctor_omission():
    assert default_endpoint(FULL) == "refine-doctor"
    assert workflow_policy(FULL)["select_recommendation"] is True
    off = {**FULL, "workflow": {"mode": "full-auto", "run_doctor": False}}
    assert default_endpoint(off) == "autorefine"
    assert workflow_policy(off)["select_recommendation"] is False


@pytest.mark.parametrize("value", [
    {"schema_version": 1, "workflow": {"mode": "full-auto"}},
    {"schema_version": True}, {"schema_version": 3},
    {"schema_version": 2, "workflow": "full-auto"},
    {"schema_version": 2, "workflow": {"mode": []}},
    {"schema_version": 2, "workflow": {"mode": "magic"}},
    {"schema_version": 2, "workflow": {"command": "anything"}},
    {"schema_version": 2, "workflow": {"run_doctor": "true"}},
    {"schema_version": 2, "workflow": {"select_recommendation": 1}},
    {"schema_version": 2, "workflow": {"mode": "guarded", "select_recommendation": True}},
    {"schema_version": 2, "workflow": {"mode": "full-auto", "run_doctor": False, "select_recommendation": True}},
])
def test_invalid_or_unversioned_permission_is_rejected(value):
    with pytest.raises(ValueError):
        workflow_policy(value)


@pytest.mark.parametrize("tfz", [None, True, "7.6", float("nan"), float("inf"), 6.9, 8.0])
def test_review_trial_requires_finite_existing_borderline_band(tfz):
    assert continuation_warning(FULL, "phaser", {"status": "MR_REVIEW", "tfz": tfz}) is None


@pytest.mark.parametrize("tfz", [7.0, 7.6, 7.99])
def test_mr_review_is_trialled_without_changing_its_status(tfz):
    receipt = {"status": "MR_REVIEW", "tfz": tfz}
    assert "trial" in continuation_warning(FULL, "phaser", receipt)
    assert receipt == {"status": "MR_REVIEW", "tfz": tfz}


@pytest.mark.parametrize("status", ["MR_FAILED", "BLOCKED", "MR_SUCCESS"])
def test_failed_mr_is_not_relabeled(status):
    assert continuation_warning(FULL, "phaser", {"status": status, "tfz": 7.6}) is None


@pytest.mark.parametrize("status", ["AUTOSOL_WARNING", "AUTOSOL_REVIEW"])
def test_phase_fallback_is_explicit_and_does_not_import_phases(status):
    assert "without rejected phases" in continuation_warning(FULL, "autosol", {"status": status})
    inspect = {**FULL, "autosol": {"policy": "when-anomalous", "on_unaccepted": "inspect"}}
    assert continuation_warning(inspect, "autosol", {"status": status}) is None
    assert continuation_warning(FULL, "autosol", {"status": "BLOCKED"}) is None


def test_run_warning_survives_subsequent_stages_and_never_approves(tmp_path):
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"workflow": "automr", "status": "MR_REVIEW", "inputs": {"unchanged": 1}}))
    record_runtime_policy(tmp_path, FULL, "phaser", {"status": "MR_REVIEW", "tfz": 7.6})
    after = json.loads(path.read_text())
    assert after["status"] == "MR_REVIEW"
    assert after["inputs"] == {"unchanged": 1}
    first = after["campaign_automation"]["warnings"]
    record_runtime_policy(tmp_path, FULL, "autorefine", {"status": "AUTOREFINE_READY", "checkpoint": "refine-001"})
    final = json.loads(path.read_text())["campaign_automation"]
    assert final["warnings"] == first
    assert final["presented_checkpoint"] == "refine-001"
    assert final["user_approved"] is False


def test_guarded_policy_does_not_rewrite_report(tmp_path):
    path = tmp_path / "report.json"; path.write_bytes(b"not read by guarded path")
    assert record_runtime_policy(tmp_path, {"schema_version": 1}, "phaser", {}) is None
    assert path.read_bytes() == b"not read by guarded path"


def checkpoint_module(monkeypatch, *, status="SUCCESS", usable=True, corrupt=False):
    module = ModuleType("nasolve.checkpoints")
    registry = {"current": "postmr"}
    calls = []
    module.initialize_registry = lambda run: (run, registry)
    module.resolve_checkpoint = lambda reg, name: {"id": name, "status": status, "usable": usable}
    def verify(item, run):
        if corrupt:
            raise ValueError("checksum changed")
        calls.append("verified")
    module.inherited_paths = verify
    def select(run, name):
        calls.append("selected"); registry["current"] = name
        return SimpleNamespace(checkpoint_id=name)
    module.select_checkpoint = select
    monkeypatch.setitem(sys.modules, "nasolve.checkpoints", module)
    return registry, calls


def recommendation(status="REFINE_DOCTOR_RECOMMEND"):
    return SimpleNamespace(status=status, recommended_checkpoint="refine-002", source_checkpoint="refine-001",
                           recommendation="first eligible bounded candidate", current_checkpoint_preserved=True)


def test_only_verified_successful_recommendation_becomes_provisional_current(monkeypatch, tmp_path):
    registry, calls = checkpoint_module(monkeypatch)
    choice = select_provisional_recommendation(tmp_path, recommendation(), FULL)
    assert calls == ["verified", "selected"]
    assert registry["current"] == "refine-002"
    assert choice["previous_current"] == "postmr"
    assert choice["user_approved"] is False
    assert choice["core_doctor_preserved_current"] is True


@pytest.mark.parametrize("status", ["REFINE_DOCTOR_REVIEW", "REFINE_DOCTOR_FLAG_REPAIR_REQUIRED", "REFINE_DOCTOR_GOOD_ENOUGH"])
def test_unresolved_doctor_results_are_presented_not_auto_selected(monkeypatch, tmp_path, status):
    registry, calls = checkpoint_module(monkeypatch)
    assert select_provisional_recommendation(tmp_path, recommendation(status), FULL) is None
    assert registry["current"] == "postmr" and calls == []


@pytest.mark.parametrize("options", [{"status": "REVIEW"}, {"usable": False}, {"corrupt": True}])
def test_invalid_recommendation_cannot_move_current(monkeypatch, tmp_path, options):
    registry, calls = checkpoint_module(monkeypatch, **options)
    with pytest.raises(ValueError):
        select_provisional_recommendation(tmp_path, recommendation(), FULL)
    assert registry["current"] == "postmr"
    assert "selected" not in calls


def test_guarded_recommendation_and_opt_out_preserve_current(monkeypatch, tmp_path):
    registry, calls = checkpoint_module(monkeypatch)
    for policy in ({"schema_version": 1}, {**FULL, "workflow": {"mode": "full-auto", "select_recommendation": False}}):
        assert select_provisional_recommendation(tmp_path, recommendation(), policy) is None
    assert registry["current"] == "postmr" and calls == []


def atom(name, code="5IU", element="C"):
    return f"HETATM{1:5d} {name:>4s} {code:>3s} B{4:4d}    {0:8.3f}{0:8.3f}{0:8.3f}{1:6.2f}{20:6.2f}          {element:>2s}\n"


def test_diu_iodine_candidate_is_exact_and_not_phasing_evidence(tmp_path):
    model = tmp_path / "m.pdb"
    model.write_text(atom("C1'") + atom("C3'") + atom("I5", element="I"))
    audit = audit_iodine_targets(model, [{"site": "B:4", "atom_name": "I5", "element": "I"}])
    assert audit["expected_atoms"][0]["status"] == "CANDIDATE_READY"
    assert audit["warnings"] == []
    assert "NOT_ESTABLISHED" in audit["phase_or_anomalous_data_availability"]


@pytest.mark.parametrize("include,element,registered", [(False,"I",False), (True,"C",False), (True,"I",False)])
def test_missing_wrong_or_unregistered_iodine_is_flagged(tmp_path, include, element, registered):
    model = tmp_path / "m.pdb"
    model.write_text(atom("C1'") + (atom("I5", element=element) if include else ""))
    audit = audit_iodine_targets(model, [])
    assert len(audit["warnings"]) == 1


def test_anomalous_refinement_and_experimental_phases_are_distinct():
    report = {"postmr": {"anomalous": {"candidates": [{"element":"I", "site":"B:4", "atom_name":"I5"}]}},
              "autosol": {"status": "AUTOSOL_WARNING", "use_for_refinement": False}}
    audit = iodine_refinement_audit(report, {"refinement": {"anomalous": True, "use_experimental_phases": False}})
    assert audit["anomalous_refinement"] is True
    assert audit["experimental_phases_used"] is False
    assert audit["warnings"] == []
    off = iodine_refinement_audit(report, {"refinement": {"anomalous": False}})
    assert len(off["warnings"]) == 1
