"""Retirement removes only reproducible duplicates after durable successful proof."""
from copy import deepcopy
import pytest
from nasolve.campaign_records import read_record, write_record
from tests.test_cif_complete_request import case
from tests.test_cif_complete_continuation import joined
from tests.test_cif_attempt_retention import completed
from tests.test_cif_repair_attempt import inventory


def test_successful_retirement_keeps_result_and_original_scientific_records(joined):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);before=inventory(attempt)
    public={n:v for n,v in before.items() if r.kept_path(n)}
    original=m.read_dictionary_request_result(root,1)
    receipt=r.retire_attempt_working_files(root,1)
    assert receipt['retired_files']==len(before)-len(public)
    assert inventory(attempt)==public
    assert m.read_dictionary_request_result(root,1)==original
    state=inventory(root)
    assert r.retire_attempt_working_files(root,1)==receipt and inventory(root)==state
    assert m.inspect_dictionary_request(root)['attempts'][0]['state']=='STOPPED'


@pytest.mark.parametrize('after',[0,2,'last'])
def test_interrupted_removal_is_readable_then_resumes_without_native_retry(joined,monkeypatch,after):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);before=inventory(attempt);remove=r._remove_duplicate;calls=[]
    limit=sum(not r.kept_path(n) for n in before) if after=='last' else after
    def interrupted(path,reference):
        assert (root/'retention/attempt-0001/archive.json').is_file()
        assert (root/'retention/attempt-0001/retire-intent.json').is_file()
        if len(calls)==limit:raise KeyboardInterrupt('storage interruption')
        remove(path,reference);calls.append(path)
        if after=='last' and len(calls)==limit:raise KeyboardInterrupt('after final unlink')
    monkeypatch.setattr(r,'_remove_duplicate',interrupted)
    with pytest.raises(KeyboardInterrupt):r.retire_attempt_working_files(root,1)
    assert not (root/'retention/attempt-0001/retired.json').exists()
    assert m.read_dictionary_request_result(root,1)['runtime']['model'].is_file()
    monkeypatch.setattr(r,'_remove_duplicate',remove)
    receipt=r.retire_attempt_working_files(root,1)
    assert receipt['retired_files']==sum(not r.kept_path(n) for n in before)
    assert len(joined[-1]['calls'])==1 and inventory(attempt)=={n:v for n,v in before.items() if r.kept_path(n)}


def test_changed_working_file_is_preserved_instead_of_removed(joined,monkeypatch):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);remove=r._remove_duplicate;changed=[]
    def altered(path,reference):
        path.write_bytes(b'new operator work');changed.append(path);remove(path,reference)
    monkeypatch.setattr(r,'_remove_duplicate',altered)
    with pytest.raises(ValueError,match='changed before retirement'):r.retire_attempt_working_files(root,1)
    assert len(changed)==1 and changed[0].read_bytes()==b'new operator work'
    assert not (root/'retention/attempt-0001/retired.json').exists()


def test_finished_publication_interruption_recovers_without_removing_more_files(joined,monkeypatch):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);write=r.write_record
    def interrupted(path,*a,**k):
        if path.name=='retired.json':raise OSError('completion interrupted')
        return write(path,*a,**k)
    monkeypatch.setattr(r,'write_record',interrupted)
    with pytest.raises(OSError):r.retire_attempt_working_files(root,1)
    before=inventory(attempt);assert m.read_dictionary_request_result(root,1)['runtime']['model'].is_file()
    monkeypatch.setattr(r,'write_record',write)
    monkeypatch.setattr(r,'_remove_duplicate',lambda *a,**k:pytest.fail('No duplicates remain'))
    r.retire_attempt_working_files(root,1);assert inventory(attempt)==before


def test_unqualified_or_failed_attempt_is_not_archived_or_retired(case):
    from nasolve import cif_attempt_retention as r
    m,args,root,sdk,store,generations,calls=case
    m.initialize_dictionary_request(output=root,**args);m.execute_dictionary_request_attempt(root,sdk,store,generation=generations)
    before=inventory(root)
    with pytest.raises(ValueError,match='qualified'):r.retire_attempt_working_files(root,1)
    assert inventory(root)==before and not (root/'retention').exists()


