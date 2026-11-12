"""Maintained whole-plane attribution over owned source/capture evidence.

One bounded native job rebuilds both fixed managers and evaluates complete groups.
The existing caller owns process identity/recovery; this reader runs no saved code.
Chemical approval, derivatives, geometry and runtime adoption remain separate.
"""
from hashlib import sha256
import inspect
import math
import re
from pathlib import Path
import subprocess
import tempfile
import time

from .cif_attachment_native import _json
from .cif_captured_mixed_gradients import _inputs
from .cif_component_runtime import _tree, MAX_FILES, MAX_BYTES
from .cif_dictionary_store import _bytes
from .cif_fana_junction import _path
from .cif_linked_linear_torsion import _exact
from .cif_mixed_geometry import _ref
from .cif_plane_generation import read_owned_plane_support
from .cif_plane_native import qualify_owned_plane_captures
from .cif_plane_energy import changed_plane_pairs, native_plane_evaluator, qualify_linked_plane_energy

POLICY_ID = 'cif-captured-owned-plane-attribution-v1'
REPORT = 'captured_plane_attribution.json'
ANCHOR = 'captured_plane_attribution_directory'
MODULES = ('cctbx.geometry_restraints.flags', 'cctbx.geometry_restraints.energies',
           'cctbx.geometry_restraints.manager', 'cctbx.geometry_restraints',
           'cctbx.array_family.flex', 'cctbx_geometry_restraints_ext')
_FIXED = dict(schema_version=1, policy_id=POLICY_ID, maximum_native_calls=1,
    maximum_changed_planes=128, coordinate_selection='UNCHANGED_CAPTURE_INPUT',
    source_chemical_qualification='NOT_ASSESSED', derivative_qualification='NOT_RUN',
    achieved_geometry='NOT_ASSESSED', model_optimization='NOT_RUN', refinement='NOT_RUN',
    captured_code_execution='NOT_RUN', automatic_adoption=False)

_WORKER = r'''from pathlib import Path
from hashlib import sha256
import importlib,json,os,sys
from cctbx import geometry_restraints as gr
from cctbx.array_family import flex
from evaluator import native_plane_evaluator
modules=('cctbx.geometry_restraints.flags','cctbx.geometry_restraints.energies',
 'cctbx.geometry_restraints.manager','cctbx.geometry_restraints',
 'cctbx.array_family.flex','cctbx_geometry_restraints_ext')
def pins():
 result=[]
 for name in modules:
  p=Path(importlib.import_module(name).__file__).resolve(strict=True)
  result.append(dict(module=name,historical_path=str(p),sha256=sha256(p.read_bytes()).hexdigest()))
 return result
home=Path.cwd();raw=Path('spec.json').read_bytes();spec=json.loads(raw);before=pins()
assert before[:3]==spec['installed_sources']
evaluate=native_plane_evaluator(gr,flex);sides={}
for label in ('before','after'):
 os.chdir(home/label)
 namespace={'__name__':'__main__','__file__':'native_worker.py'};sys.argv=['native_worker.py','native_spec.json']
 try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
 except SystemExit as exc:
  if exc.code!=0:raise RuntimeError('Native manager rebuild failed')
 actual=namespace['report'];expected=spec[label]['inventory']
 assert json.dumps(actual,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False)
 geo=namespace['geo'];assert list(geo.site_symmetry_table.special_position_indices())==[]
 points=actual['geometry']['sites_cart_exact'];references=[]
 assert 0<len(spec[label]['planes'])<=128
 for row in spec[label]['planes']:
  matches=[p for p in geo.planarity_proxies if set(p.i_seqs)==set(row['i_seqs'])]
  assert len(matches)==1;p=matches[0]
  observed=sorted(zip(list(p.i_seqs),list(p.weights)))
  assert [i for i,w in observed]==row['i_seqs'] and [w for i,w in observed]==row['weights'] and int(p.origin_id)==row['origin_id']==0
  ops=None if p.sym_ops is None else [r.as_xyz() for _,r in sorted(zip(list(p.i_seqs),list(p.sym_ops)),key=lambda x:x[0])]
  assert ops is None or (len(ops)==len(row['i_seqs']) and all(v=='x,y,z' for v in ops))
  local=[points[i] for i in row['i_seqs']]
  references.append(dict(proxy=row,sites_cart=local,symmetry_operations=ops,evaluations=[evaluate(local,row) for _ in range(2)]))
 sides[label]=dict(exact_native_inventory=True,special_position_indices=[],references=references)
 os.chdir(home)
after=pins();assert before==after
result=dict(spec_sha256=sha256(raw).hexdigest(),evaluator_sha256=sha256(Path('evaluator.py').read_bytes()).hexdigest(),
 installed_sources=before,installed_sources_after=after,sides=sides)
Path('result.json').write_text(json.dumps(result,sort_keys=True,allow_nan=False)+'\n')
'''


