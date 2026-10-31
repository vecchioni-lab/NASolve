"""Bounded native attribution for a frozen declared-linear repair chain.

Capture authentication, exact graph omissions and numerical attribution remain
separate from source chemistry, derivative checks and coordinate adoption.
Readers execute no saved worker and require no historical installation paths.
"""
from hashlib import sha256
import math
import os
from pathlib import Path
import subprocess
import time

from . import cif_linear_torsion_bundle as bundle
from .cif_captured_mixed_gradients import _inputs
from .cif_component_runtime import _tree
from .cif_dictionary_store import _bytes, _json
from .cif_fana_junction import _path
from .cif_linked_linear_torsion import _exact, qualify_linked_linear_torsion_candidate
from .cif_linked_torsion_energy import _removed
from .cif_mixed_geometry import _ref

POLICY_ID = 'cif-captured-linear-torsion-attribution-v1'
REPORT = 'captured_linear_attribution.json'
ANCHOR = 'captured_linear_attribution_directory'
MAX_PROXIES = 128
MODULES = ('cctbx.geometry_restraints.flags', 'cctbx.geometry_restraints.energies',
           'cctbx.geometry_restraints.manager', 'cctbx.geometry_restraints',
           'cctbx.array_family.flex', 'cctbx_geometry_restraints_ext')
_FIXED = dict(schema_version=1, policy_id=POLICY_ID, maximum_native_calls=1,
    maximum_removed_proxies=MAX_PROXIES, coordinate_selection='UNCHANGED_CAPTURE_INPUT',
    source_chemical_qualification='NOT_ASSESSED', derivative_qualification='NOT_RUN',
    model_optimization='NOT_RUN', readyset_execution='NOT_RUN', refinement='NOT_RUN',
    captured_code_execution='NOT_RUN', automatic_adoption=False)

_WORKER = r"""from pathlib import Path
from hashlib import sha256
import json,importlib
from cctbx import geometry_restraints as gr
from cctbx.array_family import flex
from conditioning_core import native_evaluator
modules=('cctbx.geometry_restraints.flags','cctbx.geometry_restraints.energies',
 'cctbx.geometry_restraints.manager','cctbx.geometry_restraints',
 'cctbx.array_family.flex','cctbx_geometry_restraints_ext')
def pins():
 result=[]
 for name in modules:
  p=Path(importlib.import_module(name).__file__).resolve(strict=True)
  result.append(dict(module=name,historical_path=str(p),sha256=sha256(p.read_bytes()).hexdigest()))
 return result
raw=Path('spec.json').read_bytes();spec=json.loads(raw);before=pins()
assert before[:3]==spec['installed_sources']
evaluate=native_evaluator(gr,flex);groups=[]
assert 0<sum(map(len,spec['groups']))<=128
for group in spec['groups']:
 refs=[]
 for row in group:
  values=[evaluate(row['sites_cart'],row['proxy']) for _ in range(2)]
  refs.append(dict(row,evaluations=[{k:v[k] for k in
   ('single_target','single_gradient','accumulated_target','accumulated_gradient')} for v in values]))
 groups.append(refs)
after=pins();assert before==after
result=dict(spec_sha256=sha256(raw).hexdigest(),
 core_sha256=sha256(Path('conditioning_core.py').read_bytes()).hexdigest(),
 installed_sources=before,installed_sources_after=after,groups=groups)
Path('result.json').write_text(json.dumps(result,sort_keys=True,allow_nan=False)+'\n')
"""


def _need(ok):
    if not ok:raise ValueError('Captured linear-torsion attribution does not reproduce')


def _reference(path, root):
    return _ref(path, root, ANCHOR)


def _derive(root):
    plan = bundle.read_linear_torsion_bundle(root/'bundle')
    _need(bool(plan['steps']))
    stages = [plan['inputs']] + [s['dictionaries_after'] for s in plan['steps']]
    inventories, receipts, context, groups = [], [], None, []
    for i, refs in enumerate(stages):
        parent = root/'captures'/f'{i:03d}'
        capture, model, dictionaries, phils, native, _ = _inputs(parent)
        # A receipt's parent is not permission to absorb unrelated local files.
        # Refuse them during preflight, before a new attempt or native process.
        _need(set(_tree(parent)) == {'native_receipt.json'} | {r['path'] for r in capture['outputs']})
        _need([p.read_bytes() for p in dictionaries] == [(root/'bundle'/r['path']).read_bytes() for r in refs])
        current = dict(model=model.read_bytes(), phils=[p.read_bytes() for p in phils],
            **{k:capture[k] for k in ('phenix_version','executable_sha256','phil_namespace_policy','dictionary_source_policy')})
        if context is None:context = current
        else:_need(context == current)
        inventories.append(native);receipts.append(parent/'native_receipt.json')
    _need(sorted({a['identity']['resname'].strip() for a in inventories[0]['atoms']}) == plan['modeled_components'])
    pins = inventories[0]['energy_inventory']['installed_sources']
    for i, step in enumerate(plan['steps']):
        before, after = inventories[i:i+2]
        q = qualify_linked_linear_torsion_candidate(before, after, root/'bundle'/step['source']['path'],
            step['component'], root/'bundle'/step['candidate']['path'])
        _need(q['inventory_checks_pass'] is True and before['energy_inventory']['installed_sources'] == pins
              and after['energy_inventory']['installed_sources'] == pins)
        points = before['geometry']['sites_cart_exact']
        groups.append([dict(proxy_kind=k, proxy=p, sites_cart=[points[j] for j in p['i_seqs']]) for k,p in _removed(before,after)])
    _need(0 < sum(map(len, groups)) <= MAX_PROXIES)
    return dict(groups=groups, installed_sources=pins), receipts, context


