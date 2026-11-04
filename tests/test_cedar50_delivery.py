"""C49 traces and fresh controls must be replayed without hiding hand reviews."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar49_delivery import returned as previous_return


def save(members,r):
    for c in r['source_constructor_audit']['cases'].values():
        for key in ['native','control_native']:
            n=c[key];p=n['directory']['path'];members[p+'/constructor_result.json']=json.dumps(n['result']).encode()
            n['outputs']=[{'anchor':'constructor_directory','path':path.removeprefix(p+'/'),'sha256':sha256(data).hexdigest(),'size':len(data)}
                for path,data in members.items() if path.startswith(p+'/') and not path.endswith('/constructor_receipt.json')]
            members[p+'/constructor_receipt.json']=json.dumps({k:v for k,v in n.items() if k!='directory'}).encode()
    members['source_constructor_receipt.json']=json.dumps(r['source_constructor_audit']).encode()


def returned(tmp_path):
    from nasolve.cif_constructor_trace import POLICY_ID,analyze_constructor_trace,compare_constructor_runs
    m,members,r=previous_return(tmp_path);prior=deepcopy(r);a=r['source_constructor_audit']
    for c in a['cases'].values():c['native']['execution']['timeout_seconds']=30
    a.update(native_execution='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_TRACE',trace_policy_id=POLICY_ID,observer_control='FRESH_UNOBSERVED_AND_OBSERVED_RUNS',native_internal_observation='METHOD_BOUNDARIES_ONLY')
    m.CEDAR49_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_OBSERVED_WORKER').hexdigest()
    methods={'ChiralClass':['GenerateZMatrixClass','Chiralise','GetRestrainedParameters','TightenRestraints','Optimise','GetRSNotation'],
             'CCTBXMixins':['OptimiseCCTBX'],'TopologyMixins':['Chiralise']}
    payloads={cls:('class '+cls+':\n'+''.join(' def '+name+'(self):pass\n' for name in names)).encode() for cls,names in methods.items()}
    m.CEDAR48_BACKEND_SHA256=sha256(payloads['CCTBXMixins']).hexdigest()
    for code,c in a['cases'].items():
        n=c['native'];p=n['directory']['path'];sources=n['sources']+n['result']['backend_control']['sources']
        method_sources=[]
        for row in sources:
            cls=row['path'].removesuffix('.py').split('/')[-1]
            if cls in payloads:
                payload=payloads[cls];members[p+'/'+row['snapshot']['path']]=payload;row.update(size=len(payload),sha256=sha256(payload).hexdigest())
                for i,name in enumerate(methods[cls]):method_sources.append({'method':cls+'.'+name,'module':'elbow.'+row['path'].split('/elbow/')[-1].removesuffix('.py').replace('/','.'),'path':row['path'],'sha256':row['sha256'],'definition_line':i+2})
        for row in n['result']['backend_control']['methods'].values():row['sha256']=m.CEDAR48_BACKEND_SHA256
        c['control_native']=deepcopy(n);control=c['control_native'];cp='source_constructor_control/'+code;control['directory']['path']=cp
        for path,data in list(members.items()):
            if path.startswith(p+'/'):members[cp+'/'+path.removeprefix(p+'/')]=data
        snap=n['result']['constructor'];trace={'policy_id':POLICY_ID,'hooks':[v['method'] for v in method_sources],'method_sources':method_sources,
            'before':deepcopy(snap['promoted']),'after':deepcopy(snap['after']),'methods_restored':True,'source_hashes_preserved':True,'events':[
             {'call_id':0,'parent_call_id':None,'method':'TopologyMixins.Chiralise','phase':'enter','snapshot':deepcopy(snap['promoted']),'arguments_forwarded_unchanged':True,'local_atoms':[]},
             {'call_id':0,'parent_call_id':None,'method':'TopologyMixins.Chiralise','phase':'exit','snapshot':deepcopy(snap['after']),'status':'COMPLETED','local_atoms':[]}]}
        n['result']['constructor_trace']=trace;n['trace_analysis']=analyze_constructor_trace(tmp_path/(code+'.cif'),code,trace)
        c['observer_comparison']=compare_constructor_runs(control,n,prior['source_constructor_audit']['cases'][code]['native'])
        members[p+'/constructor_worker.py']=b'EXPLICIT_FAKE_OBSERVED_WORKER'
        members[p+'/constructor_spec.json']=json.dumps({'component':code,'native_cctbx':True,'trace_sources':[row for row in n['sources'] if row['path'].endswith('/elbow/chemistry/ChiralClass.py')]+n['result']['backend_control']['sources']}).encode()
    members['inputs/review/probe_receipt.json']=json.dumps(prior).encode();save(members,r)
    return m,members,r


@pytest.mark.parametrize('defect',['none','hidden_hand','hidden_trace','comparison','control_worker','observed_worker','trace_endpoint','hook_source','hook_line','backend','spec','control_endpoint','budget','adoption','mapping_before'])
def test_trace_return_replays_both_workers_raw_boundaries_and_previous_endpoint(tmp_path,defect):
    m,members,r=returned(tmp_path);c=r['source_constructor_audit']['cases']['DP'];n=c['native'];p=n['directory']['path']
    if defect=='hidden_hand':n['qualification']['checks']['source_handedness_preserved']=True
    if defect=='hidden_trace':n['trace_analysis']['checks_pass']=False
    if defect=='comparison':c['observer_comparison']['previous_endpoint_match']=False
    if defect=='control_worker':members[c['control_native']['directory']['path']+'/constructor_worker.py']=b'CHANGED'
    if defect=='observed_worker':members[p+'/constructor_worker.py']=b'CHANGED'
    if defect=='trace_endpoint':n['result']['constructor_trace']['after']['atoms'][0]['xyz'][0]+=1
    if defect=='hook_source':n['result']['constructor_trace']['method_sources'][0]['sha256']='CHANGED'
    if defect=='hook_line':n['result']['constructor_trace']['method_sources'][0]['definition_line']+=1
    if defect=='backend':n['result']['backend_control']['selected_value']=False
    if defect=='spec':members[p+'/constructor_spec.json']=json.dumps({'component':'DP','native_cctbx':True,'trace_sources':[]}).encode()
    if defect=='control_endpoint':c['control_native']['result']['constructor']['after']['atoms'][0]['xyz'][0]+=1
    if defect=='budget':n['execution']['timeout_seconds']=31
    if defect=='adoption':r['source_constructor_audit']['automatic_adoption']=True
    if defect=='mapping_before':n['result']['constructor_trace']['mapping_policy_id']='CHANGED'
    save(members,r)
    if defect=='none':
        replay=m._check_constructor_trace_return(members,r)
        assert all(v['failed_checks']==['source_handedness_preserved'] and v['observer_comparison']['checks_pass'] for v in replay.values())
    else:
        with pytest.raises(ValueError):m._check_constructor_trace_return(members,r)
