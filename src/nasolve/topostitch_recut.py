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


def _orbit_permutation(op, operations, gemmi):
    """Right multiplication permutes group cosets; keep left lattice shifts."""
    from .topostitch_graph import _compose, _inverse
    from .topostitch_periodic import _op_key
    members = {_op_key(member): i for i, member in enumerate(operations)}
    if len(members) != len(operations):
        raise ValueError('Space-group representative inventory is not unique')
    def rows(image):
        result = []
        for i, member in enumerate(operations):
            product = _compose(member, image)
            wrapped = gemmi.Op(product.triplet()).wrap()
            j = members.get(_op_key(wrapped))
            if j is None:
                raise ValueError('Representative image does not permute the crystal group')
            delta = [a-b for a, b in zip(product.tran, operations[j].tran)]
            if product.rot != operations[j].rot or any(v % product.DEN for v in delta):
                raise ValueError('Orbit correspondence has a noninteger lattice shift')
            result.append(dict(input_group_index=i, mapped_group_index=j,
                               lattice_translation=[v//product.DEN for v in delta]))
        if sorted(row['mapped_group_index'] for row in result) != list(range(len(operations))):
            raise ValueError('Orbit correspondence is not a bijection')
        return result
    forward = rows(op)
    inverse = rows(_inverse(op, gemmi.Op('x,y,z')))
    for row in forward:
        back = inverse[row['mapped_group_index']]
        if (back['mapped_group_index'] != row['input_group_index']
                or back['lattice_translation'] != [-v for v in row['lattice_translation']]):
            raise ValueError('Orbit correspondence does not invert with exact lattice shifts')
    return forward, inverse


def observe_registered_relabel_orbits(model, discovery, registration, *, node_images,
        expected_registered_graph_sha256, extra_edges=(),
        coincidence_tolerance_angstrom=.01, max_atom_tests=2_000_000,
        max_permutation_rows=200_000):
    """Certify labelled position-orbit reassignment, without physical acceptance.

    For each selected image h and group representative g, record the exact
    permutation and integer n with g*h = T_n*g_permuted. This preserves every
    labelled atom/image over all lattice cells, including repeated images at
    special positions. It does not establish correct occupancies, tensors,
    chemical connectivity, a serialized model or complete scattering invariance.
    """
    from .topostitch_graph import _operator
    from .topostitch_periodic import _crystal, _op_key
    if type(max_permutation_rows) is not int or not 1 <= max_permutation_rows <= 2_000_000:
        raise ValueError('Require a bounded positive orbit permutation row budget')
    paths = [Path(p) for p in (model, discovery, registration)]
    originals = {p: p.read_bytes() for p in paths}
    preview = preview_registered_relabel(*paths, node_images=node_images,
        expected_registered_graph_sha256=expected_registered_graph_sha256, extra_edges=extra_edges,
        coincidence_tolerance_angstrom=coincidence_tolerance_angstrom, max_atom_tests=max_atom_tests)
    if _fingerprint({k:v for k,v in preview.items() if k != 'preview_sha256'}) != preview['preview_sha256']:
        raise ValueError('Registered preview checksum differs')
    crystal = preview['registered_graph']['periodic_graph']['crystal']
    gemmi, cell, group = _crystal(crystal['cell_parameters'], crystal['space_group'])
    operations = sorted(group.operations(), key=_op_key)
    members = {_op_key(op) for op in operations}
    atoms = preview['source_orbit_observation']['atoms']
    points = preview['proposed_points_angstrom']
    if len(points) != len(atoms):
        raise ValueError('Orbit correspondence atom inventory differs')
    assignments = {}
    def assign(xyz, indices):
        op = _operator(xyz, gemmi, members)
        assignments.setdefault(op.triplet(), []).extend(indices)
    if preview['fixed_atom_indices']:
        assign('x,y,z', preview['fixed_atom_indices'])
    for row in preview['atom_image_groups']:
        assign(row['operator_xyz'], row['atom_indices'])
    indices = [i for values in assignments.values() for i in values]
    if any(type(i) is not int for i in indices) or sorted(indices) != list(range(len(atoms))):
        raise ValueError('Orbit correspondence must own every source atom exactly once')
    rows = 2*len(operations)*len(assignments)
    if rows > max_permutation_rows:
        raise ValueError('Orbit permutation row budget exceeded')
    tables = []; max_error = 0.; fixed = set(preview['fixed_atom_indices'])
    for xyz, indices in sorted(assignments.items()):
        op = _operator(xyz, gemmi, members)
        forward, inverse = _orbit_permutation(op, operations, gemmi)
        transform = cell.op_as_transform(op)
        for i in indices:
            before = atoms[i]['position_angstrom']; after = points[i]
            if len(after) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in after):
                raise ValueError('Orbit correspondence requires finite Cartesian points')
            expected = list(transform.apply(gemmi.Position(*before)))
            error = max(abs(a-b) for a,b in zip(after, expected))
            if (error > _arithmetic_bound(before, after, expected)
                    or i in fixed and before != after):
                raise ValueError('Orbit correspondence does not bind the proposed coordinates')
            max_error = max(max_error, error)
        tables.append(dict(operator_xyz=xyz, atom_indices=sorted(indices), forward=forward, inverse=inverse))
    report = dict(schema_version=1, kind='topostitch-registered-orbit-permutation-observation',
        status='EXACT_LABELLED_ORBIT_PERMUTATIONS', source_model_sha256=preview['source_model_sha256'],
        registered_graph_sha256=expected_registered_graph_sha256, preview_sha256=preview['preview_sha256'],
        proposed_points_sha256=_fingerprint(points), crystal=crystal,
        space_group_operations=[op.triplet() for op in operations], image_assignments=tables,
        atom_count=len(atoms), labelled_cell_image_count=len(atoms)*len(operations),
        permutation_rows=rows, max_permutation_rows=max_permutation_rows,
        maximum_coordinate_binding_error_angstrom=max_error,
        source_orbit_status=preview['source_orbit_observation']['assessment'],
        correspondence='g*h = T_n*g_mapped; (atom,g,lattice_m) maps to (same_atom,g_mapped,lattice_m+n)',
        lattice_action='Translations act after the group operation; group indices are zero-based',
        source_bytes_verified=True, labelled_position_multiplicity_preserved=True,
        special_position_weights_qualified=False, physical_identity_validated=False,
        scattering_invariance_validated=False, coordinates_materialized=False, runtime_authority=False,
        limitations=['Labelled position images only; no deduplication, special-position occupancy correction or molecule identity inference',
                     'Exact group algebra plus floating coordinate binding; no ANISOU transport or serialized-coordinate proof',
                     'No chemical seam, native restraint, refinement, GUI review or checkpoint authority'])
    if any(p.read_bytes() != value for p,value in originals.items()):
        raise ValueError('Orbit source inputs changed during observation')
    report['report_sha256'] = _fingerprint(report)
    return report
