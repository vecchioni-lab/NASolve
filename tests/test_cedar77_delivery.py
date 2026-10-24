"""C77 preserves the C76 native pass and failed builder guard as immutable data."""
from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from tests.test_cedar65_delivery import template


@pytest.mark.parametrize('action,delivery,valid',[
    ('postmr_cached_model_only','76_Cedar',True),('postmr_cached_model_only','77_Cedar',False),
    ('postmr_readyset_consumption_only','76_Cedar',False),('saved_native_usability_only','76_Cedar',False)])
def test_c76_return_has_one_explicit_retry_scope(action,delivery,valid):
    m=template();args=SimpleNamespace(**{action:True})
    if valid:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)


@pytest.mark.parametrize('defect',['none','build','delivery','action','status','parent','payloads','readyset_calls','native_calls',
    'policy','after','after_qualification','roundtrip','decision','selection','adoption','student_gate','preservation','native_label',
    'proxy_label','linked_label','generation','optimization','editing','refinement','policy_recompilation','report'])
def test_c76_header_requires_original_review_and_verified_start(monkeypatch,defect):
    m=template()
    a={'policy_id':'cif-postmr-cached-model-readback-v1','status':'REVIEW','new_readyset_calls':1,'new_native_calls':1,
        'requires_cif_review':False,'automatic_adoption':False,'after':{'status':'NOT_RUN'},
        'after_qualification':{'status':'NOT_RUN'},'roundtrip':{'status':'NOT_RUN'},
        'decision':{'status':'CONTINUE_WITH_NOTES','selected':'verified_constructed_model'}}
    r={'delivery_prefix':'76_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
        'requested_action':'ORDINARY_POSTMR_CACHED_MODEL_READBACK','status':'REVIEW','build':{'explicit_fixture':True},
        'requires_cif_review':False,'automatic_adoption':False,'policy_authority':'NARestraints',
        **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
        **{k:'NOT_RUN' for k in ['model_editing','policy_recompilation','refinement','installed_phenix_edits','scientific_approval']},
        'native_execution':'FIXED_WHOLE_MODEL_CACHED_READBACK','native_proxy_validation':'FIXED_WHOLE_MODEL_CACHED_READBACK',
        'linked_site_validation':'EXPLICIT_CURRENT_MODEL_CONTEXT_READBACK','dictionary_generation':'OBSERVED_NATIVE_BUILDER_CALLS',
        'model_optimization':'NOT_REQUESTED; NATIVE_INTERNALS_NOT_EXHAUSTIVELY_INSTRUMENTED',
        'prior_archive':{'sha256':m.CEDAR75_SHA256,'verified_payloads':5949},'postmr_cached_model_audit':a}
    m.CEDAR76_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_verify_manifest',lambda *args:None)
    monkeypatch.setattr(m,'_read_cedar75_members',lambda members:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar76_return',lambda members:True)
    if defect=='build':r['build']['changed']=True
    if defect=='delivery':r['delivery_prefix']='77_Cedar'
    if defect=='action':r['requested_action']='OTHER'
    if defect=='status':r['status']='PASS'
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='payloads':r['prior_archive']['verified_payloads']=0
    if defect=='readyset_calls':a['new_readyset_calls']=0
    if defect=='native_calls':a['new_native_calls']=2
    if defect=='policy':a['policy_id']='OTHER'
    if defect in {'after','after_qualification','roundtrip'}:a[defect]={'status':'PASS'}
    if defect=='decision':a['decision']['status']='PASS'
    if defect=='selection':a['decision']['selected']='readyset_checked_model'
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='student_gate':r['requires_cif_review']=True
    if defect=='preservation':r['frozen_inputs_preserved']=False
    if defect=='native_label':r['native_execution']='NOT_RUN'
    if defect=='proxy_label':r['native_proxy_validation']='NOT_RUN'
    if defect=='linked_label':r['linked_site_validation']='NOT_RUN'
    if defect=='generation':r['dictionary_generation']='NOT_RUN'
    if defect=='optimization':r['model_optimization']='RUN'
    if defect in {'editing','refinement','policy_recompilation'}:r['model_editing' if defect=='editing' else defect]='RUN'
    members={'probe_receipt.json':json.dumps(r).encode(),'postmr_cached_model_audit.json':json.dumps(a).encode()}
    if defect=='report':members['postmr_cached_model_audit.json']=b'{}'
    if defect=='none':assert m._read_cedar76_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar76_members(members)
