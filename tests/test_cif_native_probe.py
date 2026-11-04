"""A relocated diagnostic uses explicit frozen refs and invented test chemistry."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest
import restraints

from nasolve.cif_doctor import assess_dictionaries
from nasolve.ligand_profiles import _blocks, _emit, dictionary_component_codes


ROOT = Path(__file__).resolve().parents[1]


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _initialize_git(root):
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Native probe fixture",
                    "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                    "commit", "--no-verify", "-qm", "Invented source fixture"],
                   check=True, capture_output=True)


def _component(code, *, numerical=False, distance="1.4"):
    values = {
        "data_": "comp_" + code, "_chem_comp.id": [code],
        "_chem_comp_atom.comp_id": [code] * 4,
        "_chem_comp_atom.atom_id": ["C5", "C5'", "N3", "H1"],
        "_chem_comp_atom.type_symbol": ["C", "C", "N", "H"],
        "_chem_comp_atom.pdbx_formal_charge": ["0"] * 4,
        "_chem_comp_atom.pdbx_model_Cartn_x_ideal": ["0", "1.5", "1.5", "2.5"],
        "_chem_comp_atom.pdbx_model_Cartn_y_ideal": ["0", "0", "1.4", "1.4"],
        "_chem_comp_atom.pdbx_model_Cartn_z_ideal": ["0"] * 4,
        "_chem_comp_bond.comp_id": [code] * 3,
        "_chem_comp_bond.atom_id_1": ["C5", "C5'", "N3"],
        "_chem_comp_bond.atom_id_2": ["C5'", "N3", "H1"],
        "_chem_comp_bond.value_order": ["SING"] * 3,
    }
    if numerical:
        values.update({
            "_chem_comp_atom.type_energy": ["C", "C", "N", "H"],
            "_chem_comp_bond.value_dist": ["1.5", distance, "1.0"],
            "_chem_comp_bond.value_dist_esd": ["0.02"] * 3,
            "_chem_comp_angle.comp_id": [code] * 2,
            "_chem_comp_angle.atom_id_1": ["C5", "C5'"],
            "_chem_comp_angle.atom_id_2": ["C5'", "N3"],
            "_chem_comp_angle.atom_id_3": ["N3", "H1"],
            "_chem_comp_angle.value_angle": ["110"] * 2,
            "_chem_comp_angle.value_angle_esd": ["2"] * 2,
        })
    return values


def _ref(path, directory, *, candidate=False):
    return {"anchor": "candidate_directory" if candidate else "run",
            "path" if candidate else "relative_path": path.relative_to(directory).as_posix(),
            "sha256": _sha(path.read_bytes()), "size": path.stat().st_size}


@pytest.fixture
def delivered(tmp_path):
    origin = tmp_path / "original-NASolve"
    nar = tmp_path / "original-NARestraints"
    for relative in ("src/nasolve", "MR_frames/5W6W"):
        shutil.copytree(ROOT / relative, origin / relative,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for relative in ("docs/recipes/synthetic-dna-combined.toml", "scripts/cif_native_probe_template.py"):
        path = origin / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, path)
    shutil.copytree(Path(restraints.__file__).resolve().parent, nar / "restraints",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    _initialize_git(origin)
    _initialize_git(nar)
    script = tmp_path / "relocated-downloads/05_Cedar_probe_cif_native.py"
    builder = _module(ROOT / "scripts/build_synthetic_dna_shuttle.py", "native_probe_builder")
    metadata = builder.build(origin, nar, script, template_name="cif_native_probe_template.py",
                             delivery_prefix="05_Cedar")
    shutil.rmtree(origin)
    shutil.rmtree(nar)

    run = tmp_path / "preserved-dataset/AutoMR/run_001"
    source_dir = run / "PostMR/Restraints/source_dictionaries"
    source_dir.mkdir(parents=True)
    sources = []
    for code in ("Q11", "Y22", "Z33"):
        path = source_dir / (code + ".cif")
        path.write_text(_emit(_component(code, numerical=code == "Z33")))
        sources.append(path)
    runtime_dir = run / "PostMR/Restraints"
    runtime_paths = []
    for index, path in enumerate(sources):
        destination = runtime_dir / ("explicit_" + str(index) + ".cif")
        destination.write_bytes(path.read_bytes())
        runtime_paths.append(destination)
    mod = runtime_dir / "recorded_modification.cif"
    mod.write_text("data_mod_fixture\nloop_\n_chem_mod_atom.mod_id\n_chem_mod_atom.function\n"
                   "_chem_mod_atom.atom_id\nFIX delete XX\n")
    phil = runtime_dir / "recorded_parameters.phil"
    phil.write_text("refinement {\n  geometry_restraints {\n  }\n}\n")
    eff = runtime_dir / "recorded_secondary.eff"
    eff.write_text("refinement {\n  secondary_structure { enabled = False }\n}\n")
    runtime_paths.extend([mod, phil, eff])
    generated = run / "PostMR/ReadySet/prepared_model.ligands.cif"
    generated.parent.mkdir(parents=True)
    generated.write_text(_emit(_component("Q11", numerical=True, distance="0.000"))
                         + _emit(_component("Y22", numerical=True, distance="1.41"))
                         + _emit(_component("Z33", numerical=True, distance="9.9")))
    model = run / "PostMR/Model/prepared_model.pdb"
    model.parent.mkdir(parents=True)
    model.write_text("HETATM    1  C5  Q11 A   1       0.000   0.000   0.000  1.00 20.00           C\nEND\n")
    audit = assess_dictionaries(sources, stage="postmr-source")
    audit["inputs"] = [_ref(path, run) for path in sources]
    audit["model"] = _ref(model, run)
    audit["runtime_assessment"] = {"schema_version": 1, "audit_kind": "cif_restraint_assessment",
                                   "stage": "postmr-runtime-source",
                                   "inputs": [_ref(path, run) for path in runtime_paths],
                                   "model": _ref(model, run)}
    audit_path = runtime_dir / "cif_doctor_source.json"
    audit_path.write_text(json.dumps(audit) + "\n")

    candidate_dir = tmp_path / "preserved-generation/candidates/cif-generation-fixture"
    candidate_dir.mkdir(parents=True)
    candidate_files = {}
    for name, data in {
            "source.cif": sources[0].read_bytes(),
            "candidate.cif": _emit(_component("Q11", numerical=True, distance="1.42")).encode(),
            "elbow.log": b"Invented successful native generation fixture\n",
            "elbow_help.log": b"Invented installed --pH=PH help\n",
            "source_ideal.pdb": b"Invented naming seed fixture\n"}.items():
        path = candidate_dir / name
        path.write_bytes(data)
        candidate_files[name] = path
    generation = {
        "schema_version": 1, "audit_kind": "cif_numerical_generation_candidate",
        "policy_id": "cif-independent-elbow-candidate-v3", "component_id": "Q11",
        "status": "CANDIDATE_REVIEW", "automatic_adoption": False,
        "source_preserved": True, "frozen_source_preserved": True,
        "execution": {"status": "COMPLETED", "returncode": 0},
        "source": _ref(candidate_files["source.cif"], candidate_dir, candidate=True),
        "seed": {"artifact": _ref(candidate_files["source_ideal.pdb"], candidate_dir, candidate=True)},
        "generator_capabilities": {"status": "SUPPORTED",
                                   "help_output": _ref(candidate_files["elbow_help.log"], candidate_dir, candidate=True)},
        "source_state_preservation": {"generator_option": "--pH", "generator_value": "low"},
        "outputs": [_ref(path, candidate_dir, candidate=True) for path in candidate_files.values()],
    }
    generation_path = candidate_dir / "generation_receipt.json"
    generation_path.write_text(json.dumps(generation) + "\n")
    generation_probe_path = candidate_dir.parent.parent / "probe_receipt.json"
    generation_probe_path.write_text(json.dumps({
        "schema_version": 1, "kind": "cif-generation-native-probe",
        "status": "CANDIDATES_AWAITING_REVIEW", "native_generation": "REQUESTED",
        "automatic_adoption": False, "candidates": {"Q11": generation},
        "snapshots": {"source_audit": {"historical_source": "/missing/historical/source_audit.json",
                                        "sha256": _sha(audit_path.read_bytes()), "size": audit_path.stat().st_size},
                      "failed_readyset": {"historical_source": "/missing/historical/readyset.cif",
                                          "sha256": _sha(generated.read_bytes()), "size": generated.stat().st_size}}
    }) + "\n")
    poison = tmp_path / "frozen-checkout/src"
    for package in ("nasolve", "restraints"):
        path = poison / package / "__init__.py"
        path.parent.mkdir(parents=True)
        path.write_text("raise RuntimeError('DO NOT IMPORT THE FROZEN CHECKOUT')\n")
    preserved = {path: path.read_bytes() for root in (run, candidate_dir, poison)
                 for path in root.rglob("*") if path.is_file()}
    preserved[generation_probe_path] = generation_probe_path.read_bytes()
    return {"script": script, "run": run, "sources": sources, "runtime": runtime_paths,
            "candidate": candidate_dir, "generation": generation_path,
            "generation_probe": generation_probe_path, "files": candidate_files,
            "audit": audit_path, "model": model, "generated": generated, "poison": poison,
            "metadata": metadata, "output": tmp_path / "new-probes", "preserved": preserved,
            "working": tmp_path / "unrelated-working-directory"}


def _launch(fixture, *extra):
    fixture["working"].mkdir(exist_ok=True)
    env = dict(os.environ)
    env.update(PYTHONPATH=str(fixture["poison"]), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-B", str(fixture["script"]), "--inspect-only",
                           "--run", str(fixture["run"]), "--candidate-directory", str(fixture["candidate"]),
                           "--generation-probe", str(fixture["generation_probe"]),
                           "--output-parent", str(fixture["output"]), "--phenix-root",
                           str(fixture["working"] / "no-phenix"), *extra],
                          cwd=fixture["working"], env=env, capture_output=True, text=True, timeout=30)


def _receipt(result):
    line = next(row for row in result.stdout.splitlines() if row.startswith("REVIEW ZIP: "))
    review = Path(line.removeprefix("REVIEW ZIP: "))
    return review, json.loads((review.parent / "probe_receipt.json").read_text())


def _preserved(fixture):
    assert all(path.read_bytes() == data for path, data in fixture["preserved"].items())


@pytest.mark.parametrize("generation_policy", ["cif-independent-elbow-candidate-v3",
                                             "cif-independent-elbow-candidate-v4"])
def test_relocated_inspection_preserves_bytes_precedence_and_full_bound_runtime(delivered, generation_policy):
    generation = json.loads(delivered["generation"].read_text())
    generation["policy_id"] = generation_policy
    delivered["generation"].write_text(json.dumps(generation) + "\n")
    probe = json.loads(delivered["generation_probe"].read_text())
    probe["candidates"]["Q11"] = generation
    delivered["generation_probe"].write_text(json.dumps(probe) + "\n")
    for path in (delivered["generation"], delivered["generation_probe"]):
        delivered["preserved"][path] = path.read_bytes()
    result = _launch(delivered)
    assert result.returncode == 0, result.stderr + result.stdout
    review, receipt = _receipt(result)
    assert receipt["status"] == "INSPECTED"
    assert receipt["native_validation"] == "NOT_RUN"
    assert receipt["automatic_adoption"] is False
    assert receipt["linked_site_qualification"] == "NOT_RUN"
    assert receipt["preserved_inputs"] == "UNCHANGED"
    assert receipt["generation_probe_baseline"] == "CHECKSUM_BOUND"
    assert receipt["build"] == delivered["metadata"]
    assert receipt["component_id"] == "Q11"
    assert receipt["candidate_inspection"]["status"] == "CANDIDATE_REVIEW"
    assert review.parent.name.startswith("05_Cedar_cif-native-probe-")
    assert review.name == "05_Cedar_" + review.parent.name.rsplit("-", 1)[-1] + "_cif_native_review.zip"
    assert "CIF native diagnostic: 05_Cedar | cif-native-bundle-inventory-v1" in result.stdout
    assert "phenix_version" not in receipt
    assert list(delivered["working"].iterdir()) == []
    selected = [review.parent / record["path"] for record in receipt["selected_bundle"]["selected_inputs"]]
    cifs = [path for path in selected if path.suffix == ".cif"]
    codes = [code for path in cifs for code in dictionary_component_codes(path)]
    assert sorted(codes) == ["Q11", "Y22", "Z33"]
    blocks = {next(iter(dictionary_component_codes(path))): _blocks(path)[0].values
              for path in cifs if len(dictionary_component_codes(path)) == 1}
    assert blocks["Q11"]["_chem_comp_bond.value_dist"][1] == "1.42"
    assert blocks["Y22"]["_chem_comp_bond.value_dist"][1] == "1.41"
    assert blocks["Z33"]["_chem_comp_bond.value_dist"][1] == "1.4"
    assert not any(path.read_bytes() == delivered["sources"][0].read_bytes() for path in selected)
    assert len([path for path in selected if path.suffix in {".phil", ".eff"}]) == 2
    assert any(path.read_bytes() == delivered["runtime"][3].read_bytes() for path in selected)
    assert receipt["selected_bundle"]["new_generic_modifications"] is False
    assert len(receipt["selected_bundle"]["replaced_runtime_sources"]) == 1
    for record in receipt["snapshots"].values():
        copied = review.parent / record["path"]
        assert copied.read_bytes() == Path(record["historical_source"]).read_bytes()
        assert (_sha(copied.read_bytes()), copied.stat().st_size) == (record["sha256"], record["size"])
    with zipfile.ZipFile(review) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert set(archive.namelist()) == {*manifest, "manifest.json"}
        assert not any(name.startswith("runtime/") or name.endswith((".pickle", ".pkl")) for name in manifest)
        for name, expected in manifest.items():
            data = archive.read(name)
            assert (_sha(data), len(data)) == (expected["sha256"], expected["bytes"])
    _preserved(delivered)


@pytest.mark.parametrize("which", ["source", "runtime", "model", "candidate", "log", "seed"])
def test_bound_inputs_cannot_change_before_native_interpretation(delivered, which):
    path = {"source": delivered["sources"][0], "runtime": delivered["runtime"][-1],
            "model": delivered["model"], "candidate": delivered["files"]["candidate.cif"],
            "log": delivered["files"]["elbow.log"], "seed": delivered["files"]["source_ideal.pdb"]}[which]
    path.write_bytes(path.read_bytes() + b"# changed\n")
    delivered["preserved"][path] = path.read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    _, receipt = _receipt(result)
    assert receipt["status"] == "FAILED"
    assert receipt["native_validation"] == "NOT_RUN"
    assert "changed" in receipt["error"] or "checksum" in receipt["error"]
    _preserved(delivered)


def test_candidate_claim_does_not_override_a_changed_frozen_chemistry_authority(delivered):
    source = delivered["sources"][0]
    source.write_text(source.read_text().replace("SING", "DOUB", 1))
    audit = json.loads(delivered["audit"].read_text())
    audit["inputs"][0] = _ref(source, delivered["run"])
    delivered["audit"].write_text(json.dumps(audit) + "\n")
    for path in (source, delivered["audit"]):
        delivered["preserved"][path] = path.read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    _, receipt = _receipt(result)
    assert "checksum or byte size mismatch" in receipt["error"]
    assert receipt["native_validation"] == "NOT_RUN"
    _preserved(delivered)


def test_hash_bound_candidate_is_reassessed_instead_of_trusting_status_claim(delivered):
    candidate = delivered["files"]["candidate.cif"]
    candidate.write_text(_emit(_component("Q11", numerical=True, distance="0.000")))
    generation = json.loads(delivered["generation"].read_text())
    generation["outputs"] = [(_ref(candidate, delivered["candidate"], candidate=True)
                             if record["path"] == "candidate.cif" else record)
                            for record in generation["outputs"]]
    delivered["generation"].write_text(json.dumps(generation) + "\n")
    generation_probe = json.loads(delivered["generation_probe"].read_text())
    generation_probe["candidates"]["Q11"] = generation
    delivered["generation_probe"].write_text(json.dumps(generation_probe) + "\n")
    for path in (candidate, delivered["generation"], delivered["generation_probe"]):
        delivered["preserved"][path] = path.read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    review, receipt = _receipt(result)
    assert "Current source/candidate assessment rejected" in receipt["error"]
    assert json.loads((review.parent / "candidate_inspection.json").read_text())["status"] == "REJECTED"
    assert receipt["native_validation"] == "NOT_RUN"
    _preserved(delivered)


@pytest.mark.parametrize("which", ["raw_readyset", "source_audit"])
def test_generation_probe_binds_baseline_files_despite_valid_current_content(delivered, which):
    if which == "raw_readyset":
        path = delivered["generated"]
        path.write_text(_emit(_component("Q11", numerical=True, distance="1.99"))
                        + _emit(_component("Y22", numerical=True, distance="1.41"))
                        + _emit(_component("Z33", numerical=True, distance="9.9")))
    else:
        path = delivered["audit"]
        audit = json.loads(path.read_text())
        audit["inputs"][0] = _ref(delivered["sources"][0], delivered["run"])
        audit["new_current_metadata"] = "This is valid current JSON but not the preserved probe baseline"
        path.write_text(json.dumps(audit) + "\n")
    delivered["preserved"][path] = path.read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    _, receipt = _receipt(result)
    assert "checksum or byte size mismatch" in receipt["error"]
    assert receipt["native_validation"] == "NOT_RUN"
    _preserved(delivered)


def test_candidate_receipt_must_match_explicit_generation_probe(delivered):
    generation = json.loads(delivered["generation"].read_text())
    generation["distinct_receipt_metadata"] = "A different candidate receipt"
    delivered["generation"].write_text(json.dumps(generation) + "\n")
    delivered["preserved"][delivered["generation"]] = delivered["generation"].read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    _, receipt = _receipt(result)
    assert "differs from its selected generation-probe evidence" in receipt["error"]
    assert receipt["native_validation"] == "NOT_RUN"
    _preserved(delivered)


@pytest.mark.parametrize("missing", ["source_audit", "failed_readyset"])
def test_missing_generation_baseline_identity_does_not_disable_hash_binding(delivered, missing):
    proof = json.loads(delivered["generation_probe"].read_text())
    del proof["snapshots"][missing]
    delivered["generation_probe"].write_text(json.dumps(proof) + "\n")
    delivered["preserved"][delivered["generation_probe"]] = delivered["generation_probe"].read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    _, receipt = _receipt(result)
    assert "requires a SHA-256 and byte size" in receipt["error"]
    assert receipt["native_validation"] == "NOT_RUN"
    _preserved(delivered)


@pytest.mark.parametrize("field", ["status", "policy_id", "automatic_adoption"])
def test_unreviewed_receipt_is_rejected(delivered, field):
    generation = json.loads(delivered["generation"].read_text())
    generation[field] = {"status": "REJECTED", "policy_id": "cif-independent-elbow-candidate-v2",
                         "automatic_adoption": True}[field]
    delivered["generation"].write_text(json.dumps(generation) + "\n")
    delivered["preserved"][delivered["generation"]] = delivered["generation"].read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    _, receipt = _receipt(result)
    assert "Require a completed source-preserving v3" in receipt["error"]
    _preserved(delivered)


def test_candidate_ref_cannot_escape_its_preserved_directory(delivered):
    generation = json.loads(delivered["generation"].read_text())
    candidate_record = next(record for record in generation["outputs"] if record["path"] == "candidate.cif")
    candidate_record["path"] = "../candidate.cif"
    delivered["generation"].write_text(json.dumps(generation) + "\n")
    delivered["preserved"][delivered["generation"]] = delivered["generation"].read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    _, receipt = _receipt(result)
    assert receipt["native_validation"] == "NOT_RUN"
    _preserved(delivered)


def test_repeat_inspections_have_distinct_receipts_and_preserve_prior_evidence(delivered):
    first = _launch(delivered)
    assert first.returncode == 0, first.stderr + first.stdout
    first_zip, _ = _receipt(first)
    first_bytes = first_zip.read_bytes()
    second = _launch(delivered)
    assert second.returncode == 0, second.stderr + second.stdout
    second_zip, _ = _receipt(second)
    assert first_zip != second_zip
    assert first_zip.read_bytes() == first_bytes
    _preserved(delivered)


@pytest.mark.parametrize("protected", ["run", "candidate", "generation_probe_directory"])
def test_fresh_outputs_cannot_be_allocated_inside_the_original_packet(delivered, protected):
    parent = (delivered["generation_probe"].parent if protected == "generation_probe_directory"
              else delivered[protected])
    result = _launch(delivered, "--output-parent", str(parent))
    assert result.returncode == 2
    assert "outside the preserved run, candidate and generation-probe directories" in result.stderr
    assert not list(parent.glob("05_Cedar_cif-native-probe-*"))
    _preserved(delivered)
