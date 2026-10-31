"""Bounded geometry for a freshly qualified source-recovered objective.

Only the parent/receipt adapter is new. The maintained geometry worker,
optimizer, endpoint derivative policy and native mechanics checks are unchanged.
Historical mixed-model workers remain byte-identical for saved-evidence replay.
"""
from hashlib import sha256
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from . import cif_mixed_geometry as geometry
from . import cif_mixed_source_recovery as recovery
from . import cif_recovered_gradient as gradients

POLICY_ID = 'cif-recovered-mixed-geometry-trial-v1'
REPORT = 'recovered_geometry_trial.json'
ANCHOR = geometry.ANCHOR
GRADIENT_ANCHOR = 'recovered_gradient_directory'
ARCHIVE_VERIFICATION = 'C98_READER_VERIFIED_EXACT_CAPSULE_BYTES; CURRENT_OBJECTIVE_BOUND_BY_C99'
SOURCE_SCOPE = 'PRESERVED_IN_BOUND_RECOVERY; NOT_PROMOTED_BY_GEOMETRY_TRIAL'


def _need(value):
    if not value:
        raise ValueError('Recovered geometry evidence does not reproduce')


def _resolve(root, gradient, parent, ref):
    if isinstance(ref, dict) and ref.get('anchor') == recovery.ANCHOR:
        return recovery._resolve(parent, ref)
    _need(isinstance(ref, dict) and ref.get('anchor') in {ANCHOR, GRADIENT_ANCHOR})
    directory = root if ref['anchor'] == ANCHOR else gradient
    from .cif_mixed_recovery import _safe
    _need(_safe(ref.get('path')))
    path = directory/ref['path']
    _need(geometry._ref(path, directory, ref['anchor']) == ref)
    return path


def _inputs(gradient, parent):
    source = gradients.read_recovered_gradients(gradient, recovery_directory=parent)
    _need(source['status'] == 'RECOVERED_MIXED_DERIVATIVES_PASS' and source['new_native_calls'] == 1)
    # C99's maintained reader has already replayed C98. Resolve only those
    # validated bindings, avoiding a second independent parent interpretation.
    bindings = source['inputs']
    path = lambda ref: recovery._resolve(parent, ref)
    recovered = geometry._load(path(bindings['recovery_report']))
    capture = geometry._load(path(bindings['active_capture']))
    capsule = recovery._ref(parent/'capsules/endpoint.zip', parent)
    _need(capsule in recovered['outputs'] and capsule['sha256'] == recovered['specification']['endpoint_sha256'])
    proof_path = gradient/'job/gradient_result.json'
    bindings = {**bindings, 'endpoint_capsule': capsule,
        'gradient_report': geometry._ref(gradient/gradients.REPORT, gradient, GRADIENT_ANCHOR),
        'gradient_result': geometry._ref(proof_path, gradient, GRADIENT_ANCHOR)}
    return (source, path(bindings['model']), [path(ref) for ref in bindings['dictionaries']],
            [path(ref) for ref in bindings['phils']], capture['native_validation'],
            geometry._load(proof_path), bindings)


def _decision(checks, stopping=None):
    decision = geometry._decision(checks, stopping)
    if not decision['endpoint_usable']:
        decision['selected'] = 'verified_recovered_model'
    return decision


def _analysis(root, gradient, parent, report, expected, proof, model, cifs, phils):
    # The established analysis resolves only its owned native-readback receipt.
    # Parent resources have already been resolved through their genuine anchors.
    qualification, decision, summary = geometry._analysis(
        root, gradient, parent, parent, report, expected, proof, model, cifs, phils)
    if not decision['endpoint_usable']:
        decision['selected'] = 'verified_recovered_model'
    return qualification, decision, summary


