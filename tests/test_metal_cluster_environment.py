"""Declared cluster B environments are fixed inputs, independent of view scope."""
import copy
import json
from pathlib import Path
import pytest
from nasolve.metal import RecipeError
from nasolve.metal.environment import calibrate_b
from nasolve.metal.context import parse_pdb
from tests.test_metal_b_environment import inputs
from tests.test_metal_materialize import atom


def cluster():
    raw, sites, preview = inputs()
    for i in range(2,7):
        raw += atom(10+i,'AG','AG','M',i,(i,2,1),'Ag',b=25).encode()
        key = parse_pdb(raw).snapshot.atoms[-1].key.to_dict()
        sites.append(dict(node_id=f'm{i}',key=key))
        preview['nodes'].append(dict(node_id=f'm{i}',kind='metal',atom=dict(key=key)))
        preview['restraints'].append(dict(kind='distance',enabled=True,status='resolved',node_ids=['m1',f'm{i}']))
    names=[s['node_id'] for s in sites]
    groups={'cluster':dict(metal_nodes=names,donor_nodes=['a','b'])}
    return raw,sites,preview,names,groups


def test_interior_members_share_explicit_base_means_without_changing_xyz_q_or_ligands():
    raw,sites,preview,names,groups=cluster()
    before=copy.deepcopy(groups)
    report,model=calibrate_b(raw,sites,preview,names,'base-mean',environments=groups)
    assert groups==before
    assert report['protocol']=='metal-environment-b-v2'
    assert report['environments']==groups
    assert {s['applied_b_A2'] for s in report['sites']}=={275}
    assert all(s['base_means_A2']==[200,350] and s['environment_id']=='cluster' for s in report['sites'])
    a,b=parse_pdb(raw),parse_pdb(model)
    assert a.snapshot.atoms==b.snapshot.atoms
    for old,new in zip(a.to_dict()['atomic_state'],b.to_dict()['atomic_state']):
        assert dict(old,b_iso=new['b_iso'])==new
    assert a.to_dict()['atomic_state'][:7]==b.to_dict()['atomic_state'][:7]
    with pytest.raises(RecipeError,match='No connected ligand'):
        calibrate_b(raw,sites,preview,names,'base-mean')


def test_explicit_donors_need_no_geometric_edges_and_aliases_do_not_reweight():
    raw,sites,preview,names,groups=cluster()
    preview['restraints']=[]
    preview['nodes'].append(dict(preview['nodes'][0],node_id='alias'))
    groups['cluster']['donor_nodes'].append('alias')
    report,_=calibrate_b(raw,sites,preview,names,'donor-mean',environments=groups)
    assert all(s['applied_b_A2']==235 and len(s['atoms'])==2 for s in report['sites'])


@pytest.mark.parametrize('change', ['empty','unknown_field','unknown_donor','metal_as_donor','unknown_metal',
                                  'duplicate_metal','duplicate_donor','overlap','unfitted','unresolved','wrong_identity','keep'])
def test_invalid_or_ambiguous_environments_fail(change):
    raw,sites,preview,names,groups=cluster();policy='base-mean'
    if change=='empty':groups={}
    elif change=='unknown_field':groups['cluster']['radius']=5
    elif change=='unknown_donor':groups['cluster']['donor_nodes']=['missing']
    elif change=='metal_as_donor':groups['cluster']['donor_nodes']=['m1']
    elif change=='unknown_metal':groups['cluster']['metal_nodes']=['absent']
    elif change=='duplicate_metal':groups['cluster']['metal_nodes']+=['m1']
    elif change=='duplicate_donor':groups['cluster']['donor_nodes']+=['a']
    elif change=='overlap':groups['other']=copy.deepcopy(groups['cluster'])
    elif change=='unfitted':names=['m1']
    elif change=='unresolved':preview['nodes'][0]['atom']=None
    elif change=='wrong_identity':preview['nodes'][0]['atom']['key']['altloc']='B'
    elif change=='keep':policy='keep'
    with pytest.raises(RecipeError):calibrate_b(raw,sites,preview,names,policy,environments=groups)


def test_unassigned_metals_keep_direct_donors_and_no_implicit_cluster_traversal():
    raw,sites,preview,names,groups=cluster()
    groups['cluster']['metal_nodes']=names[1:]
    groups['cluster']['donor_nodes']=['a']
    report,_=calibrate_b(raw,sites,preview,names,'base-mean',environments=groups)
    assert report['sites'][0]['applied_b_A2']==275
    assert 'environment_id' not in report['sites'][0]
    assert all(s['applied_b_A2']==200 for s in report['sites'][1:])


