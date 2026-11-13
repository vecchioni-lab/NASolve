import builtins
import hashlib
import json
import math
from itertools import product

import pytest

from nasolve.topostitch import DuplexEnd
from nasolve.topostitch_periodic import propose_periodic_connections, inspect_periodic_end_assignments
from .test_topostitch_coordinates import two_end_fixture


HASH = "a"*64
CELL = (10,10,10,90,90,90)


def end(name, seq, xyz):
    return DuplexEnd(name,seq,"5prime",xyz)


def search(ends, cell=CELL, group="P 1", radius=3., **kwargs):
    return propose_periodic_connections(ends,cell_parameters=cell,space_group=group,
        source_model_sha256=HASH,max_distance_angstrom=radius,**kwargs)


def test_optional_dependency_has_actionable_error(monkeypatch):
    original=builtins.__import__
    def blocked(name,*args,**kwargs):
        if name=="gemmi": raise ImportError("absent")
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,"__import__",blocked)
    with pytest.raises(RuntimeError,match=r"NASolve\[topology\]"):
        search([])


def test_p1_boundary_connection_has_exact_image():
    pytest.importorskip("gemmi")
    report=search([end("a","GA",(1,0,0)),end("b","TC",(9,0,0))])
    edge,=report["candidates"]
    assert edge["ends"] == ["a","b"]
    assert edge["distance_angstrom"] == pytest.approx(2)
    assert edge["target_image"]["symmetry_operation"] == "x,y,z"
    assert edge["target_image"]["lattice_translation"] == [-1,0,0]
    assert edge["target_image"]["operator_xyz"] == "x-1,y,z"
    assert edge["target_position_angstrom"] == pytest.approx([-1,0,0])
    assert report["selected_candidate"] is None
    assert report["search_complete_within_declared_scope"] is True


def test_screw_mate_is_not_replaced_by_a_translation():
    pytest.importorskip("gemmi")
    ends=[end("a","GA",(3,-2,11)),end("b","TC",(2,3,0))]
    report=search(ends,cell=(10,10,40,90,90,90),group="P 43",radius=1.1)
    edge,=report["candidates"]
    assert edge["target_image"]["operator_xyz"] == "y,-x,z+1/4"
    assert edge["distance_angstrom"] == pytest.approx(1)


def test_outside_cell_coordinates_require_large_shift():
    pytest.importorskip("gemmi")
    report=search([end("a","GA",(101,0,0)),end("b","TC",(-91,0,0))])
    edge,=report["candidates"]
    assert edge["target_image"]["lattice_translation"] == [19,0,0]
    assert edge["distance_angstrom"] == pytest.approx(2)


def test_periodic_self_edges_are_retained_once_per_inverse_pair():
    pytest.importorskip("gemmi")
    report=search([end("a","AT",(1,2,3))],radius=10.01)
    assert len(report["candidates"]) == 3
    for edge in report["candidates"]:
        assert edge["ends"] == ["a","a"]
        assert edge["target_image"]["operator_xyz"] != "x,y,z"
        assert edge["distance_angstrom"] == pytest.approx(10)
    assert report["ends"][0]["status"] == "COMPETING_CANDIDATES"


def test_skew_cell_search_matches_independent_brute_force():
    gemmi=pytest.importorskip("gemmi")
    cell=(10,11,12,80,75,20)
    unit=gemmi.UnitCell(*cell)
    a=(1.,2.,3.); b=(8.,1.,4.);radius=8
    expected=set()
    for shift in product(range(-5,6),repeat=3):
        delta=unit.orthogonalize(gemmi.Fractional(*shift))
        p=tuple(b[i]+(delta.x,delta.y,delta.z)[i] for i in range(3))
        if math.dist(a,p)<=radius: expected.add(shift)
    result=search([end("a","GA",a),end("b","TC",b)],cell=cell,radius=radius)
    actual={tuple(c["target_image"]["lattice_translation"]) for c in result["candidates"]}
    assert actual == expected
    assert any(max(map(abs,s))>1 for s in actual)


def test_centering_translations_are_included():
    pytest.importorskip("gemmi")
    r=search([end("a","GA",(5,5,5)),end("b","TC",(0,0,0))],group="I 2 2 2",radius=.01)
    assert r["candidates"]
    assert any(c["target_image"]["symmetry_operation"]=="x+1/2,y+1/2,z+1/2" for c in r["candidates"])
    assert all(c["image_distinctness_validated"] is False for c in r["candidates"])


