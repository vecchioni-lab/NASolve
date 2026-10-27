"""Bounded recipe-only geometry, immutable parents and portable replay."""
import json
from pathlib import Path
import hashlib
import math
import os
import shutil
import subprocess
import sys

import pytest

from nasolve.metal import Recipe, RecipeError
from nasolve.metal.context import read_pdb
from nasolve.metal.geometry import prepare_geometry, verify_geometry
from nasolve.metal.materialize import build_hypothesis
from nasolve.metal.recipe import digest
from tests.test_metal_materialize import control


def built(tmp_path, **kwargs):
    context, recipe, plan = control(tmp_path, **kwargs)
    plan['sites'][0]['xyz'] = [2.6, .3, .2]
    parent = build_hypothesis(context, recipe, plan)
    return context, parent, context.run / Path(parent['files']['model']['relative_path']).parent


def test_geometry_moves_only_metal_and_reports_remaining_freedom(tmp_path):
    context, parent, directory = built(tmp_path)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    result = prepare_geometry(context.run, directory)
    assert result['status'] == 'GEOMETRY_REVIEW' and result['native_ready'] is False
    assert result['parent']['hypothesis_id'] == parent['hypothesis_id']
    evidence = json.loads((context.run/result['files']['result']['relative_path']).read_text())
    assert evidence['selection'] == 'proposed_metal_coordinates'
    assert evidence['selected']['objective'] < evidence['initial']['objective'] * .001
    assert evidence['selected']['local_unconstrained_dimensions'] == 2
    model = context.run/result['files']['model']['relative_path']
    initial, final = read_pdb(directory/'model.pdb'), read_pdb(model)
    assert initial.snapshot.atoms[:-1] == final.snapshot.atoms[:-1]
    assert initial.to_dict()['atomic_state'] == final.to_dict()['atomic_state']
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    assert verify_geometry(context.run, model.parent) == result
    assert not (context.run/'AutoRefine').exists()


def evidence(context, result):
    return json.loads((context.run/result['files']['result']['relative_path']).read_text())


def test_two_distances_and_angle_recover_known_geometry_without_claiming_uniqueness(tmp_path):
    context, recipe, plan = control(tmp_path)
    doc = recipe.to_dict()
    row = doc['restraints'][0]
    row['target'] = math.sqrt(5)
    doc['restraints'] += [dict(row, id='r2', nodes=['d2', 'm1']),
        dict(row, id='a', kind='angle', nodes=['d1', 'm1', 'd2'], target=math.degrees(math.acos(-.6)), sigma=2., unit='degree')]
    recipe = Recipe(doc); plan['recipe_sha256'] = recipe.sha256
    plan['sites'][0]['xyz'] = [2.6, .3, .2]
    parent = build_hypothesis(context, recipe, plan)
    result = prepare_geometry(context.run, Path(parent['files']['model']['relative_path']).parent)
    report = evidence(context, result)
    assert report['selected']['objective'] < .001
    assert report['selected']['local_unconstrained_dimensions'] == 1
    atom = read_pdb(context.run/result['files']['model']['relative_path']).snapshot.atoms[-1]
    assert atom.xyz[0] == pytest.approx(2, abs=.001)
    assert math.hypot(*atom.xyz[1:]) == pytest.approx(1, abs=.001)


def test_nonplanar_six_metal_cluster_can_prepare_all_sites(tmp_path):
    context, recipe, plan = control(tmp_path, metals=('Ag',)*6)
    ideal = [[3, 0, 0], [1, 0, 0], [2, 1, 0], [2, -1, 0], [2, 0, 1], [2, 0, -1]]
    doc = recipe.to_dict(); doc['restraints'] = []
    for i, site in enumerate(plan['sites']):
        site['xyz'] = [v+.1*(1+(i+j)%3) for j, v in enumerate(ideal[i])]
        for j in range(i):
            doc['restraints'].append({'id': f'r{i}{j}', 'kind': 'distance', 'nodes': [f'm{i+1}', f'm{j+1}'],
                'set_id': 's', 'enabled': True, 'target': math.dist(ideal[i], ideal[j]), 'sigma': .1,
                'unit': 'angstrom', 'source': {'kind': 'user', 'note': 'Octahedron numerical control'}})
    recipe = Recipe(doc); plan['recipe_sha256'] = recipe.sha256
    parent = build_hypothesis(context, recipe, plan)
    result = prepare_geometry(context.run, Path(parent['files']['model']['relative_path']).parent)
    report = evidence(context, result)
    assert report['selected']['objective'] < .001
    assert report['selected']['local_unconstrained_dimensions'] == 6  # rigid body remains free
    atoms = read_pdb(context.run/result['files']['model']['relative_path']).snapshot.atoms[-6:]
    assert abs(atoms[4].xyz[2]-atoms[5].xyz[2]) > 1.9


