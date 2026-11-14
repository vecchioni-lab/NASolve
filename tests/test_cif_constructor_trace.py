"""Trace local construction without changing its chemistry or native arguments."""
from copy import deepcopy
import json,os
import pytest
from tests.test_cif_constructor_backend import installation
from tests.test_cif_source_constructor import evidence
from tests.test_cif_stereochemistry_audit import tetrahedron,write


@pytest.mark.parametrize('code',['Q17','ZZ9'])
@pytest.mark.parametrize('change',['none','rotation','inversion','flat','missing'])
def test_all_neighbor_bases_and_four_neighbor_volume_are_source_relative(tmp_path,code,change):
    from nasolve.cif_constructor_trace import assess_snapshot_hands
    v,_=tetrahedron(code);p=write(tmp_path/'source.cif',v);snapshot=evidence(v)['constructor']['after']
    for a in snapshot['atoms']:
        x,y,z=a['xyz']
        if change=='rotation':a['xyz']=[-y+3,x+2,z-1]
        if change=='inversion':a['xyz']=[x,y,-z]
        if change=='flat':a['xyz']=[x,y,0.]
    if change=='missing':snapshot['atoms'].pop()
    q=assess_snapshot_hands(p,code,snapshot);c=q['centres'][0]
    assert c['centre']=='CTR' and len(c['triple_bases'])==4
    assert c['all_bases_preserve_hand'] is (change in {'none','rotation'})
    assert c['four_neighbor_hand_preserved'] is (change in {'none','rotation'})
    assert q['absolute_cip_assignment']=='NOT_RUN'


def fake_trace_installation(tmp_path,mode):
    from hashlib import sha256
    root,python,site,proof,api=installation(tmp_path,'correct')
    p=site/'elbow/cctbx_api/CCTBXMixins.py';p.write_text(p.read_text()+''' def OptimiseCCTBX(self,enforce_chiral=True,return_lbfgs_object=False):
  assert enforce_chiral is False and return_lbfgs_object is True
  self.GetRestrainedParameters()
  MODE
  return None,None
'''.replace('MODE',"raise RuntimeError('EXPLICIT_FAKE_LOCAL_EXCEPTION')" if mode=='exception' else 'pass'))
    p=site/'elbow/chemistry/ChiralClass.py';p.write_text('''from ..cctbx_api.CCTBXMixins import CCTBXMixins
class ChiralClass(list,CCTBXMixins):
 def __init__(self,parent):
  self+=parent;self.parent=parent;self.chiral_atom=parent[0]
 def GenerateZMatrixClass(self):
  MODE
 def Chiralise(self,switch_atoms_only=False):pass
 def GetRSNotation(self,input_xyz=False,explain=False):return 'R'
 def TightenRestraints(self):pass
 def GetRestrainedParameters(self,additional_restraints=None):
  self.TightenRestraints();self.GetRSNotation()
 def Optimise(self,atom_selection=None,explain=False):
  self.OptimiseCCTBX(enforce_chiral=False,return_lbfgs_object=True)
  self.TightenRestraints();self.GetRSNotation()
'''.replace('MODE',"\n  for a in self:a.xyz.z=-a.xyz.z" if mode=='inverted' else 'pass'))
    p=site/'elbow/chemistry/TopologyMixins.py';p.write_text('''from .ChiralClass import ChiralClass
class TopologyMixins:
 def Chiralise(self,chiral_treatment='retain'):
  assert self.GetCCTBX() is True
  for i,a in enumerate(self):a.index=i+1
  c=ChiralClass(self);c.GenerateZMatrixClass();c.Chiralise();c.Optimise()
''')
    if mode=='unsupported':
        p=site/'elbow/chemistry/ChiralClass.py';p.write_text(p.read_text().replace('def TightenRestraints','def RemovedMethod'))
    for row in proof:
        data=(root/row['path']).read_bytes();row.update(size=len(data),sha256=sha256(data).hexdigest())
    trace=[]
    for name in ['elbow/chemistry/ChiralClass.py','elbow/cctbx_api/CCTBXMixins.py']:
        data=(site/name).read_bytes();trace.append({'anchor':'phenix_installation','path':'lib/python3.11/site-packages/'+name,'size':len(data),'sha256':sha256(data).hexdigest()})
    return root,python,site,proof,api,trace


