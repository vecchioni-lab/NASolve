"""Generic capture binding; analytic fake SDK evidence is not chemical proof."""
from hashlib import sha256
import json,os,sys,shutil
from pathlib import Path
from types import SimpleNamespace
import pytest


def parent(tmp_path,monkeypatch,mode=None,namespace='direct'):
    from tests.test_cif_mixed_gradient import anchored_initial_parent,fake_sdk_parent
    from nasolve.cif_native_validation import _artifact,_NATIVE_WORKER
    if mode is None:base,_=anchored_initial_parent(tmp_path,monkeypatch);sdk=None
    else:base,_,sdk=fake_sdk_parent(tmp_path,monkeypatch,mode)
    from nasolve.cif_candidate_usability import native_energy_worker
    import nasolve.cif_native_validation as native_module
    monkeypatch.setattr('nasolve.cif_attachment_native._NATIVE_WORKER',native_module._NATIVE_WORKER)
    root=base/'capture';root.mkdir();(root/'inputs').mkdir();resources=[]
    for i,(role,name,suffix) in enumerate([('model','model.pdb','.pdb'),('dictionary','projected.cif','.cif'),('phil','explicit.phil','.phil')]):
        path=root/'inputs'/f'{i:03d}_{role}{suffix}';path.write_bytes((base/name).read_bytes())
        resources.append(dict(_artifact(path,root),role=role,input_index=i))
    native=json.loads((base/'saved_active.json').read_text());native.update(scientific_approval='NOT_RUN',model_editing='NOT_RUN',optimization='NOT_RUN',automatic_adoption=False,
        dictionary_loading=[{'input':resources[1]['path'],'status':'RECORDED'}],phil_adaptations=[{'input':resources[2]['path']}])
    native['geometry'].setdefault('simple_bonds',native['geometry']['proxy_details']['bond_simple']);native['geometry'].setdefault('asu_bonds',[])
    (base/'saved_active.json').write_text(json.dumps(native))
    spec={'policy_id':'cif-native-bundle-inventory-v1','model':resources[0]['path'],'dictionaries':[resources[1]['path']],
        'phil_files':[resources[2]['path']],'phil_namespace_policy':namespace,'inventory_detail':'linked','policy_inventory':True,'energy_inventory':True}
    (root/'native_spec.json').write_text(json.dumps(spec));(root/'native_worker.py').write_text(native_energy_worker(native_module._NATIVE_WORKER));(root/'native_validation.json').write_text(json.dumps(native));(root/'native.log').write_text('Explicit analytic fake SDK fixture\n')
    receipt={'schema_version':1,'audit_kind':'cif_native_bundle_inspection','policy_id':'cif-native-bundle-inventory-v1','status':'REVIEW',
        'source_preserved':True,'frozen_inputs_preserved':True,'symlink_outputs':[],'automatic_adoption':False,'scientific_approval':'NOT_RUN','optimization':'NOT_RUN',
        'model_editing':'NOT_RUN','readyset_retry':'NOT_RUN','phenix_version':'EXPLICIT_FAKE','executable_sha256':sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
        'execution':{'status':'COMPLETED','returncode':0},'inputs':resources,'outputs':[_artifact(p,root) for p in sorted(root.rglob('*')) if p.is_file()],
        'phil_namespace_policy':namespace,'dictionary_source_policy':'EXPLICIT_DICTIONARIES','native_validation':native}
    path=root/'native_receipt.json';path.write_text(json.dumps(receipt))
    phenix=SimpleNamespace(executables={'phenix.python':sys.executable},version='EXPLICIT_FAKE',environment={**os.environ,'PYTHONPATH':str(sdk),'EXPLICIT_FAKE_NATIVE':str(base/'saved_active.json')})
    return path,phenix,sdk


