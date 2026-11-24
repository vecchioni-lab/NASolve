"""A separate starting-coordinate trial for one graph-selected alkynyl methyl."""
import json
import re

import pytest

from nasolve.cif_doctor_repair import prepare_dictionary
from nasolve.cli import main
from nasolve.ligand_profiles import _blocks, _emit


RECIPE = "alkynyl-methyl-template-v1"


def molecule(start):
    code = "ZXQ"
    atoms = ["left", "sp", "cap", "one", "two", "three", "tailH"]
    edges = [("left", "sp", "TRIP"), ("sp", "cap", "SING"),
             ("cap", "one", "SING"), ("cap", "two", "SING"), ("cap", "three", "SING"), ("left", "tailH", "SING")]
    data = {"data_": "alternate_names", "_chem_comp.id": [code],
            "_chem_comp_atom.comp_id": [code] * 7, "_chem_comp_atom.atom_id": atoms,
            "_chem_comp_atom.type_symbol": ["C"] * 3 + ["H"] * 4,
            "_chem_comp_atom.charge": ["0"] * 7,
            "_chem_comp_atom.x": list(map(str, [-1.2, 0, start, start+.3, start+.3, start+.3, -2.2])),
            "_chem_comp_atom.y": ["0", "0", "0", ".6", "-.3", "-.3", "0"],
            "_chem_comp_atom.z": ["0", "0", "0", "0", ".52", "-.52", "0"],
            "_chem_comp_bond.comp_id": [code] * 6,
            "_chem_comp_bond.atom_id_1": [a for a,b,o in edges],
            "_chem_comp_bond.atom_id_2": [b for a,b,o in edges],
            "_chem_comp_bond.type": [o for a,b,o in edges],
            "_chem_comp_bond.value_dist": ["1.20", "1.47", "1.09", "1.09", "1.09", "1.0"],
            "_chem_comp_bond.value_dist_esd": [".02"] * 6}
    return data


def source_file(tmp_path, values):
    source = tmp_path / "supplier.cif"
    source.write_text("# Original supplier metadata\n" + _emit(values) + "\n# Preserve the trailing comment\n")
    return source


@pytest.mark.parametrize("start", [1.36, 1.61])
def test_candidate_moves_only_methyl_positions_and_retains_native_layout(tmp_path, start, capsys):
    values = molecule(start)
    source = source_file(tmp_path, values)
    before = source.read_bytes()
    candidate = tmp_path / "trial.cif"
    assert main(["cif-doctor", "prepare", str(source), "--recipe", RECIPE, "--output", str(candidate), "--json"]) == 2
    report = json.loads(capsys.readouterr().out)
    event, = report["events"]
    assert event["bond"] == ["sp", "cap"] and event["moved_atoms"] == ["cap", "one", "three", "two"]
    assert event["starting_A"] == pytest.approx(start) and event["candidate_A"] == pytest.approx(1.47)
    assert not report["automatic_adoption"] and report["source_preserved"] and report["changed"]
    raw = candidate.read_bytes()
    assert raw.startswith(b"# Original supplier metadata") and raw.endswith(b"# Preserve the trailing comment\n")
    assert source.read_bytes() == before
    orig = _blocks(source)[0].values
    actual = _blocks(candidate)[0].values
    assert float(actual["_chem_comp_atom.x"][2]) == pytest.approx(1.47)
    assert actual["_chem_comp_atom.x"][:2] == orig["_chem_comp_atom.x"][:2]
    for k in orig:
        if k not in {"_chem_comp_atom." + a for a in "xyz"}:
            assert orig[k] == actual[k]
    with pytest.raises(FileExistsError):
        prepare_dictionary(source, candidate, recipe=RECIPE)


def test_already_at_target_makes_an_exact_copy(tmp_path):
    source = source_file(tmp_path, molecule(1.47))
    target = tmp_path / "trial.cif"
    report = prepare_dictionary(source, target, recipe=RECIPE)
    assert target.read_bytes() == source.read_bytes() and not report["changed"]


@pytest.mark.parametrize("problem", ["hydrogen isotope", "wrong bond", "extra heavy connection",
                                     "unresolved hand", "no length", "incomplete coordinates", "zero axis", "charged methyl"])
