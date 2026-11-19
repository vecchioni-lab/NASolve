"""Archive the existing owner's partitions without weakening inventory or bounds."""
from hashlib import sha256

import pytest
from nasolve import cif_runtime_evidence as storage, cif_component_runtime as trees
from nasolve.campaign_records import read_record, write_record
from nasolve.cif_complete_request import _attempt_files, ARTIFACT_POLICY
from tests.test_cif_runtime_evidence import rewrite


@pytest.fixture
def attempt(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'MAX_BYTES',32768)
    monkeypatch.setattr(storage,'MAX_ACTIVE_BYTES',32768)
    monkeypatch.setattr(trees,'MAX_BYTES',32768)
    root=tmp_path/'attempt-0001';root.mkdir()
    intent=write_record(root/'attempt.json',{'fixture':'storage, not process authority'})
    write_record(root/'result.json',{'fixture':'no scientific claim'})
    for name in ('working.bin','repair/attempts/attempt-0001/execution/runtime/model.bin',
                 'continuation/working.bin','continuation/runtime/model.bin'):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'x'*18000)
    inventory=_attempt_files(root,with_continuation=True,artifact_policy=ARTIFACT_POLICY)
    write_record(root/'finished.json',dict(attempt_sha256=intent['record_sha256'],outcome='RETURNED',
        stopped_verified=True,artifacts=inventory))
    return root


def pack(attempt,out):
    from nasolve.cif_complete_attempt_archive import pack_complete_attempt_evidence
    return pack_complete_attempt_evidence(attempt,out,with_continuation=True,artifact_policy=ARTIFACT_POLICY)


def test_partitioned_attempt_reconstructs_exactly_beyond_single_logical_bound(attempt,tmp_path):
    from nasolve.cif_complete_attempt_archive import expanded_complete_attempt_evidence
    before={p.relative_to(attempt).as_posix():p.read_bytes() for p in attempt.rglob('*') if p.is_file()}
    out=tmp_path/'attempt.zip';report=pack(attempt,out)
    assert report['logical_bytes']>storage.MAX_BYTES and report['unique_bytes']<storage.MAX_ACTIVE_BYTES
    second=tmp_path/'again.zip';assert pack(attempt,second)==report and out.read_bytes()==second.read_bytes()
    with expanded_complete_attempt_evidence(out,report['archive_sha256'],finished_sha256=report['finished_sha256']) as view:
        assert {p.relative_to(view/'evidence').as_posix():p.read_bytes() for p in (view/'evidence').rglob('*') if p.is_file()}==before
        assert storage._ACTIVE_BYTES.get()==report['unique_bytes'] and storage._ACTIVE_DEPTH.get()==0
        with pytest.raises(ValueError,match='root'):
            with expanded_complete_attempt_evidence(out,report['archive_sha256'],finished_sha256=report['finished_sha256']):pytest.fail('Nested outer view')
    assert not view.exists()
    assert {p.relative_to(attempt).as_posix():p.read_bytes() for p in attempt.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('defect',['policy','finished','partition','oversized_partition'])
def test_rehashed_working_index_cannot_change_owner_or_partition_bounds(attempt,tmp_path,defect):
    from nasolve.cif_complete_attempt_archive import expanded_complete_attempt_evidence
    out=tmp_path/'attempt.zip';report=pack(attempt,out)
    def change(index,members):
        if defect=='policy':index['artifact_policy']='unknown'
        elif defect=='finished':index['finished_sha256']='0'*64
        elif defect=='partition':index['with_continuation']=False
        else:index['files']['extra.bin']=dict(index['files']['working.bin'])
    rewrite(out,change)
    with pytest.raises(ValueError):
        with expanded_complete_attempt_evidence(out,sha256(out.read_bytes()).hexdigest(),finished_sha256=report['finished_sha256']):pytest.fail('Changed archived owner/bounds')
    assert storage._ACTIVE_BYTES.get()==0


def test_changed_source_inventory_prevents_archive_publication(attempt,tmp_path):
    (attempt/'working.bin').write_bytes(b'changed')
    out=tmp_path/'bad.zip'
    with pytest.raises(ValueError,match='inventory|artifacts'):pack(attempt,out)
    assert not out.exists()


def test_wrong_external_finished_binding_and_old_reader_refuse(attempt,tmp_path):
    from nasolve.cif_complete_attempt_archive import expanded_complete_attempt_evidence
    out=tmp_path/'attempt.zip';report=pack(attempt,out)
    with pytest.raises(ValueError,match='finished|owner'):
        with expanded_complete_attempt_evidence(out,report['archive_sha256'],finished_sha256='0'*64):pytest.fail('Wrong owner')
    with pytest.raises(ValueError,match='Unsupported'):
        with storage.expanded_runtime_evidence(out,report['archive_sha256']):pytest.fail('Old layout reader accepted new format')


@pytest.mark.parametrize('field,value',[('outcome','RAISED'),('stopped_verified',False),('attempt_sha256','0'*64)])
def test_unfinished_failed_or_other_attempt_seal_cannot_be_archived(attempt,tmp_path,field,value):
    path=attempt/'finished.json';record=read_record(path);record[field]=value
    write_record(path,record,replace=True)
    out=tmp_path/'refused.zip'
    with pytest.raises(ValueError,match='sealed'):pack(attempt,out)
    assert not out.exists()


def test_existing_archive_is_never_overwritten(attempt,tmp_path):
    out=tmp_path/'existing.zip';out.write_bytes(b'earlier work')
    with pytest.raises(ValueError,match='fresh'):pack(attempt,out)
    assert out.read_bytes()==b'earlier work'


def test_rehashed_objects_cannot_disagree_with_original_sealed_inventory(attempt,tmp_path):
    from nasolve.cif_complete_attempt_archive import expanded_complete_attempt_evidence
    out=tmp_path/'attempt.zip';report=pack(attempt,out)
    def change(index,members):
        index['files']['working.bin']=dict(index['files']['result.json'])
    rewrite(out,change)
    with pytest.raises(ValueError,match='sealed inventory'):
        with expanded_complete_attempt_evidence(out,sha256(out.read_bytes()).hexdigest(),finished_sha256=report['finished_sha256']):pytest.fail('Changed logical file despite original seal')
