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

def test_oversize_original_reads_each_member_after_relocation(mixed, tmp_path):
    import shutil
    from nasolve.cif_complete_attempt_archive import expanded_complete_attempt_evidence, read_complete_attempt_member

    original = requests._attempt_files(mixed, artifact_policy=V5)
    intent = read_record(mixed/'attempt.json')
    write_record(mixed/'finished.json', dict(attempt_sha256=intent['record_sha256'], outcome='RETURNED',
                                             stopped_verified=True, artifacts=original))
    expected = {p.relative_to(mixed).as_posix():p.read_bytes() for p in mixed.rglob('*') if p.is_file()}
    archive = tmp_path/'working.zip'
    report = pack_complete_attempt_evidence(mixed, archive, artifact_policy=V5, with_continuation=False)
    assert report['unique_bytes'] > storage.MAX_ACTIVE_BYTES
    assert report['working_unique_bytes'] < storage.MAX_ACTIVE_BYTES
    assert report['encoded_only_files'] == 2
    shutil.rmtree(mixed)
    moved = archive.rename(tmp_path/'relocated.zip')
    with expanded_complete_attempt_evidence(moved, report['archive_sha256'], finished_sha256=report['finished_sha256'],
                                           artifact_policy=V5) as directory:
        view = directory/'evidence'
        assert requests._attempt_files(view, artifact_policy=V5) == original
        assert {name:read_complete_attempt_member(view, name) for name in expected} == expected
        assert not (view/EXECUTION/'plane-attribution-000/captures/before/data').exists()
        assert storage._ACTIVE_BYTES.get() == report['working_unique_bytes']
        with pytest.raises(ValueError):
            read_complete_attempt_member(view, '../input')
        with pytest.raises(ValueError):
            read_complete_attempt_member(view, 'unrecorded')
    assert not directory.exists() and storage._ACTIVE_BYTES.get() == 0


def test_incompressible_stages_cannot_raise_the_shared_capacity(mixed, tmp_path):
    import random
    first = mixed/EXECUTION/'plane-attribution-000/captures/before/data'
    second = mixed/EXECUTION/'bond-attribution-000/job/partial.bin'
    first.write_bytes(random.Random(17).randbytes(17000))
    second.write_bytes(random.Random(91).randbytes(17000))
    original = requests._attempt_files(mixed, artifact_policy=V5)
    intent = read_record(mixed/'attempt.json')
    write_record(mixed/'finished.json', dict(attempt_sha256=intent['record_sha256'], outcome='RETURNED',
                                             stopped_verified=True, artifacts=original))
    out = tmp_path/'too-large.zip'
    with pytest.raises(ValueError, match='physical|shared'):
        pack_complete_attempt_evidence(mixed, out, artifact_policy=V5, with_continuation=False)
    assert not out.exists() and second.exists()


def test_archive_index_at_original_directory_limit(mixed, tmp_path, monkeypatch):
    for module in (trees, storage):
        monkeypatch.setattr(module, 'MAX_FILES', 3)
    prefixes = requests._artifact_partitions(V5, False)
    limit = 4 * (1 + len(prefixes)) * trees.MAX_FILES
    existing = sum(path.is_dir() for path in mixed.rglob('*'))
    for number in range(limit - existing):
        (mixed / f'empty-{number}').mkdir()
    original = requests._attempt_files(mixed, artifact_policy=V5)
    intent = read_record(mixed / 'attempt.json')
    write_record(mixed / 'finished.json', dict(attempt_sha256=intent['record_sha256'], outcome='RETURNED',
                                                stopped_verified=True, artifacts=original))
    packed = pack_complete_attempt_evidence(mixed, tmp_path / 'at-limit.zip', artifact_policy=V5, with_continuation=False)
    assert packed['encoded_only_files'] == 2
    (mixed / 'one-extra-real-directory').mkdir()
    with pytest.raises(ValueError, match='directory count'):
        requests._attempt_files(mixed, artifact_policy=V5)


