"""Check the two contacts of a declared canonical A:uracil pair against its source graph."""
from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace

from .cif_doctor import _bridges
from .cif_na_policy import _parse
from .cif_plane_coverage import _six_rings_through


def source_uracil_edge(graph, attachment):
    """Find the neutral dioxopyrimidine edge relative to the verified sugar–ring bond.

    In cis Watson–Crick geometry adenine N6 faces the carbonyl opposite the
    attachment. The adjacent carbonyl faces the sugar side. The central N–H
    donates to adenine N1. Other ring or protonation representations stay open.
    """
    elements, bonds, charges, neighbors = graph
    bridges = _bridges(neighbors)
    ring_neighbors = {
        atom: {n for n in adjacent if frozenset((atom, n)) not in bridges}
        for atom, adjacent in neighbors.items()
    }
    flanks = ring_neighbors.get(attachment, set())
    if len(flanks) != 2:
        return None
    rings = _six_rings_through(attachment, flanks, elements, neighbors)
    if len(rings) != 1:
        return None
    ring, = rings
    if (sorted(elements[a] for a in ring) != ["C"] * 4 + ["N"] * 2
            or any(charges[a] != 0 or len(ring_neighbors[a]) != 2 for a in ring)):
        return None

    def order(a, b):
        return bonds[tuple(sorted((a, b)))]

    ring_orders = [order(a, ring[(i + 1) % 6]) for i, a in enumerate(ring)]
    if sorted(ring_orders) != ["DOUBLE"] + ["SINGLE"] * 5:
        return None
    carbonyls = {}
    for i, carbon in enumerate(ring):
        if elements[carbon] != "C":
            continue
        for atom in neighbors[carbon] - set(ring):
            if (elements[atom] == "O" and charges[atom] == 0 and len(neighbors[atom]) == 1
                    and order(carbon, atom) == "DOUBLE"):
                distance = min(i, 6 - i)
                if distance in carbonyls or len(neighbors[carbon]) != 3:
                    return None
                carbonyls[distance] = (carbon, atom)
    if set(carbonyls) != {1, 3}:
        return None
    near, far = carbonyls[1], carbonyls[3]
    middle = ring_neighbors[near[0]] & ring_neighbors[far[0]]
    if len(middle) != 1:
        return None
    donor, = middle
    attached = neighbors[donor] - {near[0], far[0]}
    if (elements[donor] != "N" or len(attached) != 1
            or any(order(donor, atom) != "SINGLE" for atom in neighbors[donor])):
        return None
    hydrogen, = attached
    if elements[hydrogen] not in {"H", "D"} or charges[hydrogen] != 0 or neighbors[hydrogen] != {donor}:
        return None
    return {"adenine_N6_acceptor": far[1], "adenine_N1_donor": donor,
            "proximal_carbonyl_oxygen": near[1]}


def _emitted_contacts(record, elements):
    from restraints.builder import pair_residue_from_pdb
    from restraints.phenix import AT_PARALLEL_A, PairResidue, generate_pair_restraints

    identity = SimpleNamespace(get_resname=lambda: record["Ligand code"], has_id=elements.__contains__,
                               id=("", 1, ""), get_parent=lambda: SimpleNamespace(get_id=lambda: "T"))
    pyrimidine = pair_residue_from_pdb([record], identity)
    adenine = PairResidue("A", "2", {a: a for a in AT_PARALLEL_A}, "A")
    phil = generate_pair_restraints(pyrimidine, adenine, planes=False, parallels=False)
    if not phil:
        raise ValueError("NARestraints did not emit the requested canonical pair")
    target = {f"chain T and resid 1 and name {a}": a for a in elements}
    partner = {f"chain A and resid 2 and name {a}": a for a in ("N1", "N6")}
    contacts = {}
    nodes, _ = _parse(phil)
    for node in nodes:
        if node["path"].split(".")[-1] != "bond":
            continue
        selections = {node["fields"].get(f"atom_selection_{n}") for n in (1, 2)}
        pyr, pur = selections & target.keys(), selections & partner.keys()
        if len(pyr) != 1 or len(pur) != 1:
            raise ValueError("An emitted distance did not resolve to one atom on each base")
        key = partner[pur.pop()]
        if key in contacts:
            raise ValueError("Duplicate contact to adenine " + key)
        contacts[key] = target[pyr.pop()]
    if set(contacts) != {"N1", "N6"}:
        raise ValueError("Incomplete emitted pair")
    return contacts, sha256(phil.encode()).hexdigest()


def inspect_at_pair(record, graph, attachment):
    if record.get("Base Analog") != "T":
        return {"status": "OUTSIDE_SCOPE"}
    edge = source_uracil_edge(graph, attachment)
    if edge is None:
        return {"status": "OUTSIDE_SCOPE"}
    expected = {"N1": edge["adenine_N1_donor"], "N6": edge["adenine_N6_acceptor"]}
    report = {"source_atoms_by_adenine_contact": expected,
              "proximal_carbonyl_oxygen": edge["proximal_carbonyl_oxygen"]}
    try:
        emitted, digest = _emitted_contacts(record, graph[0])
    except ValueError as exc:
        return {**report, "status": "RECIPE_UNRESOLVED", "reason": str(exc)}
    return {**report, "status": "AGREES" if emitted == expected else "CONFLICT",
            "narestraints_atoms_by_adenine_contact": emitted, "compiled_phil_sha256": digest}
