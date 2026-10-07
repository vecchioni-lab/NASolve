"""Pathless Coot show follows one owned campaign result, never a guessed model."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nasolve.cli import main
from nasolve.config import AppConfig, WorkspaceSettings
from nasolve.coot_runtime import CootInstallation
from nasolve.coot_view import launch_coot_view

from .test_coot_view import make_view_run


def _solved_result(root: Path, run: Path, status: str = "SOLVED") -> dict:
    return {
        "counts": {"total": 1, "discovered": 1, "blocked": 0},
        "plan_path": str(root / "NASolveCampaign/plan.json"),
        "preset": {"id": "5w6w", "version": "1.1.0"},
        "integrity": "OK",
        "datasets": [{"id": "dataset", "status": "DISCOVERED", "integrity": "OK"}],
        "execution": {
            "state": "COMPLETE" if status == "SOLVED" else "COMPLETE_WITH_FLAGS",
            "datasets": [{
                "id": "dataset", "status": status, "integrity": "OK",
                "run": str(run.relative_to(root)),
                "next_stage": None, "checkpoint": "refine-001",
                "numerical_success": status == "SOLVED",
                "inspection_required": True,
            }],
        },
    }


def _stage_refined(run: Path) -> None:
    report = run / "report.json"
    payload = json.loads(report.read_text())
    payload.update(stage="autorefine", status="AUTOREFINE_READY")
    report.write_text(json.dumps(payload))


class CampaignShowActivationTests(unittest.TestCase):

    def test_completed_single_campaign_run_makes_bare_show_open_exact_refinement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = make_view_run(root, 1)
            target = make_view_run(root, 5)
            _stage_refined(target)
            config = AppConfig(workspace=WorkspaceSettings(
                dataset=str(previous.parent.parent), run=str(previous)
            ))
            expected = _solved_result(root, target)
            coot = root / "fake-coot"
            coot.write_text("fixture")
            launch = partial(
                launch_coot_view,
                launcher=lambda *args, **kwargs: SimpleNamespace(pid=9988),
            )
            output = io.StringIO()
            with (
                patch("nasolve.campaign_execution.execute_campaign", return_value=expected),
                patch("nasolve.cli.load_config", return_value=config),
                patch("nasolve.cli.save_config") as save,
                patch("nasolve.cli.discover_coot",
                      return_value=CootInstallation(coot, "fixture", "test")),
                patch("nasolve.cli.launch_coot_view", side_effect=launch),
                redirect_stdout(output),
            ):
                self.assertEqual(main([
                    "campaign", "run", str(root), "--dataset", "dataset",
                ]), 0)
                self.assertEqual(config.workspace.run, str(target.resolve()))
                self.assertEqual(config.workspace.dataset, str(target.parent.parent.resolve()))
                self.assertIn("Active Coot view: ./nasolve show", output.getvalue())
                save.assert_called_once()
                output.seek(0)
                output.truncate(0)
                self.assertEqual(main(["show"]), 0)

            self.assertIn(f"in run: {target.resolve()}", output.getvalue())
            self.assertIn(
                str(target / "AutoRefine/round_001/refined_001.pdb"),
                output.getvalue(),
            )
            self.assertIn(
                str(target / "AutoRefine/round_001/refined_001_map_coeffs.mtz"),
                output.getvalue(),
            )
            launch_record = json.loads(
                (target / "CootGUI/autorefine/refine-001/launch.json").read_text()
            )
            self.assertEqual(launch_record["checkpoint_id"], "refine-001")
            self.assertEqual(launch_record["stage"], "autorefine")
            self.assertEqual(Path(launch_record["model_path"]).name, "refined_001.pdb")
            self.assertEqual(Path(launch_record["map_path"]).name, "refined_001_map_coeffs.mtz")
            self.assertEqual(
                json.loads((target / "AutoRefine/checkpoints.json").read_text())["current"],
                "refine-001",
            )

    def test_dataset_only_workspace_bare_show_uses_last_numbered_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_view_run(root, 1)
            newest = make_view_run(root, 8)
            coot = root / "coot"
            coot.write_text("")
            config = AppConfig(workspace=WorkspaceSettings(
                dataset=str(newest.parent.parent), run=None
            ))
            with (
                patch("nasolve.cli.load_config", return_value=config),
                patch("nasolve.cli.save_config"),
                patch("nasolve.cli.discover_coot",
                      return_value=CootInstallation(coot, "fixture", "test")),
                patch("nasolve.cli.launch_coot_view", side_effect=partial(
                    launch_coot_view,
                    launcher=lambda *args, **kwargs: SimpleNamespace(pid=9989),
                )),
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(main(["show"]), 0)
            self.assertIn(f"in run: {newest.resolve()}", output.getvalue())
            self.assertIn("current refinement checkpoint refine-001", output.getvalue())

    def test_multidataset_run_never_overwrites_active_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = make_view_run(root, 5)
            _stage_refined(target)
            config = AppConfig(workspace=WorkspaceSettings(run="my-protected-selection"))
            with (
                patch("nasolve.campaign_execution.execute_campaign",
                      return_value=_solved_result(root, target)),
                patch("nasolve.cli.load_config",
                      side_effect=AssertionError("Unexpected workspace read")),
                patch("nasolve.cli.save_config",
                      side_effect=AssertionError("Unexpected workspace write")),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(main([
                    "campaign", "run", str(root), "--dataset", "dataset",
                    "--dataset", "other",
                ]), 0)
            self.assertEqual(config.workspace.run, "my-protected-selection")

    def test_opt_out_and_blocked_result_do_not_activate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = make_view_run(root, 5)
            _stage_refined(target)
            for args, status, exit_code in (
                (["--no-activate"], "SOLVED", 0),
                ([], "BLOCKED", 3),
            ):
                with self.subTest(args=args, status=status), (
                    patch("nasolve.campaign_execution.execute_campaign",
                          return_value=_solved_result(root, target, status=status)),
                    patch("nasolve.cli.load_config",
                          side_effect=AssertionError("Should not read workspace")),
                    patch("nasolve.cli.save_config",
                          side_effect=AssertionError("Should not modify workspace")),
                    redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(main([
                        "campaign", "run", str(root), "--dataset", "dataset", *args,
                    ]), exit_code)

    def test_preflight_only_does_not_activate_or_claim_viewable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = make_view_run(root, 5)
            report_path = target / "report.json"
            report = json.loads(report_path.read_text())
            report.update(stage="automr", status="PREFLIGHT_READY")
            report_path.write_text(json.dumps(report))
            record = _solved_result(root, target, status="PAUSED")
            with (
                patch("nasolve.campaign_execution.execute_campaign", return_value=record),
                patch("nasolve.cli.load_config",
                      side_effect=AssertionError("Should not use incomplete run")),
                patch("nasolve.cli.save_config",
                      side_effect=AssertionError("Should not change workspace")),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(main([
                    "campaign", "run", str(root), "--dataset", "dataset",
                    "--through", "preflight",
                ]), 0)


if __name__ == "__main__":
    unittest.main()
