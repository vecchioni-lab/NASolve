"""Canonical, descriptive simple-step twist for explicitly assigned DNA pairs.

Reference geometry: Olson et al., JMB313 (2001), Table1,
https://doi.org/10.1006/jmbi.2001.4987.
Convention: Lu & Olson; Li et al. (2019), https://doi.org/10.1093/nar/gkz394;
3DNA analyze.c at43eafa8407be1a8292e38ca995ab16adfbeffcac, lines237–247.
Fit canonical rings, orient each pair normal toward the next pair origin,
project C1′ directions, untilt the normals, then take the signed angle.
No axis-radius inference, contact assignment, rebuilding or scientific approval.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import math
from pathlib import Path

from .helical_geometry import _site_atom, inspect_phosphate_spans
from .topostitch_coordinates import _read_atoms
from .topostitch_recipe import recipe_digest

METHOD = 'declared-canonical-simple-step-twist-v1'
_NAMES = ('N1', 'C2', 'N3', 'C4', 'C5', 'C6', 'N7', 'C8', 'N9')
_REFERENCE = {
 'DA': ((-.668,.532,0),(-1.912,1.023,0),(-2.320,2.290,0),(-1.267,3.124,0),(.071,2.771,0),(.369,1.398,0),(.877,3.902,0),(.024,4.897,0),(-1.291,4.498,0)),
 'DG': ((-.700,.641,0),(-1.999,1.087,0),(-2.342,2.364,.001),(-1.265,3.177,0),(.071,2.833,0),(.424,1.460,0),(.870,3.969,0),(.023,4.962,0),(-1.289,4.551,0)),
 'DC': ((-1.285,4.542,0),(-1.472,3.158,0),(-.391,2.344,0),(.837,2.868,0),(1.056,4.275,0),(-.023,5.068,0)),
 'DT': ((-1.284,4.500,0),(-1.462,3.135,0),(-.298,2.407,0),(.994,2.897,0),(1.106,4.338,0),(-.024,5.057,0)),
}
_EPS = 1e-8  # Numerical orientation guard, not a biological acceptance cutoff.


class _Unavailable(ValueError):
    pass


def _sub(a, b):
    return tuple(x-y for x,y in zip(a,b))


def _dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _unit(v, reason):
    n = math.hypot(*v)
    if not math.isfinite(n) or n <= _EPS:
        raise _Unavailable(reason)
    return tuple(x/n for x in v)


def _rotate(v, axis, angle):
    cross, dot = _cross(axis, v), _dot(axis, v)
    c, s = math.cos(angle), math.sin(angle)
    return tuple(c*x+s*y+(1-c)*dot*z for x,y,z in zip(v,cross,axis))


def _base_frame(atoms, site, maximum, gemmi):
    row = dict(site=asdict(site), status='UNAVAILABLE', reason=None)
    if site.component not in _REFERENCE:
        return {**row, 'reason': 'UNSUPPORTED_COMPONENT'}
    reference = _REFERENCE[site.component]
    names = _NAMES[:len(reference)]
    records = [_site_atom(atoms, site, name) for name in (*names, "C1'")]
    row['atoms'] = records
    missing = next((r for r in records if r['status'] != 'AVAILABLE'), None)
    if missing:
        return {**row, 'reason': missing['reason']}
    observed = [r['xyz_angstrom'] for r in records[:-1]]
    # A collapsed/collinear point set does not define a unique ring orientation.
    vectors = [_sub(p, observed[0]) for p in observed[1:]]
    span = max(math.hypot(*v) for v in vectors)
    area = max(math.hypot(*_cross(a,b)) for a in vectors for b in vectors)
    if span <= _EPS or area <= 1e-6*span*span:
        return {**row, 'reason': 'DEGENERATE_RING_FIT'}
    fit = gemmi.superpose_positions([gemmi.Position(*p) for p in observed],
                                    [gemmi.Position(*p) for p in reference])
    rmsd = float(fit.rmsd)
    row['fit_rmsd_angstrom'] = rmsd if math.isfinite(rmsd) else None
    if not math.isfinite(rmsd):
        return {**row, 'reason': 'DEGENERATE_RING_FIT'}
    if rmsd > maximum:
        return {**row, 'reason': 'RING_FIT_EXCEEDS_LIMIT'}
    origin = tuple(fit.transform.apply(gemmi.Position(0,0,0)))
    tip = tuple(fit.transform.apply(gemmi.Position(0,0,1)))
    try:
        normal = _unit(_sub(tip,origin), 'DEGENERATE_RING_FIT')
    except _Unavailable as exc:
        return {**row, 'reason': str(exc)}
    return {**row, 'status': 'AVAILABLE', 'origin_angstrom': list(origin),
            'normal': list(normal), 'c1_prime_angstrom': records[-1]['xyz_angstrom']}


def _pair_frame(atoms, pair, maximum, gemmi):
    bases = [_base_frame(atoms, s, maximum, gemmi) for s in (pair.strand_i,pair.strand_ii)]
    row = dict(pair_id=pair.pair_id, status='UNAVAILABLE', reason=None, base_frames=bases)
    if any(b['status'] != 'AVAILABLE' for b in bases):
        return {**row, 'reason': 'BASE_FRAME_UNAVAILABLE'}
    a, b = bases
    dot = _dot(a['normal'],b['normal'])
    if abs(dot) <= _EPS:
        return {**row, 'reason': 'AMBIGUOUS_PAIR_NORMAL'}
    try:
        normal = _unit(tuple(x+(1 if dot>0 else -1)*y for x,y in zip(a['normal'],b['normal'])), 'AMBIGUOUS_PAIR_NORMAL')
        across = _sub(a['c1_prime_angstrom'], b['c1_prime_angstrom'])
        length = math.hypot(*across)
        if length <= _EPS:
            raise _Unavailable('DEGENERATE_C1_DIRECTION')
        projected = tuple(x-_dot(across,normal)*z for x,z in zip(across,normal))
        direction = _unit(tuple(v/length for v in projected), 'DEGENERATE_C1_DIRECTION')
    except _Unavailable as exc:
        return {**row, 'reason': str(exc)}
    return {**row, 'status': 'AVAILABLE',
            'origin_angstrom': [(x+y)/2 for x,y in zip(a['origin_angstrom'],b['origin_angstrom'])],
            'normal': list(normal), 'c1_direction': list(direction),
            'interbase_normal_angle_deg': math.degrees(math.acos(min(1.,abs(dot))))}


def _step(first, second, left, right):
    row = dict(pair_ids=[left.pair_id,right.pair_id], status='UNAVAILABLE',
               reason=None, twist_deg=None)
    if right.break_before:
        return {**row, 'reason': 'DECLARED_BREAK'}
    if first['status'] != 'AVAILABLE' or second['status'] != 'AVAILABLE':
        return {**row, 'reason': 'PAIR_FRAME_UNAVAILABLE'}
    try:
        d = _unit(_sub(second['origin_angstrom'], first['origin_angstrom']), 'COINCIDENT_PAIR_ORIGINS')
        normals, reversals = [], []
        for frame in (first, second):
            projection = _dot(d, frame['normal'])
            if abs(projection) <= _EPS:
                raise _Unavailable('AMBIGUOUS_STEP_DIRECTION')
            reverse = projection < 0
            reversals.append(reverse)
            normals.append(tuple(-v if reverse else v for v in frame['normal']))
        a,b = normals
        common = _unit(tuple(x+y for x,y in zip(a,b)), 'AMBIGUOUS_STEP_NORMAL')
        cross = _cross(a,b); size = math.hypot(*cross)
        y1, y2 = first['c1_direction'], second['c1_direction']
        if size > _EPS:
            axis = tuple(v/size for v in cross)
            half = math.atan2(size, _dot(a,b))/2
            y1, y2 = _rotate(y1,axis,half), _rotate(y2,axis,-half)
        angle = math.degrees(math.atan2(_dot(common,_cross(y1,y2)),_dot(y1,y2)))
        if abs(abs(angle)-180) <= _EPS:
            raise _Unavailable('AMBIGUOUS_TWIST_WRAP')
    except _Unavailable as exc:
        return {**row, 'reason': str(exc)}
    return {**row, 'status': 'MEASURED', 'twist_deg': angle,
            'normal_reversed': reversals, 'oriented_pair_normals': [list(a),list(b)],
            'common_normal': list(common)}


def _stacking_step(first, second, *, declared_break):
    """Unoriented fitted planes and observed ring centroids, not contact scores."""
    row = dict(sites=[first['site'], second['site']], status='UNAVAILABLE', reason=None,
        plane_angle_deg=None, centroid_distance_angstrom=None,
        normal_spacing_angstrom=None, lateral_offset_angstrom=None)
    if declared_break:
        return {**row, 'reason': 'DECLARED_BREAK'}
    if first['status'] != 'AVAILABLE' or second['status'] != 'AVAILABLE':
        return {**row, 'reason': 'BASE_FRAME_UNAVAILABLE'}
    # The last frame atom is C1'; only fitted ring atoms define these centroids.
    centers = [tuple(math.fsum(atom['xyz_angstrom'][i] for atom in frame['atoms'][:-1])
                     / (len(frame['atoms'])-1) for i in range(3))
               for frame in (first, second)]
    delta = _sub(centers[1], centers[0])
    distance = math.hypot(*delta)
    a, b = first['normal'], second['normal']
    dot = max(-1., min(1., _dot(a, b)))
    row.update(plane_angle_deg=math.degrees(math.acos(abs(dot))),
               ring_centroids_angstrom=[list(c) for c in centers],
               centroid_distance_angstrom=distance)
    # A plane has no arrow. Align normals along their acute branch, not along
    # the displacement: coplanar sliding and coincident centroids remain measurable.
    if abs(dot) <= _EPS:
        return {**row, 'reason': 'AMBIGUOUS_MIDPLANE_NORMAL'}
    normal = _unit(tuple(x+(1 if dot > 0 else -1)*y for x,y in zip(a,b)),
                   'AMBIGUOUS_MIDPLANE_NORMAL')
    projection = _dot(delta, normal)
    lateral = math.hypot(*(x-projection*n for x,n in zip(delta, normal)))
    return {**row, 'status': 'MEASURED',
            'normal_spacing_angstrom': abs(projection), 'lateral_offset_angstrom': lateral}


def _stacking_geometry(frames, pairs):
    steps = [dict(pair_ids=[left.pair_id,right.pair_id],
                  pair_roles=[left.role,right.role], break_before=right.break_before,
                  strand_order=['strand_i','strand_ii'],
                  strands=[_stacking_step(a,b,declared_break=right.break_before)
                           for a,b in zip(first['base_frames'],second['base_frames'])])
             for first,second,left,right in zip(frames,frames[1:],pairs,pairs[1:])]
    count = sum(row['status']=='MEASURED' for step in steps for row in step['strands'])
    return dict(method='declared-ring-stacking-v1', status='ASSESSED', steps=steps,
        coverage=dict(declared_strand_steps=2*len(steps), measured_strand_steps=count,
                      unavailable_strand_steps=2*len(steps)-count),
        convention='Observed ring centroids; acute fitted-plane angle; unsigned displacement along the aligned mean normal and residual lateral magnitude',
        frame_source='simple_step_twist.pair_frames.base_frames',
        overlap=dict(status='NOT_MEASURED', reason='Centroid offset does not measure ring overlap'),
        geometry_accepted=False, limitations=[
            'Descriptive same-strand adjacency from caller order, not inferred stacking contacts or chemical topology',
            'Within-pair normal angle and signed step twist remain separate in simple_step_twist',
            'Uses existing canonical frames and fit limit; missing C1-prime also makes that frame unavailable',
            'No signed roll/tilt, local helix axis, overlap, stacking energy or acceptance cutoff',
            'Acute unoriented planes cannot distinguish a flipped base from an unflipped plane'])


def inspect_helical_region(model_path, region, *, expected_model_sha256,
                           max_ring_fit_rmsd_angstrom, include_half_span=False,
                           include_stacking=False):
    """Compose independent phosphate spans and canonical simple-step twist.

    Caller declares pairing, strand order and a maximum ring-fit RMSD; the limit
    is reported, not interpreted as a chemical acceptance rule. Requires the
    existing topology extra (Gemmi). Modified rings are deliberately unavailable.
    Explicit include_stacking adds same-strand ring placement descriptors from
    those exact frames; it grants no contact assignment or geometry acceptance.
    """
    if type(include_stacking) is not bool:
        raise ValueError('include_stacking must be boolean')
    maximum = max_ring_fit_rmsd_angstrom
    if type(maximum) not in (int,float) or not math.isfinite(maximum) or maximum <= 0:
        raise ValueError('Require an explicit positive finite ring-fit RMSD limit')
    try:
        import gemmi
    except ImportError as exc:
        raise RuntimeError('Simple-step twist requires NASolve[topology] (Gemmi)') from exc
    result = inspect_phosphate_spans(model_path, region,
        expected_model_sha256=expected_model_sha256, include_half_span=include_half_span)
    path = Path(model_path); payload = path.read_bytes()
    if sha256(payload).hexdigest() != expected_model_sha256:
        raise ValueError('Model hash changed before frame measurement')
    atoms = _read_atoms(payload)
    frames = [_pair_frame(atoms, pair, maximum, gemmi) for pair in region.pairs]
    steps = [_step(a,b,left,right) for a,b,left,right in
             zip(frames,frames[1:],region.pairs,region.pairs[1:])]
    if path.read_bytes() != payload:
        raise ValueError('Model bytes changed during frame measurement')
    measured = sum(s['status'] == 'MEASURED' for s in steps)
    result['kind'] = 'regional-helical-geometry'
    result['simple_step_twist'] = dict(status='ASSESSED', method=METHOD,
        max_ring_fit_rmsd_angstrom=maximum, reference_coordinates_sha256=recipe_digest(_REFERENCE),
        numerical_orientation_epsilon=_EPS, ring_collinearity_area_ratio=1e-6,
        fit_engine={'name':'gemmi.superpose_positions','version':gemmi.__version__},
        atom_name_policy='Existing PDB reader normalizes legacy star to prime; duplicates refuse',
        pair_frames=frames, steps=steps,
        coverage={'declared_steps':len(steps),'measured_steps':measured,'unavailable_steps':len(steps)-measured})
    if include_stacking:
        result['stacking_geometry'] = _stacking_geometry(frames, region.pairs)
    return result


def _weighted_step_summary(steps, weights, minimum):
    """Summarize reader-owned steps; no partial-coverage renormalization."""
    if (type(minimum) not in (int, float) or not math.isfinite(minimum)
            or not 0 < minimum < 180):
        raise ValueError('Require an explicit finite mean-twist limit between 0 and 180 degrees')
    if (not isinstance(weights, (list, tuple)) or len(weights) != len(steps)
            or not weights or any(type(w) not in (int, float) or not math.isfinite(w) or w < 0 for w in weights)
            or not any(w > 0 for w in weights)):
        raise ValueError('Declare one finite nonnegative weight per step, with positive total weight')
    try:
        total = math.fsum(weights)
    except OverflowError as exc:
        raise ValueError('Total step weight must be finite') from exc
    if not math.isfinite(total):
        raise ValueError('Total step weight must be finite')
    rows = [{**step, 'weight': weight} for step, weight in zip(steps, weights)]
    selected = [i for i, weight in enumerate(weights) if weight > 0]
    measured = [r for r in rows if r['weight'] > 0 and r['status'] == 'MEASURED']
    result = dict(method='declared-weighted-simple-twist-v1', status='UNAVAILABLE',
        reason=None, weighted_mean_twist_deg=None, signed_bp_per_turn=None,
        repeat_reason='MEAN_UNAVAILABLE', min_abs_mean_twist_deg=minimum,
        weight_policy='Caller-declared ordered weights; zero excludes a step',
        angle_policy='Signed arithmetic mean on one branch; range >=180 degrees unavailable',
        steps=rows, coverage=dict(declared_steps=len(steps), included_steps=len(selected),
            excluded_steps=len(steps)-len(selected), measured_included_steps=len(measured),
            declared_weight=total, measured_weight=math.fsum(r['weight'] for r in measured)))
    if len(measured) != len(selected):
        return {**result, 'reason': 'INCOMPLETE_WEIGHTED_COVERAGE'}
    if selected != list(range(selected[0], selected[-1]+1)):
        return {**result, 'reason': 'DISCONTIGUOUS_WEIGHTED_REGION'}
    values = [r['twist_deg'] for r in measured]
    if max(values)-min(values) >= 180-1e-8:
        return {**result, 'reason': 'AMBIGUOUS_ANGLE_BRANCH'}
    # Normalize first to avoid overflow in weight*angle for large valid weights.
    mean = math.fsum(r['weight']/total*r['twist_deg'] for r in measured)
    result.update(status='MEASURED', weighted_mean_twist_deg=mean,
                  repeat_reason='MEAN_AT_OR_BELOW_DECLARED_LIMIT')
    if abs(mean) > minimum:
        repeat = 360/mean
        if math.isfinite(repeat):
            result.update(signed_bp_per_turn=repeat, repeat_reason=None)
        else:
            result['repeat_reason'] = 'NONFINITE_REPEAT'
    return result


def inspect_weighted_twist(model_path, region, *, expected_model_sha256,
                           max_ring_fit_rmsd_angstrom, step_weights,
                           min_abs_mean_twist_deg, include_half_span=False):
    """Add a declared contiguous regional summary to the existing raw report.

    Supply one weight for every adjacent pair step, including explicit zeros.
    Missing positive-weight steps leave the mean unavailable. The caller's
    positive mean-magnitude limit suppresses unstable signed bp/turn; it is not
    an experimental uncertainty or chemical acceptance threshold. No circular
    unwrapping, radius, curvature or coordinate operation is inferred.
    """
    result = inspect_helical_region(model_path, region,
        expected_model_sha256=expected_model_sha256,
        max_ring_fit_rmsd_angstrom=max_ring_fit_rmsd_angstrom,
        include_half_span=include_half_span)
    result['regional_twist_summary'] = _weighted_step_summary(
        result['simple_step_twist']['steps'], step_weights, min_abs_mean_twist_deg)
    return result
