"""Bounded original/candidate numerical comparisons at unchanged coordinates.

The candidate is already separately prepared and inventory-qualified. This
module evaluates it without optimization, model output or automatic adoption.
"""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

POLICY_ID='cif-fixed-linear-torsion-numerical-impact-v1'
FAMILIES=('all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded')
STEPS=(1e-3,1e-4,1e-5,1e-6,1e-7,1e-8)


def _norm(v):return math.sqrt(math.fsum(x*x for x in v))
def _close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _vector_close(a,b):return len(a)==len(b) and _norm([x-y for x,y in zip(a,b)])<=1e-8+1e-10*max(1.,_norm(a),_norm(b))


def removed_torsion_references(conditioning,proxies,atom_count):
    """Scatter the saved single-proxy derivatives using exact native indices."""
    result={}
    for label,case in conditioning['cases'].items():
        rows=case['proxies']
        if len(rows)!=len(proxies):raise ValueError('Removed-proxy reference count differs')
        gradient=[0.]*(3*atom_count);targets=[]
        for row,p in zip(rows,proxies):
            b=row['baseline'];ids=p['i_seqs']
            if row['proxy']!=p or len(ids)!=4 or len(set(ids))!=4 or any(type(i) is not int or not 0<=i<atom_count for i in ids):
                raise ValueError('Removed-proxy reference identity differs')
            if len(b['single_gradient'])!=12 or any(not math.isfinite(x) for x in [b['single_target'],*b['single_gradient']]):
                raise ValueError('Invalid removed-proxy reference')
            targets.append(b['single_target'])
            for j,i in enumerate(ids):
                for axis in range(3):gradient[3*i+axis]+=b['single_gradient'][3*j+axis]
        result[label]={'target':math.fsum(targets),'gradient':gradient}
    return result


def _validate(coordinate_cases,selected_indices,removed_references,max_calls):
    if not 1<=len(coordinate_cases)<=3 or set(coordinate_cases)!=set(removed_references):raise ValueError('Require matching bounded coordinate/reference cases')
    count=len(next(iter(coordinate_cases.values())))
    if not count or not 1<=len(selected_indices)<=6 or len(set(selected_indices))!=len(selected_indices) or any(type(i) is not int or not 0<=i<count for i in selected_indices):raise ValueError('Invalid coordinate probes')
    if type(max_calls) is not int or not 1<=max_calls<=2000:raise ValueError('Invalid evaluation budget')
    for label,points in coordinate_cases.items():
        r=removed_references[label]
        if (len(points)!=count or any(len(p)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in p) for p in points)
                or len(r['gradient'])!=3*count or any(type(x) not in (int,float) or not math.isfinite(x) for x in [r['target'],*r['gradient']])):
            raise ValueError('Require complete finite coordinates and removed references')
    return count


