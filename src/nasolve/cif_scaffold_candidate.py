"""Separate source-qualified full-bundle candidates with an unchanged model.

The caller supplies the frozen manager, every input and explicit site contexts.
Only owned component/modifier resources are replaced. Native qualification and
the automatic decision are separate from production file adoption.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from itertools import combinations
import json
import math
from pathlib import Path, PurePosixPath
import re

from .cif_candidate_usability import energy_inventory_checks
from .cif_effective_source_recovery import mechanics_can_continue
from .cif_fixed_geometry import _fixed_policy
from .cif_fragment_restoration import _model
from .cif_linked_control import _heavy_proxy_checks
from .cif_linked_preparation import prepare_linked_component
from .cif_linked_qualification import _site, native_backbone_links, site_definition_checks, proxy_signature
from .cif_na_policy import _parse, _path
from .cif_terminal_qualification import definition_projection_checks, _proxy_subset
from .ligand_profiles import _blocks, dictionary_component_codes

POLICY_ID = 'cif-qualified-scaffold-candidate-v1'
SCOPE = 'SEPARATE_FULL_SCAFFOLD_CANDIDATE'


def _artifact(path, root):
    data = path.read_bytes()
    return {'path': path.relative_to(root).as_posix(), 'sha256': sha256(data).hexdigest(), 'size': len(data)}


def _selection(value):
    match = re.fullmatch(r"chain\s+(['\"])([A-Za-z0-9_]?)\1\s+and\s+resid\s+(-?\d+)\s+and\s+resname\s+([A-Za-z0-9]{1,3})", value)
    if not match:
        raise ValueError('Unsupported modification selector; explicit chain/residue/component required')
    return (match[2] or '_') + ':' + match[3], match[4]


def _strip_requests(path, selected, old_ids):
    """Remove exact whole blocks; retain every other byte and declaration."""
    data = path.read_bytes()
    text = data.decode('utf-8')
    if 'apply_cif_modification' not in text:
        return data, [], set()
    nodes, lines = _parse(text)
    removed, spans, retained = [], [], set()
    for node in nodes:
        if _path(node) != 'pdb_interpretation.apply_cif_modification':
            continue
        if node['children'] or set(node['fields']) != {'data_mod', 'residue_selection'}:
            raise ValueError('Unsupported modification request fields')
        site, code = _selection(node['fields']['residue_selection'])
        identifier = node['fields']['data_mod']
        if not re.fullmatch(r'[A-Za-z0-9_]+', identifier):
            raise ValueError('Unsupported native modification identifier')
        if site in selected:
            if selected[site] != code or identifier not in old_ids[site]:
                raise ValueError('Selected request does not match captured component/modifier ownership')
            spans.append((node['start'], node['end']))
            removed.append({'site': site, 'component': code, 'modification_id': identifier})
        else:
            retained.add(identifier)
    delete = {i for start, end in spans for i in range(start, end)}
    return ''.join(line for i, line in enumerate(lines) if i not in delete).encode('utf-8'), removed, retained


def prepare_scaffold_candidate(source, numerical, model, dictionaries, phils, baseline, contexts, output,
                               *, code, native_qualification):
    """Write a separate complete resource bundle; preserve all model bytes.

    No context, component ownership or end state is inferred from proximity.
    Shared modification definitions remain when any unselected request uses them.
    Mixed component dictionaries and ambiguous selectors require a wider adapter.
    """
    source, numerical, model, output = map(Path, (source, numerical, model, output))
    dictionaries, phils = list(map(Path, dictionaries)), list(map(Path, phils))
    paths = [source, numerical, model, *dictionaries, *phils]
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if any(p.is_symlink() for p in output.parents):
        raise ValueError('Output parent cannot traverse a symlink')
    if any(p.parent.resolve() == output.resolve() or p.parent.resolve() in output.resolve().parents for p in paths):
        raise ValueError('Candidate output must be outside preserved input directories')
    if (not dictionaries or not phils or len({p.resolve() for p in dictionaries}) != len(dictionaries)
            or len({p.resolve() for p in phils}) != len(phils)):
        raise ValueError('Require unique complete dictionary and parameter resources')
    snapshots = [p.read_bytes() for p in paths]
    _model(baseline, model, coordinates_match=True)
    mapping_rows = baseline['monomer_mappings']['rows']
    mappings = {row['site']: row for row in mapping_rows}
    if len(mappings) != len(mapping_rows):
        raise ValueError('Captured monomer mapping is ambiguous')
    contexts = list(contexts)
    selected = {c['site']: code for c in contexts}
    if (not contexts or len(selected) != len(contexts)
            or set(selected) != {s for s, row in mappings.items() if row['resname'].strip() == code}):
        raise ValueError('Explicit contexts must cover every site sharing the selected component')
    links = native_backbone_links(baseline)
    for context in contexts:
        site = context['site']
        incoming = [a for a, b in links if b == site]
        outgoing = [b for a, b in links if a == site]
        if incoming != ([context['incoming_site']] if context.get('incoming_site') else []) or outgoing != ([context['outgoing_site']] if context.get('outgoing_site') else []):
            raise ValueError('Explicit candidate context differs from captured backbone links')
    old_ids = {}
    for site in selected:
        captured = mappings[site].get('chem_mod_ids', {})
        if captured.get('status') != 'RECORDED' or len(captured.get('ids', [])) != len(set(captured.get('ids', []))):
            raise ValueError('Captured selected modification inventory unavailable')
        old_ids[site] = set(captured['ids'])
    codes = [dictionary_component_codes(path) for path in dictionaries]
    owned = [i for i, inventory in enumerate(codes) if code in inventory]
    if len(owned) != 1 or codes[owned[0]] != {code}:
        raise ValueError('Require one independent original dictionary for the selected component')
    rewritten, removed, retained = [], [], set()
    for i, path in enumerate(phils):
        data, requests, in_use = _strip_requests(path, selected, old_ids)
        rewritten.append(data)
        removed.extend({**row, 'input_index': i} for row in requests)
        retained.update(in_use)
    expected = Counter((site, identifier) for site, ids in old_ids.items() for identifier in ids)
    actual = Counter((row['site'], row['modification_id']) for row in removed)
    if actual != expected:
        raise ValueError('Every selected captured modification needs one exact owned request')
    obsolete_ids = set().union(*old_ids.values()) - retained
    obsolete = []
    for i, path in enumerate(dictionaries):
        if codes[i]:
            continue
        blocks = _blocks(path)
        ids = {str(block.values.get('data_', '')).removeprefix('mod_') for block in blocks}
        # Remove only whole exclusively owned files. Mixed definitions remain
        # byte-identical and harmlessly available for their unselected callers.
        if blocks and all(str(b.values.get('data_', '')).startswith('mod_') for b in blocks) and ids <= obsolete_ids:
            obsolete.append(i)
    output.mkdir(parents=True)
    prepared_dir = output / 'prepared'
    preparation = prepare_linked_component(source, numerical, model, contexts, prepared_dir,
                                           code=code, native_qualification=native_qualification)
    written_dictionaries, written_phils = [], []
    resources = output / 'resources'; resources.mkdir()
    for i, path in enumerate(dictionaries):
        if i == owned[0] or i in obsolete:
            continue
        target = resources / f'{i:03d}_dictionary.cif'; target.write_bytes(path.read_bytes())
        written_dictionaries.append(_artifact(target, output))
    for key in ['dictionary', 'modifications']:
        written_dictionaries.append(_artifact(prepared_dir / preparation['outputs'][key]['path'], output))
    for i, data in enumerate(rewritten):
        target = resources / f'{i:03d}_phil.phil'; target.write_bytes(data)
        written_phils.append(_artifact(target, output))
    written_phils.append(_artifact(prepared_dir / preparation['outputs']['parameters']['path'], output))
    target_model = output / 'model.pdb'; target_model.write_bytes(model.read_bytes())
    if snapshots != [p.read_bytes() for p in paths]:
        raise ValueError('Preserved candidate inputs changed')
    result = {'schema_version': 1, 'policy_id': POLICY_ID, 'component': code, 'scope': SCOPE,
        'status': 'PREPARED_REVIEW', 'changed_sites': sorted(selected), 'preparation': preparation,
        'preparation_directory': 'prepared', 'selected_original_dictionary': owned[0],
        'removed_modifier_requests': removed,
        'removed_obsolete_modification_files': [{'input_index': i, 'sha256': sha256(dictionaries[i].read_bytes()).hexdigest()} for i in obsolete],
        'inputs': [{'role': role, 'input_index': i, 'name': p.name, 'sha256': sha256(data).hexdigest(), 'size': len(data)}
                   for i, (role, p, data) in enumerate(zip(['source', 'numerical', 'model'] + ['dictionary'] * len(dictionaries) + ['phil'] * len(phils), paths, snapshots))],
        'outputs': {'model': _artifact(target_model, output), 'dictionaries': written_dictionaries, 'phils': written_phils,
            'projections': {site: _artifact(prepared_dir / ('projected_' + site.replace(':', '_') + '.cif'), output) for site in selected}},
        'model_bytes_preserved': True, 'source_preserved': True, 'model_optimization': 'NOT_RUN',
        'automatic_adoption': False, 'requires_cif_review': False, 'production_pipeline': 'UNCHANGED'}
    (output / 'scaffold_preparation.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return result


def _bound_artifact(root, row):
    name = row['path']; p = PurePosixPath(name)
    if (not isinstance(name, str) or name.startswith('/') or '\\' in name or ':' in name
            or any(v in {'', '.', '..'} for v in name.split('/'))):
        raise ValueError('Unsafe candidate artifact path')
    path = root / p
    if any(v.is_symlink() for v in [path, *path.parents]) or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Candidate artifact traverses a symlink or leaves its root')
    data = path.read_bytes()
    if sha256(data).hexdigest() != row['sha256'] or len(data) != row['size']:
        raise ValueError('Candidate artifact changed')
    return path


def _cross_site_proxies(native, kind):
    atoms = {a['i_seq']: a for a in native['atoms']}
    return Counter(json.dumps({k: v for k, v in row.items() if k not in {'i_seqs', 'j_seqs'}}, sort_keys=True, allow_nan=False)
        for row in native['geometry']['proxy_details'][kind]
        if len({_site(atoms[i]) for i in [*row['i_seqs'], *row.get('j_seqs', [])]}) > 1)


def qualify_scaffold_candidate(baseline, native, model, receipt, output, *, code):
    """Require exact preserved scaffold/policy and projected selected mechanics."""
    checks = []
    def check(name, ok, **evidence):
        checks.append({'check': name, 'status': 'PASS' if ok else 'REVIEW', **evidence})
    try:
        output, model = Path(output), Path(model)
        if receipt.get('policy_id') != POLICY_ID or receipt.get('component') != code:
            raise ValueError('Unbound scaffold preparation policy/component')
        model_copy = _bound_artifact(output, receipt['outputs']['model'])
        for row in [*receipt['outputs']['dictionaries'], *receipt['outputs']['phils']]:
            _bound_artifact(output, row)
        projections = {site: (_bound_artifact(output, row), code) for site, row in receipt['outputs']['projections'].items()}
        changed = set(receipt['changed_sites'])
        if not changed or set(projections) != changed or {r['site'] for r in receipt['preparation']['sites']} != changed:
            raise ValueError('Selected preparation/projection sites differ')
        check('preserved-model-bytes', model.read_bytes() == model_copy.read_bytes())
        _model(baseline, model, coordinates_match=True); _model(native, model, coordinates_match=True)
        identity = lambda n: [{k: v for k, v in a.items() if k != 'xyz'} for a in n['atoms']]
        check('exact-scaffold-identities', identity(baseline) == identity(native) and baseline['atom_count'] == native['atom_count'] == len(native['atoms']))
        for label, record in [('baseline', baseline), ('candidate', native)]:
            points = record['geometry']['sites_cart_exact']; atoms = record['atoms']
            check(label + ':coordinate-roundtrip', len(points) == len(atoms) and all(len(p) == len(a['xyz']) == 3 and all(type(x) in (int, float) and math.isfinite(x) and abs(x-y) <= 1e-12 for x, y in zip(p, a['xyz'])) for p, a in zip(points, atoms)))
            check(label + ':native-interpreter', record.get('status') == 'REVIEW' and record.get('inventory_detail') == 'linked'
                and record.get('fatal_problems') is None and record.get('unused_definitions') == [] and record.get('unsupported_fields') == [])
            for name, ok in energy_inventory_checks(record).items(): check(label + ':' + name, ok)
        check('unchanged-coordinate-values', all(all(math.isfinite(x) and math.isfinite(y) and abs(x-y) <= 1e-12 for x, y in zip(a['xyz'], b['xyz'])) for a, b in zip(baseline['atoms'], native['atoms'])))
        check('fixed-narestraints-policy', _fixed_policy(baseline) and _fixed_policy(native) and baseline['restraint_policy'] == native['restraint_policy'])
        check('exact-installed-apis', bool(baseline.get('installed_api_sources')) and baseline['installed_api_sources'] == native.get('installed_api_sources'))
        before_links, after_links = native_backbone_links(baseline), native_backbone_links(native)
        check('all-backbone-links-preserved', before_links == after_links, expected=len(before_links), observed=len(after_links))
        old_rows, rows = baseline['monomer_mappings']['rows'], native['monomer_mappings']['rows']
        old, mappings = {r['site']: r for r in old_rows}, {r['site']: r for r in rows}
        check('all-complete-monomer-sites', len(old) == len(old_rows) and len(mappings) == len(rows) and set(old) == set(mappings)
            and all(r.get('missing_non_hydrogen_atoms', {}).get('status') == 'RECORDED' and r['missing_non_hydrogen_atoms']['atom_ids'] == []
                and r.get('unexpected_atoms', {}).get('status') == 'RECORDED' and r['unexpected_atoms']['atom_ids'] == [] for r in rows))
        check('unselected-monomer-mappings-preserved', {s: r for s, r in old.items() if s not in changed} == {s: r for s, r in mappings.items() if s not in changed})
        checks.extend(site_definition_checks(native, [receipt['preparation']]))
        checks.extend(definition_projection_checks(native, projections))
        edit_origin = native['restraint_policy']['origin_ids']['edits']
        covalent = deepcopy(native)
        covalent['geometry']['proxy_details'] = {k: [r for r in vs if r.get('origin_id') != edit_origin] for k, vs in native['geometry']['proxy_details'].items()}
        for plan in receipt['preparation']['sites']:
            site = plan['site']; mapping = mappings[site]
            check('selected-component-identity:' + site, mapping['resname'].strip() == code)
            check('native-dna-metadata:' + site, mapping['metadata'].get('group') == 'DNA' and mapping['metadata'].get('classification') == {'status': 'RECORDED', 'value': 'DNA'})
            ids = [plan['modification_id']] if plan.get('modification_id') else []
            check('exact-selected-modifier:' + site, mapping.get('chem_mod_ids') == {'status': 'RECORDED', 'ids': ids})
            check('no-deleted-coordinate-atoms:' + site, not any(a['atom_id'] in plan['deleted_atoms'] and _site(a) == site for a in native['atoms']))
            for name, ok in _heavy_proxy_checks(covalent, projections[site][0], code, site).items(): check(name + ':' + site, ok)
            if plan.get('incoming_site'):
                atoms = {a['i_seq']: a for a in native['atoms']}
                p = next(i for i, a in atoms.items() if _site(a) == site and a['atom_id'] == 'P')
                ns = {next(i for i in r['i_seqs'] if i != p) for r in native['geometry']['proxy_details']['bond_simple'] if p in r['i_seqs'] and r.get('origin_id') != edit_origin}
                angles = {min(tuple(r['i_seqs']), tuple(r['i_seqs'])[::-1]) for r in native['geometry']['proxy_details']['angle'] if r.get('origin_id') != edit_origin}
                expected = {(plan['incoming_site'], "O3'"), (site, "O5'"), (site, 'OP1'), (site, 'OP2')}
                check('linked-phosphate-tetrahedral-coverage:' + site, {(_site(atoms[i]), atoms[i]['atom_id']) for i in ns} == expected
                    and all(min((a, p, b), (b, p, a)) in angles for a, b in combinations(ns, 2)))
        kinds = {'bond_simple', 'bond_asu', 'angle', 'dihedral', 'const_dihedral', 'chirality', 'planarity', 'parallelity'}
        details = native['geometry']['proxy_details']
        check('complete-proxy-inventory', set(details) == kinds and all(isinstance(vs, list) and native['geometry']['proxy_counts'].get(k) == len(vs) for k, vs in details.items()))
        dump = lambda row: json.dumps(row, sort_keys=True, allow_nan=False)
        requests, previous = native['geometry']['custom_proxy_requests'], baseline['geometry']['custom_proxy_requests']
        check('exact-custom-requests', Counter(map(dump, requests)) == Counter(map(dump, previous)))
        failures = []
        for request in requests:
            kind = 'bond_simple' if request['kind'] == 'bond' else request['kind']
            if sum(proxy_signature(request['kind'], request) == proxy_signature(request['kind'], row)
                   for row in details[kind] if row.get('origin_id') == edit_origin) != 1:
                failures.append(request['kind'])
        check('exact-custom-request-membership', not failures, failures=failures)
        for kind in kinds:
            check('unaffected-native-proxies:' + kind, _proxy_subset(baseline, changed, kind) == _proxy_subset(native, changed, kind))
            check('inter-site-native-proxies:' + kind, _cross_site_proxies(baseline, kind) == _cross_site_proxies(native, kind))
            check('explicit-policy-proxies:' + kind, Counter(dump(r) for r in baseline['geometry']['proxy_details'][kind] if r.get('origin_id') == edit_origin)
                == Counter(dump(r) for r in details[kind] if r.get('origin_id') == edit_origin))
        finite = True
        for kind, vs in details.items():
            for row in vs:
                weights = row.get('weights', [row.get('weight')])
                finite &= all(type(w) in (int, float) and math.isfinite(w) and (w > 0 or kind == 'const_dihedral' and w == 0 and row.get('periodicity') == 0) for w in weights)
                fields = [] if kind == 'planarity' else ['distance_ideal'] if kind in {'bond_simple', 'bond_asu'} else ['angle_ideal'] if kind in {'angle', 'dihedral', 'const_dihedral'} else ['volume_ideal'] if kind == 'chirality' else ['target_angle_deg']
                finite &= all(type(row.get(k)) in (int, float) and math.isfinite(row[k]) for k in fields)
        check('finite-positive-active-parameters', finite)
    except (KeyError, TypeError, ValueError, OSError, IndexError, StopIteration, ZeroDivisionError, OverflowError) as exc:
        check('complete-scaffold-evidence', False, error=type(exc).__name__ + ': ' + str(exc))
    result = {'schema_version': 1, 'policy_id': POLICY_ID, 'component': code, 'scope': SCOPE, 'checks': checks,
        'model_sha256': receipt.get('outputs', {}).get('model', {}).get('sha256'), 'scientific_approval': 'NOT_RUN',
        'nonbonded_pair_identity': 'NOT_ASSESSED', 'formal_charge_readback': 'UNSUPPORTED_UNLESS_RECORDED',
        'automatic_adoption': False, 'requires_cif_review': False, 'production_pipeline': 'UNCHANGED'}
    result['native_usable'] = mechanics_can_continue(result)
    result['status'] = 'SCAFFOLD_CANDIDATE_MECHANICS_PASS' if result['native_usable'] else 'REVIEW'
    return result


def select_scaffold_candidate(preparation, qualification, baseline_usable, *, candidate_execution='COMPLETED'):
    """Choose a separately verified bundle or retain the frozen usable original.

    The orchestration must establish baseline_usable by fresh exact matching to
    its qualified capture. No energies from changed objectives are ranked and no
    unseen original stereochemistry or chemical-state equivalence is asserted.
    """
    if type(baseline_usable) is not bool:
        raise ValueError('Fresh baseline verification must be explicit')
    usable = (baseline_usable and candidate_execution == 'COMPLETED'
        and preparation.get('policy_id') == qualification.get('policy_id') == POLICY_ID
        and preparation.get('component') == qualification.get('component')
        and qualification.get('scope') == SCOPE and qualification.get('native_usable') is True
        and qualification.get('status') == 'SCAFFOLD_CANDIDATE_MECHANICS_PASS'
        and qualification.get('model_sha256') == preparation.get('outputs', {}).get('model', {}).get('sha256')
        and bool(qualification.get('checks')) and mechanics_can_continue(qualification))
    selected = 'qualified_candidate' if usable else 'original_frozen_bundle' if baseline_usable else None
    notes = ['The separate bundle retains unresolved convergence, geometry, chemical-state and stereochemical qualification notes.']
    if selected == 'original_frozen_bundle': notes.append('The replacement did not pass this native context; the verified frozen bundle remains available automatically.')
    if selected is None: notes.append('A fresh usable baseline was not established; no bundle was selected.')
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'scope': SCOPE,
        'status': 'CONTINUE_WITH_NOTES' if selected else 'NO_USABLE_DICTIONARY',
        'selected_candidate': selected, 'continue_solving': selected is not None,
        'candidate_native_usable': usable, 'baseline_usable': baseline_usable, 'notes': notes,
        'ranking': 'VERIFIED_CONTEXT_THEN_PRESERVED_FALLBACK', 'objective_comparison': 'NOT_RUN',
        'scientific_approval': 'NOT_RUN', 'automatic_adoption': False, 'requires_cif_review': False,
        'production_pipeline': 'UNCHANGED'}
