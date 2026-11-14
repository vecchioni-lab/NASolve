"""Saved cut requests must retain chosen graph links and anchor meaning."""
from hashlib import sha256
import json
import shutil
import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_graph import build_registered_periodic_graph,propose_forest_representatives
from nasolve.topostitch_recut_bundle import build_relabel_preview,load_relabel_preview,main
from nasolve.topostitch_view import representative_scene
from tests.test_topostitch_recut import anchored,node


def setup(tmp_path):
    paths=anchored(tmp_path);extra=[dict(kind='base_pairing',source_site='A:1',target_site='C:1',target_operator_xyz='y,-x,z+1/4')]
    bound=build_registered_periodic_graph(*paths,extra_edges=extra);graph=bound['periodic_graph']
    request=dict(schema_version=1,kind='topostitch-forest-proposal',registered_graph_sha256=bound['report_sha256'],
        selected_edge_ids=[graph['edges'][-1]['edge_id']],anchor_node_ids=[node(bound,'A:1')['node_id']],
        extra_edges=extra,coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000)
    path=tmp_path/'forest-request.json';path.write_text(json.dumps(request))
    return dict(model=paths[0],discovery=paths[1],registration_path=paths[2],proposal_path=path),request,bound


def test_saved_forest_retains_selection_and_replays_same_images_as_explicit_request(tmp_path):
    args,request,bound=setup(tmp_path);out=tmp_path/'forest';receipt=build_relabel_preview(**args,output_directory=out)
    graph=bound['periodic_graph'];derived=propose_forest_representatives(graph,selected_edge_ids=request['selected_edge_ids'],anchor_node_ids=request['anchor_node_ids'],expected_graph_sha256=graph['graph_sha256'])
    assert receipt['forest_selection']==dict(selected_edge_ids=request['selected_edge_ids'],anchor_node_ids=request['anchor_node_ids'],source_graph_sha256=graph['graph_sha256'],graph_proposal_sha256=derived['proposal_sha256'])
    assert (out/'proposal.json').read_bytes()==args['proposal_path'].read_bytes()
    direct={k:v for k,v in request.items() if k not in ('selected_edge_ids','anchor_node_ids')};direct.update(kind='topostitch-representative-proposal',node_images=derived['node_images'])
    args['proposal_path'].write_text(json.dumps(direct));explicit=build_relabel_preview(**args,output_directory=tmp_path/'explicit')
    assert 'forest_selection' not in explicit and receipt['observation']==explicit['observation']
    assert receipt['proposal_sha256']!=explicit['proposal_sha256']
    assert load_relabel_preview(out)==receipt
    scene=representative_scene(out);assert scene['forest_selection']==receipt['forest_selection']
    assert 'forest_selection' not in representative_scene(tmp_path/'explicit')
    assert not scene['chemical_connectivity_changed'] and not scene['graphical_review_recorded']


def test_forest_cli_and_relocated_replay_preserve_all_source_bytes(tmp_path,monkeypatch):
    original=tmp_path/'original';original.mkdir();args,_,_=setup(original);snapshots={p:p.read_bytes() for p in args.values()};out=original/'preview'
    assert main([str(args['model']),'--discovery',str(args['discovery']),'--registration',str(args['registration_path']),'--proposal',str(args['proposal_path']),'--out',str(out)])==0
    receipt=load_relabel_preview(out);assert all(p.read_bytes()==b for p,b in snapshots.items())
    moved=tmp_path/'relocated';shutil.move(out,moved);shutil.rmtree(original)
    from pathlib import Path
    opener=Path.open
    def guarded(self,*a,**kw):
        if self.resolve().is_relative_to(original):raise AssertionError('Original input lookup')
        return opener(self,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    assert load_relabel_preview(moved)==receipt
    assert representative_scene(moved)['forest_selection']==receipt['forest_selection']


@pytest.mark.parametrize('field,value',[('node_images',[]),('anchor_node_ids',[]),('selected_edge_ids',[True]),('registered_graph_sha256','a'*64),('schema_version',True)])
def test_invalid_forest_requests_create_no_packet(tmp_path,field,value):
    args,request,_=setup(tmp_path);request[field]=value;args['proposal_path'].write_text(json.dumps(request));out=tmp_path/'preview'
    with pytest.raises(ValueError):build_relabel_preview(**args,output_directory=out)
    assert not out.exists()


@pytest.mark.parametrize('tamper',['derived_choice','rehashed_request'])
def test_changed_selection_cannot_hide_behind_unchanged_image_observation(tmp_path,tamper):
    args,request,bound=setup(tmp_path);out=tmp_path/'preview';receipt=build_relabel_preview(**args,output_directory=out)
    if tamper=='derived_choice':receipt['forest_selection']['anchor_node_ids']=[True]
    else:
        request['anchor_node_ids']=[node(bound,'C:1')['node_id']]
        data=json.dumps(request).encode();(out/'proposal.json').write_bytes(data)
        receipt['artifacts']['proposal'].update(sha256=sha256(data).hexdigest(),size_bytes=len(data));receipt['proposal_sha256']=sha256(data).hexdigest()
    (out/'preview.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError):load_relabel_preview(out)
