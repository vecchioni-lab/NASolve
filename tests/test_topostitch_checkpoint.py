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
