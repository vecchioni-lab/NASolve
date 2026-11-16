"""Cluster response profiles preserve matching, signed evidence and immutable lineage."""
import json
from pathlib import Path
import pytest
from nasolve.metal.recipe import RecipeError
from nasolve.metal import fdp_count_compare as module
from nasolve.metal.fdp_count import summarize_count
from tests.test_metal_fdp_count import result, groups
from tests.test_metal_fdp_compare import trials


def read_report(run,doc):
    return json.loads((run/doc['files']['report']['relative_path']).read_text())


def test_cancelling_sites_cannot_hide_behind_a_small_cluster_sum():
    r=result(('Ag','Ag'),occupancy=.5)
    r['sites'][0]['f_double_prime']=10.;r['sites'][1]['f_double_prime']=-9.
    g=summarize_count(r,groups(['m1','m2']))['groups'][0]
    d=module.response_diagnostics(g)
    assert d['unweighted_fdp_e']==1.
    assert d['positive_q_weighted_fdp_e']==5.
    assert d['negative_q_weighted_fdp_e']==-4.5
    assert d['absolute_q_weighted_fdp_e']==9.5
    assert d['cancellation_fraction']==pytest.approx(1-.5/9.5)
    assert 'MIXED_SIGN_FDP' in d['warnings']
    assert d['b_range_A2']==0 and d['occupancy_sum']==1.
    zero=result(('Ag',),fdp=0.)
    z=module.response_diagnostics(summarize_count(zero,groups(['m1']))['groups'][0])
    assert z['cancellation_fraction'] is None


def test_group_profile_holds_neighbor_occupancy_fixed_and_does_not_select(tmp_path,monkeypatch):
    c,paths=trials(tmp_path,monkeypatch,[
        dict(occupancies={'m1':.6,'m2':.8},cycles=6),
        dict(occupancies={'m1':.4,'m2':.8},cycles=6),
        dict(occupancies={'m1':.4,'m2':.7},cycles=6),
        dict(occupancies={'m1':.4,'m2':.8},cycles=10)],metals=('Au','Ag'))
    before={p:p.read_bytes() for p in c.run.rglob('*') if p.is_file()}
    import subprocess
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:pytest.fail('Offline comparison ran native software'))
    doc=module.build_count_comparison(c.run,paths,groups(['m1','m2']))
    data=read_report(c.run,doc)
    assert len(data['snapshots'])==4
    assert data['automatic_checkpoint_selection'] is False
    assert data['convergence']=='NOT_ESTABLISHED_BY_ENDPOINT_COMPARISON'
    profiles=[p for p in data['profiles'] if p['status']=='COMPARED']
    first=next(p for p in profiles if p['axis']=={'kind':'occupancy','node_id':'m1'})
    assert first['fixed_occupancies']=={'m2':.8}
    assert [p['value'] for p in first['points']]==[.4,.6]
    assert all(len(s['sites'])==2 for s in data['snapshots'])
    assert all(len(s['groups'][0]['elements'])==2 for s in data['snapshots'])
    assert all('sites' not in s['groups'][0] for s in data['snapshots'])
    assert module.verify_count_comparison(c.run,'Metal/fdp_count_comparison_001')==doc
    assert all(p.read_bytes()==raw for p,raw in before.items())


def test_matched_settings_and_outside_group_q_still_matter(tmp_path,monkeypatch):
    c,paths=trials(tmp_path,monkeypatch,[
        dict(occupancies={'m1':.6,'m2':.8}),
        dict(occupancies={'m1':.4,'m2':.7})],metals=('Hg','Ag'))
    d=read_report(c.run,module.build_count_comparison(c.run,paths,groups(['m1'])))
    assert all(p['status']=='NOT_TESTED' for p in d['profiles'])
    assert all(s['excluded_fitted_nodes']==['m2'] for s in d['snapshots'])


