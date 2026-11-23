"""Declared continuation must survive recutting even with unresolved chemistry."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_graph import build_registered_periodic_graph
from nasolve.topostitch_recut_bundle import build_relabel_preview, observe_relabel_backbone_intent
from tests.test_topostitch_graph import registered
from tests.helpers import pdb_record


def packet(tmp_path, *, missing=None, op3=False, aliases=False, duplicate=False, boundary='representation', move=True, omit=()):
    model, discovery, reg, manifest = registered(tmp_path, rename=True, missing=missing)
    lines = model.read_text().splitlines(True)
    seen = set(); serial = 1000; additions = {}
    for line in lines:
        if not line.startswith('ATOM'): continue
        key = line[21:27]
        if key in seen: continue
        seen.add(key); additions[key] = []
        names = ["O3'", 'P', 'O1P' if aliases else 'OP1', 'O2P' if aliases else 'OP2']
        if op3: names.append('O3P' if aliases else 'OP3')
        if duplicate: names.append('OP1' if aliases else 'O1P')
        for k, name in enumerate(names):
            if name in omit: continue
            serial += 1
            additions[key].append(pdb_record('ATOM', serial, name, line[17:20].strip(), line[21], int(line[22:26]),
                x=float(line[30:38])+k*.3, y=float(line[38:46])+1, z=float(line[46:54]), element='P' if name == 'P' else 'O'))
    expanded = []
    for line in lines:
        if line.startswith('ATOM'):
            expanded.extend(additions.pop(line[21:27], []))
        expanded.append(line)
    model.write_text(''.join(expanded))
    registry = json.loads(reg.read_text()); registry['model']['sha256'] = sha256(model.read_bytes()).hexdigest()
    reg.write_text(json.dumps(registry))
    manifest['model_sha256'] = registry['model']['sha256']; manifest['registration_sha256'] = sha256(reg.read_bytes()).hexdigest()
    manifest['strands'][0]['five_prime_boundary'] = boundary
    discovery.write_text(json.dumps(manifest))
    graph = build_registered_periodic_graph(model, discovery, reg)
    chosen = next(n['node_id'] for n in graph['nodes'] if n['logical_site'] == 'A:2')
    request = dict(schema_version=1,kind='topostitch-representative-proposal',registered_graph_sha256=graph['report_sha256'],
        node_images=[dict(node_id=chosen,operator_xyz='y,-x,z+1/4')] if move else [],extra_edges=[],
        coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000)
    proposal=tmp_path/'request.json';proposal.write_text(json.dumps(request))
    out=tmp_path/'packet'
    build_relabel_preview(model, discovery, registration_path=reg,proposal_path=proposal,output_directory=out)
    return out


def sites(result): return {row['logical_site']:row for row in result['sites']}


def test_continuation_survives_unknown_partner_and_exact_screw_recut(tmp_path):
    root=packet(tmp_path); before={p:p.read_bytes() for p in root.iterdir()}
    result=observe_relabel_backbone_intent(root); rows=sites(result)
    first=rows['A:1']; assert first['coordinate_mapping']['coordinate_site']=='M:101'
    assert first['incoming_state']=='DECLARED_CONTINUATION' and first['partner_resolution']=='UNRESOLVED'
    assert first['incoming_partner'] is None and first['preserve_existing_atoms']==['P','OP1','OP2']
    assert first['do_not_connect'] and first['terminal_phosphate_authorized'] is None
    second=rows['A:2']; incoming=second['incoming_partner']
    assert second['protected'] and incoming['logical_site']=='A:1'
    assert incoming['before_target_operator_xyz']=='x,y,z'
    assert incoming['after_target_operator_xyz']=='-y,x,z-1/4'
    assert incoming['proposed_representation_seam'] and incoming['coordinate_endpoints_resolved']
    geometry=incoming['geometry']
    assert geometry['before_distance_angstrom']==pytest.approx(geometry['after_image_distance_angstrom'])
    assert geometry['after_direct_distance_angstrom']!=pytest.approx(geometry['after_image_distance_angstrom'])
    assert not geometry['chemical_geometry_validated']
    assert all(not result[k] for k in ('runtime_authority','bond_enforcement_enabled','phosphate_atoms_changed','chemical_connectivity_changed','scientific_acceptance'))
    assert all(p.read_bytes()==data for p,data in before.items()) and str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize('boundary,state,preserve',[('representation','DECLARED_CONTINUATION',True),('chemical','DECLARED_CHEMICAL_BOUNDARY',False),('unknown','UNKNOWN_BOUNDARY',False)])
def test_op3_conflict_is_scoped_to_explicit_continuation(tmp_path,boundary,state,preserve):
    root=packet(tmp_path,op3=True,boundary=boundary,aliases=True)
    row=sites(observe_relabel_backbone_intent(root))['A:1']
    assert row['incoming_state']==state and bool(row['preserve_existing_atoms'])==preserve
    assert ('EXISTING_OP3_CONFLICTS_WITH_DECLARED_CONTINUATION' in row['issues'])==preserve
    assert row['phosphate_inventory']['OP1'][0]['atom_name']=='O1P'
    assert row['phosphate_inventory']['OP2'][0]['atom_name']=='O2P'
    assert row['phosphate_inventory']['OP3'][0]['atom_name']=='O3P'
    assert row['terminal_phosphate_authorized'] is None


def test_missing_registered_partner_preserves_intent_without_geometry(tmp_path):
    root=packet(tmp_path,missing='A:1'); rows=sites(observe_relabel_backbone_intent(root))
    first=rows['A:1']; assert first['incoming_state']=='DECLARED_CONTINUATION'
    assert first['mapping_issues']==['MISSING_LOGICAL_MAPPING']
    assert first['issues']==['MISSING_P','MISSING_OP1','MISSING_OP2']
    second=rows['A:2']; assert second['partner_resolution']=='LOGICAL_PARTNER_RESOLVED'
    assert second['incoming_partner']['source_atom_indices']==[]
    assert not second['incoming_partner']['coordinate_endpoints_resolved']
    assert second['incoming_partner']['geometry'] is None


def test_alias_collision_is_retained_as_ambiguity(tmp_path):
    root=packet(tmp_path,aliases=True,duplicate=True)
    row=sites(observe_relabel_backbone_intent(root))['A:1']
    assert 'AMBIGUOUS_OP1' in row['issues']
    assert {a['atom_name'] for a in row['phosphate_inventory']['OP1']}=={'OP1','O1P'}


def test_source_geometry_does_not_infer_missing_bonds_or_dephosphorylation(tmp_path):
    root=packet(tmp_path,move=False,op3=True)
    result=observe_relabel_backbone_intent(root)
    assert result['proposed_route_seam_count']==0
    assert result['unresolved_continuation_count']==1
    rows=sites(result)
    assert rows['A:4']['three_prime_boundary']=='unknown'
    assert rows['B:3']['incoming_state']=='DECLARED_CHEMICAL_BOUNDARY'
    assert 'EXISTING_OP3_CONFLICTS_WITH_DECLARED_CONTINUATION' not in rows['B:3']['issues']


def test_relocation_preserves_observation_when_original_inputs_are_gone(tmp_path,monkeypatch):
    original=tmp_path/'original';original.mkdir();root=packet(original)
    expected=observe_relabel_backbone_intent(root)
    moved=tmp_path/'moved';shutil.move(root,moved);shutil.rmtree(original)
    opener=Path.open
    def guarded(self,*a,**kw):
        if self.resolve().is_relative_to(original):raise AssertionError('Original lookup forbidden')
        return opener(self,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    assert observe_relabel_backbone_intent(moved)==expected


def test_packet_drift_during_observation_refuses(tmp_path,monkeypatch):
    import nasolve.topostitch_recut_bundle as module
    root=packet(tmp_path);old=module._backbone_intent_observation
    def drift(*args):
        result=old(*args);p=root/'source.pdb';p.write_bytes(p.read_bytes()+b'REMARK drift\n');return result
    monkeypatch.setattr(module,'_backbone_intent_observation',drift)
    with pytest.raises(ValueError,match='changed during'):observe_relabel_backbone_intent(root)


def test_tampered_intent_in_derived_packet_is_not_authoritative(tmp_path):
    root=packet(tmp_path);path=root/'preview.json';r=json.loads(path.read_text())
    r['observation']['registered_graph']['declared_routes'][0]['five_prime_boundary']='chemical'
    path.write_text(json.dumps(r))
    with pytest.raises(ValueError):observe_relabel_backbone_intent(root)


def test_optional_view_preserves_old_scene_and_binds_preference_to_intent_context(tmp_path):
    from nasolve.topostitch_view import representative_scene, representative_comparison, validate_cut_preference, main
    from tests.test_topostitch_cut_comparison import cuts
    paths,_,_,_=cuts(tmp_path)
    old=representative_scene(paths[0]); enriched=representative_scene(paths[0],backbone_intent=True)
    assert enriched.pop('backbone_intent')==observe_relabel_backbone_intent(paths[0])
    assert enriched==old
    plain=representative_comparison(paths); result=representative_comparison(paths,backbone_intent=True)
    assert result['comparison_sha256']!=plain['comparison_sha256']
    request={k:result[k] for k in ('comparison_sha256','source_model_sha256','registered_graph_sha256')}
    request.update(schema_version=1,kind='topostitch-cut-preference',decision='needs_revision',preferred_preview_receipt_sha256=None,comment='Review unresolved continuation')
    preference=tmp_path/'preference.json'; preference.write_text(json.dumps(request))
    assert validate_cut_preference(paths,preference,backbone_intent=True)['decision']=='needs_revision'
    with pytest.raises(ValueError):validate_cut_preference(paths,preference)
    out=tmp_path/'view.html'
    assert main([str(paths[0]),'--compare',str(paths[1]),'--backbone-intent','--preference',str(preference),'--out',str(out)])==0
    assert 'topostitch-representative-backbone-intent' in out.read_text()
    assert representative_scene(paths[0])==old


@pytest.mark.parametrize('value',[1,'yes',None])
def test_intent_view_option_requires_boolean(tmp_path,value):
    from nasolve.topostitch_view import representative_scene,write_preview_view
    with pytest.raises(ValueError,match='boolean'):representative_scene(tmp_path,backbone_intent=value)
    with pytest.raises(ValueError,match='boolean'):write_preview_view(tmp_path,tmp_path/'no.html',backbone_intent=value)
    assert not (tmp_path/'no.html').exists()


def test_backbone_intent_flag_refuses_bend_packet(tmp_path):
    from tests.test_topostitch_preview import setup_preview,build
    from nasolve.topostitch_view import write_preview_view
    inputs=setup_preview(tmp_path);root=tmp_path/'bend';build(inputs,root)
    out=tmp_path/'no.html'
    with pytest.raises(ValueError,match='representative'):write_preview_view(root,out,backbone_intent=True)
    assert not out.exists()


@pytest.mark.parametrize('name,issue', [('P','MISSING_P'),('OP1','MISSING_OP1'),("O3'",None)])
def test_missing_atom_is_reported_without_erasing_logical_continuation(tmp_path,name,issue):
    root=packet(tmp_path,omit=(name,));row=sites(observe_relabel_backbone_intent(root))['A:2']
    assert row['incoming_state']=='DECLARED_CONTINUATION'
    assert row['partner_resolution']=='LOGICAL_PARTNER_RESOLVED'
    if issue:assert issue in row['issues']
    assert row['incoming_partner']['coordinate_endpoints_resolved']==(name=='OP1')
    assert not row['terminal_phosphate_authorized']


@pytest.mark.parametrize('cell,group,operator', [
    ((30, 30, 40, 90, 90, 90), 'P 43', 'y,-x,z+1/4'),
    ((30, 30, 40, 90, 90, 120), 'R 3:H', '-y,x-y,z'),
])
def test_one_pair_stagger_preserves_both_routes_phosphates_and_tensor_frame(
        tmp_path, cell, group, operator):
    """Synthetic bookkeeping only: a cut is not a nick or a repaired molecule."""
    import gemmi
    from tests.test_topostitch_periodic import cryst1
    from nasolve.topostitch_recut_bundle import load_relabel_reference_frame

    packet(tmp_path)  # Reuse the renamed two-duplex fixture and phosphate atoms.
    model = tmp_path/'model.pdb'
    discovery = tmp_path/'discovery.json'
    registration = tmp_path/'registration.json'
    model.write_text(cryst1(cell, group) + '\n'.join(model.read_text().splitlines()[1:]) + '\n')
    registry = json.loads(registration.read_text())
    registry['model']['sha256'] = sha256(model.read_bytes()).hexdigest()
    registration.write_text(json.dumps(registry))
    manifest = json.loads(discovery.read_text())
    # The reusable fixture stores target sites in record order; declare 5′→3′.
    for strand in manifest['strands']:
        strand['sites'].sort(key=lambda site: int(site.split(':')[1]))
    manifest.update(model_sha256=registry['model']['sha256'],
                    registration_sha256=sha256(registration.read_bytes()).hexdigest())
    discovery.write_text(json.dumps(manifest))
    graph = build_registered_periodic_graph(model, discovery, registration)
    # Rungs A3:B3 and A4:B2: cut A2|A3 opposite B2|B3.
    # Exactly one paired rung crosses the new representative boundary.
    moved = {'A:3', 'A:4', 'B:2'}
    assert sum((a in moved) != (b in moved) for a, b in manifest['duplex_pairs']) == 1
    request = dict(schema_version=1, kind='topostitch-representative-proposal',
                   registered_graph_sha256=graph['report_sha256'], extra_edges=[],
                   node_images=[dict(node_id=n['node_id'], operator_xyz=operator)
                                for n in graph['nodes'] if n['logical_site'] in moved],
                   coincidence_tolerance_angstrom=.01, max_atom_tests=2_000_000)
    proposal = tmp_path/'stagger.json'
    proposal.write_text(json.dumps(request))
    original = {p: p.read_bytes() for p in (model, discovery, registration, proposal)}
    root = tmp_path/'stagger'
    result = build_relabel_preview(model, discovery, registration_path=registration,
                                  proposal_path=proposal, output_directory=root)
    observation = result['observation']
    rows = sites(observe_relabel_backbone_intent(root))
    seams = {site: row['incoming_partner'] for site, row in rows.items()
             if row['incoming_partner'] and row['incoming_partner']['proposed_representation_seam']}
    assert set(seams) == {'A:3', 'B:3'}
    assert seams['A:3']['logical_site'] == 'A:2'
    assert seams['B:3']['logical_site'] == 'B:2'
    assert seams['A:3']['after_target_operator_xyz'] == gemmi.Op(operator).inverse().triplet()
    assert seams['B:3']['after_target_operator_xyz'] == operator
    for site in seams:
        assert rows[site]['preserve_existing_atoms'] == ['P', 'OP1', 'OP2']
        assert rows[site]['phosphate_inventory']['OP3'] == []
        assert rows[site]['terminal_phosphate_authorized'] is None
        geometry = seams[site]['geometry']
        assert geometry['before_distance_angstrom'] == pytest.approx(geometry['after_image_distance_angstrom'])
    assert {g['logical_site'] for g in observation['atom_image_groups']} == moved
    assert not result['coordinates_materialized'] and not result['chemical_connectivity_changed']
    digest = sha256((root/'preview.json').read_bytes()).hexdigest()
    frame = load_relabel_reference_frame(root, expected_receipt_sha256=digest)
    points = [a['position_angstrom'] for a in observation['source_orbit_observation']['atoms']]
    represented = frame.to_representatives(points, source_labels=frame.source_labels, context_sha256=digest)
    restored = frame.to_source(represented, atom_labels=frame.atom_labels, context_sha256=digest)
    tensors = [(.1 + i*.001, .2, .3, .01, -.02, .03) for i in range(len(points))]
    rotated = frame.tensors_to_representatives(tensors, source_labels=frame.source_labels, context_sha256=digest)
    recovered = frame.tensors_to_source(rotated, atom_labels=frame.atom_labels, context_sha256=digest)
    for i in range(len(points)):
        assert restored[i] == pytest.approx(points[i], abs=1e-10)
        assert recovered[i] == pytest.approx(tensors[i], abs=1e-12)
    for i in observation['fixed_atom_indices']:
        assert represented[i] == tuple(points[i]) and rotated[i] == tensors[i]
    assert all(p.read_bytes() == value for p, value in original.items())
    assert str(tmp_path) not in json.dumps(result)
