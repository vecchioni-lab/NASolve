"""A native restraint index belongs to a proved named array, not list position."""
from copy import deepcopy
import pytest
from tests.test_cif_constructor_mapping import mapping_trace
from tests.test_cif_stereochemistry_audit import tetrahedron,write


def index_trace(v):
    from nasolve.cif_constructor_index_basis import POLICY_ID
    t=mapping_trace(v);local=deepcopy(t['events'][0]['local_atoms']);ordered=sorted(local,key=lambda a:a['global_index'])
    source={'method':'RestraintClass.GetRestraints','module':'elbow.cctbx_api.RestraintClass','path':'site/elbow/cctbx_api/RestraintClass.py','sha256':'a'*64,'definition_line':2}
    t.update(index_sources=[{'path':source['path'],'sha256':'a'*64},{'path':'site/elbow/cctbx_api/geometry_manager.py','sha256':'b'*64}],index_policy_id=POLICY_ID,index_method_sources=[{'method':'geometry_manager.run','module':'elbow.cctbx_api.geometry_manager','path':'site/elbow/cctbx_api/geometry_manager.py','sha256':'b'*64,'definition_line':1}])
    entry={'call_id':3,'parent_call_id':2,'method':'ChiralClass.GetRestrainedParameters','phase':'exit','centre':'CTR','status':'COMPLETED','local_atoms':local,
        'mapping':{'index_basis':{'restraint_method':source,'native_atom_keys':[{'atom':a['atom'],'global_index':a['global_index'],'stored_xyz':deepcopy(a['xyz']),'same_parent_object':True} for a in local],
            'returned_coordinates':[deepcopy(a['xyz']) for a in ordered],'returned_chirality_parameters':[[[0,1,2,3],1.,False,1.]]}}}
    t['events'][1]['parent_call_id']=2
    t['events'].insert(5,entry)
    t['events'][-1]['mapping']['chirality_proxies'][0]['i_seqs']=[0,1,2,3]
    return t


@pytest.mark.parametrize('code',['Q17','ZZ9'])
@pytest.mark.parametrize('defect',['none','missing_keys','duplicate_index','key_identity','stored_vector','returned_order','proxy_index','target_sign','method_source','wrong_module','duplicate_coordinates'])
def test_index_basis_requires_live_named_keys_and_exact_returned_vector_alignment(tmp_path,code,defect):
    from nasolve.cif_constructor_index_basis import analyze_index_basis
    v,_=tetrahedron(code);source=write(tmp_path/'source.cif',v);t=index_trace(v);basis=t['events'][5]['mapping']['index_basis']
    if defect=='missing_keys':basis.pop('native_atom_keys')
    if defect=='duplicate_index':basis['native_atom_keys'][0]['global_index']=basis['native_atom_keys'][1]['global_index']
    if defect=='key_identity':basis['native_atom_keys'][0]['same_parent_object']=False
    if defect=='stored_vector':basis['native_atom_keys'][0]['stored_xyz'][0]+=0.5
    if defect=='returned_order':basis['returned_coordinates'].reverse()
    if defect=='proxy_index':t['events'][-1]['mapping']['chirality_proxies'][0]['i_seqs'][0]=99
    if defect=='target_sign':t['events'][-1]['mapping']['chirality_proxies'][0]['volume_ideal']=-1.
    if defect=='method_source':basis['restraint_method']['sha256']='CHANGED'
    if defect=='wrong_module':basis['restraint_method']['module']='unselected.module'
    if defect=='duplicate_coordinates':
        basis['native_atom_keys'][0]['stored_xyz']=deepcopy(basis['native_atom_keys'][1]['stored_xyz'])
        ordered=sorted(basis['native_atom_keys'],key=lambda a:a['global_index'])
        basis['returned_coordinates']=[a['stored_xyz'] for a in ordered]
    original=deepcopy(t);q=analyze_index_basis(source,code,t)
    assert t==original and q['checks_pass'] is (defect in {'none','target_sign'})
    if defect=='none':
        row=q['managers'][0]
        assert row['restraint_atom_order']!=row['evaluation_atom_order']
        assert row['restraint_basis_targets'][0]['source_hand_matches_target']
        assert row['evaluation_basis_targets'][0]['valid_proxy_basis'] is False
    assert q['absolute_cip_assignment']==q['scientific_approval']=='NOT_RUN' and not q['automatic_adoption']


