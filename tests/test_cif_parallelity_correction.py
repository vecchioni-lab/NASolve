"""Complete native plane accumulation must preserve the objective and policy."""
from copy import deepcopy
import math
from types import SimpleNamespace as NS
import pytest


class Vec(list):
    def __init__(self, values, fill=None):super().__init__([fill]*values if isinstance(values,int) else values)
    def as_double(self):return [v for point in self for v in point]


class PlaneAPI:
    def __init__(self,broken=True,defect=None):self.broken=broken;self.defect=defect
    def parallelity(self,sites_cart,proxy):
        def target():return proxy.weight*sum((i+1)*(axis+2)*v*v for i in proxy.i_seqs+proxy.j_seqs for axis,v in enumerate(sites_cart[i]))+proxy.target_angle_deg
        def gradient():
            result=[[2*proxy.weight*(i+1)*(axis+2)*v for axis,v in enumerate(sites_cart[i])] for i in proxy.i_seqs+proxy.j_seqs]
            if self.defect=='gradient':result[0][0]=float('nan')
            if self.defect=='count':result.pop()
            return result
        return NS(residual=target,gradients=gradient)
    def parallelity_residual_sum(self,sites_cart,proxies,gradient_array):
        total=0.
        for p in proxies:
            r=self.parallelity(sites_cart,p);total+=r.residual()
            for offset,(index,values) in enumerate(zip(p.i_seqs+p.j_seqs,r.gradients())):
                if self.broken and offset>=len(p.i_seqs)+max(0,len(p.j_seqs)-len(p.i_seqs)):continue
                gradient_array[index]=tuple(a+b for a,b in zip(gradient_array[index],values))
        return total+(1. if self.defect=='residual' else 0.)


def fixture(broken=True):
    points=[[.2+i*.3,.4-i*.1,.5+i*.2] for i in range(9)]
    p=NS(i_seqs=[0,1,2,3],j_seqs=[4,5,6,7,8],weight=2.7,target_angle_deg=7.3,
         slack=.2,limit=1.4,top_out=False,origin_id=6,sym_ops=None)
    gr=PlaneAPI(broken);flex=NS(vec3_double=Vec)
    plane=Vec(len(points),(0.,0.,0.));target=gr.parallelity_residual_sum(points,[p],plane)
    other=[.7*(axis+1)*value for point in points for axis,value in enumerate(point)]
    raw=[a+b for a,b in zip(other,plane.as_double())]
    return points,p,gr,flex,raw,other,target


@pytest.mark.parametrize('broken',[False,True])
@pytest.mark.parametrize('swapped',[False,True])
def test_repaired_gradient_matches_independent_full_objective_derivatives(broken,swapped):
    from nasolve.cif_parallelity_correction import correct_parallelity_gradient
    points,p,gr,flex,_,other,_=fixture(broken)
    if swapped:p.i_seqs,p.j_seqs=p.j_seqs,p.i_seqs
    native=Vec(len(points),(0.,0.,0.));target=gr.parallelity_residual_sum(points,[p],native)
    raw=[a+b for a,b in zip(other,native.as_double())];original=deepcopy((points,vars(p),raw))
    report=correct_parallelity_gradient(gr,flex,[p],points,raw,native_residual=target)
    def energy(x):return .35*sum((axis+1)*v*v for point in x for axis,v in enumerate(point))+gr.parallelity(x,p).residual()
    for index in range(len(points)):
        for axis in range(3):
            plus=deepcopy(points);minus=deepcopy(points);plus[index][axis]+=1e-5;minus[index][axis]-=1e-5
            numerical=(energy(plus)-energy(minus))/(2e-5)
            assert report['gradient'][3*index+axis]==pytest.approx(numerical,rel=1e-7,abs=1e-7)
    assert report['energy_agreement'] and report['native_plane_residual']==target
    assert (points,vars(p),raw)==original
    if not broken:assert report['gradient']==raw
    assert report['correction_norm']>0 if broken else report['correction_norm']==0.


def test_shared_atoms_and_multiple_proxies_accumulate_every_contribution():
    from nasolve.cif_parallelity_correction import correct_parallelity_gradient
    points,p,gr,flex,_,_,_=fixture();p.j_seqs=[1,4,5,6]
    p2=deepcopy(p);p2.i_seqs=[3,4,6];p2.j_seqs=[0,7,8];p2.weight=.5
    raw=Vec(len(points),(0.,0.,0.));target=gr.parallelity_residual_sum(points,[p,p2],raw)
    r=correct_parallelity_gradient(gr,flex,[p,p2],points,raw.as_double(),native_residual=target)
    correct=PlaneAPI(False);truth=Vec(len(points),(0.,0.,0.));correct.parallelity_residual_sum(points,[p,p2],truth)
    assert r['gradient']==pytest.approx(truth.as_double()) and r['proxy_count']==2


