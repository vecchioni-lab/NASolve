"""Read-only request joins; stub reader tests do not qualify native execution."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest
from nasolve import checkpoints
from nasolve.topostitch_checkpoint import load_checkpoint_bend_motion
from tests.test_topostitch_checkpoint import bound


@pytest.fixture
def execution(bound):
    run,preview,pin=bound
    child='refine-002';folder=run/'AutoRefine/round_002';folder.mkdir()
    params=folder/'autorefine.params';params.write_text('refinement.main.number_of_macro_cycles = 1\n')
    parent=checkpoints.read_registry(run)[1]['checkpoints'][0]
    request=dict(checkpoint=child,parent='postmr',policy_id='TEST_READER_NOT_NATIVE',
        inputs=[parent['observations'],parent['model'],*parent['restraints'],checkpoints._file_reference(params,run)],command=['not-executed'])
    rp=folder/'parallelity_runtime';rp.mkdir();path=rp/'request.json';path.write_text(json.dumps(request))
    reference=checkpoints._file_reference(path,run)
    def reader(run,ref,*,checkpoint):
        p=checkpoints._ref_path(ref,'test request',run)
        value=json.loads(p.read_text());assert value['checkpoint']==checkpoint
        for row in value['inputs']:checkpoints._ref_path(row,'test request input',run)
        return value
    context=load_checkpoint_bend_motion(run,preview,expected_checkpoint_id='postmr',expected_receipt_sha256=pin)[2]['context_sha256']
    args=dict(expected_checkpoint_id='postmr',expected_receipt_sha256=pin,
        expected_checkpoint_context_sha256=context,execution_reference=reference,
        child_checkpoint_id=child,request_model_role='parent',
        generated_parameters=checkpoints._file_reference(params,run),execution_reader=reader)
    return bound,args,path


def load(execution,**overrides):
    from nasolve.topostitch_checkpoint import load_execution_bend_motion
    bound,args,_=execution
    return load_execution_bend_motion(bound[0],bound[1],**dict(args,**overrides))


def rewrite(execution,change):
    bound,args,path=execution;v=json.loads(path.read_text());change(v)
    path.write_text(json.dumps(v));args['execution_reference']=checkpoints._file_reference(path,bound[0])


def test_exact_parent_request_is_read_only_and_not_candidate_admission(execution):
    bound,args,_=execution
    before={p:p.read_bytes() for root in (bound[0],bound[1]) for p in root.rglob('*') if p.is_file()}
    motion,parameters,binding=load(execution)
    assert binding['request_model_role']=='parent'
    assert binding['runtime_authority'] is False and binding['chemical_admission'] is False
    assert binding['candidate_coordinates_in_request'] is False
    assert binding['child_checkpoint_id']=='refine-002' and binding['parent_checkpoint_id']=='postmr'
    assert [r['role'] for r in binding['inputs']]==['observations','model','restraint','restraint','generated_parameters']
    assert binding==load(execution,expected_execution_context_sha256=binding['context_sha256'])[2]
    assert all(p.read_bytes()==b for p,b in before.items())
    assert str(bound[0]) not in json.dumps(binding)


def test_candidate_request_requires_explicit_role_and_exact_bytes(execution):
    bound,args,_=execution;run,preview,_=bound
    model=run/'AutoRefine/round_002/candidate.pdb';model.write_bytes((preview/'candidate.pdb').read_bytes())
    rewrite(execution,lambda r:r['inputs'].__setitem__(1,checkpoints._file_reference(model,run)))
    with pytest.raises(ValueError,match='model'):load(execution)
    binding=load(execution,request_model_role='candidate')[2]
    assert binding['candidate_coordinates_in_request'] and not binding['runtime_authority']
    model.write_bytes(model.read_bytes()+b'REMARK changed metadata\n')
    rewrite(execution,lambda r:r['inputs'].__setitem__(1,checkpoints._file_reference(model,run)))
    with pytest.raises(ValueError,match='candidate'):load(execution,request_model_role='candidate')


@pytest.mark.parametrize('change',['parent','model','observations','restraint_order','drop_restraint','extra_input','parameters'])
def test_rehashed_request_cannot_change_declared_input_roles(execution,change):
    def edit(r):
        if change=='parent':r['parent']='refine-001'
        elif change=='model':r['inputs'][1]=r['inputs'][0]
        elif change=='observations':r['inputs'][0]=r['inputs'][1]
        elif change=='restraint_order':r['inputs'][2:4]=reversed(r['inputs'][2:4])
        elif change=='drop_restraint':r['inputs'].pop(2)
        elif change=='extra_input':r['inputs'].insert(2,r['inputs'][2])
        else:r['inputs'][-1]=r['inputs'][2]
    rewrite(execution,edit)
    with pytest.raises(ValueError):load(execution)


def test_same_parent_bytes_but_reselected_checkpoint_refuses(execution):
    checkpoints.select_checkpoint(execution[0][0],'refine-001')
    with pytest.raises(ValueError,match='checkpoint'):load(execution)


def test_distinct_child_identity_and_exact_round_parameters_required(execution):
    with pytest.raises(ValueError):load(execution,child_checkpoint_id='postmr')
    ref=deepcopy(execution[1]['generated_parameters']);ref['relative_path']='elsewhere.params'
    with pytest.raises(ValueError,match='parameters'):load(execution,generated_parameters=ref)
    with pytest.raises(ValueError,match='role'):load(execution,request_model_role='auto')


def test_request_change_after_binding_refuses(execution):
    digest=load(execution)[2]['context_sha256']
    rewrite(execution,lambda r:r.update(command=['changed-but-otherwise-bound']))
    with pytest.raises(ValueError,match='execution context'):load(execution,expected_execution_context_sha256=digest)


def test_request_reader_change_to_checkpoint_is_detected(execution):
    reader=execution[1]['execution_reader'];calls=[]
    def changing(*args,**kwargs):
        result=reader(*args,**kwargs);calls.append(True)
        if len(calls)==2:checkpoints.select_checkpoint(execution[0][0],'refine-001')
        return result
    with pytest.raises(ValueError,match='checkpoint'):load(execution,execution_reader=changing)


def test_changed_request_during_join_refuses(execution):
    reader=execution[1]['execution_reader'];calls=[]
    def changing(*args,**kwargs):
        result=reader(*args,**kwargs);calls.append(True)
        if len(calls)==1:execution[2].write_bytes(execution[2].read_bytes()+b' ')
        return result
    with pytest.raises((ValueError,checkpoints.CheckpointError)):load(execution,execution_reader=changing)


def test_explicit_additional_restraint_order_is_separately_bound(execution):
    run=execution[0][0];p=run/'extra.phil';p.write_text('geometry_restraints {}\n');ref=checkpoints._file_reference(p,run)
    rewrite(execution,lambda r:r['inputs'].insert(-1,ref))
    with pytest.raises(ValueError):load(execution)
    binding=load(execution,additional_restraints=[ref])[2]
    assert binding['inputs'][-2]['role']=='additional_restraint'


def test_declared_phase_is_checked_in_execution_order(execution):
    run=execution[0][0];_,reg=checkpoints.read_registry(run);p=run/'phases.mtz';p.write_bytes(b'declared phases')
    ref=checkpoints._file_reference(p,run);reg['checkpoints'][0]['phases']=ref;checkpoints.save_registry(run,reg)
    b=execution[0];execution[1]['expected_checkpoint_context_sha256']=load_checkpoint_bend_motion(b[0],b[1],expected_checkpoint_id='postmr',expected_receipt_sha256=b[2])[2]['context_sha256']
    with pytest.raises(ValueError):load(execution)
    rewrite(execution,lambda r:r['inputs'].insert(-1,ref))
    assert load(execution)[2]['inputs'][-2]['role']=='phases'


def test_owner_validated_namespace_adaptation_preserves_source_order(execution):
    run=execution[0][0];source=json.loads(execution[2].read_text())['inputs'][2]
    derivative=run/'AutoRefine/round_002/adapted.phil';derivative.write_text('refinement {}\n');dref=checkpoints._file_reference(derivative,run)
    receipt=run/'AutoRefine/round_002/refinement_inputs.json';receipt.write_text('fixture adaptation')
    aref=checkpoints._file_reference(receipt,run)
    def owner(run,refs,ref,*,checkpoint):
        assert refs[0]==source and ref==aref and checkpoint=='refine-002'
        return dict(adaptations=[dict(index=0,source=source,execution=dref)])
    rewrite(execution,lambda r:r['inputs'].__setitem__(2,dref))
    with pytest.raises(ValueError):load(execution)
    result=load(execution,refinement_input_reference=aref,refinement_input_reader=owner)[2]
    assert result['inputs'][2]['source']=={k:source[k] for k in ('anchor','relative_path','sha256','size')}
    derivative.write_text('changed')
    with pytest.raises(checkpoints.CheckpointError):load(execution,refinement_input_reference=aref,refinement_input_reader=owner)


def test_join_relocates_with_original_dataset_and_preview_gone(execution,tmp_path):
    before=load(execution)[2];bound,args,path=execution
    old=bound[0].parent.parent;dataset=tmp_path/'relocated';shutil.move(str(old),dataset)
    preview=tmp_path/'relocated-preview';shutil.move(str(bound[1]),preview)
    moved=(dataset/'AutoMR/run_001',preview,bound[2])
    assert not old.exists() and not bound[1].exists()
    after=load((moved,args,moved[0]/'AutoRefine/round_002/parallelity_runtime/request.json'),expected_execution_context_sha256=before['context_sha256'])[2]
    assert after==before


@pytest.mark.parametrize('name',['preview.json','candidate.pdb'])
def test_preview_change_during_request_join_refuses(execution,name):
    reader=execution[1]['execution_reader'];calls=[]
    def changing(*args,**kwargs):
        result=reader(*args,**kwargs);calls.append(True)
        if len(calls)==2:
            p=execution[0][1]/name;p.write_bytes(p.read_bytes()+b' ')
        return result
    with pytest.raises(ValueError):load(execution,execution_reader=changing)


def test_missing_shared_reader_is_explicit_not_a_permissive_fallback(execution,monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules,'nasolve.refinement_parallelity',None)
    with pytest.raises(RuntimeError,match='maintained Cedar'):
        load(execution,execution_reader=None)
