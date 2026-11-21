"""Compact comparisons must retain explicit parent and important-result evidence."""
from pathlib import Path
from unittest.mock import patch
import json,shutil
import pytest
from nasolve.metal import publication as m,parent_archive,child_session
from nasolve.metal.recipe import RecipeError
from tests.test_metal_retained_execution import run
from tests.test_metal_child_session import setup
from tests.test_metal_child_process import inventory


def ready(tmp_path,monkeypatch):
    values,native=setup(tmp_path,monkeypatch)
    store=tmp_path/'store';store.mkdir();protected=store/'important';protected.mkdir()
    parent=store/'parent';values[1].rename(parent);values=(values[0],parent,values[2],values[3])
    with parent_archive.retained_parent_inputs(parent,values[3]['parent_manifest_sha256']) as handle:
        first=run(protected,values,native,handle,'selected')
        second=run(tmp_path,values,native,handle,'increment')
    children=[dict(directory=protected/'selected',review_id=first['record_sha256']),dict(directory=tmp_path/'increment',review_id=second['record_sha256'])]
    parents={values[3]['parent_manifest_sha256']:parent}
    return store,children,parents,[first['record_sha256']],[first['result'],second['result']]


def publish(values,**kwargs):
    store,children,parents,protected,_=values
    return m.publish_audited_results(store,children,store/'results.zip',store/'publication.json',
        parent_archives=parents,protected_reviews=protected,**kwargs)


def test_shared_requests_cold_reopen_after_only_expendable_fixture_removal(tmp_path,monkeypatch):
    values=ready(tmp_path,monkeypatch);store,children,parents,protected,expected=values
    protected_before=inventory(store/'important');parent_before=inventory(store/'parent')
    receipt=publish(values)
    assert len(receipt['attempts'])==2 and receipt['request_count']==1
    assert len(receipt['parents'])==len(receipt['protected_reviews'])==1
    assert str(tmp_path) not in json.dumps(receipt)
    shutil.rmtree(children[1]['directory']);shutil.rmtree(tmp_path/'layout');shutil.rmtree(tmp_path/'prepared')
    moved=tmp_path/'relocated';store.rename(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')),patch.object(m.archive_owner,'_expanded_evidence',wraps=m.archive_owner._expanded_evidence) as expansion:
        report=m.inspect_published_audited_results(moved,receipt,publication_id=receipt['record_sha256'])
        assert expansion.call_count==1
    assert [r['result'] for r in report['records']]==expected
    assert report['protected_reviews_verified']==protected
    assert report['scientific_audit_replayed_for_all_records'] is False
    assert not report['retirement_authorized'] and not report['reuse_authorized']
    assert protected_before==inventory(moved/'important') and parent_before==inventory(moved/'parent')


@pytest.mark.parametrize('missing',['parent-part','important-native','important-review'])
def test_missing_protected_evidence_refuses_despite_intact_compact_rows(tmp_path,monkeypatch,missing):
    values=ready(tmp_path,monkeypatch);receipt=publish(values);store=values[0]
    targets={'parent-part':store/'parent/part-001.zip','important-native':store/'important/selected/attempt/native/fdp/job/native-result.json.gz','important-review':store/'important/selected/review.json'}
    archive=(store/'results.zip').read_bytes();targets[missing].unlink()
    with pytest.raises(ValueError):m.inspect_published_audited_results(store,receipt,publication_id=receipt['record_sha256'])
    assert (store/'results.zip').read_bytes()==archive


@pytest.mark.parametrize('defect',['unknown-protection','missing-parent','outside-protected','budget'])
def test_invalid_publication_refuses_without_allocating_archive(tmp_path,monkeypatch,defect):
    values=list(ready(tmp_path,monkeypatch));options={}
    if defect=='unknown-protection':values[3]=['0'*64]
    elif defect=='missing-parent':values[2]={}
    elif defect=='outside-protected':values[3]=[values[1][1]['review_id']]
    else:options['max_input_bytes']=1
    before=inventory(values[0])
    with pytest.raises(ValueError):publish(values,**options)
    assert not (values[0]/'results.zip').exists() and inventory(values[0])==before


def test_interrupted_receipt_retains_sources_and_unpublished_archive(tmp_path,monkeypatch):
    values=ready(tmp_path,monkeypatch);before=inventory(values[0])
    monkeypatch.setattr(m,'_write_publication',lambda *a,**k:(_ for _ in ()).throw(OSError('Interrupted publication')))
    with pytest.raises(RecipeError,match='Interrupted'):publish(values)
    assert (values[0]/'results.zip').is_file() and not (values[0]/'publication.json').exists()
    assert all((values[0]/name).read_bytes()==raw for name,raw in before.items())


def test_late_changed_source_refuses_final_publication(tmp_path,monkeypatch):
    values=ready(tmp_path,monkeypatch);sync=m._sync_archive
    def changed(path):
        sync(path);p=values[1][-1]['directory']/'review.json';p.write_bytes(p.read_bytes()+b'changed')
    monkeypatch.setattr(m,'_sync_archive',changed)
    with pytest.raises(ValueError):publish(values)
    assert (values[0]/'results.zip').is_file() and not (values[0]/'publication.json').exists()


def test_wrong_independent_pin_and_changed_archive_refuse(tmp_path,monkeypatch):
    values=ready(tmp_path,monkeypatch);receipt=publish(values)
    with patch.object(m.archive_owner,'_expanded_evidence',side_effect=AssertionError('Pin must refuse before expansion')):
        with pytest.raises(ValueError):m.inspect_published_audited_results(values[0],receipt,publication_id='0'*64)
    (values[0]/'results.zip').write_bytes(b'changed')
    with pytest.raises(ValueError):m.inspect_published_audited_results(values[0],receipt,publication_id=receipt['record_sha256'])


@pytest.mark.parametrize('target',['parent','important/selected'])
def test_publication_cannot_write_inside_a_protected_node(tmp_path,monkeypatch,target):
    values=ready(tmp_path,monkeypatch);store,children,parents,protected,_=values
    before=inventory(store)
    with pytest.raises(RecipeError,match='outside'):
        m.publish_audited_results(store,children,store/target/'new.zip',store/'publication.json',
            parent_archives=parents,protected_reviews=protected)
    assert inventory(store)==before
