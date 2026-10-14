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

from .cif_doctor import assess_dictionaries, compare_dictionaries, _bridges, _number, _ORDERS
from .ligand_profiles import _blocks

POLICY_ID = "cif-independent-elbow-candidate-v4"
BOND_REPRESENTATION_POLICY = "cif-source-declared-six-member-aromatic-v1"
ELBOW_DOCUMENTATION = "https://phenix-online.org/documentation/reference/elbow.html"
_OPTION_ALIASES = {
    "id": ("--id",), "output": ("--output",), "template": ("--template",),
    "initial_geometry": ("--initial-geometry", "--initial_geometry"),
    "add_hydrogens": ("--add-hydrogens", "--add_hydrogens"),
    "source_state_preservation": ("--pH",),
    "chiral": ("--chiral",), "opt": ("--opt",),
}
_INCOMPLETE_NUMERICS = {"incomplete-numerical-parameterization", "missing-angle-category", "graph-only-source"}
_HELP_SECTION = re.compile(r"^(?:options|optional arguments|optional-arguments|named arguments):\s*$", re.I)
_OPTION_START = re.compile(r"^(\s+)(?:-[A-Za-z0-9?](?:[ =][A-Z][A-Z0-9_]*)?\s*,\s*)?--[A-Za-z][A-Za-z0-9_-]*(?=$|[ =,\t])")
_OPTION_TOKEN = re.compile(r"(?<!\S)(--[A-Za-z][A-Za-z0-9_-]*)(?=$|[ =,\t])")
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


def _bond_representation(source: dict, generated: dict) -> dict:
    """Recognize one bounded declared representation without perceiving aromaticity.

    Only complete, isolated, alternating six-member C/N rings declared aromatic
    by the source can become aromatic bond types. Exact atom names, side bonds,
    explicit neutral ring charges and non-stereogenic ring bonds are required.
    Raw comparisons and all independent chemistry/numerical gates stay intact.
    """
    result = {"policy_id": BOND_REPRESENTATION_POLICY, "status": "UNSUPPORTED_DIFFERENCE",
              "connectivity_unchanged": False, "equivalent_rings": [], "unresolved_bonds": []}

    def inventory(component):
        rows = {}
        for row in component["inventory"]["bond_orders"]:
            edge = tuple(sorted(row["atoms"]))
            if len(edge) != 2 or edge[0] == edge[1] or edge in rows:
                return None
            rows[edge] = row
        return rows

    def orders(row):
        return {_ORDERS.get(value.upper(), value.upper()) for value in row["declarations"].values()}

    left, right = inventory(source), inventory(generated)
    if left is None or right is None:
        result["reason"] = "incomplete-or-ambiguous-bond-definition"
        return result
    result["connectivity_unchanged"] = left.keys() == right.keys()
    changed = {edge for edge in left.keys() | right.keys()
               if edge not in left or edge not in right or orders(left[edge]) != orders(right[edge])}
    result["unresolved_bonds"] = [list(edge) for edge in sorted(changed)]
    if not result["connectivity_unchanged"]:
        return result
    if not changed:
        result["status"] = "EXACT"
        return result
    adjacency = {}
    for a, b in left:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    bridges = _bridges(adjacency)
    eligible = {edge for edge in changed
                if orders(left[edge]) in ({"SINGLE"}, {"DOUBLE"})
                and orders(right[edge]) == {"AROMATIC"}
                and set(left[edge]["aromatic_declarations"].values()) == {"Y"}
                and set(right[edge]["aromatic_declarations"].values()) <= {"Y"}
                and all(set(row["stereo_declarations"].values()) <= {"N"}
                        for row in (left[edge], right[edge]))}
    eligible_by_atom = {}
    for edge in eligible:
        for atom in edge:
            eligible_by_atom.setdefault(atom, set()).add(edge)
    source_atoms = {atom["atom_id"]: atom["element"] for atom in source["inventory"]["atoms"]}
    generated_atoms = {atom["atom_id"]: atom["element"] for atom in generated["inventory"]["atoms"]}
    source_charges, generated_charges = _explicit_formal_charges(source), _explicit_formal_charges(generated)
    remaining, covered = set(eligible), set()
    while remaining:
        start = min(remaining)
        edges, atoms, pending = set(), set(), set(start)
        while pending:
            atom = pending.pop()
            if atom in atoms:
                continue
            atoms.add(atom)
            for edge in eligible_by_atom.get(atom, ()):
                edges.add(edge)
                pending.update(set(edge) - atoms)
        remaining -= edges
        if len(atoms) != 6 or len(edges) != 6:
            continue
        if any(len([edge for edge in edges if atom in edge]) != 2
               or {next(iter(orders(left[edge]))) for edge in edges if atom in edge} != {"SINGLE", "DOUBLE"}
               for atom in atoms):
            continue
        if any(source_atoms.get(atom) not in {"C", "N"}
               or generated_atoms.get(atom) != source_atoms[atom]
               or source_charges.get(atom) != 0 or generated_charges.get(atom) != 0
               for atom in atoms):
            continue
        # Reject chords, fused/spiro rings and exocyclic multiple bonds. A
        # simple substituent must connect through an unchanged single bridge.
        side_edges = {edge for edge in left if set(edge) & atoms} - edges
        if any(frozenset(edge) not in bridges or orders(left[edge]) != {"SINGLE"}
               or orders(right[edge]) != {"SINGLE"} for edge in side_edges):
            continue
        covered |= edges
        result["equivalent_rings"].append({"atoms": sorted(atoms), "bonds": [
            {"atoms": list(edge), "source_order": next(iter(orders(left[edge]))),
             "generated_order": "AROMATIC", "source_aromatic_declaration": "Y"}
            for edge in sorted(edges)]})
    result["unresolved_bonds"] = [list(edge) for edge in sorted(changed - covered)]
    if not result["unresolved_bonds"]:
        result["status"] = "SOURCE_DECLARED_EQUIVALENT"
    return result


