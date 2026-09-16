#!/usr/bin/env python3
"""Apply the reviewed ReadySet successful-noop compatibility fix.

Temporary maintainer helper: edits only tracked source/test/changelog files and
refuses to proceed if the expected feature-branch text is not present exactly.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"refusing to patch {path}: expected block count {text.count(old)}, wanted 1")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


postmr = ROOT / "src" / "nasolve" / "postmr.py"
old = '''    updated = readyset_directory / f"{model.stem}.updated.pdb"\n    generated_cif = readyset_directory / f"{model.stem}.ligands.cif"\n    if completed.returncode or not updated.is_file():\n        raise PostMRPreparationError(\n            f"ReadySet failed with status {completed.returncode}; inspect {log}"\n        )\n    before = _atom_counts(model)\n    raw_counts = _atom_counts(updated)\n'''
new = '''    updated = readyset_directory / f"{model.stem}.updated.pdb"\n    generated_cif = readyset_directory / f"{model.stem}.ligands.cif"\n    if completed.returncode:\n        raise PostMRPreparationError(\n            f"ReadySet failed with status {completed.returncode}; inspect {log}"\n        )\n    readyset_source = updated\n    readyset_output_mode = "updated-model"\n    if not updated.is_file():\n        if re.search(r"\\bNo unknown residues\\b", completed.stdout, re.I):\n            # Phenix 2.2 may return success without writing an updated PDB when\n            # ReadySet has nothing to modify. Preserve the already-prepared\n            # model, but still run the same phosphate and atom-count audits.\n            readyset_source = model\n            readyset_output_mode = "successful-noop"\n        else:\n            raise PostMRPreparationError(\n                "ReadySet exited successfully but did not write its expected updated model; "\n                f"inspect {log}"\n            )\n    before = _atom_counts(model)\n    raw_counts = _atom_counts(readyset_source)\n'''
replace_once(postmr, old, new)

old = '''        phosphate_audit = sanitize_phosphates(\n            updated, checked, reference_model=model, check_sites=phosphate_sites,\n            allow_op3_sites=allow_op3_sites, passthrough_sites=passthrough_sites,\n        )\n'''
new = '''        phosphate_audit = sanitize_phosphates(\n            readyset_source, checked, reference_model=model, check_sites=phosphate_sites,\n            allow_op3_sites=allow_op3_sites, passthrough_sites=passthrough_sites,\n        )\n        phosphate_audit["readyset_output_mode"] = readyset_output_mode\n'''
replace_once(postmr, old, new)

old = '''            "updated_model": str(readyset_dir / f"{prepared.stem}.updated.pdb"),\n            "phosphate_checked_model": {\n'''
new = '''            "output_mode": phosphate_after.get("readyset_output_mode"),\n            "updated_model": (\n                str(readyset_dir / f"{prepared.stem}.updated.pdb")\n                if phosphate_after.get("readyset_output_mode") == "updated-model"\n                else None\n            ),\n            "phosphate_checked_model": {\n'''
replace_once(postmr, old, new)

test = ROOT / "tests" / "test_postmr.py"
old = '''    _restore_shared_parent_coordinates,\n    _solution_model,\n    build_mutation_plan,\n'''
new = '''    _restore_shared_parent_coordinates,\n    _run_readyset,\n    _solution_model,\n    build_mutation_plan,\n'''
replace_once(test, old, new)

marker = '''    def test_modified_pairs_only_works_for_nonstandard_and_still_runs_readyset(self):\n'''
insert = '''    def test_readyset_successful_noop_preserves_and_audits_model(self):\n        with tempfile.TemporaryDirectory() as directory:\n            root = Path(directory)\n            model = root / "prepared_model.pdb"\n            model.write_text(postmr_model_text("DC", "DG"))\n            readyset_directory = root / "ReadySet"\n            readyset_directory.mkdir()\n            executable = root / "phenix.ready_set"\n            executable.write_text(\n                "#!/bin/sh\\n"\n                "echo 'No unknown residues'\\n"\n                "exit 0\\n"\n            )\n            executable.chmod(executable.stat().st_mode | 0o100)\n\n            checked, log, generated_cif, command, audit = _run_readyset(\n                model, executable, readyset_directory, None, None\n            )\n\n            self.assertTrue(checked.is_file())\n            self.assertEqual(checked.read_text(), model.read_text())\n            self.assertIn("No unknown residues", log.read_text())\n            self.assertIsNone(generated_cif)\n            self.assertEqual(command[0], str(executable))\n            self.assertEqual(audit["readyset_output_mode"], "successful-noop")\n            self.assertFalse((readyset_directory / "prepared_model.updated.pdb").exists())\n\n''' + marker
replace_once(test, marker, insert)

changelog = ROOT / "CHANGELOG.md"
old = '''### Fixed\n\n'''
new = '''### Fixed\n\n- ReadySet exit status 0 with the explicit `No unknown residues` result is now accepted as a successful no-op when Phenix writes no `*.updated.pdb`. NASolve preserves the already-prepared model, still runs its phosphate/atom-count audits, and records the no-op output mode; missing ReadySet output without that explicit success condition still fails closed.\n\n'''
replace_once(changelog, old, new)

print("Applied ReadySet successful-noop fix to postmr.py, test_postmr.py, and CHANGELOG.md")
