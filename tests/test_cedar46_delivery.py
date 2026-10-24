"""The next diagnostic preserves returned count failures and recomputes math."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar45_delivery import returned as prior_return


def returned(count_review=False):
    from nasolve.cif_linear_torsion_impact import POLICY_ID,audit_linear_torsion_impact,FAMILIES
    m,prior,old=prior_return();prior['probe_receipt.json']=json.dumps(old).encode();members={'inputs/review/'+n:d for n,d in prior.items()}
    m.CEDAR45_WORKER_SHA256=sha256(b'FAKE IMPACT WORKER').hexdigest()
    a={'policy_id':POLICY_ID,'status':'REVIEW','native_execution':'ISOLATED_FIXED_COORDINATE_TORSION_IMPACT','automatic_adoption':False,
       'restraint_changes':'NONE; SAVED_SEPARATE_CANDIDATES_EVALUATED',**{k:'NOT_RUN' for k in ['dictionary_generation','readyset','model_optimization','model_editing','scientific_approval']},'cases':{}}
    for code in ['PDU','5PC']:
        calls=0;points=[[.1+i,.3+i,.5+i] for i in range(6)];cases={k:deepcopy(points) for k in ['generated_dictionary_full_precision','generated_dictionary_pdb_rounded','source_seed_native']}
        refs={k:{'target':10*sum(v*v for p in points for v in p),'gradient':[20*v for p in points for v in p]} for k in cases}
        def evaluate(manager,xyz,family):
            nonlocal calls
            calls+=1;factor=sum(range(1,8)) if family=='all' else FAMILIES.index(family)
            if manager=='original' and family in {'all','dihedral'}:factor+=10
            return {'target':factor*sum(v*v for p in xyz for v in p),'gradient':[2*factor*v for p in xyz for v in p],
                    'proxy_counts':{'count':1 if not count_review or calls<=16 else 2}}
        x=audit_linear_torsion_impact(evaluate,cases,list(range(6)),refs)
        numeric=[{'module':'fake'+str(i),'sha256':'pinned'} for i in range(6)]
        x.update(captured_inventories_match=True,constraint_signatures_before={'original':'fixed','candidate':'fixed'},
                 constraint_signatures_after={'original':'fixed','candidate':'fixed'},normalization=False,installed_numeric_sources=numeric)
        n={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,'automatic_adoption':False,
           **{k:'NOT_RUN' for k in ['model_optimization','model_editing','dictionary_generation','readyset','scientific_approval']},'inputs':[],'outputs':[],'result':x}
        p=m.CEDAR45_NATIVE_PREFIX[code];oldcase=old['linear_torsion_candidate_audit']['cases'][code]
        for phase in ['original','candidate']:
            for row in oldcase[phase+'_native']['inputs']:
                r=deepcopy(row);r['path']=phase+'/'+r['path'];r['phase']=phase;n['inputs'].append(r)
                members[p+'/'+r['path']]=prior[m.CEDAR44_NATIVE_PREFIX[code][phase+'_native']+'/'+row['path']]
            expected=oldcase[phase+'_native']['native_validation']
            for name in ['expected_inventory.json','native_validation.json']:members[p+'/'+phase+'/'+name]=json.dumps(expected).encode()
            members[p+'/'+phase+'/native_worker.py']=b'FAKE NATIVE WORKER'
        c={'native':n,'coordinate_cases':cases,'selected_indices':list(range(6)),'removed_references':refs,
           'candidate_sha256':m.CEDAR44_CANDIDATE_SHA256[code],'source_state_review':oldcase['source_state_review']};a['cases'][code]=c
        members[p+'/impact_worker.py']=b'FAKE IMPACT WORKER'
        members[p+'/impact_spec.json']=json.dumps({'coordinate_cases':cases,'selected_indices':list(range(6)),'removed_references':refs,'expected_numeric_sources':numeric}).encode()
    r={'linear_torsion_impact_audit':a};save(m,members,r);return m,members,r


def save(m,members,r):
    a=r['linear_torsion_impact_audit']
    for code,c in a['cases'].items():
        p=m.CEDAR45_NATIVE_PREFIX[code];n=c['native'];members[p+'/impact_receipt.json']=json.dumps(n).encode();members[p+'/impact_result.json']=json.dumps(n['result']).encode()
    members['linear_torsion_impact_receipt.json']=json.dumps(a).encode()


@pytest.mark.parametrize('defect',['none','count_review','worker','input','manager','signature','arithmetic','hide_review','state','adoption','execution','budget'])
def test_return_gate_preserves_failures_and_recomputes_every_native_call(defect):
    m,members,r=returned(defect in {'count_review','hide_review'});a=r['linear_torsion_impact_audit'];c=a['cases']['5PC'];n=c['native'];p=m.CEDAR45_NATIVE_PREFIX['5PC']
    if defect=='worker':members[p+'/impact_worker.py']=b'CHANGED'
    if defect=='input':members[p+'/candidate/inputs/001_dictionary.cif']=b'CHANGED'
    if defect=='manager':members[p+'/original/expected_inventory.json']=b'{}'
    if defect=='signature':n['result']['constraint_signatures_after']['original']='changed'
    if defect=='arithmetic':n['result']['cases']['source_seed_native']['candidate_derivatives']['all'][0]['samples'][0]['numerical']+=1
    if defect=='hide_review':n['result']['cases']['generated_dictionary_full_precision']['checks']['baseline_repeats_consistent']=True
    if defect=='state':c['source_state_review']['generated_charge_sum']=0
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='execution':n['execution']['returncode']=1
    if defect=='budget':n['result']['evaluation_calls']=2001
    save(m,members,r)
    if defect in {'none','count_review'}:
        q=m._check_impact_return(members,r)
        assert all(v['evaluation_calls_recomputed']==1620 for v in q.values())
        if defect=='count_review':assert q['5PC']['cases']['generated_dictionary_full_precision']['failed_checks']
    else:
        with pytest.raises(ValueError):m._check_impact_return(members,r)
