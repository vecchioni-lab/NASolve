"""Bounded occupancy grids retain seed controls and immutable execution passes."""
import json
from pathlib import Path
import pytest
from nasolve.metal import RecipeError
from nasolve.metal.fdp_scan import create_plan, verify_plan, run_scan, verify_scan
from tests.test_metal_fdp import fake_execution
from nasolve.metal.fdp import run_fdp


def seed(tmp_path,monkeypatch):
    module,context,g,native=fake_execution(tmp_path,monkeypatch)
    run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'],occupancies={'m1':.6})
    import nasolve.metal.fdp_scan as scan
    monkeypatch.setattr(scan,'_check_native',lambda *a,**kw:None)
    return context.run,native


def test_budgeted_scan_reuses_seed_and_resumes_without_overwriting(tmp_path,monkeypatch):
    run,native=seed(tmp_path,monkeypatch)
    plan=create_plan(run,'Metal/fdp_001',{'m1':[.4,.6,.8]},max_trials=3)
    assert verify_plan(run,'Metal/fdp_scan_plan_001')==plan
    first=run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=1)
    report=json.loads((run/first['files']['report']['relative_path']).read_text())
    assert report['status']=='PARTIAL_REVIEW'
    assert [r['state'] for r in report['points']]==['EXECUTED','REUSED_SEED','PENDING']
    before={str(p.relative_to(run)):p.read_bytes() for p in run.rglob('*') if p.is_file()}
    second=run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=1,resume='Metal/fdp_scan_001')
    assert second['status']=='SCAN_REVIEW'
    assert verify_scan(run,'Metal/fdp_scan_002')==second
    assert all((run/name).read_bytes()==raw for name,raw in before.items())
    assert len(list((run/'Metal').glob('fdp_[0-9]*')))==3


def read_report(run,doc):
    return json.loads((run/doc['files']['report']['relative_path']).read_text())


@pytest.mark.parametrize('axes,limit',[
    ({},3),({'missing':[.4]},3),({'m1':[]},3),({'m1':[True]},3),
    ({'m1':[0.]},3),({'m1':[1e-11]},3),({'m1':[-.1]},3),({'m1':[1.1]},3),
    ({'m1':[.333]},3),({'m1':[float('nan')]},3),({'m1':[.4,.4]},3),
    ({'m1':[.4,.40000000001]},3),({'m1':[.4,.6,.8]},2),({'m1':[.4]},True),
    ({'m1':[.4]},129),({'m1':[.4]},0)])
def test_invalid_or_overbudget_grids_allocate_nothing(tmp_path,monkeypatch,axes,limit):
    run,native=seed(tmp_path,monkeypatch)
    with pytest.raises(RecipeError):create_plan(run,'Metal/fdp_001',axes,max_trials=limit)
    assert not list((run/'Metal').glob('fdp_scan_plan_*'))


def test_independent_axes_and_locked_sites_preserve_entire_q_vector(tmp_path,monkeypatch):
    from tests.test_metal_fdp_compare import trials
    context,paths=trials(tmp_path,monkeypatch,[dict(occupancies={'m1':.6,'m2':.8})],metals=('Au','Ag'))
    locked=create_plan(context.run,paths[0],{'m1':[.5,.7]},max_trials=2)
    assert locked['locked_occupancies']=={'m2':.8}
    assert [p['occupancies'] for p in locked['points']]==[{'m1':.5,'m2':.8},{'m1':.7,'m2':.8}]
    cartesian=create_plan(context.run,paths[0],{'m2':[.7,.8],'m1':[.5,.6]},max_trials=4)
    assert len(cartesian['points'])==4 and cartesian['locked_occupancies']=={}
    assert len({p['point_id'] for p in cartesian['points']})==4


@pytest.mark.parametrize('budget',[-1,True,129])
def test_invalid_execution_budget_allocates_nothing(tmp_path,monkeypatch,budget):
    run,native=seed(tmp_path,monkeypatch)
    create_plan(run,'Metal/fdp_001',{'m1':[.4,.6]},max_trials=2)
    with pytest.raises(RecipeError):run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=budget)
    assert not list((run/'Metal').glob('fdp_scan_[0-9]*'))


