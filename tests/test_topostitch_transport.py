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


def bound_frame():
    from nasolve.topostitch_transport import ReferenceFrame
    return ReferenceFrame(('A','B'), (IDENTITY_IMAGE, CartesianImage(((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.)),(10.,20.,30.))), 'a'*64)


def test_complete_reference_frame_roundtrip_and_explicit_reordering():
    frame=bound_frame();source=((1.,2.,3.),(4.,5.,6.));labels=('A','B')
    represented=frame.to_representatives(source,source_labels=labels,context_sha256='a'*64)
    assert represented==((1.,2.,3.),(5.,24.,36.))
    assert frame.to_source(represented,atom_labels=labels,context_sha256='a'*64)==source
    reordered=frame.reindex([1,0]);assert reordered.atom_labels==('B','A')
    assert reordered.to_representatives(source,source_labels=labels,context_sha256='a'*64)==represented[::-1]
    assert reordered.to_source(represented[::-1],atom_labels=('B','A'),context_sha256='a'*64)==source
    assert reordered.reindex([1,0])==frame


def test_reference_frame_force_transport_excludes_translation_and_matches_derivatives():
    frame=bound_frame().reindex([1,0]);source=((1.,2.,3.),(4.,5.,6.))
    points=frame.to_representatives(source,source_labels=('A','B'),context_sha256='a'*64)
    gradient=frame.gradients_to_representatives(source,source_labels=('A','B'),context_sha256='a'*64)
    assert gradient==((-5.,4.,6.),(1.,2.,3.))
    def energy(p):
        x=frame.to_source(p,atom_labels=frame.atom_labels,context_sha256='a'*64)
        return sum(v*v/2 for point in x for v in point)
    for i in range(2):
        for j in range(3):
            a=[list(p) for p in points];b=[list(p) for p in points];a[i][j]+=1e-5;b[i][j]-=1e-5
            assert (energy(a)-energy(b))/2e-5==pytest.approx(gradient[i][j],abs=1e-8)


@pytest.mark.parametrize('order', [[],[0],[0,0],[0,2],[False,1],[1,0,2]])
def test_reference_frame_refuses_partial_or_ambiguous_selection(order):
    with pytest.raises(ValueError,match='complete permutation'):bound_frame().reindex(order)


@pytest.mark.parametrize('method,keyword', [('to_source','atom_labels'),('to_representatives','source_labels'),('gradients_to_representatives','source_labels')])
def test_reference_frame_checks_context_and_order_in_both_directions(method,keyword):
    function=getattr(bound_frame(),method);points=[(1.,2.,3.),(4.,5.,6.)]
    with pytest.raises(ValueError,match='context'):function(points,**{keyword:('A','B')},context_sha256='b'*64)
    with pytest.raises(ValueError,match='order'):function(points,**{keyword:('B','A')},context_sha256='a'*64)
    with pytest.raises(ValueError):function(points[:1],**{keyword:('A','B')},context_sha256='a'*64)


def test_reference_frame_plain_copy_pickle_and_input_detachment():
    import copy,pickle
    from nasolve.topostitch_transport import ReferenceFrame
    labels=['A','B'];images=[IDENTITY_IMAGE,IDENTITY_IMAGE]
    frame=ReferenceFrame(labels,images,'a'*64);labels.reverse();images.pop()
    assert frame.source_labels==('A','B') and len(frame.images)==2
    assert copy.deepcopy(frame)==frame and pickle.loads(pickle.dumps(frame))==frame
    with pytest.raises(ValueError):ReferenceFrame(('A','A'),(IDENTITY_IMAGE,IDENTITY_IMAGE),'a'*64)
    with pytest.raises(ValueError):ReferenceFrame(('A',),(IDENTITY_IMAGE,),'unbound')
