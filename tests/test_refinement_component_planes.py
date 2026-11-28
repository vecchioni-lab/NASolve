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


def arm_inputs(root, *, charge=None, second_site=False):
    from .test_refinement_plane_departures import ring_arm_observation
    sources, observation = ring_arm_observation(charge=charge)
    values, _ = sources["B:4"]
    values = dict(values, data_="comp_XYZ")
    for category in ("atom", "bond"):
        count = len(values["_chem_comp_"+category+(".atom_id" if category=="atom" else ".atom_id_1")])
        values["_chem_comp_"+category+".comp_id"] = ["XYZ"] * count
    cif = write(root, values, "alternative.cif" if charge is not None else "ordinary.cif")
    model, geo = root/"arm.pdb", root/"arm.geo"
    records = []
    for num in ([4,5] if second_site else [4]):
        for atom, element in zip(observation["atoms"],values["_chem_comp_atom.type_symbol"],strict=True):
            name = atom["atom_id"]
            x,y,z = atom["xyz"]
            occ = 0. if name=="Q8" and num==5 else 1.
            records.append(f"ATOM  {len(records)+1:5d} {name:>4s} XYZ B{num:4}    "
                           f"{x:8.3f}{y:8.3f}{z:8.3f}{occ:6.2f}{20.:6.2f}          {element:>2}")
    model.write_text("\n".join([*records,"END",""]))
    geo.write_text("Bond | covalent geometry | restraints: 0\n")
    return cif, model, geo


def test_dictionary_alkyne_measurement_works_without_a_printed_plane(tmp_path, capsys):
    cif,model,geo = arm_inputs(tmp_path, second_site=True)
    before = _snapshot(tmp_path)
    report = direct(capsys,[cif],model,geo)
    assert report["status"] == "NOT_RECORDED"
    good, absent = report["written_ring_arms"]
    assert good["tip_plane_comparisons"] is None
    assert good["site"] == "B:4" and good["arm_atoms"] == ["Q0","Q6","Q7","Q8"]
    assert good["arm_distances_angstrom"]["Q8"] == pytest.approx(.4)
    assert good["bond_directions"]["segments"][-1]["length_A"] > 1
    assert absent["site"] == "B:5" and absent["status"] == "UNASSESSED"
    assert absent["missing_atoms"] == ["Q8"]
    assert _snapshot(tmp_path) == before


def test_conflicting_alkyne_definitions_cannot_choose_the_ring(tmp_path,capsys):
    cif,model,geo = arm_inputs(tmp_path)
    changed,_,_ = arm_inputs(tmp_path,charge=6)
    assert direct(capsys,[changed],model,geo)["written_ring_arms"] == []
    conflict, = direct(capsys,[cif,changed],model,geo)["written_ring_arms"]
    assert conflict["status"] == "UNASSESSED" and "conflict" in conflict["reason"].lower()


def test_two_components_in_one_cif_block_keep_their_own_charges(tmp_path, capsys):
    from .test_refinement_plane_departures import ring_arm_observation

    _, model, geo = arm_inputs(tmp_path, second_site=True)
    combined = {"data_": "two_components"}
    for code, charge in (("XYZ", None), ("ABC", 6)):
        sources, _ = ring_arm_observation(charge=charge)
        values = dict(sources["B:4"][0])
        for category, field in (("atom", "atom_id"), ("bond", "atom_id_1")):
            prefix = "_chem_comp_" + category + "."
            values[prefix + "comp_id"] = [code] * len(values[prefix + field])
        for tag, entries in values.items():
            combined.setdefault(tag, []).extend(entries)
    cif = write(tmp_path, combined)
    model.write_text(model.read_text().replace("XYZ B   5", "ABC B   5"))
    arm, = direct(capsys, [cif], model, geo)["written_ring_arms"]
    assert (arm["site"], arm["component"], arm["status"]) == ("B:4", "XYZ", "MEASURED")


def test_bad_printed_table_and_wrong_model_element_have_separate_outcomes(tmp_path,capsys):
    cif,model,geo = arm_inputs(tmp_path)
    geo.write_text("Planarity | broken header\n")
    report = direct(capsys,[cif],model,geo)
    assert report["status"] == "UNASSESSED"
    arm, = report["written_ring_arms"]
    assert arm["status"] == "MEASURED" and arm["arm_distances_angstrom"]["Q8"] == pytest.approx(.4)
    records = model.read_text().splitlines(keepends=True)
    index = next(i for i,row in enumerate(records) if row[12:16].strip()=="Q8")
    records[index] = records[index][:76]+" N"+records[index][78:]
    model.write_text("".join(records))
    arm, = direct(capsys,[cif],model,geo)["written_ring_arms"]
    assert arm["status"] == "UNASSESSED" and arm["missing_atoms"] == ["Q8"]


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


