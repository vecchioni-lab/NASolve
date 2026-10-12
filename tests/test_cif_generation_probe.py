"""The candidate probe diagnoses constructed CIFs without its source checkouts."""

import base64
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
from nasolve.ligand_profiles import _emit


ROOT = Path(__file__).resolve().parents[1]


def _module(path, name):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _initialize_git(root):
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run([
        "git", "-C", str(root), "-c", "user.name=Probe fixture",
        "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
        "commit", "--no-verify", "-qm", "Isolated public source fixture",
    ], check=True, capture_output=True)


def _component(code, *, numerical=False, zero_bond=False):
    # Invented, public test chemistry only. No returned experimental CIF enters
    # this fixture. The prime-bearing names must remain distinct in receipts.
    values = {
        "data_": "comp_" + code,
        "_chem_comp.id": [code],
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
            "_chem_comp_bond.value_dist": ["1.5", "0.000" if zero_bond else "1.4", "1.0"],
            "_chem_comp_bond.value_dist_esd": ["0.02"] * 3,
            "_chem_comp_angle.comp_id": [code] * 2,
            "_chem_comp_angle.atom_id_1": ["C5", "C5'"],
            "_chem_comp_angle.atom_id_2": ["C5'", "N3"],
            "_chem_comp_angle.atom_id_3": ["N3", "H1"],
            "_chem_comp_angle.value_angle": ["110"] * 2,
            "_chem_comp_angle.value_angle_esd": ["2"] * 2,
        })
    return values


