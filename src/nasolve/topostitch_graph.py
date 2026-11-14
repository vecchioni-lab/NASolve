"""Declared periodic connectivity and exact image-loop algebra for Pine.

An edge u -> v means x_u is connected to g(x_v). Different edge kinds stay
separate. This is a quotient graph of caller-declared identities, not proof
that the represented molecular orbits are distinct or chemically connected.
"""
from __future__ import annotations

from collections import deque
from hashlib import sha256
import json
from pathlib import Path

from .topostitch_periodic import _crystal, _image_record, _op_key
from .topostitch_registration import _fingerprint

EDGE_KINDS = ('covalent_backbone', 'base_pairing', 'stacking', 'symmetry_correspondence')
_MAX_NODES = 10_000
_MAX_EDGES = 20_000
_MAX_NUMERATOR = 1_000_000


def _bounded(op):
    if any(abs(v) > _MAX_NUMERATOR for v in _op_key(op)):
        raise ValueError('Periodic graph image exceeds exact arithmetic budget')
    return op


def _compose(a, b):
    """a after b; check integer arithmetic before entering Gemmi's C++ ints."""
    den = a.DEN
    if b.DEN != den:
        raise ValueError('Inconsistent crystallographic operator denominator')
    products = [sum(a.rot[i][k]*b.rot[k][j] for k in range(3))
                for i in range(3) for j in range(3)]
    offsets = [sum(a.rot[i][k]*b.tran[k] for k in range(3)) for i in range(3)]
    if any(v % den for v in products+offsets):
        raise ValueError('Operator composition is not exactly representable')
    expected = tuple(v//den for v in products)+tuple(offsets[i]//den+a.tran[i] for i in range(3))
    if any(abs(v) > _MAX_NUMERATOR for v in expected):
        raise ValueError('Periodic graph image exceeds exact arithmetic budget')
    result = a.combine(b)
    if _op_key(result) != expected:
        raise ValueError('Crystallographic operator composition disagrees with exact arithmetic')
    return result


def _inverse(op, identity):
    inverse = _bounded(op.inverse())
    if _op_key(_compose(op, inverse)) != _op_key(identity):
        raise ValueError('Crystallographic operator inverse failed exact check')
    return inverse


def _operator(xyz, gemmi, members):
    if not isinstance(xyz, str) or not xyz.strip() or len(xyz) > 128:
        raise ValueError('Require a bounded explicit image operator')
    try:
        op = _bounded(gemmi.Op(xyz))
    except RuntimeError as exc:
        raise ValueError('Invalid periodic edge image') from exc
    if _op_key(gemmi.Op(op.triplet()).wrap()) not in members:
        raise ValueError('Periodic edge image does not belong to the declared space group')
    return op


def describe_periodic_graph(node_ids, edges, *, cell_parameters, space_group):
    """Describe a bounded typed multigraph and its fundamental image loops.

    Node/edge numbers are caller-owned positive integers, not PDB serials.
    Parallel edges and nonidentity self loops are retained. Each component's
    deterministic spanning tree stores parent edges and exact root images;
    every remaining edge supplies one independent graph cycle. A nonidentity
    loop is legitimate periodic winding, never an automatic closure failure.
    """
    if (not isinstance(node_ids, (list, tuple)) or not 1 <= len(node_ids) <= _MAX_NODES
            or any(type(n) is not int or n < 1 for n in node_ids)
            or len(set(node_ids)) != len(node_ids)):
        raise ValueError('Require 1..10000 distinct positive integer node identifiers')
    if not isinstance(edges, (list, tuple)) or len(edges) > _MAX_EDGES:
        raise ValueError('Periodic graph requires at most 20000 explicit edges')
    gemmi, _, group = _crystal(cell_parameters, space_group)
    identity = gemmi.Op('x,y,z')
    members = {_op_key(op) for op in group.operations()}
    nodes = sorted(node_ids)
    adjacency = {n: [] for n in nodes}
    definitions, operators, seen = [], {}, set()
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {'edge_id', 'kind', 'source', 'target', 'target_operator_xyz'}:
            raise ValueError('Malformed periodic edge fields')
        number = edge['edge_id']
        if type(number) is not int or number < 1 or number in seen:
            raise ValueError('Require distinct positive integer edge identifiers')
        if any(type(edge[k]) is not int or edge[k] not in adjacency for k in ('source', 'target')):
            raise ValueError('Periodic edge references an unknown node')
        if edge['kind'] not in EDGE_KINDS:
            raise ValueError('Unknown periodic edge kind')
        op = _operator(edge['target_operator_xyz'], gemmi, members)
        reverse = _inverse(op, identity)
        seen.add(number)
        operators[number] = op
        definitions.append({**edge, 'target_operator_xyz': op.triplet(),
                            'target_image': _image_record(op, gemmi)})
        adjacency[edge['source']].append((number, 1, edge['target'], op))
        adjacency[edge['target']].append((number, -1, edge['source'], reverse))
    definitions.sort(key=lambda e: e['edge_id'])
    for values in adjacency.values():
        values.sort(key=lambda row: (row[0], -row[1]))
    frames, roots, tree_edges, components = {}, {}, set(), []
    for root in nodes:
        if root in frames:
            continue
        frames[root], roots[root] = identity, root
        queue = deque([root])
        tree = [{'node_id': root, 'parent_node_id': None, 'edge_id': None,
                 'direction': None, 'root_image': _image_record(identity, gemmi)}]
        while queue:
            source = queue.popleft()
            for number, direction, target, op in adjacency[source]:
                if target in frames:
                    continue
                frames[target] = _compose(frames[source], op)
                roots[target] = root
                tree_edges.add(number)
                tree.append({'node_id': target, 'parent_node_id': source,
                             'edge_id': number, 'direction': direction,
                             'root_image': _image_record(frames[target], gemmi)})
                queue.append(target)
        components.append({'root_node_id': root, 'tree': tree, 'cycles': []})
    by_root = {c['root_node_id']: c for c in components}
    for edge in definitions:
        number = edge['edge_id']
        if number in tree_edges:
            continue
        source, target = edge['source'], edge['target']
        loop = _compose(_compose(frames[source], operators[number]), _inverse(frames[target], identity))
        classification = ('IDENTITY' if _op_key(loop) == _op_key(identity) else
                          'LATTICE_TRANSLATION' if loop.rot == identity.rot else 'ROTATION_AND_TRANSLATION')
        by_root[roots[source]]['cycles'].append({
            'edge_id': number, 'source': source, 'target': target, 'edge_kind': edge['kind'],
            'walk': 'root-to-source tree path, forward edge, reversed root-to-target tree path',
            'classification': classification, 'root_image': _image_record(loop, gemmi)})
    report = {'schema_version': 1, 'kind': 'topostitch-declared-periodic-graph',
              'algorithm': 'exact-declared-periodic-graph-v1',
              'crystal': {'cell_parameters': list(cell_parameters), 'space_group': group.xhm()},
              'node_ids': nodes, 'edges': definitions, 'components': components,
              'cycle_count': len(definitions)-len(nodes)+len(components),
              'edge_convention': 'source identity image to target_operator_xyz(target)',
              'physical_orbit_identity_validated': False, 'chemical_connectivity_validated': False,
              'runtime_authority': False, 'changes': [],
              'limitations': ['Declared quotient identities; no stabilizer or multiplicity quotient',
                              'Mixed edge-kind loops do not prove covalent strand closure',
                              'No coordinates, termini, restraints or checkpoints are changed']}
    report['graph_sha256'] = _fingerprint(report)
    return report


def build_registered_periodic_graph(model, discovery_path, registration_path, *, extra_edges=()):
    """Bind one discovery copy's declared routes to source bytes and Pine sites.

    All logical target sites are retained, including missing mappings and sites
    outside declared routes. Other registered copies and unrepresented atoms
    remain explicit excluded scope. Extra noncovalent edges are caller intent,
    never inferred from endpoint proximity. Representation-seam covalent links
    need a future explicit chemistry-aware route adapter.
    """
    from .construct_registration import validate_construct_registration
    from .topostitch_inspect import _unique_object, load_registered_end_assignments
    from .topostitch_periodic import crystal_from_pdb_bytes
    from .topostitch_recipe import model_atom_rows
    from .topostitch_coordinates import _read_atoms
    from .topostitch_registration import _coordinate_site
    expected, _, discovery_hash, mapping = load_registered_end_assignments(
        model, discovery_path, registration_path)
    if 'discovery_assessment' not in mapping:
        raise ValueError('Periodic graph requires a registered end-discovery manifest')
    data = Path(model).read_bytes()
    registration_bytes = Path(registration_path).read_bytes()
    if (sha256(data).hexdigest() != expected or sha256(registration_bytes).hexdigest() != mapping['registration_file_sha256']
            or sha256(Path(discovery_path).read_bytes()).hexdigest() != discovery_hash):
        raise ValueError('Graph inputs changed during registration resolution')
    registration = validate_construct_registration(json.loads(registration_bytes, object_pairs_hook=_unique_object))
    declared = mapping['discovery_assessment']['inputs']
    copy = next(c for c in registration['copies'] if c['copy_id'] == declared['copy_id'])
    if len(registration['target']['sites']) > _MAX_NODES:
        raise ValueError('Registered periodic graph exceeds node budget')
    rows = model_atom_rows(data)
    residue_groups = _read_atoms(data)
    atom_groups = {}
    for index, row in enumerate(rows):
        key = (row['chain'], row['residue_number'], row['insertion_code'])
        atom_groups.setdefault(key, []).append(index)
    mapped = {r['logical_site']: r for r in copy['mappings']}
    owner = {site: s['strand_id'] for s in declared['strands'] for site in s['sites']}
    nodes, used = [], set()
    for number, logical in enumerate(registration['target']['sites'], 1):
        binding = mapped.get(logical)
        indices, issues = [], []
        if binding is None:
            issues.append('MISSING_LOGICAL_MAPPING')
        else:
            try:
                site = _coordinate_site(binding['coordinate_site'])
            except ValueError:
                issues.append('UNSUPPORTED_COORDINATE_IDENTIFIER')
            else:
                indices = atom_groups.get((site.chain, site.residue_number, site.insertion_code), [])
                if len(residue_groups.get(site, {})) > 1:
                    issues.append('AMBIGUOUS_COORDINATE_SITE')
                if not indices:
                    issues.append('MISSING_COORDINATE_SITE')
                elif {rows[i]['residue_code'] for i in indices} != {binding['coordinate_residue_code']}:
                    issues.append('COORDINATE_IDENTITY_MISMATCH')
                if any(rows[i]['altloc'] for i in indices):
                    issues.append('ALTERNATE_CONFORMER')
            if binding['identity_relation'] != 'SAME':
                issues.append('TARGET_IDENTITY_MISMATCH')
        used.update(indices)
        nodes.append({'node_id': number, 'copy_id': copy['copy_id'], 'logical_site': logical,
                      'mapping': binding, 'atom_indices': indices, 'issues': issues,
                      'strand_id': owner.get(logical), 'protected': logical in declared['protected_sites'],
                      'do_not_connect': logical in declared['do_not_connect_sites']})
    numbers = {n['logical_site']: n['node_id'] for n in nodes}
    edges, origins = [], []
    def add(kind, a, b, xyz, origin):
        number = len(edges)+1
        edges.append({'edge_id': number, 'kind': kind, 'source': numbers[a],
                      'target': numbers[b], 'target_operator_xyz': xyz})
        origins.append({'edge_id': number, 'origin': origin})
    for strand in declared['strands']:
        for a, b in zip(strand['sites'], strand['sites'][1:]):
            add('covalent_backbone', a, b, 'x,y,z', {'strand_id': strand['strand_id']})
    for a, b in declared['duplex_pairs']:
        add('base_pairing', a, b, 'x,y,z', 'declared_duplex_core')
    if not isinstance(extra_edges, (list, tuple)) or len(extra_edges)+len(edges) > _MAX_EDGES:
        raise ValueError('Registered periodic graph exceeds edge budget')
    for row in extra_edges:
        if not isinstance(row, dict) or set(row) != {'kind', 'source_site', 'target_site', 'target_operator_xyz'}:
            raise ValueError('Malformed declared extra edge')
        if row['kind'] not in EDGE_KINDS[1:]:
            raise ValueError('Extra covalent edges require a future chemistry-aware seam declaration')
        if any(not isinstance(row[k], str) or row[k] not in numbers for k in ('source_site', 'target_site')):
            raise ValueError('Unknown logical site in declared extra edge')
        add(row['kind'], row['source_site'], row['target_site'], row['target_operator_xyz'], 'caller_declared_extra_edge')
    _, cell, group = crystal_from_pdb_bytes(data)
    graph = describe_periodic_graph(list(numbers.values()), edges,
                                   cell_parameters=list(cell.parameters), space_group=group)
    report = {'schema_version': 1, 'kind': 'topostitch-registered-periodic-graph',
              'source_model_sha256': expected, 'registration_file_sha256': mapping['registration_file_sha256'],
              'discovery_file_sha256': discovery_hash, 'copy_id': copy['copy_id'], 'copy_status': copy['status'],
              'nodes': nodes, 'declared_routes': declared['strands'], 'edge_origins': origins,
              'declared_pairing_inventory_complete': declared['pairing_inventory_complete'],
              'discovery_assessment': mapping['discovery_assessment'], 'periodic_graph': graph,
              'scope': {'other_registered_copies': [c['copy_id'] for c in registration['copies'] if c != copy],
                        'outside_declared_routes': [n['node_id'] for n in nodes if n['strand_id'] is None],
                        'unrepresented_atom_indices': sorted(set(range(len(rows)))-used),
                        'unresolved_node_ids': [n['node_id'] for n in nodes if n['issues']],
                        'whole_asu_graph_validated': False, 'tile_multiplicity_inferred': False},
              'source_bytes_verified': True, 'runtime_authority': False, 'changes': []}
    report['report_sha256'] = _fingerprint(report)
    return report


def relabel_periodic_graph(report, node_images, *, expected_graph_sha256):
    """Preview y_v = h_v(x_v) by exact g' = h_u g h_v^-1 edge relabeling.

    Recompute and compare the complete source report before using it. Unlisted
    nodes retain their identity representative. Verify every fundamental loop
    by root-image conjugacy and recover the original graph by inverse relabeling.
    These checks establish algebra only, not molecular/scattering equivalence.
    """
    if not isinstance(report, dict) or report.get('graph_sha256') != expected_graph_sha256:
        raise ValueError('Periodic graph checksum mismatch')
    try:
        crystal = report['crystal']
        edges = [{k: e[k] for k in ('edge_id', 'kind', 'source', 'target', 'target_operator_xyz')}
                 for e in report['edges']]
        before = describe_periodic_graph(report['node_ids'], edges, **crystal)
    except (KeyError, TypeError) as exc:
        raise ValueError('Malformed periodic graph report') from exc
    if before != report:
        raise ValueError('Stale or inconsistent periodic graph; recompute from declared inputs')
    if not isinstance(node_images, (list, tuple)) or len(node_images) > len(before['node_ids']):
        raise ValueError('Require at most one explicit image per graph node')
    gemmi, _, group = _crystal(crystal['cell_parameters'], crystal['space_group'])
    members = {_op_key(op) for op in group.operations()}
    identity = gemmi.Op('x,y,z')
    images = {n: identity for n in before['node_ids']}
    seen = set()
    for row in node_images:
        if not isinstance(row, dict) or set(row) != {'node_id', 'operator_xyz'}:
            raise ValueError('Malformed graph node image assignment')
        node = row['node_id']
        if type(node) is not int or node not in images or node in seen:
            raise ValueError('Node image requires a unique known node identifier')
        seen.add(node)
        images[node] = _operator(row['operator_xyz'], gemmi, members)
    inverses = {n: _inverse(op, identity) for n, op in images.items()}

    def transformed(source_edges, forward, reverse):
        return [{**e, 'target_operator_xyz': _compose(
            _compose(forward[e['source']], gemmi.Op(e['target_operator_xyz'])),
            reverse[e['target']]).triplet()} for e in source_edges]

    after_edges = transformed(edges, images, inverses)
    after = describe_periodic_graph(before['node_ids'], after_edges, **crystal)
    loop_checks = []
    for old_component, new_component in zip(before['components'], after['components']):
        root = old_component['root_node_id']
        if new_component['root_node_id'] != root or len(old_component['cycles']) != len(new_component['cycles']):
            raise ValueError('Relabeling changed the declared graph cycle basis')
        for old, new in zip(old_component['cycles'], new_component['cycles']):
            expected = _compose(_compose(images[root], gemmi.Op(old['root_image']['operator_xyz'])), inverses[root])
            if old['edge_id'] != new['edge_id'] or _op_key(expected) != _op_key(gemmi.Op(new['root_image']['operator_xyz'])):
                raise ValueError('Periodic loop did not transform by root conjugacy')
            loop_checks.append({'root_node_id': root, 'edge_id': old['edge_id'],
                                'expected_root_image': _image_record(expected, gemmi), 'exact_match': True})
    restored = describe_periodic_graph(before['node_ids'], transformed(after_edges, inverses, images), **crystal)
    if restored != before:
        raise ValueError('Inverse image relabeling failed exact graph round trip')
    proposed = [{'node_id': n, 'image': _image_record(images[n], gemmi)} for n in sorted(seen)]
    result = {'schema_version': 1, 'kind': 'topostitch-periodic-image-relabel-preview',
              'source_graph_sha256': before['graph_sha256'], 'proposed_node_images': proposed,
              'changed_node_ids': [n for n in sorted(seen) if _op_key(images[n]) != _op_key(identity)],
              'periodic_graph': after, 'cycle_conjugacy_checks': loop_checks,
              'exact_inverse_graph_round_trip': True, 'coordinates_materialized': False,
              'physical_orbit_identity_validated': False, 'scattering_invariance_validated': False,
              'runtime_authority': False, 'changes': [],
              'limitations': ['Graph image labels only; no coordinate or chemistry edits',
                              'Node orbit identity and full source binding need the registered physical audit',
                              'Not an approved ASU cut, persistent choice or graphical review']}
    result['preview_sha256'] = _fingerprint(result)
    return result
