import json
import tempfile
import unittest
from pathlib import Path

from nasolve.autorefine import execute_autorefine
from nasolve.checkpoints import list_checkpoints, select_checkpoint
from nasolve.refine_doctor import audit_free_r_flags, execute_refine_doctor

from .test_autorefine import make_mtz_dump, make_refine, make_refine_run


class RefineDoctorTests(unittest.TestCase):
    def test_already_successful_checkpoint_is_good_enough_without_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = make_refine_run(root)
            mtz_dump = make_mtz_dump(root)
            source = execute_autorefine(
                run,
                make_refine(root, final_work=0.244, final_free=0.267),
                mtz_dump,
                environment={"PATH": "/usr/bin:/bin"},
            )
            result = execute_refine_doctor(
                run,
                make_refine(root),
                mtz_dump,
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
                environment={"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(source.status, "AUTOREFINE_REVIEW")
            select_checkpoint(run, source.checkpoint_id)
            result = execute_refine_doctor(
                run,
                make_refine(root, final_work=0.244, final_free=0.267),
                mtz_dump,
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


if __name__ == "__main__":
    unittest.main()
