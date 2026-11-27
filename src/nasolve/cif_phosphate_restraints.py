"""Restore a registered O3′–P connection using two agreeing native reference links.

The current scope is the ordinary phosphate and its four angles and three
torsions. Targets and weights come from the chemically matched links in the
actual model. Unqualified links stay available for inspection.
"""
from hashlib import sha256
from math import dist, fsum, isfinite, pi, sqrt
import re

from .cif_explicit_na_policy import _CODE, _SITE
from .topostitch_recipe import recipe_digest


# Ordered local backbone paths. Fully reversing a path preserves the angle or
# signed torsion. Keep the native order when installing the individual terms.
_DONOR = {"C4'", "C3'", "O3'"}
_PATHS = {
    "bond_simple": ("O3' P",),
    "angle": ("C3' O3' P", "O3' P O5'", "O3' P OP1", "O3' P OP2"),
    "dihedral": ("C4' C3' O3' P", "C3' O3' P O5'", "O3' P O5' C5'"),
}


def _undirected(atoms):
    return min(atoms, atoms[::-1])


def _number(value):
    return type(value) in (float, int) and isfinite(value)


def _reference_group(inspection):
    edge = inspection.get("registered_continuation") or {}
    image = inspection.get("o3_image")
    if (inspection.get("policy_id") != "phosphate-image-observation-v1"
            or edge.get("measurement_status") != "MEASURED" or not isinstance(image, str)
            or edge.get("oxygen_operator_xyz") != image or image == "x,y,z"
            or not re.fullmatch(r"[xyz0-9/+\-]+(?:,[xyz0-9/+\-]+){2}", image)):
        raise ValueError("A measured, explicitly registered crystal-image phosphate is required")
    endpoints = []
    for name, side, atom in (("phosphate", "target", "P"), ("o3", "source", "O3'")):
        site, code, label = inspection[name]
        role = edge[side]
        if (label != atom or role["atom"] != atom or role["coordinate_site"] != site
                or not _SITE.fullmatch(site) or not _CODE.fullmatch(code)):
            raise ValueError("Registered phosphate endpoint differs from the measured atom")
        endpoints.append(site)
    local = inspection["phosphate_atoms"]
    if (endpoints[0] == endpoints[1] or local["OP3"] is not None or
            any(not local.get(name) or local[name]["element"] != element or
                not _number(local[name]["occupancy"]) or not 0 < local[name]["occupancy"] <= 1
                for name, element in (("P","P"), ("OP1","O"), ("OP2","O"), ("O5'","O")))):
        raise ValueError("The registered acceptor requires an occupied ordinary linked phosphate")
    references = inspection.get("native_reference_links") or {}
    groups = references.get("groups", [])
    if references.get("status") != "AGREEING_REFERENCES" or len(groups) != 1:
        raise ValueError("At least two chemically matched intact links must agree")
    group = groups[0]
    links = group["links"]
    if (len(links) < 2 or any(len(pair) != 2 or pair[0] == pair[1]
            or not all(isinstance(site, str) and _SITE.fullmatch(site) for site in pair) for pair in links)
            or len({tuple(pair) for pair in links}) != len(links)
            or any(set(pair) == set(endpoints) for pair in links)):
        raise ValueError("Require distinct native references outside the queried link")
    if recipe_digest(group["terms"]) != group.get("terms_sha256"):
        raise ValueError("Native reference terms differ from their recorded checksum")
    wanted = {(kind, _undirected(tuple(path.split()))) for kind, paths in _PATHS.items() for path in paths}
    found = set()
    for term in group["terms"]:
        kind, atoms, params = term["kind"], term["atoms"], term["parameters"]
        names = tuple(atom for _, atom in atoms)
        key = kind, _undirected(names)
        if (key not in wanted or key in found or any(role != ("o3-site" if name in _DONOR else "phosphate-site")
                for role, name in atoms) or not _number(params["weight"]) or params["weight"] <= 0):
            raise ValueError("Unqualified atom path or weight in the native phosphate reference")
        fields = {"weight", "angle_ideal"} if kind != "bond_simple" else {"weight", "distance_ideal", "symmetry_operation"}
        if kind == "dihedral":
            fields.update(("periodicity", "alt_angle_ideals"))
        if set(params) != fields:
            raise ValueError("Unexpected parameters in the native phosphate reference")
        if kind == "bond_simple":
            if (params["symmetry_operation"] not in (None, "x,y,z") or not _number(params["distance_ideal"])
                    or params["distance_ideal"] <= 0):
                raise ValueError("Require a positive ordinary reference bond")
        elif (not _number(params["angle_ideal"]) or kind == "angle" and not 0 < params["angle_ideal"] <= 180
              or kind == "dihedral" and (type(params["periodicity"]) != int or params["periodicity"] <= 0
                                         or params["alt_angle_ideals"] not in (None, []))):
            raise ValueError("Unqualified native angle or torsion target")
        found.add(key)
    if found != wanted:
        raise ValueError("The complete set of ordinary phosphate reference terms is required")
    return group


