"""XYZ probes must use phases explicitly and freeze Q/scattering, not XYZ/B."""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from nasolve.metal.context import _reference, parse_pdb
from nasolve.metal.fdp import audit_reflections
from nasolve.metal.materialize import build_hypothesis
from nasolve.metal.recipe import RecipeError, digest
from tests.test_metal_materialize import control
from tests.test_metal_fdp import native_result, reflection_evidence


def test_merged_audit_is_explicit_and_never_weakens_frozen_fdp_default():
    merged=reflection_evidence();merged['anomalous']=False
    with pytest.raises(RecipeError):audit_reflections(merged,merged)
    result=audit_reflections(merged,merged,anomalous=False)
    assert result['anomalous'] is False and result['indices_and_flags']=='UNCHANGED'
    with pytest.raises(RecipeError):audit_reflections(merged,merged,anomalous=0)
    with pytest.raises(RecipeError):audit_reflections(reflection_evidence(),reflection_evidence(),anomalous=False)


def prepared(tmp_path):
    from nasolve.metal import xyz
    context,recipe,placement=control(tmp_path,metals=('Au','Ag'),restrained=False)
    h=build_hypothesis(context,recipe,placement)
    raw=(context.run/h['files']['model']['relative_path']).read_bytes()
    meta=dict(wavelength_A=.92,anomalous_labels=['F(+)','SIGF(+)','F(-)','SIGF(-)'],free_r_label='FreeR_flag')
    refs=[dict(element=e,f_prime=-.2,f_double_prime=3.,wavelength_A=.92,provider='cctbx-sasaki',
          phenix_version='2.2.1',native_version='2.2.1-6174',table_sha256='1'*64)
          for e in sorted({a.element for a in parse_pdb(raw).snapshot.atoms})]
    phases=context.run/'discovery.mtz';phases.write_bytes(b'synthetic captured HL file')
    ref=_reference(phases,context.run)
    p=xyz.make_plan(raw,h['sites'],meta,refs,dict(sha256=ref['sha256'],size=ref['size'],labels=['HLAM','HLBM','HLCM','HLDM']))
    return xyz,context,h,raw,p,ref


def evidence(plan,model):
    e=native_result(plan,model)
    e['reflection_before']['anomalous']=False;e['reflection_after']['anomalous']=False
    rows=[[[1,0,0],[1.,2.,3.,4.]],[[2,0,0],[0.,0.,0.,0.]]]
    phase=dict(rows=rows,count=2,hash=digest(rows))
    symmetry=dict(unit_cell=[40.,40.,40.,90.,90.,90.],space_group_number=1)
    e.update(input_symmetry=copy.deepcopy(symmetry),symmetry_before=copy.deepcopy(symmetry),symmetry_after=copy.deepcopy(symmetry))
    e.update(phases_before=copy.deepcopy(phase),phases_after=copy.deepcopy(phase),phase_source=copy.deepcopy(phase),phase_labels=plan['phases']['labels'])
    return e


