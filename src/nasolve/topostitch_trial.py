"""Bounded diagnostic native trials; never a model/checkpoint adoption policy."""
from hashlib import sha256
import importlib
import io
import math
from pathlib import Path

STEPS = (1e-4, 1e-5)
ABSOLUTE_BOUND = 1e-3


def check_masked_derivatives(evaluate, displacements):
    """Check every variable at both declared steps and repeat the exact endpoint.

    The tolerance is the predeclared W38 full-native diagnostic bound. Retain
    actual plus/minus targets for review; this is not an adjustable fit criterion.
    """
    values=list(displacements)
    if (not 0<len(values)<=1200 or any(type(v) not in (int,float) or not math.isfinite(v) for v in values)):
        raise ValueError('Require 1-1200 finite explicit displacement variables')
    start=evaluate(values)
    if (not math.isfinite(start['target']) or len(start['gradient'])!=len(values)
            or any(not math.isfinite(v) for v in start['gradient'])):
        raise ValueError('Incomplete finite objective/gradient')
    checks=[];samples=[]
    for step in STEPS:
        maximum=0.;worst=None;rows=[]
        for i in range(len(values)):
            plus=values.copy();minus=values.copy();plus[i]+=step;minus[i]-=step
            p=evaluate(plus)['target'];m=evaluate(minus)['target']
            numeric=(p-m)/(2*step);error=abs(numeric-start['gradient'][i])
            if not all(math.isfinite(v) for v in (p,m,numeric,error)):
                raise ValueError('Nonfinite derivative sample')
            if error>maximum:maximum,worst=error,i
            rows.append(dict(variable=i,plus_target=p,minus_target=m,numeric_gradient=numeric,absolute_error=error))
        checks.append(dict(step_angstrom=step,coordinate_count=len(values),max_absolute_error=maximum,worst_variable=worst))
        samples.append(dict(step_angstrom=step,rows=rows))
    repeat=evaluate(values)
    if start['target']!=repeat['target'] or tuple(start['gradient'])!=tuple(repeat['gradient']):
        raise ValueError('Endpoint objective/gradient changed on repeat')
    return dict(status='DERIVATIVES_PASS' if all(c['max_absolute_error']<=ABSOLUTE_BOUND for c in checks) else 'DERIVATIVE_REVIEW',
        absolute_bound=ABSOLUTE_BOUND,baseline=start,derivatives=checks,samples=samples,
        exact_repeat=True,evaluation_calls=2+4*len(values))



def _observe_failed_last_accepted(objective, result, sources, pinned):
    """Audit an accepted trace point, never a rejected/best/restored trial.

    This nested observation cannot replace the original optimizer failure or
    populate the successful trial's endpoint fields. It uses the existing mask,
    derivative policy and remaining evaluation budget; no candidate is emitted.
    """
    report=dict(status='NO_ACCEPTED_STEP',coordinate_origin='LAST_ACCEPTED_OPTIMIZER_STEP',
        optimizer_failure_preserved=True,scientific_acceptance=False,evaluation_calls=0)
    start_calls=objective._calls
    try:
        if sources()!=pinned:raise ValueError('Native optimizer sources changed')
        if not result['accepted_steps']:return report
        step=result['accepted_steps'][-1]
        saved=result['trace'][step['trace_index']]
        values=saved['displacements']
        report['accepted_step']=dict(step)
        if objective.binding_report()['max_evaluations']-objective._calls<2*(4*len(values)+2):
            report['status']='INSUFFICIENT_BUDGET';return report
        def evaluate(delta):
            value=objective.evaluate(delta)
            if objective._calls==start_calls+1:
                if (any(value[k]!=saved[k] for k in ('target','native_target','pair_target',
                        'unweighted_pair_target','tether_target'))
                        or math.hypot(*value['gradient'])!=saved['gradient_norm']):
                    raise ValueError('Last accepted trace scalar/gradient-norm replay differs')
                report['exact_trace_replay']=True
            return value
        full=check_masked_derivatives(evaluate,values)
        report['full_precision_derivatives']=full
        points=list(full['baseline']['points'])
        for i in objective.binding_report()['movable_indices']:
            points[i]=tuple(float(f'{v:.3f}') for v in points[i])
        rounded=check_masked_derivatives(objective.evaluate,objective._mask.displacements(points))
        report['serialized_derivatives']=rounded
        if sources()!=pinned:raise ValueError('Native optimizer sources changed')
        report['status']='DERIVATIVES_PASS' if full['status']==rounded['status']=='DERIVATIVES_PASS' else 'DERIVATIVE_REVIEW'
    except (ValueError,RuntimeError,OverflowError,OSError) as exc:
        report.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
    finally:
        report['evaluation_calls']=objective._calls-start_calls
    return report


