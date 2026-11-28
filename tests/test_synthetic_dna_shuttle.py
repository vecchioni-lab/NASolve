"""The delivered synthetic-DNA shuttle must work without its source checkouts."""

import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

import pytest
import restraints


ROOT = Path(__file__).resolve().parents[1]


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _initialize_git(root):
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run([
        "git", "-C", str(root), "-c", "user.name=Shuttle fixture",
        "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
        "commit", "--no-verify", "-qm", "Isolated source fixture",
    ], check=True, capture_output=True)


@pytest.fixture
def delivered(tmp_path):
    origin = tmp_path / "original-NASolve"
    narestraints_origin = tmp_path / "original-NARestraints"
    for relative in ("src/nasolve", "MR_frames/5W6W"):
        shutil.copytree(ROOT / relative, origin / relative,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for relative in ("docs/recipes/synthetic-dna-combined.toml",
                     "scripts/synthetic_dna_shuttle_template.py"):
        destination = origin / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    shutil.copytree(Path(restraints.__file__).resolve().parent,
                    narestraints_origin / "restraints",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    _initialize_git(origin)
    _initialize_git(narestraints_origin)
    downloads = tmp_path / "relocated-downloads"
    downloads.mkdir()
    script = downloads / "run_synthetic_dna_mechanics.py"
    builder = _module(ROOT / "scripts/build_synthetic_dna_shuttle.py", "synthetic_shuttle_builder")
    metadata = builder.build(origin, narestraints_origin, script)
    shutil.rmtree(origin)
    shutil.rmtree(narestraints_origin)

    donor = tmp_path / "private-donor"
    donor.mkdir()
    # Staging checks the signature only; this fixture is not diffraction data.
    (donor / "staraniso_alldata-unique.mtz").write_bytes(b"MTZ offline-staging-fixture")
    (donor / "Data_1_autoPROC_STARANISO_all.cif").write_text("data_staging_fixture\n")
    (donor / "summary.html").write_text("<html>offline donor fixture</html>\n")
    (donor / "nasolve.txt").write_text("Existing donor intent must remain unchanged.\n")

    repository = tmp_path / "frozen-user-checkout"
    poison = repository / "src/nasolve/__init__.py"
    poison.parent.mkdir(parents=True)
    poison.write_text("raise RuntimeError('FROZEN CHECKOUT MUST NOT BE IMPORTED')\n")
    (repository / "keep.txt").write_text("Unrelated checkout state\n")
    configuration = tmp_path / "user-config.json"
    configuration.write_text(json.dumps({
        "schema_version": 1,
        "phenix": {"root": "not-a-native-installation"},
        "coot": {"executable": "not-a-coot-installation"},
        "workspace": {"dataset": str(donor), "run": "keep-current-choice"},
    }))
    preserved = {path: path.read_bytes() for path in
                 (*donor.iterdir(), configuration, poison, repository / "keep.txt")}
    return {
        "script": script, "metadata": metadata, "donor": donor,
        "repository": repository, "configuration": configuration,
        "output": tmp_path / "fresh-outputs", "preserved": preserved,
        "working": tmp_path / "unrelated-working-directory",
    }


def _launch(fixture, *extra):
    fixture["working"].mkdir(exist_ok=True)
    environment = dict(os.environ)
    environment.update(
        NASOLVE_CONFIG_FILE=str(fixture["configuration"]),
        PYTHONPATH=str(fixture["repository"] / "src"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    return subprocess.run([
        sys.executable, "-B", str(fixture["script"]), "--stage-only",
        "--donor", str(fixture["donor"]), "--repo", str(fixture["repository"]),
        "--output-parent", str(fixture["output"]), *extra,
    ], cwd=fixture["working"], env=environment, capture_output=True, text=True,
       timeout=30)


def _receipt(result):
    line = next(row for row in result.stdout.splitlines() if row.startswith("Receipt: "))
    path = Path(line.removeprefix("Receipt: "))
    return path, json.loads(path.read_text())


def test_relocated_shuttle_stages_with_only_bundled_sources_and_preserves_user_state(delivered):
    result = _launch(delivered)
    assert result.returncode == 0, result.stderr + result.stdout
    receipt_path, receipt = _receipt(result)
    session = receipt_path.parent
    assert receipt["status"] == "STAGED_ONLY"
    assert receipt["native_tools"] == "NOT_RUN"
    assert receipt["autosol"] == {"policy": "disabled", "experimental_phases": False}
    assert receipt["build"] == delivered["metadata"]
    assert receipt["build"]["private_diffraction_included"] is False
    assert receipt["build"]["prior_native_results_included"] is False
    assert receipt["staging"]["target_count"] == 42
    assert receipt["staging"]["validation"]["autosol"] == "DISABLED"
    assert "AutoSol: DISABLED; experimental phases: OFF" in result.stdout
    assert receipt["runtime_module_origins"] == {
        "nasolve": {"anchor": "session", "relative_path": "runtime/src/nasolve/__init__.py"},
        "restraints": {"anchor": "session", "relative_path": "runtime/restraints/__init__.py"},
    }

    for relative, expected in delivered["metadata"]["runtime_files"].items():
        data = (session / "runtime" / relative).read_bytes()
        assert (_sha(data), len(data)) == (expected["sha256"], expected["size"])
    assert "src/nasolve/cif_doctor.py" in delivered["metadata"]["runtime_files"]
    assert "restraints/data/Ligands.xlsx" in delivered["metadata"]["runtime_files"]
    saved = json.loads((session / "runtime-config.json").read_text())
    assert saved["phenix"]["root"] == "not-a-native-installation"
    assert saved["coot"]["executable"] == "not-a-coot-installation"
    assert "workspace" not in saved
    assert all(path.read_bytes() == data for path, data in delivered["preserved"].items())
    assert list(delivered["working"].iterdir()) == []
    assert not (delivered["donor"] / "AutoMR").exists()
    assert not (delivered["repository"] / "examples").exists()

    campaign = Path(receipt["campaign_root"])
    plan = json.loads((campaign / "NASolveCampaign/plan.json").read_text())
    assert plan["fingerprint"] == receipt["plan_fingerprint"]
    assert plan["counts"]["blocked"] == 0
    assert plan["preset"]["policy"]["autosol"]["policy"] == "disabled"
    assert plan["preset"]["policy"]["chemistry"]["terminal_phosphate_sites"] == []
    assert plan["datasets"][0]["status"] == "DISCOVERED"
    assert not (campaign / "dataset/AutoMR").exists()


def test_repeated_staging_keeps_separate_attempts_and_earlier_receipts(delivered):
    first = _launch(delivered)
    assert first.returncode == 0, first.stderr + first.stdout
    first_path, first_receipt = _receipt(first)
    first_bytes = first_path.read_bytes()
    second = _launch(delivered)
    assert second.returncode == 0, second.stderr + second.stdout
    second_path, second_receipt = _receipt(second)
    assert first_path.parent != second_path.parent
    assert first_receipt["campaign_root"] != second_receipt["campaign_root"]
    assert first_path.read_bytes() == first_bytes
    assert all(path.read_bytes() == data for path, data in delivered["preserved"].items())


def test_embedded_runtime_tampering_is_rejected_before_any_output_is_created(delivered):
    script = delivered["script"]
    assembled = _module(script, "assembled_synthetic_shuttle")
    changed = base64.b64decode(assembled.RUNTIME_BASE64) + b"altered-runtime"
    script.write_text(script.read_text().replace(
        repr(assembled.RUNTIME_BASE64), repr(base64.b64encode(changed).decode("ascii")), 1))
    result = _launch(delivered)
    assert result.returncode == 2
    assert "Embedded runtime archive SHA-256 differs" in result.stderr
    assert not delivered["output"].exists()
    assert all(path.read_bytes() == data for path, data in delivered["preserved"].items())


@pytest.mark.parametrize("kind", ["traversal", "symlink", "missing", "manifest-mismatch", "oversize-inventory"])
def test_runtime_structure_and_manifest_are_checked_even_with_matching_archive_hash(kind):
    template = _module(ROOT / "scripts/synthetic_dna_shuttle_template.py", "synthetic_runtime_template")
    data = b"unchanged source\n"
    name = "src/nasolve/source.py"
    entries = [(name, data)]
    if kind == "traversal":
        entries = [("../outside.py", data)]
    elif kind == "symlink":
        name = zipfile.ZipInfo(name)
        name.external_attr = (stat.S_IFLNK | 0o777) << 16
        entries = [(name, b"../../outside.py")]
    elif kind == "missing":
        entries = []
    elif kind == "manifest-mismatch":
        entries = [(name, data + b"changed")]
    elif kind == "oversize-inventory":
        entries = [(f"src/source{number}.py", b"") for number in range(513)]
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry, content in entries:
            archive.writestr(entry, content)
    payload = stream.getvalue()
    template.RUNTIME_BASE64 = base64.b64encode(payload).decode("ascii")
    template.BUNDLE = {
        "runtime_archive_sha256": _sha(payload),
        "runtime_files": {"src/nasolve/source.py": {"sha256": _sha(data), "size": len(data)}},
    }
    with pytest.raises(ValueError, match="Unsafe|inventory|manifest|bounds"):
        template._runtime_members()


def test_builder_refuses_overwriting_an_existing_delivery(tmp_path):
    builder = _module(ROOT / "scripts/build_synthetic_dna_shuttle.py", "synthetic_shuttle_builder")
    output = tmp_path / "existing.py"
    output.write_text("preserve existing delivery\n")
    with pytest.raises(FileExistsError):
        builder.build(tmp_path / "unavailable-origin", tmp_path / "unavailable-narestraints", output)
    assert output.read_text() == "preserve existing delivery\n"
