"""Read-only torsion diagnosis of a source-recovered geometry attempt.

The established fixed-coordinate worker, selection and numerical replay policy
remain unchanged. This adapter binds them to the recovered objective and carries
its prior coordinate decision without requalifying or adopting the endpoint.
"""
from copy import deepcopy
from hashlib import sha256
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from . import cif_mixed_torsion as torsion
from . import cif_mixed_geometry as legacy_geometry
from . import cif_recovered_geometry as geometry
from . import cif_mixed_source_recovery as recovery

POLICY_ID = 'cif-recovered-mixed-fixed-torsion-v1'
REPORT = 'recovered_torsion_audit.json'
ANCHOR = torsion.ANCHOR
GEOMETRY_ANCHOR = 'recovered_geometry_directory'
ARCHIVE_VERIFICATION = 'MAINTAINED_C100_C99_C98_READERS; EXACT_RECOVERY_CAPSULE_BYTES'
SOURCE_SCOPE = 'PRESERVED_IN_BOUND_RECOVERY; NOT_PROMOTED_BY_DIAGNOSTIC'
MAX_PAIRS, MAX_GROUP_CALLS = torsion.MAX_PAIRS, torsion.MAX_GROUP_CALLS
_ref, _load, _dump, _digest = torsion._ref, torsion._load, torsion._dump, torsion._digest
_prepare, _analysis = torsion._prepare, torsion._analysis


def _need(value):
    if not value:
        raise ValueError('Recovered torsion evidence does not reproduce')


def _resolve(root, endpoint, gradient, parent, ref):
    if isinstance(ref, dict) and ref.get('anchor') == recovery.ANCHOR:
        return recovery._resolve(parent, ref)
    from .cif_mixed_recovery import _safe
    anchors = {ANCHOR: root, GEOMETRY_ANCHOR: endpoint, geometry.GRADIENT_ANCHOR: gradient}
    _need(isinstance(ref, dict) and ref.get('anchor') in anchors and _safe(ref.get('path')))
    directory = anchors[ref['anchor']]; path = directory/ref['path']
    _need(_ref(path, directory, ref['anchor']) == ref)
    return path


def _inputs(endpoint, gradient, parent):
    source = geometry.read_recovered_geometry(endpoint, gradient_directory=gradient, recovery_directory=parent)
    _need(source['execution']['status'] == 'COMPLETED' and source['new_native_calls'] >= 1)
    # The maintained parent reader has already replayed C99 and C98. Resolve its
    # verified resources, keeping each genuine anchor instead of inventing an
    # archive identity for this three-directory lineage.
    bindings = source['inputs']
    path = lambda ref: recovery._resolve(parent, ref)
    expected = _load(path(bindings['active_capture']))['native_validation']
    result = legacy_geometry._completed_result(endpoint, expected)
    proof = _load(gradient/'job/gradient_result.json')
    final = result['final_sites_cart']
    cases = {'initial': expected['geometry']['sites_cart_exact'], 'full_precision': final,
        'pdb_rounded': [[float('%.3f'%v) for v in point] for point in final]}
    _need(torsion._points(cases) == expected['atom_count'])
    references = {'initial': proof['gradient_audit']['cases']['initial']['families']['dihedral']['baseline'],
        **{name: result['endpoint_gradient_audit']['cases'][name]['families']['dihedral']['baseline']
           for name in ['full_precision', 'pdb_rounded']}}
    _need(result['constraint_signature_before'] == result['constraint_signature_after'] == proof['constraint_signature_before']
        and result['installed_optimizer_sources'] == proof['installed_numeric_sources']
        and result['installed_adapter_sources'] == proof['installed_adapter_sources'])
    plan = torsion.select_torsions(expected, cases, {name: row['gradient'] for name, row in references.items()})
    bindings = {**bindings, 'geometry_report': _ref(endpoint/geometry.REPORT, endpoint, GEOMETRY_ANCHOR),
        'geometry_result': _ref(endpoint/'job/geometry_result.json', endpoint, GEOMETRY_ANCHOR),
        'expected_inventory': _ref(endpoint/'job/expected_inventory.json', endpoint, GEOMETRY_ANCHOR)}
    return (source, path(bindings['model']), [path(ref) for ref in bindings['dictionaries']],
        [path(ref) for ref in bindings['phils']], expected, proof, cases, references, plan, bindings)


