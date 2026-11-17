"""Refinement iteration allowances are explicit policy, never convergence claims."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace as S

import pytest
from nasolve.metal.recipe import RecipeError
from tests.test_metal_xyz import prepared, evidence, fake_execution


def test_explicit_coordinate_allowance_preserves_other_policy(tmp_path):
    xyz,c,h,raw,old,ref=prepared(tmp_path)
    plan=xyz.make_plan(raw,h['sites'],old['metadata'],old['references'],old['phases'],refinement_max_iterations=100)
    assert plan['options']['refinement_max_iterations']==100
    assert plan['policy']['refinement_max_iterations']==100
    reduced=copy.deepcopy(plan)
    reduced['options'].pop('refinement_max_iterations');reduced['policy'].pop('refinement_max_iterations')
    assert reduced==old
    phil,args=xyz.parameters(plan,[])
    assert b'  max_number_of_iterations = 100\n' in phil
    assert b'max_number_of_iterations' not in xyz.parameters(old,[])[0]
    assert args==xyz.parameters(old,[])[1]
    native=copy.deepcopy(evidence(plan,raw))
    assert xyz.audit_result(plan,raw,native,raw)['convergence']=='NOT_INDEPENDENTLY_ASSESSED'
    native['policy']['refinement_max_iterations']=25
    with pytest.raises(RecipeError,match='policy'):xyz.audit_result(plan,raw,native,raw)


@pytest.mark.parametrize('value',[0,-1,201,True,100.,'100',float('nan'),float('inf')])
def test_invalid_coordinate_allowance_rejected(tmp_path,value):
    xyz,c,h,raw,old,ref=prepared(tmp_path)
    with pytest.raises(RecipeError,match='refinement iteration'):
        xyz.make_plan(raw,h['sites'],old['metadata'],old['references'],old['phases'],refinement_max_iterations=value)


def test_omission_is_legacy_and_explicit_default_is_recorded(tmp_path):
    xyz,c,h,raw,old,ref=prepared(tmp_path)
    assert xyz.make_plan(raw,h['sites'],old['metadata'],old['references'],old['phases'],refinement_max_iterations=None)==old
    plan=xyz.make_plan(raw,h['sites'],old['metadata'],old['references'],old['phases'],refinement_max_iterations=25)
    assert plan!=old and plan['policy']['refinement_max_iterations']==25
    assert xyz.make_plan(raw,h['sites'],old['metadata'],old['references'],old['phases'],refinement_max_iterations=200)['policy']['refinement_max_iterations']==200


def test_native_reader_observes_actual_allowance(tmp_path):
    from nasolve.metal._xyz_native import policy
    xyz,c,h,raw,old,ref=prepared(tmp_path)
    plan=xyz.make_plan(raw,h['sites'],old['metadata'],old['references'],old['phases'],refinement_max_iterations=100)
    target=plan['policy']
    main_names=('target','random_seed','nproc','apply_overall_isotropic_scale_to_adp','update_f_part1','nqh_flips','ordered_solvent','find_and_add_hydrogens','bulk_solvent_and_scale')
    params=S(main=S(**{k:target[k]for k in main_names},number_of_macro_cycles=target['cycles'],max_number_of_iterations=100),
        refine=S(strategy=target['strategy'],adp=S(individual=S(isotropic='all',anisotropic=None))),
        bulk_solvent_and_scale=S(apply_back_trace=False),group_anomalous=S(number_of_minimizer_cycles=3,lbfgs_max_iterations=20,find_automatically=False),
        pdb_interpretation=S(automatic_linking=S(link_metals=False)),target_weights=S(optimize_xyz_weight=False,optimize_adp_weight=False))
    dm=S(data_manager=S(fmodel=S(xray_data=S(outliers_rejection=False,force_anomalous_flag_to_be_equal_to=False,r_free_flags=S(test_flag_value=0)))))
    assert policy(params,dm,True,main_iterations=True)==target
    assert policy(params,dm,True)==old['policy']
    params.main.max_number_of_iterations=25
    captured=policy(params,dm,True,main_iterations=True)
    assert captured['refinement_max_iterations']==25
    native=evidence(plan,raw);native['policy']=captured
    with pytest.raises(RecipeError,match='policy'):xyz.audit_result(plan,raw,native,raw)


def test_declared_siblings_relocate_and_keep_fdp_lineage(tmp_path,monkeypatch):
    old_root=tmp_path/'original'
    xyz,c,h,ref,n=fake_execution(old_root,monkeypatch)
    original_files={str(p.relative_to(c.run)):p.read_bytes()for p in c.run.rglob('*')if p.is_file()}
    docs=[]
    for allowance in (None,25,100):
        docs.append(xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'],refinement_max_iterations=allowance))
    assert len({d['trial_id']for d in docs})==3
    assert all((c.run/name).read_bytes()==raw for name,raw in original_files.items())
    assert len({json.dumps(d['parent'],sort_keys=True)for d in docs})==1
    from nasolve.metal.fdp import _input_bundle
    inherited=_input_bundle(c.run,'Metal/xyz_003')
    assert inherited['lineage']['xyz_trial_id']==docs[2]['trial_id']
    assert inherited['source_kind']=='native_xyz_endpoint'
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',old_root/'src',ignore=shutil.ignore_patterns('__pycache__'))
    moved=tmp_path/'relocated';old_root.rename(moved)
    script="from nasolve.metal.xyz import verify_xyz; import sys; print([verify_xyz(sys.argv[1], 'Metal/xyz_%03d'%i)['status'] for i in (1,2,3)])"
    result=subprocess.run([sys.executable,'-B','-c',script,str(moved/'dataset/AutoMR/run_001')],cwd=moved,
        env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,check=True)
    assert result.stdout.strip()=="['XYZ_REVIEW', 'XYZ_REVIEW', 'XYZ_REVIEW']" and not old_root.exists()
