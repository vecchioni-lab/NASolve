"""Fresh initial derivatives for a qualified full-scaffold dictionary replacement.

This audit preserves native targets and the existing qualified plane correction.
It produces an initial-only proof accepted by the unchanged bounded trial API;
it does not optimize, adopt files or compare different dictionary objectives.
"""
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .cif_candidate_usability import energy_inventory_checks
from .cif_corrected_geometry import (REPLACEMENT_AUDIT_ID, QUALIFIED_CORRECTION_SHA256,
    replacement_manager_view, validate_replacement_manager_bridge, validate_gradient_qualification)

POLICY_ID = REPLACEMENT_AUDIT_ID


_REPLACEMENT_WORKER = r'''from __future__ import print_function
import hashlib,importlib,json,math,sys,traceback
from pathlib import Path
from correction_core import evaluate_fixed_native,ORDER_CORRECTION_ID
from gradient_core import audit_gradients,fixed_signature
from corrected_geometry_core import (replacement_manager_view,validate_replacement_manager_bridge,
    validate_gradient_qualification,QUALIFIED_CORRECTION_SHA256,NUMERIC_MODULES,ADAPTER_MODULES)
spec=json.loads(Path(sys.argv[1]).read_text())
result={'schema_version':1,'policy_id':spec['policy_id'],'status':'FAILED','model_optimization':'NOT_RUN',
    'automatic_adoption':False,'scientific_approval':'NOT_RUN','normalization':False,'analysis_completed':False}
try:
    parent=json.loads(Path('parent_gradient_qualification.json').read_text())
    expected=json.loads(Path('expected_inventory.json').read_text())
    bridge=spec['manager_bridge']
    validate_replacement_manager_bridge(bridge,parent,expected['atom_count'])
    if hashlib.sha256(Path('correction_core.py').read_bytes()).hexdigest()!=QUALIFIED_CORRECTION_SHA256:
        raise RuntimeError('Qualified correction source changed')
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Native replacement bootstrap failed')
    actual=namespace['report']
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):
        raise RuntimeError('Native replacement manager differs from qualified capture')
    if replacement_manager_view(actual)!=bridge['replacement']:
        raise RuntimeError('Native replacement plane inventory/index basis differs')
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    modules=[importlib.import_module(name) for name in NUMERIC_MODULES]
    def fingerprints(values):return [{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),
        'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in values]
    sources,adapters=fingerprints(modules),fingerprints([gr,flex])
    sig=lambda rows:[(r['module'],r['sha256']) for r in rows]
    if sig(sources)!=sig(parent['installed_numeric_sources']):raise RuntimeError('Qualified native numerical sources changed')
    if sig(adapters)!=sig(parent['installed_adapter_sources']):raise RuntimeError('Qualified native adapter sources changed')
    source_dir=Path(modules[2].__file__).resolve().parent;cpp=[]
    for row in parent['installed_parallelity_sources']:
        if row.get('status')!='RECORDED' or row.get('path') not in {'parallelity.h','parallelity_bpl.cpp'}:
            raise RuntimeError('Unpinned native plane source')
        data=(source_dir/row['path']).read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise RuntimeError('Qualified native plane source changed')
        target=Path('installed_source')/row['path'];target.parent.mkdir(exist_ok=True);target.write_bytes(data);cpp.append(row)
    geo,sites=namespace['geo'],namespace['sites']
    if len(geo.site_symmetry_table.special_position_indices()):raise RuntimeError('Special-position replacement gradients unsupported')
    points=[list(p) for p in sites]
    if points!=expected['geometry']['sites_cart_exact']:raise RuntimeError('Replacement coordinates differ')
    signature=fixed_signature(geo,sites)
    proxies=[{'i_seqs':list(p.i_seqs),'j_seqs':list(p.j_seqs),'weight':float(p.weight),
        'target_angle_deg':float(p.target_angle_deg),'slack':float(p.slack),'limit':float(p.limit),
        'top_out':bool(p.top_out),'origin_id':int(p.origin_id)} for p in geo.parallelity_proxies]
    if proxies!=parent['native_parallelity_proxies']:raise RuntimeError('Qualified native plane parameters differ')
    active=flags.flags(default=True)
    raw=geo.energies_sites(sites_cart=sites,flags=active,compute_gradients=True,normalization=False)
    rebuilt={'target':float(raw.target),'gradient':[float(g) for g in raw.gradients.as_double()]}
    captured=expected['energy_inventory']['snapshots'][0]
    captured={k:captured[k] for k in ['target','gradient']}
    close=lambda a,b:math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
    if not(close(captured['target'],rebuilt['target']) and len(captured['gradient'])==len(rebuilt['gradient'])==3*expected['atom_count']
        and all(close(a,b) for a,b in zip(captured['gradient'],rebuilt['gradient']))):
        raise RuntimeError('Captured replacement raw target or named gradient differs')
    stats={'max_energy_change':0.,'correction_evaluations':0}
    def evaluate(values,family):
        active=flags.flags(default=family=='all')
        if family!='all':setattr(active,family,True)
        value=evaluate_fixed_native(geo,values,active,gr,flex,plane_order_safe=True)
        change=abs(value['target']-value['native_target']);stats['max_energy_change']=max(stats['max_energy_change'],change)
        if change:raise RuntimeError('Plane correction changed native replacement energy')
        if value['parallelity_correction']['applied']:stats['correction_evaluations']+=1
        return value
    result.update(audit_gradients(evaluate,{'initial':points},spec['selected_indices'],
        references={'initial':{'target':captured['target']}},max_calls=spec['max_calls']))
    result.update(policy_id=spec['policy_id'],parent_qualification=parent,manager_bridge=bridge,
        raw_snapshot={'captured':captured,'rebuilt':rebuilt},native_parallelity_proxies=proxies,
        correction_policy_id=ORDER_CORRECTION_ID,correction_core_sha256=QUALIFIED_CORRECTION_SHA256,
        correction_qualification='SAMPLED_NATIVE_DERIVATIVES_PASS' if result['cases']['initial']['sampled_gradients_consistent'] else 'DERIVATIVE_REVIEW',
        plane_order_safe=True,normalization=False,captured_inventory_matches=True,
        installed_numeric_sources=sources,installed_adapter_sources=adapters,installed_parallelity_sources=cpp,
        constraint_signature_before=signature,constraint_signature_after=fixed_signature(geo,sites),
        correction_statistics=stats,preflight_native_evaluations=1)
    if points!=[list(p) for p in sites] or result['constraint_signature_after']!=signature:
        raise RuntimeError('Replacement audit changed coordinates or fixed native restraints')
    for row in sources+adapters:
        if hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:
            raise RuntimeError('Native replacement numerical source changed during audit')
    for row in cpp:
        if hashlib.sha256((source_dir/row['path']).read_bytes()).hexdigest()!=row['sha256']:
            raise RuntimeError('Native plane source changed during replacement audit')
    validate_gradient_qualification(result,expected['atom_count'])
    result['status']='REVIEW'
except Exception as exc:
    result.update(status='FAILED',error=type(exc).__name__+': '+str(exc));traceback.print_exc()
Path('replacement_gradient_result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def run_initial_replacement_audit(model, dictionaries, phils, expected, parent_proof, parent_inventory,
        selected_indices, output_parent, executable, *, environment, phenix_version,
        timeout_seconds=600, max_calls=2000):
    """Freeze explicit inputs and require a fresh initial-only corrected audit."""
    from .cif_native_validation import _NATIVE_WORKER, _artifact, _stop, NATIVE_POLICY_ID
    from .cif_fixed_geometry import _model, _fixed_policy
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise ValueError('Replacement timeout must be an integer from 1 to 3600 seconds')
    if type(max_calls) is not int or not 1 <= max_calls <= 2000:
        raise ValueError('Replacement initial audit budget must be 1 to 2000 evaluations')
    if (not phenix_version or not _fixed_policy(expected) or not _fixed_policy(parent_inventory)
            or not all(energy_inventory_checks(expected).values())):
        raise ValueError('Require a fixed native replacement policy and finite captured raw evaluations')
    _model(expected, Path(model), coordinates_match=True)
    if (not 1 <= len(selected_indices) <= 6 or len(set(selected_indices)) != len(selected_indices)
            or any(type(i) is not int or not 0 <= i < expected['atom_count'] for i in selected_indices)):
        raise ValueError('Require one to six explicit native derivative probe indices')
    bridge = {'previous': replacement_manager_view(parent_inventory), 'replacement': replacement_manager_view(expected)}
    validate_replacement_manager_bridge(bridge, parent_proof, expected['atom_count'])
    correction = Path(__file__).with_name('cif_parallelity_correction.py')
    if sha256(correction.read_bytes()).hexdigest() != QUALIFIED_CORRECTION_SHA256:
        raise ValueError('Qualified correction source changed')
    paths = [Path(p).resolve() for p in [model, *dictionaries, *phils]]
    parent = Path(output_parent).resolve()
    if (not dictionaries or len(paths) != len(set(paths))
            or any(parent == p.parent or p.parent in parent.parents for p in paths)):
        raise ValueError('Require distinct native inputs and a separate owned audit directory')
    original = [p.read_bytes() for p in paths]
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='cif-replacement-gradient-', dir=parent)); (work/'inputs').mkdir()
    frozen, inputs = [], []
    for i, (path, data) in enumerate(zip(paths, original)):
        role = 'model' if i == 0 else 'dictionary' if i <= len(dictionaries) else 'phil'
        target = work/'inputs'/(f'{i:03d}_{role}' + path.suffix); target.write_bytes(data); frozen.append(target)
        inputs.append({'input_index': i, 'role': role, 'source_provenance': str(path), **_artifact(target, work)})
    native = {'policy_id': NATIVE_POLICY_ID, 'model': frozen[0].relative_to(work).as_posix(),
        'dictionaries': [p.relative_to(work).as_posix() for p in frozen[1:1+len(dictionaries)]],
        'phil_files': [p.relative_to(work).as_posix() for p in frozen[1+len(dictionaries):]],
        'phil_namespace_policy': 'refinement-root-to-interpreter-v1', 'inventory_detail': 'linked', 'policy_inventory': True}
    spec = {'policy_id': POLICY_ID, 'manager_bridge': bridge, 'selected_indices': list(selected_indices), 'max_calls': max_calls}
    for name, value in [('native_spec.json', native), ('replacement_gradient_spec.json', spec),
            ('expected_inventory.json', expected), ('parent_gradient_qualification.json', parent_proof)]:
        (work/name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    (work/'native_worker.py').write_text(_NATIVE_WORKER)
    (work/'replacement_gradient_worker.py').write_text(_REPLACEMENT_WORKER)
    for name, source in [('correction_core.py', 'cif_parallelity_correction.py'), ('gradient_core.py', 'cif_gradient_audit.py'),
                         ('corrected_geometry_core.py', 'cif_corrected_geometry.py')]:
        (work/name).write_bytes(Path(__file__).with_name(source).read_bytes())
    executable = Path(executable).resolve()
    command = [str(executable), '-B', 'replacement_gradient_worker.py', 'replacement_gradient_spec.json']
    receipt = {'schema_version': 1, 'audit_kind': 'cif_replacement_initial_gradient_qualification', 'policy_id': POLICY_ID,
        'status': 'FAILED', 'native_directory': str(work), 'inputs': inputs, 'command': command,
        'executable_provenance': str(executable), 'executable_sha256': sha256(executable.read_bytes()).hexdigest(),
        'phenix_version': phenix_version, 'correction_core_sha256': QUALIFIED_CORRECTION_SHA256,
        'model_optimization': 'NOT_RUN', 'automatic_adoption': False, 'scientific_approval': 'NOT_RUN',
        'execution': {'status': 'NOT_RUN', 'timeout_seconds': timeout_seconds}}
    started = time.monotonic()
    try:
        with (work/'replacement_gradient.log').open('xb') as log:
            process = subprocess.Popen(command, cwd=work, env=dict(environment), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name == 'posix')
            try: code = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _stop(process); receipt['execution'].update(status='TIMED_OUT', returncode=process.returncode)
            except BaseException: _stop(process); raise
            else:
                receipt['execution'].update(status='COMPLETED' if code == 0 else 'FAILED', returncode=code)
                result_path = work/'replacement_gradient_result.json'
                if not result_path.is_file() or result_path.is_symlink():
                    raise ValueError('Worker omitted regular replacement-gradient evidence')
                result = json.loads(result_path.read_text()); receipt['result'] = result
                if result.get('status') != 'REVIEW' or code != 0:
                    raise ValueError(result.get('error', 'Replacement initial gradients remain unqualified'))
                validate_gradient_qualification(result, expected['atom_count'])
                if (result['parent_qualification'] != parent_proof or result['manager_bridge'] != bridge
                        or result['selected_indices'] != list(selected_indices)):
                    raise ValueError('Replacement worker evidence differs from frozen request')
                receipt['status'] = 'REVIEW'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        receipt.update(error=str(exc)); receipt['execution']['status'] = 'FAILED'
    receipt['source_preserved'] = all(p.is_file() and p.read_bytes() == data for p, data in zip(paths, original))
    receipt['frozen_inputs_preserved'] = all(p.is_file() and p.read_bytes() == data for p, data in zip(frozen, original))
    if not receipt['source_preserved'] or not receipt['frozen_inputs_preserved']:
        receipt.update(status='FAILED', error='Original or frozen replacement inputs changed')
    receipt['execution']['elapsed_seconds'] = round(time.monotonic() - started, 6)
    receipt['outputs'] = [_artifact(p, work) for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):
        receipt.update(status='FAILED', error='Unexpected replacement-gradient output symlink')
    (work/'replacement_gradient_receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return receipt
