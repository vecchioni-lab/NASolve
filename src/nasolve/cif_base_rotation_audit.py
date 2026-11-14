"""Bounded base-orientation diagnostics under an unchanged native objective.

Rotations are ephemeral evaluations, not optimized or adoptable coordinates.
The graph rule is shared with attached-fragment restoration; no residue code
or base-attachment atom name selects the moving group.
"""
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

POLICY_ID='cif-fixed-na-base-rotation-audit-v1'
ANGLES=(-180,-90,-30,-10,0,10,30,90,180)
STEPS=(1e-3,1e-4,1e-5,1e-6)
FAMILIES=('all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded')
MAX_CALLS=3000


def _norm(v):return math.sqrt(math.fsum(x*x for x in v))
def _close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def _finite(values):
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('Require finite numerical evidence')


def _axis(points,group):
    if (len(points)<3 or any(len(p)!=3 for p in points)):
        raise ValueError('Require complete Cartesian coordinates')
    _finite([v for p in points for v in p])
    indices=group['i_seqs'];origin=group['origin_index'];anchor=group['attachment_index']
    if (not indices or len(set(indices))!=len(indices) or origin in indices or anchor not in indices
            or any(type(i) is not int or not 0<=i<len(points) for i in [*indices,origin,anchor])):
        raise ValueError('Require an unambiguous base and attachment axis')
    vector=[a-b for a,b in zip(points[anchor],points[origin])];length=_norm(vector)
    if length<.5:raise ValueError('Degenerate base attachment axis')
    return points[origin],[v/length for v in vector]


def rotate_group(points,group,radians):
    """Proper Rodrigues rotation about C1'-attachment; scaffold is exact."""
    _finite([radians]);origin,axis=_axis(points,group);out=deepcopy(points)
    if radians==0:return out
    c,s=math.cos(radians),math.sin(radians)
    for i in group['i_seqs']:
        if i==group['attachment_index']:continue
        v=[a-b for a,b in zip(points[i],origin)];cross=_cross(axis,v);dot=math.fsum(a*b for a,b in zip(axis,v))
        out[i]=[o+c*x+s*y+(1-c)*dot*z for o,x,y,z in zip(origin,v,cross,axis)]
    return out


def rotational_derivative(gradient,points,group):
    origin,axis=_axis(points,group)
    return math.fsum(gradient[3*i+j]*v for i in group['i_seqs']
        for j,v in enumerate(_cross(axis,[a-b for a,b in zip(points[i],origin)])))


