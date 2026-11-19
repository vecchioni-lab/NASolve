"""Whole-sugar graph transfer; synthetic targets are not physical geometry proofs."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest
from tests.test_cif_fana import molecule, numerical
from tests.test_cif_catalogue import workbook, row, snapshot, source as public_source
from tests.test_cif_stereochemistry_audit import write


def setup(tmp_path, *, bridged=False, rename=False, hand='D'):
    from nasolve.cif_stereochemistry_audit import _values, _coordinates, _graph
    from nasolve.cif_attachment_profiles import inspect_attachment_profile
    if bridged:
        v=_values(public_source(tmp_path/'public','ATL'),'ATL');xyz=_coordinates(v,source=True)[1]
        for axis,i in zip('xyz',range(3)):v['_chem_comp_atom.'+axis]=[str(xyz[n][i]) for n in v['_chem_comp_atom.atom_id']]
        for key in v:
            if key.endswith('.comp_id') or key=='_chem_comp.id':v[key]=['Z99']*len(v[key])
        v['data_']='Z99'
    else:
        v,_=molecule(hand=hand)
        if hand=='L':v['_chem_comp_atom.z']=[str(-float(x)) for x in v['_chem_comp_atom.z']]
    names={n:('X'+str(i)) if rename else n for i,n in enumerate(v['_chem_comp_atom.atom_id'])}
    for key in v:
        if 'atom_id' in key:v[key]=[names.get(n,n) for n in v[key]]
    base=names['N1' if bridged else 'BN'];carbon=names['C5' if bridged else 'BC']
    book=workbook(tmp_path,[('thymine' if bridged else 'cytosine',row('Z99',N1=base,C5=carbon))])
    source=write(tmp_path/'source.cif',v);candidate=write(tmp_path/'candidate.cif',numerical(v))
    roles=inspect_attachment_profile(source,'Z99',workbook=book)['bindings']
    leaving=names['OXT' if bridged else 'OP3'];xyz=_coordinates(_values(candidate,'Z99'),source=False)[1];elements=_graph(v)[0]
    lines=['REMARK untouched diagnostic frame\n'];serial=0
    for site in (10,11,12,20):
        for n,p in xyz.items():
            if elements[n] in {'H','D'} or n==leaving:continue
            serial+=1;x,y,z=p;x,y,z=-y+site*5,x+10,z+2
            lines.append(f'ATOM  {serial:5d} {n:>4} Z99 A{site:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  0.75 12.50          {elements[n]:>2}\n')
    frame=tmp_path/'frame.pdb';frame.write_text(''.join(lines)+'TER\nEND\n')
    context={'schema_version':1,'site':'A:11','ports':{
        'phosphate':{'state':'linked','partner':{'site':'A:10','component':'Z99','atom_id':roles['three_o']},'symmetry_operation':'x,y,z','leaving_atom':leaving},
        'alcohol':{'state':'linked','partner':{'site':'A:12','component':'Z99','atom_id':roles['phosphate']},'symmetry_operation':'x,y,z'}}}
    return [source,candidate,source,book,frame,tmp_path/'control'],context,roles


def run(paths,context):
    from nasolve.cif_whole_furanose import prepare_whole_furanose_control
    return prepare_whole_furanose_control(*paths,code='Z99',context=context)


@pytest.mark.parametrize('bridged,rename,hand',[(False,False,'D'),(False,True,'D'),(False,False,'L'),(True,False,'D'),(True,True,'D')])
def test_graph_bound_whole_sugar_keeps_bridge_names_and_hands(tmp_path,bridged,rename,hand):
    from nasolve.cif_whole_furanose import read_whole_furanose_control
    paths,context,roles=setup(tmp_path,bridged=bridged,rename=rename,hand=hand);before=snapshot(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):
        q=run(paths,context);assert read_whole_furanose_control(paths[-1])==q
    assert q['source_projection']['plan_status']=='PROPOSED'
    assert len({r['center'] for r in q['retained_hands']})==4
    assert q['max_internal_distance_error_angstrom']<=.002 and q['native_linkage']=='NOT_ASSESSED'
    assert not q['automatic_adoption'] and q['partner_chemistry']=='NOT_ASSESSED'
    if bridged:assert roles['bridge_c'] in q['model_heavy_atoms'] and len(q['retained_hands'])==7
    unchanged=lambda p:[l for l in p.read_text().splitlines() if not(l[:6] in {'ATOM  ','HETATM'} and l[21:26]=='A  11')]
    assert unchanged(paths[4])==unchanged(paths[-1]/'model.pdb')
    assert all(snapshot(tmp_path)[k]==v for k,v in before.items())
    assert str(tmp_path) not in json.dumps(q)


@pytest.mark.parametrize('defect',['mirror','missing_f','charge','missing_chirality','wrong_host_hand','flat','altloc','link_record','serial','symmetry','wrong_partner','leaving_double','source_port','extra_context'])
def test_unproved_changes_refuse(tmp_path,defect):
    from nasolve.cif_stereochemistry_audit import _values
    paths,c,roles=setup(tmp_path)
    if defect in {'mirror','missing_f','charge','missing_chirality'}:
        v=_values(paths[1],'Z99');a='_chem_comp_atom.'
        if defect=='mirror':v[a+'z']=[str(-float(x)) for x in v[a+'z']]
        if defect=='missing_f':v[a+'type_symbol'][v[a+'atom_id'].index('F')]='O'
        if defect=='charge':v[a+'charge'][v[a+'atom_id'].index('OP3')]='-1'
        if defect=='missing_chirality':v={k:x for k,x in v.items() if not k.startswith('_chem_comp_chir.')}
        write(paths[1],v)
    elif defect in {'symmetry','wrong_partner','leaving_double','source_port','extra_context'}:
        if defect=='symmetry':c['ports']['phosphate']['symmetry_operation']='-x,y,z'
        if defect=='wrong_partner':c['ports']['phosphate']['partner']['component']='BAD'
        if defect=='leaving_double':c['ports']['phosphate']['leaving_atom']='P1'
        if defect=='source_port':c['ports']['alcohol']={'state':'source'}
        if defect=='extra_context':c['guess']=True
    else:
        lines=paths[4].read_text().splitlines(keepends=True)
        if defect=='link_record':lines.insert(0,'LINK  stale\n')
        for i,l in enumerate(lines):
            if l[:6]!='ATOM  ':continue
            if defect=='wrong_host_hand' and l[21:26]=='A  11':l=l[:46]+f'{-float(l[46:54]):8.3f}'+l[54:]
            if defect=='flat' and l[21:26]=='A  11':l=l[:30]+f'{0:8.3f}'*3+l[54:]
            if defect=='altloc':l=l[:16]+'A'+l[17:]
            if defect=='serial':l=l[:6]+'    1'+l[11:]
            lines[i]=l
        paths[4].write_text(''.join(lines))
    with pytest.raises(ValueError):run(paths,c)
    assert not (paths[-1]/'receipt.json').exists()


@pytest.mark.parametrize('defect',['model','report','context','extra','symlink','schema','incomplete'])
def test_replay_refuses_forgery_even_rehashed(tmp_path,defect):
    from nasolve.cif_whole_furanose import read_whole_furanose_control
    from nasolve.cif_fana_component import _digest
    paths,c,_=setup(tmp_path);run(paths,c);root=paths[-1];p=root/'receipt.json';r=json.loads(p.read_text());name=None
    if defect=='model':name='model.pdb';(root/name).write_text((root/name).read_text().replace('20.00','99.00'))
    if defect=='report':name='placement.json';v=json.loads((root/name).read_text());v['native_linkage']='PASS';(root/name).write_text(json.dumps(v))
    if defect=='context':name='context.json';c['ports']['phosphate']['leaving_atom']='P2';(root/name).write_text(json.dumps(c))
    if defect=='extra':(root/'extra').write_text('x')
    if defect=='symlink':(root/'source.cif').unlink();(root/'source.cif').symlink_to(paths[0])
    if defect=='schema':r['schema_version']=True
    if name:r['files'][name]=_digest(root/name)
    p.write_text(json.dumps(r))
    if defect=='incomplete':p.unlink()
    with pytest.raises((ValueError,FileNotFoundError)):read_whole_furanose_control(root)


def test_cold_relocation_and_immutable_attempt(tmp_path):
    from nasolve.cif_whole_furanose import read_whole_furanose_control
    original=tmp_path/'original';original.mkdir();paths,c,_=setup(original,bridged=True);q=run(paths,c)
    with pytest.raises(FileExistsError):run(paths,c)
    moved=original.rename(tmp_path/'moved');before=snapshot(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):assert read_whole_furanose_control(moved/'control')==q
    assert not original.exists() and snapshot(moved)==before


def test_host_and_target_atom_names_are_independently_bound(tmp_path):
    from nasolve.cif_stereochemistry_audit import _values
    paths,c,roles=setup(tmp_path);v=_values(paths[2],'Z99');mapping={n:'Y'+str(i) for i,n in enumerate(v['_chem_comp_atom.atom_id'])}
    for key in v:
        if 'atom_id' in key:v[key]=[mapping.get(n,n) for n in v[key]]
        if key.endswith('.comp_id') or key=='_chem_comp.id':v[key]=['HST']*len(v[key])
    host=write(tmp_path/'host.cif',v);paths[2]=host
    paths[3]=workbook(tmp_path,[('cytosine',row('Z99',N1='BN',C5='BC')),('cytosine',row('HST',N1=mapping['BN'],C5=mapping['BC']))])
    lines=paths[4].read_text().splitlines(keepends=True)
    for i,l in enumerate(lines):
        if l[:6]=='ATOM  ' and l[21:26]=='A  11':lines[i]=l[:12]+f"{mapping[l[12:16].strip()]:>4}"+l[16:17]+'HST'+l[20:]
    paths[4].write_text(''.join(lines));q=run(paths,c)
    assert len(q['host_hand_checks'])==3 and 'C1' in q['model_heavy_atoms']


@pytest.mark.parametrize('kind',['parent_symlink','existing_output','interruption'])
def test_fresh_attempt_boundaries(tmp_path,kind):
    import nasolve.cif_whole_furanose as module
    paths,c,_=setup(tmp_path)
    if kind=='parent_symlink':
        link=tmp_path/'link';link.symlink_to(tmp_path,target_is_directory=True);paths[-1]=link/'new'
        with pytest.raises(ValueError):run(paths,c)
    elif kind=='existing_output':
        paths[-1].mkdir();(paths[-1]/'partial.txt').write_text('preserved');before=snapshot(tmp_path)
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
        assert (paths[-1]/'frame.pdb').exists() and not (paths[-1]/'receipt.json').exists()
        with pytest.raises(FileExistsError):run(paths,c)


def test_fixed_chiral_source_centres_without_rs_labels_are_preserved(tmp_path):
    from nasolve.cif_stereochemistry_audit import _values
    paths,c,_=setup(tmp_path)
    v=_values(paths[1],'Z99');v['_chem_comp_atom.pdbx_stereo_config']=['N']*len(v['_chem_comp_atom.atom_id'])
    write(paths[0],v);write(paths[1],v)
    q=run(paths,c)
    assert {r['center'] for r in q['retained_hands']}=={'C1','C2','C3','C4'}
