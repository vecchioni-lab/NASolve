"""A sulfur side follows the component graph and the recorded crystal connection."""
import json
from pathlib import Path

import pytest

from nasolve.cli import main
from nasolve.cif_linked_preparation import _render, component_values
from .test_cif_deposition_links import make_cif

gemmi = pytest.importorskip("gemmi")
PUBLIC = Path(__file__).parent / "fixtures" / "public_ccd"
NAMES = {"P": "PX", "OP1": "KEEP", "OP2": "TIP", "OP3": "LEAVE", "O5'": "ARM"}


def inputs(root, *, extended=True, reverse=False):
    values = component_values(PUBLIC / "PDU.cif", "PDU")
    idx = values["_chem_comp_atom.atom_id"].index("OP2")
    values["_chem_comp_atom.type_symbol"][idx] = "S"
    for key, column in values.items():
        if "atom_id" in key:
            values[key] = [NAMES.get(atom, atom) for atom in column]
    dictionary = root / "component.cif"
    dictionary.write_text(_render(values, "PDU"))

    model = make_cif(root / "model.cif", extended=extended, reverse=reverse)
    doc = gemmi.cif.read_file(str(model))
    for category in ("_atom_site.", "_struct_conn."):
        table = doc[0].get_mmcif_category(category)
        for key, column in table.items():
            if key.endswith("comp_id"):
                table[key] = ["PDU" if v == "QX" else v for v in column]
            elif key.endswith("atom_id"):
                table[key] = [NAMES.get(v, v) for v in column]
        if category == "_atom_site.":
            table["type_symbol"][table["label_atom_id"].index("TIP")] = "S"
        doc[0].set_mmcif_category(category, table)
    doc.write_file(str(model))
    return model, dictionary


def read(model, dictionary, capsys, status=0):
    assert main(["cif-doctor", "sulfur-links", str(model), str(dictionary),
                 "--code", "PDU", "--json"]) == status
    return json.loads(capsys.readouterr().out)


def test_relative_sulfur_hand_uses_declared_crystal_mate_and_survives_relocation(tmp_path, capsys):
    original = tmp_path / "original"
    original.mkdir()
    model, source = inputs(original, reverse=True)
    before = [(p.stat().st_mtime_ns, p.read_bytes()) for p in (model, source)]
    report = read(model, source, capsys)
    site, = report["sites"]
    assert site["status"] == "MEASURED" and site["donor_image_in_phosphate_frame"] == "x+1,y,z"
    assert site["lengths_A"]["preceding_O3"] == pytest.approx(1.61)
    assert len(site["lengths_A"]) == 4 and len(site["angles_deg"]) == 6
    assert site["donor_C3_O3_P_deg"] is not None
    assert site["ordered_volume_A3"] != 0
    assert report["roles"] == {"phosphorus": "PX", "carbon_linked_oxygen": "ARM",
                               "retained_oxygen": "KEEP", "sulfur": "TIP", "leaving_oxygen": "LEAVE"}
    assert before == [(p.stat().st_mtime_ns, p.read_bytes()) for p in (model, source)]
    moved = original.rename(tmp_path / "moved")
    assert read(moved / model.name, moved / source.name, capsys) == report


def test_mirror_reverses_hand_without_changing_the_six_angles(tmp_path, capsys):
    model, source = inputs(tmp_path, extended=False)
    doc = gemmi.cif.read_file(str(model))
    # An identical explicit image at both ends cancels even when the numbered
    # operation is not tabulated. PDB coordinates often omit the operator list.
    doc[0].find_loop("_space_group_symop.id").erase()
    doc.write_file(str(model))
    first, = read(model, source, capsys)["sites"]
    atoms = doc[0].get_mmcif_category("_atom_site.")
    atoms["Cartn_z"] = [str(-float(z)) for z in atoms["Cartn_z"]]
    doc[0].set_mmcif_category("_atom_site.", atoms)
    doc.write_file(str(model))
    second, = read(model, source, capsys)["sites"]
    assert first["ordered_volume_A3"] == pytest.approx(-second["ordered_volume_A3"])
    assert first["native_order_volume_A3"] == pytest.approx(-second["native_order_volume_A3"])
    assert first["angles_deg"] == pytest.approx(second["angles_deg"])


