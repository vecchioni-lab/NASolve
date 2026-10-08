"""Explicit preferred-component preparation; never rewrite frozen MR inputs.

Only the user-approved 1W5 -> DZ and 1WA -> DP policies live here.  These
are NOT general tautomer equivalences.  Mapped heavy-atom coordinates are
retained, source hydrogens/charge annotations are discarded, and the chosen
parameterized target dictionary supplies the prepared chemical definition.
"""
from __future__ import annotations

from collections import OrderedDict
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .curated_ligands import PDB_DEPOSITION_ALIASES

POLICY = "preferred-DZ-DP-v1"
PREFERRED_COMPONENTS = MappingProxyType({"1W5": "DZ", "1WA": "DP"})
BACKBONE_ELEMENTS = {
    "P": "P", "OP1": "O", "OP2": "O", "OP3": "O", "O5'": "O",
    "C5'": "C", "C4'": "C", "O4'": "O", "C3'": "C", "O3'": "O",
    "C2'": "C", "C1'": "C",
}
BASE_ELEMENTS = {
    "DZ": {"C1": "C", "C2": "C", "O2": "O", "N3": "N", "C4": "C",
           "N4": "N", "C5": "C", "C6": "C", "N": "N", "ON1": "O", "ON2": "O"},
    "DP": {"N1": "N", "C2": "C", "N2": "N", "N3": "N", "C4": "C",
           "N5": "N", "C6": "C", "O6": "O", "C7": "C", "C8": "C", "N9": "N"},
}
# Reviewed heavy-atom names are identical between each source/target pair.
# O1P/O2P/O3P are the existing PDB phosphate spelling convention only.
ATOM_ALIASES = {"O1P": "OP1", "O2P": "OP2", "O3P": "OP3"}
SOURCE_MONOMER_BLOBS = {
    "1W5": "b309086c6d215b6ae48d7beb4654b9e278633005",
    "1WA": "c4d547e90bbe99595e44d674248a3613350dc54d",
}


def preferred_component(code: str) -> str:
    """Normalize a requested preparation code, not its stored source spelling."""
    return PREFERRED_COMPONENTS.get(code, code)


def prepared_target_code(code: str) -> str:
    """Emit reviewed long deposition identity under its exact PDB-compatible name.

    This mapping is for an explicit target, not for rewriting source coordinates
    or discovering equivalent chemistry. All non-reviewed long codes still stop.
    """
    return PDB_DEPOSITION_ALIASES.get(code, preferred_component(code))


def _identity(line: str, offset: int = 0) -> tuple[str, str] | None:
    if len(line) < offset + 27:
        return None
    site = f"{line[21 + offset:22 + offset].strip() or '_'}:{line[22 + offset:27 + offset].strip()}"
    return site, line[17 + offset:20 + offset].strip()


def preparation_targets(targets: Mapping[str, str], model: Path) -> OrderedDict[str, str]:
    """Normalize explicit targets; also catch source components outside targets.

    An explicit target at a site still wins over retaining its source residue.
    The original target mapping and coordinate bytes are never changed here.
    """
    result = OrderedDict((site, prepared_target_code(code)) for site, code in targets.items())
    for line in model.read_text(encoding="utf-8").splitlines():
        if line.startswith(("ATOM  ", "HETATM")) and (identity := _identity(line)):
            site, code = identity
            if code in PREFERRED_COMPONENTS:
                result.setdefault(site, PREFERRED_COMPONENTS[code])
    return result


def target_changes(targets: Mapping[str, str]) -> list[dict[str, str]]:
    """Freeze an exact requested-to-prepared mapping with distinct authority."""
    changes: list[dict[str, str]] = []
    for site, code in targets.items():
        prepared = prepared_target_code(code)
        if prepared == code:
            continue
        entry = {"site": site, "requested_code": code, "prepared_code": prepared}
        if code in PDB_DEPOSITION_ALIASES:
            entry["basis"] = "reviewed-deposition-to-pdb-code"
        changes.append(entry)
    return changes


def _mapped_atom(name: str, element: str, target: str) -> tuple[str | None, str]:
    mapped = ATOM_ALIASES.get(name, name)
    allowed = {**BACKBONE_ELEMENTS, **BASE_ELEMENTS[target]}
    if mapped in allowed:
        expected = allowed[mapped]
        if element and element != expected:
            raise ValueError(f"Component normalization: {name} is {element}, expected {expected}")
        return mapped, expected
    if element in {"H", "D", "T"} or (not element and name.lstrip("0123456789").startswith(("H", "D"))):
        return None, element or "H"
    raise ValueError(f"Component normalization has no reviewed heavy-atom mapping for {name!r} -> {target}")


