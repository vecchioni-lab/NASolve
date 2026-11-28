"""Read a furanose pseudorotation only when the written native ring is complete."""
import json
import math

import pytest

from nasolve.cli import main
from nasolve.model_assessment import file_sha256
from nasolve.topostitch_contacts import _angle
from .test_checkpoints import make_checkpoint_run
from .test_cif_doctor_run import _child, _reference, _snapshot

pytest.importorskip("gemmi")

# Deposited 1BNA A:4 coordinates from the worked Altona–Sundaralingam example at
# https://x3dna.org/articles/conformation-of-the-sugar-ring-in-nucleic-acid-structures
RING = {
    "C4'": (21.393, 16.960, 18.505), "O4'": (20.353, 17.952, 18.496),
    "C1'": (19.716, 17.901, 17.218), "C2'": (20.793, 17.368, 16.288),
    "C3'": (21.264, 16.229, 17.176),
}


def write_inputs(folder, positions, *, ring_bonds=5, occupancy=1.0, oxygen="O"):
    folder.mkdir()
    model, geometry = folder / "model.pdb", folder / "model_final.geo"
    labels, atoms = [], []
    for i, (name, (x, y, z)) in enumerate(positions.items(), 1):
        is_oxygen = name.replace("*", "'") == "O4'"
        element = oxygen if is_oxygen else "C"
        occ = occupancy if is_oxygen else 1.0
        atom = (f"HETATM{i:5d} {name:>4}  Z9 A   4    {x:8.3f}{y:8.3f}{z:8.3f}"
                f"{occ:6.2f}{20:6.2f}          {element:>2}")
        atoms.append(atom)
        labels.append(f'pdb="{atom[12:27]}"')
    model.write_text("\n".join(atoms + ["END", ""]))
    points = list(positions.values())
    lines = [f"Bond | covalent geometry | restraints: {ring_bonds}", "Sorted by residual:"]
    for i in range(ring_bonds):
        j = (i + 1) % 5
        distance = math.dist(points[i], points[j])
        lines.extend([f"bond {labels[i]}", f"     {labels[j]}", " ideal model delta sigma weight residual",
                      f" {distance:.3f} {distance:.3f} 0.000 2.00e-02 2.50e+03 0.000"])
    angle = _angle(points[:3])
    lines.extend(["Bond angle | covalent geometry | restraints: 1", f"angle {labels[0]}",
                  f"      {labels[1]}", f"      {labels[2]}", " ideal model delta sigma weight residual",
                  f" {angle:.2f} {angle:.2f} 0.00 1.00e+00 1.00e+00 0.00"])
    geometry.write_text("\n".join(lines) + "\n")
    return model, geometry


def read(files, capsys, *extra):
    model, geo = files
    args = ["cif-doctor", "residue-geometry", str(model), "--geometry", str(geo), "--site", "A:4",
            "--sugar-pucker", "--json", *extra]
    code = main(args)
    return code, json.loads(capsys.readouterr().out)


def test_native_named_ring_matches_the_published_example_and_its_mirror(tmp_path, capsys):
    first = write_inputs(tmp_path / "first", RING)
    code, report = read(first, capsys)
    row = report["sugar_puckers"]["sites"][0]
    assert code == 0 and (row["site"], row["component"], row["status"]) == ("A:4", "Z9", "MEASURED")
    assert row["torsions_deg"] == pytest.approx([-26.7, 46.3, -47.1, 33.4, -4.4], abs=0.06)
    assert row["phase_deg"] == pytest.approx(166.35, abs=0.08)
    assert row["amplitude_deg"] == pytest.approx(48.469, abs=0.08)
    reflected = write_inputs(tmp_path / "mirror", {a: (-x, y, z) for a, (x, y, z) in RING.items()})
    code, report = read(reflected, capsys, "--reference-pdb", str(first[0]), "--reference-geometry", str(first[1]))
    earlier = report["reference"]["sugar_puckers"]["sites"][0]
    later = report["current"]["sugar_puckers"]["sites"][0]
    assert code == 0 and earlier["phase_deg"] == row["phase_deg"]
    assert later["phase_deg"] == pytest.approx((earlier["phase_deg"] + 180) % 360)
    assert later["amplitude_deg"] == pytest.approx(earlier["amplitude_deg"])


