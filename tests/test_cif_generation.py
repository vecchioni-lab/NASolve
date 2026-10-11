"""Candidate-only generation mechanics; fake programs are not native evidence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

import pytest

from nasolve.cif_generation import generate_elbow_candidate, inspect_component_generation
from nasolve.ligand_profiles import _emit


def component(code="ZZZ", *, numerical=False):
    values = {
        "data_": "comp_" + code, "_chem_comp.id": [code],
        "_chem_comp_atom.comp_id": [code] * 4,
        "_chem_comp_atom.atom_id": ["C5", "C5'", "O4'", "C1'"],
        "_chem_comp_atom.type_symbol": ["C", "C", "O", "C"],
        "_chem_comp_atom.pdbx_formal_charge": ["0"] * 4,
        "_chem_comp_atom.pdbx_model_Cartn_x_ideal": ["9.111", "10.222", "11.333", "12.444"],
        "_chem_comp_atom.pdbx_model_Cartn_y_ideal": ["1.2", "1.3", "1.4", "1.5"],
        "_chem_comp_atom.pdbx_model_Cartn_z_ideal": ["-1", "-2", "-3", "-4"],
        "_chem_comp_bond.comp_id": [code] * 3,
        "_chem_comp_bond.atom_id_1": ["C5", "C5'", "O4'"],
        "_chem_comp_bond.atom_id_2": ["C5'", "O4'", "C1'"],
        "_chem_comp_bond.value_order": ["SING"] * 3,
    }
    if numerical:
        values.update({
            "_chem_comp_atom.type_energy": ["C", "C", "O", "C"],
            "_chem_comp_bond.value_dist": ["1.50"] * 3,
            "_chem_comp_bond.value_dist_esd": ["0.02"] * 3,
            "_chem_comp_angle.comp_id": [code] * 2,
            "_chem_comp_angle.atom_id_1": ["C5", "C5'"],
            "_chem_comp_angle.atom_id_2": ["C5'", "O4'"],
            "_chem_comp_angle.atom_id_3": ["O4'", "C1'"],
            "_chem_comp_angle.value_angle": ["110"] * 2,
            "_chem_comp_angle.value_angle_esd": ["2"] * 2,
        })
    return values


def write(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_emit(values), encoding="utf-8")
    return path


def inputs(tmp_path, code="ZZZ", *, generated=None):
    source = write(tmp_path / "source" / "component.cif", component(code))
    fixture = write(tmp_path / "fixtures" / "generated.cif", generated or component(code, numerical=True))
    return source, fixture


HELP = """Usage: phenix.elbow [options]

Options:
  -h, --help            Show help
  --id=ID              Component identifier
  --output=OUTPUT      Output prefix
  --template=TEMPLATE  Exact atom naming
  --initial-geometry=FILE  Initial geometry
  --add-hydrogens=BOOL  Control hydrogen addition; default True
  --chiral=MODE        Chiral treatment
  --opt                Optimize
"""


def program(tmp_path, body=None, *, help_text=HELP, help_body=None):
    executable = tmp_path / "bin" / "phenix.elbow"
    executable.parent.mkdir(exist_ok=True)
    help_branch = help_body or f"print({help_text!r}); sys.exit(0)"
    prelude = "import sys\nif sys.argv[1:] == ['--help']:\n" + "\n".join("    " + line for line in help_branch.splitlines()) + "\n"
    executable.write_text("#!" + sys.executable + "\n" + prelude + (body or """