def phosphate_bond_phil(inspection):
    """Render the native distance edit; the native manager owns its bonded shells."""
    group = _reference_group(inspection)
    bond, = (r["parameters"] for r in group["terms"] if r["kind"] == "bond_simple")
    def selector(end):
        site, code, atom = inspection[end]
        chain, number = site.split(":")
        return f"chain {chain} and resseq {number} and resname {code} and name {atom}"
    return ("refinement.geometry_restraints.edits {\n  bond {\n    action = add\n"
            f"    atom_selection_1 = {selector('phosphate')}\n    atom_selection_2 = {selector('o3')}\n"
            f"    symmetry_operation = {inspection['o3_image']}\n    distance_ideal = {bond['distance_ideal']}\n"
            f"    sigma = {1 / sqrt(bond['weight'])}\n  }}\n}}\n")


def ordinary_proxy_parameters(term, proxy):
    """Check the native fields omitted by the standard capture before copying a force."""
    kind = term["kind"]
    parameters = dict(term["parameters"])
    try:
        if proxy.origin_id != 0 or proxy.slack != 0:
            raise ValueError("Reference has a noncovalent origin or nonzero slack")
        if kind == "bond_simple":
            parameters.pop("symmetry_operation")
            op = proxy.rt_mx_ji
            if op is not None and not op.is_unit_mx():
                raise ValueError("Reference bond has a crystal image")
        elif any(not op.is_unit_mx() for op in (proxy.sym_ops or ())):
            raise ValueError("Reference atoms carry crystal images")
        if kind in ("bond_simple", "dihedral"):
            if proxy.top_out is not False or proxy.limit != -1.:
                raise ValueError("Unqualified top-out or limit on the reference force")
            parameters["limit"] = proxy.limit
        if kind == "dihedral":
            if proxy.alt_angle_ideals or parameters.pop("alt_angle_ideals"):
                raise ValueError("Unqualified alternate torsion targets")
        if any(value != getattr(proxy, key) for key, value in parameters.items()):
            raise ValueError("Native reference force differs from the captured target or weight")
    except AttributeError as exc:
        raise ValueError("A required native reference field is unavailable") from exc
    return parameters


def _labels(hierarchy):
    from .topostitch_native_recipe import native_atom_identities
    rows = native_atom_identities(hierarchy)
    labels = [(r["chain"] + ":" + str(r["residue_number"]), r["residue_code"], r["atom_name"])
              for r in rows]
    if len(set(labels)) != len(labels) or any(r["altloc"] or r["insertion_code"] for r in rows):
        raise ValueError("The native phosphate reader requires unambiguous model atom identities")
    return labels


def _cryst1_cell(parameters):
    """Lengths have three decimal places and angles have two on a PDB CRYST1 line."""
    return tuple(format(x, ".3f" if n < 3 else ".2f") for n, x in enumerate(parameters))


def _matching_displacement(source, live, scatterer, cell):
    """Check the original PDB displacement against the hierarchy and the diffraction atom."""
    missing = (-1.,) * 6
    source_u = tuple(source.uij)
    anisotropic = source_u != missing
    if scatterer.flags.use_u_aniso() != anisotropic or scatterer.flags.use_u_iso() == anisotropic:
        return False
    b_scale = 8 * pi**2
    scattering_b = scatterer.u_iso_or_equiv(cell) * b_scale
    if not anisotropic:
        return tuple(live.uij) == missing and all(abs(v - source.b) <= 1e-3 for v in (live.b, scattering_b))

    # The B field is printed to 0.01 Å² and each Cartesian U component to
    # 0.0001 Å². Phenix can replace the printed B with 8π² times the mean
    # diagonal U. Only the comparison of those two source fields allows rounding.
    equivalent_b = fsum(source_u[:3]) * b_scale / 3
    pdb_roundoff = 0.005 + 0.00005 * b_scale
    return (abs(source.b - equivalent_b) <= pdb_roundoff + 1e-9
            and (abs(live.b - equivalent_b) <= 1e-8 or abs(live.b - source.b) <= 1e-8)
            and abs(scattering_b - equivalent_b) <= 1e-8
            and dist(live.uij, source_u) <= 1e-9
            and dist(scatterer.u_cart_plus_u_iso(cell), source_u) <= 1e-9)