def test_shared_b_survives_xyz_scan_count_replay_and_changes_comparison_basis(tmp_path,monkeypatch):
    from tests.test_metal_fdp_endpoint import endpoint
    from nasolve.metal.fdp import run_fdp,verify_fdp
    from nasolve.metal import fdp_scan as scan
    from nasolve.metal.fdp_count import capture_count,verify_count
    from nasolve.metal.fdp_compare import build_comparison
    c,h,x,native=endpoint(tmp_path,monkeypatch)
    names=[f'm{i}' for i in range(1,7)]
    groups={'shell':dict(metal_nodes=list(reversed(names)),donor_nodes=['d2','d1'])}
    seed=run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=names,metal_b_policy='donor-mean',metal_b_environments=groups)
    p=json.loads((c.run/seed['files']['plan.json']['relative_path']).read_text())
    assert p['options']['metal_b_environments']['shell']['metal_nodes']==names
    scan.create_plan(c.run,'Metal/fdp_001',{'m1':[.5,.6]},max_trials=2)
    monkeypatch.setattr(scan,'_check_native',lambda *a,**kw:None)
    out=scan.run_scan(c.run,'Metal/fdp_scan_plan_001',native=native,job_budget=1)
    report=json.loads((c.run/out['files']['report']['relative_path']).read_text())
    assert report['new_completed']==1 and report['reused']==1
    assert all(s['b_iso']==260 and s['b_calibration']['environment_id']=='shell' for p in report['points'] for s in p['sites'])
    assert scan.verify_scan(c.run,'Metal/fdp_scan_001')==out
    count=capture_count(c.run,'Metal/fdp_001',{'cluster':dict(nodes=names,representation='explicit-sites')})
    assert verify_count(c.run,'Metal/fdp_count_001')==count
    assert verify_fdp(c.run,'Metal/fdp_001')==seed
    run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=names,metal_b_policy='donor-mean')
    with pytest.raises(RecipeError,match='same geometry'):
        build_comparison(c.run,['Metal/fdp_001','Metal/fdp_003'])
    path=c.run/'Metal/fdp_001/plan.json';p['options']['metal_b_environments']['shell']['donor_nodes']=['d1']
    path.write_text(json.dumps(p))
    with pytest.raises(RecipeError):verify_fdp(c.run,'Metal/fdp_001')


def test_shared_environment_replays_without_original_source_or_config_file(tmp_path,monkeypatch):
    import os,shutil,subprocess,sys
    from tests.test_metal_fdp_endpoint import endpoint
    from nasolve.metal.fdp import run_fdp
    old=tmp_path/'old';c,h,x,n=endpoint(old,monkeypatch)
    names=[f'm{i}' for i in range(1,7)]
    groups={'shell':dict(metal_nodes=names,donor_nodes=['d1','d2'])}
    doc=run_fdp(c.run,'Metal/xyz_001',native=n,fit_nodes=names,metal_b_policy='donor-mean',metal_b_environments=groups)
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',old/'src',ignore=shutil.ignore_patterns('__pycache__'))
    moved=tmp_path/'moved';old.rename(moved)
    code="from nasolve.metal.fdp import verify_fdp;print(verify_fdp('dataset/AutoMR/run_001','Metal/fdp_001')['trial_id'])"
    done=subprocess.run([sys.executable,'-B','-c',code],cwd=moved,env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
    assert done.returncode==0,done.stderr
    assert done.stdout.strip()==doc['trial_id'] and not old.exists()


def test_environment_requires_explicit_policy_and_cli_reads_file(tmp_path,monkeypatch,capsys):
    from tests.test_metal_fdp import prepared
    from nasolve.metal.fdp import make_plan
    c,g,p,model=prepared(tmp_path)
    with pytest.raises(RecipeError,match='B policy'):
        make_plan(model,[],p['metadata'],p['references'],fit_nodes=['m1'],metal_b_environments={})
    from nasolve.cli import build_parser
    args=build_parser().parse_args(['metal','fdp',str(c.run),'--xyz','Metal/xyz_001','--fit','m1','--metal-b-environments',str(tmp_path/'groups.json')])
    assert args.metal_b_environments==tmp_path/'groups.json'

    import nasolve.metal.cli as cli
    import nasolve.metal.fdp as fdp
    declared={'shell':dict(metal_nodes=['m1'],donor_nodes=['d1'])}
    args.metal_b_environments.write_text(json.dumps(declared));args.json=True
    monkeypatch.setattr(cli,'load_config',lambda:None)
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**kw:None)
    captured={}
    def fake(*a,**kw):captured.update(kw);return {'status':'CLI_TEST'}
    monkeypatch.setattr(fdp,'run_fdp',fake)
    assert cli._fdp(args)==0
    assert captured['metal_b_environments']==declared
