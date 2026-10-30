"""Native trial inspection must keep exact geometry, maps and action boundaries."""
import copy
import json
from pathlib import Path
import pytest
from nasolve.metal.recipe import RecipeError
from nasolve.metal.workbench import capture_catalog
from nasolve.metal.viewer import open_viewer
from nasolve.metal.inspection import coot_script
from nasolve.metal._map_preview_native import contours
from tests.test_metal_candidate_review import cases


def setup(tmp_path, monkeypatch):
    c,paths=cases(tmp_path,monkeypatch)
    hypotheses=[]
    for i,path in enumerate(paths):
        trial=json.loads((c.run/path/'manifest.json').read_text())
        hypotheses.append(dict(hypothesis_id='candidate'+str(i),label='Geometry '+str(i),
          geometry={k:trial['parent']['manifest'][k] for k in ('anchor','relative_path')},sites=[],
          results=[dict(result_id='fit',label='Frozen fit',kind='fdp-trial',manifest=dict(anchor='run',relative_path=str(path/'manifest.json')))]))
    request=dict(kind='metal-workbench-request',schema_version=1,campaign_id='native',label='Native endpoints',datasets=[dict(dataset_id='one',label='Data',structures=[dict(structure_id='frame',label='Frame',run=dict(anchor='dataset',relative_path='AutoMR/run_001'),hypotheses=hypotheses)])])
    mounts={'one':c.run.parent.parent}
    return c.run,request,mounts,open_viewer(capture_catalog(request,mounts),mounts)


def test_native_endpoints_and_single_fdp_trials_select_their_own_sources(tmp_path,monkeypatch):
    run,request,mounts,viewer=setup(tmp_path,monkeypatch)
    rows=viewer.workbench.to_dict()['rows'];assert len(rows)==4
    for row in rows:
        out=viewer.navigate(dict(action='row',selection=viewer.workbench.initial_selection(),row_id=row['row_id']))
        scene=out['scene'];assert scene['status']=='XYZ_REVIEW'
        info=scene['inspection'];assert info['id']==row['data']['trial_id']
        assert info['model']['relative_path'].endswith('final.pdb')
        assert '/fdp_' in info['model']['relative_path']
        assert '/xyz_' in scene['model']['relative_path']
        assert info['maps']==[]
    wrong=copy.deepcopy(request)
    wrong['datasets'][0]['structures'][0]['hypotheses'][0]['results'][0]['manifest']=request['datasets'][0]['structures'][0]['hypotheses'][1]['results'][0]['manifest']
    with pytest.raises(RecipeError,match='different geometry'):capture_catalog(wrong,mounts)


def test_inspection_rechecks_sources_before_launch_or_cache(tmp_path,monkeypatch):
    run,_,_,viewer=setup(tmp_path,monkeypatch);scene=viewer.present()['scene'];calls=[]
    monkeypatch.setattr(viewer.inspections,'_coot',lambda *args:calls.append(args) or {'status':'LAUNCHED'})
    assert viewer.inspections.perform('coot',scene,None)['status']=='LAUNCHED'
    assert len(calls)==1
    key=copy.deepcopy(scene['atoms'][0]['key']);key['atom_name']='absent'
    with pytest.raises(RecipeError,match='exact atom'):viewer.inspections.perform('coot',scene,key)
    (run/scene['inspection']['model']['relative_path']).write_text('changed')
    with pytest.raises(RecipeError):viewer.inspections.perform('coot',scene,None)
    assert len(calls)==1


def test_coot_script_uses_exact_labels_boolean_flag_and_reports_actual_load():
    script=coot_script([], [dict(filename='map.mtz',labels=['ANOM','PHANOM'],sigma=3.,difference=False,title='Anomalous')],[1.,2.,3.],'Test')
    assert "phase,'',False)" in script
    assert "status='READY'" in script and "status='ERROR'" in script
    compile(script,'coot.py','exec')


def test_density_intersection_is_on_the_expected_cartesian_plane():
    values=[[[float(i) for k in range(3)] for j in range(3)] for i in range(3)]
    segments,truncated=contours(values,[-1.,2.,3.],.5,1.5)
    assert segments and not truncated
    assert all(p[0]==pytest.approx(-.25) for edge in segments for p in edge)
    assert contours(values,[0.,0.,0.],1.,4.)==( [],False)
    assert contours(values,[0.,0.,0.],1.,1.5,limit=2)[1] is True


def test_native_catalog_relocates_and_inspection_uses_new_mount(tmp_path,monkeypatch):
    run,request,mounts,viewer=setup(tmp_path/'old',monkeypatch)
    catalog=capture_catalog(request,mounts);expected=viewer.present()
    old=tmp_path/'old';moved=tmp_path/'moved';old.rename(moved)
    restored=open_viewer(catalog,{'one':moved/'dataset'})
    assert restored.present()==expected and not old.exists()
    calls=[];monkeypatch.setattr(restored.inspections,'_coot',lambda *a:calls.append(a[0]['run']) or {})
    restored.inspections.perform('coot',restored.present()['scene'],None)
    assert calls==[moved/'dataset/AutoMR/run_001']


def test_ligand_source_chemistry_and_metal_state_defaults_do_not_guess_targets():
    from importlib.resources import files
    from nasolve.metal.chemistry import dictionaries,coordination_context
    from nasolve.metal.recipe import canonical
    source=dictionaries([('DF.cif',files('nasolve').joinpath('data/ligands/DF.cif').read_bytes())])
    captured=copy.deepcopy(source);captured['DF']['bond_orders'][canonical(['C2','S1'])]='SINGLE'
    nodes=[dict(node_id='s',kind='donor',atom=dict(element='S',key=dict(component_id='DF',atom_name='S1')))]
    for i,e in enumerate(('Au','Ag','Hg','Ag','Ag')):nodes.append(dict(node_id='m'+str(i),kind='metal',atom=dict(element=e,key={})))
    preview=dict(nodes=nodes,restraints=[dict(kind='distance',enabled=True,node_ids=['m3','m4'])])
    result=coordination_context(preview,captured)
    assert [m['oxidation_state'] for m in result['metals']]==['I','I','II','mixed-0-I','mixed-0-I']
    donor=result['donors'][0]
    assert donor['chemical_type']=='thione S' and donor['warnings']
    assert donor['suggested_distance_A'] is None
    assert result['metal_groups']==[['m3','m4']]
    assert all(m['coordination_number'] is None for m in result['metals'])


def test_identical_trial_ids_in_distinct_datasets_use_the_selected_mount(tmp_path,monkeypatch):
    import shutil
    run,request,mounts,_=setup(tmp_path/'first',monkeypatch)
    second=tmp_path/'second';shutil.copytree(mounts['one'],second)
    dataset=copy.deepcopy(request['datasets'][0]);dataset['dataset_id']='two';request['datasets'].append(dataset);mounts['two']=second
    viewer=open_viewer(capture_catalog(request,mounts),mounts);calls=[]
    monkeypatch.setattr(viewer.inspections,'_coot',lambda profile,*a:calls.append(profile['run']) or {})
    for dataset_id in ('one','two'):
        row=next(r for r in viewer.workbench.to_dict()['rows'] if r['dataset_id']==dataset_id)
        out=viewer.navigate(dict(action='row',selection=viewer.workbench.initial_selection(),row_id=row['row_id']))
        viewer.inspections.perform('coot',out['scene'],None)
    assert calls==[run,second/'AutoMR/run_001']
