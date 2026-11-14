"""Comparing explicit cuts must not select a model or hide stale sources."""
from pathlib import Path
import json
import re
import shutil

import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_recut_bundle import build_relabel_preview
from nasolve.topostitch_view import representative_comparison, representative_scene, write_preview_view, main
from tests.test_topostitch_forest_bundle import setup
from tests.test_topostitch_recut import node


def cuts(tmp_path):
    args,request,bound=setup(tmp_path)
    paths=[tmp_path/'first',tmp_path/'second']
    build_relabel_preview(**args,output_directory=paths[0])
    request['anchor_node_ids']=[node(bound,'C:1')['node_id']]
    args['proposal_path'].write_text(json.dumps(request))
    build_relabel_preview(**args,output_directory=paths[1])
    return paths,args,request,bound


def test_comparison_keeps_exact_scenes_and_explicit_order_without_approval(tmp_path):
    paths,_,_,_=cuts(tmp_path);old=[representative_scene(p) for p in paths]
    result=representative_comparison(paths)
    assert [a['cut_id'] for a in result['alternatives']]==[1,2]
    assert [a['scene'] for a in result['alternatives']]==old
    assert result['kind']=='topostitch-representative-comparison-view'
    assert result['source_model_sha256']==old[0]['source_model_sha256']
    assert result['registered_graph_sha256']==old[0]['registered_graph_sha256']
    assert result['selection_applied'] is False and result['graphical_review_recorded'] is False
    assert result['coordinates_materialized'] is False and result['runtime_authority'] is False
    assert [representative_scene(p) for p in paths]==old
    assert str(tmp_path) not in json.dumps(result)
    reverse=representative_comparison(paths[::-1])
    assert reverse['comparison_sha256']!=result['comparison_sha256']
    assert reverse['alternatives'][0]['scene']==old[1]


@pytest.mark.parametrize('which',['source','graph'])
def test_different_source_or_registered_graph_cannot_be_compared_as_cuts(tmp_path,which):
    paths,args,request,_=cuts(tmp_path)
    from nasolve.topostitch_graph import build_registered_periodic_graph
    if which=='source':
        from tests.test_topostitch_recut import prepare
        other=tmp_path/'other';other.mkdir();inputs,bound=prepare(other,rename=True)
        args.update(model=inputs[0],discovery=inputs[1],registration_path=inputs[2])
        request=dict(schema_version=1,kind='topostitch-representative-proposal',node_images=[],extra_edges=[],
            registered_graph_sha256=bound['report_sha256'],coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000)
    else:
        request['extra_edges'][0]['kind']='stacking'
        bound=build_registered_periodic_graph(args['model'],args['discovery'],args['registration_path'],extra_edges=request['extra_edges'])
        request['registered_graph_sha256']=bound['report_sha256']
    args['proposal_path'].write_text(json.dumps(request));other=tmp_path/'different'
    build_relabel_preview(**args,output_directory=other)
    out=tmp_path/'invalid.html'
    with pytest.raises(ValueError,match='same source and registered graph'):
        write_preview_view(paths[0],out,comparison_directories=[other])
    assert not out.exists()


@pytest.mark.parametrize('paths',[[],['missing'],['missing']*9,'missing'])
def test_comparison_count_and_type_refuse_before_reading(paths):
    with pytest.raises(ValueError,match='2 to 8'):representative_comparison(paths)


def test_duplicate_packet_alias_and_copied_packet_refuse(tmp_path):
    paths,_,_,_=cuts(tmp_path)
    with pytest.raises(ValueError,match='distinct'):representative_comparison([paths[0],paths[0]/'.'])
    copied=tmp_path/'copied';shutil.copytree(paths[0],copied)
    with pytest.raises(ValueError,match='duplicate'):representative_comparison([paths[0],copied])


def test_changed_earlier_packet_during_later_replay_refuses(tmp_path,monkeypatch):
    import nasolve.topostitch_view as module
    paths,_,_,_=cuts(tmp_path);old=module.representative_scene;calls=0
    def drift(*a,**kw):
        nonlocal calls
        result=old(*a,**kw);calls+=1
        if calls==2:
            p=paths[0]/'proposal.json';p.write_bytes(p.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(module,'representative_scene',drift)
    with pytest.raises(ValueError,match='changed during'):representative_comparison(paths)


def test_relocated_comparison_cli_preserves_every_packet_byte(tmp_path,monkeypatch):
    original=tmp_path/'original';original.mkdir();paths,_,_,_=cuts(original)
    expected=representative_comparison(paths);moved=tmp_path/'moved';moved.mkdir()
    paths=[Path(shutil.move(p,moved/p.name)) for p in paths];shutil.rmtree(original)
    before={p:p.read_bytes() for root in paths for p in root.iterdir()}
    opener=Path.open
    def guarded(self,*a,**kw):
        if self.resolve().is_relative_to(original):raise AssertionError('Original lookup forbidden')
        return opener(self,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    out=tmp_path/'comparison.html'
    assert main([str(paths[0]),'--compare',str(paths[1]),'--out',str(out)])==0
    html=out.read_text();scene=json.loads(re.search(r'<script id="scene" type="application/json">(.*?)</script>',html,re.S).group(1))
    assert scene==expected and all(p.read_bytes()==b for p,b in before.items())
    assert str(tmp_path) not in html and 'fetch(' not in html
    with pytest.raises(FileExistsError):write_preview_view(paths[0],out,comparison_directories=[paths[1]])
    with pytest.raises(ValueError,match='frozen'):write_preview_view(paths[0],paths[1]/'bad.html',comparison_directories=[paths[1]])
    assert not (paths[1]/'bad.html').exists()


def test_comparison_refuses_bend_options_and_excess_display_budget(tmp_path,monkeypatch):
    import nasolve.topostitch_view as module
    paths,_,_,_=cuts(tmp_path);out=tmp_path/'bad.html'
    with pytest.raises(ValueError,match='search'):write_preview_view(paths[0],out,comparison_directories=[paths[1]],periodic=True)
    monkeypatch.setattr(module,'_MAX_COMPARISON_POINTS',1)
    with pytest.raises(ValueError,match='display budget'):write_preview_view(paths[0],out,comparison_directories=[paths[1]])
    assert not out.exists()


def test_comparison_requires_representative_packets(tmp_path):
    from tests.test_topostitch_preview import setup_preview,build
    paths,_,_,_=cuts(tmp_path);bendroot=tmp_path/'bend';bendroot.mkdir();inputs=setup_preview(bendroot)
    bend=bendroot/'preview';build(inputs,bend)
    out=tmp_path/'bad.html'
    with pytest.raises(ValueError,match='representative'):write_preview_view(bend,out,comparison_directories=[paths[0]])
    assert not out.exists()
