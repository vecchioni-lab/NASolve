"""A native input row order must never become a phosphate chemistry edit."""
from collections import Counter
from copy import deepcopy
from itertools import permutations
from pathlib import Path

import pytest

from nasolve.cif_linked_preparation import component_values, _render
from nasolve.ligand_profiles import _blocks, _emit

A, B = '_chem_comp_atom.', '_chem_comp_bond.'


def phosphate(code='Q17'):
    names = ['J9', 'OX', 'OY', 'OZ', 'OW', 'C8', 'H8']
    return {'data_':'comp_'+code, '_chem_comp.id':[code],
        A+'comp_id':[code]*7, A+'atom_id':names,
        A+'type_symbol':['P','O','O','O','O','C','H'],
        A+'charge':['0','-1','0','-1','0','0','0'],
        A+'pdbx_stereo_config':['?']*7,
        A+'x':['0','1','0','0','-1','-2','-3'],
        A+'y':['0','0','1','0','-1','-2','-3'],
        A+'z':['0','0','0','1','-1','-2','-3'],
        B+'comp_id':[code]*6, B+'atom_id_1':['J9']*4+['OW','C8'],
        B+'atom_id_2':['OX','OY','OW','OZ','C8','H8'],
        B+'type':['single','double','single','single','single','single'],
        B+'value_order':['SING','DOUB','SING','SING','SING','SING'],
        B+'value_dist':['1.61','1.48','1.60','1.62','1.43','1.0'],
        B+'value_dist_esd':['0.02']*6, B+'ordinal':['19','3','5','11','4','6'],
        '_chem_comp_chir.comp_id':[code], '_chem_comp_chir.id':['Pboth'],
        '_chem_comp_chir.atom_id_centre':['J9'], '_chem_comp_chir.atom_id_1':['OX'],
        '_chem_comp_chir.atom_id_2':['OY'], '_chem_comp_chir.atom_id_3':['OW'],
        '_chem_comp_chir.volume_sign':['both']}


def prepare(source, output, code='Q17'):
    from nasolve.cif_elbow_input import prepare_elbow_phosphate_bond_order
    return prepare_elbow_phosphate_bond_order(source, code, output)


def write(path, values, monomer=True):
    path.write_text(_render(values, values['_chem_comp.id'][0]) if monomer else _emit(values))
    return path


def bond_rows(values):
    keys=sorted(k for k in values if k.lower().startswith(B))
    return Counter(zip(*(values[k] for k in keys)))


@pytest.mark.parametrize('code', ['Q17','Z93'])
def test_all_bond_row_orders_preserve_complete_rows_and_every_other_field(tmp_path, code):
    original=phosphate(code)
    for i, order in enumerate(permutations(range(4))):
        v=deepcopy(original)
        indices=list(order)+[4,5]
        for key in v:
            if key.startswith(B):v[key]=[v[key][j] for j in indices]
        source=write(tmp_path/f'source-{i}.cif',v)
        before=source.read_bytes(),source.stat().st_mtime_ns
        out=tmp_path/f'out-{i}.cif';report=prepare(source,out,code)
        actual=component_values(out,code)
        assert bond_rows(actual)==bond_rows(v)
        assert {k:x for k,x in actual.items() if not k.startswith(B)}=={k:x for k,x in v.items() if not k.startswith(B)}
        assert _blocks(out)[0].text==_blocks(source)[0].text
        # Mimic only the observed native choice: first terminal oxygen in bond order.
        first=next(n for n in actual[B+'atom_id_2'] if n in {'OX','OY','OZ'})
        assert first=='OY'
        assert report['sites'][0]['declared_double_bond']==['J9','OY']
        assert report['chemical_declarations']=='PRESERVED'
        assert report['native_qualification']=='NOT_RUN' and report['automatic_adoption'] is False
        assert (source.read_bytes(),source.stat().st_mtime_ns)==before
        again=tmp_path/f'again-{i}.cif'
        assert prepare(out,again,code)['changed'] is False
        assert again.read_bytes()==out.read_bytes()


@pytest.mark.parametrize('defect', ['no_double','two_doubles','delocalized','conflicting_alias',
    'unknown_order','three_neighbours','duplicate_edge','unknown_endpoint','other_component','extra_block'])
