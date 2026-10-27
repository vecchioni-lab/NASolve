"""Bounded source-topology profiles; no linkage or chemical-state transformation.

Atom names, component codes and descriptive family labels do not choose a
profile. The selected NAR record supplies base membership, not backbone truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import openpyxl
from restraints import residue_library

from .cif_catalogue import MAX_SOURCE_BYTES, _digest, _workbook_records
from .cif_doctor import assess_dictionaries
from .cif_linked_preparation import component_values
from .cif_stereochemistry_audit import _graph, _stereo
from .component_records import resolve_component_record, role_signature

POLICY_ID = "cif-source-attachment-topology-v1"
MAX_HEAVY_ATOMS = 128
MAX_SEARCH_STEPS = 20000
MAX_EMBEDDINGS = 64


@dataclass(frozen=True)
class _Profile:
    identifier: str
    nodes: tuple[tuple[str, tuple[str, ...], int, int], ...]
    edges: tuple[tuple[str, str, str], ...]
    ports: tuple[tuple[str, str, str], ...]


_SUGAR_NODES = (
    ("base", ('C', 'N'), 1, 4), ("anomeric", ('C',), 3, 3), ("ring_o", ('O',), 2, 2),
    ("ring_c4", ('C',), 3, 3), ("ring_c3", ('C',), 3, 3), ("ring_c2", ('C',), 2, 3),
    ("five_c", ('C',), 2, 2), ("five_o", ('O',), 2, 2), ("phosphate", ('P',), 4, 4),
    ("three_o", ('O',), 1, 1),
)
_SUGAR_EDGES = tuple((a, b, "SINGLE") for a, b in (
    ("base", "anomeric"), ("anomeric", "ring_o"), ("ring_o", "ring_c4"),
    ("ring_c4", "ring_c3"), ("ring_c3", "ring_c2"), ("ring_c2", "anomeric"),
    ("ring_c4", "five_c"), ("five_c", "five_o"), ("five_o", "phosphate"),
    ("ring_c3", "three_o"),
))
_SUGAR_PORTS = (("phosphate", "phosphate", "phosphate"), ("alcohol", "three_o", "alcohol"))
PROFILES = (
    _Profile("unbridged-furanose-phosphate-v1", _SUGAR_NODES, _SUGAR_EDGES, _SUGAR_PORTS),
    _Profile("two-o-four-c-methylene-furanose-phosphate-v1",
             tuple((role, element, 4, 4) if role == "ring_c4" else
                   (role, element, 3, 3) if role == "ring_c2" else (role, element, lo, hi)
                   for role, element, lo, hi in _SUGAR_NODES)
             + (("bridge_c", ('C',), 2, 2), ("bridge_o", ('O',), 2, 2)),
             _SUGAR_EDGES + (("ring_c4", "bridge_c", "SINGLE"),
                             ("bridge_c", "bridge_o", "SINGLE"),
                             ("bridge_o", "ring_c2", "SINGLE")), _SUGAR_PORTS),
    _Profile("uncapped-aminoethylglycine-pna-core-v1", (
        ("base", ('C', 'N'), 1, 4), ("base_methylene", ('C',), 2, 2),
        ("base_carbonyl", ('C',), 3, 3), ("base_carbonyl_o", ('O',), 1, 1),
        ("backbone_n", ('N',), 3, 3), ("glycine_c", ('C',), 2, 2),
        ("carboxyl_c", ('C',), 3, 3), ("carboxyl_o", ('O',), 1, 1), ("acid_o", ('O',), 1, 1),
        ("amino_c", ('C',), 2, 3), ("middle_c", ('C',), 2, 2), ("amine_n", ('N',), 1, 1),
    ), (
        ("base", "base_methylene", "SINGLE"), ("base_methylene", "base_carbonyl", "SINGLE"),
        ("base_carbonyl", "base_carbonyl_o", "DOUBLE"), ("base_carbonyl", "backbone_n", "SINGLE"),
        ("backbone_n", "glycine_c", "SINGLE"), ("glycine_c", "carboxyl_c", "SINGLE"),
        ("carboxyl_c", "carboxyl_o", "DOUBLE"), ("carboxyl_c", "acid_o", "SINGLE"),
        ("backbone_n", "middle_c", "SINGLE"), ("middle_c", "amino_c", "SINGLE"),
        ("amino_c", "amine_n", "SINGLE"),
    ), (("amine", "amine_n", "amine"), ("carboxyl", "carboxyl_c", "carboxyl"))),
)


def _embeddings(profile, elements, bonds, neighbors, base_atoms):
    """Injective induced heavy-graph embeddings with explicit work limits."""
    heavy = {a for a, e in elements.items() if e not in {"H", "D"}}
    degree = {a: len(neighbors[a] & heavy) for a in heavy}
    domains = {role: sorted(a for a in heavy if elements[a] in allowed
                           and lo <= degree[a] <= hi and ((a in base_atoms) == (role == "base")))
               for role, allowed, lo, hi in profile.nodes}
    edges = {frozenset((a, b)): order for a, b, order in profile.edges}
    matches, assigned = [], {}
    steps = 0
    limited = False

    def visit():
        nonlocal steps, limited
        if limited:
            return
        if len(assigned) == len(domains):
            if "phosphate" in assigned:
                p, oxygen = assigned["phosphate"], assigned["five_o"]
                terminal = (neighbors[p] & heavy) - {oxygen}
                if (len(terminal) != 3 or any(elements[a] != "O" or degree[a] != 1 for a in terminal)
                        or sorted(bonds[tuple(sorted((a, p)))] for a in terminal) != ["DOUBLE", "SINGLE", "SINGLE"]):
                    return
            matches.append(dict(sorted(assigned.items())))
            if len(matches) >= MAX_EMBEDDINGS:
                limited = True
            return
        # Expand connected roles first; use the smallest domain to avoid broad
        # element-only permutations. Every remaining candidate is still checked.
        role = min((r for r in domains if r not in assigned), key=lambda r: (
            -sum(frozenset((r, done)) in edges for done in assigned), len(domains[r]), r))
        for atom in domains[role]:
            steps += 1
            if steps > MAX_SEARCH_STEPS:
                limited = True
                return
            if atom in assigned.values():
                continue
            if any(bonds.get(tuple(sorted((atom, other)))) != edges.get(frozenset((role, done)))
                   for done, other in assigned.items()):
                continue
            assigned[role] = atom
            visit()
            del assigned[role]
            if limited:
                return
    visit()
    return {"profile": profile.identifier, "matches": matches, "search_steps": steps,
            "search_complete": not limited}


def inspect_attachment_profile(source, code, *, workbook):
    """Bind a unique topology and source-state ports without preparing a model.

    Exact source and workbook anchors are explicit. This adds no family label,
    leaving-group choice, protonation change, linkage, coordinates or native claim.
    """
    source, workbook = (Path(p).expanduser().resolve(strict=True) for p in (source, workbook))
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Oversized attachment-profile source")
    original, workbook_bytes = source.read_bytes(), workbook.read_bytes()
    records, locations = _workbook_records(workbook)
    assessment = assess_dictionaries([source], stage="source")
    selected = [c for c in assessment["components"] if c["component_id"] == code]
    report = {
        "schema_version": 1, "policy_id": POLICY_ID, "status": "REVIEW", "component": code,
        "source": {"anchor": "source_directory", "path": source.name, **_digest(original)},
        "workbook": {"anchor": "workbook_directory", "path": workbook.name, **_digest(workbook_bytes)},
        "loader": {"module": "restraints.residue_library", "openpyxl_version": openpyxl.__version__,
                   **_digest(Path(residue_library.__file__).read_bytes())},
        "search_limits": {"heavy_atoms": MAX_HEAVY_ATOMS, "steps_per_profile": MAX_SEARCH_STEPS,
                          "embeddings_per_profile": MAX_EMBEDDINGS},
        "native_execution": "NOT_RUN",
        "source_assessor_policy": assessment["policy_id"], "source_findings": assessment["findings"],
        "workbook_rows": [loc for rec, loc in zip(records, locations) if rec["Ligand code"] == code],
        "topology_status": "NOT_ASSESSED", "matched_profile": None, "bindings": {}, "ports": {},
        "review_reasons": [], "native_qualification": "NOT_ASSESSED", "site_context": "NOT_ASSESSED",
        "permitted_delta": "NOT_ASSIGNED", "transformations": [], "automatic_adoption": False,
        "limitations": [
            "A matched core topology is not complete chemical, linkage, NAR recipe or native qualification.",
            "Source charges, hydrogens and stereo markers are evidence, not a selected terminal/protonation state.",
            "External branches remain unclassified; no leaving atom, bond formation or deletion is authorized.",
            "The profiles cover declared single-phosphate furanoses and an uncapped aminoethylglycine PNA core only.",
        ],
    }
    try:
        record, resolution = resolve_component_record(records, code)
    except ValueError:
        report["review_reasons"].append("NAR_RECORD_ABSENT_OR_CONFLICTING")
        record = None
    else:
        report["record_resolution"] = resolution["resolution"]
        report["operational_signature"] = role_signature(record)
    if (len(selected) != 1 or len(assessment["components"]) != 1
            or selected[0]["verdicts"]["graph"] != "PASS"
            or any(f["status"] in {"FAIL", "ERROR"} for f in assessment["findings"])):
        report["review_reasons"].append("SOURCE_GRAPH_OR_IDENTITY_UNRESOLVED")
    elif record is not None:
        values = {k.lower(): v for k, v in component_values(source, code).items()}
        required = ("_chem_comp_atom.atom_id", "_chem_comp_atom.type_symbol",
                    "_chem_comp_bond.atom_id_1", "_chem_comp_bond.atom_id_2")
        if any(field not in values for field in required):
            raise ValueError("Attachment profile requires explicit atom and bond tables")
        elements, bonds, charges, neighbors = _graph(values)
        markers = _stereo(values)
        roles = {k: v for k, v in role_signature(record)["atom_roles"].items() if v != "/"}
        base_atoms = set(roles.values())
        missing = sorted(base_atoms - elements.keys())
        report["source_type_declaration"] = values.get("_chem_comp.type", values.get("_chem_comp.group", [None]))[0]
        report["source_stereo_markers"] = markers
        report["missing_mapped_atoms"] = missing
        if not base_atoms or missing or any(elements[a] in {"H", "D"} for a in base_atoms):
            report["review_reasons"].append("NAR_BASE_MEMBERSHIP_UNRESOLVED")
        elif sum(e not in {"H", "D"} for e in elements.values()) > MAX_HEAVY_ATOMS:
            report["review_reasons"].append("SOURCE_SIZE_LIMIT")
        else:
            searches = [_embeddings(profile, elements, bonds, neighbors, base_atoms) for profile in PROFILES]
            report["profile_searches"] = searches
            matches = [(r["profile"], m) for r in searches for m in r["matches"]]
            complete = all(r["search_complete"] for r in searches)
            report["topology_status"] = ("SEARCH_LIMIT" if not complete else "AMBIGUOUS" if len(matches) > 1
                                         else "MATCH" if matches else "NO_MATCH")
            if report["topology_status"] == "MATCH":
                identifier, binding = matches[0]
                profile = next(p for p in PROFILES if p.identifier == identifier)
                report.update(matched_profile=identifier, bindings=binding)
                inventory = {a["atom_id"]: a for a in selected[0]["inventory"]["atoms"]}
                def atom_evidence(atom):
                    return {"atom_id": atom, "element": elements[atom],
                            "source_hydrogens": sorted(a for a in neighbors[atom] if elements[a] in {"H", "D"}),
                            "formal_charge": charges[atom], "charge_declarations": inventory[atom]["declared_charge_fields"],
                            "stereo_declarations": inventory[atom]["stereo_declarations"]}
                for name, role, chemical_group in profile.ports:
                    atom = binding[role]
                    report["ports"][name] = {
                        **atom_evidence(atom), "chemical_group": chemical_group,
                        "neighbors": [{**atom_evidence(a), "bond_order": bonds[tuple(sorted((a, atom)))]}
                                      for a in sorted(neighbors[atom])],
                        "terminal_state_selection": "NOT_ASSIGNED", "leaving_atoms": "NOT_ASSIGNED",
                    }
                matched_atoms = set(binding.values())
                report["external_heavy_neighbors"] = {
                    role: sorted(a for a in neighbors[atom] if a not in matched_atoms and elements[a] not in {"H", "D"})
                    for role, atom in binding.items()
                }
                declared_attachment = record.get("Glycosidic atom")
                report["base_attachment"] = {"source_atom": binding["base"],
                    "loader_atom": declared_attachment, "matches_loader": declared_attachment == binding["base"]}
                if declared_attachment != binding["base"]:
                    report["review_reasons"].append("NAR_LOADER_ATTACHMENT_DISAGREES_WITH_TOPOLOGY")
            else:
                report["review_reasons"].append("TOPOLOGY_" + report["topology_status"])
    if (source.read_bytes() != original or workbook.read_bytes() != workbook_bytes
            or assessment["input_integrity"] != "UNCHANGED"
            or assessment["inputs"][0]["sha256"] != sha256(original).hexdigest()):
        raise ValueError("Attachment-profile input changed during inspection")
    report["input_integrity"] = "UNCHANGED"
    return report