import json, os, shutil, sys
from pathlib import Path
Path('argv.json').write_text(json.dumps(sys.argv[1:]))
Path('actual_seed.pdb').write_bytes(Path('source_ideal.pdb').read_bytes())
shutil.copyfile(os.environ['CANDIDATE_FIXTURE'], 'candidate.cif')
Path('candidate.pdb').write_text('raw backend output\\n')
print('fake eLBOW generation only')
"""))
    executable.chmod(0o755)
    return executable


def run(source, fixture, executable, output_parent, **kwargs):
    environment = {**os.environ, "CANDIDATE_FIXTURE": str(fixture)}
    return generate_elbow_candidate(source, "ZZZ", output_parent, executable,
                                    environment=environment, phenix_version="2.2.1-test-only", **kwargs)


@pytest.mark.parametrize("code", ["ZZZ", "Q99", "1AP"])
def test_zero_bond_diagnosis_is_general_and_exact(tmp_path, code):
    values = component(code, numerical=True)
    values["_chem_comp_bond.value_dist"][0] = "0.000"
    source, generated = inputs(tmp_path, code, generated=values)
    before = source.read_bytes(), generated.read_bytes()
    receipt = inspect_component_generation(source, generated, code)
    assert receipt["status"] == "REJECTED"
    issues = [row for row in receipt["numerical_issues"] if row["code"] == "numeric-domain-violation"]
    assert len(issues) == 1
    assert issues[0]["measurements"] == {
        "category": "bond", "row": 0, "field": "value_dist", "value": "0.000", "atoms": ["C5", "C5'"]}
    assert (source.read_bytes(), generated.read_bytes()) == before
    assert receipt["automatic_adoption"] is False


def test_generation_uses_complete_source_ideal_seed_and_preserves_raw_output(tmp_path):
    source, fixture = inputs(tmp_path)
    source_bytes = source.read_bytes()
    out = tmp_path / "candidates"
    receipt = run(source, fixture, program(tmp_path), out)
    work = Path(receipt["candidate_directory"])
    assert receipt["status"] == "CANDIDATE_REVIEW"
    assert receipt["source_preserved"] and receipt["frozen_source_preserved"]
    assert source.read_bytes() == source_bytes == (work / "source.cif").read_bytes()
    assert (work / "candidate.cif").read_bytes() == fixture.read_bytes()
    assert (work / "candidate.pdb").read_text() == "raw backend output\n"
    assert json.loads((work / "argv.json").read_text()) == [
        "source.cif", "--id=ZZZ", "--output=candidate", "--template=source_ideal.pdb",
        "--initial-geometry=source_ideal.pdb", "--add-hydrogens=False", "--chiral=retain", "--opt"]
    atoms = [line for line in (work / "actual_seed.pdb").read_text().splitlines() if line.startswith("HETATM")]
    assert [line[12:16].strip() for line in atoms] == ["C5", "C5'", "O4'", "C1'"]
    assert [float(line[30:38]) for line in atoms] == [9.111, 10.222, 11.333, 12.444]
    assert receipt["seed"]["experimental_model_used"] is False
    assert receipt["seed"]["formal_charges"] == {"C5": 0, "C5'": 0, "O4'": 0, "C1'": 0}
    assert receipt["readyset_retry"] == "NOT_RUN"
    assert receipt["native_proxy_validation"] == "NOT_RUN"
    assert receipt["generator_capabilities"]["status"] == "SUPPORTED"
    assert receipt["generator_capabilities"]["command"] == [str(tmp_path / "bin/phenix.elbow"), "--help"]
    assert receipt["generator_capabilities"]["returncode"] == 0
    assert receipt["generator_capabilities"]["selected_aliases"]["initial_geometry"] == "--initial-geometry"
    assert receipt["generator_capabilities"]["executable_sha256"] == hashlib.sha256((tmp_path / "bin/phenix.elbow").read_bytes()).hexdigest()
    assert receipt["generator_capabilities"]["help_output"]["sha256"] == hashlib.sha256((work / "elbow_help.log").read_bytes()).hexdigest()
    saved = json.loads((work / "generation_receipt.json").read_text())
    assert saved == receipt
    for artifact in receipt["outputs"]:
        assert artifact["anchor"] == "candidate_directory"
        assert hashlib.sha256((work / artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"]


def test_every_invocation_is_fresh_and_does_not_overwrite(tmp_path):
    source, fixture = inputs(tmp_path)
    executable = program(tmp_path)
    first = run(source, fixture, executable, tmp_path / "out")
    preserved = {path.name: path.read_bytes() for path in Path(first["candidate_directory"]).iterdir() if path.is_file()}
    second = run(source, fixture, executable, tmp_path / "out")
    assert first["candidate_directory"] != second["candidate_directory"]
    assert preserved == {path.name: path.read_bytes() for path in Path(first["candidate_directory"]).iterdir() if path.is_file()}


@pytest.mark.parametrize("defect", ["zero", "dangling", "charge", "hydrogen"])
def test_generated_numerical_or_chemical_defects_are_rejected(tmp_path, defect):
    values = component(numerical=True)
    if defect == "zero":
        values["_chem_comp_bond.value_dist"][0] = "0"
    elif defect == "dangling":
        values["_chem_comp_bond.atom_id_2"][0] = "C55"
    elif defect == "charge":
        values["_chem_comp_atom.pdbx_formal_charge"][0] = "1"
    elif defect == "hydrogen":
        values["_chem_comp_atom.type_symbol"][0] = "H"
    source, fixture = inputs(tmp_path, generated=values)
    receipt = run(source, fixture, program(tmp_path), tmp_path / "out")
    assert receipt["status"] == "REJECTED"
    assert receipt["inspection"]["rejection_reasons"]
    assert receipt["automatic_adoption"] is False
    if defect in {"charge", "hydrogen"}:
        assert receipt["inspection"]["chemical_changes"]


@pytest.mark.parametrize("field,bad", [
    ("pdbx_model_Cartn_x_ideal", "?"), ("pdbx_formal_charge", "?"),
    ("pdbx_formal_charge", "0.5"), ("atom_id", "C5555"), ("type_symbol", "?"),
])
def test_unsupported_seed_is_reported_without_launch_or_coordinate_fallback(tmp_path, field, bad):
    source, fixture = inputs(tmp_path)
    values = component()
    values["_chem_comp_atom." + field][0] = bad
    write(source, values)
    receipt = run(source, fixture, program(tmp_path), tmp_path / "out")
    assert receipt["status"] == "REJECTED"
    assert receipt["execution"]["status"] in {"NOT_RUN", "UNSUPPORTED_INPUT"}
    assert receipt["command"] is None
    assert not (Path(receipt["candidate_directory"]) / "argv.json").exists()


def test_formal_charge_is_written_to_pdb_columns_without_changing_source(tmp_path):
    values = component()
    values["_chem_comp_atom.pdbx_formal_charge"][0] = "1"
    source, fixture = inputs(tmp_path)
    write(source, values)
    numeric = component(numerical=True)
    numeric["_chem_comp_atom.pdbx_formal_charge"][0] = "1"
    write(fixture, numeric)
    receipt = run(source, fixture, program(tmp_path), tmp_path / "out")
    first = [line for line in (Path(receipt["candidate_directory"]) / "source_ideal.pdb").read_text().splitlines() if line.startswith("HETATM")][0]
    assert first[78:80] == "1+"
    assert receipt["status"] == "CANDIDATE_REVIEW"


def test_explicit_stereochemical_contradiction_is_rejected_not_erased(tmp_path):
    source, fixture = inputs(tmp_path)
    values = component()
    values["_chem_comp_atom.pdbx_stereo_config"] = ["R", "N", "N", "N"]
    write(source, values)
    numeric = component(numerical=True)
    numeric["_chem_comp_atom.pdbx_stereo_config"] = ["S", "N", "N", "N"]
    write(fixture, numeric)
    receipt = inspect_component_generation(source, fixture, "ZZZ")
    assert receipt["status"] == "REJECTED"
    assert "generated-explicit-atom-stereochemistry-changed" in receipt["rejection_reasons"]
    assert any(row["field"] == "atom_stereo_declarations" for row in receipt["chemical_changes"])


def test_charge_field_translation_is_review_evidence_not_an_invented_change(tmp_path):
    source, fixture = inputs(tmp_path)
    numeric = component(numerical=True)
    numeric["_chem_comp_atom.charge"] = numeric.pop("_chem_comp_atom.pdbx_formal_charge")
    write(fixture, numeric)
    receipt = inspect_component_generation(source, fixture, "ZZZ")
    assert receipt["status"] == "CANDIDATE_REVIEW"
    assert any(row["field"] == "declared_charge_fields" for row in receipt["chemical_changes"])
    assert receipt["automatic_adoption"] is False


def test_original_source_race_rejects_candidate_and_preserves_receipt(tmp_path):
    source, fixture = inputs(tmp_path)
    body = """
