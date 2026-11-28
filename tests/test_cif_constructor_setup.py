"""Retain the input coordinate cache used by the native chiral constructor."""
from hashlib import sha256
import os
import pytest
from tests.test_cif_constructor_backend import installation
from tests.test_cif_stereochemistry_audit import tetrahedron,write

REFERENCE='''def builder(molecule,options):
 molecule.SetCCTBX(options.cctbx)
 molecule.Setup()
 molecule.Chiralise(chiral_treatment=options.chiral)
'''


@pytest.mark.parametrize('defect',['none','missing','after','other_object','arguments','conditional','duplicate','rebound'])
def test_native_setup_reference_requires_same_object_preparation_before_constructor(defect):
    from nasolve.cif_constructor_setup import native_setup_reference
    text=REFERENCE
    if defect=='missing':text=text.replace(' molecule.Setup()\n','')
    if defect=='after':text=text.replace(' molecule.Setup()\n','')+' molecule.Setup()\n'
    if defect=='other_object':text=text.replace('molecule.Setup','other.Setup')
    if defect=='arguments':text=text.replace('Setup()','Setup(True)')
    if defect=='conditional':text=text.replace(' molecule.Setup()',' if options:\n  molecule.Setup()')
    if defect=='duplicate':text=text.replace(' molecule.Setup()',' molecule.Setup()\n molecule.Setup()')
    if defect=='rebound':text=text.replace(' molecule.Chiralise',' molecule=other\n molecule.Chiralise')
    if defect=='none':assert native_setup_reference(text)['setup_line']<native_setup_reference(text)['constructor_line']
    else:
        with pytest.raises(ValueError):native_setup_reference(text)


@pytest.mark.parametrize('mode',['correct','missing_cache','wrong_cache','coordinate_change','exception','reference_hash','missing_method','bad_reference','cache_mutated_after'])
def test_owned_setup_worker_uses_original_native_method_and_keeps_state_evidence(tmp_path,mode):
    from nasolve.cif_source_constructor import audit_source_constructor
    root,python,site,proof,api=installation(tmp_path,'correct')
    folder=site/'elbow/command_line';folder.mkdir();(folder/'__init__.py').write_text('')
    reference=folder/'builder.py';reference.write_text(REFERENCE if mode!='bad_reference' else REFERENCE.replace('Setup()','Setup(True)'))
    native=site/'elbow/chemistry/SimpleMoleculeClass.py'
    native.write_text(native.read_text()+''' def Setup(self):
  self.setup_calls=getattr(self,'setup_calls',0)+1
  for i,a in enumerate(self):
   a.input_xyz=a.xyz
   a.input_index=i
   a.serial=str(i+1)
   a.original_serial=a.serial
  CHANGE
'''.replace('CHANGE',{'missing_cache':'del self[0].input_xyz','wrong_cache':'self[0].input_xyz=type(self[0].xyz)(x=99.,y=0.,z=0.)','coordinate_change':'self[0].xyz.x+=1'}.get(mode,'pass')))
    if mode=='missing_method':native.write_text(native.read_text().replace('def Setup','def Other'))
    p=site/'elbow/chemistry/TopologyMixins.py';p.write_text('''class TopologyMixins:
 def Chiralise(self,chiral_treatment='retain'):
  assert self.GetCCTBX() is True
  assert all(hasattr(a,'input_xyz') for a in self),'INPUT CACHE MUST PRECEDE CONSTRUCTION'
  assert self.setup_calls==1,'ORIGINAL SETUP CALLED ONCE'
  CHANGE
'''.replace('CHANGE',"raise RuntimeError('EXPLICIT_FAKE_NATIVE_EXCEPTION')" if mode=='exception' else 'self[0].input_xyz.x+=1' if mode=='cache_mutated_after' else 'pass'))
    for row in proof:
        data=(root/row['path']).read_bytes();row.update(sha256=sha256(data).hexdigest(),size=len(data))
    v,_=tetrahedron();source=write(tmp_path/'inputs/source.cif',v);out=tmp_path/'native'
    expected='a'*64 if mode=='reference_hash' else sha256(reference.read_bytes()).hexdigest()
    kwargs=dict(environment={**os.environ,'PYTHONPATH':str(site)},expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,
                native_cctbx=True,source_setup=True,setup_reference_sha256=expected,timeout_seconds=10)
    if mode in {'reference_hash','bad_reference'}:
        with pytest.raises(ValueError):audit_source_constructor(root,python,api,source,'Q17',out,**kwargs)
        assert not out.exists();return
    n=audit_source_constructor(root,python,api,source,'Q17',out,**kwargs)
    assert n['execution']['status']=='COMPLETED' and n['source_preserved']
    assert n['setup_analysis']['checks_pass'] is (mode in {'correct','exception','cache_mutated_after'})
    assert n['result']['constructor']['status']==('COMPLETED' if mode in {'correct','cache_mutated_after'} else 'EXCEPTION')
    assert n['setup_sources'] and n['installed_phenix_edits']=='NOT_RUN'
    assert not n['automatic_adoption'] and n['whole_builder_replay']=='NOT_RUN'
    if mode=='correct':
        assert n['setup_analysis']['cached_input_coordinates_preserved_after_constructor']
        assert n['setup_analysis']['absolute_cip_assignment']=='NOT_RUN'
    if mode=='cache_mutated_after':assert not n['setup_analysis']['cached_input_coordinates_preserved_after_constructor']


def test_legacy_worker_does_not_gain_implicit_setup():
    from nasolve.cif_source_constructor import WORKER
    assert 'prepare_native_setup' not in WORKER
