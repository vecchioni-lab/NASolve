"""Complete only an exact saved phasing result; no native retry or reselection."""
import json
import pytest
from nasolve import cli
from tests.test_autosol_selected_reference import selected_run, run_autosol


def test_complete_publication_option_is_explicit_and_does_not_discover_phenix(tmp_path,monkeypatch):
    monkeypatch.setattr(cli,'load_config',lambda:object())
    monkeypatch.setattr(cli,'_workspace_run',lambda *a:tmp_path)
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**k:pytest.fail('Completion must not discover Phenix'))
    # A missing receipt is a reported recovery refusal, not an unknown CLI option.
    assert cli.main(['autosol',str(tmp_path),'--complete-publication'])==2


@pytest.fixture
def interrupted(selected_run,tmp_path,monkeypatch):
    import nasolve.cif_postmr_publication as publication
    run,exact,calls,identifier=selected_run
    original=publication._publish_run_report
    def fail(path,previous,report):
        if report.get('stage')=='autosol':raise RuntimeError('explicit interruption before run-report save')
        return original(path,previous,report)
    with monkeypatch.context() as m:
        m.setattr(publication,'_publish_run_report',fail)
        with pytest.raises(RuntimeError,match='explicit interruption'):run_autosol(run,tmp_path)
    assert 'autosol' not in json.loads((run/'report.json').read_text())
    assert (run/'AutoSol/publication.json').is_file()
    return run,exact,calls,identifier


def stop(monkeypatch):
    import nasolve.autosol_publication as publication
    monkeypatch.setattr(publication,'coordinator_alive',lambda identity:False)
    monkeypatch.setattr(publication,'process_alive',lambda identity:False)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Completion must not launch native tools'))
    return publication


def test_complete_exact_saved_result_preserves_later_selection_and_is_idempotent(interrupted,monkeypatch):
    from nasolve import checkpoints
    from tests.test_cif_postmr_publication import snapshot
    from nasolve.autosol_reference import validate_result_reference
    run,_,_,identifier=interrupted
    checkpoints.select_checkpoint(run,'postmr');before=snapshot(run)
    publication=stop(monkeypatch)
    result=publication.complete_autosol_publication(run)
    assert result.status=='AUTOSOL_READY' and result.matched_distance==0.
    report=json.loads((run/'report.json').read_text())
    assert validate_result_reference(run,report)['checkpoint_id']==identifier
    assert checkpoints.read_registry(run)[1]['current']=='postmr'
    after=snapshot(run)
    assert all(after[n]==value for n,value in before.items() if n!='report.json')
    assert set(after)-set(before)=={'AutoSol/.publication.lock'}
    assert publication.complete_autosol_publication(run)==result
    assert snapshot(run)==after


@pytest.mark.parametrize('coordinator,group',[(True,False),(None,False),(False,True),(False,None)])
def test_active_or_unknown_producer_group_never_authorizes_a_save(interrupted,monkeypatch,coordinator,group):
    from tests.test_cif_postmr_publication import snapshot
    from nasolve.autosol import AutoSolPreparationError
    run,*_=interrupted;publication=stop(monkeypatch)
    monkeypatch.setattr(publication,'coordinator_alive',lambda identity:coordinator)
    monkeypatch.setattr(publication,'process_alive',lambda identity:group)
    before=snapshot(run)
    with pytest.raises(AutoSolPreparationError,match='active or unknown'):publication.complete_autosol_publication(run)
    assert snapshot(run)==before


