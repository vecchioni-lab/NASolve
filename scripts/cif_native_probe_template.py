#!/usr/bin/env python3
"""Inventory a reviewed numerical candidate in an isolated native model bundle.

The preserved run supplies its hash-bound prepared model and complete runtime
restraint stack. This diagnostic changes no model, checkpoint or campaign, runs
no ReadySet, optimization or refinement, and adopts no dictionary.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
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


def _digest_record(record):
    if (not isinstance(record, dict) or not isinstance(record.get("sha256"), str)
            or len(record["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in record["sha256"].lower())
            or isinstance(record.get("size"), bool)
            or not isinstance(record.get("size"), int) or record["size"] < 0):
        raise ValueError("Artifact reference requires a SHA-256 and byte size")


def _snapshot(path, destination, session, expected=None):
    data = path.read_bytes()
    digest = _sha(data)
    if expected is not None:
        _digest_record(expected)
        if digest != expected["sha256"].lower() or len(data) != expected["size"]:
            raise ValueError("Frozen input checksum or byte size mismatch: " + str(path))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(data)
    if path.read_bytes() != data:
        raise ValueError("Input changed while snapshotting: " + str(path))
    return {"anchor": "probe_directory", "path": destination.relative_to(session).as_posix(),
            "historical_source": str(path), "sha256": digest, "size": len(data)}


def _run_reference(record, run):
    from nasolve.run_context import resolve_artifact_path
    _digest_record(record)
    if record.get("anchor") != "run":
        raise ValueError("Native input must use its recorded run anchor")
    path = resolve_artifact_path(record, run)
    if path is None or not path.resolve().is_relative_to(run):
        raise ValueError("Recorded run input is missing, changed or escapes its anchor")
    if path.stat().st_size != record["size"]:
        raise ValueError("Recorded run input byte size differs")
    return path


def _candidate_reference(record, candidate_directory, *, exact=None):
    _digest_record(record)
    value = record.get("path")
    if (record.get("anchor") != "candidate_directory" or not isinstance(value, str)
            or value.startswith("/") or "\\" in value or ":" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
            or (exact is not None and value != exact)):
        raise ValueError("Candidate artifact must use its exact safe directory reference")
    path = candidate_directory.joinpath(*PurePosixPath(value).parts).resolve()
    if not path.is_relative_to(candidate_directory) or not path.is_file():
        raise ValueError("Candidate artifact missing or escapes its directory")
    if _sha(path.read_bytes()) != record["sha256"].lower() or path.stat().st_size != record["size"]:
        raise ValueError("Candidate artifact checksum or byte size mismatch: " + value)
    return path


def _capture_candidate(directory, session, snapshots):
    receipt_path = directory / "generation_receipt.json"
    snapshots["generation_receipt"] = _snapshot(
        receipt_path, session / "inputs/candidate/generation_receipt.json", session)
    receipt = json.loads((session / snapshots["generation_receipt"]["path"]).read_text())
    if (receipt.get("schema_version") != 1
            or receipt.get("audit_kind") != "cif_numerical_generation_candidate"
            or receipt.get("policy_id") not in {"cif-independent-elbow-candidate-v3",
                                                "cif-independent-elbow-candidate-v4"}
            or receipt.get("status") != "CANDIDATE_REVIEW"
            or receipt.get("automatic_adoption") is not False
            or receipt.get("source_preserved") is not True
            or receipt.get("frozen_source_preserved") is not True
            or receipt.get("execution", {}).get("status") != "COMPLETED"
            or receipt.get("execution", {}).get("returncode") != 0
            or receipt.get("generator_capabilities", {}).get("status") != "SUPPORTED"
            or receipt.get("source_state_preservation", {}).get("generator_option") != "--pH"
            or receipt.get("source_state_preservation", {}).get("generator_value") != "low"):
        raise ValueError("Require a completed source-preserving v3/v4 CANDIDATE_REVIEW receipt")
    code = receipt.get("component_id")
    if not isinstance(code, str) or not code or code in {".", "?"}:
        raise ValueError("Candidate receipt must declare an exact component identity")
    output_records = {}
    for record in receipt.get("outputs", []):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ValueError("Invalid candidate output reference")
        if record["path"] in output_records:
            raise ValueError("Duplicate candidate output reference")
        output_records[record["path"]] = record
    required = {"source.cif": receipt.get("source"),
                "candidate.cif": output_records.get("candidate.cif"),
                "elbow.log": output_records.get("elbow.log"),
                "elbow_help.log": receipt.get("generator_capabilities", {}).get("help_output"),
                "source_ideal.pdb": receipt.get("seed", {}).get("artifact")}
    for name, record in required.items():
        path = _candidate_reference(record, directory, exact=name)
        if name in output_records and output_records[name] != record:
            raise ValueError("Candidate receipt has inconsistent artifact identities")
        snapshots["candidate/" + name] = _snapshot(
            path, session / "inputs/candidate" / name, session, record)
    return receipt, code, session / "inputs/candidate/source.cif", session / "inputs/candidate/candidate.cif"


def _review_zip(session):
    run_token = session.name.rsplit("-", 1)[-1]
    destination = session / (BUNDLE["delivery_prefix"] + "_" + run_token + "_cif_native_review.zip")
    if destination.exists():
        return destination
    files = {}
    for path in sorted(session.rglob("*")):
        if not path.is_file() or path.is_relative_to(session / "runtime") or path == destination:
            continue
        if path.is_symlink():
            raise ValueError("Unexpected symlink in probe output")
        if path.suffix.lower() in {".pkl", ".pickle", ".pyc"}:
            continue
        files[path.relative_to(session).as_posix()] = path.read_bytes()
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", json.dumps({
            name: {"sha256": _sha(data), "bytes": len(data)} for name, data in files.items()
        }, indent=2))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path.home() / (
        "NASolve-live-tests/synthetic-dna-mechanics-om4jv7qq/"
        "synthetic-dna-combined-2n4kszi5/dataset/AutoMR/run_001"))
    parser.add_argument("--candidate-directory", type=Path, default=Path.home() / (
        "NASolve-live-tests/04_Cedar_cif-generation-probe-r2cunjcc/"
        "candidates/cif-generation-xpj7v6bw"))
    parser.add_argument("--generation-probe", type=Path, default=Path.home() / (
        "NASolve-live-tests/04_Cedar_cif-generation-probe-r2cunjcc/probe_receipt.json"))
    parser.add_argument("--output-parent", type=Path, default=Path.home() / "NASolve-live-tests")
    parser.add_argument("--phenix-root", default=str(Path.home() / "Applications/phenix-2.2.1-6174"))
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--inspect-only", action="store_true")
    args = parser.parse_args()
    session = None
    snapshots = {}
    receipt = {"schema_version": 1, "kind": "cif-native-bundle-probe", "build": BUNDLE,
               "delivery_prefix": BUNDLE["delivery_prefix"], "automatic_adoption": False,
               "native_validation": "NOT_RUN", "linked_site_qualification": "NOT_RUN",
               "optimization": "NOT_RUN", "readyset_retry": "NOT_RUN", "refinement": "NOT_RUN"}
    try:
        if not 1 <= args.timeout_seconds <= 3600:
            raise ValueError("Timeout must be 1–3600 seconds")
        members = _runtime_members()
        run = args.run.expanduser().resolve(strict=True)
        candidate_directory = args.candidate_directory.expanduser().resolve(strict=True)
        generation_probe_path = args.generation_probe.expanduser().resolve(strict=True)
        parent = args.output_parent.expanduser().resolve()
        if (parent == run or parent.is_relative_to(run) or parent == candidate_directory
                or parent.is_relative_to(candidate_directory)
                or parent == generation_probe_path.parent
                or parent.is_relative_to(generation_probe_path.parent)):
            raise ValueError("Probe output must be outside the preserved run, candidate and generation-probe directories")
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE["delivery_prefix"] + "_cif-native-probe-", dir=parent))
        runtime = session / "runtime"
        for name, data in members.items():
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
        sys.path[:0] = [str(runtime / "src"), str(runtime)]
        sys.dont_write_bytecode = True
        from nasolve.cif_native_validation import inspect_native_bundle, NATIVE_POLICY_ID
        from nasolve.cif_generation import inspect_component_generation
        from nasolve.cif_doctor import assess_dictionaries
        from nasolve.ligand_profiles import dictionary_component_codes, effective_restraints
        from nasolve.phenix_runtime import installation_from_candidate
        print("CIF native diagnostic:", BUNDLE["delivery_prefix"], "|", NATIVE_POLICY_ID, flush=True)

        snapshots["generation_probe"] = _snapshot(
            generation_probe_path, session / "inputs/generation_probe.json", session)
        generation_probe = json.loads((session / "inputs/generation_probe.json").read_text())
        if (generation_probe.get("schema_version") != 1
                or generation_probe.get("kind") != "cif-generation-native-probe"
                or generation_probe.get("status") != "CANDIDATES_AWAITING_REVIEW"
                or generation_probe.get("native_generation") != "REQUESTED"
                or generation_probe.get("automatic_adoption") is not False):
            raise ValueError("Require the completed generation-probe receipt awaiting candidate review")
        source_report = run / "PostMR/Restraints/cif_doctor_source.json"
        generated = run / "PostMR/ReadySet/prepared_model.ligands.cif"
        baseline = generation_probe.get("snapshots", {})
        if not isinstance(baseline, dict):
            raise ValueError("Generation-probe receipt is missing baseline snapshot identities")
        _digest_record(baseline.get("source_audit"))
        _digest_record(baseline.get("failed_readyset"))
        snapshots["source_audit"] = _snapshot(
            source_report, session / "inputs/source_audit.json", session, baseline.get("source_audit"))
        snapshots["raw_readyset"] = _snapshot(
            generated, session / "inputs/raw_readyset.cif", session, baseline.get("failed_readyset"))
        source_audit = json.loads((session / "inputs/source_audit.json").read_text())
        if (source_audit.get("schema_version") != 1
                or source_audit.get("audit_kind") != "cif_restraint_assessment"
                or source_audit.get("stage") != "postmr-source"):
            raise ValueError("Require the recorded schema-1 PostMR source assessment")
        generation, code, frozen_source, candidate = _capture_candidate(candidate_directory, session, snapshots)
        if generation_probe.get("candidates", {}).get(code) != generation:
            raise ValueError("Candidate generation receipt differs from its selected generation-probe evidence")
        inspection = inspect_component_generation(frozen_source, candidate, code)
        _json(session / "candidate_inspection.json", inspection)
        if inspection["status"] != "CANDIDATE_REVIEW":
            raise ValueError("Current source/candidate assessment rejected the numerical candidate")
        if dictionary_component_codes(frozen_source) != {code} or dictionary_component_codes(candidate) != {code}:
            raise ValueError("Candidate and source must each define exactly the declared component")

        source_matches = []
        for index, record in enumerate(source_audit.get("inputs", [])):
            path = _run_reference(record, run)
            copied = session / "inputs/sources" / (str(index) + "_" + path.name)
            snapshots["source/" + str(index)] = _snapshot(path, copied, session, record)
            if code in dictionary_component_codes(copied):
                source_matches.append((copied, record))
        if (len(source_matches) != 1 or dictionary_component_codes(source_matches[0][0]) != {code}
                or source_matches[0][1]["sha256"].lower() != generation["source"]["sha256"].lower()
                or source_matches[0][0].read_bytes() != frozen_source.read_bytes()):
            raise ValueError("Candidate chemistry is not bound to exactly one frozen source-audit component")

        model_record = source_audit.get("model")
        model_source = _run_reference(model_record, run)
        model = session / "inputs/prepared_model.pdb"
        snapshots["model"] = _snapshot(model_source, model, session, model_record)
        runtime_assessment = source_audit.get("runtime_assessment")
        if (not isinstance(runtime_assessment, dict) or not runtime_assessment.get("inputs")
                or runtime_assessment.get("schema_version") != 1
                or runtime_assessment.get("audit_kind") != "cif_restraint_assessment"
                or runtime_assessment.get("stage") != "postmr-runtime-source"):
            raise ValueError("Source audit is missing the recorded complete runtime restraint stack")
        if runtime_assessment.get("model") is not None:
            runtime_model = _run_reference(runtime_assessment["model"], run)
            if runtime_model != model_source or runtime_assessment["model"]["sha256"] != model_record["sha256"]:
                raise ValueError("Source and runtime model references disagree")
        paths, replacement_origins = [], []
        for index, record in enumerate(runtime_assessment["inputs"]):
            path = _run_reference(record, run)
            copied = session / "inputs/runtime_sources" / (str(index) + "_" + path.name)
            snapshots["runtime/" + str(index)] = _snapshot(path, copied, session, record)
            if copied.suffix.lower() not in {".cif", ".phil", ".eff"}:
                raise ValueError("Unsupported recorded native restraint input: " + path.name)
            if copied.suffix.lower() == ".cif" and code in dictionary_component_codes(copied):
                if dictionary_component_codes(copied) != {code}:
                    raise ValueError("Candidate replacement requires a single-component runtime source")
                replacement_origins.append(snapshots["runtime/" + str(index)])
            else:
                paths.append(copied)
        if len(replacement_origins) != 1:
            raise ValueError("Candidate must replace exactly one recorded runtime component definition")
        paths.append(candidate)
        selection_dir = session / "selected_bundle"
        selection_dir.mkdir()
        adaptations = []
        selected, dictionaries = effective_restraints(
            paths, session / "inputs/raw_readyset.cif", selection_dir,
            normalize_effective=True, prefer_parameterized_inputs=True, audit=adaptations)
        cifs = [path for path in selected if path.suffix.lower() == ".cif"]
        parameters = [path for path in selected if path.suffix.lower() in {".phil", ".eff"}]
        _json(session / "selected_bundle_assessment.json", assess_dictionaries(
            cifs, stage="postmr-effective", model=model))
        bundle = {"schema_version": 1, "policy": "parameterized-inputs-over-readyset-v2",
                  "candidate_component": code, "replaced_runtime_sources": replacement_origins,
                  "selected_inputs": [{"anchor": "probe_directory", "path": path.relative_to(session).as_posix(),
                                       "sha256": _sha(path.read_bytes()), "size": path.stat().st_size}
                                      for path in selected],
                  "dictionary_components": {path.relative_to(session).as_posix(): sorted(dictionary_component_codes(path))
                                            for path in dictionaries},
                  "torsion_adaptations": adaptations,
                  "new_generic_modifications": False, "chemical_qualification": "NOT_RUN"}
        _json(session / "selected_bundle.json", bundle)
        receipt.update(status="INSPECTED", component_id=code, candidate_inspection=inspection,
                       selected_bundle=bundle, snapshots=snapshots, native_policy=NATIVE_POLICY_ID,
                       generation_probe_baseline="CHECKSUM_BOUND")
        if not args.inspect_only:
            environment = {key: value for key, value in os.environ.items() if key not in NATIVE_OVERRIDES}
            phenix = installation_from_candidate(args.phenix_root, base_environment=environment)
            executable = phenix.executables.get("phenix.python")
            if not executable:
                raise ValueError("Selected Phenix installation has no installation-bound phenix.python")
            print("Reading selected dictionaries and prepared model with Phenix; diagnostic only.", flush=True)
            native = inspect_native_bundle(
                model, cifs, session / "native", executable, phil_files=parameters,
                phil_namespace_policy="refinement-root-to-interpreter-v1",
                environment=phenix.environment, phenix_version=phenix.version,
                timeout_seconds=args.timeout_seconds)
            receipt.update(status=native["status"], native_validation=native, phenix_version=phenix.version)
            print("Native inventory:", native["status"], flush=True)
        for record in snapshots.values():
            if _sha(Path(record["historical_source"]).read_bytes()) != record["sha256"]:
                raise ValueError("Original input changed during probe")
        receipt["preserved_inputs"] = "UNCHANGED"
        _json(session / "probe_receipt.json", receipt)
        print("Results:", session, flush=True)
        print("REVIEW ZIP:", _review_zip(session), flush=True)
        print("Original run and candidate preserved; native inventory is diagnostic evidence, not adoption.", flush=True)
        return 0 if receipt["status"] in {"INSPECTED", "REVIEW"} else 2
    except (Exception, KeyboardInterrupt) as exc:
        receipt.update(status="INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "FAILED",
                       error=f"{type(exc).__name__}: {exc}", snapshots=snapshots)
        if session is not None:
            if not (session / "probe_receipt.json").exists():
                _json(session / "probe_receipt.json", receipt)
            print("REVIEW ZIP:", _review_zip(session), flush=True)
        print(receipt["error"], file=sys.stderr, flush=True)
        return 130 if isinstance(exc, KeyboardInterrupt) else 2


if __name__ == "__main__":
    raise SystemExit(main())
