"""Proved integer-key evidence must survive before native Setup is introduced."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar52_delivery import returned as previous_return,save


@pytest.mark.parametrize('delivery,field',[('46_Cedar','source_constructor_audit_only'),('47_Cedar','source_constructor_backend_audit_only'),
    ('48_Cedar','source_constructor_trace_audit_only'),('49_Cedar','source_constructor_mapping_audit_only'),
    ('50_Cedar','source_constructor_index_basis_audit_only'),('51_Cedar','source_constructor_index_basis_audit_only'),
    ('52_Cedar','source_constructor_setup_audit_only'),('29_Cedar',None)])
@pytest.mark.parametrize('wrong',[False,True])
def test_constructor_action_routing_keeps_setup_separate_from_legacy_index_mode(tmp_path,delivery,field,wrong):
    from types import SimpleNamespace
    from pathlib import Path
    import importlib.util
    spec=importlib.util.spec_from_file_location('constructor_routing',Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);args=SimpleNamespace()
    if field:setattr(args,field,True)
    if wrong:args.source_constructor_index_basis_audit_only=not getattr(args,'source_constructor_index_basis_audit_only',False)
    if wrong:
        with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
    else:m._check_constructor_input_mode(args,delivery)


def returned(tmp_path):
    from nasolve.cif_constructor_index_basis import INTEGER_KEYS_POLICY_ID,analyze_index_basis
    m,members,r=previous_return(tmp_path);r['source_constructor_audit']['index_policy_id']=INTEGER_KEYS_POLICY_ID
    m.CEDAR52_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_INTEGER_KEYS_WORKER').hexdigest()
    for code,c in r['source_constructor_audit']['cases'].items():
        n=c['native'];p=n['directory']['path'];t=n['result']['constructor_trace'];t['index_policy_id']=INTEGER_KEYS_POLICY_ID
        row=n['index_sources'][0];payload=members[p+'/'+row['snapshot']['path']]+b' def get_key(self,atom):pass\n def GetCoordinates(self):pass\n'
        row.update(sha256=sha256(payload).hexdigest(),size=len(payload));members[p+'/'+row['snapshot']['path']]=payload
        t['index_sources']=deepcopy(n['index_sources'])
        for event in t['events']:
            if event.get('method')!='ChiralClass.GetRestrainedParameters' or event.get('phase')!='exit':continue
            b=event['mapping']['index_basis'];b['restraint_method']['sha256']=row['sha256']
            b['integer_key_methods']=[{**b['restraint_method'],'method':'RestraintClass.'+name,'definition_line':line} for name,line in [('get_key',3),('GetCoordinates',4)]]
        spec=json.loads(members[p+'/constructor_spec.json']);spec.update(integer_keys=True,index_sources=n['index_sources'])
        members[p+'/constructor_spec.json']=json.dumps(spec).encode();members[p+'/constructor_worker.py']=b'EXPLICIT_FAKE_INTEGER_KEYS_WORKER'
        n['index_analysis']=analyze_index_basis(tmp_path/(code+'.cif'),code,t)
    save(members,r);return m,members,r


@pytest.mark.parametrize('defect',['none','setup_before','setup_source_before','hide_hand','hide_index','integer_flag','policy','key_method_line','key_method_source','missing_key_method','worker','comparison'])
def test_integer_key_return_is_replayed_without_setup_or_gate_relaxation(tmp_path,defect):
    m,members,r=returned(tmp_path);c=r['source_constructor_audit']['cases']['PDU'];n=c['native'];p=n['directory']['path'];t=n['result']['constructor_trace']
    spec=json.loads(members[p+'/constructor_spec.json']);params=[e['mapping']['index_basis'] for e in t['events'] if e.get('method')=='ChiralClass.GetRestrainedParameters' and e.get('phase')=='exit']
    if defect=='setup_before':spec['source_setup']=True
    if defect=='setup_source_before':spec['setup_sources']=[]
    if defect=='hide_hand':n['qualification']['checks']['source_handedness_preserved']=True
    if defect=='hide_index':n['index_analysis']['checks_pass']=True
    if defect=='integer_flag':spec['integer_keys']=False
    if defect=='policy':t['index_policy_id']='CHANGED'
    if defect=='key_method_line':params[0]['integer_key_methods'][0]['definition_line']+=1
    if defect=='key_method_source':params[0]['integer_key_methods'][0]['sha256']='CHANGED'
    if defect=='missing_key_method':params[0]['integer_key_methods'].pop()
    if defect=='worker':members[p+'/constructor_worker.py']=b'CHANGED'
    if defect=='comparison':c['observer_comparison']['previous_endpoint_match']=False
    members[p+'/constructor_spec.json']=json.dumps(spec).encode();save(members,r)
    if defect=='none':
        q=m._check_constructor_trace_return(members,r,mapping=True,index=True,integer_keys=True)
        assert all(v['failed_checks']==['source_handedness_preserved'] for v in q.values())
    else:
        with pytest.raises(ValueError):m._check_constructor_trace_return(members,r,mapping=True,index=True,integer_keys=True)
