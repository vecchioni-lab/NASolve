"""A fresh copied worker must carry the maintained sibling modules it imports."""
from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from unittest.mock import patch
import pytest
from nasolve.metal import child_process as m
from nasolve.metal.recipe import RecipeError,digest
from tests.test_metal_child_process import setup,invoke

NAMES={'_fdp_native.py','fit_diagnostics.py','anomalous_maps.py','map_diagnostics.py'}


def test_copied_worker_has_complete_pinned_standalone_imports(tmp_path):
    values=setup(tmp_path);request=values[2]
    assert request['schema_version']==2 and set(request['worker_files'])==NAMES
    report=invoke(tmp_path,values)
    assert report['status']=='COMPLETED' and report['worker_bundle_pinned']
    root=tmp_path/'attempt/inputs'
    for name,ref in request['worker_files'].items():
        raw=(root/name).read_bytes()
        assert len(raw)==ref['size'] and sha256(raw).hexdigest()==ref['sha256']
    code="""from pathlib import Path
import _fdp_native,fit_diagnostics,anomalous_maps,map_diagnostics
root=Path.cwd().resolve()
for m in [_fdp_native,fit_diagnostics,anomalous_maps,map_diagnostics]:
 assert Path(m.__file__).resolve().parent==root
assert anomalous_maps.common is map_diagnostics
print('Maintained helper imports are local')
"""
    result=subprocess.run([sys.executable,'-B','-c',code],cwd=root,env=dict(os.environ,PYTHONPATH='',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('problem',['missing','changed','extra','bad-size'])
def test_rehashed_bundle_changes_refuse_before_new_attempt(tmp_path,problem):
    prepared,parent,request,native=setup(tmp_path)
    if problem=='missing':request['worker_files'].pop('anomalous_maps.py')
    elif problem=='changed':request['worker_files']['fit_diagnostics.py']['sha256']='0'*64
    elif problem=='extra':request['worker_files']['other.py']=request['worker_files']['fit_diagnostics.py']
    else:request['worker_files']['fit_diagnostics.py']['size']=True
    request.pop('request_id');request['request_id']=digest(request)
    with patch('subprocess.Popen',side_effect=AssertionError('No worker')):
        with pytest.raises(ValueError):invoke(tmp_path,(prepared,parent,request,native))
    assert not (tmp_path/'attempt').exists()


def test_prepared_inputs_cannot_shadow_a_maintained_helper(tmp_path):
    prepared,parent,request,native=setup(tmp_path)
    (prepared/'fit_diagnostics.py').write_text('raise AssertionError("untrusted helper")')
    p=prepared/'native-plan.json';value=json.loads(p.read_text());value['args'].append('fit_diagnostics.py');p.write_text(json.dumps(value))
    with pytest.raises(RecipeError,match='Reserved'):
        m.make_request(prepared,parent_manifest_sha256=request['parent_manifest_sha256'])


def test_changed_helper_snapshot_cannot_be_inspected_as_complete(tmp_path):
    values=setup(tmp_path);invoke(tmp_path,values)
    p=tmp_path/'attempt/inputs/fit_diagnostics.py';p.write_bytes(p.read_bytes()+b'changed')
    with pytest.raises(RecipeError):m.inspect_child(tmp_path/'attempt',request_id=values[2]['request_id'])


def legacy_attempt(tmp_path,values,failed):
    """Construct the v1 process contract through the unchanged shared owner."""
    prepared,parent,request,native=values
    request=dict(request);request.pop('worker_files');request['schema_version']=1;request.pop('request_id');request['request_id']=digest(request)
    root=tmp_path/'legacy';inputs=root/'inputs';inputs.mkdir(parents=True)
    payload=m._inputs(prepared,request['files'])
    for name,raw in payload.items():(inputs/name).write_bytes(raw)
    shutil.copyfile(Path(m.__file__).with_name('_fdp_native.py'),inputs/'_fdp_native.py')
    (inputs/'request.json').write_text(json.dumps(request))
    executable=Path(native.executables['phenix.python']);executable_sha=sha256(executable.read_bytes()).hexdigest()
    m.records.write_record(inputs/'execution.json',dict(native_version=native.version,native_executable_sha256=executable_sha,
        request_id=request['request_id'],parent_manifest_sha256=request['parent_manifest_sha256'],retry_of=None))
    with m.parent_archive.materialized_parent_inputs(parent,request['parent_manifest_sha256']):
        owner=m.ChildProcesses(root);work=root/'native/fdp/job';work.mkdir(parents=True)
        for name,raw in payload.items():(work/name).write_bytes(raw)
        if failed:native.environment['SIM_MODE']='fail'
        code=owner.runner('native-fdp')([str(executable),'-B',str(inputs/'_fdp_native.py'),'native-plan.json'],cwd=work,log_path=work/'native.log',environment=native.environment,timeout_seconds=5)
        assert owner.finish('RETURNED')
    m.records.write_record(root/'outcome.json',dict(kind='metal-fdp-child-process-outcome',schema_version=1,
        policy_id=m.POLICY,request_id=request['request_id'],parent_manifest_sha256=request['parent_manifest_sha256'],
        parent_transport_verified=True,native_executable_sha256=executable_sha,ownership_sha256=owner.header['record_sha256'],
        status='FAILED' if failed else 'COMPLETED',returncode=code,stopped_verified=True,error=None,retry_of=None,
        scientific_acceptance='NOT_ASSESSED',retirement_authorized=False))
    return root,request


@pytest.mark.parametrize('failed',[False,True])
def test_v1_process_evidence_stays_readable_but_cannot_launch_or_retry(tmp_path,failed):
    values=setup(tmp_path);root,request=legacy_attempt(tmp_path,values,failed)
    report=m.inspect_child(root,request_id=request['request_id'])
    assert report['status']==('FAILED' if failed else 'COMPLETED') and report['stopped_verified']
    assert report['worker_bundle_pinned'] is False and report['fresh_retry_eligible'] is False
    with patch('subprocess.Popen',side_effect=AssertionError('No v1 launch')):
        with pytest.raises(RecipeError,match='Legacy'):
            m.run_child(values[0],values[1],request,request_id=request['request_id'],attempt_directory=tmp_path/'new',native=values[3])
    assert not (tmp_path/'new').exists()


def test_discovery_release_label_defers_exact_build_check_to_pinned_worker(tmp_path):
    values=setup(tmp_path);values[3].version='2.2.1'
    report=invoke(tmp_path,values)
    assert report['status']=='COMPLETED' and report['worker_bundle_pinned']
    execution=m.records.read_record(tmp_path/'attempt/inputs/execution.json')
    assert execution['native_version']=='2.2.1'
    assert report['scientific_acceptance']=='NOT_ASSESSED'


def test_worker_rejects_other_build_before_refinement(tmp_path,monkeypatch):
    import runpy
    from types import ModuleType,SimpleNamespace
    def no_refine(*args,**kwargs):
        raise AssertionError('A different build must not start refinement')
    cli=ModuleType('iotbx.cli_parser');cli.run_program=no_refine
    refine=ModuleType('phenix.programs.phenix_refine')
    refine.Program=object;refine.PhenixRefineParser=object;refine.custom_process_arguments=no_refine
    phenix=ModuleType('phenix');phenix.phenix_info=SimpleNamespace(version_and_release_tag=lambda:('2.2.1','9999'))
    for name,module in [('iotbx.cli_parser',cli),('phenix.programs.phenix_refine',refine),('phenix',phenix)]:
        monkeypatch.setitem(sys.modules,name,module)
    plan=tmp_path/'native-plan.json';plan.write_text(json.dumps({'plan':{}}))
    worker=runpy.run_path(str(Path(m.__file__).with_name('_fdp_native.py')))
    with pytest.raises(ValueError,match='Unsupported native version: 2.2.1-9999'):
        worker['run'](str(plan))
    assert list(tmp_path.iterdir())==[plan]
