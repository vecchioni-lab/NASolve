"""A compact projection must not confer authority over omitted evidence."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from nasolve.metal.recipe import RecipeError, digest
from tests.test_metal_fdp import fake_execution


def trials(tmp_path, monkeypatch, qs=(.6, .7, .6)):
    module, context, _, native = fake_execution(tmp_path, monkeypatch)
    for q in qs:
        module.run_fdp(context.run, 'Metal/geometry_001', native=native,
                       fit_nodes=['m1'], occupancies={'m1': q})
    monkeypatch.setattr(module, '_native', lambda *a, **kw: pytest.fail('No native job'))
    return context.run, [Path(f'Metal/fdp_{i+1:03}') for i in range(len(qs))]


def test_shared_metadata_lossless_results_and_duplicate_attempts(tmp_path, monkeypatch):
    from nasolve.metal.compact import project_trials, verify_projection, encode
    run, paths = trials(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in run.rglob('*') if p.is_file()}
    report = project_trials(run, paths)
    assert len(report['bases']) == 1
    assert len(report['requests']) == 2
    assert len(report['records']) == 3
    rows = report['records']
    assert rows[0]['input_id'] == rows[2]['input_id'] != rows[1]['input_id']
    assert rows[0]['record_id'] != rows[2]['record_id']
    for row, path in zip(rows, paths):
        assert row['result'] == json.loads((run/path/'result.json').read_text())
        assert row['occupancy_vector']['m1'] == row['result']['sites'][0]['occupancy']
    assert report['source_replay'] == 'FULL_FDP_REPLAY_AT_PROJECTION'
    assert all(report[k] is False for k in ['retirement_authorized','reuse_authorized','materialization_supported','standalone_evidence'])
    assert verify_projection(run, json.loads(encode(report))) == report
    assert str(run) not in encode(report).decode()
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert before.keys() == {p for p in run.rglob('*') if p.is_file()}


@pytest.mark.parametrize('change', ['result','permission','request','basis','size','missing-record','duplicate-record','source-ref','limit-claim'])
def test_rehashed_projection_cannot_replace_source_replay(tmp_path, monkeypatch, change):
    from nasolve.metal.compact import project_trials, verify_projection
    run, paths = trials(tmp_path, monkeypatch, (.6,))
    report = project_trials(run, paths)
    if change == 'result': report['records'][0]['result']['sites'][0]['f_double_prime'] += 1
    elif change == 'permission': report['retirement_authorized'] = True
    elif change == 'request': next(iter(report['requests'].values()))['settings']['cycles'] += 1
    elif change == 'basis': next(iter(report['bases'].values()))['native_version'] = 'future'
    elif change == 'size': report['section_bytes']['records'] += 1
    elif change == 'missing-record': report['records'] = []
    elif change == 'duplicate-record': report['records'] *= 2
    elif change == 'source-ref': report['records'][0]['source_manifest']['anchor'] = 'absolute'
    elif change == 'limit-claim': report['limits']['upstream_replay_budgeted'] = True
    report.pop('projection_id'); report['projection_id'] = digest(report)
    with pytest.raises(RecipeError): verify_projection(run, report)


def test_payload_integrity_is_not_a_freeze_audit(tmp_path, monkeypatch):
    from nasolve.metal.compact import project_trials
    from nasolve.metal.storage import inspect_storage
    run, paths = trials(tmp_path, monkeypatch, (.6,))
    root = run/paths[0]
    p = root/'native-result.json.gz'
    native = json.loads(gzip.decompress(p.read_bytes()))
    native['atoms'][0]['xyz'][0] += .2
    p.write_bytes(gzip.compress(json.dumps(native).encode(), mtime=0))
    manifest = json.loads((root/'manifest.json').read_text())
    manifest['files'][p.name].update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), size=p.stat().st_size)
    manifest.pop('trial_id'); manifest['trial_id'] = digest(manifest)
    (root/'manifest.json').write_text(json.dumps(manifest))
    inspect_storage(run, paths)
    with pytest.raises(RecipeError, match='Frozen native state'): project_trials(run, paths)


@pytest.mark.parametrize('removed', ['native-result.json.gz', 'parent'])
def test_deleted_native_or_parent_evidence_is_not_excused(tmp_path, monkeypatch, removed):
    from nasolve.metal.compact import project_trials, verify_projection
    run, paths = trials(tmp_path, monkeypatch, (.6,))
    report = project_trials(run, paths)
    if removed == 'parent':
        shutil.rmtree(run/'Metal/geometry_001')
    else:
        (run/paths[0]/removed).unlink()
    with pytest.raises(RecipeError): verify_projection(run, report)


def test_limits_and_no_implicit_trial_discovery(tmp_path, monkeypatch):
    from nasolve.metal.compact import project_trials
    run, paths = trials(tmp_path, monkeypatch, (.6,))
    for selected, options in [([],{}),(paths*2,{}),(paths,{'max_bytes':1}),
                              (paths,{'max_projection_bytes':1}),(paths,{'max_projection_bytes':True}),
                              (['Metal/../Metal/fdp_001'],{})]:
        with pytest.raises(RecipeError): project_trials(run, selected, **options)


def test_relocated_source_and_data_without_original_in_new_process(tmp_path, monkeypatch):
    from nasolve.metal.compact import project_trials, encode
    old = tmp_path/'original'; old.mkdir()
    run, paths = trials(old, monkeypatch, (.6,.7))
    report = project_trials(run, paths)
    (old/'projection.json').write_bytes(encode(report))
    source = Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source, old/'src', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved = tmp_path/'moved'; old.rename(moved); assert not old.exists()
    code = """import json,sys,subprocess
