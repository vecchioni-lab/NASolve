"""Offline navigation must never mix scientific parents or mutate their artifacts."""
import copy
import json
from pathlib import Path
import pytest

from nasolve.metal import RecipeError
from nasolve.metal.context import parse_pdb
from nasolve.metal.fdp_compare import build_comparison
from nasolve.metal.workbench import capture_catalog, open_workbench
from tests.test_metal_fdp_compare import trials


def fixture(tmp_path, monkeypatch):
    context, paths = trials(tmp_path, monkeypatch, metals=('Au', 'Ag'))
    build_comparison(context.run, paths)
    atoms = [a.key.to_dict() for a in parse_pdb((context.run/'Metal/geometry_001/model.pdb').read_bytes()).snapshot.atoms]
    hypothesis = dict(hypothesis_id='mixed', label='Mixed candidate',
        geometry=dict(anchor='run', relative_path='Metal/geometry_001/manifest.json'),
        sites=[dict(site_id='pair', label='Pair', atoms=atoms[-2:]),
               dict(site_id='neighbor', label='Neighbor', atoms=[atoms[-1], atoms[2]])],
        results=[dict(result_id='profile', label='Profile', kind='fdp-comparison',
            manifest=dict(anchor='run', relative_path='Metal/fdp_comparison_001/manifest.json'))])
    structure = dict(structure_id='model', label='Prepared scaffold',
        run=dict(anchor='dataset', relative_path='AutoMR/run_001'), hypotheses=[hypothesis])
    request = dict(kind='metal-workbench-request', schema_version=1, campaign_id='controls', label='Controls',
        datasets=[dict(dataset_id='one', label='First crystal', structures=[structure])])
    return context.run, request, {'one': context.run.parent.parent}


def test_navigation_is_scoped_and_row_selection_links_all_parents(tmp_path, monkeypatch):
    run, request, mounts = fixture(tmp_path, monkeypatch)
    before = {p:p.read_bytes() for p in run.rglob('*') if p.is_file()}
    catalog = capture_catalog(request, mounts)
    workbench = open_workbench(catalog, mounts)
    initial = workbench.initial_selection()
    row = workbench.to_dict()['rows'][1]
    selected = workbench.select_row(initial, row['row_id'], site_id='neighbor')
    assert selected['dataset_id']=='one' and selected['hypothesis_id']=='mixed'
    assert selected['site_id']=='neighbor' and selected['result_id']=='profile'
    assert workbench.view(selected)['rows'][0]['data']['node_id']=='m2'
    cleared = workbench.select(selected, 'hypothesis_id', None)
    assert all(cleared[k] is None for k in ('hypothesis_id','site_id','result_id','row_id'))
    assert initial['dataset_id'] is None
    assert all(p.read_bytes()==raw for p, raw in before.items())


def test_overlapping_sites_do_not_duplicate_or_filter_unassigned_results(tmp_path, monkeypatch):
    run, request, mounts = fixture(tmp_path, monkeypatch)
    wb = open_workbench(capture_catalog(request,mounts), mounts)
    rows = wb.to_dict()['rows']
    assert len(rows)==8 and len({r['row_id'] for r in rows})==8
    assert rows[1]['site_ids']==['pair','neighbor']
    selection=wb.select_row(wb.initial_selection(),rows[1]['row_id'])
    assert selection['site_id'] is None  # Do not invent one of two valid memberships.
    request['datasets'][0]['structures'][0]['hypotheses'][0]['sites']=[]
    no_sites=open_workbench(capture_catalog(request,mounts),mounts)
    assert len(no_sites.to_dict()['rows'])==8
    assert all(r['site_ids']==[] for r in no_sites.to_dict()['rows'])


def test_catalog_and_selection_are_snapshots_with_no_shared_mutable_state(tmp_path, monkeypatch):
    run, request, mounts = fixture(tmp_path, monkeypatch)
    catalog = capture_catalog(request,mounts)
    wb = open_workbench(catalog,mounts)
    original=wb.to_dict()
    catalog['datasets'].clear()
    exposed=wb.to_dict();exposed['rows'].clear()
    assert wb.to_dict()==original
    selected=wb.select(wb.initial_selection(),'dataset_id','one')
    selected['camera']={'zoom':2}
    with pytest.raises(RecipeError):wb.view(selected)


