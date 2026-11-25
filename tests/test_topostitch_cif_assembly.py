"""Assembly operator IDs are category-scoped; Cartesian values own the image."""
from hashlib import sha256
import json, math, shutil
import pytest
from tests.test_topostitch_cif_polymer import fixture as polymer_fixture
from tests.test_topostitch_cif_source import edit
from nasolve.topostitch_transport import crystallographic_image


def fixture(tmp_path):
    import gemmi
    root,model,kw,owner=polymer_fixture(tmp_path)
    def add(doc):
        b=doc[0];s=gemmi.make_structure_from_block(b);ops=list(s.find_spacegroup().operations())
        chains=b.get_mmcif_category('_struct_asym.')['id'];operators=[]
        for i,op in enumerate(ops[:3],1):
            image=crystallographic_image(list(s.cell.parameters),s.find_spacegroup().xhm(),op.triplet())
            row=dict(id=str(i),name=f'{i}_555',type='declared assembly operation')
            row.update({f'matrix[{a+1}][{z+1}]':str(image.rotation[a][z])for a in range(3)for z in range(3)})
            row.update({f'vector[{a+1}]':str(image.translation[a])for a in range(3)})
            operators.append(row)
        for suffix in ('','_depositor_info'):
            rows=[dict(r)for r in operators]
            if suffix:
                rows[1],rows[2]=rows[2],rows[1]
                for i,row in enumerate(rows,1):row['id']=str(i);row['name']=f'{i}_555'
            b.set_mmcif_category('_pdbx_struct_oper_list'+suffix+'.',{k:[r[k]for r in rows]for k in rows[0]})
            b.set_mmcif_category('_pdbx_struct_assembly'+suffix+'.',dict(id=['assembly'],details=['author-defined'],oligomeric_count=['9']))
            b.set_mmcif_category('_pdbx_struct_assembly_gen'+suffix+'.',dict(assembly_id=['assembly']*3,oper_expression=['1','2','3'],asym_id_list=[','.join(chains)]*3))
        b.set_mmcif_category('_pdbx_struct_assembly_auth_evidence.',dict(id=['evidence'],assembly_id=['assembly'],experimental_support=['declared experiment'],details=[None]))
    kw['expected_model_sha256']=edit(model,add)
    kw.update(max_rotation_component_error=1e-8,max_translation_component_error_angstrom=1e-6,max_assembly_position_error_angstrom=1e-5)
    return root,model,kw,owner


def observe(root,model,kw):
    from nasolve.topostitch_cif_assembly import observe_relabel_cif_assemblies
    return observe_relabel_cif_assemblies(root,model,**kw)


def test_original_assembly_members_and_physical_positions_survive_recut(tmp_path):
    root,model,kw,owner=fixture(tmp_path);before={p:p.read_bytes()for p in [model,owner,*root.iterdir()]}
    r=observe(root,model,kw);ns=r['namespaces']['curated']
    assert len(ns['generators'])==3
    for g in ns['generators']:
        assert g['status']=='TRANSPORT_OBSERVED_REVIEW_REQUIRED'
        assert len(g['member_atom_ids'])==len(set(g['member_atom_ids']))==84
        assert sorted(a for p in g['partitions']for a in p['original_atom_ids'])==sorted(g['member_atom_ids'])
        assert g['maximum_position_transport_error_angstrom']<1e-10
    assert ns['operators'][1]['symmetry_matches'][0]['operator_xyz']=='-y,x,z+3/4'
    assert ns['operators'][1]['symmetry_matches'][0]['declared_operation_ids']==['2']
    assert not r['writer_authorized']and not r['coordinates_written']and not r['assembly_set_equivalence_proved']
    assert str(tmp_path)not in json.dumps(r)
    assert all(p.read_bytes()==v for p,v in before.items())


def test_depositor_operator_number_never_aliases_curated_number(tmp_path):
    root,model,kw,_=fixture(tmp_path);r=observe(root,model,kw)
    a=r['namespaces']['curated']['operators'][1];b=r['namespaces']['depositor']['operators'][1]
    assert a['raw_fields']['id']==b['raw_fields']['id']=='2'
    assert a['raw_fields']['name']==b['raw_fields']['name']=='2_555'
    assert a['symmetry_matches'][0]['operator_xyz']=='-y,x,z+3/4'
    assert b['symmetry_matches'][0]['operator_xyz']=='-x,-y,z+1/2'
    assert b['symmetry_matches'][0]['declared_operation_ids']==['3']


