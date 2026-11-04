"""Exact C57 boundary and opt-in C58 routing; earlier/native replay is separate."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest


def fake_return(monkeypatch):
    p=Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py';spec=importlib.util.spec_from_file_location('cedar58',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    a={'policy_id':'cif-source-declared-dna-metadata-v1','scope':'ISOLATED_COMPONENT_ONLY','native_execution':'SOURCE_DNA_METADATA_NATIVE_EQUIVALENCE',
       'automatic_adoption':False,'requires_cif_review':False,'cases':{code:{'explicit_fake':code} for code in ['DP','PDU','5PC']}}
    a.update({k:'NOT_RUN' for k in ['dictionary_generation','model_optimization','linked_adoption']})
    r={'build':{'explicit_fake':'TEST_BUILD'},'delivery_prefix':'57_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
       'requested_action':'SOURCE_DNA_METADATA_NATIVE_EQUIVALENCE','native_execution':'SOURCE_DNA_METADATA_NATIVE_EQUIVALENCE','phenix_version':'2.2.1','status':'REVIEW',
       'policy_authority':'NARestraints','requires_cif_review':False,'automatic_adoption':False,'source_classification_audit':a,
       'prior_archive':{'sha256':m.CEDAR56_SHA256,'verified_payloads':2774}}
    r.update({k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']})
    r.update({k:'NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','linked_site_validation','refinement','readyset_retry','installed_phenix_edits']})
    m.CEDAR57_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar56_members',lambda members:('qualified','prior','rotation'))
    monkeypatch.setattr(m,'_replay_source_metadata',lambda members:deepcopy(a['cases']))
    return m,r


def members_for(r):
    members={'probe_receipt.json':json.dumps(r).encode(),'source_classification_audit.json':json.dumps(r['source_classification_audit']).encode(),
       'inputs/review/probe_receipt.json':b'{"explicit_fake":"earlier boundary tested separately"}'}
    for i in range(2854-len(members)):members['padding/'+str(i)]=b'EXPLICIT_FAKE_PADDING'
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode();return members


@pytest.mark.parametrize('defect',['none','build','kind','action','lineage','preservation','native','version','scope','adoption','policy','different_report'])
def test_exact_completed_metadata_return_boundary(monkeypatch,defect):
    m,r=fake_return(monkeypatch);a=r['source_classification_audit']
    if defect=='build':r['build']['changed']=True
    if defect=='kind':r['kind']='UNRELATED'
    if defect=='action':r['requested_action']='RUN_GENERATOR'
    if defect=='lineage':r['prior_archive']['sha256']='0'*64
    if defect=='preservation':r['original_archive_preserved']=False
    if defect=='native':r['native_execution']='NOT_RUN'
    if defect=='version':r['phenix_version']='DIFFERENT'
    if defect=='scope':a['cases'].pop('PDU')
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='policy':a['policy_id']='UNVERIFIED'
    if defect=='different_report':
        members=members_for(r);members['source_classification_audit.json']=b'{}';members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items() if n!='manifest.json'}).encode()
    else:members=members_for(r)
    if defect=='none':assert m._read_cedar57_members(members)==('qualified','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar57_members(members)


@pytest.mark.parametrize('delivery,option',[('57_Cedar','linked_control_only'),('56_Cedar','source_dna_metadata_only'),('55_Cedar','saved_native_usability_only')])
def test_linked_controls_require_their_explicit_input_action(monkeypatch,delivery,option):
    m,_=fake_return(monkeypatch);args=SimpleNamespace(**{option:True});m._check_constructor_input_mode(args,delivery)
    args.linked_control_only=not getattr(args,'linked_control_only',False)
    with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
