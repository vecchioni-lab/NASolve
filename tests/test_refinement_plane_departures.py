from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch

import pytest

from nasolve.refinement_plane_departures import describe_planes


def ring_arm_observation(*, extra_bonds=(), revised_orders=None, charge=None, stereo=None):
    from math import cos, pi, sin
    from nasolve.cif_stereochemistry_audit import _graph

    names = ["Q" + str(i) for i in range(11)]
    bonds = [(i, (i+1) % 6, "DOUBLE" if i % 2 == 0 else "SINGLE") for i in range(6)]
    bonds += [(0, 6, "SINGLE"), (6, 7, "TRIPLE"), (7, 8, "SINGLE"), *extra_bonds]
    # The first carbon beyond the triple can have another carbon attached.
    bonds.append((8, 10, "SINGLE"))
    values = {
        "_chem_comp_atom.atom_id": names,
        "_chem_comp_atom.type_symbol": ["N" if i == 2 else "C" for i in range(11)],
        "_chem_comp_atom.charge": ["1" if i == charge else "0" for i in range(11)],
        "_chem_comp_atom.pdbx_stereo_config": ["R" if i == stereo else "N" for i in range(11)],
        "_chem_comp_bond.atom_id_1": [names[i] for i, _, _ in bonds],
        "_chem_comp_bond.atom_id_2": [names[j] for _, j, _ in bonds],
        "_chem_comp_bond.value_order": [(revised_orders or {}).get((i, j), order) for i, j, order in bonds],
    }
    pts = [(cos(i*pi/3), sin(i*pi/3), 2.) for i in range(6)]
    pts += [(2.,0.,2.05),(3.,0.,2.18),(4.,0.,2.4),(0.,1.,3.),(5.,0.,2.5)]
    obs = observation(pts, list(range(7)), [3.] * 7)
    for atom, name in zip(obs["atoms"], names, strict=True):
        atom["atom_id"] = name
    return {"B:4": (values, _graph(values))}, obs


def test_same_source_ring_reference_survives_changing_native_plane_membership():
    from nasolve.refinement_plane_departures import measure_source_ring_arms

    sources, obs = ring_arm_observation()
    for include_tip in (False, True):
        if include_tip:
            obs["geometry"]["proxy_details"]["planarity"][0]["i_seqs"].append(obs["atoms"][8]["i_seq"])
            obs["geometry"]["proxy_details"]["planarity"][0]["weights"].append(3.)
        native = describe_planes(obs)["planes"]
        arm, = measure_source_ring_arms(sources, obs, native)
        assert arm["status"] == "MEASURED" and arm["component"] == "XYZ"
        assert arm["ring_atoms"] == ["Q" + str(i) for i in range(6)]
        assert arm["arm_atoms"] == ["Q0", "Q6", "Q7", "Q8"]
        assert arm["ring_rms_angstrom"] == pytest.approx(0., abs=1e-12)
        assert arm["arm_distances_angstrom"] == pytest.approx({"Q6":.05, "Q7":.18, "Q8":.4})
        plane, = arm["captured_ring_planes"]
        assert plane == {"proxy_index": 0, "positive_arm_members": ["Q6", "Q8"] if include_tip else ["Q6"]}
    assert measure_source_ring_arms(sources, obs, [])[0]["arm_distances_angstrom"]["Q8"] == pytest.approx(.4)


def test_arm_comparison_measures_the_terminal_bond_even_when_the_tip_gets_flatter():
    from nasolve.refinement_plane_departures import compare_source_ring_arms

    sources, before = ring_arm_observation()
    after = deepcopy(before)
    after["atoms"][8]["xyz"] = [4.5, 0., 2.01]
    for index, phase in enumerate((before, after)):
        for atom in phase["atoms"]:
            atom["i_seq"] += 100 * index
        atoms = phase["atoms"]
        phase["geometry"]["proxy_details"]["bond_simple"] = [{
            "i_seqs": [atoms[8]["i_seq"], atoms[7]["i_seq"]],
            "distance_ideal": 1.47, "weight": 2500., "origin_id": 0, "slack": 0.,
        }]
    comparison = compare_source_ring_arms(sources, before, after)
    arm, = comparison["arms"]
    assert comparison["status"] == "MEASURED" and arm["site"] == "B:4"
    assert arm["arm_atoms"] == ["Q0", "Q6", "Q7", "Q8"]
    assert arm["tip_height_change_A"] == pytest.approx(-.39)
    assert arm["terminal_bond_change_A"] > .45
    assert arm["refined"]["tip_height_A"] == pytest.approx(.01)
    assert arm["refined"]["terminal_targets"] == [
        {"ideal_A": 1.47, "weight": 2500., "sigma_A": .02, "origin_id": 0, "symmetry_operation": None}]
    proxy, = after["geometry"]["proxy_details"]["bond_simple"]
    proxy["symmetry_operation"] = "-x,y,-z"
    image = compare_source_ring_arms(sources, before, after)["arms"][0]["refined"]
    assert image["terminal_targets"] == [] and image["terminal_image_targets"][0]["symmetry_operation"] == "-x,y,-z"
    after["geometry"]["proxy_details"]["bond_simple"] = []
    result = compare_source_ring_arms(sources, before, after)["arms"][0]
    assert result["refined"]["terminal_targets"] == []
    assert result["terminal_bond_change_A"] == arm["terminal_bond_change_A"]


