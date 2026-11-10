"""Ordered explicit restraint intent is separate from native usability and topology."""
from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch
import shutil

import pytest

from nasolve.campaign_records import read_record, write_record
from tests.test_cif_complete_request import case
from tests.test_cif_model_context import bind, model
from tests.test_cif_repair_attempt import inventory


def phils(tmp_path):
    first = tmp_path/'pair.phil'; second = tmp_path/'stack.phil'
    first.write_text('''# Preserve this exact input and its caller order.
refinement {
 pdb_interpretation.secondary_structure {
  enabled = False
 }
 geometry_restraints.edits {
  bond {
   action = add
   atom_selection_1 = chain A and resid 1 and name P
   atom_selection_2 = chain A and resid 2 and name OP1
   distance_ideal = 2.91
   sigma = 0.07
  }
  angle {
   action = add
   atom_selection_1 = chain A and resid 1 and name OP1
   atom_selection_2 = chain A and resid 1 and name P
   atom_selection_3 = chain A and resid 2 and name OP2
   angle_ideal = 123.4
   sigma = 3.2
  }
 }
}
''')
    second.write_text('''geometry_restraints.edits.parallelity {
 action = add
 atom_selection_1 = chain A and resid 1 and (name P or name OP1 or name OP2)
 atom_selection_2 = chain A and resid 2 and (name P or name OP1 or name OP2)
 target_angle_deg = 0
 sigma = 0.027
}
''')
    return [first, second]


def declared(args, tmp_path):
    from nasolve.cif_restraint_context import derive_restraint_context
    args = bind(args); args['supplementary_phils'] = phils(tmp_path)
    args['restraint_context'] = derive_restraint_context(args['model'], args['supplementary_phils'])
    args['native_context']['custom_restraints'] = 'required'
    return args


def test_ordered_context_preserves_exact_requests_and_has_no_native_claim(tmp_path):
    from nasolve.cif_restraint_context import derive_restraint_context, validate_restraint_context
    path = model(tmp_path/'model.pdb', last=2); inputs = phils(tmp_path); before = inventory(tmp_path)
    with patch('subprocess.Popen', side_effect=AssertionError('Read-only context must not execute')):
        saved = derive_restraint_context(path, inputs)
        assert validate_restraint_context(path, inputs, saved) == saved
    assert [r['input_index'] for r in saved['inputs']] == [0, 1]
    assert [r['sha256'] for r in saved['inputs']] == [sha256(p.read_bytes()).hexdigest() for p in inputs]
    assert [r['request_indices'] for r in saved['inputs']] == [[0, 1], [2]]
    assert saved['request_counts'] == {'angle': 1, 'bond': 1, 'parallelity': 1}
    assert saved['requests'][0]['distance_ideal'] == 2.91
    assert saved['requests'][1]['angle_ideal'] == 123.4
    assert saved['requests'][2]['weight'] == 1 / .027**2
    assert saved['site_modifier_owner'] == 'DICTIONARY_COMPOSER'
    assert saved['target_authority'] == 'SUPPLIED_EXPLICIT_PHIL'
    assert saved['native_membership'] == 'NOT_ASSESSED'
    assert inventory(tmp_path) == before
    reversed_context = derive_restraint_context(path, inputs[::-1])
    assert reversed_context != saved and reversed_context['requests'][0]['kind'] == 'parallelity'


def test_maintained_nar_compiler_keeps_every_request_and_separate_orientation_controls(tmp_path):
    from nasolve.cif_explicit_na_policy import compile_explicit_na_policy
    from nasolve.cif_restraint_context import derive_restraint_context
    from tests.test_cif_explicit_na_policy import fixture
    path, pairs, stacks, sources, controls = fixture(tmp_path)
    compiled = compile_explicit_na_policy(path, pairs, stacks, sources, tmp_path/'compiled', orientation_controls=controls)
    active = tmp_path/'compiled/explicit_na_policy.phil'
    before = inventory(tmp_path)
    derived = derive_restraint_context(path, [active])
    assert derived['requests'] == compiled['compiled_requests']
    assert derived['request_counts'] == compiled['request_counts']
    assert len(derived['inputs']) == 1 and inventory(tmp_path) == before
    control = tmp_path/'compiled'/compiled['orientation_controls'][0]['file']['path']
    with pytest.raises(ValueError, match='Duplicate'):
        derive_restraint_context(path, [active, control])


