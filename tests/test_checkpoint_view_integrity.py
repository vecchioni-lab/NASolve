"""Viewing a checkpoint must not hide damage to its recorded restraints."""
import json
import shutil
from pathlib import Path
import pytest
from tests.test_coot_view import make_view_run, add_review_checkpoint
from nasolve.coot_view import CootViewError, resolve_view_profile
from nasolve.model_assessment import file_sha256
from nasolve.run_context import artifact_reference


def setup(root, schema):
    run = make_view_run(root)
    path = run / "AutoRefine/checkpoints.json"
    registry = json.loads(path.read_text())
    item = registry["checkpoints"][0]
    phil = run / "PostMR/pairs.phil"
    phil.write_text("geometry_restraints.edits {}\n")
    dictionary = Path(item["restraints"][0]["path"])
    def ref(p):
        return {**artifact_reference(p, run), "sha256": file_sha256(p)}
    item["model"] = ref(Path(item["model"]["path"]))
    item["outputs"]["map_coefficients"] = ref(Path(item["outputs"]["map_coefficients"]))
    item["restraints"] = [ref(dictionary), ref(phil), ref(dictionary)]
    registry["schema_version"] = schema
    path.write_text(json.dumps(registry))
    return run, phil, dictionary


def inventory(run):
    return {str(p.relative_to(run)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in run.rglob("*") if p.is_file()}


@pytest.mark.parametrize("schema", [1, 2])
@pytest.mark.parametrize("damage", ["missing", "changed", "directory"])
def test_non_display_restraint_damage_blocks_view_without_writes(tmp_path, schema, damage):
    run, phil, _ = setup(tmp_path, schema)
    if damage == "changed":
        phil.write_text("changed base-pair restraints\n")
    else:
        phil.unlink()
        if damage == "directory": phil.mkdir()
    before = inventory(run)
    with pytest.raises(CootViewError, match="restraint"):
        resolve_view_profile(run, checkpoint="refine-001")
    assert inventory(run) == before


@pytest.mark.parametrize("malformed", ["not a list", {}, [None]])
def test_malformed_recorded_restraint_list_is_not_an_empty_display(tmp_path, malformed):
    run, _, _ = setup(tmp_path, 1)
    p = run / "AutoRefine/checkpoints.json"
    data = json.loads(p.read_text()); data["checkpoints"][0]["restraints"] = malformed
    p.write_text(json.dumps(data))
    with pytest.raises(CootViewError, match="restraint"):
        resolve_view_profile(run, checkpoint="refine-001")


def test_relocated_exact_checkpoint_preserves_order_without_following_latest(tmp_path):
    original, phil, dictionary = setup(tmp_path / "original", 2)
    add_review_checkpoint(original)
    registry_path = original / "AutoRefine/checkpoints.json"
    registry = json.loads(registry_path.read_text()); registry["current"] = "refine-002"
    registry_path.write_text(json.dumps(registry))
    moved = tmp_path / "moved run"
    shutil.move(str(original), moved)
    shutil.rmtree(tmp_path / "original")
    before = inventory(moved)
    view = resolve_view_profile(moved, checkpoint="refine-001")
    assert view.checkpoint_id == "refine-001"
    assert view.dictionary_paths == (moved / dictionary.relative_to(original),) * 2
    assert inventory(moved) == before


@pytest.mark.parametrize("changed", [False, True])
def test_modification_dictionary_is_verified_even_when_not_displayed(tmp_path, changed):
    from nasolve.ligand_profiles import MOD_CIF
    run, _, dictionary = setup(tmp_path, 2)
    modification = run / "PostMR/linked-phosphate.cif"
    modification.write_text(MOD_CIF)
    p = run / "AutoRefine/checkpoints.json"; data = json.loads(p.read_text())
    data["checkpoints"][0]["restraints"].append(
        {**artifact_reference(modification, run), "sha256": file_sha256(modification)})
    p.write_text(json.dumps(data))
    if changed:
        modification.write_text(MOD_CIF + "# changed\n")
        with pytest.raises(CootViewError, match="dictionary"):
            resolve_view_profile(run, checkpoint="refine-001")
    else:
        assert resolve_view_profile(run, checkpoint="refine-001").dictionary_paths == (dictionary, dictionary)
