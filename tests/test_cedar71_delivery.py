"""The ordinary PostMR cache probe requires the exact completed C70 evidence."""
from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from tests.test_cedar66_delivery import template


@pytest.mark.parametrize('action,delivery,ok',[
    ('postmr_dictionary_reuse_only','70_Cedar',True),
    ('postmr_dictionary_reuse_only','69_Cedar',False),
    ('saved_source_reuse_only','70_Cedar',False)])
def test_postmr_cache_action_has_exact_parent(action,delivery,ok):
    m=template();args=SimpleNamespace(**{action:True})
    if ok:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)


@pytest.mark.parametrize('defect',['none','build','action','calls','parent','repeat','report','student','adoption','preserved','replay'])
def test_completed_c70_reader_preserves_scope(monkeypatch,defect):
    m=template()
    a={'policy_id':'cif-saved-source-reuse-v1','status':'SAVED_SOURCE_REUSE_PASS','new_native_calls':0,
       'qualification_adapter_calls':3,'source_selection':'REPLAY_OF_EXACT_C69_ORDINARY_SOURCE_AND_AUTHORITY',
       'native_evidence':'VERIFIED_C69_CAPTURE; NO_NEW_NATIVE_QUALIFICATION',
       'scope':'SOURCE_BOUND_ISOLATED_NUMERICS; CURRENT_INSTALLATION_LINKS_AND_MODEL_REMAIN_SEPARATE',
       'production_adoption':'NOT_RUN','requires_cif_review':False,
       'cases':{c:{'first':{'status':'SOURCE_REQUALIFIED_AND_FROZEN'},'repeat':{'status':'REUSED'},'exact_repeat':True,
                   'qualification_adapter_calls':1} for c in ['DP','PDU','5PC']}}
    r={'delivery_prefix':'70_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
       'build':{'FAKE':'C70'},'requested_action':'SAVED_ORDINARY_SOURCE_REUSE','status':'REVIEW',
       'prior_archive':{'sha256':'199a795df9d3d782192c459d0c754bb6ad68d22e7d5712c3eb6d2cf3248850e2','verified_payloads':3849},
       'requires_cif_review':False,'automatic_adoption':False,'policy_authority':'NARestraints',
       **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
       **{k:'NOT_RUN' for k in ['native_execution','model_editing','model_optimization','dictionary_generation','policy_recompilation','refinement','readyset_retry','installed_phenix_edits','scientific_approval','linked_site_validation']},
       'saved_source_reuse_audit':a}
    m.CEDAR70_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar69_members',lambda x:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar70_return',lambda *a:defect!='replay',raising=False)
    if defect=='build':r['build']['changed']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='calls':a['new_native_calls']=1
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='repeat':a['cases']['DP']['exact_repeat']=False
    if defect=='student':r['requires_cif_review']=True
    if defect=='adoption':a['production_adoption']='RAN'
    if defect=='preserved':r['frozen_inputs_preserved']=False
    members={'probe_receipt.json':json.dumps(r).encode(),'saved_source_reuse_audit.json':json.dumps(a).encode()}
    if defect=='report':members['saved_source_reuse_audit.json']=b'{}'
    members.update({'padding/'+str(n):b'EXPLICIT_FAKE' for n in range(4008-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar70_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar70_members(members)