@pytest.mark.parametrize("case", ["no_declaration", "unknown_image", "duplicate_link",
    "wrong_element", "unassigned_alternate", "leaving_oxygen", "zero_occupancy", "conflicting_sequence"])
def test_incomplete_site_has_no_assigned_hand(tmp_path, capsys, case):
    model, source = inputs(tmp_path)
    doc = gemmi.cif.read_file(str(model))
    block = doc[0]
    if case in {"no_declaration", "unknown_image", "duplicate_link"}:
        table = block.get_mmcif_category("_struct_conn.")
        if case == "no_declaration":
            table["conn_type_id"] = ["hydrog"]
        elif case == "unknown_image":
            table["ptnr2_symmetry"] = ["6_455"]
        else:
            table = {k: v * 2 for k, v in table.items()}
            table["id"][1] = "c2"
        block.set_mmcif_category("_struct_conn.", table)
    elif case == "conflicting_sequence":
        block.set_mmcif_category("_entity_poly_seq.", {"entity_id": ["1","1"],
            "num": ["1","2"], "mon_id": ["WRONG","PDU"]})
    else:
        table = block.get_mmcif_category("_atom_site.")
        index = table["label_atom_id"].index("TIP")
        if case == "wrong_element":
            table["type_symbol"][index] = "O"
        elif case == "unassigned_alternate":
            table["label_alt_id"][index] = "A"
        elif case == "zero_occupancy":
            table["occupancy"][index] = "0"
        else:
            for col in table.values():
                col.append(col[index])
            table["label_atom_id"][-1], table["type_symbol"][-1], table["id"][-1] = "LEAVE","O","99"
        block.set_mmcif_category("_atom_site.", table)
    doc.write_file(str(model))
    report = read(model, source, capsys, 2)
    site, = report["sites"]
    assert report["status"] == "REVIEW" and site["status"] != "MEASURED"
    assert "ordered_volume_A3" not in site


def test_declared_alternate_is_measured_and_conflicting_aliases_are_rejected(tmp_path, capsys):
    model, source = inputs(tmp_path, extended=False)
    doc = gemmi.cif.read_file(str(model))
    atoms = doc[0].get_mmcif_category("_atom_site.")
    atoms["label_alt_id"][atoms["label_atom_id"].index("TIP")] = "B"
    doc[0].set_mmcif_category("_atom_site.", atoms)
    link = doc[0].get_mmcif_category("_struct_conn.")
    link["ptnr2_label_alt_id"] = ["B"]
    doc[0].set_mmcif_category("_struct_conn.", link)
    doc.write_file(str(model))
    site, = read(model, source, capsys)["sites"]
    assert site["status"] == "MEASURED"
    link["pdbx_ptnr2_label_alt_id"] = ["A"]
    doc[0].set_mmcif_category("_struct_conn.", link)
    doc.write_file(str(model))
    assert main(["cif-doctor","sulfur-links",str(model),str(source),"--code","PDU"]) == 1
    assert "Conflicting alternate" in capsys.readouterr().err


@pytest.mark.parametrize("atom,x", [("PX", "-0.9"), ("O3'", "-20")])
def test_outside_phosphorus_and_long_link_have_no_assigned_hand(tmp_path, capsys, atom, x):
    model, source = inputs(tmp_path, extended=False)
    doc = gemmi.cif.read_file(str(model))
    atoms = doc[0].get_mmcif_category("_atom_site.")
    atoms["Cartn_x"][atoms["label_atom_id"].index(atom)] = x
    doc[0].set_mmcif_category("_atom_site.", atoms)
    doc.write_file(str(model))
    site, = read(model, source, capsys, 2)["sites"]
    assert site["status"] == ("LONG_DECLARED_LINK" if atom == "O3'" else "PHOSPHORUS_OUTSIDE_TETRAHEDRON")
    assert "ordered_volume_A3" not in site


