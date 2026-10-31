"""Local template order, native proxy basis and writeback are separate gates."""
from copy import deepcopy
from hashlib import sha256
import os
import pytest
from tests.test_cif_constructor_trace import fake_trace_installation
from tests.test_cif_source_constructor import evidence
from tests.test_cif_stereochemistry_audit import tetrahedron,write


def mapping_trace(v):
    from nasolve.cif_constructor_mapping import POLICY_ID
    from nasolve.cif_constructor_trace import POLICY_ID as TRACE
    snap=evidence(v)['constructor']['after'];by={a['atom']:a for a in snap['atoms']}
    # Deliberately nonnumeric list order. No atom labels are special to the audit.
    names=['H','CTR','O','N','C'];indices=[5,1,2,3,4]
    local=[{'atom':n,'global_index':i,'xyz':by[n]['xyz'],'same_parent_object':True} for n,i in zip(names,indices)]
    events=[]
    def call(method,payload=None,args=None):
        k=len(events)//2
        events.extend([{'call_id':k,'parent_call_id':None,'method':method,'phase':'enter','snapshot':deepcopy(snap),'local_atoms':deepcopy(local),'centre':'CTR','arguments_forwarded_unchanged':True,'resolved_arguments':args or {},'mapping':payload or {}},
          {'call_id':k,'parent_call_id':None,'method':method,'phase':'exit','snapshot':deepcopy(snap),'local_atoms':deepcopy(local),'centre':'CTR','status':'COMPLETED','mapping':payload or {}}])
    xyz=[a['xyz'] for a in local]
    call('CCTBXMixins.GetCoordinates',{'coordinates_returned':xyz},{'cctbx_format':True,'proper_atoms_only':False})
    call('CCTBXMixins.SetCoordinates',{'coordinates_input':xyz},{'cctbx_format':True})
    call('CCTBXMixins.GetNewManager',{'chirality_proxies':[{'i_seqs':[1,2,3,4],'volume_ideal':1.,'weight':1.,'both_signs':False}]})
    return {'policy_id':TRACE,'mapping_policy_id':POLICY_ID,'before':snap,'after':snap,'events':events,'hooks':[e['method'] for e in events],
        'methods_restored':True,'source_hashes_preserved':True}


@pytest.mark.parametrize('code',['Q17','ZZ9'])
@pytest.mark.parametrize('defect',['none','getter_order','setter_order','proxy_index','target_sign','missing_getter','shared_identity','nonfinite'])
def test_mapping_replay_uses_named_local_order_and_never_approves_stereochemistry(tmp_path,code,defect):
    from nasolve.cif_constructor_mapping import analyze_constructor_mapping
    v,_=tetrahedron(code);source=write(tmp_path/'source.cif',v);t=mapping_trace(v)
    if defect=='getter_order':t['events'][1]['mapping']['coordinates_returned'].reverse()
    if defect=='setter_order':t['events'][2]['mapping']['coordinates_input'].reverse()
    if defect=='proxy_index':t['events'][5]['mapping']['chirality_proxies'][0]['i_seqs'][0]=99
    if defect=='target_sign':t['events'][5]['mapping']['chirality_proxies'][0]['volume_ideal']=-1.
    if defect=='missing_getter':t['events']=t['events'][2:]
    if defect=='shared_identity':t['events'][0]['local_atoms'][0]['same_parent_object']=False
    if defect=='nonfinite':t['events'][1]['mapping']['coordinates_returned'][0][0]=float('nan')
    q=analyze_constructor_mapping(source,code,t)
    assert q['checks_pass'] is (defect in {'none','target_sign'})
    assert q['target_source_hands_preserved'] is (defect not in {'target_sign','proxy_index'})
    assert q['absolute_cip_assignment']==q['scientific_approval']=='NOT_RUN' and not q['automatic_adoption']


