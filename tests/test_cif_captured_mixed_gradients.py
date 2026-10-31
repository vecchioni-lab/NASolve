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
