"""One owned, bounded ReadySet continuation of a qualified selected runtime.

Existing adapters own source chemistry, lossless serialization and native selection.
This execution is never resumed in place; enclosing requests own durable retries.
"""
import math
from pathlib import Path
from time import monotonic

from .failure_reporting import add_failure_note
from .campaign_records import read_record, write_record, path_in, serialized_record_size
from .cif_attachment_native import _capture, _capture_timeout
from . import cif_component_runtime as frozen_tree
from .cif_component_runtime import _tree, prepare_runtime_readyset_bundle, component_runtime_evidence
from .cif_dictionary_sites import _need, _read, _bind_capture_inputs
from .cif_dictionary_bundle import read_dictionary_bundle
from .cif_dictionary_store import _bytes, _json, _snapshot_destination
from .cif_native_validation import inspect_native_bundle, NATIVE_POLICY_ID
from .cif_native_asu import POLICY_ID as NATIVE_NONBONDED_POLICY, validate_policy as validate_nonbonded_policy
from .cif_outer_context import OuterAllowance, parent_identity
from .cif_postmr_cache import verify_current_consumer
from .cif_postmr_readyset import read_readyset_consumption, WORKER
from .cif_readyset_atom_order import _derive, prepare_readyset_atom_order, read_readyset_atom_order
from .cif_repair_attempt import _members, _root
from .cif_runtime_bundle import resolve_runtime_bundle
from .cif_runtime_readyset import (_parent, _selected_view, audit_runtime_readyset_consumption,
                                  runtime_readyset_endpoint_inputs, inspect_runtime_readyset)
from .cif_runtime_continuation_process import RuntimeContinuationProcesses, inspect_runtime_continuation_processes

POLICY_ID = 'cif-selected-runtime-continuation-execution-v1'
ANCHOR = 'continuation_directory'
ARTIFACT_POLICY = 'cif-continuation-partitioned-artifacts-v1'


class RuntimeContinuationBudgetExceeded(TimeoutError):
    """No allowance remains; preserve the complete or partial fresh execution."""


def _artifact_fields(policy):
    _need(policy is None or (type(policy) is str and policy == ARTIFACT_POLICY),
          'Unsupported continuation artifact policy')
    return {} if policy is None else dict(artifact_policy=policy)


def _native_fields(policy):
    validate_nonbonded_policy(policy, enabled=True)
    return {} if policy is None else dict(nonbonded_policy=policy)


def _configuration(limits, restore_serialization, *, artifact_policy=None, nonbonded_policy=None, compact_evidence=False):
    _need(type(compact_evidence) is bool, 'Require a boolean compact-evidence choice')
    _need(isinstance(limits, dict) and set(limits) == {'native', 'readyset', 'total'}
          and all(type(limits[k]) in (int, float) and math.isfinite(limits[k])
                  and 0 < limits[k] <= cap for k,cap in [('native',600),('readyset',180)])
          and type(limits['total']) is int and 1 <= limits['total'] <= 3600
          and type(restore_serialization) is bool, 'Invalid bounded continuation settings')
    return dict(schema_version=1, policy_id=POLICY_ID, limits=dict(limits),
                restore_serialization=restore_serialization, **(dict(compact_evidence=True) if compact_evidence else {}), **_artifact_fields(artifact_policy),
                **_native_fields(nonbonded_policy))


def _selected_consumer(parent):
    with component_runtime_evidence(parent['manifest_path'].parent,parent['manifest']) as evidence:
        return read_dictionary_bundle(evidence/'evidence/bundle')['report']['consumer']


