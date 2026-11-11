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


@pytest.fixture
def frozen_entry(entry_case, case):
    m, args, sdk, store, generations, calls = entry_case
    args.update(frozen_sources=case[1]['source_selection'], source_output=None,
                ready_set_executable=None, data_root=None)
    return entry_case


def test_frozen_source_entry_preserves_exact_authority_without_discovery(frozen_entry, case, monkeypatch):
    from nasolve import cif_postmr_request as entry
    m, args, sdk, store, generations, calls = frozen_entry
    original = inventory(args['frozen_sources'])
    shutil.rmtree(case[2].parent/'data')
    def forbidden(*a, **k): raise AssertionError('Frozen input must not rediscover sources')
    monkeypatch.setattr(entry, 'freeze_acquisition_sources', forbidden)
    with patch('subprocess.Popen', side_effect=AssertionError('Initialization must not execute')):
        request = entry.initialize_postmr_dictionary_request(**args)
    assert inventory(args['frozen_sources']) == original
    assert (args['output']/'inputs/sources/source_selection.json').read_bytes() == (args['frozen_sources']/'source_selection.json').read_bytes()
    assert request['configuration']['model_context']['components'] == ['YYY', 'ZZZ']
    assert m.inspect_dictionary_request(args['output'])['attempts'] == [] and not calls


def test_frozen_and_fresh_source_entry_produce_identical_owned_configuration(frozen_entry, case):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, sdk, *_ = frozen_entry
    frozen = initialize_postmr_dictionary_request(**args)
    fresh_args = deepcopy(args); fresh_args.pop('frozen_sources')
    fresh_args.update(source_output=case[2].parent/'fresh-sources', output=case[2].parent/'fresh-request',
                      data_root=case[2].parent/'data', ready_set_executable=sdk.executables['phenix.ready_set'])
    fresh = initialize_postmr_dictionary_request(**fresh_args)
    assert fresh['request_id'] != frozen['request_id']
    assert fresh['configuration'] == frozen['configuration']


def test_frozen_source_entry_owns_recovery_after_source_origin_disappears(frozen_entry, monkeypatch):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m, args, sdk, store, generations, calls = frozen_entry
    initialize_postmr_dictionary_request(**args); shutil.rmtree(args['frozen_sources'])
    def forbidden(*a, **k): raise AssertionError('Frozen request must not reselect or generate')
    monkeypatch.setattr(m.acquisition, 'generate_source_candidate_attempt', forbidden)
    root = args['output']; first = m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    before = inventory(root/'attempts/attempt-0001')
    second = m.execute_dictionary_request_attempt(root, sdk, store, generation=generations)
    assert second['attempt_id'] != first['attempt_id'] and second['result']['status'] == 'NO_USABLE_BUNDLE'
    assert inventory(root/'attempts/attempt-0001') == before
    assert all(a['state'] == 'STOPPED' for a in m.inspect_dictionary_request(root)['attempts'])
    moved = root.rename(root.with_name('relocated-request')); before = inventory(moved)
    with patch('subprocess.Popen', side_effect=AssertionError('Cold replay must not execute')):
        assert m.read_dictionary_request_result(moved, 2)['result'] == second['result']
    assert inventory(moved) == before


@pytest.mark.parametrize('defect', ['source_output', 'discovery_sdk', 'local_data', 'source_bytes',
    'component_set', 'symlink', 'missing_manifest', 'nested_output'])
def test_frozen_source_entry_refuses_conflicts_without_rediscovery(frozen_entry, case, monkeypatch, defect):
    from nasolve import cif_postmr_request as entry
    m, args, sdk, store, generations, calls = frozen_entry
    source = args['frozen_sources']
    if defect == 'source_output': args['source_output'] = case[2].parent/'competing-output'
    elif defect == 'discovery_sdk': args['ready_set_executable'] = sdk.executables['phenix.ready_set']
    elif defect == 'local_data': args['data_root'] = case[2].parent/'data'
    elif defect == 'source_bytes':
        p=source/'sources/ZZZ.cif'; p.write_bytes(p.read_bytes()+b'# changed source\n')
    elif defect == 'component_set': args['components'].pop()
    elif defect == 'symlink':
        link=source.with_name('source-link');link.symlink_to(source,target_is_directory=True);args['frozen_sources']=link
    elif defect == 'missing_manifest': (source/'source_selection.json').unlink()
    elif defect == 'nested_output': args['output'] = source/'nested'
    def forbidden(*a, **k): raise AssertionError('Invalid frozen input must never trigger source discovery')
    monkeypatch.setattr(entry, 'freeze_acquisition_sources', forbidden)
    before=inventory(case[2].parent)
    with pytest.raises((ValueError, FileNotFoundError)):
        entry.initialize_postmr_dictionary_request(**args)
    assert inventory(case[2].parent) == before and not calls


def test_frozen_source_changed_during_context_derivation_never_publishes_request(frozen_entry, monkeypatch):
    from nasolve import cif_postmr_request as entry
    m, args, *_ = frozen_entry; original = entry.derive_prepared_model_context
    def change(*a, **k):
        context=original(*a, **k);p=args['frozen_sources']/'sources/ZZZ.cif'
        p.write_bytes(p.read_bytes()+b'# changed while preparing context\n');return context
    monkeypatch.setattr(entry, 'derive_prepared_model_context', change)
    with pytest.raises(ValueError):entry.initialize_postmr_dictionary_request(**args)
    assert not args['output'].exists()


