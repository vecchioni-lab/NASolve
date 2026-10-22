"""Separate full-bundle candidates preserve unrelated files and native policy."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest


def preparation_case(tmp_path):
    from tests.test_cif_linked_usability_bridge import prepared_inputs
    from nasolve.cif_construction_provenance import _pdb_inventory
    source, numerical, model, contexts, qualification = prepared_inputs(tmp_path)
    # A shared modification remains in use by an unselected canonical residue.
    model.write_text(model.read_text().replace('END\n', '') +
        'HETATM   99    P  DG C   1       0.000   0.000   0.000  1.00 20.00           P\nEND\n')
    inventory = _pdb_inventory(model)
    atoms = []
    for i, (key, a) in enumerate(inventory.items()):
        chain, resid, icode, altloc, name = key
        atoms.append({'i_seq': i, 'atom_id': name, 'element': a['element'], 'xyz': a['xyz'],
            'identity': dict(model_id='', chain_id=chain, resseq=resid, icode=icode, altloc=altloc, resname=a['code']),
            'label': ':'.join(key)})
    old = {'A:1': 'OLD1', 'A:2': 'SHARED', 'B:1': 'OLD2', 'C:1': 'SHARED'}
    mappings = [{'site': s, 'resname': 'DG' if s == 'C:1' else 'ZZZ',
                 'chem_mod_ids': {'status': 'RECORDED', 'ids': [m]}} for s, m in old.items()]
    index = {((a['identity']['chain_id'] + ':' + a['identity']['resseq']), a['atom_id']): a['i_seq'] for a in atoms}
    bond = {'i_seqs': [index[('A:1', "O3'")], index[('A:2', 'P')]], 'distance_ideal': 1.6, 'weight': 10000.}
    baseline = {'atoms': atoms, 'monomer_mappings': {'rows': mappings}, 'geometry': {'simple_bonds': [bond], 'asu_bonds': []}}
    shared = numerical.with_name('shared.cif')
    shared.write_text('data_mod_SHARED\nloop_\n_chem_mod_atom.mod_id\n_chem_mod_atom.function\n_chem_mod_atom.atom_id\nSHARED delete OP3\n')
    obsolete = numerical.with_name('obsolete.cif')
    obsolete.write_text(''.join(f'data_mod_{m}\nloop_\n_chem_mod_atom.mod_id\n_chem_mod_atom.function\n_chem_mod_atom.atom_id\n{m} delete OP3\n' for m in ['OLD1', 'OLD2']))
    other = numerical.with_name('other.cif'); other.write_text('data_other\n# unrelated exact bytes\n')
    def request(site, code, mod):
        chain, resid = site.split(':')
        return (f'refinement.pdb_interpretation.apply_cif_modification {{\n  data_mod = {mod}\n'
                f"  residue_selection = chain '{chain}' and resid {resid} and resname {code}\n}}\n")
    keep = request('C:1', 'DG', 'SHARED')
    phil = numerical.with_name('shared.phil')
    phil.write_text('# original comment survives\n' + ''.join(request(s, 'ZZZ', m) for s, m in old.items() if s != 'C:1') + keep)
    untouched = numerical.with_name('policy.phil'); untouched.write_text('# exact policy\npdb_interpretation.secondary_structure.enabled = False\n')
    return source, numerical, model, [numerical, shared, obsolete, other], [phil, untouched], baseline, contexts, qualification, keep


def run_preparation(tmp_path, defect='none'):
    from nasolve.cif_scaffold_candidate import prepare_scaffold_candidate
    source, numerical, model, dictionaries, phils, baseline, contexts, q, keep = preparation_case(tmp_path)
    if defect == 'mixed_dictionary':
        dictionaries[0].write_text(dictionaries[0].read_text() + dictionaries[0].read_text().replace('ZZZ', 'YYY'))
    if defect == 'two_selected': dictionaries.append(numerical)
    if defect == 'missing_request': phils[0].write_text(phils[0].read_text().replace('data_mod = OLD2', 'data_mod = UNKNOWN'))
    if defect == 'wrong_selection': phils[0].write_text(phils[0].read_text().replace("resid 2 and resname ZZZ", "resid 2 and resname DG"))
    if defect == 'unknown_selector': phils[0].write_text(phils[0].read_text().replace("chain 'A' and resid 2 and resname ZZZ", "chain 'A' or resid 2"))
    if defect == 'context': contexts[0]['incoming_site'] = 'C:1'
    if defect == 'uncovered_code': contexts.pop()
    if defect == 'baseline_atom': baseline['atoms'].pop()
    if defect == 'qualification': q['native_usable'] = False
    if defect == 'symlink_parent':
        (tmp_path / 'alias').symlink_to(tmp_path / 'inputs', target_is_directory=True)
    output = tmp_path / ('alias/out' if defect == 'symlink_parent' else 'out')
    snapshots = {p: p.read_bytes() for p in [source, numerical, model, *dictionaries, *phils]}
    r = prepare_scaffold_candidate(source, numerical, model, dictionaries, phils, baseline, contexts, output,
                                   code='ZZZ', native_qualification=q)
    assert all(p.read_bytes() == data for p, data in snapshots.items())
    assert (output / r['outputs']['model']['path']).read_bytes() == model.read_bytes()
    assert [v['input_index'] for v in r['removed_obsolete_modification_files']] == [2]
    assert len(r['removed_modifier_requests']) == 3
    copied = [output / a['path'] for a in r['outputs']['dictionaries']]
    assert any(p.read_bytes() == dictionaries[1].read_bytes() for p in copied)
    assert any(p.read_bytes() == dictionaries[3].read_bytes() for p in copied)
    phil = (output / r['outputs']['phils'][0]['path']).read_text()
    assert phil == '# original comment survives\n' + keep
    assert (output / r['outputs']['phils'][1]['path']).read_bytes() == phils[1].read_bytes()
    assert not r['automatic_adoption'] and not r['requires_cif_review']
    return r


def test_separate_bundle_removes_only_owned_requests_and_resources(tmp_path):
    run_preparation(tmp_path)


@pytest.mark.parametrize('defect', ['mixed_dictionary', 'two_selected', 'missing_request', 'wrong_selection', 'unknown_selector',
    'context', 'uncovered_code', 'baseline_atom', 'qualification', 'symlink_parent'])
def test_preparation_cannot_guess_ownership_or_hide_bad_evidence(tmp_path, defect):
    with pytest.raises((ValueError, FileExistsError)):
        run_preparation(tmp_path, defect)


def native_case(tmp_path):
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_scaffold_candidate import POLICY_ID
    a, b, model, prep, projected = case(tmp_path)
    for n in [a, b]:
        n['installed_api_sources'] = [{'module': 'fixed-native', 'sha256': 'a' * 64}]
        n['geometry']['custom_proxy_requests'] = []
        # Explicit policy angle crosses the selected site's boundary.
        angle = deepcopy(n['geometry']['proxy_details']['angle'][-1]); angle['origin_id'] = 2; angle['angle_ideal'] = 125.
        n['geometry']['proxy_details']['angle'].append(angle)
        n['geometry']['proxy_counts']['angle'] += 1
        n['geometry']['custom_proxy_requests'].append({**angle, 'kind': 'angle', 'action': 'add'})
    def artifact(path): return {'path': path.name, 'sha256': sha256(path.read_bytes()).hexdigest(), 'size': path.stat().st_size}
    receipt = {'policy_id': POLICY_ID, 'component': 'ZZZ', 'changed_sites': ['A:2'], 'preparation': prep,
        'outputs': {'model': artifact(model), 'dictionaries': [], 'phils': [], 'projections': {'A:2': artifact(projected)}},
        'automatic_adoption': False, 'requires_cif_review': False}
    return a, b, model, receipt


@pytest.mark.parametrize('defect', ['none', 'coordinate', 'roundoff', 'roundtrip', 'identity', 'mapping', 'definition',
    'link', 'custom_request', 'custom_weight', 'proxy_weight', 'proxy_count', 'ss', 'api', 'charge', 'unsupported_charge',
    'modifier', 'phosphate_angle', 'energy', 'nan', 'artifact', 'projection', 'unselected_proxy'])
def test_full_scaffold_checks_do_not_accept_counts_or_notes_as_proof(tmp_path, defect):
    from nasolve.cif_scaffold_candidate import qualify_scaffold_candidate
    a, b, model, r = native_case(tmp_path)
    d = b['geometry']['proxy_details']; site = b['monomer_mappings']['rows'][1]
    if defect == 'coordinate': b['atoms'][0]['xyz'][0] += .01
    if defect == 'roundoff': b['atoms'][0]['xyz'][0] += 1e-15
    if defect == 'roundtrip': b['geometry']['sites_cart_exact'][0][0] += .01
    if defect == 'identity': b['atoms'][0]['identity']['resname'] = 'DA'
    if defect == 'mapping': b['monomer_mappings']['rows'].pop()
    if defect == 'definition': b['monomer_mappings']['rows'][0]['metadata']['effective_definition']['changed'] = []
    if defect == 'link': d['bond_simple'][-1]['distance_ideal'] += .1
    if defect == 'custom_request': b['geometry']['custom_proxy_requests'][0]['angle_ideal'] += 1
    if defect == 'custom_weight': d['angle'][-1]['weight'] *= 2
    if defect == 'proxy_weight': d['bond_simple'][0]['weight'] *= 2
    if defect == 'proxy_count': b['geometry']['proxy_counts']['angle'] += 1
    if defect == 'ss': b['restraint_policy']['secondary_structure_enabled'] = True
    if defect == 'api': b['installed_api_sources'][0]['sha256'] = 'b' * 64
    if defect == 'charge': site['metadata']['effective_definition']['atoms'][0]['charge'] = '-1'
    if defect == 'unsupported_charge':
        for x in site['metadata']['effective_definition']['atoms']: x['charge'] = None
    if defect == 'modifier': site['chem_mod_ids']['ids'] = []
    if defect == 'phosphate_angle': d['angle'].pop(-2); b['geometry']['proxy_counts']['angle'] -= 1
    if defect == 'energy': b['energy_inventory']['snapshots'][1]['target'] += 1
    if defect == 'nan': d['angle'][-1]['angle_ideal'] = float('nan')
    if defect == 'artifact': r['outputs']['model']['sha256'] = '0' * 64
    if defect == 'projection': (tmp_path / r['outputs']['projections']['A:2']['path']).write_text('data_broken\n')
    if defect == 'unselected_proxy':
        p = deepcopy(d['bond_simple'][-1]); p['i_seqs'] = [0, 7]; p['atoms'] = [b['atoms'][i]['label'] for i in p['i_seqs']]
        d['bond_simple'].append(p); b['geometry']['proxy_counts']['bond_simple'] += 1
    q = qualify_scaffold_candidate(a, b, model, r, tmp_path, code='ZZZ')
    assert q['native_usable'] is (defect in {'none', 'roundoff', 'unsupported_charge'}), q['checks']
    assert not q['automatic_adoption'] and not q['requires_cif_review']


@pytest.mark.parametrize('candidate,baseline,expected', [(True, True, 'qualified_candidate'), (False, True, 'original_frozen_bundle'), (True, False, None)])
def test_decision_selects_only_verified_usable_candidate_and_preserves_fallback(tmp_path, candidate, baseline, expected):
    from nasolve.cif_scaffold_candidate import qualify_scaffold_candidate, select_scaffold_candidate
    a, b, model, r = native_case(tmp_path)
    q = qualify_scaffold_candidate(a, b, model, r, tmp_path, code='ZZZ')
    if not candidate: q['native_usable'] = False; q['status'] = 'REVIEW'
    d = select_scaffold_candidate(r, q, baseline_usable=baseline)
    assert d['selected_candidate'] == expected
    assert d['continue_solving'] is (baseline and expected is not None)
    assert not d['requires_cif_review'] and not d['automatic_adoption']


def test_decision_rejects_unbound_candidate_report(tmp_path):
    from nasolve.cif_scaffold_candidate import select_scaffold_candidate
    _, _, _, r = native_case(tmp_path)
    d = select_scaffold_candidate(r, {'native_usable': True, 'policy_id': 'forged'}, baseline_usable=True)
    assert d['selected_candidate'] == 'original_frozen_bundle'


@pytest.mark.parametrize('defect', ['execution', 'failed_check', 'empty_checks', 'model_binding', 'component_binding', 'wrong_scope'])
def test_failed_candidate_automatically_retains_verified_original(tmp_path, defect):
    from nasolve.cif_scaffold_candidate import qualify_scaffold_candidate, select_scaffold_candidate
    a, b, model, r = native_case(tmp_path)
    q = qualify_scaffold_candidate(a, b, model, r, tmp_path, code='ZZZ')
    execution = 'COMPLETED'
    if defect == 'execution': execution = 'TIMED_OUT'
    if defect == 'failed_check': q['checks'][0]['status'] = 'REVIEW'
    if defect == 'empty_checks': q['checks'] = []
    if defect == 'model_binding': q['model_sha256'] = '0' * 64
    if defect == 'component_binding': q['component'] = 'YYY'
    if defect == 'wrong_scope': q['scope'] = 'ISOLATED_COMPONENT_ONLY'
    d = select_scaffold_candidate(r, q, baseline_usable=True, candidate_execution=execution)
    assert d['selected_candidate'] == 'original_frozen_bundle'
    assert d['status'] == 'CONTINUE_WITH_NOTES' and d['continue_solving']
    assert d['objective_comparison'] == 'NOT_RUN' and not d['automatic_adoption']
