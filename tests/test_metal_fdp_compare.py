"""Comparisons preserve controls and report sensitivity without selecting a solution."""
import copy
import gzip
import json
from pathlib import Path
import pytest

from nasolve.metal import RecipeError
from nasolve.metal.fdp import run_fdp
from nasolve.metal.fdp_compare import build_comparison, verify_comparison
from nasolve.metal.materialize import _json_bytes
from tests.test_metal_fdp import prepared, native_result


def trials(tmp_path, monkeypatch, options=None, metals=('Hg',)):
    from types import SimpleNamespace
    import nasolve.metal.fdp as module
    context, geometry, base_plan, _ = prepared(tmp_path, metals=metals)
    refs = copy.deepcopy(base_plan['references'])
    monkeypatch.setattr(module, 'inspect_observations', lambda *a,**kw: base_plan['metadata'])
    monkeypatch.setattr(module, 'reference_scattering', lambda *a,**kw: refs)
    monkeypatch.setattr(module, 'audit_free_r_flags', lambda *a,**kw: SimpleNamespace(status='VALID', valid=True, details={}, warnings=()))
    native = SimpleNamespace(version='2.2.1', executables={'phenix.python':'unused', 'phenix.mtz.dump':'unused'}, environment={})
    def execute(directory, native, timeout):
        plan = json.loads((directory/'plan.json').read_text())
        model = (directory/'input.pdb').read_bytes()
        result = native_result(plan, model)
        for group in result['groups']:
            if group['refine_fdp']:
                q = result['atoms'][group['indices'][0]]['occupancy']
                value = 3/q + plan['options']['start_fdp']/10 + 1/plan['options']['cycles']
                group['f_double_prime'] = value
                for index in group['indices']: result['atoms'][index]['fdp'] = value
        (directory/'native-result.json.gz').write_bytes(gzip.compress(_json_bytes(result), mtime=0))
        (directory/'final.pdb').write_bytes(model)
        return result
    monkeypatch.setattr(module, '_native', execute)
    options = options or [dict(occupancies={'m1':.6}, cycles=3, start_fdp=0),
                          dict(occupancies={'m1':.6}, cycles=6, start_fdp=0),
                          dict(occupancies={'m1':.6}, cycles=6, start_fdp=10),
                          dict(occupancies={'m1':.4}, cycles=6, start_fdp=0)]
    paths = []
    for original in options:
        settings = dict(original)
        refs[:] = copy.deepcopy(base_plan['references'])
        shift = settings.pop('reference_shift', 0)
        for reference in refs:
            reference['f_prime'] += shift
            if settings.get('zero_reference'): reference['f_double_prime'] = 0.
        settings.pop('zero_reference', None)
        fit = settings.pop('fit_nodes', ['m'+str(i+1) for i in range(len(metals))])
        doc = run_fdp(context.run, 'Metal/geometry_001', native=native, fit_nodes=fit, **settings)
        paths.append(Path(doc['files']['result.json']['relative_path']).parent)
    return context, paths


def report(run, doc):
    return json.loads((run/doc['files']['report']['relative_path']).read_text())


def test_comparison_measures_only_matched_variations_without_native_execution(tmp_path, monkeypatch):
    context, paths = trials(tmp_path, monkeypatch)
    before = {str(p.relative_to(context.run)):p.read_bytes() for p in context.run.rglob('*') if p.is_file()}
    import subprocess
    monkeypatch.setattr(subprocess, 'run', lambda *a,**kw: pytest.fail('Comparison must be offline'))
    doc = build_comparison(context.run, paths)
    data = report(context.run, doc)
    assert len(data['rows']) == 4
    assert len({r['row_id'] for r in data['rows']}) == 4
    assert data['automatic_checkpoint_selection'] is False
    assert data['convergence'] == 'NOT_ESTABLISHED_BY_ENDPOINT_COMPARISON'
    assert data['scientific_acceptance'] == 'NOT_ASSESSED'
    assert data['rows'][0]['reference_deviation_fraction'] == pytest.approx((5+1/3-3)/3)
    starts = [g for g in data['sensitivity']['start_fdp'] if g['status']=='COMPARED']
    cycles = [g for g in data['sensitivity']['cycles'] if g['status']=='COMPARED']
    occupancy = [g for g in data['sensitivity']['occupancy'] if g['status']=='COMPARED']
    assert len(starts)==len(cycles)==len(occupancy)==1
    assert starts[0]['f_double_prime_range_e'] == pytest.approx(1.)
    assert cycles[0]['f_double_prime_range_e'] == pytest.approx(1/6)
    assert occupancy[0]['f_double_prime_range_e'] == pytest.approx(2.5)
    assert verify_comparison(context.run, 'Metal/fdp_comparison_001') == doc
    assert all((context.run/name).read_bytes()==raw for name,raw in before.items())


def two_options(**second):
    return [dict(occupancies={'m1':.6}), dict(occupancies={'m1':.6}, **second)]


