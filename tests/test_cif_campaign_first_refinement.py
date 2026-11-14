"""A checked preparation registry is not a previous refinement attempt."""
import json
from unittest.mock import patch
import pytest
from nasolve import checkpoints
from nasolve.autorefine import AutoRefineError
from nasolve.campaign_stages import execute_stage,CampaignStageError
from nasolve.config import AppConfig
from nasolve.phenix_runtime import PhenixInstallation
from nasolve.presets import load_preset
from tests.test_cif_postmr_publication import setup,snapshot
from tests.test_autorefine import make_refine,make_mtz_dump


@pytest.fixture
def prepared(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run,exact,reads=setup(tmp_path,monkeypatch)
    publish_checked_preparation(run,attempt_number=1)
    native=tmp_path/'tools';native.mkdir()
    sdk=PhenixInstallation(native,None,'2.2.1-6174',
        {'phenix.refine':make_refine(native),'phenix.mtz.dump':make_mtz_dump(native,anomalous=False)},
        {'PATH':'/usr/bin:/bin'},'fixture')
    monkeypatch.setattr('nasolve.campaign_stages.load_config',lambda:AppConfig())
    monkeypatch.setattr('nasolve.campaign_stages.discover_phenix',lambda *a,**k:sdk)
    policy=load_preset().to_dict();policy['schema_version']=2;policy['postmr']['checked_preparation']=True
    stage=tmp_path/'NASolveCampaign/jobs/autorefine';stage.mkdir(parents=True)
    return run,exact,policy,stage


def execute(root,values):
    run,_,policy,stage=values
    return execute_stage(root,{'id':'dataset','relative_path':'dataset'},policy,'autorefine',stage,run)


def test_campaign_first_refinement_accepts_checked_root_and_keeps_exact_restraints(prepared,tmp_path):
    run,exact,_,_=prepared;before=snapshot(run/'PostMR')
    with patch('nasolve.autorefine.read_registry',wraps=checkpoints.read_registry) as reader:
        result=execute(tmp_path,prepared)
    assert reader.call_count==1
    assert result['checkpoint']=='refine-001'
    assert snapshot(run/'PostMR')==before
    _,registry=checkpoints.read_registry(run)
    child=checkpoints.resolve_checkpoint(registry,'refine-001');assert child['parent']=='postmr'
    assert checkpoints.inherited_paths(child,run)['restraints']==exact['runtime']['phils']+exact['runtime']['dictionaries']
    args=json.loads((run/'AutoRefine/round_001/received_args.json').read_text())
    assert all(str(p) in args for p in exact['runtime']['phils']+exact['runtime']['dictionaries'])


@pytest.mark.parametrize('defect',['empty','unknown-file','partial-round','manual-choice','broken-registry','changed-model','symlink-registry','prior-history'])
def test_first_refinement_preserves_existing_work_or_invalid_preparation(prepared,tmp_path,monkeypatch,defect):
    run,exact,_,_=prepared;folder=run/'AutoRefine'
    if defect=='empty':
        for path in folder.iterdir():path.unlink()
    elif defect=='unknown-file':(folder/'unclassified-output.dat').write_text('preserve')
    elif defect=='partial-round':(folder/'round_001').mkdir()
    elif defect=='manual-choice':
        child=checkpoints.add_checkpoint(run,name='later manual choice',model=exact['runtime']['model'])
        checkpoints.select_checkpoint(run,child.checkpoint_id)
    elif defect=='broken-registry':(folder/'checkpoints.json').write_text('{}')
    elif defect=='changed-model':exact['runtime']['model'].write_text(exact['runtime']['model'].read_text()+'REMARK changed\n')
    elif defect=='prior-history':
        for path in folder.iterdir():path.unlink()
        folder.rmdir()
        path=run/'report.json';report=json.loads(path.read_text());report['autorefine_history']=[];path.write_text(json.dumps(report))
    else:
        registry=folder/'checkpoints.json';copy=tmp_path/'registry.json';registry.rename(copy);registry.symlink_to(copy)
    before=snapshot(run)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('No native work on existing/invalid state'))
    with pytest.raises((CampaignStageError,AutoRefineError)):
        execute(tmp_path,prepared)
    assert snapshot(run)==before



def test_new_manual_choice_between_admission_and_engine_read_is_preserved(prepared,tmp_path,monkeypatch):
    from nasolve import autorefine
    run,exact,_,_=prepared;preserved={}
    def changed(path):
        child=checkpoints.add_checkpoint(run,name='concurrent manual choice',model=exact['runtime']['model'])
        checkpoints.select_checkpoint(run,child.checkpoint_id)
        preserved.update(snapshot(run))
        return checkpoints.read_registry(path)
    monkeypatch.setattr(autorefine,'read_registry',changed,raising=False)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('No native launch after changed selection'))
    with pytest.raises(AutoRefineError,match='changed before refinement'):
        execute(tmp_path,prepared)
    assert snapshot(run)==preserved


def test_expected_registry_guard_never_initializes_a_missing_registry(tmp_path,monkeypatch):
    from nasolve.autorefine import execute_autorefine
    from tests.test_autorefine import make_refine_run
    run=make_refine_run(tmp_path,autosol=False);before=snapshot(run)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('No native launch'))
    with pytest.raises(AutoRefineError,match='changed before refinement'):
        execute_autorefine(run,tmp_path/'unused-refine',tmp_path/'unused-dump',
            phenix_version='2.2.1-6174',expected_registry_sha256='0'*64)
    assert snapshot(run)==before and not (run/'AutoRefine').exists()
