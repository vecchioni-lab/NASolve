"""Shared freezing, execution and cold-read lifecycle for native repair attribution.

Family adapters own scientific derivation and qualification. This module retains
one existing bounded runner contract and never selects or adopts a dictionary.
"""
from hashlib import sha256
import math
import re
from pathlib import Path
import subprocess
import tempfile
import time

from .cif_component_runtime import _tree, MAX_FILES, MAX_BYTES
from .cif_dictionary_store import _bytes, _json
from .cif_fana_junction import _path
from .cif_linked_linear_torsion import _exact
from .cif_mixed_geometry import _ref


def _need(value,message='Captured attribution evidence does not reproduce'):
    if not value:raise ValueError(message)


def inventory(root,contract):
    files=_tree(root)
    return ([_ref(root/name,root,contract.anchor) for name in files if name!=contract.report],
            sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()))


def audit(source,roots,controls,phenix,output,*,timeout_seconds,process_runner,contract,extra_inputs=None):
    _need(type(timeout_seconds) is int and 1<=timeout_seconds<=600, 'Invalid attribution timeout')
    source=_path(source);roots={name:_path(path,directory=True) for name,path in roots.items()}
    output = Path(output).expanduser().absolute()
    _need(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents))
          and not source.is_relative_to(output)
          and all(not output.is_relative_to(p) and not p.is_relative_to(output) for p in roots.values()))
    original = source.read_bytes(); snapshots = {name:_tree(p) for name,p in roots.items()}
    extra = {name: _path(path).read_bytes() for name,path in (extra_inputs or {}).items()}
    _need(all(Path(n).name==n and n!='source.cif' for n in extra), 'Invalid attribution extra input')
    _need(sum(len(v) for v in snapshots.values()) <= MAX_FILES
          and sum(len(b) for v in snapshots.values() for b in v.values()) + len(original) + sum(map(len,extra.values())) <= MAX_BYTES)
    def unchanged():
        _need(source.read_bytes() == original and all(_tree(roots[k]) == v for k,v in snapshots.items())
              and all(_path(extra_inputs[n]).read_bytes()==v for n,v in extra.items()),
              'Original attribution evidence changed during execution')
    with tempfile.TemporaryDirectory(prefix='captured-attribution-preflight-') as temporary:
        staging = Path(temporary).resolve(); (staging/'inputs').mkdir()
        (staging/'inputs/source.cif').write_bytes(original)
        for name,data in extra.items():(staging/'inputs'/name).write_bytes(data)
        for name, files in snapshots.items():
            for relative, data in files.items():
                p=staging/'inputs'/name/relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
        prepared, context, proof, arguments = contract.derive(staging, controls)
        executable = None
        if phenix is not None:
            executable = Path(phenix.executables['phenix.python']).resolve(strict=True)
            _need(phenix.version == context['phenix_version']
                  and sha256(executable.read_bytes()).hexdigest() == context['executable_sha256'],
                  'Selected attribution consumer differs from captures')
        unchanged(); output.mkdir(parents=True, exist_ok=False)
        for name, data in {**_tree(staging), **prepared}.items():
            p=output/name; p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as stream: stream.write(data)
    prepared, context, proof, arguments = contract.derive(output, controls)
    inputs = _tree(output/'inputs')
    report = dict(contract.fixed, controls=controls, status='PREPARED_ONLY', timeout_seconds=timeout_seconds,
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
                timeout_seconds=timeout_seconds, process_runner=process_runner,
                on_started=lambda:report.update(new_native_calls=1))
        except subprocess.TimeoutExpired as exc:
            report['execution']={'status':'TIMED_OUT', 'returncode':exc.returncode}
        else:
            report['execution']={'status':'COMPLETED' if code == 0 else 'FAILED', 'returncode':code}
        report['execution']['elapsed_seconds']=time.monotonic()-started
        report['status']='REVIEW'
        if report['execution']['status'] == 'COMPLETED':
            report['qualification']=contract.qualify(output, prepared, arguments)
            report['kernel_execution_authentication']='MAINTAINED_FRESH_NATIVE_JOB'
            if report['qualification']['numerical_checks_pass']:
                report['status']=contract.pass_status
        _need(sha256(executable.read_bytes()).hexdigest() == context['executable_sha256'])
    unchanged(); _need(_tree(output/'inputs') == inputs)
    _need(all((output/k).read_bytes() == v for k,v in prepared.items()), 'Prepared attribution job changed')
    report['outputs'], report['directories'] = inventory(output,contract)
    with (output/contract.report).open('xb') as stream: stream.write(_bytes(report))
    return read(output,contract)


