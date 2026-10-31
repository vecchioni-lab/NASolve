"""Bounded mechanics-only geometry from a qualified, frozen native capture.

Reuse maintained numerical workers without component-name or recovery ancestry
requirements. Neither input usability nor source chemistry follows from a
numerical proof; the candidate is never automatically selected or adopted.
"""
from hashlib import sha256
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from . import cif_mixed_geometry as geometry
from . import cif_captured_mixed_gradients as gradients
from .cif_attachment_native import _capture
from .cif_fana_junction import _path

POLICY_ID = 'cif-captured-fixed-geometry-trial-v1'
REPORT = 'captured_geometry_trial.json'
ANCHOR = geometry.ANCHOR
GRADIENT_ANCHOR = 'captured_gradient_directory'
SOURCE_SCOPE = 'NOT_ESTABLISHED_BY_NUMERICAL_CAPTURE'


def _need(value):
    if not value:raise ValueError('Captured geometry evidence does not reproduce')


def _resolve(root, gradient, ref):
    _need(isinstance(ref,dict) and ref.get('anchor') in {ANCHOR,GRADIENT_ANCHOR})
    directory=root if ref['anchor']==ANCHOR else gradient
    from .cif_mixed_recovery import _safe
    _need(_safe(ref.get('path')));path=directory/ref['path']
    _need(geometry._ref(path,directory,ref['anchor'])==ref)
    return path


def _inputs(gradient):
    gradient=_path(gradient,directory=True)
    source=gradients.read_captured_mixed_gradients(gradient)
    _need(source['status']=='CAPTURED_MIXED_DERIVATIVES_PASS' and source['new_native_calls']==1)
    capture,model,cifs,phils,expected,_=gradients._inputs(gradient/'capture')
    proof_path=gradient/'job/gradient_result.json'
    ref=lambda p:geometry._ref(p,gradient,GRADIENT_ANCHOR)
    bindings={'gradient_report':ref(gradient/gradients.REPORT),'gradient_result':ref(proof_path),
        'active_capture':ref(gradient/'capture/native_receipt.json'),'model':ref(model),
        'dictionaries':[ref(p) for p in cifs],'phils':[ref(p) for p in phils]}
    return source,model,cifs,phils,expected,geometry._load(proof_path),bindings,capture


def _prepare(root,model,cifs,phils,expected,proof,proof_bytes,digest,max_iterations,capture):
    prep=geometry._prepare(root,model,cifs,phils,expected,proof,proof_bytes,digest,max_iterations)
    path=root/'job/native_spec.json';spec=geometry._load(path)
    spec['phil_namespace_policy']=capture['phil_namespace_policy']
    if capture['dictionary_source_policy']=='INSTALLED_LIBRARY_ONLY':spec['installed_library_only']=True
    geometry._dump(path,spec);prep['native_spec']=geometry._ref(path,root)
    return prep


def _decision(checks,stopping=None):
    passed=bool(checks) and all(v is True for v in checks.values())
    return {'status':'MECHANICS_PASS' if passed else 'REVIEW','selected':'INPUT_MODEL_UNCHANGED',
        'candidate_mechanics_pass':passed,'checks':checks,'stopping':stopping,
        'input_usability':'NOT_ESTABLISHED_BY_NUMERICAL_CAPTURE','chemical_qualification':'NOT_ASSESSED',
        'scientific_qualification':'NOT_ASSESSED','automatic_adoption':False}


def _readback(root,ref,model,cifs,phils,capture):
    _need(ref['anchor']==ANCHOR and ref['path'].startswith('native_readback/') and Path(ref['path']).name=='native_receipt.json')
    path=_resolve(root,root/'gradient',ref)
    receipt,native,snapshots=_capture(path,model.read_bytes())
    expected=[('model',model),*[('dictionary',p) for p in cifs],*[('phil',p) for p in phils]]
    _need(len(receipt['inputs'])==len(expected)
        and receipt['phil_namespace_policy']==capture['phil_namespace_policy']
        and receipt['dictionary_source_policy']==capture['dictionary_source_policy'])
    for row,(role,source) in zip(receipt['inputs'],expected):
        _need(row['role']==role and (path.parent/row['path']).read_bytes()==source.read_bytes())
    return receipt

