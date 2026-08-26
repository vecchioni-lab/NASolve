import tempfile
import unittest
from pathlib import Path

from nasolve.model_assessment import copy_preserving_model, file_sha256, inspect_pdb

from .helpers import model_text, pdb_record


class ModelAssessmentTests(unittest.TestCase):
    def test_counts_and_preserving_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdb"
            destination = root / "run" / "input_model.pdb"
            source.write_text(model_text())
            assessment = inspect_pdb(source, polymer_ligand_codes={"DA", "DC"})
            self.assertEqual(assessment.atom_count, 3)
            self.assertEqual(assessment.polymer_residue_count, 2)
            self.assertEqual(assessment.heteroatom_count, 1)
            self.assertEqual(assessment.polymer_residue_ids_by_chain, {"A": ["1", "2"]})
            copy_preserving_model(source, destination, assessment)
            self.assertEqual(file_sha256(source), file_sha256(destination))
            self.assertTrue(assessment.heteroatoms_preserved)

    def test_modified_nucleotide_hetatm_counts_as_polymer_residue(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "modified.pdb"
            source.write_text(
                pdb_record("ATOM", 1, "P", "DA", "A", 1)
                + pdb_record("HETATM", 2, "P", "DE", "A", 2)
                + pdb_record("HETATM", 3, "C1'", "DE", "A", 2, element="C")
                + pdb_record("HETATM", 4, "MG", "MG", "A", 50, element="MG")
            )
            assessment = inspect_pdb(
                source, polymer_ligand_codes={"DA", "DE"}
            )
            self.assertEqual(assessment.polymer_residue_count, 2)
            self.assertEqual(assessment.modified_polymer_residue_count, 1)
            self.assertEqual(assessment.modified_polymer_atom_count, 2)
            self.assertEqual(assessment.nonpolymer_hetero_residue_count, 1)
            self.assertEqual(assessment.polymer_residue_ids_by_chain, {"A": ["1", "2"]})


if __name__ == "__main__":
    unittest.main()
