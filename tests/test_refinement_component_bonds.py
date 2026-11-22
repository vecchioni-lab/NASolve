"""Read the target Phenix used for an explicit component, including superseding edits."""
import json

from nasolve.cli import main
from nasolve.model_assessment import file_sha256

from .test_cif_doctor import component, write
from .test_cif_doctor_run import _child, _reference, _snapshot
from .test_checkpoints import make_checkpoint_run
from .test_refinement_link_geometry import bond, section


def inputs(directory):
    values = component()
    values["_chem_comp_bond.value_dist"] = ["1.470", "1.430", "1.510"]
    values["_chem_comp_bond.value_dist_esd"] = ["0.020"] * 3
    dictionary = write(directory, values)
    names = values["_chem_comp_atom.atom_id"]
    xyz = [(0, 0, 0), (1.48, 0, 0), (1.48, 1.43, 0), (1.48, 1.43, 1.51)]
    lines = [f"ATOM  {i:5} {name:>4}   X B{4:4}    {a:8.3f}{b:8.3f}{c:8.3f}{1:6.2f}{20:6.2f}          {el:>2}"
             for i, (name, (a, b, c), el) in enumerate(zip(names, xyz, values["_chem_comp_atom.type_symbol"]), 1)]
    model = directory / "before.pdb"
    model.write_text("\n".join(lines + ["END"]) + "\n")
    labels = [f'pdb="{line[12:27]}"' for line in lines]
    geometry = directory / "after.geo"
    geometry.write_text(section("User supplied", bond(labels, 1, 0, "1.607", "1.480", "1.00e-02", "1.00e+04"))
                        + section("covalent geometry", bond(labels, 1, 2, "1.430", "1.430", "2.00e-02", "2.50e+03"),
                                  bond(labels, 2, 3, "1.510", "1.510", "3.00e-02", "1.11e+03")))
    return dictionary, model, geometry


def standalone(capsys, dictionaries, model, geometry):
    rc = main(["cif-doctor", "assess", *map(str, dictionaries), "--model", str(model),
               "--bond-targets", str(geometry), "--json"])
    assert rc in (0, 2)
    return json.loads(capsys.readouterr().out)["refined_bond_targets"]


def test_changed_target_and_sigma_are_compared_separately(tmp_path, capsys):
    dictionary, model, geometry = inputs(tmp_path)
    snapshot = _snapshot(tmp_path)
    report = standalone(capsys, [dictionary], model, geometry)
    assert report["status"] == "OBSERVED"
    assert report["counts"] == {"TARGET_AND_SIGMA_DIFFER": 1, "AGREES": 1, "SIGMA_DIFFERS": 1}
    rows = {tuple(row["atoms"]): row for row in report["observations"]}
    edited = rows[("C5", "C5'")]
    assert (edited["site"], edited["component"], edited["origin"]) == ("B:4", "X", "User supplied")
    assert (edited["dictionary_ideal_A"], edited["printed_ideal_A"], edited["model_A"]) == (1.47, 1.607, 1.480)
    assert edited["printed_sigma_A"] == .01
    assert report["geometry_sha256"] == file_sha256(geometry) and report["scientific_approval"] == "NOT_ASSESSED"
    assert _snapshot(tmp_path) == snapshot


def test_multiple_definitions_and_graph_only_are_not_resolved_by_order(tmp_path, capsys):
    dictionary, model, geometry = inputs(tmp_path)
    graph = write(tmp_path, component(numeric=False), name="graph.cif")
    report = standalone(capsys, [dictionary, graph], model, geometry)
    assert report["counts"] == {"AMBIGUOUS_DEFINITION": 3}
    assert all(row["input_indices"] == [0, 1] for row in report["observations"])
    assert standalone(capsys, [graph], model, geometry)["counts"] == {"NO_NUMERICAL_TARGET": 3}
    duplicate = tmp_path / "other.cif"
    duplicate.write_bytes(dictionary.read_bytes())
    assert standalone(capsys, [dictionary, duplicate], model, geometry)["counts"]["TARGET_AND_SIGMA_DIFFER"] == 1


