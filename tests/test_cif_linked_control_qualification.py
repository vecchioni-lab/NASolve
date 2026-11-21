"""Full synthetic receipt: preserved counts alone cannot pass linked mechanics."""
from copy import deepcopy
from itertools import combinations
import math
import pytest


def case(tmp_path):
    from nasolve.cif_linked_preparation import _render
    from nasolve.cif_terminal_qualification import _rows,_CATEGORIES,projection_site_plan
    names=['P','OP1','OP2',"O5'","C3'","O3'"];els=['P','O','O','O','C','O']
    bonds=[('P','OP1'),('P','OP2'),('P',"O5'"),("C3'","O3'")];angles=[(a,'P',b) for a,b in combinations(['OP1','OP2',"O5'"],2)]
    v={'_chem_comp.id':['ZZZ'],'_chem_comp.group':['DNA'],'_chem_comp_atom.comp_id':['ZZZ']*6,
       '_chem_comp_atom.atom_id':names,'_chem_comp_atom.type_symbol':els,'_chem_comp_atom.type_energy':['P','OP','OP','O2','C','OC2'],
       '_chem_comp_atom.charge':['0']*6,'_chem_comp_atom.partial_charge':['0']*6}
    for cat,rows,fields in [('_chem_comp_bond',bonds,['atom_id_1','atom_id_2']),('_chem_comp_angle',angles,['atom_id_1','atom_id_2','atom_id_3'])]:
        v[cat+'.comp_id']=['ZZZ']*len(rows)
        for i,f in enumerate(fields):v[cat+'.'+f]=[r[i] for r in rows]
    v.update({'_chem_comp_bond.type':['single']*4,'_chem_comp_bond.value_dist':['1.5']*4,'_chem_comp_bond.value_dist_esd':['.02']*4,
        '_chem_comp_angle.value_angle':['109.5']*3,'_chem_comp_angle.value_angle_esd':['2']*3})
    projected=tmp_path/'projected.cif';projected.write_text(_render(v,'ZZZ'))
    points=[[-1.5,0,0],[0,0,0],[1,1,1],[1,-1,-1],[0,0,1.5],[3,0,0],[4.5,0,0],[6,0,0]]
    model=tmp_path/'model.pdb';atoms=[];lines=[]
    for i,(site,code,name,element) in enumerate([(1,'DG',"O3'",'O'),*[(2,'ZZZ',n,e) for n,e in zip(names,els)],(3,'DG','P','P')]):
        x,y,z=points[i];label=f'A:{site}:{code}:{name}';atoms.append({'i_seq':i,'atom_id':name,'element':element,'xyz':points[i],
            'label':label,'identity':dict(model_id='',chain_id='A',resseq=str(site),icode='',altloc='',resname=code)})
        lines.append(f'HETATM{i+1:5d} {name:>4} {code:>3} A{site:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {element:>2}')
    model.write_text('\n'.join(lines)+'\nEND\n');index={n:i+1 for i,n in enumerate(names)}
    details={k:[] for k in ['bond_simple','bond_asu','angle','dihedral','const_dihedral','chirality','planarity','parallelity']}
    def endpoints(ids):return {'i_seqs':ids,'atoms':[atoms[i]['label'] for i in ids],'origin_id':0}
    for a,b in bonds:details['bond_simple'].append({**endpoints([index[a],index[b]]),'distance_ideal':1.5,'weight':2500.})
    for a,b,c in angles:details['angle'].append({**endpoints([index[a],index[b],index[c]]),'angle_ideal':109.5,'weight':.25})
    for ids in [[0,1],[6,7]]:details['bond_simple'].append({**endpoints(ids),'distance_ideal':1.6,'weight':10000.})
    for neighbor in [2,3,4]:details['angle'].append({**endpoints([0,1,neighbor]),'angle_ideal':109.5,'weight':.25})
    definition={name:[{f:r.get(f) for f in fields} for r in _rows(v,cat)] for name,(cat,fields) in _CATEGORIES.items()}
    mappings=[]
    for site in ['A:1','A:2','A:3']:
        mappings.append({'site':site,'resname':'ZZZ' if site=='A:2' else 'DG','metadata':{'group':'DNA',
            'classification':{'status':'RECORDED','value':'DNA'},'effective_definition':definition if site=='A:2' else {},
            'atom_ids':names if site=='A:2' else ["O3'" if site=='A:1' else 'P']},
            'chem_mod_ids':{'status':'RECORDED','ids':['EXPLICIT_TEST_MOD']} if site=='A:2' else {'status':'RECORDED','ids':[]},
            'missing_non_hydrogen_atoms':{'status':'RECORDED','atom_ids':[]},'unexpected_atoms':{'status':'RECORDED','atom_ids':[]}})
    e={'target':7.,'gradient':[1.]*(3*len(atoms)),'gradient_norm':math.sqrt(3*len(atoms))}
    n={'status':'REVIEW','inventory_detail':'linked','fatal_problems':None,'unused_definitions':[],'unsupported_fields':[],'atom_count':len(atoms),
       'atoms':atoms,'monomer_mappings':{'rows':mappings},'geometry':{'sites_cart_exact':deepcopy(points),'simple_bonds':details['bond_simple'],
       'asu_bonds':[],'proxy_details':details,'proxy_counts':{k:len(v) for k,v in details.items()}},
       'restraint_policy':{'secondary_structure_enabled':False,'origin_ids':{'hydrogen bonds':1,'edits':2,'basepair stacking':3,'basepair parallelity':4,'basepair planarity':5}},
       'energy_inventory':{'policy_id':'cif-fixed-native-usability-energy-v1','status':'RECORDED','normalization':False,'evaluation_calls':2,'snapshots':[e,deepcopy(e)]}}
    prep={'sites':[{**projection_site_plan(projected,'ZZZ','A:2'),'modification_id':'EXPLICIT_TEST_MOD','deleted_atoms':['OP3','oddH']}]}
    return deepcopy(n),n,model,prep,projected