def test_locked_and_floating_sites_keep_exact_records(tmp_path):
    context, recipe, plan = control(tmp_path, metals=('Au', 'Ag', 'Hg'))
    doc = recipe.to_dict(); doc['restraints'].append(dict(doc['restraints'][0], id='r2', nodes=['d2', 'm2']))
    recipe = Recipe(doc); plan['recipe_sha256'] = recipe.sha256
    plan['sites'][0]['xyz'] = [2.6, .3, .2]
    parent = build_hypothesis(context, recipe, plan)
    directory = context.run/Path(parent['files']['model']['relative_path']).parent
    result = prepare_geometry(context.run, directory, mobile_nodes=['m1'])
    before = read_pdb(directory/'model.pdb'); after = read_pdb(context.run/result['files']['model']['relative_path'])
    assert before.snapshot.atoms[-2:] == after.snapshot.atoms[-2:]
    assert set(evidence(context, result)['selected_metal_shifts_A']) == {'m1'}
    assert verify_geometry(context.run, 'Metal/geometry_001') == result


@pytest.mark.parametrize('parameters', [dict(max_iterations=0), dict(max_iterations=True), dict(max_iterations=301),
    dict(max_shift_A=0), dict(max_shift_A=float('nan')), dict(max_shift_A=5.01), dict(max_shift_A=True),
    dict(mobile_nodes=[]), dict(mobile_nodes=['d1']), dict(mobile_nodes=['m1', 'm1']), dict(mobile_nodes=['missing'])])
def test_invalid_parameters_allocate_nothing(tmp_path, parameters):
    context, _, directory = built(tmp_path)
    with pytest.raises(RecipeError): prepare_geometry(context.run, directory, **parameters)
    assert not list((context.run/'Metal').glob('geometry_*'))


def test_floating_hypothesis_has_no_optimizable_sites(tmp_path):
    context, _, directory = built(tmp_path, restrained=False)
    with pytest.raises(RecipeError, match='restrained'): prepare_geometry(context.run, directory)


def test_bounded_move_and_iteration_limit_are_reported_without_overshoot(tmp_path):
    context, _, directory = built(tmp_path)
    result = prepare_geometry(context.run, directory, max_iterations=1, max_shift_A=.1)
    report = evidence(context, result)
    assert report['optimization']['stopping'] == 'ITERATION_LIMIT'
    assert report['optimization']['iterations'] == 1
    assert report['selected_metal_shifts_A']['m1'] <= .1
    assert report['selected']['objective'] <= report['initial']['objective']


def test_satisfied_start_retains_source_and_stopping_note(tmp_path):
    context, recipe, plan = control(tmp_path)
    parent = build_hypothesis(context, recipe, plan)
    directory = context.run/Path(parent['files']['model']['relative_path']).parent
    result = prepare_geometry(context.run, directory)
    report = evidence(context, result)
    assert report['selection'] == 'parent_coordinates'
    assert report['retained_parent_reason'] == 'NO_SERIALIZED_CHANGE'
    assert (context.run/result['files']['model']['relative_path']).read_bytes() == (directory/'model.pdb').read_bytes()


def test_rounding_cannot_increase_the_selected_objective(tmp_path, monkeypatch):
    import nasolve.metal.geometry as module
    context, _, directory = built(tmp_path)
    # Deliberately inject a bad optimizer endpoint to exercise publication's
    # independent objective/readback check, not the numerical search itself.
    def worse(self, *args):
        return [3., .3, .2], {'stopping': 'CONTROL', 'iterations': 0}
    monkeypatch.setattr(module.Problem, 'optimize', worse)
    report = evidence(context, prepare_geometry(context.run, directory))
    assert report['selection'] == 'parent_coordinates'
    assert report['retained_parent_reason'] == 'SERIALIZED_OBJECTIVE_INCREASE'


@pytest.mark.parametrize('target', ['model', 'result', 'parameters', 'typed_manifest', 'rehashed_model', 'parent'])
def test_tampering_and_rehashed_derivatives_are_rejected(tmp_path, target):
    context, _, directory = built(tmp_path)
    result = prepare_geometry(context.run, directory)
    output = (context.run/result['files']['model']['relative_path']).parent
    if target == 'typed_manifest':
        result['native_ready'] = 0
        (output/'manifest.json').write_text(json.dumps(result))
    elif target == 'parent':
        with (directory/'model.pdb').open('a') as handle: handle.write('REMARK changed\n')
    else:
        key = 'model' if target == 'rehashed_model' else target
        path = context.run/result['files'][key]['relative_path']
        with path.open('a') as handle: handle.write('\n')
        if target == 'rehashed_model':
            result['files']['model'].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size=path.stat().st_size)
            result.pop('geometry_id'); result['geometry_id'] = digest(result)
            (output/'manifest.json').write_text(json.dumps(result))
    with pytest.raises(RecipeError): verify_geometry(context.run, output)


