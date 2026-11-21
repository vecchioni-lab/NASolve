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
          and type(config.get('schema_version')) is int and config['schema_version'] == 1,
          'Storage budget identity or version changed')
    checksum(config.get('store_id'), 'storage instance identity')
    _integer(config.get('quota_bytes'), 'quota_bytes', 1)
    _integer(config.get('free_space_reserve_bytes'), 'free_space_reserve_bytes')
    ledger = _record(metadata/'ledger.json', MAX_LEDGER_BYTES)
    _need(ledger.get('kind') == 'metal-storage-reservations' and type(ledger.get('schema_version')) is int
          and ledger['schema_version'] == 1 and ledger.get('budget_id') == budget_id
          and isinstance(ledger.get('reservations'), dict)
          and len(ledger['reservations']) <= MAX_RESERVATIONS, 'Malformed storage reservation ledger')
    paths = []
    for reservation_id, item in ledger['reservations'].items():
        checksum(reservation_id, 'reservation identity')
        _need(isinstance(item, dict) and set(item) == {'grant', 'settlement'}, 'Malformed reservation entry')
        grant = item['grant']
        _need(isinstance(grant, dict) and digest(grant) == reservation_id
              and grant.get('budget_id') == budget_id, 'Reservation identity changed')
        _integer(grant.get('allowance_bytes'), 'allowance_bytes', 1)
        checksum(grant.get('request_id'), 'child request identity')
        child = _child_path(root, grant.get('child'))
        paths.append(child)
        settled = item['settlement']
        if settled is not None:
            _need(isinstance(settled, dict) and settled.get('reservation_id') == reservation_id
                  and settled.get('request_id') == grant['request_id'] and settled.get('status') in STOPPED
                  and settled.get('stopped_verified') is True
                  and settled.get('retirement_authorized') is False, 'Malformed recorded settlement')
            checksum(settled.get('outcome_sha256'), 'recorded stopped outcome identity')
    paths.sort(key=lambda path: path.parts)
    _need(not any(right == left or right.is_relative_to(left)
                  for left, right in zip(paths, paths[1:])), 'Reserved child paths overlap')
    return config, ledger


def _child_path(root, relative):
    _need(isinstance(relative, str), 'Require a store-relative child path')
    child = records.path_in(root, relative)
    _need(child.parts[len(root.parts)] not in {META, LOCK}, 'Child cannot occupy budget metadata')
    return child


def _pending(ledger):
    return sum(item['grant']['allowance_bytes'] for item in ledger['reservations'].values()
               if item['settlement'] is None)


def _space(root, required, reserve):
    _need(shutil.disk_usage(root).free >= required + reserve,
          'Insufficient free space for outstanding reservations and record publication')


def _save(root, ledger):
    _need(records.serialized_record_size(ledger) <= MAX_LEDGER_BYTES, 'Budget ledger byte limit exceeded')
    return records.write_record(root/META/'ledger.json', ledger, replace=True)


