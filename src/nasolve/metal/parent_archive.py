"""Bounded transport of an explicit portable parent layout.

Transport is not scientific validation, execution authorization, a reuse cache
or retirement authority. The caller owns layout/dependency completeness and
must use the ordinary scientific readers after materialization. Captured code
is data. No source discovery, automatic name rewriting or native execution.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
import os
import shutil
import secrets

from .. import cif_runtime_evidence as owner
from ..campaign_records import _sync_directory
from ..cif_dictionary_sites import _need, _read
from .recipe import checksum

KIND = 'metal-parent-input-archive'
MANIFEST = 'parent.json'
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_PARTS = 8
DEFAULT_DISK_BYTES = 256 * 1024 * 1024
DEFAULT_RESERVE_BYTES = 256 * 1024 * 1024
_PART_TARGET_BYTES = 24 * 1024 * 1024
_PARENT_ACTIVE = ContextVar('metal_parent_snapshot_active', default=False)


def _integer(value, label, minimum=0):
    _need(type(value) is int and value >= minimum, 'Invalid '+label)


def _path(path):
    p=Path(path).expanduser().absolute()
    _need(not any(q.is_symlink() for q in (p,*p.parents)), 'Unsafe parent transport path')
    return p


def _manifest(directory, digest):
    checksum(digest,'expected parent manifest identity')
    directory=_path(directory);p=_path(directory/MANIFEST)
    _need(p.is_file() and p.stat().st_size<=MAX_MANIFEST_BYTES, 'Missing or oversized parent manifest')
    raw=_read(p)
    _need(len(raw)<=MAX_MANIFEST_BYTES and sha256(raw).hexdigest()==digest, 'Parent manifest changed')
    value=owner._parse_json(raw)
    _need(isinstance(value,dict) and set(value)=={'kind','schema_version','index','parts'}
          and value['kind']==KIND and type(value['schema_version']) is int
          and value['schema_version']==1, 'Unsupported parent transport manifest')
    owner._index(value['index'])
    parts=value['parts']
    _need(isinstance(parts,list) and 1<=len(parts)<=MAX_PARTS, 'Invalid parent part count')
    for i,ref in enumerate(parts,1):
        _need(isinstance(ref,dict) and set(ref)=={'name','sha256','bytes'}
              and ref['name']==f'part-{i:03d}.zip', 'Unsafe or repeated parent part')
        checksum(ref['sha256'],'parent part identity')
        _integer(ref['bytes'],'part bytes',1)
        _need(ref['bytes']<=owner.MAX_ARCHIVE_BYTES, 'Parent part exceeds shared archive bound')
    _need(sum(r['bytes'] for r in parts)<=owner.MAX_BYTES, 'Parent compressed parts exceed bound')
    return value


def _part_bytes(directory, ref):
    p=_path(directory/ref['name'])
    _need(p.is_file() and p.stat().st_size==ref['bytes'], 'Missing or changed parent part')
    raw=_read(p)
    _need(len(raw)==ref['bytes'] and sha256(raw).hexdigest()==ref['sha256'], 'Parent part changed')
    return raw


def _decode(directory, data, digest):
    # The shared working owner has read the manifest; also bind it to the
    # current declared parts directory, without a fallback to source paths.
    value=_manifest(directory,digest)
    _need(sha256(data).hexdigest()==digest, 'Parent manifest changed during expansion')
    files,dirs,total=owner._index(value['index'])
    merged={};directories=set();objects={}
    for ref in value['parts']:
        sub,payloads,_=owner._decode(_part_bytes(directory,ref),ref['sha256'])
        _need(not set(merged).intersection(sub['files']), 'Repeated logical member across parent parts')
        merged.update(sub['files']);directories.update(sub['directories'])
        for h,raw in payloads.items():
            _need(h not in objects or objects[h]==raw, 'Conflicting parent object')
            objects[h]=raw
        _need(sum(map(len,objects.values()))<=owner.MAX_BYTES, 'Parent objects exceed shared bound')
    _need(merged==files and sorted(directories)==dirs, 'Parent parts differ from complete index')
    return value['index'],objects,total


def _index(root, contents):
    result=dict(schema_version=1,policy_id=owner.POLICY_ID,
        files={name:dict(sha256=sha256(raw).hexdigest(),size=len(raw)) for name,raw in contents.items()},
        directories=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()))
    owner._index(result)
    return result


def _write(path, raw):
    with path.open('xb') as handle:
        handle.write(raw);handle.flush();os.fsync(handle.fileno())


def pack_parent_inputs(layout, output):
    """Pack a caller-declared portable layout, preserving exact paths/bytes.

    Shared logical/member/object bounds remain unchanged. Parts stay below the
    original compressed cap. The output directory must be fresh and separate.
    The manifest is published last; an interrupted partial output is not a
    completed archive and is retained for explicit inspection, not overwritten.
    This function does not prove dependency completeness or retire any source.
    """
    root=_path(layout);output=_path(output)
    _need(root.is_dir() and not output.exists()
          and not output.resolve().is_relative_to(root.resolve()), 'Require a fresh separate parent archive')
    contents=owner._tree(root);index=_index(root,contents)
    objects={index['files'][name]['sha256']:raw for name,raw in contents.items()}
    groups=[];group=[];size=0
    for h in sorted(objects):
        if group and (size+len(objects[h])>_PART_TARGET_BYTES or len(group)+2>=1024):
            groups.append(group);group=[];size=0
        group.append(h);size+=len(objects[h])
    if group:groups.append(group)
    _need(1<=len(groups)<=MAX_PARTS, 'Parent needs too many bounded archive parts')
    encoded=[];parts=[]
    for i,group in enumerate(groups,1):
        keys=set(group)
        sub=dict(index,files={n:r for n,r in index['files'].items() if r['sha256'] in keys})
        raw,digest=owner._archive_bytes(sub,{h:objects[h] for h in group})
        owner._decode(raw,digest)  # Same decoder/caps as the cold reader.
        parts.append(dict(name=f'part-{i:03d}.zip',sha256=digest,bytes=len(raw)))
        encoded.append(raw)
    value=dict(kind=KIND,schema_version=1,index=index,parts=parts)
    manifest=owner._json_bytes(value);digest=sha256(manifest).hexdigest()
    _need(len(manifest)<=MAX_MANIFEST_BYTES and sum(map(len,encoded))<=owner.MAX_BYTES,
          'Parent transport exceeds metadata/compressed bounds')
    _need(owner._tree(root)==contents and _index(root,contents)==index,
          'Parent source changed during packing')
    output.mkdir()  # Exclusive reservation; do not adopt an existing directory.
    for ref,raw in zip(parts,encoded):_write(output/ref['name'],raw)
    _sync_directory(output)
    _need(owner._tree(root)==contents and _index(root,contents)==index,
          'Parent source changed before manifest publication')
    _write(output/MANIFEST,manifest);_sync_directory(output);_sync_directory(output.parent)
    return dict(kind=KIND,schema_version=1,manifest_sha256=digest,
        logical_files=len(contents),logical_bytes=sum(map(len,contents.values())),
        unique_files=len(objects),unique_bytes=sum(map(len,objects.values())),
        parts=len(parts),archive_bytes=sum(map(len,encoded)),manifest_bytes=len(manifest),
        scientific_validation=False,execution_authorized=False,reuse_authorized=False,
        retirement_authorized=False,software_environment_identity_complete=False)


def _verify_snapshot(root,index):
    actual=owner._tree(root)
    _need(_index(root,actual)==index, 'Protected parent snapshot changed')


def _unlock(root):
    if root.is_symlink() or not root.is_dir():return
    root.chmod(0o700)
    for current,dirs,_ in os.walk(root,followlinks=False):
        for name in dirs:
            p=Path(current)/name
            if not p.is_symlink():p.chmod(0o700)


@contextmanager
def materialized_parent_inputs(directory, manifest_sha256, *,
                               max_disk_bytes=DEFAULT_DISK_BYTES,
                               reserve_bytes=DEFAULT_RESERVE_BYTES,
                               scratch_directory=None):
    """Yield (temporary parent root, transport receipt) with no open archive scope.

    The caller replays its ordinary scientific owner inside this scope. Full
    entry/exit hashes and read-only modes detect observed changes; these are not
    isolation against same-user/privileged mutation. Paths expire on exit.
    Budgets include retained parts/manifest, copy overlap and one shared reader
    allowance. They are per invocation, not RAM limits or campaign reservations.
    Nested parent snapshots in this context are refused; concurrent independent
    tasks need their own aggregate reservation owner. No native code is run.
    """
    _need(not _PARENT_ACTIVE.get(), 'A parent scope is already active')
    _integer(max_disk_bytes,'parent disk budget',1);_integer(reserve_bytes,'free-space reserve')
    directory=_path(directory);value=_manifest(directory,manifest_sha256)
    files,_,logical=owner._index(value['index'])
    compressed=sum(r['bytes'] for r in value['parts'])
    manifest_bytes=(directory/MANIFEST).stat().st_size
    bound=compressed+manifest_bytes+max(2*logical,logical+owner.MAX_ACTIVE_BYTES)
    _need(bound<=max_disk_bytes, 'Parent snapshot exceeds declared disk budget')
    scratch=Path(scratch_directory if scratch_directory is not None else gettempdir()).expanduser().resolve()
    # The unchanged archive owner and ordinary readers use the system temp
    # filesystem. If a caller chooses another device, conservatively require
    # the allowance on each device; never charge its free space to the other.
    _need(scratch.is_dir(), 'Parent scratch directory is unavailable')
    devices={}
    for path in (scratch,Path(gettempdir()).resolve()):devices[path.stat().st_dev]=path
    _need(all(shutil.disk_usage(p).free>=max_disk_bytes+reserve_bytes for p in devices.values()),
          'Insufficient scratch space plus declared reserve')
    receipt=dict(kind=KIND,manifest_sha256=manifest_sha256,logical_bytes=logical,
        archive_bytes=compressed,manifest_bytes=manifest_bytes,disk_bound_bytes=bound,
        max_disk_bytes=max_disk_bytes,transport_scope_closed=False,inputs_unchanged=False,
        snapshot_removed=False,scientific_validation=False,execution_authorized=False,
        reuse_authorized=False,retirement_authorized=False)
    token=_PARENT_ACTIVE.set(True);root=None
    try:
        with TemporaryDirectory(prefix='metal-parent-',dir=scratch) as temporary:
            root=Path(temporary)/'parent'
            try:
                with owner._working_evidence(directory/MANIFEST,manifest_sha256,
                        decoder=lambda data,digest:_decode(directory,data,digest)) as view:
                    shutil.copytree(view/'evidence',root)
                _need(not view.exists(), 'Parent transport scope did not close')
                receipt['transport_scope_closed']=True
                _verify_snapshot(root,value['index'])
                for p in root.rglob('*'):p.chmod(0o500 if p.is_dir() else 0o400)
                root.chmod(0o500)
                try:yield root,receipt
                finally:
                    _verify_snapshot(root,value['index'])
                    _need(_manifest(directory,manifest_sha256)==value, 'Retained parent manifest changed')
                    for ref in value['parts']:_part_bytes(directory,ref)
                    receipt['inputs_unchanged']=True
            finally:_unlock(root)
    finally:
        receipt['snapshot_removed']=root is not None and not root.exists()
        _PARENT_ACTIVE.reset(token)


_RETAINED_PARENT = ContextVar('metal_retained_parent', default=None)
READ_KIND = 'metal-parent-input-read'


class _RetainedParent:
    """Opaque, context-local lifetime owner; never a cached scientific verdict."""
    __slots__ = ('directory','digest','root','receipt','active','reading','invalidated','scope_id','storage_budget')

    def __init__(self,directory,digest,root,receipt,scope_id=None):
        self.directory=directory;self.digest=digest;self.root=root;self.receipt=receipt
        self.active=True;self.reading=False;self.invalidated=False
        self.scope_id=secrets.token_hex(32) if scope_id is None else checksum(scope_id,'owned parent scope identity')
        self.storage_budget=None

    def verify(self):
        _need(not self.invalidated, 'Retained parent was invalidated; open a fresh scope')
        try:
            _need(self.active and _RETAINED_PARENT.get() is self, 'Retained parent expired during read')
            # The independently supplied digest remains authoritative. Neither
            # a handle nor an earlier read substitutes for current byte checks.
            value=_manifest(self.directory,self.digest)
            for ref in value['parts']:_part_bytes(self.directory,ref)
            _verify_snapshot(self.root,value['index'])
        except BaseException:
            self.invalidated=True
            raise


@contextmanager
def retained_parent_inputs(directory, manifest_sha256, *,
                           max_disk_bytes=DEFAULT_DISK_BYTES,
                           reserve_bytes=DEFAULT_RESERVE_BYTES,
                           scratch_directory=None,storage_budget=None):
    """Use the ordinary retained owner, optionally binding an explicit budget.

    Default behavior is unchanged. Budgeted scopes delegate only storage lifecycle
    bookkeeping; materialization, serial reads and byte checks keep their owner.
    """
    options=dict(max_disk_bytes=max_disk_bytes,reserve_bytes=reserve_bytes,
                 scratch_directory=scratch_directory)
    if storage_budget is None:
        with _retained_parent_inputs(directory,manifest_sha256,**options) as retained:
            yield retained
    else:
        from . import parent_budget
        with parent_budget.retained_parent_inputs(directory,manifest_sha256,
                storage_budget=storage_budget,**options) as retained:
            yield retained


@contextmanager
def _retained_parent_inputs(directory, manifest_sha256, *,
                           max_disk_bytes=DEFAULT_DISK_BYTES,
                           reserve_bytes=DEFAULT_RESERVE_BYTES,
                           scratch_directory=None,scope_id=None):
    """Retain one owned read-only snapshot for serial, explicit parent reads.

    The existing transport owner expands/copies once and closes its archive
    scope before yielding this opaque handle. Each read still hashes the full
    snapshot and pinned archive on entry/exit and replays its scientific owner.
    No source files are linked, chmodded or retired. Only this owned temporary
    snapshot is removed on normal/exceptional exit. Abrupt process termination
    may leave scratch; this is not crash recovery or campaign quota ownership.
    """
    directory=_path(directory)
    with materialized_parent_inputs(directory,manifest_sha256,max_disk_bytes=max_disk_bytes,
            reserve_bytes=reserve_bytes,scratch_directory=scratch_directory) as (root,receipt):
        retained=_RetainedParent(directory,manifest_sha256,root,receipt,scope_id=scope_id)
        token=_RETAINED_PARENT.set(retained)
        try:
            yield retained
            _need(not retained.reading, 'Cannot close retained parent with an active read')
        finally:
            retained.active=False
            _RETAINED_PARENT.reset(token)


@contextmanager
def read_parent_inputs(directory, manifest_sha256, *, retained_parent=None,
                       max_disk_bytes=DEFAULT_DISK_BYTES):
    """Read one pinned parent, optionally borrowing its explicit retained scope.

    An ordinary call keeps the existing one-shot receipt. A borrowed read returns
    a distinct read receipt: its read scope closes, but snapshot cleanup belongs
    to the outer retained scope. It never claims that the snapshot was removed.
    Handles expire on exit, cannot be substituted across directories/digests or
    contexts, and do not permit overlapping reads. Detected changes or consumer
    exceptions invalidate the handle even if the offending bytes are restored.
    """
    if retained_parent is None:
        with materialized_parent_inputs(directory,manifest_sha256,max_disk_bytes=max_disk_bytes) as value:
            yield value
        return
    retained=retained_parent
    _need(type(retained) is _RetainedParent and retained.active
          and _RETAINED_PARENT.get() is retained, 'Require an active retained parent in this context')
    _need(not retained.reading, 'Retained parent already has an active read')
    _need(_path(directory)==retained.directory and manifest_sha256==retained.digest,
          'Retained parent directory or digest substituted')
    _integer(max_disk_bytes,'parent disk budget',1)
    _need(retained.receipt['disk_bound_bytes']<=max_disk_bytes, 'Retained parent exceeds read disk budget')
    retained.verify()
    receipt=dict(retained.receipt,kind=READ_KIND,schema_version=1,max_disk_bytes=max_disk_bytes,
        retained_snapshot=True,read_scope_closed=False,snapshot_removed=False,inputs_unchanged=False,
        consumer_completed=False)
    retained.reading=True
    try:
        try:yield retained.root,receipt
        except BaseException:
            # Still check exact bytes below, but never continue an interrupted
            # consumer's lifetime as if it completed normally.
            try:
                retained.verify()
                receipt['inputs_unchanged']=True
            finally:retained.invalidated=True
            raise
        else:
            retained.verify()
            receipt['inputs_unchanged']=True
            receipt['consumer_completed']=True
    finally:
        retained.reading=False
        receipt['read_scope_closed']=True


def retained_parent_binding(retained,directory,manifest_sha256):
    """Bind the active context-local lifetime, without granting execution/reuse."""
    _need(type(retained) is _RetainedParent and retained.active
          and _RETAINED_PARENT.get() is retained and not retained.reading
          and not retained.invalidated, 'Require an idle valid retained parent scope')
    _need(_path(directory)==retained.directory and manifest_sha256==retained.digest,
          'Retained parent directory or digest substituted')
    return dict(kind='metal-retained-parent-scope',schema_version=1,scope_id=retained.scope_id,
        parent_manifest_sha256=manifest_sha256,lifetime='CONTEXT_LOCAL_SERIAL_READS',
        snapshot_cleanup='OWNED_BY_OUTER_SCOPE',worker_inherits_snapshot=False)


def validate_parent_binding(value,manifest_sha256):
    """Validate recorded lifetime identity; it is not a live handle or authority."""
    _need(isinstance(value,dict) and set(value)=={'kind','schema_version','scope_id',
        'parent_manifest_sha256','lifetime','snapshot_cleanup','worker_inherits_snapshot'},
        'Invalid recorded retained-parent scope')
    checksum(value['scope_id'],'retained parent scope identity')
    _need(value['kind']=='metal-retained-parent-scope' and type(value['schema_version']) is int
        and value['schema_version']==1 and value['parent_manifest_sha256']==manifest_sha256
        and value['lifetime']=='CONTEXT_LOCAL_SERIAL_READS'
        and value['snapshot_cleanup']=='OWNED_BY_OUTER_SCOPE' and value['worker_inherits_snapshot'] is False,
        'Changed recorded retained-parent scope')


def validate_parent_read(value,manifest_sha256,*,completed=False):
    """Check saved read semantics without pretending to reacquire its parent."""
    fields={'kind','schema_version','manifest_sha256','logical_bytes','archive_bytes','manifest_bytes',
        'disk_bound_bytes','max_disk_bytes','transport_scope_closed','inputs_unchanged','snapshot_removed',
        'scientific_validation','execution_authorized','reuse_authorized','retirement_authorized',
        'retained_snapshot','read_scope_closed','consumer_completed'}
    _need(isinstance(value,dict) and set(value)==fields and value['kind']==READ_KIND
        and type(value['schema_version']) is int and value['schema_version']==1
        and value['manifest_sha256']==manifest_sha256, 'Invalid retained parent read receipt')
    for field in ('logical_bytes','archive_bytes','manifest_bytes','disk_bound_bytes','max_disk_bytes'):
        _integer(value[field],field,1)
    logical=value['logical_bytes'];compressed=value['archive_bytes'];manifest=value['manifest_bytes']
    _need(logical<=owner.MAX_BYTES and compressed<=owner.MAX_BYTES and manifest<=MAX_MANIFEST_BYTES
        and value['disk_bound_bytes']==compressed+manifest+max(2*logical,logical+owner.MAX_ACTIVE_BYTES)
        and value['disk_bound_bytes']<=value['max_disk_bytes'], 'Invalid retained read budget')
    _need(all(value[k] is True for k in ('transport_scope_closed','retained_snapshot','read_scope_closed'))
        and all(value[k] is False for k in ('snapshot_removed','scientific_validation','execution_authorized',
            'reuse_authorized','retirement_authorized'))
        and all(type(value[k]) is bool for k in ('inputs_unchanged','consumer_completed')),
        'Invalid retained read lifecycle')
    _need(not value['consumer_completed'] or value['inputs_unchanged'], 'Completed read has changed inputs')
    if completed:_need(value['consumer_completed'] and value['inputs_unchanged'], 'Retained parent read did not complete')