def test_truncated_and_unprinted_geometry_keep_source_inventory_visible(tmp_path, capsys):
    dictionary, model, geometry = inputs(tmp_path)
    geometry.write_text(geometry.read_text().replace("User supplied | restraints: 1", "User supplied | restraints: 2"))
    table = standalone(capsys, [dictionary], model, geometry)
    assert table["status"] == "UNASSESSED" and table["counts"] is None and table["observations"] is None
    geometry.write_text("# No bond tables\n")
    assert standalone(capsys, [dictionary], model, geometry)["status"] == "NOT_RECORDED"


def test_requested_comparison_requires_review_without_changing_the_dictionary_verdict(tmp_path, capsys):
    dictionary, model, geometry = inputs(tmp_path)
    args = ["cif-doctor", "assess", str(dictionary), "--model", str(model), "--json"]
    assert main(args) == 0
    ordinary = json.loads(capsys.readouterr().out)
    assert ordinary["status"] == "PASS" and "bond_target_status" not in ordinary
    assert main([*args, "--bond-targets", str(geometry)]) == 2
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["status"] == inspected["bond_target_status"] == "REVIEW"
    assert inspected["dictionary_status"] == "PASS"
    assert main([*args, "--bond-targets"]) == 1
    assert "GEO path" in capsys.readouterr().err


def test_printed_rounding_and_alternate_nuclear_targets_are_distinguished(tmp_path, capsys):
    dictionary, model, geometry = inputs(tmp_path)
    values = component()
    values["_chem_comp_bond.value_dist"] = ["1.6069", "1.430", "1.510"]
    values["_chem_comp_bond.value_dist_esd"] = [".01001", ".020", ".030"]
    dictionary = write(tmp_path, values)
    report = standalone(capsys, [dictionary], model, geometry)
    assert report["counts"] == {"AGREES": 3}
    row, = report["observations"]
    assert row["origin"] == "User supplied" and row["comparison"] == "AGREES"
    values["_chem_comp_bond.value_dist_nucleus"] = ["1.617", "?", "?"]
    dictionary = write(tmp_path, values)
    report = standalone(capsys, [dictionary], model, geometry)
    assert report["counts"] == {"SEPARATE_NUCLEAR_TARGET": 1, "AGREES": 2}


def test_checkpoint_uses_its_frozen_effective_dictionary_and_own_geometry(tmp_path, capsys):
    original = tmp_path / "original"
    run = make_checkpoint_run(original)
    dictionary, model, geometry = inputs(tmp_path)
    root_model = run / "PostMR/Model/readyset_model.pdb"
    root_model.write_bytes(model.read_bytes())
    report_path = run / "report.json"
    report = json.loads(report_path.read_bytes())
    report["postmr"]["prepared_sha256"] = file_sha256(root_model)
    report_path.write_text(json.dumps(report))
    _child(run)
    registry_path = run / "AutoRefine/checkpoints.json"
    registry = json.loads(registry_path.read_bytes())
    registry["current"] = "postmr"
    child = registry["checkpoints"][-1]
    child_geo = (run / child["model"]["relative_path"]).with_suffix(".geo")
    effective = run / child["restraints"][1]["relative_path"]
    effective.write_bytes(dictionary.read_bytes())
    child["restraints"][1] = _reference(effective, run)
    child_geo.write_bytes(geometry.read_bytes())
    child.update(kind="refinement", outputs={"final_geometry": _reference(child_geo, run)})
    registry_path.write_text(json.dumps(registry))
    moved = tmp_path / "moved"
    original.rename(moved)
    run = moved / run.relative_to(original)
    before = _snapshot(moved)
    base = ["cif-doctor", "assess", "--run", str(run), "--checkpoint", "first-refinement", "--bond-targets"]
    assert main([*base, "--json"]) == 2
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["preflight_bond_targets"] is None
    assert receipt["refined_bond_targets"]["counts"]["TARGET_AND_SIGMA_DIFFER"] == 1
    assert receipt["refined_bond_targets"]["model_sha256"] == child["model"]["sha256"]
    assert _snapshot(moved) == before
    assert main([*base, str(geometry)]) == 1
    assert "recorded" in capsys.readouterr().err
    selected = run / child["outputs"]["final_geometry"]["relative_path"]
    selected.write_bytes(selected.read_bytes() + b"\n")
    assert main(base) == 1 and "changed after it was frozen" in capsys.readouterr().err
