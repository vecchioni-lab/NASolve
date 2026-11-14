"""Usability is verified mechanics, not convergence or student CIF review."""
from copy import deepcopy
from itertools import combinations
from pathlib import Path
import json,math,os
import pytest
from tests.test_cif_stereochemistry_audit import tetrahedron,write


def component(code='Q17'):
    _,g=tetrahedron(code);a='_chem_comp_angle.';pairs=list(combinations(['O','N','C','H'],2))
    g.update({'_chem_comp.group':['ligand'],'_chem_comp_atom.type_energy':['C','O','N','C','H'],
        '_chem_comp_bond.type':['single']*4,
        '_chem_comp_bond.value_dist':['1.5']*4,'_chem_comp_bond.value_dist_esd':['0.02']*4,
        '_chem_comp_plane_atom.comp_id':[code]*3,'_chem_comp_plane_atom.plane_id':['test']*3,
        '_chem_comp_plane_atom.atom_id':['CTR','O','N'],'_chem_comp_plane_atom.dist_esd':['.02']*3,
        a+'comp_id':[code]*6,a+'atom_id_1':[p[0] for p in pairs],a+'atom_id_2':['CTR']*6,
        a+'atom_id_3':[p[1] for p in pairs],a+'value_angle':['109.5']*6,a+'value_angle_esd':['2']*6})
    return g


@pytest.mark.parametrize('mode',['unchanged','omitted_both','omitted_fixed','flipped_fixed','both_with_R_label','changed_charge','missing_angle','inverted','parity_equivalent'])
def test_unoriented_volume_omission_is_a_recorded_mechanical_delta_not_fixed_stereo_loss(tmp_path,mode):
    from nasolve.cif_candidate_usability import reassess_complete_candidate
    v=component();g=deepcopy(v);p='_chem_comp_chir.'
    if mode in {'omitted_both','both_with_R_label'}:
        v[p+'volume_sign']=['both']
        if mode=='omitted_both':v['_chem_comp_atom.pdbx_stereo_config'][0]='N';g['_chem_comp_atom.pdbx_stereo_config'][0]='N'
    if mode in {'omitted_both','omitted_fixed','both_with_R_label'}:g={k:x for k,x in g.items() if not k.startswith(p)}
    if mode=='flipped_fixed':g[p+'volume_sign']=['negative']
    if mode=='changed_charge':g['_chem_comp_atom.charge'][1]='-1'
    if mode=='missing_angle':g={k:x for k,x in g.items() if not k.startswith('_chem_comp_angle.')}
    if mode=='inverted':g['_chem_comp_atom.z']=[str(-float(x)) for x in g['_chem_comp_atom.z']]
    if mode=='parity_equivalent':g[p+'atom_id_1'],g[p+'atom_id_2']=g[p+'atom_id_2'],g[p+'atom_id_1'];g[p+'volume_sign']=['negative']
    source,candidate=write(tmp_path/'s.cif',v),write(tmp_path/'c.cif',g);before=source.read_bytes(),candidate.read_bytes()
    q=reassess_complete_candidate(source,candidate,'Q17')
    assert q['candidate_status']==('CANDIDATE_REVIEW' if mode in {'unchanged','omitted_both','parity_equivalent'} else 'REJECTED')
    if mode=='omitted_both':assert q['unoriented_volume_omissions'] and q['requires_native_tetrahedral_coverage']
    assert not q['requires_cif_review'] and q['native_usability']=='NOT_RUN'
    assert before==(source.read_bytes(),candidate.read_bytes())


