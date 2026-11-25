"""Read the recorded covalent terms at chemically matched, intact O3′–P links."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import degrees, dist, isfinite, radians, sin, sqrt
from pathlib import Path

from .cif_attachment_native import _capture, _native_atoms
from .cif_native_parent_chemistry import _COMPONENT_CATEGORIES, _PROXY_FAMILIES, _PROXY_STATUS_FAMILIES
from .cif_native_target_comparison import _mappings
from .cif_terminal_qualification import _bound_proxy_endpoints
from .cif_dihedral_conditioning import dihedral_geometry
from .cif_phosphate_continuation import _endpoint_atoms
from .cif_phosphate_restraints import _reference_group
from .topostitch_contacts import _angle
from .topostitch_graph import _bounded, _inverse, _operator
from .topostitch_images import _cartesian, _fractional
from .topostitch_periodic import _gemmi, _op_key, crystal_from_pdb_bytes


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


def _bond_image(value, *, invert=False):
    if not isinstance(value, str) or not 0 < len(value) <= 128:
        raise ValueError("Require a recorded crystal bond operator")
    gemmi = _gemmi()
    try:
        op = _bounded(gemmi.Op(value))
        return (_inverse(op, gemmi.Op("x,y,z")) if invert else op).triplet()
    except RuntimeError as exc:
        raise ValueError("Invalid crystal bond operator") from exc


def _existing_oxygen_image(kind, row, phosphorus_first):
    # Phenix maps the second atom onto the first. Express both stored orders
    # with P fixed so that the full cell translation can be compared literally.
    value = row.get("symmetry_operation")
    if kind == "bond_asu":
        if not isinstance(value, dict) or value.get("status") != "RECORDED":
            return None
        value = value.get("operator")
    elif "symmetry_operation" in row and value is None:
        value = "x,y,z"
    try:
        return _bond_image(value, invert=not phosphorus_first)
    except ValueError:
        return None


def reference_link_terms(native, *, phosphate, o3, o3_image=None):
    """Group reference links by their recorded terms. No restraints are proposed.

    Require an observed, positive, ordinary covalent O3′–P bond between distinct
    sites. Exclude the queried pair, keeping it independent of its references.
    Preserve signed atom order for torsions and chirality, duplicate terms and
    zero weights. Report any other non-hydrogen-bond O3′–P distance sharing the
    proposed donor or acceptor. When an image is given, compare any bond using
    the exact same atoms with that specific copy, including its cell translation.
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
    competing = set()
    expected_image = _bond_image(o3_image) if o3_image is not None else None
    other_images = set()
    unresolved_image = False
    policy = native.get("restraint_policy")
    origins = policy.get("origin_ids") if isinstance(policy, dict) else None
    hydrogen_origin = origins.get("hydrogen bonds") if isinstance(origins, dict) else None
    for kind in ("bond_simple", "bond_asu"):
        for row in details[kind]:
            origin = row["origin_id"]
            if type(origin) is not int or origin < 0:
                raise ValueError("Invalid recorded bond origin")
            # Phenix stores recognised hydrogen bonds in these same bond arrays.
            # An unclassified distance or an explicit bond edit may change link geometry.
            if type(hydrogen_origin) is int and hydrogen_origin > 0 and origin == hydrogen_origin:
                continue
            indices, named = _bound_proxy_endpoints(row, atoms, names)
            if len(indices) != 2:
                raise ValueError("Native reference bond needs two endpoints")
            left, right = named["atoms"]
            phosphorus_first = left[1] == "P"
            if phosphorus_first:
                left, right = right, left
                indices = indices[::-1]
            source, target = left[0], right[0]
            if expected_image is not None and (left, right) == ((o3, "O3'"), (phosphate, "P")):
                image = _existing_oxygen_image(kind, row, phosphorus_first)
                if image is None:
                    unresolved_image = True
                elif image != expected_image:
                    other_images.add(image)
            between[frozenset((source, target))] += 1
            if ((left[1], right[1]) == ("O3'", "P") and (source == o3 or target == phosphate)
                    and (source, target) != (o3, phosphate)):
                competing.add((source, target))
            if (origin == 0 and kind == "bond_simple" and row["symmetry_operation"] in (None, "x,y,z") and row["weight"] > 0
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
    result = dict(status=status, groups=list(groups.values()), o3_chemistry_sha256=chemistry[o3],
                  phosphate_chemistry_sha256=chemistry[phosphate], excluded_multiple_bonds=[list(p) for p in sorted(multiple)],
                  automatic_adoption=False,
                  scope="Recorded covalent terms confined to both reference residues. Per-atom angle and torsion images are not recorded in this capture format.")
    if competing:
        pairs = sorted(competing)
        observed = ", ".join(f"{donor} O3′ to {acceptor} P" for donor, acceptor in pairs)
        result.update(status="COMPETING_ENDPOINT_BOND", reference_status=status,
                      competing_endpoint_bonds=[list(pair) for pair in pairs],
                      reason=f"Phenix already restrains {observed}. That shares an atom with the proposed {o3} O3′ to {phosphate} P bond.")
    if other_images or unresolved_image:
        reasons = [result["reason"]] if competing else []
        observed = sorted(other_images)
        if observed:
            reasons.append(f"Phenix already joins {o3} O3′ to {phosphate} P in crystal image "
                           + ", ".join(observed) + f". The requested O3′ image is {expected_image}.")
        if unresolved_image:
            reasons.append(f"The image of an existing {o3} O3′–{phosphate} P bond is unresolved.")
        result.update(status="COMPETING_ENDPOINT_BOND" if competing or observed else "UNRESOLVED_ENDPOINT_IMAGE",
                      reference_status=status, requested_o3_image=expected_image, existing_o3_images=observed,
                      unresolved_endpoint_image=unresolved_image, reason=" ".join(reasons))
    return result


def read_phosphate_references(receipt, model_bytes, *, phosphate, o3, o3_image=None):
    _, references = read_phosphate_reference_set(receipt, model_bytes, [(phosphate, o3)], o3_images=[o3_image])
    return references[0]


def read_phosphate_reference_set(receipt, model_bytes, endpoints, *, o3_images=None):
    """Check one preserved native interpretation, then read each named (P site, O3′ site)."""
    path = Path(receipt).expanduser().resolve(strict=True)
    try:
        proof, native, snapshots = _capture(path, model_bytes)
        _native_atoms(native, model_bytes)
        endpoints = list(endpoints)
        images = [None] * len(endpoints) if o3_images is None else o3_images
        references = [reference_link_terms(native, phosphate=p, o3=o, o3_image=image)
                      for (p, o), image in zip(endpoints, images, strict=True)]
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ValueError("Incomplete native phosphate reference capture") from exc
    if any(p.read_bytes() != data for p, data in snapshots.items()):
        raise ValueError("Native capture changed during phosphate reference comparison")
    receipt_sha256 = sha256(snapshots[path]).hexdigest()
    for result in references:
        result.update(native_receipt_sha256=receipt_sha256, phenix_version=proof["phenix_version"])
    return proof, references


def _written_measurement(term, points, target, width, gemmi):
    ordered = []
    for role, name in term["atoms"]:
        xyz = points.get((role, name))
        if xyz is None:
            return dict(value=None, reason=f"Missing or unoccupied {role} {name} with its expected residue and element")
        ordered.append(xyz)
    kind = term["kind"]
    if kind == "bond_simple":
        value = dist(*ordered)
    elif kind == "angle":
        value = _angle(ordered)
        if value is None:
            return dict(value=None, reason="Coincident atoms leave the angle undefined")
    else:
        condition = dihedral_geometry(ordered)
        if not condition["geometry_defined"]:
            return dict(value=None, reason="Collinear or coincident atoms leave the torsion undefined")
        value = degrees(gemmi.calculate_dihedral(*(gemmi.Position(*p) for p in ordered)))
        if not isfinite(value):
            return dict(value=None, reason="The signed torsion could not be measured")
    delta = value - target
    result = dict(value=value)
    if kind == "dihedral":
        turn = 360. / term["parameters"]["periodicity"]
        delta = (delta + turn / 2) % turn - turn / 2
        result["near_collinear_review"] = condition["near_collinear_review"]
    return dict(result, delta=delta, delta_in_widths=delta / width)


def _periodic_response(measurement, periodicity):
    """Fractions of the barrier and peak angular slope for a qualified positive-period native torsion."""
    if measurement["value"] is None:
        return dict(status="UNASSESSED", reason=measurement["reason"])
    if measurement["near_collinear_review"]:
        return dict(status="UNASSESSED", reason="The near-collinear atom path makes the written torsion unstable")
    # cctbx uses E = K * (1 - cos(n * delta)). Normalization cancels K.
    delta = measurement["delta"]
    phase = radians(periodicity * delta)
    return dict(status="MEASURED", fraction_of_barrier=sin(phase / 2) ** 2,
                fraction_of_peak_slope=abs(sin(phase)),
                degrees_to_nearest_maximum=max(0., 180. / periodicity - abs(delta)))


def measure_written_phosphate(model, starting_inspection, *, model_sha256, torsion_response=False):
    """Measure a fitted crystal bond and its ordinary reference links in the written model.

    All donor atoms follow the registered image. The ordinary links retain the
    identity image used by their native proxies. Widths refer to restraints.
    """
    group = _reference_group(starting_inspection)
    donor, donor_code, _ = starting_inspection["o3"]
    acceptor, acceptor_code, _ = starting_inspection["phosphate"]
    links = [(donor, acceptor), *group["links"]]
    raw, atoms = _endpoint_atoms(model, {site for pair in links for site in pair})
    written_digest = sha256(raw).hexdigest()
    if not isinstance(model_sha256, str) or written_digest != model_sha256.casefold():
        raise ValueError("Written phosphate model differs from its checkpoint checksum")
    gemmi, cell, setting = crystal_from_pdb_bytes(raw)
    spacegroup = gemmi.find_spacegroup_by_name(setting)
    source_group = gemmi.find_spacegroup_by_name(starting_inspection["space_group"])
    if (list(cell.parameters) != starting_inspection["cell"] or source_group is None
            or source_group.hall != spacegroup.hall):
        raise ValueError("The written phosphate model differs from the registered crystal frame")
    operation = _operator(starting_inspection["o3_image"], gemmi, {_op_key(op) for op in spacegroup.operations()})
    needed = {name for term in group["terms"] for _, name in term["atoms"]}
    by_site = defaultdict(dict)
    for (site, code, name, _, element, _, occupied), xyz in atoms.items():
        if name in needed and occupied and element == name[0]:
            by_site[site, code][name] = xyz
    positions = []
    for i, (left, right) in enumerate(links):
        points = {}
        for name, xyz in by_site[left, donor_code].items():
            if i == 0:
                xyz = _cartesian(operation.apply_to_xyz(_fractional(xyz, cell, gemmi)), cell, gemmi)
            points["o3-site", name] = xyz
        for name, xyz in by_site[right, acceptor_code].items():
            points["phosphate-site", name] = xyz
        positions.append(points)
    terms = []
    for term in group["terms"]:
        kind, params = term["kind"], term["parameters"]
        target = params["distance_ideal"] if kind == "bond_simple" else params["angle_ideal"]
        width = 1. / sqrt(params["weight"])
        written, *peers = [_written_measurement(term, points, target, width, gemmi) for points in positions]
        ordinary = [dict(o3_site=left, phosphate_site=right, **measurement)
                    for (left, right), measurement in zip(group["links"], peers, strict=True)]
        row = dict(kind=kind, atoms=term["atoms"], units="angstrom" if kind == "bond_simple" else "degrees",
                   target=target, restraint_width=width, written=written, ordinary_links=ordinary)
        if kind == "dihedral":
            row["periodicity"] = params["periodicity"]
            if torsion_response:
                for measurement in [written, *ordinary]:
                    measurement["periodic_response"] = _periodic_response(measurement, row["periodicity"])
        terms.append(row)
    return dict(written_model_sha256=written_digest, reference_terms_sha256=group["terms_sha256"],
                o3_site=donor, phosphate_site=acceptor, oxygen_operator_xyz=starting_inspection["o3_image"],
                terms=terms)
