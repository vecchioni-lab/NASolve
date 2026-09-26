import tempfile
import unittest
from pathlib import Path

from nasolve.model_candidates import (
    ModelCandidateInventoryError,
    inventory_dataset_pdb_candidates,
    scout_dataset_pdb_candidates,
)

from .helpers import model_text, pdb_record


CODES = {"DA", "DC", "DG", "DT"}


def target(*rows):
    return {
        "schema_version": 1,
        "kind": "sequence-family-target",
        "reference": {
            "id": "candidate-fixture",
            "version": "1",
            "content_sha256": "a" * 64,
        },
        "sites": [
            {
                "site": site,
                "residue_code": code,
                "source": "family_reference",
                "assignments": [
                    {
                        "source": "family_reference",
                        "residue_code": code,
                    }
                ],
            }
            for site, code in rows
        ],
    }


class ModelCandidateInventoryTests(unittest.TestCase):
    def test_multiple_top_level_pdbs_are_inventoried_without_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "zeta.pdb").write_text(model_text(), encoding="utf-8")
            (root / "alpha.pdb").write_text(
                "".join([
                    pdb_record("ATOM", 1, "C1'", "DA", "M", 10, element="C"),
                    pdb_record("ATOM", 2, "C1'", "DC", "M", 11, element="C"),
                    "END\n",
                ]),
                encoding="utf-8",
            )

            result = inventory_dataset_pdb_candidates(
                root,
                polymer_ligand_codes=CODES,
            )
            self.assertEqual(result["candidate_count"], 2)
            self.assertEqual(result["valid_candidate_count"], 2)
            self.assertEqual(result["invalid_candidate_count"], 0)
            self.assertEqual(
                [row["selector"] for row in result["candidates"]],
                ["alpha.pdb", "zeta.pdb"],
            )
            self.assertIsNone(result["selection"])
            self.assertFalse(
                result["semantics"]["automatic_selection_authorized"]
            )
            self.assertFalse(result["semantics"]["mr_attempt_authorized"])

    def test_invalid_pdb_remains_visible_with_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "good.pdb").write_text(model_text(), encoding="utf-8")
            (root / "bad.pdb").write_text("HEADER only\nEND\n", encoding="utf-8")

            result = inventory_dataset_pdb_candidates(
                root,
                polymer_ligand_codes=CODES,
            )
            self.assertEqual(result["candidate_count"], 2)
            self.assertEqual(result["valid_candidate_count"], 1)
            self.assertEqual(result["invalid_candidate_count"], 1)
            by_name = {
                row["selector"]: row
                for row in result["candidates"]
            }
            self.assertEqual(by_name["bad.pdb"]["status"], "INVALID")
            self.assertIsNone(by_name["bad.pdb"]["assessment"])
            self.assertIn("contains no ATOM or HETATM", by_name["bad.pdb"]["diagnostic"])
            self.assertEqual(by_name["good.pdb"]["status"], "VALID")
            self.assertIsNotNone(by_name["good.pdb"]["assessment"])

    def test_nested_pdbs_are_out_of_scope_for_first_inventory_slice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "top.pdb").write_text(model_text(), encoding="utf-8")
            nested = root / "models"
            nested.mkdir()
            (nested / "nested.pdb").write_text(model_text(), encoding="utf-8")

            result = inventory_dataset_pdb_candidates(
                root,
                polymer_ligand_codes=CODES,
            )
            self.assertEqual(result["candidate_count"], 1)
            self.assertEqual(result["candidates"][0]["selector"], "top.pdb")
            self.assertFalse(result["semantics"]["nested_pdbs_discovered"])

    def test_empty_dataset_inventory_is_valid_and_nondecisional(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = inventory_dataset_pdb_candidates(
                root,
                polymer_ligand_codes=CODES,
            )
            self.assertEqual(result["candidate_count"], 0)
            self.assertEqual(result["valid_candidate_count"], 0)
            self.assertEqual(result["invalid_candidate_count"], 0)
            self.assertEqual(result["candidates"], [])
            self.assertIsNone(result["selection"])

    def test_duplicate_atom_identity_is_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = pdb_record("ATOM", 1, "C1'", "DA", "A", 1, element="C")
            (root / "duplicate.pdb").write_text(
                row + row + "END\n",
                encoding="utf-8",
            )
            result = inventory_dataset_pdb_candidates(
                root,
                polymer_ligand_codes=CODES,
            )
            candidate = result["candidates"][0]
            self.assertEqual(candidate["status"], "VALID")
            self.assertEqual(
                candidate["assessment"]["duplicate_atom_identities"],
                1,
            )
            self.assertTrue(candidate["assessment"]["warnings"])

    def test_multi_pdb_scout_reports_registered_and_ambiguous_without_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "registered.pdb").write_text(
                "".join([
                    pdb_record("ATOM", 1, "C1'", "DA", "A", 1, element="C"),
                    pdb_record("ATOM", 2, "C1'", "DA", "A", 2, element="C"),
                    pdb_record("ATOM", 3, "C1'", "DG", "B", 1, element="C"),
                    pdb_record("ATOM", 4, "C1'", "DG", "B", 2, element="C"),
                    "END\n",
                ]),
                encoding="utf-8",
            )
            (root / "ambiguous.pdb").write_text(
                "".join([
                    pdb_record("ATOM", 1, "C1'", "DA", "M", 1, element="C"),
                    pdb_record("ATOM", 2, "C1'", "DA", "M", 2, element="C"),
                    pdb_record("ATOM", 3, "C1'", "DG", "N", 1, element="C"),
                    pdb_record("ATOM", 4, "C1'", "DG", "N", 2, element="C"),
                    "END\n",
                ]),
                encoding="utf-8",
            )
            result = scout_dataset_pdb_candidates(
                root,
                target(
                    ("A:1", "DA"),
                    ("A:2", "DA"),
                    ("B:1", "DG"),
                    ("B:2", "DG"),
                ),
                polymer_ligand_codes=CODES,
            )
            self.assertEqual(result["candidate_count"], 2)
            self.assertEqual(result["registered_candidate_count"], 1)
            self.assertEqual(result["ambiguous_candidate_count"], 1)
            self.assertEqual(result["unresolved_candidate_count"], 0)
            self.assertIsNone(result["selection"])
            by_name = {
                row["selector"]: row
                for row in result["candidates"]
            }
            self.assertEqual(
                by_name["registered.pdb"]["registration_scout"]["status"],
                "REGISTERED",
            )
            self.assertEqual(
                by_name["ambiguous.pdb"]["registration_scout"]["status"],
                "AMBIGUOUS",
            )
            self.assertFalse(
                result["semantics"]["automatic_selection_authorized"]
            )
            self.assertTrue(
                result["semantics"]["registration_status_is_not_mr_quality"]
            )

    def test_multi_pdb_scout_keeps_invalid_candidates_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "good.pdb").write_text(
                pdb_record("ATOM", 1, "C1'", "DA", "A", 1, element="C")
                + "END\n",
                encoding="utf-8",
            )
            (root / "bad.pdb").write_text("HEADER only\nEND\n", encoding="utf-8")
            result = scout_dataset_pdb_candidates(
                root,
                target(("A:1", "DA")),
                polymer_ligand_codes=CODES,
            )
            self.assertEqual(result["valid_candidate_count"], 1)
            self.assertEqual(result["invalid_candidate_count"], 1)
            self.assertEqual(result["registered_candidate_count"], 1)
            by_name = {
                row["selector"]: row
                for row in result["candidates"]
            }
            self.assertEqual(by_name["bad.pdb"]["status"], "INVALID")
            self.assertIsNone(by_name["bad.pdb"]["registration_scout"])
            self.assertIsNotNone(by_name["bad.pdb"]["diagnostic"])

    def test_missing_dataset_directory_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaisesRegex(
                ModelCandidateInventoryError,
                "does not exist",
            ):
                inventory_dataset_pdb_candidates(
                    missing,
                    polymer_ligand_codes=CODES,
                )


if __name__ == "__main__":
    unittest.main()