def native_case(tmp_path,values=None):
    from nasolve.cif_terminal_qualification import _rows,_CATEGORIES
    from nasolve.cif_triple_bond_audit import write_component_control_model
    v=component() if values is None else values;source=write(tmp_path/'source/s.cif',v);candidate=write(tmp_path/'candidate/c.cif',v)
    model=tmp_path/'models/model.pdb';write_component_control_model(candidate,'Q17',model)
    names=v['_chem_comp_atom.atom_id'];xyz=list(zip(*[[float(x) for x in v['_chem_comp_atom.'+axis]] for axis in 'xyz']))
    atoms=[{'i_seq':i,'atom_id':n,'label':'A:1:Q17:'+n,'element':v['_chem_comp_atom.type_symbol'][i],
        'xyz':list(xyz[i]),'identity':dict(model_id='1',chain_id='A',resseq='1',icode='',altloc='',resname='Q17')} for i,n in enumerate(names)]
    details={k:[] for k in ['bond_simple','bond_asu','angle','dihedral','const_dihedral','chirality','planarity','parallelity']}
    def endpoints(ids):return {'i_seqs':[names.index(n) for n in ids],'atoms':['A:1:Q17:'+n for n in ids],'origin_id':0}
    for row in _rows(v,'_chem_comp_bond'):
        details['bond_simple'].append({**endpoints([row['atom_id_1'],row['atom_id_2']]),'distance_ideal':float(row['value_dist']),'weight':1/float(row['value_dist_esd'])**2,'symmetry_operation':None})
    for row in _rows(v,'_chem_comp_angle'):
        details['angle'].append({**endpoints([row['atom_id_'+str(i)] for i in range(1,4)]),'angle_ideal':float(row['value_angle']),'weight':1/float(row['value_angle_esd'])**2})
    details['chirality']=[{**endpoints([r['atom_id_centre'],*[r['atom_id_'+str(i)] for i in range(1,4)]]),'volume_ideal':1. if r['volume_sign'].startswith('pos') else -1.,'both_signs':r['volume_sign']=='both','weight':1.} for r in _rows(v,'_chem_comp_chir')]
    for row in _rows(v,'_chem_comp_tor'):
        details['dihedral'].append({**endpoints([row['atom_id_'+str(i)] for i in range(1,5)]),'angle_ideal':float(row['value_angle']),
            'weight':1/float(row['value_angle_esd'])**2,'periodicity':int(row['period']),'alt_angle_ideals':[float(x) for x in row.get('alt_value_angle','').split(',') if x]})
    planes={}
    for row in _rows(v,'_chem_comp_plane_atom'):planes.setdefault(row['plane_id'],[]).append(row)
    for rows in planes.values():details['planarity'].append({**endpoints([r['atom_id'] for r in rows]),'weights':[1/float(r['dist_esd'])**2 for r in rows]})
    definition={name:[{field:(float(r[field]) if field in {'value_dist','value_dist_esd','value_angle','value_angle_esd'} else r.get(field)) for field in fields} for r in _rows(v,cat)] for name,(cat,fields) in _CATEGORIES.items()}
    e={'target':5.,'gradient':[1.]*(3*len(names)),'gradient_norm':math.sqrt(3*len(names)),'terms':{},'proxy_counts':{}}
    native={'schema_version':1,'policy_id':'cif-native-bundle-inventory-v1','status':'REVIEW','inventory_detail':'linked','atom_count':len(names),'atoms':atoms,
        'fatal_problems':None,'unused_definitions':[],'unsupported_fields':[],
        'restraint_policy':{'secondary_structure_enabled':False,'origin_ids':{'hydrogen bonds':1,'edits':2,'basepair stacking':3,'basepair parallelity':4,'basepair planarity':5}},
        'monomer_mappings':{'rows':[{'site':'A:1','resname':'Q17','metadata':{'group':'ligand','effective_definition':definition},'missing_non_hydrogen_atoms':{'status':'RECORDED','atom_ids':[]},'missing_hydrogen_atoms':{'status':'RECORDED','atom_ids':[]},'unexpected_atoms':{'status':'RECORDED','atom_ids':[]}}]},
        'geometry':{'status':'RECORDED','sites_cart_exact':[a['xyz'] for a in atoms],'proxy_details':details,'proxy_counts':{k:len(x) for k,x in details.items()}},
        'energy_inventory':{'policy_id':'cif-fixed-native-usability-energy-v1','status':'RECORDED','normalization':False,'evaluation_calls':2,'snapshots':[e,deepcopy(e)]}}
    return source,candidate,model,native


