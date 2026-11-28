"""Recover a measured parent chi on an isolated, source-bound Coot monomer."""
from copy import deepcopy
from inspect import getsource
import math

from . import cif_base_rotation_audit as rotation
from .cif_base_rotation_audit import rotate_group


def named_rotation_scope(graph, elements, bonds, neighbors):
    """Include the complete base side of the single cut, including its H/D atoms."""
    fragment = set(graph["fragment_atoms"])
    moving = set(fragment)
    for name, element in elements.items():
        if element not in {"H", "D"}:
            continue
        partners = neighbors[name]
        if len(partners) != 1:
            return None
        partner = next(iter(partners))
        if elements[partner] in {"H", "D"} or bonds[tuple(sorted((name, partner)))] != "SINGLE":
            return None
        if partner in fragment:
            moving.add(name)
    return {"elements": elements, "moving_atoms": sorted(moving)}


def nasolve_monomer_atoms(coot_api, molecule, elements):
    """Read every atom by its literal Coot name in the one isolated monomer."""
    atoms = {}
    for row in coot_api.residue_info_py(molecule, "A", 1, ""):
        label, alt = row[0]
        name = label.strip()
        point = row[2]
        if (alt.strip() or name in atoms or elements.get(name) != row[1][2].strip().upper()
                or len(point) != 3 or not all(type(x) in (int, float) and math.isfinite(x) for x in point)):
            raise RuntimeError("Coot monomer differs from the source atoms for named chi recovery")
        atoms[name] = (label, alt, deepcopy(row[1]), list(point))
    heavy = {name for name, element in elements.items() if element not in {"H", "D"}}
    if not heavy.issubset(atoms):
        raise RuntimeError("Coot monomer is missing source heavy atoms for named chi recovery")
    return atoms


def nasolve_recover_named_chi(coot_api, molecule, expected, observed, names, scope, site):
    if not all(callable(getattr(coot_api, fn, None)) for fn in ("residue_info_py", "set_atom_attributes_py")):
        raise RuntimeError("Coot did not preserve the parent chi and lacks named coordinate recovery at " + site)
    original = nasolve_monomer_atoms(coot_api, molecule, scope["elements"])
    indices = {name: i for i, name in enumerate(original)}
    moving = set(scope["moving_atoms"]).intersection(original)
    group = {
        "i_seqs": sorted(indices[name] for name in moving),
        "origin_index": indices[names[1]],
        "attachment_index": indices[names[2]],
    }
    change = (expected - observed + 180.0) % 360.0 - 180.0
    targets = rotate_group([row[3] for row in original.values()], group, math.radians(change))
    edits = []
    for name in sorted(moving - {names[2]}):
        label, alt, _, _ = original[name]
        for axis, value in zip("xyz", targets[indices[name]]):
            edits.append([molecule, "A", 1, "", label, alt, axis, value])
    coot_api.set_atom_attributes_py(edits)
    actual = nasolve_monomer_atoms(coot_api, molecule, scope["elements"])
    if actual.keys() != original.keys() or any(actual[n][:3] != row[:3] for n, row in original.items()):
        raise RuntimeError("Coot changed atom identity, occupancy or displacement during named chi recovery")
    for name, row in actual.items():
        if name not in moving or name == names[2]:
            if row[3] != original[name][3]:
                raise RuntimeError("Coot moved a protected atom during named chi recovery")
        elif math.dist(row[3], targets[indices[name]]) > 0.0001:
            # Coot stores coordinates as floats. Verify the actual written point to 0.0001 Å.
            raise RuntimeError("Coot did not realize the named rigid rotation at " + site)
    print("NASOLVE_NAMED_CHI_RECOVERY", site, observed, expected, change, len(moving) - 1, flush=True)


def native_rotation_helpers():
    """Freeze the same Cartesian arithmetic in the self-contained native script."""
    functions = (rotation._norm, rotation._cross, rotation._finite, rotation._axis,
                 rotate_group, nasolve_monomer_atoms, nasolve_recover_named_chi)
    lines = ["from copy import deepcopy"]
    for function in functions:
        lines.extend(getsource(function).splitlines())
    return lines