import os, shutil
from pathlib import Path
Path(os.environ['MUTATE_SOURCE']).write_text('external change during generation')
shutil.copyfile(os.environ['CANDIDATE_FIXTURE'], 'candidate.cif')
"""
    receipt = generate_elbow_candidate(source, "ZZZ", tmp_path / "out", program(tmp_path, body),
        environment={**os.environ, "CANDIDATE_FIXTURE": str(fixture), "MUTATE_SOURCE": str(source)},
        phenix_version="test")
    assert receipt["status"] == "REJECTED"
    assert receipt["source_preserved"] is False
    assert receipt["frozen_source_preserved"] is True
    assert (Path(receipt["candidate_directory"]) / "generation_receipt.json").exists()
    assert source.read_text() == "external change during generation"


def test_deleted_frozen_source_rejects_candidate_with_failure_receipt(tmp_path):
    source, fixture = inputs(tmp_path)
    body = """
from pathlib import Path
Path('source.cif').unlink()
print('backend removed frozen input')
"""
    receipt = run(source, fixture, program(tmp_path, body), tmp_path / "out")
    assert receipt["status"] == "REJECTED"
    assert receipt["source_preserved"] is True
    assert receipt["frozen_source_preserved"] is False
    assert (Path(receipt["candidate_directory"]) / "generation_receipt.json").exists()


@pytest.mark.skipif(os.name != "posix", reason="Owned process-group timeout is a POSIX contract")
def test_timeout_kills_optimizer_descendants_and_retains_raw_evidence(tmp_path):
    source, fixture = inputs(tmp_path)
    sentinel = tmp_path / "descendant-survived"
    body = """
