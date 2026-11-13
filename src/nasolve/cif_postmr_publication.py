"""Publish one checked preparation for ordinary review/refinement callers.

The existing complete request owns science and execution. This module only binds
its exact result to the ordinary report/checkpoint inputs under that request's
lock. REVIEW means a preparation available for a trial, not a refined structure.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
import os
import re
from pathlib import Path
import tempfile

from .campaign_records import now, read_record, write_record, _sync_directory
from .campaign_process import exclusive_lock
from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _bytes
from .cif_model_context import _intent, prepared_model_topology
from .cif_ordinary_postmr import _ordinary_request_directory, _read_ordinary_postmr_result

POLICY_ID = 'checked-postmr-publication-v1'
CHECKPOINT_SCHEMA = 3


def _intent_digest(report):
    return sha256(_bytes({k: report.get(k) for k in ('workflow', 'frame', 'inputs', 'post_mr_plan')})).hexdigest()


def _reference(path, run):
    from .checkpoints import _file_reference
    ref = _file_reference(path, run)
    _need(ref['anchor'] != 'absolute', 'Published preparation input needs a declared run/dataset anchor')
    return ref


def _payload(run, report, checked, exact, *, created, previous_report_sha256):
    from .checkpoints import _required_file
    from .postmr import scan_anomalous_candidates, DEFAULT_ANOMALOUS_ELEMENTS
    from .anomalous_expectations import audit_iodine_targets
    from .phosphate import requested_op3_sites
    from .ligand_profiles import is_modification_only
    _need(checked.model_path is not None, 'Preparation has no independently checked model/restraint combination')
    request = read_record(checked.request_directory/'request.json')
    _need(_intent(report) == request['configuration']['model_context']['intent'],
          'Run chemical intent differs from the checked preparation')
    inputs = report.get('inputs')
    _need(isinstance(inputs, dict), 'Require frozen observation inputs')
    observations = _required_file(inputs.get('reflections'), 'authoritative reflections', run)
    observation_ref = _reference(observations, run)
    expected_observations = inputs.get('reflections_sha256')
    _need(isinstance(expected_observations, str) and expected_observations.casefold() == observation_ref['sha256'],
          'Authoritative observations must match their original frozen checksum')
    model_ref = _reference(checked.model_path, run)
    _need(model_ref['anchor'] == 'run', 'Checked model must remain in its run')
    candidates = scan_anomalous_candidates(checked.model_path)
    return dict(
        status='POSTMR_READY',
        message=checked.message+' Saved as a review checkpoint for trial refinement; refinement has not been performed.',
        created_utc=created, prepared_model=model_ref['relative_path'], prepared_sha256=model_ref['sha256'],
        refinement_restraints=[_reference(p, run) for p in (*checked.restraint_paths, *checked.dictionary_paths)],
        view_dictionaries=[_reference(p, run) for p in checked.dictionary_paths if not is_modification_only(p)],
        mutation_actions=deepcopy(exact['construction_inputs']['report']['controls']['actions']),
        checked_model_topology=prepared_model_topology(request['configuration']['model_context']),
        phosphate_policy=dict(mode='op3-explicit-opt-in-v1', allow_op3_sites=list(requested_op3_sites(report))),
        anomalous=dict(trigger_elements=sorted(DEFAULT_ANOMALOUS_ELEMENTS), candidates=candidates,
                       autosol_required=bool(candidates), iodine_expectations=audit_iodine_targets(checked.model_path, candidates)),
        readyset=dict(status=checked.readyset_status),
        checked_preparation=dict(policy_id=POLICY_ID, attempt_number=checked.attempt_number,
            request=_reference(checked.request_directory/'request.json', run), result=_reference(checked.report_path, run),
            selected=checked.selected, input_intent_sha256=_intent_digest(report), observations=observation_ref,
            previous_run_report_sha256=previous_report_sha256, refinement='NOT_RUN', adoption='EXPLICIT_REVIEW_CHECKPOINT'),
    )


def _checked_record(run, report, record):
    meta = record.get('checked_preparation')
    _need(isinstance(meta, dict) and meta.get('policy_id') == POLICY_ID, 'Missing checked preparation binding')
    _need(isinstance(meta.get('previous_run_report_sha256'), str) and re.fullmatch('[0-9a-f]{64}', meta['previous_run_report_sha256']), 'Malformed original run-report checksum')
    _need(isinstance(record.get('created_utc'), str) and datetime.fromisoformat(record['created_utc']).tzinfo is not None, 'Malformed publication date')
    _need(meta.get('input_intent_sha256') == _intent_digest(report), 'Frozen run intent changed after publication')
    checked, exact = _read_ordinary_postmr_result(run, attempt_number=meta.get('attempt_number'))
    expected = _payload(run, report, checked, exact, created=record.get('created_utc'),
                        previous_report_sha256=meta.get('previous_run_report_sha256'))
    _need({k:v for k,v in record.items() if k != 'record_sha256'} == expected,
          'Published model/restraints or preparation evidence differ from the exact checked result')
    return checked


def _registry(run, report):
    from .checkpoints import _root_payload
    created = report['postmr']['created_utc']
    return dict(schema_version=CHECKPOINT_SCHEMA, run_directory='.', created_utc=created, updated_utc=created,
                current='postmr', bookmarks={}, checkpoints=[_root_payload(report, run)])


def _check_root(run, report, registry):
    from .checkpoints import _root_payload
    _need(registry.get('schema_version') == CHECKPOINT_SCHEMA, 'Checked preparation requires checkpoint schema 3')
    items = registry.get('checkpoints')
    _need(isinstance(items, list) and all(isinstance(i, dict) for i in items), 'Malformed checked checkpoint registry')
    roots = [item for item in items if item.get('id') == 'postmr']
    _need(len(roots) == 1, 'Require one checked PostMR root')
    # Later AutoSol evidence is validated by its own consumer, not required to
    # re-establish the original preparation (which predates AutoSol).
    expected = _root_payload({k:v for k,v in report.items() if k != 'autosol'}, run)
    _need(roots[0] == expected, 'Checked root differs from published preparation')


def validate_published_preparation(run, report, registry=None):
    """Validate the exact producer/compiler/result join once per ordinary read.

    Legacy runs have no publication binding and keep their previous read path.
    Later checkpoints may have new coordinates; their starting proof stays bound
    to the immutable root, not falsely compared to a refined child model.
    """
    postmr = report.get('postmr')
    active = isinstance(postmr, dict) and 'checked_preparation' in postmr
    active = active or (isinstance(registry, dict) and registry.get('schema_version') == CHECKPOINT_SCHEMA)
    path = run/'PostMR/report.json'
    if not active and path.is_file():
        try:
            saved = json.loads(path.read_text())
            active = isinstance(saved, dict) and 'checked_preparation' in saved
        except (OSError, ValueError):
            return  # An unrelated legacy side report is not a new authority.
    if not active:
        return
    _read(path)  # Reject symbolic-link traversal before reading the sealed record.
    record = read_record(path)
    _need(postmr == record, 'Run report does not match its published checked preparation')
    _checked_record(run, report, record)
    from .checkpoints import registry_path
    _read(registry_path(run))
    saved_registry = read_record(registry_path(run))
    _need(registry is None or registry == saved_registry, 'Checkpoint registry changed during read')
    _check_root(run, report, saved_registry)


def validate_preparation_lineage(registry, selected):
    """Retain inherited restraints along the selected branch; allow new models."""
    if registry.get('schema_version') != CHECKPOINT_SCHEMA:
        return
    items = registry.get('checkpoints', [])
    indexed = {i['id']:i for i in items if isinstance(i, dict) and isinstance(i.get('id'), str)}
    _need(len(indexed) == len(items) and 'postmr' in indexed, 'Malformed checked checkpoint lineage')
    node = selected; seen = set()
    while node.get('id') != 'postmr':
        identifier = node.get('id')
        _need(identifier not in seen, 'Cycle in checked checkpoint lineage'); seen.add(identifier)
        _need(isinstance(node.get('parent'), str), 'Missing checked checkpoint parent')
        parent = indexed.get(node['parent'])
        _need(parent is not None, 'Missing checked checkpoint parent')
        inherited = parent.get('restraints'); current = node.get('restraints')
        _need(isinstance(inherited, list) and isinstance(current, list)
              and current[:len(inherited)] == inherited,
              'Checkpoint lost or reordered inherited preparation restraints')
        node = parent


def _publish_run_report(path, previous_sha256, report):
    """Commit the run pointer last; retain any interrupted temporary output."""
    _need(sha256(_read(path)).hexdigest() == previous_sha256, 'Run report changed during publication; preserve existing work')
    descriptor, temporary = tempfile.mkstemp(prefix='.checked-preparation-', suffix='.json', dir=path.parent)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    _need(sha256(_read(path)).hexdigest() == previous_sha256, 'Run report changed during publication; temporary output retained')
    os.replace(temporary, path); _sync_directory(path.parent)


def publish_checked_preparation(run_directory, *, attempt_number):
    """Publish/recover one initial review checkpoint; retain the receipt-only API."""
    return _publish_checked_preparation(run_directory, attempt_number=attempt_number)[0]


def publish_checked_preparation_with_notes(run_directory, *, attempt_number) -> tuple[dict, tuple[str, ...]]:
    """Return the sealed receipt and current notes from the same verified result.

    Notes are descriptive, not selection authority, and are never inserted into
    the historical preparation receipt. Repeating publication revalidates once;
    callers must not replay the full proof again merely to format these notes.
    """
    record, checked = _publish_checked_preparation(run_directory, attempt_number=attempt_number)
    return record, checked.limitations


def _publish_checked_preparation(run_directory, *, attempt_number):
    """Publish one initial review checkpoint, or finish the same interrupted save.

    A different preparation never overwrites an earlier choice. No construction,
    native execution, checkpoint reselection or in-place scientific retry occurs.
    """
    _need(type(attempt_number) is int and attempt_number >= 1, 'Require an exact positive preparation attempt')
    run = Path(run_directory).expanduser().resolve()
    request = _ordinary_request_directory(run)
    _need(request.is_dir(), 'No saved ordinary preparation request')
    from .checkpoints import _root_payload, registry_path
    with exclusive_lock(request/'request.lock'):
        root_path = run/'report.json'; previous = _read(root_path); report = json.loads(previous)
        _need(isinstance(report, dict) and report.get('workflow') == 'automr', 'Require an AutoMR run report')
        receipt = run/'PostMR/report.json'; checkpoint_path = registry_path(run)
        if receipt.exists() or receipt.is_symlink():
            _read(receipt); record = read_record(receipt)
            meta = record.get('checked_preparation')
            _need(isinstance(meta, dict) and meta.get('attempt_number') == attempt_number,
                  'A different preparation is already published or reserved; preserve its choice')
            checked = _checked_record(run, report, record)
            if report.get('postmr') == record:
                _read(checkpoint_path)
                _check_root(run, report, read_record(checkpoint_path))
                return record, checked
            _need(sha256(previous).hexdigest() == record['checked_preparation']['previous_run_report_sha256'],
                  'Run report changed since publication was reserved; preserve existing work')
        else:
            _need(report.get('stage') == 'phaser' and report.get('status') in {'MR_SUCCESS', 'MR_REVIEW'}
                  and 'postmr' not in report and 'autosol' not in report and not checkpoint_path.exists() and not checkpoint_path.is_symlink(),
                  'Initial publication requires an unadopted Phaser run without checkpoints')
            checked, exact = _read_ordinary_postmr_result(run, attempt_number=attempt_number)
            # This is a NEW adoption. Verify the current requested mutations
            # against the recorded producer once; completed publications do not
            # reinterpret their old mutation plan through future planning policy.
            from .postmr import build_mutation_plan
            construction = exact['construction_inputs']['report']
            original = request/'inputs/construction'/construction['inputs']['reference_model']['path']
            actions = [asdict(a) for a in build_mutation_plan(report, original, run_directory=run)]
            _need(actions == construction['controls']['actions'], 'Run mutation intent differs from recorded construction')
            payload = _payload(run, report, checked, exact, created=now(), previous_report_sha256=sha256(previous).hexdigest())
            # Existing root validation checks observations, model and phosphate
            # intent before publishing anything. Binding is attached after sealing.
            candidate = dict(report, postmr={k:v for k,v in payload.items() if k != 'checked_preparation'})
            _root_payload(candidate, run)
            record = write_record(receipt, payload)
        published = dict(report, stage='postmr', status='POSTMR_READY', message=record['message'],
                         updated_utc=record['created_utc'], postmr=record)
        desired = _registry(run, published)
        if checkpoint_path.exists() or checkpoint_path.is_symlink():
            _read(checkpoint_path)
            existing = read_record(checkpoint_path)
            _need({k:v for k,v in existing.items() if k != 'record_sha256'} == desired,
                  'Partial publication checkpoint changed; preserve existing work')
        else:
            write_record(checkpoint_path, desired)
        _publish_run_report(root_path, record['checked_preparation']['previous_run_report_sha256'], published)
        return record, checked
