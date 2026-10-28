"""Freeze audits must reject a successful process that changed fixed science."""
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import pytest

from nasolve.metal import RecipeError
from nasolve.metal.fdp import make_plan, audit_result, audit_reflections, run_fdp, verify_fdp
from nasolve.metal.geometry import prepare_geometry
from nasolve.metal.materialize import build_hypothesis
from nasolve.metal.context import parse_pdb
from tests.test_metal_materialize import control


def prepared(tmp_path, metals=('Hg',)):
    context, recipe, placement = control(tmp_path, metals=metals)
    h = build_hypothesis(context, recipe, placement)
    g = prepare_geometry(context.run, Path(h['files']['model']['relative_path']).parent)
    raw = (context.run / g['files']['model']['relative_path']).read_bytes()
    refs = [{'element': e, 'f_prime': -.2, 'f_double_prime': 3., 'wavelength_A': 1.,
             'provider': 'cctbx-sasaki', 'phenix_version': '2.2.1', 'native_version': '2.2.1-6174',
             'table_sha256': '1'*64, 'f_prime_policy': 'fixed', 'refined': False}
            for e in sorted({a.element for a in parse_pdb(raw).snapshot.atoms})]
    meta = {'wavelength_A': 1., 'anomalous_labels': ['F(+)', 'SIGF(+)', 'F(-)', 'SIGF(-)'], 'free_r_label': 'FreeR_flag'}
    plan, model = make_plan(raw, h['sites'], meta, refs, fit_nodes=['m1'], occupancies={'m1': .4})
    return context, g, plan, model


def reflection_evidence(rows=None):
    from nasolve.metal.recipe import canonical
    if rows is None:rows=[[[1,0,0],12.,1.,False],[[2,0,0],20.,2.,True]]
    return dict(hash=hashlib.sha256(canonical(rows).encode()).hexdigest(),count=len(rows),
                anomalous=True,free_count=sum(x[3] for x in rows),rows=rows)


def native_result(plan, model):
    parsed = parse_pdb(model)
    atoms = []
    for i, (a, s) in enumerate(zip(parsed.snapshot.atoms, parsed.to_dict()['atomic_state'])):
        group = next(g for g in plan['groups'] if i in g['indices'])
        atoms.append(dict(key=a.key.to_dict(), element=a.element, xyz=list(a.xyz), occupancy=s['occupancy'],
                          b_iso=s['b_iso'], charge='',normal_scattering_type=a.element.upper(),u_cart=None, fp=group['f_prime'],
                          fdp=5. if group['refine_fdp'] else group['f_double_prime_start']))
    groups = [dict(g, f_double_prime=5. if g['refine_fdp'] else g['f_double_prime_start']) for g in plan['groups']]
    return {'protocol': plan['protocol'], 'completed': True, 'atoms': atoms, 'groups': groups,
            'policy': plan['policy'], 'reflection_before': reflection_evidence(),
            'reflection_after': reflection_evidence(),
            'r_work': .3, 'r_free': .4, 'native_version': '2.2.1-6174',
            'normal_scattering_before':[a['normal_scattering_type'] for a in atoms],
            'native_source_hashes':{name:'4'*64 for name in ['fp_fdp','bulk_scaling','anomalous_minimizer','xray_kernel','lbfgs_kernel']},
            'execution': 'complete', 'convergence': 'NOT_INDEPENDENTLY_ASSESSED'}


def test_plan_changes_only_requested_occupancy_and_accounts_for_iodine(tmp_path):
    context, g, plan, model = prepared(tmp_path)
    original = (context.run/g['files']['model']['relative_path']).read_bytes()
    a,b=parse_pdb(original),parse_pdb(model)
    assert a.snapshot.atoms == b.snapshot.atoms
    assert b.to_dict()['atomic_state'][-1]['occupancy']==.4
    assert a.to_dict()['atomic_state'][:-1]==b.to_dict()['atomic_state'][:-1]
    assert len([x for x in plan['groups'] if x['refine_fdp']])==1
    iodine=next(x for x in plan['groups'] if x['element']=='I')
    assert not iodine['refine_fdp'] and iodine['f_double_prime_start']==3.
    assert all(not g['refine_fp'] for g in plan['groups'])
    assert sorted(i for g in plan['groups'] for i in g['indices'])==list(range(4))