def _native(root, child, inputs, consumer, *, nonbonded_policy=None):
    """Bind a completed/failed capture to the exact stopped owned invocation."""
    job, finished = child['job'], child['finished']
    _need(child['state'] == 'STOPPED' and 'identity' in child
          and finished['status'] in {'COMPLETED','FAILED','TIMED_OUT'}, 'Native worker is not known stopped')
    receipt = path_in(root, job['cwd']['path'])/'native_receipt.json'
    record, native, snapshots = (_capture_timeout if finished['status'] == 'TIMED_OUT' else _capture)(receipt, _read(inputs['model']))
    execution = record['execution']
    _need(execution['status'] == finished['status'] and type(execution.get('returncode')) is int
          and execution['returncode'] == finished['returncode']
          and execution['timeout_seconds'] == job['timeout_seconds']
          and record['command'] == job['argv_provenance'] and len(record['command']) == 3
          and record['command'][1:] == ['native_worker.py','native_spec.json']
          and record['phenix_version'] == consumer['version']
          and record['executable_sha256'] == consumer['executable_sha256'], 'Native capture and owned job differ')
    _bind_capture_inputs(record, inputs['model'], inputs['dictionaries'], inputs['phils'])
    rows = record['inputs']
    expected = dict(policy_id=NATIVE_POLICY_ID, model=rows[0]['path'],
        dictionaries=[r['path'] for r in rows if r['role'] == 'dictionary'],
        phil_files=[r['path'] for r in rows if r['role'] == 'phil'],
        phil_namespace_policy='refinement-root-to-interpreter-v1', inventory_detail='linked',
        policy_inventory=True, energy_inventory=True, nonbonded_inventory=True, full_monomer_inventory=True,
        **_native_fields(nonbonded_policy))
    _need(_json(_read(receipt.parent/'native_spec.json')) == expected,
          'Continuation native request differs from the maintained context')
    _need(all(_read(p) == data for p,data in snapshots.items()), 'Native proof changed during reading')
    return receipt, finished['status'] == 'COMPLETED' and record['status'] == 'REVIEW'


def _readyset(root, child, parent):
    job, finished = child['job'], child['finished']; directory = root/'readyset'
    _need(child['state'] == 'STOPPED' and 'identity' in child
          and finished['status'] in {'COMPLETED','FAILED','TIMED_OUT'}, 'ReadySet worker is not known stopped')
    report = read_readyset_consumption(directory)['report']; execution = report['execution']
    _need(execution['status'] == finished['status'] and type(execution.get('returncode')) is int
          and execution['returncode'] == finished['returncode']
          and execution['timeout_seconds'] == job['timeout_seconds']
          and job['argv_provenance'][1:] == ['consumption_worker.py','consumption_spec.json']
          and _read(directory/'readyset/consumption_worker.py') == WORKER.encode(),
          'ReadySet observation and owned invocation differ')
    # This binding also applies to failed observations. Successful interpretation
    # still passes the complete shared observer checker below.
    with _selected_view(parent['manifest_path']) as (_, view):
        for name in ('model','source','dictionary'):
            _need(_read(path_in(directory,report['inputs'][name]['path'])) == _read(view[name]),
                  'ReadySet observation used another selected input')
        _need(set(report.get('component_inputs',{})) == set(view['component_dictionaries']), 'ReadySet component owners differ')
        for code,p in view['component_dictionaries'].items():
            _need(_read(path_in(directory,report['component_inputs'][code]['path'])) == _read(p), 'ReadySet component input differs')
    try:
        return runtime_readyset_endpoint_inputs(parent['manifest_path'],directory)
    except (ValueError, OSError, KeyError, TypeError, IndexError):
        return None


def _serialization(parent, inputs, raw, enabled):
    if raw['decision']['selected'] != 'verified_parent_runtime' or raw['endpoint'] is None:
        return dict(status='NOT_NEEDED')
    if not enabled: return dict(status='DISABLED')
    try:
        restored, _ = _derive(_read(parent['model']), _read(inputs['model']))
    except ValueError as exc:
        return dict(status='UNSUPPORTED', reason=str(exc))
    return dict(status='APPLIED' if restored != _read(inputs['model']) else 'UNCHANGED')