def run_native_masked_trial(objective, *, max_iterations, max_calls, initial_displacements=None):
    """Use the installed scitbx optimizer with hard motion/evaluation bounds.

    Initial, full-precision and rounded endpoint derivatives are required. Errors
    and iteration limits remain explicit; no candidate file is written here.
    An optional explicit diagnostic start uses displacements from the original
    objective source. It does not rebase the mask/tether or adopt a prior trial.
    Callers authenticate any parent point and retain its original outcome; this
    stage independently checks its starting and ending derivatives and bounds.
    """
    if type(max_iterations) is not int or not 1<=max_iterations<=500 or type(max_calls) is not int or not 10<=max_calls<=5000:
        raise ValueError('Require 1-500 iterations and 10-5000 optimizer evaluations')
    from scitbx import lbfgs
    from scitbx.array_family import flex
    binding=objective.binding_report();count=3*len(binding['movable_indices'])
    if initial_displacements is None:
        initial_values=(0.,)*count
    else:
        if not isinstance(initial_displacements,(list,tuple)):
            raise ValueError('Require explicit diagnostic-start displacement numbers')
        initial_values=tuple(initial_displacements)
        objective._mask.expand(initial_values)  # Same source, order and hard bound.
    if 3*(4*count+2)+max_calls>binding['max_evaluations']-objective._calls:
        raise ValueError('Remaining mask evaluation budget cannot cover declared optimizer and three derivative audits')
    def sources():
        return [dict(module=name,sha256=sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest())
                for name in ('scitbx.lbfgs','scitbx_lbfgs_ext')]
    pinned=sources();log=io.StringIO()
    result=dict(schema_version=1,kind='topostitch-bounded-native-trial',status='FAILED',
        max_iterations=max_iterations,max_optimizer_calls=max_calls,optimizer_sources=pinned,
        accepted_steps=[],trace=[],optimization_started=False,refinement=False,automatic_adoption=False,
        scientific_acceptance=False)
    if initial_displacements is not None:
        result['initialization']=dict(coordinate_origin='EXPLICIT_DIAGNOSTIC_START',
            reference='ORIGINAL_OBJECTIVE_SOURCE',displacements=list(initial_values))
    try:
        initial=check_masked_derivatives(objective.evaluate,initial_values)
        result['initial_derivatives']=initial
        if initial['status']!='DERIVATIVES_PASS':
            result['status']='INITIAL_DERIVATIVE_REVIEW';return result
        class Evaluator:
            def __init__(self):self.x=flex.double(initial_values)
            def compute_functional_and_gradients(self):
                if len(result['trace'])>=max_calls:raise ValueError('Optimizer evaluation budget exhausted')
                self.current=objective.evaluate(self.x)
                result['trace'].append(dict(displacements=list(self.x),target=self.current['target'],
                    native_target=self.current['native_target'],pair_target=self.current['pair_target'],
                    unweighted_pair_target=self.current['unweighted_pair_target'],tether_target=self.current['tether_target'],
                    gradient_norm=math.hypot(*self.current['gradient'])))
                return self.current['target'],flex.double(self.current['gradient'])
            def callback_after_step(self,minimizer):
                if not result['trace'] or list(self.x)!=result['trace'][-1]['displacements']:
                    raise ValueError('Optimizer accepted point differs from the last evaluated trace')
                result['accepted_steps'].append(dict(iteration=int(minimizer.iter()),calls=int(minimizer.nfun()),trace_index=len(result['trace'])-1))
                return False
        evaluator=Evaluator();result['optimization_started']=True
        try:
            optimizer=lbfgs.run(target_evaluator=evaluator,
                termination_params=lbfgs.termination_parameters(max_iterations=max_iterations,max_calls=max_calls,
                    traditional_convergence_test=True,traditional_convergence_test_eps=1e-5),
                exception_handling_params=lbfgs.exception_handling_parameters(ignore_line_search_failed_rounding_errors=False),log=log)
        except (ValueError,RuntimeError,OverflowError) as exc:
            result['error']=type(exc).__name__+': '+str(exc)
            result['failure_endpoint']=_observe_failed_last_accepted(objective,result,sources,pinned)
            return result
        full=check_masked_derivatives(objective.evaluate,list(evaluator.x));result['full_precision_derivatives']=full
        points=list(initial['baseline']['points'])
        for i in binding['movable_indices']:
            points[i]=tuple(float(f'{v:.3f}') for v in full['baseline']['points'][i])
        rounded=check_masked_derivatives(objective.evaluate,objective._mask.displacements(points))
        result['serialized_derivatives']=rounded
        stops=[line.split('lbfgs minimizer stop: ',1)[1].strip() for line in log.getvalue().splitlines() if 'lbfgs minimizer stop: ' in line]
        result['stopping']=dict(reason=stops[-1] if stops else 'unreported',error=optimizer.error,
            iterations=int(optimizer.iter()),calls=int(optimizer.nfun()),max_iterations=max_iterations,
            native_criterion_met=bool(lbfgs.traditional_convergence_test(count,1e-5)(evaluator.x,flex.double(full['baseline']['gradient']))))
        result['status']='ENDPOINT_DERIVATIVES_PASS' if full['status']==rounded['status']=='DERIVATIVES_PASS' else 'ENDPOINT_DERIVATIVE_REVIEW'
        if sources()!=pinned:raise ValueError('Native optimizer sources changed')
    except (ValueError,RuntimeError,OverflowError) as exc:
        result.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
    finally:
        result['optimizer_log']=log.getvalue()
        result['objective_evaluation_calls']=objective._calls
    return result


