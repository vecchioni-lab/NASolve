"""Retain a verified metal construction and experiment as an ordinary review input.

This is not a refinement executor. The new node is deliberately not reusable by
ordinary refinement, selection or lossy manual import. A future mixed execution
consumer must qualify final adapted inputs, crystal forces and returned state.
Historical registry versions and ordinary AutoSol approval retain their meaning.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

CHECKPOINT_SCHEMA = 6
POLICY_ID = 'source-backed-metal-checkpoint-v1'
KIND = 'metal-construction'


def _need(value, message):
    if not value:
        raise ValueError(message)


def _file(run, reference, role):
    from .refinement_command_binding import _portable
    from .refinement_inputs import _bound_path
    _portable(reference)
    return _bound_path(reference, role, run)


def _reference(run, path):
    from .checkpoints import _file_reference
    from .refinement_command_binding import _portable
    reference = _file_reference(path, run)
    _portable(reference)
    return reference


def _native_review(run, parent, hypothesis, native_reference):
    from .cif_attachment_native import _capture, _native_atoms
    from .cif_dictionary_sites import _bind_capture_inputs
    model = _file(run, hypothesis['files']['model'], 'metal model')
    receipt_path = _file(run, native_reference, 'metal native receipt')
    receipt, native, snapshots = _capture(receipt_path, model.read_bytes())
    _need(receipt['status'] == 'REVIEW' and receipt['execution']['returncode'] == 0,
          'Metal input requires completed native interpretation, not refinement')
    _native_atoms(native, model.read_bytes())
    inputs = [_file(run, r, 'metal inherited restraint') for r in parent['restraints']]
    inputs.append(_file(run, hypothesis['files']['restraints'], 'metal recipe PHIL'))
    _bind_capture_inputs(receipt, model,
        [p for p in inputs if p.suffix.casefold() == '.cif'],
        [p for p in inputs if p.suffix.casefold() != '.cif'])
    _need(all(p.read_bytes() == raw for p, raw in snapshots.items()),
          'Native metal capture changed during review')
    return dict(status='PREPARATION_INPUTS_VERIFIED', native_receipt=deepcopy(native_reference),
        native_version=receipt['phenix_version'], atom_count=native['atom_count'],
        ordered_inputs=[{k:r[k] for k in ('role','sha256','size')} for r in receipt['inputs']],
        scientific_acceptance='NOT_ASSESSED', execution_ready=False)


def _review_inputs(run, parent, hypothesis_reference, native_reference, selectors):
    try:
        from iotbx import reflection_file_reader
        from libtbx import phil
    except ImportError as exc:
        raise ValueError('Source-backed metal inputs require the Phenix Python environment for discovery and diffraction replay') from exc
    from .metal.materialize import verify_hypothesis, _source
    from .metal.recipe import digest
    from .refinement_mixed_parent import _selectors
    from .refinement_external_autosol import review_external_autosol
    from .refinement_diffraction_source import read_source_arrays
    from .ligand_profiles import validate_model_phosphate_policy

    _need(parent.get('usable') is True and 'checked_preparation' in parent,
          'Metal input needs an independently checked ordinary preparation')
    _need(parent.get('phases') is None, 'External metal discovery cannot replace parent phases')
    manifest_path = _file(run, hypothesis_reference, 'metal hypothesis')
    _need(manifest_path.name == 'manifest.json', 'Require the exact metal hypothesis manifest')
    hypothesis = verify_hypothesis(run, manifest_path.parent)
    _need(hypothesis['parent']['checkpoint_id'] == parent['id'], 'Metal hypothesis belongs to another parent')
    for key in ('model', 'observations', 'phases', 'restraints'):
        _need(hypothesis['inputs'][key] == parent[key], 'Metal hypothesis parent ' + key + ' differs')
    _need(not hypothesis['unrestrained_metal_nodes'], 'Metal input has unrestrained metal nodes')
    placement = json.loads(_source(hypothesis['files']['placement'], run))
    _need(placement.get('schema_version') == 2, 'Ordinary metal input requires source-backed discovery')
    external = placement['discovery']['external_autosol']
    report = json.loads(_source(hypothesis['files']['report'], run))
    _selectors(selectors)
    observations = _file(run, parent['observations'], 'original observations')
    phase, phase_review = review_external_autosol(run, external, report=report,
        observations=observations, phase_labels=selectors['phase_labels'])
    arrays = read_source_arrays(data_file=observations, phase_file=phase, **selectors)
    experiment = dict(phase_origin='external-declared-autosol', producer_scope='EXPERIMENT_ONLY',
        declaration=deepcopy(external), selectors=deepcopy(selectors),
        phase_reference=_reference(run, phase), observations=len(arrays.observations),
        free_count=sum(arrays.flags[1]), phases=len(arrays.hl[0]),
        indexed_values_sha256=digest(dict(observations=arrays.observations, flags=arrays.flags, hl=arrays.hl)),
        source_cell=list(arrays.crystal.unit_cell().parameters()),
        source_space_group=str(arrays.crystal.space_group_info()),
        native_version=phase_review['native_version'], ordinary_autosol_approval=False,
        discovery_occupancy='RAW_DISCOVERY_OUTPUT_NOT_QUANTITATIVE_Q')
    model = _file(run, hypothesis['files']['model'], 'metal model')
    validate_model_phosphate_policy(model, report, run_directory=run)
    native = _native_review(run, parent, hypothesis, native_reference)
    # Native review can be the slowest read. Recheck the scientific closure
    # afterwards so a late source change cannot publish an earlier verdict.
    references = [hypothesis_reference, native_reference, parent['model'],
        parent['observations'], *parent['restraints'],
        *hypothesis['files'].values(), *external['sources'].values()]
    for reference in references:
        _file(run, reference, 'metal input final source check')
    _need(_reference(run, manifest_path) == hypothesis_reference,
          'Metal hypothesis changed during input review')
    return hypothesis, experiment, native


def _payload(run, record, reference, hypothesis):
    parent = record['parent']
    return dict(id=record['checkpoint'], parent=parent['id'], kind=KIND,
        created_utc=record['created_utc'], status='REVIEW', usable=False,
        recipe='Metal/source-backed-construction', label=record['label'],
        model=deepcopy(hypothesis['files']['model']), observations=deepcopy(parent['observations']),
        phases=None, restraints=[*deepcopy(parent['restraints']), deepcopy(hypothesis['files']['restraints'])],
        metal_construction=deepcopy(reference), metrics={},
        compatibility=dict(validated=False, review_required=True, source='VERIFIED_METAL_INPUT',
            execution='MIXED_POLICY_REQUIRED'),
        **({'terminal_geometry_protection':deepcopy(parent['terminal_geometry_protection'])}
           if 'terminal_geometry_protection' in parent else {}))


def _marked(node):
    return (node.get('kind') == KIND or 'metal_construction' in node
            or isinstance(node.get('id'), str) and node['id'].startswith('metal-'))


def validate_metal_checkpoints(run, registry):
    """Called by the ordinary reader; no native process or mutable registry pin.