@pytest.mark.parametrize('namespace',['direct','refinement-root-to-interpreter-v1'])
def test_authentic_capture_prepares_without_code_or_historical_lineage_and_relocates(tmp_path,monkeypatch,namespace):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients,read_captured_mixed_gradients
    from tests.test_cif_catalogue import snapshot
    receipt,_,_=parent(tmp_path,monkeypatch,namespace=namespace);before=snapshot(receipt.parent);out=tmp_path/'audit'
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Preparation/replay launched native work'))
    q=audit_captured_mixed_gradients(receipt,None,out)
    assert q['status']=='PREPARED_ONLY' and q['qualification']=={'status':'NOT_RUN'} and not q['automatic_adoption']
    assert q['source_chemical_findings']=='NOT_ESTABLISHED_BY_NUMERICAL_CAPTURE'
    assert q['policy_authority']=='CAPTURED_EXPLICIT_POLICY'
    assert json.loads((out/'job/native_spec.json').read_text())['phil_namespace_policy']==namespace
    assert before==snapshot(receipt.parent)
    moved=out.rename(tmp_path/'moved');shutil.rmtree(receipt.parent)
    assert read_captured_mixed_gradients(moved)==q


@pytest.mark.parametrize('seconds',[True,0,-1,601,1.5])
def test_invalid_deadline_precedes_any_capture_read(tmp_path,seconds):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients
    with pytest.raises(ValueError):audit_captured_mixed_gradients(tmp_path/'missing',None,tmp_path/'out',timeout_seconds=seconds)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('mode',['correct','manager','timeout'])
def test_fresh_job_and_saved_numerics_use_unchanged_worker(tmp_path,monkeypatch,mode):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients,read_captured_mixed_gradients
    receipt,phenix,sdk=parent(tmp_path,monkeypatch,mode);out=tmp_path/'audit'
    q=audit_captured_mixed_gradients(receipt,phenix,out,timeout_seconds=1 if mode=='timeout' else 30)
    assert q['execution']['status']=={'correct':'COMPLETED','manager':'FAILED','timeout':'TIMED_OUT'}[mode]
    assert q['status']==('CAPTURED_MIXED_DERIVATIVES_PASS' if mode=='correct' else 'REVIEW'),q.get('error')
    assert q['new_native_calls']==1 and q['model_optimization']=='NOT_RUN'
    assert not list(tmp_path.rglob('fake_optimizer_called'))
    moved=out.rename(tmp_path/'moved');shutil.rmtree(receipt.parent);shutil.rmtree(sdk)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Replay launched native work'))
    assert read_captured_mixed_gradients(moved)==q
    with pytest.raises(ValueError):audit_captured_mixed_gradients(moved/'capture/native_receipt.json',None,moved)


@pytest.mark.parametrize('defect',['worker','core','input','spec','plan','capture','adoption','science','calls','status','extra','empty','bound_extra','bound_empty','duplicate_key','incomplete'])
def test_rehashed_preparation_forgery_is_refused(tmp_path,monkeypatch,defect):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients,read_captured_mixed_gradients,REPORT
    from nasolve.cif_mixed_gradient import _ref
    receipt,_,_=parent(tmp_path,monkeypatch);out=tmp_path/'audit';q=audit_captured_mixed_gradients(receipt,None,out)
    names={'worker':'job/gradient_worker.py','core':'job/correction_core.py','input':'job/inputs/000_model.pdb','spec':'job/native_spec.json','plan':'initial_probe_plan.json','capture':'capture/native.log'}
    if defect in names:
        p=out/names[defect];p.write_bytes(p.read_bytes()+b'\n')
    elif defect=='adoption':q['automatic_adoption']=True
    elif defect=='science':q['source_chemical_findings']='APPROVED'
    elif defect=='calls':q['new_native_calls']=True
    elif defect=='status':q['status']='CAPTURED_MIXED_DERIVATIVES_PASS'
    elif defect=='extra':(out/'extra').write_text('unbound')
    elif defect in {'empty','bound_empty'}:(out/'empty').mkdir()
    elif defect=='bound_extra':(out/'extra').write_text('unbound')
    q['outputs']=[_ref(out/r['path'],out) for r in q['outputs']]
    if defect=='bound_extra':q['outputs'].append(_ref(out/'extra',out))
    if defect=='bound_empty':q['directories'].append('empty');q['directories'].sort()
    (out/REPORT).write_text(json.dumps(q))
    if defect=='duplicate_key':(out/REPORT).write_text(json.dumps(q).replace('{','{"schema_version":1,',1))
    if defect=='incomplete':(out/REPORT).unlink()
    with pytest.raises((ValueError,FileNotFoundError)):read_captured_mixed_gradients(out)


