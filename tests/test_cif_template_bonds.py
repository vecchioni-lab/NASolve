"""Dictionary starting coordinates and refinement targets retain separate meanings."""
import json
import shutil
from pathlib import Path

import pytest

from nasolve.cif_doctor import assess_dictionaries
from nasolve.cli import main
from nasolve.ligand_profiles import _emit

from .test_cif_doctor_degenerate_geometry import _component


def audit(tmp_path, values):
    from nasolve.cif_template_bonds import read_template_bonds

    path = tmp_path / "explicit.cif"
    path.write_text(_emit(values))
    receipt = assess_dictionaries([path])
    result = read_template_bonds([path], receipt)
    assert "template_bonds" not in receipt
    return result["components"][0]


def test_template_and_ccd_families_are_measured_separately_without_a_model(tmp_path):
    values = _component()
    for axis in "xyz":
        source = values["_chem_comp_atom." + axis]
        values["_chem_comp_atom.pdbx_model_Cartn_" + axis + "_ideal"] = list(source)
        values["_chem_comp_atom.model_Cartn_" + axis] = ["?"] * 4
    values["_chem_comp_atom.x"][1] = "1.64(1)"
    values["_chem_comp_atom.pdbx_model_Cartn_x_ideal"][1] = "1.50"
    values["_chem_comp_bond.value_dist_esd"][1] = "?"
    item = audit(tmp_path, values)
    xyz, ideal, model = item["coordinate_sets"]
    assert [s["family"] for s in (xyz, ideal, model)] == ["RESTRAINT_CARTESIAN", "SOURCE_IDEAL", "SOURCE_MODEL"]
    first, second = xyz["bonds"]
    assert set(first["atoms"]) == {"C5", "C5'"}
    assert first["distance_A"] == pytest.approx(1.64)
    assert first["minus_target_A"] == pytest.approx(.14)
    assert first["difference_in_esds"] == pytest.approx(7.)
    assert ideal["bonds"][0]["minus_target_A"] == pytest.approx(0.)
    assert second["difference_in_esds"] is None
    assert model["measured"] == 0 and all(b["reason"] == "coordinates-unavailable" for b in model["bonds"])
    assert all("H1" not in row["atoms"] for row in xyz["bonds"])


@pytest.mark.parametrize("mode", ["graph-only", "nuclear-only", "duplicate", "no-coordinates"])
def test_missing_chemical_authority_is_explained(tmp_path, mode):
    values = _component(numerical=mode != "graph-only", coordinate_set=None if mode == "no-coordinates" else "atom_xyz")
    if mode == "nuclear-only":
        values["_chem_comp_bond.value_dist_nucleus"] = values.pop("_chem_comp_bond.value_dist")
    if mode == "duplicate":
        values["_chem_comp_atom.atom_id"][1] = "C5"
    item = audit(tmp_path, values)
    if mode == "nuclear-only":
        group, = item["coordinate_sets"]
        assert group["measured"] == 0 and {b["reason"] for b in group["bonds"]} == {"no-positive-value_dist"}
    else:
        assert item["reason"] == {"graph-only": "graph-only", "duplicate": "ambiguous-graph", "no-coordinates": "no-coordinate-set"}[mode]


def test_changed_dictionary_cannot_be_spliced_into_an_older_report(tmp_path):
    from nasolve.cif_template_bonds import read_template_bonds

    path = tmp_path / "input.cif"
    path.write_text(_emit(_component()))
    receipt = assess_dictionaries([path])
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="changed"):
        read_template_bonds([path], receipt)


def test_named_checkpoint_uses_its_frozen_dictionary_after_the_run_moves(tmp_path):
    from nasolve.cif_doctor_run import assess_run
    from .test_checkpoints import make_checkpoint_run
    from .test_cif_doctor_run import _child, _reference, _snapshot

    original = tmp_path / "original"
    run = make_checkpoint_run(original)
    _child(run)
    index = run / "AutoRefine/checkpoints.json"
    registry = json.loads(index.read_text())
    ligand = run / "AutoRefine/refine_001/effective.cif"
    ligand.write_text(_emit(_component()))
    registry["checkpoints"][-1]["restraints"][1] = _reference(ligand, run)
    index.write_text(json.dumps(registry))
    moved = tmp_path / "moved"
    shutil.move(original, moved)
    destination = moved / run.relative_to(original)
    before = _snapshot(moved)
    assessment = assess_run(destination, checkpoint="refine-001", template_bonds=True)
    row, = assessment["template_bonds"]["components"]
    assert row["input_index"] == 1 and row["coordinate_sets"][0]["measured"] == 2
    assert before == _snapshot(moved)


def test_cli_reports_each_input_after_relocation_and_preserves_default(tmp_path, capsys):
    src = tmp_path / "first"
    src.mkdir()
    chain = _component()
    for name, x in [("a", "1.64"), ("b", "1.51")]:
        chain["_chem_comp_atom.x"][1] = x
        (src / (name + ".cif")).write_text(_emit(chain))
    dst = tmp_path / "second"
    shutil.move(src, dst)
    paths = [str(dst / (x + ".cif")) for x in ("a", "b")]
    before = [Path(p).read_bytes() for p in paths]
    main(["cif-doctor", "assess", *paths, "--json"])
    default = json.loads(capsys.readouterr().out)
    main(["cif-doctor", "assess", *paths, "--template-bonds", "--json"])
    requested = json.loads(capsys.readouterr().out)
    items = requested.pop("template_bonds")["components"]
    assert requested == default and [r["input_index"] for r in items] == [0, 1]
    assert [r["coordinate_sets"][0]["bonds"][0]["distance_A"] for r in items] == pytest.approx([1.64, 1.51])
    assert [Path(p).read_bytes() for p in paths] == before
