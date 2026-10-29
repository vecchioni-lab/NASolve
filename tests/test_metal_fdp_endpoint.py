"""Native-refined endpoint lineage must survive environmental B and Q branches."""
import copy
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
from nasolve.metal import Recipe, RecipeError
from nasolve.metal.context import _reference, parse_pdb
from nasolve.metal.materialize import build_hypothesis
from tests.test_metal_materialize import control
from tests.test_metal_fdp import native_result
from tests.test_metal_xyz import evidence


def endpoint(tmp_path, monkeypatch, metals=('Ag',)*6):
    from nasolve.metal import xyz, fdp
    c, recipe, placement = control(tmp_path, metals=metals)
    doc = recipe.to_dict()
    for i in range(1, len(metals)+1):
        for donor in ('d1', 'd2'):
            doc['restraints'].append(dict(id=f'{donor}-{i}', kind='distance', nodes=[donor,f'm{i}'],
                set_id='s', enabled=True, target=2.5, sigma=.1, unit='angstrom',
                source={'kind':'user','note':'Synthetic endpoint test'}))
    recipe = Recipe(doc); placement['recipe_sha256'] = recipe.sha256
    h = build_hypothesis(c, recipe, placement)
    raw = (c.run/h['files']['model']['relative_path']).read_bytes()
    metadata = dict(wavelength_A=2.0664, anomalous_labels=['F(+)','SIGF(+)','F(-)','SIGF(-)'],free_r_label='FreeR_flag')
    refs = [dict(element=e,f_prime=-.2,f_double_prime=6.9 if e=='Ag' else 3.,wavelength_A=2.0664,
                 provider='cctbx-sasaki',native_version='2.2.1-6174',table_sha256='1'*64)
            for e in sorted({a.element for a in parse_pdb(raw).snapshot.atoms})]
    native = SimpleNamespace(version='2.2.1', executables={'phenix.python':'unused','phenix.mtz.dump':'unused'},environment={})
    for module in (xyz,fdp):
        monkeypatch.setattr(module,'inspect_observations',lambda *a,**kw:metadata)
        monkeypatch.setattr(module,'reference_scattering',lambda *a,**kw:refs)
        monkeypatch.setattr(module,'audit_free_r_flags',lambda *a,**kw:SimpleNamespace(valid=True,status='VALID',details={},warnings=()))
    def fake_xyz(directory,native,timeout):
        p=json.loads((directory/'plan.json').read_text()); raw=(directory/'input.pdb').read_bytes()
        e=evidence(p,raw); lines=raw.decode().splitlines(keepends=True); index=0
        for i,line in enumerate(lines):
            if line[:6].strip() not in {'ATOM','HETATM'}: continue
            b=[170.,350.,150.][index] if index<3 else 55.
            x=e['atoms'][index]['xyz'][0]+.25
            lines[i]=line[:30]+f'{x:8.3f}'+line[38:60]+f'{b:6.2f}'+line[66:]
            e['atoms'][index]['xyz'][0]=x;e['atoms'][index]['b_iso']=b;index+=1
        (directory/'final.pdb').write_text(''.join(lines));(directory/'native.log').write_text('synthetic XYZ')
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()))
        return e
    def fake_fdp(directory,native,timeout):
        p=json.loads((directory/'plan.json').read_text());raw=(directory/'input.pdb').read_bytes()
        e=native_result(p,raw)
        for g in e['groups']:
            if g['refine_fdp']:
                g['f_double_prime']=g['reference_f_double_prime']
                for i in g['indices']:e['atoms'][i]['fdp']=g['f_double_prime']
        (directory/'final.pdb').write_bytes(raw);(directory/'native.log').write_text('synthetic fdp')
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()))
        return e
    monkeypatch.setattr(xyz,'_native',fake_xyz);monkeypatch.setattr(fdp,'_native',fake_fdp)
    phase=c.run/'phases.mtz';phase.write_bytes(b'synthetic phases')
    x=xyz.run_xyz(c.run,'Metal/hypothesis_001',native=native,phases=_reference(phase,c.run),phase_labels=['HLAM','HLBM','HLCM','HLDM'])
    return c,h,x,native


