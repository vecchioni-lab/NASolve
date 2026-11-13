"""Archive-backed complete-attempt reads with stable public model/restraint paths.

This storage layer does not replace the complete owner's scientific validation.
It prepares an explicit, durable archive binding; retirement is a separate explicit
operation for qualified, completely stopped successful native work.
Unpublished/partial archives do not change ordinary reads or grant retry authority.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import errno
import os

from .campaign_records import read_record, write_record, _sync_directory
from .campaign_process import exclusive_lock
from .cif_dictionary_sites import _need, _read
from .cif_complete_attempt_archive import (
    ARTIFACT_POLICY, REPAIR_RUNTIME, CONTINUATION_RUNTIME,
    pack_complete_attempt_evidence, expanded_complete_attempt_evidence,
)

POLICY_ID = 'cif-complete-attempt-retention-v1'
RETIREMENT_POLICY = 'cif-complete-attempt-working-retirement-v1'
PUBLIC_ROOTS = ('preparation/bundle/', REPAIR_RUNTIME, CONTINUATION_RUNTIME,
                'continuation/inputs/runtime/')
PUBLIC_FILES = frozenset({'attempt.json', 'result.json', 'finished.json'})


def kept_path(name):
    """Stable public files and complete bundles, including their readable manifests."""
    return name in PUBLIC_FILES or any(name.startswith(p) for p in PUBLIC_ROOTS)


def validate_retention_layout(root):
    from .cif_repair_attempt import _members
    folder=root/'retention'
    if not folder.exists():
        _need(not folder.is_symlink(), 'Symbolic retention path')
        return
    names={p.name for p in (root/'attempts').iterdir()} if (root/'attempts').is_dir() else set()
    _members(folder,set(),names)
    for child in folder.iterdir():
        _members(child,{'evidence.zip','archive.json','retire-intent.json','retired.json'},set())


def _binding(root, attempt, number, request):
    """Read the immutable storage receipt against original scientific records."""
    from .cif_complete_request import _intent
    record_path=root/'retention'/attempt.name/'archive.json'
    if not record_path.exists():
        _need(not any((record_path.parent/n).exists() for n in ('retire-intent.json','retired.json')),
              'Retirement has no durable archive binding')
        return None
    data=_read(record_path);record=read_record(record_path)
    intent=_intent(attempt,number,request)
    finished=_read(attempt/'finished.json')
    expected={'schema_version','policy_id','request_sha256','attempt_sha256','number',
              'finished_sha256','archive','record_sha256'}
    _need(set(record)==expected and type(record['schema_version']) is int and record['schema_version']==1
          and record['policy_id']==POLICY_ID and type(record['number']) is int and record['number']==number
          and record['request_sha256']==request['record_sha256']
          and record['attempt_sha256']==intent['record_sha256']
          and record['finished_sha256']==sha256(finished).hexdigest(),
          'Attempt archive has a different request/owner/finished binding')
    ref=record['archive']
    from . import cif_runtime_evidence as storage
    _need(isinstance(ref,dict) and set(ref)=={'path','sha256','size'} and ref['path']=='evidence.zip'
          and isinstance(ref['sha256'],str) and storage._SHA.fullmatch(ref['sha256'])
          and type(ref['size']) is int and 0<ref['size']<=storage.MAX_ARCHIVE_BYTES,
          'Invalid complete-attempt archive reference')
    _need(request['configuration'].get('artifact_policy')==ARTIFACT_POLICY,
          'Unsupported retained owner partition policy')
    return record,data


def _remaining(attempt, request, finished):
    """Only exact archived duplicates may be absent; public files must remain."""
    from .cif_complete_request import _attempt_files, _artifact_options
    expected=finished['artifacts'];current=_attempt_files(attempt,**_artifact_options(request['configuration']))
    _need(set(current['directories'])<=set(expected['directories'])
          and all(expected['files'].get(n)==ref for n,ref in current['files'].items()),
          'Remaining attempt files differ from their archived owner')
    _need(all(current['files'].get(n)==ref for n,ref in expected['files'].items() if kept_path(n)),
          'Archived attempt lost or changed a public model/restraint file')
    return current


def public_result(value, view, attempt):
    """Rebase validated results before temporary evidence leaves its read scope."""
    if isinstance(value,Path):
        if not value.is_relative_to(view):return value
        name=value.relative_to(view).as_posix();target=attempt/name
        is_public=kept_path(name) or any(name==p.rstrip('/') for p in PUBLIC_ROOTS)
        _need(is_public and target.exists(), 'Result exposes an unretained working path')
        return target
    if isinstance(value,dict):return {k:public_result(v,view,attempt) for k,v in value.items()}
    if isinstance(value,list):return [public_result(v,view,attempt) for v in value]
    if isinstance(value,tuple):return tuple(public_result(v,view,attempt) for v in value)
    _need(not isinstance(value,str) or not value.startswith(str(view)),
          'Result exposes an untyped temporary working path')
    return value


@contextmanager
def attempt_read_view(root, attempt, number, request):
    """Use the same complete-owner reader whether working duplicates exist or not."""
    bound=_binding(root,attempt,number,request)
    if bound is None:
        yield attempt
        return
    record,record_bytes=bound;archive=root/'retention'/attempt.name/'evidence.zip'
    finished=read_record(attempt/'finished.json')
    current=_remaining(attempt,request,finished)
    _retirement_records(archive.parent,record,finished,current)
    _need(archive.stat().st_size==record['archive']['size'], 'Attempt archive size changed')
    with expanded_complete_attempt_evidence(archive,record['archive']['sha256'],
            finished_sha256=record['finished_sha256']) as view:
        yield view/'evidence'
        current=_remaining(attempt,request,finished)
        _retirement_records(archive.parent,record,finished,current)
        _need(_read(archive.parent/'archive.json')==record_bytes
              and sha256(_read(attempt/'finished.json')).hexdigest()==record['finished_sha256']
              and sha256(_read(archive)).hexdigest()==record['archive']['sha256'],
              'Attempt archive changed during read')


def _archive_history(root, attempt_number):
    from . import cif_complete_request as complete
    results=[]
    state=complete._inspect_dictionary_request(root,selected_attempt=attempt_number,result_sink=results)
    _need(state['state']=='RECORDED' and state['availability'] in {'AVAILABLE','EXHAUSTED'}
          and attempt_number<=len(state['attempts']), 'Require a known-stopped complete request')
    request=state['request'];row=state['attempts'][attempt_number-1]
    _need(request['configuration'].get('artifact_policy')==ARTIFACT_POLICY and row['state']=='STOPPED'
          and row['finished']['outcome']=='RETURNED' and len(results)==1,
          'Require a returned current-partition attempt')
    return request,row,results[0]


def _sync_archive(path):
    # An earlier writer may have died after writing all bytes but before fsync.
    # Recovery must make them durable before publishing deletion authority.
    with path.open('rb') as stream:os.fsync(stream.fileno())
    _sync_directory(path.parent)


def _prepare_locked(root, attempt_number, history):
    from . import cif_complete_request as complete
    request,row,_=history;config=request['configuration']
    attempt=root/'attempts'/f'attempt-{attempt_number:04d}'
    existing=_binding(root,attempt,attempt_number,request)
    if existing is not None:return existing[0]
    folder=root/'retention'/attempt.name
    folder.mkdir(parents=True,exist_ok=True);_sync_directory(folder.parent);_sync_directory(root)
    archive=folder/'evidence.zip'
    finished_sha=sha256(_read(attempt/'finished.json')).hexdigest()
    if not archive.exists():
        pack_complete_attempt_evidence(attempt,archive,artifact_policy=ARTIFACT_POLICY,
            with_continuation='continuation' in config)
    from .cif_runtime_evidence import MAX_ARCHIVE_BYTES
    _need(archive.is_file() and archive.stat().st_size<=MAX_ARCHIVE_BYTES,
          'Unsafe or oversized unpublished attempt archive')
    digest=sha256(_read(archive)).hexdigest();results=[]
    with expanded_complete_attempt_evidence(archive,digest,finished_sha256=finished_sha) as view:
        complete._attempt_state(root,view/'evidence',attempt_number,request,results)
        _need(len(results)==1, 'Archive has no exact returned result')
        public_result(results[0],view/'evidence',attempt)
    _need(complete._request(root)==request
          and complete._attempt_files(attempt,**complete._artifact_options(config))==row['finished']['artifacts']
          and sha256(_read(attempt/'finished.json')).hexdigest()==finished_sha,
          'Complete request changed while preparing its archive')
    _sync_archive(archive)
    _need(sha256(_read(archive)).hexdigest()==digest, 'Archive changed before durable publication')
    return write_record(folder/'archive.json',dict(schema_version=1,policy_id=POLICY_ID,
        request_sha256=request['record_sha256'],attempt_sha256=row['intent']['record_sha256'],
        number=attempt_number,finished_sha256=finished_sha,
        archive=dict(path='evidence.zip',sha256=digest,size=archive.stat().st_size)))


def prepare_attempt_archive(directory, attempt_number):
    """Explicit archive preparation; never remove working files or run native jobs.

    A complete unpublished archive can be recovered without repacking. A partial
    archive is preserved/refused and does not change ordinary result reading.
    """
    from .cif_repair_attempt import _root
    _need(type(attempt_number) is int and attempt_number>=1, 'Require an exact positive attempt number')
    root=_root(directory)
    with exclusive_lock(root/'request.lock'):
        return _prepare_locked(root,attempt_number,_archive_history(root,attempt_number))


def _retirement_records(folder, archive, finished, current):
    """Validate storage receipts without inventing new scientific authority."""
    intent_path=folder/'retire-intent.json';done_path=folder/'retired.json'
    if not intent_path.exists():
        _need(not done_path.exists(), 'Retirement completion lacks its intent')
        return None
    intent=read_record(intent_path)
    expected=dict(schema_version=1,policy_id=RETIREMENT_POLICY,retention_sha256=archive['record_sha256'])
    _need({k:v for k,v in intent.items() if k!='record_sha256'}==expected
          and type(intent['schema_version']) is int, 'Retirement intent differs from its archive')
    if not done_path.exists():return None
    done=read_record(done_path);expected=_retirement_completion(intent,finished)
    _need({k:v for k,v in done.items() if k!='record_sha256'}==expected
          and all(type(done[k]) is int for k in ('schema_version','retired_files','retired_logical_bytes')),
          'Retirement completion differs from its original inventory')
    _need(current['files']=={n:r for n,r in finished['artifacts']['files'].items() if kept_path(n)},
          'Retired working files have reappeared')
    return done


def _retirement_completion(intent, finished):
    files={n:r for n,r in finished['artifacts']['files'].items() if not kept_path(n)}
    return dict(schema_version=1,policy_id=RETIREMENT_POLICY,intent_sha256=intent['record_sha256'],
        retired_files=len(files),retired_logical_bytes=sum(r['size'] for r in files.values()))


def _successful_work(row, exact):
    """Keep unsuccessful/partial native work unpacked even when fallback is usable."""
    _need(exact['runtime'] is not None, 'Retirement requires an independently qualified public runtime')
    execution=exact['execution']
    _need('optional_failure' not in execution
          and all(r.get('status')!='KNOWN_STOPPED_NATIVE_FAILURE' for r in execution.get('plane_results',[])),
          'Preserve failed optional native work unpacked')
    generation=exact['result'].get('plane_generation',{}).get('components',{})
    _need(all(r['status'] in {'NO_GENERATION_NEEDED','OWNED_SUPPORT_READY'} for r in generation.values()),
          'Preserve unsuccessful plane generation unpacked')
    scopes=[row['children']['repair']['execution']]
    if exact.get('continuation') is not None:scopes.append(exact['continuation']['process_evidence'])
    for scope in scopes:
        _need(scope['state']=='STOPPED' and scope['finished']['outcome']=='RETURNED'
              and all(p['state']=='STOPPED' and p['finished']['status']=='COMPLETED'
                      and type(p['finished']['returncode']) is int and p['finished']['returncode']==0
                      for p in scope['phases'].values()), 'Preserve failed or uncertain native work unpacked')


def _remove_duplicate(path, reference):
    _need(path.stat().st_size==reference['size'], 'Working file changed before retirement; preserve it')
    data=_read(path)
    _need(len(data)==reference['size'] and sha256(data).hexdigest()==reference['sha256'],
          'Working file changed before retirement; preserve it')
    path.unlink()


def _file_stamp(path):
    info=path.lstat()
    return (info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def _retirement_guard(root, attempt, number, request, archive):
    from .cif_complete_request import _request
    folder=root/'retention'/attempt.name;path=folder/'evidence.zip'
    _need(_request(root)==request and _binding(root,attempt,number,request)[0]==archive,
          'Archive/request binding changed before retirement')
    ref=archive['archive']
    _need(path.stat().st_size==ref['size'], 'Archive changed before retirement; preserve working files')
    data=_read(path)
    _need(len(data)==ref['size'] and sha256(data).hexdigest()==ref['sha256'],
          'Archive changed before retirement; preserve working files')
    return {p:_file_stamp(p) for p in (path,folder/'archive.json',root/'request.json',
        attempt/'attempt.json',attempt/'finished.json')}


def retire_attempt_working_files(directory, attempt_number):
    """Retire only exact archived working duplicates, with interruption recovery.

    The same lock excludes native attempts and other storage operations. The
    durable archive and retirement intent precede every unlink. Public bundles,
    original records, shared request inputs and failed native work stay in place.
    Repeating this explicit operation resumes deletions; it never reruns chemistry.
    """
    from .cif_repair_attempt import _root
    _need(type(attempt_number) is int and attempt_number>=1, 'Require an exact positive attempt number')
    root=_root(directory)
    with exclusive_lock(root/'request.lock'):
        history=_archive_history(root,attempt_number);request,row,exact=history
        _successful_work(row,exact)
        archive=_prepare_locked(root,attempt_number,history)
        attempt=root/'attempts'/f'attempt-{attempt_number:04d}';folder=root/'retention'/attempt.name
        current=_remaining(attempt,request,row['finished'])
        done=_retirement_records(folder,archive,row['finished'],current)
        if done is not None:return done
        stamps=_retirement_guard(root,attempt,attempt_number,request,archive)
        intent_path=folder/'retire-intent.json'
        if not intent_path.exists():
            write_record(intent_path,dict(schema_version=1,policy_id=RETIREMENT_POLICY,
                retention_sha256=archive['record_sha256']))
        intent=read_record(intent_path)
        stamps[intent_path]=_file_stamp(intent_path)
        touched=set()
        for name,reference in sorted(current['files'].items()):
            if not kept_path(name):
                _need(all(_file_stamp(p)==stamp for p,stamp in stamps.items()),
                      'Archive/owner changed during retirement; preserve remaining files')
                path=attempt/name;_remove_duplicate(path,reference);touched.add(path.parent)
        # Flush removals before publishing completion; an interruption before this
        # point may leave duplicates, which the same exact archive can reread.
        for parent in sorted(touched):_sync_directory(parent)
        for name in sorted(current['directories'],key=lambda n:len(Path(n).parts),reverse=True):
            prefix=name+'/'
            if any(prefix.startswith(p) or p.startswith(prefix) for p in PUBLIC_ROOTS):continue
            path=attempt/name
            try:path.rmdir()
            except OSError as exc:
                if exc.errno not in {errno.ENOENT,errno.ENOTEMPTY,errno.EEXIST}:raise
            else:_sync_directory(path.parent)
        remaining=_remaining(attempt,request,row['finished'])
        _need(all(kept_path(n) for n in remaining['files']), 'Working duplicates remain after retirement')
        # Recheck the durable binding after removal, before a completion claim.
        _need(read_record(intent_path)==intent, 'Retirement intent changed before completion')
        _retirement_guard(root,attempt,attempt_number,request,archive)
        done=write_record(folder/'retired.json',_retirement_completion(intent,row['finished']))
        _retirement_records(folder,archive,row['finished'],remaining)
        return done
