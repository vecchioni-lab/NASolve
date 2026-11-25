"""Witnessed native normalization must never become general scale permission."""
from copy import deepcopy
import pytest
from nasolve.refinement_normalization import NativeScaleWitness
from tests.test_refinement_diffraction_observation import reference,sources,signature


def event(w, divisor=.004, mutate=None):
    before=deepcopy(w.current);after=deepcopy(before)
    factor=1. if .9<divisor<1.1 or divisor==0 else divisor
    for row in after['rows']:row[1]/=factor;row[2]/=factor
    if mutate:mutate(after)
    after=signature(after['rows'],True)
    w.record_event(before,after,sources()[1],sources()[1],divisor=divisor,
                   r_before=(.33,.36),r_after=(.33,.36))
    return after


def witness():
    w=NativeScaleWitness(reference());w.check_order([(0,0,1),(0,1,0),(1,0,0)],initial=True)
    return w


def test_witnessed_scale_preserves_source_and_exact_new_state():
    w=witness();source=w.record();after=event(w)
    r=w.state(after,sources()[1],target='mlhl')
    assert not r['exact_source_values'] and r['normalization_events']==1
    assert w.record()==source and w.summary()['events'][0]['division']==.004
    with pytest.raises(ValueError):reference().state(after,sources()[1],target='mlhl')


@pytest.mark.parametrize('kind',['F','sigma','flags','index','tiny_F'])
def test_one_changed_reflection_is_not_a_native_normalization(kind):
    w=witness()
    def change(obs):
        row=obs['rows'][0]
        if kind=='F':row[1]*=1.01
        elif kind=='sigma':row[2]*=1.01
        elif kind=='flags':row[3]=True
        elif kind=='index':row[0]=[0,0,2]
        else:row[1]+=1e-9
    with pytest.raises(ValueError):event(w,mutate=change)
    assert not w.summary()['events']


def test_unwitnessed_ratio_and_old_arrays_refuse():
    w=witness();after=event(w)
    other=deepcopy(after)
    for row in other['rows']:row[1]*=2;row[2]*=2
    other=signature(other['rows'],True)
    for obs in [sources()[0],other]:
        with pytest.raises(ValueError):w.state(obs,sources()[1],target='mlhl')


@pytest.mark.parametrize('divisor',[float('nan'),float('inf'),-1.,True])
def test_bad_divisor_refuses(divisor):
    w=witness()
    with pytest.raises(ValueError):event(w,divisor)


@pytest.mark.parametrize('which',['work','free','HL','before'])
def test_changed_R_or_source_refuses(which):
    w=witness();before,hl=sources();after=deepcopy(before);phase=deepcopy(hl)
    r=[.33,.36]
    if which=='work':r[0]=.34
    elif which=='free':r[1]=.37
    elif which=='HL':phase['rows'][0][1][0]+=1;phase=signature(phase['rows'])
    else:before['rows'][0][1]+=1;before=signature(before['rows'],True)
    with pytest.raises(ValueError):w.record_event(before,after,hl,phase,divisor=1.,r_before=(.33,.36),r_after=r)


def test_native_noop_and_multiple_observed_events():
    w=witness();event(w,1.);event(w,.004);after=event(w,2.)
    assert w.state(after,sources()[1],target='mlhl')['normalization_events']==3
    assert w.summary()['cumulative_F_sigma_multiplier']==125.


def test_order_is_never_sorted_away_or_rebound():
    w=witness()
    with pytest.raises(ValueError):w.check_order([(1,0,0),(0,1,0),(0,0,1)])
    with pytest.raises(ValueError):w.check_order([(0,0,1),(0,1,0),(1,0,0)],initial=True)


def test_summary_detached_and_event_bound():
    w=witness();event(w,1.);r=w.summary();r['events'].clear()
    assert len(w.summary()['events'])==1
    for _ in range(127):event(w,1.)
    with pytest.raises(ValueError):event(w,1.)


def test_v3_requires_explicit_boolean_and_cell_scope():
    from nasolve.refinement_mixed_runtime import MixedRuntimeGuard
    from nasolve.refinement_parameter_scope import ParameterScope,scope_digest
    from tests.test_refinement_parameter_scope import packet
    p=packet();scope=ParameterScope(p,expected_sha256=scope_digest(p))
    for value in [1,'yes',None]:
        with pytest.raises(ValueError):MixedRuntimeGuard(scope,reference(),cell_roundoff_ulps=4,witness_native_normalization=value)
    with pytest.raises(ValueError):MixedRuntimeGuard(scope,reference(),witness_native_normalization=True)
    g=MixedRuntimeGuard(scope,reference(),cell_roundoff_ulps=4,witness_native_normalization=True)
    assert g.summary()['policy_id'].endswith('-v3')
