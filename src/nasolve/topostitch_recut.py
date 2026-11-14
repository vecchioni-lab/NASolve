"""Read-only registered ASU-representative preview; no coordinate file writer.

Compose existing graph, image and coordinate owners. A representative image is
not a backbone bend or a chemical endpoint declaration. Numerical image checks
remain separate from physical/scattering and native seam qualification.
"""
from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path

from .topostitch_graph import build_registered_periodic_graph, relabel_periodic_graph
from .topostitch_images import inspect_model_orbit_identity
from .topostitch_registration import _fingerprint
from .topostitch_transport import crystallographic_image


def _arithmetic_bound(*points):
    # Numerical coordinate arithmetic only, not a geometric acceptance cutoff.
    return 1e-7 + 64 * max(math.ulp(max(1., abs(v))) for p in points for v in p)


def preview_registered_relabel(model, discovery, registration, *, node_images,
                               expected_registered_graph_sha256, extra_edges=(),
                               coincidence_tolerance_angstrom=.01, max_atom_tests=2_000_000):
    """Bind explicit whole-residue representative images to a fresh source graph.

    Rebuild the registered graph, inspect all present source atom orbits, and
    apply each requested image to that node's exact source atom indices in
    memory. Missing/ambiguous requested nodes refuse. Unrequested/context atoms
    remain exactly unchanged; unresolved graph scope remains visible. This does
    not serialize an ASU, update a registry, assign termini, or authorize a cut.
    """
    paths = [Path(p) for p in (model, discovery, registration)]
    originals = {p: p.read_bytes() for p in paths}
    bound = build_registered_periodic_graph(*paths, extra_edges=extra_edges)
    if bound['report_sha256'] != expected_registered_graph_sha256:
        raise ValueError('Registered graph checksum mismatch; rebuild the proposed cut against current inputs')
    graph = bound['periodic_graph']
    relabeled = relabel_periodic_graph(graph, node_images, expected_graph_sha256=graph['graph_sha256'])
    orbit = inspect_model_orbit_identity(paths[0], expected_sha256=bound['source_model_sha256'],
        coincidence_tolerance_angstrom=coincidence_tolerance_angstrom, max_atom_tests=max_atom_tests)
    atoms = orbit['atoms']; before = [a['position_angstrom'][:] for a in atoms]
    after = [p[:] for p in before]
    nodes = {n['node_id']: n for n in bound['nodes']}
    # Registration forbids overlapping coordinate sites; verify actual atom
    # ownership too before composing independent whole-residue images.
    owners = {}
    for node in nodes.values():
        for i in node['atom_indices']:
            if type(i) is not int or not 0 <= i < len(atoms) or i in owners:
                raise ValueError('Registered graph has ambiguous atom ownership')
            identity = atoms[i]['identity']; binding = node['mapping']
            if (binding is None or identity['residue_code'] != binding['coordinate_residue_code']):
                # Unrequested identity conflicts are retained below; they must
                # not become silently trusted atom owners for a requested cut.
                continue
            owners[i] = node['node_id']
    image_by_node = {n: 'x,y,z' for n in nodes}
    for row in relabeled['proposed_node_images']:
        image_by_node[row['node_id']] = row['image']['operator_xyz']
    crystal = graph['crystal']
    cache = {}
    def image(xyz):
        if xyz not in cache:
            cache[xyz] = crystallographic_image(**crystal, operator_xyz=xyz)
        return cache[xyz]
    moved = set(); groups = []; max_error = 0.
    for number in relabeled['changed_node_ids']:
        node = nodes[number]
        if node['issues'] or not node['atom_indices']:
            raise ValueError('Requested representative has missing or ambiguous registered coordinates')
        transform = image(image_by_node[number]); inverse = transform.inverse()
        for i in node['atom_indices']:
            if owners.get(i) != number:
                raise ValueError('Requested representative lacks exact registered atom ownership')
            after[i] = list(transform.apply(before[i])); restored = inverse.apply(after[i])
            error = max(abs(a-b) for a, b in zip(restored, before[i]))
            if error > _arithmetic_bound(before[i], after[i], restored):
                raise ValueError('Atom image round trip exceeds the numerical arithmetic bound')
            max_error = max(max_error, error); moved.add(i)
        groups.append({'node_id': number, 'copy_id': node['copy_id'], 'logical_site': node['logical_site'],
                       'coordinate_site': node['mapping']['coordinate_site'],
                       'operator_xyz': image_by_node[number], 'atom_indices': node['atom_indices'][:],
                       'protected': node['protected'], 'do_not_connect': node['do_not_connect']})
    fixed = [i for i in range(len(atoms)) if i not in moved]
    if any(before[i] != after[i] for i in fixed):
        raise ValueError('Unrequested atom coordinates changed')
    # O3' is a declared display anchor, never an inferred phosphate/bond center.
    anchors = {}; unavailable = []
    for number, node in nodes.items():
        candidates = [i for i in node['atom_indices'] if atoms[i]['identity']['atom_name'].replace('*', "'") == "O3'"]
        if node['issues'] or len(candidates) != 1:
            unavailable.append(number)
        else:
            anchors[number] = candidates[0]
    edges = []
    for old, new in zip(graph['edges'], relabeled['periodic_graph']['edges']):
        if any(old[k] != new[k] for k in ('edge_id', 'kind', 'source', 'target')):
            raise ValueError('Representative relabeling changed graph topology')
        row = {'edge_id': old['edge_id'], 'kind': old['kind'], 'source_node_id': old['source'],
               'target_node_id': old['target'], 'before_operator_xyz': old['target_operator_xyz'],
               'after_operator_xyz': new['target_operator_xyz'], 'anchor_atom_name': "O3'"}
        if old['source'] not in anchors or old['target'] not in anchors:
            row.update(status='ANCHOR_UNAVAILABLE', missing_node_ids=[n for n in (old['source'], old['target']) if n not in anchors])
        else:
            left, right = anchors[old['source']], anchors[old['target']]
            original = [before[left], list(image(old['target_operator_xyz']).apply(before[right]))]
            proposed = [after[left], list(image(new['target_operator_xyz']).apply(after[right]))]
            expected = [list(image(image_by_node[old['source']]).apply(p)) for p in original]
            tolerance = _arithmetic_bound(*original, *proposed, *expected)
            error = max(abs(a-b) for p, q in zip(proposed, expected) for a, b in zip(p, q))
            old_distance, new_distance = math.dist(*original), math.dist(*proposed)
            if error > tolerance or abs(old_distance-new_distance) > 4*tolerance:
                raise ValueError('Graph edge image geometry changed beyond numerical arithmetic')
            row.update(status='IMAGE_ARITHMETIC_VERIFIED', source_atom_index=left, target_atom_index=right,
                       before_points=original, after_points=proposed,
                       before_anchor_distance_angstrom=old_distance, after_anchor_distance_angstrom=new_distance,
                       maximum_coordinate_error_angstrom=error, coordinate_arithmetic_bound_angstrom=tolerance,
                       distances_are_chemical_restraints=False)
        edges.append(row)
    report = {'schema_version': 1, 'kind': 'topostitch-registered-image-relabel-preview',
              'status': 'PREVIEW_BUILT_REVIEW_REQUIRED', 'source_model_sha256': bound['source_model_sha256'],
              'registered_graph': bound, 'graph_relabeling': relabeled, 'source_orbit_observation': orbit,
              'atom_image_groups': groups, 'proposed_points_angstrom': after,
              'fixed_atom_indices': fixed, 'requested_image_atom_indices': sorted(moved),
              'maximum_atom_round_trip_error_angstrom': max_error,
              'display_anchor': "O3'", 'unavailable_anchor_node_ids': unavailable,
              'edge_image_observations': edges, 'source_bytes_verified': True,
              'coordinates_materialized': False, 'boundary_chemistry_changed': False,
              'physical_identity_validated': False, 'scattering_invariance_validated': False,
              'graphical_review_recorded': False, 'runtime_authority': False, 'changes': [],
              'limitations': ['In-memory representative preview only; source orbit/registration review findings remain applicable',
                              'O3-prime edge lengths are display observations, not chemical bond or pairing restraints',
                              'No ANISOU transport, coordinate serialization, termini, covalent seam policy or native interpretation',
                              'No tile/molecular multiplicity inference, physical deformation, repair or checkpoint adoption']}
    report['preview_sha256'] = _fingerprint(report)
    if any(p.read_bytes() != data for p, data in originals.items()):
        raise ValueError('Registered preview source inputs changed during observation')
    return report
