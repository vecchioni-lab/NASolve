"""Orchestration contracts only; native scientific qualification is separate."""
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import pytest
from nasolve import topostitch_captured_job as job
from nasolve.topostitch_recipe import recipe_digest
from tests.test_topostitch_capture import capture


def test_public_api_rejects_invalid_controls_before_loading_owners(monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('Native owners should not be loaded')
    monkeypatch.setattr(job,'_cedar',forbidden)
    for control in (dict(include_pairs=1),dict(trial_iterations=True),dict(trial_calls=9),
                    dict(timeout_seconds=True),dict(timeout_seconds=float('nan')),dict(_process_runner=5),dict(endpoint_points='points'),dict(endpoint_sha256='a'*64),
                    dict(endpoint_points='points',endpoint_sha256='a'*64,trial_iterations=1)):
        with pytest.raises(ValueError):
            job.run_captured_objective('a','b','c','d','out',recipe_sha256='a'*64,
                mask_sha256='b'*64,phenix='native',**control)


def test_developer_owners_are_isolated_and_removed_on_every_exit(tmp_path):
    package=tmp_path/'nasolve';package.mkdir()
    names=('cif_attachment_native','cif_native_validation','cif_candidate_usability',
           'cif_native_nonbonded','cif_native_monomers','cif_fixed_geometry','phenix_runtime',
           'cif_captured_mixed_gradients','campaign_process','cif_selected_environment')
    for name in names:(package/(name+'.py')).write_text('token = object()\n')
    first=None
    for fail in (False,True):
        try:
            with job._cedar(tmp_path) as owners:
                current=owners['cif_attachment_native'];prefix=current.__package__
                assert current is not first
                assert 'nasolve.topostitch_captured_job' in sys.modules
                first=current
                if fail:raise RuntimeError('caller failure')
        except RuntimeError:pass
        assert not any(n==prefix or n.startswith(prefix+'.') for n in sys.modules)
    with pytest.raises(ImportError):
        with job._cedar(tmp_path,guard_live_policy=True):pass
    assert not any(n.startswith('_topostitch_cedar_') for n in sys.modules)
    (package/'cif_live_nonbonded_policy.py').write_text('token = object()\n')
    with job._cedar(tmp_path,guard_live_policy=True) as owners:
        assert 'cif_live_nonbonded_policy' in owners
    (package/'cif_native_validation.py').unlink()
    with pytest.raises(ImportError):
        with job._cedar(tmp_path):pass
    assert not any(n.startswith('_topostitch_cedar_') for n in sys.modules)


def test_context_layering_reuses_cedar_owner_and_keeps_order():
    calls=[]
    def energy(worker):calls.append('energy');return worker+'E'
    def asu(worker,*,policy):calls.append(policy);return worker+'A'
    capture_record={'full_monomer_inventory_policy':'observed'}
    def context(worker,record):
        assert record is capture_record
        calls.append('context');return worker+'M'
    owners={'cif_native_validation':SimpleNamespace(_NATIVE_WORKER='fresh'),
        'cif_candidate_usability':SimpleNamespace(native_energy_worker=energy),
        'cif_native_nonbonded':SimpleNamespace(native_nonbonded_worker=asu),
        'cif_captured_mixed_gradients':SimpleNamespace(_native_context_worker=context)}
    spec=dict(inventory_detail='linked',policy_inventory=True,energy_inventory=True,
        nonbonded_inventory=True,full_monomer_inventory=True,
        nonbonded_policy='cif-native-nonbonded-asu-attribution-v1')
    assert job._worker(spec,capture_record,owners)=='freshEAM'
    assert calls==['energy',spec['nonbonded_policy'],'context']
    with pytest.raises(ValueError):job._worker(dict(spec,atom_name_mapping=True),capture_record,owners)


@pytest.fixture
def context(tmp_path,monkeypatch):
    # Fake owners isolate orchestration. Their reports are deliberately synthetic
    # and are never used to claim a native capture passes authentication.
    root=tmp_path/'inputs';root.mkdir();native=capture()
    native['geometry']['proxy_details']={};native['restraint_policy']['origin_ids']={'edits':7}
    model=root/'model.pdb';model.write_bytes(b'synthetic-model')
    packet={};recipe=root/'recipe.json';recipe.write_text(json.dumps(packet))
    mask=root/'mask.json';mask.write_text(json.dumps(dict(schema_version=1,
        kind='topostitch-native-mask-request',source_model_sha256=sha256(model.read_bytes()).hexdigest(),
        movable_indices=[0],tether_sigma_angstrom=.1,max_displacement_angstrom=.5,max_evaluations=10000)))
    receipt=root/'capture/native_receipt.json';receipt.parent.mkdir()
    executable=tmp_path/'phenix.python';executable.write_bytes(b'synthetic-dispatcher')
    installation=SimpleNamespace(version='test-version',executables={'phenix.python':executable},environment={})
    observed=dict(status='REVIEW',phenix_version=installation.version,executable_sha256=sha256(executable.read_bytes()).hexdigest())
    receipt.write_text(json.dumps(observed))
    spec=dict(model='inputs/model.pdb',dictionaries=[],phil_files=[])
    for name,data in [('native_spec.json',json.dumps(spec).encode()),('native_validation.json',json.dumps(native).encode()),('inputs/model.pdb',model.read_bytes())]:
        p=receipt.parent/name;p.parent.mkdir(exist_ok=True);p.write_bytes(data)
    snapshots={p:p.read_bytes() for p in receipt.parent.rglob('*') if p.is_file()}
    src=tmp_path/'owners';src.mkdir()
    for name in ('owner.py','cif_parallelity_correction.py','cif_gradient_audit.py'):(src/name).write_text('# synthetic owner\n')
    class OwnershipError(RuntimeError):pass
    seen=[]
    def native_command(command,**kwargs):
        runner=kwargs.pop('process_runner');seen.append(runner)
        return runner(command,**kwargs)
    owners=dict(cif_attachment_native=SimpleNamespace(__file__=str(src/'owner.py'),__package__='_synthetic_cedar',
        _capture=lambda *a:(observed,native,snapshots)),
        cif_fixed_geometry=SimpleNamespace(_fixed_policy=lambda n:True),
        cif_native_validation=SimpleNamespace(_run_native_command=native_command),
        cif_native_monomers=SimpleNamespace(review_full_monomers=lambda n:None),
        cif_native_nonbonded=SimpleNamespace(review_native_nonbonded=lambda n:None),
        campaign_process=SimpleNamespace(CampaignProcessError=OwnershipError))
    @contextmanager
    def selected(*a,**kw):yield owners
    monkeypatch.setattr(job,'_cedar',selected);monkeypatch.setattr(job,'_worker',lambda *a:'# fresh trusted builder\n')
    args=dict(model=model,recipe=recipe,mask=mask,native_receipt=receipt,output_parent=tmp_path/'output',
        recipe_sha256=recipe_digest(packet),mask_sha256=sha256(mask.read_bytes()).hexdigest(),phenix=installation)
    return SimpleNamespace(args=args,native=native,seen=seen,OwnershipError=OwnershipError,installation=installation,owners=owners)


def test_owned_runner_is_forwarded_and_repeat_jobs_keep_separate_evidence(context):
    context.installation.version='test-version-build-label'
    def runner(command,*,cwd,log_path,environment,timeout_seconds):
        assert command[1:]==['-B','evaluate.py'] and timeout_seconds==600
        assert environment['PYTHONDONTWRITEBYTECODE']=='1'
        (cwd/'evaluation.json').write_text(json.dumps(dict(status='INITIAL_CONTEXT_AND_EVALUATIONS_MATCH',optimization=False)))
        (cwd/'bootstrap/native_validation.json').write_text(json.dumps(context.native));log_path.write_text('synthetic execution')
        return 0
    a,first=job.run_captured_objective(**context.args,_process_runner=runner)
    b,second=job.run_captured_objective(**context.args,_process_runner=runner)
    assert a!=b and first==second
    assert first['inputs_and_sources_preserved'] and not first['optimization']
    assert context.seen==[runner,runner]
    assert all(row['anchor']=='probe_directory' and not Path(row['path']).is_absolute() for row in first['files'])


def test_uncertain_process_ownership_escapes_after_receipt_is_preserved(context):
    def runner(*a,**kw):raise context.OwnershipError('cleanup not verified')
    with pytest.raises(context.OwnershipError,match='cleanup not verified'):
        job.run_captured_objective(**context.args,_process_runner=runner)
    receipts=list(context.args['output_parent'].glob('*/receipt.json'));assert len(receipts)==1
    report=json.loads(receipts[0].read_bytes())
    assert report['status']=='FAILED' and report['execution']['status']=='OWNERSHIP_ERROR'
    assert report['inputs_and_sources_preserved']


@pytest.mark.parametrize('removed',['model','dispatcher'])
def test_verified_timeout_and_removed_input_still_retain_failed_receipt(context,removed):
    def timeout(command,**kw):raise subprocess.TimeoutExpired(command,600)
    root,report=job.run_captured_objective(**context.args,_process_runner=timeout)
    assert report['execution']==dict(status='TIMED_OUT',timeout_seconds=600,returncode=None)
    assert (root/'receipt.json').exists()
    def changed(*a,**kw):
        path=context.args['model'] if removed=='model' else context.installation.executables['phenix.python']
        path.unlink();raise ValueError('failed job')
    root,report=job.run_captured_objective(**context.args,_process_runner=changed)
    assert not report['inputs_and_sources_preserved'] and report['status']=='FAILED'
    assert (root/'receipt.json').exists()


def test_dispatcher_mismatch_rejects_before_any_output_or_launch(context):
    context.installation.executables['phenix.python'].write_bytes(b'changed')
    with pytest.raises(ValueError,match='dispatcher'):
        job.run_captured_objective(**context.args)
    assert not context.args['output_parent'].exists() and context.seen==[]


def test_failed_trial_receipt_keeps_diagnostic_pass_separate_from_job_status(context):
    def runner(command,*,cwd,log_path,**kw):
        (cwd/'evaluation.json').write_text(json.dumps(dict(status='TRIAL_REVIEW_REQUIRED',optimization=True,
            trial=dict(status='FAILED',error='RuntimeError: original line-search failure',
                failure_endpoint=dict(status='DERIVATIVES_PASS')))))
        log_path.write_text('synthetic failed optimizer with passing diagnostic')
        return 2
    root,report=job.run_captured_objective(**context.args,trial_iterations=500,_process_runner=runner)
    assert report['status']==report['trial_status']=='FAILED'
    assert report['failure_endpoint_status']=='DERIVATIVES_PASS'
    assert report['execution']['returncode']==2 and not report['scientific_acceptance']
    assert report['inputs_and_sources_preserved']
    assert 'stopping_classification' not in report
    assert json.loads((root/'evaluation.json').read_text())['trial']['error']=='RuntimeError: original line-search failure'


@pytest.fixture
def guard_context(context):
    root=Path(context.owners['cif_attachment_native'].__file__).parent
    source=root/'cif_live_nonbonded_policy.py';source.write_text('# synthetic guard')
    profile=root/'data/nonbonded-native-profile.json';profile.parent.mkdir()
    profile.write_text(json.dumps({'profile_id':'synthetic-native'}))
    context.owners['cif_live_nonbonded_policy']=SimpleNamespace(__file__=str(source),
        POLICY_ID='synthetic-policy',PROFILE_ID='synthetic-native',
        snapshot_live_nonbonded_policy=lambda *a:None,require_live_nonbonded_policy=lambda *a:None)
    context.guard_source=source;context.guard_profile=profile
    return context


def guarded_result(cwd,context):
    request=json.loads((cwd/'request.json').read_bytes())
    metadata=request['live_policy_guard']
    policy={'synthetic':True}
    digest=sha256(json.dumps(policy,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    snapshot=dict(schema_version=1,policy_id=metadata['policy_id'],native_profile_id=metadata['native_profile_id'],
        policy=policy,policy_sha256=digest,cache_observations={})
    record=dict(schema_version=1,kind='topostitch-live-policy-baseline',origin='FRESH_RECONSTRUCTED_CONTEXT',
        source_model_sha256=metadata['source_model_sha256'],source_receipt_sha256=metadata['source_receipt_sha256'],snapshot=snapshot)
    (cwd/'live-policy.json').write_text(json.dumps(record))
    binding={k:snapshot[k] for k in ('policy_id','native_profile_id','policy_sha256')}
    binding.update({k:metadata[k] for k in ('owner_source_sha256','native_profile_sha256')})
    (cwd/'evaluation.json').write_text(json.dumps(dict(status='INITIAL_CONTEXT_AND_EVALUATIONS_MATCH',
        optimization=False,binding={'live_nonbonded_policy':binding})))
    (cwd/'bootstrap/native_validation.json').write_text(json.dumps(context.native))


def test_guarded_worker_stages_complete_pinned_assets_and_retains_baseline(guard_context):
    c=guard_context
    def runner(*a,cwd,log_path,**kw):
        assert (cwd/'runtime/nasolve/cif_live_nonbonded_policy.py').read_bytes()==c.guard_source.read_bytes()
        assert (cwd/'runtime/nasolve/data/nonbonded-native-profile.json').read_bytes()==c.guard_profile.read_bytes()
        worker=(cwd/'evaluate.py').read_text()
        assert worker.index('context=compare_reconstructed_context')<worker.index('snapshot_live_nonbonded_policy')
        assert worker.index('snapshot_live_nonbonded_policy')<worker.index('signature=audit.fixed_signature')
        compile(worker,'evaluate.py','exec')
        guarded_result(cwd,c);log_path.write_text('synthetic guarded process');return 0
    root,r=job.run_captured_objective(**c.args,guard_live_policy=True,_process_runner=runner)
    assert r['status']=='INITIAL_CONTEXT_AND_EVALUATIONS_MATCH' and r['inputs_and_sources_preserved']
    assert r['live_policy_guard']['baseline_verified'] is True
    assert r['live_policy_guard']['baseline']['path']=='live-policy.json'
    hashes={v['sha256'] for v in r['trusted_sources']}
    assert sha256(c.guard_source.read_bytes()).hexdigest() in hashes
    assert sha256(c.guard_profile.read_bytes()).hexdigest() in hashes


@pytest.mark.parametrize('missing',['source','profile'])
def test_requested_guard_missing_asset_refuses_before_job_allocation(guard_context,missing):
    c=guard_context;getattr(c,'guard_'+missing).unlink()
    with pytest.raises((OSError,ValueError)):
        job.run_captured_objective(**c.args,guard_live_policy=True)
    assert not c.args['output_parent'].exists() and not c.seen


@pytest.mark.parametrize('defect',['binding','baseline','digest','source','identity'])
def test_guarded_worker_cannot_claim_success_without_matching_evidence(guard_context,defect):
    c=guard_context
    def runner(*a,cwd,log_path,**kw):
        guarded_result(cwd,c)
        if defect=='binding':
            p=cwd/'evaluation.json';v=json.loads(p.read_bytes());v.pop('binding');p.write_text(json.dumps(v))
        elif defect=='baseline':(cwd/'live-policy.json').unlink()
        else:
            p=cwd/'live-policy.json';v=json.loads(p.read_bytes())
            if defect=='digest':v['snapshot']['policy']['synthetic']=False
            elif defect=='source':v['source_model_sha256']='a'*64
            else:v['snapshot']['native_profile_id']='wrong-profile'
            p.write_text(json.dumps(v))
        log_path.write_text('synthetic invalid success');return 0
    root,r=job.run_captured_objective(**c.args,guard_live_policy=True,_process_runner=runner)
    assert r['status']=='FAILED' and r['error'] and not r['live_policy_guard']['baseline_verified']
    assert (root/'receipt.json').exists()


def test_guard_profile_change_during_process_invalidates_retained_result(guard_context):
    c=guard_context
    def runner(*a,cwd,log_path,**kw):
        guarded_result(cwd,c);c.guard_profile.write_text('changed');log_path.write_text('changed source');return 0
    root,r=job.run_captured_objective(**c.args,guard_live_policy=True,_process_runner=runner)
    assert r['status']=='FAILED' and not r['inputs_and_sources_preserved']


def test_default_worker_remains_unguarded_even_with_owner_available(guard_context):
    c=guard_context
    def runner(*a,cwd,log_path,**kw):
        assert 'live_policy_guard' not in json.loads((cwd/'request.json').read_bytes())
        assert not (cwd/'runtime/nasolve/cif_live_nonbonded_policy.py').exists()
        assert (cwd/'evaluate.py').read_text()==job.WORKER
        (cwd/'evaluation.json').write_text(json.dumps(dict(status='INITIAL_CONTEXT_AND_EVALUATIONS_MATCH',optimization=False)))
        (cwd/'bootstrap/native_validation.json').write_text(json.dumps(c.native));log_path.write_text('legacy');return 0
    root,r=job.run_captured_objective(**c.args,_process_runner=runner)
    assert 'live_policy_guard' not in r


def test_guard_option_requires_boolean_before_loading_owners(monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('owner loaded')
    monkeypatch.setattr(job,'_cedar',forbidden)
    with pytest.raises(ValueError,match='boolean'):
        job.run_captured_objective('a','b','c','d','out',recipe_sha256='a'*64,mask_sha256='b'*64,
            phenix='native',guard_live_policy='yes')


@pytest.mark.parametrize('value',[[],[0.,0.],['x',0.,0.],[True,0.,0.],[float('nan'),0.,0.],
    [float('inf'),0.,0.],[0.]*1203,iter([0.,0.,0.])])
def test_explicit_trial_start_refuses_bad_vectors_before_owners(monkeypatch,value):
    def forbidden(*a,**kw):raise AssertionError('owner loaded')
    monkeypatch.setattr(job,'_cedar',forbidden)
    with pytest.raises(ValueError,match='start'):
        job.run_captured_objective('a','b','c','d','out',recipe_sha256='a'*64,mask_sha256='b'*64,
            phenix='native',trial_iterations=1,initial_displacements=value)


def test_explicit_start_requires_an_opted_in_trial_before_owners(monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('owner loaded')
    monkeypatch.setattr(job,'_cedar',forbidden)
    with pytest.raises(ValueError,match='trial'):
        job.run_captured_objective('a','b','c','d','out',recipe_sha256='a'*64,mask_sha256='b'*64,
            phenix='native',initial_displacements=[0.,0.,0.])


@pytest.mark.parametrize('value',[[0.]*6,[.4,.4,0.]])
def test_explicit_start_matches_mask_count_and_radial_bound_before_allocation(context,value):
    with pytest.raises(ValueError,match='start'):
        job.run_captured_objective(**context.args,trial_iterations=1,initial_displacements=value)
    assert not context.args['output_parent'].exists() and not context.seen


def test_explicit_trial_start_is_frozen_and_forwarded_with_guard(guard_context,monkeypatch):
    c=guard_context;start=[.1,-.1,.2]
    original=job._run
    def enter(args,*rest):
        start[0]=99.  # Changing caller data after API entry cannot change request.
        return original(args,*rest)
    monkeypatch.setattr(job,'_run',enter)
    def runner(*a,cwd,log_path,**kw):
        request=json.loads((cwd/'request.json').read_bytes())
        assert request['trial']==dict(max_iterations=1,max_calls=10,initial_displacements=[.1,-.1,.2])
        guarded_result(cwd,c)
        p=cwd/'evaluation.json';v=json.loads(p.read_bytes());v.update(status='TRIAL_REVIEW_REQUIRED',optimization=True,
            trial=dict(status='FAILED',error='original bounded failure'));p.write_text(json.dumps(v))
        log_path.write_text('failed trial retains its explicit initialization');return 2
    root,r=job.run_captured_objective(**c.args,trial_iterations=1,trial_calls=10,
        initial_displacements=start,guard_live_policy=True,_process_runner=runner)
    assert r['status']==r['trial_status']=='FAILED' and r['inputs_and_sources_preserved']
    assert json.loads((root/'request.json').read_bytes())['trial']['initial_displacements']==[.1,-.1,.2]
    assert json.loads((root/'evaluation.json').read_bytes())['trial']['error']=='original bounded failure'