def audit_linear_torsion_impact(evaluate,coordinate_cases,selected_indices,removed_references,*,max_calls=2000):
    """Check exact numerical deltas and sample the candidate derivatives.

    The callback receives manager name, temporary coordinates and diagnostic
    family flags. Raw values, every finite-difference step and failed checks
    remain visible. A smaller gradient norm is descriptive, never required.
    """
    count=_validate(coordinate_cases,selected_indices,removed_references,max_calls)
    result={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','analysis_completed':False,'numerical_checks_pass':False,
        'model_optimization':'NOT_RUN','model_editing':'NOT_RUN','coordinate_model_written':False,'scientific_approval':'NOT_RUN','automatic_adoption':False,
        'evaluation_calls':0,'max_evaluation_calls':max_calls,'selected_indices':list(selected_indices),'step_sizes_angstrom':list(STEPS),
        'directional_tolerance':{'absolute':1e-4,'relative':1e-4},'repeat_delta_tolerance':{'absolute':1e-8,'relative':1e-10},'cases':{},
        'limitations':['Fixed-coordinate diagnostic only; no chemical-state selection, geometry qualification or adoption.',
            'Sampled derivatives do not prove all derivatives or convergence. Gradient norms can increase when cancelling contributions are removed.',
            'Family flags isolate numerical contributions; they are not changed production policies.']}
    def call(manager,points,family):
        if result['evaluation_calls']>=max_calls:raise ValueError('Native evaluation budget exhausted')
        result['evaluation_calls']+=1;p=deepcopy(points);raw=evaluate(manager,p,family)
        if p!=points:raise ValueError('Evaluation callback mutated coordinates')
        target=raw['target'];gradient=raw['gradient']
        if (type(target) not in (int,float) or not math.isfinite(target) or len(gradient)!=3*count
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in gradient)):
            raise ValueError('Require finite native target and complete gradient')
        return {**deepcopy(raw),'gradient_norm':_norm(gradient)}
    def equal(a,b):return _close(a['target'],b['target']) and _vector_close(a['gradient'],b['gradient']) and a.get('proxy_counts')==b.get('proxy_counts')
    for label,points in coordinate_cases.items():
        baselines={m:{f:call(m,points,f) for f in FAMILIES} for m in ['original','candidate']}
        repeats={m:{f:call(m,points,f) for f in FAMILIES} for m in baselines};checks={}
        checks['baseline_repeats_consistent']=all(equal(baselines[m][f],repeats[m][f]) for m in baselines for f in FAMILIES)
        changes={}
        for family in FAMILIES:
            a,b=baselines['original'][family],baselines['candidate'][family]
            delta={'target':a['target']-b['target'],'gradient':[x-y for x,y in zip(a['gradient'],b['gradient'])]};delta['gradient_norm']=_norm(delta['gradient']);changes[family]=delta
            if family not in {'all','dihedral'}:checks[family+'_unchanged']=_close(a['target'],b['target']) and _vector_close(a['gradient'],b['gradient'])
        ref=removed_references[label]
        for family in ['all','dihedral']:
            d=changes[family];checks[('full' if family=='all' else family)+'_delta_matches_removed']=_close(d['target'],ref['target']) and _vector_close(d['gradient'],ref['gradient'])
        for manager,base in baselines.items():
            target=math.fsum(base[f]['target'] for f in FAMILIES[1:]);gradient=[math.fsum(base[f]['gradient'][i] for f in FAMILIES[1:]) for i in range(3*count)]
            checks[manager+'_target_additivity']=_close(target,base['all']['target']);checks[manager+'_gradient_additivity']=_vector_close(gradient,base['all']['gradient'])
        candidate=baselines['candidate'];direction_rows={}
        common=[('alternating_global',[(-1. if i%2==0 else 1.)/math.sqrt(3*count) for i in range(3*count)])]
        if candidate['all']['gradient_norm']:common.append(('full_gradient',[v/candidate['all']['gradient_norm'] for v in candidate['all']['gradient']]))
        for i in selected_indices:
            for axis in range(3):common.append((f'atom_{i}_axis_{axis}',[float(j==3*i+axis) for j in range(3*count)]))
        for family in ['all','dihedral']:
            baseline=candidate[family];directions=list(common);rows=[]
            if family=='dihedral' and baseline['gradient_norm']:directions.append(('family_gradient',[v/baseline['gradient_norm'] for v in baseline['gradient']]))
            for name,vector in directions:
                analytic=math.fsum(v*g for v,g in zip(vector,baseline['gradient']));samples=[]
                for h in STEPS:
                    shifted=lambda sign:[[v+sign*h*vector[3*i+j] for j,v in enumerate(p)] for i,p in enumerate(points)]
                    plus,minus=call('candidate',shifted(1),family),call('candidate',shifted(-1),family)
                    numerical=(plus['target']-minus['target'])/(2*h);error=abs(numerical-analytic);bound=1e-4+1e-4*max(abs(numerical),abs(analytic))
                    counts=plus.get('proxy_counts')==minus.get('proxy_counts')==baseline.get('proxy_counts')
                    samples.append({'step_angstrom':h,'plus_target':plus['target'],'minus_target':minus['target'],'numerical':numerical,
                        'absolute_error':error,'bound':bound,'proxy_counts_consistent':counts,'consistent':error<=bound and counts,
                        'plus_proxy_counts':plus.get('proxy_counts',{}),'minus_proxy_counts':minus.get('proxy_counts',{})})
                passed=any(a['consistent'] and b['consistent'] for a,b in zip(samples,samples[1:]))
                rows.append({'direction':name,'analytical':analytic,'samples':samples,'sampled_derivative_consistent':passed})
            direction_rows[family]=rows;checks['candidate_'+family+'_sampled_derivatives']=all(r['sampled_derivative_consistent'] for r in rows)
        final={m:{f:call(m,points,f) for f in FAMILIES} for m in baselines}
        checks['final_repeats_consistent']=all(equal(baselines[m][f],final[m][f]) for m in baselines for f in FAMILIES)
        result['cases'][label]={'baselines':baselines,'repeats':repeats,'final_repeats':final,'original_minus_candidate':changes,
            'saved_removed_reference':deepcopy(ref),'candidate_derivatives':direction_rows,'checks':checks,'numerical_checks_pass':all(checks.values()),
            'full_gradient_norm_change':candidate['all']['gradient_norm']-baselines['original']['all']['gradient_norm']}
    result['analysis_completed']=True;result['numerical_checks_pass']=all(c['numerical_checks_pass'] for c in result['cases'].values())
    return result


