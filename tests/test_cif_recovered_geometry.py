"""A repaired objective needs a fresh, bounded geometry attempt."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import pytest
from nasolve.cif_recovered_geometry import trial_recovered_geometry, read_recovered_geometry


def qualified_parent(tmp_path, monkeypatch, *, optimizer='limit'):
    from tests.test_cif_mixed_geometry import qualified_gradient_parent
    from nasolve.cif_mixed_source_recovery import _ref
    from nasolve.cif_recovered_gradient import audit_recovered_gradients
    _, parent, _, sdk, phenix = qualified_gradient_parent(tmp_path, monkeypatch, optimizer=optimizer)
    capture = parent/'active_receipt.json'
    capture.write_text(json.dumps({'native_validation': json.loads((parent/'saved_active.json').read_bytes()),
        'phenix_version': phenix.version, 'executable_sha256': sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()}))
    capsule = parent/'capsules/endpoint.zip'; capsule.parent.mkdir(); capsule.write_bytes(b'EXPLICIT_FAKE_PARENT_CAPSULE')
    source = {'status': 'MIXED_SOURCE_RECOVERY_MECHANICS_PASS', 'qualification': {'mechanics_checks_pass': True},
        'inputs': {'resources': [{'role': 'model', 'artifact': _ref(parent/'model.pdb', parent)}],
                   'active_policy': _ref(parent/'explicit.phil', parent)},
        'bundle': {'native_dictionaries': [_ref(parent/'projected.cif', parent)], 'context_phils': []},
        'native_captures': {'linked': {'active': _ref(capture, parent)}},
        'specification': {'endpoint_sha256': sha256(capsule.read_bytes()).hexdigest()},
        'outputs': [_ref(capsule, parent)], 'model_preserved': True, 'source_inputs_preserved': True, 'automatic_adoption': False}
    (parent/'mixed_source_recovery.json').write_text(json.dumps(source))
    monkeypatch.setattr('nasolve.cif_mixed_source_recovery.read_mixed_source_recovery',
        lambda p: json.loads((Path(p)/'mixed_source_recovery.json').read_bytes()))
    gradient = tmp_path/'c99'
    report = audit_recovered_gradients(parent, phenix, gradient, timeout_seconds=30)
    assert report['status'] == 'RECOVERED_MIXED_DERIVATIVES_PASS'
    return gradient, parent, sdk, phenix


@pytest.mark.parametrize('changes', [{'max_iterations': v} for v in [0,1001,True,1.5]]+
                         [{'timeout_seconds': v} for v in [0,601,True,1.5]])
def test_bounds_precede_parent_access_and_output_creation(tmp_path, changes):
    with pytest.raises(ValueError): trial_recovered_geometry(tmp_path/'missing', tmp_path/'also_missing', None, tmp_path/'out', **changes)
    assert not (tmp_path/'out').exists()


def test_prepared_repaired_trial_never_inherits_endpoint_pass_and_relocates(tmp_path, monkeypatch):
    gradient, parent, sdk, _ = qualified_parent(tmp_path, monkeypatch)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **kw: pytest.fail('Preparation launched a process'))
    out = tmp_path/'geometry'; report = trial_recovered_geometry(gradient, parent, None, out)
    assert report['status'] == 'PREPARED_ONLY' and report['new_native_calls'] == 0
    assert report['coordinate_decision']['selected'] == 'verified_recovered_model'
    assert report['model_optimization'] == 'NOT_RUN' and not report['automatic_adoption']
    moved = tmp_path/'moved'; moved.mkdir()
    for name, path in [('gradient',gradient),('recovery',parent),('geometry',out)]: path.rename(moved/name)
    import shutil
    shutil.rmtree(sdk)
    assert read_recovered_geometry(moved/'geometry', gradient_directory=moved/'gradient', recovery_directory=moved/'recovery') == report


@pytest.mark.parametrize('mode', ['limit', 'manager', 'timeout'])
def test_unchanged_worker_retains_usable_recovered_start_or_qualified_endpoint(tmp_path, monkeypatch, mode):
    from nasolve.cif_fixed_geometry import _GEOMETRY_WORKER
    gradient, parent, sdk, phenix = qualified_parent(tmp_path, monkeypatch,
        optimizer='timeout' if mode == 'timeout' else 'limit')
    if mode == 'manager': phenix.environment['EXPLICIT_C90_MISMATCH'] = '1'
    before = {p: p.read_bytes() for r in [parent,gradient] for p in r.rglob('*') if p.is_file()}
    out = tmp_path/'geometry'; report = trial_recovered_geometry(gradient, parent, phenix, out,
        max_iterations=5, timeout_seconds=1 if mode == 'timeout' else 30)
    assert (out/'job/geometry_worker.py').read_text() == _GEOMETRY_WORKER
    assert report['new_native_calls'] == (2 if mode == 'limit' else 1)
    assert report['status'] == ('RECOVERED_GEOMETRY_ENDPOINT_PASS' if mode == 'limit' else 'REVIEW'),report.get('optional_trial_finding')
    assert report['coordinate_decision']['selected'] == ('qualified_geometry_endpoint' if mode == 'limit' else 'verified_recovered_model')
    assert report['execution']['status'] == {'limit':'COMPLETED','manager':'FAILED','timeout':'TIMED_OUT'}[mode]
    assert report['coordinate_decision']['continue_solving'] and not report['requires_cif_review'] and not report['automatic_adoption']
    assert all(p.read_bytes() == data for p,data in before.items())
    assert read_recovered_geometry(out, gradient_directory=gradient, recovery_directory=parent) == report
    if mode == 'limit':
        assert report['geometry_summary']['stopping_classification'] == 'NOT_CONVERGED_LIMIT'
        assert report['geometry_summary']['final_target'] < report['geometry_summary']['initial_target']
        moved = tmp_path/'moved'; moved.mkdir()
        for name,path in [('gradient',gradient),('recovery',parent),('geometry',out)]:path.rename(moved/name)
        import shutil
        shutil.rmtree(sdk)
        monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('Reader launched a process'))
        assert read_recovered_geometry(moved/'geometry', gradient_directory=moved/'gradient', recovery_directory=moved/'recovery') == report
    else:
        assert not (out/'candidate/mixed_geometry_model.pdb').exists()
        with pytest.raises(ValueError): trial_recovered_geometry(gradient,parent,None,out)


def test_launch_failure_retains_verified_recovery_without_a_native_call(tmp_path, monkeypatch):
    gradient,parent,_,phenix=qualified_parent(tmp_path,monkeypatch)
    def fail(*a,**k):raise OSError('EXPLICIT_FAKE_LAUNCH_FAILURE')
    monkeypatch.setattr('subprocess.Popen',fail)
    report=trial_recovered_geometry(gradient,parent,phenix,tmp_path/'out')
    assert report['status']=='REVIEW' and report['new_native_calls']==0
    assert report['execution']['status']=='LAUNCH_FAILED'
    assert report['coordinate_decision']['selected']=='verified_recovered_model'
    assert read_recovered_geometry(tmp_path/'out',gradient_directory=gradient,recovery_directory=parent)==report


@pytest.mark.parametrize('defect',['version','executable','gradient_pass','gradient_sample','parent_capsule'])
def test_unqualified_parent_or_consumer_cannot_start_an_attempt(tmp_path,monkeypatch,defect):
    gradient,parent,_,phenix=qualified_parent(tmp_path,monkeypatch)
    if defect=='version':phenix.version='CHANGED'
    elif defect=='executable':phenix.executables['phenix.python']=str(parent/'projected.cif')
    elif defect in {'gradient_pass','gradient_sample'}:
        from nasolve.cif_recovered_gradient import REPORT
        if defect=='gradient_pass':
            path=gradient/REPORT;v=json.loads(path.read_bytes());v['status']='REVIEW';path.write_text(json.dumps(v))
        else:
            path=gradient/'job/gradient_result.json';v=json.loads(path.read_bytes())
            v['gradient_audit']['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1
            path.write_text(json.dumps(v))
    else:(parent/'capsules/endpoint.zip').write_bytes(b'CHANGED')
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Unqualified inputs launched'))
    with pytest.raises(ValueError):trial_recovered_geometry(gradient,parent,phenix,tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('defect',['worker','shim','dictionary','proof','spec','decision','archive','scope','adoption','max_calls','extra'])
def test_prepared_reader_rejects_rebound_recipe_and_scope_changes(tmp_path,monkeypatch,defect):
    from nasolve.cif_recovered_geometry import REPORT
    from nasolve.cif_mixed_geometry import _ref
    gradient,parent,_,_=qualified_parent(tmp_path,monkeypatch);out=tmp_path/'out'
    report=trial_recovered_geometry(gradient,parent,None,out)
    paths={'worker':'job/geometry_worker.py','shim':'job/corrected_geometry_core.py',
           'dictionary':report['preparation']['inputs'][1]['artifact']['path'],'proof':'job/mixed_initial_result.json','spec':'job/geometry_spec.json'}
    if defect in paths:
        p=out/paths[defect];p.write_bytes(p.read_bytes()+b' ')
    elif defect=='decision':report['coordinate_decision']['selected']='qualified_geometry_endpoint'
    elif defect=='archive':report['parent_archive_sha256']='0'*64
    elif defect=='scope':report['source_chemical_findings']='CLEARED'
    elif defect=='adoption':report['automatic_adoption']=True
    elif defect=='max_calls':report['maximum_native_calls']=True
    elif defect=='extra':(out/'unbound.json').write_text('{}')
    report['outputs']=[_ref(out/r['path'],out) for r in report['outputs']]
    (out/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Reader launched'))
    with pytest.raises(ValueError):read_recovered_geometry(out,gradient_directory=gradient,recovery_directory=parent)


@pytest.mark.parametrize('defect',['endpoint_sample','candidate','mechanics','readback','native_manager','consumer','counter'])
def test_completed_reader_rejects_rebound_endpoint_or_native_evidence(tmp_path,monkeypatch,defect):
    from nasolve.cif_recovered_geometry import REPORT
    from nasolve.cif_mixed_geometry import _ref
    gradient,parent,_,phenix=qualified_parent(tmp_path,monkeypatch);out=tmp_path/'out'
    report=trial_recovered_geometry(gradient,parent,phenix,out,max_iterations=5,timeout_seconds=30)
    assert report['status']=='RECOVERED_GEOMETRY_ENDPOINT_PASS'
    if defect=='endpoint_sample':
        p=out/'job/geometry_result.json';v=json.loads(p.read_bytes())
        v['endpoint_gradient_audit']['cases']['full_precision']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1
        p.write_text(json.dumps(v))
    elif defect=='candidate':
        p=out/'candidate/mixed_geometry_model.pdb';p.write_bytes(p.read_bytes()+b'CHANGED')
    elif defect=='mechanics':
        p=out/'native_mechanics.json';v=json.loads(p.read_bytes());v['mechanics_checks_pass']=False;p.write_text(json.dumps(v))
    elif defect=='readback':
        p=out/report['native_readback']['receipt']['path'];v=json.loads(p.read_bytes());v['executable_sha256']='0'*64
        p.write_text(json.dumps(v));report['native_readback']['receipt']=_ref(p,out)
    elif defect=='native_manager':
        p=out/'job/native_validation.json';v=json.loads(p.read_bytes());v['atoms'][0]['atom_id']='CHANGED';p.write_text(json.dumps(v))
    elif defect=='consumer':report['executable_sha256']='0'*64
    else:report['new_native_calls']=1
    report['outputs']=[_ref(out/r['path'],out) for r in report['outputs']]
    (out/REPORT).write_text(json.dumps(report))
    with pytest.raises(ValueError):read_recovered_geometry(out,gradient_directory=gradient,recovery_directory=parent)


@pytest.mark.parametrize('defect',['missing_result','unqualified_derivatives'])
def test_exit_zero_without_qualified_endpoint_skips_native_reread_and_preserves_start(tmp_path,monkeypatch,defect):
    import subprocess
    gradient,parent,_,phenix=qualified_parent(tmp_path,monkeypatch);original=subprocess.Popen;calls=[]
    class Worker:
        def __init__(self,process,job):self.process,self.job=process,job
        def __getattr__(self,name):return getattr(self.process,name)
        def wait(self,**kwargs):
            code=self.process.wait(**kwargs);assert code==0
            path=self.job/'geometry_result.json'
            if defect=='missing_result':path.unlink()
            else:
                value=json.loads(path.read_bytes());value['endpoint_derivative_qualification']='DERIVATIVE_REVIEW'
                path.write_text(json.dumps(value))
            return code
    def controlled(*args,**kwargs):
        calls.append(args[0]);assert len(calls)==1,'Unqualified endpoint launched native reread'
        return Worker(original(*args,**kwargs),Path(kwargs['cwd']))
    monkeypatch.setattr(subprocess,'Popen',controlled)
    report=trial_recovered_geometry(gradient,parent,phenix,tmp_path/'out',max_iterations=5,timeout_seconds=30)
    assert report['execution']['status']=='COMPLETED' and report['status']=='REVIEW'
    assert report['new_native_calls']==1 and report['native_readback']=={'status':'NOT_RUN'}
    assert report['coordinate_decision']['selected']=='verified_recovered_model'
    assert not (tmp_path/'out/candidate/mixed_geometry_model.pdb').exists()
    assert read_recovered_geometry(tmp_path/'out',gradient_directory=gradient,recovery_directory=parent)==report
