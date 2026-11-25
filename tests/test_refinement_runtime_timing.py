"""Diagnostic timing must preserve disjoint costs and interrupted evidence."""
import json
import pytest
from nasolve.refinement_runtime_timing import RuntimeTiming
from nasolve.refinement_mixed_runtime import MixedRuntimeGuard
from tests.test_refinement_mixed_runtime import scene, step
from tests.test_refinement_diffraction_observation import reference


class Clock:
    def __init__(self):self.value=0.0
    def __call__(self):return self.value
    def advance(self,amount):self.value+=amount


def test_nested_native_and_observer_costs_are_not_double_counted():
    c=Clock();t=RuntimeTiming(clock=c)
    c.advance(2)
    with t.measure('observer','stage'):
        c.advance(1)
        with t.measure('native','stage:xyz'):
            c.advance(3)
            with t.measure('observer','xyz'):
                c.advance(4)
                with t.measure('native','xyz'):c.advance(5)
            c.advance(6)
        c.advance(7)
    c.advance(8)
    r=t.summary()
    assert r['elapsed_seconds']==36
    assert r['exclusive_seconds']==dict(observer=12,native=14,telemetry=0)
    assert r['unattributed_seconds']==10 and r['active']==[]
    assert sum(row['inclusive_seconds'] for row in r['calls'])>26
    assert all(row['entered']==row['completed']==1 for row in r['calls'])


def test_partial_snapshot_keeps_active_calls_and_does_not_charge_twice():
    c=Clock();t=RuntimeTiming(clock=c)
    with t.measure('native','xyz'):
        c.advance(5);r=t.summary();assert r==t.summary()
        assert r['active']==[dict(category='native',label='xyz')]
        assert r['calls'][0]['completed']==0
        r['calls'][0]['exclusive_seconds']=999
        c.advance(2)
    assert t.summary()['calls'][0]['exclusive_seconds']==7


def test_interrupt_retains_elapsed_and_restores_nested_stack():
    c=Clock();t=RuntimeTiming(clock=c)
    with pytest.raises(KeyboardInterrupt):
        with t.measure('observer','stage'):
            c.advance(1)
            with t.measure('native','stage:xyz'):
                c.advance(2);raise KeyboardInterrupt
    r=t.summary();assert r['active']==[]
    assert r['exclusive_seconds']==dict(observer=1,native=2,telemetry=0)
    assert all(row['interrupted']==1 and row['completed']==0 for row in r['calls'])


def test_repeated_calls_remain_compact_and_label_bound_fails_explicitly():
    c=Clock();t=RuntimeTiming(clock=c,max_labels=1)
    for _ in range(10000):
        with t.measure('observer','xyz'):c.advance(.001)
    assert len(json.dumps(t.summary()))<1500
    assert t.summary()['calls'][0]['completed']==10000
    with pytest.raises(ValueError,match='bound'):
        with t.measure('native','xyz'):pass
    assert t.summary()['active']==[]


def test_invalid_clock_or_label_refuses():
    c=Clock();t=RuntimeTiming(clock=c)
    with pytest.raises(ValueError):
        with t.measure('science','XYZ'):pass
    c.value=-1
    with pytest.raises(ValueError,match='backwards'):t.summary()
    with pytest.raises(ValueError):RuntimeTiming(clock=lambda:float('nan'))


def test_timed_guard_preserves_calls_return_values_and_untimed_receipt(scene):
    s=scene;t=RuntimeTiming();g=MixedRuntimeGuard(s.scope,reference(),timing=t)
    with g:
        assert s.driver.write_before_run_outputs()=='initialized'
        assert s.xyz.compute_target()==17
        step(s);g.finish(s.driver,dry_run=False)
    r=g.summary();assert r['status']=='OBSERVED' and r['bindings_restored']
    assert r['counts']['xyz']==2 and r['counts']['group_B']==1
    assert r['timing']['active']==[]
    assert {'observer','native'}<=set(row['category'] for row in r['timing']['calls'])
    assert 'timing' not in s.guard().summary()


def test_timing_does_not_hide_scientific_failure_or_native_interrupt(scene):
    s=scene
    for error in ('changed_Q','interrupt'):
        g=MixedRuntimeGuard(s.scope,reference(),timing=RuntimeTiming())
        def action():
            if error=='interrupt':raise KeyboardInterrupt
            s.xs.scatterers()[3].occupancy-=.1
        with pytest.raises((ValueError,KeyboardInterrupt)):
            with g:
                s.driver.write_before_run_outputs();s.xyz.action=action;step(s)
        r=g.summary();assert r['status']=='FAILED' and r['bindings_restored']
        assert r['timing']['active']==[]
        assert any(row['interrupted'] for row in r['timing']['calls'])
        s.xs.scatterers()[3].occupancy=s.scope.record()['initial_atoms'][3]['Q']