@pytest.mark.parametrize('mode',['correct','reversed_return','non_dict','native_exception','integer_keys','unique_index_keys'])
def test_owned_index_worker_captures_native_dictionary_keys_without_reordering_calls(tmp_path,mode):
    from hashlib import sha256
    import os
    from tests.test_cif_constructor_trace import fake_trace_installation
    from nasolve.cif_source_constructor import audit_source_constructor
    root,python,site,proof,api,trace=fake_trace_installation(tmp_path,'correct')
    reader=site/'elbow/chemistry/any_chemical_format_reader.py';reader.write_text(reader.read_text().replace('from types import SimpleNamespace as NS', 'from types import SimpleNamespace\nclass NS(SimpleNamespace):\n __hash__=object.__hash__\n __eq__=object.__eq__'))
    p=site/'elbow/cctbx_api/RestraintClass.py';p.write_text('''class RestraintClass(dict):
 def GetRestraints(self):
  rows=sorted(self,key=lambda a:a.index)
  coordinates=[self[a] for a in rows]
  CHANGE
  return coordinates,[],[],[],[],[[[0,1,2,3],1.,False,1.]]
'''.replace('CHANGE','coordinates.reverse()' if mode=='reversed_return' else 'pass'))
    (site/'elbow/cctbx_api/geometry_manager.py').write_text('def run(coordinates,*args,**kwargs):return None\n')
    integer = mode in {'integer_keys', 'unique_index_keys'}
    if integer:
        p.write_text('''class RestraintClass(dict):
 def get_key(self,atom):return getattr(atom,'unique_index',atom.index)
 def __setitem__(self,atom,xyz):dict.__setitem__(self,self.get_key(atom),xyz)
 def GetCoordinates(self):
  keys=sorted(k for k in self if type(k) is int)
  self.link={k:i for i,k in enumerate(keys)}
  return [self[k] for k in keys]
 def GetRestraints(self):
  return self.GetCoordinates(),[],[],[],[],[[[0,1,2,3],1.,1.]]
''')
    p=site/'elbow/cctbx_api/CCTBXMixins.py';s=p.read_text();s=s[:s.index(' def OptimiseCCTBX')]+''' def GetCoordinates(self,cctbx_format=True,proper_atoms_only=False):
  return [(a.xyz.x,a.xyz.y,a.xyz.z) for a in self]
 def SetCoordinates(self,coordinates,cctbx_format=True):
  for a,xyz in zip(self,coordinates):a.xyz.x,a.xyz.y,a.xyz.z=xyz
 def GetNewManager(self):
  from types import SimpleNamespace
  self.GetRestrainedParameters();self.GetCoordinates()
  return SimpleNamespace(chirality_proxies=[SimpleNamespace(i_seqs=(0,1,2,3),volume_ideal=1.,weight=1.,both_signs=False)])
 def OptimiseCCTBX(self,enforce_chiral=True,return_lbfgs_object=False):
  self.GetNewManager();xyz=self.GetCoordinates();self.SetCoordinates(xyz)
  CHANGE
  return xyz,None
'''.replace('CHANGE',"raise RuntimeError('EXPLICIT_FAKE_NATIVE_EXCEPTION')" if mode=='native_exception' else 'pass');p.write_text(s)
    p=site/'elbow/chemistry/ChiralClass.py';s=p.read_text();a=s.index(' def GetRestrainedParameters');b=s.index(' def Optimise',a)
    s=s[:a]+''' def GetRestrainedParameters(self,additional_restraints=None):
  from ..cctbx_api.RestraintClass import RestraintClass
  self.restraint_class=RestraintClass()
  for atom in self:self.restraint_class[atom]=(atom.xyz.x,atom.xyz.y,atom.xyz.z)
  values=self.restraint_class.GetRestraints()
  CHANGE
  return values
'''.replace('CHANGE','self.restraint_class=object()' if mode=='non_dict' else 'pass')+s[b:];p.write_text(s)
    if mode=='unique_index_keys':
        p.write_text(p.read_text().replace('for atom in self:self.restraint_class[atom]',
            'for atom in self:atom.unique_index=atom.index+100\n  for atom in self:self.restraint_class[atom]'))
    for rows in [proof,trace]:
        for row in rows:
            data=(root/row['path']).read_bytes();row.update(size=len(data),sha256=sha256(data).hexdigest())
    v,_=tetrahedron();source=write(tmp_path/'inputs/source.cif',v);out=tmp_path/'native'
    n=audit_source_constructor(root,python,api,source,'Q17',out,environment={**os.environ,'PYTHONPATH':str(site)},expected_dialect='CHEMICAL_COMPONENTS_CIF',
        prior_sources=proof,trace_sources=trace,native_cctbx=True,trace_chirality=True,coordinate_mapping=True,index_basis=True,integer_keys=integer,timeout_seconds=10)
    assert n['execution']['status']=='COMPLETED' and n['source_preserved']
    assert len(n['index_sources'])==2 and all((out/r['snapshot']['path']).is_file() for r in n['index_sources'])
    assert n['index_analysis']['checks_pass'] is (mode in {'correct','native_exception','integer_keys','unique_index_keys'})
    if integer:
        assert n['index_analysis']['policy_id']=='cif-native-integer-restraint-keys-v2'
        assert n['index_analysis']['managers'][0]['integer_key_binding']['checks_pass']
    assert n['result']['constructor_trace']['methods_restored'] and n['result']['constructor_trace']['source_hashes_preserved']
    assert n['result']['constructor']['status']==('EXCEPTION' if mode=='native_exception' else 'COMPLETED')
    assert n['index_analysis']['scientific_approval']=='NOT_RUN' and not n['automatic_adoption']


