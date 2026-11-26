"""Prospective interior windows reuse registered preview/replay and motion owners."""
from hashlib import sha256
import json,shutil
import pytest
from .test_topostitch_preview import setup_preview, build, coords
from nasolve.topostitch_preview import load_bend_preview,load_bend_motion
from nasolve.topostitch_endpoint import audit_masked_endpoint
from nasolve.topostitch_view import preview_scene


def setup(tmp_path):
    paths=setup_preview(tmp_path,anisou=False,extended=True)
    t=json.loads(paths[3].read_bytes());t.update(schema_version=3,
        ordered_pairs=[[f'A:{i}',f'B:{9-i}']for i in range(3,9)],
        pair_weights=[0,.3,1,.8,.2,0],origin_pair_index=2,fixed_anchor_pairs=1,
        max_backbone_torsion_change_degrees=180)
    t.pop('window_id');paths[3].write_text(json.dumps(t));return paths


def test_two_flanks_fixed_and_full_precision_motion_replays(tmp_path):
    paths=setup(tmp_path);out=tmp_path/'preview';r=build(paths,out)
    assert r['schema_version']==3
    assert r['window']['kind']=='interior-paired-window' and r['window']['end_id']is None
    assert set(r['window']['fixed_sites'])=={'A:3','B:6','A:8','B:1'}
    original=(out/'source.pdb').read_bytes();candidate=(out/'candidate.pdb').read_bytes()
    for a,b in zip(original.splitlines(),candidate.splitlines()):
        if a.startswith(b'ATOM'):
            assert a[:30]==b[:30] and a[54:]==b[54:]
            site=a[21:22].decode()+':'+str(int(a[22:26]))
            if site not in r['window']['movable_sites']:assert a==b
    pin=sha256((out/'preview.json').read_bytes()).hexdigest()
    motion,parameters=load_bend_motion(out,expected_receipt_sha256=pin,parent_model_bytes=original)
    points=motion.mask.expand(motion.displacements(parameters))
    assert audit_masked_endpoint(original,candidate,points,movable_indices=motion.mask.indices,
        max_displacement_angstrom=motion.mask.max_displacement_angstrom)['status']=='EXACT_MASKED_SERIALIZATION'
    assert load_bend_preview(out)==r
    assert 'max_torsion_change_degrees'in r['backbone_audit']
    assert preview_scene(out)['atoms']
    assert r['geometry_validated']is False and r['runtime_authority']is False


@pytest.mark.parametrize('fault',['weight_length','fixed_weight','zero_interior','negative','nan','too_large','pair_mate','duplicate','reorder','parallel','bound','anchors','pivot','protected'])
def test_malformed_or_unsafe_interior_scope_refuses_without_output(tmp_path,fault):
    paths=setup(tmp_path);t=json.loads(paths[3].read_bytes())
    if fault=='weight_length':t['pair_weights'].pop()
    if fault=='fixed_weight':t['pair_weights'][0]=.1
    if fault=='zero_interior':t['pair_weights'][2]=0
    if fault=='negative':t['pair_weights'][2]=-.1
    if fault=='nan':t['pair_weights'][2]=float('nan')
    if fault=='too_large':t['pair_weights'][2]=1.1
    if fault=='pair_mate':t['ordered_pairs'][1][1]='B:1'
    if fault=='duplicate':t['ordered_pairs'][1]=t['ordered_pairs'][2]
    if fault=='reorder':t['ordered_pairs'][2],t['ordered_pairs'][3]=t['ordered_pairs'][3],t['ordered_pairs'][2]
    if fault=='parallel':
        d=json.loads(paths[1].read_bytes());d['strands'][1]['sites'].reverse();paths[1].write_text(json.dumps(d));t['discovery_file_sha256']=sha256(paths[1].read_bytes()).hexdigest()
    if fault=='bound':t['max_window_pairs']=5
    if fault=='anchors':t['fixed_anchor_pairs']=3
    if fault=='pivot':t['origin_pair_index']=True
    if fault=='protected':
        d=json.loads(paths[1].read_bytes());d['protected_sites']=['A:6'];paths[1].write_text(json.dumps(d));t['discovery_file_sha256']=sha256(paths[1].read_bytes()).hexdigest()
    paths[3].write_text(json.dumps(t));out=tmp_path/'preview'
    with pytest.raises((ValueError,TypeError)):build(paths,out)
    assert not out.exists()


