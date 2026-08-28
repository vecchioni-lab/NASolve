import tempfile
import unittest
from pathlib import Path

from nasolve.automr_input import (
    AutoMRInputError,
    AutoMRIntent,
    format_intent,
    read_intent,
    read_sequence_file,
    resolve_automr_input,
)

from .helpers import make_dataset, model_text


VALID = {"1AP", "DT", "DA", "A", "5IU", "DG", "DC", "DF", "DE"}


class AutoMRInputTests(unittest.TestCase):
    def test_autoproc_staraniso_dataset_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "staraniso_alldata-unique.mtz").write_bytes(b"mtz")
            (root / "Data_1_autoPROC_STARANISO_all.cif").write_text("data_test\n")
            (root / "summary.html").write_text("<html></html>\n")
            (root / "search.pdb").write_text(model_text())
            resolved = resolve_automr_input(
                root, AutoMRIntent(), valid_ligand_codes=VALID
            )
            self.assertEqual(resolved.dataset.reflections.name, "staraniso_alldata-unique.mtz")
            self.assertEqual(
                resolved.dataset.metadata.name, "Data_1_autoPROC_STARANISO_all.cif"
            )

    def test_multiple_staraniso_all_data_files_bounce(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_dataset(Path(directory))
            (root / "staraniso_alldata-unique.mtz").write_bytes(b"other")
            with self.assertRaisesRegex(AutoMRInputError, "Ambiguous STARANISO"):
                resolve_automr_input(root, AutoMRIntent(), valid_ligand_codes=VALID)

    def test_standard_frame_and_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset = make_dataset(base / "dataset", include_model=False)
            frames = base / "MR_frames"
            catalogue = frames / "5W6W"
            catalogue.mkdir(parents=True)
            (catalogue / "C_G.pdb").write_text(model_text())
            resolved = resolve_automr_input(
                dataset,
                AutoMRIntent(mode="standard", frame="5W6W", pair="D:T"),
                frames_dir=frames,
                valid_ligand_codes=VALID,
            )
            self.assertEqual(resolved.frame.name, "W")
            self.assertEqual(resolved.model.name, "C_G.pdb")
            self.assertFalse(resolved.exact_pair_model)
            self.assertEqual(
                tuple(item.ligand_code for item in resolved.pair), ("1AP", "DT")
            )

    def test_catalogue_matches_resolved_codes_not_only_spelling(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset = make_dataset(base / "dataset", include_model=False)
            catalogue = base / "MR_frames" / "5W6W"
            catalogue.mkdir(parents=True)
            (catalogue / "C_G.pdb").write_text(model_text())
            (catalogue / "D_F.pdb").write_text(model_text())
            resolved = resolve_automr_input(
                dataset,
                AutoMRIntent(mode="standard", frame="W", pair="1AP:DF"),
                frames_dir=base / "MR_frames",
                valid_ligand_codes=VALID,
            )
            self.assertEqual(resolved.model.name, "D_F.pdb")
            self.assertTrue(resolved.exact_pair_model)

    def test_unrelated_unknown_catalogue_token_is_a_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset = make_dataset(base / "dataset", include_model=False)
            catalogue = base / "MR_frames" / "5W6W"
            catalogue.mkdir(parents=True)
            (catalogue / "C_G.pdb").write_text(model_text())
            (catalogue / "E_G.pdb").write_text(model_text())
            (catalogue / "D33_D33.pdb").write_text(model_text())
            resolved = resolve_automr_input(
                dataset,
                AutoMRIntent(mode="standard", frame="W", pair="E:G"),
                frames_dir=base / "MR_frames",
                valid_ligand_codes=VALID,
            )
            self.assertEqual(resolved.model.name, "E_G.pdb")
            self.assertTrue(resolved.exact_pair_model)
            self.assertRegex(resolved.catalogue_warnings[0], "D33")

    def test_3gbi_uses_c_c_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset = make_dataset(base / "dataset", include_model=False)
            catalogue = base / "MR_frames" / "3GBI"
            catalogue.mkdir(parents=True)
            (catalogue / "C_C.pdb").write_text(model_text())
            resolved = resolve_automr_input(
                dataset,
                AutoMRIntent(mode="standard", frame="3GBI", pair="D:T"),
                frames_dir=base / "MR_frames",
                valid_ligand_codes=VALID,
            )
            self.assertEqual(resolved.model.name, "C_C.pdb")
            self.assertFalse(resolved.exact_pair_model)

    def test_nonstandard_discovers_one_top_level_pdb(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = make_dataset(Path(directory))
            resolved = resolve_automr_input(
                dataset, AutoMRIntent(), valid_ligand_codes=VALID
            )
            self.assertEqual(resolved.mode, "nonstandard")
            self.assertEqual(resolved.model.name, "search.pdb")

    def test_nonstandard_missing_and_ambiguous_models_bounce(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = make_dataset(root, include_model=False)
            with self.assertRaisesRegex(AutoMRInputError, "MODEL_REQUIRED"):
                resolve_automr_input(dataset, AutoMRIntent(), valid_ligand_codes=VALID)
            (root / "one.pdb").write_text(model_text())
            (root / "two.pdb").write_text(model_text())
            with self.assertRaisesRegex(AutoMRInputError, "Ambiguous"):
                resolve_automr_input(dataset, AutoMRIntent(), valid_ligand_codes=VALID)

    def test_shared_file_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "nasolve.txt"
            path.write_text(
                "[automr]\nmode = nonstandard\nmodel = models/search.pdb\nmirror = true\n\n"
                "[sequences]\nA = AC\n\n[mutations]\nA:2 = 5IU\n"
            )
            intent = read_intent(path)
            self.assertEqual(intent.model, "models/search.pdb")
            self.assertTrue(intent.mirror)
            self.assertEqual(intent.sequences, {"A": "AC"})
            self.assertEqual(intent.mutations, {"A:2": "5IU"})

    def test_chain_labelled_sequence_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fasta = root / "construct.fasta"
            fasta.write_text(">A target strand\nACGT\n>B\nTGCA\n")
            self.assertEqual(
                read_sequence_file(fasta),
                {"A": "ACGT", "B": "TGCA"},
            )
            listed = root / "construct.txt"
            listed.write_text("A = ACGT\nB = TGCA\n")
            self.assertEqual(
                read_sequence_file(listed),
                {"A": "ACGT", "B": "TGCA"},
            )

    def test_nonstandard_sequence_file_is_resolved_and_frozen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = make_dataset(root)
            (root / "construct.fasta").write_text(">A\nAC\n")
            config = root / "nasolve.txt"
            config.write_text(
                "[automr]\nmode = nonstandard\nmodel = search.pdb\n"
                "sequence_file = construct.fasta\n"
            )
            resolved = resolve_automr_input(
                dataset,
                read_intent(config),
                valid_ligand_codes=VALID,
            )
            self.assertEqual(resolved.sequences, {"A": "AC"})
            self.assertEqual(resolved.sequence_file, (root / "construct.fasta").resolve())
            effective = format_intent(resolved)
            self.assertIn("[sequences]\nA = AC", effective)
            self.assertNotIn("sequence_file", effective)

    def test_sequence_file_rejects_ambiguous_or_escaping_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = make_dataset(root)
            outside = root.parent / "outside-sequence.fasta"
            outside.write_text(">A\nAC\n")
            try:
                with self.assertRaisesRegex(AutoMRInputError, "remain inside"):
                    resolve_automr_input(
                        dataset,
                        AutoMRIntent(
                            mode="nonstandard",
                            model="search.pdb",
                            sequence_file="../outside-sequence.fasta",
                        ),
                        valid_ligand_codes=VALID,
                    )
                (root / "inside.fasta").write_text(">A\nAC\n")
                with self.assertRaisesRegex(AutoMRInputError, "either"):
                    resolve_automr_input(
                        dataset,
                        AutoMRIntent(
                            mode="nonstandard",
                            model="search.pdb",
                            sequence_file="inside.fasta",
                            sequences={"A": "AC"},
                        ),
                        valid_ligand_codes=VALID,
                    )
            finally:
                outside.unlink(missing_ok=True)

    def test_nonstandard_pair_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = make_dataset(Path(directory))
            with self.assertRaisesRegex(AutoMRInputError, "only valid in standard mode"):
                resolve_automr_input(
                    dataset, AutoMRIntent(pair="D:T"), valid_ligand_codes=VALID
                )

    def test_canonical_nonstandard_model_path_remains_relative(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = make_dataset(root, include_model=False)
            models = root / "models"
            models.mkdir()
            (models / "search.pdb").write_text(model_text())
            resolved = resolve_automr_input(
                dataset,
                AutoMRIntent(mode="nonstandard", model="models/search.pdb"),
                valid_ligand_codes=VALID,
            )
            self.assertIn("model = models/search.pdb", format_intent(resolved))

    def test_mirror_cli_override_is_frozen(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = make_dataset(Path(directory))
            resolved = resolve_automr_input(
                dataset,
                AutoMRIntent(),
                mirror_override=True,
                valid_ligand_codes=VALID,
            )
            self.assertTrue(resolved.mirror)
            self.assertIn("mirror = true", format_intent(resolved))


if __name__ == "__main__":
    unittest.main()
