"""A uniform crystal image carries declared TLS; mixed group images need review."""
import json
import math
import shutil
from pathlib import Path

import pytest
from tests.test_topostitch_cif_reference_ranges import fixture as reference_fixture
from tests.test_topostitch_cif_source import edit
from nasolve.topostitch_transport import CartesianImage


def parameters():
    return dict(origin_angstrom=[1.,2.,3.],T_angstrom_squared=[1.,2.,3.,.2,.3,.4],
        L_degrees_squared=[4.,5.,6.,.1,.2,.3],S_angstrom_degrees=[1.,2.,3.,4.,5.,6.,7.,8.,9.])


def fixture(tmp_path,mixed=False):
    root,model,kw,owner=reference_fixture(tmp_path)
    def add(doc):
        b=doc[0];p=parameters();row=dict(id='tls-1',pdbx_refine_id='X-RAY DIFFRACTION',method='refined',details=None)
        row.update({f'origin_{axis}':str(value)for axis,value in zip('xyz',p['origin_angstrom'])})
        for prefix,key in [('T','T_angstrom_squared'),('L','L_degrees_squared')]:
            for (i,j),v in zip([(1,1),(2,2),(3,3),(1,2),(1,3),(2,3)],p[key]):row[f'{prefix}[{i}][{j}]']=str(v)
        for i in range(3):
            for j in range(3):row[f'S[{i+1}][{j+1}]']=str(p['S_angstrom_degrees'][i*3+j])
        b.set_mmcif_category('_pdbx_refine_tls.',{k:[v]for k,v in row.items()})
        preview=json.loads((root/'preview.json').read_text())['observation']
        moved=preview['graph_relabeling']['changed_node_ids'][0]
        node=next(n for n in preview['registered_graph']['nodes']if n['node_id']==moved)
        a=b.get_mmcif_category('_atom_site.');idx=node['atom_indices'][0]
        chain=a['label_asym_id'][idx];seq=int(a['label_seq_id'][idx]);auth=a['auth_asym_id'][idx];num=int(a['auth_seq_id'][idx])
        beg,end=(1,4) if mixed else (seq,seq)
        first,last=(101,104)if mixed else(num,num)
        group=dict(id='group-1',pdbx_refine_id='X-RAY DIFFRACTION',refine_tls_id='tls-1',
            beg_label_asym_id=chain,end_label_asym_id=chain,beg_label_seq_id=str(beg),end_label_seq_id=str(end),
            beg_auth_asym_id=auth,end_auth_asym_id=auth,beg_auth_seq_id=str(first),end_auth_seq_id=str(last),
            beg_PDB_ins_code=None,end_PDB_ins_code=None,selection=None,
            selection_details=f"(chain '{auth}' and resid {first} through {last})")
        b.set_mmcif_category('_pdbx_refine_tls_group.',{k:[v]for k,v in group.items()})
    kw['expected_model_sha256']=edit(model,add)
    return root,model,kw,owner


def observe(root,model,kw):
    from nasolve.topostitch_cif_tls import observe_relabel_cif_tls
    return observe_relabel_cif_tls(root,model,**kw)


def test_declared_tls_units_and_screw_convention():
    from nasolve.topostitch_cif_tls import tls_u_cart
    p=dict(origin_angstrom=[0.,0.,0.],T_angstrom_squared=[0.]*6,L_degrees_squared=[1.,0.,0.,0.,0.,0.],S_angstrom_degrees=[0.]*9)
    assert tls_u_cart(p,[0.,1.,0.])==pytest.approx([0.,0.,(math.pi/180)**2,0.,0.,0.])
    p['L_degrees_squared']=[0.]*6;p['S_angstrom_degrees'][3]=1.
    assert tls_u_cart(p,[0.,0.,1.])==pytest.approx([2*math.pi/180,0.,0.,0.,0.,0.])


