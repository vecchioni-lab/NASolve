"""The temporary constructor must use the backend selected by native readers.

Process tests use explicit fake APIs; they are not native Phenix validation.
"""
from copy import deepcopy
import json,os
import pytest
from tests.test_cif_source_constructor import fake_installation,evidence
from tests.test_cif_stereochemistry_audit import tetrahedron,write


REFERENCE='''def get_elbow_molecule_from_chemical_components(code,chirals=False):
 molecule=object()
 if chirals:
  molecule.SetCCTBX(True)
  molecule.Chiralise()
 return molecule
'''


@pytest.mark.parametrize('defect',['none','false','reversed','different_object','conditional_setter','missing'])
def test_backend_reference_requires_explicit_native_preparation_before_constructor(defect):
    from nasolve.cif_source_constructor import native_cctbx_reference
    text=REFERENCE
    if defect=='false':text=text.replace('SetCCTBX(True)','SetCCTBX(False)')
    if defect=='reversed':text=text.replace('  molecule.SetCCTBX(True)\n  molecule.Chiralise()','  molecule.Chiralise()\n  molecule.SetCCTBX(True)')
    if defect=='different_object':text=text.replace('molecule.SetCCTBX','other.SetCCTBX')
    if defect=='conditional_setter':text=text.replace('  molecule.SetCCTBX(True)','  if code:\n   molecule.SetCCTBX(True)')
    if defect=='missing':text='def unrelated():pass\n'
    if defect=='none':
        proof=native_cctbx_reference(text)
        assert proof['setter_line']<proof['constructor_line'] and proof['value'] is True
    else:
        with pytest.raises(ValueError):native_cctbx_reference(text)


def installation(tmp_path,mode):
    from hashlib import sha256
    root,python,site,proof,api=fake_installation(tmp_path,'correct')
    (site/'elbow/utilities/Utilities.py').write_text(REFERENCE)
    folder=site/'elbow/cctbx_api';folder.mkdir();(folder/'__init__.py').write_text('')
    (folder/'CCTBXMixins.py').write_text('''class CCTBXMixins:
 def SetCCTBX(self,value):
  self.cctbx=value
  MODE
 def GetCCTBX(self):return getattr(self,'cctbx',False)
'''.replace('MODE',{'charge':'self[0].charge=-1','coordinates':'self[0].xyz.z+=1','flag':'self.cctbx=False'}.get(mode,'pass')))
    (site/'elbow/chemistry/MoleculeClass.py').write_text('''from .SimpleMoleculeClass import SimpleMoleculeClass
from .TopologyMixins import TopologyMixins
from ..cctbx_api.CCTBXMixins import CCTBXMixins
class MoleculeClass(SimpleMoleculeClass,TopologyMixins,CCTBXMixins):pass
''')
    (site/'elbow/chemistry/TopologyMixins.py').write_text('''class TopologyMixins:
 def Chiralise(self,chiral_treatment='retain'):
  assert self.GetCCTBX() is True,'BACKEND MUST BE SELECTED BEFORE CONSTRUCTION'
  MODE
'''.replace('MODE',"raise RuntimeError('EXPLICIT_FAKE_CONSTRUCTOR_EXCEPTION')" if mode=='exception' else 'pass'))
    if mode=='reference':(site/'elbow/utilities/Utilities.py').write_text(REFERENCE.replace('SetCCTBX(True)','SetCCTBX(False)'))
    if mode=='missing_api':(folder/'CCTBXMixins.py').write_text('class CCTBXMixins:pass\n')
    if mode=='unsupported_api':(folder/'CCTBXMixins.py').write_text('class CCTBXMixins:\n def SetCCTBX(self):pass\n def GetCCTBX(self):return False\n')
    for row in proof:
        data=(root/row['path']).read_bytes();row.update(size=len(data),sha256=sha256(data).hexdigest())
    return root,python,site,proof,api


