"""Printed covalent planes are distinct from supplied pairing planes and achieved geometry."""
import json

import pytest

from nasolve.cli import main
from nasolve.model_assessment import file_sha256
from .test_cif_doctor import component, write
from .test_cif_doctor_run import _child, _reference, _snapshot
from .test_checkpoints import make_checkpoint_run
from .test_refinement_component_bonds import inputs


def plane_cif(root, *, short=False):
    values = component()
    names = values["_chem_comp_atom.atom_id"][:3 if short else 4]
    for key, rows in (("comp_id", ["X"]*len(names)), ("plane_id", ["ring"]*len(names)),
                      ("atom_id", names), ("dist_esd", [".02"]*len(names))):
        values["_chem_comp_plane_atom."+key] = rows
    return write(root,values,name="short.cif" if short else "ring.cif")


def section(model, origin, weights):
    labels = [line[12:27] for line in model.read_text().splitlines() if line.startswith("ATOM")]
    rows = [f"Planarity | {origin} | restraints: 1", "Sorted by residual:",
            "delta sigma weight rms_deltas residual"]
    for i, weight in enumerate(weights):
        prefix = "plane " if i == 0 else "      "
        summary = " 0.03 2.25" if i == 0 else ""
        rows.append(f'{prefix}pdb="{labels[i]}" 0.010 2.00e-02 {weight:.2e}{summary}')
    return "\n".join(rows)+"\n"


def direct(capsys, dictionaries, model, geo):
    result = main(["cif-doctor","assess",*map(str,dictionaries),"--model",str(model),
                   "--refined-planes",str(geo),"--json"])
    assert result in (0,2), capsys.readouterr().err
    return json.loads(capsys.readouterr().out)["refined_printed_planes"]


def test_only_positive_covalent_members_cover_the_modelled_cif_plane(tmp_path,capsys):
    _,model,geo = inputs(tmp_path)
    dictionary = plane_cif(tmp_path)
    geo.write_text(section(model,"covalent geometry",[2500]*3+[0])+section(model,"User supplied",[2500]*4))
    before = _snapshot(tmp_path)
    report = direct(capsys,[dictionary],model,geo)
    assert report["sections"] == {"covalent geometry":1,"User supplied":1}
    site, = report["sites"]
    assert site["site"] == "B:4"
    plane, = site["dictionary_planes"]
    assert plane["status"] == "NO_EXACT_MODELED_MATCH"
    assert plane["modeled_atoms_without_positive_covalent_plane"] == ["C1'"]
    assert site["printed_planes"][0]["members"][-1]["weight"] == 0
    assert _snapshot(tmp_path) == before
    geo.write_text(section(model,"covalent geometry",[2500]*4))
    matched, = direct(capsys,[dictionary],model,geo)["sites"][0]["dictionary_planes"]
    assert matched["status"] == "EXACT_MODELED_MEMBERS" and matched["matching_covalent_planes"] == [1]


def test_ambiguous_definitions_and_unmodelled_atoms_stay_visible(tmp_path,capsys):
    _,model,geo = inputs(tmp_path)
    full,short = plane_cif(tmp_path),plane_cif(tmp_path,short=True)
    geo.write_text(section(model,"covalent geometry",[2500]*3))
    ambiguous, = direct(capsys,[full,short],model,geo)["sites"]
    assert ambiguous["dictionary_planes"] is None and ambiguous["input_indices"] == [0,1]
    model.write_text("\n".join(line for line in model.read_text().splitlines() if line[12:16].strip() != "C1'")+"\n")
    plane, = direct(capsys,[full],model,geo)["sites"][0]["dictionary_planes"]
    assert plane["unmodeled_atoms"] == ["C1'"] and plane["status"] == "EXACT_MODELED_MEMBERS"


def test_pairing_planes_alone_leave_covalent_membership_unmeasured(tmp_path, capsys):
    _, model, geo = inputs(tmp_path)
    geo.write_text(section(model, "User supplied", [2500] * 4))
    report = direct(capsys, [plane_cif(tmp_path)], model, geo)
    plane, = report["sites"][0]["dictionary_planes"]
    assert plane["status"] == "COVALENT_SECTION_NOT_RECORDED"
    assert plane["modeled_atoms_without_positive_covalent_plane"] is None


def test_alternate_atom_identity_leaves_only_the_optional_reading_unassessed(tmp_path, capsys):
    _, model, geo = inputs(tmp_path)
    geo.write_text(section(model, "covalent geometry", [2500] * 4))
    lines = model.read_text().splitlines(keepends=True)
    atom = next(i for i, line in enumerate(lines) if line.startswith("ATOM"))
    lines[atom] = lines[atom][:16] + "A" + lines[atom][17:]
    model.write_text("".join(lines))
    reading = direct(capsys, [plane_cif(tmp_path)], model, geo)
    assert reading["status"] == "UNASSESSED" and reading["sites"] is None
    assert "Alternate" in reading["reason"]
    assert reading["model_sha256"] == file_sha256(model)


@pytest.mark.parametrize("damage", ["missing group", "unknown label", "invalid weight", "duplicate member", "short group"])
def test_malformed_tables_do_not_return_partial_membership(tmp_path,capsys,damage):
    _,model,geo = inputs(tmp_path)
    dictionary = plane_cif(tmp_path)
    table = section(model,"covalent geometry",[2500]*4)
    if damage == "missing group":
        table = table.replace("restraints: 1","restraints: 2")
    elif damage == "unknown label":
        table = table.replace('pdb="  C5','pdb="  Q9',1)
    elif damage == "invalid weight":
        table = table.replace("2.50e+03","nan",1)
    elif damage == "duplicate member":
        table += table.splitlines()[-1]+"\n"
    else:
        table = "\n".join(table.splitlines()[:-2])+"\n"
    geo.write_text(table)
    report = direct(capsys,[dictionary],model,geo)
    assert report["status"] == "UNASSESSED" and report["sites"] is None


def test_registered_plane_read_uses_only_the_named_checkpoints_geometry(tmp_path,capsys):
    run = make_checkpoint_run(tmp_path/"original")
    _child(run)
    _,model,geo = inputs(tmp_path)
    cif = plane_cif(tmp_path)
    registry_path = run/"AutoRefine/checkpoints.json"
    registry = json.loads(registry_path.read_text())
    child = registry["checkpoints"][-1]
    frozen = run/child["model"]["relative_path"]
    frozen.write_bytes(model.read_bytes())
    child["model"] = _reference(frozen,run)
    resource = frozen.parent/"plane-input.cif"
    resource.write_bytes(cif.read_bytes())
    child["restraints"] = [_reference(resource,run)]
    final = frozen.with_suffix(".geo")
    final.write_text(section(frozen,"covalent geometry",[2500]*4))
    child.update(kind="refinement",outputs={"final_geometry":_reference(final,run)})
    registry_path.write_text(json.dumps(registry))
    moved = tmp_path/"relocated"
    (tmp_path/"original").rename(moved)
    actual = moved/run.relative_to(tmp_path/"original")
    before = _snapshot(moved)
    result = main(["cif-doctor","assess","--run",str(actual),"--checkpoint","refine-001","--refined-planes","--json"])
    assert result in (0,2), capsys.readouterr().err
    payload = json.loads(capsys.readouterr().out)
    assert payload["refined_planes"] is None
    assert payload["refined_printed_planes"]["geometry_sha256"] == file_sha256(actual/final.relative_to(run))
    assert payload["refined_printed_planes"]["sites"][0]["dictionary_planes"][0]["status"] == "EXACT_MODELED_MEMBERS"
    assert _snapshot(moved) == before
