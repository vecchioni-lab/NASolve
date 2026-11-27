"""Read-only explicit plane coverage for source-declared trigonal carbon.

This is a connectivity-selected screen, not a universal hybridization model or
permission to flatten a molecule. A missing plane can coexist with torsions and
angles; neither its presence nor absence alone establishes achieved geometry.
"""
from hashlib import sha256
from math import hypot, isfinite
from pathlib import Path

from .cif_doctor import _ORDERS, _rows
from .cif_stereochemistry_audit import _values, _graph, _stereo, _coordinates
from .cif_triple_bond_audit import _numeric

POLICY_ID = "cif-source-trigonal-plane-coverage-v1"
QUALIFIED_RING_POLICY = "cif-qualified-ring-trigonal-plane-coverage-v1"


def _table(values, category):
    findings = []
    rows = _rows(values, "_chem_comp_" + category, findings)
    if findings:
        raise ValueError("Ambiguous plane-coverage category: " + category)
    return rows


def _planes(values, names):
    planes = {}
    for row in _table(values, "plane_atom"):
        plane, atom = row.get("plane_id"), row.get("atom_id")
        sigma = _numeric(row.get("dist_esd"))
        if (plane in (None, "", ".", "?") or atom not in names
                or sigma is None or sigma <= 0):
            raise ValueError("Require identified plane atoms with positive finite ESDs")
        members = planes.setdefault(plane, {})
        if atom in members:
            raise ValueError("Duplicate plane member")
        members[atom] = sigma
    return planes


def _local_geometry(coordinates, centre, neighbors):
    """Descriptive normalized volume; coordinates do not choose the chemistry."""
    if not all(n in coordinates for n in [centre, *neighbors]):
        return {"status": "UNAVAILABLE"}
    origin = coordinates[centre]
    vectors = [[x-y for x,y in zip(coordinates[n], origin)] for n in neighbors]
    lengths = [hypot(*v) for v in vectors]
    if any(not isfinite(x) for v in vectors for x in v) or any(not isfinite(x) for x in lengths) or min(lengths) <= 1e-12:
        return {"status": "DEGENERATE"}
    a,b,c = [[x/length for x in v] for v,length in zip(vectors,lengths)]
    determinant = sum(a[i] * (b[(i+1)%3]*c[(i+2)%3] - b[(i+2)%3]*c[(i+1)%3]) for i in range(3))
    return {"status": "DESCRIPTIVE", "absolute_normalized_volume": abs(determinant)}


def audit_trigonal_plane_coverage(source, dictionary, code, *, bond_representation_policy=None):
    """Screen explicit neutral C(=X)(-Y)(-Z) centres with three heavy neighbors.

    The default requires identical graphs. An explicit policy can reassess a
    complete source-declared ring representation. Aromatic-only sources,
    implicit-H centres, charged/unknown states and declared chiral centres are
    explicitly outside this first rule. No residue or atom-name allowlist is used.
    Existing graph-numerics policies and historical receipts are not changed.
    """
    from .cif_purine_representation import validate_policy
    validate_policy(bond_representation_policy)
    return _audit_coverage(Path(source), Path(dictionary), code, bond_representation_policy, snapshot=None)


def audit_snapshot_trigonal_planes(directory, code):
    """Read the isolated, qualified dictionary before site edits or plane generation."""
    from .cif_dictionary_store import resolve_dictionary_snapshot

    saved = resolve_dictionary_snapshot(directory)
    if saved["manifest"]["request"]["component"] != code:
        raise ValueError("Plane screen component differs from the acquired snapshot")
    policy = saved["manifest"]["request"]["recipe"].get("bond_representation_policy")
    audit = _audit_coverage(saved["source"], saved["dictionary"], code, policy, snapshot=saved)
    files = saved["manifest"]["artifacts"]
    if (audit["source_sha256"] != files["source"]["sha256"]
            or audit["dictionary_sha256"] != files["dictionary"]["sha256"]):
        raise ValueError("Plane screen inputs differ from the qualified snapshot")
    return audit


