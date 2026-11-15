"""A reduced coordinate vector must never silently move fixed ASU atoms."""
import math
import pytest

from nasolve.topostitch_transport import CoordinateMask


def test_mask_preserves_explicit_order_and_exact_fixed_coordinates():
    points=[(1.,2.,3.),(4.,5.,6.),(7.,8.,9.)]
    mask=CoordinateMask(points,[2,0],0.5)
    points[1]=(99.,99.,99.)
    delta=[.1,.2,.3,-.2,0.,.1]
    moved=mask.expand(delta)
    assert moved[1]==(4.,5.,6.)
    assert moved[2]==pytest.approx((7.1,8.2,9.3))
    assert mask.displacements(moved)==pytest.approx(delta)
    assert mask.project([(1.,2.,3.),(4.,5.,6.),(7.,8.,9.)])==(7.,8.,9.,1.,2.,3.)
    with pytest.raises(ValueError,match='Fixed'):
        mask.displacements([moved[0],(4.,5.,6.000001),moved[2]])


@pytest.mark.parametrize('indices,bound', [([],1),([0,0],1),([3],1),([True],1),([-1],1),([0],0),([0],float('inf')),([0],True)])
def test_invalid_mask_is_rejected(indices,bound):
    with pytest.raises(ValueError):CoordinateMask([(0.,0.,0.)]*3,indices,bound)


def test_mask_rejects_wrong_shapes_nonfinite_and_excess_motion():
    m=CoordinateMask([(1.,2.,3.),(4.,5.,6.)],[0],.1)
    for delta in ([0,0],[0,0,0,0],[0,float('nan'),0],[0,0,.100001],[.09,.09,0]):
        with pytest.raises(ValueError):m.expand(delta)
    with pytest.raises(ValueError):m.project([(1.,2.,3.)])
    with pytest.raises(ValueError):m.project([(1.,2.,3.),(0.,float('nan'),0.)])


def test_projected_gradient_matches_independent_masked_energy():
    m=CoordinateMask([(1.,2.,3.),(4.,5.,6.),(7.,8.,9.)],[2,0],1.)
    delta=[.1,-.2,.3,-.1,.2,-.3]
    def energy(x):
        # The moving atom interacts with a fixed atom: its contribution must
        # remain in the target while only selected derivatives are projected.
        a,b,c=m.expand(x)
        return sum((u-v)**2 for u,v in zip(a,b))+sum((u-v)**2 for u,v in zip(c,a))
    a,b,c=m.expand(delta)
    full=[tuple(2*(u-v)+2*(u-w) for u,v,w in zip(a,b,c)),
          tuple(2*(u-v) for u,v in zip(b,a)),tuple(2*(u-v) for u,v in zip(c,a))]
    g=m.project(full)
    for i in range(len(delta)):
        plus=delta.copy();minus=delta.copy();plus[i]+=1e-5;minus[i]-=1e-5
        assert g[i]==pytest.approx((energy(plus)-energy(minus))/(2e-5),abs=1e-8)



def tapered_motion(*, indices=(2,0), bound=20.):
    from nasolve.topostitch_transport import TaperedMotion
    return TaperedMotion(CoordinateMask(((2.,1.,-1.),(8.,9.,10.),(-3.,2.,4.)),indices,bound),
                         (1.,-.5,2.),(.25,0.,1.))


def test_tapered_motion_keeps_exact_zero_fixed_points_and_mask_order():
    motion=tapered_motion();mask=motion.mask
    assert motion.displacements([0.]*6)==(0.,)*6
    parameters=(0.,0.,90.,.2,-.3,.1)
    actual=mask.expand(motion.displacements(parameters))
    assert actual[1]==mask.reference[1]
    # Independently known z rotation about the explicit pivot, with the full
    # angle at atom2 and a quarter-angle at atom0. Translation tapers as well.
    for index,weight in ((0,.25),(2,1.)):
        x,y,z=(a-b for a,b in zip(mask.reference[index],motion.origin));a=math.pi/2*weight
        expected=(math.cos(a)*x-math.sin(a)*y+1+weight*.2,
                  math.sin(a)*x+math.cos(a)*y-.5-weight*.3,z+2+weight*.1)
        assert actual[index]==pytest.approx(expected,abs=1e-14)
    assert motion.displacements(parameters)[:3]==pytest.approx(tuple(x-y for x,y in zip(actual[2],mask.reference[2])))


