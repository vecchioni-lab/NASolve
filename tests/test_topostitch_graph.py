"""Periodic loops retain exact images without manufacturing chemical closure."""
import copy
from hashlib import sha256
import json

import pytest

pytest.importorskip('gemmi')
from nasolve.topostitch_graph import describe_periodic_graph, build_registered_periodic_graph
from nasolve.topostitch_registration import _fingerprint
from .test_topostitch_registration import inputs
from .test_topostitch_periodic import cryst1

CELL = (30, 30, 40, 90, 90, 90)


def edge(number, source, target, xyz='x,y,z', kind='covalent_backbone'):
    return dict(edge_id=number, source=source, target=target, target_operator_xyz=xyz, kind=kind)


def graph(nodes, edges, group='P 1'):
    return describe_periodic_graph(nodes, edges, cell_parameters=CELL, space_group=group)


def cycles(report):
    return [c for component in report['components'] for c in component['cycles']]


def test_tree_reverse_image_and_isolated_vertex_have_explicit_ownership():
    report = graph([3, 2, 1], [edge(1, 2, 1, 'x+2,y,z')])
    assert report['node_ids'] == [1, 2, 3]
    assert len(report['components']) == 2 and report['cycle_count'] == 0
    child = report['components'][0]['tree'][1]
    assert child['direction'] == -1
    assert child['root_image']['operator_xyz'] == 'x-2,y,z'
    assert report['runtime_authority'] is False and report['changes'] == []
    assert not report['physical_orbit_identity_validated']
    value = copy.deepcopy(report); digest = value.pop('graph_sha256')
    assert digest == _fingerprint(value)


def test_closed_local_loop_and_translated_winding_are_different_legitimate_cycles():
    edges = [edge(1, 1, 2), edge(2, 2, 3), edge(3, 1, 3), edge(4, 1, 3, 'x+2,y,z')]
    report = graph([1, 2, 3], edges)
    assert report['cycle_count'] == 2
    assert [c['classification'] for c in cycles(report)] == ['IDENTITY', 'LATTICE_TRANSLATION']
    assert cycles(report)[1]['root_image']['lattice_translation'] == [2, 0, 0]
    assert not report['chemical_connectivity_validated']


def test_noncommuting_screw_and_translation_use_path_order_without_wrapping():
    # Root->2 is g. Root->3 is t. The remaining 2->3 identity edge
    # yields g * t^-1, not t^-1 * g.
    report = graph([1, 2, 3], [edge(1, 1, 2, 'y,-x,z+1/4'),
                              edge(2, 1, 3, 'x+1,y,z'), edge(3, 2, 3)], 'P 43')
    cycle = cycles(report)[0]
    assert cycle['root_image']['operator_xyz'] == 'y,-x+1,z+1/4'
    assert cycle['root_image']['operator_xyz'] != 'y-1,-x,z+1/4'
    assert cycle['classification'] == 'ROTATION_AND_TRANSLATION'


@pytest.mark.parametrize('group,xyz,expected', [
    ('P 1', 'x+1,y,z', 'LATTICE_TRANSLATION'),
    ('P 43', 'y,-x,z+1/4', 'ROTATION_AND_TRANSLATION'),
    ('C 2', 'x+1/2,y+1/2,z', 'LATTICE_TRANSLATION'),
    ('P 1', 'x,y,z', 'IDENTITY'),
])
def test_self_loops_and_centering_are_not_deduplicated(group, xyz, expected):
    report = graph([1], [edge(1, 1, 1, xyz, 'symmetry_correspondence')], group)
    assert report['cycle_count'] == 1
    assert cycles(report)[0]['classification'] == expected
    assert cycles(report)[0]['root_image']['operator_xyz'] == xyz


