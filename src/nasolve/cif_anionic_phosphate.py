"""Source-bound internal phosphodiester projection from an explicit dianionic monoester."""
from .cif_stereochemistry_audit import _graph, _stereo

POLICY_ID = "cif-internal-dianionic-phosphate-leaving-oxygen-v1"


def anionic_leaving_state(values, context, names, graph):
    """Require one terminal O anion and both untouched nonbridging source oxygens."""
    if (not context.get("incoming_site") or context.get("five_prime_state") != "linked"
            or context.get("symmetry_operation") not in (None, "x,y,z")
            or context.get("experimental_passthrough")):
        raise ValueError("Anionic leaving oxygen requires a declared same-ASU incoming link")
    _, orders, charges, neighbors = graph
    if charges["P"] != 0 or _stereo(values)["P"] in {"R", "S"}:
        raise ValueError("Charged or stereospecified phosphorus requires separate authority")
    prefix = "_chem_comp_chir."
    for center, sign in zip(values.get(prefix+"atom_id_centre", []),
                            values.get(prefix+"volume_sign", []), strict=True):
        if center == "P" and sign.lower() != "both":
            raise ValueError("Stereospecified phosphorus requires separate authority")
    oxygens = {}
    for role, atom in names.items():
        order = orders[tuple(sorted(("P", atom)))]
        if neighbors[atom] != {"P"}:
            raise ValueError("Require three terminal phosphate oxygens without hydrogen")
        oxygens[role] = dict(atom=atom, bond_order=order, formal_charge=charges[atom])
    leaving = oxygens.pop("OP3")
    if leaving["formal_charge"] != -1 or leaving["bond_order"] != "SINGLE":
        raise ValueError("Require a singly bonded terminal OP3 anion")
    retained = {(row["bond_order"], row["formal_charge"]) for row in oxygens.values()}
    if retained != {("DOUBLE", 0), ("SINGLE", -1)}:
        raise ValueError("Require a declared phosphate dianion with unchanged nonbridging oxygens")
    return dict(policy_id=POLICY_ID, leaving_atom=leaving["atom"], leaving_charge=-1,
                retained_phosphate_oxygens=oxygens)


def verify_anionic_projection(before, after, context, state):
    """Account for the departing oxygen and the independent outgoing hydroxyl, if linked."""
    elements, bonds, charges, _ = _graph(before)
    final_elements, final_bonds, final_charges, _ = _graph(after)
    removed = {state["leaving_atom"]}
    if context.get("outgoing_site"):
        removed.update(state["source_o3_hydrogens"])
    if (set(final_elements) != elements.keys() - removed
            or any(final_elements[n] != elements[n] or final_charges[n] != charges[n] for n in final_elements)
            or final_bonds != {pair:order for pair,order in bonds.items() if removed.isdisjoint(pair)}):
        raise ValueError("Anionic phosphate projection changed retained atoms, charges or bond orders")
    if any(value is None or not float(value).is_integer() for value in charges.values()):
        raise ValueError("Anionic phosphate projection requires complete integral formal charges")
    initial, final = int(sum(charges.values())), int(sum(final_charges.values()))
    if final - initial != 1:
        raise ValueError("Unexpected charge difference after removal of OP3 anion")
    return dict(policy_id=POLICY_ID, deleted_atoms=sorted(removed), component_charge_before=initial,
                component_charge_after=final, component_charge_change=final-initial)


def select_anionic_phosphate(source, code, contexts):
    """Select the explicit operation only when every occurrence has the supported state."""
    from .cif_linked_preparation import component_values
    from .cif_phosphate_names import phosphate_names
    from .cif_preparation_qualification import qualify_native_backbone_ports

    if not contexts or any(not context.get("incoming_site") for context in contexts):
        return None
    values = component_values(source, code)
    try:
        names = phosphate_names(values)
        for context in contexts:
            qualify_native_backbone_ports(values, context, phosphate_names=names, anionic_leaving=True)
    except ValueError:
        # No permission is granted. Normal source/site qualification still runs.
        return None
    return POLICY_ID