def _publish(root,endpoint,gradient,parent,report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['outputs']=[_ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT]
    _dump(root/REPORT,report);read_recovered_torsions(root,geometry_directory=endpoint,gradient_directory=gradient,recovery_directory=parent);return report


def audit_recovered_torsions(geometry_directory,gradient_directory,recovery_directory,phenix,output,*,timeout_seconds=120):
    from .cif_native_validation import _stop
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=600:raise ValueError('Require a native deadline from 1 to 600 seconds')
    endpoint,gradient,parent=map(Path,(geometry_directory,gradient_directory,recovery_directory));root=Path(output).absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root,*root.parents]) and not any(root.resolve().is_relative_to(p.resolve()) for p in [endpoint,gradient,parent]))
    source,model,cifs,phils,expected,proof,cases,references,plan,bindings=_inputs(endpoint,gradient,parent)
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True);fingerprint=sha256(executable.read_bytes()).hexdigest()
        _need(fingerprint==source['executable_sha256'] and phenix.version==source['phenix_version'])
    root.mkdir(parents=True)
    prep=_prepare(root,model,cifs,phils,expected,proof,cases,references,plan)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':prep,'parent_archive_sha256':source['parent_archive_sha256'],
        'parent_archive_verification':ARCHIVE_VERIFICATION,
        'maximum_native_calls':1,'new_native_calls':0,'timeout_seconds':timeout_seconds,'maximum_evaluation_pairs':MAX_PAIRS,'maximum_group_calls':MAX_GROUP_CALLS,
        'execution':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},'coordinate_decision':deepcopy(source['coordinate_decision']),
        'original_geometry_status':source['status'],'original_geometry_qualification':deepcopy(source['qualification']),
        'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','readyset_execution':'NOT_RUN','coot_execution':'NOT_RUN','refinement':'NOT_RUN',
        'cache_writes':'NOT_RUN','captured_code_execution':'NOT_RUN','endpoint_requalification':'NOT_RUN','scientific_qualification':'NOT_ASSESSED',
        'automatic_adoption':False,'requires_cif_review':False,'policy_authority':'NARestraints','source_chemical_findings':SOURCE_SCOPE}
    if phenix is not None:
        _need(sha256(executable.read_bytes()).hexdigest()==fingerprint)
        report.update(status='REVIEW',phenix_version=phenix.version,executable_provenance=str(executable),executable_sha256=fingerprint);started=time.monotonic()
        try:
            with (root/'job/torsion.log').open('xb') as log:
                process=subprocess.Popen([str(executable),'-B','torsion_worker.py'],cwd=root/'job',env=dict(phenix.environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                report['new_native_calls']=1
                try:code=process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:_stop(process);report['execution']={'status':'TIMED_OUT','returncode':process.returncode}
                except BaseException as exc:
                    _stop(process);report['execution']={'status':'WAIT_FAILED','returncode':process.returncode,'error_type':type(exc).__name__};raise
                else:report['execution']={'status':'COMPLETED' if code==0 else 'FAILED','returncode':code}
        except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError) as exc:
            report['optional_finding']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['optional_finding']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6);_need(sha256(executable.read_bytes()).hexdigest()==fingerprint)
        report['qualification']=_analysis(root,report,expected,proof,cases,references,plan)
        if report['qualification']['status']=='MIXED_TORSION_AUDIT_COMPLETE':report['status']='RECOVERED_MIXED_TORSION_AUDIT_COMPLETE';report['summary']=report['qualification']['summary']
    return _publish(root,endpoint,gradient,parent,report)


