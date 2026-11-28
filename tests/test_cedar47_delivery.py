"""The constructor action requires the exact completed native cache evidence."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar46_delivery import returned as prior_return


def returned():
    from nasolve.cif_linear_torsion_impact import FAMILIES
    from nasolve.cif_nonbonded_cache_audit import audit_cache_stabilized_impact
    from tests.test_cif_nonbonded_cache_audit import snapshot
    m,prior,old=prior_return();prior['probe_receipt.json']=json.dumps(old).encode()
    members={'inputs/review/'+n:d for n,d in prior.items()};a=deepcopy(old['linear_torsion_impact_audit'])
    a['cache_policy_id']='cif-native-nonbonded-cache-proof-v1'
    m.CEDAR46_WORKER_SHA256=sha256(b'FAKE CACHE WORKER').hexdigest()
    helpers={name:('FAKE HELPER '+name).encode() for name in m.CEDAR46_HELPER_SHA256}
    m.CEDAR46_HELPER_SHA256={name:sha256(data).hexdigest() for name,data in helpers.items()}
    for code,c in a['cases'].items():
        n=c['native'];previous=m.CEDAR45_NATIVE_PREFIX[code];p=m.CEDAR46_NATIVE_PREFIX[code]
        for name,data in prior.items():
            if name.startswith(previous+'/'):members[p+'/'+name.removeprefix(previous+'/')]=data
        def evaluate(manager,points,family,*,capture_pairs=False):
            factor=sum(range(1,8)) if family=='all' else FAMILIES.index(family)
            if manager=='original' and family in {'all','dihedral'}:factor+=10
            r={'target':factor*sum(v*v for pt in points for v in pt),'gradient':[2*factor*v for pt in points for v in pt],
               'proxy_counts':{'count':1},'nonbonded_membership':None}
            if family in {'all','nonbonded'}:
                s=snapshot(True);r.update(pairs=s['pairs'],nonbonded_target=s['nonbonded_target'],nonbonded_gradient=s['nonbonded_gradient']+[0.]*(3*len(points)-9),
                    nonbonded_membership=[{'i_seqs':q['i_seqs'],'vdw_distance':q['vdw_distance']} for q in s['pairs']],function_parameters={'class':'EXPLICIT_QUADRATIC_ORACLE'})
                r['proxy_counts']['n_nonbonded_proxies']=2
            return r
        x=audit_cache_stabilized_impact(evaluate,c['coordinate_cases'],c['selected_indices'],c['removed_references'])
        x.update({k:deepcopy(n['result'][k]) for k in ['captured_inventories_match','constraint_signatures_before','constraint_signatures_after','installed_numeric_sources','normalization']})
        x['pair_kernel_calls']=sum(len(s[manager][family]['pairs'])+1 for case in x['cases'].values() for s in case['cache_preflight']['snapshots'] for manager in ['original','candidate'] for family in ['all','nonbonded'])
        x['installed_cache_sources']=[]
        for name in ['manager.py','energies.py','nonbonded.h','nonbonded_bpl.cpp']:
            data=('EXPLICIT_FAKE_CAPTURE '+name).encode();path='installed_source/'+name;members[p+'/'+path]=data
            x['installed_cache_sources'].append({'path':path,'status':'RECORDED','sha256':sha256(data).hexdigest(),'bytes':len(data)})
        n['result']=x;n['cache_preflight_requested']=True
        spec=json.loads(members[p+'/impact_spec.json']);spec['cache_preflight']=True;members[p+'/impact_spec.json']=json.dumps(spec).encode()
        members[p+'/impact_worker.py']=b'FAKE CACHE WORKER'
        for name,data in helpers.items():members[p+'/'+name]=data
    r={'linear_torsion_impact_audit':a};save(m,members,r);return m,members,r


def save(m,members,r):
    a=r['linear_torsion_impact_audit']
    for code,c in a['cases'].items():
        p=m.CEDAR46_NATIVE_PREFIX[code];n=c['native']
        members[p+'/impact_receipt.json']=json.dumps(n).encode();members[p+'/impact_result.json']=json.dumps(n['result']).encode()
    members['linear_torsion_impact_receipt.json']=json.dumps(a).encode()


@pytest.mark.parametrize('defect',['none','worker','helper','scientific_input','installed_source','membership','arithmetic','cache_action','state','adoption','execution','budget'])
def test_constructor_prerequisite_requires_preserved_inputs_and_recomputed_cache_proofs(defect):
    m,members,r=returned();a=r['linear_torsion_impact_audit'];c=a['cases']['5PC'];n=c['native'];p=m.CEDAR46_NATIVE_PREFIX['5PC']
    if defect=='worker':members[p+'/impact_worker.py']=b'CHANGED'
    if defect=='helper':members[p+'/cache_core.py']=b'CHANGED'
    if defect=='scientific_input':members[p+'/candidate/inputs/001_dictionary.cif']=b'CHANGED'
    if defect=='installed_source':members[p+'/installed_source/nonbonded.h']=b'CHANGED'
    if defect=='membership':n['result']['cases']['source_seed_native']['cache_preflight']['post_preflight_membership_stable']=False
    if defect=='arithmetic':n['result']['cases']['source_seed_native']['candidate_derivatives']['all'][0]['samples'][0]['numerical']+=1
    if defect=='cache_action':n['cache_preflight_requested']=False
    if defect=='state':c['source_state_review']['generated_charge_sum']=0
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='execution':n['execution']['returncode']=1
    if defect=='budget':n['result']['evaluation_calls']+=1
    save(m,members,r)
    if defect=='none':
        q=m._check_impact_return(members,r,cache=True)
        assert all(v['evaluation_calls_recomputed']==1716 and v['preflight_transitions_recomputed']==24 for v in q.values())
    else:
        with pytest.raises(ValueError):m._check_impact_return(members,r,cache=True)
