"""Preserved candidates need current source and linkage evidence."""
from hashlib import sha256
import pytest
from nasolve.cif_mixed_source_recovery import candidate_bytes, replacement_scope
from tests.test_mixed_endpoint_window_probe import pack


def test_candidate_reuse_binds_archive_member_and_exact_current_source():
    raw = pack({'saved/source.cif': b'source', 'saved/candidate.cif': b'candidate',
                'captured.py': b'raise RuntimeError("never execute")'})
    digest = sha256(raw).hexdigest()
    assert candidate_bytes(raw, digest, 'saved/source.cif', 'saved/candidate.cif', b'source') == b'candidate'
    with pytest.raises(ValueError, match='source'):
        candidate_bytes(raw, digest, 'saved/source.cif', 'saved/candidate.cif', b'different source')
    with pytest.raises(ValueError):
        candidate_bytes(raw, digest, 'saved/source.cif', '../candidate.cif', b'source')


def test_replacement_refuses_prior_modifiers_or_incomplete_shared_code_scope():
    rows = [{'site': 'A:2', 'resname': 'Q17', 'chem_mod_ids': {'status': 'RECORDED', 'ids': []}},
            {'site': 'B:2', 'resname': 'Q17', 'chem_mod_ids': {'status': 'RECORDED', 'ids': []}}]
    assert replacement_scope(rows, {'A:2': 'Q17', 'B:2': 'Q17'}, 'Q17') == ['A:2', 'B:2']
    with pytest.raises(ValueError): replacement_scope(rows, {'A:2': 'Q17'}, 'Q17')
    rows[0]['chem_mod_ids']['ids'] = ['OLD']
    with pytest.raises(ValueError, match='modifiers'):
        replacement_scope(rows, {'A:2': 'Q17', 'B:2': 'Q17'}, 'Q17')


@pytest.mark.parametrize('defect', ['none', 'source_charge', 'native_target', 'missing_angle', 'nonrepeat_gradient'])
def test_reuse_requalifies_both_controls_against_current_source(tmp_path, monkeypatch, defect):
    from copy import deepcopy
    from nasolve import cif_mixed_source_recovery as recovery
    from tests.test_cif_candidate_usability import native_case
    from nasolve.cif_linked_preparation import component_values, _render
    source, candidate, model, native = native_case(tmp_path)
    policy = tmp_path/'isolated.phil'; policy.write_text('declared test policy')
    second = deepcopy(native)
    if defect == 'source_charge':
        values = component_values(source, 'Q17'); values['_chem_comp_atom.charge'][0] = '1'
        source.write_text(_render(values, 'Q17'))
    elif defect == 'native_target': second['geometry']['proxy_details']['bond_simple'][0]['distance_ideal'] += 0.1
    elif defect == 'missing_angle':
        second['geometry']['proxy_details']['angle'].pop(); second['geometry']['proxy_counts']['angle'] -= 1
    elif defect == 'nonrepeat_gradient': second['energy_inventory']['snapshots'][1]['gradient'][0] += 1
    # Only the capture transport is synthetic. Both chemistry and all native
    # qualification predicates execute against complete artificial dictionaries.
    calls = []
    def capture(root, ref, paths, **kwargs):
        calls.append(ref)
        return {'native_validation': native if ref == 'source' else second}
    monkeypatch.setattr(recovery, '_capture', capture)
    inputs = {'sources': {'Q17': recovery._ref(source, tmp_path)}, 'candidate': recovery._ref(candidate, tmp_path),
              'models': {'candidate_seed': recovery._ref(model, tmp_path), 'source_seed': recovery._ref(model, tmp_path)},
              'isolated_policy': recovery._ref(policy, tmp_path)}
    spec = {'component': 'Q17', 'timeout_seconds': 60, 'phenix_version': 'SYNTHETIC'}
    q = recovery._isolated(tmp_path, inputs, spec, {'source_seed': 'source', 'candidate_seed': 'candidate'})
    assert calls == ['source', 'candidate']  # independent of JSON object order
    assert q['combined']['native_usable'] is (defect == 'none')
    assert q['coordinate_cases']['source_seed']['native_usable'] is (defect != 'source_charge')


def preparation_case(tmp_path):
    from nasolve import cif_mixed_source_recovery as recovery
    from tests.test_cif_linked_usability_bridge import prepared_inputs
    source, candidate, model, contexts, q = prepared_inputs(tmp_path)
    current = tmp_path/'old.cif'; current.write_bytes(candidate.read_bytes())
    bystander = tmp_path/'bystander.cif'; bystander.write_text(candidate.read_text().replace('ZZZ', 'V29'))
    active = tmp_path/'active.phil'; active.write_text('unchanged declared NA policy')
    empty = tmp_path/'empty.phil'; empty.write_bytes(b'')
    resource = lambda role, p: {'role': role, 'artifact': recovery._ref(p, tmp_path)}
    inputs = {'sources': {'ZZZ': recovery._ref(source, tmp_path)}, 'candidate': recovery._ref(candidate, tmp_path),
        'resources': [resource('model', model), resource('dictionary', current), resource('dictionary', bystander),
                      resource('phil', active), resource('phil', empty)],
        'active_policy': recovery._ref(active, tmp_path), 'projections': {}}
    return inputs, contexts, {'combined': q}, current, bystander


