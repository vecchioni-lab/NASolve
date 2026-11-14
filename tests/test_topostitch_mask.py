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