@pytest.mark.parametrize("cell,group", [
    ((0,10,10,90,90,90),"P 1"), ((10,10,10,1,1,179),"P 1"),
    ((10,11,40,90,90,90),"P 43"), (CELL,"not a group"),
    (CELL,"P -1"), (CELL,""), ((True,10,10,90,90,90),"P 1"),
    ((10,10,10,float("nan"),90,90),"P 1"),
])
def test_invalid_or_unsupported_crystal_context_fails(cell,group):
    pytest.importorskip("gemmi")
    with pytest.raises(ValueError): search([],cell=cell,group=group)


def test_budget_is_not_a_truncated_success():
    pytest.importorskip("gemmi")
    with pytest.raises(ValueError,match="budget"):
        search([end("a","AT",(1,2,3))],radius=100,max_image_tests=2)


def test_determinism_and_no_mutation():
    pytest.importorskip("gemmi")
    ends=[end("b","TC",(9,0,0)),end("a","GA",(1,0,0))]
    r=search(ends)
    assert r==search(list(reversed(ends)))
    assert json.loads(json.dumps(r,allow_nan=False))==r
    assert ends[0].end_id=="b"
    assert r["workflow"]["execution_state"]=="NOT_ATTEMPTED"
    assert r["changes"]==[]


def test_known_free_end_cannot_acquire_a_symmetry_partner():
    pytest.importorskip("gemmi")
    assert not search([DuplexEnd("a","GA","5prime",(1,0,0),"free"),end("b","TC",(9,0,0))])["candidates"]


def cryst1(cell=CELL,group="P 1"):
    a,b,c,alpha,beta,gamma=cell
    return f"CRYST1{a:9.3f}{b:9.3f}{c:9.3f}{alpha:7.2f}{beta:7.2f}{gamma:7.2f} {group:<11}    1\n"


def test_coordinate_wrapper_reads_exact_cryst1_and_preserves_proposal_state(tmp_path):
    pytest.importorskip("gemmi")
    text,assignments=two_end_fixture()
    p=tmp_path/"input.pdb";p.write_text(cryst1((30,30,30,90,90,90))+text)
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    report=inspect_periodic_end_assignments(p,assignments,expected_sha256=digest,max_distance_angstrom=15)
    assert report["source_bytes_verified"] is True
    assert report["crystal_source"] == "verified_pdb_cryst1"
    assert report["periodic_screening"]["candidates"]
    assert report["changes"] == []
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    assert str(tmp_path) not in json.dumps(report)


@pytest.mark.parametrize("header", ["",cryst1()+cryst1()])
def test_wrapper_refuses_missing_or_duplicate_crystal_context(tmp_path,header):
    pytest.importorskip("gemmi")
    text,assignments=two_end_fixture()
    p=tmp_path/"m.pdb";p.write_text(header+text)
    with pytest.raises(ValueError,match="CRYST1"):
        inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=15)


def test_wrapper_refuses_unvalidated_nonstandard_scale(tmp_path):
    pytest.importorskip("gemmi")
    text,assignments=two_end_fixture()
    p=tmp_path/"m.pdb";p.write_text(cryst1()+"SCALE1      0.1       0.0       0.0         1.0\n"+text)
    with pytest.raises(ValueError,match="SCALE"):
        inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=15)


def test_reversed_end_labels_record_reciprocal_operator():
    gemmi=pytest.importorskip("gemmi")
    a=end("a","GA",(3,-2,11));b=end("b","TC",(2,3,0))
    forward=search([a,b],cell=(10,10,40,90,90,90),group="P 43",radius=1.1)["candidates"][0]
    reverse=search([end("z",a.sequence,a.position),b],cell=(10,10,40,90,90,90),group="P 43",radius=1.1)["candidates"][0]
    assert reverse["target_image"]["operator_xyz"] == gemmi.Op(forward["target_image"]["operator_xyz"]).inverse().triplet()
    assert reverse["distance_angstrom"] == pytest.approx(forward["distance_angstrom"])


def test_reimaging_end_representatives_preserves_physical_candidate():
    gemmi=pytest.importorskip("gemmi")
    old=search([end("a","GA",(3,-2,11)),end("b","TC",(2,3,0))],cell=(10,10,40,90,90,90),group="P 43",radius=1.1)
    new=search([end("a","GA",(23,-2,11)),end("b","TC",(2,33,0))],cell=(10,10,40,90,90,90),group="P 43",radius=1.1)
    assert len(new["candidates"])==len(old["candidates"])==1
    assert new["candidates"][0]["distance_angstrom"] == pytest.approx(old["candidates"][0]["distance_angstrom"])
    op=gemmi.Op(new["candidates"][0]["target_image"]["operator_xyz"])
    point=op.apply_to_xyz([.2,3.3,0])
    assert point == pytest.approx([2.3,-.2,.25])