@pytest.mark.parametrize("changes,reason", [
    ({"ring_bonds": 4}, "bond"), ({"occupancy": 0}, "O4'"), ({"oxygen": "S"}, "O4'"),
])
def test_source_must_establish_five_occupied_atoms_and_the_covalent_cycle(tmp_path, capsys, changes, reason):
    files = write_inputs(tmp_path / "incomplete", RING, **changes)
    code, report = read(files, capsys)
    row = report["sugar_puckers"]["sites"][0]
    assert code == 2 and row["status"] == "UNASSESSED"
    assert reason in row["reason"] and row.get("phase_deg") is None


def test_ring_flat_at_written_precision_has_no_assigned_phase(tmp_path, capsys):
    positions = {a: (round(math.cos(i * math.tau / 5), 3), round(math.sin(i * math.tau / 5), 3), 0.)
                 for i, a in enumerate(RING)}
    files = write_inputs(tmp_path / "flat", positions)
    code, report = read(files, capsys)
    row = report["sugar_puckers"]["sites"][0]
    assert code == 2 and row["status"] == "PHASE_UNRESOLVED"
    assert row["phase_deg"] is None and row["amplitude_deg"] == pytest.approx(0.)


def test_older_prime_spelling_must_identify_each_ring_atom_once(tmp_path, capsys):
    files = write_inputs(tmp_path / "older", {a.replace("'", "*"): p for a, p in RING.items()}, oxygen="O")
    pdb, _ = files
    original = pdb.read_text().splitlines()
    code, report = read(files, capsys)
    row = report["sugar_puckers"]["sites"][0]
    assert code == 0 and row["phase_deg"] == pytest.approx(166.35, abs=0.08)
    assert row["written_atom_names"]["C3'"] == "C3*"
    extra = original[0].replace("C4*", "C4'").replace("HETATM    1", "HETATM    6")
    pdb.write_text("\n".join([*original[:-1], extra, "END", ""]))
    code, report = read(files, capsys)
    assert code == 2 and "Multiple" in report["sugar_puckers"]["sites"][0]["reason"]


def test_all_sites_counts_nonfuranose_residues_separately(tmp_path, capsys):
    pdb, geo = write_inputs(tmp_path / "mixed", RING)
    metal = "HETATM   80   AG  AG M  40       9.000  10.000  11.000  1.00 20.00          AG"
    pdb.write_text(pdb.read_text().replace("END\n", metal + "\nEND\n"))
    args = ["cif-doctor", "residue-geometry", str(pdb), "--geometry", str(geo), "--all-sites", "--sugar-pucker"]
    assert main(args + ["--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["sugar_puckers"]["counts"] == {"MEASURED": 1, "NO_NAMED_RING": 1}
    assert main(args) == 0
    phase = report["sugar_puckers"]["sites"][0]["phase_deg"]
    assert f"phase {phase:.1f}°" in capsys.readouterr().out


def test_named_checkpoint_uses_only_its_own_model_and_final_geometry(tmp_path, capsys):
    run = make_checkpoint_run(tmp_path / "dataset")
    model, geo = write_inputs(tmp_path / "native", RING)
    initial = run / "PostMR/Model/readyset_model.pdb"
    initial.write_bytes(model.read_bytes())
    path = run / "report.json"
    report = json.loads(path.read_bytes())
    report["postmr"]["prepared_sha256"] = file_sha256(initial)
    path.write_text(json.dumps(report))
    _child(run)
    path = run / "AutoRefine/checkpoints.json"
    registry = json.loads(path.read_bytes())
    child = registry["checkpoints"][-1]
    final = (run / child["model"]["relative_path"]).with_suffix(".geo")
    final.write_bytes(geo.read_bytes())
    child.update(kind="refinement", outputs={"final_geometry": _reference(final, run)})
    registry["current"] = "postmr"
    path.write_text(json.dumps(registry))
    before = _snapshot(run)
    args = ["cif-doctor", "residue-geometry", str(run), "--site", "A:4", "--sugar-pucker", "--json"]
    assert main(args + ["--checkpoint", "first-refinement"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["checkpoint"]["id"] == child["id"]
    assert report["sugar_puckers"]["sites"][0]["phase_deg"] == pytest.approx(166.35, abs=0.08)
    assert main(args + ["--checkpoint", "postmr"]) == 2
    assert json.loads(capsys.readouterr().out)["sugar_puckers"]["sites"][0]["status"] == "UNASSESSED"
    assert _snapshot(run) == before