def test_ambiguous_source_does_not_guess_or_write_output(tmp_path, defect):
    v=phosphate()
    if defect=='no_double':v[B+'type'][1]='single';v[B+'value_order'][1]='SING'
    if defect=='two_doubles':v[B+'type'][0]='double';v[B+'value_order'][0]='DOUB'
    if defect=='delocalized':v[B+'type'][1]='deloc';v[B+'value_order'][1]='DELO'
    if defect=='conflicting_alias':v[B+'value_order'][0]='DOUB'
    if defect=='unknown_order':v[B+'type'][0]='?';v[B+'value_order'][0]='?'
    if defect=='three_neighbours':
        for key in list(v):
            if key.startswith(B):v[key].pop(3)
    if defect=='duplicate_edge':v[B+'atom_id_2'][0]='OY'
    if defect=='unknown_endpoint':v[B+'atom_id_2'][0]='MISSING'
    if defect=='other_component':v[B+'comp_id'][0]='ZZ9'
    source=write(tmp_path/'source.cif',v)
    if defect=='extra_block':source.write_text(source.read_text()+'\ndata_unrelated\n_foo.bar 42\n')
    with pytest.raises(ValueError):prepare(source,tmp_path/'out.cif')
    assert not (tmp_path/'out.cif').exists()


def test_no_phosphorus_is_byte_exact_and_does_not_reorder_other_double_bonds(tmp_path):
    from tests.test_cif_stereochemistry_audit import tetrahedron
    v,_=tetrahedron();source=write(tmp_path/'source.cif',v)
    out=tmp_path/'out.cif';report=prepare(source,out)
    assert not report['changed'] and report['sites']==[]
    assert out.read_bytes()==source.read_bytes()


def test_explicit_adapter_requires_monomer_dialect(tmp_path):
    source=write(tmp_path/'source.cif',phosphate(),False)
    with pytest.raises(ValueError,match='monomer'):prepare(source,tmp_path/'out.cif')


def test_existing_output_and_symlink_ancestors_are_not_overwritten(tmp_path):
    source=write(tmp_path/'source.cif',phosphate());out=tmp_path/'out.cif'
    out.write_bytes(b'owned elsewhere')
    with pytest.raises(FileExistsError):prepare(source,out)
    assert out.read_bytes()==b'owned elsewhere'
    folder=tmp_path/'real';folder.mkdir();alias=tmp_path/'alias';alias.symlink_to(folder,target_is_directory=True)
    with pytest.raises(ValueError):prepare(source,alias/'out.cif')
    assert not (folder/'out.cif').exists()


def test_real_curated_source_survives_relocation_with_original_path_gone(tmp_path):
    source=tmp_path/'original.cif';source.write_bytes((Path(__file__).resolve().parents[1]/'src/nasolve/data/ligands/1AP.cif').read_bytes())
    original=source.read_bytes();out=tmp_path/'prepared.cif';report=prepare(source,out,'1AP')
    assert report['changed']
    assert bond_rows(component_values(source,'1AP'))==bond_rows(component_values(out,'1AP'))
    moved=tmp_path/'relocated';moved.mkdir();source.rename(moved/'source.cif');out.rename(moved/'prepared.cif')
    assert not source.exists() and not out.exists()
    assert prepare(moved/'source.cif',moved/'replayed.cif','1AP')==report
    assert (moved/'replayed.cif').read_bytes()==(moved/'prepared.cif').read_bytes()
    assert (moved/'source.cif').read_bytes()==original


def test_two_phosphates_keep_separate_declared_double_oxygens(tmp_path):
    v=phosphate()
    v[A+'type_symbol'][5:]=['P','O'];v[A+'charge'][6]='-1'
    for key, extra in {'comp_id':['Q17']*2, 'atom_id':['OQ','OR'],
            'type_symbol':['O','O'], 'charge':['-1','0'], 'pdbx_stereo_config':['?','?'],
            'x':['-3','-2'], 'y':['-2','-3'], 'z':['-2','-2']}.items():
        v[A+key].extend(extra)
    for key, extra in {'comp_id':['Q17']*2,'atom_id_1':['C8','C8'],
            'atom_id_2':['OQ','OR'],'type':['single','double'],'value_order':['SING','DOUB'],
            'value_dist':['1.61','1.48'],'value_dist_esd':['0.02']*2,'ordinal':['8','12']}.items():
        v[B+key].extend(extra)
    source=write(tmp_path/'source.cif',v);out=tmp_path/'out.cif';report=prepare(source,out)
    actual=component_values(out,'Q17');assert bond_rows(actual)==bond_rows(v)
    assert {tuple(s['declared_double_bond']) for s in report['sites']}=={('J9','OY'),('C8','OR')}
    pairs=list(zip(actual[B+'atom_id_1'],actual[B+'atom_id_2']))
    assert next(n for c,n in pairs if c=='J9' and n in {'OX','OY','OZ'})=='OY'
    assert next(n for c,n in pairs if c=='C8' and n in {'H8','OQ','OR'})=='OR'
