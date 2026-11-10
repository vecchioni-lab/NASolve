"""Frozen prepared-repair requests with finite immutable explicit attempts.

All callers for one logical request must share its directory. This owns prepared
execution only; discovery, acquisition, scientific selection and adoption remain
separate. Readers observe state but never lock, signal, repair or authorize retry.
"""
from hashlib import sha256
import os
from pathlib import Path
import uuid
from time import monotonic

from .failure_reporting import add_failure_note
from .campaign_process import CampaignProcessError, coordinator_alive, current_process_identity, exclusive_lock
from .campaign_records import _sync_directory, now, path_in, read_record, write_record
from .cif_component_runtime import _tree
from .cif_dictionary_store import _json, _bytes
from .cif_dictionary_sites import _read
from .cif_dictionary_bundle import read_dictionary_bundle
from .cif_generation_process import _valid_identity, _valid_attempt_identity
from .cif_outer_context import OuterAllowance, parent_identity
from .cif_generation_attempt import _attempt_identity
from .cif_postmr_cache import verify_current_consumer
from .cif_prepared_repair_execution import execute_prepared_dictionary_repair, POLICY_ID as EXECUTION_POLICY, PreparedRepairBudgetExceeded
from .cif_repair_process import inspect_prepared_repair_processes, _uuid, POLICY_ID as PROCESS_POLICY
from .cif_prepared_repair_failure import inspect_prepared_native_failure, failure_policy_fields, FALLBACK_POLICY_ID

POLICY_ID = 'cif-prepared-repair-request-v1'
ANCHOR = 'request_directory'
_LIMITS = {'native_timeout_seconds':600, 'attribution_timeout_seconds':300,
           'derivative_timeout_seconds':600, 'total_timeout_seconds':3600}


def _need(value, message='Invalid prepared repair request evidence'):
    if not value:
        raise ValueError(message)


def _root(path):
    path = Path(path).absolute()
    _need(not any(p.is_symlink() or (p.exists() and not p.is_dir()) for p in (path,*path.parents)),
          'Prepared repair request requires regular directory ancestors')
    return path.resolve()


def _members(path, files, directories):
    for p in path.iterdir():
        _need(not p.is_symlink() and ((p.name in directories and p.is_dir()) or
              (p.is_file() and (p.name in files or p.name.startswith('.record-')))),
              'Unexpected prepared repair request member: '+p.name)


def _digest(data):
    return {'sha256':sha256(data).hexdigest(), 'size':len(data)}


def _inventory(tree):
    return {name:_digest(data) for name,data in tree.items()}


def _configuration(tree, limits, max_attempts, *, qualify_no_repair=False, optional_failure_policy=None):
    _need(type(qualify_no_repair) is bool, "Require a boolean no-repair qualification mode")
    _need(set(limits) == set(_LIMITS) and all(type(v) is int and 1 <= v <= _LIMITS[k]
          for k,v in limits.items()), 'Require bounded integer repair deadlines')
    _need(type(max_attempts) is int and 1 <= max_attempts <= 5, 'Require one to five repair attempts')
    _need(bool(tree), 'Require a nonempty prepared bundle')
    return dict(bundle_files=_inventory(tree), limits=dict(limits), max_attempts=max_attempts,
                execution_policy=EXECUTION_POLICY, process_policy=PROCESS_POLICY,
                **({'qualify_no_repair':True} if qualify_no_repair else {}),**failure_policy_fields(optional_failure_policy))


def _request(root):
    request = read_record(path_in(root,'request.json'))
    _need(type(request.get('schema_version')) is int and request['schema_version'] == 1
          and request.get('policy_id') == POLICY_ID and _uuid(request.get('request_id'))
          and request.get('bundle') == {'anchor':ANCHOR,'path':'inputs/bundle'})
    _members(root/'inputs',set(),{'bundle'})
    config = request.get('configuration')
    _need(isinstance(config,dict))
    expected = _configuration(_tree(path_in(root,'inputs/bundle')),config.get('limits',{}),config.get('max_attempts'),qualify_no_repair=config.get('qualify_no_repair',False),optional_failure_policy=config.get('optional_failure_policy'))
    _need(config == expected, 'Prepared request snapshot or configuration changed')
    return request


