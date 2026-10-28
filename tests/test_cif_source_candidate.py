"""Complete candidate handoffs use native APIs; fake programs are not Phenix proof."""
from copy import deepcopy
from hashlib import sha256
import os
import pytest
from tests.test_cif_constructor_backend import installation
from tests.test_cif_stereochemistry_audit import tetrahedron,write
from tests.test_cif_generation import HELP,program


REFERENCE='''def builder(molecule,options):
 molecule.SetCCTBX(True)
 molecule.Setup()
 molecule.Chiralise(chiral_treatment=options.chiral)
 return molecule
def run(**kwds):
 molecule=None
 if "molecule" in kwds:
  molecule=kwds["molecule"]
  del kwds["molecule"]
 if molecule==None:
  parsing_time=0
  molecule=parser()
  parsing_time=1
 from types import SimpleNamespace
 molecule=builder(molecule,SimpleNamespace(chiral='retain'))
 molecule=post_process(molecule,None)
 return molecule
'''


@pytest.mark.parametrize('defect',['none','missing_object','unconditional_parser','other_object','missing_builder','missing_postprocess'])
def test_full_builder_reference_proves_prepared_object_bypasses_file_parser(defect):
    from nasolve.cif_source_candidate import native_object_reference
    text=REFERENCE
    if defect=='missing_object':text=text.replace('molecule=kwds["molecule"]','molecule=other')
    if defect=='unconditional_parser':text=text.replace(' if molecule==None:\n  parsing_time=0\n  molecule=parser()\n  parsing_time=1',' molecule=parser()')
    if defect=='other_object':text=text.replace('builder(molecule,','builder(other,')
    if defect=='missing_builder':text=text.replace(" molecule=builder(molecule,SimpleNamespace(chiral='retain'))\n",'')
    if defect=='missing_postprocess':text=text.replace(' molecule=post_process(molecule,None)\n','')
    if defect=='none':assert native_object_reference(text)['function']=='run'
    else:
        with pytest.raises(ValueError):native_object_reference(text)


@pytest.mark.parametrize('signed_source',[False,True])
@pytest.mark.parametrize('defect',['none','omitted_label','inverted','flat','no_coordinates','central_deformation'])
def test_finished_coordinate_handedness_uses_named_source_centres_and_keeps_unknowns_soft(tmp_path,signed_source,defect):
    from nasolve.cif_source_candidate import complete_candidate_stereo
    v,g=tetrahedron()
    if signed_source:
        v.update({k:deepcopy(x) for k,x in g.items() if k.startswith('_chem_comp_chir.')})
        v.pop('_chem_comp_atom.pdbx_stereo_config')
    if defect=='omitted_label':g.pop('_chem_comp_atom.pdbx_stereo_config')
    if defect=='inverted':g['_chem_comp_atom.z']=[str(-float(x)) for x in g['_chem_comp_atom.z']]
    if defect=='flat':g['_chem_comp_atom.z']=['0']*5
    if defect=='central_deformation':g['_chem_comp_atom.z'][0]='2'
    if defect=='no_coordinates':g={k:x for k,x in g.items() if k not in ['_chem_comp_atom.'+a for a in 'xyz'] and '_Cartn_' not in k}
    s,c=write(tmp_path/'s.cif',v),write(tmp_path/'c.cif',g);before=s.read_bytes(),c.read_bytes()
    q=complete_candidate_stereo(s,c,'Q17')
    assert q['coordinate_stage']=='COMPLETE_DICTIONARY' and q['absolute_cip_assignment']=='NOT_RUN'
    assert q['stereochemistry']==('INVERTED' if defect=='inverted' else 'UNASSESSED' if defect in {'flat','no_coordinates'} else 'PRESERVED')
    assert not q['requires_cif_review'] and (s.read_bytes(),c.read_bytes())==before


