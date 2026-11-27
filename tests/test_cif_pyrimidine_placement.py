"""A source-validated C–glycoside can keep the host's pairing face and sugar hand."""
from unittest.mock import patch

import openpyxl
import pytest

from nasolve.cif_construction_provenance import _pdb_inventory
from nasolve.cif_furanose_bridge import prepare_furanose_bridge_seed
from nasolve.cif_stereochemistry_audit import _coordinates, _graph, _values
from nasolve.postmr_restoration import _chi
from nasolve.cif_whole_furanose import prepare_base_anchored_furanose_from_model, read_base_anchored_furanose_control
from tests.test_cif_catalogue import row, snapshot, source, workbook
from tests.test_cif_fana import numerical
from tests.test_cif_model_context import report
from tests.test_cif_stereochemistry_audit import write


def inputs(root, *, wrong_edge=False, mirror=False):
    host = source(root / "ccd", "PDU")
    target = source(root / "ccd", "UY1")
    data = _values(target, "UY1")
    names = data["_chem_comp_atom.atom_id"]
    _, points = _coordinates(data, source=True)
    for index, axis in enumerate("xyz"):
        data["_chem_comp_atom." + axis] = [str(points[n][index]) for n in names]
    candidate = numerical(data)
    for key in candidate:
        if key.endswith(".comp_id"):
            candidate[key] = ["UY1"] * len(candidate[key])
    numbers = write(root / "numerical.cif", candidate)

    book = workbook(root, [("thymine", row("PDU")), ("thymine", row("UY1"))])
    wb = openpyxl.load_workbook(book)
    sheet = wb["thymine"]
    # Two known mappings exercise the library writer even on an older installation.
    for i, (role, ordinary, pseudo) in enumerate([
            ("O2","O2","O2" if wrong_edge else "O4"), ("O4","O4","O4" if wrong_edge else "O2"),
            ("N3","N3","N3"), ("C4","C4","C4"), ("C2","C2","C2"), ("C6","C6","C6"),
            ("Glycosidic atom","N1","C5"), ("Backbone attachment atom","C1'","C1'")], sheet.max_column + 1):
        for r, value in enumerate((role, ordinary, pseudo), 1):
            sheet.cell(r, i, value)
    wb.save(book)
    wb.close()

    values = _values(host, "PDU")
    _, ideal = _coordinates(values, source=True)
    elements = _graph(values)[0]
    # Repeated source phosphate geometry places the next leaving oxygen on the prior O3′.
    shift = [u - v for u,v in zip(ideal["O3'"], ideal["OP3"])]
    lines = []
    for resid in (1, 2, 3):
        for name, point in ideal.items():
            if elements[name] in {"H","D"} or name == "OP3" or (resid == 1 and name in {"P","OP1","OP2"}):
                continue
            x, y, z = (val + resid * delta for val, delta in zip(point, shift))
            z = -z if mirror else z
            lines.append(f"ATOM  {len(lines)+1:5d} {name:>4} PDU A{resid:4d}    "
                         f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 24.00          {elements[name]:>2}\n")
    frame = root / "frame.pdb"
    frame.write_text("".join(lines) + "TER\nEND\n")
    return target, numbers, host, book, frame


def test_canonical_edge_places_a_c_glycoside_and_replays_its_actual_glycosidic_rotation(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    paths = inputs(original)
    args = dict(code="UY1", site="A:2", postmr_report=report())
    with pytest.raises(ValueError, match="different workbook roles"):
        prepare_base_anchored_furanose_from_model(*paths, original / "older", canonical_at_edge=False, **args)
    assert not (original / "older").exists()
    before = snapshot(original)
    result = prepare_base_anchored_furanose_from_model(*paths, original / "edge", canonical_at_edge=True, **args)
    automatic = prepare_base_anchored_furanose_from_model(*paths, original / "automatic", **args)
    assert automatic == result
    explicit_files = snapshot(original / "edge")
    auto_files = snapshot(original / "automatic")
    assert auto_files.keys() == explicit_files.keys()
    assert all(auto_files[path][0] == data for path, (data, _) in explicit_files.items())
    fields = {l[12:16].strip(): l[12:16] for l in (original / "edge" / "model.pdb").read_text().splitlines()
              if l.startswith("HETATM") and l[21:26] == "A   2"}
    assert [fields[n] for n in ("P", "C5", "O2", "O2'", "CM2")] == [" P  ", " C5 ", " O2 ", " O2'", " CM2"]
    assert result["alignment"] == "CANONICAL_URACIL_EDGE"
    assert result["target_frame_atoms"] == ["C5", "N3", "O2"]
    assert result["host_frame_atoms"] == ["N1", "N3", "O4"]
    rotation = result["glycosidic_rotation"]
    assert abs((rotation["after_degrees"] - rotation["host_degrees"] + 180) % 360 - 180) < 1e-6
    assert all(hand["compatible"] for hand in result["host_hand_checks"])
    assert result["native_linkage"] == "NOT_ASSESSED" and not result["automatic_adoption"]
    assert "OP3" not in result["model_heavy_atoms"]
    assert all(snapshot(original)[k] == v for k,v in before.items())
    seed = prepare_furanose_bridge_seed(original / "edge", original / "seed",
                                        endpoint_weight=1000., max_base_displacement=2.)
    # Rotating the phosphate arm and fitting the whole body preserve the transferred torsion.
    # The unrounded seed detects even a small return to the numerical dictionary's starting angle.
    final = _chi(seed["full_precision_heavy_coordinates"], rotation["source_atoms"])
    assert abs((final - rotation["host_degrees"] + 180) % 360 - 180) < 1e-6
    assert max(abs(row["pdb_rounded"] - 1.61) for row in seed["junctions"]) < 0.02
    measured = _pdb_inventory(original / "seed" / "model.pdb")
    assert sum(key[:2] == ("A", "2") for key in measured) == len(result["model_heavy_atoms"])
    relocated = original.rename(tmp_path / "moved") / "edge"
    with patch("subprocess.Popen", side_effect=AssertionError("cold read started a program")):
        assert read_base_anchored_furanose_control(relocated) == result


@pytest.mark.parametrize("bad_host", [False, True])
def test_pairing_edge_seed_starts_with_the_host_residue_median_b(tmp_path, bad_host):
    from statistics import median
    from nasolve.cif_furanose_bridge import read_furanose_bridge_seed

    target, numbers, host, book, frame = inputs(tmp_path)
    lines = frame.read_text().splitlines(keepends=True)
    host_b = []
    for index, line in enumerate(lines):
        if line.startswith("ATOM  ") and line[21:26] == "A   2":
            value = 77.5 + len(host_b) * 3.4
            occupancy = 0.5 if bad_host and not host_b else 1.0
            host_b.append(value)
            lines[index] = line[:54] + f"{occupancy:6.2f}{value:6.2f}" + line[66:]
    frame.write_text("".join(lines))
    placed = tmp_path / "placement"
    prepare_base_anchored_furanose_from_model(target, numbers, host, book, frame, placed,
        code="UY1", site="A:2", postmr_report=report(), canonical_at_edge=True)
    out = tmp_path / "seed"
    record = prepare_furanose_bridge_seed(placed, out, endpoint_weight=1000., max_base_displacement=2.)
    decision = record["site_displacement"]
    built = (out / "model.pdb").read_text().splitlines()
    selected = [l for l in built if l[:6] in {"ATOM  ", "HETATM"} and l[21:26] == "A   2"]
    if bad_host:
        assert decision["status"] == "RETAINED_SEED" and "occupancy" in decision["reason"]
        assert {float(l[60:66]) for l in selected} == {20.0}
    else:
        assert decision["status"] == "HOST_RESIDUE_MEDIAN"
        assert decision["host_atoms"] == len(host_b) and decision["replacement_atoms"] == len(selected)
        assert {float(l[60:66]) for l in selected} == {float(f"{median(host_b):.2f}")}
    assert {float(l[54:60]) for l in selected} == {1.0}

    def bystanders(lines):
        return [l for l in lines if not (l[:6] in {"ATOM  ", "HETATM"} and l[21:26] == "A   2")]

    assert bystanders(built) == bystanders((placed / "model.pdb").read_text().splitlines())
    moved = out.rename(tmp_path / "moved")
    assert read_furanose_bridge_seed(moved) == record


@pytest.mark.parametrize("defect,reason", [("workbook", "pairing contacts"), ("mirror", "sugar hands"),
                                           ("manual", "explicit base frame")])
def test_ambiguous_or_inconsistent_placement_does_not_allocate_output(tmp_path, defect, reason):
    paths = inputs(tmp_path, wrong_edge=defect == "workbook", mirror=defect == "mirror")
    options = {"base_frame_roles": ["N1","C2","C6"]} if defect == "manual" else {}
    with pytest.raises(ValueError, match=reason):
        prepare_base_anchored_furanose_from_model(*paths, tmp_path/"placement", code="UY1",
            site="A:2", postmr_report=report(), canonical_at_edge=True, **options)
    assert not (tmp_path / "placement").exists()
    if defect in {"workbook", "mirror"}:
        with pytest.raises(ValueError, match=reason):
            prepare_base_anchored_furanose_from_model(*paths, tmp_path / "auto", code="UY1",
                site="A:2", postmr_report=report())
        assert not (tmp_path / "auto").exists()