def test_no_planes_is_a_noop_without_native_kernel_calls():
    from nasolve.cif_parallelity_correction import correct_parallelity_gradient
    class NoCalls:
        def __getattr__(self,name):raise AssertionError(name)
    raw=[.1,.2,.3];r=correct_parallelity_gradient(NoCalls(),NoCalls(),[],[[0.,0.,0.]],raw,native_residual=0.)
    assert r['gradient']==raw and r['proxy_count']==0 and r['correction_norm']==0.


@pytest.mark.parametrize('defect',['gradient','count','residual','symmetry','index','raw_nonfinite','raw_count'])
def test_unsupported_or_inconsistent_inputs_cannot_return_a_corrected_gradient(defect):
    from nasolve.cif_parallelity_correction import correct_parallelity_gradient
    points,p,gr,flex,raw,_,target=fixture()
    if defect in {'gradient','count','residual'}:gr.defect=defect
    if defect=='symmetry':p.sym_ops=['x+1,y,z']
    if defect=='index':p.j_seqs[-1]=len(points)
    if defect=='raw_nonfinite':raw[0]=float('nan')
    if defect=='raw_count':raw.pop()
    with pytest.raises(ValueError):correct_parallelity_gradient(gr,flex,[p],points,raw,native_residual=target)


def test_owned_native_evaluation_keeps_native_energy_and_objects_unchanged():
    from nasolve.cif_parallelity_correction import evaluate_fixed_native
    points,p,gr,flex,raw,_,target=fixture();energy=NS(target=target+123.,gradients=Vec([raw[i:i+3] for i in range(0,len(raw),3)]),parallelity_residual_sum=target,n_parallelity_proxies=1)
    saved=deepcopy(energy);calls=[]
    def native(**kw):calls.append(kw);return energy
    geo=NS(parallelity_proxies=[p],energies_sites=native)
    r=evaluate_fixed_native(geo,points,NS(parallelity=True),gr,flex)
    assert r['target']==energy.target==saved.target and energy.gradients==saved.gradients
    assert r['parallelity_correction']['correction_norm']>0 and calls[0]['normalization'] is False
    r=evaluate_fixed_native(geo,points,NS(parallelity=False),gr,flex)
    assert r['gradient']==raw and r['parallelity_correction']['applied'] is False