def observe_masked_coordinates(objective, cases, *, capture_pairs, describe_pairs=None, describe_native=None):
    """Observe actual native directed pairs at three explicitly bound coordinates.

    Fresh manager construction/context authentication belongs to the caller.
    Raw native gradients serve capture replay; the masked objective separately
    retains Cedar's corrected gradients. No optimization or derivative audit.
    """
    if list(cases)!=['source','full_precision','rounded']:
        raise ValueError('Require source, full-precision and rounded coordinate cases')
    binding=objective.binding_report()
    if binding['max_evaluations']-objective._calls<9:
        raise ValueError('Mask budget cannot cover three repeated endpoint observations')
    deltas={name:objective._mask.displacements(points) for name,points in cases.items()}
    result=dict(schema_version=1,kind='topostitch-native-coordinate-observations',status='FAILED',
        origin='FIXED_MANAGER_EVALUATION_NOT_REINTERPRETATION',normalization=False,
        coordinate_evaluation='SOURCE_PLUS_BINARY_DISPLACEMENTS',
        optimization=False,derivative_qualification='NOT_RUN',scientific_acceptance=False,
        automatic_adoption=False,cases=[])
    initial_calls=objective._calls
    try:
        for name,points in cases.items():
            evaluation=objective.evaluate(deltas[name])
            row=dict(name=name,points=[list(p) for p in evaluation['points']],evaluation=evaluation)
            result['cases'].append(row)
            if row['points']!=points:raise ValueError('Evaluated points differ from explicit coordinate case')
            repeat=objective.evaluate(deltas[name])
            inventory=capture_pairs([list(p) for p in points])
            row['nonbonded_inventory']=inventory
            final=objective.evaluate(deltas[name])
            for value in (repeat,final):
                if any(evaluation[k]!=value[k] for k in evaluation if k!='evaluation_calls'):
                    raise ValueError('Endpoint objective changed around directed pair capture')
            snapshots=[]
            for raw in inventory['snapshots']:
                if (not math.isclose(raw['target'],evaluation['native_target'],abs_tol=1e-8,rel_tol=1e-10)
                        or raw['proxy_counts']!=evaluation['native_proxy_counts']):
                    raise ValueError('Directed capture and composed native evaluation differ')
                snapshots.append(dict(target=raw['target'],gradient=raw['gradient'],
                    gradient_norm=math.hypot(*raw['gradient']),terms=evaluation['native_components'],
                    proxy_counts=raw['proxy_counts']))
            if len(snapshots)!=2:raise ValueError('Require two actual native snapshots')
            row.update(native_energy_snapshots=snapshots,exact_repeat=True)
            if describe_pairs is not None:
                attribution=describe_pairs(points)
                if not math.isclose(attribution['target'],evaluation['unweighted_pair_target'],rel_tol=1e-10,abs_tol=1e-8):
                    raise ValueError('Individual pair attribution differs from the composed raw pair target')
                row['pair_attribution']=attribution
            if describe_native is not None:
                row['native_terms']=describe_native(points,evaluation['native_components'])
        result['status']='COORDINATE_OBSERVATIONS_REVIEW'
    except (ValueError,RuntimeError,OverflowError,KeyError,TypeError) as exc:
        result['error']=type(exc).__name__+': '+str(exc)
    result['objective_evaluation_calls']=objective._calls-initial_calls
    return result
