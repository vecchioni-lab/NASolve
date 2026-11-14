from types import SimpleNamespace
import pytest
from nasolve.topostitch_trial import check_masked_derivatives
from nasolve.topostitch_native_recipe import NativeMaskedObjective
from nasolve.topostitch_transport import CoordinateMask


def test_complete_derivatives_use_both_steps_and_retain_actual_samples():
    calls=[]
    def evaluate(x):
        calls.append(tuple(x));return dict(target=x[0]**4+3*x[1]**2,gradient=[4*x[0]**3,6*x[1]])
    report=check_masked_derivatives(evaluate,[.2,-.3])
    assert report['status']=='DERIVATIVES_PASS'
    assert len(calls)==report['evaluation_calls']==10
    assert [r['step_angstrom'] for r in report['derivatives']]==[1e-4,1e-5]
    assert all(len(r['rows'])==2 for r in report['samples'])
    assert report['exact_repeat']


def test_wrong_gradient_and_step_truncation_remain_review():
    bad=lambda x:dict(target=x[0]**2,gradient=[0.])
    assert check_masked_derivatives(bad,[1.])['status']=='DERIVATIVE_REVIEW'
    strained=lambda x:dict(target=1e6*x[0]**4,gradient=[4e6*x[0]**3])
    assert check_masked_derivatives(strained,[1.])['status']=='DERIVATIVE_REVIEW'


def test_nondeterminism_and_nonfinite_values_do_not_pass():
    calls=[]
    def changed(x):
        calls.append(x);return dict(target=sum(v*v for v in x)+len(calls),gradient=[2*v for v in x])
    with pytest.raises(ValueError,match='repeat'):check_masked_derivatives(changed,[1.])
    with pytest.raises(ValueError):check_masked_derivatives(lambda x:dict(target=float('nan'),gradient=[0.]),[0.])
    with pytest.raises(ValueError):check_masked_derivatives(lambda x:None,[0.]*1201)


@pytest.mark.parametrize('include',[True,False])
def test_pair_control_changes_only_pair_contribution_and_keeps_raw_score(include):
    # Exercise the actual composition independently of Phenix construction. Real
    # manager identity/derivatives are qualified by the native controls separately.
    objective=object.__new__(NativeMaskedObjective)
    objective._mask=CoordinateMask(((0,0,0),(3,0,0)),(0,),1)
    objective._calls=0;objective._max_calls=100;objective._check_native=lambda points:None
    objective._geometry=object();objective._gr=object();objective._flex=object()
    objective._flags=SimpleNamespace(flags=lambda **kw:object());objective._identities=['first','fixed']
    def native(_,points,*args,**kw):
        return dict(target=sum(v*v for p in points for v in p),gradient=[2*v for p in points for v in p],terms={},proxy_counts={})
    def pair(points,**kw):
        d=points[0][0]-points[1][0]+1
        return dict(target=d*d,gradients=((2*d,0,0),(-2*d,0,0)),components={'bond':d*d})
    objective._correction=SimpleNamespace(evaluate_fixed_native=native)
    objective._pairs=SimpleNamespace(evaluate=pair);objective._pair_weight=1. if include else 0.;objective._tether_weight=.25
    report=objective.evaluate([.2,0,0]);weight=1 if include else 0
    assert report['target']==pytest.approx(9.04+weight*3.24+.01)
    assert report['gradient'][0]==pytest.approx(.5-weight*3.6)
    assert report['unweighted_pair_target']==pytest.approx(3.24)
    assert report['pair_target']==pytest.approx(weight*3.24)
    assert report['points'][1]==(3.,0.,0.)


def test_pair_control_requires_boolean_before_loading_native_sdk():
    with pytest.raises(ValueError,match='explicit boolean'):
        NativeMaskedObjective(None,None,b'',None,movable_indices=[],expected_native_signature='',
            correction=None,native_audit=None,tether_sigma_angstrom=1,max_displacement_angstrom=1,
            max_evaluations=100,include_pairs='yes')