def test_zero_budget_and_completed_resume_need_no_native_installation(tmp_path,monkeypatch):
    import nasolve.metal.fdp_scan as m
    run,native=seed(tmp_path,monkeypatch)
    create_plan(run,'Metal/fdp_001',{'m1':[.4,.6]},max_trials=2)
    partial=run_scan(run,'Metal/fdp_scan_plan_001',job_budget=0)
    assert read_report(run,partial)['trial_attempts']==0
    run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=1,resume='Metal/fdp_scan_001')
    monkeypatch.setattr(m,'_check_native',lambda *a,**kw:pytest.fail('No identity probe needed'))
    monkeypatch.setattr(m,'run_fdp',lambda *a,**kw:pytest.fail('Completed trials must be reused'))
    complete=run_scan(run,'Metal/fdp_scan_plan_001',job_budget=4,resume='Metal/fdp_scan_002')
    report=read_report(run,complete)
    assert report['reused']==2 and report['trial_attempts']==0 and report['pending']==0
    assert verify_scan(run,'Metal/fdp_scan_003')==complete


@pytest.mark.parametrize('error',[RecipeError('Synthetic failed fit'),KeyboardInterrupt()])
def test_failed_trial_or_interrupt_preserves_completed_points_for_resume(tmp_path,monkeypatch,error):
    import nasolve.metal.fdp_scan as m
    run,native=seed(tmp_path,monkeypatch)
    create_plan(run,'Metal/fdp_001',{'m1':[.2,.4,.6,.8]},max_trials=4)
    actual=m.run_fdp;calls=[]
    def interrupted(*args,**kwargs):
        calls.append(kwargs['occupancies'])
        if len(calls)==2:raise error
        return actual(*args,**kwargs)
    monkeypatch.setattr(m,'run_fdp',interrupted)
    doc=run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=3)
    report=read_report(run,doc)
    assert report['new_completed']==1 and report['trial_attempts']==2 and report['pending']==2
    assert report['failure']['exception']==type(error).__name__
    assert verify_scan(run,'Metal/fdp_scan_001')==doc
    monkeypatch.setattr(m,'run_fdp',actual)
    result=run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=2,resume='Metal/fdp_scan_001')
    assert result['status']=='SCAN_REVIEW'
    assert read_report(run,result)['new_completed']==2


def test_resume_requires_same_plan_and_still_valid_seed(tmp_path,monkeypatch):
    run,native=seed(tmp_path,monkeypatch)
    create_plan(run,'Metal/fdp_001',{'m1':[.4,.6]},max_trials=2)
    run_scan(run,'Metal/fdp_scan_plan_001',job_budget=0)
    create_plan(run,'Metal/fdp_001',{'m1':[.4,.6]},max_trials=2)
    with pytest.raises(RecipeError,match='identical scan plan'):
        run_scan(run,'Metal/fdp_scan_plan_002',native=native,job_budget=1,resume='Metal/fdp_scan_001')
    (run/'Metal/fdp_001/input.pdb').write_text('changed')
    with pytest.raises(RecipeError):verify_scan(run,'Metal/fdp_scan_001')


@pytest.mark.parametrize('target',['report','receipt','manifest','plan','extra','symlink'])
def test_tampering_even_with_rehashed_report_is_rejected(tmp_path,monkeypatch,target):
    from nasolve.metal.context import _reference
    from nasolve.metal.materialize import _json_bytes
    from nasolve.metal.recipe import digest
    run,native=seed(tmp_path,monkeypatch)
    create_plan(run,'Metal/fdp_001',{'m1':[.4,.6]},max_trials=2)
    doc=run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=1)
    directory=run/'Metal/fdp_scan_001'
    if target in {'report','receipt'}:
        key='report' if target=='report' else 'point_001'
        p=run/doc['files'][key]['relative_path'];data=json.loads(p.read_text())
        if target=='report':data['points'][0]['sites'][0]['f_double_prime']=999
        else:data['point_id']='a'*64
        p.write_bytes(_json_bytes(data));doc['files'][key]=_reference(p,run)
    elif target=='manifest':doc['automatic_checkpoint_selection']=True
    elif target=='plan':
        p=run/'Metal/fdp_scan_plan_001/plan.json';p.write_text(p.read_text()+'\n')
    elif target=='extra':(directory/'unexpected.txt').write_text('extra')
    else:
        (directory/'point_001.json').unlink();(directory/'point_001.json').symlink_to(directory/'report.json')
    doc.pop('scan_id');doc['scan_id']=digest(doc)
    (directory/'manifest.json').write_bytes(_json_bytes(doc))
    with pytest.raises(RecipeError):verify_scan(run,directory)


