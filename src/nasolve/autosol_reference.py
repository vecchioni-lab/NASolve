"""Bind checked AutoSol site validation to the model chosen before launch.

The reference is small and immutable. It supplements the preparation proof; it
never replaces that proof, selects a checkpoint or changes the native MR input.
"""
from copy import deepcopy
import json
import math
import re
from hashlib import sha256

from .campaign_records import path_in, read_record, write_record
from .cif_dictionary_sites import _need, _read

CHECKPOINT_SCHEMA = 5
POLICY_ID = 'autosol-selected-site-reference-v1'
REFERENCE_PATH = 'AutoSol/site-reference.json'


def chosen_model(run, registry):
    from .checkpoints import _ref_path, resolve_checkpoint
    from .postmr import scan_anomalous_candidates
    checkpoint = resolve_checkpoint(registry)
    model = _ref_path(checkpoint.get('model'), 'AutoSol chosen model', run)
    return checkpoint, model, scan_anomalous_candidates(model)


def freeze_reference(run, registry, checkpoint, model, candidates, phaser_model,
                     automatic_tolerance, review_tolerance, report):
    from .checkpoints import _file_reference, save_registry
    from .autosol import _unit_cell
    model_ref = _file_reference(model, run)
    phaser_ref = _file_reference(phaser_model, run)
    _need(model_ref == checkpoint['model'], 'Chosen model changed before AutoSol launch')
    _need(model_ref.get('anchor') == phaser_ref.get('anchor') == 'run',
          'AutoSol model references must remain within their run')
    previous = _read(run/'report.json')
    _need(json.loads(previous) == report, 'Run report changed before AutoSol launch')
    _need(type(automatic_tolerance) in (int, float) and type(review_tolerance) in (int, float)
          and math.isfinite(automatic_tolerance) and math.isfinite(review_tolerance)
          and 0 < automatic_tolerance <= review_tolerance,
          'Malformed AutoSol acceptance/review distances')
    path = path_in(run, REFERENCE_PATH)
    write_record(path, dict(policy_id=POLICY_ID, checkpoint_id=checkpoint['id'],
        model=model_ref, original_phaser_model=phaser_ref,
        run_report_sha256_before_autosol=sha256(previous).hexdigest(),
        candidates=deepcopy(candidates), unit_cell=list(_unit_cell(model)),
        automatic_acceptance_distance=automatic_tolerance, review_distance=review_tolerance))
    reference = _file_reference(path, run)
    registry['schema_version'] = CHECKPOINT_SCHEMA
    registry['autosol_site_reference'] = reference
    # A competing selection is not overwritten: the existing guarded save must
    # succeed before any native process starts. Preserve the receipt on failure.
    save_registry(run, registry)
    return reference


def validate_reference(run, registry):
    """Check only the saved input binding; unused AutoSol outputs stay optional."""
    from .checkpoints import _ref_path, resolve_checkpoint
    from .autosol import _unit_cell
    from .postmr import scan_anomalous_candidates
    reference = registry.get('autosol_site_reference')
    if registry.get('schema_version') != CHECKPOINT_SCHEMA:
        _need(reference is None, 'AutoSol site reference requires checkpoint schema 5')
        return None
    _need(isinstance(reference, dict) and reference.get('anchor') == 'run'
          and reference.get('relative_path') == REFERENCE_PATH,
          'Missing or malformed AutoSol site reference')
    path = path_in(run, REFERENCE_PATH); _read(path)
    _need(_ref_path(reference, 'AutoSol site reference', run) == path,
          'AutoSol site reference resolves elsewhere')
    record = read_record(path)
    _need(set(record) == {'policy_id', 'checkpoint_id', 'model', 'original_phaser_model',
          'run_report_sha256_before_autosol', 'candidates', 'unit_cell',
          'automatic_acceptance_distance', 'review_distance', 'record_sha256'},
          'Malformed AutoSol site reference fields')
    previous = record.get('run_report_sha256_before_autosol')
    _need(isinstance(previous, str) and re.fullmatch('[0-9a-f]{64}', previous),
          'Malformed original AutoSol run-report checksum')
    _need(record.get('policy_id') == POLICY_ID, 'Unsupported AutoSol site reference policy')
    identifier = record.get('checkpoint_id')
    _need(isinstance(identifier, str) and bool(identifier), 'Missing AutoSol reference checkpoint')
    checkpoint = resolve_checkpoint(registry, identifier)
    _need(checkpoint.get('id') == identifier, 'AutoSol checkpoint identity was redirected')
    _need(record.get('model') == checkpoint.get('model'), 'AutoSol reference differs from its checkpoint model')
    model = _ref_path(record.get('model'), 'AutoSol reference model', run)
    original = record.get('original_phaser_model')
    _need(isinstance(original, dict) and original.get('anchor') == 'run',
          'Original Phaser reference must be run-relative')
    _ref_path(original, 'original Phaser phasing model', run)
    _need(record.get('candidates') == scan_anomalous_candidates(model),
          'AutoSol reference candidates differ from the chosen model')
    _need(record.get('unit_cell') == list(_unit_cell(model)),
          'AutoSol reference cell differs from the chosen model')
    for key in ('automatic_acceptance_distance', 'review_distance'):
        value = record.get(key)
        _need(type(value) in (int, float) and math.isfinite(value) and value > 0,
              'Malformed AutoSol reference distance')
    _need(record['automatic_acceptance_distance'] <= record['review_distance'],
          'AutoSol reference distances are reversed')
    return record


