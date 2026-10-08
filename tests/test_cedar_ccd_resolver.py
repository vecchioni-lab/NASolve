"""Cedar regression: generic Phenix CCD sources, no new chemistry catalogue."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nasolve.curated_ligands import (
    ligand_dictionary,
    validate_ligand_dictionary,
)
from nasolve.ligand_profiles import _parameterized_codes
from nasolve.postmr import (
    PostMRPreparationError,
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
