"""Selected-checkpoint provenance around existing preview/endpoint owners."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest
from nasolve import checkpoints
from tests.test_checkpoints import make_checkpoint_run
from tests.test_topostitch_preview import setup_preview, build


@pytest.fixture
def bound(tmp_path):
    source=tmp_path/'preview-input';source.mkdir()
    paths=setup_preview(source,anisou=False)
    preview=tmp_path/'preview';build(paths,preview)
    run=make_checkpoint_run(tmp_path/'run-input')
    report=json.loads((run/'report.json').read_text())
    model=Path(report['postmr']['prepared_model']);model.write_bytes(paths[0].read_bytes())
    report['postmr']['prepared_sha256']=sha256(model.read_bytes()).hexdigest()
    (run/'report.json').write_text(json.dumps(report))
    _,registry=checkpoints.initialize_registry(run)
    alternate=deepcopy(registry['checkpoints'][0]);alternate.update(id='refine-001',parent='postmr')
    registry['checkpoints'].append(alternate);checkpoints.save_registry(run,registry)
    return run,preview,sha256((preview/'preview.json').read_bytes()).hexdigest()


def load(bound,**kwargs):
    from nasolve.topostitch_checkpoint import load_checkpoint_bend_motion
    run,preview,pin=bound
    return load_checkpoint_bend_motion(run,preview,expected_checkpoint_id='postmr',expected_receipt_sha256=pin,**kwargs)


def test_saved_current_parent_binds_all_inputs_and_replays_without_writes(bound):
    run,preview,_=bound
    before={p:p.read_bytes() for root in (run.parent.parent,preview) for p in root.rglob('*') if p.is_file()}
    motion,parameters,report=load(bound)
    assert report['context']['checkpoint_id']=='postmr'
    assert report['context']['selection']=={'mode':'current','requested':None}
    assert [r['role'] for r in report['context']['inputs']]==['model','observations','restraint','restraint']
    assert report['endpoint']['status']=='EXACT_MASKED_SERIALIZATION'
    assert report['endpoint']['moved_atom_count']>0
    assert report['runtime_authority'] is False and report['locking'] is False
    assert str(run) not in json.dumps(report)
    _,again,replayed=load(bound,expected_checkpoint_context_sha256=report['context_sha256'])
    assert again==parameters and replayed==report
    assert all(p.read_bytes()==b for p,b in before.items())


def test_explicit_checkpoint_does_not_follow_current_or_bookmark_silently(bound):
    from nasolve.topostitch_checkpoint import load_checkpoint_bend_motion
    run,preview,pin=bound
    result=load_checkpoint_bend_motion(run,preview,checkpoint='refine-001',expected_checkpoint_id='refine-001',expected_receipt_sha256=pin)[2]
    assert result['context']['checkpoint_id']=='refine-001'
    assert checkpoints.read_registry(run)[1]['current']=='postmr'
    with pytest.raises(ValueError,match='checkpoint identity'):
        load(bound,checkpoint='refine-001')


def test_same_bytes_different_current_checkpoint_refused(bound):
    checkpoints.select_checkpoint(bound[0],'refine-001')
    with pytest.raises(ValueError,match='checkpoint identity'):load(bound)


@pytest.mark.parametrize('change',['model','observations','restraint','phase'])
def test_changed_inherited_input_is_not_consumed(bound,change):
    run,_,_=bound
    _,registry=checkpoints.read_registry(run);parent=registry['checkpoints'][0]
    if change=='phase':
        phase=run/'phase.mtz';phase.write_bytes(b'phase input')
        parent['phases']={'anchor':'run','relative_path':'phase.mtz','sha256':sha256(phase.read_bytes()).hexdigest(),'size':phase.stat().st_size}
        checkpoints.save_registry(run,registry)
    inherited=checkpoints.inherited_paths(parent,run)
    path=inherited['restraints'][0] if change=='restraint' else inherited['phases' if change=='phase' else change]
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises((ValueError,checkpoints.CheckpointError)):load(bound)


@pytest.mark.parametrize('change',['restraint_order','registry_metadata','report_intent','rebound_model'])
def test_dispatch_context_pin_detects_rebound_or_metadata_changes(bound,change):
    run,_,_=bound;pin=load(bound)[2]['context_sha256']
    _,registry=checkpoints.read_registry(run)
    if change=='restraint_order':registry['checkpoints'][0]['restraints'].reverse()
    elif change=='registry_metadata':registry['checkpoints'][0]['label']='reconsidered'
    elif change=='report_intent':
        p=run/'report.json';report=json.loads(p.read_text());report['requested_connection']='changed';p.write_text(json.dumps(report))
    else:
        parent=registry['checkpoints'][0];p=checkpoints.inherited_paths(parent,run)['model'];p.write_bytes(p.read_bytes()+b'REMARK new parent\n');parent['model'].update(sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
    checkpoints.save_registry(run,registry)
    with pytest.raises(ValueError,match='context changed'):load(bound,expected_checkpoint_context_sha256=pin)


@pytest.mark.parametrize('change',['missing_registry','legacy_registry','unusable','duplicate_id','missing_checksum','wrong_size','malformed_restraints','missing_phase'])
def test_unbound_or_ambiguous_parent_refuses_before_motion(bound,change,monkeypatch):
    from nasolve import topostitch_checkpoint as owner
    run,_,_=bound;path=checkpoints.registry_path(run);r=json.loads(path.read_text());p=r['checkpoints'][0]
    if change=='missing_registry':path.unlink()
    elif change=='legacy_registry':r['schema_version']=1
    elif change=='unusable':p['usable']=False
    elif change=='duplicate_id':r['checkpoints'].append(deepcopy(p))
    elif change=='missing_checksum':p['model'].pop('sha256')
    elif change=='wrong_size':p['observations']['size']+=1
    elif change=='malformed_restraints':p['restraints'].append('unbound.phil')
    else:p['phases']={'anchor':'run','relative_path':'missing.mtz','sha256':'a'*64,'size':1}
    if change!='missing_registry':path.write_text(json.dumps(r))
    monkeypatch.setattr(owner,'load_bend_motion',lambda *a,**k:pytest.fail('Motion loaded before parent admission'))
    with pytest.raises((ValueError,checkpoints.CheckpointError,OSError)):load(bound)


def test_parent_change_during_preview_replay_is_detected(bound,monkeypatch):
    from nasolve import topostitch_checkpoint as owner
    original=owner.load_bend_motion
    def replay(*a,**kwargs):
        result=original(*a,**kwargs)
        path=checkpoints.registry_path(bound[0]);r=json.loads(path.read_text());r['current']='refine-001';path.write_text(json.dumps(r))
        return result
    monkeypatch.setattr(owner,'load_bend_motion',replay)
    with pytest.raises(ValueError,match='checkpoint identity'):load(bound)


def test_relocated_dataset_and_preview_replay_after_original_is_gone(bound,tmp_path):
    run,preview,pin=bound;report=load(bound)[2];old_dataset=run.parent.parent
    moved=tmp_path/'moved';moved.mkdir();dataset=moved/'dataset';shutil.move(str(old_dataset),dataset)
    new_preview=moved/'preview';shutil.move(str(preview),new_preview)
    assert not old_dataset.exists() and not preview.exists()
    relocated=(dataset/'AutoMR'/run.name,new_preview,pin)
    assert load(relocated,expected_checkpoint_context_sha256=report['context_sha256'])[2]==report


def test_invalid_context_pin_fails_before_filesystem():
    from nasolve.topostitch_checkpoint import load_checkpoint_bend_motion
    with pytest.raises(ValueError,match='SHA-256'):
        load_checkpoint_bend_motion('missing','missing',expected_checkpoint_id='postmr',expected_receipt_sha256='a'*64,expected_checkpoint_context_sha256='wrong')


@pytest.mark.parametrize('role',['observations','restraint'])
def test_inherited_file_change_during_replay_is_rechecked(bound,monkeypatch,role):
    from nasolve import topostitch_checkpoint as owner
    original=owner.load_bend_motion
    def replay(*a,**kwargs):
        result=original(*a,**kwargs)
        _,r=checkpoints.read_registry(bound[0]);paths=checkpoints.inherited_paths(r['checkpoints'][0],bound[0])
        path=paths['restraints'][0] if role=='restraint' else paths[role]
        path.write_bytes(path.read_bytes()+b'changed during replay')
        return result
    monkeypatch.setattr(owner,'load_bend_motion',replay)
    with pytest.raises(checkpoints.CheckpointError,match='changed after'):load(bound)


def test_valid_declared_phase_is_included_in_binding(bound):
    run,_,_=bound;_,r=checkpoints.read_registry(run)
    phase=run/'phases.mtz';phase.write_bytes(b'frozen phases')
    r['checkpoints'][0]['phases']={'anchor':'run','relative_path':'phases.mtz','sha256':sha256(phase.read_bytes()).hexdigest(),'size':phase.stat().st_size}
    checkpoints.save_registry(run,r)
    result=load(bound)[2]
    assert result['context']['inputs'][2]==dict(role='phases',**r['checkpoints'][0]['phases'])


def inspect_inputs(bound, **overrides):
    from nasolve.topostitch_checkpoint import inspect_checkpoint_inputs
    run, _, _ = bound
    registry = json.loads(checkpoints.registry_path(run).read_bytes())
    parent = next(r for r in registry['checkpoints'] if r['id'] == 'refine-001')
    options = dict(checkpoint='refine-001', expected_checkpoint_id='refine-001',
                   expected_model_sha256=parent['model']['sha256'], registry_reader=checkpoints.read_registry)
    return inspect_checkpoint_inputs(run, **dict(options, **overrides))


def test_refined_inputs_without_preview_preserve_roles_and_relocate(bound, tmp_path):
    run, preview, _ = bound
    shutil.rmtree(preview)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in run.parent.parent.rglob('*') if p.is_file()}
    result = inspect_inputs(bound)
    assert result['kind'] == 'topostitch-checkpoint-input-observation'
    assert result['context']['checkpoint_id'] == 'refine-001'
    assert 'preview_receipt_sha256' not in result['context']
    assert [r['role'] for r in result['context']['inputs']] == ['model', 'observations', 'restraint', 'restraint']
    assert not any(result[k] for k in ('runtime_authority', 'chemical_admission', 'motion_admission', 'native_restart_qualified', 'selection_applied', 'locking'))
    assert str(run) not in json.dumps(result)
    assert all((p.read_bytes(), p.stat().st_mtime_ns) == value for p, value in before.items())
    dataset = run.parent.parent
    moved = tmp_path/'relocated-input-dataset'
    shutil.move(str(dataset), moved)
    assert not dataset.exists()
    new = (moved/'AutoMR'/run.name, preview, None)
    assert inspect_inputs(new, expected_context_sha256=result['context_sha256']) == result


def test_checkpoint_input_reader_failure_and_different_registry_propagate(bound):
    def refuse(run):
        raise ValueError('native history is not authenticated')
    with pytest.raises(ValueError, match='history'):
        inspect_inputs(bound, registry_reader=refuse)
    def changed(run):
        path, record = checkpoints.read_registry(run)
        record['current'] = 'refine-001'
        return path, record
    with pytest.raises(ValueError, match='unchanged saved'):
        inspect_inputs(bound, registry_reader=changed)
    with pytest.raises(ValueError, match='trusted registry reader'):
        inspect_inputs(bound, registry_reader=None)


def test_checkpoint_input_model_and_context_pins_refuse_rebound_data(bound):
    with pytest.raises(ValueError, match='model'):
        inspect_inputs(bound, expected_model_sha256='0'*64)
    old = inspect_inputs(bound)
    run = bound[0]
    _, registry = checkpoints.read_registry(run)
    row = next(r for r in registry['checkpoints'] if r['id'] == 'refine-001')
    p = checkpoints.inherited_paths(row, run)['observations']
    p.write_bytes(b'replaced observed data')
    row['observations'] = checkpoints._file_reference(p, run)
    checkpoints.save_registry(run, registry)
    with pytest.raises(ValueError, match='context changed'):
        inspect_inputs(bound, expected_context_sha256=old['context_sha256'])


@pytest.mark.parametrize("change", ["restraint", "selection"])
def test_checkpoint_input_change_during_owner_read_is_refused(bound, change):
    calls = []
    def reader(run):
        calls.append(run)
        result = checkpoints.read_registry(run)
        if len(calls) == 2:
            row = next(r for r in result[1]['checkpoints'] if r['id'] == 'refine-001')
            if change == 'restraint':
                p = checkpoints.inherited_paths(row, run)['restraints'][0]
                p.write_bytes(p.read_bytes()+b'changed')
            else:
                saved = json.loads(checkpoints.registry_path(run).read_bytes())
                saved['current'] = 'refine-001'
                checkpoints.registry_path(run).write_text(json.dumps(saved))
        return result
    with pytest.raises((checkpoints.CheckpointError, ValueError), match='changed'):
        inspect_inputs(bound, registry_reader=reader)
    assert len(calls) == 2


def test_checkpoint_input_inspection_does_not_admit_selection_or_new_schema(bound):
    with pytest.raises(ValueError, match='checkpoint identity'):
        inspect_inputs(bound, checkpoint=None)
    run = bound[0]; path = checkpoints.registry_path(run)
    record = json.loads(path.read_bytes()); record['schema_version'] = 3
    path.write_text(json.dumps(record))
    def reader(run):
        return run, json.loads(path.read_bytes())
    with pytest.raises(ValueError, match='schema-2'):
        inspect_inputs(bound, registry_reader=reader)


@pytest.fixture
def recut_child(tmp_path):
    from tests.test_topostitch_continuations import setup, request
    from tests.test_topostitch_graph import identity_reader
    from nasolve.topostitch_recut_bundle import build_relabel_preview
    from nasolve.topostitch_checkpoint import inspect_checkpoint_inputs
    source=tmp_path/'cut-input';source.mkdir()
    paths,links=setup(source)
    args,graph,proposal=request(paths,links,forest=True)
    preview=tmp_path/'parent-preview';build_relabel_preview(**args,output_directory=preview)
    run=make_checkpoint_run(tmp_path/'checkpoint-input')
    report=json.loads((run/'report.json').read_bytes());model=Path(report['postmr']['prepared_model'])
    model.write_bytes(paths[0].read_bytes());report['postmr']['prepared_sha256']=sha256(model.read_bytes()).hexdigest()
    (run/'report.json').write_text(json.dumps(report))
    _,registry=checkpoints.initialize_registry(run)
    child=run/'child.pdb';lines=model.read_text().splitlines()
    index=next(i for i,line in enumerate(lines) if line.startswith('ATOM'))
    line=lines[index];lines[index]=line[:30]+f'{float(line[30:38])+.1:8.3f}'+line[38:]
    child.write_text('\n'.join(lines)+'\n')
    row=deepcopy(registry['checkpoints'][0]);row.update(id='refine-001',parent='postmr',kind='refinement',model=checkpoints._file_reference(child,run))
    registry['checkpoints'].append(row);checkpoints.save_registry(run,registry)
    def context(identifier):
        row=checkpoints.resolve_checkpoint(checkpoints.read_registry(run)[1],identifier)
        return inspect_checkpoint_inputs(run,checkpoint=identifier,expected_checkpoint_id=identifier,
            expected_model_sha256=row['model']['sha256'],registry_reader=checkpoints.read_registry)['context_sha256']
    options=dict(parent_checkpoint_id='postmr',child_checkpoint_id='refine-001',
        expected_parent_context_sha256=context('postmr'),expected_child_context_sha256=context('refine-001'),
        expected_preview_receipt_sha256=sha256((preview/'preview.json').read_bytes()).hexdigest(),
        registry_reader=checkpoints.read_registry,closest_image_reader=identity_reader,image_separation_angstrom=.004)
    return run,preview,child,options


def refresh_recut(case,output,**overrides):
    from nasolve.topostitch_checkpoint import build_checkpoint_recut_preview
    run,preview,_,options=case
    return build_checkpoint_recut_preview(run,preview,output_directory=output,**dict(options,**overrides))


def test_checkpoint_child_cut_refresh_preserves_intent_and_requires_new_review(recut_child,tmp_path):
    from nasolve.topostitch_recut_bundle import load_relabel_preview,observe_relabel_backbone_intent
    run,parent,child,options=recut_child
    before={p:p.read_bytes() for root in (run.parent.parent,parent) for p in root.rglob('*') if p.is_file()}
    out=tmp_path/'child-preview';report=refresh_recut(recut_child,out)
    fresh=load_relabel_preview(out)
    assert fresh['source_model_sha256']==sha256(child.read_bytes()).hexdigest()
    assert fresh['workflow']['review_state']=='UNREVIEWED' and not fresh['selection_applied']
    assert report['parent_checkpoint_id']=='postmr' and report['child_checkpoint_id']=='refine-001'
    assert report['review_inherited'] is False and report['native_restart_qualified'] is False
    assert json.loads((out/'checkpoint-refresh.json').read_bytes())==report
    assert report['child_preview_sha256']==sha256((out/'preview.json').read_bytes()).hexdigest()
    old_request=json.loads((parent/'proposal.json').read_bytes());new_request=json.loads((out/'proposal.json').read_bytes())
    assert old_request.pop('registered_graph_sha256')!=new_request.pop('registered_graph_sha256')
    assert old_request==new_request
    intent=observe_relabel_backbone_intent(out)
    assert intent['source_model_sha256']==fresh['source_model_sha256']
    assert all(p.read_bytes()==raw for p,raw in before.items())
    assert checkpoints.read_registry(run)[1]['current']=='postmr'
    assert str(run) not in json.dumps(report)


@pytest.mark.parametrize('field',['expected_parent_context_sha256','expected_child_context_sha256','expected_preview_receipt_sha256'])
def test_child_cut_refresh_refuses_stale_bindings_before_output(recut_child,tmp_path,field):
    out=tmp_path/'refused'
    with pytest.raises(ValueError,match='context|preview'):
        refresh_recut(recut_child,out,**{field:'0'*64})
    assert not out.exists()


def test_child_cut_refresh_refuses_wrong_parent_and_preserves_existing_output(recut_child,tmp_path):
    out=tmp_path/'existing';out.mkdir();(out/'mine').write_text('owned')
    with pytest.raises(FileExistsError):refresh_recut(recut_child,out)
    assert (out/'mine').read_text()=='owned'
    with pytest.raises(ValueError,match='distinct'):
        refresh_recut(recut_child,tmp_path/'refused',child_checkpoint_id='postmr')


def test_child_cut_refresh_refuses_changed_images_and_late_input_drift(recut_child,tmp_path):
    from tests.test_topostitch_graph import identity_reader
    def images(*args):
        a,b=identity_reader(*args);a['image']['operator_xyz']='x+1,y,z';return a,b
    with pytest.raises(ValueError,match='representative'):
        refresh_recut(recut_child,tmp_path/'bad-image',closest_image_reader=images)
    def drift(*args):
        recut_child[2].write_bytes(recut_child[2].read_bytes()+b'REMARK changed\n')
        return identity_reader(*args)
    with pytest.raises((ValueError,checkpoints.CheckpointError),match='changed'):
        refresh_recut(recut_child,tmp_path/'drift',closest_image_reader=drift)
    assert not (tmp_path/'bad-image').exists() and not (tmp_path/'drift').exists()


def test_child_cut_refresh_relocates_run_and_replays_without_original_inputs(recut_child,tmp_path):
    from nasolve.topostitch_recut_bundle import load_relabel_preview
    run,parent,child,options=recut_child
    out=tmp_path/'child-preview';report=refresh_recut(recut_child,out)
    old=run.parent.parent;moved=tmp_path/'relocated-dataset';shutil.move(old,moved)
    new_parent=tmp_path/'relocated-parent';shutil.move(parent,new_parent)
    new_run=moved/'AutoMR'/run.name
    relocated=(new_run,new_parent,new_run/'child.pdb',options)
    new_out=tmp_path/'second-preview';assert refresh_recut(relocated,new_out)==report
    assert not old.exists() and not parent.exists()
    assert load_relabel_preview(out)==load_relabel_preview(new_out)


@pytest.mark.parametrize('change',['missing_atom','wrong_parent','reordered_atoms'])
def test_child_cut_refresh_uses_lineage_and_atom_identity_not_only_model_hash(recut_child,tmp_path,change):
    from nasolve.topostitch_checkpoint import inspect_checkpoint_inputs
    run,parent,child,options=recut_child
    _,registry=checkpoints.read_registry(run);row=checkpoints.resolve_checkpoint(registry,'refine-001')
    if change=='wrong_parent':row['parent']=None
    else:
        lines=child.read_text().splitlines();atoms=[s for s in lines if s.startswith(('ATOM  ','HETATM'))]
        if change=='missing_atom':atoms.pop()
        else:atoms.reverse()
        child.write_text(next(s for s in lines if s.startswith('CRYST1'))+'\n'+'\n'.join(atoms)+'\nEND\n')
        row['model']=checkpoints._file_reference(child,run)
    checkpoints.save_registry(run,registry)
    # Fresh valid hashes do not establish ancestry or complete atom correspondence.
    for identifier,key in [('postmr','expected_parent_context_sha256'),('refine-001','expected_child_context_sha256')]:
        cp=checkpoints.resolve_checkpoint(registry,identifier)
        options[key]=inspect_checkpoint_inputs(run,checkpoint=identifier,expected_checkpoint_id=identifier,
            expected_model_sha256=cp['model']['sha256'],registry_reader=checkpoints.read_registry)['context_sha256']
    out=tmp_path/'derived'
    if change=='reordered_atoms':
        report=refresh_recut(recut_child,out)
        assert report['graph_descent']['reordered_atom_count']>0
        assert report['graph_descent']['source_to_descendant_atom_indices']==list(reversed(range(report['graph_descent']['atom_count'])))
    else:
        with pytest.raises(ValueError,match='bijection|direct refinement child'):
            refresh_recut(recut_child,out)
        assert not out.exists()


def test_child_cut_refresh_preserves_explicit_images_without_rechoosing_forest(recut_child,tmp_path):
    from nasolve.topostitch_recut_bundle import build_relabel_preview
    run,parent,child,options=recut_child
    request=json.loads((parent/'proposal.json').read_bytes())
    request['kind']='topostitch-representative-proposal'
    request.pop('selected_edge_ids');request.pop('anchor_node_ids')
    request['node_images']=[dict(node_id=1,operator_xyz='x+1,y,z')]
    proposal=tmp_path/'explicit.json';proposal.write_text(json.dumps(request))
    explicit=tmp_path/'explicit-parent'
    build_relabel_preview(parent/'source.pdb',parent/'discovery.json',registration_path=parent/'registration.json',proposal_path=proposal,output_directory=explicit)
    options['expected_preview_receipt_sha256']=sha256((explicit/'preview.json').read_bytes()).hexdigest()
    out=tmp_path/'explicit-child';refresh_recut((run,explicit,child,options),out)
    assert json.loads((out/'proposal.json').read_bytes())['node_images']==request['node_images']



def test_child_cut_refresh_leaves_no_complete_binding_if_inputs_change_during_write(recut_child,tmp_path,monkeypatch):
    from nasolve import topostitch_recut_bundle as bundle
    original=bundle.build_relabel_preview
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        recut_child[2].write_bytes(recut_child[2].read_bytes()+b'REMARK changed after snapshot\n')
        return result
    monkeypatch.setattr(bundle,'build_relabel_preview',changed)
    out=tmp_path/'partial'
    with pytest.raises(checkpoints.CheckpointError,match='changed'):
        refresh_recut(recut_child,out)
    assert (out/'preview.json').exists() and not (out/'checkpoint-refresh.json').exists()
    with pytest.raises(FileExistsError):refresh_recut(recut_child,out)



def read_saved_refresh(case,output,**overrides):
    from nasolve.topostitch_checkpoint import load_checkpoint_recut_preview
    options=case[3]
    args=dict(expected_refresh_sha256=sha256((output/'checkpoint-refresh.json').read_bytes()).hexdigest(),
        registry_reader=options['registry_reader'],closest_image_reader=options['closest_image_reader'],
        image_separation_angstrom=options['image_separation_angstrom'])
    return load_checkpoint_recut_preview(case[0],case[1],output,**dict(args,**overrides))


def test_saved_refresh_rederives_exact_binding_without_touching_run_or_packets(recut_child,tmp_path):
    out=tmp_path/'fresh';created=refresh_recut(recut_child,out)
    roots=(recut_child[0].parent.parent,recut_child[1],out)
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for root in roots for p in root.rglob('*') if p.is_file()}
    assert read_saved_refresh(recut_child,out)==created
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==raw for p,raw in before.items())
    old_run=recut_child[0];dataset=old_run.parent.parent;moved=tmp_path/'moved-dataset';shutil.move(dataset,moved)
    parent=tmp_path/'moved-parent';shutil.move(recut_child[1],parent)
    preview=tmp_path/'moved-child';shutil.move(out,preview)
    assert not dataset.exists() and not out.exists() and not recut_child[1].exists()
    relocated=(moved/'AutoMR'/old_run.name,parent,None,recut_child[3])
    assert read_saved_refresh(relocated,preview)==created


@pytest.mark.parametrize('change',['authority','typed_schema','distance'])
def test_saved_refresh_rehashing_a_claim_does_not_authenticate_it(recut_child,tmp_path,change):
    from nasolve.topostitch_recipe import recipe_digest
    out=tmp_path/'fresh';record=refresh_recut(recut_child,out)
    if change=='authority':record['runtime_authority']=True;record['review_state']='APPROVED'
    elif change=='typed_schema':record['schema_version']=True
    else:record['graph_descent']['max_atom_shift_angstrom']+=1
    record.pop('report_sha256');record['report_sha256']=recipe_digest(record)
    (out/'checkpoint-refresh.json').write_text(json.dumps(record))
    with pytest.raises(ValueError,match='refresh'):
        read_saved_refresh(recut_child,out)


def test_saved_refresh_refuses_wrong_pin_missing_completion_and_changed_run(recut_child,tmp_path):
    out=tmp_path/'fresh';refresh_recut(recut_child,out)
    with pytest.raises(ValueError,match='refresh'):
        read_saved_refresh(recut_child,out,expected_refresh_sha256='0'*64)
    path=out/'checkpoint-refresh.json';raw=path.read_bytes();path.unlink()
    from nasolve.topostitch_checkpoint import load_checkpoint_recut_preview
    with pytest.raises(FileNotFoundError):
        load_checkpoint_recut_preview(recut_child[0],recut_child[1],out,expected_refresh_sha256=sha256(raw).hexdigest(),
            registry_reader=checkpoints.read_registry,closest_image_reader=recut_child[3]['closest_image_reader'],image_separation_angstrom=.004)
    path.write_bytes(raw)
    checkpoints.select_checkpoint(recut_child[0],'refine-001')
    with pytest.raises(ValueError,match='context'):
        read_saved_refresh(recut_child,out)


def test_saved_refresh_rejects_another_valid_cut_even_with_rehashed_sidecar(recut_child,tmp_path):
    from nasolve.topostitch_recut_bundle import build_relabel_preview,_FILES
    from nasolve.topostitch_recipe import recipe_digest
    out=tmp_path/'fresh';record=refresh_recut(recut_child,out)
    proposal=json.loads((out/'proposal.json').read_bytes())
    proposal['kind']='topostitch-representative-proposal';proposal.pop('selected_edge_ids');proposal.pop('anchor_node_ids');proposal['node_images']=[]
    request=tmp_path/'different.json';request.write_text(json.dumps(proposal))
    other=tmp_path/'other'
    build_relabel_preview(out/'source.pdb',out/'discovery.json',registration_path=out/'registration.json',proposal_path=request,output_directory=other)
    for name in [*_FILES.values(),'preview.json']:(out/name).write_bytes((other/name).read_bytes())
    record['child_preview_sha256']=sha256((out/'preview.json').read_bytes()).hexdigest()
    record.pop('report_sha256');record['report_sha256']=recipe_digest(record)
    (out/'checkpoint-refresh.json').write_text(json.dumps(record))
    with pytest.raises(ValueError,match='refresh'):
        read_saved_refresh(recut_child,out)