def test_replacement_preserves_bystanders_and_all_declared_phosphate_contexts(tmp_path):
    from nasolve import cif_mixed_source_recovery as recovery
    from nasolve.cif_linked_preparation import component_values
    inputs, contexts, qualification, current, bystander = preparation_case(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    bundle = recovery._prepare(tmp_path, inputs, {'component': 'ZZZ'}, contexts, qualification)
    sites = {r['site']: r for r in bundle['preparations']['ZZZ']['receipt']['sites']}
    assert sites['A:2']['deleted_atoms'] == ['OP3', 'leaveH']
    assert sites['A:2']['retained_op2_hydrogens'] == ['keepH']
    assert sites['A:1']['deleted_atoms'] == ['oddH'] and 'OP3' in sites['A:1']['expected_atoms']
    assert sites['B:1']['deleted_atoms'] == ['OP1', 'OP2', 'OP3', 'P', 'keepH', 'leaveH']
    paths = [recovery._resolve(tmp_path, ref) for ref in bundle['native_dictionaries']]
    assert current not in paths and bystander in paths
    assert all(p.read_bytes() == data for p, data in before.items())
    moved = tmp_path.parent/(tmp_path.name+'-relocated'); tmp_path.rename(moved)
    assert not tmp_path.exists()
    for row in bundle['site_projections'].values():
        assert component_values(recovery._resolve(moved, row['dictionary']), 'ZZZ')


@pytest.mark.parametrize('defect', ['shared_dictionary', 'duplicate_provider', 'missing_context', 'unusable_candidate', 'ambiguous_policy'])
def test_replacement_fails_closed_without_broad_resource_rewrites(tmp_path, defect):
    from nasolve import cif_mixed_source_recovery as recovery
    inputs, contexts, qualification, current, bystander = preparation_case(tmp_path)
    if defect == 'shared_dictionary':
        current.write_bytes(current.read_bytes()+bystander.read_bytes())
        inputs['resources'][1]['artifact'] = recovery._ref(current, tmp_path)
    elif defect == 'duplicate_provider': inputs['resources'].append(inputs['resources'][1])
    elif defect == 'missing_context': contexts.pop()
    elif defect == 'unusable_candidate': qualification['combined']['native_usable'] = False
    elif defect == 'ambiguous_policy': inputs['resources'].append(inputs['resources'][3])
    before = current.read_bytes(), bystander.read_bytes()
    with pytest.raises(ValueError): recovery._prepare(tmp_path, inputs, {'component': 'ZZZ'}, contexts, qualification)
    assert before == (current.read_bytes(), bystander.read_bytes())


@pytest.mark.parametrize('defect', ['bytes', 'traversal', 'symlink'])
def test_owned_artifacts_cannot_escape_or_change(tmp_path, defect):
    from nasolve import cif_mixed_source_recovery as recovery
    path = tmp_path/'data'; path.write_bytes(b'original'); ref = recovery._ref(path, tmp_path)
    if defect == 'bytes': path.write_bytes(b'changed')
    elif defect == 'traversal': ref['path'] = '../data'
    else:
        outside = tmp_path.parent/(tmp_path.name+'-external'); outside.write_bytes(b'original')
        path.unlink(); path.symlink_to(outside)
    with pytest.raises(ValueError): recovery._resolve(tmp_path, ref)


@pytest.mark.parametrize('defect', ['none', 'different_interpreter', 'missing_hash', 'missing_control'])
def test_native_controls_bind_one_selected_interpreter(tmp_path, defect):
    import json
    from nasolve import cif_mixed_source_recovery as recovery
    captures = {'isolated': {}, 'linked': {}}
    for scope, names in [('isolated', ['source_seed', 'candidate_seed']), ('linked', ['baseline', 'active'])]:
        for name in names:
            digest = 'a'*64
            if name == 'active' and defect == 'different_interpreter': digest = 'b'*64
            if name == 'active' and defect == 'missing_hash': digest = None
            path = tmp_path/(name+'.json'); path.write_text(json.dumps({'executable_sha256': digest, 'phenix_version': 'test'}))
            captures[scope][name] = recovery._ref(path, tmp_path)
    if defect == 'missing_control': del captures['linked']['active']
    if defect == 'none': recovery._same_interpreter(tmp_path, captures)
    else:
        with pytest.raises(ValueError): recovery._same_interpreter(tmp_path, captures)


def test_inventory_rejects_dangling_symlink_and_reader_refuses_existing_output(tmp_path):
    from types import SimpleNamespace
    from nasolve import cif_mixed_source_recovery as recovery
    link = tmp_path/'unexpected'; link.symlink_to(tmp_path/'absent')
    with pytest.raises(ValueError, match='symlink'): recovery._inventory(tmp_path)
    with pytest.raises(ValueError, match='fresh'):
        recovery.audit_mixed_source_recovery(tmp_path/'a.zip', tmp_path/'b.zip', tmp_path,
            SimpleNamespace(), endpoint_sha256='a'*64, candidate_archive_sha256='b'*64, component='Q17',
            source_member='source.cif', candidate_member='candidate.cif')