# Preserve the historical worker for old evidence. The compact form changes only
# where the exact expected inventory is read, not the comparison or calculation.
_REFERENCED_WORKER = _WORKER.replace(
    " actual=namespace['report'];expected=spec[label]['inventory']",
    """ ref=spec[label]['inventory_ref']
 assert set(ref)=={'anchor','path','sha256','size'}
 assert ref['anchor']=='captured_plane_attribution_directory' and ref['path']=='inputs/'+label+'/native_validation.json'
 expected_raw=(home.parent/ref['path']).read_bytes()
 assert len(expected_raw)==ref['size'] and sha256(expected_raw).hexdigest()==ref['sha256']
 actual=namespace['report'];expected=json.loads(expected_raw)""")


def _need(value, message='Captured whole-plane evidence does not reproduce'):
    if not value:
        raise ValueError(message)


def _derive(root, controls):
    compact = controls.get('compact_inventory',False)
    _need(type(compact) is bool and set(controls) == {'component', 'attempt_number', 'dictionary_index'}
          | ({'compact_inventory'} if compact else set()))
    source = root/'inputs/source.cif'; request = root/'inputs/generation'
    entries = [_inputs(root/'inputs'/label) for label in ('before', 'after')]
    before, after = entries
    index = controls['dictionary_index']
    _need(type(index) is int and 0 <= index < len(before[2]) and len(after[2]) == len(before[2]))
    proof = qualify_owned_plane_captures(source, controls['component'], request,
        controls['attempt_number'], after[2][index], before[1],
        root/'inputs/before/native_receipt.json', root/'inputs/after/native_receipt.json',
        dictionaries=before[2], dictionary_index=index, phil_files=before[3])
    support = read_owned_plane_support(source, controls['component'], request, controls['attempt_number'])
    pairs = changed_plane_pairs(before[4], after[4])
    pins = before[4]['energy_inventory']['installed_sources']
    _need(_exact(pins, after[4]['energy_inventory']['installed_sources']))
    prepared = {'job/worker.py': (_REFERENCED_WORKER if compact else _WORKER).encode(),
                'job/evaluator.py': inspect.getsource(native_plane_evaluator).encode()}
    spec = {'installed_sources': pins}
    from .cif_candidate_usability import native_energy_worker
    from .cif_native_validation import _NATIVE_WORKER
    from .cif_native_monomers import native_monomer_worker
    for ordinal, (label, entry) in enumerate(zip(('before', 'after'), entries)):
        capture, model, dictionaries, phils, native, _ = entry
        parent = root/'inputs'/label
        _need(set(_tree(parent)) == {'native_receipt.json'} | {r['path'] for r in capture['outputs']},
              'Capture directory has unrelated files')
        native_spec = (parent/'native_spec.json').read_bytes()
        parsed = _json(native_spec)
        # _inputs validates the supported spec fields and energy capture. Write
        # maintained code afresh; no historical worker is used as executable input.
        worker = native_energy_worker(_NATIVE_WORKER)
        if parsed.get('full_monomer_inventory'):
            worker = native_monomer_worker(worker)
        prepared[f'job/{label}/native_worker.py'] = worker.encode()
        prepared[f'job/{label}/native_spec.json'] = native_spec
        for row in capture['inputs']:
            prepared[f"job/{label}/{row['path']}"] = (parent/row['path']).read_bytes()
        expected = ({'inventory_ref':_ref(parent/'native_validation.json',root,ANCHOR)}
                    if compact else {'inventory':native})
        spec[label] = {**expected, 'planes': [p[ordinal] for p in pairs]}
    prepared['job/spec.json'] = _bytes(spec)
    arguments = (before[4], after[4], source, before[2][index],
                 request/support['support']['path'], controls['component'], after[2][index])
    return prepared, before[0], proof, arguments


def _native_auxiliary(root):
    """Expected PHIL outputs of the maintained native interpreter, already bound
    by each authenticated capture. They are regenerated, not prepopulated.
    """
    result = {}
    for label in ('before', 'after'):
        parent = root/'inputs'/label
        capture = _json((parent/'native_receipt.json').read_bytes())
        for row in capture['outputs']:
            name = row['path']
            if name == 'native_effective.phil' or re.fullmatch(r'canonical_[0-9]{3,}\.phil', name):
                result[f'job/{label}/{name}'] = (parent/name).read_bytes()
    return result


