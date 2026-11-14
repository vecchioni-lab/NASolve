"""Fixed-coordinate resolution diagnostics for a recovered objective.

Reuse the maintained resolution-window worker and strict prerequisites. This
adapter records fresh evidence without selecting or requalifying an endpoint.
"""
from copy import deepcopy
from hashlib import sha256
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from . import cif_mixed_endpoint_window as window
from . import cif_mixed_torsion as torsion
from . import cif_mixed_geometry as legacy_geometry
from . import cif_recovered_torsion as recovered
from . import cif_recovered_geometry as geometry
from . import cif_mixed_source_recovery as recovery

POLICY_ID = 'cif-recovered-fixed-resolution-diagnostic-v1'
REPORT = 'recovered_resolution_audit.json'
ANCHOR = window.ANCHOR
TORSION_ANCHOR = 'recovered_torsion_directory'
ARCHIVE_VERIFICATION = 'MAINTAINED_C101_C100_C99_C98_READERS; EXACT_RECOVERY_CAPSULE_BYTES'
SOURCE_SCOPE = 'PRESERVED_IN_BOUND_RECOVERY; NOT_PROMOTED_BY_DIAGNOSTIC'
_ref, _load, _dump, _digest = window._ref, window._load, window._dump, window._digest


def _need(value):
    if not value:
        raise ValueError('Recovered resolution evidence does not reproduce')


def _resolve(root, ref):
    from .cif_mixed_recovery import _safe
    _need(isinstance(ref, dict) and ref.get('anchor') == ANCHOR and _safe(ref.get('path')))
    path = root/ref['path']
    _need(_ref(path, root) == ref)
    return path


def _inputs(torsions, endpoint, gradient, parent):
    source = recovered.read_recovered_torsions(torsions, geometry_directory=endpoint,
        gradient_directory=gradient, recovery_directory=parent)
    _need(source['status'] == 'RECOVERED_MIXED_TORSION_AUDIT_COMPLETE' and source['execution']['status'] == 'COMPLETED')
    # C101 has already replayed C100/C99/C98. Resolve the same verified resources
    # and preserve their genuine anchors without replaying the ancestry twice.
    bindings = source['inputs']; path = lambda ref: recovery._resolve(parent, ref)
    expected = _load(path(bindings['active_capture']))['native_validation']
    proof = _load(gradient/'job/gradient_result.json')
    result = legacy_geometry._completed_result(endpoint, expected)
    old = _load(endpoint/geometry.REPORT)
    _need(result['policy_id'] == legacy_geometry.POLICY_ID and result['status'] == 'REVIEW'
        and result['captured_inventory_matches'] is True and result['qualified_initial_snapshot_matches'] is True
        and result['policy_inventory'] is True and result['normalization'] is False and result['automatic_adoption'] is False
        and result['starting_coordinates'] == 'CAPTURED_INITIAL' and result['special_position_count'] == 0
        and result['constraint_signature_before'] == result['constraint_signature_after'] == proof['constraint_signature_before']
        and result['correction_policy_id'] == proof['correction_policy_id']
        and result['derivative_precondition'] == 'SAMPLED_NATIVE_DERIVATIVES_PASS')
    for new,key in [('installed_optimizer_sources','installed_numeric_sources'),('installed_adapter_sources','installed_adapter_sources'),
                    ('installed_parallelity_sources','installed_parallelity_sources')]:
        _need(result[new] == proof[key])
    for key in ['target','gradient_norm']:
        _need(window._close(result['initial'][key], proof['gradient_audit']['cases']['initial']['families']['all']['baseline'][key]))
    iterations = old['max_iterations']
    _need(result['termination_parameters'] == {'max_iterations':iterations,'max_calls':iterations*20,
        'traditional_convergence_test':True,'traditional_convergence_test_eps':1e-5}
        and result['derivative_validation_archive'] == old['parent_archive_sha256'])
    stop = result['stopping']
    _need(all(type(stop[k]) is int and stop[k] >= 0 for k in ['iterations','calls','max_iterations']) and stop['max_iterations'] == iterations
        and isinstance(stop['reason'], str) and type(stop['native_criterion_met']) is bool and (stop['error'] is None or isinstance(stop['error'], str)))
    final = result['final_sites_cart']
    cases = {'initial':expected['geometry']['sites_cart_exact'],'full_precision':final,
        'pdb_rounded':[[float('%.3f'%v) for v in point] for point in final]}
    _need(torsion._points(cases) == expected['atom_count'])
    references = {'initial':proof['gradient_audit']['cases']['initial']['families']['dihedral']['baseline'],
        **{name:result['endpoint_gradient_audit']['cases'][name]['families']['dihedral']['baseline'] for name in ['full_precision','pdb_rounded']}}
    selection = torsion.select_torsions(expected, cases, {name:row['gradient'] for name,row in references.items()})
    raw = _load(torsions/'job/torsion_result.json')
    plan = window.refinement_plan(result, proof, raw, cases)
    bindings = {**bindings,'torsion_report':_ref(torsions/recovered.REPORT, torsions, TORSION_ANCHOR),
        'torsion_result':_ref(torsions/'job/torsion_result.json', torsions, TORSION_ANCHOR)}
    return (source, path(bindings['model']), [path(ref) for ref in bindings['dictionaries']],
        [path(ref) for ref in bindings['phils']], expected, proof, cases, references, selection, plan, bindings)


