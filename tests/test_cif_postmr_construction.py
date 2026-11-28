"""Fresh ordinary construction controls with synthetic Coot process fixtures.

No installed Coot, Phenix, MR, ReadySet, or refinement is used by these tests.
"""
from dataclasses import asdict
import json
from math import sqrt
from pathlib import Path
import shutil

import pytest

from nasolve.cif_postmr_construction import (
    ORDINARY_POSTMR_CONSTRUCTION_CONTROLS, POLICY_ID,
    audit_construction_context, audit_postmr_construction, run_postmr_construction_controls,
)
from nasolve.postmr import MutationAction
from tests.test_cif_fragment_restoration import fixture, SCAFFOLD, EDGES

ROOT = Path(__file__).resolve().parents[1]
FRAME = ROOT / "MR_frames/5W6W/5W6W_noPO4.pdb"


def dictionary(path, code="DP", *, op3=False, bridge=False):
    names = [*SCAFFOLD, "NX", "C2", "QZ"] + (["OP3"] if op3 else [])
    edges = EDGES + [("C1'", "NX"), ("NX", "C2"), ("C2", "QZ")]
    if op3:
        edges += [("P", "OP3")]
    if bridge:
        edges += [("QZ", "C2'")]
    path.write_text(f'data_{code}\n_chem_comp.id {code}\n_chem_comp.type "DNA LINKING"\n'
        'loop_\n_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n_chem_comp_atom.type_symbol\n'
        + ''.join(f'{code} "{name}" {"P" if name=="P" else "O" if name.startswith("O") else "N" if name=="NX" else "C"}\n'
                  for name in names)
        + '#\nloop_\n_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n_chem_comp_bond.value_order\n'
        + ''.join(f'"{a}" "{b}" SING\n' for a, b in edges) + '#\n')
    return path


def dictionaries(tmp_path, *, op3=False):
    return {code: dictionary(tmp_path / (code + ".cif"), code, op3=op3)
            for code in ("DP", "PDU", "5PC")}


def audit_fixture(tmp_path):
    raw, _, parent, _, expected = fixture(tmp_path)
    raw.write_text("HEADER raw header\n" + raw.read_text().replace(" ZZZ ", "  DP "))
    parent.write_text(parent.read_text().replace("  DC ", "  DG "))
    # Add an independent unselected site and check it through both boundaries.
    other = next(l for l in parent.read_text().splitlines(keepends=True) if l.startswith("HETATM"))
    other = other[:21] + "Y" + other[22:]
    for path in (parent, raw):
        path.write_text(path.read_text() + other)
    final = tmp_path / "final.pdb"
    lines = []
    for line in raw.read_text().splitlines(keepends=True):
        if line.startswith("HETATM") and line[21] == "Z":
            xyz = expected[line[12:16].strip()]
            line = line[:30] + ''.join(f'{v:8.3f}' for v in xyz) + line[54:]
        lines.append(line)
    final.write_text(''.join(lines))
    source = dictionary(tmp_path / "source.cif")
    action = MutationAction("Z:9", "DG", "DP", "coot-parent-overlap", parent_code="DG")
    report = {"Z:9": {"status": "GRAPH_FRAGMENT_RESTORED"}}
    return parent, raw, final, (action,), {"DP": source}, {"Z:9": parent}, report


def test_independent_audit_measures_whole_fragment_and_preserved_context(tmp_path):
    inputs = audit_fixture(tmp_path)
    report = audit_postmr_construction(*inputs)
    assert report["status"] == "CONSTRUCTION_CONTROLS_PASS"
    assert report["sites"][0]["fragment_atoms"] == ["C2", "NX", "QZ"]
    assert report["sites"][0]["scaffold_matches_frozen_parent"] is True
    assert report["sites"][0]["attachment_orientation_preserved"] is True
    assert report["sites"][0]["max_fragment_distance_change"] <= .002
    assert report["scientific_geometry_qualification"] == "NOT_ASSESSED"