@pytest.mark.parametrize('mode',['correct','reversed_getter','reversed_setter','exception'])
def test_owned_mapping_observer_forwards_original_calls_and_restores_methods(tmp_path,mode):
    from nasolve.cif_source_constructor import audit_source_constructor
    root,python,site,proof,api,trace=fake_trace_installation(tmp_path,'correct')
    p=site/'elbow/cctbx_api/CCTBXMixins.py';s=p.read_text()
    s=s[:s.index(' def OptimiseCCTBX')]+''' def GetCoordinates(self,cctbx_format=True,proper_atoms_only=False):
  values=[(a.xyz.x,a.xyz.y,a.xyz.z) for a in self]
  GET
  return values
 def SetCoordinates(self,coordinates,cctbx_format=True):
  values=list(coordinates)
  SET
  for a,xyz in zip(self,values):a.xyz.x,a.xyz.y,a.xyz.z=xyz
 def GetNewManager(self,additional_restraints=None):
  from types import SimpleNamespace
  self.GetRestrainedParameters()
  return SimpleNamespace(chirality_proxies=[SimpleNamespace(i_seqs=(0,1,2,3),volume_ideal=1.,weight=1.,both_signs=False)])
 def OptimiseCCTBX(self,enforce_chiral=True,return_lbfgs_object=False):
  assert enforce_chiral is False and return_lbfgs_object is True
  self.GetNewManager();xyz=self.GetCoordinates();self.SetCoordinates(xyz)
  EXCEPTION
  return xyz,None
'''.replace('GET','values.reverse()' if mode=='reversed_getter' else 'pass').replace('SET','values.reverse()' if mode=='reversed_setter' else 'pass').replace('EXCEPTION',"raise RuntimeError('EXPLICIT_FAKE_MAPPING_EXCEPTION')" if mode=='exception' else 'pass')
    p.write_text(s)
    for rows in [proof,trace]:
        for row in rows:
            data=(root/row['path']).read_bytes();row.update(size=len(data),sha256=sha256(data).hexdigest())
    v,_=tetrahedron();source=write(tmp_path/'inputs/source.cif',v)
    n=audit_source_constructor(root,python,api,source,'Q17',tmp_path/'native',environment={**os.environ,'PYTHONPATH':str(site)},
        expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,trace_sources=trace,native_cctbx=True,trace_chirality=True,coordinate_mapping=True,timeout_seconds=10)
    assert n['execution']['status']=='COMPLETED' and n['source_preserved'] and n['result']['constructor_trace']['methods_restored']
    q=n['mapping_analysis'];assert q['checks_pass'] is (mode in {'correct','exception'})
    assert n['result']['constructor']['status']==('EXCEPTION' if mode=='exception' else 'COMPLETED')
    assert not n['automatic_adoption'] and q['scientific_approval']=='NOT_RUN'


@pytest.mark.parametrize('code',['Q17','ZZ9'])
@pytest.mark.parametrize('transfer',['identity','sorted_index'])
@pytest.mark.parametrize('rotation',[False,True])
def test_post_optimizer_transfer_is_replayed_by_index_without_a_repair_or_cip_claim(tmp_path,code,transfer,rotation):
    from nasolve.cif_constructor_mapping import analyze_constructor_mapping
    v,_=tetrahedron(code);source=write(tmp_path/'source.cif',v);t=mapping_trace(v)
    local=deepcopy(t['events'][0]['local_atoms'])
    if rotation:
        for a in local:
            x,y,z=a['xyz'];a['xyz']=[-y+2,x+3,z-1]
    changed=deepcopy(local)
    if transfer=='sorted_index':
        expected={a['atom']:local[i]['xyz'] for i,a in enumerate(sorted(local,key=lambda a:a['global_index']))}
        for a in changed:a['xyz']=expected[a['atom']]
    def event(call,parent,method,phase,atoms):
        return {'call_id':call,'parent_call_id':parent,'method':method,'phase':phase,'local_atoms':atoms,'centre':'CTR','status':'COMPLETED'}
    t['events']+=[event(3,None,'ChiralClass.Optimise','enter',local),event(4,3,'ChiralClass.TightenRestraints','enter',local),
        event(4,3,'ChiralClass.TightenRestraints','exit',local),event(5,3,'ChiralClass.GetRSNotation','enter',changed),
        event(5,3,'ChiralClass.GetRSNotation','exit',changed),event(3,None,'ChiralClass.Optimise','exit',changed)]
    before=deepcopy(t);q=analyze_constructor_mapping(source,code,t);row=q['post_optimizer_transfers'][0]
    assert t==before and q['checks_pass'] and row['same_atom_order']
    assert row['coordinates_unchanged_by_identity'] is (transfer=='identity')
    assert row['matches_sorted_index_transfer'] is (transfer=='sorted_index')
    assert row['local_source_hand_before'] is True
    assert q['scientific_approval']=='NOT_RUN' and not q['automatic_adoption']
