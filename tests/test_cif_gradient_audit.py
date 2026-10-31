"""Finite differences must expose biased gradients without relaxing definitions."""
from copy import deepcopy
import math
import pytest


def polynomial(points,family):
    from nasolve.cif_gradient_audit import FAMILIES
    flat=[v for p in points for v in p]
    coefficient=sum(range(1,8)) if family=='all' else list(FAMILIES).index(family)
    return {'target':coefficient*sum((i+1)*v*v for i,v in enumerate(flat)),
        'gradient':[2*coefficient*(i+1)*v for i,v in enumerate(flat)],
        'terms':{},'proxy_counts':{'n_nonbonded_proxies':5}}


@pytest.mark.parametrize('biased',[False,True])
def test_directional_differences_reveal_an_incorrect_gradient(biased):
    from nasolve.cif_gradient_audit import audit_gradients
    points=[[.25,.5,.75],[1.,1.25,1.5]];saved=deepcopy(points)
    def evaluate(p,family):
        result=polynomial(p,family)
        if biased and family=='parallelity':result['gradient'][0]+=3.
        return result
    result=audit_gradients(evaluate,{'endpoint':points},[0,1])
    assert result['analysis_completed'] and result['model_optimization']=='NOT_RUN'
    assert result['cases']['endpoint']['sampled_gradients_consistent'] is (not biased)
    assert result['cases']['endpoint']['gradient_additivity']['consistent'] is (not biased)
    assert result['evaluation_calls']<4000 and points==saved
    assert result['scientific_approval']=='NOT_RUN' and result['automatic_adoption'] is False


def test_cache_drift_nonfinite_results_and_call_limit_cannot_be_reported_as_consistent():
    from nasolve.cif_gradient_audit import audit_gradients
    calls=0
    def drift(points,family):
        nonlocal calls
        calls+=1;r=polynomial(points,family);r['target']+=calls*.01;return r
    result=audit_gradients(drift,{'endpoint':[[.25,.5,.75]]},[0])
    assert not result['cases']['endpoint']['baseline_repeats_consistent']
    with pytest.raises(ValueError,match='budget'):audit_gradients(polynomial,{'endpoint':[[.25,.5,.75]]},[0],max_calls=5)
    def nonfinite(points,family):
        r=polynomial(points,family);r['gradient'][0]=float('nan');return r
    with pytest.raises(ValueError,match='finite'):audit_gradients(nonfinite,{'endpoint':[[.25,.5,.75]]},[0])


def test_step_size_evidence_remains_visible_and_reference_mismatch_retains_review():
    from nasolve.cif_gradient_audit import audit_gradients,STEPS
    result=audit_gradients(polynomial,{'endpoint':[[.25,.5,.75]]},[0],references={'endpoint':{'target':-1.,'gradient_norm':0.}})
    case=result['cases']['endpoint'];assert not case['captured_snapshot_match']['consistent']
    for family in case['families'].values():
        for row in family['directions']:
            assert [v['step'] for v in row['samples']]==list(STEPS)
            assert len(row['samples'])==4
    assert result['status']=='REVIEW'


@pytest.mark.parametrize('indices',[[True],[2],[-1],[0,0]])
def test_ambiguous_or_invalid_coordinate_probes_are_refused(indices):
    from nasolve.cif_gradient_audit import audit_gradients
    with pytest.raises(ValueError):audit_gradients(polynomial,{'endpoint':[[.25,.5,.75]]},indices)


