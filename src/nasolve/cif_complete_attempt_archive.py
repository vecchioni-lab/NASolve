"""Exact archive transport for an already sealed complete-attempt inventory.

The owner's existing partitions retain their logical limits. One shared object
store and C254 outer view retain the physical limit. This layer checks transport,
not process ownership or chemistry; callers must replay the existing owner before
using results. It never removes a source file or changes a scientific receipt.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import os

from . import cif_runtime_evidence as storage
from . import cif_complete_stages as stages, cif_complete_staged_archive as packed
from .campaign_records import read_record, _sync_directory
from .cif_dictionary_sites import _need, _read

POLICY_ID = 'cif-complete-attempt-working-archive-v1'
ARTIFACT_POLICY = 'cif-complete-request-partitioned-artifacts-v3'
SUPPORTED_ARTIFACT_POLICIES = frozenset({
    'cif-complete-request-partitioned-artifacts-v2', ARTIFACT_POLICY,
    'cif-complete-request-partitioned-artifacts-v4', stages.POLICY_ID})
REPAIR_RUNTIME = 'repair/attempts/attempt-0001/execution/runtime/'
CONTINUATION_RUNTIME = 'continuation/runtime/'


def _prefixes(artifact_policy, with_continuation):
    from .cif_complete_request import _artifact_partitions
    _need(type(artifact_policy) is str and artifact_policy in SUPPORTED_ARTIFACT_POLICIES
          and type(with_continuation) is bool,
          'Unsupported complete-attempt archive partition policy')
    # Use the owner's exact boundaries and longest-prefix order on both paths.
    return _artifact_partitions(artifact_policy, with_continuation)


def _index(value):
    _need(isinstance(value,dict) and set(value)=={'schema_version','policy_id','artifact_policy',
          'with_continuation','finished_sha256','files','directories'}
          and type(value['schema_version']) is int and (
              (value['schema_version']==1 and value['policy_id']==POLICY_ID) or
              (value['schema_version']==2 and value['policy_id']==packed.POLICY_ID and value['artifact_policy']==stages.POLICY_ID)
          ), 'Unsupported complete-attempt working index')
    prefixes=_prefixes(value['artifact_policy'],value['with_continuation'])
    files=value['files'];directories=value['directories']
    # The staged encoding adds one storage directory outside the original
    # inventory. check_projection verifies its exact identity and contents.
    storage._file_index(files, directories, max_files=(1+len(prefixes))*storage.MAX_FILES,
                        extra_directories=int(value['schema_version']==2))
    if value['schema_version'] == 2:
        unique = {r['sha256']:r['size'] for r in files.values()}
        _need(len(unique)+2 <= 1024 and sum(unique.values()) <= storage.MAX_ACTIVE_BYTES,
              'Staged objects exceed shared archive/physical bounds')
    elif value['artifact_policy'] == stages.POLICY_ID:
        bounds = stages.AttemptBounds(prefixes)
        for name, ref in files.items():
            bounds.charge(name, ref['size'])
    else:
        partitions={p:[] for p in (*prefixes,'')}
        for name,ref in files.items():
            partitions[next((p for p in prefixes if name.startswith(p)),'')].append(ref)
        for rows in partitions.values():
            _need(len(rows)<=storage.MAX_FILES and sum(r['size'] for r in rows)<=storage.MAX_BYTES,
                  'Complete-attempt archive exceeds an owner partition bound')
    finished=value['finished_sha256']
    _need(isinstance(finished,str) and storage._SHA.fullmatch(finished)
          and files.get('finished.json',{}).get('sha256')==finished,
          'Complete-attempt archive has a different finished-file binding')
    return files,directories,sum(r['size'] for r in files.values())


def _decode(data, digest, *, bind_view=None):
    index,objects,total=storage._decode(data,digest,index_reader=_index)
    finished=storage._parse_json(objects[index['finished_sha256']])
    if index['schema_version'] == 2:
        prefixes = _prefixes(index['artifact_policy'], index['with_continuation'])
        original = packed.validate_contents(index, objects, prefixes, finished)
        if bind_view is not None:
            bind_view(index, original)
    else:
        expected=dict(files={n:r for n,r in index['files'].items() if n!='finished.json'},
                      directories=index['directories'])
        _need(isinstance(finished,dict) and finished.get('artifacts')==expected,
              'Working archive differs from the original sealed inventory')
    return index,objects,total


def pack_complete_attempt_evidence(directory, output, *, artifact_policy, with_continuation):
    """Pack a matching sealed inventory; no source retirement or native execution."""
    from .cif_complete_request import _attempt_files
    from .cif_repair_attempt import _root
    prefixes = _prefixes(artifact_policy,with_continuation)
    root=_root(directory);output=Path(output).absolute()
    _need(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents))
          and not output.resolve().is_relative_to(root), 'Require a fresh separate attempt archive')
    before=_attempt_files(root,artifact_policy=artifact_policy,with_continuation=with_continuation)
    finished_bytes=_read(root/'finished.json');finished=read_record(root/'finished.json')
    intent=read_record(root/'attempt.json')
    _need(finished.get('outcome')=='RETURNED' and finished.get('stopped_verified') is True
          and finished.get('attempt_sha256')==intent['record_sha256']
          and finished.get('artifacts')==before,
          'Complete-attempt archive requires its matching sealed artifacts/inventory')
    finished_sha256=sha256(finished_bytes).hexdigest()
    files=dict(before['files'], **{'finished.json':dict(sha256=finished_sha256,size=len(finished_bytes))})
    index=dict(schema_version=1,policy_id=POLICY_ID,artifact_policy=artifact_policy,
        with_continuation=with_continuation,finished_sha256=finished_sha256,
        files=files,directories=before['directories'])
    unique={r['sha256']:r['size'] for r in files.values()}
    detail = {}
    if artifact_policy == stages.POLICY_ID and any(stages.stage_root(name) for name in files):
        projected, directories, objects = packed.encode(root, files, before['directories'], prefixes)
        index.update(schema_version=2, policy_id=packed.POLICY_ID, files=projected, directories=directories)
        detail = dict(working_unique_bytes=sum(map(len,objects.values())),
                      encoded_only_files=sum(name.startswith(packed.PACKED+'/') for name in projected))
    else:
        _need(len(unique)+2<=1024 and sum(unique.values())<=storage.MAX_ACTIVE_BYTES,
              'Complete-attempt objects exceed shared archive/physical bounds')
        objects={}
        for name,ref in files.items():
            if ref['sha256'] not in objects:
                data=_read(root/name)
                _need(len(data)==ref['size'] and sha256(data).hexdigest()==ref['sha256'],
                      'Attempt source changed during compression')
                objects[ref['sha256']]=data
    _index(index)
    data,digest=storage._archive_bytes(index,objects)
    if index['schema_version'] == 2:
        _need(len(data) <= storage.MAX_ARCHIVE_BYTES, 'Staged attempt exceeds the shared archive file bound')
    _decode(data,digest)
    _need(_attempt_files(root,artifact_policy=artifact_policy,with_continuation=with_continuation)==before
          and _read(root/'finished.json')==finished_bytes, 'Attempt inventory changed during compression')
    with output.open('xb') as handle:
        handle.write(data);handle.flush();os.fsync(handle.fileno())
    _sync_directory(output.parent)
    return dict(policy_id=index['policy_id'],logical_files=len(files),logical_bytes=sum(r['size'] for r in files.values()),
        unique_files=len(unique),unique_bytes=sum(unique.values()),**detail,
        archive_bytes=len(data),archive_sha256=digest,finished_sha256=finished_sha256)


@contextmanager
def expanded_complete_attempt_evidence(archive, digest, *, finished_sha256, artifact_policy=None):
    """Keep all reconstructed paths inside one root-only, physically bounded view.

    The caller supplies the original completion checksum and replays its owner
    inside this scope. Compact mixed attempts retain the ordinary working
    directories and public files. Use read_complete_attempt_member for a
    private intermediate file that exists only in compressed storage.
    """
    _need(isinstance(finished_sha256,str) and storage._SHA.fullmatch(finished_sha256),
          'Require the original finished-file checksum')
    _need(artifact_policy is None or (type(artifact_policy) is str
          and artifact_policy in SUPPORTED_ARTIFACT_POLICIES), 'Unsupported expected owner partition policy')
    staged_view = None
    def bind_view(index, original):
        nonlocal staged_view
        staged_view = (index, original)

    def expected_decode(data, digest):
        index,objects,total=_decode(data,digest,bind_view=bind_view)
        _need(artifact_policy is None or index['artifact_policy']==artifact_policy,
              'Working archive partition policy differs from frozen owner')
        _need(index['finished_sha256']==finished_sha256, 'Working archive belongs to a different finished owner')
        return index,objects,total
    with storage._working_evidence(archive,digest,decoder=expected_decode) as view:
        if staged_view is None:
            yield view
        else:
            with packed.owner_view(view/'evidence', *staged_view):
                yield view


def read_complete_attempt_member(evidence_directory, name):
    """Read one exact original working file inside an expanded complete-attempt view.

    A staged view keeps public models and process records at their paths. Some
    private intermediate files share verified objects and are read individually.
    """
    return packed.read_member(evidence_directory, name)