@pytest.mark.parametrize('defect',['none','target','period','alternative'])
def test_declared_torsion_targets_periods_and_alternatives_survive_native_readback(tmp_path,defect):
    from tests.test_cif_generation import component as linear_component
    from nasolve.cif_candidate_usability import qualify_candidate_native
    v=linear_component('Q17',numerical=True);v['_chem_comp_bond.type']=['single']*3
    for axis in 'xyz':v['_chem_comp_atom.'+axis]=v['_chem_comp_atom.pdbx_model_Cartn_'+axis+'_ideal']
    t='_chem_comp_tor.';v.update({t+'comp_id':['Q17'],t+'id':['test'],t+'atom_id_1':['C5'],t+'atom_id_2':["C5'"],t+'atom_id_3':["O4'"],t+'atom_id_4':["C1'"],t+'value_angle':['-180'],t+'value_angle_esd':['10'],t+'period':['3'],t+'alt_value_angle':['-60,60']})
    s,c,m,n=native_case(tmp_path,v);tor=n['geometry']['proxy_details']['dihedral'][0]
    if defect=='target':tor['angle_ideal']+=1
    if defect=='period':tor['periodicity']=1
    if defect=='alternative':tor['alt_angle_ideals'][0]+=1
    q=qualify_candidate_native(s,c,m,'Q17',n)
    assert q['native_usable'] is (defect=='none')


@pytest.mark.parametrize('missing_angle',[False,True])
def test_omitted_both_volume_requires_all_six_native_angles_even_if_dictionary_loses_one_too(tmp_path,missing_angle):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    from nasolve.cif_stereochemistry_audit import _values
    s,c,m,n=native_case(tmp_path);v=_values(s,'Q17');g=_values(c,'Q17');v['_chem_comp_chir.volume_sign']=['both']
    v['_chem_comp_atom.pdbx_stereo_config'][0]=g['_chem_comp_atom.pdbx_stereo_config'][0]='N'
    g={k:x for k,x in g.items() if not k.startswith('_chem_comp_chir.')}
    n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['chirality']=[]
    n['geometry']['proxy_details']['chirality']=[];n['geometry']['proxy_counts']['chirality']=0
    if missing_angle:
        for k in [k for k in g if k.startswith('_chem_comp_angle.')]:g[k].pop()
        n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['angles'].pop()
        n['geometry']['proxy_details']['angle'].pop();n['geometry']['proxy_counts']['angle']-=1
    write(s,v);write(c,g);q=qualify_candidate_native(s,c,m,'Q17',n)
    assert q['checks']['omitted_unoriented_volume_coverage'] is not missing_angle
    assert q['native_usable'] is not missing_angle


@pytest.mark.parametrize('mode',['unchanged','reordered','changed_weight'])
def test_fixed_covalent_comparison_is_named_and_independent_of_native_atom_array_order(tmp_path,mode):
    from nasolve.cif_candidate_usability import covalent_proxy_signature
    _,_,_,a=native_case(tmp_path);b=deepcopy(a)
    if mode=='reordered':
        b['atoms'].reverse();new={r['i_seq']:i for i,r in enumerate(b['atoms'])}
        for i,r in enumerate(b['atoms']):r['i_seq']=i
        for rows in b['geometry']['proxy_details'].values():
            for r in rows:r['i_seqs']=[new[i] for i in r['i_seqs']]
    if mode=='changed_weight':b['geometry']['proxy_details']['bond_simple'][0]['weight']+=1
    assert (covalent_proxy_signature(a)==covalent_proxy_signature(b)) is (mode!='changed_weight')


@pytest.mark.parametrize('mode',['not_converged','unknown_stopping','unusable'])
def test_verified_native_adapter_feeds_automatic_policy_without_student_approval(tmp_path,mode):
    from nasolve.cif_candidate_usability import qualify_candidate_native,isolated_candidate_decision
    s,c,m,n=native_case(tmp_path);q=qualify_candidate_native(s,c,m,'Q17',n)
    if mode=='unusable':q['native_usable']=False
    decision=isolated_candidate_decision(s,c,'Q17',q,'NOT_CONVERGED_REPORTED' if mode=='not_converged' else 'NOT_REPORTED')
    assert not decision['requires_cif_review'] and not decision['automatic_adoption'] and decision['linked_adoption']=='NOT_RUN'
    assert decision['continue_solving'] is (mode!='unusable')
    if mode=='not_converged':assert decision['converged'] is False and decision['status']=='CONTINUE_WITH_NOTES'