def test_localization_does_not_permit_crossing_a_route_break(tmp_path):
    paths=setup(tmp_path);d=json.loads(paths[1].read_bytes())
    strand=d['strands'][0];strand['sites']=strand['sites'][:5]
    d['strands'].append(dict(strand_id='A-after-nick',sites=['A:6','A:7','A:8'],five_prime_boundary='chemical',three_prime_boundary='chemical'))
    paths[1].write_text(json.dumps(d));t=json.loads(paths[3].read_bytes());t['discovery_file_sha256']=sha256(paths[1].read_bytes()).hexdigest();paths[3].write_text(json.dumps(t))
    with pytest.raises(ValueError,match='consecutive|route'):build(paths,tmp_path/'preview')


def test_bounded_motion_and_stale_receipts_still_refuse(tmp_path):
    paths=setup(tmp_path);t=json.loads(paths[3].read_bytes());t['max_atom_displacement_angstrom']=.001;paths[3].write_text(json.dumps(t))
    with pytest.raises(ValueError,match='displacement'):build(paths,tmp_path/'no-output')
    t['max_atom_displacement_angstrom']=30;paths[3].write_text(json.dumps(t));out=tmp_path/'preview';build(paths,out)
    r=json.loads((out/'preview.json').read_bytes());r['site_weights']['A:4']=.9;(out/'preview.json').write_text(json.dumps(r))
    with pytest.raises(ValueError,match='reproduce'):load_bend_preview(out)


def test_relocation_after_original_paths_removed(tmp_path):
    source=tmp_path/'source';source.mkdir();paths=setup(source);out=tmp_path/'preview';r=build(paths,out)
    pin=sha256((out/'preview.json').read_bytes()).hexdigest();expected=load_bend_motion(out,expected_receipt_sha256=pin)
    shutil.rmtree(source);moved=tmp_path/'moved';out.rename(moved)
    assert load_bend_preview(moved)==r
    actual=load_bend_motion(moved,expected_receipt_sha256=pin)
    assert actual==expected


def test_changed_parent_snapshot_refused_before_motion(tmp_path):
    paths=setup(tmp_path);out=tmp_path/'preview';build(paths,out)
    pin=sha256((out/'preview.json').read_bytes()).hexdigest()
    changed=(out/'source.pdb').read_bytes()+b'REMARK different parent\n'
    with pytest.raises(ValueError,match='Current parent bytes differ'):
        load_bend_motion(out,expected_receipt_sha256=pin,parent_model_bytes=changed)


@pytest.mark.parametrize('interior', [False, True])
def test_window_inspection_precedes_rendering_and_matches_preview(tmp_path, monkeypatch, interior):
    from nasolve import topostitch_preview as preview
    paths=setup(tmp_path) if interior else setup_preview(tmp_path,anisou=False,extended=True)
    snapshots={p:p.read_bytes() for p in paths[:4]}
    with monkeypatch.context() as m:
        def forbidden(*args,**kwargs):
            raise AssertionError('Window review must not render or audit a candidate')
        m.setattr(preview,'_render',forbidden)
        m.setattr(preview,'_audit_links',forbidden)
        m.setattr(preview,'_plane',forbidden)
        review=preview.inspect_bend_window(paths[0],paths[1],registration_path=paths[2],trial_path=paths[3])
    assert all(p.read_bytes()==raw for p,raw in snapshots.items())
    assert set(tmp_path.iterdir())==set(paths[:4])
    assert review['status']=='WINDOW_FOR_REVIEW'
    assert review['candidate_written'] is review['geometry_feasibility_evaluated'] is review['runtime_authority'] is False
    assert str(tmp_path) not in json.dumps(review)
    made=build(paths,tmp_path/'preview')
    assert review['window']==made['window']
    lines=[l for l in paths[0].read_text().splitlines() if l.startswith(('ATOM  ','HETATM'))]
    movable=set(made['window']['movable_sites']);anchors=set(made['window']['fixed_sites'])
    expected=[i for i,l in enumerate(lines) if l[21]+':'+str(int(l[22:26])) in movable]
    fixed=[i for i,l in enumerate(lines) if l[21]+':'+str(int(l[22:26])) in anchors]
    assert review['movable_atom_indices']==expected
    assert review['fixed_anchor_atom_indices']==fixed
    assert sorted(review['fixed_context_atom_indices']+expected)==list(range(len(lines)))
    assert review['trial_file_sha256']==sha256(paths[3].read_bytes()).hexdigest()
    assert review['backbone_links']


