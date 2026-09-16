#!/usr/bin/env python3
"""Apply the bounded NASolve -> NARestraints terminal-phosphate wiring patch.

Temporary development helper.  It edits only tracked source/tests/changelog and
refuses to continue if the expected feature-branch text has drifted.
"""
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one patch target, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


POSTMR = "src/nasolve/postmr.py"
TEST = "tests/test_postmr.py"
CHANGELOG = "CHANGELOG.md"

replace_once(
    POSTMR,
    '''def _default_narestraints_builder(\n    pdb: Path,\n    pairs: Path,\n    output: Path,\n) -> list[dict[str, str]]:\n''',
    '''def _default_narestraints_builder(\n    pdb: Path,\n    pairs: Path,\n    output: Path,\n    *,\n    terminal_phosphate_sites: tuple[str, ...] = (),\n) -> list[dict[str, str]]:\n''',
)
replace_once(
    POSTMR,
    '''        builder.build_phil_from_pdb(\n            pdb,\n            read_base_pair_file(pairs),\n            output,\n            include_stacking=True,\n        )\n''',
    '''        builder.build_phil_from_pdb(\n            pdb,\n            read_base_pair_file(pairs),\n            output,\n            include_stacking=True,\n            terminal_phosphate_sites=terminal_phosphate_sites,\n        )\n''',
)
replace_once(
    POSTMR,
    '''def _default_modified_pair_restraints_builder(\n    prepared_pdb: Path,\n    compatibility_pdb: Path,\n    pair_output: Path,\n    restraint_output: Path,\n) -> dict[str, object]:\n''',
    '''def _default_modified_pair_restraints_builder(\n    prepared_pdb: Path,\n    compatibility_pdb: Path,\n    pair_output: Path,\n    restraint_output: Path,\n    *,\n    terminal_phosphate_sites: tuple[str, ...] = (),\n) -> dict[str, object]:\n''',
)
replace_once(
    POSTMR,
    '''        if selected:\n            builder.build_phil_from_pdb(\n                compatibility_pdb,\n                read_base_pair_file(pair_output),\n                restraint_output,\n                include_stacking=False,\n            )\n''',
    '''        if selected or terminal_phosphate_sites:\n            builder.build_phil_from_pdb(\n                compatibility_pdb,\n                read_base_pair_file(pair_output),\n                restraint_output,\n                include_stacking=False,\n                terminal_phosphate_sites=terminal_phosphate_sites,\n            )\n''',
)
replace_once(
    POSTMR,
    '''        try:\n            builder_result = (\n                modified_pair_builder or _default_modified_pair_restraints_builder\n            )(prepared, compatibility, pair_file, narestraints)\n''',
    '''        try:\n            if modified_pair_builder is None:\n                builder_result = _default_modified_pair_restraints_builder(\n                    prepared, compatibility, pair_file, narestraints,\n                    terminal_phosphate_sites=allowed_op3,\n                )\n            else:\n                builder_result = modified_pair_builder(\n                    prepared, compatibility, pair_file, narestraints\n                )\n''',
)
replace_once(
    POSTMR,
    '''        narestraints_report = dict(builder_result)\n        narestraints_report.setdefault("mode", "modified-pairs-only")\n''',
    '''        narestraints_report = dict(builder_result)\n        narestraints_report.setdefault("mode", "modified-pairs-only")\n        narestraints_report["terminal_phosphate_sites"] = list(allowed_op3)\n''',
)
replace_once(
    POSTMR,
    '''        try:\n            builder_result = (narestraints_builder or _default_narestraints_builder)(\n                compatibility, pair_file, narestraints\n            )\n''',
    '''        try:\n            if narestraints_builder is None:\n                builder_result = _default_narestraints_builder(\n                    compatibility, pair_file, narestraints,\n                    terminal_phosphate_sites=allowed_op3,\n                )\n            else:\n                builder_result = narestraints_builder(\n                    compatibility, pair_file, narestraints\n                )\n''',
)
replace_once(
    POSTMR,
    '''            "include_stacking": True,\n            "secondary_structure_file": str(secondary),\n''',
    '''            "include_stacking": True,\n            "terminal_phosphate_sites": list(allowed_op3),\n            "secondary_structure_file": str(secondary),\n''',
)

