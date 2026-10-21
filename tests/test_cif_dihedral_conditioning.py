"""Keep torsion geometry, numerical derivatives and chemistry approval separate."""
from copy import deepcopy
import math
import pytest


def source():
    points=[[0.,1.,.2],[0.,0.,0.],[1.3,0.,0.],[1.6,.8,1.1]]
    proxy={'i_seqs':[0,1,2,3],'angle_ideal':27.,'weight':.3,'periodicity':3,'alt_angle_ideals':None,'origin_id':0}
    return points,proxy


def oracle(points,proxy,*,biased=False,nonfinite=False):
    # Independent analytic quadratic, deliberately not a torsion implementation.
    target=proxy['weight']*sum(v*v for p in points for v in p)
    gradient=[2*proxy['weight']*v for p in points for v in p]
    if biased:gradient[0]+=1.
    if nonfinite:gradient[0]=float('nan')
    return {'single_target':target,'accumulated_target':target,'single_gradient':gradient,'accumulated_gradient':gradient.copy(),
        'native_angle_defined':True,'native_angle_degrees':42.}


@pytest.mark.parametrize('biased',[False,True])
def test_sampled_derivatives_detect_wrong_gradient_without_changing_originals(biased):
    from nasolve.cif_dihedral_conditioning import audit_dihedral_conditioning
    points,proxy=source();saved=deepcopy((points,proxy))
    r=audit_dihedral_conditioning(lambda x,p:oracle(x,p,biased=biased),{'saved':points},[proxy])
    assert r['analysis_completed'] and r['model_optimization']=='NOT_RUN' and r['automatic_adoption'] is False
    assert (points,proxy)==saved and r['evaluation_pairs']<=r['max_evaluation_pairs']
    row=r['cases']['saved']['proxies'][0]
    assert row['sampled_derivatives_consistent'] is (not biased)
    assert row['geometry']['geometry_defined'] and row['baseline_repeats_consistent']
    assert len(row['directions'])>=12
    assert r['numerical_controls']['well_conditioned']['geometry']['geometry_defined']
    assert not r['numerical_controls']['exact_collinear']['geometry']['geometry_defined']
    assert r['numerical_controls']['exact_collinear']['qualification']=='UNDEFINED_GEOMETRY'


def test_near_linear_and_exact_linear_geometry_cannot_be_promoted_by_finite_zero_gradients():
    from nasolve.cif_dihedral_conditioning import audit_dihedral_conditioning
    points,proxy=source();points[0]=[-1.,1e-7,0.]
    r=audit_dihedral_conditioning(oracle,{'near':points,'exact':[[-1.,0.,0.],*points[1:]]},[proxy])
    near=r['cases']['near']['proxies'][0];exact=r['cases']['exact']['proxies'][0]
    assert near['geometry']['near_collinear_review'] and near['qualification']=='NEAR_COLLINEAR_REVIEW'
    assert exact['qualification']=='UNDEFINED_GEOMETRY' and not exact['sampled_derivatives_consistent']


def test_nonfinite_or_exceptional_kernel_results_remain_explicit_evidence():
    import json
    from nasolve.cif_dihedral_conditioning import audit_dihedral_conditioning
    points,proxy=source()
    r=audit_dihedral_conditioning(lambda x,p:oracle(x,p,nonfinite=True),{'saved':points},[proxy])
    assert r['cases']['saved']['proxies'][0]['qualification']=='NATIVE_NONFINITE_REVIEW'
    json.dumps(r,allow_nan=False)
    def fail(x,p):raise RuntimeError('EXPLICIT_FAKE_NATIVE_ERROR')
    r=audit_dihedral_conditioning(fail,{'saved':points},[proxy])
    assert r['cases']['saved']['proxies'][0]['baseline']['status']=='EXCEPTION'