@pytest.mark.parametrize('defect',['none','missing_atom','moved_coordinate','energy_type','native_formal_contradiction','definition_target','bond_target','bond_weight','missing_angle','missing_plane','plane_weight','extra_torsion','chirality_sign','zero_weight','zero_volume','nonfinite_energy','nonrepeat_gradient','missing_energy','ss_enabled','competing_ss','extra_proxy'])
def test_native_usability_requires_exact_definitions_membership_and_finite_repeatable_energy(tmp_path,defect):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    s,c,m,n=native_case(tmp_path);d=n['geometry']['proxy_details']
    if defect=='missing_atom':n['atoms'].pop();n['atom_count']-=1
    if defect=='moved_coordinate':n['atoms'][0]['xyz'][0]+=1
    if defect=='energy_type':n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['atoms'][0]['type_energy']='BAD'
    if defect=='native_formal_contradiction':n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['atoms'][0]['charge']=-1
    if defect=='definition_target':n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['value_dist']+=.1
    if defect=='bond_target':d['bond_simple'][0]['distance_ideal']+=.1
    if defect=='bond_weight':d['bond_simple'][0]['weight']*=.5
    if defect=='missing_angle':d['angle'].pop();n['geometry']['proxy_counts']['angle']-=1
    if defect=='missing_plane':d['planarity'].clear();n['geometry']['proxy_counts']['planarity']=0
    if defect=='plane_weight':d['planarity'][0]['weights'][0]*=.5
    if defect=='extra_torsion':
        d['dihedral'].append({**deepcopy(d['chirality'][0]),'angle_ideal':180.,'periodicity':3,'alt_angle_ideals':None});n['geometry']['proxy_counts']['dihedral']=1
    if defect=='chirality_sign':d['chirality'][0]['volume_ideal']=-1.
    if defect=='zero_weight':d['chirality'][0]['weight']=0.
    if defect=='zero_volume':d['chirality'][0]['volume_ideal']=0.
    if defect=='nonfinite_energy':n['energy_inventory']['snapshots'][0]['target']=float('nan')
    if defect=='nonrepeat_gradient':n['energy_inventory']['snapshots'][1]['gradient'][0]+=.1
    if defect=='missing_energy':n.pop('energy_inventory')
    if defect=='ss_enabled':n['restraint_policy']['secondary_structure_enabled']=True
    if defect=='competing_ss':d['bond_simple'][0]['origin_id']=1
    if defect=='extra_proxy':d['bond_simple'].append(deepcopy(d['bond_simple'][0]));n['geometry']['proxy_counts']['bond_simple']+=1
    q=qualify_candidate_native(s,c,m,'Q17',n)
    assert q['native_usable'] is (defect=='none') and not q['automatic_adoption'] and not q['requires_cif_review']
    assert q['scope']=='ISOLATED_COMPONENT_ONLY' and q['linked_context']=='NOT_RUN'


@pytest.mark.parametrize('mode',['correct','nonfinite','missing_api','disabled'])
def test_owned_energy_inventory_is_opt_in_and_does_not_change_legacy_worker(tmp_path,mode):
    from tests.test_cif_native_validation import native_runtime,files
    from nasolve.cif_native_validation import inspect_native_bundle,_NATIVE_WORKER
    executable,env=native_runtime(tmp_path);root=Path(env['PYTHONPATH']);f=root/'fake_native.py'
    f.write_text(f.read_text()+'''
class Gradients(list):
 def as_double(self):return [v for row in self for v in row]
def energy(self,sites_cart,flags,compute_gradients,normalization):
 assert compute_gradients and normalization is False
 return NS(target=5.,gradients=Gradients([[1.,2.,3.]]*len(sites_cart)))
Geometry.energies_sites=energy
''')
    pkg=root/'cctbx/geometry_restraints';pkg.mkdir(parents=True)
    for p in [root/'cctbx/__init__.py',pkg/'__init__.py',pkg/'energies.py']:p.write_text('')
    (pkg/'flags.py').write_text('class flags:\n def __init__(self,default=True):pass\n')
    if mode=='nonfinite':f.write_text(f.read_text().replace('target=5.','target=float("nan")'))
    if mode=='missing_api':f.write_text(f.read_text().replace('Geometry.energies_sites=energy','pass'))
    model,dicts=files(tmp_path);r=inspect_native_bundle(model,dicts,tmp_path/'native',executable,environment=env,phenix_version='2.2.1-FAKE',energy_inventory=mode!='disabled')
    worker=Path(r['native_directory'])/'native_worker.py'
    if mode=='disabled':assert worker.read_text()==_NATIVE_WORKER and 'energy_inventory' not in r['native_validation']
    elif mode=='correct':assert r['native_validation']['energy_inventory']['evaluation_calls']==2 and r['native_validation']['energy_inventory']['status']=='RECORDED'
    else:assert r['status'] in {'FAILED','UNSUPPORTED'}
