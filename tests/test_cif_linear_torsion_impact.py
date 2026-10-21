"""A dictionary omission must explain exactly its measured numerical delta."""
from copy import deepcopy
from pathlib import Path
import json, math, os, sys
import pytest


def fixture():
    cases={'source_seed_native':[[.2,.3,.4],[.8,1.1,1.3]],
           'generated_dictionary_full_precision':[[.25,.35,.45],[.85,1.15,1.35]],
           'generated_dictionary_pdb_rounded':[[.251,.351,.451],[.851,1.151,1.351]]}
    # Independent quadratic oracle. No fake implementation of torsion physics.
    def evaluate(manager,points,family):
        from nasolve.cif_linear_torsion_impact import FAMILIES
        factor=sum(range(1,8)) if family=='all' else FAMILIES.index(family)
        if manager=='original' and family in {'all','dihedral'}:factor+=10.
        return {'target':factor*sum(x*x for p in points for x in p),
                'gradient':[2*factor*x for p in points for x in p],
                'proxy_counts':{'n_dihedral_proxies':3 if manager=='original' else 2}}
    removed={k:{'target':10*sum(x*x for p in points for x in p),'gradient':[20*x for p in points for x in p]} for k,points in cases.items()}
    return cases,evaluate,removed


@pytest.mark.parametrize('defect',['none','unrelated_change','wrong_delta','biased_candidate','repeat_drift','count_drift','nonfinite','mutation'])
def test_impact_mechanics_derivatives_and_norms_are_independent_gates(defect):
    from nasolve.cif_linear_torsion_impact import audit_linear_torsion_impact
    cases,oracle,removed=fixture();saved=deepcopy((cases,removed));calls=0
    def evaluate(manager,points,family):
        nonlocal calls
        calls+=1;r=oracle(manager,points,family)
        if defect=='unrelated_change' and manager=='candidate' and family=='angle':r['gradient'][0]+=1
        if defect=='wrong_delta' and manager=='original' and family in {'all','dihedral'}:r['target']+=1
        if defect=='biased_candidate' and manager=='candidate' and family=='all':r['gradient'][0]+=1
        if defect=='repeat_drift':r['target']+=calls*.001
        if defect=='count_drift' and manager=='candidate' and calls>32:r['proxy_counts']['extra']=1
        if defect=='nonfinite':r['gradient'][0]=float('nan')
        if defect=='mutation':points[0][0]+=1
        return r
    if defect in {'nonfinite','mutation'}:
        with pytest.raises(ValueError):audit_linear_torsion_impact(evaluate,cases,[0,1],removed)
    else:
        r=audit_linear_torsion_impact(evaluate,cases,[0,1],removed)
        assert r['analysis_completed'] and r['status']=='REVIEW' and not r['automatic_adoption']
        assert r['numerical_checks_pass'] is (defect=='none')
        assert r['evaluation_calls']<=2000 and r['model_optimization']=='NOT_RUN'
        if defect=='none':
            assert all(c['checks']['full_delta_matches_removed'] and c['checks']['dihedral_delta_matches_removed'] for c in r['cases'].values())
    assert (cases,removed)==saved


def test_budget_and_invalid_coordinate_or_reference_scopes_are_refused():
    from nasolve.cif_linear_torsion_impact import audit_linear_torsion_impact
    cases,oracle,removed=fixture()
    with pytest.raises(ValueError,match='budget'):audit_linear_torsion_impact(oracle,cases,[0],removed,max_calls=2)
    for indices in [[True],[0,0],[-1],[2],[]]:
        with pytest.raises(ValueError):audit_linear_torsion_impact(oracle,cases,indices,removed)
    removed.pop('source_seed_native')
    with pytest.raises(ValueError):audit_linear_torsion_impact(oracle,cases,[0],removed)


def test_removed_gradients_scatter_by_exact_proxy_indices_and_add_shared_atoms():
    from nasolve.cif_linear_torsion_impact import removed_torsion_references
    proxies=[{'i_seqs':[0,1,2,3]},{'i_seqs':[2,3,4,5]}]
    rows=[{'proxy':p,'baseline':{'single_target':i+1.,'single_gradient':[float(i+1)]*12}} for i,p in enumerate(proxies)]
    r=removed_torsion_references({'cases':{'saved':{'proxies':rows}}},proxies,6)
    assert r['saved']['target']==3 and r['saved']['gradient']==[1.]*6+[3.]*6+[2.]*6
    rows[0]['proxy']={'i_seqs':[1,0,2,3]}
    with pytest.raises(ValueError):removed_torsion_references({'cases':{'saved':{'proxies':rows}}},proxies,6)


