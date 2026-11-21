"""Compare actual Phenix parent chemistry with the original typed observation.

Phenix reduces an effective residue dictionary to a small mapping summary
during normal refinement. Observe that return on the calling thread, then
join the original objects to the exact summaries retained by this manager.
Only compact comparison results outlive the call.
"""
from contextlib import contextmanager
from functools import lru_cache
import json
import math
from pathlib import Path
import sys
from textwrap import dedent, indent
from types import SimpleNamespace

from . import cif_native_validation as native
from .cif_na_policy import POLICY_ID, _qualify_observed_fields, _signature
from .cif_native_parent import NativeParentInterpretation, _canonical, _checked_bytes, _digest, _require

_PROXY_FAMILIES = {"bond_simple", "bond_asu", "angle", "dihedral", "const_dihedral",
                   "chirality", "planarity", "parallelity"}
_PROXY_STATUS_FAMILIES = _PROXY_FAMILIES - {"bond_simple", "bond_asu"}
_COMPONENT_CATEGORIES = {"atoms", "bonds", "angles", "torsions", "chirality", "plane_atoms"}
_INTERPRETER_SHA = "6b9c8ad96e521b933d4bf02c626598378efe731542d4e34b8433b1af1e3c3235"


class NativeParentChemistryMismatch(ValueError):
    """Compact comparison details for a failed model that must be discarded."""

    def __init__(self, checks, sites, restraints):
        self.differences = {"checks": checks, "component_sites": sites, "restraint_families": restraints}
        super().__init__("Source chemistry or compiled restraints differ: " + ", ".join((checks + sites)[:12]))


def _restraint_difference(check, original, current):
    """Describe a unique same-atom example after the existing policy comparison fails."""
    def by_identity(rows):
        unique = {}
        for row in rows:
            key = _canonical([row["origin_id"], row["atoms"], row.get("j_atoms"), row.get("symmetry_operation")])
            unique[key] = None if key in unique else row
        return unique

    old = by_identity(original)
    changed = [(old[k], row) for k, row in by_identity(current).items()
               if row is not None and old.get(k) is not None and row != old[k]]
    example = None
    if changed:
        earlier, row = changed[0]
        example = {"atoms": row["atoms"], "parameters": {
            k: {"source": earlier.get(k), "live": row.get(k)} for k in sorted(earlier.keys() | row.keys())
            if earlier.get(k) != row.get(k)}}
    return {"missing": check["missing"], "extra": check["extra"],
            "unmatched_requests": len(check["unmatched_requests"]),
            "changed_with_identical_atoms_and_origin": len(changed), "first_example": example}


def _source_observation(bound, pin, data):
    raw = bound.source_report_json
    _require(type(raw) is bytes and _digest(raw) == pin, "Original typed compiler report differs")
    report = json.loads(raw)
    _require(_canonical(report) == raw and report["policy_id"] == "cif-typed-native-literal-inputs-v1",
             "Require the original typed compiler report")
    records = [r for r in report["files"] if r.get("anchor") == "literal_na_input_directory"
               and r.get("path") == "native/native_validation.json"]
    _require(len(records) == 1, "Missing or repeated original native observation")
    _checked_bytes(data, records[0])
    before = json.loads(data)
    _require(before["status"] == "REVIEW" and before["inventory_detail"] == "linked"
             and before["fatal_problems"] is None and before["unsupported_fields"] == []
             and before["unused_definitions"] == [], "Incomplete original native observation")
    policy = report["compilation"]
    _require(policy["policy_id"] == POLICY_ID and policy["policy_authority"] == "NARestraints",
             "Require the original compiled NARestraints policy")
    return before, policy


@contextmanager
def _capture_returns(method):
    _require(sys.getprofile() is None, "An existing thread profiler owns this observation point")
    code = method.__code__
    pairs = []

    def observe(frame, event, value):
        if event == "return" and frame.f_code is code:
            pairs.append((frame.f_locals["self"], value))

    sys.setprofile(observe)
    try:
        yield pairs
        _require(sys.getprofile() is observe, "Lost ownership of the native mapping observation")
    except BaseException:
        pairs.clear()
        raise
    finally:
        # Leave a foreign owner and an in-flight native exception intact.
        if sys.getprofile() is observe:
            sys.setprofile(None)


def _matching_mappings(pairs, summaries):
    _require(pairs and len(pairs) == len(summaries)
             and all(summary is observed for (_, observed), summary in zip(pairs, summaries))
             and len({id(mm) for mm, _ in pairs}) == len(pairs)
             and len({id(s) for s in summaries}) == len(summaries),
             "Observed residue summaries do not belong to this interpretation")
    return [mm for mm, _ in pairs]


@lru_cache(maxsize=1)
def _component_reader():
    # Extract the same package-owned readers as the sealed standalone worker.
    # No executable code comes from the scientific input or its report.
    source = native._NATIVE_WORKER
    _require(_digest(source.encode()) == native._LIVE_WORKER_SHA256, "Changed native component reader")
    metadata = source[source.index("def monomer_metadata("):source.index("\ntry:\n")]
    start = source.index('    rows = []\n    if hasattr(acp, "all_monomer_mappings"):')
    rows = dedent(source[start:source.index("    save()", start)])
    body = ('spec = {"inventory_detail": "linked"}\nreport = {"unsupported_fields": []}\n'
            + metadata + "\n" + rows + '\nreturn report')
    namespace = {}
    exec(compile("def read(acp):\n" + indent(body, "    "), "<NASolve installed component reader>", "exec"),
         namespace)
    return namespace["read"]


