"""Temporary native construction must keep source chemistry and handedness."""
from copy import deepcopy
import json,os,sys
import pytest
from tests.test_cif_stereochemistry_audit import tetrahedron,write


def evidence(values):
    ids=values['_chem_comp_atom.atom_id'];points=list(zip(*[[float(x) for x in values['_chem_comp_atom.pdbx_model_Cartn_'+a+'_ideal']] for a in 'xyz']))
    snapshot={'atoms':[{'atom':n,'element':e,'native_atom_charge':0,'native_chiral_marker':'R' if n=='CTR' else False,
        'native_volume_sign':None,'xyz':list(xyz)} for n,e,xyz in zip(ids,values['_chem_comp_atom.type_symbol'],points)],
        'bonds':[{'atoms':sorted(['CTR',n]),'native_order':1} for n in ids[1:]],'molecule_charge':0}
    return {'reader':{**deepcopy(snapshot),'execution':'COMPLETED','format':'CHEMICAL COMPONENTS','dispatch_is_chemical_components':True},
        'charge_control':{'status':'DECLARED_CHARGE_CONTROL_PASS','action':'ALREADY_PRESERVED','before':deepcopy(snapshot),'after':deepcopy(snapshot)},
        'constructor':{'status':'COMPLETED','promoted':deepcopy(snapshot),'after':deepcopy(snapshot),
            'promoted_format':'CHEMICAL COMPONENTS','after_format':'CHEMICAL COMPONENTS'}}


@pytest.mark.parametrize('code',['Q17','ZZ9'])
@pytest.mark.parametrize('defect',['none','charge','total_charge','order','element','missing_atom','duplicate','nonfinite','inverted','flat','marker','nonchiral_marker','route','promotion','exception','not_run','proper_rotation'])
def test_constructor_gate_preserves_raw_chemistry_and_source_relative_stereo(tmp_path,code,defect):
    from nasolve.cif_source_constructor import qualify_constructor_evidence
    v,_=tetrahedron(code);source=write(tmp_path/'source.cif',v);r=evidence(v);after=r['constructor']['after']
    if defect=='charge':after['atoms'][0]['native_atom_charge']=-1
    if defect=='total_charge':after['molecule_charge']=-1
    if defect=='order':after['bonds'][0]['native_order']=2
    if defect=='element':after['atoms'][0]['element']='N'
    if defect=='missing_atom':after['atoms'].pop()
    if defect=='duplicate':after['atoms'].append(deepcopy(after['atoms'][0]))
    if defect=='nonfinite':after['atoms'][0]['xyz'][0]=float('nan')
    if defect=='inverted':
        for atom in after['atoms']:atom['xyz'][2]*=-1
    if defect=='flat':
        for atom in after['atoms']:atom['xyz'][2]=0.
    if defect=='marker':after['atoms'][0]['native_chiral_marker']='S'
    if defect=='route':r['constructor']['after_format']='SMILES'
    if defect=='nonchiral_marker':
        for row in [r['reader'],r['charge_control']['before'],r['charge_control']['after'],r['constructor']['promoted'],after]:row['atoms'][1]['native_chiral_marker']=True
    if defect=='promotion':r['constructor']['promoted']['atoms'][1]['xyz'][0]+=1
    if defect=='exception':r['constructor']={'status':'EXCEPTION','message':'retained native error','after':after}
    if defect=='not_run':r['constructor']={'status':'NOT_RUN'}
    if defect=='proper_rotation':
        for atom in after['atoms']:
            x,y,z=atom['xyz'];atom['xyz']=[-y+3,x-2,z+1]
    before=source.read_bytes();q=qualify_constructor_evidence(source,code,r,'CHEMICAL_COMPONENTS_CIF')
    assert source.read_bytes()==before and not q['automatic_adoption'] and q['absolute_cip_assignment']=='NOT_RUN'
    assert q['checks_pass'] is (defect in {'none','proper_rotation'})
    assert q['status']==('SOURCE_CONSTRUCTOR_HANDOFF_PASS' if q['checks_pass'] else 'REVIEW')
    if defect=='proper_rotation':assert q['maximum_coordinate_shift_angstrom']>0
    if defect=='exception':assert q['constructor_status']=='EXCEPTION'


