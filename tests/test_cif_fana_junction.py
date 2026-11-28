"""Synthetic compiler fixtures; native Phenix validation is recorded separately."""
from copy import deepcopy
from itertools import combinations
import json
from unittest.mock import patch

import pytest
from tests.test_cif_fana_placement import setup as placement_setup, run, CONTEXT
from tests.test_cif_catalogue import snapshot
from nasolve.ligand_profiles import _emit


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def template(path):
    v={'data_':'link_rna3p'}
    for cat, rows in [('bond',[{'link_id':'rna2p','atom_1_comp_id':'1','atom_id_1':"O3'",'atom_2_comp_id':'2','atom_id_2':'P','type':'single','value_dist':'1.607','value_dist_esd':'0.012'}]),('angle',[
        {'link_id':'rna2p',**{f'atom_{i}_comp_id':str(s) for i,(s,n) in enumerate(ends,1)},**{f'atom_id_{i}':n for i,(s,n) in enumerate(ends,1)},'value_angle':str(target),'value_angle_esd':str(sigma)}
        for ends,target,sigma in [([(1,"O3'"),(2,'P'),(2,"O5'")],104,1.9),([(1,"O3'"),(2,'P'),(2,'OP1')],108,3),([(1,"O3'"),(2,'P'),(2,'OP2')],108,3),([(1,"C3'"),(1,"O3'"),(2,'P')],119.7,1.2)]])]:
        for key in rows[0]:v['_chem_link_'+cat+'.'+key]=[r[key] for r in rows]
    path.write_text(_emit(v));return path


def fixture(tmp_path, alias=True):
    from nasolve.cif_construction_provenance import _pdb_inventory
    from nasolve.cif_linked_preparation import component_values,_prune
    from nasolve.cif_terminal_qualification import _CATEGORIES,_rows
    from nasolve.dictionary_compatibility import normalize_torsion_block
    paths=placement_setup(tmp_path,phosphate_alias=alias)
    p=run(paths,{**CONTEXT,'leaving_atom':'O3P' if alias else 'OP3'})
    control=paths[-1];model=control/'model.pdb';inventory=_pdb_inventory(model)
    atoms=[];by={}
    for i,(key,row) in enumerate(inventory.items()):
        chain,resid,icode,altloc,name=key
        atoms.append({'i_seq':i,'label':'synthetic_'+str(i),'atom_id':name,'xyz':row['xyz'],'element':row['element'],'identity':{'model_id':'','chain_id':chain,'resseq':resid,'icode':icode,'altloc':altloc,'resname':row['code']}})
        by[resid,name]=i
    details={k:[] for k in ['bond_simple','bond_asu','angle','dihedral','const_dihedral','chirality','planarity','parallelity']}
    def proxy(kind, endpoints, **fields):
        indices=[by[e] for e in endpoints]
        r={'i_seqs':indices,'atoms':[atoms[i]['label'] for i in indices],'origin_id':0,**fields};details[kind].append(r);return r
    o1,o2=('O1P','O2P') if alias else ('OP1','OP2')
    neighbors=[('1',"O3'"),('2',o1),('2',o2),('2',"O5'")]
    for neighbor in neighbors:proxy('bond_simple',[neighbor,('2','P')],distance_ideal=1.607,weight=1/.012**2,symmetry_operation=None)
    for a,b in combinations(neighbors,2):
        if a[0]=='1' and b[1] in {o1,o2}:continue
        proxy('angle',[a,('2','P'),b],angle_ideal=104. if a[0]=='1' else 110.,weight=1/1.9**2 if a[0]=='1' else .1)
    proxy('angle',[('1',"C3'"),('1',"O3'"),('2','P')],angle_ideal=119.7,weight=1/1.2**2)
    values=_prune(component_values(paths[1],'LF1'),set(p['deleted_source_atoms_for_declared_links']),outgoing=True)
    values,_=normalize_torsion_block(values)
    definition={cat:_rows(values,prefix) for cat,(prefix,_) in _CATEGORIES.items()}
    n={'schema_version':1,'policy_id':'cif-native-bundle-inventory-v1','inventory_detail':'linked','status':'REVIEW','fatal_problems':None,'unsupported_fields':[],'unused_definitions':[], 'atoms':atoms,'atom_count':len(atoms),
       'restraint_policy':{'origin_ids':{'edits':4},'secondary_structure_enabled':False},
       'monomer_mappings':{'rows':[{'site':'A:2','resname':'LF1','metadata':{'effective_definition':definition},'unexpected_atoms':{'atom_ids':[]},'missing_non_hydrogen_atoms':{'atom_ids':[]}}]},
       'geometry':{'status':'RECORDED','sites_cart_exact':[a['xyz'] for a in atoms],'proxy_details':details,'proxy_counts':{k:len(v) for k,v in details.items()},'simple_bonds':deepcopy(details['bond_simple']),'asu_bonds':[],'custom_proxy_requests':[]}}
    native=tmp_path/'native.json';save(native,n)
    return (control,model,native,template(tmp_path/'link.cif'),tmp_path/'junction'),n