def test_phase_geometry_policy_separates_anomalous_quantitation(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    assert p['policy']['strategy']==['individual_sites','individual_adp']
    assert p['policy']['target']=='mlhl' and p['policy']['experimental_phases']
    assert all(not g['refine_fp'] and not g['refine_fdp'] and g['f_double_prime_start']==0 for g in p['groups'])
    assert any(g['element']=='I' for g in p['groups'])
    phil,args=xyz.parameters(p,['resource_000.cif'])
    assert b'force_anomalous_flag_to_be_equal_to = False' in phil
    assert b'link_metals = False' in phil and b'isotropic = all' in phil
    assert 'experimental_phases.labels=HLAM,HLBM,HLCM,HLDM' in args
    assert b'group_anomalous\n' not in phil and b'occupancies' not in phil
    result=xyz.audit_result(p,raw,evidence(p,raw),raw)
    assert result['fixed_state_audit']=='PASS' and result['fdp_quantitation_ready'] is False
    assert len(result['sites'])==2 and result['environmental_b_applied'] is False


def test_native_xyz_and_high_b_may_change_but_serialization_must_match(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path);e=evidence(p,raw)
    e['atoms'][-1]['xyz'][0]+=.02;e['atoms'][-1]['b_iso']=345.1234
    lines=raw.decode().splitlines(keepends=True)
    for i,l in enumerate(lines):
        if l[:6]=='HETATM' and l[21:26].strip()=='M   2':
            lines[i]=l[:30]+f'{e["atoms"][-1]["xyz"][0]:8.3f}'+l[38:60]+f'{345.1234:6.2f}'+l[66:]
    endpoint=''.join(lines).encode()
    result=xyz.audit_result(p,raw,e,endpoint)
    assert result['sites'][-1]['b_iso']==345.1234
    assert result['sites'][-1]['displacement_A']==pytest.approx(.02)
    with pytest.raises(RecipeError):xyz.audit_result(p,raw,e,raw)


@pytest.mark.parametrize('change',['q','fp','fdp','identity','element','charge','normal_type','count','aniso','negative_b','nan','group','policy','labels','phase','phase_hash','phase_indices','phase_source','flags','completion','symmetry','source_hashes'])
def test_successful_exit_does_not_excuse_science_changes(tmp_path,change):
    xyz,c,h,raw,p,ref=prepared(tmp_path);e=evidence(p,raw)
    if change=='symmetry':e['symmetry_after']['unit_cell'][0]=41.
    elif change=='source_hashes':e['native_source_hashes']={}
    elif change=='q':e['atoms'][0]['occupancy']+=.1
    elif change in {'fp','fdp'}:e['atoms'][0][change]+=.1
    elif change=='identity':e['atoms'][0]['key']['atom_name']='wrong'
    elif change=='element':e['atoms'][0]['element']='O'
    elif change=='charge':e['atoms'][0]['charge']='1+'
    elif change=='normal_type':e['atoms'][0]['normal_scattering_type']='S2-'
    elif change=='count':e['atoms'].pop()
    elif change=='aniso':e['atoms'][0]['u_cart']=[1.]*6
    elif change=='negative_b':e['atoms'][0]['b_iso']=-1.
    elif change=='nan':e['atoms'][0]['xyz'][0]=float('nan')
    elif change=='group':e['groups'][0]['indices']=[0]
    elif change=='policy':e['policy']=dict(p['policy'],target='ml')
    elif change=='labels':e['phase_labels']=['HLA','HLB','HLC','HLD']
    elif change=='phase':e['phases_after']['rows'][0][1][0]=22.;e['phases_after']['hash']=digest(e['phases_after']['rows'])
    elif change=='phase_hash':e['phases_before']['hash']='4'*64
    elif change=='phase_indices':e['phases_before']['rows'][0][0][0]=4;e['phases_before']['hash']=digest(e['phases_before']['rows'])
    elif change=='phase_source':e['phase_source']['rows'][0][1][0]=22.;e['phase_source']['hash']=digest(e['phase_source']['rows'])
    elif change=='flags':e['reflection_after']['rows'][0][3]=True;e['reflection_after']['hash']=digest(e['reflection_after']['rows'])
    elif change=='completion':e['completed']=False
    with pytest.raises(RecipeError):xyz.audit_result(p,raw,e,raw)


@pytest.mark.parametrize('labels',[[],['HLA','HLBM','HLC','HLD'],['I(+)','SIGI(+)','I(-)','SIGI(-)']])
def test_invalid_phase_family_rejected_before_execution(tmp_path,labels):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    with pytest.raises(RecipeError):xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],dict(p['phases'],labels=labels))


def fake_execution(tmp_path,monkeypatch):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    monkeypatch.setattr(xyz,'inspect_observations',lambda *a,**kw:p['metadata'])
    monkeypatch.setattr(xyz,'reference_scattering',lambda *a,**kw:p['references'])
    monkeypatch.setattr(xyz,'audit_free_r_flags',lambda *a,**kw:SimpleNamespace(valid=True,status='VALID',details={},warnings=()))
    def fake(directory,native,timeout):
        plan=json.loads((directory/'plan.json').read_text());model=(directory/'input.pdb').read_bytes()
        e=evidence(plan,model)
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()))
        (directory/'final.pdb').write_bytes(model);(directory/'native.log').write_text('synthetic')
        return e
    monkeypatch.setattr(xyz,'_native',fake)
    native=SimpleNamespace(version='2.2.1',executables={'phenix.python':'unused','phenix.mtz.dump':'unused'},environment={})
    return xyz,c,h,ref,native


def run_control(tmp_path,monkeypatch):
    xyz,c,h,ref,n=fake_execution(tmp_path,monkeypatch)
    before={str(p.relative_to(c.run)):p.read_bytes() for p in c.run.rglob('*') if p.is_file()}
    result=xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'])
    directory=c.run/Path(result['files']['result.json']['relative_path']).parent
    assert all((c.run/name).read_bytes()==v for name,v in before.items())
    return xyz,c,ref,n,result,directory