def test_arm_comparison_explains_unavailable_geometry_and_missing_atoms():
    from nasolve.refinement_plane_departures import compare_source_ring_arms

    sources, before = ring_arm_observation()
    after = deepcopy(before)
    after["atoms"].pop(8)
    for phase in (before, after):
        phase["geometry"]["proxy_details"]["bond_simple"] = []
    result = compare_source_ring_arms(sources, before, after)
    arm, = result["arms"]
    assert result["status"] == "PARTIAL" and arm["tip_height_change_A"] is None
    assert arm["refined"]["status"] == "UNASSESSED" and "missing" in arm["refined"]["reason"].lower()
    unknown = {"status": "UNASSESSED", "reason": "Selected atoms unavailable", "sites": before["sites"]}
    result = compare_source_ring_arms(sources, unknown, after)
    assert result["status"] == "UNASSESSED" and result["unavailable"] == {"preflight": unknown["reason"]}


@pytest.mark.parametrize("case", [
    {"charge": 7}, {"stereo": 0}, {"stereo": 6}, {"revised_orders": {(0,1):"SINGLE"}},
    {"revised_orders": {(6,7):"DOUBLE"}}, {"extra_bonds":[(8, 4, "SINGLE")]},
])
def test_ring_arm_requires_the_declared_neutral_pendant_carbon_alkyne(case):
    from nasolve.refinement_plane_departures import measure_source_ring_arms

    sources, obs = ring_arm_observation(**case)
    assert measure_source_ring_arms(sources, obs, []) == []


def test_ring_arm_reports_ambiguous_ring_missing_atoms_and_degenerate_ring():
    from nasolve.refinement_plane_departures import measure_source_ring_arms

    sources, obs = ring_arm_observation(extra_bonds=[(2,9,"SINGLE"), (9,4,"SINGLE")])
    ambiguous, = measure_source_ring_arms(sources, obs, [])
    assert ambiguous["status"] == "UNASSESSED" and ambiguous["candidate_ring_count"] == 2
    sources, obs = ring_arm_observation()
    del obs["atoms"][8]
    missing, = measure_source_ring_arms(sources, obs, [])
    assert missing["status"] == "UNASSESSED" and missing["missing_atoms"] == ["Q8"]
    sources, obs = ring_arm_observation()
    for i, atom in enumerate(obs["atoms"][:6]):
        atom["xyz"] = [float(i), 0., 0.]
    degenerate, = measure_source_ring_arms(sources, obs, [])
    assert degenerate["status"] == "UNASSESSED" and "unique plane" in degenerate["reason"]


def test_nitrile_and_unknown_carbon_charge_do_not_create_a_source_ring_arm():
    from nasolve.cif_stereochemistry_audit import _graph
    from nasolve.refinement_plane_departures import measure_source_ring_arms

    for field, value in (("type_symbol", "N"), ("charge", "?")):
        sources, obs = ring_arm_observation()
        values, _ = sources["B:4"]
        values["_chem_comp_atom." + field][7] = value
        assert measure_source_ring_arms({"B:4": (values, _graph(values))}, obs, []) == []


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


def test_distant_member_cannot_tilt_its_own_independent_reference():
    points = [(-1,0,0), (1,0,0), (0,-1,0), (0,1,0), (5,0,1), (0,0,2)]
    weights = [1., 2., 3., 4., 5., 0.]
    obs = observation(points, list(range(6)), weights)
    original, = describe_planes(obs)["planes"]
    reported = describe_planes(obs, omit_each_member=True)
    plane, = reported["planes"]
    tip, inactive = plane["members"][-2:]
    assert reported["policy_id"] == "refinement-declared-site-plane-departures-v2"
    assert 0. < tip["distance_angstrom"] < .1
    assert tip["other_members"] == {"distance_angstrom": pytest.approx(1.), "reason": None}
    assert inactive["other_members"]["distance_angstrom"] == pytest.approx(inactive["distance_angstrom"])
    for before, after in zip(original["members"], plane["members"]):
        assert {k: v for k, v in after.items() if k != "other_members"} == before
    moved = [(z+7, x-5, y+3) for x, y, z in points]
    other = observation(moved, list(range(6)), [w*11 for w in weights])
    transformed, = describe_planes(other, omit_each_member=True)["planes"]
    assert [m["other_members"]["distance_angstrom"] for m in transformed["members"]] == pytest.approx(
        [m["other_members"]["distance_angstrom"] for m in plane["members"]])