def _rewrite_atom_line(line: str, target: str, atom: str, element: str) -> str:
    # PDB atom-name alignment; the original xyz/occupancy/B and serial survive.
    name_field = (" " + atom.ljust(3)) if len(atom) < 4 and len(element) == 1 else atom.ljust(4)
    newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    text = line.removesuffix(newline) if newline else line
    text = text.ljust(80)
    return (text[:12] + name_field + text[16:17] + f"{target:>3}" + text[20:76]
            + f"{element:>2}" + "  " + text[80:] + newline)


def normalize_model(source: Path, destination: Path,
                    conversions: Mapping[str, tuple[str, str]]) -> dict[str, object]:
    """Write a new heavy-atom mapped derivative for the specified actual sites.

    Required target dictionaries are validated by PostMR before this operation.
    Missing atoms are reported, not invented; ordinary preparation and native
    interpretation retain authority over usable geometry. Only these exact
    source/target pairs are accepted. No same-name element substitutions occur.
    """
    if source.resolve() == destination.resolve() or destination.exists():
        raise ValueError("Component normalization requires a new derivative path")
    for site, (before, after) in conversions.items():
        if PREFERRED_COMPONENTS.get(before) != after:
            raise ValueError(f"Unreviewed component conversion at {site}: {before}->{after}")
    data = source.read_bytes()
    if not conversions:
        with destination.open("xb") as handle:
            handle.write(data)
        return {"schema_version": 1, "policy": POLICY, "conversions": [],
                "source_sha256": sha256(data).hexdigest(),
                "output_sha256": sha256(data).hexdigest(),
                "mapped_xyz_occupancy_b_preserved": True, "source_modified": False,
                "structurally_approved": False}
    lines = data.decode("utf-8").splitlines(keepends=True)
    if conversions and sum(line.startswith("MODEL ") for line in lines) > 1:
        raise ValueError("Component normalization requires one coordinate model")
    events = {site: {"site": site, "source_code": before, "target_code": after,
                    "source_dictionary_git_blob": SOURCE_MONOMER_BLOBS[before],
                    "atom_map": [], "removed_hydrogens": [], "cleared_formal_charge_count": 0}
              for site, (before, after) in conversions.items()}
    changed: dict[int, str | None] = {}
    serial_sites: dict[int, str] = {}
    removed_serials: set[int] = set()
    seen: set[tuple[str, str, str]] = set()
    atom_keys: dict[tuple[str, str, str], tuple[str | None, str]] = {}
    for index, line in enumerate(lines):
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        identity = _identity(line)
        if identity is None or identity[0] not in conversions:
            continue
        site, code = identity
        before, target = conversions[site]
        if code != before:
            raise ValueError(f"Mixed or unexpected source identity at {site}: {code} != {before}")
        name, alt = line[12:16].strip(), line[16:17]
        element = line[76:78].strip().upper() if len(line) >= 78 else ""
        mapped, effective_element = _mapped_atom(name, element, target)
        key = (site, name, alt)
        if key in atom_keys:
            raise ValueError(f"Duplicate source atom at {site}: {name}/{alt.strip()}")
        atom_keys[key] = mapped, effective_element
        try:
            serial = int(line[6:11])
        except ValueError as exc:
            raise ValueError("Component normalization requires ordinary PDB atom serials") from exc
        if serial in serial_sites:
            raise ValueError("Duplicate serial in component-normalized atoms")
        serial_sites[serial] = site
        if mapped is None:
            changed[index] = None
            removed_serials.add(serial)
            events[site]["removed_hydrogens"].append({"atom": name, "alternate": alt.strip(), "serial": serial})
            continue
        final_key = (site, mapped, alt)
        if final_key in seen:
            raise ValueError(f"Normalization would collide at {site}: {mapped}/{alt.strip()}")
        seen.add(final_key)
        events[site]["atom_map"].append({"source_atom": name, "target_atom": mapped,
                                         "element": effective_element, "alternate": alt.strip()})
        if len(line) >= 80 and line[78:80].strip():
            events[site]["cleared_formal_charge_count"] += 1
        changed[index] = _rewrite_atom_line(line, target, mapped, effective_element)
    for site, event in events.items():
        if not event["atom_map"]:
            raise ValueError(f"No mapped heavy atoms at requested normalization site {site}")
        present = {row["target_atom"] for row in event["atom_map"]}
        event["unobserved_dictionary_heavy_atoms"] = sorted(
            (set(BACKBONE_ELEMENTS) | set(BASE_ELEMENTS[event["target_code"]])) - present)
    removed_connectivity = 0
    removed_metadata = 0
    output: list[str] = []
    for index, line in enumerate(lines):
        if index in changed:
            if changed[index] is not None:
                output.append(changed[index])
            continue
        kind = line[:6].strip()
        identity = _identity(line)
        if kind in {"ANISOU", "SIGATM", "SIGUIJ"} and identity and identity[0] in conversions:
            site, code = identity
            if code != conversions[site][0]:
                raise ValueError(f"Tensor record has inconsistent residue identity at {site}")
            key = (site, line[12:16].strip(), line[16:17])
            if key not in atom_keys:
                raise ValueError(f"Tensor record has no matching converted atom at {site}")
            mapped, element = atom_keys[key]
            if mapped is not None:
                output.append(_rewrite_atom_line(line, conversions[site][1], mapped, element))
            continue
        if kind == "TER" and identity and identity[0] in conversions:
            line = line[:17] + f"{conversions[identity[0]][1]:>3}" + line[20:]
        elif kind == "LINK":
            drop = False
            for offset in (0, 30):
                endpoint = _identity(line, offset)
                if endpoint and endpoint[0] in conversions:
                    site, code = endpoint
                    if code != conversions[site][0]:
                        raise ValueError(f"LINK residue identity disagrees at {site}")
                    atom = line[12 + offset:16 + offset].strip()
                    mapped, element = _mapped_atom(atom, "", conversions[site][1])
                    if mapped is None:
                        drop = True
                        break
                    name_field = " " + mapped.ljust(3) if len(mapped) < 4 else mapped.ljust(4)
                    line = (line[:12 + offset] + name_field + line[16 + offset:17 + offset]
                            + f"{conversions[site][1]:>3}" + line[20 + offset:])
            if drop:
                removed_metadata += 1
                continue
        elif kind == "CONECT":
            try:
                values = [int(line[i:i + 5]) for i in range(6, len(line.rstrip("\r\n")), 5)
                          if line[i:i + 5].strip()]
            except ValueError as exc:
                raise ValueError("Cannot preserve malformed CONECT during component conversion") from exc
            if not values:
                output.append(line)
                continue
            centre, neighbors = values[0], values[1:]
            if centre in removed_serials:
                removed_connectivity += len(neighbors)
                continue
            kept = [v for v in neighbors if v not in removed_serials and not (
                centre in serial_sites and v in serial_sites and serial_sites[centre] == serial_sites[v])]
            removed_connectivity += len(neighbors) - len(kept)
            if len(kept) != len(neighbors):
                if kept:
                    output.append("CONECT" + "".join(f"{v:5d}" for v in [centre, *kept]) + "\n")
                continue
        elif kind in {"MASTER", "MODRES", "HETNAM", "HETSYN", "FORMUL", "HET"}:
            # Descriptive source-component records cannot define target chemistry.
            # The complete original stays frozen. Unrelated metadata is retained.
            if kind == "MASTER" or any(before in line.split() for before, _ in conversions.values()):
                removed_metadata += 1
                continue
        elif kind == "SEQRES" and any(code in line.split() for code in PREFERRED_COMPONENTS):
            # Source sequence annotations do not define a derived target. Its
            # exact raw sequence request remains in the frozen run contract.
            removed_metadata += 1
            continue
        output.append(line)
    if source.read_bytes() != data:
        raise ValueError("Source model changed during component normalization")
    rendered = "".join(output).encode("utf-8")
    with destination.open("xb") as handle:
        handle.write(rendered)
    return {
        "schema_version": 1, "policy": POLICY,
        "source_sha256": sha256(data).hexdigest(), "output_sha256": sha256(rendered).hexdigest(),
        "conversions": list(events.values()),
        "removed_source_connectivity_references": removed_connectivity,
        "removed_source_metadata_records": removed_metadata,
        "mapped_xyz_occupancy_b_preserved": True,
        "chemical_authority": "parameterized target dictionary; not source hydrogen/bond/charge records",
        "source_modified": False, "structurally_approved": False,
    }