def test_audit_reports_fitted_values_separately_from_scientific_acceptance(tmp_path):
    _,_,plan,model=prepared(tmp_path)
    result=audit_result(plan,model,native_result(plan,model))
    assert result['status']=='FDP_REVIEW'
    assert result['freeze_audit']=='PASS'
    assert result['sites'][0]['f_double_prime']==5.
    assert result['sites'][0]['occupancy']==.4
    assert result['scientific_acceptance']=='NOT_ASSESSED'
    assert result['automatic_checkpoint_selection'] is False


@pytest.mark.parametrize('change',['xyz','occupancy','b_iso','fp','element','identity','missing_atom','fixed_fdp','group_indices','group_refine_fp','policy','reflections','nan','completion','charge','normal_type'])
def test_changed_fixed_state_or_evidence_rejects_native_success(tmp_path,change):
    _,_,plan,model=prepared(tmp_path)
    evidence=native_result(plan,model)
    if change in ['occupancy','b_iso','fp']: evidence['atoms'][0][change]+=.1
    elif change=='xyz':evidence['atoms'][0]['xyz'][0]+=.01
    elif change=='element':evidence['atoms'][0]['element']='O'
    elif change=='identity':evidence['atoms'][0]['key']['residue_id']='99'
    elif change=='missing_atom':evidence['atoms'].pop()
    elif change=='fixed_fdp':evidence['atoms'][0]['fdp']+=.1
    elif change=='group_indices':evidence['groups'][0]['indices']=[0,1]
    elif change=='group_refine_fp':evidence['groups'][0]['refine_fp']=True
    elif change=='policy':evidence['policy']=dict(plan['policy'],strategy=['individual_sites'])
    elif change=='reflections':evidence['reflection_after']['hash']='3'*64
    elif change=='nan':evidence['atoms'][-1]['fdp']=float('nan')
    elif change=='completion':evidence['completed']=False
    elif change=='charge':evidence['atoms'][0]['charge']='1+'
    elif change=='normal_type':evidence['atoms'][0]['normal_scattering_type']='S1-'
    with pytest.raises(RecipeError):audit_result(plan,model,evidence)


def fake_execution(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import nasolve.metal.fdp as module
    context,g,plan,_=prepared(tmp_path)
    monkeypatch.setattr(module,'inspect_observations',lambda *a,**kw:plan['metadata'])
    monkeypatch.setattr(module,'reference_scattering',lambda *a,**kw:plan['references'])
    monkeypatch.setattr(module,'audit_free_r_flags',lambda *a,**kw:SimpleNamespace(status='VALID',valid=True,details={},warnings=()))
    def fake(directory,native,timeout):
        plan=json.loads((directory/'plan.json').read_text());model=(directory/'input.pdb').read_bytes()
        result=native_result(plan,model)
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(result).encode(),mtime=0))
        (directory/'final.pdb').write_bytes(model)
        (directory/'native.log').write_text('Synthetic protocol control; no native fit\n')
        return result
    monkeypatch.setattr(module,'_native',fake)
    native=SimpleNamespace(version='2.2.1',executables={'phenix.python':'unused','phenix.mtz.dump':'unused'},environment={})
    return module,context,g,native


