"""Prepared-model context is derived, never inferred from numbering or NAR edges."""
from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch
import shutil

import pytest

from nasolve.campaign_records import read_record, write_record
from tests.test_cif_complete_request import case
from tests.test_cif_repair_attempt import inventory
from tests.test_phosphate import atom


def model(path, *, chains=(("A", "ZZZ"),), free=False, last=9):
    """Two geometrically linked sites per chain, with a numbering gap."""
    points = {"P": (0, 0, 0), "OP1": (-.5, 1.4, 0), "OP2": (-.5, -.7, 1.212),
              "O5'": (1.6, 0, 0), "OP3": (-.5, -.9, -1.2),
              "C5'": (2.9, 0, 0), "C3'": (4.2, 0, 1.2), "O3'": (5, 0, 0)}
    lines = []
    for index, (chain, code) in enumerate(chains):
        for number, shift in [(1, (0, index * 40, 0)), (last, (5.53, .76 + index * 40, 1.308))]:
            for name, xyz in points.items():
                if (number == last and name == 'OP3') or (free and number == 1 and name in {'P', 'OP1', 'OP2', 'OP3'}):
                    continue
                lines.append(atom(len(lines) + 1, name, code, chain, number,
                                  tuple(a + b for a, b in zip(xyz, shift))))
        lines.append('TER\n')
    path.write_text(''.join(lines) + 'END\n')
    return path


def report(*sites):
    return {'post_mr_plan': {'allow_op3_sites': list(sites), 'phosphate_intent': {
        'schema_version': 1, 'source': 'dataset' if sites else 'none',
        'allow_op3_sites': list(sites), 'recipe': None}}}


def bind(args):
    from nasolve.cif_model_context import derive_prepared_model_context
    args = deepcopy(args)
    model(args['model'], chains=(('A', 'ZZZ'), ('B', 'YYY')), last=2)
    saved = derive_prepared_model_context(args['model'], report('A:1', 'B:1'), ['ZZZ', 'YYY'])
    args['model_context'] = saved
    args['expected_links'] = saved['expected_links']
    for item in args['components']:
        item['contexts'] = saved['contexts'][item['code']]
    return args


def test_derivation_covers_selected_sites_and_whole_model_links_read_only(tmp_path):
    from nasolve.cif_model_context import derive_prepared_model_context, validate_prepared_model_context
    path = model(tmp_path/'model.pdb', chains=(('A', 'ZZZ'), ('B', 'YYY')))
    intent = report('A:1', 'B:1')
    intent['post_mr_plan']['stack_edges'] = [['A:9', 'B:1']]
    before = inventory(tmp_path); original = deepcopy(intent)
    with patch('subprocess.Popen', side_effect=AssertionError('Derivation must not execute')):
        saved = derive_prepared_model_context(path, intent, ['YYY'])
        assert validate_prepared_model_context(path, saved) == saved
    assert saved['components'] == ['YYY'] and set(saved['contexts']) == {'YYY'}
    assert saved['expected_links'] == [['A:1', 'A:9'], ['B:1', 'B:9']]
    assert saved['contexts']['YYY'] == [
        dict(site='B:1', incoming_site=None, outgoing_site='B:9', five_prime_state='phosphate', three_prime_state='linked'),
        dict(site='B:9', incoming_site='B:1', outgoing_site=None, five_prime_state='linked', three_prime_state='free_OH')]
    assert saved['model_sha256'] == sha256(path.read_bytes()).hexdigest()
    assert 'stack_edges' not in saved['intent']['post_mr_plan']
    assert saved['scientific_qualification'] == 'NOT_ASSESSED'
    assert inventory(tmp_path) == before and intent == original


def test_five_prime_hydroxyl_uses_the_other_sites_verified_incoming_link(tmp_path):
    from nasolve.cif_model_context import derive_prepared_model_context
    path = model(tmp_path/'model.pdb', free=True)
    saved = derive_prepared_model_context(path, report(), ['ZZZ'])
    first, last = saved['contexts']['ZZZ']
    assert first['five_prime_state'] == 'free_OH' and first['outgoing_site'] == 'A:9'
    assert last['incoming_site'] == 'A:1' and saved['expected_links'] == [['A:1', 'A:9']]


