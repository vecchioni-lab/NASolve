"""The C68 preflight failure is evidence, never a native qualification."""
from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from tests.test_cedar66_delivery import template


@pytest.mark.parametrize('defect',['none','build','action','parent','report','status','attempts','worker',
    'selected','reason','repeat','projection','student','adoption','generation','preserved','replay'])
def test_retry_requires_exact_unlaunched_source_reuse_return(monkeypatch,defect):
    m=template()
    a={'schema_version':1,'policy_id':'cif-ordinary-source-reuse-qualification-v1','status':'REVIEW',
        'new_native_calls':3,'native_execution':'FIXED_ISOLATED_SOURCE_REUSE_QUALIFICATION',
        'scope':'ORDINARY_SOURCE_BOUND_ISOLATED_NUMERICS; CURRENT_LINKS_AND_MODEL_SEPARATE',
        'requires_cif_review':False,
        **{k:'NOT_RUN' for k in ['dictionary_generation','model_optimization','readyset_execution','production_adoption']},
        'cases':{code:{'native':{'status':'NOT_RUN'},'source_matches_C67':True,
            'first_directory':{'anchor':'probe_directory','path':'ordinary_source_reuse/'+code+'/first'},
            'first':{'component':code,'status':'ORDINARY_SOURCE_FALLBACK','selected':'ordinary_source',
                'numerics':None,'native_adapter_calls':1,
                'notes':['Saved numerics were not selected: Native output parent must be outside every source input directory'],
                'projection':{'status':'SOURCE_PROJECTION_PASS','checks':{'EXPLICIT_FAKE':True}}}}
            for code in ['DP','PDU','5PC']}}
    r={'build':{'EXPLICIT_FAKE':'C68'},'delivery_prefix':'68_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
        'status':'REVIEW','requested_action':'ORDINARY_SOURCE_REUSE_QUALIFICATION','source_reuse_audit':a,
        'prior_archive':{'sha256':m.CEDAR67_SHA256,'verified_payloads':3713},
        'policy_authority':'NARestraints','requires_cif_review':False,'automatic_adoption':False,
        **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
        **{k:'NOT_RUN' for k in ['model_editing','model_optimization','dictionary_generation','refinement','policy_recompilation',
            'readyset_retry','installed_phenix_edits','scientific_approval','linked_site_validation']}}
    m.CEDAR68_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar67_members',lambda x:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar68_return',lambda x:defect!='replay',raising=False)
    if defect=='build':r['build']['OTHER']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='status':a['status']='SOURCE_REUSE_QUALIFICATION_PASS'
    if defect=='attempts':a['new_native_calls']=0
    if defect=='worker':a['cases']['DP']['native']['status']='REVIEW'
    if defect=='selected':a['cases']['DP']['first']['selected']='qualified_dictionary'
    if defect=='reason':a['cases']['DP']['first']['notes']=[]
    if defect=='repeat':a['cases']['DP']['repeat']={'status':'REUSED'}
    if defect=='projection':a['cases']['DP']['first']['projection']['checks']['EXPLICIT_FAKE']=False
    if defect=='student':r['requires_cif_review']=True
    if defect=='adoption':a['production_adoption']='RAN'
    if defect=='generation':r['dictionary_generation']='RAN'
    if defect=='preserved':r['frozen_inputs_preserved']=False
    members={'probe_receipt.json':json.dumps(r).encode(),'source_reuse_audit.json':json.dumps(a).encode(),
        'inputs/review/probe_receipt.json':b'{}'}
    if defect=='report':members['source_reuse_audit.json']=b'{}'
    members.update({'padding/'+str(i):b'EXPLICIT_FAKE' for i in range(3766-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar68_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar68_members(members)


@pytest.mark.parametrize('action,delivery,valid',[
    ('source_reuse_qualification_only','68_Cedar',True),
    ('ordinary_acquisition_only','68_Cedar',False),
    ('source_reuse_qualification_only','66_Cedar',False)])
def test_retry_mode_keeps_its_verified_lineage(action,delivery,valid):
    args=SimpleNamespace(**{action:True});m=template()
    if valid:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
