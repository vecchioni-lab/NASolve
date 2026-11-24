"""Construct a separate Cartesian starting template for one explicit alkynyl methyl."""
from copy import deepcopy
from math import dist, isclose, isfinite
import re

from .cif_linear_bond_reference import linear_bond_query, _source_energy_types
from .cif_stereochemistry_audit import _coordinates, _graph, _stereo
from .cif_triple_bond_audit import _numeric, _rows
from .ligand_profiles import _blocks


_ATOM = "_chem_comp_atom."
_AXES = tuple(_ATOM + axis for axis in "xyz")
# Cartesian positions are written with six decimals in Angstroms.
_PRECISION_A = 2e-6


def _methyl_group(snapshot, code, values):
    query = linear_bond_query(snapshot, code)
    types = _source_energy_types(query)
    elements, orders, _, neighbors = _graph(values)
    stereo = _stereo(values)
    groups = []
    for left, right in query["selected_bonds"]:
        for center, tip in ((left, right), (right, left)):
            if types.get(center) != "CSP" or types.get(tip) != "CH3":
                continue
            distal, = neighbors[center] - {tip}
            attached = neighbors[tip] - {center}
            if elements[distal] == "C" and all(elements[n] == "H" for n in attached):
                groups.append((center, tip, sorted({tip, *attached})))
    if len(groups) != 1:
        raise ValueError("Require one neutral terminal methyl on an explicit carbon–carbon triple bond")
    center, tip, moved = groups[0]
    ids = values[_ATOM + "atom_id"]
    if any(stereo[n] in {"R", "S"} for n in (center, *moved)):
        raise ValueError("The selected group has a declared stereocenter")
    for key, column in values.items():
        if key.startswith("_chem_comp_chir.atom_id") and set(moved).intersection(column):
            raise ValueError("The selected methyl participates in a declared chiral volume")
        if key.startswith(_ATOM) and ("isotope" in key or "mass_number" in key):
            if any(column[ids.index(n)] not in {"?", ".", "0"} for n in moved):
                raise ValueError("The selected methyl has an explicit isotope declaration")
    return center, tip, moved, orders


def _replace_coordinate_tokens(text, block, changes):
    """Replace only three values in each uniquely located, parsed CIF atom row."""
    columns = [key for key in block if key.lower().startswith(_ATOM)]
    ids = block[next(key for key in columns if key.lower() == _ATOM + "atom_id")]
    replacements = []
    for atom, position in changes.items():
        row = ids.index(atom)
        fields = []
        for key in columns:
            value = block[key][row]
            literal = re.escape(value)
            token = "(?:" + "|".join((literal, "'" + literal + "'", '"' + literal + '"')) + ")"
            if key.lower() in _AXES:
                if "(" in value:
                    raise ValueError("A Cartesian coordinate has an explicit uncertainty")
                token = "(?P<" + key[-1].lower() + ">" + token + ")"
            fields.append(token)
        matches = list(re.finditer(r"(?<!\S)" + r"\s+".join(fields) + r"(?!\S)", text))
        if len(matches) != 1:
            raise ValueError("Cannot locate one unambiguous Cartesian atom row for " + atom)
        match = matches[0]
        for axis, updated in zip("xyz", position):
            start, stop = match.span(axis)
            if text[start] in {"'", '"'}:
                start += 1
                stop -= 1
            replacements.append((start, stop, updated))
    for start, stop, value in sorted(replacements, reverse=True):
        text = text[:start] + value + text[stop:]
    return text


def prepare_template(snapshot, candidate, blocks, assessment):
    """Prepare and independently check the candidate before the caller publishes it."""
    components = assessment["components"]
    if len(components) != 1 or components[0]["verdicts"]["graph"] != "PASS":
        raise ValueError("Require one graph-valid component for the terminal methyl recipe")
    item = components[0]
    block, = (b.values for b in blocks if b.values["data_"] == item["block"])
    values = {key.lower(): column for key, column in block.items()}
    center, tip, moved, bonds = _methyl_group(snapshot, item["component_id"], values)
    for entry in blocks:
        for key, column in entry.values.items():
            category, _, field = key.lower().partition(".")
            if category in {"_chem_link_bond", "_chem_mod_bond", "_chem_mod_atom"}:
                if field.startswith(("atom_id", "new_atom_id")) and set(moved).intersection(column):
                    raise ValueError("A declared link or residue modification refers to the methyl group")
    family, xyz = _coordinates(values, source=False)
    ids = values[_ATOM + "atom_id"]
    leaving = values.get(_ATOM + "pdbx_leaving_atom_flag")
    if leaving and any(leaving[ids.index(n)].upper() == "Y" for n in moved):
        raise ValueError("The selected group includes a declared leaving atom")
    if family != "RESTRAINT_CARTESIAN" or set(xyz) != set(ids):
        raise ValueError("Require a complete set of restraint Cartesian starting positions")
    rows = [r for r in _rows(values, "bond", 2) if set(r["atoms"]) == {center, tip}]
    if len(rows) != 1:
        raise ValueError("Require one numerical target for the methyl bond")
    target = _numeric(rows[0].get("value_dist"))
    esd = _numeric(rows[0].get("value_dist_esd"))
    start = dist(xyz[center], xyz[tip])
    if target is None or esd is None or not 0 < esd < target or not isfinite(start) or start == 0:
        raise ValueError("Require a positive bond target, uncertainty and starting direction")
    changes = {}
    if not isclose(start, target, abs_tol=_PRECISION_A, rel_tol=0):
        shift = [(b-a) * (target/start-1) for a, b in zip(xyz[center], xyz[tip])]
        changes = {n: [f"{v+d:.6f}" for v, d in zip(xyz[n], shift)] for n in moved}
    text = _replace_coordinate_tokens(snapshot.read_bytes().decode("utf-8"), block, changes)
    candidate.write_bytes(text.encode("utf-8"))
    expected = deepcopy(block)
    fields = {key.lower(): key for key in expected}
    for n, position in changes.items():
        for key, value in zip(_AXES, position):
            expected[fields[key]][ids.index(n)] = value
    actual = [b.values for b in _blocks(candidate)]
    if actual != [expected if b.values is block else b.values for b in blocks]:
        raise ValueError("The candidate changed fields outside the four Cartesian positions")
    _, updated = _coordinates({k.lower(): v for k, v in expected.items()}, source=False)
    for left, right in bonds:
        expected_length = target if {left, right} == {center, tip} else dist(xyz[left], xyz[right])
        if not isclose(dist(updated[left], updated[right]), expected_length, abs_tol=_PRECISION_A, rel_tol=0):
            raise ValueError("The candidate did not preserve the other template bonds")
    event = dict(component=item["component_id"], coordinate_family=family, bond=[center, tip],
                 moved_atoms=sorted(changes), starting_A=start, candidate_A=dist(updated[center], updated[tip]),
                 target_A=target, esd_A=esd)
    return [dict(atom=n, before=xyz[n], after=updated[n]) for n in sorted(changes)], [event]
