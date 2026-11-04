"""Replay native Setup without turning temporary-frame reviews into a new gate."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar53_delivery import returned as previous_return,save
from tests.test_cif_constructor_setup import REFERENCE


def returned(tmp_path):
    from nasolve.cif_constructor_setup import qualify_setup_evidence,native_setup_reference,POLICY_ID
    m,members,r=previous_return(tmp_path);a=r['source_constructor_audit']
    a.update(native_execution='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INPUT_SETUP',setup_policy_id=POLICY_ID)
    m.CEDAR53_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_SETUP_OBSERVER').hexdigest()
    m.CEDAR53_CONTROL_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_SETUP_CONTROL').hexdigest()
    m.ELBOW_SOURCE_SHA256['elbow/command_line/builder.py']=sha256(REFERENCE.encode()).hexdigest()
    for code,c in a['cases'].items():
        for key in ['native','control_native']:
            n=c[key];p=n['directory']['path'];result=n['result'];before=result['constructor']['promoted']
            native=next(v for v in n['sources'] if v['path'].endswith('/elbow/chemistry/SimpleMoleculeClass.py'))
            payload=b'class SimpleMoleculeClass:\n def Setup(self):pass\n';native.update(sha256=sha256(payload).hexdigest(),size=len(payload))
            members[p+'/'+native['snapshot']['path']]=payload
            ss={'anchor':'phenix_installation','path':'site/elbow/command_line/builder.py','sha256':sha256(REFERENCE.encode()).hexdigest(),'size':len(REFERENCE),
                'snapshot':{'anchor':'constructor_directory','path':'setup_sources/elbow/command_line/builder.py.txt'}}
            n['setup_sources']=[ss];members[p+'/'+ss['snapshot']['path']]=REFERENCE.encode()
            cache=[{'atom':x['atom'],'input_xyz':x['xyz'],'aliases_current_xyz':True} for x in before['atoms']]
            result['setup_control']={'policy_id':POLICY_ID,'status':'NATIVE_SOURCE_SETUP_PASS','reference':native_setup_reference(REFERENCE),
                'before':deepcopy(before),'after':deepcopy(before),'before_format':result['constructor']['promoted_format'],
                'after_format':result['constructor']['promoted_format'],'input_before':[], 'input_after':cache,'input_after_constructor':deepcopy(cache),
                'method':{'module':'elbow.chemistry.SimpleMoleculeClass','path':native['path'],'sha256':native['sha256'],'definition_line':2,'selected_source':True}}
            n['setup_analysis']=qualify_setup_evidence(result)
            spec=json.loads(members[p+'/constructor_spec.json']);spec.update(source_setup=True,setup_sources=[ss])
            members[p+'/constructor_spec.json']=json.dumps(spec).encode()
            members[p+'/constructor_worker.py']=b'EXPLICIT_FAKE_SETUP_OBSERVER' if key=='native' else b'EXPLICIT_FAKE_SETUP_CONTROL'
    save(members,r);return m,members,r


@pytest.mark.parametrize('defect',['none','setup_flag','setup_source','method_line','method_hash','hidden_cache','changed_cache','reference','worker','control_worker','hidden_hand','comparison'])
def test_setup_return_replays_cache_sources_and_historical_hand_findings(tmp_path,defect):
    m,members,r=returned(tmp_path);c=r['source_constructor_audit']['cases']['PDU'];n=c['native'];p=n['directory']['path']
    spec=json.loads(members[p+'/constructor_spec.json']);setup=n['result']['setup_control']
    if defect=='setup_flag':spec['source_setup']=False
    if defect=='setup_source':members[p+'/'+n['setup_sources'][0]['snapshot']['path']]+=b'CHANGED'
    if defect=='method_line':setup['method']['definition_line']+=1
    if defect=='method_hash':setup['method']['sha256']='CHANGED'
    if defect=='hidden_cache':n['setup_analysis']['checks_pass']=False
    if defect=='changed_cache':setup['input_after_constructor'][0]['input_xyz'][0]+=1
    if defect=='reference':setup['reference']['setup_line']+=1
    if defect=='worker':members[p+'/constructor_worker.py']=b'CHANGED'
    if defect=='control_worker':members[c['control_native']['directory']['path']+'/constructor_worker.py']=b'CHANGED'
    if defect=='hidden_hand':n['qualification']['checks']['source_handedness_preserved']=True
    if defect=='comparison':c['observer_comparison']['previous_endpoint_match']=False
    members[p+'/constructor_spec.json']=json.dumps(spec).encode();save(members,r)
    if defect=='none':
        replay=m._check_constructor_trace_return(members,r,mapping=True,index=True,integer_keys=True,setup=True)
        assert all(v['setup_analysis']['checks_pass'] and v['failed_checks']==['source_handedness_preserved'] for v in replay.values())
    else:
        with pytest.raises(ValueError):m._check_constructor_trace_return(members,r,mapping=True,index=True,integer_keys=True,setup=True)


@pytest.mark.parametrize('delivery,flag',[('53_Cedar',True),('52_Cedar',False),('29_Cedar',False)])
def test_complete_generation_action_is_separate_from_constructor_audits(tmp_path,delivery,flag):
    from types import SimpleNamespace
    m,_,_=previous_return(tmp_path);args=SimpleNamespace(source_candidate_generation_only=flag,source_constructor_setup_audit_only=delivery=='52_Cedar')
    m._check_constructor_input_mode(args,delivery)
    args.source_candidate_generation_only=not flag
    with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
