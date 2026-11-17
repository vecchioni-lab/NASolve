import pytest
from nasolve.topostitch_endpoint import audit_masked_endpoint
from .helpers import pdb_record


def source():
    return ('REMARK exact metadata\r\n'+pdb_record('ATOM',1,"P",'DA','A',1,x=1,y=2,z=3)
            +pdb_record('ATOM',2,"P",'DT','B',2,x=4,y=5,z=6)+'TER\nEND\n').encode()


def serialize(data,point):
    rows=data.splitlines(keepends=True)
    rows[1]=rows[1][:30]+''.join(f'{v:8.3f}' for v in point).encode()+rows[1][54:]
    return b''.join(rows)


def audit(data=None,points=None,**kwargs):
    data=source() if data is None else data
    points=[[1.0014,2,3],[4,5,6]] if points is None else points
    return audit_masked_endpoint(data,serialize(data,points[0]),points,
        movable_indices=[0],max_displacement_angstrom=.01,**kwargs)


def test_exact_fixed_records_and_rounding_are_separate_evidence():
    report=audit()
    assert report['status']=='EXACT_MASKED_SERIALIZATION'
    assert report['fixed_atom_count']==1 and report['moved_atom_count']==1
    assert report['roundtrip_max_distance_angstrom']==pytest.approx(.0004)
    assert report['full_precision_max_displacement_angstrom']==pytest.approx(.0014)
    assert report['serialized_max_displacement_angstrom']==pytest.approx(.001)
    assert not report['geometry_accepted'] and not report['runtime_authority']


@pytest.mark.parametrize('change', ['fixed_coordinate','b_factor','occupancy','cell','line_endings','record_order','extra_atom','conect','wrong_rounding'])
def test_coordinate_permission_does_not_allow_other_changes(change):
    data=source();points=[[1.0014,2,3],[4,5,6]];candidate=serialize(data,points[0])
    rows=candidate.splitlines(keepends=True)
    if change=='fixed_coordinate':rows[2]=rows[2][:30]+b'   4.001'+rows[2][38:]
    if change=='b_factor':rows[1]=rows[1][:60]+b' 22.00'+rows[1][66:]
    if change=='occupancy':rows[1]=rows[1][:54]+b'  0.50'+rows[1][60:]
    if change=='cell':rows[0]=b'CRYST1 changed\n'
    if change=='line_endings':rows[0]=rows[0].replace(b'\r\n',b'\n')
    if change=='record_order':rows[1],rows[2]=rows[2],rows[1]
    if change=='extra_atom':rows.insert(3,pdb_record('ATOM',3,'P','DA','A',3).encode())
    if change=='conect':rows.insert(3,b'CONECT    1    2\n')
    if change=='wrong_rounding':rows[1]=rows[1][:30]+b'   1.002'+rows[1][38:]
    with pytest.raises(ValueError):audit_masked_endpoint(data,b''.join(rows),points,movable_indices=[0],max_displacement_angstrom=.01)


def test_full_precision_fixed_atom_cannot_hide_behind_pdb_rounding():
    with pytest.raises(ValueError,match='Fixed ASU'):
        audit(points=[[1.0014,2,3],[4.0001,5,6]])


def test_rounding_cannot_exceed_a_full_precision_motion_limit():
    data=source()
    # Diagonal outward rounding crosses a bound although the exact point fits.
    points=[[1.0006,2.0006,3],[4,5,6]]
    with pytest.raises(ValueError,match='exceeds'):
        audit_masked_endpoint(data,serialize(data,points[0]),points,movable_indices=[0],max_displacement_angstrom=.001)


@pytest.mark.parametrize('change',['modified','alternate','partial','nan'])
def test_unqualified_moving_chemistry_is_not_silently_accepted(change):
    rows=source().splitlines(keepends=True)
    if change=='modified':rows[1]=rows[1][:17]+b'PDU'+rows[1][20:]
    if change=='alternate':rows[1]=rows[1][:16]+b'A'+rows[1][17:]
    if change=='partial':rows[1]=rows[1][:54]+b'  0.50'+rows[1][60:]
    if change=='nan':rows[1]=rows[1][:54]+b'   nan'+rows[1][60:]
    with pytest.raises(ValueError,match='full-occupancy'):audit(b''.join(rows))


def test_movable_anisou_requires_a_motion_policy_but_fixed_tensors_are_preserved():
    rows=source().splitlines(keepends=True)
    tensor=b'ANISOU'+rows[1][6:27]+b'   1000   1000   1000      0      0      0\n'
    rows.insert(3,tensor)
    with pytest.raises(ValueError,match='ANISOU'):audit(b''.join(rows))
    rows[3]=b'ANISOU'+rows[2][6:27]+tensor[27:]
    assert audit(b''.join(rows))['fixed_records_preserved']


