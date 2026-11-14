"""Boundary observation must retain the returned C48 handedness warnings."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar48_delivery import returned as prior_return,save
from tests.test_cif_constructor_backend import REFERENCE


def returned(tmp_path):
    from nasolve.cif_source_constructor import BACKEND_POLICY_ID,native_cctbx_reference,qualify_constructor_evidence
    m,members,r=prior_return(tmp_path);a=r['source_constructor_audit']
    a.update(backend_policy_id=BACKEND_POLICY_ID,native_backend_selection='EXPLICIT_NATIVE_CCTBX',native_execution='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_HANDOFF')
    m.CEDAR48_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_BACKEND_WORKER').hexdigest();payload=b'# EXPLICIT_FAKE_BACKEND_SOURCE'
    m.CEDAR48_BACKEND_SHA256=sha256(payload).hexdigest()
    for code,c in a['cases'].items():
        n=c['native'];p=n['directory']['path'];x=n['result'];constructor=x['constructor'];snapshot=constructor['promoted']
        constructor.update(status='COMPLETED',after_format=x['reader']['format']);constructor.pop('exception_type');constructor.pop('message')
        for atom in constructor['after']['atoms']:atom['xyz'][2]*=-1
        row={'anchor':'phenix_installation','path':'site/elbow/cctbx_api/CCTBXMixins.py','size':len(payload),'sha256':sha256(payload).hexdigest(),
            'snapshot':{'anchor':'constructor_directory','path':'backend_sources/CCTBXMixins.py.txt'}}
        x['backend_control']={'policy_id':BACKEND_POLICY_ID,'status':'NATIVE_CCTBX_PREPARATION_PASS',
            'reference':native_cctbx_reference(REFERENCE),'previous_value':False,'selected_value':True,
            'before':deepcopy(snapshot),'after':deepcopy(snapshot),'before_format':x['reader']['format'],'after_format':x['reader']['format'],
            'methods':{name:{'module':'elbow.cctbx_api.CCTBXMixins','path':row['path'],'sha256':row['sha256'],'selected_source':True} for name in ['SetCCTBX','GetCCTBX']},'sources':[row]}
        members[p+'/'+row['snapshot']['path']]=payload;members[p+'/constructor_worker.py']=b'EXPLICIT_FAKE_BACKEND_WORKER'
        members[p+'/constructor_spec.json']=json.dumps({'component':code,'native_cctbx':True}).encode()
        members[p+'/elbow/utilities/Utilities.py.txt']=REFERENCE.encode()
        for source in n['sources']:
            if source['snapshot']['path']=='elbow/utilities/Utilities.py.txt':source.update(size=len(REFERENCE.encode()),sha256=sha256(REFERENCE.encode()).hexdigest())
        n['qualification']=qualify_constructor_evidence(tmp_path/(code+'.cif'),code,x,c['reader_dialect'],native_cctbx=True)
    save(members,r);return m,members,r


@pytest.mark.parametrize('defect',['none','hide_hand_review','backend_flag','backend_state','reference','backend_source','method_source','worker','missing_after','charge','status','traced_before','adoption'])
def test_completed_constructor_return_keeps_hand_reviews_and_exact_backend_proof(tmp_path,defect):
    m,members,r=returned(tmp_path);a=r['source_constructor_audit'];n=a['cases']['PDU']['native'];b=n['result']['backend_control'];p=n['directory']['path']
    if defect=='hide_hand_review':n['qualification']['checks']['source_handedness_preserved']=True
    if defect=='backend_flag':b['selected_value']=False
    if defect=='backend_state':b['after']['atoms'][0]['xyz'][0]+=1
    if defect=='reference':b['reference']['setter_line']+=1
    if defect=='backend_source':members[p+'/'+b['sources'][0]['snapshot']['path']]=b'CHANGED'
    if defect=='method_source':b['methods']['SetCCTBX']['sha256']='CHANGED'
    if defect=='worker':members[p+'/constructor_worker.py']=b'CHANGED'
    if defect=='missing_after':n['result']['constructor'].pop('after_format')
    if defect=='charge':n['result']['constructor']['after']['atoms'][0]['native_atom_charge']=1
    if defect=='status':n['result']['constructor']['status']='EXCEPTION'
    if defect=='traced_before':members[p+'/constructor_spec.json']=json.dumps({'component':'PDU','native_cctbx':True,'trace_sources':[]}).encode()
    if defect=='adoption':a['automatic_adoption']=True
    save(members,r)
    if defect=='none':
        q=m._check_constructor_return(members,r,backend=True)
        assert all(v['qualification']['constructor_status']=='COMPLETED' and v['failed_checks']==['source_handedness_preserved'] for v in q.values())
    else:
        with pytest.raises(ValueError):m._check_constructor_return(members,r,backend=True)
