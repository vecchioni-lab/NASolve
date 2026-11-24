"""All deposited connection kinds retain explicit original atom/image lineage."""
from hashlib import sha256
import json
import shutil

import pytest
gemmi = pytest.importorskip('gemmi')
from tests.test_topostitch_cif_paths import labelled
from tests.test_topostitch_cif_source import edit


def fixture(tmp_path):
    root, model, kw = labelled(tmp_path)
    src = tmp_path/'owner'/'nasolve'; src.mkdir(parents=True)
    names = ('cif_attachment_native','cif_native_validation','cif_candidate_usability',
        'cif_native_nonbonded','cif_native_monomers','cif_fixed_geometry','phenix_runtime',
        'cif_captured_mixed_gradients','campaign_process','cif_selected_environment')
    for name in names: (src/(name+'.py')).write_text('')
    owner = src/'cif_deposition_links.py'
    # Contract fake, not a second production symmetry-code parser.
    owner.write_text('def resolve_deposition_image(code, operations):\n'
                     '    return operations.get({"1_555":"1", "2_555":"2"}.get(code))\n')
    kw.update(cedar_source=src.parent, expected_image_owner_sha256=sha256(owner.read_bytes()).hexdigest())
    def add(doc):
        ops=list(gemmi.read_pdb_string((root/'source.pdb').read_text()).find_spacegroup().operations())
        doc[0].set_mmcif_category('_space_group_symop.', {'id':[str(i+1)for i in range(len(ops))], 'operation_xyz':[op.triplet()for op in ops]})
        table=doc[0].get_mmcif_category('_atom_site.')
        packet=json.loads((root/'preview.json').read_bytes())['observation']
        changed=set(packet['graph_relabeling']['changed_node_ids'])
        nodes=packet['registered_graph']['nodes']
        moved=next(n['atom_indices'][0] for n in nodes if n['node_id'] in changed)
        other=next(n['atom_indices'][0] for n in nodes if n['node_id'] not in changed)
        row={'id':'contact','conn_type_id':'hydrog','details':'retain original note',
             'ptnr1_symmetry':'2_555','ptnr2_symmetry':'1_555'}
        for side,index in ((1,moved),(2,other)):
            for field in ('label_asym_id','label_seq_id','label_comp_id','label_atom_id',
                          'auth_asym_id','auth_seq_id'):
                row[f'ptnr{side}_{field}']=table[field][index]
            row[f'pdbx_ptnr{side}_label_alt_id']=False
        doc[0].set_mmcif_category('_struct_conn.',{k:[v]for k,v in row.items()})
    kw['expected_model_sha256']=edit(model,add)
    return root,model,kw,owner


def observe(root,model,kw):
    from nasolve.topostitch_cif_annotations import observe_relabel_cif_connections
    return observe_relabel_cif_connections(root,model,**kw)


def change(model,kw,fn):
    def editrow(doc):
        t=doc[0].get_mmcif_category('_struct_conn.');fn(t)
        doc[0].set_mmcif_category('_struct_conn.',t)
    kw['expected_model_sha256']=edit(model,editrow)