@pytest.mark.parametrize("defect", ["partial_parent_base_copy", "scaffold", "component", "metadata", "outside", "delete", "added", "header", "reflection", "parent"])
def test_independent_audit_refuses_geometry_and_identity_regressions(tmp_path, defect):
    inputs = audit_fixture(tmp_path)
    parent, raw, final, *_ = inputs
    lines = final.read_text().splitlines(keepends=True)
    index = next(i for i,l in enumerate(lines) if l.startswith("HETATM") and l[12:16].strip() == "C2")
    if defect == "partial_parent_base_copy":
        # The old behavior copied one parent's same-name base atom, leaving the
        # rest of the fragment in another frame.
        row = next(l for l in parent.read_text().splitlines() if l[12:16].strip() == "C2")
        lines[index] = lines[index][:30] + row[30:54] + lines[index][54:]
    elif defect == "scaffold":
        index = next(i for i,l in enumerate(lines) if l[12:16].strip() == "C3'")
        lines[index] = lines[index][:30] + f'{91.:8.3f}' + lines[index][38:]
    elif defect == "component":
        lines[index] = lines[index][:17] + " DC" + lines[index][20:]
    elif defect == "metadata":
        lines[index] = lines[index][:54] + "  1.00" + lines[index][60:]
    elif defect == "outside":
        lines[-1] = lines[-1][:30] + f'{91.:8.3f}' + lines[-1][38:]
    elif defect == "delete":
        lines.pop(index)
    elif defect == "added":
        lines.append(lines[index][:12] + " QQQ" + lines[index][16:])
    elif defect == "header":
        lines[0] = "HEADER changed\n"
    elif defect == "reflection":
        for i,line in enumerate(lines):
            if line.startswith("HETATM") and line[12:16].strip() in {"NX", "C2", "QZ"}:
                z = float(line[46:54])
                lines[i] = line[:46] + f'{60-z:8.3f}' + line[54:]
    elif defect == "parent":
        parent.write_text(parent.read_text().replace("  DG ", "  DT "))
    final.write_text(''.join(lines))
    with pytest.raises(ValueError):
        audit_postmr_construction(*inputs)


def test_supported_raw_fallback_is_reported_as_notes_without_user_gate(tmp_path):
    inputs = list(audit_fixture(tmp_path))
    shutil.copyfile(inputs[1], inputs[2])
    inputs[-1] = {"Z:9": {"status": "RAW_SITE_RETAINED", "reason": "Unmatched OP3",
                           "notes": ["Preserved raw component; terminal context remains provisional."]}}
    report = audit_postmr_construction(*inputs)
    assert report["status"] == "CONSTRUCTION_CONTROLS_PASS_WITH_NOTES"
    assert report["raw_fallback_sites"] == ["Z:9"]
    assert report["sites"][0]["fragment_transport_tested"] is False
    # Retaining a raw site is never permission to accept a missing base atom.
    for path in inputs[1:3]:
        path.write_text(''.join(l for l in path.read_text().splitlines(keepends=True) if l[12:16].strip() != "QZ"))
    with pytest.raises(ValueError, match="missing a declared base atom"):
        audit_postmr_construction(*inputs)


def test_inspect_only_stages_exact_sources_and_no_native_claim(tmp_path, monkeypatch):
    sources = dictionaries(tmp_path, op3=True)
    atl = dictionary(tmp_path / "ATL.cif", "ATL", bridge=True)
    before = {p: p.read_bytes() for p in [FRAME, *sources.values(), atl]}
    monkeypatch.setattr("nasolve.postmr.construct_postmr_model", lambda *a, **k: pytest.fail("Inspect-only called Coot"))
    output = tmp_path / "control"
    report = run_postmr_construction_controls(FRAME, sources, output, inspect_only=True, atl_dictionary=atl)
    assert report["policy_id"] == POLICY_ID and report["status"] == "INSPECT_ONLY"
    assert report["controls"] == [asdict(MutationAction(row["site"], row["parent"], row["component"], "coot-parent-overlap", parent_code=row["parent"]))
                                  for row in ORDINARY_POSTMR_CONSTRUCTION_CONTROLS]
    assert all((output / "inputs" / (code + ".cif")).read_bytes() == path.read_bytes() for code, path in sources.items())
    assert report["atl_control"]["restoration_eligibility"] == "RAW_SITE_RETAINED"
    assert all(row["dictionary_scaffold_atoms_absent_from_parent"] == ["OP3"] for row in report["expected_restoration_context"].values())
    assert report["coot"]["execution"] == "NOT_RUN" and report["coot"]["timeout_seconds"] == 600
    assert report["readyset_execution"] == report["phenix_execution"] == report["optimization"] == report["refinement"] == "NOT_RUN"
    assert report["mtz_used"] is False and report["user_cif_review_required"] is False
    assert report["source_inputs_preserved"] and all(p.read_bytes() == data for p, data in before.items())
    saved = json.loads((output / "construction_report.json").read_text())
    assert saved == report
    # Output references retain their meaning after the inputs' old directory is gone.
    relocated = tmp_path / "relocated"
    shutil.move(output, relocated)
    for path in sources.values():
        path.unlink()
    assert (relocated / report["input_model"]["path"]).is_file()
    assert all((relocated / row["path"]).is_file() for row in report["dictionaries"].values())


