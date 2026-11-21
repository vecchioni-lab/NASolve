"""Retained read lifetime is explicit in process and scientific review records."""
from pathlib import Path
from unittest.mock import patch
import shutil
import pytest
from nasolve.metal import parent_archive as p,child_session as m,child_process as process
from nasolve.metal.recipe import RecipeError
from tests.test_metal_child_session import setup
from tests.test_metal_child_review import republish
from tests.test_metal_child_process import setup as process_setup,invoke,inventory


def run(tmp_path,values,native,retained,name='session'):
    return m.run_audited_child(values[2],values[1],values[3],request_id=values[3]['request_id'],
        run_relative='dataset/AutoMR/run_001',endpoint_relative='Metal/xyz_001',
        session_directory=tmp_path/name,native=native,timeout_seconds=5,retained_parent=retained)


def finished(tmp_path,monkeypatch):
    values,native=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256']) as retained:
        review=run(tmp_path,values,native,retained)
    return values,review


def test_two_audited_children_share_one_parent_but_reacquire_every_scientific_gate(tmp_path,monkeypatch):
    values,native=setup(tmp_path,monkeypatch);original=inventory(values[1])
    with patch.object(p,'_decode',wraps=p._decode) as expansion,patch.object(m,'inspect_observations',wraps=m.inspect_observations) as metadata,patch.object(m,'reference_scattering',wraps=m.reference_scattering) as scattering,patch.object(m,'audit_free_r_flags',wraps=m.audit_free_r_flags) as free_r,patch.object(m.child_inputs,'read_registry',wraps=m.child_inputs.read_registry) as registry:
        with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256']) as retained:
            a=run(tmp_path,values,native,retained,'first');b=run(tmp_path,values,native,retained,'second')
            assert a['schema_version']==b['schema_version']==2
            assert a['parent_scope']==b['parent_scope']
            assert a['result']==b['result'] and a['result']['freeze_audit']=='PASS'
            for name,review in [('first',a),('second',b)]:
                outcome=m.records.read_record(tmp_path/name/'attempt/outcome.json')
                assert outcome['schema_version']==2 and outcome['parent_scope']==review['parent_scope']
                assert outcome['parent_read']['consumer_completed'] and outcome['parent_transport_verified']
                assert not outcome['parent_read']['snapshot_removed']
            assert expansion.call_count==1 and registry.call_count==4
            assert metadata.call_count==scattering.call_count==free_r.call_count==2
        assert not retained.root.exists()
    assert inventory(values[1])==original


def test_relocated_retained_session_cold_reads_without_handle_originals_or_native(tmp_path,monkeypatch):
    values,review=finished(tmp_path,monkeypatch)
    moved=tmp_path/'relocated';(tmp_path/'session').rename(moved)
    shutil.rmtree(tmp_path/'layout');shutil.rmtree(values[1]);shutil.rmtree(values[2])
    before=inventory(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('No native execution')),patch.object(m.child_inputs,'verify_child_inputs',side_effect=AssertionError('No parent replay')):
        result=m.inspect_audited_child(moved,review_id=review['record_sha256'])
    assert result['schema_version']==2 and result['result']==review['result']
    assert result['recorded_parent_scope']==review['parent_scope']
    assert not result['parent_snapshot_cleanup_verified'] and not result['reuse_authorized']
    assert inventory(moved)==before


@pytest.mark.parametrize('defect',['expired','substituted'])
def test_invalid_handle_prevents_session_allocation(tmp_path,monkeypatch,defect):
    values,native=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256']) as retained:
        if defect=='expired':retained.active=False
        else:retained.digest='0'*64
        with pytest.raises(ValueError):run(tmp_path,values,native,retained)
        assert not (tmp_path/'session').exists()


@pytest.mark.parametrize('defect',['expired','changed'])
def test_parent_changed_after_process_prevents_scientific_publication(tmp_path,monkeypatch,defect):
    values,native=setup(tmp_path,monkeypatch);original=inventory(values[1]);real=process.run_child
    def changed(*args,**kwargs):
        value=real(*args,**kwargs)
        if defect=='expired':retained.active=False
        else:
            target=next(retained.root.rglob('model.pdb'));target.chmod(0o600);target.write_bytes(target.read_bytes()+b'changed')
        return value
    monkeypatch.setattr(process,'run_child',changed)
    try:
        with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256']) as retained:
            with pytest.raises(ValueError):run(tmp_path,values,native,retained)
    except ValueError:
        assert defect=='changed'
    assert not retained.root.exists() and inventory(values[1])==original
    assert not (tmp_path/'session/review.json').exists()
    assert (tmp_path/'session/failure.json').is_file() and (tmp_path/'session/attempt/outcome.json').is_file()


def test_uncertain_stop_preserves_attempt_and_invalidates_parent_scope(tmp_path,monkeypatch):
    values=process_setup(tmp_path);original=inventory(values[1])
    monkeypatch.setattr('nasolve.campaign_process._group_alive',lambda pgid:None)
    with p.retained_parent_inputs(values[1],values[2]['parent_manifest_sha256']) as retained:
        result=invoke(tmp_path,values,retained_parent=retained,timeout_seconds=5)
        assert result['status']=='STOP_UNCERTAIN' and not result['stopped_verified']
        assert not result['fresh_retry_eligible'] and not result['outcome']['parent_transport_verified']
        assert result['outcome']['parent_read']['inputs_unchanged']
        assert not result['outcome']['parent_read']['consumer_completed']
        with pytest.raises(ValueError):invoke(tmp_path,values,'second',retained_parent=retained)
        assert not (tmp_path/'second').exists()
    assert inventory(values[1])==original and (tmp_path/'attempt/outcome.json').is_file()


