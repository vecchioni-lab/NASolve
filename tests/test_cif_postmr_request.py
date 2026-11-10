"""Ordinary-source entry delegates to the existing owner without weakening proof."""
from copy import deepcopy
from unittest.mock import patch
import json
import shutil

import pytest

from tests.test_cif_complete_request import case
from tests.test_cif_model_context import bind
from tests.test_cif_restraint_context import phils
from tests.test_cif_repair_attempt import inventory


@pytest.fixture
def entry_case(case, tmp_path, monkeypatch):
    from nasolve import cif_repair_attempt as repair
    m, args, root, sdk, store, generations, calls = case
    args = bind(args)
    kwargs = dict(model=args['model'], report=args['model_context']['intent'],
        components=[{k:v for k,v in item.items() if k != 'contexts'} for item in args['components']],
        source_output=tmp_path/'entry-sources', output=root, consumer=args['consumer'],
        ready_set_executable=sdk.executables['phenix.ready_set'], data_root=tmp_path/'data',
        supplementary_phils=phils(tmp_path), total_timeout_seconds=60,
        component_timeout_seconds=30, max_attempts=2)
    # Synthetic transport cannot qualify a scientific runtime. Retain the real
    # owner/children and return an explicit no-usable result under new defaults.
    old = repair.execute_prepared_dictionary_repair
    def execute(*a, **k):
        assert k['qualify_no_repair'] is True and k['optional_failure_policy'] == repair.FALLBACK_POLICY_ID
        result = old(*a, **k)
        result.update(status='NO_USABLE_BUNDLE', qualify_no_repair=True,
                      optional_failure_policy=k['optional_failure_policy'])
        (a[2]/'repair_execution.json').write_text(json.dumps(result))
        return result
    monkeypatch.setattr(repair, 'execute_prepared_dictionary_repair', execute)
    return m, kwargs, sdk, store, generations, calls


def test_entry_freezes_ordinary_sources_and_both_derived_contexts_without_execution(entry_case):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, sdk, store, generations, calls = entry_case
    prior = deepcopy(args); files = inventory(args['data_root'])
    with patch('subprocess.Popen', side_effect=AssertionError('Initializer must not execute')):
        request = initialize_postmr_dictionary_request(**args)
    assert args == prior and inventory(args['data_root']) == files
    c = request['configuration']
    assert c['model_context']['components'] == ['YYY', 'ZZZ']
    assert c['model_context']['expected_links'] == [['A:1', 'A:2'], ['B:1', 'B:2']]
    assert c['restraint_context']['request_counts'] == {'angle':1, 'bond':1, 'parallelity':1}
    assert c['controls']['native_context'] == dict(policy_id='cif-explicit-site-native-context-v2',
        monomer_inventory='full_model', custom_restraints='required')
    assert c['qualify_no_repair'] is True and c['optional_failure_policy']
    assert len(c['controls']['sites']['ZZZ']['contexts']) == 2
    assert m.inspect_dictionary_request(args['output'])['attempts'] == []
    assert not store.exists() and not calls


@pytest.mark.parametrize('kind', ['retained', 'current_cache'])
def test_entry_uses_existing_cache_owner_and_keeps_fresh_attempts_cold(entry_case, kind, monkeypatch):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot, make_dictionary_request, publish_dictionary
    from nasolve.cif_generation_acquisition import generation_dictionary_options
    from nasolve import cif_postmr_cache
    m, args, sdk, store, generations, calls = entry_case
    if kind == 'current_cache':
        for item in args['components']:
            saved = resolve_dictionary_snapshot(item.pop('retained_snapshot'))
            req = make_dictionary_request(saved['source'], item['code'], source_authority='EXPLICIT',
                                          **generation_dictionary_options(item['generation']))
            publish_dictionary(store, req, saved['source'], saved['dictionary'], saved['qualification'],
                               consumer=args['consumer'], provenance=saved['provenance'])
    def forbidden(*a, **k): raise AssertionError('Entry must reuse the complete owner, not the old reuse-only filter')
    monkeypatch.setattr(cif_postmr_cache, 'prepare_postmr_dictionaries', forbidden)
    monkeypatch.setattr(m.acquisition, 'generate_source_candidate_attempt', forbidden)
    initialize_postmr_dictionary_request(**args); root = args['output']
    first = m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    old = inventory(root/'attempts/attempt-0001')
    second = m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    state = m.inspect_dictionary_request(root)
    assert first['attempt_id'] != second['attempt_id'] and len(state['attempts']) == 2
    assert all(a['state'] == 'STOPPED' for a in state['attempts'])
    assert second['result']['status'] == 'NO_USABLE_BUNDLE' and second['result']['automatic_adoption'] is False
    assert inventory(root/'attempts/attempt-0001') == old and len(calls) == 2
    assert not any((root/'acquisitions'/code/'generation').exists() for code in generations)
    if kind == 'current_cache':
        for code in generations:
            assert m.acquisition.read_acquisition_result(root/'acquisitions'/code, 1)['report']['status'] == 'REUSED'
    before = inventory(root); moved = root.rename(root.with_name('moved'))
    shutil.rmtree(args['data_root']); shutil.rmtree(args['source_output']); shutil.rmtree(store)
    args['model'].unlink()
    for p in args['supplementary_phils']: p.unlink()
    for item in args['components']:
        if 'retained_snapshot' in item: shutil.rmtree(item['retained_snapshot'])
    with patch('subprocess.Popen', side_effect=AssertionError('Cold replay must not execute')):
        assert m.read_dictionary_request_result(moved, 2)['result'] == second['result']
    assert inventory(moved) == before


