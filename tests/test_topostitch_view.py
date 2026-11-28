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
    assert all(isinstance(a[state],list) for a in scene['atoms'] for state in ('before','after'))
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


def test_missing_packaged_template_leaves_no_empty_output(tmp_path,monkeypatch):
    import nasolve.topostitch_view as module
    paths=setup_preview(tmp_path);preview=tmp_path/'preview';build(paths,preview)
    before={p.name:p.read_bytes() for p in preview.iterdir()}
    monkeypatch.setattr(module,'files',lambda package:tmp_path/'missing-installed-package')
    out=tmp_path/'view.html'
    with pytest.raises(FileNotFoundError):write_preview_view(preview,out)
    assert not out.exists()
    assert {p.name:p.read_bytes() for p in preview.iterdir()}==before


# Reuse the genuine checkpoint/recut synthetic fixture; no second run factory.
from tests.test_topostitch_checkpoint import recut_child,refresh_recut


def refreshed_view(case,preview,output,**overrides):
    from hashlib import sha256
    from nasolve.topostitch_view import write_checkpoint_recut_view
    options=case[3]
    args=dict(expected_refresh_sha256=sha256((preview/'checkpoint-refresh.json').read_bytes()).hexdigest(),
        registry_reader=options['registry_reader'],closest_image_reader=options['closest_image_reader'],
        image_separation_angstrom=options['image_separation_angstrom'])
    return write_checkpoint_recut_view(case[0],case[1],preview,output,**dict(args,**overrides))


def test_refined_cut_view_shows_verified_child_without_inherited_review(recut_child,tmp_path):
    from nasolve.topostitch_view import representative_scene
    preview=tmp_path/'child-preview';report=refresh_recut(recut_child,preview)
    before={p:p.read_bytes() for root in (recut_child[0].parent.parent,recut_child[1],preview) for p in root.rglob('*') if p.is_file()}
    output=tmp_path/'child.html';scene=refreshed_view(recut_child,preview,output)
    assert scene['atoms']==representative_scene(preview,backbone_intent=True)['atoms']
    checked=scene['verified_checkpoint_refresh']
    assert checked['parent_checkpoint_id']=='postmr' and checked['child_checkpoint_id']=='refine-001'
    assert checked['review_state']=='UNREVIEWED' and not checked['review_inherited']
    assert checked['max_atom_shift_angstrom']==report['graph_descent']['max_atom_shift_angstrom']
    assert not checked['selection_applied'] and not checked['native_restart_qualified']
    html=output.read_text();payload=re.search(r'<script id="scene" type="application/json">(.*?)</script>',html,re.S)
    assert json.loads(payload.group(1))==scene
    assert 'Cut on refined model' in html and str(tmp_path) not in html
    assert all(p.read_bytes()==value for p,value in before.items())
    with pytest.raises(FileExistsError):refreshed_view(recut_child,preview,output)
    with pytest.raises(ValueError,match='outside'):refreshed_view(recut_child,preview,preview/'nested.html')


def test_refined_cut_view_refuses_stale_binding_and_drift_before_emission(recut_child,tmp_path,monkeypatch):
    from nasolve import topostitch_view as owner
    preview=tmp_path/'child-preview';refresh_recut(recut_child,preview)
    output=tmp_path/'refused.html'
    with pytest.raises(ValueError,match='refresh'):
        refreshed_view(recut_child,preview,output,expected_refresh_sha256='0'*64)
    assert not output.exists()
    original=owner.representative_scene
    def drift(*args,**kwargs):
        scene=original(*args,**kwargs)
        p=recut_child[1]/'proposal.json';p.write_bytes(p.read_bytes()+b'\n')
        return scene
    monkeypatch.setattr(owner,'representative_scene',drift)
    with pytest.raises(ValueError,match='changed'):
        refreshed_view(recut_child,preview,output)
    assert not output.exists()


def refreshed_choice(case,tmp_path):
    from nasolve.topostitch_recut_bundle import build_relabel_preview
    from nasolve.topostitch_view import representative_comparison
    preview=tmp_path/'refreshed';refresh_recut(case,preview)
    proposal=json.loads((preview/'proposal.json').read_bytes())
    proposal['kind']='topostitch-representative-proposal'
    proposal.pop('selected_edge_ids');proposal.pop('anchor_node_ids');proposal['node_images']=[]
    request=tmp_path/'alternative.json';request.write_text(json.dumps(proposal))
    other=tmp_path/'alternative'
    build_relabel_preview(preview/'source.pdb',preview/'discovery.json',
        registration_path=preview/'registration.json',proposal_path=request,output_directory=other)
    comparison=representative_comparison([preview,other],backbone_intent=True)
    note=dict(schema_version=1,kind='topostitch-cut-preference',
        **{key:comparison[key] for key in ('comparison_sha256','source_model_sha256','registered_graph_sha256')},
        decision='prefer_cut',preferred_preview_receipt_sha256=comparison['alternatives'][1]['scene']['preview_receipt_sha256'],
        comment='Inspect the alternative </script> before any decision.')
    preference=tmp_path/'preference.json';preference.write_text(json.dumps(note))
    return preview,other,preference,comparison