@pytest.mark.parametrize('defect',['energy','sample','plane','sources','coordinates','qualification','executable','version'])
def test_completed_evidence_is_recomputed_after_rehash(tmp_path,monkeypatch,defect):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients,read_captured_mixed_gradients,REPORT
    from nasolve.cif_mixed_gradient import _ref
    receipt,phenix,_=parent(tmp_path,monkeypatch,'correct');out=tmp_path/'audit';q=audit_captured_mixed_gradients(receipt,phenix,out,timeout_seconds=30)
    assert q['status']=='CAPTURED_MIXED_DERIVATIVES_PASS'
    p=out/'job/gradient_result.json';v=json.loads(p.read_text())
    if defect=='energy':v['raw_snapshot']['target']+=1
    if defect=='sample':v['gradient_audit']['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1
    if defect=='plane':v['plane_order_audit']['order_safe_qualified']=False
    if defect=='sources':v['installed_numeric_sources_after'][0]['sha256']='0'*64
    if defect=='coordinates':v['coordinates_unchanged']=False
    if defect=='qualification':q['qualification']={'status':'NOT_RUN'};q['status']='REVIEW'
    if defect=='executable':q['executable_sha256']='0'*64
    if defect=='version':q['phenix_version']='different'
    p.write_text(json.dumps(v));q['outputs']=[_ref(out/r['path'],out) for r in q['outputs']];(out/REPORT).write_text(json.dumps(q))
    with pytest.raises(ValueError):read_captured_mixed_gradients(out)


def test_changed_capture_and_consumer_refuse_before_attempt(tmp_path,monkeypatch):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients
    receipt,phenix,_=parent(tmp_path,monkeypatch);phenix.version='different'
    with pytest.raises(ValueError):audit_captured_mixed_gradients(receipt,phenix,tmp_path/'out')
    assert not (tmp_path/'out').exists()
    (receipt.parent/'native.log').write_text('changed')
    with pytest.raises(ValueError):audit_captured_mixed_gradients(receipt,None,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_launch_failure_is_preserved_and_cannot_be_retried_in_place(tmp_path,monkeypatch):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients,read_captured_mixed_gradients
    receipt,phenix,_=parent(tmp_path,monkeypatch);out=tmp_path/'audit'
    def fail(*a,**k):raise OSError('explicit launch refusal')
    monkeypatch.setattr('subprocess.Popen',fail)
    q=audit_captured_mixed_gradients(receipt,phenix,out)
    assert q['status']=='REVIEW' and q['execution']['status']=='LAUNCH_FAILED'
    assert q['new_native_calls']==0 and (out/'job/gradient.log').is_file()
    assert read_captured_mixed_gradients(out)==q
    with pytest.raises(ValueError):audit_captured_mixed_gradients(receipt,phenix,out)


def test_ineligible_policy_refuses_before_reserving_output(tmp_path,monkeypatch):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients
    from nasolve.cif_native_validation import _artifact
    receipt,_,_=parent(tmp_path,monkeypatch);root=receipt.parent
    r=json.loads(receipt.read_text());native=r['native_validation'];native['restraint_policy']['secondary_structure_enabled']=True
    (root/'native_validation.json').write_text(json.dumps(native))
    r['outputs']=[_artifact(root/x['path'],root) for x in r['outputs']];receipt.write_text(json.dumps(r))
    with pytest.raises(ValueError):audit_captured_mixed_gradients(receipt,None,tmp_path/'out')
    assert not (tmp_path/'out').exists()


# Analytic SDK controls exercise absent-family bookkeeping, not chemistry.
def zero_parent(tmp_path, monkeypatch, namespace='direct'):
    from copy import deepcopy
    from math import fsum, sqrt
    from nasolve.cif_native_validation import _artifact
    receipt, phenix, sdk = parent(tmp_path, monkeypatch, 'correct', namespace)
    manager = sdk/'cctbx/geometry_restraints/manager.py'
    manager.write_text(''.join('    parallelity_proxies=gr.shared_parallelity_proxy([])\n'
        if line.startswith('    parallelity_proxies=') else line for line in manager.read_text().splitlines(keepends=True)))
    r = json.loads(receipt.read_text()); native = r['native_validation']
    native['geometry']['proxy_details']['parallelity'] = []
    native['geometry']['proxy_counts']['parallelity'] = 0
    for row in native['energy_inventory']['installed_sources']:
        if row['module'] == 'cctbx.geometry_restraints.manager':row['sha256'] = sha256(manager.read_bytes()).hexdigest()
    points = native['geometry']['sites_cart_exact']; gradient = [12.*x for p in points for x in p]
    raw = {'target':6*sum(v*v for p in points for v in p), 'gradient':gradient,
        'gradient_norm':sqrt(fsum(x*x for x in gradient)),
        'terms':{'parallelity_residual_sum':0.}, 'proxy_counts':{'n_parallelity_proxies':0}}
    native['energy_inventory']['snapshots'] = [raw, deepcopy(raw)]
    Path(phenix.environment['EXPLICIT_FAKE_NATIVE']).write_text(json.dumps(native))
    (receipt.parent/'native_validation.json').write_text(json.dumps(native))
    r['outputs'] = [_artifact(receipt.parent/x['path'], receipt.parent) for x in r['outputs']]
    receipt.write_text(json.dumps(r))
    return receipt, phenix, sdk


@pytest.mark.parametrize('namespace', ['direct', 'refinement-root-to-interpreter-v1'])
def test_absent_parallelity_qualifies_actual_families_and_replays_cold(tmp_path, monkeypatch, namespace):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients, read_captured_mixed_gradients
    from tests.test_cif_catalogue import snapshot
    receipt, phenix, sdk = zero_parent(tmp_path, monkeypatch, namespace)
    before = snapshot(receipt.parent); out = tmp_path/'audit'
    q = audit_captured_mixed_gradients(receipt, phenix, out, timeout_seconds=30)
    assert q['status'] == 'CAPTURED_MIXED_DERIVATIVES_PASS', q.get('error')
    result = json.loads((out/'job/gradient_result.json').read_text())
    assert result['policy_id'] == 'cif-captured-zero-parallelity-gradient-v1'
    assert result['plane_order_audit']['status'] == 'NOT_APPLICABLE'
    assert result['plane_order_audit']['evaluation_pairs'] == 0
    assert result['native_parallelity_proxies'] == []
    assert set(result['gradient_audit']['cases']['initial']['families']) == {
        'all', 'bond', 'angle', 'dihedral', 'chirality', 'planarity', 'parallelity', 'nonbonded'}
    assert before == snapshot(receipt.parent)
    moved = out.rename(tmp_path/'moved'); shutil.rmtree(receipt.parent); shutil.rmtree(sdk)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k:pytest.fail('Reader executed a job'))
    unchanged = snapshot(moved)
    assert read_captured_mixed_gradients(moved) == q
    assert snapshot(moved) == unchanged


@pytest.mark.parametrize('defect', ['count', 'energy_count', 'energy_target', 'unfulfilled_request'])
def test_absent_parallelity_refuses_contradictory_native_evidence_before_reservation(tmp_path, monkeypatch, defect):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients
    from nasolve.cif_native_validation import _artifact
    receipt, _, _ = zero_parent(tmp_path, monkeypatch)
    r = json.loads(receipt.read_text()); native = r['native_validation']
    if defect == 'count':native['geometry']['proxy_counts']['parallelity'] = 1
    if defect == 'unfulfilled_request':native['geometry']['custom_proxy_requests'] = [{'kind':'parallelity', 'action':'add'}]
    for raw in native['energy_inventory']['snapshots']:
        if defect == 'energy_count':raw['proxy_counts']['n_parallelity_proxies'] = 1
        if defect == 'energy_target':raw['terms']['parallelity_residual_sum'] = 0.1
    (receipt.parent/'native_validation.json').write_text(json.dumps(native))
    r['outputs'] = [_artifact(receipt.parent/x['path'], receipt.parent) for x in r['outputs']]
    receipt.write_text(json.dumps(r))
    with pytest.raises(ValueError):audit_captured_mixed_gradients(receipt, None, tmp_path/'audit')
    assert not (tmp_path/'audit').exists()


@pytest.mark.parametrize('defect', ['policy', 'absent_claim', 'plane_count', 'sample', 'family_target', 'family_gradient', 'all_count', 'correction', 'worker', 'dihedral_sample'])
def test_absent_parallelity_rehashed_evidence_cannot_bypass_derivative_checks(tmp_path, monkeypatch, defect):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients, read_captured_mixed_gradients, REPORT
    from nasolve.cif_mixed_gradient import _ref
    receipt, phenix, _ = zero_parent(tmp_path, monkeypatch); out = tmp_path/'audit'
    q = audit_captured_mixed_gradients(receipt, phenix, out, timeout_seconds=30)
    assert q['status'] == 'CAPTURED_MIXED_DERIVATIVES_PASS'
    path = out/'job/gradient_result.json'; r = json.loads(path.read_text())
    family = r['gradient_audit']['cases']['initial']['families']['parallelity']
    if defect == 'policy':r['policy_id'] = 'cif-mixed-initial-native-gradient-v1'
    elif defect == 'absent_claim':r['plane_order_audit']['status'] = 'PASS'
    elif defect == 'plane_count':r['native_parallelity_proxies'] = [{'i_seqs':[0, 1, 2]}]
    elif defect == 'sample':family['directions'][0]['samples'][0]['plus_target'] += .1
    elif defect == 'dihedral_sample':r['gradient_audit']['cases']['initial']['families']['dihedral']['directions'][0]['samples'][0]['plus_target'] += .1
    elif defect == 'family_target':r['baseline_evaluations']['parallelity'][0]['target'] = .1
    elif defect == 'family_gradient':r['baseline_evaluations']['parallelity'][0]['gradient'][0] = .1
    elif defect == 'all_count':r['baseline_evaluations']['all'][0]['proxy_counts']['n_parallelity_proxies'] = 1
    elif defect == 'correction':r['correction_statistics']['max_plane_residual_difference'] = .1
    elif defect == 'worker':
        worker = out/'job/gradient_worker.py'; worker.write_text(worker.read_text()+'\n# changed\n')
    path.write_text(json.dumps(r)); q['outputs'] = [_ref(out/r['path'], out) for r in q['outputs']]
    (out/REPORT).write_text(json.dumps(q))
    with pytest.raises(ValueError):read_captured_mixed_gradients(out)


def test_zero_context_does_not_grant_legacy_geometry_trial_qualification(tmp_path, monkeypatch):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients
    from nasolve.cif_captured_geometry_trial import trial_captured_geometry
    receipt, phenix, _ = zero_parent(tmp_path, monkeypatch); gradient = tmp_path/'gradient'
    result = audit_captured_mixed_gradients(receipt, phenix, gradient, timeout_seconds=30)
    assert result['status'] == 'CAPTURED_MIXED_DERIVATIVES_PASS'
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k:pytest.fail('Unqualified optimizer launched'))
    with pytest.raises(ValueError):trial_captured_geometry(gradient, None, tmp_path/'geometry')
    assert not (tmp_path/'geometry').exists()


