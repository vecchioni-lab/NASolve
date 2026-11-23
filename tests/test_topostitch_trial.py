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


class ObservationObjective:
    def __init__(self,budget=100):
        self._mask=CoordinateMask(((1.,2.,3.),(4.,5.,6.)),(0,),.1)
        self._calls=0;self.budget=budget;self.changed=False
    def binding_report(self):return dict(max_evaluations=self.budget)
    def evaluate(self,delta):
        self._calls+=1;points=self._mask.expand(delta)
        target=sum(v*v for p in points for v in p)+int(self.changed)
        return dict(points=points,target=target,native_target=target,gradient=[2*v for v in points[0]],
            native_components={'bond_residual_sum':target},native_proxy_counts={'n_bond_proxies':1},evaluation_calls=self._calls)


def observation_cases():
    return dict(source=[[1.,2.,3.],[4.,5.,6.]],full_precision=[[1.0014,2.,3.],[4.,5.,6.]],rounded=[[1.001,2.,3.],[4.,5.,6.]])


def observed_pairs(points):
    from copy import deepcopy
    row=dict(target=sum(v*v for p in points for v in p),gradient=[2*v for p in points for v in p],proxy_counts={'n_bond_proxies':1})
    return dict(snapshots=[row,deepcopy(row)])


def test_endpoint_observer_retains_actual_snapshots_and_never_optimizes():
    from nasolve.topostitch_trial import observe_masked_coordinates
    objective=ObservationObjective();calls=[]
    def pairs(points):calls.append(points);return observed_pairs(points)
    result=observe_masked_coordinates(objective,observation_cases(),capture_pairs=pairs)
    assert result['status']=='COORDINATE_OBSERVATIONS_REVIEW'
    assert result['objective_evaluation_calls']==9 and len(calls)==3
    assert result['derivative_qualification']=='NOT_RUN' and not result['optimization']
    assert not result['automatic_adoption'] and not result['scientific_acceptance']
    assert [r['points'] for r in result['cases']]==calls
    assert all(len(r['native_energy_snapshots'])==2 and r['exact_repeat'] for r in result['cases'])


@pytest.mark.parametrize('failure',['target','counts','state','snapshots'])
def test_inconsistent_endpoint_capture_retains_partial_failed_evidence(failure):
    from nasolve.topostitch_trial import observe_masked_coordinates
    objective=ObservationObjective()
    def pairs(points):
        value=observed_pairs(points)
        if failure=='target':value['snapshots'][0]['target']+=1
        elif failure=='counts':value['snapshots'][0]['proxy_counts']={}
        elif failure=='snapshots':value['snapshots'].pop()
        else:objective.changed=True
        return value
    result=observe_masked_coordinates(objective,observation_cases(),capture_pairs=pairs)
    assert result['status']=='FAILED' and result['error']
    assert len(result['cases'])==1 and 'nonbonded_inventory' in result['cases'][0]
    assert not result['automatic_adoption']


def test_endpoint_observer_admits_complete_cases_and_budget_before_evaluation():
    from nasolve.topostitch_trial import observe_masked_coordinates
    objective=ObservationObjective(budget=8)
    with pytest.raises(ValueError,match='budget'):observe_masked_coordinates(objective,observation_cases(),capture_pairs=observed_pairs)
    assert objective._calls==0
    with pytest.raises(ValueError,match='Require source'):observe_masked_coordinates(objective,{},capture_pairs=observed_pairs)


def test_endpoint_pair_attribution_must_match_raw_unweighted_score():
    from nasolve.topostitch_trial import observe_masked_coordinates
    objective=ObservationObjective();evaluate=objective.evaluate
    def with_pair_score(delta):
        return dict(evaluate(delta),unweighted_pair_target=3.)
    objective.evaluate=with_pair_score
    result=observe_masked_coordinates(objective,observation_cases(),capture_pairs=observed_pairs,
        describe_pairs=lambda points:dict(target=4.))
    assert result['status']=='FAILED' and 'raw pair target' in result['error']
    assert not result['scientific_acceptance']


@pytest.fixture
def fake_optimizer(tmp_path, monkeypatch):
    """A line search can restore its best trial even when that trial was rejected."""
    import sys
    lbfgs=SimpleNamespace(__file__=str(tmp_path/'lbfgs.py'))
    extension=SimpleNamespace(__file__=str(tmp_path/'extension.py'))
    for module in (lbfgs,extension):
        from pathlib import Path
        Path(module.__file__).write_text('# pinned synthetic optimizer\n')
    lbfgs.termination_parameters=lambda **kw:kw
    lbfgs.exception_handling_parameters=lambda **kw:kw
    lbfgs.traditional_convergence_test=lambda *a:lambda *a:False
    flex=SimpleNamespace(double=lambda x,value=None: [value]*x if isinstance(x,int) else list(x))
    monkeypatch.setitem(sys.modules,'scitbx',SimpleNamespace(lbfgs=lbfgs))
    monkeypatch.setitem(sys.modules,'scitbx.lbfgs',lbfgs)
    monkeypatch.setitem(sys.modules,'scitbx_lbfgs_ext',extension)
    monkeypatch.setitem(sys.modules,'scitbx.array_family',SimpleNamespace(flex=flex))
    return lbfgs


