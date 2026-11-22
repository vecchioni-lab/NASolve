"""Read a named Pine backbone continuation in the registered source frame."""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from .model_assessment import file_sha256
from .cif_phosphate_image import PhosphateEndpointUnavailable, _inspect_coordinates
from .topostitch_graph import _inverse, build_registered_periodic_graph
from .topostitch_inspect import _unique_object
from .topostitch_periodic import crystal_from_pdb_bytes


@dataclass(frozen=True)
class RegisteredContinuation:
    identifier: int
    registration: Path
    discovery: Path
    continuations: Path


def _endpoint(node, atom):
    mapping = node["mapping"]
    return dict(logical_site=node["logical_site"], coordinate_site=mapping["coordinate_site"] if mapping else None,
                atom=atom, mapping_issues=node["issues"])


def inspect_registered_continuation(model, request, *, geometry, native_receipt):
    if type(request.identifier) is not int or request.identifier < 1:
        raise ValueError("Require a positive registered continuation ID")
    model = Path(model)
    edges = request.continuations.read_bytes()
    graph = build_registered_periodic_graph(
        model, request.discovery, request.registration,
        backbone_continuations=json.loads(edges, object_pairs_hook=_unique_object),
    )
    edge = next((row for row in graph.get("declared_continuations", [])
                 if row["continuation_id"] == request.identifier), None)
    if edge is None:
        raise ValueError(f"Continuation {request.identifier} is absent from the declared backbone connections")
    connection = next(row for row in graph["periodic_graph"]["edges"] if row["edge_id"] == edge["edge_id"])
    nodes = {node["node_id"]: node for node in graph["nodes"]}
    donor = _endpoint(nodes[connection["source"]], "O3'")
    acceptor = _endpoint(nodes[connection["target"]], "P")
    raw = model.read_bytes()
    gemmi, cell, space_group = crystal_from_pdb_bytes(raw)
    oxygen_op = _inverse(gemmi.Op(connection["target_operator_xyz"]), gemmi.Op("x,y,z")).triplet()
    sources = dict(registration_sha256=graph["registration_file_sha256"],
                   discovery_sha256=graph["discovery_file_sha256"], continuations_sha256=sha256(edges).hexdigest())
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
            or file_sha256(request.registration) != sources["registration_sha256"]
            or file_sha256(request.discovery) != sources["discovery_sha256"]
            or file_sha256(request.continuations) != sources["continuations_sha256"]):
        raise ValueError("Registered phosphate inputs changed during inspection")
    result["registered_continuation"] = dict(
        continuation_id=request.identifier, edge_id=edge["edge_id"], copy_id=graph["copy_id"], sources=sources,
        registered_graph_sha256=graph["report_sha256"], source=donor, target=acceptor,
        target_operator_xyz=connection["target_operator_xyz"], oxygen_operator_xyz=oxygen_op,
        measurement_status="UNRESOLVED" if reason else "MEASURED", reason=reason,
        frame="registered source coordinates", runtime_authority=False,
    )
    return result