def prepare(paths):
    from nasolve.cif_fana_junction import prepare_fana_junction_angles
    return prepare_fana_junction_angles(*paths)


def completed(n, report):
    after=deepcopy(n)
    for q in report['requests']:
        row={k:deepcopy(v) for k,v in q.items() if k not in {'kind','action','selections','sigma','template_atoms'}}
        row['origin_id']=4;after['geometry']['proxy_details']['angle'].append(row)
        after['geometry']['custom_proxy_requests'].append({k:deepcopy(v) for k,v in q.items() if k not in {'sigma','template_atoms'}})
    after['geometry']['proxy_counts']['angle']=len(after['geometry']['proxy_details']['angle'])
    return after


@pytest.mark.parametrize('alias',[True,False])
def test_missing_angles_are_source_named_and_template_valued(tmp_path,alias):
    from nasolve.cif_fana_junction import read_fana_junction_angles,qualify_fana_junction_angles
    paths,n=fixture(tmp_path,alias);before=snapshot(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):
        report=prepare(paths);assert read_fana_junction_angles(paths[-1])==report
        assert qualify_fana_junction_angles(paths[-1],completed(n,report))['status']=='JUNCTION_ANGLE_MECHANICS_PASS'
    assert len(report['requests'])==2 and report['phosphate_angles_before']==4
    assert all(q['angle_ideal']==108 and q['sigma']==3 and q['weight']==pytest.approx(1/9) for q in report['requests'])
    assert report['automatic_adoption'] is False and report['chemical_qualification']=='NOT_ESTABLISHED'
    text=(paths[-1]/'angles.phil').read_text();assert 'action = add' in text and "name O3'" in text
    assert ('name O1P' in text)==alias
    assert all(snapshot(tmp_path)[p]==v for p,v in before.items())


@pytest.mark.parametrize('defect',['no_bond','wrong_bond','symmetry','missing_internal','duplicate_angle','conflicting_angle','projection','coordinate','missing_atom','counts','fatal','unsupported'])
def test_unsafe_or_unbound_capture_is_refused_before_writing(tmp_path,defect):
    paths,n=fixture(tmp_path);d=n['geometry']['proxy_details']
    if defect=='no_bond':d['bond_simple'].pop(0)
    if defect=='wrong_bond':d['bond_simple'][0]['weight']*=2
    if defect=='symmetry':d['bond_simple'][0]['symmetry_operation']='-x,y,z'
    if defect=='missing_internal':d['angle'].pop(1)
    if defect=='duplicate_angle':d['angle'].append(deepcopy(d['angle'][0]))
    if defect=='conflicting_angle':
        # Exact endpoints of a missing angle, but conflicting target.
        by={(a['identity']['resseq'],a['atom_id']):a['i_seq'] for a in n['atoms']}
        ids=[by['1',"O3'"],by['2','P'],by['2','O1P']]
        d['angle'].append({'i_seqs':ids,'atoms':[n['atoms'][i]['label'] for i in ids],'origin_id':0,'angle_ideal':109.,'weight':1/9})
    if defect=='projection':n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['atoms'].pop()
    if defect=='coordinate':n['atoms'][0]['xyz']=[1.,2.,3.]
    if defect=='missing_atom':n['atoms'].pop()
    if defect=='fatal':n['fatal_problems']='error'
    if defect=='unsupported':n['unsupported_fields']=['angles']
    n['geometry']['simple_bonds']=deepcopy(d['bond_simple']);n['geometry']['proxy_counts']={k:len(v) for k,v in d.items()}
    if defect=='counts':n['geometry']['proxy_counts']['angle']+=1
    save(paths[2],n)
    with pytest.raises(ValueError):prepare(paths)
    assert not paths[-1].exists()


