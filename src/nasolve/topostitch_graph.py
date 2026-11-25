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


def _boundary_continuations(values, declared):
    """Validate explicit directed seam intent within the existing discovery copy.

    A declaration resolves representation boundaries only. It cannot rewrite a
    true/unknown boundary or override a do-not-connect choice by proximity.
    Exact crystallographic operators are validated by the common graph owner.
    """
    if not isinstance(values, (list, tuple)) or len(values) > _MAX_EDGES:
        raise ValueError('Require a bounded array of explicit backbone continuations')
    owners = {site: (route, i) for route in declared['strands'] for i, site in enumerate(route['sites'])}
    ids, sources, targets, result = set(), set(), set(), []
    fields = {'continuation_id', 'source_site', 'target_site', 'target_operator_xyz'}
    for row in values:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError('Malformed backbone continuation fields')
        number = row['continuation_id']
        if type(number) is not int or number < 1 or number in ids:
            raise ValueError('Require unique positive integer continuation identifiers')
        if any(not isinstance(row[k], str) or row[k] not in owners for k in ('source_site', 'target_site')):
            raise ValueError('Unknown logical route site in backbone continuation')
        source, target = row['source_site'], row['target_site']
        if source in sources or target in targets:
            raise ValueError('A backbone boundary cannot have competing incoming or outgoing partners')
        left, i = owners[source]; right, j = owners[target]
        if i != len(left['sites'])-1:
            raise ValueError('Continuation source must be a declared 3-prime route endpoint')
        if j != 0:
            raise ValueError('Continuation target must be a declared 5-prime route endpoint')
        if left['three_prime_boundary'] != 'representation' or right['five_prime_boundary'] != 'representation':
            raise ValueError('Explicit continuation requires two declared representation boundaries')
        if {source, target} & set(declared['do_not_connect_sites']):
            raise ValueError('Backbone continuation conflicts with a do-not-connect declaration')
        ids.add(number); sources.add(source); targets.add(target)
        result.append(dict(row))
    return sorted(result, key=lambda row: row['continuation_id'])


