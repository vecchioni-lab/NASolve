"""Separate single-restraint derivatives from native accumulation defects."""
from copy import deepcopy
import math
import pytest


def evaluate(points, proxy, *, broken=False, biased=False):
    """Analytic quadratic oracle; the audit does not implement this objective."""
    single=[0.]*(3*len(points));accumulated=single.copy();target=0.
    for side,key in enumerate(['i_seqs','j_seqs']):
        for offset,index in enumerate(proxy[key]):
            for axis,value in enumerate(points[index]):
                target+=proxy['weight']*value*value
                gradient=2*proxy['weight']*value
                single[3*index+axis]+=gradient
                if not broken or side==0 or offset<max(0,len(proxy['j_seqs'])-len(proxy['i_seqs'])):
                    accumulated[3*index+axis]+=gradient
    if biased:
        single[0]+=2.;accumulated[0]+=2.
    return {'single_target':target,'single_gradient':single,
            'accumulated_target':target,'accumulated_gradient':accumulated}


def source():
    points=[[.2+i*.3,.4-i*.1,.5+i*.2] for i in range(9)]
    proxy={'i_seqs':[0,1,2,3],'j_seqs':[4,5,6,7,8],
           'weight':2.7,'target_angle_deg':0.,'slack':0.,'limit':1.,'top_out':False,'origin_id':6}
    return points,proxy


@pytest.mark.parametrize('broken',[False,True])
def test_generic_accumulation_defect_is_localized_without_changing_restraints(broken):
    from nasolve.cif_parallelity_audit import audit_parallelities
    points,proxy=source();saved=deepcopy((points,proxy))
    report=audit_parallelities(lambda x,p:evaluate(x,p,broken=broken),{'endpoint':points},[proxy])
    assert report['analysis_completed'] and report['model_optimization']=='NOT_RUN'
    assert report['automatic_adoption'] is False and report['scientific_approval']=='NOT_RUN'
    assert (points,proxy)==saved
    case=report['cases']['endpoint']
    assert case['summary']['single_derivatives_consistent']
    assert case['summary']['accumulated_derivatives_consistent'] is (not broken)
    assert case['summary']['single_and_accumulated_gradients_agree'] is (not broken)
    assert case['summary']['swapped_gradients_consistent'] is (not broken)
    assert report['evaluation_pairs']<=report['max_evaluation_pairs']
    assert len(case['proxies'])==1 and len(report['toy_cases'])==3
    for row in [*case['proxies'],*report['toy_cases']]:
        assert row['original']['energy_agreement'] and row['swapped']['energy_agreement']
        for order in ['original','swapped']:
            assert len(row[order]['directions'])==3
            for direction in row[order]['directions']:
                assert [s['step'] for s in direction['samples']]==[1e-3,1e-4,1e-5,1e-6]


def test_wrong_single_restraint_gradient_cannot_be_blame_shifted_to_accumulation():
    from nasolve.cif_parallelity_audit import audit_parallelities
    points,proxy=source()
    report=audit_parallelities(lambda x,p:evaluate(x,p,biased=True),{'endpoint':points},[proxy])
    summary=report['cases']['endpoint']['summary']
    assert not summary['single_derivatives_consistent']
    assert not summary['accumulated_derivatives_consistent']
    assert summary['single_and_accumulated_gradients_agree']


def test_nonfinite_drift_and_energy_disagreement_remain_visible():
    from nasolve.cif_parallelity_audit import audit_parallelities
    points,proxy=source();calls=0
    def drift(x,p):
        nonlocal calls
        calls+=1;r=evaluate(x,p);r['single_target']+=calls*.001;return r
    r=audit_parallelities(drift,{'endpoint':points},[proxy])
    assert not r['cases']['endpoint']['summary']['baseline_repeats_consistent']
    assert not r['cases']['endpoint']['proxies'][0]['original']['energy_agreement']
    def bad(x,p):
        r=evaluate(x,p);r['single_gradient'][0]=float('nan');return r
    with pytest.raises(ValueError,match='finite'):
        audit_parallelities(bad,{'endpoint':points},[proxy])


def test_native_evaluation_budget_is_enforced():
    from nasolve.cif_parallelity_audit import audit_parallelities
    points,proxy=source()
    with pytest.raises(ValueError,match='budget'):
        audit_parallelities(evaluate,{'endpoint':points},[proxy],max_pairs=3)


