import unittest

from nasolve.residue_aliases import LigandCodeError, resolve_ligand, resolve_pair


VALID = {"1AP", "DT", "DA", "A", "A1AAZ", "DF", "5IU"}


class ResidueAliasTests(unittest.TestCase):
    def test_aliases_are_case_sensitive(self):
        self.assertEqual(resolve_ligand("D", VALID).ligand_code, "1AP")
        self.assertEqual(resolve_ligand("A", VALID).ligand_code, "DA")
        self.assertEqual(resolve_ligand("rA", VALID).ligand_code, "A")

    def test_literal_code_is_allowed_when_known(self):
        resolved = resolve_ligand("5IU", VALID)
        self.assertEqual(resolved.ligand_code, "5IU")
        self.assertFalse(resolved.used_alias)

    def test_f_defaults_to_df_while_a1aaz_remains_explicit(self):
        self.assertEqual(resolve_ligand("F", VALID).ligand_code, "DF")
        self.assertEqual(resolve_ligand("A1AAZ", VALID).ligand_code, "A1AAZ")

    def test_e_uses_curated_8ro_identity(self):
        self.assertEqual(resolve_ligand("E", VALID).ligand_code, "8RO")

    def test_ordered_pair(self):
        first, second = resolve_pair("D:T", VALID)
        self.assertEqual((first.ligand_code, second.ligand_code), ("1AP", "DT"))

    def test_unknown_literal_is_rejected(self):
        with self.assertRaisesRegex(LigandCodeError, "Unknown ligand code"):
            resolve_ligand("NOPE", VALID)


if __name__ == "__main__":
    unittest.main()
