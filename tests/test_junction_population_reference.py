"""Independent population bands at an explicitly named real or crystal junction."""
import json

import pytest

from nasolve.cli import main
from .test_phosphate_duplex import FRAMES, four_sites


pytest.importorskip("gemmi")


def inspect(model, capsys, *extra, image="x,y,z"):
    args = ["cif-doctor", "phosphate-image", str(model), "--phosphate", "A:12", "--o3", "A:11",
            "--na-val-2026", "--json", *extra]
    args.append("--nearest-image" if image is None else "--o3-image=" + image)
    code = main(args)
    report = json.loads(capsys.readouterr().out)
    return code, report


def test_published_observation_names_roles_and_bounds_in_a_complete_ring_pair(capsys):
    model = FRAMES / "C_G.pdb"
    code, report = inspect(model, capsys)
    population = report["na_val_2026"]
    assert code == 0 and population["status"] == "MEASURED" and population["family"] == "DNA"
    assert population["model_sha256"] == report["model_sha256"]
    assert population["source"] == "https://doi.org/10.5281/zenodo.17286401"
    assert population["source_archive_sha256"] == "97cf25c310ae7617e1b948858e64912e80662d7f24ef1842e051ab04bf47b8a2"
    terms = {(r["group"], r["feature"]): r for r in population["terms"]}
    bond = terms["link", "O3pr2-P"]
    assert bond["interval"] == [1.53873, 1.63970]
    assert bond["observed"] == pytest.approx(report["distance_A"], abs=1e-8)
    assert terms["link", "OP1-P-O3pr2"]["observed"] == pytest.approx(report["coordinate_angles_degrees"]["O3'-P-OP1"])
    assert terms["donor", "C2p-C3p-O3p"]["interval"] == [101.16669, 120.02181]
    assert ("donor", "OP1-P") not in terms and ("acceptor", "C2p-C3p-O3p") not in terms


def test_complete_cell_translation_preserves_all_local_and_cross_image_values(tmp_path, capsys):
    model = tmp_path / "moved.pdb"
    four_sites(model)
    _, baseline = inspect(model, capsys)
    from nasolve.topostitch_periodic import crystal_from_pdb_bytes
    gemmi, cell, _ = crystal_from_pdb_bytes(model.read_bytes())
    offset = cell.orthogonalize(gemmi.Fractional(0, 0, 1))
    def move(site, name, line):
        if site != ("A", 11):
            return line
        xyz = [float(line[i:i+8]) + delta for i, delta in zip((30, 38, 46), tuple(offset))]
        return line[:30] + "".join(f"{v:8.3f}" for v in xyz) + line[54:]
    four_sites(model, move)
    _, moved = inspect(model, capsys, image="x,y,z-1")
    expected = baseline["na_val_2026"]["terms"]
    observed = moved["na_val_2026"]["terms"]
    assert [(r["group"], r["feature"]) for r in expected] == [(r["group"], r["feature"]) for r in observed]
    for a, b in zip(expected, observed, strict=True):
        assert abs(a["observed"] - b["observed"]) < (0.002 if a["unit"] == "Å" else 0.12)


@pytest.mark.parametrize("problem", ["nearest", "terminal alias", "sulfur", "modified"])
def test_reference_is_withheld_when_the_bond_or_chemical_family_is_unqualified(tmp_path, capsys, problem):
    model = tmp_path / "variant.pdb"
    def change(site, name, line):
        if site == ("A", 12):
            if problem == "modified":
                return line[:17] + "PDU" + line[20:]
            if problem == "sulfur" and name == "OP1":
                return line[:76] + " S" + line[78:]
            if problem == "terminal alias" and name == "OP1":
                return line + "\n" + line[:12] + " O3P" + line[16:]
        return line
    four_sites(model, change)
    code, report = inspect(model, capsys, image=None if problem == "nearest" else "x,y,z")
    assert code == 2 and report["na_val_2026"]["status"] == "UNASSESSED"
    assert not report["na_val_2026"]["terms"]


