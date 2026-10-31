"""Frozen, opt-in composition of independently qualified component dictionaries.

One model and native context own the ordered bundle. Component/site preparation
continues to use the existing source chemistry adapters; composing evidence never
promotes isolated qualification to whole-model readiness.
"""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_dictionary_store import _bytes, _json, resolve_dictionary_snapshot
from .cif_dictionary_sites import (
    _bind_capture, _consumer, _diagnostic_continuation, _need, _read,
    _site_native_checks, prepare_dictionary_sites, read_dictionary_sites,
)
from .cif_native_context import validate_native_context
from .cif_native_monomers import FULL_MODEL_PHIL
from .ligand_profiles import combine_dictionary_inputs, dictionary_component_codes

POLICY_ID = 'cif-stored-dictionary-bundle-v1'
ANCHOR = 'dictionary_bundle_directory'


def _files(root):
    paths = sorted(root.rglob('*'))
    _need(not any(p.is_symlink() for p in paths), 'Symlinked bundle artifact')
    return [dict(anchor=ANCHOR, path=p.relative_to(root).as_posix(),
        sha256=sha256(_read(p)).hexdigest(), size=p.stat().st_size)
        for p in paths if p.is_file() and p != root/'bundle_receipt.json']


def _context(context):
    result = validate_native_context(context)
    _need(result.get('monomer_inventory') == 'full_model',
        'Composed dictionaries require full-model native evidence')
    return result


def _children(root, controls):
    codes = controls['components']
    _need(isinstance(codes, list) and 2 <= len(codes) <= 16
        and all(isinstance(c, str) and c.isascii() and c.isalnum() and 1 <= len(c) <= 3 for c in codes)
        and codes == sorted(set(codes)), 'Require two to sixteen unique ordered components')
    _consumer(controls['consumer']); _context(controls['native_context'])
    model = _read(root/'inputs/model.pdb')
    children = []; owners = {}; modifiers = set()
    for code in codes:
        child = read_dictionary_sites(root/'components'/code); r = child['report']
        _need(r['component'] == code and _read(child['model']) == model,
            'Component model or ownership differs')
        _need(all(_bytes(r[k]) == _bytes(controls[k]) for k in
            ('consumer', 'native_context', 'expected_links')), 'Component native contract differs')
        _need(r['supplementary_dictionaries'] == r['supplementary_phils'] == [],
            'Component-local supplementary inputs are not part of the shared contract')
        for path in (child['snapshot']['source'], child['snapshot']['dictionary'],
                root/'components'/code/'prepared/base_dictionary.cif'):
            _need(dictionary_component_codes(path) == {code}, 'Dictionary has another component owner')
        for context in r['contexts']:
            site = context['site']
            _need(site not in owners, 'Multiple component owners for one model site')
            owners[site] = code
        for plan in child['preparation']['sites']:
            modifier = plan.get('modification_id')
            if modifier is not None:
                _need(modifier not in modifiers, 'Conflicting site modifier identity')
                modifiers.add(modifier)
        children.append(child)
    return children, owners


def _derive(root, children, destination):
    destination.mkdir()
    combine_dictionary_inputs([c['snapshot']['source'] for c in children], destination/'sources.cif')
    combine_dictionary_inputs([c['after_dictionaries'][0] for c in children], destination/'dictionaries.cif')
    (destination/'native_interpretation.phil').write_text(FULL_MODEL_PHIL)


def _inputs(root, controls, children):
    names = controls['supplementary_phils']
    _need(isinstance(names, list) and names == [f'inputs/phils/{i:03}.phil' for i in range(len(names))],
        'Shared PHIL layout or order differs')
    phils = [root/name for name in names]
    for path in phils: _read(path)
    policy = root/'prepared/native_interpretation.phil'
    # Empty modification placeholders are evidence, not effective definitions.
    active = [c for c in children if any(p.get('modification_id') for p in c['preparation']['sites'])]
    return dict(model=root/'inputs/model.pdb',
        source=root/'prepared/sources.cif', dictionary=root/'prepared/dictionaries.cif',
        before_dictionaries=[c['before_dictionaries'][0] for c in children],
        after_dictionaries=[p for c in children for p in
            (c['after_dictionaries'][:2] if c in active else c['after_dictionaries'][:1])],
        before_phils=[*phils, policy],
        after_phils=[*phils, *(c['after_phils'][0] for c in active), policy],
        component_dictionaries={c['report']['component']:c['after_dictionaries'][0] for c in children},
        native_options=dict(full_monomer_inventory=True),
        preparations=[c['preparation'] for c in children],
        projections={s:p for c in children for s,p in c['projections'].items()})


