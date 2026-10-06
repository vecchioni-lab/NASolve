"""Full-checkout tests: real coordinator/receipts/stages, fixture native tools."""
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from nasolve.campaign_execution import execute_campaign, execution_status
from nasolve.campaign_records import job_relative, read_record
from nasolve.campaigns import plan_campaign
from nasolve.presets import load_preset, PresetError
from nasolve.checkpoints import initialize_registry, select_checkpoint
from .test_campaign_pipeline import CampaignPipelineTests
from .test_postmr import postmr_model_text
from .test_autorefine import make_refine

RECIPE = '''schema_version = 2
id = "full-auto-fixture"
version = "1"
[workflow]
mode = "full-auto"
'''


@pytest.fixture
def full_case(tmp_path):
    case = CampaignPipelineTests()
    try:
        case.setUp()
        # Test-owned plan only: production plans are never edited in place.
        shutil.rmtree(case.root / "NASolveCampaign")
        frames = case.base / "new-frames" / "5W6W"
        frames.mkdir(parents=True)
        (frames / "C_G.pdb").write_text(postmr_model_text("DC", "DG"))
        (frames / "seq_base.txt").write_text("C\n\nG\n")
        recipe = case.base / "recipe.txt"  # A text file containing typed TOML is accepted.
        recipe.write_text(RECIPE)
        case.plan = plan_campaign(case.root, preset=recipe, frames_directory=frames.parent)
        case.plan_bytes = (case.root / "NASolveCampaign/plan.json").read_bytes()
        case.test_recipe = recipe
        case.test_frames = frames
        yield case
    finally:
        case.doCleanups()


def receipt(case, stage):
    return read_record(case.root / job_relative("dataset", 1, stage) / "result.json")


def set_tfz(case, value):
    phaser = case.installation.executables["phenix.phaser"]
    phaser.write_text(phaser.read_text().replace("TFZ=14.3", f"TFZ={value}"))


def test_borderline_mr_continues_once_under_frozen_full_auto(full_case):
    case = full_case
    set_tfz(case, 7.6)
    source = case.root / "dataset/staraniso-alldata.mtz"
    before = source.read_bytes()
    result = execute_campaign(case.root)
    item = result["execution"]["datasets"][0]
    assert case.jobs == ["preflight", "phaser", "postmr", "autosol", "autorefine"], item["diagnostic"]
    assert item["status"] == "SOLVED", item["diagnostic"]
    assert item["provisional"] is True and item["inspection_required"] is True
    assert any("7.60" in value for value in item["scientific_warnings"])
    assert receipt(case, "phaser")["status"] == "MR_REVIEW"
    assert receipt(case, "phaser")["tfz"] == 7.6
    report = json.loads((case.root / item["run"] / "report.json").read_text())
    assert report["campaign_automation"]["user_approved"] is False
    assert any("MR REVIEW" in w for w in report["campaign_automation"]["warnings"])
    assert source.read_bytes() == before
    assert (case.root / "NASolveCampaign/plan.json").read_bytes() == case.plan_bytes
    jobs = list(case.jobs)
    execute_campaign(case.root)
    assert case.jobs == jobs


def test_full_auto_still_stops_failed_mr(full_case):
    set_tfz(full_case, 6.9)
    result = execute_campaign(full_case.root)
    assert result["execution"]["datasets"][0]["status"] == "NO_SOLUTION"
    assert full_case.jobs == ["preflight", "phaser"]


def test_explicit_endpoint_overrides_recipe(full_case):
    set_tfz(full_case, 7.6)
    result = execute_campaign(full_case.root, through="phaser")
    assert full_case.jobs == ["preflight", "phaser"]
    assert result["execution"]["datasets"][0]["next_stage"] == "postmr"


def test_guarded_recipe_retains_original_mr_stop():
    case = CampaignPipelineTests()
    try:
        case.setUp()
        set_tfz(case, 7.6)
        result = execute_campaign(case.root, through="refine-doctor")
        item = result["execution"]["datasets"][0]
        assert item["status"] == "AWAITING_INSPECTION"
        assert case.jobs == ["preflight", "phaser"]
        assert item["provisional"] is False
    finally:
        case.doCleanups()


