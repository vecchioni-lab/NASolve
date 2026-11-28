"""A constructed metal input is retained without inventing a refined parent.

Ordinary preparation/native capture authentication are controlled at their owner
boundaries here. Discovery, model replay, real MTZ indexing, durable records and
registry guards are exercised. Genuine capture qualification is a local check.
"""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve import checkpoints
from nasolve.campaign_records import read_record, write_record
from nasolve.metal.context import load_run_context
from nasolve.metal.materialize import build_hypothesis
from tests.test_metal_discovery import scene, plan


def setup(tmp_path, monkeypatch):
    case = scene(tmp_path)
    monkeypatch.setattr(checkpoints, '_validate_preparation', lambda *a, **kw: {})
    p = case.run/'report.json'
    report = json.loads(p.read_text())
    report['postmr'].update(checked_preparation={'test_owner': True,
        'observations': checkpoints._file_reference(case.run.parent.parent/'observations.mtz',case.run)},
        message='Synthetic checked preparation')
    p.write_text(json.dumps(report))
    proof = case.run/'PostMR/report.json'; proof.parent.mkdir(); proof.write_text('{}')
    _, registry = checkpoints.initialize_registry(case.run)
    registry['schema_version'] = 3
    write_record(checkpoints.registry_path(case.run), registry, replace=True)
    case.context = load_run_context(case.run, records=case.context.roles.records())
    hypothesis = build_hypothesis(case.context, case.recipe, plan(case))
    case.hypothesis = case.run/hypothesis['files']['model']['relative_path']; case.hypothesis = case.hypothesis.parent
    case.native = case.run/'native-receipt.json'; case.native.write_text('{"controlled_native_owner":true}')
    case.selectors = dict(data_labels=['F','SIGF'], free_label='FreeR_flag', test_flag_value=0,
                          phase_labels=['HLA','HLB','HLC','HLD'])
    return case


def module(monkeypatch):
    m = importlib.import_module('nasolve.metal_checkpoint')
    def native_review(run, parent, hypothesis, native):
        m._file(run, native, 'controlled native receipt')
        return dict(status='PREPARATION_INPUTS_VERIFIED', native_receipt=native,
            scientific_acceptance='NOT_ASSESSED', execution_ready=False)
    monkeypatch.setattr(m, '_native_review', native_review)
    return m


def publish(m, case):
    return m.publish_metal_checkpoint(case.run, hypothesis=case.hypothesis,
        native_receipt=case.native, selectors=case.selectors, label='Hg construction')


def test_publish_retains_recipe_experiment_and_unselected_parent(tmp_path, monkeypatch):
    case = setup(tmp_path, monkeypatch)
    before = checkpoints.read_registry(case.run)[1]
    model = (case.run/'model.pdb').read_bytes()
    m = module(monkeypatch)
    with patch('subprocess.Popen', side_effect=AssertionError('No native execution')):
        result = publish(m, case)
        _, after = checkpoints.read_registry(case.run)
        review = m.inspect_metal_checkpoint(case.run, result.checkpoint_id)
    node = checkpoints.resolve_checkpoint(after, result.checkpoint_id)
    assert after['schema_version'] == 6 and after['current'] == before['current']
    assert after['checkpoints'][0] == before['checkpoints'][0]
    assert node['status'] == 'REVIEW' and node['usable'] is False
    assert node['parent'] == 'postmr' and node['phases'] is None
    assert node['restraints'][:-1] == before['checkpoints'][0]['restraints']
    assert node['restraints'][-1]['relative_path'].endswith('hypothesis_001/restraints.phil')
    assert review['experiment']['phase_origin'] == 'external-declared-autosol'
    assert review['experiment']['observations'] == 3 and review['experiment']['free_count'] == 1
    assert review['experiment']['selectors'] == case.selectors
    assert review['scientific_acceptance'] == 'NOT_ASSESSED'
    assert review['execution_ready'] is False and review['refinement'] == 'NOT_RUN'
    assert (case.run/'model.pdb').read_bytes() == model
    assert list((case.run/'AutoRefine/Checkpoints'/node['id']).iterdir()) == [
        case.run/'AutoRefine/Checkpoints'/node['id']/'input.json']


def test_relocates_without_original_path_or_selected_checkpoint(tmp_path, monkeypatch):
    case = setup(tmp_path/'original', monkeypatch); m = module(monkeypatch)
    result = publish(m, case)
    before = m.inspect_metal_checkpoint(case.run, result.checkpoint_id)
    old = tmp_path/'original'; moved = tmp_path/'moved'; old.rename(moved)
    run = moved/'dataset/AutoMR/run_001'
    assert not old.exists()
    assert m.inspect_metal_checkpoint(run, result.checkpoint_id) == before


def test_normal_publication_updates_do_not_invalidate_frozen_ancestry(tmp_path, monkeypatch):
    case = setup(tmp_path, monkeypatch); m = module(monkeypatch); result = publish(m, case)
    before = m.inspect_metal_checkpoint(case.run, result.checkpoint_id)
    p=case.run/'report.json'; doc=json.loads(p.read_text()); doc['message']='Later stage status';p.write_text(json.dumps(doc))
    checkpoints.add_checkpoint(case.run, name='Original bookmark', parent='postmr')
    assert m.inspect_metal_checkpoint(case.run, result.checkpoint_id) == before


@pytest.mark.parametrize('change',['recipe','model','phases','discovery','native','receipt'])
def test_changed_inputs_or_receipts_refuse_on_ordinary_read(tmp_path, monkeypatch, change):
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch);result=publish(m,case)
    target={'recipe':case.hypothesis/'restraints.phil','model':case.hypothesis/'model.pdb',
        'phases':case.run/'external/phases.mtz','discovery':case.heavy,'native':case.native,
        'receipt':case.run/'AutoRefine/Checkpoints'/result.checkpoint_id/'input.json'}[change]
    target.write_bytes(target.read_bytes()+b'\n')
    with pytest.raises(checkpoints.CheckpointError):checkpoints.read_registry(case.run)


