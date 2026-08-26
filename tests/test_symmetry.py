import tempfile
import unittest
from pathlib import Path

from nasolve.symmetry import SymmetryError, assess_standard_symmetry

from .helpers import make_mtz_dump


class SymmetryTests(unittest.TestCase):
    def files(self, root: Path, cif_symbol: str, summary_symbol: str):
        mtz = root / "data.mtz"
        mtz.write_bytes(b"mtz")
        cif = root / "Data_1.cif"
        cif.write_text(
            "data_one\n"
            f"_symmetry.space_group_name_H-M '{cif_symbol}'\n"
            "data_two\n"
            f"_symmetry.space_group_name_H-M '{cif_symbol}'\n"
        )
        summary = root / "summary.html"
        summary.write_text(
            "Possible space group P1\n"
            "Best Solution: space group H 3 2\n"
            f"Spacegroup name          {summary_symbol}\n"
        )
        return mtz, cif, summary

    def test_h3_and_r3_are_equivalent_and_bottom_summary_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mtz, cif, summary = self.files(root, "R 3", "H3")
            assessment = assess_standard_symmetry(
                mtz, cif, summary,
                make_mtz_dump(root, "H 3", 146, matrix_symbol="R 3 :H"),
            )
            self.assertEqual(assessment.evidence.normalized_class, "H3/R3")
            self.assertEqual(assessment.mr_copies, 1)
            self.assertEqual(assessment.final_output_patch["target_symbol"], "H 3")

    def test_authoritative_disagreement_bounces(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mtz, cif, summary = self.files(root, "P 1", "H3")
            with self.assertRaisesRegex(SymmetryError, "disagree"):
                assess_standard_symmetry(
                    mtz, cif, summary, make_mtz_dump(root, "H 3", 146)
                )


if __name__ == "__main__":
    unittest.main()