@pytest.fixture
def delivered(tmp_path, request):
    bad_code = getattr(request, "param", "XRAWR")
    origin = tmp_path / "original-NASolve"
    narestraints_origin = tmp_path / "original-NARestraints"
    for relative in ("src/nasolve", "MR_frames/5W6W"):
        shutil.copytree(ROOT / relative, origin / relative,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for relative in ("docs/recipes/synthetic-dna-combined.toml",
                     "scripts/cif_generation_probe_template.py"):
        destination = origin / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    shutil.copytree(Path(restraints.__file__).resolve().parent,
                    narestraints_origin / "restraints",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    _initialize_git(origin)
    _initialize_git(narestraints_origin)
    script = tmp_path / "relocated-downloads/04_Cedar_probe_cif_generation.py"
    builder = _module(ROOT / "scripts/build_synthetic_dna_shuttle.py", "cif_probe_builder")
    metadata = builder.build(origin, narestraints_origin, script,
                             template_name="cif_generation_probe_template.py")
    shutil.rmtree(origin)
    shutil.rmtree(narestraints_origin)

    run = tmp_path / "preserved-dataset/AutoMR/run_001"
    sources = run / "PostMR/Restraints/source_dictionaries"
    sources.mkdir(parents=True)
    dictionaries = []
    for code in (bad_code, "Y"):
        path = sources / (code + ".cif")
        path.write_text(_emit(_component(code)), encoding="utf-8")
        dictionaries.append(path)
    generated = run / "PostMR/ReadySet/prepared_model.ligands.cif"
    generated.parent.mkdir(parents=True)
    generated.write_text(
        _emit(_component(bad_code, numerical=True, zero_bond=True))
        + _emit(_component("Y", numerical=True)), encoding="utf-8",
    )
    source_audit = assess_dictionaries(dictionaries, stage="postmr-source")
    source_audit["inputs"] = [{
        "anchor": "run", "relative_path": path.relative_to(run).as_posix(),
        "sha256": _sha(path.read_bytes()), "size": path.stat().st_size,
    } for path in dictionaries]
    audit_path = run / "PostMR/Restraints/cif_doctor_source.json"
    audit_path.write_text(json.dumps(source_audit, indent=2) + "\n")
    (run / "report.json").write_text('{"status": "POSTMR_FAILED", "fixture": true}\n')
    preserved = {path: path.read_bytes() for path in run.rglob("*") if path.is_file()}

    poison = tmp_path / "frozen-user-checkout/src"
    for package in ("nasolve", "restraints"):
        path = poison / package / "__init__.py"
        path.parent.mkdir(parents=True)
        path.write_text("raise RuntimeError('PRESERVED CHECKOUT MUST NOT BE IMPORTED')\n")
        preserved[path] = path.read_bytes()
    return {
        "script": script, "metadata": metadata, "run": run,
        "sources": dictionaries, "generated": generated, "audit": audit_path,
        "bad_code": bad_code, "output": tmp_path / "new-probes",
        "poison": poison, "preserved": preserved,
        "working": tmp_path / "unrelated-working-directory",
    }


def _launch(fixture, *extra):
    fixture["working"].mkdir(exist_ok=True)
    environment = dict(os.environ)
    environment.update(PYTHONPATH=str(fixture["poison"]), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([
        sys.executable, "-B", str(fixture["script"]), "--inspect-only",
        "--run", str(fixture["run"]), "--output-parent", str(fixture["output"]),
        "--phenix-root", str(fixture["working"] / "no-native-installation"), *extra,
    ], cwd=fixture["working"], env=environment, capture_output=True, text=True,
       timeout=30)


def _receipt(result):
    line = next(row for row in result.stdout.splitlines() if row.startswith("REVIEW ZIP: "))
    review = Path(line.removeprefix("REVIEW ZIP: "))
    return review, json.loads((review.parent / "probe_receipt.json").read_text())


def _preserved(fixture):
    assert all(path.read_bytes() == data for path, data in fixture["preserved"].items())


@pytest.mark.parametrize("delivered", ["XRAWR", "Q99"], indirect=True)
def test_relocated_inspect_probe_is_general_and_preserves_all_original_inputs(delivered):
    result = _launch(delivered)
    assert result.returncode == 0, result.stderr + result.stdout
    review, receipt = _receipt(result)
    session = review.parent
    code = delivered["bad_code"]
    assert receipt["status"] == "INSPECTED"
    assert receipt["native_generation"] == "NOT_RUN"
    assert receipt["automatic_adoption"] is False
    assert receipt["components"] == sorted([code, "Y"])
    assert receipt["regeneration_queue"] == [code]
    assert "IGU" not in receipt["components"]
    assert receipt["preserved_inputs"] == "UNCHANGED"
    assert receipt["build"] == delivered["metadata"]
    assert receipt["build"]["kind"] == "cif-generation-probe-shuttle"
    assert receipt["delivery_prefix"] == "04_Cedar"
    assert session.name.startswith("04_Cedar_cif-generation-probe-")
    assert review.name == "04_Cedar_" + session.name.rsplit("-", 1)[-1] + "_cif_generation_review.zip"
    assert "CIF generation probe: 04_Cedar | cif-independent-elbow-candidate-v3" in result.stdout
    assert receipt["build"]["private_diffraction_included"] is False
    assert receipt["build"]["prior_native_results_included"] is False
    assert "candidates" not in receipt and not (session / "candidates").exists()
    assert "phenix_version" not in receipt
    assert list(delivered["working"].iterdir()) == []
    assert not (delivered["run"] / "AutoSol").exists()
    assert not (delivered["run"] / "AutoRefine").exists()
    _preserved(delivered)

    copies = {"source_audit": session / "inputs/source_audit.json",
              "failed_readyset": session / "inputs/failed_readyset.cif"}
    copies.update({str(index): session / "inputs/sources" / (str(index) + "_" + source.name)
                   for index, source in enumerate(delivered["sources"])})
    assert set(receipt["snapshots"]) == set(copies)
    for key, copied in copies.items():
        record = receipt["snapshots"][key]
        original = Path(record["historical_source"])
        assert copied.read_bytes() == original.read_bytes()
        assert (_sha(copied.read_bytes()), copied.stat().st_size) == (record["sha256"], record["size"])
    assert copies["0"].read_bytes() == delivered["sources"][0].read_bytes()

    assessment = json.loads((session / "failed_readyset_assessment.json").read_text())
    assert {row["component_id"] for row in assessment["components"]} == {code, "Y"}
    assert next(row for row in assessment["components"] if row["component_id"] == code)["status"] == "INVALID"
    inspections = json.loads((session / "component_inspections.json").read_text())
    assert inspections[code]["component_id"] == code
    assert inspections[code]["status"] == "REJECTED"
    assert inspections["Y"]["status"] == "CANDIDATE_REVIEW"
    zero, = [issue for issue in inspections[code]["numerical_issues"]
             if issue["code"] == "numeric-domain-violation"]
    assert zero["measurements"]["atoms"] == ["C5'", "N3"]

    for name, expected in receipt["build"]["runtime_files"].items():
        data = (session / "runtime" / name).read_bytes()
        assert (_sha(data), len(data)) == (expected["sha256"], expected["size"])
    assert "src/nasolve/cif_generation.py" in receipt["build"]["runtime_files"]
    with zipfile.ZipFile(review) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert set(archive.namelist()) == {*manifest, "manifest.json"}
        assert not any(name.startswith("runtime/") for name in manifest)
        assert "inputs/sources/0_" + code + ".cif" in manifest
        assert "probe_receipt.json" in manifest
        for name, expected in manifest.items():
            payload = archive.read(name)
            assert (_sha(payload), len(payload)) == (expected["sha256"], expected["bytes"])
            assert payload == (session / name).read_bytes()


@pytest.mark.parametrize("source_index", [0, 1])
def test_any_frozen_source_tamper_is_rejected_before_generation(delivered, source_index):
    changed = delivered["sources"][source_index]
    changed.write_bytes(changed.read_bytes() + b"# changed since source audit\n")
    delivered["preserved"][changed] = changed.read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    review, receipt = _receipt(result)
    assert receipt["status"] == "FAILED"
    assert receipt["native_generation"] == "NOT_RUN"
    assert "anchor" in receipt["error"] or "checksum" in receipt["error"]
    assert not (review.parent / "candidates").exists()
    _preserved(delivered)


@pytest.mark.parametrize("escape", ["traversal", "absolute", "symlink"])
def test_source_anchor_escape_cannot_trigger_generation(delivered, escape):
    outside = delivered["run"].parent / "outside.cif"
    outside.write_bytes(delivered["sources"][0].read_bytes())
    audit = json.loads(delivered["audit"].read_text())
    record = audit["inputs"][0]
    if escape == "traversal":
        record["relative_path"] = "../outside.cif"
    elif escape == "absolute":
        record.pop("relative_path")
        record.update(anchor="absolute", absolute_path=str(outside))
    else:
        link = delivered["run"] / "escaping-source.cif"
        link.symlink_to(outside)
        record["relative_path"] = link.name
    delivered["audit"].write_text(json.dumps(audit) + "\n")
    delivered["preserved"][delivered["audit"]] = delivered["audit"].read_bytes()
    delivered["preserved"][outside] = outside.read_bytes()
    result = _launch(delivered)
    assert result.returncode == 2
    review, receipt = _receipt(result)
    assert receipt["status"] == "FAILED"
    assert receipt["native_generation"] == "NOT_RUN"
    assert "escapes the recorded run anchor" in receipt["error"]
    assert not (review.parent / "candidates").exists()
    _preserved(delivered)


def test_probe_runtime_tamper_is_rejected_before_output_allocation(delivered):
    module = _module(delivered["script"], "assembled_cif_generation_probe")
    changed = base64.b64decode(module.RUNTIME_BASE64) + b"changed-runtime"
    delivered["script"].write_text(delivered["script"].read_text().replace(
        repr(module.RUNTIME_BASE64), repr(base64.b64encode(changed).decode("ascii")), 1))
    result = _launch(delivered)
    assert result.returncode == 2
    assert "Embedded runtime SHA-256 changed" in result.stderr
    assert not delivered["output"].exists()
    _preserved(delivered)


def test_repeated_inspection_keeps_distinct_probe_receipts(delivered):
    first = _launch(delivered)
    assert first.returncode == 0, first.stderr + first.stdout
    first_zip, _ = _receipt(first)
    first_bytes = first_zip.read_bytes()
    first_receipt = (first_zip.parent / "probe_receipt.json").read_bytes()
    second = _launch(delivered)
    assert second.returncode == 0, second.stderr + second.stdout
    second_zip, _ = _receipt(second)
    assert first_zip.parent != second_zip.parent
    assert first_zip.read_bytes() == first_bytes
    assert (first_zip.parent / "probe_receipt.json").read_bytes() == first_receipt
    _preserved(delivered)


@pytest.mark.parametrize("statuses", [("FAILED",), ("REJECTED",), ("FAILED", "REJECTED")])
def test_failed_generation_never_claims_candidates_are_awaiting_review(statuses):
    module = _module(ROOT / "scripts/cif_generation_probe_template.py", "probe_summary")
    summary = module._candidate_status({str(i): {"status": status} for i, status in enumerate(statuses)})
    assert "AWAITING_REVIEW" not in summary


@pytest.mark.parametrize("prefix", ["../escape", "/absolute", "two words", "Cedar/04", "λ"])
def test_delivery_identifier_cannot_escape_or_create_ambiguous_filename(tmp_path, prefix):
    builder = _module(ROOT / "scripts/build_synthetic_dna_shuttle.py", "prefix_builder")
    destination = tmp_path / "new-delivery.py"
    with pytest.raises(ValueError, match="Delivery prefix"):
        builder.build(tmp_path / "missing-source", tmp_path / "missing-narestraints", destination,
                      template_name="cif_generation_probe_template.py", delivery_prefix=prefix)
    assert not destination.exists()
