"""PostMR -> checkpoint/view dictionary integration; external tools are fixtures."""
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from nasolve.checkpoints import CheckpointError, _initial_restraints
from nasolve.coot_view import _postmr_dictionaries
from nasolve.curated_ligands import ligand_definition, ligand_dictionary
from nasolve.ligand_profiles import _blocks
from nasolve.postmr import prepare_postmr
from .helpers import make_postmr_report
from .test_phosphate import phosphate, without_extra

ROOT = Path(__file__).parents[1]
DZ = ROOT / "src/nasolve/data/ligands/DZ.cif"


def test_dz_production_resource_and_intermediate_are_available():
    definition = ligand_definition("DZ")
    assert definition.parent_code == "DC"
    assert definition.code == definition.narestraints_label == "DZ"
    assert ligand_dictionary("DZ").read_bytes() == DZ.read_bytes()


def test_readyset_cannot_reintroduce_conflicting_dz_into_checkpoint_or_view(tmp_path, monkeypatch):
    # Use the established synthetic internal-phosphate fixture, not a real
    # crystallographic model. This tests artifact wiring, not chemical geometry.
    original = tmp_path / "original.pdb"
    original.write_text("".join(without_extra(phosphate())).replace("1AP", " DZ"))
    run = tmp_path / "dataset/AutoMR/run_001"
    report_path = make_postmr_report(run, original)
    report = json.loads(report_path.read_text())
    report["frame"] = None
    report["post_mr_plan"] = {"sequences": {}, "standard_pair": None, "mutations": {}}
    report_path.write_text(json.dumps(report))
    original_bytes = original.read_bytes()

    def readyset(command, cwd, **kwargs):
        prepared = Path(command[1])
        (cwd / "prepared_model.updated.pdb").write_text(prepared.read_text())
        # Deliberately return the raw competing C2e/C3e rows.
        (cwd / "prepared_model.ligands.cif").write_bytes(DZ.read_bytes())
        return SimpleNamespace(returncode=0, stdout="mocked ReadySet")

    def no_pairs(prepared, compatibility, pair_file, output):
        pair_file.write_text("")
        return {"retained_pair_count": 0, "retained_pairs": [], "modified_sites": ["A:12"]}

    monkeypatch.setattr("nasolve.postmr.subprocess.run", readyset)
    result = prepare_postmr(run, tmp_path / "ready_set", modified_pairs_only=True,
                            modified_pair_builder=no_pairs)
    assert result.status == "POSTMR_READY"
    assert original.read_bytes() == original_bytes
    prepared = json.loads(result.report_path.read_text())
    selected = _initial_restraints(prepared, run)
    names = {path.name for path in selected}
    assert {"DZ.cif", "linked_phosphate.cif", "linked_phosphate.phil"} <= names
    assert "prepared_model.ligands.cif" not in names
    assert prepared["linked_phosphate_profile"]["profile_codes"] == ["1AP", "DZ"]
    assert len(prepared["linked_phosphate_profile"]["modifications"]) == 1
    audit = prepared["dictionary_compatibility"]["input_adaptations"]
    assert any(event["status"] == "ADAPTED" for record in audit for event in record["events"])
    for record in audit:
        assert record["source"]["anchor"] == record["output"]["anchor"] == "run"
    source_copy = run / "PostMR/Restraints/source_dictionaries/DZ.cif"
    assert source_copy.read_bytes() == DZ.read_bytes()
    generated = run / "PostMR/ReadySet/prepared_model.ligands.cif"
    assert generated.read_bytes() == DZ.read_bytes()
    assert "C3e-nyu0" in generated.read_text()
    runtime = next(path for path in selected if path.name == "DZ.cif")
    component = next(block.values for block in _blocks(runtime)
                     if block.values.get("_chem_comp_atom.comp_id"))
    assert "C3e-nyu0" not in component["_chem_comp_tor.id"]
    assert "2.8" in component["_chem_comp_tor.alt_value_angle"]
    assert _postmr_dictionaries(run, {"postmr": prepared}) == (runtime,)

    # Normal portable references survive removal of the original fixture path.
    moved_dataset = tmp_path / "moved_dataset"
    shutil.copytree(run.parents[1], moved_dataset)
    shutil.rmtree(run.parents[1])
    moved_run = moved_dataset / "AutoMR/run_001"
    selected = _initial_restraints(prepared, moved_run)
    moved_cif = next(path for path in selected if path.name == "DZ.cif")
    assert moved_cif.is_relative_to(moved_run)
    assert _postmr_dictionaries(moved_run, {"postmr": prepared}) == (moved_cif,)
    moved_cif.write_text("corrupted")
    with pytest.raises(CheckpointError):
        _initial_restraints(prepared, moved_run)