@pytest.mark.parametrize('parameters',[(0.,)*6,(1e-9,-2e-9,3e-9,.2,-.1,.3),(.2,-.15,.1,.3,-.2,.1),(70.,-30.,25.,1.,-2.,3.)])
def test_tapered_motion_gradient_matches_independent_coupled_energy(parameters):
    motion=tapered_motion();mask=motion.mask
    def evaluate(q):
        a,b,c=mask.expand(motion.displacements(q))
        return sum((x-y)**2 for x,y in zip(a,b))+3*sum((x-y)**2 for x,y in zip(c,a))
    a,b,c=mask.expand(motion.displacements(parameters))
    full=(tuple(2*(x-y)+6*(x-z) for x,y,z in zip(a,b,c)),
          tuple(2*(x-y) for x,y in zip(b,a)),tuple(6*(x-y) for x,y in zip(c,a)))
    gradient=motion.pullback(parameters,mask.project(full))
    for h in (1e-3,1e-4):
        for k in range(6):
            plus=list(parameters);minus=list(parameters);plus[k]+=h;minus[k]-=h
            assert gradient[k]==pytest.approx((evaluate(plus)-evaluate(minus))/(2*h),abs=2e-7)


def test_tapered_motion_equal_weights_preserve_internal_geometry_and_detach_inputs():
    from nasolve.topostitch_transport import TaperedMotion
    origin=[1.,2.,3.];weights=[.5,.5,0.]
    mask=CoordinateMask(((3.,2.,1.),(7.,8.,9.),(20.,20.,20.)),(1,0),10.)
    motion=TaperedMotion(mask,origin,weights);origin[0]=99.;weights[0]=0.
    moved=mask.expand(motion.displacements((20.,-10.,5.,1.,2.,3.)))
    assert math.dist(moved[0],moved[1])==pytest.approx(math.dist(*mask.reference[:2]),abs=1e-13)
    assert moved[2]==mask.reference[2] and motion.origin==(1.,2.,3.) and motion.weights==(.5,.5,0.)
    with pytest.raises(AttributeError):motion.origin=(0.,0.,0.)


@pytest.mark.parametrize('weights',[(1.,0.),(.25,0.,0.),(.25,.1,1.),(-.1,0.,1.),(.25,0.,1.01),(True,0.,1.),(.25,0.,float('nan'))])
def test_tapered_motion_refuses_incomplete_or_leaking_weights(weights):
    from nasolve.topostitch_transport import TaperedMotion
    with pytest.raises(ValueError):TaperedMotion(CoordinateMask(((0.,0.,0.),)*3,(2,0),1.),(0.,0.,0.),weights)


@pytest.mark.parametrize('parameters',[(0.,)*5,(0.,)*7,(True,0.,0.,0.,0.,0.),(float('nan'),0.,0.,0.,0.,0.),(0.,0.,0.,float('inf'),0.,0.)])
def test_tapered_motion_refuses_bad_parameters(parameters):
    motion=tapered_motion()
    with pytest.raises(ValueError):motion.displacements(parameters)
    with pytest.raises(ValueError):motion.pullback(parameters,(0.,)*6)


def test_tapered_motion_reuses_motion_bound_in_both_directions():
    motion=tapered_motion(bound=.1)
    for parameters in ((0.,0.,0.,.2,0.,0.),(0.,0.,90.,0.,0.,0.)):
        with pytest.raises(ValueError,match='bound'):motion.displacements(parameters)
        with pytest.raises(ValueError,match='bound'):motion.pullback(parameters,(0.,)*6)
    with pytest.raises(ValueError):motion.pullback((0.,)*6,(0.,)*3)
    with pytest.raises(ValueError):motion.pullback((0.,)*6,(float('inf'),0.,0.,0.,0.,0.))


def test_tapered_motion_rejects_invalid_origin_mask_and_nonfinite_arithmetic():
    from nasolve.topostitch_transport import TaperedMotion
    with pytest.raises(ValueError):TaperedMotion(None,(0.,0.,0.),(1.,))
    with pytest.raises(ValueError):TaperedMotion(CoordinateMask(((0.,0.,0.),),(0,),1.),(0.,float('inf'),0.),(1.,))
    motion=TaperedMotion(CoordinateMask(((1e308,0.,0.),),(0,),1.),(-1e308,0.,0.),(1.,))
    with pytest.raises(ValueError):motion.displacements((0.,0.,1.,0.,0.,0.))
