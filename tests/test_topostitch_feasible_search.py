import math
import pytest
from nasolve.topostitch_feasible_search import minimize, project_balls, projected_residual

def quadratic(target, weights=None, seen=None):
    weights = weights or [1.0] * len(target)

    def evaluate(x):
        if seen is not None:
            seen.append(tuple(x))
        d = [a - b for a, b in zip(x, target)]
        return (0.5 * sum((w * v * v for w, v in zip(weights, d))), tuple((w * v for w, v in zip(weights, d))))
    return evaluate

def test_interior_known_minimum():
    target = (0.2, -0.3, 0.4)
    r = minimize(quadratic(target), variable_count=3, radius=2)
    assert r['status'] == 'PROJECTED_STATIONARY'
    assert r['last_accepted_displacements'] == list(target)
    assert r['cartesian_gradient_norm'] == 0 and r['active_atoms'] == []

def test_boundary_optimum_is_not_cartesian_stationarity():
    seen = []
    r = minimize(quadratic((3.0, 4.0, 0.0), seen=seen), variable_count=3, radius=2)
    assert r['status'] == 'PROJECTED_STATIONARY'
    assert r['last_accepted_displacements'] == pytest.approx([1.2, 1.6, 0])
    assert r['cartesian_gradient_norm'] == pytest.approx(3.0)
    assert r['projected_residual'] < 1e-14 and r['active_atoms'] == [0]
    assert all((math.hypot(*x) <= 2 for x in seen))
    assert not r['scientific_acceptance'] and (not r['automatic_adoption'])

def test_product_balls_and_anisotropic_interior():
    target = (3.0, 4.0, 0.0, 0.2, -0.3, 0.4)
    seen = []
    r = minimize(quadratic(target, [1, 1, 1, 4, 10, 30], seen), variable_count=6, radius=2, max_iterations=150)
    assert r['status'] == 'PROJECTED_STATIONARY'
    assert r['last_accepted_displacements'] == pytest.approx([1.2, 1.6, 0, 0.2, -0.3, 0.4], abs=2e-05)
    assert all((math.hypot(*x[j:j + 3]) <= 2 for x in seen for j in [0, 3]))
    for row in r['trace'][1:]:
        if row['accepted']:
            assert row['target'] <= row['armijo_threshold'] and row['actual_slope'] < 0

def test_evaluation_limit_never_returns_rejected_point():
    r = minimize(quadratic((0.2, 0.3, 0.4), [100, 200, 300]), variable_count=3, radius=2, max_evaluations=2)
    assert r['status'] == 'EVALUATION_LIMIT' and r['evaluations'] == 2
    assert r['last_accepted_displacements'] == [0.0, 0.0, 0.0]
    assert not r['trace'][-1]['accepted']

def test_iteration_limit_is_not_convergence():
    r = minimize(quadratic((0.2, 0.3, 0.4), [100, 200, 300]), variable_count=3, radius=2, max_iterations=1)
    assert r['status'] == 'ITERATION_LIMIT' and r['iterations'] == 1
    assert r['last_accepted_displacements'] == r['trace'][r['accepted_steps'][-1]['trace_index']]['displacements']

def test_failed_objective_preserves_accepted_source():
    n = 0

    def bad(x):
        nonlocal n
        n += 1
        if n == 2:
            raise RuntimeError('scientific guard')
        return quadratic((1.0, 1.0, 1.0))(x)
    r = minimize(bad, variable_count=3, radius=2)
    assert r['status'] == 'FAILED' and 'scientific guard' in r['error']
    assert r['evaluations'] == 2 and len(r['trace']) == 1
    assert r['last_accepted_displacements'] == [0.0, 0.0, 0.0]

@pytest.mark.parametrize('kw', [dict(radius=0), dict(radius=float('nan')), dict(radius=True), dict(variable_count=4), dict(max_iterations=True), dict(max_evaluations=0), dict(tolerance=0)])
def test_invalid_controls_before_objective(kw):
    args = dict(variable_count=3, radius=2)
    args.update(kw)
    with pytest.raises(ValueError):
        minimize(lambda x: pytest.fail('should not call'), **args)

def test_nonfinite_objective_is_failure():
    r = minimize(lambda x: (float('nan'), (0.0, 0.0, 0.0)), variable_count=3, radius=2)
    assert r['status'] == 'FAILED' and r['last_accepted_displacements'] is None

def test_projection_is_identity_inside_and_idempotent():
    assert project_balls((0.2, 0.3, 0.4), 2) == (0.2, 0.3, 0.4)
    for q in [(3, 4, 5), (1e+100, -1e+100, 1e+100), (2, 0, 0)]:
        p = project_balls(q, 2)
        assert math.hypot(*p) <= 2
        assert project_balls(p, 2) == p

def test_rotated_boundary_solution():
    for v in [(1.0, 2.0, 3.0), (-3.0, 1.0, 4.0), (0.0, 0.0, 5.0)]:
        r = minimize(quadratic(v), variable_count=3, radius=2)
        assert r['last_accepted_displacements'] == pytest.approx([2 * x / math.hypot(*v) for x in v])
        assert r['status'] == 'PROJECTED_STATIONARY'

