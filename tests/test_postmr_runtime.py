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
def test_conflicting_selected_runtime_refuses_before_postmr_work(tmp_path,defect):
    run,ready,sdk,data=setup(tmp_path);environment=dict(sdk.environment)
    if defect=='ready':
        other=tmp_path/'other';other.mkdir();ready=make_ready_set(other)
    elif defect=='environment':environment['PATH']='/different'
    elif defect=='missing_dispatcher':sdk.executables.clear()
    else:ready.unlink()
    before=(run/'report.json').read_bytes()
    with pytest.raises(PostMRPreparationError,match='selected Phenix'):
        prepare_postmr(run,ready,phenix_installation=sdk,environment=environment,data_root=data)
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