def test_nonbackbone_connection_survives_recut_without_writing(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    before={p:p.read_bytes()for p in [model,owner,*root.iterdir()]}
    r=observe(root,model,kw);row=r['connections'][0]
    assert r['source_row_count']==r['transported_row_count']==1 and r['unresolved_row_count']==0
    assert row['raw_fields']['conn_type_id']=='hydrog' and row['raw_fields']['details']=='retain original note'
    assert row['endpoints'][0]['original_operator_xyz'] != row['endpoints'][0]['representative_operator_xyz']
    assert row['maximum_endpoint_error_angstrom']<1e-10
    assert abs(row['original_distance_angstrom']-row['representative_distance_angstrom'])<1e-10
    assert all(e['original_atom_id']and e['proposed_path_position'] for e in row['endpoints'])
    assert not r['coordinates_written'] and not r['runtime_authority'] and not r['chemical_connectivity_validated']
    assert str(tmp_path)not in json.dumps(r)
    assert all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('defect', ['missing_symmetry','unknown_symmetry','wrong_author','unknown_atom',
    'third_partner','missing_atom_name','conflicting_alt','unknown_auth_alt'])
def test_unresolved_rows_are_kept_with_reasons(tmp_path,defect):
    root,model,kw,owner=fixture(tmp_path)
    def damage(t):
        if defect=='missing_symmetry':t['ptnr1_symmetry'][0]=None
        elif defect=='unknown_symmetry':t['ptnr1_symmetry'][0]='999_555'
        elif defect=='wrong_author':t['ptnr1_auth_asym_id'][0]='WRONG'
        elif defect=='unknown_atom':t['ptnr1_label_atom_id'][0]='NO_SUCH_ATOM'
        elif defect=='third_partner':t['pdbx_ptnr3_label_atom_id']=['P']
        elif defect=='missing_atom_name':t['ptnr1_label_atom_id'][0]=None
        elif defect=='conflicting_alt':t['pdbx_ptnr1_label_alt_id'][0]='A'
        elif defect=='unknown_auth_alt':t['pdbx_ptnr1_auth_alt_id']=['A']
    change(model,kw,damage)
    r=observe(root,model,kw)
    assert r['source_row_count']==r['unresolved_row_count']==1 and not r['transported_row_count']
    assert r['connections'][0]['reasons'] and r['connections'][0]['raw_fields']['id']=='contact'


def test_unknown_types_and_duplicate_row_ids_are_never_discarded(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    def duplicate(t):
        t['conn_type_id'][0]='unrecognized_kind'
        for values in t.values():values.append(values[0])
    change(model,kw,duplicate)
    r=observe(root,model,kw)
    assert len(r['connections'])==2 and r['source_row_count']==2
    assert r['duplicate_connection_ids']==['contact']
    assert r['unresolved_row_count']==2
    assert [x['source_row_number']for x in r['connections']]==[1,2]


def test_no_connection_table_is_not_connectivity_approval(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    kw['expected_model_sha256']=edit(model,lambda d:d[0].find_mmcif_category('_struct_conn.').erase())
    r=observe(root,model,kw)
    assert r['source_row_count']==0 and not r['connection_category_present']
    assert not r['chemical_connectivity_validated'] and not r['complete_construct_connectivity_validated']


def test_conflicting_operation_ids_are_visible_not_arbitrarily_chosen(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    def damage(d):
        t=d[0].get_mmcif_category('_space_group_symop.')
        t['id'][1]=t['id'][0];d[0].set_mmcif_category('_space_group_symop.',t)
    kw['expected_model_sha256']=edit(model,damage)
    r=observe(root,model,kw)
    assert r['unresolved_row_count']==1 and r['operation_table_issues']


def test_owner_pin_and_late_change_refuse(tmp_path,monkeypatch):
    root,model,kw,owner=fixture(tmp_path)
    bad=dict(kw,expected_image_owner_sha256='0'*64)
    with pytest.raises(ValueError,match='owner'):observe(root,model,bad)
    import nasolve.topostitch_cif_annotations as module
    original=module._endpoint
    def drift(*args,**kwargs):
        result=original(*args,**kwargs);owner.write_bytes(owner.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'_endpoint',drift)
    with pytest.raises(ValueError,match='changed'):observe(root,model,kw)


def test_observation_relocates_without_original_paths(tmp_path):
    old=tmp_path/'old';old.mkdir();root,model,kw,owner=fixture(old)
    expected=observe(root,model,kw)
    moved=tmp_path/'moved';shutil.move(old,moved);assert not old.exists()
    kw['cedar_source']=moved/kw['cedar_source'].relative_to(old)
    assert observe(moved/root.relative_to(old),moved/model.relative_to(old),kw)==expected


def test_unknown_connection_type_can_preserve_known_endpoints(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    change(model,kw,lambda t:t['conn_type_id'].__setitem__(0,'future_type'))
    r=observe(root,model,kw)
    assert r['transported_row_count']==1
    assert r['connections'][0]['raw_fields']['conn_type_id']=='future_type'
    assert not r['chemical_connectivity_validated']


def test_ambiguous_and_incomplete_alternate_identity_is_never_first_match():
    from nasolve.topostitch_cif_annotations import _endpoint
    atom=dict(label_asym_id='X',label_comp_id='DT',label_atom_id='P',label_seq_id='1')
    row={f'ptnr1_{k}':v for k,v in atom.items()}
    a=dict(atom,label_alt_id='A');b=dict(atom,label_alt_id='B')
    assert _endpoint(row,1,[a,b])[0] is None
    assert _endpoint(row,1,[a])[0] is None
    row['pdbx_ptnr1_label_alt_id']='A'
    assert _endpoint(row,1,[a,b])==(0,[])
    row['ptnr1_label_alt_id']='B'
    assert _endpoint(row,1,[a,b])[0] is None


def test_unregistered_atom_remains_at_identity_image(tmp_path):
    from tests.test_topostitch_cif_paths import partial_labelled
    root,model,kw,owner=fixture(tmp_path)
    other=tmp_path/'partial';other.mkdir()
    partial,original,binding=partial_labelled(other)
    from nasolve.topostitch_cif_source import observe_relabel_cif_paths
    unregistered=observe_relabel_cif_paths(partial,original,**binding)['unregistered_original_atom_ids']
    def annotate(d):
        atoms=d[0].get_mmcif_category('_atom_site.')
        i=atoms['id'].index(unregistered[0])
        row={'id':'context','conn_type_id':'hydrog','ptnr1_symmetry':'1_555','ptnr2_symmetry':'1_555'}
        for side,j in ((1,i),(2,0)):
            for key in ('label_asym_id','label_seq_id','label_comp_id','label_atom_id'):
                row[f'ptnr{side}_{key}']=atoms[key][j]
        d[0].set_mmcif_category('_struct_conn.',{k:[v]for k,v in row.items()})
        d[0].set_mmcif_category('_space_group_symop.',gemmi.cif.read_file(str(model))[0].get_mmcif_category('_space_group_symop.'))
    binding['expected_model_sha256']=edit(original,annotate)
    binding.update({k:kw[k]for k in ('cedar_source','expected_image_owner_sha256')})
    r=observe(partial,original,binding);e=r['connections'][0]['endpoints'][0]
    assert r['transported_row_count']==1
    assert e['registered_node_id'] is None and e['proposed_path_position'] is None
    assert e['representative_image_xyz']=='x,y,z'


@pytest.mark.parametrize('field,annotation',[('label_alt_id','pdbx_ptnr1_label_alt_id'),('pdbx_PDB_ins_code','pdbx_ptnr1_PDB_ins_code')])
@pytest.mark.parametrize('unknown',[None,'absent'])
def test_declared_blank_is_not_unknown_or_absent(field,annotation,unknown):
    from nasolve.topostitch_cif_annotations import _endpoint
    atom=dict(label_asym_id='X',label_comp_id='DT',label_atom_id='P',label_seq_id='1')
    row={f'ptnr1_{k}':v for k,v in atom.items()};row[annotation]=False
    if unknown!='absent':atom[field]=unknown
    assert _endpoint(row,1,[atom])[0] is None
    atom[field]=False
    assert _endpoint(row,1,[atom])==(0,[])


def test_polymer_endpoint_needs_explicit_residue_locator_even_when_unique():
    from nasolve.topostitch_cif_annotations import _endpoint
    atom=dict(label_asym_id='X',label_comp_id='DT',label_atom_id='P',label_seq_id='42')
    row={f'ptnr1_{k}':v for k,v in atom.items()if k!='label_seq_id'}
    assert _endpoint(row,1,[atom])[0] is None
    row['ptnr1_label_seq_id']='42'
    assert _endpoint(row,1,[atom])==(0,[])