def test_tls_rotation_origin_and_nonzero_trace_are_preserved():
    from nasolve.topostitch_cif_tls import transport_tls_parameters,tls_u_cart
    p=parameters();image=CartesianImage(((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.)),(2.,3.,4.))
    moved=transport_tls_parameters(p,image)
    assert moved['origin_angstrom']==pytest.approx([0.,4.,7.])
    assert moved['T_angstrom_squared']==pytest.approx([2.,1.,3.,-.2,-.4,.3])
    assert moved['S_angstrom_degrees']==pytest.approx([5.,-4.,-6.,-2.,1.,3.,-8.,7.,9.])
    for xyz in ([0.,0.,0.],[3.,-2.,4.],[8.,9.,-1.]):
        assert tls_u_cart(moved,image.apply(xyz))==pytest.approx(image.rotate_tensor(tls_u_cart(p,xyz)),abs=1e-12)
    inverse=transport_tls_parameters(moved,image.inverse())
    for key in p:assert inverse[key]==pytest.approx(p[key])
    assert sum(moved['S_angstrom_degrees'][i]for i in (0,4,8))==15.


def test_one_moved_group_transports_every_member_and_keeps_raw_trace(tmp_path):
    root,model,kw,owner=fixture(tmp_path);before={p:p.read_bytes()for p in [model,owner,*root.iterdir()]}
    r=observe(root,model,kw);g=r['groups'][0]
    assert g['status']=='UNIFORM_IMAGE_TRANSPORT_OBSERVED'
    assert g['operator_xyz']!='x,y,z' and len(g['member_atom_ids'])==7
    assert g['maximum_tls_u_component_error_angstrom_squared']<1e-10
    assert g['source_s_trace_angstrom_degrees']==pytest.approx(15.)
    assert g['parameter_convention_status']=='NONZERO_S_TRACE_REVIEW'
    assert g['native_zeroize_trace_applied'] is False
    assert not r['writer_authorized'] and not r['native_refinement_compatibility_approved']
    assert all(p.read_bytes()==data for p,data in before.items())


def test_mixed_image_group_is_retained_without_splitting_or_transport(tmp_path):
    root,model,kw,_=fixture(tmp_path,mixed=True);g=observe(root,model,kw)['groups'][0]
    assert g['status']=='MIXED_IMAGES_REVIEW'
    assert len(g['member_images'])==2 and len(g['member_atom_ids'])==28
    assert g['transported_parameters'] is None
    assert len(g['original_group_rows'])==1 and g['original_parameters']


@pytest.mark.parametrize('problem',['missing_parameter','nonfinite','unsupported_selection','selection_details','wrong_author','unknown_insertion','duplicate_tls','orphan_group','missing_refine_id','unknown_selection'])
def test_incomplete_or_conflicting_tls_evidence_cannot_transport(tmp_path,problem):
    root,model,kw,_=fixture(tmp_path)
    def damage(doc):
        b=doc[0];t=b.get_mmcif_category('_pdbx_refine_tls.');g=b.get_mmcif_category('_pdbx_refine_tls_group.')
        if problem=='missing_parameter':t['S[3][3]'][0]=None
        elif problem=='nonfinite':t['T[1][1]'][0]='nan'
        elif problem=='unsupported_selection':g['selection'][0]='name P'
        elif problem=='selection_details':g['selection_details'][0]+=' and name P'
        elif problem=='wrong_author':g['beg_auth_seq_id'][0]='999'
        elif problem=='unknown_insertion':
            a=b.get_mmcif_category('_atom_site.');a['pdbx_PDB_ins_code']=[None]*len(a['id']);b.set_mmcif_category('_atom_site.',a)
            s=b.get_mmcif_category('_pdbx_poly_seq_scheme.');s['pdb_ins_code']=[None]*len(s['seq_id']);b.set_mmcif_category('_pdbx_poly_seq_scheme.',s)
        elif problem=='duplicate_tls':
            for v in t.values():v.append(v[0])
        elif problem=='orphan_group':g['refine_tls_id'][0]='absent'
        elif problem=='missing_refine_id':t['pdbx_refine_id'][0]=g['pdbx_refine_id'][0]=None
        elif problem=='unknown_selection':g['selection_details'][0]=None
        b.set_mmcif_category('_pdbx_refine_tls.',t);b.set_mmcif_category('_pdbx_refine_tls_group.',g)
    kw['expected_model_sha256']=edit(model,damage)
    r=observe(root,model,kw)
    assert all(g['status']=='REVIEW_REQUIRED' and g['issues'] and g['transported_parameters'] is None for g in r['groups'])
    if problem=='orphan_group':assert len(r['orphan_group_rows'])==1


