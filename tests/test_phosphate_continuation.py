"""A declared source-frame continuation can be read without guessing either endpoint."""
import json

import pytest

pytest.importorskip("gemmi")
from nasolve.cli import main
from nasolve.construct_registration import build_construct_registration
from nasolve.model_assessment import file_sha256, inspect_pdb
from .test_construct_registration import target
from .test_cif_doctor_run import _child, _reference, _snapshot
from .test_checkpoints import make_checkpoint_run
from .test_phosphate_image import inputs


def put(path, value):
    path.write_text(json.dumps(value))
    return path


def files(root, *, missing=False, absent_atom=False, protected_nick=False):
    model, geo = inputs(root)
    text = model.read_text().replace("Z99", " DC")
    if absent_atom:
        text = "\n".join(line for line in text.splitlines() if line[12:16].strip() != "O3'") + "\n"
    model.write_text(text)
    reg, disc, declarations = register(root, model, missing=missing, protected_nick=protected_nick)
    geo.write_text(geo.read_text().replace("Z99", " DC"))
    return model, geo, reg, disc, declarations


def register(root, model, *, missing=False, protected_nick=False):
    mapping = {"L:1": "B:1"}
    if not missing:
        mapping["L:2"] = "A:7"
    assembly = build_construct_registration(
        inspect_pdb(model), target(("L:1","DC"), ("L:2","DA")), {"strand": mapping}, source="test strand"
    )
    reg = put(root/"registration.json", assembly)
    disc = put(root/"ends.json", dict(
        schema_version=1, kind="topostitch-end-discovery-input", model_sha256=file_sha256(model),
        registration_sha256=file_sha256(reg), copy_id="strand",
        strands=[dict(strand_id="central", sites=["L:1","L:2"],
                     five_prime_boundary="chemical" if protected_nick else "representation",
                     three_prime_boundary="representation")],
        duplex_pairs=[], protected_sites=[], do_not_connect_sites=[], pairing_inventory_complete=False,
    ))
    edge = dict(continuation_id=9, source_site="L:2", target_site="L:1", target_operator_xyz="x+1,y,z")
    declarations = put(root/"edges.json", [edge])
    return reg, disc, declarations


def invoke(model, reg, disc, edges, *extra):
    return main(["cif-doctor", "phosphate-image", str(model), "--registered-continuation", "9",
                 "--registration", str(reg), "--discovery-input", str(disc),
                 "--backbone-continuations", str(edges), *map(str, extra)])


def test_registered_sites_use_actual_coordinate_labels_and_keep_the_directed_image(tmp_path, capsys):
    model, geo, reg, disc, edges = files(tmp_path)
    before = _snapshot(tmp_path)
    assert invoke(model, reg, disc, edges, "--geometry", geo, "--json") == 0
    observed = json.loads(capsys.readouterr().out)
    declared = observed["registered_continuation"]
    assert declared["source"]["logical_site"] == "L:2" and declared["source"]["coordinate_site"] == "A:7"
    assert declared["target"]["logical_site"] == "L:1" and declared["target"]["coordinate_site"] == "B:1"
    assert declared["target_operator_xyz"] == "x+1,y,z" and observed["o3_image"] == "x-1,y,z"
    assert observed["distance_A"] == pytest.approx(3) and observed["scientific_approval"] == "NOT_ASSESSED"
    assert len(observed["printed_geometry"]["nonbonded"]["matches"]) == 1
    assert declared["sources"] == {"registration_sha256": file_sha256(reg), "discovery_sha256": file_sha256(disc),
                                   "continuations_sha256": file_sha256(edges)}
    assert str(tmp_path) not in json.dumps(observed) and _snapshot(tmp_path) == before
    row, = json.loads(edges.read_bytes())
    put(edges, [dict(row, target_operator_xyz="x,y,z")])
    assert invoke(model, reg, disc, edges, "--json") == 0
    assert json.loads(capsys.readouterr().out)["distance_A"] == pytest.approx(17)


@pytest.mark.parametrize("kind", ["missing mapping", "missing oxygen"])
def test_declared_edge_survives_an_unmeasurable_endpoint(tmp_path, capsys, kind):
    model, geo, reg, disc, edges = files(tmp_path, missing=kind=="missing mapping", absent_atom=kind=="missing oxygen")
    assert invoke(model, reg, disc, edges, "--geometry", geo, "--json") == 0
    report = json.loads(capsys.readouterr().out)
    intent = report["registered_continuation"]
    assert intent["measurement_status"] == "UNRESOLVED" and intent["source"]["logical_site"] == "L:2"
    assert report["distance_A"] is None and report["phosphate_atoms"] is None
    assert report["printed_geometry"]["geometry_sha256"] == file_sha256(geo)
    assert report["scientific_approval"] == "NOT_ASSESSED"


@pytest.mark.parametrize("damage", ["chemical terminus", "changed model", "wrong ID", "manual endpoints"])
def test_changed_or_contradictory_inputs_cannot_supply_a_measurement(tmp_path, capsys, damage):
    model, _, reg, disc, edges = files(tmp_path, protected_nick=damage=="chemical terminus")
    if damage == "changed model":
        model.write_bytes(model.read_bytes()+b"\n")
    if damage == "wrong ID":
        row, = json.loads(edges.read_bytes())
        put(edges, [dict(row, continuation_id=8)])
    extra = ["--o3","A:7"] if damage == "manual endpoints" else []
    assert invoke(model, reg, disc, edges, *extra, "--json") == 1
    assert not capsys.readouterr().out