def test_explicit_empty_phil_uses_existing_absent_contract(entry_case):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, *_ = entry_case; args['supplementary_phils'] = []
    c = initialize_postmr_dictionary_request(**args)['configuration']
    assert c['controls']['native_context']['custom_restraints'] == 'absent'
    assert 'restraint_context' not in c and c['model_context']


@pytest.mark.parametrize('defect', ['manual_context', 'duplicate', 'absent_code', 'generation', 'no_consent',
    'modifier', 'unordered_phils', 'qualify_override', 'failure_override', 'context_override',
    'unknown_limit', 'boolean_limit', 'zero_limit', 'oversized_limit', 'empty_components'])
def test_invalid_entry_intent_refuses_before_sources_or_attempts(entry_case, defect):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, sdk, store, generations, calls = entry_case
    if defect == 'manual_context': args['components'][0]['contexts'] = []
    elif defect == 'duplicate': args['components'].append(deepcopy(args['components'][0]))
    elif defect == 'absent_code': args['components'][0]['code'] = 'QQQ'
    elif defect == 'generation': args['components'][0]['generation']['expected_dialect'] = None
    elif defect == 'no_consent': args['report'] = {'post_mr_plan':{}}
    elif defect == 'modifier': args['supplementary_phils'][0].write_text('refinement.pdb_interpretation.apply_cif_modification {\n data_mod = OLD\n residue_selection = chain A and resid 1\n}\n')
    elif defect == 'unordered_phils': args['supplementary_phils'] = set(args['supplementary_phils'])
    elif defect == 'qualify_override': args['qualify_no_repair'] = False
    elif defect == 'failure_override': args['optional_failure_policy'] = None
    elif defect == 'context_override': args['native_context'] = {}
    elif defect == 'unknown_limit': args['timeout'] = 90
    elif defect == 'boolean_limit': args['max_attempts'] = True
    elif defect == 'zero_limit': args['max_attempts'] = 0
    elif defect == 'oversized_limit': args['native_timeout_seconds'] = 601
    elif defect == 'empty_components': args['components'] = []
    before = inventory(args['output'].parent)
    with pytest.raises(ValueError): initialize_postmr_dictionary_request(**args)
    assert inventory(args['output'].parent) == before and not store.exists() and not calls


@pytest.mark.parametrize('where', ['same', 'nested', 'input_parent', 'retained_child', 'sdk_child',
    'data_child', 'existing_source', 'existing_request', 'symlink'])
def test_entry_destinations_cannot_overlap_or_overwrite_inputs(entry_case, where):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, sdk, store, generations, calls = entry_case
    if where == 'same': args['source_output'] = args['output']
    elif where == 'nested': args['source_output'] = args['output']/'sources'
    elif where == 'input_parent': args['source_output'] = args['model'].parent
    elif where == 'retained_child': args['source_output'] = args['components'][0]['retained_snapshot']/'extra'
    elif where == 'sdk_child': args['output'] = sdk.root/'request'
    elif where == 'data_child': args['source_output'] = args['data_root']/'output'
    elif where == 'existing_source': args['source_output'].mkdir()
    elif where == 'existing_request': args['output'].mkdir()
    elif where == 'symlink': args['source_output'].symlink_to(args['output'].parent/'absent', target_is_directory=True)
    before = inventory(sdk.root.parent)
    with pytest.raises((ValueError, FileExistsError)): initialize_postmr_dictionary_request(**args)
    assert inventory(sdk.root.parent) == before and not calls


@pytest.mark.parametrize('changed', ['model', 'phil'])
def test_input_change_after_source_freeze_retains_partial_work_without_request(entry_case, monkeypatch, changed):
    from nasolve import cif_postmr_request as entry
    m, args, sdk, store, generations, calls = entry_case
    original = entry.freeze_acquisition_sources
    def change(*a, **k):
        result = original(*a, **k)
        p = args['model'] if changed == 'model' else args['supplementary_phils'][0]
        p.write_bytes(p.read_bytes() + b'\n# CHANGED AFTER PREFLIGHT\n')
        return result
    monkeypatch.setattr(entry, 'freeze_acquisition_sources', change)
    with pytest.raises(ValueError): entry.initialize_postmr_dictionary_request(**args)
    assert (args['source_output']/'source_selection.json').is_file()
    assert not (args['output']/'request.json').exists() and not (args['output']/'attempts').exists()
    assert not store.exists() and not calls


def test_failed_source_selection_never_falls_back_to_an_unrequested_source(entry_case):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, sdk, store, generations, calls = entry_case
    (args['data_root']/'ligands/ZZZ.cif').unlink()
    before = inventory(args['output'].parent)
    with pytest.raises((ValueError, FileNotFoundError)): initialize_postmr_dictionary_request(**args)
    assert inventory(args['output'].parent) == before and not calls