@pytest.mark.parametrize('change', ['reference', 'test_flags', 'worker', 'kernel', 'reflections', 'groups'])
def test_incompatible_experiments_are_rejected_before_allocating(tmp_path, monkeypatch, change):
    from nasolve.metal.context import _reference
    from nasolve.metal.recipe import digest
    options = two_options()
    if change=='reference': options[1]['reference_shift'] = .1
    if change=='test_flags': options[1]['free_r_test_value'] = 1
    if change=='groups': options[0]['fit_nodes'] = ['m1']
    context, paths = trials(tmp_path, monkeypatch, options, metals=('Hg','Ag'))
    if change in {'worker','kernel','reflections'}:
        directory = context.run/paths[1]
        doc = json.loads((directory/'manifest.json').read_text())
        if change=='worker': doc['worker_sha256'] = 'e'*64
        else:
            from tests.test_metal_fdp import reflection_evidence
            p = directory/'native-result.json.gz'
            evidence = json.loads(gzip.decompress(p.read_bytes()))
            if change=='kernel': evidence['native_source_hashes']['xray_kernel'] = 'e'*64
            else:
                for side in ('reflection_before','reflection_after'):
                    data = evidence[side]['rows']
                    data[0][1] += 1
                    evidence[side] = reflection_evidence(data)
            p.write_bytes(gzip.compress(_json_bytes(evidence), mtime=0))
            doc['files'][p.name] = _reference(p, context.run)
            # Recompute the legitimate individual audit; only cross-trial matching fails.
            from nasolve.metal.fdp import audit_result
            result = audit_result(json.loads((directory/'plan.json').read_text()), (directory/'input.pdb').read_bytes(), evidence)
            (directory/'result.json').write_bytes(_json_bytes(result))
            doc['files']['result.json'] = _reference(directory/'result.json', context.run)
        doc.pop('trial_id'); doc['trial_id'] = digest(doc)
        (directory/'manifest.json').write_bytes(_json_bytes(doc))
    from nasolve.metal.fdp import verify_fdp
    for path in paths: verify_fdp(context.run, path)
    with pytest.raises(RecipeError, match='same geometry'):
        build_comparison(context.run, paths)
    assert not list((context.run/'Metal').glob('fdp_comparison_*'))


def test_multi_site_occupancy_changes_are_not_mislabeled_as_one_site_response(tmp_path, monkeypatch):
    context, paths = trials(tmp_path, monkeypatch, [
        dict(occupancies={'m1':.6, 'm2':.8}),
        dict(occupancies={'m1':.4, 'm2':.7}),
        dict(occupancies={'m1':.5, 'm2':.8})], metals=('Hg','Ag'))
    data = report(context.run, build_comparison(context.run, paths))
    groups = [g for g in data['sensitivity']['occupancy'] if g['status']=='COMPARED']
    assert len(groups)==1 and groups[0]['node_id']=='m1'
    assert groups[0]['fixed_occupancies']=={'m2':.8}
    assert [point['value'] for point in groups[0]['endpoints']]==[.5,.6]
    assert all(len(row['occupancy_vector'])==2 for row in data['rows'])


def test_replicates_and_untested_axes_do_not_imply_stability(tmp_path, monkeypatch):
    context, paths = trials(tmp_path, monkeypatch, two_options())
    data = report(context.run, build_comparison(context.run, paths))
    assert len(data['trials'])==2
    for groups in data['sensitivity'].values():
        assert all(g['status']=='NOT_TESTED' and g['f_double_prime_range_e'] is None for g in groups)
        assert all(len(g['endpoints'][0]['row_ids'])==2 for g in groups)


def test_zero_reference_is_not_divided_or_used_to_rank(tmp_path, monkeypatch):
    context, paths = trials(tmp_path, monkeypatch, [dict(zero_reference=True), dict(zero_reference=True, cycles=6)])
    data = report(context.run, build_comparison(context.run, paths))
    assert all(r['reference_deviation_fraction'] is None and r['normalization_status']=='ZERO_REFERENCE' for r in data['rows'])
    assert 'selected_trial' not in data and 'rank' not in data


@pytest.mark.parametrize('case', ['one','too_many','alias','missing','outside'])
def test_invalid_trial_sets_do_not_allocate(tmp_path, monkeypatch, case):
    context, paths = trials(tmp_path, monkeypatch, two_options())
    if case=='one': paths=paths[:1]
    elif case=='too_many': paths=paths*65
    elif case=='alias': paths=[paths[0],context.run/paths[0]]
    elif case=='missing': paths[1]=Path('Metal/fdp_999')
    elif case=='outside': paths[1]=tmp_path/'outside'
    with pytest.raises(RecipeError): build_comparison(context.run, paths)
    assert not list((context.run/'Metal').glob('fdp_comparison_*'))