def test_tampered_sources_or_catalog_fail_closed(tmp_path, monkeypatch):
    run, request, mounts = fixture(tmp_path, monkeypatch)
    catalog = capture_catalog(request,mounts)
    changed=copy.deepcopy(catalog);changed['datasets'][0]['label']='Changed'
    with pytest.raises(RecipeError):open_workbench(changed,mounts)
    (run/'Metal/fdp_comparison_001/report.json').write_text('{}')
    with pytest.raises(RecipeError):open_workbench(catalog,mounts)


def test_state_from_other_catalog_is_rejected(tmp_path, monkeypatch):
    run, request, mounts = fixture(tmp_path, monkeypatch)
    wb = open_workbench(capture_catalog(request,mounts),mounts)
    state=wb.initial_selection()
    request['label']='Revised campaign'
    other=open_workbench(capture_catalog(request,mounts),mounts)
    with pytest.raises(RecipeError):other.view(state)


def test_two_datasets_keep_colliding_local_ids_distinct_and_clear_children(tmp_path,monkeypatch):
    first, request, mounts = fixture(tmp_path/'first',monkeypatch)
    import shutil
    second=tmp_path/'second/dataset'
    shutil.copytree(mounts['one'],second)
    dataset=copy.deepcopy(request['datasets'][0]);dataset['dataset_id']='two'
    request['datasets'].append(dataset);mounts['two']=second
    wb=open_workbench(capture_catalog(request,mounts),mounts)
    rows=wb.to_dict()['rows']
    assert len(rows)==16 and len({r['row_id'] for r in rows})==16
    selected=wb.select_row(wb.initial_selection(),rows[0]['row_id'])
    changed=wb.select(selected,'dataset_id','two')
    assert all(changed[k] is None for k in ('structure_id','hypothesis_id','site_id','result_id','row_id'))
    assert len(wb.view(changed)['rows'])==8
    moved=wb.select_row(selected,rows[-1]['row_id'])
    assert moved['dataset_id']=='two' and moved['site_id'] is None
    assert rows[0]['data']==rows[8]['data']  # Dataset identity still prevents collision.


@pytest.mark.parametrize('change', ['duplicate-dataset','duplicate-site','missing-atom','duplicate-atom',
    'unknown-field','absolute','escape','windows','non-normalized','wrong-anchor','bad-version',
    'unknown-kind','missing-mount','extra-mount','symlink'])
def test_invalid_catalog_input_is_rejected_before_any_write(tmp_path,monkeypatch,change):
    run, request, mounts=fixture(tmp_path,monkeypatch)
    structure=request['datasets'][0]['structures'][0];hypothesis=structure['hypotheses'][0]
    if change=='duplicate-dataset':request['datasets'].append(copy.deepcopy(request['datasets'][0]))
    if change=='duplicate-site':hypothesis['sites'].append(copy.deepcopy(hypothesis['sites'][0]))
    if change=='missing-atom':hypothesis['sites'][0]['atoms'][0]['residue_id']='999'
    if change=='duplicate-atom':hypothesis['sites'][0]['atoms']*=2
    if change=='unknown-field':request['camera']={}
    if change=='absolute':hypothesis['geometry']['relative_path']=str(run/'Metal/geometry_001/manifest.json')
    if change=='escape':structure['run']['relative_path']='../dataset/AutoMR/run_001'
    if change=='windows':structure['run']['relative_path']='C:\\AutoMR\\run_001'
    if change=='non-normalized':structure['run']['relative_path']='AutoMR//run_001'
    if change=='wrong-anchor':structure['run']['anchor']='run'
    if change=='bad-version':request['schema_version']=True
    if change=='unknown-kind':hypothesis['results'][0]['kind']='inferred-best-model'
    if change=='missing-mount':mounts={}
    if change=='extra-mount':mounts['extra']=tmp_path
    if change=='symlink':
        (run/'Metal/link').symlink_to(run/'Metal/geometry_001',target_is_directory=True)
        hypothesis['geometry']['relative_path']='Metal/link/manifest.json'
    before={p:p.read_bytes() for p in run.rglob('*') if p.is_file()}
    with pytest.raises(RecipeError):capture_catalog(request,mounts)
    assert all(p.read_bytes()==raw for p,raw in before.items())


