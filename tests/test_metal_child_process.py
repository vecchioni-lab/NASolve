"""A real caller exercises shared process ownership with simulated native work."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import os
import shutil
import sys
from unittest.mock import patch
import pytest
from nasolve.cli import main
from nasolve.metal import child_process as m
from nasolve.metal import parent_archive
from nasolve.metal.recipe import RecipeError,digest


def setup(tmp_path):
    layout=tmp_path/'layout';layout.mkdir();(layout/'model.pdb').write_text('Protected test parent\n')
    parent=tmp_path/'parent';receipt=parent_archive.pack_parent_inputs(layout,parent)
    prepared=tmp_path/'prepared';prepared.mkdir()
    plan={'policy':{'strategy':['group_anomalous']}}
    (prepared/'plan.json').write_text(json.dumps(plan))
    (prepared/'native-plan.json').write_text(json.dumps({'plan':plan,'args':['input.pdb','observations.mtz','parameters.phil']}))
    for n in ['input.pdb','observations.mtz','parameters.phil']:(prepared/n).write_text('Synthetic prepared input '+n+'\n')
    executable=tmp_path/'simulated-phenix-python'
    executable.write_text('#!'+sys.executable+'\n'+"""import os,subprocess,sys,time
from pathlib import Path
mode=os.environ.get('SIM_MODE','success')
if mode=='timeout':
    child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    Path('child.pid').write_text(str(child.pid));Path('partial').write_text('retained')
    time.sleep(30)