@pytest.mark.parametrize('options',[
    [dict(occupancies={'m1':.6}),dict(occupancies={'m1':.4},reference_shift=.2)],
    [dict(occupancies={'m1':.6}),dict(occupancies={'m1':.4},free_r_test_value=1)],
])
def test_different_scientific_controls_fail_before_allocation(tmp_path,monkeypatch,options):
    c,paths=trials(tmp_path,monkeypatch,options)
    with pytest.raises(RecipeError,match='same geometry'):
        module.build_count_comparison(c.run,paths,groups(['m1']))
    assert not list((c.run/'Metal').glob('fdp_count_comparison_*'))


@pytest.mark.parametrize('change',['report','manifest','source','extra','symlink'])
def test_saved_report_and_even_rehashed_tampering_are_rejected(tmp_path,monkeypatch,change):
    from nasolve.metal.context import _reference
    from nasolve.metal.materialize import _json_bytes
    from nasolve.metal.recipe import digest
    c,paths=trials(tmp_path,monkeypatch)
    doc=module.build_count_comparison(c.run,paths,groups(['m1']));d=c.run/'Metal/fdp_count_comparison_001'
    if change=='report':
        r=read_report(c.run,doc);r['snapshots'][0]['groups'][0]['q_weighted_fdp_e']=999
        (d/'report.json').write_bytes(_json_bytes(r));doc['files']['report']=_reference(d/'report.json',c.run)
    elif change=='manifest':doc['scientific_acceptance']='ACCEPTED'
    elif change=='source':(c.run/paths[0]/'final.pdb').write_text('changed')
    elif change=='extra':(d/'unexpected').write_text('extra')
    else:
        p=d/'report.json';dest=tmp_path/'moved.json';p.rename(dest);p.symlink_to(dest)
    doc.pop('comparison_id');doc['comparison_id']=digest(doc);(d/'manifest.json').write_bytes(_json_bytes(doc))
    with pytest.raises(RecipeError):module.verify_count_comparison(c.run,d)


def test_native_endpoint_b_policies_cannot_be_mixed(tmp_path,monkeypatch):
    from tests.test_metal_fdp_endpoint import endpoint
    from nasolve.metal.fdp import run_fdp
    c,h,x,n=endpoint(tmp_path,monkeypatch,metals=('Ag','Ag'))
    for b in ('donor-mean','keep'):
        run_fdp(c.run,'Metal/xyz_001',native=n,fit_nodes=['m1','m2'],metal_b_policy=b)
    with pytest.raises(RecipeError,match='same geometry'):
        module.build_count_comparison(c.run,['Metal/fdp_001','Metal/fdp_002'],groups(['m1','m2']))
    assert not list((c.run/'Metal').glob('fdp_count_comparison_*'))


def test_groups_are_explicit_bounded_and_partial_membership_is_rejected(tmp_path,monkeypatch):
    c,paths=trials(tmp_path,monkeypatch)
    for invalid in ({},groups(['missing']),groups(['m1','m1']),None,{str(i):groups(['m1'])['cluster'] for i in range(33)}):
        with pytest.raises(RecipeError):module.build_count_comparison(c.run,paths,invalid)
    assert not list((c.run/'Metal').glob('fdp_count_comparison_*'))


def test_replicates_zero_reference_and_different_b_remain_explicit(tmp_path, monkeypatch):
    c, paths = trials(tmp_path, monkeypatch, [dict(zero_reference=True), dict(zero_reference=True)])
    data = read_report(c.run, module.build_count_comparison(c.run, paths, groups(['m1'])))
    assert all(p['status']=='NOT_TESTED' for p in data['profiles'])
    assert all(len(p['points'][0]['trial_ids'])==2 for p in data['profiles'])
    assert all(p['points'][0]['response_ratio_min'] is None for p in data['profiles'])
    assert all(s['groups'][0]['response_ratio'] is None for s in data['snapshots'])
    r = result(('Ag', 'Ag')); r['sites'][1]['b_iso'] = 400.
    d = module.response_diagnostics(summarize_count(r, groups(['m1', 'm2']))['groups'][0])
    assert d['b_range_A2']==100. and 'DIFFERENT_SITE_B' in d['warnings']