def test_reciprocal_exact_operator_roundtrip():
    gemmi=pytest.importorskip("gemmi")
    result=search([end("a","AT",(2,3,4))],cell=(10,10,40,90,90,90),group="P 43",radius=25)
    for edge in result["candidates"]:
        op=gemmi.Op(edge["target_image"]["operator_xyz"])
        inverse=gemmi.Op(edge["reciprocal_image"]["operator_xyz"])
        assert inverse.apply_to_xyz(op.apply_to_xyz([.2,.3,.4])) == pytest.approx([.2,.3,.4])


def test_large_search_radius_has_bounded_failure():
    pytest.importorskip("gemmi")
    with pytest.raises(ValueError,match="budget|numerical range"):
        search([end("a","AT",(0,0,0))],radius=1e200)


def test_cartesian_sphere_includes_boundary_but_not_extra_cube_points():
    pytest.importorskip("gemmi")
    report=search([end("a","AT",(0,0,0))],radius=10)
    assert len(report["candidates"])==3
    assert all(c["distance_angstrom"]<=10+1e-7 for c in report["candidates"])


def test_periodic_frames_show_actual_image_and_facing_observations(tmp_path):
    pytest.importorskip("gemmi")
    text,assignments=two_end_fixture()
    p=tmp_path/"input.pdb";p.write_text(cryst1((30,30,30,90,90,90))+text)
    report=inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=15)
    obs,=report["candidate_frame_observations"]
    assert obs["outward_axis_angle_degrees"] == pytest.approx(180)
    assert obs["source_facing_angle_degrees"] == pytest.approx(0)
    assert obs["target_facing_angle_degrees"] == pytest.approx(0)
    assert obs["target_image_frame"]["origin"] == pytest.approx([0,0,12])
    assert obs["acceptance_evaluated"] is False


def test_screw_operation_rotates_frame_vectors_without_translation(tmp_path):
    pytest.importorskip("gemmi")
    text,assignments=two_end_fixture()
    p=tmp_path/"input.pdb";p.write_text(cryst1((30,30,40,90,90,90),"P 43")+text)
    report=inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=25)
    edge=next(e for e in report["periodic_screening"]["candidates"] if e["target_image"]["operator_xyz"]=="y,-x,z+1/4")
    obs=report["candidate_frame_observations"][edge["candidate_index"]]
    assert obs["target_image_frame"]["x"] == pytest.approx([0,1,0])
    assert obs["target_image_frame"]["z"] == pytest.approx([0,0,-1])
    assert obs["target_image_frame"]["origin"] == pytest.approx([0,0,22])


@pytest.mark.parametrize("group,cell", [
    ("P 1", (10,12,14,80,85,100)),
    ("P 21", (10,12,14,90,100,90)),
    ("P 21 21 21", (10,12,14,90,90,90)),
    ("P 43", (12,12,18,90,90,90)),
    ("R 3:H", (14,14,20,90,90,120)),
    ("P 63", (14,14,20,90,90,120)),
])
def test_multiple_space_groups_match_brute_force_images(group,cell):
    gemmi=pytest.importorskip("gemmi")
    unit=gemmi.UnitCell(*cell)
    fa=(.17,.24,.31);fb=(.72,.61,.83)
    a=unit.orthogonalize(gemmi.Fractional(*fa));b=unit.orthogonalize(gemmi.Fractional(*fb))
    expected={}
    for op in gemmi.SpaceGroup(group).operations():
        f=op.apply_to_xyz(fb)
        for n in product(range(-3,4),repeat=3):
            image=unit.orthogonalize(gemmi.Fractional(*(f[i]+n[i] for i in range(3))))
            distance=math.dist((a.x,a.y,a.z),(image.x,image.y,image.z))
            if distance<=8+1e-7:
                expected[op.translated([op.DEN*v for v in n]).triplet()]=distance
    report=search([end("a","GA",(a.x,a.y,a.z)),end("b","TC",(b.x,b.y,b.z))],cell=cell,group=group,radius=8)
    actual={e["target_image"]["operator_xyz"]:e["distance_angstrom"] for e in report["candidates"]}
    assert actual.keys()==expected.keys()
    for key in actual: assert actual[key]==pytest.approx(expected[key])


