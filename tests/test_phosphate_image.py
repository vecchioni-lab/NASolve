"""The named O3' image can be a nonbonded neighbour, even with P/OP1/OP2."""
import json

import pytest

from nasolve.cli import main


def inputs(root):
    atoms = [
        ("B", 1, "Z99", "P", "P", (2, 2, 2)),
        ("B", 1, "Z99", "OP1", "O", (2, 3, 2)),
        ("B", 1, "Z99", "O5'", "O", (2, 2, 3)),
        ("A", 7, "DA", "O3'", "O", (19, 2, 2)),
        ("A", 7, "DA", "C3'", "C", (19, 3, 2)),
    ]
    lines = [
        f"ATOM  {i:5} {name:>4} {code:>3} {chain}{site:4}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}{1:6.2f}{30:6.2f}          {element:>2}"
        for i, (chain, site, code, name, element, (x, y, z)) in enumerate(atoms, 1)
    ]
    model = root / "model.pdb"
    model.write_text("CRYST1   20.000   20.000   20.000  90.00  90.00  90.00 P 1           1\n"
                     + "\n".join(lines) + "\nEND\n")
    p, o3 = [f'pdb="{lines[i][12:27]}"' for i in (0, 3)]
    geo = root / "final.geo"
    # Phenix prints the inverse image when O3' is the first label.
    geo.write_text("Bond | covalent geometry | restraints: 0\n\n"
                   "Nonbonded | unspecified | interactions: 1\nSorted by model distance:\n"
                   f"nonbonded {o3}\n          {p}\n   model vdw sym.op.\n   3.000 3.400 x+1,y,z\n")
    return model, geo


def run(model, capsys, *extra, image="x-1,y,z"):
    code = main(["cif-doctor", "phosphate-image", str(model), "--phosphate", "B:1", "--o3", "A:7",
                 "--o3-image=" + image, "--json", *map(str, extra)])
    out = capsys.readouterr()
    assert code == 0, out.err
    return json.loads(out.out)


def nearest(model, capsys, *extra):
    args = ["cif-doctor", "phosphate-image", str(model), "--phosphate", "B:1", "--o3", "A:7",
            "--nearest-image", "--json", *map(str, extra)]
    code = main(args)
    output = capsys.readouterr()
    assert code == 0, output.err
    return json.loads(output.out)


