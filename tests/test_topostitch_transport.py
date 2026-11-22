"""Independent derivatives for image transport and shared ASU variables."""
import math

import pytest

from nasolve.topostitch_transport import (
    CartesianImage, CoordinateMask, IDENTITY_IMAGE, crystallographic_image,
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


@pytest.mark.parametrize('cell,group,operator',[
    ((10,11,12,80,75,20),'P 1','x+19,y-3,z+2'),
    ((10,10,40,90,90,90),'P 43','y,-x,z+1/4'),
    ((105.547,105.547,96.268,90,90,120),'R 3:H','-x+y+2/3,-x+1/3,z+1/3'),
])
def test_cartesian_tensor_rotation_matches_independent_crystal_path(cell,group,operator):
    gemmi=pytest.importorskip('gemmi')
    image=crystallographic_image(cell,group,operator)
    tensor=(.14,.23,.37,.021,-.032,.044)
    expected=gemmi.SMat33d(*tensor).transformed_by(gemmi.UnitCell(*cell).op_as_transform(gemmi.Op(operator)).mat)
    actual=image.rotate_tensor(tensor)
    assert actual==pytest.approx(expected.elements_pdb(),abs=1e-14)
    assert image.inverse().rotate_tensor(actual)==pytest.approx(tensor,abs=1e-14)
    assert sum(actual[:3])==pytest.approx(sum(tensor[:3]),abs=1e-14)
    norm=lambda u:sum(v*v for v in u[:3])+2*sum(v*v for v in u[3:])
    assert norm(actual)==pytest.approx(norm(tensor),abs=1e-14)
    assert CartesianImage(image.rotation,(1e6,-2e6,3e6)).rotate_tensor(tensor)==actual


def test_complete_tensor_frame_reindexing_retains_identity_and_off_diagonal_signs():
    frame=bound_frame().reindex([1,0]);tensors=((.1,.1,.1,0.,0.,0.),(1.,2.,3.,.4,.5,.6))
    represented=frame.tensors_to_representatives(tensors,source_labels=('A','B'),context_sha256='a'*64)
    assert represented[0]==pytest.approx((2.,1.,3.,-.4,-.6,.5))
    assert represented[1]==tensors[0]
    restored=frame.tensors_to_source(represented,atom_labels=('B','A'),context_sha256='a'*64)
    for actual,expected in zip(restored,tensors):assert actual==pytest.approx(expected)
    # Covariance rotates; translations must not be added to any tensor component.
    zero=((0.,)*6,)*2
    assert frame.tensors_to_representatives(zero,source_labels=('A','B'),context_sha256='a'*64)==zero


@pytest.mark.parametrize('method,keyword',[
    ('tensors_to_source','atom_labels'),('tensors_to_representatives','source_labels')])
def test_tensor_binding_refuses_stale_context_reassigned_atoms_and_incomplete_inventory(method,keyword):
    frame=bound_frame();call=getattr(frame,method);u=[(.1,.2,.3,0.,0.,0.)]*2
    with pytest.raises(ValueError,match='context'):call(u,**{keyword:('A','B')},context_sha256='b'*64)
    with pytest.raises(ValueError,match='order'):call(u,**{keyword:('B','A')},context_sha256='a'*64)
    with pytest.raises(ValueError,match='complete source'):call(u[:1],**{keyword:('A','B')},context_sha256='a'*64)
    with pytest.raises(ValueError):call([None,u[1]],**{keyword:('A','B')},context_sha256='a'*64)


@pytest.mark.parametrize('tensor',[(1,2,3,4,5),(1,2,3,4,5,6,7),None,(1,2,3,4,float('nan'),6),(1,2,3,4,float('inf'),6),(1,2,3,True,5,6)])
def test_tensor_transport_rejects_ambiguous_or_nonfinite_components(tensor):
    with pytest.raises(ValueError):IDENTITY_IMAGE.rotate_tensor(tensor)


def test_tensor_transport_refuses_finite_input_that_overflows_on_rotation():
    c=math.sqrt(.5);image=CartesianImage(((c,-c,0.),(c,c,0.),(0.,0.,1.)),(0.,0.,0.))
    with pytest.raises(ValueError):image.rotate_tensor((1.5e308,1.5e308,1.,1.5e308,0.,0.))


def test_pivoted_rotation_keeps_molecular_center_and_cycles_three_placements():
    # A 120-degree molecular rotation is valid arithmetic even in a P1 dataset.
    # The cell origin must not become the molecular pivot.
    c, s = -.5, math.sqrt(3)/2
    rotation=((c,-s,0.),(s,c,0.),(0.,0.,1.))
    pivot=(11.,-7.,3.)
    image=CartesianImage.around_pivot(rotation,pivot)
    assert image.apply(pivot)==pytest.approx(pivot,abs=1e-13)
    point=(13.,-7.,4.)
    assert image.apply(point)==pytest.approx((10.,-7.+math.sqrt(3),4.),abs=1e-13)
    assert image.apply(image.apply(image.apply(point)))==pytest.approx(point,abs=1e-13)
    assert image.inverse().apply(image.apply(point))==pytest.approx(point,abs=1e-13)
    assert image.apply(point)!=CartesianImage(rotation,(0.,0.,0.)).apply(point)


def test_pivoted_rotation_translates_after_rotation_and_retains_tensor_gradient_rules():
    rotation=((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.))
    image=CartesianImage.around_pivot(rotation,(10.,20.,30.),translation=(2.,-3.,4.))
    assert image.apply((11.,20.,32.))==pytest.approx((12.,18.,36.))
    tensor=(.1,.2,.3,.04,.05,.06)
    assert image.rotate_tensor(tensor)==CartesianImage(rotation,(0.,0.,0.)).rotate_tensor(tensor)
    assert image.pullback((2.,3.,4.))==(3.,-2.,4.)
    assert image.inverse().apply(image.apply((11.,20.,32.)))==pytest.approx((11.,20.,32.))


def test_identity_pivot_preserves_small_translation_at_large_origin_and_detaches_inputs():
    rotation=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
    pivot=[1e20,-1e20,1e20];translation=[.1,.2,.3]
    image=CartesianImage.around_pivot(rotation,pivot,translation=translation)
    assert image.translation==(.1,.2,.3)  # p+t-p would erase these translations.
    rotation[0][0]=2.;pivot[0]=0.;translation[0]=9.
    assert image.apply((1.,2.,3.))==(1.1,2.2,3.3)
    assert CartesianImage.around_pivot(IDENTITY_IMAGE.rotation,(1e300,)*3)==IDENTITY_IMAGE


@pytest.mark.parametrize('pivot,translation',[
    ((1.,2.),(0.,0.,0.)), ((0.,float('nan'),0.),(0.,0.,0.)),
    ((False,0.,0.),(0.,0.,0.)), ((0.,0.,0.),(0.,float('inf'),0.)),
    ((0.,0.,0.),(0.,0.,True)),
])
def test_pivoted_rotation_refuses_invalid_origin_or_translation(pivot,translation):
    with pytest.raises(ValueError):
        CartesianImage.around_pivot(IDENTITY_IMAGE.rotation,pivot,translation=translation)


def test_pivoted_rotation_refuses_improper_rotation_and_overflow():
    with pytest.raises(ValueError,match='proper rotation'):
        CartesianImage.around_pivot(((-1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),(1.,2.,3.))
    with pytest.raises(ValueError,match='finite'):
        CartesianImage.around_pivot(((-1.,0.,0.),(0.,-1.,0.),(0.,0.,1.)),(1e308,0.,0.))



def test_displacement_summary_distinguishes_cancelled_centroid_from_real_motion():
    from nasolve.topostitch_transport import CoordinateMask
    mask=CoordinateMask(((-1,0,0),(1,0,0),(9,9,9)),(0,1),3)
    result=mask.displacement_summary(((-2,0,0),(2,0,0),(9,9,9)))
    assert result['centroid_displacement_angstrom']==0
    assert result['weighted_rms_atom_displacement_angstrom']==1
    assert result['max_atom_displacement_angstrom']==1
    assert result['atom_indices']==(0,1) and result['normalized_weights']==(.5,.5)
    assert not result['frame_identity_verified'] and not result['centerline_measured']


def test_displacement_summary_explicit_weights_follow_mask_order():
    from nasolve.topostitch_transport import CoordinateMask
    mask=CoordinateMask(((0,0,0),(10,0,0),(99,0,0)),(1,0),3)
    result=mask.displacement_summary(((2,0,0),(8,0,0),(99,0,0)),weights=(3,1))
    assert result['reference_centroid_angstrom']==(7.5,0,0)
    assert result['candidate_centroid_angstrom']==(6.5,0,0)
    assert result['centroid_displacement_vector_angstrom']==(-1,0,0)
    assert result['centroid_displacement_angstrom']==1
    assert result['weighted_rms_atom_displacement_angstrom']==2
    assert result['max_atom_displacement_angstrom']==2
    assert result['weighting']=='explicit'


def test_displacement_summary_common_translation_and_frame_rotation():
    from nasolve.topostitch_transport import CoordinateMask
    reference=((1,2,3),(4,5,6));points=tuple(tuple(a+b for a,b in zip(p,(2,3,6)))for p in reference)
    result=CoordinateMask(reference,(0,1),8).displacement_summary(points)
    assert result['centroid_displacement_vector_angstrom']==(2,3,6)
    for key in ('centroid_displacement_angstrom','weighted_rms_atom_displacement_angstrom','max_atom_displacement_angstrom'):assert result[key]==pytest.approx(7)
    image=CartesianImage(((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.)),(100,200,300))
    transformed=CoordinateMask(tuple(map(image.apply,reference)),(0,1),8).displacement_summary(tuple(map(image.apply,points)))
    assert transformed['centroid_displacement_vector_angstrom']==(-3,2,6)
    for key in ('centroid_displacement_angstrom','weighted_rms_atom_displacement_angstrom','max_atom_displacement_angstrom'):assert transformed[key]==pytest.approx(result[key])


@pytest.mark.parametrize('weights',[(0,1),(-1,1),(True,1),(float('nan'),1),(1,),(1,float('inf')),(1e-308,1e308)])
def test_displacement_summary_refuses_ambiguous_weights(weights):
    from nasolve.topostitch_transport import CoordinateMask
    mask=CoordinateMask(((0,0,0),(1,0,0)),(0,1),2)
    with pytest.raises(ValueError):mask.displacement_summary(mask.reference,weights=weights)


def test_displacement_summary_retains_mask_bounds_and_fixed_atoms():
    from nasolve.topostitch_transport import CoordinateMask
    mask=CoordinateMask(((0,0,0),(1,0,0)),(0,),2)
    with pytest.raises(ValueError,match='Fixed ASU'):mask.displacement_summary(((0,0,0),(1,0,1)))
    with pytest.raises(ValueError,match='exceeds'):mask.displacement_summary(((3,0,0),(1,0,0)))


def test_displacement_summary_large_finite_weights_are_normalized_without_overflow():
    from nasolve.topostitch_transport import CoordinateMask
    mask=CoordinateMask(((0,0,0),(1,0,0)),(0,1),2)
    weights=[1e308,1e308];r=mask.displacement_summary(((1,0,0),(2,0,0)),weights=weights)
    weights[0]=0
    assert r['normalized_weights']==(.5,.5) and r['centroid_displacement_angstrom']==1
    assert mask.reference==((0.,0.,0.),(1.,0.,0.))


def test_measurement_subset_keeps_core_target_when_editable_window_expands():
    reference=((0.,0.,0.),(1.,0.,0.),(2.,0.,0.),(9.,9.,9.))
    mask=CoordinateMask(reference,(0,1,2),11.)
    # Surrounding atoms move in the opposite direction; the core still moved10A.
    points=((-5.,0.,0.),(11.,0.,0.),(-3.,0.,0.),reference[3])
    whole=mask.displacement_summary(points)
    core=mask.displacement_summary(points,measurement_indices=(1,))
    assert whole['centroid_displacement_angstrom']==0
    assert core['centroid_displacement_angstrom']==10
    assert core['weighted_rms_atom_displacement_angstrom']==10
    assert core['max_atom_displacement_angstrom']==10
    assert core['atom_indices']==(1,) and core['motion_atom_indices']==mask.indices
    assert 'motion_atom_indices'not in whole
    assert not core['frame_identity_verified']and not core['centerline_measured']


def test_measurement_subset_weights_follow_explicit_order_not_mask_order():
    mask=CoordinateMask(((0.,0.,0.),(1.,0.,0.),(2.,0.,0.)),(1,0,2),10.)
    indices=[2,0];weights=[3,1]
    result=mask.displacement_summary(((2.,0.,0.),(1.,0.,0.),(10.,0.,0.)),measurement_indices=indices,weights=weights)
    assert result['atom_indices']==(2,0)and result['normalized_weights']==(.75,.25)
    assert result['reference_centroid_angstrom']==(1.5,0.,0.)
    assert result['candidate_centroid_angstrom']==(8.,0.,0.)
    assert result['centroid_displacement_angstrom']==6.5
    assert result['weighted_rms_atom_displacement_angstrom']==pytest.approx(7.)
    indices[:]=[1];weights[:]=[99]
    assert result['atom_indices']==(2,0)and result['normalized_weights']==(.75,.25)


@pytest.mark.parametrize('selection',[[],[0,0],[True],[1.0],[-1],[3],[2],[[0]],'0'])
def test_measurement_subset_refuses_empty_duplicate_noninteger_or_nonmovable(selection):
    mask=CoordinateMask(((0.,0.,0.),(1.,0.,0.),(2.,0.,0.)),(0,1),2.)
    with pytest.raises(ValueError):
        mask.displacement_summary(mask.reference,measurement_indices=selection)


def test_measurement_subset_cannot_hide_noncore_bound_or_fixed_atom_violation():
    mask=CoordinateMask(((0.,0.,0.),(1.,0.,0.),(2.,0.,0.)),(0,1),2.)
    with pytest.raises(ValueError,match='exceeds'):
        mask.displacement_summary(((0.,0.,0.),(4.,0.,0.),(2.,0.,0.)),measurement_indices=(0,))
    with pytest.raises(ValueError,match='Fixed ASU'):
        mask.displacement_summary(((0.,0.,0.),(1.,0.,0.),(3.,0.,0.)),measurement_indices=(0,))
    with pytest.raises(ValueError,match='weight'):
        mask.displacement_summary(mask.reference,measurement_indices=(0,),weights=(1,1))


def test_explicit_complete_measurement_preserves_existing_numeric_report():
    mask=CoordinateMask(((0.,0.,0.),(1.,0.,0.)),(1,0),2.)
    points=((1.,0.,0.),(1.,1.,0.))
    old=mask.displacement_summary(points,weights=(2,1))
    explicit=mask.displacement_summary(points,weights=(2,1),measurement_indices=mask.indices)
    assert explicit.pop('motion_atom_indices')==mask.indices
    assert explicit==old


def test_measurement_subset_is_rigid_frame_invariant_and_requires_full_points():
    reference=((0.,0.,0.),(1.,1.,0.),(2.,0.,0.));points=((1.,0.,0.),(2.,2.,0.),(3.,0.,0.))
    image=CartesianImage(((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.)),(7.,-4.,2.))
    first=CoordinateMask(reference,(0,1,2),2.).displacement_summary(points,measurement_indices=(0,1),weights=(1,3))
    other=CoordinateMask(tuple(map(image.apply,reference)),(0,1,2),2.).displacement_summary(tuple(map(image.apply,points)),measurement_indices=(0,1),weights=(1,3))
    for key in ('centroid_displacement_angstrom','weighted_rms_atom_displacement_angstrom','max_atom_displacement_angstrom'):
        assert other[key]==pytest.approx(first[key],abs=1e-12)
    with pytest.raises(ValueError,match='count'):
        CoordinateMask(reference,(0,1,2),2.).displacement_summary(points[:2],measurement_indices=(0,1))