@pytest.mark.parametrize('defect',['run-report','phase','map','model','result','execution','publication','missing-receipt','symlink'])
def test_changed_missing_or_conflicting_saved_evidence_is_never_adopted(interrupted,tmp_path,monkeypatch,defect):
    from tests.test_cif_postmr_publication import snapshot
    from nasolve.autosol import AutoSolPreparationError
    from nasolve.campaign_records import read_record
    from nasolve.run_context import resolve_artifact_path
    run,*_=interrupted;publication=stop(monkeypatch)
    record=read_record(run/'AutoSol/report.json')
    if defect=='run-report':
        path=run/'report.json';data=json.loads(path.read_text());data['newer_work']='preserve me';path.write_text(json.dumps(data))
    elif defect in {'phase','map'}:
        key='refinement_data' if defect=='phase' else 'density_modified_map'
        path=resolve_artifact_path(record['outputs'][key],run);path.write_bytes(path.read_bytes()+b'changed')
    elif defect=='model':
        ref=read_record(run/'AutoSol/site-reference.json')['model'];path=resolve_artifact_path(ref,run);path.write_text(path.read_text()+'REMARK changed\n')
    elif defect=='missing-receipt':(run/'AutoSol/publication.json').unlink()
    elif defect=='symlink':
        path=run/'AutoSol/publication.json';other=tmp_path/'outside.json';path.rename(other);path.symlink_to(other)
    else:
        name={'result':'report','execution':'execution','publication':'publication'}[defect]
        path=run/'AutoSol'/f'{name}.json';path.write_text(path.read_text()+'invalid')
    before=snapshot(run)
    with pytest.raises(AutoSolPreparationError):publication.complete_autosol_publication(run)
    assert snapshot(run)==before


def test_relocated_completion_does_not_consult_historical_paths_or_select_again(interrupted,tmp_path,monkeypatch):
    from nasolve import checkpoints
    run,exact,calls,identifier=interrupted
    publication=stop(monkeypatch)
    moved=run.parent/'relocated_run';run.rename(moved);assert not run.exists()
    runtime=exact['runtime'];runtime['model']=moved/runtime['model'].relative_to(run)
    for key in ('dictionaries','phils'):
        runtime[key]=[moved/p.relative_to(run) for p in runtime[key]]
    def read(root,number):
        assert root==moved/'PostMR/DictionaryEngine/request' and number==1
        calls.append(number);return exact
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',read)
    result=publication.complete_autosol_publication(moved)
    assert result.status=='AUTOSOL_READY' and result.heavy_atom_model.is_relative_to(moved)
    assert result.refinement_data.is_relative_to(moved)
    assert checkpoints.read_registry(moved)[1]['current']==identifier


def test_completed_publication_is_read_only_even_when_original_group_remains_alive(selected_run,tmp_path,monkeypatch):
    from tests.test_cif_postmr_publication import snapshot
    run,*_=selected_run;original=run_autosol(run,tmp_path);publication=stop(monkeypatch)
    monkeypatch.setattr(publication,'coordinator_alive',lambda identity:True)
    monkeypatch.setattr(publication,'process_alive',lambda identity:True)
    before=snapshot(run)
    assert publication.complete_autosol_publication(run)==original
    assert snapshot(run)==before


def test_cli_completes_saved_result_without_installation_or_checkpoint_reselection(interrupted,monkeypatch,capsys):
    run,*_=interrupted;stop(monkeypatch)
    monkeypatch.setattr(cli,'load_config',lambda:object())
    monkeypatch.setattr(cli,'_workspace_run',lambda *a:run)
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**k:pytest.fail('No Phenix discovery'))
    assert cli.main(['autosol',str(run),'--complete-publication'])==0
    assert 'AUTOSOL_READY' in capsys.readouterr().out


def test_interruption_during_completion_keeps_same_receipts_and_can_finish(interrupted,monkeypatch):
    import nasolve.cif_postmr_publication as writer
    from tests.test_cif_postmr_publication import snapshot
    run,*_=interrupted;publication=stop(monkeypatch);before=snapshot(run)
    with monkeypatch.context() as m:
        m.setattr(writer,'_publish_run_report',lambda *a:(_ for _ in ()).throw(KeyboardInterrupt()))
        with pytest.raises(KeyboardInterrupt):publication.complete_autosol_publication(run)
    after=snapshot(run)
    assert all(after[n]==value for n,value in before.items())
    assert publication.complete_autosol_publication(run).status=='AUTOSOL_READY'


