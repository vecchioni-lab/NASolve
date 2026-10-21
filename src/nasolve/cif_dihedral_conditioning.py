"""Read-only numerical conditioning of graph-selected native dihedrals.

No restraint is removed, weakened, regenerated or adopted. Temporary coordinate
perturbations are evaluations, never output models or optimization steps.
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

POLICY_ID='cif-native-linear-axis-dihedral-conditioning-v1'
STEPS=(1e-3,1e-4,1e-5,1e-6,1e-7,1e-8)
NEAR_LINEAR_SINE=1e-3  # Descriptive screen only; not a chemical acceptance bound.


def _norm(v):return math.sqrt(math.fsum(x*x for x in v))
def _close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _safe_json(v):
    if type(v) is float and not math.isfinite(v):return {'nonfinite_native_float':str(v)}
    if isinstance(v,dict):return {k:_safe_json(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [_safe_json(x) for x in v]
    return v


def dihedral_geometry(points):
    """Record the two plane-normal sines without inventing a torsion at zero."""
    sines=[];normals=[]
    for a,b,c in [points[:3],points[1:]]:
        u=[x-y for x,y in zip(a,b)];v=[x-y for x,y in zip(c,b)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        denominator=_norm(u)*_norm(v);normal=_norm(cross)
        normals.append(normal);sines.append(normal/denominator if denominator else 0.)
    minimum=min(sines)
    return {'plane_normal_sines':sines,'plane_normal_norms_angstrom2':normals,'minimum_sine':minimum,
        'inverse_minimum_sine':1/minimum if minimum else None,'geometry_defined':minimum>0,
        'near_collinear_review':minimum<NEAR_LINEAR_SINE,'near_collinear_sine_screen':NEAR_LINEAR_SINE}


def _validate(cases,proxies):
    if not 1<=len(cases)<=3 or not 1<=len(proxies)<=12:raise ValueError('Require bounded coordinate cases and explicit proxies')
    count=len(next(iter(cases.values())))
    for points in cases.values():
        if len(points)!=count or not points or any(len(p)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in p) for p in points):raise ValueError('Require complete finite coordinates')
    for p in proxies:
        ids=p['i_seqs'];alt=p.get('alt_angle_ideals')
        if (len(ids)!=4 or len(set(ids))!=4 or any(type(i) is not int or not 0<=i<count for i in ids)
                or type(p['periodicity']) is not int or type(p['weight']) not in (int,float) or not math.isfinite(p['weight']) or p['weight']<=0
                or type(p['angle_ideal']) not in (int,float) or not math.isfinite(p['angle_ideal'])
                or alt is not None and (not isinstance(alt,list) or len(alt)>6 or any(type(x) not in (int,float) or not math.isfinite(x) for x in alt))):
            raise ValueError('Unsupported dihedral proxy or selection')


def audit_dihedral_conditioning(evaluate,coordinate_cases,proxies,*,max_pairs=3000):
    """Compare original single/container kernels with central differences.

    The callback receives four local points and original parameter values. Each
    call is two native kernels. Undefined/nonfinite responses remain evidence;
    no finite zero gradient can establish a derivative at collinearity.
    """
    _validate(coordinate_cases,proxies)
    if type(max_pairs) is not int or not 1<=max_pairs<=6000:raise ValueError('Invalid evaluation budget')
    result={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','analysis_completed':False,
        'model_optimization':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'restraint_changes':'NONE','coordinate_model_written':False,'step_sizes_angstrom':list(STEPS),
        'directional_tolerance':{'absolute':1e-4,'relative':1e-4},'evaluation_pairs':0,'max_evaluation_pairs':max_pairs,
        'native_kernels_per_pair':2,'cases':{},'numerical_controls':{},'approach_to_collinearity':[],
        'limitations':['Near-collinearity is a descriptive screen, not a restraint-removal or chemical policy.',
            'Sampled derivative agreement does not establish conditioning, chemistry, convergence or historical causation.',
            'Only selected existing heavy-atom proxies are evaluated; dictionary hydrogen torsions are retained separately.']}
    def call(points,proxy):
        if result['evaluation_pairs']>=max_pairs:raise ValueError('Native evaluation budget exhausted')
        result['evaluation_pairs']+=1;x,p=deepcopy(points),deepcopy(proxy)
        try:raw=evaluate(x,p)
        except Exception as exc:
            if x!=points or p!=proxy:raise ValueError('Evaluation callback mutated inputs')
            return {'status':'EXCEPTION','exception_type':type(exc).__name__,'message':str(exc)}
        if x!=points or p!=proxy:raise ValueError('Evaluation callback mutated inputs')
        try:
            targets=[raw[k] for k in ['single_target','accumulated_target']]
            vectors=[raw[k] for k in ['single_gradient','accumulated_gradient']]
            valid=all(type(v) in (int,float) and math.isfinite(v) for v in targets)
            valid &= all(len(v)==12 and all(type(n) in (int,float) and math.isfinite(n) for n in v) for v in vectors)
            if valid:
                return {'status':'FINITE',**raw,**{k+'_gradient_norm':_norm(raw[k+'_gradient']) for k in ['single','accumulated']}}
            return {'status':'NONFINITE_OR_INVALID',**_safe_json(raw)}
        except (KeyError,TypeError,ValueError) as exc:return {'status':'INVALID_RESULT','message':str(exc)}
    def agrees(a,b):
        return a.get('status')==b.get('status')=='FINITE' and all(_close(a[k+'_target'],b[k+'_target']) and all(_close(x,y) for x,y in zip(a[k+'_gradient'],b[k+'_gradient'])) for k in ['single','accumulated'])
    def probe(points,proxy):
        geometry=dihedral_geometry(points);baseline=call(points,proxy)
        row={'geometry':geometry,'baseline':baseline,'directions':[],'sampled_derivatives_consistent':False}
        finite=baseline['status']=='FINITE';defined=geometry['geometry_defined'] and baseline.get('native_angle_defined') is True
        if finite and defined:
            directions=[('atom_'+str(i//3)+'_axis_'+str(i%3),[1. if j==i else 0. for j in range(12)]) for i in range(12)]
            length=baseline['single_gradient_norm']
            if length:directions.append(('single_gradient',[v/length for v in baseline['single_gradient']]))
            for name,direction in directions:
                analytic={k:math.fsum(x*y for x,y in zip(direction,baseline[k+'_gradient'])) for k in ['single','accumulated']};samples=[]
                for h in STEPS:
                    shifted=lambda sign:[[v+sign*h*direction[3*i+j] for j,v in enumerate(p)] for i,p in enumerate(points)]
                    plus,minus=call(shifted(1),proxy),call(shifted(-1),proxy);sample={'step':h,'plus':{k:v for k,v in plus.items() if 'gradient' not in k},'minus':{k:v for k,v in minus.items() if 'gradient' not in k}}
                    for kind in ['single','accumulated']:
                        okay=plus['status']==minus['status']=='FINITE' and plus.get('native_angle_defined') is True and minus.get('native_angle_defined') is True
                        if okay:
                            value=(plus[kind+'_target']-minus[kind+'_target'])/(2*h);error=abs(value-analytic[kind]);bound=1e-4+1e-4*max(abs(value),abs(analytic[kind]))
                            sample[kind]={'numerical':value,'absolute_error':error,'bound':bound,'consistent':error<=bound}
                        else:sample[kind]={'consistent':False,'reason':'NONFINITE_EXCEPTIONAL_OR_UNDEFINED_SAMPLE'}
                    samples.append(sample)
                row['directions'].append({'direction':name,'analytical':analytic,'samples':samples,
                    **{k+'_consistent':any(samples[i][k]['consistent'] and samples[i+1][k]['consistent'] for i in range(len(samples)-1)) for k in ['single','accumulated']}})
            row['sampled_derivatives_consistent']=all(v[k+'_consistent'] for v in row['directions'] for k in ['single','accumulated'])
        repeat=call(points,proxy);row['repeat']=repeat;row['baseline_repeats_consistent']=agrees(baseline,repeat)
        reverse=call(points[::-1],proxy);row['reversed_order_baseline']=reverse
        row['reversed_order_consistent']=(finite and reverse['status']=='FINITE' and all(_close(baseline[k+'_target'],reverse[k+'_target']) and all(_close(a,b) for a,b in zip(baseline[k+'_gradient'],[v for p in [reverse[k+'_gradient'][i:i+3] for i in range(0,12,3)][::-1] for v in p])) for k in ['single','accumulated']))
        row['single_and_container_agree']=(finite and _close(baseline['single_target'],baseline['accumulated_target']) and all(_close(a,b) for a,b in zip(baseline['single_gradient'],baseline['accumulated_gradient'])))
        row['qualification']=('UNDEFINED_GEOMETRY' if not geometry['geometry_defined'] else 'NATIVE_NONFINITE_REVIEW' if not finite else 'NATIVE_UNDEFINED_REVIEW' if not defined else 'NEAR_COLLINEAR_REVIEW' if geometry['near_collinear_review'] else 'SAMPLED_DERIVATIVES_PASS' if row['sampled_derivatives_consistent'] and row['baseline_repeats_consistent'] and row['single_and_container_agree'] and row['reversed_order_consistent'] else 'DERIVATIVE_REVIEW')
        return row
    for label,points in coordinate_cases.items():
        rows=[{'proxy':deepcopy(p),**probe([points[i] for i in p['i_seqs']],p)} for p in proxies]
        result['cases'][label]={'proxies':rows,'summary':{'proxy_count':len(rows),
            'sampled_derivatives_consistent':all(r['sampled_derivatives_consistent'] for r in rows),
            'baseline_repeats_consistent':all(r['baseline_repeats_consistent'] for r in rows),
            'single_and_container_agree':all(r['single_and_container_agree'] for r in rows),
            'near_collinear_proxies':sum(r['geometry']['near_collinear_review'] for r in rows),
            'undefined_proxies':sum(not r['geometry']['geometry_defined'] for r in rows)}}
    parameter=proxies[0]
    for label,points in {'well_conditioned':[[0.,1.,.2],[0.,0.,0.],[1.3,0.,0.],[1.6,.8,1.1]],
                         'exact_collinear':[[-1.,0.,0.],[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]]}.items():
        result['numerical_controls'][label]={'scope':'NONCHEMICAL_NUMERICAL_CONTROL',**probe(points,parameter)}
    for radius in [1e-2,1e-4,1e-6,1e-8,0.]:
        for phase in [0.,90.]:
            angle=math.radians(phase);points=[[-1.,radius,0.],[0.,0.,0.],[1.,0.,0.],[2.,radius*math.cos(angle),radius*math.sin(angle)]]
            result['approach_to_collinearity'].append({'radius_angstrom':radius,'phase_degrees':phase,'scope':'NONCHEMICAL_NUMERICAL_CONTROL','geometry':dihedral_geometry(points),'evaluation':call(points,parameter)})
    result['analysis_completed']=True
    return result


def native_evaluator(gr,flex):
    def evaluate(points,row):
        proxy=gr.dihedral_proxy(i_seqs=[0,1,2,3],angle_ideal=row['angle_ideal'],weight=row['weight'],
            periodicity=row['periodicity'],alt_angle_ideals=row.get('alt_angle_ideals'),origin_id=row.get('origin_id',0))
        sites=flex.vec3_double(points);r=gr.dihedral(sites_cart=sites,proxy=proxy)
        proxies=gr.shared_dihedral_proxy();proxies.append(proxy);gradient=flex.vec3_double(4,(0.,0.,0.))
        target=gr.dihedral_residual_sum(sites_cart=sites,proxies=proxies,gradient_array=gradient)
        return {'single_target':float(r.residual()),'single_gradient':[float(x) for p in r.gradients() for x in p],
            'accumulated_target':float(target),'accumulated_gradient':[float(x) for x in gradient.as_double()],
            'native_angle_defined':bool(r.have_angle_model),'native_angle_degrees':float(r.angle_model) if r.have_angle_model else None}
    return evaluate


_WORKER=r'''from pathlib import Path
import hashlib,importlib,json,sys,traceback
from conditioning_core import POLICY_ID,audit_dihedral_conditioning,native_evaluator
from gradient_core import fixed_signature
spec=json.loads(Path(sys.argv[1]).read_text());root=Path(spec['installation_root']).resolve(strict=True)
result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN'}
try:
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Native inventory bootstrap failed')
    expected=json.loads(Path('expected_inventory.json').read_text());actual=namespace['report']
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):
        raise RuntimeError('Native manager changed before torsion audit')
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    modules=[importlib.import_module(r['module']) for r in spec['expected_numeric_sources']]
    sources=[{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in modules]
    if [(r['module'],r['sha256']) for r in sources]!=[(r['module'],r['sha256']) for r in spec['expected_numeric_sources']]:raise RuntimeError('Native numerical sources changed')
    adapter=[{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in [gr,flex]]
    if any(not Path(row['historical_path']).is_relative_to(root) for row in sources+adapter):raise RuntimeError('Unselected numerical module')
    geo=namespace['geo'];sites=namespace['sites']
    if len(geo.site_symmetry_table.special_position_indices()):raise RuntimeError('Special-position torsions unsupported')
    original=fixed_signature(geo,sites);selected=[];parameters=[]
    def record(p):
        alt=getattr(p,'alt_angle_ideals',None)
        return {'i_seqs':list(p.i_seqs),'angle_ideal':float(p.angle_ideal),'weight':float(p.weight),'periodicity':int(p.periodicity),
            'alt_angle_ideals':None if alt is None else [float(v) for v in alt],'origin_id':int(p.origin_id)}
    for row in spec['proxies']:
        matches=[p for p in geo.dihedral_proxies if record(p)==row]
        if len(matches)!=1:raise RuntimeError('Selected native torsion membership changed')
        p=matches[0]
        if (p.sym_ops is not None and len(p.sym_ops)) or p.limit!=-1 or p.top_out is not False or p.slack!=0:
            raise RuntimeError('Unsupported nondefault torsion function or symmetry')
        selected.append(record(p));parameters.append({**record(p),'limit':float(p.limit),'top_out':bool(p.top_out),'slack':float(p.slack),'symmetry':'NONE'})
    installed=[];source_dir=Path(gr.__file__).resolve().parent
    for name in ['dihedral.h','dihedral_bpl.cpp']:
        path=source_dir/name;row={'anchor':'native_geometry_module','path':name,'status':'UNAVAILABLE'}
        if path.is_file():
            data=path.read_bytes();output=Path('installed_source')/name;output.parent.mkdir(exist_ok=True);output.write_bytes(data)
            row.update(status='RECORDED',sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
        installed.append(row)
    result.update(audit_dihedral_conditioning(native_evaluator(gr,flex),spec['coordinate_cases'],selected,max_pairs=3000))
    result.update(captured_inventory_matches=True,installed_numeric_sources=sources,installed_adapter_sources=adapter,
        installed_dihedral_sources=installed,selected_native_parameters=parameters,
        constraint_signature_before=original,constraint_signature_after=fixed_signature(geo,sites))
    if result['constraint_signature_after']!=original:raise RuntimeError('Native constraints changed during torsion audit')
    for row in sources+adapter:
        if hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Native numerical source changed during audit')
    for row in installed:
        if row['status']=='RECORDED' and hashlib.sha256((source_dir/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Installed source changed')
    result['status']='REVIEW'
except Exception as exc:
    result.update(status='FAILED',error=type(exc).__name__+': '+str(exc));traceback.print_exc()
Path('conditioning_result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def run_native_dihedral_conditioning(model,dictionary,phils,expected,coordinate_cases,proxies,numeric_sources,
        output_parent,executable,*,environment,phenix_version,installation_root,timeout_seconds=180):
    """Rebuild the captured isolated manager before temporary kernel evaluations."""
    from .cif_native_validation import _NATIVE_WORKER,_artifact,_stop,NATIVE_POLICY_ID
    from .cif_fixed_geometry import _model,_fixed_policy
    from . import cif_gradient_audit
    _validate(coordinate_cases,proxies)
    if not _fixed_policy(expected) or not phenix_version or type(timeout_seconds) is not int or not 1<=timeout_seconds<=180:raise ValueError('Require explicit captured policy and bounded native execution')
    if any(len(points)!=expected['atom_count'] for points in coordinate_cases.values()):raise ValueError('Native coordinate count differs')
    if len(numeric_sources)!=6 or len({r['module'] for r in numeric_sources})!=6:raise ValueError('Require all six pinned numerical source identities')
    root=Path(installation_root).resolve(strict=True);executable=Path(executable).resolve(strict=True)
    if not executable.is_relative_to(root):raise ValueError('Require selected Phenix interpreter')
    dispatcher=executable.read_bytes();paths=[Path(p).resolve(strict=True) for p in [model,dictionary,*phils]];parent=Path(output_parent).resolve()
    if len(paths)!=len(set(paths)) or any(parent==p.parent or p.parent in parent.parents for p in paths):raise ValueError('Require separate native output and explicit distinct inputs')
    _model(expected,paths[0],coordinates_match=True);original=[p.read_bytes() for p in paths]
    parent.mkdir(parents=True,exist_ok=True);work=Path(tempfile.mkdtemp(prefix='cif-dihedral-conditioning-',dir=parent));(work/'inputs').mkdir()
    frozen=[];inputs=[]
    for i,(path,data) in enumerate(zip(paths,original)):
        role='model' if i==0 else 'dictionary' if i==1 else 'phil';target=work/'inputs'/(f'{i:03d}_'+role+path.suffix);target.write_bytes(data)
        frozen.append(target);inputs.append({'role':role,'source_provenance':str(path),**_artifact(target,work)})
    native={'policy_id':NATIVE_POLICY_ID,'model':frozen[0].relative_to(work).as_posix(),'dictionaries':[frozen[1].relative_to(work).as_posix()],
        'phil_files':[p.relative_to(work).as_posix() for p in frozen[2:]],'phil_namespace_policy':'direct','inventory_detail':'linked','policy_inventory':True}
    spec={'installation_root':str(root),'coordinate_cases':coordinate_cases,'proxies':proxies,'expected_numeric_sources':numeric_sources}
    for name,value in [('native_spec.json',native),('expected_inventory.json',expected),('conditioning_spec.json',spec)]:
        (work/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    (work/'native_worker.py').write_text(_NATIVE_WORKER);(work/'conditioning_worker.py').write_text(_WORKER)
    (work/'conditioning_core.py').write_bytes(Path(__file__).read_bytes());(work/'gradient_core.py').write_bytes(Path(cif_gradient_audit.__file__).read_bytes())
    receipt={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','native_directory':str(work),'inputs':inputs,
        'phenix_version':phenix_version,'executable_sha256':hashlib.sha256(dispatcher).hexdigest(),'execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds},
        'model_optimization':'NOT_RUN','readyset':'NOT_RUN','dictionary_generation':'NOT_RUN','restraint_changes':'NONE','scientific_approval':'NOT_RUN','automatic_adoption':False}
    started=time.monotonic()
    try:
        with (work/'conditioning.log').open('xb') as log:
            process=subprocess.Popen([str(executable),'-B','conditioning_worker.py','conditioning_spec.json'],cwd=work,env={**environment,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:rc=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:_stop(process);receipt['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_stop(process);raise
            else:
                receipt['execution'].update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc)
                result=json.loads((work/'conditioning_result.json').read_text());receipt['result']=result
                if (rc==0 and result.get('policy_id')==POLICY_ID and result.get('status')=='REVIEW'
                        and result.get('analysis_completed') and result.get('captured_inventory_matches')
                        and result.get('model_optimization')=='NOT_RUN' and result.get('automatic_adoption') is False
                        and set(result.get('cases',{}))==set(coordinate_cases) and 0<result.get('evaluation_pairs',0)<=3000
                        and result.get('constraint_signature_before')==result.get('constraint_signature_after')):receipt['status']='REVIEW'
                else:receipt['error']=result.get('error','Incomplete dihedral conditioning evidence')
    except (OSError,ValueError,KeyError,TypeError) as exc:receipt['error']=str(exc);receipt['execution']['status']='FAILED'
    receipt['source_preserved']=all(p.is_file() and p.read_bytes()==data for p,data in zip(paths,original)) and executable.read_bytes()==dispatcher
    receipt['frozen_inputs_preserved']=all(p.is_file() and p.read_bytes()==data for p,data in zip(frozen,original))
    if not receipt['source_preserved'] or not receipt['frozen_inputs_preserved']:receipt.update(status='FAILED',error='Original or frozen inputs changed')
    receipt['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
    receipt['outputs']=[_artifact(p,work) for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):receipt.update(status='FAILED',error='Unexpected native output symlink')
    (work/'conditioning_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return receipt
