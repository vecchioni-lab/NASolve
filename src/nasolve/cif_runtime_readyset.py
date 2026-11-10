"""ReadySet continuation of an independently qualified selected runtime.

Reuse the existing observer and exact native comparator. A failed optional
improvement retains the selected parent, including its repaired dictionaries.
This module owns neither recovery attempts nor production checkpoint adoption.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_dictionary_sites import _need, _read, _bind_capture
from .cif_dictionary_bundle import read_dictionary_bundle
from .cif_dictionary_bundle_readyset import _readyset_endpoint_inputs
from .cif_component_runtime import _tree, ORIGINAL_POLICY_ID, REPAIRED_POLICY_ID
from .cif_runtime_bundle import MANIFEST_FILE, _load_json, resolve_runtime_bundle
from .ligand_profiles import combine_dictionary_inputs

POLICY_ID = 'cif-selected-runtime-readyset-roundtrip-v1'


def _parent(manifest):
    path = Path(manifest).absolute()
    if path.is_dir(): path = path/MANIFEST_FILE
    _need(not any(p.is_symlink() for p in (path, *path.parents)), 'Unsafe parent runtime')
    # Check before recursive resolution. This continuation accepts one qualified
    # request result, not an arbitrarily nested chain of ReadySet publications.
    _need(_load_json(path).get('policy_id') in (ORIGINAL_POLICY_ID, REPAIRED_POLICY_ID),
          'Require a qualified original or repaired parent runtime')
    return resolve_runtime_bundle(path)


@contextmanager
def _selected_view(manifest):
    parent = _parent(manifest); root = parent['manifest_path'].parent
    frozen = _tree(root)
    prepared = read_dictionary_bundle(root/'evidence/bundle')
    original = prepared['after_dictionaries']; selected = parent['dictionaries']
    _need(len(original) == len(selected)
          and _read(parent['model']) == _read(prepared['model'])
          and [_read(p) for p in parent['phils']] == [_read(p) for p in prepared['after_phils']],
          'Selected runtime model, dictionary membership or PHIL order differs')
    indices = {c:original.index(p) for c,p in prepared['component_dictionaries'].items()}
    _need(len(set(indices.values())) == len(indices), 'Selected component owners alias')
    _need(all(_read(selected[i]) == _read(p) for i,p in enumerate(original) if i not in indices.values()),
          'Selected runtime changed a site modifier')
    components = {c:selected[i] for c,i in indices.items()}
    try:
        with TemporaryDirectory(prefix='runtime-readyset-inputs-') as temporary:
            combined = Path(temporary).resolve()/'selected.cif'
            combine_dictionary_inputs([components[c] for c in sorted(components)], combined)
            view = {**prepared, 'model':parent['model'], 'dictionary':combined,
                    'component_dictionaries':components, 'after_dictionaries':selected,
                    'after_phils':parent['phils']}
            yield parent, view
    finally:
        _need(_tree(root) == frozen, 'Selected parent runtime changed during continuation')


def audit_runtime_readyset_consumption(manifest, phenix, output, *, timeout_seconds=180, _process_runner=None):
    """Observe one bounded ReadySet call using the selected numerical dictionaries.

    Frozen inputs and failures use the existing ReadySet report. Publication later
    binds them to the qualified parent; consumption alone never adopts an endpoint.
    """
    from .cif_postmr_readyset import audit_readyset_bundle_consumption
    output = Path(output).absolute()
    with _selected_view(manifest) as (parent, view):
        root = parent['manifest_path'].parent
        target = output.resolve()
        _need(not target.is_relative_to(root.resolve()) and not root.resolve().is_relative_to(target),
              'ReadySet output overlaps selected parent runtime')
        return audit_readyset_bundle_consumption(view['source'], view['dictionary'], view['model'],
            view['report']['components'], phenix, view['report']['consumer'], output,
            timeout_seconds=timeout_seconds, component_dictionaries=view['component_dictionaries'],_process_runner=_process_runner)


def runtime_readyset_endpoint_inputs(manifest, readyset_directory, *, atom_order_directory=None):
    """Replay the shared observer checks against the exact selected parent inputs."""
    with _selected_view(manifest) as (_, view):
        return _readyset_endpoint_inputs(view, readyset_directory, atom_order_directory=atom_order_directory)


def inspect_runtime_readyset(manifest, baseline_receipt, readyset_directory,
                            endpoint_receipt=None, *, atom_order_directory=None):
    """Compare a fresh selected-runtime baseline and final effective native inputs.

    Parent integrity/qualification is mandatory. Missing or failed optional evidence
    cannot substitute a pre-repair bundle for the independently qualified parent.
    """
    from .cif_attachment_native import _capture
    from .cif_postmr_cached_model import qualify_cached_model_roundtrip
    from .cif_native_monomers import POLICY_ID as monomer_policy, review_full_monomers
    with _selected_view(manifest) as (parent, view):
        endpoint = None; error = None; accepted = False; pins = {}
        try:
            inputs = _readyset_endpoint_inputs(view, readyset_directory, atom_order_directory=atom_order_directory)
            _need(baseline_receipt is not None, 'Fresh selected-runtime native baseline is missing')
            _need(endpoint_receipt is not None, 'Final effective ReadySet native readback is missing')
            before_record, before, before_files = _capture(Path(baseline_receipt), _read(parent['model']))
            record, after, after_files = _capture(Path(endpoint_receipt), _read(inputs['model']))
            _bind_capture(before_record, view['report']['consumer'], parent['model'], parent['dictionaries'], parent['phils'])
            _bind_capture(record, view['report']['consumer'], inputs['model'], inputs['dictionaries'], inputs['phils'])
            for r,native in ((before_record,before),(record,after)):
                _need(r.get('full_monomer_inventory_policy') == monomer_policy, 'Full native identities are required')
                review_full_monomers(native)
            endpoint = qualify_cached_model_roundtrip(before, after, parent['model'], inputs['model'])
            accepted = endpoint['mechanics_checks_pass'] is True
            # The comparator can be expensive. Recheck the observer and exact
            # final inputs afterward, including any serialization-only adapter.
            repeated = _readyset_endpoint_inputs(view, readyset_directory,
                atom_order_directory=atom_order_directory)
            _bind_capture(record, view['report']['consumer'], repeated['model'],
                repeated['dictionaries'], repeated['phils'])
            _need(all(_read(p) == data for p,data in {**before_files,**after_files}.items()),
                  'Native evidence changed during selected-runtime inspection')
            pins = dict(baseline_receipt_sha256=sha256(_read(Path(baseline_receipt))).hexdigest(),
                        endpoint_receipt_sha256=sha256(_read(Path(endpoint_receipt))).hexdigest(),
                        readyset_receipt_sha256=sha256(_read(Path(readyset_directory)/'readyset_consumption.json')).hexdigest())
            if atom_order_directory is not None:
                pins['atom_order_receipt_sha256'] = sha256(_read(Path(atom_order_directory)/'atom_order.json')).hexdigest()
        except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
            error = type(exc).__name__+': '+str(exc); accepted = False
        return dict(schema_version=1, policy_id=POLICY_ID,
            parent_manifest_sha256=sha256(_read(parent['manifest_path'])).hexdigest(),
            parent_selected=parent['manifest']['decision']['selected'], endpoint=endpoint, endpoint_error=error, **pins,
            decision=dict(status='CONTINUE_WITH_NOTES',
                selected=('readyset_ordered_checked_model' if atom_order_directory is not None else 'readyset_checked_model')
                    if accepted else 'verified_parent_runtime',
                parent_selected=parent['manifest']['decision']['selected'], scope='SEPARATE_DIAGNOSTIC_PHASE_ONLY',
                requires_cif_review=False, automatic_adoption=False),
            unavailable_native_checks=deepcopy(parent['manifest']['unavailable_native_checks']),
            scientific_qualification='NOT_ASSESSED', native_execution='NOT_RUN', automatic_adoption=False)


def selected_runtime_readyset_publication(root, controls):
    """Recompute one public selection using fixed source-evidence anchors."""
    _need(isinstance(controls,dict) and set(controls) ==
          {'runtime','baseline_receipt','readyset_directory','endpoint_receipt','atom_order_directory'},
          'Incomplete selected-runtime ReadySet controls')
    _need(controls['runtime'] == 'evidence/runtime' and controls['readyset_directory'] == 'evidence/readyset',
          'Selected-runtime evidence roots differ')
    names = {'runtime','readyset'}
    for field,folder,filename in [('baseline_receipt','baseline','native_receipt.json'),
                                  ('endpoint_receipt','endpoint','native_receipt.json'),
                                  ('atom_order_directory','atom-order',None)]:
        expected = 'evidence/'+folder+('/'+filename if filename else '')
        _need(controls[field] in (None,expected), 'Unsafe selected-runtime evidence reference')
        if controls[field] is not None: names.add(folder)
    evidence = root/'evidence'
    _need({p.name for p in evidence.iterdir()} == names and all(p.is_dir() and not p.is_symlink() for p in evidence.iterdir()),
          'Unexpected selected-runtime evidence roots')
    args = {k:root/v if v is not None else None for k,v in controls.items()}
    runtime = args.pop('runtime'); parent = _parent(runtime)
    review = inspect_runtime_readyset(runtime, **args)
    if isinstance(review['endpoint_error'], str):
        review['endpoint_error'] = review['endpoint_error'].replace(str(root.absolute())+'/', 'runtime_bundle/')
    decision = deepcopy(review['decision'])
    if decision['selected'] == 'verified_parent_runtime':
        inputs = {k:parent[k] for k in ('model','dictionaries','phils')}
        note = 'Optional ReadySet improvement was not selected; the qualified parent model and its selected restraints were retained together.'
    else:
        inputs = runtime_readyset_endpoint_inputs(runtime, args['readyset_directory'], atom_order_directory=args['atom_order_directory'])
        note = 'The ReadySet endpoint preserves the selected parent definitions, native policy and named restraints.'
    decision['notes'] = [note, 'Source qualification and numerical repair proof remain bound to the parent; ordinary refinement and checkpoint adoption are unassessed.']
    return review, decision, inputs, review['unavailable_native_checks']