def test_cli_build_and_replay_without_native_discovery(tmp_path, monkeypatch, capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    import nasolve.metal.cli as cli
    c, paths = trials(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, 'discover_phenix', lambda *a, **k: pytest.fail('No native discovery'))
    scope = tmp_path/'groups.json'; scope.write_text(json.dumps(groups(['m1'])))
    args = ['metal', 'compare-fdp-count', str(c.run), '--groups', str(scope)]
    for path in paths: args += ['--trial', str(path)]
    parser = build_parser()
    assert execute(parser.parse_args(args))==0
    text = capsys.readouterr().out
    assert 'sum Q (occ)' in text and 'cancellation' in text
    assert execute(parser.parse_args(['metal', 'verify-fdp-count-comparison', str(c.run),
        '--comparison', 'Metal/fdp_count_comparison_001', '--json']))==0
    assert json.loads(capsys.readouterr().out)['status']=='COMPARISON_REVIEW'


def test_publication_race_is_retained_and_never_reused(tmp_path, monkeypatch):
    c, paths = trials(tmp_path, monkeypatch)
    original = module._load_trials
    reads = 0
    def changing(*args):
        nonlocal reads
        loaded = original(*args); reads += 1
        if reads==2: loaded[0]['result']['r_work'] += .01
        return loaded
    monkeypatch.setattr(module, '_load_trials', changing)
    with pytest.raises(RecipeError, match='changed while publishing'):
        module.build_count_comparison(c.run, paths, groups(['m1']))
    failed = c.run/'Metal/fdp_count_comparison_001'
    assert (failed/'failure.json').is_file() and not (failed/'manifest.json').exists()
    with pytest.raises(RecipeError): module.verify_count_comparison(c.run, failed)
    monkeypatch.setattr(module, '_load_trials', original)
    doc = module.build_count_comparison(c.run, paths, groups(['m1']))
    assert 'fdp_count_comparison_002' in doc['files']['report']['relative_path']


def test_relocation_replays_in_fresh_interpreter_after_source_and_data_move(tmp_path, monkeypatch):
    import os, shutil, subprocess, sys
    original = tmp_path/'original'; original.mkdir()
    c, paths = trials(original, monkeypatch)
    doc = module.build_count_comparison(c.run, paths, groups(['m1']))
    source = Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source, original/'src', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved = tmp_path/'moved'; original.rename(moved)
    assert not original.exists()
    code = """import sys, subprocess
from pathlib import Path
import nasolve.metal.fdp_count_compare as m
assert str(Path(m.__file__).resolve()).startswith(str(Path(sys.argv[1]).resolve()))
def forbidden(*a,**k): raise AssertionError('Offline replay launched native software')
subprocess.run=forbidden
print(m.verify_count_comparison(sys.argv[2], 'Metal/fdp_count_comparison_001')['comparison_id'])
"""
    done = subprocess.run([sys.executable, '-B', '-c', code, str(moved/'src'),
        str(moved/'dataset/AutoMR/run_001')], cwd=moved,
        env=dict(os.environ, PYTHONPATH=str(moved/'src'), PYTHONDONTWRITEBYTECODE='1'),
        capture_output=True, text=True, timeout=30)
    assert done.returncode==0, done.stderr
    assert done.stdout.strip()==doc['comparison_id']


@pytest.mark.parametrize('invalid', ['one', 'duplicate', 'too_many'])
def test_trial_bounds_are_enforced_before_allocation(tmp_path, monkeypatch, invalid):
    c, paths = trials(tmp_path, monkeypatch)
    paths = paths[:1] if invalid=='one' else [paths[0]]*2 if invalid=='duplicate' else paths*33
    with pytest.raises(RecipeError): module.build_count_comparison(c.run, paths, groups(['m1']))
    assert not list((c.run/'Metal').glob('fdp_count_comparison_*'))