@pytest.mark.parametrize('defect', ['modifier', 'flat_modifier', 'flat_field_modifier', 'include', 'variable',
    'ss_enabled', 'no_disabled_ss', 'unknown_field', 'unknown_scope', 'delete', 'missing_action',
    'zero_sigma', 'negative_sigma', 'nan_sigma', 'infinite_target', 'negative_bond',
    'duplicate_field', 'duplicate_request', 'duplicate_different_weight', 'wrong_atom', 'self_bond',
    'overlapping_planes', 'open_parenthesis', 'close_parenthesis', 'tiny_sigma', 'huge_sigma', 'empty_requests', 'no_inputs', 'unbalanced', 'symlink'])
def test_unsupported_or_competing_phil_cannot_hide_in_a_frozen_context(tmp_path, defect):
    from nasolve.cif_restraint_context import derive_restraint_context
    path = model(tmp_path/'model.pdb', last=2); inputs = phils(tmp_path); text = inputs[0].read_text()
    if defect == 'modifier': text += 'refinement {\n pdb_interpretation {\n apply_cif_modification {\n data_mod = OLD\n residue_selection = chain A and resid 1\n }\n }\n}\n'
    elif defect == 'flat_modifier': text += 'refinement.pdb_interpretation.apply_cif_modification {\n data_mod = OLD\n residue_selection = chain A and resid 1\n}\n'
    elif defect == 'flat_field_modifier': text += 'refinement {\n pdb_interpretation.apply_cif_modification.data_mod = OLD\n}\n'
    elif defect == 'include': text += 'include file external.phil\n'
    elif defect == 'variable': text = text.replace('2.91', '$TARGET')
    elif defect == 'ss_enabled': text = text.replace('enabled = False', 'enabled = True')
    elif defect == 'no_disabled_ss': text = text.replace(' pdb_interpretation.secondary_structure {\n  enabled = False\n }\n', '')
    elif defect == 'unknown_field': text = text.replace('distance_ideal = 2.91', 'distance_ideal = 2.91\n   slack = 0.5')
    elif defect == 'unknown_scope': text += 'refinement.strategy {\n mode = extra\n}\n'
    elif defect == 'delete': text = text.replace('action = add', 'action = delete', 1)
    elif defect == 'missing_action': text = text.replace('   action = add\n', '', 1)
    elif defect == 'zero_sigma': text = text.replace('sigma = 0.07', 'sigma = 0')
    elif defect == 'negative_sigma': text = text.replace('sigma = 0.07', 'sigma = -0.07')
    elif defect == 'nan_sigma': text = text.replace('sigma = 0.07', 'sigma = nan')
    elif defect == 'infinite_target': text = text.replace('angle_ideal = 123.4', 'angle_ideal = inf')
    elif defect == 'negative_bond': text = text.replace('distance_ideal = 2.91', 'distance_ideal = -2.91')
    elif defect == 'duplicate_field': text = text.replace('sigma = 0.07', 'sigma = 0.07\n   sigma = 0.08')
    elif defect in {'duplicate_request', 'duplicate_different_weight'}:
        other = tmp_path/'duplicate.phil'; other.write_text(text if defect == 'duplicate_request' else text.replace('sigma = 0.07', 'sigma = 0.08')); inputs.append(other)
    elif defect == 'wrong_atom': text = text.replace('and name OP1', 'and name MISSING', 1)
    elif defect == 'self_bond': text = text.replace('chain A and resid 2 and name OP1', 'chain A and resid 1 and name P')
    elif defect == 'overlapping_planes': inputs[1].write_text(inputs[1].read_text().replace('resid 2', 'resid 1'))
    elif defect == 'open_parenthesis': inputs[1].write_text(inputs[1].read_text().replace('name OP2)', 'name OP2', 1))
    elif defect == 'close_parenthesis': inputs[1].write_text(inputs[1].read_text().replace('(name P', 'name P', 1))
    elif defect == 'tiny_sigma': text = text.replace('sigma = 0.07', 'sigma = 1e-200')
    elif defect == 'huge_sigma': text = text.replace('sigma = 0.07', 'sigma = 1e200')
    elif defect == 'empty_requests': text = 'pdb_interpretation.secondary_structure {\n enabled = False\n}\n'; inputs = inputs[:1]
    elif defect == 'no_inputs': inputs = []
    elif defect == 'unbalanced': text += '}\n'
    inputs[0].write_text(text) if inputs else None
    if defect == 'symlink':
        alias = tmp_path/'alias.phil'; alias.symlink_to(inputs[0]); inputs[0] = alias
    before = inventory(tmp_path)
    with pytest.raises(ValueError): derive_restraint_context(path, inputs)
    assert inventory(tmp_path) == before


