"""P2 integration using the normal NASolve path and fixture ReadySet only."""
from copy import deepcopy
from hashlib import sha1
from math import dist
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from nasolve.component_normalization import (
    BASE_ELEMENTS, BACKBONE_ELEMENTS, normalize_model, validate_preferred_dictionary,
)
from nasolve.curated_ligands import ligand_dictionary, ligand_definition, validate_ligand_dictionary
from nasolve.ligand_profiles import _blocks, normalize_ccp4_torsion_alternates, LINKED_PROFILE_CODES
from nasolve.postmr import prepare_postmr, build_mutation_plan, PostMRPreparationError
from nasolve.run_context import resolve_artifact_path
from nasolve.autorefine import validate_refined_model
from nasolve.phosphate import PhosphateError, sanitize_phosphates
from .test_component_normalization import atom


def test_dp_resource_reconstructs_exact_pinned_supplier_bytes(tmp_path):
    path = ligand_dictionary("DP")
    raw = path.read_bytes().replace(b" DNA 35 23 .", b" NON-POLYMER 35 23 .", 1)
    assert sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == "50218f6ebd8ccaa5582c32286c675f466d8a6d0d"
    validate_ligand_dictionary("DP", path)
    assert ligand_definition("DP").parent_code == "DG"
    assert "DP" in LINKED_PROFILE_CODES
    runtime = tmp_path / "runtime.cif"
    normalize_ccp4_torsion_alternates(path, runtime)
    validate_preferred_dictionary("DP", runtime)


@pytest.mark.parametrize("target", ["DZ", "DP"])
def test_actual_target_matches_explicit_heavy_skeleton_and_carbonyl(target):
    validate_preferred_dictionary(target, ligand_dictionary(target))


@pytest.mark.parametrize("source,target,parent", [("1W5", "DZ", "DC"), ("1WA", "DP", "DG")])
def test_new_requests_normalize_without_rewriting_frozen_plan(tmp_path, monkeypatch, source, target, parent):
    import nasolve.postmr as postmr
    path = tmp_path / "m.pdb"
    path.write_text(atom(code="DC"))
    targets = {"A:12": source}
    report = {"inputs": {"mirror": False}, "post_mr_plan": {"mutations": {"A:12": {"ligand_code": source}}}}
    before = deepcopy(report)
    monkeypatch.setattr(postmr, "_target_sites", lambda *a, **kw: targets)
    action, = build_mutation_plan(report, path)
    assert (action.after, action.parent_code, action.method) == (target, parent, "coot-parent-overlap")
    assert report == before and targets == {"A:12": source}
    path.write_text(atom(code=source))
    action, = build_mutation_plan(report, path)
    assert (action.after, action.method) == (target, "component-normalization")


def test_mirrored_source_is_not_reinterpreted_with_a_d_sugar_dictionary(tmp_path, monkeypatch):
    import nasolve.postmr as postmr
    path = tmp_path / "m.pdb"; path.write_text(atom(code="1WA"))
    monkeypatch.setattr(postmr, "_target_sites", lambda *a, **kw: {"A:12": "1WA"})
    with pytest.raises(PostMRPreparationError, match="mirrored"):
        build_mutation_plan({"inputs": {"mirror": True}}, path)


def pdb_atom(serial, name, code, resid, xyz, element):
    return (f"HETATM{serial:5d} {name:>4} {code:>3} A{resid:4d}    "
            f"{xyz[0]:8.3f}{xyz[1]:8.3f}{xyz[2]:8.3f}{1.0:6.2f}{20.0:6.2f}"
            f"          {element:>2}\n")


def placed_source(source, target):
    values = next(b.values for b in _blocks(ligand_dictionary(target)) if "_chem_comp_atom.atom_id" in b.values)
    atoms = {}
    rows = []
    for name, element, x, y, z in zip(values["_chem_comp_atom.atom_id"], values["_chem_comp_atom.type_symbol"],
                                     values["_chem_comp_atom.x"], values["_chem_comp_atom.y"], values["_chem_comp_atom.z"]):
        if element in {"H", "D"}:
            continue
        atoms[name] = (float(x), float(y), float(z))
        rows.append(pdb_atom(len(rows) + 2, name, source, 12, atoms[name], element))
    p, o3 = atoms["P"], atoms["O3'"]
    # This is synthetic linked geometry, not a coordinate edit to a model.
    # Place the preceding O3' on the monomer's OP3 ray, rather than an
    # arbitrary laboratory axis. Normal cleanup replaces OP3 with that link.
    op3 = atoms["OP3"]
    length = dist(p, op3)
    incoming = tuple(a + 1.6 * (b - a) / length for a, b in zip(p, op3))
    predecessor = pdb_atom(1, "O3'", "DT", 11, incoming, "O")
    successor = pdb_atom(50, "P", "DC", 13, (o3[0] + 1.6, o3[1], o3[2]), "P")
    return predecessor + "".join(rows) + successor + "END\n"


