"""Source interpretation must remain distinct from a new symmetry bond."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import shutil

import pytest
pytest.importorskip('gemmi')
from nasolve.topostitch_recut_bundle import build_relabel_preview,observe_relabel_native_links
from tests.test_topostitch_recut_bundle import setup


@pytest.fixture
def seam(tmp_path,monkeypatch):
    # Fake Cedar owners isolate this adapter only; actual authentication is
    # exercised separately on retained native captures, not claimed by mocks.
    args,_=setup(tmp_path);packet=tmp_path/'packet';r=build_relabel_preview(**args,output_directory=packet)
    atoms=r['observation']['source_orbit_observation']['atoms'];keys=[]
    for atom in atoms:
        a=atom['identity'];keys.append((a['chain']+':'+str(a['residue_number']),a['residue_code'],a['atom_name']))
    moved=set(r['observation']['requested_image_atom_indices']);i=next(iter(moved));j=next(k for k in range(len(atoms)) if k not in moved)
    link=dict(endpoints=[list(keys[i]),list(keys[j])],distance_ideal=1.6,weight=100.,origin_id=0)
    capture=tmp_path/'capture';capture.mkdir();receipt=capture/'receipt.json';receipt.write_text('synthetic capture')
    state=dict(args=args,links=[link],symmetry=[],keys=keys,receipt=receipt,capture=capture,packet=packet,model=(packet/'source.pdb').read_bytes(),status='REVIEW',native_counts=dict(bond_simple=1,bond_asu=0))
    @contextmanager
    def owners(source=None):
        def read(path,model):
            assert model==state['model'] and path==state['receipt']
            if state.get('refuse'):raise ValueError('Native receipt authentication refused')
            return dict(status=state['status'],policy_id='synthetic-policy',phenix_version='synthetic-version'),state.get('native',dict(geometry=dict(proxy_counts=state['native_counts']))),{path.resolve():path.read_bytes()}
        def links(*args):
            if state.get('drift'):state['receipt'].write_text('changed capture')
            return deepcopy(state['links']),deepcopy(state['symmetry'])
        def review(native):
            if state.get('packing_drift'):state['receipt'].write_text('changed during packing review')
            return deepcopy(state['review'])
        yield dict(cif_attachment_native=SimpleNamespace(_capture=read,_native_atoms=lambda *a:(state['keys'],state.get('labels',['synthetic']*len(keys))),_links=links),
                   cif_native_nonbonded=SimpleNamespace(review_native_nonbonded=review))
    import nasolve.topostitch_captured_job as jobs
    monkeypatch.setattr(jobs,'_cedar',owners)
    return state


def test_native_identity_link_moves_to_exact_image_without_activating_bond(seam):
    r=observe_relabel_native_links(seam['packet'],seam['receipt']);row=r['links'][0]
    assert row['status']=='PROPOSED_SYMMETRY_SEAM' and r['proposed_seam_count']==1
    assert row['before_distance_angstrom']==pytest.approx(row['after_image_distance_angstrom'],abs=1e-10)
    assert row['after_direct_distance_angstrom']!=pytest.approx(row['after_image_distance_angstrom'])
    assert row['maximum_coordinate_error_angstrom']<1e-10
    assert not any(r[k] for k in ('bond_enforcement_enabled','chemical_connectivity_changed','phosphate_atoms_changed','coordinates_materialized','scientific_acceptance','runtime_authority'))
    assert str(seam['packet'].parent) not in json.dumps(r)


def test_duplicate_source_links_retain_multiplicity_and_source_symmetry_stays_unqualified(seam):
    seam['links']*=2;seam['native_counts']['bond_simple']=3
    existing=dict(i_seqs=[0,1],symmetry_operation='y,-x,z+1/4',weight=100.)
    seam['symmetry']=[existing]
    r=observe_relabel_native_links(seam['packet'],seam['receipt'])
    assert len(r['links'])==2 and [v['link_id'] for v in r['links']]==[1,2]
    assert r['source_symmetry_links_unqualified']==[existing] and r['proposed_seam_count']==2


def test_native_reordering_does_not_reassign_source_coordinates(seam):
    expected=observe_relabel_native_links(seam['packet'],seam['receipt']);seam['keys']=list(reversed(seam['keys']))
    assert observe_relabel_native_links(seam['packet'],seam['receipt'])==expected


@pytest.mark.parametrize('defect',['refuse','drift','failed','missing_atom'])
def test_stale_incomplete_or_failed_capture_cannot_gain_seam_authority(seam,defect):
    if defect in ('refuse','drift'):seam[defect]=True
    elif defect=='failed':seam['status']='FAILED'
    else:seam['keys']=seam['keys'][:-1]
    with pytest.raises(ValueError):observe_relabel_native_links(seam['packet'],seam['receipt'])


def test_packet_and_capture_relocate_without_original_inputs(seam,tmp_path):
    expected=observe_relabel_native_links(seam['packet'],seam['receipt'])
    new=tmp_path/'relocated';new.mkdir();oldpacket=seam['packet'];oldcapture=seam['capture']
    shutil.move(oldpacket,new/'packet');shutil.move(oldcapture,new/'capture')
    seam.update(packet=new/'packet',capture=new/'capture',receipt=new/'capture/receipt.json')
    assert not oldpacket.exists() and not oldcapture.exists()
    assert observe_relabel_native_links(seam['packet'],seam['receipt'])==expected


def test_noop_retains_source_identity_links_without_new_seams(seam):
    request=seam['args']['proposal_path'];data=json.loads(request.read_text());data['node_images']=[];request.write_text(json.dumps(data))
    out=seam['packet'].parent/'noop';build_relabel_preview(**seam['args'],output_directory=out)
    r=observe_relabel_native_links(out,seam['receipt'])
    assert r['proposed_seam_count']==0 and r['links'][0]['status']=='SAME_REPRESENTATIVE'
    assert r['links'][0]['after_direct_distance_angstrom']==r['links'][0]['before_distance_angstrom']


def test_optional_view_and_cli_expose_seams_but_old_scene_stays_exact(seam,tmp_path):
    from nasolve.topostitch_view import representative_scene,write_preview_view,main
    old=representative_scene(seam['packet']);assert 'native_links' not in old
    before={p:p.read_bytes() for p in seam['packet'].iterdir()}
    r=write_preview_view(seam['packet'],tmp_path/'native.html',native_receipt=seam['receipt'])
    assert r['native_links']['proposed_seam_count']==1
    assert any('existing source interresidue' in warning for warning in r['warnings'])
    assert not r['graphical_review_recorded'] and not r['chemical_connectivity_changed']
    assert main([str(seam['packet']),'--out',str(tmp_path/'cli.html'),'--native-receipt',str(seam['receipt'])])==0
    assert representative_scene(seam['packet'])==old
    assert all(p.read_bytes()==data for p,data in before.items())


def test_invalid_native_view_options_and_bad_capture_create_no_html(seam,tmp_path):
    from nasolve.topostitch_view import write_preview_view
    out=tmp_path/'invalid.html'
    with pytest.raises(ValueError,match='requires an explicit native receipt'):write_preview_view(seam['packet'],out,cedar_source='developer')
    assert not out.exists()
    seam['refuse']=True
    with pytest.raises(ValueError,match='authentication'):write_preview_view(seam['packet'],out,native_receipt=seam['receipt'])
    assert not out.exists()


def packing_source(state):
    import math
    from nasolve.topostitch_recut_bundle import load_relabel_preview
    from nasolve.topostitch_packing import NATIVE_POLICY
    preview=load_relabel_preview(state['packet'])['observation']
    points=[a['position_angstrom'][:] for a in preview['source_orbit_observation']['atoms']]
    labels=['source-atom-'+str(i) for i in range(len(points))]
    keys=[tuple(v) for v in state['links'][0]['endpoints']]
    i,j=[state['keys'].index(key) for key in keys];distance=math.dist(points[i],points[j]);vdw=3.
    state['labels']=labels
    state['native']=dict(atom_count=len(points),atoms=[dict(i_seq=i,label=label,xyz=points[i]) for i,label in enumerate(labels)],
        geometry=dict(proxy_counts=state['native_counts'],sites_cart_exact=points),
        nonbonded_inventory=dict(policy_id=NATIVE_POLICY,unit_cell=preview['registered_graph']['periodic_graph']['crystal']['cell_parameters'],
            pairs=[['simple',i,j,0,vdw]],mappings=[]))
    row=dict(proxy_index=0,kind='simple',i_seqs=[i,j],image_j=0,atoms=[labels[i],labels[j]],vdw_distance=vdw,
             distance=distance,overlap=vdw-distance,residual=max(0.,vdw-distance)**4,residual_weight=1.)
    state['review']=dict(policy_id=NATIVE_POLICY,analysis_completed=True,pair_sum_and_gradient_replay=True,
        fixed_manager_repeats=True,geometry_accepted=False,measurements=[row],pair_count=1,total_residual=row['residual'])
    return state


def packing_report(state):
    from nasolve.topostitch_recut_bundle import observe_relabel_native_packing
    return observe_relabel_native_packing(state['packet'],state['receipt'])


def test_native_packing_report_binds_complete_preview_and_receipt_without_edits(seam):
    from hashlib import sha256
    state=packing_source(seam);paths=[*state['packet'].iterdir(),state['receipt']]
    frozen={p:p.read_bytes() for p in paths};r=packing_report(state)
    assert r['preview_receipt_sha256']==sha256(frozen[state['packet']/'preview.json']).hexdigest()
    assert r['native_receipt_sha256']==sha256(frozen[state['receipt']]).hexdigest()
    assert r['source_model_sha256']==sha256(state['model']).hexdigest()
    assert r['packing']['source_directed_row_count']==1
    assert r['packing']['maximum_distance_error_angstrom']<1e-10
    assert r['maximum_preview_coordinate_error_angstrom']<1e-10
    assert not any(r[k] for k in ('runtime_authority','scientific_acceptance','coordinates_materialized'))
    assert all(p.read_bytes()==data for p,data in frozen.items())
    assert str(state['packet'].parent) not in json.dumps(r)


def test_native_packing_uses_native_order_without_reassigning_atom_identity(seam):
    state=packing_source(seam);before=packing_report(state);n=state['native'];size=n['atom_count']
    state['keys'].reverse();state['labels'].reverse();n['atoms'].reverse();n['geometry']['sites_cart_exact'].reverse()
    for i,a in enumerate(n['atoms']):a['i_seq']=i
    pair=n['nonbonded_inventory']['pairs'][0];pair[1],pair[2]=size-1-pair[1],size-1-pair[2]
    state['review']['measurements'][0]['i_seqs']=[pair[1],pair[2]]
    after=packing_report(state)
    a,b=before['packing']['contacts'][0],after['packing']['contacts'][0]
    assert a['source']['atoms']==b['source']['atoms']
    assert a['representative_target_operator_xyz']==b['representative_target_operator_xyz']
    assert a['representative_distance_angstrom']==pytest.approx(b['representative_distance_angstrom'],abs=1e-10)
    assert before['packing']['source_native_sha256']!=after['packing']['source_native_sha256']


@pytest.mark.parametrize('defect',['missing','translated','cell','review_drift'])
def test_native_packing_refuses_incomplete_or_changed_preview_context(seam,defect):
    state=packing_source(seam)
    if defect=='missing':state['keys'].pop()
    elif defect=='translated':
        for point in state['native']['geometry']['sites_cart_exact']:point[0]+=.1
    elif defect=='cell':state['native']['nonbonded_inventory']['unit_cell']=list(state['native']['nonbonded_inventory']['unit_cell']);state['native']['nonbonded_inventory']['unit_cell'][2]+=1
    else:state['packing_drift']=True
    with pytest.raises(ValueError):packing_report(state)


def test_native_packing_replays_after_declared_packet_and_capture_relocation(seam,tmp_path):
    state=packing_source(seam);before=packing_report(state);oldpacket=state['packet'];oldcapture=state['capture']
    moved=tmp_path/'native-packing-relocated';moved.mkdir();shutil.move(oldpacket,moved/'packet');shutil.move(oldcapture,moved/'capture')
    state.update(packet=moved/'packet',capture=moved/'capture',receipt=moved/'capture/receipt.json')
    assert not oldpacket.exists() and not oldcapture.exists()
    assert packing_report(state)==before