def replay_impact_evidence(saved,cases,indices,references):
    """Replay the raw saved call sequence, preserving failing count checks."""
    events=[];count=len(next(iter(cases.values())))
    for label,points in cases.items():
        c=saved['cases'][label]
        for stage in ['baselines','repeats']:
            for manager in ['original','candidate']:
                for family in FAMILIES:events.append((manager,points,family,c[stage][manager][family]))
        candidate=c['baselines']['candidate']
        vectors={'alternating_global':[(-1. if i%2==0 else 1.)/math.sqrt(3*count) for i in range(3*count)]}
        if candidate['all']['gradient_norm']:vectors['full_gradient']=[v/candidate['all']['gradient_norm'] for v in candidate['all']['gradient']]
        for i in indices:
            for axis in range(3):vectors[f'atom_{i}_axis_{axis}']=[float(j==3*i+axis) for j in range(3*count)]
        for family in ['all','dihedral']:
            directions=dict(vectors)
            if family=='dihedral' and candidate[family]['gradient_norm']:
                directions['family_gradient']=[v/candidate[family]['gradient_norm'] for v in candidate[family]['gradient']]
            rows=c['candidate_derivatives'][family]
            if [r['direction'] for r in rows]!=list(directions):raise ValueError('Saved derivative directions differ')
            for row in rows:
                v=directions[row['direction']]
                if len(row['samples'])!=len(STEPS):raise ValueError('Saved step count differs')
                for sample,h in zip(row['samples'],STEPS):
                    if sample['step_angstrom']!=h:raise ValueError('Saved finite-difference step differs')
                    for sign,prefix in [(1,'plus'),(-1,'minus')]:
                        moved=[[x+sign*h*v[3*i+j] for j,x in enumerate(p)] for i,p in enumerate(points)]
                        events.append(('candidate',moved,family,{'target':sample[prefix+'_target'],'gradient':[0.]*(3*count),'proxy_counts':sample[prefix+'_proxy_counts']}))
        for manager in ['original','candidate']:
            for family in FAMILIES:events.append((manager,points,family,c['final_repeats'][manager][family]))
    cursor=0
    def evaluate(manager,points,family):
        nonlocal cursor
        if cursor>=len(events):raise ValueError('Saved call sequence exhausted')
        m,p,f,row=events[cursor];cursor+=1
        if (m,p,f)!=(manager,points,family):raise ValueError('Saved native call identity differs')
        return deepcopy(row)
    rebuilt=audit_linear_torsion_impact(evaluate,cases,indices,references,max_calls=2000)
    def same(a,b):
        if type(a) is float or type(b) is float:return type(a) in (int,float) and type(b) in (int,float) and _close(a,b)
        if isinstance(a,dict):return isinstance(b,dict) and set(a)==set(b) and all(same(a[k],b[k]) for k in a)
        if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
        return type(a) is type(b) and a==b
    if cursor!=len(events) or any(not same(rebuilt[k],saved[k]) for k in rebuilt):raise ValueError('Saved numerical impact evidence does not replay')
    return {'status':'SAVED_EVIDENCE_REPLAY_PASS','captured_code_execution':'NOT_RUN','evaluation_calls_recomputed':cursor,
        'cases':{label:{'failed_checks':[k for k,v in c['checks'].items() if not v],
            'arithmetic_directions_pass':{family:sum(any(a['absolute_error']<=a['bound'] and b['absolute_error']<=b['bound'] for a,b in zip(d['samples'],d['samples'][1:])) for d in rows)
                for family,rows in c['candidate_derivatives'].items()}} for label,c in rebuilt['cases'].items()}}