def test_budget_and_mutating_callbacks_do_not_silently_pass():
    from nasolve.cif_dihedral_conditioning import audit_dihedral_conditioning
    points,proxy=source()
    with pytest.raises(ValueError,match='budget'):audit_dihedral_conditioning(oracle,{'saved':points},[proxy],max_pairs=3)
    def mutate(x,p):x[0][0]+=1.;return oracle(x,p)
    with pytest.raises(ValueError,match='mutated'):audit_dihedral_conditioning(mutate,{'saved':points},[proxy])


@pytest.mark.parametrize('defect',['index','repeated','weight','periodicity','alternate','nonfinite','empty'])
def test_invalid_selection_or_unsupported_proxy_parameters_are_refused(defect):
    from nasolve.cif_dihedral_conditioning import audit_dihedral_conditioning
    points,proxy=source()
    if defect=='index':proxy['i_seqs'][-1]=5
    if defect=='repeated':proxy['i_seqs'][-1]=0
    if defect=='weight':proxy['weight']=0.
    if defect=='periodicity':proxy['periodicity']=1.5
    if defect=='alternate':proxy['alt_angle_ideals']=[float('nan')]
    if defect=='nonfinite':points[0][0]=float('inf')
    with pytest.raises(ValueError):audit_dihedral_conditioning(oracle,{'saved':points},[] if defect=='empty' else [proxy])


_FAKE_DIHEDRAL_API=r'''
from types import SimpleNamespace as NS
from cctbx.array_family import flex
BIAS=False
TAMPER=False
def dihedral_proxy(**kwargs):return NS(**kwargs,sym_ops=None,limit=-1.,top_out=False,slack=0.)
class shared_dihedral_proxy(list):pass
class dihedral:
    def __init__(self,sites_cart,proxy):
        self.points=sites_cart;self.proxy=proxy;self.have_angle_model=True;self.angle_model=42.
    def residual(self):return self.proxy.weight*sum(v*v for i in self.proxy.i_seqs for v in self.points[i])
    def gradients(self):
        rows=[[2*self.proxy.weight*v for v in self.points[i]] for i in self.proxy.i_seqs]
        if BIAS:rows[0][0]+=1.
        return flex.vec3_double(rows)
def dihedral_residual_sum(sites_cart,proxies,gradient_array):
    global TAMPER
    if TAMPER:
        from pathlib import Path
        p=Path(__file__);p.write_bytes(p.read_bytes()+b'\n# EXPLICIT_FAKE_SOURCE_CHANGE\n');TAMPER=False
    total=0.
    for p in proxies:
        r=dihedral(sites_cart,p);total+=r.residual()
        for i,v in zip(p.i_seqs,r.gradients()):gradient_array[i]=tuple(a+b for a,b in zip(gradient_array[i],v))
    return total
'''