def test_unknown_labels_do_not_become_a_stereo_pass_by_absence(tmp_path):
    from nasolve.cif_source_constructor import qualify_constructor_evidence
    v,_=tetrahedron();v['_chem_comp_atom.pdbx_stereo_config']=['?']*5
    q=qualify_constructor_evidence(write(tmp_path/'source.cif',v),'Q17',evidence(v),'CHEMICAL_COMPONENTS_CIF')
    assert q['checks']['source_handedness_assessed'] is False and not q['checks_pass']


@pytest.mark.parametrize('sign,expected',[('positiv',True),('negativ',False),('both',True),('?',False)])
def test_explicit_both_volume_is_preserved_as_permissive_without_assigning_a_hand(tmp_path,sign,expected):
    from nasolve.cif_source_constructor import qualify_constructor_evidence
    v,g=tetrahedron();p='_chem_comp_chir.'
    # A second, separately translated fixed centre keeps the sugar hand gate
    # meaningful while this first source centre permits both hands explicitly.
    for key in list(v):
        if key.startswith('_chem_comp_atom.'):
            column=v[key]
            if key.endswith('atom_id'):column.extend(['X'+n for n in column[:]])
            elif 'Cartn_' in key:column.extend([str(float(x)+5) for x in column[:]])
            else:column.extend(column[:])
        elif key.startswith('_chem_comp_bond.'):
            column=v[key];column.extend(['X'+n for n in column[:]] if 'atom_id_' in key else column[:])
    for key in [p+'comp_id',p+'id',p+'atom_id_centre',p+'atom_id_1',p+'atom_id_2',p+'atom_id_3',p+'volume_sign']:v[key]=g[key][:]
    v[p+'volume_sign']=[sign];v['_chem_comp_atom.pdbx_stereo_config'][0]='?'
    source=write(tmp_path/'source.cif',v);r=evidence(tetrahedron()[0])
    base=deepcopy(r['constructor']['after'])
    for row in [r['reader'],r['charge_control']['before'],r['charge_control']['after'],r['constructor']['promoted'],r['constructor']['after']]:
        row['atoms'][0]['native_volume_sign']=sign
        row['atoms'][0]['native_chiral_marker']=False
        row['atoms'].extend([{**a,'atom':'X'+a['atom'],'xyz':[x+5 for x in a['xyz']]} for a in base['atoms']])
        row['bonds'].extend([{'atoms':['X'+n for n in b['atoms']],'native_order':b['native_order']} for b in base['bonds']])
    if sign=='both':
        for atom in r['constructor']['after']['atoms'][:5]:atom['xyz'][2]*=-1
    q=qualify_constructor_evidence(source,'Q17',r,'CHEMICAL_COMPONENTS_CIF')
    assert q['checks_pass'] is expected
    if sign=='both':assert q['source_relative_handedness'][0]['requires_fixed_hand'] is False and q['checks']['source_handedness_assessed']