@pytest.mark.parametrize('change',['usable','status','parent','model','restraints','phase','proof','kind','schema'])
def test_rehashed_registry_cannot_relabel_input_as_ready(tmp_path,monkeypatch,change):
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch);result=publish(m,case)
    path=checkpoints.registry_path(case.run);r=read_record(path);node=r['checkpoints'][-1]
    if change=='usable':node['usable']=True
    elif change=='status':node['status']='SUCCESS'
    elif change=='parent':node['parent']='missing'
    elif change=='model':node['model']=r['checkpoints'][0]['model']
    elif change=='restraints':node['restraints']=[]
    elif change=='phase':node['phases']={'unapproved':'phase'}
    elif change=='proof':node.pop('metal_construction')
    elif change=='kind':node['kind']='manual'
    else:r['schema_version']=5
    write_record(path,r,replace=True)
    with pytest.raises(checkpoints.CheckpointError):checkpoints.read_registry(case.run)


@pytest.mark.parametrize('field,value',[('free_label','SAflags'),('test_flag_value',True),
    ('phase_labels',['HLB','HLA','HLC','HLD'])])
def test_wrong_experiment_allocates_nothing(tmp_path,monkeypatch,field,value):
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch);case.selectors[field]=value
    before=checkpoints.registry_path(case.run).read_bytes()
    with pytest.raises(ValueError):publish(m,case)
    assert checkpoints.registry_path(case.run).read_bytes()==before
    assert not (case.run/'AutoRefine/Checkpoints').exists()


def test_held_input_cannot_be_selected_or_used_for_manual_descendant(tmp_path,monkeypatch):
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch);result=publish(m,case)
    with pytest.raises(checkpoints.CheckpointError,match='reusable'):
        checkpoints.select_checkpoint(case.run,result.checkpoint_id)
    with pytest.raises(checkpoints.CheckpointError,match='metal|Metal'):
        checkpoints.add_checkpoint(case.run,name='Lossy descendant',parent=result.checkpoint_id,model=case.hypothesis/'model.pdb')


def test_concurrent_registry_save_keeps_failed_number_and_newer_choice(tmp_path,monkeypatch):
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch)
    append=checkpoints.append_checkpoint
    def race(run,registry,payload,**kwargs):
        current=read_record(checkpoints.registry_path(run));current['bookmarks']['newer']='postmr'
        write_record(checkpoints.registry_path(run),current,replace=True)
        return append(run,registry,payload,**kwargs)
    monkeypatch.setattr(checkpoints,'append_checkpoint',race)
    with pytest.raises(checkpoints.CheckpointError,match='changed'):publish(m,case)
    assert read_record(checkpoints.registry_path(case.run))['bookmarks']['newer']=='postmr'
    assert (case.run/'AutoRefine/Checkpoints/metal-001/failure.json').is_file()
    monkeypatch.setattr(checkpoints,'append_checkpoint',append)
    assert publish(m,case).checkpoint_id=='metal-002'


def test_old_reader_refuses_new_input_and_save_cannot_downgrade(tmp_path,monkeypatch):
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch);publish(m,case)
    with monkeypatch.context() as old:
        old.setattr(checkpoints,'READABLE_SCHEMA_VERSIONS',{1,2,3,4,5})
        with pytest.raises(checkpoints.CheckpointError,match='Unsupported checkpoint schema'):
            checkpoints.read_registry(case.run)
    _,registry=checkpoints.read_registry(case.run);registry['schema_version']=5
    with pytest.raises(checkpoints.CheckpointError,match='downgrade'):
        checkpoints.save_registry(case.run,registry)


def test_late_phase_change_during_final_native_review_cannot_publish(tmp_path,monkeypatch):
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch)
    original=m._native_review;calls=[]
    def change_late(*args):
        value=original(*args);calls.append(1)
        if len(calls)==2:
            phase=case.run/'external/phases.mtz';phase.write_bytes(phase.read_bytes()+b'changed')
        return value
    monkeypatch.setattr(m,'_native_review',change_late)
    before=checkpoints.registry_path(case.run).read_bytes()
    with pytest.raises(checkpoints.CheckpointError, match='changed after it was frozen'):
        publish(m,case)
    assert checkpoints.registry_path(case.run).read_bytes()==before
    assert (case.run/'AutoRefine/Checkpoints/metal-001/failure.json').is_file()


def test_rehashed_selection_cannot_promote_held_input(tmp_path,monkeypatch):
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch);result=publish(m,case)
    path=checkpoints.registry_path(case.run);registry=read_record(path)
    registry['current']=result.checkpoint_id;write_record(path,registry,replace=True)
    with pytest.raises(checkpoints.CheckpointError,match='current refinement checkpoint'):
        checkpoints.read_registry(case.run)


def test_explicit_native_requirement_leaves_registry_read_only(tmp_path,monkeypatch):
    import builtins
    case=setup(tmp_path,monkeypatch);m=module(monkeypatch);publish(m,case)
    before=checkpoints.registry_path(case.run).read_bytes()
    original=builtins.__import__
    def without_native(name,*args,**kwargs):
        if name=='iotbx':raise ImportError('controlled missing native library')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',without_native)
    with pytest.raises(checkpoints.CheckpointError,match='Phenix Python environment'):
        checkpoints.read_registry(case.run)
    assert checkpoints.registry_path(case.run).read_bytes()==before
