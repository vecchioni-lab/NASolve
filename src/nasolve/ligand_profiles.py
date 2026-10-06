"""Reviewed monomer profiles and per-site linked-phosphate modifications.

1AP is the first reviewed profile. Do not infer new chemistry for other codes.
Source dictionaries are preserved; supported runtime adaptations are audited.
Models are never edited here.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from Bio.PDB.MMCIF2Dict import MMCIF2Dict
from Bio.PDB.mmcifio import MMCIFIO

from .dictionary_compatibility import normalize_torsion_block, TORSION_POLICY
from .model_assessment import file_sha256
from .phosphate import (PhosphateError, _atoms, audit_phosphates,
                        requested_op3_sites, validate_op3_sites)
from .run_context import artifact_reference
from .backbone import requested_backbone_policy

# Legacy profiles without an explicit scope remain 1AP-only. Never reinterpret
# their frozen inventory when adding another supported component.
AUTHORITATIVE_CODES = frozenset({"1AP"})
LINKED_PROFILE_CODES = AUTHORITATIVE_CODES | {"DZ", "5CM"}
MOD_ID = "NASnoOP3"
MOD_CIF = """data_mod_NASnoOP3
loop_
_chem_mod_atom.mod_id
_chem_mod_atom.function
_chem_mod_atom.atom_id
_chem_mod_atom.new_atom_id
_chem_mod_atom.new_type_symbol
_chem_mod_atom.new_type_energy
_chem_mod_atom.new_partial_charge
NASnoOP3 delete OP3 . . . .
"""


@dataclass
class _Block:
    text: str
    values: dict


def _blocks(path: Path) -> list[_Block]:
    """Split CIF1 data blocks without splitting semicolon-delimited text.

    Bio.PDB performs the token/loop parsing of each block. Do not flatten a
    multi-component file with MMCIF2Dict: repeated category names lose data.
    """
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    starts = []
    in_text = False
    for i, line in enumerate(lines):
        if line.startswith(";"):
            in_text = not in_text
        elif not in_text and re.match(r"^\s*data_\S+\s*(?:#.*)?$", line, re.I):
            starts.append(i)
    if in_text or not starts:
        raise PhosphateError(f"Invalid or unsupported dictionary CIF: {path.name}")
    result = []
    for first, last in zip(starts, [*starts[1:], len(lines)]):
        text = "".join(lines[first:last])
        try:
            values = dict(MMCIF2Dict(io.StringIO(text)))
        except (ValueError, StopIteration, IndexError) as exc:
            raise PhosphateError(f"Cannot parse dictionary {path.name}: {exc}") from exc
        result.append(_Block(text, values))
    if len({block.values["data_"].lower() for block in result}) != len(result):
        raise PhosphateError(f"Duplicate CIF data blocks in {path.name}")
    return result


def _emit(values: dict) -> str:
    output = io.StringIO()
    writer = MMCIFIO()
    writer.set_dict(values)
    writer.save(output)
    return output.getvalue()


def _component_ids(block: _Block) -> set[str]:
    return set(block.values.get("_chem_comp_atom.comp_id", []))


def _normalized_dictionary(source: Path) -> tuple[str, list[dict], bool]:
    rendered = []
    events = []
    changed = False
    for block in _blocks(source):
        values, block_events = normalize_torsion_block(block.values)
        block_changed = values != block.values
        changed = changed or block_changed
        rendered.append(_emit(values) if block_changed else block.text)
        events.extend({"block": block.values["data_"], **event} for event in block_events)
    text = ("# NASolve runtime torsion adaptation; source unchanged.\n"
            + "\n".join(rendered)) if changed else source.read_text(encoding="utf-8")
    return text, events, changed


def _dictionary_audit(source: Path, output: Path, events: list[dict], changed: bool) -> dict:
    # Paths here are descriptive provenance. Operational inputs are separately
    # frozen as run-anchored, checksum-bound refinement/view references.
    return {"source": str(source), "source_sha256": file_sha256(source),
            "output": str(output), "output_sha256": file_sha256(output),
            "policy": TORSION_POLICY, "changed": changed, "events": events}


def normalize_ccp4_torsion_alternates(
    source: Path, output: Path, *, audit: list[dict] | None = None,
) -> bool:
    """Create a runtime derivative; preserve recognized alternatives and source.

    Unknown conflicts remain intact with warnings for native interpretation.
    The first row's sigma is retained explicitly, matching CCTBX's conversion.
    """
    text, events, changed = _normalized_dictionary(source)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(text)
    if audit is not None:
        audit.append(_dictionary_audit(source, output, events, changed))
    return changed


def dictionary_component_codes(path: Path) -> set[str]:
    """Read component identity from CIF content, never from its filename."""
    codes = set()
    for block in _blocks(path):
        codes.update(block.values.get("_chem_comp.id", []))
        for key, column in block.values.items():
            if key.startswith("_chem_comp_") and key.endswith(".comp_id"):
                codes.update(column)
    return codes - {"", ".", "?"}


def _parameterized_codes(path: Path) -> set[str]:
    """Which explicit inputs already contain usable numerical monomer targets?

    A raw CCD graph remains a construction source, not an authoritative
    replacement for the numerical dictionary subsequently supplied by ReadySet.
    This is a capability check, not a second chemical library.
    """
    from math import isfinite
    usable = set()
    for block in _blocks(path):
        v = block.values
        codes = _component_ids(block)
        names = v.get("_chem_comp_atom.atom_id", [])
        energies = v.get("_chem_comp_atom.type_energy", [])
        bonds = v.get("_chem_comp_bond.atom_id_1", [])
        if (len(codes) != 1 or not names or len(energies) != len(names)
                or any(value in {"", ".", "?"} for value in energies) or not bonds):
            continue
        try:
            valid = all(len(v.get(key, [])) == len(bonds) and all(
                isfinite(float(value)) and float(value) > 0 for value in v[key])
                for key in ("_chem_comp_bond.value_dist", "_chem_comp_bond.value_dist_esd"))
        except (ValueError, TypeError, OverflowError):
            valid = False
        if valid:
            usable.update(codes)
    return usable


def validate_dz_dictionary(path: Path) -> None:
    """Check the selected DZ identity/parameterization, not its pairing recipe."""
    blocks = _blocks(path)
    groups = [group for block in blocks
              for group in block.values.get("_chem_comp.group", [])]
    if dictionary_component_codes(path) != {"DZ"} or groups != ["DNA"]:
        raise ValueError("DZ dictionary must declare only DNA-group DZ")
    if _parameterized_codes(path) != {"DZ"}:
        raise ValueError("DZ requires parameterized atom energy types and bond targets")
    component = next(block.values for block in blocks if _component_ids(block))
    names = component.get("_chem_comp_atom.atom_id", [])
    elements = dict(zip(names, component.get("_chem_comp_atom.type_symbol", [])))
    if elements.get("C1") != "C" or "N1" in elements:
        raise ValueError("DZ requires its C-glycoside atom C1, not a DC N1 atom")
    planes: dict[str, set[str]] = {}
    for plane, atom in zip(component.get("_chem_comp_plane_atom.plane_id", []),
                           component.get("_chem_comp_plane_atom.atom_id", [])):
        planes.setdefault(plane, set()).add(atom)
    if not any({"C1", "C2", "N3", "C4", "C5", "C6", "N4", "O2"} <= plane
               for plane in planes.values()):
        raise ValueError("DZ base-plane definition is incomplete")


def freeze_dictionary_audits(records: Sequence[dict], run: Path) -> list[dict]:
    """Turn adaptation receipts into normal portable NASolve references."""
    return [{**record, "source": frozen_reference(Path(record["source"]), run),
             "output": frozen_reference(Path(record["output"]), run)}
            for record in records]


def combine_dictionary_inputs(paths: Sequence[Path], output: Path) -> None:
    """Merge component lists; never concatenate duplicate data_comp_list blocks."""
    blocks = []
    names = set()
    list_rows: list[dict[str, str]] = []
    keys = []
    seen_ids = set()
    for path in paths:
        for block in _blocks(path):
            values = block.values
            if "_chem_comp.id" in values and not _component_ids(block):
                columns = {k: v for k, v in values.items() if k.startswith("_chem_comp.")}
                n = len(values["_chem_comp.id"])
                if any(len(v) != n for v in columns.values()):
                    raise PhosphateError(f"Inconsistent component list in {path.name}")
                for key in columns:
                    if key not in keys:
                        keys.append(key)
                for i in range(n):
                    row = {k: v[i] for k, v in columns.items()}
                    if row["_chem_comp.id"] in seen_ids:
                        raise PhosphateError("Duplicate component identity in supplied dictionaries")
                    seen_ids.add(row["_chem_comp.id"])
                    list_rows.append(row)
            else:
                name = values["data_"].lower()
                if name in names:
                    raise PhosphateError(f"Conflicting dictionary data block: {name}")
                names.add(name)
                blocks.append(block.text)
    prefix = ""
    if list_rows:
        prefix = _emit({"data_": "comp_list", **{
            k: [row.get(k, "?") for row in list_rows] for k in keys
        }})
    with output.open("x", encoding="utf-8") as handle:
        handle.write(prefix + "\n" + "\n".join(blocks))


def _exclude_components(source: Path, codes: set[str], output: Path) -> tuple[Path | None, set[str]]:
    """Keep ReadySet additions except authoritative component definitions."""
    retained = []
    present = set()
    for block in _blocks(source):
        values = block.values
        ids = _component_ids(block)
        if ids & codes:
            if ids - codes:
                raise PhosphateError("Mixed-component atom block cannot be overridden safely")
            continue
        if not ids and "_chem_comp.id" in values:
            keep = [i for i, code in enumerate(values["_chem_comp.id"]) if code not in codes]
            if not keep:
                continue
            if len(keep) != len(values["_chem_comp.id"]):
                if any(k != "data_" and not k.startswith("_chem_comp.") for k in values):
                    raise PhosphateError("Mixed-category component list requires review")
                values = {k: ([v[i] for i in keep] if k != "data_" else v)
                          for k, v in values.items()}
                retained.append(_emit(values))
                continue
        retained.append(block.text)
        present.update(ids)
    if not retained:
        return None, present
    with output.open("x", encoding="utf-8") as handle:
        handle.write("# ReadySet output with reviewed component overrides excluded.\n" + "\n".join(retained))
    return output, present


def _profile_inventory(model: Path, codes: frozenset[str] = AUTHORITATIVE_CODES) -> dict[str, str]:
    residues = {}
    for atom in _atoms(model.read_text(encoding="utf-8").splitlines(keepends=True)):
        code = atom.line[17:20].strip()
        if code in codes:
            residues[atom.site] = code
    return residues


def write_linked_profile(
    model: Path, directory: Path, *, allow_op3_sites: tuple[str, ...] = (),
    passthrough_sites: tuple[str, ...] = (),
    profile_codes: frozenset[str] = AUTHORITATIVE_CODES,
) -> tuple[dict[str, object], tuple[Path, ...]]:
    if not profile_codes <= LINKED_PROFILE_CODES:
        raise PhosphateError("Unsupported linked-phosphate component profile")
    inventory = _profile_inventory(model, profile_codes)
    audit = audit_phosphates(
        model, allow_op3_sites=allow_op3_sites, inspect_sites=tuple(inventory),
        passthrough_sites=passthrough_sites,
    )
    modifications = []
    for item in audit["checked"]:
        if item["site"] in inventory and item["incoming_site"] is not None:
            chain, resid = item["site"].split(":")
            # Supported selectors are explicit PDB identities, not arbitrary PHIL.
            validate_op3_sites([item["site"]])
            selection = f"chain '{'' if chain == '_' else chain}' and resid {resid} and resname {inventory[item['site']]}"
            modifications.append({"site": item["site"], "residue": inventory[item["site"]],
                                  "incoming_site": item["incoming_site"], "outgoing_site": item["outgoing_site"], "data_mod": MOD_ID,
                                  "selection": selection})
    paths = ()
    if modifications:
        cif = directory / "linked_phosphate.cif"
        phil = directory / "linked_phosphate.phil"
        with cif.open("x", encoding="utf-8") as handle:
            handle.write(MOD_CIF)
        with phil.open("x", encoding="utf-8") as handle:
            handle.write("# Generated from verified connectivity; do not apply by residue code alone.\n")
            for item in modifications:
                handle.write("refinement.pdb_interpretation.apply_cif_modification {\n"
                             f"  data_mod = {MOD_ID}\n  residue_selection = {item['selection']}\n}}\n")
        paths = (cif, phil)
    profile = {"schema_version": 1, "inventory": inventory, "modifications": modifications}
    if profile_codes != AUTHORITATIVE_CODES:
        profile["profile_codes"] = sorted(profile_codes)
    return profile, paths


def validate_model_phosphate_policy(model: Path, report: Mapping[str, object]) -> dict[str, object]:
    """Validate both default OP3 policy and the identities frozen in the PHIL."""
    allowed = requested_op3_sites(report)
    backbone = requested_backbone_policy(report)
    passthrough = tuple(backbone["experimental_passthrough_sites"])
    postmr = report.get("postmr")
    profile = postmr.get("linked_phosphate_profile") if isinstance(postmr, Mapping) else None
    modifications = []
    if profile is not None:
        if not isinstance(profile, Mapping) or profile.get("schema_version") != 1:
            raise PhosphateError("Malformed linked-phosphate profile")
        scope = profile.get("profile_codes", sorted(AUTHORITATIVE_CODES))
        if (not isinstance(scope, list) or not all(isinstance(code, str) for code in scope)
                or len(scope) != len(set(scope)) or not set(scope) <= LINKED_PROFILE_CODES):
            raise PhosphateError("Malformed linked-phosphate component scope")
        if profile.get("inventory") != _profile_inventory(model, frozenset(scope)):
            raise PhosphateError("Reviewed nucleotide identities changed; prepare new dictionary profiles")
        modifications = profile.get("modifications")
        if not isinstance(modifications, list) or any(
            not isinstance(item, Mapping) or not isinstance(item.get("site"), str)
            or not isinstance(item.get("incoming_site"), str) or item.get("data_mod") != MOD_ID
            for item in modifications
        ):
            raise PhosphateError("Malformed linked-phosphate modification inventory")
    result = audit_phosphates(
        model, allow_op3_sites=allowed,
        check_sites=tuple(item["site"] for item in modifications),
        passthrough_sites=passthrough,
    )
    actual = {item["site"]: (item["incoming_site"], item["outgoing_site"]) for item in result["checked"]}
    if any(actual.get(item["site"]) != (item["incoming_site"], item.get("outgoing_site"))
           for item in modifications):
        raise PhosphateError("Phosphate backbone link differs from the frozen site modification")
    return result


def effective_restraints(
    paths: Sequence[Path], generated: Path | None, directory: Path, *,
    normalize_effective: bool = False, audit: list[dict] | None = None,
    prefer_parameterized_inputs: bool = False,
) -> tuple[list[Path], list[Path]]:
    """Freeze the effective CIF authority, independently of phosphate profiles.

    Explicit parameterized definitions win over generated copies when requested
    by PostMR. Construction-only CCD graphs still defer to ReadySet. Legacy
    direct callers retain the original 1AP policy unless they opt into the new
    bundle path. Raw generated CIFs and all source definitions remain intact.
    """
    cifs = [p for p in paths if p.suffix.lower() == ".cif" and not is_modification_only(p)]
    ids = {p: dictionary_component_codes(p) for p in cifs}
    codes = set().union(*(value & AUTHORITATIVE_CODES for value in ids.values())) if ids else set()
    if prefer_parameterized_inputs:
        for path in cifs:
            codes.update(_parameterized_codes(path))
    other = [p for p in paths if p not in cifs]
    dictionaries = []
    generated_codes = set()
    if generated is not None:
        if codes:
            filtered, generated_codes = _exclude_components(
                generated, codes, directory / "readyset_supplement.cif")
            if filtered is not None:
                dictionaries.append(filtered)
        else:
            # No explicit override: preserve the native generated path unless
            # normalization below actually needs a changed derivative.
            dictionaries.append(generated)
            generated_codes = dictionary_component_codes(generated)
    for index, cif in enumerate(cifs):
        # Remove only components actually superseded by the chosen generated
        # definition; a multi-block input may retain other components.
        overlap = ids[cif] & generated_codes
        if not overlap:
            dictionaries.append(cif)
        elif ids[cif] - overlap:
            filtered, _ = _exclude_components(
                cif, overlap, directory / f"input_supplement_{index:03d}.cif")
            if filtered is not None:
                dictionaries.append(filtered)
    if normalize_effective:
        selected = []
        for index, source in enumerate(dictionaries):
            text, events, changed = _normalized_dictionary(source)
            output = source
            if changed:
                effective_dir = directory / "effective_dictionaries"
                effective_dir.mkdir(exist_ok=True)
                output = effective_dir / f"{index:03d}_{source.name}"
                with output.open("x", encoding="utf-8") as handle:
                    handle.write(text)
            if audit is not None:
                audit.append(_dictionary_audit(source, output, events, changed))
            selected.append(output)
        dictionaries = selected
    return [*other, *dictionaries], dictionaries


def frozen_reference(path: Path, run: Path) -> dict[str, object]:
    return {**artifact_reference(path, run), "sha256": file_sha256(path), "size": path.stat().st_size}


def is_modification_only(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return "_chem_mod_atom." in text and "_chem_comp_atom." not in text
