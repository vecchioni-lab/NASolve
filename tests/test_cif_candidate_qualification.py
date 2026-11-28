"""Isolated qualification owns processes but grants no linked/refinement approval."""
import os
import subprocess
import sys
from pathlib import Path
import pytest
from tests.test_cif_repair_process import inventory


def test_qualification_ownership_is_distinct_and_read_only(tmp_path):
    from nasolve.cif_candidate_qualification import CandidateQualificationProcesses, inspect_candidate_qualification_processes
    (tmp_path/'inputs').mkdir();(tmp_path/'inputs/source.cif').write_text('exact source')
    owner=CandidateQualificationProcesses(tmp_path)
    work=tmp_path/'native/000/capture';work.mkdir(parents=True)
    assert owner.runner('native-000')([sys.executable,'-c','print("owned")'],cwd=work,log_path=work/'native.log',environment=dict(os.environ),timeout_seconds=3)==0
    assert owner.finish('RETURNED')
    before=inventory(tmp_path);state=inspect_candidate_qualification_processes(tmp_path)
    assert state['state']=='STOPPED' and not state['retry_authorized']
    assert state['header']['policy_id']=='cif-candidate-qualification-process-v1'
    assert state['header']['inputs']=={'anchor':'qualification_directory','path':'inputs'}
    assert inventory(tmp_path)==before and not (tmp_path/'ownership/repair.json').exists()
    with pytest.raises(ValueError):owner.runner('attribution')


def test_partial_qualification_timeout_preserves_inputs(tmp_path):
    from nasolve.cif_candidate_qualification import CandidateQualificationProcesses, inspect_candidate_qualification_processes
    (tmp_path/'inputs').mkdir();(tmp_path/'inputs/source.cif').write_text('exact source')
    owner=CandidateQualificationProcesses(tmp_path);work=tmp_path/'native/001/capture';work.mkdir(parents=True)
    with pytest.raises(subprocess.TimeoutExpired):
        owner.runner('native-001')([sys.executable,'-c',"import time;from pathlib import Path;Path('partial').write_text('keep');time.sleep(30)"],cwd=work,log_path=work/'native.log',environment=dict(os.environ),timeout_seconds=.4)
    assert owner.finish('RAISED') and (work/'partial').read_text()=='keep'
    assert inspect_candidate_qualification_processes(tmp_path)['state']=='STOPPED'


@pytest.mark.parametrize('phase',['native-baseline','native-002','original-gradient','../native-000'])
def test_qualification_refuses_unrequested_phases(tmp_path,phase):
    from nasolve.cif_candidate_qualification import CandidateQualificationProcesses
    (tmp_path/'inputs').mkdir();owner=CandidateQualificationProcesses(tmp_path)
    with pytest.raises(ValueError):owner.runner(phase)


@pytest.mark.parametrize('defect',['changed_input','extra_input','symlink','repair_reader','second_owner'])
def test_scope_and_input_identity_fail_closed(tmp_path,defect):
    from nasolve.cif_candidate_qualification import CandidateQualificationProcesses, inspect_candidate_qualification_processes
    from nasolve.cif_repair_process import inspect_prepared_repair_processes
    (tmp_path/'inputs').mkdir();source=tmp_path/'inputs/source.cif';source.write_text('frozen')
    owner=CandidateQualificationProcesses(tmp_path)
    if defect=='changed_input':source.write_text('different')
    if defect=='extra_input':(source.parent/'extra').write_text('different')
    if defect=='symlink':(source.parent/'link').symlink_to(source)
    before=inventory(tmp_path)
    with pytest.raises((ValueError,FileExistsError)):
        if defect=='repair_reader':inspect_prepared_repair_processes(tmp_path)
        elif defect=='second_owner':CandidateQualificationProcesses(tmp_path)
        else:inspect_candidate_qualification_processes(tmp_path)
    assert inventory(tmp_path)==before


@pytest.mark.parametrize('publication',['missing_header','missing_job','missing_identity'])
def test_unknown_publication_never_grants_recovery(tmp_path,monkeypatch,publication):
    from nasolve.cif_candidate_qualification import CandidateQualificationProcesses, inspect_candidate_qualification_processes
    from nasolve import cif_repair_process as shared
    (tmp_path/'inputs').mkdir();owner=CandidateQualificationProcesses(tmp_path)
    monkeypatch.setattr(shared,'coordinator_alive',lambda identity:False)
    work=tmp_path/'native/000/capture';work.mkdir(parents=True)
    if publication=='missing_header':(tmp_path/'ownership/qualification.json').unlink()
    elif publication=='missing_job':(tmp_path/'ownership/phases/native-000').mkdir(parents=True)
    else:
        def unobserved(*args,**kwargs):raise RuntimeError('uncertain spawn')
        monkeypatch.setattr(shared,'run_owned_command',unobserved)
        with pytest.raises(RuntimeError):owner.runner('native-000')([sys.executable,'-c','pass'],cwd=work,log_path=work/'native.log',environment=dict(os.environ),timeout_seconds=3)
    before=inventory(tmp_path);state=inspect_candidate_qualification_processes(tmp_path)
    assert state['state']=='UNKNOWN' and state['activity'] is None and not state['retry_authorized']
    assert inventory(tmp_path)==before


def test_two_distinct_seeds_require_separate_immutable_jobs(tmp_path):
    from nasolve.cif_candidate_qualification import CandidateQualificationProcesses, inspect_candidate_qualification_processes
    (tmp_path/'inputs').mkdir();owner=CandidateQualificationProcesses(tmp_path)
    for phase in ('000','001'):
        work=tmp_path/'native'/phase/'capture';work.mkdir(parents=True)
        runner=owner.runner('native-'+phase)
        runner([sys.executable,'-c','pass'],cwd=work,log_path=work/'native.log',environment=dict(os.environ),timeout_seconds=3)
        before=inventory(tmp_path)
        with pytest.raises(ValueError):runner([sys.executable,'-c','pass'],cwd=work,log_path=work/'native.log',environment=dict(os.environ),timeout_seconds=3)
        assert inventory(tmp_path)==before
    assert inspect_candidate_qualification_processes(tmp_path)['state']=='LIVE'
    owner.finish('RETURNED');state=inspect_candidate_qualification_processes(tmp_path)
    assert set(state['phases'])=={'native-000','native-001'}
    assert len({row['job']['invocation_id'] for row in state['phases'].values()})==2
    assert not any('native_usable' in row for row in state['phases'].values())
