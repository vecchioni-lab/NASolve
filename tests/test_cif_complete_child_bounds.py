"""An owned repair attempt retains its own cap, including archive replay."""
import shutil

import pytest

from nasolve import cif_complete_request as complete
from nasolve import cif_component_runtime as trees, cif_runtime_evidence as storage
from nasolve.campaign_records import write_record
from nasolve.cif_complete_attempt_archive import pack_complete_attempt_evidence, expanded_complete_attempt_evidence

V2 = 'cif-complete-request-partitioned-artifacts-v2'
V3 = 'cif-complete-request-partitioned-artifacts-v3'
CHILD = 'repair/attempts/attempt-0001/'
PARTS = ('', CHILD, CHILD+'execution/runtime/', 'continuation/', 'continuation/runtime/')


def tree(root, monkeypatch):
    for module in (trees,storage): monkeypatch.setattr(module,'MAX_BYTES',32768)
    monkeypatch.setattr(storage,'MAX_ACTIVE_BYTES',32768)
    root.mkdir()
    intent=write_record(root/'attempt.json',{'fixture':'bounded ownership, no science'})
    for folder in PARTS:
        p=root/folder/'evidence.bin';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'x'*18000)
    return intent


def test_owned_repair_partition_does_not_borrow_parent_or_runtime_allowance(tmp_path,monkeypatch):
    root=tmp_path/'attempt';tree(root,monkeypatch)
    with pytest.raises(ValueError,match='bounds'):
        complete._attempt_files(root,with_continuation=True,artifact_policy=V2)
    value=complete._attempt_files(root,with_continuation=True,artifact_policy=V3)
    assert len(value['files'])==6
    assert complete.ARTIFACT_POLICY==V3
    # Public/individual tree contracts stay bounded, not quietly upgraded.
    with pytest.raises(ValueError,match='bounds'):trees._tree(root)


@pytest.mark.parametrize('part',PARTS)
@pytest.mark.parametrize('excess',['bytes','files','member'])
def test_each_owned_partition_keeps_all_original_limits(tmp_path,monkeypatch,part,excess):
    root=tmp_path/'attempt';tree(root,monkeypatch)
    monkeypatch.setattr(trees,'MAX_FILES',8)
    if excess=='member':monkeypatch.setattr(trees,'MAX_FILE_BYTES',20000)
    count=9 if excess=='files' else 1
    for i in range(count):(root/part/f'extra-{i}').write_bytes(b'y'*(21000 if excess=='member' else 16000 if excess=='bytes' else 1))
    with pytest.raises(ValueError,match='bounds'):
        complete._attempt_files(root,with_continuation=True,artifact_policy=V3)


@pytest.mark.parametrize('alias',['repair/attempts/attempt-0001-extra','repair/attempts/attempt-0002','repair/attempts/attempt-0001-link'])
def test_repair_partition_requires_exact_owned_directory_boundary(tmp_path,monkeypatch,alias):
    root=tmp_path/'attempt';tree(root,monkeypatch);p=root/alias
    if alias.endswith('-link'):p.symlink_to(root/CHILD,target_is_directory=True)
    else:p.mkdir();(p/'extra').write_bytes(b'y'*18000)
    with pytest.raises(ValueError):complete._attempt_files(root,with_continuation=True,artifact_policy=V3)


def test_archive_deduplicates_all_partitions_under_unchanged_physical_bound_and_relocates(tmp_path,monkeypatch):
    root=tmp_path/'attempt';intent=tree(root,monkeypatch)
    files=complete._attempt_files(root,with_continuation=True,artifact_policy=V3)
    write_record(root/'finished.json',dict(attempt_sha256=intent['record_sha256'],outcome='RETURNED',stopped_verified=True,artifacts=files))
    expected={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    archive=tmp_path/'evidence.zip';report=pack_complete_attempt_evidence(root,archive,artifact_policy=V3,with_continuation=True)
    assert report['logical_bytes']>storage.MAX_BYTES and report['unique_bytes']<storage.MAX_ACTIVE_BYTES
    shutil.rmtree(root);moved=tmp_path/'relocated.zip';archive.rename(moved)
    with expanded_complete_attempt_evidence(moved,report['archive_sha256'],finished_sha256=report['finished_sha256']) as view:
        assert {str(p.relative_to(view/'evidence')):p.read_bytes() for p in (view/'evidence').rglob('*') if p.is_file()}==expected
    assert not view.exists() and not root.exists() and not archive.exists()
    with pytest.raises(ValueError,match='partition policy'):
        with expanded_complete_attempt_evidence(moved,report['archive_sha256'],
                finished_sha256=report['finished_sha256'],artifact_policy=V2):pytest.fail('Different frozen policy')
    monkeypatch.setattr(storage,'MAX_ACTIVE_BYTES',report['unique_bytes']-1)
    with pytest.raises(ValueError):
        with expanded_complete_attempt_evidence(moved,report['archive_sha256'],finished_sha256=report['finished_sha256']):pytest.fail('Physical bound was widened')


def test_existing_v2_archive_and_retention_remain_readable(joined):
    from nasolve.cif_attempt_retention import prepare_attempt_archive,kept_path
    m,args,root,sdk,store,generations,state=joined
    m.initialize_dictionary_request(output=root,artifact_policy=V2,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=m.read_dictionary_request_result(root,1);prepare_attempt_archive(root,1)
    attempt=root/'attempts/attempt-0001'
    for p in attempt.rglob('*'):
        if p.is_file() and not kept_path(str(p.relative_to(attempt))):p.unlink()
    assert m.read_dictionary_request_result(root,1)==before
    assert m.inspect_dictionary_request(root)['request']['configuration']['artifact_policy']==V2

from tests.test_cif_complete_request import case
from tests.test_cif_complete_continuation import joined
