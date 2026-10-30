"""Anomalous-map evidence must remain tied to the exact frozen fit."""
import gzip
import hashlib
import json
import pytest
from nasolve.metal import anomalous_maps as maps
from nasolve.metal import fdp
from tests.test_metal_fdp import prepared,native_result,reflection_evidence,fake_execution


def fixture(plan,native,directory=None):
    native['reflection_before']=native['reflection_after']=reflection_evidence([
        [[-2,0,0],18.,1.,True],[[-1,0,0],8.,1.,False],
        [[1,0,0],12.,1.,False],[[2,0,0],20.,1.,True]])
    raw=b'synthetic anomalous coefficients'
    if directory is not None:(directory/maps.FILENAME).write_bytes(raw)
    samples=[]
    for g in plan['groups']:
        if not g['refine_fdp']:continue
        a=native['atoms'][g['indices'][0]]
        samples.append(dict(node_id=g['id'],key=a['key'],xyz=a['xyz'],samples=123,center_sigma=1.,sphere_min_sigma=-1.,sphere_max_sigma=2.,sphere_mean_sigma=.5))
    return dict(protocol=maps.PROTOCOL,policy=maps.request(),endpoint_sha256=maps.endpoint_digest(native),
        active_state_before='a'*64,active_state_after='a'*64,implementation_sha256='b'*64,
        native_source_hashes={k:'c'*64 for k in ('map_tools','miller','mtz','map_diagnostics')},
        wavelength_A=plan['metadata']['wavelength_A'],pair_indices=[[1,0,0],[2,0,0]],excluded_free_pair_count=1,
        filename=maps.FILENAME,column_labels=['ANOM','PHANOM'],sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
        coefficient_indices=[[1,0,0]],coefficient_count=1,max_abs_coefficient=2.,readback_max_complex_error=1e-7,
        max_dano_amplitude_error=0.,grid=[12,12,12],sites=samples)


def enabled(tmp_path):
    c,g,p,raw=prepared(tmp_path)
    sites=[dict(node_id='m1',key=next(a for a in native_result(p,raw)['atoms'] if a['element']=='Hg')['key'])]
    plan,model=fdp.make_plan(raw,sites,p['metadata'],p['references'],fit_nodes=['m1'],capture_anomalous_map=True)
    n=native_result(plan,model);n['anomalous_map']=fixture(plan,n)
    return plan,model,n


def test_opt_in_does_not_change_parameters_or_default_plan(tmp_path):
    c,g,p,raw=prepared(tmp_path);sites=[dict(node_id='m1',key=native_result(p,raw)['atoms'][-1]['key'])]
    default,_=fdp.make_plan(raw,sites,p['metadata'],p['references'],**p['options'])
    explicit,_=fdp.make_plan(raw,sites,p['metadata'],p['references'],**p['options'],capture_anomalous_map=False)
    new,_=fdp.make_plan(raw,sites,p['metadata'],p['references'],**p['options'],capture_anomalous_map=True)
    assert default==explicit and 'anomalous_map_capture' not in default
    assert fdp.parameters(default,[])==fdp.parameters(new,[])
    plan,model,n=enabled(tmp_path/'enabled');r=fdp.audit_result(plan,model,n)
    assert r['anomalous_map']['scientific_acceptance']=='NOT_ASSESSED'
    assert r['freeze_audit']=='PASS' and r['sites'][0]['f_double_prime']==5.


