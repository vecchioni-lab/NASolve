"""An explicitly proven ribose is protected during whole-base placement."""
from math import dist, radians

import pytest

from nasolve.cif_base_rotation_audit import rotate_group
from nasolve.cif_stereochemistry_audit import _values
from nasolve.ligand_profiles import _emit
from nasolve.postmr import MutationAction, construct_postmr_model
from nasolve.postmr_canonical_seed import canonical_parent_seed
from nasolve.postmr_conformation import parent_conformation_plan
from nasolve.postmr_restoration import _atom_records, restore_graph_site, source_graph_fragment
from tests.test_postmr_ribose_parent import SOURCE, TEMPLATE, frame
from tests.test_postmr_canonical_seed import selected


def local_component(tmp_path, defect=None):
    values = _values(TEMPLATE, "G")
    for key in list(values):
        if key == "_chem_comp.id" or key.endswith(".comp_id"):
            values[key] = ["RXG"] * len(values[key])
    index = values["_chem_comp_atom.atom_id"].index
    if defect == "charge":
        values["_chem_comp_atom.charge"][index("O2'")] = "-1"
    if defect == "wrong_marker":
        values["_chem_comp_atom.pdbx_stereo_config"][index("C2'")] = "S"
    if defect == "ether":
        values["_chem_comp_atom.type_symbol"][index("HO2'")] = "C"
    path = tmp_path / "local.cif"
    path.write_text(_emit(values))
    return path


def placed_models():
    seeded, _ = canonical_parent_seed(frame(), "A:1", SOURCE, "DG", TEMPLATE, "G")
    parent = selected(seeded, "G")
    raw_lines = []
    for row in parent.values():
        x, y, z = row["xyz"]
        line = row["line"]
        raw_lines.append(line[:17] + "RXG" + line[20:30] +
                         "".join(f"{v:8.3f}" for v in (7 - y, x, 9 + z)) + line[54:])
    return raw_lines, [row["line"] for row in parent.values()]


def test_source_reader_accepts_ccd_mixed_case_cartesian_tags():
    graph = source_graph_fragment(TEMPLATE, "G", ribose_parent=(TEMPLATE, "G"))
    assert graph["attachment_atom"] == "N9"
    assert "O2'" in graph["sugar_atoms"]


def test_rotated_base_is_detected_even_when_all_ribose_centres_are_correct(tmp_path):
    target = local_component(tmp_path)
    graph = source_graph_fragment(target, "RXG", ribose_parent=(TEMPLATE, "G"))
    raw, parent = placed_models()
    atoms = _atom_records(raw, "RXG")
    order = list(atoms)
    group = {"origin_index": order.index("C1'"), "attachment_index": order.index("N9"),
             "i_seqs": [order.index(n) for n in graph["fragment_atoms"]]}
    points = rotate_group([list(atoms[n]["xyz"]) for n in order], group, radians(30))
    rotated = [line[:30] + "".join(f"{v:8.3f}" for v in xyz) + line[54:] for line, xyz in zip(raw, points)]
    with pytest.raises(ValueError, match="glycosidic torsion"):
        restore_graph_site(rotated, parent, target, "RXG", "G", ribose_template=TEMPLATE)


def test_unrecognized_modified_ribose_protects_the_whole_sugar_and_base(tmp_path):
    target = local_component(tmp_path)
    with pytest.raises(ValueError, match="DNA"):
        source_graph_fragment(target, "RXG")  # Historical deoxy-only policy.
    plan = parent_conformation_plan(target, "RXG", "G", ribose_template=TEMPLATE)
    assert plan["status"] == "MATCH_PARENT_CHI"
    assert plan["atoms"] == ["O4'", "C1'", "N9", "C4"]
    raw, parent = placed_models()
    restored, proof = restore_graph_site(raw, parent, target, "RXG", "G", ribose_template=TEMPLATE)
    original, expected, actual = (_atom_records(rows, name) for rows, name in
                                  ((raw, "RXG"), (parent, "G"), (restored, "RXG")))
    assert "O2'" in proof["scaffold_atoms"]
    assert set(proof["ribose_hands"]) == {"C1'", "C2'", "C3'", "C4'"}
    assert all(actual[n]["xyz"] == expected[n]["xyz"] for n in proof["scaffold_atoms"])
    for a in proof["fragment_atoms"]:
        for b in proof["fragment_atoms"]:
            assert dist(actual[a]["xyz"], actual[b]["xyz"]) == pytest.approx(
                dist(original[a]["xyz"], original[b]["xyz"]), abs=0.002)