@pytest.mark.parametrize('defect',['none','arithmetic','transition','nonzero_pair','membership','function','kernel_budget','calls','hidden_failure'])
def test_saved_cache_proof_replays_before_it_can_authorize_a_new_action(defect):
    from nasolve.cif_nonbonded_cache_audit import audit_cache_stabilized_impact,replay_cache_impact_evidence
    from tests.test_cif_linear_torsion_impact import fixture
    from tests.test_cif_nonbonded_cache_audit import snapshot
    cases,oracle,refs=fixture();cases={k:[*v,[2.,2.,2.]] for k,v in cases.items()}
    refs={k:{'target':10*sum(x*x for p in v for x in p),'gradient':[20*x for p in v for x in p]} for k,v in cases.items()}
    def evaluate(manager,points,family,*,capture_pairs=False):
        r=oracle(manager,points,family)
        if family in {'all','nonbonded'}:
            s=snapshot(True);r.update(pairs=s['pairs'],nonbonded_target=s['nonbonded_target'],nonbonded_gradient=s['nonbonded_gradient'],
                function_parameters={'class':'fake-oracle'},nonbonded_membership=[{'i_seqs':p['i_seqs'],'vdw_distance':p['vdw_distance']} for p in s['pairs']])
            r['proxy_counts']['n_nonbonded_proxies']=2
        else:r['nonbonded_membership']=None
        return r
    r=audit_cache_stabilized_impact(evaluate,cases,[0,1],refs)
    # Explicit oracle exposes no native kernels; count the recorded proof rows.
    r['pair_kernel_calls']=sum(len(s[m][f]['pairs'])+1 for c in r['cases'].values() for s in c['cache_preflight']['snapshots'] for m in ['original','candidate'] for f in ['all','nonbonded'])
    c=next(iter(r['cases'].values()));pf=c['cache_preflight']
    if defect=='arithmetic':c['candidate_derivatives']['all'][0]['samples'][0]['numerical']+=1
    if defect=='transition':pf['transitions']['original_full_repeat']['after_count']+=1
    if defect=='nonzero_pair':pf['snapshots'][0]['original']['all']['pairs'][0]['residual']+=1
    if defect=='membership':c['baselines']['original']['all']['nonbonded_membership'][0]['vdw_distance']+=1
    if defect=='function':c['repeats']['candidate']['all']['function_parameters']['class']='changed'
    if defect=='kernel_budget':r['pair_kernel_calls']+=1
    if defect=='calls':r['evaluation_calls']+=1
    if defect=='hidden_failure':pf['post_preflight_membership_stable']=False
    if defect=='none':
        q=replay_cache_impact_evidence(r,cases,[0,1],refs);assert q['preflight_transitions_recomputed']==24 and q['captured_code_execution']=='NOT_RUN'
    else:
        with pytest.raises(ValueError):replay_cache_impact_evidence(r,cases,[0,1],refs)


def fake_installation(tmp_path,mode):
    from hashlib import sha256
    from nasolve.cif_source_constructor import SOURCE_PATHS,PRIOR_PATHS
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages'
    for package in ['elbow','elbow/utilities','elbow/chemistry','elbow/formats']:
        p=site/package;p.mkdir(parents=True,exist_ok=True);(p/'__init__.py').write_text('')
    for name in SOURCE_PATHS:(site/name).write_text('# EXPLICIT_FAKE_INSTALLED_API\n')
    (site/'elbow/chemistry/SimpleMoleculeClass.py').write_text('''class SimpleMoleculeClass(list):
 def GetOriginalFormat(self):return 'CHEMICAL COMPONENTS'
''')
    (site/'elbow/chemistry/TopologyMixins.py').write_text('''from pathlib import Path
import time
class TopologyMixins:
 def Chiralise(self,chiral_treatment='retain'):
  mode=MODE
  if mode=='exception':raise RuntimeError('EXPLICIT_FAKE_CONSTRUCTOR_EXCEPTION')
  if mode=='charge':self[0].charge=-1
  if mode=='inverted':
   for a in self:a.xyz.z=-a.xyz.z
  if mode=='changed_input':Path('source.cif').write_text('CHANGED')
  if mode=='changed_source':Path(__file__).write_text('# CHANGED')
  if mode=='changed_snapshot':Path('elbow/chemistry/ChiralClass.py.txt').write_text('# CHANGED')
  if mode=='timeout':time.sleep(60)
'''.replace('MODE',repr(mode)))
    (site/'elbow/chemistry/MoleculeClass.py').write_text('''from .SimpleMoleculeClass import SimpleMoleculeClass
from .TopologyMixins import TopologyMixins
class MoleculeClass(SimpleMoleculeClass,TopologyMixins):pass
''')
    (site/'elbow/chemistry/any_chemical_format_reader.py').write_text('''from types import SimpleNamespace as NS
from .SimpleMoleculeClass import SimpleMoleculeClass
from .MoleculeClass import MoleculeClass
import sys
def is_chemical_components_file(lines):return True
def any_chemical_format_reader(data,simple=True,return_all_restraints=False,do_not_check_for_smiles=False):
 assert sys.argv==['constructor_worker.py']
 m=SimpleMoleculeClass()
 for n,e,xyz in zip(['CTR','O','N','C','H'],['C','O','N','C','H'],[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(-1,-1,-1)]):
  m.append(NS(name=n,symbol=e,charge=0,chiral='R' if n=='CTR' else False,xyz=NS(x=xyz[0],y=xyz[1],z=xyz[2])))
 m.bonds=[(m[0],a) for a in m[1:]]
 class Bond(tuple):order=1
 m.bonds=[Bond(b) for b in m.bonds];m.charge=0
 return [m]
def return_molecule_class(molecule,simple=True):
 m=MoleculeClass(molecule);m.__dict__.update(molecule.__dict__);return m
''')
    python=root/'bin/phenix.python';python.parent.mkdir(parents=True)
    python.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv=[a for a in sys.argv[1:] if a!="-B"]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');python.chmod(0o755)
    prefix='lib/python3.11/site-packages/'
    proof=[{'anchor':'phenix_installation','path':prefix+p,'size':len((site/p).read_bytes()),'sha256':sha256((site/p).read_bytes()).hexdigest()} for p in PRIOR_PATHS]
    api=[{'anchor':'phenix_installation','path':prefix+'iotbx/phil.py'}]
    return root,python,site,proof,api


