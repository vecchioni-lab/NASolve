"""Bounded per-restraint versus accumulated native plane-gradient evidence."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

POLICY_ID = 'cif-native-parallelity-accumulation-audit-v1'
STEPS = (1e-3, 1e-4, 1e-5, 1e-6)
MAX_PAIRS = 7000


def _norm(values):
    return math.sqrt(math.fsum(v*v for v in values))


def _close(a, b):
    return math.isclose(a, b, abs_tol=1e-8, rel_tol=1e-10)


def _vector_agrees(a, b):
    return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))


def _validate(points, proxy):
    if not points or any(len(p) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in p) for p in points):
        raise ValueError('Require complete finite coordinates')
    for key in ['i_seqs', 'j_seqs']:
        indices = proxy[key]
        if len(indices) < 3 or len(set(indices)) != len(indices) or any(type(i) is not int or not 0 <= i < len(points) for i in indices):
            raise ValueError('Require unambiguous plane atom indices')
    if type(proxy['weight']) not in (int, float) or not math.isfinite(proxy['weight']) or proxy['weight'] <= 0:
        raise ValueError('Require positive finite weight')
    if proxy.get('target_angle_deg') != 0 or proxy.get('slack') != 0 or proxy.get('top_out') is not False:
        raise ValueError('This bounded audit supports zero-target, zero-slack, non-top-out planes only')
    if not math.isfinite(proxy.get('limit', 1)) or proxy.get('limit', 1) < 1:
        raise ValueError('Invalid plane limit')


def toy_planes():
    """Asymmetric tilted planes exercise equal and unequal membership sizes."""
    shape = [(0., 0.), (1.4, .1), (.4, 1.1), (-.8, .5), (-.3, -.9), (.9, -.6)]
    angle = math.radians(31.)
    result = []
    for ni, nj in [(4, 4), (4, 6), (6, 4)]:
        first = [[x, y, .017*(k % 3-1)] for k, (x, y) in enumerate(shape[:ni])]
        second = [[2.1+x, 3.2+y*math.cos(angle)-.013*(k % 3-1)*math.sin(angle),
                   .8+y*math.sin(angle)+.013*(k % 3-1)*math.cos(angle)] for k, (x, y) in enumerate(shape[:nj])]
        result.append({'label':f'tilted_{ni}_{nj}', 'points':first+second,
                       'proxy':{'i_seqs':list(range(ni)), 'j_seqs':list(range(ni, ni+nj)),
                                'weight':3.7, 'target_angle_deg':0., 'slack':0., 'limit':1., 'top_out':False, 'origin_id':0}})
    return result


def audit_parallelities(evaluate, coordinate_cases, proxies, *, max_pairs=MAX_PAIRS):
    """Callback returns one-restraint and singleton-container energies/gradients.

    Native calls are isolated controls, with no adopted objective or coordinates.
    Each callback pair invokes two residual kernels; the bound is explicit.
    """
    if not coordinate_cases or len(coordinate_cases) > 2 or not 1 <= len(proxies) <= 64:
        raise ValueError('Require one/two coordinate cases and at most 64 proxies')
    if type(max_pairs) is not int or not 1 <= max_pairs <= MAX_PAIRS:
        raise ValueError('Invalid native evaluation budget')
    for points in coordinate_cases.values():
        for proxy in proxies:
            _validate(points, proxy)
    result = {'schema_version':1, 'policy_id':POLICY_ID, 'status':'REVIEW', 'analysis_completed':False,
              'model_optimization':'NOT_RUN', 'scientific_approval':'NOT_RUN', 'automatic_adoption':False,
              'step_sizes':list(STEPS), 'directional_tolerance':{'absolute':1e-4, 'relative':1e-4},
              'comparison_tolerance':{'absolute':1e-8, 'relative':1e-10},
              'evaluation_pairs':0, 'max_evaluation_pairs':max_pairs, 'residual_kernels_per_pair':2,
              'cases':{}, 'toy_cases':[],
              'limitations':['Sampled derivatives do not prove convergence or chemistry.',
                             'Swapping plane order and isolated kernels are diagnostic evaluations only.']}

    def call(points, proxy):
        if result['evaluation_pairs'] >= max_pairs:
            raise ValueError('Native evaluation budget exhausted')
        result['evaluation_pairs'] += 1
        raw = evaluate(deepcopy(points), deepcopy(proxy))
        for key in ['single_target', 'accumulated_target']:
            if type(raw[key]) not in (int, float) or not math.isfinite(raw[key]):
                raise ValueError('Require finite residuals')
        for key in ['single_gradient', 'accumulated_gradient']:
            if len(raw[key]) != 3*len(points) or any(type(v) not in (int, float) or not math.isfinite(v) for v in raw[key]):
                raise ValueError('Require complete finite gradients')
        return raw

    def order(points, proxy):
        baseline = call(points, proxy)
        directions = []
        for name, selected in [('i_plane', set(proxy['i_seqs'])), ('j_plane', set(proxy['j_seqs']))]:
            vector = [v if i//3 in selected else 0. for i, v in enumerate(baseline['single_gradient'])]
            source = 'single_restraint_gradient'
            if not _norm(vector):
                vector = [(1. if i % 2 else -1.) if i//3 in selected else 0. for i in range(3*len(points))]
                source = 'alternating_zero_gradient_control'
            length = _norm(vector)
            directions.append((name, source, [v/length for v in vector]))
        vector = [1. if i % 2 else -1. for i in range(3*len(points))]
        directions.append(('alternating_local', 'alternating', [v/_norm(vector) for v in vector]))
        rows = []
        for name, source, vector in directions:
            analytical = {k:math.fsum(v*g for v, g in zip(vector, baseline[k+'_gradient'])) for k in ['single', 'accumulated']}
            samples = []
            for step in STEPS:
                shifted = lambda sign:[[v+sign*step*vector[3*i+j] for j, v in enumerate(p)] for i, p in enumerate(points)]
                plus, minus = call(shifted(1), proxy), call(shifted(-1), proxy)
                sample = {'step':step}
                for kind in ['single', 'accumulated']:
                    numerical = (plus[kind+'_target']-minus[kind+'_target'])/(2*step)
                    error = abs(numerical-analytical[kind]); bound = 1e-4+1e-4*max(abs(numerical), abs(analytical[kind]))
                    sample[kind] = {'plus_target':plus[kind+'_target'], 'minus_target':minus[kind+'_target'],
                                    'numerical':numerical, 'absolute_error':error, 'bound':bound, 'consistent':error <= bound}
                samples.append(sample)
            rows.append({'direction':name, 'basis':source, 'analytical':analytical, 'samples':samples,
                         **{k+'_consistent':any(samples[i][k]['consistent'] and samples[i+1][k]['consistent'] for i in range(3)) for k in ['single', 'accumulated']}})
        repeat = call(points, proxy)
        return {'baseline':baseline, 'repeat':repeat, 'directions':rows,
                'baseline_repeat_consistent':all(_close(repeat[k+'_target'], baseline[k+'_target']) and _vector_agrees(repeat[k+'_gradient'], baseline[k+'_gradient']) for k in ['single', 'accumulated']),
                'energy_agreement':_close(baseline['single_target'], baseline['accumulated_target']),
                'gradient_agreement':_vector_agrees(baseline['single_gradient'], baseline['accumulated_gradient']),
                'gradient_difference_norm':_norm([x-y for x, y in zip(baseline['single_gradient'], baseline['accumulated_gradient'])]),
                **{k+'_derivatives_consistent':all(row[k+'_consistent'] for row in rows) for k in ['single', 'accumulated']}}

    def pair(points, proxy, label):
        indices = list(dict.fromkeys(proxy['i_seqs']+proxy['j_seqs']))
        mapping = {i:j for j, i in enumerate(indices)}
        local = {**deepcopy(proxy), **{key:[mapping[i] for i in proxy[key]] for key in ['i_seqs', 'j_seqs']}}
        original = order([points[i] for i in indices], local)
        swapped = order([points[i] for i in indices], {**local, 'i_seqs':local['j_seqs'], 'j_seqs':local['i_seqs']})
        return {'label':label, 'global_indices':indices, 'proxy':deepcopy(proxy), 'original':original, 'swapped':swapped,
                'swapped_energies_consistent':all(_close(original['baseline'][k+'_target'], swapped['baseline'][k+'_target']) for k in ['single', 'accumulated']),
                **{k+'_swapped_gradients_consistent':_vector_agrees(original['baseline'][k+'_gradient'], swapped['baseline'][k+'_gradient']) for k in ['single', 'accumulated']}}

    def summary(rows):
        orders = [row[order] for row in rows for order in ['original', 'swapped']]
        return {'proxy_count':len(rows), 'orders':len(orders),
                'single_derivatives_consistent':all(row['single_derivatives_consistent'] for row in orders),
                'accumulated_derivatives_consistent':all(row['accumulated_derivatives_consistent'] for row in orders),
                'single_and_accumulated_gradients_agree':all(row['gradient_agreement'] for row in orders),
                'baseline_repeats_consistent':all(row['baseline_repeat_consistent'] for row in orders),
                'swapped_energies_consistent':all(row['swapped_energies_consistent'] for row in rows),
                'swapped_gradients_consistent':all(row['single_swapped_gradients_consistent'] and row['accumulated_swapped_gradients_consistent'] for row in rows),
                'single_derivative_review_orders':sum(not row['single_derivatives_consistent'] for row in orders),
                'accumulated_derivative_review_orders':sum(not row['accumulated_derivatives_consistent'] for row in orders)}

    for label, points in coordinate_cases.items():
        rows = [pair(points, proxy, f'proxy_{i:03d}') for i, proxy in enumerate(proxies)]
        result['cases'][label] = {'proxies':rows, 'summary':summary(rows)}
    result['toy_cases'] = [pair(toy['points'], toy['proxy'], toy['label']) for toy in toy_planes()]
    result['toy_summary'] = summary(result['toy_cases'])
    result['analysis_completed'] = True
    return result


def native_evaluator(geometry_restraints, flex):
    """Call public per-restraint and singleton-container APIs independently."""
    def evaluate(points, spec):
        proxy = geometry_restraints.parallelity_proxy(
            i_seqs=flex.size_t(spec['i_seqs']), j_seqs=flex.size_t(spec['j_seqs']),
            weight=spec['weight'], target_angle_deg=spec['target_angle_deg'], slack=spec['slack'],
            limit=spec['limit'], top_out=spec['top_out'], origin_id=spec['origin_id'])
        sites = flex.vec3_double(points)
        restraint = geometry_restraints.parallelity(sites_cart=sites, proxy=proxy)
        raw = list(restraint.gradients()); indices = spec['i_seqs']+spec['j_seqs']
        if len(raw) != len(indices):
            raise ValueError('Unexpected per-restraint gradient count')
        manual = [0.]*(3*len(points))
        for index, values in zip(indices, raw):
            for axis, value in enumerate(values):
                manual[3*index+axis] += float(value)
        proxies = geometry_restraints.shared_parallelity_proxy(); proxies.append(proxy)
        gradient = flex.vec3_double(len(points), (0., 0., 0.))
        target = geometry_restraints.parallelity_residual_sum(sites_cart=sites, proxies=proxies, gradient_array=gradient)
        return {'single_target':float(restraint.residual()), 'single_gradient':manual,
                'accumulated_target':float(target), 'accumulated_gradient':[float(v) for v in gradient.as_double()]}
    return evaluate


_PARALLELITY_WORKER = r'''from __future__ import print_function
import hashlib,importlib,json,sys,traceback
from pathlib import Path
from parallelity_core import POLICY_ID,audit_parallelities,native_evaluator,_close,_vector_agrees,_norm
from gradient_core import fixed_signature
spec=json.loads(Path(sys.argv[1]).read_text())
result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN'}
try:
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Native inventory bootstrap failed')
    expected=json.loads(Path('expected_inventory.json').read_text());actual=namespace['report']
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):
        raise RuntimeError('Native manager changed before accumulation audit')
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    modules=[importlib.import_module(name) for name in ['scitbx.lbfgs','cctbx.geometry_restraints.flags','cctbx.geometry_restraints.manager','cctbx.geometry_restraints.energies','scitbx_lbfgs_ext','cctbx_geometry_restraints_ext']]
    sources=[{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in modules]
    sig=lambda rows:[(r['module'],r['sha256']) for r in rows]
    if sig(sources)!=sig(spec['expected_numeric_sources']):raise RuntimeError('Native numerical sources changed')
    adapter_sources=[{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in [gr,flex]]
    geo=namespace['geo'];sites=namespace['sites']
    if len(geo.site_symmetry_table.special_position_indices()):raise RuntimeError('Special-position gradient policy unsupported')
    original=fixed_signature(geo,sites)
    if original!=spec['expected_constraint_signature']:raise RuntimeError('Static native constraints differ from saved trial')
    proxies=[]
    for p in geo.parallelity_proxies:
        if p.sym_ops is not None and len(p.sym_ops):raise RuntimeError('Symmetry-bearing plane proxies unsupported by this diagnostic')
        proxies.append({'i_seqs':list(p.i_seqs),'j_seqs':list(p.j_seqs),'weight':float(p.weight),'target_angle_deg':float(p.target_angle_deg),
                        'slack':float(p.slack),'limit':float(p.limit),'top_out':bool(p.top_out),'origin_id':int(p.origin_id)})
    installed=[];source_dir=Path(modules[2].__file__).resolve().parent
    for filename in ['parallelity.h','parallelity_bpl.cpp']:
        path=source_dir/filename
        record={'anchor':'native_geometry_module','path':filename,'status':'UNAVAILABLE'}
        if path.is_file():
            payload=path.read_bytes();destination=Path('installed_source')/filename;destination.parent.mkdir(exist_ok=True);destination.write_bytes(payload)
            record.update(status='RECORDED',sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload))
        installed.append(record)
    batch={}
    for label,points in spec['coordinate_cases'].items():
        vector=flex.vec3_double(points);manual=[0.]*(3*len(points));target=0.
        for p in geo.parallelity_proxies:
            restraint=gr.parallelity(sites_cart=vector,proxy=p);target+=float(restraint.residual())
            for index,values in zip(list(p.i_seqs)+list(p.j_seqs),restraint.gradients()):
                for axis,value in enumerate(values):manual[3*index+axis]+=float(value)
        gradient=flex.vec3_double(len(points),(0.,0.,0.))
        accumulated=float(gr.parallelity_residual_sum(sites_cart=vector,proxies=geo.parallelity_proxies,gradient_array=gradient))
        flat=[float(v) for v in gradient.as_double()];active=flags.flags(default=False);active.parallelity=True
        manager=geo.energies_sites(sites_cart=vector,flags=active,compute_gradients=True,normalization=False)
        manager_gradient=[float(v) for v in manager.gradients.as_double()];captured=spec['captured_baselines'][label]
        if not (_close(accumulated,captured['target']) and _vector_agrees(flat,captured['gradient'])
                and _close(float(manager.target),accumulated) and _vector_agrees(manager_gradient,flat)):
            raise RuntimeError('Captured/native batch parallelity gradients differ')
        batch[label]={'captured_snapshot_match':True,'manager_matches_batch':True,'single_residual_sum':target,'accumulated_residual':accumulated,
                      'energy_agreement':_close(target,accumulated),'manual_gradient':manual,'accumulated_gradient':flat,
                      'gradient_agreement':_vector_agrees(manual,flat),'gradient_difference_norm':_norm([a-b for a,b in zip(manual,flat)])}
    result.update(audit_parallelities(native_evaluator(gr,flex),spec['coordinate_cases'],proxies,max_pairs=spec['max_pairs']))
    result.update(captured_inventory_matches=True,installed_numeric_sources=sources,installed_parallelity_sources=installed,
                  installed_adapter_sources=adapter_sources,
                  full_batch_comparisons=batch,native_parallelity_proxies=proxies,constraint_signature_before=original,
                  constraint_signature_after=fixed_signature(geo,sites))
    if result['constraint_signature_after']!=original:raise RuntimeError('Static native constraints changed')
    for row in sources+adapter_sources:
        if hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Native numerical source changed')
    for row in installed:
        path=source_dir/row['path']
        if row['status']=='RECORDED' and (not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']):raise RuntimeError('Installed C++ source changed')
    result['status']='REVIEW'
except Exception as exc:
    result.update(status='FAILED',error=type(exc).__name__+': '+str(exc));traceback.print_exc()
Path('parallelity_result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def run_native_parallelity_audit(model, dictionaries, phils, expected, coordinate_cases, captured_baselines,
        expected_numeric_sources, expected_constraint_signature, output_parent, executable, *, environment, phenix_version, timeout_seconds=1200):
    """Own a separate native job; freeze and preserve every existing input."""
    from .cif_native_validation import _NATIVE_WORKER, _artifact, _stop, NATIVE_POLICY_ID
    from .cif_fixed_geometry import _model, _fixed_policy, _points
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise ValueError('Invalid native timeout')
    if not _fixed_policy(expected) or not phenix_version:
        raise ValueError('Require captured explicit policy and native version')
    _model(expected, model, coordinates_match=True)
    if set(coordinate_cases) != {'full_precision', 'pdb_rounded'} or set(captured_baselines) != set(coordinate_cases):
        raise ValueError('Require both captured coordinate/baseline cases')
    for points in coordinate_cases.values():
        _points(points, expected['atom_count'])
    paths = [Path(p).resolve() for p in [model, *dictionaries, *phils]]; parent = Path(output_parent).resolve()
    if not dictionaries or len(paths) != len(set(paths)) or any(parent == p.parent or p.parent in parent.parents for p in paths):
        raise ValueError('Require distinct inputs and separate output')
    original = [p.read_bytes() for p in paths]; parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='cif-parallelity-audit-', dir=parent)); (work/'inputs').mkdir()
    frozen = []; inputs = []
    for i, (path, data) in enumerate(zip(paths, original)):
        role = 'model' if i == 0 else 'dictionary' if i <= len(dictionaries) else 'phil'
        target = work/'inputs'/(f'{i:03d}_{role}'+path.suffix); target.write_bytes(data); frozen.append(target)
        inputs.append({'role':role, 'input_index':i, 'source_provenance':str(path), **_artifact(target, work)})
    native = {'policy_id':NATIVE_POLICY_ID, 'model':frozen[0].relative_to(work).as_posix(),
              'dictionaries':[p.relative_to(work).as_posix() for p in frozen[1:1+len(dictionaries)]],
              'phil_files':[p.relative_to(work).as_posix() for p in frozen[1+len(dictionaries):]],
              'phil_namespace_policy':'refinement-root-to-interpreter-v1', 'inventory_detail':'linked', 'policy_inventory':True}
    spec = {'policy_id':POLICY_ID, 'coordinate_cases':coordinate_cases, 'captured_baselines':captured_baselines,
            'expected_numeric_sources':expected_numeric_sources, 'expected_constraint_signature':expected_constraint_signature, 'max_pairs':MAX_PAIRS}
    for name, value in [('native_spec.json', native), ('expected_inventory.json', expected), ('parallelity_spec.json', spec)]:
        (work/name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')
    (work/'native_worker.py').write_text(_NATIVE_WORKER); (work/'parallelity_worker.py').write_text(_PARALLELITY_WORKER)
    (work/'parallelity_core.py').write_bytes(Path(__file__).read_bytes())
    (work/'gradient_core.py').write_bytes(Path(__file__).with_name('cif_gradient_audit.py').read_bytes())
    executable = Path(executable).resolve(); command = [str(executable), '-B', 'parallelity_worker.py', 'parallelity_spec.json']
    receipt = {'schema_version':1, 'audit_kind':'cif_native_parallelity_accumulation_audit', 'policy_id':POLICY_ID, 'status':'FAILED',
               'native_directory':str(work), 'inputs':inputs, 'command':command, 'phenix_version':phenix_version,
               'executable_provenance':str(executable), 'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
               'model_optimization':'NOT_RUN', 'automatic_adoption':False, 'scientific_approval':'NOT_RUN',
               'execution':{'status':'NOT_RUN', 'timeout_seconds':timeout_seconds}}
    started = time.monotonic()
    try:
        with (work/'parallelity.log').open('xb') as log:
            process = subprocess.Popen(command, cwd=work, env=dict(environment), stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name == 'posix')
            try:
                code = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _stop(process); receipt['execution'].update(status='TIMED_OUT', returncode=process.returncode)
            except BaseException:
                _stop(process); raise
            else:
                receipt['execution'].update(status='COMPLETED' if code == 0 else 'FAILED', returncode=code)
                result = json.loads((work/'parallelity_result.json').read_text()); receipt['result'] = result
                if (code == 0 and result.get('status') == 'REVIEW' and result.get('policy_id') == POLICY_ID
                        and result.get('analysis_completed') and result.get('captured_inventory_matches')
                        and result.get('model_optimization') == 'NOT_RUN' and result.get('automatic_adoption') is False
                        and set(result.get('cases', {})) == set(coordinate_cases) and 0 < result.get('evaluation_pairs', 0) <= MAX_PAIRS
                        and result.get('constraint_signature_before') == result.get('constraint_signature_after') == expected_constraint_signature):
                    receipt['status'] = 'REVIEW'
                else:
                    receipt['error'] = result.get('error', 'Incomplete fixed-manager plane evidence')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        receipt.update(error=str(exc)); receipt['execution']['status'] = 'FAILED'
    receipt['source_preserved'] = all(p.is_file() and p.read_bytes() == data for p, data in zip(paths, original))
    receipt['frozen_inputs_preserved'] = all(p.is_file() and p.read_bytes() == data for p, data in zip(frozen, original))
    if not receipt['source_preserved'] or not receipt['frozen_inputs_preserved']:
        receipt.update(status='FAILED', error='Original or frozen inputs changed')
    receipt['execution']['elapsed_seconds'] = round(time.monotonic()-started, 6)
    receipt['outputs'] = [_artifact(p, work) for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):
        receipt.update(status='FAILED', error='Unexpected output symlink')
    (work/'parallelity_receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False)+'\n')
    return receipt
