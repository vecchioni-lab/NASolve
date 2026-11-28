"""Bounded numerical checks of a fixed native objective; no minimization."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

POLICY_ID='cif-fixed-native-gradient-audit-v1'
FAMILIES=('all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded')
STEPS=(1e-3,1e-4,1e-5,1e-6)
FD_ABSOLUTE=1e-4
FD_RELATIVE=1e-4


def _norm(values):return math.sqrt(math.fsum(v*v for v in values))
def _unit(values):
    length=_norm(values)
    return [v/length for v in values] if length else None
def _close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)


def audit_gradients(evaluate,coordinate_cases,selected_indices,*,references=None,max_calls=4000):
    """Compare directional derivatives at four steps, retaining raw evidence.

    ``evaluate(points, family)`` returns a target and a flat Cartesian gradient.
    Per-family evaluations are isolated controls, never adopted objectives.
    Consistency applies only to sampled directions at these coordinates.
    """
    if not coordinate_cases or type(max_calls) is not int or not 1<=max_calls<=6000:raise ValueError('Invalid audit cases or budget')
    count=len(next(iter(coordinate_cases.values())))
    if not count or not 1<=len(selected_indices)<=6 or len(set(selected_indices))!=len(selected_indices):raise ValueError('Invalid coordinate probes')
    if any(type(i) is not int or not 0<=i<count for i in selected_indices):raise ValueError('Invalid coordinate probes')
    for points in coordinate_cases.values():
        if len(points)!=count or any(len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points):
            raise ValueError('Require complete finite coordinates')
    result={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','analysis_completed':False,
        'model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN',
        'step_sizes':list(STEPS),'directional_tolerance':{'absolute':FD_ABSOLUTE,'relative':FD_RELATIVE},
        'repeat_and_snapshot_tolerance':{'absolute':1e-8,'relative':1e-10},
        'selected_indices':list(selected_indices),'max_evaluation_calls':max_calls,'evaluation_calls':0,'cases':{},
        'limitations':['Sampled directional agreement does not prove every gradient component or global convergence.',
            'Control-family flags are diagnostic evaluations only; no policy, target, weight or model is adopted.']}
    def call(points,family):
        if result['evaluation_calls']>=max_calls:raise ValueError('Native evaluation budget exhausted')
        result['evaluation_calls']+=1;raw=evaluate(deepcopy(points),family)
        target=float(raw['target']);gradient=list(raw['gradient'])
        if not math.isfinite(target) or len(gradient)!=3*count or any(type(v) not in (int,float) or not math.isfinite(v) for v in gradient):
            raise ValueError('Require finite target and complete Cartesian gradient')
        return {**raw,'target':target,'gradient':gradient,'gradient_norm':_norm(gradient)}
    for label,points in coordinate_cases.items():
        baselines={family:call(points,family) for family in FAMILIES};full=baselines['all']
        case={'families':{},'captured_snapshot_match':{'consistent':True,'comparisons':{}},'descent_profile':[]}
        reference=(references or {}).get(label,{})
        for field in ['target','gradient_norm']:
            if field in reference:
                case['captured_snapshot_match']['comparisons'][field]={'captured':reference[field],'rebuilt':full[field],'consistent':_close(reference[field],full[field])}
        case['captured_snapshot_match']['consistent']=all(v['consistent'] for v in case['captured_snapshot_match']['comparisons'].values())
        target_sum=math.fsum(baselines[f]['target'] for f in FAMILIES[1:])
        gradient_sum=[math.fsum(baselines[f]['gradient'][i] for f in FAMILIES[1:]) for i in range(3*count)]
        case['target_additivity']={'all':full['target'],'sum_controls':target_sum,'consistent':_close(target_sum,full['target'])}
        mismatch=_norm([a-b for a,b in zip(gradient_sum,full['gradient'])])
        case['gradient_additivity']={'difference_norm':mismatch,'consistent':mismatch<=1e-8+1e-10*max(1.,full['gradient_norm'])}
        common=[]
        if (direction:=_unit(full['gradient'])) is not None:common.append(('full_gradient',direction))
        common.append(('alternating_global',_unit([1. if i%2 else -1. for i in range(3*count)])))
        for index in selected_indices:
            for axis in range(3):
                direction=[0.]*(3*count);direction[3*index+axis]=1.;common.append((f'atom_{index}_axis_{axis}',direction))
        for family in FAMILIES:
            baseline=baselines[family];directions=list(common)
            if (direction:=_unit(baseline['gradient'])) is not None:directions.append(('family_gradient',direction))
            rows=[]
            for name,direction in directions:
                analytical=math.fsum(a*b for a,b in zip(baseline['gradient'],direction));samples=[]
                for step in STEPS:
                    shifted=lambda sign:[[v+sign*step*direction[3*i+j] for j,v in enumerate(p)] for i,p in enumerate(points)]
                    plus,minus=call(shifted(1),family),call(shifted(-1),family)
                    numerical=(plus['target']-minus['target'])/(2*step);error=abs(numerical-analytical)
                    bound=FD_ABSOLUTE+FD_RELATIVE*max(abs(numerical),abs(analytical))
                    samples.append({'step':step,'plus_target':plus['target'],'minus_target':minus['target'],
                        'numerical':numerical,'absolute_error':error,'bound':bound,'consistent':error<=bound,
                        'plus_proxy_counts':plus.get('proxy_counts',{}),'minus_proxy_counts':minus.get('proxy_counts',{})})
                consecutive=any(samples[i]['consistent'] and samples[i+1]['consistent'] for i in range(len(samples)-1))
                rows.append({'direction':name,'analytical':analytical,'samples':samples,'status':'CONSISTENT' if consecutive else 'REVIEW'})
            repeat=call(points,family)
            repeat_ok=_close(repeat['target'],baseline['target']) and all(_close(a,b) for a,b in zip(repeat['gradient'],baseline['gradient']))
            case['families'][family]={'baseline':baseline,'directions':rows,'repeat_target':repeat['target'],
                'repeat_gradient_norm':repeat['gradient_norm'],'repeat_consistent':repeat_ok,
                'sampled_directions_consistent':all(r['status']=='CONSISTENT' for r in rows)}
        if (direction:=_unit(full['gradient'])) is not None:
            for step in [1e-2,1e-3,1e-4,1e-5,1e-6,1e-7]:
                moved=[[v-step*direction[3*i+j] for j,v in enumerate(p)] for i,p in enumerate(points)]
                sample=call(moved,'all');case['descent_profile'].append({'step':step,'target':sample['target'],
                    'change':sample['target']-full['target'],'first_order_change':-step*full['gradient_norm'],
                    'proxy_counts':sample.get('proxy_counts',{})})
        final=call(points,'all')
        case['baseline_repeats_consistent']=all(v['repeat_consistent'] for v in case['families'].values()) and _close(final['target'],full['target']) and all(_close(a,b) for a,b in zip(final['gradient'],full['gradient']))
        case['sampled_gradients_consistent']=all(v['sampled_directions_consistent'] for v in case['families'].values()) and case['baseline_repeats_consistent'] and case['target_additivity']['consistent'] and case['gradient_additivity']['consistent'] and case['captured_snapshot_match']['consistent']
        result['cases'][label]=case
    result['analysis_completed']=True
    return result


def fixed_signature(geo,points):
    """Fingerprint static targets, weights, membership and symmetry, not neighbours."""
    def value(v):return v if v is None or isinstance(v,(str,bool,int,float)) else list(v)
    pair=geo.pair_proxies(sites_cart=points).bond_proxies
    data={'simple':[[list(p.i_seqs),float(p.distance_ideal),float(p.weight),getattr(p,'origin_id',None),
        value(getattr(p,'slack',None)),value(getattr(p,'limit',None)),value(getattr(p,'top_out',None)),str(getattr(p,'rt_mx_ji',None))] for p in pair.simple],
        'asu':[[int(p.i_seq),int(p.j_seq),int(p.j_sym),float(p.distance_ideal),float(p.weight),getattr(p,'origin_id',None),str(pair.asu_mappings().get_rt_mx_ji(pair=p))] for p in pair.asu]}
    fields={'angle':['angle_ideal','weight'],'dihedral':['angle_ideal','weight','periodicity','alt_angle_ideals'],
        'const_dihedral':['angle_ideal','weight','periodicity'],'chirality':['volume_ideal','both_signs','weight'],
        'planarity':['weights'],'parallelity':['j_seqs','weight','target_angle_deg','slack','top_out']}
    for kind,attributes in fields.items():
        data[kind]=[[list(p.i_seqs),getattr(p,'origin_id',None)]+[value(getattr(p,a,None)) for a in attributes] for p in (getattr(geo,kind+'_proxies') or [])]
    return hashlib.sha256(json.dumps(data,sort_keys=True,allow_nan=False).encode()).hexdigest()


def review_distance_groups(native,points):
    """Group explicit intersite distance requests; choose probes from raw outliers."""
    from .cif_fixed_geometry import review_fixed_coordinates
    report=review_fixed_coordinates(native,points);groups={};indices=[]
    atoms=native['atoms']
    site=lambda i:atoms[i]['identity']['chain_id'].strip()+':'+atoms[i]['identity']['resseq'].strip()
    for request in native['geometry']['custom_proxy_requests']:
        if request['kind']!='bond':continue
        pair=sorted({site(i) for i in request['i_seqs']})
        if len(pair)!=2:continue
        observed=math.dist(*(points[i] for i in request['i_seqs']))
        groups.setdefault(tuple(pair),[]).append({'atoms':request['atoms'],'i_seqs':request['i_seqs'],
            'target':request['distance_ideal'],'observed':observed,'nominal_deviation':(observed-request['distance_ideal'])*math.sqrt(request['weight'])})
    measured=[r for kind in ['bond_simple','angle'] for r in report['measurements'][kind] if r['nominal_deviation'] is not None]
    for row in sorted(measured,key=lambda r:-abs(r['nominal_deviation'])):
        for i in row['i_seqs']:
            if i not in indices:indices.append(i)
            if len(indices)==6:break
        if len(indices)==6:break
    if not indices:indices=list(range(min(6,len(atoms))))
    return {'schema_version':1,'status':'REVIEW','groups':[{'sites':list(s),'requests':v} for s,v in sorted(groups.items())],
        'selected_indices':indices,'selected_labels':[atoms[i]['label'] for i in indices],
        'selection':'First six unique endpoints of largest absolute captured bond/angle nominal deviations; no site/code allowlist.',
        'scientific_approval':'NOT_RUN','automatic_adoption':False}


_GRADIENT_WORKER=r'''from __future__ import print_function
import hashlib,importlib,json,sys,traceback
from pathlib import Path
from gradient_core import audit_gradients,fixed_signature,FAMILIES
spec=json.loads(Path(sys.argv[1]).read_text())
result={'schema_version':1,'policy_id':spec['policy_id'],'status':'FAILED','model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN'}
try:
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Native inventory bootstrap failed')
    expected=json.loads(Path('expected_inventory.json').read_text());actual=namespace['report']
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):
        raise RuntimeError('Native manager changed before gradient audit')
    result['captured_inventory_matches']=True
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    import scitbx.lbfgs
    modules=[scitbx.lbfgs,flags,importlib.import_module('cctbx.geometry_restraints.manager'),importlib.import_module('cctbx.geometry_restraints.energies'),importlib.import_module('scitbx_lbfgs_ext'),importlib.import_module('cctbx_geometry_restraints_ext')]
    sources=[{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in modules]
    sig=lambda rows:[(r['module'],r['sha256']) for r in rows]
    if sig(sources)!=sig(spec['expected_numeric_sources']):raise RuntimeError('Native numerical sources changed')
    geo=namespace['geo'];sites=namespace['sites']
    if len(geo.site_symmetry_table.special_position_indices()):raise RuntimeError('Special-position gradient policy unsupported')
    original=fixed_signature(geo,sites)
    if original!=spec['expected_constraint_signature']:raise RuntimeError('Static native constraints differ from saved trial')
    def evaluate(points,family):
        active=flags.flags(default=family=='all')
        if family!='all':setattr(active,family,True)
        e=geo.energies_sites(sites_cart=flex.vec3_double(points),flags=active,compute_gradients=True,normalization=False)
        return {'target':float(e.target),'gradient':[float(v) for v in e.gradients.as_double()],
            'terms':{k:float(v) for k,v in vars(e).items() if k.endswith('_residual_sum') and isinstance(v,(int,float))},
            'proxy_counts':{k:v for k,v in vars(e).items() if k.startswith('n_') and k.endswith('_proxies') and (v is None or isinstance(v,int))}}
    result.update(audit_gradients(evaluate,spec['coordinate_cases'],spec['selected_indices'],references=spec['references'],max_calls=spec['max_calls']))
    result['captured_inventory_matches']=True;result['installed_numeric_sources']=sources
    result['constraint_signature_before']=original;result['constraint_signature_after']=fixed_signature(geo,sites)
    if result['constraint_signature_after']!=original:raise RuntimeError('Static native constraints changed during numerical evaluation')
    for row in sources:
        if hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Native numerical source changed during audit')
    result['normalization']=False;result['status']='REVIEW'
except Exception as exc:
    result.update(status='FAILED',error=type(exc).__name__+': '+str(exc));traceback.print_exc()
Path('gradient_result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def run_native_gradient_audit(model,dictionaries,phils,expected,coordinate_cases,references,selected_indices,
        expected_numeric_sources,expected_constraint_signature,output_parent,executable,*,environment,phenix_version,timeout_seconds=1200):
    """Rebuild one exact manager and evaluate finite differences in an owned job."""
    from .cif_native_validation import _NATIVE_WORKER,_artifact,_stop,NATIVE_POLICY_ID
    from .cif_fixed_geometry import _model,_fixed_policy,_points
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=3600:raise ValueError('Invalid native timeout')
    if not _fixed_policy(expected) or not phenix_version:raise ValueError('Require captured explicit policy and native version')
    _model(expected,model,coordinates_match=True)
    if set(coordinate_cases)!={'full_precision','pdb_rounded'}:raise ValueError('Require full-precision and rounded coordinate cases')
    for points in coordinate_cases.values():_points(points,expected['atom_count'])
    paths=[Path(p).resolve() for p in [model,*dictionaries,*phils]];parent=Path(output_parent).resolve()
    if not dictionaries or len(paths)!=len(set(paths)) or any(parent==p.parent or p.parent in parent.parents for p in paths):raise ValueError('Require distinct inputs and separate output')
    original=[p.read_bytes() for p in paths];parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='cif-gradient-audit-',dir=parent));(work/'inputs').mkdir();frozen=[];inputs=[]
    for i,(path,data) in enumerate(zip(paths,original)):
        role='model' if i==0 else 'dictionary' if i<=len(dictionaries) else 'phil'
        target=work/'inputs'/(f'{i:03d}_{role}'+path.suffix);target.write_bytes(data);frozen.append(target)
        inputs.append({'role':role,'input_index':i,'source_provenance':str(path),**_artifact(target,work)})
    native={'policy_id':NATIVE_POLICY_ID,'model':frozen[0].relative_to(work).as_posix(),
        'dictionaries':[p.relative_to(work).as_posix() for p in frozen[1:1+len(dictionaries)]],
        'phil_files':[p.relative_to(work).as_posix() for p in frozen[1+len(dictionaries):]],
        'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked','policy_inventory':True}
    spec={'policy_id':POLICY_ID,'coordinate_cases':coordinate_cases,'references':references,'selected_indices':selected_indices,
        'expected_numeric_sources':expected_numeric_sources,'expected_constraint_signature':expected_constraint_signature,'max_calls':4000}
    for name,value in [('native_spec.json',native),('expected_inventory.json',expected),('gradient_spec.json',spec)]:
        (work/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    (work/'native_worker.py').write_text(_NATIVE_WORKER);(work/'gradient_worker.py').write_text(_GRADIENT_WORKER)
    (work/'gradient_core.py').write_bytes(Path(__file__).read_bytes())
    executable=Path(executable).resolve();command=[str(executable),'gradient_worker.py','gradient_spec.json']
    receipt={'schema_version':1,'audit_kind':'cif_fixed_native_gradient_audit','policy_id':POLICY_ID,'status':'FAILED',
        'native_directory':str(work),'inputs':inputs,'command':command,'phenix_version':phenix_version,
        'executable_provenance':str(executable),'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
        'model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN','execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds}}
    started=time.monotonic()
    try:
        with (work/'gradient.log').open('xb') as log:
            process=subprocess.Popen(command,cwd=work,env=dict(environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:code=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:_stop(process);receipt['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_stop(process);raise
            else:
                receipt['execution'].update(status='COMPLETED' if code==0 else 'FAILED',returncode=code)
                result=json.loads((work/'gradient_result.json').read_text());receipt['result']=result
                if (code==0 and result.get('status')=='REVIEW' and result.get('policy_id')==POLICY_ID
                        and result.get('analysis_completed') and result.get('captured_inventory_matches')
                        and result.get('model_optimization')=='NOT_RUN' and result.get('automatic_adoption') is False
                        and set(result.get('cases',{}))==set(coordinate_cases) and 0<result.get('evaluation_calls',0)<=4000
                        and result.get('constraint_signature_before')==result.get('constraint_signature_after')==expected_constraint_signature):
                    receipt['status']='REVIEW'
                else:receipt['error']=result.get('error','Incomplete fixed-manager gradient evidence')
    except (OSError,ValueError,KeyError,TypeError) as exc:receipt.update(error=str(exc));receipt['execution']['status']='FAILED'
    receipt['source_preserved']=all(p.is_file() and p.read_bytes()==data for p,data in zip(paths,original))
    receipt['frozen_inputs_preserved']=all(p.is_file() and p.read_bytes()==data for p,data in zip(frozen,original))
    if not receipt['source_preserved'] or not receipt['frozen_inputs_preserved']:receipt.update(status='FAILED',error='Original or frozen inputs changed')
    receipt['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
    receipt['outputs']=[_artifact(p,work) for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):receipt.update(status='FAILED',error='Unexpected output symlink')
    (work/'gradient_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return receipt