def test_failed_coot_leaves_portable_plan_sources_and_failed_receipt(tmp_path, monkeypatch):
    sources = dictionaries(tmp_path)
    def fail(*args, **kwargs):
        assert kwargs["timeout_seconds"] == 600
        raise RuntimeError("Synthetic Coot failure")
    monkeypatch.setattr("nasolve.postmr.construct_postmr_model", fail)
    output = tmp_path / "failed"
    with pytest.raises(RuntimeError, match="Synthetic Coot"):
        run_postmr_construction_controls(FRAME, sources, output, coot_executable=Path("/fixture/coot"), coot_version="fixture")
    report = json.loads((output / "construction_report.json").read_text())
    assert report["status"] == "FAILED" and report["analysis_completed"] is False
    assert report["coot"]["execution"] == "FAILED" and report["source_inputs_preserved"]
    assert report["coot"]["version"] == "fixture"
    assert (output / "construction_plan.json").is_file()


def live_fixture(tmp_path, monkeypatch, op3=True, *, foreign_conect=False):
    """Fake only the external Coot process; run ordinary production context/restoration."""
    from nasolve.cif_construction_provenance import _pdb_inventory
    sources = dictionaries(tmp_path, op3=op3)
    calls = []
    def fake_coot(input_model, output_model, actions, executable, coot_directory,
                  environment, dictionary_paths, parent_models, *, timeout_seconds):
        calls.append((actions, dict(dictionary_paths), executable, dict(environment), timeout_seconds))
        current = _pdb_inventory(input_model)
        replacements = {}
        for action in actions:
            shutil.copyfile(input_model, parent_models[action.site])
            chain, resid = action.site.split(":")
            parent = {k[-1]: row["xyz"] for k, row in current.items() if k[:2] == (chain, resid)}
            center = parent["C1'"]
            a, b = [[parent[name][i]-center[i] for i in range(3)] for name in ("O4'", "C2'")]
            normal = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
            length = sqrt(sum(x*x for x in normal)); normal = [x/length for x in normal]
            points = {name: parent[name] for name in SCAFFOLD}
            for j, name in enumerate(("NX", "C2", "QZ")):
                points[name] = [center[i]+(.2+j*.2)*a[i]+(.3+j*.1)*b[i]+(1.4+j*.4)*normal[i] for i in range(3)]
            if op3:
                points["OP3"] = [parent["P"][i]+(.3, .5, 1.2)[i] for i in range(3)]
            lines = []
            for serial, (name, xyz) in enumerate(points.items(), 9000):
                x,y,z = xyz; xyz = (-y+10, x+20, z+30)
                element = "P" if name == "P" else "O" if name.startswith("O") else "N" if name == "NX" else "C"
                lines.append(f'HETATM{serial:5d} {name:>4} {action.after:>3} {chain}{int(resid):4d}    '
                    + ''.join(f'{value:8.3f}' for value in xyz) + f'  0.75 17.00          {element:>2}\n')
            replacements[action.site] = ''.join(lines)
        lines = []
        for line in input_model.read_text().splitlines(keepends=True):
            site = line[21].strip() + ":" + line[22:26].strip() if line.startswith(("ATOM  ", "HETATM")) else None
            if site in replacements:
                lines.append(replacements.pop(site))
            elif site not in {a.site for a in actions}:
                lines.append(line)
        output_model.write_text(''.join(lines))
        if foreign_conect:
            output_model.write_text(output_model.read_text() + "CONECT9999999998\n")
        log = coot_directory / "coot.log"; log.write_text("Synthetic external process fixture; no Coot installed.\n")
        script = coot_directory / "mutate.py"; script.write_text("# synthetic process fixture\n")
        return script, log
    monkeypatch.setattr("nasolve.postmr._run_coot", fake_coot)
    output = tmp_path / "fresh"
    report = run_postmr_construction_controls(FRAME, sources, output,
        coot_executable=Path("/fixture/coot"), coot_version="fixture", environment={"FIXTURE": "yes"})
    return output, report, calls


