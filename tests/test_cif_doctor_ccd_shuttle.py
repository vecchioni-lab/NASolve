"""Offline, integrity-bound control runner and relocated single-file delivery."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

import pytest

from nasolve.cif_doctor import assess_dictionaries
from nasolve.ligand_profiles import _emit
from tests.test_cif_doctor import component

ROOT = Path(__file__).parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def corpus(tmp_path):
    payload = _emit(component(numeric=False)).encode("utf-8")
    manifest = {"schema_version": 1, "components": [{"code": "X", "filename": "X.cif",
                "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}]}
    archive = tmp_path / "controls.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("source_manifest.json", json.dumps(manifest))
        handle.writestr("source_audit_receipts.json", '{"older_reference_only": true}')
        handle.writestr("README.txt", "Graph-only control\n")
        handle.writestr("ccd/X.cif", payload)
    return archive, payload


def builder():
    return module(ROOT / "scripts" / "build_cif_doctor_ccd_shuttle.py", "shuttle_builder")


def launch(script, archive, output):
    return subprocess.run([sys.executable, "-B", str(script), str(archive), "--output", str(output), "--json"],
                          cwd=script.parent, capture_output=True, text=True)


def test_delivered_runner_audits_offline_after_original_checkout_is_gone(tmp_path):
    origin = tmp_path / "original-checkout"
    for relative in ("src/nasolve/cif_doctor.py", "src/nasolve/dictionary_compatibility.py",
                     "src/nasolve/ligand_profiles.py", "src/nasolve/phosphate.py",
                     "scripts/cif_doctor_ccd_shuttle_template.py"):
        target = origin / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    archive, payload = corpus(tmp_path)
    delivery = tmp_path / "downloaded-shuttle.py"
    metadata = builder().build(origin, archive, delivery)
    moved = tmp_path / "relocated-downloads"
    moved.mkdir()
    shutil.move(str(delivery), moved / delivery.name)
    shutil.move(str(archive), moved / archive.name)
    shutil.rmtree(origin)
    output = moved / "fresh-audit"
    result = launch(moved / delivery.name, moved / archive.name, output)
    assert result.returncode == 0, result.stderr
    compact = json.loads(result.stdout)
    assert compact["status_counts"] == {"source": {"PASS": 1}, "effective": {"REVIEW": 1}}
    summary = json.loads((output / "audit_summary.json").read_text())
    assert summary["input_integrity"] == "UNCHANGED"
    assert summary["native_interpretation"] == "NOT_RUN"
    assert summary["coordinate_changes"] is False
    assert (output / "controls/ccd/X.cif").read_bytes() == payload
    assert summary["build"]["assessor_source_sha256"] == metadata["assessor_source_sha256"]
    for stage in ("source", "effective"):
        delivered = json.loads((output / f"receipts/X.{stage}.json").read_text())
        direct = assess_dictionaries([output / "controls/ccd/X.cif"], stage=stage)
        assert delivered == direct
        ref = summary["results"][0][stage]["receipt"]
        assert ref["anchor"] == "output"
        assert hashlib.sha256((output / ref["relative_path"]).read_bytes()).hexdigest() == ref["sha256"]


def test_zip_tampering_and_existing_output_are_refused_without_overwrite(tmp_path):
    archive, _ = corpus(tmp_path)
    delivery = tmp_path / "shuttle.py"
    builder().build(ROOT, archive, delivery)
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "unrelated.txt"
    sentinel.write_text("preserve")
    original = archive.read_bytes()
    result = launch(delivery, archive, output)
    assert result.returncode == 1
    assert "File exists" in result.stderr
    assert sentinel.read_text() == "preserve"
    archive.write_bytes(original + b"altered")
    new = tmp_path / "never-created"
    result = launch(delivery, archive, new)
    assert result.returncode == 1
    assert "ZIP SHA-256 differs" in result.stderr
    assert not new.exists()


def test_repeated_one_command_runs_create_distinct_outputs_beside_zip(tmp_path):
    archive, _ = corpus(tmp_path)
    delivery = tmp_path / "shuttle.py"
    builder().build(ROOT, archive, delivery)
    working = tmp_path / "unrelated-working-directory"
    working.mkdir()
    folders = []
    for _ in range(2):
        result = subprocess.run([sys.executable, "-B", str(delivery), str(archive), "--json"],
                                cwd=working, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        folder = Path(json.loads(result.stdout)["output"])
        assert folder.parent == archive.parent
        assert (folder / "audit_summary.json").is_file()
        folders.append(folder)
    assert folders[0] != folders[1]
    assert list(working.iterdir()) == []


@pytest.mark.parametrize("kind", ["traversal", "absolute", "windows", "duplicate", "symlink", "extra", "missing", "cif-mismatch"])
def test_reviewed_archive_validation_rejects_unsafe_or_unmanifested_members(tmp_path, kind):
    archive, payload = corpus(tmp_path)
    members = {name: data for name, data in module(ROOT / "scripts" / "cif_doctor_ccd_shuttle_template.py", "raw_template")._archive_members(archive.read_bytes()).items()}
    if kind == "missing":
        del members["ccd/X.cif"]
    elif kind == "cif-mismatch":
        members["ccd/X.cif"] = payload + b"# changed\n"
    rewritten = tmp_path / "changed.zip"
    with zipfile.ZipFile(rewritten, "w") as handle:
        for name, data in members.items():
            handle.writestr(name, data)
        if kind in {"traversal", "absolute", "windows", "extra"}:
            handle.writestr({"traversal": "../outside", "absolute": "/outside", "windows": "C:\\outside", "extra": "unexpected.txt"}[kind], "bad")
        elif kind == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate name"):
                handle.writestr("ccd/X.cif", payload)
        elif kind == "symlink":
            info = zipfile.ZipInfo("linked")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            handle.writestr(info, "../outside")
    delivery = tmp_path / "shuttle.py"
    # Build pins the deliberately malformed archive; structural validation must
    # still refuse it independently of the whole-archive checksum guard.
    builder().build(ROOT, rewritten, delivery)
    output = tmp_path / "never-created"
    result = launch(delivery, rewritten, output)
    assert result.returncode == 1
    assert not output.exists()
    assert not (tmp_path / "outside").exists()


def test_builder_refuses_replacing_a_delivered_script(tmp_path):
    archive, _ = corpus(tmp_path)
    delivery = tmp_path / "shuttle.py"
    delivery.write_text("existing")
    with pytest.raises(FileExistsError):
        builder().build(ROOT, archive, delivery)
    assert delivery.read_text() == "existing"
