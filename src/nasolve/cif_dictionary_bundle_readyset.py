"""Read-only final ReadySet qualification for a frozen component bundle.

The starting bundle must qualify independently. ReadySet output is an optional
candidate until its actual effective model/dictionaries have a complete native
readback. A missing or failed improvement retains the checked starting evidence.
"""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_dictionary_store import _bytes, _json
from .cif_dictionary_sites import _bind_capture, _need, _read, _safe
from .cif_dictionary_bundle import read_dictionary_bundle, inspect_dictionary_bundle_native

POLICY_ID = 'cif-stored-bundle-readyset-roundtrip-v1'
ATOM_ORDER_POLICY_ID = 'cif-stored-bundle-readyset-roundtrip-v2'


def _artifact(root, ref):
    _need(isinstance(ref, dict) and ref.get('anchor') == 'postmr_readyset_directory'
        and _safe(ref.get('path')), 'Unsafe ReadySet artifact')
    path = root/ref['path']; data = _read(path)
    _need(ref.get('sha256') == sha256(data).hexdigest() and type(ref.get('size')) is int and ref['size'] == len(data),
        'ReadySet artifact differs')
    return path


def readyset_endpoint_inputs(bundle, readyset_directory, *, atom_order_directory=None):
    """Recheck the ordinary consumption proof and return exact final native inputs.

    Does not run ReadySet or trust its saved PASS/check booleans. This accepts the
    maintained per-component input policy only; incomplete attempts raise and
    can be retained as failed improvements by the final inspection function.
    An explicit atom-order directory must reconstruct from these exact inputs;
    it changes serialization only and still requires a fresh native capture.
    """
    from .cif_postmr_readyset import (read_readyset_consumption, COMPONENT_POLICY_ID,
        EXPECTED_ACTIONS, WORKER, _atoms, heavy_control, effective_cached_input, OBSERVED_MODULES)
    from .cif_readyset_process_policy import classify_subprocesses
    b = read_dictionary_bundle(bundle); root = Path(readyset_directory).absolute()
    saved = read_readyset_consumption(root); r = saved['report']
    _need(r['policy_id'] == COMPONENT_POLICY_ID and r.get('components') == b['report']['components']
        and r.get('automatic_adoption') is False and r.get('verified_input_retained') is True,
        'ReadySet component policy differs')
    for field in ('source', 'dictionary', 'model'):
        _need(_read(_artifact(root, r['inputs'][field])) == _read(b[field]), 'ReadySet input differs: '+field)
    _need(set(r.get('component_inputs', {})) == set(b['component_dictionaries']), 'ReadySet component owners differ')
    for code, path in b['component_dictionaries'].items():
        _need(_read(_artifact(root, r['component_inputs'][code])) == _read(path), 'ReadySet component input differs')
    heavy = _artifact(root, r['heavy_control']); model = _artifact(root, r['readyset_model'])
    dictionary = _artifact(root, r['effective_dictionary'])
    raw = _artifact(root, r['raw_readyset_dictionary']) if r.get('raw_readyset_dictionary') else None
    _need(_read(root/'readyset/consumption_worker.py') == WORKER.encode(), 'ReadySet observer implementation differs')
    spec = _json(_read(root/'readyset/consumption_spec.json'))
    trace = _json(_read(root/'readyset/consumption_trace.json'))
    result = _json(_read(root/'readyset/consumption_result.json'))
    _need(trace == r['trace'] and result == r['worker_result'], 'ReadySet observation differs from raw evidence')
    sources = r['source_evidence']; rows = sources['sources']
    _need(len({p['path'] for p in rows}) == len(rows), 'Duplicate ReadySet implementation pin')
    for row in rows:
        ref = row['snapshot']
        _need(row.get('anchor') == 'phenix_installation' and _safe(row.get('path'))
            and ref.get('anchor') == 'readyset_audit_directory' and _safe(ref.get('path')), 'Unsafe ReadySet source pin')
        data = _read(root/'source_evidence'/ref['path'])
        _need(len(data) == row['size'] and sha256(data).hexdigest() == row['sha256'], 'ReadySet source snapshot differs')
    _need(spec['sources'] == [{k:p[k] for k in ('path','sha256')} for p in rows]
        and spec['entrypoint'] == sources['entrypoint']['path'] and spec['expected_actions'] == EXPECTED_ACTIONS
        and _safe(spec['library']) and _safe(spec['entrypoint']), 'ReadySet execution source contract differs')
    _need({str(Path(spec['library'])/n) for n in OBSERVED_MODULES} <= {p['path'] for p in rows},
        'Incomplete ReadySet observer roots')
    # Historical absolute paths only reconstruct the saved invocation. Frozen
    # inputs above are resolved exclusively through their declared anchors.
    arguments = r['ordinary_arguments']; suffix = '/'+r['heavy_control']['path']
    _need(isinstance(arguments, list) and len(arguments) >= 5
        and all(isinstance(value, str) for value in arguments) and arguments[1].endswith(suffix),
        'ReadySet model argument does not bind to its declared anchor')
    historical = arguments[1][:-len(suffix)]
    _need(Path(historical).is_absolute() and _safe(r['readyset_dispatcher']['path']), 'Invalid historical execution root')
    expected = [str(Path(spec['installation'])/r['readyset_dispatcher']['path']),
        historical+suffix, 'ready_set.actions.hydrogens=False', 'ready_set.actions.ligands=True',
        'ready_set.actions.optimise_ligand_geometry=False',
        *['ready_set.input.cif_file_name='+historical+'/'+r['component_inputs'][c]['path'] for c in b['report']['components']]]
    _need(arguments == expected and spec['arguments'] == expected[1:], 'ReadySet ordered invocation differs')
    classified = classify_subprocesses(trace, sources, root/'source_evidence', Path(spec['installation']), Path(spec['library']))
    _need(classified == r['process_classification'], 'ReadySet process classification does not replay')
    with TemporaryDirectory(prefix='bundle-readyset-read-') as temporary:
        temp = Path(temporary); regenerated = temp/'heavy.pdb'; heavy_control(b['model'], regenerated)
        _need(regenerated.read_bytes() == _read(heavy), 'ReadySet heavy control does not replay')
        selected, checks = effective_cached_input(b['dictionary'], raw, temp/'effective')
        _need(selected is not None and selected.read_bytes() == _read(dictionary), 'Effective ReadySet dictionary does not replay')
    checks.update(unchanged_heavy_sites=_atoms(model) == _atoms(heavy),
        readyset_completed=r['execution']['status'] == 'COMPLETED' and r['execution'].get('returncode') == 0
            and result.get('execution') == 'COMPLETED',
        observer_complete=result.get('observer_retained') is True and trace.get('truncated') is False,
        effective_actions=trace.get('effective_actions') == EXPECTED_ACTIONS,
        no_observed_builder_or_template_calls=trace.get('builder_calls') == trace.get('template_calls') == 0,
        no_unclassified_subprocess_calls=classified['accepted'])
    _need(_bytes(checks) == _bytes(r['checks']) and len(checks) == 8 and all(v is True for v in checks.values())
        and r['status'] == 'READYSET_CACHED_INPUT_PASS', 'ReadySet consumption did not qualify')
    if atom_order_directory is not None:
        from .cif_readyset_atom_order import read_readyset_atom_order
        ordered = read_readyset_atom_order(atom_order_directory)
        _need(_read(ordered['reference']) == _read(b['model'])
            and _read(ordered['candidate']) == _read(model), 'Atom-order evidence belongs to different inputs')
        model = ordered['model']
    modifiers = [p for p in b['after_dictionaries'] if p not in b['component_dictionaries'].values()]
    return dict(model=model, dictionaries=[dictionary, *modifiers], phils=b['after_phils'],
        native_options=b['native_options'], checks=checks)