def test_each_edge_kind_remains_distinct_even_for_identical_endpoints():
    kinds = ['covalent_backbone', 'base_pairing', 'stacking', 'symmetry_correspondence']
    report = graph([1, 2], [edge(i+1, 1, 2, kind=k) for i, k in enumerate(kinds)])
    assert [e['kind'] for e in report['edges']] == kinds
    assert report['cycle_count'] == 3
    assert graph([2, 1], list(reversed([edge(i+1, 1, 2, kind=k) for i, k in enumerate(kinds)]))) == report


@pytest.mark.parametrize('nodes,edges,match', [
    ([True], [], 'identifiers'), ([1, 1], [], 'identifiers'),
    ([1], [edge(True, 1, 1)], 'identifiers'), ([1], [edge(1, 1, 2)], 'unknown node'),
    ([1], [edge(1, 1, 1), edge(1, 1, 1)], 'identifiers'),
    ([1], [edge(1, 1, 1, kind='nick')], 'edge kind'),
    ([1], [edge(1, 1, 1, 'y,-x,z')], 'space group'),
    ([1], [edge(1, 1, 1, 'x+50000,y,z')], 'arithmetic budget'),
    ([1, 2, 3], [edge(1, 1, 2, 'x+30000,y,z'), edge(2, 2, 3, 'x+30000,y,z')], 'arithmetic budget'),
])
def test_unsupported_or_unbounded_graph_is_refused(nodes, edges, match):
    with pytest.raises(ValueError, match=match):
        graph(nodes, edges)


def registered(tmp_path, missing=None, rename=False):
    model, registration, logical = inputs(tmp_path, missing=missing, rename=rename)
    model.write_text(cryst1(CELL, 'P 43')+model.read_text())
    registration['model']['sha256'] = sha256(model.read_bytes()).hexdigest()
    reg = tmp_path/'registration.json'; reg.write_text(json.dumps(registration))
    sites = registration['target']['sites']
    discovery = {'schema_version': 1, 'kind': 'topostitch-end-discovery-input',
                 'model_sha256': registration['model']['sha256'],
                 'registration_sha256': sha256(reg.read_bytes()).hexdigest(),
                 'copy_id': 'copy_1', 'strands': [
                     {'strand_id': c, 'sites': [s for s in sites if s.startswith(c+':')],
                      'five_prime_boundary': 'representation' if c == 'A' else 'chemical',
                      'three_prime_boundary': 'unknown'} for c in 'ABCD'],
                 'duplex_pairs': [list(p) for item in logical for p in (item.terminal_pair, item.inner_pair)],
                 'protected_sites': ['A:2'], 'do_not_connect_sites': ['A:1'],
                 'pairing_inventory_complete': False}
    path = tmp_path/'discovery.json'; path.write_text(json.dumps(discovery))
    return model, path, reg, discovery


def test_registered_graph_retains_missing_sites_boundaries_and_protected_junctions(tmp_path):
    model, discovery, reg, _ = registered(tmp_path, missing='A:1', rename=True)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    report = build_registered_periodic_graph(model, discovery, reg)
    by_site = {n['logical_site']: n for n in report['nodes']}
    missing = by_site['A:1']
    assert missing['issues'] == ['MISSING_LOGICAL_MAPPING'] and missing['atom_indices'] == []
    assert missing['do_not_connect']
    assert by_site['A:2']['protected']
    assert by_site['A:2']['mapping']['coordinate_site'] == 'M:102'
    assert report['declared_routes'][0]['five_prime_boundary'] == 'representation'
    assert report['declared_routes'][0]['three_prime_boundary'] == 'unknown'
    assert report['scope']['unresolved_node_ids'] == [missing['node_id']]
    assert report['scope']['unrepresented_atom_indices']
    assert report['copy_status'] == 'PARTIAL' and not report['runtime_authority']
    assert str(tmp_path) not in json.dumps(report)
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    # Missing geometry must not erase declared covalent intent.
    assert any(e['source'] == missing['node_id'] for e in report['periodic_graph']['edges'])