def test_integer_lattice_shift_is_kept_not_wrapped_away(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def shift(doc):
        t=doc[0].get_mmcif_category('_pdbx_struct_oper_list.')
        t['vector[1]'][1]='30';t['vector[2]'][1]='-60'
        doc[0].set_mmcif_category('_pdbx_struct_oper_list.',t)
    kw['expected_model_sha256']=edit(model,shift);r=observe(root,model,kw)
    m=r['namespaces']['curated']['operators'][1]['symmetry_matches'][0]
    assert m['operator_xyz']=='-y+1,x-2,z+3/4'and m['lattice_shift']==[1,-2,0]
    assert r['namespaces']['curated']['generators'][1]['maximum_position_transport_error_angstrom']<1e-10
    # The shifted assembly operation and changed representative do not commute.
    g=r['namespaces']['curated']['generators'][1]
    part=next(p for p in g['partitions']if p['representative_image_xyz']!='x,y,z')
    G=crystallographic_image(**r['crystal'],operator_xyz=part['representative_image_xyz'])
    H=crystallographic_image(**r['crystal'],operator_xyz=m['operator_xyz'])
    x=[2.,3.,4.];new=G.apply(x)
    assert math.dist(G.inverse().apply(H.apply(new)),H.apply(x))>1.


@pytest.mark.parametrize('problem',['unknown_operator','expression_product','unknown_asym','duplicate_asym','unknown_assembly','duplicate_operator','missing_matrix','inapplicable_matrix','nonfinite_matrix','noncrystal_rotation','unknown_depositor_operator'])
def test_unresolved_original_rows_stay_visible_without_transport(tmp_path,problem):
    root,model,kw,_=fixture(tmp_path)
    def damage(doc):
        b=doc[0];g=b.get_mmcif_category('_pdbx_struct_assembly_gen.');o=b.get_mmcif_category('_pdbx_struct_oper_list.')
        if problem=='unknown_operator':g['oper_expression'][1]='missing'
        elif problem=='expression_product':g['oper_expression'][1]='(1)(2)'
        elif problem=='unknown_asym':g['asym_id_list'][1]='missing'
        elif problem=='duplicate_asym':g['asym_id_list'][1]+=','+g['asym_id_list'][1].split(',')[0]
        elif problem=='unknown_assembly':g['assembly_id'][1]='missing'
        elif problem=='duplicate_operator':
            for v in o.values():v.append(v[1])
        elif problem=='missing_matrix':o['matrix[1][1]'][1]=None
        elif problem=='inapplicable_matrix':o['matrix[1][3]'][1]=False
        elif problem=='nonfinite_matrix':o['vector[1]'][1]='nan'
        elif problem=='noncrystal_rotation':
            c=math.sqrt(.5)
            for k,v in {'matrix[1][1]':c,'matrix[1][2]':-c,'matrix[2][1]':c,'matrix[2][2]':c}.items():o[k][1]=str(v)
        elif problem=='unknown_depositor_operator':
            d=b.get_mmcif_category('_pdbx_struct_oper_list_depositor_info.')
            for k in d:d[k]=d[k][:1]
            b.set_mmcif_category('_pdbx_struct_oper_list_depositor_info.',d)
        b.set_mmcif_category('_pdbx_struct_assembly_gen.',g);b.set_mmcif_category('_pdbx_struct_oper_list.',o)
    kw['expected_model_sha256']=edit(model,damage);r=observe(root,model,kw)
    ns=r['namespaces']['depositor'if problem=='unknown_depositor_operator'else'curated'];g=ns['generators'][1]
    assert g['status']=='UNRESOLVED_REVIEW'and g['issues']
    assert not g['partitions']and g['maximum_position_transport_error_angstrom']is None
    assert len(ns['generators'])==3


def test_assembly_observer_relocates_and_rejects_source_drift(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old);r=observe(root,model,kw)
    paths=[p.relative_to(old)for p in(root,model,kw['cedar_source'])];new=tmp_path/'new';shutil.move(old,new)
    root,model,kw['cedar_source']=[new/p for p in paths]
    assert not old.exists()and observe(root,model,kw)==r
    import nasolve.topostitch_cif_assembly as module
    fn=module.observe_relabel_cif_fragments
    def mutate(*a,**k):
        result=fn(*a,**k);model.write_bytes(model.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'observe_relabel_cif_fragments',mutate)
    with pytest.raises(ValueError,match='changed'):observe(root,model,kw)


@pytest.mark.parametrize('conflict',[False,True])
def test_depositor_inline_matrix_must_agree_with_its_own_operator(tmp_path,conflict):
    root,model,kw,_=fixture(tmp_path)
    def add(doc):
        b=doc[0];g=b.get_mmcif_category('_pdbx_struct_assembly_gen_depositor_info.');o=b.get_mmcif_category('_pdbx_struct_oper_list_depositor_info.')
        matrix=[]
        for index in range(3):
            values=[o[f'matrix[{i}][{j}]'][index]if j<4 else o[f'vector[{i}]'][index]for i in(1,2,3)for j in(1,2,3,4)]
            if conflict and index==1:values[3]='99'
            matrix.append(' '.join(values))
        g['full_matrices']=matrix;b.set_mmcif_category('_pdbx_struct_assembly_gen_depositor_info.',g)
    kw['expected_model_sha256']=edit(model,add);g=observe(root,model,kw)['namespaces']['depositor']['generators'][1]
    assert (g['status']=='UNRESOLVED_REVIEW')is conflict
    assert g['inline_matrix_status']==('CONFLICT_OR_UNSUPPORTED'if conflict else'AGREES_WITH_OPERATOR')


def test_unknown_support_reference_is_preserved_and_flagged(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def change(doc):
        t=doc[0].get_mmcif_category('_pdbx_struct_assembly_auth_evidence.')
        t['assembly_id'][0]='unknown';doc[0].set_mmcif_category('_pdbx_struct_assembly_auth_evidence.',t)
    kw['expected_model_sha256']=edit(model,change);r=observe(root,model,kw)
    support=r['namespaces']['curated']['support_references'][0]
    assert support['raw_fields']['assembly_id']=='unknown'and support['status']=='UNRESOLVED_REVIEW'


def test_absent_assembly_is_unavailable_and_invalid_bounds_rejected(tmp_path):
    root,model,kw,_=polymer_fixture(tmp_path)
    options=dict(kw,max_rotation_component_error=1e-8,max_translation_component_error_angstrom=1e-6,max_assembly_position_error_angstrom=1e-5)
    r=observe(root,model,options);assert r['status']=='UNAVAILABLE'
    assert not r['namespaces']['curated']['generators']
    for bad in (True,float('nan'),-.1,.1):
        options['max_rotation_component_error']=bad
        with pytest.raises(ValueError,match='bounds'):observe(root,model,options)



def view_binding(kw):
    kw=dict(kw);bounds={k:kw.pop(k)for k in ('max_rotation_component_error','max_translation_component_error_angstrom','max_assembly_position_error_angstrom')}
    cedar=kw.pop('cedar_source');return kw,bounds,cedar


def test_ordinary_view_recomputes_exact_assembly_without_changing_default_scene(tmp_path):
    from nasolve.topostitch_view import representative_scene,write_preview_view
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old);expected=observe(root,model,kw);binding,bounds,cedar=view_binding(kw)
    options=dict(original_cif=model,cif_binding=binding,cedar_source=cedar)
    baseline=representative_scene(root,**options)
    scene=write_preview_view(root,tmp_path/'view.html',assembly_bounds=bounds,**options)
    assert scene['original_cif_assemblies']==expected
    assert {k:v for k,v in scene.items()if k!='original_cif_assemblies'}==baseline
    relative=[p.relative_to(old)for p in(root,model,cedar)];moved=tmp_path/'moved';shutil.move(old,moved)
    root,model,cedar=[moved/p for p in relative]
    assert not old.exists()
    assert representative_scene(root,original_cif=model,cif_binding=binding,cedar_source=cedar,assembly_bounds=bounds)==scene


@pytest.mark.parametrize('problem',['missing_cif','missing_binding','unknown_bound','bad_bound','drift'])
def test_assembly_view_refuses_unbound_or_changed_inputs_before_output(tmp_path,monkeypatch,problem):
    from nasolve.topostitch_view import write_preview_view
    root,model,kw,_=fixture(tmp_path);binding,bounds,cedar=view_binding(kw)
    options=dict(original_cif=model,cif_binding=binding,cedar_source=cedar,assembly_bounds=bounds)
    if problem=='missing_cif':options['original_cif']=None
    elif problem=='missing_binding':options['cif_binding']=None
    elif problem=='unknown_bound':bounds['unknown']=1.
    elif problem=='bad_bound':bounds['max_rotation_component_error']=True
    elif problem=='drift':
        import nasolve.topostitch_cif_assembly as module
        before=module.observe_relabel_cif_assemblies
        def drift(*a,**k):
            result=before(*a,**k);(root/'source.pdb').write_bytes((root/'source.pdb').read_bytes()+b'REMARK changed\n');return result
        monkeypatch.setattr(module,'observe_relabel_cif_assemblies',drift)
    out=tmp_path/'bad.html'
    with pytest.raises(ValueError):write_preview_view(root,out,**options)
    assert not out.exists()


def test_assembly_view_cli_embeds_separate_actual_matrices_and_images(tmp_path):
    from nasolve.topostitch_view import main
    import re
    root,model,kw,_=fixture(tmp_path);binding,bounds,cedar=view_binding(kw)
    bp=tmp_path/'binding.json';bp.write_text(json.dumps(binding));rp=tmp_path/'rounding.json';rp.write_text(json.dumps(bounds));out=tmp_path/'view.html'
    args=[str(root),'--out',str(out),'--original-cif',str(model),'--cif-binding',str(bp),'--cedar-source',str(cedar),'--assembly-bounds',str(rp)]
    assert main(args)==0
    html=out.read_text();scene=json.loads(re.search(r'<script id="scene" type="application/json">(.*?)</script>',html,re.S)[1])
    assert scene['original_cif_assemblies']==observe(root,model,kw)
    assert 'Assembly images' in html and 'Supplied Cartesian matrix' in html
    assert str(tmp_path)not in html
    rp.write_text('null');args[args.index('--out')+1]=str(tmp_path/'invalid.html')
    with pytest.raises(SystemExit)as e:main(args)
    assert e.value.code==2 and not(tmp_path/'invalid.html').exists()



def instances(root,model,kw,**options):
    from nasolve.topostitch_cif_assembly import observe_relabel_cif_assembly_instances
    return observe_relabel_cif_assembly_instances(root,model,**kw,**options)


def test_instance_coverage_preserves_deposited_tensors_and_original_observer(tmp_path):
    root,model,kw,_=fixture(tmp_path);baseline=observe(root,model,kw)
    r=instances(root,model,kw);a=r['namespaces']['curated']['assemblies'][0]
    assert r['assembly_observation_sha256']==baseline['report_sha256']
    assert observe(root,model,kw)==baseline
    assert a['status']=='LABELLED_INSTANCES_OBSERVED' and a['instance_count']==252
    assert a['anisotropic_instance_count']==252 and a['isotropic_instance_count']==0
    assert a['maximum_raw_U_transport_error_angstrom_squared']<1e-12
    # Three P43 generators are a finite subset, not the complete infinite crystal.
    assert not a['unchanged_generator_exact_set_preserved']
    assert a['missing_exact_instances']>0 and a['extra_exact_instances']>0
    assert not r['tls_U_added_or_substituted'] and not r['writer_authorized']
    assert str(tmp_path)not in json.dumps(r)


def test_instance_coverage_keeps_duplicate_generator_multiplicity(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def duplicate(doc):
        t=doc[0].get_mmcif_category('_pdbx_struct_assembly_gen.')
        for values in t.values():values.append(values[0])
        doc[0].set_mmcif_category('_pdbx_struct_assembly_gen.',t)
    kw['expected_model_sha256']=edit(model,duplicate)
    r=instances(root,model,kw)['namespaces']['curated']['assemblies'][0]
    assert r['instance_count']==336 and r['unique_exact_image_keys']<336
    assert r['source_generator_rows']==[1,2,3,4]


def test_unresolved_generator_blocks_complete_instance_observation(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def damage(doc):
        t=doc[0].get_mmcif_category('_pdbx_struct_assembly_gen.');t['oper_expression'][1]='(1)(2)'
        doc[0].set_mmcif_category('_pdbx_struct_assembly_gen.',t)
    kw['expected_model_sha256']=edit(model,damage)
    r=instances(root,model,kw)['namespaces']['curated']['assemblies'][0]
    assert r['status']=='UNRESOLVED_REVIEW' and r['unresolved_generator_rows']==[2]
    assert 'instance_count'not in r


@pytest.mark.parametrize('budget',[True,0,1,2_000_001])
def test_instance_budget_refuses_before_expanding(tmp_path,budget):
    root,model,kw,_=fixture(tmp_path)
    with pytest.raises(ValueError,match='[Bb]udget|instance'):instances(root,model,kw,max_instances=budget)


def test_instance_source_relocation_and_race(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old);r=instances(root,model,kw)
    paths=[p.relative_to(old)for p in(root,model,kw['cedar_source'])];moved=tmp_path/'moved';shutil.move(old,moved)
    root,model,kw['cedar_source']=[moved/p for p in paths]
    assert not old.exists()and instances(root,model,kw)==r
    import nasolve.topostitch_cif_source as module
    original=module.load_relabel_cif_source
    def drift(*a,**k):
        value=original(*a,**k);model.write_bytes(model.read_bytes()+b'\n');return value
    monkeypatch.setattr(module,'load_relabel_cif_source',drift)
    with pytest.raises(ValueError,match='changed'):instances(root,model,kw)



def test_complete_threefold_set_can_permute_but_whole_cell_shift_cannot(tmp_path,monkeypatch):
    import tests.test_topostitch_scattering as scattering
    original=scattering.fixture
    for index,image in enumerate(('-y,x-y,z','-y+1,x-y,z')):
        monkeypatch.setattr(scattering,'fixture',lambda path,op=image:original(path,cell=(30,30,40,90,90,120),group='H 3',image=op))
        path=tmp_path/str(index);path.mkdir();root,model,kw,_=fixture(path)
        a=instances(root,model,kw)['namespaces']['curated']['assemblies'][0]
        assert a['unchanged_generator_exact_set_preserved']is(index==0)
        assert (a['missing_exact_instances']==0)is(index==0)


@pytest.mark.parametrize('isotropic_atoms',[1,84])
def test_instance_coverage_retains_mixed_and_absent_anisotropic_modes(tmp_path,monkeypatch,isotropic_atoms):
    import gemmi
    import tests.test_topostitch_scattering as scattering
    import tests.test_topostitch_cif_paths as paths_module
    original=scattering.fixture
    def working(path):
        paths,kw=original(path,anisou=isotropic_atoms!=84)
        if isotropic_atoms==1:
            lines=paths[0].read_text().splitlines(keepends=True)
            del lines[next(i for i,s in enumerate(lines)if s.startswith('ANISOU'))]
            scattering.rebind(paths,''.join(lines))
            kw['expected_registered_graph_sha256']=scattering.build_registered_periodic_graph(*paths)['report_sha256']
        return paths,kw
    monkeypatch.setattr(scattering,'fixture',working)
    def original_cif(path):
        root,pin,_=scattering.saved_scattering_packet(path)
        model=path/'original.cif';gemmi.read_pdb_string((root/'source.pdb').read_text()).make_mmcif_document().write_file(str(model))
        return root,model,dict(expected_receipt_sha256=pin,expected_model_sha256=sha256(model.read_bytes()).hexdigest(),component_aliases={},max_coordinate_component_error_angstrom=.000501,max_u_component_error_angstrom_squared=.0000501,max_b_error_angstrom_squared=.00501,max_occupancy_error=.00501)
    monkeypatch.setattr(paths_module,'fixture',original_cif)
    root,model,kw,_=fixture(tmp_path);a=instances(root,model,kw)['namespaces']['curated']['assemblies'][0]
    assert a['isotropic_instance_count']==3*isotropic_atoms
    assert a['anisotropic_instance_count']==3*(84-isotropic_atoms)
    if isotropic_atoms==84:assert a['maximum_raw_U_transport_error_angstrom_squared']is None


@pytest.mark.parametrize('fault',['drop','duplicate','wrong_tensor_rotation'])
def test_instance_coverage_refuses_partition_or_tensor_damage(tmp_path,monkeypatch,fault):
    import nasolve.topostitch_cif_assembly as module
    root,model,kw,_=fixture(tmp_path);original=module.observe_relabel_cif_assemblies
    def changed(*a,**k):
        r=original(*a,**k)
        p=next(p for p in r['namespaces']['curated']['generators'][0]['partitions']if p['representative_image_xyz']!='x,y,z')
        if fault=='drop':p['original_atom_ids'].pop()
        elif fault=='duplicate':p['original_atom_ids'].append(p['original_atom_ids'][0])
        else:p['proposed_cartesian_rotation']=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
        return r
    monkeypatch.setattr(module,'observe_relabel_cif_assemblies',changed)
    with pytest.raises(ValueError,match='partition|tensor'):instances(root,model,kw)