@pytest.mark.parametrize("source,target", [("1W5", "DZ"), ("1WA", "DP")])
@pytest.mark.parametrize("explicit", [False, True])
def test_normal_postmr_keeps_source_and_freezes_target_definition(tmp_path, monkeypatch, source, target, explicit):
    run = tmp_path / "dataset/AutoMR/run_001"
    phaser = run / "Phaser"; phaser.mkdir(parents=True)
    source_model = phaser / "mr_solution.pdb"
    source_model.write_text(placed_source(source, target))
    observations = tmp_path / "dataset/observations.mtz"; observations.write_bytes(b"frozen fixture observations")
    plan = {"sequences": {}, "standard_pair": None, "allow_op3_sites": [], "mutations": (
        {"A:12": {"ligand_code": source, "requested": source}} if explicit else {})}
    report = {"workflow": "automr", "stage": "phaser", "status": "MR_SUCCESS", "frame": None,
              "post_mr_plan": plan, "inputs": {"reflections": str(observations)},
              "execution": {"phaser": {"solution_pdb": str(source_model)}}}
    (run / "report.json").write_text(json.dumps(report))
    original = source_model.read_bytes()
    def readyset(command, cwd, **kwargs):
        prepared = Path(command[1])
        assert source not in {v[17:20].strip() for v in prepared.read_text().splitlines() if v.startswith("HETATM")}
        (cwd / "prepared_model.updated.pdb").write_bytes(prepared.read_bytes())
        (cwd / "prepared_model.ligands.cif").write_bytes(ligand_dictionary(target).read_bytes())
        return SimpleNamespace(returncode=0, stdout="fixture ReadySet")
    monkeypatch.setattr("nasolve.postmr.subprocess.run", readyset)
    result = prepare_postmr(run, tmp_path / "phenix.ready_set")
    saved = json.loads((run / "report.json").read_text())
    postmr = saved["postmr"]
    assert postmr["coot"]["ran"] is False
    assert source_model.read_bytes() == original
    assert (run / "PostMR/Model/mr_solution.pdb").read_bytes() == original
    assert saved["post_mr_plan"] == plan
    conversion = postmr["component_normalization"]
    assert conversion["frozen_input_intent_unchanged"] is True
    assert conversion["coordinate_conversion"]["conversions"][0]["target_code"] == target
    assert target in conversion["target_dictionaries"]
    assert resolve_artifact_path(conversion["target_dictionaries"][target], run).is_file()
    assert target in postmr["dictionary_precedence"]["authoritative_codes"]
    assert postmr["linked_phosphate_profile"]["inventory"] == {"A:12": target}
    assert postmr["mutation_actions"][0]["after"] == target
    assert validate_refined_model(result.model_path, saved)["validated"] is True
    from nasolve.coot_view import _postmr_dictionaries
    assert _postmr_dictionaries(run, saved)
    if explicit:
        assert conversion["requested_target_changes"] == [{"site": "A:12", "requested_code": source, "prepared_code": target}]
    else:
        assert conversion["requested_target_changes"] == []
    with pytest.raises(PostMRPreparationError):
        prepare_postmr(run, tmp_path / "phenix.ready_set")


def test_installed_library_retains_source_and_target_semantics():
    from restraints.residue_library import load_residue_records
    records = load_residue_records()
    for code, category in (("1W5", "Z"), ("DZ", "Z"), ("1WA", "P"), ("DP", "P")):
        rows = [r for r in records if str(r.get("Ligand code")) == code]
        assert len(rows) == 1
        assert rows[0]["Source sheet"].upper() == category
        assert rows[0]["Sugar Type"].upper() == "DNA"


@pytest.mark.parametrize("source,target", [("1W5", "DZ"), ("1WA", "DP")])
def test_linked_fixture_is_valid_before_conversion_and_preserves_geometry(tmp_path, source, target):
    """A monomer orientation must not invalidate the synthetic incoming link."""
    model = tmp_path / "source.pdb"
    model.write_text(placed_source(source, target))
    original = model.read_bytes()
    source_clean = tmp_path / "source-clean.pdb"
    before = sanitize_phosphates(model, source_clean, reference_model=model)
    assert [(row["site"], row["atom"]) for row in before["removed"]] == [("A:12", "OP3")]
    first = before["checked"][0]
    assert (first["incoming_site"], first["outgoing_site"]) == ("A:11", "A:13")
    assert len(first["o_p_o_angles_degrees"]) == 6
    assert all(100.0 < value < 120.0 for value in first["o_p_o_angles_degrees"].values())
    converted = tmp_path / "converted.pdb"
    conversion = normalize_model(model, converted, {"A:12": (source, target)})
    converted_bytes = converted.read_bytes()
    assert conversion["mapped_xyz_occupancy_b_preserved"] is True
    after = sanitize_phosphates(converted, tmp_path / "converted-clean.pdb", reference_model=model)
    second = after["checked"][0]
    for field in ("incoming_site", "outgoing_site", "p_o_distances_angstrom", "o_p_o_angles_degrees"):
        assert second[field] == first[field]
    assert model.read_bytes() == original
    assert converted.read_bytes() == converted_bytes


@pytest.mark.parametrize("source,target,angle", [("1W5", "DZ", "28.5"), ("1WA", "DP", "29.8")])
def test_normalization_does_not_hide_invalid_phosphate_geometry(tmp_path, source, target, angle):
    """Retain the original bad fixture as a negative control, not a bypass."""
    lines = placed_source(source, target).splitlines(keepends=True)
    phosphorus = next(line for line in lines if line[12:16].strip() == "P"
                      and line[22:26].strip() == "12")
    p = tuple(float(phosphorus[i:i + 8]) for i in (30, 38, 46))
    lines[0] = pdb_atom(1, "O3'", "DT", 11, (p[0] - 1.6, p[1], p[2]), "O")
    model = tmp_path / "bad-source.pdb"
    model.write_text("".join(lines))
    original = model.read_bytes()
    converted = tmp_path / "bad-converted.pdb"
    normalize_model(model, converted, {"A:12": (source, target)})
    for path in (model, converted):
        destination = tmp_path / (path.stem + "-clean.pdb")
        with pytest.raises(PhosphateError) as caught:
            sanitize_phosphates(path, destination, reference_model=model)
        assert "angle " + angle + " degrees" in str(caught.value)
        assert not destination.exists()
    assert model.read_bytes() == original