def _replay(root, config, state):
    """Reconstruct the prescribed phase chain and exact final public inputs."""
    parent = _parent(root/'inputs/runtime'); consumer = _selected_consumer(parent)
    phases = state['phases']; expected = {'native-baseline'}
    _need('native-baseline' in phases and all(p['state'] == 'STOPPED' for p in phases.values()),
          'Continuation has unknown or unfinished native work')
    for name,p in phases.items():
        _need(p['job']['timeout_seconds'] <= config['limits']['readyset' if name == 'readyset' else 'native'],
              'Continuation worker exceeds its frozen limit')
    native_policy=config.get('nonbonded_policy')
    baseline, usable = _native(root,phases['native-baseline'],parent,consumer,nonbonded_policy=native_policy)
    readyset = endpoint = order = None; serialization = dict(status='NOT_NEEDED'); raw = None
    if usable:
        expected.add('readyset'); _need('readyset' in phases, 'Completed baseline lacks its ReadySet phase')
        readyset = root/'readyset'; inputs = _readyset(root,phases['readyset'],parent)
        if inputs is not None:
            expected.add('native-endpoint'); _need('native-endpoint' in phases, 'Qualified ReadySet observation lacks final native capture')
            endpoint, _ = _native(root,phases['native-endpoint'],inputs,consumer,nonbonded_policy=native_policy)
            raw = inspect_runtime_readyset(parent['manifest_path'],baseline,readyset,endpoint)
            serialization = _serialization(parent,inputs,raw,config['restore_serialization'])
            if serialization['status'] == 'APPLIED':
                expected.add('native-ordered'); _need('native-ordered' in phases, 'Lossless serialization lacks fresh native capture')
                order = root/'atom-order'; read_readyset_atom_order(order)
                ordered = runtime_readyset_endpoint_inputs(parent['manifest_path'],readyset,atom_order_directory=order)
                endpoint, _ = _native(root,phases['native-ordered'],ordered,consumer,nonbonded_policy=native_policy)
    _need(set(phases) == expected and (root/'atom-order').exists() == (order is not None), 'Unexpected continuation phase or serialization')
    review = inspect_runtime_readyset(parent['manifest_path'],baseline,readyset,endpoint,atom_order_directory=order)
    roots = dict(runtime=root/'inputs/runtime', baseline=baseline.parent,
                 readyset=readyset, endpoint=None if endpoint is None else endpoint.parent,
                 **({'atom-order':order} if order is not None else {}))
    return parent, review, serialization, roots


def _continuation_files(root, config):
    _artifact_fields(config.get('artifact_policy'))
    return frozen_tree._bounded_inventory(root,max_files=frozen_tree.MAX_FILES,
        max_bytes=frozen_tree.MAX_BYTES,
        partition_prefixes=('runtime/',) if 'artifact_policy' in config else ())


def _completion_space(root, config, completion):
    files=_continuation_files(root,config)
    working={n:data for n,data in files.items()
             if 'artifact_policy' not in config or not n.startswith('runtime/')}
    size=serialized_record_size(completion)
    _need(len(working)+1 <= frozen_tree.MAX_FILES and size <= frozen_tree.MAX_FILE_BYTES
          and sum(r['size'] for r in working.values())+size <= frozen_tree.MAX_BYTES,
          'Continuation completion exceeds frozen artifact bounds')


def read_runtime_continuation(directory):
    """Replay a completed owned continuation without the SDK or historical paths."""
    root = _root(directory)
    _members(root, {'continuation_execution.json'}, {'inputs','ownership','native','readyset','atom-order','runtime'})
    _members(root/'inputs', {'configuration.json'}, {'runtime'})
    config = _json(_read(root/'inputs/configuration.json'))
    _need(config == _configuration(config.get('limits'),config.get('restore_serialization'),
          artifact_policy=config.get('artifact_policy'),nonbonded_policy=config.get('nonbonded_policy'),
          compact_evidence=config.get('compact_evidence',False)),
          'Continuation configuration differs')
    before = _continuation_files(root,config)
    state = inspect_runtime_continuation_processes(root)
    _need(state['state'] == 'STOPPED' and state['finished']['outcome'] == 'RETURNED', 'Continuation execution did not finish')
    parent, review, serialization, roots = _replay(root,config,state)
    runtime = resolve_runtime_bundle(root/'runtime')
    _need(('evidence_storage' in runtime['manifest']) == config.get('compact_evidence',False),
          'Published continuation storage differs from frozen choice')
    with component_runtime_evidence(root/'runtime',runtime['manifest']) as view:
        evidence = view/'evidence'
        _need({p.name for p in evidence.iterdir()} == {k for k,v in roots.items() if v is not None or k == 'readyset'}, 'Public continuation evidence roots differ')
        for name,p in roots.items():
            if p is not None: _need(_tree(evidence/name) == _tree(p), 'Public continuation copied different evidence')
            elif name == 'readyset': _need(_tree(evidence/name) == {}, 'Unexpected ReadySet evidence')
    _need(runtime['manifest']['decision']['selected'] == review['decision']['selected'], 'Final continuation selection differs')
    report = read_record(root/'continuation_execution.json'); elapsed = report.get('elapsed_seconds')
    _need(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0 <= elapsed < config['limits']['total'], 'Continuation exceeded its recorded allowance')
    expected = _report(root, config, state, runtime, serialization, elapsed)
    _need({k:v for k,v in report.items() if k != 'record_sha256'} == expected, 'Continuation result or frozen artifacts differ')
    _need(_continuation_files(root,config) == before, 'Continuation changed during read-only replay')
    return dict(report=report, runtime=runtime, process_evidence=state, parent=parent)