def test_window_inspection_does_not_claim_displacement_feasibility(tmp_path):
    from nasolve import topostitch_preview as preview
    paths=setup(tmp_path);t=json.loads(paths[3].read_bytes());t['max_atom_displacement_angstrom']=.001
    paths[3].write_text(json.dumps(t))
    report=preview.inspect_bend_window(paths[0],paths[1],registration_path=paths[2],trial_path=paths[3])
    assert report['geometry_feasibility_evaluated'] is False
    with pytest.raises(ValueError,match='displacement'):build(paths,tmp_path/'too-far')
    assert not (tmp_path/'too-far').exists()


def test_window_inspection_refuses_source_drift_during_mapping(tmp_path,monkeypatch):
    from nasolve import topostitch_preview as preview
    paths=setup(tmp_path);original=preview._mapped_residues
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        paths[0].write_bytes(paths[0].read_bytes()+b'REMARK changed while reading\n')
        return result
    monkeypatch.setattr(preview,'_mapped_residues',changed)
    with pytest.raises(ValueError,match='changed while being read'):
        preview.inspect_bend_window(paths[0],paths[1],registration_path=paths[2],trial_path=paths[3])


def test_window_inspection_relocates_without_original_paths(tmp_path):
    from nasolve import topostitch_preview as preview
    source=tmp_path/'source';source.mkdir();paths=setup(source)
    expected=preview.inspect_bend_window(paths[0],paths[1],registration_path=paths[2],trial_path=paths[3])
    moved=tmp_path/'moved';source.rename(moved)
    shifted=[moved/p.name for p in paths[:4]]
    assert preview.inspect_bend_window(shifted[0],shifted[1],registration_path=shifted[2],trial_path=shifted[3])==expected


def test_normal_preview_cli_can_inspect_without_creating_output(tmp_path,capsys):
    from nasolve import topostitch_preview as preview
    paths=setup(tmp_path)
    args=[str(paths[0]),str(paths[1]),'--registration',str(paths[2]),'--trial',str(paths[3]),'--inspect-window']
    assert preview.main(args)==0
    report=json.loads(capsys.readouterr().out)
    assert report['kind']=='topostitch-window-inspection' and report['candidate_written'] is False
    assert set(tmp_path.iterdir())==set(paths[:4])
    with pytest.raises(SystemExit) as error:preview.main(args+['--out',str(tmp_path/'bad')])
    assert error.value.code==2 and not (tmp_path/'bad').exists()


@pytest.mark.parametrize('complete,expected', [(False,'DUPLEX_PARTNERS_UNSPECIFIED'),(True,'NO_EDITABLE_WINDOWS')])
def test_unspecified_pairs_have_an_explicit_window_status(tmp_path,complete,expected):
    from nasolve.topostitch_discovery import plan_editable_windows
    from nasolve.topostitch_inspect import load_registered_end_assignments
    paths=setup(tmp_path);d=json.loads(paths[1].read_bytes())
    d['duplex_pairs']=[];d['pairing_inventory_complete']=complete;paths[1].write_text(json.dumps(d))
    _,ends,_,mapping=load_registered_end_assignments(paths[0],paths[1],paths[2])
    report=plan_editable_windows(mapping['discovery_assessment'],max_base_pairs=6,fixed_anchor_pairs=1)
    assert not ends and report['ends']==[]
    assert report['planning_status']==expected
    assert report['selected_window'] is None and report['runtime_authority'] is False