if mode=='mutate':Path('input.pdb').write_text('changed')
print('simulated worker: '+mode)
sys.exit(7 if mode=='fail' else 0)
""")
    executable.chmod(0o700)
    native=SimpleNamespace(version=m.NATIVE_VERSION,executables={'phenix.python':executable},environment=dict(os.environ))
    request=m.make_request(prepared,parent_manifest_sha256=receipt['manifest_sha256'])
    return prepared,parent,request,native


def invoke(tmp_path,values,name='attempt',**options):
    prepared,parent,request,native=values
    return m.run_child(prepared,parent,request,request_id=request['request_id'],
        attempt_directory=tmp_path/name,native=native,**options)


def inventory(root):return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_normal_prepare_run_inspect_cli_and_relocation(tmp_path,monkeypatch,capsys):
    values=setup(tmp_path);prepared,parent,request,native=values
    output=tmp_path/'request.json'
    assert main(['metal','prepare-fdp-child-process',str(prepared),'--parent-manifest-sha256',request['parent_manifest_sha256'],'--output',str(output),'--json'])==0
    assert json.loads(capsys.readouterr().out)==request
    monkeypatch.setattr('nasolve.metal.cli.discover_phenix',lambda *a,**k:native)
    before=inventory(parent)
    args=['metal','run-fdp-child-process',str(prepared),'--request',str(output),'--request-id',request['request_id'],
        '--parent-archive',str(parent),'--attempt',str(tmp_path/'attempt'),'--timeout','5','--json']
    assert main(args)==0
    report=json.loads(capsys.readouterr().out)
    assert report['status']=='COMPLETED' and report['stopped_verified']
    assert report['outcome']['parent_transport_verified'] and not report['fresh_retry_eligible']
    assert report['scientific_acceptance']=='NOT_ASSESSED' and not report['retirement_authorized']
    assert inventory(parent)==before
    assert main(args)==2
    assert not capsys.readouterr().out
    relocated=tmp_path/'relocated';(tmp_path/'attempt').rename(relocated);shutil.rmtree(prepared);shutil.rmtree(parent)
    before=inventory(relocated)
    with patch('subprocess.Popen',side_effect=AssertionError('Inspection never executes')):
        assert main(['metal','inspect-fdp-child-process',str(relocated),'--request-id',request['request_id'],'--json'])==0
    assert json.loads(capsys.readouterr().out)['status']=='COMPLETED'
    assert inventory(relocated)==before


def test_timeout_stops_child_and_retry_is_a_new_explicit_attempt(tmp_path):
    from nasolve.campaign_process import _group_alive
    values=setup(tmp_path);values[3].environment['SIM_MODE']='timeout'
    report=invoke(tmp_path,values,timeout_seconds=.5)
    assert report['status']=='TIMED_OUT' and report['stopped_verified'] and report['fresh_retry_eligible']
    phase=report['process']['phases']['native-fdp']
    assert _group_alive(phase['identity']['pgid']) is False
    assert (tmp_path/'attempt/native/fdp/job/partial').read_text()=='retained'
    assert (tmp_path/'attempt/native/fdp/job/child.pid').is_file()
    before=inventory(tmp_path/'attempt')
    values[3].environment['SIM_MODE']='success'
    second=invoke(tmp_path,values,'retry',retry_from=tmp_path/'attempt',timeout_seconds=5)
    assert second['status']=='COMPLETED'
    assert second['outcome']['retry_of']==report['outcome']['record_sha256']
    assert inventory(tmp_path/'attempt')==before


def test_uncertain_stop_is_durable_and_blocks_retry(tmp_path,monkeypatch):
    values=setup(tmp_path)
    monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    report=invoke(tmp_path,values,timeout_seconds=5)
    assert report['status']=='STOP_UNCERTAIN' and not report['stopped_verified']
    assert not report['fresh_retry_eligible'] and (tmp_path/'attempt/outcome.json').exists()
    with pytest.raises(RecipeError,match='not qualified'):
        invoke(tmp_path,values,'retry',retry_from=tmp_path/'attempt')
    assert not (tmp_path/'retry').exists()


@pytest.mark.parametrize('change',['parent-pin','input','worker','native-version'])
def test_changed_pins_refuse_before_attempt_or_worker(tmp_path,change):
    prepared,parent,request,native=setup(tmp_path)
    if change=='parent-pin':request['parent_manifest_sha256']='0'*64
    elif change=='worker':request['worker_sha256']='0'*64
    elif change=='input':(prepared/'input.pdb').write_text('different')
    else:native.version='unsupported'
    if change in {'parent-pin','worker'}:
        request.pop('request_id');request['request_id']=digest(request)
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')):
        with pytest.raises((ValueError,RecipeError)):
            invoke(tmp_path,(prepared,parent,request,native))
    assert not (tmp_path/'attempt').exists()


def test_mutated_work_input_never_becomes_retry_eligible(tmp_path):
    values=setup(tmp_path);values[3].environment['SIM_MODE']='mutate'
    report=invoke(tmp_path,values)
    assert report['status']=='REVIEW_REQUIRED' and report['stopped_verified']
    assert not report['fresh_retry_eligible']


def test_outcome_publication_gap_stays_visible_without_implicit_retry(tmp_path,monkeypatch):
    values=setup(tmp_path);write=m.records.write_record
    def interrupted(path,value):
        if Path(path).name=='outcome.json':raise OSError('Interrupted outcome publication')
        return write(path,value)
    monkeypatch.setattr(m.records,'write_record',interrupted)
    with pytest.raises(OSError,match='Interrupted'):invoke(tmp_path,values)
    report=m.inspect_child(tmp_path/'attempt',request_id=values[2]['request_id'])
    assert report['status']=='REVIEW_REQUIRED' and report['stopped_verified']
    assert report['outcome'] is None and not report['fresh_retry_eligible']


def test_failed_native_exit_is_recorded_and_changed_retry_request_refuses(tmp_path):
    values=setup(tmp_path);values[3].environment['SIM_MODE']='fail'
    report=invoke(tmp_path,values)
    assert report['status']=='FAILED' and report['outcome']['returncode']==7 and report['fresh_retry_eligible']
    prepared,parent,request,native=values
    (prepared/'input.pdb').write_text('new request bytes')
    changed=m.make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])
    with pytest.raises(RecipeError):invoke(tmp_path,(prepared,parent,changed,native),'retry',retry_from=tmp_path/'attempt')
    assert not (tmp_path/'retry').exists()


def test_live_child_is_visible_and_cannot_be_retried_until_timeout(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import time
    values=setup(tmp_path);values[3].environment['SIM_MODE']='timeout'
    with ThreadPoolExecutor(max_workers=1) as pool:
        task=pool.submit(invoke,tmp_path,values,timeout_seconds=1.5)
        marker=tmp_path/'attempt/native/fdp/job/child.pid'
        deadline=time.monotonic()+4
        while not marker.exists() and not task.done() and time.monotonic()<deadline:time.sleep(.02)
        assert marker.exists(), task.result() if task.done() else 'Child did not start'
        live=m.inspect_child(tmp_path/'attempt',request_id=values[2]['request_id'])
        assert live['process']['state']=='LIVE' and not live['stopped_verified']
        assert not live['fresh_retry_eligible']
        with pytest.raises(RecipeError,match='not qualified'):
            invoke(tmp_path,values,'retry',retry_from=tmp_path/'attempt')
        result=task.result(timeout=10)
    assert result['status']=='TIMED_OUT' and result['stopped_verified']
    assert not (tmp_path/'retry').exists()


def test_request_rejects_nonportable_input_name_and_nonobject_plan(tmp_path):
    prepared,parent,request,native=setup(tmp_path)
    native_plan=json.loads((prepared/'native-plan.json').read_text())
    name='bad'+chr(92)+'input.pdb';(prepared/name).write_text('bad name')
    native_plan['args'].append(name);(prepared/'native-plan.json').write_text(json.dumps(native_plan))
    with pytest.raises(RecipeError):m.make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])
    (prepared/'plan.json').write_text('[]');(prepared/'native-plan.json').write_text('[]')
    with pytest.raises(RecipeError):m.make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])


def test_rehashed_outcome_cannot_change_its_owner_binding(tmp_path):
    from hashlib import sha256
    values=setup(tmp_path);invoke(tmp_path,values)
    path=tmp_path/'attempt/outcome.json';value=json.loads(path.read_text())
    value['ownership_sha256']='0'*64;value.pop('record_sha256')
    value['record_sha256']=sha256(m.records._canonical(value)).hexdigest();path.write_text(json.dumps(value))
    with pytest.raises(RecipeError,match='ownership'):m.inspect_child(tmp_path/'attempt',request_id=values[2]['request_id'])


def test_parent_change_after_worker_exit_prevents_successful_outcome(tmp_path,monkeypatch):
    values=setup(tmp_path);parent=values[1]
    name=json.loads((parent/'parent.json').read_text())['parts'][0]['name']
    part=parent/name;original_bytes=part.read_bytes();runner=m.ChildProcesses.runner
    def changed(self,phase):
        invoke=runner(self,phase)
        def call(*args,**kwargs):
            code=invoke(*args,**kwargs)
            part.write_bytes(original_bytes+b'changed after worker')
            return code
        return call
    monkeypatch.setattr(m.ChildProcesses,'runner',changed)
    report=invoke(tmp_path,values)
    assert report['status']=='REVIEW_REQUIRED' and report['stopped_verified']
    assert report['outcome']['parent_transport_verified'] is False
    assert not report['fresh_retry_eligible']
    part.write_bytes(original_bytes)
    assert not m.inspect_child(tmp_path/'attempt',request_id=values[2]['request_id'])['fresh_retry_eligible']