def test_absent_parallelity_preparation_is_read_only_and_not_qualification(tmp_path, monkeypatch):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients, read_captured_mixed_gradients
    receipt, _, _ = zero_parent(tmp_path, monkeypatch)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k:pytest.fail('Preparation executed native code'))
    out = tmp_path/'audit'; report = audit_captured_mixed_gradients(receipt, None, out)
    assert report['status']=='PREPARED_ONLY' and report['qualification']=={'status':'NOT_RUN'}
    assert report['preparation']['required_plane_pairs']==0
    assert read_captured_mixed_gradients(out)==report


@pytest.mark.parametrize('defect', ['gradient', 'counts'])
def test_absent_parallelity_cannot_change_captured_full_gradient_or_counts(tmp_path, monkeypatch, defect):
    from copy import deepcopy
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients
    from nasolve.cif_zero_parallelity_gradients import _validate_result
    receipt, phenix, _ = zero_parent(tmp_path, monkeypatch); out = tmp_path/'audit'
    report = audit_captured_mixed_gradients(receipt, phenix, out, timeout_seconds=30)
    assert report['status']=='CAPTURED_MIXED_DERIVATIVES_PASS'
    result = json.loads((out/'job/gradient_result.json').read_text())
    expected = json.loads((out/'job/native_validation.json').read_text())
    for raw in expected['energy_inventory']['snapshots']:
        if defect=='gradient':raw['gradient'][0] += 0.1
        else:raw['proxy_counts']['n_bond_proxies'] = 1
    result['raw_snapshot'] = deepcopy(expected['energy_inventory']['snapshots'][0])
    with pytest.raises(ValueError):_validate_result(result, expected, result['selected_indices'])