def test_timeout_retains_evidence_and_requires_new_explicit_attempt(tmp_path):
    values=process_setup(tmp_path);original=inventory(values[1]);values[3].environment['SIM_MODE']='timeout'
    with p.retained_parent_inputs(values[1],values[2]['parent_manifest_sha256']) as retained:
        result=invoke(tmp_path,values,retained_parent=retained,timeout_seconds=.5)
        assert result['status']=='TIMED_OUT' and result['stopped_verified'] and result['fresh_retry_eligible']
        before=inventory(tmp_path/'attempt');values[3].environment['SIM_MODE']='success'
        second=invoke(tmp_path,values,'retry',retry_from=tmp_path/'attempt',retained_parent=retained,timeout_seconds=5)
        assert second['status']=='COMPLETED' and second['outcome']['retry_of']==result['outcome']['record_sha256']
        assert inventory(tmp_path/'attempt')==before
    assert inventory(values[1])==original


@pytest.mark.parametrize('defect',['scope','cleanup','read-incomplete','old-review-version'])
def test_rehashed_lifetime_claims_cannot_cross_cold_review(tmp_path,monkeypatch,defect):
    _,review=finished(tmp_path,monkeypatch);root=tmp_path/'session'
    if defect=='scope':review['parent_scope']['scope_id']='0'*64
    elif defect=='cleanup':review['parent_scope']['snapshot_cleanup']='REMOVED'
    elif defect=='old-review-version':review['schema_version']=1
    else:
        # Even consistent before/after, derivation and proof hashes cannot claim
        # that an unfinished parent read qualified this fit.
        from nasolve.metal.recipe import digest
        for name in ('parent-before.json','parent-after.json'):
            value=m.records.read_record(root/name);value['parent_transport']['consumer_completed']=False
            unsigned={k:v for k,v in value.items() if k not in {'derivation_id','record_sha256'}}
            value['derivation_id']=digest(unsigned);m.records.write_record(root/name,value,replace=True)
            review['parent_derivation_before']=review['parent_derivation_after']=value['derivation_id']
            review=republish(root,review,name)
    changed=republish(root,review)
    with pytest.raises(RecipeError):m.inspect_audited_child(root,review_id=changed['record_sha256'])


def test_expiry_during_borrow_refuses_and_preserves_originals(tmp_path):
    values=process_setup(tmp_path);original=inventory(values[1])
    with p.retained_parent_inputs(values[1],values[2]['parent_manifest_sha256']) as retained:
        with pytest.raises(ValueError,match='expired'):
            with p.read_parent_inputs(values[1],values[2]['parent_manifest_sha256'],retained_parent=retained) as (root,receipt):
                retained.active=False
    assert not root.exists() and not receipt['inputs_unchanged'] and inventory(values[1])==original


def test_owned_interrupt_retains_stopped_phase_and_original_parent(tmp_path,monkeypatch):
    from nasolve import campaign_process
    values=process_setup(tmp_path);original=inventory(values[1]);values[3].environment['SIM_MODE']='timeout'
    runner=campaign_process._run_owned_process
    def interrupting(*args,**kwargs):
        heartbeat=kwargs.get('on_heartbeat')
        def interrupted(identity):
            if heartbeat:heartbeat(identity)
            raise KeyboardInterrupt('Synthetic owned-child interruption')
        kwargs['on_heartbeat']=interrupted
        return runner(*args,**kwargs)
    monkeypatch.setattr(campaign_process,'_run_owned_process',interrupting)
    with p.retained_parent_inputs(values[1],values[2]['parent_manifest_sha256']) as retained:
        result=invoke(tmp_path,values,retained_parent=retained,timeout_seconds=5)
        assert result['status']=='INTERRUPTED' and result['stopped_verified']
        assert result['fresh_retry_eligible'] and result['outcome']['parent_transport_verified']
        assert result['outcome']['error']['type']=='KeyboardInterrupt'
        assert result['process']['phases']['native-fdp']['finished']['status']=='INTERRUPTED'
    assert inventory(values[1])==original and (tmp_path/'attempt/outcome.json').is_file()


@pytest.mark.parametrize('target',['outcome.json','review.json'])
def test_interrupted_publication_never_becomes_a_completed_review(tmp_path,monkeypatch,target):
    values,native=setup(tmp_path,monkeypatch);original=inventory(values[1]);write=m.records.write_record
    def interrupted(path,value,**kwargs):
        if Path(path).name==target:raise OSError('Interrupted publication')
        return write(path,value,**kwargs)
    monkeypatch.setattr(m.records,'write_record',interrupted)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256']) as retained:
        with pytest.raises(RecipeError,match='Interrupted publication'):run(tmp_path,values,native,retained)
    assert not (tmp_path/'session/review.json').exists()
    assert (tmp_path/'session/failure.json').exists() and (tmp_path/'session/attempt/inputs/request.json').exists()
    assert inventory(values[1])==original
    status=process.inspect_child(tmp_path/'session/attempt',request_id=values[3]['request_id'])
    if target=='outcome.json':assert status['status']=='REVIEW_REQUIRED' and not status['fresh_retry_eligible']
    else:assert status['status']=='COMPLETED' and status['stopped_verified']


def test_retained_process_outcome_cannot_be_relabelled_legacy(tmp_path,monkeypatch):
    _,review=finished(tmp_path,monkeypatch);attempt=tmp_path/'session/attempt'
    value=m.records.read_record(attempt/'outcome.json');value['schema_version']=1
    m.records.write_record(attempt/'outcome.json',value,replace=True)
    with pytest.raises(RecipeError,match='legacy outcome'):
        process.inspect_child(attempt,request_id=review['request_id'])
