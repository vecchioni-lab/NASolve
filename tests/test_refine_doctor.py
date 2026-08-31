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
            self.assertEqual(len(result.trials), 2)
            self.assertTrue(result.current_checkpoint_preserved)
            self.assertEqual(result.audit.status, "NOISY")
            self.assertEqual(result.benchmark[0]["source_checkpoint"], "refine-001")
            records, current, _ = list_checkpoints(run)
            self.assertEqual(current, "refine-001")
            self.assertEqual(
                {record.parent for record in records[-2:]}, {"refine-001"}
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
