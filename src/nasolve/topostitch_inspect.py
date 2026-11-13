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


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="nasolve-topostitch-inspect",
        description="Inspect explicitly assigned DNA ends; print proposals without changing models.")
    parser.add_argument("model",type=Path,help="Exact single-model PDB path")
    parser.add_argument("assignments",type=Path,help="Schema-1 end assignments bound to the model SHA-256")
    parser.add_argument("--radius",required=True,type=float,help="Explicit endpoint search radius in Angstrom")
    parser.add_argument("--periodic",action="store_true",help="Search CRYST1 symmetry images (requires NASolve[topology])")
    parser.add_argument("--max-pairs",type=int,default=100_000,help="Maximum endpoint-pair budget")
    parser.add_argument("--max-image-tests",type=int,default=100_000,help="Periodic translation-box test budget")
    args = parser.parse_args(argv)
    try:
        if args.max_image_tests < 1:
            raise ValueError("max-image-tests must be a positive integer")
        digest,assignments,manifest_hash = load_end_assignments(args.assignments)
        options = dict(expected_sha256=digest,max_distance_angstrom=args.radius,max_pairs=args.max_pairs)
        if args.periodic:
            report = inspect_periodic_end_assignments(args.model,assignments,
                max_image_tests=args.max_image_tests,**options)
        else:
            report = inspect_end_assignments(args.model,assignments,**options)
        report["assignment_file_sha256"] = manifest_hash
        output = json.dumps(report,indent=2,sort_keys=True,allow_nan=False)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(2, f"{parser.prog}: {exc}\n")
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