def inspect_dictionary_bundle_readyset(bundle, baseline_receipt, candidate_receipt,
        readyset_directory, endpoint_receipt=None, *, atom_order_directory=None):
    """Choose diagnostic evidence only after rechecking the final effective bundle.

    Unavailable charge evidence keeps its existing diagnostic-only limitation.
    A damaged starting bundle raises; a failed optional improvement is reported
    and cannot replace the usable start. No file or checkpoint is modified.
    """
    from .cif_attachment_native import _capture
    from .cif_postmr_cached_model import qualify_cached_model_roundtrip
    from .cif_native_monomers import POLICY_ID as monomer_policy, review_full_monomers
    b = read_dictionary_bundle(bundle)
    initial = inspect_dictionary_bundle_native(bundle, baseline_receipt, candidate_receipt)
    usable = initial['diagnostic_continuation']['allowed'] is True
    endpoint = None; error = None; accepted = False; pins = {}
    if usable:
        try:
            inputs = readyset_endpoint_inputs(bundle, readyset_directory, atom_order_directory=atom_order_directory)
            _need(endpoint_receipt is not None, 'Final effective ReadySet native readback is missing')
            before_record, before, before_files = _capture(Path(candidate_receipt), _read(b['model']))
            record, after, after_files = _capture(Path(endpoint_receipt), _read(inputs['model']))
            _bind_capture(before_record, b['report']['consumer'], b['model'], b['after_dictionaries'], b['after_phils'])
            _bind_capture(record, b['report']['consumer'], inputs['model'], inputs['dictionaries'], inputs['phils'])
            _need(record.get('full_monomer_inventory_policy') == monomer_policy, 'Final full-model native evidence missing')
            review_full_monomers(after)
            endpoint = qualify_cached_model_roundtrip(before, after, b['model'], inputs['model'])
            accepted = endpoint['mechanics_checks_pass'] is True
            _need(all(_read(p) == data for p,data in {**before_files,**after_files}.items()), 'Native evidence changed during inspection')
            pins = dict(endpoint_receipt_sha256=sha256(_read(Path(endpoint_receipt))).hexdigest(),
                readyset_receipt_sha256=sha256(_read(Path(readyset_directory)/'readyset_consumption.json')).hexdigest())
            if atom_order_directory is not None:
                repeated = readyset_endpoint_inputs(bundle, readyset_directory, atom_order_directory=atom_order_directory)
                _need(all(_read(p) == data for p,data in after_files.items()), 'Atom-order evidence changed during inspection')
                pins['atom_order_receipt_sha256'] = sha256(_read(Path(atom_order_directory)/'atom_order.json')).hexdigest()
        except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
            error = type(exc).__name__+': '+str(exc); accepted = False
    # Revalidate shared evidence after the optional endpoint inspection.
    _need(read_dictionary_bundle(bundle)['report'] == b['report'], 'Starting bundle changed during inspection')
    _need(sha256(_read(Path(baseline_receipt))).hexdigest() == initial['baseline_receipt_sha256']
        and sha256(_read(Path(candidate_receipt))).hexdigest() == initial['candidate_receipt_sha256'],
        'Starting native receipts changed during inspection')
    return dict(schema_version=1, policy_id=ATOM_ORDER_POLICY_ID if atom_order_directory is not None else POLICY_ID, initial=initial, endpoint=endpoint,
        endpoint_error=error, **pins,
        decision=dict(status='CONTINUE_WITH_NOTES' if usable else 'NO_USABLE_MODEL',
            selected=('readyset_ordered_checked_model' if atom_order_directory is not None else 'readyset_checked_model') if accepted else 'verified_prepared_model' if usable else None,
            scope='SEPARATE_DIAGNOSTIC_PHASE_ONLY', requires_cif_review=False, automatic_adoption=False),
        scientific_qualification='NOT_ASSESSED', native_execution='NOT_RUN', automatic_adoption=False)
