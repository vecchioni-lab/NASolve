"""Supplemental full-rank derivative audit inside per-atom movement balls.

Does not replace existing centered/serialized checks. Boundary radial probes are
second-order one-sided; tangent probes follow constant-radius sphere geodesics.
"""
import math
STEPS = (0.0001, 1e-05)
ABSOLUTE_BOUND = 0.001

def _dot(a, b):
    return math.fsum((x * y for x, y in zip(a, b)))

def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

def _need(c, msg):
    if not c:
        raise ValueError(msg)

def frames(values, radius):
    """Build a full-rank feasible frame for each Cartesian displacement triple.

    Interior atoms use Cartesian directions. Near a boundary, use the inward
    radius and two orthonormal sphere tangents at the *actual* radius, not the cap.
    Refuse insufficient clearance instead of shrinking the fixed audit steps.
    """
    x = tuple(values)
    _need(bool(x) and len(x) % 3 == 0 and (len(x) <= 1200) and all((type(v) in (int, float) and math.isfinite(v) for v in x)), 'Require finite Cartesian triples')
    _need(type(radius) in (int, float) and math.isfinite(radius) and (radius > 0), 'Require positive radius')
    result = []
    for offset in range(0, len(x), 3):
        d = x[offset:offset + 3]
        m = math.hypot(*d)
        _need(m <= radius, 'Source displacement exceeds cap')
        centered = True
        for axis in range(3):
            for sign in [-1, 1]:
                q = list(d)
                q[axis] += sign * max(STEPS)
                centered &= math.hypot(*q) <= radius
        if centered:
            result.append(dict(offset=offset, mode='CARTESIAN_CENTERED', basis=[tuple((1.0 if i == j else 0.0 for j in range(3))) for i in range(3)], radius=m))
        else:
            _need(m >= 2 * max(STEPS), 'Insufficient inward radial clearance for unchanged steps')
            radial = tuple((v / m for v in d))
            axis = min(range(3), key=lambda i: abs(radial[i]))
            v = tuple(((1.0 if i == axis else 0.0) - radial[axis] * radial[i] for i in range(3)))
            norm = math.hypot(*v)
            t1 = tuple((z / norm for z in v))
            t2 = _cross(radial, t1)
            basis = [tuple((-v for v in radial)), t1, t2]
            _need(all((abs(_dot(a, b) - (1.0 if i == j else 0.0)) < 1e-12 for i, a in enumerate(basis) for j, b in enumerate(basis))), 'Invalid full-rank frame')
            result.append(dict(offset=offset, mode='INWARD_RADIAL_AND_GEODESIC_TANGENTS', basis=basis, radius=m))
    return result

def _point(values, frame, axis, step, radius):
    x = list(values)
    offset = frame['offset']
    d = x[offset:offset + 3]
    direction = frame['basis'][axis]
    if frame['mode'] == 'CARTESIAN_CENTERED' or axis == 0:
        q = tuple((a + step * b for a, b in zip(d, direction)))
    else:
        m = frame['radius']
        q = tuple((math.cos(step / m) * a + m * math.sin(step / m) * b for a, b in zip(d, direction)))
        # Correct only binary roundoff beyond the declared hard cap.
        if math.hypot(*q) > radius:
            scale = math.nextafter(float(radius), 0.0) / math.hypot(*q)
            q = tuple((v * scale for v in q))
    _need(math.hypot(*q) <= radius, 'Probe exceeds cap')
    delta = tuple(a - b for a, b in zip(q, d))
    _need(tuple(d) != q and _dot(delta, direction) * step > 0,
          'Probe has no representable signed displacement')
    x[offset:offset + 3] = q
    return tuple(x)

def check(evaluate, values, *, radius):
    """Supplementally audit an ambient gradient using feasible full-rank probes.

    The callback returns a mapping with finite ``target`` and ``gradient``.
    Snapshot only those values, allowing reused native callback buffers without
    retaining bulky native metadata. For n coordinates the complete audit calls
    the objective 2 + 4*n times, including baseline and exact repeat. The caller
    owns source identity, execution deadlines and recovery of external processes.
    This does not establish constrained stationarity, feasibility after file
    serialization or chemical validity, nor replace existing required checks.
    On failure, the last sample pair may be incomplete and have no derivative row.
    """
    values = tuple(values)
    basis = frames(values, radius)
    report = dict(status='FAILED', kind='feasible-ball-basis-derivatives-v1', absolute_bound=ABSOLUTE_BOUND, steps_angstrom=list(STEPS), frames=basis, rows=[], samples=[], evaluation_calls=0, scientific_acceptance=False, replaces_centered_or_serialized_checks=False)

    def call(x, label):
        report['evaluation_calls'] += 1
        try:
            r = evaluate(x)
            target, gradient = r['target'], tuple(r['gradient'])
            _need(type(target) in (int, float) and math.isfinite(target)
                  and len(gradient) == len(values)
                  and all(type(v) in (int, float) and math.isfinite(v) for v in gradient)
                  and math.isfinite(math.hypot(*gradient)), 'Incomplete finite scalar/gradient')
            return dict(target=target, gradient=list(gradient))
        except Exception as exc:
            report['failed_sample'] = dict(label=label, displacements=list(x), error=type(exc).__name__ + ': ' + str(exc))
            raise
    try:
        start = call(values, 'baseline')
        report['baseline'] = start
        for frame in basis:
            offset = frame['offset']
            g = start['gradient'][offset:offset + 3]
            for axis, direction in enumerate(frame['basis']):
                analytic = _dot(g, direction)
                for h in STEPS:
                    radial = frame['mode'] != 'CARTESIAN_CENTERED' and axis == 0
                    amounts = [h, 2 * h] if radial else [-h, h]
                    samples = []
                    # Preserve a completed first probe if its partner fails.
                    report['samples'].append(samples)
                    for amount in amounts:
                        q = _point(values, frame, axis, amount, radius)
                        _need(all(tuple(sample['displacements']) != q for sample in samples),
                              'Probe pair has no representable separation')
                        value = call(q, dict(offset=offset, axis=axis, step_A=amount))['target']
                        samples.append(dict(displacements=list(q), step_A=amount, target=value))
                    numeric = (-3 * start['target'] + 4 * samples[0]['target'] - samples[1]['target']) / (2 * h) if radial else (samples[1]['target'] - samples[0]['target']) / (2 * h)
                    error = abs(numeric - analytic)
                    _need(math.isfinite(error), 'Nonfinite derivative error')
                    report['rows'].append(dict(offset=offset, basis_axis=axis, step_A=h, formula='SECOND_ORDER_INWARD' if radial else 'CENTERED', analytic=analytic, numeric=numeric, absolute_error=error))
        repeat = call(values, 'repeat')
        report['exact_repeat'] = start['target'] == repeat['target'] and list(start['gradient']) == list(repeat['gradient'])
        _need(report['exact_repeat'], 'Repeated objective/gradient changed')
        report['max_absolute_error'] = max((r['absolute_error'] for r in report['rows']))
        report['status'] = 'FEASIBLE_BASIS_DERIVATIVES_PASS' if report['max_absolute_error'] <= ABSOLUTE_BOUND else 'FEASIBLE_BASIS_DERIVATIVE_REVIEW'
    except Exception as exc:
        report.update(status='FAILED', error=type(exc).__name__ + ': ' + str(exc))
    return report