def test_mirrored_sugar_and_missing_base_coordinates_have_different_coverage(tmp_path, capsys):
    model = tmp_path / "variant.pdb"

    def reflect(site, name, line):
        if site == ("A", 12):
            return line[:30] + f"{-float(line[30:38]):8.3f}" + line[38:]
        return line

    four_sites(model, reflect)
    code, report = inspect(model, capsys)
    assert code == 2 and "sugar hand" in report["na_val_2026"]["reason"]
    four_sites(model, lambda site, name, line: None if site == ("A", 12) and name == "C6" else line)
    code, report = inspect(model, capsys)
    population = report["na_val_2026"]
    assert code == 2 and population["status"] == "PARTIAL"
    assert population["missing_count"] == 1
    unavailable, = [r for r in population["terms"] if r["observed"] is None]
    assert (unavailable["feature"], unavailable["outside"]) == ("C1p-N1-C6", None)


def test_ribose_uses_rna_intervals_and_requires_the_2_prime_hand(tmp_path, capsys):
    import numpy as np

    model = tmp_path / "rna.pdb"
    four_sites(model)
    lines = model.read_text().splitlines()
    positions = {(l[21:26], l[12:16].strip()): np.array([float(l[i:i+8]) for i in (30, 38, 46)])
                 for l in lines if l.startswith("ATOM")}

    def ribose(site, name, line):
        if site not in {("A", 11), ("A", 12)}:
            return line
        if name == "C7":
            return None
        code = "U" if site[1] == 11 else "C"
        line = line[:17] + f"{code:>3}" + line[20:]
        if name != "C2'":
            return line
        key = line[21:26]
        center = positions[key, "C2'"]
        axis = np.cross(positions[key, "C3'"]-center, positions[key, "C1'"]-center)
        oxygen = center + 1.43 * axis / np.linalg.norm(axis)
        coords = "".join(f"{v:8.3f}" for v in oxygen)
        return line + "\n" + line[:12] + " O2'" + line[16:30] + coords + line[54:76] + " O" + line[78:]

    four_sites(model, ribose)
    code, report = inspect(model, capsys)
    result = report["na_val_2026"]
    assert code == 0 and result["family"] == "RNA" and result["measured_count"] == 59
    assert next(r["interval"] for r in result["terms"] if r["feature"] == "O3pr2-P") == [1.53387, 1.64676]
    model.write_text("\n".join(l for l in model.read_text().splitlines() if l[12:16].strip() != "O2'") + "\n")
    code, report = inspect(model, capsys)
    assert code == 2 and "C2'" in report["na_val_2026"]["reason"]


def test_frozen_checkpoint_after_relocation_uses_its_own_coordinates(tmp_path, capsys):
    from nasolve.model_assessment import file_sha256
    from .test_checkpoints import make_checkpoint_run
    from .test_cif_doctor_run import _snapshot

    before = tmp_path / "original"
    run = make_checkpoint_run(before)
    parent = run / "PostMR/Model/readyset_model.pdb"
    four_sites(parent)
    report_file = run / "report.json"
    record = json.loads(report_file.read_bytes())
    record["postmr"]["prepared_sha256"] = file_sha256(parent)
    report_file.write_text(json.dumps(record))
    moved = before.rename(tmp_path / "moved")
    relocated = moved / run.relative_to(before)
    snapshot = _snapshot(moved)
    code, result = inspect(relocated, capsys, "--checkpoint", "postmr")
    assert code == 0 and result["na_val_2026"]["model_sha256"] == record["postmr"]["prepared_sha256"]
    assert result["checkpoint"]["id"] == "postmr" and _snapshot(moved) == snapshot


def test_same_copy_cannot_supply_both_ends_and_a_saved_read_cannot_change_models(tmp_path):
    from nasolve.cif_phosphate_image import inspect_phosphate_image
    from nasolve.junction_population_reference import inspect_junction_reference

    model = tmp_path / "pair.pdb"
    four_sites(model)
    args = dict(phosphate="A:12", o3="A:12", o3_image="x,y,z")
    old = inspect_phosphate_image(model, **args)
    assert "na_val_2026" not in old
    assert "same residue copy" in inspect_junction_reference(model, old)["reason"]
    model.write_bytes(model.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="differ from the inspected"):
        inspect_junction_reference(model, old)
