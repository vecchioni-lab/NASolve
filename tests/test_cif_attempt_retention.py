from tests.test_cif_complete_request import case
from tests.test_cif_complete_continuation import joined


def test_archived_result_keeps_original_public_paths_after_working_files_are_removed(joined):
    from nasolve.cif_attempt_retention import prepare_attempt_archive, kept_path
    m,args,root,sdk,store,generations,state=joined
    m.initialize_dictionary_request(output=root,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=m.read_dictionary_request_result(root,1)
    prepare_attempt_archive(root,1)
    attempt=root/'attempts/attempt-0001'
    for path in sorted(attempt.rglob('*'),reverse=True):
        name=path.relative_to(attempt).as_posix()
        if path.is_file() and not kept_path(name):path.unlink()
    after=m.read_dictionary_request_result(root,1)
    assert after==before
    assert after['runtime']['model'].is_file()
    assert after['preparation']['bundle_directory'].is_dir()

from hashlib import sha256
import pytest
from nasolve.campaign_records import read_record, write_record
from nasolve.campaign_process import exclusive_lock, CampaignProcessError
from tests.test_cif_repair_attempt import inventory


def completed(joined):
    m,args,root,sdk,store,generations,state=joined
    m.initialize_dictionary_request(output=root,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    return m,root,root/'attempts/attempt-0001'


def test_archive_publication_repeat_and_reads_do_not_change_scientific_records(joined):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,root,attempt=completed(joined);original=inventory(attempt)
    record=prepare_attempt_archive(root,1);before=inventory(root)
    assert prepare_attempt_archive(root,1)==record
    m.inspect_dictionary_request(root);m.read_dictionary_request_result(root,1)
    assert inventory(root)==before and inventory(attempt)==original
    assert record['finished_sha256']==sha256((attempt/'finished.json').read_bytes()).hexdigest()


def test_exact_archive_reads_relocate_and_allow_a_fresh_attempt_without_repairing_old_work(joined,tmp_path):
    from nasolve.cif_attempt_retention import prepare_attempt_archive, kept_path
    m,root,attempt=completed(joined);prepare_attempt_archive(root,1)
    for p in attempt.rglob('*'):
        if p.is_file() and not kept_path(p.relative_to(attempt).as_posix()):p.unlink()
    moved=tmp_path/'relocated';root.rename(moved)
    before=inventory(moved/'attempts/attempt-0001');archive=inventory(moved/'retention')
    value=m.read_dictionary_request_result(moved,1)
    assert value['runtime']['model'].is_relative_to(moved) and value['runtime']['model'].is_file()
    assert not root.exists()
    _,args,_,sdk,store,generations,state=joined
    result=m.execute_dictionary_request_attempt(moved,sdk,store,generation=generations)
    assert result['attempt_number']==2 and len(state['calls'])==2
    assert inventory(moved/'attempts/attempt-0001')==before and inventory(moved/'retention')==archive
    assert set(m.read_dictionary_request_results(moved,[2,1]))=={1,2}


@pytest.mark.parametrize('defect',['request','attempt','number','finished','archive-bytes','public-missing',
    'public-changed','unexpected-file','symbolic-public','unlisted-directory'])
def test_archived_owner_or_remaining_evidence_cannot_drift(joined,defect,tmp_path):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,root,attempt=completed(joined);prepare_attempt_archive(root,1)
    folder=root/'retention/attempt-0001';receipt=folder/'archive.json';record=read_record(receipt)
    if defect in {'request','attempt','finished'}:
        record[defect+'_sha256']='0'*64;write_record(receipt,record,replace=True)
    elif defect=='number':record['number']=True;write_record(receipt,record,replace=True)
    elif defect=='archive-bytes':(folder/'evidence.zip').write_bytes(b'corrupt')
    elif defect.startswith('public') or defect=='symbolic-public':
        model=attempt/'continuation/runtime/model.pdb'
        if defect=='public-changed':model.write_text('changed')
        else:
            old=model.read_bytes();model.unlink()
            if defect=='symbolic-public':
                target=tmp_path/'outside.pdb';target.write_bytes(old);model.symlink_to(target)
    elif defect=='unexpected-file':(attempt/'unexpected.txt').write_text('unowned')
    else:(attempt/'unknown').mkdir()
    before=inventory(root) if defect!='symbolic-public' else None
    with pytest.raises((ValueError,OSError)):m.read_dictionary_request_result(root,1)
    if before is not None:assert inventory(root)==before


def test_unpublished_partial_archive_neither_changes_read_nor_authorizes_overwrite(joined):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,root,attempt=completed(joined);folder=root/'retention/attempt-0001';folder.mkdir(parents=True)
    archive=folder/'evidence.zip';archive.write_bytes(b'interrupted write')
    before=inventory(root);assert m.read_dictionary_request_result(root,1)['runtime']['model'].is_file()
    with pytest.raises(ValueError):prepare_attempt_archive(root,1)
    assert inventory(root)==before and not (folder/'archive.json').exists()


def test_complete_unpublished_archive_recovers_without_repacking(joined,monkeypatch):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);write=r.write_record
    monkeypatch.setattr(r,'write_record',lambda *a,**k:(_ for _ in ()).throw(OSError('interrupted publication')))
    with pytest.raises(OSError):r.prepare_attempt_archive(root,1)
    archive=root/'retention/attempt-0001/evidence.zip';before=archive.read_bytes();stamp=archive.stat().st_mtime_ns
    monkeypatch.setattr(r,'write_record',write)
    monkeypatch.setattr(r,'pack_complete_attempt_evidence',lambda *a,**k:pytest.fail('Repacked immutable archive'))
    r.prepare_attempt_archive(root,1)
    assert archive.read_bytes()==before and archive.stat().st_mtime_ns==stamp
    assert m.read_dictionary_request_result(root,1)['runtime']['model'].is_file()


def test_unretained_result_path_refuses_archive_binding(joined,monkeypatch):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,root,attempt=completed(joined);old=m._result;before=inventory(attempt)
    def expose(root,attempt,*a,**k):
        value=old(root,attempt,*a,**k);value['new_unstable_path']=attempt/'repair/request.json';return value
    monkeypatch.setattr(m,'_result',expose)
    with pytest.raises(ValueError,match='unretained'):prepare_attempt_archive(root,1)
    assert not (root/'retention/attempt-0001/archive.json').exists() and inventory(attempt)==before


def test_retention_uses_existing_request_lock(joined):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,root,attempt=completed(joined)
    with exclusive_lock(root/'request.lock'):
        with pytest.raises(CampaignProcessError):prepare_attempt_archive(root,1)
    assert not (root/'retention').exists()


def test_failed_or_unfinished_owner_is_preserved_without_archive(joined):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,args,root,sdk,store,generations,state=joined;state['fault']='interrupted'
    m.initialize_dictionary_request(output=root,**args)
    with pytest.raises(KeyboardInterrupt):m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=inventory(root)
    with pytest.raises(ValueError):prepare_attempt_archive(root,1)
    assert inventory(root)==before and not (root/'retention').exists()


def test_archiving_one_attempt_cannot_hide_bad_other_history(joined):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,root,attempt=completed(joined);prepare_attempt_archive(root,1)
    _,args,_,sdk,store,generations,state=joined
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    (root/'attempts/attempt-0002/continuation/runtime/model.pdb').write_text('changed')
    with pytest.raises(ValueError):m.read_dictionary_request_result(root,1)


@pytest.mark.parametrize('defect',['archive','public'])
def test_change_during_read_is_detected_before_temporary_view_closes(joined,monkeypatch,defect):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,root,attempt=completed(joined);prepare_attempt_archive(root,1);original=m._result
    def changed(root_,view,*args,**kwargs):
        result=original(root_,view,*args,**kwargs)
        if view!=attempt:
            path=root/'retention/attempt-0001/evidence.zip' if defect=='archive' else attempt/'continuation/runtime/model.pdb'
            path.write_bytes(b'changed after validation')
        return result
    monkeypatch.setattr(m,'_result',changed)
    with pytest.raises(ValueError):m.read_dictionary_request_result(root,1)


def test_legacy_layout_is_readable_but_not_silently_migrated(case):
    from nasolve.cif_attempt_retention import prepare_attempt_archive
    m,args,root,sdk,store,generations,calls=case
    m.initialize_dictionary_request(output=root,artifact_policy=None,**args)
    m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=inventory(root)
    with pytest.raises(ValueError,match='current-partition'):prepare_attempt_archive(root,1)
    assert inventory(root)==before and m.read_dictionary_request_result(root,1)['runtime'] is None
