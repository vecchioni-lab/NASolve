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


def run_native_masked_trial(objective, *, max_iterations, max_calls):
    """Use the installed scitbx optimizer with hard motion/evaluation bounds.

    Initial, full-precision and rounded endpoint derivatives are required. Errors
    and iteration limits remain explicit; no candidate file is written here.
    """
    if type(max_iterations) is not int or not 1<=max_iterations<=500 or type(max_calls) is not int or not 10<=max_calls<=5000:
        raise ValueError('Require 1-500 iterations and 10-5000 optimizer evaluations')
    from scitbx import lbfgs
    from scitbx.array_family import flex
    binding=objective.binding_report();count=3*len(binding['movable_indices'])
    if 3*(4*count+2)+max_calls>binding['max_evaluations']:
        raise ValueError('Mask evaluation budget cannot cover declared optimizer and three derivative audits')
    def sources():
        return [dict(module=name,sha256=sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest())
                for name in ('scitbx.lbfgs','scitbx_lbfgs_ext')]
    pinned=sources();log=io.StringIO()
    result=dict(schema_version=1,kind='topostitch-bounded-native-trial',status='FAILED',
        max_iterations=max_iterations,max_optimizer_calls=max_calls,optimizer_sources=pinned,
        accepted_steps=[],trace=[],optimization_started=False,refinement=False,automatic_adoption=False,
        scientific_acceptance=False)
    try:
        initial=check_masked_derivatives(objective.evaluate,[0.]*count)
        result['initial_derivatives']=initial
        if initial['status']!='DERIVATIVES_PASS':
            result['status']='INITIAL_DERIVATIVE_REVIEW';return result
        class Evaluator:
            def __init__(self):self.x=flex.double(count,0.)
            def compute_functional_and_gradients(self):
                if len(result['trace'])>=max_calls:raise ValueError('Optimizer evaluation budget exhausted')
                self.current=objective.evaluate(self.x)
                result['trace'].append(dict(displacements=list(self.x),target=self.current['target'],
                    native_target=self.current['native_target'],pair_target=self.current['pair_target'],
                    unweighted_pair_target=self.current['unweighted_pair_target'],tether_target=self.current['tether_target'],
                    gradient_norm=math.hypot(*self.current['gradient'])))
                return self.current['target'],flex.double(self.current['gradient'])
            def callback_after_step(self,minimizer):
                result['accepted_steps'].append(dict(iteration=int(minimizer.iter()),calls=int(minimizer.nfun()),trace_index=len(result['trace'])-1))
                return False
        evaluator=Evaluator();result['optimization_started']=True
        optimizer=lbfgs.run(target_evaluator=evaluator,
            termination_params=lbfgs.termination_parameters(max_iterations=max_iterations,max_calls=max_calls,
                traditional_convergence_test=True,traditional_convergence_test_eps=1e-5),
            exception_handling_params=lbfgs.exception_handling_parameters(ignore_line_search_failed_rounding_errors=False),log=log)
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
