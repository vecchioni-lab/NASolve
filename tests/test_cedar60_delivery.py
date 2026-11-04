"""C60 consumes only completed C59 full-scaffold mechanics evidence."""
from hashlib import sha256
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest


def fake_return(monkeypatch):
    p=Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py';spec=importlib.util.spec_from_file_location('cedar60',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    a={'policy_id':'cif-qualified-scaffold-candidate-v1','scope':'SEPARATE_FULL_SCAFFOLD_CANDIDATE','component':'DP','selected_sites':['B:4'],
       'native_execution':'SOURCE_NATIVE_FULL_SCAFFOLD_CANDIDATE','automatic_adoption':False,'requires_cif_review':False,'production_pipeline':'UNCHANGED'}
    a.update({k:'NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization']})
    r={'build':{'explicit_fake':'TEST_BUILD'},'delivery_prefix':'59_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
       'requested_action':'SOURCE_NATIVE_FULL_SCAFFOLD_CANDIDATE','status':'REVIEW','phenix_version':'2.2.1','policy_authority':'NARestraints',
       'requires_cif_review':False,'automatic_adoption':False,'scaffold_candidate_audit':a,'linked_dictionary_preparation':'SOURCE_GRAPH_SITE_MODIFIERS',
       'prior_archive':{'sha256':m.CEDAR58_SHA256,'verified_payloads':2940}}
    r.update({k:'SOURCE_NATIVE_FULL_SCAFFOLD_CANDIDATE' for k in ['native_execution','native_proxy_validation','linked_site_validation']})
    r.update({k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']})
    r.update({k:'NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','policy_recompilation','refinement','readyset_retry','installed_phenix_edits','scientific_approval']})
    m.CEDAR59_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar58_members',lambda members:('qualified','prior','rotation'))
    monkeypatch.setattr(m,'_replay_scaffold_candidate',lambda members:{'explicit_fake':'replayer tested separately'},raising=False)
    return m,r


def members_for(r):
    members={'probe_receipt.json':json.dumps(r).encode(),'scaffold_candidate_audit.json':json.dumps(r['scaffold_candidate_audit']).encode(),
       'inputs/review/probe_receipt.json':b'{"explicit_fake":"earlier boundary tested separately"}'}
    for i in range(3097-len(members)):members['padding/'+str(i)]=b'EXPLICIT_FAKE_PADDING'
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode();return members


@pytest.mark.parametrize('defect',['none','build','kind','action','lineage','preservation','native','version','site','adoption','policy','different_report','optimization','student_gate'])
def test_exact_completed_scaffold_return_boundary(monkeypatch,defect):
    m,r=fake_return(monkeypatch);a=r['scaffold_candidate_audit']
    if defect=='build':r['build']['changed']=True
    if defect=='kind':r['kind']='UNRELATED'
    if defect=='action':r['requested_action']='UNQUALIFIED_OPTIMIZER'
    if defect=='lineage':r['prior_archive']['sha256']='0'*64
    if defect=='preservation':r['original_archive_preserved']=False
    if defect=='native':r['native_execution']='NOT_RUN'
    if defect=='version':r['phenix_version']='DIFFERENT'
    if defect=='site':a['selected_sites']=['B:5']
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='policy':a['policy_id']='UNVERIFIED'
    if defect=='optimization':r['model_optimization']='RAN'
    if defect=='student_gate':r['requires_cif_review']=True
    members=members_for(r)
    if defect=='different_report':
        members['scaffold_candidate_audit.json']=b'{}';members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items() if n!='manifest.json'}).encode()
    if defect=='none':assert m._read_cedar59_members(members)==('qualified','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar59_members(members)


@pytest.mark.parametrize('delivery,option',[('59_Cedar','scaffold_geometry_only'),('58_Cedar','scaffold_candidate_only'),('57_Cedar','linked_control_only')])
def test_replacement_geometry_requires_its_explicit_input_action(monkeypatch,delivery,option):
    m,_=fake_return(monkeypatch);args=SimpleNamespace(**{option:True});m._check_constructor_input_mode(args,delivery)
    args.scaffold_geometry_only=not getattr(args,'scaffold_geometry_only',False)
    with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