@pytest.mark.parametrize('defect',['none','key','link','duplicate','unique_override','identity','method','coordinate','bool_key','extra_entry','missing_method'])
def test_integer_key_proof_requires_complete_native_links_and_unique_index_precedence(tmp_path,defect):
    from nasolve.cif_constructor_index_basis import analyze_index_basis,INTEGER_KEYS_POLICY_ID
    v,_=tetrahedron();source=write(tmp_path/'source.cif',v);t=index_trace(v);t['index_policy_id']=INTEGER_KEYS_POLICY_ID
    basis=t['events'][5]['mapping']['index_basis'];old=basis.pop('native_atom_keys')
    basis['integer_coordinate_entries']=[{'native_key':a['global_index']+100,'stored_xyz':a['stored_xyz']} for a in old]
    basis['local_atom_keys']=[{'atom':a['atom'],'global_index':a['global_index'],'unique_index':a['global_index']+100,
        'key_attribute':'unique_index','native_key':a['global_index']+100,'same_parent_object':True} for a in old]
    basis['native_link']=[{'native_key':a['global_index']+100,'index':i} for i,a in enumerate(sorted(old,key=lambda a:a['global_index']))]
    basis['integer_key_methods']=[{**basis['restraint_method'],'method':'RestraintClass.'+name} for name in ['get_key','GetCoordinates']]
    if defect=='key':basis['local_atom_keys'][0]['native_key']+=99
    if defect=='link':basis['native_link'][0]['index']=99
    if defect=='duplicate':basis['integer_coordinate_entries'].append(deepcopy(basis['integer_coordinate_entries'][0]))
    if defect=='unique_override':basis['local_atom_keys'][0]['key_attribute']='index'
    if defect=='identity':basis['local_atom_keys'][0]['same_parent_object']=False
    if defect=='method':basis['integer_key_methods'][0]['sha256']='CHANGED'
    if defect=='coordinate':basis['integer_coordinate_entries'][0]['stored_xyz'][0]+=0.5
    if defect=='bool_key':basis['native_link'][0]['native_key']=True
    if defect=='extra_entry':basis['integer_coordinate_entries'].append({'native_key':999,'stored_xyz':[0.,0.,0.]})
    if defect=='missing_method':basis['integer_key_methods'].pop()
    original=deepcopy(t);q=analyze_index_basis(source,'Q17',t)
    assert t==original and q['checks_pass'] is (defect=='none')
    if defect=='none':assert q['managers'][0]['integer_key_binding']['checks_pass']
