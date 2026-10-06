"""Actual dictionary/parser regressions for DiU and the local 5CM resource."""
from pathlib import Path
import hashlib
import json
from math import dist

import pytest

from nasolve.curated_ligands import (
    dictionary_ideal_bond_length, ligand_definition, ligand_dictionary,
    validate_ligand_dictionary,
)
from nasolve.ligand_profiles import _blocks, normalize_ccp4_torsion_alternates
from nasolve.postmr import scan_anomalous_candidates
from nasolve.anomalous_expectations import audit_iodine_targets
from .helpers import pdb_record

ROOT = Path(__file__).parents[1]


def test_diu_actual_dictionary_uses_ring_c5_not_sugar_c5_prime():
    source = ligand_dictionary("5IU")
    before = source.read_bytes()
    distance = dictionary_ideal_bond_length(source, "C5", "I5")
    assert distance == pytest.approx(2.0951107369301507)
    assert dictionary_ideal_bond_length(source, "C5'", "I5") == pytest.approx(8.843030419488558)
    assert source.read_bytes() == before


@pytest.mark.parametrize("ring_first", [True, False])
@pytest.mark.parametrize("quote", ['"', ""])
def test_prime_names_survive_unquoting_and_atom_row_order(tmp_path, ring_first, quote):
    source = tmp_path / "component.cif"
    rows = ["ABC C5 C 0 0 0\n", f"ABC {quote}C5'{quote} C 9 0 0\n"]
    if not ring_first:
        rows.reverse()
    source.write_text("data_test\nloop_\n_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n"
        "_chem_comp_atom.type_symbol\n_chem_comp_atom.x\n_chem_comp_atom.y\n_chem_comp_atom.z\n"
        + "".join(rows) + "ABC I5 I 2 0 0\n#\n")
    assert dictionary_ideal_bond_length(source, "C5", "I5") == 2.0
    assert dictionary_ideal_bond_length(source, "C5'", "I5") == 7.0


def test_real_5cm_resource_is_unchanged_pinned_parameterized_library_data(tmp_path):
    source = ligand_dictionary("5CM")
    data = source.read_bytes()
    digest = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    assert digest == "a8a590f15f0b50c42ed9ad46d59eec3aab11d583"
    validate_ligand_dictionary("5CM", source)
    assert ligand_definition("5CM").parent_code == "DC"
    blocks = _blocks(source)
    atoms = next(v.values for v in blocks if "_chem_comp_atom.atom_id" in v.values)
    assert {"C5", "C5A", "C1'", "N1"} <= set(atoms["_chem_comp_atom.atom_id"])
    assert "_chem_comp_bond.value_dist" in atoms
    runtime = tmp_path / "runtime.cif"
    normalize_ccp4_torsion_alternates(source, runtime)
    assert runtime.is_file()
    assert source.read_bytes() == data


def test_installed_narestraints_knows_5cm_and_no_record_is_relabelled():
    from restraints.residue_library import load_residue_records
    rows = [r for r in load_residue_records() if str(r.get("Ligand code")) == "5CM"]
    assert len(rows) == 1
    record = rows[0]
    assert record["Sugar Type"].upper() == "DNA"
    assert record["Source sheet"].lower() == "cytosine"
    assert record["Base Analog"].upper() == "C"


def test_diu_final_iodine_is_in_the_actual_anomalous_selection(tmp_path):
    source = tmp_path / "model.pdb"
    source.write_text(
        pdb_record("HETATM", 1, "C1'", "5IU", "B", 4, element="C") +
        pdb_record("HETATM", 2, "C3'", "5IU", "B", 4, element="C") +
        pdb_record("HETATM", 3, "I5", "5IU", "B", 4, element="I") + "END\n")
    candidates = scan_anomalous_candidates(source)
    assert [(r["site"], r["atom_name"], r["element"]) for r in candidates] == [("B:4", "I5", "I")]
    assert audit_iodine_targets(source, candidates)["warnings"] == []
    from nasolve.autorefine import anomalous_selections
    assert anomalous_selections({"postmr":{"anomalous":{"candidates":candidates}}}) == ("chain B and resid 4 and name I5",)


def test_5cm_postmr_freezes_its_own_internal_phosphate_scope(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from nasolve.postmr import prepare_postmr
    from .test_linked_phosphate_profile import model
    from .helpers import make_postmr_report
    original = model(tmp_path, extra=True)
    original.write_text(original.read_text().replace("1AP", "5CM"))
    before = original.read_bytes()
    run = tmp_path / "dataset/AutoMR/run_001"
    report_path = make_postmr_report(run, original)
    report = json.loads(report_path.read_text())
    report["frame"] = None
    report["post_mr_plan"] = {"sequences": {}, "standard_pair": None, "mutations": {}}
    report_path.write_text(json.dumps(report))
    def readyset(command, cwd, **kwargs):
        prepared = Path(command[1])
        (cwd / "prepared_model.updated.pdb").write_bytes(prepared.read_bytes())
        (cwd / "prepared_model.ligands.cif").write_bytes(ligand_dictionary("5CM").read_bytes())
        return SimpleNamespace(returncode=0, stdout="fixture ReadySet")
    def no_pairs(prepared, compatibility, pairs, output):
        pairs.write_text("")
        return {"retained_pair_count": 0, "retained_pairs": [], "modified_sites": ["A:12"]}
    monkeypatch.setattr("nasolve.postmr.subprocess.run", readyset)
    result = prepare_postmr(run, tmp_path / "ready_set", modified_pairs_only=True, modified_pair_builder=no_pairs)
    prepared = json.loads(result.report_path.read_text())
    profile = prepared["linked_phosphate_profile"]
    assert "5CM" in profile["profile_codes"]
    assert profile["inventory"] == {"A:12": "5CM"}
    assert len(profile["modifications"]) == 1
    assert profile["modifications"][0]["residue"] == "5CM"
    assert "5CM" in prepared["dictionary_precedence"]["authoritative_codes"]
    assert original.read_bytes() == before