def test_extra_symmetry_connection_keeps_its_kind_and_no_covalent_stitch_is_added(tmp_path):
    model, discovery, reg, _ = registered(tmp_path)
    extra = {'kind': 'base_pairing', 'source_site': 'A:1', 'target_site': 'C:1',
             'target_operator_xyz': 'y,-x,z+1/4'}
    baseline = build_registered_periodic_graph(model, discovery, reg)
    result = build_registered_periodic_graph(model, discovery, reg, extra_edges=[extra])
    assert result['periodic_graph']['edges'][:-1] == baseline['periodic_graph']['edges']
    assert result['periodic_graph']['edges'][-1]['kind'] == 'base_pairing'
    assert result['periodic_graph']['edges'][-1]['target_operator_xyz'] == extra['target_operator_xyz']
    with pytest.raises(ValueError, match='chemistry-aware'):
        build_registered_periodic_graph(model, discovery, reg, extra_edges=[{**extra, 'kind': 'covalent_backbone'}])


def test_unassigned_routes_are_explicit_and_source_drift_is_refused(tmp_path):
    model, discovery, reg, value = registered(tmp_path)
    value['strands'] = value['strands'][:-1]
    value['duplex_pairs'] = [p for p in value['duplex_pairs'] if all(not s.startswith('D:') for s in p)]
    discovery.write_text(json.dumps(value))
    report = build_registered_periodic_graph(model, discovery, reg)
    assert report['scope']['outside_declared_routes']
    model.write_text(model.read_text()+'REMARK changed\n')
    with pytest.raises(ValueError, match='checksum'):
        build_registered_periodic_graph(model, discovery, reg)


def relabel(report, images):
    from nasolve.topostitch_graph import relabel_periodic_graph
    return relabel_periodic_graph(report, images, expected_graph_sha256=report['graph_sha256'])


def test_relabeling_conjugates_screw_loops_and_changes_incident_edge_images():
    original = graph([1, 2], [edge(1, 1, 2, 'x,y,z'), edge(2, 1, 2, 'y,-x,z+1/4')], 'P 43')
    frozen = copy.deepcopy(original)
    result = relabel(original, [{'node_id': 1, 'operator_xyz': 'x+1,y,z'},
                                {'node_id': 2, 'operator_xyz': 'y,-x,z+1/4'}])
    assert original == frozen
    after = result['periodic_graph']
    assert after['edges'][0]['target_operator_xyz'] == '-y+1,x,z-1/4'
    assert after['edges'][1]['target_operator_xyz'] == 'x+1,y,z'
    assert cycles(after)[0]['root_image']['operator_xyz'] == 'y+1,-x+1,z+1/4'
    assert all(c['exact_match'] for c in result['cycle_conjugacy_checks'])
    assert result['exact_inverse_graph_round_trip']
    assert result['changed_node_ids'] == [1, 2]
    assert not result['coordinates_materialized'] and not result['scattering_invariance_validated']
    assert not result['runtime_authority'] and result['changes'] == []


def test_nonroot_relabeling_preserves_root_loop_and_inverse_recovers_source():
    import gemmi
    original = graph([1, 2, 3], [edge(1, 1, 2), edge(2, 2, 3), edge(3, 3, 1, 'x+2,y,z')])
    assignments = [{'node_id': 2, 'operator_xyz': 'x+3,y-2,z'}, {'node_id': 3, 'operator_xyz': 'x-2,y,z+1'}]
    result = relabel(original, assignments)
    assert cycles(result['periodic_graph']) == cycles(original)
    back = relabel(result['periodic_graph'], [{'node_id': r['node_id'], 'operator_xyz': gemmi.Op(r['operator_xyz']).inverse().triplet()} for r in assignments])
    assert back['periodic_graph'] == original


def test_relabeling_isolated_nodes_and_noop_preserve_topology():
    original = graph([1, 2], [])
    no_op = relabel(original, [])
    assert no_op['periodic_graph'] == original and no_op['changed_node_ids'] == []
    changed = relabel(original, [{'node_id': 2, 'operator_xyz': 'x+1,y,z'}])
    assert changed['periodic_graph'] == original
    assert changed['changed_node_ids'] == [2] and changed['cycle_conjugacy_checks'] == []


