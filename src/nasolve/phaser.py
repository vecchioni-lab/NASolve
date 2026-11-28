"""Phenix Phaser execution and TFZ gating for a frozen AutoMR run."""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .model_assessment import file_sha256
from .run_context import artifact_reference, resolve_artifact_path


class PhaserExecutionError(RuntimeError):
    """Raised when a frozen run cannot be prepared for Phaser."""


@dataclass(frozen=True)
class PhaserExecutionResult:
    status: str
    message: str
    run_directory: Path
    phaser_directory: Path
    report_path: Path
    log_path: Path
    parameter_path: Path
    tfz: float | None
    llg: float | None
    solution_pdb: Path | None
    solution_mtz: Path | None

    @property
    def exit_code(self) -> int:
        if self.status == "MR_SUCCESS":
            return 0
        if self.status == "MR_REVIEW":
            return 3
        return 4


_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"
_TFZ_RE = re.compile(rf"\bTFZ\s*={{0,2}}\s*({_NUMBER})", re.I)
_LLG_RE = re.compile(rf"\bLLG\s*={{0,2}}\s*({_NUMBER})", re.I)
_ANNOTATION_FIELD_RE = re.compile(r"\b(TFZ|LLG)(?:\s*(={1,2})\s*|\s+)(\S+)", re.I)


def _annotation_scores(line: str) -> tuple[float | None, float | None, str | None]:
    """Read the final scores in one solution's chronological annotation.

    Phaser distinguishes orientation-dependent TFZ= from refined-orientation
    TFZ== (TFZ-equivalent); repeated LLGs describe successive refinement stages.
    https://www.phenix-online.org/documentation/reference/phaser.html#annotation
    """
    fields = list(_ANNOTATION_FIELD_RE.finditer(line))
    translations = [m for m in fields if m.group(1).upper() == "TFZ"]
    equivalents = [m for m in translations if m.group(2) == "=="]
    selected = (equivalents or translations)[-1:]
    likelihoods = [m for m in fields if m.group(1).upper() == "LLG"]

    def number(match):
        if match is None:
            return None
        token = match.group(3)
        if re.fullmatch(_NUMBER, token) is None:
            return None
        value = float(token)
        return value if math.isfinite(value) else None

    tfz = number(selected[0] if selected else None)
    llg = number(likelihoods[-1] if likelihoods else None)
    kind = ("tfz-equivalent" if equivalents else "translation-search-tfz") if selected else None
    return tfz, llg, kind


def parse_selected_solution_scores(pdb_text: str) -> dict[str, object]:
    """Read scores only from the selected PDB's own Phaser REMARK annotation.

    An invalid/conflicting annotation is deliberately distinct from an absent
    one: callers must not replace it with a more favourable unrelated log score.
    """
    lines = [line.strip() for line in pdb_text.splitlines()
             if line.startswith("REMARK") and re.search(r"\bTFZ\b", line, re.I)]
    if not lines:
        return {"status": "ABSENT", "tfz": None, "llg": None, "score_kind": None,
                "raw_annotations": []}
    unique = list(dict.fromkeys(lines))
    if len(unique) != 1:
        return {"status": "AMBIGUOUS", "tfz": None, "llg": None, "score_kind": None,
                "raw_annotations": unique}
    tfz, llg, kind = _annotation_scores(unique[0])
    return {"status": "PARSED" if tfz is not None else "INVALID",
            "tfz": tfz, "llg": llg, "score_kind": kind, "raw_annotations": unique}


def _phil_string(value: str | Path) -> str:
    """Return a double-quoted PHIL string with conservative escaping."""
    return json.dumps(str(value))