Replay uses the same explicit native libraries as source-backed discovery.
Unrelated later report/registry publication is allowed; scientific inputs and the
exact parent payload remain frozen. Nothing upgrades this input to a refined node.
"""
    from .campaign_records import path_in, read_record
    if not any(isinstance(n, dict) and _marked(n) for n in registry['checkpoints']):
        return
    _need(all(isinstance(n, dict) and isinstance(n.get('id'), str) for n in registry['checkpoints']),
          'Malformed metal checkpoint lineage')
    indexed = {n['id']: n for n in registry['checkpoints']}
    _need(len(indexed) == len(registry['checkpoints']), 'Duplicate metal checkpoint lineage identity')
    for node in registry['checkpoints']:
        if not _marked(node):
            continue
        _need(registry['schema_version'] == CHECKPOINT_SCHEMA, 'Metal input requires checkpoint schema 6')
        identifier = node.get('id')
        _need(isinstance(identifier, str) and re.fullmatch(r'metal-[0-9]{3,}', identifier),
              'Malformed metal checkpoint identity')
        _need(registry.get('current') != identifier,
              'Held metal construction cannot be the current refinement checkpoint')
        path = path_in(run, f'AutoRefine/Checkpoints/{identifier}/input.json')
        _need(not (path.parent/'failure.json').exists(), 'Metal input publication failed')
        reference = node.get('metal_construction')
        _need(_file(run, reference, 'metal construction') == path, 'Metal construction belongs to another checkpoint')
        record = read_record(path)
        _need(set(record) == {'schema_version','policy_id','checkpoint','created_utc','label',
            'parent','hypothesis','native_receipt','selectors','experiment','native_preparation',
            'scientific_acceptance','execution_ready','refinement','record_sha256'},
            'Unexpected metal input fields')
        _need(type(record['schema_version']) is int and record['schema_version'] == 1
              and record['policy_id'] == POLICY_ID and record['checkpoint'] == identifier,
              'Unsupported metal input record')
        parent = indexed.get(node.get('parent'))
        _need(parent is not None and parent == record['parent'], 'Metal input ordinary parent changed')
        hypothesis, experiment, native = _review_inputs(run, parent, record['hypothesis'],
            record['native_receipt'], record['selectors'])
        _need(record['experiment'] == experiment and record['native_preparation'] == native,
              'Metal experiment or native evidence differs from its sources')
        _need(record['scientific_acceptance'] == 'NOT_ASSESSED' and record['execution_ready'] is False
              and record['refinement'] == 'NOT_RUN', 'Metal input is not a refined or accepted model')
        _need(node == _payload(run, record, reference, hypothesis), 'Metal checkpoint differs from its verified input')
    # Until a mixed consumer is qualified, a manual/refined child cannot erase
    # this hold by merely copying a model or inheriting a restraint list.
    for node in registry['checkpoints']:
        parent = indexed.get(node.get('parent'))
        _need(parent is None or not _marked(parent), 'A metal construction needs the qualified mixed execution consumer')


def publish_metal_checkpoint(run, *, hypothesis, native_receipt, selectors, label):
    """Save one unselected, held REVIEW input; reuse existing immutable artifacts.

