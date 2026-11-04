"""Native readback of immutable ordinary Coot construction controls.

Reuse the qualified source-graph site-modifier preparation and native inventory
worker. These controls connect actual construction to effective restraints;
they do not run ReadySet, optimize or create a production checkpoint.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import combinations
import json
import math
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .cif_candidate_usability import energy_inventory_checks
from .cif_construction_provenance import _pdb_inventory
from .cif_effective_source_recovery import mechanics_can_continue
from .cif_fixed_geometry import _fixed_policy
from .cif_fragment_restoration import _model
from .cif_linked_control import _heavy_proxy_checks
from .cif_linked_preparation import prepare_linked_component, component_values, atom_rows, _prune, _render
from .cif_linked_qualification import _site, native_backbone_links, site_definition_checks
from .cif_terminal_qualification import definition_projection_checks, _proxy_subset, PROXY_COMPARISON_POLICY

POLICY_ID = 'cif-ordinary-construction-native-readback-v1'
SCOPE = 'SEPARATE_CONSTRUCTED_MODEL_NATIVE_READBACK'
NATIVE_KINDS = {'bond_simple', 'bond_asu', 'angle', 'dihedral', 'const_dihedral',
    'chirality', 'planarity', 'parallelity'}
ORDINARY_CONSTRUCTION_CONTEXTS = {
    'DP': {'site': 'A:6', 'incoming_site': 'A:5', 'outgoing_site': 'A:7',
        'five_prime_state': 'linked', 'three_prime_state': 'linked'},
    '5PC': {'site': 'A:7', 'incoming_site': 'A:6', 'outgoing_site': 'A:8',
        'five_prime_state': 'linked', 'three_prime_state': 'linked'},
    'PDU': {'site': 'A:9', 'incoming_site': 'A:8', 'outgoing_site': 'A:10',
        'five_prime_state': 'linked', 'three_prime_state': 'linked'},
}
SAVED_POLICY_ID = 'cif-saved-constructed-native-replay-v1'


def _preparation_replays(recorded, recomputed, path=()):
    """Only derived finding eigenvalues/determinants admit machine roundoff.

    Source/target values, findings, rules and every other field remain exact.
    This does not apply to CIF/PHIL/model bytes or native proxy comparisons.
    """
    if type(recorded) is not type(recomputed): return False
    if isinstance(recorded, dict):
        return set(recorded) == set(recomputed) and all(
            _preparation_replays(v, recomputed[k], path + (k,)) for k, v in recorded.items())
    if isinstance(recorded, list):
        return len(recorded) == len(recomputed) and all(
            _preparation_replays(v, w, path + (i,)) for i, (v, w) in enumerate(zip(recorded, recomputed)))
    derived = ('findings' in path and (path[-2:] == ('measurements', 'determinant')
        or len(path) >= 3 and path[-3:-1] == ('measurements', 'eigenvalues') and type(path[-1]) is int))
    if type(recorded) is float and derived:
        return math.isfinite(recorded) and math.isfinite(recomputed) and math.isclose(recorded, recomputed, rel_tol=1e-12, abs_tol=1e-12)
    return recorded == recomputed


def _saved_artifact(members, prefix, ref, anchor):
    from .cif_scaffold_return import _need, _safe
    _need(ref.get('anchor') == anchor and _safe(ref.get('path')), 'Unsafe saved construction native artifact')
    data = members[prefix + ref['path']]
    _need(type(data) is bytes and len(data) == ref['size'] and sha256(data).hexdigest() == ref['sha256'],
        'Saved construction native artifact bytes differ')
    return data


def _saved_native_capture(members, record, expected_inputs, *, installed_only):
    """Bind a completed capture to exact maintained worker/spec/input bytes.

    Historical paths are provenance only. Captured Python is compared as text,
    never imported or executed; all operational paths use declared anchors.
    """
    from .cif_scaffold_return import _json, _need, _safe
    from .cif_native_validation import _NATIVE_WORKER, NATIVE_POLICY_ID
    from .cif_candidate_usability import native_energy_worker
    directory = record['directory']
    _need(directory.get('anchor') == 'probe_directory' and _safe(directory.get('path')),
        'Unsafe saved native capture directory')
    prefix = directory['path'] + '/'
    _need(_json(members, prefix + 'native_receipt.json') == {k: v for k, v in record.items() if k != 'directory'},
        'Saved native receipt differs from its embedded capture')
    _need(record.get('status') == 'REVIEW' and record.get('policy_id') == NATIVE_POLICY_ID
        and record.get('phenix_version') == '2.2.1' and record.get('execution', {}).get('status') == 'COMPLETED'
        and record['execution'].get('returncode') == 0 and record['execution'].get('timeout_seconds') == 60
        and record.get('source_preserved') is True and record.get('frozen_inputs_preserved') is True
        and record.get('symlink_outputs') == [] and record.get('automatic_adoption') is False
        and all(record.get(k) == 'NOT_RUN' for k in ['model_editing', 'optimization', 'readyset_retry', 'scientific_approval'])
        and record.get('phil_namespace_policy') == 'refinement-root-to-interpreter-v1'
        and record.get('dictionary_source_policy') == ('INSTALLED_LIBRARY_ONLY' if installed_only else 'EXPLICIT_DICTIONARIES'),
        'Incomplete or changed saved native construction execution')
    inputs = record['inputs']; outputs = record['outputs']
    _need(len(inputs) == len(expected_inputs) and record['input_integrity'] == [
        {'input_index': i, 'source_preserved': True, 'snapshot_preserved': True} for i in range(len(inputs))],
        'Saved native input integrity differs')
    for index, (ref, (role, data)) in enumerate(zip(inputs, expected_inputs)):
        _need(ref.get('input_index') == index and ref.get('role') == role
            and _saved_artifact(members, prefix, ref, 'native_directory') == data,
            'Saved native input role/order/bytes differ')
    for ref in outputs: _saved_artifact(members, prefix, ref, 'native_directory')
    _need(len({r['path'] for r in outputs}) == len(outputs)
        and {prefix + r['path'] for r in outputs} | {prefix + 'native_receipt.json'}
            == {n for n in members if n.startswith(prefix)}, 'Saved native output inventory differs')
    spec = {'policy_id': NATIVE_POLICY_ID, 'model': inputs[0]['path'],
        'dictionaries': [r['path'] for r in inputs if r['role'] == 'dictionary'],
        'phil_files': [r['path'] for r in inputs if r['role'] == 'phil'],
        'phil_namespace_policy': 'refinement-root-to-interpreter-v1', 'inventory_detail': 'linked',
        'policy_inventory': True, 'energy_inventory': True}
    if installed_only: spec['installed_library_only'] = True
    _need(_json(members, prefix + 'native_spec.json') == spec
        and members[prefix + 'native_worker.py'] == native_energy_worker(_NATIVE_WORKER).encode()
        and _json(members, prefix + 'native_validation.json') == record['native_validation'],
        'Saved native worker, specification or result differs')
    return record['native_validation']


def replay_constructed_native(members, resources, output):
    """Reprepare and requalify saved construction readback with current code.

    The caller verifies the exact capsule/parent and resolves resources through
    its declared C63-to-C57 lineage. This adapter checks every prepared artifact,
    native worker/input/result and implementation fingerprint. It runs no native
    process, changes no chemical definition and preserves the original verdict.
    """
    from .cif_scaffold_return import _json, _need, _safe
    from pathlib import PurePosixPath
    receipt = _json(members, 'probe_receipt.json'); saved = receipt['construction_native_audit']
    _need(saved == _json(members, 'construction_native_audit.json') and saved.get('policy_id') == POLICY_ID
        and saved.get('scope') == SCOPE and saved.get('native_execution') == 'ORDINARY_CONSTRUCTION_NATIVE_READBACK'
        and saved.get('automatic_adoption') is False and saved.get('requires_cif_review') is False
        and saved.get('mtz_used') is False and saved.get('scientific_geometry_qualification') == 'NOT_ASSESSED'
        and saved.get('energy_comparison_between_models') == 'NOT_COMPARABLE_DIFFERENT_OBJECTIVES'
        and all(saved.get(k) == 'NOT_RUN' for k in ['coot_execution', 'readyset_execution', 'dictionary_generation',
            'model_optimization', 'policy_recompilation', 'refinement']), 'Saved native construction scope differs')
    directory = saved['directory']
    _need(directory.get('anchor') == 'probe_directory' and _safe(directory.get('path')),
        'Unsafe saved construction preparation directory')
    prefix = directory['path'] + '/'; prep = saved['preparation']; refs = prep['outputs']
    _need(prep == _json(members, prefix + 'preparation.json'), 'Saved native preparation receipt differs')
    original = _saved_artifact(members, prefix, refs['reference'], 'construction_native_directory')
    model = _saved_artifact(members, prefix, refs['model'], 'construction_native_directory')
    parent = _json(members, 'inputs/review/probe_receipt.json')['postmr_construction_audit']
    for data, ref in [(original, parent['input_model']), (model, parent['outputs']['model'])]:
        _need(_saved_artifact(members, 'inputs/review/postmr_construction/', ref, 'construction_directory') == data,
            'Saved native model differs from the proved ordinary construction')
    output = Path(output)
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    if any(p.is_symlink() for p in output.parents): raise ValueError('Output parent cannot traverse a symlink')
    output.mkdir(parents=True); inputs = output / 'inputs'; inputs.mkdir()
    reference_path = inputs / 'reference.pdb'; reference_path.write_bytes(original)
    model_path = inputs / 'constructed.pdb'; model_path.write_bytes(model)
    folder = output / 'prepared'; preparation = prepare_constructed_native(reference_path, model_path, resources, folder)
    _need(_preparation_replays(prep, preparation), 'Saved source-qualified preparation does not reproduce')
    for path in folder.rglob('*'):
        if path.is_file():
            name = prefix + path.relative_to(folder).as_posix()
            if path.name in {'preparation.json', 'preparation_receipt.json'}:
                same = _preparation_replays(_json(members, name), json.loads(path.read_bytes()))
            else: same = members[name] == path.read_bytes()
            _need(same, 'Saved prepared construction resource does not reproduce: ' + name)
    def artifact(ref): return _saved_artifact(members, prefix, ref, 'construction_native_directory')
    policy = artifact(refs['phils'][0])
    before = _saved_native_capture(members, saved['canonical_reference'], [('model', original), ('phil', policy)], installed_only=True)
    after = _saved_native_capture(members, saved['constructed_model'], [('model', model)]
        + [('dictionary', artifact(r)) for r in refs['dictionaries']]
        + [('phil', artifact(r)) for r in refs['phils']], installed_only=False)
    captures = [saved['canonical_reference'], saved['constructed_model']]
    _need(captures[0]['executable_sha256'] == captures[1]['executable_sha256']
        and captures[0]['executable_provenance'] == captures[1]['executable_provenance']
        and before['installed_api_sources'] == after['installed_api_sources'], 'Saved native implementations differ')
    energy_sources = saved['energy_sources']
    _need(len(energy_sources) == 3, 'Incomplete saved native energy source proof')
    for pin in energy_sources:
        data = _saved_artifact(members, 'inputs/review/', pin['snapshot'], 'input_capsule')
        _need(sha256(data).hexdigest() == pin['sha256'], 'Saved native energy source snapshot differs')
    for capture, native in zip(captures, [before, after]):
        root = PurePosixPath(capture['executable_provenance']).parent.parent
        _need([{'anchor': 'phenix_installation', 'path': PurePosixPath(r['historical_path']).relative_to(root).as_posix(),
            'sha256': r['sha256']} for r in native['installed_api_sources']] == receipt['installed_api_sources'],
            'Saved native API implementation binding differs')
        proof = native['energy_inventory']['installed_sources']
        _need([(PurePosixPath(r['historical_path']).relative_to(root).as_posix(), r['sha256']) for r in proof]
            == [(r['path'], r['sha256']) for r in energy_sources], 'Saved native energy implementations differ')
    entries = [{'component': code, 'context': context, 'preparation': preparation['preparations'][code],
        'projected': folder / refs['projections'][context['site']]['path']}
        for code, item in resources.items() for context in item['contexts']]
    qualification = qualify_constructed_native(before, after, reference_path, model_path, entries)
    return {'schema_version': 1, 'policy_id': SAVED_POLICY_ID, 'scope': 'SAVED_ORDINARY_CONSTRUCTION_NATIVE_READBACK',
        'status': qualification['status'], 'qualification': qualification,
        'preparation': preparation, 'original_qualification_status': saved['qualification']['status'],
        'original_review_checks': [r['check'] for r in saved['qualification']['checks'] if r['status'] == 'REVIEW'],
        'original_evidence': {'anchor': 'input_capsule', 'path': 'construction_native_audit.json',
            'sha256': sha256(members['construction_native_audit.json']).hexdigest(), 'size': len(members['construction_native_audit.json'])},
        'native_evidence': 'PRESERVED_PHENIX_2.2.1-6174_CAPTURE', 'new_native_calls': 0,
        'preparation_measurement_comparison': 'DERIVED_FINDING_EIGENVALUES_DETERMINANTS_ONLY_1e-12; ALL_OTHER_FIELDS_EXACT',
        'source_inputs_preserved': True, 'native_execution': 'NOT_RUN', 'captured_code_execution': 'NOT_RUN',
        'model_editing': 'EXACT_CONSTRUCTED_MODEL_COPY', 'model_optimization': 'NOT_RUN',
        'dictionary_generation': 'NOT_RUN', 'coot_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
        'refinement': 'NOT_RUN', 'policy_recompilation': 'NOT_RUN', 'policy_authority': 'NARestraints',
        'energy_comparison_between_models': 'NOT_COMPARABLE_DIFFERENT_OBJECTIVES', 'production_checkpoint': 'NOT_CREATED',
        'scientific_geometry_qualification': 'NOT_ASSESSED', 'automatic_adoption': False, 'requires_cif_review': False}


def _artifact(path, root):
    data = path.read_bytes()
    return {'anchor': 'construction_native_directory', 'path': path.relative_to(root).as_posix(),
        'sha256': sha256(data).hexdigest(), 'size': len(data)}


def prepare_constructed_native(reference_model, model, resources, output):
    """Stage exact models and source-qualified site resources at explicit contexts.

    Each resource supplies source/numerical paths, independently bound native
    qualification and complete contexts for its component. No atom position,
    numerical target, context or chemical state is inferred or optimized here.
    """
    reference_model, model, output = map(Path, (reference_model, model, output))
    if not resources:
        raise ValueError('Require explicit source-qualified construction resources')
    if any(not re.fullmatch(r'[A-Za-z0-9]{1,3}', code) for code in resources):
        raise ValueError('Unsupported construction resource component code')
    inputs = [reference_model, model]
    for item in resources.values(): inputs.extend([Path(item['source']), Path(item['numerical'])])
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    if any(p.is_symlink() for p in output.parents): raise ValueError('Output parent cannot traverse a symlink')
    if any(p.parent.resolve() == output.resolve() or p.parent.resolve() in output.resolve().parents for p in inputs):
        raise ValueError('Native controls must be separate from every input directory')
    snapshots = {p: p.read_bytes() for p in inputs}
    before, after = _pdb_inventory(reference_model), _pdb_inventory(model)
    selected = [c['site'] for row in resources.values() for c in row['contexts']]
    if not selected or len(selected) != len(set(selected)):
        raise ValueError('Require unique explicit constructed sites')
    unselected = lambda inventory: {k: v for k, v in inventory.items() if k[0] + ':' + k[1] + k[2] not in selected}
    if unselected(before) != unselected(after): raise ValueError('Construction changed an unselected atom or coordinate')
    output.mkdir(parents=True); staged = output / 'inputs'; staged.mkdir()
    ref = staged / 'reference.pdb'; ref.write_bytes(snapshots[reference_model])
    candidate = staged / 'constructed.pdb'; candidate.write_bytes(snapshots[model])
    policy = staged / 'native_policy.phil'
    policy.write_text('refinement {\n pdb_interpretation.secondary_structure {\n  enabled = False\n }\n}\n')
    preparations = {}; dictionaries = []; phils = [policy]; projections = {}
    for code, item in sorted(resources.items()):
        folder = output / 'preparations' / code
        preparation = prepare_linked_component(Path(item['source']), Path(item['numerical']), candidate,
            item['contexts'], folder, code=code, native_qualification=item['qualification'])
        preparations[code] = preparation
        dictionaries.extend(folder / preparation['outputs'][k]['path'] for k in ['dictionary', 'modifications'])
        phils.append(folder / preparation['outputs']['parameters']['path'])
        for context in item['contexts']:
            site = context['site']
            projections[site] = folder / ('projected_' + site.replace(':', '_') + '.cif')
    if any(p.read_bytes() != data for p, data in snapshots.items()): raise ValueError('Construction native preparation changed an input')
    report = {'schema_version': 1, 'policy_id': POLICY_ID, 'scope': SCOPE, 'status': 'PREPARED',
        'source_inputs_preserved': True, 'models_preserved': True, 'contexts': {
            code: item['contexts'] for code, item in sorted(resources.items())}, 'preparations': preparations,
        'source_hashes': {code: {'source': sha256(snapshots[Path(v['source'])]).hexdigest(),
            'numerical': sha256(snapshots[Path(v['numerical'])]).hexdigest()} for code, v in resources.items()},
        'outputs': {'reference': _artifact(ref, output), 'model': _artifact(candidate, output),
            'dictionaries': [_artifact(p, output) for p in dictionaries], 'phils': [_artifact(p, output) for p in phils],
            'projections': {s: _artifact(p, output) for s, p in projections.items()}},
        'native_execution': 'NOT_RUN', 'model_editing': 'EXACT_CONSTRUCTED_MODEL_COPY',
        'dictionary_generation': 'NOT_RUN', 'model_optimization': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
        'policy_recompilation': 'NOT_RUN', 'policy_authority': 'NARestraints',
        'scientific_geometry_qualification': 'NOT_ASSESSED', 'automatic_adoption': False, 'requires_cif_review': False}
    (output / 'preparation.json').write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return report


def _triple_readback(projected, code, native, site):
    """Restrict the native view and declared graph to the same heavy-atom site."""
    from .cif_triple_bond_audit import audit_triple_bonds
    values = component_values(projected, code)
    hydrogens = {n for n, a in atom_rows(values).items() if a['type_symbol'].upper() in {'H', 'D'}}
    with TemporaryDirectory(prefix='nasolve-constructed-triples-') as temporary:
        reference = Path(temporary).resolve() / 'heavy.cif'
        reference.write_text(_render(_prune(values, hydrogens, outgoing=False), code))
        atoms = [a for a in native['atoms'] if _site(a) == site]; indices = {a['i_seq'] for a in atoms}
        view = {'atoms': atoms, 'monomer_mappings': {'rows': [r for r in native['monomer_mappings']['rows'] if r['site'] == site]},
            'geometry': {'proxy_details': {k: [r for r in rows if set(r['i_seqs']) <= indices]
                for k, rows in native['geometry']['proxy_details'].items()}}}
        report = audit_triple_bonds(reference, code, native=view)
    report.update(projected_dictionary_sha256=sha256(Path(projected).read_bytes()).hexdigest(),
        reference_scope='DECLARED_HEAVY_ATOM_PROJECTION_AT_EXPLICIT_SITE', site=site)
    return report


def qualify_constructed_native(reference, native, reference_model, model, entries):
    """Require fixed native linkage/definitions at exact constructed coordinates.

    The reference is canonical and has a different objective. Its energy is
    never ranked against the constructed model. Residual geometry, retained
    linear-axis torsions and nonconvergence remain developer/solution notes.
    """
    checks = []; triples = {}
    def check(name, passes, **evidence):
        checks.append({'check': name, 'status': 'PASS' if passes else 'REVIEW', **evidence})
    try:
        selected = {r['context']['site'] for r in entries}
        if not selected or len(selected) != len(entries): raise ValueError('Require unique explicit constructed contexts')
        _model(reference, Path(reference_model), coordinates_match=True)
        _model(native, Path(model), coordinates_match=True)
        check('exact-frozen-models', True)
        for label, record in [('reference', reference), ('constructed', native)]:
            check(label + ':native-interpreter', record.get('status') == 'REVIEW' and record.get('inventory_detail') == 'linked'
                and record.get('fatal_problems') is None and record.get('unused_definitions') == [] and record.get('unsupported_fields') == [])
            atoms, points = record['atoms'], record['geometry']['sites_cart_exact']
            check(label + ':native-coordinate-roundtrip', len(points) == len(atoms) and all(len(p) == len(a['xyz']) == 3
                and all(type(x) in (int, float) and math.isfinite(x) and abs(x-y) <= 1e-12 for x, y in zip(p, a['xyz']))
                for p, a in zip(points, atoms)))
            for name, ok in energy_inventory_checks(record).items(): check(label + ':' + name, ok)
            details = record['geometry']['proxy_details']
            check(label + ':complete-proxy-inventory', set(details) == NATIVE_KINDS
                and all(isinstance(rows, list) and record['geometry']['proxy_counts'].get(k) == len(rows) for k, rows in details.items()))
        check('native-secondary-structure-disabled', _fixed_policy(reference) and _fixed_policy(native))
        check('no-pairing-or-stacking-guess', not reference['geometry'].get('custom_proxy_requests')
            and not native['geometry'].get('custom_proxy_requests') and not native['geometry']['proxy_details']['parallelity'])
        before_links, links = native_backbone_links(reference), native_backbone_links(native)
        declared = {(r['context']['incoming_site'], r['context']['site']) for r in entries}
        declared |= {(r['context']['site'], r['context']['outgoing_site']) for r in entries}
        check('all-canonical-backbone-links-preserved', links == before_links and declared <= set(links),
            canonical_links=len(before_links), constructed_links=len(links), declared_selected_links=len(declared))
        old_rows, rows = reference['monomer_mappings']['rows'], native['monomer_mappings']['rows']
        old, mappings = {r['site']: r for r in old_rows}, {r['site']: r for r in rows}
        check('complete-heavy-monomer-sites', len(old) == len(old_rows) and len(mappings) == len(rows) and set(old) == set(mappings)
            and all(r.get(k, {}).get('status') == 'RECORDED' and r[k]['atom_ids'] == []
                for r in rows for k in ['missing_non_hydrogen_atoms', 'unexpected_atoms']))
        check('unchanged-unselected-definitions', {s: r['metadata']['effective_definition'] for s, r in old.items() if s not in selected}
            == {s: r['metadata']['effective_definition'] for s, r in mappings.items() if s not in selected})
        for kind in sorted(NATIVE_KINDS):
            left, right = _proxy_subset(reference, selected, kind), _proxy_subset(native, selected, kind)
            check('unaffected-native-proxies:' + kind, left == right,
                reference_rows=sum(left.values()), constructed_rows=sum(right.values()),
                missing_or_changed_rows=sum((left-right).values()), extra_or_changed_rows=sum((right-left).values()))
        for entry in entries:
            code, context, prep, projected = (entry[k] for k in ['component', 'context', 'preparation', 'projected'])
            site = context['site']; mapping = mappings[site]
            plans = [p for p in prep['sites'] if p['site'] == site]
            if len(plans) != 1: raise ValueError('Missing or ambiguous prepared construction context')
            plan = plans[0]
            check('exact-component:' + site, mapping['resname'].strip() == code)
            check('native-dna-metadata:' + site, mapping['metadata'].get('group') == 'DNA'
                and mapping['metadata'].get('classification') == {'status': 'RECORDED', 'value': 'DNA'})
            checks.extend(site_definition_checks(native, [{'sites': [plan]}]))
            checks.extend(definition_projection_checks(native, {site: (Path(projected), code)}))
            check('exact-site-modifier:' + site, mapping.get('chem_mod_ids') == {'status': 'RECORDED',
                'ids': [plan['modification_id']] if plan.get('modification_id') else []})
            check('no-deleted-coordinate-atoms:' + site, not any(a['atom_id'] in plan['deleted_atoms'] and _site(a) == site for a in native['atoms']))
            for name, ok in _heavy_proxy_checks(native, projected, code, site).items(): check(name + ':' + site, ok)
            atoms = {a['i_seq']: a for a in native['atoms']}
            p = next(i for i, a in atoms.items() if _site(a) == site and a['atom_id'] == 'P')
            ns = {next(i for i in r['i_seqs'] if i != p) for r in native['geometry']['proxy_details']['bond_simple'] if p in r['i_seqs']}
            angles = {min(tuple(r['i_seqs']), tuple(r['i_seqs'])[::-1]) for r in native['geometry']['proxy_details']['angle']}
            expected = {(context['incoming_site'], "O3'"), (site, "O5'"), (site, 'OP1'), (site, 'OP2')}
            check('linked-phosphate-tetrahedral-coverage:' + site, {(_site(atoms[i]), atoms[i]['atom_id']) for i in ns} == expected
                and all(min((a, p, b), (b, p, a)) in angles for a, b in combinations(ns, 2)))
            triples[site] = _triple_readback(projected, code, native, site)
            check('active-triple-targets:' + site, not triples[site]['triple_bonds'] or triples[site]['target_screen'] == 'PASS')
        finite = True
        for kind, rows in native['geometry']['proxy_details'].items():
            for row in rows:
                weights = row.get('weights', [row.get('weight')])
                finite &= all(type(w) in (int, float) and math.isfinite(w)
                    and (w > 0 or kind == 'const_dihedral' and w == 0 and row.get('periodicity') == 0) for w in weights)
                fields = [] if kind == 'planarity' else ['distance_ideal'] if kind in {'bond_simple', 'bond_asu'} else ['angle_ideal'] if kind in {'angle', 'dihedral', 'const_dihedral'} else ['volume_ideal'] if kind == 'chirality' else ['target_angle_deg']
                finite &= all(type(row.get(f)) in (int, float) and math.isfinite(row[f]) for f in fields)
        check('finite-positive-active-proxy-parameters', finite)
    except (KeyError, TypeError, ValueError, OSError, IndexError, StopIteration, ZeroDivisionError, OverflowError) as exc:
        check('complete-constructed-native-evidence', False, error=type(exc).__name__ + ': ' + str(exc))
    result = {'schema_version': 1, 'policy_id': POLICY_ID, 'scope': SCOPE, 'checks': checks,
        'unaffected_proxy_comparison': PROXY_COMPARISON_POLICY,
        'triple_readback': triples, 'scientific_geometry_qualification': 'NOT_ASSESSED',
        'formal_charge_readback': 'UNSUPPORTED_UNLESS_RECORDED', 'nonbonded_pair_identity': 'NOT_ASSESSED',
        'model_optimization': 'NOT_RUN', 'policy_authority': 'NARestraints', 'policy_recompilation': 'NOT_RUN',
        'requires_cif_review': False, 'automatic_adoption': False}
    result['mechanics_checks_pass'] = mechanics_can_continue(result)
    result['status'] = 'CONSTRUCTED_NATIVE_MECHANICS_PASS' if result['mechanics_checks_pass'] else 'REVIEW'
    return result
