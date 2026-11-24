"""Explicit bounded projected-gradient diagnostic; no model adoption.

This is an explicit alternative to the existing hard-guarded L-BFGS caller.
Projection constructs trial coordinates, never a surrogate objective/gradient.
"""
import math


class _EvaluationLimit(Exception):
    """Internal budget stop, distinct from any callback exception."""


def _vector(values):
    result = tuple(values)
    if not result or len(result) % 3 or len(result) > 1200 or any((type(v) not in (int, float) or not math.isfinite(v) for v in result)):
        raise ValueError('Require complete finite Cartesian triples')
    return result

def project_balls(values, radius):
    """Project 1–400 Cartesian displacement triples into equal origin-centred balls."""
    values = _vector(values)
    if type(radius) not in (int, float) or not math.isfinite(radius) or radius <= 0:
        raise ValueError('Require positive finite radius')
    out = []
    for offset in range(0, len(values), 3):
        xyz = values[offset:offset + 3]
        length = math.hypot(*xyz)
        if not math.isfinite(length):
            raise ValueError('Nonfinite displacement length')
        if length > radius:
            xyz = tuple((v / length * radius for v in xyz))
            # Remove only binary roundoff beyond the hard bound.
            if math.hypot(*xyz) > radius:
                xyz = tuple((v * (math.nextafter(float(radius), 0.0) / math.hypot(*xyz)) for v in xyz))
            if math.hypot(*xyz) > radius:
                raise ValueError('Projection roundoff exceeds radius')
        out.extend(xyz)
    return tuple(out)

def projected_residual(x, g, radius):
    """Return ||x - P(x-g)||; a boundary optimum need not have zero gradient."""
    x, g = _vector(x), _vector(g)
    if len(x) != len(g) or project_balls(x, radius) != x:
        raise ValueError('Require matched vectors and a feasible displacement')
    trial = project_balls(tuple((a - b for a, b in zip(x, g))), radius)
    return math.hypot(*(a - b for a, b in zip(x, trial)))

