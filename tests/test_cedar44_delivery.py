"""Saved conditioning arithmetic and scientific inputs stay independently gated."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar43_delivery import fixture
from tests.test_cif_dihedral_conditioning import source, oracle


def conditioning_return():
    from nasolve.cif_dihedral_conditioning import audit_dihedral_conditioning, POLICY_ID
    m,members,previous=fixture();members['inputs/review/probe_receipt.json']=json.dumps(previous).encode()
    a={'policy_id':POLICY_ID,'status':'REVIEW','cases':{},'restraint_changes':'NONE','automatic_adoption':False,
       'native_execution':'ISOLATED_DIHEDRAL_CONDITIONING_ONLY',**{k:'NOT_RUN' for k in ['dictionary_generation','readyset','model_optimization','scientific_approval']}}
    m.CEDAR43_WORKER_SHA256=sha256(b'FAKE CONDITIONING WORKER').hexdigest()
    for code in ['PDU','5PC']:
        old=previous['readyset_generation_audit']['cases'][code]['native_interpretation']
        points,proxy=source();proxies=[{**proxy,'angle_ideal':27.+i} for i in range(3)]
        cases={k:deepcopy(points) for k in ['source_seed_native','generated_dictionary_full_precision','generated_dictionary_pdb_rounded']}
        x=audit_dihedral_conditioning(oracle,cases,proxies)
        x.update(captured_inventory_matches=True,constraint_signature_before='fixed',constraint_signature_after='fixed',
                 installed_numeric_sources=[{'module':'fake'+str(i),'sha256':'pinned'} for i in range(6)],installed_dihedral_sources=[])
        p=m.CEDAR43_NATIVE_PREFIX[code];n={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},
            'source_preserved':True,'frozen_inputs_preserved':True,'automatic_adoption':False,'restraint_changes':'NONE',
            'inputs':old['inputs'],'outputs':[],'result':x}
        for row in n['inputs']:members[p+'/'+row['path']]=members[m.CEDAR42_NATIVE_PREFIX[code]+'/'+row['path']]
        for name,value in [('conditioning_result.json',x),('conditioning_receipt.json',n),('expected_inventory.json',old['native_validation']),
                           ('conditioning_spec.json',{'coordinate_cases':cases,'proxies':proxies,'expected_numeric_sources':x['installed_numeric_sources']})]:
            members[p+'/'+name]=json.dumps(value).encode()
        members[p+'/conditioning_worker.py']=b'FAKE CONDITIONING WORKER';members[p+'/native_worker.py']=b'FAKE NATIVE WORKER'
        a['cases'][code]={'native':n,'candidate_sha256':m.CEDAR42_CANDIDATE_SHA256[code],'coordinate_cases':cases,'proxies':proxies,
            'source_state_review':{'source_charge_sum':0.,'generated_charge_sum':-2.,'missing_source_atoms':['HX','HY'],'status':'REVIEW'}}
    r={'torsion_conditioning_audit':a};save(m,members,r);return m,members,r


def save(m,members,r):
    a=r['torsion_conditioning_audit']
    for code,c in a['cases'].items():
        p=m.CEDAR43_NATIVE_PREFIX[code];n=c['native']
        members[p+'/conditioning_receipt.json']=json.dumps(n).encode();members[p+'/conditioning_result.json']=json.dumps(n['result']).encode()
    members['torsion_conditioning_receipt.json']=json.dumps(a).encode()


@pytest.mark.parametrize('defect',['none','worker','input','signature','arithmetic','scope','state','promote_undefined','expected_inventory','budget','candidate','source_preserved'])
def test_returned_conditioning_cannot_hide_a_changed_input_or_open_chemistry(defect):
    m,members,r=conditioning_return();c=r['torsion_conditioning_audit']['cases']['PDU'];n=c['native'];p=m.CEDAR43_NATIVE_PREFIX['PDU']
    if defect=='worker':members[p+'/conditioning_worker.py']=b'CHANGED'
    if defect=='input':members[p+'/inputs/001_dictionary.cif']=b'CHANGED'
    if defect=='signature':n['result']['constraint_signature_after']='changed'
    if defect=='arithmetic':n['result']['cases']['source_seed_native']['proxies'][0]['directions'][0]['samples'][0]['single']['numerical']+=1.
    if defect=='scope':r['torsion_conditioning_audit']['model_optimization']='RUN'
    if defect=='state':c['source_state_review']['generated_charge_sum']=0
    if defect=='promote_undefined':n['result']['numerical_controls']['exact_collinear']['qualification']='PASS'
    if defect=='expected_inventory':members[p+'/expected_inventory.json']=b'{}'
    if defect=='budget':n['result']['evaluation_pairs']=4000
    if defect=='candidate':c['candidate_sha256']='changed'
    if defect=='source_preserved':n['source_preserved']=False
    save(m,members,r)
    if defect=='none':
        replay=m._check_conditioning_return(members,r)
        assert all(v['directions_recomputed']==117 for v in replay.values())
    else:
        with pytest.raises(ValueError):m._check_conditioning_return(members,r)
