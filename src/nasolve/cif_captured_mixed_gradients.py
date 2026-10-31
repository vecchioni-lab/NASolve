"""Fresh complete-policy derivatives from an authenticated native capture.

Eligibility and probes depend on captured restraints, never residue codes or a
specific recovery ancestry. Numerical consistency does not approve chemistry,
optimize coordinates or grant ordinary Phenix-refinement support.
"""
from hashlib import sha256
import math
import os
from pathlib import Path
import subprocess
import time

from . import cif_mixed_gradient as numerical
from .cif_attachment_native import _capture, _json, _native_atoms
from .cif_attachment_links import _input
from .cif_candidate_usability import energy_inventory_checks
from .cif_fana_junction import _path

POLICY_ID = 'cif-captured-mixed-fixed-gradient-v1'
REPORT = 'captured_mixed_gradients.json'
# Embedded preparation and job artifacts retain the unchanged worker's schema.
ANCHOR = numerical.ANCHOR
MAX_CALLS = numerical.MAX_CALLS
MAX_PAIRS = numerical.MAX_PAIRS


def _need(value):
    if not value:
        raise ValueError('Captured manager derivative evidence does not reproduce')


def _resolve(root, parent, ref):
    if isinstance(ref, dict) and ref.get('anchor') == 'captured_native_directory':
        return numerical._resolve(parent, parent, parent, dict(ref, anchor=ANCHOR))
    _need(isinstance(ref, dict) and ref.get('anchor') == ANCHOR)
    return numerical._resolve(root, parent, parent, ref)


def _inputs(parent):
    parent = _path(parent, directory=True); path = parent/'native_receipt.json'
    raw = _json(path.read_bytes())
    rows = [r for r in raw['inputs'] if r['role'] == 'model']
    _need(len(rows) == 1)
    model = _input(parent, {k:rows[0][k] for k in ('path','sha256','size')} | {'anchor':'manifest_directory'}, {})
    capture, expected, snapshots = _capture(path, model.read_bytes())
    _need(capture['status'] == 'REVIEW' and all(energy_inventory_checks(expected).values()))
    _native_atoms(expected, model.read_bytes())
    spec = _json((parent/'native_spec.json').read_bytes())
    _need(set(spec) <= {'policy_id','model','dictionaries','phil_files','phil_namespace_policy',
        'inventory_detail','policy_inventory','energy_inventory','installed_library_only'}
        and spec.get('policy_inventory') is True and spec.get('energy_inventory') is True)
    dictionaries = [parent/p for p in spec['dictionaries']]; phils = [parent/p for p in spec['phil_files']]
    bind = lambda p:numerical._ref(p,parent,'captured_native_directory')
    bindings = {'active_capture':bind(path),'model':bind(model),
        'dictionaries':[bind(p) for p in dictionaries],'phils':[bind(p) for p in phils]}
    return capture, model, dictionaries, phils, expected, bindings


def _prepare(root, model, dictionaries, phils, expected, capture):
    # Preserve the consumer namespace and dictionary authority. Numerical cores
    # and their original policies stay byte-identical for historical replay.
    preparation = numerical._prepare(root, model, dictionaries, phils, expected)
    path = root/'job/native_spec.json'; spec = _json(path.read_bytes())
    spec['phil_namespace_policy'] = capture['phil_namespace_policy']
    if capture['dictionary_source_policy'] == 'INSTALLED_LIBRARY_ONLY':spec['installed_library_only'] = True
    numerical._compact_dump(path, spec); preparation['native_spec'] = numerical._ref(path, root)
    return preparation


def _publish(root, report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['directories'] = sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())
    report['outputs'] = [numerical._ref(p, root) for p in sorted(root.rglob('*'))
                         if p.is_file() and p != root/REPORT]
    numerical._compact_dump(root/REPORT, report)
    read_captured_mixed_gradients(root)
    return report


