"""Descriptive Cartesian geometry from a captured native manager inventory.

These scalar comparisons are deliberately separate from native residuals:
the existing capture does not retain every symmetry/slack/top-out convention.
No target, weight, coordinate, dictionary or qualification gate is changed.
"""
from __future__ import annotations

from collections import Counter
from math import acos, degrees, dist, isfinite, sqrt

CAPTURED_GEOMETRY_POLICY = 'cif-captured-cartesian-geometry-v1'
_KINDS = {'bond_simple': (2, 'distance_ideal', 'angstrom'),
          'angle': (3, 'angle_ideal', 'degree'),
          'chirality': (4, 'volume_ideal', 'angstrom_cubed')}
_DEFERRED = ('bond_asu', 'dihedral', 'const_dihedral', 'planarity', 'parallelity')
_SUGAR = {"C1'", "C2'", "C3'", "C4'", "C5'", "O3'", "O4'", "O5'"}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError('Require a finite recorded number')
    return float(value)


def _point(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('Require three captured Cartesian coordinates')
    return [_number(v) for v in value]


def _subtract(a, b):
    return [x-y for x, y in zip(a, b)]


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _site(atom):
    identity = atom['identity']
    return (identity['chain_id'].strip() or '_') + ':' + identity['resseq'].strip() + identity['icode'].strip()


def _observed(kind, points):
    if kind == 'bond_simple':
        return dist(*points)
    if kind == 'angle':
        a, b = _subtract(points[0], points[1]), _subtract(points[2], points[1])
        length = sqrt(_dot(a, a)*_dot(b, b))
        if length == 0:
            return None
        return degrees(acos(max(-1., min(1., _dot(a, b)/length))))
    a, b, c = [_subtract(p, points[0]) for p in points[1:]]
    cross = [b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0]]
    return _dot(a, cross)


