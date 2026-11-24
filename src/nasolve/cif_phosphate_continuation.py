"""Read a named Pine backbone continuation in the registered source frame."""
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from .model_assessment import file_sha256
from .cif_phosphate_image import PDB_IMAGE_SEPARATION_A, PhosphateEndpointUnavailable, _inspect_coordinates
from .refinement_link_geometry import _model_labels
from .topostitch_graph import _inverse, build_registered_periodic_graph
from .topostitch_images import closest_atom_images
from .topostitch_inspect import _unique_object
from .topostitch_periodic import crystal_from_pdb_bytes


@dataclass(frozen=True)
class RegisteredContinuation:
    identifier: int
    registration: Path
    discovery: Path
    continuations: Path


def _sources_match(request, sources):
    return (file_sha256(request.registration) == sources["registration_sha256"]
            and file_sha256(request.discovery) == sources["discovery_sha256"]
            and file_sha256(request.continuations) == sources["continuations_sha256"])


def _endpoint(node, atom):
    mapping = node["mapping"]
    return dict(logical_site=node["logical_site"], coordinate_site=mapping["coordinate_site"] if mapping else None,
                atom=atom, mapping_issues=node["issues"])


def _registration(model, registration, discovery, continuations):
    edges = continuations.read_bytes()
    graph = build_registered_periodic_graph(
        model, discovery, registration,
        backbone_continuations=json.loads(edges, object_pairs_hook=_unique_object),
    )
    sources = dict(registration_sha256=graph["registration_file_sha256"],
                   discovery_sha256=graph["discovery_file_sha256"], continuations_sha256=sha256(edges).hexdigest())
    return graph, sources


def inspect_registered_continuation(model, request, *, geometry, native_receipt):
    if type(request.identifier) is not int or request.identifier < 1:
        raise ValueError("Require a positive registered continuation ID")
    model = Path(model)
    graph, sources = _registration(model, request.registration, request.discovery, request.continuations)
    edge = next((row for row in graph.get("declared_continuations", [])
                 if row["continuation_id"] == request.identifier), None)
    if edge is None:
        raise ValueError(f"Continuation {request.identifier} is absent from the declared backbone connections")
    return _inspect_registered_edge(model, request, graph, sources, edge, geometry, native_receipt)


def inspect_registered_backbone(model, registration, discovery, continuations):
    """Measure every declaration against one verified graph, in declaration-ID order."""
    model, registration, discovery, continuations = map(Path, (model, registration, discovery, continuations))
    graph, sources = _registration(model, registration, discovery, continuations)
    edges = graph.get("declared_continuations")
    if not edges:
        raise ValueError("Require at least one declared crystal backbone continuation")
    return [_inspect_registered_edge(model, RegisteredContinuation(edge["continuation_id"], registration,
                discovery, continuations), graph, sources, edge, None, None) for edge in edges]


def _inspect_registered_edge(model, request, graph, sources, edge, geometry, native_receipt):
    connection = next(row for row in graph["periodic_graph"]["edges"] if row["edge_id"] == edge["edge_id"])
    nodes = {node["node_id"]: node for node in graph["nodes"]}
    donor = _endpoint(nodes[connection["source"]], "O3'")
    acceptor = _endpoint(nodes[connection["target"]], "P")
    raw = model.read_bytes()
    gemmi, cell, space_group = crystal_from_pdb_bytes(raw)
    oxygen_op = _inverse(gemmi.Op(connection["target_operator_xyz"]), gemmi.Op("x,y,z")).triplet()
    reason = None
    if donor["mapping_issues"] or acceptor["mapping_issues"]:
        reason = "The registered mapping leaves one or both endpoints unresolved"
    else:
        try:
            result = _inspect_coordinates(
                model, phosphate=acceptor["coordinate_site"], o3=donor["coordinate_site"], o3_image=oxygen_op,
                geometry=geometry, native_receipt=native_receipt,
            )
        except PhosphateEndpointUnavailable as exc:
            reason = str(exc)
    if reason:
        printed = None
        if geometry is not None:
            printed = dict(status="UNASSESSED", reason=reason, geometry_sha256=file_sha256(Path(geometry)))
        result = dict(policy_id="phosphate-image-observation-v1", model_sha256=sha256(raw).hexdigest(),
                      phosphate=None, o3=None, o3_image=None, distance_A=None, phosphate_atoms=None,
                      coordinate_angles_degrees=None, printed_geometry=printed, scientific_approval="NOT_ASSESSED",
                      cell=list(cell.parameters), space_group=space_group)
        if native_receipt is not None:
            result["native_reference_links"] = dict(status="UNASSESSED", reason=reason, groups=[])
    if (result["model_sha256"] != graph["source_model_sha256"] or sha256(raw).hexdigest() != result["model_sha256"]
            or file_sha256(model) != result["model_sha256"]
            or not _sources_match(request, sources)):
        raise ValueError("Registered phosphate inputs changed during inspection")
    result["registered_continuation"] = dict(
        continuation_id=request.identifier, edge_id=edge["edge_id"], copy_id=graph["copy_id"], sources=sources,
        registered_graph_sha256=graph["report_sha256"], source=donor, target=acceptor,
        target_operator_xyz=connection["target_operator_xyz"], oxygen_operator_xyz=oxygen_op,
        measurement_status="UNRESOLVED" if reason else "MEASURED", reason=reason,
        frame="registered source coordinates", runtime_authority=False,
    )
    return result