@pytest.mark.parametrize('change',['missing','unexpected','state','endpoint','free','pair','duplicate','site','coordinate','nan','range','label','path','policy','readback','amplitude','source','grid','wavelength'])
def test_bad_evidence_is_rejected(tmp_path,change):
    p,raw,n=enabled(tmp_path);e=n['anomalous_map']
    if change=='missing':n.pop('anomalous_map')
    if change=='unexpected':p.pop('anomalous_map_capture')
    if change=='state':e['active_state_after']='d'*64
    if change=='endpoint':e['endpoint_sha256']='d'*64
    if change=='free':e['coefficient_indices'].append([2,0,0]);e['coefficient_count']+=1
    if change=='pair':e['pair_indices'].append([3,0,0])
    if change=='duplicate':e['pair_indices'].append([1,0,0])
    if change=='site':e['sites'][0]['node_id']='other'
    if change=='coordinate':e['sites'][0]['xyz']=list(e['sites'][0]['xyz']);e['sites'][0]['xyz'][0]+=.1
    if change=='nan':e['sites'][0]['center_sigma']=float('nan')
    if change=='range':e['sites'][0]['sphere_mean_sigma']=99.
    if change=='label':e['column_labels']=['ANOM','PANOM']
    if change=='path':e['filename']='../bad.mtz'
    if change=='policy':e['policy']['exclude_free_r_pairs']=False
    if change=='readback':e['readback_max_complex_error']=100.
    if change=='amplitude':e['max_dano_amplitude_error']=100.
    if change=='source':e['native_source_hashes']['miller']='bad'
    if change=='grid':e['grid']=[0,1,1]
    if change=='wavelength':e['wavelength_A']=2.
    with pytest.raises(ValueError):fdp.audit_result(p,raw,n)


@pytest.mark.parametrize('value',[1,None,'true',[],{}])
def test_strict_boolean_and_no_failed_attempt_for_invalid_option(tmp_path,monkeypatch,value):
    m,c,g,n=fake_execution(tmp_path,monkeypatch)
    with pytest.raises(ValueError):m.run_fdp(c.run,'Metal/geometry_001',native=n,fit_nodes=['m1'],capture_anomalous_map=value)
    assert not list((c.run/'Metal').glob('fdp_*'))


def test_either_free_mate_excludes_pair_and_missing_mates_cannot_supply_coefficients():
    rows=[[[-1,0,0],8.,1.,True],[[1,0,0],12.,1.,False]]
    assert maps.work_pair_indices([[1,0,0]],rows)==[]
    with pytest.raises(ValueError):maps.work_pair_indices([[2,0,0]],rows)
    with pytest.raises(ValueError):maps.work_pair_indices([[1,0,0],[-1,0,0]],rows)


def test_relocation_and_rehashed_map_tampering(tmp_path,monkeypatch):
    import os,shutil,subprocess,sys
    from pathlib import Path
    from nasolve.metal.context import _reference
    from nasolve.metal.recipe import digest
    old=tmp_path/'old';m,c,g,n=fake_execution(old,monkeypatch);original=m._native
    def capture(directory,native,timeout):
        e=original(directory,native,timeout);p=json.loads((directory/'plan.json').read_text())
        e['anomalous_map']=fixture(p,e,directory)
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()));return e
    monkeypatch.setattr(m,'_native',capture)
    d=m.run_fdp(c.run,'Metal/geometry_001',native=n,fit_nodes=['m1'],capture_anomalous_map=True)
    assert m.verify_fdp(c.run,'Metal/fdp_001')==d
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',old/'src',ignore=shutil.ignore_patterns('__pycache__'))
    moved=tmp_path/'moved';old.rename(moved);run=moved/'dataset/AutoMR/run_001'
    result=subprocess.run([sys.executable,'-B','-c',"from nasolve.metal.fdp import verify_fdp;import sys;print(verify_fdp(sys.argv[1],'Metal/fdp_001')['trial_id'])",str(run)],cwd=moved,env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,check=True)
    assert result.stdout.strip()==d['trial_id'] and not old.exists()
    directory=run/'Metal/fdp_001';p=directory/maps.FILENAME;p.write_bytes(b'changed coefficients')
    d['files'][maps.FILENAME]=_reference(p,run);d.pop('trial_id');d['trial_id']=digest(d)
    (directory/'manifest.json').write_text(json.dumps(d))
    with pytest.raises(ValueError):m.verify_fdp(run,directory)