@pytest.mark.parametrize('defect', ['no_consent', 'internal_consent', 'extra_op3', 'missing_terminal_op3',
    'bad_geometry', 'alternate', 'insertion', 'multiple_models', 'ter_boundary', 'alias',
    'missing_sugar', 'ambiguous_incoming', 'inorganic_phosphate', 'symmetry_link', 'cycle'])
def test_ambiguous_or_unsupported_chemistry_refuses_without_editing(tmp_path, defect):
    from nasolve.cif_model_context import derive_prepared_model_context
    path = model(tmp_path/'model.pdb'); intent = report('A:1'); lines = path.read_text().splitlines(keepends=True)
    if defect == 'no_consent': intent = report()
    elif defect == 'internal_consent': intent = report('A:1', 'A:9')
    elif defect == 'extra_op3': lines.insert(-1, atom(90, 'OP3', 'ZZZ', 'A', 9, (5.03, -.14, .108)))
    elif defect == 'missing_terminal_op3': lines = [l for l in lines if l[12:16].strip() != 'OP3']
    elif defect == 'bad_geometry': lines = [l[:30] + f'{99.:8.3f}' + l[38:] if l[12:16].strip() == 'OP1' else l for l in lines]
    elif defect == 'alternate': lines[0] = lines[0][:16] + 'A' + lines[0][17:]
    elif defect == 'insertion': lines[0] = lines[0][:26] + 'A' + lines[0][27:]
    elif defect == 'multiple_models': lines = ['MODEL        1\n', *lines, 'ENDMDL\n', 'MODEL        2\n', 'ENDMDL\n']
    elif defect == 'ter_boundary': lines.insert(8, 'TER\n')
    elif defect == 'alias': lines = [l[:12] + ' O1P' + l[16:] if l[12:16].strip() == 'OP1' else l for l in lines]
    elif defect == 'missing_sugar': lines = [l for l in lines if l[12:16].strip() != "C5'"]
    elif defect == 'ambiguous_incoming': lines.insert(-1, atom(90, "O3'", 'DC', 'A', 3, (5, 0, 0)))
    elif defect == 'inorganic_phosphate': lines.insert(-1, atom(90, 'P', 'PO4', 'Z', 1, (90, 90, 90)))
    elif defect == 'symmetry_link':
        link = list(' ' * 80); link[:6] = 'LINK  '; link[12:16] = " O3'"; link[21] = 'A'; link[22:26] = '   1'
        link[42:46] = '   P'; link[51] = 'A'; link[52:56] = '   9'; link[66:72] = '  2555'
        lines.insert(0, ''.join(link) + '\n')
    else:
        intent = report(); lines = [l for l in lines if l[12:16].strip() != 'OP3']
        lines = [l[:30] + f'{-.53:8.3f}{-.76:8.3f}{-1.308:8.3f}' + l[54:]
                 if l[12:16].strip() == "O3'" and l[22:26].strip() == '9' else l for l in lines]
    path.write_text(''.join(lines)); before = inventory(tmp_path)
    with pytest.raises(ValueError): derive_prepared_model_context(path, intent, ['ZZZ'])
    assert inventory(tmp_path) == before


@pytest.mark.parametrize('defect', ['missing_plan', 'passthrough', 'phosphate_disagreement', 'backbone_disagreement',
    'recipe_disagreement', 'absent_site', 'unknown_code', 'duplicate_code', 'empty_codes'])