def _supported_plane_review(finding: dict) -> bool:
    """Retain finite, realizable Gram reviews, never an impossible angle set."""
    if finding["code"] != "plane-angle-compatibility" or finding["status"] != "REVIEW":
        return False
    measurements = finding["measurements"]
    if measurements.get("positive_semidefinite") is not True:
        return False
    for field in ("angles_degrees", "angle_esds", "eigenvalues"):
        values = measurements.get(field)
        if not isinstance(values, list) or len(values) != 3:
            return False
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value)
               for value in values):
            return False
    determinant = measurements.get("determinant")
    return (all(0 <= angle <= 180 for angle in measurements["angles_degrees"])
            and all(sigma > 0 for sigma in measurements["angle_esds"])
            and isinstance(determinant, (int, float)) and not isinstance(determinant, bool)
            and isfinite(determinant))


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
    representation = (_bond_representation(left[0], right[0]) if len(left) == len(right) == 1 else
                      {"policy_id": BOND_REPRESENTATION_POLICY, "status": "NOT_RUN",
                       "connectivity_unchanged": None, "equivalent_rings": [], "unresolved_bonds": []})
    reasons = []
    if len(left) != 1:
        reasons.append("source-component-missing-or-ambiguous")
    elif left[0]["verdicts"]["graph"] != "PASS" or before["input_integrity"] != "UNCHANGED":
        reasons.append("source-graph-or-integrity-invalid")
    if after is not None:
        if len(right) != 1:
            reasons.append("generated-component-missing-or-ambiguous")
        elif right[0]["status"] == "INVALID" or any(
                finding["code"] in _INCOMPLETE_NUMERICS and finding["status"] != "PASS"
                for finding in right[0]["findings"]):
            reasons.append("generated-restraints-invalid-or-incomplete")
        if len(right) == 1 and any(
                finding["rule_id"] == "PLANE-01" and finding["status"] != "PASS"
                and not _supported_plane_review(finding)
                for finding in right[0]["findings"]):
            reasons.append("generated-plane-angle-geometry-invalid-or-unassessed")
        if after["input_integrity"] != "UNCHANGED" or comparison["input_integrity"] != "UNCHANGED":
            reasons.append("generation-input-integrity-invalid")
        if any(row["field"] in {"atom_elements", "hydrogen_attachments"}
               or (row["field"] == "bond_orders" and representation["status"] != "SOURCE_DECLARED_EQUIVALENT")
               for row in changes):
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
            "chemical_changes": changes, "bond_representation": representation, "automatic_adoption": False,
            "native_validation": "NOT_RUN", "linked_site_validation": "NOT_RUN",
            "limitations": ["Numerical completeness does not certify chemistry, native proxies or achieved geometry.",
                            "Only complete finite positive-semidefinite Gram findings can remain soft plane reviews.",
                            "Well-formed unresolved torsion relationships remain review evidence pending native interpretation; no term is removed or adopted.",
                            "Only complete source-declared isolated neutral C/N six-member alternating rings can change to aromatic bond types; other order changes remain rejected.",
                            "Charge representation and newly supplied stereochemistry remain explicit review evidence."]}


class _UnsupportedSeed(ValueError):
    pass


class _UnsupportedGenerator(ValueError):
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


def _help_option_definitions(help_text: str) -> dict[str, bool | None]:
    """Read exact definitions, excluding examples and wrapped description text.

    Runtime optparse/argparse help has an explicit options section. Only the
    least-indented option-definition rows are used; deeper continuations are
    descriptions. Value placeholders are required for valued semantics.
    """
    rows = []
    section = False
    for line in help_text.splitlines():
        if _HELP_SECTION.fullmatch(line.strip()):
            section = True
            continue
        if section and line and not line[0].isspace():
            section = False
        if not section:
            continue
        match = _OPTION_START.match(line)
        if match:
            signature = re.split(r"\s{2,}", line.strip(), maxsplit=1)[0]
            rows.append((len(match.group(1)), signature))
    if not rows:
        return {}
    indentation = min(row[0] for row in rows)
    definitions = {}
    for depth, signature in rows:
        if depth != indentation:
            continue
        for token in _OPTION_TOKEN.finditer(signature):
            remainder = signature[token.end():]
            valued = bool(re.match(r"(?:=|[ \t]+)(?:[A-Z][A-Z0-9_]*|<[^>]+>|\{[^}]+\})(?=$|[, \t])", remainder))
            option = token.group(1)
            if option in definitions and definitions[option] != valued:
                # Ambiguous usage is never silently treated as compatible.
                definitions[option] = None
            else:
                definitions[option] = valued
    return definitions