def _execution(attempt, intent, config):
    work = path_in(attempt,'execution')
    if not work.exists():
        return {'state':'NOT_CREATED','activity':False}, None
    _need(work.is_dir())
    state = inspect_prepared_repair_processes(work)
    header = state.get('header')
    if header is not None:
        _need(header.get('attempt_owner') == _attempt_identity(intent)
              and header['bundle_files'] == config['bundle_files']
              and all(header['coordinator'].get(k) == intent['coordinator'].get(k)
                      for k in ('pid','pgid','host','boot_id','start_marker')),
              'Prepared execution belongs to another request, attempt or coordinator')
        for phase, evidence in state['phases'].items():
            if 'job' not in evidence:
                continue
            limit = ('native_timeout_seconds' if phase.startswith('native-') else
                     'attribution_timeout_seconds' if phase == 'attribution' else 'derivative_timeout_seconds')
            _need(evidence['job']['timeout_seconds'] <= config['limits'][limit], 'Worker exceeded frozen phase limit')
    report = work/'repair_execution.json'
    if report.exists():
        value = _json(_read(report)); mode = value.get('qualify_no_repair',False)
        _need(value.get('optional_failure_policy') == config.get('optional_failure_policy'),
              'Execution optional failure policy differs from frozen request')
        if 'optional_failure' in value:
            _need(config.get('optional_failure_policy') == FALLBACK_POLICY_ID
                and _bytes(value['optional_failure']) == _bytes(inspect_prepared_native_failure(work,value['optional_failure']['phase'])),
                'Saved optional failure does not reproduce')
        _need(type(mode) is bool and mode == config.get('qualify_no_repair',False),
              'Execution no-repair mode differs from frozen request')
    binding = {'header':header['record_sha256'] if header else None,
               'finished':state.get('finished',{}).get('record_sha256')}
    return state, binding


def _receipt(attempt):
    path = path_in(attempt,'execution/repair_execution.json')
    if not path.exists():
        return None
    _need(path.is_file())
    return {'anchor':'attempt_directory','path':'execution/repair_execution.json',**_digest(path.read_bytes())}


def _attempt_state(attempt, number, request):
    _members(attempt,{'attempt.json','finished.json'},{'execution'})
    result = dict(number=number,state='UNKNOWN',activity=None)
    if not (attempt/'attempt.json').exists():
        _need(not (attempt/'finished.json').exists() and not (attempt/'execution').exists())
        return result
    intent = read_record(attempt/'attempt.json')
    _need(intent.get('request_sha256') == request['record_sha256']
          and type(intent.get('number')) is int and intent['number'] == number
          and _uuid(intent.get('attempt_id')) and _valid_identity(intent.get('coordinator'))
          and intent.get('execution') == {'anchor':'attempt_directory','path':'execution'}
          and ('parent_attempt' not in intent or _valid_attempt_identity(intent['parent_attempt'])))
    # Final records precede their dependencies. For unsealed work, observe the
    # caller before inspecting output that may be published immediately before exit.
    finished = read_record(attempt/'finished.json') if (attempt/'finished.json').exists() else None
    caller = coordinator_alive(intent['coordinator']) if finished is None else None
    execution,binding = _execution(attempt,intent,request['configuration'])
    result.update(intent=intent,execution=execution)
    if finished is not None:
        _need(finished.get('attempt_sha256') == intent['record_sha256']
              and finished.get('outcome') in {'RETURNED','RAISED'} and finished.get('stopped_verified') is True
              and finished.get('process_records') == binding and finished.get('execution_receipt') == _receipt(attempt)
              and execution['state'] in {'STOPPED','NOT_CREATED'}
              and (finished['outcome'] != 'RETURNED' or execution['state'] == 'STOPPED'))
        return dict(result,state='STOPPED',activity=False,finished=finished)
    safe = caller is False and execution['state'] in {'STOPPED','STOPPED_UNFINISHED','NOT_CREATED'}
    live = caller is True or execution['activity'] is True
    return dict(result,coordinator_activity=caller,activity=False if safe else True if live else None,
                state='STOPPED_UNFINISHED' if safe else 'LIVE' if live else 'UNKNOWN')


