"""Original deposition precision is distinct from its working PDB preview."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
import shutil

import pytest
gemmi = pytest.importorskip('gemmi')
from nasolve.topostitch_cif_source import load_relabel_cif_source
from tests.test_topostitch_scattering import saved_scattering_packet


def fixture(tmp_path):
    root, digest, _ = saved_scattering_packet(tmp_path)
    source = gemmi.read_pdb_string((root/'source.pdb').read_text())
    doc = source.make_mmcif_document(); block = doc.sole_block()
    atoms = block.get_mmcif_category('_atom_site.')
    # Deliberately retain information absent from the working three-place PDB.
    atoms['Cartn_x'][0] = format(float(atoms['Cartn_x'][0])+.000123456789, '.17g')
    atoms['B_iso_or_equiv'][0] = format(float(atoms['B_iso_or_equiv'][0])+.00123456789, '.17g')
    original = atoms['label_comp_id'][0]
    atoms['label_comp_id'] = ['LONG1' if c == original else c for c in atoms['label_comp_id']]
    if 'auth_comp_id' in atoms:
        atoms['auth_comp_id'] = ['LONG1' if c == original else c for c in atoms['auth_comp_id']]
    block.set_mmcif_category('_atom_site.', atoms)
    adp = block.get_mmcif_category('_atom_site_anisotrop.')
    adp['U[1][1]'][0] = format(float(adp['U[1][1]'][0])+.0000123456789, '.17g')
    block.set_mmcif_category('_atom_site_anisotrop.', adp)
    component = doc.add_new_block('comp_LONG1'); component.set_pair('_chem_comp.id', 'LONG1')
    component.set_pair('_chem_comp.name', "'explicit supplied component spelling'")
    path = tmp_path/'original.cif'; doc.write_file(str(path))
    kw = dict(expected_receipt_sha256=digest, expected_model_sha256=sha256(path.read_bytes()).hexdigest(),
        component_aliases={'LONG1':original}, max_coordinate_component_error_angstrom=.000501,
        max_u_component_error_angstrom_squared=.0000501,
        max_b_error_angstrom_squared=.00501, max_occupancy_error=.00501)
    return root, path, kw


def edit(path, fn):
    doc = gemmi.cif.read_file(str(path)); fn(doc); doc.write_file(str(path))
    return sha256(path.read_bytes()).hexdigest()


def test_original_precision_and_names_define_distinct_immutable_frame(tmp_path):
    root,path,kw=fixture(tmp_path);before={p:p.read_bytes()for p in [path,*root.iterdir()]}
    ctx=load_relabel_cif_source(root,path,**kw);report=ctx.observation
    block=gemmi.cif.read_file(str(path))[0];atoms=block.get_mmcif_category('_atom_site.')
    assert ctx.document_bytes==path.read_bytes()
    assert ctx.positions_angstrom[0][0]==float(atoms['Cartn_x'][0])
    assert ctx.u_cart_angstrom_squared[0][0]==float(block.get_mmcif_category('_atom_site_anisotrop.')['U[1][1]'][0])
    assert report['original_identities'][0]['residue_code']=='LONG1'
    assert report['attached_components'][0]['component']=='LONG1'
    assert ctx.frame.context_sha256==report['report_sha256']!=kw['expected_receipt_sha256']
    assert report['maximum_working_precision_errors']['coordinate']>0
    assert not report['runtime_authority'] and not report['annotation_coverage_validated']
    assert str(tmp_path) not in json.dumps(report)
    options=dict(source_labels=ctx.frame.source_labels,context_sha256=ctx.frame.context_sha256)
    moved=ctx.frame.to_representatives(ctx.positions_angstrom,**options)
    restored=ctx.frame.to_source(moved,atom_labels=ctx.frame.atom_labels,context_sha256=ctx.frame.context_sha256)
    assert max(abs(a-b)for p,q in zip(restored,ctx.positions_angstrom)for a,b in zip(p,q))<1e-12
    report['component_aliases'].clear();assert ctx.observation['component_aliases']
    with pytest.raises(FrozenInstanceError):ctx.atom_ids=()
    assert all(p.read_bytes()==b for p,b in before.items())


@pytest.mark.parametrize('damage',['source_pin','preview_pin','missing_alias','unused_alias','atom_name','cell','occupancy','B','coordinate','U','adp_mode','duplicate_id','extra_atom'])
def test_different_source_or_unexplained_working_mapping_is_refused(tmp_path,damage):
    root,path,kw=fixture(tmp_path)
    if damage=='source_pin':kw['expected_model_sha256']='0'*64
    elif damage=='preview_pin':kw['expected_receipt_sha256']='0'*64
    elif damage=='missing_alias':kw['component_aliases']={}
    elif damage=='unused_alias':kw['component_aliases']['EXTRA']='EXT'
    else:
        def mutate(doc):
            b=doc[0]
            if damage=='cell':b.set_pair('_cell.length_a','31');return
            if damage=='adp_mode':b.find_mmcif_category('_atom_site_anisotrop.').erase();return
            cat='_atom_site_anisotrop.'if damage=='U'else'_atom_site.';t=b.get_mmcif_category(cat)
            fields={'atom_name':('label_atom_id','ZZ'),'occupancy':('occupancy','0.5'),'B':('B_iso_or_equiv','200'),
                'coordinate':('Cartn_x','200'),'U':('U[1][1]','0.9'),'duplicate_id':('id',t['id'][1])}
            if damage=='extra_atom':
                for k,v in t.items():v.append(v[0]if k!='id'else'new')
            else:k,v=fields[damage];t[k][0]=v
            b.set_mmcif_category(cat,t)
        kw['expected_model_sha256']=edit(path,mutate)
    with pytest.raises(ValueError):load_relabel_cif_source(root,path,**kw)


@pytest.mark.parametrize('damage',['second_coordinate','noncomponent_extra','duplicate_component','missing_component_id'])
def test_unique_coordinate_block_and_explicit_component_attachments(tmp_path,damage):
    root,path,kw=fixture(tmp_path)
    def mutate(doc):
        if damage=='second_coordinate':
            b=doc.add_copied_block(doc[0]);b.name='second'
        else:
            b=doc.add_new_block('extra')
            if damage=='noncomponent_extra':b.set_pair('_refln.index_h','1')
            elif damage=='duplicate_component':b.set_pair('_chem_comp.id','LONG1')
            else:b.set_pair('_chem_comp.name','missing')
    kw['expected_model_sha256']=edit(path,mutate)
    with pytest.raises(ValueError):load_relabel_cif_source(root,path,**kw)


def test_raw_atom_permutation_is_explicit_without_losing_images(tmp_path):
    root,path,kw=fixture(tmp_path);before=load_relabel_cif_source(root,path,**kw)
    def mutate(doc):
        b=doc[0];t=b.get_mmcif_category('_atom_site.');n=len(t['id'])
        # Reverse atoms within each residue, preserving contiguous residue groups.
        groups=[]
        for i in range(n):
            k=tuple(t[x][i]for x in ('auth_asym_id','auth_seq_id'))
            if not groups or groups[-1][0]!=k:groups.append((k,[]))
            groups[-1][1].append(i)
        order=[i for _,indices in groups for i in reversed(indices)]
        b.set_mmcif_category('_atom_site.',{k:[v[i]for i in order]for k,v in t.items()})
    kw['expected_model_sha256']=edit(path,mutate);after=load_relabel_cif_source(root,path,**kw)
    assert set(after.working_atom_indices)==set(before.working_atom_indices)
    assert after.working_atom_indices!=before.working_atom_indices
    old={i:(p,u,image)for i,p,u,image in zip(before.atom_ids,before.positions_angstrom,before.u_cart_angstrom_squared,before.frame.images)}
    assert old=={i:(p,u,image)for i,p,u,image in zip(after.atom_ids,after.positions_angstrom,after.u_cart_angstrom_squared,after.frame.images)}


@pytest.mark.parametrize('value',[True,-1,float('nan'),float('inf')])
def test_precision_cannot_be_missing_nonfinite_or_boolean(tmp_path,value):
    root,path,kw=fixture(tmp_path);kw['max_coordinate_component_error_angstrom']=value
    with pytest.raises(ValueError,match='precision'):load_relabel_cif_source(root,path,**kw)


def test_relocation_and_read_race_preserve_original_binding(tmp_path,monkeypatch):
    original=tmp_path/'old';original.mkdir();root,path,kw=fixture(original)
    expected=load_relabel_cif_source(root,path,**kw).observation
    moved=tmp_path/'new';shutil.move(original,moved);assert not original.exists()
    root=moved/root.relative_to(original);path=moved/path.relative_to(original)
    assert load_relabel_cif_source(root,path,**kw).observation==expected
    import nasolve.topostitch_cif_source as module
    parse=module._coordinate_block
    def drift(data):
        result=parse(data);path.write_bytes(path.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'_coordinate_block',drift)
    with pytest.raises(ValueError,match='changed during'):load_relabel_cif_source(root,path,**kw)


def test_isotropic_forest_source_keeps_absent_tensors_and_empty_aliases(tmp_path):
    root,digest,_=saved_scattering_packet(tmp_path,forest=True)
    st=gemmi.read_pdb_string((root/'source.pdb').read_text())
    path=tmp_path/'forest-original.cif';st.make_mmcif_document().write_file(str(path))
    ctx=load_relabel_cif_source(root,path,expected_receipt_sha256=digest,
        expected_model_sha256=sha256(path.read_bytes()).hexdigest(),component_aliases={},
        max_coordinate_component_error_angstrom=1e-12,max_u_component_error_angstrom_squared=0.,
        max_b_error_angstrom_squared=1e-5,max_occupancy_error=1e-5)
    assert all(u is None for u in ctx.u_cart_angstrom_squared)
    assert ctx.observation['anisotropic_atom_count']==0
    assert not ctx.observation['component_aliases'] and not ctx.observation['attached_components']


def test_declared_symmetry_table_cannot_contradict_the_bound_crystal(tmp_path):
    root,path,kw=fixture(tmp_path)
    def mutate(doc):
        doc[0].set_mmcif_category('_space_group_symop.',{'id':['1'],'operation_xyz':['x,y,z']})
    kw['expected_model_sha256']=edit(path,mutate)
    with pytest.raises(ValueError,match='crystal operations'):
        load_relabel_cif_source(root,path,**kw)