replace_once(
    TEST,
    '''    _default_modified_pair_restraints_builder,\n''',
    '''    _default_modified_pair_restraints_builder,\n    _default_narestraints_builder,\n''',
)
replace_once(
    TEST,
    '''            def build_phil_from_pdb(\n                path: Path,\n                stretches: object,\n                output: Path,\n                *,\n                include_stacking: bool,\n            ):\n                self.assertEqual(path, compatibility)\n                self.assertEqual(stretches, "parsed")\n                self.assertFalse(include_stacking)\n                output.write_text("geometry_restraints.edits {}\\n")\n''',
    '''            def build_phil_from_pdb(\n                path: Path,\n                stretches: object,\n                output: Path,\n                *,\n                include_stacking: bool,\n                terminal_phosphate_sites: tuple[str, ...] = (),\n            ):\n                self.assertEqual(path, compatibility)\n                self.assertEqual(stretches, "parsed")\n                self.assertFalse(include_stacking)\n                self.assertEqual(terminal_phosphate_sites, ("D:1",))\n                output.write_text("geometry_restraints.edits {}\\n")\n''',
)
replace_once(
    TEST,
    '''                report = _default_modified_pair_restraints_builder(\n                    prepared, compatibility, pair_output, restraint_output\n                )\n''',
    '''                report = _default_modified_pair_restraints_builder(\n                    prepared, compatibility, pair_output, restraint_output,\n                    terminal_phosphate_sites=("D:1",),\n                )\n''',
)
replace_once(
    TEST,
    '''            self.assertTrue(restraint_output.is_file())\n\n    def test_mirrored_canonical_targets_do_not_revert_to_d_dna(self):\n''',
    '''            self.assertTrue(restraint_output.is_file())\n\n    def test_default_narestraints_builder_forwards_terminal_phosphate_sites(self):\n        with tempfile.TemporaryDirectory() as directory:\n            root = Path(directory)\n            model = root / "model.pdb"\n            model.write_text(\n                pdb_record("ATOM", 1, "P", "DC", "D", 1, element="P") + "END\\n"\n            )\n            pairs = root / "pairs.txt"\n            pairs.write_text("D 1\\nD 1\\n")\n            output = root / "restraints.phil"\n            seen: dict[str, object] = {}\n\n            builder = types.ModuleType("restraints.builder")\n            base_pairs = types.ModuleType("restraints.base_pairs")\n            residue_library = types.ModuleType("restraints.residue_library")\n            builder.load_residue_records = lambda: []\n            residue_library.load_residue_records = lambda: []\n            base_pairs.read_base_pair_file = lambda _path: "parsed"\n\n            def build_phil_from_pdb(\n                path: Path, stretches: object, destination: Path, *,\n                include_stacking: bool,\n                terminal_phosphate_sites: tuple[str, ...] = (),\n            ) -> None:\n                seen["path"] = path\n                seen["stretches"] = stretches\n                seen["include_stacking"] = include_stacking\n                seen["terminal_phosphate_sites"] = terminal_phosphate_sites\n                destination.write_text("geometry_restraints.edits {}\\n")\n\n            builder.build_phil_from_pdb = build_phil_from_pdb\n            package = types.ModuleType("restraints")\n            package.builder = builder\n            modules = {\n                "restraints": package,\n                "restraints.builder": builder,\n                "restraints.base_pairs": base_pairs,\n                "restraints.residue_library": residue_library,\n            }\n            with patch.dict(sys.modules, modules):\n                corrections = _default_narestraints_builder(\n                    model, pairs, output, terminal_phosphate_sites=("D:1",)\n                )\n\n            self.assertEqual(corrections, [])\n            self.assertEqual(seen["path"], model)\n            self.assertEqual(seen["stretches"], "parsed")\n            self.assertTrue(seen["include_stacking"])\n            self.assertEqual(seen["terminal_phosphate_sites"], ("D:1",))\n            self.assertTrue(output.is_file())\n\n    def test_mirrored_canonical_targets_do_not_revert_to_d_dna(self):\n''',
)

replace_once(
    CHANGELOG,
    '''- Generalized the OP3-specific policy into an explicit standard-phosphodiester backbone contract. `five_prime_phosphate_sites` is the preferred user-facing name (legacy `allow_op3_sites` remains readable). PostMR now treats a requested 5'-terminal phosphate as the complete P/OP1/OP2/OP3 group, preserving a complete group, completing missing OP3 from existing P/OP1/OP2, or seeding a whole missing group from O5'-C5' with recorded idealized starting geometry. Partial ambiguous groups still fail closed.\n''',
    '''- Generalized the OP3-specific policy into an explicit standard-phosphodiester backbone contract. `five_prime_phosphate_sites` is the preferred user-facing name (legacy `allow_op3_sites` remains readable). PostMR now treats a requested 5'-terminal phosphate as the complete P/OP1/OP2/OP3 group, preserving a complete group, completing missing OP3 from existing P/OP1/OP2, or seeding a whole missing group from O5'-C5' with recorded idealized starting geometry. Partial ambiguous groups still fail closed.\n- Forward explicit 5'-terminal phosphate sites to NARestraints so its site-scoped terminal-phosphomonoester angle restraints can supplement Phenix's native P-OP3 bond without duplicating ordinary internal phosphodiester geometry. Injected custom restraint builders retain their historical call signatures.\n''',
)

print("Applied NASolve -> NARestraints terminal-phosphate wiring patch")
