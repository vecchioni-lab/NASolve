"""Scattering observations must distinguish representative changes from damage."""
from hashlib import sha256
import json
import shutil

import pytest
gemmi=pytest.importorskip('gemmi')
from nasolve.topostitch_graph import build_registered_periodic_graph
from nasolve.topostitch_scattering import observe_registered_relabel_scattering
from tests.test_topostitch_graph import registered
from tests.test_topostitch_periodic import cryst1

HKLS=[[0,0,0],[1,2,3],[-1,3,2],[3,2,1],[1,1,4],[2,0,0]]


def rebind(paths,text):
    model,discovery,reg=paths;model.write_text(text)
    r=json.loads(reg.read_text());r['model']['sha256']=sha256(model.read_bytes()).hexdigest();reg.write_text(json.dumps(r))
    d=json.loads(discovery.read_text());d['model_sha256']=r['model']['sha256'];d['registration_sha256']=sha256(reg.read_bytes()).hexdigest();discovery.write_text(json.dumps(d))


def fixture(tmp_path,*,anisou=True,cell=(30,30,40,90,90,90),group='P 43',image='y,-x,z+1/4'):
    model,discovery,reg,_=registered(tmp_path,rename=True);paths=(model,discovery,reg)
    rows=[]
    for row in model.read_text().splitlines(keepends=True):
        if row.startswith('CRYST1'):rows.append(cryst1(cell,group));continue
        rows.append(row)
        if anisou and row.startswith(('ATOM','HETATM')):
            rows.append('ANISOU'+row[6:28]+''.join(f'{v:7d}' for v in (1000,2000,3000,100,50,-25))+row[70:])
    rebind(paths,''.join(rows));graph=build_registered_periodic_graph(*paths)
    chosen=next(n for n in graph['nodes'] if n['logical_site']=='A:2')
    kwargs=dict(node_images=[dict(node_id=chosen['node_id'],operator_xyz=image)],expected_registered_graph_sha256=graph['report_sha256'],hkls=HKLS)
    return paths,kwargs


@pytest.mark.parametrize('cell,group,image',[
    ((30,30,40,90,90,90),'P 43','y,-x,z+1/4'),
    ((30,30,40,90,90,120),'H 3','-x+y+2/3,-x+1/3,z+1/3'),
    ((30,40,50,90,110,90),'P 21','-x,y+1/2,-z'),
])
def test_screw_centered_and_oblique_representatives_preserve_sampled_scattering(tmp_path,cell,group,image):
    paths,kw=fixture(tmp_path,cell=cell,group=group,image=image)
    before={p:p.read_bytes() for p in paths}
    report=observe_registered_relabel_scattering(*paths,**kw)
    assert report['relative_l2_complex_difference']<1e-7
    assert report['transported_anisou'] and report['anisou_count']==report['atom_count']
    assert report['space_group_image_count']==len(gemmi.SpaceGroup(group).operations())
    assert report['reflections'][0]['absolute_complex_difference']==0
    assert report['status']=='OBSERVED_REVIEW_REQUIRED'
    assert not report['scattering_invariance_validated'] and not report['coordinates_materialized']
    assert report['policy']['numerical_acceptance_threshold'] is None
    assert str(tmp_path) not in json.dumps(report)
    assert all(p.read_bytes()==b for p,b in before.items())


def test_isotropic_noop_and_lattice_translation_are_distinct_explicit_cases(tmp_path):
    paths,kw=fixture(tmp_path,anisou=False,image='x+2,y-1,z')
    report=observe_registered_relabel_scattering(*paths,**kw)
    assert report['anisou_count']==0 and report['transported_anisou']==[]
    assert report['maximum_absolute_complex_difference']<1e-9
    noop=observe_registered_relabel_scattering(*paths,**{**kw,'node_images':[]})
    assert noop['maximum_absolute_complex_difference']==0


def test_unrotated_anisotropic_tensors_are_detectable_by_complex_scattering(tmp_path,monkeypatch):
    paths,kw=fixture(tmp_path)
    monkeypatch.setattr(gemmi.UnitCell,'op_as_transform',lambda *a:gemmi.Transform())
    result=observe_registered_relabel_scattering(*paths,**kw)
    assert result['maximum_absolute_complex_difference']>.01
    assert result['relative_l2_complex_difference']>1e-5
    assert not result['scattering_invariance_validated']


def test_distorted_coordinate_is_visible_without_becoming_a_new_acceptance_policy(tmp_path,monkeypatch):
    paths,kw=fixture(tmp_path,anisou=False)
    import nasolve.topostitch_scattering as module
    original=module.preview_registered_relabel
    def damaged(*a,**kw):
        value=original(*a,**kw);value['proposed_points_angstrom'][value['requested_image_atom_indices'][0]][0]+=.5
        return value
    monkeypatch.setattr(module,'preview_registered_relabel',damaged)
    result=observe_registered_relabel_scattering(*paths,**kw)
    assert result['maximum_absolute_complex_difference']>.1
    assert result['status']=='OBSERVED_REVIEW_REQUIRED'


