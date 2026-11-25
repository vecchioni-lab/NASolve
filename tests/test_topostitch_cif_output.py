"""Whole-asym drafts retain scientific metadata or refuse unsupported scope."""
from hashlib import sha256
import json
import shutil
import pytest
import gemmi
from tests.test_topostitch_cif_assembly import fixture as assembly_fixture
from tests.test_topostitch_cif_source import edit
from nasolve.topostitch_registration import _fingerprint
from nasolve.topostitch_cif_annotations import _rows


def fixture(tmp_path, *, mixed=False):
    root, model, kw, owner = assembly_fixture(tmp_path)
    # The shared polymer fixture renumbers label positions. Carry those labels
    # into its contact row; this draft test requires a genuinely resolved row.
    def repair_labels(doc):
        b=doc[0]; atoms=_rows(b,'_atom_site.'); rows=_rows(b,'_struct_conn.')
        for r in rows:
            for side in (1,2):
                found=[a for a in atoms if a['auth_asym_id']==r[f'ptnr{side}_auth_asym_id']
                    and a['auth_seq_id']==r[f'ptnr{side}_auth_seq_id']
                    and a['label_atom_id']==r[f'ptnr{side}_label_atom_id']]
                assert len(found)==1
                r[f'ptnr{side}_label_seq_id']=found[0]['label_seq_id']
        b.set_mmcif_category('_struct_conn.',{k:[r[k]for r in rows]for k in rows[0]})
    kw['expected_model_sha256']=edit(model,repair_labels)
    # Explicit finite decoder fake for this synthetic P43 fixture, including
    # its inverse screw's -1 c translation. Actual-file checks use pinned Cedar.
    ops=gemmi.make_structure_from_block(gemmi.cif.read_file(str(model))[0]).find_spacegroup().operations()
    codes={}
    for i,op in enumerate(ops,1):
        codes[str(i)+'_555']=op.triplet()
        moved=gemmi.Op(op.triplet()); moved.tran=[op.tran[0],op.tran[1],op.tran[2]-op.DEN]
        codes[str(i)+'_554']=moved.triplet()
    owner.write_text(owner.read_text()+'\nimport gemmi\n_CODES='+repr(codes)+'\ndef resolve_deposition_image(code, operations):\n    return gemmi.Op(_CODES[code]) if code in _CODES else None\n')
    kw['expected_deposition_owner_sha256']=sha256(owner.read_bytes()).hexdigest()
    if not mixed:
        from nasolve.topostitch_recut_bundle import build_relabel_preview
        request = json.loads((root/'proposal.json').read_text())
        observation = json.loads((root/'preview.json').read_text())['observation']
        image = request['node_images'][0]['operator_xyz']
        request['node_images'] = [dict(node_id=n['node_id'], operator_xyz=image)
                                 for n in observation['registered_graph']['nodes']]
        proposal = tmp_path/'whole-request.json'; proposal.write_text(json.dumps(request))
        new = tmp_path/'whole-preview'
        build_relabel_preview(root/'source.pdb', root/'discovery.json',
            registration_path=root/'registration.json', proposal_path=proposal, output_directory=new)
        root = new; kw['expected_receipt_sha256'] = sha256((root/'preview.json').read_bytes()).hexdigest()
    kw.update(max_rotation_component_error=1e-8,
              max_translation_component_error_angstrom=1e-6,
              max_assembly_position_error_angstrom=1e-5)
    return root, model, kw, owner


def policy(model):
    b=gemmi.cif.read_file(str(model))[0]
    return {c:_fingerprint(_rows(b,c)) for c in b.get_mmcif_category_names()}


def prepare(root, model, kw, reviewed=None):
    from nasolve.topostitch_cif_output import prepare_whole_asym_cif
    return prepare_whole_asym_cif(root, model, reviewed_categories=policy(model) if reviewed is None else reviewed,
        tls_policy='preserve_raw_no_restart', center_policy='unit_occupancy_present_polymer_mass', **kw)