@pytest.mark.parametrize('mutation', [
    lambda r: r['components'][0]['tree'][0].update(parent_node_id=999),
    lambda r: r.update(runtime_authority=True),
    lambda r: r.update(cycle_count=999),
    lambda r: r['edges'][0]['target_image'].update(lattice_translation=[99,0,0]),
])
def test_relabeling_replays_complete_report_instead_of_trusting_summary_or_hash(mutation):
    original = graph([1, 2], [edge(1, 1, 2)])
    mutation(original)
    # Rehashing a malformed derived report cannot turn it into a trusted graph.
    original['graph_sha256'] = _fingerprint({k:v for k,v in original.items() if k != 'graph_sha256'})
    with pytest.raises(ValueError, match='inconsistent'):
        relabel(original, [])


@pytest.mark.parametrize('images,match', [
    ([{'node_id': 99, 'operator_xyz': 'x,y,z'}], 'known node'),
    ([{'node_id': True, 'operator_xyz': 'x,y,z'}], 'known node'),
    ([{'node_id': 1, 'operator_xyz': 'x,y,z'}, {'node_id': 1, 'operator_xyz': 'x,y,z'}], 'known node'),
    ([{'node_id': 1, 'operator_xyz': 'y,-x,z'}], 'space group'),
    ([{'node_id': 1, 'operator_xyz': 'x+50000,y,z'}], 'arithmetic budget'),
    ([{'node_id': 1, 'operator_xyz': 'x,y,z', 'apply': True}], 'Malformed'),
])
def test_invalid_relabel_assignment_is_refused(images, match):
    with pytest.raises(ValueError, match=match):
        relabel(graph([1, 2], [edge(1, 1, 2)]), images)


def test_relabel_requires_expected_source_graph_digest():
    from nasolve.topostitch_graph import relabel_periodic_graph
    original = graph([1], [])
    with pytest.raises(ValueError, match='checksum'):
        relabel_periodic_graph(original, [], expected_graph_sha256='a'*64)


def test_relabel_rejects_type_changed_report_even_when_python_values_compare_equal():
    report=graph([1],[]);changed=copy.deepcopy(report);changed['runtime_authority']=0
    assert changed==report  # Python equality alone loses this schema distinction.
    with pytest.raises(ValueError,match='inconsistent'):
        relabel(changed,[])


def descendant_case(tmp_path):
    model, discovery, registration, _ = registered(tmp_path)
    # Keep an unregistered water as explicit retained context.
    lines = model.read_text().splitlines()
    template = next(s for s in lines if s.startswith('ATOM  '))
    water = 'HETATM'+template[6:12]+' O  '+' '+'HOH'+' '+'Z'+' 999'+template[26:]
    water = water[:76]+' O'+water[78:]
    model.write_text('\n'.join(s for s in lines if s != 'END')+'\n'+water+'\nEND\n')
    reg = json.loads(registration.read_bytes()); reg['model']['sha256'] = sha256(model.read_bytes()).hexdigest()
    registration.write_text(json.dumps(reg))
    declaration = json.loads(discovery.read_bytes())
    declaration.update(model_sha256=reg['model']['sha256'],registration_sha256=sha256(registration.read_bytes()).hexdigest())
    discovery.write_text(json.dumps(declaration))
    original = model.read_bytes()
    # Reverse records while keeping a single contiguous block per residue/chain.
    lines = original.decode().splitlines()
    atoms = [s for s in lines if s.startswith(('ATOM  ', 'HETATM'))]
    child = tmp_path/'descendant.pdb'
    child.write_text(next(s for s in lines if s.startswith('CRYST1'))+'\n'+'\n'.join(reversed(atoms))+'\nEND\n')
    source_graph = build_registered_periodic_graph(model, discovery, registration)
    return model, child, discovery, registration, source_graph