def _load_report(report_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PhaserExecutionError(f"Could not read frozen AutoMR report {report_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PhaserExecutionError(f"Frozen AutoMR report is not a JSON object: {report_path}")
    if payload.get("workflow") != "automr" or payload.get("stage") != "preflight":
        raise PhaserExecutionError("Phaser requires a frozen AutoMR preflight report")
    return payload


def _integer_field(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PhaserExecutionError(f"Frozen report has no valid {label}")
    return value


def build_phaser_eff(report: Mapping[str, object], phaser_directory: Path) -> str:
    """Build one explicit ensemble, one NA composition, and one search request."""
    inputs = report.get("inputs")
    assessment = report.get("model_assessment")
    symmetry = report.get("symmetry")
    if not isinstance(inputs, Mapping) or not isinstance(assessment, Mapping):
        raise PhaserExecutionError("Frozen report is missing its input or model assessment")

    run = phaser_directory.parent
    reflections = resolve_artifact_path(inputs.get("reflections"), run)
    copied_model = resolve_artifact_path(assessment.get("copied_model"), run)
    if reflections is None:
        raise PhaserExecutionError("Frozen report reflections file is missing")
    if copied_model is None:
        raise PhaserExecutionError("Frozen, checksum-verified MR model is missing")
    model_sha256 = assessment.get("sha256")
    if not isinstance(model_sha256, str) or file_sha256(copied_model) != model_sha256:
        raise PhaserExecutionError("Frozen MR model does not match its recorded checksum")
    reflections_sha256 = inputs.get("reflections_sha256")
    if reflections_sha256 is not None and not isinstance(reflections_sha256, str):
        raise PhaserExecutionError("Frozen reflections checksum is malformed")
    if (
        isinstance(reflections_sha256, str)
        and file_sha256(reflections) != reflections_sha256
    ):
        raise PhaserExecutionError(
            "Frozen reflections do not match their recorded checksum"
        )

    residue_count = _integer_field(
        assessment.get("polymer_residue_count"), "polymer residue count"
    )
    copies = 1
    if isinstance(symmetry, Mapping) and "mr_copies" in symmetry:
        copies = _integer_field(symmetry.get("mr_copies"), "MR copy count")

    # Do not set ``phaser.model`` as well as ``phaser.ensemble``.  The shortcut
    # can create an additional anonymous ensemble in some Phenix versions.
    return "\n".join([
        "phaser {",
        "  mode = MR_AUTO",
        f"  hklin = {_phil_string(str(reflections))}",
        "  chain_type = dna",
        "  composition {",
        "    chain {",
        "      chain_type = na",
        "      comp_type = nres",
        f"      nres = {residue_count}",
        f"      num = {copies}",
        "    }",
        "  }",
        "  ensemble {",
        "    model_id = nasolve_model",
        "    use_hetatm = True",
        "    coordinates {",
        f"      pdb = {_phil_string(str(copied_model))}",
        "      rmsd = 1.0",
        "    }",
        "  }",
        "  search {",
        "    ensembles = nasolve_model",
        f"    copies = {copies}",
        "  }",
        f"  output_dir = {_phil_string(phaser_directory.resolve())}",
        "  keywords {",
        "    general {",
        '      root = "PHASER"',
        "    }",
        "  }",
        "}",
        "",
    ])


def parse_best_tfz(log_text: str) -> tuple[float | None, float | None]:
    """Return the highest per-annotation final TFZ for legacy log diagnostics.

    This public tuple API is retained; execution gates instead use the selected
    output's annotation, since the highest-scoring log solution may not be the
    PDB selected by Phaser's output ranking.
    """
    solution_lines = [
        line for line in log_text.splitlines()
        if re.search(r"\bSOLU\s+SET\b", line, re.I) and _TFZ_RE.search(line)
    ]
    candidate_lines = solution_lines or [
        line for line in log_text.splitlines() if _TFZ_RE.search(line)
    ]
    scored: list[tuple[float, float | None]] = []
    for line in candidate_lines:
        tfz, llg, _kind = _annotation_scores(line)
        if tfz is not None:
            scored.append((tfz, llg))
    return max(scored, key=lambda item: item[0]) if scored else (None, None)


def _solution_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"\.(\d+)\.(?:pdb|mtz)$", path.name, re.I)
    return (int(match.group(1)) if match else 10**9, path.name.casefold())


def _find_solution(phaser_directory: Path, suffix: str) -> Path | None:
    candidates = sorted(
        (
            path for path in phaser_directory.glob(f"PHASER*{suffix}")
            if path.is_file() and not path.name.startswith("mr_solution")
        ),
        key=_solution_sort_key,
    )
    return candidates[0] if candidates else None


def _selected_scores(raw_pdb: Path | None, output: str, directory: Path,
                     run: Path) -> dict[str, object]:
    """Bind the gate score to one selected artifact, with a narrow legacy fallback."""
    evidence: dict[str, object] = {
        "schema_version": 1, "selection_rule": "selected-output-final-annotation",
        "tfz": None, "llg": None, "score_kind": None, "source": None,
        "raw_annotations": [], "status": "NO_SELECTED_MODEL",
    }
    if raw_pdb is None:
        return evidence
    parsed = parse_selected_solution_scores(raw_pdb.read_text(encoding="utf-8", errors="replace"))
    evidence.update(parsed)
    evidence["source"] = {**artifact_reference(raw_pdb, run), "sha256": file_sha256(raw_pdb)}
    if parsed["status"] != "ABSENT":
        evidence["method"] = "selected-pdb-remark"
        return evidence
    # Older simple output fixtures/builds may omit the PDB score annotation.
    # Only a single output pair and one distinct SOLU SET annotation can bind
    # such a log score to this model. Never fall back to arbitrary TFZ text.
    pdbs = list(directory.glob("PHASER*.pdb"))
    mtzs = list(directory.glob("PHASER*.mtz"))
    lines = list(dict.fromkeys(
        line.strip() for line in output.splitlines()
        if re.search(r"\bSOLU\s+SET\b", line, re.I) and re.search(r"\bTFZ\b", line, re.I)
    ))
    if len(pdbs) != 1 or len(mtzs) != 1 or mtzs[0] != raw_pdb.with_suffix(".mtz") or len(lines) != 1:
        evidence.update(status="UNASSOCIATED_LOG", method="no-unambiguous-score-source")
        return evidence
    tfz, llg, kind = _annotation_scores(lines[0])
    evidence.update(status="PARSED" if tfz is not None else "INVALID",
                    tfz=tfz, llg=llg, score_kind=kind, raw_annotations=lines,
                    method="single-output-single-annotation-log-compatibility",
                    source={**artifact_reference(directory / "phaser.log", run),
                            "sha256": file_sha256(directory / "phaser.log")})
    return evidence


def _write_report(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_run_log(path: Path, lines: list[str]) -> None:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError:
        existing = ""
    existing = existing.replace("Phaser executed: no", "Phaser executed: yes", 1)
    existing = existing.replace(
        "Next layer: use this frozen run input to prepare and execute Phenix Phaser.",
        "Phaser execution completed; details follow.",
        1,
    )
    if existing and not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + "\n".join(lines) + "\n", encoding="utf-8")


def execute_phaser(
    report_path: Path,
    phaser_executable: Path,
    environment: Mapping[str, str] | None = None,
    phenix_version: str = "unknown",
) -> PhaserExecutionResult:
    """Run Phaser once, preserve its raw output, and apply the AutoMR TFZ gate."""
    frozen_report_path = report_path.expanduser().resolve()
    report = _load_report(frozen_report_path)
    run_directory = frozen_report_path.parent
    phaser_directory = run_directory / "Phaser"
    try:
        phaser_directory.mkdir()
    except FileExistsError as exc:
        raise PhaserExecutionError(
            f"Phaser directory already exists; refusing to overwrite {phaser_directory}"
        ) from exc

    parameter_path = phaser_directory / "phaser.eff"
    log_path = phaser_directory / "phaser.log"
    parameter_path.write_text(build_phaser_eff(report, phaser_directory), encoding="utf-8")
    executable = phaser_executable.expanduser().resolve()
    command = [str(executable), str(parameter_path)]
    try:
        completed = subprocess.run(
            command,
            cwd=phaser_directory,
            env=dict(environment) if environment is not None else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        output = completed.stdout
        return_code = completed.returncode
    except OSError as exc:
        output = f"NASolve could not launch Phaser: {exc}\n"
        return_code = 127
    log_path.write_text(output, encoding="utf-8")

    raw_pdb = _find_solution(phaser_directory, ".pdb")
    # Phaser ranks numbered output models. Require that exact model's MTZ;
    # independently sorting extensions could silently pair .1.pdb with .2.mtz.
    paired_mtz = raw_pdb.with_suffix(".mtz") if raw_pdb else None
    raw_mtz = paired_mtz if paired_mtz is not None and paired_mtz.is_file() else None
    score_evidence = _selected_scores(raw_pdb, output, phaser_directory, run_directory)
    tfz, llg = score_evidence["tfz"], score_evidence["llg"]
    solution_pdb: Path | None = None
    solution_mtz: Path | None = None
    if raw_pdb:
        solution_pdb = phaser_directory / "mr_solution.pdb"
        shutil.copyfile(raw_pdb, solution_pdb)
    if raw_mtz:
        solution_mtz = phaser_directory / "mr_solution.mtz"
        shutil.copyfile(raw_mtz, solution_mtz)

    outputs_complete = solution_pdb is not None and solution_mtz is not None
    if return_code != 0:
        status = "MR_FAILED"
        message = f"Phaser exited with status {return_code}; inspect phaser.log"
    elif not outputs_complete and (raw_pdb is not None or _TFZ_RE.search(output)):
        status = "MR_FAILED"
        message = "Phaser did not produce both PDB and MTZ outputs for the same selected solution"
    elif tfz is None:
        status = "MR_FAILED"
        message = "Phaser did not report a TFZ associated unambiguously with the selected output; inspect score_evidence and phaser.log"
    elif tfz < 7.0:
        status = "MR_FAILED"
        message = f"Best TFZ {tfz:.2f} is below the 7.0 acceptance floor"
    elif not outputs_complete:
        status = "MR_FAILED"
        message = "Phaser reported a candidate solution but did not produce both PDB and MTZ outputs"
    elif tfz < 8.0:
        status = "MR_REVIEW"
        message = f"Best TFZ {tfz:.2f} is a red flag and requires user review"
    else:
        status = "MR_SUCCESS"
        message = f"Best TFZ {tfz:.2f} passes the 8.0 AutoMR threshold"

    previous_status = report.get("status")
    previous_message = report.get("message")
    report["stage"] = "phaser"
    report["status"] = status
    report["message"] = message
    report["updated_utc"] = datetime.now(timezone.utc).isoformat()
    report["preflight"] = {"status": previous_status, "message": previous_message}
    report["execution"] = {
        "phaser_ran": True,
        "phaser": {
            "executable": str(executable),
            "phenix_version": phenix_version,
            "command": command,
            "return_code": return_code,
            "parameters": str(parameter_path),
            "log": str(log_path),
            "ensemble_count": 1,
            "ensemble_id": "nasolve_model",
            "preserve_heteroatoms": True,
            "model_rmsd": 1.0,
            "composition_nres": report["model_assessment"]["polymer_residue_count"],
            "search_copies": (
                report["symmetry"].get("mr_copies", 1)
                if isinstance(report.get("symmetry"), Mapping) else 1
            ),
            "best_tfz": tfz,
            "best_llg": llg,
            "score_evidence": score_evidence,
            "raw_solution_pdb": str(raw_pdb) if raw_pdb else None,
            "raw_solution_mtz": str(raw_mtz) if raw_mtz else None,
            "solution_pdb": str(solution_pdb) if solution_pdb else None,
            "solution_mtz": str(solution_mtz) if solution_mtz else None,
            "solution_pdb_sha256": file_sha256(solution_pdb) if solution_pdb else None,
            "solution_mtz_sha256": file_sha256(solution_mtz) if solution_mtz else None,
        },
    }
    _write_report(frozen_report_path, report)
    _append_run_log(
        run_directory / "automr.log",
        [
            "Phaser execution",
            f"Status: {status}",
            f"Phenix version: {phenix_version}",
            "Ensembles: 1 (nasolve_model)",
            "Preserve heteroatoms: True",
            "Model RMSD: 1.0 A",
            f"Composition residues: {report['model_assessment']['polymer_residue_count']}",
            f"Search copies: {report['execution']['phaser']['search_copies']}",
            f"Best TFZ: {tfz if tfz is not None else 'not reported'}",
            f"Best LLG: {llg if llg is not None else 'not reported'}",
            f"Result: {message}",
            f"Phaser log: {log_path}",
            "",
        ],
    )
    return PhaserExecutionResult(
        status=status,
        message=message,
        run_directory=run_directory,
        phaser_directory=phaser_directory,
        report_path=frozen_report_path,
        log_path=log_path,
        parameter_path=parameter_path,
        tfz=tfz,
        llg=llg,
        solution_pdb=solution_pdb,
        solution_mtz=solution_mtz,
    )


__all__ = [
    "PhaserExecutionError",
    "PhaserExecutionResult",
    "build_phaser_eff",
    "execute_phaser",
    "parse_best_tfz",
    "parse_selected_solution_scores",
]
