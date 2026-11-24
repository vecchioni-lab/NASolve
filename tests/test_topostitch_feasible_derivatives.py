import math
import pytest
from nasolve.topostitch_feasible_derivatives import frames, check

def objective(x):
    return dict(target=sum(((i + 1) * v * v + 0.1 * v ** 3 for i, v in enumerate(x))) + 0.3 * x[0] * x[-1], gradient=[2 * (i + 1) * v + 0.3 * v * v + (0.3 * x[-1] if i == 0 else 0.3 * x[0] if i == len(x) - 1 else 0) for i, v in enumerate(x)])

@pytest.mark.parametrize('x', [(0.0, 0.0, 0.0), (0.2, 0.3, 0.4), (2.0, 0.0, 0.0), (1.2, 1.6, 0.0), (0.0, -2.0, 0.0), (0.2, 0.3, 0.4, 1.2, 1.6, 0.0)])
def test_exact_gradient_with_full_rank_feasible_basis(x):
    seen = []

    def evaluate(q):
        assert all((math.hypot(*q[i:i + 3]) <= 2 for i in range(0, len(q), 3)))
        seen.append(q)
        return objective(q)
    r = check(evaluate, x, radius=2)
    assert r['status'] == 'FEASIBLE_BASIS_DERIVATIVES_PASS' and r['exact_repeat']
    assert r['evaluation_calls'] == 2 + 4 * len(x) == len(seen)
    assert r['max_absolute_error'] < 1e-05 and (not r['replaces_centered_or_serialized_checks'])

def test_wrong_radial_gradient_fails():

    def bad(x):
        r = objective(x)
        r['gradient'][0] += 0.01
        return r
    r = check(bad, (2.0, 0.0, 0.0), radius=2)
    assert r['status'] == 'FEASIBLE_BASIS_DERIVATIVE_REVIEW'
    assert r['max_absolute_error'] > 0.009

def test_wrong_tangential_gradient_fails():

    def bad(x):
        r = objective(x)
        r['gradient'][1] += 0.01
        return r
    r = check(bad, (2.0, 0.0, 0.0), radius=2)
    assert r['status'] == 'FEASIBLE_BASIS_DERIVATIVE_REVIEW'

def test_boundary_probes_use_sphere_and_inward_ray():
    r = check(objective, (2.0, 0.0, 0.0), radius=2)
    assert r['frames'][0]['mode'] == 'INWARD_RADIAL_AND_GEODESIC_TANGENTS'
    for row, samples in zip(r['rows'], r['samples']):
        if row['basis_axis'] == 0:
            assert all((math.hypot(*s['displacements']) < 2 for s in samples))
        else:
            assert all((math.hypot(*s['displacements']) == pytest.approx(2, abs=1e-14) for s in samples))

def test_no_silent_step_shrinking():
    with pytest.raises(ValueError, match='clearance'):
        check(lambda x: pytest.fail('no evaluation'), (0.0, 0.0, 0.0), radius=1e-06)

def test_partial_failure_retained():
    n = 0

    def bad(x):
        nonlocal n
        n += 1
        if n == 3:
            raise RuntimeError('sample failure')
        return objective(x)
    r = check(bad, (2.0, 0.0, 0.0), radius=2)
    assert r['status'] == 'FAILED' and r['evaluation_calls'] == 3 and r['failed_sample']
    assert 'max_absolute_error' not in r

def test_exact_repeat_must_hold():
    n = 0

    def drift(x):
        nonlocal n
        n += 1
        r = objective(x)
        if n == 14:
            r['target'] += 1e-06
        return r
    r = check(drift, (2.0, 0.0, 0.0), radius=2)
    assert r['status'] == 'FAILED' and (not r['exact_repeat'])

def test_rotated_frame_reconstructs_full_cartesian_gradient():
    x = (1.2, 0.0, 1.6)
    r = check(objective, x, radius=2)
    basis = r['frames'][0]['basis']
    rows = [v for v in r['rows'] if v['step_A'] == 1e-05]
    recovered = [sum((v['numeric'] * basis[v['basis_axis']][j] for v in rows)) for j in range(3)]
    assert recovered == pytest.approx(objective(x)['gradient'], abs=1e-06)