def validate_result_reference(run, report):
    """Phase/map consumers check the chosen-model binding, never current choice.

    Read the small registry/receipt directly; the caller's preparation read owns
    expensive history verification. Legacy runs keep their original contract.
    """
    from .checkpoints import registry_path
    from .autosol import _match_sites, _pdb_atoms, _autosol_outcome
    from .run_context import resolve_artifact_path
    from .model_assessment import file_sha256
    autosol = report.get('autosol')
    if not isinstance(autosol, dict):
        return
    postmr = report.get('postmr')
    checked = isinstance(postmr, dict) and 'checked_preparation' in postmr
    if not checked:
        _need('site_reference' not in autosol, 'AutoSol site reference requires checked preparation')
        return
    path = registry_path(run); _read(path); registry = read_record(path)
    reference = validate_reference(run, registry)
    if reference is None:
        _need('site_reference' not in autosol, 'AutoSol reference is not bound by the registry')
        return
    _need(autosol.get('site_reference') == registry['autosol_site_reference'],
          'AutoSol result differs from its saved site reference')
    # The native result is immutable for new checked runs. A result-publication
    # interruption leaves it available for diagnosis, never silently adopted.
    result_path = path_in(run, 'AutoSol/report.json'); _read(result_path)
    _need(read_record(result_path) == autosol, 'AutoSol result differs from its immutable report')
    validation = autosol.get('site_validation')
    if validation is None:
        _need(autosol.get('status') == 'AUTOSOL_WARNING'
              and autosol.get('use_for_refinement') is False,
              'AutoSol has no site validation for accepted phases')
        return reference
    _need(isinstance(validation, dict), 'Malformed AutoSol site validation')
    outputs = autosol.get('outputs')
    _need(isinstance(outputs, dict), 'Missing AutoSol outputs')
    heavy = resolve_artifact_path(outputs.get('heavy_atom_model'), run)
    _need(heavy is not None and file_sha256(heavy) == outputs.get('heavy_atom_model_sha256'),
          'AutoSol heavy-atom evidence changed')
    model = resolve_artifact_path(reference['model'], run)
    automatic = reference['automatic_acceptance_distance']; review = reference['review_distance']
    attempts = _match_sites(reference['candidates'], _pdb_atoms(heavy), model, automatic, review)
    distances = [item['nearest_site']['distance'] for item in attempts if 'nearest_site' in item]
    best = min(distances) if distances else None
    _need(validation.get('attempts') == attempts
          and validation.get('best_distance') == best
          and validation.get('automatic_acceptance_distance') == automatic
          and validation.get('review_distance') == review
          and validation.get('accepted') == [a for a in attempts if a.get('within_automatic_limit') is True]
          and validation.get('review_candidates') == [a for a in attempts if a.get('within_review_limit') is True
              and a.get('within_automatic_limit') is not True],
          'AutoSol validation differs from chosen-model evidence')
    status, _, accepted = _autosol_outcome(best, automatic, review)
    _need(autosol.get('status') == status and autosol.get('use_for_refinement') is accepted,
          'AutoSol phase acceptance differs from chosen-model evidence')
    return reference