@pytest.mark.parametrize('defect',['duplicate','index','few','weight','nonfinite','top_out'])
def test_unsupported_proxy_or_coordinate_inputs_are_refused(defect):
    from nasolve.cif_parallelity_audit import audit_parallelities
    points,proxy=source()
    if defect=='duplicate':proxy['i_seqs']=[0,0,2,3]
    if defect=='index':proxy['j_seqs'][-1]=len(points)
    if defect=='few':proxy['i_seqs']=[0,1]
    if defect=='weight':proxy['weight']=0.
    if defect=='nonfinite':points[0][0]=float('inf')
    if defect=='top_out':proxy['top_out']=True
    with pytest.raises(ValueError):audit_parallelities(evaluate,{'endpoint':points},[proxy])


def test_overlapping_plane_indices_accumulate_by_identity():
    from nasolve.cif_parallelity_audit import audit_parallelities
    points,proxy=source();proxy['j_seqs']=[1,4,5,6]
    report=audit_parallelities(evaluate,{'endpoint':points},[proxy])
    assert report['cases']['endpoint']['summary']['single_derivatives_consistent']
    assert report['cases']['endpoint']['summary']['single_and_accumulated_gradients_agree']


_FAKE_PLANE_API = r'''
from types import SimpleNamespace as NS
from cctbx.array_family import flex
BROKEN = False
TAMPER = False
def parallelity_proxy(**kw):return NS(**kw,sym_ops=None)
class shared_parallelity_proxy(list):pass
class parallelity:
    def __init__(self,sites_cart,proxy):self.points=sites_cart;self.proxy=proxy
    def residual(self):return self.proxy.weight*sum(v*v for i in self.proxy.i_seqs+self.proxy.j_seqs for v in self.points[i])
    def gradients(self):return flex.vec3_double([[2*self.proxy.weight*v for v in self.points[i]] for i in self.proxy.i_seqs+self.proxy.j_seqs])
def parallelity_residual_sum(sites_cart,proxies,gradient_array):
    global TAMPER
    if TAMPER:
        from pathlib import Path
        path=Path(__file__);path.write_bytes(path.read_bytes()+b'\n# EXPLICIT_FAKE_CHANGE\n');TAMPER=False
    total=0.
    for p in proxies:
        r=parallelity(sites_cart,p);total+=r.residual()
        for offset,(index,values) in enumerate(zip(p.i_seqs+p.j_seqs,r.gradients())):
            if BROKEN and offset>=len(p.i_seqs)+max(0,len(p.j_seqs)-len(p.i_seqs)):continue
            gradient_array[index]=tuple(a+b for a,b in zip(gradient_array[index],values))
    return total
'''


@pytest.mark.parametrize('mode',['correct','broken_accumulation','changed_manager','changed_api','changed_adapter','changed_snapshot','timeout'])
def test_installed_adapter_control_flow_is_checked_with_explicit_fakes(tmp_path,monkeypatch,mode):
    import hashlib,json,os,sys
    from pathlib import Path
    from types import SimpleNamespace as NS
    import nasolve.cif_parallelity_audit as audit
    import nasolve.cif_native_validation as native_module
    from nasolve.cif_gradient_audit import fixed_signature
    from tests.test_cif_fixed_geometry import worker_fixture,policy_inventory
    from tests.test_cif_fragment_restoration import fixture
    protected=tmp_path/'protected';protected.mkdir()
    _,model,_,native,_=fixture(protected);policy_inventory(native)
    dictionary=protected/'fake.cif';dictionary.write_text('data_comp_ZZZ\n_chem_comp.id ZZZ\n')
    seed=worker_fixture(tmp_path/'fake',native,'limit')
    (seed/'cctbx/array_family/flex.py').write_text('from fake_arrays import Vec\ndef vec3_double(values,fill=None):return Vec([fill]*values if isinstance(values,int) else values)\ndef size_t(v):return list(v)\n')
    (seed/'cctbx/geometry_restraints/flags.py').write_text('class flags:\n def __init__(self,default=False):self.parallelity=default\n')
    (seed/'cctbx/geometry_restraints/__init__.py').write_text(_FAKE_PLANE_API.replace('BROKEN = False',f'BROKEN = {mode=="broken_accumulation"!r}').replace('TAMPER = False',f'TAMPER = {mode=="changed_adapter"!r}'))
    (seed/'cctbx/geometry_restraints/parallelity.h').write_text('EXPLICIT_FAKE_HEADER\n')
    proxy={'i_seqs':[0,1,2],'j_seqs':[3,4,5,6],'weight':2.7,'target_angle_deg':0.,'slack':0.,'limit':1.,'top_out':False,'origin_id':4}
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
    angle_proxies=[];dihedral_proxies=[];const_dihedral_proxies=[];chirality_proxies=[];planarity_proxies=[]
    parallelity_proxies=gr.shared_parallelity_proxy([gr.parallelity_proxy(**PROXY)])
    def pair_proxies(self,sites_cart):return NS(bond_proxies=NS(simple=[],asu=[]))
    def energies_sites(self,sites_cart,flags,compute_gradients,normalization):
        assert flags.parallelity and compute_gradients and normalization is False
        gradient=flex.vec3_double(len(sites_cart),(0.,0.,0.))
        target=gr.parallelity_residual_sum(sites_cart,self.parallelity_proxies,gradient)
        return NS(target=target,gradients=gradient)
