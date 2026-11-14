"""Explicit source-table ordering for native construction, without chemical edits.

This preparation does not guarantee a native coordinate table or candidate is
correct. All downstream source identity and native qualification gates still apply.
"""
from collections import deque
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

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