def test_tls_relocation_and_input_drift(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old);r=observe(root,model,kw)
    rel=[p.relative_to(old)for p in (root,model,kw['cedar_source'])];new=tmp_path/'moved';shutil.move(old,new)
    root,model,cedar=[new/p for p in rel];kw['cedar_source']=cedar
    assert not old.exists()and observe(root,model,kw)==r
    import nasolve.topostitch_cif_tls as module
    before=module.observe_relabel_cif_fragments
    def drift(*args,**kwargs):
        result=before(*args,**kwargs);model.write_bytes(model.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'observe_relabel_cif_fragments',drift)
    with pytest.raises(ValueError,match='changed'):observe(root,model,kw)


def test_explicitly_inapplicable_selection_uses_complete_declared_range(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def edit_group(doc):
        t=doc[0].get_mmcif_category('_pdbx_refine_tls_group.')
        t['selection'][0]=False;t['selection_details'][0]=False
        doc[0].set_mmcif_category('_pdbx_refine_tls_group.',t)
    kw['expected_model_sha256']=edit(model,edit_group)
    g=observe(root,model,kw)['groups'][0]
    assert g['status']=='UNIFORM_IMAGE_TRANSPORT_OBSERVED'
    assert g['original_group_rows'][0]['selection'] is False


def test_tls_view_keeps_exact_mixed_members_and_relocates(tmp_path):
    from nasolve.topostitch_view import representative_scene, write_preview_view
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old,mixed=True)
    cedar=kw.pop('cedar_source');expected=observe(root,model,dict(kw,cedar_source=cedar))
    plain=representative_scene(root)
    before={p:p.read_bytes()for p in [model,*root.iterdir()]}
    scene=representative_scene(root,original_cif=model,cif_binding=kw,cedar_source=cedar)
    assert scene['original_cif_tls']==expected
    assert {k:v for k,v in scene.items()if k!='original_cif_tls'}==plain
    assert all(p.read_bytes()==v for p,v in before.items())
    output=tmp_path/'view.html';write_preview_view(root,output,original_cif=model,cif_binding=kw,cedar_source=cedar)
    html=output.read_text();assert 'Original TLS groups' in html and 'MIXED_IMAGES_REVIEW' in html
    moved=tmp_path/'moved';relative=[p.relative_to(old)for p in (root,model,cedar)];shutil.move(old,moved)
    root,model,cedar=[moved/p for p in relative]
    assert not old.exists()
    assert representative_scene(root,original_cif=model,cif_binding=kw,cedar_source=cedar)==scene


@pytest.mark.parametrize('problem',['missing_binding','missing_cif','wrong_preview','wrong_model','unknown_key','comparison'])
def test_tls_view_refuses_unbound_evidence_before_output(tmp_path,problem):
    from nasolve.topostitch_view import write_preview_view
    root,model,kw,_=fixture(tmp_path,mixed=True);cedar=kw.pop('cedar_source')
    args=dict(original_cif=model,cif_binding=kw,cedar_source=cedar)
    if problem=='missing_binding':args['cif_binding']=None
    elif problem=='missing_cif':args['original_cif']=None
    elif problem=='wrong_preview':kw['expected_receipt_sha256']='0'*64
    elif problem=='wrong_model':kw['expected_model_sha256']='0'*64
    elif problem=='unknown_key':kw['unexpected']=True
    elif problem=='comparison':args['comparison_directories']=[root]
    output=tmp_path/'invalid.html'
    with pytest.raises(ValueError):write_preview_view(root,output,**args)
    assert not output.exists()


def test_tls_view_cli_uses_explicit_original_and_path_free_binding(tmp_path):
    from nasolve.topostitch_view import main
    root,model,kw,_=fixture(tmp_path,mixed=True);cedar=kw.pop('cedar_source')
    binding=tmp_path/'binding.json';binding.write_text(json.dumps(kw));out=tmp_path/'view.html'
    assert main([str(root),'--out',str(out),'--original-cif',str(model),
        '--cif-binding',str(binding),'--cedar-source',str(cedar)])==0
    import re
    scene=json.loads(re.search(r'<script id="scene" type="application/json">(.*?)</script>',out.read_text(),re.S)[1])
    assert scene['original_cif_tls']['mixed_group_count']==1
    binding.write_text('{"expected_model_sha256":"a","expected_model_sha256":"b"}')
    with pytest.raises(SystemExit)as exc:
        main([str(root),'--out',str(tmp_path/'bad.html'),'--original-cif',str(model),'--cif-binding',str(binding)])
    assert exc.value.code==2 and not(tmp_path/'bad.html').exists()