def _analysis(root,gradient,report,expected,proof,model,cifs,phils,source_capture):
    """Derive optional endpoint eligibility from saved evidence, never stopping alone."""
    from .cif_fixed_geometry import write_geometry_candidate,qualify_fixed_policy_geometry,review_fixed_coordinates
    from .cif_captured_geometry import review_captured_geometry
    execution=report['execution'];checks={};summary=None;qualification={'status':'NOT_RUN'};stopping=None
    capture=None;count=int('returncode' in execution)
    if 'receipt' in report['native_readback']:
        ref=report['native_readback']['receipt'];_resolve(root,gradient,ref)
        capture=_readback(root,ref,root/'candidate/mixed_geometry_model.pdb',cifs,phils,source_capture)
        count+=int('returncode' in capture.get('execution',{}))
        _need(capture['phenix_version']==report['phenix_version'] and capture['executable_sha256']==report['executable_sha256']
            and capture['execution']['timeout_seconds']==min(report['timeout_seconds'],60))
    _need(report['new_native_calls']==count and count<=2)
    if execution['status']=='COMPLETED':
        result=None
        try:
            result=geometry._completed_result(root,expected)
            qualification=geometry._validate_endpoint(result,proof,expected['atom_count'],report['max_iterations'],report['gradient_report_sha256'])
        except (OSError,ValueError,KeyError,TypeError,IndexError,ZeroDivisionError,OverflowError) as exc:
            qualification={'status':'REVIEW','sampled_derivatives_pass':False,'finding_type':type(exc).__name__,'finding':'OPTIONAL_ENDPOINT_UNQUALIFIED'}
        stopping=result.get('stopping') if isinstance(result,dict) else None;checks['qualified_endpoint_derivatives']=qualification.get('sampled_derivatives_pass') is True
        if checks['qualified_endpoint_derivatives']:
            summary=geometry._result_summary(result);candidate=root/'candidate/mixed_geometry_model.pdb'
            if candidate.is_file():
                try:
                    with tempfile.TemporaryDirectory(prefix='mixed-geometry-serialization-') as temporary:
                        path=Path(temporary).resolve()/'model.pdb';serialization=write_geometry_candidate(model,path,expected,result['final_sites_cart'])
                        _need(path.read_bytes()==candidate.read_bytes() and geometry._load(root/'serialization.json')==serialization)
                    full=review_fixed_coordinates(expected,result['final_sites_cart']);_need(geometry._load(root/'full_precision_geometry.json')==full)
                    checks['exact_identity_serialization']=True
                except (OSError,ValueError,KeyError,TypeError,IndexError):checks['exact_identity_serialization']=False
            else:checks['exact_identity_serialization']=False
            if capture is not None and capture.get('status')=='REVIEW' and capture['execution'].get('status')=='COMPLETED' and capture['execution'].get('returncode')==0:
                try:
                    after=capture['native_validation'];mechanics=qualify_fixed_policy_geometry(expected,after,candidate,geometry._load(root/'serialization.json'))
                    _need(geometry._load(root/'native_mechanics.json')==mechanics)
                    rounded=review_captured_geometry(after);_need(geometry._load(root/'rounded_geometry.json')==rounded)
                    checks['fixed_native_mechanics']=mechanics['mechanics_checks_pass'] is True
                    checks['fresh_rounded_target']=geometry._close(after['energy_inventory']['snapshots'][0]['target'],result['serialized']['target'])
                except (OSError,ValueError,KeyError,TypeError,IndexError):checks['fixed_native_mechanics']=False
            else:checks['fixed_native_mechanics']=False
            checks['nonworse_fixed_objective']=all(result[f]['target']<=result['initial']['target']+1e-8+1e-10*abs(result['initial']['target']) for f in ['final','serialized'])
        elif capture is not None:_need(False)
    elif capture is not None:_need(False)
    return qualification,_decision(checks,stopping),summary


def _publish(root, report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['directories']=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())
    report['outputs']=[geometry._ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT]
    geometry._dump(root/REPORT,report);read_captured_geometry_trial(root)
    return report

