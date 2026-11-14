"""Saved representative proposals must replay from their own immutable inputs."""
from hashlib import sha256
import json
import shutil

import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_graph import build_registered_periodic_graph
from nasolve.topostitch_recut_bundle import build_relabel_preview,load_relabel_preview,main
from nasolve.topostitch_registration import _fingerprint
from tests.test_topostitch_graph import registered


def setup(tmp_path):
    model,discovery,registration,_=registered(tmp_path,rename=True)
    graph=build_registered_periodic_graph(model,discovery,registration)
    chosen=next(n for n in graph['nodes'] if n['logical_site']=='A:2')
    request=dict(schema_version=1,kind='topostitch-representative-proposal',registered_graph_sha256=graph['report_sha256'],
        node_images=[dict(node_id=chosen['node_id'],operator_xyz='y,-x,z+1/4')],extra_edges=[],
        coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000)
    proposal=tmp_path/'request.json';proposal.write_text(json.dumps(request))
    return dict(model=model,discovery=discovery,registration_path=registration,proposal_path=proposal),request


def test_bundle_keeps_sources_and_proposal_bytes_and_replays_without_model_emission(tmp_path):
    args,request=setup(tmp_path);originals={p:p.read_bytes() for p in args.values()};out=tmp_path/'preview'
    report=build_relabel_preview(**args,output_directory=out)
    assert set(p.name for p in out.iterdir())=={'source.pdb','discovery.json','registration.json','proposal.json','preview.json'}
    assert report==load_relabel_preview(out)
    assert report['observation']['registered_graph']['nodes'][1]['logical_site']=='A:2'
    assert report['workflow']==dict(execution_state='PREVIEW_BUILT',review_state='UNREVIEWED',refinement_state='NOT_ATTEMPTED')
    assert all(not report[k] for k in ('coordinates_materialized','chemical_connectivity_changed','checkpoint_created','selection_applied','runtime_authority'))
    assert all(p.read_bytes()==b for p,b in originals.items())
    assert (out/'proposal.json').read_bytes()==args['proposal_path'].read_bytes()
    assert (out/'source.pdb').read_bytes()==args['model'].read_bytes()
    for reference in report['artifacts'].values():
        assert reference['anchor']=='run' and reference['sha256']==sha256((out/reference['relative_path']).read_bytes()).hexdigest()
    assert 'absolute_path' not in json.dumps(report)