def test_numbered_trial_replays_without_native_and_preserves_parent(tmp_path,monkeypatch):
    xyz,c,ref,n,result,d=run_control(tmp_path,monkeypatch)
    monkeypatch.setattr(xyz,'_native',lambda *a,**kw:pytest.fail('Must not execute during verification'))
    assert xyz.verify_xyz(c.run,d)==result
    assert not (c.run/'AutoRefine').exists()
    assert str(c.run) not in (d/'parameters.phil').read_text()


def test_failed_attempt_retained_and_next_attempt_has_new_number(tmp_path,monkeypatch):
    xyz,c,h,ref,n=fake_execution(tmp_path,monkeypatch);good=xyz._native
    def fail(*a,**kw):raise RecipeError('Synthetic failure')
    monkeypatch.setattr(xyz,'_native',fail)
    with pytest.raises(RecipeError):xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'])
    assert (c.run/'Metal/xyz_001/failure.json').is_file()
    assert not (c.run/'Metal/xyz_001/manifest.json').exists()
    monkeypatch.setattr(xyz,'_native',good)
    result=xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'])
    assert '/xyz_002/' in result['files']['result.json']['relative_path']


@pytest.mark.parametrize('target',['phases.mtz','parameters.phil','final.pdb','result.json'])
def test_even_rehashed_payload_cannot_bypass_replay(tmp_path,monkeypatch,target):
    xyz,c,ref,n,result,d=run_control(tmp_path,monkeypatch)
    (d/target).write_bytes((d/target).read_bytes()+b'\n')
    if target=='final.pdb':
        (d/target).write_bytes((d/target).read_bytes().replace(b' 31.00',b' 32.00'))
    result['files'][target]=_reference(d/target,c.run);check=dict(result);check.pop('trial_id');result['trial_id']=digest(check)
    (d/'manifest.json').write_text(json.dumps(result))
    with pytest.raises(RecipeError):xyz.verify_xyz(c.run,d)


def test_relocated_temporary_checkout_and_data_verify_after_old_path_removed(tmp_path,monkeypatch):
    xyz,c,ref,n,result,d=run_control(tmp_path/'old',monkeypatch)
    source=Path(__file__).resolve().parents[1]/'src'
    old=tmp_path/'old';shutil.copytree(source,old/'src',ignore=shutil.ignore_patterns('__pycache__'))
    new=tmp_path/'relocated';old.rename(new)
    run=new/'dataset/AutoMR/run_001'
    script="from nasolve.metal.xyz import verify_xyz; import sys; print(verify_xyz(sys.argv[1], 'Metal/xyz_001')['status'])"
    completed=subprocess.run([sys.executable,'-B','-c',script,str(run)],cwd=new,
        env=dict(os.environ,PYTHONPATH=str(new/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,check=True)
    assert completed.stdout.strip()=='XYZ_REVIEW' and not old.exists()


def test_native_timeout_cleans_entire_process_group(tmp_path,monkeypatch):
    from nasolve.metal import xyz
    calls=[]
    class Process:
        pid=12345
        returncode=0
        def wait(self,timeout=None):
            calls.append(('wait',timeout))
            if timeout==17:raise subprocess.TimeoutExpired('native',17)
    monkeypatch.setattr(xyz.subprocess,'Popen',lambda *a,**kw:Process())
    monkeypatch.setattr(xyz.os,'killpg',lambda pid,sig:calls.append(('kill',pid,sig)))
    native=SimpleNamespace(executables={'phenix.python':'unused'},environment={})
    with pytest.raises(RecipeError,match='timeout'):xyz._native(tmp_path,native,17)
    assert ('kill',12345,xyz.signal.SIGTERM) in calls
    assert ('kill',12345,xyz.signal.SIGKILL) in calls
    assert (tmp_path/'native.log').exists()


def test_serialized_symmetry_cannot_change_even_with_identical_coordinates(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    changed=raw.replace(b'90.00 P 1',b'90.00 P 2')
    assert changed!=raw
    with pytest.raises(RecipeError,match='space-group'):xyz.audit_result(p,raw,evidence(p,raw),changed)


def test_mtz_cell_precision_may_exceed_pdb_precision_without_changing_symmetry(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path);e=evidence(p,raw)
    for k in ('symmetry_before','symmetry_after'):e[k]['unit_cell'][0]+=1e-6
    e['symmetry_after']['unit_cell'][0]+=1e-13
    assert xyz.audit_result(p,raw,e,raw)['fixed_state_audit']=='PASS'
    for k in ('symmetry_before','symmetry_after'):e[k]['unit_cell'][0]+=.002
    with pytest.raises(RecipeError,match='precision'):xyz.audit_result(p,raw,e,raw)
