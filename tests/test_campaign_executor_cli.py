import io
import json
import shlex
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from nasolve.campaigns import CampaignError
from nasolve.cli import main


def execution_record(*, status="PAUSED", state="PAUSED", numerical_success=False):
    return {
        "counts": {"total": 1, "discovered": 1, "blocked": 0},
        "plan_path": "examples/NASolveCampaign/plan.json",
        "preset": {"id": "5w6w", "version": "1.0.0"},
        "integrity": "OK",
        "datasets": [{"id": "DOHU", "status": "DISCOVERED", "integrity": "OK"}],
        "execution": {
            "schema_version": 1,
            "state": state,
            "datasets": [{
                "id": "DOHU", "status": status,
                "diagnostic": "Stage completed; model inspection remains required.",
                "run": "DOHU/AutoMR/run_005", "next_stage": "autorefine",
                "checkpoint": "refine-001" if numerical_success else None,
                "numerical_success": numerical_success,
                "inspection_required": numerical_success,
                "attempts": [],
            }],
        },
    }


class CampaignExecutorCLITests(unittest.TestCase):
    def invoke(self, arguments):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = main(arguments)
        return code, output.getvalue(), error.getvalue()

    def test_run_passes_explicit_root_datasets_boundary_and_phenix_override(self):
        def execute(root, **kwargs):
            self.assertEqual(root, Path("examples"))
            self.assertEqual(kwargs["datasets"], ("DOHU", "QiC_120325_0513"))
            self.assertEqual(kwargs["through"], "postmr")
            self.assertEqual(kwargs["phenix_root"], "/tools/phenix")
            kwargs["progress"]("DOHU: postmr started")
            return execution_record()

        with (
            patch("nasolve.campaign_execution.execute_campaign", side_effect=execute) as run,
            patch("nasolve.cli.save_config", side_effect=AssertionError("Workspace write")),
        ):
            code, output, error = self.invoke([
                "--phenix-root", "/tools/phenix", "campaign", "run", "examples",
                "--dataset", "DOHU", "--dataset", "QiC_120325_0513", "--through", "postmr",
            ])
        self.assertEqual((code, error), (0, ""))
        run.assert_called_once()
        self.assertIn("DOHU: postmr started", output)
        self.assertIn("Execution: PAUSED", output)
        self.assertIn(f"Run: {Path('examples').resolve() / 'DOHU/AutoMR/run_005'}", output)
        self.assertIn("Next stage: autorefine", output)
        self.assertNotIn("scientific preflight and stage execution are pending", output)

    def test_json_run_is_one_parseable_record_and_suppresses_progress(self):
        expected = execution_record(status="SOLVED", state="COMPLETE", numerical_success=True)
        with patch("nasolve.campaign_execution.execute_campaign", return_value=expected) as run:
            code, output, error = self.invoke(["campaign", "run", "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output), expected)
        run.assert_called_once_with(
            Path("."), datasets=None, through="autorefine", phenix_root=None, progress=None,
        )

    def test_status_reports_current_execution_and_numerical_pass_without_approval(self):
        record = execution_record(status="SOLVED", state="COMPLETE", numerical_success=True)
        with patch("nasolve.campaign_execution.execution_status", return_value=record) as status:
            code, output, error = self.invoke(["campaign", "status", "examples with spaces"])
        self.assertEqual((code, error), (0, ""))
        status.assert_called_once_with(Path("examples with spaces"))
        self.assertIn("DOHU: SOLVED; integrity OK", output)
        self.assertIn("Checkpoint: refine-001", output)
        self.assertIn("inspect the model and maps", output)
        self.assertNotIn("approved", output)
        inspection = next(line.strip().removeprefix("Inspect: ")
                          for line in output.splitlines() if line.strip().startswith("Inspect: "))
        self.assertEqual(shlex.split(inspection), [
            "./nasolve", "show", str(Path("examples with spaces").resolve() / "DOHU/AutoMR/run_005"),
            "--checkpoint", "refine-001",
        ])

    def test_local_inspection_and_failure_states_return_review_exit_code(self):
        for state in ("BLOCKED", "NO_SOLUTION", "AWAITING_INSPECTION", "DRIFT"):
            with self.subTest(state=state), patch(
                "nasolve.campaign_execution.execution_status", return_value=execution_record(status=state),
            ):
                code, output, error = self.invoke(["campaign", "status", "examples", "--json"])
            self.assertEqual((code, error), (3, ""))
            self.assertEqual(json.loads(output)["execution"]["datasets"][0]["status"], state)

    def test_pause_and_retry_dispatch_without_running_scientific_stages(self):
        paused = execution_record(state="PAUSE_REQUESTED")
        paused["execution"]["pause_requested"] = True
        with (
            patch("nasolve.campaign_execution.request_pause", return_value=paused) as pause,
            patch("nasolve.campaign_execution.retry_dataset", return_value=execution_record()) as retry,
            patch("nasolve.campaign_execution.execute_campaign", side_effect=AssertionError("execution")),
        ):
            code, output, error = self.invoke(["campaign", "pause", "examples"])
            self.assertEqual((code, error), (0, ""))
            self.assertIn("Pause requested", output)
            code, output, error = self.invoke([
                "campaign", "retry", "examples", "--dataset", "DOHU", "--json",
            ])
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(json.loads(output)["execution"]["state"], "PAUSED")
        pause.assert_called_once_with(Path("examples"))
        retry.assert_called_once_with(Path("examples"), "DOHU")

    def test_execution_errors_are_reported_without_partial_json(self):
        with patch("nasolve.campaign_execution.execute_campaign", side_effect=CampaignError("dataset is locked")):
            code, output, error = self.invoke(["campaign", "run", "examples", "--json"])
        self.assertEqual((code, output), (2, ""))
        self.assertIn("Campaign error: dataset is locked", error)

    def test_retry_rejects_repeated_dataset_instead_of_choosing_the_last_one(self):
        with patch("nasolve.campaign_execution.retry_dataset", side_effect=AssertionError("retry")):
            code, output, error = self.invoke([
                "campaign", "retry", "examples", "--dataset", "DOHU", "--dataset", "QiC_120325_0513",
            ])
        self.assertEqual((code, output), (2, ""))
        self.assertIn("exactly one --dataset", error)

    def test_unsupported_stage_and_missing_retry_dataset_are_rejected(self):
        for arguments in (
            ["campaign", "run", "examples", "--through", "refine-doctor"],
            ["campaign", "retry", "examples"],
        ):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    main(arguments)
            self.assertEqual(caught.exception.code, 2)