def _report(root, config, state, runtime, serialization, elapsed):
    files = _continuation_files(root,config); files.pop('continuation_execution.json',None)
    # Completion is published last and independently binds every stopped phase.
    # Excluding that seal avoids a circular result/seal publication dependency.
    files.pop('ownership/finished.json',None)
    return dict(schema_version=1,policy_id=POLICY_ID,status='QUALIFIED_DIAGNOSTIC_CONTINUATION',
        inputs=dict(anchor=ANCHOR,path='inputs'),runtime=dict(anchor=ANCHOR,path='runtime'),
        process_evidence=dict(anchor=ANCHOR,path='ownership/continuation.json'),
        configuration=config, selected=runtime['manifest']['decision']['selected'], serialization=serialization,
        phases={k:p['finished']['status'] for k,p in state['phases'].items()},
        artifacts=files,elapsed_seconds=elapsed,automatic_adoption=False,
        retry_authorized=False,refinement='NOT_RUN',
        scope='ONE_OWNED_EXECUTION; ENCLOSING_REQUEST_OWNS_RECOVERY')


def execute_runtime_continuation(manifest, phenix, output, *, native_timeout_seconds=120,
        readyset_timeout_seconds=120, total_timeout_seconds=900, restore_serialization=True,
        artifact_policy=ARTIFACT_POLICY, nonbonded_policy=NATIVE_NONBONDED_POLICY, compact_evidence=False,
        _attempt_identity=None, _remaining_seconds=None):
    """Run one fresh selected baseline/ReadySet/native/publication chain.

    A known stopped optional failure retains the exact qualified parent. Unknown
    cleanup, interruption, malformed ownership or damaged parent raises with all
    partial work preserved. At most one C140 lossless serialization and separate
    native capture follow a valid but rejected raw comparison; chemistry is never
    changed to make that comparison pass. The shared allowance is cooperative,
    including preflight, native jobs and final replay/publication/inventory.
    New executions freeze separately bounded working and published-runtime trees;
    artifact_policy=None retains the historical flat bound. Completion must fit
    before success is sealed. No old execution is resumed, no retry granted, and
    no checkpoint is replaced. New executions freeze the maintained ASU pair
    policy; nonbonded_policy=None retains the historical C127 native request.
    """
    started = monotonic(); identity = parent_identity(_attempt_identity)
    config = _configuration(dict(native=native_timeout_seconds,readyset=readyset_timeout_seconds,total=total_timeout_seconds),restore_serialization,artifact_policy=artifact_policy,nonbonded_policy=nonbonded_policy,compact_evidence=compact_evidence)
    outer = OuterAllowance(_remaining_seconds,monotonic,RuntimeContinuationBudgetExceeded)
    def remaining():
        left = total_timeout_seconds-(monotonic()-started); cap = outer.remaining()
        if cap is not None: left = min(left,cap)
        if left <= 0: raise RuntimeContinuationBudgetExceeded('Selected-runtime continuation allowance exhausted; preserve partial work')
        return left
    def limit(name): return min(config['limits'][name],remaining())
    parent = _parent(manifest); original = parent['manifest_path'].parent; before = _tree(original)
    output = _snapshot_destination(output).resolve(); installation = Path(phenix.root).resolve()
    _need(all(not output.is_relative_to(p) and not p.is_relative_to(output) for p in (original.resolve(),installation)), 'Continuation output overlaps selected input or installation')
    consumer = _selected_consumer(parent)
    _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer), 'Selected continuation consumer differs')
    remaining(); output.mkdir(parents=True)
    for name,data in before.items():
        p=output/'inputs/runtime'/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
    (output/'inputs/configuration.json').write_bytes(_bytes(config))
    frozen = _parent(output/'inputs/runtime'); processes = RuntimeContinuationProcesses(output,attempt_identity=identity)
    def unchanged():
        _need(_tree(original) == before and _tree(output/'inputs/runtime') == before, 'Selected runtime changed during continuation')
        remaining()
    def capture(label, inputs):
        result=inspect_native_bundle(inputs['model'],inputs['dictionaries'],output/'native'/label,
            phenix.executables['phenix.python'],environment=phenix.environment,phenix_version=phenix.version,
            timeout_seconds=limit('native'),phil_files=inputs['phils'],inventory_detail='linked',
            phil_namespace_policy='refinement-root-to-interpreter-v1',policy_inventory=True,energy_inventory=True,
            nonbonded_inventory=True,nonbonded_policy=nonbonded_policy,full_monomer_inventory=True,
            _process_runner=processes.runner('native-'+label))
        state=inspect_runtime_continuation_processes(output)
        receipt,usable=_native(output,state['phases']['native-'+label],inputs,consumer,nonbonded_policy=nonbonded_policy)
        _need(Path(result['native_directory']).absolute() == receipt.parent, 'Native capture returned a different phase')
        unchanged();return receipt,usable
    try:
        baseline,usable=capture('baseline',frozen);readyset=endpoint=order=None
        if usable:
            readyset=output/'readyset'
            audit_runtime_readyset_consumption(frozen['manifest_path'],phenix,readyset,
                timeout_seconds=limit('readyset'),_process_runner=processes.runner('readyset'))
            unchanged();state=inspect_runtime_continuation_processes(output)
            inputs=_readyset(output,state['phases']['readyset'],frozen)
            if inputs is not None:
                endpoint,_=capture('endpoint',inputs)
                raw=inspect_runtime_readyset(frozen['manifest_path'],baseline,readyset,endpoint)
                serialization=_serialization(frozen,inputs,raw,restore_serialization)
                if serialization['status']=='APPLIED':
                    order=output/'atom-order';prepare_readyset_atom_order(frozen['model'],inputs['model'],order)
                    unchanged();ordered=runtime_readyset_endpoint_inputs(frozen['manifest_path'],readyset,atom_order_directory=order)
                    endpoint,_=capture('ordered',ordered)
        unchanged();state=inspect_runtime_continuation_processes(output)
        _,review,serialization,_=_replay(output,config,state)
        prepare_runtime_readyset_bundle(frozen['manifest_path'],baseline,readyset,output/'runtime',
                                       endpoint_receipt=endpoint,atom_order_directory=order,
                                       **(dict(compact_evidence=True) if compact_evidence else {}))
        runtime=resolve_runtime_bundle(output/'runtime')
        _need(runtime['manifest']['decision']['selected']==review['decision']['selected'], 'Published continuation differs')
        _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer), 'Continuation consumer changed')
        unchanged()
        state=inspect_runtime_continuation_processes(output)
        report=_report(output,config,state,runtime,serialization,0)
        unchanged();report['elapsed_seconds']=monotonic()-started
        saved=write_record(output/'continuation_execution.json',report)
        remaining()
        def reserve(completion):
            _completion_space(output,config,completion)
            remaining()
        _need(processes.finish('RETURNED',before_publish=reserve), 'Continuation workers have unknown cleanup')
        return saved
    except BaseException as exc:
        if not (output/'ownership/finished.json').exists():
            try: processes.finish('RAISED')
            except Exception as seal_error:
                add_failure_note(exc, 'Continuation completion could not be sealed', seal_error)
        raise
