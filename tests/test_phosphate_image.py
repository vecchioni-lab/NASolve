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