def test_bundle_replays_after_original_checkout_and_sources_are_gone(tmp_path,monkeypatch):
    original=tmp_path/'original';original.mkdir();args,_=setup(original)
    report=build_relabel_preview(**args,output_directory=original/'preview')
    moved=tmp_path/'relocated';shutil.move(original/'preview',moved);shutil.rmtree(original)
    from pathlib import Path
    opener=Path.open
    def guarded(self,*a,**kw):
        if self.resolve().is_relative_to(original):raise AssertionError('Original input lookup forbidden')
        return opener(self,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    assert load_relabel_preview(moved)==report


@pytest.mark.parametrize('field,value',[('schema_version',True),('registered_graph_sha256','a'*64),('max_atom_tests',True),('unknown','field')])
def test_invalid_requests_create_no_output(tmp_path,field,value):
    args,request=setup(tmp_path);request[field]=value;args['proposal_path'].write_text(json.dumps(request));out=tmp_path/'preview'
    with pytest.raises(ValueError):build_relabel_preview(**args,output_directory=out)
    assert not out.exists()


def test_duplicate_request_keys_and_covalent_edge_proposals_refuse(tmp_path):
    args,request=setup(tmp_path);out=tmp_path/'preview'
    args['proposal_path'].write_text(json.dumps(request)[:-1]+',"schema_version":1}')
    with pytest.raises(ValueError,match='Duplicate'):build_relabel_preview(**args,output_directory=out)
    request['extra_edges']=[dict(kind='covalent_backbone',source_site='A:1',target_site='C:1',target_operator_xyz='x,y,z')]
    args['proposal_path'].write_text(json.dumps(request))
    with pytest.raises(ValueError,match='chemistry-aware'):build_relabel_preview(**args,output_directory=out)
    assert not out.exists()


def test_input_drift_during_preparation_refuses_before_freezing(tmp_path,monkeypatch):
    args,_=setup(tmp_path)
    import nasolve.topostitch_recut_bundle as module
    original=module.preview_registered_relabel
    def changed(*a,**kw):
        result=original(*a,**kw);args['discovery'].write_bytes(args['discovery'].read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'preview_registered_relabel',changed)
    out=tmp_path/'preview'
    with pytest.raises(ValueError,match='changed during'):build_relabel_preview(**args,output_directory=out)
    assert not out.exists()


def test_existing_output_wins_before_any_new_input_is_read(tmp_path):
    out=tmp_path/'preview';out.mkdir();(out/'mine').write_text('preserve')
    with pytest.raises(FileExistsError):build_relabel_preview('absent','absent',registration_path='absent',proposal_path='absent',output_directory=out)
    assert (out/'mine').read_text()=='preserve'


@pytest.mark.parametrize('tamper',['derived','typed_derived','approval','artifact_bytes','rehashed_proposal'])
def test_changed_or_rehashed_evidence_cannot_replay(tmp_path,tamper):
    args,_=setup(tmp_path);out=tmp_path/'preview';report=build_relabel_preview(**args,output_directory=out)
    if tamper=='derived':
        observation=report['observation'];observation['proposed_points_angstrom'][0][0]+=.1
        observation['preview_sha256']=_fingerprint({k:v for k,v in observation.items() if k!='preview_sha256'})
    elif tamper=='typed_derived':report['observation']['registered_graph']['nodes'][0]['node_id']=True
    elif tamper=='approval':report['runtime_authority']=True
    elif tamper=='artifact_bytes':(out/'source.pdb').write_bytes((out/'source.pdb').read_bytes()+b'REMARK corrupted\n')
    else:
        request=json.loads((out/'proposal.json').read_text());request['node_images']=[]
        data=(json.dumps(request)+'\n').encode();(out/'proposal.json').write_bytes(data)
        report['artifacts']['proposal'].update(sha256=sha256(data).hexdigest(),size_bytes=len(data));report['proposal_sha256']=sha256(data).hexdigest()
    (out/'preview.json').write_text(json.dumps(report))
    with pytest.raises(ValueError):load_relabel_preview(out)


@pytest.mark.parametrize('field,value',[('anchor','absolute'),('relative_path','../source.pdb'),('sha256',''),('size_bytes',True)])
def test_artifact_reference_must_remain_exact_and_local(tmp_path,field,value):
    args,_=setup(tmp_path);out=tmp_path/'preview';report=build_relabel_preview(**args,output_directory=out)
    report['artifacts']['source'][field]=value;(out/'preview.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='anchored'):load_relabel_preview(out)


def test_matching_external_symlink_is_not_a_local_snapshot(tmp_path):
    args,_=setup(tmp_path);out=tmp_path/'preview';build_relabel_preview(**args,output_directory=out)
    (out/'source.pdb').unlink();(out/'source.pdb').symlink_to(args['model'])
    with pytest.raises(ValueError,match='artifact'):load_relabel_preview(out)


def test_interrupted_write_preserves_partial_evidence_without_a_complete_receipt(tmp_path,monkeypatch):
    args,_=setup(tmp_path);out=tmp_path/'preview'
    from pathlib import Path
    original=Path.open
    def failed(self,*a,**kw):
        if self==out/'registration.json' and a==('xb',):raise OSError('simulated disk failure')
        return original(self,*a,**kw)
    monkeypatch.setattr(Path,'open',failed)
    with pytest.raises(OSError,match='disk failure'):build_relabel_preview(**args,output_directory=out)
    assert (out/'source.pdb').exists() and (out/'discovery.json').exists()
    assert not (out/'preview.json').exists()
    with pytest.raises(FileExistsError):build_relabel_preview(**args,output_directory=out)


def test_cli_uses_explicit_paths_and_describes_an_unreviewed_proposal(tmp_path,capsys):
    args,_=setup(tmp_path);out=tmp_path/'preview'
    command=[str(args['model']),'--discovery',str(args['discovery']),'--registration',str(args['registration_path']),
             '--proposal',str(args['proposal_path']),'--out',str(out)]
    assert main(command)==0
    assert 'preview unreviewed' in capsys.readouterr().out
    assert load_relabel_preview(out)['runtime_authority'] is False
    with pytest.raises(SystemExit) as error:main(command)
    assert error.value.code==2


def test_artifact_drift_after_recomputation_is_detected_before_return(tmp_path,monkeypatch):
    args,_=setup(tmp_path);out=tmp_path/'preview';build_relabel_preview(**args,output_directory=out)
    import nasolve.topostitch_recut_bundle as module
    original=module._prepare
    def changed(*a,**kw):
        value=original(*a,**kw);(out/'source.pdb').write_bytes((out/'source.pdb').read_bytes()+b'REMARK late drift\n');return value
    monkeypatch.setattr(module,'_prepare',changed)
    with pytest.raises(ValueError,match='changed during replay'):load_relabel_preview(out)