import os, subprocess, sys, time
child = 'import os,time; from pathlib import Path; time.sleep(0.4); Path(os.environ["SENTINEL"]).write_text("survived")'
subprocess.Popen([sys.executable, '-c', child])
print('optimizer launched', flush=True)
time.sleep(5)
"""
    receipt = generate_elbow_candidate(source, "ZZZ", tmp_path / "out", program(tmp_path, body),
        environment={**os.environ, "SENTINEL": str(sentinel)}, phenix_version="test", timeout_seconds=0.15)
    assert receipt["status"] == "FAILED"
    assert receipt["execution"]["status"] == "TIMED_OUT"
    time.sleep(0.4)
    assert not sentinel.exists()
    assert "optimizer launched" in (Path(receipt["candidate_directory"]) / "elbow.log").read_text()
    assert receipt["source_preserved"]


def test_missing_output_or_bad_exit_cannot_become_a_candidate(tmp_path):
    source, fixture = inputs(tmp_path)
    receipt = run(source, fixture, program(tmp_path, "print('no candidate')\n"), tmp_path / "out")
    assert receipt["status"] == "FAILED"
    assert "exact regular candidate.cif" in receipt["error"]


def test_generation_refuses_output_inside_source_directory(tmp_path):
    source, fixture = inputs(tmp_path)
    with pytest.raises(ValueError, match="outside"):
        run(source, fixture, program(tmp_path), source.parent / "outputs")
    assert not (source.parent / "outputs").exists()


def test_relocation_uses_current_explicit_paths_after_originals_disappear(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    source, fixture = inputs(original)
    executable = program(original)
    relocated = tmp_path / "relocated"
    shutil.copytree(original, relocated)
    shutil.rmtree(original)
    receipt = run(relocated / "source/component.cif", relocated / "fixtures/generated.cif",
                  relocated / "bin/phenix.elbow", tmp_path / "out")
    assert receipt["status"] == "CANDIDATE_REVIEW"
    assert receipt["source_provenance"]["path"].startswith(str(relocated))
    assert not original.exists()


@pytest.mark.parametrize("initial,hydrogen", [
    ("--initial_geometry", "--add_hydrogens"),
    ("--initial_geometry", "--add-hydrogens"),
    ("--initial-geometry", "--add_hydrogens"),
])
def test_installed_help_selects_each_supported_option_spelling_independently(tmp_path, initial, hydrogen):
    source, fixture = inputs(tmp_path)
    help_text = HELP.replace("--initial-geometry", initial).replace("--add-hydrogens", hydrogen)
    body = f"""