def _qualification(root, prepared, arguments):
    result = _json((root/'job/result.json').read_bytes())
    _need(set(result) == {'spec_sha256', 'evaluator_sha256', 'installed_sources',
                         'installed_sources_after', 'sides'})
    _need(result['spec_sha256'] == sha256(prepared['job/spec.json']).hexdigest()
          and result['evaluator_sha256'] == sha256(prepared['job/evaluator.py']).hexdigest())
    pins = result['installed_sources']
    _need(isinstance(pins, list) and [r['module'] for r in pins] == list(MODULES)
          and all(set(r) == {'module', 'sha256', 'historical_path'}
              and isinstance(r['historical_path'], str) and r['historical_path']
              and isinstance(r['sha256'], str) and len(r['sha256']) == 64
              and all(c in '0123456789abcdef' for c in r['sha256']) for r in pins)
          and _exact(pins, result['installed_sources_after'])
          and _exact(pins[:3], arguments[0]['energy_inventory']['installed_sources']))
    _need(all((root/k).read_bytes() == v for k,v in _native_auxiliary(root).items()),
          'Rebuilt native PHIL differs from frozen capture')
    sides = result['sides']; _need(set(sides) == {'before', 'after'})
    for label, native in zip(('before', 'after'), arguments[:2]):
        side = sides[label]
        _need(set(side) == {'exact_native_inventory', 'special_position_indices', 'references'}
              and side['exact_native_inventory'] is True and side['special_position_indices'] == [])
        _need(_exact(_json((root/f'job/{label}/native_validation.json').read_bytes()), native),
              'Rebuilt native inventory differs from frozen capture')
    _need(len(sides['before']['references']) == len(sides['after']['references']))
    references = [dict(before=a, after=b) for a,b in zip(sides['before']['references'], sides['after']['references'])]
    return qualify_linked_plane_energy(*arguments, references)


def _inventory(root):
    files = _tree(root)
    return ([_ref(root/name, root, ANCHOR) for name in files if name != REPORT],
            sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()))


def audit_captured_plane_attribution(source, component, request_directory, attempt_number,
        before_receipt, after_receipt, dictionary_index, phenix, output, *,
        timeout_seconds=120, compact_inventory=False, _process_runner=None):
    """Freeze owned generation and two exact captures, then run one bounded job.

    Passing None for phenix prepares only. A fresh output is mandatory; failed
    jobs and interruptions are preserved. The supplied runner belongs to the
    existing repair owner, not this adapter. No candidate is adopted here.
    """
    _need(type(timeout_seconds) is int and 1 <= timeout_seconds <= 600)
    _need(type(compact_inventory) is bool, 'Require a boolean native-inventory storage choice')
    controls = dict(component=component, attempt_number=attempt_number, dictionary_index=dictionary_index,
                    **({'compact_inventory':True} if compact_inventory else {}))
    source = _path(source); request = _path(request_directory, directory=True)
    receipts = [_path(p) for p in (before_receipt, after_receipt)]
    _need(all(p.name == 'native_receipt.json' for p in receipts))
    roots = dict(generation=request, before=receipts[0].parent, after=receipts[1].parent)
    output = Path(output).expanduser().absolute()
    _need(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents))
          and not source.is_relative_to(output)
          and all(not output.is_relative_to(p) and not p.is_relative_to(output) for p in roots.values()))
    original = source.read_bytes(); snapshots = {name:_tree(p) for name,p in roots.items()}
    _need(sum(len(v) for v in snapshots.values()) <= MAX_FILES
          and sum(len(b) for v in snapshots.values() for b in v.values()) + len(original) <= MAX_BYTES)
    def unchanged():
        _need(source.read_bytes() == original and all(_tree(roots[k]) == v for k,v in snapshots.items()),
              'Original plane evidence changed during execution')
    with tempfile.TemporaryDirectory(prefix='plane-attribution-preflight-') as temporary:
        staging = Path(temporary).resolve(); (staging/'inputs').mkdir()
        (staging/'inputs/source.cif').write_bytes(original)
        for name, files in snapshots.items():
            for relative, data in files.items():
                p=staging/'inputs'/name/relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
        prepared, context, proof, arguments = _derive(staging, controls)
        executable = None
        if phenix is not None:
            executable = Path(phenix.executables['phenix.python']).resolve(strict=True)
            _need(phenix.version == context['phenix_version']
                  and sha256(executable.read_bytes()).hexdigest() == context['executable_sha256'],
                  'Selected plane consumer differs from captures')
        unchanged(); output.mkdir(parents=True, exist_ok=False)
        for name, data in {**_tree(staging), **prepared}.items():
            p=output/name; p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as stream: stream.write(data)
    prepared, context, proof, arguments = _derive(output, controls)
    inputs = _tree(output/'inputs')
    report = dict(_FIXED, controls=controls, status='PREPARED_ONLY', timeout_seconds=timeout_seconds,
        new_native_calls=0, execution={'status':'NOT_RUN'}, capture_qualification=proof,
        qualification={'status':'NOT_RUN'}, kernel_execution_authentication='NOT_RUN')
    if executable is not None:
        from .cif_native_validation import _run_native_command
        report.update(phenix_version=phenix.version, executable_provenance=str(executable),
                      executable_sha256=context['executable_sha256'])
        started=time.monotonic()
        try:
            code=_run_native_command([str(executable), '-B', 'worker.py'], cwd=output/'job',
                log_path=output/'job/execution.log', environment=phenix.environment,
                timeout_seconds=timeout_seconds, process_runner=_process_runner,
                on_started=lambda:report.update(new_native_calls=1))
        except subprocess.TimeoutExpired as exc:
            report['execution']={'status':'TIMED_OUT', 'returncode':exc.returncode}
        else:
            report['execution']={'status':'COMPLETED' if code == 0 else 'FAILED', 'returncode':code}
        report['execution']['elapsed_seconds']=time.monotonic()-started
        report['status']='REVIEW'
        if report['execution']['status'] == 'COMPLETED':
            report['qualification']=_qualification(output, prepared, arguments)
            report['kernel_execution_authentication']='MAINTAINED_FRESH_NATIVE_JOB'
            if report['qualification']['numerical_checks_pass']:
                report['status']='CAPTURED_PLANE_ATTRIBUTION_PASS'
        _need(sha256(executable.read_bytes()).hexdigest() == context['executable_sha256'])
    unchanged(); _need(_tree(output/'inputs') == inputs)
    _need(all((output/k).read_bytes() == v for k,v in prepared.items()), 'Prepared plane job changed')
    report['outputs'], report['directories'] = _inventory(output)
    with (output/REPORT).open('xb') as stream: stream.write(_bytes(report))
    return read_captured_plane_attribution(output)


