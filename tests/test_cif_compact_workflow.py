"""Fresh ordinary requests freeze compact storage; saved requests keep their choice."""
import json
import pytest
from nasolve.campaign_records import read_record
from tests.test_cif_complete_request import case
from tests.test_cif_repair_attempt import setup
from tests.test_cif_prepared_repair_execution import case as prepared_case


def test_fresh_complete_request_defaults_to_compact_evidence(case):
    m,args,root,sdk,store,generations,calls=case;args=dict(args);args.pop('compact_evidence',None)
    q=m.initialize_dictionary_request(output=root,**args)
    assert q['configuration']['compact_evidence'] is True
    assert m.inspect_dictionary_request(root)['request']['configuration']['compact_evidence'] is True


@pytest.mark.parametrize('compact',[False,True])
def test_complete_request_forwards_same_frozen_choice_to_repair_and_continuation(case,monkeypatch,compact):
    m,args,root,sdk,store,generations,calls=case;args=dict(args);args.pop('compact_evidence',None)
    from nasolve import cif_repair_attempt as repair
    original=repair.execute_prepared_dictionary_repair;seen=[]
    def execute(*a,**k):
        seen.append(k.get('compact_evidence',False));r=original(*a,**k)
        if k.get('compact_evidence'):r['compact_evidence']=True;(a[2]/'repair_execution.json').write_text(json.dumps(r))
        return r
    monkeypatch.setattr(repair,'execute_prepared_dictionary_repair',execute)
    q=m.initialize_dictionary_request(output=root,compact_evidence=compact,
        continuation_options=dict(readyset_timeout_seconds=10,restore_serialization=True),**args)
    assert m._continuation_parameters(q['configuration']).get('compact_evidence',False) is compact
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    config=read_record(root/'attempts/attempt-0001/repair/request.json')['configuration']
    assert config.get('compact_evidence',False) is compact and seen==[compact]
    if not compact:assert 'compact_evidence' not in config and 'compact_evidence' not in q['configuration']
    m.read_dictionary_request_result(root,1)


@pytest.mark.parametrize('value',[1,None,'yes'])
def test_unknown_storage_choice_refuses_before_complete_request_freezing(case,value):
    m,args,root,sdk,store,generations,calls=case;args=dict(args);args.pop('compact_evidence',None)
    with pytest.raises(ValueError):m.initialize_dictionary_request(output=root,compact_evidence=value,**args)
    assert not root.exists() and not calls


def test_repair_request_preserves_storage_choice_across_fresh_attempts(setup,monkeypatch):
    m,args,options,calls=setup;original=m.execute_prepared_dictionary_repair;seen=[]
    def execute(*a,**k):
        seen.append(k.get('compact_evidence',False));r=original(*a,**k)
        if k.get('compact_evidence'):r['compact_evidence']=True;(a[2]/'repair_execution.json').write_text(json.dumps(r))
        return r
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',execute)
    first=m.execute_prepared_dictionary_repair_attempt(*args,compact_evidence=True,**options)
    assert first['execution']['compact_evidence'] is True
    with pytest.raises(ValueError,match='identity differs'):
        m.execute_prepared_dictionary_repair_attempt(*args,compact_evidence=False,**options)
    assert len(calls)==1
    second=m.execute_prepared_dictionary_repair_attempt(*args,compact_evidence=True,**options)
    assert second['attempt_number']==2 and seen==[True,True]


def test_missing_execution_storage_binding_cannot_seal_a_compact_request(setup):
    m,args,options,calls=setup
    # The old synthetic executor deliberately omits the new recorded choice.
    with pytest.raises(ValueError,match='storage'):
        m.execute_prepared_dictionary_repair_attempt(*args,compact_evidence=True,**options)
    assert not (args[-1]/'attempts/attempt-0001/finished.json').exists()


def test_existing_repair_executor_publishes_compact_result_without_new_owner(prepared_case,monkeypatch):
    m,b,sdk,out,state,calls,options=prepared_case
    publish=m.prepare_repaired_component_runtime_bundle;seen=[]
    def compact(output,**k):
        seen.append(k.pop('compact_evidence',False));r=publish(output,**k)
        r['evidence_storage']={'synthetic':'compact'};(output/'runtime_bundle.json').write_text(json.dumps(r));return r
    monkeypatch.setattr(m,'prepare_repaired_component_runtime_bundle',compact)
    r=m.execute_prepared_dictionary_repair(b,sdk,out,compact_evidence=True,**options)
    assert r['compact_evidence'] is True and r['status']=='QUALIFIED_DIAGNOSTIC_RUNTIME'
    assert seen==[True]
