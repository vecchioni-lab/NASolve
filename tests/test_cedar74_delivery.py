from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from tests.test_cedar66_delivery import template


@pytest.mark.parametrize('delivery,action,ok',[
    ('73_Cedar','postmr_readyset_consumption_only',True),
    ('73_Cedar','postmr_dictionary_reuse_only',False),
    ('75_Cedar','postmr_readyset_consumption_only',False)])
def test_subprocess_trace_uses_explicit_consumption_input(delivery,action,ok):
    m=template();args=SimpleNamespace(**{action:True})
    if ok:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)


@pytest.mark.parametrize('defect',['none','build','action','readyset_calls','native_calls','cases','native_label','parent',
    'report','status','preserved','student','adoption','policy','generation_claim','optimization_claim','replay'])
def test_c73_reader_retains_completed_but_unresolved_subprocess_evidence(monkeypatch,defect):
    m=template()
    a={'policy_id':'cif-postmr-readyset-consumption-controls-v1','status':'REVIEW',
       'new_readyset_calls':3,'new_native_calls':0,'requires_cif_review':False,'automatic_adoption':False,
       'production_checkpoint':'NOT_CREATED','cases':{c:{} for c in ['DP','PDU','5PC']}}
    r={'delivery_prefix':'73_Cedar','kind':'cif-source-graph-numerical-recovery-probe','build':{'EXPLICIT_FAKE':'C73'},
       'requested_action':'ORDINARY_POSTMR_READYSET_CONSUMPTION','status':'REVIEW',
       'requires_cif_review':False,'automatic_adoption':False,'policy_authority':'NARestraints',
       'native_execution':'ISOLATED_READYSET_CONSUMPTION_AND_EFFECTIVE_NATIVE_READBACK',
       'dictionary_generation':'NOT_OBSERVED_BY_SELECTED_BUILDER_TRACE',
       'model_optimization':'NOT_REQUESTED; NATIVE_INTERNALS_NOT_EXHAUSTIVELY_INSTRUMENTED',
       'readyset_retry':'ISOLATED_ORDINARY_ARGUMENTS_OBSERVED_ENTRYPOINT',
       'prior_archive':{'sha256':m.CEDAR72_SHA256,'verified_payloads':4482},
       **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
       **{k:'NOT_RUN' for k in ['model_editing','policy_recompilation','refinement','installed_phenix_edits','scientific_approval','linked_site_validation','native_proxy_validation']},
       'postmr_readyset_consumption_audit':a}
    m.CEDAR73_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar72_members',lambda x:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar73_return',lambda *a:defect!='replay')
    if defect=='build':r['build']['changed']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='readyset_calls':a['new_readyset_calls']=0
    if defect=='native_calls':a['new_native_calls']=3
    if defect=='cases':a['cases'].pop('DP')
    if defect=='native_label':r['native_execution']='COMPLETE_SCAFFOLD_NATIVE_PASS'
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='status':a['status']='PASS'
    if defect=='preserved':r['frozen_inputs_preserved']=False
    if defect=='student':r['requires_cif_review']=True
    if defect=='adoption':a['production_checkpoint']='CREATED'
    if defect=='policy':r['policy_authority']='NATIVE_GUESSED_SS'
    if defect=='generation_claim':r['dictionary_generation']='NO_INTERNAL_GENERATION_PROVED'
    if defect=='optimization_claim':r['model_optimization']='CONVERGED'
    members={'probe_receipt.json':json.dumps(r).encode(),'postmr_readyset_consumption_audit.json':json.dumps(a).encode()}
    if defect=='report':members['postmr_readyset_consumption_audit.json']=b'{}'
    members.update({'padding/'+str(n):b'EXPLICIT_FAKE' for n in range(4830-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar73_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar73_members(members)