def _same_atomic_species(source, live):
    # The fresh PDB reader can preserve Hg while native interpretation prints HG.
    return (source.element.strip().upper() == live.element.strip().upper()
            and source.charge.strip() == live.charge.strip())


def verify_phosphate_start(model, raw, inspection):
    """Bind the newly prepared native manager to the exact child, allowing atom reordering."""
    from cctbx import sgtbx
    from iotbx import pdb
    if sha256(raw).hexdigest() != inspection["model_sha256"]:
        raise ValueError("The phosphate observation belongs to a different input model")
    native_input = pdb.input(source_info=None, lines=raw.decode("ascii"))
    original = native_input.construct_hierarchy(sort_atoms=False)
    expected = dict(zip(_labels(original), original.atoms()))
    live = model.get_hierarchy()
    current = _labels(live)
    xrs = model.get_xray_structure()
    crystal = native_input.crystal_symmetry()
    if (set(current) != set(expected) or len(xrs.sites_cart()) != len(current)
            or xrs.space_group() != crystal.space_group()
            or xrs.space_group() != sgtbx.space_group_info(symbol=inspection["space_group"]).group()
            or _cryst1_cell(xrs.unit_cell().parameters()) != _cryst1_cell(crystal.unit_cell().parameters())
            or _cryst1_cell(xrs.unit_cell().parameters()) != _cryst1_cell(inspection["cell"])
            or sgtbx.rt_mx(inspection["o3_image"]).mod_positive() not in xrs.space_group()):
        raise ValueError("Native phosphate model atoms or crystal frame differ from the numbered input")
    for name, atom, xyz, scatterer in zip(current, live.atoms(), xrs.sites_cart(), xrs.scatterers(), strict=True):
        before = expected[name]
        if (not _same_atomic_species(before, atom)
                or abs(atom.occ-before.occ) > 1e-6 or abs(scatterer.occupancy-before.occ) > 1e-6
                or dist(atom.xyz, before.xyz) > 1e-8 or dist(xyz, before.xyz) > 1e-8):
            raise ValueError(f"Native phosphate starting state differs at {name}")
        if not _matching_displacement(before, atom, scatterer, xrs.unit_cell()):
            raise ValueError(f"Native phosphate displacement parameters differ at {name}")


def qualify_live_phosphate_sources(model, inspection):
    """Read the complete live terms for every independently matched source in this manager."""
    from cctbx.geometry_restraints.linking_class import linking_class
    group = _reference_group(inspection)
    hierarchy = model.get_hierarchy()
    labels = _labels(hierarchy)
    atoms = hierarchy.atoms()
    indices = {name: i for i, name in enumerate(labels)}
    geometry = model.restraints_manager.geometry
    bonds = geometry.pair_proxies(sites_cart=model.get_xray_structure().sites_cart()).bond_proxies
    origins = linking_class()
    hydrogen = origins.get_origin_id("hydrogen bonds")
    references = {frozenset(pair): pair for pair in group["links"]}
    if len(references) != len(group["links"]):
        raise ValueError("Native reference directions identify the same physical link")
    # Compare the whole covalent neighbourhood across each source link, including
    # any extra crossing restraint added by refinement after dictionary capture.
    collections = {"bond_simple": bonds.simple, "bond_asu": bonds.asu,
                   **{k: getattr(geometry, k+"_proxies") for k in
                      ("angle", "dihedral", "const_dihedral", "chirality", "planarity", "parallelity")}}
    candidates = {tuple(pair): {} for pair in group["links"]}
    additional = {tuple(pair): set() for pair in group["links"]}
    for kind, proxies in collections.items():
        for proxy in proxies or ():
            ids = (proxy.i_seq, proxy.j_seq) if kind == "bond_asu" else tuple(proxy.i_seqs)
            if kind == "parallelity":
                ids = (*ids, *proxy.j_seqs)
            pair = references.get(frozenset(labels[i][0] for i in ids))
            if pair is None:
                continue
            key = kind, _undirected(ids)
            found = candidates[tuple(pair)]
            if proxy.origin_id != 0:
                if kind in ("bond_simple","bond_asu") and proxy.origin_id != hydrogen:
                    raise ValueError(f"Additional non-hydrogen distance across reference {pair}")
                additional[tuple(pair)].add(key)
                continue
            if kind not in _PATHS or key in found:
                raise ValueError(f"Extra or duplicate native covalent term across reference {pair}")
            found[key] = proxy
    common = None
    for donor, acceptor in group["links"]:
        codes = {"o3-site": (donor, inspection["o3"][1]), "phosphate-site": (acceptor, inspection["phosphate"][1])}
        found = candidates[donor, acceptor]
        terms = []
        for row in group["terms"]:
            try:
                ids = tuple(indices[(*codes[role], name)] for role, name in row["atoms"])
            except KeyError as exc:
                raise ValueError("Live native reference lacks a required atom") from exc
            if any(atoms[i].occ <= 0 or atoms[i].element.strip() != atom[0]
                   for i, (_, atom) in zip(ids, row["atoms"])):
                raise ValueError("Live phosphate reference atom has different occupancy or element")
            key = row["kind"], _undirected(ids)
            proxy = found.pop(key, None)
            if proxy is None or key in additional[donor, acceptor]:
                raise ValueError("Missing or competing force in a live phosphate reference")
            if row["kind"] == "dihedral" and tuple(proxy.i_seqs) != ids:
                raise ValueError("Live phosphate torsion differs from the recorded signed atom order")
            terms.append(dict(kind=row["kind"], atoms=row["atoms"], parameters=ordinary_proxy_parameters(row, proxy)))
        if found or (common is not None and terms != common):
            raise ValueError("The complete live phosphate references disagree")
        common = terms
    return common