def test_verified_child_comparison_reopens_preference_without_approval(recut_child,tmp_path):
    preview,other,preference,plain=refreshed_choice(recut_child,tmp_path)
    before={p:p.read_bytes() for root in (recut_child[0].parent.parent,recut_child[1],preview,other) for p in root.rglob('*') if p.is_file()}
    output=tmp_path/'comparison.html'
    scene=refreshed_view(recut_child,preview,output,comparison_directories=[other],preference_path=preference)
    assert scene['comparison_sha256']==plain['comparison_sha256']
    assert not scene['selection_applied'] and not scene['graphical_review_recorded']
    for i,row in enumerate(scene['alternatives']):
        assert row['scene']['atoms']==plain['alternatives'][i]['scene']['atoms']
        observed=row['scene']['verified_checkpoint_refresh']
        assert observed['child_checkpoint_id']=='refine-001'
        assert observed['cut_relation']==('retained_parent_cut' if i==0 else 'alternative_same_child')
        assert observed['refreshed_preview_sha256']==plain['alternatives'][0]['scene']['preview_receipt_sha256']
        assert observed['review_state']=='UNREVIEWED' and not observed['scientific_acceptance']
    html=output.read_text();note=json.loads(re.search(r'<script id="preference" type="application/json">(.*?)</script>',html,re.S).group(1))
    assert note['decision']=='prefer_cut' and not note['reviewer_authenticated']
    assert not note['checkpoint_selection_applied'] and not note['runtime_authority']
    assert note['preferred_preview_receipt_sha256']==plain['alternatives'][1]['scene']['preview_receipt_sha256']
    assert 'alternative_same_child' in html and '</script> before' not in html
    assert str(tmp_path) not in html
    assert all(p.read_bytes()==raw for p,raw in before.items())


@pytest.mark.parametrize('bad',['wrong_source','duplicate','inside_alternative','preference_without_comparison','wrong_preference'])
def test_verified_child_choice_refuses_invalid_context(recut_child,tmp_path,bad):
    preview,other,preference,_=refreshed_choice(recut_child,tmp_path)
    output=tmp_path/'refused.html';kwargs=dict(comparison_directories=[other],preference_path=preference)
    if bad=='wrong_source':kwargs['comparison_directories']=[recut_child[1]]
    if bad=='duplicate':kwargs['comparison_directories']=[preview]
    if bad=='inside_alternative':output=other/'refused.html'
    if bad=='preference_without_comparison':kwargs['comparison_directories']=[]
    if bad=='wrong_preference':
        note=json.loads(preference.read_text());note['comparison_sha256']='0'*64;preference.write_text(json.dumps(note))
    with pytest.raises(ValueError):refreshed_view(recut_child,preview,output,**kwargs)
    assert not output.exists()