def _endpoint_atoms(model, sites):
    raw, labels = _model_labels(model)
    atoms = {}
    for line in raw.decode("ascii").splitlines():
        if line[:6] not in ("ATOM  ", "HETATM"):
            continue
        identity, xyz = labels[line[12:27]]
        if identity[0] in sites:
            occupancy = float(line[54:60])
            if not isfinite(occupancy) or not 0 <= occupancy <= 1:
                raise ValueError("Invalid occupancy at a registered phosphate endpoint")
            key = (*identity, line[:6], line[76:78].strip().upper(), line[78:80].strip(), occupancy > 0)
            atoms[key] = xyz
    return raw, atoms


def inspect_inherited_continuation(source_model, child_model, request, *, geometry=None, native_receipt=None):
    """Follow the two registered residues into a coordinate refinement in the same frame.

    Inspect every occupied atom in those residues against its own source position.
    The original mate must remain meaningful. No new partner or image is chosen.
    Checkpoint ancestry is verified separately by the run reader.
    """
    source_model, child_model = Path(source_model), Path(child_model)
    source = inspect_registered_continuation(source_model, request, geometry=None, native_receipt=None)
    return _inherit_measured(source_model, child_model, request, source, geometry=geometry, native_receipt=native_receipt)


def _inherit_measured(source_model, child_model, request, source, *, geometry=None, native_receipt=None):
    """Transfer a measured member of a verified source registration to the same named residues."""
    edge = source["registered_continuation"]
    if edge["measurement_status"] != "MEASURED":
        raise ValueError("Cannot transfer an unresolved phosphate registration")
    sites = (edge["source"]["coordinate_site"], edge["target"]["coordinate_site"])
    original, prior = _endpoint_atoms(source_model, sites)
    current, present = _endpoint_atoms(child_model, sites)
    gemmi, cell, setting = crystal_from_pdb_bytes(original)
    _, child_cell, child_setting = crystal_from_pdb_bytes(current)
    group = gemmi.find_spacegroup_by_name(setting)
    if (tuple(cell.parameters) != tuple(child_cell.parameters)
            or group.hall != gemmi.find_spacegroup_by_name(child_setting).hall):
        raise ValueError("Registered phosphate requires the same crystal frame")
    if prior.keys() != present.keys():
        raise ValueError("The two registered residues changed chemical identities or atom occupancy status")
    distances = []
    same_bytes = original == current
    for key, xyz in prior.items():
        if key[-1]:
            if same_bytes:
                distances.append(0.)
                continue
            first, second = closest_atom_images(xyz, present[key], cell, group, gemmi)
            if (first["image"]["operator_xyz"] != "x,y,z"
                    or second["distance_A"] - first["distance_A"] <= PDB_IMAGE_SEPARATION_A):
                raise ValueError(f"Changed or ambiguous crystal representative at {key[0]} {key[2]}")
            distances.append(first["distance_A"])
    result = _inspect_coordinates(child_model, o3=sites[0], phosphate=sites[1], o3_image=source["o3_image"],
                                  geometry=geometry, native_receipt=native_receipt)
    if (source["model_sha256"] != sha256(original).hexdigest() or file_sha256(source_model) != source["model_sha256"]
            or result["model_sha256"] != sha256(current).hexdigest() or file_sha256(child_model) != result["model_sha256"]
            or not _sources_match(request, edge["sources"])):
        raise ValueError("Registered phosphate inputs changed during frame transfer")
    result["registered_continuation"] = dict(edge, frame="same crystal representatives in descendant coordinates",
        frame_transfer=dict(source_model_sha256=source["model_sha256"], child_model_sha256=result["model_sha256"],
                            method="identical model bytes" if same_bytes else "nearest image of each named atom",
                            atom_count=len(distances), max_atom_shift_A=max(distances)))
    return result