def trial_captured_geometry(gradient_directory,phenix,output,*,max_iterations=1000,timeout_seconds=600):
    from .cif_native_validation import _stop,inspect_native_bundle
    from .cif_fixed_geometry import write_geometry_candidate,review_fixed_coordinates,qualify_fixed_policy_geometry
    from .cif_captured_geometry import review_captured_geometry
    if type(max_iterations) is not int or not 1<=max_iterations<=1000:raise ValueError('Require 1 to 1000 geometry iterations')
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=600:raise ValueError('Require a native deadline from 1 to 600 seconds')
    original=_path(gradient_directory,directory=True);root=Path(output).expanduser().absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root,*root.parents])
        and not root.is_relative_to(original) and not original.is_relative_to(root))
    source,model,cifs,phils,expected,proof,bindings,capture=_inputs(original)
    digest=bindings['gradient_report']['sha256']
    snapshots={original/gradients.REPORT:(original/gradients.REPORT).read_bytes()}
    snapshots.update({original/r['path']:(original/r['path']).read_bytes() for r in source['outputs']})
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True)
        fingerprint=sha256(executable.read_bytes()).hexdigest()
        _need(fingerprint==source['executable_sha256'] and phenix.version==source['phenix_version'])
    proof_bytes=(original/'job/gradient_result.json').read_bytes()
    with tempfile.TemporaryDirectory(prefix='captured-geometry-preflight-') as temporary:
        _prepare(Path(temporary).resolve(),model,cifs,phils,expected,proof,proof_bytes,digest,max_iterations,capture)
    _need(all(p.read_bytes()==data for p,data in snapshots.items()))
    root.mkdir(parents=True,exist_ok=False);gradient=root/'gradient'
    for path,data in snapshots.items():
        destination=gradient/path.relative_to(original);destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as stream:stream.write(data)
    frozen,model,cifs,phils,expected,proof,frozen_bindings,frozen_capture=_inputs(gradient)
    _need(source==frozen and bindings==frozen_bindings and capture==frozen_capture
        and all(p.read_bytes()==data for p,data in snapshots.items()))
    prep=_prepare(root,model,cifs,phils,expected,proof,proof_bytes,digest,max_iterations,capture)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':prep,
        'gradient_report_sha256':digest,'coordinate_scope':'ALL_CAPTURED_ATOMS_VARIABLE',
        'max_iterations':max_iterations,'timeout_seconds':timeout_seconds,'maximum_native_calls':2,'new_native_calls':0,
        'execution':{'status':'NOT_RUN'},'native_readback':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},
        'coordinate_decision':_decision({}),'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN',
        'readyset_execution':'NOT_RUN','coot_execution':'NOT_RUN','refinement':'NOT_RUN','cache_writes':'NOT_RUN',
        'captured_code_execution':'NOT_RUN','scientific_qualification':'NOT_ASSESSED','automatic_adoption':False,
        'requires_cif_review':False,'policy_authority':'CAPTURED_EXPLICIT_POLICY','source_chemical_findings':SOURCE_SCOPE}
    if phenix is not None:
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
                result=geometry._completed_result(root,expected)
                geometry._validate_endpoint(result,proof,expected['atom_count'],max_iterations,digest)
                candidate=root/'candidate/mixed_geometry_model.pdb';candidate.parent.mkdir()
                serialization=write_geometry_candidate(model,candidate,expected,result['final_sites_cart']);geometry._dump(root/'serialization.json',serialization)
                geometry._dump(root/'full_precision_geometry.json',review_fixed_coordinates(expected,result['final_sites_cart']))
                readback=inspect_native_bundle(candidate,cifs,root/'native_readback',executable,environment=phenix.environment,phenix_version=phenix.version,
                    timeout_seconds=min(timeout_seconds,60),phil_files=phils,phil_namespace_policy=capture['phil_namespace_policy'],inventory_detail='linked',policy_inventory=True,energy_inventory=True,installed_library_only=capture['dictionary_source_policy']=='INSTALLED_LIBRARY_ONLY')
                report['new_native_calls']+=int('returncode' in readback.get('execution',{}))
                report['native_readback']={'receipt':geometry._ref(Path(readback['native_directory'])/'native_receipt.json',root)}
                if readback.get('status')=='REVIEW' and readback['execution'].get('returncode')==0:
                    after=readback['native_validation'];geometry._dump(root/'native_mechanics.json',qualify_fixed_policy_geometry(expected,after,candidate,serialization))
                    geometry._dump(root/'rounded_geometry.json',review_captured_geometry(after))
        except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError) as exc:
            report['optional_trial_finding']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['optional_trial_finding']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
        _need(sha256(executable.read_bytes()).hexdigest()==fingerprint)
        q,decision,summary=_analysis(root,gradient,report,expected,proof,model,cifs,phils,capture)
        report['qualification']=q;report['coordinate_decision']=decision
        if summary is not None:report['geometry_summary']=summary
        if decision['candidate_mechanics_pass']:report['status']='CAPTURED_GEOMETRY_MECHANICS_PASS'
    return _publish(root,report)


