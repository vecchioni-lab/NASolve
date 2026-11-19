from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch

import pytest

from nasolve.refinement_plane_departures import describe_planes


def observation(points, plane_ids, weights, angles=()):
    ids = [7 + 3*i for i in range(len(points))]
    atoms = [{"i_seq": index, "atom_id": f"X{i}", "xyz": list(xyz),
              "identity": {"chain_id": "B", "resseq": "4", "icode": "", "resname": "XYZ"}}
             for i, (index, xyz) in enumerate(zip(ids, points))]
    proxies = [{"i_seqs": [ids[i] for i in endpoints], "angle_ideal": target, "weight": weight}
               for endpoints, target, weight in angles]
    plane = {"i_seqs": [ids[i] for i in plane_ids], "weights": weights, "origin_id": 0}
    return {"status": "OBSERVED", "sites": [{"site": "B:4", "component": "XYZ"}], "atoms": atoms,
            "coordinate_precision": "NATIVE", "model_state_sha256": "a"*64,
            "geometry": {"proxy_details": {"angle": proxies, "planarity": [plane]}}}


def test_linear_continuation_is_measured_without_tilting_the_fitted_plane():
    points = [(0,0,1), (1,0,1), (0,1,1), (2,.1,1.35), (3,.2,1.55),
              (4,0,3), (5,0,4)]
    angles = [((1,3,4),180.,2.), ((0,1,3),180.,1.),
              ((3,4,5),179.,1.), ((3,4,6),180.,0.)]
    obs = observation(points, [0,1,2], [5.,5.,5.], angles)
    before = deepcopy(obs)
    result = describe_planes(obs)
    plane, = result["planes"]
    assert plane["status"] == "MEASURED" and plane["positive_member_rms_angstrom"] == pytest.approx(0.)
    assert [r["atom"] for r in plane["members"]] == ["X0","X1","X2"]
    ext = plane["linear_extensions"]
    assert [r["atom"] for r in ext] == ["X3","X4"]
    assert [r["angle_proxy_index"] for r in ext] == [1,0]
    assert [r["distance_angstrom"] for r in ext] == pytest.approx([.35,.55])
    assert all(r["observed_angle_degrees"] < r["angle_target_degrees"] for r in ext)
    assert [r["angle_weight"] for r in ext] == [1.,2.]
    assert obs == before and result["scientific_approval"] == "NOT_RUN"


def test_nonuniform_weights_set_plane_and_zero_weight_member_cannot_tilt_it():
    pts = [(-2,0,0),(2,0,0),(0,-2,0),(0,2,0),(0,0,1),(0,0,8)]
    obs = observation(pts,list(range(6)),[1.,1.,1.,1.,4.,0.])
    p, = describe_planes(obs)["planes"]
    assert p["positive_member_rms_angstrom"] == pytest.approx(.5)
    assert [r["distance_angstrom"] for r in p["members"]] == pytest.approx([.5]*5+[7.5])
    assert p["members"][-1]["weight"] == 0.


@pytest.mark.parametrize("points,weights", [
    ([(0,0,0),(1,0,0),(2,0,0)],[1,1,1]),
    ([(0,0,0),(1,0,0),(0,1,0)],[0,0,0]),
    ([(0,0,0),(1,0,0),(0,1,0)],[1,1,0]),
    ([(1,1,1),(1,-1,-1),(-1,1,-1),(-1,-1,1)],[1,1,1,1]),
])
def test_missing_unique_plane_has_no_invented_departure(points,weights):
    result = describe_planes(observation(points,list(range(len(points))),weights))
    plane, = result["planes"]
    assert result["status"] == plane["status"] == "UNASSESSED"
    assert plane["reason"] and all(m["distance_angstrom"] is None for m in plane["members"])
    assert plane["positive_member_rms_angstrom"] is None and plane["linear_extensions"] == []


@pytest.mark.parametrize("weights", [[-1.,1.,1.],[float("nan"),1.,1.],[1.,True,1.],[1.]])
def test_invalid_plane_weights_refuse(weights):
    obs = observation([(0,0,0),(1,0,0),(0,1,0)],[0,1,2],weights)
    with pytest.raises(ValueError):
        describe_planes(obs)


def test_unavailable_angles_and_absent_planes_stay_distinct():
    obs = observation([(0,0,0),(1,0,0),(0,1,0),(2,0,1)],[0,1,2],[1,1,1],
                      [((0,1,3),180.,None)])
    p, = describe_planes(obs)["planes"]
    assert p["status"] == "MEASURED" and not p["linear_extensions"]
    obs["geometry"]["proxy_details"]["planarity"] = []
    assert describe_planes(obs)["status"] == "UNASSESSED"
    result=describe_planes({"status":"UNASSESSED","reason":"Capture unavailable","sites":[]})
    assert result["reason"]=="Capture unavailable" and not result["planes"]


