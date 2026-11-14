"""Explicit graph forests can choose image representatives, never chemistry."""
import copy
import json
import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_graph import propose_forest_representatives
from tests.test_topostitch_graph import graph,edge,cycles


def propose(report,edges,anchors):
    return propose_forest_representatives(report,selected_edge_ids=edges,anchor_node_ids=anchors,expected_graph_sha256=report['graph_sha256'])


def fixture():
    return graph([1,2,3,4],[edge(1,1,2,'y,-x,z+1/4'),edge(2,2,3,'x+1,y,z'),edge(3,1,3),edge(4,4,4,'x+2,y,z','symmetry_correspondence')],'P 43')


def test_explicit_noncommuting_path_is_rebased_to_the_requested_anchor():
    report=fixture();frozen=copy.deepcopy(report);result=propose(report,[2,1],[2])
    images={r['node_id']:r['operator_xyz'] for r in result['node_images']}
    assert images=={1:'-y,x,z-1/4',2:'x,y,z',3:'x+1,y,z'}
    assert result['selected_edge_ids']==[1,2] and result['anchor_node_ids']==[2]
    assert result['unselected_node_ids']==[4]
    assert report==frozen and not result['runtime_authority'] and not result['chemical_connectivity_changed']
    after=result['relabel_preview']['periodic_graph']
    assert [e['target_operator_xyz'] for e in after['edges'][:2]]==['x,y,z']*2
    assert after['edges'][2]['target_operator_xyz']=='-y,x-1,z-1/4'
    assert after['edges'][3]['target_operator_xyz']=='x+2,y,z'
    assert result['remaining_periodic_edge_ids']==[3,4]
    assert result['relabel_preview']['exact_inverse_graph_round_trip']
    assert all(c['exact_match'] for c in result['relabel_preview']['cycle_conjugacy_checks'])
    assert len(cycles(after))==len(cycles(report))


def test_reversed_edge_and_independent_components_keep_their_own_anchors():
    report=graph([1,2,3,4,5],[edge(1,2,1,'x+1,y,z'),edge(2,3,4,'x,y+2,z')])
    result=propose(report,[2,1],[4,1]);images={r['node_id']:r['operator_xyz'] for r in result['node_images']}
    assert images=={1:'x,y,z',2:'x-1,y,z',3:'x,y-2,z',4:'x,y,z'}
    assert result['unselected_node_ids']==[5]
    assert len(result['components'])==2
    assert propose(report,[1,2],[1,4])==result


@pytest.mark.parametrize('group,xyz',[('R 3:H','-x+y+2/3,-x+1/3,z+1/3'),('P 21','-x,y+1/2,-z'),('P 1','x-4,y+2,z')])
def test_centered_screw_and_lattice_images_are_never_wrapped(group,xyz):
    from nasolve.topostitch_graph import describe_periodic_graph
    cell=[30,30,40,90,90,120] if group=='R 3:H' else [30,35,40,90,105,90] if group=='P 21' else [30,30,40,90,90,90]
    report=describe_periodic_graph([1,2],[edge(1,1,2,xyz)],cell_parameters=cell,space_group=group)
    result=propose(report,[1],[1]);assert result['node_images'][1]['operator_xyz']==xyz
    assert result['relabel_preview']['periodic_graph']['edges'][0]['target_operator_xyz']=='x,y,z'


def test_no_selected_edges_is_an_explicit_noop():
    report=fixture();result=propose(report,[],[])
    assert result['node_images']==[] and result['components']==[]
    assert result['unselected_node_ids']==report['node_ids']
    assert result['relabel_preview']['periodic_graph']==report


@pytest.mark.parametrize('selected,anchors',[( [True],[1]),([1,1],[1]),([99],[1]),([1],[True]),([1],[1,1]),([1],[99]),([1],[]),([1],[1,2]),([1],[3]),([],[1])])
def test_unknown_duplicate_or_incomplete_choices_refuse(selected,anchors):
    with pytest.raises(ValueError):propose(fixture(),selected,anchors)


@pytest.mark.parametrize('selected',[[1,2,3],[4]])
def test_cycles_require_a_deliberately_omitted_edge_not_silent_seam_choice(selected):
    report=fixture()
    with pytest.raises(ValueError,match='forest'):propose(report,selected,[1] if len(selected)>1 else [4])


def test_source_hash_and_typed_report_are_rechecked():
    report=fixture()
    with pytest.raises(ValueError,match='checksum'):
        propose_forest_representatives(report,selected_edge_ids=[1],anchor_node_ids=[1],expected_graph_sha256='0'*64)
    report['runtime_authority']=0
    with pytest.raises(ValueError,match='inconsistent'):propose(report,[1],[1])


def test_assignment_composes_with_existing_registered_packet_and_view(tmp_path):
    from tests.test_topostitch_recut import anchored,node
    from nasolve.topostitch_graph import build_registered_periodic_graph
    from nasolve.topostitch_recut_bundle import build_relabel_preview,load_relabel_preview
    from nasolve.topostitch_view import representative_scene
    paths=anchored(tmp_path)
    extra=[dict(kind='base_pairing',source_site='A:1',target_site='C:1',target_operator_xyz='y,-x,z+1/4')]
    bound=build_registered_periodic_graph(*paths,extra_edges=extra);graph=bound['periodic_graph']
    selected=graph['edges'][-1]['edge_id'];result=propose(graph,[selected],[node(bound,'A:1')['node_id']])
    request=dict(schema_version=1,kind='topostitch-representative-proposal',registered_graph_sha256=bound['report_sha256'],node_images=result['node_images'],extra_edges=extra,coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000)
    p=tmp_path/'proposal.json';p.write_text(json.dumps(request));out=tmp_path/'preview'
    receipt=build_relabel_preview(paths[0],paths[1],registration_path=paths[2],proposal_path=p,output_directory=out)
    assert load_relabel_preview(out)==receipt
    scene=representative_scene(out)
    assert scene['periodic_edges'][-1]['after_operator_xyz']=='x,y,z'
    assert scene['periodic_edges'][-1]['before_operator_xyz']=='y,-x,z+1/4'
    assert all(a['logical_site']=='C:1' for a in scene['atoms'] if a['scope']=='representative')


def test_anchor_rebasing_cannot_exceed_the_existing_exact_arithmetic_budget():
    report=graph([1,2,3],[edge(1,1,2,'x+30000,y,z'),edge(2,1,3,'x-30000,y,z')])
    with pytest.raises(ValueError,match='arithmetic budget'):propose(report,[1,2],[2])
