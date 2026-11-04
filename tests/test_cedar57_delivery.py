"""C56 saved-data boundary; native/earlier capsule checks have separate tests."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest


def fake_return(monkeypatch):
    p=Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py';m=importlib.util.module_from_spec(spec:=importlib.util.spec_from_file_location('cedar57',p));spec.loader.exec_module(m)
    cases={code:{'explicit_fake':code,'decision':'CONTINUE_WITH_NOTES'} for code in ['DP','PDU','5PC']}
    audit={'policy_id':'cif-isolated-candidate-native-usability-v2','scope':'ISOLATED_COMPONENT_ONLY','captured_native_interpretations_replayed':6,
        'captured_native_energy_calls':12,'cases':deepcopy(cases),'automatic_adoption':False,'requires_cif_review':False}
    audit.update({k:'NOT_RUN' for k in ['native_execution','dictionary_generation','model_optimization','captured_code_execution','linked_adoption']})
    r={'build':{'explicit_fake':'TEST_BUILD'},'delivery_prefix':'56_Cedar','requested_action':'SAVED_ISOLATED_CANDIDATE_NATIVE_USABILITY','status':'REVIEW',
        'policy_authority':'NARestraints','requires_cif_review':False,'automatic_adoption':False,'saved_candidate_usability_audit':audit,
        'prior_archive':{'sha256':m.CEDAR55_SHA256,'verified_payloads':2760}}
    r.update({k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']})
    r.update({k:'NOT_RUN' for k in ['native_execution','dictionary_generation','model_editing','model_optimization','linked_site_validation','refinement','readyset_retry','installed_phenix_edits']})
    m.CEDAR56_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar55_members',lambda members:('qualified','prior','rotation'))
    monkeypatch.setattr(m,'_replay_saved_usability',lambda members:deepcopy(cases))
    return m,r


def members_for(r):
    members={'probe_receipt.json':json.dumps(r).encode(),'saved_candidate_usability_audit.json':json.dumps(r['saved_candidate_usability_audit']).encode(),
        'inputs/review/probe_receipt.json':b'{"explicit_fake":"parent boundary validated separately"}'}
    for i in range(2774-len(members)):members['padding/'+str(i)]=b'EXPLICIT_FAKE_PADDING'
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    return members


@pytest.mark.parametrize('defect',['none','build','action','lineage','preservation','native','calls','captured_code','decision','candidate_scope','adoption','different_report'])
def test_exact_saved_return_counts_decisions_and_nonexecution_remain_required(monkeypatch,defect):
    m,r=fake_return(monkeypatch);a=r['saved_candidate_usability_audit']
    if defect=='build':r['build']['changed']=True
    if defect=='action':r['requested_action']='RUN_GENERATOR'
    if defect=='lineage':r['prior_archive']['sha256']='a'*64
    if defect=='preservation':r['frozen_inputs_preserved']=False
    if defect=='native':r['native_execution']='COMPLETED'
    if defect=='calls':a['captured_native_energy_calls']=13
    if defect=='captured_code':a['captured_code_execution']='COMPLETED'
    if defect=='decision':a['cases']['DP']['decision']='HIDDEN_FAILURE'
    if defect=='candidate_scope':a['cases'].pop('5PC')
    if defect=='adoption':a['automatic_adoption']=True
    members=members_for(r)
    if defect=='different_report':
        members['saved_candidate_usability_audit.json']=b'{}';table={n:d for n,d in members.items() if n!='manifest.json'}
        members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in table.items()}).encode()
    if defect=='none':assert m._read_cedar56_members(members)==('qualified','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar56_members(members)


@pytest.mark.parametrize('delivery,option',[('56_Cedar','source_dna_metadata_only'),('55_Cedar','saved_native_usability_only'),('54_Cedar','candidate_native_usability_only')])
def test_source_metadata_action_is_separate_from_saved_and_new_native_usability(monkeypatch,delivery,option):
    m,_=fake_return(monkeypatch);args=SimpleNamespace(**{option:True});m._check_constructor_input_mode(args,delivery)
    args.source_dna_metadata_only=not getattr(args,'source_dna_metadata_only',False)
    with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
