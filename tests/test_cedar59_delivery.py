"""C59 accepts the completed C58 linkage return only through its explicit action."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest


def fake_return(monkeypatch):
    p=Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py'
    spec=importlib.util.spec_from_file_location('cedar59',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    a={'schema_version':1,'policy_id':'cif-qualified-dna-linked-control-v1',
       'scope':'SEPARATE_SYNTHETIC_THREE_RESIDUE_CONTROLS','native_execution':'SOURCE_DNA_LINKED_CONTROLS',
       'automatic_adoption':False,'requires_cif_review':False,
       'canonical_reference':{'explicit_fake':True},'cases':{code:{'explicit_fake':code} for code in ['DP','PDU','5PC']}}
    a.update({k:'NOT_RUN' for k in ['dictionary_generation','model_optimization','scaffold_adoption']})
    r={'build':{'explicit_fake':'TEST_BUILD'},'delivery_prefix':'58_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
       'requested_action':'SOURCE_DNA_LINKED_CONTROLS','native_execution':'SOURCE_DNA_LINKED_CONTROLS',
       'native_proxy_validation':'SOURCE_DNA_LINKED_CONTROLS','linked_site_validation':'SOURCE_DNA_LINKED_CONTROLS',
       'phenix_version':'2.2.1','status':'REVIEW','policy_authority':'NARestraints',
       'requires_cif_review':False,'automatic_adoption':False,'linked_control_audit':a,
       'model_editing':'SEPARATE_SYNTHETIC_CONTROL_MODELS','linked_dictionary_preparation':'SOURCE_GRAPH_SITE_MODIFIERS',
       'prior_archive':{'sha256':m.CEDAR57_SHA256,'verified_payloads':2854}}
    r.update({k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']})
    r.update({k:'NOT_RUN' for k in ['dictionary_generation','model_optimization','policy_recompilation','refinement','readyset_retry','installed_phenix_edits','scientific_approval']})
    m.CEDAR58_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar57_members',lambda members:('qualified','prior','rotation'))
    monkeypatch.setattr(m,'_replay_linked_controls',lambda members:deepcopy(a['cases']),raising=False)
    return m,r


def members_for(r):
    members={'probe_receipt.json':json.dumps(r).encode(),'linked_control_audit.json':json.dumps(r['linked_control_audit']).encode(),
       'inputs/review/probe_receipt.json':b'{"explicit_fake":"earlier boundary tested separately"}'}
    for i in range(2940-len(members)):members['padding/'+str(i)]=b'EXPLICIT_FAKE_PADDING'
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode();return members


@pytest.mark.parametrize('defect',['none','build','kind','action','lineage','preservation','native','version','scope','adoption','policy','different_report','optimization','student_gate'])
def test_exact_completed_linked_return_boundary(monkeypatch,defect):
    m,r=fake_return(monkeypatch);a=r['linked_control_audit']
    if defect=='build':r['build']['changed']=True
    if defect=='kind':r['kind']='UNRELATED'
    if defect=='action':r['requested_action']='RUN_OPTIMIZER'
    if defect=='lineage':r['prior_archive']['sha256']='0'*64
    if defect=='preservation':r['original_archive_preserved']=False
    if defect=='native':r['native_execution']='NOT_RUN'
    if defect=='version':r['phenix_version']='DIFFERENT'
    if defect=='scope':a['cases'].pop('PDU')
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='policy':a['policy_id']='UNVERIFIED'
    if defect=='optimization':r['model_optimization']='RAN'
    if defect=='student_gate':r['requires_cif_review']=True
    members=members_for(r)
    if defect=='different_report':
        members['linked_control_audit.json']=b'{}';members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items() if n!='manifest.json'}).encode()
    if defect=='none':assert m._read_cedar58_members(members)==('qualified','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar58_members(members)


@pytest.mark.parametrize('delivery,option',[('58_Cedar','scaffold_candidate_only'),('57_Cedar','linked_control_only'),('56_Cedar','source_dna_metadata_only')])
def test_scaffold_candidate_requires_its_explicit_input_action(monkeypatch,delivery,option):
    m,_=fake_return(monkeypatch);args=SimpleNamespace(**{option:True});m._check_constructor_input_mode(args,delivery)
    args.scaffold_candidate_only=not getattr(args,'scaffold_candidate_only',False)
    with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
