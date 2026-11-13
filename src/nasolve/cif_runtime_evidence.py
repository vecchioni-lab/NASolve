"""Compact exact runtime evidence, reusing Cedar's bounded archive verifier.

Objects are stored once by content hash. Logical scientific paths are reconstructed
only in a temporary read view; captured programs and nested payloads are never run.
This storage layer grants no chemical or numerical qualification.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
from tempfile import TemporaryDirectory
import zipfile

from .cif_component_runtime import _tree, MAX_FILES, MAX_BYTES, MAX_FILE_BYTES
from .cif_dictionary_sites import _need, _read
from .cif_mixed_runtime_source import archive_members, MAX_ARCHIVE_BYTES
from .cif_review_transport import _parse_json, _json_bytes, _strict, _unique, _alias

POLICY_ID = 'cif-content-addressed-runtime-evidence-v1'
ARCHIVE = 'evidence.zip'
MAX_ACTIVE_BYTES = MAX_BYTES
_ACTIVE_BYTES = ContextVar('runtime_evidence_expanded_bytes', default=0)
_ACTIVE_OBJECTS = ContextVar('runtime_evidence_objects', default=None)
_ACTIVE_DEPTH = ContextVar('runtime_evidence_depth', default=0)
_WORKING_VIEW_ACTIVE = ContextVar('working_evidence_view_active', default=False)
MAX_DEPTH = 2
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _index(value):
    _need(isinstance(value,dict) and set(value)=={'schema_version','policy_id','files','directories'}
          and type(value['schema_version']) is int and value['schema_version']==1
          and value['policy_id']==POLICY_ID, 'Unsupported compact evidence index')
    files=value['files'];directories=value['directories']
    _need(isinstance(files,dict) and 0<len(files)<=MAX_FILES
          and all(_strict(name) for name in files), 'Unsafe or excessive logical evidence files')
    _unique(files)
    _need(isinstance(directories,list) and len(directories)<=4*MAX_FILES
          and all(_strict(name) for name in directories)
          and directories==sorted(set(directories))
          and len({_alias(n) for n in directories})==len(directories), 'Unsafe evidence directories')
    file_aliases={_alias(n) for n in files};dir_aliases={_alias(n):n for n in directories}
    for name in [*files,*directories]:
        for parent in PurePosixPath(name).parents:
            if str(parent)=='.':continue
            _need(str(parent) in directories and dir_aliases.get(_alias(str(parent)))==str(parent),
                  'Missing or aliased evidence parent')
    _need(not file_aliases.intersection(dir_aliases), 'Evidence file/directory collision')
    for ref in files.values():
        _need(isinstance(ref,dict) and set(ref)=={'sha256','size'}
              and isinstance(ref['sha256'],str) and _SHA.fullmatch(ref['sha256'])
              and type(ref['size']) is int and 0<=ref['size']<=MAX_FILE_BYTES,
              'Malformed evidence object reference')
    total=sum(r['size'] for r in files.values())
    _need(total<=MAX_BYTES, 'Logical evidence exceeds expanded bounds')
    return files,directories,total


def _decode(data,digest):
    try:
        members=archive_members(data,digest)
        value=_parse_json(members['index.json']);files,directories,total=_index(value)
        objects={name.removeprefix('objects/'):payload for name,payload in members.items() if name.startswith('objects/')}
        expected={r['sha256'] for r in files.values()}
        _need(set(members)=={'manifest.json','index.json'}|{'objects/'+h for h in expected}
              and set(objects)==expected, 'Missing or unused evidence objects')
        _need(all(sha256(data).hexdigest()==h for h,data in objects.items()), 'Evidence object hash differs')
        _need(all(len(objects[r['sha256']])==r['size'] for r in files.values()), 'Evidence object size differs')
        return value,objects,total
    except (KeyError,TypeError,IndexError,zipfile.BadZipFile,NotImplementedError,RuntimeError) as exc:
        raise ValueError('Incomplete or damaged compact evidence') from exc


def pack_runtime_evidence(directory, output):
    """Write a fresh deterministic archive, retaining exact paths and bytes."""
    root=Path(directory).absolute();output=Path(output).absolute()
    _need(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents))
          and not output.resolve().is_relative_to(root.resolve()), 'Require a fresh separate evidence archive')
    before=_tree(root)
    directories=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())
    refs={name:dict(sha256=sha256(data).hexdigest(),size=len(data)) for name,data in before.items()}
    index=dict(schema_version=1,policy_id=POLICY_ID,files=refs,directories=directories)
    _index(index)
    objects={refs[name]['sha256']:data for name,data in before.items()}
    members={'objects/'+h:data for h,data in objects.items()};members['index.json']=_json_bytes(index)
    members['manifest.json']=_json_bytes({name:dict(sha256=sha256(data).hexdigest(),bytes=len(data)) for name,data in members.items()})
    _need(len(members)<=1024, 'Too many unique archive objects')
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(members.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3;info.external_attr=(stat.S_IFREG|0o600)<<16
            archive.writestr(info,data,compresslevel=9)
    data=stream.getvalue();digest=sha256(data).hexdigest()
    _decode(data,digest)  # Same bounds and CRC/object checks as the public reader.
    _need(_tree(root)==before and directories==sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()),
          'Source evidence changed during compression')
    with output.open('xb') as handle:handle.write(data)
    return dict(policy_id=POLICY_ID,logical_files=len(refs),logical_bytes=sum(map(len,before.values())),
                unique_files=len(objects),unique_bytes=sum(map(len,objects.values())),
                archive_bytes=len(data),archive_sha256=digest)


@contextmanager
def expanded_runtime_evidence(archive, digest):
    """Yield one bounded temporary evidence root; no original paths are consulted.

    Each view retains its logical expansion bound. Nested views additionally share
    one physical-byte allowance and reuse identical temporary objects. A platform
    without hard links must charge each real copy to that same allowance.
    """
    _need(_ACTIVE_DEPTH.get()<MAX_DEPTH, 'Nested evidence exceeds supported view depth')
    with _expanded_evidence(archive, digest, runtime_layer=True) as view:
        yield view


@contextmanager
def expanded_working_evidence(archive, digest):
    """Own one outer working-directory view around the existing runtime proof.

    Entry is root-only: a runtime or another working view cannot open this scope.
    Its objects share the same physical-byte budget and temporary-object pool as
    the two permitted runtime layers. Temporary paths expire at scope exit. This
    operation never retires source files, authorizes recovery or qualifies science.
    """
    _need(not _WORKING_VIEW_ACTIVE.get() and _ACTIVE_DEPTH.get() == 0
          and _ACTIVE_BYTES.get() == 0 and _ACTIVE_OBJECTS.get() is None,
          'Working evidence requires an outer root scope')
    token = _WORKING_VIEW_ACTIVE.set(True)
    try:
        with _expanded_evidence(archive, digest, runtime_layer=False) as view:
            yield view
    finally:
        _WORKING_VIEW_ACTIVE.reset(token)


@contextmanager
def _expanded_evidence(archive, digest, *, runtime_layer):
    """One decoder/expander and accounting path for both explicitly owned scopes."""
    archive=Path(archive).absolute()
    _need(archive.is_file() and not any(p.is_symlink() for p in (archive,*archive.parents))
          and archive.stat().st_size<=MAX_ARCHIVE_BYTES, 'Unsafe or oversized evidence archive')
    data=_read(archive);index,objects,total=_decode(data,digest)
    used=_ACTIVE_BYTES.get();written=dict(_ACTIVE_OBJECTS.get() or {})
    _need(used+sum(len(data) for h,data in objects.items() if h not in written)<=MAX_ACTIVE_BYTES,
          'Nested evidence exceeds temporary expansion allowance')
    with TemporaryDirectory(prefix='runtime-evidence-') as temporary:
        view=Path(temporary).resolve();root=view/'evidence';root.mkdir()
        for name in index['directories']:(root/name).mkdir(parents=True,exist_ok=True)
        for name,ref in sorted(index['files'].items()):
            target=root/name;previous=written.get(ref['sha256']);linked=False
            if previous is not None:
                _need(_read(previous)==objects[ref['sha256']], 'Shared temporary evidence changed')
                try:os.link(previous,target);linked=True
                except OSError:pass  # Charge a real copy below; never relax the bound.
            if not linked:
                _need(used+ref['size']<=MAX_ACTIVE_BYTES, 'Copied evidence exceeds temporary expansion allowance')
                target.write_bytes(objects[ref['sha256']]);used+=ref['size']
                written.setdefault(ref['sha256'],target)
            target.chmod(0o400)
        token=_ACTIVE_BYTES.set(used);object_token=_ACTIVE_OBJECTS.set(written)
        depth_token=_ACTIVE_DEPTH.set(_ACTIVE_DEPTH.get()+int(runtime_layer))
        try:yield view
        finally:
            _ACTIVE_DEPTH.reset(depth_token);_ACTIVE_OBJECTS.reset(object_token);_ACTIVE_BYTES.reset(token)
