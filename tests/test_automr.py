import json
import tempfile
import unittest
from pathlib import Path

from nasolve.automr import AutoMRInputError, prepare_automr

from .helpers import make_dataset, make_mtz_dump, model_text


VALID = {"1AP", "DT", "DA", "A", "5IU", "DG", "DC", "DF"}


class AutoMRPreflightTests(unittest.TestCase):
    def test_nonstandard_preflight_generates_input_and_run_records(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = make_dataset(Path(directory))
            result = prepare_automr(dataset, valid_ligand_codes=VALID)
            self.assertEqual(result.status, "READY")
            self.assertTrue(result.generated_config)
            self.assertEqual(result.run_directory.name, "run_001")
            self.assertTrue((dataset / "nasolve.txt").is_file())
            for relative in (
                "nasolve.input.txt", "automr.log", "report.json",
                "Model/input_model.pdb", "Model/assessment.json",
            ):
                self.assertTrue((result.run_directory / relative).is_file(), relative)
            report = json.loads(result.report_path.read_text())
            self.assertFalse(report["execution"]["phaser_ran"])
            self.assertTrue(report["model_assessment"]["heteroatoms_preserved"])

            second = prepare_automr(dataset, valid_ligand_codes=VALID)
            self.assertEqual(second.run_directory.name, "run_002")
            self.assertFalse(second.generated_config)

    def test_standard_pair_records_post_mr_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = make_dataset(root / "dataset", include_model=False)
            frames = root / "frames"
            catalogue = frames / "5W6W"
            catalogue.mkdir(parents=True)
            (catalogue / "C_G.pdb").write_text(model_text())
            result = prepare_automr(
                dataset, frame_override="W", pair_override="D:T",
                frames_dir=frames, valid_ligand_codes=VALID,
                mtz_dump_executable=make_mtz_dump(root),
            )
            self.assertEqual(result.status, "READY_POST_MR_MUTATION")
            report = json.loads(result.report_path.read_text())
            self.assertEqual(
                report["post_mr_plan"]["standard_pair"]["ligand_codes"],
                ["1AP", "DT"],
            )
            self.assertFalse(
                report["post_mr_plan"]["standard_pair"]["exact_model_match"]
            )

    def test_exact_standard_pair_model_is_ready_without_pair_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = make_dataset(root / "dataset", include_model=False)
            catalogue = root / "frames" / "5W6W"
            catalogue.mkdir(parents=True)
            (catalogue / "C_G.pdb").write_text(model_text())
            (catalogue / "A_G.pdb").write_text(model_text())
            result = prepare_automr(
                dataset, frame_override="W", pair_override="A:G",
                frames_dir=root / "frames", valid_ligand_codes=VALID,
                mtz_dump_executable=make_mtz_dump(root),
            )
            self.assertEqual(result.status, "READY")
            report = json.loads(result.report_path.read_text())
            self.assertEqual(Path(report["inputs"]["model"]).name, "A_G.pdb")
            self.assertTrue(
                report["post_mr_plan"]["standard_pair"]["exact_model_match"]
            )

    def test_p1_standard_is_blocked_unless_explicitly_shunted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = make_dataset(root / "dataset", include_model=False)
            (dataset / "data_1.cif").write_text(
                "data_test\n_symmetry.space_group_name_H-M 'P 1'\n"
            )
            (dataset / "summary.html").write_text("Spacegroup name P1\n")
            catalogue = root / "frames" / "5W6W"
            catalogue.mkdir(parents=True)
            (catalogue / "C_G.pdb").write_text(model_text())
            dump = make_mtz_dump(root, "P 1", 1)
            with self.assertRaisesRegex(AutoMRInputError, "three MR copies"):
                prepare_automr(
                    dataset, frame_override="W", pair_override="D:T",
                    frames_dir=root / "frames", valid_ligand_codes=VALID,
                    mtz_dump_executable=dump,
                )
            result = prepare_automr(
                dataset, frame_override="W", pair_override="D:T",
                frames_dir=root / "frames", valid_ligand_codes=VALID,
                mtz_dump_executable=dump, allow_p1_standard=True,
            )
            self.assertEqual(result.status, "READY_WITH_RED_FLAG")
            report = json.loads(result.report_path.read_text())
            self.assertEqual(report["symmetry"]["mr_copies"], 3)
            self.assertIn(
                "allow_p1_standard = true", (dataset / "nasolve.txt").read_text()
            )

    def test_sequence_length_and_mutation_target_are_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = make_dataset(Path(directory))
            config = dataset / "nasolve.txt"
            config.write_text(
                "[automr]\nmode = nonstandard\nmodel = search.pdb\n"
                "[sequences]\nA = A\n"
            )
            with self.assertRaisesRegex(AutoMRInputError, "has length 1"):
                prepare_automr(dataset, valid_ligand_codes=VALID)
            config.write_text(
                "[automr]\nmode = nonstandard\nmodel = search.pdb\n"
                "[mutations]\nA:99 = 5IU\n"
            )
            with self.assertRaisesRegex(AutoMRInputError, "does not exist"):
                prepare_automr(dataset, valid_ligand_codes=VALID)


if __name__ == "__main__":
    unittest.main()
