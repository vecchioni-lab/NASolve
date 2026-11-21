"""Failed science may release future space only with its own stopped-session proof."""
from unittest.mock import patch
import shutil
import pytest
from nasolve import campaign_records as records
from nasolve.metal import child_session as m,storage_budget as b,parent_archive as p
from nasolve.metal.recipe import RecipeError
from tests.test_metal_session_budget import setup,run,inspect,ALLOWANCE
from tests.test_metal_child_process import inventory


def fail(tmp_path,values,native,parent,options,name='session'):
    with patch.object(m,'_audit_job',side_effect=RecipeError('Synthetic scientific rejection')):
        with pytest.raises(RecipeError,match='scientific rejection'):
            run(tmp_path,values,native,parent,options,name)
    return records.read_record(tmp_path/name/'failure.json')


def settle(tmp_path,options,failure,name='session'):
    admission=records.read_record(tmp_path/name/'storage-admission.json')
    return b.settle_failed_audited_session(tmp_path,budget_id=options['budget_id'],
        reservation_id=admission['reservation_id'],failure_id=failure['record_sha256'])


def test_failed_scientific_audit_releases_only_session_allowance_and_retains_files(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=fail(tmp_path,values,native,parent,options)
        assert failure['schema_version']==2 and failure['process_stop_evidence']['native_status']=='COMPLETED'
        before=inventory(tmp_path/'session')
        proof=settle(tmp_path,options,failure)
        assert proof['postflight_review_complete'] is False and proof['native_stopped_verified']
        assert proof['scientific_acceptance']=='NOT_ASSESSED' and not proof['retirement_authorized']
        assert inventory(tmp_path/'session')==before
        assert inspect(options)['outstanding_bytes']==parent_options['allowance_bytes']
    assert inspect(options)['outstanding_bytes']==0
    moved=tmp_path.with_name(tmp_path.name+'-moved');tmp_path.rename(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')):
        read=m.inspect_failed_audited_child(moved/'session',failure_id=failure['record_sha256'])
        assert read['native_stopped_verified'] and not read['postflight_review_complete']
        with patch.object(m,'inspect_failed_audited_child',side_effect=AssertionError('Already settled')):
            assert b.inspect_budget(moved,budget_id=options['budget_id'])['held_count']==0
            assert settle(moved,options,failure)==proof


@pytest.mark.parametrize('defect',['missing-outer','missing-phase','missing-preflight','declaration','failure','old-failure','review-present'])
def test_incomplete_or_changed_failure_never_releases(tmp_path,monkeypatch,defect):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=fail(tmp_path,values,native,parent,options)
    root=tmp_path/'session'
    if defect=='missing-outer':(root/'attempt/ownership/finished.json').unlink()
    elif defect=='missing-phase':(root/'attempt/ownership/phases/native-fdp/finished.json').unlink()
    elif defect=='missing-preflight':(root/'preflight/ownership/finished.json').unlink()
    elif defect=='review-present':records.write_record(root/'review.json',dict(ambiguous=True))
    else:
        name='request.json' if defect=='declaration' else 'failure.json'
        value=records.read_record(root/name)
        if defect=='declaration':value['storage_reservation']['reservation_id']='0'*64
        elif defect=='old-failure':
            value['schema_version']=1
            value.pop('session_declaration_sha256',None);value.pop('process_stop_evidence',None)
        else:value['message']='changed'
        records.write_record(root/name,value,replace=True)
    with patch('nasolve.cif_repair_process.coordinator_alive',side_effect=AssertionError('No historical PID query')):
        with patch('nasolve.cif_repair_process.process_alive',side_effect=AssertionError('No historical PID query')):
            with pytest.raises((RecipeError,OSError)):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_bytes']==ALLOWANCE


def test_preflight_failure_remains_held_without_recoverable_stop_receipt(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch,'metadata')
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options)
    failure=records.read_record(tmp_path/'session/failure.json')
    assert failure['process_stop_evidence'] is None
    with pytest.raises(RecipeError):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_bytes']==ALLOWANCE


def test_another_failed_session_cannot_release_a_different_grant(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        fail(tmp_path,values,native,parent,options,'first')
        admission=(tmp_path/'first/storage-admission.json').read_bytes()
        other=fail(tmp_path,values,native,parent,options,'other')
    shutil.copytree(tmp_path/'other',tmp_path/'first',dirs_exist_ok=True)
    (tmp_path/'first/storage-admission.json').write_bytes(admission)
    with pytest.raises(RecipeError,match='reservation'):settle(tmp_path,options,other,'first')
    assert inspect(options)['outstanding_bytes']==2*ALLOWANCE


def test_failed_settlement_acknowledgement_loss_is_retryable(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=fail(tmp_path,values,native,parent,options)
    save=b._save
    def lost(*args):
        save(*args);raise OSError('Acknowledgement lost')
    with patch.object(b,'_save',side_effect=lost):
        with pytest.raises(OSError,match='Acknowledgement'):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_bytes']==0
    with patch.object(m,'inspect_failed_audited_child',side_effect=AssertionError('Do not repeat inspection')):
        assert settle(tmp_path,options,failure)['failure_sha256']==failure['record_sha256']


@pytest.mark.parametrize('behavior',['nonzero','timeout'])
def test_known_stopped_native_failure_can_settle_without_scientific_outputs(tmp_path,monkeypatch,behavior):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    executable=native.executables['phenix.python']
    # Preflight exits earlier; only the main synthetic worker takes this path.
    text=executable.read_text();cut=text.index("Path('native-result.json.gz')")
    executable.write_text(text[:cut]+("sys.exit(7)\n" if behavior=='nonzero' else 'time.sleep(20)\n'))
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options)
    failure=records.read_record(tmp_path/'session/failure.json')
    assert failure['process_stop_evidence']['native_status']==('FAILED' if behavior=='nonzero' else 'TIMED_OUT')
    assert not (tmp_path/'session/attempt/outputs.json').exists()
    before=inventory(tmp_path/'session');settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_bytes']==0 and inventory(tmp_path/'session')==before


def test_unknown_native_stop_is_not_promoted_to_recoverable_failure(tmp_path,monkeypatch):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    run_child=m.child_process.run_child
    def uncertain(*args,**kwargs):
        with patch('nasolve.campaign_process._group_alive',return_value=None):
            return run_child(*args,**kwargs)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with patch.object(m.child_process,'run_child',side_effect=uncertain):
            with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options)
    failure=records.read_record(tmp_path/'session/failure.json')
    assert failure['process_stop_evidence'] is None
    with pytest.raises(RecipeError):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_by_scope']['audited_session']==ALLOWANCE


@pytest.mark.parametrize('after_write',[False,True])
def test_review_publication_failure_keeps_success_and_failure_routes_distinct(tmp_path,monkeypatch,after_write):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    write=records.write_record
    def interrupted(path,value,**kwargs):
        if path.name=='review.json':
            if after_write:write(path,value,**kwargs)
            raise OSError('Publication interrupted')
        return write(path,value,**kwargs)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with patch.object(records,'write_record',side_effect=interrupted):
            with pytest.raises(RecipeError):run(tmp_path,values,native,parent,options)
    failure=records.read_record(tmp_path/'session/failure.json')
    if after_write:
        assert failure['process_stop_evidence'] is None
        with pytest.raises(RecipeError):settle(tmp_path,options,failure)
        from tests.test_metal_session_budget import settle as settle_success
        review=records.read_record(tmp_path/'session/review.json')
        settle_success(tmp_path,options,'session',review)
        with pytest.raises(RecipeError):settle(tmp_path,options,failure)
    else:
        assert failure['process_stop_evidence'] is not None
        settle(tmp_path,options,failure)
        from tests.test_metal_session_budget import settle as settle_success
        with pytest.raises(RecipeError):settle_success(tmp_path,options,'session',{'record_sha256':'0'*64})
    assert inspect(options)['outstanding_bytes']==0


def test_busy_lock_preserves_failed_session_credit_for_later_explicit_settlement(tmp_path,monkeypatch):
    from nasolve.campaign_process import exclusive_lock,CampaignProcessError
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        failure=fail(tmp_path,values,native,parent,options)
    with exclusive_lock(tmp_path/b.LOCK):
        with pytest.raises(CampaignProcessError):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_bytes']==ALLOWANCE
    settle(tmp_path,options,failure)
    with pytest.raises(RecipeError):settle(tmp_path,options,dict(record_sha256='0'*64))
    assert inspect(options)['outstanding_bytes']==0


@pytest.mark.parametrize('relative',['attempt/outcome.json','preflight/inspection.json'])
def test_invalid_stop_record_does_not_hide_original_scientific_failure(tmp_path,monkeypatch,relative):
    values,native,parent_options,options=setup(tmp_path,monkeypatch)
    def rejected(*args):
        (tmp_path/'session'/relative).write_text('{}')
        raise RecipeError('Original scientific rejection')
    with p.retained_parent_inputs(values[1],values[3]['parent_manifest_sha256'],storage_budget=parent_options) as parent:
        with patch.object(m,'_audit_job',side_effect=rejected):
            with pytest.raises(RecipeError,match='Original scientific rejection'):run(tmp_path,values,native,parent,options)
    failure=records.read_record(tmp_path/'session/failure.json')
    assert failure['message']=='Original scientific rejection' and failure['process_stop_evidence'] is None
    with pytest.raises(RecipeError):settle(tmp_path,options,failure)
    assert inspect(options)['outstanding_bytes']==ALLOWANCE