def _prepared(root):
    spec, receipts, context = _derive(root)
    core = Path(__file__).with_name('cif_dihedral_conditioning.py').read_bytes()
    return {'job/spec.json':_bytes(spec), 'job/worker.py':_WORKER.encode(),
            'job/conditioning_core.py':core}, receipts, context


def _result(root, receipts):
    work = root/'job';result = _json((work/'result.json').read_bytes())
    spec = _json((work/'spec.json').read_bytes())
    _need(set(result) == {'spec_sha256','core_sha256','installed_sources','installed_sources_after','groups'}
        and result['spec_sha256'] == sha256((work/'spec.json').read_bytes()).hexdigest()
        and result['core_sha256'] == sha256((work/'conditioning_core.py').read_bytes()).hexdigest())
    pins = result['installed_sources']
    _need(isinstance(pins,list) and [p['module'] for p in pins] == list(MODULES)
          and all(set(p)=={'module','sha256','historical_path'} and isinstance(p['historical_path'],str)
            and p['historical_path'] and isinstance(p['sha256'],str) and len(p['sha256'])==64
            and all(c in '0123456789abcdef' for c in p['sha256']) for p in pins)
          and pins == result['installed_sources_after'] and pins[:3] == spec['installed_sources'])
    return bundle.qualify_captured_linear_torsion_bundle(root/'bundle', receipts, result['groups'])


def _inventory(root):
    files = _tree(root)
    return ([_reference(root/name,root) for name in files if name != REPORT],
            sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()))


def _publish(root, report):
    report['outputs'],report['directories'] = _inventory(root)
    (root/REPORT).write_bytes(_bytes(report))
    return read_captured_linear_attribution(root)