@pytest.mark.parametrize('defect',['none','lost_link','link_target','link_weight','extra_link','proxy_weight','proxy_target','extra_proxy','coordinate','roundtrip',
    'wrong_type','charge','modifier','missing_site','missing_heavy','extra_h','ss','missing_p_angle','nonfinite_cross_angle','energy','constant_zero','unsupported_charge'])
def test_linked_controls_require_projected_chemistry_links_and_usable_mechanics(tmp_path,defect):
    from nasolve.cif_linked_control import qualify_linked_control
    a,b,m,p,c=case(tmp_path);g=b['geometry'];details=g['proxy_details'];site=b['monomer_mappings']['rows'][1]
    if defect=='lost_link':details['bond_simple'].pop()
    if defect=='link_target':details['bond_simple'][-1]['distance_ideal']=1.9
    if defect=='link_weight':details['bond_simple'][-1]['weight']=20.
    if defect=='extra_link':details['bond_simple'].append(deepcopy(details['bond_simple'][-1]))
    if defect=='proxy_weight':details['bond_simple'][0]['weight']*=2
    if defect=='proxy_target':details['angle'][0]['angle_ideal']+=1
    if defect=='extra_proxy':details['angle'].append(deepcopy(details['angle'][0]))
    if defect=='coordinate':b['atoms'][0]['xyz'][0]+=.1
    if defect=='roundtrip':g['sites_cart_exact'][0][0]+=.1
    if defect=='wrong_type':site['metadata']['effective_definition']['atoms'][-1]['type_energy']='OH1'
    if defect=='charge':site['metadata']['effective_definition']['atoms'][0]['charge']='-1'
    if defect=='modifier':site['chem_mod_ids']['ids']=[]
    if defect=='missing_site':b['monomer_mappings']['rows'].pop()
    if defect=='missing_heavy':site['missing_non_hydrogen_atoms']['atom_ids']=['OP1']
    if defect=='extra_h':p['sites'][0]['deleted_atoms'].append('OP1')
    if defect=='ss':b['restraint_policy']['secondary_structure_enabled']=True
    if defect=='missing_p_angle':details['angle'].pop()
    if defect=='nonfinite_cross_angle':details['angle'][-1]['angle_ideal']=float('nan')
    if defect=='energy':b['energy_inventory']['snapshots'][1]['target']+=1
    if defect=='constant_zero':details['bond_simple'][0]['weight']=0.
    if defect=='unsupported_charge':
        for row in site['metadata']['effective_definition']['atoms']:row['charge']=None
    # Preserve aggregate counts for most mutations: values and exact identities
    # must still be checked, independently of reported totals.
    g['proxy_counts']={k:len(v) for k,v in details.items()}
    r=qualify_linked_control(a,b,m,p,c,'ZZZ')
    assert r['status']==('LINKED_CONTROL_MECHANICS_PASS' if defect in {'none','unsupported_charge'} else 'REVIEW'),r['checks']
    assert not r['automatic_adoption'] and not r['requires_cif_review']
