"""Explicit boundary partners are intent, never inferred bonds or native proxies."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_registration import _fingerprint
from nasolve.topostitch_graph import build_registered_periodic_graph
from nasolve.topostitch_recut_bundle import build_relabel_preview,load_relabel_preview,observe_relabel_backbone_intent
from nasolve.topostitch_view import representative_scene
from tests.test_topostitch_backbone_intent import packet,sites


def setup(tmp_path, *, missing=None):
    packet(tmp_path,missing=missing)
    model,discovery,reg=tmp_path/'model.pdb',tmp_path/'discovery.json',tmp_path/'registration.json'
    manifest=json.loads(discovery.read_text())
    for route in manifest['strands']:
        if route['strand_id']=='A':route['three_prime_boundary']='representation'
        if route['strand_id']=='C':route['five_prime_boundary']='representation'
    discovery.write_text(json.dumps(manifest))
    links=[dict(continuation_id=1,source_site='A:4',target_site='C:1',target_operator_xyz='y,-x,z+1/4')]
    return (model,discovery,reg),links


def request(paths,links,*,images=(),forest=False):
    bound=build_registered_periodic_graph(*paths,backbone_continuations=links)
    value=dict(schema_version=2,kind='topostitch-forest-proposal' if forest else 'topostitch-representative-proposal',
        registered_graph_sha256=bound['report_sha256'],extra_edges=[],backbone_continuations=links,
        coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000)
    if forest:
        value.update(selected_edge_ids=[bound['declared_continuations'][0]['edge_id']],
            anchor_node_ids=[next(n['node_id'] for n in bound['nodes'] if n['logical_site']=='A:4')])
    else:value['node_images']=list(images)
    proposal=paths[0].parent/'continuation-request.json';proposal.write_text(json.dumps(value))
    args=dict(model=paths[0],discovery=paths[1],registration_path=paths[2],proposal_path=proposal)
    return args,bound,value


def test_explicit_directed_continuation_is_replayed_and_relabelled_by_existing_owners(tmp_path):
    paths,links=setup(tmp_path);args,bound,value=request(paths,links,forest=True)
    before={p:p.read_bytes() for p in args.values()};root=tmp_path/'connected'
    result=build_relabel_preview(**args,output_directory=root)
    assert load_relabel_preview(root)==result
    declared=bound['declared_continuations'][0]
    assert declared['source_site']=='A:4' and declared['target_site']=='C:1'
    edge=next(e for e in bound['periodic_graph']['edges'] if e['edge_id']==declared['edge_id'])
    assert edge['kind']=='covalent_backbone' and edge['target_operator_xyz']=='y,-x,z+1/4'
    target=sites(observe_relabel_backbone_intent(root))['C:1'];partner=target['incoming_partner']
    assert target['partner_resolution']=='LOGICAL_PARTNER_RESOLVED' and target['incoming_state']=='DECLARED_CONTINUATION'
    assert partner['continuation_id']==1 and partner['logical_site']=='A:4'
    assert partner['after_target_operator_xyz']=='x,y,z' and not partner['proposed_representation_seam']
    assert partner['geometry']['before_distance_angstrom']==pytest.approx(partner['geometry']['after_image_distance_angstrom'])
    assert not partner['geometry']['chemical_geometry_validated']
    scene=representative_scene(root,backbone_intent=True)
    assert scene['backbone_intent']['sites']==observe_relabel_backbone_intent(root)['sites']
    assert not result['chemical_connectivity_changed'] and not result['runtime_authority']
    assert all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('field,value,match',[
 ('continuation_id',True,'identifier'),('continuation_id',0,'identifier'),
 ('source_site','A:2','3-prime'),('target_site','C:2','5-prime'),
 ('source_site','A:999','logical'),('target_site',True,'logical'),
 ('target_operator_xyz',None,'operator'),('target_operator_xyz','y,-x,z','space group'),
 ('target_operator_xyz','x+50000,y,z','budget'),('unknown','extra','fields')])
def test_malformed_or_wrong_endpoint_declarations_refuse(tmp_path,field,value,match):
    paths,links=setup(tmp_path);links[0][field]=value
    with pytest.raises(ValueError,match=match):build_registered_periodic_graph(*paths,backbone_continuations=links)


@pytest.mark.parametrize('boundary',['chemical','unknown'])
@pytest.mark.parametrize('end',['source','target'])
def test_true_or_unknown_boundaries_are_never_overridden(tmp_path,boundary,end):
    paths,links=setup(tmp_path);manifest=json.loads(paths[1].read_text())
    strand,field=('A','three_prime_boundary') if end=='source' else ('C','five_prime_boundary')
    next(r for r in manifest['strands'] if r['strand_id']==strand)[field]=boundary;paths[1].write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='representation'):build_registered_periodic_graph(*paths,backbone_continuations=links)


def test_do_not_connect_and_competing_partners_refuse(tmp_path):
    paths,links=setup(tmp_path)
    for change in ('duplicate_id','duplicate_source','duplicate_target','do_not_connect'):
        candidates=deepcopy(links)
        if change=='do_not_connect':
            manifest=json.loads(paths[1].read_text());manifest['do_not_connect_sites'].append('A:4');paths[1].write_text(json.dumps(manifest))
        else:
            extra=deepcopy(candidates[0])
            if change!='duplicate_id':extra['continuation_id']=2
            candidates.append(extra)
        with pytest.raises(ValueError):build_registered_periodic_graph(*paths,backbone_continuations=candidates)


def test_legacy_graph_and_packets_are_exact_and_extra_edges_cannot_smuggle_covalence(tmp_path):
    paths,links=setup(tmp_path);old=build_registered_periodic_graph(*paths)
    assert build_registered_periodic_graph(*paths,backbone_continuations=[])==old
    assert 'declared_continuations' not in old
    with pytest.raises(ValueError,match='chemistry-aware'):
        build_registered_periodic_graph(*paths,extra_edges=[dict(kind='covalent_backbone',**{k:v for k,v in links[0].items() if k!='continuation_id'})])
    args,_,value=request(paths,links);value['schema_version']=1;args['proposal_path'].write_text(json.dumps(value))
    with pytest.raises(ValueError):build_relabel_preview(**args,output_directory=tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


def test_missing_coordinate_partner_remains_explicit_not_chemically_terminal(tmp_path):
    paths,links=setup(tmp_path,missing='C:1');args,_,_=request(paths,links)
    root=tmp_path/'connected';build_relabel_preview(**args,output_directory=root)
    row=sites(observe_relabel_backbone_intent(root))['C:1']
    assert row['incoming_state']=='DECLARED_CONTINUATION' and row['partner_resolution']=='LOGICAL_PARTNER_RESOLVED'
    assert row['preserve_existing_atoms']==['P','OP1','OP2']
    assert not row['incoming_partner']['coordinate_endpoints_resolved'] and row['incoming_partner']['geometry'] is None


def test_explicit_continuation_cannot_hide_behind_old_graph_digest(tmp_path):
    paths,links=setup(tmp_path);args,_,value=request(paths,links)
    value['registered_graph_sha256']=build_registered_periodic_graph(*paths)['report_sha256']
    args['proposal_path'].write_text(json.dumps(value))
    with pytest.raises(ValueError,match='checksum'):build_relabel_preview(**args,output_directory=tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


def test_round_trip_and_relocation_retain_exact_connection_request(tmp_path,monkeypatch):
    original=tmp_path/'original';original.mkdir();paths,links=setup(original);args,_,_=request(paths,links,forest=True)
    root=original/'connected';expected=build_relabel_preview(**args,output_directory=root);intent=observe_relabel_backbone_intent(root)
    moved=tmp_path/'moved';shutil.move(root,moved);shutil.rmtree(original)
    opener=Path.open
    def guarded(self,*a,**kw):
        if self.resolve().is_relative_to(original):raise AssertionError('Original lookup forbidden')
        return opener(self,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    assert load_relabel_preview(moved)==expected and observe_relabel_backbone_intent(moved)==intent


def test_noncommuting_images_preserve_directed_seam_and_scattering(tmp_path):
    from nasolve.topostitch_recut import observe_registered_relabel_orbits
    from nasolve.topostitch_scattering import observe_registered_relabel_scattering
    paths,links=setup(tmp_path);bound=build_registered_periodic_graph(*paths,backbone_continuations=links)
    numbers={n['logical_site']:n['node_id'] for n in bound['nodes']}
    images=[dict(node_id=numbers['A:4'],operator_xyz='y,-x,z+1/4'),dict(node_id=numbers['C:1'],operator_xyz='x+1,y,z')]
    args,_,_=request(paths,links,images=images);root=tmp_path/'connected';build_relabel_preview(**args,output_directory=root)
    partner=sites(observe_relabel_backbone_intent(root))['C:1']['incoming_partner']
    assert partner['after_target_operator_xyz']=='-x+1,-y,z+1/2'
    assert partner['geometry']['before_distance_angstrom']==pytest.approx(partner['geometry']['after_image_distance_angstrom'])
    kwargs=dict(node_images=images,backbone_continuations=links,expected_registered_graph_sha256=bound['report_sha256'])
    orbit=observe_registered_relabel_orbits(*paths,**kwargs)
    assert orbit['status']=='EXACT_LABELLED_ORBIT_PERMUTATIONS'
    assert orbit['registered_graph_sha256']==bound['report_sha256']
    assert orbit['preview_sha256']==load_relabel_preview(root)['observation']['preview_sha256']
    assert sorted(i for group in orbit['image_assignments'] for i in group['atom_indices'])==list(range(orbit['atom_count']))
    observation=observe_registered_relabel_scattering(*paths,hkls=[[1,0,0],[0,1,1],[1,1,1]],**kwargs)
    assert not observation['runtime_authority']
    # A synthetic regression bound, not a scientific acceptance threshold.
    assert observation['maximum_absolute_complex_difference'] < 1e-5


@pytest.mark.parametrize('group,cell,operator',[
    ('P 1',(30,31,40,80,95,110),'x+1,y-2,z+3'),
    ('R 3',(30,30,40,90,90,120),'x+2/3,y+1/3,z+1/3'),
])
def test_oblique_translation_and_centered_boundary_images(tmp_path,group,cell,operator):
    from tests.test_topostitch_periodic import cryst1
    paths,links=setup(tmp_path);model,discovery,reg=paths
    text=model.read_text();model.write_text(cryst1(cell,group)+''.join(text.splitlines(True)[1:]))
    registry=json.loads(reg.read_text());registry['model']['sha256']=sha256(model.read_bytes()).hexdigest();reg.write_text(json.dumps(registry))
    manifest=json.loads(discovery.read_text());manifest['model_sha256']=registry['model']['sha256'];manifest['registration_sha256']=sha256(reg.read_bytes()).hexdigest();discovery.write_text(json.dumps(manifest))
    links[0]['target_operator_xyz']=operator;args,_,_=request(paths,links,forest=True)
    root=tmp_path/'connected';build_relabel_preview(**args,output_directory=root)
    partner=sites(observe_relabel_backbone_intent(root))['C:1']['incoming_partner']
    assert partner['before_target_operator_xyz']==operator and partner['after_target_operator_xyz']=='x,y,z'
    assert partner['geometry']['before_distance_angstrom']==pytest.approx(partner['geometry']['after_image_distance_angstrom'])


@pytest.mark.parametrize('capacity',['incoming','outgoing'])
def test_distinct_competing_boundary_partners_are_rejected(tmp_path,capacity):
    paths,links=setup(tmp_path);manifest=json.loads(paths[1].read_text());extra=deepcopy(links[0]);extra['continuation_id']=2
    if capacity=='incoming':
        next(r for r in manifest['strands'] if r['strand_id']=='D')['three_prime_boundary']='representation'
        extra['source_site']='D:2'
    else:
        next(r for r in manifest['strands'] if r['strand_id']=='B')['five_prime_boundary']='representation'
        extra['target_site']='B:3'
    paths[1].write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='competing'):build_registered_periodic_graph(*paths,backbone_continuations=links+[extra])


def test_periodic_strand_winding_is_not_forced_to_zero(tmp_path):
    paths,links=setup(tmp_path);manifest=json.loads(paths[1].read_text());manifest['do_not_connect_sites']=[];paths[1].write_text(json.dumps(manifest))
    links[0].update(target_site='A:1',target_operator_xyz='x+1,y,z')
    bound=build_registered_periodic_graph(*paths,backbone_continuations=links)
    edge_id=bound['declared_continuations'][0]['edge_id']
    cycles=[c for component in bound['periodic_graph']['components'] for c in component['cycles']]
    # The added edge may enter the spanning tree; a different edge then carries
    # the fundamental cycle. Do not mistake that basis choice for lost winding.
    assert any(c['classification']=='LATTICE_TRANSLATION' and c['root_image']['operator_xyz'] in ('x+1,y,z','x-1,y,z') for c in cycles)
    assert next(e for e in bound['periodic_graph']['edges'] if e['edge_id']==edge_id)['target_operator_xyz']=='x+1,y,z'
    args,_,_=request(paths,links);root=tmp_path/'connected';build_relabel_preview(**args,output_directory=root)
    partner=sites(observe_relabel_backbone_intent(root))['A:1']['incoming_partner']
    assert partner['logical_site']=='A:4' and partner['after_target_operator_xyz']=='x+1,y,z'


# The receiving adapter uses trusted Cedar observations; these stubs isolate its
# cross-owner contract. The genuine Cedar reader/group check is qualified locally.
def joint_packet(tmp_path):
    import gemmi
    paths, links = setup(tmp_path)
    discovery = json.loads(paths[1].read_bytes())
    routes = {r['strand_id']: r for r in discovery['strands']}
    routes['C']['three_prime_boundary'] = 'representation'
    routes['D']['five_prime_boundary'] = 'representation'
    paths[1].write_text(json.dumps(discovery))
    links.append(dict(continuation_id=2, source_site=routes['C']['sites'][-1],
                      target_site=routes['D']['sites'][0], target_operator_xyz='x+1,y,z'))
    args, _, _ = request(paths, links, forest=True)
    root = tmp_path/'joint'; build_relabel_preview(**args, output_directory=root)
    intent = observe_relabel_backbone_intent(root)
    rows = {r['node_id']: r for r in intent['sites']}
    inspections = []
    for target in rows.values():
        partner = target['incoming_partner']
        if not partner or 'continuation_id' not in partner: continue
        source = rows[partner['node_id']]
        def endpoint(row, atom):
            return dict(logical_site=row['logical_site'],
                        coordinate_site=row['coordinate_mapping']['coordinate_site'],
                        atom=atom, mapping_issues=[])
        donor, acceptor = endpoint(source, "O3'"), endpoint(target, 'P')
        oxygen = gemmi.Op(partner['before_target_operator_xyz']).inverse().triplet()
        inspections.append(dict(model_sha256=intent['source_model_sha256'],
            o3=[donor['coordinate_site'], source['coordinate_mapping']['coordinate_residue_code'], "O3'"],
            phosphate=[acceptor['coordinate_site'], target['coordinate_mapping']['coordinate_residue_code'], 'P'],
            o3_image=oxygen, distance_A=partner['geometry']['before_distance_angstrom'],
            registered_continuation=dict(continuation_id=partner['continuation_id'],
                copy_id=target['copy_id'], source=donor, target=acceptor,
                target_operator_xyz=partner['before_target_operator_xyz'], oxygen_operator_xyz=oxygen,
                measurement_status='MEASURED', registered_graph_sha256='c'*64,
                sources={'registration_sha256':'a'*64})))
    return root, inspections


def bind_joint(root, inspections, checker=None):
    from nasolve.topostitch_recut_bundle import bind_recut_phosphates
    return bind_recut_phosphates(root, inspections,
        expected_receipt_sha256=sha256((root/'preview.json').read_bytes()).hexdigest(),
        group_checker=checker or (lambda rows: tuple(r['registered_continuation']['continuation_id'] for r in rows)))


def test_joint_binding_keeps_source_operators_when_display_cut_is_local(tmp_path):
    root, inspections = joint_packet(tmp_path)
    before = {p:p.read_bytes() for p in root.iterdir()}; original = deepcopy(inspections)
    calls = []
    def check(rows):
        calls.append(deepcopy(rows)); return (1, 2)
    result = bind_joint(root, inspections, check)
    assert calls == [inspections] and inspections == original
    assert result['native_continuation_ids'] == [1, 2]
    first, second = result['connections']
    assert first['source']['logical_site'] == 'A:4'
    assert first['source']['coordinate_site'] == 'M:104'
    assert first['source']['strand_id'] == 'A' and first['target']['strand_id'] == 'C'
    assert first['native_target_operator_xyz'] == 'y,-x,z+1/4'
    assert first['display_target_operator_xyz'] == 'x,y,z'
    assert second['native_target_operator_xyz'] == 'x+1,y,z'
    assert result['native_registered_graph_sha256'] != result['preview_registered_graph_sha256']
    assert not result['runtime_authority'] and not result['checkpoint_admission']
    assert not result['chemical_geometry_validated'] and not result['selection_applied']
    assert all(p.read_bytes() == b for p,b in before.items())
    assert str(tmp_path) not in json.dumps(result)
    assert result['report_sha256'] == _fingerprint({k:v for k,v in result.items() if k != 'report_sha256'})


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'model', 'copy', 'logical', 'coordinate',
                                  'display_operator', 'inverse', 'distance', 'unresolved', 'atom'])
def test_joint_binding_rejects_incomplete_or_wrong_cross_owner_identity(tmp_path, change):
    root, rows = joint_packet(tmp_path); edge = rows[0]['registered_continuation']
    if change == 'missing': rows.pop()
    elif change == 'duplicate': rows[1] = deepcopy(rows[0])
    elif change == 'model': rows[0]['model_sha256'] = '0'*64
    elif change == 'copy': edge['copy_id'] = 'another-copy'
    elif change == 'logical': edge['source']['logical_site'] = 'A:2'
    elif change == 'coordinate': edge['source']['coordinate_site'] = 'A:4'
    elif change == 'display_operator': edge['target_operator_xyz'] = 'x,y,z'
    elif change == 'inverse': edge['oxygen_operator_xyz'] = 'x,y,z'
    elif change == 'distance': rows[0]['distance_A'] += .1
    elif change == 'unresolved': edge['measurement_status'] = 'UNRESOLVED'
    elif change == 'atom': rows[0]['o3'][2] = "C3'"
    with pytest.raises(ValueError): bind_joint(root, rows)


@pytest.mark.parametrize('change', ['refusal', 'wrong_ids', 'inspection_drift', 'packet_drift'])
def test_joint_binding_respects_group_owner_and_rejects_drift(tmp_path, change):
    root, rows = joint_packet(tmp_path)
    def check(frozen):
        if change == 'refusal': raise ValueError('Cedar rejected group')
        if change == 'wrong_ids': return (2, 1)
        if change == 'inspection_drift': frozen[0]['distance_A'] += .1
        if change == 'packet_drift': (root/'source.pdb').write_bytes((root/'source.pdb').read_bytes()+b'REMARK drift\n')
        return (1, 2)
    with pytest.raises(ValueError): bind_joint(root, rows, check)


def test_joint_binding_relocates_and_rejects_stale_receipt(tmp_path):
    from nasolve.topostitch_recut_bundle import bind_recut_phosphates
    original=tmp_path/'original'; original.mkdir(); root,rows=joint_packet(original)
    expected=bind_joint(root,rows)
    moved=tmp_path/'moved'; shutil.move(root,moved); shutil.rmtree(original)
    assert bind_joint(moved,rows)==expected
    with pytest.raises(ValueError,match='receipt'):
        bind_recut_phosphates(moved,rows,expected_receipt_sha256='0'*64,group_checker=lambda rows:(1,2))