def test_changed_run_report_during_proof_read_is_preserved(interrupted,monkeypatch):
    from nasolve import checkpoints
    from nasolve.autosol import AutoSolPreparationError
    run,*_=interrupted;publication=stop(monkeypatch);original=checkpoints._validate_preparation
    def changed(*args,**kwargs):
        original(*args,**kwargs)
        path=run/'report.json';report=json.loads(path.read_text());report['newer_work']='preserve';path.write_text(json.dumps(report))
    monkeypatch.setattr(checkpoints,'_validate_preparation',changed)
    with pytest.raises(AutoSolPreparationError,match='changed since'):publication.complete_autosol_publication(run)
    assert json.loads((run/'report.json').read_text())['newer_work']=='preserve'


@pytest.mark.parametrize('defect',['site-outcome','command','target-hash'])
def test_rehashed_receipts_do_not_replace_scientific_or_launch_checks(interrupted,monkeypatch,defect):
    from nasolve.campaign_records import read_record,write_record
    from nasolve.checkpoints import _file_reference
    from nasolve.autosol import AutoSolPreparationError
    from hashlib import sha256
    run,*_=interrupted;publication=stop(monkeypatch)
    path=run/'AutoSol/report.json';result=read_record(path)
    if defect=='site-outcome':result['site_validation']['best_distance']+=1.
    elif defect=='command':result['command']=['another-command']
    if defect!='target-hash':result=write_record(path,result,replace=True)
    pubpath=run/'AutoSol/publication.json';pub=read_record(pubpath)
    pub['result']=_file_reference(path,run)
    target=publication._target(json.loads((run/'report.json').read_text()),result)
    pub['published_run_report_sha256']=sha256(publication._report_bytes(target)).hexdigest()
    if defect=='target-hash':pub['published_run_report_sha256']='0'*64
    write_record(pubpath,pub,replace=True)
    before=(run/'report.json').read_bytes()
    with pytest.raises(AutoSolPreparationError):publication.complete_autosol_publication(run)
    assert (run/'report.json').read_bytes()==before


def test_finished_warning_can_be_saved_without_promoting_phases(selected_run,tmp_path,monkeypatch):
    from nasolve.autosol import execute_autosol
    from nasolve.autorefine import _effective_phase
    from tests.test_autosol import make_autosol,make_mtz_dump
    import nasolve.cif_postmr_publication as writer
    run,*_=selected_run
    with monkeypatch.context() as m:
        m.setattr(writer,'_publish_run_report',lambda *a:(_ for _ in ()).throw(RuntimeError('interrupted warning')))
        with pytest.raises(RuntimeError,match='interrupted warning'):
            execute_autosol(run,make_autosol(tmp_path,(20.,2.,3.),return_code=1),make_mtz_dump(tmp_path),environment={'PATH':'/usr/bin:/bin'})
    publication=stop(monkeypatch);result=publication.complete_autosol_publication(run)
    assert result.status=='AUTOSOL_WARNING' and result.refinement_data is None
    report=json.loads((run/'report.json').read_text())
    assert report['autosol']['use_for_refinement'] is False and _effective_phase(report,{},run) is None


def test_old_completed_run_without_new_receipts_remains_readable_but_is_not_retrofitted(selected_run,tmp_path,monkeypatch):
    from nasolve import checkpoints
    from nasolve.autosol import AutoSolPreparationError
    from nasolve.autosol_reference import validate_result_reference
    from tests.test_cif_postmr_publication import snapshot
    run,*_=selected_run;run_autosol(run,tmp_path)
    (run/'AutoSol/execution.json').unlink();(run/'AutoSol/publication.json').unlink()
    publication=stop(monkeypatch);before=snapshot(run)
    assert checkpoints.read_registry(run)[1]['schema_version']==5
    assert validate_result_reference(run,json.loads((run/'report.json').read_text())) is not None
    with pytest.raises(AutoSolPreparationError):publication.complete_autosol_publication(run)
    assert snapshot(run)==before