def build_registered_periodic_graph(model, discovery_path, registration_path, *, extra_edges=(), backbone_continuations=()):
    """Bind one discovery copy's declared routes to source bytes and Pine sites.

    All logical target sites are retained, including missing mappings and sites
    outside declared routes. Other registered copies and unrepresented atoms
    remain explicit excluded scope. Extra noncovalent edges are caller intent,
    never inferred from endpoint proximity. Explicit directed continuations may
    resolve two representation boundaries without a bond or chemistry edit.
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
    continuations = _boundary_continuations(backbone_continuations, declared)
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
    if not isinstance(extra_edges, (list, tuple)) or len(extra_edges)+len(edges)+len(continuations) > _MAX_EDGES:
        raise ValueError('Registered periodic graph exceeds edge budget')
    for row in extra_edges:
        if not isinstance(row, dict) or set(row) != {'kind', 'source_site', 'target_site', 'target_operator_xyz'}:
            raise ValueError('Malformed declared extra edge')
        if row['kind'] not in EDGE_KINDS[1:]:
            raise ValueError('Extra covalent edges require a future chemistry-aware seam declaration')
        if any(not isinstance(row[k], str) or row[k] not in numbers for k in ('source_site', 'target_site')):
            raise ValueError('Unknown logical site in declared extra edge')
        add(row['kind'], row['source_site'], row['target_site'], row['target_operator_xyz'], 'caller_declared_extra_edge')
    for row in continuations:
        add('covalent_backbone', row['source_site'], row['target_site'], row['target_operator_xyz'],
            {'continuation_id': row['continuation_id'], 'source': 'caller_declared_representation_boundary'})
        row['edge_id'] = len(edges)
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
    if continuations:
        by_edge = {edge['edge_id']: edge for edge in graph['edges']}
        report['declared_continuations'] = [{**row, 'target_operator_xyz': by_edge[row['edge_id']]['target_operator_xyz']}
                                            for row in continuations]
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
    if _fingerprint(before) != _fingerprint(report):
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


def propose_forest_representatives(report, *, selected_edge_ids, anchor_node_ids,
                                   expected_graph_sha256):
    """Calculate images along an explicitly selected forest of declared edges.

    Each selected component requires exactly one caller-chosen node whose
    representative stays fixed. Selected edges then have identity partner images;
    unselected edges retain any necessary periodic winding. This is an algebraic
    display/cut proposal, not a search, chemical connection or approved ASU.
    """
    initial=relabel_periodic_graph(report,[],expected_graph_sha256=expected_graph_sha256)
    graph=initial['periodic_graph'];by_edge={e['edge_id']:e for e in graph['edges']}
    for values,known,name in ((selected_edge_ids,by_edge,'selected edge'),
                               (anchor_node_ids,set(graph['node_ids']),'anchor node')):
        if (not isinstance(values,(list,tuple)) or len(values)>len(known)
                or any(type(v) is not int or v not in known for v in values)
                or len(set(values))!=len(values)):
            raise ValueError(f'Require distinct known integer {name} identifiers')
    selected=sorted(selected_edge_ids);anchors=sorted(anchor_node_ids)
    active=sorted({by_edge[e][k] for e in selected for k in ('source','target')})
    if not set(anchors)<=set(active):raise ValueError('Anchor nodes must belong to the selected forest')
    images=[];components=[]
    if selected:
        rows=[{k:by_edge[e][k] for k in ('edge_id','kind','source','target','target_operator_xyz')} for e in selected]
        forest=describe_periodic_graph(active,rows,**graph['crystal'])
        if forest['cycle_count']:raise ValueError('Selected edges must form a forest; choose which cycle edges to leave periodic')
        by_node={r['node_id']:i for i,c in enumerate(forest['components']) for r in c['tree']}
        chosen={i:[] for i in range(len(forest['components']))}
        edge_ids={i:[] for i in chosen}
        for n in anchors:chosen[by_node[n]].append(n)
        if any(len(v)!=1 for v in chosen.values()):raise ValueError('Require exactly one anchor node per selected forest component')
        for e in selected:edge_ids[by_node[by_edge[e]['source']]].append(e)
        gemmi,_,_=_crystal(graph['crystal']['cell_parameters'],graph['crystal']['space_group']);identity=gemmi.Op('x,y,z')
        for i,component in enumerate(forest['components']):
            anchor=chosen[i][0]
            frames={r['node_id']:gemmi.Op(r['root_image']['operator_xyz']) for r in component['tree']}
            inverse_anchor=_inverse(frames[anchor],identity)
            for n in sorted(frames):
                images.append(dict(node_id=n,operator_xyz=_compose(inverse_anchor,frames[n]).triplet()))
            components.append(dict(anchor_node_id=anchor,node_ids=sorted(frames),selected_edge_ids=edge_ids[i]))
    images.sort(key=lambda row:row['node_id'])
    preview=relabel_periodic_graph(graph,images,expected_graph_sha256=expected_graph_sha256)
    after=preview['periodic_graph'];selected_set=set(selected)
    if any(e['target_operator_xyz']!='x,y,z' for e in after['edges'] if e['edge_id'] in selected_set):
        raise ValueError('Selected forest edges did not reach identity partner images')
    if any(row['operator_xyz']!='x,y,z' for row in images if row['node_id'] in anchors):
        raise ValueError('A selected anchor representative changed')
    result=dict(schema_version=1,kind='topostitch-explicit-forest-representatives',status='PROPOSED_REVIEW_REQUIRED',
        source_graph_sha256=graph['graph_sha256'],selected_edge_ids=selected,anchor_node_ids=anchors,
        components=components,node_images=images,unselected_node_ids=sorted(set(graph['node_ids'])-set(active)),
        remaining_periodic_edge_ids=[e['edge_id'] for e in after['edges'] if e['target_operator_xyz']!='x,y,z'],
        selected_edges_identity_verified=True,relabel_preview=preview,coordinates_materialized=False,
        chemical_connectivity_changed=False,graphical_review_recorded=False,runtime_authority=False,
        limitations=['Explicit declared forest only; no partner, tree, cut or anchor inferred',
                     'Identity edge images do not prove short distances, chemical closure or physical orbit identity',
                     'Unselected periodic edges are representation boundaries, not newly declared chemical nicks',
                     'Use the registered source-bound preview owner before atom-level inspection; no model or persistent choice written'])
    result['proposal_sha256']=_fingerprint(result)
    return result


def observe_registered_graph_descent(source_model, descendant_model, discovery, registration, *,
        expected_graph_sha256, expected_descendant_sha256, closest_image_reader,
        image_separation_angstrom, extra_edges=(), backbone_continuations=()):
    """Carry declared graph identities into a same-representative coordinate descendant.

    Reuse the source-bound graph reader and Cedar's explicitly trusted
    ``closest_atom_images`` callable. Every unique atom identity must survive;
    changed record order is mapped explicitly, never assumed to be index identity.
    A changed/ambiguous nearest image or crystal is refused. The separation must
    cover both PDB coordinate-rounding errors (2*sqrt(3)*0.001 Angstrom).

    This is a geometric correspondence observation, not checkpoint ancestry,
    chemistry or native restart admission. The caller must authenticate original
    construction and descendant history separately through their existing owners.
    Original registration/discovery stay immutable. The returned distinct report
    is not a replacement registration or an accepted recut-preview input.
    """
    from copy import deepcopy
    import math
    import re
    import gemmi
    from .topostitch_scattering import _serialized_structure, _parsed_identity

    if any(not isinstance(v,str) or re.fullmatch(r'[0-9a-f]{64}',v) is None
           for v in (expected_graph_sha256,expected_descendant_sha256)):
        raise ValueError('Require exact source graph and descendant SHA-256 bindings')
    if not callable(closest_image_reader):
        raise ValueError('Require an explicit trusted closest-image reader')
    if (type(image_separation_angstrom) not in (int,float)
            or not math.isfinite(image_separation_angstrom)
            or image_separation_angstrom < 2*math.sqrt(3)*.001):
        raise ValueError('Image separation must cover PDB coordinate rounding')
    paths=list(map(Path,(source_model,descendant_model,discovery,registration)))
    frozen={p:p.read_bytes() for p in paths}
    if sha256(frozen[paths[1]]).hexdigest()!=expected_descendant_sha256:
        raise ValueError('Unexpected descendant model bytes')
    graph=build_registered_periodic_graph(paths[0],paths[2],paths[3],
        extra_edges=extra_edges,backbone_continuations=backbone_continuations)
    if graph['report_sha256']!=expected_graph_sha256:
        raise ValueError('Unexpected registered source graph')
    if graph['scope']['unresolved_node_ids']:
        raise ValueError('Unresolved registered nodes cannot be carried into a descendant')
    source=_serialized_structure(frozen[paths[0]],'pdb')
    descendant=_serialized_structure(frozen[paths[1]],'pdb')
    group=source.find_spacegroup();other=descendant.find_spacegroup()
    if (group is None or other is None or source.cell.parameters!=descendant.cell.parameters
            or group.hall!=other.hall):
        raise ValueError('Graph descent requires the same crystal frame')
    old=list(source[0].all());new=list(descendant[0].all())
    from .topostitch_recipe import model_atom_rows
    for raw,parsed in ((frozen[paths[0]],old),(frozen[paths[1]],new)):
        written=model_atom_rows(raw)
        xyz=[tuple(float(line[start:start+8]) for start in (30,38,46))
             for line in raw.decode('ascii').splitlines() if line.startswith(('ATOM  ','HETATM'))]
        if written!=[_parsed_identity(a) for a in parsed] or xyz!=[tuple(a.atom.pos) for a in parsed]:
            raise ValueError('Parser changed source or descendant PDB atom record order')
    old_keys=[_fingerprint(_parsed_identity(a)) for a in old]
    new_keys=[_fingerprint(_parsed_identity(a)) for a in new]
    if (not old or len(set(old_keys))!=len(old) or len(set(new_keys))!=len(new)
            or set(old_keys)!=set(new_keys)):
        raise ValueError('Require a complete unique atom identity bijection')
    lookup={key:i for i,key in enumerate(new_keys)};order=[lookup[key] for key in old_keys]
    shifts=[];gaps=[]
    for i,a in enumerate(old):
        b=new[order[i]]
        def properties(v):
            return v.residue.het_flag,v.atom.element,v.atom.charge,v.atom.occ>0
        if properties(a)!=properties(b):
            raise ValueError('Graph descendant changed record, element, charge or occupancy status')
        first,second=closest_image_reader(tuple(a.atom.pos),tuple(b.atom.pos),source.cell,group,gemmi)
        distances=(first['distance_A'],second['distance_A'])
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in distances):
            raise ValueError('Invalid closest-image distance observation')
        gap=distances[1]-distances[0]
        if first['image']['operator_xyz']!='x,y,z' or gap<=image_separation_angstrom:
            raise ValueError('Changed or ambiguous crystal representative at source atom '+str(i))
        shifts.append(distances[0]);gaps.append(gap)
    nodes=deepcopy(graph['nodes'])
    for node in nodes:
        node['atom_indices']=[order[i] for i in node['atom_indices']]
    scope=deepcopy(graph['scope'])
    scope['unrepresented_atom_indices']=sorted(order[i] for i in scope['unrepresented_atom_indices'])
    result=dict(schema_version=1,kind='topostitch-registered-graph-descent',
        status='SAME_REPRESENTATIVE_GRAPH_OBSERVATION',
        source_model_sha256=graph['source_model_sha256'],descendant_model_sha256=expected_descendant_sha256,
        source_registered_graph_sha256=expected_graph_sha256,
        source_registration_sha256=graph['registration_file_sha256'],
        source_discovery_sha256=graph['discovery_file_sha256'],
        atom_count=len(old),source_to_descendant_atom_indices=order,
        reordered_atom_count=sum(i!=j for i,j in enumerate(order)),
        max_atom_shift_angstrom=max(shifts),minimum_image_separation_angstrom=min(gaps),
        required_image_separation_angstrom=image_separation_angstrom,
        periodic_graph=deepcopy(graph['periodic_graph']),nodes=nodes,scope=scope,
        declared_routes=deepcopy(graph['declared_routes']),edge_origins=deepcopy(graph['edge_origins']),
        declared_continuations=deepcopy(graph.get('declared_continuations',[])),
        atom_index_basis='DESCENDANT_PDB_ATOM_RECORD_ORDER',
        checkpoint_ancestry_verified=False,registration_rewritten=False,coordinates_written=False,
        runtime_authority=False,chemical_admission=False,native_restart_qualified=False,
        scientific_acceptance=False,
        limitations=['Geometric correspondence only; authenticate genuine checkpoint/construction history separately',
            'Declared edge images retained; no new partner, bond inference, force admission or recut',
            'ADPs and numeric occupancies may change during refinement; no scattering-invariance or thermal-policy claim'])
    result['report_sha256']=_fingerprint(result)
    if any(p.read_bytes()!=raw for p,raw in frozen.items()):
        raise ValueError('Graph descent inputs changed during observation')
    return result
