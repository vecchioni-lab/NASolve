"""One optional geometry trial under a freshly qualified mixed native objective.

The geometry worker, optimizer, evaluator and serializer are unchanged. A local
precondition adapter binds the genuine initial-only proof instead of borrowing
historical endpoints from a different manager.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

POLICY_ID='cif-mixed-qualified-geometry-trial-v1'
PRECONDITION_ID='cif-mixed-initial-geometry-precondition-v1'
REPORT='mixed_geometry_trial.json'
ANCHOR='mixed_geometry_directory'
_PACKAGE=('cif_mixed_geometry.py','cif_mixed_gradient.py','cif_gradient_audit.py',
    'cif_parallelity_correction.py','cif_parallelity_audit.py','cif_corrected_geometry.py')
_FIELDS=('selected_indices','constraint_signature_before','constraint_signature_after',
    'installed_numeric_sources','installed_adapter_sources','installed_parallelity_sources','correction_policy_id')


def _need(value):
    if not value:raise ValueError('Mixed geometry evidence does not reproduce')


def _digest(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def _close(a,b):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _dump(path,value):path.write_text(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
def _load(path):
    from .cif_review_transport import _parse_json
    return _parse_json(Path(path).read_bytes())


def _ref(path,root,anchor=ANCHOR):
    from .cif_mixed_recovery import _safe
    path,root=Path(path),Path(root)
    _need(not any(p.is_symlink() for p in [path,*path.parents]))
    name=path.relative_to(root).as_posix();_need(_safe(name));data=path.read_bytes()
    return {'anchor':anchor,'path':name,'sha256':sha256(data).hexdigest(),'size':len(data)}


def _resolve(root,gradient,context,parent,ref):
    from .cif_mixed_recovery import _safe
    anchors={ANCHOR:Path(root),'gradient_directory':Path(gradient),'context_directory':Path(context),'linked_parent_directory':Path(parent)}
    _need(isinstance(ref,dict) and ref.get('anchor') in anchors and _safe(ref.get('path')))
    directory=anchors[ref['anchor']];path=directory/ref['path'];_need(_ref(path,directory,ref['anchor'])==ref);return path


def _inputs(gradient,context,parent):
    from .cif_mixed_gradient import read_mixed_initial_gradients,_inputs as native_inputs
    gradient,context,parent=map(Path,(gradient,context,parent))
    source=read_mixed_initial_gradients(gradient,context_directory=context,linked_parent_directory=parent)
    _need(source['status']=='MIXED_INITIAL_DERIVATIVES_PASS' and source['new_native_calls']==1)
    _,model,cifs,phils,expected,bindings=native_inputs(context,parent)
    proof=_load(gradient/'job/gradient_result.json')
    bindings={**bindings,'gradient_report':_ref(gradient/'mixed_initial_gradients.json',gradient,'gradient_directory'),
        'gradient_result':_ref(gradient/'job/gradient_result.json',gradient,'gradient_directory')}
    return source,model,cifs,phils,expected,proof,bindings


def _wrapper(proof,expected,proof_bytes,parent_archive_sha256):
    """Project only worker-required fields from a genuine current initial proof."""
    from .cif_mixed_gradient import _validate_result,_manager_digest,_NUMERIC,_ADAPTERS
    from .cif_corrected_geometry import QUALIFIED_CORRECTION_SHA256
    _need(_digest(parent_archive_sha256) and proof['status']=='REVIEW' and proof['scientific_qualification']=='NOT_ASSESSED'
        and proof['manager_sha256']==_manager_digest(expected) and proof['coordinates_unchanged'] is True
        and proof['special_position_indices']==[] and proof['correction_core_sha256']==QUALIFIED_CORRECTION_SHA256)
    qualification=_validate_result(proof,expected,proof['selected_indices']);_need(qualification['sampled_derivatives_pass'] is True)
    pins={}
    for field,names in [('installed_numeric_sources',_NUMERIC),('installed_adapter_sources',_ADAPTERS)]:
        rows=proof[field];_need([r['module'] for r in rows]==list(names) and proof[field+'_after']==rows)
        _need(all(_digest(r['sha256']) and isinstance(r['historical_path'],str) and r['historical_path'] for r in rows))
        pins.update({r['module']:r['sha256'] for r in rows})
    _need(all(pins.get(r['module'])==r['sha256'] for r in expected['energy_inventory']['installed_sources']))
    _need({r['path'] for r in proof['installed_parallelity_sources']}=={'parallelity.h','parallelity_bpl.cpp'}
        and all(r['status']=='RECORDED' and type(r['bytes']) is int and r['bytes']>0 and _digest(r['sha256']) for r in proof['installed_parallelity_sources']))
    return {'schema_version':1,'policy_id':PRECONDITION_ID,'source_policy_id':proof['policy_id'],
        'source_result_sha256':sha256(proof_bytes).hexdigest(),'source_result_size':len(proof_bytes),
        'parent_archive_sha256':parent_archive_sha256,'expected_manager_sha256':_manager_digest(expected),
        'correction_core_sha256':QUALIFIED_CORRECTION_SHA256,'cases':deepcopy(proof['gradient_audit']['cases']),
        **{k:deepcopy(proof[k]) for k in _FIELDS},'model_optimization':'NOT_RUN','automatic_adoption':False}


_ADAPTER='''"""Trusted current initial-only precondition adapter; no historical-case claim."""
import json
from pathlib import Path
from nasolve.cif_mixed_geometry import _wrapper,_need

def validate_gradient_qualification(wrapper,atom_count):
    data=Path("mixed_initial_result.json").read_bytes()
    raw=json.loads(data);expected=json.loads(Path("expected_inventory.json").read_bytes())
    _need(expected["atom_count"]==atom_count)
    _need(wrapper==_wrapper(raw,expected,data,wrapper["parent_archive_sha256"]))
    return True
'''


def _prepare(root,model,cifs,phils,expected,proof,proof_bytes,parent_archive_sha256,max_iterations):
    from .cif_fixed_geometry import _GEOMETRY_WORKER
    from .cif_native_validation import _NATIVE_WORKER,NATIVE_POLICY_ID
    from .cif_corrected_geometry import QUALIFIED_CORRECTION_SHA256
    _need(sha256(Path(__file__).with_name('cif_parallelity_correction.py').read_bytes()).hexdigest()==QUALIFIED_CORRECTION_SHA256)
    wrapper=_wrapper(proof,expected,proof_bytes,parent_archive_sha256)
    work=root/'job';(work/'inputs').mkdir(parents=True);inputs=[]
    for i,path in enumerate([model,*cifs,*phils]):
        role='model' if i==0 else 'dictionary' if i<=len(cifs) else 'phil';out=work/'inputs'/f'{i:03d}_{role}{path.suffix}'
        out.write_bytes(path.read_bytes());inputs.append({'input_index':i,'role':role,'artifact':_ref(out,root)})
    native={'policy_id':NATIVE_POLICY_ID,'model':inputs[0]['artifact']['path'].removeprefix('job/'),
        'dictionaries':[r['artifact']['path'].removeprefix('job/') for r in inputs if r['role']=='dictionary'],
        'phil_files':[r['artifact']['path'].removeprefix('job/') for r in inputs if r['role']=='phil'],
        'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked','policy_inventory':True}
    trial={'policy_id':POLICY_ID,'native_spec':'native_spec.json','expected_inventory':'expected_inventory.json',
        'max_iterations':max_iterations,'max_calls':max_iterations*20,'gradient_epsilon':1e-5,'policy_inventory':True,
        'validated_correction':{'archive_sha256':parent_archive_sha256,'correction_core_sha256':QUALIFIED_CORRECTION_SHA256}}
    for name,value in [('native_spec.json',native),('geometry_spec.json',trial),('expected_inventory.json',expected),('gradient_validation.json',wrapper)]:_dump(work/name,value)
    (work/'mixed_initial_result.json').write_bytes(proof_bytes)
    for name,data in [('geometry_worker.py',_GEOMETRY_WORKER.encode()),('native_worker.py',_NATIVE_WORKER.encode()),
        ('corrected_geometry_core.py',_ADAPTER.encode()),('nasolve/__init__.py',b'"""Owned trusted numerical validation package."""\n')]:
        path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    for name,source in [('correction_core.py','cif_parallelity_correction.py'),('gradient_core.py','cif_gradient_audit.py'),
            *[('nasolve/'+n,n) for n in _PACKAGE]]:(work/name).write_bytes(Path(__file__).with_name(source).read_bytes())
    return {'inputs':inputs,'native_spec':_ref(work/'native_spec.json',root),'geometry_spec':_ref(work/'geometry_spec.json',root),
        'worker':_ref(work/'geometry_worker.py',root),'precondition':_ref(work/'gradient_validation.json',root),
        'correction_core_sha256':QUALIFIED_CORRECTION_SHA256,'precondition_policy_id':PRECONDITION_ID}


def _endpoint_derivatives(result,proof,count):
    """Recompute the established positive endpoint proof without convergence gates."""
    from .cif_corrected_geometry import _sampled_cases,FAMILIES,_norm
    _need(result['policy_id']==POLICY_ID and result['status']=='REVIEW' and result['captured_inventory_matches'] is True
        and result['qualified_initial_snapshot_matches'] is True and result['policy_inventory'] is True and result['normalization'] is False
        and result['automatic_adoption'] is False and result['starting_coordinates']=='CAPTURED_INITIAL' and result['special_position_count']==0
        and result['constraint_signature_before']==result['constraint_signature_after']==proof['constraint_signature_before']
        and result['correction_policy_id']==proof['correction_policy_id'] and result['derivative_precondition']=='SAMPLED_NATIVE_DERIVATIVES_PASS')
    for new,old in [('installed_optimizer_sources','installed_numeric_sources'),('installed_adapter_sources','installed_adapter_sources'),('installed_parallelity_sources','installed_parallelity_sources')]:_need(result[new]==proof[old])
    for k in ['target','gradient_norm']:_need(_close(result['initial'][k],proof['gradient_audit']['cases']['initial']['families']['all']['baseline'][k]))
    audit=result['endpoint_gradient_audit']
    _need(audit['policy_id']=='cif-fixed-native-gradient-audit-v1' and audit['analysis_completed'] is True and audit['model_optimization']=='NOT_RUN'
        and audit['automatic_adoption'] is False and audit['selected_indices']==proof['selected_indices']
        and type(audit['evaluation_calls']) is int and type(audit['max_evaluation_calls']) is int and 0<audit['evaluation_calls']<=audit['max_evaluation_calls']<=4000
        and result['endpoint_derivative_qualification']=='SAMPLED_NATIVE_DERIVATIVES_PASS')
    _sampled_cases(audit,count,{'full_precision','pdb_rounded'})
    calls=sum(2*len(FAMILIES)+1+len(case['descent_profile'])
        +sum(2*len(direction['samples']) for family in case['families'].values() for direction in family['directions'])
        for case in audit['cases'].values())
    _need(audit['evaluation_calls']==calls and audit['max_evaluation_calls']==4000)
    for label,field in [('full_precision','final'),('pdb_rounded','serialized')]:
        case=audit['cases'][label];families=case['families'];baseline=families['all']['baseline']
        _need(all(_close(result[field][k],baseline[k]) for k in ['target','gradient_norm']))
        for family in families.values():
            b=family['baseline'];_need(_close(b['target'],family['repeat_target']) and _close(b['gradient_norm'],family['repeat_gradient_norm']))
        total=math.fsum(families[f]['baseline']['target'] for f in FAMILIES[1:]);_need(_close(total,baseline['target'])
            and _close(case['target_additivity']['all'],baseline['target']) and _close(case['target_additivity']['sum_controls'],total))
        summed=[math.fsum(families[f]['baseline']['gradient'][i] for f in FAMILIES[1:]) for i in range(3*count)]
        mismatch=_norm([a-b for a,b in zip(summed,baseline['gradient'])]);_need(_close(mismatch,case['gradient_additivity']['difference_norm']) and mismatch<=1e-8+1e-10*max(1.,baseline['gradient_norm']))
        comparisons=case['captured_snapshot_match']['comparisons'];_need(set(comparisons)=={'target','gradient_norm'} and all(v['consistent'] is True
            and _close(v['captured'],result[field][k]) and _close(v['rebuilt'],baseline[k]) for k,v in comparisons.items()))
    return True


def _validate_endpoint(result,proof,count,max_iterations,parent_archive_sha256):
    from .cif_fixed_geometry import _points,classify_stopping
    _points(result['final_sites_cart'],count)
    _need(result['termination_parameters']=={'max_iterations':max_iterations,'max_calls':max_iterations*20,'traditional_convergence_test':True,'traditional_convergence_test_eps':1e-5}
        and result['derivative_validation_archive']==parent_archive_sha256)
    stop=result['stopping'];_need(all(type(stop[k]) is int and stop[k]>=0 for k in ['iterations','calls','max_iterations']) and stop['max_iterations']==max_iterations
        and isinstance(stop['reason'],str) and type(stop['native_criterion_met']) is bool and (stop['error'] is None or isinstance(stop['error'],str)))
    okay=_endpoint_derivatives(result,proof,count)
    for field in ['initial','final','serialized']:
        _need(all(type(result[field][k]) in (int,float) and math.isfinite(result[field][k]) and (k!='gradient_norm' or result[field][k]>=0) for k in ['target','gradient_norm']))
    return {'status':'ENDPOINT_DERIVATIVES_PASS','sampled_derivatives_pass':okay,'stopping_classification':classify_stopping(stop),
        'scientific_qualification':'NOT_ASSESSED','automatic_adoption':False}


def _decision(checks,stopping=None):
    usable=bool(checks) and all(v is True for v in checks.values())
    return {'status':'CONTINUE_WITH_NOTES','selected':'qualified_geometry_endpoint' if usable else 'verified_constructed_model',
        'native_usable':True,'endpoint_usable':usable,'checks':checks,'stopping':stopping,'continue_solving':True,
        'notes':['Stopping, pucker, chirality and residual findings are recorded separately from fixed native mechanics.',
            'The optional separate endpoint is selected only when its fixed objective and native checks qualify; otherwise the usable starting model is retained.'],
        'scientific_qualification':'NOT_ASSESSED','automatic_adoption':False,'requires_cif_review':False}


def _result_summary(result):
    from .cif_fixed_geometry import classify_stopping
    return {'stopping_classification':classify_stopping(result['stopping']),
        'initial_target':result['initial']['target'],'final_target':result['final']['target'],
        'initial_gradient_norm':result['initial']['gradient_norm'],'final_gradient_norm':result['final']['gradient_norm'],
        'endpoint_derivative_qualification':result['endpoint_derivative_qualification']}


def _completed_result(root,expected):
    from .cif_mixed_gradient import _manager_digest
    result=_load(root/'job/geometry_result.json');fresh=_load(root/'job/native_validation.json')
    _need(_manager_digest(fresh)==_manager_digest(expected))
    return result


def _analysis(root,gradient,context,parent,report,expected,proof,model,cifs,phils):
    """Derive optional endpoint eligibility from saved evidence, never stopping alone."""
    from .cif_fixed_geometry import write_geometry_candidate,qualify_fixed_policy_geometry,review_fixed_coordinates
    from .cif_captured_geometry import review_captured_geometry
    from .cif_mixed_linked_recovery import _capture
    execution=report['execution'];checks={};summary=None;qualification={'status':'NOT_RUN'};stopping=None
    capture=None;count=int('returncode' in execution)
    if 'receipt' in report['native_readback']:
        ref=report['native_readback']['receipt'];_resolve(root,gradient,context,parent,ref)
        capture=_capture(root,{**ref,'anchor':'mixed_linked_recovery_directory'},root/'candidate/mixed_geometry_model.pdb',cifs,phils)
        count+=int('returncode' in capture.get('execution',{}))
        _need(capture['phenix_version']==report['phenix_version'] and capture['executable_sha256']==report['executable_sha256']
            and capture['execution']['timeout_seconds']==min(report['timeout_seconds'],60))
    _need(report['new_native_calls']==count and count<=2)
    if execution['status']=='COMPLETED':
        result=None
        try:
            result=_completed_result(root,expected)
            qualification=_validate_endpoint(result,proof,expected['atom_count'],report['max_iterations'],report['parent_archive_sha256'])
        except (OSError,ValueError,KeyError,TypeError,IndexError,ZeroDivisionError,OverflowError) as exc:
            qualification={'status':'REVIEW','sampled_derivatives_pass':False,'finding_type':type(exc).__name__,'finding':'OPTIONAL_ENDPOINT_UNQUALIFIED'}
        stopping=result.get('stopping') if isinstance(result,dict) else None;checks['qualified_endpoint_derivatives']=qualification.get('sampled_derivatives_pass') is True
        if checks['qualified_endpoint_derivatives']:
            summary=_result_summary(result);candidate=root/'candidate/mixed_geometry_model.pdb'
            if candidate.is_file():
                try:
                    with tempfile.TemporaryDirectory(prefix='mixed-geometry-serialization-') as temporary:
                        path=Path(temporary).resolve()/'model.pdb';serialization=write_geometry_candidate(model,path,expected,result['final_sites_cart'])
                        _need(path.read_bytes()==candidate.read_bytes() and _load(root/'serialization.json')==serialization)
                    full=review_fixed_coordinates(expected,result['final_sites_cart']);_need(_load(root/'full_precision_geometry.json')==full)
                    checks['exact_identity_serialization']=True
                except (OSError,ValueError,KeyError,TypeError,IndexError):checks['exact_identity_serialization']=False
            else:checks['exact_identity_serialization']=False
            if capture is not None and capture.get('status')=='REVIEW' and capture['execution'].get('status')=='COMPLETED' and capture['execution'].get('returncode')==0:
                try:
                    after=capture['native_validation'];mechanics=qualify_fixed_policy_geometry(expected,after,candidate,_load(root/'serialization.json'))
                    _need(_load(root/'native_mechanics.json')==mechanics)
                    rounded=review_captured_geometry(after);_need(_load(root/'rounded_geometry.json')==rounded)
                    checks['fixed_native_mechanics']=mechanics['mechanics_checks_pass'] is True
                    checks['fresh_rounded_target']=_close(after['energy_inventory']['snapshots'][0]['target'],result['serialized']['target'])
                except (OSError,ValueError,KeyError,TypeError,IndexError):checks['fixed_native_mechanics']=False
            else:checks['fixed_native_mechanics']=False
            checks['nonworse_fixed_objective']=all(result[f]['target']<=result['initial']['target']+1e-8+1e-10*abs(result['initial']['target']) for f in ['final','serialized'])
        elif capture is not None:_need(False)
    elif capture is not None:_need(False)
    return qualification,_decision(checks,stopping),summary


def _publish(root,gradient,context,parent,report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['outputs']=[_ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT and p.suffix not in {'.pkl','.pickle','.pyc'}]
    _dump(root/REPORT,report)
    read_mixed_geometry_trial(root,gradient_directory=gradient,context_directory=context,linked_parent_directory=parent,parent_archive_sha256=report['parent_archive_sha256'])
    return report


def trial_mixed_geometry(gradient_directory,context_directory,linked_parent_directory,phenix,output,*,parent_archive_sha256,max_iterations=1000,timeout_seconds=600):
    from .cif_native_validation import _stop,inspect_native_bundle
    from .cif_fixed_geometry import write_geometry_candidate,review_fixed_coordinates,qualify_fixed_policy_geometry
    from .cif_captured_geometry import review_captured_geometry
    if type(max_iterations) is not int or not 1<=max_iterations<=1000:raise ValueError('Require1to1000geometryiterations')
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=600:raise ValueError('Require1to600secondnative deadline')
    if not _digest(parent_archive_sha256):raise ValueError('RequireverifiedparentarchiveSHA256')
    gradient,context,parent=map(lambda p:Path(p).resolve(strict=True),(gradient_directory,context_directory,linked_parent_directory));root=Path(output).absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root,*root.parents]) and not any(root.resolve().is_relative_to(p) for p in [gradient,context,parent]))
    source,model,cifs,phils,expected,proof,bindings=_inputs(gradient,context,parent)
    proof_bytes=(gradient/'job/gradient_result.json').read_bytes();root.mkdir(parents=True)
    prep=_prepare(root,model,cifs,phils,expected,proof,proof_bytes,parent_archive_sha256,max_iterations)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':prep,
        'parent_archive_sha256':parent_archive_sha256,'parent_archive_verification':'CALLER_VERIFIED_EXACT_CAPSULE_BYTES; SCIENCE_BOUND_BY_MAINTAINED_PARENT_READERS',
        'max_iterations':max_iterations,'timeout_seconds':timeout_seconds,'maximum_native_calls':2,'new_native_calls':0,
        'execution':{'status':'NOT_RUN'},'native_readback':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},
        'coordinate_decision':_decision({}),'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN',
        'readyset_execution':'NOT_RUN','coot_execution':'NOT_RUN','refinement':'NOT_RUN','cache_writes':'NOT_RUN',
        'captured_code_execution':'NOT_RUN','scientific_qualification':'NOT_ASSESSED','automatic_adoption':False,
        'requires_cif_review':False,'policy_authority':'NARestraints','source_chemical_findings':'PRESERVED_IN_BOUND_CONTEXT; NOT_PROMOTED_BY_GEOMETRY_TRIAL'}
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True);fingerprint=sha256(executable.read_bytes()).hexdigest()
        report.update(status='REVIEW',phenix_version=phenix.version,executable_provenance=str(executable),executable_sha256=fingerprint)
        started=time.monotonic()
        try:
            with (root/'job/geometry.log').open('xb') as log:
                process=subprocess.Popen([str(executable),'-B','geometry_worker.py','geometry_spec.json'],cwd=root/'job',env=dict(phenix.environment),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                report['new_native_calls']=1;report['model_optimization']='EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL'
                try:code=process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:_stop(process);report['execution']={'status':'TIMED_OUT','returncode':process.returncode}
                except BaseException as exc:
                    _stop(process);report['execution']={'status':'WAIT_FAILED','returncode':process.returncode,'error_type':type(exc).__name__}
                    raise
                else:report['execution']={'status':'COMPLETED' if code==0 else 'FAILED','returncode':code}
            if report['execution']['status']=='COMPLETED':
                result=_completed_result(root,expected)
                _validate_endpoint(result,proof,expected['atom_count'],max_iterations,parent_archive_sha256)
                candidate=root/'candidate/mixed_geometry_model.pdb';candidate.parent.mkdir()
                serialization=write_geometry_candidate(model,candidate,expected,result['final_sites_cart']);_dump(root/'serialization.json',serialization)
                _dump(root/'full_precision_geometry.json',review_fixed_coordinates(expected,result['final_sites_cart']))
                capture=inspect_native_bundle(candidate,cifs,root/'native_readback',executable,environment=phenix.environment,phenix_version=phenix.version,
                    timeout_seconds=min(timeout_seconds,60),phil_files=phils,phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',policy_inventory=True,energy_inventory=True)
                report['new_native_calls']+=int('returncode' in capture.get('execution',{}))
                report['native_readback']={'receipt':_ref(Path(capture['native_directory'])/'native_receipt.json',root)}
                if capture.get('status')=='REVIEW' and capture['execution'].get('returncode')==0:
                    after=capture['native_validation'];_dump(root/'native_mechanics.json',qualify_fixed_policy_geometry(expected,after,candidate,serialization))
                    _dump(root/'rounded_geometry.json',review_captured_geometry(after))
        except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError) as exc:
            report['optional_trial_finding']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['optional_trial_finding']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
        _need(sha256(executable.read_bytes()).hexdigest()==fingerprint)
        q,decision,summary=_analysis(root,gradient,context,parent,report,expected,proof,model,cifs,phils)
        report['qualification']=q;report['coordinate_decision']=decision
        if summary is not None:report['geometry_summary']=summary
        if decision['endpoint_usable']:report['status']='MIXED_GEOMETRY_ENDPOINT_PASS'
    return _publish(root,gradient,context,parent,report)


def _read_mixed_geometry_trial(directory,*,gradient_directory,context_directory,linked_parent_directory,parent_archive_sha256):
    root,gradient,context,parent=map(Path,(directory,gradient_directory,context_directory,linked_parent_directory))
    _need(_digest(parent_archive_sha256) and not any(p.is_symlink() for p in [root,*root.parents]))
    report=_load(root/REPORT)
    _need(report['schema_version']==1 and report['policy_id']==POLICY_ID and report['status'] in {'PREPARED_ONLY','REVIEW','MIXED_GEOMETRY_ENDPOINT_PASS'}
        and report['parent_archive_sha256']==parent_archive_sha256 and report['maximum_native_calls']==2
        and type(report['new_native_calls']) is int and 0<=report['new_native_calls']<=2
        and type(report['max_iterations']) is int and 1<=report['max_iterations']<=1000
        and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600
        and report['scientific_qualification']=='NOT_ASSESSED' and report['automatic_adoption'] is False and report['requires_cif_review'] is False
        and report['policy_authority']=='NARestraints' and all(report[k]=='NOT_RUN' for k in ['dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution']))
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,gradient,context,parent,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT and p.suffix not in {'.pkl','.pickle','.pyc'}:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    _,model,cifs,phils,expected,proof,bindings=_inputs(gradient,context,parent);_need(report['inputs']==bindings)
    with tempfile.TemporaryDirectory(prefix='mixed-geometry-reader-') as temporary:
        replay=Path(temporary).resolve();prep=_prepare(replay,model,cifs,phils,expected,proof,(gradient/'job/gradient_result.json').read_bytes(),parent_archive_sha256,report['max_iterations'])
        _need(prep==report['preparation'])
        for p in replay.rglob('*'):
            if p.is_file():_need((root/p.relative_to(replay)).read_bytes()==p.read_bytes())
    execution=report['execution'];state=execution['status']
    if report['new_native_calls']==0:
        _need(report['qualification']=={'status':'NOT_RUN'} and report['native_readback']=={'status':'NOT_RUN'} and report['model_optimization']=='NOT_RUN'
            and ((report['status']=='PREPARED_ONLY' and execution=={'status':'NOT_RUN'}) or (report['status']=='REVIEW' and state=='LAUNCH_FAILED' and isinstance(execution['error'],str))))
    else:
        _need(report['status']!='PREPARED_ONLY' and state in {'COMPLETED','FAILED','TIMED_OUT','WAIT_FAILED'} and type(execution['returncode']) is int
            and (state!='COMPLETED' or execution['returncode']==0) and (state!='FAILED' or execution['returncode']!=0)
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0
            and report['model_optimization']=='EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL' and _digest(report['executable_sha256'])
            and isinstance(report['phenix_version'],str) and bool(report['phenix_version']))
    q,decision,summary=_analysis(root,gradient,context,parent,report,expected,proof,model,cifs,phils)
    _need(report['qualification']==q and report['coordinate_decision']==decision and report.get('geometry_summary')==summary
        and (report['status']=='MIXED_GEOMETRY_ENDPOINT_PASS') is decision['endpoint_usable'])
    return report


def read_mixed_geometry_trial(directory,*,gradient_directory,context_directory,linked_parent_directory,parent_archive_sha256):
    """Reproduce the saved decision from bound evidence without a native process."""
    try:return _read_mixed_geometry_trial(directory,gradient_directory=gradient_directory,context_directory=context_directory,
        linked_parent_directory=linked_parent_directory,parent_archive_sha256=parent_archive_sha256)
    except (KeyError,TypeError,IndexError,OverflowError) as exc:raise ValueError('Incomplete mixed geometry report') from exc
