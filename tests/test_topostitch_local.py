"""Intrinsic shoulder proposals preserve exact anchors, not chemical approval."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
import math

import pytest

from nasolve.topostitch_coordinates import ResidueSite
from .helpers import pdb_record


def model():
    # Nonplanar P-O5-C5-C4 segment and an independently oriented C4 sugar frame.
    values=[('P',(0,0,0)),("O5'",(1,1,0)),("C5'",(2,1,1)),
            ("C4'",(3,0,0)),("C3'",(3,0,1)),("O4'",(3,1,0)),
            ('OP1',(-1,0,0)),('OP2',(0,-1,0)),('N1',(9,8,7))]
    text='REMARK protected crystal/metadata\r\n'
    for i,(name,(x,y,z)) in enumerate(values,1):
        text+=pdb_record('ATOM',i,name,'DT','Q',-4,x=x,y=y,z=z,element=name[0])
    return (text+'TER\nEND\n').encode()


def propose(data=None,**overrides):
    from nasolve.topostitch_local import propose_backbone_shoulder
    data=model() if data is None else data
    options=dict(expected_source_sha256=sha256(data).hexdigest(),site=ResidueSite('Q',-4),
                 reflection=False,rotation_degrees=30,max_displacement_angstrom=4)
    return propose_backbone_shoulder(data,**dict(options,**overrides))


def points(data):
    return [tuple(float(line[a:b])for a,b in [(30,38),(38,46),(46,54)])
            for line in data.splitlines()if line[:6]in(b'ATOM  ',b'HETATM')]


def test_intrinsic_rotation_has_known_geometry_and_only_two_movable_atoms():
    p=propose();original=points(model());c=math.sqrt(3)/2
    assert p.points[1]==pytest.approx((1,c,.5))
    assert p.points[2]==pytest.approx((2,c-.5,.5+c))
    assert p.movable_indices==(1,2)
    for i in set(range(len(original)))-{1,2}:assert p.points[i]==original[i]
    for i in range(4):
        for j in range(i):assert math.dist(p.points[i],p.points[j])==pytest.approx(math.dist(original[i],original[j]),abs=1e-12)
    report=json.loads(p.report_json)
    assert report['endpoint_audit']['fixed_records_preserved']
    assert report['relative_C4_handedness_preserved']
    assert not report['scientific_acceptance'] and not report['motion_admission']
    assert report['source_model_sha256']==sha256(model()).hexdigest()
    assert report['candidate_model_sha256']==sha256(p.candidate_bytes).hexdigest()
    with pytest.raises(FrozenInstanceError):p.points=()


def test_reflected_branch_and_exact_neutral_are_distinct():
    p=propose(reflection=True,rotation_degrees=0)
    assert p.points[1]==(1,1,0) and p.points[2]==(2,1,-1)
    neutral=propose(rotation_degrees=0)
    assert neutral.candidate_bytes==model()
    assert json.loads(neutral.report_json)['endpoint_audit']['moved_atom_count']==0


@pytest.mark.parametrize('options',[
    {'expected_source_sha256':'0'*64},{'site':ResidueSite('A',-4)},
    {'reflection':1},{'rotation_degrees':True},{'rotation_degrees':float('nan')},
    {'rotation_degrees':181},{'max_displacement_angstrom':.01},
])
def test_explicit_request_and_displacement_bound_are_enforced(options):
    with pytest.raises(ValueError):propose(**options)


@pytest.mark.parametrize('change',['missing','alternate','partial','modified','hydrogen','split_site','degenerate_axis','degenerate_plane','degenerate_sugar'])
def test_unsupported_local_identity_or_frame_refuses(change):
    data=model();rows=data.splitlines(keepends=True)
    if change=='missing':rows.pop(3)
    if change=='alternate':rows[3]=rows[3][:16]+b'A'+rows[3][17:]
    if change=='partial':rows[3]=rows[3][:54]+b'  0.50'+rows[3][60:]
    if change=='modified':rows=[r[:17]+b'PDU'+r[20:]if r.startswith(b'ATOM')else r for r in rows]
    if change=='hydrogen':rows.insert(-2,pdb_record('ATOM',10,'H5\'','DT','Q',-4,x=2,y=2,z=1).encode())
    if change=='split_site':rows.insert(3,b'TER\n')
    if change=='degenerate_axis':rows[4]=rows[4][:30]+rows[1][30:54]+rows[4][54:]
    if change=='degenerate_plane':rows[2]=rows[2][:30]+b'   1.000   0.000   0.000'+rows[2][54:]
    if change=='degenerate_sugar':rows[5]=rows[5][:30]+rows[6][30:54]+rows[5][54:]
    with pytest.raises(ValueError):propose(b''.join(rows))


def test_local_sugar_sign_inversion_refuses_even_with_preserved_chain_lengths():
    # Rotation flips C5 from x<3 to x<3 still, so change sugar frame to y-normal.
    rows=model().splitlines(keepends=True)
    rows[5]=rows[5][:30]+b'   4.000   0.000   0.000'+rows[5][54:]
    rows[6]=rows[6][:30]+b'   3.000   0.000   1.000'+rows[6][54:]
    with pytest.raises(ValueError,match='handedness'):propose(b''.join(rows),rotation_degrees=180)


def test_existing_native_mapper_consumes_the_exact_endpoint_without_new_motion_schema():
    from nasolve.topostitch_endpoint import map_native_endpoint
    from nasolve.topostitch_recipe import model_atom_rows,recipe_digest
    from types import SimpleNamespace
    p=propose();source=model();report=json.loads(p.report_json)
    def atoms(native,payload):
        rows=model_atom_rows(payload)
        assert [a['xyz']for a in native['atoms']]==[list(x)for x in reversed(points(payload))]
        return [(r['chain']+':'+str(r['residue_number']),r['residue_code'],r['atom_name'])for r in reversed(rows)],None
    mapping=map_native_endpoint(source,p.candidate_bytes,p.points,movable_indices=p.movable_indices,
        max_displacement_angstrom=4,expected_audit_sha256=recipe_digest(report['endpoint_audit']),
        native={'atom_count':9,'atoms':[{'xyz':p}for p in reversed(points(p.candidate_bytes))]},native_model_role='candidate',native_owner=SimpleNamespace(_native_atoms=atoms))
    assert mapping.movable_native_indices==(7,6)
    assert mapping.full_precision_points==tuple(reversed(p.points))


def test_proposal_is_equivariant_under_an_independent_rigid_frame_change():
    original=propose(reflection=True)
    transform=lambda p:(10-p[1],20+p[0],30+p[2])
    rows=model().splitlines(keepends=True)
    for i,line in enumerate(rows):
        if line.startswith(b'ATOM'):
            xyz=tuple(float(line[a:b])for a,b in ((30,38),(38,46),(46,54)))
            rows[i]=line[:30]+''.join(f'{v:8.3f}'for v in transform(xyz)).encode()+line[54:]
    changed=propose(b''.join(rows),reflection=True)
    for a,b in zip(original.points,changed.points):assert transform(a)==pytest.approx(b,abs=1e-12)


def test_insertion_codes_are_exact_and_movable_tensors_are_not_silently_carried():
    rows=model().splitlines(keepends=True)
    rows=[r[:26]+b'B'+r[27:]if r.startswith(b'ATOM')else r for r in rows]
    data=b''.join(rows)
    with pytest.raises(ValueError):propose(data)
    assert propose(data,site=ResidueSite('Q',-4,'B')).movable_indices==(1,2)
    tensor=b'ANISOU'+rows[2][6:27]+b'   1000   1000   1000      0      0      0\n'
    rows.insert(-2,tensor)
    with pytest.raises(ValueError,match='ANISOU'):propose(b''.join(rows),site=ResidueSite('Q',-4,'B'))