def test_nearest_and_runner_up_belong_to_these_named_atoms(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    explicit = run(model, capsys, "--geometry", geo)
    ranked = nearest(model, capsys, "--geometry", geo)
    ranking = ranked.pop("image_ranking")
    assert ranked == explicit
    assert ranking["status"] == "SEPARATED"
    assert [(c["image"]["operator_xyz"], c["distance_A"]) for c in ranking["closest_two"]] == [
        ("x-1,y,z", pytest.approx(3)), ("x,y,z", pytest.approx(17))]
    assert ranking["separation_A"] == pytest.approx(14)


@pytest.mark.parametrize("test_case", ["exact tie", "coordinate rounding", "special position"])
def test_tied_operators_keep_the_decision_open(tmp_path, capsys, test_case):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    text = model.read_text()
    if test_case == "special position":
        text = text.replace("90.00 P 1", "90.00 P 2").replace("  19.000   2.000   2.000", "   0.000   2.000   0.000")
        candidates = {"-x,y,-z", "x,y,z"}
    else:
        target = 12 if test_case == "exact tie" else 11.999
        text = text.replace("  19.000   2.000   2.000", f"{target:8.3f}   2.000   2.000")
        candidates = {"x-1,y,z", "x,y,z"}
    model.write_text(text)
    report = nearest(model, capsys, "--geometry", geo)
    ranking = report["image_ranking"]
    assert ranking["status"] == "AMBIGUOUS_AT_PDB_PRECISION"
    assert {row["image"]["operator_xyz"] for row in ranking["closest_two"]} == candidates
    assert report["o3_image"] is None and report["distance_A"] is None
    assert all(a is None for a in report["coordinate_angles_degrees"].values())
    assert report["printed_geometry"]["status"] == "UNASSESSED"
    assert run(model, capsys, image="x,y,z")["distance_A"] is not None


def test_nearest_in_skew_cell_checks_other_lattice_translations(tmp_path, capsys):
    from itertools import product
    import math
    gemmi = pytest.importorskip("gemmi")
    model, _ = inputs(tmp_path)
    cell = gemmi.UnitCell(20,20,20,90,90,60)
    xyz = cell.orthogonalize(gemmi.Fractional(3.44,-1.51,0))
    written = tuple(round(v,3) for v in xyz)
    text = model.read_text().replace("90.00  90.00  90.00", "90.00  90.00  60.00")
    text = text.replace("   2.000   2.000   2.000", "   0.000   0.000   0.000")
    text = text.replace("  19.000   2.000   2.000", "".join(f"{v:8.3f}" for v in written))
    model.write_text(text)
    brute = []
    for shift in product(range(-6,7),range(-5,6),range(-2,3)):
        offset = cell.orthogonalize(gemmi.Fractional(*shift))
        brute.append((math.hypot(*(a+b for a,b in zip(written,offset))),list(shift)))
    winners = sorted(brute)[:2]
    assert winners[0][1] != [-3,2,0]
    ranking = nearest(model, capsys)["image_ranking"]
    for row, (distance, shift) in zip(ranking["closest_two"], winners, strict=True):
        assert row["distance_A"] == pytest.approx(distance)
        assert row["image"]["lattice_translation"] == shift


def test_nearest_unoccupied_endpoint_and_resource_limit_are_explicit(tmp_path, capsys):
    pytest.importorskip("gemmi")
    from nasolve.cif_phosphate_image import inspect_phosphate_image
    from nasolve.topostitch_images import closest_atom_images
    from nasolve.topostitch_periodic import _crystal
    model, _ = inputs(tmp_path)
    rows = model.read_text().splitlines(keepends=True)
    i = next(i for i, line in enumerate(rows) if line[12:16].strip() == "O3'")
    rows[i] = rows[i][:54] + "  0.00" + rows[i][60:]
    model.write_text("".join(rows))
    with pytest.raises(ValueError,match="occupied"):
        inspect_phosphate_image(model, phosphate="B:1", o3="A:7", nearest_image=True)
    gemmi, cell, group = _crystal((20,20,20,90,90,90),"P 1")
    with pytest.raises(ValueError,match="budget"):
        closest_atom_images((0,0,0),(1,2,3),cell,group,gemmi,max_image_tests=5)


def test_plain_ambiguous_report_names_both_copies(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    model.write_text(model.read_text().replace("  19.000   2.000   2.000", "  12.000   2.000   2.000"))
    assert main(["cif-doctor", "phosphate-image", str(model), "--phosphate", "B:1", "--o3", "A:7",
                 "--nearest-image", "--geometry", str(geo)]) == 0
    output = capsys.readouterr().out
    assert "x-1,y,z" in output and "x,y,z" in output and "--o3-image" in output


def test_checkpoint_follows_its_own_model_and_geometry_after_relocation(tmp_path, capsys, monkeypatch):
    pytest.importorskip("gemmi")
    from nasolve.model_assessment import file_sha256
    from .test_checkpoints import make_checkpoint_run
    from .test_cif_doctor_run import _child, _reference, _snapshot

    original = tmp_path / "original"
    directory = make_checkpoint_run(original)
    model, geometry = inputs(tmp_path)
    parent = directory / "PostMR/Model/readyset_model.pdb"
    parent.write_bytes(model.read_bytes())
    report_path = directory / "report.json"
    report = json.loads(report_path.read_bytes())
    report["postmr"]["prepared_sha256"] = file_sha256(parent)
    report_path.write_text(json.dumps(report))
    _child(directory)
    regpath = directory / "AutoRefine/checkpoints.json"
    registry = json.loads(regpath.read_bytes())
    registry["current"] = "postmr"
    child = registry["checkpoints"][-1]
    geo = (directory / child["model"]["relative_path"]).with_suffix(".geo")
    geo.write_bytes(geometry.read_bytes())
    child.update(kind="refinement", outputs={"final_geometry": _reference(geo, directory)})
    regpath.write_text(json.dumps(registry))
    moved = tmp_path / "relocated"
    original.rename(moved)
    actual = moved / directory.relative_to(original)
    def unexpected_assessment(*args, **kwargs):
        pytest.fail("A geometric observation started an unrelated dictionary assessment")
    monkeypatch.setattr("nasolve.cif_doctor_run.assess_dictionaries", unexpected_assessment)
    before = _snapshot(moved)
    selected = run(actual, capsys, "--checkpoint", "first-refinement")
    assert selected["checkpoint"]["id"] == "refine-001"
    assert selected["model_sha256"] == child["model"]["sha256"]
    assert selected["checkpoint"]["geometry"]["relative_path"] == child["outputs"]["final_geometry"]["relative_path"]
    assert selected["printed_geometry"]["geometry_sha256"] == file_sha256(geometry)
    assert len(selected["printed_geometry"]["nonbonded"]["matches"]) == 1
    ranked = nearest(actual, capsys, "--checkpoint", "first-refinement")
    assert ranked["image_ranking"]["status"] == "SEPARATED"
    assert ranked["checkpoint"] == selected["checkpoint"] and ranked["printed_geometry"] == selected["printed_geometry"]
    root = run(actual, capsys, "--checkpoint", "postmr")
    assert root["model_sha256"] == file_sha256(model)
    assert root["checkpoint"]["geometry"] is None and root["printed_geometry"] is None
    assert _snapshot(moved) == before
    args = ["cif-doctor", "phosphate-image", str(actual), "--checkpoint", "first-refinement",
            "--phosphate", "B:1", "--o3", "A:7", "--o3-image=x-1,y,z"]
    assert main([*args, "--geometry", str(geometry)]) == 1
    assert "recorded" in capsys.readouterr().err
    empty = [*args]
    empty[empty.index("first-refinement")] = ""
    assert main(empty) == 1
    assert "explicit checkpoint" in capsys.readouterr().err
    dest = actual / geo.relative_to(directory)
    (actual / dest.name).write_bytes(dest.read_bytes())
    dest.write_bytes(dest.read_bytes() + b"\n")
    assert main(args) == 1
    assert "changed after it was frozen" in capsys.readouterr().err


def test_read_only_actual_image_and_reversed_printed_terms(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (model, geo)}
    report = run(model, capsys, "--geometry", geo)
    assert report["distance_A"] == pytest.approx(3)
    assert report["o3_image"] == "x-1,y,z"
    assert report["phosphate_atoms"]["OP2"] is None and report["phosphate_atoms"]["OP3"] is None
    angles = report["coordinate_angles_degrees"]
    assert angles["O3'-P-OP1"] == pytest.approx(90)
    assert angles["C3'-O3'-P"] == pytest.approx(90) and angles["O3'-P-OP2"] is None
    printed = report["printed_geometry"]
    assert printed["bonds"]["matches"] == []
    contact, = printed["nonbonded"]["matches"]
    assert contact["image_of_second_atom"] == "x+1,y,z"
    assert contact["model_A"] == 3 and contact["vdw_A"] == 3.4
    assert abs(contact["printed_minus_coordinate_A"]) < 1e-10
    assert report["scientific_approval"] == "NOT_ASSESSED"
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()} == before
    # The same group operation in a different unit cell is a different contact.
    direct = run(model, capsys, "--geometry", geo, image="x,y,z")
    assert direct["distance_A"] == pytest.approx(17)
    assert direct["printed_geometry"]["nonbonded"]["matches"] == []


def test_unprinted_or_truncated_table_cannot_establish_absence(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    assert run(model, capsys)["printed_geometry"] is None
    geo.write_text(geo.read_text().replace("restraints: 0", "restraints: 1"))
    tables = run(model, capsys, "--geometry", geo)["printed_geometry"]
    assert tables["bonds"]["status"] == "UNASSESSED" and tables["bonds"]["matches"] is None
    assert tables["nonbonded"]["status"] == "OBSERVED"
    geo.write_text("Geometry restraints\n")
    tables = run(model, capsys, "--geometry", geo)["printed_geometry"]
    assert all(tables[k]["status"] == "NOT_RECORDED" and tables[k]["matches"] is None
               for k in ("bonds", "nonbonded"))


def test_matching_printed_bond_keeps_origin_and_chemical_target(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    labels = [f'pdb="{line[12:27]}"' for line in model.read_text().splitlines() if line.startswith("ATOM")]
    geo.write_text("Bond | User supplied | restraints: 1\nSorted by residual:\n"
                   f"bond {labels[0]}\n     {labels[3]}\n"
                   "  ideal model delta sigma weight residual sym.op.\n"
                   "  1.607 3.001 -1.394 2.00e-02 2.50e+03 4.86e+03 x-1,y,z\n"
                   "Nonbonded | unspecified | interactions: 0\n")
    printed = run(model, capsys, "--geometry", geo)["printed_geometry"]
    bond, = printed["bonds"]["matches"]
    assert (bond["origin"], bond["ideal_A"], bond["sigma_A"]) == ("User supplied", 1.607, .02)
    assert bond["printed_minus_coordinate_A"] == pytest.approx(.001)
    assert printed["nonbonded"]["matches"] == []


def test_zero_occupancy_and_missing_oxygen_are_visible(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, _ = inputs(tmp_path)
    source = model.read_text().splitlines(keepends=True)
    op1 = next(i for i, line in enumerate(source) if line[12:16].strip() == "OP1")
    source[op1] = source[op1][:54] + "  0.00" + source[op1][60:]
    model.write_text("".join(source))
    report = run(model, capsys)
    assert report["phosphate_atoms"]["OP1"] == {"element": "O", "occupancy": 0}
    assert report["coordinate_angles_degrees"]["O3'-P-OP1"] is None
    assert report["phosphate_atoms"]["OP2"] is None


def test_unknown_crystal_operator_is_rejected(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, _ = inputs(tmp_path)
    code = main(["cif-doctor", "phosphate-image", str(model), "--phosphate", "B:1", "--o3", "A:7",
                 "--o3-image=-x,-y,z"])
    assert code == 1 and "space group" in capsys.readouterr().err


def printed_angle(model, geo, value, *, operations=("", "", ""), reverse=False):
    lines = [line for line in model.read_text().splitlines() if line.startswith("ATOM")]
    op1 = lines[1]
    model.write_text(model.read_text().replace(op1, op1[:30] + f"{3.:8.3f}" + op1[38:]))
    labels = [(f'pdb="{lines[i][12:27]}"' + ("  " + op if op else "")) for i, op in zip((3, 0, 1), operations)]
    if reverse:
        labels.reverse()
    with geo.open("a") as out:
        out.write("Bond angle | User supplied | restraints: 1\nSorted by residual:\n"
                  + "angle " + "\n      ".join(labels) + "\n"
                  + "  ideal model delta sigma weight residual\n"
                  + f"  108.00 {value} 0.00 3.00e+00 1.11e-01 0.00e+00\n")


@pytest.mark.parametrize("value,ops,reverse,agreement,image", [
    ("45.00", ("", "", ""), False, "ASYMMETRIC_UNIT", "NOT_PRINTED"),
    ("135.00", ("x-1,y,z", "", ""), True, "CRYSTAL_MATE", "REQUESTED_IMAGE"),
    ("135.04", ("", "x+1,y,z", "x+1,y,z"), True, "CRYSTAL_MATE", "REQUESTED_IMAGE"),
    ("45.00", ("x+1,y,z", "", ""), False, "ASYMMETRIC_UNIT", "OTHER_IMAGE"),
    ("90.00", ("", "", ""), False, "NEITHER", "NOT_PRINTED"),
])
def test_printed_angle_compares_physical_mate_and_asymmetric_unit(tmp_path, capsys, value, ops, reverse, agreement, image):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    printed_angle(model, geo, value, operations=ops, reverse=reverse)
    table = run(model, capsys, "--geometry", geo)["printed_geometry"]["angles"]
    assert table["status"] == "OBSERVED" and table["sections"] == {"User supplied": 1}
    row, = table["matches"]
    assert (row["angle"], row["coordinate_agreement"], row["image_relation"]) == ("O3'-P-OP1", agreement, image)
    assert row["origin"] == "User supplied" and row["model_degrees"] == float(value)
    assert row["asymmetric_unit_degrees"] == pytest.approx(45) and row["crystal_mate_degrees"] == pytest.approx(135)


def test_printed_angle_degenerate_evidence_is_explicit(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    assert run(model, capsys, "--geometry", geo)["printed_geometry"]["angles"]["status"] == "NOT_RECORDED"
    printed_angle(model, geo, "90.00")
    model.write_text(model.read_text().replace("   3.000   3.000   2.000", "   2.000   3.000   2.000"))
    result = run(model, capsys, "--geometry", geo)["printed_geometry"]["angles"]
    assert result["matches"][0]["coordinate_agreement"] == "BOTH"
    lines = model.read_text().splitlines(keepends=True)
    oi = next(i for i,line in enumerate(lines) if line[12:16].strip() == "OP1")
    lines[oi] = lines[oi][:54] + "  0.00" + lines[oi][60:]
    model.write_text("".join(lines))
    row, = run(model, capsys, "--geometry", geo)["printed_geometry"]["angles"]["matches"]
    assert row["coordinate_agreement"] == "UNAVAILABLE" and row["crystal_mate_degrees"] is None
    geo.write_text(geo.read_text().replace("User supplied | restraints: 1", "User supplied | restraints: 2"))
    table = run(model, capsys, "--geometry", geo)["printed_geometry"]["angles"]
    assert table["status"] == "UNASSESSED" and table["matches"] is None


def test_plain_report_explains_the_printed_coordinate_frame(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    printed_angle(model, geo, "45.00")
    code = main(["cif-doctor", "phosphate-image", str(model), "--phosphate", "B:1", "--o3", "A:7",
                 "--o3-image=x-1,y,z", "--geometry", str(geo)])
    out = capsys.readouterr()
    assert code == 0 and "45.00°" in out.out and "matches the asymmetric unit alone" in out.out


def test_angle_operations_keep_translation_on_a_threefold_mate(tmp_path, capsys):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    model.write_text(model.read_text().replace("90.00  90.00  90.00 P 1", "90.00  90.00 120.00 P 3"))
    printed_angle(model, geo, "45.00", operations=("-y+1,x-y,z", "x+1,y,z", "x+1,y,z"))
    rows = run(model, capsys, "--geometry", geo, image="-y,x-y,z")["printed_geometry"]["angles"]
    assert rows["matches"][0]["image_relation"] == "REQUESTED_IMAGE"
    geo.write_text(geo.read_text().replace("-y+1,x-y,z", "-y,x-y+1,z"))
    rows = run(model, capsys, "--geometry", geo, image="-y,x-y,z")["printed_geometry"]["angles"]
    assert rows["matches"][0]["image_relation"] == "OTHER_IMAGE"


@pytest.mark.parametrize("change", ["bad precision", "invalid image", "incomplete row"])
def test_unreadable_angle_table_leaves_other_geometry_available(tmp_path, capsys, change):
    pytest.importorskip("gemmi")
    model, geo = inputs(tmp_path)
    printed_angle(model, geo, "135.00", operations=("x-1,y,z", "", ""))
    text = geo.read_text()
    if change == "bad precision":
        text = text.replace("135.00", "135")
    elif change == "invalid image":
        text = text.replace("x-1,y,z", "-x,-y,z")
    else:
        text = text.rsplit("  108.00", 1)[0]
    geo.write_text(text)
    tables = run(model, capsys, "--geometry", geo)["printed_geometry"]
    assert tables["angles"]["status"] == "UNASSESSED" and tables["angles"]["matches"] is None
    assert tables["nonbonded"]["status"] == "OBSERVED" and len(tables["nonbonded"]["matches"]) == 1
