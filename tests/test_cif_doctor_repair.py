"""Bounded derivative preparation; these tests do not execute native Phenix."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from nasolve import cif_doctor_repair as repair
from nasolve.ligand_profiles import _blocks, _emit, normalize_ccp4_torsion_alternates


ROOT = Path(__file__).parents[1]
DZ = ROOT / "src/nasolve/data/ligands/DZ.cif"
FIVE_CM = ROOT / "src/nasolve/data/ligands/5CM.cif"
TOR = "_chem_comp_tor."


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_five_cm(tmp_path, monkeypatch):
    """Synthetic reference-edit test, not the historical scientific fixture."""
    atoms = ["C4'", "O4'", "C1'", "C2'", "C2"]
    fields = ("comp_id", "id", "atom_id_1", "atom_id_2", "atom_id_3",
              "atom_id_4", "value_angle", "value_angle_esd", "period")
    rows = [
        ["5CM", "C2e-nyu0", "C4'", "O4'", "C1'", "C2", "340.700", "6.300", "1"],
        ["5CM", "C3e-nyu0", "C4'", "O4'", "C1'", "C2'", "2.8", "6.100", "1"],
    ]
    values = {
        "data_": "comp_5CM",
        "_chem_comp_atom.comp_id": ["5CM"] * len(atoms),
        "_chem_comp_atom.atom_id": atoms,
        "_chem_comp_atom.type_symbol": ["C", "O", "C", "C", "C"],
        "_chem_comp_bond.comp_id": ["5CM"] * 3,
        "_chem_comp_bond.atom_id_1": atoms[:3],
        "_chem_comp_bond.atom_id_2": atoms[1:4],
        "_chem_comp_bond.type": ["single"] * 3,
        **{TOR + field: [row[i] for row in rows] for i, field in enumerate(fields)},
    }
    source = tmp_path / "synthetic_5CM.cif"
    source.write_text(_emit(values), encoding="utf-8")
    reviewed = deepcopy(values)
    reviewed[TOR + "atom_id_4"][0] = "C2'"
    intermediate = tmp_path / "synthetic_expected_intermediate.cif"
    intermediate.write_text(_emit(reviewed), encoding="utf-8")
    expected = tmp_path / "synthetic_expected.cif"
    normalize_ccp4_torsion_alternates(intermediate, expected)
    monkeypatch.setattr(repair, "REVIEWED_5CM_SOURCE_SHA256", digest(source))
    monkeypatch.setattr(repair, "REVIEWED_5CM_CANDIDATE_SHA256", digest(expected))
    return source, expected


def test_alternates_receipt_preserves_source_and_other_categories(tmp_path):
    source = tmp_path / "supplier.cif"
    source.write_bytes(DZ.read_bytes())
    before = source.read_bytes()
    output = tmp_path / "prepared.cif"
    receipt = repair.prepare_dictionary(source, output, recipe="torsion-alternates-v1")
    assert source.read_bytes() == before
    assert receipt["source_preserved"] is True
    assert receipt["source"]["sha256"] == hashlib.sha256(before).hexdigest()
    assert receipt["output"]["sha256"] == digest(output)
    assert receipt["changed"] is True
    assert receipt["automatic_adoption"] is False
    assert receipt["native_validation"]["status"] == "NOT_RUN"
    assert receipt["before_assessment"]["inputs"][0]["sha256"] == digest(source)
    assert receipt["after_assessment"]["inputs"][0]["sha256"] == digest(output)
    assert any(event["status"] == "ADAPTED" for event in receipt["events"])
    for before_block, after_block in zip(_blocks(source), _blocks(output)):
        assert {key: value for key, value in before_block.values.items()
                if not key.startswith(TOR)} == {
                    key: value for key, value in after_block.values.items()
                    if not key.startswith(TOR)}


def test_noop_preserves_exact_bytes_including_crlf(tmp_path):
    source = tmp_path / "plain.cif"
    original = b"# supplier comment\r\ndata_plain\r\n_chem_comp.id PLAIN\r\n"
    source.write_bytes(original)
    output = tmp_path / "prepared.cif"
    receipt = repair.prepare_dictionary(source, output, recipe="torsion-alternates-v1")
    assert source.read_bytes() == output.read_bytes() == original
    assert receipt["changed"] is False
    assert receipt["changes"] == []


def test_reviewed_reference_recipe_is_strictly_source_hash_scoped(tmp_path):
    output = tmp_path / "prepared.cif"
    with pytest.raises(repair.CIFPreparationError, match="source SHA-256"):
        repair.prepare_dictionary(FIVE_CM, output, recipe="5cm-reviewed-torsion-v1")
    assert not output.exists()
    assert repair.REVIEWED_5CM_SOURCE_SHA256 == (
        "38378c7df4eef73a0bd2be40059b2c3dd2b98618a4eeb7e91f6ec3427f7e7858")


def test_synthetic_reviewed_reference_edit_then_existing_alternate_adapter(tmp_path, monkeypatch):
    source, expected = synthetic_five_cm(tmp_path, monkeypatch)
    before = source.read_bytes()
    output = tmp_path / "prepared.cif"
    receipt = repair.prepare_dictionary(source, output, recipe="5cm-reviewed-torsion-v1")
    assert source.read_bytes() == before
    assert output.read_bytes() == expected.read_bytes()
    values = _blocks(output)[0].values
    assert values[TOR + "atom_id_4"] == ["C2'"]
    assert values[TOR + "value_angle"] == ["340.700"]
    assert values[TOR + "alt_value_angle"] == ["2.8"]
    assert values[TOR + "value_angle_esd"] == ["6.300"]
    edits = [event for event in receipt["events"] if event.get("action") == "reviewed-atom-reference"]
    assert len(edits) == 1
    assert edits[0]["before"] == "C2"
    assert edits[0]["after"] == "C2'"


def test_reviewed_candidate_hash_mismatch_blocks_publication(tmp_path, monkeypatch):
    source, _ = synthetic_five_cm(tmp_path, monkeypatch)
    monkeypatch.setattr(repair, "REVIEWED_5CM_CANDIDATE_SHA256", "0" * 64)
    output = tmp_path / "prepared.cif"
    with pytest.raises(repair.CIFPreparationError, match="candidate SHA-256"):
        repair.prepare_dictionary(source, output, recipe="5cm-reviewed-torsion-v1")
    assert not output.exists()


@pytest.mark.parametrize("target_kind", ["existing", "source", "symlink"])
def test_never_overwrites_target_or_source(tmp_path, target_kind):
    source = tmp_path / "source.cif"
    source.write_bytes(DZ.read_bytes())
    original = source.read_bytes()
    target = tmp_path / "target.cif"
    if target_kind == "existing":
        target.write_bytes(b"existing result")
    elif target_kind == "source":
        target = source
    else:
        target.symlink_to(source)
    with pytest.raises((FileExistsError, repair.CIFPreparationError)):
        repair.prepare_dictionary(source, target, recipe="torsion-alternates-v1")
    assert source.read_bytes() == original
    if target_kind == "existing":
        assert target.read_bytes() == b"existing result"


def test_unknown_recipe_does_not_create_output(tmp_path):
    output = tmp_path / "prepared.cif"
    with pytest.raises(repair.CIFPreparationError, match="Unknown"):
        repair.prepare_dictionary(DZ, output, recipe="fix-all-bond-orders")
    assert not output.exists()


def test_allowlist_rejects_unrelated_atom_or_bond_mutation(tmp_path, monkeypatch):
    original_normalizer = repair.normalize_ccp4_torsion_alternates

    def tampered_normalizer(source, output, **kwargs):
        changed = original_normalizer(source, output, **kwargs)
        blocks = _blocks(output)
        atom_block = next(block for block in blocks if "_chem_comp_atom.atom_id" in block.values)
        atom_block.values["_chem_comp_atom.type_symbol"][0] = "I"
        output.write_text("\n".join(_emit(block.values) for block in blocks), encoding="utf-8")
        return changed

    monkeypatch.setattr(repair, "normalize_ccp4_torsion_alternates", tampered_normalizer)
    output = tmp_path / "prepared.cif"
    with pytest.raises(repair.CIFPreparationError, match="allowlist"):
        repair.prepare_dictionary(DZ, output, recipe="torsion-alternates-v1")
    assert not output.exists()


def test_source_change_during_preparation_blocks_publication(tmp_path, monkeypatch):
    source = tmp_path / "source.cif"
    source.write_bytes(DZ.read_bytes())
    original_normalizer = repair.normalize_ccp4_torsion_alternates

    def source_changing_normalizer(snapshot, output, **kwargs):
        changed = original_normalizer(snapshot, output, **kwargs)
        source.write_bytes(source.read_bytes() + b"# concurrent supplier update\n")
        return changed

    monkeypatch.setattr(repair, "normalize_ccp4_torsion_alternates", source_changing_normalizer)
    output = tmp_path / "prepared.cif"
    with pytest.raises(repair.CIFPreparationError, match="Source changed"):
        repair.prepare_dictionary(source, output, recipe="torsion-alternates-v1")
    assert not output.exists()


def test_unknown_competing_torsions_remain_visible_and_unchanged(tmp_path):
    values = {"data_": "comp_X"}
    fields = ("comp_id", "id", "atom_id_1", "atom_id_2", "atom_id_3", "atom_id_4",
              "value_angle", "value_angle_esd", "period")
    rows = [["X", "unknown1", "A", "B", "C", "D", "0", "4", "1"],
            ["X", "unknown2", "A", "B", "C", "D", "90", "4", "1"]]
    values.update({TOR + field: [row[i] for row in rows] for i, field in enumerate(fields)})
    source = tmp_path / "unknown.cif"
    source.write_text(_emit(values), encoding="utf-8")
    output = tmp_path / "prepared.cif"
    receipt = repair.prepare_dictionary(source, output, recipe="torsion-alternates-v1")
    assert output.read_bytes() == source.read_bytes()
    assert receipt["events"][0]["status"] == "WARNING"
    assert receipt["automatic_adoption"] is False


def test_prepared_invalid_inventory_is_explicitly_blocked_from_adoption(tmp_path):
    source = tmp_path / "duplicate_atoms.cif"
    source.write_text(_emit({
        "data_": "comp_X",
        "_chem_comp_atom.comp_id": ["X", "X"],
        "_chem_comp_atom.atom_id": ["C1", "C1"],
        "_chem_comp_atom.type_symbol": ["C", "C"],
    }), encoding="utf-8")
    output = tmp_path / "prepared.cif"
    receipt = repair.prepare_dictionary(source, output, recipe="torsion-alternates-v1")
    assert output.read_bytes() == source.read_bytes()
    assert receipt["after_assessment"]["status"] == "INVALID"
    assert receipt["adoption_status"] == "BLOCKED"
    assert receipt["automatic_adoption"] is False
