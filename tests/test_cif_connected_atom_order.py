"""Atom ordering is a source-table permutation, never a chemistry repair."""
from copy import deepcopy
from itertools import permutations

import pytest

from nasolve.cif_linked_preparation import component_values, _render
from nasolve.ligand_profiles import _emit, _blocks
from tests.test_cif_stereochemistry_audit import tetrahedron, write


def prepare(source, output, code="Q17"):
    from nasolve.cif_connected_atom_order import prepare_connected_atom_order
    return prepare_connected_atom_order(source, code, output)


def permute(values, indices):
    return {k: [v[i] for i in indices] if k.lower().startswith("_chem_comp_atom.") else deepcopy(v)
            for k, v in values.items()}


def rows(values):
    names = values["_chem_comp_atom.atom_id"]
    return {n: {k: v[i] for k, v in values.items() if k.startswith("_chem_comp_atom.")}
            for i, n in enumerate(names)}


@pytest.mark.parametrize("legacy", [False, True])
def test_permutation_preserves_every_atom_field_and_nonatom_declaration(tmp_path, legacy):
    _, v = tetrahedron()
    v["_chem_comp_atom.custom_note"] = ["centre", "oxygen", "nitrogen", "carbon", "hydrogen"]
    v["_chem_comp_atom.charge"][2] = "1"
    v["_chem_comp_atom.pdbx_ordinal"] = ["17", "5", "42", "8", "1"]
    v["_chem_comp_bond.pdbx_stereo_config"] = ["N"] * 4
    source = tmp_path / "source.cif"
    source.write_text(_render(v, "Q17") if legacy else _emit(v))
    before = source.read_bytes(), source.stat().st_mtime_ns
    output = tmp_path / "output.cif"
    report = prepare(source, output)
    after = component_values(output, "Q17")
    assert rows(after) == rows(v)
    assert {k: x for k, x in after.items() if not k.startswith("_chem_comp_atom.")} == {
        k: x for k, x in component_values(source, "Q17").items() if not k.startswith("_chem_comp_atom.")}
    assert report["output_atom_order"] == ["C", "CTR", "N", "O", "H"]
    assert report["changed"] is True
    assert report["chemical_declarations"] == "PRESERVED"
    assert report["native_qualification"] == "NOT_RUN" and not report["automatic_adoption"]
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before
    if legacy:
        assert _blocks(source)[0].text == _blocks(output)[0].text
    second = tmp_path / "second.cif"
    assert prepare(output, second)["changed"] is False
    assert second.read_bytes() == output.read_bytes()


def test_all_input_permutations_have_same_heavy_traversal_and_exact_hydrogen_rows(tmp_path):
    v, _ = tetrahedron()
    v["_chem_comp_atom.type_symbol"][-1] = "D"
    expected = None
    for i, order in enumerate(permutations(range(5))):
        source = write(tmp_path / f"source-{i}.cif", permute(v, order))
        output = tmp_path / f"output-{i}.cif"
        report = prepare(source, output)
        result = component_values(output, "Q17")
        assert rows(result) == rows(v)
        assert expected is None or result == expected
        expected = result
        assert report["output_atom_order"][-1] == "H"


@pytest.mark.parametrize("defect", ["duplicate_atom", "ragged_atom", "duplicate_edge", "self_edge",
    "unknown_endpoint", "disconnected_heavy", "hydrogen_bridge", "hydrogen_pair", "case_alias",
    "second_component", "hidden_block", "wrong_code", "unknown_order"])
def test_ambiguous_or_unsupported_inputs_fail_before_creating_output(tmp_path, defect):
    v, _ = tetrahedron()
    a, b = "_chem_comp_atom.", "_chem_comp_bond."
    if defect == "duplicate_atom": v[a + "atom_id"][1] = "CTR"
    if defect == "ragged_atom": v[a + "custom"] = ["x"]
    if defect == "duplicate_edge": v[b + "atom_id_2"][1] = "O"
    if defect == "self_edge": v[b + "atom_id_2"][1] = "CTR"
    if defect == "unknown_endpoint": v[b + "atom_id_2"][1] = "MISSING"
    if defect == "disconnected_heavy":
        for k in list(v):
            if k.startswith(b): v[k] = v[k][1:]
    if defect == "hydrogen_bridge": v[a + "type_symbol"][0] = "H"
    if defect == "hydrogen_pair": v[a + "type_symbol"] = ["H"] * 5
    if defect == "case_alias": v[a + "ATOM_ID"] = list(v[a + "atom_id"])
    if defect == "unknown_order": v[b + "value_order"][0] = "?"
    source = tmp_path / "source.cif"
    # Render a ragged atom loop as a separate scalar field, which parsers retain.
    custom = v.pop(a + "custom", None)
    text = _emit(v)
    if custom: text += a + "custom x\n"
    if defect == "second_component": text += _emit(tetrahedron("ZZ9")[0])
    if defect == "hidden_block": text += "data_hidden\n_private.value opaque\n"
    source.write_text(text)
    output = tmp_path / "out.cif"
    with pytest.raises(ValueError): prepare(source, output, "BAD" if defect == "wrong_code" else "Q17")
    assert not output.exists()


@pytest.mark.parametrize("kind", ["existing", "source", "symlink", "symlink_parent"])
def test_output_ownership_prevents_overwrite_and_path_aliases(tmp_path, kind):
    source = write(tmp_path / "source.cif", tetrahedron()[0])
    output = tmp_path / "output.cif"
    if kind == "existing": output.write_text("owned by someone else")
    if kind == "source": output = source
    if kind == "symlink": output.symlink_to(source)
    if kind == "symlink_parent":
        (tmp_path / "real").mkdir(); (tmp_path / "alias").symlink_to(tmp_path / "real", target_is_directory=True)
        output = tmp_path / "alias/output.cif"
    before = source.read_bytes()
    with pytest.raises((ValueError, FileExistsError)): prepare(source, output)
    assert source.read_bytes() == before
    if kind == "existing": assert output.read_text() == "owned by someone else"


def test_seed_is_only_a_permutation_not_a_claim_of_native_graph_invariance(tmp_path):
    # Ring entered through R3, rather than its first lexical atom R1.
    a, b = "_chem_comp_atom.", "_chem_comp_bond."
    names = ["C", "R1", "R2", "R3", "LINK", "H"]
    v = {"data_": "Q17", "_chem_comp.id": ["Q17"], a + "comp_id": ["Q17"] * 6,
         a + "atom_id": names, a + "type_symbol": ["C"] * 5 + ["H"], a + "charge": ["0"] * 6,
         b + "comp_id": ["Q17"] * 6, b + "atom_id_1": ["C", "LINK", "R1", "R2", "R3", "C"],
         b + "atom_id_2": ["LINK", "R3", "R2", "R3", "R1", "H"], b + "value_order": ["SING"] * 6}
    source = write(tmp_path / "source.cif", v); out = tmp_path / "out.cif"
    result = prepare(source, out)
    assert result["output_atom_order"] == ["C", "LINK", "R3", "R1", "R2", "H"]
    assert rows(component_values(out, "Q17")) == rows(v)
    assert result["native_qualification"] == "NOT_RUN"
