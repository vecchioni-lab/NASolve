"""Frozen, opt-in campaign autonomy. A working choice is never user approval.

Schema-1 recipes keep the original guarded behavior byte-for-byte. Schema 2
adds a small typed workflow table; it supplies neither commands nor new chemistry.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping


WORKFLOW_KEYS = frozenset({"mode", "run_doctor", "select_recommendation"})
GUARDED = {"mode": "guarded", "run_doctor": False, "select_recommendation": False}
INSPECTION_WARNING = (
    "PROVISIONAL FULL-AUTO RESULT: inspect the maps, model and decision history "
    "before accepting. Automatic selection is not user approval."
)


def workflow_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve a versioned recipe; reject accidental or unversioned opt-ins."""
    schema = policy.get("schema_version", 1)
    if type(schema) is not int or schema not in {1, 2}:
        raise ValueError("Unsupported workflow recipe schema_version")
    if schema == 1:
        if "workflow" in policy:
            raise ValueError("workflow requires preset schema_version = 2")
        return dict(GUARDED)
    supplied = policy.get("workflow", {})
    if not isinstance(supplied, dict) or set(supplied) - WORKFLOW_KEYS:
        raise ValueError("workflow must contain only mode, run_doctor and select_recommendation")
    mode = supplied.get("mode", "guarded")
    if type(mode) is not str or mode not in {"guarded", "full-auto"}:
        raise ValueError("workflow.mode must be guarded or full-auto")
    doctor = supplied.get("run_doctor", mode == "full-auto")
    select = supplied.get("select_recommendation", mode == "full-auto" and doctor is True)
    if type(doctor) is not bool or type(select) is not bool:
        raise ValueError("workflow run_doctor and select_recommendation must be bool")
    if select and (mode != "full-auto" or not doctor):
        raise ValueError("Automatic recommendation selection requires full-auto with run_doctor")
    return {"mode": mode, "run_doctor": doctor, "select_recommendation": select}


def default_endpoint(policy: Mapping[str, Any]) -> str:
    return "refine-doctor" if workflow_policy(policy)["run_doctor"] else "autorefine"


def continuation_warning(policy: Mapping[str, Any], stage: str,
                         receipt: Mapping[str, Any]) -> str | None:
    """Authorize a bounded trial without relabelling the upstream evidence.

    MR_FAILED/no model is never promoted. The existing 7 <= TFZ < 8 REVIEW band
    is trialled only under full-auto. AutoSol rejection can fall back to the
    intact PostMR model, but never import rejected/unavailable phase files.
    """
    if workflow_policy(policy)["mode"] != "full-auto":
        return None
    status = receipt.get("status")
    if stage == "phaser" and status == "MR_REVIEW":
        tfz = receipt.get("tfz")
        if (type(tfz) in {int, float} and math.isfinite(tfz) and 7 <= tfz < 8):
            return (
                f"MR REVIEW retained (TFZ {tfz:.2f}); frozen full-auto recipe "
                "authorizes a downstream trial, not acceptance of this MR solution."
            )
    if (stage == "autosol" and status in {"AUTOSOL_WARNING", "AUTOSOL_REVIEW"}
            and (policy.get("autosol") or {}).get("on_unaccepted") == "continue-without-phases"):
        return (
            "AutoSol phases were not accepted. Full-auto continues from PostMR "
            "without rejected phases; inspect anomalous evidence and refinement."
        )
    return None


def select_provisional_recommendation(run: Path, result: Any,
                                      policy: Mapping[str, Any]) -> dict[str, Any] | None:
    """Select only the bounded Doctor's numerically successful recommendation.

    Core Doctor still preserves current. The campaign performs a separate,
    explicitly authorized selection before freezing its stage receipt. No node
    is relabelled USER_APPROVED, and resuming does not repeat this decision.
    """
    if not workflow_policy(policy)["select_recommendation"]:
        return None
    if result.status != "REFINE_DOCTOR_RECOMMEND" or not result.recommended_checkpoint:
        return None
    from .checkpoints import (
        initialize_registry, resolve_checkpoint, inherited_paths, select_checkpoint,
    )
    _, registry = initialize_registry(run)
    chosen = resolve_checkpoint(registry, result.recommended_checkpoint)
    if chosen.get("usable") is not True or chosen.get("status") != "SUCCESS":
        raise ValueError("Doctor recommendation is not a usable numerical SUCCESS checkpoint")
    inherited_paths(chosen, run)  # Verify model, observations, phases and restraints.
    previous = registry["current"]
    selected = select_checkpoint(run, result.recommended_checkpoint)
    return {
        "schema_version": 1,
        "kind": "recipe-authorized-provisional-selection",
        "previous_current": previous,
        "selected_checkpoint": selected.checkpoint_id,
        "source_checkpoint": result.source_checkpoint,
        "selection_rule": "bounded-doctor-recommendation-not-global-rfree-minimum",
        "reason": result.recommendation,
        "user_approved": False,
        "inspection_required": True,
        "core_doctor_preserved_current": result.current_checkpoint_preserved,
    }


def record_runtime_policy(run: Path, policy: Mapping[str, Any], stage: str,
                          outcome: Mapping[str, Any]) -> dict[str, Any] | None:
    """Persist decision provenance during the owning stage, before its receipt."""
    workflow = workflow_policy(policy)
    if workflow["mode"] != "full-auto":
        return None
    path = run / "report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    old = report.get("campaign_automation", {})
    if not isinstance(old, dict):
        raise ValueError("Malformed campaign automation provenance")
    if old and old.get("workflow") != workflow:
        raise ValueError("Frozen campaign workflow changed inside an existing run")
    warnings = list(old.get("warnings", []))
    warning = continuation_warning(policy, stage, outcome)
    if warning and warning not in warnings:
        warnings.append(warning)
    for value in outcome.get("scientific_warnings", []):
        if value not in warnings:
            warnings.append(value)
    record = {
        **old, "schema_version": 1,
        "recipe": {"id": policy.get("id"), "version": policy.get("version")},
        "workflow": workflow, "warnings": warnings,
        "inspection_required": True, "user_approved": False,
    }
    if outcome.get("provisional_selection") is not None:
        record["provisional_selection"] = outcome["provisional_selection"]
    if outcome.get("checkpoint"):
        record["presented_checkpoint"] = outcome["checkpoint"]
    report["campaign_automation"] = record
    temporary = path.with_name("campaign-automation.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    temporary.replace(path)
    return record