@pytest.mark.parametrize('target', ['report','manifest','trial','extra'])
def test_rehashed_tampering_is_rejected_by_comparison_replay(tmp_path, monkeypatch, target):
    from nasolve.metal.context import _reference
    from nasolve.metal.recipe import digest
    context, paths = trials(tmp_path, monkeypatch, two_options(cycles=6))
    doc = build_comparison(context.run, paths)
    directory = context.run/'Metal/fdp_comparison_001'
    if target=='report':
        data = report(context.run, doc)
        data['rows'][0]['f_double_prime'] += 1
        (directory/'report.json').write_bytes(_json_bytes(data))
        doc['files']['report'] = _reference(directory/'report.json', context.run)
    elif target=='manifest': doc['automatic_checkpoint_selection'] = True
    elif target=='trial': (context.run/paths[0]/'input.pdb').write_text('tampered')
    else: (directory/'unrecorded.txt').write_text('extra')
    doc.pop('comparison_id'); doc['comparison_id'] = digest(doc)
    (directory/'manifest.json').write_bytes(_json_bytes(doc))
    with pytest.raises(RecipeError): verify_comparison(context.run, directory)


def test_failed_publication_is_retained_and_next_number_is_new(tmp_path, monkeypatch):
    import nasolve.metal.fdp_compare as module
    context, paths = trials(tmp_path, monkeypatch, two_options(cycles=6))
    original = module._manifest
    def fail(*a,**kw): raise RecipeError('Publication control failure')
    monkeypatch.setattr(module, '_manifest', fail)
    with pytest.raises(RecipeError, match='Publication'): build_comparison(context.run, paths)
    failed = context.run/'Metal/fdp_comparison_001'
    assert (failed/'failure.json').exists() and not (failed/'manifest.json').exists()
    with pytest.raises(RecipeError): verify_comparison(context.run, failed)
    monkeypatch.setattr(module, '_manifest', original)
    doc = build_comparison(context.run, paths)
    assert 'fdp_comparison_002' in doc['files']['report']['relative_path']
    assert (failed/'failure.json').exists()


def test_relocation_replays_with_original_source_removed_and_no_native_process(tmp_path, monkeypatch):
    import os, shutil, subprocess, sys
    original = tmp_path/'original'; original.mkdir()
    context, paths = trials(original, monkeypatch, two_options(cycles=6))
    doc = build_comparison(context.run, paths)
    source = Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source, original/'src', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved = tmp_path/'moved'; original.rename(moved)
    assert not original.exists()
    code = """import sys, subprocess
from pathlib import Path
import nasolve.metal.fdp_compare as m
assert str(Path(m.__file__).resolve()).startswith(str(Path(sys.argv[1]).resolve()))
def forbidden(*a,**kw):raise AssertionError('Comparison replay must not launch native code')
subprocess.run=forbidden
print(m.verify_comparison(sys.argv[2], 'Metal/fdp_comparison_001')['comparison_id'])
"""
    done = subprocess.run([sys.executable,'-B','-c',code,str(moved/'src'),str(moved/'dataset/AutoMR/run_001')],
                          cwd=moved, env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),
                          capture_output=True,text=True,timeout=30)
    assert done.returncode==0, done.stderr
    assert done.stdout.strip()==doc['comparison_id']


def test_cli_publishes_and_replays_existing_trials_without_discovering_phenix(tmp_path, monkeypatch, capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    import nasolve.metal.cli as module
    context, paths = trials(tmp_path, monkeypatch, two_options(cycles=6))
    monkeypatch.setattr(module, 'discover_phenix', lambda *a,**kw: pytest.fail('No native discovery'))
    parser = build_parser()
    args = parser.parse_args(['metal','compare-fdp',str(context.run),'--trial',str(paths[0]),'--trial',str(paths[1])])
    assert execute(args)==0
    assert 'does not prove convergence' in capsys.readouterr().out
    args = parser.parse_args(['metal','verify-fdp-comparison',str(context.run),'--comparison','Metal/fdp_comparison_001','--json'])
    assert execute(args)==0
    assert json.loads(capsys.readouterr().out)['status']=='COMPARISON_REVIEW'


def test_different_geometry_lineages_are_not_pooled_even_with_identical_coordinates(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from nasolve.metal.geometry import prepare_geometry
    context, paths = trials(tmp_path, monkeypatch, two_options())
    geometry = prepare_geometry(context.run, 'Metal/hypothesis_001')
    native = SimpleNamespace(version='2.2.1', executables={'phenix.python':'unused','phenix.mtz.dump':'unused'}, environment={})
    doc = run_fdp(context.run, Path(geometry['files']['model']['relative_path']).parent,
                  native=native, fit_nodes=['m1'], occupancies={'m1':.6})
    with pytest.raises(RecipeError, match='same geometry'):
        build_comparison(context.run, [paths[0], Path(doc['files']['result.json']['relative_path']).parent])


@pytest.mark.parametrize('axis,value', [('minimizer_cycles',4), ('max_iterations',30)])
def test_optimizer_budget_axes_are_compared_without_pooling_other_changes(tmp_path, monkeypatch, axis, value):
    context, paths = trials(tmp_path, monkeypatch, two_options(**{axis:value}))
    data = report(context.run, build_comparison(context.run, paths))
    for name, groups in data['sensitivity'].items():
        assert all(g['status']==('COMPARED' if name==axis else 'NOT_TESTED') for g in groups)