def tip_plane(model, members, *, zero_weight=(), foreign=None, tip_weight=100):
    records = [line for line in model.read_text().splitlines() if line.startswith("ATOM")]
    rows = ["Planarity | User supplied | restraints: 1", "Sorted by residual:",
            "delta sigma weight rms_deltas residual"]
    for i, atom in enumerate(members):
        residue = 5 if atom == foreign else 4
        label, = [line[12:27] for line in records
                  if line[12:16].strip() == atom and int(line[22:26]) == residue]
        weight = tip_weight if atom == "Q8" else 100
        if atom in zero_weight:
            weight = 0
        prefix, summary = ("plane ", " 0.10 1.0") if i == 0 else ("      ", "")
        rows.append(f'{prefix}pdb="{label}" -0.180 0.1 {weight}{summary}')
    return "\n".join(rows) + "\n"


def test_measures_tip_against_the_same_plane_with_and_without_its_own_weight(tmp_path, capsys):
    cif, model, geo = arm_inputs(tmp_path)
    ring = [f"Q{i}" for i in range(6)]
    geo.write_text(tip_plane(model, [*ring, "Q8"]))
    arm, = direct(capsys, [cif], model, geo)["written_ring_arms"]
    comparison, = arm["tip_plane_comparisons"]
    assert (comparison["status"], comparison["origin"], comparison["section_index"]) == ("MEASURED", "User supplied", 1)
    assert arm["arm_distances_angstrom"]["Q8"] == pytest.approx(.4)
    assert comparison["tip_to_other_members_plane_A"] == pytest.approx(.4)
    assert 0 < comparison["tip_to_all_members_plane_A"] < .1
    assert 3 < comparison["tilt_on_omitting_tip_deg"] < 7
    # The artificial GEO carries unrelated deltas. Keep the printed observation
    # separate from the geometry recomputed on the supplied coordinates.
    assert comparison["printed_tip_distance_A"] == pytest.approx(.18)
    assert comparison["max_printed_distance_difference_A"] > .1

    geo.write_text(tip_plane(model, [*ring, "Q8"], tip_weight=10))
    lighter, = direct(capsys, [cif], model, geo)["written_ring_arms"][0]["tip_plane_comparisons"]
    assert lighter["tip_to_all_members_plane_A"] > comparison["tip_to_all_members_plane_A"]
    assert lighter["tilt_on_omitting_tip_deg"] < comparison["tilt_on_omitting_tip_deg"]
    assert lighter["tip_to_other_members_plane_A"] == pytest.approx(.4)

    geo.write_text(tip_plane(model, [*ring, "Q8", "Q9"]))
    comparison, = direct(capsys, [cif], model, geo)["written_ring_arms"][0]["tip_plane_comparisons"]
    assert comparison["positive_member_count"] == 8
    assert comparison["tip_to_other_members_plane_A"] != pytest.approx(.4)


@pytest.mark.parametrize("zero,foreign", [(["Q8"], None), (["Q1"], None), ([], "Q3")])
def test_tip_comparison_requires_the_whole_positive_ring_and_tip_at_one_site(tmp_path, capsys, zero, foreign):
    cif, model, geo = arm_inputs(tmp_path, second_site=True)
    geo.write_text(tip_plane(model, [*(f"Q{i}" for i in range(6)), "Q8"], zero_weight=zero, foreign=foreign))
    measured, missing = direct(capsys, [cif], model, geo)["written_ring_arms"]
    assert measured["tip_plane_comparisons"] == []
    assert missing["tip_plane_comparisons"] is None


def test_unoccupied_extra_member_prevents_a_partial_plane_fit(tmp_path, capsys):
    cif, model, geo = arm_inputs(tmp_path)
    records = model.read_text().splitlines(keepends=True)
    index = next(i for i, row in enumerate(records) if row[12:16].strip() == "Q9")
    records[index] = records[index][:54] + "  0.00" + records[index][60:]
    model.write_text("".join(records))
    geo.write_text(tip_plane(model, [*(f"Q{i}" for i in range(6)), "Q8", "Q9"]))
    arm, = direct(capsys, [cif], model, geo)["written_ring_arms"]
    comparison, = arm["tip_plane_comparisons"]
    assert arm["status"] == "MEASURED"
    assert comparison["status"] == "UNASSESSED"
    assert comparison["unavailable_atoms"] == ["Q9"]
    assert comparison["tip_to_all_members_plane_A"] is None
