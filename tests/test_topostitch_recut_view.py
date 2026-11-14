"""Periodic views must display exact representative and edge-image ownership."""
import copy
import json
import re
import shutil

import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_recut_bundle import build_relabel_preview
from nasolve.topostitch_view import representative_scene,write_preview_view,main
from tests.test_topostitch_recut_bundle import setup


def bundle(tmp_path):
    args,request=setup(tmp_path);out=tmp_path/'preview'
    return out,build_relabel_preview(**args,output_directory=out)


def test_scene_preserves_every_source_atom_and_renamed_logical_ownership(tmp_path):
    out,receipt=bundle(tmp_path);scene=representative_scene(out);observation=receipt['observation']
    assert scene['kind']=='topostitch-representative-view' and not scene['runtime_authority']
    assert scene['workflow']==receipt['workflow'] and not scene['coordinates_materialized']
    assert len(scene['atoms'])==len(observation['source_orbit_observation']['atoms'])
    changed=observation['requested_image_atom_indices']
    for i,atom in enumerate(scene['atoms']):
        assert atom['source_atom_index']==i
        assert atom['before']==observation['source_orbit_observation']['atoms'][i]['position_angstrom']
        assert atom['after']==observation['proposed_points_angstrom'][i]
        assert (atom['scope']=='representative')==(i in changed)
        if i not in changed:assert atom['before']==atom['after']
    moved=[a for a in scene['atoms'] if a['scope']=='representative']
    assert {a['logical_site'] for a in moved}=={'A:2'}
    assert {a['label'] for a in moved}=={'M:102'}
    assert all(a['protected'] and a['node_id'] is not None for a in moved)
    assert not scene['traces'] and not scene['contacts']
    assert scene['graph_scope']==observation['registered_graph']['scope']
    assert scene['declared_routes']==observation['registered_graph']['declared_routes']
    assert scene['source_image_assessment']==observation['source_orbit_observation']['assessment']


def test_periodic_edges_use_transformed_partner_not_the_chosen_representative(tmp_path):
    import gemmi
    from tests.test_topostitch_recut import anchored,node
    from nasolve.topostitch_graph import build_registered_periodic_graph
    paths=anchored(tmp_path);graph=build_registered_periodic_graph(*paths)
    request=dict(schema_version=1,kind='topostitch-representative-proposal',registered_graph_sha256=graph['report_sha256'],
        node_images=[dict(node_id=node(graph,'A:2')['node_id'],operator_xyz='y,-x,z+1/4')],
        extra_edges=[],coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000)
    proposal=tmp_path/'proposal.json';proposal.write_text(json.dumps(request));out=tmp_path/'preview'
    receipt=build_relabel_preview(paths[0],paths[1],registration_path=paths[2],proposal_path=proposal,output_directory=out)
    scene=representative_scene(out)
    original=receipt['observation']['edge_image_observations']
    assert len(scene['periodic_edges'])==len(original)
    cell=gemmi.UnitCell(*scene['crystal']['cell_parameters']);nonidentity=0
    for edge,expected in zip(scene['periodic_edges'],original):
        assert all(edge[k]==v for k,v in expected.items())
        if edge['status']!='IMAGE_ARITHMETIC_VERIFIED':continue
        for state in ('before','after'):
            left=scene['atoms'][edge['source_atom_index']][state]
            right=scene['atoms'][edge['target_atom_index']][state]
            op=gemmi.Op(edge[state+'_operator_xyz']);frac=cell.fractionalize(gemmi.Position(*right))
            partner=list(cell.orthogonalize(gemmi.Fractional(*op.apply_to_xyz(list(frac)))))
            assert edge[state+'_points'][0]==pytest.approx(left,abs=1e-10)
            assert edge[state+'_points'][1]==pytest.approx(partner,abs=1e-10)
            if edge[state+'_operator_xyz']!='x,y,z':
                nonidentity+=1;assert partner!=pytest.approx(right)
    assert nonidentity
    assert len(scene['cell_edges'])==12 and len(scene['cell_corners'])==8
    assert scene['cell_corners'][-1]==pytest.approx([30,30,40])