def test_refined_xyz_and_b_are_used_with_exact_phase_and_observation_lineage(tmp_path,monkeypatch):
    from nasolve.metal.fdp import run_fdp,verify_fdp
    c,h,x,native=endpoint(tmp_path,monkeypatch)
    before={p:p.read_bytes() for p in c.run.rglob('*') if p.is_file()}
    result=run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=[f'm{i}' for i in range(1,7)],metal_b_policy='donor-mean')
    saved=json.loads((c.run/result['files']['result.json']['relative_path']).read_text())
    plan=json.loads((c.run/result['files']['plan.json']['relative_path']).read_text())
    final=parse_pdb((c.run/x['files']['final.pdb']['relative_path']).read_bytes())
    prepared=parse_pdb((c.run/result['files']['input.pdb']['relative_path']).read_bytes())
    assert final.snapshot.atoms==prepared.snapshot.atoms
    assert all(s['b_iso']==260 for s in saved['sites'])
    assert plan['b_calibration']['source_model_sha256']==x['files']['final.pdb']['sha256']
    assert result['parent']['xyz_trial_id']==x['trial_id']
    assert result['input_sources']['phases']==x['input_sources']['phases']
    assert plan['phase_policy']=='model_phases_without_external_phase_restraints'
    assert all(p.read_bytes()==raw for p,raw in before.items())
    assert verify_fdp(c.run,'Metal/fdp_001')==result


def test_xyz_requires_explicit_b_policy_before_any_trial(tmp_path,monkeypatch):
    from nasolve.metal.fdp import run_fdp
    c,h,x,native=endpoint(tmp_path,monkeypatch)
    with pytest.raises(RecipeError,match='B policy'):
        run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=['m1'])
    assert not list((c.run/'Metal').glob('fdp_*'))


def test_refined_seed_flows_through_existing_scan_and_reuse(tmp_path,monkeypatch):
    from nasolve.metal.fdp import run_fdp
    from nasolve.metal import fdp_scan as scan
    c,h,x,native=endpoint(tmp_path,monkeypatch,metals=('Au','Ag'))
    run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=['m1','m2'],metal_b_policy='donor-mean')
    scan.create_plan(c.run,'Metal/fdp_001',{'m1':[.5,.6]},max_trials=2)
    monkeypatch.setattr(scan,'_check_native',lambda *a,**kw:None)
    doc=scan.run_scan(c.run,'Metal/fdp_scan_plan_001',native=native,job_budget=1)
    report=json.loads((c.run/doc['files']['report']['relative_path']).read_text())
    assert report['new_completed']==1 and report['reused']==1
    assert all(s['b_iso']==260 for p in report['points'] for s in p['sites'])
    assert scan.verify_scan(c.run,'Metal/fdp_scan_001')==doc


@pytest.mark.parametrize('target',['final.pdb','phases.mtz','result.json'])
def test_changed_xyz_source_invalidates_child(tmp_path,monkeypatch,target):
    from nasolve.metal.fdp import run_fdp,verify_fdp
    c,h,x,native=endpoint(tmp_path,monkeypatch)
    run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=['m1'],metal_b_policy='donor-mean')
    path=c.run/'Metal/xyz_001'/target;path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(RecipeError):verify_fdp(c.run,'Metal/fdp_001')


def test_refined_endpoint_replays_after_checkout_and_data_relocation(tmp_path,monkeypatch):
    from nasolve.metal.fdp import run_fdp
    old=tmp_path/'old';c,h,x,native=endpoint(old,monkeypatch)
    doc=run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=['m1'],metal_b_policy='donor-mean')
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',old/'src',ignore=shutil.ignore_patterns('__pycache__'))
    moved=tmp_path/'moved';old.rename(moved)
    code="from nasolve.metal.fdp import verify_fdp;print(verify_fdp('dataset/AutoMR/run_001','Metal/fdp_001')['trial_id'])"
    done=subprocess.run([sys.executable,'-B','-c',code],cwd=moved,
        env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
    assert done.returncode==0,done.stderr
    assert done.stdout.strip()==doc['trial_id'] and not old.exists()


def test_identical_atom_records_in_distinct_xyz_trials_are_not_reused_as_one_basis(tmp_path,monkeypatch):
    from nasolve.metal import xyz
    from nasolve.metal.fdp import run_fdp
    from nasolve.metal.fdp_compare import build_comparison
    c,h,x,n=endpoint(tmp_path,monkeypatch,metals=('Hg',))
    xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=x['input_sources']['phases'],phase_labels=['HLAM','HLBM','HLCM','HLDM'])
    for source in ('xyz_001','xyz_002'):
        run_fdp(c.run,'Metal/'+source,native=n,fit_nodes=['m1'],metal_b_policy='donor-mean')
    with pytest.raises(RecipeError,match='same geometry'):
        build_comparison(c.run,['Metal/fdp_001','Metal/fdp_002'])