@pytest.mark.parametrize('defect',['duplicate_anisou','orphan_anisou','zero_tensor','negative_tensor','missing_element','unsupported_element','negative_b','ncs'])
def test_ambiguous_or_unsupported_scattering_inputs_refuse(tmp_path,defect):
    paths,kw=fixture(tmp_path);rows=paths[0].read_text().splitlines(keepends=True)
    i=next(i for i,r in enumerate(rows) if r.startswith('ANISOU'))
    if defect=='duplicate_anisou':rows.insert(i,rows[i])
    elif defect=='orphan_anisou':rows[i]=rows[i][:6]+'99999'+rows[i][11:]
    elif defect in ('zero_tensor','negative_tensor'):
        values=(0,0,0,0,0,0) if defect=='zero_tensor' else (-1000,2000,3000,0,0,0)
        rows[i]=rows[i][:28]+''.join(f'{v:7d}' for v in values)+rows[i][70:]
    elif defect=='missing_element':
        rows=[r[:76]+'  '+r[78:] if r.startswith(('ATOM','HETATM','ANISOU')) else r for r in rows]
    elif defect=='unsupported_element':
        rows=[r[:76]+'OG'+r[78:] if r.startswith(('ATOM','HETATM','ANISOU')) else r for r in rows]
    elif defect=='negative_b':rows[i-1]=rows[i-1][:60]+' -1.00'+rows[i-1][66:]
    else:
        for axis in range(3):rows.insert(1,f'MTRIX{axis+1}   1'+''.join(f'{float(j==axis):10.6f}' for j in range(3))+'     0.00000    1\n')
    rebind(paths,''.join(rows));kw['expected_registered_graph_sha256']=build_registered_periodic_graph(*paths)['report_sha256']
    with pytest.raises(ValueError):observe_registered_relabel_scattering(*paths,**kw)


@pytest.mark.parametrize('hkls',[[],[[True,0,1]],[[1,2,10001]],[[1,2,3],[1,2,3]],[[0,0,0],[0,0,1]]])
def test_invalid_or_noninformative_reflection_requests_refuse(tmp_path,hkls):
    paths,kw=fixture(tmp_path)
    with pytest.raises(ValueError):observe_registered_relabel_scattering(*paths,**{**kw,'hkls':hkls})


def test_scattering_work_budget_is_enforced_before_calculation(tmp_path,monkeypatch):
    paths,kw=fixture(tmp_path)
    def forbidden(*a):raise AssertionError('Should not construct calculator')
    monkeypatch.setattr(gemmi,'StructureFactorCalculatorX',forbidden)
    with pytest.raises(ValueError,match='work budget'):observe_registered_relabel_scattering(*paths,**kw,max_structure_factor_terms=1)


def test_inputs_changed_during_observation_refuse_and_relocation_replays(tmp_path,monkeypatch):
    original=tmp_path/'original';original.mkdir();paths,kw=fixture(original)
    report=observe_registered_relabel_scattering(*paths,**kw)
    relocated=tmp_path/'relocated';shutil.move(original,relocated);paths=tuple(relocated/p.name for p in paths)
    assert not original.exists()
    assert observe_registered_relabel_scattering(*paths,**kw)==report
    import nasolve.topostitch_scattering as module
    original_structure=module._structure
    def changed(*a,**kw):
        value=original_structure(*a,**kw);paths[1].write_text(paths[1].read_text()+'\n');return value
    monkeypatch.setattr(module,'_structure',changed)
    with pytest.raises(ValueError,match='changed during'):observe_registered_relabel_scattering(*paths,**kw)


def test_process_global_charge_policy_is_not_silently_changed(tmp_path):
    paths,kw=fixture(tmp_path)
    original=gemmi.IT92_get_ignore_charge()
    try:
        gemmi.IT92_set_ignore_charge(False)
        with pytest.raises(ValueError,match='neutral IT92'):observe_registered_relabel_scattering(*paths,**kw)
        assert gemmi.IT92_get_ignore_charge() is False
    finally:gemmi.IT92_set_ignore_charge(original)