def _qualified_ring_changes(source, dictionary, code, sg, dg, policy, saved):
    """Require the maintained representation check for these two chemical definitions."""
    if policy is None or sg[0] != dg[0] or sg[2:] != dg[2:] or sg[1].keys() != dg[1].keys():
        raise ValueError("Require identical source/dictionary atom, bond and charge graphs")
    if saved is not None:
        # resolve_dictionary_snapshot already replays the bound isolated qualification.
        if not saved["qualification_current"]:
            raise ValueError("Ring plane screen requires current isolated qualification")
        assessment = saved["qualification"]["source_assessment"]
    else:
        # A generated support or selected file can differ from the isolated CIF.
        # Its own atoms, charges, orders and source configurations must qualify.
        from .cif_candidate_usability import reassess_complete_candidate
        assessment = reassess_complete_candidate(source, dictionary, code, bond_representation_policy=policy)
        if (assessment["candidate_status"] != "CANDIDATE_REVIEW" or any(
                term["handedness"] != "PRESERVED" for term in assessment["finished_stereo"]["terms"])):
            raise ValueError("Plane screen requires a source-preserving numerical dictionary")
    proof = assessment["legacy_inspection"]["bond_representation"]
    if (proof["status"] != "SOURCE_DECLARED_EQUIVALENT" or proof["policy_id"] != policy
            or proof["unresolved_bonds"]):
        raise ValueError("Require source-qualified equivalent ring bond orders")
    changes = {edge: (order, dg[1][edge]) for edge, order in sg[1].items() if order != dg[1][edge]}
    systems = proof["equivalent_rings"] + proof["equivalent_fused_systems"]
    qualified = {tuple(b["atoms"]): (b["source_order"], b["generated_order"])
                 for system in systems for b in system["bonds"]}
    if changes != qualified:
        raise ValueError("Plane screen bond differences exceed the qualified ring representation")
    result = dict(policy_id=policy, changed_bonds=[list(edge) for edge in sorted(changes)])
    if saved is not None:
        result["qualification_sha256"] = saved["manifest"]["artifacts"]["qualification"]["sha256"]
    return result


def _declared_chiral_centres(values):
    marked = {atom for atom, marker in _stereo(values).items() if marker not in {"N", "?"}}
    return marked | {r["atom_id_centre"] for r in _table(values, "chir")}


def _trigonal_carbon_neighborhood(graph, centre, chiral):
    """Read the neutral three-heavy-neighbor carbon rule from an explicit graph."""
    elements, orders, charges, neighbors = graph
    adjacent = sorted(neighbors[centre])
    declared = [orders[tuple(sorted((centre, n)))] for n in adjacent]
    reason = None
    if elements[centre] != "C" or len(adjacent) != 3:
        reason = "OUTSIDE_THREE_COORDINATE_CARBON_SCOPE"
    elif any(elements[n] in {"H", "D"} for n in adjacent):
        reason = "IMPLICIT_OR_HYDROGEN_FLANK_NOT_ASSESSED"
    elif sorted(declared) != ["DOUBLE", "SINGLE", "SINGLE"]:
        reason = "BOND_REPRESENTATION_NOT_ASSESSED"
    elif charges[centre] != 0:
        reason = "CHARGED_OR_UNKNOWN_CENTRE_NOT_ASSESSED"
    elif centre in chiral:
        reason = "DECLARED_CHIRAL_CENTRE_NOT_ASSESSED"
    return adjacent, declared, reason


def _six_rings_through(centre, flanks, elements, neighbors):
    """Chordless six-membered C/N rings through both specified ring bonds."""
    left, right = sorted(flanks)
    rings = []
    for second in sorted(neighbors[left] - {centre, right}):
        for fourth in sorted(neighbors[right] - {centre, left}):
            for third in sorted(neighbors[second] & neighbors[fourth]):
                ring = (centre, left, second, third, fourth, right)
                members = set(ring)
                if (len(members) == 6 and all(elements[n] in {"C", "N"} for n in ring)
                        and all(len(neighbors[n] & members) == 2 for n in ring)):
                    rings.append(ring)
    return rings