def _read_recovered_torsions(directory,*,geometry_directory,gradient_directory,recovery_directory):
    root,endpoint,gradient,parent=map(Path,(directory,geometry_directory,gradient_directory,recovery_directory));report=_load(root/REPORT)
    _need(not any(p.is_symlink() for p in [root,*root.parents]))
    _need(_digest(report['parent_archive_sha256']) and report['schema_version']==1 and report['policy_id']==POLICY_ID
        and report['status'] in {'PREPARED_ONLY','REVIEW','RECOVERED_MIXED_TORSION_AUDIT_COMPLETE'} and type(report['schema_version']) is int
        and type(report['maximum_native_calls']) is int and report['maximum_native_calls']==1
        and type(report['new_native_calls']) is int and report['new_native_calls'] in [0,1] and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600
        and report['maximum_evaluation_pairs']==MAX_PAIRS and report['maximum_group_calls']==MAX_GROUP_CALLS
        and report['automatic_adoption'] is False and report['requires_cif_review'] is False and report['policy_authority']=='NARestraints'
        and report['parent_archive_verification']==ARCHIVE_VERIFICATION
        and report['source_chemical_findings']==SOURCE_SCOPE
        and report['scientific_qualification']=='NOT_ASSESSED' and all(report[k]=='NOT_RUN' for k in ['model_optimization','dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution','endpoint_requalification']))
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,endpoint,gradient,parent,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    source,model,cifs,phils,expected,proof,cases,references,plan,bindings=_inputs(endpoint,gradient,parent)
    _need(report['parent_archive_sha256']==source['parent_archive_sha256'] and report['inputs']==bindings and report['coordinate_decision']==source['coordinate_decision'] and report['original_geometry_status']==source['status'] and report['original_geometry_qualification']==source['qualification'])
    with tempfile.TemporaryDirectory(prefix='mixed-torsion-reader-') as temporary:
        replay=Path(temporary).resolve();prep=_prepare(replay,model,cifs,phils,expected,proof,cases,references,plan);_need(prep==report['preparation'])
        for p in replay.rglob('*'):
            if p.is_file():_need((root/p.relative_to(replay)).read_bytes()==p.read_bytes())
    execution=report['execution'];state=execution['status']
    if report['new_native_calls']==0:
        _need((report['status']=='PREPARED_ONLY' and execution=={'status':'NOT_RUN'}) or (report['status']=='REVIEW' and state=='LAUNCH_FAILED' and isinstance(execution['error'],str)))
    else:
        _need(report['status']!='PREPARED_ONLY' and state in {'COMPLETED','FAILED','TIMED_OUT','WAIT_FAILED'} and type(execution['returncode']) is int
            and (state!='COMPLETED' or execution['returncode']==0) and (state!='FAILED' or execution['returncode']!=0)
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0
            and _digest(report['executable_sha256']))
    if state!='NOT_RUN':
        _need(report['executable_sha256']==source['executable_sha256'] and report['phenix_version']==source['phenix_version']
            and isinstance(report['executable_provenance'],str) and bool(report['executable_provenance']))
    q=_analysis(root,report,expected,proof,cases,references,plan)
    _need(report['qualification']==q and report.get('summary')==q.get('summary') and (report['status']=='RECOVERED_MIXED_TORSION_AUDIT_COMPLETE') is (q['status']=='MIXED_TORSION_AUDIT_COMPLETE'))
    return report


def read_recovered_torsions(directory,*,geometry_directory,gradient_directory,recovery_directory):
    """Replay saved diagnostics and preserve the prior decision without an SDK."""
    try:return _read_recovered_torsions(directory,geometry_directory=geometry_directory,
        gradient_directory=gradient_directory,recovery_directory=recovery_directory)
    except (KeyError,TypeError,IndexError,OverflowError) as exc:raise ValueError('Incomplete recovered torsion report') from exc