def audit_captured_linear_attribution(directory, native_receipts, phenix, output, *, timeout_seconds=90):
    """Freeze exact staged captures; None prepares, otherwise run one fresh kernel.

    Failed and interrupted attempts are preserved. A fresh output is mandatory;
    this API never resumes an old process or retries in place.
    """
    _need(type(timeout_seconds) is int and 1 <= timeout_seconds <= 300)
    original = _path(directory,directory=True);plan = bundle.read_linear_torsion_bundle(original)
    _need(bool(plan['steps']) and isinstance(native_receipts,(list,tuple)) and len(native_receipts)==len(plan['steps'])+1)
    sources = {'bundle':original}
    for i,p in enumerate(native_receipts):
        p = _path(p);_need(p.name=='native_receipt.json');sources[f'captures/{i:03d}']=p.parent
    root = Path(output).expanduser().absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in (root,*root.parents))
          and all(not root.is_relative_to(p) and not p.is_relative_to(root) for p in sources.values()))
    snapshots = {name:_tree(p) for name,p in sources.items()}
    _need(sum(len(v) for v in snapshots.values())<=1024 and sum(len(b) for v in snapshots.values() for b in v.values())<=128*1024*1024)
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix='linear-attribution-preflight-') as temporary:
        staging = Path(temporary).resolve()
        for name,files in snapshots.items():
            for relative,data in files.items():
                p=staging/name/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        prepared,_,context = _prepared(staging)
        executable = None
        if phenix is not None:
            executable = Path(phenix.executables['phenix.python']).resolve(strict=True)
            _need(phenix.version==context['phenix_version'] and sha256(executable.read_bytes()).hexdigest()==context['executable_sha256'])
        _need(all(_tree(sources[k])==v for k,v in snapshots.items()))
        root.mkdir(parents=True,exist_ok=False)
        for p in sorted(staging.rglob('*')):
            if p.is_file():
                target=root/p.relative_to(staging);target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:stream.write(p.read_bytes())
    for name,data in prepared.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as stream:stream.write(data)
    _,receipts,_ = _prepared(root)
    report = dict(_FIXED, status='PREPARED_ONLY', timeout_seconds=timeout_seconds,
        new_native_calls=0, execution={'status':'NOT_RUN'}, qualification={'status':'NOT_RUN'},
        kernel_execution_authentication='NOT_RUN')
    if executable is not None:
        from .cif_native_validation import _stop
        report.update(status='REVIEW',phenix_version=phenix.version,
            executable_provenance=str(executable),executable_sha256=context['executable_sha256'])
        started=time.monotonic()
        try:
            with (root/'job/execution.log').open('xb') as log:
                process=subprocess.Popen([str(executable),'-B','worker.py'],cwd=root/'job',env=dict(phenix.environment),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                report['new_native_calls']=1
                try:code=process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:_stop(process);report['execution']={'status':'TIMED_OUT','returncode':process.returncode}
                except BaseException:_stop(process);raise
                else:report['execution']={'status':'COMPLETED' if code==0 else 'FAILED','returncode':code}
            if report['execution']['status']=='COMPLETED':
                report['qualification']=_result(root,receipts)
                report.update(status='CAPTURED_LINEAR_ATTRIBUTION_PASS',kernel_execution_authentication='MAINTAINED_FRESH_NATIVE_JOB')
        except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
            report['error']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['error']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
        _need(sha256(executable.read_bytes()).hexdigest()==context['executable_sha256'])
    _need(all(_tree(sources[k])==v for k,v in snapshots.items()))
    return _publish(root,report)


def _read(directory):
    root=_path(directory,directory=True);report=_json((root/REPORT).read_bytes())
    _need(all(_exact(report.get(k),v) for k,v in _FIXED.items()))
    prepared,receipts,context=_prepared(root)
    _need(all((root/k).read_bytes()==v for k,v in prepared.items()))
    refs,dirs=_inventory(root)
    _need(_exact(report['outputs'],refs) and _exact(report['directories'],dirs))
    plan=bundle.read_linear_torsion_bundle(root/'bundle')
    allowed={'bundle/'+r['path'] for r in plan['outputs']} | {'bundle/'+bundle.REPORT} | set(prepared)
    for i,p in enumerate(receipts):
        capture=_json(p.read_bytes());allowed.add(f'captures/{i:03d}/native_receipt.json')
        allowed.update(f'captures/{i:03d}/'+r['path'] for r in capture['outputs'])
    execution=report['execution'];state=execution['status'];calls=report['new_native_calls']
    _need(type(calls) is int and calls in (0,1) and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=300)
    fields=set(_FIXED)|{'status','timeout_seconds','new_native_calls','execution','qualification','kernel_execution_authentication','outputs','directories'}
    if state=='NOT_RUN':
        _need(calls==0 and execution=={'status':'NOT_RUN'} and report['status']=='PREPARED_ONLY')
    else:
        fields|={'phenix_version','executable_provenance','executable_sha256'}
        allowed|={'job/execution.log','job/result.json'}
        _need(report['phenix_version']==context['phenix_version'] and report['executable_sha256']==context['executable_sha256']
            and isinstance(report['executable_provenance'],str) and bool(report['executable_provenance'])
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0)
        if state=='LAUNCH_FAILED':
            _need(calls==0 and set(execution)=={'status','error','elapsed_seconds'}
                and isinstance(report.get('error'),str) and bool(report['error']) and execution['error']==report['error'])
        else:
            code=execution['returncode']
            _need(calls==1 and state in {'COMPLETED','FAILED','TIMED_OUT'} and type(code) is int
                and (state!='COMPLETED' or code==0) and (state!='FAILED' or code!=0)
                and set(execution)=={'status','returncode','elapsed_seconds'})
    if 'error' in report:
        fields.add('error');_need(isinstance(report['error'],str) and bool(report['error']))
    _need(set(report)==fields)
    actual={r['path'] for r in refs}
    expected_dirs={p.as_posix() for n in actual for p in Path(n).parents if p!=Path('.')}
    _need(actual<=allowed and set(dirs)==expected_dirs)
    q=None
    if state=='COMPLETED':
        try:q=_result(root,receipts)
        except (OSError,ValueError,KeyError,TypeError,IndexError):_need('error' in report)
    if q is None:
        _need(report['qualification']=={'status':'NOT_RUN'} and report['kernel_execution_authentication']=='NOT_RUN'
            and report['status']==('PREPARED_ONLY' if state=='NOT_RUN' else 'REVIEW'))
    else:
        _need('error' not in report and _exact(report['qualification'],q)
            and report['status']=='CAPTURED_LINEAR_ATTRIBUTION_PASS'
            and report['kernel_execution_authentication']=='MAINTAINED_FRESH_NATIVE_JOB')
    return report


def read_captured_linear_attribution(directory):
    """Recompute every claim offline; never execute captured code or open an SDK."""
    try:return _read(directory)
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete captured linear-torsion attribution') from exc