from pathlib import Path
import nasolve.metal.compact as module
assert Path(module.__file__).is_relative_to(Path(sys.argv[1]))
def forbidden(*args,**kwargs): raise AssertionError('No native process')
subprocess.run=forbidden
report=module.read_projection(Path(sys.argv[2]))
print(module.verify_projection(Path(sys.argv[3]),report)['projection_id'])
"""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(moved/'src'))
    done = subprocess.run([sys.executable,'-B','-c',code,str(moved/'src'),str(moved/'projection.json'),
                           str(moved/'dataset/AutoMR/run_001')],cwd=moved,env=env,capture_output=True,text=True,timeout=30)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == report['projection_id']


def test_cli_projection_is_new_external_file_and_verifies(tmp_path, monkeypatch, capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    run, paths = trials(tmp_path, monkeypatch, (.6,))
    parser = build_parser()
    base = ['metal','project-fdp-records',str(run),'--trial',str(paths[0])]
    assert execute(parser.parse_args(base+['--output',str(run/paths[0]/'projection.json')])) == 2
    target = tmp_path/'projection.json'
    assert execute(parser.parse_args(base+['--output',str(target)])) == 0
    assert 'no retirement or reuse' in capsys.readouterr().out
    assert execute(parser.parse_args(base+['--output',str(target)])) == 2
    assert execute(parser.parse_args(['metal','verify-fdp-records',str(run),'--projection',str(target)])) == 0


def test_duplicate_json_keys_and_oversized_projection_are_rejected(tmp_path):
    from nasolve.metal.compact import read_projection
    p=tmp_path/'projection.json'; p.write_text('{"kind":1,"kind":2}')
    with pytest.raises(RecipeError): read_projection(p)
    with pytest.raises(RecipeError): read_projection(p,max_projection_bytes=1)
    p.write_text('['*2000 + '0' + ']'*2000)
    with pytest.raises(RecipeError): read_projection(p)


@pytest.mark.parametrize('option,value', [('start_fdp',2.),('cycles',4),('minimizer_cycles',2),('max_iterations',21),('metal_b_policy','keep')])
def test_changed_fit_requests_do_not_share_input_fingerprint(tmp_path,monkeypatch,option,value):
    from nasolve.metal.compact import project_trials
    module, context, _, native = fake_execution(tmp_path, monkeypatch)
    module.run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'])
    module.run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'],**{option:value})
    report=project_trials(context.run,['Metal/fdp_001','Metal/fdp_002'])
    assert len(report['requests'])==2
    assert report['records'][0]['input_id']!=report['records'][1]['input_id']


def test_parent_mutation_during_projection_is_rejected(tmp_path,monkeypatch):
    import nasolve.metal.compact as compact
    run, paths=trials(tmp_path,monkeypatch,(.6,))
    original=compact._load_trial
    calls=[]
    def mutate(*args,**kwargs):
        result=original(*args,**kwargs)
        calls.append(1)
        if len(calls)==1:
            (run/'Metal/geometry_001/manifest.json').write_text('{}')
        return result
    monkeypatch.setattr(compact,'_load_trial',mutate)
    with pytest.raises(RecipeError):compact.project_trials(run,paths)


def test_stricter_verification_budget_does_not_change_record(tmp_path,monkeypatch):
    from nasolve.metal.compact import project_trials,verify_projection,encode
    run, paths=trials(tmp_path,monkeypatch,(.6,))
    report=project_trials(run,paths)
    assert verify_projection(run,report,max_bytes=report['source_trial_bytes'],max_projection_bytes=len(encode(report)))==report
    with pytest.raises(RecipeError):verify_projection(run,report,max_bytes=report['source_trial_bytes']-1)
    with pytest.raises(RecipeError):verify_projection(run,report,max_projection_bytes=len(encode(report))-1)


@pytest.mark.parametrize('directory,size', [('Metal/fdp_999',1024*1024+1),('rogue',100)])
def test_untrusted_manifest_is_rejected_before_source_read(tmp_path,monkeypatch,directory,size):
    import nasolve.metal.compact as compact
    run, paths=trials(tmp_path,monkeypatch,(.6,))
    report=compact.project_trials(run,paths)
    parent=run/directory;parent.mkdir(parents=True)
    path=parent/'manifest.json';path.write_bytes(b'x'*size)
    report['records'][0]['source_manifest']=dict(anchor='run',relative_path=path.relative_to(run).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),size=size)
    report.pop('projection_id');report['projection_id']=digest(report)
    monkeypatch.setattr(compact,'_source',lambda *a,**kw:pytest.fail('Unbounded read before trial preflight'))
    with pytest.raises(RecipeError):compact.verify_projection(run,report)
