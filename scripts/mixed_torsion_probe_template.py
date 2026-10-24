#!/usr/bin/env python3
"""Audit native torsions at saved mixed-model coordinates with finer numerical steps.

One bounded fixed-coordinate diagnostic; no optimization, chemical changes,
refinement or adoption. The original usable coordinate decision is preserved.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

BUNDLE = None  # @bundle-metadata@
RUNTIME_BASE64 = None  # @runtime-base64@
REVIEW_SHA256 = 'b9d100bf2366fc524921f053b91262a26a848910c3ddf581d49be865f004f44e'
GEOMETRY_PARENT_SHA256 = '19299c870e48f907097879e37735b972c9da7a7597aa08dc633238ebdfb0c654'
GEOMETRY_PREFIX = 'mixed_geometry/'
GRADIENT_PREFIX = 'mixed_gradient/'
CONTEXT_PREFIX = 'inputs/review/inputs/review/mixed_context/'
PARENT_PREFIX = 'inputs/review/inputs/review/inputs/review/inputs/review/inputs/review/mixed_linked_recovery/'
NATIVE_OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'PHENIX', 'PHENIX_ROOT', 'PHENIX_VERSION',
                    'LIBTBX_BUILD', 'LIBTBX_DIST', 'BOOST_ADAPTBX_FPE_DEFAULT'}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe(name):
    return (isinstance(name, str) and bool(name) and not name.startswith('/')
            and '\\' not in name and ':' not in name
            and not any(ord(c) < 32 or ord(c) == 127 for c in name)
            and all(p not in {'', '.', '..'} for p in name.split('/')))


def _runtime_members():
    if not isinstance(BUNDLE, dict) or not isinstance(RUNTIME_BASE64, str):
        raise ValueError('Use the assembled probe, not its source template')
    data = base64.b64decode(RUNTIME_BASE64, validate=True)
    if _sha(data) != BUNDLE['runtime_archive_sha256']:
        raise ValueError('Runtime archive checksum differs')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries = z.infolist()
        if (len(entries) > 512 or len(entries) != len({e.filename for e in entries})
                or sum(e.file_size for e in entries) > 32 * 1024 * 1024
                or any(not _safe(e.filename) or e.is_dir() or e.flag_bits & 1
                       or stat.S_IFMT(e.external_attr >> 16) not in {0, stat.S_IFREG}
                       or e.file_size > 8 * 1024 * 1024 for e in entries)):
            raise ValueError('Unsafe or oversized runtime archive')
        members = {e.filename: z.read(e) for e in entries}
    if set(members) != set(BUNDLE['runtime_files']):
        raise ValueError('Runtime inventory differs')
    for name, value in members.items():
        ref = BUNDLE['runtime_files'][name]
        if len(value) != ref['size'] or _sha(value) != ref['sha256']:
            raise ValueError('Runtime member checksum differs')
    return members


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    with path.open('xb') as handle:
        handle.write(data)


def _configuration_source():
    if os.environ.get('NASOLVE_CONFIG_FILE'):
        return Path(os.environ['NASOLVE_CONFIG_FILE']).expanduser()
    if sys.platform == 'darwin':
        return Path.home()/'Library/Application Support/NASolve/config.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))/'nasolve/config.json'


def _isolate(runtime, session, members):
    if any(n == p or n.startswith(p+'.') for n in sys.modules for p in ['nasolve', 'restraints']):
        raise ValueError('Start the probe in a fresh Python process')
    config = {'schema_version': 1}
    source = _configuration_source()
    if source.is_file():
        old = json.loads(source.read_bytes())
        if not isinstance(old, dict):
            raise ValueError('Saved configuration must be an object')
        config.update({k: old[k] for k in ['phenix', 'coot'] if k in old})
    _write(session/'runtime-config.json', config)
    for name, data in members.items():
        _write(runtime/name, data)
    sys.path[:0] = [str(runtime/'src'), str(runtime)]
    os.environ['PYTHONPATH'] = os.pathsep.join(sys.path[:2])
    os.environ['NASOLVE_CONFIG_FILE'] = str(session/'runtime-config.json')
    os.environ['NASOLVE_NATIVE_ENV_ISOLATION'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    sys.dont_write_bytecode = True


def _save_receipt(session, receipt):
    path = session/'probe_receipt.json'
    if path.is_symlink():
        raise ValueError('Receipt cannot be a symlink')
    descriptor, temporary = tempfile.mkstemp(prefix='.receipt-', dir=session)
    try:
        with os.fdopen(descriptor, 'w') as handle:
            json.dump(receipt, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _review_zip(session, *, receipt_only=False):
    token = session.name.rsplit('-', 1)[-1]
    suffix = '_failure_review.zip' if receipt_only else '_mixed_torsion_review.zip'
    destination = session/(BUNDLE['delivery_prefix']+'_'+token+suffix)
    if receipt_only:
        files = {'probe_receipt.json': (session/'probe_receipt.json').read_bytes()}
    else:
        from nasolve.cif_review_transport import review_archive_files
        files = review_archive_files(session, destination)
    manifest = json.dumps({n: {'sha256': _sha(d), 'bytes': len(d)}
                           for n, d in files.items()}, indent=2).encode()
    if (len(files)+1 > 1024 or sum(map(len, files.values()))+len(manifest) > 128*1024*1024
            or any(len(d) > 32*1024*1024 for d in [*files.values(), manifest])):
        raise ValueError('Review output exceeds the unchanged archive bounds')
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', manifest)
    return destination


def _report_failure(session, receipt, exc):
    """Keep the first failure and a receipt when full collection is unavailable."""
    receipt.update(analysis_completed=False, error_type=type(exc).__name__, error=str(exc))
    _save_receipt(session, receipt)
    try:
        return _review_zip(session)
    except Exception as collection_error:
        receipt.update(archive_collection_error=str(collection_error),
                       failure_archive_scope='RECEIPT_ONLY; OTHER_OUTPUTS_REMAIN_IN_SESSION')
        _save_receipt(session, receipt)
        return _review_zip(session, receipt_only=True)


def _bound_member(members, reference, *, anchor, prefix=''):
    if (not isinstance(reference, dict) or reference.get('anchor') != anchor
            or not _safe(reference.get('path')) or type(reference.get('size')) is not int):
        raise ValueError('Unbound saved evidence reference')
    data = members.get(prefix+reference['path'])
    if not isinstance(data, bytes) or reference != {'anchor': anchor, 'path': reference['path'],
            'sha256': _sha(data), 'size': len(data)}:
        raise ValueError('Saved evidence reference bytes differ')
    return data


def _archive_members(original, expected_sha256):
    from nasolve.cif_review_transport import is_safe_review_member, _parse_json
    if len(original) > 32*1024*1024 or _sha(original) != expected_sha256:
        raise ValueError('Require the exact bounded verified parent ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries = archive.infolist()
        if (len(entries) > 1024 or len(entries) != len({e.filename for e in entries})
                or sum(e.file_size for e in entries) > 128*1024*1024
                or any(not is_safe_review_member(e.filename) or e.is_dir() or e.flag_bits & 1
                       or stat.S_IFMT(e.external_attr >> 16) not in {0, stat.S_IFREG}
                       or e.file_size > 32*1024*1024 for e in entries)):
            raise ValueError('Unsafe or oversized review archive')
        members = {entry.filename: archive.read(entry) for entry in entries}
    manifest = _parse_json(members['manifest.json'])
    if not isinstance(manifest, dict) or set(manifest) != set(members)-{'manifest.json'}:
        raise ValueError('Review inventory differs')
    for name, ref in manifest.items():
        if (not isinstance(ref, dict) or type(ref.get('bytes')) is not int
                or ref != {'sha256': _sha(members[name]), 'bytes': len(members[name])}):
            raise ValueError('Review member checksum differs')
    return members


def _c89_members(original):
    from nasolve.cif_review_transport import _parse_json
    members = _archive_members(original, GEOMETRY_PARENT_SHA256)
    receipt = _parse_json(members['probe_receipt.json'])
    data = members['mixed_gradient/mixed_initial_gradients.json']
    report = _parse_json(data)
    qualification = _parse_json(_bound_member(members, report.get('qualification', {}).get('artifact'),
        anchor='mixed_initial_gradient_directory', prefix=GRADIENT_PREFIX))
    expected = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_gradient'},
        'report_sha256': _sha(data), 'report_size': len(data),
        'status': 'MIXED_INITIAL_DERIVATIVES_PASS', 'new_native_calls': 1}
    checks = {'captured_raw_snapshot', 'complete_both_order_plane_derivatives_and_controls',
        'complete_initial_sampled_derivatives', 'unchanged_native_energy', 'unchanged_static_constraint_signature'}
    if (receipt.get('schema_version') != 1 or receipt.get('kind') != 'mixed-gradient-probe'
            or receipt.get('delivery_prefix') != '89_Cedar' or receipt.get('analysis_completed') is not True
            or receipt.get('automatic_adoption') is not False or receipt.get('requires_cif_review') is not False
            or receipt.get('mixed_gradient') != expected
            or type(receipt.get('mixed_gradient', {}).get('new_native_calls')) is not int
            or report.get('schema_version') != 1 or report.get('policy_id') != 'cif-mixed-initial-native-gradient-v1'
            or report.get('status') != 'MIXED_INITIAL_DERIVATIVES_PASS'
            or type(report.get('new_native_calls')) is not int or report['new_native_calls'] != 1
            or report.get('automatic_adoption') is not False or report.get('requires_cif_review') is not False
            or report.get('scientific_qualification') != 'NOT_ASSESSED'
            or report.get('model_optimization') != 'NOT_RUN'
            or report.get('initial_coordinates_only') is not True
            or report.get('execution', {}).get('status') != 'COMPLETED'
            or type(report.get('execution', {}).get('returncode')) is not int
            or report['execution']['returncode'] != 0
            or report.get('coordinate_decision', {}).get('native_usable') is not True
            or report.get('qualification', {}).get('artifact', {}).get('path') != 'qualification.json'
            or qualification.get('policy_id') != report['policy_id']
            or qualification.get('status') != report['status'] or qualification.get('sampled_derivatives_pass') is not True
            or qualification.get('scientific_qualification') != 'NOT_ASSESSED'
            or qualification.get('automatic_adoption') is not False
            or qualification.get('checks') != {k: True for k in checks}
            or any(v is not True for v in qualification.get('checks', {}).values())):
        raise ValueError('Require the completed qualified C89 initial gradient evidence')
    return members


def _read_capsule(path):
    """Bind the completed C90 trial and its original C89 evidence, including failures."""
    from nasolve.cif_review_transport import _parse_json
    original = path.read_bytes()
    members = _archive_members(original, REVIEW_SHA256)
    receipt = _parse_json(members['probe_receipt.json'])
    report_data = members['mixed_geometry/mixed_geometry_trial.json']
    report = _parse_json(report_data)
    expected = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_geometry'},
        'report_sha256': _sha(report_data), 'report_size': len(report_data),
        'status': report.get('status'), 'new_native_calls': report.get('new_native_calls')}
    if (type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1
            or receipt.get('kind') != 'mixed-geometry-probe' or receipt.get('delivery_prefix') != '90_Cedar'
            or receipt.get('analysis_completed') is not True or receipt.get('automatic_adoption') is not False
            or receipt.get('requires_cif_review') is not False or receipt.get('mixed_geometry') != expected
            or receipt.get('parent_review_preserved') is not True
            or type(report.get('schema_version')) is not int or report['schema_version'] != 1
            or report.get('policy_id') != 'cif-mixed-qualified-geometry-trial-v1'
            or report.get('status') != 'REVIEW' or type(report.get('new_native_calls')) is not int
            or report['new_native_calls'] != 1 or type(receipt['mixed_geometry'].get('new_native_calls')) is not int
            or report.get('automatic_adoption') is not False or report.get('requires_cif_review') is not False
            or report.get('scientific_qualification') != 'NOT_ASSESSED'
            or report.get('model_optimization') != 'EXPLICIT_BOUNDED_FIXED_DEFINITION_TRIAL'
            or report.get('execution', {}).get('status') != 'COMPLETED'
            or type(report.get('execution', {}).get('returncode')) is not int or report['execution']['returncode'] != 0
            or report.get('coordinate_decision', {}).get('native_usable') is not True
            or report.get('coordinate_decision', {}).get('automatic_adoption') is not False
            or report.get('parent_archive_sha256') != GEOMETRY_PARENT_SHA256):
        raise ValueError('Require completed C90 fixed-trial evidence, including its endpoint findings')
    parent = _bound_member(members, receipt.get('parent_review', {}).get('artifact'), anchor='probe_directory')
    if receipt.get('parent_review', {}).get('preserved') is not True or _sha(parent) != GEOMETRY_PARENT_SHA256:
        raise ValueError('Original C89 parent binding differs')
    c89 = _c89_members(parent)
    if (type(receipt.get('parent_review', {}).get('payload_count')) is not int
            or receipt['parent_review']['payload_count'] != len(c89)-1):
        raise ValueError('Original C89 parent payload count differs')
    if path.read_bytes() != original:
        raise ValueError('Review archive changed while reading')
    return members


def _materialize_inputs(members, destination):
    """Write only four declared data views; captured programs are never imported."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Torsion data destination already exists')
    parent = _c89_members(members['inputs/parent_review.zip'])
    views = [(members, GEOMETRY_PREFIX, 'geometry', 'mixed_geometry_trial.json'),
             (parent, GRADIENT_PREFIX, 'gradient', 'mixed_initial_gradients.json'),
             (parent, CONTEXT_PREFIX, 'context', 'mixed_context.json'),
             (parent, PARENT_PREFIX, 'linked_parent', 'mixed_linked_recovery.json')]
    for source, prefix, _, report in views:
        if prefix+report not in source or any(not _safe(n) for n in source if n.startswith(prefix)):
            raise ValueError('Missing or unsafe declared torsion data view')
    for source, prefix, view, _ in views:
        for name, data in source.items():
            if name.startswith(prefix):
                _write(destination/view/name[len(prefix):], data)
    return tuple(destination/name for name in ['geometry', 'gradient', 'context', 'linked_parent'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, required=True, help='Exact verified C90 ZIP; original archives stay opaque, captured programs stay data')
    parser.add_argument('--phenix-root', type=Path, default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--inspect-only', action='store_true', help='Prepare the fixed torsion audit without an SDK process')
    parser.add_argument('--timeout-seconds', type=int, default=120, help='Deadline 1–600 seconds for each native process')
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 600:
        parser.error('The native deadline must be from 1 to 600 seconds')
    session = None
    receipt = {'schema_version': 1, 'kind': 'mixed-torsion-probe',
        'delivery_prefix': BUNDLE['delivery_prefix'] if isinstance(BUNDLE, dict) else None,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'build': BUNDLE,
        'analysis_completed': False, 'requires_cif_review': False, 'automatic_adoption': False,
        'policy_authority': 'NARestraints', 'coot_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
        'captured_code_execution': 'NOT_RUN', 'generation_execution': 'NOT_RUN',
        'model_optimization_requested': False, 'refinement': 'NOT_RUN', 'mtz_used': False,
        'production_checkpoint': 'NOT_CREATED', 'parent_transport': 'EXACT_OPAQUE_ZIP; NO_FLATTENED_ANCESTRY'}
    try:
        runtime_members = _runtime_members()
        for package in ['Bio', 'numpy', 'openpyxl']:
            __import__(package)
        parent = args.output_parent.expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-torsion-', dir=parent)).resolve()
        runtime = session/'runtime'
        _isolate(runtime, session, runtime_members)
        import nasolve, restraints
        for package in [nasolve, restraints]:
            if not Path(package.__file__).resolve().is_relative_to(runtime):
                raise ValueError('Probe imported an ambient runtime')
        source = args.review_zip.expanduser().resolve(strict=True)
        members = _read_capsule(source)
        original = source.read_bytes()
        if _sha(original) != REVIEW_SHA256:
            raise ValueError('Verified C90 archive changed before preservation')
        _write(session/'inputs/parent_review.zip', original)
        receipt['parent_review'] = {'artifact': {'anchor': 'probe_directory', 'path': 'inputs/parent_review.zip',
            'sha256': REVIEW_SHA256, 'size': len(original)}, 'historical_path': str(args.review_zip),
            'payload_count': len(members)-1, 'preserved': True,
            'scope': 'EXACT_C90_ZIP_OPAQUE; CAPTURED_CODE_NOT_EXECUTED'}
        phenix = None
        if not args.inspect_only:
            from nasolve.config import load_config
            from nasolve.phenix_runtime import discover_phenix
            environment = {k: v for k, v in os.environ.items() if k not in NATIVE_OVERRIDES}
            phenix = discover_phenix(load_config(), explicit=args.phenix_root, environ=environment)
            receipt['phenix'] = {'version': phenix.version, 'historical_root': str(phenix.root),
                'source': phenix.source, 'executables': {n: {'historical_path': str(p), 'sha256': _sha(p.read_bytes())}
                    for n, p in phenix.executables.items() if n == 'phenix.python'}}
        from nasolve.cif_mixed_torsion import audit_mixed_torsions, read_mixed_torsions
        print('Saved mixed-model torsion audit:', BUNDLE['delivery_prefix'], flush=True)
        print('Fixed saved coordinates, native torsions and NARestraints targets; no optimization or adoption.', flush=True)
        with tempfile.TemporaryDirectory(prefix='nasolve-mixed-torsion-parent-') as temporary:
            geometry, gradient, context, linked_parent = _materialize_inputs(members, Path(temporary).resolve()/'data')
            result = audit_mixed_torsions(geometry, gradient, context, linked_parent, phenix, session/'mixed_torsion',
                parent_archive_sha256=REVIEW_SHA256,
                timeout_seconds=args.timeout_seconds)
            if read_mixed_torsions(session/'mixed_torsion', geometry_directory=geometry, gradient_directory=gradient,
                    context_directory=context, linked_parent_directory=linked_parent,
                    parent_archive_sha256=REVIEW_SHA256) != result:
                raise ValueError('Portable mixed torsion report differs')
        data = (session/'mixed_torsion/mixed_torsion_audit.json').read_bytes()
        receipt['mixed_torsion'] = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_torsion'},
            'report_sha256': _sha(data), 'report_size': len(data), 'status': result['status'],
            'new_native_calls': result['new_native_calls']}
        if (source.read_bytes() != original or (session/'inputs/parent_review.zip').read_bytes() != original):
            raise ValueError('Original or preserved C90 ZIP changed')
        for name, data in runtime_members.items():
            if (runtime/name).read_bytes() != data:
                raise ValueError('Bundled runtime changed')
        receipt.update(analysis_completed=True, frozen_runtime_preserved=True, parent_review_preserved=True)
        _save_receipt(session, receipt)
        print('Mixed torsion audit:', result['status'], '; new native calls:', result['new_native_calls'], flush=True)
        summary = result.get('summary')
        if isinstance(summary, dict):
            print('Fixed-coordinate findings:', json.dumps(summary, sort_keys=True), flush=True)
        if result.get('error'):
            print('Follow-up:', result['error'], flush=True)
        print('Diagnostic: REVIEW (fixed-coordinate torsion evidence; original usable fallback and scientific qualification remain separate)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Mixed torsion audit stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None:
            try:
                print('REVIEW ZIP:', _report_failure(session, receipt, exc), flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())


