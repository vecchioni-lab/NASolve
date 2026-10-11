"""Explicit, source-preserving numerical dictionary candidates.

This module never adopts a candidate or retries ReadySet.  Chemistry comes
from the supplied dictionary, and the naming/starting geometry comes only
from that dictionary's complete ideal coordinates, never a fitted model.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import re
import signal
import subprocess
from tempfile import mkdtemp
import time
from typing import Mapping

from .cif_doctor import assess_dictionaries, compare_dictionaries, _number
from .ligand_profiles import _blocks

POLICY_ID = "cif-independent-elbow-candidate-v1"
ELBOW_DOCUMENTATION = "https://phenix-online.org/documentation/reference/elbow.html"
_CHEMICAL_FIELDS = {
    "atom_elements", "declared_charge_fields", "atom_stereo_declarations",
    "bond_orders", "bond_aromatic_declarations", "bond_stereo_declarations",
    "hydrogen_attachments", "signed_chirality",
}


def _sha(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _selected(assessment: dict, code: str) -> list[dict]:
    return [row for row in assessment["components"] if row["component_id"] == code]


def _numerical_issues(assessment: dict, code: str, role: str) -> list[dict]:
    issues = []
    for component in _selected(assessment, code):
        restraints = component["inventory"]["numerical_restraints"]
        for finding in component["findings"]:
            if finding["rule_id"] not in {"NUM-01", "TOR-01", "PLANE-01"}:
                continue
            if finding["status"] == "PASS":
                continue
            measurements = dict(finding["measurements"])
            category = measurements.get("category")
            index = measurements.get("row")
            if category in restraints and isinstance(index, int) and 0 <= index < len(restraints[category]):
                row = restraints[category][index]
                measurements["atoms"] = [row[key] for key in sorted(row) if key.startswith("atom_id")]
            issues.append({"role": role, "component_id": code, **finding,
                           "measurements": measurements})
    return issues


def _explicit_formal_charges(component: dict) -> dict[str, float]:
    result = {}
    for atom in component["inventory"]["atoms"]:
        fields = atom["declared_charge_fields"]
        # Partial charges remain a different declaration. Missing stays unknown.
        token = fields.get("pdbx_formal_charge", fields.get("charge"))
        try:
            number = _number(token)
        except (TypeError, ValueError, OverflowError):
            continue
        if number is not None:
            result[atom["atom_id"]] = number
    return result


def _explicit_atom_stereo(component: dict) -> dict[str, set[str]]:
    return {atom["atom_id"]: {value.upper() for value in atom["stereo_declarations"].values()
                             if value not in {"", ".", "?"}}
            for atom in component["inventory"]["atoms"]}


def inspect_component_generation(source: Path, generated: Path | None, code: str) -> dict:
    """Inventory general numerical defects and same-ID chemical differences.

    Full source/candidate assessments are retained; the requested component
    determines rejection. Other components in a ReadySet bundle remain visible.
    A numerically valid candidate still requires chemical and native review.
    """
    source = Path(source)
    before = assess_dictionaries([source], stage="source")
    after = assess_dictionaries([Path(generated)], stage="effective") if generated is not None else None
    comparison = compare_dictionaries([source], [Path(generated)]) if generated is not None else None
    left, right = _selected(before, code), _selected(after, code) if after else []
    changes = [row for row in comparison["differences"]
               if row["component_id"] == code and row["field"] in _CHEMICAL_FIELDS] if comparison else []
    reasons = []
    if len(left) != 1:
        reasons.append("source-component-missing-or-ambiguous")
    elif left[0]["verdicts"]["graph"] != "PASS" or before["input_integrity"] != "UNCHANGED":
        reasons.append("source-graph-or-integrity-invalid")
    if after is not None:
        if len(right) != 1:
            reasons.append("generated-component-missing-or-ambiguous")
        elif right[0]["status"] == "INVALID" or right[0]["verdicts"]["numerical"] != "PASS":
            reasons.append("generated-restraints-invalid-or-incomplete")
        if after["input_integrity"] != "UNCHANGED" or comparison["input_integrity"] != "UNCHANGED":
            reasons.append("generation-input-integrity-invalid")
        if any(row["field"] in {"atom_elements", "bond_orders", "hydrogen_attachments"} for row in changes):
            reasons.append("generated-atom-bond-or-hydrogen-identity-changed")
        if len(left) == len(right) == 1:
            source_charges, generated_charges = _explicit_formal_charges(left[0]), _explicit_formal_charges(right[0])
            if any(source_charges[atom] != generated_charges[atom]
                   for atom in source_charges.keys() & generated_charges.keys()):
                reasons.append("generated-explicit-formal-charge-changed")
            source_stereo, generated_stereo = _explicit_atom_stereo(left[0]), _explicit_atom_stereo(right[0])
            if any(source_stereo[atom] and generated_stereo[atom]
                   and source_stereo[atom] != generated_stereo[atom]
                   for atom in source_stereo.keys() & generated_stereo.keys()):
                reasons.append("generated-explicit-atom-stereochemistry-changed")
            if left[0]["inventory"]["chirality"] and right[0]["inventory"]["chirality"] \
                    and any(row["field"] == "signed_chirality" for row in changes):
                reasons.append("generated-declared-chirality-changed")
    issues = _numerical_issues(before, code, "source")
    if after:
        issues.extend(_numerical_issues(after, code, "generated"))
    return {"schema_version": 1, "audit_kind": "cif_component_generation_inspection",
            "policy_id": POLICY_ID, "component_id": code,
            "status": "REJECTED" if reasons else "CANDIDATE_REVIEW" if after else "SOURCE_REVIEW",
            "rejection_reasons": reasons,
            "source_assessment": before, "generated_assessment": after,
            "comparison": comparison, "numerical_issues": issues,
            "chemical_changes": changes, "automatic_adoption": False,
            "native_validation": "NOT_RUN", "linked_site_validation": "NOT_RUN",
            "limitations": ["Numerical completeness does not certify chemistry, native proxies or achieved geometry.",
                            "Charge representation and newly supplied stereochemistry remain explicit review evidence."]}


class _UnsupportedSeed(ValueError):
    pass


def _ideal_seed(source: Path, code: str) -> tuple[str, dict]:
    """Represent exact CCD ideal atoms in PDB, refusing lossy fallbacks."""
    if not re.fullmatch(r"[A-Za-z0-9]{1,3}", code):
        raise _UnsupportedSeed("Component identifier cannot be represented as a three-column PDB residue name")
    candidates = []
    for block in _blocks(source):
        values = {key.lower(): value for key, value in block.values.items()}
        names = values.get("_chem_comp_atom.atom_id", [])
        ids = values.get("_chem_comp_atom.comp_id", [])
        if not ids and values.get("_chem_comp.id") == [code]:
            ids = [code] * len(names)
        if code not in ids:
            continue
        columns = {key[len("_chem_comp_atom."):]: value for key, value in values.items()
                   if key.startswith("_chem_comp_atom.")}
        if any(not isinstance(column, list) or len(column) != len(names) for column in columns.values()):
            raise _UnsupportedSeed("Atom category columns do not have a complete consistent row inventory")
        candidates.append([{key: column[index] for key, column in columns.items()}
                           for index in range(len(names)) if ids[index] == code])
    if len(candidates) != 1 or not candidates[0]:
        raise _UnsupportedSeed("Expected exactly one source atom definition for the requested component")
    rows = candidates[0]
    if len(rows) > 99999:
        raise _UnsupportedSeed("Atom serial inventory exceeds the PDB representation")
    names = [row["atom_id"] for row in rows]
    if len(set(names)) != len(names):
        raise _UnsupportedSeed("Source exact atom identifiers are not unique")
    lines = ["REMARK  Source dictionary ideal coordinates; naming/starting seed only.\n"]
    charges = {}
    for index, row in enumerate(rows, 1):
        name, element = row["atom_id"], row.get("type_symbol", "")
        if not name or len(name) > 4 or any(char.isspace() for char in name) or not name.isascii():
            raise _UnsupportedSeed("An exact source atom identifier cannot be represented in four PDB columns: " + repr(name))
        if not re.fullmatch(r"[A-Za-z]{1,2}", element):
            raise _UnsupportedSeed("A source atom element is absent or unsupported: " + repr(element))
        coords = []
        for axis in "xyz":
            try:
                number = _number(row.get(f"pdbx_model_cartn_{axis}_ideal"))
            except (ValueError, TypeError, OverflowError) as exc:
                raise _UnsupportedSeed(f"Invalid ideal {axis} coordinate for exact atom {name}") from exc
            if number is None or not isfinite(number) or len(f"{number:8.3f}") != 8:
                raise _UnsupportedSeed(f"Missing or unrepresentable ideal {axis} coordinate for exact atom {name}")
            coords.append(number)
        try:
            charge = _number(row.get("pdbx_formal_charge", row.get("charge")))
        except (ValueError, TypeError, OverflowError) as exc:
            raise _UnsupportedSeed("Invalid explicit formal charge for exact atom " + name) from exc
        if charge is None or not charge.is_integer() or abs(charge) > 9:
            raise _UnsupportedSeed("Missing or unrepresentable integer formal charge for exact atom " + name)
        charges[name] = int(charge)
        charge_field = f"{abs(int(charge))}{'+' if charge > 0 else '-'}" if charge else "  "
        x, y, z = coords
        lines.append(f"HETATM{index:5d} {name:>4} {code:>3} A   1    "
                     f"{x:8.3f}{y:8.3f}{z:8.3f}{1.0:6.2f}{0.0:6.2f}          {element.upper():>2}{charge_field}\n")
    lines.append("END\n")
    return "".join(lines), {"origin": "source_dictionary_ideal_coordinates",
                            "atom_ids": names, "formal_charges": charges,
                            "coordinate_rounding_decimals": 3,
                            "experimental_model_used": False,
                            "role": "exact naming and independent initial geometry; not final restraint targets"}


def _artifact(path: Path, root: Path) -> dict:
    return {"anchor": "candidate_directory", "path": path.relative_to(root).as_posix(),
            "sha256": _sha(path.read_bytes()), "size": path.stat().st_size}


def _terminate_owned_group(process: subprocess.Popen) -> None:
    # The unreaped child reserves its PID, preventing process-group reuse before
    # this one escalation. Kill descendants too; an optimizer may launch helpers.
    if process.returncode is not None:
        return  # A reaped child no longer reserves its PID for signalling.
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()
    process.wait(timeout=5)


def generate_elbow_candidate(source: Path, code: str, output_parent: Path,
                             executable: Path, *, environment: Mapping[str, str],
                             phenix_version: str, timeout_seconds: float = 600) -> dict:
    """Run explicitly requested eLBOW generation in a fresh preserved folder.

    The documented AM1 optimization is requested; the exact installed backend
    and its result remain evidence in the raw log. There is no target invention,
    dictionary adoption, linked-site transformation or ReadySet retry here.
    """
    source, output_parent, executable = Path(source).resolve(), Path(output_parent).resolve(), Path(executable).resolve()
    if output_parent == source.parent or source.parent in output_parent.parents:
        raise ValueError("Candidate output parent must be outside the source dictionary directory")
    if not phenix_version or not str(phenix_version).strip():
        raise ValueError("An explicit Phenix version is required")
    if not isfinite(float(timeout_seconds)) or timeout_seconds <= 0:
        raise ValueError("Candidate timeout must be finite and positive")
    source_bytes = source.read_bytes()
    source_sha = _sha(source_bytes)
    output_parent.mkdir(parents=True, exist_ok=True)
    work = Path(mkdtemp(prefix="cif-generation-", dir=output_parent))
    snapshot = work / "source.cif"
    with snapshot.open("xb") as handle:
        handle.write(source_bytes)
    start = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    result = {"schema_version": 1, "audit_kind": "cif_numerical_generation_candidate",
              "policy_id": POLICY_ID, "component_id": code, "status": "FAILED",
              "candidate_directory": str(work), "candidate_directory_is_fresh": True,
              "source_provenance": {"path": str(source), "sha256": source_sha, "size": len(source_bytes)},
              "source": _artifact(snapshot, work), "phenix_version": str(phenix_version),
              "executable_provenance": str(executable), "documentation": ELBOW_DOCUMENTATION,
              "command": None, "seed": None, "execution": {"status": "NOT_RUN", "started_at": start},
              "inspection": inspect_component_generation(snapshot, None, code),
              "automatic_adoption": False, "readyset_retry": "NOT_RUN",
              "native_proxy_validation": "NOT_RUN", "linked_site_validation": "NOT_RUN"}
    error = None
    if result["inspection"]["status"] == "REJECTED":
        result["status"] = "REJECTED"
        error = "Source graph/identity is unsuitable for numerical generation"
    else:
        try:
            seed_text, seed_receipt = _ideal_seed(snapshot, code)
            seed = work / "source_ideal.pdb"
            with seed.open("x", encoding="ascii") as handle:
                handle.write(seed_text)
            result["seed"] = {**seed_receipt, "artifact": _artifact(seed, work)}
            command = [str(executable), "source.cif", f"--id={code}", "--output=candidate",
                       "--template=source_ideal.pdb", "--initial-geometry=source_ideal.pdb",
                       "--add-hydrogens=False", "--chiral=retain", "--opt"]
            result["command"] = command
            with (work / "elbow.log").open("xb") as log:
                process = subprocess.Popen(command, cwd=work, env=dict(environment),
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=os.name == "posix")
                try:
                    returncode = process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    _terminate_owned_group(process)
                    result["execution"].update(status="TIMED_OUT", returncode=process.returncode)
                    error = "Owned eLBOW process group exceeded the requested timeout"
                except BaseException:
                    _terminate_owned_group(process)
                    raise
                else:
                    result["execution"].update(status="COMPLETED" if returncode == 0 else "FAILED", returncode=returncode)
                    if returncode != 0:
                        error = "eLBOW returned a nonzero exit status"
                    elif not (work / "candidate.cif").is_file() or (work / "candidate.cif").is_symlink():
                        error = "eLBOW did not produce the exact regular candidate.cif output"
                    else:
                        result["inspection"] = inspect_component_generation(snapshot, work / "candidate.cif", code)
                        result["status"] = result["inspection"]["status"]
        except _UnsupportedSeed as exc:
            result["status"] = "REJECTED"
            result["execution"]["status"] = "UNSUPPORTED_INPUT"
            error = str(exc)
        except (OSError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            result["execution"]["status"] = "FAILED"
    try:
        source_preserved = _sha(source.read_bytes()) == source_sha
    except OSError:
        source_preserved = False
    try:
        snapshot_preserved = _sha(snapshot.read_bytes()) == source_sha
    except OSError:
        snapshot_preserved = False
    result["source_preserved"] = source_preserved
    result["frozen_source_preserved"] = snapshot_preserved
    if not source_preserved or not snapshot_preserved:
        result["status"] = "REJECTED"
        error = "Source or frozen source changed during numerical generation"
    result["error"] = error
    result["execution"].update(finished_at=datetime.now(timezone.utc).isoformat(),
                               elapsed_seconds=round(time.monotonic() - clock, 6),
                               timeout_seconds=timeout_seconds)
    result["outputs"] = [_artifact(path, work) for path in sorted(work.rglob("*"))
                         if path.is_file() and not path.is_symlink()]
    result["symlink_outputs"] = [path.relative_to(work).as_posix() for path in sorted(work.rglob("*")) if path.is_symlink()]
    result["receipt"] = {"anchor": "candidate_directory", "path": "generation_receipt.json"}
    with (work / "generation_receipt.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result
