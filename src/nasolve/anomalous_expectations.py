"""Small explicit iodine diagnostics; never invent anomalous data or phases."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

# These atom names are the existing curated construction targets, not names
# guessed from a dataset title. Keep additional exceptions explicit.
IODINE_COMPONENTS = {"5IU": "I5", "C38": "I"}


def audit_iodine_targets(model: Path, candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    residues: dict[tuple[str, str], list[str]] = {}
    for line in model.read_text(encoding="utf-8").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 27:
            continue
        code = line[17:20].strip()
        if code in IODINE_COMPONENTS:
            site = f"{line[21].strip() or '_'}:{line[22:27].strip()}"
            residues.setdefault((site, code), []).append(line)
    expected = []
    warnings = []
    detected = {(v.get("site"), v.get("atom_name"), v.get("element")) for v in candidates}
    for (site, code), lines in sorted(residues.items()):
        name = IODINE_COMPONENTS[code]
        atoms = [v for v in lines if v[12:16].strip() == name]
        # The ordinary scanner permits atom-name fallback if the element column
        # is blank; this diagnostic uses the same rule for these iodine names.
        present = bool(atoms) and all(
            ((v[76:78].strip().upper() if len(v) >= 78 else "") or "I") == "I"
            for v in atoms
        )
        registered = (site, name, "I") in detected
        status = ("CANDIDATE_READY" if present and registered else
                  "EXPECTED_IODINE_MISSING_OR_WRONG_ELEMENT" if not present else
                  "IODINE_PRESENT_NOT_CLASSIFIED_AS_ANOMALOUS_CANDIDATE")
        expected.append({"site": site, "residue": code, "atom_name": name,
                         "element": "I", "atom_present": present,
                         "candidate_registered": registered, "status": status})
        if status != "CANDIDATE_READY":
            warnings.append(f"{code} {site} requires iodine {name}: {status}; inspect before approval.")
    return {"schema_version": 1, "expected_atoms": expected, "warnings": warnings,
            "phase_or_anomalous_data_availability": "NOT_ESTABLISHED_BY_ATOM_PRESENCE"}


def iodine_refinement_audit(run_report: Mapping[str, Any],
                            refinement: Mapping[str, Any]) -> dict[str, Any]:
    """Distinguish atom detection, experimental phasing and anomalous refinement."""
    postmr = run_report.get("postmr") or {}
    anomalous = postmr.get("anomalous") or {}
    expected = (anomalous.get("iodine_expectations") or {}).get("expected_atoms", [])
    iodine = [v for v in anomalous.get("candidates", []) if v.get("element") == "I"]
    warnings = list((anomalous.get("iodine_expectations") or {}).get("warnings", []))
    enabled = (refinement.get("refinement") or {}).get("anomalous") is True
    autosol = run_report.get("autosol") or {}
    # A default permission is not evidence of supplied experimental phases.
    # Use this exact refinement report, never a parent/AutoSol availability flag.
    # This is a reporting check, not a new phase-file reader or execution gate.
    inputs = refinement.get("inputs") or {}
    phase_requested = (refinement.get("refinement") or {}).get("use_experimental_phases") is True
    phase_file = inputs.get("phase_file")
    raw_phase_labels = inputs.get("phase_labels")
    phase_labels = list(raw_phase_labels) if isinstance(raw_phase_labels, (list, tuple)) else []
    phase_inputs_present = (
        isinstance(phase_file, str) and bool(phase_file.strip())
        and len(phase_labels) == 4
        and all(isinstance(label, str) and bool(label.strip()) for label in phase_labels)
        and len({label.strip() for label in phase_labels}) == 4
    )
    if (expected or iodine) and not enabled:
        warnings.append(
            "Iodine was expected or detected, but this refinement did not use anomalous "
            "observations/scattering. Inspect the data labels and anomalous stage report; "
            "do not describe this as an anomalous refinement."
        )
    return {"schema_version": 1, "expected_atoms": expected, "iodine_candidates": iodine,
            "anomalous_refinement": enabled,
            "autosol_status": autosol.get("status", "NOT_RUN"),
            "experimental_phases_requested": phase_requested,
            "experimental_phase_inputs_present": phase_inputs_present,
            "experimental_phases_used": phase_requested and phase_inputs_present,
            "phase_file": phase_file,
            "phase_labels": phase_labels,
            "phase_usage_basis": "reported-refinement-inputs-v1",
            "observation_labels": inputs.get("observation_labels"),
            "warnings": warnings}