def test_candidate_declines_unqualified_geometry_before_writing(tmp_path, problem):
    values = molecule(1.36)
    if problem == "hydrogen isotope":
        values["_chem_comp_atom.type_symbol"][3] = "D"
    elif problem == "wrong bond":
        values["_chem_comp_bond.type"][0] = "DOUB"
    elif problem == "extra heavy connection":
        values["_chem_comp_atom.type_symbol"][3] = "C"
    elif problem == "unresolved hand":
        values["_chem_comp_atom.pdbx_stereo_config"] = ["N", "N", "R", "N", "N", "N", "N"]
    elif problem == "no length":
        values["_chem_comp_bond.value_dist"][1] = "?"
    elif problem == "incomplete coordinates":
        values["_chem_comp_atom.z"][3] = "?"
    elif problem == "zero axis":
        values["_chem_comp_atom.x"][2] = "0"
    else:
        values["_chem_comp_atom.charge"][2] = "-1"
    source = source_file(tmp_path, values)
    target = tmp_path / "rejected.cif"
    with pytest.raises(ValueError):
        prepare_dictionary(source, target, recipe=RECIPE)
    assert not target.exists()


def test_other_coordinate_sets_quotes_and_wrapped_rows_are_preserved(tmp_path):
    values = molecule(1.61)
    for axis in "xyz":
        values["_chem_comp_atom.pdbx_model_Cartn_" + axis + "_ideal"] = list(values["_chem_comp_atom." + axis])
    source = source_file(tmp_path, values)
    text = source.read_text()
    text, count = re.subn(r"(?m)^ZXQ\s+cap\s+C\s+", "ZXQ  'cap'\n C  ", text, count=1)
    assert count == 1
    source.write_text(text)
    dest = tmp_path / "trial.cif"
    prepare_dictionary(source, dest, recipe=RECIPE)
    ref = _blocks(source)[0].values
    actual = _blocks(dest)[0].values
    assert "'cap'\n C" in dest.read_text()
    for axis in "xyz":
        key = "_chem_comp_atom.pdbx_model_Cartn_" + axis + "_ideal"
        assert ref[key] == actual[key]


@pytest.mark.parametrize("kind", ["link", "mod", "leaving"])
def test_residue_context_must_leave_the_methyl_terminal(tmp_path, kind):
    values = molecule(1.36)
    if kind == "leaving":
        values["_chem_comp_atom.pdbx_leaving_atom_flag"] = ["N", "N", "Y", "N", "N", "N", "N"]
    source = source_file(tmp_path, values)
    if kind != "leaving":
        category = "_chem_link_bond" if kind == "link" else "_chem_mod_bond"
        with source.open("a") as stream:
            stream.write("\ndata_context\n" + category + ".atom_id_1 cap\n" + category + ".atom_id_2 X\n")
    dest = tmp_path / "trial.cif"
    with pytest.raises(ValueError, match="declared"):
        prepare_dictionary(source, dest, recipe=RECIPE)
    assert not dest.exists()


def test_second_eligible_methyl_or_explicit_volume_requires_review(tmp_path):
    values = molecule(1.36)
    a, b = "_chem_comp_atom.", "_chem_comp_bond."
    values[a+"type_symbol"][-1] = "C"
    for field, extra in {"comp_id": ["ZXQ"]*3, "atom_id": ["x1","x2","x3"], "type_symbol": ["H"]*3,
                         "charge": ["0"]*3, "x": ["-2.5"]*3, "y": [".6","-.3","-.3"],
                         "z": ["0",".52","-.52"]}.items():
        values[a+field].extend(extra)
    for field, extra in {"comp_id": ["ZXQ"]*3, "atom_id_1": ["tailH"]*3, "atom_id_2": ["x1","x2","x3"],
                         "type": ["SING"]*3, "value_dist": ["1.09"]*3, "value_dist_esd": [".02"]*3}.items():
        values[b+field].extend(extra)
    src = source_file(tmp_path, values)
    with pytest.raises(ValueError, match="one neutral terminal methyl"):
        prepare_dictionary(src, tmp_path/"ambiguous.cif", recipe=RECIPE)
    values = molecule(1.36)
    for key, value in {"comp_id":"ZXQ", "id":"hand", "atom_id_centre":"cap", "atom_id_1":"one",
                       "atom_id_2":"two", "atom_id_3":"three", "volume_sign":"both"}.items():
        values["_chem_comp_chir."+key] = [value]
    src = source_file(tmp_path, values)
    with pytest.raises(ValueError, match="declared chiral volume"):
        prepare_dictionary(src, tmp_path/"chiral.cif", recipe=RECIPE)
    assert not (tmp_path/"ambiguous.cif").exists() and not (tmp_path/"chiral.cif").exists()