_WORKER=r'''from pathlib import Path
import hashlib,importlib,json,os,sys,traceback
from impact_core import POLICY_ID,audit_linear_torsion_impact
from gradient_core import fixed_signature
work=Path.cwd();spec=json.loads(Path(sys.argv[1]).read_text());root=Path(spec['installation_root']).resolve(strict=True)
result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN'}
try:
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    modules=[importlib.import_module(r['module']) for r in spec['expected_numeric_sources']]
    def record(m):
        p=Path(m.__file__).resolve();return {'module':m.__name__,'historical_path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    sources=[record(m) for m in modules];adapters=[record(m) for m in [gr,flex]]
    if [(r['module'],r['sha256']) for r in sources]!=[(r['module'],r['sha256']) for r in spec['expected_numeric_sources']]:raise RuntimeError('Native numerical sources changed')
    if any(not Path(r['historical_path']).is_relative_to(root) for r in sources+adapters):raise RuntimeError('Unselected numerical adapter/module')
    managers={};signatures={};reports={}
    for name in ['original','candidate']:
        os.chdir(work/name);sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
        try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
        except SystemExit as exc:
            if exc.code!=0:raise RuntimeError('Native inventory bootstrap failed')
        expected=json.loads(Path('expected_inventory.json').read_text());actual=namespace['report']
        fields=['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy','fatal_problems','unused_definitions','unsupported_fields']
        if any(actual.get(k)!=expected.get(k) for k in fields):raise RuntimeError(name+' native manager changed')
        geo,sites=namespace['geo'],namespace['sites']
        if len(geo.site_symmetry_table.special_position_indices()) or geo.parallelity_proxies:raise RuntimeError('Unsupported special-position/parallelity manager')
        managers[name]=(geo,sites);signatures[name]=fixed_signature(geo,sites);reports[name]=actual
    os.chdir(work)
    if reports['original']['atoms']!=reports['candidate']['atoms']:raise RuntimeError('Original/candidate atom identity differs')
    def evaluate(manager,points,family):
        geo,_=managers[manager];active=flags.flags(default=family=='all')
        if family!='all':setattr(active,family,True)
        e=geo.energies_sites(sites_cart=flex.vec3_double(points),flags=active,compute_gradients=True,normalization=False)
        return {'target':float(e.target),'gradient':[float(v) for v in e.gradients.as_double()],
            'proxy_counts':{k:v for k,v in vars(e).items() if k.startswith('n_') and k.endswith('_proxies') and (v is None or isinstance(v,int))}}
    if spec.get('cache_preflight'):
        from cache_core import audit_cache_stabilized_impact,native_cache_evaluator
        installed=[]
        for path in [*[Path(r['historical_path']) for r in sources if r['module'] in ['cctbx.geometry_restraints.manager','cctbx.geometry_restraints.energies']],
                     Path(gr.__file__).resolve().parent/'nonbonded.h',Path(gr.__file__).resolve().parent/'nonbonded_bpl.cpp']:
            row={'historical_path':str(path),'status':'UNAVAILABLE'}
            if path.is_file():
                data=path.read_bytes();target=work/'installed_source'/path.name;target.parent.mkdir(exist_ok=True);target.write_bytes(data)
                row.update(status='RECORDED',path=target.relative_to(work).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
            installed.append(row)
        result.update(audit_cache_stabilized_impact(native_cache_evaluator(managers,gr,flex,flags),spec['coordinate_cases'],spec['selected_indices'],spec['removed_references']))
        result['installed_cache_sources']=installed
    else:
        result.update(audit_linear_torsion_impact(evaluate,spec['coordinate_cases'],spec['selected_indices'],spec['removed_references'],max_calls=2000))
    after={name:fixed_signature(geo,sites) for name,(geo,sites) in managers.items()}
    if after!=signatures:raise RuntimeError('Native constraints changed during numerical impact audit')
    for row in sources+adapters:
        if hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Native numerical adapter/source changed during audit')
    for row in result.get('installed_cache_sources',[]):
        if row['status']=='RECORDED' and hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Installed cache source changed')
    result.update(status='REVIEW',captured_inventories_match=True,constraint_signatures_before=signatures,constraint_signatures_after=after,
        installed_numeric_sources=sources,installed_adapter_sources=adapters,normalization=False)
except Exception as exc:
    result.update(status='FAILED',error=type(exc).__name__+': '+str(exc));traceback.print_exc()
finally:os.chdir(work)
Path('impact_result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def run_native_linear_torsion_impact(model,original_dictionary,candidate_dictionary,phils,expected,coordinate_cases,selected_indices,
        removed_references,numeric_sources,output_parent,executable,*,environment,phenix_version,installation_root,timeout_seconds=180,cache_preflight=False):
    """Rebuild two exact isolated managers in one owned, bounded interpreter."""
    from .cif_native_validation import _NATIVE_WORKER,_artifact,_stop,NATIVE_POLICY_ID
    from .cif_fixed_geometry import _model,_fixed_policy
    from . import cif_gradient_audit
    if set(expected)!={'original','candidate'} or not all(_fixed_policy(v) for v in expected.values()):raise ValueError('Require both captured explicit policies')
    if not phenix_version or type(timeout_seconds) is not int or not 1<=timeout_seconds<=180:raise ValueError('Require bounded native execution/version')
    if type(cache_preflight) is not bool:raise ValueError('Cache preflight must be explicit boolean')
    if len(numeric_sources)!=6 or len({v['module'] for v in numeric_sources})!=6:raise ValueError('Require six pinned numerical source identities')
    root=Path(installation_root).resolve(strict=True);executable=Path(executable).resolve(strict=True)
    if not executable.is_relative_to(root):raise ValueError('Require selected installation interpreter')
    paths=[Path(p).resolve(strict=True) for p in [model,original_dictionary,candidate_dictionary,*phils]];parent=Path(output_parent).resolve()
    if len(set(paths))!=len(paths) or any(parent==p.parent or p.parent in parent.parents for p in paths):raise ValueError('Require separate native output and distinct inputs')
    for v in expected.values():_model(v,paths[0],coordinates_match=True)
    if any(len(p)!=expected['original']['atom_count'] for p in coordinate_cases.values()):raise ValueError('Coordinate counts differ')
    _validate(coordinate_cases,selected_indices,removed_references,2000)
    original=[p.read_bytes() for p in paths];dispatcher=executable.read_bytes();parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='cif-linear-torsion-impact-',dir=parent));frozen=[];inputs=[]
    for name,index in [('original',1),('candidate',2)]:
        phase=work/name;(phase/'inputs').mkdir(parents=True)
        phase_paths=[paths[0],paths[index],*paths[3:]];phase_payloads=[original[0],original[index],*original[3:]];saved=[]
        for i,(path,data) in enumerate(zip(phase_paths,phase_payloads)):
            role='model' if i==0 else 'dictionary' if i==1 else 'phil';target=phase/'inputs'/(f'{i:03d}_'+role+path.suffix);target.write_bytes(data);saved.append(target);frozen.append((target,data))
            inputs.append({'phase':name,'role':role,'source_provenance':str(path),**_artifact(target,work)})
        spec={'policy_id':NATIVE_POLICY_ID,'model':saved[0].relative_to(phase).as_posix(),'dictionaries':[saved[1].relative_to(phase).as_posix()],
            'phil_files':[p.relative_to(phase).as_posix() for p in saved[2:]],'phil_namespace_policy':'direct','inventory_detail':'linked','policy_inventory':True}
        for filename,value in [('native_spec.json',spec),('expected_inventory.json',expected[name])]:
            (phase/filename).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
        (phase/'native_worker.py').write_text(_NATIVE_WORKER)
    spec={'installation_root':str(root),'coordinate_cases':coordinate_cases,'selected_indices':selected_indices,'removed_references':removed_references,'expected_numeric_sources':numeric_sources}
    if cache_preflight:
        from . import cif_nonbonded_cache_audit
        spec['cache_preflight']=True;(work/'cache_core.py').write_bytes(Path(cif_nonbonded_cache_audit.__file__).read_bytes())
    (work/'impact_spec.json').write_text(json.dumps(spec,indent=2,sort_keys=True,allow_nan=False)+'\n');(work/'impact_worker.py').write_text(_WORKER)
    (work/'impact_core.py').write_bytes(Path(__file__).read_bytes());(work/'gradient_core.py').write_bytes(Path(cif_gradient_audit.__file__).read_bytes())
    receipt={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','native_directory':str(work),'inputs':inputs,'phenix_version':phenix_version,
        'executable_sha256':hashlib.sha256(dispatcher).hexdigest(),'execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds},
        'model_optimization':'NOT_RUN','model_editing':'NOT_RUN','readyset':'NOT_RUN','dictionary_generation':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False}
    if cache_preflight:receipt['cache_preflight_requested']=True
    started=time.monotonic()
    try:
        with (work/'impact.log').open('xb') as log:
            process=subprocess.Popen([str(executable),'-B','impact_worker.py','impact_spec.json'],cwd=work,env={**environment,'PYTHONDONTWRITEBYTECODE':'1'},
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:rc=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:_stop(process);receipt['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_stop(process);raise
            else:
                receipt['execution'].update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc)
                result=json.loads((work/'impact_result.json').read_text());receipt['result']=result
                if (rc==0 and result.get('policy_id')==POLICY_ID and result.get('status')=='REVIEW' and result.get('analysis_completed') is True
                        and result.get('captured_inventories_match') is True and result.get('model_optimization')=='NOT_RUN' and result.get('automatic_adoption') is False
                        and 0<result.get('evaluation_calls',0)<=2000 and set(result.get('cases',{}))==set(coordinate_cases)
                        and result.get('constraint_signatures_before')==result.get('constraint_signatures_after')
                        and (not cache_preflight or result.get('cache_preflight_completed') is True and result.get('cache_policy_id')=='cif-native-nonbonded-cache-proof-v1'
                             and 0<result.get('pair_kernel_calls',0)<=5000)):receipt['status']='REVIEW'
                else:receipt['error']=result.get('error','Incomplete numerical impact evidence')
    except (OSError,ValueError,KeyError,TypeError) as exc:receipt['error']=str(exc);receipt['execution']['status']='FAILED'
    receipt['source_preserved']=all(p.is_file() and p.read_bytes()==d for p,d in zip(paths,original)) and executable.read_bytes()==dispatcher
    receipt['frozen_inputs_preserved']=all(p.is_file() and p.read_bytes()==d for p,d in frozen)
    if not receipt['source_preserved'] or not receipt['frozen_inputs_preserved']:receipt.update(status='FAILED',error='Original or frozen inputs changed')
    receipt['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
    receipt['outputs']=[_artifact(p,work) for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):receipt.update(status='FAILED',error='Unexpected native output symlink')
    (work/'impact_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return receipt