def test_trial_preserves_parents_and_replays_without_native_execution(tmp_path,monkeypatch):
    module,context,g,native=fake_execution(tmp_path,monkeypatch)
    before={str(p.relative_to(context.run)):p.read_bytes() for p in context.run.rglob('*') if p.is_file()}
    doc=run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'],occupancies={'m1':.4})
    directory=context.run/Path(doc['files']['result.json']['relative_path']).parent
    monkeypatch.setattr(module,'_native',lambda *a,**kw:pytest.fail('Verification must not run native code'))
    assert verify_fdp(context.run,directory)==doc
    assert all((context.run/name).read_bytes()==data for name,data in before.items())
    assert not (context.run/'AutoRefine').exists()
    assert doc['files']['input.pdb']['anchor']=='run'
    assert str(context.run) not in (directory/'parameters.phil').read_text()
    assert 'target = "ml"' in (directory/'parameters.phil').read_text()


@pytest.mark.parametrize('field,value',[('fit_nodes',[]),('fit_nodes',['m1','m1']),('fit_nodes',['bad']),
    ('occupancies',{'m1':0}),('occupancies',{'m1':.123}),('occupancies',{'bad':.5}),
    ('cycles',True),('cycles',0),('max_iterations',101),('start_fdp',float('nan')),('free_r_test_value',-1)])
def test_invalid_plan_never_allocates_or_launches_a_trial(tmp_path,monkeypatch,field,value):
    module,context,g,native=fake_execution(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'_native',lambda *a,**kw:pytest.fail('Invalid plan launched'))
    kwargs={'fit_nodes':['m1'],field:value}
    with pytest.raises(RecipeError):run_fdp(context.run,'Metal/geometry_001',native=native,**kwargs)
    assert not list((context.run/'Metal').glob('fdp_*'))


def test_failure_is_retained_and_next_attempt_gets_a_new_number(tmp_path,monkeypatch):
    module,context,g,native=fake_execution(tmp_path,monkeypatch)
    original=module._native
    def broken(*a,**kw):raise RecipeError('Native test failure')
    monkeypatch.setattr(module,'_native',broken)
    with pytest.raises(RecipeError,match='test failure'):run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'])
    failed=context.run/'Metal/fdp_001'
    assert (failed/'failure.json').is_file() and not (failed/'manifest.json').exists()
    monkeypatch.setattr(module,'_native',original)
    doc=run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'])
    assert 'fdp_002' in doc['files']['result.json']['relative_path']
    assert verify_fdp(context.run,'Metal/fdp_002')==doc


@pytest.mark.parametrize('target',['input.pdb','final.pdb','native-result.json.gz','result.json','free-r.json','manifest.json'])
def test_rehashed_or_changed_payloads_cannot_bypass_derivation_and_audit(tmp_path,monkeypatch,target):
    from nasolve.metal.context import _reference
    from nasolve.metal.recipe import digest
    module,context,g,native=fake_execution(tmp_path,monkeypatch)
    doc=run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'])
    d=context.run/'Metal/fdp_001';p=d/target
    if target=='manifest.json':doc['automatic_checkpoint_selection']=True
    elif target in {'input.pdb','final.pdb'}:
        text=p.read_text();lines=text.splitlines(keepends=True)
        index=next(i for i,line in enumerate(lines) if line.startswith('HETATM'))
        lines[index]=lines[index][:60]+' 99.00'+lines[index][66:]
        changed=''.join(lines);assert changed!=text;p.write_text(changed)
    else:
        value=json.loads(gzip.decompress(p.read_bytes()) if target.endswith('.gz') else p.read_text())
        if target=='native-result.json.gz':value['atoms'][0]['occupancy']+=.1
        elif target=='result.json':value['freeze_audit']='INVALID'
        elif target=='free-r.json':value['usable']=False
        p.write_bytes(gzip.compress(json.dumps(value).encode(),mtime=0) if target.endswith('.gz') else json.dumps(value).encode())
    if target!='manifest.json':doc['files'][target]=_reference(p,context.run)
    doc.pop('trial_id');doc['trial_id']=digest(doc)
    (d/'manifest.json').write_text(json.dumps(doc))
    with pytest.raises(RecipeError):verify_fdp(context.run,d)