def _generator_capabilities(executable: Path, work: Path,
                            environment: Mapping[str, str], timeout_seconds: float,
                            phenix_version: str) -> dict:
    timeout = min(float(timeout_seconds), 20.0)
    command = [str(executable), "--help"]
    clock = time.monotonic()
    receipt = {"schema_version": 1, "status": "UNSUPPORTED_GENERATOR", "command": command,
               "phenix_version": phenix_version, "timeout_seconds": timeout,
               "returncode": None, "selected_aliases": {}, "required_semantics": list(_OPTION_ALIASES),
               "definition_parser": "exact-installed-help-option-definitions-v1"}
    try:
        receipt["executable_sha256"] = _sha(executable.read_bytes())
        with (work / "elbow_help.log").open("xb") as log:
            process = subprocess.Popen(command, cwd=work, env=dict(environment),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=os.name == "posix")
            try:
                receipt["returncode"] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _terminate_owned_group(process)
                receipt.update(reason="help-timeout", returncode=process.returncode)
            except BaseException:
                _terminate_owned_group(process)
                raise
            else:
                if receipt["returncode"] != 0:
                    receipt["reason"] = "help-nonzero-exit"
                else:
                    definitions = _help_option_definitions((work / "elbow_help.log").read_text(encoding="utf-8", errors="replace"))
                    receipt["supported_option_definitions"] = definitions
                    missing = []
                    for semantic, aliases in _OPTION_ALIASES.items():
                        expected_value = semantic != "opt"
                        selected = next((option for option in aliases if definitions.get(option) is expected_value), None)
                        if selected is None:
                            missing.append(semantic)
                        else:
                            receipt["selected_aliases"][semantic] = selected
                    receipt["unsupported_semantics"] = missing
                    if missing:
                        receipt["reason"] = "required-option-semantics-unavailable"
                    else:
                        receipt["status"] = "SUPPORTED"
        if _sha(executable.read_bytes()) != receipt["executable_sha256"]:
            receipt.update(status="UNSUPPORTED_GENERATOR", reason="executable-changed-during-help")
    except OSError as exc:
        receipt.update(reason="help-execution-error", error=f"{type(exc).__name__}: {exc}")
    receipt["elapsed_seconds"] = round(time.monotonic() - clock, 6)
    if (work / "elbow_help.log").is_file():
        receipt["help_output"] = _artifact(work / "elbow_help.log", work)
    return receipt


def generate_elbow_candidate(source: Path, code: str, output_parent: Path,
                             executable: Path, *, environment: Mapping[str, str],
                             phenix_version: str, timeout_seconds: float = 600) -> dict:
    """Run explicitly requested eLBOW generation in a fresh preserved folder.

    Required option spelling/value support is discovered from installed help.
    The installed generator's best available optimization is requested; its backend
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
              "generator_capabilities": None,
              "source_state_preservation": {
                  "generator_value": "low", "purpose": "retain the exact supplied input chemistry during generation",
                  "source_state_authority": "explicit supplied source dictionary",
                  "experimental_ph": "UNASSESSED", "solution_protonation": "UNASSESSED",
                  "limitations": ["The generator's source-retention selector is not an experimental or crystal pH assignment.",
                                  "Source hydrogen, charge, bond and stereochemical declarations remain subject to comparison and review."]},
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
            capabilities = _generator_capabilities(executable, work, environment, timeout_seconds, str(phenix_version))
            result["generator_capabilities"] = capabilities
            if capabilities["status"] != "SUPPORTED":
                raise _UnsupportedGenerator("Installed eLBOW cannot preserve the required generation semantics: "
                                            + capabilities.get("reason", "unknown"))
            flags = capabilities["selected_aliases"]
            result["source_state_preservation"]["generator_option"] = flags["source_state_preservation"]
            command = [str(executable), "source.cif", f"{flags['id']}={code}", f"{flags['output']}=candidate",
                       f"{flags['template']}=source_ideal.pdb", f"{flags['initial_geometry']}=source_ideal.pdb",
                       f"{flags['add_hydrogens']}=False", f"{flags['source_state_preservation']}=low",
                       f"{flags['chiral']}=retain", flags['opt']]
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
        except _UnsupportedGenerator as exc:
            result["status"] = "REJECTED"
            result["execution"]["status"] = "UNSUPPORTED_GENERATOR"
            error = str(exc)
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
