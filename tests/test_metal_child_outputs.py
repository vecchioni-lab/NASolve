"""Sealing stopped-process bytes does not admit scientific results."""
import json
import shutil
from unittest.mock import patch
import pytest
from nasolve.metal import child_outputs as outputs
from nasolve.metal.recipe import RecipeError
from tests.test_metal_child_process import setup, invoke, inventory


def completed(tmp_path):
    values=setup(tmp_path);invoke(tmp_path,values)
    root=tmp_path/'attempt';job=root/'native/fdp/job'
    for name in outputs.REQUIRED_OUTPUTS:(job/name).write_text('Simulated output '+name+'\n')
    return values,root,job


def test_seal_read_and_relocate_without_original_paths(tmp_path):
    values,root,job=completed(tmp_path);before=inventory(job)
    record=outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    assert record['scientific_acceptance']=='NOT_ASSESSED' and not record['retirement_authorized']
    assert record['job']=={'anchor':'child','relative_path':'native/fdp/job'}
    assert record['total_bytes']==sum(len(b) for b in before.values())
    assert set(record['files'])==set(before) and inventory(job)==before
    with pytest.raises(ValueError):outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    destination=tmp_path/'relocated';root.rename(destination)
    shutil.rmtree(values[0]);shutil.rmtree(values[1])
    with patch('subprocess.Popen',side_effect=AssertionError('No process on readback')):
        read=outputs.inspect_child_outputs(destination,request_id=values[2]['request_id'],output_id=record['record_sha256'])
    assert read==record


@pytest.mark.parametrize('state',['live','uncertain','timeout','missing','empty'])
def test_partial_or_unstopped_never_seals(tmp_path,monkeypatch,state):
    values,root,job=completed(tmp_path)
    if state in {'live','uncertain','timeout'}:
        inspect=outputs.inspect_child
        def changed(*a,**k):
            value=inspect(*a,**k);value['status']='TIMED_OUT' if state=='timeout' else 'STOP_UNCERTAIN'
            value['stopped_verified']=state=='timeout';return value
        monkeypatch.setattr(outputs,'inspect_child',changed)
    elif state=='missing':(job/'final.pdb').unlink()
    else:(job/'final.pdb').write_bytes(b'')
    with pytest.raises(RecipeError):outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    assert not (root/'outputs.json').exists()


@pytest.mark.parametrize('change',['same-size','extra','missing','symlink','input'])
def test_changed_file_or_inventory_refuses(tmp_path,change):
    values,root,job=completed(tmp_path)
    record=outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    path=job/'final.pdb'
    if change=='same-size':path.write_bytes(b'X'*path.stat().st_size)
    elif change=='extra':(job/'extra').write_text('extra')
    elif change=='missing':path.unlink()
    elif change=='input':(job/'input.pdb').write_text('changed')
    else:path.unlink();path.symlink_to(job/'effective-final.phil')
    with pytest.raises((RecipeError,OSError)):
        outputs.inspect_child_outputs(root,request_id=values[2]['request_id'],output_id=record['record_sha256'])


def test_budget_and_mutation_during_inventory_refuse(tmp_path,monkeypatch):
    values,root,job=completed(tmp_path)
    with pytest.raises(RecipeError,match='budget'):
        outputs.freeze_child_outputs(root,request_id=values[2]['request_id'],max_bytes=1)
    original=outputs._hash
    def change(path,state):
        value=original(path,state)
        if path.name=='final.pdb':path.write_bytes(b'X'*path.stat().st_size)
        return value
    monkeypatch.setattr(outputs,'_hash',change)
    with pytest.raises(RecipeError,match='changed'):
        outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    assert not (root/'outputs.json').exists()


