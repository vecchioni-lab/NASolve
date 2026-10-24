from types import SimpleNamespace
from hashlib import sha256
import json
import pytest
from tests.test_cedar66_delivery import template


@pytest.mark.parametrize('delivery,action,ok',[
    ('71_Cedar','postmr_readyset_consumption_only',True),
    ('70_Cedar','postmr_readyset_consumption_only',False),
    ('71_Cedar','postmr_dictionary_reuse_only',False)])
def test_readyset_consumption_has_exact_successful_parent(delivery,action,ok):
    m=template();args=SimpleNamespace(**{action:True})
    if ok:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)


def test_c71_reader_and_replay_are_available():
    m=template()
    assert callable(m._read_cedar71_members) and callable(m._replay_cedar71_return)


@pytest.mark.parametrize('defect',['none','build','action','calls','parent','status','student','adoption','preserved','replay','report','readyset'])
def test_completed_c71_reader_rejects_changed_scope(monkeypatch,defect):
    m=template()
    a={'policy_id':'cif-postmr-cache-handoff-controls-v1','status':'POSTMR_CACHE_HANDOFF_PASS','new_native_calls':3,
       'source_selection':'CURRENT_CONFIGURED_INSTALLATION','production_checkpoint':'NOT_CREATED','requires_cif_review':False,
       'scope':'ORDINARY_DICTIONARY_ACQUISITION_AND_ISOLATED_NORMALIZED_NATIVE_INPUTS; FULL_POSTMR_RUN_REMAINS_SEPARATE',
       'cases':{c:{} for c in ['DP','PDU','5PC']},
       **{k:'NOT_RUN' for k in ['dictionary_generation','model_optimization','coot_execution','readyset_execution','refinement']}}
    r={'delivery_prefix':'71_Cedar','kind':'cif-source-graph-numerical-recovery-probe','build':{'EXPLICIT_FAKE':'C71'},
       'requested_action':'ORDINARY_POSTMR_DICTIONARY_REUSE','status':'REVIEW','native_execution':'FIXED_ISOLATED_POSTMR_INPUT_READBACK',
       'prior_archive':{'sha256':m.CEDAR70_SHA256,'verified_payloads':4008},
       'requires_cif_review':False,'automatic_adoption':False,'policy_authority':'NARestraints',
       **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
       **{k:'NOT_RUN' for k in ['model_editing','model_optimization','dictionary_generation','policy_recompilation','refinement','readyset_retry','installed_phenix_edits','scientific_approval','linked_site_validation']},
       'postmr_dictionary_reuse_audit':a}
    m.CEDAR71_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar70_members',lambda x:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar71_return',lambda *a:defect!='replay')
    if defect=='build':r['build']['changed']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='calls':a['new_native_calls']=4
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='status':a['status']='REVIEW'
    if defect=='student':r['requires_cif_review']=True
    if defect=='adoption':a['production_checkpoint']='CREATED'
    if defect=='preserved':r['frozen_inputs_preserved']=False
    if defect=='readyset':a['readyset_execution']='RAN'
    members={'probe_receipt.json':json.dumps(r).encode(),'postmr_dictionary_reuse_audit.json':json.dumps(a).encode()}
    if defect=='report':members['postmr_dictionary_reuse_audit.json']=b'{}'
    members.update({'padding/'+str(n):b'EXPLICIT_FAKE' for n in range(4231-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar71_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar71_members(members)