@pytest.mark.parametrize('mode',['correct','charge','coordinates','flag','reference','missing_api','unsupported_api','exception'])
def test_backend_control_precedes_constructor_and_preserves_chemistry(tmp_path,mode):
    from nasolve.cif_source_constructor import audit_source_constructor
    root,python,site,proof,api=installation(tmp_path,mode);v,_=tetrahedron();source=write(tmp_path/'inputs/source.cif',v)
    out=tmp_path/'native'
    if mode=='reference':
        with pytest.raises(ValueError,match='native CCTBX preparation'):
            audit_source_constructor(root,python,api,source,'Q17',out,environment=os.environ,
                expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,native_cctbx=True,timeout_seconds=10)
        assert not out.exists();return
    r=audit_source_constructor(root,python,api,source,'Q17',out,environment={**os.environ,'PYTHONPATH':str(site)},
        expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,native_cctbx=True,timeout_seconds=10)
    assert r['source_preserved'] and not r['automatic_adoption'] and r['dictionary_generation']=='NOT_RUN'
    assert r['execution']['status']=='COMPLETED' and r['status']=='REVIEW'
    q=r['qualification'];assert q['checks_pass'] is (mode=='correct')
    assert r['result']['constructor']['status']==('COMPLETED' if mode=='correct' else 'EXCEPTION')
    if mode in {'correct','exception'}:
        b=r['result']['backend_control'];assert b['status']=='NATIVE_CCTBX_PREPARATION_PASS'
        assert b['before']==b['after']==r['result']['constructor']['promoted']
        assert b['selected_value'] is True and b['previous_value'] is False
        assert b['sources'] and all((out/p['snapshot']['path']).is_file() for p in b['sources'])
    if mode=='exception':assert q['checks']['native_reader_route_preserved'] and not q['checks']['constructor_completed']
    assert json.loads((out/'constructor_receipt.json').read_text())==r


def test_legacy_mode_does_not_silently_select_new_backend(tmp_path):
    from nasolve.cif_source_constructor import audit_source_constructor
    root,python,site,proof,api=installation(tmp_path,'correct');v,_=tetrahedron();source=write(tmp_path/'inputs/source.cif',v)
    r=audit_source_constructor(root,python,api,source,'Q17',tmp_path/'native',environment={**os.environ,'PYTHONPATH':str(site)},
        expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,timeout_seconds=10)
    assert not r['qualification']['checks_pass'] and r['result']['constructor']['status']=='EXCEPTION'
    assert 'BACKEND MUST BE SELECTED' in r['result']['constructor']['message']


@pytest.mark.parametrize('defect',['none','missing','false_flag','inventory','route','reference','status','unselected_method'])
def test_backend_qualification_recomputes_state_and_selection_gates(tmp_path,defect):
    from nasolve.cif_source_constructor import qualify_constructor_evidence,BACKEND_POLICY_ID,native_cctbx_reference
    v,_=tetrahedron();source=write(tmp_path/'source.cif',v);r=evidence(v);snapshot=r['constructor']['promoted']
    r['backend_control']={'policy_id':BACKEND_POLICY_ID,'status':'NATIVE_CCTBX_PREPARATION_PASS',
        'reference':native_cctbx_reference(REFERENCE),'previous_value':False,'selected_value':True,
        'before':deepcopy(snapshot),'after':deepcopy(snapshot),'before_format':'CHEMICAL COMPONENTS','after_format':'CHEMICAL COMPONENTS',
        'methods':{'SetCCTBX':{'selected_source':True},'GetCCTBX':{'selected_source':True}}}
    if defect=='missing':r.pop('backend_control')
    if defect=='false_flag':r['backend_control']['selected_value']=False
    if defect=='inventory':r['backend_control']['after']['atoms'][0]['xyz'][0]+=1
    if defect=='route':r['backend_control']['after_format']='SMILES'
    if defect=='reference':r['backend_control']['reference']['value']=False
    if defect=='status':r['backend_control']['status']='STARTED'
    if defect=='unselected_method':r['backend_control']['methods']['SetCCTBX']['selected_source']=False
    q=qualify_constructor_evidence(source,'Q17',r,'CHEMICAL_COMPONENTS_CIF',native_cctbx=True)
    assert q['checks_pass'] is (defect=='none')
