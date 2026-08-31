"""Quiet, guarded Phenix refinement with immutable checkpoint lineage."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .checkpoints import (
    CheckpointError,
    _inherited_paths_for_autorefine,
    append_checkpoint,
    inherited_paths,
    initialize_registry,
    next_checkpoint_id,
    resolve_checkpoint,
)
from .model_assessment import file_sha256
from .run_context import artifact_reference, resolve_artifact_path


class AutoRefineError(RuntimeError):
    """Raised when a guarded refinement cannot be prepared safely."""


@dataclass(frozen=True)
class ReflectionPlan:
    observation_labels: tuple[str, ...]
    free_r_label: str
    free_r_test_value: int
    anomalous: bool
    phase_labels: tuple[str, ...]
    phase_file: Path | None
    anomalous_fallback: bool
    fallback_is_error: bool
    resolution_limit: float | None


@dataclass(frozen=True)
class ReflectionSelectorPolicy:
    """Version-gated Phenix reflection-array selection behavior."""

    phenix_version: str
    mode: str

    @property
    def use_data_manager(self) -> bool:
        if self.mode == DATA_MANAGER_FILE_SCOPED:
            return True
        if self.mode == LEGACY_EXPLICIT:
            return False
        raise AutoRefineError(f"Unsupported reflection-selector mode: {self.mode}")


@dataclass(frozen=True)
class AutoRefineResult:
    status: str
    message: str
    exit_code: int
    run_directory: Path
    round_directory: Path
    checkpoint_id: str
    parent_checkpoint: str
    report_path: Path
    log_path: Path
    model_path: Path | None
    model_cif: Path | None
    reflection_cif: Path | None
    map_coefficients: Path | None
    statistics: dict[str, object]
    selected_as_current: bool


@dataclass(frozen=True)
class _VerifiedPhase:
    """An approved phase file and the identity verified before refinement."""

    path: Path
    sha256: str
    size: int
    identity: tuple[int, int, int, int, int]


ANOMALOUS_F_LABELS = ("F(+)", "SIGF(+)", "F(-)", "SIGF(-)")
MEAN_LABEL_SETS = (
    ("IMEAN", "SIGIMEAN"),
    ("F", "SIGF"),
    ("FP", "SIGFP"),
    ("I", "SIGI"),
)
HL_LABEL_SETS = (
    ("HLAM", "HLBM", "HLCM", "HLDM"),
    ("HLA", "HLB", "HLC", "HLD"),
    ("HL_A", "HL_B", "HL_C", "HL_D"),
)
FREE_R_LABELS = ("FreeR_flag", "R-free-flags", "FREE", "FreeR")
DATA_MANAGER_FILE_SCOPED = "data-manager-file-scoped"
LEGACY_EXPLICIT = "legacy-explicit"
_PHENIX_VERSION = re.compile(
    r"(?:Phenix\s+)?(\d+)\.(\d+)(?:\.(\d+))?"
    r"(?:[-._][A-Za-z0-9][A-Za-z0-9._-]*)?",
    re.I,
)


def reflection_selector_policy(phenix_version: str) -> ReflectionSelectorPolicy:
    """Choose only a reflection-selector mode validated for this Phenix family."""
    if not isinstance(phenix_version, str):
        raise AutoRefineError(
            "Phenix version is missing; NASolve will not guess selector support"
        )
    normalized = phenix_version.strip()
    match = _PHENIX_VERSION.fullmatch(normalized)
    if match is None:
        raise AutoRefineError(
            f"Could not interpret Phenix version {phenix_version!r}; NASolve will not "
            "guess reflection-selector support"
        )
    family = (int(match.group(1)), int(match.group(2)))
    if family == (1, 20):
        mode = LEGACY_EXPLICIT
    elif family == (2, 1):
        mode = DATA_MANAGER_FILE_SCOPED
    else:
        raise AutoRefineError(
            f"Phenix {normalized} has no validated NASolve reflection-selector policy; "
            "validated families are 1.20.x and 2.1.x"
        )
    return ReflectionSelectorPolicy(normalized, mode)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_report(run: Path) -> dict[str, object]:
    try:
        report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutoRefineError(f"Could not read NASolve run report: {exc}") from exc
    if not isinstance(report, dict):
        raise AutoRefineError("NASolve run report is not a JSON object")
    if report.get("workflow") != "automr" or not isinstance(report.get("postmr"), Mapping):
        raise AutoRefineError("AutoRefine requires a completed NASolve PostMR run")
    return report


def _run_mtz_dump(
    path: Path,
    executable: Path,
    environment: Mapping[str, str] | None,
) -> str:
    try:
        completed = subprocess.run(
            [str(executable.expanduser().resolve()), str(path)],
            env=dict(environment) if environment is not None else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AutoRefineError(f"Could not inspect reflection file {path}: {exc}") from exc
    if completed.returncode:
        raise AutoRefineError(f"phenix.mtz.dump failed for {path.name}")
    return completed.stdout


def _has_label(output: str, label: str) -> bool:
    return re.search(rf"(?<!\S){re.escape(label)}(?!\S)", output, re.I) is not None


def _first_label_set(output: str, candidates: Sequence[Sequence[str]]) -> tuple[str, ...] | None:
    for labels in candidates:
        if all(_has_label(output, label) for label in labels):
            return tuple(labels)
    return None


def _free_r_label(output: str) -> str:
    for label in FREE_R_LABELS:
        if _has_label(output, label):
            return label
    raise AutoRefineError(
        "Authoritative STARANISO reflections contain no recognized Free-R label; "
        "NASolve will not generate a new test set"
    )


def _resolution_limit(output: str) -> float | None:
    match = re.search(
        r"Resolution range:\s*([0-9]+(?:\.[0-9]+)?)\s+([0-9]+(?:\.[0-9]+)?)",
        output,
        re.I,
    )
    if match is None:
        return None
    return min(float(match.group(1)), float(match.group(2)))


def _anomalous_candidates(report: Mapping[str, object]) -> list[dict[str, object]]:
    postmr = report.get("postmr")
    anomalous = postmr.get("anomalous") if isinstance(postmr, Mapping) else None
    candidates = anomalous.get("candidates") if isinstance(anomalous, Mapping) else None
    if not isinstance(candidates, list):
        return []
    return [dict(candidate) for candidate in candidates if isinstance(candidate, Mapping)]


def build_reflection_plan(
    report: Mapping[str, object],
    observations: Path,
    mtz_dump_executable: Path,
    environment: Mapping[str, str] | None = None,
    phase_file: Path | None = None,
) -> ReflectionPlan:
    """Select observations without ever regenerating Free-R flags."""
    dump = _run_mtz_dump(observations, mtz_dump_executable, environment)
    free_r = _free_r_label(dump)
    candidates = _anomalous_candidates(report)
    anomalous_labels = _first_label_set(dump, (ANOMALOUS_F_LABELS,))
    mean_labels = _first_label_set(dump, MEAN_LABEL_SETS)
    if not candidates:
        if mean_labels is None:
            raise AutoRefineError("No supported mean observation labels were found")
        anomalous = False
        selected = mean_labels
        fallback = False
    elif anomalous_labels is not None:
        anomalous = True
        selected = anomalous_labels
        fallback = False
    else:
        if mean_labels is None:
            raise AutoRefineError(
                "PostMR found a heavy atom, but the STARANISO MTZ has neither a complete "
                "F(+)/F(-) quartet nor supported mean observations"
            )
        anomalous = False
        selected = mean_labels
        fallback = True

    phases: tuple[str, ...] = ()
    approved_autosol = False
    autosol = report.get("autosol")
    if isinstance(autosol, Mapping) and autosol.get("use_for_refinement") is True:
        approved_autosol = True
    if phase_file is not None:
        phase_dump = _run_mtz_dump(phase_file, mtz_dump_executable, environment)
        discovered = _first_label_set(phase_dump, HL_LABEL_SETS)
        if discovered is None:
            raise AutoRefineError(
                f"Approved phase file has no complete Hendrickson-Lattman quartet: {phase_file}"
            )
        phases = discovered
    return ReflectionPlan(
        observation_labels=selected,
        free_r_label=free_r,
        free_r_test_value=0,
        anomalous=anomalous,
        phase_labels=phases,
        phase_file=phase_file,
        anomalous_fallback=fallback,
        fallback_is_error=fallback and approved_autosol,
        resolution_limit=_resolution_limit(dump),
    )


def anomalous_selections(report: Mapping[str, object]) -> tuple[str, ...]:
    selections: list[str] = []
    for candidate in _anomalous_candidates(report):
        site = candidate.get("site")
        atom = candidate.get("atom_name")
        alternate = candidate.get("alternate")
        if not isinstance(site, str) or ":" not in site or not isinstance(atom, str):
            raise AutoRefineError("PostMR anomalous candidate is malformed")
        chain, residue = site.split(":", 1)
        if not chain or not residue or not atom:
            raise AutoRefineError("PostMR anomalous candidate has an empty selection field")
        selection = f"chain {chain} and resid {residue} and name {atom}"
        if isinstance(alternate, str) and alternate:
            selection += f" and altloc {alternate}"
        selections.append(selection)
    return tuple(selections)


def write_recipe_parameters(
    path: Path,
    *,
    selector_policy: ReflectionSelectorPolicy,
    observations: Path,
    reflection_plan: ReflectionPlan,
    macro_cycles: int,
    processor_count: int,
    anomalous_atom_selections: Sequence[str],
    real_space_sites: bool = True,
    adp_mode: str = "group",
    refine_occupancies: bool = True,
    anomalous_mode: str = "refine",
) -> tuple[str, ...]:
    if macro_cycles < 1:
        raise AutoRefineError("AutoRefine requires at least one macrocycle")
    if adp_mode not in {"group", "individual", "none"}:
        raise AutoRefineError("ADP mode must be group, individual, or none")
    if anomalous_mode not in {"refine", "off"}:
        raise AutoRefineError("Anomalous mode must be refine or off")
    strategies = ["individual_sites"]
    if real_space_sites:
        strategies.append("individual_sites_real_space")
    if adp_mode == "group":
        strategies.append("group_adp")
    elif adp_mode == "individual":
        strategies.append("individual_adp")
    if refine_occupancies:
        strategies.append("occupancies")
    if anomalous_atom_selections and anomalous_mode == "refine":
        strategies.append("group_anomalous")

    observations = observations.expanduser().resolve()
    reflection_arrays: list[tuple[Path, list[str]]] = [
        (
            observations,
            [
                ",".join(reflection_plan.observation_labels),
                reflection_plan.free_r_label,
            ],
        )
    ]
    if reflection_plan.phase_labels:
        if reflection_plan.phase_file is None:
            raise AutoRefineError("Selected experimental phases have no reflection file")
        phase_file = reflection_plan.phase_file.expanduser().resolve()
        phase_labels = ",".join(reflection_plan.phase_labels)
        if phase_file == observations:
            reflection_arrays[0][1].append(phase_labels)
        else:
            reflection_arrays.append((phase_file, [phase_labels]))

    lines: list[str] = []
    if selector_policy.use_data_manager:
        lines.append("data_manager {")
        for reflection_file, label_sets in reflection_arrays:
            escaped_file = str(reflection_file).replace("\\", "\\\\").replace('"', '\\"')
            lines.extend([
                "  miller_array {",
                f'    file = "{escaped_file}"',
            ])
            for labels in label_sets:
                escaped_labels = labels.replace("\\", "\\\\").replace('"', '\\"')
                lines.extend([
                    "    labels {",
                    f'      name = "{escaped_labels}"',
                    "    }",
                ])
            lines.append("  }")
        lines.extend(["}", ""])
    lines.extend([
        "refinement {",
        "  main {",
        f"    number_of_macro_cycles = {macro_cycles}",
        '    target = "auto"',
        "    scattering_table = n_gaussian",
        f"    nproc = {processor_count}",
        "  }",
        "  refine {",
        "    strategy = " + " ".join(f"*{strategy}" for strategy in strategies),
        "    sites {",
        "      individual = all",
        "    }",
    ])
    if adp_mode == "group":
        lines.extend([
            "    adp {",
            "      group_adp_refinement_mode = one_adp_group_per_residue",
            "      group = all",
            "    }",
        ])
    elif adp_mode == "individual":
        lines.extend([
            "    adp {",
            "      individual {",
            "        isotropic = all",
            "      }",
            "    }",
        ])
    for selection in anomalous_atom_selections if anomalous_mode == "refine" else ():
        escaped = selection.replace('"', '\\"')
        lines.extend([
            "    anomalous_scatterers {",
            "      group {",
            f'        selection = "{escaped}"',
            "        f_prime = 0",
            "        f_double_prime = 0",
            "        refine = *f_prime *f_double_prime",
            "      }",
            "    }",
        ])
    lines.extend([
        "  }",
        "  target_weights {",
        "    optimize_xyz_weight = True",
        "    optimize_adp_weight = True",
        "  }",
        "}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return tuple(strategies)


def build_refine_command(
    executable: Path,
    model: Path,
    observations: Path,
    restraints: Sequence[Path],
    parameters: Path,
    plan: ReflectionPlan,
) -> list[str]:
    command = [
        str(executable.expanduser().resolve()),
        str(observations),
        str(model),
        *(str(path) for path in restraints),
    ]
    if plan.phase_file is not None:
        command.append(str(plan.phase_file))
    command.extend([
        str(parameters),
        "--overwrite",
        f"xray_data.file_name={observations}",
        'xray_data.labels=' + ",".join(plan.observation_labels),
        f"xray_data.r_free_flags.file_name={observations}",
        f"xray_data.r_free_flags.label={plan.free_r_label}",
        f"xray_data.r_free_flags.test_flag_value={plan.free_r_test_value}",
        "xray_data.r_free_flags.generate=False",
        'main.target="auto"',
        "ordered_solvent=False",
        "simulated_annealing=False",
        "output.prefix=refined",
        "output.write_model_cif_file=True",
        "output.write_reflection_cif_file=True",
        "output.export_final_f_model=True",
    ])
    if plan.phase_labels:
        command.append(f"experimental_phases.file_name={plan.phase_file}")
        command.append("experimental_phases.labels=" + ",".join(plan.phase_labels))
    if plan.anomalous:
        command.append("xray_data.force_anomalous_flag_to_be_equal_to=True")
    else:
        command.append("xray_data.force_anomalous_flag_to_be_equal_to=False")
    return command


_R_PAIR = re.compile(
    r"r[_ -]?work\s*[=:]\s*([0-9]*\.?[0-9]+).*?"
    r"r[_ -]?free\s*[=:]\s*([0-9]*\.?[0-9]+)",
    re.I,
)
_BONDS_ANGLES = re.compile(
    r"bonds?\s*[=:]\s*([0-9]*\.?[0-9]+).*?"
    r"angles?\s*[=:]\s*([0-9]*\.?[0-9]+)",
    re.I,
)
_CLASHSCORE = re.compile(r"clashscore\s*[=:]\s*([0-9]*\.?[0-9]+)", re.I)
_ANOMALOUS_GROUP = re.compile(
    r'Anomalous scatterer group:\s*Selection:\s*"([^"]+)".*?'
    r"f_prime:\s*([-+0-9.eE]+)\s*f_double_prime:\s*([-+0-9.eE]+)",
    re.I | re.S,
)


def _final_anomalous_values(log_text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for match in _ANOMALOUS_GROUP.finditer(log_text):
        values[match.group(1)] = float(match.group(3))
    return values


def _henke_f_double_prime(
    refine_executable: Path,
    element: str,
    wavelength: float,
    environment: Mapping[str, str] | None,
) -> float | None:
    phenix_python = refine_executable.expanduser().resolve().parent / "phenix.python"
    if not phenix_python.is_file():
        return None
    script = (
        "from cctbx.eltbx import henke; "
        f"print(henke.table({element!r}).at_angstrom({wavelength!r}).fdp())"
    )
    try:
        completed = subprocess.run(
            [str(phenix_python), "-c", script],
            env=dict(environment) if environment is not None else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode:
        return None
    matches = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", completed.stdout)
    return float(matches[-1]) if matches else None


def anomalous_scatterer_diagnostics(
    log_text: str,
    model_path: Path | None,
    report: Mapping[str, object],
    refine_executable: Path,
    environment: Mapping[str, str] | None,
    resolution_limit: float | None,
) -> list[dict[str, object]]:
    """Compare refined anomalous strength with wavelength-calculated values."""
    if model_path is None or not model_path.is_file():
        return []
    autosol = report.get("autosol")
    wavelength_value = autosol.get("wavelength") if isinstance(autosol, Mapping) else None
    wavelength = float(wavelength_value) if isinstance(wavelength_value, (int, float)) else None
    refined_values = _final_anomalous_values(log_text)
    lines = model_path.read_text(encoding="utf-8", errors="replace").splitlines()
    results: list[dict[str, object]] = []
    for candidate in _anomalous_candidates(report):
        site = candidate.get("site")
        atom_name = candidate.get("atom_name")
        element_value = candidate.get("element")
        if not isinstance(site, str) or ":" not in site or not isinstance(atom_name, str):
            continue
        chain, residue = site.split(":", 1)
        selection = f"chain {chain} and resid {residue} and name {atom_name}"
        record = next(
            (
                line for line in lines
                if (identity := _record_identity(line)) is not None
                and identity[0] == chain and identity[1] == residue
                and line[12:16].strip() == atom_name
            ),
            None,
        )
        if record is None:
            continue
        try:
            occupancy = float(record[54:60])
            b_factor = float(record[60:66])
        except ValueError:
            continue
        element = (
            str(element_value).strip().upper()
            if isinstance(element_value, str) and element_value.strip()
            else record[76:78].strip().upper()
        )
        refined = refined_values.get(selection)
        calculated = (
            _henke_f_double_prime(refine_executable, element, wavelength, environment)
            if wavelength is not None and element else None
        )
        attenuation = (
            math.exp(-b_factor / (4.0 * resolution_limit * resolution_limit))
            if resolution_limit is not None and resolution_limit > 0 else None
        )
        results.append({
            "site": site,
            "atom_name": atom_name,
            "element": element,
            "wavelength": wavelength,
            "resolution_limit": resolution_limit,
            "refined_f_double_prime": refined,
            "calculated_f_double_prime": calculated,
            "model_occupancy": occupancy,
            "b_factor": b_factor,
            "calculated_f_double_prime_at_occupancy": (
                calculated * occupancy if calculated is not None else None
            ),
            "refined_f_double_prime_at_occupancy": (
                refined * occupancy if refined is not None else None
            ),
            "apparent_anomalous_occupancy": (
                refined * occupancy / calculated
                if refined is not None and calculated not in {None, 0.0} else None
            ),
            "b_attenuation_at_resolution_limit": attenuation,
            "calculated_contribution_at_resolution_limit": (
                calculated * occupancy * attenuation
                if calculated is not None and attenuation is not None else None
            ),
            "refined_contribution_at_resolution_limit": (
                refined * occupancy * attenuation
                if refined is not None and attenuation is not None else None
            ),
        })
    return results


def parse_refinement_statistics(log_text: str, model_text: str = "") -> dict[str, object]:
    pairs = [(float(a), float(b)) for a, b in _R_PAIR.findall(log_text)]
    # Logs repeat some summaries; preserve changes while collapsing immediate duplicates.
    series: list[dict[str, float | int]] = []
    for work, free in pairs:
        if series and series[-1]["r_work"] == work and series[-1]["r_free"] == free:
            continue
        series.append({"index": len(series), "r_work": work, "r_free": free})
    geometry = [(float(a), float(b)) for a, b in _BONDS_ANGLES.findall(log_text)]
    clash_values = [float(value) for value in _CLASHSCORE.findall(log_text + "\n" + model_text)]
    final = series[-1] if series else None
    initial = series[0] if series else None
    final_geometry = geometry[-1] if geometry else (None, None)
    diagnostics: list[str] = []
    for line in log_text.splitlines():
        stripped = line.strip()
        if re.match(r"^(?:WARNING\b|ERROR\b|Sorry\b|FATAL\b)", stripped, re.I):
            if stripped not in diagnostics:
                diagnostics.append(stripped)
    return {
        "initial_r_work": initial["r_work"] if initial else None,
        "initial_r_free": initial["r_free"] if initial else None,
        "r_work": final["r_work"] if final else None,
        "r_free": final["r_free"] if final else None,
        "r_free_minus_r_work": (
            round(float(final["r_free"]) - float(final["r_work"]), 6)
            if final else None
        ),
        "bond_rmsd": final_geometry[0],
        "angle_rmsd": final_geometry[1],
        "clashscore": clash_values[-1] if clash_values else None,
        "cycle_series": series,
        "diagnostics": diagnostics,
    }


def _write_metrics_tsv(path: Path, statistics: Mapping[str, object]) -> None:
    series = statistics.get("cycle_series")
    lines = ["index\tr_work\tr_free"]
    if isinstance(series, list):
        for item in series:
            if isinstance(item, Mapping):
                lines.append(f"{item.get('index')}\t{item.get('r_work')}\t{item.get('r_free')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _discover_output(round_directory: Path, pattern: str) -> Path | None:
    candidates = sorted(
        (path.resolve() for path in round_directory.glob(pattern) if path.is_file()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    return candidates[-1] if candidates else None


def _discover_filtered_output(
    round_directory: Path,
    pattern: str,
    *,
    include: Callable[[Path], bool],
) -> Path | None:
    candidates = sorted(
        (
            path.resolve()
            for path in round_directory.glob(pattern)
            if path.is_file() and include(path)
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    return candidates[-1] if candidates else None


def _record_identity(line: str) -> tuple[str, str, str, str] | None:
    if line[0:6].strip().upper() not in {"ATOM", "HETATM"} or len(line) < 27:
        return None
    return (
        line[21:22].strip(),
        line[22:26].strip(),
        line[26:27].strip(),
        line[17:20].strip(),
    )


def validate_refined_model(path: Path, report: Mapping[str, object]) -> dict[str, object]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise AutoRefineError(f"Could not inspect refined model {path}: {exc}") from exc
    records = [line for line in lines if _record_identity(line) is not None]
    if not records:
        raise AutoRefineError("Refined model contains no coordinate records")
    postmr = report.get("postmr")
    actions = postmr.get("mutation_actions") if isinstance(postmr, Mapping) else None
    missing: list[str] = []
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, Mapping):
                continue
            site, expected = action.get("site"), action.get("after")
            if not isinstance(site, str) or ":" not in site or not isinstance(expected, str):
                continue
            chain, residue = site.split(":", 1)
            if not any(
                (identity := _record_identity(line)) is not None
                and identity[0] == chain and identity[1] == residue and identity[3] == expected
                for line in records
            ):
                missing.append(f"{site} {expected}")
    for candidate in _anomalous_candidates(report):
        site, atom = candidate.get("site"), candidate.get("atom_name")
        if not isinstance(site, str) or ":" not in site or not isinstance(atom, str):
            continue
        chain, residue = site.split(":", 1)
        if not any(
            (identity := _record_identity(line)) is not None
            and identity[0] == chain and identity[1] == residue
            and line[12:16].strip() == atom
            for line in records
        ):
            missing.append(f"{site} atom {atom}")
    if missing:
        raise AutoRefineError(
            "Refined model is not checkpoint-compatible; missing " + ", ".join(missing)
        )
    return {"validated": True, "coordinate_record_count": len(records), "required_items": missing}


def _file_reference(path: Path, run: Path) -> dict[str, object]:
    return {
        **artifact_reference(path, run),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def _cached_file_referencer(
    run: Path,
) -> Callable[[Path], dict[str, object]]:
    """Build artifact references while hashing each resolved file only once."""
    cache: dict[Path, dict[str, object]] = {}

    def reference(path: Path) -> dict[str, object]:
        resolved = path.expanduser().resolve()
        if resolved not in cache:
            cache[resolved] = _file_reference(resolved, run)
        # Callers may annotate a reference; never expose the cached dictionary.
        return dict(cache[resolved])

    return reference


def _file_identity(path: Path) -> tuple[int, int, int, int, int]:
    status = path.stat()
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _verify_phase_file(
    path: Path,
    expected_sha256: object,
    *,
    mismatch_message: str,
) -> _VerifiedPhase:
    try:
        identity_before = _file_identity(path)
        actual_sha256 = file_sha256(path)
        identity_after = _file_identity(path)
    except OSError as exc:
        raise AutoRefineError(f"Could not verify approved phase data {path}: {exc}") from exc
    if identity_before != identity_after:
        raise AutoRefineError(
            f"Approved phase data changed while it was being verified: {path}"
        )
    if (
        isinstance(expected_sha256, str)
        and actual_sha256 != expected_sha256.casefold()
    ):
        raise AutoRefineError(mismatch_message)
    return _VerifiedPhase(
        path=path,
        sha256=actual_sha256,
        size=identity_after[2],
        identity=identity_after,
    )


def _require_unchanged_phase(phase: _VerifiedPhase) -> None:
    try:
        identity = _file_identity(phase.path)
    except OSError as exc:
        raise AutoRefineError(
            f"Approved phase data disappeared while Phenix was running: {phase.path}"
        ) from exc
    if identity != phase.identity:
        raise AutoRefineError(
            f"Approved phase data changed while Phenix was running: {phase.path}"
        )


def _effective_phase(
    report: Mapping[str, object], inherited: Mapping[str, object], run: Path
) -> _VerifiedPhase | None:
    inherited_phase = inherited.get("phases")
    if isinstance(inherited_phase, Path) and inherited_phase.is_file():
        metadata = inherited.get("phase_metadata")
        expected = metadata.get("sha256") if isinstance(metadata, Mapping) else None
        return _verify_phase_file(
            inherited_phase,
            expected,
            mismatch_message=(
                f"Checkpoint phase data changed after it was frozen: {inherited_phase}"
            ),
        )
    autosol = report.get("autosol")
    outputs = autosol.get("outputs") if isinstance(autosol, Mapping) else None
    value = outputs.get("refinement_data") if isinstance(outputs, Mapping) else None
    if (
        isinstance(autosol, Mapping)
        and autosol.get("use_for_refinement") is True
    ):
        resolved = resolve_artifact_path(value, run)
        if resolved is None:
            raise AutoRefineError(
                "Approved AutoSol phase data is missing or failed checksum validation"
            )
        expected = outputs.get("refinement_data_sha256")
        embedded_expected = value.get("sha256") if isinstance(value, Mapping) else None
        if expected is None:
            expected = embedded_expected
        elif (
            isinstance(expected, str)
            and isinstance(embedded_expected, str)
            and expected.casefold() != embedded_expected.casefold()
        ):
            raise AutoRefineError("Approved AutoSol phase checksums disagree")
        if expected is not None and (
            not isinstance(expected, str)
            or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None
        ):
            raise AutoRefineError("Approved AutoSol phase checksum is malformed")
        return _verify_phase_file(
            resolved,
            expected,
            mismatch_message=(
                "Approved AutoSol phase data failed checksum validation"
            ),
        )
    return None


def _update_run_report(run: Path, round_payload: Mapping[str, object]) -> None:
    report = _run_report(run)
    history = report.setdefault("autorefine_history", [])
    if not isinstance(history, list):
        raise AutoRefineError("Run report has malformed AutoRefine history")
    history.append(dict(round_payload))
    report["stage"] = "autorefine"
    report["status"] = round_payload["status"]
    report["message"] = round_payload["message"]
    report["updated_utc"] = round_payload["created_utc"]
    report["autorefine"] = dict(round_payload)
    _write_json(run / "report.json", report)


def execute_autorefine(
    run_directory: Path,
    refine_executable: Path,
    mtz_dump_executable: Path,
    *,
    phenix_version: str,
    environment: Mapping[str, str] | None = None,
    from_checkpoint: str | None = None,
    recipe: str = "AutoRefine/default",
    macro_cycles: int = 5,
    processor_count: int | None = None,
    use_experimental_phases: bool = True,
    real_space_sites: bool = True,
    adp_mode: str = "group",
    refine_occupancies: bool = True,
    anomalous_mode: str = "refine",
    auto_select_success: bool = True,
    progress: Callable[[str, Path], None] | None = None,
) -> AutoRefineResult:
    """Run one quiet refinement round and append an immutable checkpoint."""
    selector_policy = reflection_selector_policy(phenix_version)
    try:
        run, registry = initialize_registry(run_directory)
        parent = resolve_checkpoint(registry, from_checkpoint)
        if parent.get("usable") is not True:
            raise AutoRefineError(f"Checkpoint {parent.get('id')} is not reusable")
        inherited = (
            _inherited_paths_for_autorefine(parent, run)
            if use_experimental_phases
            else inherited_paths(parent, run)
        )
    except CheckpointError as exc:
        raise AutoRefineError(str(exc)) from exc
    report = _run_report(run)
    verified_phase = (
        _effective_phase(report, inherited, run)
        if use_experimental_phases
        else None
    )
    phase_file = verified_phase.path if verified_phase is not None else None
    observations = inherited["observations"]
    model = inherited["model"]
    restraints = inherited["restraints"]
    assert isinstance(observations, Path) and isinstance(model, Path)
    assert isinstance(restraints, list)
    validate_refined_model(model, report)
    plan = build_reflection_plan(
        report,
        observations,
        mtz_dump_executable,
        environment,
        phase_file,
    )
    selections = anomalous_selections(report) if plan.anomalous else ()
    checkpoint_id = next_checkpoint_id(registry, "refine")
    round_number = int(checkpoint_id.rsplit("-", 1)[1])
    round_directory = run / "AutoRefine" / f"round_{round_number:03d}"
    try:
        round_directory.mkdir(parents=True)
    except FileExistsError as exc:
        raise AutoRefineError(
            f"Refinement round already exists; refusing to overwrite {round_directory}"
        ) from exc
    parameters = round_directory / "autorefine.params"
    nproc = max(1, processor_count if processor_count is not None else (os.cpu_count() or 1))
    strategies = write_recipe_parameters(
        parameters,
        selector_policy=selector_policy,
        observations=observations,
        reflection_plan=plan,
        macro_cycles=macro_cycles,
        processor_count=nproc,
        anomalous_atom_selections=selections,
        real_space_sites=real_space_sites,
        adp_mode=adp_mode,
        refine_occupancies=refine_occupancies,
        anomalous_mode=anomalous_mode,
    )
    command = build_refine_command(
        refine_executable,
        model,
        observations,
        restraints,
        parameters,
        plan,
    )
    log_path = round_directory / "phenix.refine.log"
    preflight_log = round_directory / "phenix.refine.preflight.log"
    preflight_command = [command[0], "--dry_run", *command[1:]]
    if progress is not None:
        progress(checkpoint_id, log_path)
    preflight_failed = False
    try:
        with preflight_log.open("w", encoding="utf-8") as preflight_handle:
            preflight = subprocess.run(
                preflight_command,
                cwd=round_directory,
                env=dict(environment) if environment is not None else None,
                text=True,
                stdout=preflight_handle,
                stderr=subprocess.STDOUT,
                check=False,
            )
    except OSError as exc:
        preflight_log.write_text(
            f"NASolve could not launch phenix.refine preflight: {exc}\n", encoding="utf-8"
        )
        log_path.write_text(
            f"Refinement preflight failed; see {preflight_log}\n", encoding="utf-8"
        )
        completed_returncode = 127
        preflight_failed = True
    else:
        if preflight.returncode:
            log_path.write_text(
                f"Refinement preflight failed with status {preflight.returncode}; "
                f"see {preflight_log}\n",
                encoding="utf-8",
            )
            completed_returncode = preflight.returncode
            preflight_failed = True
        else:
            try:
                with log_path.open("w", encoding="utf-8") as log_handle:
                    completed = subprocess.run(
                        command,
                        cwd=round_directory,
                        env=dict(environment) if environment is not None else None,
                        text=True,
                        stdout=log_handle,
                        stderr=subprocess.STDOUT,
                        check=False,
                    )
            except OSError as exc:
                log_path.write_text(
                    f"NASolve could not launch phenix.refine: {exc}\n", encoding="utf-8"
                )
                completed_returncode = 127
            else:
                completed_returncode = completed.returncode
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    output_model = _discover_output(round_directory, "refined_*.pdb")
    model_cif = _discover_filtered_output(
        round_directory,
        "refined_*.cif",
        include=lambda path: "reflection" not in path.name.casefold(),
    )
    reflection_cif = _discover_filtered_output(
        round_directory,
        "refined_*.cif",
        include=lambda path: "reflection" in path.name.casefold(),
    )
    map_coefficients = _discover_output(round_directory, "refined_*map_coeffs.mtz")
    if map_coefficients is None and output_model is not None:
        legacy_map = output_model.with_suffix(".mtz")
        if legacy_map.is_file():
            map_coefficients = legacy_map.resolve()
    output_reflections = _discover_filtered_output(
        round_directory,
        "refined_*.mtz",
        include=lambda path: "map_coeffs" not in path.name.casefold(),
    )
    model_text = (
        output_model.read_text(encoding="utf-8", errors="replace")
        if output_model is not None else ""
    )
    statistics = parse_refinement_statistics(log_text, model_text)
    statistics["anomalous_scatterers"] = anomalous_scatterer_diagnostics(
        log_text,
        output_model,
        report,
        refine_executable,
        environment,
        plan.resolution_limit,
    )
    _write_metrics_tsv(round_directory / "metrics.tsv", statistics)
    compatibility: dict[str, object] = {"validated": False}
    compatibility_error: str | None = None
    if output_model is not None:
        try:
            compatibility = validate_refined_model(output_model, report)
        except AutoRefineError as exc:
            compatibility_error = str(exc)

    file_reference = _cached_file_referencer(run)
    model_reference = file_reference(output_model) if output_model is not None else None
    output_references = {
        "model_cif": file_reference(model_cif) if model_cif else None,
        "reflection_cif": file_reference(reflection_cif) if reflection_cif else None,
        "map_coefficients": (
            file_reference(map_coefficients) if map_coefficients else None
        ),
        "refinement_reflections": (
            file_reference(output_reflections) if output_reflections else None
        ),
        "metrics_tsv": file_reference(round_directory / "metrics.tsv"),
        "full_log": file_reference(log_path),
        "preflight_log": file_reference(preflight_log),
    }

    phase_error: str | None = None
    if verified_phase is not None:
        try:
            _require_unchanged_phase(verified_phase)
        except AutoRefineError as exc:
            phase_error = str(exc)

    r_work = statistics.get("r_work")
    r_free = statistics.get("r_free")
    numerical_success = (
        isinstance(r_work, float)
        and isinstance(r_free, float)
        and r_work < r_free
        and r_work < 0.30
    )
    if phase_error is not None:
        status = "AUTOREFINE_FAILED"
        message = phase_error
        checkpoint_status = "FAILED"
        usable = False
        exit_code = 2
    elif completed_returncode != 0 or output_model is None:
        status = "AUTOREFINE_FAILED"
        message = (
            f"Phenix refinement preflight failed with exit status {completed_returncode}"
            if preflight_failed
            else f"Phenix refinement failed with exit status {completed_returncode}"
        )
        checkpoint_status = "FAILED"
        usable = False
        exit_code = 2
    elif compatibility_error is not None:
        status = "AUTOREFINE_FAILED"
        message = compatibility_error
        checkpoint_status = "FAILED"
        usable = False
        exit_code = 2
    elif plan.fallback_is_error:
        status = "AUTOREFINE_ANOMALOUS_FALLBACK"
        message = (
            "Refinement completed with mean observations, but validated AutoSol phases "
            "were available and F(+)/F(-) amplitudes were missing; user action is required"
        )
        checkpoint_status = "REVIEW"
        usable = True
        exit_code = 2
    elif numerical_success:
        status = "AUTOREFINE_READY"
        message = "Numerical refinement criteria passed; inspect the model and maps"
        checkpoint_status = "SUCCESS"
        usable = True
        exit_code = 0
    else:
        status = "AUTOREFINE_REVIEW"
        message = "Refinement completed, but numerical acceptance criteria were not met"
        checkpoint_status = "REVIEW"
        usable = True
        exit_code = 0
    created = _now()
    phase_reference = (
        {
            **artifact_reference(verified_phase.path, run),
            "sha256": verified_phase.sha256,
            "size": verified_phase.size,
        }
        if verified_phase is not None and phase_error is None
        else None
    )
    if phase_reference is not None:
        phase_reference["labels"] = list(plan.phase_labels)
        phase_reference["source"] = "validated-autosol"
    checkpoint_payload = {
        "id": checkpoint_id,
        "parent": parent["id"],
        "kind": "refinement",
        "status": checkpoint_status,
        "usable": usable,
        "created_utc": created,
        "recipe": recipe,
        "phenix_version": selector_policy.phenix_version,
        "reflection_selector_mode": selector_policy.mode,
        "label": None,
        "model": model_reference,
        # Keep observations authoritative across every branch; output MTZ is evidence only.
        "observations": parent.get("observations"),
        "phases": phase_reference or parent.get("phases"),
        "restraints": parent.get("restraints", []),
        "metrics": {
            key: value
            for key, value in statistics.items()
            if key not in {"cycle_series", "diagnostics"}
        },
        "compatibility": {
            **compatibility,
            "error": compatibility_error,
        },
        "outputs": output_references,
    }
    selected = auto_select_success and status == "AUTOREFINE_READY"
    try:
        append_checkpoint(run, registry, checkpoint_payload, select=selected)
    except CheckpointError as exc:
        raise AutoRefineError(str(exc)) from exc
    round_payload = {
        "status": status,
        "message": message,
        "created_utc": created,
        "checkpoint": checkpoint_id,
        "parent_checkpoint": parent["id"],
        "selected_as_current": selected,
        "recipe": recipe,
        "phenix_version": selector_policy.phenix_version,
        "reflection_selector_mode": selector_policy.mode,
        "macro_cycles": macro_cycles,
        "processor_count": nproc,
        "command": command,
        "preflight_command": preflight_command,
        "parameters": str(parameters),
        "inputs": {
            "model": str(model),
            "authoritative_observations": str(observations),
            "observation_labels": list(plan.observation_labels),
            "free_r_label": plan.free_r_label,
            "free_r_test_value": plan.free_r_test_value,
            "phase_file": str(phase_file) if phase_file else None,
            "phase_labels": list(plan.phase_labels),
            "restraints": [str(path) for path in restraints],
        },
        "refinement": {
            "target": "automatic",
            "strategies": list(strategies),
            "anomalous": plan.anomalous,
            "anomalous_selections": list(selections),
            "anomalous_parameter_mode": anomalous_mode,
            "anomalous_fallback": plan.anomalous_fallback,
            "use_experimental_phases": use_experimental_phases,
            "real_space_sites": real_space_sites,
            "adp_mode": adp_mode,
            "refine_occupancies": refine_occupancies,
            "weights": {"optimize_xyz": True, "optimize_adp": True},
            "ordered_solvent": False,
            "simulated_annealing": False,
        },
        "statistics": statistics,
        "acceptance": {
            "r_work_less_than_r_free": (
                r_work < r_free if isinstance(r_work, float) and isinstance(r_free, float) else False
            ),
            "r_work_less_than_0_30": r_work < 0.30 if isinstance(r_work, float) else False,
            "numerical_success": numerical_success,
            "visual_inspection_required": True,
        },
        "outputs": {
            "model": str(output_model) if output_model else None,
            "model_cif": str(model_cif) if model_cif else None,
            "reflection_cif": str(reflection_cif) if reflection_cif else None,
            "map_coefficients": str(map_coefficients) if map_coefficients else None,
            "refinement_reflections": str(output_reflections) if output_reflections else None,
            "metrics_tsv": str(round_directory / "metrics.tsv"),
            "log": str(log_path),
            "preflight_log": str(preflight_log),
        },
        "compatibility": compatibility,
        "phenix_exit_code": completed_returncode,
        "preflight_failed": preflight_failed,
    }
    report_path = round_directory / "report.json"
    _write_json(report_path, round_payload)
    _update_run_report(run, round_payload)
    return AutoRefineResult(
        status=status,
        message=message,
        exit_code=exit_code,
        run_directory=run,
        round_directory=round_directory,
        checkpoint_id=checkpoint_id,
        parent_checkpoint=str(parent["id"]),
        report_path=report_path,
        log_path=log_path,
        model_path=output_model,
        model_cif=model_cif,
        reflection_cif=reflection_cif,
        map_coefficients=map_coefficients,
        statistics=statistics,
        selected_as_current=selected,
    )


__all__ = [
    "AutoRefineError",
    "AutoRefineResult",
    "DATA_MANAGER_FILE_SCOPED",
    "LEGACY_EXPLICIT",
    "ReflectionPlan",
    "ReflectionSelectorPolicy",
    "anomalous_selections",
    "anomalous_scatterer_diagnostics",
    "build_refine_command",
    "build_reflection_plan",
    "execute_autorefine",
    "parse_refinement_statistics",
    "reflection_selector_policy",
    "validate_refined_model",
    "write_recipe_parameters",
]