def read(directory,contract):
    try:
        root=_path(directory, directory=True); report=_json((root/contract.report).read_bytes())
        _need(all(_exact(report.get(k),v) for k,v in contract.fixed.items()))
        prepared, context, proof, arguments=contract.derive(root, report['controls'])
        _need(all((root/k).read_bytes() == v for k,v in prepared.items()))
        refs, dirs=inventory(root,contract)
        _need(_exact(report['outputs'],refs) and _exact(report['directories'],dirs)
              and _exact(report['capture_qualification'],proof))
        allowed={f'inputs/{n}' for n in _tree(root/'inputs')} | set(prepared)
        execution=report['execution']; state=execution['status']; calls=report['new_native_calls']
        _need(type(calls) is int and calls in (0,1) and type(report['timeout_seconds']) is int
              and 1 <= report['timeout_seconds'] <= 600)
        fields=set(contract.fixed) | {'controls','status','timeout_seconds','new_native_calls','execution',
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
            allowed |= {'job/execution.log','job/result.json','job/before/native_validation.json','job/after/native_validation.json'} | set(contract.auxiliary(root))
            _need((root/'job/execution.log').is_file(), 'Missing attribution execution log')
            status='REVIEW'
            if state == 'COMPLETED':
                q=contract.qualify(root,prepared,arguments); authentication='MAINTAINED_FRESH_NATIVE_JOB'
                if q['numerical_checks_pass']: status=contract.pass_status
        _need(set(report) == fields and _exact(report['qualification'],q)
              and report['status'] == status and report['kernel_execution_authentication'] == authentication)
        actual={r['path'] for r in refs}
        expected_dirs={p.as_posix() for n in actual for p in Path(n).parents if p != Path('.')}
        _need(actual <= allowed and set(dirs) == expected_dirs)
        return report
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete captured attribution') from exc


def native_auxiliary(root):
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


def kernel_references(root, prepared, before, after, modules):
    result = _json((root/'job/result.json').read_bytes())
    _need(set(result) == {'spec_sha256', 'evaluator_sha256', 'installed_sources',
                         'installed_sources_after', 'sides'})
    _need(result['spec_sha256'] == sha256(prepared['job/spec.json']).hexdigest()
          and result['evaluator_sha256'] == sha256(prepared['job/evaluator.py']).hexdigest())
    pins = result['installed_sources']
    _need(isinstance(pins, list) and [r['module'] for r in pins] == list(modules)
          and all(set(r) == {'module', 'sha256', 'historical_path'}
              and isinstance(r['historical_path'], str) and r['historical_path']
              and isinstance(r['sha256'], str) and len(r['sha256']) == 64
              and all(c in '0123456789abcdef' for c in r['sha256']) for r in pins)
          and _exact(pins, result['installed_sources_after'])
          and _exact(pins[:3], before['energy_inventory']['installed_sources']))
    _need(all((root/k).read_bytes() == v for k,v in native_auxiliary(root).items()),
          'Rebuilt native PHIL differs from frozen capture')
    sides = result['sides']; _need(set(sides) == {'before', 'after'})
    for label, native in zip(('before', 'after'), (before,after)):
        side = sides[label]
        _need(set(side) == {'exact_native_inventory', 'special_position_indices', 'references'}
              and side['exact_native_inventory'] is True and side['special_position_indices'] == [])
        _need(_exact(_json((root/f'job/{label}/native_validation.json').read_bytes()), native),
              'Rebuilt native inventory differs from frozen capture')
    _need(len(sides['before']['references']) == len(sides['after']['references']))
    references = [dict(before=a, after=b) for a,b in zip(sides['before']['references'], sides['after']['references'])]
    return references
