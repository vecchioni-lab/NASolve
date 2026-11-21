"""Declared arithmetic region weights, coverage and signed-repeat limits."""
from dataclasses import replace
import math
from hashlib import sha256
import pytest
from nasolve.helical_twist import inspect_weighted_twist, _weighted_step_summary


def steps(values):
    return [dict(pair_ids=[f'p{i}',f'p{i+1}'],status='MEASURED' if v is not None else 'UNAVAILABLE',
                 reason=None if v is not None else 'DECLARED_BREAK',twist_deg=v) for i,v in enumerate(values)]


def summary(values, weights, minimum=.1):
    return _weighted_step_summary(steps(values),weights,minimum)


def test_declared_local_edge_and_half_step_weights():
    values=[20,30,40,50,60,70,80,90]
    edge=summary(values,[0,1,1,1,1,1,1,0])
    assert edge['weighted_mean_twist_deg']==55
    assert edge['signed_bp_per_turn']==pytest.approx(360/55)
    junction=summary(values,[.5,1,1,1,1,1,1,.5])
    assert junction['coverage']['declared_weight']==7
    assert junction['weighted_mean_twist_deg']==pytest.approx(55)
    local=summary(values,[0,0,0,1,1,0,0,0])
    assert local['weighted_mean_twist_deg']==55
    assert [r['weight']for r in local['steps']]==[0,0,0,1,1,0,0,0]
    assert local['method']=='declared-weighted-simple-twist-v1'


def test_missing_positive_weight_never_renormalizes_or_fills_zero():
    r=summary([20,None,40],[1,1,1])
    assert r['weighted_mean_twist_deg']is None and r['signed_bp_per_turn']is None
    assert r['reason']=='INCOMPLETE_WEIGHTED_COVERAGE'
    assert r['coverage']['measured_weight']==2 and r['coverage']['declared_weight']==3
    assert r['steps'][1]['reason']=='DECLARED_BREAK'
    excluded=summary([None,30,40],[0,1,1])
    assert excluded['weighted_mean_twist_deg']==35


def test_gaps_and_angle_branch_ambiguity_do_not_become_a_helix():
    assert summary([20,None,40],[1,0,1])['reason']=='DISCONTIGUOUS_WEIGHTED_REGION'
    assert summary([179,-179],[1,1])['reason']=='AMBIGUOUS_ANGLE_BRANCH'
    assert summary([90,-90],[1,1])['reason']=='AMBIGUOUS_ANGLE_BRANCH'


@pytest.mark.parametrize('values,expected',[([0,0],0),([30,-30],0),([.02,.04],.03)])
def test_near_zero_mean_remains_measured_without_unbounded_repeat(values,expected):
    r=summary(values,[1,1])
    assert r['weighted_mean_twist_deg']==pytest.approx(expected)
    assert r['status']=='MEASURED' and r['signed_bp_per_turn']is None
    assert r['repeat_reason']=='MEAN_AT_OR_BELOW_DECLARED_LIMIT'


def test_negative_handedness_and_weight_scale_are_retained():
    r=summary([-30,-40],[1,3])
    assert r['weighted_mean_twist_deg']==-37.5 and r['signed_bp_per_turn']==-9.6
    assert summary([-30,-40],[1e200,3e200])['weighted_mean_twist_deg']==-37.5


@pytest.mark.parametrize('weights', [[],[1],[-1,1],[0,0],[True,1],[float('nan'),1],[float('inf'),1],[1e308,1e308]])
def test_invalid_or_overflowing_weights_refuse(weights):
    with pytest.raises(ValueError):summary([20,40],weights)


@pytest.mark.parametrize('minimum',[None,True,0,-1,180,float('nan'),float('inf')])
def test_repeat_limit_must_be_explicit_finite_and_bounded(minimum):
    with pytest.raises(ValueError):summary([20,40],[1,1],minimum)


def test_whole_model_measurement_keeps_raw_step_provenance(tmp_path):
    pytest.importorskip('gemmi')
    from .test_helical_twist import model,region
    p=tmp_path/'model.pdb';p.write_text(model(30));pin=sha256(p.read_bytes()).hexdigest()
    r=inspect_weighted_twist(p,region(),expected_model_sha256=pin,
        max_ring_fit_rmsd_angstrom=.15,step_weights=(.5,1),min_abs_mean_twist_deg=.1)
    s=r['regional_twist_summary']
    assert s['weighted_mean_twist_deg']==pytest.approx(30,abs=.02)
    assert s['signed_bp_per_turn']==pytest.approx(12,abs=.01)
    assert r['source']['sha256']==pin
    assert r['simple_step_twist']['pair_frames'][0]['base_frames'][0]['atoms']
    assert r['coordinate_changes']is False
    d=region();d=replace(d,pairs=(d.pairs[0],replace(d.pairs[1],break_before=True),d.pairs[2]))
    r=inspect_weighted_twist(p,d,expected_model_sha256=pin,
        max_ring_fit_rmsd_angstrom=.15,step_weights=(.5,1),min_abs_mean_twist_deg=.1)
    assert r['regional_twist_summary']['reason']=='INCOMPLETE_WEIGHTED_COVERAGE'
