"""Explicit geometry/data weights are frozen policy, not silent defaults."""
import copy
import json
import pytest
from nasolve.metal.recipe import RecipeError
from tests.test_metal_xyz import prepared, evidence, fake_execution


def test_explicit_scale_changes_only_declared_weight_policy(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    new=xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],xyz_weight_scale=.05)
    assert new['options']['xyz_weight_scale']==.05
    assert new['policy']['weight_controls']==dict(wxc_scale=.05,wxu_scale=1.,wc=1.,wu=1.,fix_wxc=None,fix_wxu=None)
    base=copy.deepcopy(new);base['options'].pop('xyz_weight_scale');base['policy'].pop('weight_controls')
    assert base==p
    text,args=xyz.parameters(new,[])
    assert b'wxc_scale = 0.05' in text and b'fix_wxc = None' in text
    assert b'wxc_scale' not in xyz.parameters(p,[])[0]
    e=copy.deepcopy(evidence(new,raw))
    assert xyz.audit_result(new,raw,e,raw)['fixed_state_audit']=='PASS'
    e['policy']['weight_controls']['wxc_scale']=.5
    with pytest.raises(RecipeError,match='policy'):xyz.audit_result(new,raw,e,raw)


@pytest.mark.parametrize('value',[0,-.1,True,float('nan'),float('inf'),.00001,10.01,'0.05'])
def test_invalid_scale_rejected_before_allocation(tmp_path,value):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    with pytest.raises(RecipeError):xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],xyz_weight_scale=value)


def test_explicit_default_is_distinct_from_legacy_implicit_default(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    controlled=xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],xyz_weight_scale=.5)
    assert controlled!=p and 'weight_controls' not in p['policy']
    assert xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],xyz_weight_scale=None)==p


def test_controlled_trial_replays_and_inherits_into_fdp_parent(tmp_path,monkeypatch):
    xyz,c,h,ref,n=fake_execution(tmp_path,monkeypatch)
    doc=xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'],xyz_weight_scale=.05)
    assert xyz.verify_xyz(c.run,'Metal/xyz_001')==doc
    assert json.loads((c.run/'Metal/xyz_001/plan.json').read_text())['options']['xyz_weight_scale']==.05
    from nasolve.metal.fdp import _input_bundle
    source=_input_bundle(c.run,'Metal/xyz_001')
    assert source['lineage']['xyz_trial_id']==doc['trial_id']
    assert source['source_kind']=='native_xyz_endpoint'


def test_native_capture_reads_controls_instead_of_echoing_requested_plan(tmp_path):
    from types import SimpleNamespace as S
    from nasolve.metal._xyz_native import policy
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    controlled=xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],xyz_weight_scale=.05)
    target=controlled['policy']
    main_names=('target','random_seed','nproc','apply_overall_isotropic_scale_to_adp','update_f_part1','nqh_flips','ordered_solvent','find_and_add_hydrogens','bulk_solvent_and_scale')
    params=S(main=S(**{k:target[k] for k in main_names},number_of_macro_cycles=target['cycles']),
        refine=S(strategy=target['strategy'],adp=S(individual=S(isotropic='all',anisotropic=None))),
        bulk_solvent_and_scale=S(apply_back_trace=False),group_anomalous=S(number_of_minimizer_cycles=3,lbfgs_max_iterations=20,find_automatically=False),
        pdb_interpretation=S(automatic_linking=S(link_metals=False)),
        target_weights=S(optimize_xyz_weight=False,optimize_adp_weight=False,**target['weight_controls']))
    dm=S(data_manager=S(fmodel=S(xray_data=S(outliers_rejection=False,force_anomalous_flag_to_be_equal_to=False,r_free_flags=S(test_flag_value=0)))))
    assert policy(params,dm,True,weight_controls=True)==target
    assert policy(params,dm,True)==p['policy']
    for field in target['weight_controls']:
        original=getattr(params.target_weights,field)
        setattr(params.target_weights,field,.123)
        captured=policy(params,dm,True,weight_controls=True)
        assert captured['weight_controls'][field]==.123
        e=copy.deepcopy(evidence(controlled,raw));e['policy']=captured
        with pytest.raises(RecipeError,match='policy'):xyz.audit_result(controlled,raw,e,raw)
        setattr(params.target_weights,field,original)


def test_controlled_siblings_relocate_after_original_path_is_gone(tmp_path,monkeypatch):
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    old=tmp_path/'original'
    xyz,c,h,ref,n=fake_execution(old,monkeypatch)
    docs=[]
    for scale in (.5,.05):
        docs.append(xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'],xyz_weight_scale=scale))
    assert docs[0]['parent']==docs[1]['parent'] and docs[0]['trial_id']!=docs[1]['trial_id']
    assert xyz.verify_xyz(c.run,'Metal/xyz_001')==docs[0]
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',old/'src',ignore=shutil.ignore_patterns('__pycache__'))
    moved=tmp_path/'relocated';old.rename(moved)
    script="from nasolve.metal.xyz import verify_xyz; import sys; print([verify_xyz(sys.argv[1], 'Metal/xyz_%03d'%i)['status'] for i in (1,2)])"
    run=subprocess.run([sys.executable,'-B','-c',script,str(moved/'dataset/AutoMR/run_001')],cwd=moved,env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,check=True)
    assert run.stdout.strip()=="['XYZ_REVIEW', 'XYZ_REVIEW']" and not old.exists()