def plan_base_rotations(native,points,*,threshold=5.,max_groups=6):
    """Select supported base groups from nominal bond/angle outlier sites."""
    from .cif_fixed_geometry import review_fixed_coordinates
    from .cif_fragment_restoration import _fragment,_key
    _finite([threshold])
    if threshold<=0 or type(max_groups) is not int or not 1<=max_groups<=6:raise ValueError('Invalid rotation selection bounds')
    atoms=native['atoms']
    if len({_key(a) for a in atoms})!=len(atoms):raise ValueError('Ambiguous captured atom identities')
    report=review_fixed_coordinates(native,points)
    outliers=[{'kind':kind,**row} for kind in ['bond_simple','angle'] for row in report['measurements'][kind]
        if row['nominal_deviation'] is not None and abs(row['nominal_deviation'])>=threshold]
    sites={s:max(abs(r['nominal_deviation']) for r in outliers if s in r['sites']) for s in {s for r in outliers for s in r['sites']}}
    mappings=native['monomer_mappings']['rows']
    if len({r['site'] for r in mappings})!=len(mappings):raise ValueError('Ambiguous native site mappings')
    mappings={r['site']:r for r in mappings};groups=[];unsupported=[];unprobed=[]
    for site in sorted(sites,key=lambda s:(-sites[s],s)):
        if len(groups)>=max_groups:unprobed.append({'site':site,'reason':'Declared group limit','rank':sites[site]});continue
        selected=[a for a in atoms if (a['identity']['chain_id'].strip() or '_')+':'+a['identity']['resseq'].strip()+a['identity']['icode'].strip()==site]
        try:
            if site not in mappings or any(a['identity']['altloc'].strip() or a['identity']['icode'].strip() for a in selected):
                raise ValueError('Alternate or insertion context requires a separate rule')
            definition=mappings[site]['metadata']['effective_definition'];byid={a['atom_id']:a for a in selected}
            fragment,anchor=_fragment(definition,byid)
            g={'site':site,'component':mappings[site]['resname'],'i_seqs':[byid[a]['i_seq'] for a in fragment],
               'atom_ids':fragment,'attachment_atom':anchor,'attachment_index':byid[anchor]['i_seq'],
               'origin_index':byid["C1'"]['i_seq'],'axis_definition':'C1_PRIME_TO_GRAPH_SELECTED_ATTACHMENT',
               'rank':sites[site],'outlier_constraints':[r for r in outliers if site in r['sites']]}
            _axis(points,g)
            contexts=[]
            for row in g['outlier_constraints']:
                if row['kind']!='angle' or row['sites']!=[site]:continue
                names=[atoms[i]['atom_id'] for i in row['i_seqs']]
                planes={}
                for p in definition.get('plane_atoms',[]):planes.setdefault(p['plane_id'],set()).add(p['atom_id'])
                contexts.append({'atom_ids':names,'target':row['target'],'observed':row['observed'],
                    'weight':row['weight'],'common_declared_planes':[k for k,v in planes.items() if set(names)<=v],
                    'center_atom_rows':[a for a in definition['atoms'] if a['atom_id']==names[1]],
                    'definition_rows':[a for a in definition.get('angles',[]) if [a['atom_id_1'],a['atom_id_2'],a['atom_id_3']] in [names,names[::-1]]]})
            g['intrasite_angle_source_contexts']=contexts;groups.append(g)
        except (ValueError,KeyError) as exc:unsupported.append({'site':site,'status':'UNSUPPORTED','reason':str(exc)})
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','groups':groups,
        'selected_sites':[g['site'] for g in groups],'unsupported_sites':unsupported,'unprobed_sites':unprobed,
        'threshold':threshold,'max_groups':max_groups,'outlier_count':len(outliers),
        'selection':'Largest nominal bond/angle outlier sites, then supported connected base graph; no code/attachment-name allowlist.',
        'model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN'}