def test_result_from_another_geometry_is_rejected(tmp_path,monkeypatch):
    from nasolve.metal.geometry import prepare_geometry
    run,request,mounts=fixture(tmp_path,monkeypatch)
    prepare_geometry(run,'Metal/hypothesis_001',max_shift_A=.5)
    request['datasets'][0]['structures'][0]['hypotheses'][0]['geometry']['relative_path']='Metal/geometry_002/manifest.json'
    with pytest.raises(RecipeError,match='different geometry'):capture_catalog(request,mounts)


def test_scan_pending_points_and_provenance_remain_visible_without_jobs(tmp_path,monkeypatch):
    import subprocess
    from nasolve.metal.fdp_scan import create_plan,run_scan
    run,request,mounts=fixture(tmp_path,monkeypatch)
    create_plan(run,'Metal/fdp_001',{'m1':[.4,.6,.8]},max_trials=3)
    scan=run_scan(run,'Metal/fdp_scan_plan_001',job_budget=0)
    h=request['datasets'][0]['structures'][0]['hypotheses'][0]
    h['results']=[dict(result_id='scan',label='Scan',kind='fdp-scan',
        manifest=dict(anchor='run',relative_path='Metal/fdp_scan_001/manifest.json'))]
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw:pytest.fail('Workbench must stay offline'))
    wb=open_workbench(capture_catalog(request,mounts),mounts)
    view=wb.view(wb.initial_selection())
    assert len(view['rows'])==2
    report=view['details'][1]['report']
    assert report['pending']==2 and report['trial_attempts']==0
    assert report==json.loads((run/scan['files']['report']['relative_path']).read_text())
    assert all(r['data']['state']=='REUSED_SEED' for r in view['rows'])


def test_reference_report_is_preserved_with_unmapped_scatterers(tmp_path,monkeypatch):
    from tests.test_metal_reference import setup
    from nasolve.metal.reference import compare_reference
    run,request,mounts=fixture(tmp_path/'fdp',monkeypatch)
    context,g,reference,plan=setup(tmp_path/'reference')
    doc=compare_reference(context.run,'Metal/geometry_001',reference,plan)
    mounts['one']=context.run.parent.parent
    h=request['datasets'][0]['structures'][0]['hypotheses'][0]
    h['sites']=[]
    h['results']=[dict(result_id='human',label='Human snapshot',kind='reference-comparison',
        manifest=dict(anchor='run',relative_path='Metal/reference_comparison_001/manifest.json'))]
    wb=open_workbench(capture_catalog(request,mounts),mounts)
    report=wb.to_dict()['details'][1]['report']
    assert report==json.loads((context.run/doc['files']['report']['relative_path']).read_text())
    assert report['unmapped_reference_atoms_of_interest']
    assert report['stored_anomalous_parameters']=='UNTRUSTED_IGNORED'
    assert all('f_double_prime' not in r['data'] for r in wb.to_dict()['rows'])


def test_selection_validation_and_result_site_sibling_behavior(tmp_path,monkeypatch):
    run,request,mounts=fixture(tmp_path,monkeypatch)
    wb=open_workbench(capture_catalog(request,mounts),mounts)
    row=wb.to_dict()['rows'][0]
    state=wb.select_row(wb.initial_selection(),row['row_id'])
    assert state['site_id']=='pair'
    changed=wb.select(state,'site_id','neighbor')
    assert changed['result_id']=='profile' and changed['row_id'] is None
    assert len(wb.view(changed)['rows'])==4
    assert wb.select(state,'dataset_id','one')==state
    for bad in (dict(state,result_id=None),dict(state,site_id='neighbor'),dict(state,structure_id='wrong'),
                dict(state,row_id='unknown'),dict(state,schema_version=True),dict(state,dataset_id=7)):
        with pytest.raises(RecipeError):wb.view(bad)
    with pytest.raises(RecipeError):wb.select_row(state,row['row_id'],site_id='neighbor')
    with pytest.raises(RecipeError):wb.select_row(state,'unknown')
    with pytest.raises(RecipeError):wb.select(state,'row_id',row['row_id'])