@pytest.mark.parametrize('mode',['correct','changed_manager','changed_api','timeout'])
def test_native_worker_checks_real_control_flow_without_ever_calling_optimizer(tmp_path,monkeypatch,mode):
    import hashlib,json,os,sys
    from pathlib import Path
    from types import SimpleNamespace as NS
    import nasolve.cif_gradient_audit as audit
    import nasolve.cif_native_validation as native_module
    from tests.test_cif_fixed_geometry import worker_fixture,policy_inventory
    from tests.test_cif_fragment_restoration import fixture
    protected=tmp_path/'protected';protected.mkdir()
    _,model,_,native,_=fixture(protected);policy_inventory(native)
    dictionary=protected/'fake.cif';dictionary.write_text('data_comp_ZZZ\n_chem_comp.id ZZZ\n')
    seed=worker_fixture(tmp_path/'fake',native,'limit')
    kinds=['bond','angle','dihedral','chirality','planarity','parallelity','nonbonded']
    (seed/'cctbx/geometry_restraints/flags.py').write_text('class flags:\n def __init__(self,default=False):\n'+''.join(f'  self.{k}=default\n' for k in kinds))
    bootstrap='''
import json
from pathlib import Path
from types import SimpleNamespace as NS
from fake_arrays import Vec
report=json.loads(Path('expected_inventory.json').read_text())
if MODE=='changed_manager':report['restraint_policy']['secondary_structure_enabled']=True
sites=Vec(report['geometry']['sites_cart_exact'])
class Geo:
    site_symmetry_table=NS(special_position_indices=lambda:[])
    angle_proxies=[];dihedral_proxies=[];const_dihedral_proxies=[];chirality_proxies=[];planarity_proxies=[];parallelity_proxies=[]
    def pair_proxies(self,sites_cart):return NS(bond_proxies=NS(simple=[],asu=[]))
    def energies_sites(self,sites_cart,flags,compute_gradients,normalization):
        assert compute_gradients and normalization is False
        coefficient=sum(i+1 for i,k in enumerate(KINDS) if getattr(flags,k))
        target=coefficient*sum(v*v for p in sites_cart for v in p)
        return NS(target=target,gradients=Vec([[2*coefficient*v for v in p] for p in sites_cart]),n_nonbonded_proxies=5)
geo=Geo()
raise SystemExit(0)
'''.replace('MODE',repr(mode)).replace('KINDS',repr(kinds))
    monkeypatch.setattr(native_module,'_NATIVE_WORKER',bootstrap)
    if mode=='timeout':monkeypatch.setattr(audit,'_GRADIENT_WORKER','import time\ntime.sleep(30)\n')
    mapping=[('scitbx.lbfgs','scitbx/lbfgs.py'),('cctbx.geometry_restraints.flags','cctbx/geometry_restraints/flags.py'),
        ('cctbx.geometry_restraints.manager','cctbx/geometry_restraints/manager.py'),('cctbx.geometry_restraints.energies','cctbx/geometry_restraints/energies.py'),
        ('scitbx_lbfgs_ext','scitbx_lbfgs_ext.py'),('cctbx_geometry_restraints_ext','cctbx_geometry_restraints_ext.py')]
    sources=[{'module':m,'sha256':hashlib.sha256((seed/f).read_bytes()).hexdigest()} for m,f in mapping]
    if mode=='changed_api':sources[0]['sha256']='0'*64
    fake=NS(pair_proxies=lambda **kw:NS(bond_proxies=NS(simple=[],asu=[])),**{k+'_proxies':[] for k in ['angle','dihedral','const_dihedral','chirality','planarity','parallelity']})
    signature=audit.fixed_signature(fake,[])
    points=native['geometry']['sites_cart_exact']
    result=audit.run_native_gradient_audit(model,[dictionary],[],native,{'full_precision':points,'pdb_rounded':points},{},[0],
        sources,signature,tmp_path/'out',Path(sys.executable),environment={**os.environ,'PYTHONPATH':str(seed)},
        phenix_version='EXPLICIT_FAKE',timeout_seconds=1 if mode=='timeout' else 30)
    assert result['source_preserved'] and result['frozen_inputs_preserved']
    assert result['status']==('REVIEW' if mode=='correct' else 'FAILED')
    work=Path(result['native_directory']);assert not (work/'fake_optimizer_called').exists()
    assert json.loads((work/'gradient_receipt.json').read_text())==result
    if mode=='correct':
        assert result['result']['analysis_completed'] and result['result']['captured_inventory_matches']
        assert all(case['sampled_gradients_consistent'] for case in result['result']['cases'].values())
        assert result['result']['evaluation_calls']<4000
