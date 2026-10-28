"""A browser can navigate verified evidence, never mutate its scientific parents."""
import copy
import http.client
import json
from pathlib import Path
import threading

import pytest

from nasolve.metal.recipe import RecipeError
from nasolve.metal.workbench import capture_catalog
from nasolve.metal.viewer import create_server, open_viewer
from tests.test_metal_workbench import fixture


def setup(tmp_path, monkeypatch):
    run, request, mounts = fixture(tmp_path, monkeypatch)
    catalog = capture_catalog(request, mounts)
    return run, catalog, mounts, open_viewer(catalog, mounts)


def test_row_navigation_projects_exact_model_and_recipe_without_writes(tmp_path, monkeypatch):
    run, catalog, mounts, viewer = setup(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in run.rglob('*') if p.is_file()}
    rows = viewer.workbench.to_dict()['rows']
    out = viewer.navigate({'action': 'row', 'selection': viewer.workbench.initial_selection(),
                           'row_id': rows[1]['row_id'], 'site_id': 'neighbor'})
    assert out['view']['selected_row'] == rows[1]
    scene = out['scene']
    assert scene['model'] == viewer.workbench.to_dict()['details'][0]['model']
    from nasolve.metal.context import parse_pdb
    model = parse_pdb((run / scene['model']['relative_path']).read_bytes())
    assert [a['key'] for a in scene['atoms']] == [a.key.to_dict() for a in model.snapshot.atoms]
    assert [a['xyz'] for a in scene['atoms']] == [list(a.xyz) for a in model.snapshot.atoms]
    preview = json.loads((run / 'Metal/geometry_001/preview.json').read_text())
    assert scene['restraints'] == preview['restraints']
    assert scene['nodes'] == preview['nodes']
    assert scene['status'] == 'GEOMETRY_REVIEW'
    assert len(scene['site_atoms']) == 2
    assert out['view']['scientific_acceptance'] == 'NOT_ASSESSED'
    assert all(p.read_bytes() == raw for p, raw in before.items())
    # An already open viewer owns detached evidence; no further source I/O.
    import nasolve.metal.viewer as module
    monkeypatch.setattr(module, '_source', lambda *a: pytest.fail('Navigation must not reread inputs'))
    out['scene']['atoms'].clear()
    assert viewer.present()['scene']['atoms']
    assert viewer.navigate({'action': 'reset'})['scene'] is None


def test_colliding_candidate_ids_in_different_datasets_keep_scene_scope(tmp_path, monkeypatch):
    import shutil
    run, request, mounts = fixture(tmp_path / 'first', monkeypatch)
    second = tmp_path / 'second'
    shutil.copytree(mounts['one'], second)
    dataset = copy.deepcopy(request['datasets'][0]); dataset['dataset_id'] = 'two'
    request['datasets'].append(dataset); mounts['two'] = second
    viewer = open_viewer(capture_catalog(request, mounts), mounts)
    row = viewer.workbench.to_dict()['rows'][-1]
    out = viewer.navigate({'action': 'row', 'selection': viewer.workbench.initial_selection(), 'row_id': row['row_id']})
    assert out['scene']['dataset_id'] == 'two'
    assert out['scene']['hypothesis_id'] == row['hypothesis_id']
    out = viewer.navigate({'action': 'select', 'selection': out['view']['selection'], 'field': 'dataset_id', 'value': 'one'})
    assert out['scene'] is None and out['view']['selection']['row_id'] is None


def test_invalid_actions_and_changed_geometry_fail_closed(tmp_path, monkeypatch):
    run, catalog, mounts, viewer = setup(tmp_path, monkeypatch)
    for action in ({'action':'run'}, {'action':'reset','job':True},
                   {'action':'select','selection':viewer.workbench.initial_selection(),'field':'camera','value':1}):
        with pytest.raises(RecipeError): viewer.navigate(action)
    (run / 'Metal/geometry_001/model.pdb').write_text('changed')
    with pytest.raises(RecipeError): open_viewer(catalog, mounts)