def test_usable_fallback_does_not_authorize_retiring_failed_native_work(joined):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);request,row,exact=r._archive_history(root,1)
    for defect in ('repair','continuation','plane','optional'):
        owner=deepcopy(row);value=deepcopy(exact)
        failed=dict(state='STOPPED',finished=dict(status='FAILED',returncode=1))
        if defect=='repair':owner['children']['repair']['execution']['phases']['native-example']=failed
        elif defect=='continuation':value['continuation']['process_evidence']['phases']['readyset']=failed
        elif defect=='plane':value['result']['plane_generation']=dict(components={'example':dict(status='KNOWN_GENERATION_FAILURE')})
        else:value['execution']['optional_failure']={'recorded':'failure'}
        with pytest.raises(ValueError,match='Preserve'):r._successful_work(owner,value)
    assert not (root/'retention').exists()


@pytest.mark.parametrize('defect',['intent','completion','reappeared','lost-archive'])
def test_retirement_claim_cannot_outlive_its_archive_or_inventory(joined,defect):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);r.retire_attempt_working_files(root,1);folder=root/'retention/attempt-0001'
    if defect=='intent':
        p=folder/'retire-intent.json';v=read_record(p);v['retention_sha256']='0'*64;write_record(p,v,replace=True)
    elif defect=='completion':
        p=folder/'retired.json';v=read_record(p);v['retired_files']+=1;write_record(p,v,replace=True)
    elif defect=='lost-archive':(folder/'archive.json').unlink()
    else:
        p=attempt/'repair/request.lock';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'')
    with pytest.raises(ValueError):m.read_dictionary_request_result(root,1)


def test_archive_changed_after_preparation_cannot_authorize_any_removal(joined,monkeypatch):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);before=inventory(attempt);remaining=r._remaining;changed=[]
    def corrupt(*args,**kwargs):
        value=remaining(*args,**kwargs)
        archive=root/'retention/attempt-0001/evidence.zip'
        if archive.exists() and not changed:
            archive.write_bytes(b'changed before cleanup');changed.append(True)
        return value
    monkeypatch.setattr(r,'_remaining',corrupt)
    with pytest.raises(ValueError,match='archive|Archive'):r.retire_attempt_working_files(root,1)
    assert inventory(attempt)==before and not (root/'retention/attempt-0001/retired.json').exists()


def test_archive_flush_failure_preserves_originals_and_recovers_before_deletion(joined,monkeypatch):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);before=inventory(attempt);sync=r._sync_archive;seen=[]
    def interrupted(path):
        seen.append(path)
        assert not (path.parent/'archive.json').exists()
        raise OSError('archive durability interrupted')
    monkeypatch.setattr(r,'_sync_archive',interrupted)
    with pytest.raises(OSError):r.retire_attempt_working_files(root,1)
    assert inventory(attempt)==before and len(seen)==1
    assert not (root/'retention/attempt-0001/retire-intent.json').exists()
    saved=seen[0].read_bytes()
    monkeypatch.setattr(r,'_sync_archive',sync)
    receipt=r.retire_attempt_working_files(root,1)
    assert receipt['retired_files']>0 and seen[0].read_bytes()==saved
    assert m.read_dictionary_request_result(root,1)['runtime']['model'].is_file()


def test_changed_intent_after_last_removal_cannot_publish_completion(joined,monkeypatch):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);remove=r._remove_duplicate
    total=sum(not r.kept_path(n) for n in inventory(attempt));count=[]
    def changed(path,reference):
        remove(path,reference);count.append(path)
        if len(count)==total:
            intent=root/'retention/attempt-0001/retire-intent.json'
            value=read_record(intent);value['unexpected']='changed after removals';write_record(intent,value,replace=True)
    monkeypatch.setattr(r,'_remove_duplicate',changed)
    with pytest.raises(ValueError,match='intent changed'):r.retire_attempt_working_files(root,1)
    assert not (root/'retention/attempt-0001/retired.json').exists()
    assert all(r.kept_path(n) for n in inventory(attempt))


def test_retired_request_relocates_without_previous_paths(joined,tmp_path):
    from nasolve import cif_attempt_retention as r
    m,root,attempt=completed(joined);done=r.retire_attempt_working_files(root,1)
    moved=tmp_path/'relocated-retired-request';root.rename(moved)
    assert not root.exists()
    before=inventory(moved);value=m.read_dictionary_request_result(moved,1)
    assert value['runtime']['model'].is_relative_to(moved) and value['runtime']['model'].is_file()
    assert r.retire_attempt_working_files(moved,1)==done and inventory(moved)==before
