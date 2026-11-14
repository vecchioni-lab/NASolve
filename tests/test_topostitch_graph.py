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