class TrialObjective:
    def __init__(self):
        self._mask=CoordinateMask(((1.,2.,3.),(4.,5.,6.)),(0,),1.)
        self._calls=0;self.budget=100;self.shift=0.;self.bad_gradient=False;self.visited=[]
    def binding_report(self):return dict(movable_indices=[0],max_evaluations=self.budget)
    def evaluate(self,x):
        self._calls+=1;self.visited.append(tuple(x))
        if self._calls>self.budget:raise ValueError('objective budget exhausted')
        target=(x[0]-.3)**2+x[1]**2+x[2]**2+self.shift
        gradient=[2*(x[0]-.3),2*x[1],2*x[2]]
        if self.bad_gradient:gradient[0]+=1.
        return dict(target=target,native_target=target,pair_target=0.,unweighted_pair_target=0.,
            tether_target=0.,gradient=gradient,points=self._mask.expand(x))


def failed_optimizer(lbfgs, objective, *, accepted=True, mode=None):
    def run(*,target_evaluator,exception_handling_params,**kwargs):
        assert exception_handling_params['ignore_line_search_failed_rounding_errors'] is False
        target_evaluator.x[:]=[.2004,0.,0.]
        target_evaluator.compute_functional_and_gradients()
        if accepted:
            target_evaluator.callback_after_step(SimpleNamespace(iter=lambda:1,nfun=lambda:1))
        # A lower-energy trial exists, but the optimizer has not accepted it.
        target_evaluator.x[:]=[.3,0.,0.]
        target_evaluator.compute_functional_and_gradients()
        if mode=='drift':objective.shift=1.
        elif mode=='gradient':objective.bad_gradient=True
        elif mode=='budget':objective._calls=objective.budget-1
        elif mode=='missing_source':
            from pathlib import Path
            Path(lbfgs.__file__).unlink()
        elif mode=='source':
            from pathlib import Path
            Path(lbfgs.__file__).write_text('# source changed\n')
        raise RuntimeError('original line-search failure')
    lbfgs.run=run


