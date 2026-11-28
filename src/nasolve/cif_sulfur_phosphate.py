"""Identify the roles declared around source P–S centres without assigning a polymer product."""
from .cif_linked_preparation import atom_rows
from .cif_stereochemistry_audit import _graph, _stereo


def source_sulfur_phosphates(values, phosphorus_atoms):
    """Read validated P–S centres. A carbon-linked oxygen need not belong to a sugar."""
    if not phosphorus_atoms:
        return []
    try:
        atoms = atom_rows(values)
        elements, bonds, charges, neighbors = _graph(values)
        stereo = _stereo(values)
    except ValueError as exc:
        return [dict(phosphorus=p, status="INCOMPLETE_SOURCE_DECLARATIONS", reason=str(exc))
                for p in phosphorus_atoms]

    result = []
    for p in phosphorus_atoms:
        adjacent = {}
        for name in sorted(neighbors[p]):
            others = sorted(neighbors[name] - {p})
            adjacent[name] = dict(element=elements[name], bond_order=bonds[tuple(sorted((p, name)))],
                                  formal_charge=charges[name], leaving=atoms[name].get("pdbx_leaving_atom_flag"),
                                  hydrogens=[a for a in others if elements[a] in {"H", "D"}],
                                  other_heavy_neighbors=[a for a in others if elements[a] not in {"H", "D"}])
        row = dict(phosphorus=p, source_stereo=stereo[p], neighbors=adjacent)
        sulfur = [a for a, v in adjacent.items() if v["element"] == "S"]
        oxygen = [a for a, v in adjacent.items() if v["element"] == "O"]
        if len(sulfur) != 1:
            row["status"] = "MULTIPLE_SULFURS"
        elif adjacent[sulfur[0]]["other_heavy_neighbors"]:
            row["status"] = "BRIDGING_SULFUR"
        else:
            carbon = [a for a in oxygen if [elements[n] for n in adjacent[a]["other_heavy_neighbors"]] == ["C"]
                      and adjacent[a]["bond_order"] == "SINGLE" and adjacent[a]["leaving"] == "N"]
            terminal = [a for a in oxygen if not adjacent[a]["other_heavy_neighbors"]]
            leaving = [a for a in terminal if adjacent[a]["leaving"] == "Y"]
            kept = [a for a in terminal if adjacent[a]["leaving"] == "N"]
            row["status"] = "UNRESOLVED_SOURCE_ROLES"
            if (len(adjacent) == 4 and len(carbon) == len(leaving) == len(kept) == 1
                    and adjacent[sulfur[0]]["leaving"] == "N"):
                row.update(status="SOURCE_ROLES_IDENTIFIED",
                           roles=dict(sulfur=sulfur[0], retained_oxygen=kept[0],
                                      leaving_oxygen=leaving[0], carbon_linked_oxygen=carbon[0]))
        result.append(row)
    return result