def source_ring_alkyne_arms(values, graph):
    """Select source-declared ring–C≡C–C paths. Return each possible ring explicitly."""
    from .cif_doctor import _bridges

    elements, orders, charges, neighbors = graph
    triples = [edge for edge, order in sorted(orders.items())
               if order == "TRIPLE" and all(elements[n] == "C" for n in edge)]
    if not triples:
        return []
    chiral = _declared_chiral_centres(values)
    bridges = _bridges(neighbors)
    arms = []
    for a, b in triples:
        for inner, outer in ((a, b), (b, a)):
            if inner in chiral or outer in chiral:
                continue
            before, after = neighbors[inner] - {outer}, neighbors[outer] - {inner}
            if len(before) != 1 or len(after) != 1:
                continue
            anchor, = before
            tip, = after
            arm = (anchor, inner, outer, tip)
            if any(elements[n] != "C" or charges[n] != 0 for n in arm):
                continue
            if any(frozenset(edge) not in bridges or orders[tuple(sorted(edge))] != "SINGLE"
                   for edge in ((anchor, inner), (outer, tip))):
                continue
            adjacent, _, reason = _trigonal_carbon_neighborhood(graph, anchor, chiral)
            if reason is None:
                rings = _six_rings_through(anchor, set(adjacent) - {inner}, elements, neighbors)
                if rings:
                    arms.append((arm, rings))
    return arms


def dictionary_ring_arm_paths(component):
    """Use the chemical declarations retained by the original component assessment."""
    inventory = component["inventory"]
    bonds = inventory["bond_orders"]
    if not any(_ORDERS.get(order.upper()) == "TRIPLE" for bond in bonds for order in bond["declarations"].values()):
        return dict(status="NO_DECLARED_TRIPLE", arms=[])
    if component["verdicts"]["graph"] != "PASS" or any(len(row["atoms"]) != 4 for row in inventory["chirality"]):
        return dict(status="UNASSESSED", reason="The supplied component graph needs review", arms=[])
    atoms = inventory["atoms"]
    values = {"_chem_comp_atom.atom_id": [r["atom_id"] for r in atoms],
              "_chem_comp_atom.type_symbol": [r["element"] for r in atoms],
              "_chem_comp_bond.atom_id_1": [r["atoms"][0] for r in bonds],
              "_chem_comp_bond.atom_id_2": [r["atoms"][1] for r in bonds],
              "_chem_comp_chir.atom_id_centre": [r["atoms"][0] for r in inventory["chirality"]]}
    for key in ("charge", "pdbx_formal_charge"):
        values["_chem_comp_atom." + key] = [r["declared_charge_fields"].get(key, "?") for r in atoms]
    for key in ("stereo_config", "pdbx_stereo_config"):
        values["_chem_comp_atom." + key] = [r["stereo_declarations"].get(key, "?") for r in atoms]
    for key in ("type", "value_order"):
        values["_chem_comp_bond." + key] = [r["declarations"].get(key, "?") for r in bonds]
    try:
        arms = source_ring_alkyne_arms(values, _graph(values))
    except (KeyError, ValueError) as exc:
        return dict(status="UNASSESSED", reason=f"Cannot interpret the supplied component graph: {exc}", arms=[])
    return dict(status="CHECKED", arms=[dict(arm=list(arm), rings=[list(r) for r in rings]) for arm, rings in arms])


