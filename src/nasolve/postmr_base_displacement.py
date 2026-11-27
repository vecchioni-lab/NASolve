"""Starting isotropic B at a verified ribose site with a single new base methyl."""
from collections import Counter
from dataclasses import dataclass, replace
from math import isfinite

from .cif_base_displacement import _site_lines
from .cif_stereochemistry_audit import _graph, _stereo, _values
from .cif_whole_furanose import base_fragment_atoms
from .model_assessment import file_sha256
from .postmr_restoration import canonical_name, source_graph_fragment

POLICY_ID = "postmr-source-methylated-base-initial-b-v1"


@dataclass
class _Base:
    elements: dict[str, str]
    hydrogen_counts: Counter[str]
    bonds: dict[tuple[str, str], str]
    aromatic_edges: set[tuple[str, str]]


def _read_base(path, code, root, digest):
    values = _values(path, code)
    if file_sha256(path) != digest:
        raise ValueError("Base dictionary differs from the one used for construction")
    elements, orders, charges, neighbors = _graph(values)
    if orders.get(tuple(sorted((root, "C1'")))) != "SINGLE":
        raise ValueError("Require the same single glycosidic bond at the canonical base")
    members = base_fragment_atoms({"base": root, "anomeric": "C1'"}, neighbors)
    if members.intersection(values.get("_chem_comp_chir.atom_id_centre", [])):
        raise ValueError("A handed base requires a separate displacement correspondence")
    stereo = _stereo(values)
    for i, atom in enumerate(values["_chem_comp_atom.atom_id"]):
        if atom not in members:
            continue
        if charges[atom] != 0 or stereo[atom] != "N" or elements[atom] not in {"C", "N", "O", "H"}:
            raise ValueError("Require a neutral, explicitly typed base without a stereocentre")
        for tag in ("pdbx_mass_number", "pdbx_isotope", "isotope"):
            column = values.get("_chem_comp_atom." + tag)
            if column and column[i] not in {"", ".", "?"}:
                raise ValueError("An isotopically specified base needs a separate correspondence")

    heavy = {n: elements[n] for n in members if elements[n] != "H"}
    hydrogens = Counter()
    for h in members - heavy.keys():
        hosts = neighbors[h] & heavy.keys()
        if len(hosts) != 1 or neighbors[h] != hosts:
            raise ValueError("Require explicit singly attached base hydrogens")
        donor = next(iter(hosts))
        if orders[tuple(sorted((h, donor)))] != "SINGLE":
            raise ValueError("Require single bonds to the declared base hydrogens")
        hydrogens[donor] += 1
    bonds = {edge: order for edge, order in orders.items() if all(atom in heavy for atom in edge)}
    aromatic = set()
    prefix = "_chem_comp_bond."
    for i, edge in enumerate(zip(values[prefix+"atom_id_1"], values[prefix+"atom_id_2"], strict=True)):
        edge = tuple(sorted(edge))
        if edge not in bonds:
            continue
        if any(values[prefix+tag][i].upper() not in {"N", ".", "?"}
               for tag in ("pdbx_stereo_config", "stereo_config") if prefix+tag in values):
            raise ValueError("A stereospecific base bond needs a separate correspondence")
        flags = {values[prefix+tag][i].upper() for tag in ("pdbx_aromatic_flag", "aromatic")
                 if prefix+tag in values}
        if len(flags - {".", "?"}) > 1:
            raise ValueError("Contradictory aromatic labels on a base bond")
        if flags == {"Y"}:
            aromatic.add(edge)
    return _Base(heavy, hydrogens, bonds, aromatic)


def _shared_bond_orders(host, target):
    """Accept an explicitly aromatic six-ring drawn with the opposite alternating bonds."""
    common = {edge: value for edge, value in target.bonds.items() if all(n in host.elements for n in edge)}
    if common.keys() != host.bonds.keys() or (target.aromatic_edges & common.keys()) != host.aromatic_edges:
        raise ValueError("The conserved base connectivity or aromatic declarations differ")
    changed = {edge for edge in common if common[edge] != host.bonds[edge]}
    if not changed:
        return []
    ring = {n for pair in changed for n in pair}
    if (len(changed) != 6 or len(ring) != 6 or not changed <= host.aromatic_edges
            or any(host.elements[n] not in {"C", "N"} for n in ring)
            or {edge for edge in common if set(edge) <= ring} != changed):
        raise ValueError("The conserved base bond orders differ outside a declared alternating six-ring")
    for atom in ring:
        edges = [edge for edge in changed if atom in edge]
        if (len(edges) != 2 or {host.bonds[e] for e in edges} != {"SINGLE", "DOUBLE"}
                or {common[e] for e in edges} != {"SINGLE", "DOUBLE"}):
            raise ValueError("Require the same valence at every atom of the aromatic six-ring")
    return [list(edge) for edge in sorted(changed)]


def _methyl_mapping(host, target):
    additions = target.elements.keys() - host.elements.keys()
    if len(additions) != 1 or any(target.elements.get(n) != el for n, el in host.elements.items()):
        raise ValueError("Require the complete same-name host base and one added heavy atom")
    methyl = next(iter(additions))
    attachments = [(edge, order) for edge, order in target.bonds.items() if methyl in edge]
    if (target.elements[methyl] != "C" or target.hydrogen_counts[methyl] != 3 or len(attachments) != 1
            or attachments[0][1] != "SINGLE" or attachments[0][0] in target.aromatic_edges):
        raise ValueError("The added atom must be a terminal carbon with three explicit hydrogens")
    anchor = next(n for n in attachments[0][0] if n != methyl)
    if (host.elements[anchor] not in {"C", "N"} or any(
            host.hydrogen_counts[n] - target.hydrogen_counts[n] != int(n == anchor) for n in host.elements)):
        raise ValueError("The methyl must replace one host hydrogen on carbon or nitrogen")
    return methyl, anchor, _shared_bond_orders(host, target)