@pytest.fixture
def construction_entry(entry_case, tmp_path):
    """Synthetic producer transport; no Coot/native qualification is claimed."""
    from nasolve.postmr import MutationAction
    from nasolve.postmr_lineage import begin_postmr_construction, finish_postmr_construction
    m,args,sdk,store,generations,calls=entry_case
    run=tmp_path/'ordinary run'; models=run/'PostMR/Model'; models.mkdir(parents=True)
    sources=run/'PostMR/Coot/source_dictionaries'; sources.mkdir(parents=True)
    prepared=models/'prepared_model.pdb';prepared.write_bytes(args['model'].read_bytes())
    after=models/'after_coot.pdb';after.write_bytes(prepared.read_bytes())
    original=models/'mr_solution.pdb'
    lines=[]
    for line in prepared.read_text().splitlines(keepends=True):
        if line.startswith(('ATOM','HETATM')) and line[21:22]=='A' and line[22:26].strip()=='1':
            line=line[:17]+' DA'+line[20:]
        lines.append(line)
    original.write_text(''.join(lines))
    source=sources/'ZZZ.cif';source.write_bytes((args['data_root']/'ligands/ZZZ.cif').read_bytes())
    start=begin_postmr_construction(run,original,original,{'ZZZ':source},
        [MutationAction('A:1','DA','ZZZ','coot-parent-overlap',parent_code='DA')],
        allow_op3_sites=args['report']['post_mr_plan']['allow_op3_sites'])
    finish_postmr_construction(run,start,prepared,dict(model=after,raw_model=None,coot_log=None))
    (run/'unrelated-private-material').write_text('MUST NOT BE COPIED')
    args['construction_inputs']=run
    return entry_case


def test_prepared_request_freezes_only_declared_construction_closure(construction_entry):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    from nasolve.postmr_lineage import read_postmr_construction
    m,args,sdk,store,generations,calls=construction_entry
    original=inventory(args['construction_inputs'])
    declared=read_postmr_construction(args['construction_inputs'])['files']
    with patch('subprocess.Popen',side_effect=AssertionError('Initialization must not execute')):
        request=initialize_postmr_dictionary_request(**args)
    assert request['configuration']['construction_inputs']['path']=='inputs/construction'
    assert read_postmr_construction(args['output']/'inputs/construction')['files']==declared
    assert not (args['output']/'inputs/construction/unrelated-private-material').exists()
    assert inventory(args['construction_inputs'])==original and not calls
    assert m.inspect_dictionary_request(args['output'])['attempts']==[]


def test_construction_lineage_survives_owned_attempt_recovery_and_cold_move(construction_entry):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,sdk,store,generations,calls=construction_entry
    initialize_postmr_dictionary_request(**args)
    first=m.execute_dictionary_request_attempt(args['output'],sdk,store,generation=generations)
    previous=inventory(args['output']/'attempts/attempt-0001')
    second=m.execute_dictionary_request_attempt(args['output'],sdk,store,generation=generations)
    assert first['attempt_id']!=second['attempt_id']
    assert inventory(args['output']/'attempts/attempt-0001')==previous
    assert second['result']['construction_inputs']['path']=='inputs/construction'
    assert not (args['output']/'attempts/attempt-0001/preparation/inputs/construction').exists()
    before=inventory(args['output']);moved=args['output'].rename(args['output'].with_name('relocated request'))
    shutil.rmtree(args['construction_inputs']);shutil.rmtree(args['data_root']);shutil.rmtree(args['source_output'])
    args['model'].unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Cold replay cannot execute')):
        state=m.inspect_dictionary_request(moved)
        result=m.read_dictionary_request_result(moved,2)
    assert all(a['state']=='STOPPED' for a in state['attempts'])
    assert result['construction_inputs']['model'].is_file()
    assert inventory(moved)==before


@pytest.mark.parametrize('problem',['model','source','policy','missing-record'])
def test_prepared_request_rejects_unbound_construction_before_attempt(construction_entry, problem):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    from nasolve.campaign_records import write_record
    m,args,sdk,store,generations,calls=construction_entry
    run=args['construction_inputs'];record=run/'PostMR/Coot/construction.json'
    if problem=='model':args['model'].write_bytes(args['model'].read_bytes()+b'\n')
    elif problem=='source':
        p=args['data_root']/'ligands/ZZZ.cif';p.write_bytes(p.read_bytes()+b'\n')
    elif problem=='policy':
        r=json.loads(record.read_bytes());r.pop('record_sha256');r['controls']['allow_op3_sites']=['A:1']
        record.unlink();write_record(record,r)
    else:record.unlink()
    with pytest.raises((ValueError,OSError)):
        initialize_postmr_dictionary_request(**args)
    assert not (args['output']/'attempts').exists() and not calls


def test_construction_source_change_during_request_freezing_refuses(construction_entry, monkeypatch):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    m,args,sdk,store,generations,calls=construction_entry
    original=m._freeze
    def changed(*a,**k):
        original(*a,**k)
        p=args['construction_inputs']/'PostMR/Model/prepared_model.pdb'
        p.write_bytes(p.read_bytes()+b'\n')
    monkeypatch.setattr(m,'_freeze',changed)
    with pytest.raises(ValueError,match='source changed'):
        initialize_postmr_dictionary_request(**args)
    assert not (args['output']/'request.json').exists() and not calls
