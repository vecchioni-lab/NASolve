import json
import shutil
import tempfile
import unittest
from pathlib import Path

from nasolve.postmr import PostMRPreparationError, prepare_postmr, residue_name

from .helpers import make_postmr_report, make_ready_set, pdb_record


def postmr_model_text() -> str:
    return "".join([
        pdb_record("HETATM", 1, "P", "DE", "A", 12),
        pdb_record("ATOM", 2, "P", "DG", "B", 4),
        pdb_record("HETATM", 3, "MG", "MG", "A", 50, element="MG"),
        "END\n",
    ])


def make_data_root(root: Path) -> Path:
    data = root / "data"
    ligands = data / "ligands"
    restraints = data / "restraints"
    ligands.mkdir(parents=True)
    restraints.mkdir()
    (ligands / "8RO.cif").write_text(
        "data_comp_8RO\nloop_\n_chem_comp_bond.comp_id\n"
        "_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n"
        "8RO C4 S4\n"
    )
    package = Path(__file__).parents[1] / "src" / "nasolve" / "data" / "restraints"
    for name in ("5W6W_Std_padd.txt", "5W6W_secondary_structure.eff"):
        shutil.copyfile(package / name, restraints / name)
    return data


class PostMRTests(unittest.TestCase):
    def test_w_frame_normalizes_8ro_and_runs_readyset_without_coot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdb"
            source.write_text(postmr_model_text())
            run = root / "run_004"
            make_postmr_report(run, source)
            calls = []

            def fake_builder(pdb: Path, pairs: Path, output: Path) -> None:
                calls.append((pdb.read_text(), pairs.read_text()))
                output.write_text("geometry_restraints.edits {}\n")

            result = prepare_postmr(
                run,
                make_ready_set(root),
                data_root=make_data_root(root),
                narestraints_builder=fake_builder,
            )
            self.assertEqual(result.status, "POSTMR_READY")
            self.assertEqual(residue_name(result.model_path, "A:12"), "8RO")
            self.assertEqual(residue_name(result.model_path, "B:4"), "DG")
            self.assertIn(" DE ", calls[0][0])
            self.assertNotIn("8RO", calls[0][0])
            self.assertEqual(calls[0][1], "A 11:13\nB 5:3\n")
            self.assertFalse((result.postmr_directory / "Coot" / "coot.log").exists())
            readyset = (result.postmr_directory / "ReadySet" / "ready_set.log").read_text()
            self.assertIn("user provided restraints", readyset)
            report = json.loads((run / "report.json").read_text())
            self.assertEqual(report["stage"], "postmr")
            self.assertEqual(report["postmr"]["mutation_actions"][0]["method"], "curated-label-normalization")

    def test_secondary_template_has_base_pairs_but_no_stacking_pairs(self):
        template = (
            Path(__file__).parents[1]
            / "src" / "nasolve" / "data" / "restraints"
            / "5W6W_secondary_structure.eff"
        ).read_text()
        self.assertEqual(template.count("base_pair {"), 17)
        self.assertNotIn("stacking_pair", template)
        self.assertNotIn("file_name", template)
        self.assertNotIn("unit_cell", template)

    def test_legacy_e_de_report_is_migrated_to_curated_8ro(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdb"
            source.write_text(postmr_model_text())
            run = root / "run_legacy"
            make_postmr_report(run, source, first="DE")

            def fake_builder(_pdb: Path, _pairs: Path, output: Path) -> None:
                output.write_text("geometry_restraints.edits {}\n")

            result = prepare_postmr(
                run,
                make_ready_set(root),
                data_root=make_data_root(root),
                narestraints_builder=fake_builder,
            )
            self.assertEqual(residue_name(result.model_path, "A:12"), "8RO")

    def test_review_result_requires_explicit_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdb"
            source.write_text(postmr_model_text())
            run = root / "run"
            report_path = make_postmr_report(run, source)
            report = json.loads(report_path.read_text())
            report["status"] = "MR_REVIEW"
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(PostMRPreparationError, "--allow-mr-review"):
                prepare_postmr(
                    run,
                    make_ready_set(root),
                    data_root=make_data_root(root),
                    narestraints_builder=lambda *_: None,
                )


if __name__ == "__main__":
    unittest.main()