The supplied hypothesis fixes its exact ordinary parent. The placement supplies
the discovery/phase declaration; explicit selectors fix the original Free-R/HL
index join. The receipt authenticates preparation inputs, not final execution
adaptation or applied crystal forces. No model/MTZ/capture is copied.
"""
    from . import checkpoints as cp
    from .campaign_records import now, path_in, write_record
    from .metal.context import _metadata_snapshot
    run, registry = cp.read_registry(Path(run))
    _need(registry.get('schema_version') in {3,4,5,CHECKPOINT_SCHEMA}
          and isinstance(registry.get('record_sha256'), str),
          'Metal publication requires an existing checked ordinary registry')
    before = _metadata_snapshot(run)
    _need(isinstance(label, str), 'Metal input label must be text')
    label = cp._valid_bookmark(label)
    directory = Path(hypothesis).expanduser()
    if not directory.is_absolute(): directory = run/directory
    native_path = Path(native_receipt).expanduser()
    if not native_path.is_absolute(): native_path = run/native_path
    hypothesis_ref = _reference(run, directory/'manifest.json')
    native_ref = _reference(run, native_path)
    raw = json.loads(_file(run, hypothesis_ref, 'metal hypothesis').read_bytes())
    parent = cp.resolve_checkpoint(registry, raw['parent']['checkpoint_id'])
    selectors = deepcopy(selectors)
    verified, experiment, native = _review_inputs(run, parent, hypothesis_ref, native_ref, selectors)
    _need(_metadata_snapshot(run) == before, 'Ordinary inputs changed during metal publication')
    number = int(cp.next_checkpoint_id(registry, 'metal').split('-')[1])
    while True:
        identifier = f'metal-{number:03d}'
        folder = path_in(run, f'AutoRefine/Checkpoints/{identifier}')
        try:
            folder.mkdir(parents=True)
            break
        except FileExistsError:
            number += 1
    try:
        record = dict(schema_version=1, policy_id=POLICY_ID, checkpoint=identifier,
            created_utc=now(), label=label, parent=deepcopy(parent), hypothesis=hypothesis_ref,
            native_receipt=native_ref, selectors=selectors, experiment=experiment,
            native_preparation=native, scientific_acceptance='NOT_ASSESSED',
            execution_ready=False, refinement='NOT_RUN')
        path = folder/'input.json'
        write_record(path, record)
        reference = _reference(run, path)
        payload = _payload(run, record, reference, verified)
        # Recheck all source-derived evidence before the guarded registry save.
        again = _review_inputs(run, parent, hypothesis_ref, native_ref, selectors)
        _need(again == (verified, experiment, native) and _metadata_snapshot(run) == before,
              'Metal or ordinary inputs changed before publication')
        registry['schema_version'] = CHECKPOINT_SCHEMA
        cp.append_checkpoint(run, registry, payload, select=False)
        return cp.checkpoint_record(payload, run)
    except Exception as exc:
        write_record(folder/'failure.json', dict(status='FAILED', error=str(exc)))
        raise


def inspect_metal_checkpoint(run, checkpoint):
    """Return the exact verified input record without selecting or executing it."""
    from .checkpoints import read_registry, resolve_checkpoint
    from .campaign_records import read_record
    run, registry = read_registry(Path(run))
    node = resolve_checkpoint(registry, checkpoint)
    _need(node.get('kind') == KIND, 'Checkpoint is not a metal construction')
    return read_record(_file(run, node['metal_construction'], 'metal construction'))
