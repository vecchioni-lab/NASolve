#!/usr/bin/env python3
"""Stage and run one isolated, fresh modified-DNA mechanics challenge.

This assembled shuttle bundles the source runtime and public MR templates;
private donor data stay on the user's computer. It never patches a checkout.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
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


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _runtime_members() -> dict[str, bytes]:
    if not isinstance(BUNDLE, dict) or not isinstance(RUNTIME_BASE64, str):
        raise ValueError("Use the assembled shuttle, not its source template")
    payload = base64.b64decode(RUNTIME_BASE64, validate=True)
    if _sha(payload) != BUNDLE["runtime_archive_sha256"]:
        raise ValueError("Embedded runtime archive SHA-256 differs")
    result = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as handle:
        infos = handle.infolist()
        if len(infos) > 512 or sum(item.file_size for item in infos) > 32 * 1024 * 1024:
            raise ValueError("Runtime archive exceeds bounds")
        for item in infos:
            name = item.filename
            if (name.startswith("/") or "\\" in name or ":" in name
                    or any(part in {"", ".", ".."} for part in name.split("/"))
                    or item.is_dir() or name in result or item.flag_bits & 1
                    or stat.S_IFMT(item.external_attr >> 16) not in {0, stat.S_IFREG}
                    or item.file_size > 8 * 1024 * 1024):
                raise ValueError("Unsafe or duplicate runtime member")
            data = handle.read(item)
            expected = BUNDLE["runtime_files"].get(name)
            if expected is None or len(data) != expected["size"] or _sha(data) != expected["sha256"]:
                raise ValueError("Runtime member differs from its frozen manifest")
            result[name] = data
    if set(result) != set(BUNDLE["runtime_files"]):
        raise ValueError("Runtime inventory differs from its frozen manifest")
    return result


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(data)


def _configuration_source() -> Path:
    if os.environ.get("NASOLVE_CONFIG_FILE"):
        return Path(os.environ["NASOLVE_CONFIG_FILE"]).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/NASolve/config.json"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "nasolve/config.json"


def _isolate(runtime: Path, session: Path, members: dict[str, bytes]) -> None:
    if any(name == "nasolve" or name.startswith("nasolve.") or name == "restraints"
           or name.startswith("restraints.") for name in sys.modules):
        raise ValueError("Start this shuttle in a fresh Python process")
    config_source = _configuration_source()
    configuration = {"schema_version": 1}
    if config_source.is_file():
        original = json.loads(config_source.read_text())
        if not isinstance(original, dict):
            raise ValueError("Saved NASolve configuration is not an object")
        configuration.update({key: original[key] for key in ("phenix", "coot") if key in original})
    _write(session / "runtime-config.json", configuration)
    for name, data in members.items():
        _write(runtime / name, data)
    paths = [str(runtime / "src"), str(runtime)]
    sys.path[:0] = paths
    os.environ["PYTHONPATH"] = os.pathsep.join(paths)
    os.environ["NASOLVE_CONFIG_FILE"] = str(session / "runtime-config.json")
    os.environ["NASOLVE_NATIVE_ENV_ISOLATION"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True


def _outcome(result: dict, root: Path) -> dict:
    execution = result.get("execution", {})
    rows = []
    for item in execution.get("datasets", []):
        row = {key: item.get(key) for key in
               ("id", "status", "diagnostic", "run", "checkpoint", "numerical_success", "inspection_required")}
        row["input_space_group"] = None
        row["model_space_group"] = None
        if item.get("run"):
            run = root / item["run"]
            if (run / "report.json").is_file():
                report = json.loads((run / "report.json").read_text())
                row["input_space_group"] = (report.get("symmetry") or {}).get("evidence", {}).get("mtz_symbol")
                row["cif_doctor"] = report.get("postmr", {}).get("cif_doctor")
            if item.get("checkpoint"):
                from nasolve.checkpoints import read_registry, resolve_checkpoint, checkpoint_record
                try:
                    _, registry = read_registry(run)
                    checkpoint = resolve_checkpoint(registry, item["checkpoint"])
                    model = checkpoint_record(checkpoint, run).model
                    if model:
                        for line in model.read_text(errors="replace").splitlines():
                            if line.startswith("CRYST1"):
                                row["model_space_group"] = line[55:66].strip()
                                break
                except Exception as exc:
                    row["model_space_group_note"] = str(exc)
        rows.append(row)
    return {"state": execution.get("state", "PLANNED"), "datasets": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.home() / "Documents/Amsterdam/_Wind/GitHub/NASolve-cedar",
                        help="donor checkout anchor only; its source is never imported or edited")
    parser.add_argument("--donor", type=Path, help="explicit donor dataset; default: REPO/examples/TestSets/GZ11")
    parser.add_argument("--mtz", default="staraniso_alldata-unique.mtz", help="exact donor-relative MTZ path")
    parser.add_argument("--cif", default="Data_1_autoPROC_STARANISO_all.cif", help="exact donor-relative processing CIF path")
    parser.add_argument("--summary", default="summary.html", help="exact donor-relative processing summary path")
    parser.add_argument("--output-parent", type=Path, default=Path.home() / "NASolve-live-tests")
    parser.add_argument("--phenix-root", default=str(Path.home() / "Applications/phenix-2.2.1-6174"))
    parser.add_argument("--coot", help="explicit Coot executable, if discovery needs an override")
    parser.add_argument("--stage-only", action="store_true", help="prepare and freeze inputs without native tools")
    parser.add_argument("--through", choices=("preflight", "phaser", "postmr", "autorefine", "refine-doctor"), default="refine-doctor")
    args = parser.parse_args()
    session = None
    receipt = {"schema_version": 1, "kind": "synthetic-dna-mechanics-launch",
               "created_utc": datetime.now(timezone.utc).isoformat(), "build": BUNDLE,
               "autosol": {"policy": "disabled", "experimental_phases": False},
               "scientific_scope": "hypothetical modified DNA on real donor diffraction; mechanics only",
               "native_tools": "NOT_RUN"}
    try:
        members = _runtime_members()
        for dependency in ("Bio", "numpy", "openpyxl"):
            __import__(dependency)
        if sys.version_info < (3, 10):
            raise ValueError("Python >=3.10 is required")
        parent = args.output_parent.expanduser().resolve()
        repository = args.repo.expanduser().resolve()
        donor = args.donor.expanduser().resolve() if args.donor else repository / "examples/TestSets/GZ11"
        if parent == repository or repository in parent.parents or parent == donor or donor in parent.parents:
            raise ValueError("Outputs must be outside the donor and its checkout")
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix="synthetic-dna-mechanics-", dir=parent))
        runtime = session / "runtime"
        _isolate(runtime, session, members)
        if args.coot:
            os.environ["NASOLVE_COOT"] = args.coot
        from nasolve.synthetic_dna import stage_synthetic_dna
        from nasolve.campaigns import plan_campaign
        from nasolve.campaign_execution import execute_campaign
        import nasolve
        import restraints
        origins = {"nasolve": Path(nasolve.__file__).resolve(), "restraints": Path(restraints.__file__).resolve()}
        if any(not path.is_relative_to(runtime) for path in origins.values()):
            raise ValueError("NASolve/NARestraints imports did not resolve the bundled runtime")
        receipt["runtime_module_origins"] = {name: {"anchor": "session", "relative_path": path.relative_to(session).as_posix()}
                                             for name, path in origins.items()}
        staged = stage_synthetic_dna(runtime, donor, session,
                                    mtz_relative_path=args.mtz, cif_relative_path=args.cif,
                                    summary_relative_path=args.summary)
        root = Path(staged["root"])
        recipe = Path(staged["recipe"])
        dataset = Path(staged["dataset"])
        plan = plan_campaign(root, preset=recipe, datasets=(dataset.name,),
                             frames_directory=runtime / "MR_frames")
        receipt.update(campaign_root=str(root), campaign={"anchor": "session", "relative_path": root.relative_to(session).as_posix()}, staging=staged,
                       plan_fingerprint=plan["fingerprint"], status="STAGED_ONLY")
        print("Synthetic DNA: K:X / B:S / Z:P / D:T; 42 targets", flush=True)
        print("Termini: free 5′ OH; AutoSol: DISABLED; experimental phases: OFF", flush=True)
        print("Campaign:", root, flush=True)
        if plan["counts"]["blocked"]:
            receipt.update(status="BLOCKED", outcome={"datasets": plan["datasets"]})
        elif not args.stage_only:
            receipt["native_tools"] = "REQUESTED"
            result = execute_campaign(root, through=args.through, phenix_root=args.phenix_root,
                                      progress=lambda message: print(message, flush=True))
            outcome = _outcome(result, root)
            receipt.update(status=outcome["state"], outcome=outcome)
        else:
            receipt["outcome"] = {"state": "STAGED_ONLY", "datasets": plan["datasets"]}
        _write(session / "shuttle_receipt.json", receipt)
        for row in receipt["outcome"].get("datasets", []):
            print(f"{row.get('id')}: {row.get('status')} | space group: "
                  f"{row.get('model_space_group') or row.get('input_space_group') or 'not yet determined'}", flush=True)
            print(row.get("diagnostic", ""), flush=True)
        print("Receipt:", session / "shuttle_receipt.json", flush=True)
        print("Mechanics test only; inspect model/maps before scientific use.", flush=True)
        blocked = any(row.get("status") in {"BLOCKED", "FAILED", "INTEGRITY_FAILED"}
                      for row in receipt["outcome"].get("datasets", []))
        return 2 if blocked else 0
    except (Exception, KeyboardInterrupt) as exc:
        receipt.update(status="INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "BLOCKED",
                       error=f"{type(exc).__name__}: {exc}")
        if session is not None and not (session / "shuttle_receipt.json").exists():
            _write(session / "shuttle_receipt.json", receipt)
        print(receipt["error"], file=sys.stderr, flush=True)
        if session:
            print("Retained results:", session, file=sys.stderr, flush=True)
        return 130 if isinstance(exc, KeyboardInterrupt) else 2


if __name__ == "__main__":
    raise SystemExit(main())
