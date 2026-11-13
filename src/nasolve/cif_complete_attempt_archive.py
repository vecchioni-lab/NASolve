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
from .campaign_records import read_record, _sync_directory
from .cif_dictionary_sites import _need, _read

POLICY_ID = 'cif-complete-attempt-working-archive-v1'
ARTIFACT_POLICY = 'cif-complete-request-partitioned-artifacts-v2'
REPAIR_RUNTIME = 'repair/attempts/attempt-0001/execution/runtime/'
CONTINUATION_RUNTIME = 'continuation/runtime/'


def _prefixes(artifact_policy, with_continuation):
    _need(artifact_policy == ARTIFACT_POLICY and type(with_continuation) is bool,
          'Unsupported complete-attempt archive partition policy')
    # Most specific prefix wins, exactly as in the owner's bounded inventory.
    return (REPAIR_RUNTIME, CONTINUATION_RUNTIME, 'continuation/') if with_continuation else (REPAIR_RUNTIME,)


def _index(value):
    _need(isinstance(value,dict) and set(value)=={'schema_version','policy_id','artifact_policy',
          'with_continuation','finished_sha256','files','directories'}
          and type(value['schema_version']) is int and value['schema_version']==1
          and value['policy_id']==POLICY_ID, 'Unsupported complete-attempt working index')
    prefixes=_prefixes(value['artifact_policy'],value['with_continuation'])
    files=value['files'];directories=value['directories']
    storage._file_index(files,directories,max_files=(1+len(prefixes))*storage.MAX_FILES)
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


def _decode(data, digest):
    index,objects,total=storage._decode(data,digest,index_reader=_index)
    finished=storage._parse_json(objects[index['finished_sha256']])
    expected=dict(files={n:r for n,r in index['files'].items() if n!='finished.json'},
                  directories=index['directories'])
    _need(isinstance(finished,dict) and finished.get('artifacts')==expected,
          'Working archive differs from the original sealed inventory')
    return index,objects,total


def pack_complete_attempt_evidence(directory, output, *, artifact_policy, with_continuation):
    """Pack a matching sealed inventory; no source retirement or native execution."""
    from .cif_complete_request import _attempt_files
    from .cif_repair_attempt import _root
    _prefixes(artifact_policy,with_continuation)
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
    _index(index)
    unique={r['sha256']:r['size'] for r in files.values()}
    _need(len(unique)+2<=1024 and sum(unique.values())<=storage.MAX_ACTIVE_BYTES,
          'Complete-attempt objects exceed shared archive/physical bounds')
    objects={}
    for name,ref in files.items():
        if ref['sha256'] not in objects:
            data=_read(root/name)
            _need(len(data)==ref['size'] and sha256(data).hexdigest()==ref['sha256'],
                  'Attempt source changed during compression')
            objects[ref['sha256']]=data
    data,digest=storage._archive_bytes(index,objects)
    _decode(data,digest)
    _need(_attempt_files(root,artifact_policy=artifact_policy,with_continuation=with_continuation)==before
          and _read(root/'finished.json')==finished_bytes, 'Attempt inventory changed during compression')
    with output.open('xb') as handle:
        handle.write(data);handle.flush();os.fsync(handle.fileno())
    _sync_directory(output.parent)
    return dict(policy_id=POLICY_ID,logical_files=len(files),logical_bytes=sum(r['size'] for r in files.values()),
        unique_files=len(objects),unique_bytes=sum(map(len,objects.values())),
        archive_bytes=len(data),archive_sha256=digest,finished_sha256=finished_sha256)


@contextmanager
def expanded_complete_attempt_evidence(archive, digest, *, finished_sha256):
    """Keep all reconstructed paths inside one root-only, physically bounded view.

    The caller supplies the original sealed finished-file checksum, then replays
    the existing complete-attempt owner inside this scope. No paths are published.
    """
    _need(isinstance(finished_sha256,str) and storage._SHA.fullmatch(finished_sha256),
          'Require the original finished-file checksum')
    def expected_decode(data, digest):
        index,objects,total=_decode(data,digest)
        _need(index['finished_sha256']==finished_sha256, 'Working archive belongs to a different finished owner')
        return index,objects,total
    with storage._working_evidence(archive,digest,decoder=expected_decode) as view:
        yield view
