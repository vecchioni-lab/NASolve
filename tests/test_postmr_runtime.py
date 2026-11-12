"""Ordinary PostMR must retain the already selected installation contract."""
from pathlib import Path
from unittest.mock import patch
import io,json
import pytest
from nasolve.phenix_runtime import PhenixInstallation
from nasolve.postmr import prepare_postmr,PostMRPreparationError
from tests.helpers import make_postmr_report,make_ready_set
from tests.test_postmr import make_data_root,postmr_model_text


def setup(tmp_path):
    source=tmp_path/'source.pdb';source.write_text(postmr_model_text());run=tmp_path/'run';report=make_postmr_report(run,source)
    value=json.loads(report.read_text());value['frame']=None;value['post_mr_plan']={'sequences':{},'standard_pair':None,'mutations':{}};report.write_text(json.dumps(value))
    ready=make_ready_set(tmp_path);sdk=PhenixInstallation(tmp_path,None,'TEST',{'phenix.ready_set':ready},{'PATH':'/usr/bin:/bin'},'explicit')
    return run,ready,sdk,make_data_root(tmp_path)


@pytest.mark.parametrize('explicit_environment',[False,True])
def test_existing_installation_reaches_cache_without_rediscovery(tmp_path,monkeypatch,explicit_environment):
    from nasolve import cif_postmr_cache as cache
    run,ready,sdk,data=setup(tmp_path);original=cache.prepare_postmr_dictionaries;seen=[]
    def prepare(*args,**kwargs):
        seen.append(kwargs);assert kwargs['installation'] is sdk
        return original(*args,**kwargs)
    monkeypatch.setattr(cache,'prepare_postmr_dictionaries',prepare)
    with patch('nasolve.phenix_runtime.installation_from_candidate',side_effect=AssertionError('Do not rediscover selected SDK')):
        result=prepare_postmr(run,ready,phenix_installation=sdk,data_root=data,**({'environment':dict(sdk.environment)} if explicit_environment else {}))
    assert result.model_path.is_file() and len(seen)==1
    assert seen[0]['environment']==sdk.environment and seen[0]['environment'] is not sdk.environment
    assert sdk.environment=={'PATH':'/usr/bin:/bin'}


@pytest.mark.parametrize('defect',['ready','environment','missing_dispatcher','missing_file'])
@pytest.mark.parametrize('checked',[False,True])
def test_conflicting_selected_runtime_refuses_before_postmr_work(tmp_path,defect,checked):
    run,ready,sdk,data=setup(tmp_path);environment=dict(sdk.environment)
    if defect=='ready':
        other=tmp_path/'other';other.mkdir();ready=make_ready_set(other)
    elif defect=='environment':environment['PATH']='/different'
    elif defect=='missing_dispatcher':sdk.executables.clear()
    else:ready.unlink()
    before=(run/'report.json').read_bytes()
    with pytest.raises(PostMRPreparationError,match='selected Phenix'):
        prepare_postmr(run,ready,phenix_installation=sdk,environment=environment,data_root=data,**({'checked_preparation':True} if checked else {}))
    assert not (run/'PostMR').exists() and (run/'report.json').read_bytes()==before


def test_direct_path_callers_keep_legacy_optional_installation(tmp_path,monkeypatch):
    from nasolve import cif_postmr_cache as cache
    run,ready,sdk,data=setup(tmp_path);original=cache.prepare_postmr_dictionaries;seen=[]
    def prepare(*args,**kwargs):
        seen.append(kwargs);assert kwargs.get('installation') is None;return original(*args,**kwargs)
    monkeypatch.setattr(cache,'prepare_postmr_dictionaries',prepare)
    assert prepare_postmr(run,ready,data_root=data).readyset_log.is_file()
    assert len(seen)==1