def test_complete_request_preserves_order_and_composer_owns_modifiers(case, tmp_path):
    from nasolve.cif_na_policy import _parse, _path
    m, args, root, sdk, store, generations, calls = case; args = declared(args, tmp_path)
    originals = [p.read_bytes() for p in args['supplementary_phils']]
    m.initialize_dictionary_request(output=root, **args)
    result = m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    bundle = m.read_dictionary_request_result(root, 1)['preparation']['bundle']
    assert [p.read_bytes() for p in bundle['before_phils'][:2]] == originals
    assert [p.read_bytes() for p in bundle['after_phils'][:2]] == originals
    modifiers = [n for p in bundle['after_phils'] for n in _parse(p.read_text())[0]
                 if _path(n) == 'pdb_interpretation.apply_cif_modification']
    assert len(modifiers) == 4 and len({n['fields']['residue_selection'] for n in modifiers}) == 4
    before = inventory(root); root = root.rename(tmp_path/'relocated')
    args['model'].unlink(); shutil.rmtree(args['source_selection']); shutil.rmtree(store)
    for item in args['components']: shutil.rmtree(item['retained_snapshot'])
    for path in args['supplementary_phils']: path.unlink()
    with patch('subprocess.Popen', side_effect=AssertionError('Cold replay must not execute')):
        assert m.read_dictionary_request_result(root, 1)['result'] == result['result']
    assert inventory(root) == before


@pytest.mark.parametrize('defect', ['order', 'request', 'modifier_owner', 'native_claim', 'model', 'phi_hash',
    'context_absent', 'model_context_absent', 'native_absent', 'boolean_schema', 'new_target_rehashed'])
def test_rehashed_intent_mismatch_refuses_before_any_attempt(case, tmp_path, defect):
    m, args, root, sdk, store, generations, calls = case; args = declared(args, tmp_path)
    m.initialize_dictionary_request(output=root, **args)
    r = read_record(root/'request.json'); c = r['configuration']; proof = c['restraint_context']
    if defect == 'order': proof['inputs'].reverse()
    elif defect == 'request': proof['requests'][0]['distance_ideal'] += .1
    elif defect == 'modifier_owner': proof['site_modifier_owner'] = 'LEGACY_PROFILE'
    elif defect == 'native_claim': proof['native_membership'] = 'PASS'
    elif defect == 'model': proof['model_sha256'] = '0'*64
    elif defect == 'phi_hash': proof['inputs'][0]['sha256'] = '0'*64
    elif defect == 'context_absent': c.pop('restraint_context')
    elif defect == 'model_context_absent': c.pop('model_context')
    elif defect == 'native_absent': c['controls']['native_context']['custom_restraints'] = 'absent'
    elif defect == 'boolean_schema': proof['schema_version'] = True
    else:
        p = root/'inputs/phils/000.phil'; p.write_text(p.read_text().replace('distance_ideal = 2.91', 'distance_ideal = 3.91'))
        row = dict(sha256=sha256(p.read_bytes()).hexdigest(), size=p.stat().st_size)
        c['input_files']['phils/000.phil'] = row; proof['inputs'][0].update(row)
    write_record(root/'request.json', r, replace=True); before = inventory(root)
    with pytest.raises(ValueError): m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    assert inventory(root) == before and not calls and not (root/'attempts').exists()


def test_legacy_explicit_phil_and_c175_absent_mode_are_unchanged(case, tmp_path):
    m, args, root, sdk, store, generations, calls = case
    args = bind(args); plain = m.initialize_dictionary_request(output=root, **args)
    assert 'restraint_context' not in plain['configuration']
    args.pop('model_context'); args['supplementary_phils'] = phils(tmp_path)
    args['native_context']['custom_restraints'] = 'required'
    legacy = m.initialize_dictionary_request(output=tmp_path/'legacy', **args)
    assert 'restraint_context' not in legacy['configuration'] and 'model_context' not in legacy['configuration']
    assert m.inspect_dictionary_request(tmp_path/'legacy')['availability'] == 'AVAILABLE'