def _publish(root, gradient, parent, report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['outputs'] = [geometry._ref(p, root) for p in sorted(root.rglob('*'))
                         if p.is_file() and p != root/REPORT]
    geometry._dump(root/REPORT, report)
    read_recovered_geometry(root, gradient_directory=gradient, recovery_directory=parent)
    return report


def trial_recovered_geometry(gradient_directory,recovery_directory,phenix,output,*,max_iterations=1000,timeout_seconds=600):
    from .cif_native_validation import _stop,inspect_native_bundle
    from .cif_fixed_geometry import write_geometry_candidate,review_fixed_coordinates,qualify_fixed_policy_geometry
    from .cif_captured_geometry import review_captured_geometry
    if type(max_iterations) is not int or not 1<=max_iterations<=1000:raise ValueError('Require 1 to 1000 geometry iterations')
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=600:raise ValueError('Require a native deadline from 1 to 600 seconds')
    gradient,parent=map(Path,(gradient_directory,recovery_directory));root=Path(output).absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root,*root.parents]) and not any(root.resolve().is_relative_to(p) for p in [gradient.resolve(),parent.resolve()]))
    source,model,cifs,phils,expected,proof,bindings=_inputs(gradient,parent)
    parent_archive_sha256=bindings['endpoint_capsule']['sha256']
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True)
        fingerprint=sha256(executable.read_bytes()).hexdigest()
        _need(fingerprint==source['executable_sha256'] and phenix.version==source['phenix_version'])
    proof_bytes=(gradient/'job/gradient_result.json').read_bytes();root.mkdir(parents=True)
    prep=geometry._prepare(root,model,cifs,phils,expected,proof,proof_bytes,parent_archive_sha256,max_iterations)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':prep,
        'parent_archive_sha256':parent_archive_sha256,'parent_archive_verification':ARCHIVE_VERIFICATION,
        'max_iterations':max_iterations,'timeout_seconds':timeout_seconds,'maximum_native_calls':2,'new_native_calls':0,
        'execution':{'status':'NOT_RUN'},'native_readback':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},
        'coordinate_decision':_decision({}),'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN',
        'readyset_execution':'NOT_RUN','coot_execution':'NOT_RUN','refinement':'NOT_RUN','cache_writes':'NOT_RUN',
        'captured_code_execution':'NOT_RUN','scientific_qualification':'NOT_ASSESSED','automatic_adoption':False,
        'requires_cif_review':False,'policy_authority':'NARestraints','source_chemical_findings':SOURCE_SCOPE}
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
                geometry._validate_endpoint(result,proof,expected['atom_count'],max_iterations,parent_archive_sha256)
                candidate=root/'candidate/mixed_geometry_model.pdb';candidate.parent.mkdir()
                serialization=write_geometry_candidate(model,candidate,expected,result['final_sites_cart']);geometry._dump(root/'serialization.json',serialization)
                geometry._dump(root/'full_precision_geometry.json',review_fixed_coordinates(expected,result['final_sites_cart']))
                capture=inspect_native_bundle(candidate,cifs,root/'native_readback',executable,environment=phenix.environment,phenix_version=phenix.version,
                    timeout_seconds=min(timeout_seconds,60),phil_files=phils,phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',policy_inventory=True,energy_inventory=True)
                report['new_native_calls']+=int('returncode' in capture.get('execution',{}))
                report['native_readback']={'receipt':geometry._ref(Path(capture['native_directory'])/'native_receipt.json',root)}
                if capture.get('status')=='REVIEW' and capture['execution'].get('returncode')==0:
                    after=capture['native_validation'];geometry._dump(root/'native_mechanics.json',qualify_fixed_policy_geometry(expected,after,candidate,serialization))
                    geometry._dump(root/'rounded_geometry.json',review_captured_geometry(after))
        except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError) as exc:
            report['optional_trial_finding']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['optional_trial_finding']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
        _need(sha256(executable.read_bytes()).hexdigest()==fingerprint)
        q,decision,summary=_analysis(root,gradient,parent,report,expected,proof,model,cifs,phils)
        report['qualification']=q;report['coordinate_decision']=decision
        if summary is not None:report['geometry_summary']=summary
        if decision['endpoint_usable']:report['status']='RECOVERED_GEOMETRY_ENDPOINT_PASS'
    return _publish(root,gradient,parent,report)


def _read_recovered_geometry(directory,*,gradient_directory,recovery_directory):
    root,gradient,parent=map(Path,(directory,gradient_directory,recovery_directory))
    _need(not any(p.is_symlink() for p in [root,*root.parents]))
    report=geometry._load(root/REPORT)
    _need(type(report['schema_version']) is int and report['schema_version']==1 and report['policy_id']==POLICY_ID and report['status'] in {'PREPARED_ONLY','REVIEW','RECOVERED_GEOMETRY_ENDPOINT_PASS'}
        and geometry._digest(report['parent_archive_sha256']) and type(report['maximum_native_calls']) is int and report['maximum_native_calls']==2
        and report['parent_archive_verification']==ARCHIVE_VERIFICATION and report['source_chemical_findings']==SOURCE_SCOPE
        and type(report['new_native_calls']) is int and 0<=report['new_native_calls']<=2
        and type(report['max_iterations']) is int and 1<=report['max_iterations']<=1000
        and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600
        and report['scientific_qualification']=='NOT_ASSESSED' and report['automatic_adoption'] is False and report['requires_cif_review'] is False
        and report['policy_authority']=='NARestraints' and all(report[k]=='NOT_RUN' for k in ['dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution']))
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,gradient,parent,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    source,model,cifs,phils,expected,proof,bindings=_inputs(gradient,parent)
    parent_archive_sha256=bindings['endpoint_capsule']['sha256']
    _need(report['inputs']==bindings and report['parent_archive_sha256']==parent_archive_sha256)
    with tempfile.TemporaryDirectory(prefix='mixed-geometry-reader-') as temporary:
        replay=Path(temporary).resolve();prep=geometry._prepare(replay,model,cifs,phils,expected,proof,(gradient/'job/gradient_result.json').read_bytes(),parent_archive_sha256,report['max_iterations'])
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
            and report['model_optimization']=='EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL' and geometry._digest(report['executable_sha256'])
            and report['phenix_version']==source['phenix_version'] and report['executable_sha256']==source['executable_sha256']
            and isinstance(report['executable_provenance'],str) and bool(report['executable_provenance']))
    q,decision,summary=_analysis(root,gradient,parent,report,expected,proof,model,cifs,phils)
    _need(report['qualification']==q and report['coordinate_decision']==decision and report.get('geometry_summary')==summary
        and (report['status']=='RECOVERED_GEOMETRY_ENDPOINT_PASS') is decision['endpoint_usable'])
    return report


def read_recovered_geometry(directory,*,gradient_directory,recovery_directory):
    """Reproduce the saved decision from bound evidence without a native process."""
    try:return _read_recovered_geometry(directory,gradient_directory=gradient_directory,recovery_directory=recovery_directory)
    except (KeyError,TypeError,IndexError,OverflowError) as exc:raise ValueError('Incomplete recovered geometry report') from exc