def test_nonfinite_or_overflowing_full_precision_coordinates_fail():
    with pytest.raises(ValueError):audit(points=[[float('nan'),2,3],[4,5,6]])
    data=source();points=[[1e10,2,3],[4,5,6]]
    with pytest.raises(ValueError,match='field width'):
        audit_masked_endpoint(data,data,points,movable_indices=[0],max_displacement_angstrom=1e11)


def test_explicit_coordinate_only_policy_preserves_tensors_without_claiming_adp_quality():
    rows=source().splitlines(keepends=True)
    rows.insert(3,b'ANISOU'+rows[1][6:27]+b'   1000   1000   1000      0      0      0\n')
    data=b''.join(rows);report=audit(data,anisou_policy='preserve-cartesian')
    assert report['movable_anisou_count']==1 and not report['thermal_model_qualified']
    points=[[1.0014,2,3],[4,5,6]];candidate=serialize(data,points[0]).replace(b'   1000   1000',b'   1200   1000',1)
    with pytest.raises(ValueError,match='protected bytes'):
        audit_masked_endpoint(data,candidate,points,movable_indices=[0],max_displacement_angstrom=.01,anisou_policy='preserve-cartesian')


def test_unknown_tensor_policy_cannot_silently_default():
    with pytest.raises(ValueError,match='ANISOU policy'):audit(anisou_policy='guess')


def test_coordinate_observation_cases_keep_exact_fixed_atoms_and_round_only_selection():
    from nasolve.topostitch_endpoint import endpoint_coordinate_cases
    value=endpoint_coordinate_cases(source(),[[1.0014,2,3],[4,5,6]],movable_indices=[0],max_displacement_angstrom=.01)
    assert list(value)==['source','full_precision','rounded']
    assert value['source']==[[1.,2.,3.],[4.,5.,6.]]
    assert value['full_precision'][0]==[1.0014,2.,3.]
    assert value['rounded'][0]==[1.001,2.,3.]
    assert all(points[1]==[4.,5.,6.] for points in value.values())


@pytest.mark.parametrize('points,bound',[([[1.001,2,3],[4.00001,5,6]],.01),
    ([[1.0006,2,3],[4,5,6]],.0007),([[float('nan'),2,3],[4,5,6]],.01)])
def test_observation_preflight_refuses_fixed_motion_outward_rounding_and_nonfinite(points,bound):
    from nasolve.topostitch_endpoint import endpoint_coordinate_cases
    with pytest.raises(ValueError):endpoint_coordinate_cases(source(),points,movable_indices=[0],max_displacement_angstrom=bound)


def test_observation_projection_is_detached_and_coordinate_bound():
    from copy import deepcopy
    from nasolve.topostitch_endpoint import project_coordinate_observation
    native=dict(atom_count=2,atoms=[dict(xyz=[1,2,3]),dict(xyz=[4,5,6])],geometry=dict(sites_cart_exact=[[1,2,3],[4,5,6]],proxy_details={'frozen':True}),energy_inventory={'snapshots':['source']},nonbonded_inventory={'source':True})
    points=[[1.001,2.,3.],[4.,5.,6.]]
    observation=dict(points=points,native_energy_snapshots=[{'actual':1},{'actual':2}],nonbonded_inventory={'actual_pairs':[]},exact_repeat=True)
    before=deepcopy((native,observation));value=project_coordinate_observation(native,observation,expected_points=points)
    assert (native,observation)==before
    assert value['atoms'][0]['xyz']==points[0]
    assert value['geometry']['proxy_details']==native['geometry']['proxy_details']
    value['nonbonded_inventory']['actual_pairs'].append('changed')
    assert observation['nonbonded_inventory']['actual_pairs']==[]
    with pytest.raises(ValueError,match='bound request'):
        project_coordinate_observation(native,observation,expected_points=[[1.,2.,3.],[4.,5.,6.]])
    observation['native_energy_snapshots'].pop()
    with pytest.raises(ValueError,match='complete repeated'):
        project_coordinate_observation(native,observation,expected_points=points)


def test_rounded_observation_uses_actual_binary_displacement_coordinates():
    from nasolve.topostitch_endpoint import endpoint_coordinate_cases
    from nasolve.topostitch_transport import CoordinateMask
    data=(pdb_record('ATOM',1,'P','DA','A',1,x=1,y=2,z=.047)
          +pdb_record('ATOM',2,'P','DT','B',2,x=4,y=5,z=6)).encode()
    cases=endpoint_coordinate_cases(data,[[1,2,.0144],[4,5,6]],movable_indices=[0],max_displacement_angstrom=.1)
    mask=CoordinateMask(((1,2,.047),(4,5,6)),(0,),.1)
    actual=mask.expand(mask.displacements([[1,2,.014],[4,5,6]]))
    assert cases['rounded']==[list(p) for p in actual]
    assert cases['rounded'][0][2]!=.014
    assert format(cases['rounded'][0][2],'.3f')=='0.014'
