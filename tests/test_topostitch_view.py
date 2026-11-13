"""A graphical view must show verified frozen coordinates without changing state."""
import json
import shutil
import re

import pytest

from nasolve.topostitch_view import preview_scene,write_preview_view
from .test_topostitch_preview import setup_preview,build


def test_view_replays_preview_and_preserves_inputs_after_relocation(tmp_path):
    original=tmp_path/'original';original.mkdir()
    paths=setup_preview(original)
    preview=original/'preview';receipt=build(paths,preview)
    moved=tmp_path/'moved';shutil.move(preview,moved);shutil.rmtree(original)
    before={p.name:p.read_bytes() for p in moved.iterdir()}
    out=tmp_path/'view.html';scene=write_preview_view(moved,out)
    assert scene['workflow']==receipt['workflow']
    assert scene['candidate_model_sha256']==receipt['candidate_model_sha256']
    assert scene['runtime_authority'] is False
    assert scene['atoms'] and scene['traces']
    assert any(a['before']!=a['after'] for a in scene['atoms'])
    assert all(a['before']==a['after'] for a in scene['atoms'] if a['scope']=='fixed')
    assert {p.name:p.read_bytes() for p in moved.iterdir()}==before
    html=out.read_text();match=re.search(r'<script id="scene" type="application/json">(.*?)</script>',html,re.S)
    assert json.loads(match.group(1))==scene
    assert str(tmp_path) not in html
    assert 'fetch(' not in html and 'http://' not in html and 'https://' not in html
    assert 'content="default-src' in html
    with pytest.raises(FileExistsError):write_preview_view(moved,out)
    with pytest.raises(ValueError,match='frozen preview'):write_preview_view(moved,moved/'view.html')


def test_view_refuses_tampered_preview_before_creating_output(tmp_path):
    paths=setup_preview(tmp_path);preview=tmp_path/'preview';build(paths,preview)
    candidate=preview/'candidate.pdb';candidate.write_bytes(candidate.read_bytes()+b'REMARK changed\n')
    out=tmp_path/'view.html'
    with pytest.raises(ValueError):write_preview_view(preview,out)
    assert not out.exists()


def test_view_requires_explicit_candidate_for_periodic_display(tmp_path):
    paths=setup_preview(tmp_path);preview=tmp_path/'preview';build(paths,preview)
    with pytest.raises(ValueError,match='candidate'):preview_scene(preview,periodic=True)


def test_scene_json_is_script_safe():
    from nasolve.topostitch_view import _html
    scene={'label':'</script><script>alert(1)</script>&\u2028'}
    html=_html(scene)
    assert '</script><script>alert(1)' not in html
    match=re.search(r'<script id="scene" type="application/json">(.*?)</script>',html,re.S)
    assert json.loads(match.group(1))==scene


@pytest.mark.parametrize('move_target',[False,True])
def test_periodic_view_applies_exact_mate_to_both_coordinate_sets(tmp_path,move_target):
    gemmi=pytest.importorskip('gemmi')
    from .test_topostitch_fit import fit_inputs,fit
    from nasolve.topostitch_preview import build_bend_preview
    paths=fit_inputs(tmp_path,periodic=True,move_target=move_target)
    fitted=fit(paths);trial=tmp_path/'trial-new.json';trial.write_text(json.dumps(fitted['trial']))
    preview=tmp_path/'preview'
    build_bend_preview(paths[0],paths[1],registration_path=paths[2],trial_path=trial,output_directory=preview)
    scene=preview_scene(preview,candidate_index=0,radius_angstrom=20,periodic=True)
    assert scene['contacts'] and scene['source_image_assessment']=='SELECTED_COORDINATES_DISTINCT'
    assert scene['candidate_image_assessment']=='SELECTED_COORDINATES_DISTINCT'
    assert scene['selected_candidate']['target_image']==fitted['selected_candidate']['target_image']
    op=gemmi.Op(scene['selected_candidate']['target_image']['operator_xyz'])
    cell=gemmi.UnitCell(*scene['crystal']['cell_parameters'])
    for state,filename in [('before','source.pdb'),('after','candidate.pdb')]:
        coordinates={}
        for line in (preview/filename).read_text().splitlines():
            if line.startswith('ATOM'):
                coordinates[(line[21].strip(),int(line[22:26]),line[26].strip(),line[12:16].strip())]=[float(line[i:i+8]) for i in (30,38,46)]
        for atom in scene['atoms']:
            site=atom['site'];xyz=coordinates[(site['chain'],site['residue_number'],site['insertion_code'],atom['atom_name'])]
            if atom['instance']=='target':
                f=cell.fractionalize(gemmi.Position(*xyz));xyz=list(cell.orthogonalize(gemmi.Fractional(*op.apply_to_xyz(list(f)))))
            assert atom[state]==pytest.approx(xyz,abs=1e-10)
    assert all(scene['atoms'][i]['atom_name']=="O3'" for edge in scene['traces'] for i in edge)


def test_view_preserves_window_with_unmapped_unrelated_route(tmp_path):
    from nasolve.construct_registration import build_construct_registration
    from nasolve.model_assessment import inspect_pdb
    from .test_construct_registration import target
    from .test_topostitch_preview import digest,change_trial
    paths=setup_preview(tmp_path)
    codes={f'{chain}:{i}':code for chain,n,code in [('A',8,'DA'),('B',6,'DT')] for i in range(1,n+1)}
    registry=build_construct_registration(inspect_pdb(paths[0],polymer_ligand_codes={'DA','DT'}),
        target(*codes.items(),('U:1','DA'),('U:2','DT')),
        {'copy_1':{s:s for s in codes}},source='partial-view-fixture')
    paths[2].write_text(json.dumps(registry))
    manifest=json.loads(paths[1].read_text())
    manifest['strands'].append(dict(strand_id='unmapped',sites=['U:1','U:2'],
        five_prime_boundary='unknown',three_prime_boundary='unknown'))
    manifest['registration_sha256']=digest(paths[2].read_bytes())
    paths[1].write_text(json.dumps(manifest))
    change_trial(paths,registration_file_sha256=digest(paths[2].read_bytes()),
        discovery_file_sha256=digest(paths[1].read_bytes()))
    preview=tmp_path/'preview';build(paths,preview)
    scene=preview_scene(preview)
    assert scene['traces'] and scene['atoms']
    assert all(a['site']['chain'] in {'A','B'} for a in scene['atoms'])
