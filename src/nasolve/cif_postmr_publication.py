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

from .autosol_reference import CHECKPOINT_SCHEMA as SITE_REFERENCE_SCHEMA
from .campaign_records import now, read_record, write_record, _sync_directory
from .campaign_process import exclusive_lock
from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _bytes
from .cif_model_context import _intent, prepared_model_topology
from .cif_ordinary_postmr import _ordinary_request_directory, _read_ordinary_postmr_result

POLICY_ID = 'checked-postmr-publication-v1'
CHECKPOINT_SCHEMA = 3
ALTERNATIVE_SCHEMA = 4
ALTERNATIVE_POLICY = 'checked-postmr-alternative-v1'


def _intent_digest(report):
    return sha256(_bytes({k: report.get(k) for k in ('workflow', 'frame', 'inputs', 'post_mr_plan')})).hexdigest()


def _reference(path, run):
    from .checkpoints import _file_reference
    ref = _file_reference(path, run)
    _need(ref['anchor'] != 'absolute', 'Published preparation input needs a declared run/dataset anchor')
    return ref


def _payload(run, report, checked, exact, *, created, previous_report_sha256):
    from .checkpoints import _required_observations
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
    observations = _required_observations(report,run)
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


def _checked_record(run, report, record, *, verified=None):
    meta = record.get('checked_preparation')
    _need(isinstance(meta, dict) and meta.get('policy_id') == POLICY_ID, 'Missing checked preparation binding')
    _need(isinstance(meta.get('previous_run_report_sha256'), str) and re.fullmatch('[0-9a-f]{64}', meta['previous_run_report_sha256']), 'Malformed original run-report checksum')
    _need(isinstance(record.get('created_utc'), str) and datetime.fromisoformat(record['created_utc']).tzinfo is not None, 'Malformed publication date')
    _need(meta.get('input_intent_sha256') == _intent_digest(report), 'Frozen run intent changed after publication')
    _need(type(meta.get('attempt_number')) is int and meta['attempt_number'] >= 1, 'Malformed preparation attempt identity')
    checked, exact = verified if verified is not None else _read_ordinary_postmr_result(run, attempt_number=meta.get('attempt_number'))
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
    _need(type(registry.get('schema_version')) is int and registry['schema_version'] in {CHECKPOINT_SCHEMA, ALTERNATIVE_SCHEMA, SITE_REFERENCE_SCHEMA},
          'Checked preparation requires checkpoint schema 3, 4 or 5')
    items = registry.get('checkpoints')
    _need(isinstance(items, list) and all(isinstance(i, dict) for i in items), 'Malformed checked checkpoint registry')
    roots = [item for item in items if item.get('id') == 'postmr']
    _need(len(roots) == 1, 'Require one checked PostMR root')
    # Later AutoSol evidence is validated by its own consumer, not required to
    # re-establish the original preparation (which predates AutoSol).
    expected = _root_payload({k:v for k,v in report.items() if k != 'autosol'}, run)
    _need(roots[0] == expected, 'Checked root differs from published preparation')


def _alternative_path(run, number):
    _need(type(number) is int and number >= 1, 'Require an exact positive preparation attempt')
    from .campaign_records import path_in
    return path_in(run,f'PostMR/Preparations/attempt-{number:04d}.json')


def _alternative_node(run, report, record):
    from .checkpoints import _root_payload
    preparation = record['preparation']
    number = preparation['checked_preparation']['attempt_number']
    node = _root_payload(dict({k:v for k,v in report.items() if k != 'autosol'}, postmr=preparation), run)
    node.update(id=f'prepare-{number:03d}', parent='postmr', kind='preparation',
        recipe='PostMR/checked-preparation-alternative', preparation_relation='SAME_FROZEN_CONSTRUCTION',
        checked_preparation=_reference(_alternative_path(run,number),run))
    return node


