"""Read-only installed eLBOW evidence, separate from numerical generation.

Capture only declared modules beneath the already verified Phenix API anchor.
No captured Python or serialized molecule is imported or executed. Input checks
use the installed CLI's exact help definition for its read-only option.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import subprocess
from tempfile import mkdtemp
import time

from .cif_generation import _generator_capabilities, _terminate_owned_group, _ideal_seed

POLICY_ID = 'cif-installed-elbow-read-only-contract-v1'
SOURCE_PATHS = ('elbow/utilities/Utilities.py',
                'elbow/utilities/optimisation_manager.py',
                'elbow/command_line/builder.py',
                'elbow/chemistry/any_chemical_format_reader.py')
MAX_SOURCE_BYTES = 1024 * 1024


def _safe(name):
    return isinstance(name, str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(
        part not in {'', '.', '..'} for part in name.split('/'))


def _digest(data):
    return sha256(data).hexdigest()


def _inside(root, relative):
    if not _safe(relative):
        raise ValueError('Unsafe installed source reference')
    path = root / PurePosixPath(relative)
    if not path.resolve(strict=True).is_relative_to(root):
        raise ValueError('Installed source escapes the selected installation')
    return path


def capture_elbow_sources(installation_root, api_sources, output, *, phenix_version):
    """Copy four exact installed source files; this is evidence, not a patch."""
    root = Path(installation_root).resolve(strict=True)
    output = Path(output).absolute()
    if output.resolve().is_relative_to(root):
        raise ValueError('Source evidence must be outside the installation')
    anchors = [r for r in api_sources if r.get('anchor') == 'phenix_installation'
               and _safe(r.get('path')) and r['path'].endswith('/iotbx/phil.py')]
    if len(anchors) != 1:
        raise ValueError('Require one verified installed Python-library anchor')
    site = PurePosixPath(anchors[0]['path']).parent.parent
    rows, payloads = [], {}
    for relative in SOURCE_PATHS:
        installed = (site / relative).as_posix()
        path = _inside(root, installed)
        if not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError('Missing or oversized installed eLBOW source')
        data = path.read_bytes()
        if len(data) > MAX_SOURCE_BYTES:
            raise ValueError('Oversized installed eLBOW source')
        ast.parse(data, filename=relative)
        payloads[relative] = data
        rows.append({'anchor': 'phenix_installation', 'path': installed,
                     'snapshot': {'anchor': 'contract_directory', 'path': relative},
                     'sha256': _digest(data), 'size': len(data)})
    # Static accesses are an inventory. Guarded accesses and optional fields
    # are not promoted to a universal required-field schema.
    tree = ast.parse(payloads[SOURCE_PATHS[0]])
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == 'get_elbow_molecule_from_chemical_components']
    accesses = sorted({n.attr for f in functions for n in ast.walk(f)
                       if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'item'})
    output.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle:
            handle.write(data)
    report = {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'CAPTURED_NOT_QUALIFIED',
              'phenix_version': str(phenix_version), 'sources': rows,
              'reader_item_attribute_accesses': accesses,
              'static_attribute_inventory_is_required_schema': False,
              'installed_phenix_edits': 'NOT_RUN', 'captured_code_execution': 'NOT_RUN',
              'pickle_loading': 'NOT_RUN', 'automatic_adoption': False}
    verify_elbow_source_capture(root, report, output)
    with (output / 'source_capture.json').open('x') as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write('\n')
    return report


def verify_elbow_source_capture(installation_root, report, output):
    root, output = Path(installation_root).resolve(strict=True), Path(output).resolve(strict=True)
    if len(report['sources']) != len(SOURCE_PATHS) or {
            row['snapshot']['path'] for row in report['sources']} != set(SOURCE_PATHS):
        raise ValueError('Installed source inventory differs')
    for row in report['sources']:
        if row.get('anchor') != 'phenix_installation' or row['snapshot'].get('anchor') != 'contract_directory':
            raise ValueError('Unsupported installed source anchor')
        installed = _inside(root, row['path'])
        snapshot = _inside(output, row['snapshot']['path'])
        for path in [installed, snapshot]:
            data = path.read_bytes()
            if len(data) != row['size'] or _digest(data) != row['sha256']:
                raise ValueError('Installed or captured eLBOW source changed')
    return True


def audit_elbow_input(source, code, output_parent, executable, *, environment,
                     phenix_version, timeout_seconds=60):
    """Run a bounded installed --read-only input check, without generation."""
    source, executable = Path(source).resolve(strict=True), Path(executable).resolve(strict=True)
    parent = Path(output_parent).resolve()
    if parent == source.parent or parent.is_relative_to(source.parent):
        raise ValueError('Input-check output must be outside the source directory')
    if not phenix_version or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60:
        raise ValueError('Require an explicit version and a timeout in (0, 60]')
    original, executable_bytes = source.read_bytes(), executable.read_bytes()
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(mkdtemp(prefix='cif-elbow-input-', dir=parent))
    snapshot = work / 'source.cif'
    snapshot.write_bytes(original)
    result = {'schema_version': 1, 'policy_id': POLICY_ID, 'component': code,
              'status': 'REVIEW', 'candidate_directory': str(work),
              'phenix_version': str(phenix_version), 'executable_sha256': _digest(executable_bytes),
              'source_sha256': _digest(original), 'command': None,
              'execution': {'status': 'NOT_RUN'}, 'dictionary_generation': 'NOT_RUN',
              'model_optimization': 'NOT_RUN', 'chemical_qualification': 'NOT_RUN',
              'native_proxy_validation': 'NOT_RUN', 'automatic_adoption': False}
    clock = time.monotonic()
    result['execution']['started_at'] = datetime.now(timezone.utc).isoformat()
    try:
        capabilities = _generator_capabilities(executable, work, environment, timeout_seconds, str(phenix_version))
        result['generator_capabilities'] = capabilities
        definitions = capabilities.get('supported_option_definitions', {})
        read_only = next((flag for flag in ['--read-only', '--read_only'] if definitions.get(flag) is False), None)
        if capabilities['status'] != 'SUPPORTED' or read_only is None:
            result['execution']['status'] = 'UNSUPPORTED_READ_ONLY_OPTION'
        else:
            flags = capabilities['selected_aliases']
            command = [str(executable), 'source.cif', read_only, f"{flags['id']}={code}",
                       f"{flags['output']}=read_only", f"{flags['add_hydrogens']}=False",
                       f"{flags['source_state_preservation']}=low", f"{flags['chiral']}=retain"]
            result['command'] = command
            with (work / 'elbow_read_only.log').open('xb') as log:
                process = subprocess.Popen(command, cwd=work, env=dict(environment),
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=os.name == 'posix')
                try:
                    returncode = process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    _terminate_owned_group(process)
                    result['execution'].update(status='TIMED_OUT', returncode=process.returncode)
                except BaseException:
                    _terminate_owned_group(process)
                    raise
                else:
                    result['execution'].update(status='COMPLETED' if returncode == 0 else 'FAILED', returncode=returncode)
                    text = (work / 'elbow_read_only.log').read_text(errors='replace')
                    unexpected = any(marker in text for marker in ['Optimisation Manager', 'GDIISClass'])
                    result['unexpected_processing_detected'] = unexpected
                    if returncode == 0 and not unexpected:
                        result['status'] = 'PARSER_READ_ONLY_PASS'
    except (OSError, ValueError) as exc:
        result.update(error=f'{type(exc).__name__}: {exc}')
        result['execution']['status'] = 'FAILED'
    result['source_preserved'] = source.read_bytes() == original
    result['frozen_source_preserved'] = snapshot.read_bytes() == original
    result['executable_preserved'] = executable.read_bytes() == executable_bytes
    if not all(result[k] for k in ['source_preserved', 'frozen_source_preserved', 'executable_preserved']):
        result.update(status='REVIEW', error='Input, frozen input or dispatcher changed')
    result['execution'].update(finished_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(time.monotonic()-clock, 6), timeout_seconds=timeout_seconds)
    if any(path.is_symlink() for path in work.rglob('*')):
        result.update(status='REVIEW', error='Unexpected input-check output symlink')
    result['outputs'] = [{'anchor': 'contract_directory', 'path': p.relative_to(work).as_posix(),
        'sha256': _digest(p.read_bytes()), 'size': p.stat().st_size}
        for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    with (work / 'input_receipt.json').open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write('\n')
    return result


_OPTIONS_WORKER = '''import hashlib,importlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
spec=json.loads(Path(sys.argv[1]).read_text());destination=Path(sys.argv[2])
module=importlib.import_module('elbow.utilities.options_parser')
actual=Path(module.__file__).resolve()
if actual!=Path(spec['installed_module']).resolve():raise ValueError('Unselected eLBOW options module')
if hashlib.sha256(actual.read_bytes()).hexdigest()!=spec['module_sha256']:raise ValueError('Options module changed')
sys.argv=spec['command']
options,args,description=module.run()
result={'steps':options.opt_steps,'macro_override':getattr(options,'opt_macro_steps',False),
        'tolerance':options.opt_tol,'module_sha256':hashlib.sha256(actual.read_bytes()).hexdigest()}
destination.write_text(json.dumps(result,sort_keys=True)+'\\n')
'''


def audit_single_block_options(installation_root, python_executable, api_sources, source, code,
                               capabilities, output, *, environment, steps):
    """Interrogate installed option parsing; require exactly one effective block."""
    if type(steps) is not int or not 1 <= steps <= 600:
        raise ValueError('Invalid single-block step request')
    root=Path(installation_root).resolve(strict=True);output=Path(output).absolute()
    python_executable=Path(python_executable).resolve(strict=True)
    if not python_executable.is_relative_to(root) or output.resolve().is_relative_to(root):
        raise ValueError('Require selected Phenix Python and a separate options-audit directory')
    anchors=[r for r in api_sources if r.get('anchor')=='phenix_installation' and _safe(r.get('path')) and r['path'].endswith('/iotbx/phil.py')]
    if len(anchors)!=1:raise ValueError('Require one verified installed library anchor')
    relative=(PurePosixPath(anchors[0]['path']).parent.parent/'elbow/utilities/options_parser.py').as_posix()
    module=_inside(root,relative);data=module.read_bytes()
    if len(data)>MAX_SOURCE_BYTES:raise ValueError('Oversized installed options module')
    definitions=capabilities.get('supported_option_definitions',{})
    flag=next((k for k in ['--opt-steps','--opt_steps'] if definitions.get(k) is True),None)
    if flag is None:raise ValueError('Installed help has no valued step-control option')
    aliases=capabilities['selected_aliases']
    command=['phenix.elbow','source.cif',f"{aliases['id']}={code}",f"{aliases['output']}=candidate",
        f"{aliases['template']}=source_ideal.pdb",f"{aliases['initial_geometry']}=source_ideal.pdb",
        f"{aliases['add_hydrogens']}=False",f"{aliases['source_state_preservation']}=low",f"{aliases['chiral']}=retain",aliases['opt'],f'{flag}={steps}']
    output.mkdir(parents=True,exist_ok=False)
    (output/'source.cif').write_bytes(Path(source).read_bytes())
    (output/'source_ideal.pdb').write_text(_ideal_seed(Path(source),code)[0])
    (output/'options_parser.py.txt').write_bytes(data)
    (output/'options_worker.py').write_text(_OPTIONS_WORKER)
    spec={'installed_module':str(module),'module_sha256':_digest(data),'command':command}
    (output/'options_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    with (output/'options_worker.log').open('xb') as log:
        process=subprocess.Popen([str(python_executable),'options_worker.py','options_spec.json','options_result.json'],
            cwd=output,env=dict(environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
        try:returncode=process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            _terminate_owned_group(process);raise ValueError('Installed options audit timed out')
        except BaseException:
            _terminate_owned_group(process);raise
    if returncode!=0 or not (output/'options_result.json').is_file():raise ValueError('Installed options audit failed; inspect options_worker.log')
    parsed=json.loads((output/'options_result.json').read_text());oms=parsed['macro_override']
    try:effective_blocks=1 if oms==False else int(oms)
    except (ValueError,TypeError) as exc:raise ValueError('Unsupported installed macro-step override') from exc
    if parsed['steps']!=steps or effective_blocks!=1 or parsed['module_sha256']!=_digest(data):
        raise ValueError('Installed options do not select exactly one requested optimization block')
    report={'policy_id':'cif-installed-single-block-option-proof-v1','status':'SINGLE_BLOCK_OPTIONS_PASS',
        'steps':steps,'effective_blocks':effective_blocks,'macro_override':oms,'tolerance':parsed['tolerance'],
        'source':{'anchor':'phenix_installation','path':relative,'sha256':_digest(data),'size':len(data)},
        'snapshot':{'anchor':'contract_directory','path':'options_parser.py.txt'},
        'installed_module_execution':'OPTIONS_PARSER_ONLY','captured_code_execution':'NOT_RUN',
        'optimization_execution':'NOT_RUN','convergence_claimed':False}
    verify_single_block_options(root,report,output)
    (output/'options_receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def verify_single_block_options(installation_root, report, output):
    root=Path(installation_root).resolve(strict=True);output=Path(output).resolve(strict=True)
    row=report['source']
    if row.get('anchor')!='phenix_installation' or report['snapshot'].get('anchor')!='contract_directory':raise ValueError('Unsupported options source anchor')
    for path in [_inside(root,row['path']),_inside(output,report['snapshot']['path'])]:
        data=path.read_bytes()
        if len(data)!=row['size'] or _digest(data)!=row['sha256']:raise ValueError('Installed or captured options module changed')
    return True