def test_failed_trial_audits_accepted_step_not_best_rejected_trial(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();failed_optimizer(fake_optimizer,objective)
    report=run_native_masked_trial(objective,max_iterations=2,max_calls=10)
    assert report['status']=='FAILED' and report['error']=='RuntimeError: original line-search failure'
    assert 'failed_proposal' not in report  # Evaluations returned before the optimizer failed.
    assert report['trace'][1]['target']<report['trace'][0]['target']
    diagnostic=report['failure_endpoint']
    assert diagnostic['status']=='DERIVATIVES_PASS' and diagnostic['exact_trace_replay']
    assert diagnostic['accepted_step']==dict(iteration=1,calls=1,trace_index=0)
    assert diagnostic['coordinate_origin']=='LAST_ACCEPTED_OPTIMIZER_STEP'
    assert diagnostic['full_precision_derivatives']['baseline']['points'][0][0]==pytest.approx(1.2004)
    assert diagnostic['serialized_derivatives']['baseline']['points'][0][0]==pytest.approx(1.200)
    assert diagnostic['evaluation_calls']==28
    assert 'full_precision_derivatives' not in report and 'stopping' not in report
    assert not report['scientific_acceptance'] and not report['automatic_adoption']
    assert objective._calls==44


def test_failure_before_accepted_step_has_no_invented_endpoint(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();failed_optimizer(fake_optimizer,objective,accepted=False)
    report=run_native_masked_trial(objective,max_iterations=2,max_calls=10)
    assert report['failure_endpoint']['status']=='NO_ACCEPTED_STEP'
    assert report['failure_endpoint']['evaluation_calls']==0 and objective._calls==16
    assert report['status']=='FAILED'


@pytest.mark.parametrize('mode,status',[('drift','FAILED'),('gradient','FAILED'),('budget','INSUFFICIENT_BUDGET'),('source','FAILED'),('missing_source','FAILED')])
def test_failure_diagnostics_never_replace_original_error(fake_optimizer,mode,status):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();failed_optimizer(fake_optimizer,objective,mode=mode)
    report=run_native_masked_trial(objective,max_iterations=2,max_calls=10)
    assert report['error']=='RuntimeError: original line-search failure' and report['status']=='FAILED'
    diagnostic=report['failure_endpoint'];assert diagnostic['status']==status
    if mode in ('drift','gradient'):assert 'replay' in diagnostic['error']
    if mode in ('budget','source','missing_source'):assert diagnostic['evaluation_calls']==0
    assert not report['automatic_adoption']


def test_trial_failure_endpoint_derivative_review_stays_failed(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();original=objective.evaluate
    def evaluate(x):
        value=original(x)
        # Same baseline and gradient norm, but incorrect derivatives nearby.
        if objective._calls>17 and tuple(x)!=(.2004,0.,0.):value['target']+=x[1]
        return value
    objective.evaluate=evaluate;failed_optimizer(fake_optimizer,objective)
    report=run_native_masked_trial(objective,max_iterations=2,max_calls=10)
    assert report['status']=='FAILED'
    assert report['failure_endpoint']['status']=='DERIVATIVE_REVIEW'
    assert report['error']=='RuntimeError: original line-search failure'


def test_successful_trial_retains_existing_endpoint_and_stopping_fields(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective()
    def run(*,target_evaluator,log,**kw):
        target_evaluator.x[:]=[.2004,0.,0.];target_evaluator.compute_functional_and_gradients()
        optimizer=SimpleNamespace(iter=lambda:2,nfun=lambda:1,error=None)
        target_evaluator.callback_after_step(optimizer)
        log.write('lbfgs minimizer stop: max_iterations\n')
        return optimizer
    fake_optimizer.run=run
    report=run_native_masked_trial(objective,max_iterations=2,max_calls=10)
    assert report['status']=='ENDPOINT_DERIVATIVES_PASS'
    assert report['stopping']['reason']=='max_iterations'
    assert 'failure_endpoint' not in report and 'failed_proposal' not in report


def test_unmatched_callback_cannot_mislabel_an_evaluated_trial_as_accepted(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective()
    def run(*,target_evaluator,**kw):
        target_evaluator.compute_functional_and_gradients()
        target_evaluator.x[0]=.2
        target_evaluator.callback_after_step(SimpleNamespace(iter=lambda:1,nfun=lambda:1))
        raise AssertionError('Mismatched callback should have refused')
    fake_optimizer.run=run
    report=run_native_masked_trial(objective,max_iterations=2,max_calls=10)
    assert report['status']=='FAILED' and 'accepted' in report['error']
    assert report['accepted_steps']==[] and report['failure_endpoint']['status']=='NO_ACCEPTED_STEP'


def test_failure_during_rounded_audit_retains_full_precision_and_original_error(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();original=objective.evaluate
    def evaluate(x):
        if objective._calls>=30:raise RuntimeError('rounded observation unavailable')
        return original(x)
    objective.evaluate=evaluate;failed_optimizer(fake_optimizer,objective)
    report=run_native_masked_trial(objective,max_iterations=2,max_calls=10)
    assert report['status']=='FAILED' and report['error']=='RuntimeError: original line-search failure'
    diagnostic=report['failure_endpoint']
    assert diagnostic['status']=='FAILED' and 'rounded observation unavailable' in diagnostic['error']
    assert diagnostic['full_precision_derivatives']['status']=='DERIVATIVES_PASS'
    assert 'serialized_derivatives' not in diagnostic



def test_native_motion_view_retains_cartesian_evaluation_and_complete_chain_rule():
    from nasolve.topostitch_transport import TaperedMotion
    objective=object.__new__(NativeMaskedObjective)
    objective._mask=CoordinateMask(((2.,1.,3.),(4.,2.,-1.),(8.,9.,10.)),(1,0),2.)
    calls=[]
    def evaluate(delta):
        calls.append(delta);points=objective._mask.expand(delta)
        # An independent coupled target includes a fixed-context atom and a
        # displacement tether. The motion view must keep every contribution.
        a,b,c=points;v=tuple(x-y for x,y in zip(a,c));u=tuple(x-y for x,y in zip(b,a))
        full=(tuple(2*x-6*y for x,y in zip(v,u)),tuple(6*x for x in u),tuple(-2*x for x in v))
        return dict(target=sum(x*x for x in v)+3*sum(x*x for x in u)+.5*sum(x*x for x in delta),
            gradient=tuple(g+x for g,x in zip(objective._mask.project(full),delta)),points=points,
            native_target=123.,pair_target=456.,tether_target=.5*sum(x*x for x in delta),evaluation_calls=len(calls))
    objective.evaluate=evaluate;motion=TaperedMotion(objective._mask,(1.,2.,0.),(.5,1.,0.));q=(.2,-.15,.1,.03,-.02,.01)
    actual=objective.evaluate_motion(motion,q);assert len(calls)==1
    direct=evaluate(motion.displacements(q))
    for key in direct:
        if key not in ('gradient','evaluation_calls'):assert actual[key]==direct[key]
    assert actual['cartesian_gradient']==direct['gradient'] and len(actual['gradient'])==6
    assert actual['parameters']==q and actual['parameterization']=='tapered-rotation-degrees-translation-angstrom-v1'
    for k in range(6):
        plus=list(q);minus=list(q);plus[k]+=1e-4;minus[k]-=1e-4
        fd=(objective.evaluate_motion(motion,plus)['target']-objective.evaluate_motion(motion,minus)['target'])/2e-4
        assert actual['gradient'][k]==pytest.approx(fd,abs=1e-7)
    before=len(calls)
    bad=TaperedMotion(CoordinateMask(objective._mask.reference,(0,1),2.),motion.origin,motion.weights)
    with pytest.raises(ValueError,match='mask'):objective.evaluate_motion(bad,q)
    with pytest.raises(ValueError):objective.evaluate_motion(motion,(float('inf'),)*6)
    assert len(calls)==before



def test_native_motion_checks_exact_source_even_with_identical_coordinates():
    from nasolve.topostitch_transport import TaperedMotion
    objective=object.__new__(NativeMaskedObjective)
    objective._mask=CoordinateMask(((1.,2.,3.),),(0,),1.)
    objective._report={'source_model_sha256':'a'*64}
    calls=[]
    def evaluate(delta):
        calls.append(delta)
        return {'target':0.,'gradient':(0.,0.,0.)}
    objective.evaluate=evaluate
    wrong=TaperedMotion(objective._mask,(0.,0.,0.),(1.,),source_model_sha256='b'*64)
    with pytest.raises(ValueError,match='source model'):objective.evaluate_motion(wrong,(0.,)*6)
    assert calls==[]
    right=TaperedMotion(objective._mask,(0.,0.,0.),(1.,),source_model_sha256='a'*64)
    assert objective.evaluate_motion(right,(0.,)*6)['target']==0.
    assert len(calls)==1



def test_explicit_atomic_start_keeps_source_reference_and_seed_audits(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();source=objective._mask.reference;seed=[.1254,.02,-.01]
    original=objective.evaluate
    def evaluate(x):
        value=original(x)
        seed[:]=[.9,.9,.9]  # Caller mutation must not change the frozen start.
        return value
    objective.evaluate=evaluate
    def run(*,target_evaluator,termination_params,exception_handling_params,log,**kw):
        assert list(target_evaluator.x)==[.1254,.02,-.01]
        assert termination_params['traditional_convergence_test_eps']==1e-5
        assert exception_handling_params['ignore_line_search_failed_rounding_errors'] is False
        target_evaluator.compute_functional_and_gradients()
        target_evaluator.x[:]=[.2004,0.,0.];target_evaluator.compute_functional_and_gradients()
        opt=SimpleNamespace(iter=lambda:1,nfun=lambda:2,error=None)
        target_evaluator.callback_after_step(opt);log.write('lbfgs minimizer stop: max_iterations\n');return opt
    fake_optimizer.run=run
    result=run_native_masked_trial(objective,max_iterations=2,max_calls=10,initial_displacements=seed)
    assert result['status']=='ENDPOINT_DERIVATIVES_PASS'
    assert objective.visited[0]==(.1254,.02,-.01)
    assert result['initialization']=={'coordinate_origin':'EXPLICIT_DIAGNOSTIC_START',
        'reference':'ORIGINAL_OBJECTIVE_SOURCE','displacements':[.1254,.02,-.01]}
    assert result['initial_derivatives']['baseline']['target']==pytest.approx((.1254-.3)**2+.02**2+.01**2)
    assert result['trace'][0]['displacements']==[.1254,.02,-.01]
    assert objective._mask.reference==source
    assert result['full_precision_derivatives']['baseline']['points'][1]==source[1]
    assert result['serialized_derivatives']['baseline']['points'][0][0]==pytest.approx(1.2)
    assert not result['stopping']['native_criterion_met']  # Cap is not convergence.
    assert not result['scientific_acceptance'] and not result['automatic_adoption']


def test_explicit_start_is_not_an_accepted_optimizer_step(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective()
    def run(**kw):raise RuntimeError('failure before accepting anything')
    fake_optimizer.run=run
    result=run_native_masked_trial(objective,max_iterations=2,max_calls=10,initial_displacements=[.1,0.,0.])
    assert result['status']=='FAILED' and result['failure_endpoint']['status']=='NO_ACCEPTED_STEP'
    assert result['accepted_steps']==[] and result['trace']==[]
    assert result['initialization']['coordinate_origin']=='EXPLICIT_DIAGNOSTIC_START'
    assert 'full_precision_derivatives' not in result


def test_explicit_start_does_not_promote_subsequent_failed_trial(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();failed_optimizer(fake_optimizer,objective)
    result=run_native_masked_trial(objective,max_iterations=2,max_calls=10,initial_displacements=[.1,0.,0.])
    assert result['status']=='FAILED' and result['error']=='RuntimeError: original line-search failure'
    assert result['initial_derivatives']['baseline']['points'][0][0]==1.1
    assert result['failure_endpoint']['full_precision_derivatives']['baseline']['points'][0][0]==pytest.approx(1.2004)
    assert 'full_precision_derivatives' not in result and 'stopping' not in result


@pytest.mark.parametrize('seed',[[],[.1],[0.,0.,0.,0.],[float('nan'),0.,0.],[float('inf'),0.,0.],[True,0.,0.],[1.01,0.,0.],'abc'])
def test_invalid_atomic_start_refused_before_evaluation(fake_optimizer,seed):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective()
    with pytest.raises(ValueError):run_native_masked_trial(objective,max_iterations=2,max_calls=10,initial_displacements=seed)
    assert objective._calls==0


def test_explicit_start_does_not_bypass_budget_or_initial_gradient_gate(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();objective.budget=20
    with pytest.raises(ValueError,match='budget'):
        run_native_masked_trial(objective,max_iterations=2,max_calls=10,initial_displacements=[.1,0.,0.])
    assert objective._calls==0
    objective.budget=100;objective.bad_gradient=True
    fake_optimizer.run=lambda **kw:pytest.fail('Initial bad derivatives cannot launch the optimizer')
    result=run_native_masked_trial(objective,max_iterations=2,max_calls=10,initial_displacements=[.1,0.,0.])
    assert result['status']=='INITIAL_DERIVATIVE_REVIEW' and not result['optimization_started']


def test_default_atomic_start_report_and_behavior_remain_unchanged(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    first=TrialObjective();failed_optimizer(fake_optimizer,first)
    default=run_native_masked_trial(first,max_iterations=2,max_calls=10)
    second=TrialObjective();failed_optimizer(fake_optimizer,second)
    explicit=run_native_masked_trial(second,max_iterations=2,max_calls=10,initial_displacements=[0.,0.,0.])
    assert explicit.pop('initialization')['coordinate_origin']=='EXPLICIT_DIAGNOSTIC_START'
    assert default==explicit and first.visited==second.visited



def test_atomic_start_checks_remaining_not_original_evaluation_budget(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective=TrialObjective();objective._calls=50;objective.budget=100
    fake_optimizer.run=lambda **kw:pytest.fail('Insufficient remaining budget must refuse before optimizer')
    with pytest.raises(ValueError,match='budget'):
        run_native_masked_trial(objective,max_iterations=2,max_calls=10,initial_displacements=[.1,0.,0.])
    assert objective._calls==50 and objective.visited==[]


@pytest.fixture
def guarded_objective(tmp_path):
    # Protocol doubles only: the pinned native owner is qualified separately.
    import json
    from hashlib import sha256
    objective=object.__new__(NativeMaskedObjective)
    objective._mask=CoordinateMask(((0,0,0),),(0,),1)
    objective._calls=0;objective._max_calls=10
    objective._geometry=SimpleNamespace(policy={'unused_radius':1.9},cache=0)
    objective._gr=object();objective._flex=object();objective._identities=['first']
    objective._pair_weight=0.;objective._tether_weight=.25
    trace=[];active=SimpleNamespace(nonbonded=True)
    objective._flags=SimpleNamespace(flags=lambda **kw:active)
    def static(points):trace.append('static');objective._geometry.cache+=1
    objective._check_native=static
    def native(geo,points,flags,*args,**kwargs):
        assert flags is active and kwargs=={'plane_order_safe':True}
        trace.append('native');geo.cache+=1
        return dict(target=1.,gradient=[2.,0.,0.],terms={},proxy_counts={})
    objective._correction=SimpleNamespace(evaluate_fixed_native=native)
    objective._pairs=SimpleNamespace(evaluate=lambda *a,**kw:dict(target=0.,gradients=((0.,0.,0.),),components={}))
    source=tmp_path/'owner.py';source.write_text('# trusted test double')
    profile=tmp_path/'data/nonbonded-native-profile.json';profile.parent.mkdir();profile.write_text('{}')
    def require(geo,expected,**options):
        trace.append('guard')
        assert options['flags'] is active
        assert {k:v for k,v in options.items() if k!='flags'}==dict(normalization=False,
            compute_gradients=True,disable_asu_cache=False,gradients=None,
            custom_nonbonded_function=None,external_energy_function=None,extension_objects=())
        if geo.policy!=expected['policy'] or not active.nonbonded:raise ValueError('Policy changed')
        return expected
    owner=SimpleNamespace(__file__=str(source),require_live_nonbonded_policy=require)
    expected=dict(policy={'unused_radius':1.9},policy_id='synthetic',native_profile_id='synthetic',policy_sha256='d'*64)
    provenance=objective._bind_live_policy(owner,expected,active)
    assert provenance['owner_source_sha256']==sha256(source.read_bytes()).hexdigest()
    assert provenance['native_profile_sha256']==sha256(profile.read_bytes()).hexdigest()
    trace.clear()
    return objective,expected,trace,active


def test_live_policy_uses_actual_flags_and_brackets_native_helpers(guarded_objective):
    objective,expected,trace,active=guarded_objective
    result=objective.evaluate((.2,0,0))
    assert trace[0]==trace[-1]=='guard'
    assert trace.index('guard')<trace.index('static')<trace.index('native')
    assert trace.count('static')==2 and trace.count('native')==1
    assert result['target']==1.01 and result['gradient']==(2.1,0.,0.)
    assert 'live_nonbonded_policy' not in result  # binding provenance only
    assert objective._geometry.cache==3


def test_live_policy_detaches_baseline_and_refuses_preexisting_drift(guarded_objective):
    objective,expected,trace,active=guarded_objective
    expected['policy']['unused_radius']=2.1
    objective.evaluate((0,0,0))  # original caller dict cannot redefine expectation
    trace.clear();objective._geometry.policy['unused_radius']=2.1
    with pytest.raises(ValueError,match='Policy changed'):objective.evaluate((0,0,0))
    assert trace==['guard'] and objective._calls==2


@pytest.mark.parametrize('where',['native','final_static','flags'])
def test_live_policy_rejects_mutation_before_returning_identical_energy(guarded_objective,where):
    objective,expected,trace,active=guarded_objective
    if where=='final_static':
        original=objective._check_native
        def change(points):
            original(points)
            if trace.count('static')==2:objective._geometry.policy['unused_radius']=9.
        objective._check_native=change
    else:
        original=objective._correction.evaluate_fixed_native
        def change(*args,**kw):
            value=original(*args,**kw)
            if where=='flags':active.nonbonded=False
            else:objective._geometry.policy['unused_radius']=9.
            return value
        objective._correction.evaluate_fixed_native=change
    with pytest.raises(ValueError,match='Policy changed'):objective.evaluate((0,0,0))
    assert trace[-1]=='guard'


def test_live_policy_preserves_native_error_and_exhausted_budget(guarded_objective):
    objective,expected,trace,active=guarded_objective
    def fail(*args,**kw):
        objective._geometry.policy['unused_radius']=9.
        raise RuntimeError('original native error')
    objective._correction.evaluate_fixed_native=fail
    with pytest.raises(RuntimeError,match='original native error'):objective.evaluate((0,0,0))
    trace.clear();objective._calls=objective._max_calls
    with pytest.raises(ValueError,match='budget exhausted'):objective.evaluate((0,0,0))
    assert not trace


@pytest.mark.parametrize('arguments',[{'live_policy_owner':object()},{'expected_live_policy':{}},
    {'live_policy_owner':object(),'expected_live_policy':{}}])
def test_live_policy_invalid_dependency_refuses_before_sdk_import(arguments):
    with pytest.raises(ValueError,match='live policy'):
        NativeMaskedObjective(None,None,b'',None,movable_indices=[],expected_native_signature='',
            correction=None,native_audit=None,tether_sigma_angstrom=1,max_displacement_angstrom=1,
            max_evaluations=100,**arguments)


def motion_case():
    from nasolve.topostitch_transport import TaperedMotion
    motion=TaperedMotion(CoordinateMask(((1.,0.,0.),(0.,0.,0.)),(0,),2.),
        (0.,0.,0.),(1.,0.),source_model_sha256='a'*64)
    calls=[]
    def evaluate(parameters):
        calls.append(tuple(parameters));target=sum((x-y)**2 for x,y in zip(parameters,(0.,0.,0.,.3,0.,0.)))
        return dict(target=target,gradient=tuple(2*(x-y)for x,y in zip(parameters,(0.,0.,0.,.3,0.,0.))),
            points=motion.mask.expand(motion.displacements(list(parameters))))
    return motion,evaluate,calls


def motion_optimizer(lbfgs, *, failed=False, rejected=False, corrupt_source=False):
    def run(*,target_evaluator,log,**kwargs):
        target_evaluator.x[:]=[0.,0.,0.,.2004,0.,0.]
        target_evaluator.compute_functional_and_gradients()
        target_evaluator.callback_after_step(SimpleNamespace(iter=lambda:1,nfun=lambda:1))
        if rejected:
            target_evaluator.x[:]=[0.,0.,0.,.3,0.,0.]
            target_evaluator.compute_functional_and_gradients()
        if corrupt_source:
            from pathlib import Path
            Path(lbfgs.__file__).write_text('# changed optimizer\n')
        if failed:raise RuntimeError('native line search failed')
        log.write('lbfgs minimizer stop: max_iterations\n')
        return SimpleNamespace(error=None,iter=lambda:1,nfun=lambda:2 if rejected else 1)
    lbfgs.run=run


def test_motion_trial_keeps_units_exact_points_and_capped_outcome(fake_optimizer):
    from nasolve.topostitch_trial import run_native_motion_trial
    motion,evaluate,calls=motion_case();motion_optimizer(fake_optimizer)
    result=run_native_motion_trial(evaluate,motion,initial_parameters=[0.]*6,
        max_iterations=1,max_optimizer_calls=5,max_evaluations=58)
    assert result['status']=='ENDPOINT_DERIVATIVES_PASS'
    assert result['stopping']['reason']=='max_iterations'and not result['stopping']['native_criterion_met']
    assert result['callback_evaluations']==len(calls)==54
    assert result['initial_derivatives']['evaluation_calls']==26
    assert result['full_precision_derivatives']['evaluation_calls']==26
    assert result['parameter_units']==['degree']*3+['angstrom']*3
    assert all('step_angstrom'not in r and r['step']in (1e-4,1e-5)
        for r in result['initial_derivatives']['derivatives'])
    assert result['baseline_restoration']['status']=='EXACT_REPEAT'
    assert calls[-1]==(0.,)*6
    assert result['full_precision_derivatives']['baseline']['points'][1]==(0.,0.,0.)
    assert not result['serialized_endpoint_qualified']and not result['scientific_acceptance']
    assert not result['coordinate_writer_called']and not result['automatic_adoption']


def test_motion_trial_failure_never_promotes_lower_rejected_step(fake_optimizer):
    from nasolve.topostitch_trial import run_native_motion_trial
    motion,evaluate,calls=motion_case();motion_optimizer(fake_optimizer,failed=True,rejected=True)
    result=run_native_motion_trial(evaluate,motion,initial_parameters=[0.]*6,
        max_iterations=2,max_optimizer_calls=5,max_evaluations=58)
    assert result['status']=='FAILED'and result['error']=='RuntimeError: native line search failed'
    assert result['trace'][1]['target']<result['trace'][0]['target']
    assert result['accepted_steps']==[dict(iteration=1,calls=1,trace_index=0)]
    assert 'full_precision_derivatives'not in result
    assert result['baseline_restoration']['status']=='EXACT_REPEAT'
    assert len(calls)==29


@pytest.mark.parametrize('failure',['points','gradient','target','wrong_gradient','changed_repeat'])
def test_motion_trial_refuses_bad_callback_before_optimizer(fake_optimizer,failure):
    from nasolve.topostitch_trial import run_native_motion_trial
    motion,evaluate,calls=motion_case();motion_optimizer(fake_optimizer)
    def bad(p):
        row=evaluate(p)
        if failure=='points':row['points']=((99.,0.,0.),(0.,0.,0.))
        elif failure=='gradient':row['gradient']=[0.]*5
        elif failure=='target':row['target']=float('nan')
        elif failure=='wrong_gradient':row['gradient']=[0.]*6
        else:row['target']+=len(calls)*1e-3
        return row
    result=run_native_motion_trial(bad,motion,initial_parameters=[0.]*6,
        max_iterations=2,max_optimizer_calls=5,max_evaluations=58)
    assert not result['optimization_started']
    assert result['status']in ('FAILED','INITIAL_DERIVATIVE_REVIEW')
    assert not result['trace']and not result['automatic_adoption']


@pytest.mark.parametrize('options',[
    {'max_iterations':True},{'max_optimizer_calls':0},{'max_evaluations':57},
    {'initial_parameters':[0.]*5},{'initial_parameters':[0.,0.,0.,3.,0.,0.]}])
def test_motion_trial_bad_declaration_has_no_callback(options):
    from nasolve.topostitch_trial import run_native_motion_trial
    motion,evaluate,calls=motion_case();kwargs=dict(initial_parameters=[0.]*6,
        max_iterations=2,max_optimizer_calls=5,max_evaluations=58);kwargs.update(options)
    with pytest.raises(ValueError):run_native_motion_trial(evaluate,motion,**kwargs)
    assert not calls


def test_motion_trial_requires_a_source_bound_motion():
    from nasolve.topostitch_trial import run_native_motion_trial
    from nasolve.topostitch_transport import TaperedMotion
    motion,evaluate,calls=motion_case();unbound=TaperedMotion(motion.mask,motion.origin,motion.weights)
    with pytest.raises(ValueError,match='source-bound'):
        run_native_motion_trial(evaluate,unbound,initial_parameters=[0.]*6,
            max_iterations=2,max_optimizer_calls=5,max_evaluations=58)
    assert not calls


def test_motion_trial_optimizer_source_drift_keeps_failure(fake_optimizer):
    from nasolve.topostitch_trial import run_native_motion_trial
    motion,evaluate,calls=motion_case();motion_optimizer(fake_optimizer,corrupt_source=True)
    result=run_native_motion_trial(evaluate,motion,initial_parameters=[0.]*6,
        max_iterations=1,max_optimizer_calls=5,max_evaluations=58)
    assert result['status']=='FAILED'and 'sources changed'in result['error']
    assert result['baseline_restoration']['status']=='EXACT_REPEAT'


def test_motion_trial_restoration_failure_cannot_leave_a_pass(fake_optimizer):
    from nasolve.topostitch_trial import run_native_motion_trial
    motion,evaluate,calls=motion_case();motion_optimizer(fake_optimizer)
    def changed(p):
        row=evaluate(p)
        if len(calls)==54:row['target']+=1
        return row
    result=run_native_motion_trial(changed,motion,initial_parameters=[0.]*6,
        max_iterations=1,max_optimizer_calls=5,max_evaluations=58)
    assert result['status']=='FAILED'and result['baseline_restoration']['status']=='FAILED'
    assert 'restor'in result['error'].lower()


def test_motion_trial_checks_optimizer_pins_after_restoration(fake_optimizer):
    from nasolve.topostitch_trial import run_native_motion_trial
    from pathlib import Path
    motion,evaluate,calls=motion_case();motion_optimizer(fake_optimizer)
    def changed(p):
        row=evaluate(p)
        if len(calls)==54:Path(fake_optimizer.__file__).write_text('# changed during restore\n')
        return row
    result=run_native_motion_trial(changed,motion,initial_parameters=[0.]*6,
        max_iterations=1,max_optimizer_calls=5,max_evaluations=58)
    assert result['status']=='FAILED'and 'sources changed'in result['error']
    assert result['baseline_restoration']['status']=='EXACT_REPEAT'


@pytest.mark.parametrize('error,calls,iterations', [('native error',1,1),(None,2,1),(None,1,3)])
def test_motion_trial_rejects_native_error_and_unaccounted_counts(fake_optimizer,error,calls,iterations):
    from nasolve.topostitch_trial import run_native_motion_trial
    motion,evaluate,seen=motion_case();motion_optimizer(fake_optimizer)
    original=fake_optimizer.run
    def changed(**kw):
        original(**kw);return SimpleNamespace(error=error,nfun=lambda:calls,iter=lambda:iterations)
    fake_optimizer.run=changed
    result=run_native_motion_trial(evaluate,motion,initial_parameters=[0.]*6,
        max_iterations=1,max_optimizer_calls=5,max_evaluations=58)
    assert result['status']=='FAILED'and result['error']
    assert 'full_precision_derivatives'not in result
    assert result['baseline_restoration']['status']=='EXACT_REPEAT'


@pytest.mark.parametrize('mode,expected', [
    ('native_error', 'Native optimizer returned an error: returned line-search error'),
    ('wrong_count', 'Native optimizer counts differ'),
    ('iteration_overflow', 'Native optimizer counts differ'),
    ('unaccepted_final', 'Final displacement is not the last accepted optimizer step'),
    ('no_accepted_step', 'Final displacement changed without an accepted step'),
])
def test_atomic_trial_rejects_invalid_returned_optimizer_endpoint(fake_optimizer, mode, expected):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective = TrialObjective()
    def run(*, target_evaluator, **kw):
        target_evaluator.x[:] = [.2004, 0., 0.]
        target_evaluator.compute_functional_and_gradients()
        if mode != 'no_accepted_step':
            target_evaluator.callback_after_step(SimpleNamespace(iter=lambda: 1, nfun=lambda: 1))
        calls = 1
        if mode == 'unaccepted_final':
            target_evaluator.x[:] = [.3, 0., 0.]
            target_evaluator.compute_functional_and_gradients()
            calls += 1
        return SimpleNamespace(error='returned line-search error' if mode == 'native_error' else None,
            iter=lambda: 3 if mode == 'iteration_overflow' else 1,
            nfun=lambda: calls + (mode == 'wrong_count'))
    fake_optimizer.run = run
    report = run_native_masked_trial(objective, max_iterations=2, max_calls=10)
    assert report['status'] == 'FAILED'
    assert expected in report['error']
    assert all(key not in report for key in ('full_precision_derivatives', 'serialized_derivatives', 'stopping'))
    assert not report['scientific_acceptance'] and not report['automatic_adoption']
    diagnostic = report['failure_endpoint']
    if mode == 'no_accepted_step':
        assert diagnostic['status'] == 'NO_ACCEPTED_STEP'
        assert diagnostic['evaluation_calls'] == 0
    else:
        assert diagnostic['status'] == 'DERIVATIVES_PASS'
        assert diagnostic['full_precision_derivatives']['baseline']['points'][0][0] == pytest.approx(1.2004)
        assert diagnostic['optimizer_failure_preserved']


def test_atomic_trial_can_finish_at_unchanged_initial_point_without_accepted_step(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective = TrialObjective()
    def run(*, target_evaluator, **kw):
        target_evaluator.compute_functional_and_gradients()
        return SimpleNamespace(error=None, iter=lambda: 0, nfun=lambda: 1)
    fake_optimizer.run = run
    report = run_native_masked_trial(objective, max_iterations=2, max_calls=10)
    assert report['status'] == 'ENDPOINT_DERIVATIVES_PASS'
    assert report['accepted_steps'] == []
    assert report['full_precision_derivatives']['baseline']['points'] == objective._mask.reference
    assert not report['stopping']['native_criterion_met']


@pytest.mark.parametrize('accepted', [False, True])
def test_failed_objective_retains_first_outside_move_without_evaluating_it_again(fake_optimizer, accepted):
    import json
    from hashlib import sha256
    from nasolve.topostitch_trial import run_native_masked_trial
    objective = TrialObjective()
    objective._mask = CoordinateMask(objective._mask.reference, (1,), 1.)
    objective.binding_report = lambda: dict(movable_indices=[1], max_evaluations=100,
        source_model_sha256='a'*64)
    proposed = [1.2, .1, 0.]
    def run(*, target_evaluator, **kw):
        if accepted:
            target_evaluator.x[:] = [.2004, 0., 0.]
            target_evaluator.compute_functional_and_gradients()
            target_evaluator.callback_after_step(SimpleNamespace(iter=lambda:1, nfun=lambda:1))
        target_evaluator.x[:] = proposed
        target_evaluator.compute_functional_and_gradients()
        pytest.fail('The motion guard must still reject the proposal')
    fake_optimizer.run = run
    report = run_native_masked_trial(objective, max_iterations=2, max_calls=10)
    assert report['status'] == 'FAILED'
    assert report['error'] == 'ValueError: Movable atom displacement exceeds declared bound'
    failed = report['failed_proposal']
    assert failed['status'] == 'OBSERVED' and not failed['objective_returned']
    assert not failed['accepted_by_this_call'] and failed['observation_evaluations'] == 0
    assert failed['source_model_sha256'] == 'a'*64
    assert failed['first_exceeding_displacement'] == dict(source_atom_index=1,
        movable_atom_offset=0, displacement_angstrom=pytest.approx(1.2041594578792296), bound_angstrom=1.)
    assert failed['displacements_sha256'] == sha256(json.dumps(proposed, separators=(',', ':')).encode('ascii')).hexdigest()
    assert not any(k in failed for k in ('points', 'displacements', 'target', 'gradient'))
    assert objective.visited.count(tuple(proposed)) == 1
    assert objective._calls == (44 if accepted else 15)
    assert len(report['trace']) == int(accepted) and len(report['accepted_steps']) == int(accepted)
    assert report['failure_endpoint']['status'] == ('DERIVATIVES_PASS' if accepted else 'NO_ACCEPTED_STEP')
    json.dumps(report, allow_nan=False)


def test_failed_proposal_is_copied_before_a_failing_objective_mutates_optimizer_values(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective = TrialObjective(); original = objective.evaluate
    def evaluate(x):
        if x[0] == 1.2:
            x[:] = [0., 0., 0.]
            raise RuntimeError('objective failed after changing its argument')
        return original(x)
    objective.evaluate = evaluate
    def run(*, target_evaluator, **kw):
        target_evaluator.x[:] = [1.2, 0., 0.]
        target_evaluator.compute_functional_and_gradients()
    fake_optimizer.run = run
    report = run_native_masked_trial(objective, max_iterations=2, max_calls=10)
    assert report['error'] == 'RuntimeError: objective failed after changing its argument'
    assert report['failed_proposal']['first_exceeding_displacement']['displacement_angstrom'] == 1.2
    assert objective._calls == 14 and report['trace'] == []


@pytest.mark.parametrize('proposed', [[float('nan'),0.,0.], [float('inf'),0.,0.], [0.,0.], [1.7e308]*3])
def test_malformed_failed_proposal_cannot_replace_original_error_or_break_json(fake_optimizer, proposed):
    import json
    from nasolve.topostitch_trial import run_native_masked_trial
    objective = TrialObjective(); original = objective.evaluate
    def evaluate(x):
        objective._mask.expand(x)
        return original(x)
    objective.evaluate = evaluate
    def run(*, target_evaluator, **kw):
        target_evaluator.x[:] = proposed
        target_evaluator.compute_functional_and_gradients()
    fake_optimizer.run = run
    report = run_native_masked_trial(objective, max_iterations=2, max_calls=10)
    assert report['status'] == 'FAILED' and report['error'].startswith('ValueError:')
    assert report['failed_proposal']['status'] == 'UNAVAILABLE'
    assert report['failure_endpoint']['status'] == 'NO_ACCEPTED_STEP'
    assert objective._calls == 14 and report['trace'] == []
    json.dumps(report, allow_nan=False)


def test_other_objective_failure_does_not_invent_a_motion_violation(fake_optimizer):
    from nasolve.topostitch_trial import run_native_masked_trial
    objective = TrialObjective(); original = objective.evaluate
    def evaluate(x):
        if x[0] == .4: raise RuntimeError('unrelated objective failure')
        return original(x)
    objective.evaluate = evaluate
    def run(*, target_evaluator, **kw):
        target_evaluator.x[:] = [.4, 0., 0.]
        target_evaluator.compute_functional_and_gradients()
    fake_optimizer.run = run
    report = run_native_masked_trial(objective, max_iterations=2, max_calls=10)
    assert report['error'] == 'RuntimeError: unrelated objective failure'
    assert report['failed_proposal']['status'] == 'OBSERVED'
    assert report['failed_proposal']['first_exceeding_displacement'] is None
    assert not report['failed_proposal']['objective_returned']


def test_failed_proposal_reports_first_mask_order_violation_without_duplicate_coordinates():
    from nasolve.topostitch_trial import _observe_failed_proposal
    mask = CoordinateMask(((0,0,0),(1,1,1),(2,2,2)), (2,0,1), 1.)
    report = _observe_failed_proposal((.5,0,0, 1.1,0,0, 9.,0,0), mask, {})
    assert report['first_exceeding_displacement']['source_atom_index'] == 0
    assert report['first_exceeding_displacement']['movable_atom_offset'] == 1
    assert report['first_exceeding_displacement']['displacement_angstrom'] == 1.1
    assert report['variable_count'] == 9 and 'displacements' not in report
