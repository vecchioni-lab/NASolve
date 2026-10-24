"""Cache membership may change only with explicit zero-contribution proof."""
from copy import deepcopy
import pytest


def snapshot(extra=False):
    pairs=[{'i_seqs':[0,1],'vdw_distance':2.,'residual':1.,'gradient':[1.,0.,0.,-1.,0.,0.]}]
    if extra:pairs.append({'i_seqs':[0,2],'vdw_distance':1.,'residual':0.,'gradient':[0.]*6})
    return {'pairs':pairs,'nonbonded_target':1.,'nonbonded_gradient':[1.,0.,0.,-1.,0.,0.,0.,0.,0.],
            'target':10.,'gradient':[1.,0.,0.,-1.,0.,0.,0.,0.,0.],
            'proxy_counts':{'n_nonbonded_proxies':len(pairs)}}


@pytest.mark.parametrize('defect',['none','active_added','nonzero_force','changed_vdw','changed_common','duplicate','missing_pair','target','gradient','nonfinite'])
def test_pair_cache_transition_needs_complete_kernel_proof(defect):
    from nasolve.cif_nonbonded_cache_audit import compare_cache_snapshots
    a,b=snapshot(),snapshot(True)
    if defect=='active_added':b['pairs'][-1]['residual']=.01
    if defect=='nonzero_force':b['pairs'][-1]['gradient'][0]=.01
    if defect=='changed_vdw':b['pairs'][0]['vdw_distance']=3.
    if defect=='changed_common':b['pairs'][0]['gradient'][0]=2.
    if defect=='duplicate':b['pairs'].append(deepcopy(b['pairs'][0]))
    if defect=='missing_pair':b['pairs'].pop(0)
    if defect=='target':b['nonbonded_target']=2.
    if defect=='gradient':b['nonbonded_gradient'][0]=2.
    if defect=='nonfinite':b['pairs'][-1]['residual']=float('nan')
    r=compare_cache_snapshots(a,b,3)
    assert r['checks_pass'] is (defect=='none')
    if defect=='none':assert r['added_pairs']==[[0,2]] and r['removed_pairs']==[]


@pytest.mark.parametrize('defect',['none','active_change','membership_drift','wrong_gradient','budget'])
def test_stabilized_retry_retains_original_count_gate_and_rejects_other_changes(defect):
    from nasolve.cif_nonbonded_cache_audit import audit_cache_stabilized_impact
    from tests.test_cif_linear_torsion_impact import fixture
    cases,oracle,refs=fixture();calls=0
    # Use three coordinates, with an independent quadratic removed contribution.
    cases={k:[*v,[2.,2.,2.]] for k,v in cases.items()}
    refs={k:{'target':10*sum(x*x for p in v for x in p),'gradient':[20*x for p in v for x in p]} for k,v in cases.items()}
    def evaluate(manager,points,family,*,capture_pairs=False):
        nonlocal calls
        calls+=1;r=oracle(manager,points,family)
        if defect=='wrong_gradient' and manager=='candidate' and family=='all':r['gradient'][0]+=1.
        if family in {'all','nonbonded'}:
            pair=snapshot(calls>1);r.update(pairs=pair['pairs'],nonbonded_target=pair['nonbonded_target'],nonbonded_gradient=pair['nonbonded_gradient'])
            r['proxy_counts']['n_nonbonded_proxies']=len(pair['pairs'])
            r['nonbonded_membership']=[{'i_seqs':p['i_seqs'],'vdw_distance':p['vdw_distance']} for p in pair['pairs']]
            if defect=='active_change' and calls>1:r['pairs'][-1]['residual']=1.
            if defect=='membership_drift' and not capture_pairs:r['nonbonded_membership'][0]['vdw_distance']=3.
        else:r['nonbonded_membership']=None
        return r
    if defect=='budget':
        with pytest.raises(ValueError,match='budget'):audit_cache_stabilized_impact(evaluate,cases,[0,1],refs,max_calls=2)
    else:
        r=audit_cache_stabilized_impact(evaluate,cases,[0,1],refs)
        assert r['analysis_completed'] and not r['automatic_adoption'] and r['evaluation_calls']<=2000
        assert r['numerical_checks_pass'] is (defect=='none')
        assert all(c['cache_preflight']['raw_transitions_preserved'] for c in r['cases'].values())


@pytest.mark.parametrize('mode',['correct','wrong_gradient','changed_candidate','changed_api','timeout'])
def test_owned_native_worker_executes_cache_proof_before_strict_retry(tmp_path,monkeypatch,mode):
    import nasolve.cif_linear_torsion_impact as impact
    import nasolve.cif_native_validation as native
    from pathlib import Path
    from tests.test_cif_linear_torsion_impact import test_native_pair_worker_matches_both_managers_and_never_calls_optimizer as existing
    run=impact.run_native_linear_torsion_impact
    def wrapped(*args,**kwargs):
        seed=Path(kwargs['environment']['PYTHONPATH']);gr=seed/'cctbx/geometry_restraints/__init__.py'
        gr.write_text('''class prolsq_repulsion_function:
 c_rep=16.;k_rep=1.;irexp=1.;rexp=4.
class nonbonded_prolsq:
 def __init__(self,**kw):pass
 def residual(self):return 0.
 def gradients(self):return [(0.,0.,0.),(0.,0.,0.)]
def nonbonded_residual_sum(**kw):return 0.
''')
        (seed/'cctbx/array_family/flex.py').write_text('from fake_arrays import Vec\ndef vec3_double(values,fill=None):return Vec([fill]*values if isinstance(values,int) else values)\n')
        bootstrap=native._NATIVE_WORKER.replace('from cctbx.array_family import flex','from cctbx.array_family import flex\nfrom cctbx import geometry_restraints as gr')
        bootstrap=bootstrap.replace('n_dihedral_proxies=3 if phase==\'original\' else 2)',
          "n_dihedral_proxies=3 if phase=='original' else 2,nonbonded_proxies=NS(simple=[NS(i_seqs=[0,1],rt_mx_ji=None,vdw_distance=2.)],asu=[]),nonbonded_function=gr.prolsq_repulsion_function(),nonbonded_residual_sum=0.,n_nonbonded_proxies=1)")
        monkeypatch.setattr(native,'_NATIVE_WORKER',bootstrap)
        kwargs['cache_preflight']=True
        r=run(*args,**kwargs)
        if mode in {'correct','wrong_gradient'}:
            assert r['result']['cache_preflight_completed'] and r['result']['pair_kernel_calls']>0
            assert r['cache_preflight_requested'] is True
        return r
    monkeypatch.setattr(impact,'run_native_linear_torsion_impact',wrapped)
    existing(tmp_path,monkeypatch,mode)
