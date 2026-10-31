"""Qualify a saved endpoint with a uniform bounded resolution window.

The C90/C91/C92 findings stay immutable. This separate evidence policy can
select a saved endpoint only after complete derivative coverage, exact identity
serialization and the existing native readback gates. No optimization occurs.
"""
from __future__ import annotations
from collections import deque
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

POLICY_ID='cif-mixed-saved-endpoint-resolution-window-v1'
REPORT='mixed_endpoint_window_qualification.json'
ANCHOR='mixed_endpoint_window_directory'
STEPS=(1.e-7,3.e-8,1.e-8,3.e-9,1.e-9,3.e-10,1.e-10)
FAMILIES=('all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded')
CASES=('initial','full_precision','pdb_rounded')
MAX_EVALUATIONS=2000
MAX_DIRECTIONS=120


def _need(value):
    if not value:raise ValueError('Saved mixed endpoint resolution-window evidence does not reproduce')
def _close(a,b):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _norm(v):return math.sqrt(math.fsum(x*x for x in v))
def _digest(v):return isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)
def _unit(v):
    n=_norm(v);return [x/n for x in v] if n else None
def _bytes(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def _hash(v):return sha256(_bytes(v)).hexdigest()
def _dump(p,v):Path(p).write_bytes(_bytes(v)+b'\n')
def _load(p):
    from .cif_review_transport import _parse_json
    return _parse_json(Path(p).read_bytes())
def _same(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(_same(v,b[k]) for k,v in a.items())
    if isinstance(a,list):return len(a)==len(b) and all(_same(x,y) for x,y in zip(a,b))
    return _close(a,b) if isinstance(a,float) else a==b
def _finite(points):
    _need(isinstance(points,list) and bool(points) and all(isinstance(p,list) and len(p)==3 and all(type(v) in (int,float) and math.isfinite(v) for v in p) for p in points))
def _raw(value,count):
    _need(type(value['target']) in (int,float) and math.isfinite(value['target']))
    g=value['gradient'];_need(isinstance(g,list) and len(g)==3*count and all(type(v) in (int,float) and math.isfinite(v) for v in g))
    return {'target':float(value['target']),'gradient':[float(v) for v in g]}


def refine_direction(evaluate,points,direction,baseline):
    """Keep the original tolerance and demand two adjacent resolved new steps.

    Representation and target-ULP checks describe floating resolution, not a
    rigorous error bound for every operation within a native kernel.
    """
    _finite(points);n=len(points);b=_raw(baseline,n)
    _need(isinstance(direction,list) and len(direction)==3*n and all(type(v) in (int,float) and math.isfinite(v) for v in direction) and _norm(direction)>0)
    analytical=math.fsum(g*v for g,v in zip(b['gradient'],direction));_need(math.isfinite(analytical));flat=[x for p in points for x in p];samples=[]
    for step in STEPS:
        shifted=lambda sign:[[x+sign*step*direction[3*i+j] for j,x in enumerate(p)] for i,p in enumerate(points)]
        plus_points,minus_points=shifted(1),shifted(-1)
        plus=evaluate(deepcopy(plus_points));minus=evaluate(deepcopy(minus_points))
        _need(all(type(v['target']) in (int,float) and math.isfinite(v['target']) for v in [plus,minus]))
        p,m=plus['target'],minus['target'];numerical=(p-m)/(2*step)
        bound=1e-4+1e-4*max(abs(numerical),abs(analytical));error=abs(numerical-analytical)
        pf,mf=[x for q in plus_points for x in q],[x for q in minus_points for x in q]
        effective=[(x-y)/(2*step) for x,y in zip(pf,mf)]
        uncertainty=math.fsum(abs(g)*abs(e-v) for g,e,v in zip(b['gradient'],effective,direction))
        midpoint=[(x+y)/2-z for x,y,z in zip(pf,mf,flat)]
        target_resolution=(math.ulp(float(p))+math.ulp(float(m)))/(2*step)
        _need(all(math.isfinite(v) for v in [numerical,bound,error,uncertainty,target_resolution,*effective,*midpoint]))
        guards={'representable_displacement':pf!=mf and pf!=flat and mf!=flat,
            'representation_uncertainty_resolved':uncertainty<=.1*bound,
            'target_resolution_resolved':target_resolution<=.1*bound,
            'symmetric_midpoint':all(abs(x)<=2*math.ulp(float(z)) for x,z in zip(midpoint,flat))}
        samples.append({'step':step,'plus_points_sha256':_hash(plus_points),'minus_points_sha256':_hash(minus_points),
            'plus_target':p,'minus_target':m,'numerical':numerical,'analytical':analytical,'absolute_error':error,'bound':bound,
            'effective_direction':effective,'representation_derivative_uncertainty':uncertainty,
            'target_ulp_derivative_resolution':target_resolution,'midpoint_drift':midpoint,'guards':guards,
            'consistent':error<=bound and all(guards.values())})
    return {'analytical':analytical,'tolerance':{'absolute':1e-4,'relative':1e-4},'samples':samples,
        'consistent':any(a['consistent'] and b['consistent'] for a,b in zip(samples,samples[1:])),
        'resolution_limit':'FLOATING_RESOLUTION_SCREEN; NOT_A_BOUND_ON_ALL_NATIVE_KERNEL_ERROR'}


def _vectors(case,selected):
    count=len(case['families']['all']['baseline']['gradient'])//3;common=[]
    full=_unit(case['families']['all']['baseline']['gradient'])
    if full is not None:common.append(('full_gradient',full))
    common.append(('alternating_global',_unit([1. if i%2 else -1. for i in range(3*count)])))
    for i in selected:
        for axis in range(3):
            v=[0.]*(3*count);v[3*i+axis]=1.;common.append((f'atom_{i}_axis_{axis}',v))
    return {family:[*common,*([('family_gradient',v)] if (v:=_unit(case['families'][family]['baseline']['gradient'])) is not None else [])] for family in FAMILIES}


def refinement_plan(geometry_result,initial_proof,torsion_result,cases):
    """Recompute old arithmetic and retain all canonical failed direction names."""
    old=geometry_result['endpoint_gradient_audit'];_need(set(old['cases'])=={'full_precision','pdb_rounded'} and old['step_sizes']==[1e-3,1e-4,1e-5,1e-6]
        and old['directional_tolerance']=={'absolute':1e-4,'relative':1e-4} and old['selected_indices']==initial_proof['selected_indices']
        and old['policy_id']=='cif-fixed-native-gradient-audit-v1' and old['analysis_completed'] is True
        and old['model_optimization']=='NOT_RUN' and old['automatic_adoption'] is False
        and type(old['evaluation_calls']) is int and type(old['max_evaluation_calls']) is int and 0<old['evaluation_calls']<=old['max_evaluation_calls']==4000
        and old['evaluation_calls']==sum(2*len(FAMILIES)+1+len(case['descent_profile'])+sum(2*len(d['samples']) for f in case['families'].values() for d in f['directions']) for case in old['cases'].values()))
    plan={'schema_version':1,'policy_id':POLICY_ID,'step_sizes':list(STEPS),'local':[],'families':[],
        'retained_original_passing_directions':0,'original_direction_count':0,'prerequisites':{},'references':{}}
    for label,case in old['cases'].items():
        _need(set(case['families'])==set(FAMILIES));vectors=_vectors(case,old['selected_indices']);n=len(cases[label])
        baselines={family:_raw(row['baseline'],n) for family,row in case['families'].items()}
        field='final' if label=='full_precision' else 'serialized'
        _need(all(_close(geometry_result[field][k],case['families']['all']['baseline'][k]) for k in ['target','gradient_norm']))
        comparisons=case['captured_snapshot_match']['comparisons'];_need(set(comparisons)=={'target','gradient_norm'} and all(v['consistent'] is True
            and _close(v['captured'],geometry_result[field][k]) and _close(v['rebuilt'],case['families']['all']['baseline'][k]) for k,v in comparisons.items()))
        target_sum=math.fsum(baselines[f]['target'] for f in FAMILIES[1:]);g=baselines['all']['gradient']
        summed=[math.fsum(baselines[f]['gradient'][i] for f in FAMILIES[1:]) for i in range(3*n)]
        mismatch=_norm([x-y for x,y in zip(g,summed)])
        _need(_close(target_sum,baselines['all']['target']) and _close(case['target_additivity']['all'],baselines['all']['target'])
            and _close(case['target_additivity']['sum_controls'],target_sum) and case['target_additivity']['consistent'] is True
            and _close(mismatch,case['gradient_additivity']['difference_norm']) and mismatch<=1e-8+1e-10*max(1.,_norm(g))
            and case['gradient_additivity']['consistent'] is True and case['captured_snapshot_match']['consistent'] is True
            and case['baseline_repeats_consistent'] is True)
        for family,row in case['families'].items():
            base=baselines[family];_need(_close(_norm(base['gradient']),row['baseline']['gradient_norm']) and _close(row['repeat_target'],base['target'])
                and _close(row['repeat_gradient_norm'],_norm(base['gradient'])) and row['repeat_consistent'] is True
                and [r['direction'] for r in row['directions']]==[k for k,v in vectors[family]])
            passes=[]
            for d,(name,vector) in zip(row['directions'],vectors[family]):
                analytical=math.fsum(a*b for a,b in zip(base['gradient'],vector));_need(_close(analytical,d['analytical']) and [s['step'] for s in d['samples']]==old['step_sizes']);flags=[]
                for sample in d['samples']:
                    _need(all(type(sample[k]) in (int,float) and math.isfinite(sample[k]) for k in ['plus_target','minus_target','numerical','absolute_error','bound']))
                    numerical=(sample['plus_target']-sample['minus_target'])/(2*sample['step']);error=abs(numerical-analytical);bound=1e-4+1e-4*max(abs(numerical),abs(analytical));okay=error<=bound
                    _need(_close(numerical,sample['numerical']) and _close(error,sample['absolute_error']) and _close(bound,sample['bound']) and sample['consistent'] is okay)
                    flags.append(okay)
                passed=any(a and b for a,b in zip(flags,flags[1:]));_need(d['status']==('CONSISTENT' if passed else 'REVIEW'));passes.append(passed)
                plan['original_direction_count']+=1
                if passed:plan['retained_original_passing_directions']+=1
                else:plan['families'].append({'case':label,'family':family,'direction':name,'vector':vector,'original_direction_sha256':_hash(d)})
            _need(row['sampled_directions_consistent'] is all(passes))
        _need(case['sampled_gradients_consistent'] is all(v['sampled_directions_consistent'] for v in case['families'].values()))
        plan['references'][label]=baselines
    plan['references']['initial']={f:_raw(v['baseline'],len(cases['initial'])) for f,v in initial_proof['gradient_audit']['cases']['initial']['families'].items()}
    audit=torsion_result['audit']
    for label,case in audit['cases'].items():
        for proxy_index,row in enumerate(case['proxies']):
            for order,data in row['orders'].items():
                plan['prerequisites'][f'{label}:{proxy_index}:{order}']=bool(row['reversed_order_consistent'] and data['baseline_repeats_consistent'] and data['single_and_container_agree']
                    and data['baseline'].get('native_angle_defined') is True and data['directions'])
                for d in data['directions']:
                    if all(d['adjacent_step_agreement'].values()):continue
                    name=d['direction'];vector=[0.]*12
                    if name.startswith('atom_'):
                        _,i,_,axis=name.split('_');vector[3*int(i)+int(axis)]=1.
                    elif name=='local_gradient':vector=_unit(data['baseline']['single_gradient'])
                    else:_need(name=='alternating_local');vector=[(1. if i%2 else -1.)/math.sqrt(12) for i in range(12)]
                    plan['local'].append({'case':label,'proxy':row['proxy'],'order':order,'direction':name,'vector':vector,
                        'expected_baseline':data['baseline'],'original_direction_sha256':_hash(d)})
        plan['prerequisites'][label+':group_attribution']=all(case['attribution'].values())
        plan['prerequisites'][label+':group_samples']=case['summary']['group_sampled_agreement'] is True
        plan['prerequisites'][label+':saved_family_match']=case['saved_family_match'] is True
    plan['prerequisites']['full_native_family_coverage']=torsion_result['positive_constant_count']==0
    _need(len(plan['local'])+len(plan['families'])<=MAX_DIRECTIONS)
    return plan


def audit_endpoint_refinement(evaluate,local,cases,plan):
    """Fresh snapshots and boundary samples, retaining every raw native response."""
    _need(set(cases)==set(CASES))
    _need(plan['policy_id']==POLICY_ID and plan['step_sizes']==list(STEPS)
        and len(plan['local'])+len(plan['families'])<=MAX_DIRECTIONS)
    result={'schema_version':1,'policy_id':POLICY_ID,'observations':[],'evaluation_calls':0,'max_evaluation_calls':MAX_EVALUATIONS,
        'step_sizes':list(STEPS),'model_optimization':'NOT_RUN','automatic_adoption':False,'baselines':{},'families':[],'local':[],'checks':deepcopy(plan['prerequisites'])}
    def call(kind,points,selector):
        _need(result['evaluation_calls']<MAX_EVALUATIONS);result['evaluation_calls']+=1;p=deepcopy(points);s=deepcopy(selector)
        value=(evaluate if kind=='family' else local)(p,s);_need(p==points and s==selector)
        result['observations'].append({'request':{'kind':kind,'points_sha256':_hash(points),'selector':deepcopy(selector)},'value':deepcopy(value)});return value
    for label in CASES:
        points=cases[label]
        _finite(points);rows={}
        for family in FAMILIES:
            baseline=_raw(call('family',points,family),len(points));repeat=_raw(call('family',points,family),len(points));reference=plan['references'][label][family]
            rows[family]={'baseline':baseline,'repeat':repeat,'saved_snapshot_match':_same(baseline,reference),'baseline_repeats_consistent':_same(baseline,repeat)}
            result['checks'][label+':'+family+':snapshot']=rows[family]['saved_snapshot_match'] and rows[family]['baseline_repeats_consistent']
        result['baselines'][label]=rows
    for row in plan['families']:
        points=cases[row['case']];baseline=result['baselines'][row['case']][row['family']]['baseline']
        evidence=refine_direction(lambda p:call('family',p,row['family']),points,row['vector'],baseline)
        result['families'].append({'selection':deepcopy(row),'evidence':evidence})
    for row in plan['local']:
        points=[cases[row['case']][i] for i in row['proxy']['i_seqs']]
        if row['order']=='reversed':points=points[::-1]
        selector={'proxy':row['proxy'],'order':row['order']};baseline=call('local',points,selector);repeat=call('local',points,selector)
        expected=row['expected_baseline'];checks={'baseline_repeats_consistent':_same(baseline,repeat),'saved_snapshot_match':_same(baseline,expected),
            'native_angle_defined':baseline.get('native_angle_defined') is True,
            'single_and_container_agree':_close(baseline['single_target'],baseline['accumulated_target']) and _same(baseline['single_gradient'],baseline['accumulated_gradient'])}
        # Each response is shared by the single/container comparisons; neither
        # representation is substituted for the other in the saved evidence.
        cache=deque()
        def target(p,kind):
            if kind=='single':
                value=call('local',p,selector)
                _need(value.get('native_angle_defined') is True and _close(value['single_target'],value['accumulated_target'])
                    and _same(value['single_gradient'],value['accumulated_gradient']))
                cache.append((_hash(p),value))
            else:
                key,value=cache.popleft();_need(key==_hash(p))
            return {'target':value[kind+'_target']}
        single=refine_direction(lambda p:target(p,'single'),points,row['vector'],{'target':baseline['single_target'],'gradient':baseline['single_gradient']})
        accumulated=refine_direction(lambda p:target(p,'accumulated'),points,row['vector'],{'target':baseline['accumulated_target'],'gradient':baseline['accumulated_gradient']})
        _need(not cache)
        result['local'].append({'selection':deepcopy(row),'baseline':baseline,'repeat':repeat,'checks':checks,'single':single,'accumulated':accumulated})
    okay=all(result['checks'].values()) and all(r['evidence']['consistent'] for r in result['families']) and all(all(r['checks'].values()) and r['single']['consistent'] and r['accumulated']['consistent'] for r in result['local'])
    result['summary']={'refined_local_directions':len(result['local']),'refined_family_directions':len(result['families']),
        'retained_original_passing_directions':plan['retained_original_passing_directions'],'original_direction_count':plan['original_direction_count'],
        'sampled_derivatives_pass':okay,'evaluation_calls':result['evaluation_calls'],'endpoint_native_readback':'NOT_RUN'}
    result['status']='ADAPTIVE_ENDPOINT_DERIVATIVES_PASS' if okay else 'REVIEW';return result


def replay_endpoint_refinement(result,cases,plan):
    # Step sizes and tolerances are semantic recipe fields, not quantities to
    # compare with the numerical-value roundoff tolerance used below.
    _need(result['step_sizes']==list(STEPS))
    for row in result['families']:
        _need([s['step'] for s in row['evidence']['samples']]==list(STEPS)
            and row['evidence']['tolerance']=={'absolute':1e-4,'relative':1e-4})
    for row in result['local']:
        for kind in ['single','accumulated']:
            _need([s['step'] for s in row[kind]['samples']]==list(STEPS)
                and row[kind]['tolerance']=={'absolute':1e-4,'relative':1e-4})
    stream=deque(deepcopy(result['observations']))
    def callback(kind):
        def evaluate(points,selector):
            _need(bool(stream));row=stream.popleft();_need(row['request']=={'kind':kind,'points_sha256':_hash(points),'selector':selector});return deepcopy(row['value'])
        return evaluate
    rebuilt=audit_endpoint_refinement(callback('family'),callback('local'),cases,plan)
    _need(not stream and _same(rebuilt,result));return {'status':rebuilt['status'],'summary':rebuilt['summary']}


_WORKER=r'''from pathlib import Path
import hashlib,importlib,json,sys,traceback
from endpoint_core import POLICY_ID,audit_endpoint_refinement,_dump,_same,_need
from mixed_torsion_core import _manager_digest,_proxy
from conditioning_core import native_evaluator
from correction_core import evaluate_fixed_native
from gradient_core import fixed_signature
spec=json.loads(Path('endpoint_spec.json').read_bytes())
result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','model_optimization':'NOT_RUN','automatic_adoption':False}
try:
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Fresh endpoint native bootstrap failed')
    native=namespace['report'];expected=json.loads(Path('expected_inventory.json').read_bytes());_dump(Path('native_validation.json'),native)
    _need(_manager_digest(native)==spec['expected_manager_sha256']==_manager_digest(expected) and _same(native['energy_inventory'],expected['energy_inventory']))
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    geo,sites=namespace['geo'],namespace['sites'];original=[list(p) for p in sites]
    _need(not geo.site_symmetry_table.special_position_indices())
    def fingerprints():
        out=[]
        for row in spec['expected_sources']:
            module=importlib.import_module(row['module']);path=Path(module.__file__).resolve();out.append({'module':module.__name__,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        return out
    sources=fingerprints();_need(sources==spec['expected_sources'])
    signature=fixed_signature(geo,sites);_need(signature==spec['expected_constraint_signature'])
    selected_parameters=[]
    for row in json.loads(Path('torsion_spec.json').read_bytes())['selection']['selected']:
        p=list(geo.dihedral_proxies or [])[row['native_index']]
        values={k:list(p.i_seqs) if k=='i_seqs' else getattr(p,k,None) for k in ['i_seqs','angle_ideal','weight','periodicity','alt_angle_ideals','origin_id']}
        if values['alt_angle_ideals'] is not None:values['alt_angle_ideals']=list(values['alt_angle_ideals'])
        _need(_proxy(values,len(sites))==row['proxy'] and (p.sym_ops is None or not len(p.sym_ops)) and p.limit==-1 and p.top_out is False and p.slack==0)
        selected_parameters.append({**row['proxy'],'limit':float(p.limit),'slack':float(p.slack),'top_out':bool(p.top_out),'symmetry':'NONE'})
    def family(points,name):
        active=flags.flags(default=name=='all')
        if name!='all':setattr(active,name,True)
        raw=evaluate_fixed_native(geo,points,active,gr,flex,plane_order_safe=True)
        _need(raw['target']==raw['native_target'])
        return {'target':raw['target'],'gradient':raw['gradient']}
    evaluator=native_evaluator(gr,flex)
    def local(points,selector):
        raw=evaluator(points,selector['proxy']);return {**raw,'status':'FINITE'}
    audit=audit_endpoint_refinement(family,local,spec['coordinate_cases'],spec['plan'])
    after=fixed_signature(geo,sites);_need(after==signature and [list(p) for p in sites]==original and fingerprints()==sources)
    result.update(status='REVIEW',analysis_completed=True,audit=audit,captured_inventory_matches=True,manager_sha256=_manager_digest(native),
        constraint_signature_before=signature,constraint_signature_after=after,initial_coordinates_unchanged=True,
        installed_sources=sources,installed_sources_after=fingerprints(),selected_native_parameters=selected_parameters,
        restraint_changes='NONE',scientific_qualification='NOT_ASSESSED')
except Exception as exc:
    result.update(error=type(exc).__name__+': '+str(exc));traceback.print_exc()
_dump(Path('endpoint_result.json'),result)
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def _ref(path,root,anchor=ANCHOR):
    from .cif_mixed_geometry import _ref as reference
    return reference(path,root,anchor)
def _resolve(root,torsion,geometry,gradient,context,parent,ref):
    from .cif_mixed_recovery import _safe
    anchors={ANCHOR:Path(root),'torsion_directory':Path(torsion),'geometry_directory':Path(geometry),'gradient_directory':Path(gradient),'context_directory':Path(context),'linked_parent_directory':Path(parent)}
    _need(isinstance(ref,dict) and ref.get('anchor') in anchors and _safe(ref.get('path')))
    directory=anchors[ref['anchor']];p=directory/ref['path'];_need(_ref(p,directory,ref['anchor'])==ref);return p


def _inputs(torsion,geometry,gradient,context,parent,parent_archive_sha256):
    from .cif_mixed_torsion import read_mixed_torsions,_inputs as old_inputs,REPORT as OLD_REPORT
    from .cif_mixed_geometry import _completed_result
    _need(_digest(parent_archive_sha256));record=_load(torsion/OLD_REPORT)
    source=read_mixed_torsions(torsion,geometry_directory=geometry,gradient_directory=gradient,context_directory=context,
        linked_parent_directory=parent,parent_archive_sha256=record['parent_archive_sha256'])
    _need(source['status']=='MIXED_TORSION_AUDIT_COMPLETE' and source['execution']['status']=='COMPLETED')
    old,model,cifs,phils,expected,proof,cases,references,selection,bindings=old_inputs(geometry,gradient,context,parent,record['parent_archive_sha256'])
    result=_completed_result(geometry,expected)
    from .cif_mixed_geometry import POLICY_ID as GEOMETRY_POLICY
    _need(result['policy_id']==GEOMETRY_POLICY and result['status']=='REVIEW' and result['captured_inventory_matches'] is True
        and result['qualified_initial_snapshot_matches'] is True and result['policy_inventory'] is True and result['normalization'] is False
        and result['automatic_adoption'] is False and result['starting_coordinates']=='CAPTURED_INITIAL' and result['special_position_count']==0
        and result['constraint_signature_before']==result['constraint_signature_after']==proof['constraint_signature_before']
        and result['correction_policy_id']==proof['correction_policy_id'] and result['derivative_precondition']=='SAMPLED_NATIVE_DERIVATIVES_PASS')
    for new,key in [('installed_optimizer_sources','installed_numeric_sources'),('installed_adapter_sources','installed_adapter_sources'),('installed_parallelity_sources','installed_parallelity_sources')]:_need(result[new]==proof[key])
    for k in ['target','gradient_norm']:_need(_close(result['initial'][k],proof['gradient_audit']['cases']['initial']['families']['all']['baseline'][k]))
    iterations=old['max_iterations'];_need(result['termination_parameters']=={'max_iterations':iterations,'max_calls':iterations*20,'traditional_convergence_test':True,'traditional_convergence_test_eps':1e-5}
        and result['derivative_validation_archive']==old['parent_archive_sha256'])
    stop=result['stopping'];_need(all(type(stop[k]) is int and stop[k]>=0 for k in ['iterations','calls','max_iterations']) and stop['max_iterations']==iterations
        and isinstance(stop['reason'],str) and type(stop['native_criterion_met']) is bool and (stop['error'] is None or isinstance(stop['error'],str)))
    raw=_load(torsion/'job/torsion_result.json');plan=refinement_plan(result,proof,raw,cases)
    bindings={**bindings,'torsion_report':_ref(torsion/OLD_REPORT,torsion,'torsion_directory'),
        'torsion_result':_ref(torsion/'job/torsion_result.json',torsion,'torsion_directory')}
    return source,model,cifs,phils,expected,proof,cases,references,selection,result,plan,bindings


def _prepare(root,model,cifs,phils,expected,proof,cases,references,selection,plan):
    from .cif_mixed_torsion import _prepare as old_prepare,_manager_digest
    prep=old_prepare(root,model,cifs,phils,expected,proof,cases,references,selection)
    spec={'schema_version':1,'policy_id':POLICY_ID,'coordinate_cases':cases,'plan':plan,
        'expected_manager_sha256':_manager_digest(expected),'expected_constraint_signature':proof['constraint_signature_before'],
        'expected_sources':[{k:r[k] for k in ['module','sha256']} for r in proof['installed_numeric_sources']+proof['installed_adapter_sources']]}
    _dump(root/'refinement_plan.json',plan);_dump(root/'job/endpoint_spec.json',spec)
    (root/'job/endpoint_worker.py').write_text(_WORKER);(root/'job/endpoint_core.py').write_bytes(Path(__file__).read_bytes())
    return {'native_preparation':prep,'plan':_ref(root/'refinement_plan.json',root),'spec':_ref(root/'job/endpoint_spec.json',root),
        'worker':_ref(root/'job/endpoint_worker.py',root),'core':_ref(root/'job/endpoint_core.py',root)}


def _validate_result(root,result,expected,proof,cases,plan):
    from .cif_mixed_torsion import _manager_digest
    r=result;_need(type(r['schema_version']) is int and r['schema_version']==1 and r['policy_id']==POLICY_ID and r['status']=='REVIEW'
        and r['analysis_completed'] is True and r['captured_inventory_matches'] is True and r['manager_sha256']==_manager_digest(expected)
        and r['constraint_signature_before']==r['constraint_signature_after']==proof['constraint_signature_before']
        and r['initial_coordinates_unchanged'] is True and r['model_optimization']=='NOT_RUN' and r['restraint_changes']=='NONE'
        and r['automatic_adoption'] is False and r['scientific_qualification']=='NOT_ASSESSED')
    native=_load(root/'job/native_validation.json');_need(_manager_digest(native)==_manager_digest(expected) and _same(native['energy_inventory'],expected['energy_inventory']))
    pins=[{k:r[k] for k in ['module','sha256']} for r in proof['installed_numeric_sources']+proof['installed_adapter_sources']]
    _need(r['installed_sources']==r['installed_sources_after']==pins)
    selection=_load(root/'job/torsion_spec.json')['selection']['selected']
    _need(r['selected_native_parameters']==[{**row['proxy'],'limit':-1.,'slack':0.,'top_out':False,'symmetry':'NONE'} for row in selection])
    return replay_endpoint_refinement(r['audit'],cases,plan)


def _analysis(root,parents,report,expected,proof,cases,plan,geometry_result,model,cifs,phils):
    from .cif_mixed_geometry import _decision
    from .cif_fixed_geometry import write_geometry_candidate,review_fixed_coordinates,qualify_fixed_policy_geometry
    from .cif_captured_geometry import review_captured_geometry
    from .cif_mixed_linked_recovery import _capture
    q={'status':'NOT_RUN'};checks={};summary=None;capture=None;count=int('returncode' in report['execution'])
    if 'receipt' in report['native_readback']:
        ref=report['native_readback']['receipt'];_resolve(root,*parents,ref)
        capture=_capture(root,{**ref,'anchor':'mixed_linked_recovery_directory'},root/'candidate/saved_mixed_endpoint.pdb',cifs,phils)
        count+=int('returncode' in capture.get('execution',{}));_need(capture['phenix_version']==report['phenix_version'] and capture['executable_sha256']==report['executable_sha256']
            and capture['execution']['timeout_seconds']==min(report['timeout_seconds'],60))
    _need(report['new_native_calls']==count and count<=2)
    if report['execution']['status']=='COMPLETED':
        try:q=_validate_result(root,_load(root/'job/endpoint_result.json'),expected,proof,cases,plan)
        except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError,ZeroDivisionError) as exc:q={'status':'REVIEW','finding_type':type(exc).__name__,'finding':'ADAPTIVE_EVIDENCE_INCOMPLETE'}
        checks['qualified_endpoint_derivatives']=q['status']=='ADAPTIVE_ENDPOINT_DERIVATIVES_PASS'
        if checks['qualified_endpoint_derivatives']:
            summary=deepcopy(q['summary']);candidate=root/'candidate/saved_mixed_endpoint.pdb'
            try:
                with tempfile.TemporaryDirectory(prefix='mixed-endpoint-serialization-') as temporary:
                    p=Path(temporary).resolve()/'model.pdb';serialization=write_geometry_candidate(model,p,expected,cases['full_precision'])
                    _need(p.read_bytes()==candidate.read_bytes() and _load(root/'serialization.json')==serialization)
                _need(_load(root/'full_precision_geometry.json')==review_fixed_coordinates(expected,cases['full_precision']));checks['exact_identity_serialization']=True
            except (OSError,ValueError,KeyError,TypeError,IndexError):checks['exact_identity_serialization']=False
            checks['fixed_native_mechanics']=False;checks['fresh_rounded_target']=False
            if capture is not None and capture.get('status')=='REVIEW' and capture['execution'].get('status')=='COMPLETED' and capture['execution'].get('returncode')==0:
                try:
                    after=capture['native_validation'];mechanics=qualify_fixed_policy_geometry(expected,after,candidate,_load(root/'serialization.json'))
                    _need(_load(root/'native_mechanics.json')==mechanics and _load(root/'rounded_geometry.json')==review_captured_geometry(after))
                    checks['fixed_native_mechanics']=mechanics['mechanics_checks_pass'] is True
                    checks['fresh_rounded_target']=_close(after['energy_inventory']['snapshots'][0]['target'],geometry_result['serialized']['target'])
                except (OSError,ValueError,KeyError,TypeError,IndexError):pass
            checks['nonworse_fixed_objective']=all(geometry_result[f]['target']<=geometry_result['initial']['target']+1e-8+1e-10*abs(geometry_result['initial']['target']) for f in ['final','serialized'])
            summary['endpoint_native_readback']='PASS' if checks['fixed_native_mechanics'] and checks['fresh_rounded_target'] else 'REVIEW'
        elif capture is not None:_need(False)
    elif capture is not None:_need(False)
    return q,_decision(checks,deepcopy(geometry_result['stopping'])),summary


def _publish(root,parents,report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['outputs']=[_ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT and p.suffix not in {'.pkl','.pickle','.pyc'}]
    _dump(root/REPORT,report);read_saved_mixed_endpoint(root,torsion_directory=parents[0],geometry_directory=parents[1],gradient_directory=parents[2],
        context_directory=parents[3],linked_parent_directory=parents[4],parent_archive_sha256=report['parent_archive_sha256']);return report


def qualify_saved_mixed_endpoint(torsion_directory,geometry_directory,gradient_directory,context_directory,linked_parent_directory,phenix,output,*,parent_archive_sha256,timeout_seconds=120):
    from .cif_native_validation import _stop,inspect_native_bundle
    from .cif_fixed_geometry import write_geometry_candidate,review_fixed_coordinates,qualify_fixed_policy_geometry
    from .cif_captured_geometry import review_captured_geometry
    _need(type(timeout_seconds) is int and 1<=timeout_seconds<=600 and _digest(parent_archive_sha256))
    parents=tuple(map(Path,(torsion_directory,geometry_directory,gradient_directory,context_directory,linked_parent_directory)));root=Path(output).absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root,*root.parents]) and not any(root.resolve().is_relative_to(p.resolve()) for p in parents))
    source,model,cifs,phils,expected,proof,cases,references,selection,result,plan,bindings=_inputs(*parents,parent_archive_sha256);root.mkdir(parents=True)
    prep=_prepare(root,model,cifs,phils,expected,proof,cases,references,selection,plan)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':prep,'parent_archive_sha256':parent_archive_sha256,
        'parent_archive_verification':'CALLER_VERIFIED_EXACT_C91_CAPSULE_BYTES; SCIENCE_BOUND_BY_MAINTAINED_PARENT_READERS',
        'maximum_native_calls':2,'new_native_calls':0,'timeout_seconds':timeout_seconds,'maximum_evaluation_calls':MAX_EVALUATIONS,'maximum_refined_directions':MAX_DIRECTIONS,
        'execution':{'status':'NOT_RUN'},'native_readback':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},
        'coordinate_decision':deepcopy(source['coordinate_decision']),'original_coordinate_decision':deepcopy(source['coordinate_decision']),
        'original_geometry_qualification':deepcopy(source['original_geometry_qualification']),
        'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','readyset_execution':'NOT_RUN','coot_execution':'NOT_RUN','refinement':'NOT_RUN',
        'cache_writes':'NOT_RUN','captured_code_execution':'NOT_RUN','scientific_qualification':'NOT_ASSESSED','automatic_adoption':False,'requires_cif_review':False,
        'policy_authority':'NARestraints','source_chemical_findings':'PRESERVED_IN_BOUND_CONTEXT; NOT_PROMOTED_BY_ENDPOINT_QUALIFICATION'}
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True);fingerprint=sha256(executable.read_bytes()).hexdigest()
        report.update(status='REVIEW',phenix_version=phenix.version,executable_provenance=str(executable),executable_sha256=fingerprint);started=time.monotonic()
        try:
            with (root/'job/endpoint.log').open('xb') as log:
                process=subprocess.Popen([str(executable),'-B','endpoint_worker.py'],cwd=root/'job',env=dict(phenix.environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                report['new_native_calls']=1
                try:code=process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:_stop(process);report['execution']={'status':'TIMED_OUT','returncode':process.returncode}
                except BaseException as exc:_stop(process);report['execution']={'status':'WAIT_FAILED','returncode':process.returncode,'error_type':type(exc).__name__};raise
                else:report['execution']={'status':'COMPLETED' if code==0 else 'FAILED','returncode':code}
            if report['execution']['status']=='COMPLETED':
                q=_validate_result(root,_load(root/'job/endpoint_result.json'),expected,proof,cases,plan)
                if q['status']=='ADAPTIVE_ENDPOINT_DERIVATIVES_PASS':
                    candidate=root/'candidate/saved_mixed_endpoint.pdb';candidate.parent.mkdir()
                    serialization=write_geometry_candidate(model,candidate,expected,cases['full_precision']);_dump(root/'serialization.json',serialization)
                    _dump(root/'full_precision_geometry.json',review_fixed_coordinates(expected,cases['full_precision']))
                    capture=inspect_native_bundle(candidate,cifs,root/'native_readback',executable,environment=phenix.environment,phenix_version=phenix.version,
                        timeout_seconds=min(timeout_seconds,60),phil_files=phils,phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',policy_inventory=True,energy_inventory=True)
                    report['new_native_calls']+=int('returncode' in capture.get('execution',{}));report['native_readback']={'receipt':_ref(Path(capture['native_directory'])/'native_receipt.json',root)}
                    if capture.get('status')=='REVIEW' and capture['execution'].get('returncode')==0:
                        after=capture['native_validation'];_dump(root/'native_mechanics.json',qualify_fixed_policy_geometry(expected,after,candidate,serialization));_dump(root/'rounded_geometry.json',review_captured_geometry(after))
        except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError,ZeroDivisionError) as exc:
            report['optional_finding']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['optional_finding']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6);_need(sha256(executable.read_bytes()).hexdigest()==fingerprint)
        q,decision,summary=_analysis(root,parents,report,expected,proof,cases,plan,result,model,cifs,phils)
        report['qualification']=q;report['coordinate_decision']=decision
        if summary is not None:report['summary']=summary
        if decision['endpoint_usable']:report['status']='MIXED_ENDPOINT_QUALIFIED'
    return _publish(root,parents,report)


def _read_saved_mixed_endpoint(directory,*,torsion_directory,geometry_directory,gradient_directory,context_directory,linked_parent_directory,parent_archive_sha256):
    root=Path(directory);parents=tuple(map(Path,(torsion_directory,geometry_directory,gradient_directory,context_directory,linked_parent_directory)));report=_load(root/REPORT)
    _need(not any(p.is_symlink() for p in [root,*root.parents]))
    _need(_digest(parent_archive_sha256) and report['parent_archive_sha256']==parent_archive_sha256 and type(report['schema_version']) is int and report['schema_version']==1
        and report['policy_id']==POLICY_ID and report['status'] in {'PREPARED_ONLY','REVIEW','MIXED_ENDPOINT_QUALIFIED'}
        and type(report['maximum_native_calls']) is int and report['maximum_native_calls']==2 and type(report['new_native_calls']) is int and 0<=report['new_native_calls']<=2
        and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600 and report['maximum_evaluation_calls']==MAX_EVALUATIONS and report['maximum_refined_directions']==MAX_DIRECTIONS
        and report['parent_archive_verification']=='CALLER_VERIFIED_EXACT_C91_CAPSULE_BYTES; SCIENCE_BOUND_BY_MAINTAINED_PARENT_READERS'
        and report['scientific_qualification']=='NOT_ASSESSED' and report['automatic_adoption'] is False and report['requires_cif_review'] is False and report['policy_authority']=='NARestraints'
        and report['source_chemical_findings']=='PRESERVED_IN_BOUND_CONTEXT; NOT_PROMOTED_BY_ENDPOINT_QUALIFICATION'
        and all(report[k]=='NOT_RUN' for k in ['model_optimization','dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution']))
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,*parents,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT and p.suffix not in {'.pkl','.pickle','.pyc'}:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    source,model,cifs,phils,expected,proof,cases,references,selection,result,plan,bindings=_inputs(*parents,parent_archive_sha256)
    _need(report['inputs']==bindings and report['original_coordinate_decision']==source['coordinate_decision'] and report['original_geometry_qualification']==source['original_geometry_qualification'])
    with tempfile.TemporaryDirectory(prefix='mixed-endpoint-reader-') as temporary:
        replay=Path(temporary).resolve();prep=_prepare(replay,model,cifs,phils,expected,proof,cases,references,selection,plan);_need(prep==report['preparation'])
        for p in replay.rglob('*'):
            if p.is_file():_need((root/p.relative_to(replay)).read_bytes()==p.read_bytes())
    execution=report['execution'];state=execution['status']
    if report['new_native_calls']==0:
        _need((report['status']=='PREPARED_ONLY' and execution=={'status':'NOT_RUN'}) or (report['status']=='REVIEW' and state=='LAUNCH_FAILED' and isinstance(execution['error'],str)))
    else:
        _need(report['status']!='PREPARED_ONLY' and state in {'COMPLETED','FAILED','TIMED_OUT','WAIT_FAILED'} and type(execution['returncode']) is int
            and (state!='COMPLETED' or execution['returncode']==0) and (state!='FAILED' or execution['returncode']!=0)
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0
            and _digest(report['executable_sha256']) and isinstance(report['phenix_version'],str) and bool(report['phenix_version']))
    if report['status']=='PREPARED_ONLY':_need(report['qualification']=={'status':'NOT_RUN'} and report['native_readback']=={'status':'NOT_RUN'} and report['coordinate_decision']==source['coordinate_decision'])
    else:
        q,decision,summary=_analysis(root,parents,report,expected,proof,cases,plan,result,model,cifs,phils)
        _need(report['qualification']==q and report['coordinate_decision']==decision and report.get('summary')==summary and (report['status']=='MIXED_ENDPOINT_QUALIFIED') is decision['endpoint_usable'])
    return report


def read_saved_mixed_endpoint(directory,*,torsion_directory,geometry_directory,gradient_directory,context_directory,linked_parent_directory,parent_archive_sha256):
    """Recompute the new qualification without native discovery or execution."""
    try:return _read_saved_mixed_endpoint(directory,torsion_directory=torsion_directory,geometry_directory=geometry_directory,
        gradient_directory=gradient_directory,context_directory=context_directory,linked_parent_directory=linked_parent_directory,parent_archive_sha256=parent_archive_sha256)
    except (KeyError,TypeError,IndexError,OverflowError,ZeroDivisionError) as exc:raise ValueError('Incomplete saved mixed endpoint resolution-window report') from exc