@pytest.mark.parametrize('defect',['unbound-file','qualification','rehashed-sample','rehashed-sources'])
def test_warm_numerical_reuse_still_rechecks_every_saved_artifact(tmp_path,monkeypatch,defect):
    from nasolve.cif_captured_mixed_gradients import audit_captured_mixed_gradients,read_captured_mixed_gradients,REPORT
    from nasolve.cif_numerical_replay import numerical_replay_scope
    from nasolve import cif_mixed_gradient as numerical
    receipt,phenix,_=parent(tmp_path,monkeypatch,'correct');out=tmp_path/'audit'
    q=audit_captured_mixed_gradients(receipt,phenix,out,timeout_seconds=30)
    assert q['status']=='CAPTURED_MIXED_DERIVATIVES_PASS'
    original=numerical._validate_result;calls=[]
    def counted(*args):calls.append(1);return original(*args)
    monkeypatch.setattr(numerical,'_validate_result',counted)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Read launched native work'))
    with numerical_replay_scope():
        assert read_captured_mixed_gradients(out)==q
        assert read_captured_mixed_gradients(out)==q
        assert len(calls)==1
        if defect=='unbound-file':(out/'capture/native.log').write_text('changed after successful read')
        else:
            path=out/('qualification.json' if defect=='qualification' else 'job/gradient_result.json')
            value=json.loads(path.read_text())
            if defect=='qualification':value['checks']['unchanged_native_energy']=False
            elif defect=='rehashed-sample':value['gradient_audit']['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1.
            else:value['installed_numeric_sources_after'][0]['sha256']='0'*64
            path.write_text(json.dumps(value))
            q['outputs']=[numerical._ref(out/row['path'],out) for row in q['outputs']]
            (out/REPORT).write_text(json.dumps(q))
        with pytest.raises(ValueError):read_captured_mixed_gradients(out)
