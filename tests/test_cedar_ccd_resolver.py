"""Cedar regression: generic Phenix CCD sources, no new chemistry catalogue."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nasolve.curated_ligands import (
    CURATED_LIGANDS,
    PDB_DEPOSITION_ALIASES,
    ligand_data_directory,
    ligand_definition,
    ligand_dictionary,
    validate_ligand_dictionary,
)
from nasolve.ligand_profiles import _parameterized_codes
from nasolve.postmr import (
    MutationAction,
    PostMRPreparationError,
    _coot_script,
    _require_generic_parameterization,
)


def ccd_text(code: str, *, parameterized: bool = False) -> str:
    """Small, parseable CCD-shaped graph with optional numerical targets."""
    if parameterized:
        return (
            f"data_comp_{code}\n"
            f"_chem_comp.id {code}\n"
            "loop_\n_chem_comp_atom.comp_id\n"
            "_chem_comp_atom.atom_id\n_chem_comp_atom.type_energy\n"
            f"{code} C1 C\n{code} N1 N\n#\n"
            "loop_\n_chem_comp_bond.comp_id\n"
            "_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n"
            "_chem_comp_bond.value_dist\n_chem_comp_bond.value_dist_esd\n"
            f"{code} C1 N1 1.42 0.02\n#\n"
        )
    return (
        f"data_comp_{code}\n"
        f"_chem_comp.id {code}\n"
        "loop_\n_chem_comp_atom.comp_id\n"
        "_chem_comp_atom.atom_id\n_chem_comp_atom.type_symbol\n"
        f"{code} C1 C\n{code} N1 N\n#\n"
        "loop_\n_chem_comp_bond.comp_id\n"
        "_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n"
        f"{code} C1 N1\n#\n"
    )


class CedarCCDResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.phenix = self.root / "phenix"
        self.executable = self.phenix / "bin" / "phenix.ready_set"
        self.executable.parent.mkdir(parents=True)
        self.executable.write_text("test executable placeholder\n")
        self.data_root = self.root / "nasolve_data"
        (self.data_root / "ligands").mkdir(parents=True)

    def ccd(self, code: str, python_version: str = "3.11", *,
            identity: str | None = None) -> Path:
        path = (
            self.phenix / "lib" / f"python{python_version}" / "site-packages"
            / "chem_data" / "chemical_components" / code[0].lower()
            / f"data_{code}.cif"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ccd_text(identity or code))
        return path

    def test_four_reviewed_families_resolve_without_curating(self) -> None:
        for code in ("IGU", "IMC", "CGY", "DX"):
            with self.subTest(code=code):
                expected = self.ccd(code)
                found = ligand_dictionary(
                    code, self.data_root, ready_set_executable=self.executable
                )
                self.assertEqual(found, expected.resolve())
                validate_ligand_dictionary(code, found)
                self.assertNotIn(code, _parameterized_codes(found))

    def test_local_generic_dictionary_takes_precedence(self) -> None:
        self.ccd("IGU")
        override = self.data_root / "ligands" / "IGU.cif"
        override.write_text(ccd_text("IGU", parameterized=True))
        found = ligand_dictionary(
            "IGU", self.data_root, ready_set_executable=self.executable
        )
        self.assertEqual(found, override)
        self.assertIn("IGU", _parameterized_codes(found))

    def test_missing_reviewed_curated_dictionary_never_falls_back(self) -> None:
        self.ccd("1AP")
        with self.assertRaisesRegex(FileNotFoundError, "Curated dictionary"):
            ligand_dictionary(
                "1AP", self.data_root, ready_set_executable=self.executable
            )

    def test_every_curated_cif_wins_even_when_phenix_has_competing_ccd(self) -> None:
        """Nine known problem residues must always use their reviewed CIFs.

        Check the actual bundled sources, chemical validation, and the Coot
        script that loads each source before parent-overlap reconstruction.
        """
        self.assertEqual(
            set(CURATED_LIGANDS),
            {"1AP", "DE", "DF", "S6G", "C38", "5IU", "5CM", "DZ", "DP"},
        )
        chosen: dict[str, Path] = {}
        fake_ccds: dict[str, Path] = {}
        actions: list[MutationAction] = []
        parents: dict[str, Path] = {}
        for index, code in enumerate(sorted(CURATED_LIGANDS), start=1):
            with self.subTest(code=code):
                fake_ccds[code] = self.ccd(code)
                path = ligand_dictionary(
                    code, ready_set_executable=self.executable
                )
                expected = ligand_data_directory() / CURATED_LIGANDS[code].dictionary_filename
                self.assertEqual(path.resolve(), expected.resolve())
                self.assertTrue(path.is_file(), f"Missing reviewed source for {code}")
                validate_ligand_dictionary(code, path)
                self.assertNotEqual(path.resolve(), fake_ccds[code].resolve())
                chosen[code] = path
                ligand = ligand_definition(code)
                site = f"A:{index}"
                actions.append(MutationAction(
                    site, ligand.parent_code, code, "coot-parent-overlap",
                    parent_code=ligand.parent_code,
                    deposition_code=ligand.deposition_code,
                ))
                parents[site] = self.root / f"parent_{code}.pdb"
        script = _coot_script(
            self.root / "source.pdb", self.root / "after_coot.pdb",
            tuple(actions), chosen, parents,
        )
        for code, source in chosen.items():
            with self.subTest(coot_code=code):
                self.assertIn(
                    f"coot.read_cif_dictionary({json.dumps(str(source))})",
                    script,
                )
                self.assertIn(
                    f"coot.get_monomer_from_dictionary({code!r}, 0)", script
                )
                self.assertNotIn(str(fake_ccds[code]), script)

    def test_missing_any_curated_cif_never_falls_back_to_phenix(self) -> None:
        """The known-problem library is not an optional overlay."""
        for code in sorted(CURATED_LIGANDS):
            with self.subTest(code=code):
                self.ccd(code)
                with self.assertRaisesRegex(
                    FileNotFoundError, f"Curated dictionary for {code} is missing"
                ):
                    ligand_dictionary(
                        code, self.data_root,
                        ready_set_executable=self.executable,
                    )

    def test_wrong_reviewed_local_chemistry_stops_instead_of_using_ccd(self) -> None:
        """Even with a matching component ID, DE must retain C4-S4 topology."""
        self.ccd("DE")
        invalid = self.data_root / "ligands" / "DE.cif"
        invalid.write_text(ccd_text("DE"))
        source = ligand_dictionary(
            "DE", self.data_root, ready_set_executable=self.executable
        )
        self.assertEqual(source, invalid)
        with self.assertRaisesRegex(ValueError, "C4-S4"):
            validate_ligand_dictionary("DE", source)

    def test_local_ohu_is_preserved_without_making_it_curated(self) -> None:
        """Existing OHU local data path is separate from the reviewed exceptions."""
        self.assertNotIn("OHU", CURATED_LIGANDS)
        competing = self.ccd("OHU")
        source = ligand_dictionary("OHU", ready_set_executable=self.executable)
        self.assertEqual(source.resolve(), (ligand_data_directory() / "OHU.cif").resolve())
        self.assertNotEqual(source.resolve(), competing.resolve())
        validate_ligand_dictionary("OHU", source)

    def test_de_and_df_deposition_identity_bridges_are_unchanged(self) -> None:
        self.assertEqual(PDB_DEPOSITION_ALIASES["A1AAZ"], "DF")
        self.assertEqual(ligand_definition("DF").deposition_code, "A1AAZ")
        self.assertEqual(ligand_definition("DF").parent_code, "DT")
        self.assertEqual(ligand_definition("DE").parent_code, "DT")
        self.assertNotIn("8RO", CURATED_LIGANDS)

    def test_mismatched_component_id_fails_after_discovery(self) -> None:
        self.ccd("IGU", identity="IMC")
        source = ligand_dictionary(
            "IGU", self.data_root, ready_set_executable=self.executable
        )
        with self.assertRaisesRegex(ValueError, "does not declare"):
            validate_ligand_dictionary("IGU", source)

    def test_absent_or_ambiguous_phenix_ccd_fails_closed(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "Expected one Phenix CCD"):
            ligand_dictionary("IGU", self.data_root, ready_set_executable=self.executable)
        self.ccd("IGU", "3.11")
        self.ccd("IGU", "3.12")
        with self.assertRaisesRegex(FileNotFoundError, "found 2"):
            ligand_dictionary("IGU", self.data_root, ready_set_executable=self.executable)

    def test_missing_executable_does_not_guess_other_installations(self) -> None:
        self.ccd("IGU")
        with self.assertRaisesRegex(FileNotFoundError, "was not supplied"):
            ligand_dictionary("IGU", self.data_root)


class GenericParameterizationTests(unittest.TestCase):
    def test_raw_ccd_without_readyset_numerical_restraints_is_blocked(self) -> None:
        with self.assertRaisesRegex(
            PostMRPreparationError, "parameterized ligand restraints for IGU"
        ):
            _require_generic_parameterization(
                {"IGU": {"parameterized": False}},
                None,
                Path("/tmp/readyset.log"),
            )

    def test_generated_numerical_restraints_allow_generic_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / "generated.cif"
            generated.write_text(ccd_text("IGU", parameterized=True))
            self.assertIn("IGU", _parameterized_codes(generated))
            _require_generic_parameterization(
                {"IGU": {"parameterized": False}},
                generated,
                Path(tmp) / "readyset.log",
            )

    def test_another_component_cannot_satisfy_missing_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / "wrong.cif"
            generated.write_text(ccd_text("IMC", parameterized=True))
            with self.assertRaisesRegex(
                PostMRPreparationError, "parameterized ligand restraints for IGU"
            ):
                _require_generic_parameterization(
                    {"IGU": {"parameterized": False}},
                    generated,
                    Path(tmp) / "readyset.log",
                )

    def test_parameterized_inputs_and_curated_chemistry_are_unchanged(self) -> None:
        _require_generic_parameterization(
            {"IGU": {"parameterized": True}, "1AP": {"parameterized": False}},
            None,
            Path("/tmp/readyset.log"),
        )


if __name__ == "__main__":
    unittest.main()
