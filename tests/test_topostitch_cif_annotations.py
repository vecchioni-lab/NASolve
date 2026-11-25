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


def annotation_proposal_fixture(tmp_path):
    from nasolve.topostitch_cif_annotations import _rows
    from nasolve.topostitch_registration import _fingerprint
    root,model,kw,owner=fixture(tmp_path)
    def incomplete(doc):
        atoms=doc[0].get_mmcif_category('_atom_site.')
        atoms['label_entity_id']=[None]*len(atoms['id'])
        doc[0].set_mmcif_category('_atom_site.',atoms)
        table=doc[0].get_mmcif_category('_struct_conn.')
        table.pop('ptnr1_symmetry');table.pop('ptnr2_symmetry')
        table['conn_type_id'][0]='covale'
        for values in table.values():values.append(values[0])
        table['id'][1]='unreviewed';table['conn_type_id'][1]='unknown_kind'
        doc[0].set_mmcif_category('_struct_conn.',table)
    kw['expected_model_sha256']=edit(model,incomplete)
    row=_rows(gemmi.cif.read_file(str(model))[0],'_struct_conn.')[0]
    evidence={}
    for name in ('images','chemistry'):
        path=tmp_path/(name+'.json');path.write_text('{"scope":"controlled test evidence"}')
        evidence[name]=dict(path=path,sha256=sha256(path.read_bytes()).hexdigest())
    changes=[dict(connection_id='contact',expected_row_sha256=_fingerprint(row),
        fields=dict(conn_type_id='hydrog',ptnr1_symmetry='2_555',ptnr2_symmetry='1_555'),
        evidence=dict(conn_type_id=['chemistry'],ptnr1_symmetry=['images'],ptnr2_symmetry=['images']))]
    args=dict(expected_model_sha256=kw['expected_model_sha256'],changes=changes,evidence=evidence,
        cedar_source=kw['cedar_source'],expected_image_owner_sha256=kw['expected_image_owner_sha256'])
    return root,model,kw,args


def propose_annotations(model,kw):
    from nasolve.topostitch_cif_annotations import prepare_connection_annotation_proposal
    return prepare_connection_annotation_proposal(model,**kw)


def test_annotation_proposal_preserves_incomplete_source_without_approving_export(tmp_path):
    root,model,source_kw,args=annotation_proposal_fixture(tmp_path)
    paths=[model,*(x['path']for x in args['evidence'].values())];before={p:p.read_bytes()for p in paths}
    r=propose_annotations(model,args)
    assert r['kind']=='topostitch-connection-annotation-proposal' and r['proposed_row_count']==1
    assert r['source_row_count']==2 and r['proposed_added_columns']==['ptnr1_symmetry','ptnr2_symmetry']
    changed,retained=r['connections']
    assert changed['original_fields']['conn_type_id']=='covale' and changed['proposed_fields']['conn_type_id']=='hydrog'
    assert 'ptnr1_symmetry' not in changed['original_fields']
    assert changed['proposed_fields']['ptnr1_symmetry']=='2_555'
    assert changed['original_fields']['details']==changed['proposed_fields']['details']
    assert retained['original_fields']==retained['proposed_fields'] and not retained['field_changes']
    assert retained['original_fields']['conn_type_id']=='unknown_kind'
    assert set(changed['field_changes'])==set(args['changes'][0]['fields'])
    assert changed['field_changes']['conn_type_id']['evidence_ids']==['chemistry']
    assert not any(r[k] for k in ('applied','coordinates_written','evidence_semantics_validated',
        'endpoint_identity_validated','chemical_semantics_validated','native_restart_qualified','runtime_authority'))
    assert str(tmp_path)not in json.dumps(r) and json.loads(json.dumps(r))==r
    assert all(p.read_bytes()==b for p,b in before.items())
    with pytest.raises(ValueError,match='complete original CIF site label'):
        observe(root,model,source_kw)


@pytest.mark.parametrize('defect,reason',[
    ('source_hash','source'),('row_hash','row'),('evidence_hash','evidence'),
    ('missing_evidence','evidence'),('unknown_evidence','evidence'),('empty_evidence','evidence'),
    ('identity_edit','field'),('unknown_image','image'),('unknown_type','type'),
    ('duplicate_change','Duplicate'),('unknown_row','connection'),('duplicate_source','Duplicate')])