def test_rotated_shifted_donor_is_compared_in_the_original_phosphorus_frame(tmp_path, capsys):
    model, source = inputs(tmp_path, extended=False)
    original, = read(model, source, capsys)["sites"]
    doc = gemmi.cif.read_file(str(model))
    block = doc[0]
    block.set_mmcif_category("_symmetry.", {"space_group_name_H-M": ["P 4"]})
    block.set_mmcif_category("_space_group_symop.", {
        "id": ["1", "2", "3", "4"],
        "operation_xyz": ["x,y,z", "-y,x,z", "-x,-y,z", "y,-x,z"],
    })
    link = block.get_mmcif_category("_struct_conn.")
    link["ptnr1_symmetry"], link["ptnr2_symmetry"] = ["3_655"], ["2_555"]
    block.set_mmcif_category("_struct_conn.", link)
    atoms = block.get_mmcif_category("_atom_site.")
    for i, number in enumerate(atoms["label_seq_id"]):
        if number == "1":
            x, y = float(atoms["Cartn_x"][i]), float(atoms["Cartn_y"][i])
            atoms["Cartn_x"][i], atoms["Cartn_y"][i] = str(y + 20), str(-x)
    block.set_mmcif_category("_atom_site.", atoms)
    doc.write_file(str(model))
    site, = read(model, source, capsys)["sites"]
    assert site["donor_image_in_phosphate_frame"] == "-y,x-1,z"
    for key in ("lengths_A", "angles_deg", "donor_C3_O3_P_deg", "ordered_volume_A3", "native_order_volume_A3"):
        assert site[key] == pytest.approx(original[key])


def test_optional_donor_carbon_and_individual_models(tmp_path, capsys):
    model, source = inputs(tmp_path, extended=False)
    doc = gemmi.cif.read_file(str(model))
    atoms = doc[0].get_mmcif_category("_atom_site.")
    keep = [i for i, name in enumerate(atoms["label_atom_id"]) if name != "C3'"]
    atoms = {key: [values[i] for i in keep] for key, values in atoms.items()}
    count = len(keep)
    atoms = {key: values + values for key, values in atoms.items()}
    atoms["id"] = [str(i + 1) for i in range(2 * count)]
    atoms["pdbx_PDB_model_num"][count:] = ["2"] * count
    atoms["Cartn_z"][count:] = [str(-float(z)) for z in atoms["Cartn_z"][count:]]
    doc[0].set_mmcif_category("_atom_site.", atoms)
    doc.write_file(str(model))
    first, second = read(model, source, capsys)["sites"]
    assert (first["model"], second["model"]) == ("1", "2")
    assert first["donor_C3_O3_P_deg"] is second["donor_C3_O3_P_deg"] is None
    assert first["ordered_volume_A3"] == pytest.approx(-second["ordered_volume_A3"])


def test_source_without_sulfur_and_absent_component_are_reported(tmp_path, capsys):
    model, source = inputs(tmp_path)
    report = read(model, PUBLIC / "PDU.cif", capsys, 2)
    assert report["review_reasons"] == ["NO_PHOSPHORUS_SULFUR_BOND"]
    assert not report["sites"]
    doc = gemmi.cif.read_file(str(model))
    atoms = doc[0].get_mmcif_category("_atom_site.")
    atoms["label_comp_id"] = ["UNK" if x == "PDU" else x for x in atoms["label_comp_id"]]
    doc[0].set_mmcif_category("_atom_site.", atoms)
    doc.write_file(str(model))
    report = read(model, source, capsys, 2)
    assert report["review_reasons"] == ["NO_MATCHING_NUCLEIC_ACID_POLYMER_SITE"]
