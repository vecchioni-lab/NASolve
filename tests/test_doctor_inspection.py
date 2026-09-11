import io
import json
import shlex
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nasolve.cli import main
from nasolve.config import AppConfig
from nasolve.coot_runtime import CootDiscoveryError, CootInstallation
from nasolve.coot_view import launch_coot_view
from nasolve.refine_doctor import FreeRAudit, RefineDoctorResult

from .test_coot_view import add_review_checkpoint, make_view_run


class DoctorInspectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "checkout with spaces"
        self.run = make_view_run(self.root)
        self.model, self.maps = add_review_checkpoint(self.run)
        self.registry = self.run / "AutoRefine" / "checkpoints.json"
        registry = json.loads(self.registry.read_text())
        registry["checkpoints"][-1]["status"] = "SUCCESS"
        self.registry.write_text(json.dumps(registry))
        self.original_registry = self.registry.read_bytes()
        report_path = self.run / "RefineDoctor" / "doctor_001" / "report.json"
        report_path.parent.mkdir(parents=True)
        report_path.write_text("{}\n")
        self.result = RefineDoctorResult(
            status="REFINE_DOCTOR_RECOMMEND", message="Inspect this branch",
            exit_code=0, run_directory=self.run, doctor_directory=report_path.parent,
            source_checkpoint="refine-001", current_checkpoint_preserved=True,
            recommended_checkpoint="refine-002", recommendation="Inspect this branch",
            audit=FreeRAudit("NOISY", True, {}, (), report_path.parent / "audit.log"),
            trials=(), benchmark=(), report_path=report_path,
        )
        self.coot = self.root / "coot"
        self.coot.write_text("")

    def run_prompt(self, answers, *, terminal=True, discovery_error=None):
        answers = iter(answers)
        prompts = []
        output, errors = io.StringIO(), io.StringIO()
        installation = SimpleNamespace(
            version="2.2.1-6174", environment={}, executables={
                "phenix.refine": self.root / "phenix.refine",
                "phenix.mtz.dump": self.root / "phenix.mtz.dump",
            },
        )

        def answer(prompt):
            # Inspecting and asking again must not accept the candidate.
            select.assert_not_called()
            self.assertEqual(self.registry.read_bytes(), self.original_registry)
            prompts.append(prompt)
            value = next(answers)
            if isinstance(value, BaseException):
                raise value
            return value

        with (
            patch("nasolve.cli.load_config", return_value=AppConfig()),
            patch("nasolve.cli.save_config"),
            patch("nasolve.cli.remember_phenix"),
            patch("nasolve.cli.discover_phenix", return_value=installation),
            patch("nasolve.cli.execute_refine_doctor", return_value=self.result) as doctor,
            patch("nasolve.cli.discover_coot", return_value=CootInstallation(
                self.coot, "1.3.3", "fixture",
            ), side_effect=discovery_error) as discover,
            patch("nasolve.cli.launch_coot_view", side_effect=partial(
                launch_coot_view, launcher=lambda *args, **kwargs: SimpleNamespace(pid=1234),
            )) as launch,
            patch("nasolve.cli.select_checkpoint", return_value=SimpleNamespace(
                checkpoint_id="refine-002",
            )) as select,
            patch("sys.stdin.isatty", return_value=terminal),
            patch("builtins.input", side_effect=answer),
            redirect_stdout(output), redirect_stderr(errors),
        ):
            code = main(["refine-doctor", str(self.run), "--from", "refine-001"])
        doctor.assert_called_once()
        self.assertEqual(self.registry.read_bytes(), self.original_registry)
        return SimpleNamespace(
            code=code, output=output.getvalue(), errors=errors.getvalue(),
            prompts=prompts, launch=launch, select=select, discover=discover,
        )

    def test_inspect_then_yes_reprompts_and_opens_exact_checkpoint(self):
        result = self.run_prompt(["i", "y"])
        self.assertEqual(result.code, 0)
        self.assertEqual(len(result.prompts), 2)
        result.launch.assert_called_once()
        result.select.assert_called_once_with(self.run, "refine-002")
        self.assertIn("Current checkpoint: refine-002", result.output)
        launch = json.loads((self.run / "CootGUI" / "autorefine" / "refine-002"
                             / "launch.json").read_text())
        self.assertEqual(launch["checkpoint_id"], "refine-002")
        self.assertEqual(launch["model_path"], str(self.model.resolve()))
        self.assertEqual(launch["map_path"], str(self.maps.resolve()))

    def test_inspect_then_no_preserves_selection(self):
        result = self.run_prompt(["inspect", "n"])
        self.assertEqual(result.code, 0)
        self.assertEqual(len(result.prompts), 2)
        result.launch.assert_called_once()
        result.select.assert_not_called()
        self.assertIn("Current checkpoint unchanged.", result.output)

    def test_repeat_inspection_and_invalid_input_keep_prompt(self):
        result = self.run_prompt([" i ", "?", "I", "no"])
        self.assertEqual(len(result.prompts), 4)
        self.assertEqual(result.launch.call_count, 2)
        self.assertIn("Please enter y, n, or i.", result.output)
        result.select.assert_not_called()

    def test_coot_failure_returns_to_selection_prompt(self):
        result = self.run_prompt(
            ["i", "n"], discovery_error=CootDiscoveryError("Coot unavailable"),
        )
        self.assertEqual(result.code, 0)
        self.assertEqual(len(result.prompts), 2)
        self.assertIn("Coot unavailable", result.errors)
        result.launch.assert_not_called()
        result.select.assert_not_called()

    def test_empty_eof_and_interrupt_after_inspection_keep_selection(self):
        for ending in ("", EOFError(), KeyboardInterrupt()):
            with self.subTest(ending=type(ending).__name__):
                result = self.run_prompt(["i", ending])
                self.assertEqual(result.code, 0)
                self.assertEqual(len(result.prompts), 2)
                result.select.assert_not_called()
                self.assertIn("Current checkpoint unchanged.", result.output)

    def test_noninteractive_prints_copyable_commands_without_opening_coot(self):
        result = self.run_prompt([], terminal=False)
        self.assertEqual(result.code, 0)
        self.assertEqual(result.prompts, [])
        result.discover.assert_not_called()
        result.launch.assert_not_called()
        result.select.assert_not_called()
        commands = [shlex.split(line.strip()) for line in result.output.splitlines()
                    if line.startswith("  nasolve ")]
        self.assertIn(["nasolve", "show", str(self.run), "--checkpoint", "refine-002"], commands)
        self.assertIn(["nasolve", "checkpoints", "use", str(self.run), "refine-002"], commands)