def test_distances_survive_a_change_of_frame_and_common_weight_scale():
    points = [(0,0,.2),(1,0,0),(0,1,0),(2,2,1),(2.4,2.3,1.5)]
    angles = [((0,3,4),180.,5.)]
    r, = describe_planes(observation(points,[0,1,2,3],[1,2,3,4],angles))["planes"]
    transformed = [(y+8,-x+9,z-7) for x,y,z in points]
    s, = describe_planes(observation(transformed,[0,1,2,3],[3,6,9,12],angles))["planes"]
    assert r["positive_member_rms_angstrom"] == pytest.approx(s["positive_member_rms_angstrom"])
    for category in ["members","linear_extensions"]:
        assert [m["distance_angstrom"] for m in r[category]] == pytest.approx(
            [m["distance_angstrom"] for m in s[category]])


def test_angle_through_coincident_supporting_atoms_cannot_extend_a_plane():
    pts = [(0,0,0),(1,0,0),(0,1,0),(0,0,0),(2,2,1)]
    obs = observation(pts,[0,1,2,3],[1,1,1,1],[((0,3,4),180.,1.)])
    p, = describe_planes(obs)["planes"]
    assert p["status"] == "MEASURED" and not p["linear_extensions"]


def test_existing_owner_relocates_checks_exact_model_and_preserves_reports(tmp_path,monkeypatch):
    from nasolve.refinement_parallelity import read_execution_plane_geometry, read_execution_chemistry
    from tests.test_refinement_parallelity import completed
    run, result, _, child, _, _ = completed(tmp_path,monkeypatch,chemistry="bent")
    old = run.parents[1]
    moved = tmp_path/"relocated"
    old.rename(moved)
    run = moved/run.relative_to(old)
    model = run/child["model"]["relative_path"]
    args = dict(checkpoint=child["id"],parent=child["parent"])
    ref = child["outputs"]["parallelity_execution"]
    snapshot = {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in run.rglob("*") if p.is_file()}
    with patch("subprocess.Popen",side_effect=AssertionError("Cold reader launched a process")):
        report = read_execution_plane_geometry(run,ref,model=model,**args)
        assert report["model_sha256"] == sha256(model.read_bytes()).hexdigest()
        assert report["declared_sites"] == result.statistics["chemical_geometry"]["declared_sites"]
        assert read_execution_chemistry(run,ref,model=model,**args) == result.statistics["chemical_geometry"]
        wrong = tmp_path/"wrong.pdb"
        wrong.write_bytes(model.read_bytes()+b"REMARK different model\n")
        with pytest.raises(ValueError):
            read_execution_plane_geometry(run,ref,model=wrong,**args)
    assert {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in run.rglob("*") if p.is_file()} == snapshot


@pytest.mark.parametrize("chemistry", [None,"unavailable"])
def test_legacy_or_unavailable_capture_remains_explicit(tmp_path, monkeypatch, chemistry):
    from nasolve.refinement_parallelity import read_execution_plane_geometry
    from tests.test_refinement_parallelity import completed
    run,result,_,child,_,_ = completed(tmp_path,monkeypatch,chemistry=chemistry,declared_sites=True)
    report = read_execution_plane_geometry(run,child["outputs"]["parallelity_execution"],
        checkpoint=child["id"],parent=child["parent"],model=result.model_path)
    if chemistry is None:
        assert report is None
    else:
        assert report["status"]=="UNASSESSED" and report["reason"] and report["planes"]==[]


def test_linear_angle_with_two_known_ends_measures_its_middle_atom():
    obs = observation([(0, 0, 0), (2, 0, 0), (0, 1, 0), (1, 0, .5)],
                      [0, 1, 2], [1, 1, 1], [((0, 3, 1), 180., 2.)])
    report = describe_planes(obs)
    middle, = report["planes"][0]["linear_extensions"]
    assert middle["atom"] == "X3"
    assert middle["supporting_i_seqs"] == [7, 10]
    assert middle["angle_i_seqs"] == [7, 16, 10]
    assert middle["distance_angstrom"] == pytest.approx(.5)
    assert middle["observed_angle_degrees"] == pytest.approx(126.86989765)
    assert report["symmetry_context"] == "UNASSESSED"


def test_declared_site_without_plane_is_visible_alongside_a_measured_site():
    obs = observation([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [0, 1, 2], [1, 1, 1])
    obs["sites"].append({"site": "A:1", "component": "ABC"})
    result = describe_planes(obs)
    assert result["status"] == "PARTIAL"
    assert result["sites_without_captured_plane"] == ["A:1"]
    assert result["planes"][0]["status"] == "MEASURED"


@pytest.mark.parametrize("field", ["name", "element", "component"])
def test_checkpoint_plane_reader_checks_atom_identity_against_declared_source(tmp_path, monkeypatch, field):
    from nasolve import refinement_parallelity as owner
    from tests.test_refinement_scalar_geometry import selected

    projections, obs = selected(tmp_path)
    atom = obs["atoms"][0]
    if field == "name":
        atom["atom_id"] = "UNDECLARED"
    elif field == "element":
        atom["element"] = "N"
    else:
        atom["identity"]["resname"] = "BAD"
    monkeypatch.setattr(owner, "_selected_chemistry_observation", lambda *a, **kw: (b"model", projections, obs))
    monkeypatch.setattr(owner, "_declared_chemistry_sources", lambda *a, **kw: {"A:1": {"component": "Q17"}})
    with pytest.raises(ValueError, match="differs from source"):
        owner.read_execution_plane_geometry(tmp_path, {}, checkpoint="refine-001", parent="postmr", model=tmp_path)