def _check_alternative(run, report, record, number, verified):
    preparation = record.get('preparation')
    _need(isinstance(preparation,dict) and isinstance(preparation.get('checked_preparation'),dict)
          and preparation['checked_preparation'].get('attempt_number') == number,
          'Alternative preparation attempt differs')
    _need(number > report['postmr']['checked_preparation']['attempt_number'],
          'Alternative requires a later attempt of the same frozen construction')
    expected = dict(policy_id=ALTERNATIVE_POLICY, checkpoint_id=f'prepare-{number:03d}',
        initial_preparation=_reference(run/'PostMR/report.json',run), preparation=preparation)
    _need({k:v for k,v in record.items() if k != 'record_sha256'} == expected,
          'Alternative receipt differs from its initial preparation binding')
    return _checked_record(run,report,preparation,verified=verified)


def validate_published_preparation(run, report, registry=None, *, additional_attempts=()):
    """Validate published choices in one history read; preserve legacy semantics.

    A later preparation is an alternative from frozen construction, not a refined
    descendant's coordinates. Return call-local verified results for publication;
    no verdict survives this read and no saved receipt or selection is changed.
    """
    postmr = report.get('postmr')
    active = isinstance(postmr, dict) and 'checked_preparation' in postmr
    active = active or (isinstance(registry, dict) and registry.get('schema_version') in (CHECKPOINT_SCHEMA,ALTERNATIVE_SCHEMA,SITE_REFERENCE_SCHEMA))
    path = run/'PostMR/report.json'
    if not active and path.is_file():
        try:
            saved = json.loads(path.read_text())
            active = isinstance(saved, dict) and 'checked_preparation' in saved
        except (OSError, ValueError):
            return  # An unrelated legacy side report is not a new authority.
    if not active:
        return
    report_path = run/'report.json'
    pins = {path:_read(path), report_path:_read(report_path)}
    _need(json.loads(pins[report_path]) == report, 'Run report changed during validation')
    record = read_record(path)
    _need(postmr == record, 'Run report does not match its published checked preparation')
    from .checkpoints import registry_path
    cp = registry_path(run); pins[cp] = _read(cp)
    saved_registry = read_record(cp)
    _need(registry is None or registry == saved_registry, 'Checkpoint registry changed during read')
    _check_root(run, report, saved_registry)
    alternatives = {}
    items = saved_registry['checkpoints']
    identifiers = [i.get('id') for i in items]
    _need(all(isinstance(i,str) for i in identifiers) and len(set(identifiers)) == len(identifiers),
          'Malformed checked checkpoint identities')
    for item in items:
        if item['id'] == 'postmr': continue
        marked = (item.get('kind') == 'preparation' or item['id'].startswith('prepare-')
                  or 'preparation_relation' in item or 'checked_preparation' in item)
        if not marked: continue
        _need(saved_registry['schema_version'] in {ALTERNATIVE_SCHEMA, SITE_REFERENCE_SCHEMA},
              'Preparation alternatives require checkpoint schema 4')
        match = re.fullmatch(r'prepare-([0-9]{3,})',item['id'])
        _need(match is not None, 'Malformed preparation checkpoint identity')
        number = int(match.group(1)); receipt = _alternative_path(run,number)
        _need(number not in alternatives, 'Duplicate preparation attempt')
        pins[receipt] = _read(receipt)
        alternatives[number] = (item, read_record(receipt))
    meta = record.get('checked_preparation')
    _need(isinstance(meta,dict), 'Missing initial checked preparation binding')
    initial = meta.get('attempt_number')
    _need(type(initial) is int and initial >= 1 and all(type(n) is int and n >= 1 for n in additional_attempts),
          'Require exact positive preparation attempts')
    numbers = sorted({initial,*alternatives,*additional_attempts})
    if alternatives or additional_attempts:
        from .cif_ordinary_postmr import _read_ordinary_postmr_results
        verified = _read_ordinary_postmr_results(run,numbers)
    else:
        verified = {initial:_read_ordinary_postmr_result(run,attempt_number=initial)}
    _checked_record(run,report,record,verified=verified[initial])
    for number,(item,receipt) in alternatives.items():
        _check_alternative(run,report,receipt,number,verified[number])
        _need(item == _alternative_node(run,report,receipt),
              'Alternative checkpoint differs from its exact checked preparation')
    from .autosol_reference import validate_reference
    validate_reference(run, saved_registry)
    _need(all(_read(path) == before for path,before in pins.items()),
          'Published preparation changed during validation')
    return verified