def inspect_prepared_repair_request(directory):
    """Read advisory availability; the modifying API rechecks under its lock."""
    root = _root(directory)
    result = dict(schema_version=1,policy_id=POLICY_ID,state='NOT_RECORDED',availability='BLOCKED',
                  retry_authorized=False,attempts=[],scope='PREPARED_REPAIR_ONLY; NOT_ACQUISITION_OR_ADOPTION')
    if not root.exists():
        return result
    _members(root,{'request.json','request.lock'},{'inputs','attempts'})
    if not (root/'request.json').exists():
        return dict(result,state='UNKNOWN')
    request = _request(root)
    attempts = path_in(root,'attempts');rows=[]
    if attempts.exists():
        _need(attempts.is_dir())
        for number,folder in enumerate(sorted(attempts.iterdir()),1):
            _need(not folder.is_symlink() and folder.is_dir() and folder.name == f'attempt-{number:04d}',
                  'Prepared repair attempts must be consecutive immutable directories')
            rows.append(_attempt_state(folder,number,request))
    limit = request['configuration']['max_attempts']
    _need(len(rows) <= limit, 'Prepared repair attempt allowance exceeded')
    safe = all(row['state'] in {'STOPPED','STOPPED_UNFINISHED'} for row in rows)
    availability = 'BLOCKED' if not safe else 'EXHAUSTED' if len(rows) == limit else 'AVAILABLE'
    return dict(result,state='RECORDED',request=request,attempts=rows,availability=availability)


def _seal(attempt, intent, request, outcome, error=None):
    execution,binding = _execution(attempt,intent,request['configuration'])
    if execution['state'] not in {'STOPPED','NOT_CREATED'} or (outcome == 'RETURNED' and execution['state'] != 'STOPPED'):
        raise CampaignProcessError('Prepared repair attempt has unresolved execution ownership')
    write_record(attempt/'finished.json',dict(attempt_sha256=intent['record_sha256'],outcome=outcome,
        error_type=error,stopped_verified=True,finished_utc=now(),process_records=binding,execution_receipt=_receipt(attempt)))