def test_incompatible_trial_stops_without_becoming_completed_result(tmp_path,monkeypatch):
    import nasolve.metal.fdp_scan as m
    run,native=seed(tmp_path,monkeypatch)
    create_plan(run,'Metal/fdp_001',{'m1':[.4]},max_trials=1)
    actual=m.run_fdp
    def changed(*args,**kwargs):
        kwargs['start_fdp']=10
        return actual(*args,**kwargs)
    monkeypatch.setattr(m,'run_fdp',changed)
    doc=run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=1)
    assert read_report(run,doc)['new_completed']==0
    assert read_report(run,doc)['stopping']=='EXECUTION_ERROR'
    assert verify_scan(run,'Metal/fdp_scan_001')==doc


@pytest.mark.parametrize('mismatch',['version','kernels','worker'])
def test_native_identity_mismatch_stops_before_allocating_scan(tmp_path,monkeypatch,mismatch):
    from types import SimpleNamespace
    import nasolve.metal.fdp_scan as m
    check=m._check_native
    run,native=seed(tmp_path,monkeypatch)
    monkeypatch.setattr(m,'_check_native',check)
    create_plan(run,'Metal/fdp_001',{'m1':[.4]},max_trials=1)
    loaded=m._load_trial(run,'Metal/fdp_001')
    response={'version':loaded['basis']['native_version'],'hashes':loaded['basis']['native_source_hashes']}
    if mismatch=='version':response['version']='changed'
    elif mismatch=='kernels':response['hashes']={}
    else:
        original=m._inputs
        def different(*a,**kw):
            data=original(*a,**kw);data[2]['basis']['worker_sha256']='0'*64;return data
        monkeypatch.setattr(m,'_inputs',different)
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=0,stdout=json.dumps(response),stderr=''))
    with pytest.raises(RecipeError):run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=1)
    assert not list((run/'Metal').glob('fdp_scan_[0-9]*'))


def test_relocated_completed_scan_replays_offline_after_original_root_removed(tmp_path,monkeypatch):
    import os,shutil,subprocess,sys
    original=tmp_path/'original';original.mkdir()
    run,native=seed(original,monkeypatch)
    create_plan(run,'Metal/fdp_001',{'m1':[.4,.6,.8]},max_trials=3)
    run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=1)
    doc=run_scan(run,'Metal/fdp_scan_plan_001',native=native,job_budget=1,resume='Metal/fdp_scan_001')
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',original/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved=tmp_path/'moved';original.rename(moved);assert not original.exists()
    code="""import sys,subprocess
from pathlib import Path
import nasolve.metal.fdp_scan as m
assert Path(m.__file__).is_relative_to(Path(sys.argv[1]))
def forbidden(*a,**kw):raise AssertionError('No native execution during replay')
subprocess.run=forbidden
print(m.verify_scan(sys.argv[2],'Metal/fdp_scan_002')['scan_id'])
"""
    done=subprocess.run([sys.executable,'-B','-c',code,str(moved/'src'),str(moved/'dataset/AutoMR/run_001')],cwd=moved,
                        env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
    assert done.returncode==0,done.stderr
    assert done.stdout.strip()==doc['scan_id']


def test_cli_plan_pause_and_verify_are_offline_and_json_is_stable(tmp_path,monkeypatch,capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    import nasolve.metal.cli as cli
    run,native=seed(tmp_path,monkeypatch)
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**kw:pytest.fail('No native discovery'))
    parser=build_parser()
    assert execute(parser.parse_args(['metal','plan-fdp-scan',str(run),'--seed','Metal/fdp_001','--occupancies','m1=.4,.6','--max-trials','2']))==0
    assert 'Plan: ' in capsys.readouterr().out
    assert execute(parser.parse_args(['metal','run-fdp-scan',str(run),'--plan','Metal/fdp_scan_plan_001','--job-budget','0','--json']))==0
    doc=json.loads(capsys.readouterr().out)
    assert doc['status']=='PARTIAL_REVIEW'
    assert execute(parser.parse_args(['metal','verify-fdp-scan',str(run),'--scan','Metal/fdp_scan_001','--json']))==0
    assert json.loads(capsys.readouterr().out)==doc