def test_http_is_local_authenticated_bounded_and_stateless(tmp_path, monkeypatch):
    _, _, _, viewer = setup(tmp_path, monkeypatch)
    with create_server(viewer) as server:
        assert server.server_address[0] == '127.0.0.1'
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            host = '127.0.0.1:' + str(server.server_address[1])
            def request(method, path, body=None, **headers):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=5)
                connection.request(method, path, body=body, headers=headers)
                response = connection.getresponse(); data = response.read()
                status, response_headers = response.status, dict(response.getheaders()); connection.close()
                return status, response_headers, data
            status, headers, body = request('GET', server.base_path)
            assert status == 200 and b'Saved metal results' in body
            assert "default-src 'none'" in headers['Content-Security-Policy']
            assert headers['Cache-Control'] == 'no-store'
            assert 'Access-Control-Allow-Origin' not in headers
            for asset in ('app.mjs', 'core.mjs', 'style.css'):
                assert request('GET', server.base_path + asset)[0] == 200
            assert request('GET', '/')[0] == 404
            assert request('GET', server.base_path + '../model.pdb')[0] == 404
            assert request('GET', server.base_path, Host='hostile.example')[0] == 403
            assert request('GET', server.base_path, Origin='https://hostile.example')[0] == 403
            initial = json.loads(request('GET', server.base_path + 'view')[2])
            action = json.dumps({'action':'reset'})
            endpoint = server.base_path + 'view'
            assert request('POST', endpoint, action, **{'Content-Type':'application/json'})[0] == 403
            good = {'Origin':'http://' + host, 'Content-Type':'application/json'}
            status, _, body = request('POST', endpoint, action, **good)
            assert status == 200 and json.loads(body)['scene'] is None
            assert json.loads(request('GET', endpoint)[2]) == initial  # No shared session selection.
            assert request('POST', endpoint, '{}', **good)[0] == 400
            assert request('POST', endpoint, '{"action":"reset","action":"run"}', **good)[0] == 400
            assert request('POST', endpoint, 'x' * 16385, **good)[0] == 413
            assert request('POST', endpoint, action, **dict(good, **{'Content-Type':'text/plain'}))[0] == 415
            assert request('POST', server.base_path + 'run', action, **good)[0] == 404
        finally:
            server.shutdown(); thread.join(timeout=5)


def test_cli_passes_exact_mounts_without_native_discovery(tmp_path, monkeypatch, capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    import nasolve.metal.cli as cli
    import nasolve.metal.viewer as module
    _, catalog, mounts, _ = setup(tmp_path, monkeypatch)
    path = tmp_path / 'catalog.json'; path.write_text(json.dumps(catalog))
    calls = []
    monkeypatch.setattr(module, 'serve', lambda viewer, port=0: calls.append((viewer,port)))
    monkeypatch.setattr(cli, 'discover_phenix', lambda *a,**kw: pytest.fail('No native discovery'))
    args = build_parser().parse_args(['metal','serve-workbench','--catalog',str(path),'--dataset','one='+str(mounts['one']),'--port','0'])
    assert execute(args) == 0 and len(calls) == 1
    args.dataset += args.dataset
    assert execute(args) == 2 and 'distinct' in capsys.readouterr().err


def test_viewer_and_packaged_assets_survive_source_removed_relocation(tmp_path, monkeypatch):
    import os, shutil, subprocess, sys
    original = tmp_path / 'original'
    run, catalog, mounts, viewer = setup(original, monkeypatch)
    (original / 'catalog.json').write_text(json.dumps(catalog))
    expected = viewer.present()
    shutil.copytree(Path(__file__).resolve().parents[1] / 'src', original / 'src', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved = tmp_path / 'moved'; original.rename(moved); assert not original.exists()
    code = '''import json,subprocess
from pathlib import Path
from nasolve.metal.viewer import open_viewer, assets
subprocess.run=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('No native work'))
assert set(assets())=={'','style.css','app.mjs','core.mjs'}
v=open_viewer(json.loads(Path('catalog.json').read_text()),{'one':Path('dataset')})
print(json.dumps(v.present()))
'''
    done = subprocess.run([sys.executable,'-B','-c',code],cwd=moved,
        env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == expected
