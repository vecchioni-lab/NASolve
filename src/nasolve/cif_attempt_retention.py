"""Archive-backed complete-attempt reads with stable public model/restraint paths.

This storage layer does not replace the complete owner's scientific validation.
It prepares an explicit, durable archive binding; it never removes source files.
Unpublished/partial archives do not change ordinary reads or grant retry authority.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from .campaign_records import read_record, write_record, _sync_directory
from .campaign_process import exclusive_lock
from .cif_dictionary_sites import _need, _read
from .cif_complete_attempt_archive import (
    ARTIFACT_POLICY, REPAIR_RUNTIME, CONTINUATION_RUNTIME,
    pack_complete_attempt_evidence, expanded_complete_attempt_evidence,
)

POLICY_ID = 'cif-complete-attempt-retention-v1'
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
        _members(child,{'evidence.zip','archive.json'},set())


def _binding(root, attempt, number, request):
    """Read the immutable storage receipt against original scientific records."""
    from .cif_complete_request import _intent
    record_path=root/'retention'/attempt.name/'archive.json'
    if not record_path.exists():return None
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
    _remaining(attempt,request,finished)
    _need(archive.stat().st_size==record['archive']['size'], 'Attempt archive size changed')
    with expanded_complete_attempt_evidence(archive,record['archive']['sha256'],
            finished_sha256=record['finished_sha256']) as view:
        yield view/'evidence'
        _remaining(attempt,request,finished)
        _need(_read(archive.parent/'archive.json')==record_bytes
              and sha256(_read(attempt/'finished.json')).hexdigest()==record['finished_sha256']
              and sha256(_read(archive)).hexdigest()==record['archive']['sha256'],
              'Attempt archive changed during read')


def prepare_attempt_archive(directory, attempt_number):
    """Explicitly archive a completed attempt under its existing request lock.

    Replay the existing owner before publishing the binding and check every
    returned path. A complete unpublished archive can be recovered; a partial
    archive is preserved and refused. No working file is deleted or native job run.
    """
    from . import cif_complete_request as complete
    from .cif_repair_attempt import _root
    _need(type(attempt_number) is int and attempt_number>=1, 'Require an exact positive attempt number')
    root=_root(directory)
    with exclusive_lock(root/'request.lock'):
        state=complete.inspect_dictionary_request(root)
        _need(state['state']=='RECORDED' and state['availability'] in {'AVAILABLE','EXHAUSTED'}
              and attempt_number<=len(state['attempts']), 'Require a known-stopped complete request')
        request=state['request'];config=request['configuration'];row=state['attempts'][attempt_number-1]
        _need(config.get('artifact_policy')==ARTIFACT_POLICY and row['state']=='STOPPED'
              and row['finished']['outcome']=='RETURNED', 'Require a returned current-partition attempt')
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
        return write_record(folder/'archive.json',dict(schema_version=1,policy_id=POLICY_ID,
            request_sha256=request['record_sha256'],attempt_sha256=row['intent']['record_sha256'],
            number=attempt_number,finished_sha256=finished_sha,
            archive=dict(path='evidence.zip',sha256=digest,size=archive.stat().st_size)))