@pytest.mark.parametrize('mode',['corrected','already_fixed','biased_single','changed_manager','changed_api','changed_adapter','changed_cpp','changed_baseline','timeout'])
def test_source_pinned_worker_validates_fresh_corrected_derivatives(tmp_path,monkeypatch,mode):
    import hashlib,json,os,sys
    from pathlib import Path
    import nasolve.cif_parallelity_correction as correction
    import nasolve.cif_native_validation as native_module
    from nasolve.cif_gradient_audit import fixed_signature
    from tests.test_cif_fixed_geometry import worker_fixture,policy_inventory
    from tests.test_cif_fragment_restoration import fixture as model_fixture
    from tests.test_cif_parallelity_audit import _FAKE_PLANE_API,evaluate as plane_evaluate
    protected=tmp_path/'protected';protected.mkdir();_,model,_,native,_=model_fixture(protected);policy_inventory(native)
    dictionary=protected/'fake.cif';dictionary.write_text('data_comp_ZZZ\n_chem_comp.id ZZZ\n')
    seed=worker_fixture(tmp_path/'fake',native,'limit');kinds=['bond','angle','dihedral','chirality','planarity','nonbonded']
    (seed/'cctbx/array_family/flex.py').write_text('from fake_arrays import Vec\ndef vec3_double(values,fill=None):return Vec([fill]*values if isinstance(values,int) else values)\ndef size_t(v):return list(v)\n')
    (seed/'cctbx/geometry_restraints/flags.py').write_text('class flags:\n def __init__(self,default=False):\n'+''.join(f'  self.{k}=default\n' for k in kinds+['parallelity']))
    api=_FAKE_PLANE_API.replace('BROKEN = False',f'BROKEN = {mode!="already_fixed"!r}')
    if mode=='biased_single':api=api.replace('2*self.proxy.weight*v','2*self.proxy.weight*v+3.')
    (seed/'cctbx/geometry_restraints/__init__.py').write_text(api)
    cpp=[]
    for name in ['parallelity.h','parallelity_bpl.cpp']:
        path=seed/'cctbx/geometry_restraints'/name;path.write_text('EXPLICIT_FAKE_'+name+'\n');data=path.read_bytes()
        cpp.append({'anchor':'native_geometry_module','path':name,'status':'RECORDED','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    if mode=='changed_cpp':cpp[0]['sha256']='0'*64
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
        assert compute_gradients and normalization is False
        coefficient=sum(i+1 for i,k in enumerate(KINDS) if getattr(flags,k))
        gradient=flex.vec3_double(len(sites_cart),(0.,0.,0.));parallel=0.
        if flags.parallelity:parallel=gr.parallelity_residual_sum(sites_cart,self.parallelity_proxies,gradient)
        for i,point in enumerate(sites_cart):gradient[i]=tuple(a+2*coefficient*v for a,v in zip(gradient[i],point))
        return NS(target=coefficient*sum(v*v for p in sites_cart for v in p)+parallel,gradients=gradient,
                  parallelity_residual_sum=parallel,n_parallelity_proxies=len(self.parallelity_proxies) if flags.parallelity else None)
geo=Geo()
raise SystemExit(0)
'''.replace('MODE',repr(mode)).replace('PROXY',repr(proxy)).replace('KINDS',repr(kinds))
    monkeypatch.setattr(native_module,'_NATIVE_WORKER',bootstrap)
    if mode=='timeout':monkeypatch.setattr(correction,'_CORRECTION_WORKER','import time\ntime.sleep(30)\n')
    source_files=[('scitbx.lbfgs','scitbx/lbfgs.py'),('cctbx.geometry_restraints.flags','cctbx/geometry_restraints/flags.py'),
        ('cctbx.geometry_restraints.manager','cctbx/geometry_restraints/manager.py'),('cctbx.geometry_restraints.energies','cctbx/geometry_restraints/energies.py'),
        ('scitbx_lbfgs_ext','scitbx_lbfgs_ext.py'),('cctbx_geometry_restraints_ext','cctbx_geometry_restraints_ext.py')]
    fingerprint=lambda files:[{'module':name,'sha256':hashlib.sha256((seed/path).read_bytes()).hexdigest()} for name,path in files]
    sources=fingerprint(source_files);adapters=fingerprint([('cctbx.geometry_restraints','cctbx/geometry_restraints/__init__.py'),('cctbx.array_family.flex','cctbx/array_family/flex.py')])
    if mode=='changed_api':sources[0]['sha256']='0'*64
    if mode=='changed_adapter':adapters[0]['sha256']='0'*64
    points=native['geometry']['sites_cart_exact'];p=plane_evaluate(points,proxy,broken=mode!='already_fixed')
    manual=plane_evaluate(points,proxy)['single_gradient']
    if mode=='biased_single':
        for side,key in enumerate(['i_seqs','j_seqs']):
            for offset,index in enumerate(proxy[key]):
                for axis in range(3):
                    manual[3*index+axis]+=3.
                    if side==0 or offset<max(0,len(proxy['j_seqs'])-len(proxy['i_seqs'])):p['accumulated_gradient'][3*index+axis]+=3.
    full=[2*21*v+g for point,gvalues in zip(points,[p['accumulated_gradient'][i:i+3] for i in range(0,len(p['accumulated_gradient']),3)]) for v,g in zip(point,gvalues)]
    refs={label:{'target':21*sum(v*v for p in points for v in p)+p['accumulated_target'],'gradient_norm':math.sqrt(math.fsum(v*v for v in full))} for label in ['initial','full_precision','pdb_rounded']}
    if mode=='changed_baseline':refs['initial']['target']+=1.
    captured={label:{'accumulated_residual':p['accumulated_target'],'accumulated_gradient':p['accumulated_gradient'],'manual_gradient':manual} for label in ['full_precision','pdb_rounded']}
    fake=NS(pair_proxies=lambda **kw:NS(bond_proxies=NS(simple=[],asu=[])),parallelity_proxies=[NS(**proxy)],
            **{kind+'_proxies':[] for kind in ['angle','dihedral','const_dihedral','chirality','planarity']})
    signature=fixed_signature(fake,[])
    r=correction.run_native_correction_audit(model,[dictionary],[],native,{label:points for label in refs},refs,captured,[0],sources,adapters,cpp,signature,
        tmp_path/'out',sys.executable,environment={**os.environ,'PYTHONPATH':str(seed)},phenix_version='EXPLICIT_FAKE',timeout_seconds=1 if mode=='timeout' else 30)
    good=mode in {'corrected','already_fixed','biased_single'}
    assert r['status']==('REVIEW' if good else 'FAILED'),r
    assert r['source_preserved'] and r['frozen_inputs_preserved']
    work=Path(r['native_directory']);assert not (work/'fake_optimizer_called').exists()
    assert json.loads((work/'correction_receipt.json').read_text())==r
    if good:
        q=r['result'];assert q['analysis_completed'] and q['captured_inventory_matches'] and q['evaluation_calls']<=5500
        assert q['correction_statistics']['max_energy_change']==0.
        assert q['correction_qualification']==('DERIVATIVE_REVIEW' if mode=='biased_single' else 'SAMPLED_NATIVE_DERIVATIVES_PASS')
        assert q['constraint_signature_before']==q['constraint_signature_after']==signature
    elif mode=='timeout':assert r['execution']['status']=='TIMED_OUT'
    else:
        messages={'changed_manager':'Native manager changed','changed_api':'Native numerical sources changed',
            'changed_adapter':'Native adapter sources changed','changed_cpp':'Installed plane source changed','changed_baseline':'Captured native full-objective baseline differs'}
        assert messages[mode] in r['error']
