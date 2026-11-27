"""Bind one completed local fit and its fresh native geometry to a review checkpoint."""
from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from .campaign_records import _sync_directory, path_in
from .cif_attachment_native import _capture, _native_atoms
from .cif_dictionary_sites import _bind_capture, _need, _read
from .cif_furanose_fit import fit_inputs_from_checked
from .cif_furanose_fit_attempt import _parent, _read_finished
from .cif_na_policy import _qualify_observed_fields
from .cif_native_monomers import review_full_monomers
from .cif_native_parent_chemistry import _PROXY_FAMILIES, _PROXY_STATUS_FAMILIES
from .cif_ordinary_postmr import local_sugar_seed_note
from .cif_runtime_evidence import expanded_runtime_evidence, pack_runtime_evidence


def compare_fit_mechanics(before, after):
    """Require the full original geometry and chemistry after reinterpreting the moved sugar."""
    for native in (before, after):
        geometry = native.get('geometry', {})
        details = geometry.get('proxy_details', {})
        counts = geometry.get('proxy_counts', {})
        states = geometry.get('proxy_count_status', {})
        _need(native.get('status') == 'REVIEW' and native.get('inventory_detail') == 'linked'
              and native.get('fatal_problems') is None and native.get('unused_definitions') == []
              and native.get('unsupported_fields') == []
              and set(details) == set(counts) == _PROXY_FAMILIES
              and states == dict.fromkeys(_PROXY_STATUS_FAMILIES, 'RECORDED')
              and all(isinstance(rows, list) and type(counts[k]) is int and counts[k] == len(rows)
                      for k, rows in details.items()), 'The fitted sugar needs all eight native geometry families')
    _need(before['restraint_policy'] == after['restraint_policy'], 'Native restraint origin or policy changed')
    result = _qualify_observed_fields(before, after, None, [], preserve_native=True)
    failed = [row['check'] for row in result['checks'] if row['status'] != 'PASS']
    _need(result['mechanics_checks_pass'], 'Reinterpreting the fitted sugar changed ' + ', '.join(failed))
    return dict(after['geometry']['proxy_counts'])


def _qualify(receipt, fit, checked, plan, parent):
    receipt = Path(receipt).expanduser().resolve(strict=True)
    _need(receipt.name == 'native_receipt.json', 'Expected a native_receipt.json for the fitted coordinates')
    model = _read(fit.model)
    record, native, files = _capture(receipt, model)
    _bind_capture(record, plan.consumer, fit.model, checked.dictionary_paths, checked.restraint_paths)
    _native_atoms(native, model)
    _need(review_full_monomers(native) == review_full_monomers(parent),
          'The fitted model has different residue identities or native monomer coverage')
    counts = compare_fit_mechanics(parent, native)
    return dict(native_receipt_sha256=sha256(files[receipt]).hexdigest(), proxy_counts=counts,
                residue_count=native['full_monomer_inventory']['residue_count']), files


def _freeze_native(receipt, files, archive):
    """Freeze only the files read by the native verifier. Publish the archive atomically."""
    receipt = Path(receipt).expanduser().resolve(strict=True)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.native-fit-', dir=archive.parent) as temporary:
        stage = Path(temporary)
        tree = stage/'records'
        for source, data in files.items():
            destination = tree/source.relative_to(receipt.parent)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        packed = stage/'evidence.zip'
        pack_runtime_evidence(tree, packed)
        with packed.open('rb') as handle:
            os.fsync(handle.fileno())
        os.link(packed, archive)
        _sync_directory(archive.parent)


def _configured_phenix():
    from .config import load_config
    from .phenix_runtime import discover_phenix
    return discover_phenix(load_config())


def bind_fitted_preparation(run, checked, exact, number, *, native_receipt=None, may_freeze=False,
                            discover_phenix=None, after_native_read=None):
    """Return the checked fitted coordinates and portable evidence binding. Existing proofs reopen offline."""
    from .cif_postmr_publication import _reference

    _need(type(number) is int and number > 0, 'Require an exact positive sugar fit number')
    plan, parent_native = fit_inputs_from_checked(checked, exact)
    fit_root = path_in(_parent(run, checked.attempt_number), f'fit-{number:04d}')
    _need(fit_root.is_dir(), 'The named sugar fit does not exist for this preparation')
    fit = _read_finished(plan, fit_root, number)
    archive = path_in(run, f'PostMR/FittedPreparationEvidence/preparation-{checked.attempt_number:04d}/fit-{number:04d}.zip')
    managed = None
    if not archive.exists():
        _need(may_freeze, 'Frozen Phenix evidence for the fitted coordinates is missing')
        if native_receipt is None:
            from .cif_fitted_native_read import acquire_fit_read
            def verify(receipt):
                return _qualify(receipt, fit, checked, plan, parent_native)[1]
            receipt, files = acquire_fit_read(run, checked, plan, fit, discover=discover_phenix or _configured_phenix,
                                              after=after_native_read, verify=verify)
            managed = receipt, files
        else:
            receipt = native_receipt
            _, files = _qualify(receipt, fit, checked, plan, parent_native)
        _freeze_native(receipt, files, archive)
    else:
        _need(after_native_read is None, 'A verified native reading is already available. Omit --after-native-read to use it.')
    archive_ref = _reference(archive, run)
    with expanded_runtime_evidence(archive, archive_ref['sha256']) as view:
        source = (view/'evidence').resolve()
        assessment, archived_files = _qualify(source/'native_receipt.json', fit, checked, plan, parent_native)
        if managed:
            from .cif_fitted_native_read import compact_verified_read
            try:
                compact_verified_read(*managed, archived_files, source, archive_ref)
            except OSError as exc:
                from warnings import warn
                warn(f'Fitted native evidence is archived. Some duplicate working files may remain ({exc}).', RuntimeWarning)
    if native_receipt is not None:
        _need(sha256(_read(Path(native_receipt).expanduser().resolve(strict=True))).hexdigest()
              == assessment['native_receipt_sha256'], 'A different native receipt already belongs to this fit')
    _need(_reference(archive, run) == archive_ref, 'Frozen fitted-model evidence changed while reading')
    note = local_sugar_seed_note(plan.site, plan.code)
    _need(checked.local_fit_site == plan.site and note in checked.limitations, 'The preparation did not request this sugar fit')
    limitation = f'{plan.site} {plan.code} completed a local geometry fit. Inspect its remaining contacts after diffraction refinement.'
    selected = replace(checked, model_path=fit.model, local_fit_site=None,
                       message=f'The checked preparation supplied a locally fitted {plan.code} at {plan.site}.',
                       limitations=tuple(limitation if s == note else s for s in checked.limitations))
    binding = dict(policy_id='checked-local-sugar-publication-v1', fit_number=number, site=plan.site,
                   component=plan.code, fit_result=_reference(fit.report, run),
                   parent_native_sha256=plan.native_receipt_sha256, archive=archive_ref, **assessment)
    return selected, binding
