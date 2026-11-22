"""Explicit cooperative disk admission for owned frozen metal children.

Charges observed logical bytes plus every held allowance, conservatively counting
partial work twice. This is not an OS quota, a scheduler, or a retirement owner.
A create-only configuration and atomically replaced grant/settlement ledger share the
existing campaign lock/record owners. Interrupted or uncertain children hold space.
"""
from pathlib import Path
import os
import secrets
import shutil
import stat

from .. import campaign_records as records
from ..campaign_process import exclusive_lock
from .child_process import _root, _need, inspect_child
from .recipe import checksum, digest
from .storage import _integer

META = '.metal-budget'
LOCK = '.metal-budget.lock'
MAX_ENTRIES = 100_000
MAX_RESERVATIONS = 4096
MAX_LEDGER_BYTES = 16 * 1024 * 1024
MAX_RECORD_BYTES = 8192
STOPPED = {'COMPLETED', 'FAILED', 'TIMED_OUT', 'INTERRUPTED'}


def _record(path, limit):
    state = path.lstat()
    _need(stat.S_ISREG(state.st_mode) and state.st_size <= limit, 'Budget record is nonregular or oversized')
    return records.read_record(path)


def _observed(root):
    """Count all files, including protected/partial/ledger bytes; never follow links.

    Cooperating writers may grow files during this scan; outstanding allowances
    cover their declared future work. File blocks, unrelated writers and writes
    outside this root are not a measured or enforced bound.
    """
    device = root.stat().st_dev
    total = entries = 0
    stack = [root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as children:
            for entry in children:
                entries += 1
                _need(entries <= MAX_ENTRIES, 'Budget store entry limit exceeded')
                state = entry.stat(follow_symlinks=False)
                _need(state.st_dev == device, 'Budget store must use one filesystem')
                if stat.S_ISDIR(state.st_mode):
                    stack.append(Path(entry.path))
                else:
                    _need(stat.S_ISREG(state.st_mode), 'Budget store contains a link or nonregular file')
                    total += state.st_size
    return total, entries


def _read(root, budget_id):
    checksum(budget_id, 'independent storage budget identity')
    metadata = records.path_in(root, META)
    _need(metadata.is_dir() and {p.name for p in metadata.iterdir()} == {'config.json', 'ledger.json'},
          'Budget metadata is incomplete or contains interrupted/unrecognized files')
    config = _record(metadata/'config.json', MAX_RECORD_BYTES)
    _need(config.get('record_sha256') == budget_id and config.get('kind') == 'metal-storage-budget'
          and type(config.get('schema_version')) is int and config['schema_version'] in (1,2,3),
          'Storage budget identity or version changed')
    if config['schema_version']>=2:
        types=['child','retained_parent']+(['audited_session'] if config['schema_version']==3 else [])
        _need(config.get('reservation_types')==types, 'Unsupported mixed reservation profile')
    else:
        _need('reservation_types' not in config, 'Mixed scopes cannot use budget version 1')
    checksum(config.get('store_id'), 'storage instance identity')
    _integer(config.get('quota_bytes'), 'quota_bytes', 1)
    _integer(config.get('free_space_reserve_bytes'), 'free_space_reserve_bytes')
    ledger = _record(metadata/'ledger.json', MAX_LEDGER_BYTES)
    _need(ledger.get('kind') == 'metal-storage-reservations' and type(ledger.get('schema_version')) is int
          and ledger['schema_version'] == config['schema_version'] and ledger.get('budget_id') == budget_id
          and isinstance(ledger.get('reservations'), dict)
          and len(ledger['reservations']) <= MAX_RESERVATIONS, 'Malformed storage reservation ledger')
    paths = []; scope_ids = set()
    for reservation_id, item in ledger['reservations'].items():
        checksum(reservation_id, 'reservation identity')
        _need(isinstance(item, dict) and set(item) == {'grant', 'settlement'}, 'Malformed reservation entry')
        grant = item['grant']
        _need(isinstance(grant, dict) and digest(grant) == reservation_id
              and grant.get('budget_id') == budget_id, 'Reservation identity changed')
        _integer(grant.get('allowance_bytes'), 'allowance_bytes', 1)
        kind = _scope_type(ledger,grant)
        if ledger['schema_version']==1:
            _need(not {'scope_type','parent_reservation_id','scope'}.intersection(grant),
                  'Mixed scopes cannot use ledger version 1')
        else:
            common={'budget_id','allowance_bytes','nonce','scope_type'}
            fields=({'scope','scope_id','parent_manifest_sha256'} if kind=='retained_parent' else
                    {'session' if kind=='audited_session' else 'child','request_id','parent_reservation_id'})
            _need(set(grant)==common|fields, 'Malformed mixed-scope grant')
            _need(isinstance(grant['nonce'],str) and len(grant['nonce'])==32
                  and all(c in '0123456789abcdef' for c in grant['nonce']), 'Malformed grant nonce')
        if kind!='retained_parent':
            checksum(grant.get('request_id'), 'child request identity')
        else:
            checksum(grant.get('parent_manifest_sha256'), 'parent manifest identity')
            checksum(grant.get('scope_id'), 'reserved parent scope identity')
            _need(grant['scope_id'] not in scope_ids, 'Parent scope identity reused')
            scope_ids.add(grant['scope_id'])
            if item['settlement'] is not None:
                from .parent_budget import _check_settlement
                _check_settlement(root,grant,reservation_id,item['settlement'])
        paths.append(_grant_path(root,grant))
        settled = item['settlement']
        if settled is not None and kind=='audited_session':_check_session_settlement(grant,reservation_id,settled)
        if settled is not None and kind=='child':
            _need(isinstance(settled, dict) and settled.get('reservation_id') == reservation_id
                  and settled.get('request_id') == grant['request_id'] and settled.get('status') in STOPPED
                  and settled.get('stopped_verified') is True
                  and settled.get('retirement_authorized') is False, 'Malformed recorded settlement')
            checksum(settled.get('outcome_sha256'), 'recorded stopped outcome identity')
    if ledger['schema_version']>=2:
        for item in ledger['reservations'].values():
            grant=item['grant']
            if grant['scope_type']!='retained_parent':
                if grant['scope_type']=='audited_session':checksum(grant['parent_reservation_id'],'session parent reservation')
                _parent_reference(ledger,grant['parent_reservation_id'])
    paths.sort(key=lambda path: path.parts)
    _need(not any(right == left or right.is_relative_to(left)
                  for left, right in zip(paths, paths[1:])), 'Reserved child paths overlap')
    return config, ledger


def _child_path(root, relative):
    _need(isinstance(relative, str), 'Require a store-relative child path')
    child = records.path_in(root, relative)
    _need(child.parts[len(root.parts)] not in {META, LOCK}, 'Child cannot occupy budget metadata')
    return child


def _scope_type(ledger, grant):
    kind = 'child' if ledger['schema_version']==1 else grant.get('scope_type')
    allowed={'child','retained_parent'} | ({'audited_session'} if ledger['schema_version']==3 else set())
    _need(isinstance(kind,str) and kind in allowed, 'Unsupported reservation scope')
    return kind


def _grant_path(root, grant):
    field={'retained_parent':'scope','audited_session':'session'}.get(grant.get('scope_type'),'child')
    return _child_path(root,grant.get(field))


def _parent_reference(ledger, reference, *, require_held=False):
    if reference is None:return
    checksum(reference, 'parent reservation identity')
    item=ledger['reservations'].get(reference)
    _need(item is not None and item['grant'].get('scope_type')=='retained_parent'
          and (not require_held or item['settlement'] is None), 'Missing, closed or wrong parent reservation reference')


def _pending(ledger):
    return sum(item['grant']['allowance_bytes'] for item in ledger['reservations'].values()
               if item['settlement'] is None)


def _space(root, required, reserve):
    _need(shutil.disk_usage(root).free >= required + reserve,
          'Insufficient free space for outstanding reservations and record publication')


def _save(root, ledger):
    _need(records.serialized_record_size(ledger) <= MAX_LEDGER_BYTES, 'Budget ledger byte limit exceeded')
    return records.write_record(root/META/'ledger.json', ledger, replace=True)


def create_budget(directory, *, quota_bytes, free_space_reserve_bytes=256*1024*1024,
                  include_retained_parents=False,include_audited_sessions=False):
    """Declare one immutable budget on an existing store; never adopt partial state."""
    root = _root(directory)
    _need(type(include_retained_parents) is bool, 'Explicit retained-parent profile must be boolean')
    _need(type(include_audited_sessions) is bool and (not include_audited_sessions or include_retained_parents),
          'Audited sessions require explicit retained-parent support')
    version=3 if include_audited_sessions else 2 if include_retained_parents else 1
    _integer(quota_bytes, 'quota_bytes', 1)
    _integer(free_space_reserve_bytes, 'free_space_reserve_bytes')
    with exclusive_lock(records.path_in(root, LOCK)):
        metadata = records.path_in(root, META)
        _need(not metadata.exists(), 'Storage budget already exists or is incomplete')
        observed, _ = _observed(root)
        config = dict(kind='metal-storage-budget', schema_version=version, store_id=secrets.token_hex(32), quota_bytes=quota_bytes,
                      free_space_reserve_bytes=free_space_reserve_bytes)
        if include_retained_parents:config['reservation_types']=['child','retained_parent']+(['audited_session'] if include_audited_sessions else [])
        # The digest has fixed length; reserve exact config/initial-ledger sizes.
        ledger = dict(kind='metal-storage-reservations', schema_version=version,
                      budget_id='0'*64, reservations={})
        required = records.serialized_record_size(config) + records.serialized_record_size(ledger)
        _need(observed + required <= quota_bytes, 'Existing store exceeds storage budget')
        _space(root, required, free_space_reserve_bytes)
        metadata.mkdir()
        records._sync_directory(root)
        result = records.write_record(metadata/'config.json', config)
        ledger['budget_id'] = result['record_sha256']
        records.write_record(metadata/'ledger.json', ledger)
        return result


def _admit(root, config, ledger, grant):
    """One locked publication path for all supported grants."""
    path = _grant_path(root,grant)
    _need(path.parent.is_dir() and not path.exists(), 'Reserved path must be fresh with an existing parent')
    _need(len(ledger['reservations']) < MAX_RESERVATIONS, 'Budget reservation limit exceeded')
    for item in ledger['reservations'].values():
        other = _grant_path(root,item['grant'])
        _need(not (path == other or path.is_relative_to(other) or other.is_relative_to(path)),
              'Path already reserved or overlaps an existing reservation')
    observed, _ = _observed(root)
    reservation_id = digest(grant)
    ledger['reservations'][reservation_id] = dict(grant=grant, settlement=None)
    ledger_bytes = records.serialized_record_size(ledger)
    _need(ledger_bytes <= MAX_LEDGER_BYTES, 'Budget ledger byte limit exceeded')
    pending = _pending(ledger)
    # Charge the complete replacement while the old ledger still exists.
    _need(observed + pending + ledger_bytes <= config['quota_bytes'], 'Storage budget cannot admit reservation')
    _space(root, pending + ledger_bytes, config['free_space_reserve_bytes'])
    _save(root, ledger)
    return dict(grant, reservation_id=reservation_id)


def reserve_child(directory, *, budget_id, child, request_id, allowance_bytes,
                  parent_reservation_id=None):
    """Reserve child growth; a v2 parent reference records accounting lineage only.

    No directory or process is created, and a parent reference is not a live
    retained handle or scientific parent admission. V1 remains child-only.
    """
    root = _root(directory)
    checksum(request_id, 'child request identity')
    _integer(allowance_bytes, 'allowance_bytes', 1)
    with exclusive_lock(records.path_in(root, LOCK)):
        config, ledger = _read(root, budget_id)
        grant = dict(budget_id=budget_id, child=child, request_id=request_id,
                     allowance_bytes=allowance_bytes, nonce=secrets.token_hex(16))
        if ledger['schema_version']==1:
            _need(parent_reservation_id is None, 'Parent references require ledger version 2')
        else:
            _parent_reference(ledger,parent_reservation_id,require_held=True)
            grant.update(scope_type='child',parent_reservation_id=parent_reservation_id)
        return _admit(root,config,ledger,grant)


def reserve_retained_parent(directory, *, budget_id, scope, parent_manifest_sha256, allowance_bytes):
    """Reserve a v2 parent scope without expanding or creating a live handle.

    The grant stays held: authoritative parent closure/settlement is separate.
    """
    root = _root(directory)
    checksum(parent_manifest_sha256, 'parent manifest identity')
    _integer(allowance_bytes, 'allowance_bytes', 1)
    with exclusive_lock(records.path_in(root, LOCK)):
        config, ledger = _read(root,budget_id)
        _need(ledger['schema_version'] in (2,3), 'Retained parent grants require ledger version 2 or 3')
        grant=dict(budget_id=budget_id,scope_type='retained_parent',scope=scope,
                   scope_id=secrets.token_hex(32),parent_manifest_sha256=parent_manifest_sha256,
                   allowance_bytes=allowance_bytes,nonce=secrets.token_hex(16))
        return _admit(root,config,ledger,grant)


def _stopped(path, request_id):
    report = inspect_child(path, request_id=request_id)
    outcome = report.get('outcome')
    _need(report.get('request_id') == request_id and report.get('status') in STOPPED
          and report.get('stopped_verified') is True and isinstance(outcome, dict)
          and outcome.get('stopped_verified') is True and outcome.get('request_id') == request_id,
          'Reservation release requires a verified stopped outcome')
    return report['status'], outcome['record_sha256']


def settle_child(directory, *, budget_id, reservation_id):
    """Release only future allowance after shared process-owner verification.

    Completed/failed/timed-out/interrupted *known stopped* outcomes may settle.
    Missing outcomes and uncertain ownership keep their reservation indefinitely.
    Retained files remain charged. No age/PID expiry, cancellation or deletion.
    """
    root = _root(directory)
    checksum(reservation_id, 'reservation identity')
    with exclusive_lock(records.path_in(root, LOCK)):
        config, ledger = _read(root, budget_id)
        item = ledger['reservations'].get(reservation_id)
        _need(item is not None and item['settlement'] is None, 'Reservation absent or already settled')
        grant = item['grant']
        _need(_scope_type(ledger,grant)=='child', 'Only child reservations settle as a child; parent/session need their own evidence')
        path = _child_path(root, grant['child'])
        status, outcome_id = _stopped(path, grant['request_id'])
        _observed(root)
        value = dict(reservation_id=reservation_id, request_id=grant['request_id'], status=status,
                     outcome_sha256=outcome_id, stopped_verified=True, retirement_authorized=False)
        item['settlement'] = value
        _space(root, records.serialized_record_size(ledger), config['free_space_reserve_bytes'])
        _need(_stopped(path, grant['request_id']) == (status, outcome_id), 'Stopped outcome changed during settlement')
        _save(root, ledger)
        return value


def inspect_budget(directory, *, budget_id):
    """Observe current bytes and recorded reservations; do not launch or release."""
    root = _root(directory)
    with exclusive_lock(records.path_in(root, LOCK)):
        config, ledger = _read(root, budget_id)
        observed, entries = _observed(root)
        pending = _pending(ledger)
        held = sum(item['settlement'] is None for item in ledger['reservations'].values())
        free = shutil.disk_usage(root).free
        result = dict(kind='metal-storage-budget-inspection', schema_version=ledger['schema_version'], budget_id=budget_id,
                    ledger_sha256=ledger['record_sha256'], observed_bytes=observed, observed_entries=entries,
                    outstanding_bytes=pending, charged_bytes=observed+pending,
                    quota_bytes=config['quota_bytes'], within_declared_budget=observed+pending<=config['quota_bytes'],
                    free_bytes=free, free_space_reserve_bytes=config['free_space_reserve_bytes'],
                    pending_fits_free_space=pending+config['free_space_reserve_bytes']<=free,
                    held_count=held, settled_count=len(ledger['reservations'])-held,
                    stop_evidence='RECORDED_AT_SETTLEMENT', os_enforced=False,
                    scientific_acceptance='NOT_ASSESSED', retirement_authorized=False)
        if ledger['schema_version']>=2:
            kinds=('child','retained_parent')+(('audited_session',) if ledger['schema_version']==3 else ())
            held_items=[item['grant'] for item in ledger['reservations'].values() if item['settlement'] is None]
            result['held_by_scope']={kind:sum(grant['scope_type']==kind for grant in held_items) for kind in kinds}
            result['outstanding_by_scope']={kind:sum(grant['allowance_bytes'] for grant in held_items if grant['scope_type']==kind) for kind in kinds}
        return result


def _reserve_execution(options, *, attempt, request_id, max_parent_disk_bytes,
                       known_child_input_bytes, scratch_directory, retained_parent):
    """Admit one-shot growth or a child borrowing a separately charged live parent."""
    _need(isinstance(options, dict)
          and set(options) == {'directory', 'budget_id', 'allowance_bytes'},
          'Explicit storage budget requires directory, budget_id and allowance_bytes')
    root = _root(options['directory'])
    _need(attempt.is_relative_to(root), 'Budgeted child must be inside the declared store')
    scratch = Path(scratch_directory).expanduser().resolve()
    _need(scratch.is_dir() and scratch.stat().st_dev == root.stat().st_dev,
          'Budgeted child and parent temporary expansion must share one filesystem')
    _integer(max_parent_disk_bytes, 'parent disk allowance', 1)
    _integer(known_child_input_bytes, 'known child input bytes')
    allowance = _integer(options['allowance_bytes'], 'execution allowance', 1)
    parent_id=None
    with exclusive_lock(records.path_in(root,LOCK)):
        config,ledger = _read(root,options['budget_id'])
        if retained_parent is None:
            _need(config['schema_version']==1, 'A mixed-scope launch requires a live budgeted retained parent')
            _need(allowance > max_parent_disk_bytes + known_child_input_bytes + 16*1024,
                  'Execution allowance needs parent space, known input copies and child headroom')
        else:
            _need(config['schema_version'] in (2,3), 'A budgeted retained parent requires the mixed profile')
            from .parent_budget import _active_reservation
            parent_id=_active_reservation(root,ledger,retained_parent)
            _need(allowance > known_child_input_bytes + 16*1024,
                  'Execution allowance needs known input copies and child headroom')
    grant = reserve_child(root, budget_id=options['budget_id'], child=attempt.relative_to(root).as_posix(),
                          request_id=request_id, allowance_bytes=allowance,parent_reservation_id=parent_id)
    return root, grant


SESSION_SETTLEMENT='metal-audited-session-storage-settlement'
SESSION_ADMISSION='metal-audited-session-storage-admission'


def _reserve_audited_execution(options,*,session,request_id,known_input_bytes,max_output_bytes,retained_parent):
    """Reserve the entire ordinary session before its first native inspection."""
    from . import preflight_process
    from .parent_budget import _active_reservation
    _need(isinstance(options,dict) and set(options)=={'directory','budget_id','allowance_bytes'},
          'Explicit session budget requires directory, budget_id and allowance_bytes')
    root=_root(options['directory'])
    _need(session.is_relative_to(root),'Budgeted session must be inside its declared store')
    checksum(request_id,'audited session request identity')
    _integer(options['allowance_bytes'],'session allowance',1)
    # Three prepared-input copies (inspection plus the child's two copies),
    # declared native output and bounded inspection captures/proofs. This is
    # conservative cooperative headroom, not an OS-enforced write limit.
    minimum=3*known_input_bytes+max_output_bytes+4*preflight_process.MAX_CAPTURE_BYTES+8*preflight_process.MAX_RECORD_BYTES
    _need(options['allowance_bytes']>minimum,'Session allowance needs copied inputs, declared output and preflight headroom')
    with exclusive_lock(records.path_in(root,LOCK)):
        config,ledger=_read(root,options['budget_id'])
        _need(config['schema_version']==3,'Audited session admission requires explicit ledger version 3')
        parent_id=_active_reservation(root,ledger,retained_parent)
        grant=dict(budget_id=options['budget_id'],scope_type='audited_session',session=session.relative_to(root).as_posix(),
            request_id=request_id,parent_reservation_id=parent_id,allowance_bytes=options['allowance_bytes'],nonce=secrets.token_hex(16))
        return root,_admit(root,config,ledger,grant),minimum


def _check_session_settlement(grant,reservation_id,value):
    if isinstance(value,dict) and value.get('kind') in {FAILED_SESSION_SETTLEMENT,FAILED_PREFLIGHT_SETTLEMENT}:
        return _check_failed_session_settlement(grant,reservation_id,value)
    fields={'kind','schema_version','reservation_id','request_id','parent_reservation_id','review_sha256',
            'output_evidence_id','preflight_stopped_verified','native_stopped_verified','postflight_review_complete',
            'verification_scope','scientific_acceptance','retirement_authorized'}
    _need(isinstance(value,dict) and set(value)==fields and value['kind']==SESSION_SETTLEMENT
          and type(value['schema_version']) is int and value['schema_version']==1
          and value['reservation_id']==reservation_id and value['request_id']==grant['request_id']
          and value['parent_reservation_id']==grant['parent_reservation_id']
          and all(value[k] is True for k in ('preflight_stopped_verified','native_stopped_verified','postflight_review_complete'))
          and value['verification_scope']=='COMPLETED_REVIEW_CHECKED_AT_SETTLEMENT'
          and value['scientific_acceptance']=='NOT_ASSESSED' and value['retirement_authorized'] is False,
          'Malformed audited-session settlement')
    checksum(value['review_sha256'],'settled scientific review identity')
    checksum(value['output_evidence_id'],'settled native output evidence identity')


def _session_admission(path,grant,reservation_id):
    admission=_record(path/'storage-admission.json',MAX_RECORD_BYTES)
    _need(set(admission)=={'kind','schema_version','reservation_id','grant','minimum_allowance_bytes','scientific_acceptance','retirement_authorized','record_sha256'}
          and admission.get('kind')==SESSION_ADMISSION and type(admission.get('schema_version')) is int
          and admission['schema_version']==1 and admission.get('grant')==grant
          and admission.get('reservation_id')==reservation_id and admission.get('retirement_authorized') is False
          and admission.get('scientific_acceptance')=='NOT_ASSESSED'
          and type(admission.get('minimum_allowance_bytes')) is int
          and 0<admission['minimum_allowance_bytes']<grant['allowance_bytes'],
          'Session storage admission changed')


def _audited_review(root,ledger,grant,reservation_id,review_id):
    from . import child_session
    path=_grant_path(root,grant);_session_admission(path,grant,reservation_id)
    report=child_session.inspect_audited_child(path,review_id=review_id)
    declaration=child_session._session_record(path,'request.json')
    _need(declaration.get('storage_reservation')==dict(budget_id=grant['budget_id'],reservation_id=reservation_id),
          'Scientific session reservation binding changed')
    parent=ledger['reservations'][grant['parent_reservation_id']]['grant']
    scope=report.get('recorded_parent_scope')
    _need(report['schema_version']==3 and report['request_id']==grant['request_id']
          and report.get('preflight_stopped_verified') is True and isinstance(scope,dict)
          and scope.get('scope_id')==parent['scope_id'] and scope.get('parent_manifest_sha256')==parent['parent_manifest_sha256'],
          'Complete owned session and exact retained parent are required for release')
    return report


def settle_audited_session(directory,*,budget_id,reservation_id,review_id):
    """Release future session allowance only after a complete owned scientific review.

    Failed, unknown or unrecorded sessions remain held. Native payloads are never
    removed. The compact ledger records this check; routine budget inspection is
    not a fresh scientific readback of all old arrays. Exact retries are idempotent.
    """
    root=_root(directory);checksum(reservation_id,'session reservation identity');checksum(review_id,'independent scientific review identity')
    with exclusive_lock(records.path_in(root,LOCK)):
        config,ledger=_read(root,budget_id);item=ledger['reservations'].get(reservation_id)
        _need(item is not None and item['grant'].get('scope_type')=='audited_session','Require an exact audited-session reservation')
        grant=item['grant']
        if item['settlement'] is not None:
            _need(item['settlement'].get('review_sha256')==review_id,'Session already settled against a different review')
            return item['settlement']
        report=_audited_review(root,ledger,grant,reservation_id,review_id)
        value=dict(kind=SESSION_SETTLEMENT,schema_version=1,reservation_id=reservation_id,request_id=grant['request_id'],
            parent_reservation_id=grant['parent_reservation_id'],review_sha256=review_id,output_evidence_id=report['output_evidence_id'],
            preflight_stopped_verified=True,native_stopped_verified=True,postflight_review_complete=True,
            verification_scope='COMPLETED_REVIEW_CHECKED_AT_SETTLEMENT',scientific_acceptance='NOT_ASSESSED',retirement_authorized=False)
        _observed(root);item['settlement']=value
        _space(root,records.serialized_record_size(ledger),config['free_space_reserve_bytes'])
        _need(_audited_review(root,ledger,grant,reservation_id,review_id)==report,'Audited session changed during settlement')
        _check_session_settlement(grant,reservation_id,value);_save(root,ledger)
        return value


FAILED_SESSION_SETTLEMENT='metal-failed-session-storage-settlement'
FAILED_PREFLIGHT_SETTLEMENT='metal-failed-preflight-session-storage-settlement'


def _check_failed_session_settlement(grant,reservation_id,value):
    if value.get('kind')==FAILED_PREFLIGHT_SETTLEMENT:
        fields={'kind','schema_version','reservation_id','request_id','parent_reservation_id','failure_sha256',
                'preflight_ownership_sha256','preflight_finished_sha256','preflight_stopped_verified',
                'native_not_started_verified','postflight_review_complete','verification_scope',
                'scientific_acceptance','retirement_authorized'}
        _need(set(value)==fields and type(value['schema_version']) is int and value['schema_version']==1
            and value['reservation_id']==reservation_id and value['request_id']==grant['request_id']
            and value['parent_reservation_id']==grant['parent_reservation_id']
            and value['preflight_stopped_verified'] is True and value['native_not_started_verified'] is True
            and value['postflight_review_complete'] is False
            and value['verification_scope']=='FAILED_PREFLIGHT_STOP_CHECKED_AT_SETTLEMENT'
            and value['scientific_acceptance']=='NOT_ASSESSED' and value['retirement_authorized'] is False,
            'Malformed failed-preflight settlement')
        for key in ('failure_sha256','preflight_ownership_sha256','preflight_finished_sha256'):checksum(value[key],key)
        return
    fields={'kind','schema_version','reservation_id','request_id','parent_reservation_id','failure_sha256',
            'preflight_inspection_id','native_outcome_sha256','native_status','preflight_stopped_verified',
            'native_stopped_verified','postflight_review_complete','verification_scope','scientific_acceptance','retirement_authorized'}
    _need(set(value)==fields and value['kind']==FAILED_SESSION_SETTLEMENT
        and type(value['schema_version']) is int and value['schema_version']==1
        and value['reservation_id']==reservation_id and value['request_id']==grant['request_id']
        and value['parent_reservation_id']==grant['parent_reservation_id'] and value['native_status'] in STOPPED
        and value['preflight_stopped_verified'] is True and value['native_stopped_verified'] is True
        and value['postflight_review_complete'] is False and value['verification_scope']=='FAILED_SESSION_STOP_CHECKED_AT_SETTLEMENT'
        and value['scientific_acceptance']=='NOT_ASSESSED' and value['retirement_authorized'] is False,
        'Malformed failed-session settlement')
    for key in ('failure_sha256','preflight_inspection_id','native_outcome_sha256'):checksum(value[key],key)


def _failed_session_review(root,ledger,grant,reservation_id,failure_id):
    from . import child_session
    path=_grant_path(root,grant)
    _session_admission(path,grant,reservation_id)
    report=child_session.inspect_failed_audited_child(path,failure_id=failure_id)
    _need(report['storage_reservation']==dict(budget_id=grant['budget_id'],reservation_id=reservation_id),
          'Failed session reservation binding changed')
    parent=ledger['reservations'][grant['parent_reservation_id']]['grant'];scope=report['recorded_parent_scope']
    _need(report['request_id']==grant['request_id'] and scope['scope_id']==parent['scope_id']
          and scope['parent_manifest_sha256']==parent['parent_manifest_sha256'],'Failed session retained parent changed')
    return report


def settle_failed_audited_session(directory,*,budget_id,reservation_id,failure_id):
    """Release a new, exactly bound, known-stopped failed session's allowance.

    This is accounting only: failed science stays failed and files remain.
    Uncertain/unsealed and historical unbound failures stay held. A newly
    sealed preflight failure proves that no main child attempt was created.
    """
    root=_root(directory);checksum(reservation_id,'session reservation identity');checksum(failure_id,'independent session failure')
    with exclusive_lock(records.path_in(root,LOCK)):
        config,ledger=_read(root,budget_id);item=ledger['reservations'].get(reservation_id)
        _need(item is not None and item['grant'].get('scope_type')=='audited_session','Require an exact audited-session reservation')
        grant=item['grant']
        if item['settlement'] is not None:
            _need(item['settlement'].get('failure_sha256')==failure_id,'Session already settled against different evidence')
            return item['settlement']
        report=_failed_session_review(root,ledger,grant,reservation_id,failure_id)
        partial=report['stage']=='FRESH_INPUT_INSPECTION'
        proof_fields=(('preflight_ownership_sha256','preflight_finished_sha256','preflight_stopped_verified',
                       'native_not_started_verified','postflight_review_complete') if partial else
                      ('preflight_inspection_id','native_outcome_sha256','native_status',
                       'preflight_stopped_verified','native_stopped_verified','postflight_review_complete'))
        value=dict(kind=FAILED_PREFLIGHT_SETTLEMENT if partial else FAILED_SESSION_SETTLEMENT,
            schema_version=1,reservation_id=reservation_id,
            request_id=grant['request_id'],parent_reservation_id=grant['parent_reservation_id'],failure_sha256=failure_id,
            **{k:report[k] for k in proof_fields},
            verification_scope='FAILED_PREFLIGHT_STOP_CHECKED_AT_SETTLEMENT' if partial else 'FAILED_SESSION_STOP_CHECKED_AT_SETTLEMENT',
            scientific_acceptance='NOT_ASSESSED',retirement_authorized=False)
        _observed(root);item['settlement']=value
        _space(root,records.serialized_record_size(ledger),config['free_space_reserve_bytes'])
        _need(_failed_session_review(root,ledger,grant,reservation_id,failure_id)==report,'Failed session changed during settlement')
        _check_failed_session_settlement(grant,reservation_id,value);_save(root,ledger)
        return value
