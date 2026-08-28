"""Resolve and launch stage-appropriate Coot views in isolated run pens."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping


class CootViewError(RuntimeError):
    """Raised when a requested result cannot be opened safely."""


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


def _reported_file(value: object, description: str) -> Path:
    if not isinstance(value, str):
        raise CootViewError(f"Run report has no {description}")
    return _required_file(Path(value).expanduser(), description)


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


def _postmr_dictionaries(report: Mapping[str, object]) -> tuple[Path, ...]:
    postmr = report.get("postmr")
    readyset = postmr.get("readyset") if isinstance(postmr, Mapping) else None
    generated = readyset.get("generated_ligand_cif") if isinstance(readyset, Mapping) else None
    if isinstance(generated, str) and Path(generated).expanduser().is_file():
        return (Path(generated).expanduser().resolve(),)
    restraints = postmr.get("restraints") if isinstance(postmr, Mapping) else None
    if not isinstance(restraints, list):
        return ()
    return tuple(
        Path(value).expanduser().resolve()
        for value in restraints
        if isinstance(value, str)
        and value.casefold().endswith(".cif")
        and Path(value).expanduser().is_file()
    )


def _phaser_profile(run: Path, report: Mapping[str, object]) -> ViewProfile:
    execution = report.get("execution")
    phaser = execution.get("phaser") if isinstance(execution, Mapping) else None
    model_value = phaser.get("solution_pdb") if isinstance(phaser, Mapping) else None
    map_value = phaser.get("solution_mtz") if isinstance(phaser, Mapping) else None
    model = (
        _reported_file(model_value, "Phaser model")
        if isinstance(model_value, str)
        else _required_file(run / "Phaser" / "mr_solution.pdb", "Phaser model")
    )
    map_path = (
        _reported_file(map_value, "Phaser reflections")
        if isinstance(map_value, str)
        else _required_file(run / "Phaser" / "mr_solution.mtz", "Phaser reflections")
    )
    return ViewProfile("automr", model, map_path, (), (), "Phaser solution")


def _postmr_profile(run: Path, report: Mapping[str, object]) -> ViewProfile:
    postmr = report.get("postmr")
    if not isinstance(postmr, Mapping) or postmr.get("status") != "POSTMR_READY":
        raise CootViewError("This run has no completed PostMR result")
    model = _reported_file(postmr.get("prepared_model"), "ReadySet model")
    phaser = _phaser_profile(run, report)
    return ViewProfile(
        "postmr",
        model,
        phaser.map_path,
        (),
        _postmr_dictionaries(report),
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
    heavy_atom = _reported_file(outputs.get("heavy_atom_model"), "AutoSol HA model")
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
    model = _reported_file(
        model_ref.get("path") if isinstance(model_ref, Mapping) else None,
        "checkpoint model",
    )
    map_value = outputs.get("map_coefficients") if isinstance(outputs, Mapping) else None
    if isinstance(map_value, str) and Path(map_value).expanduser().is_file():
        map_path = Path(map_value).expanduser().resolve()
    else:
        # Phenix 1.20.x stores 2mFo-DFc/mFo-DFc coefficients in the primary
        # refinement MTZ rather than a separately named *_map_coeffs.mtz file.
        map_path = _required_file(model.with_suffix(".mtz"), "refinement map coefficients")
    restraints = checkpoint.get("restraints")
    dictionaries: list[Path] = []
    if isinstance(restraints, list):
        for value in restraints:
            path_value = value.get("path") if isinstance(value, Mapping) else None
            if isinstance(path_value, str) and path_value.casefold().endswith(".cif"):
                path = Path(path_value).expanduser()
                if path.is_file():
                    dictionaries.append(path.resolve())
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
    for candidate in ("autorefine", "autosol", "postmr", "automr"):
        try:
            return resolvers[candidate](run, report)
        except CootViewError:
            continue
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
    profile = resolve_view_profile(run, stage=stage, checkpoint=checkpoint)
    working = run / "CootGUI" / profile.stage
    if checkpoint is not None:
        working = working / checkpoint
    backups = working / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    log = working / "coot_gui.log"
    command = [str(coot_executable.expanduser().resolve()), "--pdb", str(profile.model_path)]
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
    (working / "launch.json").write_text(
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
