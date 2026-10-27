"""Read-only coordinate previews keyed by recipe node and restraint IDs.

Resolved means addressable and numerically specified in this supplied inventory.
It never means native-qualified, chemically approved or selected as a checkpoint.
"""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Mapping

from .binding import Atom, AtomKey, ModelSnapshot, ResidueKey, RoleMap
from .recipe import Recipe, RecipeError, digest


def _measurement(kind: str, atoms: list[Atom]) -> tuple[float | None, list[str]]:
    if len({a.key for a in atoms}) != len(atoms):
        return None, ['same_atom_endpoints']
    if kind == 'distance':
        value = math.dist(atoms[0].xyz, atoms[1].xyz)
        return (value, []) if math.isfinite(value) else (None, ['nonfinite_geometry'])
    first, center, last = (a.xyz for a in atoms)
    u = tuple(a - b for a, b in zip(first, center))
    v = tuple(a - b for a, b in zip(last, center))
    nu, nv = math.hypot(*u), math.hypot(*v)
    if not math.isfinite(nu) or not math.isfinite(nv):
        return None, ['nonfinite_geometry']
    if nu == 0 or nv == 0:
        return None, ['undefined_angle']
    u, v = tuple(x / nu for x in u), tuple(x / nv for x in v)
    cross = (u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0])
    value = math.degrees(math.atan2(math.hypot(*cross), sum(x*y for x, y in zip(u, v))))
    return value, []


def preview(recipe: Recipe, *, model: ModelSnapshot, roles: RoleMap | None = None,
            residue_slots: Mapping[str, ResidueKey], atom_bindings: Mapping[str, AtomKey]) -> dict:
    """Resolve one recipe without file I/O, coordinate edits or native execution.

    Blank alternate IDs match only blank alternates. Symmetry mates are retained
    as explicit identities but are unsupported until a qualified transform adapter
    exists. Missing donors/placeholders are row diagnostics, not global exceptions.
    Malformed caller bindings are rejected rather than silently discarded.
    """
    if not isinstance(recipe, Recipe) or not isinstance(model, ModelSnapshot):
        raise RecipeError('Preview requires a Recipe and ModelSnapshot')
    if roles is not None and not isinstance(roles, RoleMap):
        raise RecipeError('Preview roles must be a RoleMap')
    if not isinstance(residue_slots, Mapping) or not isinstance(atom_bindings, Mapping):
        raise RecipeError('Require explicit binding mappings')
    residues, concrete = dict(residue_slots), dict(atom_bindings)
    doc = recipe.to_dict()
    allowed_slots = {n['residue_slot'] for n in doc['nodes'] if n['kind'] == 'donor'}
    allowed_atoms = {n['id'] for n in doc['nodes'] if n['kind'] != 'donor'}
    if residues.keys() - allowed_slots:
        raise RecipeError('Unknown residue binding')
    if concrete.keys() - allowed_atoms:
        raise RecipeError('Unknown atom binding; donor nodes require explicit role resolution')
    if any(type(r) is not ResidueKey for r in residues.values()):
        raise RecipeError('Residue slots require exact ResidueKey values')
    if any(type(a) is not AtomKey for a in concrete.values()):
        raise RecipeError('Atom bindings require exact AtomKey values')

    inventory: dict[AtomKey, list[Atom]] = defaultdict(list)
    for atom in model.atoms:
        inventory[atom.key].append(atom)
    bound: dict[str, Atom] = {}
    node_rows = []
    for node in doc['nodes']:
        row = {'node_id': node['id'], 'kind': node['kind'],
               'scope': 'concrete_only' if node['kind'] == 'atom' else 'logical_slot',
               'atom': None, 'issues': []}
        key = None
        if node['kind'] == 'donor':
            row.update(role=node['role'], residue_slot=node['residue_slot'], role_resolution=None)
            residue = residues.get(node['residue_slot'])
            if residue is None:
                row['issues'].append('missing_residue_binding')
            elif roles is None:
                row['issues'].append('missing_role_map')
            else:
                name, proof, issues = roles.resolve(residue.component_id, node['role'])
                row['role_resolution'] = proof
                row['issues'].extend(issues)
                if name is not None:
                    key = AtomKey(**residue.to_dict(), atom_name=name)
        else:
            key = concrete.get(node['id'])
            if node['kind'] == 'metal':
                row['requested_element'] = node['element']
            if key is None:
                row['issues'].append('missing_atom_binding')
        row['requested_key'] = key.to_dict() if key is not None else None
        if key is not None:
            matches = inventory.get(key, [])
            if key.symmetry != 'x,y,z':
                row['issues'].append('unsupported_symmetry')
            elif not matches:
                row['issues'].append('missing_atom')
            elif len(matches) != 1:
                row['issues'].append('ambiguous_atom')
            else:
                atom = matches[0]
                row['atom'] = atom.to_dict()
                if node['kind'] == 'metal' and node['element'] != atom.element:
                    row['issues'].append('metal_element_mismatch')
                else:
                    bound[node['id']] = atom
        row['status'] = 'incomplete' if row['issues'] else 'resolved'
        node_rows.append(row)

    sets = {s['id']: s for s in doc['sets']}
    restraint_rows = []
    for restraint in doc['restraints']:
        enabled = restraint['enabled'] and sets[restraint['set_id']]['enabled']
        issues = []
        measured = None
        unresolved = [n for n in restraint['nodes'] if n not in bound]
        if unresolved:
            issues.append('unresolved_nodes')
        else:
            measured, geometry_issues = _measurement(restraint['kind'], [bound[n] for n in restraint['nodes']])
            issues.extend(geometry_issues)
        for field in ('target', 'sigma', 'source'):
            if restraint[field] is None:
                issues.append('missing_' + field)
        restraint_rows.append({
            'restraint_id': restraint['id'], 'set_id': restraint['set_id'],
            'kind': restraint['kind'], 'node_ids': restraint['nodes'], 'enabled': enabled,
            'unit': restraint['unit'], 'measured': measured, 'target': restraint['target'],
            'sigma': restraint['sigma'], 'source': restraint['source'], 'issues': issues,
            'unresolved_node_ids': unresolved,
            'status': 'disabled' if not enabled else ('incomplete' if issues else 'resolved'),
        })
    active = [r for r in restraint_rows if r['enabled']]
    inputs = {
        'recipe': doc, 'recipe_sha256': recipe.sha256,
        'model': model.to_dict(), 'model_inventory_sha256': model.fingerprint,
        'roles': roles.to_dict() if roles is not None else None,
        'role_map_sha256': roles.fingerprint if roles is not None else None,
        'residue_slots': {k: residues[k].to_dict() for k in sorted(residues)},
        'atom_bindings': {k: concrete[k].to_dict() for k in sorted(concrete)},
    }
    return {
        'kind': 'metal-restraint-preview', 'schema_version': 1,
        'protocol': 'metal-coordinate-preview-v1', 'native_ready': False,
        'qualification': 'caller-supplied coordinate inventory; no native or chemistry qualification',
        'status': 'draft' if not active else ('resolved' if all(r['status'] == 'resolved' for r in active) else 'incomplete'),
        'input_sha256': digest({'protocol': 'metal-coordinate-preview-v1', 'inputs': inputs}),
        'inputs': inputs, 'nodes': node_rows, 'restraints': restraint_rows,
    }
