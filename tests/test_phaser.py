import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nasolve.automr import prepare_automr
from nasolve.phaser import (
    PhaserExecutionError, execute_phaser, parse_best_tfz, parse_selected_solution_scores,
)

from .helpers import make_dataset, make_mtz_dump, make_phaser, model_text, w_model_text


VALID = {"DA", "DC"}


class PhaserExecutionTests(unittest.TestCase):
    def _preflight(self, root: Path):
        dataset = make_dataset(root / "dataset")
        return prepare_automr(dataset, valid_ligand_codes=VALID)

    def test_one_ensemble_uses_checker_residue_count_and_preserves_hetatm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preflight = self._preflight(root)
            result = execute_phaser(
                preflight.report_path, make_phaser(root), phenix_version="1.20.1"
            )
            self.assertEqual(result.status, "MR_SUCCESS")
            self.assertEqual(result.exit_code, 0)
            eff = result.parameter_path.read_text()
            self.assertEqual(eff.count("  ensemble {"), 1)
            self.assertNotIn("\n  model =", eff)
            self.assertIn("model_id = nasolve_model", eff)
            self.assertIn("ensembles = nasolve_model", eff)
            self.assertIn("use_hetatm = True", eff)
            self.assertIn("rmsd = 1.0", eff)
            self.assertNotIn("identity =", eff)
            self.assertIn("nres = 2", eff)
            self.assertIn("copies = 1", eff)
            self.assertTrue(result.solution_pdb.is_file())
            self.assertTrue(result.solution_mtz.is_file())
            report = json.loads(result.report_path.read_text())
            self.assertEqual(report["execution"]["phaser"]["ensemble_count"], 1)
            self.assertEqual(report["execution"]["phaser"]["model_rmsd"], 1.0)
            self.assertEqual(report["execution"]["phaser"]["composition_nres"], 2)

    def test_preflight_inputs_rebase_after_checkout_moves(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preflight = self._preflight(root / "collaborator")
            source_dataset = preflight.run_directory.parent.parent
            checkout_dataset = root / "checkout" / source_dataset.name
            shutil.copytree(source_dataset, checkout_dataset)
            shutil.rmtree(root / "collaborator")
            report_path = (
                checkout_dataset / "AutoMR" / preflight.run_directory.name / "report.json"
            )

            result = execute_phaser(
                report_path,
                make_phaser(root),
                phenix_version="1.20.1",
            )

            self.assertEqual(result.status, "MR_SUCCESS")
            parameters = result.parameter_path.read_text()
            self.assertIn(str(checkout_dataset.resolve()), parameters)

    def test_relocated_preflight_rejects_changed_local_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preflight = self._preflight(root / "collaborator")
            source_dataset = preflight.run_directory.parent.parent
            checkout_dataset = root / "checkout" / source_dataset.name
            shutil.copytree(source_dataset, checkout_dataset)
            run = checkout_dataset / "AutoMR" / preflight.run_directory.name
            (run / "Model" / "input_model.pdb").write_text("changed\n")

            with self.assertRaisesRegex(PhaserExecutionError, "recorded checksum"):
                execute_phaser(
                    run / "report.json",
                    make_phaser(root),
                    phenix_version="1.20.1",
                )

    def test_preflight_records_and_checks_authoritative_reflections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preflight = self._preflight(root)
            report = json.loads(preflight.report_path.read_text())
            self.assertRegex(report["inputs"]["reflections_sha256"], r"^[0-9a-f]{64}$")
            Path(report["inputs"]["reflections"]).write_bytes(b"changed")

            with self.assertRaisesRegex(PhaserExecutionError, "reflections"):
                execute_phaser(preflight.report_path, make_phaser(root))

    def test_tfz_review_and_failure_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review = self._preflight(root / "review")
            reviewed = execute_phaser(review.report_path, make_phaser(root / "review", 7.5))
            self.assertEqual((reviewed.status, reviewed.exit_code), ("MR_REVIEW", 3))

            failed = self._preflight(root / "fail")
            failure = execute_phaser(failed.report_path, make_phaser(root / "fail", 6.9))
            self.assertEqual((failure.status, failure.exit_code), ("MR_FAILED", 4))

    def test_p1_shunt_uses_three_composition_and_search_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = make_dataset(root / "dataset", include_model=False)
            (dataset / "data_1.cif").write_text(
                "data_test\n_symmetry.space_group_name_H-M 'P 1'\n"
            )
            (dataset / "summary.html").write_text("Spacegroup name P1\n")
            catalogue = root / "frames" / "5W6W"
            catalogue.mkdir(parents=True)
            (catalogue / "C_G.pdb").write_text(w_model_text())
            preflight = prepare_automr(
                dataset,
                frame_override="W",
                pair_override="D:T",
                frames_dir=root / "frames",
                allow_p1_standard=True,
                mtz_dump_executable=make_mtz_dump(root, "P 1", 1),
                valid_ligand_codes={"1AP", "DT", "DC", "DG"},
            )
            result = execute_phaser(preflight.report_path, make_phaser(root))
            eff = result.parameter_path.read_text()
            self.assertIn("num = 3", eff)
            self.assertIn("copies = 3", eff)
            self.assertEqual(eff.count("  ensemble {"), 1)

    def test_missing_tfz_or_outputs_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing_tfz = self._preflight(root / "tfz")
            result = execute_phaser(
                missing_tfz.report_path, make_phaser(root / "tfz", None)
            )
            self.assertEqual(result.status, "MR_FAILED")
            self.assertIn("did not report a TFZ", result.message)

            missing_outputs = self._preflight(root / "outputs")
            result = execute_phaser(
                missing_outputs.report_path,
                make_phaser(root / "outputs", 8.4, create_outputs=False),
            )
            self.assertEqual(result.status, "MR_FAILED")
            self.assertIn("both PDB and MTZ", result.message)

    def test_existing_phaser_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preflight = self._preflight(root)
            (preflight.run_directory / "Phaser").mkdir()
            with self.assertRaisesRegex(PhaserExecutionError, "refusing to overwrite"):
                execute_phaser(preflight.report_path, make_phaser(root))

    def test_parser_prefers_best_solu_set(self):
        text = "\n".join([
            "intermediate TFZ=99.0",
            "SOLU SET RFZ=5.0 TFZ=7.2 LLG=50",
            "SOLU SET RFZ=8.0 TFZ==8.6 LLG=125.5",
        ])
        self.assertEqual(parse_best_tfz(text), (8.6, 125.5))

    def test_native_annotation_histories_use_final_model_scores(self):
        # Sanitized Phaser 2.9/Phenix 2.2.1 annotation-only evidence: no models,
        # coordinates, observations, machine paths or project identifiers.
        histories = [
            ("RFZ=11.1 TFZ=7.4 PAK=0 LLG=371 TFZ==9.9 LLG=692 TFZ==14.5 PAK=0 LLG=692 TFZ==14.5", 14.5, 692),
            ("RFZ=8.2 TFZ=5.1 PAK=1 LLG=304 TFZ==10.8 LLG=353 TFZ==12.2 PAK=0 LLG=353 TFZ==12.2", 12.2, 353),
            ("RFZ=7.2 TFZ=7.8 PAK=0 LLG=202 TFZ==7.6 LLG=227 TFZ==7.7 PAK=0 LLG=226 TFZ==7.7", 7.7, 226),
            ("RFZ=5.5 TFZ=6.2 PAK=1 LLG=172 TFZ==7.9 LLG=176 TFZ==8.0 PAK=1 LLG=176 TFZ==8.0", 8.0, 176),
            ("RFZ=6.1 TFZ=9.9 PAK=0 LLG=225 TFZ==11.1 LLG=299 TFZ==13.8 PAK=0 LLG=299 TFZ==13.8", 13.8, 299),
            ("RFZ=13.6 TFZ=* PAK=0 LLG=323 TFZ==15.2 LLG=368 TFZ==16.9 PAK=0 LLG=367 TFZ==16.9", 16.9, 367),
            ("RFZ=13.1 TFZ=* PAK=1 LLG=396 TFZ==15.2 LLG=417 TFZ==15.3 PAK=1 LLG=417 TFZ==15.3", 15.3, 417),
            ("RFZ=10.6 TFZ=6.1 PAK=0 LLG=384 TFZ==8.8 LLG=414 TFZ==9.8 PAK=0 LLG=414 TFZ==9.8", 9.8, 414),
        ]
        for history, tfz, llg in histories:
            with self.subTest(history=history):
                result = parse_selected_solution_scores("REMARK  " + history + "\nEND\n")
                self.assertEqual((result["tfz"], result["llg"]), (tfz, llg))
                self.assertEqual(result["score_kind"], "tfz-equivalent")
                self.assertEqual(parse_best_tfz("SOLU SET " + history), (tfz, llg))

    def _selected_fixture(self, root, files, text):
        preflight = self._preflight(root)
        executable = make_phaser(root)

        def external(command, **kwargs):
            for name, contents in files.items():
                (kwargs["cwd"] / name).write_text(contents)
            return subprocess.CompletedProcess(command, 0, text)

        with patch("nasolve.phaser.subprocess.run", side_effect=external):
            return execute_phaser(preflight.report_path, executable, phenix_version="2.2.1")

    def test_execution_uses_selected_pdb_final_score_not_other_solution_or_history(self):
        with tempfile.TemporaryDirectory() as directory:
            header = "REMARK RFZ=7 TFZ=5.1 LLG=30 TFZ==12.2 LLG=45 TFZ==7.7 LLG=44\n"
            result = self._selected_fixture(Path(directory), {
                "PHASER.1.pdb": header + "END\n", "PHASER.1.mtz": "first",
                "PHASER.2.pdb": "REMARK TFZ==18.0 LLG=120\nEND\n", "PHASER.2.mtz": "second",
            }, "SOLU SET TFZ==18 LLG=120\nSOLU SET TFZ=99 LLG=999\n")
            self.assertEqual((result.status, result.tfz, result.llg), ("MR_REVIEW", 7.7, 44.0))
            self.assertEqual(result.solution_mtz.read_text(), "first")
            record = json.loads(result.report_path.read_text())["execution"]["phaser"]
            evidence = record["score_evidence"]
            self.assertEqual(evidence["method"], "selected-pdb-remark")
            self.assertEqual(evidence["score_kind"], "tfz-equivalent")
            self.assertEqual(evidence["raw_annotations"], [header.strip()])
            self.assertEqual(evidence["source"]["anchor"], "run")
            self.assertEqual(evidence["source"]["relative_path"], "Phaser/PHASER.1.pdb")
            self.assertRegex(evidence["source"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(record["solution_pdb_sha256"], evidence["source"]["sha256"])

    def test_invalid_selected_annotation_never_falls_back_to_high_log_score(self):
        for invalid in ("*", "nan", "1e999", "12.2oops"):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                result = self._selected_fixture(Path(directory), {
                    "PHASER.1.pdb": f"REMARK TFZ=5.1 LLG=10 TFZ=={invalid} LLG=20\nEND\n",
                    "PHASER.1.mtz": "map",
                }, "SOLU SET TFZ=99 LLG=999\n")
                self.assertEqual(result.status, "MR_FAILED")
                self.assertIsNone(result.tfz)
                evidence = json.loads(result.report_path.read_text())["execution"]["phaser"]["score_evidence"]
                self.assertEqual(evidence["status"], "INVALID")

    def test_conflicting_selected_annotation_fails_without_log_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._selected_fixture(Path(directory), {
                "PHASER.1.pdb": "REMARK TFZ==8.2 LLG=100\nREMARK TFZ==6.2 LLG=90\nEND\n",
                "PHASER.1.mtz": "map",
            }, "SOLU SET TFZ=99 LLG=999\n")
            self.assertEqual(result.status, "MR_FAILED")
            self.assertIsNone(result.tfz)

    def test_selected_pdb_cannot_borrow_another_numbered_mtz(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._selected_fixture(Path(directory), {
                "PHASER.1.pdb": "REMARK TFZ==12.2 LLG=353\nEND\n",
                "PHASER.2.mtz": "wrong map",
            }, "SOLU SET TFZ==12.2 LLG=353\n")
            self.assertEqual(result.status, "MR_FAILED")
            self.assertIsNone(result.solution_mtz)
            self.assertFalse((result.phaser_directory / "mr_solution.mtz").exists())
            self.assertIn("same selected solution", result.message)

    def test_unannotated_single_output_retains_unambiguous_log_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._selected_fixture(Path(directory), {
                "PHASER.1.pdb": "MODEL\nEND\n", "PHASER.1.mtz": "map",
            }, "SOLU SET TFZ=5.1 LLG=304 TFZ==12.2 LLG=353\n")
            self.assertEqual((result.status, result.tfz, result.llg), ("MR_SUCCESS", 12.2, 353.0))
            evidence = json.loads(result.report_path.read_text())["execution"]["phaser"]["score_evidence"]
            self.assertEqual(evidence["method"], "single-output-single-annotation-log-compatibility")

    def test_unannotated_output_cannot_choose_between_log_solutions(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._selected_fixture(Path(directory), {
                "PHASER.1.pdb": "MODEL\nEND\n", "PHASER.1.mtz": "map",
            }, "SOLU SET TFZ==6.2 LLG=50\nSOLU SET TFZ==12.2 LLG=100\n")
            self.assertEqual(result.status, "MR_FAILED")
            self.assertIsNone(result.tfz)

    def test_no_selected_model_keeps_candidate_log_scores_nonauthoritative(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._selected_fixture(Path(directory), {}, "intermediate TFZ=2.9\nNo solution\n")
            self.assertEqual(result.status, "MR_FAILED")
            self.assertIsNone(result.tfz)
            self.assertIsNone(result.llg)
            evidence = json.loads(result.report_path.read_text())["execution"]["phaser"]["score_evidence"]
            self.assertEqual(evidence["status"], "NO_SELECTED_MODEL")


if __name__ == "__main__":
    unittest.main()
