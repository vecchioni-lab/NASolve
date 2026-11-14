"""A cut preference is source-bound review input, never model approval."""
import json
import re
import shutil
import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_view import representative_comparison,validate_cut_preference,write_preview_view
from tests.test_topostitch_cut_comparison import cuts


def preference(tmp_path,decision='prefer_cut'):
    paths,_,_,_=cuts(tmp_path);comparison=representative_comparison(paths)
    request=dict(schema_version=1,kind='topostitch-cut-preference',
        comparison_sha256=comparison['comparison_sha256'],source_model_sha256=comparison['source_model_sha256'],
        registered_graph_sha256=comparison['registered_graph_sha256'],decision=decision,
        preferred_preview_receipt_sha256=comparison['alternatives'][1]['scene']['preview_receipt_sha256'] if decision=='prefer_cut' else None,
        comment='Keep the junction in view. </script>')
    path=tmp_path/'preference.json';path.write_text(json.dumps(request));return paths,comparison,path,request


@pytest.mark.parametrize('decision',['prefer_cut','keep_original','needs_revision'])
def test_preference_replays_exact_scope_without_approving_or_changing_packets(tmp_path,decision):
    paths,comparison,path,request=preference(tmp_path,decision);before={p:p.read_bytes() for root in paths for p in root.iterdir()}
    checked=validate_cut_preference(paths,path)
    assert checked['decision']==decision and checked['comment']==request['comment']
    assert checked['preferred_preview_receipt_sha256']==request['preferred_preview_receipt_sha256']
    assert checked['comparison_sha256']==comparison['comparison_sha256']
    assert not any(checked[k] for k in ('reviewer_authenticated','scientific_acceptance','checkpoint_selection_applied','runtime_authority'))
    assert all(p.read_bytes()==v for p,v in before.items())
    out=tmp_path/'noted.html';scene=write_preview_view(paths[0],out,comparison_directories=[paths[1]],preference_path=path)
    assert scene==comparison
    html=out.read_text();embedded=re.search(r'<script id="preference" type="application/json">(.*?)</script>',html,re.S)
    assert json.loads(embedded.group(1))==checked
    assert 'Keep the junction in view. </script>' not in html


@pytest.mark.parametrize('field,value',[('schema_version',True),('comparison_sha256','0'*64),('source_model_sha256','0'*64),('registered_graph_sha256','0'*64),('preferred_preview_receipt_sha256','0'*64),('decision','approve'),('runtime_authority',True),('comment','x'*2001)])
def test_invalid_stale_or_authority_bearing_preference_creates_no_output(tmp_path,field,value):
    paths,_,path,request=preference(tmp_path);request[field]=value;path.write_text(json.dumps(request));out=tmp_path/'invalid.html'
    with pytest.raises(ValueError):write_preview_view(paths[0],out,comparison_directories=[paths[1]],preference_path=path)
    assert not out.exists()


def test_keep_original_cannot_hide_a_preferred_cut_and_duplicate_keys_refuse(tmp_path):
    paths,_,path,request=preference(tmp_path);request['decision']='keep_original';path.write_text(json.dumps(request))
    with pytest.raises(ValueError):validate_cut_preference(paths,path)
    request['preferred_preview_receipt_sha256']=None;path.write_text(json.dumps(request)[:-1]+',"decision":"needs_revision"}')
    with pytest.raises(ValueError,match='Duplicate'):validate_cut_preference(paths,path)


def test_preference_relocates_and_reordering_cuts_requires_new_review(tmp_path):
    old=tmp_path/'old';old.mkdir();paths,_,path,_=preference(old);expected=validate_cut_preference(paths,path)
    new=tmp_path/'new';shutil.move(old,new);paths=[new/p.name for p in paths];path=new/path.name
    assert not old.exists() and validate_cut_preference(paths,path)==expected
    with pytest.raises(ValueError,match='comparison'):validate_cut_preference(paths[::-1],path)


def test_preference_requires_comparison_and_bounded_file(tmp_path):
    paths,_,path,_=preference(tmp_path);out=tmp_path/'bad.html'
    with pytest.raises(ValueError,match='comparison'):write_preview_view(paths[0],out,preference_path=path)
    path.write_text(' '*17000)
    with pytest.raises(ValueError,match='size'):validate_cut_preference(paths,path)
    assert not out.exists()


def test_scene_and_preference_placeholder_text_round_trips_without_substitution():
    from nasolve.topostitch_view import _html
    scene={'note':'__PREFERENCE_JSON__'};preference={'comment':'__SCENE_JSON__ </script>'}
    html=_html(scene,preference)
    for name,expected in [('scene',scene),('preference',preference)]:
        assert json.loads(re.search(r'<script id="'+name+r'" type="application/json">(.*?)</script>',html,re.S).group(1))==expected
