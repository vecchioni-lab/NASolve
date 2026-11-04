from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from tests.test_cedar66_delivery import template


@pytest.mark.parametrize('defect',['none','build','action','parent','scope','native','generation','adoption','student',
    'preserved','missing_case','missing_check','false_check','first','repeat','report'])
def test_acquisition_accepts_only_completed_c66(monkeypatch,defect):
    m=template()
    a={'policy_id':'cif-qualified-dictionary-reuse-controls-v1','status':'QUALIFIED_DICTIONARY_REUSE_PASS',
        'directory':{'anchor':'probe_directory','path':'dictionary_reuse'},'source_inputs_preserved':True,
        'new_native_calls':0,'requires_cif_review':False,
        **{k:'NOT_RUN' for k in ['dictionary_generation','model_optimization','model_editing','readyset_execution','refinement','policy_recompilation','production_adoption']},
        'cases':{c:{'checks':{k:True for k in ['persistent_store_available','independent_first_snapshot','repeat_reuses_same_entry',
            'repeat_exact_numerical_bytes','original_stopping_and_notes_preserved','different_source_is_not_a_hit',
            'source_authority_is_not_overridden','changed_consumer_requalifies_before_generation',
            'snapshot_survives_cache_removal_and_relocation','site_and_model_evidence_remain_separate']},
            'first':{'status':'PREPARED_AND_FROZEN'},'repeat':{'status':'REUSED'}} for c in ['DP','PDU','5PC']}}
    r={'build':{'EXPLICIT_FAKE':'C66'},'delivery_prefix':'66_Cedar','requested_action':'QUALIFIED_LOCAL_DICTIONARY_REUSE',
        'kind':'cif-source-graph-numerical-recovery-probe','status':'REVIEW','policy_authority':'NARestraints',
        'automatic_adoption':False,'requires_cif_review':False,'native_execution':'NOT_RUN',
        'native_proxy_validation':'INHERITED_VERIFIED_CAPTURE; NO_NEW_NATIVE_QUALIFICATION',
        'linked_site_validation':'NOT_RUN; CURRENT_CONTEXT_MUST_BE_REQUALIFIED',
        'dictionary_reuse_audit':a,'prior_archive':{'sha256':'7922b7399e0205553a06ec090ae834e76ba51482ee96ba96b8b940eb9378843b','verified_payloads':3587},
        **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
        **{k:'NOT_RUN' for k in ['model_editing','model_optimization','dictionary_generation','policy_recompilation','refinement','readyset_retry','installed_phenix_edits','scientific_approval']}}
    m.CEDAR66_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar65_members',lambda x:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar66_return',lambda x:True,raising=False)
    if defect=='build':r['build']['changed']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='scope':a['directory']['path']='OTHER'
    if defect=='native':a['new_native_calls']=1
    if defect=='generation':r['dictionary_generation']='RAN'
    if defect=='adoption':a['production_adoption']='RAN'
    if defect=='student':r['requires_cif_review']=True
    if defect=='preserved':r['original_archive_preserved']=False
    if defect=='missing_case':del a['cases']['DP']
    if defect=='missing_check':a['cases']['DP']['checks'].pop('different_source_is_not_a_hit')
    if defect=='false_check':a['cases']['DP']['checks']['repeat_exact_numerical_bytes']=False
    if defect=='first':a['cases']['DP']['first']['status']='UNKNOWN'
    if defect=='repeat':a['cases']['DP']['repeat']['status']='UNKNOWN'
    members={'probe_receipt.json':json.dumps(r).encode(),'dictionary_reuse_audit.json':json.dumps(a).encode(),
        'inputs/review/probe_receipt.json':b'{}'}
    if defect=='report':members['dictionary_reuse_audit.json']=b'{}'
    members.update({'padding/'+str(i):b'EXPLICIT_FAKE' for i in range(3659-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar66_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar66_members(members)


@pytest.mark.parametrize('action,delivery,valid',[('ordinary_acquisition_only','66_Cedar',True),
    ('local_dictionary_reuse_only','66_Cedar',False),('ordinary_acquisition_only','65_Cedar',False)])
def test_acquisition_has_one_explicit_scope(action,delivery,valid):
    m=template();args=SimpleNamespace(**{action:True})
    if valid:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