def verify_phosphate_bond(model, inspection, terms):
    """Verify the distance, the four bonded-neighbour exclusions and their exact mate."""
    from cctbx import sgtbx
    from cctbx.geometry_restraints.linking_class import linking_class
    labels = _labels(model.get_hierarchy())
    indices = {label: i for i, label in enumerate(labels)}
    phosphate, donor = tuple(inspection["phosphate"][:2]), tuple(inspection["o3"][:2])
    p, o = indices[(*phosphate, "P")], indices[(*donor, "O3'")]
    image = sgtbx.rt_mx(inspection["o3_image"])
    identity = sgtbx.rt_mx("x,y,z")
    reverse = image.inverse()
    wanted = {(p, o): 1, (p, indices[(*donor, "C3'")]): 2,
              **{(indices[(*phosphate, atom)], o): 2 for atom in ("OP1", "OP2", "O5'")}}
    def pair_in_frame(left, right, op):
        if (left, right) in wanted and op == image:
            return left, right
        if (right, left) in wanted and op == reverse:
            return right, left
        return None
    geo = model.restraints_manager.geometry
    shell_counts = {key: [] for key in wanted}
    for number, table in enumerate(geo.shell_sym_tables, 1):
        for a, b in wanted:
            for i, j in ((a, b), (b, a)):
                # The native triplet tables store only one of the two directions.
                for partner, ops in table[i].items():
                    if partner == j:
                        shell_counts[a,b].extend(number for k in range(len(ops)) if pair_in_frame(i,j,ops[k]))
    if any(shell_counts[key] != [shell] for key, shell in wanted.items()):
        raise ValueError("The registered phosphate did not build the expected first and second bonded shells")
    pairs = geo.pair_proxies(sites_cart=model.get_xray_structure().sites_cart())
    found = []
    for kind, collection in (("bond", pairs.bond_proxies), ("nonbonded", pairs.nonbonded_proxies)):
        if collection is None:
            raise ValueError("The native phosphate neighbour lists are unavailable")
        def observe(i, j, op, proxy):
            key = pair_in_frame(i, j, op)
            if kind == "nonbonded" and key is not None:
                raise ValueError("A registered phosphate bonded neighbour still has nonbonded repulsion")
            if kind == "bond" and {i,j} == {p,o}:
                if key != (p,o):
                    raise ValueError("An additional bond joins different copies of the phosphate endpoints")
                found.append(proxy)
        for proxy in collection.simple:
            observe(*proxy.i_seqs, proxy.rt_mx_ji or identity, proxy)
        for proxy in collection.asu:
            if (proxy.i_seq,proxy.j_seq) in wanted or (proxy.j_seq,proxy.i_seq) in wanted:
                observe(proxy.i_seq, proxy.j_seq, collection.asu_mappings().get_rt_mx_ji(pair=proxy), proxy)
    bond, = (t["parameters"] for t in terms if t["kind"] == "bond_simple")
    if len(found) != 1:
        raise ValueError("Require exactly one native bond across the registered crystal image")
    proxy = found[0]
    # The PHIL writer travels through sigma, and Phenix reconstructs the weight.
    from math import isclose
    if (proxy.origin_id != linking_class().get_origin_id("edits") or proxy.slack != 0
            or proxy.top_out is not False or proxy.limit != bond["limit"]
            or not isclose(proxy.weight, bond["weight"], rel_tol=1e-12)
            or proxy.distance_ideal != bond["distance_ideal"]):
        raise ValueError("The installed phosphate bond differs from the live source force")
    return {"bonds": len(found), "second_shell_pairs": len(wanted)-1, "remaining_nonbonded": 0}
