"""A proposed cut must bind exact registered atoms, not just graph labels."""
import copy
from hashlib import sha256
import json

import pytest
pytest.importorskip('gemmi')

from nasolve.topostitch_graph import build_registered_periodic_graph
from nasolve.topostitch_recut import preview_registered_relabel
from .test_topostitch_graph import registered


def prepare(tmp_path, **kwargs):
    model, discovery, reg, _ = registered(tmp_path, **kwargs)
    graph = build_registered_periodic_graph(model, discovery, reg)
    return (model, discovery, reg), graph


def preview(paths, graph, images):
    return preview_registered_relabel(*paths, node_images=images, expected_registered_graph_sha256=graph['report_sha256'])


def node(graph, site):
    return next(n for n in graph['nodes'] if n['logical_site']==site)


def test_registered_cut_moves_exact_whole_residue_in_memory_only(tmp_path):
    paths, graph = prepare(tmp_path, rename=True)
    chosen = node(graph,'A:2');frozen={p:p.read_bytes() for p in paths}
    result=preview(paths,graph,[dict(node_id=chosen['node_id'],operator_xyz='y,-x,z+1/4')])
    assert result['requested_image_atom_indices']==chosen['atom_indices']
    assert result['atom_image_groups'][0]['coordinate_site']=='M:102'
    assert result['atom_image_groups'][0]['protected'] is True
    before=[a['position_angstrom'] for a in result['source_orbit_observation']['atoms']]
    after=result['proposed_points_angstrom']
    assert all(after[i]==before[i] for i in result['fixed_atom_indices'])
    for i in chosen['atom_indices']:
        x,y,z=before[i];assert after[i]==pytest.approx([y,-x,z+10],abs=1e-10)
    assert result['maximum_atom_round_trip_error_angstrom']<1e-10
    assert not result['coordinates_materialized'] and not result['boundary_chemistry_changed']
    assert not result['physical_identity_validated'] and not result['runtime_authority']
    assert result['registered_graph']==graph and result['changes']==[]
    assert all(p.read_bytes()==b for p,b in frozen.items())
    assert str(tmp_path) not in json.dumps(result)


def test_noop_preserves_all_points_and_reports_missing_display_anchors(tmp_path):
    paths,graph=prepare(tmp_path)
    result=preview(paths,graph,[])
    assert result['requested_image_atom_indices']==[]
    assert result['proposed_points_angstrom']==[a['position_angstrom'] for a in result['source_orbit_observation']['atoms']]
    # This synthetic base-only fixture has no O3' atoms. Do not invent centroids.
    assert result['unavailable_anchor_node_ids']==graph['periodic_graph']['node_ids']
    assert all(e['status']=='ANCHOR_UNAVAILABLE' for e in result['edge_image_observations'])


def test_missing_unrequested_node_is_visible_but_requested_missing_node_refuses(tmp_path):
    paths,graph=prepare(tmp_path,missing='A:1')
    missing=node(graph,'A:1')
    result=preview(paths,graph,[])
    assert missing['node_id'] in result['registered_graph']['scope']['unresolved_node_ids']
    with pytest.raises(ValueError,match='missing or ambiguous'):
        preview(paths,graph,[dict(node_id=missing['node_id'],operator_xyz='x+1,y,z')])


def test_registered_cut_requires_outer_identity_and_detects_source_drift(tmp_path):
    paths,graph=prepare(tmp_path)
    with pytest.raises(ValueError,match='Registered graph checksum'):
        preview_registered_relabel(*paths,node_images=[],expected_registered_graph_sha256='a'*64)
    paths[0].write_bytes(paths[0].read_bytes()+b'REMARK drift\n')
    with pytest.raises(ValueError,match='checksum'):
        preview(paths,graph,[])


def test_same_graph_algebra_does_not_authorize_different_registered_source(tmp_path):
    first=tmp_path/'first';first.mkdir();paths,a=prepare(first)
    second=tmp_path/'second';second.mkdir();renamed,b=prepare(second,rename=True)
    assert a['periodic_graph']==b['periodic_graph']
    assert a['report_sha256']!=b['report_sha256']
    with pytest.raises(ValueError,match='Registered graph checksum'):
        preview(renamed,a,[])


