#!/usr/bin/env python3
"""Live validation harness for the forced 5W6W_noPO4 search model.

This script deliberately exercises a fresh numbered AutoMR -> Phaser -> PostMR
path against a real local dataset while forcing the committed
MR_frames/5W6W/5W6W_noPO4.pdb fixture. It never edits the dataset's input
configuration or any existing run. The goal is to validate that recipe-declared
D:1 5'-phosphate chemistry can be constructed from a model with no phosphate
atoms, survive ReadySet, and remain interpretable by Phenix.

Usage examples:

    python scripts/live_validate_no_po4.py /path/to/dataset
    python scripts/live_validate_no_po4.py /path/to/dataset --pair F:D
    python scripts/live_validate_no_po4.py --pair F:D

When DATASET is omitted, the active NASolve workspace dataset is used.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nasolve.automr import prepare_automr
from nasolve.automr_input import AutoMRInputError, read_intent, resolve_automr_input
from nasolve.config import ConfigError, load_config
from nasolve.coot_runtime import CootDiscoveryError, discover_coot
from nasolve.phaser import PhaserExecutionError, execute_phaser
from nasolve.phenix_runtime import PhenixDiscoveryError, discover_phenix
from nasolve.postmr import PostMRPreparationError, prepare_postmr
from nasolve.presets import PresetError, load_preset


PHOSPHATE_NAMES = {"P", "OP1", "OP2", "OP3", "O1P", "O2P", "O3P"}
REQUIRED_TERMINAL = {"P", "OP1", "OP2", "OP3"}


class LiveValidationError(RuntimeError):
    pass


def canonical_atom_name(name: str) -> str:
    return {"O1P": "OP1", "O2P": "OP2", "O3P": "OP3"}.get(name, name)


def site_atom_names(path: Path, chain: str = "D", resid: str = "1") -> set[str]:
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 27:
            continue
        line_chain = line[21:22].strip() or "_"
        line_resid = line[22:26].strip() + line[26:27].strip()
        if line_chain == chain and line_resid == resid:
            names.add(canonical_atom_name(line[12:16].strip().upper().replace("*", "'")))
    return names


def find_construction_record(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("mode") == "ensure-complete-5prime-phosphate-v1":
            return value
        for child in value.values():
            found = find_construction_record(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_construction_record(child)
            if found is not None:
                return found
    return None


def phenix_pdb_interpretation(phenix) -> Path:
    candidates: list[Path] = []
    phaser = phenix.executables.get("phenix.phaser")
    if phaser is not None:
        candidates.append(phaser.parent / "phenix.pdb_interpretation")
    if phenix.root is not None:
        candidates.extend([
            phenix.root / "bin" / "phenix.pdb_interpretation",
            phenix.root / "build" / "bin" / "phenix.pdb_interpretation",
        ])
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise LiveValidationError(
        "Could not find phenix.pdb_interpretation beside the discovered Phenix installation"
    )


def run_interpretation(run: Path, model: Path, restraints: tuple[Path, ...], phenix) -> Path:
    validation = run / "PostMR" / "Validation"
    validation.mkdir(exist_ok=True)
    log = validation / "pdb_interpretation.log"
    executable = phenix_pdb_interpretation(phenix)
    inputs = [path for path in restraints if path.suffix.lower() in {".cif", ".phil", ".eff"}]
    command = [str(executable), str(model), *(str(path) for path in inputs)]
    completed = subprocess.run(
        command,
        cwd=validation,
        env=dict(phenix.environment),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise LiveValidationError(
            f"phenix.pdb_interpretation exited with status {completed.returncode}; inspect {log}"
        )
    return log


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description=(
            "Force 5W6W_noPO4.pdb through a fresh W-frame AutoMR/Phaser/PostMR run "
            "and verify recipe-driven D:1 phosphate construction."
        )
    )
    value.add_argument("dataset", nargs="?", type=Path, help="dataset directory; defaults to active workspace dataset")
    value.add_argument("--pair", help="ordered W-frame pair override; otherwise use dataset nasolve.txt")
    value.add_argument("--phenix-root", help="one-run Phenix override")
    value.add_argument("--coot", help="one-run Coot executable override")
    value.add_argument(
        "--allow-mr-review",
        action="store_true",
        help="continue PostMR when forced-model Phaser returns MR_REVIEW instead of MR_SUCCESS",
    )
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        config = load_config()
        if args.dataset is not None:
            dataset = args.dataset.expanduser().resolve()
        elif config.workspace.dataset:
            dataset = Path(config.workspace.dataset).expanduser().resolve()
        else:
            raise LiveValidationError(
                "No dataset supplied and no active workspace dataset is configured"
            )
        if not dataset.is_dir():
            raise LiveValidationError(f"Dataset does not exist: {dataset}")

        fixture = ROOT / "MR_frames" / "5W6W" / "5W6W_noPO4.pdb"
        if not fixture.is_file():
            raise LiveValidationError(f"Validation fixture is missing: {fixture}")
        fixture_atoms = site_atom_names(fixture)
        if fixture_atoms & PHOSPHATE_NAMES:
            raise LiveValidationError(
                "Validation fixture is no longer phosphate-free at D:1: "
                + ", ".join(sorted(fixture_atoms & PHOSPHATE_NAMES))
            )
        if not {"O5'", "C5'"} <= fixture_atoms:
            raise LiveValidationError("Validation fixture D:1 lacks O5'/C5' construction anchors")

        config_path = dataset / "nasolve.txt"
        intent = read_intent(config_path if config_path.is_file() else None)
        pair = args.pair or intent.pair
        if not pair:
            raise LiveValidationError(
                "No W-frame pair is available. Add pair= to dataset nasolve.txt or pass --pair FIRST:SECOND."
            )

        recipe = load_preset("5w6w")
        resolved = resolve_automr_input(
            dataset,
            intent,
            frame_override="W",
            pair_override=pair,
            frames_dir=ROOT / "MR_frames",
            recipe=recipe,
        )
        if tuple(resolved.allow_op3_sites) != ("D:1",):
            raise LiveValidationError(
                "The effective W recipe did not resolve exactly D:1 as its terminal phosphate site: "
                + repr(resolved.allow_op3_sites)
            )
        forced = replace(
            resolved,
            model=fixture.resolve(),
            model_source="forced live-validation fixture: MR_frames/5W6W/5W6W_noPO4.pdb",
            model_pair=None,
            exact_pair_model=False,
            catalogue_warnings=tuple(resolved.catalogue_warnings) + (
                "Forced phosphate-free 5W6W validation model; never use this selection implicitly.",
            ),
        )

        phenix = discover_phenix(config, explicit=args.phenix_root)
        mtz_dump = phenix.executables.get("phenix.mtz.dump")
        if mtz_dump is None:
            raise LiveValidationError("The discovered Phenix installation has no phenix.mtz.dump")
        coot = discover_coot(config, explicit=args.coot)

        print("NASolve live 5'-phosphate validation")
        print(f"Dataset: {dataset}")
        print(f"Pair: {pair}")
        print(f"Forced model: {fixture}")
        print(f"Phenix: {phenix.version}")
        print(f"Coot: {coot.version}")
        print("Fixture D:1 phosphate atoms: none")

        preflight = prepare_automr(
            dataset,
            resolved_input=forced,
            mtz_dump_executable=mtz_dump,
            phenix_environment=phenix.environment,
        )
        print(f"Fresh run: {preflight.run_directory}")
        copied_atoms = site_atom_names(preflight.run_directory / "Model" / "input_model.pdb")
        if copied_atoms & PHOSPHATE_NAMES:
            raise LiveValidationError("AutoMR unexpectedly introduced D:1 phosphate atoms before Phaser")

        phaser = execute_phaser(
            preflight.report_path,
            phenix.executables["phenix.phaser"],
            environment=phenix.environment,
            phenix_version=phenix.version,
        )
        print(f"Phaser: {phaser.status}; TFZ={phaser.tfz}; LLG={phaser.llg}")
        if phaser.status == "MR_FAILED":
            raise LiveValidationError(f"Forced-model Phaser failed; preserve and inspect {phaser.log_path}")
        if phaser.status == "MR_REVIEW" and not args.allow_mr_review:
            raise LiveValidationError(
                "Forced-model Phaser returned MR_REVIEW. Inspect it first, then rerun only with --allow-mr-review if scientifically acceptable."
            )
        if phaser.solution_pdb is None:
            raise LiveValidationError("Phaser produced no solution PDB")
        mr_atoms = site_atom_names(phaser.solution_pdb)
        if mr_atoms & PHOSPHATE_NAMES:
            raise LiveValidationError("Phaser unexpectedly introduced D:1 phosphate atoms")

        postmr = prepare_postmr(
            phaser.run_directory,
            phenix.executables["phenix.ready_set"],
            coot_executable=coot.executable,
            environment=phenix.environment,
            allow_mr_review=args.allow_mr_review,
        )
        final_atoms = site_atom_names(postmr.model_path)
        missing = REQUIRED_TERMINAL - final_atoms
        if missing:
            raise LiveValidationError(
                "PostMR/ReadySet final model lacks D:1 terminal phosphate atom(s): "
                + ", ".join(sorted(missing))
            )

        postmr_payload = json.loads(postmr.report_path.read_text(encoding="utf-8"))
        construction = find_construction_record(postmr_payload)
        if construction is None:
            raise LiveValidationError("PostMR report contains no terminal-phosphate construction provenance")
        built_sites = {
            row.get("site")
            for row in construction.get("constructed", [])
            if isinstance(row, dict)
        }
        if "D:1" not in built_sites:
            raise LiveValidationError(
                "PostMR did not record D:1 as a newly constructed whole phosphate: "
                + json.dumps(construction, sort_keys=True)
            )

        interpretation_log = run_interpretation(
            phaser.run_directory,
            postmr.model_path,
            postmr.restraint_paths,
            phenix,
        )

        print("PASS: D:1 whole 5'-phosphate was constructed from a phosphate-free MR model.")
        print("PASS: P/OP1/OP2/OP3 survived ReadySet and NASolve phosphate validation.")
        print("PASS: phenix.pdb_interpretation accepted the prepared model/restraint bundle.")
        print(f"Final model: {postmr.model_path}")
        print(f"PostMR report: {postmr.report_path}")
        print(f"Interpretation log: {interpretation_log}")
        print("No refinement was run by this validation harness.")
        return 0

    except (
        AutoMRInputError,
        ConfigError,
        CootDiscoveryError,
        LiveValidationError,
        PhaserExecutionError,
        PhenixDiscoveryError,
        PostMRPreparationError,
        PresetError,
        OSError,
        ValueError,
    ) as exc:
        print(f"LIVE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
