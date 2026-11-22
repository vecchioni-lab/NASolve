"""Read the recorded covalent terms at chemically matched, intact O3′–P links."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from .cif_attachment_native import _capture, _native_atoms
from .cif_native_parent_chemistry import _COMPONENT_CATEGORIES, _PROXY_FAMILIES, _PROXY_STATUS_FAMILIES
from .cif_native_target_comparison import _mappings
from .cif_terminal_qualification import _bound_proxy_endpoints


def _packed(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _chemistry(mapping):
    meta, mods = mapping["metadata"], mapping["chem_mod_ids"]
    body = meta["effective_definition"]
    if (meta.get("status") != "RECORDED" or mods.get("status") != "RECORDED"
            or not isinstance(mods.get("ids"), list) or set(body) != _COMPONENT_CATEGORIES
            or not all(isinstance(rows, list) for rows in body.values()) or not body["atoms"]):
        raise ValueError("Incomplete effective monomer chemistry at " + mapping["site"])
    return sha256(_packed([mapping["resname"], sorted(mods["ids"]), body]).encode()).hexdigest()


def _recorded_parameters(kind, row, atom_count):
    parameters = {k:v for k,v in row.items() if k not in {"i_seqs", "j_seqs", "atoms", "j_atoms", "origin_id"}}
    ideals = {"bond_simple":"distance_ideal", "bond_asu":"distance_ideal", "angle":"angle_ideal",
              "dihedral":"angle_ideal", "const_dihedral":"angle_ideal", "chirality":"volume_ideal",
              "parallelity":"target_angle_deg"}
    weights = parameters.get("weights") if kind == "planarity" else [parameters.get("weight")]
    if (not isinstance(weights, list) or len(weights) != (atom_count if kind == "planarity" else 1)
            or any(type(w) not in (int, float) or not isfinite(w) or w < 0 for w in weights)):
        raise ValueError("Incomplete recorded weights for " + kind)
    if kind != "planarity":
        ideal = parameters.get(ideals[kind])
        if type(ideal) not in (int, float) or not isfinite(ideal):
            raise ValueError("Incomplete recorded target for " + kind)
    if kind in ("dihedral", "const_dihedral") and type(parameters.get("periodicity")) is not int:
        raise ValueError("Missing recorded torsion periodicity")
    if kind == "chirality" and type(parameters.get("both_signs")) is not bool:
        raise ValueError("Missing recorded chirality sign policy")
    return parameters


def reference_link_terms(native, *, phosphate, o3):
    """Group reference links by their recorded terms. No restraints are proposed.

    Require an observed, positive, ordinary covalent O3′–P bond between distinct
    sites. Exclude the queried pair, keeping it independent of its references.
    Preserve signed atom order for torsions and chirality, duplicate terms and
    zero weights. Terms reaching a third residue are outside this comparison.
    """
    mappings = _mappings(native)
    if phosphate not in mappings or o3 not in mappings:
        raise ValueError("Queried phosphate or O3' site is absent from the native capture")
    wanted_codes = {mappings[phosphate]["resname"], mappings[o3]["resname"]}
    chemistry = {site: _chemistry(row) for site, row in mappings.items() if row["resname"] in wanted_codes}
    geometry = native["geometry"]
    details, counts, status = geometry["proxy_details"], geometry["proxy_counts"], geometry["proxy_count_status"]
    if (set(details) != _PROXY_FAMILIES or set(counts) != _PROXY_FAMILIES
            or set(status) != _PROXY_STATUS_FAMILIES or any(s != "RECORDED" for s in status.values())
            or any(not isinstance(rows, list) or type(counts[k]) is not int or len(rows) != counts[k]
                   for k, rows in details.items())):
        raise ValueError("Incomplete native restraint families for phosphate reference comparison")

    atoms = {a["i_seq"]: a for a in native["atoms"]}
    names = {i: (a["identity"]["chain_id"].strip() + ":" + a["identity"]["resseq"].strip(), a["atom_id"])
             for i, a in atoms.items()}
    references = {}
    between = Counter()
    for kind in ("bond_simple", "bond_asu"):
        for row in details[kind]:
            if row["origin_id"] != 0:
                continue
            indices, named = _bound_proxy_endpoints(row, atoms, names)
            if len(indices) != 2:
                raise ValueError("Native reference bond needs two endpoints")
            left, right = named["atoms"]
            if left[1] == "P":
                left, right = right, left
                indices = indices[::-1]
            source, target = left[0], right[0]
            between[frozenset((source, target))] += 1
            if (kind == "bond_simple" and row["symmetry_operation"] in (None, "x,y,z") and row["weight"] > 0
                    and (left[1], right[1]) == ("O3'", "P") and source != target
                    and [atoms[i]["element"].strip().upper() for i in indices] == ["O", "P"]
                    and (source, target) != (o3, phosphate)
                    and chemistry.get(source) == chemistry[o3] and chemistry.get(target) == chemistry[phosphate]):
                references[source, target] = []
    multiple = [pair for pair in references if between[frozenset(pair)] > 1]
    for pair in multiple:
        del references[pair]
    successors = defaultdict(list)
    for source, target in references:
        successors[source].append(target)
    for kind, rows in details.items():
        for row in rows:
            if row["origin_id"] != 0:
                continue
            _, named = _bound_proxy_endpoints(row, atoms, names)
            sites = {site for group in named.values() for site, _ in group}
            if len(sites) != 2:
                continue
            for source in sites:
                for target in successors.get(source, ()):
                    if target not in sites:
                        continue
                    groups = {k: [["o3-site" if site == source else "phosphate-site", atom] for site, atom in group]
                              for k, group in named.items()}
                    if kind in ("bond_simple", "angle"):
                        groups["atoms"] = min(groups["atoms"], groups["atoms"][::-1])
                    parameters = _recorded_parameters(kind, row, len(named["atoms"]))
                    references[source, target].append(dict(kind=kind, **groups, parameters=parameters))
    groups = {}
    for sites, terms in sorted(references.items()):
        terms.sort(key=_packed)
        fingerprint = sha256(_packed(terms).encode()).hexdigest()
        groups.setdefault(fingerprint, dict(terms_sha256=fingerprint, terms=terms, links=[]))["links"].append(list(sites))
    if len(groups) > 1:
        status = "DIFFERENT_REFERENCES"
    elif len(references) > 1:
        status = "AGREEING_REFERENCES"
    else:
        status = "ONE_REFERENCE" if references else "NO_MATCHING_REFERENCE"
    return dict(status=status, groups=list(groups.values()), o3_chemistry_sha256=chemistry[o3],
                phosphate_chemistry_sha256=chemistry[phosphate], excluded_multiple_bonds=[list(p) for p in sorted(multiple)],
                automatic_adoption=False,
                scope="Recorded covalent terms confined to both reference residues. Per-atom angle and torsion images are not recorded in this capture format.")


def read_phosphate_references(receipt, model_bytes, *, phosphate, o3):
    path = Path(receipt).expanduser().resolve(strict=True)
    try:
        proof, native, snapshots = _capture(path, model_bytes)
        _native_atoms(native, model_bytes)
        result = reference_link_terms(native, phosphate=phosphate, o3=o3)
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ValueError("Incomplete native phosphate reference capture") from exc
    if any(p.read_bytes() != data for p, data in snapshots.items()):
        raise ValueError("Native capture changed during phosphate reference comparison")
    result.update(native_receipt_sha256=sha256(snapshots[path]).hexdigest(), phenix_version=proof["phenix_version"])
    return result
