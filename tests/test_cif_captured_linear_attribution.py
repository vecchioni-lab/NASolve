"""Fresh native jobs and portable replay; synthetic execution is not chemistry."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import json,os,shutil,sys
import pytest


def fixture(tmp_path,monkeypatch):
    from tests.test_cif_linear_torsion_bundle import numerical_case
    from nasolve import cif_captured_linear_attribution as m
    from nasolve import cif_linear_torsion_bundle as b
    out,states,refs=numerical_case(tmp_path);plan=b.read_linear_torsion_bundle(out)
    capture={'phenix_version':'EXPLICIT_FAKE','executable_sha256':sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
             'phil_namespace_policy':'direct','dictionary_source_policy':'EXPLICIT_DICTIONARIES'}
    parents=[]
    for i,(state,ds) in enumerate(zip(states,[plan['inputs'],plan['final_dictionaries']])):
        p=tmp_path/f'capture{i}';p.mkdir();(p/'model.pdb').write_text('EXPLICIT FAKE MODEL')
        (p/'policy.phil').write_text('EXPLICIT FAKE POLICY')
        for j,r in enumerate(ds):shutil.copyfile(out/r['path'],p/f'{j}.cif')
        (p/'native.json').write_text(json.dumps(state))
        (p/'native_receipt.json').write_text(json.dumps(dict(capture,outputs=[{'path':x.name} for x in sorted(p.iterdir())])))
        parents.append(p/'native_receipt.json')
    def inputs(parent):
        parent=Path(parent);cap=json.loads((parent/'native_receipt.json').read_text());state=json.loads((parent/'native.json').read_text())
        return cap,parent/'model.pdb',sorted(parent.glob('*.cif')),[parent/'policy.phil'],state,{}
    monkeypatch.setattr(m,'_inputs',inputs);monkeypatch.setattr(b,'_captured_inputs',inputs)
    return m,out,parents,refs


def test_preparation_and_relocated_reader_never_execute(tmp_path,monkeypatch):
    m,b,rs,refs=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('unexpected execution'))
    q=m.audit_captured_linear_attribution(b,rs,None,tmp_path/'out')
    assert q['status']=='PREPARED_ONLY' and q['kernel_execution_authentication']=='NOT_RUN'
    assert not q['automatic_adoption'] and q['source_chemical_qualification']=='NOT_ASSESSED'
    moved=(tmp_path/'out').rename(tmp_path/'moved');shutil.rmtree(b)
    for r in rs:shutil.rmtree(r.parent)
    assert m.read_captured_linear_attribution(moved)==q


def fake_process(monkeypatch,m,refs,mode='pass'):
    class Process:
        returncode=0
        def __init__(self,*args,**kwargs):
            self.root=Path(kwargs['cwd'])
            if mode=='launch':raise OSError('explicit launch failure')
        def wait(self,timeout):
            if mode=='timeout':
                import subprocess
                raise subprocess.TimeoutExpired('test',timeout)
            if mode=='failed':self.returncode=3;return 3
            pins=json.loads((self.root/'spec.json').read_text())['installed_sources']
            pins=deepcopy(pins)+[dict(module=n,sha256='b'*64,historical_path='/missing/'+n) for n in m.MODULES[3:]]
            result=dict(spec_sha256=sha256((self.root/'spec.json').read_bytes()).hexdigest(),core_sha256=sha256((self.root/'conditioning_core.py').read_bytes()).hexdigest(),
                installed_sources=pins,installed_sources_after=deepcopy(pins),groups=deepcopy(refs))
            if mode=='numeric':result['groups'][0][0]['evaluations'][0]['single_target']+=1
            (self.root/'result.json').write_text(json.dumps(result))
            return 0
    monkeypatch.setattr('subprocess.Popen',Process)
    monkeypatch.setattr('nasolve.cif_native_validation._stop',lambda p:setattr(p,'returncode',-15))
    return SimpleNamespace(executables={'phenix.python':sys.executable},version='EXPLICIT_FAKE',environment=os.environ)


@pytest.mark.parametrize('mode',['pass','failed','launch','timeout','numeric'])
def test_execution_and_failed_attempts_are_immutable(tmp_path,monkeypatch,mode):
    m,b,rs,refs=fixture(tmp_path,monkeypatch);sdk=fake_process(monkeypatch,m,refs,mode)
    q=m.audit_captured_linear_attribution(b,rs,sdk,tmp_path/'out',timeout_seconds=1)
    assert q['status']==('CAPTURED_LINEAR_ATTRIBUTION_PASS' if mode=='pass' else 'REVIEW')
    assert q['new_native_calls']==(0 if mode=='launch' else 1)
    assert q['execution']['status']=={'pass':'COMPLETED','failed':'FAILED','launch':'LAUNCH_FAILED','timeout':'TIMED_OUT','numeric':'COMPLETED'}[mode]
    if mode=='pass':
        assert q['qualification']['removed_proxy_count']==1 and q['kernel_execution_authentication']=='MAINTAINED_FRESH_NATIVE_JOB'
        assert q['derivative_qualification']=='NOT_RUN' and q['coordinate_selection']=='UNCHANGED_CAPTURE_INPUT'
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('reader executed'))
    moved=(tmp_path/'out').rename(tmp_path/'moved')
    for r in rs:shutil.rmtree(r.parent)
    shutil.rmtree(b)
    assert m.read_captured_linear_attribution(moved)==q
    with pytest.raises(ValueError):m.audit_captured_linear_attribution(moved/'bundle',[moved/'captures'/f'{i:03d}/native_receipt.json' for i in range(2)],None,moved)


@pytest.mark.parametrize('defect',['worker','core','spec','result','pins','core_pin','spec_pin','qualification','adoption','science','calls','bool_schema','status','extra','bound_extra','bound_empty','unknown','executable','version','suppressed_pass','extra_result_field'])
def test_rehashed_forgery_cannot_invent_or_hide_a_pass(tmp_path,monkeypatch,defect):
    m,b,rs,refs=fixture(tmp_path,monkeypatch);sdk=fake_process(monkeypatch,m,refs)
    root=tmp_path/'out';q=m.audit_captured_linear_attribution(b,rs,sdk,root)
    if defect in ['worker','core','spec']:
        name={'worker':'worker.py','core':'conditioning_core.py','spec':'spec.json'}[defect];p=root/'job'/name;p.write_bytes(p.read_bytes()+b'\n')
    if defect in ['result','pins','core_pin','spec_pin','extra_result_field']:
        p=root/'job/result.json';v=json.loads(p.read_text())
        if defect=='result':v['groups'][0][0]['evaluations'][0]['single_target']+=1
        if defect=='pins':v['installed_sources_after'][0]['sha256']='0'*64
        if defect=='core_pin':v['core_sha256']='0'*64
        if defect=='spec_pin':v['spec_sha256']='0'*64
        if defect=='extra_result_field':v['invented']=True
        p.write_text(json.dumps(v))
    if defect=='qualification':q['qualification']['removed_proxy_count']=2
    if defect=='adoption':q['automatic_adoption']=True
    if defect=='science':q['source_chemical_qualification']='PASS'
    if defect=='calls':q['new_native_calls']=True
    if defect=='bool_schema':q['schema_version']=True
    if defect=='status':q['status']='REVIEW'
    if defect in ['extra','bound_extra']:(root/'extra').write_text('extra')
    if defect=='bound_empty':(root/'empty').mkdir()
    if defect=='unknown':q['invented']=True
    if defect=='executable':q['executable_sha256']='0'*64
    if defect=='version':q['phenix_version']='other'
    if defect=='suppressed_pass':q.update(status='REVIEW',qualification={'status':'NOT_RUN'},kernel_execution_authentication='NOT_RUN',error='fake error')
    q['outputs']=[m._reference(root/r['path'],root) for r in q['outputs']]
    if defect=='bound_extra':q['outputs'].append(m._reference(root/'extra',root))
    if defect=='bound_empty':q['directories'].append('empty');q['directories'].sort()
    (root/m.REPORT).write_bytes(m._bytes(q))
    with pytest.raises(ValueError):m.read_captured_linear_attribution(root)


@pytest.mark.parametrize('defect',['deadline','version','model','phils','dictionary','stage','authority','sources','no_steps'])
def test_preflight_refuses_before_reserving(tmp_path,monkeypatch,defect):
    m,b,rs,refs=fixture(tmp_path,monkeypatch);sdk=fake_process(monkeypatch,m,refs);seconds=90
    if defect=='deadline':seconds=True
    if defect=='version':sdk.version='other'
    if defect in ['model','phils','dictionary']:
        p=rs[-1].parent/{'model':'model.pdb','phils':'policy.phil','dictionary':'0.cif'}[defect];p.write_text('changed')
    if defect=='stage':rs=rs[:-1]
    if defect=='authority':
        p=rs[-1];v=json.loads(p.read_text());v['dictionary_source_policy']='OTHER';p.write_text(json.dumps(v))
    if defect=='sources':
        p=rs[-1].parent/'native.json';v=json.loads(p.read_text());v['energy_inventory']['installed_sources'][0]['sha256']='0'*64;p.write_text(json.dumps(v))
    if defect=='no_steps':
        from nasolve.cif_linear_torsion_bundle import prepare_linear_torsion_bundle
        b=tmp_path/'no';prepare_linear_torsion_bundle([tmp_path/'bundle/inputs/000.cif'],['DG'],b)
    with pytest.raises(ValueError):m.audit_captured_linear_attribution(b,rs,sdk,tmp_path/'out',timeout_seconds=seconds)
    assert not (tmp_path/'out').exists()


def test_unregistered_capture_artifact_refuses_before_reservation(tmp_path,monkeypatch):
    m,b,rs,refs=fixture(tmp_path,monkeypatch)
    (rs[0].parent/'unregistered.txt').write_text('unrelated to recorded native capture')
    with pytest.raises(ValueError):m.audit_captured_linear_attribution(b,rs,None,tmp_path/'out')
    assert not (tmp_path/'out').exists()

def test_launch_failure_requires_its_explicit_error(tmp_path,monkeypatch):
    m,b,rs,refs=fixture(tmp_path,monkeypatch);sdk=fake_process(monkeypatch,m,refs,'launch')
    root=tmp_path/'out';q=m.audit_captured_linear_attribution(b,rs,sdk,root)
    q.pop('error');q['execution']['error']=None
    (root/m.REPORT).write_bytes(m._bytes(q))
    with pytest.raises(ValueError):m.read_captured_linear_attribution(root)
