"""Separate captured native states from analysis copies without growing archive capacity."""
import shutil
import pytest
from nasolve import cif_complete_request as complete
from nasolve import cif_component_runtime as trees, cif_runtime_evidence as storage
from nasolve.campaign_records import write_record
from nasolve.cif_complete_attempt_archive import pack_complete_attempt_evidence, expanded_complete_attempt_evidence
from tests.test_cif_complete_child_bounds import tree,PARTS,V3
from tests.test_cif_complete_request import case
from tests.test_cif_complete_continuation import joined

V4='cif-complete-request-partitioned-artifacts-v4'
NATIVE='repair/attempts/attempt-0001/execution/native/'


def captured(root,monkeypatch):
    intent=tree(root,monkeypatch)
    p=root/NATIVE/'baseline/evidence.bin';p.parent.mkdir(parents=True);p.write_bytes(b'x'*18000)
    return intent


def test_explicit_capture_partition_keeps_historical_defaults(tmp_path,monkeypatch):
    root=tmp_path/'attempt';captured(root,monkeypatch)
    with pytest.raises(ValueError,match='bounds'):complete._attempt_files(root,with_continuation=True,artifact_policy=V3)
    r=complete._attempt_files(root,with_continuation=True,artifact_policy=V4)
    assert len(r['files'])==7 and complete.ARTIFACT_POLICY==V3
    assert complete._artifact_partitions(V4,True)==tuple(sorted((*complete._artifact_partitions(V3,True),NATIVE),key=len,reverse=True))
    with pytest.raises(ValueError,match='bounds'):trees._tree(root)


@pytest.mark.parametrize('part',[*PARTS,NATIVE])
@pytest.mark.parametrize('excess',['bytes','files','member'])
def test_capture_and_other_partitions_cannot_borrow_capacity(tmp_path,monkeypatch,part,excess):
    root=tmp_path/'attempt';captured(root,monkeypatch);monkeypatch.setattr(trees,'MAX_FILES',8)
    if excess=='member':monkeypatch.setattr(trees,'MAX_FILE_BYTES',20000)
    for i in range(9 if excess=='files' else 1):
        (root/part/f'extra-{i}').write_bytes(b'y'*(21000 if excess=='member' else 16000 if excess=='bytes' else 1))
    with pytest.raises(ValueError,match='bounds'):complete._attempt_files(root,with_continuation=True,artifact_policy=V4)


@pytest.mark.parametrize('alias',['execution/native-extra','execution/Native','execution/native-link','other/native'])
def test_native_capture_boundary_is_exact(tmp_path,monkeypatch,alias):
    root=tmp_path/'attempt';captured(root,monkeypatch);p=root/'repair/attempts/attempt-0001'/alias
    if alias.endswith('link'):p.symlink_to(root/NATIVE,target_is_directory=True)
    elif alias=='execution/Native':
        # Exercise actual saved spelling on both case-sensitive and default macOS filesystems.
        temporary=(root/NATIVE).rename(root/'case-change')
        temporary.rename(p)
    else:p.mkdir(parents=True);(p/'extra').write_bytes(b'y'*18000)
    with pytest.raises(ValueError):complete._attempt_files(root,with_continuation=True,artifact_policy=V4)


def test_capture_archive_relocation_retains_shared_physical_limit(tmp_path,monkeypatch):
    root=tmp_path/'attempt';intent=captured(root,monkeypatch)
    r=complete._attempt_files(root,with_continuation=True,artifact_policy=V4)
    write_record(root/'finished.json',dict(attempt_sha256=intent['record_sha256'],outcome='RETURNED',stopped_verified=True,artifacts=r))
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    archive=tmp_path/'archive.zip';report=pack_complete_attempt_evidence(root,archive,artifact_policy=V4,with_continuation=True)
    shutil.rmtree(root);moved=archive.rename(tmp_path/'moved.zip')
    with expanded_complete_attempt_evidence(moved,report['archive_sha256'],finished_sha256=report['finished_sha256'],artifact_policy=V4) as view:
        assert {str(p.relative_to(view/'evidence')):p.read_bytes() for p in (view/'evidence').rglob('*') if p.is_file()}==before
        assert storage._ACTIVE_BYTES.get()==report['unique_bytes']<storage.MAX_ACTIVE_BYTES
    with pytest.raises(ValueError):
        with expanded_complete_attempt_evidence(moved,report['archive_sha256'],finished_sha256=report['finished_sha256'],artifact_policy=V3):pytest.fail('Historical boundary changed')
    monkeypatch.setattr(storage,'MAX_ACTIVE_BYTES',report['unique_bytes']-1)
    with pytest.raises(ValueError):
        with expanded_complete_attempt_evidence(moved,report['archive_sha256'],finished_sha256=report['finished_sha256'],artifact_policy=V4):pytest.fail('Physical limit grew')
    assert storage._ACTIVE_BYTES.get()==0 and not root.exists() and not archive.exists()


def test_explicit_capture_policy_reuses_complete_retirement(joined):
    from nasolve.cif_attempt_retention import retire_attempt_working_files
    m,args,root,sdk,store,generations,state=joined
    m.initialize_dictionary_request(output=root,artifact_policy=V4,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=m.read_dictionary_request_result(root,1)
    retire_attempt_working_files(root,1)
    assert m.read_dictionary_request_result(root,1)==before
    assert m.inspect_dictionary_request(root)['request']['configuration']['artifact_policy']==V4
