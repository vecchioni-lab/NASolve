"""Saved source qualification must retain the real auditor/consumer contracts."""
from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from tests.test_cedar66_delivery import template
from tests.test_cif_triple_bond_audit import fixture


@pytest.mark.parametrize('code',['Q17','Q1','PDU'])
def test_source_reuse_reports_dictionary_and_native_triples_separately(tmp_path,code):
    m=template();source,values=fixture(tmp_path,code)
    native={'atoms':[], 'geometry':{'proxy_details':{}},'monomer_mappings':{'rows':[]}}
    from nasolve.cif_triple_bond_audit import audit_triple_bonds
    expected={'dictionary':audit_triple_bonds(source,code,dictionary=source),
              'native':audit_triple_bonds(source,code,native=native)}
    assert m._source_reuse_triple_screens(source,source,code,native)==expected


@pytest.mark.parametrize('action,valid',[('saved_source_reuse_only',True),('source_reuse_qualification_only',False)])
def test_saved_source_action_requires_completed_c69(action,valid):
    m=template();args=SimpleNamespace(**{action:True})
    if valid:m._check_constructor_input_mode(args,'69_Cedar')
    else:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,'69_Cedar')


@pytest.mark.parametrize('defect',['none','build','action','parent','worker','notes','qualification','calls',
    'report','student','adoption','preserved','replay'])
def test_saved_source_replay_requires_completed_native_return(monkeypatch,defect):
    m=template();a={'policy_id':'cif-ordinary-source-reuse-qualification-v1','status':'REVIEW',
        'native_attempts':3,'new_native_calls':3,'requires_cif_review':False,
        **{k:'NOT_RUN' for k in ['dictionary_generation','model_optimization','readyset_execution','production_adoption']},
        'cases':{c:{'native':{'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0}},
          'source_matches_C67':True,'qualification':{'status':'ISOLATED_NATIVE_USABILITY_PASS','native_usable':True},
          'first':{'status':'ORDINARY_SOURCE_FALLBACK','selected':'ordinary_source',
          'notes':['Saved numerics were not selected: Require exactly one dictionary or native inventory']}} for c in ['DP','PDU','5PC']}}
    r={'build':{'EXPLICIT_FAKE':'C69'},'delivery_prefix':'69_Cedar','kind':'cif-source-graph-numerical-recovery-probe',
       'requested_action':'ORDINARY_SOURCE_REUSE_QUALIFICATION','status':'REVIEW','source_reuse_audit':a,
       'prior_archive':{'sha256':m.CEDAR68_SHA256,'verified_payloads':3766},
       'requires_cif_review':False,'automatic_adoption':False,'policy_authority':'NARestraints',
       **{k:True for k in ['analysis_completed','original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed']},
       **{k:'NOT_RUN' for k in ['model_editing','model_optimization','dictionary_generation','policy_recompilation','refinement','readyset_retry','installed_phenix_edits','scientific_approval','linked_site_validation']}}
    m.CEDAR69_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(m,'_read_cedar68_members',lambda x:('proof','prior','rotation'))
    monkeypatch.setattr(m,'_replay_cedar69_return',lambda *a:defect!='replay',raising=False)
    if defect=='build':r['build']['changed']=True
    if defect=='action':r['requested_action']='OTHER'
    if defect=='parent':r['prior_archive']['sha256']='0'*64
    if defect=='worker':a['cases']['DP']['native']['execution']['returncode']=1
    if defect=='notes':a['cases']['DP']['first']['notes']=[]
    if defect=='qualification':a['cases']['DP']['qualification']['native_usable']=False
    if defect=='calls':a['new_native_calls']=0
    if defect=='student':r['requires_cif_review']=True
    if defect=='adoption':a['production_adoption']='RAN'
    if defect=='preserved':r['frozen_inputs_preserved']=False
    members={'probe_receipt.json':json.dumps(r).encode(),'source_reuse_audit.json':json.dumps(a).encode(),
             'inputs/review/probe_receipt.json':b'{}'}
    if defect=='report':members['source_reuse_audit.json']=b'{}'
    members.update({'padding/'+str(i):b'EXPLICIT_FAKE' for i in range(3849-len(members))})
    members['manifest.json']=json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}).encode()
    if defect=='none':assert m._read_cedar69_members(members)==('proof','prior','rotation')
    else:
        with pytest.raises(ValueError):m._read_cedar69_members(members)
