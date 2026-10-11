#!/usr/bin/env python3
"""Diagnose failed generic ReadySet dictionaries and generate isolated candidates.

No existing run is changed, no candidate is adopted, and no MR, AutoSol or
refinement is rerun. A review ZIP contains the source and candidate evidence.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

BUNDLE = None  # @bundle-metadata@
RUNTIME_BASE64 = None  # @runtime-base64@
NATIVE_OVERRIDES = ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CCP4", "CLIBD_MON",
                    "LIBMOL_ROOT", "__PYVENV_LAUNCHER__", "PYTHONEXECUTABLE", "PYTHONUSERBASE")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _runtime_members():
    if not isinstance(BUNDLE, dict) or not isinstance(RUNTIME_BASE64, str):
        raise ValueError("Use the assembled probe")
    payload = base64.b64decode(RUNTIME_BASE64, validate=True)
    if _sha(payload) != BUNDLE["runtime_archive_sha256"]:
        raise ValueError("Embedded runtime SHA-256 changed")
    members = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        infos = archive.infolist()
        if len(infos) > 512 or sum(info.file_size for info in infos) > 32 * 1024 * 1024:
            raise ValueError("Runtime archive exceeds bounds")
        for info in infos:
            name = info.filename
            if (name.startswith("/") or "\\" in name or ":" in name
                    or any(part in {"", ".", ".."} for part in name.split("/"))
                    or info.is_dir() or name in members or info.flag_bits & 1
                    or stat.S_IFMT(info.external_attr >> 16) not in {0, stat.S_IFREG}
                    or info.file_size > 8 * 1024 * 1024):
                raise ValueError("Unsafe runtime member")
            data = archive.read(info)
            if {"sha256": _sha(data), "size": len(data)} != BUNDLE["runtime_files"].get(name):
                raise ValueError("Runtime member differs from the manifest")
            members[name] = data
    if set(members) != set(BUNDLE["runtime_files"]):
        raise ValueError("Runtime inventory changed")
    return members


def _snapshot(path, destination, expected_sha=None):
    data = path.read_bytes()
    digest = _sha(data)
    if expected_sha is not None and digest != expected_sha:
        raise ValueError("Frozen source checksum mismatch: " + str(path))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(data)
    if path.read_bytes() != data:
        raise ValueError("Input changed while snapshotting: " + str(path))
    return {"historical_source": str(path), "sha256": digest, "size": len(data)}


def _review_zip(session):
    destination = session / "cif_generation_review.zip"
    if destination.exists():
        return destination
    files = {}
    for path in sorted(session.rglob("*")):
        if not path.is_file() or path.is_relative_to(session / "runtime") or path == destination:
            continue
        if path.is_symlink():
            raise ValueError("Unexpected symlink in probe output")
        # Never serialize tool pickles into the review capsule.
        if path.suffix.lower() in {".pkl", ".pickle", ".pyc"}:
            continue
        name = path.relative_to(session).as_posix()
        data = path.read_bytes()
        files[name] = data
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", json.dumps({
            name: {"sha256": _sha(data), "bytes": len(data)} for name, data in files.items()
        }, indent=2))
    return destination


def _candidate_status(candidates):
    statuses = [candidate["status"] for candidate in candidates.values()]
    if statuses and all(status == "CANDIDATE_REVIEW" for status in statuses):
        return "CANDIDATES_AWAITING_REVIEW"
    if "CANDIDATE_REVIEW" in statuses:
        return "PARTIAL_CANDIDATES_AWAITING_REVIEW"
    if statuses and all(status == "REJECTED" for status in statuses):
        return "CANDIDATES_REJECTED"
    return "GENERATION_FAILED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path.home() / (
        "NASolve-live-tests/synthetic-dna-mechanics-om4jv7qq/"
        "synthetic-dna-combined-2n4kszi5/dataset/AutoMR/run_001"))
    parser.add_argument("--output-parent", type=Path, default=Path.home() / "NASolve-live-tests")
    parser.add_argument("--phenix-root", default=str(Path.home() / "Applications/phenix-2.2.1-6174"))
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--inspect-only", action="store_true")
    args = parser.parse_args()
    session = None
    receipt = {"schema_version": 1, "kind": "cif-generation-native-probe", "build": BUNDLE,
               "automatic_adoption": False, "native_generation": "NOT_RUN"}
    try:
        if not 1 <= args.timeout_seconds <= 3600:
            raise ValueError("Timeout must be 1–3600 seconds")
        members = _runtime_members()
        run = args.run.expanduser().resolve(strict=True)
        source_report = run / "PostMR/Restraints/cif_doctor_source.json"
        generated = run / "PostMR/ReadySet/prepared_model.ligands.cif"
        if not source_report.is_file() or not generated.is_file():
            raise ValueError("Run must contain the recorded source audit and failed ReadySet CIF")
        parent = args.output_parent.expanduser().resolve()
        if parent == run or parent.is_relative_to(run):
            raise ValueError("Probe output must be outside the preserved run")
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix="cif-generation-probe-", dir=parent))
        runtime = session / "runtime"
        for name, data in members.items():
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
        sys.path[:0] = [str(runtime / "src"), str(runtime)]
        sys.dont_write_bytecode = True
        from nasolve.cif_generation import inspect_component_generation, generate_elbow_candidate
        from nasolve.cif_doctor import assess_dictionaries
        from nasolve.curated_ligands import CURATED_LIGANDS
        from nasolve.ligand_profiles import dictionary_component_codes, _parameterized_codes
        from nasolve.run_context import resolve_artifact_path
        from nasolve.phenix_runtime import installation_from_candidate
        snapshots = {"source_audit": _snapshot(source_report, session / "inputs/source_audit.json"),
                     "failed_readyset": _snapshot(generated, session / "inputs/failed_readyset.cif")}
        source_audit = json.loads((session / "inputs/source_audit.json").read_text())
        failed = session / "inputs/failed_readyset.cif"
        assessment = assess_dictionaries([failed], stage="postmr-effective")
        _json(session / "failed_readyset_assessment.json", assessment)
        invalid = {item["component_id"] for item in assessment["components"] if item["status"] == "INVALID"}
        numerical = _parameterized_codes(failed)
        inspections, selected, frozen = {}, [], {}
        for index, record in enumerate(source_audit["inputs"]):
            path = resolve_artifact_path(record, run)
            if path is None or not path.resolve().is_relative_to(run):
                raise ValueError("Source dictionary escapes the recorded run anchor")
            destination = session / "inputs/sources" / (str(index) + "_" + path.name)
            snapshots[str(index)] = _snapshot(path, destination, record["sha256"])
            codes = dictionary_component_codes(destination)
            if len(codes) != 1:
                raise ValueError("Source snapshot must define exactly one component")
            code = next(iter(codes))
            if code in CURATED_LIGANDS:
                continue
            inspections[code] = inspect_component_generation(destination, failed, code)
            frozen[code] = destination
            if code not in _parameterized_codes(destination) and (code not in numerical or code in invalid):
                selected.append(code)
        _json(session / "component_inspections.json", inspections)
        receipt.update(snapshots=snapshots, components=sorted(inspections),
                       regeneration_queue=sorted(selected), status="INSPECTED")
        print("Invalid generic numerical components:", ", ".join(sorted(selected)) or "none", flush=True)
        candidates = {}
        if selected and not args.inspect_only:
            base_environment = {key: value for key, value in os.environ.items() if key not in NATIVE_OVERRIDES}
            phenix = installation_from_candidate(args.phenix_root, base_environment=base_environment)
            executable = phenix.executables.get("phenix.elbow")
            if not executable:
                raise ValueError("Selected Phenix installation has no phenix.elbow")
            receipt.update(native_generation="REQUESTED", phenix_version=phenix.version)
            for code in sorted(selected):
                print("Generating whole-component candidate from frozen chemistry:", code, flush=True)
                candidates[code] = generate_elbow_candidate(
                    frozen[code], code, session / "candidates", executable,
                    environment=phenix.environment, phenix_version=phenix.version,
                    timeout_seconds=args.timeout_seconds)
                print(code + ": " + str(candidates[code]["status"]), flush=True)
            receipt.update(status=_candidate_status(candidates), candidates=candidates)
        receipt["preserved_inputs"] = "UNCHANGED"
        for record in snapshots.values():
            if _sha(Path(record["historical_source"]).read_bytes()) != record["sha256"]:
                raise ValueError("Original input changed during probe")
        _json(session / "probe_receipt.json", receipt)
        review = _review_zip(session)
        print("Results:", session, flush=True)
        print("REVIEW ZIP:", review, flush=True)
        print("Original run preserved; candidates require review before adoption.", flush=True)
        return 2 if any(candidate["status"] in {"REJECTED", "FAILED"} for candidate in candidates.values()) else 0
    except (Exception, KeyboardInterrupt) as exc:
        receipt.update(status="INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "FAILED",
                       error=f"{type(exc).__name__}: {exc}")
        if session is not None:
            if not (session / "probe_receipt.json").exists():
                _json(session / "probe_receipt.json", receipt)
            print("REVIEW ZIP:", _review_zip(session), flush=True)
        print(receipt["error"], file=sys.stderr, flush=True)
        return 130 if isinstance(exc, KeyboardInterrupt) else 2


if __name__ == "__main__":
    raise SystemExit(main())