def test_completed_report_rollback_during_validation_cannot_report_success(selected_run,tmp_path,monkeypatch):
    from nasolve import checkpoints
    from nasolve.autosol import AutoSolPreparationError
    run,*_=selected_run;previous=(run/'report.json').read_bytes()
    run_autosol(run,tmp_path);publication=stop(monkeypatch)
    original=checkpoints._validate_preparation
    def rollback(*args,**kwargs):
        original(*args,**kwargs)
        (run/'report.json').write_bytes(previous)
    monkeypatch.setattr(checkpoints,'_validate_preparation',rollback)
    with pytest.raises(AutoSolPreparationError,match='changed during'):
        publication.complete_autosol_publication(run)
    assert (run/'report.json').read_bytes()==previous


def test_ordinary_autosol_command_finishes_saved_result_without_sdk(interrupted,monkeypatch,capsys):
    from nasolve import checkpoints
    from tests.test_cif_postmr_publication import snapshot
    run,*_=interrupted;checkpoints.select_checkpoint(run,'postmr');stop(monkeypatch)
    monkeypatch.setattr(cli,'load_config',lambda:object())
    monkeypatch.setattr(cli,'_workspace_run',lambda requested,config:requested)
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**k:pytest.fail('Saved completion needs no SDK discovery'))
    assert cli.main(['autosol',str(run)])==0
    assert 'Saved AutoSol result' in capsys.readouterr().out
    assert checkpoints.read_registry(run)[1]['current']=='postmr'
    after=snapshot(run)
    assert cli.main(['autosol',str(run/'report.json')])==0
    assert snapshot(run)==after


@pytest.mark.parametrize('defect',['active','unknown','malformed','missing-result','newer-report'])
def test_ordinary_saved_completion_never_falls_back_to_native_on_failure(interrupted,monkeypatch,defect):
    from tests.test_cif_postmr_publication import snapshot
    run,*_=interrupted;publication=stop(monkeypatch)
    if defect in {'active','unknown'}:
        monkeypatch.setattr(publication,'process_alive',lambda identity:True if defect=='active' else None)
    elif defect=='malformed':(run/'AutoSol/publication.json').write_text('{}')
    elif defect=='missing-result':(run/'AutoSol/report.json').unlink()
    else:
        path=run/'report.json';value=json.loads(path.read_text());value['newer_work']='preserve';path.write_text(json.dumps(value))
    before=snapshot(run)
    monkeypatch.setattr(cli,'load_config',lambda:object())
    monkeypatch.setattr(cli,'_workspace_run',lambda *a:run)
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**k:pytest.fail('Failed saved completion must not discover native tools'))
    monkeypatch.setattr(cli,'execute_autosol',lambda *a,**k:pytest.fail('Failed saved completion must not relaunch'))
    assert cli.main(['autosol',str(run)])==2
    assert snapshot(run)==before


def test_absent_receipt_probe_is_read_only_and_explicit_completion_still_refuses(tmp_path):
    from nasolve.autosol_publication import complete_autosol_publication
    from nasolve.autosol import AutoSolPreparationError
    run=tmp_path/'run';run.mkdir()
    assert complete_autosol_publication(run,if_present=True) is None
    assert list(run.iterdir())==[]
    with pytest.raises(AutoSolPreparationError):complete_autosol_publication(run)
    assert list(run.iterdir())==[]


def test_dangling_saved_receipt_is_not_treated_as_a_fresh_launch(tmp_path):
    from nasolve.autosol_publication import complete_autosol_publication
    from nasolve.autosol import AutoSolPreparationError
    run=tmp_path/'run';(run/'AutoSol').mkdir(parents=True)
    (run/'AutoSol/publication.json').symlink_to(tmp_path/'missing')
    with pytest.raises(AutoSolPreparationError,match='symbolic link'):
        complete_autosol_publication(run,if_present=True)