@pytest.mark.parametrize('defect',['block','extra_block','missing_angle','ambiguous_alias','nan','bond_target','anchor_angle'])
def test_template_or_name_ambiguity_does_not_guess(tmp_path,defect):
    paths,n=fixture(tmp_path);p=paths[3];text=p.read_text()
    if defect=='block':text=text.replace('link_rna3p','link_other')
    if defect=='extra_block':text+='\ndata_other\n_x.y z\n'
    if defect=='missing_angle':text=text.replace('OP2','OX2')
    if defect=='ambiguous_alias':text=text.replace('OP2','OP1')
    if defect=='nan':text=text.replace('108','nan')
    if defect=='bond_target':text=text.replace('1.607','1.9')
    if defect=='anchor_angle':text=text.replace('104','105')
    p.write_text(text)
    with pytest.raises(ValueError):prepare(paths)
    assert not paths[-1].exists()


@pytest.mark.parametrize('defect',['missing','extra','wrong_weight','wrong_origin','old_proxy','coordinate','definition','requests'])
def test_native_delta_requires_only_exact_requested_additions(tmp_path,defect):
    from nasolve.cif_fana_junction import qualify_fana_junction_angles
    paths,n=fixture(tmp_path);report=prepare(paths);after=completed(n,report);d=after['geometry']['proxy_details']
    if defect=='missing':d['angle'].pop()
    if defect=='extra':d['angle'].append(deepcopy(d['angle'][-1]))
    if defect=='wrong_weight':d['angle'][-1]['weight']*=2
    if defect=='wrong_origin':d['angle'][-1]['origin_id']=0
    if defect=='old_proxy':d['bond_simple'][0]['weight']*=2
    if defect=='coordinate':after['atoms'][0]['xyz']=[1.,2.,3.]
    if defect=='definition':after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['atoms'].pop()
    if defect=='requests':after['geometry']['custom_proxy_requests'].pop()
    after['geometry']['proxy_counts']={k:len(v) for k,v in d.items()}
    assert qualify_fana_junction_angles(paths[-1],after)['status']=='REVIEW'


def test_cold_reader_recomputes_outputs_and_keeps_originals(tmp_path):
    from nasolve.cif_fana_junction import read_fana_junction_angles
    from nasolve.cif_fana_component import _digest
    original=tmp_path/'original';original.mkdir();paths,n=fixture(original);q=prepare(paths)
    moved=original.rename(tmp_path/'relocated');root=moved/'junction';before=snapshot(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):assert read_fana_junction_angles(root)==q
    assert not original.exists() and snapshot(moved)==before
    receipt=json.loads((root/'receipt.json').read_text());(root/'angles.phil').write_text('bad')
    receipt['files']['angles.phil']=_digest(root/'angles.phil');save(root/'receipt.json',receipt)
    with pytest.raises(ValueError):read_fana_junction_angles(root)


def test_already_covered_angles_are_not_duplicated(tmp_path):
    paths,n=fixture(tmp_path);q=prepare(paths);save(paths[2],completed(n,q));new=(*paths[:-1],tmp_path/'second')
    report=prepare(new);assert report['requests']==[] and report['phosphate_angles_before']==6
    assert 'action = add' not in (new[-1]/'angles.phil').read_text()


