import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nasolve.autorefine import (
    AutoRefineError, build_reflection_plan, execute_autorefine,
    calculated_anomalous_groups, reflection_selector_policy, write_recipe_parameters,
)
from nasolve.cli import main
from nasolve.config import AppConfig
from nasolve.checkpoints import list_checkpoints
from nasolve.refine_doctor import (
    FreeRAudit, _candidate, _recommend, execute_refine_doctor,
)
from .test_autorefine import PHENIX_21, make_mtz_dump, make_refine, make_refine_run


class DoctorTriageTests(unittest.TestCase):
    def test_small_inversion_is_review_not_a_scientific_endorsement(self):
        candidates = [
            _candidate(name, "test", {"r_work": work, "r_free": free})
            for name, work, free in (
                ("refine-001", .1644, .1562),
                ("refine-002", .151, .148),
                ("refine-003", .162, .157),
            )
        ]
        audit = FreeRAudit("NOISY", True, {}, (), Path("audit.log"))
        status, selected, reason, code = _recommend(candidates, "refine-001", audit)
        self.assertEqual(status, "REFINE_DOCTOR_REVIEW")
        self.assertIsNone(selected)
        self.assertEqual(code, 2)
        self.assertIn("refine-002", reason)
        self.assertIn("uncertainty", reason)

    def test_bad_or_unusable_statistics_cannot_win(self):
        for work, free in ((True, .2), (.1, math.inf), (-.1, .2), (.1, math.nan)):
            with self.subTest(work=work, free=free):
                item = _candidate("bad", "test", {"r_work": work, "r_free": free})
                self.assertFalse(item["strict_success"])
        item = _candidate("failed", "test", {"r_work": .1, "r_free": .2}, usable=False)
        self.assertFalse(item["strict_success"])

    def mean_run(self, root):
        run = make_refine_run(root, autosol=False)
        report_path = run / "report.json"
        report = json.loads(report_path.read_text())
        report["postmr"]["anomalous"]["candidates"] = []
        report_path.write_text(json.dumps(report))
        return run

    def test_mean_data_fallbacks_are_bounded_siblings_with_frozen_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            dump = make_mtz_dump(root, anomalous=False)
            source = execute_autorefine(run, make_refine(root, final_work=.22, final_free=.21),
                                       dump, phenix_version=PHENIX_21)
            before = list_checkpoints(run)[1]
            result = execute_refine_doctor(run, make_refine(root, final_work=.20, final_free=.19),
                                          dump, phenix_version=PHENIX_21,
                                          from_checkpoint=source.checkpoint_id)
            self.assertEqual(result.status, "REFINE_DOCTOR_REVIEW")
            self.assertEqual(len(result.trials), 3)
            self.assertEqual(list_checkpoints(run)[1], before)
            strategies = []
            for trial in result.trials:
                payload = json.loads(trial.report_path.read_text())
                self.assertEqual(trial.parent_checkpoint, source.checkpoint_id)
                self.assertEqual(payload["inputs"]["observation_labels"], ["IMEAN", "SIGIMEAN"])
                self.assertEqual(payload["inputs"]["free_r_test_value"], 0)
                self.assertFalse(payload["refinement"]["refine_occupancies"])
                self.assertEqual(payload["statistics"]["anomalous_scatterers"], [])
                strategies.append(payload["refinement"]["strategies"])
            self.assertEqual(strategies, [["individual_sites", "group_adp"],
                                          ["individual_sites"], ["group_adp"]])
            payload = json.loads(result.report_path.read_text())
            self.assertEqual(payload["triage"]["stop_reason"], "eligible-recipes-exhausted")
            self.assertTrue(payload["triage"]["next_actions"])
            self.assertEqual(payload["inspection_checkpoint"], result.trials[0].checkpoint_id)
            reasons = " ".join(item["reason"] for item in payload["triage"]["recipes"])
            self.assertIn("phases", reasons)
            self.assertIn("resolution", reasons)

    def test_pass_stops_default_recipes_and_does_not_select(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            result = execute_refine_doctor(run, make_refine(root, final_work=.2, final_free=.22),
                                          make_mtz_dump(root, anomalous=False),
                                          phenix_version=PHENIX_21)
            self.assertEqual(len(result.trials), 1)
            self.assertEqual(result.status, "REFINE_DOCTOR_RECOMMEND")
            self.assertEqual(list_checkpoints(run)[1], "postmr")

    def test_budget_exhaustion_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            result = execute_refine_doctor(run, make_refine(root, final_work=.4, final_free=.5),
                                          make_mtz_dump(root, anomalous=False),
                                          phenix_version=PHENIX_21, max_trials=1)
            self.assertEqual(len(result.trials), 1)
            payload = json.loads(result.report_path.read_text())
            self.assertEqual(payload["triage"]["stop_reason"], "trial-budget-exhausted")
            self.assertEqual(result.status, "REFINE_DOCTOR_REVIEW")

    def test_failed_phil_dry_run_stops_fallbacks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            result = execute_refine_doctor(run, make_refine(root, preflight_return_code=8),
                                          make_mtz_dump(root, anomalous=False), phenix_version=PHENIX_21)
            self.assertEqual(len(result.trials), 1)
            self.assertIsNone(result.recommended_checkpoint)
            payload = json.loads(result.report_path.read_text())
            self.assertEqual(payload["triage"]["stop_reason"], "technical-failure")
            self.assertIsNone(payload["inspection_checkpoint"])

    def test_unavailable_audit_does_not_launch_refinement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            audit = FreeRAudit("UNAVAILABLE", None, {}, ("Audit unavailable",), root / "audit.log")
            with patch("nasolve.refine_doctor.audit_free_r_flags", return_value=audit):
                result = execute_refine_doctor(run, make_refine(root), make_mtz_dump(root),
                                              phenix_version=PHENIX_21)
            self.assertEqual(result.status, "REFINE_DOCTOR_REVIEW")
            self.assertEqual(result.trials, ())

    def test_anomalous_trials_explicitly_set_fixed_and_fdp_only_scattering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            refine = make_refine(root, final_work=.2, final_free=.19)
            python = root / "phenix.python"
            text = python.read_text().replace(
                '  *) printf',
                "  *NASOLVE_SCATTERING_JSON*) printf '%s\\n' "
                "'NASOLVE_SCATTERING_JSON:{\"I\": [-1.8, 5.75]}';;\n  *) printf",
            )
            python.write_text(text)
            result = execute_refine_doctor(run, refine, make_mtz_dump(root),
                                          phenix_version=PHENIX_21, max_trials=3)
            self.assertEqual(len(result.trials), 3)
            modes = []
            for trial in result.trials:
                payload = json.loads(trial.report_path.read_text())
                modes.append(payload["refinement"]["anomalous_parameter_mode"])
                params = (trial.round_directory / "autorefine.params").read_text()
                self.assertIn("f_prime = -1.8", params)
                self.assertIn("f_double_prime = 5.75", params)
                self.assertEqual(payload["inputs"]["observation_labels"][0], "F(+)")
                if modes[-1] == "fixed":
                    self.assertNotIn("*group_anomalous", params)
                    self.assertIsNone(payload["statistics"]["anomalous_scatterers"][0]["refined_f_double_prime"])
                else:
                    self.assertIn("refine = f_prime *f_double_prime", params)
            self.assertEqual(modes, ["fixed", "fixed", "fdp-only"])
            self.assertEqual(result.benchmark[0]["source_checkpoint"], result.trials[2].checkpoint_id)

    def test_missing_wavelength_skips_anomalous_recipes_with_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root, autosol=False)
            result = execute_refine_doctor(run, make_refine(root), make_mtz_dump(root),
                                          phenix_version=PHENIX_21)
            self.assertEqual(result.trials, ())
            self.assertEqual(result.status, "REFINE_DOCTOR_REVIEW")
            payload = json.loads(result.report_path.read_text())
            self.assertIn("wavelength", json.dumps(payload["triage"]))

    def test_explicit_scattering_modes_reject_mean_data_before_writing_phil(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            report = json.loads((run / "report.json").read_text())
            observations = Path(report["inputs"]["reflections"])
            plan = build_reflection_plan(report, observations, make_mtz_dump(root, anomalous=False), None)
            with self.assertRaisesRegex(AutoRefineError, "anomalous observations"):
                write_recipe_parameters(root / "params", selector_policy=reflection_selector_policy(PHENIX_21),
                    observations=observations, reflection_plan=plan, macro_cycles=3, processor_count=1,
                    anomalous_atom_selections=(), anomalous_mode="fdp-only")
            self.assertFalse((root / "params").exists())

    def test_review_cli_shows_inspection_and_never_prompts_for_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            result = execute_refine_doctor(run, make_refine(root, final_work=.2, final_free=.19),
                                          make_mtz_dump(root, anomalous=False),
                                          phenix_version=PHENIX_21, max_trials=1)
            installation = SimpleNamespace(version=PHENIX_21, environment={}, executables={
                "phenix.refine": root / "phenix.refine", "phenix.mtz.dump": root / "phenix.mtz.dump",
            })
            output = io.StringIO()
            with (
                patch("nasolve.cli.load_config", return_value=AppConfig()),
                patch("nasolve.cli._workspace_run", return_value=run),
                patch("nasolve.cli.discover_phenix", return_value=installation),
                patch("nasolve.cli.remember_phenix"), patch("nasolve.cli.save_config"),
                patch("nasolve.cli.execute_refine_doctor", return_value=result) as execute,
                patch("sys.stdin.isatty", return_value=True),
                patch("builtins.input", side_effect=AssertionError("Unexpected selection prompt")),
                redirect_stdout(output),
            ):
                self.assertEqual(main(["refine-doctor", str(run), "--max-trials", "1"]), 2)
            self.assertEqual(execute.call_args.kwargs["max_trials"], 1)
            self.assertIn("inspection only", output.getvalue())
            self.assertIn("--checkpoint refine-001", output.getvalue())
            self.assertIn("trial-budget-exhausted", output.getvalue())

    def test_failed_process_cannot_win_even_if_it_printed_good_statistics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            refine = make_refine(root, final_work=.1, final_free=.2)
            refine.write_text(refine.read_text() + "\nraise SystemExit(9)\n")
            result = execute_refine_doctor(run, refine, make_mtz_dump(root, anomalous=False),
                                          phenix_version=PHENIX_21)
            self.assertIsNone(result.recommended_checkpoint)
            self.assertEqual(result.status, "REFINE_DOCTOR_REVIEW")
            self.assertEqual(len(result.trials), 1)
            self.assertEqual(result.trials[0].statistics["r_free"], .2)

    def test_bad_scattering_calculation_is_never_replaced_with_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            report = json.loads((run / "report.json").read_text())
            refine = make_refine(root)
            for stdout in ("5.75", 'NASOLVE_SCATTERING_JSON:{"I": [NaN, 5.75]}',
                           'NASOLVE_SCATTERING_JSON:{"I": [-1.8, -9999]}'):
                with self.subTest(stdout=stdout), patch("nasolve.autorefine.subprocess.run",
                    return_value=SimpleNamespace(returncode=0, stdout=stdout)):
                    with self.assertRaises(AutoRefineError):
                        calculated_anomalous_groups(report, refine, None)

    def test_invalid_budgets_fail_before_doctor_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self.mean_run(root)
            for budget in (0, 11, True):
                with self.subTest(budget=budget), self.assertRaisesRegex(RuntimeError, "max_trials"):
                    execute_refine_doctor(run, make_refine(root), make_mtz_dump(root),
                                         phenix_version=PHENIX_21, max_trials=budget)
            self.assertFalse((run / "RefineDoctor").exists())

    def test_scattering_preserves_alternate_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            report = json.loads((run / "report.json").read_text())
            report["postmr"]["anomalous"]["candidates"][0]["alternate"] = "B"
            groups = calculated_anomalous_groups(report, make_refine(root), None)
            self.assertEqual(set(groups), {"chain B and resid 4 and name I and altloc B"})


if __name__ == "__main__":
    unittest.main()
