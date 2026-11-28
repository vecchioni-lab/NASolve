"""Explicit source-table ordering for native construction, without chemical edits.

This preparation does not guarantee a native coordinate table or candidate is
correct. All downstream source identity and native qualification gates still apply.
"""
from collections import deque
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import re

from .cif_doctor import assess_dictionaries
from .cif_stereochemistry_audit import _graph
from .ligand_profiles import _blocks, _emit

POLICY_ID = "cif-connected-heavy-atom-order-v1"
_ATOM = "_chem_comp_atom."
_BOND = "_chem_comp_bond."
_HYDROGENS = {"H", "D", "T"}


def _ordered_values(values, code):
    lookup = {key.lower(): value for key, value in values.items()}
    if len(lookup) != len(values):
        raise ValueError("Ambiguous case variants in atom-order input")
    names = lookup.get(_ATOM + "atom_id", [])
    if (not names or any(not n or n in {"?", "."} for n in names)
            or len(set(names)) != len(names)):
        raise ValueError("Require unique explicit atom identities")
    for category, count in ((_ATOM, len(names)),
                            (_BOND, len(lookup.get(_BOND + "atom_id_1", [])))):
        columns = {k: v for k, v in lookup.items() if k.startswith(category)}
        if not columns or any(not isinstance(v, list) or len(v) != count for v in columns.values()):
            raise ValueError("Incomplete atom-order category: " + category)
        if category + "comp_id" not in columns or set(columns[category + "comp_id"]) != {code}:
            raise ValueError("Require one exact component in atom-order categories")
    if _ATOM + "type_symbol" not in lookup or _BOND + "atom_id_2" not in lookup:
        raise ValueError("Missing atom elements or bond endpoints")
    edges = set()
    for left, right in zip(lookup[_BOND + "atom_id_1"], lookup[_BOND + "atom_id_2"]):
        edge = tuple(sorted((left, right)))
        if left == right or left not in names or right not in names or edge in edges:
            raise ValueError("Ambiguous or invalid declared bond graph")
        edges.add(edge)
    elements, bonds, _, neighbors = _graph(lookup)
    if set(bonds.values()) - {"SINGLE", "DOUBLE", "TRIPLE", "AROMATIC", "DELOCALIZED"}:
        raise ValueError("Unsupported declared bond order")
    heavy = {n for n in names if elements[n] not in _HYDROGENS}
    hydrogen = set(names) - heavy
    if not heavy or any(len(neighbors[n]) != 1 or not neighbors[n] <= heavy for n in hydrogen):
        raise ValueError("Require heavy atoms and singly attached terminal H/D/T")
    # Exact names provide a deterministic tie-breaker, not a chemical priority.
    # Every heavy atom after the root has an earlier declared heavy neighbour.
    first = min(heavy)
    queue, seen, order = deque([first]), {first}, []
    while queue:
        name = queue.popleft()
        order.append(name)
        for other in sorted((neighbors[name] & heavy) - seen):
            seen.add(other)
            queue.append(other)
    if seen != heavy:
        raise ValueError("Require a connected declared heavy-atom graph")
    order.extend(sorted(hydrogen))
    positions = {name: i for i, name in enumerate(names)}
    indices = [positions[name] for name in order]
    result = deepcopy(values)
    for key, column in values.items():
        if key.lower().startswith(_ATOM):
            result[key] = [column[i] for i in indices]
    return result, list(names), order