def _summary(audit, plan):
    """Describe fresh samples separately from carried prerequisites and selection."""
    groups = {}
    for row in audit['local']:
        selected = row['selection']; key = (selected['case'], window._hash(selected['proxy']))
        group = groups.setdefault(key, {'case':selected['case'],'proxy':selected['proxy'],'orders':{}})
        previous = group['orders'].setdefault(selected['order'], row['baseline'])
        _need(window._same(previous, row['baseline']))
    reversals = []
    for key,group in sorted(groups.items()):
        row = {'case':group['case'],'proxy':group['proxy'],'orders_observed':sorted(group['orders'])}
        if set(group['orders']) == {'forward','reversed'}:
            forward,reverse = group['orders']['forward'],group['orders']['reversed']; comparisons = {}
            for kind in ['single','accumulated']:
                a,b = forward[kind+'_gradient'], reverse[kind+'_gradient']
                reordered = [v for i in [9,6,3,0] for v in b[i:i+3]]
                comparisons[kind] = {'target_difference':abs(forward[kind+'_target']-reverse[kind+'_target']),
                    'maximum_gradient_component_difference':max(abs(x-y) for x,y in zip(a,reordered)),
                    'forward_gradient_norm':window._norm(a),'reversed_gradient_norm':window._norm(reordered),
                    'consistent':window._close(forward[kind+'_target'],reverse[kind+'_target']) and all(window._close(x,y) for x,y in zip(a,reordered))}
            row.update(status='PASS' if all(v['consistent'] for v in comparisons.values()) else 'REVIEW',
                comparisons=comparisons,comparison_tolerance={'absolute':1e-8,'relative':1e-10})
        else:
            row['status'] = 'NOT_SAMPLED_IN_BOTH_ORDERS'
        reversals.append(row)
    return {**deepcopy(audit['summary']),
        'passing_local_directions':sum(all(r['checks'].values()) and r['single']['consistent'] and r['accumulated']['consistent'] for r in audit['local']),
        'passing_family_directions':sum(r['evidence']['consistent'] for r in audit['families']),
        'failed_prerequisites':sorted(k for k,v in plan['prerequisites'].items() if not v),
        'failed_checks':sorted(k for k,v in audit['checks'].items() if not v),
        'fresh_local_reversals':reversals,'endpoint_requalification':'NOT_RUN','automatic_adoption':False}


def _analysis(root, report, expected, proof, cases, plan):
    if report['execution']['status'] != 'COMPLETED':
        return {'status':'NOT_RUN'},None
    try:
        result = _load(root/'job/endpoint_result.json')
        qualification = window._validate_result(root, result, expected, proof, cases, plan)
        return qualification,_summary(result['audit'], plan)
    except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError,ZeroDivisionError) as exc:
        return {'status':'REVIEW','finding_type':type(exc).__name__,'finding':'OPTIONAL_RESOLUTION_EVIDENCE_INCOMPLETE'},None