import json, os, shutil, sys
from pathlib import Path
assert {initial + '=source_ideal.pdb'!r} in sys.argv
assert {hydrogen + '=False'!r} in sys.argv
assert '--chiral=retain' in sys.argv and '--opt' in sys.argv
Path('argv.json').write_text(json.dumps(sys.argv[1:]))
shutil.copyfile(os.environ['CANDIDATE_FIXTURE'], 'candidate.cif')
"""
    receipt = run(source, fixture, program(tmp_path, body, help_text=help_text), tmp_path / "out")
    assert receipt["status"] == "CANDIDATE_REVIEW"
    assert receipt["generator_capabilities"]["selected_aliases"]["initial_geometry"] == initial
    assert receipt["generator_capabilities"]["selected_aliases"]["add_hydrogens"] == hydrogen
    assert hydrogen + "=False" in receipt["command"]
    assert receipt["source_preserved"] and receipt["frozen_source_preserved"]


@pytest.mark.parametrize("option", [
    "--id=ID", "--output=OUTPUT", "--template=TEMPLATE", "--initial-geometry=FILE",
    "--add-hydrogens=BOOL", "--chiral=MODE", "--opt",
])
def test_missing_required_semantics_block_chemistry_call(tmp_path, option):
    source, fixture = inputs(tmp_path)
    help_text = "\n".join(line for line in HELP.splitlines() if option not in line)
    receipt = run(source, fixture, program(tmp_path, help_text=help_text), tmp_path / "out")
    assert receipt["status"] == "REJECTED"
    assert receipt["execution"]["status"] == "UNSUPPORTED_GENERATOR"
    assert receipt["generator_capabilities"]["unsupported_semantics"]
    assert receipt["command"] is None
    work = Path(receipt["candidate_directory"])
    assert not (work / "candidate.cif").exists()
    assert not (work / "argv.json").exists()
    assert receipt["source_preserved"] and receipt["frozen_source_preserved"]
    assert (work / "generation_receipt.json").exists()


@pytest.mark.parametrize("substitute", [
    "  --initial-geometry-extra=FILE  A similar prefix is not the option",
    "        --initial-geometry=FILE  Wrapped prose is not a definition",
    "  Example: use --initial-geometry=FILE",
    "Examples:\n  --initial-geometry=FILE  An example outside the options section",
])
def test_prefixes_and_help_examples_do_not_claim_a_required_option(tmp_path, substitute):
    source, fixture = inputs(tmp_path)
    help_text = "\n".join(line for line in HELP.splitlines() if "--initial-geometry" not in line) + "\n" + substitute
    receipt = run(source, fixture, program(tmp_path, help_text=help_text), tmp_path / "out")
    assert receipt["execution"]["status"] == "UNSUPPORTED_GENERATOR"
    assert "initial_geometry" in receipt["generator_capabilities"]["unsupported_semantics"]
    assert receipt["command"] is None


@pytest.mark.parametrize("replacement", [
    "--add-hydrogens", "--no-add-hydrogens", "--add-hydrogens-negative=BOOL",
])
def test_hydrogen_false_semantics_cannot_be_replaced_with_a_flag_or_negative_alias(tmp_path, replacement):
    source, fixture = inputs(tmp_path)
    help_text = HELP.replace("--add-hydrogens=BOOL", replacement)
    receipt = run(source, fixture, program(tmp_path, help_text=help_text), tmp_path / "out")
    assert receipt["status"] == "REJECTED"
    assert receipt["execution"]["status"] == "UNSUPPORTED_GENERATOR"
    assert "add_hydrogens" in receipt["generator_capabilities"]["unsupported_semantics"]
    assert receipt["command"] is None


def test_help_error_is_preserved_without_attempting_chemistry(tmp_path):
    source, fixture = inputs(tmp_path)
    before = source.read_bytes()
    executable = program(tmp_path, help_body="print('Usage: phenix.elbow [options]'); print('parser help failed'); sys.exit(2)")
    receipt = run(source, fixture, executable, tmp_path / "out")
    assert receipt["status"] == "REJECTED"
    assert receipt["execution"]["status"] == "UNSUPPORTED_GENERATOR"
    assert receipt["generator_capabilities"]["returncode"] == 2
    assert receipt["generator_capabilities"]["reason"] == "help-nonzero-exit"
    assert "parser help failed" in (Path(receipt["candidate_directory"]) / "elbow_help.log").read_text()
    assert source.read_bytes() == before
    assert receipt["command"] is None


@pytest.mark.skipif(os.name != "posix", reason="Owned help-process groups are a POSIX contract")
def test_help_timeout_kills_descendants_and_blocks_generation(tmp_path):
    source, fixture = inputs(tmp_path)
    sentinel = tmp_path / "help-descendant-survived"
    help_body = """