def test_existing_output_and_symlink_are_refused(tmp_path):
    from nasolve.cif_fana_junction import read_fana_junction_angles
    paths,n=fixture(tmp_path);prepare(paths);before=snapshot(tmp_path)
    with pytest.raises(FileExistsError):prepare(paths)
    assert snapshot(tmp_path)==before
    p=paths[-1]/'native.json';p.unlink();p.symlink_to(paths[2])
    with pytest.raises(ValueError):read_fana_junction_angles(paths[-1])


@pytest.mark.parametrize('sigma',['0','-1','1e-200','1e200','inf'])
def test_unrepresentable_template_weights_refuse_before_output(tmp_path,sigma):
    from nasolve.ligand_profiles import _blocks
    paths,n=fixture(tmp_path);v=_blocks(paths[3])[0].values
    v['_chem_link_angle.value_angle_esd'][1]=sigma;paths[3].write_text(_emit(v))
    with pytest.raises(ValueError):prepare(paths)
    assert not paths[-1].exists()


def test_translated_control_is_allowed_but_deformation_is_not(tmp_path):
    from nasolve.cif_construction_provenance import _pdb_inventory
    paths,n=fixture(tmp_path);control,model,capture,link,out=paths
    shifted=tmp_path/'shifted.pdb';lines=[]
    for line in model.read_text().splitlines(keepends=True):
        if line[:6] in {'ATOM  ','HETATM'} and line[21:26]=='A   2':
            xyz=[float(line[i:i+8])+d for i,d in zip((30,38,46),(1.,2.,3.))]
            line=line[:30]+''.join(f'{x:8.3f}' for x in xyz)+line[54:]
        lines.append(line)
    shifted.write_text(''.join(lines));inv=_pdb_inventory(shifted)
    for a in n['atoms']:
        i=a['identity'];a['xyz']=inv[(i['chain_id'],i['resseq'],i['icode'],i['altloc'],a['atom_id'])]['xyz']
    n['geometry']['sites_cart_exact']=[a['xyz'] for a in n['atoms']];save(capture,n)
    q=prepare((control,shifted,capture,link,out));assert q['translation_angstrom']==[1.,2.,3.]
    # A changed single coordinate cannot hide behind a matching native capture.
    chosen=next(a for a in n['atoms'] if a['identity']['resseq']=='2' and a['atom_id']=='F')
    chosen['xyz'][0]+=1
    for i,line in enumerate(lines):
        if line[:6] in {'ATOM  ','HETATM'} and line[21:26]=='A   2' and line[12:16].strip()=='F':
            lines[i]=line[:30]+f"{float(line[30:38])+1:8.3f}"+line[38:]
    shifted.write_text(''.join(lines));save(capture,n)
    with pytest.raises(ValueError,match='translated whole residue'):prepare((control,shifted,capture,link,tmp_path/'bad'))


@pytest.mark.parametrize('defect',['report','extra','incomplete','receipt'])
def test_corrupt_or_incomplete_package_never_reuses_saved_success(tmp_path,defect):
    from nasolve.cif_fana_junction import read_fana_junction_angles
    from nasolve.cif_fana_component import _digest
    paths,n=fixture(tmp_path);prepare(paths);root=paths[-1];r=json.loads((root/'receipt.json').read_text())
    if defect=='report':
        q=json.loads((root/'junction.json').read_text());q['chemical_qualification']='PASS';save(root/'junction.json',q);r['files']['junction.json']=_digest(root/'junction.json')
    if defect=='extra':(root/'unbound.txt').write_text('unbound')
    if defect=='receipt':r['schema_version']=True
    save(root/'receipt.json',r)
    if defect=='incomplete':(root/'receipt.json').unlink()
    with pytest.raises((ValueError,FileNotFoundError)):read_fana_junction_angles(root)