def _compare(before, live, components, policy):
    rows = components["rows"]
    _require(components["status"] == "RECORDED" and rows and live["unsupported_fields"] == []
             and before["atom_count"] == live["atom_count"] == len(live["atoms"]) > 0,
             "Incomplete active parent chemistry")
    for row in rows:
        meta = row["metadata"]
        _require(row["literal_identity"]["status"] == meta["status"] == "RECORDED"
                 and set(meta["effective_definition"]) == _COMPONENT_CATEGORIES
                 and all(isinstance(r, list) for r in meta["effective_definition"].values()),
                 "Incomplete effective component definition at " + row["site"])
    for observation in (before, live):
        geo = observation["geometry"]
        _require(set(geo["proxy_details"]) == set(geo["proxy_counts"]) == _PROXY_FAMILIES
                 and set(geo["proxy_count_status"]) == _PROXY_STATUS_FAMILIES
                 and all(v == "RECORDED" for v in geo["proxy_count_status"].values())
                 and all(isinstance(geo["proxy_details"][k], list)
                         and geo["proxy_counts"][k] == len(geo["proxy_details"][k]) for k in _PROXY_FAMILIES),
                 "Incomplete native restraint families")
    origins = before["restraint_policy"]["origin_ids"]
    _require(origins == live["restraint_policy"]["origin_ids"], "Native restraint origin registry changed")
    observed = dict(live, monomer_mappings=components)
    qualification = _qualify_observed_fields(before, observed, policy, [])
    failures = [r for r in qualification["checks"] if r["status"] != "PASS"]
    if failures:
        names = [r["check"] for r in failures]
        old_components = {r["site"]: r for r in before["monomer_mappings"]["rows"]}
        new_components = {r["site"]: r for r in rows}
        sites = sorted(k for k in old_components.keys() | new_components.keys()
                       if old_components.get(k) != new_components.get(k))
        changes = {}
        if "atom-identities" not in names:
            for check in failures:
                if check["check"].startswith("exact-proxies:"):
                    kind = check["check"].split(":", 1)[1]
                    changes[kind] = _restraint_difference(check, before["geometry"]["proxy_details"][kind],
                                                          live["geometry"]["proxy_details"][kind])
        raise NativeParentChemistryMismatch(names, sites, changes)
    # These are two reads of the same input coordinates. Keep six decimals,
    # well below the PDB file's 0.001 Å coordinate precision.
    displacements = [math.dist(a["xyz"], b["xyz"]) for a, b in zip(before["atoms"], live["atoms"])]
    _require(all(math.isfinite(d) and d <= 1.e-6 for d in displacements),
             "Native coordinates differ from the bound parent")
    # The compiler emits an ordinary quadratic parallelity with no slack.
    # The original C21 comparison already verified each target, weight and atom selection.
    generated = {_signature("parallelity", r, values=False) for r in policy["compiled_requests"]
                 if r["kind"] == "parallelity"}
    for r in live["geometry"]["proxy_details"]["parallelity"]:
        if r["origin_id"] == origins["edits"] and _signature("parallelity", r, values=False) in generated:
            _require(r.get("slack") == 0.0 and r.get("top_out") is False,
                     "Compiled plane parallelity has a different slack or top-out")
    automatic = {value for name, value in origins.items() if name != "edits"}
    families = {}
    for name, source_rows in before["geometry"]["proxy_details"].items():
        retained = sum(r["origin_id"] not in automatic for r in source_rows)
        families[name] = {"unchanged": retained, "source_secondary_structure": len(source_rows) - retained,
                          "compiled_relationships": len(live["geometry"]["proxy_details"][name]) - retained}
    missing_charge = [r["site"] for r in rows if
        r["metadata"]["formal_charge_readback"]["status"] != "SUPPORTED"
        or r["metadata"]["formal_charge_readback"].get("null_value_atoms")]
    return {"policy_id": "cif-live-parent-source-chemistry-v1", "status":"MATCH", "residues":len(rows),
            "site_definitions_sha256":_digest(_canonical(components)), "proxy_families":families,
            "largest_source_coordinate_difference_A":max(displacements),
            "sites_without_full_formal_charge_readback":missing_charge, "scientific_acceptance":False}


def compare_parent_chemistry(service, model, bound, pin, options, source_native_json):
    """Observe one ordinary service call under its outer ownership and cleanup."""
    from mmtbx.monomer_library import pdb_interpretation
    before, policy = _source_observation(bound, pin, source_native_json)
    # The selected-site observer may now own the class binding. It returns
    # the real summary unchanged. Observe the original method inside it.
    summary = service._api.monomer_summary
    _require(_digest(Path(pdb_interpretation.__file__).read_bytes()) == _INTERPRETER_SHA
             and getattr(summary, "__qualname__", None) == "monomer_mapping.summary"
             and summary.__globals__ is vars(pdb_interpretation)
             and Path(summary.__code__.co_filename).resolve() == Path(pdb_interpretation.__file__).resolve(),
             "Unqualified native monomer summary")
    with _capture_returns(summary) as pairs:
        result = service._interpret(model, bound, pin, options)
    chain = result.processed.all_chain_proxies
    try:
        _require(chain.fatal_problems_message() is None, "Native parent has a fatal interpretation problem")
        mappings = _matching_mappings(pairs, chain.all_monomer_mappings)
        raw = _component_reader()(SimpleNamespace(all_monomer_mappings=mappings))
        _require(not raw["unsupported_fields"], "Incomplete native component mapping")
    finally:
        pairs.clear()
    live = native.collect_live_geometry(model, processed=result.processed)["native_view"]
    comparison = _compare(before, live, raw["monomer_mappings"], policy)
    comparison["source_native_sha256"] = _digest(source_native_json)
    return NativeParentInterpretation(result.processed, result.native_result,
                                      dict(result.receipt, source_chemistry=comparison))