def audit_base_rotations(evaluate,coordinate_cases,plan,*,references=None,max_calls=MAX_CALLS,measure=None):
    """Evaluate a fixed angular grid and fresh four-step rotational derivatives.

    Family flags isolate diagnostic contributions. The full objective and all
    targets/weights remain unchanged; a lower grid sample is never adopted.
    """
    if not coordinate_cases or not plan['groups'] or len(plan['groups'])>6 or type(max_calls) is not int or not 1<=max_calls<=MAX_CALLS:
        raise ValueError('Require bounded coordinate cases, groups and evaluation budget')
    if len(coordinate_cases)>2:raise ValueError('At most two coordinate precisions')
    if len({g['site'] for g in plan['groups']})!=len(plan['groups']):raise ValueError('Ambiguous selected groups')
    count=len(next(iter(coordinate_cases.values())))
    for points in coordinate_cases.values():
        if len(points)!=count:raise ValueError('Coordinate cases differ in atom count')
        for g in plan['groups']:_axis(points,g)
    result={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','analysis_completed':False,
        'angles_degrees':list(ANGLES),'derivative_steps_radians':list(STEPS),
        'derivative_tolerance':{'absolute':1e-4,'relative':1e-4},'cases':{},
        'evaluation_calls':0,'max_evaluation_calls':max_calls,'model_optimization':'NOT_RUN','model_editing':'NOT_RUN',
        'automatic_adoption':False,'scientific_approval':'NOT_RUN',
        'limitations':['Finite angular samples are neither optimized candidates nor proof of a minimum.',
            'Each base is tested independently; coupled backbone/base or two-base motions are not sampled.',
            'Internal base geometry is preserved; this scan cannot repair an inconsistent internal angle target.',
            'Nominal scalar outliers and torque decompositions are descriptive, not chemical acceptance gates.']}
    def call(points,family):
        if result['evaluation_calls']>=max_calls:raise ValueError('Native rotation evaluation budget exhausted')
        result['evaluation_calls']+=1;raw=evaluate(deepcopy(points),family);target=raw['target'];gradient=list(raw['gradient'])
        _finite([target,*gradient])
        if len(gradient)!=3*count:raise ValueError('Incomplete Cartesian gradient')
        return {**raw,'gradient':gradient,'gradient_norm':_norm(gradient)}
    def derivative(base,group,radians,baseline,family):
        points=rotate_group(base,group,radians);analytical=rotational_derivative(baseline['gradient'],points,group);samples=[]
        for step in STEPS:
            plus=call(rotate_group(base,group,radians+step),family);minus=call(rotate_group(base,group,radians-step),family)
            numerical=(plus['target']-minus['target'])/(2*step);error=abs(numerical-analytical);bound=1e-4+1e-4*max(abs(numerical),abs(analytical))
            samples.append({'step_radians':step,'plus_target':plus['target'],'minus_target':minus['target'],
                'numerical':numerical,'absolute_error':error,'bound':bound,'consistent':error<=bound,
                'plus_proxy_counts':plus.get('proxy_counts',{}),'minus_proxy_counts':minus.get('proxy_counts',{})})
        return {'analytical_per_radian':analytical,'samples':samples,
            'consistent':any(samples[i]['consistent'] and samples[i+1]['consistent'] for i in range(3))}
    for label,points in coordinate_cases.items():
        baselines={f:call(points,f) for f in FAMILIES};reference=(references or {}).get(label,{})
        full=baselines['all'];matches=all(_close(full[k],reference[k]) for k in ['target','gradient_norm'] if k in reference)
        if 'gradient' in reference:matches=matches and len(reference['gradient'])==3*count and all(_close(a,b) for a,b in zip(reference['gradient'],full['gradient']))
        case={'baseline':baselines,'captured_snapshot_matches':matches,'groups':[]}
        for group in plan['groups']:
            profile=[];rigid_error=0.
            origin=group['origin_index'];indices=group['i_seqs']+[origin]
            for degrees in ANGLES:
                radians=math.radians(degrees);moved=rotate_group(points,group,radians)
                for i in indices:
                    for j in indices:rigid_error=max(rigid_error,abs(math.dist(moved[i],moved[j])-math.dist(points[i],points[j])))
                families=baselines if degrees==0 else {f:call(moved,f) for f in FAMILIES}
                value=families['all'];tsum=math.fsum(families[f]['target'] for f in FAMILIES[1:])
                gsum=[math.fsum(families[f]['gradient'][i] for f in FAMILIES[1:]) for i in range(3*count)]
                difference=_norm([a-b for a,b in zip(gsum,value['gradient'])])
                profile.append({'angle_degrees':degrees,'target':value['target'],'change_from_baseline':value['target']-full['target'],
                    'families':{f:{'target':v['target'],'gradient_norm':v['gradient_norm'],
                        'rotational_derivative_per_radian':rotational_derivative(v['gradient'],moved,group),
                        'proxy_counts':v.get('proxy_counts',{})} for f,v in families.items()},
                    'target_additivity':{'sum_controls':tsum,'consistent':_close(tsum,value['target'])},
                    'gradient_additivity':{'difference_norm':difference,'consistent':difference<=1e-8+1e-10*max(1.,value['gradient_norm'])},
                    'derivative':derivative(points,group,radians,value,'all')})
                if measure is not None:profile[-1]['selected_scalar_measurements']=measure(moved,group)
            local={f:derivative(points,group,0.,baselines[f],f) for f in FAMILIES[1:]}
            lowest=min(profile,key=lambda v:v['target'])
            case['groups'].append({'site':group['site'],'profile':profile,'zero_angle_family_derivatives':local,
                'periodic_energy_consistent':_close(profile[0]['target'],profile[-1]['target']),
                'max_rigid_distance_change':rigid_error,
                'lowest_sampled_target':{'angle_degrees':lowest['angle_degrees'],'target':lowest['target'],
                    'change_from_baseline':lowest['change_from_baseline'],'interpretation':'DIAGNOSTIC_SAMPLE_NOT_A_CANDIDATE_OR_OPTIMUM'}})
        repeats={f:call(points,f) for f in FAMILIES}
        case['baseline_repeats_consistent']=all(_close(repeats[f]['target'],v['target']) and all(_close(a,b) for a,b in zip(repeats[f]['gradient'],v['gradient'])) for f,v in baselines.items())
        case['sampled_rotation_derivatives_consistent']=matches and case['baseline_repeats_consistent'] and all(
            g['periodic_energy_consistent'] and g['max_rigid_distance_change']<=1e-9
            and all(v['derivative']['consistent'] and v['target_additivity']['consistent'] and v['gradient_additivity']['consistent'] for v in g['profile'])
            and all(v['consistent'] for v in g['zero_angle_family_derivatives'].values()) for g in case['groups'])
        result['cases'][label]=case
    result['analysis_completed']=True
    return result


