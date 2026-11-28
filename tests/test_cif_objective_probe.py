"""Whole-objective probes must not invent or switch restraint families."""
from copy import deepcopy
import json
import math
import pytest


def quadratic(points, *, bias=0., metadata=None):
    values=[v for p in points for v in p]
    return {'target':sum((i+1)*v*v for i,v in enumerate(values)),
            'gradient':[2*(i+1)*v+bias for i,v in enumerate(values)],
            'metadata':{} if metadata is None else metadata}


@pytest.mark.parametrize('bias',[0.,.5])
def test_single_callback_preserves_inputs_and_exposes_biased_forces(bias):
    from nasolve.cif_objective_probe import probe_objective,review_objective_probe
    points=[[.2,.4,.6],[.8,1.,1.2]];before=deepcopy(points);calls=[]
    def evaluate(p):
        calls.append(deepcopy(p));value=quadratic(p,bias=bias,metadata={'normalization':1.})
        p[0][0]=999 # A native adapter must receive its own coordinate copy.
        return value
    result=probe_objective(evaluate,points,[0,1]);review=review_objective_probe(result)
    assert points==before and result['evaluation_calls']==len(calls)<=256
    assert calls[-1]==before and all(len(p)==2 for p in calls)
    assert review['sampled_gradients_consistent'] is (bias==0.)
    assert review['baseline_repeat_consistent'] and review['context_observation']=='UNCHANGED'
    assert result['model_optimization']=='NOT_RUN' and result['scientific_approval']=='NOT_RUN'
    assert result['automatic_adoption'] is False
    assert review==review_objective_probe(json.loads(json.dumps(result)))


def test_point_specific_normalization_is_observed_without_rescaling_or_hiding_it():
    from nasolve.cif_objective_probe import probe_objective,review_objective_probe
    def evaluate(points):
        count=10 if points[0][0]>=1. else 11
        row=quadratic(points)
        return {'target':row['target']/count,'gradient':[g/count for g in row['gradient']],
                'metadata':{'normalization_factor':1/count,'number_of_restraints':count}}
    result=probe_objective(evaluate,[[1.,.5,.25]],[0]);review=review_objective_probe(result)
    assert result['baseline']['metadata']['number_of_restraints']==10
    assert result['baseline']['target']==pytest.approx(quadratic([[1.,.5,.25]])['target']/10)
    assert review['context_observation']=='CHANGED' and not review['sampled_gradients_consistent']
    assert any(s['plus']['metadata']!=s['minus']['metadata'] for d in result['directions'] for s in d['samples'])


def test_metadata_change_is_distinct_from_a_wrong_derivative():
    from nasolve.cif_objective_probe import probe_objective,review_objective_probe
    calls=0
    def evaluate(points):
        nonlocal calls
        calls+=1
        return quadratic(points,metadata={'cache_generation':calls})
    review=review_objective_probe(probe_objective(evaluate,[[.1,.2,.3]],[0]))
    assert review['sampled_gradients_consistent'] and review['context_observation']=='CHANGED'


def test_zero_gradient_and_absent_context_are_not_proof_of_recorded_context():
    from nasolve.cif_objective_probe import probe_objective,review_objective_probe
    def evaluate(points):return {'target':0.,'gradient':[0.]*3}
    result=probe_objective(evaluate,[[0.,0.,0.]],[0]);review=review_objective_probe(result)
    assert review['sampled_gradients_consistent'] and review['context_observation']=='NOT_RECORDED'
    assert [d['name'] for d in result['directions']]==['alternating_global','atom_0_axis_0','atom_0_axis_1','atom_0_axis_2']


@pytest.mark.parametrize('change',['target','gradient'])
def test_repeated_baseline_drift_remains_visible(change):
    from nasolve.cif_objective_probe import probe_objective,review_objective_probe
    calls=0
    def evaluate(points):
        nonlocal calls
        calls+=1;row=quadratic(points)
        if change=='target':row['target']+=calls*.01
        else:row['gradient'][0]+=calls*.01
        return row
    review=review_objective_probe(probe_objective(evaluate,[[.1,.2,.3]],[0]))
    assert not review['baseline_repeat_consistent'] and not review['sampled_gradients_consistent']


@pytest.mark.parametrize('indices',[[True],[0,0],[-1],[1],[]])
def test_invalid_indices_refuse_before_native_call(indices):
    from nasolve.cif_objective_probe import probe_objective
    def no_call(points):pytest.fail('Invalid request reached evaluator')
    with pytest.raises(ValueError):probe_objective(no_call,[[1.,2.,3.]],indices)


@pytest.mark.parametrize('kind',['nan','short','bool','metadata_nan','metadata_large'])
def test_invalid_native_values_refuse(kind):
    from nasolve.cif_objective_probe import probe_objective
    def evaluate(points):
        row=quadratic(points)
        if kind=='nan':row['target']=float('nan')
        if kind=='short':row['gradient']=[]
        if kind=='bool':row['gradient'][0]=True
        if kind=='metadata_nan':row['metadata']={'bad':float('inf')}
        if kind=='metadata_large':row['metadata']={'large':'x'*20000}
        return row
    with pytest.raises(ValueError):probe_objective(evaluate,[[1.,2.,3.]],[0])


def test_budget_is_bounded_and_report_cannot_forge_probe_order_or_arithmetic():
    from nasolve.cif_objective_probe import probe_objective,review_objective_probe
    calls=0
    def evaluate(points):
        nonlocal calls
        calls+=1;return quadratic(points)
    with pytest.raises(ValueError,match='budget'):probe_objective(evaluate,[[1.,2.,3.]],[0],max_calls=1)
    assert calls<=1
    result=probe_objective(evaluate,[[1.,2.,3.]],[0])
    for mutate in [lambda r:r.update(evaluation_calls=1),lambda r:r['directions'][0].update(name='forged'),
                   lambda r:r['directions'][0]['samples'][0].update(step=42),
                   lambda r:r['directions'][0]['samples'].pop(),lambda r:r.update(automatic_adoption=True)]:
        forged=deepcopy(result);mutate(forged)
        with pytest.raises(ValueError):review_objective_probe(forged)
    changed=deepcopy(result);changed['directions'][0]['samples'][0]['plus']['target']+=100
    # The reader recalculates arithmetic; it does not authenticate native execution.
    observed=review_objective_probe(changed)
    assert observed['directions'][0]['samples'][0]['consistent'] is False