@pytest.mark.parametrize("op3", [False, True])
def test_live_controls_use_shared_ordinary_construction_once_and_audit_the_actual_files(tmp_path, monkeypatch, op3):
    output, report, calls = live_fixture(tmp_path, monkeypatch, op3)
    assert len(calls) == 1 and calls[0][-1] == 600
    assert calls[0][3] == {"FIXTURE": "yes"}
    assert {a.after for a in calls[0][0]} == {"DP", "PDU", "5PC"}
    assert set(calls[0][1]) == {"DP", "PDU", "5PC"}
    assert report["coot"]["execution"] == "COMPLETED" and report["analysis_completed"]
    assert report["source_inputs_preserved"]
    assert all(row["actual_coot_composition"] == "OBSERVED" for row in report["expected_restoration_context"].values())
    assert all(row["actual_coot_inventory"]["atom_count"] == 14 + op3 for row in report["expected_restoration_context"].values())
    assert report["status"] == "CONSTRUCTION_CONTROLS_PASS"
    assert all(r["fragment_transport_tested"] for r in report["audit"]["sites"])
    assert all(r["status"] == "GRAPH_FRAGMENT_RESTORED" for r in report["coordinate_restoration"].values())
    if op3:
        context = report["audit"]["context_audit"]
        assert context["status"] == "CONSTRUCTION_CONTEXT_DELTA_PASS"
        assert report["audit"]["raw_composition_preserved"] is False
        assert report["audit"]["contextual_composition_preserved"] is True
        assert context["raw_coordinates_preserved"] is True
        assert {row["site"] for row in context["removed_atoms"]} == {"A:6", "A:9", "A:7"}
        assert all(row["atom"] == "OP3" for row in context["removed_atoms"])
        assert len(context["serial_repairs"]) == 45 and len(context["retained_atom_serial_repairs"]) == 42
        assert context["unique_context_serials"] and context["inherited_connections_rebound"]
        assert context["final_phosphate_audit"]["removed"] == []
        assert all(row["actual_restoration_input_composition"]["removed_from_raw_coot"] == ["OP3"]
                   for row in report["expected_restoration_context"].values())
    else:
        assert report["audit"]["context_audit"]["status"] == "NO_CONTEXT_CHANGE"
        assert report["audit"]["raw_composition_preserved"] is True
    assert report["readyset_execution"] == report["phenix_execution"] == report["optimization"] == "NOT_RUN"


def test_unproved_context_retains_complete_raw_with_observed_inventory_and_notes(tmp_path, monkeypatch):
    output, report, calls = live_fixture(tmp_path, monkeypatch, foreign_conect=True)
    assert len(calls) == 1
    assert report["status"] == "CONSTRUCTION_CONTROLS_PASS_WITH_NOTES"
    assert report["context_receipt"]["status"] == "RAW_CONTEXT_RETAINED"
    assert report["context_receipt"]["removed_atoms"] == report["context_receipt"]["serial_repairs"] == []
    assert report["audit"]["raw_composition_preserved"] is True
    assert report["audit"]["context_audit"]["unique_context_serials"] is False
    assert set(report["audit"]["raw_fallback_sites"]) == {"A:6", "A:9", "A:7"}
    assert all(row["actual_coot_composition"] == "OBSERVED" for row in report["expected_restoration_context"].values())
    assert (output / report["outputs"]["model"]["path"]).read_bytes() == (output / report["outputs"]["raw_model"]["path"]).read_bytes()
    assert report["user_cif_review_required"] is False