def test_member_omission_only_reports_a_distance_with_independent_support():
    obs = observation([(0,0,0), (1,0,0), (2,0,0), (0,1,1)], [0,1,2,3], [1,1,1,1])
    plane, = describe_planes(obs, omit_each_member=True)["planes"]
    assert plane["status"] == "MEASURED"
    assert plane["members"][0]["other_members"]["distance_angstrom"] == pytest.approx(0.)
    outside = plane["members"][-1]["other_members"]
    assert outside["distance_angstrom"] is None and "unique" in outside["reason"]
    obs["geometry"]["proxy_details"]["planarity"][0]["weights"][2] = 0
    plane, = describe_planes(obs, omit_each_member=True)["planes"]
    assert "three" in plane["members"][0]["other_members"]["reason"]
    assert plane["members"][2]["other_members"]["distance_angstrom"] == pytest.approx(0.)


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
        excluded = read_execution_plane_geometry(run,ref,model=model,omit_each_member=True,**args)
        assert excluded["policy_id"] == "refinement-declared-site-plane-departures-v2"
        assert excluded["source_ring_arms"] == []
        assert "source_ring_arms" not in report
        assert excluded["model_sha256"] == report["model_sha256"]
        assert report["model_sha256"] == sha256(model.read_bytes()).hexdigest()
        assert report["declared_sites"] == result.statistics["chemical_geometry"]["declared_sites"]
        assert read_execution_chemistry(run,ref,model=model,**args) == result.statistics["chemical_geometry"]
        wrong = tmp_path/"wrong.pdb"
        wrong.write_bytes(model.read_bytes()+b"REMARK different model\n")
        with pytest.raises(ValueError):
            read_execution_plane_geometry(run,ref,model=wrong,**args)
        with pytest.raises(ValueError):
            read_execution_plane_geometry(run,ref,model=wrong,omit_each_member=True,**args)
    assert {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in run.rglob("*") if p.is_file()} == snapshot


@pytest.mark.parametrize("chemistry", [None,"unavailable"])
def test_legacy_or_unavailable_capture_remains_explicit(tmp_path, monkeypatch, chemistry):
    from nasolve.refinement_parallelity import read_execution_plane_geometry
    from tests.test_refinement_parallelity import completed
    run,result,_,child,_,_ = completed(tmp_path,monkeypatch,chemistry=chemistry,declared_sites=True)
    report = read_execution_plane_geometry(run,child["outputs"]["parallelity_execution"],
        checkpoint=child["id"],parent=child["parent"],model=result.model_path,compare_preflight=True)
    if chemistry is None:
        assert report is None
    else:
        assert report["status"]=="UNASSESSED" and report["reason"] and report["planes"]==[]
        change = report["source_ring_arm_changes"]
        assert change["status"] == "UNASSESSED" and change["written_model_sha256"] is None
        assert change["unavailable"].keys() == {"preflight", "refined"}


def test_cif_doctor_reads_selected_refined_planes_without_changing_checkpoint(tmp_path, monkeypatch, capsys):
    import json
    from nasolve.cli import main
    from tests.test_refinement_parallelity import completed

    run, _, registry, child, _, _ = completed(tmp_path, monkeypatch, chemistry="bent")
    entrance = next(row for row in registry["checkpoints"] if row["id"] == child["parent"])
    moved = tmp_path / "moved"
    old = run.parents[1]
    old.rename(moved)
    run = moved / run.relative_to(old)
    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in run.rglob("*") if p.is_file()}
    capsys.readouterr()
    with patch("subprocess.Popen", side_effect=AssertionError("Inspection launched a process")):
        for checkpoint in (child["id"], "postmr"):
            code = main(["cif-doctor", "assess", "--run", str(run), "--checkpoint", checkpoint,
                         "--refined-planes", "--json"])
            assert code in (0, 2, 3)
            receipt = json.loads(capsys.readouterr().out)
            assert receipt["run_context"]["checkpoint"]["id"] == checkpoint
            if checkpoint == "postmr":
                assert receipt["refined_planes"] is None
            else:
                assert receipt["refined_planes"]["schema_version"] == 2
                assert receipt["refined_planes"]["model_sha256"] == child["model"]["sha256"]
                phases = receipt["refined_planes"]["source_ring_arm_changes"]
                assert phases["status"] == "NO_ELIGIBLE_ARMS" and phases["arms"] == []
                assert phases["input_model_sha256"] == entrance["model"]["sha256"]
                assert phases["written_model_sha256"] == child["model"]["sha256"]
    assert before == {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in run.rglob("*") if p.is_file()}


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
