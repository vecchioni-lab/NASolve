"""C51's empty key observations remain immutable when the adapter is corrected."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from tests.test_cedar51_delivery import returned as previous_return, save


def returned(tmp_path):
    from nasolve.cif_constructor_index_basis import POLICY_ID, analyze_index_basis
    from nasolve.cif_constructor_trace import analyze_constructor_trace
    from nasolve.cif_constructor_mapping import analyze_constructor_mapping
    m,members,r=previous_return(tmp_path);a=r['source_constructor_audit']
    a.update(native_execution='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS',index_policy_id=POLICY_ID)
    m.CEDAR51_WORKER_SHA256=sha256(b'EXPLICIT_FAKE_INDEX_WORKER').hexdigest()
    for code,c in a['cases'].items():
        n=c['native'];p=n['directory']['path'];t=n['result']['constructor_trace'];rows=[]
        for filename,data in [('RestraintClass.py',b'class RestraintClass:\n def GetRestraints(self):pass\n'),('geometry_manager.py',b'def run(coordinates):pass\n')]:
            row={'anchor':'phenix_installation','path':'site/elbow/cctbx_api/'+filename,'size':len(data),'sha256':sha256(data).hexdigest(),
                 'snapshot':{'anchor':'constructor_directory','path':'index_sources/elbow/cctbx_api/'+filename+'.txt'}}
            members[p+'/'+row['snapshot']['path']]=data;rows.append(row)
        n['index_sources']=rows;t.update(index_policy_id=POLICY_ID,index_sources=deepcopy(rows),index_method_sources=[
            {'method':'geometry_manager.run','module':'elbow.cctbx_api.geometry_manager','path':rows[1]['path'],'sha256':rows[1]['sha256'],'definition_line':1}])
        for i in range(1,4):
            start={'call_id':i,'parent_call_id':0,'method':'ChiralClass.GetRestrainedParameters','phase':'enter',
                   'snapshot':deepcopy(t['before']),'local_atoms':[],'arguments_forwarded_unchanged':True}
            end={**deepcopy(start),'phase':'exit','status':'COMPLETED','mapping':{'index_basis':{'native_atom_keys':[],
                 'restraint_method':{'method':'RestraintClass.GetRestraints','module':'elbow.cctbx_api.RestraintClass',
                 'path':rows[0]['path'],'sha256':rows[0]['sha256'],'definition_line':2},'returned_coordinates':[],
                 'returned_chirality_parameters':[]}}}
            t['events'][-1:-1]=[start,end]
        n['trace_analysis']=analyze_constructor_trace(tmp_path/(code+'.cif'),code,t)
        n['mapping_analysis']=analyze_constructor_mapping(tmp_path/(code+'.cif'),code,t)
        n['index_analysis']=analyze_index_basis(tmp_path/(code+'.cif'),code,t)
        spec=json.loads(members[p+'/constructor_spec.json']);spec.update(index_basis=True,index_sources=rows)
        members[p+'/constructor_spec.json']=json.dumps(spec).encode();members[p+'/constructor_worker.py']=b'EXPLICIT_FAKE_INDEX_WORKER'
    save(members,r);return m,members,r


@pytest.mark.parametrize('defect',['none','hide_index','integer_keys_before','missing_source','source_bytes','source_hash','factory_line','restraint_line','worker','control_worker','changed_hand','changed_mapping'])
def test_index_return_replays_failed_adapter_and_pins_both_native_sources(tmp_path,defect):
    m,members,r=returned(tmp_path);c=r['source_constructor_audit']['cases']['PDU'];n=c['native'];p=n['directory']['path']
    spec=json.loads(members[p+'/constructor_spec.json']);t=n['result']['constructor_trace']
    if defect=='hide_index':n['index_analysis']['checks_pass']=True
    if defect=='integer_keys_before':spec['integer_keys']=True
    if defect=='missing_source':n['index_sources'].pop()
    if defect=='source_bytes':members[p+'/'+n['index_sources'][0]['snapshot']['path']]+=b'CHANGED'
    if defect=='source_hash':n['index_sources'][0]['sha256']='CHANGED'
    if defect=='factory_line':t['index_method_sources'][0]['definition_line']+=1
    if defect=='restraint_line':t['events'][2]['mapping']['index_basis']['restraint_method']['definition_line']+=1
    if defect=='worker':members[p+'/constructor_worker.py']=b'CHANGED'
    if defect=='control_worker':members[c['control_native']['directory']['path']+'/constructor_worker.py']=b'CHANGED'
    if defect=='changed_hand':n['qualification']['checks']['source_handedness_preserved']=True
    if defect=='changed_mapping':n['mapping_analysis']['checks_pass']=True
    members[p+'/constructor_spec.json']=json.dumps(spec).encode();save(members,r)
    if defect=='none':
        q=m._check_constructor_trace_return(members,r,mapping=True,index=True)
        assert all(v['index_analysis']['status']=='REVIEW' and v['failed_checks']==['source_handedness_preserved'] for v in q.values())
    else:
        with pytest.raises(ValueError):m._check_constructor_trace_return(members,r,mapping=True,index=True)