@pytest.mark.parametrize("defect", ["retained_xyz", "unselected_serial", "extra_deletion", "context_conect", "raw_conect", "shadow_base", "shadow_scaffold", "repair_identity", "deletion_identity", "file_binding"])
def test_independent_context_audit_refuses_unauthorized_delta_or_forged_proof(tmp_path, monkeypatch, defect):
    output, report, _ = live_fixture(tmp_path, monkeypatch)
    def path(row):
        return output / row["path"]
    initial = path(report["input_model"])
    raw = path(report["outputs"]["raw_model"])
    context = path(report["outputs"]["restoration_input"])
    shadow = path(report["outputs"]["context_shadow"])
    if defect in {"retained_xyz", "unselected_serial", "extra_deletion"}:
        lines = context.read_text().splitlines(keepends=True)
        index = next(i for i,l in enumerate(lines) if l.startswith("HETATM") and l[12:16].strip() == "NX")
        if defect == "retained_xyz":
            lines[index] = lines[index][:30] + f'{91.:8.3f}' + lines[index][38:]
        elif defect == "extra_deletion":
            lines.pop(index)
        else:
            index = next(i for i,l in enumerate(lines) if l.startswith("ATOM  ") and l[21:26] == "A   1")
            lines[index] = lines[index][:6] + "50000" + lines[index][11:]
        context.write_text(''.join(lines))
    elif defect in {"context_conect", "raw_conect"}:
        target = context if defect == "context_conect" else raw
        target.write_text(target.read_text() + "CONECT    1    3\n")
    elif defect in {"shadow_base", "shadow_scaffold"}:
        lines = shadow.read_text().splitlines(keepends=True)
        name = "NX" if defect == "shadow_base" else "C3'"
        index = next(i for i,l in enumerate(lines) if l.startswith("HETATM") and l[12:16].strip() == name)
        lines[index] = lines[index][:30] + f'{91.:8.3f}' + lines[index][38:]
        shadow.write_text(''.join(lines))
    elif defect == "repair_identity":
        report["context_receipt"]["serial_repairs"][0]["site"] = "A:99"
    elif defect == "deletion_identity":
        report["context_receipt"]["removed_atoms"][0]["atom"] = "OP1"
    else:
        report["context_receipt"]["raw_model_sha256"] = "0" * 64
    actions = tuple(MutationAction(**row) for row in report["controls"])
    with pytest.raises(ValueError):
        audit_construction_context(initial, raw, context, actions,
            {code: path(row) for code, row in report["dictionaries"].items()}, report["context_receipt"],
            context_shadow=shadow, parent_models={site: path(row) for site, row in report["parents"].items()})


@pytest.mark.parametrize("defect", ["missing_dictionary", "extra_dictionary", "timeout", "parent", "existing", "symlink"])
def test_staging_refuses_wrong_scope_or_overwrites(tmp_path, defect):
    sources = dictionaries(tmp_path)
    frame = tmp_path / "frame.pdb"
    shutil.copyfile(FRAME, frame)
    out = tmp_path / "control"
    kwargs = {"inspect_only": True}
    if defect == "missing_dictionary":
        sources.pop("DP")
    elif defect == "extra_dictionary":
        sources["ATL"] = dictionary(tmp_path / "ATL.cif", "ATL")
    elif defect == "timeout":
        kwargs["timeout_seconds"] = 601
    elif defect == "parent":
        frame.write_text(''.join(l[:17] + " DT" + l[20:] if l.startswith(("ATOM", "HETATM")) and l[21:26] == "A   6" else l
                                 for l in frame.read_text().splitlines(keepends=True)))
    elif defect == "existing":
        out.mkdir(); (out / "KEEP").write_text("keep")
    elif defect == "symlink":
        original = tmp_path / "actual"; original.mkdir()
        link = tmp_path / "link"; link.symlink_to(original, target_is_directory=True)
        out = link / "control"
    with pytest.raises((ValueError, FileExistsError)):
        run_postmr_construction_controls(frame, sources, out, **kwargs)
    if defect == "existing":
        assert (out / "KEEP").read_text() == "keep"
