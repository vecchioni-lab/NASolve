"""Storage accounting must never be mistaken for replay or retirement authority."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import os

import pytest
from nasolve.metal.recipe import RecipeError, digest
from tests.test_metal_fdp import fake_execution


def sample(tmp_path, monkeypatch, count=2):
    module, context, _, native = fake_execution(tmp_path, monkeypatch)
    for i in range(count):
        module.run_fdp(context.run, 'Metal/geometry_001', native=native,
                       fit_nodes=['m1'], occupancies={'m1': .6+.1*i})
    paths = [Path(f'Metal/fdp_{i+1:03}') for i in range(count)]
    monkeypatch.setattr(module, '_native', lambda *a, **kw: pytest.fail('No native execution'))
    monkeypatch.setattr(module, 'verify_fdp', lambda *a, **kw: pytest.fail('No full scientific replay'))
    return context.run, paths


def test_exact_bytes_duplicate_content_and_immutable_inputs(tmp_path, monkeypatch):
    from nasolve.metal.storage import inspect_storage
    run, paths = sample(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for directory in paths for p in (run/directory).iterdir()}
    report = inspect_storage(run, paths)
    unique = {hashlib.sha256(raw).hexdigest(): len(raw) for raw in before.values()}
    assert report['logical_bytes'] == sum(map(len, before.values()))
    assert report['unique_content_bytes'] == sum(unique.values())
    assert report['repeated_content_bytes'] == report['logical_bytes']-sum(unique.values()) > 0
    assert report['scientific_replay'] is report['retirement_authorized'] is False
    assert report['upstream_payloads_counted'] is False
    assert before == {p: p.read_bytes() for p in before}
    assert sum(report['bytes_by_role'].values()) == report['logical_bytes']
    assert len(report['files']) == len(before)
    assert str(run) not in json.dumps(report)


@pytest.mark.parametrize('damage', ['checksum','size','anchor','extra','missing','symlink','manifest','failed','missing-required'])
def test_refuses_changed_or_incomplete_inventory(tmp_path, monkeypatch, damage):
    from nasolve.metal.storage import inspect_storage
    run, paths = sample(tmp_path, monkeypatch, 1)
    directory=run/paths[0]
    manifest=directory/'manifest.json'
    doc=json.loads(manifest.read_text())
    target=directory/'input.pdb'
    if damage=='checksum': target.write_bytes(b'x'*target.stat().st_size)
    elif damage=='size': target.write_bytes(target.read_bytes()+b'\n')
    elif damage=='anchor':
        doc['files']['input.pdb']['anchor']='dataset'
    elif damage=='extra': (directory/'unexpected.txt').write_text('extra')
    elif damage=='missing': target.unlink()
    elif damage=='symlink':
        outside=tmp_path/'outside.pdb'; target.rename(outside); target.symlink_to(outside)
    elif damage=='manifest': doc['status']='CHANGED'
    elif damage=='failed': (directory/'failure.json').write_text('{}')
    elif damage=='missing-required':
        target.unlink(); del doc['files']['input.pdb']
    if damage in {'anchor','manifest','missing-required'}:
        doc.pop('trial_id'); doc['trial_id']=digest(doc); manifest.write_text(json.dumps(doc))
    with pytest.raises(RecipeError): inspect_storage(run, paths)


def test_budgets_duplicates_and_paths(tmp_path, monkeypatch):
    from nasolve.metal.storage import inspect_storage
    run, paths=sample(tmp_path, monkeypatch, 1)
    for selected, kwargs in [([],{}), (paths*2,{}), (paths,{'max_bytes':1}),
                             (paths,{'max_bytes':True}), (['Metal/../Metal/fdp_001'],{}),
                             (['Metal/geometry_001'],{})]:
        with pytest.raises(RecipeError): inspect_storage(run, selected, **kwargs)
    alias=run/'Metal/fdp_002'; alias.symlink_to(run/paths[0], target_is_directory=True)
    with pytest.raises(RecipeError): inspect_storage(run,[alias])


def test_forecast_has_explicit_allowances_and_no_compaction_claim():
    from nasolve.metal.storage import forecast_storage
    request=dict(datasets=200,trials_per_dataset=100,protected_bytes_per_dataset=1000,
                 concurrent_jobs=4,scratch_bytes_per_job=300,compaction_overlap_bytes=400,reserve_bytes=500)
    result=forecast_storage(1024,request)
    assert result['scenario_peak_bytes']==20000*1024+200*1000+4*300+400+500
    assert result['compact_layout_estimated'] is result['guaranteed_upper_bound'] is False
    assert result['reserved_bytes']==0
    for wrong in [{},dict(request, datasets=True),dict(request,reserve_bytes=-1),dict(request,concurrent_jobs=20001)]:
        with pytest.raises(RecipeError): forecast_storage(1024,wrong)


def test_relocated_sample_after_original_path_gone(tmp_path, monkeypatch):
    from nasolve.metal.storage import inspect_storage
    original=tmp_path/'original'; original.mkdir()
    run,paths=sample(original,monkeypatch,1)
    expected=inspect_storage(run,paths)
    relative_run=run.relative_to(original)
    source=Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source,original/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Remove parent payload deliberately: the inventory must not claim to audit it.
    shutil.rmtree(run/'Metal/geometry_001')
    moved=tmp_path/'relocated'; original.rename(moved)
    assert not original.exists()
    script="""from nasolve.metal.storage import inspect_storage
