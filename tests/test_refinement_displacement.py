import pytest

from tests.test_refinement_link_geometry import setup_files


def test_group_offsets_follow_atom_identity_and_keep_the_written_occupancies(tmp_path):
    from nasolve.refinement_displacement import compare_pdb_displacements
    model, _, _ = setup_files(tmp_path)
    atoms = model.read_text().splitlines()[:-1]
    before = atoms.copy()
    before[4] = atoms[4][:54] + "  0.50138.44" + atoms[4][66:]
    after = before.copy()
    after[4] = before[4][:54] + "  0.40295.55" + before[4][66:]
    after[5] = before[5][:60] + "187.11" + before[5][66:]
    result = compare_pdb_displacements("\n".join(before).encode(), "\n".join(reversed(after)).encode(), ["B:4"])
    site = result["sites"]["B:4"]
    assert site["status"] == "COMPARED" and site["component"] == "Z99"
    assert site["b_change_range_A2"] == [157.11, 157.11]
    assert site["changed_occupancies"] == 1
    atom = site["atoms"]["C5T"]
    assert atom["input"] == {"occupancy": .5, "b_A2": 138.44, "has_anisou": False}
    assert atom["selected"] == {"occupancy": .4, "b_A2": 295.55, "has_anisou": False}
    assert atom["element"] == "C" and atom["b_change_A2"] == 157.11


def test_selected_model_only_and_unsupported_site_fields_stay_distinct(tmp_path):
    from nasolve.refinement_displacement import compare_pdb_displacements
    model, _, _ = setup_files(tmp_path)
    lines = model.read_text().splitlines()
    anisou = "ANISOU" + lines[4][6:27] + " " + "   1000"*6 + "       C"
    data = "\n".join(lines[:-1] + [anisou, "END"]).encode()
    group = compare_pdb_displacements(None, data, ["B:4","A:8"])["sites"]
    assert group["B:4"]["status"] == "SELECTED_ONLY"
    assert group["B:4"]["atoms"]["C5T"]["selected"]["has_anisou"]
    assert group["A:8"]["status"] == "UNASSESSED"
    for index, bad in ((16, "B"), (60, "   nan"), (60, "      ")):
        edit = lines.copy()
        edit[4] = edit[4][:index] + bad + edit[4][index+len(bad):]
        partial = compare_pdb_displacements(data, "\n".join(edit).encode(), ["B:4","A:2"])["sites"]
        assert partial["B:4"]["status"] == "UNASSESSED" and partial["A:2"]["status"] == "COMPARED"
    renamed = [r.replace("Z99 B", "Z88 B") for r in lines]
    result = compare_pdb_displacements(data, "\n".join(renamed).encode(), ["B:4"])
    assert result["sites"]["B:4"]["status"] == "UNASSESSED"
    for changed in (lines[:-2], [r[:-2]+" N" if i==4 else r for i,r in enumerate(lines)]):
        result = compare_pdb_displacements(data, "\n".join(changed).encode(), ["B:4"])
        partial = result["sites"]["B:4"]
        assert partial["status"] == "PARTIAL" and partial["matched_atoms"] == 1
        assert partial["b_change_range_A2"] == [0, 0]
    with pytest.raises(ValueError, match="distinct"):
        compare_pdb_displacements(data, data, ["B:4", "B:4"])


def test_explicit_single_model_and_conflicting_ensembles(tmp_path):
    from nasolve.refinement_displacement import compare_pdb_displacements
    model, _, _ = setup_files(tmp_path)
    atoms = model.read_bytes().removesuffix(b"END\n")
    single = b"MODEL        1\n" + atoms + b"ENDMDL\n"
    assert compare_pdb_displacements(atoms, single, ["B:4"])["sites"]["B:4"]["status"] == "COMPARED"
    for data in (single + single, atoms + single, single + atoms, b"MODEL        1\n" + atoms, b"\xff"):
        site = compare_pdb_displacements(atoms, data, ["B:4"])["sites"]["B:4"]
        assert site["status"] == "UNASSESSED" and "single fixed-column" in site["reason"]