def _report(root, controls, children, owners):
    return dict(schema_version=1, policy_id=POLICY_ID, status='PREPARED_REVIEW',
        **controls, site_owners=owners,
        contexts=[ctx for c in children for ctx in c['report']['contexts']],
        entries={c['report']['component']:c['report']['entry_id'] for c in children},
        files=_files(root), native_validation='NOT_RUN', scientific_qualification='NOT_ASSESSED',
        automatic_adoption=False, model_editing='NOT_RUN', model_optimization='NOT_RUN')


def prepare_dictionary_bundle(components, model, output, *, consumer, expected_links,
        native_context, supplementary_phils=()):
    """Publish a fresh composition; no native execution or automatic adoption.

    Each component is an explicit snapshot/contexts/optional terminal_resource
    mapping. Every site of each selected code must be declared. Shared PHILs keep
    their caller order; component dictionaries are ordered by code, with active
    modifiers adjacent and the full-model interpretation policy last.
    """
    output = Path(output).absolute()
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    _need(not any(p.is_symlink() for p in output.parents), 'Unsafe bundle destination')
    _need(isinstance(components, (list, tuple)) and 2 <= len(components) <= 16,
        'Require two to sixteen explicit components')
    _consumer(consumer); _context(native_context)
    selected = {}
    for item in components:
        _need(isinstance(item, dict) and {'snapshot', 'contexts'} <= item.keys()
            and item.keys() <= {'snapshot', 'contexts', 'terminal_resource', 'phosphate_atom_policy'}, 'Unknown component request')
        snapshot = Path(item['snapshot']).absolute()
        _need(snapshot != output and snapshot not in output.parents, 'Cannot publish inside a snapshot')
        saved = resolve_dictionary_snapshot(snapshot); code = saved['manifest']['request']['component']
        _need(code not in selected, 'Duplicate component code')
        selected[code] = item
    controls = _json(_bytes(dict(components=sorted(selected), consumer=consumer,
        expected_links=expected_links, native_context=native_context,
        supplementary_phils=[f'inputs/phils/{i:03}.phil' for i in range(len(supplementary_phils))])))
    originals = {Path(p):_read(p) for p in [model, *supplementary_phils]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='dictionary-bundle-', dir=output.parent) as temporary:
        root = Path(temporary)/'bundle'; (root/'inputs').mkdir(parents=True)
        (root/'inputs/model.pdb').write_bytes(originals[Path(model)])
        for name, path in zip(controls['supplementary_phils'], supplementary_phils):
            target = root/name; target.parent.mkdir(exist_ok=True); target.write_bytes(originals[Path(path)])
        for code, item in sorted(selected.items()):
            prepare_dictionary_sites(item['snapshot'], root/'inputs/model.pdb', item['contexts'],
                root/'components'/code, consumer=consumer, expected_links=expected_links,
                native_context=native_context, terminal_resource=item.get('terminal_resource'),
                phosphate_atom_policy=item.get('phosphate_atom_policy'))
        children, owners = _children(root, controls)
        _derive(root, children, root/'prepared')
        report = _report(root, controls, children, owners)
        (root/'bundle_receipt.json').write_bytes(_bytes(report))
        read_dictionary_bundle(root)
        _need(all(_read(p) == data for p,data in originals.items()), 'Input changed during composition')
        root.rename(output)
    return report