def test_linear_objective_on_sphere_uses_arc_length_and_radial_sign():
    g = (2.0, -3.0, 5.0)
    x = (1.2, 0.0, 1.6)
    r = check(lambda q: dict(target=sum((a * b for a, b in zip(g, q))), gradient=list(g)), x, radius=2)
    assert r['status'] == 'FEASIBLE_BASIS_DERIVATIVES_PASS'
    assert len({v['step_A'] for v in r['rows']}) == 2
    radial = [v for v in r['rows'] if v['basis_axis'] == 0]
    assert all((v['numeric'] == pytest.approx(-sum((a * b / 2 for a, b in zip(g, x))), abs=1e-09) for v in radial))

def test_near_boundary_tangents_do_not_snap_to_cap():
    x = (1.99999, 0.0, 0.0)
    r = check(objective, x, radius=2)
    assert r['frames'][0]['mode'] == 'INWARD_RADIAL_AND_GEODESIC_TANGENTS'
    for row, samples in zip(r['rows'], r['samples']):
        if row['basis_axis'] > 0:
            assert all((math.hypot(*s['displacements']) == pytest.approx(1.99999, abs=1e-14) for s in samples))



def test_callback_reused_buffers_are_snapshotted_without_native_payload():
    shared = dict(target=0., gradient=[0.,0.,0.], native_inventory=object())
    def evaluate(x):
        fresh = objective(x)
        shared['target'] = fresh['target']
        shared['gradient'][:] = fresh['gradient']
        return shared
    r = check(evaluate, (2.,0.,0.), radius=2)
    assert r['status'] == 'FEASIBLE_BASIS_DERIVATIVES_PASS'
    expected = objective((2.,0.,0.))
    assert r['baseline'] == expected
    shared['gradient'][0] = -999
    shared['target'] = -999
    assert r['baseline'] == expected
    assert 'native_inventory' not in r['baseline']


def test_reused_buffer_cannot_hide_repeat_drift():
    shared = dict(target=0., gradient=[0.,0.,0.])
    calls = 0
    def evaluate(x):
        nonlocal calls
        calls += 1
        fresh = objective(x)
        shared['target'] = fresh['target'] + (1e-6 if calls == 14 else 0.)
        shared['gradient'][:] = fresh['gradient']
        return shared
    r = check(evaluate, (2.,0.,0.), radius=2)
    assert r['status'] == 'FAILED' and not r['exact_repeat']


@pytest.mark.parametrize('gradient', [(True, 0., 0.), (1.7e308,1.7e308,1.7e308)])
def test_invalid_native_gradient_is_not_a_baseline(gradient):
    r = check(lambda x: dict(target=0.,gradient=gradient), (2.,0.,0.), radius=2)
    assert r['status'] == 'FAILED' and r['evaluation_calls'] == 1
    assert 'baseline' not in r


def test_callback_stop_iteration_is_failure_not_escape():
    def evaluate(x):
        raise StopIteration('pretend complete')
    r = check(evaluate, (2.,0.,0.), radius=2)
    assert r['status'] == 'FAILED' and r['evaluation_calls'] == 1
    assert 'StopIteration' in r['failed_sample']['error']



@pytest.mark.parametrize('point', [(1e100,1e100,1e100), (1e16,0.,0.)])
def test_unrepresentable_probe_is_not_a_derivative_pass(point):
    seen = []
    def evaluate(x):
        seen.append(x)
        # Deliberately wrong gradient: collapsed probes used to hide this.
        return dict(target=x[0] - point[0], gradient=[0.,0.,0.])
    r = check(evaluate, point, radius=2*max(point))
    assert r['status'] == 'FAILED'
    assert 'representable' in r['error']
    assert len(seen) == 1


def test_successful_probe_before_failure_is_preserved():
    seen = []
    def evaluate(x):
        seen.append(x)
        if len(seen) == 3:
            raise RuntimeError('second probe failed')
        return objective(x)
    r = check(evaluate, (2.,0.,0.), radius=2)
    assert r['status'] == 'FAILED'
    assert r['samples'] == [[dict(displacements=list(seen[1]), step_A=1e-4,
                                  target=objective(seen[1])['target'])]]
    assert not r['rows']
    assert r['failed_sample']['displacements'] == list(seen[2])
