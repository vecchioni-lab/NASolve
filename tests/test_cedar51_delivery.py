"""C50 mapping reviews are immutable prerequisites for a named-basis proof."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar50_delivery import returned as prior_return,save


def returned(tmp_path):
    from nasolve.cif_constructor_mapping import POLICY_ID,analyze_constructor_mapping
    m,members,r=prior_return(tmp_path);a=r['source_constructor_audit'];a.update(native_execution='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_MAPPING',mapping_policy_id=POLICY_ID)
    m.CEDAR50_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_MAPPING_WORKER').hexdigest()
    extra=['GetCoordinates','SetCoordinates','GetNewManager']
    for code,c in a['cases'].items():
        n=c['native'];p=n['directory']['path'];cp=c['control_native']['directory']['path'];t=n['result']['constructor_trace'];t['mapping_policy_id']=POLICY_ID
        row=n['result']['backend_control']['sources'][0];snapshot=row['snapshot']['path'];payload=members[p+'/'+snapshot]+''.join(' def '+name+'(self):pass\n' for name in extra).encode()
        digest=sha256(payload).hexdigest();m.CEDAR48_BACKEND_SHA256=digest
        for key,path in [('native',p),('control_native',cp)]:
            b=c[key]['result']['backend_control'];b['sources'][0].update(size=len(payload),sha256=digest)
            for v in b['methods'].values():v['sha256']=digest
            members[path+'/'+snapshot]=payload
        for v in t['method_sources']:
            if v['module']=='elbow.cctbx_api.CCTBXMixins':v['sha256']=digest
        t['method_sources'] +=[{'method':'CCTBXMixins.'+name,'module':'elbow.cctbx_api.CCTBXMixins','path':row['path'],'sha256':digest,'definition_line':i+3} for i,name in enumerate(extra)]
        t['hooks']=[v['method'] for v in t['method_sources']]
        spec=json.loads(members[p+'/constructor_spec.json']);spec.update(coordinate_mapping=True,trace_sources=[v for v in n['sources'] if v['path'].endswith('/elbow/chemistry/ChiralClass.py')]+n['result']['backend_control']['sources'])
        members[p+'/constructor_spec.json']=json.dumps(spec).encode();members[p+'/constructor_worker.py']=b'EXPLICIT_FAKE_MAPPING_WORKER'
        n['mapping_analysis']=analyze_constructor_mapping(tmp_path/(code+'.cif'),code,t)
    save(members,r);return m,members,r


@pytest.mark.parametrize('defect',['none','hide_mapping','hide_hand','mapping_spec','worker','control_worker','mapping_policy','index_before','method_line','coordinate_snapshot','budget','comparison'])
def test_mapping_return_preserves_raw_legacy_reviews_and_exact_worker_scope(tmp_path,defect):
    m,members,r=returned(tmp_path);c=r['source_constructor_audit']['cases']['PDU'];n=c['native'];p=n['directory']['path'];spec=json.loads(members[p+'/constructor_spec.json'])
    if defect=='hide_mapping':n['mapping_analysis']['checks_pass']=True
    if defect=='hide_hand':n['qualification']['checks']['source_handedness_preserved']=True
    if defect=='mapping_spec':spec['coordinate_mapping']=False
    if defect=='worker':members[p+'/constructor_worker.py']=b'CHANGED'
    if defect=='control_worker':members[c['control_native']['directory']['path']+'/constructor_worker.py']=b'CHANGED'
    if defect=='mapping_policy':n['result']['constructor_trace']['mapping_policy_id']='CHANGED'
    if defect=='index_before':spec['index_basis']=True
    if defect=='method_line':n['result']['constructor_trace']['method_sources'][-1]['definition_line']+=1
    if defect=='coordinate_snapshot':n['result']['constructor_trace']['after']['atoms'][0]['xyz'][0]+=1
    if defect=='budget':n['execution']['timeout_seconds']=31
    if defect=='comparison':c['observer_comparison']['previous_endpoint_match']=False
    members[p+'/constructor_spec.json']=json.dumps(spec).encode();save(members,r)
    if defect=='none':
        replay=m._check_constructor_trace_return(members,r,mapping=True)
        assert all(v['mapping_analysis']['status']=='REVIEW' and v['failed_checks']==['source_handedness_preserved'] for v in replay.values())
    else:
        with pytest.raises(ValueError):m._check_constructor_trace_return(members,r,mapping=True)
