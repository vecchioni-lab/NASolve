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

from .cif_generation import _generator_capabilities, _terminate_owned_group

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