def test_catalog_replays_after_source_tree_move_in_fresh_interpreter(tmp_path,monkeypatch):
    import os,shutil,subprocess,sys
    original=tmp_path/'original'
    run,request,mounts=fixture(original,monkeypatch)
    catalog=capture_catalog(request,mounts)
    before=open_workbench(catalog,mounts).to_dict()
    (original/'catalog.json').write_text(json.dumps(catalog))
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',original/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved=tmp_path/'moved';original.rename(moved);assert not original.exists()
    code='''import json,sys,subprocess
from pathlib import Path
import nasolve.metal.workbench as m
assert Path(m.__file__).is_relative_to(Path(sys.argv[1]))
def forbidden(*a,**kw):raise AssertionError('No native work during navigation')
subprocess.run=forbidden
catalog=json.loads(Path('catalog.json').read_text())
wb=m.open_workbench(catalog,{'one':Path('dataset')})
row=wb.to_dict()['rows'][0]
assert wb.view(wb.select_row(wb.initial_selection(),row['row_id']))['selected_row']==row
print(json.dumps(wb.to_dict(),sort_keys=True))
'''
    done=subprocess.run([sys.executable,'-B','-c',code,str(moved/'src')],cwd=moved,
        env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
    assert done.returncode==0,done.stderr
    assert json.loads(done.stdout)==before
    assert str(original) not in json.dumps(catalog)


def test_cli_capture_and_linked_row_are_offline_and_never_overwrite(tmp_path,monkeypatch,capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    import nasolve.metal.cli as cli
    run,request,mounts=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**kw:pytest.fail('No native discovery'))
    request_file=tmp_path/'request.json';request_file.write_text(json.dumps(request))
    output=tmp_path/'catalog.json'
    parser=build_parser();mount='one='+str(mounts['one'])
    args=parser.parse_args(['metal','capture-workbench','--request',str(request_file),'--dataset',mount,'--output',str(output),'--json'])
    assert execute(args)==0
    assert json.loads(capsys.readouterr().out)==json.loads(output.read_text())
    assert execute(args)==2
    assert 'new files' in capsys.readouterr().err
    wb=open_workbench(json.loads(output.read_text()),mounts);row=wb.to_dict()['rows'][1]
    args=parser.parse_args(['metal','inspect-workbench','--catalog',str(output),'--dataset',mount,
                            '--row',row['row_id'],'--site','neighbor','--json'])
    assert execute(args)==0
    result=json.loads(capsys.readouterr().out)
    assert result['selected_row']==row and result['selection']['site_id']=='neighbor'
    args.json=False
    assert execute(args)==0
    assert 'No jobs' in capsys.readouterr().out
    args.dataset += [mount]
    assert execute(args)==2 and 'distinct' in capsys.readouterr().err


def test_dataset_mount_must_match_existing_run_context_anchor(tmp_path,monkeypatch):
    run,request,mounts=fixture(tmp_path,monkeypatch)
    request['datasets'][0]['structures'][0]['run']['relative_path']='dataset/AutoMR/run_001'
    with pytest.raises(RecipeError,match='dataset root'):
        capture_catalog(request,{'one':tmp_path})


def test_switching_structures_and_hypotheses_clears_prior_result_scope(tmp_path,monkeypatch):
    run,request,mounts=fixture(tmp_path,monkeypatch)
    structures=request['datasets'][0]['structures']
    alternate=copy.deepcopy(structures[0]['hypotheses'][0]);alternate['hypothesis_id']='alternative'
    structures[0]['hypotheses'].append(alternate)
    structures.append(copy.deepcopy(structures[0]));structures[1]['structure_id']='second-scaffold'
    wb=open_workbench(capture_catalog(request,mounts),mounts)
    first=wb.to_dict()['rows'][0]
    selected=wb.select_row(wb.initial_selection(),first['row_id'])
    changed=wb.select(selected,'hypothesis_id','alternative')
    assert changed['site_id'] is None and changed['result_id'] is None and changed['row_id'] is None
    assert all(r['hypothesis_id']=='alternative' for r in wb.view(changed)['rows'])
    changed=wb.select(changed,'structure_id','second-scaffold')
    assert changed['hypothesis_id'] is None
    row=wb.view(changed)['rows'][-1]
    assert wb.select_row(selected,row['row_id'])['structure_id']=='second-scaffold'
