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
from .cif_terminal_qualification import definition_projection_checks, _proxy_subset

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
            check('unaffected-native-proxies:' + kind, _proxy_subset(reference, selected, kind) == _proxy_subset(native, selected, kind))
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
        'triple_readback': triples, 'scientific_geometry_qualification': 'NOT_ASSESSED',
        'formal_charge_readback': 'UNSUPPORTED_UNLESS_RECORDED', 'nonbonded_pair_identity': 'NOT_ASSESSED',
        'model_optimization': 'NOT_RUN', 'policy_authority': 'NARestraints', 'policy_recompilation': 'NOT_RUN',
        'requires_cif_review': False, 'automatic_adoption': False}
    result['mechanics_checks_pass'] = mechanics_can_continue(result)
    result['status'] = 'CONSTRUCTED_NATIVE_MECHANICS_PASS' if result['mechanics_checks_pass'] else 'REVIEW'
    return result