@pytest.mark.parametrize('mode',['correct','inverted','exception','unsupported'])
def test_owned_observer_preserves_original_calls_and_restores_native_methods(tmp_path,mode):
    from nasolve.cif_source_constructor import audit_source_constructor
    root,python,site,proof,api,trace=fake_trace_installation(tmp_path,mode);v,_=tetrahedron();p=write(tmp_path/'inputs/source.cif',v)
    native=audit_source_constructor(root,python,api,p,'Q17',tmp_path/'observed',environment={**os.environ,'PYTHONPATH':str(site)},
        expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,native_cctbx=True,trace_chirality=True,trace_sources=trace,timeout_seconds=10)
    assert native['execution']['status']=='COMPLETED' and native['source_preserved'] and not native['automatic_adoption']
    if mode=='unsupported':
        assert native['result']['constructor']['status']=='EXCEPTION';return
    t=native['result']['constructor_trace'];q=native['trace_analysis']
    assert t['methods_restored'] and t['source_hashes_preserved'] and q['checks_pass']
    assert all(e['arguments_forwarded_unchanged'] for e in t['events'] if e['phase']=='enter')
    assert all(e['local_atoms'][0]['same_parent_object'] for e in t['events'])
    assert q['first_observed_hand_reviews']==([] if mode in {'correct','exception'} else [
        {'centre':'CTR','method':'ChiralClass.GenerateZMatrixClass','phase':'exit','event_index':2,'call_id':1}])
    if mode=='exception':assert native['result']['constructor']['status']=='EXCEPTION'
    else:
        control=audit_source_constructor(root,python,api,p,'Q17',tmp_path/'control',environment={**os.environ,'PYTHONPATH':str(site)},
            expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,native_cctbx=True,timeout_seconds=10)
        assert control['result']['constructor']['after']==native['result']['constructor']['after']


@pytest.mark.parametrize('defect',['none','nesting','snapshot','restore','arguments','policy','nonfinite','endpoint','call_cap','shared_atom'])
def test_trace_replay_rejects_changed_observation_evidence(tmp_path,defect):
    from nasolve.cif_constructor_trace import analyze_constructor_trace,POLICY_ID
    v,_=tetrahedron();source=write(tmp_path/'source.cif',v);snapshot=evidence(v)['constructor']['after']
    t={'policy_id':POLICY_ID,'before':snapshot,'after':snapshot,'methods_restored':True,'source_hashes_preserved':True,
        'hooks':['ChiralClass.GenerateZMatrixClass'],'events':[
          {'call_id':1,'parent_call_id':None,'method':'ChiralClass.GenerateZMatrixClass','phase':'enter','snapshot':deepcopy(snapshot),'arguments_forwarded_unchanged':True,'local_atoms':[]},
          {'call_id':1,'parent_call_id':None,'method':'ChiralClass.GenerateZMatrixClass','phase':'exit','snapshot':deepcopy(snapshot),'status':'COMPLETED','local_atoms':[]}]}
    if defect=='nesting':t['events'][1]['call_id']=2
    if defect=='snapshot':t['events'][0]['snapshot']['atoms'][0]['native_atom_charge']=-1
    if defect=='restore':t['methods_restored']=False
    if defect=='arguments':t['events'][0]['arguments_forwarded_unchanged']=False
    if defect=='policy':t['policy_id']='CHANGED'
    if defect=='nonfinite':t['events'][0]['snapshot']['atoms'][0]['xyz'][0]=float('nan')
    if defect=='endpoint':t['after']=deepcopy(snapshot);t['after']['atoms'][0]['xyz'][0]+=1
    if defect=='call_cap':t['call_cap_reached']=True
    if defect=='shared_atom':t['events'][0]['local_atoms']=[{'same_parent_object':True,'atom':'CTR','xyz':[1,2,3]}]
    q=analyze_constructor_trace(source,'Q17',t)
    assert q['checks_pass'] is (defect=='none')
    assert q['scientific_approval']=='NOT_RUN' and not q['automatic_adoption']


@pytest.mark.parametrize('defect',['none','endpoint','source','status','previous_endpoint'])
def test_fresh_repeat_comparison_is_distinct_from_handedness_and_old_endpoint(tmp_path,defect):
    from nasolve.cif_constructor_trace import compare_constructor_runs
    v,_=tetrahedron();x=evidence(v);n={'source_sha256':'explicit_source','execution':{'status':'COMPLETED','returncode':0},'result':x}
    control=deepcopy(n);observed=deepcopy(n);previous=deepcopy(n)
    if defect=='endpoint':observed['result']['constructor']['after']['atoms'][0]['xyz'][0]+=1
    if defect=='source':observed['source_sha256']='different'
    if defect=='status':observed['result']['constructor']['status']='EXCEPTION'
    if defect=='previous_endpoint':previous['result']['constructor']['after']['atoms'][0]['xyz'][0]+=1
    q=compare_constructor_runs(control,observed,previous)
    assert q['checks_pass'] is (defect in {'none','previous_endpoint'})
    assert q['previous_endpoint_match'] is (defect!='previous_endpoint')
    assert q['scientific_approval']=='NOT_RUN' and not q['automatic_adoption']
