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


def test_describe_graph_without_proposal_is_read_only_and_has_cli_parity(tmp_path,capsys,monkeypatch):
    from nasolve import topostitch_recut_bundle as module
    args,_=setup(tmp_path);args.pop('proposal_path');before={p:p.read_bytes() for p in tmp_path.iterdir()};names=set(tmp_path.iterdir())
    monkeypatch.setattr(module,'preview_registered_relabel',lambda *a,**k:pytest.fail('Graph description must not build a cut'))
    report=module.describe_relabel_graph(**args)
    assert report['kind']=='topostitch-registered-graph-description' and report['status']=='GRAPH_DESCRIPTION_ONLY'
    assert report['registered_graph']==build_registered_periodic_graph(args['model'],args['discovery'],args['registration_path'])
    assert report['proposal_binding'] is None and not report['cut_selection_validated'] and not report['runtime_authority']
    assert main([str(args['model']),'--discovery',str(args['discovery']),'--registration',str(args['registration_path']),'--describe-graph'])==0
    assert json.loads(capsys.readouterr().out)==report
    assert set(tmp_path.iterdir())==names and all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('binding',['MATCH','MISMATCH'])
def test_graph_description_reports_requested_hash_without_rewriting_it(tmp_path,binding):
    from nasolve.topostitch_recut_bundle import describe_relabel_graph
    args,request=setup(tmp_path)
    if binding=='MISMATCH':request['registered_graph_sha256']='0'*64;args['proposal_path'].write_text(json.dumps(request))
    original=args['proposal_path'].read_bytes();report=describe_relabel_graph(**args)
    check=report['proposal_binding']
    assert check==dict(status=binding,kind=request['kind'],schema_version=1,proposal_sha256=sha256(original).hexdigest(),requested_graph_sha256=request['registered_graph_sha256'],actual_graph_sha256=report['registered_graph']['report_sha256'])
    assert args['proposal_path'].read_bytes()==original and not report['cut_selection_validated']
    if binding=='MISMATCH':
        with pytest.raises(ValueError,match='checksum'):build_relabel_preview(**args,output_directory=tmp_path/'bad')
        assert not (tmp_path/'bad').exists()


def test_graph_description_uses_explicit_boundary_declarations(tmp_path):
    from tests.test_topostitch_continuations import setup as connected,request as proposal
    from nasolve.topostitch_recut_bundle import describe_relabel_graph
    paths,links=connected(tmp_path);args,bound,_=proposal(paths,links,forest=True)
    report=describe_relabel_graph(**args)
    assert report['registered_graph']==bound and report['proposal_binding']['status']=='MATCH'
    assert report['registered_graph']['declared_continuations'][0]['source_site']=='A:4'
    request=json.loads(args['proposal_path'].read_text());request['backbone_continuations'][0]['source_site']='A:2';args['proposal_path'].write_text(json.dumps(request))
    with pytest.raises(ValueError,match='3-prime'):describe_relabel_graph(**args)


@pytest.mark.parametrize('change',['unknown_field','schema_bool','duplicate_key'])
def test_describe_graph_reuses_strict_request_envelope(tmp_path,change):
    from nasolve.topostitch_recut_bundle import describe_relabel_graph
    args,request=setup(tmp_path)
    if change=='unknown_field':request['surprise']=True
    if change=='schema_bool':request['schema_version']=True
    text=json.dumps(request)
    if change=='duplicate_key':text=text[:-1]+',"schema_version":1}'
    args['proposal_path'].write_text(text)
    with pytest.raises(ValueError):describe_relabel_graph(**args)


