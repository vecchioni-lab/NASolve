"""Completed generation, active triple terms and retained reviews are distinct."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
import pytest
from tests.test_cedar42_delivery import returned


def fixture():
    m,members,r=returned();a=r['readyset_generation_audit'];a['policy_id']='cif-isolated-readyset-call-and-triple-restraint-audit-v2'
    m.CEDAR42_WORKER_SHA256=m.CEDAR41_WORKER_SHA256;m.CEDAR42_NATIVE_WORKER_SHA256=sha256(b'FAKE NATIVE WORKER').hexdigest()
    for code,c in a['cases'].items():
        g=c['generation'];pre='readyset_controls/generation/'+code;g['policy_id']=a['policy_id']
        g['result']={'execution':'COMPLETED','effective_actions':g['actions'],'process_argv':['/FAKE_INSTALL/ready_set.py'],
            'process_argv_policy':'EXPLICIT_API_ARGUMENTS_NO_PROCESS_OPTIONS'}
        g['trace']['events'][0].update(status='RETURNED',process_argv=['/FAKE_INSTALL/ready_set.py']);g['trace']['events'][0].pop('exception_type');g['trace']['events'][0].pop('message')
        data=b'FAKE GENERATED NUMERICAL CIF';members[pre+'/'+code+'.cif']=data
        g['candidate'].update(classification='COMPLETED_READYSET_OUTPUT',generation_claim='COMPLETED_READYSET_OUTPUT',source_bytes_match=False,sha256=sha256(data).hexdigest(),size=len(data))
        m.CEDAR42_CANDIDATE_SHA256[code]=sha256(data).hexdigest()
        n={'policy_id':'cif-native-bundle-inventory-v1','status':'REVIEW','source_preserved':True,'frozen_inputs_preserved':True,
            'execution':{'status':'COMPLETED','returncode':0},'inputs':[], 'outputs':[],
            'native_validation':{'status':'REVIEW','fatal_problems':None,'unused_definitions':[],'unsupported_fields':[],
                'atom_count':23,'atoms':[{'i_seq':i,'atom_id':'X'+str(i)} for i in range(23)],'restraint_policy':{'secondary_structure_enabled':False}}}
        c['native_interpretation']=n;c['native_triple_screen']={'status':'REVIEW','target_screen':'PASS','linear_axis_torsions':[{}, {}, {}]}
        c['dictionary_triple_screen']={'status':'REVIEW','target_screen':'PASS','linear_axis_torsions':[{}]*6}
        np=m.CEDAR42_NATIVE_PREFIX[code];members[np+'/native_worker.py']=b'FAKE NATIVE WORKER'
        for role,path,content in [('model','inputs/000_model.pdb',b'FAKE MODEL'),('dictionary','inputs/001_dictionary.cif',data),('phil','inputs/002_phil.phil',b'FAKE POLICY')]:
            members[np+'/'+path]=content;n['inputs'].append({'role':role,'anchor':'native_directory','path':path,'size':len(content),'sha256':sha256(content).hexdigest()})
    return m,members,r


def save(m,members,r):
    a=r['readyset_generation_audit']
    for code,c in a['cases'].items():
        pre='readyset_controls/generation/'+code;g=deepcopy(c['generation']);g.pop('directory')
        for name,data in [('readyset_generation_receipt.json',g),('readyset_result.json',g['result']),('call_trace.json',g['trace'])]:members[pre+'/'+name]=json.dumps(data).encode()
        np=m.CEDAR42_NATIVE_PREFIX[code];n=c['native_interpretation'];members[np+'/native_receipt.json']=json.dumps(n).encode();members[np+'/native_validation.json']=json.dumps(n['native_validation']).encode()
    members['readyset_controls/readyset_control_receipt.json']=json.dumps(a).encode()


@pytest.mark.parametrize('defect',['none','native_failure','source_copy','options_leak','actions','worker','native_worker','snapshot','missing_triple','hide_torsions','adoption','wrong_native_dictionary'])
def test_completed_return_gate_preserves_numerical_scope_and_open_findings(defect):
    m,members,r=fixture();c=r['readyset_generation_audit']['cases']['PDU'];g=c['generation'];np=m.CEDAR42_NATIVE_PREFIX['PDU']
    if defect=='native_failure':c['native_interpretation']['execution']['returncode']=1
    if defect=='source_copy':g['candidate']['source_bytes_match']=True
    if defect=='options_leak':g['result']['process_argv'].append('ready_set.actions.hydrogens=False')
    if defect=='actions':g['result']['effective_actions']['hydrogens']=True
    if defect=='worker':members['readyset_controls/generation/PDU/readyset_worker.py']=b'CHANGED'
    if defect=='native_worker':members[np+'/native_worker.py']=b'CHANGED'
    if defect=='snapshot':members['readyset_controls/generation/PDU/api_sources/ready_set.py.txt']=b'CHANGED'
    if defect=='missing_triple':c['native_triple_screen']['target_screen']='REVIEW'
    if defect=='hide_torsions':c['native_triple_screen']['linear_axis_torsions']=[]
    if defect=='adoption':r['readyset_generation_audit']['automatic_adoption']=True
    if defect=='wrong_native_dictionary':members[np+'/inputs/001_dictionary.cif']=b'OTHER'
    save(m,members,r)
    if defect=='none':m._check_completed_readyset_return(members,r)
    else:
        with pytest.raises(ValueError):m._check_completed_readyset_return(members,r)