def review_captured_geometry(native: dict) -> dict:
    """Report distances, angles and ordered volumes, never scientific PASS.

    ``nominal_deviation`` is (observed - target) * sqrt(recorded weight),
    using abs(ordered volume) only when the recorded both_signs flag is true.
    It is a ranking aid, not a native energy or a calibrated acceptance test.
    All rows and deferred categories remain visible, including zero weights.
    """
    if (native.get('schema_version') != 1 or native.get('policy_id') != 'cif-native-bundle-inventory-v1'
            or native.get('inventory_detail') != 'linked' or native.get('status') != 'REVIEW'):
        raise ValueError('Require a completed detailed native inventory')
    geometry = native['geometry']; atoms = native['atoms']
    if geometry.get('status') != 'RECORDED' or native.get('atom_count') != len(atoms):
        raise ValueError('Incomplete captured geometry inventory')
    coords = [_point(p) for p in geometry['sites_cart_exact']]
    if len(coords) != len(atoms) or len({a['label'] for a in atoms}) != len(atoms):
        raise ValueError('Captured atom identities and geometry sites disagree')
    for i, atom in enumerate(atoms):
        if type(atom['i_seq']) is not int or atom['i_seq'] != i or max(abs(x-y) for x, y in zip(_point(atom['xyz']), coords[i])) > 1e-9:
            raise ValueError('Captured atom ordering or coordinates differ from manager sites')
    details, counts = geometry['proxy_details'], geometry['proxy_counts']
    measurements = {}; summaries = {}
    for kind, (size, target_field, unit) in _KINDS.items():
        proxies = details.get(kind)
        if not isinstance(proxies, list) or counts.get(kind) != len(proxies):
            raise ValueError('Captured proxy detail/count mismatch: ' + kind)
        rows = []
        for index, proxy in enumerate(proxies):
            indices = proxy['i_seqs']
            if (len(indices) != size or any(type(i) is not int or not 0 <= i < len(atoms) for i in indices)
                    or proxy['atoms'] != [atoms[i]['label'] for i in indices]):
                raise ValueError('Captured proxy endpoint identity mismatch: ' + kind)
            row = {'proxy_index': index, 'i_seqs': list(indices), 'atoms': list(proxy['atoms']),
                   'sites': sorted({_site(atoms[i]) for i in indices}),
                   'contains_sugar_atoms': any(atoms[i]['atom_id'] in _SUGAR for i in indices),
                   'origin_id': proxy.get('origin_id'), 'unit': unit,
                   'comparison_scope': 'CAPTURED_CARTESIAN_ENDPOINTS', 'status': 'MEASURED',
                   'observed': None, 'target': proxy.get(target_field), 'weight': proxy.get('weight'),
                   'difference': None, 'nominal_deviation': None, 'sign_agreement': None,
                   'native_residual': 'UNASSESSED'}
            if kind == 'bond_simple' and proxy.get('symmetry_operation') not in (None, 'x,y,z'):
                row.update(status='UNSUPPORTED', reason='Nonidentity bond symmetry needs native evaluation')
                rows.append(row); continue
            if kind == 'chirality' and type(proxy.get('both_signs')) is not bool:
                row.update(status='UNSUPPORTED', reason='Native both_signs convention unavailable')
                rows.append(row); continue
            observed = _observed(kind, [coords[i] for i in indices])
            row['observed'] = observed
            if observed is None:
                row.update(status='DEGENERATE', reason='Coincident angle endpoints')
                rows.append(row); continue
            _number(observed)
            for value in (row['target'], row['weight']):
                if isinstance(value, float) and not isfinite(value):
                    raise ValueError('Nonfinite captured proxy field')
            try:
                target = _number(row['target'])
                if (kind == 'bond_simple' and target <= 0) or (kind == 'angle' and not 0 <= target <= 180):
                    raise ValueError('Invalid scalar target')
                compared = abs(observed) if kind == 'chirality' and proxy['both_signs'] else observed
                row['difference'] = compared-target
                if kind == 'chirality':
                    row['both_signs'] = proxy['both_signs']
                    if not proxy['both_signs'] and target != 0 and observed != 0:
                        row['sign_agreement'] = (observed > 0) == (target > 0)
                weight = _number(row['weight'])
                if weight < 0:
                    row.update(status='INVALID_PROXY', reason='Negative recorded weight')
                elif weight == 0:
                    row.update(status='UNWEIGHTED', reason='Zero recorded weight; no nominal deviation')
                else:
                    row['nominal_deviation'] = row['difference'] * sqrt(weight)
                if kind == 'chirality' and observed == 0:
                    row.update(status='DEGENERATE', reason='Zero ordered Cartesian volume')
                if kind == 'bond_simple' and observed == 0:
                    row.update(status='DEGENERATE', reason='Coincident bond endpoints')
            except ValueError as exc:
                row.update(status='UNSUPPORTED', reason=str(exc))
            rows.append(row)
        measurements[kind] = rows
        ranked = sorted((r for r in rows if r['nominal_deviation'] is not None),
                        key=lambda r: (-abs(r['nominal_deviation']), r['proxy_index']))
        summaries[kind] = {
            'captured_proxies': len(rows), 'status_counts': dict(Counter(r['status'] for r in rows)),
            'nominal_abs_ge_3': sum(abs(r['nominal_deviation']) >= 3 for r in ranked),
            'nominal_abs_ge_5': sum(abs(r['nominal_deviation']) >= 5 for r in ranked),
            'sign_conflicts': sum(r['sign_agreement'] is False for r in rows),
            'worst': ranked[:10]}
    deferred = {}
    for kind in _DEFERRED:
        rows = details.get(kind); count = counts.get(kind)
        if isinstance(rows, list) and count != len(rows):
            raise ValueError('Captured deferred proxy detail/count mismatch: ' + kind)
        deferred[kind] = {'count': count, 'status': 'UNASSESSED',
                          'reason': 'Requires separate native convention and geometry qualification'}
    return {'schema_version': 1, 'audit_kind': 'cif_captured_cartesian_geometry_review',
            'policy_id': CAPTURED_GEOMETRY_POLICY, 'status': 'REVIEW', 'analysis_completed': True,
            'atom_count': len(atoms), 'measurements': measurements, 'summary': summaries,
            'deferred_proxy_kinds': deferred, 'native_execution': 'NOT_RUN',
            'native_residuals': 'UNASSESSED', 'absolute_stereochemistry': 'UNASSESSED',
            'sugar_pucker': 'UNASSESSED', 'complete_geometry_qualification': 'NOT_RUN',
            'model_editing': 'NOT_RUN', 'optimization': 'NOT_RUN', 'refinement': 'NOT_RUN',
            'scientific_approval': 'NOT_RUN', 'automatic_adoption': False,
            'limitations': [
                'Scalar Cartesian comparisons only; no symmetry inference for angle/chirality endpoints.',
                'The capture lacks some symmetry, slack and top-out fields; nominal deviations are not native residuals.',
                'Threshold counts at 3 and 5 are descriptive ranking aids, not scientific acceptance gates.',
                'Ordered-volume sign agreement is relative to the captured proxy, not independent absolute stereochemistry.',
                'Deferred categories, source chemistry, formal charges, pucker and experimental evidence remain open.']}