def initialize_methylated_base(restored, host_lines, geometry, site, parent, template, dictionary):
    """Initialize B only for a complete fresh uniform base on a verified canonical ribose."""
    record = dict(policy_id=POLICY_ID, scope="STARTING_ISOTROPIC_B_ONLY",
                  source_model_sha256=geometry["host_displacement"]["source_sha256"],
                  parent_dictionary_sha256=geometry["canonical_ribose_sha256"],
                  target_dictionary_sha256=geometry["source_sha256"])
    try:
        if geometry["host_displacement"]["status"] != "TRANSFERRED":
            raise ValueError("The reconstructed scaffold has no verified host displacement transfer")
        root = geometry["attachment_atom"]
        host = _read_base(template, parent, root, record["parent_dictionary_sha256"])
        target = _read_base(dictionary, geometry["component"], root, record["target_dictionary_sha256"])
        if set(geometry["fragment_atoms"]) != target.elements.keys():
            raise ValueError("The transported fragment differs from the target base graph")
        methyl, anchor, rotated = _methyl_mapping(host, target)
        original, built = _site_lines(host_lines, site), _site_lines(restored, site)
        fields = {}
        starting = set()
        for name, element in sorted(target.elements.items()):
            donor = anchor if name == methyl else name
            if name not in built or donor not in original:
                raise ValueError("A declared base atom is absent from the site")
            i, after = built[name]
            _, before = original[donor]
            q, b = float(before[54:60]), float(before[60:66])
            target_b = float(after[60:66])
            if (before[17:20].strip() != parent or after[17:20].strip() != geometry["component"]
                    or before[76:78].strip().upper() != host.elements[donor] or after[76:78].strip().upper() != element
                    or not 0 < q <= 1 or q != float(after[54:60]) or not isfinite(b) or b <= 0
                    or not isfinite(target_b) or target_b < 0):
                raise ValueError("Incompatible base atom identity, occupancy or isotropic B")
            fields[i] = before[60:66]
            starting.add(target_b)
        if len(starting) != 1:
            raise ValueError("The newly constructed base already has atom-specific displacement values")
    except (ValueError, OSError) as exc:
        return restored, dict(record, status="RETAINED_SEED", reason=str(exc))

    result = list(restored)
    for index, field in fields.items():
        result[index] = result[index][:60] + field + result[index][66:]
    return result, dict(record, status="INITIALIZED_FROM_HOST", added_atom=methyl, attachment_atom=anchor,
                        alternate_aromatic_edges=rotated, constructed_b=starting.pop(),
                        starting_b={n: float(fields[built[n][0]]) for n in sorted(target.elements)})


def verify_starting_values(canonical, decisions, dictionaries, site_dictionaries, raw_model, returned_model):
    """Recompute the starting values from the declared files of a saved construction."""
    from .cif_dictionary_store import _bytes
    from .postmr import MutationAction
    from .postmr_canonical_input import _resolve
    from .postmr_scaffold_displacement import HostDisplacement, _indexed

    steps = {s["action"]["site"]: s for s in canonical["receipt"]["steps"]
             if s["proof"].get("status") == "CANONICAL_RIBOSE_SEED"}
    if not isinstance(decisions, dict) or not decisions or not decisions.keys() <= steps.keys():
        raise ValueError("Base displacement decisions require recorded canonical ribose sites")
    host = HostDisplacement(canonical["model"], raw_model.read_text().splitlines(), canonical_ribose=True)
    written = _indexed(returned_model.read_text().splitlines())
    if host.original is None or host.raw is None or written is None:
        raise ValueError("Base displacement readback requires one unambiguous coordinate model")
    for site, decision in decisions.items():
        step = steps[site]
        action = MutationAction(**step["action"])
        template = _resolve(canonical["directory"], step["template"])
        source = site_dictionaries.get(site, dictionaries[action.after])
        graph = source_graph_fragment(source, action.after, ribose_parent=(template, action.parent_code))
        key = tuple(site.split(":"))
        after = written.get(key, [])
        present = {canonical_name(line[12:16].strip()) for line in after}
        if not set(graph["sugar_atoms"] + graph["fragment_atoms"]) <= present:
            raise ValueError("Base displacement readback lacks part of the returned base or sugar")
        graph["scaffold_atoms"] = sorted(set(graph["scaffold_atoms"]) & present)
        graph["canonical_ribose_sha256"] = graph["ribose_reference"]["template_sha256"]
        scaffold = host.apply(replace(action, before=action.parent_code), after, graph)
        if scaffold != after:
            raise ValueError("Returned scaffold B factors differ from the verified transfer")
        expected, observed = initialize_methylated_base(
            host.raw.get(key, []), host.original.get(key, []), graph, site, action.parent_code, template, source)
        if _bytes(observed) != _bytes(decision):
            raise ValueError("Base displacement decision differs from its raw model, host or dictionary")
        def fields(lines):
            return sorted((line[12:17], line[26:27], line[54:66], line[76:78])
                          for line in lines if line[:6].strip() in {"ATOM", "HETATM"}
                          and line[12:16].strip() in graph["fragment_atoms"])
        if fields(expected) != fields(after):
            raise ValueError("Returned base occupancy, element or B factor differs from construction")
