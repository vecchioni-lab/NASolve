#!/usr/bin/env python3
"""Offline runner for one hash-bound public CCD control ZIP.

This template is assembled by build_cif_doctor_ccd_shuttle.py. The generated
single-file runner contains the assessed sources; it does not install NASolve,
contact a server, modify a checkout, or perform native refinement.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib
import io
import json
from pathlib import Path
import re
import stat
import sys
import uuid
import zipfile

# Replaced by the builder. Never run the unassembled template as a shuttle.
BUNDLE = None  # @bundle-metadata@
RUNTIME_BASE64 = None  # @runtime-base64@
_MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
_MAX_MEMBER_BYTES = 8 * 1024 * 1024
_PACKAGE = "_nasolve_ccd_shuttle_runtime"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _archive_members(payload: bytes) -> dict[str, bytes]:
    """Read bounded plain files without extractall or path interpretation."""
    result = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        infos = archive.infolist()
        if len(infos) > 64 or sum(item.file_size for item in infos) > _MAX_ARCHIVE_BYTES:
            raise ValueError("ZIP exceeds the bounded control-corpus size")
        for item in infos:
            name = item.filename
            if (not name or name.startswith("/") or "\\" in name or ":" in name
                    or any(part in {"", ".", ".."} for part in name.split("/"))
                    or any(ord(character) < 32 for character in name)
                    or item.is_dir() or name in result):
                raise ValueError("ZIP contains an unsafe, duplicate or non-file member")
            kind = stat.S_IFMT(item.external_attr >> 16)
            if kind not in {0, stat.S_IFREG} or item.flag_bits & 1:
                raise ValueError("ZIP contains a special file or encrypted member")
            if item.file_size > _MAX_MEMBER_BYTES:
                raise ValueError("ZIP member exceeds the bounded size")
            result[name] = archive.read(item)
    return result


def _verified_controls(path: Path) -> tuple[bytes, dict, dict[str, bytes]]:
    if path.stat().st_size > _MAX_ARCHIVE_BYTES:
        raise ValueError("ZIP exceeds the bounded control-corpus size")
    payload = path.read_bytes()
    if _sha(payload) != BUNDLE["control_zip_sha256"]:
        raise ValueError("ZIP SHA-256 differs from this shuttle's frozen control ZIP")
    members = _archive_members(payload)
    manifest_bytes = members.get("source_manifest.json", b"")
    if _sha(manifest_bytes) != BUNDLE["manifest_sha256"]:
        raise ValueError("Source-manifest SHA-256 differs from this shuttle's frozen manifest")
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict):
        raise ValueError("Source manifest must be an object")
    components = manifest.get("components")
    if manifest.get("schema_version") != 1 or not isinstance(components, list) or not components:
        raise ValueError("Unsupported or empty source manifest")
    required = {"source_manifest.json", "source_audit_receipts.json", "README.txt"}
    codes = set()
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("Source manifest contains a non-object component")
        code = component.get("code")
        if (not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9]{1,8}", code)
                or code in codes or component.get("filename") != code + ".cif"):
            raise ValueError("Source manifest has an unsafe or duplicate component identity")
        codes.add(code)
        name = "ccd/" + component["filename"]
        required.add(name)
        data = members.get(name)
        if (data is None or type(component.get("bytes")) is not int
                or len(data) != component["bytes"] or _sha(data) != component.get("sha256")):
            raise ValueError("A declared CIF is absent or differs from its manifest hash/size")
    if set(members) != required:
        raise ValueError("ZIP member inventory differs from the declared public controls")
    if len(components) != BUNDLE["component_count"]:
        raise ValueError("Control count differs from this shuttle's build manifest")
    return payload, manifest, members


def _runtime_members() -> dict[str, bytes]:
    payload = base64.b64decode(RUNTIME_BASE64, validate=True)
    if _sha(payload) != BUNDLE["runtime_archive_sha256"]:
        raise ValueError("Embedded runtime archive failed its SHA-256 check")
    members = _archive_members(payload)
    if set(members) != set(BUNDLE["runtime_files"]):
        raise ValueError("Embedded runtime member inventory changed")
    for name, data in members.items():
        if _sha(data) != BUNDLE["runtime_files"][name]["sha256"]:
            raise ValueError("Embedded runtime source failed its SHA-256 check")
    return members


def _publish(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def run(archive: Path, output: Path | None) -> tuple[dict, Path]:
    if BUNDLE is None or RUNTIME_BASE64 is None:
        raise ValueError("This is the unassembled template; use the generated shuttle")
    # Complete input/dependency checks before creating any output folder.
    try:
        import Bio  # noqa: F401 - explicit dependency preflight
    except ImportError as error:
        raise ValueError("Biopython is required; run this with the existing NASolve virtual-environment Python") from error
    original, manifest, controls = _verified_controls(archive)
    runtime = _runtime_members()
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = archive.absolute().parent / ("cif-doctor-ccd-" + stamp + "-" + uuid.uuid4().hex[:8])
    output = output.absolute()
    # Refuses existing directories, files, dangling symlinks and reused output.
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, data in controls.items():
        _publish(output / "controls" / name, data)
    for name, data in runtime.items():
        _publish(output / "runtime" / _PACKAGE / name, data)
    runtime_parent = str(output / "runtime")
    sys.path.insert(0, runtime_parent)
    try:
        if _PACKAGE in sys.modules:
            raise ValueError("The private shuttle runtime was already imported; start a fresh process")
        assessor = importlib.import_module(_PACKAGE + ".cif_doctor").assess_dictionaries
        rows = []
        counts: dict[str, Counter] = {"source": Counter(), "effective": Counter()}
        for component in manifest["components"]:
            code = component["code"]
            relative = "controls/ccd/" + component["filename"]
            source = output / relative
            record = {"code": code, "input": {"anchor": "output", "relative_path": relative,
                      "sha256": component["sha256"], "size": component["bytes"]}}
            for stage in ("source", "effective"):
                receipt = assessor([source], stage=stage)
                if receipt["provenance"]["assessor_source_sha256"] != BUNDLE["assessor_source_sha256"]:
                    raise ValueError("Imported assessor differs from the hash-bound build")
                name = "receipts/" + code + "." + stage + ".json"
                receipt_bytes = _json_bytes(receipt)
                _publish(output / name, receipt_bytes)
                numerical = [item["verdicts"]["numerical"] for item in receipt["components"]]
                record[stage] = {"status": receipt["status"], "numerical": numerical,
                                 "receipt": {"anchor": "output", "relative_path": name,
                                             "sha256": _sha(receipt_bytes), "size": len(receipt_bytes)}}
                counts[stage][receipt["status"]] += 1
                if receipt["input_integrity"] != "UNCHANGED":
                    raise ValueError("A frozen input changed during its assessment")
            rows.append(record)
        for name, data in controls.items():
            if (output / "controls" / name).read_bytes() != data:
                raise ValueError("A preserved control input changed during the shuttle run")
        if archive.read_bytes() != original:
            raise ValueError("The downloaded ZIP changed during the shuttle run")
        report = {"schema_version": 1, "audit_kind": "offline_public_ccd_shuttle",
                  "created_utc": datetime.now(timezone.utc).isoformat(),
                  "build": BUNDLE, "input_zip": {"name": archive.name,
                  "sha256": _sha(original), "size": len(original)},
                  "input_integrity": "UNCHANGED", "component_count": len(rows),
                  "assessment_count": len(rows) * 2,
                  "status_counts": {stage: dict(sorted(value.items())) for stage, value in counts.items()},
                  "results": rows, "native_interpretation": "NOT_RUN", "coordinate_changes": False,
                  "limitations": ["PASS covers checked graph/restraint invariants; it is not chemical or scientific approval.",
                    "The same public CCD files are screened in two contexts; ReadySet was not run and no effective dictionary was generated.",
                    "Source numerical UNASSESSED and effective REVIEW are expected for graph-only CCD controls.",
                    "Phenix interpretation, linked-site chemistry, achieved geometry, diffraction refinement and assembly stitching were not run."]}
        _publish(output / "audit_summary.json", _json_bytes(report))
        text = ["NASolve CIF Doctor public CCD audit", "",
                "Code       Source       Effective    Source numerical",
                "---------- ------------ ------------ ----------------"]
        for row in rows:
            text.append(f"{row['code']:<10} {row['source']['status']:<12} {row['effective']['status']:<12} "
                        + ",".join(row["source"]["numerical"]))
        text.extend(["", *report["limitations"], "", "Inputs are preserved; each receipt is bound by SHA-256.",
                     "audit_summary.json and receipts/ contain the current audit; controls/source_audit_receipts.json is older reference evidence."])
        _publish(output / "audit_summary.txt", ("\n".join(text) + "\n").encode("utf-8"))
        return report, output
    finally:
        sys.path.remove(runtime_parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_file", type=Path, help="downloaded public CCD control ZIP (left unchanged)")
    parser.add_argument("--output", type=Path, help="new output folder; default creates a unique folder beside the ZIP")
    parser.add_argument("--json", action="store_true", help="print the compact machine-readable summary")
    args = parser.parse_args()
    try:
        report, output = run(args.zip_file, args.output)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, ImportError) as error:
        print("CIF Doctor shuttle stopped: " + str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"output": str(output), "status_counts": report["status_counts"],
                          "component_count": report["component_count"], "assessment_count": report["assessment_count"],
                          "input_integrity": report["input_integrity"], "native_interpretation": "NOT_RUN"}, sort_keys=True))
    else:
        print((output / "audit_summary.txt").read_text(encoding="utf-8"))
        print("Results: " + str(output))
    # REVIEW is an expected successful control result, not an operational failure.
    return 3 if any(row[stage]["status"] == "INVALID" for row in report["results"]
                    for stage in ("source", "effective")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