import nasolve.metal.storage as module
import json,sys,subprocess
from pathlib import Path
assert Path(module.__file__).is_relative_to(Path(sys.argv[1]))
def forbidden(*a,**kw): raise AssertionError('No native execution')
subprocess.run=forbidden
print(json.dumps(inspect_storage(sys.argv[2],['Metal/fdp_001'])))
"""
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(moved/'src'))
    done=subprocess.run([sys.executable,'-B','-c',script,str(moved/'src'),str(moved/relative_run)],
                        cwd=moved,env=env,capture_output=True,text=True,timeout=20)
    assert done.returncode==0,done.stderr
    assert json.loads(done.stdout)==expected


def test_cli_reports_scope_and_refuses_output_inside_trials(tmp_path,monkeypatch,capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    run,paths=sample(tmp_path,monkeypatch,1)
    command=['metal','inspect-fdp-storage',str(run),'--trial',str(paths[0])]
    args=build_parser().parse_args(command)
    assert execute(args)==0
    assert 'parents excluded' in capsys.readouterr().out
    output=run/paths[0]/'inventory.json'
    assert execute(build_parser().parse_args(command+['--output',str(output)]))==2
    assert not output.exists()
    output=tmp_path/'inventory.json'
    assert execute(build_parser().parse_args(command+['--json','--output',str(output)]))==0
    assert json.loads(output.read_text())['kind']=='metal-fdp-storage-inventory'
    assert execute(build_parser().parse_args(command+['--output',str(output)]))==2


def test_inventory_change_during_hashing_is_rejected(tmp_path,monkeypatch):
    import nasolve.metal.storage as storage
    run,paths=sample(tmp_path,monkeypatch,1)
    original=storage._hash
    def changed(path,state):
        value=original(path,state)
        if path.name=='result.json':
            (path.parent/'late.txt').write_text('concurrent mutation')
        return value
    monkeypatch.setattr(storage,'_hash',changed)
    with pytest.raises(RecipeError,match='changed during'):
        storage.inspect_storage(run,paths)


def test_manifest_and_file_count_limits(tmp_path,monkeypatch):
    import nasolve.metal.storage as storage
    run,paths=sample(tmp_path,monkeypatch,1)
    monkeypatch.setattr(storage,'MAX_MANIFEST_BYTES',1)
    with pytest.raises(RecipeError,match='oversized'):
        storage.inspect_storage(run,paths)
    monkeypatch.setattr(storage,'MAX_MANIFEST_BYTES',1024*1024)
    monkeypatch.setattr(storage,'MAX_FILES_PER_TRIAL',1)
    with pytest.raises(RecipeError,match='file-count'):
        storage.inspect_storage(run,paths)
