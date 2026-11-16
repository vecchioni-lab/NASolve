"""Read-only, site-scoped chemistry reporting for an exact refinement checkpoint.

Separate final-model interpretation is evidence about that model and those
restraints, not proof of the manager used inside a diffraction-refinement job.
No capture is launched, stored code executed, checkpoint selected or file saved.
"""
from hashlib import sha256
from pathlib import Path

from .cif_attachment_native import _capture, _native_atoms
from .cif_construction_native import _triple_readback
from .cif_dictionary_sites import _need, _read, _bind_capture_inputs
from .cif_captured_geometry import review_captured_geometry

POLICY_ID = 'refinement-declared-site-triple-readback-v1'


def _unassessed(reason):
    return dict(schema_version=1, policy_id=POLICY_ID, status='UNASSESSED',
        reason=reason, sites={}, target_screen='UNASSESSED', coordinate_screen='UNASSESSED',
        actual_refinement_manager='NOT_ASSESSED', scientific_approval='NOT_RUN',
        automatic_adoption=False, native_execution='NOT_RUN',
        limitations=['Explicit source triple bonds only; no whole-ligand or diffraction approval.',
            'A separate interpretation does not establish the actual final refinement manager.'])


def _readback(model, projections, dictionaries, phils, native_receipt=None):
    """Adapt already verified preparation resources and exact execution inputs."""
    model = Path(model)
    paths = [model, *dictionaries, *phils, *(p for p, _ in projections.values())]
    snapshots = {Path(p): _read(Path(p)) for p in paths}
    result = _unassessed('No separate final-model native capture was supplied.')
    result.update(model_sha256=sha256(snapshots[model]).hexdigest(),
        declared_sites={site: dict(component=code, projection_sha256=sha256(snapshots[Path(p)]).hexdigest())
                        for site, (p, code) in sorted(projections.items())})
    if native_receipt is not None:
        receipt_path = Path(native_receipt).resolve(strict=True)
        receipt, native, captured = _capture(receipt_path, snapshots[model])
        _need(receipt['execution']['status'] == 'COMPLETED' and native['status'] == 'REVIEW',
              'Require a completed final-model native interpretation')
        _native_atoms(native, snapshots[model])
        _bind_capture_inputs(receipt, model, dictionaries, phils)
        review_captured_geometry(native)  # Existing atom/proxy/count consistency checks.
        sites = {site: _triple_readback(path, code, native, site)
                 for site, (path, code) in sorted(projections.items())}
        screened = [row for row in sites.values() if row['triple_bonds']]
        result.update(reason=None, sites=sites,
            native_receipt_sha256=sha256(captured[receipt_path]).hexdigest(),
            native_scope='SEPARATE_FINAL_MODEL_REINTERPRETATION',
            phenix_version=receipt.get('phenix_version'),
            target_screen=('REVIEW' if any(r['target_screen'] != 'PASS' for r in screened) else 'PASS') if screened else 'UNASSESSED',
            coordinate_screen=('REVIEW' if any(r['coordinate_screen'] != 'PASS' for r in screened) else 'PASS') if screened else 'UNASSESSED',
            status=('REVIEW' if any(r['status'] != 'TRIPLE_SCREEN_PASS' for r in screened)
                    else 'SCOPED_TRIPLE_SCREEN_PASS') if screened else 'UNASSESSED')
        if not screened:
            result['reason'] = 'No explicit triple bonds occur in the declared site projections.'
        for path, data in captured.items():
            _need(path not in snapshots or snapshots[path] == data, 'Native capture input changed during read')
            snapshots[path] = data
    _need(all(_read(path) == data for path, data in snapshots.items()),
          'Refinement chemistry evidence changed during read')
    return result


def read_refinement_chemistry(run_directory, *, checkpoint, native_receipt=None):
    """Report one saved refinement against its own checked preparation lineage.

    The optional receipt must describe this final PDB and the exact ordered
    dictionaries/PHIL inherited by this round, including round-local namespace
    adaptations. Legacy or unavailable evidence stays explicitly unassessed.
    Supplied damaged or mismatched evidence raises; it is never an empty pass.
    """
    from .checkpoints import (_read_registry_with_preparations, resolve_checkpoint,
                             inherited_paths, _ref_path)
    from .refinement_inputs import validate_checkpoint_refinement_inputs
    _need(isinstance(checkpoint, str) and bool(checkpoint), 'Require an explicit refinement checkpoint')
    run, registry, verified = _read_registry_with_preparations(run_directory)
    item = resolve_checkpoint(registry, checkpoint)
    _need(item.get('kind') == 'refinement', 'Require a refinement checkpoint')
    # Resolve actual saved identity, not latest round or current selection.
    identity = dict(checkpoint=item['id'], preparation_checkpoint=None)
    if item.get('usable') is not True or item.get('model') is None:
        _need(native_receipt is None, 'An unusable checkpoint cannot supply final-model evidence')
        return dict(_unassessed('Refinement has no reusable final model.'), **identity)
    inherited = inherited_paths(item, run)
    indexed = {node['id']: node for node in registry['checkpoints']}
    node = item; seen = set()
    while 'checked_preparation' not in node and node.get('parent') is not None:
        _need(node['id'] not in seen and node['parent'] in indexed, 'Invalid preparation ancestry')
        seen.add(node['id']); node = indexed[node['parent']]
    if 'checked_preparation' not in node:
        _need(native_receipt is None, 'Final-model evidence requires declared checked-preparation projections')
        return dict(_unassessed('This lineage has no checked site projections.'), **identity)
    identity['preparation_checkpoint'] = node['id']
    record_path = _ref_path(node['checked_preparation'], 'checked preparation', run)
    from .campaign_records import read_record
    publication = read_record(record_path)
    metadata = publication.get('preparation', publication)['checked_preparation']
    _need(verified is not None and metadata['attempt_number'] in verified,
          'Missing validated preparation result')
    checked, exact = verified[metadata['attempt_number']]
    acquired = exact.get('preparation')
    prepared = None if acquired is None else acquired.get('bundle')
    _need(checked.model_path is not None and prepared is not None and prepared.get('projections'),
          'Checked result has no declared site projections')
    # The registry's preparation reader and lineage validator already bind the
    # exact selected runtime and inherited order. Apply only its verified spelling adapter.
    restraints = list(inherited['restraints'])
    adaptation = validate_checkpoint_refinement_inputs(run, item)
    if adaptation is not None:
        for row in adaptation['adaptations']:
            restraints[row['index']] = _ref_path(row['execution'], 'refinement execution input', run)
    dictionaries = [p for p in restraints if p.suffix.casefold() == '.cif']
    phils = [p for p in restraints if p.suffix.casefold() != '.cif']
    result = _readback(inherited['model'], prepared['projections'], dictionaries, phils, native_receipt)
    _need(result['model_sha256'] == item['model']['sha256'].lower(), 'Final checkpoint model changed during read')
    references = {row['path']: row for row in prepared['report']['files']}
    for site, (path, _) in prepared['projections'].items():
        relative = Path(path).relative_to(acquired['bundle_directory']).as_posix()
        _need(result['declared_sites'][site]['projection_sha256'] == references[relative]['sha256'],
              'Declared site projection changed during read')
    # Recheck exact execution references, without another expensive preparation replay.
    for ref in item['restraints']:
        _ref_path(ref, 'refinement restraint', run)
    validate_checkpoint_refinement_inputs(run, item)
    return dict(result, **identity)
