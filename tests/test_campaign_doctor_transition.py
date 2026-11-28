"""Regression for an eligible REVIEW encountered inside one campaign run.

Reuse the existing real coordinator/worker/receipt fixtures. Scientific workers
in the first tests are controlled; the last test uses the actual stage engines
and checkpoint registry with fixture crystallographic executables.
"""
import json
from pathlib import Path

import pytest

from nasolve import campaign_execution as execution
from nasolve.campaign_records import STAGES, job_relative, read_record
from . import test_campaign_execution as coordinator_fixture
from . import test_campaign_pipeline as pipeline_fixture
from .test_autorefine import make_refine


@pytest.fixture
def campaign():
    case = coordinator_fixture.CampaignExecutionTests()
    try:
        case.setUp()
        yield case
    finally:
        case.doCleanups()


@pytest.mark.parametrize("doctor_status", [
    "REFINE_DOCTOR_RECOMMEND", "REFINE_DOCTOR_REVIEW",
    "REFINE_DOCTOR_FLAG_REPAIR_REQUIRED",
])
def test_fresh_review_enters_requested_doctor_in_same_invocation(campaign, doctor_status):
    campaign.outcomes[("A", "autorefine")] = "AUTOREFINE_REVIEW"
    campaign.outcomes[("A", "refine-doctor")] = doctor_status
    plan_path = campaign.root / "NASolveCampaign/plan.json"
    plan_bytes = plan_path.read_bytes()

    result = execution.execute_campaign(campaign.root, through="refine-doctor")
    assert campaign.calls == (
        [("A", stage) for stage in STAGES]
        + [("B", stage) for stage in STAGES if stage != "refine-doctor"]
    )
    a, b = (campaign.items(result)[name] for name in ("A", "B"))
    assert a["status"] == "AWAITING_INSPECTION"
    assert a["next_stage"] is None
    assert a["inspection_required"] and not a["numerical_success"]
    assert b["status"] == "SOLVED"
    assert plan_path.read_bytes() == plan_bytes

    auto = read_record(campaign.directory("A", "autorefine") / "result.json")
    doctor = read_record(campaign.directory("A", "refine-doctor") / "result.json")
    job = read_record(campaign.directory("A", "refine-doctor") / "job.json")
    assert auto["selected_as_current"] is False
    assert doctor["current_checkpoint_preserved"] is True
    assert doctor["source_checkpoint"] == auto["checkpoint"]
    assert job["dependencies"][-1]["receipt_sha256"] == auto["record_sha256"]
    assert len(job["dependencies"]) == 5
    assert doctor["run"] == auto["run"] == a["run"]

    # Completion is still a terminal inspection state; do not run Doctor twice.
    before_calls = list(campaign.calls)
    before_receipts = {
        p: p.read_bytes() for p in (campaign.root / "NASolveCampaign/execution").rglob("result.json")
    }
    execution.execute_campaign(campaign.root, through="refine-doctor")
    assert campaign.calls == before_calls
    assert all(p.read_bytes() == data for p, data in before_receipts.items())


def test_default_endpoint_still_requires_explicit_doctor_resume(campaign):
    campaign.outcomes[("A", "autorefine")] = "AUTOREFINE_REVIEW"
    first = execution.execute_campaign(campaign.root)
    a = campaign.items(first)["A"]
    assert a["status"] == "AWAITING_INSPECTION"
    assert a["next_stage"] == "refine-doctor"
    assert ("A", "refine-doctor") not in campaign.calls
    prior = list(campaign.calls)
    execution.execute_campaign(campaign.root)
    assert campaign.calls == prior
    execution.execute_campaign(campaign.root, datasets=("A",), through="refine-doctor")
    assert campaign.calls == [*prior, ("A", "refine-doctor")]


@pytest.mark.parametrize("stage,outcome,expected", [
    ("phaser", "MR_REVIEW", "AWAITING_INSPECTION"),
    ("phaser", "MR_FAILED", "NO_SOLUTION"),
    ("postmr", "BLOCKED", "BLOCKED"),
    ("autosol", "AUTOSOL_REVIEW", "AWAITING_INSPECTION"),
    ("autosol", "AUTOSOL_WARNING", "AWAITING_INSPECTION"),
    ("autorefine", "AUTOREFINE_FAILED", "BLOCKED"),
])
def test_doctor_endpoint_does_not_bypass_other_stops(campaign, stage, outcome, expected):
    campaign.outcomes[("A", stage)] = outcome
    result = execution.execute_campaign(campaign.root, through="refine-doctor")
    assert campaign.items(result)["A"]["status"] == expected
    assert campaign.items(result)["B"]["status"] == "SOLVED"
    assert ("A", "refine-doctor") not in campaign.calls
    assert ("B", "refine-doctor") not in campaign.calls
    assert [s for name, s in campaign.calls if name == "A"] == list(STAGES[:STAGES.index(stage) + 1])