def test_registered_continuation_reopens_the_exact_checkpoint_after_relocation(tmp_path, capsys):
    original = tmp_path/"original"
    original.mkdir()
    model, geometry, reg, disc, edges = files(original)
    run = make_checkpoint_run(original/"dataset")
    parent = run/"PostMR/Model/readyset_model.pdb"
    parent.write_bytes(model.read_bytes())
    report = json.loads((run/"report.json").read_bytes())
    report["postmr"]["prepared_sha256"] = file_sha256(parent)
    put(run/"report.json", report)
    _child(run)
    registry = run/"AutoRefine/checkpoints.json"
    data = json.loads(registry.read_bytes())
    child = data["checkpoints"][-1]
    geo = (run/child["model"]["relative_path"]).with_suffix(".geo")
    geo.write_bytes(geometry.read_bytes())
    child.update(kind="refinement", outputs={"final_geometry": _reference(geo,run)})
    put(registry,data)
    assert invoke(run, reg, disc, edges, "--checkpoint", "refine-001", "--json") == 1
    assert "checksum" in capsys.readouterr().err
    reg, disc, edges = register(original, run/child["model"]["relative_path"])
    moved = original.rename(tmp_path/"moved")
    actual = moved/run.relative_to(original)
    before = _snapshot(moved)
    assert invoke(actual, moved/reg.name, moved/disc.name, moved/edges.name, "--checkpoint", "refine-001", "--json")==0
    reading=json.loads(capsys.readouterr().out)
    assert reading["checkpoint"]["id"]=="refine-001" and reading["distance_A"]==pytest.approx(3)
    assert reading["registered_continuation"]["measurement_status"]=="MEASURED"
    assert _snapshot(moved)==before and not original.exists()


def test_numbered_restart_carries_its_ancestors_image_after_relocation(tmp_path, capsys):
    original = tmp_path / "original"
    original.mkdir()
    model, _, reg, disc, edges = files(original)
    run = make_checkpoint_run(original / "dataset")
    parent = run / "PostMR/Model/readyset_model.pdb"
    parent.write_bytes(model.read_bytes())
    report = json.loads((run / "report.json").read_bytes())
    report["postmr"]["prepared_sha256"] = file_sha256(parent)
    put(run / "report.json", report)
    child = _child(run)
    coordinates = run / child["model"]["relative_path"]
    coordinates.write_text(coordinates.read_text().replace("  19.000", "  18.500"))
    registry = run / "AutoRefine/checkpoints.json"
    tree = json.loads(registry.read_bytes())
    tree["checkpoints"][-1]["model"] = _reference(coordinates, run)
    tree["current"] = "postmr"
    put(registry, tree)
    parent_hash, child_hash = file_sha256(parent), file_sha256(coordinates)
    moved = original.rename(tmp_path / "moved")
    actual = moved / run.relative_to(original)
    args = (actual, moved / reg.name, moved / disc.name, moved / edges.name)
    before = _snapshot(moved)
    assert invoke(*args, "--checkpoint", "first-refinement", "--registration-checkpoint", "postmr", "--json") == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["checkpoint"]["id"] == "refine-001"
    declaration = observed["registered_continuation"]
    assert declaration["source"]["logical_site"] == "L:2"
    assert declaration["oxygen_operator_xyz"] == "x-1,y,z"
    transfer = declaration["frame_transfer"]
    assert transfer["source_checkpoint"] == "postmr"
    assert transfer["source_model_sha256"] == parent_hash
    assert transfer["child_model_sha256"] == child_hash == observed["model_sha256"]
    assert transfer["atom_count"] == 5 and transfer["max_atom_shift_A"] == pytest.approx(.5)
    assert observed["distance_A"] == pytest.approx(3.5)
    assert observed["printed_geometry"] is None and declaration["runtime_authority"] is False
    assert not original.exists() and _snapshot(moved) == before
    assert invoke(*args, "--checkpoint", "postmr", "--registration-checkpoint", "first-refinement", "--json") == 1
    assert "ancestor" in capsys.readouterr().err
    assert _snapshot(moved) == before


@pytest.mark.parametrize(("change", "message"), [
    ("crystal", "crystal frame"), ("rename", "chemical identities"),
    ("element", "chemical identities"), ("charge", "chemical identities"),
    ("unoccupied", "chemical identities"), ("lattice translation", "crystal representative"),
    ("image tie", "crystal representative"),
])
def test_inherited_edge_requires_the_same_local_chemistry_and_image(tmp_path, change, message):
    from nasolve.cif_phosphate_continuation import RegisteredContinuation, inspect_inherited_continuation
    source, _, reg, disc, edges = files(tmp_path)
    lines = source.read_text().splitlines()
    for i, line in enumerate(lines):
        if change == "crystal" and line.startswith("CRYST1"):
            lines[i] = line.replace("20.000", "21.000", 1)
        if line[12:16].strip() == "OP1":
            lines[i] = {
                "rename": line.replace("OP1", "OP2"),
                "element": line[:76] + " S",
                "charge": line[:78] + "1-",
                "unoccupied": line[:54] + "  0.00" + line[60:],
                "lattice translation": line[:30] + "  22.000" + line[38:],
                "image tie": line[:30] + "  12.000" + line[38:],
            }.get(change, line)
    child = tmp_path / "child.pdb"
    child.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match=message):
        inspect_inherited_continuation(source, child, RegisteredContinuation(9, reg, disc, edges))
