import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from nasolve.cli import main

from .helpers import make_dataset, model_text


class CampaignCLITests(unittest.TestCase):
    def fixture(self, root):
        campaign = root / "campaign"
        dataset = make_dataset(campaign / "DOHU", include_model=False)
        (dataset / "nasolve.txt").write_text(
            "[automr]\nmode = standard\nframe = W\npair = D:OHU\n",
            encoding="utf-8",
        )
        frames = root / "frames"
        (frames / "5W6W").mkdir(parents=True)
        (frames / "5W6W" / "C_G.pdb").write_text(model_text())
        return campaign, frames, dataset

    def invoke(self, arguments):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            result = main(arguments)
        return result, output.getvalue(), error.getvalue()

    def test_plan_and_status_json_do_not_discover_tools_or_change_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            campaign, frames, dataset = self.fixture(root)
            intent = (dataset / "nasolve.txt").read_bytes()
            with (
                patch("nasolve.cli.discover_phenix", side_effect=AssertionError("Phenix discovery")),
                patch("nasolve.cli.discover_coot", side_effect=AssertionError("Coot discovery")),
                patch("nasolve.cli.load_config", side_effect=AssertionError("Workspace read")),
                patch("nasolve.cli.save_config", side_effect=AssertionError("Workspace write")),
            ):
                code, output, error = self.invoke([
                    "campaign", "plan", str(campaign), "--frames-dir", str(frames), "--json",
                ])
                self.assertEqual((code, error), (0, ""))
                planned = json.loads(output)
                self.assertEqual(planned["counts"]["discovered"], 1)
                self.assertEqual(planned["datasets"][0]["id"], "DOHU")
                code, output, error = self.invoke(["campaign", "status", str(campaign), "--json"])
                self.assertEqual((code, error), (0, ""))
                self.assertEqual(json.loads(output)["integrity"], "OK")
            self.assertEqual((dataset / "nasolve.txt").read_bytes(), intent)
            self.assertFalse((dataset / "AutoMR").exists())

    def test_blocked_dataset_is_visible_and_returns_review_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign, frames, _ = self.fixture(Path(directory).resolve())
            incomplete = campaign / "incomplete"
            incomplete.mkdir()
            (incomplete / "summary.html").write_text("<html></html>\n")
            code, output, error = self.invoke([
                "campaign", "plan", str(campaign), "--frames-dir", str(frames),
            ])
            self.assertEqual((code, error), (3, ""))
            self.assertIn("DOHU", output)
            self.assertIn("incomplete", output)
            self.assertIn("BLOCKED", output)
            self.assertIn("MTZ", output)
            self.assertIn("Input and model selection", output)
            code, _, _ = self.invoke(["campaign", "status", str(campaign)])
            self.assertEqual(code, 3)

    def test_status_reports_drift_without_rewriting_the_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign, frames, dataset = self.fixture(Path(directory).resolve())
            self.assertEqual(self.invoke([
                "campaign", "plan", str(campaign), "--frames-dir", str(frames),
            ])[0], 0)
            plan_path = campaign / "NASolveCampaign" / "plan.json"
            frozen = plan_path.read_bytes()
            reflection = next(dataset.glob("*.mtz"))
            reflection.write_bytes(b"changed authoritative observations")
            code, output, error = self.invoke(["campaign", "status", str(campaign), "--json"])
            self.assertEqual((code, error), (3, ""))
            self.assertEqual(json.loads(output)["integrity"], "DRIFT")
            self.assertEqual(plan_path.read_bytes(), frozen)

    def test_replanning_preserves_existing_manifest_and_reports_error(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign, frames, _ = self.fixture(Path(directory).resolve())
            args = ["campaign", "plan", str(campaign), "--frames-dir", str(frames)]
            self.assertEqual(self.invoke(args)[0], 0)
            manifest = campaign / "NASolveCampaign" / "plan.json"
            before = manifest.read_bytes()
            code, output, error = self.invoke(args)
            self.assertEqual(code, 2)
            self.assertEqual(output, "")
            self.assertIn("Campaign error:", error)
            self.assertEqual(manifest.read_bytes(), before)

    def test_preset_check_is_machine_readable_and_reports_missing_files(self):
        with patch("nasolve.cli.load_config", side_effect=AssertionError("Workspace read")):
            code, output, error = self.invoke(["preset", "check", "5w6w", "--json"])
        self.assertEqual((code, error), (0, ""))
        record = json.loads(output)
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["id"], "5w6w")
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.toml"
            code, output, error = self.invoke(["preset", "check", str(missing)])
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("Preset error:", error)