def test_pause_at_review_boundary_is_honored_before_doctor(campaign):
    campaign.outcomes[("A", "autorefine")] = "AUTOREFINE_REVIEW"
    campaign.after_stage = lambda name, stage: (
        execution.request_pause(campaign.root)
        if (name, stage) == ("A", "autorefine") else None
    )
    result = execution.execute_campaign(campaign.root, datasets=("A",), through="refine-doctor")
    assert result["execution"]["state"] == "PAUSED"
    assert campaign.items(result)["A"]["next_stage"] == "refine-doctor"
    assert ("A", "refine-doctor") not in campaign.calls
    before = list(campaign.calls)
    campaign.after_stage = None
    execution.execute_campaign(campaign.root, datasets=("A",), through="refine-doctor")
    assert campaign.calls == [*before, ("A", "refine-doctor")]


def test_report_drift_at_review_boundary_still_blocks_doctor(campaign, monkeypatch):
    campaign.outcomes[("A", "autorefine")] = "AUTOREFINE_REVIEW"

    def after_worker(path, **callbacks):
        code = campaign.run_job(path, **callbacks)
        job = read_record(path)
        if (job["dataset"], job["stage"]) == ("A", "autorefine"):
            receipt = read_record(path.parent / "result.json")
            (campaign.root / receipt["run"] / "report.json").write_text('{"outside":"edit"}\n')
        return code

    monkeypatch.setattr(execution, "run_job", after_worker)
    result = execution.execute_campaign(campaign.root, through="refine-doctor")
    a = campaign.items(result)["A"]
    assert a["status"] == "BLOCKED"
    assert "Run report changed" in a["diagnostic"]
    assert ("A", "refine-doctor") not in campaign.calls
    assert campaign.items(result)["B"]["status"] == "SOLVED"


def test_selected_fresh_doctor_does_not_rerun_solved_member(campaign):
    first = execution.execute_campaign(campaign.root, datasets=("B",))
    b_run = campaign.root / campaign.items(first)["B"]["run"]
    before = {p: p.read_bytes() for p in b_run.rglob("*") if p.is_file()}
    campaign.calls.clear()
    campaign.outcomes[("A", "autorefine")] = "AUTOREFINE_REVIEW"
    result = execution.execute_campaign(campaign.root, datasets=("A",), through="refine-doctor")
    assert campaign.calls == [("A", stage) for stage in STAGES]
    assert all(p.read_bytes() == content for p, content in before.items())
    assert campaign.items(result)["B"]["status"] == "SOLVED"


def test_same_invocation_real_stage_engines_preserve_current_and_observations(monkeypatch):
    case = pipeline_fixture.CampaignPipelineTests()
    try:
        case.setUp()
        from nasolve import campaign_stages
        from nasolve.checkpoints import initialize_registry

        # First refinement returns REVIEW. Only the fixture executable changes
        # on entry to Doctor so its bounded trial can return a recommendation.
        make_refine(case.tools, final_work=0.17, final_free=0.16)
        real_doctor = campaign_stages.execute_refine_doctor

        def doctor(*args, **kwargs):
            make_refine(case.tools, final_work=0.15, final_free=0.20)
            return real_doctor(*args, **kwargs)

        monkeypatch.setattr(campaign_stages, "execute_refine_doctor", doctor)
        data = case.root / "dataset/staraniso-alldata.mtz"
        input_bytes = data.read_bytes()
        result = execution.execute_campaign(case.root, through="refine-doctor")
        item = result["execution"]["datasets"][0]
        assert case.jobs == list(STAGES), item["diagnostic"]
        assert item["status"] == "AWAITING_INSPECTION", item["diagnostic"]
        assert item["next_stage"] is None
        run = case.root / item["run"]
        _, registry = initialize_registry(run)
        assert registry["current"] == "postmr"
        receipt = read_record(case.root / job_relative("dataset", 1, "refine-doctor") / "result.json")
        assert receipt["status"] == "REFINE_DOCTOR_RECOMMEND"
        assert receipt["current_checkpoint_preserved"] is True
        assert receipt["recommended_checkpoint"] == "refine-002"
        assert data.read_bytes() == input_bytes
        assert (case.root / "NASolveCampaign/plan.json").read_bytes() == case.plan_bytes
        before = list(case.jobs)
        execution.execute_campaign(case.root, through="refine-doctor")
        assert case.jobs == before
    finally:
        case.doCleanups()