def test_fixed_same_element_neighbor_is_not_absorbed_into_fitted_group(tmp_path):
    _,_,plan,model=prepared(tmp_path,metals=('Hg','Hg'))
    fitted=next(g for g in plan['groups'] if g['id']=='m1')
    background=next(g for g in plan['groups'] if g['id']=='background:Hg')
    assert fitted['indices']==[3] and background['indices']==[4]
    assert not set(fitted['indices'])&set(background['indices'])
    report=audit_result(plan,model,native_result(plan,model))
    assert [s['node_id'] for s in report['sites']]==['m1']


def test_relocated_trial_replays_in_fresh_interpreter_after_original_is_gone(tmp_path,monkeypatch):
    import os,shutil,subprocess,sys
    original=tmp_path/'original';original.mkdir()
    module,context,g,native=fake_execution(original,monkeypatch)
    doc=run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'])
    source=Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source,original/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved=tmp_path/'moved';original.rename(moved)
    assert not original.exists()
    relocated_run=moved/'dataset/AutoMR/run_001'
    code="""import json,subprocess,sys
from pathlib import Path
import nasolve.metal.fdp as m
assert str(Path(m.__file__).resolve()).startswith(str(Path(sys.argv[1]).resolve()))
def forbidden(*a,**kw):raise AssertionError('No native process allowed during verify')
subprocess.run=forbidden
print(m.verify_fdp(Path(sys.argv[2]),'Metal/fdp_001')['trial_id'])
"""
    env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1')
    done=subprocess.run([sys.executable,'-B','-c',code,str(moved/'src'),str(relocated_run)],cwd=moved,env=env,capture_output=True,text=True,timeout=20)
    assert done.returncode==0,done.stderr
    assert done.stdout.strip()==doc['trial_id']


def test_native_timeout_is_reported_without_claiming_completion(tmp_path,monkeypatch):
    import subprocess
    from types import SimpleNamespace
    import nasolve.metal.fdp as module
    def timeout(*a,**kw):raise subprocess.TimeoutExpired('native-control',1)
    monkeypatch.setattr(module.subprocess,'run',timeout)
    with pytest.raises(RecipeError,match='timeout'):
        module._native(tmp_path,SimpleNamespace(executables={'phenix.python':'unused'},environment={}),10)
    assert (tmp_path/'native.log').exists()


def test_cli_has_explicit_run_and_trial_paths():
    from nasolve.cli import build_parser
    parser=build_parser()
    args=parser.parse_args(['metal','fdp','run','--geometry','Metal/geometry_001','--fit','m1','--occupancy','m1=0.4'])
    assert args.fit==['m1'] and args.occupancy==['m1=0.4'] and args.cycles==3
    args=parser.parse_args(['metal','verify-fdp','run','--trial','Metal/fdp_001'])
    assert args.trial==Path('Metal/fdp_001')


def test_native_uniform_amplitude_sigma_scaling_is_audited_not_hidden():
    a=reflection_evidence();b=copy.deepcopy(a['rows'])
    for row in b:row[1]*=261.6882043655679;row[2]*=261.6882043655679
    result=audit_reflections(a,reflection_evidence(b))
    assert result['uniform_F_sigma_scale']==pytest.approx(261.6882043655679)
    assert result['indices_and_flags']=='UNCHANGED'
    assert result['input_hash']!=result['output_hash']


@pytest.mark.parametrize('change',['unequal_F','unequal_sigma','flags','indices','negative_scale','missing'])
def test_native_rescaling_does_not_excuse_reflection_mutation(change):
    a=reflection_evidence();b=copy.deepcopy(a['rows'])
    for row in b:row[1]*=4;row[2]*=4
    if change=='unequal_F':b[0][1]+=.1
    elif change=='unequal_sigma':b[0][2]+=.1
    elif change=='flags':b[0][3]=True;b[1][3]=False
    elif change=='indices':b[0][0][0]=-1
    elif change=='negative_scale':
        for row in b:row[1]*=-1
    elif change=='missing':b.pop()
    with pytest.raises(RecipeError):audit_reflections(a,reflection_evidence(b))