def prepare_connected_atom_order(source, code, output):
    """Write a fresh single-component input with complete atom rows permuted.

    Preserve each parsed atom field (including original ordinals, coordinates,
    isotopes, charge and stereo), all other tables and the source reader dialect.
    A comp_list block is retained verbatim. Unknown extra blocks, disconnected
    heavy graphs and nonterminal hydrogens require a separate reviewed adapter.
    No source state, bond representation, numerical target or acceptance changes.
    """
    source, output = Path(source).resolve(strict=True), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError("Atom-order output already exists")
    if output.resolve() == source or any(p.is_symlink() for p in output.parents):
        raise ValueError("Require a separate regular atom-order output")
    original = source.read_bytes()
    blocks = _blocks(source)
    targets = [b for b in blocks if any(k.lower() == _ATOM + "atom_id" for k in b.values)]
    if len(targets) != 1:
        raise ValueError("Require exactly one component definition block")
    target = targets[0]
    others = [b for b in blocks if b is not target]
    if len(others) > 1 or any(b.values.get("data_", "").lower() != "comp_list"
                            or b.values.get("_chem_comp.id") != [code] for b in others):
        raise ValueError("Unreviewed additional dictionary block")
    converted, before, after = _ordered_values(target.values, code)
    assessment = assess_dictionaries([source], stage="connected-atom-order")
    if (len(assessment["components"]) != 1 or assessment["components"][0]["component_id"] != code
            or assessment["components"][0]["verdicts"]["graph"] != "PASS"):
        raise ValueError("Require one graph-valid source component")
    changed = before != after
    payload = ("".join(_emit(converted) if b is target else b.text for b in blocks).encode()
               if changed else original)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(payload)
    restored = _blocks(output)
    expected = [converted if b is target else b.values for b in blocks]
    if [b.values for b in restored] != expected:
        raise ValueError("Atom-order serialization changed declarations; output retained")
    if source.read_bytes() != original:
        raise ValueError("Atom-order source changed")
    return {"schema_version": 1, "policy_id": POLICY_ID, "component": code,
            "source_sha256": sha256(original).hexdigest(),
            "consumer_sha256": sha256(payload).hexdigest(), "source_preserved": True,
            "input_atom_order": before, "output_atom_order": after, "changed": changed,
            "chemical_declarations": "PRESERVED", "coordinate_values": "PRESERVED",
            "atom_ordinals": "PRESERVED_AS_SOURCE_METADATA", "reader_dialect": "PRESERVED",
            "native_qualification": "NOT_RUN", "automatic_adoption": False}
def confirmed_aromatic_systems(allowed, converted):
    """The observed conversions must be whole, unique, source-authorized systems."""
    return (isinstance(converted, list) and bool(converted)
            and converted == [system for system in allowed if system in converted])


def unlisted_builder_bond(values, code, diagnostic, log, *, allowed_systems=(), converted_systems=()):
    """Identify one extra heavy bond in eLBOW's printed table after a failed build.

    Require every source edge in its verified representation. Only a whole ring
    conversion observed before the failed build can change its printed orders. The failing two-decimal
    length must identify only the additional row at the table's printed precision.
    A stretched source bond, partial table or retained candidate is ineligible.
    """
    error = diagnostic.get("native_exception") or {}
    if (diagnostic.get("blocking_stage") != "NATIVE_BUILDER" or diagnostic.get("builder_started") is not True
            or diagnostic.get("candidate_state") != "ABSENT" or error.get("exception_type") != "Sorry"):
        return None
    match = re.fullmatch(r"Bond length too long\s*:\s*([0-9]{1,4}\.\d{2})", error.get("message", ""))
    if not match:
        return None
    specified = Decimal(match.group(1))
    elements, bonds, _, _ = _graph(values)
    printed = {}
    for line in log.splitlines():
        parts = line.split()
        if not parts or parts[0] != code:
            continue
        if len(parts) != 6:
            return None
        _, left, right, order, length, width = parts
        edge = tuple(sorted((left, right)))
        if (left == right or left not in elements or right not in elements or edge in printed
                or not all(re.fullmatch(r"[0-9]{1,4}\.\d{3}", v) for v in (length, width))
                or Decimal(length) <= 0 or Decimal(width) <= 0):
            return None
        printed[edge] = (order.upper(), Decimal(length))
    if converted_systems and not confirmed_aromatic_systems(allowed_systems, converted_systems):
        return None
    aromatic = {tuple(edge) for system in converted_systems for edge in system}
    if not aromatic <= bonds.keys():
        return None
    for edge, source_order in bonds.items():
        expected_order = "AROMATIC" if edge in aromatic else source_order
        if edge not in printed or printed[edge][0] != expected_order:
            return None
    additional = printed.keys() - bonds.keys()
    if len(additional) != 1:
        return None
    edge, = additional
    if any(elements[n] in _HYDROGENS for n in edge):
        return None
    # Other rows at either rounding boundary could also have triggered the error.
    consistent = {pair for pair, (_, length) in printed.items() if abs(length-specified) <= Decimal("0.0055")}
    order, length = printed[edge]
    if (consistent != additional or abs(length-specified) >= Decimal("0.0045")
            or order not in {"SINGLE", "DOUBLE", "TRIPLE", "AROMATIC"}):
        return None
    proof = {"atoms": list(edge), "native_length_angstrom": float(length), "source_bonds_matched": len(bonds)}
    if converted_systems:
        proof["converted_systems"] = converted_systems
    return proof