import os, subprocess, time
subprocess.Popen([sys.executable, '-c', 'import os,time; from pathlib import Path; time.sleep(0.4); Path(os.environ["SENTINEL"]).write_text("survived")'])
print('help started', flush=True)
time.sleep(5)
"""
    receipt = generate_elbow_candidate(source, "ZZZ", tmp_path / "out", program(tmp_path, help_body=help_body),
        environment={**os.environ, "SENTINEL": str(sentinel)}, phenix_version="test", timeout_seconds=0.15)
    assert receipt["execution"]["status"] == "UNSUPPORTED_GENERATOR"
    assert receipt["generator_capabilities"]["reason"] == "help-timeout"
    assert receipt["generator_capabilities"]["timeout_seconds"] == 0.15
    assert receipt["command"] is None
    time.sleep(0.4)
    assert not sentinel.exists()
    assert receipt["source_preserved"]


def test_capability_check_has_a_separate_bounded_help_timeout(tmp_path):
    source, fixture = inputs(tmp_path)
    receipt = run(source, fixture, program(tmp_path), tmp_path / "out", timeout_seconds=600)
    assert receipt["generator_capabilities"]["timeout_seconds"] == 20
    assert receipt["execution"]["timeout_seconds"] == 600


def test_executable_change_during_help_prevents_generation(tmp_path):
    source, fixture = inputs(tmp_path)
    help_body = f"""
from pathlib import Path
print({HELP!r})
Path(__file__).write_text('# replacement executable during help')
sys.exit(0)
"""
    receipt = run(source, fixture, program(tmp_path, help_body=help_body), tmp_path / "out")
    assert receipt["execution"]["status"] == "UNSUPPORTED_GENERATOR"
    assert receipt["generator_capabilities"]["reason"] == "executable-changed-during-help"
    assert receipt["command"] is None
    assert receipt["source_preserved"] and receipt["frozen_source_preserved"]