def validate_preparation_lineage(registry, selected):
    """Retain inherited restraints along the selected branch; allow new models."""
    if registry.get('schema_version') not in {CHECKPOINT_SCHEMA, ALTERNATIVE_SCHEMA, SITE_REFERENCE_SCHEMA}:
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
        if node.get('kind') == 'preparation':
            _need(registry.get('schema_version') in {ALTERNATIVE_SCHEMA, SITE_REFERENCE_SCHEMA}
                  and node.get('preparation_relation') == 'SAME_FROZEN_CONSTRUCTION'
                  and parent['id'] == 'postmr' and 'checked_preparation' in node,
                  'Malformed preparation alternative lineage')
        else:
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
            _check_new_mutation_intent(run,report,request,exact)
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



def _check_new_mutation_intent(run, report, request, exact):
    from .postmr import build_mutation_plan
    construction = exact['construction_inputs']['report']
    original = request/'inputs/construction'/construction['inputs']['reference_model']['path']
    actions = [asdict(a) for a in build_mutation_plan(report,original,run_directory=run)]
    _need(actions == construction['controls']['actions'], 'Run mutation intent differs from recorded construction')


def publish_preparation_alternative(run_directory, *, attempt_number):
    """Save/recover an unselected REVIEW alternative; preserve the initial root.

    The exact same construction/request may supply a later checked model/restraint
    set. It is never represented as coordinates derived from a refined checkpoint.
    A sealed receipt precedes the atomic registry append. On interruption, reuse
    that receipt and preserve any intervening selection/bookmarks. No native call.
    """
    _need(type(attempt_number) is int and attempt_number >= 1, 'Require an exact positive preparation attempt')
    from .checkpoints import registry_path, save_registry, _root_payload
    run = Path(run_directory).expanduser().resolve()
    request = _ordinary_request_directory(run)
    _need(request.is_dir(), 'No saved ordinary preparation request')
    with exclusive_lock(request/'request.lock'):
        previous = _read(run/'report.json'); report = json.loads(previous)
        _need(isinstance(report,dict) and isinstance(report.get('postmr'),dict)
              and isinstance(report['postmr'].get('checked_preparation'),dict),
              'Alternative requires an initial checked preparation; legacy runs are not converted')
        initial = report['postmr']['checked_preparation'].get('attempt_number')
        _need(type(initial) is int and attempt_number > initial,
              'Alternative requires a later attempt of the same frozen construction')
        _read(registry_path(run)); registry = read_record(registry_path(run))
        verified = validate_published_preparation(run,report,registry,additional_attempts=(attempt_number,))
        checked,exact = verified[attempt_number]
        receipt = _alternative_path(run,attempt_number)
        if receipt.exists() or receipt.is_symlink():
            _read(receipt); record = read_record(receipt)
            _check_alternative(run,report,record,attempt_number,verified[attempt_number])
        else:
            _check_new_mutation_intent(run,report,request,exact)
            preparation = _payload(run,report,checked,exact,created=now(),
                                   previous_report_sha256=sha256(previous).hexdigest())
            _root_payload(dict({k:v for k,v in report.items() if k != 'autosol'},postmr=preparation),run)
            record = write_record(receipt,dict(policy_id=ALTERNATIVE_POLICY,
                checkpoint_id=f'prepare-{attempt_number:03d}',
                initial_preparation=_reference(run/'PostMR/report.json',run),preparation=preparation))
        receipt_bytes = _read(receipt)
        _need(read_record(receipt) == record, 'Alternative receipt changed during publication')
        node = _alternative_node(run,report,record)
        existing = [item for item in registry['checkpoints'] if item['id'] == node['id']]
        _need(not existing or existing == [node], 'Reserved preparation checkpoint conflicts with existing work')
        _need(_read(run/'report.json') == previous, 'Run report changed during alternative publication; receipt retained')
        _need(_read(receipt) == receipt_bytes, 'Alternative receipt changed during publication')
        if not existing:
            registry['schema_version'] = max(registry['schema_version'], ALTERNATIVE_SCHEMA)
            registry['checkpoints'].append(node)
            save_registry(run,registry)  # C250 locks and compares the original identity.
        return record, checked.limitations