def test_annotation_proposal_refuses_unbound_or_out_of_scope_changes(tmp_path,defect,reason):
    root,model,source_kw,args=annotation_proposal_fixture(tmp_path)
    c=args['changes'][0]
    if defect=='source_hash':args['expected_model_sha256']='0'*64
    elif defect=='row_hash':c['expected_row_sha256']='0'*64
    elif defect=='evidence_hash':args['evidence']['images']['sha256']='0'*64
    elif defect=='missing_evidence':c['evidence'].pop('conn_type_id')
    elif defect=='unknown_evidence':c['evidence']['conn_type_id']=['absent']
    elif defect=='empty_evidence':c['evidence']['conn_type_id']=[]
    elif defect=='identity_edit':c['fields']['ptnr1_label_asym_id']='new';c['evidence']['ptnr1_label_asym_id']=['images']
    elif defect=='unknown_image':c['fields']['ptnr1_symmetry']='999_555'
    elif defect=='unknown_type':c['fields']['conn_type_id']='invented'
    elif defect=='duplicate_change':args['changes'].append(dict(c))
    elif defect=='unknown_row':c['connection_id']='absent'
    elif defect=='duplicate_source':
        def duplicate(doc):
            t=doc[0].get_mmcif_category('_struct_conn.');t['id'][1]=t['id'][0];doc[0].set_mmcif_category('_struct_conn.',t)
        args['expected_model_sha256']=edit(model,duplicate)
    with pytest.raises(ValueError,match=reason):propose_annotations(model,args)


@pytest.mark.parametrize('target',['source','evidence'])
def test_annotation_proposal_refuses_late_input_drift(tmp_path,monkeypatch,target):
    from contextlib import contextmanager
    from nasolve import topostitch_cif_annotations as module
    root,model,source_kw,args=annotation_proposal_fixture(tmp_path)
    original=module._image_owner
    @contextmanager
    def changing(*a,**kw):
        with original(*a,**kw) as decode:
            def mutate(code,operations):
                path=model if target=='source' else args['evidence']['images']['path']
                path.write_bytes(path.read_bytes()+b'\n')
                return decode(code,operations)
            yield mutate
    monkeypatch.setattr(module,'_image_owner',changing)
    with pytest.raises(ValueError,match='changed'):propose_annotations(model,args)


def reopen_annotation_proposal(path, model, args, pin=None):
    from nasolve.topostitch_cif_annotations import load_connection_annotation_proposal
    return load_connection_annotation_proposal(path, model,
        expected_proposal_sha256=pin or sha256(path.read_bytes()).hexdigest(), **args)


def test_annotation_proposal_cold_replay(tmp_path):
    root, model, kw, args = annotation_proposal_fixture(tmp_path)
    expected = propose_annotations(model, args)
    path = tmp_path/'proposal.json'
    path.write_text(json.dumps(expected, indent=2)+'\n')
    assert reopen_annotation_proposal(path, model, args) == expected
    assert not expected['applied'] and not expected['scientific_acceptance']


@pytest.mark.parametrize('defect', ['raw_hash', 'rehash', 'boolean_integer',
    'duplicate_key', 'nonfinite', 'different_request', 'source', 'evidence'])
def test_annotation_proposal_replay_refuses_changed_inputs(tmp_path, defect):
    from nasolve.topostitch_registration import _fingerprint
    root, model, kw, args = annotation_proposal_fixture(tmp_path)
    report = propose_annotations(model, args)
    path = tmp_path/'proposal.json'; path.write_text(json.dumps(report))
    pin = sha256(path.read_bytes()).hexdigest()
    if defect == 'raw_hash':
        path.write_bytes(path.read_bytes()+b'\n')
    elif defect in ('rehash', 'boolean_integer'):
        report['applied'] = True if defect == 'rehash' else 0
        report.pop('report_sha256'); report['report_sha256'] = _fingerprint(report)
        path.write_text(json.dumps(report)); pin = None
    elif defect == 'duplicate_key':
        path.write_text('{"applied":false,'+path.read_text()[1:]); pin = None
    elif defect == 'nonfinite':
        path.write_text(path.read_text().replace('"applied": false', '"applied": NaN')); pin = None
    elif defect == 'different_request':
        args['changes'][0]['fields']['ptnr1_symmetry'] = '1_555'
    elif defect == 'source':
        model.write_bytes(model.read_bytes()+b'\n')
    elif defect == 'evidence':
        args['evidence']['images']['path'].write_text('changed evidence')
    with pytest.raises(ValueError):
        reopen_annotation_proposal(path, model, args, pin)


def test_annotation_proposal_replay_rechecks_saved_bytes(tmp_path, monkeypatch):
    from nasolve import topostitch_cif_annotations as module
    root, model, kw, args = annotation_proposal_fixture(tmp_path)
    path = tmp_path/'proposal.json'; path.write_text(json.dumps(propose_annotations(model, args)))
    original = module.prepare_connection_annotation_proposal
    def changing(*a, **kw):
        result = original(*a, **kw)
        path.write_bytes(path.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(module, 'prepare_connection_annotation_proposal', changing)
    with pytest.raises(ValueError, match='changed during replay'):
        reopen_annotation_proposal(path, model, args)