def test_coupled_active_and_interior_atoms_known_kkt_solution():
    optimum = (1.2, 1.6, 0.0, 0.2, -0.1, 0.3)

    def h(x):
        return tuple((2 * x[i] + 0.5 * x[i + 3] for i in range(3))) + tuple((0.5 * x[i] + 3 * x[i + 3] for i in range(3)))
    b = tuple((v + (0.5 * optimum[i] if i < 3 else 0) for i, v in enumerate(h(optimum))))

    def evaluate(x):
        hx = h(x)
        return (0.5 * sum((a * c for a, c in zip(x, hx))) - sum((a * c for a, c in zip(b, x))), tuple((a - c for a, c in zip(hx, b))))
    r = minimize(evaluate, variable_count=6, radius=2, max_iterations=150)
    assert r['status'] == 'PROJECTED_STATIONARY'
    assert r['last_accepted_displacements'] == pytest.approx(optimum, abs=1e-05)
    assert r['cartesian_gradient_norm'] == pytest.approx(1.0, abs=1e-05)

def test_zero_feasible_displacement_is_stationary_without_search():
    assert projected_residual((2.0, 0.0, 0.0), (-3.0, 0.0, 0.0), 2) == 0
    r = minimize(quadratic((0.0, 0.0, 0.0)), variable_count=3, radius=2)
    assert r['status'] == 'PROJECTED_STATIONARY' and r['evaluations'] == 1 and (r['iterations'] == 0)

def test_non_descent_inconsistent_objective_fails_without_adoption():
    r = minimize(lambda x: (0.0, (1.0, 0.0, 0.0)), variable_count=3, radius=2, max_evaluations=60)
    assert r['status'] == 'FAILED' and 'Line search exhausted' in r['error']
    assert r['last_accepted_displacements'] == [0.0, 0.0, 0.0] and len(r['accepted_steps']) == 1

def test_failed_attempt_is_distinct_from_valid_trace():
    calls = []

    def evaluate(x):
        calls.append(x)
        if len(calls) == 2:
            raise RuntimeError('callback refused')
        return quadratic((1.0, 0.0, 0.0))(x)
    r = minimize(evaluate, variable_count=3, radius=2)
    assert r['failed_attempt']['displacements'] == list(calls[-1])
    assert r['failed_attempt']['evaluation_call'] == 2
    assert not r['failed_attempt']['callback_returned'] and (not r['failed_attempt']['accepted'])
    assert len(r['trace']) == 1 and r['last_accepted_displacements'] == [0.0, 0.0, 0.0]

def test_unavailable_final_diagnostic_does_not_mask_failure(monkeypatch):
    import nasolve.topostitch_feasible_search as module

    def fail(*args):
        raise ValueError('diagnostic unavailable')
    monkeypatch.setattr(module, 'projected_residual', fail)
    r = minimize(quadratic((0.2, 0.3, 0.4)), variable_count=3, radius=2)
    assert r['status'] == 'FAILED' and r['error'] == 'ValueError: diagnostic unavailable'
    assert r['projected_residual'] is None
    assert r['last_accepted_displacements'] == [0.0, 0.0, 0.0]
    assert r['final_diagnostic_error'] == 'ValueError: diagnostic unavailable'

def test_overflow_gradient_norm_is_recorded_not_accepted():
    r = minimize(lambda x: (1.0, (1.7e+308, 1.7e+308, 1.7e+308)), variable_count=3, radius=2)
    assert r['status'] == 'FAILED' and r['last_accepted_displacements'] is None
    assert r['failed_attempt']['callback_returned'] and (not r['failed_attempt']['valid_objective_returned'])


@pytest.mark.parametrize('failure', [StopIteration('PROJECTED_STATIONARY'), KeyError('missing native field'), OSError('callback unavailable')])
def test_callback_errors_cannot_impersonate_termination(failure):
    def evaluate(x):
        raise failure
    r = minimize(evaluate, variable_count=3, radius=2)
    assert r['status'] == 'FAILED'
    assert r['failed_attempt']['evaluation_call'] == 1
    assert not r['failed_attempt']['callback_returned']
    assert r['last_accepted_displacements'] is None


def test_malformed_callback_result_records_that_callback_returned():
    r = minimize(lambda x: (1.,), variable_count=3, radius=2)
    assert r['status'] == 'FAILED'
    assert r['failed_attempt']['callback_returned']
    assert not r['failed_attempt']['valid_objective_returned']


@pytest.mark.parametrize('x,g', [((0.,0.,0.), (0.,0.,0.,0.,0.,0.)), ((3.,0.,0.),(0.,0.,0.)), ((0.,0.,0.), (False,0.,0.))])
def test_residual_refuses_truncated_or_invalid_vectors(x,g):
    with pytest.raises(ValueError):
        projected_residual(x,g,2)


def test_callback_process_interrupt_propagates():
    def evaluate(x):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        minimize(evaluate, variable_count=3, radius=2)
