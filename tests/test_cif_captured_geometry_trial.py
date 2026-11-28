"""Captured numerical proof grants mechanics, never chemical approval."""
from pathlib import Path
import json,shutil
import pytest


def parent(tmp_path,monkeypatch,optimizer='limit'):
    from tests.test_cif_mixed_geometry import qualified_gradient_parent
    from tests.test_cif_captured_mixed_gradients import parent as capture_parent
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients
    _,context,linked,sdk,_=qualified_gradient_parent(tmp_path,monkeypatch,optimizer=optimizer)
    monkeypatch.setattr('tests.test_cif_mixed_gradient.fake_sdk_parent',lambda *a:(context,linked,sdk))
    lbfgs=sdk/'scitbx/lbfgs.py';lbfgs.write_text(lbfgs.read_text().replace("Path('fake_optimizer_called')",'Path('+repr(str(sdk/'fake_optimizer_called'))+')'))
    receipt,phenix,_=capture_parent(tmp_path,monkeypatch,'correct')
    gradient=tmp_path/'captured-gradient';q=audit_captured_mixed_gradients(receipt,phenix,gradient,timeout_seconds=30)
    assert q['status']=='CAPTURED_MIXED_DERIVATIVES_PASS'
    return gradient,phenix,sdk


@pytest.mark.parametrize('changes',[{'max_iterations':v} for v in [0,1001,True,1.5]]+[{'timeout_seconds':v} for v in [0,601,True,1.5]])
def test_bounds_precede_input_reads(tmp_path,changes):
    from nasolve.cif_captured_geometry_trial import trial_captured_geometry
    with pytest.raises(ValueError):trial_captured_geometry(tmp_path/'missing',None,tmp_path/'out',**changes)
    assert not (tmp_path/'out').exists()


def test_preparation_is_self_contained_and_cannot_promote_input_chemistry(tmp_path,monkeypatch):
    from nasolve.cif_captured_geometry_trial import trial_captured_geometry,read_captured_geometry_trial
    gradient,_,sdk=parent(tmp_path,monkeypatch);before={p:p.read_bytes() for p in gradient.rglob('*') if p.is_file()}
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Preparation/read launched'))
    out=tmp_path/'trial';q=trial_captured_geometry(gradient,None,out)
    assert q['status']=='PREPARED_ONLY' and q['new_native_calls']==0
    assert q['coordinate_decision']['selected']=='INPUT_MODEL_UNCHANGED'
    assert q['coordinate_decision']['input_usability']=='NOT_ESTABLISHED_BY_NUMERICAL_CAPTURE'
    assert q['policy_authority']=='CAPTURED_EXPLICIT_POLICY' and q['source_chemical_findings']=='NOT_ESTABLISHED_BY_NUMERICAL_CAPTURE'
    assert q['coordinate_scope']=='ALL_CAPTURED_ATOMS_VARIABLE' and not q['automatic_adoption']
    assert json.loads((out/'job/native_spec.json').read_text())['phil_namespace_policy']=='direct'
    assert all(p.read_bytes()==v for p,v in before.items())
    moved=out.rename(tmp_path/'moved');shutil.rmtree(gradient);shutil.rmtree(sdk)
    assert read_captured_geometry_trial(moved)==q


@pytest.mark.parametrize('mode',['limit','manager','timeout'])
def test_unchanged_worker_yields_mechanics_or_preserved_failure(tmp_path,monkeypatch,mode):
    from nasolve.cif_captured_geometry_trial import trial_captured_geometry,read_captured_geometry_trial
    from nasolve.cif_fixed_geometry import _GEOMETRY_WORKER
    gradient,phenix,sdk=parent(tmp_path,monkeypatch,'timeout' if mode=='timeout' else 'limit')
    if mode=='manager':phenix.environment['EXPLICIT_C90_MISMATCH']='1'
    out=tmp_path/'trial';q=trial_captured_geometry(gradient,phenix,out,max_iterations=5,timeout_seconds=1 if mode=='timeout' else 30)
    assert q['execution']['status']=={'limit':'COMPLETED','manager':'FAILED','timeout':'TIMED_OUT'}[mode]
    assert q['status']==('CAPTURED_GEOMETRY_MECHANICS_PASS' if mode=='limit' else 'REVIEW'),q.get('optional_trial_finding')
    assert q['new_native_calls']==(2 if mode=='limit' else 1)
    assert (out/'job/geometry_worker.py').read_text()==_GEOMETRY_WORKER
    assert q['coordinate_decision']['candidate_mechanics_pass'] is (mode=='limit')
    assert q['coordinate_decision']['selected']=='INPUT_MODEL_UNCHANGED' and not q['automatic_adoption']
    assert q['coordinate_decision']['chemical_qualification']=='NOT_ASSESSED'
    moved=out.rename(tmp_path/'moved');shutil.rmtree(gradient);shutil.rmtree(sdk)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Saved read launched'))
    assert read_captured_geometry_trial(moved)==q
    with pytest.raises(ValueError):trial_captured_geometry(moved/'gradient',None,moved)