def test_public_owner_reads_retired_mixture_after_relocation(joined, monkeypatch, tmp_path):
    from nasolve.cif_attempt_retention import retire_attempt_working_files
    from nasolve import cif_complete_stages as stages

    module, options, root, sdk, store, generation, state = joined
    module.initialize_dictionary_request(output=root, artifact_policy=V5, **options)
    original = module.repair.execute_prepared_dictionary_repair

    def add_work(*args, **kwargs):
        result = original(*args, **kwargs)
        put(args[2], 'plane-attribution-000/job/details', b'P'*140000)
        put(args[2], 'bond-attribution-000/job/details', b'B'*140000)
        return result

    monkeypatch.setattr(module.repair, 'execute_prepared_dictionary_repair', add_work)
    module.execute_dictionary_request_attempt(root, sdk, store, generation=generation)
    exact = module.read_dictionary_request_result(root, 1)
    attempt = root/'attempts/attempt-0001'
    before = read_record(attempt/'finished.json')['artifacts']['files']
    core = {ref['sha256']:ref['size'] for name,ref in before.items() if stages.stage_root(name) is None}
    # Leave room for the authenticated completion record and compressed objects.
    limit = sum(core.values()) + (attempt/'finished.json').stat().st_size + 4096
    assert limit < sum({ref['sha256']:ref['size'] for ref in before.values()}.values())
    monkeypatch.setattr(storage, 'MAX_ACTIVE_BYTES', limit)
    retire_attempt_working_files(root, 1)
    assert not (attempt/EXECUTION/'plane-attribution-000/job/details').exists()
    assert module.read_dictionary_request_result(root, 1) == exact
    moved = root.rename(tmp_path/'relocated-staged-request')
    result = module.read_dictionary_request_result(moved, 1)
    assert result['runtime']['model'].is_relative_to(moved)
    assert result['runtime']['model'].read_bytes() == Path(options['model']).read_bytes()
    assert result['result'] == exact['result'] and not root.exists()
    assert len(state['calls']) == 1


@pytest.mark.parametrize('change', ['trailing compressed bytes', 'too much output', 'wrong bytes', 'hide original', 'extra object'])
def test_changed_staged_object_refuses_even_with_new_outer_digest(mixed, tmp_path, change):
    import zlib
    from nasolve import cif_complete_attempt_archive as transport, cif_complete_staged_archive as packed
    raw = requests._attempt_files(mixed, artifact_policy=V5)
    intent = read_record(mixed/'attempt.json')
    write_record(mixed/'finished.json', dict(attempt_sha256=intent['record_sha256'], outcome='RETURNED', stopped_verified=True, artifacts=raw))
    output = tmp_path/'working.zip'
    saved = pack_complete_attempt_evidence(mixed, output, artifact_policy=V5, with_continuation=False)
    index, objects, _ = transport._decode(output.read_bytes(), saved['archive_sha256'])
    member = next(n for n in index['files'] if n.startswith(packed.PACKED+'/') and n.endswith('.deflate'))
    ref = index['files'][member]
    data = objects.pop(ref['sha256'])
    if change == 'hide original':
        index['files'].pop(member)
    elif change == 'extra object':
        index['files'][member+'.extra'] = ref
        objects[ref['sha256']] = data
    else:
        changed = {'trailing compressed bytes':data+b'X', 'too much output':zlib.compress(b'X'*27000),
                   'wrong bytes':zlib.compress(b'Q'*17000)}[change]
        h = sha256(changed).hexdigest()
        objects[h] = changed
        index['files'][member] = {'size':len(changed), 'sha256':h}
    forged, digest = storage._archive_bytes(index, objects)
    with pytest.raises(ValueError):
        transport._decode(forged, digest)


def test_same_original_shared_between_core_and_stages_is_recoverable(mixed, tmp_path):
    from nasolve.cif_complete_attempt_archive import expanded_complete_attempt_evidence, read_complete_attempt_member
    put(mixed, EXECUTION+'plane-attribution-001/captures/input', b'A'*17000)
    original = requests._attempt_files(mixed, artifact_policy=V5)
    intent = read_record(mixed/'attempt.json')
    write_record(mixed/'finished.json', dict(attempt_sha256=intent['record_sha256'], outcome='RETURNED', stopped_verified=True, artifacts=original))
    output = tmp_path/'shared.zip'
    receipt = pack_complete_attempt_evidence(mixed, output, artifact_policy=V5, with_continuation=False)
    with expanded_complete_attempt_evidence(output, receipt['archive_sha256'], finished_sha256=receipt['finished_sha256']) as view:
        path = EXECUTION+'plane-attribution-001/captures/input'
        assert read_complete_attempt_member(view/'evidence', path) == (view/'evidence'/EXECUTION/'plan/input.cif').read_bytes()
        target = view/'evidence'/EXECUTION/'plan/input.cif'
        target.chmod(0o600)
        target.write_bytes(b'Z'*17000)
        with pytest.raises(ValueError, match='differs|changed'):
            requests._attempt_files(view/'evidence', artifact_policy=V5)
