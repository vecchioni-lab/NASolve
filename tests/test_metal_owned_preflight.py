"""Optional owned input checks preserve science and expose process completion."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,subprocess
import pytest
from nasolve import campaign_records as records,refine_doctor
from nasolve.metal import child_session as m,scattering as s,parent_archive as p
from nasolve.metal.recipe import RecipeError
from tests.test_metal_child_session import setup
from tests.test_metal_child_review import republish
from tests.test_metal_child_process import inventory
from tests.test_metal_integration import mtz_dump


def test_scattering_and_free_r_use_optional_runner_without_changing_parser(tmp_path):
    calls=[]
    flags=dict(free_fraction=.05,free_independent_groups=100,paired_friedel_groups=100,
               inconsistent_friedel_flag_groups=0,resolution_shells=[])
    def runner(argv,**kwargs):
        calls.append((argv,kwargs))
        if '-c' in argv:output='NASOLVE_SCATTERING='+json.dumps([dict(element='Hg',f_prime=-1.,f_double_prime=8.,table_sha256='1'*64,native_version='2.2.1-6174')])
        elif len(argv)>2:output='NASOLVE_FREE_R_AUDIT_JSON:'+json.dumps(flags)
        else:output=mtz_dump()
        return subprocess.CompletedProcess(argv,0,stdout=output,stderr='')
    with patch('subprocess.run',side_effect=AssertionError('Default runner must not run')):
        assert s.inspect_observations(tmp_path/'data',executable='unused',command_runner=runner)==s.observation_metadata(mtz_dump())
        assert s.reference_scattering(['Hg'],.92,executable='unused',version='2.2.1',command_runner=runner)[0]['f_double_prime']==8
        audit=refine_doctor.audit_free_r_flags(tmp_path/'data','FreeR_flag',0,tmp_path/'python',tmp_path,command_runner=runner)
    assert audit.valid and len(calls)==3 and [v[1]['timeout'] for v in calls]==[60,60,180]
    assert (tmp_path/'audit_free_r.py').read_text()==refine_doctor._AUDIT_SCRIPT.lstrip()


def owned_setup(tmp_path,monkeypatch,defect=None):
    values,native=setup(tmp_path,monkeypatch)
    original=native.executables['phenix.python'].read_text()
    flag_output='NASOLVE_FREE_R_AUDIT_JSON:'+json.dumps(dict(free_fraction=.05,free_independent_groups=100,paired_friedel_groups=100,inconsistent_friedel_flag_groups=0,resolution_shells=[]))
    prefix="import sys,time\nfrom pathlib import Path\nif len(sys.argv)>1 and Path(sys.argv[1]).name=='audit_free_r.py':\n print("+repr(flag_output)+");sys.exit(0)\nif len(sys.argv)>1 and sys.argv[1]=='--preflight':\n"
    prefix+=" time.sleep(20)\n" if defect=='timeout' else " print('owned synthetic input inspection');sys.exit(0)\n"
    native.executables['phenix.python'].write_text(original.split('\n',1)[0]+'\n'+prefix+original.split('\n',1)[1])
    # Scientific outputs are controlled fixtures; each inspection still launches
    # a real synthetic process through the injected shared owner.
    metadata=m.inspect_observations;references=m.reference_scattering;flags=m.audit_free_r_flags
    def invoke(function,*args,**kwargs):
        runner=kwargs.pop('command_runner')
        runner([str(native.executables['phenix.python']),'--preflight'],env=native.environment,text=True,
               stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=.15 if defect=='timeout' else 5,check=False)
        value=function(*args,**kwargs)
        if defect=='metadata' and function is metadata:value=dict(value,wavelength_A=99.)
        return value
    monkeypatch.setattr(m,'inspect_observations',lambda *a,**k:invoke(metadata,*a,**k))
    monkeypatch.setattr(m,'reference_scattering',lambda *a,**k:invoke(references,*a,**k))
    monkeypatch.setattr(m,'audit_free_r_flags',refine_doctor.audit_free_r_flags)
    return values,native


def run(tmp_path,values,native,**kwargs):
    return m.run_audited_child(values[2],values[1],values[3],request_id=values[3]['request_id'],
        run_relative='dataset/AutoMR/run_001',endpoint_relative='Metal/xyz_001',session_directory=tmp_path/'session',
        native=native,timeout_seconds=5,owned_preflight=True,**kwargs)


@pytest.mark.parametrize('retained',[False,True])
def test_owned_preflight_flows_through_normal_session_and_cold_reader(tmp_path,monkeypatch,retained):
    values,native=owned_setup(tmp_path,monkeypatch);before=inventory(values[2])
    if retained:
        with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256']) as handle:
            result=run(tmp_path,values,native,retained_parent=handle)
    else:result=run(tmp_path,values,native)
    assert result['schema_version']==3 and result['owned_preflight'] is True
    assert result['scientific_acceptance']=='NOT_ASSESSED' and inventory(values[2])==before
    from nasolve.metal import preflight_process as owner
    proof=records.read_record(tmp_path/'session/owned-preflight.json')
    inspected=owner.inspect_preflight(tmp_path/'session/preflight',inspection_id=proof['inspection_id'])
    assert inspected['stopped_verified'] and len(inspected['phases'])==3
    moved=tmp_path/'relocated-session';(tmp_path/'session').rename(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('Cold reader cannot execute')):
        report=m.inspect_audited_child(moved,review_id=result['record_sha256'])
    assert report['result']==result['result'] and report['preflight_stopped_verified']


@pytest.mark.parametrize('defect',['metadata','timeout','uncertain','missing-seal'])
def test_preflight_failure_never_starts_fdp(tmp_path,monkeypatch,defect):
    values,native=owned_setup(tmp_path,monkeypatch,defect)
    if defect=='uncertain':monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    if defect=='missing-seal':
        write=records.write_record
        def interrupted(path,value,**kwargs):
            if path.name=='inspection.json':raise OSError('Lost input-check receipt')
            return write(path,value,**kwargs)
        monkeypatch.setattr(records,'write_record',interrupted)
    with patch.object(m.child_process,'run_child',side_effect=AssertionError('No refinement')):
        with pytest.raises((RecipeError,OSError,subprocess.TimeoutExpired)):run(tmp_path,values,native)
    assert not (tmp_path/'session/attempt').exists() and not (tmp_path/'session/review.json').exists()
    assert (tmp_path/'session/failure.json').exists()
    assert (tmp_path/'session/preflight/ownership').is_dir()


def test_changed_preflight_proof_cannot_be_resealed_as_qualified(tmp_path,monkeypatch):
    values,native=owned_setup(tmp_path,monkeypatch);result=run(tmp_path,values,native)
    path=tmp_path/'session/owned-preflight.json';proof=records.read_record(path);proof['inspection_id']='0'*64
    records.write_record(path,proof,replace=True);changed=republish(tmp_path/'session',result,'owned-preflight.json')
    with pytest.raises(RecipeError):m.inspect_audited_child(tmp_path/'session',review_id=changed['record_sha256'])


@pytest.mark.parametrize('defect',['missing-phase','changed-log','changed-script','raised-seal'])
def test_cold_preflight_requires_exact_completed_evidence(tmp_path,monkeypatch,defect):
    values,native=owned_setup(tmp_path,monkeypatch);result=run(tmp_path,values,native)
    root=tmp_path/'session/preflight'
    if defect=='missing-phase':(root/'ownership/phases/native-scattering/finished.json').unlink()
    elif defect=='changed-log':(root/'native/observations/job/native.log').write_text('changed')
    elif defect=='changed-script':(root/'native/free-r/job/audit_free_r.py').write_text('changed')
    else:
        path=root/'ownership/finished.json';value=records.read_record(path);value['outcome']='RAISED';records.write_record(path,value,replace=True)
    with patch('subprocess.Popen',side_effect=AssertionError('No rerun')):
        with pytest.raises(RecipeError):m.inspect_audited_child(tmp_path/'session',review_id=result['record_sha256'])