def create_budget(directory, *, quota_bytes, free_space_reserve_bytes=256*1024*1024):
    """Declare one immutable budget on an existing store; never adopt partial state."""
    root = _root(directory)
    _integer(quota_bytes, 'quota_bytes', 1)
    _integer(free_space_reserve_bytes, 'free_space_reserve_bytes')
    with exclusive_lock(records.path_in(root, LOCK)):
        metadata = records.path_in(root, META)
        _need(not metadata.exists(), 'Storage budget already exists or is incomplete')
        observed, _ = _observed(root)
        config = dict(kind='metal-storage-budget', schema_version=1, store_id=secrets.token_hex(32), quota_bytes=quota_bytes,
                      free_space_reserve_bytes=free_space_reserve_bytes)
        # The digest has fixed length; reserve exact config/initial-ledger sizes.
        ledger = dict(kind='metal-storage-reservations', schema_version=1,
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


def reserve_child(directory, *, budget_id, child, request_id, allowance_bytes):
    """Reserve before launch; no child directory or native process is created.

    The allowance must include all caller-owned growth, inputs, outputs and
    temporary overlap. The caller must separately arrange scratch on this device;
    existing parent/native helpers are not automatically wired into this API.
    """
    root = _root(directory)
    checksum(request_id, 'child request identity')
    _integer(allowance_bytes, 'allowance_bytes', 1)
    with exclusive_lock(records.path_in(root, LOCK)):
        config, ledger = _read(root, budget_id)
        path = _child_path(root, child)
        _need(path.parent.is_dir() and not path.exists(), 'Reserved child must be fresh with an existing parent')
        _need(len(ledger['reservations']) < MAX_RESERVATIONS, 'Budget reservation limit exceeded')
        for item in ledger['reservations'].values():
            other = _child_path(root, item['grant']['child'])
            _need(not (path == other or path.is_relative_to(other) or other.is_relative_to(path)),
                  'Child path already reserved or overlaps an existing reservation')
        observed, _ = _observed(root)
        grant = dict(budget_id=budget_id, child=child, request_id=request_id,
                     allowance_bytes=allowance_bytes, nonce=secrets.token_hex(16))
        reservation_id = digest(grant)
        ledger['reservations'][reservation_id] = dict(grant=grant, settlement=None)
        ledger_bytes = records.serialized_record_size(ledger)
        _need(ledger_bytes <= MAX_LEDGER_BYTES, 'Budget ledger byte limit exceeded')
        pending = _pending(ledger)
        # Existing includes the old ledger; include the entire new ledger while
        # its temporary publication coexists. Deliberately conservative.
        _need(observed + pending + ledger_bytes <= config['quota_bytes'], 'Storage budget cannot admit child')
        _space(root, pending + ledger_bytes, config['free_space_reserve_bytes'])
        _save(root, ledger)
        return dict(grant, reservation_id=reservation_id)


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
        grant = item['grant']; path = _child_path(root, grant['child'])
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
        return dict(kind='metal-storage-budget-inspection', schema_version=1, budget_id=budget_id,
                    ledger_sha256=ledger['record_sha256'], observed_bytes=observed, observed_entries=entries,
                    outstanding_bytes=pending, charged_bytes=observed+pending,
                    quota_bytes=config['quota_bytes'], within_declared_budget=observed+pending<=config['quota_bytes'],
                    free_bytes=free, free_space_reserve_bytes=config['free_space_reserve_bytes'],
                    pending_fits_free_space=pending+config['free_space_reserve_bytes']<=free,
                    held_count=held, settled_count=len(ledger['reservations'])-held,
                    stop_evidence='RECORDED_AT_SETTLEMENT', os_enforced=False,
                    scientific_acceptance='NOT_ASSESSED', retirement_authorized=False)


def _reserve_execution(options, *, attempt, request_id, max_parent_disk_bytes,
                       known_child_input_bytes, scratch_directory, retained_parent):
    """First caller: one-shot parent expansion and child growth on one device."""
    _need(isinstance(options, dict)
          and set(options) == {'directory', 'budget_id', 'allowance_bytes'},
          'Explicit storage budget requires directory, budget_id and allowance_bytes')
    _need(retained_parent is None, 'Budgeted retained parent lifetime needs separate outer accounting')
    root = _root(options['directory'])
    _need(attempt.is_relative_to(root), 'Budgeted child must be inside the declared store')
    scratch = Path(scratch_directory).expanduser().resolve()
    _need(scratch.is_dir() and scratch.stat().st_dev == root.stat().st_dev,
          'Budgeted child and parent temporary expansion must share one filesystem')
    _integer(max_parent_disk_bytes, 'parent disk allowance', 1)
    _integer(known_child_input_bytes, 'known child input bytes')
    allowance = _integer(options['allowance_bytes'], 'execution allowance', 1)
    _need(allowance > max_parent_disk_bytes + known_child_input_bytes + 16*1024,
          'Execution allowance needs parent space, known input copies and child headroom')
    grant = reserve_child(root, budget_id=options['budget_id'], child=attempt.relative_to(root).as_posix(),
                          request_id=request_id, allowance_bytes=allowance)
    return root, grant
