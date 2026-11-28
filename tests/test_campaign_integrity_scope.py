"""Stage boundaries verify their own science; full status still audits the collection."""
from collections import Counter
from unittest.mock import patch
import json
import pytest
from nasolve import campaigns, campaign_records
from nasolve.campaign_execution import execute_campaign
from tests import test_campaign_execution as harness

@pytest.fixture
def campaign():
    case = harness.CampaignExecutionTests()
    case.setUp()
    try:
        yield case
    finally:
        case.doCleanups()

def test_stage_worker_does_not_hash_another_datasets_inputs(campaign):
    case = campaign
    inside = []
    reads = []
    run = case.run_job
    identity = campaigns._file_identity

    def worker(*args, **kwargs):
        inside.append(True)
        try:
            return run(*args, **kwargs)
        finally:
            inside.pop()

    def counted(path):
        if inside:
            reads.append(path)
        return identity(path)
    with patch('nasolve.campaign_execution.run_job', side_effect=worker), patch.object(campaigns, '_file_identity', counted):
        result = execute_campaign(case.root, datasets=('A',), through='postmr')
    assert case.items(result)['A']['next_stage'] == 'autosol'
    assert any((p.is_relative_to(case.root / 'A') for p in reads))
    assert any((p.is_relative_to(case.root / 'NASolveCampaign/resources') for p in reads))
    assert not any((p.is_relative_to(case.root / 'B') for p in reads))

def test_other_completed_dataset_is_audited_at_entry_and_exit_not_each_stage(campaign):
    case = campaign
    result = execute_campaign(case.root, datasets=('B',), through='postmr')
    target = case.root / case.items(result)['B']['run'] / 'preflight.dat'
    reads = Counter()
    identity = campaign_records._file_identity

    def counted(path):
        reads[path] += 1
        return identity(path)
    with patch.object(campaign_records, '_file_identity', counted):
        result = execute_campaign(case.root, datasets=('A',), through='postmr')
    assert case.items(result)['A']['next_stage'] == 'autosol'
    assert 2 <= reads[target] <= 3

def test_changed_waiting_dataset_is_blocked_before_it_starts(campaign):
    case = campaign

    def mutate(name, stage):
        if (name, stage) == ('A', 'preflight'):
            (case.root / 'B/staraniso-alldata.mtz').write_bytes(b'changed while A ran')
    case.after_stage = mutate
    result = execute_campaign(case.root, through='postmr')
    assert case.items(result)['A']['next_stage'] == 'autosol'
    assert case.items(result)['B']['status'] == 'BLOCKED'
    assert not any((name == 'B' for name, stage in case.calls))

def test_changed_completed_dataset_is_reported_at_final_full_audit(campaign):
    case = campaign
    result = execute_campaign(case.root, datasets=('B',), through='postmr')
    target = case.root / case.items(result)['B']['run'] / 'preflight.dat'

    def mutate(name, stage):
        if (name, stage) == ('A', 'preflight'):
            target.write_bytes(b'changed completed evidence')
    case.after_stage = mutate
    result = execute_campaign(case.root, datasets=('A',), through='postmr')
    assert case.items(result)['A']['next_stage'] == 'autosol'
    assert case.items(result)['B']['status'] == 'BLOCKED'
    assert 'Stage artifact changed' in case.items(result)['B']['diagnostic']

def test_changed_shared_resource_stops_current_stage_and_waiting_datasets(campaign):
    case = campaign
    target = case.root / case.plan['preset']['source']['relative_path']

    def mutate(name, stage):
        if (name, stage) == ('A', 'preflight'):
            target.write_bytes(target.read_bytes() + b'\n# changed shared resource\n')
    case.after_stage = mutate
    result = execute_campaign(case.root, through='postmr')
    assert {r['status'] for r in case.items(result).values()} == {'BLOCKED'}
    assert case.calls == [('A', 'preflight')]

def test_selected_input_change_during_stage_cannot_be_accepted(campaign):
    case = campaign

    def mutate(name, stage):
        if (name, stage) == ('A', 'preflight'):
            (case.root / 'A/staraniso-alldata.mtz').write_bytes(b'changed selected input')
    case.after_stage = mutate
    result = execute_campaign(case.root, datasets=('A',), through='postmr')
    assert case.items(result)['A']['status'] == 'BLOCKED'
    assert case.calls == [('A', 'preflight')]

def test_selected_dependency_change_cannot_reach_next_stage(campaign):
    case = campaign

    def mutate(name, stage):
        if (name, stage) == ('A', 'phaser'):
            (case.root / 'A/AutoMR/run_001/preflight.dat').write_bytes(b'changed dependency')
    case.after_stage = mutate
    result = execute_campaign(case.root, datasets=('A',), through='postmr')
    assert case.items(result)['A']['status'] == 'BLOCKED'
    assert case.calls == [('A', 'preflight'), ('A', 'phaser')]

def test_stage_worker_still_checks_structure_of_entire_frozen_plan(campaign):
    case = campaign
    runner = case.run_job

    def corrupted_plan(job, **kwargs):
        path = case.root / 'NASolveCampaign/plan.json'
        plan = json.loads(path.read_text())
        plan['datasets'][1]['inputs']['reflections']['sha256'] = 'malformed'
        plan['fingerprint'] = campaigns._digest(campaigns._canonical({k: v for k, v in plan.items() if k != 'fingerprint'}))
        path.write_text(json.dumps(plan))
        return runner(job, **kwargs)
    with patch('nasolve.campaign_execution.run_job', side_effect=corrupted_plan):
        with pytest.raises(campaigns.CampaignError):
            execute_campaign(case.root, datasets=('A',), through='postmr')
    assert not case.calls

@pytest.mark.parametrize('dataset', [None, True, '', 'a', '../A', 'missing'])
def test_stage_scope_requires_one_exact_frozen_dataset(campaign, dataset):
    with pytest.raises(campaigns.CampaignError):
        campaigns._stage_plan(campaign.root, dataset)

def test_stage_view_is_not_returned_as_whole_campaign_status(campaign):
    case = campaign
    original = (case.root / 'NASolveCampaign/plan.json').read_bytes()
    stage = campaigns._stage_plan(case.root, 'A')
    assert [r['id'] for r in stage['datasets']] == ['A']
    assert stage['fingerprint'] == case.plan['fingerprint']
    assert stage['counts'] == case.plan['counts']
    full = campaigns.campaign_status(case.root)
    assert [r['id'] for r in full['datasets']] == ['A', 'B']
    assert (case.root / 'NASolveCampaign/plan.json').read_bytes() == original
    from nasolve.campaign_execution import _reconcile, _new_state
    with pytest.raises(campaigns.CampaignError, match='complete dataset list'):
        _reconcile(case.root, stage, _new_state(full))
