"""Bounded, checkpoint-preserving refinement diagnosis and triage."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .autorefine import (
    AutoRefineError,
    AutoRefineResult,
    build_reflection_plan,
    execute_autorefine,
    reflection_selector_policy,
)
from .checkpoints import (
    CheckpointError,
    inherited_paths,
    initialize_registry,
    resolve_checkpoint,
)


class RefineDoctorError(RuntimeError):
    """Raised when refinement triage cannot be performed safely."""


@dataclass(frozen=True)
class FreeRAudit:
    status: str
    valid: bool | None
    details: dict[str, object]
    warnings: tuple[str, ...]
    log_path: Path


@dataclass(frozen=True)
class RefineDoctorResult:
    status: str
    message: str
    exit_code: int
    run_directory: Path
    doctor_directory: Path
    source_checkpoint: str
    current_checkpoint_preserved: bool
    recommended_checkpoint: str | None
    recommendation: str
    audit: FreeRAudit
    trials: tuple[AutoRefineResult, ...]
    benchmark: tuple[dict[str, object], ...]
    report_path: Path


@dataclass(frozen=True)
class RefineDoctorTrial:
    """One declarative branch; project presets may supply additional recipes later."""

    recipe: str
    use_experimental_phases: bool
    real_space_sites: bool = False
    adp_mode: str = "group"
    refine_occupancies: bool = False
    anomalous_mode: str = "off"
    requires_phases: bool = False
    maximum_resolution_limit: float | None = None
    minimum_observations_per_atom: float | None = None


DEFAULT_TRIALS = (
    RefineDoctorTrial("RefineDoctor/ML-group-anomalous-off", False),
    RefineDoctorTrial(
        "RefineDoctor/MLHL-group-anomalous-off", True, requires_phases=True
    ),
    RefineDoctorTrial(
        "RefineDoctor/ML-individual-ADP",
        False,
        adp_mode="individual",
        maximum_resolution_limit=3.2,
        minimum_observations_per_atom=3.0,
    ),
)


_AUDIT_MARKER = "NASOLVE_FREE_R_AUDIT_JSON:"
_AUDIT_SCRIPT = r'''
from __future__ import print_function
import json
import sys
from iotbx import reflection_file_reader

# NASOLVE_FREE_R_AUDIT
filename, wanted_label, test_text = sys.argv[1:4]
test_value = int(test_text)
reflection_file = reflection_file_reader.any_reflection_file(filename)
try:
    arrays = reflection_file.as_miller_arrays(merge_equivalents=False)
except TypeError:
    arrays = reflection_file.as_miller_arrays()
selected = None
available = []
for array in arrays:
    info = array.info()
    labels = list(getattr(info, "labels", []) or [])
    label_string = info.label_string()
    available.append(label_string)
    if wanted_label in labels or label_string == wanted_label:
        selected = array
        break
if selected is None:
    raise RuntimeError("Free-R label not found; available: " + "; ".join(available))

unit_cell = selected.unit_cell()
indices = list(selected.indices())
data = list(selected.data())
groups = []
matching_method = "cctbx-match-bijvoet-mates"
try:
    matches = selected.match_bijvoet_mates()
    paired_positions = set()
    for first, second in matches.pairs():
        first, second = int(first), int(second)
        paired_positions.update([first, second])
        groups.append({
            "indices": [tuple(indices[first]), tuple(indices[second])],
            "values": set([int(data[first]), int(data[second])]),
            "d": float(unit_cell.d(indices[first])),
        })
    for position in range(len(indices)):
        if position in paired_positions:
            continue
        groups.append({
            "indices": [tuple(indices[position])],
            "values": set([int(data[position])]),
            "d": float(unit_cell.d(indices[position])),
        })
except Exception:
    matching_method = "exact-hkl-fallback"
    exact = {}
    for hkl, raw_value in zip(indices, data):
        index = tuple(int(value) for value in hkl)
        inverse = tuple(-value for value in index)
        key = min(index, inverse)
        item = exact.setdefault(key, {"indices": set(), "values": set(), "d": None})
        item["indices"].add(index)
        item["values"].add(int(raw_value))
        if item["d"] is None:
            item["d"] = float(unit_cell.d(index))
    groups = list(exact.values())

ordered = sorted(groups, key=lambda item: item["d"], reverse=True)
shells = [{"groups": 0, "free_groups": 0} for unused in range(10)]
free_groups = 0
inconsistent = 0
paired = 0
for number, item in enumerate(ordered):
    is_free = test_value in item["values"]
    if is_free:
        free_groups += 1
    if len(item["values"]) > 1:
        inconsistent += 1
    if len(item["indices"]) > 1:
        paired += 1
    shell = min(9, int(number * 10 / max(1, len(ordered))))
    shells[shell]["groups"] += 1
    shells[shell]["free_groups"] += int(is_free)

payload = {
    "array_labels": selected.info().label_string(),
    "array_anomalous": bool(selected.anomalous_flag()),
    "matching_method": matching_method,
    "stored_observations": len(selected.indices()),
    "independent_friedel_groups": len(ordered),
    "paired_friedel_groups": paired,
    "free_independent_groups": free_groups,
    "free_fraction": float(free_groups) / max(1, len(ordered)),
    "inconsistent_friedel_flag_groups": inconsistent,
    "test_flag_value": test_value,
    "resolution_shells": shells,
}
print("NASOLVE_FREE_R_AUDIT_JSON:" + json.dumps(payload, sort_keys=True))
'''


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _next_doctor_directory(run: Path) -> Path:
    root = run / "RefineDoctor"
    root.mkdir(parents=True, exist_ok=True)
    numbers = [
        int(match.group(1))
        for path in root.glob("doctor_*")
        if path.is_dir() and (match := re.fullmatch(r"doctor_(\d+)", path.name))
    ]
    destination = root / f"doctor_{max(numbers, default=0) + 1:03d}"
    destination.mkdir()
    return destination


def audit_free_r_flags(
    observations: Path,
    free_r_label: str,
    test_flag_value: int,
    phenix_python: Path,
    destination: Path,
    environment: Mapping[str, str] | None = None,
) -> FreeRAudit:
    """Audit the frozen test set without changing or regenerating it."""
    script_path = destination / "audit_free_r.py"
    log_path = destination / "free_r_audit.log"
    script_path.write_text(_AUDIT_SCRIPT.lstrip(), encoding="utf-8")
    try:
        completed = subprocess.run(
            [
                str(phenix_python.expanduser().resolve()),
                str(script_path),
                str(observations),
                free_r_label,
                str(test_flag_value),
            ],
            env=dict(environment) if environment is not None else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(f"Free-R audit could not run: {exc}\n", encoding="utf-8")
        return FreeRAudit(
            "UNAVAILABLE", None, {}, ("Free-R audit could not be executed",), log_path
        )
    log_path.write_text(completed.stdout, encoding="utf-8")
    matches = re.findall(
        re.escape(_AUDIT_MARKER) + r"(\{.*\})", completed.stdout, re.MULTILINE
    )
    if completed.returncode or not matches:
        return FreeRAudit(
            "UNAVAILABLE",
            None,
            {"phenix_python_exit_code": completed.returncode},
            ("Free-R audit returned no machine-readable result",),
            log_path,
        )
    try:
        details = json.loads(matches[-1])
    except json.JSONDecodeError:
        return FreeRAudit(
            "UNAVAILABLE", None, {}, ("Free-R audit result was malformed",), log_path
        )

    warnings: list[str] = []
    invalid: list[str] = []
    inconsistent = details.get("inconsistent_friedel_flag_groups")
    if isinstance(inconsistent, int) and inconsistent:
        invalid.append(f"{inconsistent} Friedel group(s) have inconsistent test flags")
    fraction = details.get("free_fraction")
    if not isinstance(fraction, (int, float)) or not 0.02 <= float(fraction) <= 0.20:
        invalid.append("Free-R fraction is outside the guarded 2-20% range")
    free_groups = details.get("free_independent_groups")
    if not isinstance(free_groups, int) or free_groups < 10:
        invalid.append("Fewer than 10 independent Free-R groups are available")
    elif free_groups < 100:
        warnings.append(
            f"Only {free_groups} independent Free-R groups are available; Rfree is noisy"
        )
    paired = details.get("paired_friedel_groups")
    if paired == 0:
        warnings.append("Stored array did not expose Friedel mates for a direct consistency test")
    shells = details.get("resolution_shells")
    if isinstance(shells, list) and any(
        isinstance(shell, Mapping) and shell.get("groups", 0) and shell.get("free_groups") == 0
        for shell in shells
    ):
        warnings.append("At least one resolution shell contains no independent Free-R group")
    if invalid:
        return FreeRAudit("INVALID", False, details, tuple(invalid + warnings), log_path)
    if warnings:
        return FreeRAudit("NOISY", True, details, tuple(warnings), log_path)
    return FreeRAudit("VALID", True, details, (), log_path)


def _coordinate_atom_count(model: Path) -> int:
    return sum(
        line[0:6].strip().upper() in {"ATOM", "HETATM"}
        for line in model.read_text(encoding="utf-8", errors="replace").splitlines()
    )


def _benchmark_from_checkpoint(
    checkpoint: Mapping[str, object], source: str
) -> list[dict[str, object]]:
    metrics = checkpoint.get("metrics")
    values = metrics.get("anomalous_scatterers") if isinstance(metrics, Mapping) else None
    if not isinstance(values, list):
        return []
    benchmarks: list[dict[str, object]] = []
    for value in values:
        if not isinstance(value, Mapping) or not isinstance(
            value.get("refined_f_double_prime"), (int, float)
        ):
            continue
        benchmarks.append({**dict(value), "source_checkpoint": source})
    return benchmarks


def _metrics(checkpoint: Mapping[str, object]) -> dict[str, object]:
    values = checkpoint.get("metrics")
    return dict(values) if isinstance(values, Mapping) else {}


def _candidate(checkpoint: str, recipe: str, statistics: Mapping[str, object]) -> dict[str, object]:
    work = statistics.get("r_work")
    free = statistics.get("r_free")
    gap = (
        float(free) - float(work)
        if isinstance(work, (int, float)) and isinstance(free, (int, float)) else None
    )
    return {
        "checkpoint": checkpoint,
        "recipe": recipe,
        "r_work": work,
        "r_free": free,
        "r_free_minus_r_work": gap,
        "strict_success": (
            isinstance(work, (int, float))
            and isinstance(free, (int, float))
            and float(work) < 0.30
            and float(work) < float(free)
        ),
        "near_tie": (
            isinstance(work, (int, float))
            and isinstance(gap, float)
            and float(work) < 0.30
            and gap >= -0.01
        ),
    }


def _recommend(
    candidates: list[dict[str, object]],
    source_checkpoint: str,
    audit: FreeRAudit,
) -> tuple[str, str | None, str, int]:
    source = candidates[0]
    if source.get("strict_success") is True and audit.valid is not False:
        return (
            "REFINE_DOCTOR_GOOD_ENOUGH",
            source_checkpoint,
            "The selected checkpoint already meets the numerical gate; no replacement is needed",
            0,
        )
    successes = [candidate for candidate in candidates[1:] if candidate.get("strict_success")]
    if successes:
        choice = min(
            successes,
            key=lambda item: (
                float(item["r_free"]),
                float(item["r_work"]),
            ),
        )
        return (
            "REFINE_DOCTOR_RECOMMEND",
            str(choice["checkpoint"]),
            "A bounded validation branch restored Rwork < Rfree while retaining Rwork < 0.30",
            0,
        )
    if source.get("near_tie") is True and audit.valid is not False:
        return (
            "REFINE_DOCTOR_GOOD_ENOUGH",
            source_checkpoint,
            "The small Rwork/Rfree inversion is consistent with a noisy test set; keep the model under review rather than regenerate flags",
            0,
        )
    near_ties = [candidate for candidate in candidates[1:] if candidate.get("near_tie")]
    if near_ties and audit.valid is not False:
        choice = max(near_ties, key=lambda item: float(item["r_free_minus_r_work"]))
        return (
            "REFINE_DOCTOR_RECOMMEND",
            str(choice["checkpoint"]),
            "No branch passed strictly, but this bounded branch is the best statistically plausible checkpoint",
            0,
        )
    return (
        "REFINE_DOCTOR_REVIEW",
        None,
        "The bounded trials did not produce a defensible automatic recommendation",
        2,
    )


def _update_run_report(run: Path, payload: Mapping[str, object]) -> None:
    path = run / "report.json"
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RefineDoctorError(f"Could not update run report: {exc}") from exc
    history = report.setdefault("refine_doctor_history", [])
    if not isinstance(history, list):
        raise RefineDoctorError("Run report has malformed Refine Doctor history")
    history.append(dict(payload))
    report["refine_doctor"] = dict(payload)
    report["stage"] = "refine-doctor"
    report["status"] = payload["status"]
    report["message"] = payload["message"]
    report["updated_utc"] = payload["created_utc"]
    _write_json(path, report)


def execute_refine_doctor(
    run_directory: Path,
    refine_executable: Path,
    mtz_dump_executable: Path,
    *,
    phenix_version: str,
    environment: Mapping[str, str] | None = None,
    from_checkpoint: str | None = None,
    macro_cycles: int = 3,
    processor_count: int | None = None,
    trial_recipes: Sequence[RefineDoctorTrial] | None = None,
    progress: Callable[[str, str, Path], None] | None = None,
) -> RefineDoctorResult:
    """Audit and run a finite set of sibling refinements without selecting one."""
    try:
        selector_policy = reflection_selector_policy(phenix_version)
    except AutoRefineError as exc:
        raise RefineDoctorError(str(exc)) from exc
    try:
        run, registry = initialize_registry(run_directory)
        source = resolve_checkpoint(registry, from_checkpoint)
        if source.get("usable") is not True:
            raise RefineDoctorError(f"Checkpoint {source.get('id')} is not reusable")
        inherited = inherited_paths(source, run)
    except CheckpointError as exc:
        raise RefineDoctorError(str(exc)) from exc
    source_id = str(source["id"])
    original_current = str(registry.get("current"))
    observations = inherited.get("observations")
    model = inherited.get("model")
    if not isinstance(observations, Path) or not isinstance(model, Path):
        raise RefineDoctorError("Selected checkpoint has incomplete crystallographic inputs")
    try:
        report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RefineDoctorError(f"Could not read run report: {exc}") from exc
    destination = _next_doctor_directory(run)
    try:
        plan = build_reflection_plan(
            report, observations, mtz_dump_executable, environment, phase_file=None
        )
    except AutoRefineError as exc:
        raise RefineDoctorError(str(exc)) from exc
    phenix_python = refine_executable.expanduser().resolve().parent / "phenix.python"
    audit = audit_free_r_flags(
        observations,
        plan.free_r_label,
        plan.free_r_test_value,
        phenix_python,
        destination,
        environment,
    )
    created = _now()
    if audit.valid is False:
        status = "REFINE_DOCTOR_FLAG_REPAIR_REQUIRED"
        message = "The frozen Free-R set failed an objective audit; no refinement trials were run"
        payload = {
            "status": status,
            "message": message,
            "created_utc": created,
            "phenix_version": selector_policy.phenix_version,
            "reflection_selector_mode": selector_policy.mode,
            "source_checkpoint": source_id,
            "current_checkpoint_preserved": True,
            "audit": {**audit.details, "status": audit.status, "warnings": list(audit.warnings)},
            "benchmark": [],
            "trials": [],
            "recommended_checkpoint": None,
            "recommendation": "Repair the flags deliberately in a separate branch; NASolve did not regenerate them",
        }
        report_path = destination / "report.json"
        _write_json(report_path, payload)
        _update_run_report(run, payload)
        return RefineDoctorResult(
            status, message, 2, run, destination, source_id, True, None,
            str(payload["recommendation"]), audit, (), (), report_path
        )

    source_candidate = _candidate(source_id, str(source.get("recipe", "source")), _metrics(source))
    candidates = [source_candidate]
    benchmark = _benchmark_from_checkpoint(source, source_id)
    trials: list[AutoRefineResult] = []
    phase_available = isinstance(inherited.get("phases"), Path)
    autosol = report.get("autosol")
    if isinstance(autosol, Mapping) and autosol.get("use_for_refinement") is True:
        phase_available = True
    anomalous_present = bool(
        isinstance(report.get("postmr"), Mapping)
        and isinstance(report["postmr"].get("anomalous"), Mapping)
        and report["postmr"]["anomalous"].get("candidates")
    )

    trial_specs: list[RefineDoctorTrial] = []
    if anomalous_present and not benchmark:
        trial_specs.append(RefineDoctorTrial(
            "RefineDoctor/anomalous-benchmark",
            phase_available,
            anomalous_mode="refine",
        ))
    independent = audit.details.get("independent_friedel_groups")
    ratio = float(independent) / max(1, _coordinate_atom_count(model)) if isinstance(independent, int) else None
    default_pool: Sequence[RefineDoctorTrial] = (
        ()
        if trial_recipes is None and source_candidate.get("strict_success") is True
        else DEFAULT_TRIALS
    )
    for trial in trial_recipes if trial_recipes is not None else default_pool:
        if trial.requires_phases and not phase_available:
            continue
        if (
            trial.maximum_resolution_limit is not None
            and (
                plan.resolution_limit is None
                or plan.resolution_limit > trial.maximum_resolution_limit
            )
        ):
            continue
        if (
            trial.minimum_observations_per_atom is not None
            and (ratio is None or ratio < trial.minimum_observations_per_atom)
        ):
            continue
        trial_specs.append(trial)

    for spec in trial_specs:
        recipe = spec.recipe

        def trial_progress(checkpoint: str, log: Path, recipe_name: str = recipe) -> None:
            if progress is not None:
                progress(recipe_name, checkpoint, log)

        try:
            result = execute_autorefine(
                run,
                refine_executable,
                mtz_dump_executable,
                phenix_version=selector_policy.phenix_version,
                environment=environment,
                from_checkpoint=source_id,
                recipe=recipe,
                macro_cycles=macro_cycles,
                processor_count=processor_count,
                use_experimental_phases=spec.use_experimental_phases,
                real_space_sites=spec.real_space_sites,
                adp_mode=spec.adp_mode,
                refine_occupancies=spec.refine_occupancies,
                anomalous_mode=spec.anomalous_mode,
                auto_select_success=False,
                progress=trial_progress,
            )
        except AutoRefineError as exc:
            raise RefineDoctorError(f"Doctor trial {recipe} could not run: {exc}") from exc
        trials.append(result)
        candidates.append(_candidate(result.checkpoint_id, recipe, result.statistics))
        if recipe.endswith("anomalous-benchmark"):
            benchmark = [
                {**dict(item), "source_checkpoint": result.checkpoint_id}
                for item in result.statistics.get("anomalous_scatterers", [])
                if isinstance(item, Mapping)
                and isinstance(item.get("refined_f_double_prime"), (int, float))
            ]

    try:
        _, final_registry = initialize_registry(run)
    except CheckpointError as exc:
        raise RefineDoctorError(str(exc)) from exc
    current_preserved = str(final_registry.get("current")) == original_current
    if not current_preserved:
        raise RefineDoctorError("Refine Doctor changed the current checkpoint unexpectedly")
    status, recommended, recommendation, exit_code = _recommend(
        candidates, source_id, audit
    )
    message = {
        "REFINE_DOCTOR_GOOD_ENOUGH": "The selected refinement is defensible without changing Free-R flags",
        "REFINE_DOCTOR_RECOMMEND": "A bounded refinement branch is recommended for inspection",
        "REFINE_DOCTOR_REVIEW": "Refinement remains a user-review case after bounded triage",
    }[status]
    payload = {
        "status": status,
        "message": message,
        "created_utc": created,
        "phenix_version": selector_policy.phenix_version,
        "reflection_selector_mode": selector_policy.mode,
        "source_checkpoint": source_id,
        "current_checkpoint_preserved": current_preserved,
        "audit": {**audit.details, "status": audit.status, "warnings": list(audit.warnings)},
        "benchmark": benchmark,
        "eligibility": {
            "resolution_limit": plan.resolution_limit,
            "independent_observations_per_atom": ratio,
            "individual_adp_trial": any(
                spec.recipe.endswith("individual-ADP") for spec in trial_specs
            ),
        },
        "candidates": candidates,
        "trials": [
            {
                "checkpoint": trial.checkpoint_id,
                "parent": trial.parent_checkpoint,
                "status": trial.status,
                "report": str(trial.report_path),
                "log": str(trial.log_path),
            }
            for trial in trials
        ],
        "recommended_checkpoint": recommended,
        "recommendation": recommendation,
        "automatic_selection": False,
    }
    report_path = destination / "report.json"
    _write_json(report_path, payload)
    _update_run_report(run, payload)
    return RefineDoctorResult(
        status=status,
        message=message,
        exit_code=exit_code,
        run_directory=run,
        doctor_directory=destination,
        source_checkpoint=source_id,
        current_checkpoint_preserved=current_preserved,
        recommended_checkpoint=recommended,
        recommendation=recommendation,
        audit=audit,
        trials=tuple(trials),
        benchmark=tuple(benchmark),
        report_path=report_path,
    )


__all__ = [
    "FreeRAudit",
    "RefineDoctorError",
    "RefineDoctorResult",
    "RefineDoctorTrial",
    "DEFAULT_TRIALS",
    "audit_free_r_flags",
    "execute_refine_doctor",
]
