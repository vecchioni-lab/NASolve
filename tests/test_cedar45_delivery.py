"""Returned inventories retain exact omissions and all earlier scientific gates."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar44_delivery import conditioning_return
from tests.test_cif_linear_torsion_candidate import inventory


def returned():
    from nasolve.cif_linear_torsion_candidate import POLICY_ID,qualify_linear_torsion_candidate
    m,old_members,old_receipt=conditioning_return();old_members['probe_receipt.json']=json.dumps(old_receipt).encode()
    members={'inputs/review/'+n:d for n,d in old_members.items()};a={'policy_id':POLICY_ID,'status':'REVIEW',
        'native_execution':'ISOLATED_TORSION_OMISSION_INVENTORIES','automatic_adoption':False,
        'restraint_changes':'SEPARATE_CANDIDATE_TORSION_OMISSIONS_ONLY','cases':{},
        **{k:'NOT_RUN' for k in ['dictionary_generation','readyset','model_optimization','model_editing','scientific_approval']}}
    for code in ['PDU','5PC']:
        prior=old_receipt['torsion_conditioning_audit']['cases'][code];before=inventory();names=['L','X','Y','R','S','U']
        before['atoms']=[{'i_seq':i,'atom_id':n,'identity':{'resname':code,'chain_id':'A','resseq':'1'}} for i,n in enumerate(names)];before['atom_count']=6
        quartets=[['L','X','Y','R'],['S','X','Y','R'],['X','Y','R','U'],['H1','X','Y','R'],['H2','X','Y','R'],['X','Y','R','H3']]
        tor=[{'id':'t'+str(i),**{'atom_id_'+str(j+1):n for j,n in enumerate(p)},'value_angle':20.,'value_angle_esd':30.,'period':3} for i,p in enumerate(quartets)]
        before['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions']=tor
        proxy=before['geometry']['proxy_details']['dihedral'][0]
        before['geometry']['proxy_details']['dihedral']=[{**proxy,'i_seqs':[names.index(n) for n in p]} for p in quartets[:3]];before['geometry']['proxy_counts']['dihedral']=3
        after=deepcopy(before);after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions']=[]
        after['geometry']['proxy_details']['dihedral']=[];after['geometry']['proxy_counts']['dihedral']=0
        data=('FAKE SEPARATE CANDIDATE '+code).encode();digest=sha256(data).hexdigest();m.CEDAR44_CANDIDATE_SHA256[code]=digest
        plan={'removed_torsion_count':6,'parsed_allowlist_pass':True,'source_preserved':True,'automatic_adoption':False,'selection_coordinates':'NOT_USED',
              'source_sha256':m.CEDAR42_CANDIDATE_SHA256[code],'candidate_sha256':digest,'component':code,
              'removed_torsions':[{('_chem_comp_tor.'+k):str(v) for k,v in row.items()} for row in tor]}
        artifact={'anchor':'probe_directory','path':'linear_torsion_candidates/'+code+'/'+code+'_linear_torsion_candidate.cif','sha256':digest,'size':len(data)}
        members[artifact['path']]=data;c={'plan':plan,'candidate':artifact,'source_state_review':prior['source_state_review'],
           'original_inventory_matches':True,'native_mechanics':qualify_linear_torsion_candidate(before,after,plan),
           'dictionary_triple_screen':{'target_screen':'PASS','linear_axis_torsions':[]},'native_triple_screen':{'target_screen':'PASS','linear_axis_torsions':[]}}
        members['inputs/review/'+m.CEDAR43_NATIVE_PREFIX[code]+'/expected_inventory.json']=json.dumps(before).encode()
        for role,v in [('original_native',before),('candidate_native',after)]:
            n={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,'automatic_adoption':False,
               **{k:'NOT_RUN' for k in ['optimization','model_editing','readyset_retry','scientific_approval']},'native_validation':v,'inputs':deepcopy(prior['native']['inputs']),'outputs':[]}
            p=m.CEDAR44_NATIVE_PREFIX[code][role]
            for row in n['inputs']:
                raw=data if role=='candidate_native' and row['role']=='dictionary' else old_members[m.CEDAR43_NATIVE_PREFIX[code]+'/'+row['path']]
                row.update(sha256=sha256(raw).hexdigest(),size=len(raw));members[p+'/'+row['path']]=raw
            members[p+'/native_worker.py']=b'FAKE NATIVE WORKER';c[role]=n
        a['cases'][code]=c
    r={'linear_torsion_candidate_audit':a};save(m,members,r);return m,members,r


def save(m,members,r):
    for code,c in r['linear_torsion_candidate_audit']['cases'].items():
        for role in ['original_native','candidate_native']:
            p=m.CEDAR44_NATIVE_PREFIX[code][role];n=c[role]
            members[p+'/native_receipt.json']=json.dumps(n).encode();members[p+'/native_validation.json']=json.dumps(n['native_validation']).encode()
    members['linear_torsion_candidate_receipt.json']=json.dumps(r['linear_torsion_candidate_audit']).encode()


@pytest.mark.parametrize('defect',['none','worker','candidate_bytes','native_input','original_mismatch','hidden_state','angle_change','proxy_change','missing_triple','adoption','execution','plan_target','stale_checks'])
def test_completed_candidate_gate_recomputes_exact_native_delta(defect):
    m,members,r=returned();a=r['linear_torsion_candidate_audit'];c=a['cases']['PDU'];p=m.CEDAR44_NATIVE_PREFIX['PDU']['candidate_native']
    if defect=='worker':members[p+'/native_worker.py']=b'CHANGED'
    if defect=='candidate_bytes':members[c['candidate']['path']]=b'CHANGED'
    if defect=='native_input':members[p+'/inputs/001_dictionary.cif']=b'CHANGED'
    if defect=='original_mismatch':c['original_inventory_matches']=False
    if defect=='hidden_state':c['source_state_review']['generated_charge_sum']=0
    if defect=='angle_change':c['candidate_native']['native_validation']['geometry']['proxy_details']['angle'][0]['angle_ideal']=170
    if defect=='proxy_change':c['candidate_native']['native_validation']['geometry']['proxy_details']['dihedral']=[{'i_seqs':[0,1,2,3]}]
    if defect=='missing_triple':c['native_triple_screen']['target_screen']='REVIEW'
    if defect=='adoption':a['automatic_adoption']=True
    if defect=='execution':c['candidate_native']['execution']['returncode']=1
    if defect=='plan_target':c['plan']['removed_torsions'][0]['_chem_comp_tor.value_angle']='30'
    if defect=='stale_checks':c['native_mechanics']['checks']['geometry_exact']=False
    save(m,members,r)
    if defect=='none':assert all(v['mechanics_checks_pass'] for v in m._check_linear_torsion_candidate_return(members,r).values())
    else:
        with pytest.raises(ValueError):m._check_linear_torsion_candidate_return(members,r)