_ROTATION_WORKER=r'''from __future__ import print_function
import hashlib,importlib,json,sys,traceback
from pathlib import Path
sys.dont_write_bytecode=True
from rotation_core import audit_base_rotations,POLICY_ID,MAX_CALLS
from gradient_core import fixed_signature
from corrected_geometry_core import validate_continuation
from scalar_geometry_core import _observed
spec=json.loads(Path(sys.argv[1]).read_text())
result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','model_optimization':'NOT_RUN',
    'model_editing':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN'}
try:
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Native inventory bootstrap failed')
    expected=json.loads(Path('expected_inventory.json').read_text());actual=namespace['report']
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):
        raise RuntimeError('Native manager changed before rotation audit')
    proof=json.loads(Path('gradient_validation.json').read_text());prior=json.loads(Path('endpoint_validation.json').read_text())
    validate_continuation(prior,proof,expected['atom_count'])
    if hashlib.sha256(Path('correction_core.py').read_bytes()).hexdigest()!=spec['correction_core_sha256']:
        raise RuntimeError('Qualified correction source changed')
    from cctbx.array_family import flex
    from cctbx import geometry_restraints as gr
    from cctbx.geometry_restraints import flags
    import scitbx.lbfgs
    from correction_core import evaluate_fixed_native,_close,_vector_agrees
    modules=[scitbx.lbfgs,flags,importlib.import_module('cctbx.geometry_restraints.manager'),
        importlib.import_module('cctbx.geometry_restraints.energies'),importlib.import_module('scitbx_lbfgs_ext'),
        importlib.import_module('cctbx_geometry_restraints_ext')]
    def sources(values):return [{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),
        'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in values]
    sig=lambda rows:[(r['module'],r['sha256']) for r in rows]
    numeric=sources(modules);adapters=sources([gr,flex])
    if sig(numeric)!=sig(proof['installed_numeric_sources']):raise RuntimeError('Qualified numerical sources differ')
    if sig(adapters)!=sig(proof['installed_adapter_sources']):raise RuntimeError('Qualified adapters differ')
    cpp=[];source_dir=Path(modules[2].__file__).resolve().parent
    for row in proof['installed_parallelity_sources']:
        if row.get('status')!='RECORDED' or row.get('path') not in {'parallelity.h','parallelity_bpl.cpp'}:raise RuntimeError('Unpinned native plane source')
        data=(source_dir/row['path']).read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise RuntimeError('Qualified native plane source differs')
        target=Path('installed_source')/row['path'];target.parent.mkdir(exist_ok=True);target.write_bytes(data);cpp.append(row)
    geo=namespace['geo'];sites=namespace['sites']
    if len(geo.site_symmetry_table.special_position_indices()):raise RuntimeError('Special-position rotation policy unsupported')
    original=fixed_signature(geo,sites)
    if original!=proof['constraint_signature_before']:raise RuntimeError('Static constraints differ from qualified manager')
    calls=[0]
    def evaluate(points,family):
        if calls[0]>=MAX_CALLS:raise RuntimeError('Native rotation evaluation budget exhausted')
        calls[0]+=1;active=flags.flags(default=family=='all')
        if family!='all':setattr(active,family,True)
        return evaluate_fixed_native(geo,points,active,gr,flex,plane_order_safe=True)
    baseline=evaluate([list(p) for p in sites],'all');reference=proof['cases']['initial']['families']['all']['baseline']
    if not _close(baseline['target'],reference['target']) or not _vector_agrees(baseline['gradient'],reference['gradient']):
        raise RuntimeError('Qualified initial corrected snapshot differs')
    cases={'full_precision':prior['final_sites_cart'],
        'pdb_rounded':[[float('%.3f'%v) for v in p] for p in prior['final_sites_cart']]}
    refs={}
    for label,points in cases.items():
        if fixed_signature(geo,flex.vec3_double(points))!=original:raise RuntimeError('Endpoint static constraints differ')
        old=prior['endpoint_gradient_audit']['cases'][label]['families']
        for family,row in old.items():
            value=evaluate(points,family);saved=row['baseline']
            if not _close(value['target'],saved['target']) or not _vector_agrees(value['gradient'],saved['gradient']):
                raise RuntimeError('Saved endpoint target or complete family gradient differs')
        refs[label]=old['all']['baseline']
    preflight=calls[0]
    def measure(points,group):
        rows=[]
        for row in group.get('outlier_constraints',[]):
            observed=_observed(row['kind'],[points[i] for i in row['i_seqs']])
            rows.append({'kind':row['kind'],'proxy_index':row['proxy_index'],'atoms':row['atoms'],'observed':observed,
                'target':row['target'],'weight':row['weight'],'nominal_deviation':None if observed is None else (observed-row['target'])*row['weight']**.5,
                'comparison_scope':'DESCRIPTIVE_CAPTURED_SCALAR_NOT_NATIVE_RESIDUAL'})
        return rows
    result.update(audit_base_rotations(evaluate,cases,spec['plan'],references=refs,max_calls=MAX_CALLS-preflight,measure=measure))
    result['audit_evaluation_calls']=result['evaluation_calls'];result['evaluation_calls']=calls[0]
    result['max_evaluation_calls']=MAX_CALLS;result['preflight_evaluations']=preflight
    result['captured_inventory_matches']=True;result['qualified_initial_snapshot_matches']=True
    result['qualified_endpoint_family_snapshots_match']=True;result['normalization']=False
    result['installed_numeric_sources']=numeric;result['installed_adapter_sources']=adapters;result['installed_parallelity_sources']=cpp
    result['constraint_signature_before']=original;result['constraint_signature_after']=fixed_signature(geo,sites)
    if result['constraint_signature_after']!=original:raise RuntimeError('Static constraints changed during rotation audit')
    for row in numeric+adapters:
        if hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Native source changed during audit')
    for row in cpp:
        if hashlib.sha256((source_dir/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Installed plane source changed during audit')
    result['rotation_derivative_qualification']='SAMPLED_ROTATION_DERIVATIVES_PASS' if all(c['sampled_rotation_derivatives_consistent'] for c in result['cases'].values()) else 'DERIVATIVE_REVIEW'
    result['status']='REVIEW'
except Exception as exc:
    result.update(status='FAILED',error=type(exc).__name__+': '+str(exc));traceback.print_exc()
Path('rotation_result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def run_native_base_rotation_audit(model,dictionaries,phils,expected,prior,validated_correction,plan,
        output_parent,executable,*,environment,phenix_version,timeout_seconds=1200):
    """Rebuild the qualified manager and evaluate temporary single-base scans."""
    from .cif_native_validation import _NATIVE_WORKER,_artifact,_stop,NATIVE_POLICY_ID
    from .cif_fixed_geometry import _fixed_policy,_model
    from .cif_corrected_geometry import validate_continuation
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=3600:raise ValueError('Invalid timeout bound')
    if not _fixed_policy(expected) or not phenix_version:raise ValueError('Require explicit captured NA policy')
    validate_continuation(prior,validated_correction['result'],expected['atom_count'])
    if plan!=plan_base_rotations(expected,prior['final_sites_cart']) or not plan['groups']:raise ValueError('Require exact supported graph-selected rotation plan')
    _model(expected,model,coordinates_match=True)
    correction_path=Path(__file__).with_name('cif_parallelity_correction.py')
    if hashlib.sha256(correction_path.read_bytes()).hexdigest()!=validated_correction['correction_core_sha256']:raise ValueError('Qualified correction source changed')
    paths=[Path(p).resolve() for p in [model,*dictionaries,*phils]];parent=Path(output_parent).resolve()
    if not dictionaries or len(paths)!=len(set(paths)) or any(parent==p.parent or p.parent in parent.parents for p in paths):raise ValueError('Require distinct inputs and separate output')
    original=[p.read_bytes() for p in paths];parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='cif-base-rotation-',dir=parent));(work/'inputs').mkdir();frozen=[];inputs=[]
    for i,(path,data) in enumerate(zip(paths,original)):
        role='model' if i==0 else 'dictionary' if i<=len(dictionaries) else 'phil'
        target=work/'inputs'/(f'{i:03d}_{role}'+path.suffix);target.write_bytes(data);frozen.append(target)
        inputs.append({'role':role,'input_index':i,'source_provenance':str(path),**_artifact(target,work)})
    native={'policy_id':NATIVE_POLICY_ID,'model':frozen[0].relative_to(work).as_posix(),
        'dictionaries':[p.relative_to(work).as_posix() for p in frozen[1:1+len(dictionaries)]],
        'phil_files':[p.relative_to(work).as_posix() for p in frozen[1+len(dictionaries):]],
        'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked','policy_inventory':True}
    spec={'policy_id':POLICY_ID,'plan':plan,'correction_core_sha256':validated_correction['correction_core_sha256']}
    values={'native_spec.json':native,'expected_inventory.json':expected,'rotation_spec.json':spec,
        'gradient_validation.json':validated_correction['result'],'endpoint_validation.json':prior}
    for name,value in values.items():(work/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    (work/'native_worker.py').write_text(_NATIVE_WORKER);(work/'rotation_worker.py').write_text(_ROTATION_WORKER)
    for name,source in [('rotation_core.py',Path(__file__)),('correction_core.py',correction_path),
            ('gradient_core.py',Path(__file__).with_name('cif_gradient_audit.py')),
            ('scalar_geometry_core.py',Path(__file__).with_name('cif_captured_geometry.py')),
            ('corrected_geometry_core.py',Path(__file__).with_name('cif_corrected_geometry.py'))]:(work/name).write_bytes(source.read_bytes())
    executable=Path(executable).resolve();command=[str(executable),'rotation_worker.py','rotation_spec.json']
    receipt={'schema_version':1,'audit_kind':'cif_fixed_native_base_rotation_audit','policy_id':POLICY_ID,'status':'FAILED',
        'native_directory':str(work),'inputs':inputs,'command':command,'phenix_version':phenix_version,
        'executable_provenance':str(executable),'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
        'model_optimization':'NOT_RUN','model_editing':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN',
        'execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds}}
    started=time.monotonic()
    try:
        with (work/'rotation.log').open('xb') as log:
            process=subprocess.Popen(command,cwd=work,env=dict(environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:code=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:_stop(process);receipt['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_stop(process);raise
            else:
                receipt['execution'].update(status='COMPLETED' if code==0 else 'FAILED',returncode=code)
                result=json.loads((work/'rotation_result.json').read_text());receipt['result']=result
                if (code==0 and result.get('status')=='REVIEW' and result.get('policy_id')==POLICY_ID
                        and result.get('analysis_completed') and result.get('captured_inventory_matches')
                        and result.get('qualified_initial_snapshot_matches') and result.get('qualified_endpoint_family_snapshots_match')
                        and result.get('model_optimization')=='NOT_RUN' and result.get('model_editing')=='NOT_RUN'
                        and result.get('automatic_adoption') is False and set(result.get('cases',{}))=={'full_precision','pdb_rounded'}
                        and 0<result.get('evaluation_calls',0)<=MAX_CALLS
                        and result.get('constraint_signature_before')==result.get('constraint_signature_after')==prior['constraint_signature_before']):
                    receipt['status']='REVIEW'
                else:receipt['error']=result.get('error','Incomplete fixed-policy rotation evidence')
    except (OSError,ValueError,KeyError,TypeError) as exc:receipt.update(error=str(exc));receipt['execution']['status']='FAILED'
    receipt['source_preserved']=all(p.is_file() and p.read_bytes()==data for p,data in zip(paths,original))
    receipt['frozen_inputs_preserved']=all(p.is_file() and p.read_bytes()==data for p,data in zip(frozen,original))
    if not receipt['source_preserved'] or not receipt['frozen_inputs_preserved']:receipt.update(status='FAILED',error='Original or frozen inputs changed')
    receipt['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
    receipt['outputs']=[_artifact(p,work) for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):receipt.update(status='FAILED',error='Unexpected output symlink')
    (work/'rotation_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return receipt