@pytest.mark.parametrize("changed_parent", (False, True))
def test_construct_uses_the_frozen_ribose_for_coordinates_and_displacement(tmp_path, monkeypatch, changed_parent):
    target = local_component(tmp_path)
    model, output = tmp_path / "host.pdb", tmp_path / "work" / "model.pdb"
    model.write_bytes(frame())
    action = MutationAction("A:1", "DG", "RXG", "coot-parent-overlap", parent_code="G")

    def coot(seed, raw, actions, executable, directory, environment, dictionaries, parents, **options):
        assert options["ribose_templates"]["A:1"].parent.name == "canonical_seeds"
        assert actions[0].before == "G"
        snapshot = seed.read_bytes()
        if changed_parent:
            snapshot = b"".join(line[:60] + b" 99.00" + line[66:] if line[12:16].strip() == b"O2'" else line
                                for line in snapshot.splitlines(keepends=True))
        parents["A:1"].write_bytes(snapshot)
        rows = []
        for line in seed.read_text().splitlines(keepends=True):
            if line.startswith("ATOM") and line[21] == "A":
                x, y, z = (float(line[i:i+8]) for i in (30, 38, 46))
                line = (line[:17] + "RXG" + line[20:30] + "".join(f"{v:8.3f}" for v in (7-y, x, 9+z))
                        + line[54:60] + " 20.00" + line[66:])
            rows.append(line)
        raw.write_text("".join(rows))
        return raw, directory / "coot.log"

    monkeypatch.setattr("nasolve.postmr._run_coot", coot)
    kwargs = dict(coot_executable=tmp_path / "coot", inherit_scaffold_b=True,
                  canonical_seed_dictionaries={"A:1": (SOURCE, TEMPLATE)})
    if changed_parent:
        with pytest.raises(ValueError, match="frozen canonical ribose"):
            construct_postmr_model(model, (action,), {"RXG": target}, output, **kwargs)
        assert not output.exists()
        return
    result = construct_postmr_model(model, (action,), {"RXG": target}, output, **kwargs)
    proof = result["coordinate_restoration"]["A:1"]
    assert proof["host_displacement"]["source"] == "VERIFIED_CANONICAL_RIBOSE_INPUT"
    assert proof["host_displacement"]["status"] == "TRANSFERRED"
    seed = selected(result["canonical_parent_input"]["model"].read_bytes(), "G")
    atoms = selected(output.read_bytes(), "RXG")
    for n in proof["scaffold_atoms"]:
        assert atoms[n]["xyz"] == seed[n]["xyz"]
        assert atoms[n]["line"][54:66] == seed[n]["line"][54:66]
    assert atoms["N9"]["line"][60:66] == " 20.00"
    assert model.read_bytes() == frame()


@pytest.mark.parametrize("defect", ("charge", "ether", "wrong_marker", "missing_parent_oxygen",
                                    "inverted_raw_oxygen", "inverted_parent_oxygen"))
def test_unproven_ribose_cannot_authorize_coordinate_or_phosphate_edits(tmp_path, defect):
    target = local_component(tmp_path, defect)
    raw, parent = placed_models()
    if defect == "missing_parent_oxygen":
        parent = [line for line in parent if line[12:16].strip() != "O2'"]
    elif defect.startswith("inverted_"):
        rows = raw if defect == "inverted_raw_oxygen" else parent
        atoms = _atom_records(rows, "RXG" if rows is raw else "G")
        c2, oxygen = (atoms[n]["xyz"] for n in ("C2'", "O2'"))
        index = next(i for i, line in enumerate(rows) if line[12:16].strip() == "O2'")
        rows[index] = rows[index][:30] + "".join(f"{2*c-v:8.3f}" for c, v in zip(c2, oxygen)) + rows[index][54:]
    with pytest.raises(ValueError):
        restore_graph_site(raw, parent, target, "RXG", "G", ribose_template=TEMPLATE)
