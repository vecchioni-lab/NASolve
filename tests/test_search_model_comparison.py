import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from nasolve.model_assessment import inspect_pdb
from nasolve.search_model_comparison import (
    SearchModelComparisonError,
    compare_search_model_to_target,
    freeze_search_model_comparison,
    load_search_model_comparison,
)

from .helpers import pdb_record


def target(*rows):
    return {
        "schema_version": 1,
        "kind": "sequence-family-target",
        "reference": {
            "id": "fixture",
            "version": "1",
            "content_sha256": "a" * 64,
        },
        "sites": [
            {
                "site": site,
                "residue_code": code,
                "source": source,
                "assignments": [
                    {"source": source, "residue_code": code},
                ],
            }
            for site, code, source in rows
        ],
    }


class SearchModelComparisonTests(unittest.TestCase):
    def assessment(self, root: Path, residues):
        model = root / "model.pdb"
        model.write_text(
            "".join(
                pdb_record(
                    "ATOM",
                    number,
                    "C1'",
                    code,
                    chain,
                    resid,
                    element="C",
                )
                for number, (chain, resid, code) in enumerate(residues, 1)
            )
            + "END\n"
        )
        return inspect_pdb(
            model,
            polymer_ligand_codes={"DA", "DC", "DG", "DT"},
        )

    def test_complete_target_records_identity_delta_without_scoring_model(self):
        with tempfile.TemporaryDirectory() as directory:
            assessment = self.assessment(
                Path(directory),
                [("A", 1, "DA"), ("A", 2, "DC")],
            )
            result = compare_search_model_to_target(
                assessment,
                target(
                    ("A:1", "DA", "family_reference"),
                    ("A:2", "DT", "dataset_site_chemistry"),
                ),
            )
            self.assertEqual(result["status"], "IDENTITY_DIFFERENCES")
            self.assertEqual(result["correspondence"], {
                "exact_site_set": True,
                "missing_sites": [],
                "unexpected_sites": [],
            })
            self.assertEqual(
                result["model"]["chains"],
                [{
                    "chain": "A",
                    "residue_count": 2,
                    "residue_ids": ["1", "2"],
                }],
            )
            self.assertEqual(result["identity"]["match_count"], 1)
            self.assertEqual(result["identity"]["mismatches"], [{
                "site": "A:2",
                "model_residue_code": "DC",
                "target_residue_code": "DT",
                "target_source": "dataset_site_chemistry",
                "expected_postmr_correction": True,
                "route_validated": False,
            }])
            self.assertTrue(result["semantics"]["descriptive_only"])

    def test_missing_and_unexpected_sites_are_recorded_not_aligned(self):
        with tempfile.TemporaryDirectory() as directory:
            assessment = self.assessment(
                Path(directory),
                [("A", 1, "DA"), ("A", 3, "DG")],
            )
            result = compare_search_model_to_target(
                assessment,
                target(
                    ("A:1", "DA", "family_reference"),
                    ("B:1", "DG", "family_reference"),
                ),
            )
            self.assertEqual(result["status"], "SITE_CORRESPONDENCE_DIFFERENCE")
            self.assertEqual(result["correspondence"]["missing_sites"], ["B:1"])
            self.assertEqual(result["correspondence"]["unexpected_sites"], ["A:3"])
            self.assertEqual(result["identity"]["compared_site_count"], 1)
            self.assertEqual(result["identity"]["mismatch_count"], 0)

    def test_frozen_comparison_is_checksum_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run_001"
            (run / "Model").mkdir(parents=True)
            assessment = self.assessment(
                root,
                [("A", 1, "DA")],
            )
            comparison = compare_search_model_to_target(
                assessment,
                target(("A:1", "DA", "family_reference")),
            )
            frozen = freeze_search_model_comparison(comparison, run)
            report = {"search_model_comparison": frozen}
            self.assertEqual(
                load_search_model_comparison(report, run),
                comparison,
            )
            artifact = run / frozen["artifact"]["relative_path"]
            artifact.write_text("{}\n")
            with self.assertRaisesRegex(
                SearchModelComparisonError,
                "missing or failed checksum|changed while being read",
            ):
                load_search_model_comparison(report, run)

            forged = artifact.read_bytes()
            report["search_model_comparison"]["artifact"].update(
                sha256=sha256(forged).hexdigest(),
                size=len(forged),
            )
            with self.assertRaisesRegex(
                SearchModelComparisonError,
                "Malformed frozen search-model comparison record",
            ):
                load_search_model_comparison(report, run)


if __name__ == "__main__":
    unittest.main()
