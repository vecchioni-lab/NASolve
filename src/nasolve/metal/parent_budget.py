"""Bind the ordinary retained parent to recorded closure and space settlement.

Only the live ordinary owner produces closure evidence. Cold inspection verifies
recorded closure and current scratch absence; it cannot replay past reader state
or attribute filesystem free-space changes. No native scheduling or data retirement.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
import shutil

from .. import campaign_records as records
from ..campaign_process import exclusive_lock,CampaignProcessError
from . import parent_archive as parent,storage_budget as budget
from .recipe import checksum,RecipeError

POLICY = 'metal-parent-storage-v1'
CLOSURE = 'metal-parent-storage-closure'
SETTLEMENT = 'metal-parent-storage-settlement'
MAX_PROOF_BYTES = 16384


def _need(value,message):
    if not value:raise RecipeError(message)


def _proof(path):return budget._record(path,MAX_PROOF_BYTES)


def _reference(root,relative):
    return dict(records.artifact(root,relative),anchor='budget_store')


def _scope(root,grant):return records.path_in(root,grant['scope'])


def _scratch_absent(root,grant,snapshot):
    scratch=records.path_in(root,grant['scope']+'/scratch')
    _need(isinstance(snapshot,dict) and set(snapshot)=={'anchor','relative_path'}
          and snapshot['anchor']=='budget_store','Invalid owned snapshot reference')
    path=records.path_in(root,snapshot['relative_path'])
    _need(path.name=='parent' and path.parent.parent==scratch
          and path.parent.name.startswith('metal-parent-'),'Snapshot is outside its declared owned scratch')
    return (not path.exists() and not path.is_symlink()
            and (not scratch.exists() or (scratch.is_dir() and not any(scratch.iterdir()))))


def _measurement(root):
    # Reuse the bounded tree reader, then observe allocation/link facts separately.
    files=parent.owner._tree(root);logical=sum(map(len,files.values()));allocated=0;available=True;links=0
    for name,raw in files.items():
        path=records.path_in(root,name);state=path.lstat()
        _need(state.st_size==len(raw),'Snapshot changed during cleanup measurement')
        links+=int(state.st_nlink!=1)
        if hasattr(state,'st_blocks'):allocated+=state.st_blocks*512
        else:available=False
    return dict(file_count=len(files),logical_bytes=logical,
                allocated_file_bytes=allocated if available else None,files_with_external_links=links)


def _read_closure(root,grant,reservation_id,closure_id):
    checksum(closure_id,'independent parent closure identity')
    scope=_scope(root,grant)
    declaration=_proof(scope/'declaration.json');opened=_proof(scope/'opened.json');closure=_proof(scope/'closure.json')
    _need(declaration.get('kind')=='metal-parent-storage-declaration'
          and type(declaration.get('schema_version')) is int and declaration['schema_version']==1
          and declaration.get('policy_id')==POLICY and declaration.get('grant')==grant
          and declaration.get('reservation_id')==reservation_id,'Parent declaration changed')
    _need(opened.get('kind')=='metal-parent-storage-opening' and type(opened.get('schema_version')) is int
          and opened['schema_version']==1 and opened.get('policy_id')==POLICY
          and opened.get('declaration_id')==declaration['record_sha256'],'Parent opening changed')
    parent.validate_parent_binding(opened.get('parent_scope'),grant['parent_manifest_sha256'])
    _need(opened['parent_scope']['scope_id']==grant['scope_id'],'Parent opening scope substituted')
    fields={'kind','schema_version','policy_id','budget_id','reservation_id','scope_id','parent_manifest_sha256',
            'declaration_id','opened_id','managed_reads_closed','handle_expired','snapshot_removed',
            'transport_scope_closed','inputs_unchanged','parent_invalidated','consumer_outcome',
            'consumer_error','measurement','scientific_acceptance','retirement_authorized','record_sha256'}
    _need(set(closure)==fields and closure['record_sha256']==closure_id
          and closure['kind']==CLOSURE and type(closure['schema_version']) is int and closure['schema_version']==1
          and closure['policy_id']==POLICY and closure['budget_id']==grant['budget_id']
          and closure['reservation_id']==reservation_id and closure['scope_id']==grant['scope_id']
          and closure['parent_manifest_sha256']==grant['parent_manifest_sha256']
          and closure['declaration_id']==declaration['record_sha256'] and closure['opened_id']==opened['record_sha256'],
          'Parent closure identity or linkage changed')
    _need(all(closure[k] is True for k in ('managed_reads_closed','handle_expired','snapshot_removed','transport_scope_closed'))
          and all(type(closure[k]) is bool for k in ('inputs_unchanged','parent_invalidated'))
          and closure['consumer_outcome'] in {'RETURNED','RAISED'}
          and closure['scientific_acceptance']=='NOT_ASSESSED' and closure['retirement_authorized'] is False,
          'Parent closure lacks orderly managed-reference release')
    error=closure['consumer_error']
    _need((closure['consumer_outcome']=='RETURNED' and error is None)
          or (closure['consumer_outcome']=='RAISED' and isinstance(error,dict) and set(error)=={'type','message'}
              and all(isinstance(v,str) and len(v)<=1024 for v in error.values())), 'Invalid recorded consumer outcome')
    measurement=closure['measurement']
    _need(isinstance(measurement,dict) and set(measurement)=={'file_count','logical_bytes','allocated_file_bytes',
          'files_with_external_links','free_bytes_before','free_bytes_after','free_space_delta_bytes',
          'physical_reclaim_verified'},'Invalid cleanup measurement')
    for key in ('file_count','logical_bytes','files_with_external_links','free_bytes_before','free_bytes_after'):
        budget._integer(measurement[key],key)
    if measurement['allocated_file_bytes'] is not None:budget._integer(measurement['allocated_file_bytes'],'allocated file bytes')
    _need(measurement['files_with_external_links']==0 and measurement['physical_reclaim_verified'] is False
          and type(measurement['free_space_delta_bytes']) is int
          and measurement['free_space_delta_bytes']==measurement['free_bytes_after']-measurement['free_bytes_before'],
          'Cleanup measurement cannot claim unverified physical reclamation')
    _need(_scratch_absent(root,grant,opened.get('snapshot')),'Owned parent scratch remains or was recreated')
    return closure


def _check_settlement(root,grant,reservation_id,value):
    fields={'kind','schema_version','reservation_id','closure_id','closure','released_allowance_bytes','retirement_authorized'}
    _need(isinstance(value,dict) and set(value)==fields and value['kind']==SETTLEMENT
          and type(value['schema_version']) is int and value['schema_version']==1
          and value['reservation_id']==reservation_id and type(value['released_allowance_bytes']) is int
          and value['released_allowance_bytes']==grant['allowance_bytes']
          and value['retirement_authorized'] is False,'Unsupported retained-parent settlement')
    _read_closure(root,grant,reservation_id,value['closure_id'])
    _need(value['closure']==_reference(root,grant['scope']+'/closure.json'),'Parent closure bytes changed')



def _active_reservation(root,ledger,retained):
    """Bind a live ordinary handle to its held grant, under the budget lock."""
    _need(type(retained) is parent._RetainedParent,'Require the ordinary retained parent owner')
    binding=parent.retained_parent_binding(retained,retained.directory,retained.digest)
    info=retained.storage_budget
    _need(info is not None and info.get('state')=='ACTIVE'
          and info.get('budget_id')==ledger['budget_id'],'Require an active budgeted retained parent')
    reservation_id=info.get('reservation_id');checksum(reservation_id,'live parent reservation identity')
    budget._parent_reference(ledger,reservation_id,require_held=True)
    grant=ledger['reservations'][reservation_id]['grant'];scope=_scope(root,grant)
    _need(grant['scope_id']==binding['scope_id']==info.get('scope_id')
          and grant['parent_manifest_sha256']==binding['parent_manifest_sha256']
          and grant['scope']==info.get('scope'),'Retained parent grant was substituted')
    declaration=_proof(scope/'declaration.json');opened=_proof(scope/'opened.json')
    _need(declaration.get('kind')=='metal-parent-storage-declaration'
          and type(declaration.get('schema_version')) is int and declaration['schema_version']==1
          and declaration.get('policy_id')==POLICY and declaration.get('grant')==grant
          and declaration.get('reservation_id')==reservation_id
          and opened.get('kind')=='metal-parent-storage-opening'
          and type(opened.get('schema_version')) is int and opened['schema_version']==1
          and opened.get('policy_id')==POLICY
          and opened.get('declaration_id')==declaration['record_sha256']
          and opened.get('parent_scope')==binding
          and opened.get('snapshot')==dict(anchor='budget_store',relative_path=retained.root.relative_to(root).as_posix())
          and not (scope/'closure.json').exists() and not (scope/'failure.json').exists(),
          'Retained parent opening or live ownership changed')
    return reservation_id


def settle_parent(directory, *, budget_id, reservation_id, closure_id):
    """Retry recorded closure settlement, without expansion or native execution."""
    root=budget._root(directory);checksum(reservation_id,'parent reservation identity')
    with exclusive_lock(records.path_in(root,budget.LOCK)):
        config,ledger=budget._read(root,budget_id);item=ledger['reservations'].get(reservation_id)
        _need(item is not None and item['grant'].get('scope_type')=='retained_parent','Require an exact parent reservation')
        grant=item['grant'];_read_closure(root,grant,reservation_id,closure_id)
        if item['settlement'] is not None:
            _need(item['settlement']['closure_id']==closure_id,'Parent already settled against a different closure')
            return item['settlement']
        # A prior writer may have published the closure but failed to acknowledge
        # its directory sync. Repeat that sync before publishing the ledger edge.
        records._sync_directory(_scope(root,grant))
        value=dict(kind=SETTLEMENT,schema_version=1,reservation_id=reservation_id,closure_id=closure_id,
                   closure=_reference(root,grant['scope']+'/closure.json'),released_allowance_bytes=grant['allowance_bytes'],
                   retirement_authorized=False)
        budget._observed(root);item['settlement']=value
        budget._space(root,records.serialized_record_size(ledger),config['free_space_reserve_bytes'])
        _check_settlement(root,grant,reservation_id,value)
        budget._save(root,ledger)
        return value


def inspect_parent_closure(directory, *, budget_id, reservation_id, closure_id):
    """Read recorded owner closure/current absence, not live historical references."""
    root=budget._root(directory);checksum(reservation_id,'parent reservation identity')
    with exclusive_lock(records.path_in(root,budget.LOCK)):
        _,ledger=budget._read(root,budget_id);item=ledger['reservations'].get(reservation_id)
        _need(item is not None and item['grant'].get('scope_type')=='retained_parent','Require an exact parent reservation')
        closure=_read_closure(root,item['grant'],reservation_id,closure_id)
        return dict(kind='metal-parent-storage-inspection',schema_version=1,closure=closure,
                    settled=item['settlement'] is not None,scratch_absent_now=True,
                    verification_scope='RECORDED_OWNER_CLOSURE_AND_CURRENT_SCRATCH_ABSENCE',
                    physical_reclaim_verified=False,scientific_acceptance='NOT_ASSESSED',retirement_authorized=False)


def _error(exc):return dict(type=type(exc).__name__,message=str(exc)[:1024])


@contextmanager
def retained_parent_inputs(directory,manifest_sha256,*,storage_budget,max_disk_bytes,
                           reserve_bytes,scratch_directory):
    """Compose quota bookkeeping with the existing ordinary retained owner."""
    options=storage_budget
    _need(isinstance(options,dict) and set(options)=={'directory','budget_id','scope','allowance_bytes'},
          'Parent storage budget requires directory, budget_id, scope and allowance_bytes')
    _need(scratch_directory is None,'Budgeted parent owns its declared scratch directory')
    root=budget._root(options['directory']);source=parent._path(directory)
    parent._manifest(source,manifest_sha256)
    parent._integer(max_disk_bytes,'parent disk budget',1);parent._integer(reserve_bytes,'free-space reserve')
    _need(root.stat().st_dev==Path(parent.gettempdir()).resolve().stat().st_dev,
          'Budget store and parent expansion must share one filesystem')
    budget._integer(options['allowance_bytes'],'parent allowance',1)
    _need(options['allowance_bytes']>max_disk_bytes+65536,'Parent allowance needs transport and proof headroom')
    proposed=records.path_in(root,options['scope'])
    _need(not proposed.resolve().is_relative_to(source.resolve()),'Parent scope must be outside its protected archive')
    grant=budget.reserve_retained_parent(root,budget_id=options['budget_id'],scope=options['scope'],
        parent_manifest_sha256=manifest_sha256,allowance_bytes=options['allowance_bytes'])
    reservation_id=grant.pop('reservation_id');scope=_scope(root,grant);scope.mkdir();records._sync_directory(scope.parent)
    scratch=scope/'scratch';scratch.mkdir();records._sync_directory(scope)
    declaration=records.write_record(scope/'declaration.json',dict(kind='metal-parent-storage-declaration',schema_version=1,
        policy_id=POLICY,grant=grant,reservation_id=reservation_id,max_disk_bytes=max_disk_bytes,reserve_bytes=reserve_bytes))
    info=dict(budget_id=grant['budget_id'],reservation_id=reservation_id,scope_id=grant['scope_id'],
              scope=grant['scope'],state='OPENING',closure_id=None)
    retained=None;opened=None;measurement=None;ordered=False;error=None
    try:
        with parent._retained_parent_inputs(source,manifest_sha256,max_disk_bytes=max_disk_bytes,
                reserve_bytes=reserve_bytes,scratch_directory=scratch,scope_id=grant['scope_id']) as retained:
            binding=parent.retained_parent_binding(retained,source,manifest_sha256)
            opened=records.write_record(scope/'opened.json',dict(kind='metal-parent-storage-opening',schema_version=1,
                policy_id=POLICY,declaration_id=declaration['record_sha256'],parent_scope=binding,
                snapshot=dict(anchor='budget_store',relative_path=retained.root.relative_to(root).as_posix())))
            retained.storage_budget=MappingProxyType(info);info['state']='ACTIVE'
            try:yield retained
            finally:
                ordered=(retained.active and not retained.reading and parent._RETAINED_PARENT.get() is retained
                         and retained.scope_id==grant['scope_id'] and retained.digest==manifest_sha256
                         and retained.root==records.path_in(root,opened['snapshot']['relative_path']))
                if ordered:
                    measurement=_measurement(retained.root)
                    measurement['free_bytes_before']=shutil.disk_usage(root).free
    except BaseException as exc:
        error=_error(exc)
        raise
    finally:
        try:
            safe=(retained is not None and opened is not None and measurement is not None and ordered
                  and not retained.active and not retained.reading and retained.receipt['snapshot_removed']
                  and retained.receipt['transport_scope_closed'] and measurement['files_with_external_links']==0
                  and _scratch_absent(root,grant,opened['snapshot']))
            if not safe:
                info['state']='UNRESOLVED'
                raise RecipeError('Parent cleanup or managed references remain unresolved')
            _need(_proof(scope/'declaration.json')==declaration and _proof(scope/'opened.json')==opened,
                  'Parent opening proof changed during its lifetime')
            measurement['free_bytes_after']=shutil.disk_usage(root).free
            measurement['free_space_delta_bytes']=measurement['free_bytes_after']-measurement['free_bytes_before']
            measurement['physical_reclaim_verified']=False
            closure=dict(kind=CLOSURE,schema_version=1,policy_id=POLICY,budget_id=grant['budget_id'],reservation_id=reservation_id,
                scope_id=grant['scope_id'],parent_manifest_sha256=manifest_sha256,declaration_id=declaration['record_sha256'],
                opened_id=opened['record_sha256'],managed_reads_closed=True,handle_expired=True,snapshot_removed=True,
                transport_scope_closed=True,inputs_unchanged=retained.receipt['inputs_unchanged'],parent_invalidated=retained.invalidated,
                consumer_outcome='RAISED' if error else 'RETURNED',consumer_error=error,measurement=measurement,
                scientific_acceptance='NOT_ASSESSED',retirement_authorized=False)
            info['state']='CLOSED_HELD'
            info['closure_id']=sha256(records._canonical(closure)).hexdigest()
            saved=records.write_record(scope/'closure.json',closure)
            _need(saved['record_sha256']==info['closure_id'],'Parent closure identity changed during publication')
            try:
                settle_parent(root,budget_id=grant['budget_id'],reservation_id=reservation_id,closure_id=info['closure_id'])
            except CampaignProcessError as exc:info['settlement_error']=str(exc)
            else:info['state']='SETTLED'
        except Exception as closing_error:
            info['closure_error']=str(closing_error)
            failure=scope/'failure.json'
            if not failure.exists():
                try:records.write_record(failure,dict(kind='metal-parent-storage-failure',schema_version=1,
                    reservation_id=reservation_id,state=info['state'],consumer_error=error,closure_error=_error(closing_error),
                    scientific_acceptance='NOT_ASSESSED',retirement_authorized=False))
                except Exception:pass  # The existing held grant is the durable fail-closed state.
            if error is None:raise