def _audit_coverage(source, dictionary, code, policy, *, snapshot):
    original, before = source.read_bytes(), dictionary.read_bytes()
    try:
        sv, dv = _values(source, code), _values(dictionary, code)
        sg, dg = _graph(sv), _graph(dv)
        representation = _qualified_ring_changes(source, dictionary, code, sg, dg, policy, snapshot) if sg != dg else None
        elements, _, charges, _ = sg
        chiral = _declared_chiral_centres(sv) | _declared_chiral_centres(dv)
        planes = _planes(dv, elements)
        angles, torsions = _table(dv, "angle"), _table(dv, "tor")
        source_family, source_xyz = _coordinates(sv, source=True)
        dictionary_family, dictionary_xyz = _coordinates(dv, source=False)
        rows, excluded = [], []
        for centre in sorted(n for n,e in elements.items() if e == "C"):
            adjacent, declared, reason = _trigonal_carbon_neighborhood(sg, centre, chiral)
            if reason:
                excluded.append({"centre": centre, "neighbors": adjacent, "reason": reason})
                continue
            local = {centre, *adjacent}
            covered = [p for p,members in sorted(planes.items()) if local <= members.keys()]
            partial = []
            for plane,members in sorted(planes.items()):
                shared = set(adjacent) & members.keys()
                if centre in members and len(shared) == 2:
                    partial.append({"plane": plane, "shared": [centre, *sorted(shared)],
                                    "missing": sorted(local-members.keys()),
                                    "existing_members": sorted(members)})
            # Retain potentially relevant alternative restraints. This screen
            # deliberately does not claim that they are absent or ineffective.
            local_angles = [r for r in angles if r.get("atom_id_2") == centre
                            and {r.get("atom_id_1"),r.get("atom_id_3")} <= set(adjacent)]
            local_torsions = [r for r in torsions if centre in {r.get("atom_id_"+str(i)) for i in range(1,5)}
                             and len(local & {r.get("atom_id_"+str(i)) for i in range(1,5)}) >= 3]
            rows.append({"centre": centre, "neighbors": adjacent,
                         "bond_orders": dict(zip(adjacent,declared)), "formal_charge": charges[centre],
                         "coverage": "EXPLICIT_PLANE_PRESENT" if covered else "EXPLICIT_PLANE_MISSING",
                         "covering_planes": [{"plane": p, "member_esds": planes[p]} for p in covered],
                         "partial_planes": partial, "local_angle_terms": local_angles,
                         "related_torsion_terms": local_torsions,
                         "source_geometry": _local_geometry(source_xyz,centre,adjacent),
                         "dictionary_geometry": _local_geometry(dictionary_xyz,centre,adjacent)})
        missing = [r["centre"] for r in rows if r["coverage"] == "EXPLICIT_PLANE_MISSING"]
        return {"schema_version": 1, "policy_id": QUALIFIED_RING_POLICY if representation else POLICY_ID,
                **({"qualified_representation": representation} if representation else {}), "component": code,
                "source_sha256": sha256(original).hexdigest(), "dictionary_sha256": sha256(before).hexdigest(),
                "status": "REVIEW" if missing else "SCOPED_EXPLICIT_COVERAGE_PASS" if rows else "UNASSESSED",
                "centres": rows, "unassessed_carbon_centres": excluded, "missing_explicit_planes": missing,
                "source_coordinate_family": source_family, "dictionary_coordinate_family": dictionary_family,
                "selection": "EXPLICIT_SOURCE_GRAPH_AND_STATE; NO_COMPONENT_OR_ATOM_NAME_ALLOWLIST",
                "native_membership": "NOT_RUN", "achieved_geometry": "NOT_ASSESSED",
                "scientific_approval": "NOT_RUN", "automatic_adoption": False, "input_integrity": "UNCHANGED",
                "limitations": ["Missing explicit plane coverage is not proof of absent or inadequate alternative restraints.",
                                "Plane ESDs and related angles/torsions are reported, not calibrated or retuned.",
                                "Strained, pyramidal, aromatic-only and other chemistry need separate qualification; no universal flattening rule.",
                                "Source/dictionary coordinates are descriptive; they neither select the rule nor approve chemistry."]}
    finally:
        if source.read_bytes() != original or dictionary.read_bytes() != before:
            raise ValueError("Plane-coverage input changed during assessment")



