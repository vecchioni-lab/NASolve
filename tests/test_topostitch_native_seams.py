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
            return dict(status=state['status'],policy_id='synthetic-policy',phenix_version='synthetic-version'),dict(geometry=dict(proxy_counts=state['native_counts'])),{path.resolve():path.read_bytes()}
        def links(*args):
            if state.get('drift'):state['receipt'].write_text('changed capture')
            return deepcopy(state['links']),deepcopy(state['symmetry'])
        yield dict(cif_attachment_native=SimpleNamespace(_capture=read,_native_atoms=lambda *a:(state['keys'],['synthetic']*len(keys)),_links=links))
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