def test_new_number_for_each_trial_and_failed_publication_is_retained(tmp_path, monkeypatch):
    import nasolve.metal.geometry as module
    context, _, directory = built(tmp_path)
    original = module._manifest
    def fail(*args): raise OSError('Publication control')
    monkeypatch.setattr(module, '_manifest', fail)
    with pytest.raises(OSError): prepare_geometry(context.run, directory)
    assert (context.run/'Metal/geometry_001/failure.json').exists()
    with pytest.raises(RecipeError): verify_geometry(context.run, 'Metal/geometry_001')
    monkeypatch.setattr(module, '_manifest', original)
    result = prepare_geometry(context.run, directory)
    assert 'geometry_002/' in result['files']['model']['relative_path']
    assert verify_geometry(context.run, 'Metal/geometry_002') == result


def test_cli_prints_linked_before_after_rows_and_verifies_json(tmp_path, capsys):
    from nasolve.cli import main
    context, _, directory = built(tmp_path)
    assert main(['metal', 'geometry', str(context.run), '--hypothesis', str(directory)]) == 0
    text = capsys.readouterr().out
    assert 'Recipe objective:' in text and 'Residual (sigma)' in text and 'local unconstrained dimensions: 2' in text
    assert main(['metal', 'verify-geometry', str(context.run), '--geometry', 'Metal/geometry_001', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['kind'] == 'metal-geometry-trial'
    assert main(['metal', 'geometry', str(context.run), '--hypothesis', str(directory), '--mobile', 'd1']) == 2


def test_source_removed_relocation_replays_without_native_or_original_paths(tmp_path):
    original = tmp_path/'original'; context, _, directory = built(original)
    result = prepare_geometry(context.run, directory)
    shutil.copytree(Path(__file__).resolve().parents[1]/'src/nasolve', original/'src/nasolve', ignore=shutil.ignore_patterns('__pycache__'))
    relocated = tmp_path/'relocated'; shutil.move(original, relocated)
    assert not original.exists()
    script = '''import json,sys,subprocess
from pathlib import Path
import nasolve.metal.geometry as module
assert Path(module.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
def forbidden(*a, **k): raise AssertionError('No native execution during replay')
subprocess.Popen=forbidden
print(json.dumps(module.verify_geometry(Path(sys.argv[1])/'dataset/AutoMR/run_001', 'Metal/geometry_001')))
'''
    check = subprocess.run([sys.executable, '-B', '-c', script, str(relocated)], cwd=tmp_path,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(relocated/'src')),
        capture_output=True, text=True, timeout=30)
    assert check.returncode == 0, check.stderr
    assert json.loads(check.stdout) == result


def test_changed_observations_and_symlinked_report_are_rejected(tmp_path):
    context, _, directory = built(tmp_path)
    result = prepare_geometry(context.run, directory)
    output = (context.run/result['files']['model']['relative_path']).parent
    report = output/'manifest.json'; saved = report.read_bytes()
    elsewhere = tmp_path/'report.json'; elsewhere.write_bytes(saved)
    report.unlink(); report.symlink_to(elsewhere)
    with pytest.raises(RecipeError, match='symlink'): verify_geometry(context.run, output)
    report.unlink(); report.write_bytes(saved)
    (context.run.parent.parent/'observations.mtz').write_bytes(b'changed observations')
    with pytest.raises(RecipeError, match='checksum'): verify_geometry(context.run, output)


def test_anisou_nonmobile_records_and_metal_charge_are_preserved(tmp_path):
    from nasolve.metal.context import load_run_context
    context, recipe, plan = control(tmp_path)
    path = context.run/'model.pdb'; raw = path.read_text(); line = raw.splitlines(keepends=True)[1]
    anisou = 'ANISOU'+line[6:28]+''.join(f'{v:7d}' for v in [1000, 2000, 3000, 100, 200, 300])+line[70:]
    raw = raw.replace(line, line+anisou); path.write_text(raw)
    report_path = context.run/'report.json'; report = json.loads(report_path.read_text())
    report['postmr']['prepared_sha256'] = hashlib.sha256(raw.encode()).hexdigest(); report_path.write_text(json.dumps(report))
    context = load_run_context(context.run, records=context.roles.records())
    plan['context_id'] = context.to_dict()['context_id']; plan['sites'][0].update(xyz=[2.6, .3, .2], formal_charge=2)
    parent = build_hypothesis(context, recipe, plan)
    directory = context.run/Path(parent['files']['model']['relative_path']).parent
    result = prepare_geometry(context.run, directory)
    original = (directory/'model.pdb').read_bytes().splitlines(keepends=True)
    prepared = (context.run/result['files']['model']['relative_path']).read_bytes().splitlines(keepends=True)
    for a, b in zip(original, prepared):
        if a[17:20].strip() == b'HG': assert a[:30]+a[54:] == b[:30]+b[54:]
        else: assert a == b
