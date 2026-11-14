"""Both plane roles must differentiate the same untouched native energy."""
from copy import deepcopy
from types import SimpleNamespace as NS
import math
import pytest
from tests.test_cif_parallelity_correction import PlaneAPI,Vec,fixture


class OrderAPI(PlaneAPI):
    def __init__(self,broken=True,flip=True,defect=None,isotropic=False):super().__init__(broken,defect);self.flip=flip;self.isotropic=isotropic
    def parallelity_proxy(self,*,i_seqs,j_seqs,proxy=None,**kw):
        values=vars(proxy).copy() if proxy else {'sym_ops':None,**kw}
        values.update(i_seqs=list(i_seqs),j_seqs=list(j_seqs))
        if self.defect=='metadata':values['weight']+=1.
        return NS(**values)
    def parallelity(self,sites_cart,proxy):
        base=super().parallelity(sites_cart,proxy)
        if self.isotropic:
            base=NS(residual=lambda:proxy.weight*sum(v*v for i in proxy.i_seqs+proxy.j_seqs for v in sites_cart[i]),
                    gradients=lambda:[[2*proxy.weight*v for v in sites_cart[i]] for i in proxy.i_seqs+proxy.j_seqs])
        def gradient():
            rows=deepcopy(base.gradients())
            if self.flip:
                for i in range(len(proxy.i_seqs),len(rows)):rows[i]=[-v for v in rows[i]]
            if self.defect=='first':rows[0][0]+=3.
            return rows
        def residual():return base.residual()+(1. if self.defect=='swapped_residual' and proxy.i_seqs[0]>proxy.j_seqs[0] else 0.)
        return NS(residual=residual,gradients=gradient)


@pytest.mark.parametrize('broken',[False,True])
@pytest.mark.parametrize('flip',[False,True])
@pytest.mark.parametrize('swapped',[False,True])
def test_both_first_plane_blocks_match_full_derivatives_and_preserve_metadata(broken,flip,swapped):
    from nasolve.cif_parallelity_correction import correct_parallelity_gradient
    points,p,_,flex,_,other,_=fixture();p.top_out=True
    if swapped:p.i_seqs,p.j_seqs=p.j_seqs,p.i_seqs
    api=OrderAPI(broken,flip);buffer=Vec(len(points),(0.,0.,0.));target=api.parallelity_residual_sum(points,[p],buffer)
    raw=[a+b for a,b in zip(other,buffer.as_double())];saved=deepcopy((points,vars(p),raw))
    r=correct_parallelity_gradient(api,flex,[p],points,raw,native_residual=target,plane_order_safe=True)
    oracle=PlaneAPI(False)
    def energy(x):return .35*sum((axis+1)*v*v for point in x for axis,v in enumerate(point))+oracle.parallelity(x,p).residual()
    for index in range(len(points)):
        for axis in range(3):
            plus=deepcopy(points);minus=deepcopy(points);plus[index][axis]+=1e-5;minus[index][axis]-=1e-5
            assert r['gradient'][3*index+axis]==pytest.approx((energy(plus)-energy(minus))/(2e-5),rel=1e-7,abs=1e-7)
    assert r['policy_id']=='native-parallelity-both-first-planes-v1' and r['energy_agreement']
    assert (points,vars(p),raw)==saved
    if not broken and not flip:assert r['gradient']==raw


def test_order_safe_correction_keeps_overlapping_contributions_and_legacy_mode():
    from nasolve.cif_parallelity_correction import correct_parallelity_gradient
    points,p,_,flex,_,_,_=fixture();p.j_seqs=[1,4,5,6];p2=deepcopy(p);p2.i_seqs=[3,4,6];p2.j_seqs=[0,7,8]
    api=OrderAPI();buffer=Vec(len(points),(0.,0.,0.));target=api.parallelity_residual_sum(points,[p,p2],buffer)
    old=correct_parallelity_gradient(api,flex,[p,p2],points,buffer.as_double(),native_residual=target)
    new=correct_parallelity_gradient(api,flex,[p,p2],points,buffer.as_double(),native_residual=target,plane_order_safe=True)
    truth=Vec(len(points),(0.,0.,0.));PlaneAPI(False).parallelity_residual_sum(points,[p,p2],truth)
    assert new['gradient']==pytest.approx(truth.as_double()) and new['native_complete_plane_gradient']==old['plane_gradient']
    assert new['plane_order_difference_norm']>0.


@pytest.mark.parametrize('defect',['metadata','swapped_residual'])
def test_changed_swapped_copy_cannot_qualify_a_correction(defect):
    from nasolve.cif_parallelity_correction import correct_parallelity_gradient
    points,p,_,flex,_,_,_=fixture();api=OrderAPI(defect=defect)
    buffer=Vec(len(points),(0.,0.,0.));target=api.parallelity_residual_sum(points,[p],buffer)
    with pytest.raises(ValueError):correct_parallelity_gradient(api,flex,[p],points,buffer.as_double(),native_residual=target,plane_order_safe=True)


@pytest.mark.parametrize('defect',[None,'first'])
def test_per_plane_audit_exposes_original_sign_error_and_bad_first_derivatives(defect):
    from nasolve.cif_parallelity_correction import audit_plane_orders,plane_order_evaluator
    from nasolve.cif_parallelity_audit import toy_planes
    api=OrderAPI(defect=defect,isotropic=True);flex=NS(vec3_double=Vec,size_t=list)
    toy=toy_planes()[0]
    r=audit_plane_orders(plane_order_evaluator(api,flex),{'initial':toy['points']},[toy['proxy']])
    assert r['analysis_completed'] and r['evaluation_pairs']<=10000
    assert r['order_safe_qualified'] is (defect is None)
    assert not r['cases']['initial']['summary']['native_complete_derivatives_consistent']
    assert r['cases']['initial']['summary']['order_safe_derivatives_consistent'] is (defect is None)
    if defect is None:
        assert r['cases']['initial']['summary']['order_safe_swapped_gradients_consistent']
        assert all(row['rotation_energy_consistent'] and row['rotation_gradient_consistent'] for row in r['rotation_controls'])


def test_plane_order_audit_budget_is_enforced():
    from nasolve.cif_parallelity_correction import audit_plane_orders,plane_order_evaluator
    from nasolve.cif_parallelity_audit import toy_planes
    toy=toy_planes()[0]
    with pytest.raises(ValueError,match='budget'):
        audit_plane_orders(plane_order_evaluator(OrderAPI(),NS(vec3_double=Vec,size_t=list)),{'initial':toy['points']},[toy['proxy']],max_pairs=1)
