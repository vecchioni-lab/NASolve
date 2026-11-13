"""Independent derivatives for image transport and shared ASU variables."""
import math

import pytest

from nasolve.topostitch_transport import (
    CartesianImage, IDENTITY_IMAGE, crystallographic_image,
    expand_sites, accumulate_image_gradients,
)


@pytest.mark.parametrize('cell,group,operator',[
    ((10,11,12,80,75,20),'P 1','x+19,y-3,z+2'),
    ((10,10,40,90,90,90),'P 43','y,-x,z+1/4'),
    ((105.547,105.547,96.268,90,90,120),'R 3:H','-x+y+2/3,-x+1/3,z+1/3'),
    ((10,11,12,90,90,90),'I 2 2 2','x+1/2,y+1/2,z+1/2'),
])
def test_image_matches_fractional_crystallographic_path_and_inverse(cell,group,operator):
    gemmi=pytest.importorskip('gemmi')
    image=crystallographic_image(cell,group,operator)
    unit=gemmi.UnitCell(*cell);op=gemmi.Op(operator)
    points=[(0.,0.,0.),(1.2,-3.5,8.7),(123.4,-213.2,78.1)]
    for xyz in points:
        f=unit.fractionalize(gemmi.Position(*xyz))
        expected=tuple(unit.orthogonalize(gemmi.Fractional(*op.apply_to_xyz(list(f)))))
        assert image.apply(xyz)==pytest.approx(expected,abs=1e-10)
        assert image.inverse().apply(image.apply(xyz))==pytest.approx(xyz,abs=1e-10)
    assert math.dist(*map(image.apply,points[:2]))==pytest.approx(math.dist(*points[:2]),abs=1e-10)


def test_repeated_asu_index_accumulates_both_sides_of_self_image_contact():
    # No crystallographic dependency: exercise R versus R^T and shared variables.
    mate=CartesianImage(((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.)),(3.,2.,5.))
    refs=((0,IDENTITY_IMAGE),(0,mate))
    points=[(2.,-.5,1.7),(8.,9.,10.)]
    def energy(p):
        a,b=expand_sites(p,refs)
        return sum((x-y)**2 for x,y in zip(a,b))
    a,b=expand_sites(points,refs);delta=tuple(2*(x-y) for x,y in zip(a,b))
    gradient=accumulate_image_gradients(len(points),refs,[delta,tuple(-v for v in delta)])
    assert gradient[1]==(0.,0.,0.)
    for i in range(len(points)):
        for axis in range(3):
            h=1e-5;left=[list(p) for p in points];right=[list(p) for p in points]
            left[i][axis]-=h;right[i][axis]+=h
            assert gradient[i][axis]==pytest.approx((energy(right)-energy(left))/(2*h),abs=1e-8)
    # A constant translation contributes no Jacobian term.
    assert mate.pullback((1.,2.,3.))==(2.,-1.,3.)
    assert accumulate_image_gradients(1,[(0,IDENTITY_IMAGE)]*3,[(1e16,0,0),(1,0,0),(-1e16,0,0)])==((1.,0.,0.),)


@pytest.mark.parametrize('rotation,translation',[
    (((2,0,0),(0,1,0),(0,0,1)),(0,0,0)),
    (((-1,0,0),(0,1,0),(0,0,1)),(0,0,0)),
    (((1,0,0),(0,1,0)),(0,0,0)),
    (((1,0,0),(0,1,0),(0,0,1)),(0,float('nan'),0)),
    (((True,0,0),(0,1,0),(0,0,1)),(0,0,0)),
])
def test_nonphysical_or_nonfinite_transport_is_rejected(rotation,translation):
    with pytest.raises(ValueError):CartesianImage(rotation,translation)


def test_checked_factory_rejects_nonmember_operation():
    pytest.importorskip('gemmi')
    for op in ('-x,-y,z','x+1/2,y,z','garbage'):
        with pytest.raises(ValueError):crystallographic_image((10,10,10,90,90,90),'P 1',op)


@pytest.mark.parametrize('refs,gradients',[
    ([(1,IDENTITY_IMAGE)],[(1,2,3)]),
    ([(True,IDENTITY_IMAGE)],[(1,2,3)]),
    ([(0,IDENTITY_IMAGE)],[]),
    ([(0,IDENTITY_IMAGE)],[(1,2,float('inf'))]),
    ([(0,'not an image')],[(1,2,3)]),
])
def test_invalid_binding_cannot_silently_drop_or_redirect_a_gradient(refs,gradients):
    with pytest.raises(ValueError):accumulate_image_gradients(1,refs,gradients)


def test_transport_detaches_caller_owned_matrices():
    rotation=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]];translation=[1.,2.,3.]
    image=CartesianImage(rotation,translation);rotation[0][0]=9.;translation[0]=9.
    assert image.apply((1.,1.,1.))==(2.,3.,4.)
    with pytest.raises(ValueError):image.apply((0.,float('nan'),0.))
    with pytest.raises(ValueError):accumulate_image_gradients(True,[],[])
