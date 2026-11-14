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
    def selected(*a):yield owners
    monkeypatch.setattr(job,'_cedar',selected);monkeypatch.setattr(job,'_worker',lambda *a:'# fresh trusted builder\n')
    args=dict(model=model,recipe=recipe,mask=mask,native_receipt=receipt,output_parent=tmp_path/'output',
        recipe_sha256=recipe_digest(packet),mask_sha256=sha256(mask.read_bytes()).hexdigest(),phenix=installation)
    return SimpleNamespace(args=args,native=native,seen=seen,OwnershipError=OwnershipError,installation=installation)


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
