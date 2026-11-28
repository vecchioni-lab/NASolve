"""Every candidate sequence step can be joined to a physical backbone record by label."""
import json
import pytest
from nasolve.cli import main
from nasolve.cif_deposition_links import inspect_deposition_links
from .test_cif_deposition_links import make_cif, gemmi


def test_ordinary_measurements_share_labels_and_angles_with_the_declared_bond(tmp_path, capsys):
    path = make_cif(tmp_path / "joined.cif", extended=False)
    old = inspect_deposition_links(path)
    result = inspect_deposition_links(path, processed=path, include_ordinary_steps=True)
    assert old["status"] == result["status"] == "CHECKED" and "steps" not in old["model"]["ordinary"]
    for branch in ("model", "processed"):
        ordinary = result[branch]["ordinary"].copy()
        row, = ordinary.pop("steps")
        assert ordinary == old["model"]["ordinary"]
        decl, = result[branch]["declared"]
        assert row["status"] == "MEASURED" and row["model"] == "1" and row["operator_on_P"] == "x,y,z"
        assert row["O3_label"] == decl["O3_label"] and row["P_label"] == decl["P_label"]
        for k in ("distance_A", "O3_P_OP1_deg", "O3_P_OP2_deg", "O3_P_O5prime_deg"):
            assert row[k] == pytest.approx(decl["observations"][0][k], abs=1e-10)
    assert main(["cif-doctor","deposition-links",str(path),"--ordinary-steps","--json"]) == 0
    assert json.loads(capsys.readouterr().out)["model"]["ordinary"]["steps"][0]["P_label"] == ["NA","2","QX",""]


def test_gaps_and_unassigned_conformers_are_never_completed_by_proximity(tmp_path):
    for label, options, status in (("gap", dict(gap=True), "SEQUENCE_GAP"),
                                   ("alternates", dict(alt=True), "UNMEASURED")):
        path = make_cif(tmp_path / f"{label}.cif", extended=False, link=False, **options)
        report = inspect_deposition_links(path, include_ordinary_steps=True)
        row, = report["model"]["ordinary"]["steps"]
        assert report["status"] == "REVIEW" and row["status"] == status
        assert row["distance_A"] is None and row["O3_P_OP2_deg"] is None
        if label == "alternates":
            assert row["O3_label"] is None and row["P_label"] == ("NA", "2", "QX", "")


def test_identity_measurement_without_cell_and_missing_op_oxygen(tmp_path):
    source = make_cif(tmp_path / "uncelled.cif", extended=False, link=False)
    doc = gemmi.cif.read_file(str(source))
    b = doc[0]
    for item in list(b):
        tag = item.loop.tags[0] if item.loop else item.pair[0] if item.pair else ""
        if tag.startswith("_cell."):
            item.erase()
    atoms = b.get_mmcif_category("_atom_site.")
    atoms["occupancy"][atoms["label_atom_id"].index("OP2")] = "0"
    b.set_mmcif_category("_atom_site.", atoms)
    doc.write_file(str(source))
    report = inspect_deposition_links(source, include_ordinary_steps=True)
    row, = report["model"]["ordinary"]["steps"]
    assert report["status"] == "REVIEW" and row["status"] == "PARTIAL_ANGLES"
    assert row["distance_A"] == pytest.approx(1.61)
    assert row["O3_P_OP2_deg"] is None and 90 < row["O3_P_OP1_deg"] < 130


def test_full_identity_operator_and_sequence_distinct_from_explicit_image(tmp_path):
    path = make_cif(tmp_path / "different.cif", extended=True)
    r = inspect_deposition_links(path, include_ordinary_steps=True)
    direct, = r["model"]["ordinary"]["steps"]
    image, = r["model"]["declared"]
    assert direct["status"] == "LONG" and direct["operator_on_P"] == "x,y,z"
    assert direct["distance_A"] == pytest.approx(21.61)
    assert image["operator_on_P"] != direct["operator_on_P"] and image["observations"][0]["distance_A"] == pytest.approx(1.61)



def test_models_and_alternate_labels_remain_distinct(tmp_path):
    source = make_cif(tmp_path / "ensemble.cif", extended=False, link=False)
    doc = gemmi.cif.read_file(str(source))
    atoms = doc[0].get_mmcif_category("_atom_site.")
    size = len(atoms["id"])
    for key, values in atoms.items():
        if key == "id":
            values.extend(str(i) for i in range(size + 1, 2 * size + 1))
        elif key == "pdbx_PDB_model_num":
            values.extend(["2"] * size)
        else:
            values.extend(values[:])
    atoms["label_alt_id"][0] = "A"
    atoms["label_alt_id"][2] = "B"
    doc[0].set_mmcif_category("_atom_site.", atoms)
    doc.write_file(str(source))
    result = inspect_deposition_links(source, include_ordinary_steps=True)
    one, two = result["model"]["ordinary"]["steps"]
    assert one["model"] == "1" and one["status"] == "ALTERNATE_LABEL_REVIEW"
    assert one["O3_label"][-1] == "A" and one["P_label"][-1] == "B"
    assert two["model"] == "2" and two["status"] == "MEASURED"
    assert one["distance_A"] == two["distance_A"] == pytest.approx(1.61)
    assert result["status"] == "REVIEW"
