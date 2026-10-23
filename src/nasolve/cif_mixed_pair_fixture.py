"""Fresh explicitly mapped eight-pair construction, without MR or native claims.

The packaged W scaffold and its two declaration resources are immutable inputs.
NARestraints supplies the policy; Coot uses the ordinary construction helper.
The resulting PHIL is compiled evidence, not proof of native proxy membership.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re

POLICY_ID = "cif-eight-pair-construction-fixture-v1"
FRAME_SHA256 = "d26ebf248a0a597a3884a6d6b2c6ec8f9bba27c9cad9f0604da136e13bfb1817"
SECONDARY_SHA256 = "442ec9ef669098283f336f6382a7b69e29f119854a476ed88c1758e25335b3e8"
PADD_SHA256 = "6bf81211a0f92d76e92b2580c356e3fa47f4e0a1a2c2e1e08612fc9bff9dc7e1"
REQUESTED_MAP = (
    ("K:X", ("A:20", "D:3"), ("CGY", "DX")),
    ("D:T", ("A:5", "C:11"), ("1AP", "DT")),
    ("Z:P", ("A:12", "B:4"), ("DZ", "DP")),
    ("B:S", ("A:6", "C:10"), ("IGU", "IMC")),
    ("PDU:A", ("D:5", "A:18"), ("PDU", "DA")),
    ("5PC:G", ("A:4", "C:12"), ("5PC", "DG")),
    ("5CM:Q", ("A:7", "C:9"), ("5CM", "S6G")),
    ("F:A", ("A:19", "D:4"), ("DF", "DA")),
)
_ANCHOR = "mixed_pair_fixture_directory"


def _sha(data):
    return sha256(data).hexdigest()


def _write_json(path, value):
    data = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with Path(path).open("xb") as handle:
        handle.write(data)


def _safe(name):
    return (isinstance(name, str) and bool(name) and not name.startswith("/")
            and "\\" not in name and ":" not in name
            and not any(ord(c) < 32 or ord(c) == 127 for c in name)
            and all(part not in {"", ".", ".."} for part in name.split("/")))


def _artifact(path, root):
    path, root = Path(path), Path(root)
    relative = path.relative_to(root).as_posix()
    if not _safe(relative) or any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError("Scientific fixture reference cannot traverse a symlink or unsafe path")
    data = path.read_bytes()
    return {"anchor": _ANCHOR, "path": relative, "sha256": _sha(data), "size": len(data)}


def _read_artifact(root, ref):
    if (not isinstance(ref, dict) or ref.get("anchor") != _ANCHOR or not _safe(ref.get("path"))
            or type(ref.get("size")) is not int or ref["size"] < 0):
        raise ValueError("Invalid fixture artifact reference")
    path = Path(root) / ref["path"]
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError("Fixture artifact cannot traverse a symlink")
    data = path.read_bytes()
    if len(data) != ref["size"] or _sha(data) != ref.get("sha256"):
        raise ValueError("Frozen fixture artifact bytes differ")
    return path


def _site_codes(data):
    from .synthetic_dna import _model_inventory
    lines, _ = _model_inventory(data)
    result = OrderedDict()
    for line in lines:
        if line.startswith(("ATOM  ", "HETATM")):
            site = line[21] + ":" + line[22:26].strip()
            code = line[17:20].strip()
            if site in result and result[site] != code:
                raise ValueError("Ambiguous fixture residue identity")
            result[site] = code
    return result


def build_mixed_pair_plan(template, secondary, padd):
    """Bind all target sites to literal packaged pair declarations, never distance.

    The original canonical identities are inventoried from the actual selected
    C_G model. Its historical sequence reference is deliberately not substituted.
    """
    from .cif_acquisition import REQUESTED_PAIRS
    from .cif_na_policy import _parse, _path, _site_selection, SS
    from .postmr import build_mutation_plan
    from .synthetic_dna import CHAIN_IDS

    paths = {"template": Path(template), "secondary": Path(secondary), "padd": Path(padd)}
    snapshots = {key: path.read_bytes() for key, path in paths.items()}
    expected = {"template": FRAME_SHA256, "secondary": SECONDARY_SHA256, "padd": PADD_SHA256}
    if any(_sha(snapshots[key]) != value for key, value in expected.items()):
        raise ValueError("Packaged eight-pair frame or declaration checksum differs")
    canonical = _site_codes(snapshots["template"])
    nodes, _ = _parse(snapshots["secondary"].decode())
    declarations = []
    for node in nodes:
        if _path(node) != SS + ".nucleic_acid.base_pair":
            continue
        fields = node["fields"]
        if set(fields) != {"base1", "base2", "saenger_class"} or fields["saenger_class"] not in {"19", "20"}:
            raise ValueError("Unsupported packaged canonical pair declaration")
        sites = [":".join(_site_selection(fields[key])) for key in ("base1", "base2")]
        declarations.append({"sites": sites, "resource": "secondary", "canonical_saenger_class": fields["saenger_class"]})
    lines = snapshots["padd"].decode().splitlines()
    if len(lines) != 2:
        raise ValueError("Require exactly the declared two-row central pair stretch")
    stretches = [re.fullmatch(r"([A-Za-z0-9])\s+(-?\d+):(-?\d+)", line) for line in lines]
    if any(match is None for match in stretches):
        raise ValueError("Unsupported central pair stretch")
    ranges = [list(range(int(m[2]), int(m[3]) + (1 if int(m[3]) >= int(m[2]) else -1),
                         1 if int(m[3]) >= int(m[2]) else -1)) for m in stretches]
    if len(ranges[0]) != len(ranges[1]):
        raise ValueError("Unbalanced central pair stretch")
    for first, second in zip(*ranges):
        declarations.append({"sites": [stretches[0][1] + ":" + str(first), stretches[1][1] + ":" + str(second)],
                             "resource": "padd", "canonical_saenger_class": None})
    all_sites = [site for row in declarations for site in row["sites"]]
    if len(declarations) != 20 or len(all_sites) != len(set(all_sites)) or not set(all_sites) <= canonical.keys():
        raise ValueError("Packaged pair declarations do not bind twenty disjoint pairs")
    requested = [{"family": family, "sites": list(sites), "components": list(codes), "scope": "requested"}
                 for family, sites, codes in REQUESTED_MAP]
    if tuple(tuple(row["components"]) for row in requested) != REQUESTED_PAIRS:
        raise ValueError("Requested eight-pair chemistry differs from the shared source plan")
    by_pair = {frozenset(row["sites"]): row for row in requested}
    targets = {site: code for row in requested for site, code in zip(row["sites"], row["components"])}
    if len(by_pair) != 8 or len(targets) != 16 or not set(by_pair) <= {frozenset(row["sites"]) for row in declarations}:
        raise ValueError("Requested pairs must bind sixteen unique declared sites")
    full_pairs = []
    for row in declarations:
        selected = by_pair.get(frozenset(row["sites"]))
        sites = selected["sites"] if selected else row["sites"]
        full_pairs.append({"sites": list(sites), "components": [targets.get(site, canonical[site]) for site in sites],
                           "scope": "requested" if selected else "background"})
    stacks = []
    for chain, ids in CHAIN_IDS.items():
        for first, second in zip(ids, ids[1:]):
            if int(second) != int(first) + 1:
                raise ValueError("Undeclared gap in scaffold chain topology")
            stacks.append([chain + ":" + first, chain + ":" + second])
    if len(stacks) != 38:
        raise ValueError("Expected the frozen thirty-eight chain-adjacency relationships")
    intent = {"post_mr_plan": {"mutations": {site: {"ligand_code": code, "requested": code}
                                               for site, code in targets.items()}}}
    actions = build_mutation_plan(intent, paths["template"])
    overlap = [action for action in actions if action.method == "coot-parent-overlap"]
    if (len(actions) != 16 or len(overlap) != 12
            or any(action.before != action.parent_code for action in overlap)
            or any(action.method not in {"none", "coot-parent-overlap"} for action in actions)):
        raise ValueError("Fixture targets do not retain the declared canonical parent routes")
    final_codes = {site: targets.get(site, code) for site, code in canonical.items()}
    letters = {"DA": "A", "DC": "C", "DG": "G", "DT": "T"}
    sequences = {chain: "".join(letters.get(final_codes[chain + ":" + resid], "(" + final_codes[chain + ":" + resid] + ")")
                                  for resid in ids) for chain, ids in CHAIN_IDS.items()}
    return {"schema_version": 1, "policy_id": POLICY_ID, "source_hashes": expected,
            "canonical_site_components": dict(canonical), "target_site_components": final_codes,
            "requested_pairs": requested, "all_pairs": full_pairs, "pair_declarations": declarations,
            "pair_count": 20, "requested_pair_count": 8, "background_pair_count": 12,
            "stack_edges": stacks, "stack_count": 38,
            "stack_authority": "NARESTRAINTS_DECLARED_CONSECUTIVE_CHAIN_POLICY; NOT_OBSERVED_STACKING_GEOMETRY",
            "orientation_controls": [{key: row[key] for key in ("sites", "components", "scope")} for row in requested],
            "orientation_control_count": 16, "orientation_control_scope": "SEPARATE_BOTH_PLANE_ORDERS; NOT_ADDED_TWICE_TO_ACTIVE_POLICY",
            "mutation_actions": [asdict(action) for action in actions], "coot_mutation_count": 12,
            "annotated_sequences": sequences, "atl_scope": "INDEPENDENT_CONTROL_NOT_A_NINTH_PAIR",
            "requires_cif_review": False, "native_proxy_membership": "NOT_ASSESSED",
            "mr_execution": "NOT_RUN", "mtz_used": False, "scientific_qualification": "NOT_ASSESSED"}


def _constructed_codes(path):
    """Inventory literal final identities without imposing canonical residue names."""
    from .cif_construction_provenance import _pdb_inventory
    inventory = _pdb_inventory(Path(path))
    sites = {}
    for key, row in inventory.items():
        site = key[0] + ":" + key[1]
        if key[2] or key[3] or site in sites and sites[site] != row["code"]:
            raise ValueError("Ambiguous constructed site identity")
        sites[site] = row["code"]
    return sites


def audit_mixed_construction(initial_model, result, actions, sources, directory):
    """Audit global preservation plus each established restoration policy.

    Graph sites use the existing independent rigid-fragment auditor. Curated
    substitution/placement sites instead reproduce their explicit existing rule,
    preserving its actual bond intent rather than imposing rigid raw geometry.
    The two kinds of evidence are deliberately reported separately.
    """
    from math import dist
    from .cif_construction_provenance import _pdb_inventory
    from .cif_postmr_construction import (_records, _atoms, audit_construction_context,
                                        audit_postmr_construction)
    from .curated_ligands import CURATED_LIGANDS, dictionary_ideal_bond_length
    from .postmr import _restore_shared_parent_coordinates
    from .postmr_restoration import source_graph_fragment

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    selected = {action.site for action in actions}
    curated = tuple(action for action in actions if (ligand := CURATED_LIGANDS.get(action.after)) is not None
                    and (ligand.atom_substitutions or ligand.ring_substituents))
    curated_sites = {action.site for action in curated}
    raw = Path(result.get("restoration_input") or result["raw_model"])
    final = Path(result["model"])
    initial_inventory, raw_inventory, final_inventory = map(_pdb_inventory, (initial_model, raw, final))
    raw_lines, raw_other = _records(raw)
    final_lines, final_other = _records(final)
    site = lambda key: key[0] + ":" + key[1]
    if len(selected) != len(actions) or raw_lines.keys() != final_lines.keys() or raw_other != final_other:
        raise ValueError("Mixed restoration changed composition or non-coordinate records")
    for key, line in raw_lines.items():
        # Existing curated placement deliberately copies parent occupancy/B as
        # well as XYZ for its declared atoms. Full expected bytes are checked
        # by curated replay below; graph sites retain strict metadata identity.
        offset = 66 if site(key) in curated_sites else 54
        if line[:30] + line[offset:] != final_lines[key][:30] + final_lines[key][offset:]:
            raise ValueError("Mixed restoration changed atom metadata")
        if site(key) not in selected and line != final_lines[key]:
            raise ValueError("Mixed restoration changed an unselected record")
    if ({key: row for key, row in initial_inventory.items() if site(key) not in selected}
            != {key: row for key, row in raw_inventory.items() if site(key) not in selected}):
        raise ValueError("Mixed Coot construction changed unselected coordinates or composition")
    context = None
    if result.get("restoration_input") is not None:
        context = audit_construction_context(initial_model, result["raw_model"], raw, actions, sources,
            result.get("context_receipt") or {}, context_shadow=result.get("context_shadow"),
            parent_models=result["parent_models"])
    curated_expected = {}
    expected_lines = {}
    if curated:
        expected = directory / "curated_rule_replay.pdb"
        curated_expected = _restore_shared_parent_coordinates(raw, expected, curated, result["parent_models"], sources)
        expected_lines, _ = _records(expected)
    rows = []
    def subset(path, requested_site, destination):
        lines = [line for line in Path(path).read_text().splitlines(keepends=True)
                 if line.startswith(("ATOM  ", "HETATM"))
                 and line[21].strip() + ":" + line[22:26].strip() == requested_site]
        if not lines:
            raise ValueError("Missing audit site coordinates")
        destination.write_text("".join(lines) + "END\n")
        return destination
    for action in actions:
        outcome = result["coordinate_restoration"].get(action.site, {})
        if action not in curated:
            folder = directory / action.site.replace(":", "_")
            folder.mkdir()
            report = audit_postmr_construction(
                subset(initial_model, action.site, folder / "initial.pdb"),
                subset(raw, action.site, folder / "restoration_input.pdb"),
                subset(final, action.site, folder / "final.pdb"), (action,), sources,
                result["parent_models"], {action.site: outcome})
            rows.append({**report["sites"][0], "audit_scope": "INDEPENDENT_GRAPH_FRAGMENT_OR_RAW_SITE_AUDIT"})
            continue
        if (outcome.get("status") != "CURATED_DECLARED_PLACEMENT" or curated_expected[action.site] != outcome
                or any(expected_lines[key] != final_lines[key] for key in final_lines if site(key) == action.site)):
            raise ValueError("Curated placement differs from its exact existing rule and receipt")
        before, after = _atoms(raw_inventory, action.site), _atoms(final_inventory, action.site)
        graph = source_graph_fragment(sources[action.after], action.after)
        if (not set(graph["fragment_atoms"]) <= after.keys()
                or any(name not in graph["elements"] or atom["element"] != graph["elements"][name]
                       for name, atom in after.items())):
            raise ValueError("Curated constructed atoms differ from their source graph")
        parent = _atoms(_pdb_inventory(result["parent_models"][action.site]), action.site)
        scaffold = set(graph["scaffold_atoms"]) & after.keys()
        if not scaffold <= parent.keys() or any(after[name]["xyz"] != parent[name]["xyz"] for name in scaffold):
            raise ValueError("Curated scaffold differs from its frozen parent")
        ligand = CURATED_LIGANDS[action.after]
        bonds = []
        for item in ligand.atom_substitutions:
            old = dist(before[item.anchor_atom]["xyz"], before[item.target_atom]["xyz"])
            new = dist(after[item.anchor_atom]["xyz"], after[item.target_atom]["xyz"])
            if not .5 <= old <= 3. or abs(old - new) > .002:
                raise ValueError("Curated substitution changed its declared raw bond length")
            bonds.append({"anchor": item.anchor_atom, "target": item.target_atom,
                          "intent": "PRESERVED_RAW_LENGTH_ON_CANONICAL_PARENT_VECTOR", "raw": old, "final": new})
        for item in ligand.ring_substituents:
            ideal = dictionary_ideal_bond_length(sources[action.after], item.anchor_atom, item.target_atom)
            actual = dist(after[item.anchor_atom]["xyz"], after[item.target_atom]["xyz"])
            if not item.minimum_bond_length <= ideal <= item.maximum_bond_length or abs(actual - ideal) > .002:
                raise ValueError("Curated ring placement differs from its explicit source target")
            bonds.append({"anchor": item.anchor_atom, "target": item.target_atom,
                          "intent": "EXPLICIT_SOURCE_IDEAL_LENGTH", "ideal": ideal, "final": actual})
        rows.append({"site": action.site, "component": action.after, "status": "CURATED_DECLARED_PLACEMENT",
                     "audit_scope": "EXACT_EXISTING_CURATED_RULE_REPLAY_AND_DECLARED_BOND_CHECKS",
                     "raw_fragment_geometry_preservation": "NOT_CLAIMED_FOR_DECLARED_CURATED_PLACEMENT",
                     "scaffold_matches_frozen_parent": True, "declared_bonds": bonds})
    fallbacks = [row["site"] for row in rows if row["status"] == "RAW_SITE_RETAINED"]
    refs = [_artifact(path, directory.parent) for path in sorted(directory.rglob("*")) if path.is_file()]
    return {"status": "CONSTRUCTION_CONTROLS_PASS_WITH_NOTES" if fallbacks else "CONSTRUCTION_CONTROLS_PASS",
            "sites": rows, "raw_fallback_sites": fallbacks, "context_audit": context,
            "global_composition_metadata_and_unselected_coordinates": "PASS",
            "occupancy_temperature_factor_policy": "EXACT_EXISTING_PARENT_REPLAY_FOR_CURATED_PLACEMENTS; GRAPH_AND_UNSELECTED_METADATA_UNCHANGED",
            "graph_site_count": len(actions) - len(curated), "curated_site_count": len(curated),
            "audit_artifacts": refs, "scientific_geometry_qualification": "NOT_ASSESSED"}


def run_mixed_pair_fixture(template, secondary, padd, ready_set_executable, output, *,
                           coot_executable=None, environment=None, coot_version=None,
                           inspect_only=False, timeout_seconds=600):
    """One bounded ordinary Coot construction and explicit NAR policy compilation.

    Source acquisition is read-only; this does not invoke ReadySet, a dictionary
    generator, native interpretation, a geometry optimizer or a production run.
    Optional construction failures retain all evidence and the original template
    as an unqualified input, never as a successful mixed-chemistry result.
    """
    from .cif_acquisition import audit_ordinary_acquisition
    from .curated_ligands import ligand_source, validate_ligand_dictionary
    from .postmr import MutationAction, construct_postmr_model
    from .postmr_restoration import source_graph_fragment
    from .synthetic_dna import prepare_free_five_prime_model

    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600 or type(inspect_only) is not bool:
        raise ValueError("Require an integer Coot deadline from 1 to 600 seconds and a boolean inspect-only mode")
    output = Path(output).absolute()
    if output.exists() or output.is_symlink() or any(path.is_symlink() for path in output.parents):
        raise ValueError("Require a fresh owned fixture directory without symlink traversal")
    source_paths = {"template": Path(template), "secondary": Path(secondary), "padd": Path(padd)}
    snapshots = {key: path.read_bytes() for key, path in source_paths.items()}
    plan = build_mixed_pair_plan(template, secondary, padd)
    output.mkdir(parents=True)
    inputs = output / "inputs"
    inputs.mkdir()
    input_refs = {}
    for key, suffix in (("template", ".pdb"), ("secondary", ".eff"), ("padd", ".txt")):
        destination = inputs / (key + suffix)
        destination.write_bytes(snapshots[key])
        input_refs[key] = _artifact(destination, output)
    free, removed = prepare_free_five_prime_model(snapshots["template"])
    model = inputs / "canonical_free_5oh.pdb"
    model.write_bytes(free)
    input_refs["canonical_free_5oh"] = _artifact(model, output)
    _write_json(output / "construction_plan.json", plan)
    report = {"schema_version": 1, "policy_id": POLICY_ID, "status": "PREPARED_ONLY",
              "plan": plan, "inputs": input_refs, "plan_file": _artifact(output / "construction_plan.json", output),
              "five_prime_atoms_removed": removed, "analysis_completed": False,
              "coot": {"execution": "NOT_RUN", "version": coot_version, "timeout_seconds": timeout_seconds},
              "ordinary_construction_api": "nasolve.postmr.construct_postmr_model",
              "ordinary_source_api": "nasolve.curated_ligands.ligand_source",
              "source_bindings": {}, "outputs": {}, "parent_models": {},
              "construction_audit": {"status": "NOT_RUN"}, "policy_compilation": {"status": "NOT_RUN"},
              "decision": {"status": "NOT_ASSESSED", "selected": None, "requires_cif_review": False},
              "mr_execution": "NOT_RUN", "mtz_used": False, "readyset_execution": "NOT_RUN",
              "native_execution": "NOT_RUN", "native_proxy_membership": "NOT_ASSESSED",
              "dictionary_generation": "NOT_RUN",
              "model_optimization": "NOT_REQUESTED; COOT_INTERNALS_NOT_EXHAUSTIVELY_INSTRUMENTED", "refinement": "NOT_RUN",
              "production_checkpoint": "NOT_CREATED", "automatic_adoption": False,
              "requires_cif_review": False, "scientific_qualification": "NOT_ASSESSED",
              "auxiliary_Coot_backups": "OPAQUE_DIAGNOSTICS_ONLY; EXISTING_REVIEW_TRANSPORT; NOT_SCIENTIFIC_REFERENCES"}
    original_failure = None
    try:
        acquisition = audit_ordinary_acquisition(ready_set_executable, output / "acquisition",
                                               store_root=output / "unused_dictionary_store")
        report["acquisition"] = acquisition
        report["acquisition_file"] = _artifact(output / "acquisition/acquisition.json", output)
        if acquisition["status"] != "ORDINARY_ACQUISITION_CONTROLS_PASS":
            raise ValueError("Ordinary requested-component source acquisition did not pass")
        sources = {}
        for code, row in acquisition["sources"].items():
            path = output / "acquisition" / row["source"]["path"]
            sources[code] = path
            report["source_bindings"][code] = {"scope": "requested", "authority": row["authority"], "source": _artifact(path, output)}
            original = Path(row["historical_source_path"])
            source_paths[code] = original
            snapshots[code] = path.read_bytes()
        selected = ligand_source("DC", ready_set_executable=Path(ready_set_executable))
        validate_ligand_dictionary("DC", selected.path)
        path = inputs / "background_DC.cif"
        path.write_bytes(selected.path.read_bytes())
        sources["DC"] = path
        source_paths["DC"] = selected.path
        snapshots["DC"] = path.read_bytes()
        report["source_bindings"]["DC"] = {"scope": "background", "authority": selected.authority, "source": _artifact(path, output)}
        report["source_counts"] = {"requested": 15, "background": 1}
        actions = tuple(MutationAction(**row) for row in plan["mutation_actions"] if row["method"] != "none")
        report["source_graph_eligibility"] = {action.after: source_graph_fragment(sources[action.after], action.after) for action in actions}
        if not inspect_only:
            if coot_executable is None:
                raise ValueError("A validated Coot executable is required for construction")
            report["coot"]["execution"] = "RUNNING"
            result = construct_postmr_model(model, actions, sources, output / "model/constructed_model.pdb",
                                           coot_executable=Path(coot_executable), environment=environment,
                                           timeout_seconds=timeout_seconds)
            report["coot"]["execution"] = "COMPLETED"
            if result.get("raw_model") is None:
                raise ValueError("Fresh construction lacks raw Coot evidence")
            for key in ("model", "raw_model", "geometry_model", "coot_log", "restoration_input", "context_shadow",
                        "context_sanitized_shadow", "context_rechecked_model"):
                if result.get(key) is not None:
                    report["outputs"][key] = _artifact(result[key], output)
            report["parent_models"] = {site: _artifact(path, output) for site, path in result["parent_models"].items()}
            report["coordinate_restoration"] = result["coordinate_restoration"]
            report["context_receipt"] = result.get("context_receipt")
            audit = audit_mixed_construction(model, result, actions, sources, output / "construction_audit")
            report["construction_audit"] = audit
            if audit["status"] not in {"CONSTRUCTION_CONTROLS_PASS", "CONSTRUCTION_CONTROLS_PASS_WITH_NOTES"}:
                raise ValueError("Ordinary construction audit did not pass")
            if _constructed_codes(result["model"]) != plan["target_site_components"]:
                raise ValueError("Constructed model does not contain all exact forty-two intended identities")
            from .cif_explicit_na_policy import compile_explicit_na_policy
            policy = compile_explicit_na_policy(result["model"], plan["all_pairs"],
                [tuple(row) for row in plan["stack_edges"]], sources, output / "explicit_policy",
                orientation_controls=plan["orientation_controls"])
            report["policy_compilation"] = policy
            if (policy["status"] != "EXPLICIT_NA_POLICY_COMPILED" or policy["pair_count"] != 20
                    or policy["requested_pair_count"] != 8 or policy["stack_count"] != 38
                    or policy["orientation_control_count"] != 16):
                raise ValueError("Constructed explicit policy scope is incomplete")
            report["status"] = "MIXED_PAIR_CONSTRUCTION_PASS_WITH_NOTES" if audit["raw_fallback_sites"] else "MIXED_PAIR_CONSTRUCTION_PASS"
            report["decision"] = {"status": "CONTINUE_WITH_NOTES", "selected": "constructed_mixed_model",
                "requires_cif_review": False, "automatic_adoption": False,
                "notes": ["Construction and compiler evidence only; native proxy membership and the diffraction run remain separate."]}
        report["source_inputs_preserved"] = all(path.read_bytes() == snapshots[key] for key, path in source_paths.items())
        if not report["source_inputs_preserved"]:
            raise ValueError("Fixture construction changed a frozen source input")
        for row in report["source_bindings"].values():
            _read_artifact(output, row["source"])
        report["analysis_completed"] = True
    except Exception as exc:
        original_failure = exc
        report.update(status="MIXED_PAIR_CONSTRUCTION_REVIEW", analysis_completed=False,
                      error_type=type(exc).__name__, error=str(exc))
        if report["coot"]["execution"] == "RUNNING":
            report["coot"]["execution"] = "FAILED"
        try:
            report["source_inputs_preserved"] = all(path.read_bytes() == snapshots[key] for key, path in source_paths.items())
        except OSError:
            report["source_inputs_preserved"] = False
        report["decision"] = {"status": "NO_QUALIFIED_MIXED_MODEL", "selected": None,
            "requires_cif_review": False, "original_template_retained": True,
            "notes": ["The preserved canonical template is an unqualified construction input, not the requested mixed chemistry."]}
    try:
        # Existing source/placement APIs may expose dataclass tuples. Freeze the
        # same JSON value that a relocated reader returns, without changing any
        # operational source/model/PHIL bytes.
        report = json.loads(json.dumps(report, allow_nan=False))
        _write_json(output / "mixed_pair_fixture.json", report)
    except Exception as reporting_error:
        if original_failure is not None:
            detail = {"error_type": type(reporting_error).__name__, "error": str(reporting_error)}
            original_failure.fixture_reporting_error = detail
            if hasattr(original_failure, "add_note"):
                original_failure.add_note("Fixture reporting also failed: " + detail["error_type"] + ": " + detail["error"])
            raise original_failure from None
        raise
    return report


def _read_mixed_pair_fixture(directory):
    """Resolve frozen scientific references after relocation, without host reads.

    This verifies evidence integrity and declared identities, not native mechanics.
    Opaque Coot backups are transported separately and never consumed here.
    """
    root = Path(directory)
    if any(path.is_symlink() for path in [root, *root.parents]):
        raise ValueError("Unsafe fixture directory")
    report_path = root / "mixed_pair_fixture.json"
    if report_path.is_symlink():
        raise ValueError("Fixture report cannot be a symlink")
    report = json.loads(report_path.read_bytes())
    if report.get("policy_id") != POLICY_ID or report.get("requires_cif_review") is not False:
        raise ValueError("Fixture report policy differs")
    if (report.get("status") not in {"PREPARED_ONLY", "MIXED_PAIR_CONSTRUCTION_PASS", "MIXED_PAIR_CONSTRUCTION_PASS_WITH_NOTES", "MIXED_PAIR_CONSTRUCTION_REVIEW"}
            or any(report.get(key) != "NOT_RUN" for key in ("mr_execution", "readyset_execution", "native_execution", "dictionary_generation", "refinement"))
            or report.get("native_proxy_membership") != "NOT_ASSESSED" or report.get("mtz_used") is not False
            or report.get("production_checkpoint") != "NOT_CREATED" or report.get("automatic_adoption") is not False):
        raise ValueError("Fixture report claims an unsupported execution or adoption")
    refs = report["inputs"]
    for ref in [report["plan_file"], *refs.values(), *report["outputs"].values(),
                *report["parent_models"].values(), *(row["source"] for row in report["source_bindings"].values()),
                *report["construction_audit"].get("audit_artifacts", [])]:
        _read_artifact(root, ref)
    plan = build_mixed_pair_plan(*(root / refs[key]["path"] for key in ("template", "secondary", "padd")))
    if report["plan"] != plan or json.loads((root / report["plan_file"]["path"]).read_bytes()) != plan:
        raise ValueError("Frozen fixture plan differs")
    if "acquisition_file" in report:
        acquisition_file = _read_artifact(root, report["acquisition_file"])
        if json.loads(acquisition_file.read_bytes()) != report["acquisition"]:
            raise ValueError("Frozen source acquisition report differs")
    from .synthetic_dna import prepare_free_five_prime_model
    free, removed = prepare_free_five_prime_model((root / refs["template"]["path"]).read_bytes())
    if free != (root / refs["canonical_free_5oh"]["path"]).read_bytes() or removed != report["five_prime_atoms_removed"]:
        raise ValueError("Frozen free-hydroxyl construction input differs")
    if report["policy_compilation"].get("status") == "EXPLICIT_NA_POLICY_COMPILED":
        from .cif_explicit_na_policy import read_explicit_na_policy
        if read_explicit_na_policy(root / "explicit_policy") != report["policy_compilation"]:
            raise ValueError("Frozen explicit policy differs")
    if report["status"].startswith("MIXED_PAIR_CONSTRUCTION_PASS"):
        if (report.get("analysis_completed") is not True or report["coot"]["execution"] != "COMPLETED" or report.get("source_inputs_preserved") is not True
                or report["construction_audit"]["status"] not in {"CONSTRUCTION_CONTROLS_PASS", "CONSTRUCTION_CONTROLS_PASS_WITH_NOTES"}
                or _constructed_codes(root / report["outputs"]["model"]["path"]) != plan["target_site_components"]
                or report["policy_compilation"].get("status") != "EXPLICIT_NA_POLICY_COMPILED"):
            raise ValueError("Incomplete completed fixture evidence")
    return report


def read_mixed_pair_fixture(directory):
    """Verify portable scientific evidence; never consult historical sources."""
    try:
        return _read_mixed_pair_fixture(directory)
    except (KeyError, TypeError, AttributeError, OSError) as exc:
        raise ValueError("Incomplete or invalid mixed-pair fixture evidence") from exc
