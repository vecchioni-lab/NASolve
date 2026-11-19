"""Graph-bound native modifiers; synthetic chemistry is not native qualification."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest
from tests.test_cif_whole_furanose import setup as frame_setup
from tests.test_cif_catalogue import snapshot
from tests.test_cif_stereochemistry_audit import write


def setup(tmp_path, *, bridged=False, rename=False, hand='D', incoming=True, outgoing=True):
    from nasolve.cif_stereochemistry_audit import _values, _coordinates
    paths,c,roles=frame_setup(tmp_path,bridged=bridged,rename=rename,hand=hand)
    v=_values(paths[1],'Z99');ids=v['_chem_comp_atom.atom_id']
    v['_chem_comp_atom.type_energy'][ids.index(roles['three_o'])]='OH1'
    v['_chem_comp.group']=['non-polymer'];write(paths[1],v)
    leaving=c['ports']['phosphate']['leaving_atom']
    lines=[]
    for l in paths[4].read_text().splitlines(keepends=True):
        if l[:6] in {'ATOM  ','HETATM'} and l[21:26]!='A  11':l=l[:17]+'HST'+l[20:]
        if l.startswith(('TER','END')):continue
        lines.append(l)
    if not incoming:
        xyz=_coordinates(v,source=False)[1][leaving]
        index=next(i for i,l in enumerate(lines) if l[:6] in {'ATOM  ','HETATM'} and l[21:26]=='A  12')
        lines.insert(index,f'HETATM99999 {leaving:>4} Z99 A  11    '+''.join(f'{x:8.3f}' for x in xyz)+'  1.00 20.00           O\n')
        c['ports']['phosphate']={'state':'source'}
    else:c['ports']['phosphate']['partner']['component']='HST'
    if not outgoing:c['ports']['alcohol']={'state':'source'}
    else:c['ports']['alcohol']['partner']['component']='HST'
    paths[4].write_text(''.join(lines)+'END\n')
    return [paths[0],paths[1],paths[3],paths[4],tmp_path/'reaction'],[c],roles


def run(paths,contexts):
    from nasolve.cif_furanose_reaction import prepare_furanose_reaction_control
    return prepare_furanose_reaction_control(*paths,code='Z99',contexts=contexts)


@pytest.mark.parametrize('bridged,rename,hand',[(False,False,'D'),(False,True,'L'),(True,False,'D'),(True,True,'D')])
@pytest.mark.parametrize('incoming,outgoing',[(True,True),(True,False),(False,True),(False,False)])
def test_graph_operations_preserve_source_classification_hands_and_unreacted_state(tmp_path,bridged,rename,hand,incoming,outgoing):
    from nasolve.cif_furanose_reaction import read_furanose_reaction_control
    from nasolve.cif_linked_preparation import component_values, atom_rows
    paths,c,roles=setup(tmp_path,bridged=bridged,rename=rename,hand=hand,incoming=incoming,outgoing=outgoing)
    before=snapshot(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):
        r=run(paths,c);assert read_furanose_reaction_control(paths[-1])==r
    site=r['sites'][0];v=site['projected_definition'];atoms=atom_rows(v)
    assert len(site['source_configuration_projection'])==4
    assert v['_chem_comp.group']==['non-polymer']
    assert atoms[roles['three_o']]['type_energy']==('OC2' if outgoing else 'OH1')
    assert len(site['deleted_atoms'])==(2 if incoming else 0)+(1 if outgoing else 0)
    base=component_values(paths[-1]/'base_dictionary.cif','Z99')
    assert base['_chem_comp.group']==['non-polymer'] and base['_chem_comp.type']==v['_chem_comp.type']
    assert r['native_qualification']=='NOT_ASSESSED' and r['partner_chemistry']=='NOT_ASSESSED' and not r['automatic_adoption']
    assert all(snapshot(tmp_path)[k]==v for k,v in before.items())
    assert str(tmp_path) not in json.dumps(r)
    if bridged:assert roles['bridge_c'] in atoms and roles['bridge_o'] in atoms


@pytest.mark.parametrize('defect',['mirror','charge','missing_chirality','unknown_type','leaving_double','symmetry','extra_context','duplicate_site','uncovered_site'])
def test_unproved_reactions_refuse_without_output(tmp_path,defect):
    from nasolve.cif_stereochemistry_audit import _values
    paths,c,roles=setup(tmp_path)
    if defect in {'mirror','charge','missing_chirality','unknown_type'}:
        v=_values(paths[1],'Z99');ids=v['_chem_comp_atom.atom_id']
        if defect=='mirror':v['_chem_comp_atom.z']=[str(-float(x)) for x in v['_chem_comp_atom.z']]
        if defect=='charge':v['_chem_comp_atom.charge'][ids.index(roles['three_o'])]='-1'
        if defect=='missing_chirality':v={k:x for k,x in v.items() if not k.startswith('_chem_comp_chir.')}
        if defect=='unknown_type':v['_chem_comp_atom.type_energy'][ids.index(roles['three_o'])]='UNKNOWN'
        write(paths[1],v)
    if defect=='leaving_double':c[0]['ports']['phosphate']['leaving_atom']='P1'
    if defect=='symmetry':c[0]['ports']['alcohol']['symmetry_operation']='-x,y,z'
    if defect=='extra_context':c[0]['guess']=True
    if defect=='duplicate_site':c.append(deepcopy(c[0]))
    if defect=='uncovered_site':paths[3].write_text(paths[3].read_text().replace('HST A  10','Z99 A  10'))
    with pytest.raises(ValueError):run(paths,c)
    assert not paths[-1].exists()


@pytest.mark.parametrize('defect',['report','modifiers','parameters','base','context','extra','schema','symlink'])
def test_offline_replay_refuses_rehashed_forgery(tmp_path,defect):
    from nasolve.cif_furanose_reaction import read_furanose_reaction_control
    from nasolve.cif_fana_component import _digest
    paths,c,_=setup(tmp_path);run(paths,c);root=paths[-1];p=root/'receipt.json';r=json.loads(p.read_text());name=None
    if defect=='report':
        name='preparation.json';v=json.loads((root/name).read_text());v['native_qualification']='PASS';(root/name).write_text(json.dumps(v))
    if defect in {'modifiers','parameters','base'}:
        name={'modifiers':'site_modifications.cif','parameters':'site_modifications.phil','base':'base_dictionary.cif'}[defect];(root/name).write_text((root/name).read_text()+'# forged\n')
    if defect=='context':
        name='contexts.json';c[0]['ports']['phosphate']['leaving_atom']='P1';(root/name).write_text(json.dumps(c))
    if defect=='extra':(root/'extra').write_text('extra')
    if defect=='schema':r['schema_version']=True
    if defect=='symlink':(root/'source.cif').unlink();(root/'source.cif').symlink_to(paths[0])
    if name:r['files'][name]=_digest(root/name)
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError):read_furanose_reaction_control(root)


def test_cold_relocation_and_existing_partial_attempt(tmp_path):
    from nasolve.cif_furanose_reaction import read_furanose_reaction_control
    original=tmp_path/'original';original.mkdir();paths,c,_=setup(original,bridged=True);r=run(paths,c)
    with pytest.raises(FileExistsError):run(paths,c)
    moved=original.rename(tmp_path/'moved');before=snapshot(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):assert read_furanose_reaction_control(moved/'reaction')==r
    assert not original.exists() and snapshot(moved)==before


def test_three_same_code_sites_keep_independent_terminal_and_internal_states(tmp_path):
    from nasolve.cif_stereochemistry_audit import _values, _coordinates
    from nasolve.cif_linked_preparation import atom_rows
    paths,contexts,roles=setup(tmp_path,bridged=True)
    model=paths[3];lines=[l for l in model.read_text().splitlines(keepends=True)
        if l[:6] not in {'ATOM  ','HETATM'} or l[21:26]!='A  20']
    for i,l in enumerate(lines):
        if l[:6] in {'ATOM  ','HETATM'}:lines[i]=l[:17]+'Z99'+l[20:]
    xyz=_coordinates(_values(paths[1],'Z99'),source=False)[1]['OXT']
    index=next(i for i,l in enumerate(lines) if l[:6] in {'ATOM  ','HETATM'} and l[21:26]=='A  11')
    lines.insert(index,'HETATM99999  OXT Z99 A  10    '+''.join(f'{x:8.3f}' for x in xyz)+'  1.00 20.00           O\n')
    model.write_text(''.join(lines));contexts=[]
    for i in (10,11,12):
        ports={}
        for name,other,atom in [('phosphate',i-1,roles['three_o']),('alcohol',i+1,roles['phosphate'])]:
            if other not in (10,11,12):ports[name]={'state':'source'}
            else:
                ports[name]={'state':'linked','partner':{'site':f'A:{other}','component':'Z99','atom_id':atom},'symmetry_operation':'x,y,z'}
                if name=='phosphate':ports[name]['leaving_atom']='OXT'
        contexts.append({'schema_version':1,'site':f'A:{i}','ports':ports})
    r=run(paths,list(reversed(contexts)));sites={s['site']:s for s in r['sites']}
    assert [sites[f'A:{i}']['deleted_atoms'] for i in (10,11,12)]==[['HA'],['HA','HXT','OXT'],['HXT','OXT']]
    assert len({s['modification_id'] for s in r['sites']})==3
    assert atom_rows(sites['A:10']['projected_definition'])["O3'"]['type_energy']=='OC2'
    assert atom_rows(sites['A:12']['projected_definition'])["O3'"]['type_energy']=='OH1'
    assert 'HO2P' in atom_rows(sites['A:11']['projected_definition'])
    text=(paths[-1]/'site_modifications.cif').read_text()
    for s in r['sites']:assert 'data_mod_'+s['modification_id'] in text


@pytest.mark.parametrize('kind',['parent_symlink','partial','interruption'])
def test_attempts_are_never_repaired_in_place(tmp_path,kind):
    import nasolve.cif_furanose_reaction as module
    paths,c,_=setup(tmp_path)
    if kind=='parent_symlink':
        link=tmp_path/'link';link.symlink_to(tmp_path,target_is_directory=True);paths[-1]=link/'new'
        with pytest.raises(ValueError):run(paths,c)
    elif kind=='partial':
        paths[-1].mkdir();(paths[-1]/'partial').write_text('preserve');before=snapshot(tmp_path)
        with pytest.raises(FileExistsError):run(paths,c)
        assert snapshot(tmp_path)==before
    else:
        original=module._derive;calls=0
        def interrupt(*args):
            nonlocal calls
            calls+=1
            if calls==2:raise RuntimeError('interrupted')
            return original(*args)
        with patch.object(module,'_derive',interrupt),pytest.raises(RuntimeError):run(paths,c)
        assert (paths[-1]/'model.pdb').exists() and not (paths[-1]/'receipt.json').exists()
        with pytest.raises(FileExistsError):run(paths,c)


def test_native_preparation_cannot_relabel_source_polymer_class(tmp_path):
    from nasolve.cif_stereochemistry_audit import _values
    paths,c,_=setup(tmp_path,bridged=True);v=_values(paths[1],'Z99')
    assert v['_chem_comp.type'][0].upper()=='RNA LINKING'
    v['_chem_comp.type']=['DNA LINKING'];write(paths[1],v)
    with pytest.raises(ValueError,match='classification'):run(paths,c)
    assert not paths[-1].exists()


def test_missing_numerical_classification_is_carried_from_source(tmp_path):
    from nasolve.cif_stereochemistry_audit import _values
    from nasolve.cif_linked_preparation import component_values
    paths,c,_=setup(tmp_path,bridged=True);v=_values(paths[1],'Z99');v.pop('_chem_comp.type');write(paths[1],v)
    before=paths[1].read_bytes();r=run(paths,c)
    assert r['metadata_changes']==[{'field':'_chem_comp.type','before':None,'after':['RNA LINKING'],'authority':'SOURCE'}]
    assert component_values(paths[-1]/'base_dictionary.cif','Z99')['_chem_comp.type']==['RNA LINKING']
    assert paths[1].read_bytes()==before and r['numerical_group_preserved'] and r['source_classification_preserved']
