"""Content-based dictionary conversion and effective-input authority.

No Phenix execution is claimed by these offline representation tests.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from nasolve.dictionary_compatibility import normalize_torsion_block
from nasolve.ligand_profiles import (
    _blocks, _emit, dictionary_component_codes, effective_restraints,
    normalize_ccp4_torsion_alternates, validate_dz_dictionary,
)

ROOT = Path(__file__).parents[1]
DZ = ROOT / "src/nasolve/data/ligands/DZ.cif"
PREFIX = "_chem_comp_tor."
FIELDS = ["comp_id", "id", "atom_id_1", "atom_id_2", "atom_id_3", "atom_id_4",
          "value_angle", "value_angle_esd", "period", "alt_value_angle"]


def torsions(code="DZ", *, reverse=False, sigma="6.100", period="1", alt="."):
    atoms = ["C4'", "O4'", "C1'", "C2'"]
    rows = [
        [code, "C2e-nyu0", *atoms, "340.700", "6.300", "1", alt],
        [code, "C3e-nyu0", *(atoms[::-1] if reverse else atoms), "2.8", sigma, period, "."],
    ]
    return {"data_": "comp_" + code, **{
        PREFIX + field: [row[i] for row in rows]
        for i, field in enumerate(FIELDS)
    }}


@pytest.mark.parametrize("code", ["DZ", "1AP", "DP", "XYZ"])
@pytest.mark.parametrize("reverse", [False, True])
def test_content_not_residue_name_selects_supported_alternatives(code, reverse):
    source = torsions(code, reverse=reverse)
    before = deepcopy(source)
    source["_chem_comp_bond.value_dist"] = ["1.5"]
    source["_chem_comp_plane_atom.atom_id"] = ["N9"]
    before = deepcopy(source)
    output, events = normalize_torsion_block(source)
    assert source == before
    assert output[PREFIX + "value_angle"] == ["340.700"]
    assert output[PREFIX + "alt_value_angle"] == ["2.8"]
    assert output[PREFIX + "value_angle_esd"] == ["6.300"]
    assert output["_chem_comp_bond.value_dist"] == ["1.5"]
    assert output["_chem_comp_plane_atom.atom_id"] == ["N9"]
    assert events[0]["source_uncertainties_differ"] is True
    assert events[0]["source_rows"][1]["value_angle_esd"] == "6.100"
    assert events[0]["uncertainty_policy"] == "retain-primary-row-as-in-cctbx-conversion"
    assert normalize_torsion_block(output)[0] == output


def test_existing_alternates_are_retained_and_deduplicated():
    source = torsions(alt="2.8, 35.9, 700.7")
    output, _ = normalize_torsion_block(source)
    assert output[PREFIX + "alt_value_angle"] == ["2.8,35.9"]


def test_components_with_identical_atom_names_are_not_combined():
    source = torsions()
    source[PREFIX + "comp_id"][1] = "OTHER"
    output, events = normalize_torsion_block(source)
    assert output == source
    assert not events


def test_arbitrary_permutation_is_not_a_dihedral_reversal():
    source = torsions()
    source[PREFIX + "atom_id_2"][1], source[PREFIX + "atom_id_3"][1] = (
        source[PREFIX + "atom_id_3"][1], source[PREFIX + "atom_id_2"][1])
    output, _ = normalize_torsion_block(source)
    assert output == source


@pytest.mark.parametrize("kind", ["period", "sigma", "unknown", "extra", "nan"])
def test_unclassified_conflicts_warn_and_reach_native_interpretation(kind):
    source = torsions()
    if kind == "period": source[PREFIX + "period"][1] = "3"
    if kind == "sigma": source[PREFIX + "value_angle_esd"][1] = "0"
    if kind == "unknown": source[PREFIX + "id"] = ["alpha", "beta"]
    if kind == "extra": source[PREFIX + "unsupported"] = ["A", "B"]
    if kind == "nan": source[PREFIX + "value_angle"][1] = "nan"
    output, events = normalize_torsion_block(source)
    assert output == source
    assert events[0]["status"] == "WARNING"
    assert events[0]["action"] == "retained-for-native-interpretation"


def test_equal_rows_can_be_deduplicated_without_changing_the_target():
    source = torsions()
    source[PREFIX + "id"] = ["alpha", "copy"]
    source[PREFIX + "value_angle"] = ["0", "360"]
    source[PREFIX + "value_angle_esd"] = ["5", "5"]
    output, events = normalize_torsion_block(source)
    assert output[PREFIX + "value_angle"] == ["0"]
    assert output[PREFIX + "alt_value_angle"] == ["."]
    assert events[0]["status"] == "ADAPTED"


@pytest.mark.parametrize("bad", [1, [], ["0"]])
def test_incomplete_layout_is_retained_with_a_warning(bad):
    source = torsions()
    source[PREFIX + "value_angle"] = bad
    output, events = normalize_torsion_block(source)
    assert output == source
    assert events[0]["status"] == "WARNING"


def test_runtime_file_is_exclusive_and_preserves_source_bytes(tmp_path):
    source = tmp_path / "source.cif"
    source.write_text(_emit(torsions()))
    before = source.read_bytes()
    output = tmp_path / "runtime.cif"
    audit = []
    assert normalize_ccp4_torsion_alternates(source, output, audit=audit)
    assert source.read_bytes() == before
    assert audit[0]["source_sha256"] == hashlib.sha256(before).hexdigest()
    assert audit[0]["output_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        normalize_ccp4_torsion_alternates(source, output)
    second = tmp_path / "again.cif"
    assert not normalize_ccp4_torsion_alternates(output, second)
    assert second.read_bytes() == output.read_bytes()


def test_non_torsion_dictionary_is_byte_preserved(tmp_path):
    source = tmp_path / "plain.cif"
    source.write_text("# significant provenance comment\ndata_X\n_chem_comp.id X\n")
    output = tmp_path / "out.cif"
    assert not normalize_ccp4_torsion_alternates(source, output)
    assert output.read_bytes() == source.read_bytes()


def test_parameterized_dz_source_is_pinned_except_declared_group_adaptation():
    raw = DZ.read_text()
    body = raw[raw.index("data_comp_list"):]
    restored = body.replace(' DNA 35 23 .', ' NON-POLYMER 35 23 .')
    payload = restored.encode()
    assert hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest() == (
        "9e6151658d2887ef3902d170c77752ccc90159d4")
    validate_dz_dictionary(DZ)
    assert dictionary_component_codes(DZ) == {"DZ"}
    provenance = json.loads(DZ.with_suffix(".provenance.json").read_text())
    assert provenance["source_sha256"] == hashlib.sha256(payload).hexdigest()
    assert provenance["packaged_sha256"] == hashlib.sha256(DZ.read_bytes()).hexdigest()


def test_dz_has_four_supported_pucker_alternatives_without_changing_other_geometry(tmp_path):
    output = tmp_path / "DZ.cif"
    audit = []
    assert normalize_ccp4_torsion_alternates(DZ, output, audit=audit)
    source_blocks = _blocks(DZ)
    target_blocks = _blocks(output)
    assert len(source_blocks) == len(target_blocks)
    for source, target in zip(source_blocks, target_blocks):
        for key, values in source.values.items():
            if not key.startswith(PREFIX):
                assert target.values[key] == values
    events = [e for e in audit[0]["events"] if e["status"] == "ADAPTED"]
    assert len(events) == 4
    assert all(e["source_uncertainties_differ"] for e in events)
    validate_dz_dictionary(output)


@pytest.mark.parametrize("defect", ["group", "parameters", "glycoside", "plane"])
def test_dz_does_not_masquerade_as_an_unparameterized_or_different_component(tmp_path, defect):
    text = DZ.read_text()
    if defect == "group": text = text.replace(' DNA 35 23 .', ' NON-POLYMER 35 23 .')
    if defect == "parameters": text = text.replace('_chem_comp_bond.value_dist\n', '_chem_comp_bond.unknown_dist\n')
    if defect == "glycoside": text = text.replace('DZ C1     C CR6', 'DZ C1     N CR6')
    if defect == "plane": text = text.replace('DZ plan-1 C1    0.020', 'DZ plan-1 OTHER 0.020')
    path = tmp_path / "bad.cif"
    path.write_text(text)
    with pytest.raises(ValueError):
        validate_dz_dictionary(path)


def component_text(code="XYZ", *, parameterized=True, with_torsions=False):
    v = {"data_": "comp_" + code,
        "_chem_comp.id": [code],
        "_chem_comp_atom.comp_id": [code, code],
        "_chem_comp_atom.atom_id": ["X", "Y"],
        "_chem_comp_atom.type_energy": ["C", "N"],
        "_chem_comp_bond.comp_id": [code],
        "_chem_comp_bond.atom_id_1": ["X"],
        "_chem_comp_bond.atom_id_2": ["Y"]}
    if parameterized:
        v.update({"_chem_comp_bond.value_dist": ["1.4"],
                  "_chem_comp_bond.value_dist_esd": ["0.02"]})
    if with_torsions:
        v.update({k: val for k, val in torsions(code).items() if k != "data_"})
    return _emit(v)


def test_normalized_input_cannot_be_overridden_by_readyset_raw_dz(tmp_path):
    raw = tmp_path / "source.cif"
    raw.write_bytes(DZ.read_bytes())
    source = tmp_path / "arbitrary_filename.cif"
    normalize_ccp4_torsion_alternates(raw, source)
    generated = tmp_path / "generated.cif"
    generated.write_text(DZ.read_text() + "\n" + component_text("OTHER"))
    generated_before = generated.read_bytes()
    pair = tmp_path / "pairs.phil"
    pair.write_text("geometry_restraints.edits {}\n")
    mod = tmp_path / "modification.cif"
    mod.write_text("data_mod\n_chem_mod_atom.mod_id NASnoOP3\n")
    directory = tmp_path / "bundle"
    directory.mkdir()
    audit = []
    effective, viewing = effective_restraints(
        [pair, mod, source], generated, directory, normalize_effective=True,
        prefer_parameterized_inputs=True, audit=audit)
    assert source in effective
    assert generated not in effective
    assert mod in effective and mod not in viewing
    assert pair in effective
    counts = [dictionary_component_codes(p) for p in viewing]
    assert sum("DZ" in ids for ids in counts) == 1
    assert sum("OTHER" in ids for ids in counts) == 1
    assert generated.read_bytes() == generated_before
    assert all(e["status"] != "WARNING" for record in audit for e in record["events"])


def test_readyset_only_component_is_normalized_without_a_registry_entry(tmp_path):
    generated = tmp_path / "generated.cif"
    generated.write_text(component_text("XYZ", with_torsions=True))
    original = generated.read_bytes()
    effective, _ = effective_restraints(
        [], generated, tmp_path, normalize_effective=True,
        prefer_parameterized_inputs=True)
    assert len(effective) == 1
    assert generated.read_bytes() == original
    assert "2.8" in _blocks(effective[0])[0].values[PREFIX + "alt_value_angle"]


def test_raw_ccd_graph_still_defers_to_readyset_parameterization(tmp_path):
    raw = tmp_path / "XYZ.cif"
    raw.write_text(component_text(parameterized=False))
    generated = tmp_path / "generated.cif"
    generated.write_text(component_text(parameterized=True))
    effective, _ = effective_restraints(
        [raw], generated, tmp_path, normalize_effective=True,
        prefer_parameterized_inputs=True)
    assert raw not in effective
    assert len(effective) == 1
    assert _blocks(effective[0])[0].values["_chem_comp_bond.value_dist"] == ["1.4"]


def test_absent_generated_dictionary_retains_the_explicit_input(tmp_path):
    source = tmp_path / "input.cif"
    source.write_text(component_text())
    effective, _ = effective_restraints([source], None, tmp_path,
        normalize_effective=True, prefer_parameterized_inputs=True)
    assert effective == [source]


def test_multiple_input_components_keep_only_their_chosen_definitions(tmp_path):
    source = tmp_path / "both.cif"
    source.write_text(component_text("ONE", parameterized=False) + "\n" + component_text("TWO"))
    generated = tmp_path / "generated.cif"
    generated.write_text(component_text("ONE"))
    effective, _ = effective_restraints([source], generated, tmp_path,
        normalize_effective=True, prefer_parameterized_inputs=True)
    ids = [dictionary_component_codes(p) for p in effective]
    assert sum("ONE" in v for v in ids) == 1
    assert sum("TWO" in v for v in ids) == 1


def test_legacy_profile_scope_does_not_expand_when_dz_is_added(tmp_path, monkeypatch):
    import nasolve.ligand_profiles as profiles
    model = tmp_path / "model.pdb"
    model.write_text("END\n")
    monkeypatch.setattr(profiles, "_profile_inventory", lambda model, codes=profiles.AUTHORITATIVE_CODES:
        {"B:4": "DZ"} if "DZ" in codes else {})
    monkeypatch.setattr(profiles, "audit_phosphates", lambda *a, **k: {"checked": []})
    old = {"postmr": {"linked_phosphate_profile": {
        "schema_version": 1, "inventory": {}, "modifications": []}}}
    profiles.validate_model_phosphate_policy(model, old)
    new = deepcopy(old)
    new["postmr"]["linked_phosphate_profile"].update({
        "profile_codes": ["1AP", "DZ"], "inventory": {"B:4": "DZ"}})
    profiles.validate_model_phosphate_policy(model, new)
    new["postmr"]["linked_phosphate_profile"]["inventory"] = {}
    with pytest.raises(profiles.PhosphateError):
        profiles.validate_model_phosphate_policy(model, new)