def execute_prepared_dictionary_repair_attempt(bundle, phenix, request_directory, *,
        native_timeout_seconds=120, attribution_timeout_seconds=90, derivative_timeout_seconds=300,
        total_timeout_seconds=600, max_attempts=2, qualify_no_repair=False, optional_failure_policy=None,
        _parent_attempt_identity=None, _remaining_seconds=None):
    """Perform one fresh, bounded repair attempt under an immutable logical request.

    Calls are explicit attempts, not cache lookups. All limits and exact prepared
    bytes stay frozen across calls. Unknown ownership/publication blocks another
    reservation; prior work is never resumed, resealed, deleted or overwritten.
    A different request directory is a different coordination scope. Optional
    enclosing identity is per attempt; a remaining callback clamps preflight,
    execution and sealing without replacing the frozen request limits.
    """
    started = monotonic()
    parent = parent_identity(_parent_attempt_identity)
    outer = OuterAllowance(_remaining_seconds, monotonic, PreparedRepairBudgetExceeded)
    def remaining():
        cap = outer.remaining()
        if cap is None: return None  # Preserve standalone execution-clock semantics.
        value = min(cap, total_timeout_seconds - (monotonic() - started))
        if value <= 0: raise PreparedRepairBudgetExceeded('Enclosing prepared request allowance exhausted')
        return value
    root = _root(request_directory);original = _root(bundle)
    installation = Path(phenix.root).resolve()
    _need(not original.is_relative_to(root) and not root.is_relative_to(original)
          and not root.is_relative_to(installation) and not installation.is_relative_to(root),
          'Repair request must be separate from source bundle and installation')
    if root.exists():
        _members(root,{'request.json','request.lock'},{'inputs','attempts'})
        if not (root/'request.json').exists() and any(p.name != 'request.lock' for p in root.iterdir()):
            raise CampaignProcessError('Repair request has unresolved initial publication')
    before = _tree(original)
    limits = dict(native_timeout_seconds=native_timeout_seconds,attribution_timeout_seconds=attribution_timeout_seconds,
                  derivative_timeout_seconds=derivative_timeout_seconds,total_timeout_seconds=total_timeout_seconds)
    config = _configuration(before,limits,max_attempts,qualify_no_repair=qualify_no_repair,optional_failure_policy=optional_failure_policy)
    consumer = read_dictionary_bundle(original)['report']['consumer']
    _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer), 'Prepared repair consumer differs')
    _need(_tree(original) == before, 'Prepared source changed during preflight')
    remaining()
    coordinator = current_process_identity()
    root.mkdir(parents=True,exist_ok=True)
    with exclusive_lock(root/'request.lock'):
        if not (root/'request.json').exists():
            if {p.name for p in root.iterdir()} != {'request.lock'}:
                raise CampaignProcessError('Repair request has unresolved initial publication')
            frozen = root/'inputs/bundle'
            for name,data in before.items():
                path=frozen/name;path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(data);stream.flush();os.fsync(stream.fileno())
            for directory in sorted({frozen,*[p for p in frozen.rglob('*') if p.is_dir()]},key=lambda p:len(p.parts),reverse=True):
                _sync_directory(directory)
            _sync_directory(frozen.parent)
            write_record(root/'request.json',dict(schema_version=1,policy_id=POLICY_ID,request_id=str(uuid.uuid4()),
                created_utc=now(),configuration=config,bundle={'anchor':ANCHOR,'path':'inputs/bundle'}))
        state = inspect_prepared_repair_request(root);request = state['request']
        _need(request['configuration'] == config, 'Prepared repair identity differs from frozen request')
        if state['availability'] != 'AVAILABLE':
            reason = 'exhausted attempt allowance' if state['availability'] == 'EXHAUSTED' else 'unresolved previous attempt'
            raise CampaignProcessError('Prepared repair request has '+reason)
        _need(_tree(original) == before, 'Prepared source changed before reservation')
        _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer), 'Prepared repair consumer changed')
        remaining()
        number = len(state['attempts'])+1
        attempt=root/'attempts'/f'attempt-{number:04d}';attempt.mkdir(parents=True,exist_ok=False)
        intent=write_record(attempt/'attempt.json',dict(request_sha256=request['record_sha256'],number=number,
            attempt_id=str(uuid.uuid4()),coordinator=coordinator,created_utc=now(),
            execution={'anchor':'attempt_directory','path':'execution'},
            **({'parent_attempt':parent} if parent is not None else {})))
        try:
            result=execute_prepared_dictionary_repair(root/'inputs/bundle',phenix,attempt/'execution',
                                                     _attempt_identity=_attempt_identity(intent),**limits,
                                                     **({'qualify_no_repair':True} if qualify_no_repair else {}),**failure_policy_fields(optional_failure_policy),
                                                     **({'_remaining_seconds':remaining} if _remaining_seconds is not None else {}))
            _need(_tree(original) == before and _tree(root/'inputs/bundle') == before,
                  'Prepared source or request snapshot changed during execution')
            _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer), 'Prepared repair consumer changed')
            remaining()
            _seal(attempt,intent,request,'RETURNED')
        except BaseException as exc:
            try:
                _seal(attempt,intent,request,'RAISED',type(exc).__name__)
            except Exception as seal_error:
                add_failure_note(exc, 'Attempt completion could not be sealed', seal_error)
            raise
        return dict(schema_version=1,policy_id=POLICY_ID,request_id=request['request_id'],attempt_id=intent['attempt_id'],
                    attempt_number=number,execution_directory={'anchor':ANCHOR,'path':f'attempts/attempt-{number:04d}/execution'},
                    execution=result)
