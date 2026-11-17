"""Read-only command surface for the TopoStitch proposal backends.

This separate entry point deliberately avoids the active campaign/PostMR CLI.
It prints a descriptive report and never writes models, registries or recipes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from .topostitch_coordinates import EndAssignment, ResidueSite, inspect_end_assignments
from .topostitch_periodic import inspect_periodic_end_assignments


def _unique_object(pairs):
    value = {}
    for key,item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value)-set(required)-set(optional):
        raise ValueError(f"Expected object fields {', '.join(sorted(required))}; unknown fields are not accepted")


def _site(value):
    _keys(value, {"chain","residue_number"}, {"insertion_code"})
    return ResidueSite(**value)


def load_end_assignments(path: Path):
    """Read schema-1 explicit coordinate assignments, bound to model bytes.

    Returns the expected model digest, immutable assignment records and exact
    manifest byte digest. This is topology intent, not scientific approval.
    """
    data = Path(path).read_bytes()
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    _keys(value, {"schema_version","kind","model_sha256","ends"})
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["kind"] != "topostitch-end-assignments":
        raise ValueError("Unsupported TopoStitch assignment manifest kind/schema")
    digest = value["model_sha256"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}",digest) is None:
        raise ValueError("model_sha256 must be an exact lowercase SHA-256 digest")
    if not isinstance(value["ends"],list):
        raise ValueError("ends must be an array of explicit assignments")
    assignments = []
    for row in value["ends"]:
        _keys(row, {"end_id","overhang_sites","terminal_pair","inner_pair","polarity"}, {"state"})
        sites = {}
        for key in ("overhang_sites","terminal_pair","inner_pair"):
            if not isinstance(row[key],list):
                raise ValueError(f"{key} must be an array of coordinate sites")
            sites[key] = tuple(_site(v) for v in row[key])
        assignments.append(EndAssignment(row["end_id"],polarity=row["polarity"],
                                        state=row.get("state","available"),**sites))
    return digest,tuple(assignments),sha256(data).hexdigest()


def load_registered_end_assignments(model, path, registration_path):
    from .topostitch_registration import LogicalEndAssignment, resolve_registered_ends
    data = Path(path).read_bytes()
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("--registration requires a schema-1 logical or discovery manifest")
    discovery = None
    if value.get("kind") == "topostitch-logical-end-assignments":
        _keys(value, {"schema_version", "kind", "model_sha256", "registration_sha256", "ends"})
        if not isinstance(value["ends"], list):
            raise ValueError("ends must be an array of logical assignments")
        logical = []
        for row in value["ends"]:
            _keys(row, {"end_id", "copy_id", "overhang_sites", "terminal_pair", "inner_pair", "polarity"}, {"state"})
            logical.append(LogicalEndAssignment(**row))
    elif value.get("kind") == "topostitch-end-discovery-input":
        from .topostitch_discovery import BackboneStrand, discover_logical_end_assignments
        _keys(value, {"schema_version", "kind", "model_sha256", "registration_sha256", "copy_id", "strands", "duplex_pairs"},
              {"protected_sites", "max_overhang_length", "pairing_inventory_complete", "do_not_connect_sites"})
        if not isinstance(value["strands"], list) or not isinstance(value["duplex_pairs"], list):
            raise ValueError("strands and duplex_pairs must be arrays")
        strands = []
        for strand in value["strands"]:
            _keys(strand, {"strand_id", "sites", "five_prime_boundary", "three_prime_boundary"})
            strands.append(BackboneStrand(**strand))
        logical, discovery = discover_logical_end_assignments(strands,value["duplex_pairs"],
            copy_id=value["copy_id"],protected_sites=value.get("protected_sites",()),
            max_overhang_length=value.get("max_overhang_length",12),
            pairing_inventory_complete=value.get("pairing_inventory_complete",False),
            do_not_connect_sites=value.get("do_not_connect_sites",()))
    else:
        raise ValueError("--registration requires a logical end-assignment or end-discovery manifest")
    registration_data = Path(registration_path).read_bytes()
    registration_hash = sha256(registration_data).hexdigest()
    if value["registration_sha256"] != registration_hash:
        raise ValueError("Registration file checksum mismatch")
    registration = json.loads(registration_data.decode("utf-8"), object_pairs_hook=_unique_object)
    assignments, mapping = resolve_registered_ends(model, logical, registration,
        expected_sha256=value["model_sha256"])
    if discovery is not None:
        # Validate even unassigned routes against the selected registration;
        # otherwise a typo in an unresolved region could silently disappear.
        if value["copy_id"] not in {c["copy_id"] for c in registration["copies"]}:
            raise ValueError("Unknown registered copy in discovery input")
        known = set(registration["target"]["sites"])
        if any(site not in known for strand in strands for site in strand.sites):
            raise ValueError("Unknown logical site in discovery strand")
        mapping["discovery_assessment"] = discovery
        mapping["coverage_complete"] = mapping["coverage_complete"] and discovery["coverage_complete"]
    mapping["registration_file_sha256"] = registration_hash
    return value["model_sha256"], assignments, sha256(data).hexdigest(), mapping


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="nasolve-topostitch-inspect",
        description="Inspect explicitly assigned DNA ends; print proposals without changing models.")
    parser.add_argument("model",type=Path,help="Exact single-model PDB path")
    parser.add_argument("assignments",type=Path,help="Checksum-bound coordinate, logical or discovery manifest")
    parser.add_argument("--registration",type=Path,help="Exact construct-registration JSON for a logical or discovery manifest")
    parser.add_argument("--radius",required=True,type=float,help="Explicit endpoint search radius in Angstrom")
    parser.add_argument("--periodic",action="store_true",help="Search CRYST1 symmetry images (requires NASolve[topology])")
    parser.add_argument("--contacts",action="store_true",help="Measure canonical NARestraints contacts without accepting a pairing")
    parser.add_argument("--pairings",action="store_true",help="Enumerate bounded one-partner alternatives without selecting a scheme")
    parser.add_argument("--max-alternatives",type=int,default=256,help="Maximum alternatives per independent pairing group")
    parser.add_argument("--max-pairing-states",type=int,default=100_000,help="Maximum total pairing search states")
    parser.add_argument("--windows",action="store_true",help="Propose bounded editable windows from a discovery manifest")
    parser.add_argument("--max-window-pairs",type=int,default=12,help="Maximum paired window length")
    parser.add_argument("--fixed-anchor-pairs",type=int,default=2,help="Innermost fixed pairs in each window")
    parser.add_argument("--max-pairs",type=int,default=100_000,help="Maximum endpoint-pair budget")
    parser.add_argument("--max-image-tests",type=int,default=100_000,help="Periodic translation-box test budget")
    parser.add_argument("--audit-image",type=int,help="Audit present atom identities for one periodic candidate index")
    parser.add_argument("--coincidence-tolerance",type=float,default=.01,help="Atom coincidence observation tolerance in Angstrom (at most 0.05)")
    parser.add_argument("--max-atom-tests",type=int,default=2_000_000,help="Selected atom-image audit work budget")
    args = parser.parse_args(argv)
    try:
        if min(args.max_image_tests,args.max_alternatives,args.max_pairing_states) < 1:
            raise ValueError("Search budgets must be positive integers")
        if args.audit_image is not None and not args.periodic:
            raise ValueError("--audit-image requires --periodic")
        mapping = None
        if args.registration is not None:
            digest,assignments,manifest_hash,mapping = load_registered_end_assignments(
                args.model,args.assignments,args.registration)
        else:
            digest,assignments,manifest_hash = load_end_assignments(args.assignments)
        options = dict(expected_sha256=digest,max_distance_angstrom=args.radius,max_pairs=args.max_pairs)
        if args.windows and (mapping is None or "discovery_assessment" not in mapping):
            raise ValueError("--windows requires a registered end-discovery manifest")
        if args.contacts:
            from .topostitch_contacts import inspect_end_contacts
            report = inspect_end_contacts(args.model,assignments,periodic=args.periodic,
                max_image_tests=args.max_image_tests,**options)
        elif args.periodic:
            report = inspect_periodic_end_assignments(args.model,assignments,
                max_image_tests=args.max_image_tests,**options)
        else:
            report = inspect_end_assignments(args.model,assignments,**options)
        if args.audit_image is not None:
            from .topostitch_images import _attach_image_audit
            _attach_image_audit(args.model,assignments,report,candidate_index=args.audit_image,
                coincidence_tolerance_angstrom=args.coincidence_tolerance,max_atom_tests=args.max_atom_tests)
        if args.pairings:
            from .topostitch_pairings import describe_pairing_alternatives
            screening = report["periodic_screening"] if args.periodic else report["screening"]
            report["pairing_alternatives"] = describe_pairing_alternatives(screening,
                max_alternatives_per_component=args.max_alternatives,
                max_search_states=args.max_pairing_states)
        if args.windows:
            from .topostitch_discovery import plan_editable_windows
            report["editable_windows"] = plan_editable_windows(mapping["discovery_assessment"],
                max_base_pairs=args.max_window_pairs,fixed_anchor_pairs=args.fixed_anchor_pairs)
        if mapping is not None:
            report["registration_assessment"] = mapping
            if not mapping["coverage_complete"]:
                report["workflow"]["proposal_state"] = "INCOMPLETE_ASSESSMENT"
        report["assignment_file_sha256"] = manifest_hash
        output = json.dumps(report,indent=2,sort_keys=True,allow_nan=False)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(2, f"{parser.prog}: {exc}\n")
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
