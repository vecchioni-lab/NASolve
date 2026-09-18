import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nasolve.autorefine import LEGACY_EXPLICIT, execute_autorefine
from nasolve.checkpoints import list_checkpoints, select_checkpoint
from nasolve.refine_doctor import (
    RefineDoctorError,
    audit_free_r_flags,
    execute_refine_doctor,
    write_terminal_phosphate_protection,
)

from .test_autorefine import (
    PHENIX_120,
    PHENIX_21,
    make_mtz_dump,
    make_refine,
    make_refine_run,
)


class RefineDoctorTests(unittest.TestCase):
    def test_unknown_phenix_version_fails_before_creating_doctor_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)

            with self.assertRaisesRegex(RefineDoctorError, "will not guess"):
                execute_refine_doctor(
                    run,
                    make_refine(root),
                    make_mtz_dump(root),
                    phenix_version="unknown",
                    environment={"PATH": "/usr/bin:/bin"},
                )

            self.assertFalse((run / "RefineDoctor").exists())

    def test_already_successful_checkpoint_is_good_enough_without_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            mtz_dump = make_mtz_dump(root)
            source = execute_autorefine(
                run,
                make_refine(root, final_work=0.244, final_free=0.267),
                mtz_dump,
                phenix_version=PHENIX_21,
                environment={"PATH": "/usr/bin:/bin"},
            )
            result = execute_refine_doctor(
                run,
                make_refine(root),
                mtz_dump,
                phenix_version=PHENIX_21,
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(result.status, "REFINE_DOCTOR_GOOD_ENOUGH")
            self.assertEqual(result.recommended_checkpoint, source.checkpoint_id)
            self.assertEqual(result.trials, ())

    def test_bounded_trials_preserve_current_and_recommend_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            mtz_dump = make_mtz_dump(root)
            source = execute_autorefine(
                run,
                make_refine(root, final_work=0.162, final_free=0.155),
                mtz_dump,
                phenix_version=PHENIX_21,
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(source.status, "AUTOREFINE_REVIEW")
            select_checkpoint(run, source.checkpoint_id)
            with patch(
                "nasolve.refine_doctor.execute_autorefine",
                wraps=execute_autorefine,
            ) as execute_trial:
                result = execute_refine_doctor(
                    run,
                    make_refine(root, final_work=0.244, final_free=0.267),
                    mtz_dump,
                    phenix_version=PHENIX_120,
                    environment={"PATH": "/usr/bin:/bin"},
                    macro_cycles=3,
                )
            self.assertEqual(result.status, "REFINE_DOCTOR_RECOMMEND")
            self.assertEqual(result.source_checkpoint, "refine-001")
            self.assertEqual(result.recommended_checkpoint, "refine-002")
            self.assertEqual(len(result.trials), 1)
            self.assertTrue(result.current_checkpoint_preserved)
            self.assertEqual(result.audit.status, "NOISY")
            self.assertEqual(result.benchmark[0]["source_checkpoint"], "refine-001")
            records, current, _ = list_checkpoints(run)
            self.assertEqual(current, "refine-001")
            self.assertEqual(
                {record.parent for record in records[-1:]}, {"refine-001"}
            )
            report = json.loads(result.report_path.read_text())
            self.assertFalse(report["automatic_selection"])
            self.assertEqual(report["audit"]["free_independent_groups"], 45)
            self.assertFalse(report["eligibility"]["individual_adp_trial"])
            self.assertEqual(report["phenix_version"], PHENIX_120)
            self.assertEqual(report["reflection_selector_mode"], LEGACY_EXPLICIT)
            self.assertGreater(len(execute_trial.call_args_list), 0)
            for call in execute_trial.call_args_list:
                self.assertEqual(call.kwargs["phenix_version"], PHENIX_120)
            for trial in result.trials:
                trial_report = json.loads(trial.report_path.read_text())
                self.assertEqual(trial_report["phenix_version"], PHENIX_120)
                self.assertEqual(
                    trial_report["reflection_selector_mode"],
                    LEGACY_EXPLICIT,
                )
                params = (trial.round_directory / "autorefine.params").read_text()
                self.assertNotIn("data_manager", params)

    def test_terminal_phosphate_protection_uses_phenix_native_ideals(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "protect.phil"

            audit = {
                "requires_review": True,
                "sites": [{
                    "site": "D:1",
                    "requires_review": True,
                    "restraints": [
                        {"kind": "angle", "atoms": ["OP1", "P", "OP2"], "ideal": 120.00},
                        {"kind": "angle", "atoms": ["OP1", "P", "OP3"], "ideal": 109.47},
                        {"kind": "angle", "atoms": ["OP2", "P", "OP3"], "ideal": 109.47},
                        {"kind": "angle", "atoms": ["O5'", "P", "OP1"], "ideal": 109.00},
                        {"kind": "angle", "atoms": ["O5'", "P", "OP2"], "ideal": 108.00},
                        {"kind": "angle", "atoms": ["O5'", "P", "OP3"], "ideal": 109.47},
                        {"kind": "angle", "atoms": ["P", "O5'", "C5'"], "ideal": 120.90},
                    ],
                }],
            }

            record = write_terminal_phosphate_protection(
                audit,
                destination,
            )
            text = destination.read_text()

            self.assertEqual(record["sites"], ["D:1"])
            self.assertEqual(record["angle_count"], 6)
            self.assertEqual(record["sigma"], 1.0)
            self.assertEqual(
                record["ideal_source"],
                "source-checkpoint-final-phenix-geometry-audit",
            )

            self.assertEqual(text.count("action = *change"), 6)
            self.assertEqual(text.count("sigma = 1"), 6)

            # Native Phenix values are carried through from the audit.
            self.assertIn("angle_ideal = 120", text)
            self.assertIn("angle_ideal = 108", text)
            self.assertIn("angle_ideal = 109.47", text)

            # P-O5'-C5' is deliberately not part of the six-angle protection.
            self.assertNotIn("name C5'", text)

    def test_terminal_geometry_trigger_runs_protected_clean_parent_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            mtz_dump = make_mtz_dump(root)

            source = execute_autorefine(
                run,
                make_refine(root, final_work=0.162, final_free=0.155),
                mtz_dump,
                phenix_version=PHENIX_21,
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(source.status, "AUTOREFINE_REVIEW")

            synthetic_audit = {
                "status": "REVIEW",
                "requires_review": True,
                "sigma_threshold": 5.0,
                "sites": [{
                    "site": "D:1",
                    "requires_review": True,
                    "restraint_count": 11,
                    "expected_restraint_count": 11,
                    "max_sigma_deviation": 7.0,
                    "severe_restraints": [],
                    "restraints": [
                        {"kind": "angle", "atoms": ["OP1", "P", "OP2"], "ideal": 120.00},
                        {"kind": "angle", "atoms": ["OP1", "P", "OP3"], "ideal": 109.47},
                        {"kind": "angle", "atoms": ["OP2", "P", "OP3"], "ideal": 109.47},
                        {"kind": "angle", "atoms": ["O5'", "P", "OP1"], "ideal": 109.00},
                        {"kind": "angle", "atoms": ["O5'", "P", "OP2"], "ideal": 108.00},
                        {"kind": "angle", "atoms": ["O5'", "P", "OP3"], "ideal": 109.47},
                        {"kind": "angle", "atoms": ["P", "O5'", "C5'"], "ideal": 120.90},
                    ],
                }],
            }

            protected_pass = {
                "status": "PASS",
                "requires_review": False,
                "sigma_threshold": 5.0,
                "sites": [{
                    "site": "D:1",
                    "requires_review": False,
                    "restraint_count": 11,
                    "expected_restraint_count": 11,
                    "max_sigma_deviation": 1.0,
                    "severe_restraints": [],
                    "restraints": [],
                }],
            }

            def source_audit(checkpoint):
                return (
                    synthetic_audit
                    if checkpoint.get("id") == source.checkpoint_id
                    else None
                )

            with patch(
                "nasolve.refine_doctor._terminal_geometry_audit",
                side_effect=source_audit,
            ), patch(
                "nasolve.autorefine.audit_terminal_phosphate_geometry",
                return_value=protected_pass,
            ):
                result = execute_refine_doctor(
                    run,
                    make_refine(root, final_work=0.244, final_free=0.267),
                    mtz_dump,
                    phenix_version=PHENIX_21,
                    environment={"PATH": "/usr/bin:/bin"},
                    from_checkpoint=source.checkpoint_id,
                    macro_cycles=1,
                )

            self.assertEqual(len(result.trials), 1)
            trial = result.trials[0]
            self.assertEqual(trial.parent_checkpoint, "postmr")

            trial_report = json.loads(trial.report_path.read_text())
            self.assertEqual(
                trial_report["recipe"],
                "RefineDoctor/terminal-phosphate-protected",
            )
            self.assertEqual(
                len(trial_report["inputs"]["extra_restraints"]),
                1,
            )

            protection = Path(
                trial_report["inputs"]["extra_restraints"][0]
            )
            self.assertTrue(protection.is_file())
            self.assertEqual(
                protection.read_text().count("action = *change"),
                6,
            )

            doctor_report = json.loads(result.report_path.read_text())
            self.assertTrue(
                doctor_report["terminal_geometry"]["triggered"]
            )
            self.assertEqual(
                doctor_report["terminal_geometry"][
                    "clean_parent_checkpoint"
                ],
                "postmr",
            )
            self.assertEqual(
                doctor_report["triage"]["stop_reason"],
                "terminal-geometry-rescued",
            )
            self.assertEqual(
                doctor_report["inspection_checkpoint"],
                trial.checkpoint_id,
            )

    def test_objectively_invalid_flags_stop_before_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            observations = root / "data.mtz"
            observations.write_bytes(b"data")
            phenix_python = root / "phenix.python"
            phenix_python.write_text(
                "#!/bin/sh\n"
                "echo 'NASOLVE_FREE_R_AUDIT_JSON:{\"independent_friedel_groups\": 100, \"paired_friedel_groups\": 90, \"free_independent_groups\": 5, \"free_fraction\": 0.05, \"inconsistent_friedel_flag_groups\": 2, \"resolution_shells\": []}'\n"
            )
            phenix_python.chmod(0o755)
            destination = root / "doctor"
            destination.mkdir()
            audit = audit_free_r_flags(
                observations,
                "FreeR_flag",
                0,
                phenix_python,
                destination,
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(audit.status, "INVALID")
            self.assertFalse(audit.valid)
            self.assertTrue(any("inconsistent" in warning for warning in audit.warnings))

    def test_invalid_flags_report_selector_provenance_without_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            refine = make_refine(root)
            phenix_python = root / "phenix.python"
            phenix_python.write_text(
                "#!/bin/sh\n"
                "echo 'NASOLVE_FREE_R_AUDIT_JSON:{\"independent_friedel_groups\": 100, "
                "\"paired_friedel_groups\": 90, \"free_independent_groups\": 5, "
                "\"free_fraction\": 0.05, \"inconsistent_friedel_flag_groups\": 2, "
                "\"resolution_shells\": []}'\n"
            )
            phenix_python.chmod(0o755)

            result = execute_refine_doctor(
                run,
                refine,
                make_mtz_dump(root),
                phenix_version=PHENIX_120,
                environment={"PATH": "/usr/bin:/bin"},
            )

            self.assertEqual(result.status, "REFINE_DOCTOR_FLAG_REPAIR_REQUIRED")
            self.assertEqual(result.trials, ())
            payload = json.loads(result.report_path.read_text())
            self.assertEqual(payload["phenix_version"], PHENIX_120)
            self.assertEqual(payload["reflection_selector_mode"], LEGACY_EXPLICIT)
            records, current, _ = list_checkpoints(run)
            self.assertEqual(current, "postmr")
            self.assertEqual([record.checkpoint_id for record in records], ["postmr"])


if __name__ == "__main__":
    unittest.main()
