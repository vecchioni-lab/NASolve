"""The direction of a phosphate is measured in its explicitly assigned duplex step."""
import json
from pathlib import Path

import pytest

from nasolve.cli import main


FRAMES = Path(__file__).resolve().parents[1] / "MR_frames" / "5W6W"


def measure(model, capsys, *, donor_image="x,y,z", extra=()):
    pytest.importorskip("gemmi")
    code = main(["cif-doctor", "phosphate-image", str(model), "--phosphate", "A:12",
                 "--o3", "A:11", "--o3-image=" + donor_image, "--duplex-partners", "B:5", "B:4",
                 "--json", *extra])
    output = capsys.readouterr()
    assert code == 0, output.err
    return json.loads(output.out)["duplex_direction"]


@pytest.mark.parametrize("name", ["A_T", "C_C", "C_G", "G_C", "T_A", "T_T", "5W6W_noPO4"])
def test_catalogue_and_older_control_have_opposite_a12_poses(name, capsys):
    model = FRAMES / (name + ".pdb")
    before = model.stat().st_mtime_ns, model.read_bytes()
    result = measure(model, capsys)
    assert result["status"] == "MEASURED"
    ring, sugar = [result[key]["midpoint_A"] for key in ("ring_centres", "c1_midpoints")]
    if name == "5W6W_noPO4":
        assert -.66 < ring < -.63 and -.66 < sugar < -.62
        assert all(result["ring_centres"][key] < 0 for key in ("OP1_A", "OP2_A"))
    else:
        assert .55 < ring < .60 and .56 < sugar < .62
    assert result["ring_centres"]["midpoint_A"] == pytest.approx(
        (result["ring_centres"]["OP1_A"] + result["ring_centres"]["OP2_A"]) / 2)
    assert [p["anchor"]["site"] for p in result["pairs"]] == ["A:11", "A:12"]
    assert [p["partner"]["site"] for p in result["pairs"]] == ["B:5", "B:4"]
    assert (model.stat().st_mtime_ns, model.read_bytes()) == before


def four_sites(model, transform=lambda site, name, line: line):
    sites = {("A", 11), ("A", 12), ("B", 4), ("B", 5)}
    records = ["CRYST1  100.000  100.000  100.000  90.00  90.00  90.00 P 1           1"]
    for line in (FRAMES / "C_G.pdb").read_text().splitlines():
        if line[:6] not in ("ATOM  ", "HETATM"):
            continue
        site = line[21], int(line[22:26])
        if site in sites:
            output = transform(site, line[12:16].strip(), line)
            if output is not None:
                records.append(output)
    model.write_text("\n".join([*records, "END", ""]))


def test_unequally_translated_pair_images_recover_the_same_step(tmp_path, capsys):
    model = tmp_path / "four.pdb"
    four_sites(model)
    ordinary = measure(model, capsys)
    offsets = {("A", 11): (100, 0, 0), ("B", 5): (0, 100, 0), ("B", 4): (-100, 0, 0)}

    def shift(site, name, line):
        xyz = [float(line[i:i+8]) for i in (30, 38, 46)]
        moved = [v + d for v, d in zip(xyz, offsets.get(site, (0, 0, 0)), strict=True)]
        return line[:30] + "".join(f"{v:8.3f}" for v in moved) + line[54:]

    four_sites(model, shift)
    translated = measure(model, capsys, donor_image="x-1,y,z",
                         extra=("--partner-images", "x+1,y-1,z", "x+1,y,z"))
    assert translated["pairs"][0]["partner"]["image"] == "x,y-1,z"
    for metric in ("ring_centres", "c1_midpoints"):
        assert translated[metric] == pytest.approx(ordinary[metric], abs=1e-10)


@pytest.mark.parametrize("change,reason", [
    ("sulfur", "OP1"), ("missing purine atom", "N7"), ("empty sugar", "C1'"),
    ("third oxygen", "OP3"), ("collapsed ring", "plane"),
])
def test_unqualified_chemistry_keeps_the_directions_unassessed(tmp_path, capsys, change, reason):
    def alter(site, name, line):
        if change == "sulfur" and site == ("A", 12) and name == "OP1":
            return line[:76] + " S" + line[78:]
        if change == "missing purine atom" and site == ("B", 4) and name == "N7":
            return None
        if change == "empty sugar" and site == ("A", 11) and name == "C1'":
            return line[:54] + "  0.00" + line[60:]
        if change == "third oxygen" and site == ("A", 12) and name == "OP1":
            return line + "\n" + line[:12] + " OP3" + line[16:]
        if change == "collapsed ring" and site == ("A", 12) and name in ("N1", "C2", "N3", "C4", "C5", "C6"):
            return line[:30] + "   1.000" * 3 + line[54:]
        return line

    model = tmp_path / "changed.pdb"
    four_sites(model, alter)
    result = measure(model, capsys)
    assert result["status"] == "UNASSESSED" and reason in result["reason"]
    assert "ring_centres" not in result


def test_swapping_op_names_leaves_group_direction_unchanged(tmp_path, capsys):
    model = tmp_path / "swapped.pdb"
    four_sites(model)
    original = measure(model, capsys)

    def swap(site, name, line):
        if site == ("A", 12) and name in ("OP1", "OP2"):
            return line[:12] + (" OP2" if name == "OP1" else " OP1") + line[16:]
        return line

    four_sites(model, swap)
    swapped = measure(model, capsys)
    for key in ("ring_centres", "c1_midpoints"):
        assert original[key]["midpoint_A"] == pytest.approx(swapped[key]["midpoint_A"])
        assert original[key]["OP1_A"] == pytest.approx(swapped[key]["OP2_A"])


def test_invalid_assignment_and_reused_model_reading_are_refused(tmp_path, capsys):
    pytest.importorskip("gemmi")
    from nasolve.cif_phosphate_duplex import inspect_duplex_direction
    from nasolve.cif_phosphate_image import inspect_phosphate_image

    model = tmp_path / "step.pdb"
    four_sites(model)
    args = ["cif-doctor", "phosphate-image", str(model), "--phosphate", "A:12", "--o3", "A:11",
            "--o3-image=x,y,z"]
    assert main(args + ["--partner-images", "x,y,z", "x,y,z"]) == 1
    assert "requires --duplex-partners" in capsys.readouterr().err
    assert main(args + ["--duplex-partners", "A:12", "B:4"]) == 1
    assert "four distinct" in capsys.readouterr().err
    assert main(args + ["--duplex-partners", "B:5", "B:4", "--partner-images", "y,x,z", "x,y,z"]) == 1
    assert "space group" in capsys.readouterr().err
    result = inspect_phosphate_image(model, phosphate="A:12", o3="A:11", o3_image="x,y,z")
    assert "duplex_direction" not in result
    model.write_bytes(model.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="differ from the inspected"):
        inspect_duplex_direction(model, result, ["B:5", "B:4"])