def test_doctor_is_separately_auto_selected_and_user_veto_survives_resume(full_case, monkeypatch):
    from nasolve import campaign_stages
    case = full_case
    make_refine(case.tools, final_work=0.17, final_free=0.16)
    original = campaign_stages.execute_refine_doctor
    def doctor(*args, **kwargs):
        make_refine(case.tools, final_work=0.15, final_free=0.20)
        return original(*args, **kwargs)
    monkeypatch.setattr(campaign_stages, "execute_refine_doctor", doctor)
    result = execute_campaign(case.root)
    item = result["execution"]["datasets"][0]
    assert case.jobs == ["preflight", "phaser", "postmr", "autosol", "autorefine", "refine-doctor"], item["diagnostic"]
    assert item["status"] == "SOLVED", item["diagnostic"]
    run = case.root / item["run"]
    _, registry = initialize_registry(run)
    assert registry["current"] == "refine-002"
    chosen = next(v for v in registry["checkpoints"] if v["id"] == "refine-002")
    assert chosen["status"] == "SUCCESS", "Automatic selection must not write USER_APPROVED"
    result_receipt = receipt(case, "refine-doctor")
    assert result_receipt["doctor_current_checkpoint_preserved"] is True
    assert result_receipt["current_checkpoint_preserved"] is False
    assert result_receipt["provisional_selection"]["previous_current"] == "postmr"
    assert result_receipt["provisional_selection"]["user_approved"] is False
    jobs = list(case.jobs)
    select_checkpoint(run, "postmr")
    execute_campaign(case.root)
    assert case.jobs == jobs
    assert initialize_registry(run)[1]["current"] == "postmr"
    assert (case.root / "NASolveCampaign/plan.json").read_bytes() == case.plan_bytes


def replan(case, suffix):
    shutil.rmtree(case.root / "NASolveCampaign")
    case.test_recipe.write_text(RECIPE + suffix)
    plan_campaign(case.root, preset=case.test_recipe, frames_directory=case.test_frames.parent)


def test_selection_can_be_opted_out_without_disabling_doctor(full_case, monkeypatch):
    from nasolve import campaign_stages
    case = full_case
    replan(case, "select_recommendation = false\n")
    make_refine(case.tools, final_work=0.17, final_free=0.16)
    original = campaign_stages.execute_refine_doctor
    def doctor(*args, **kwargs):
        make_refine(case.tools, final_work=0.15, final_free=0.20)
        return original(*args, **kwargs)
    monkeypatch.setattr(campaign_stages, "execute_refine_doctor", doctor)
    item = execute_campaign(case.root)["execution"]["datasets"][0]
    assert item["checkpoint"] == "refine-002", item["diagnostic"]
    assert item["status"] == "AWAITING_INSPECTION"
    assert initialize_registry(case.root / item["run"])[1]["current"] == "postmr"
    assert receipt(case, "refine-doctor")["current_checkpoint_preserved"] is True


def test_recipe_source_mutation_is_not_silently_adopted(full_case):
    # The original human recipe is no longer the execution authority; the
    # content-addressed frozen copy and policy remain so.
    full_case.test_recipe.write_text("now broken")
    set_tfz(full_case, 7.6)
    item = execute_campaign(full_case.root)["execution"]["datasets"][0]
    assert item["status"] == "SOLVED", item["diagnostic"]
    assert any("7.60" in value for value in item["scientific_warnings"])


def test_phase_warning_can_continue_without_ever_importing_rejected_phases(full_case, monkeypatch):
    from nasolve import campaign_stages
    case = full_case
    # Exercise the AutoSol-to-refinement authorization using an explicit
    # fixture rejection; no fabricated phase file is supplied downstream.
    monkeypatch.setattr(campaign_stages, "_autosol_required", lambda report: True)
    case.installation.executables["phenix.autosol"] = case.tools / "unused-autosol"
    def rejected(run, *args, **kwargs):
        directory = run / "AutoSol"; directory.mkdir()
        log = directory / "autosol.log"; log.write_text("fixture rejected phases")
        report_path = directory / "report.json"
        outcome = {"status": "AUTOSOL_WARNING", "use_for_refinement": False,
                   "failure_reason": "fixture rejected phases"}
        report_path.write_text(json.dumps(outcome))
        run_path = run / "report.json"
        data = json.loads(run_path.read_text()); data["autosol"] = outcome
        run_path.write_text(json.dumps(data))
        return SimpleNamespace(status="AUTOSOL_WARNING", message="fixture rejection", matched_distance=None,
            autosol_directory=directory, log_path=log, report_path=report_path)
    monkeypatch.setattr(campaign_stages, "execute_autosol", rejected)
    item = execute_campaign(case.root)["execution"]["datasets"][0]
    assert "autorefine" in case.jobs, item["diagnostic"]
    run = case.root / item["run"]
    refinement = json.loads((run / "AutoRefine/round_001/report.json").read_text())
    assert refinement["inputs"].get("phase_file") is None
    assert any("phases were not accepted" in text for text in item["scientific_warnings"])
    assert receipt(case, "autosol")["status"] == "AUTOSOL_WARNING"


def test_new_preset_is_typed_and_old_bytes_keep_the_same_semantics(tmp_path):
    source = tmp_path / "recipe.txt"; source.write_text(RECIPE)
    policy = load_preset(source).to_dict()
    assert policy["schema_version"] == 2
    assert policy["workflow"] == {"mode":"full-auto", "run_doctor":True, "select_recommendation":True}
    assert policy["autosol"]["on_unaccepted"] == "continue-without-phases"
    assert "workflow" not in load_preset("5w6w").to_dict()
    source.write_text(RECIPE.replace("schema_version = 2", "schema_version = 1"))
    with pytest.raises(PresetError, match="schema_version"):
        load_preset(source)
