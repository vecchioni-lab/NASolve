"""Mapped construction orchestration with synthetic external-process fixtures.

The copying/coordinate-producing fixture below is not Coot and its invented
generic base graphs are not chemical or native qualification. The actual
ordinary context/restoration functions and independent audits still execute.
"""
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from nasolve.cif_mixed_pair_fixture import (
    REQUESTED_MAP, build_mixed_pair_plan, run_mixed_pair_fixture, read_mixed_pair_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = (ROOT / "MR_frames/5W6W/C_G.pdb",
          ROOT / "src/nasolve/data/restraints/5W6W_secondary_structure.eff",
          ROOT / "src/nasolve/data/restraints/5W6W_Std_padd.txt")


def test_fixed_site_plan_binds_all_eight_pairs_and_canonical_background():
    plan = build_mixed_pair_plan(*ASSETS)
    assert [(row["family"], tuple(row["sites"]), tuple(row["components"])) for row in plan["requested_pairs"]] == list(REQUESTED_MAP)
    assert plan["pair_count"] == 20 and plan["background_pair_count"] == 12
    assert len({site for row in plan["all_pairs"] for site in row["sites"]}) == 40
    assert len({site for row in plan["requested_pairs"] for site in row["sites"]}) == 16
    assert len(plan["target_site_components"]) == 42
    assert plan["canonical_site_components"]["A:12"] == "DC"
    assert plan["canonical_site_components"]["B:4"] == "DG"
    assert plan["target_site_components"]["A:12"] == "DZ"
    assert plan["target_site_components"]["B:4"] == "DP"
    assert plan["stack_count"] == len({tuple(row) for row in plan["stack_edges"]}) == 38
    assert plan["orientation_control_count"] == 16
    assert len(plan["orientation_controls"]) == 8
    assert plan["coot_mutation_count"] == 12
    assert sum(row["method"] == "none" for row in plan["mutation_actions"]) == 4
    assert all(row["before"] == row["parent_code"] for row in plan["mutation_actions"] if row["method"] != "none")
    assert plan["annotated_sequences"] == {
        "A": "GAG(5PC)(1AP)(IGU)(5CM)CTGT(DZ)CGGACA(DF)(CGY)A",
        "B": "CCG(DP)ACA", "C": "G(S6G)(IMC)TGCT", "D": "CT(DX)A(PDU)GT"}
    assert plan["mtz_used"] is False and plan["native_proxy_membership"] == "NOT_ASSESSED"


@pytest.mark.parametrize("index", range(3))
def test_changed_source_or_pair_declaration_is_rejected_before_output(tmp_path, index):
    assets = list(ASSETS)
    changed = tmp_path / assets[index].name
    changed.write_bytes(assets[index].read_bytes() + b"\n# CHANGED\n")
    assets[index] = changed
    with pytest.raises(ValueError, match="checksum"):
        build_mixed_pair_plan(*assets)


def artificial_sources(tmp_path, monkeypatch):
    """Fake the installed source selector, preserving actual shared byte freezing."""
    from nasolve.cif_acquisition import REQUESTED_PAIRS
    from tests.test_cif_postmr_construction import dictionary
    codes = sorted({code for pair in REQUESTED_PAIRS for code in pair})
    origin = tmp_path / "source-fixture"
    origin.mkdir()
    paths = {}
    for code in [*codes, "DC"]:
        path = origin / (code + ".cif")
        if code in {"DF", "S6G"}:
            shutil.copyfile(ROOT / "src/nasolve/data/ligands" / (code + ".cif"), path)
        else:
            dictionary(path, code)
        paths[code] = path
    calls = []
    def acquisition(executable, output, **kwargs):
        calls.append((executable, kwargs))
        folder = Path(output)
        (folder / "sources").mkdir(parents=True)
        rows = {}
        for code in codes:
            destination = folder / "sources" / (code + ".cif")
            shutil.copyfile(paths[code], destination)
            data = destination.read_bytes()
            rows[code] = {"authority": "SYNTHETIC_TEST_SOURCE", "historical_source_path": str(paths[code]),
                "source": {"anchor": "acquisition_directory", "path": "sources/" + code + ".cif",
                           "sha256": sha256(data).hexdigest(), "size": len(data)}}
        report = {"status": "ORDINARY_ACQUISITION_CONTROLS_PASS", "sources": rows,
                  "synthetic_dataclass_tuple": (("EXPLICIT", "BOUNDARY"),),
                  "fixture_scope": "ARTIFICIAL_SOURCE_SELECTION_BOUNDARY; NOT_NATIVE_CHEMISTRY"}
        (folder / "acquisition.json").write_text(json.dumps(report))
        return report
    monkeypatch.setattr("nasolve.cif_acquisition.audit_ordinary_acquisition", acquisition)
    monkeypatch.setattr("nasolve.curated_ligands.ligand_source", lambda code, **kw:
                        SimpleNamespace(path=paths[code], authority="SYNTHETIC_TEST_SOURCE"))
    return paths, calls


def fake_external_coot(monkeypatch, *, incomplete=False, failure=False, context_op3=False):
    from nasolve.cif_construction_provenance import _pdb_inventory
    from tests.test_cif_fragment_restoration import SCAFFOLD
    calls = []
    def fake(input_model, output_model, actions, executable, coot_directory,
             environment, dictionary_paths, parent_models, *, timeout_seconds):
        calls.append({"actions": actions, "deadline": timeout_seconds, "sources": dictionary_paths})
        if failure:
            raise RuntimeError("SYNTHETIC_COOT_FAILURE")
        current = _pdb_inventory(input_model)
        replacements = {}
        for action in actions:
            shutil.copyfile(input_model, parent_models[action.site])
            chain, resid = action.site.split(":")
            parent = {key[-1]: row["xyz"] for key, row in current.items() if key[:2] == (chain, resid)}
            if action.after in {"DF", "S6G"}:
                replaced, anchor, target = ("O2", "C2", "S1") if action.after == "DF" else ("O6", "C6", "S6")
                lines = []
                for line in Path(input_model).read_text().splitlines(keepends=True):
                    if not line.startswith(("ATOM  ", "HETATM")) or line[21].strip() + ":" + line[22:26].strip() != action.site:
                        continue
                    line = line[:17] + f"{action.after:>3}" + line[20:]
                    # Established curated restoration is allowed to copy the
                    # frozen parent's occupancy and B, not merely its XYZ.
                    line = line[:54] + "  0.75 17.00" + line[66:]
                    if line[12:16].strip() == replaced:
                        vector = [parent[replaced][i] - parent[anchor][i] for i in range(3)]
                        length = sqrt(sum(value * value for value in vector))
                        xyz = [parent[anchor][i] + 1.8 * vector[i] / length for i in range(3)]
                        line = line[:12] + f"{target:>4}" + line[16:30] + "".join(f"{v:8.3f}" for v in xyz) + line[54:76] + " S" + line[78:]
                    lines.append(line)
                replacements[action.site] = "".join(lines)
            else:
                center = parent["C1'"]
                a, b = [[parent[name][i] - center[i] for i in range(3)] for name in ("O4'", "C2'")]
                normal = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
                length = sqrt(sum(x*x for x in normal))
                normal = [x / length for x in normal]
                points = {name: parent[name] for name in SCAFFOLD}
                for j, name in enumerate(("NX", "C2", "QZ")):
                    points[name] = [center[i] + (.2+j*.2)*a[i] + (.3+j*.1)*b[i] + (1.4+j*.4)*normal[i] for i in range(3)]
                if context_op3 and action.after == "PDU":
                    points["OP3"] = [parent["P"][i] + (.3, .5, 1.2)[i] for i in range(3)]
                lines = []
                for serial, (name, xyz) in enumerate(points.items(), 9000):
                    x, y, z = xyz
                    xyz = (-y + 10, x + 20, z + 30)
                    element = "P" if name == "P" else "O" if name.startswith("O") else "N" if name == "NX" else "C"
                    lines.append(f'HETATM{serial:5d} {name:>4} {action.after:>3} {chain}{int(resid):4d}    '
                                 + "".join(f"{v:8.3f}" for v in xyz) + f'  0.75 17.00          {element:>2}\n')
                replacements[action.site] = "".join(lines)
        selected = set(replacements)
        if incomplete:
            replacements.pop(actions[0].site)
        lines = []
        for line in Path(input_model).read_text().splitlines(keepends=True):
            site = line[21].strip() + ":" + line[22:26].strip() if line.startswith(("ATOM  ", "HETATM", "ANISOU")) else None
            if site in replacements:
                lines.append(replacements.pop(site))
            elif site not in selected:
                lines.append(line)
        output_model.write_text("".join(lines))
        log = coot_directory / "coot.log"
        log.write_text("Synthetic external process; no Coot or native SDK.\n")
        script = coot_directory / "mutate.py"
        script.write_text("# Synthetic external process fixture\n")
        return script, log
    monkeypatch.setattr("nasolve.postmr._run_coot", fake)
    return calls


def fake_compiler(monkeypatch):
    calls = []
    def compile(model, pairs, stacks, sources, output, *, orientation_controls):
        calls.append((model, pairs, stacks, sources, orientation_controls))
        Path(output).mkdir()
        report = {"status": "EXPLICIT_NA_POLICY_COMPILED", "pair_count": len(pairs),
                  "requested_pair_count": sum(row["scope"] == "requested" for row in pairs),
                  "stack_count": len(stacks), "orientation_control_count": 2 * len(orientation_controls),
                  "fixture_scope": "MOCK_COMPILER_BOUNDARY; NOT_CHEMISTRY_OR_NATIVE_EVIDENCE"}
        (Path(output) / "fixture_policy.json").write_text(json.dumps(report))
        return report
    monkeypatch.setattr("nasolve.cif_explicit_na_policy.compile_explicit_na_policy", compile)
    monkeypatch.setattr("nasolve.cif_explicit_na_policy.read_explicit_na_policy",
                        lambda directory: json.loads((Path(directory) / "fixture_policy.json").read_bytes()))
    return calls


def test_inspect_only_stages_sources_and_declared_intent_without_a_process(tmp_path, monkeypatch):
    paths, calls = artificial_sources(tmp_path, monkeypatch)
    monkeypatch.setattr("nasolve.postmr.construct_postmr_model", lambda *a, **k: pytest.fail("Coot called in inspect-only"))
    output = tmp_path / "prepared"
    report = run_mixed_pair_fixture(*ASSETS, Path("/fake/phenix.ready_set"), output, inspect_only=True)
    assert report["status"] == "PREPARED_ONLY" and report["analysis_completed"]
    assert report["source_counts"] == {"requested": 15, "background": 1}
    assert len(report["source_bindings"]) == 16 and len(calls) == 1
    assert report["coot"]["execution"] == "NOT_RUN" and report["decision"]["selected"] is None
    assert len(report["five_prime_atoms_removed"]) == 10
    shutil.rmtree(next(iter(paths.values())).parent)
    moved = tmp_path / "relocated"
    output.rename(moved)
    assert read_mixed_pair_fixture(moved) == report


def test_one_ordinary_construction_audits_ten_graph_and_two_curated_sites(tmp_path, monkeypatch):
    artificial_sources(tmp_path, monkeypatch)
    calls = fake_external_coot(monkeypatch)
    compiled = fake_compiler(monkeypatch)
    output = tmp_path / "live-fixture"
    report = run_mixed_pair_fixture(*ASSETS, Path("/fake/phenix.ready_set"), output,
                                    coot_executable=Path("/fake/coot"), coot_version="TOY_EXTERNAL_FIXTURE")
    assert report["status"] == "MIXED_PAIR_CONSTRUCTION_PASS", report.get("error")
    assert len(calls) == 1 and calls[0]["deadline"] == 600 and len(calls[0]["actions"]) == 12
    assert len(calls[0]["sources"]) == 12
    audit = report["construction_audit"]
    assert audit["graph_site_count"] == 10 and audit["curated_site_count"] == 2
    assert audit["global_composition_metadata_and_unselected_coordinates"] == "PASS"
    assert {row["component"] for row in audit["sites"] if row["status"] == "CURATED_DECLARED_PLACEMENT"} == {"DF", "S6G"}
    assert all(row["scaffold_matches_frozen_parent"] for row in audit["sites"])
    assert len(compiled) == 1 and len(compiled[0][1]) == 20 and len(compiled[0][2]) == 38 and len(compiled[0][3]) == 16
    assert report["source_inputs_preserved"] and report["decision"]["selected"] == "constructed_mixed_model"
    assert report["native_execution"] == "NOT_RUN" and report["native_proxy_membership"] == "NOT_ASSESSED"
    assert read_mixed_pair_fixture(output) == report


def test_mixed_context_serial_repair_remains_independently_auditable(tmp_path, monkeypatch):
    from tests.test_cif_postmr_construction import dictionary

    paths, _ = artificial_sources(tmp_path, monkeypatch)
    dictionary(paths["PDU"], "PDU", op3=True)
    fake_external_coot(monkeypatch, context_op3=True)
    fake_compiler(monkeypatch)
    output = tmp_path / "mixed-context"
    report = run_mixed_pair_fixture(*ASSETS, Path("/fake/phenix.ready_set"), output,
                                    coot_executable=Path("/fake/coot"), coot_version="TOY_EXTERNAL_FIXTURE")
    assert report["status"] == "MIXED_PAIR_CONSTRUCTION_PASS", report.get("error")
    context = report["context_receipt"]
    assert context["status"] == "CONTEXT_PREPARED"
    assert {(row["site"], row["atom"]) for row in context["removed_atoms"]} == {("D:5", "OP3")}
    assert context["curated_context"]["sites"] == ["A:19", "C:9"]
    assert context["curated_context"]["candidate_sites"] == []
    assert {row["site"] for row in context["serial_repairs"]} == {
        row["site"] for row in report["plan"]["mutation_actions"] if row["method"] == "coot-parent-overlap"}
    assert report["construction_audit"]["context_audit"]["status"] == "CONSTRUCTION_CONTEXT_DELTA_PASS"
    assert read_mixed_pair_fixture(output) == report


@pytest.mark.parametrize("defect", ["exception", "incomplete"])
def test_failed_construction_preserves_input_but_never_selects_canonical_as_mixed(tmp_path, monkeypatch, defect):
    artificial_sources(tmp_path, monkeypatch)
    fake_external_coot(monkeypatch, failure=defect == "exception", incomplete=defect == "incomplete")
    compiled = fake_compiler(monkeypatch)
    output = tmp_path / "failure"
    report = run_mixed_pair_fixture(*ASSETS, Path("/fake/phenix.ready_set"), output,
                                    coot_executable=Path("/fake/coot"), coot_version="TOY_EXTERNAL_FIXTURE")
    assert report["status"] == "MIXED_PAIR_CONSTRUCTION_REVIEW"
    assert report["source_inputs_preserved"] and not report["analysis_completed"]
    assert report["decision"]["selected"] is None and report["decision"]["original_template_retained"]
    assert not compiled and (output / "inputs/template.pdb").read_bytes() == ASSETS[0].read_bytes()
    assert read_mixed_pair_fixture(output) == report


@pytest.mark.parametrize("target", ["source", "plan", "escape", "symlink", "report_symlink", "native_claim", "malformed_report"])
def test_portable_reader_rejects_changed_or_unsafe_scientific_evidence(tmp_path, monkeypatch, target):
    artificial_sources(tmp_path, monkeypatch)
    output = tmp_path / "prepared"
    report = run_mixed_pair_fixture(*ASSETS, Path("/fake/phenix.ready_set"), output, inspect_only=True)
    if target == "source":
        (output / report["source_bindings"]["PDU"]["source"]["path"]).write_text("CHANGED")
    elif target == "plan":
        (output / "construction_plan.json").write_text("{}")
    elif target == "escape":
        report["inputs"]["template"]["path"] = "../outside.pdb"
        (output / "mixed_pair_fixture.json").write_text(json.dumps(report))
    elif target == "native_claim":
        report["native_execution"] = "COMPLETED"
        (output / "mixed_pair_fixture.json").write_text(json.dumps(report))
    elif target == "malformed_report":
        (output / "mixed_pair_fixture.json").write_text("[]")
    elif target == "report_symlink":
        path = output / "mixed_pair_fixture.json"
        outside = tmp_path / "outside.json"
        path.rename(outside)
        path.symlink_to(outside)
    else:
        path = output / report["inputs"]["template"]["path"]
        path.unlink()
        path.symlink_to(ASSETS[0])
    with pytest.raises(ValueError):
        read_mixed_pair_fixture(output)


@pytest.mark.parametrize("timeout", [0, 601, True, 1.5])
def test_invalid_budget_has_no_output(tmp_path, timeout):
    output = tmp_path / "not-created"
    with pytest.raises(ValueError):
        run_mixed_pair_fixture(*ASSETS, Path("/fake/phenix.ready_set"), output, inspect_only=True, timeout_seconds=timeout)
    assert not output.exists()


def test_reporting_failure_cannot_mask_the_original_construction_error(tmp_path, monkeypatch):
    import nasolve.cif_mixed_pair_fixture as module
    artificial_sources(tmp_path, monkeypatch)
    fake_external_coot(monkeypatch, failure=True)
    write = module._write_json
    def failed_report(path, value):
        if Path(path).name == "mixed_pair_fixture.json":
            raise OSError("SYNTHETIC_RECEIPT_WRITE_FAILURE")
        return write(path, value)
    monkeypatch.setattr(module, "_write_json", failed_report)
    with pytest.raises(RuntimeError, match="SYNTHETIC_COOT_FAILURE") as caught:
        run_mixed_pair_fixture(*ASSETS, Path("/fake/phenix.ready_set"), tmp_path / "failure",
                               coot_executable=Path("/fake/coot"))
    assert caught.value.fixture_reporting_error == {
        "error_type": "OSError", "error": "SYNTHETIC_RECEIPT_WRITE_FAILURE"}