def test_cli_passes_the_selected_installation_without_another_discovery(tmp_path):
    from nasolve.cli import main
    from nasolve.config import AppConfig
    from types import SimpleNamespace
    from contextlib import redirect_stdout
    from nasolve.coot_runtime import CootDiscoveryError
    run,ready,sdk,data=setup(tmp_path)
    result=SimpleNamespace(status='POSTMR_READY',message='fixture',run_directory=run,model_path=run/'model.pdb',readyset_log=run/'ready.log',restraint_paths=[],report_path=run/'report.json',exit_code=0)
    with patch('nasolve.cli.load_config',return_value=AppConfig()),patch('nasolve.cli.save_config'),patch('nasolve.cli.discover_phenix',return_value=sdk) as discover,patch('nasolve.cli.remember_phenix'),patch('nasolve.cli.discover_coot',side_effect=CootDiscoveryError('absent')),patch('nasolve.cli.prepare_postmr',return_value=result) as prepare,redirect_stdout(io.StringIO()):
        assert main(['postmr',str(run)])==0
    assert discover.call_count==1 and prepare.call_args.kwargs['phenix_installation'] is sdk


def checked_case(tmp_path,monkeypatch,selected='verified_parent_runtime'):
    from tests.test_cif_postmr_publication import setup as published_setup
    import nasolve.cif_ordinary_postmr as ordinary
    run,exact,reads=published_setup(tmp_path,monkeypatch,selected)
    ready=tmp_path/'ready_set';ready.write_text('not executed')
    sdk=PhenixInstallation(tmp_path,None,'TEST',{'phenix.ready_set':ready},{'PATH':'/usr/bin:/bin'},'explicit')
    request=run/'PostMR/DictionaryEngine/request';calls=[]
    def initialize(path,installation,**options):
        assert path==run and installation is sdk
        assert options['continuation_options']['restore_serialization'] is True
        calls.append(('construct',options))
        return ordinary.PreparedPostMRRequest(run,request,{}, {'DA':{'frozen':True}})
    def execute(root,installation,store,**options):
        assert root==request and installation is sdk and options['after_attempt']==0
        calls.append(('execute',options));return {'attempt_number':1}
    monkeypatch.setattr(ordinary,'initialize_ordinary_postmr_request',initialize)
    monkeypatch.setattr('nasolve.cif_complete_request.execute_dictionary_request_attempt',execute)
    return run,ready,sdk,exact,calls,reads


@pytest.mark.parametrize('choice',['verified_parent_runtime','readyset_checked_model'])
def test_ordinary_checked_preparation_publishes_once_and_reports_actual_outcome(tmp_path,monkeypatch,choice):
    from nasolve.checkpoints import read_registry,inherited_paths
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch,choice)
    with patch('nasolve.postmr._prepare_postmr',side_effect=AssertionError('No legacy second preparation')):
        result=prepare_postmr(run,ready,phenix_installation=sdk,checked_preparation=True,restraint_scope='all')
    assert [name for name,_ in calls]==['construct','execute'] and reads==[1]
    assert calls[0][1]['restraint_scope']=='all'
    assert result.status=='POSTMR_READY' and result.readyset_log is None
    assert result.readyset_status==('FAILED' if choice=='verified_parent_runtime' else 'COMPLETED')
    assert result.model_path==exact['runtime']['model']
    assert list(result.restraint_paths)==exact['runtime']['phils']+exact['runtime']['dictionaries']
    assert result.report_path==run/'PostMR/report.json'
    _,registry=read_registry(run);assert registry['checkpoints'][0]['status']=='REVIEW'
    assert inherited_paths(registry['checkpoints'][0],run)['restraints']==list(result.restraint_paths)


def test_unqualified_checked_preparation_preserves_work_without_legacy_retry(tmp_path,monkeypatch):
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch);exact['runtime']=None
    before=(run/'report.json').read_bytes()
    with patch('nasolve.postmr._prepare_postmr',side_effect=AssertionError('No unchecked fallback')):
        with pytest.raises(PostMRPreparationError,match='no independently checked'):
            prepare_postmr(run,ready,phenix_installation=sdk,checked_preparation=True)
    assert (run/'report.json').read_bytes()==before and not (run/'PostMR/report.json').exists()
    assert (run/'PostMR/DictionaryEngine/request/attempts/attempt-0001/result.json').is_file()
    assert len(calls)==2 and reads==[1]


