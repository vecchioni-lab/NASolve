"""Explicit native plane accumulation correction and fixed-objective audit."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

CORRECTION_POLICY_ID = 'native-parallelity-complete-accumulation-v1'
POLICY_ID = 'cif-fixed-native-corrected-gradient-audit-v1'
MAX_CALLS = 5500


def _norm(values):return math.sqrt(math.fsum(v*v for v in values))
def _close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _vector_agrees(a,b):return len(a)==len(b) and all(_close(x,y) for x,y in zip(a,b))


def _finite(values,count):
    if len(values)!=count or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('Require complete finite Cartesian gradients')


def correct_parallelity_gradient(gr,flex,proxies,points,raw_gradient,*,native_residual):
    """Replace only native plane accumulation; never change energy or proxies.

    This function owns no global monkeypatch. Original per-restraint targets,
    weights and origin IDs are consumed directly. Symmetry-bearing planes need
    an explicit symmetry-aware implementation and are refused here.
    """
    count=len(points);original=list(raw_gradient);_finite(original,3*count)
    if not count or any(len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points):
        raise ValueError('Require complete finite coordinates')
    if not math.isfinite(native_residual):raise ValueError('Require finite native plane residual')
    proxies=[] if proxies is None else proxies
    for p in proxies:
        if getattr(p,'sym_ops',None) is not None and len(p.sym_ops):
            raise ValueError('Symmetry-bearing plane correction is unsupported')
        for indices in [list(p.i_seqs),list(p.j_seqs)]:
            if len(indices)<3 or len(set(indices))!=len(indices) or any(type(i) is not int or not 0<=i<count for i in indices):
                raise ValueError('Require unambiguous plane indices')
        if not math.isfinite(p.weight) or p.weight<=0:raise ValueError('Invalid native plane weight')
        if any(not math.isfinite(getattr(p,key)) for key in ['target_angle_deg','slack','limit']):
            raise ValueError('Invalid native plane parameters')
    manual=[0.]*(3*count);native=manual.copy();residuals=[]
    if len(proxies):
        sites=flex.vec3_double(points)
        for p in proxies:
            restraint=gr.parallelity(sites_cart=sites,proxy=p)
            residual=float(restraint.residual())
            if not math.isfinite(residual):raise ValueError('Nonfinite individual plane residual')
            residuals.append(residual);gradients=list(restraint.gradients());indices=list(p.i_seqs)+list(p.j_seqs)
            if len(gradients)!=len(indices):raise ValueError('Unexpected individual plane gradient count')
            for index,values in zip(indices,gradients):
                values=list(values);_finite(values,3)
                for axis,value in enumerate(values):manual[3*index+axis]+=value
        buffer=flex.vec3_double(count,(0.,0.,0.))
        accumulated=float(gr.parallelity_residual_sum(sites_cart=sites,proxies=proxies,gradient_array=buffer))
        native=[float(v) for v in buffer.as_double()];_finite(native,3*count)
    else:accumulated=0.
    individual=math.fsum(residuals)
    if not (_close(accumulated,native_residual) and _close(individual,accumulated)):
        raise ValueError('Individual/container/manager plane residuals disagree')
    corrected=[math.fsum((a,-b,c)) for a,b,c in zip(original,native,manual)];_finite(corrected,3*count)
    return {'policy_id':CORRECTION_POLICY_ID,'applied':bool(len(proxies)),'proxy_count':len(proxies),
            'gradient':corrected,'plane_gradient':manual,'native_plane_gradient':native,
            'native_plane_residual':accumulated,'individual_plane_residual':individual,'energy_agreement':True,
            'correction_norm':_norm([a-b for a,b in zip(manual,native)])}


def evaluate_fixed_native(geometry,points,active_flags,gr,flex):
    """Opt-in unnormalized native evaluation; the returned energy is untouched."""
    energy=geometry.energies_sites(sites_cart=flex.vec3_double(points),flags=active_flags,compute_gradients=True,normalization=False)
    native=[float(v) for v in energy.gradients.as_double()];_finite(native,3*len(points))
    correction={'policy_id':CORRECTION_POLICY_ID,'applied':False,'correction_norm':0.}
    gradient=native.copy()
    if getattr(active_flags,'parallelity',False):
        correction=correct_parallelity_gradient(gr,flex,geometry.parallelity_proxies,points,native,
                                                native_residual=float(energy.parallelity_residual_sum))
        gradient=correction['gradient'];correction={k:v for k,v in correction.items() if k!='gradient'}
    target=float(energy.target)
    if not math.isfinite(target):raise ValueError('Nonfinite native energy')
    return {'target':target,'native_target':target,'gradient':gradient,'native_gradient_norm':_norm(native),
            'parallelity_correction':correction,
            'terms':{k:float(v) for k,v in vars(energy).items() if k.endswith('_residual_sum') and isinstance(v,(int,float))},
            'proxy_counts':{k:v for k,v in vars(energy).items() if k.startswith('n_') and k.endswith('_proxies') and (v is None or isinstance(v,int))}}


_CORRECTION_WORKER=r'''from __future__ import print_function
import hashlib,importlib,json,sys,traceback
from pathlib import Path
from correction_core import POLICY_ID,CORRECTION_POLICY_ID,evaluate_fixed_native,_norm,_close,_vector_agrees
from gradient_core import audit_gradients,fixed_signature
spec=json.loads(Path(sys.argv[1]).read_text())
result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN'}
try:
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Native inventory bootstrap failed')
    expected=json.loads(Path('expected_inventory.json').read_text());actual=namespace['report']
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):
        raise RuntimeError('Native manager changed before correction audit')
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    modules=[importlib.import_module(name) for name in ['scitbx.lbfgs','cctbx.geometry_restraints.flags','cctbx.geometry_restraints.manager','cctbx.geometry_restraints.energies','scitbx_lbfgs_ext','cctbx_geometry_restraints_ext']]
    def fingerprints(modules):return [{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in modules]
    sources=fingerprints(modules);adapters=fingerprints([gr,flex]);sig=lambda rows:[(r['module'],r['sha256']) for r in rows]
    if sig(sources)!=sig(spec['expected_numeric_sources']):raise RuntimeError('Native numerical sources changed')
    if sig(adapters)!=sig(spec['expected_adapter_sources']):raise RuntimeError('Native adapter sources changed')
    source_dir=Path(modules[2].__file__).resolve().parent;installed=[]
    for row in spec['expected_cpp_sources']:
        if row.get('status')!='RECORDED' or row.get('path') not in {'parallelity.h','parallelity_bpl.cpp'}:raise RuntimeError('Unpinned installed plane source')
        data=(source_dir/row['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=row['sha256']:raise RuntimeError('Installed plane source changed')
        out=Path('installed_source')/row['path'];out.parent.mkdir(exist_ok=True);out.write_bytes(data);installed.append(row)
    geo=namespace['geo'];sites=namespace['sites']
    if len(geo.site_symmetry_table.special_position_indices()):raise RuntimeError('Special-position gradient correction unsupported')
    signature=fixed_signature(geo,sites)
    if signature!=spec['expected_constraint_signature']:raise RuntimeError('Static native constraints differ')
    checks={}
    for label,points in spec['coordinate_cases'].items():
        active=flags.flags(default=True);raw=geo.energies_sites(sites_cart=flex.vec3_double(points),flags=active,compute_gradients=True,normalization=False)
        reference=spec['raw_references'][label];norm=_norm([float(v) for v in raw.gradients.as_double()])
        if not (_close(float(raw.target),reference['target']) and _close(norm,reference['gradient_norm'])):
            raise RuntimeError('Captured native full-objective baseline differs')
        checks[label]={'target':float(raw.target),'native_gradient_norm':norm,'captured_raw_baseline_match':True}
        if label in spec['captured_plane_gradients']:
            active=flags.flags(default=False);active.parallelity=True
            corrected=evaluate_fixed_native(geo,points,active,gr,flex);capture=spec['captured_plane_gradients'][label]
            detail=corrected['parallelity_correction']
            if not (_close(corrected['target'],capture['accumulated_residual'])
                    and _vector_agrees(detail['native_plane_gradient'],capture['accumulated_gradient'])
                    and _vector_agrees(detail['plane_gradient'],capture['manual_gradient'])):
                raise RuntimeError('Saved individual/container plane gradients differ')
            checks[label]['captured_complete_plane_gradient_match']=True
    stats={'correction_evaluations':0,'max_energy_change':0.,'max_plane_residual_difference':0.}
    def evaluate(points,family):
        active=flags.flags(default=family=='all')
        if family!='all':setattr(active,family,True)
        value=evaluate_fixed_native(geo,points,active,gr,flex);change=abs(value['target']-value['native_target'])
        stats['max_energy_change']=max(stats['max_energy_change'],change)
        if change:raise RuntimeError('Correction changed native energy')
        detail=value['parallelity_correction']
        if detail['applied']:
            stats['correction_evaluations']+=1
            stats['max_plane_residual_difference']=max(stats['max_plane_residual_difference'],abs(detail['native_plane_residual']-detail['individual_plane_residual']))
        return value
    references={label:{'target':value['target']} for label,value in spec['raw_references'].items()}
    result.update(audit_gradients(evaluate,spec['coordinate_cases'],spec['selected_indices'],references=references,max_calls=spec['max_calls']))
    result.update(policy_id=POLICY_ID,correction_policy_id=CORRECTION_POLICY_ID,captured_inventory_matches=True,
                  raw_baseline_checks=checks,correction_statistics=stats,installed_numeric_sources=sources,installed_adapter_sources=adapters,
                  installed_parallelity_sources=installed,constraint_signature_before=signature,constraint_signature_after=fixed_signature(geo,sites),
                  preflight_native_evaluations=len(checks)+len(spec['captured_plane_gradients']))
    if result['constraint_signature_after']!=signature:raise RuntimeError('Static native constraints changed')
    for row in sources+adapters:
        if hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Native numerical/adapter source changed')
    for row in installed:
        if hashlib.sha256((source_dir/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Installed plane source changed during audit')
    result['correction_qualification']='SAMPLED_NATIVE_DERIVATIVES_PASS' if all(c['sampled_gradients_consistent'] for c in result['cases'].values()) else 'DERIVATIVE_REVIEW'
    result['normalization']=False;result['status']='REVIEW'
except Exception as exc:
    result.update(status='FAILED',error=type(exc).__name__+': '+str(exc));traceback.print_exc()
Path('correction_result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def run_native_correction_audit(model,dictionaries,phils,expected,coordinate_cases,raw_references,captured_plane_gradients,
        selected_indices,expected_numeric_sources,expected_adapter_sources,expected_cpp_sources,expected_constraint_signature,
        output_parent,executable,*,environment,phenix_version,timeout_seconds=1200):
    """Run the opt-in correction in an owned, source-pinned native audit job."""
    from .cif_native_validation import _NATIVE_WORKER,_artifact,_stop,NATIVE_POLICY_ID
    from .cif_fixed_geometry import _model,_fixed_policy,_points
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=3600:raise ValueError('Invalid native timeout')
    if not _fixed_policy(expected) or not phenix_version:raise ValueError('Require captured explicit policy and native version')
    _model(expected,model,coordinates_match=True)
    if set(coordinate_cases)!={'initial','full_precision','pdb_rounded'} or set(raw_references)!=set(coordinate_cases):
        raise ValueError('Require initial and both saved coordinate/reference cases')
    for points in coordinate_cases.values():_points(points,expected['atom_count'])
    paths=[Path(p).resolve() for p in [model,*dictionaries,*phils]];parent=Path(output_parent).resolve()
    if not dictionaries or len(paths)!=len(set(paths)) or any(parent==p.parent or p.parent in parent.parents for p in paths):
        raise ValueError('Require distinct inputs and separate output')
    original=[p.read_bytes() for p in paths];parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='cif-corrected-gradient-',dir=parent));(work/'inputs').mkdir();frozen=[];inputs=[]
    for i,(path,data) in enumerate(zip(paths,original)):
        role='model' if i==0 else 'dictionary' if i<=len(dictionaries) else 'phil'
        target=work/'inputs'/(f'{i:03d}_{role}'+path.suffix);target.write_bytes(data);frozen.append(target)
        inputs.append({'role':role,'input_index':i,'source_provenance':str(path),**_artifact(target,work)})
    native={'policy_id':NATIVE_POLICY_ID,'model':frozen[0].relative_to(work).as_posix(),
            'dictionaries':[p.relative_to(work).as_posix() for p in frozen[1:1+len(dictionaries)]],
            'phil_files':[p.relative_to(work).as_posix() for p in frozen[1+len(dictionaries):]],
            'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked','policy_inventory':True}
    spec={'policy_id':POLICY_ID,'coordinate_cases':coordinate_cases,'raw_references':raw_references,
          'captured_plane_gradients':captured_plane_gradients,'selected_indices':selected_indices,
          'expected_numeric_sources':expected_numeric_sources,'expected_adapter_sources':expected_adapter_sources,
          'expected_cpp_sources':expected_cpp_sources,'expected_constraint_signature':expected_constraint_signature,'max_calls':MAX_CALLS}
    for name,value in [('native_spec.json',native),('expected_inventory.json',expected),('correction_spec.json',spec)]:
        (work/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    (work/'native_worker.py').write_text(_NATIVE_WORKER);(work/'correction_worker.py').write_text(_CORRECTION_WORKER)
    (work/'correction_core.py').write_bytes(Path(__file__).read_bytes())
    (work/'gradient_core.py').write_bytes(Path(__file__).with_name('cif_gradient_audit.py').read_bytes())
    executable=Path(executable).resolve();command=[str(executable),'-B','correction_worker.py','correction_spec.json']
    receipt={'schema_version':1,'audit_kind':'cif_native_parallelity_corrected_gradient_audit','policy_id':POLICY_ID,'status':'FAILED',
             'native_directory':str(work),'inputs':inputs,'command':command,'phenix_version':phenix_version,
             'executable_provenance':str(executable),'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
             'model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN','execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds}}
    started=time.monotonic()
    try:
        with (work/'correction.log').open('xb') as log:
            process=subprocess.Popen(command,cwd=work,env=dict(environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:code=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:_stop(process);receipt['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_stop(process);raise
            else:
                receipt['execution'].update(status='COMPLETED' if code==0 else 'FAILED',returncode=code)
                result=json.loads((work/'correction_result.json').read_text());receipt['result']=result
                if (code==0 and result.get('status')=='REVIEW' and result.get('policy_id')==POLICY_ID and result.get('analysis_completed')
                        and result.get('captured_inventory_matches') and result.get('correction_policy_id')==CORRECTION_POLICY_ID
                        and result.get('model_optimization')=='NOT_RUN' and result.get('automatic_adoption') is False
                        and set(result.get('cases',{}))==set(coordinate_cases) and 0<result.get('evaluation_calls',0)<=MAX_CALLS
                        and result.get('constraint_signature_before')==result.get('constraint_signature_after')==expected_constraint_signature
                        and result.get('correction_statistics',{}).get('max_energy_change')==0.):receipt['status']='REVIEW'
                else:receipt['error']=result.get('error','Incomplete corrected-gradient evidence')
    except (OSError,ValueError,KeyError,TypeError) as exc:receipt.update(error=str(exc));receipt['execution']['status']='FAILED'
    receipt['source_preserved']=all(p.is_file() and p.read_bytes()==data for p,data in zip(paths,original))
    receipt['frozen_inputs_preserved']=all(p.is_file() and p.read_bytes()==data for p,data in zip(frozen,original))
    if not receipt['source_preserved'] or not receipt['frozen_inputs_preserved']:receipt.update(status='FAILED',error='Original or frozen inputs changed')
    receipt['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
    receipt['outputs']=[_artifact(p,work) for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):receipt.update(status='FAILED',error='Unexpected output symlink')
    (work/'correction_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return receipt