def identity_reader(fixed, moving, cell, group, gemmi):
    # Controlled dependency: real crystal-image enumeration is owned by Cedar.
    import math
    distance = math.dist(fixed, moving)
    return ({'image': {'operator_xyz': 'x,y,z'}, 'distance_A': distance},
            {'image': {'operator_xyz': 'x+1,y,z'}, 'distance_A': distance+10})


def observe_descent(case, **overrides):
    from nasolve.topostitch_graph import observe_registered_graph_descent
    model, child, discovery, registration, graph = case
    opts = dict(expected_graph_sha256=graph['report_sha256'],
                expected_descendant_sha256=sha256(child.read_bytes()).hexdigest(),
                closest_image_reader=identity_reader, image_separation_angstrom=0.004)
    return observe_registered_graph_descent(model, child, discovery, registration, **dict(opts, **overrides))


def test_graph_descent_maps_reordered_atoms_without_rewriting_registration(tmp_path):
    case = descendant_case(tmp_path)
    before = {p: p.read_bytes() for p in case[:4]}
    result = observe_descent(case)
    count = result['atom_count']
    assert result['source_to_descendant_atom_indices'] == list(reversed(range(count)))
    assert case[4]['scope']['unrepresented_atom_indices'] == [count-1]
    assert result['scope']['unrepresented_atom_indices'] == [0]
    assert result['periodic_graph'] == case[4]['periodic_graph']
    assert result['source_registered_graph_sha256'] == case[4]['report_sha256']
    assert result['registration_rewritten'] is False and result['runtime_authority'] is False
    assert result['checkpoint_ancestry_verified'] is False
    for old, new in zip(case[4]['nodes'], result['nodes']):
        assert new['atom_indices'] == [count-1-i for i in old['atom_indices']]
        assert new['logical_site'] == old['logical_site']
    assert all(p.read_bytes() == b for p,b in before.items())


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'occupancy', 'cell'])
def test_graph_descent_refuses_identity_occupancy_or_frame_damage(tmp_path, change):
    case = descendant_case(tmp_path); child = case[1]; lines = child.read_text().splitlines()
    index = next(i for i,s in enumerate(lines) if s.startswith(('ATOM  ', 'HETATM')))
    if change == 'missing': lines.pop(index)
    elif change == 'duplicate': lines.insert(index, lines[index])
    elif change == 'occupancy': lines[index] = lines[index][:54]+'  0.00'+lines[index][60:]
    else: lines[0] = cryst1((31,30,40,90,90,90), 'P 43').strip()
    child.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError): observe_descent(case)


@pytest.mark.parametrize('operator,gap', [('x+1,y,z', 10), ('x,y,z', 0.001)])
def test_graph_descent_refuses_changed_or_ambiguous_representatives(tmp_path, operator, gap):
    def images(*args):
        return ({'image': {'operator_xyz': operator}, 'distance_A': 1},
                {'image': {'operator_xyz': 'x-1,y,z'}, 'distance_A': 1+gap})
    with pytest.raises(ValueError, match='Changed or ambiguous'):
        observe_descent(descendant_case(tmp_path), closest_image_reader=images)


def test_graph_descent_keeps_hashes_and_input_lifetime_explicit(tmp_path):
    case = descendant_case(tmp_path)
    with pytest.raises(ValueError, match='graph'):
        observe_descent(case, expected_graph_sha256='0'*64)
    with pytest.raises(ValueError, match='descendant'):
        observe_descent(case, expected_descendant_sha256='0'*64)
    with pytest.raises(ValueError, match='separation'):
        observe_descent(case, image_separation_angstrom=0.001)
    def drift(*args):
        case[1].write_bytes(case[1].read_bytes()+b'REMARK changed\n')
        return identity_reader(*args)
    with pytest.raises(ValueError, match='changed during'):
        observe_descent(case, closest_image_reader=drift)