@pytest.mark.parametrize('mode',['correct','wrong_gradient','changed_original','changed_candidate','changed_api','changed_adapter','timeout'])
def test_native_pair_worker_matches_both_managers_and_never_calls_optimizer(tmp_path,monkeypatch,mode):
    from hashlib import sha256
    from types import SimpleNamespace as NS
    import nasolve.cif_linear_torsion_impact as impact
    import nasolve.cif_native_validation as native_module
    from tests.test_cif_fixed_geometry import worker_fixture,policy_inventory
    from tests.test_cif_fragment_restoration import fixture as model_fixture
    protected=tmp_path/'protected';protected.mkdir();_,model,_,expected,_=model_fixture(protected);policy_inventory(expected)
    old=protected/'original.cif';old.write_text('data_comp_ZZZ\n_chem_comp.id ZZZ\n');new=protected/'candidate.cif';new.write_bytes(old.read_bytes())
    seed=worker_fixture(tmp_path/'fake',expected,'limit');kinds=['bond','angle','dihedral','chirality','planarity','parallelity','nonbonded']
    (seed/'cctbx/geometry_restraints/flags.py').write_text('class flags:\n def __init__(self,default=False):\n'+''.join(f'  self.{k}=default\n' for k in kinds))
    (seed/'cctbx/array_family/flex.py').write_text('from fake_arrays import Vec\ndef vec3_double(values):return Vec(values)\n')
    bootstrap='''
import json
from pathlib import Path
from types import SimpleNamespace as NS
from cctbx.array_family import flex
report=json.loads(Path('expected_inventory.json').read_text())
phase=Path.cwd().name
if MODE=='changed_original' and phase=='original' or MODE=='changed_candidate' and phase=='candidate':report['restraint_policy']['secondary_structure_enabled']=True
sites=flex.vec3_double(report['geometry']['sites_cart_exact'])
class Geo:
    site_symmetry_table=NS(special_position_indices=lambda:[])
    angle_proxies=[];dihedral_proxies=[];const_dihedral_proxies=[];chirality_proxies=[];planarity_proxies=[];parallelity_proxies=[]
    def pair_proxies(self,sites_cart):return NS(bond_proxies=NS(simple=[],asu=[]))
    def energies_sites(self,sites_cart,flags,compute_gradients,normalization):
        assert compute_gradients and normalization is False
        factor=sum(i+1 for i,k in enumerate(KINDS) if getattr(flags,k))
        if phase=='original' and flags.dihedral:factor+=10.
        grad=[[2*factor*v for v in p] for p in sites_cart]
        if MODE=='wrong_gradient' and phase=='candidate':grad[0][0]+=1.
        return NS(target=factor*sum(v*v for p in sites_cart for v in p),gradients=flex.vec3_double(grad),n_dihedral_proxies=3 if phase=='original' else 2)
geo=Geo()
raise SystemExit(0)
'''.replace('MODE',repr(mode)).replace('KINDS',repr(kinds))
    monkeypatch.setattr(native_module,'_NATIVE_WORKER',bootstrap)
    if mode=='timeout':monkeypatch.setattr(impact,'_WORKER','import time\ntime.sleep(30)\n')
    files=[('scitbx.lbfgs','scitbx/lbfgs.py'),('cctbx.geometry_restraints.flags','cctbx/geometry_restraints/flags.py'),
      ('cctbx.geometry_restraints.manager','cctbx/geometry_restraints/manager.py'),('cctbx.geometry_restraints.energies','cctbx/geometry_restraints/energies.py'),
      ('scitbx_lbfgs_ext','scitbx_lbfgs_ext.py'),('cctbx_geometry_restraints_ext','cctbx_geometry_restraints_ext.py')]
    sources=[{'module':n,'sha256':sha256((seed/f).read_bytes()).hexdigest()} for n,f in files]
    if mode=='changed_api':sources[0]['sha256']='0'*64
    if mode=='changed_adapter':
        bootstrap=bootstrap.replace("geo=Geo()", "geo=Geo()\nif phase=='candidate':\n p=Path(flex.__file__);p.write_text(p.read_text()+'\\n# FAKE CHANGE\\n')")
        monkeypatch.setattr(native_module,'_NATIVE_WORKER',bootstrap)
    exe=tmp_path/'bin/phenix.python';exe.parent.mkdir();exe.write_text('#!'+sys.executable+'\nimport runpy,sys,os\nsys.path.insert(0,os.getcwd())\nsys.argv=[a for a in sys.argv[1:] if a!="-B"]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');exe.chmod(0o755)
    points=expected['geometry']['sites_cart_exact'];cases={'saved':points};removed={'saved':{'target':10*sum(v*v for p in points for v in p),'gradient':[20*v for p in points for v in p]}}
    r=impact.run_native_linear_torsion_impact(model,old,new,[],{'original':expected,'candidate':expected},cases,[0],removed,sources,
       tmp_path/'out',exe,environment={**os.environ,'PYTHONPATH':str(seed)},phenix_version='EXPLICIT_FAKE',installation_root=tmp_path,
       timeout_seconds=1 if mode=='timeout' else 30)
    assert r['source_preserved'] and r['frozen_inputs_preserved']
    assert r['status']==('REVIEW' if mode in {'correct','wrong_gradient'} else 'FAILED'),r
    if mode in {'correct','wrong_gradient'}:assert r['result']['numerical_checks_pass'] is (mode=='correct')
    if mode=='timeout':assert r['execution']['status']=='TIMED_OUT'
    work=Path(r['native_directory']);assert not list(work.rglob('fake_optimizer_called'))
    assert json.loads((work/'impact_receipt.json').read_text())==r