def test_relocated_packet_renders_through_existing_command_without_mutation(tmp_path):
    old=tmp_path/'old';old.mkdir();packet,receipt=bundle(old);new=tmp_path/'moved'
    shutil.move(packet,new);shutil.rmtree(old);before={p.name:p.read_bytes() for p in new.iterdir()}
    out=tmp_path/'view.html';scene=write_preview_view(new,out)
    assert {p.name:p.read_bytes() for p in new.iterdir()}==before
    html=out.read_text();embedded=re.search(r'<script id="scene" type="application/json">(.*?)</script>',html,re.S)
    assert json.loads(embedded.group(1))==scene and str(tmp_path) not in html
    assert 'fetch(' not in html and 'https://' not in html and 'http://' not in html
    assert main([str(new),'--out',str(tmp_path/'cli.html')])==0
    with pytest.raises(FileExistsError):write_preview_view(new,out)
    with pytest.raises(ValueError,match='frozen'):write_preview_view(new,new/'view.html')


@pytest.mark.parametrize('options',[dict(candidate_index=0,radius_angstrom=20),dict(periodic=True),dict(radius_angstrom=20),dict(max_pairs=1),dict(max_image_tests=1)])
def test_representative_packet_refuses_unrelated_search_options(tmp_path,options):
    packet,_=bundle(tmp_path);out=tmp_path/'view.html'
    with pytest.raises(ValueError,match='search'):write_preview_view(packet,out,**options)
    assert not out.exists()


def test_scene_rejects_tampered_receipt_and_late_artifact_change(tmp_path,monkeypatch):
    packet,receipt=bundle(tmp_path);out=tmp_path/'view.html'
    bad=copy.deepcopy(receipt);bad['observation']['proposed_points_angstrom'][0][0]+=1
    (packet/'preview.json').write_text(json.dumps(bad))
    with pytest.raises(ValueError):write_preview_view(packet,out)
    (packet/'preview.json').write_text(json.dumps(receipt))
    import nasolve.topostitch_recut_bundle as module
    original=module.load_relabel_preview
    def late(*args,**kw):
        value=original(*args,**kw);p=packet/'source.pdb';p.write_bytes(p.read_bytes()+b'REMARK late\n');return value
    monkeypatch.setattr(module,'load_relabel_preview',late)
    with pytest.raises(ValueError,match='changed'):write_preview_view(packet,out)
    assert not out.exists()


def test_unavailable_anchors_and_unregistered_context_remain_visible(tmp_path):
    from tests.test_topostitch_graph import registered
    from nasolve.topostitch_graph import build_registered_periodic_graph
    model,discovery,reg,_=registered(tmp_path,missing='A:1',rename=True)
    graph=build_registered_periodic_graph(model,discovery,reg)
    req=dict(schema_version=1,kind='topostitch-representative-proposal',registered_graph_sha256=graph['report_sha256'],node_images=[],extra_edges=[],coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000)
    path=tmp_path/'proposal.json';path.write_text(json.dumps(req));out=tmp_path/'preview'
    build_relabel_preview(model,discovery,registration_path=reg,proposal_path=path,output_directory=out)
    scene=representative_scene(out)
    assert scene['graph_scope']['unresolved_node_ids'] and scene['warnings']
    assert any(a['node_id'] is None for a in scene['atoms'])
    missing=[e for e in scene['periodic_edges'] if e['status']=='ANCHOR_UNAVAILABLE']
    assert missing and all('after_points' not in e for e in missing)
    assert scene['max_atom_displacement_angstrom']==0


def test_unknown_receipt_shape_refuses_without_output(tmp_path):
    packet=tmp_path/'preview';packet.mkdir();(packet/'preview.json').write_text('[]')
    out=tmp_path/'view.html'
    with pytest.raises(ValueError,match='receipt'):write_preview_view(packet,out)
    assert not out.exists()