def test_whole_asym_draft_retains_categories_precision_and_attached_definition(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    before={p:p.read_bytes()for p in [model,owner,*root.iterdir()]}
    data,report=prepare(root,model,kw)
    old=gemmi.cif.read_file(str(model)); new=gemmi.cif.read_string(data.decode('ascii'))
    assert len(new)==len(old)
    assert new[1].as_string()==old[1].as_string()
    assert set(new[0].get_mmcif_category_names())==set(old[0].get_mmcif_category_names())
    a,b=old[0].get_mmcif_category('_atom_site.'),new[0].get_mmcif_category('_atom_site.')
    for key in a:
        if key not in ('Cartn_x','Cartn_y','Cartn_z'):assert a[key]==b[key]
    assert a['Cartn_x']!=b['Cartn_x']
    assert report['atom_count']==84 and report['category_readback_exact']
    assert report['deposited_adps_transported'] and not report['tls_added_to_deposited_adps']
    assert not report['native_restart_qualified'] and not report['scientific_acceptance']
    assert not report['file_written'] and all(p.read_bytes()==v for p,v in before.items())


def test_fragmented_asym_cannot_be_emitted_by_whole_asym_draft(tmp_path):
    root,model,kw,_=fixture(tmp_path,mixed=True)
    with pytest.raises(ValueError,match='whole original asym'):prepare(root,model,kw)


def test_source_bound_category_review_cannot_skip_or_silently_accept_new_fields(tmp_path):
    root,model,kw,_=fixture(tmp_path);reviewed=policy(model)
    reviewed.pop('_cell.')
    with pytest.raises(ValueError,match='category review'):prepare(root,model,kw,reviewed)
    reviewed=policy(model)
    kw['expected_model_sha256']=edit(model,lambda d:d[0].set_pair('_new_category.Cartn_x','12.3'))
    with pytest.raises(ValueError,match='category review'):prepare(root,model,kw,reviewed)


def test_populated_uncertainties_are_not_silently_copied(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def add(doc):
        t=doc[0].get_mmcif_category('_atom_site.'); t['Cartn_x_esd']=['0.1']*len(t['id'])
        doc[0].set_mmcif_category('_atom_site.',t)
    kw['expected_model_sha256']=edit(model,add)
    with pytest.raises(ValueError,match='uncertainty|coordinate'):prepare(root,model,kw)


def test_scalar_categories_stay_scalar_without_duplicate_category(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def add(doc):
        doc[0].set_pair('_refine.entry_id', "'test structure'")
        doc[0].set_pair('_refine.ls_R_factor_R_free', '0.27')
    kw['expected_model_sha256']=edit(model,add)
    data,report=prepare(root,model,kw);b=gemmi.cif.read_string(data.decode('ascii'))[0]
    assert b.find_pair('_refine.entry_id') is not None
    assert b.find_value('_refine.ls_R_factor_R_free')=='0.27'
    assert data.count(b'_refine.ls_R_factor_R_free')==1


def test_assembly_draft_preserves_each_physical_instance_in_both_namespaces(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    # Include a lattice translation: the order H G^-1 is then consequential.
    def shifted(doc):
        t=doc[0].get_mmcif_category('_pdbx_struct_oper_list.')
        t['vector[1]'][1]='30'
        doc[0].set_mmcif_category('_pdbx_struct_oper_list.',t)
    kw['expected_model_sha256']=edit(model,shifted)
    data,report=prepare(root,model,kw);old=gemmi.cif.read_file(str(model))[0]
    new=gemmi.cif.read_string(data.decode('ascii'))[0]
    def apply(row,xyz):
        return [sum(float(row[f'matrix[{i+1}][{j+1}]'])*xyz[j]for j in range(3))+float(row[f'vector[{i+1}]'])for i in range(3)]
    a={r['id']:r for r in _rows(old,'_atom_site.')};b={r['id']:r for r in _rows(new,'_atom_site.')}
    for item in report['assembly_generator_lineage']:
        suffix=''if item['namespace']=='curated'else'_depositor_info'
        category='_pdbx_struct_oper_list'+suffix+'.'
        before=next(r for r in _rows(old,category)if r['id']==item['source_operator_id'])
        after=next(r for r in _rows(new,category)if r['id']==item['output_operator_id'])
        for key,r in a.items():
            if r['label_asym_id']not in item['original_label_asym_ids']:continue
            p=apply(before,[float(r['Cartn_'+v])for v in 'xyz'])
            q=apply(after,[float(b[key]['Cartn_'+v])for v in 'xyz'])
            assert p==pytest.approx(q,abs=1e-12)


def test_supplied_polymer_center_is_updated_in_scalar_form(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def center(doc):
        atoms=_rows(doc[0],'_atom_site.');weights=[gemmi.Element(a['type_symbol']).weight for a in atoms]
        for axis in 'xyz':
            value=sum(float(a['Cartn_'+axis])*w for a,w in zip(atoms,weights))/sum(weights)
            doc[0].set_pair('_struct.pdbx_center_of_mass_'+axis,format(value,'.17g'))
    kw['expected_model_sha256']=edit(model,center)
    data,report=prepare(root,model,kw);b=gemmi.cif.read_string(data.decode('ascii'))[0]
    assert report['center_of_mass']['source_recomputed']!=report['center_of_mass']['representative_recomputed']
    for axis,v in zip('xyz',report['center_of_mass']['representative_recomputed']):
        tag='_struct.pdbx_center_of_mass_'+axis
        assert b.find_pair(tag) is not None and float(b.find_value(tag))==v
        assert data.count(tag.encode())==1
    kw['expected_model_sha256']=edit(model,lambda d:d[0].set_pair('_struct.pdbx_center_of_mass_x','999'))
    with pytest.raises(ValueError,match='mass convention'):prepare(root,model,kw)


def test_draft_relocation_and_source_drift(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old)
    expected=prepare(root,model,kw)
    relative=[p.relative_to(old)for p in(root,model,kw['cedar_source'])]
    new=tmp_path/'moved';shutil.move(old,new);root,model,kw['cedar_source']=[new/p for p in relative]
    assert not old.exists() and prepare(root,model,kw)==expected
    import nasolve.topostitch_cif_output as module
    original=module.observe_relabel_cif_assemblies
    def drift(*a,**k):
        result=original(*a,**k);model.write_bytes(model.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'observe_relabel_cif_assemblies',drift)
    with pytest.raises(ValueError,match='changed|binding'):prepare(root,model,kw)


def test_unresolved_generator_is_refused_even_with_reviewed_category_hash(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def damage(doc):
        t=doc[0].get_mmcif_category('_pdbx_struct_assembly_gen.')
        t['oper_expression'][0]='missing';doc[0].set_mmcif_category('_pdbx_struct_assembly_gen.',t)
    kw['expected_model_sha256']=edit(model,damage)
    with pytest.raises(ValueError,match='Unresolved assembly'):prepare(root,model,kw)



@pytest.mark.parametrize('field,value', [('all_chains','N'),('at_unit_matrix','N'),
    ('chain_id_list','WRONG'),('symmetry_operation','-x,-y,z+1/2')])
def test_conflicting_generator_metadata_is_not_silently_corrected(tmp_path,field,value):
    root,model,kw,_=fixture(tmp_path)
    def damage(doc):
        category='_pdbx_struct_assembly_gen_depositor_info.'
        t=doc[0].get_mmcif_category(category);t[field]=[None]*len(t['assembly_id']);t[field][0]=value
        doc[0].set_mmcif_category(category,t)
    kw['expected_model_sha256']=edit(model,damage)
    with pytest.raises(ValueError,match='Conflicting original generator'):prepare(root,model,kw)
