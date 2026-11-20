from hashlib import sha256
from pathlib import Path
from nasolve.campaign_records import read_record, write_record
from nasolve.cif_complete_attempt_archive import pack_complete_attempt_evidence
import pytest

from tests.test_cif_complete_request import case
from tests.test_cif_complete_continuation import joined
from tests.test_cif_postmr_request import entry_case, frozen_entry

from nasolve import cif_complete_request as requests, cif_component_runtime as trees, cif_runtime_evidence as storage

V5 = 'cif-complete-request-staged-artifacts-v5'
EXECUTION = 'repair/attempts/attempt-0001/execution/'


def put(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture
def mixed(tmp_path, monkeypatch):
    for module in (trees, storage):
        monkeypatch.setattr(module, 'MAX_BYTES', 32768)
    monkeypatch.setattr(storage, 'MAX_ACTIVE_BYTES', 32768)
    root = tmp_path/'attempt'
    root.mkdir()
    write_record(root/'attempt.json', {'fixture': 'stopped storage control'})
    put(root, EXECUTION+'plan/input.cif', b'A'*17000)
    put(root, EXECUTION+'plane-attribution-000/captures/before/data', b'B'*17000)
    put(root, EXECUTION+'bond-attribution-000/job/partial.bin', b'C'*17000)
    (root/EXECUTION/'bond-attribution-000/partial-empty').mkdir()
    return root


def test_staged_current_attempt_retains_every_original_file_without_publication(mixed):
    with pytest.raises(ValueError, match='bounds'):
        requests._attempt_files(mixed, artifact_policy=requests.CAPTURE_ARTIFACT_POLICY)
    value = requests._attempt_files(mixed, artifact_policy=V5)
    expected = {str(p.relative_to(mixed)): {'sha256':sha256(p.read_bytes()).hexdigest(), 'size':p.stat().st_size}
                for p in mixed.rglob('*') if p.is_file()}
    assert value['files'] == expected
    assert str(Path(EXECUTION)/'bond-attribution-000/partial-empty') in value['directories']
    assert not (mixed/'finished.json').exists() and not (mixed/EXECUTION/'runtime').exists()


@pytest.mark.parametrize('bad', ['plane-attribution-016','xplane-attribution-000','plane-attribution-00','foo/plane-attribution-000'])
def test_only_declared_phase_locations_have_separate_storage(mixed, bad):
    put(mixed, EXECUTION+bad+'/data', b'Z'*17000)
    with pytest.raises(ValueError, match='bounds'):
        requests._attempt_files(mixed, artifact_policy=V5)


def test_a_stage_cannot_borrow_from_another_stage(mixed):
    put(mixed, EXECUTION+'plane-attribution-000/truncated', b'Z'*17000)
    with pytest.raises(ValueError, match='bounds'):
        requests._attempt_files(mixed, artifact_policy=V5)


def test_symlink_in_partial_phase_refuses(mixed):
    (mixed/EXECUTION/'plane-attribution-000/alias').symlink_to(mixed/'attempt.json')
    with pytest.raises(ValueError, match='[Uu]nsafe|[Ss]ymbolic'):
        requests._attempt_files(mixed, artifact_policy=V5)


def test_shared_physical_capacity_stays_bounded(mixed, monkeypatch):
    before = requests._attempt_files(mixed, artifact_policy=V5)
    intent = read_record(mixed/'attempt.json')
    write_record(mixed/'finished.json', {'attempt_sha256':intent['record_sha256'], 'outcome':'RETURNED',
                                        'stopped_verified':True, 'artifacts':before})
    monkeypatch.setattr(storage, 'MAX_ACTIVE_BYTES', 16000)
    with pytest.raises(ValueError, match='physical|shared'):
        pack_complete_attempt_evidence(mixed, mixed.parent/'proof.zip', artifact_policy=V5, with_continuation=False)


def test_stages_share_the_original_complete_raw_envelope(mixed):
    for i in range(8):
        put(mixed, EXECUTION+f'plane-attribution-{i+1:03d}/data', b'X'*17000)
    with pytest.raises(ValueError, match='bounds'):
        requests._attempt_files(mixed, artifact_policy=V5)



def test_interrupted_mixture_preserves_parts_and_restarts_in_new_owner(case, monkeypatch):
    module, options, root, sdk, store, generation, _ = case
    options['artifact_policy'] = V5
    module.initialize_dictionary_request(output=root, **options)
    original = module.repair.execute_prepared_dictionary_repair
    seen = []

    def execution(*args, **kwargs):
        result = original(*args, **kwargs)
        work = args[2]
        seen.append(work)
        for family in ('plane-attribution-000', 'bond-attribution-001'):
            for number in range(110):
                put(work, f'{family}/job/phase-{number}', b'exact partial and completed evidence')
        if len(seen) == 1:
            raise KeyboardInterrupt('between independently stopped repair and outer publication')
        return result

    monkeypatch.setattr(module.repair, 'execute_prepared_dictionary_repair', execution)
    monkeypatch.setattr(trees, 'MAX_FILES', 210)
    with pytest.raises(KeyboardInterrupt):
        module.execute_dictionary_request_attempt(root, sdk, store, generation=generation)
    first = root/'attempts/attempt-0001'
    original_seal = (first/'finished.json').read_bytes()
    row = module.inspect_dictionary_request(root)['attempts'][0]
    assert row['state'] == 'STOPPED' and row['finished']['outcome'] == 'RAISED'
    assert not (first/EXECUTION/'runtime').exists()
    failed_files = requests._attempt_files(first, artifact_policy=V5)
    with pytest.raises(ValueError, match='bounds'):
        requests._attempt_files(first, artifact_policy=requests.CAPTURE_ARTIFACT_POLICY)
    returned = module.execute_dictionary_request_attempt(root, sdk, store, generation=generation)
    assert returned['attempt_number'] == 2 and seen[0] != seen[1]
    assert module.read_dictionary_request_result(root, 2)['result'] == returned['result']
    assert (first/'finished.json').read_bytes() == original_seal
    assert requests._attempt_files(first, artifact_policy=V5) == failed_files


def test_live_continuation_still_blocks_recovery_under_staged_policy(joined):
    from nasolve.campaign_process import CampaignProcessError
    module, options, root, sdk, store, generation, state = joined
    module.initialize_dictionary_request(output=root, artifact_policy=V5, **options)
    state['fault'] = 'after-header'
    with pytest.raises(KeyboardInterrupt):
        module.execute_dictionary_request_attempt(root, sdk, store, generation=generation)
    assert module.inspect_dictionary_request(root)['availability'] == 'BLOCKED'
    with pytest.raises(CampaignProcessError):
        module.execute_dictionary_request_attempt(root, sdk, store, generation=generation)
    assert not (root/'attempts/attempt-0001/finished.json').exists()
    assert not (root/'attempts/attempt-0002').exists()

def test_fresh_multi_component_plane_and_bond_work_chooses_stage_storage(frozen_entry):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    _, options, *_ = frozen_entry
    assert len(options['components']) > 1
    request = initialize_postmr_dictionary_request(**options, automatic_plane_support=True, automatic_bond_targets=True)
    assert request['configuration']['artifact_policy'] == V5