def test_frozen_intent_and_component_coverage_are_required(tmp_path, defect):
    from nasolve.backbone import make_backbone_policy
    from nasolve.cif_model_context import derive_prepared_model_context
    path = model(tmp_path/'model.pdb'); intent = report('A:1'); codes = ['ZZZ']
    if defect == 'missing_plan': intent = {}
    elif defect == 'passthrough': intent['post_mr_plan']['backbone_policy'] = make_backbone_policy({'A:9': 'experimental_passthrough'}, allow_unreviewed=True)
    elif defect == 'phosphate_disagreement': intent['postmr'] = {'phosphate_policy': {'mode': 'op3-explicit-opt-in-v1', 'allow_op3_sites': []}}
    elif defect == 'backbone_disagreement': intent['postmr'] = {'backbone_chemistry': {'schema_version': 1, 'default': 'standard_phosphodiester', 'sites': {'A:9': 'experimental_passthrough'}, 'experimental_passthrough_sites': ['A:9']}}
    elif defect == 'recipe_disagreement': intent['post_mr_plan']['phosphate_intent']['allow_op3_sites'] = []
    elif defect == 'absent_site': intent = report('A:1', 'Z:99')
    elif defect == 'unknown_code': codes = ['XXX']
    elif defect == 'duplicate_code': codes = ['ZZZ', 'ZZZ']
    else: codes = []
    with pytest.raises(ValueError): derive_prepared_model_context(path, intent, codes)


def test_request_replays_derived_intent_after_original_paths_disappear(case, tmp_path):
    m, args, root, sdk, store, generations, calls = case; args = bind(args)
    m.initialize_dictionary_request(output=root, **args)
    result = m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    assert result['result']['selected_attempts'] == {'YYY': 1, 'ZZZ': 1}
    assert m.inspect_dictionary_request(root)['request']['configuration']['model_context'] == args['model_context']
    before = inventory(root); root = root.rename(tmp_path/'relocated')
    shutil.rmtree(args['source_selection']); args['model'].unlink(); shutil.rmtree(store)
    for item in args['components']: shutil.rmtree(item['retained_snapshot'])
    with patch('subprocess.Popen', side_effect=AssertionError('Cold replay must not execute')):
        assert m.read_dictionary_request_result(root, 1)['result'] == result['result']
    assert inventory(root) == before


@pytest.mark.parametrize('defect', ['links', 'contexts', 'proof', 'model', 'policy', 'consent', 'numeric_bool'])
def test_rehashed_context_tampering_blocks_before_reservation(case, defect):
    m, args, root, sdk, store, generations, calls = case; args = bind(args)
    m.initialize_dictionary_request(output=root, **args)
    r = read_record(root/'request.json'); c = r['configuration']; proof = c['model_context']
    if defect == 'links': c['controls']['expected_links'] = []
    elif defect == 'contexts': c['controls']['sites']['ZZZ']['contexts'][0]['outgoing_site'] = None
    elif defect == 'proof': proof['expected_links'] = []
    elif defect == 'model':
        p = root/'inputs/model.pdb'; p.write_bytes(p.read_bytes() + b'REMARK changed\n')
        c['input_files']['model.pdb'] = {'sha256': sha256(p.read_bytes()).hexdigest(), 'size': p.stat().st_size}
    elif defect == 'policy': proof['policy_id'] = 'unknown'
    elif defect == 'consent': proof['intent']['post_mr_plan']['allow_op3_sites'] = []
    else: proof['schema_version'] = True
    r.pop('record_sha256'); write_record(root/'request.json', r, replace=True)
    before = inventory(root)
    with pytest.raises(ValueError): m.inspect_dictionary_request(root)
    with pytest.raises(ValueError): m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    assert inventory(root) == before and not calls and not (root/'attempts').exists()


@pytest.mark.parametrize('restraints', ['required', 'modifier_phil', 'nar_phil'])
def test_context_bridge_does_not_claim_unimplemented_shared_phil_ownership(case, tmp_path, restraints):
    m, args, root, sdk, store, generations, calls = case; args = bind(args)
    if restraints == 'required': args['native_context']['custom_restraints'] = 'required'
    else:
        path = tmp_path/'extra.phil'
        path.write_text('apply_cif_modification { }\n' if restraints == 'modifier_phil' else 'geometry_restraints { edits { } }\n')
        args['supplementary_phils'] = [path]
    with pytest.raises(ValueError): m.initialize_dictionary_request(output=root, **args)
    assert not (root/'request.json').exists() and not (root/'attempts').exists() and not calls