def minimize(evaluate, *, variable_count, radius, max_iterations=100, max_evaluations=300, tolerance=1e-05):
    """Zero-start spectral projected gradient, Armijo along a feasible segment.

    The fixed mapping x - P(x-g) distinguishes constrained stationarity from
    Cartesian stationarity. A stop is never chemical acceptance. Errors and
    evaluation/iteration limits preserve only the last accepted point.

    ``evaluate(tuple_of_displacements)`` returns a finite scalar and Cartesian
    gradient. It must evaluate the actual supplied point and own any native
    source/state validation, execution deadline and process recovery. This pure
    helper starts from zero, writes nothing and cannot interrupt a blocked callback.
    Its report retains bounded valid trials and separately records a failed call.
    Invalid controls raise before any evaluation; callback exceptions become FAILED
    except process interrupts (KeyboardInterrupt/SystemExit), which propagate.
    """
    if type(variable_count) is not int or not 0 < variable_count <= 1200 or variable_count % 3:
        raise ValueError('Require 1-400 Cartesian triples')
    project_balls((0.0,) * variable_count, radius)
    if type(max_iterations) is not int or not 1 <= max_iterations <= 500:
        raise ValueError('Require bounded iterations')
    if type(max_evaluations) is not int or not 1 <= max_evaluations <= 5000:
        raise ValueError('Require bounded evaluations')
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('Require positive finite stationarity tolerance')
    x = (0.0,) * variable_count
    trace = []
    accepted = []
    calls = 0
    iterations = 0
    current = None
    result = dict(status='FAILED', scientific_acceptance=False, automatic_adoption=False, method='spectral-projected-gradient-armijo-v1', source_start='ZERO', radius=radius, stationarity_policy='norm(x-project_balls(x-gradient, radius))', tolerance=tolerance, armijo=0.0001, backtracking_factor=0.5, max_backtracks=50, spectral_step_bounds=[1e-12, 1000.0], max_iterations=max_iterations, max_evaluations=max_evaluations, trace=trace, accepted_steps=accepted)

    def call(q):
        nonlocal calls
        if calls >= max_evaluations:
            raise _EvaluationLimit('EVALUATION_LIMIT')
        if len(q) != variable_count or project_balls(q, radius) != q:
            raise ValueError('Attempted infeasible objective call')
        calls += 1
        callback_returned = False
        try:
            returned = evaluate(q)
            callback_returned = True
            f, g = returned
            g = _vector(g)
            if type(f) not in (int, float) or not math.isfinite(f) or len(g) != variable_count or (not math.isfinite(math.hypot(*g))):
                raise ValueError('Incomplete finite objective and gradient')
        except Exception as exc:
            result['failed_attempt'] = dict(displacements=list(q), evaluation_call=calls, callback_returned=callback_returned, valid_objective_returned=False, accepted=False, error=type(exc).__name__ + ': ' + str(exc))
            raise
        trace.append(dict(displacements=list(q), target=f, gradient=list(g), gradient_norm=math.hypot(*g), accepted=False))
        return (f, g)
    try:
        current = call(x)
        trace[-1]['accepted'] = True
        accepted.append(dict(iteration=0, trace_index=0))
        alpha = 1.0
        while True:
            f, g = current
            residual = projected_residual(x, g, radius)
            if residual <= tolerance:
                result['status'] = 'PROJECTED_STATIONARY'
                break
            if iterations >= max_iterations:
                result['status'] = 'ITERATION_LIMIT'
                break
            q = project_balls(tuple((a - alpha * b for a, b in zip(x, g))), radius)
            direction = tuple((b - a for a, b in zip(x, q)))
            slope = math.fsum((a * b for a, b in zip(g, direction)))
            if not math.isfinite(slope) or slope >= 0:
                raise ValueError('No feasible descent direction at unresolved stationarity')
            step = 1.0
            chosen = None
            for backtrack in range(50):
                # Evaluate the feasible segment itself, never a clipped old gradient.
                proposed = project_balls(tuple((a + step * d for a, d in zip(x, direction))), radius)
                if proposed == x:
                    raise ValueError('Representable step exhausted before stationarity')
                f_new, g_new = call(proposed)
                actual_slope = math.fsum((a * (b - c) for a, b, c in zip(g, proposed, x)))
                threshold = f + 0.0001 * actual_slope
                trace[-1].update(armijo_threshold=threshold, actual_slope=actual_slope, backtrack=backtrack, step_fraction=step)
                if actual_slope < 0 and f_new <= threshold:
                    chosen = (proposed, f_new, g_new)
                    break
                step *= 0.5
            if chosen is None:
                raise ValueError('Line search exhausted')
            new_x, f_new, g_new = chosen
            s = tuple((b - a for a, b in zip(x, new_x)))
            y = tuple((b - a for a, b in zip(g, g_new)))
            ss = math.fsum((v * v for v in s))
            sy = math.fsum((a * b for a, b in zip(s, y)))
            alpha = min(1000.0, max(1e-12, ss / sy)) if sy > 0 else 1.0
            x = new_x
            current = (f_new, g_new)
            iterations += 1
            trace[-1]['accepted'] = True
            accepted.append(dict(iteration=iterations, trace_index=len(trace) - 1))
    except _EvaluationLimit as exc:
        result['status'] = str(exc)
    except Exception as exc:
        result.update(status='FAILED', error=type(exc).__name__ + ': ' + str(exc))
    finally:
        result.update(evaluations=calls, iterations=iterations, last_accepted_displacements=list(x) if accepted else None)
        if current is not None:
            f, g = current
            result.update(last_accepted_target=f, cartesian_gradient_norm=math.hypot(*g), active_atoms=[i // 3 for i in range(0, len(x), 3) if radius - math.hypot(*x[i:i + 3]) <= 1e-08])
            try:
                result['projected_residual'] = projected_residual(x, g, radius)
            except Exception as exc:
                result['projected_residual'] = None
                result['final_diagnostic_error'] = type(exc).__name__ + ': ' + str(exc)
    return result
