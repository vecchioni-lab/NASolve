"""Existing source-preserving adapters reach ordinary/frozen callers unchanged."""
from unittest.mock import patch
import pytest
from nasolve.postmr import prepare_postmr,PostMRPreparationError
from tests.test_postmr_runtime import checked_case

POLICY='source-preserving-v1'
OPTIONS={'source_input_policy':'cif-source-reader-preparation-v1',
         'bond_representation_policy':'cif-source-declared-neutral-purine-aromatic-v1'}


def test_ordinary_postmr_freezes_existing_source_recipe_in_one_owner(tmp_path,monkeypatch):
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch)
    result=prepare_postmr(run,ready,phenix_installation=sdk,checked_preparation=True,
                          dictionary_input_policy=POLICY)
    assert result.status=='POSTMR_READY' and calls[0][1]['generation_options']==OPTIONS
    assert [name for name,_ in calls]==['construct','execute'] and reads==[1]


@pytest.mark.parametrize('policy,checked',[(POLICY,False),('unknown',True),(True,True),({},True)])
def test_invalid_input_policy_refuses_before_construction(tmp_path,monkeypatch,policy,checked):
    monkeypatch.setattr('nasolve.postmr._prepare_postmr',lambda *a,**k:pytest.fail('No construction'))
    with pytest.raises(PostMRPreparationError,match='dictionary_input_policy'):
        prepare_postmr(tmp_path,tmp_path/'unused',checked_preparation=checked,dictionary_input_policy=policy)
    assert list(tmp_path.iterdir())==[]


def test_postmr_cli_forwards_recipe_without_low_level_generation_arguments(tmp_path,monkeypatch,capsys):
    from nasolve.cli import main
    from nasolve.config import AppConfig
    from nasolve.coot_runtime import CootDiscoveryError
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch)
    with patch('nasolve.cli.load_config',return_value=AppConfig()),patch('nasolve.cli.save_config'),patch('nasolve.cli.discover_phenix',return_value=sdk),patch('nasolve.cli.remember_phenix'),patch('nasolve.cli.discover_coot',side_effect=CootDiscoveryError('absent')):
        assert main(['postmr',str(run),'--checked-preparation','--dictionary-input-policy',POLICY])==0
    assert calls[0][1]['generation_options']==OPTIONS and reads==[1]
    assert 'POSTMR_READY' in capsys.readouterr().out


def test_input_recipe_requires_checked_cli_before_discovery():
    from nasolve.cli import main
    with patch('nasolve.cli.load_config',side_effect=AssertionError('No config/discovery')):
        assert main(['postmr','--dictionary-input-policy',POLICY])==2


def test_campaign_stage_reaches_the_same_recipe_and_publisher(tmp_path,monkeypatch):
    from nasolve.campaign_stages import execute_stage
    from nasolve.config import AppConfig
    from nasolve.coot_runtime import CootDiscoveryError
    from nasolve.presets import load_preset
    run,ready,sdk,exact,calls,reads=checked_case(tmp_path,monkeypatch)
    policy=load_preset().to_dict();policy['schema_version']=2
    policy['postmr'].update(checked_preparation=True,dictionary_input_policy=POLICY)
    job=tmp_path/'NASolveCampaign/jobs/postmr';job.mkdir(parents=True)
    with patch('nasolve.campaign_stages.load_config',return_value=AppConfig()),patch('nasolve.campaign_stages.discover_phenix',return_value=sdk),patch('nasolve.campaign_stages.discover_coot',side_effect=CootDiscoveryError('absent')):
        result=execute_stage(tmp_path,{'id':'dataset','relative_path':'dataset'},policy,'postmr',job,run)
    assert calls[0][1]['generation_options']==OPTIONS and reads==[1]
    assert result['preparation_mode']=='checked' and result['readyset_status']=='FAILED'


@pytest.mark.parametrize('schema,checked,value',[(1,'true',repr(POLICY)),(2,'false',repr(POLICY)),(2,'true','true'),(2,'true','1'),(2,'true','"unknown"')])
def test_bad_frozen_recipe_rejects(tmp_path,schema,checked,value):
    from nasolve.presets import load_preset,PresetError
    p=tmp_path/'recipe.toml';p.write_text(f'schema_version = {schema}\nid = "fixture"\nversion = "1"\n[postmr]\nchecked_preparation = {checked}\ndictionary_input_policy = {value}\n')
    with pytest.raises(PresetError):load_preset(p)


def test_recipe_is_frozen_and_relocated_without_source_or_default_migration():
    from tests.test_campaigns import CampaignTests
    from nasolve.campaigns import campaign_status
    case=CampaignTests();case.setUp()
    try:
        case.dataset('sample');case.write_preset(extra='[postmr]\nchecked_preparation = true\ndictionary_input_policy = "'+POLICY+'"\n')
        case.preset.write_text(case.preset.read_text().replace('schema_version = 1','schema_version = 2'))
        plan=case.plan();expected=plan['preset']['policy']['postmr'];assert expected['dictionary_input_policy']==POLICY
        frozen=case.state_path().read_bytes();old=case.root;case.root=case.base/'relocated';old.rename(case.root);case.preset.unlink()
        assert not old.exists()
        with patch('subprocess.Popen',side_effect=AssertionError('No native lookup')):status=campaign_status(case.root)
        assert status['integrity']=='OK' and status['preset']['policy']['postmr']==expected
        assert case.state_path().read_bytes()==frozen
        from nasolve.presets import load_preset
        assert 'dictionary_input_policy' not in load_preset().to_dict()['postmr']
    finally:case.doCleanups()


def test_prepare_run_and_resume_keep_one_frozen_recipe(tmp_path,capsys):
    from nasolve.cli import main
    from nasolve.coot_runtime import CootDiscoveryError
    from tests.test_cif_ordinary_cli import outcome
    with patch('nasolve.cli.load_config',return_value=object()),patch('nasolve.cli.discover_phenix',return_value='selected'),patch('nasolve.cli.discover_coot',side_effect=CootDiscoveryError('absent')),patch('nasolve.cif_ordinary_postmr.prepare_checked_postmr',return_value=outcome(tmp_path)) as prepare:
        assert main(['cif-doctor','prepare-run',str(tmp_path),'--dictionary-input-policy',POLICY])==0
    assert prepare.call_args.kwargs['generation_options']==OPTIONS
    with pytest.raises(SystemExit):
        main(['cif-doctor','continue-preparation',str(tmp_path),'--after-attempt','1','--dictionary-input-policy',POLICY])