def _publish(root,torsions,endpoint,gradient,parent,report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['outputs']=[_ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT]
    _dump(root/REPORT,report);read_recovered_resolution(root,torsion_directory=torsions,geometry_directory=endpoint,gradient_directory=gradient,recovery_directory=parent);return report


def audit_recovered_resolution(torsion_directory,geometry_directory,gradient_directory,recovery_directory,phenix,output,*,timeout_seconds=120):
    from .cif_native_validation import _stop
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=600:raise ValueError('Require a native deadline from 1 to 600 seconds')
    torsions,endpoint,gradient,parent=map(Path,(torsion_directory,geometry_directory,gradient_directory,recovery_directory));root=Path(output).absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root,*root.parents]) and not any(root.resolve().is_relative_to(p.resolve()) for p in [torsions,endpoint,gradient,parent]))
    source,model,cifs,phils,expected,proof,cases,references,selection,plan,bindings=_inputs(torsions,endpoint,gradient,parent)
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True);fingerprint=sha256(executable.read_bytes()).hexdigest()
        _need(fingerprint==source['executable_sha256'] and phenix.version==source['phenix_version'])
    root.mkdir(parents=True)
    prep=window._prepare(root,model,cifs,phils,expected,proof,cases,references,selection,plan)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':prep,'parent_archive_sha256':source['parent_archive_sha256'],
        'parent_archive_verification':ARCHIVE_VERIFICATION,
        'maximum_native_calls':1,'new_native_calls':0,'timeout_seconds':timeout_seconds,'maximum_evaluations':window.MAX_EVALUATIONS,'maximum_directions':window.MAX_DIRECTIONS,
        'execution':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},'coordinate_decision':deepcopy(source['coordinate_decision']),
        'original_geometry_status':source['original_geometry_status'],'original_geometry_qualification':deepcopy(source['original_geometry_qualification']),
        'original_torsion_status':source['status'],
        'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','readyset_execution':'NOT_RUN','coot_execution':'NOT_RUN','refinement':'NOT_RUN',
        'cache_writes':'NOT_RUN','captured_code_execution':'NOT_RUN','endpoint_requalification':'NOT_RUN','scientific_qualification':'NOT_ASSESSED',
        'automatic_adoption':False,'requires_cif_review':False,'policy_authority':'NARestraints','source_chemical_findings':SOURCE_SCOPE}
    if phenix is not None:
        _need(sha256(executable.read_bytes()).hexdigest()==fingerprint)
        report.update(status='REVIEW',phenix_version=phenix.version,executable_provenance=str(executable),executable_sha256=fingerprint);started=time.monotonic()
        try:
            with (root/'job/resolution.log').open('xb') as log:
                process=subprocess.Popen([str(executable),'-B','endpoint_worker.py'],cwd=root/'job',env=dict(phenix.environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
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
        qualification,summary=_analysis(root,report,expected,proof,cases,plan)
        report['qualification']=qualification
        if summary is not None:report['status']='RECOVERED_RESOLUTION_AUDIT_COMPLETE';report['summary']=summary
    return _publish(root,torsions,endpoint,gradient,parent,report)


def _read_recovered_resolution(directory,*,torsion_directory,geometry_directory,gradient_directory,recovery_directory):
    root,torsions,endpoint,gradient,parent=map(Path,(directory,torsion_directory,geometry_directory,gradient_directory,recovery_directory));report=_load(root/REPORT)
    _need(not any(p.is_symlink() for p in [root,*root.parents]))
    _need(_digest(report['parent_archive_sha256']) and report['schema_version']==1 and report['policy_id']==POLICY_ID
        and report['status'] in {'PREPARED_ONLY','REVIEW','RECOVERED_RESOLUTION_AUDIT_COMPLETE'} and type(report['schema_version']) is int
        and type(report['maximum_native_calls']) is int and report['maximum_native_calls']==1
        and type(report['new_native_calls']) is int and report['new_native_calls'] in [0,1] and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600
        and report['maximum_evaluations']==window.MAX_EVALUATIONS and report['maximum_directions']==window.MAX_DIRECTIONS
        and report['automatic_adoption'] is False and report['requires_cif_review'] is False and report['policy_authority']=='NARestraints'
        and report['parent_archive_verification']==ARCHIVE_VERIFICATION
        and report['source_chemical_findings']==SOURCE_SCOPE
        and report['scientific_qualification']=='NOT_ASSESSED' and all(report[k]=='NOT_RUN' for k in ['model_optimization','dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution','endpoint_requalification']))
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    source,model,cifs,phils,expected,proof,cases,references,selection,plan,bindings=_inputs(torsions,endpoint,gradient,parent)
    _need(report['parent_archive_sha256']==source['parent_archive_sha256'] and report['inputs']==bindings and report['coordinate_decision']==source['coordinate_decision'] and report['original_geometry_status']==source['original_geometry_status'] and report['original_geometry_qualification']==source['original_geometry_qualification'] and report['original_torsion_status']==source['status'])
    with tempfile.TemporaryDirectory(prefix='mixed-torsion-reader-') as temporary:
        replay=Path(temporary).resolve();prep=window._prepare(replay,model,cifs,phils,expected,proof,cases,references,selection,plan);_need(prep==report['preparation'])
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
    q,summary=_analysis(root,report,expected,proof,cases,plan)
    _need(report['qualification']==q and report.get('summary')==summary and (report['status']=='RECOVERED_RESOLUTION_AUDIT_COMPLETE') is (summary is not None))
    return report


def read_recovered_resolution(directory,*,torsion_directory,geometry_directory,gradient_directory,recovery_directory):
    """Reproduce resolution evidence and the unchanged selection without an SDK."""
    try:return _read_recovered_resolution(directory,torsion_directory=torsion_directory,
        geometry_directory=geometry_directory,gradient_directory=gradient_directory,recovery_directory=recovery_directory)
    except (KeyError,TypeError,IndexError,OverflowError) as exc:raise ValueError('Incomplete recovered resolution report') from exc