@pytest.mark.parametrize('mode',['correct','wrong_gradient','changed_manager','changed_membership','changed_api','changed_adapter','nondefault_function','timeout'])
def test_selected_native_worker_rebuilds_and_preserves_the_exact_manager(tmp_path,monkeypatch,mode):
    from hashlib import sha256
    import json,os,sys
    from pathlib import Path
    import nasolve.cif_dihedral_conditioning as audit
    import nasolve.cif_native_validation as native_module
    from tests.test_cif_fixed_geometry import worker_fixture,policy_inventory
    from tests.test_cif_fragment_restoration import fixture
    protected=tmp_path/'protected';protected.mkdir();_,model,_,native,_=fixture(protected);policy_inventory(native)
    dictionary=protected/'fake.cif';dictionary.write_text('data_comp_ZZZ\n_chem_comp.id ZZZ\n')
    seed=worker_fixture(tmp_path/'fake',native,'limit')
    (seed/'cctbx/array_family/flex.py').write_text('from fake_arrays import Vec\ndef vec3_double(values,fill=None):return Vec([fill]*values if isinstance(values,int) else values)\n')
    (seed/'cctbx/geometry_restraints/__init__.py').write_text(_FAKE_DIHEDRAL_API.replace('BIAS=False',f'BIAS={mode=="wrong_gradient"!r}').replace('TAMPER=False',f'TAMPER={mode=="changed_adapter"!r}'))
    proxy=source()[1]
    bootstrap='''
import json
from pathlib import Path
from types import SimpleNamespace as NS
from cctbx import geometry_restraints as gr
from cctbx.array_family import flex
report=json.loads(Path('expected_inventory.json').read_text())
if MODE=='changed_manager':report['restraint_policy']['secondary_structure_enabled']=True
sites=flex.vec3_double(report['geometry']['sites_cart_exact'])
class Geo:
    site_symmetry_table=NS(special_position_indices=lambda:[])
    angle_proxies=[];const_dihedral_proxies=[];chirality_proxies=[];planarity_proxies=[];parallelity_proxies=[]
    dihedral_proxies=gr.shared_dihedral_proxy([gr.dihedral_proxy(**PROXY)])
    def pair_proxies(self,sites_cart):return NS(bond_proxies=NS(simple=[],asu=[]))
geo=Geo()
if MODE=='changed_membership':geo.dihedral_proxies[0].angle_ideal+=1.
if MODE=='nondefault_function':geo.dihedral_proxies[0].top_out=True
raise SystemExit(0)
'''.replace('MODE',repr(mode)).replace('PROXY',repr(proxy))
    monkeypatch.setattr(native_module,'_NATIVE_WORKER',bootstrap)
    if mode=='timeout':monkeypatch.setattr(audit,'_WORKER','import time\ntime.sleep(30)\n')
    files=[('scitbx.lbfgs','scitbx/lbfgs.py'),('cctbx.geometry_restraints.flags','cctbx/geometry_restraints/flags.py'),
        ('cctbx.geometry_restraints.manager','cctbx/geometry_restraints/manager.py'),('cctbx.geometry_restraints.energies','cctbx/geometry_restraints/energies.py'),
        ('scitbx_lbfgs_ext','scitbx_lbfgs_ext.py'),('cctbx_geometry_restraints_ext','cctbx_geometry_restraints_ext.py')]
    sources=[{'module':name,'sha256':sha256((seed/path).read_bytes()).hexdigest()} for name,path in files]
    if mode=='changed_api':sources[0]['sha256']='0'*64
    exe=tmp_path/'bin/phenix.python';exe.parent.mkdir();exe.write_text('#!'+sys.executable+'\nimport runpy,sys,os\nsys.path.insert(0,os.getcwd())\nsys.argv=[a for a in sys.argv[1:] if a!="-B"]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');exe.chmod(0o755)
    points=native['geometry']['sites_cart_exact']
    r=audit.run_native_dihedral_conditioning(model,dictionary,[],native,{'saved':points},[proxy],sources,tmp_path/'out',exe,
        environment={**os.environ,'PYTHONPATH':str(seed)},phenix_version='EXPLICIT_FAKE',installation_root=tmp_path,timeout_seconds=1 if mode=='timeout' else 30)
    good=mode in {'correct','wrong_gradient'}
    assert r['status']==('REVIEW' if good else 'FAILED'),r
    assert r['source_preserved'] and r['frozen_inputs_preserved']
    work=Path(r['native_directory']);assert json.loads((work/'conditioning_receipt.json').read_text())==r
    assert not (work/'fake_optimizer_called').exists()
    if good:
        q=r['result'];assert q['captured_inventory_matches'] and q['analysis_completed']
        assert q['constraint_signature_before']==q['constraint_signature_after']
        assert q['numerical_controls']['well_conditioned']['sampled_derivatives_consistent'] is (mode=='correct')
        assert q['evaluation_pairs']<=3000 and len(q['installed_adapter_sources'])==2
    elif mode=='timeout':assert r['execution']['status']=='TIMED_OUT'
    else:
        fragment={'changed_manager':'Native manager changed','changed_membership':'membership changed','changed_api':'numerical sources changed',
            'changed_adapter':'source changed during audit','nondefault_function':'Unsupported nondefault'}[mode]
        assert fragment in r['error'],r