def test_checked_option_requires_selected_installation_before_work(tmp_path):
    run,ready,sdk,data=setup(tmp_path)
    with pytest.raises(PostMRPreparationError,match='selected Phenix'):
        prepare_postmr(run,ready,checked_preparation=True)
    assert not (run/'PostMR').exists()


def test_ordinary_checked_cli_exposes_fallback_report_without_fictional_log(tmp_path,monkeypatch,capsys):
    from nasolve.cli import main
    from nasolve.config import AppConfig
    from nasolve.coot_runtime import CootDiscoveryError
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch)
    with patch('nasolve.cli.load_config',return_value=AppConfig()),patch('nasolve.cli.save_config'),patch('nasolve.cli.discover_phenix',return_value=sdk),patch('nasolve.cli.remember_phenix'),patch('nasolve.cli.discover_coot',side_effect=CootDiscoveryError('absent')):
        assert main(['postmr',str(run),'--checked-preparation'])==0
    output=capsys.readouterr().out
    assert 'retained' in output and 'ReadySet: FAILED' in output
    assert 'ReadySet log:' not in output and 'None' not in output
    assert str(run/'PostMR/report.json') in output and len(calls)==2 and reads==[1]


def test_interrupted_ordinary_handoff_finishes_without_repeating_construction(tmp_path,monkeypatch):
    import nasolve.cif_postmr_publication as publication
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch)
    with patch.object(publication,'_publish_run_report',side_effect=OSError('interrupted save')):
        with pytest.raises(PostMRPreparationError,match='interrupted save'):
            prepare_postmr(run,ready,phenix_installation=sdk,checked_preparation=True)
    receipt=run/'PostMR/report.json';saved=(receipt.read_bytes(),receipt.stat().st_mtime_ns)
    with patch('nasolve.cif_ordinary_postmr.initialize_ordinary_postmr_request',side_effect=AssertionError('Never reconstruct')):
        publication.publish_checked_preparation(run,attempt_number=1)
    assert (receipt.read_bytes(),receipt.stat().st_mtime_ns)==saved
    assert [name for name,_ in calls]==['construct','execute']
    assert json.loads((run/'report.json').read_text())['status']=='POSTMR_READY'


def test_checked_cli_failure_preserves_evidence_and_points_to_existing_recovery(tmp_path,monkeypatch,capsys):
    from nasolve.cli import main
    from nasolve.config import AppConfig
    from nasolve.coot_runtime import CootDiscoveryError
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch);exact['runtime']=None
    with patch('nasolve.cli.load_config',return_value=AppConfig()),patch('nasolve.cli.save_config'),patch('nasolve.cli.discover_phenix',return_value=sdk),patch('nasolve.cli.remember_phenix'),patch('nasolve.cli.discover_coot',side_effect=CootDiscoveryError('absent')):
        assert main(['postmr',str(run),'--checked-preparation'])==2
    output=capsys.readouterr()
    assert 'preparation-status' in output.err and 'Preserve partial work' in output.err
    assert not output.out and not (run/'PostMR/report.json').exists() and len(calls)==2


def test_checked_constructor_never_rebuilds_an_existing_partial_postmr(tmp_path):
    from types import SimpleNamespace
    run,ready,sdk,data=setup(tmp_path)
    partial=run/'PostMR';partial.mkdir();evidence=partial/'partial.txt';evidence.write_text('retain this work')
    before=(evidence.read_bytes(),evidence.stat().st_mtime_ns)
    with patch('nasolve.cif_ordinary_postmr.configure_dictionary_engine',return_value=SimpleNamespace(ready_set_executable=ready)),patch('subprocess.run',side_effect=AssertionError('No second native preparation')):
        with pytest.raises(PostMRPreparationError,match='already exists'):
            prepare_postmr(run,ready,phenix_installation=sdk,data_root=data,checked_preparation=True)
    assert (evidence.read_bytes(),evidence.stat().st_mtime_ns)==before
