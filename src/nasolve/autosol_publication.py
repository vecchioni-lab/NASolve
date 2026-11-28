"""Finish an exact checked AutoSol result save without launching native work.

Observe the existing producer/group; do not create a second process owner or
signal saved PIDs. A shared, foreign or unknown live group cannot authorize a
pending save. Existing scientific readers remain the qualification authority.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from uuid import UUID, uuid4

from .campaign_records import path_in, read_record, write_record
from .campaign_process import current_process_identity, coordinator_alive, process_alive, exclusive_lock
from .cif_dictionary_sites import _need, _read

EXECUTION_POLICY = 'autosol-inherited-process-observation-v1'
PUBLICATION_POLICY = 'autosol-result-publication-v1'
EXECUTION_PATH = 'AutoSol/execution.json'
PUBLICATION_PATH = 'AutoSol/publication.json'
RESULT_PATH = 'AutoSol/report.json'


def _group(coordinator):
    return dict(pid=coordinator['pgid'], pgid=coordinator['pgid'],
                host=coordinator['host'], boot_id=coordinator['boot_id'])


def _report_bytes(report):
    # Match the existing guarded run-report writer exactly, including newline.
    return (json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+'\n').encode('utf-8')


def _target(report, result):
    target = deepcopy(report)
    target.update(stage='autosol', status=result['status'], message=result['message'],
                  updated_utc=result['created_utc'], autosol=result)
    return target


def observe_execution(run, site_reference, command):
    """Record the inherited group before launch; native command/group is unchanged."""
    identity = current_process_identity()
    return write_record(path_in(run, EXECUTION_PATH), dict(
        policy_id=EXECUTION_POLICY, launch_id=str(uuid4()), coordinator=identity,
        process_group=_group(identity), site_reference=site_reference, command=list(command)))


def _execution(run):
    record = read_record(path_in(run, EXECUTION_PATH))
    _need(set(record) == {'policy_id','launch_id','coordinator','process_group',
                          'site_reference','command','record_sha256'}
          and record['policy_id'] == EXECUTION_POLICY, 'Unsupported AutoSol process observation')
    identifier = record['launch_id']
    _need(isinstance(identifier,str) and str(UUID(identifier)) == identifier
          and UUID(identifier).version == 4, 'Malformed AutoSol launch identity')
    identity = record['coordinator']
    _need(isinstance(identity,dict) and set(identity) == {
        'pid','pgid','host','boot_id','start_marker','started_utc','heartbeat_utc'}
        and all(type(identity[k]) is int and identity[k] > 1 for k in ('pid','pgid'))
        and isinstance(identity['host'],str) and bool(identity['host'])
        and all(identity[k] is None or isinstance(identity[k],str) for k in ('boot_id','start_marker'))
        and record['process_group'] == _group(identity), 'Malformed AutoSol producer/group observation')
    _need(isinstance(record['command'],list) and record['command']
          and all(isinstance(v,str) and v for v in record['command']), 'Malformed AutoSol historical command')
    return record


def seal_publication(run, previous_sha256, report):
    """Bind the completed stage record and exact desired pointer before writing it."""
    from .checkpoints import _file_reference
    execution = _execution(run); current = current_process_identity()
    _need(all(execution['coordinator'][k] == current[k]
              for k in ('pid','pgid','host','boot_id','start_marker')),
          'AutoSol publication belongs to a different producer')
    result = read_record(path_in(run, RESULT_PATH))
    _need(result == report['autosol'] and result['command'] == execution['command']
          and result['site_reference'] == execution['site_reference'],
          'AutoSol publication differs from its observed execution')
    return write_record(path_in(run, PUBLICATION_PATH), dict(
        policy_id=PUBLICATION_POLICY, launch_id=execution['launch_id'],
        execution=_file_reference(path_in(run, EXECUTION_PATH),run),
        result=_file_reference(path_in(run, RESULT_PATH),run),
        previous_run_report_sha256=previous_sha256,
        published_run_report_sha256=sha256(_report_bytes(report)).hexdigest()))


def _reference(run, ref, relative):
    from .checkpoints import _ref_path
    _need(isinstance(ref,dict) and ref.get('anchor') == 'run'
          and ref.get('relative_path') == relative, 'Unexpected AutoSol publication reference')
    path = path_in(run,relative); _read(path)
    _need(_ref_path(ref,'AutoSol publication evidence',run) == path,
          'AutoSol publication evidence resolves elsewhere')
    return path


def _load(run):
    from .checkpoints import registry_path, _ref_path
    from .autosol_reference import validate_reference, validate_result_reference
    from .autorefine import _effective_phase
    publication = read_record(path_in(run, PUBLICATION_PATH))
    _need(set(publication) == {'policy_id','launch_id','execution','result',
          'previous_run_report_sha256','published_run_report_sha256','record_sha256'}
          and publication['policy_id'] == PUBLICATION_POLICY, 'Unsupported AutoSol publication receipt')
    for key in ('previous_run_report_sha256','published_run_report_sha256'):
        _need(isinstance(publication[key],str) and re.fullmatch('[0-9a-f]{64}',publication[key]),
              'Malformed AutoSol publication checksum')
    _reference(run,publication['execution'],EXECUTION_PATH)
    result_path = _reference(run,publication['result'],RESULT_PATH)
    execution = _execution(run); result = read_record(result_path)
    _need(publication['launch_id'] == execution['launch_id']
          and result['command'] == execution['command']
          and result['site_reference'] == execution['site_reference'], 'AutoSol result/execution binding differs')
    registry_file = registry_path(run); _read(registry_file); registry = read_record(registry_file)
    reference = validate_reference(run,registry)
    _need(reference is not None and execution['site_reference'] == registry['autosol_site_reference']
          and publication['previous_run_report_sha256'] == reference['run_report_sha256_before_autosol'],
          'AutoSol publication differs from its frozen chosen model')
    before = _read(path_in(run,'report.json')); report = json.loads(before)
    _need(isinstance(report,dict) and report.get('workflow') == 'automr'
          and isinstance(report.get('postmr'),dict) and 'checked_preparation' in report['postmr'],
          'AutoSol completion requires checked preparation')
    digest = sha256(before).hexdigest()
    _need(digest in {publication['previous_run_report_sha256'],publication['published_run_report_sha256']},
          'Run report changed since AutoSol publication; preserve newer work')
    target = _target(report,result)
    _need(sha256(_report_bytes(target)).hexdigest() == publication['published_run_report_sha256'],
          'AutoSol publication target does not reproduce')
    validate_result_reference(run,target)
    _effective_phase(target,{},run)  # Existing checksum-bound phase consumer; no SDK.
    for key in ('heavy_atom_model','refinement_data','density_modified_map'):
        ref = result['outputs'].get(key)
        if ref is not None:
            path = _ref_path(ref,'saved AutoSol '+key,run)
            expected = result['outputs'].get(key+'_sha256')
            _need(expected is None or sha256(_read(path)).hexdigest() == expected,
                  'Saved AutoSol output checksum differs')
    return dict(publication=publication,execution=execution,result=result,
                registry=registry,target=target,before=before,
                published=digest == publication['published_run_report_sha256'])


def _stopped(state):
    execution = state['execution']
    _need(coordinator_alive(execution['coordinator']) is False
          and process_alive(execution['process_group']) is False,
          'AutoSol producer or inherited process group is active or unknown; preserve work and wait')


def _result(run, state):
    from .autosol import AutoSolResult
    from .run_context import resolve_artifact_path
    result = state['result']; outputs = result['outputs']
    return AutoSolResult(status=result['status'],message=result['message'],run_directory=run,
        autosol_directory=run/'AutoSol',report_path=run/RESULT_PATH,
        log_path=run/'AutoSol/autosol.console.log',
        heavy_atom_model=resolve_artifact_path(outputs.get('heavy_atom_model'),run),
        refinement_data=resolve_artifact_path(outputs.get('refinement_data'),run),
        matched_distance=(result.get('site_validation') or {}).get('best_distance'))


def complete_autosol_publication(run_directory, *, if_present=False):
    """Finish a sealed result save after verified stop; never run, retry or select.

    Missing old receipts are not retrofitted. An already exact completed result
    revalidates without rewriting anything, even if its producer still exists.
    Pending completion never creates a campaign-stage success receipt. With
    if_present, return None only when no publication receipt exists; invalid
    existing evidence still raises rather than authorizing native work.
    """
    from .autosol import AutoSolPreparationError
    from .checkpoints import _validate_preparation, _required_observations
    from .cif_postmr_publication import _publish_run_report
    try:
        run = Path(run_directory).expanduser().resolve()
        if run.name == 'report.json': run = run.parent
        if if_present and not path_in(run,PUBLICATION_PATH).exists():
            return None
        initial = _load(run)
        if not initial['published']: _stopped(initial)
        def checked():
            state = _load(run)
            if not state['published']: _stopped(state)
            _required_observations(state['target'],run)
            _validate_preparation(run,json.loads(state['before']),state['registry'])
            fresh = _load(run)
            _need(not initial['published'] or fresh['published'],
                  'Run report changed during completed publication inspection')
            _need(all(state[k] == fresh[k] for k in ('publication','execution','result')),
                  'AutoSol evidence changed during publication inspection')
            return fresh
        if initial['published']:
            return _result(run,checked())
        with exclusive_lock(path_in(run,'AutoSol/.publication.lock')):
            state = checked()
            if not state['published']:
                _stopped(state)
                _publish_run_report(run/'report.json',state['publication']['previous_run_report_sha256'],state['target'])
            return _result(run,state)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, IndexError) as exc:
        raise AutoSolPreparationError('Cannot complete saved AutoSol publication: '+str(exc)) from exc
