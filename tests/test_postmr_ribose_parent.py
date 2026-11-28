"""A genuine ribose parent keeps the existing base, backbone and its two ports."""
from pathlib import Path
import math

from Bio.PDB.vectors import Vector, calc_angle
import numpy as np
import pytest

from nasolve.cif_stereochemistry_audit import _coordinates, _values
from nasolve.ligand_profiles import _emit
from nasolve.postmr import MutationAction
from nasolve.postmr_canonical_input import canonical_input_plan, prepare_canonical_parent_input, read_canonical_parent_input
from nasolve.postmr_canonical_seed import canonical_parent_seed
from tests.test_postmr_canonical_seed import selected


PUBLIC = Path(__file__).parent / "fixtures/public_ccd"
SOURCE = PUBLIC / "DG.cif"
TEMPLATE = PUBLIC / "G.cif"


def frame(phosphate="internal"):
    values = _values(SOURCE, "DG")
    _, xyz = _coordinates(values, source=True)
    skip = {"OP3"} if phosphate == "internal" else {"P", "OP1", "OP2", "OP3"} if phosphate == "free" else set()
    rows = ["REMARK non-target records stay exact\n"]
    for name, element in zip(values["_chem_comp_atom.atom_id"], values["_chem_comp_atom.type_symbol"]):
        if element == "H" or name in skip:
            continue
        x, y, z = xyz[name]
        # Different crystal frame and a small change in the angle between the two retained C–C bonds.
        point = (8 - y, x + (0.08 if name == "C3'" else 0), z + 17)
        rows.append(f"ATOM  {len(rows):5d} {name:>4s}  DG A   1    " +
                    "".join(f"{v:8.3f}" for v in point) + f"  0.75{17.0 + len(rows):6.2f}          {element:>2s}\n")
    rows.extend(["TER     710       DG A   1\n", "ATOM    800  C1'  DA B   2       1.000   2.000   3.000  1.00 27.00           C\n", "END\n"])
    return "".join(rows).encode("ascii")


def angle(xyz, carbon):
    return math.degrees(calc_angle(*(Vector(xyz[n]) for n in (carbon, "C2'", "O2'"))))


@pytest.mark.parametrize("phosphate", ("internal", "free", "terminal"))
def test_rna_parent_adds_only_the_stereospecific_two_prime_oxygen(phosphate):
    original = frame(phosphate)
    result, proof = canonical_parent_seed(original, "A:1", SOURCE, "DG", TEMPLATE, "G")
    previous, observed = selected(original, "DG"), selected(result, "G")
    assert observed.keys() - previous.keys() == {"O2'"}
    for atom, row in previous.items():
        assert row["line"][:17] == observed[atom]["line"][:17]
        assert row["line"][20:] == observed[atom]["line"][20:]
    assert observed["O2'"]["line"][6:11].strip() == "801"
    assert observed["O2'"]["line"][54:66] == previous["C2'"]["line"][54:66]
    assert b"TER     710        G A   1\n" in result
    assert original.split(b"ATOM    800")[1] == result.split(b"ATOM    800")[1]
    _, ideal = _coordinates(_values(TEMPLATE, "G"), source=True)
    new = {n: a["xyz"] for n, a in observed.items()}
    assert math.dist(new["C2'"], new["O2'"]) == pytest.approx(math.dist(ideal["C2'"], ideal["O2'"]), abs=.001)
    for carbon in ("C1'", "C3'"):
        assert angle(new, carbon) == pytest.approx(angle(ideal, carbon), abs=.06)
    def hand(points):
        return np.linalg.det([np.subtract(points[a], points["C2'"]) for a in ("C1'", "C3'", "O2'")])
    assert hand(new) * hand(ideal) > 0
    assert proof["status"] == "CANONICAL_RIBOSE_SEED" and proof["native_qualification"] == "NOT_RUN"


@pytest.mark.parametrize("defect", ("mirror_host", "mirror_oxygen", "unknown_hand", "opposite_marker", "different_base", "partial_phosphate"))
def test_chemically_unproven_sugar_change_is_refused(tmp_path, defect):
    raw = frame()
    source, template = SOURCE, TEMPLATE
    if defect == "mirror_host":
        raw = b"".join(row[:30] + f"{-float(row[30:38]):8.3f}".encode() + row[38:] if row.startswith(b"ATOM") else row
                       for row in raw.splitlines(keepends=True))
    elif defect == "partial_phosphate":
        raw = b"".join(row for row in raw.splitlines(keepends=True) if row[12:16].strip() != b"OP2")
    else:
        values = _values(TEMPLATE, "G")
        idx = values["_chem_comp_atom.atom_id"].index
        if defect == "mirror_oxygen":
            _, ideal = _coordinates(values, source=True)
            center = np.array(ideal["C2'"])
            normal = np.cross(ideal["C1'"] - center, ideal["C3'"] - center)
            normal /= np.linalg.norm(normal)
            vec = ideal["O2'"] - center
            reflected = center + vec - 2 * np.dot(vec, normal) * normal
            for axis, val in zip("xyz", reflected):
                values[f"_chem_comp_atom.pdbx_model_cartn_{axis}_ideal"][idx("O2'")] = str(val)
        elif defect in {"unknown_hand", "opposite_marker"}:
            values["_chem_comp_atom.pdbx_stereo_config"][idx("C2'")] = "?" if defect == "unknown_hand" else "S"
        else:
            values["_chem_comp_atom.charge"][idx("N7")] = "1"
        template = tmp_path / "changed.cif"
        template.write_text(_emit(values))
    with pytest.raises(ValueError):
        canonical_parent_seed(raw, "A:1", source, "DG", template, "G")


def test_saved_rna_parent_replays_without_its_original_sources(tmp_path):
    import shutil
    incoming = tmp_path / "original"
    incoming.mkdir()
    model, s, t = (incoming / name for name in ("input.pdb", "DG.cif", "G.cif"))
    model.write_bytes(frame())
    shutil.copyfile(SOURCE, s)
    shutil.copyfile(TEMPLATE, t)
    action = MutationAction("A:1", "DG", "2MG", "coot-parent-overlap", parent_code="G")
    choices = canonical_input_plan((action,), {"A:1": (s, t)})
    record = prepare_canonical_parent_input(model, choices, tmp_path / "first")
    expected = record["model"].read_bytes()
    shutil.rmtree(incoming)
    (tmp_path / "first").rename(tmp_path / "moved")
    cold = read_canonical_parent_input(tmp_path / "moved")
    assert cold["model"].read_bytes() == expected
    assert cold["receipt"]["steps"][0]["proof"]["status"] == "CANONICAL_RIBOSE_SEED"