@pytest.mark.parametrize('mode',['correct','exception','charge','inverted','changed_input','changed_source','changed_snapshot','timeout'])
def test_owned_worker_checks_real_process_boundaries_with_explicit_fake_apis(tmp_path,mode):
    from nasolve.cif_source_constructor import audit_source_constructor,verify_constructor_capture
    root,python,site,proof,api=fake_installation(tmp_path,mode);v,_=tetrahedron();source=write(tmp_path/'inputs/source.cif',v);before=source.read_bytes()
    out=tmp_path/'native';r=audit_source_constructor(root,python,api,source,'Q17',out,environment={**os.environ,'PYTHONPATH':str(site)},
        expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,timeout_seconds=.5 if mode=='timeout' else 10)
    assert source.read_bytes()==before and not r['automatic_adoption'] and r['dictionary_generation']=='NOT_RUN'
    assert r['whole_molecule_optimization']=='NOT_REQUESTED' and r['constructor_local_optimization']=='NATIVE_INTERNALS_NOT_INSTRUMENTED'
    assert json.loads((out/'constructor_receipt.json').read_text())==r
    if mode in {'correct','exception','charge','inverted'}:
        assert r['status']=='REVIEW' and r['execution']['status']=='COMPLETED' and r['source_preserved']
        assert r['qualification']['checks_pass'] is (mode=='correct')
        assert r['result']['process_argv']==['constructor_worker.py'] and verify_constructor_capture(root,r,out)
    else:
        assert r['status']=='FAILED'
        if mode=='timeout':assert r['execution']['status']=='TIMED_OUT'


@pytest.mark.parametrize('defect',['proof','selected_root','source_escape','unsafe_output','timeout'])
def test_constructor_refuses_changed_proofs_and_unsafe_locations_before_execution(tmp_path,defect):
    from nasolve.cif_source_constructor import audit_source_constructor
    root,python,site,proof,api=fake_installation(tmp_path,'correct');v,_=tetrahedron();source=write(tmp_path/'inputs/source.cif',v);out=tmp_path/'out'
    if defect=='proof':proof[0]['sha256']='changed'
    if defect=='selected_root':python=sys.executable
    if defect=='source_escape':
        path=site/'elbow/chemistry/TopologyMixins.py';data=path.read_bytes();path.unlink();outside=tmp_path/'outside.py';outside.write_bytes(data);path.symlink_to(outside)
    if defect=='unsafe_output':out=source.parent/'bad'
    with pytest.raises((ValueError,FileNotFoundError)):
        audit_source_constructor(root,python,api,source,'Q17',out,environment=os.environ,expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=proof,
            timeout_seconds=61 if defect=='timeout' else 10)
    assert not out.exists()