def saved_scattering_packet(tmp_path, *, forest=False):
    from nasolve.topostitch_recut_bundle import build_relabel_preview
    if forest:
        from tests.test_topostitch_continuations import setup, request
        paths, links = setup(tmp_path)
        args, _, _ = request(paths, links, forest=True)
    else:
        paths, kw = fixture(tmp_path)
        request = dict(schema_version=1, kind='topostitch-representative-proposal',
            registered_graph_sha256=kw['expected_registered_graph_sha256'],
            node_images=kw['node_images'], extra_edges=[],
            coincidence_tolerance_angstrom=.01, max_atom_tests=2_000_000)
        proposal = tmp_path/'chosen.json'; proposal.write_text(json.dumps(request))
        args = dict(model=paths[0], discovery=paths[1], registration_path=paths[2], proposal_path=proposal)
    root = tmp_path/'saved-scattering'
    receipt = build_relabel_preview(**args, output_directory=root)
    return root, sha256((root/'preview.json').read_bytes()).hexdigest(), receipt


@pytest.mark.parametrize('forest', [False, True])
def test_saved_cut_scattering_uses_verified_images_and_continuations(tmp_path, forest):
    from nasolve.topostitch_recut_bundle import observe_relabel_scattering
    root, digest, receipt = saved_scattering_packet(tmp_path, forest=forest)
    original = {p:p.read_bytes() for p in root.iterdir()}
    result = observe_relabel_scattering(root, expected_receipt_sha256=digest, hkls=HKLS)
    observation = result['observation']
    assert result['preview_receipt_sha256'] == digest
    assert observation['preview_sha256'] == receipt['observation']['preview_sha256']
    assert observation['registered_graph_sha256'] == receipt['registered_graph_sha256']
    assert observation['source_model_sha256'] == receipt['source_model_sha256']
    assert observation['relative_l2_complex_difference'] < 1e-7
    assert not result['runtime_authority'] and not result['scientific_acceptance']
    assert not result['scattering_invariance_validated'] and not result['coordinates_materialized']
    if forest:
        assert receipt['observation']['registered_graph']['declared_continuations']
        assert receipt['forest_selection']
    else:
        assert observation['transported_anisou']
    assert {p:p.read_bytes() for p in root.iterdir()} == original
    assert str(tmp_path) not in json.dumps(result)


def test_saved_cut_wrong_pin_refuses_before_scattering(tmp_path, monkeypatch):
    from nasolve.topostitch_recut_bundle import observe_relabel_scattering
    import nasolve.topostitch_scattering as module
    root, digest, _ = saved_scattering_packet(tmp_path)
    monkeypatch.setattr(module, 'observe_registered_relabel_scattering',
        lambda *a, **k: pytest.fail('A different saved cut must not be evaluated'))
    with pytest.raises(ValueError, match='receipt'):
        observe_relabel_scattering(root, expected_receipt_sha256='0'*64, hkls=HKLS)


@pytest.mark.parametrize('change', ['receipt', 'observation'])
def test_saved_cut_drift_or_mismatched_calculation_refuses(tmp_path, monkeypatch, change):
    from nasolve.topostitch_recut_bundle import observe_relabel_scattering
    import nasolve.topostitch_scattering as module
    from nasolve.topostitch_registration import _fingerprint
    root, digest, _ = saved_scattering_packet(tmp_path)
    calculate = module.observe_registered_relabel_scattering
    def changed(*a, **k):
        result = calculate(*a, **k)
        if change == 'receipt':
            path = root/'preview.json'; path.write_bytes(path.read_bytes()+b'\n')
        else:
            result['preview_sha256'] = '0'*64
            result['report_sha256'] = _fingerprint({k:v for k,v in result.items() if k != 'report_sha256'})
        return result
    monkeypatch.setattr(module, 'observe_registered_relabel_scattering', changed)
    with pytest.raises(ValueError, match='changed|differs'):
        observe_relabel_scattering(root, expected_receipt_sha256=digest, hkls=HKLS)


def test_saved_cut_scattering_relocates_without_original_source_or_new_files(tmp_path, monkeypatch):
    from pathlib import Path
    from nasolve.topostitch_recut_bundle import observe_relabel_scattering
    original = tmp_path/'original'; original.mkdir()
    root, digest, _ = saved_scattering_packet(original)
    expected = observe_relabel_scattering(root, expected_receipt_sha256=digest, hkls=HKLS)
    moved = tmp_path/'moved'; shutil.move(root,moved); shutil.rmtree(original)
    opener = Path.open
    def guarded(self, *a, **k):
        if self.resolve().is_relative_to(original): raise AssertionError('Original path lookup')
        return opener(self, *a, **k)
    monkeypatch.setattr(Path, 'open', guarded)
    assert observe_relabel_scattering(moved, expected_receipt_sha256=digest, hkls=HKLS) == expected
    with pytest.raises(ValueError, match='work budget'):
        observe_relabel_scattering(moved, expected_receipt_sha256=digest, hkls=HKLS, max_structure_factor_terms=1)
