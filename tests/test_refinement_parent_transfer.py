"""Synthetic metadata tests; the transfer review never admits a native runtime."""
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve.refinement_parent_transfer import inspect_parent_transfer, _SOURCE_POLICY
from nasolve.autorefine import ReflectionPlan, build_refine_command
from nasolve.checkpoints import _file_reference, registry_path, CheckpointError
from nasolve.campaign_records import write_record, read_record
from tests.test_metal_source_intake import saved_run, snapshot

REVISION='a'*40


def fixture(root, phases=False):
    run=saved_run(root,phases=phases)
    ref=lambda p:_file_reference(p,run)
    registry=json.loads(registry_path(run).read_text());parent=registry['checkpoints'][0]
    directory=run/'AutoRefine/round_001';directory.mkdir()
    model=directory/'refined_001.pdb';model.write_bytes((run/'prepared.pdb').read_bytes()+b'REMARK synthetic child\n')
    restraints=[run/'base-pairs.phil',run/'ligand.cif']
    for i,p in enumerate(restraints):p.write_text('synthetic restraint '+str(i))
    bond=directory/'image-bond.phil';bond.write_text('synthetic generated image bond')
    policy=directory/'autorefine.params';policy.write_text('synthetic source policy')
    topology={}
    for name in ('registration','discovery','continuations'):
        p=directory/(name+'.json');p.write_text('{}');topology[name]=ref(p)
    phase=parent['phases']
    inputs=[parent['observations'],parent['model'],*[ref(p) for p in restraints],ref(bond),*([phase] if phase else []),ref(policy)]
    historical=[Path('/historical/input-'+str(i)) for i in range(len(inputs))]
    plan=ReflectionPlan(('IMEAN','SIGIMEAN'),'FreeR_flag',0,False,
        tuple(phase['labels']) if phase else (),historical[-2] if phase else None,False,False,None)
    command=build_refine_command(Path('phenix.refine'),historical[1],historical[0],
        historical[2:-2] if phase else historical[2:-1],historical[-1],plan)
    request_path=directory/'request.json'
    request=write_record(request_path,dict(schema_version=1,policy_id=_SOURCE_POLICY,checkpoint='refine-001',parent='postmr',
        inputs=inputs,command=command,phosphate=dict(bond=ref(bond),sources=topology,inspections=[])))
    execution_path=directory/'execution.json'
    write_record(execution_path,dict(schema_version=1,policy_id=_SOURCE_POLICY,checkpoint='refine-001',request=ref(request_path),phases=[]))
    child=dict(parent,id='refine-001',parent='postmr',status='REVIEW',usable=True,model=ref(model),restraints=[ref(p) for p in restraints],outputs=dict(parallelity_execution=ref(execution_path)))
    registry['checkpoints'].append(child);registry_path(run).write_text(json.dumps(registry))
    captured=dict(schema_version=1,kind='ordinary-parent-transfer-capture',
      owner=dict(source_revision=REVISION,methods=['read_registry','resolve_checkpoint','inherited_paths','validate_checkpoint_execution','read_execution_request']),
      checkpoint={k:child[k] for k in ('id','parent','status','usable')},
      records=dict(report=ref(run/'report.json'),registry=ref(registry_path(run)),execution=ref(execution_path),request=ref(request_path)),
      sources=dict(model=child['model'],observations=child['observations'],phases=({k:phase[k] for k in ('anchor','relative_path','sha256','size')} if phase else None),restraints=child['restraints']),phase_metadata=phase,
      source_execution={k:request[k] for k in ('policy_id','parent','inputs','command')},source_endpoint_outputs={},
      native_ready=False,scientific_approval='NOT_ASSESSED')
    capture=root/'capture.json'
    def save():capture.write_text(json.dumps(captured));return sha256(capture.read_bytes()).hexdigest()
    save()
    return run,capture,captured,save


def review(run,capture):
    return inspect_parent_transfer(run,capture,expected_sha256=sha256(capture.read_bytes()).hexdigest(),expected_owner_revision=REVISION)


@pytest.mark.parametrize('phases',[False,True])
def test_roles_and_endpoint_are_explicit_without_runtime_admission(tmp_path,phases):
    run,capture,record,_=fixture(tmp_path,phases)
    before=snapshot(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('No execution')):
        result=review(run,capture)
    assert snapshot(tmp_path)==before
    assert result['status']=='INPUT_ROLES_REVIEWED_NOT_ADMITTED'
    assert not result['native_ready'] and not result['source_owner_replayed'] and not result['checkpoint_adoption']
    assert result['current_endpoint']!=result['source_starting_model']
    assert [r['role'] for r in result['source_execution_roles']]==[
        'original_observations','source_starting_model','inherited_restraint','inherited_restraint',
        'runtime_generated_crystal_bond',*(['source_phases'] if phases else []),'source_scientific_policy']
    assert ('NO_APPROVED_AUTOSOL_HL' in result['holds']) is not phases
    assert result['runtime_owned']['disposition']=='REGENERATE_THROUGH_SOURCE_OWNER_FOR_NEW_CHILD'


def test_relocated_source_uses_references_after_original_location_is_gone(tmp_path):
    old=tmp_path/'old';run,capture,_,_=fixture(old)
    first=review(run,capture);new=tmp_path/'moved';old.rename(new)
    assert not old.exists()
    assert review(new/'dataset/AutoMR/run_001',new/'capture.json')==first


@pytest.mark.parametrize('what',['capture_hash','owner','approval','endpoint','restraint_order','source_request','phase_metadata'])
def test_changed_capture_cannot_override_recorded_source(tmp_path,what):
    run,capture,record,save=fixture(tmp_path,phases=True)
    if what=='capture_hash':
        with pytest.raises(ValueError,match='checksum'):inspect_parent_transfer(run,capture,expected_sha256='0'*64,expected_owner_revision=REVISION)
        return
    if what=='owner':record['owner']['source_revision']='b'*40
    elif what=='approval':record['native_ready']=True
    elif what=='endpoint':record['sources']['model']=record['source_execution']['inputs'][1]
    elif what=='restraint_order':record['sources']['restraints'].reverse()
    elif what=='source_request':record['source_execution']['command'].append('main.target=mlhl')
    elif what=='phase_metadata':record['phase_metadata']=None
    save()
    with pytest.raises((ValueError,CheckpointError)):review(run,capture)


@pytest.mark.parametrize('which',['model','observations','restraint','generated','policy','registration','report','registry'])
def test_changed_source_bytes_refuse(tmp_path,which):
    run,capture,record,_=fixture(tmp_path)
    refs=dict(model=record['sources']['model'],observations=record['sources']['observations'],
              restraint=record['sources']['restraints'][0],generated=record['source_execution']['inputs'][-2],
              policy=record['source_execution']['inputs'][-1],report=record['records']['report'],registry=record['records']['registry'])
    request=read_record(run/record['records']['request']['relative_path'])
    refs['registration']=request['phosphate']['sources']['registration']
    from nasolve.run_context import resolve_artifact_path
    path=resolve_artifact_path(refs[which],run);path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises((ValueError,CheckpointError)):review(run,capture)