def test_wrong_pin_and_late_owner_change_refuse(tmp_path,monkeypatch):
    values,root,job=completed(tmp_path);inspect=outputs.inspect_child;calls=[]
    def changed(*a,**k):
        value=inspect(*a,**k);calls.append(1)
        if len(calls)>1:value['stopped_verified']=False
        return value
    monkeypatch.setattr(outputs,'inspect_child',changed)
    with pytest.raises(RecipeError):outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    assert not (root/'outputs.json').exists()
    monkeypatch.setattr(outputs,'inspect_child',inspect)
    record=outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    with pytest.raises(RecipeError):
        outputs.inspect_child_outputs(root,request_id=values[2]['request_id'],output_id='0'*64)


def test_actual_live_process_and_uncertain_owner_cannot_seal(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import time
    values=setup(tmp_path);values[3].environment['SIM_MODE']='timeout'
    root=tmp_path/'attempt'
    with ThreadPoolExecutor(max_workers=1) as pool:
        task=pool.submit(invoke,tmp_path,values,timeout_seconds=1.5)
        marker=root/'native/fdp/job/child.pid';deadline=time.monotonic()+4
        while not marker.exists() and not task.done() and time.monotonic()<deadline:time.sleep(.02)
        assert marker.exists()
        with pytest.raises(RecipeError,match='verified-stopped'):
            outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
        result=task.result(timeout=10)
    assert result['status']=='TIMED_OUT' and result['stopped_verified']
    with pytest.raises(RecipeError,match='verified-stopped'):
        outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    assert not (root/'outputs.json').exists()
    values[3].environment['SIM_MODE']='success'
    monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    result=invoke(tmp_path,values,'uncertain')
    assert result['status']=='STOP_UNCERTAIN'
    with pytest.raises(RecipeError,match='verified-stopped'):
        outputs.freeze_child_outputs(tmp_path/'uncertain',request_id=values[2]['request_id'])
    assert not (tmp_path/'uncertain/outputs.json').exists()


@pytest.mark.parametrize('unsupported',['directory','nonportable-name','too-many'])
def test_inventory_boundaries(tmp_path,unsupported):
    values,root,job=completed(tmp_path)
    if unsupported=='directory':(job/'extra').mkdir()
    elif unsupported=='nonportable-name':(job/('bad'+chr(92)+'name')).write_text('x')
    else:
        for i in range(256):(job/('extra-'+str(i))).write_text('x')
    with pytest.raises(RecipeError):outputs.freeze_child_outputs(root,request_id=values[2]['request_id'])
    assert not (root/'outputs.json').exists()


def test_exact_output_bytes_do_not_bypass_existing_scientific_freeze_audit(tmp_path):
    """A correctly sealed but scientifically bad payload remains unacceptable."""
    import gzip
    from nasolve.metal import child_process
    from nasolve.metal.fdp import audit_result
    from tests.test_metal_fdp import prepared as science_prepared, native_result
    science=tmp_path/'science';science.mkdir()
    _,_,plan,model=science_prepared(science)
    process=tmp_path/'process';process.mkdir()
    prepared,parent,request,native=setup(process)
    (prepared/'input.pdb').write_bytes(model)
    (prepared/'plan.json').write_text(json.dumps(plan))
    native_plan=json.loads((prepared/'native-plan.json').read_text());native_plan['plan']=plan
    (prepared/'native-plan.json').write_text(json.dumps(native_plan))
    request=child_process.make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])
    invoke(process,(prepared,parent,request,native))
    root=process/'attempt';job=root/'native/fdp/job'
    bad=native_result(plan,model);bad['atoms'][-1]['b_iso']+=1.
    (job/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(bad).encode(),mtime=0))
    (job/'final.pdb').write_bytes(model)
    (job/'effective-final.phil').write_text('Synthetic effective parameters\n')
    receipt=outputs.freeze_child_outputs(root,request_id=request['request_id'])
    assert outputs.inspect_child_outputs(root,request_id=request['request_id'],output_id=receipt['record_sha256'])==receipt
    with pytest.raises(RecipeError,match='Frozen native state changed: b_A2'):
        audit_result(plan,model,json.loads(gzip.decompress((job/'native-result.json.gz').read_bytes())))
    assert receipt['scientific_acceptance']=='NOT_ASSESSED' and not receipt['retirement_authorized']