def test_conventional_scale_is_accepted_and_nonzero_offset_rejected(tmp_path):
    gemmi=pytest.importorskip("gemmi")
    text,assignments=two_end_fixture()
    unit=gemmi.UnitCell(30,30,30,90,90,90)
    scales="".join(f"SCALE{i+1}    {row[0]:10.6f}{row[1]:10.6f}{row[2]:10.6f}     {0.:10.5f}\n" for i,row in enumerate(unit.frac.mat.tolist()))
    p=tmp_path/"input.pdb";p.write_text(cryst1((30,30,30,90,90,90))+scales+text)
    result=inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=15)
    assert result["periodic_screening"]["candidates"]
    p.write_text(p.read_text().replace("   0.00000","   1.00000"))
    with pytest.raises(ValueError,match="SCALE"):
        inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=15)


def test_periodic_wrapper_survives_removed_original_location(tmp_path):
    pytest.importorskip("gemmi")
    old=tmp_path/"old";old.mkdir()
    text,assignments=two_end_fixture()
    p=old/"input.pdb";p.write_text(cryst1((30,30,30,90,90,90))+text)
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    before=inspect_periodic_end_assignments(p,assignments,expected_sha256=digest,max_distance_angstrom=15)
    moved=tmp_path/"renamed.pdb";p.rename(moved);old.rmdir()
    after=inspect_periodic_end_assignments(moved,assignments,expected_sha256=digest,max_distance_angstrom=15)
    assert before==after


def test_incomplete_coordinate_assessment_stays_visible_in_periodic_result(tmp_path):
    pytest.importorskip("gemmi")
    text,assignments=two_end_fixture()
    text="\n".join(line for line in text.splitlines() if not (line[12:16].strip()=="C4" and line[21:26]=="C   2"))
    p=tmp_path/"m.pdb";p.write_text(cryst1((30,30,30,90,90,90))+text)
    r=inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=15)
    assert r["workflow"]["proposal_state"]=="INCOMPLETE_ASSESSMENT"
    assert r["coordinate_assessment"]["ends"][1]["assessment"]=="UNASSESSED"
    assert r["periodic_screening"]["candidates"]==[]



def test_translational_self_edge_reports_capacity_issue():
    pytest.importorskip("gemmi")
    report=search([end("a","AT",(1,2,3))],radius=10.01)
    assert all(c["self_image_capacity_warning"] for c in report["candidates"])
    assert all(c["requires_global_assignment_review"] for c in report["candidates"])


def test_twofold_self_image_is_not_blanket_rejected():
    pytest.importorskip("gemmi")
    report=search([end("a","AT",(2,3,4))],group="P 2",radius=10)
    twofold=next(c for c in report["candidates"] if c["target_image"]["operator_xyz"]=="-x,y,-z")
    assert twofold["self_image_inverse_is_same_operator"] is True
    assert twofold["self_image_capacity_warning"] is None
    assert twofold["image_distinctness_validated"] is False


def test_empty_translation_box_does_not_materialize_huge_other_axis():
    pytest.importorskip('gemmi')
    report=search([end('a','GA',(0,0,0)),end('b','TC',(0,5e11,0))],cell=(1e-8,1e12,1e12,90,90,90),radius=1,max_image_tests=1)
    assert report['candidates']==[]
    assert report['image_tests']==0


def test_hexagonal_frame_rotation_uses_cell_metric(tmp_path):
    pytest.importorskip('gemmi')
    text,assignments=two_end_fixture()
    p=tmp_path/'m.pdb';p.write_text(cryst1((30,30,40,90,90,120),'P 63')+text)
    report=inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=35)
    edge=next(c for c in report['periodic_screening']['candidates'] if c['target_image']['operator_xyz']=='x-y,x,z+1/2')
    axes=report['candidate_frame_observations'][edge['candidate_index']]['target_image_frame']
    assert axes['x']==pytest.approx([-.5,-math.sqrt(3)/2,0])
    assert axes['y']==pytest.approx([-math.sqrt(3)/2,.5,0])
    assert axes['z']==pytest.approx([0,0,-1])
    assert axes['origin']==pytest.approx([0,0,32])


def test_coincident_periodic_frame_has_no_defined_facing_angle(tmp_path):
    pytest.importorskip('gemmi')
    text,assignments=two_end_fixture()
    p=tmp_path/'m.pdb';p.write_text(cryst1((30,30,24,90,90,90),'P 42')+text)
    report=inspect_periodic_end_assignments(p,assignments,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=1)
    assert report['periodic_screening']['candidates']
    for edge in report['periodic_screening']['candidates']:
        assert edge['coincident_reference_points'] is True
        assert edge['image_distinctness_validated'] is False
        obs=report['candidate_frame_observations'][edge['candidate_index']]
        assert obs['source_facing_angle_degrees'] is None
        assert obs['target_facing_angle_degrees'] is None
    json.dumps(report,allow_nan=False)