@pytest.mark.parametrize('defect',['worker','dictionary','proof','namespace','decision','chemistry','adoption','digest','extra','empty','bound_extra'])
def test_rehashed_recipe_and_scope_changes_are_refused(tmp_path,monkeypatch,defect):
    from nasolve.cif_captured_geometry_trial import trial_captured_geometry,read_captured_geometry_trial,REPORT
    from nasolve.cif_mixed_geometry import _ref
    gradient,_,_=parent(tmp_path,monkeypatch);out=tmp_path/'trial';q=trial_captured_geometry(gradient,None,out)
    names={'worker':'job/geometry_worker.py','dictionary':q['preparation']['inputs'][1]['artifact']['path'],'proof':'job/mixed_initial_result.json','namespace':'job/native_spec.json'}
    if defect in names:p=out/names[defect];p.write_bytes(p.read_bytes()+b' ')
    if defect=='decision':q['coordinate_decision']['selected']='ADOPT_ENDPOINT'
    if defect=='chemistry':q['source_chemical_findings']='APPROVED'
    if defect=='adoption':q['automatic_adoption']=True
    if defect=='digest':q['gradient_report_sha256']='0'*64
    if defect=='extra':(out/'extra').write_text('unbound')
    if defect=='empty':(out/'empty').mkdir();q['directories'].append('empty');q['directories'].sort()
    q['outputs']=[_ref(out/r['path'],out) for r in q['outputs']]
    if defect=='bound_extra':(out/'extra').write_text('unbound');q['outputs'].append(_ref(out/'extra',out))
    (out/REPORT).write_text(json.dumps(q))
    with pytest.raises(ValueError):read_captured_geometry_trial(out)


@pytest.mark.parametrize('defect',['sample','candidate','mechanics','readback','manager','version','calls','installed_source'])
def test_rehashed_completed_evidence_is_recomputed(tmp_path,monkeypatch,defect):
    from nasolve.cif_captured_geometry_trial import trial_captured_geometry,read_captured_geometry_trial,REPORT
    from nasolve.cif_mixed_geometry import _ref
    gradient,phenix,_=parent(tmp_path,monkeypatch);out=tmp_path/'trial';q=trial_captured_geometry(gradient,phenix,out,max_iterations=5,timeout_seconds=30)
    assert q['status']=='CAPTURED_GEOMETRY_MECHANICS_PASS',q.get('optional_trial_finding')
    if defect=='sample':
        p=out/'job/geometry_result.json';v=json.loads(p.read_text());v['endpoint_gradient_audit']['cases']['full_precision']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1;p.write_text(json.dumps(v))
    if defect=='candidate':p=out/'candidate/mixed_geometry_model.pdb';p.write_bytes(p.read_bytes()+b'CHANGED')
    if defect=='mechanics':p=out/'native_mechanics.json';v=json.loads(p.read_text());v['mechanics_checks_pass']=False;p.write_text(json.dumps(v))
    if defect=='readback':
        p=out/q['native_readback']['receipt']['path'];v=json.loads(p.read_text());v['executable_sha256']='0'*64;p.write_text(json.dumps(v));q['native_readback']['receipt']=_ref(p,out)
    if defect=='manager':p=out/'job/native_validation.json';v=json.loads(p.read_text());v['atoms'][0]['atom_id']='CHANGED';p.write_text(json.dumps(v))
    if defect=='installed_source':p=out/'job/installed_source/parallelity.h';p.write_bytes(p.read_bytes()+b'changed')
    if defect=='version':q['phenix_version']='different'
    if defect=='calls':q['new_native_calls']=1
    q['outputs']=[_ref(out/r['path'],out) for r in q['outputs']];(out/REPORT).write_text(json.dumps(q))
    with pytest.raises(ValueError):read_captured_geometry_trial(out)


def test_launch_failure_has_no_usable_input_claim_and_preserves_attempt(tmp_path,monkeypatch):
    from nasolve.cif_captured_geometry_trial import trial_captured_geometry,read_captured_geometry_trial
    gradient,phenix,_=parent(tmp_path,monkeypatch)
    def fail(*a,**k):raise OSError('explicit launch refusal')
    monkeypatch.setattr('subprocess.Popen',fail);out=tmp_path/'trial'
    q=trial_captured_geometry(gradient,phenix,out)
    assert q['execution']['status']=='LAUNCH_FAILED' and q['new_native_calls']==0
    assert q['coordinate_decision']['selected']=='INPUT_MODEL_UNCHANGED'
    assert q['coordinate_decision']['input_usability']=='NOT_ESTABLISHED_BY_NUMERICAL_CAPTURE'
    assert read_captured_geometry_trial(out)==q
    with pytest.raises(ValueError):trial_captured_geometry(gradient,phenix,out)


@pytest.mark.parametrize('defect',['consumer','gradient_evidence'])
def test_unqualified_binding_refuses_before_output_reservation(tmp_path,monkeypatch,defect):
    from nasolve.cif_captured_geometry_trial import trial_captured_geometry
    gradient,phenix,_=parent(tmp_path,monkeypatch)
    if defect=='consumer':phenix.version='changed'
    else:(gradient/'job/gradient_result.json').write_text('{}')
    with pytest.raises(ValueError):trial_captured_geometry(gradient,phenix,tmp_path/'out')
    assert not (tmp_path/'out').exists()
