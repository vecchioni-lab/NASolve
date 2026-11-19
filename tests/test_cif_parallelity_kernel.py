"""Explicit kernel composition preserves existing forces, energy and caller state."""
from copy import deepcopy
from types import SimpleNamespace as NS
import math
import pytest
from tests.test_cif_parallelity_correction import PlaneAPI,Vec,fixture

class Buffer(Vec):
    def set_selected(self,indices,values):
        for i,v in zip(indices,values):self[i]=tuple(v)
    def id(self):return id(self)

class API(PlaneAPI):
    def parallelity_proxy(self,*,i_seqs,j_seqs,proxy):
        return NS(**{**vars(proxy),'i_seqs':list(i_seqs),'j_seqs':list(j_seqs)})
    def parallelity(self,sites_cart,proxy):
        original=super().parallelity(sites_cart,proxy)
        def gradients():
            rows=original.gradients()
            return [v if i<len(proxy.i_seqs) else [-x for x in v] for i,v in enumerate(rows)]
        return NS(residual=original.residual,gradients=gradients)

def setup():
    points,p,_,_,_,_,_=fixture()
    gr=API(broken=True);flex=NS(vec3_double=Buffer,size_t=list)
    return points,p,gr,flex

def adapted(gr,flex):
    from nasolve.cif_parallelity_kernel import ParallelityKernel
    return ParallelityKernel(gr,flex)

@pytest.mark.parametrize('swap',[False,True])
@pytest.mark.parametrize('shared',[False,True])
def test_kernel_adds_complete_forces_to_existing_buffer_without_changing_score(swap,shared):
    points,p,gr,flex=setup()
    if shared:p.j_seqs=[1,4,5,6]
    if swap:p.i_seqs,p.j_seqs=p.j_seqs,p.i_seqs
    second=deepcopy(p);second.weight=.4
    proxies=[p,second]
    initial=[(.7,.8,.9)]*len(points);buffer=Buffer(initial)
    frozen=deepcopy((points,[vars(p) for p in proxies]))
    original=gr.parallelity_residual_sum;kernel=adapted(gr,flex)
    assert gr.parallelity_residual_sum==original
    target=kernel(sites_cart=Buffer(points),proxies=proxies,gradient_array=buffer)
    truth=Buffer(initial);expected=PlaneAPI(False).parallelity_residual_sum(points,proxies,truth)
    assert target==expected
    assert buffer.as_double()==pytest.approx(truth.as_double(),abs=1e-12)
    assert (points,[vars(p) for p in proxies])==frozen
    assert kernel.statistics()['gradient_calls']==1

@pytest.mark.parametrize('buffer',[None,Buffer([])])
def test_energy_only_call_preserves_native_score_and_empty_buffer(buffer):
    points,p,gr,flex=setup();kernel=adapted(gr,flex)
    target=kernel(sites_cart=Buffer(points),proxies=[p],gradient_array=buffer)
    assert target==gr.parallelity(points,p).residual()
    assert buffer is None or buffer==[]
    assert kernel.statistics()['energy_only_calls']==1

@pytest.mark.parametrize('count',[0,4])
def test_no_planes_preserves_existing_buffer_including_empty_model(count):
    points=[[0.,1.,2.]]*count;buffer=Buffer([(.4,.5,.6)]*count)
    _,_,gr,flex=setup();kernel=adapted(gr,flex);saved=deepcopy(buffer)
    assert kernel(sites_cart=Buffer(points),proxies=[],gradient_array=buffer)==0.
    assert buffer==saved

@pytest.mark.parametrize('defect',['symmetry','unit_cell','buffer_length','incoming_nan','point_nan','native_nan','residual_disagreement','aliased_sites','zero_weight'])
def test_refusal_leaves_caller_buffer_untouched(defect):
    points,p,gr,flex=setup();sites=Buffer(points);buffer=Buffer([(.4,.5,.6)]*len(points));kw={}
    if defect=='symmetry':p.sym_ops=['x+1,y,z']
    if defect=='unit_cell':kw['unit_cell']=object()
    if defect=='buffer_length':buffer.pop()
    if defect=='incoming_nan':buffer[0]=(float('nan'),.5,.6)
    if defect=='point_nan':sites[0]=[float('nan'),0.,1.]
    if defect=='native_nan':gr.defect='gradient'
    if defect=='residual_disagreement':gr.defect='residual'
    if defect=='aliased_sites':buffer=sites
    if defect=='zero_weight':p.weight=0.
    before=[list(v) for v in buffer];kernel=adapted(gr,flex)
    with pytest.raises(ValueError):kernel(sites_cart=sites,proxies=[p],gradient_array=buffer,**kw)
    for a,b in zip(before,buffer):
        assert all(x==y or math.isnan(x) and math.isnan(y) for x,y in zip(a,b))
    assert kernel.statistics()['successful_calls']==0


def test_captured_original_kernel_does_not_recurse_after_explicit_caller_binding():
    points,p,gr,flex=setup();original=gr.parallelity_residual_sum;kernel=adapted(gr,flex)
    gr.parallelity_residual_sum=kernel
    try:
        buffer=Buffer([(0.,0.,0.)]*len(points))
        target=gr.parallelity_residual_sum(sites_cart=Buffer(points),proxies=[p],gradient_array=buffer)
        assert math.isfinite(target) and kernel.statistics()['successful_calls']==1
    finally:gr.parallelity_residual_sum=original


def test_statistics_are_a_snapshot_and_not_shared_mutable_state():
    points,p,gr,flex=setup();kernel=adapted(gr,flex)
    first=kernel.statistics();first['successful_calls']=999
    assert kernel.statistics()['successful_calls']==0
    kernel(sites_cart=Buffer(points),proxies=[p],gradient_array=None)
    assert first['successful_calls']==999 and kernel.statistics()['successful_calls']==1
