"""Observed sticky-end contact geometry; no restraints or model edits are made.

The canonical NARestraints recipes are references for descriptive residuals,
not calibrated acceptance thresholds or evidence of hydrogen positions.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path

from .topostitch_coordinates import (
    _CANONICAL, _Unassessed, _dot, _plane, _read_atoms, _residue, _sub,
    inspect_end_assignments,
)
from .topostitch_periodic import _crystal, inspect_periodic_end_assignments


def _canonical_catalog():
    """Snapshot the effective installed role maps and canonical recipe tables."""
    try:
        from restraints import phenix
        from restraints.recipe_library import recipe_for
        from restraints.residue_library import load_residue_records
        library_version = version('NARestraints')
    except ImportError as exc:
        raise RuntimeError('Contact inspection requires the NARestraints dependency of NASolve') from exc
    records = load_residue_records()
    recipes = {}
    roles = {}
    for name, categories in (('AT', 'AT'), ('GC', 'GC')):
        recipe = recipe_for(*categories)
        if (recipe is None or recipe.name != name or recipe.noncanonical
                or recipe.role1_categories != frozenset(categories[0])
                or recipe.role2_categories != frozenset(categories[1])):
            raise ValueError('NARestraints canonical recipe roles are incompatible')
        recipes[name] = {
            'bonds': [list(row) for row in getattr(phenix, name+'_BONDS')],
            'angles': [list(row) for row in getattr(phenix, name+'_ANGLE_RESTRAINTS')],
        }
        for kind, size in (('bonds', 2), ('angles', 3)):
            for row in recipes[name][kind]:
                if (len(row) != size+2 or any(not isinstance(r, str) or len(r.split('.')) != 2
                                            or r.split('.')[0] not in categories for r in row[:size])
                        or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
                               for v in row[size:])):
                    raise ValueError('Invalid NARestraints canonical geometry table')
                for ref in row[:size]:
                    category, atom_role = ref.split('.')
                    roles.setdefault(category, set()).add(atom_role)
    mapping = {}
    for code, category in _CANONICAL.items():
        matches = [r for r in records if r.get('Ligand code') == code]
        if len(matches) != 1 or matches[0].get('Base Analog') != category:
            raise ValueError(f'NARestraints must provide one canonical role record for {code}')
        mapping[code] = {}
        for role in sorted(roles[category]):
            name = matches[0].get(role)
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 4:
                raise ValueError(f'NARestraints lacks a valid {code}.{role} atom mapping')
            mapping[code][role] = name.strip()
    effective = {'atom_roles': mapping, 'recipes': recipes}
    digest = sha256(json.dumps(effective, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'name': 'NARestraints', 'version': library_version,
            'effective_catalog': effective, 'effective_catalog_sha256': digest}


def _angle(points):
    a, b = _sub(points[0], points[1]), _sub(points[2], points[1])
    product = math.hypot(*a)*math.hypot(*b)
    if product < 1e-12:
        return None
    return math.degrees(math.acos(max(-1., min(1., _dot(a, b)/product))))


def _measure(row, kind, category_sites, atom_inventory, mapping, transform):
    references, ideal, sigma = row[:-2], row[-2], row[-1]
    points, atoms, issues = [], [], []
    for ref in references:
        category, role = ref.split('.')
        end_id, site, code, image = category_sites[category]
        name = mapping[code][role]
        identity = {'end_id': end_id, 'site': asdict(site), 'residue_code': code,
                    'canonical_role': role, 'atom_name': name, 'image': image}
        atoms.append(identity)
        # The coordinate adapter already ruled out duplicate sites/conformers.
        rows = next(iter(atom_inventory[site].values()))
        matches = [r for r in rows if r[0] == name]
        reason = None
        if len(matches) != 1:
            reason = 'MISSING_ATOM' if not matches else 'AMBIGUOUS_ATOM'
        elif matches[0][4] is None or not math.isfinite(matches[0][4]) or not 0 < matches[0][4] <= 1:
            reason = 'UNUSABLE_OCCUPANCY'
        if reason:
            issues.append({'code': reason, 'atom': identity})
        else:
            xyz = matches[0][3]
            points.append(transform(xyz) if image == 'target' else xyz)
    observed = None
    if not issues:
        observed = math.dist(*points) if kind == 'bonds' else _angle(points)
        if observed is None:
            issues.append({'code': 'DEGENERATE_ANGLE'})
        elif not math.isfinite(observed):
            observed = None
            issues.append({'code': 'NONFINITE_MEASUREMENT'})
    return {'atoms': atoms, 'observed': observed, 'reference_ideal': ideal,
            'reference_sigma': sigma, 'deviation': None if observed is None else observed-ideal,
            'units': 'angstrom' if kind == 'bonds' else 'degrees', 'issues': issues}


def _planes(left, right, transform):
    try:
        a, na, ra = _plane(left)
        b, nb, rb = _plane({name: transform(xyz) for name, xyz in right.items()})
        delta = _sub(b, a)
        return {'normal_angle_degrees': math.degrees(math.acos(min(1., abs(_dot(na, nb))))),
                'center_separation_angstrom': math.hypot(*delta),
                'absolute_plane_offsets_angstrom': [abs(_dot(delta, na)), abs(_dot(delta, nb))],
                'ring_plane_rms_angstrom': [ra, rb], 'issues': []}
    except _Unassessed as exc:
        return {'normal_angle_degrees': None, 'center_separation_angstrom': None,
                'absolute_plane_offsets_angstrom': None, 'ring_plane_rms_angstrom': None,
                'issues': [{'code': exc.code}]}


def inspect_end_contacts(model_path: Path, assignments, *, expected_sha256: str,
                         max_distance_angstrom: float, periodic: bool = False,
                         max_pairs: int = 100_000, max_image_tests: int = 100_000) -> dict:
    """Add observed recipe contacts to a fresh source-verified proposal report.

    All image transforms come from this call's periodic search, never a supplied
    report. Missing contact atoms keep a candidate visible with incomplete
    measurements. No distance/angle threshold chooses or approves a connection.
    """
    if type(periodic) is not bool:
        raise ValueError('periodic must be a boolean')
    assignments = tuple(assignments)
    options = dict(expected_sha256=expected_sha256, max_distance_angstrom=max_distance_angstrom,
                   max_pairs=max_pairs)
    if periodic:
        report = inspect_periodic_end_assignments(model_path, assignments,
                                                  max_image_tests=max_image_tests, **options)
        screen = report['periodic_screening']
        gemmi, cell, _ = _crystal(screen['inputs']['cell_parameters'], screen['inputs']['space_group'])
    else:
        report = inspect_end_assignments(model_path, assignments, **options)
        screen = report['screening']
    data = Path(model_path).read_bytes()
    if sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Source model checksum changed during contact inspection')
    inventory = _read_atoms(data)
    library = _canonical_catalog()
    catalog = library['effective_catalog']
    by_id = {a.end_id: a for a in assignments}
    observations = []
    for index, edge in enumerate(screen['candidates']):
        left, right = (by_id[e] for e in edge['ends'])
        if periodic:
            op = gemmi.Op(edge['target_image']['operator_xyz'])
            def transform(xyz):
                fractional = cell.fractionalize(gemmi.Position(*xyz))
                point = cell.orthogonalize(gemmi.Fractional(*op.apply_to_xyz(list(fractional))))
                return (point.x, point.y, point.z)
        else:
            def transform(xyz):
                return xyz
        pairs = []
        for i, j in edge['residue_pairs']:
            a, b = left.overhang_sites[i], right.overhang_sites[j]
            ca, aa = _residue(inventory, a)
            cb, ab = _residue(inventory, b)
            recipe = 'AT' if {ca, cb} == {'A', 'T'} else 'GC'
            category_sites = {ca: (left.end_id, a, 'D'+ca, 'source'),
                              cb: (right.end_id, b, 'D'+cb, 'target')}
            entry = {'overhang_indices': [i, j], 'sites': [asdict(a), asdict(b)], 'recipe': recipe}
            for kind in ('bonds', 'angles'):
                entry[kind] = [_measure(row, kind, category_sites, inventory, catalog['atom_roles'], transform)
                               for row in catalog['recipes'][recipe][kind]]
            entry['plane_observation'] = _planes(aa, ab, transform)
            incomplete = any(v['issues'] for kind in ('bonds', 'angles') for v in entry[kind])
            incomplete = incomplete or bool(entry['plane_observation']['issues'])
            entry['assessment'] = 'INCOMPLETE_MEASUREMENTS' if incomplete else 'MEASURED_NOT_VALIDATED'
            pairs.append(entry)
        observations.append({'candidate_index': index, 'ends': edge['ends'],
                             'target_image': edge.get('target_image'), 'residue_pairs': pairs})
    report['contact_assessment'] = {
        'schema_version': 1, 'kind': 'topostitch-contact-observations',
        'source_model_sha256': expected_sha256, 'source_bytes_verified': True,
        'library': library, 'candidates': observations, 'acceptance_evaluated': False,
        'geometry_validated': False, 'runtime_authority': False,
        'limitations': ['Canonical full-overhang contacts only; topology remains caller-declared',
                        'Recipe ideals/sigmas are reference values, not acceptance cutoffs',
                        'No hydrogen positions, stacking, torsion, clash or diffraction validation',
                        'No model edits, new covalent bonds or checkpoint selection'],
    }
    return report