def audit_selected_trigonal_planes(sources, dictionaries, *, representation_policies=None):
    """Describe explicit selected-CIF coverage against already qualified source pins.

    Live references contain path and sha256; callers retain selection authority.
    Reuse the source-graph screen without guessing dictionary precedence, applying
    native modifications, or inferring sufficient alternative restraints. Unknown
    chemistry is unassessed; changed/missing evidence is an error, never a note.
    """
    import re
    from .cif_dictionary_sites import _need, _read
    from .ligand_profiles import dictionary_component_codes

    _need(isinstance(sources, dict) and sources and all(
        isinstance(code, str) and code.isascii() and code.isalnum() for code in sources),
        'Require explicit source component identities')
    _need(isinstance(dictionaries, (list, tuple)), 'Require ordered selected dictionaries')
    from .cif_purine_representation import validate_policy
    policies = {} if representation_policies is None else representation_policies
    _need(isinstance(policies, dict) and policies.keys() <= sources.keys(),
          'Selected plane-screen policies differ from source components')
    for policy in policies.values():
        validate_policy(policy)
    references = [*sources.values(), *dictionaries]

    def checked(reference):
        _need(isinstance(reference, dict) and set(reference) == {'path', 'sha256'}
              and isinstance(reference['sha256'], str)
              and re.fullmatch('[0-9a-f]{64}', reference['sha256']), 'Require bound plane-screen references')
        path = Path(reference['path'])
        _need(sha256(_read(path)).hexdigest() == reference['sha256'],
              'Selected plane-screen input changed after qualification')
        return path

    for reference in references:
        checked(reference)
    try:
        members = []; unreadable = []
        for index, reference in enumerate(dictionaries):
            try:
                members.append(dictionary_component_codes(Path(reference['path'])))
            except ValueError as exc:
                members.append(None); unreadable.append(f'dictionary {index}: {exc}')
        rows = {}
        for code, source in sorted(sources.items()):
            indices = [i for i, codes in enumerate(members) if codes is not None and code in codes]
            row = dict(status='UNASSESSED', dictionary_indices=indices)
            if unreadable:
                row['reason'] = 'Selected dictionary membership could not be read: ' + '; '.join(unreadable)
            elif len(indices) != 1:
                row['reason'] = 'Require one explicit selected dictionary; effective precedence or library definitions were not inferred.'
            else:
                try:
                    audit = audit_trigonal_plane_coverage(Path(source['path']),
                        Path(dictionaries[indices[0]]['path']), code, bond_representation_policy=policies.get(code))
                except ValueError as exc:
                    row['reason'] = str(exc)
                else:
                    _need(audit['source_sha256'] == source['sha256']
                          and audit['dictionary_sha256'] == dictionaries[indices[0]]['sha256'],
                          'Selected plane-screen assessment differs from bound inputs')
                    row.update(status=audit['status'], missing_explicit_planes=audit['missing_explicit_planes'],
                        centres=[dict(centre=c['centre'], coverage=c['coverage']) for c in audit['centres']],
                        unassessed_centres=len(audit['unassessed_carbon_centres']))
                    if 'qualified_representation' in audit:
                        row['qualified_representation'] = audit['qualified_representation']
                    if audit['status'] == 'UNASSESSED':
                        row['reason'] = 'No centres meet the supported source-graph rule.'
            rows[code] = row
        return dict(policy_id='cif-selected-dictionary-trigonal-plane-coverage-v1',
            coverage_policy=POLICY_ID, components=rows,
            source_sha256={code:ref['sha256'] for code,ref in sorted(sources.items())},
            dictionary_sha256=[ref['sha256'] for ref in dictionaries],
            native_membership='NOT_ASSESSED', scientific_approval='NOT_RUN', automatic_adoption=False)
    finally:
        # Do not convert a concurrent input change into an unsupported-chemistry note.
        for reference in references:
            checked(reference)
