"""Saved full precision and derivative/source evidence gate a new bounded trial."""
from copy import deepcopy
import json,os,sys
from pathlib import Path
import pytest
from tests.test_cif_corrected_geometry import qualified_result,native_fixture


def saved_result(proof,count):
    points=[[v for v in p] for p in __import__('nasolve.cif_parallelity_audit',fromlist=['toy_planes']).toy_planes()[0]['points']]
    audit=deepcopy(proof);audit['cases'].pop('initial');audit.update(policy_id='cif-fixed-native-gradient-audit-v1',max_evaluation_calls=4000)
    snapshots={name:{k:case['families']['all']['baseline'][k] for k in ['target','gradient_norm']} for name,case in audit['cases'].items()}
    return {'policy_id':'cif-fixed-na-corrected-geometry-trial-v1','status':'REVIEW','captured_inventory_matches':True,
        'qualified_initial_snapshot_matches':True,'policy_inventory':True,'normalization':False,'automatic_adoption':False,
        'starting_coordinates':'CAPTURED_INITIAL','correction_policy_id':'native-parallelity-both-first-planes-v1',
        'constraint_signature_before':proof['constraint_signature_before'],'constraint_signature_after':proof['constraint_signature_after'],
        'installed_optimizer_sources':proof['installed_numeric_sources'],'installed_adapter_sources':proof['installed_adapter_sources'],
        'installed_parallelity_sources':proof['installed_parallelity_sources'],
        'endpoint_derivative_qualification':'SAMPLED_NATIVE_DERIVATIVES_PASS','endpoint_gradient_audit':audit,
        'final_sites_cart':points[:count],'final':snapshots['full_precision'],'serialized':snapshots['pdb_rounded'],
        'stopping':{'reason':'max_iterations','error':None,'iterations':5,'max_iterations':5,'calls':7,'native_criterion_met':False}}


@pytest.mark.parametrize('defect',['none','qualification','sample','family','signature','source','points','snapshot','error','criterion','indices','stopping'])
def test_continuation_requires_qualified_endpoint_and_retains_limit(defect):
    from nasolve.cif_corrected_geometry import validate_continuation
    proof,count=qualified_result();prior=saved_result(proof,count)
    if defect=='qualification':prior['endpoint_derivative_qualification']='DERIVATIVE_REVIEW'
    if defect=='sample':prior['endpoint_gradient_audit']['cases']['full_precision']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1.
    if defect=='family':prior['endpoint_gradient_audit']['cases']['pdb_rounded']['families'].pop('angle')
    if defect=='signature':prior['constraint_signature_after']='2'*64
    if defect=='source':prior['installed_optimizer_sources']=[{'module':'CHANGED','sha256':'0'*64}]
    if defect=='points':prior['final_sites_cart'].pop()
    if defect=='snapshot':prior['final']['target']+=1.
    if defect=='error':prior['stopping']['error']='previous line-search error'
    if defect=='criterion':prior['stopping']['native_criterion_met']=True
    if defect=='indices':prior['endpoint_gradient_audit']['selected_indices']=[1]
    if defect=='stopping':prior['stopping']['iterations']=1
    if defect=='none':assert validate_continuation(prior,proof,count)
    else:
        with pytest.raises(ValueError):validate_continuation(prior,proof,count)


@pytest.mark.parametrize('mode',['limit','converged','rounding','points','rounded_points','order','sample','source','unqualified','policy'])
def test_native_continuation_reproduces_full_precision_before_optimizer_and_keeps_stops(tmp_path,monkeypatch,mode):
    from nasolve.cif_fixed_geometry import run_fixed_geometry
    control=tmp_path/'optimizer_mode'
    model,dictionary,native,seed,config=native_fixture(tmp_path,monkeypatch,'limit',optimizer_control=control)
    kwargs=dict(environment={**os.environ,'PYTHONPATH':str(seed)},phenix_version='EXPLICIT_FAKE',max_iterations=5,
        timeout_seconds=30,policy_inventory=True,validated_correction=config)
    first=run_fixed_geometry(model,[dictionary],[],native,tmp_path/'first',sys.executable,**kwargs)
    assert first['status']=='REVIEW' and first['convergence']=='NOT_CONVERGED_LIMIT',first
    prior=first['result'];saved=deepcopy(prior['final_sites_cart'])
    assert any(float('%.3f'%v)!=v for p in saved for v in p)
    control.write_text(mode if mode in {'limit','converged','rounding'} else 'limit')
    continuation={'result':deepcopy(prior),'archive_sha256':'2'*64}
    if mode=='points':continuation['result']['final_sites_cart'][0][0]+=.01
    if mode=='rounded_points':continuation['result']['final_sites_cart']=[[float('%.3f'%v) for v in p] for p in saved]
    if mode=='order':continuation['result']['final_sites_cart'][0],continuation['result']['final_sites_cart'][1]=saved[1],saved[0]
    if mode=='sample':continuation['result']['endpoint_gradient_audit']['cases']['full_precision']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1.
    if mode=='source':continuation['result']['installed_optimizer_sources'][0]['sha256']='0'*64
    if mode=='unqualified':continuation['result']['endpoint_derivative_qualification']='DERIVATIVE_REVIEW'
    if mode=='policy':kwargs['policy_inventory']=False
    if mode in {'sample','source','unqualified','policy'}:
        with pytest.raises(ValueError):run_fixed_geometry(model,[dictionary],[],native,tmp_path/'second',sys.executable,continuation=continuation,**kwargs)
        assert not list((tmp_path/'second').glob('*/fake_optimizer_called'));return
    r=run_fixed_geometry(model,[dictionary],[],native,tmp_path/'second',sys.executable,continuation=continuation,**kwargs)
    work=Path(r['native_directory']);assert r['source_preserved'] and r['frozen_inputs_preserved']
    assert json.loads((work/'geometry_receipt.json').read_text())==r
    if mode in {'points','rounded_points','order'}:
        assert r['status']=='FAILED' and 'Saved full-precision corrected snapshot differs' in r['result']['error']
        assert not (work/'fake_optimizer_called').exists();return
    assert r['status']=='REVIEW' and r['policy_id']=='cif-fixed-na-corrected-geometry-continuation-v1',r
    q=r['result'];assert q['qualified_continuation_snapshot_matches'] and q['qualified_initial_snapshot_matches']
    assert q['starting_coordinates']=='SAVED_FULL_PRECISION_ENDPOINT'
    assert q['initial']['target']==prior['final']['target'] and q['initial']['gradient_norm']==prior['final']['gradient_norm']
    for actual,point in zip(q['final_sites_cart'],saved):assert actual==pytest.approx([v*.99137 for v in point])
    assert q['continuation']['prior_stopping']==prior['stopping'] and q['continuation']['optimizer_history']=='FRESH_LBFGS_FROM_SAVED_COORDINATES'
    assert q['continuation']['total_iterations']==prior['stopping']['iterations']+q['stopping']['iterations']
    assert q['continuation']['total_calls']==prior['stopping']['calls']+q['stopping']['calls']
    assert q['endpoint_derivative_qualification']=='SAMPLED_NATIVE_DERIVATIVES_PASS'
    assert r['convergence']=={'limit':'NOT_CONVERGED_LIMIT','converged':'NATIVE_CRITERION_MET','rounding':'NOT_CONVERGED_ERROR'}[mode]