def audit_captured_mixed_gradients(native_receipt, phenix, output, *, timeout_seconds=600):
    """Freeze and audit a fixed captured manager; None prepares without execution."""
    from .cif_native_validation import _stop
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=600:raise ValueError('Require a native deadline from 1 to 600 seconds')
    receipt = _path(native_receipt); original = receipt.parent; root = Path(output).expanduser().absolute()
    _need(receipt.name == 'native_receipt.json')
    if root.exists() or any(p.is_symlink() for p in [root,*root.parents]) or root.is_relative_to(original) or original.is_relative_to(root):
        raise ValueError('Require a fresh separate gradient output')
    capture,model,dictionaries,phils,expected,bindings=_inputs(original)
    _,_,snapshots=_capture(receipt,model.read_bytes())
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True)
        before=sha256(executable.read_bytes()).hexdigest()
        _need(phenix.version==capture['phenix_version'] and before==capture['executable_sha256'])
    # Preflight all numerical eligibility before reserving an immutable attempt.
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix='captured-gradient-preflight-') as temporary:
        _prepare(Path(temporary).resolve(),model,dictionaries,phils,expected,capture)
    _need(all(p.read_bytes()==data for p,data in snapshots.items()))
    root.mkdir(parents=True,exist_ok=False); parent=root/'capture'; parent.mkdir()
    for path,data in snapshots.items():
        destination=parent/path.relative_to(original);destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as stream:stream.write(data)
    frozen_capture,model,dictionaries,phils,frozen_expected,frozen_bindings=_inputs(parent)
    _need(capture==frozen_capture and expected==frozen_expected and bindings==frozen_bindings
        and all(p.read_bytes()==data for p,data in snapshots.items()))
    preparation=_prepare(root,model,dictionaries,phils,expected,capture)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':preparation,
        'new_native_calls':0,'maximum_native_calls':1,'timeout_seconds':timeout_seconds,'execution':{'status':'NOT_RUN'},
        'qualification':{'status':'NOT_RUN'},'coordinate_selection':'UNCHANGED_AUTHENTICATED_CAPTURE_INPUT','maximum_energy_calls':MAX_CALLS,'maximum_plane_pairs':MAX_PAIRS,
        'initial_coordinates_only':True,'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','readyset_execution':'NOT_RUN',
        'coot_execution':'NOT_RUN','refinement':'NOT_RUN','cache_writes':'NOT_RUN','captured_code_execution':'NOT_RUN',
        'scientific_qualification':'NOT_ASSESSED','automatic_adoption':False,'requires_cif_review':False,'policy_authority':'CAPTURED_EXPLICIT_POLICY',
        'source_chemical_findings':'NOT_ESTABLISHED_BY_NUMERICAL_CAPTURE'}
    if phenix is not None:
        report.update(status='REVIEW',phenix_version=phenix.version,executable_provenance=str(executable),executable_sha256=before)
        started=time.monotonic()
        try:
            with (root/'job/gradient.log').open('xb') as log:
                process=subprocess.Popen([str(executable),'-B','gradient_worker.py'],cwd=root/'job',env=dict(phenix.environment),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                report['new_native_calls']=1
                try:code=process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:_stop(process);report['execution']={'status':'TIMED_OUT','returncode':process.returncode}
                except BaseException:_stop(process);raise
                else:report['execution']={'status':'COMPLETED' if code==0 else 'FAILED','returncode':code}
            if report['execution']['status']=='COMPLETED':
                result=_json((root/'job/gradient_result.json').read_bytes());q=numerical._validate_result(result,expected,preparation['selected_indices'])
                numerical._compact_dump(root/'qualification.json',q);report['qualification']={'artifact':numerical._ref(root/'qualification.json',root)}
                if q['sampled_derivatives_pass']:report['status']='CAPTURED_MIXED_DERIVATIVES_PASS'
        except (OSError,ValueError,KeyError,TypeError) as exc:
            report['error']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['error']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
        if sha256(executable.read_bytes()).hexdigest()!=before:raise ValueError('Selected native interpreter changed')
    return _publish(root,report)

def _read_captured_mixed_gradients(directory):
    # The frozen capture owns exact inputs, not source chemical approval.
    from .cif_native_validation import _NATIVE_WORKER
    from .cif_candidate_usability import native_energy_worker
    root=_path(directory,directory=True);parent=root/'capture'
    if any(p.is_symlink() for p in [root,*root.parents]):raise ValueError('Unsafe gradient directory')
    report=_json((root/REPORT).read_bytes());_need(report['policy_id']==POLICY_ID and type(report['schema_version']) is int and report['schema_version']==1
        and report['status'] in {'PREPARED_ONLY','REVIEW','CAPTURED_MIXED_DERIVATIVES_PASS'} and report['initial_coordinates_only'] is True
        and report['automatic_adoption'] is False and report['requires_cif_review'] is False and report['scientific_qualification']=='NOT_ASSESSED'
        and report['policy_authority']=='CAPTURED_EXPLICIT_POLICY' and report['coordinate_selection']=='UNCHANGED_AUTHENTICATED_CAPTURE_INPUT'
        and report['source_chemical_findings']=='NOT_ESTABLISHED_BY_NUMERICAL_CAPTURE'
        and all(report[k]=='NOT_RUN' for k in ['model_optimization','dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution'])
        and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600)
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,parent,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    directories = {parent.as_posix() for name in actual for parent in Path(name).parents if parent != Path('.')}
    _need(report['directories']==sorted(directories)
        and report['directories']==sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()))
    capture,model,dictionaries,phils,expected,bindings=_inputs(parent);_need(report['inputs']==bindings)
    prep=report['preparation'];work=root/'job'
    _need((work/'native_worker.py').read_bytes()==native_energy_worker(_NATIVE_WORKER).encode() and (work/'gradient_worker.py').read_bytes()==numerical._WORKER.encode())
    for name,source in numerical._CORE_FILES.items():_need((work/name).read_bytes()==Path(__file__).with_name(source).read_bytes())
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix='mixed-gradient-reader-') as temporary:
        replay=Path(temporary).resolve();fresh=_prepare(replay,model,dictionaries,phils,expected,capture);_need(prep==fresh)
        prepared = {p.relative_to(replay).as_posix() for p in replay.rglob('*') if p.is_file()}
        for name in prepared:_need((root/name).read_bytes()==(replay/name).read_bytes())
    allowed = prepared | {'capture/native_receipt.json'} | {'capture/'+r['path'] for r in capture['outputs']}
    if report['execution']['status'] != 'NOT_RUN':
        allowed |= {'job/'+name for name in ['gradient.log','native_validation.json','gradient_result.json',
            'native_effective.phil','installed_source/parallelity.h','installed_source/parallelity_bpl.cpp']}
        allowed |= {f'job/canonical_{i:03d}.phil' for i in range(len(phils))}
    if 'artifact' in report['qualification']:allowed.add('qualification.json')
    _need(actual <= allowed)
    _need(all(type(report[k]) is int for k in ['maximum_native_calls','maximum_energy_calls','maximum_plane_pairs']) and report['maximum_native_calls']==1 and report['maximum_energy_calls']==MAX_CALLS and report['maximum_plane_pairs']==MAX_PAIRS
        and type(report['new_native_calls']) is int and report['new_native_calls'] in {0,1})
    q=None
    if 'artifact' in report['qualification']:
        _need(report['new_native_calls']==1 and report['execution']['status']=='COMPLETED' and report['execution']['returncode']==0)
        _need(report['qualification']=={'artifact':numerical._ref(root/'qualification.json',root)})
        q=_json(_resolve(root,parent,report['qualification']['artifact']).read_bytes())
        result=_json((work/'gradient_result.json').read_bytes());native=_json((work/'native_validation.json').read_bytes())
        from .cif_corrected_geometry import QUALIFIED_CORRECTION_SHA256
        _need(numerical._manager_digest(native)==numerical._manager_digest(expected) and result['manager_sha256']==numerical._manager_digest(expected)
            and result['coordinates_unchanged'] is True and result['special_position_indices']==[]
            and result['correction_core_sha256']==QUALIFIED_CORRECTION_SHA256
            and native['energy_inventory']['installed_sources']==expected['energy_inventory']['installed_sources']
            and numerical._numeric_equal(native['energy_inventory'],expected['energy_inventory'])
            and numerical._numeric_equal(result['raw_snapshot'],native['energy_inventory']['snapshots'][0]))
        _need(numerical._numeric_equal(q,numerical._validate_result(result,expected,prep['selected_indices'])))
        for field,modules in [('installed_numeric_sources',numerical._NUMERIC),('installed_adapter_sources',numerical._ADAPTERS)]:
            rows=result[field]
            _need([r['module'] for r in rows]==list(modules) and all(isinstance(r['sha256'],str) and len(r['sha256'])==64
                and all(c in '0123456789abcdef' for c in r['sha256']) and isinstance(r['historical_path'],str) and bool(r['historical_path']) for r in rows)
                and result[field+'_after']==rows)
        pins={r['module']:r['sha256'] for field in ['installed_numeric_sources','installed_adapter_sources'] for r in result[field]}
        _need(all(r['module'] in pins and pins[r['module']]==r['sha256'] for r in expected['energy_inventory']['installed_sources']))
        _need(len(result['installed_parallelity_sources'])==2 and {r['path'] for r in result['installed_parallelity_sources']}=={'parallelity.h','parallelity_bpl.cpp'})
        for row in result['installed_parallelity_sources']:
            data=(work/'installed_source'/row['path']).read_bytes();_need(row=={'path':row['path'],'bytes':len(data),'sha256':sha256(data).hexdigest(),'status':'RECORDED'})
    else:_need(report['qualification']=={'status':'NOT_RUN'})
    if report['new_native_calls']==0:
        _need(q is None and ((report['status']=='PREPARED_ONLY' and report['execution']=={'status':'NOT_RUN'})
            or (report['status']=='REVIEW' and report['execution'].get('status')=='LAUNCH_FAILED'
                and isinstance(report['execution'].get('error'),str) and bool(report['execution']['error'])
                and type(report['execution'].get('elapsed_seconds')) in (int,float)
                and math.isfinite(report['execution']['elapsed_seconds']) and report['execution']['elapsed_seconds']>=0)))
    else:
        execution=report['execution'];state=execution['status'];code=execution['returncode']
        _need(report['status']!='PREPARED_ONLY' and state in {'COMPLETED','FAILED','TIMED_OUT'}
            and type(code) is int and (state!='COMPLETED' or code==0) and (state!='FAILED' or code!=0)
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0
            and report['phenix_version']==capture['phenix_version'] and report['executable_sha256']==capture['executable_sha256']
            and isinstance(report['executable_provenance'],str) and bool(report['executable_provenance'])
            and isinstance(report['executable_sha256'],str) and len(report['executable_sha256'])==64
            and all(c in '0123456789abcdef' for c in report['executable_sha256']))
    if report['execution']['status']=='COMPLETED' and q is None:
        _need(isinstance(report.get('error'),str) and bool(report['error']))
    passed=q is not None and q['sampled_derivatives_pass'] is True
    _need((report['status']=='CAPTURED_MIXED_DERIVATIVES_PASS')==passed)
    return report


def read_captured_mixed_gradients(directory):
    """Read only maintained sources and saved evidence, never launch an SDK."""
    try:return _read_captured_mixed_gradients(directory)
    except (KeyError,TypeError,IndexError) as exc:raise ValueError('Incomplete captured manager gradient report') from exc