@pytest.mark.parametrize('drift',['alternative','preference','selection'])
def test_verified_child_choice_rechecks_after_render(recut_child,tmp_path,monkeypatch,drift):
    from nasolve import topostitch_view as owner,checkpoints
    preview,other,preference,_=refreshed_choice(recut_child,tmp_path);render=owner._html
    def changed(*args,**kwargs):
        result=render(*args,**kwargs)
        if drift=='selection':checkpoints.select_checkpoint(recut_child[0],'refine-001')
        else:
            p=preference if drift=='preference' else other/'proposal.json'
            p.write_bytes(p.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(owner,'_html',changed)
    output=tmp_path/'refused.html'
    with pytest.raises(ValueError,match='changed|context'):
        refreshed_view(recut_child,preview,output,comparison_directories=[other],preference_path=preference)
    assert not output.exists()


def test_verified_child_choice_relocates_without_original_paths(recut_child,tmp_path):
    preview,other,preference,_=refreshed_choice(recut_child,tmp_path)
    before=refreshed_view(recut_child,preview,tmp_path/'before.html',comparison_directories=[other],preference_path=preference)
    old=recut_child[0].parent.parent;moved=tmp_path/'moved-dataset';shutil.move(old,moved)
    parent=tmp_path/'moved-parent';shutil.move(recut_child[1],parent)
    fresh=tmp_path/'moved-refresh';shutil.move(preview,fresh)
    alt=tmp_path/'moved-alternative';shutil.move(other,alt)
    note=tmp_path/'moved-note.json';shutil.move(preference,note)
    run=moved/'AutoMR'/recut_child[0].name;case=(run,parent,run/'child.pdb',recut_child[3])
    after=refreshed_view(case,fresh,tmp_path/'after.html',comparison_directories=[alt],preference_path=note)
    assert before==after and (tmp_path/'before.html').read_bytes()==(tmp_path/'after.html').read_bytes()
    assert not any(p.exists() for p in (old,recut_child[1],preview,other,preference))


def installed_image_case(case):
    """Reuse the existing child fixture with the actual installed image owners."""
    from nasolve.topostitch_images import closest_atom_images
    from nasolve.cif_phosphate_image import PDB_IMAGE_SEPARATION_A
    return (*case[:3],dict(case[3],closest_image_reader=closest_atom_images,
                          image_separation_angstrom=PDB_IMAGE_SEPARATION_A))


def test_checkpoint_view_cli_reopens_relocated_choice_without_changing_current(recut_child,tmp_path,capsys):
    from hashlib import sha256
    from nasolve import checkpoints
    from nasolve.topostitch_view import main
    case=installed_image_case(recut_child)
    preview,other,preference,plain=refreshed_choice(case,tmp_path)
    digest=sha256((preview/'checkpoint-refresh.json').read_bytes()).hexdigest()
    old=case[0].parent.parent;moved=tmp_path/'moved-run-input';shutil.move(old,moved)
    parent=tmp_path/'moved-parent';shutil.move(case[1],parent)
    fresh=tmp_path/'moved-refresh';shutil.move(preview,fresh)
    alternative=tmp_path/'moved-alternative';shutil.move(other,alternative)
    note=tmp_path/'moved-note.json';shutil.move(preference,note)
    assert not any(p.exists() for p in (old,case[1],preview,other,preference))
    run=moved/'AutoMR'/case[0].name;out=tmp_path/'child-choice.html'
    frozen={p:p.read_bytes() for root in (moved,parent,fresh,alternative) for p in root.rglob('*') if p.is_file()}
    frozen[note]=note.read_bytes()
    assert main([str(fresh),'--run',str(run),'--parent-preview',str(parent),
        '--refresh-sha256',digest,'--compare',str(alternative),'--preference',str(note),'--out',str(out)])==0
    html=out.read_text();scene=json.loads(re.search(r'<script id="scene" type="application/json">(.*?)</script>',html,re.S).group(1))
    assert scene['comparison_sha256']==plain['comparison_sha256']
    for row in scene['alternatives']:
        context=row['scene']['verified_checkpoint_refresh']
        assert context['child_checkpoint_id']=='refine-001'
        assert context['current_checkpoint_id']=='postmr'
        assert context['review_state']=='UNREVIEWED' and not context['selection_applied']
    assert 'Viewed:' in html and 'Current at creation:' in html
    assert checkpoints.read_registry(run)[1]['current']=='postmr'
    assert all(p.read_bytes()==raw for p,raw in frozen.items())
    assert str(tmp_path) not in html
    console=capsys.readouterr().out
    assert 'refine-001' in console and 'postmr' in console and 'unchanged' in console


@pytest.mark.parametrize('options',[
    ['--run','run'], ['--parent-preview','parent'], ['--refresh-sha256','0'*64],
    ['--run','run','--parent-preview','parent'],
    ['--run','run','--parent-preview','parent','--refresh-sha256','0'*64,'--periodic'],
    ['--run','run','--parent-preview','parent','--refresh-sha256','0'*64,'--cedar-source','neighbor'],
    ['--run','run','--parent-preview','parent','--refresh-sha256','0'*64,'--export-sha256','0'*64],
])
def test_checkpoint_view_cli_requires_complete_unmixed_context(tmp_path,monkeypatch,capsys,options):
    from nasolve import topostitch_view as view
    def forbidden(*args,**kwargs):raise AssertionError('Do not read or render an incomplete request')
    monkeypatch.setattr(view,'write_checkpoint_recut_view',forbidden)
    monkeypatch.setattr(view,'write_preview_view',forbidden)
    out=tmp_path/'none.html'
    with pytest.raises(SystemExit) as exc:view.main(['missing','--out',str(out),*options])
    assert exc.value.code==2 and not out.exists()
    assert 'unrecognized arguments' not in capsys.readouterr().err


@pytest.mark.parametrize('fault',['digest','current','owner'])
def test_checkpoint_view_cli_refuses_stale_or_unverified_run(recut_child,tmp_path,monkeypatch,capsys,fault):
    from hashlib import sha256
    from nasolve import checkpoints
    from nasolve.topostitch_view import main
    case=installed_image_case(recut_child);preview=tmp_path/'fresh'
    refresh_recut(case,preview)
    digest=sha256((preview/'checkpoint-refresh.json').read_bytes()).hexdigest()
    if fault=='digest':digest='0'*64
    elif fault=='current':checkpoints.select_checkpoint(case[0],'refine-001')
    else:
        def refuse(*args,**kwargs):raise ValueError('Authenticated history refused')
        monkeypatch.setattr(checkpoints,'read_registry',refuse)
    out=tmp_path/'refused.html'
    with pytest.raises(SystemExit) as exc:
        main([str(preview),'--run',str(case[0]),'--parent-preview',str(case[1]),
              '--refresh-sha256',digest,'--out',str(out)])
    assert exc.value.code==2 and not out.exists()
    error=capsys.readouterr().err
    assert 'unrecognized arguments' not in error
    if fault=='owner':assert 'Authenticated history refused' in error