def test_matching_graph_does_not_validate_a_bad_forest_selection(tmp_path):
    from tests.test_topostitch_forest_bundle import setup as forest
    from nasolve.topostitch_recut_bundle import describe_relabel_graph
    args,request,_=forest(tmp_path);request['selected_edge_ids']=['not-an-edge'];args['proposal_path'].write_text(json.dumps(request))
    report=describe_relabel_graph(**args)
    assert report['proposal_binding']['status']=='MATCH' and report['cut_selection_validated'] is False
    with pytest.raises(ValueError):build_relabel_preview(**args,output_directory=tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


@pytest.mark.parametrize('field',['discovery','proposal_path'])
def test_graph_description_rejects_input_drift(tmp_path,monkeypatch,field):
    from nasolve import topostitch_graph as graph,topostitch_recut_bundle as module
    args,_=setup(tmp_path);original=graph.build_registered_periodic_graph
    def changed(*a,**kw):
        result=original(*a,**kw);args[field].write_bytes(args[field].read_bytes()+b'\n');return result
    monkeypatch.setattr(graph,'build_registered_periodic_graph',changed)
    with pytest.raises(ValueError,match='changed during'):module.describe_relabel_graph(**args)


@pytest.mark.parametrize('mode',['describe_with_out','preview_without_out','preview_without_proposal'])
def test_graph_cli_modes_cannot_silently_write_or_build(tmp_path,mode):
    args,_=setup(tmp_path);out=tmp_path/'must-not-exist';argv=[str(args['model']),'--discovery',str(args['discovery']),'--registration',str(args['registration_path'])]
    if mode=='describe_with_out':argv+=['--describe-graph','--out',str(out)]
    elif mode=='preview_without_out':argv+=['--proposal',str(args['proposal_path'])]
    else:argv+=['--out',str(out)]
    with pytest.raises(SystemExit) as exc:main(argv)
    assert exc.value.code==2 and not out.exists()


def test_graph_description_relocates_without_source_path_lookup(tmp_path,monkeypatch):
    from pathlib import Path
    from nasolve.topostitch_recut_bundle import describe_relabel_graph
    original=tmp_path/'original';original.mkdir();args,_=setup(original);expected=describe_relabel_graph(**args)
    moved=tmp_path/'moved';shutil.move(original,moved);new={k:moved/p.name for k,p in args.items()};opener=Path.open
    def guarded(self,*a,**kw):
        if self.resolve().is_relative_to(original):raise AssertionError('Original path lookup')
        return opener(self,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    assert describe_relabel_graph(**new)==expected


def test_saved_frame_reproduces_every_atom_and_explicit_reverse_order(tmp_path):
    from nasolve import topostitch_recut_bundle as bundle
    from nasolve.topostitch_transport import ReferenceFrame
    args,_=setup(tmp_path);out=tmp_path/'preview';packet=build_relabel_preview(**args,output_directory=out)
    frozen={p:p.read_bytes() for p in out.iterdir()};digest=sha256(frozen[out/'preview.json']).hexdigest()
    frame=bundle.load_relabel_reference_frame(out,expected_receipt_sha256=digest)
    atoms=packet['observation']['source_orbit_observation']['atoms'];points=[a['position_angstrom'] for a in atoms]
    expected=packet['observation']['proposed_points_angstrom'];order=list(reversed(range(len(atoms))))
    assert isinstance(frame,ReferenceFrame) and frame.context_sha256==digest
    assert [json.loads(label) for label in frame.source_labels]==[a['identity'] for a in atoms]
    assert frame.order==tuple(range(len(atoms)))
    reverse=frame.reindex(order)
    moved=reverse.to_representatives(points,source_labels=frame.source_labels,context_sha256=digest)
    for actual,i in zip(moved,order):assert actual==pytest.approx(expected[i],abs=1e-10)
    restored=reverse.to_source(moved,atom_labels=reverse.atom_labels,context_sha256=digest)
    for actual,want in zip(restored,points):assert actual==pytest.approx(want,abs=1e-10)
    fixed=packet['observation']['fixed_atom_indices'];assert fixed
    assert all(frame.images[i].apply(points[i])==tuple(points[i]) for i in fixed)
    tensors=[(.1,.2,.3,.01,.02,.03)]*len(atoms)
    rotated=reverse.tensors_to_representatives(tensors,source_labels=frame.source_labels,context_sha256=digest)
    back=reverse.tensors_to_source(rotated,atom_labels=reverse.atom_labels,context_sha256=digest)
    for actual,want in zip(back,tensors):assert actual==pytest.approx(want,abs=1e-12)
    assert set(out.iterdir())==set(frozen) and all(p.read_bytes()==b for p,b in frozen.items())


@pytest.mark.parametrize('expected',[None,True,'','f'*63,'A'*64,'0'*64])
def test_saved_frame_requires_exact_expected_receipt(tmp_path,expected):
    from nasolve import topostitch_recut_bundle as bundle
    args,_=setup(tmp_path);out=tmp_path/'preview';build_relabel_preview(**args,output_directory=out)
    with pytest.raises(ValueError,match='receipt'):
        bundle.load_relabel_reference_frame(out,expected_receipt_sha256=expected)


def test_saved_frame_survives_relocation_without_original_sources(tmp_path,monkeypatch):
    from pathlib import Path
    from nasolve import topostitch_recut_bundle as bundle
    original=tmp_path/'original';original.mkdir();args,_=setup(original);out=original/'preview'
    build_relabel_preview(**args,output_directory=out);digest=sha256((out/'preview.json').read_bytes()).hexdigest()
    expected=bundle.load_relabel_reference_frame(out,expected_receipt_sha256=digest)
    moved=tmp_path/'moved';shutil.move(out,moved);shutil.rmtree(original)
    opener=Path.open
    def guarded(self,*a,**k):
        if self.is_relative_to(original):pytest.fail('Original source lookup')
        return opener(self,*a,**k)
    monkeypatch.setattr(Path,'open',guarded)
    assert bundle.load_relabel_reference_frame(moved,expected_receipt_sha256=digest)==expected


def test_saved_frame_rejects_changed_source_even_with_original_receipt(tmp_path):
    from nasolve import topostitch_recut_bundle as bundle
    args,_=setup(tmp_path);out=tmp_path/'preview';build_relabel_preview(**args,output_directory=out)
    digest=sha256((out/'preview.json').read_bytes()).hexdigest()
    with (out/'source.pdb').open('ab') as stream:stream.write(b'REMARK different source\n')
    with pytest.raises(ValueError):bundle.load_relabel_reference_frame(out,expected_receipt_sha256=digest)


def test_saved_frame_refuses_drift_during_transform_compilation(tmp_path,monkeypatch):
    from nasolve import topostitch_recut_bundle as bundle,topostitch_transport as transport
    args,_=setup(tmp_path);out=tmp_path/'preview';build_relabel_preview(**args,output_directory=out)
    digest=sha256((out/'preview.json').read_bytes()).hexdigest();original=transport.crystallographic_image
    # Replay uses the recut module's existing import; this hook targets the new boundary.
    def changed(*a,**k):
        value=original(*a,**k)
        with (out/'proposal.json').open('ab') as stream:stream.write(b' ')
        return value
    monkeypatch.setattr(transport,'crystallographic_image',changed)
    with pytest.raises(ValueError,match='changed'):
        bundle.load_relabel_reference_frame(out,expected_receipt_sha256=digest)


def test_saved_frame_checks_compiled_points_against_independent_packet(tmp_path,monkeypatch):
    from nasolve import topostitch_recut_bundle as bundle,topostitch_transport as transport
    args,_=setup(tmp_path);out=tmp_path/'preview';build_relabel_preview(**args,output_directory=out)
    digest=sha256((out/'preview.json').read_bytes()).hexdigest()
    monkeypatch.setattr(transport,'crystallographic_image',lambda *a,**k:transport.IDENTITY_IMAGE)
    with pytest.raises(ValueError,match='coordinates'):
        bundle.load_relabel_reference_frame(out,expected_receipt_sha256=digest)


def test_saved_frame_keeps_unregistered_water_with_exact_identity(tmp_path):
    from .helpers import pdb_record
    from nasolve import topostitch_recut_bundle as bundle
    args,request=setup(tmp_path);model=args['model'];reg=args['registration_path'];discovery=args['discovery']
    water=pdb_record('HETATM',999,'O','HOH','W',9,x=11,y=2,z=3,occupancy=.5)
    water=water[:16]+'A'+water[17:26]+'B'+water[27:]
    model.write_text(model.read_text().replace('END\n','')+water+'END\n')
    registration=json.loads(reg.read_bytes());registration['model']['sha256']=sha256(model.read_bytes()).hexdigest();reg.write_text(json.dumps(registration))
    value=json.loads(discovery.read_bytes());value['model_sha256']=registration['model']['sha256'];value['registration_sha256']=sha256(reg.read_bytes()).hexdigest();discovery.write_text(json.dumps(value))
    request['registered_graph_sha256']=build_registered_periodic_graph(model,discovery,reg)['report_sha256']
    args['proposal_path'].write_text(json.dumps(request));out=tmp_path/'preview';packet=build_relabel_preview(**args,output_directory=out)
    digest=sha256((out/'preview.json').read_bytes()).hexdigest();frame=bundle.load_relabel_reference_frame(out,expected_receipt_sha256=digest)
    atom=packet['observation']['source_orbit_observation']['atoms'][-1]
    assert atom['record_type']=='HETATM' and atom['occupancy']==.5
    identity=json.loads(frame.source_labels[-1]);assert identity==atom['identity']
    assert identity['altloc']=='A' and identity['insertion_code']=='B' and identity['chain']=='W'
    assert frame.images[-1].apply((11.,2.,3.))==(11.,2.,3.)
    assert len(frame.source_labels)==len(packet['observation']['proposed_points_angstrom'])