def _read_captured_geometry_trial(directory):
    root=_path(directory,directory=True);gradient=root/'gradient'
    _need(not any(p.is_symlink() for p in [root,*root.parents]))
    report=geometry._load(root/REPORT)
    _need(type(report['schema_version']) is int and report['schema_version']==1 and report['policy_id']==POLICY_ID and report['status'] in {'PREPARED_ONLY','REVIEW','CAPTURED_GEOMETRY_MECHANICS_PASS'}
        and geometry._digest(report['gradient_report_sha256']) and type(report['maximum_native_calls']) is int and report['maximum_native_calls']==2
        and report['coordinate_scope']=='ALL_CAPTURED_ATOMS_VARIABLE' and report['source_chemical_findings']==SOURCE_SCOPE
        and type(report['new_native_calls']) is int and 0<=report['new_native_calls']<=2
        and type(report['max_iterations']) is int and 1<=report['max_iterations']<=1000
        and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600
        and report['scientific_qualification']=='NOT_ASSESSED' and report['automatic_adoption'] is False and report['requires_cif_review'] is False
        and report['policy_authority']=='CAPTURED_EXPLICIT_POLICY' and all(report[k]=='NOT_RUN' for k in ['dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution']))
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,gradient,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    directories={p.as_posix() for name in actual for p in Path(name).parents if p!=Path('.')}
    _need(report['directories']==sorted(directories) and report['directories']==sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()))
    source,model,cifs,phils,expected,proof,bindings,capture=_inputs(gradient)
    digest=bindings['gradient_report']['sha256']
    _need(report['inputs']==bindings and report['gradient_report_sha256']==digest)
    with tempfile.TemporaryDirectory(prefix='mixed-geometry-reader-') as temporary:
        replay=Path(temporary).resolve();prep=_prepare(replay,model,cifs,phils,expected,proof,(gradient/'job/gradient_result.json').read_bytes(),digest,report['max_iterations'],capture)
        _need(prep==report['preparation'])
        prepared={p.relative_to(replay).as_posix() for p in replay.rglob('*') if p.is_file()}
        for name in prepared:_need((root/name).read_bytes()==(replay/name).read_bytes())
    allowed=prepared|{'gradient/'+gradients.REPORT}|{'gradient/'+r['path'] for r in source['outputs']}
    if report['execution']['status']!='NOT_RUN':
        allowed|={'job/'+n for n in ['geometry.log','geometry_result.json','native_validation.json','minimizer.log','native_effective.phil','installed_source/parallelity.h','installed_source/parallelity_bpl.cpp']}
        allowed|={f'job/canonical_{i:03d}.phil' for i in range(len(phils))}
        allowed|={'candidate/mixed_geometry_model.pdb','serialization.json','full_precision_geometry.json','native_mechanics.json','rounded_geometry.json'}
    if 'receipt' in report['native_readback']:
        ref=report['native_readback']['receipt'];path=_resolve(root,gradient,ref)
        native=_readback(root,ref,root/'candidate/mixed_geometry_model.pdb',cifs,phils,capture)
        allowed.add(ref['path']);allowed|={(path.parent/r['path']).relative_to(root).as_posix() for r in native['outputs']}
    _need(actual<=allowed)
    for row in proof['installed_parallelity_sources']:
        path=root/'job/installed_source'/row['path']
        if path.exists():
            data=path.read_bytes();_need(len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256'])
        elif report['status']=='CAPTURED_GEOMETRY_MECHANICS_PASS':_need(False)
    execution=report['execution'];state=execution['status']
    if state!='NOT_RUN':
        _need(report['phenix_version']==source['phenix_version'] and report['executable_sha256']==source['executable_sha256']
            and isinstance(report['executable_provenance'],str) and bool(report['executable_provenance'])
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0)
    if report['new_native_calls']==0:
        _need(report['qualification']=={'status':'NOT_RUN'} and report['native_readback']=={'status':'NOT_RUN'} and report['model_optimization']=='NOT_RUN'
            and ((report['status']=='PREPARED_ONLY' and execution=={'status':'NOT_RUN'}) or (report['status']=='REVIEW' and state=='LAUNCH_FAILED' and isinstance(execution['error'],str))))
    else:
        _need(report['status']!='PREPARED_ONLY' and state in {'COMPLETED','FAILED','TIMED_OUT','WAIT_FAILED'} and type(execution['returncode']) is int
            and (state!='COMPLETED' or execution['returncode']==0) and (state!='FAILED' or execution['returncode']!=0)
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0
            and report['model_optimization']=='EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL' and geometry._digest(report['executable_sha256'])
            and report['phenix_version']==source['phenix_version'] and report['executable_sha256']==source['executable_sha256']
            and isinstance(report['executable_provenance'],str) and bool(report['executable_provenance']))
    q,decision,summary=_analysis(root,gradient,report,expected,proof,model,cifs,phils,capture)
    _need(report['qualification']==q and report['coordinate_decision']==decision and report.get('geometry_summary')==summary
        and (report['status']=='CAPTURED_GEOMETRY_MECHANICS_PASS') is decision['candidate_mechanics_pass'])
    return report


def read_captured_geometry_trial(directory):
    """Replay saved mechanics without an SDK or any source-chemical approval."""
    try:return _read_captured_geometry_trial(directory)
    except (KeyError,TypeError,IndexError,OverflowError) as exc:raise ValueError('Incomplete captured geometry report') from exc
