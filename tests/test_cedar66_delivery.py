"""Local dictionary reuse accepts the exact verified C65 transport only."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest


def template():
    spec=importlib.util.spec_from_file_location('cedar66',Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def fake_return(monkeypatch):
    m=template();checks=[{'check':'EXPLICIT_FAKE_PASS_'+str(i),'status':'PASS'} for i in range(93)]
    checks += [{'check':'effective-site-formal-charges:'+s,'status':'UNSUPPORTED'} for s in ['A:6','A:7','A:9']]
    q={'status':'CONSTRUCTED_NATIVE_MECHANICS_PASS','mechanics_checks_pass':True,'checks':checks}
    a={'policy_id':'cif-saved-constructed-native-replay-v1','scope':'SAVED_ORDINARY_CONSTRUCTION_NATIVE_READBACK',
        'status':'CONSTRUCTED_NATIVE_MECHANICS_PASS','qualification':q,'new_native_calls':0,
        'native_evidence':'PRESERVED_PHENIX_2.2.1-6174_CAPTURE','original_qualification_status':'REVIEW',
        'original_review_checks':['unaffected-native-proxies:'+k for k in ['angle','bond_simple','chirality','const_dihedral','dihedral','planarity']],
        'directory':{'anchor':'probe_directory','path':'constructed_native_replay'},
        'automatic_adoption':False,'requires_cif_review':False,'production_checkpoint':'NOT_CREATED',
        **{k:'NOT_RUN' for k in ['native_execution','captured_code_execution','coot_execution','readyset_execution',
            'dictionary_generation','model_optimization','refinement','policy_recompilation']}}
    r={'delivery_prefix':'65_Cedar','build':{'EXPLICIT_FAKE':'BUILD'},'kind':'cif-source-graph-numerical-recovery-probe',
        'status':'REVIEW','requested_action':'SAVED_ORDINARY_CONSTRUCTION_NATIVE_READBACK',
        'captured_phenix_version':'2.2.1','policy_authority':'NARestraints','requires_cif_review':False,
        'automatic_adoption':False,'native_execution':'NOT_RUN','native_proxy_validation':'SAVED_CONSTRUCTION_NATIVE_REPLAY',
        'linked_site_validation':'SAVED_CONSTRUCTION_NATIVE_REPLAY','model_editing':'EXACT_CONSTRUCTED_MODEL_COPY',
        'saved_construction_native_audit':a,'prior_archive':{'sha256':m.CEDAR64_SHA256,'verified_payloads':3552},
        **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
        **{k:'NOT_RUN' for k in ['model_optimization','dictionary_generation','policy_recompilation','refinement',
            'readyset_retry','installed_phenix_edits','scientific_approval']}}
    m.CEDAR65_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar64_members',lambda members:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar65_return',lambda members:True,raising=False)
    return m,r


@pytest.mark.parametrize('defect',['none','build','kind','action','parent','payload_count','preservation','native',
    'version','model','report','scope','optimizer','adoption','student_gate','review','unsupported','missing_check',
    'duplicate_check','native_calls','checkpoint','captured_code','original_reviews'])
def test_reuse_requires_exact_completed_return(monkeypatch,defect):
    m,r=fake_return(monkeypatch);a=r['saved_construction_native_audit']
    if defect=='build':r['build']['changed']=True
    if defect=='kind':r['kind']='OTHER'
    if defect=='action':r['requested_action']='OTHER'
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='payload_count':r['prior_archive']['verified_payloads']=0
    if defect=='preservation':r['original_archive_preserved']=False
    if defect=='native':r['native_execution']='COMPLETED'
    if defect=='version':r['captured_phenix_version']='OTHER'
    if defect=='model':r['model_editing']='EDITED'
    if defect=='scope':a['scope']='OTHER'
    if defect=='optimizer':a['model_optimization']='RAN'
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='student_gate':r['requires_cif_review']=True
    if defect=='review':a['qualification']['checks'][0]['status']='REVIEW'
    if defect=='unsupported':a['qualification']['checks'][-1]['check']='OTHER'
    if defect=='missing_check':a['qualification']['checks'].pop()
    if defect=='duplicate_check':a['qualification']['checks'][-1]=deepcopy(a['qualification']['checks'][-2])
    if defect=='native_calls':a['new_native_calls']=1
    if defect=='checkpoint':a['production_checkpoint']='CREATED'
    if defect=='captured_code':a['captured_code_execution']='RAN'
    if defect=='original_reviews':a['original_review_checks']=[]
    members={'probe_receipt.json':json.dumps(r).encode(),'saved_construction_native_audit.json':json.dumps(a).encode(),
        'inputs/review/probe_receipt.json':b'{}'}
    if defect=='report':members['saved_construction_native_audit.json']=b'{}'
    members.update({'padding/'+str(i):b'EXPLICIT_FAKE' for i in range(3587-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar65_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar65_members(members)


@pytest.mark.parametrize('action,delivery,valid',[('local_dictionary_reuse_only','65_Cedar',True),
    ('saved_postmr_construction_native_only','65_Cedar',False),('local_dictionary_reuse_only','64_Cedar',False)])
def test_local_reuse_has_one_explicit_input_scope(action,delivery,valid):
    m=template();args=SimpleNamespace(**{action:True})
    if valid:m._check_constructor_input_mode(args,delivery)
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