def test_source_snapshot_change_during_orbit_observation_refuses_preview(tmp_path,monkeypatch):
    paths,graph=prepare(tmp_path)
    import nasolve.topostitch_recut as module
    original=module.inspect_model_orbit_identity
    def changed(*a,**kw):
        result=original(*a,**kw);paths[1].write_bytes(paths[1].read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'inspect_model_orbit_identity',changed)
    with pytest.raises(ValueError,match='changed during'):
        preview(paths,graph,[])


def anchored(tmp_path):
    from .helpers import pdb_record
    paths,_=prepare(tmp_path)
    model,discovery,reg=paths
    registry=json.loads(reg.read_bytes());anchors={}
    for serial,row in enumerate(registry['copies'][0]['mappings'],1001):
        chain,resid=row['coordinate_site'].split(':');number=int(resid)
        anchors[row['coordinate_site']]=pdb_record('ATOM',serial,"O3'",row['coordinate_residue_code'],chain,number,
            x=number+1.23,y=(ord(chain)-64)*2.17,z=number*3.21)
    lines=[]
    for line in model.read_text().splitlines(keepends=True):
        if line.startswith('ATOM'):
            key=f'{line[21].strip()}:{int(line[22:26])}'
            if key in anchors:lines.append(anchors.pop(key))
        lines.append(line)
    assert not anchors
    model.write_text(''.join(lines))
    registry['model']['sha256']=sha256(model.read_bytes()).hexdigest();reg.write_text(json.dumps(registry))
    value=json.loads(discovery.read_bytes());value['model_sha256']=registry['model']['sha256'];value['registration_sha256']=sha256(reg.read_bytes()).hexdigest();discovery.write_text(json.dumps(value))
    return paths


def test_edge_geometry_follows_source_image_and_preserves_display_distances(tmp_path):
    paths=anchored(tmp_path)
    extra=[dict(kind='stacking',source_site='A:1',target_site='C:1',target_operator_xyz='y,-x,z+1/4')]
    graph=build_registered_periodic_graph(*paths,extra_edges=extra)
    assignments=[dict(node_id=node(graph,'A:1')['node_id'],operator_xyz='x+1,y,z'),
                 dict(node_id=node(graph,'C:1')['node_id'],operator_xyz='y,-x,z+1/4')]
    result=preview_registered_relabel(*paths,node_images=assignments,extra_edges=extra,
                                     expected_registered_graph_sha256=graph['report_sha256'])
    assert result['unavailable_anchor_node_ids']==[]
    assert all(e['status']=='IMAGE_ARITHMETIC_VERIFIED' for e in result['edge_image_observations'])
    for e in result['edge_image_observations']:
        assert e['before_anchor_distance_angstrom']==pytest.approx(e['after_anchor_distance_angstrom'],abs=1e-10)
        assert e['distances_are_chemical_restraints'] is False
    chosen=result['edge_image_observations'][-1]
    assert chosen['kind']=='stacking' and chosen['after_operator_xyz']=='x+1,y,z'
    for before,after in zip(chosen['before_points'],chosen['after_points']):
        assert after==pytest.approx([before[0]+30,before[1],before[2]],abs=1e-10)


def test_wrong_cartesian_image_direction_is_detected_by_noncommuting_edge_check(tmp_path,monkeypatch):
    paths=anchored(tmp_path)
    extra=[dict(kind='base_pairing',source_site='A:1',target_site='C:1',target_operator_xyz='y,-x,z+1/4')]
    graph=build_registered_periodic_graph(*paths,extra_edges=extra)
    import nasolve.topostitch_recut as module
    actual=module.crystallographic_image
    monkeypatch.setattr(module,'crystallographic_image',lambda *a,**kw:actual(*a,**kw).inverse())
    with pytest.raises(ValueError,match='edge image geometry'):
        preview_registered_relabel(*paths,node_images=[dict(node_id=node(graph,'A:1')['node_id'],operator_xyz='x+1,y,z')],
            extra_edges=extra,expected_registered_graph_sha256=graph['report_sha256'])


def test_registered_preview_replays_after_original_directory_is_gone(tmp_path):
    original=tmp_path/'original';original.mkdir();paths=anchored(original)
    graph=build_registered_periodic_graph(*paths);images=[dict(node_id=node(graph,'A:1')['node_id'],operator_xyz='x+1,y,z')]
    before=preview(paths,graph,images);moved=tmp_path/'moved';original.rename(moved)
    assert not original.exists()
    assert preview(tuple(moved/p.name for p in paths),graph,images)==before
