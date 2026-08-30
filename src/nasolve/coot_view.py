"""Resolve and launch stage-appropriate Coot views in isolated run pens."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .checkpoints import READABLE_SCHEMA_VERSIONS
from .model_assessment import file_sha256
from .run_context import resolve_artifact_path


class CootViewError(RuntimeError):
    """Raised when a requested result cannot be opened safely."""


_CHECKPOINT_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


@dataclass(frozen=True)
class ViewProfile:
    stage: str
    model_path: Path
    map_path: Path
    extra_model_paths: tuple[Path, ...]
    dictionary_paths: tuple[Path, ...]
    source: str


@dataclass(frozen=True)
class CootViewResult:
    run_directory: Path
    stage: str
    working_directory: Path
    model_path: Path
    map_path: Path
    extra_model_paths: tuple[Path, ...]
    dictionary_paths: tuple[Path, ...]
    log_path: Path
    command: tuple[str, ...]
    pid: int


def _required_file(path: Path, description: str) -> Path:
    if not path.is_file():
        raise CootViewError(f"{description} is missing: {path}")
    return path.resolve()


def _checkpoint_component(value: str) -> str:
    """Return a checkpoint ID that is safe to use as one directory name."""
    if _CHECKPOINT_COMPONENT.fullmatch(value) is None:
        raise CootViewError(
            "Checkpoint IDs used for Coot must be a single safe path component"
        )
    return value


def _reject_symlink_components(root: Path, target: Path) -> None:
    """Reject an existing symlink anywhere beneath a machine-local output path."""
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise CootViewError(f"Coot working path escapes the selected run: {target}") from exc
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise CootViewError(
                f"Coot working path contains a symbolic link: {candidate}"
            )


def _require_scratch_containment(scratch_root: Path, path: Path) -> None:
    """Verify that a created scratch path still resolves beneath its lexical root."""
    try:
        path.resolve().relative_to(scratch_root)
    except ValueError as exc:
        raise CootViewError(f"Coot working path escapes its scratch directory: {path}") from exc


def _reported_file(value: object, description: str, run: Path) -> Path:
    path = resolve_artifact_path(value, run)
    if path is None:
        raise CootViewError(f"Run report has no {description}")
    return _required_file(path, description)


def _verify_report_checksum(path: Path, expected: object, description: str) -> None:
    if expected is None:
        return
    if (
        not isinstance(expected, str)
        or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None
    ):
        raise CootViewError(f"Reported {description} checksum is malformed")
    if file_sha256(path) != expected.casefold():
        raise CootViewError(f"Reported {description} failed checksum validation")


def _require_checkpoint_checksum(value: object, description: str) -> None:
    if not isinstance(value, Mapping) or not isinstance(value.get("anchor"), str):
        raise CootViewError(f"Schema-2 checkpoint {description} is not portable")
    expected = value.get("sha256")
    if (
        not isinstance(expected, str)
        or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None
    ):
        raise CootViewError(f"Schema-2 checkpoint {description} checksum is malformed")


def _read_json(path: Path, description: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CootViewError(f"Could not read {description} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CootViewError(f"Malformed {description}: {path}")
    return value


def find_last_run(dataset: Path) -> Path:
    """Return the highest numbered run with a readable NASolve report."""
    root = dataset.expanduser().resolve()
    automr = root / "AutoMR"
    candidates: list[tuple[int, Path]] = []
    if automr.is_dir():
        for path in automr.iterdir():
            match = re.fullmatch(r"run_(\d+)", path.name)
            report_path = path / "report.json"
            if not match or not path.is_dir() or not report_path.is_file():
                continue
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(report, Mapping) and report.get("workflow") == "automr":
                candidates.append((int(match.group(1)), path.resolve()))
    if not candidates:
        raise CootViewError(f"No completed NASolve run was found beneath {root}")
    return max(candidates, key=lambda item: item[0])[1]


def resolve_run(target: Path | str, dataset: Path | None = None) -> Path:
    if str(target).casefold() == "last":
        if dataset is None:
            raise CootViewError("'nasolve show last' requires a dataset directory")
        return find_last_run(dataset)
    if dataset is not None:
        raise CootViewError("A dataset is accepted only with 'nasolve show last DATASET'")
    run = Path(target).expanduser().resolve()
    _required_file(run / "report.json", "AutoMR report")
    return run


def _postmr_dictionaries(
    run: Path, report: Mapping[str, object]
) -> tuple[Path, ...]:
    postmr = report.get("postmr")
    readyset = postmr.get("readyset") if isinstance(postmr, Mapping) else None
    generated = readyset.get("generated_ligand_cif") if isinstance(readyset, Mapping) else None
    generated_path = resolve_artifact_path(generated, run)
    if generated_path is not None:
        return (generated_path,)
    restraints = postmr.get("restraints") if isinstance(postmr, Mapping) else None
    if not isinstance(restraints, list):
        return ()
    dictionaries: list[Path] = []
    for value in restraints:
        if not isinstance(value, str) or not value.casefold().endswith(".cif"):
            continue
        path = resolve_artifact_path(value, run)
        if path is None:
            raise CootViewError(
                "PostMR ligand dictionary is missing or could not be rebased"
            )
        dictionaries.append(path)
    if isinstance(generated, str) and not dictionaries:
        raise CootViewError(
            "ReadySet ligand dictionary is missing and no input CIF fallback is available"
        )
    return tuple(dictionaries)


def _phaser_profile(run: Path, report: Mapping[str, object]) -> ViewProfile:
    execution = report.get("execution")
    phaser = execution.get("phaser") if isinstance(execution, Mapping) else None
    model_value = phaser.get("solution_pdb") if isinstance(phaser, Mapping) else None
    map_value = phaser.get("solution_mtz") if isinstance(phaser, Mapping) else None
    model = (
        _reported_file(model_value, "Phaser model", run)
        if isinstance(model_value, str)
        else _required_file(run / "Phaser" / "mr_solution.pdb", "Phaser model")
    )
    map_path = (
        _reported_file(map_value, "Phaser reflections", run)
        if isinstance(map_value, str)
        else _required_file(run / "Phaser" / "mr_solution.mtz", "Phaser reflections")
    )
    return ViewProfile("automr", model, map_path, (), (), "Phaser solution")


def _postmr_profile(run: Path, report: Mapping[str, object]) -> ViewProfile:
    postmr = report.get("postmr")
    if not isinstance(postmr, Mapping) or postmr.get("status") != "POSTMR_READY":
        raise CootViewError("This run has no completed PostMR result")
    model = _reported_file(postmr.get("prepared_model"), "ReadySet model", run)
    _verify_report_checksum(model, postmr.get("prepared_sha256"), "ReadySet model")
    phaser = _phaser_profile(run, report)
    return ViewProfile(
        "postmr",
        model,
        phaser.map_path,
        (),
        _postmr_dictionaries(run, report),
        "ReadySet model with Phaser map",
    )


def _autosol_map(run: Path) -> Path:
    preferred = [
        path for path in (run / "AutoSol").rglob("overall_best_denmod_map_coeffs.mtz")
        if path.is_file() and "PDS" not in path.parts
    ]
    if not preferred:
        preferred = [
            path for path in (run / "AutoSol").rglob("resolve_histograms*.mtz")
            if path.is_file() and "PDS" not in path.parts and "TEMP" not in path.parts
        ]
    if len(preferred) != 1:
        raise CootViewError(
            f"Expected one AutoSol density-modified map MTZ, found {len(preferred)}"
        )
    return preferred[0].resolve()


def _autosol_profile(run: Path, report: Mapping[str, object]) -> ViewProfile:
    autosol = report.get("autosol")
    outputs = autosol.get("outputs") if isinstance(autosol, Mapping) else None
    if not isinstance(outputs, Mapping):
        raise CootViewError("This run has no completed AutoSol output")
    heavy_atom = _reported_file(
        outputs.get("heavy_atom_model"), "AutoSol HA model", run
    )
    _verify_report_checksum(
        heavy_atom,
        outputs.get("heavy_atom_model_sha256"),
        "AutoSol HA model",
    )
    phaser = _phaser_profile(run, report)
    return ViewProfile(
        "autosol",
        phaser.model_path,
        _autosol_map(run),
        (heavy_atom,),
        (),
        "Phaser model, AutoSol HA sites, and density-modified map",
    )


def _autorefine_profile(
    run: Path,
    report: Mapping[str, object],
    checkpoint_id: str | None = None,
) -> ViewProfile:
    registry_path = run / "AutoRefine" / "checkpoints.json"
    registry = _read_json(registry_path, "checkpoint registry")
    schema_version = registry.get("schema_version")
    if (
        type(schema_version) is not int
        or schema_version not in READABLE_SCHEMA_VERSIONS
    ):
        raise CootViewError(f"Unsupported checkpoint schema: {schema_version}")
    current = checkpoint_id or registry.get("current")
    checkpoints = registry.get("checkpoints")
    if not isinstance(current, str) or not isinstance(checkpoints, list):
        raise CootViewError("Checkpoint registry has no requested model")
    checkpoint = next(
        (
            item for item in checkpoints
            if isinstance(item, Mapping) and item.get("id") == current
        ),
        None,
    )
    if not isinstance(checkpoint, Mapping) or checkpoint.get("kind") != "refinement":
        requested = checkpoint_id or "current"
        raise CootViewError(f"Checkpoint {requested} is not a completed refinement")
    model_ref = checkpoint.get("model")
    outputs = checkpoint.get("outputs")
    if schema_version == 2:
        _require_checkpoint_checksum(model_ref, "model")
    model = _reported_file(model_ref, "checkpoint model", run)
    map_value = outputs.get("map_coefficients") if isinstance(outputs, Mapping) else None
    if schema_version == 2 and map_value is not None:
        _require_checkpoint_checksum(map_value, "map coefficients")
    reported_map = resolve_artifact_path(map_value, run)
    if reported_map is not None:
        map_path = reported_map
    elif map_value is not None:
        raise CootViewError(
            "Checkpoint map coefficients are missing or failed checksum validation"
        )
    elif schema_version == 2:
        reflection_value = (
            outputs.get("refinement_reflections")
            if isinstance(outputs, Mapping)
            else None
        )
        _require_checkpoint_checksum(
            reflection_value,
            "refinement reflections",
        )
        refinement_reflections = resolve_artifact_path(reflection_value, run)
        if refinement_reflections is None:
            raise CootViewError(
                "Checkpoint refinement reflections are missing or failed "
                "checksum validation"
            )
        map_path = refinement_reflections
    else:
        # Phenix 1.20.x stores 2mFo-DFc/mFo-DFc coefficients in the primary
        # refinement MTZ rather than a separately named *_map_coeffs.mtz file.
        map_path = _required_file(model.with_suffix(".mtz"), "refinement map coefficients")
    restraints = checkpoint.get("restraints")
    dictionaries: list[Path] = []
    if isinstance(restraints, list):
        for value in restraints:
            if schema_version == 2:
                _require_checkpoint_checksum(value, "restraint")
            path = resolve_artifact_path(value, run)
            if path is not None:
                if path.suffix.casefold() == ".cif":
                    dictionaries.append(path)
                continue
            reported_value = (
                value.get(
                    "relative_path",
                    value.get("absolute_path", value.get("path")),
                )
                if isinstance(value, Mapping)
                else None
            )
            if (
                isinstance(reported_value, str)
                and reported_value.casefold().endswith(".cif")
            ):
                raise CootViewError(
                    "Checkpoint ligand dictionary is missing or failed checksum validation"
                )
    return ViewProfile(
        "autorefine",
        model,
        map_path,
        (),
        tuple(dictionaries),
        f"current refinement checkpoint {current}",
    )


def resolve_view_profile(
    run_directory: Path,
    *,
    stage: str | None = None,
    checkpoint: str | None = None,
) -> ViewProfile:
    run = run_directory.expanduser().resolve()
    if checkpoint is not None:
        checkpoint = _checkpoint_component(checkpoint)
    report = _read_json(_required_file(run / "report.json", "AutoMR report"), "run report")
    resolvers = {
        "automr": _phaser_profile,
        "postmr": _postmr_profile,
        "autosol": _autosol_profile,
        "autorefine": _autorefine_profile,
    }
    if checkpoint is not None:
        if stage not in {None, "autorefine"}:
            raise CootViewError("--checkpoint may be used only with the AutoRefine view")
        return _autorefine_profile(run, report, checkpoint)
    if stage is not None:
        try:
            return resolvers[stage](run, report)
        except KeyError as exc:
            raise CootViewError(f"Unknown viewing stage: {stage}") from exc

    registry_path = run / "AutoRefine" / "checkpoints.json"
    if registry_path.is_file():
        registry = _read_json(registry_path, "checkpoint registry")
        schema_version = registry.get("schema_version")
        if (
            type(schema_version) is not int
            or schema_version not in READABLE_SCHEMA_VERSIONS
        ):
            raise CootViewError(f"Unsupported checkpoint schema: {schema_version}")
        current = registry.get("current")
        checkpoints = registry.get("checkpoints")
        if not isinstance(current, str) or not isinstance(checkpoints, list):
            raise CootViewError("Checkpoint registry has no valid current pointer")
        current_item = next(
            (
                item
                for item in checkpoints
                if isinstance(item, Mapping) and item.get("id") == current
            ),
            None,
        )
        if current_item is None:
            raise CootViewError(f"Checkpoint registry current pointer is unknown: {current}")
        if current_item.get("kind") == "refinement":
            return _autorefine_profile(run, report)
    autosol = report.get("autosol")
    autosol_outputs = autosol.get("outputs") if isinstance(autosol, Mapping) else None
    heavy_atom_value = (
        autosol_outputs.get("heavy_atom_model")
        if isinstance(autosol_outputs, Mapping)
        else None
    )
    if heavy_atom_value is not None:
        return _autosol_profile(run, report)
    postmr = report.get("postmr")
    if isinstance(postmr, Mapping) and postmr.get("status") == "POSTMR_READY":
        return _postmr_profile(run, report)
    execution = report.get("execution")
    phaser = execution.get("phaser") if isinstance(execution, Mapping) else None
    if isinstance(phaser, Mapping) or (run / "Phaser" / "mr_solution.pdb").is_file():
        return _phaser_profile(run, report)
    raise CootViewError("No completed stage in this run can be opened in Coot")


def launch_coot_view(
    run_directory: Path,
    coot_executable: Path,
    *,
    stage: str | None = None,
    checkpoint: str | None = None,
    environment: Mapping[str, str] | None = None,
    launcher: Callable[..., object] = subprocess.Popen,
) -> CootViewResult:
    """Open a resolved result without allowing Coot to litter the repository."""
    run = run_directory.expanduser().resolve()
    if checkpoint is not None:
        checkpoint = _checkpoint_component(checkpoint)
    profile = resolve_view_profile(run, stage=stage, checkpoint=checkpoint)
    scratch_root = run / "CootGUI"
    working = scratch_root / profile.stage
    if checkpoint is not None:
        working = working / checkpoint
    backups = working / "backups"
    _reject_symlink_components(run, backups)
    try:
        backups.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CootViewError(f"Could not create Coot working directory: {exc}") from exc
    _reject_symlink_components(run, backups)
    _require_scratch_containment(scratch_root, working)
    _require_scratch_containment(scratch_root, backups)
    log = working / "coot_gui.log"
    launch_record = working / "launch.json"
    for output in (log, launch_record):
        if output.is_symlink():
            raise CootViewError(f"Refusing to write Coot output through a symlink: {output}")
    command = [
        str(coot_executable.expanduser().resolve()),
        "--pdb",
        str(profile.model_path),
    ]
    for extra in profile.extra_model_paths:
        command.extend(["--pdb", str(extra)])
    for dictionary in profile.dictionary_paths:
        command.extend(["--dictionary", str(dictionary)])
    command.extend(["--auto", str(profile.map_path)])

    env = dict(os.environ if environment is None else environment)
    env["COOT_BACKUP_DIR"] = str(backups)
    try:
        with log.open("a", encoding="utf-8") as stream:
            process = launcher(
                command,
                cwd=working,
                env=env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError as exc:
        raise CootViewError(f"Could not launch graphical Coot: {exc}") from exc
    pid = getattr(process, "pid", None)
    if not isinstance(pid, int):
        raise CootViewError("Graphical Coot launcher returned no process ID")
    launch_record.write_text(
        json.dumps(
            {
                "pid": pid,
                "stage": profile.stage,
                "source": profile.source,
                "command": command,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return CootViewResult(
        run_directory=run,
        stage=profile.stage,
        working_directory=working,
        model_path=profile.model_path,
        map_path=profile.map_path,
        extra_model_paths=profile.extra_model_paths,
        dictionary_paths=profile.dictionary_paths,
        log_path=log,
        command=tuple(command),
        pid=pid,
    )


__all__ = [
    "CootViewError",
    "CootViewResult",
    "ViewProfile",
    "find_last_run",
    "launch_coot_view",
    "resolve_run",
    "resolve_view_profile",
]
