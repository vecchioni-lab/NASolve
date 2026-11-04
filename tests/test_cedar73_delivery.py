from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from tests.test_cedar66_delivery import template


@pytest.mark.parametrize('delivery,action,ok',[
    ('72_Cedar','postmr_readyset_consumption_only',True),
    ('71_Cedar','postmr_readyset_consumption_only',True),
    ('72_Cedar','postmr_dictionary_reuse_only',False)])
def test_consumption_retry_requires_explicit_supported_input(delivery,action,ok):
    m=template();args=SimpleNamespace(**{action:True})
    if ok:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)


@pytest.mark.parametrize('defect',['none','build','action','error','completed','archive','inputs_flag','policy','parent','replay','native','report','status'])
def test_failed_c72_reader_preserves_exact_prelaunch_failure(monkeypatch,defect):
    m=template()
    r={'delivery_prefix':'72_Cedar','kind':'cif-source-graph-numerical-recovery-probe','build':{'EXPLICIT_FAKE':'C72'},
       'requested_action':'ORDINARY_POSTMR_READYSET_CONSUMPTION','status':'REVIEW',
       'error':'Incomplete ReadySet builder source coverage','analysis_completed':False,'frozen_inputs_preserved':False,
       'original_archive_preserved':True,'prerequisite_mechanics_replayed':True,'automatic_adoption':False,'policy_authority':'NARestraints',
       'prior_archive':{'sha256':m.CEDAR71_SHA256,'verified_payloads':4231},
       **{k:'NOT_RUN' for k in ['native_execution','model_editing','model_optimization','dictionary_generation','policy_recompilation','refinement','readyset_retry','installed_phenix_edits','scientific_approval','linked_site_validation']}}
    m.CEDAR72_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar71_members',lambda x:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar72_failure',lambda *a:defect!='replay')
    if defect=='build':r['build']['changed']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='error':r['error']='Another failure'
    if defect=='completed':r['analysis_completed']=True
    if defect=='archive':r['original_archive_preserved']=False
    if defect=='inputs_flag':r['frozen_inputs_preserved']=True
    if defect=='policy':r['policy_authority']='NATIVE_GUESSED_SS'
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='native':r['native_execution']='RAN'
    if defect=='report':r['postmr_readyset_consumption_audit']={}
    if defect=='status':r['status']='PASS'
    members={'probe_receipt.json':json.dumps(r).encode()}
    members.update({'padding/'+str(n):b'EXPLICIT_FAKE' for n in range(4482-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar72_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar72_members(members)