BACKBONE_BONDS = (
    ("P", "OP1"), ("P", "OP2"), ("P", "OP3"), ("P", "O5'"),
    ("O5'", "C5'"), ("C5'", "C4'"), ("C4'", "O4'"), ("O4'", "C1'"),
    ("C1'", "C2'"), ("C2'", "C3'"), ("C3'", "C4'"), ("C3'", "O3'"),
)
BASE_BONDS = {
    "DZ": (("C1'", "C1"), ("C1", "C2"), ("C2", "N3"), ("N3", "C4"),
           ("C4", "C5"), ("C5", "C6"), ("C6", "C1"), ("C2", "O2"),
           ("C4", "N4"), ("C5", "N"), ("N", "ON1"), ("N", "ON2")),
    "DP": (("C1'", "N9"), ("N9", "C8"), ("C8", "C7"), ("C7", "N5"),
           ("N5", "C4"), ("C4", "N9"), ("N5", "C6"), ("C6", "N1"),
           ("N1", "C2"), ("C2", "N3"), ("N3", "C4"), ("C2", "N2"), ("C6", "O6")),
}


def validate_preferred_dictionary(code: str, path: Path) -> None:
    """Validate the exact target skeleton, numerical capability and base plane.

    Source/target heavy-atom adjacency and element maps were reviewed against
    the cited MonomerLibrary definitions. This does not equate their bond
    orders, protonation or charge states. The target carbonyl must be a double
    bond; its supplier's numerical parameters are not rewritten.
    """
    from .ligand_profiles import _blocks, _parameterized_codes, dictionary_component_codes

    if code not in BASE_ELEMENTS:
        raise ValueError(f"No reviewed preferred-component dictionary contract for {code}")
    blocks = _blocks(path)
    groups = [group for block in blocks for group in block.values.get("_chem_comp.group", [])]
    if dictionary_component_codes(path) != {code} or groups != ["DNA"]:
        raise ValueError(f"{code} dictionary must declare only DNA-group {code}")
    if _parameterized_codes(path) != {code}:
        raise ValueError(f"{code} requires numerical bond targets and atom energy types")
    components = [b.values for b in blocks if "_chem_comp_atom.atom_id" in b.values]
    if len(components) != 1:
        raise ValueError(f"{code} needs one unambiguous component atom block")
    v = components[0]
    names, elements = v["_chem_comp_atom.atom_id"], v.get("_chem_comp_atom.type_symbol", [])
    if len(names) != len(elements) or len(names) != len(set(names)):
        raise ValueError(f"{code} dictionary atom inventory is inconsistent")
    heavy = {name: element for name, element in zip(names, elements) if element not in {"H", "D"}}
    if heavy != {**BACKBONE_ELEMENTS, **BASE_ELEMENTS[code]}:
        raise ValueError(f"{code} dictionary does not match its reviewed heavy-atom map")
    bonds = {frozenset((a, b)): order.upper() for a, b, order in zip(
        v.get("_chem_comp_bond.atom_id_1", []), v.get("_chem_comp_bond.atom_id_2", []),
        v.get("_chem_comp_bond.type", [])) if a in heavy and b in heavy}
    expected = {frozenset(pair) for pair in (*BACKBONE_BONDS, *BASE_BONDS[code])}
    if set(bonds) != expected:
        raise ValueError(f"{code} dictionary heavy-atom connectivity changed")
    carbonyl = frozenset(("C2", "O2") if code == "DZ" else ("C6", "O6"))
    if bonds[carbonyl] not in {"DOUBLE", "DOUB"}:
        raise ValueError(f"{code} requires the target carbonyl, not the source hydroxyl definition")
    planes: dict[str, set[str]] = {}
    for plane, name in zip(v.get("_chem_comp_plane_atom.plane_id", []),
                           v.get("_chem_comp_plane_atom.atom_id", [])):
        planes.setdefault(plane, set()).add(name)
    required_plane = set(BASE_ELEMENTS[code]) - ({"N", "ON1", "ON2"} if code == "DZ" else set())
    if not any(required_plane <= plane for plane in planes.values()):
        raise ValueError(f"{code} base-plane definition is incomplete")