geo=Geo()
raise SystemExit(0)
'''.replace('MODE',repr(mode)).replace('PROXY',repr(proxy))
    monkeypatch.setattr(native_module,'_NATIVE_WORKER',bootstrap)
    if mode=='timeout':monkeypatch.setattr(audit,'_PARALLELITY_WORKER','import time\ntime.sleep(30)\n')
    files=[('scitbx.lbfgs','scitbx/lbfgs.py'),('cctbx.geometry_restraints.flags','cctbx/geometry_restraints/flags.py'),
           ('cctbx.geometry_restraints.manager','cctbx/geometry_restraints/manager.py'),('cctbx.geometry_restraints.energies','cctbx/geometry_restraints/energies.py'),
           ('scitbx_lbfgs_ext','scitbx_lbfgs_ext.py'),('cctbx_geometry_restraints_ext','cctbx_geometry_restraints_ext.py')]
    sources=[{'module':name,'sha256':hashlib.sha256((seed/path).read_bytes()).hexdigest()} for name,path in files]
    if mode=='changed_api':sources[0]['sha256']='0'*64
    fake=NS(pair_proxies=lambda **kw:NS(bond_proxies=NS(simple=[],asu=[])),parallelity_proxies=[NS(**proxy)],
            **{kind+'_proxies':[] for kind in ['angle','dihedral','const_dihedral','chirality','planarity']})
    signature=fixed_signature(fake,[]);points=native['geometry']['sites_cart_exact']
    baseline=evaluate(points,proxy,broken=mode=='broken_accumulation')
    captured={'target':baseline['accumulated_target'],'gradient':baseline['accumulated_gradient']}
    if mode=='changed_snapshot':captured['target']+=1.
    report=audit.run_native_parallelity_audit(model,[dictionary],[],native,{'full_precision':points,'pdb_rounded':points},
        {'full_precision':captured,'pdb_rounded':captured},sources,signature,tmp_path/'out',sys.executable,
        environment={**os.environ,'PYTHONPATH':str(seed)},phenix_version='EXPLICIT_FAKE',timeout_seconds=1 if mode=='timeout' else 30)
    good=mode in {'correct','broken_accumulation'}
    assert report['status']==('REVIEW' if good else 'FAILED'),report
    assert report['source_preserved'] and report['frozen_inputs_preserved']
    work=Path(report['native_directory']);assert not (work/'fake_optimizer_called').exists()
    assert json.loads((work/'parallelity_receipt.json').read_text())==report
    if good:
        q=report['result'];assert q['analysis_completed'] and q['captured_inventory_matches']
        assert len(q['installed_adapter_sources'])==2
        assert q['installed_parallelity_sources'][0]['status']=='RECORDED'
        assert q['installed_parallelity_sources'][1]['status']=='UNAVAILABLE'
        assert q['cases']['full_precision']['summary']['accumulated_derivatives_consistent'] is (mode=='correct')
        assert q['full_batch_comparisons']['full_precision']['gradient_agreement'] is (mode=='correct')
        assert q['evaluation_pairs']<7000
    elif mode=='timeout':
        assert report['execution']['status']=='TIMED_OUT'
    else:
        errors={'changed_manager':'Native manager changed','changed_api':'Native numerical sources changed',
                'changed_adapter':'Native numerical source changed','changed_snapshot':'Captured/native batch parallelity gradients differ'}
        assert errors[mode] in report['error']