@pytest.mark.parametrize('mode',['correct','exception_after_output','exception_before_output','charge_change','missing_charge','bad_pin','bad_reference','timeout'])
def test_owned_complete_builder_keeps_output_even_without_convergence_or_success_exit(tmp_path,mode):
    from nasolve.cif_source_candidate import generate_source_candidate
    root,python,site,proof,api=installation(tmp_path,'correct')
    reader=site/'elbow/chemistry/any_chemical_format_reader.py'
    reader.write_text(reader.read_text().replace("['constructor_worker.py']","['source_candidate_worker.py']").replace(' return [m]',' m[1].charge=-1;m.charge=-1\n return [m]'))
    native=site/'elbow/chemistry/SimpleMoleculeClass.py'
    native.write_text(native.read_text()+''' def Setup(self):
  self.setup_calls=getattr(self,'setup_calls',0)+1
  for a in self:a.input_xyz=a.xyz
''')
    v,g=tetrahedron();v['_chem_comp_atom.charge'][1]='-1';g['_chem_comp_atom.charge'][1]='-1'
    g.update({'_chem_comp_atom.type_energy':['C','O','N','C','H'],
              '_chem_comp_bond.value_dist':['1.5']*4,'_chem_comp_bond.value_dist_esd':['0.02']*4})
    from itertools import combinations
    pairs=list(combinations(['O','N','C','H'],2));a='_chem_comp_angle.'
    g.update({a+'comp_id':['Q17']*6,a+'atom_id_1':[p[0] for p in pairs],a+'atom_id_2':['CTR']*6,
              a+'atom_id_3':[p[1] for p in pairs],a+'value_angle':['109.5']*6,a+'value_angle_esd':['2']*6})
    fixture=write(tmp_path/'fixture.cif',g);source=write(tmp_path/'inputs/source.cif',v)
    folder=site/'elbow/command_line';folder.mkdir();(folder/'__init__.py').write_text('')
    builder=folder/'builder.py'
    builder.write_text(REFERENCE+'''
def parser():raise RuntimeError('PREPARED OBJECT MUST BYPASS FILE PARSER')
def post_process(molecule,options):
 import os,shutil
 assert molecule.setup_calls==1
 assert molecule[1].charge==-1
 CHANGE
 shutil.copyfile(os.environ['CANDIDATE_FIXTURE'],'candidate.cif')
 print('geometry not converged')
 AFTER
 return molecule
'''.replace('CHANGE',"raise RuntimeError('EXPLICIT_FAKE_BEFORE_OUTPUT')" if mode=='exception_before_output' else "import time;time.sleep(4)" if mode=='timeout' else 'pass').replace('AFTER',"raise RuntimeError('EXPLICIT_FAKE_AFTER_OUTPUT')" if mode=='exception_after_output' else 'pass'))
    if mode=='bad_reference':builder.write_text(builder.read_text().replace('molecule=builder(molecule,','molecule=builder(other,'))
    if mode=='charge_change':
        g['_chem_comp_atom.charge'][1]='0';write(fixture,g)
    if mode=='missing_charge':g.pop('_chem_comp_atom.charge');write(fixture,g)
    names=['elbow/chemistry/any_chemical_format_reader.py','elbow/chemistry/MoleculeClass.py','elbow/chemistry/SimpleMoleculeClass.py','elbow/command_line/builder.py']
    pins=[{'anchor':'phenix_installation','path':(p:=site/name).relative_to(root).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for name in names]
    if mode=='bad_pin':pins[0]['sha256']='a'*64
    elbow=program(tmp_path,help_text=HELP+'  --opt_steps=COUNT  Step count\n')
    # The helper dispatcher lives outside this fake installation; copy it into
    # the selected installation so containment is exercised too.
    selected=root/'bin/phenix.elbow';selected.write_bytes(elbow.read_bytes());selected.chmod(0o755)
    out=tmp_path/'generation';kwargs=dict(environment={**os.environ,'PYTHONPATH':str(site),'CANDIDATE_FIXTURE':str(fixture)},
        expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=pins,phenix_version='2.2.1-FAKE',single_block_steps=12,timeout_seconds=0.5 if mode=='timeout' else 10)
    if mode in {'bad_pin','bad_reference'}:
        with pytest.raises(ValueError):generate_source_candidate(root,python,selected,api,source,'Q17',out,**kwargs)
        assert not out.exists();return
    r=generate_source_candidate(root,python,selected,api,source,'Q17',out,**kwargs)
    from nasolve.cif_source_candidate import candidate_generation_diagnostic
    assert r['diagnostic']==candidate_generation_diagnostic(r)
    assert r['source_preserved'] and r['native_proxy_validation']=='NOT_RUN' and not r['automatic_adoption'] and not r['requires_cif_review']
    if mode=='timeout':assert r['execution']['status']=='TIMED_OUT' and r['candidate'] is None
    elif mode=='exception_before_output':assert r['candidate'] is None and r['result']['builder']['status']=='EXCEPTION'
    else:
        assert r['candidate']['sha256']==sha256(fixture.read_bytes()).hexdigest()
        assert r['stopping']['status']=='NOT_CONVERGED_REPORTED'
        assert r['candidate_retained'] and r['status']==('REJECTED' if mode in {'charge_change','missing_charge'} else 'CANDIDATE_REVIEW')
        if mode=='exception_after_output':assert r['result']['builder']['status']=='EXCEPTION'
        assert r['result']['charge_control']['status']=='DECLARED_CHARGE_CONTROL_PASS'