def read_dictionary_bundle(output):
    """Reconstruct ownership and generated bytes offline without altering evidence."""
    root = Path(output).absolute(); report = _json(_read(root/'bundle_receipt.json'))
    _need(type(report.get('schema_version')) is int and report['schema_version'] == 1
        and report.get('policy_id') == POLICY_ID, 'Unknown bundle schema/policy')
    _need(report.get('files') == _files(root), 'Bundle artifact inventory or checksum differs')
    controls = {k:report[k] for k in ('components', 'consumer', 'expected_links',
        'native_context', 'supplementary_phils')}
    children, owners = _children(root, controls); inputs = _inputs(root, controls, children)
    allowed = {'inputs/model.pdb', *controls['supplementary_phils']}
    for code, child in zip(controls['components'], children):
        allowed.add(f'components/{code}/site_receipt.json')
        allowed.update(f'components/{code}/'+r['path'] for r in child['report']['files'])
    with TemporaryDirectory(prefix='dictionary-bundle-read-') as temporary:
        replay = Path(temporary)/'prepared'; _derive(root, children, replay)
        for path in replay.iterdir():
            allowed.add('prepared/'+path.name)
            _need(_read(root/'prepared'/path.name) == path.read_bytes(), 'Combined dictionary/policy does not replay')
    _need({r['path'] for r in report['files']} == allowed, 'Unrequested bundle artifact')
    _need(_bytes(report) == _bytes(_report(root, controls, children, owners)),
        'Bundle claim differs from frozen evidence')
    return dict(report=report, **inputs)


def inspect_dictionary_bundle_native(output, baseline_receipt, candidate_receipt):
    """Bind both whole-model captures, then qualify all selected sites together."""
    from .cif_attachment_native import _capture, _native_atoms
    from .cif_native_monomers import POLICY_ID as monomer_policy, review_full_monomers
    from .cif_terminal_qualification import qualify_terminal_bundle
    root = Path(output).absolute(); prepared = read_dictionary_bundle(root)
    report = prepared['report']; model = prepared['model']; captures = []; pins = []; snapshots = {}
    original = _read(root/'bundle_receipt.json')
    for label, path in [('before', baseline_receipt), ('after', candidate_receipt)]:
        path = Path(path); data = _read(path)
        record, native, captured = _capture(path, _read(model)); snapshots.update(captured)
        _bind_capture(record, report['consumer'], model, prepared[label+'_dictionaries'], prepared[label+'_phils'])
        _need(record.get('full_monomer_inventory_policy') == monomer_policy, 'Require maintained full-model capture')
        review_full_monomers(native); _native_atoms(native, _read(model))
        _need(native.get('status') == 'REVIEW' and native.get('fatal_problems') is None
            and native.get('unused_definitions') == native.get('unsupported_fields') == [],
            'Unresolved native failures or unused definitions')
        _need(_read(path) == data, 'Native receipt changed during inspection')
        captures.append(native); pins.append(sha256(data).hexdigest())
    before, after = captures
    _need(before['restraint_policy'] == after['restraint_policy'], 'Native restraint policy changed')
    qualification = qualify_terminal_bundle(before, after, prepared['preparations'],
        [tuple(p) for p in report['expected_links']],
        [c['site'] for c in report['contexts'] if c['five_prime_state'] == 'free_OH'],
        prepared['projections'], native_context=report['native_context'])
    aggregate = dict(report=report, projections=prepared['projections'],
        preparation=dict(sites=[s for p in prepared['preparations'] for s in p['sites']]))
    checks = _site_native_checks(before, after, aggregate)
    passed = qualification['status'] == 'TERMINAL_BUNDLE_MECHANICS_PASS' and all(r['status'] == 'PASS' for r in checks)
    _need(_read(root/'bundle_receipt.json') == original and _files(root) == report['files']
        and all(_read(p) == data for p,data in snapshots.items()), 'Evidence changed during bundle inspection')
    return dict(schema_version=1, policy_id=POLICY_ID,
        status='STORED_BUNDLE_NATIVE_MECHANICS_PASS' if passed else 'REVIEW',
        native_context=report['native_context'], native_checks=checks, qualification=qualification,
        diagnostic_continuation=_diagnostic_continuation(qualification, checks),
        preparation_sha256=sha256(original).hexdigest(), baseline_receipt_sha256=pins[0],
        candidate_receipt_sha256=pins[1], exact_capture_binding=True, native_execution='NOT_RUN',
        consumer_binding='CAPTURED_IMPLEMENTATION; LIVE_INSTALLATION_NOT_CHECKED',
        source_protonation='NOT_ASSESSED', scientific_qualification='NOT_ASSESSED', automatic_adoption=False)