def read_captured_plane_attribution(directory):
    """Recompute source, capture and numerical claims offline, without saved code."""
    try:
        root=_path(directory, directory=True); report=_json((root/REPORT).read_bytes())
        _need(all(_exact(report.get(k),v) for k,v in _FIXED.items()))
        prepared, context, proof, arguments=_derive(root, report['controls'])
        _need(all((root/k).read_bytes() == v for k,v in prepared.items()))
        refs, dirs=_inventory(root)
        _need(_exact(report['outputs'],refs) and _exact(report['directories'],dirs)
              and _exact(report['capture_qualification'],proof))
        allowed={f'inputs/{n}' for n in _tree(root/'inputs')} | set(prepared)
        execution=report['execution']; state=execution['status']; calls=report['new_native_calls']
        _need(type(calls) is int and calls in (0,1) and type(report['timeout_seconds']) is int
              and 1 <= report['timeout_seconds'] <= 600)
        fields=set(_FIXED) | {'controls','status','timeout_seconds','new_native_calls','execution',
            'capture_qualification','qualification','kernel_execution_authentication','outputs','directories'}
        q={'status':'NOT_RUN'}; status='PREPARED_ONLY'; authentication='NOT_RUN'
        if state == 'NOT_RUN':
            _need(calls == 0 and execution == {'status':'NOT_RUN'})
        else:
            fields |= {'phenix_version','executable_provenance','executable_sha256'}
            _need(calls == 1 and state in {'COMPLETED','FAILED','TIMED_OUT'}
                  and set(execution) == {'status','returncode','elapsed_seconds'}
                  and type(execution['returncode']) is int
                  and (state != 'COMPLETED' or execution['returncode'] == 0)
                  and (state != 'FAILED' or execution['returncode'] != 0)
                  and type(execution['elapsed_seconds']) in (int,float)
                  and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds'] >= 0
                  and report['phenix_version'] == context['phenix_version']
                  and report['executable_sha256'] == context['executable_sha256']
                  and isinstance(report['executable_provenance'],str) and report['executable_provenance'])
            allowed |= {'job/execution.log','job/result.json','job/before/native_validation.json','job/after/native_validation.json'} | set(_native_auxiliary(root))
            _need((root/'job/execution.log').is_file(), 'Missing plane execution log')
            status='REVIEW'
            if state == 'COMPLETED':
                q=_qualification(root,prepared,arguments); authentication='MAINTAINED_FRESH_NATIVE_JOB'
                if q['numerical_checks_pass']: status='CAPTURED_PLANE_ATTRIBUTION_PASS'
        _need(set(report) == fields and _exact(report['qualification'],q)
              and report['status'] == status and report['kernel_execution_authentication'] == authentication)
        actual={r['path'] for r in refs}
        expected_dirs={p.as_posix() for n in actual for p in Path(n).parents if p != Path('.')}
        _need(actual <= allowed and set(dirs) == expected_dirs)
        return report
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete captured whole-plane attribution') from exc
