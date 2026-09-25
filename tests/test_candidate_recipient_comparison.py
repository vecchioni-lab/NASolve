import json
import tempfile
import unittest
from pathlib import Path

from nasolve.candidate_recipient_comparison import (
    compare_checkpoint_to_recipient,
)

from .test_checkpoints import make_checkpoint_run


class CandidateRecipientComparisonTests(unittest.TestCase):
    def test_legacy_runs_compare_context_without_inventing_target_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            donor = make_checkpoint_run(root / "donor")
            recipient = make_checkpoint_run(root / "recipient")

            donor_report = json.loads((donor / "report.json").read_text())
            donor_report.update(
                mode="standard",
                frame={"name": "W"},
            )
            donor_report["inputs"]["mirror"] = False
            (donor / "report.json").write_text(json.dumps(donor_report))

            recipient_report = json.loads((recipient / "report.json").read_text())
            recipient_report.update(
                mode="standard",
                frame={"name": "3GBI"},
            )
            recipient_report["inputs"]["mirror"] = True
            (recipient / "report.json").write_text(json.dumps(recipient_report))

            before_donor = {
                path.relative_to(donor): path.read_bytes()
                for path in donor.rglob("*")
                if path.is_file()
            }
            before_recipient = {
                path.relative_to(recipient): path.read_bytes()
                for path in recipient.rglob("*")
                if path.is_file()
            }

            comparison = compare_checkpoint_to_recipient(donor, recipient)

            self.assertEqual(
                comparison["dimensions"]["frame_context"]["relation"],
                "DIFFERENT",
            )
            self.assertEqual(
                comparison["dimensions"]["mirror_transform_context"]["relation"],
                "DIFFERENT",
            )
            self.assertEqual(
                comparison["dimensions"]["site_set"]["relation"],
                "UNKNOWN",
            )
            self.assertEqual(
                comparison["dimensions"]["residue_identity"]["relation"],
                "UNKNOWN",
            )
            self.assertIsNone(
                comparison["dimensions"]["target_reference_context"][
                    "donor_source_reference"
                ]
            )
            self.assertIsNone(
                comparison["recipient"]["target_reference"]
            )
            self.assertEqual(comparison["semantics"], {
                "descriptive_only": True,
                "score": None,
                "ranking": None,
                "donor_eligibility": None,
                "recipient_compatibility": None,
                "automatic_reuse_authorized": False,
                "rescue_authorized": False,
            })

            after_donor = {
                path.relative_to(donor): path.read_bytes()
                for path in donor.rglob("*")
                if path.is_file()
            }
            after_recipient = {
                path.relative_to(recipient): path.read_bytes()
                for path in recipient.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after_donor, before_donor)
            self.assertEqual(after_recipient, before_recipient)
            self.assertFalse((donor / "AutoRefine").exists())
            self.assertFalse((recipient / "AutoRefine").exists())

    def test_source_observations_remain_donor_provenance_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            donor = make_checkpoint_run(root / "donor")
            recipient = make_checkpoint_run(root / "recipient")

            comparison = compare_checkpoint_to_recipient(donor, recipient)

            self.assertEqual(
                comparison["donor"]["dataset_name"],
                "dataset",
            )
            self.assertEqual(
                comparison["recipient"]["dataset_name"],
                "dataset",
            )
            self.assertNotEqual(
                comparison["donor"]["dataset_locator"],
                comparison["recipient"]["dataset_locator"],
            )
            self.assertNotEqual(
                comparison["donor"]["run_locator"],
                comparison["recipient"]["run_locator"],
            )
            self.assertNotIn("source_observations", comparison["recipient"])
            self.assertIsNone(
                comparison["semantics"]["recipient_compatibility"]
            )
            self.assertFalse(
                comparison["semantics"]["automatic_reuse_authorized"]
            )


if __name__ == "__main__":
    unittest.main()
