#!/usr/bin/env python3
"""Normalize explicitly declared DNA linkage context at fixed mixed-model coordinates.

Source-declared group metadata and incoming OP3 modifiers are separate from
source-state repair, optimization and production adoption.
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
REVIEW_SHA256 = '8e665aef19f2c0f47d6668944a0b60c95dfe2a608f04c2ada74aa171d1030661'
RETRY_REVIEW_SHA256 = '7b8fa0ee11065b58795937cdc7a2087bdad24002046508159a2d99ffac27426f'
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
    suffix = '_failure_review.zip' if receipt_only else '_mixed_context_review.zip'
    destination = session/(BUNDLE['delivery_prefix']+'_'+token+suffix)
    if receipt_only:
        files = {'probe_receipt.json': (session/'probe_receipt.json').read_bytes()}
    else:
        from nasolve.cif_review_transport import review_archive_files
        files = review_archive_files(session, destination)
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', json.dumps({n: {'sha256': _sha(d), 'bytes': len(d)}
                                                     for n, d in files.items()}, indent=2))
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


def _read_capsule(path):
    """Verify a pinned C85 replay or C86 context return; programs stay data."""
    from nasolve.cif_review_transport import is_safe_review_member, _parse_json
    original = path.read_bytes()
    digest = _sha(original)
    if digest not in {REVIEW_SHA256, RETRY_REVIEW_SHA256}:
        raise ValueError('Require the exact verified C85 or C86 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries = archive.infolist()
        if (len(entries) > 1024 or len(entries) != len({e.filename for e in entries})
                or sum(e.file_size for e in entries) > 128 * 1024 * 1024
                or any(not is_safe_review_member(e.filename) or e.is_dir() or e.flag_bits & 1
                       or stat.S_IFMT(e.external_attr >> 16) not in {0, stat.S_IFREG}
                       or e.file_size > 32 * 1024 * 1024 for e in entries)):
            raise ValueError('Unsafe or oversized review archive')
        members = {entry.filename: archive.read(entry) for entry in entries}
    manifest = _parse_json(members['manifest.json'])
    if not isinstance(manifest, dict) or set(manifest) != set(members) - {'manifest.json'}:
        raise ValueError('Review inventory differs')
    for name, ref in manifest.items():
        if (not isinstance(ref, dict) or type(ref.get('bytes')) is not int
                or ref != {'sha256': _sha(members[name]), 'bytes': len(members[name])}):
            raise ValueError('Review member checksum differs')
    receipt = _parse_json(members['probe_receipt.json'])
    if digest == RETRY_REVIEW_SHA256:
        data = members['mixed_context/mixed_context.json']
        report = _parse_json(data)
        reference = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_context'},
            'report_sha256': _sha(data), 'report_size': len(data), 'status': 'REVIEW',
            'targets': report.get('targets'), 'new_native_calls': 1}
        if (receipt.get('kind') != 'mixed-context-probe' or receipt.get('delivery_prefix') != '86_Cedar'
                or receipt.get('analysis_completed') is not True
                or receipt.get('automatic_adoption') is not False or receipt.get('requires_cif_review') is not False
                or receipt.get('mixed_context') != reference
                or report.get('schema_version') != 1 or report.get('policy_id') != 'cif-mixed-linked-context-v1'
                or report.get('status') != 'REVIEW' or type(report.get('new_native_calls')) is not int
                or report['new_native_calls'] != 1 or report.get('saved_native_calls') != 2
                or report.get('automatic_adoption') is not False or report.get('requires_cif_review') is not False
                or report.get('native_active') != {'status': 'NOT_RUN'}
                or report.get('qualification') != {'status': 'NOT_RUN'}):
            raise ValueError('Require the exact completed C86 context evidence')
        if path.read_bytes() != original:
            raise ValueError('Review archive changed while reading')
        return members
    data = members['saved_linked_recovery.json']
    summary = _parse_json(data)
    artifact = {'anchor': 'probe_directory', 'path': 'saved_linked_recovery.json',
        'sha256': _sha(data), 'size': len(data)}
    if (receipt.get('kind') != 'mixed-linked-recovery-probe' or receipt.get('delivery_prefix') != '85_Cedar'
            or receipt.get('analysis_completed') is not True
            or receipt.get('automatic_adoption') is not False or receipt.get('requires_cif_review') is not False
            or receipt.get('saved_linked_recovery') != {'artifact': artifact, 'status': 'REVIEW',
                'saved_native_calls': 2, 'new_native_calls': 0}
            or summary.get('policy_id') != 'cif-saved-mixed-linked-recovery-v1'
            or summary.get('status') != 'REVIEW' or summary.get('schema_version') != 1
            or type(summary.get('saved_native_calls')) is not int or summary['saved_native_calls'] != 2
            or type(summary.get('new_native_calls')) is not int or summary['new_native_calls'] != 0
            or summary.get('automatic_adoption') is not False or summary.get('requires_cif_review') is not False):
        raise ValueError('Require the exact completed C85 saved linked-native evidence')
    if path.read_bytes() != original:
        raise ValueError('Review archive changed while reading')
    return members


def _capsule_identity(members):
    """Choose an explicit lineage anchor, never a basename search."""
    from nasolve.cif_review_transport import _parse_json
    receipt = _parse_json(members['probe_receipt.json'])
    if receipt.get('kind') == 'mixed-context-probe' and receipt.get('delivery_prefix') == '86_Cedar':
        return 'C86', RETRY_REVIEW_SHA256, 'inputs/review/inputs/review/mixed_linked_recovery/'
    if receipt.get('kind') == 'mixed-linked-recovery-probe' and receipt.get('delivery_prefix') == '85_Cedar':
        return 'C85', REVIEW_SHA256, 'inputs/review/mixed_linked_recovery/'
    raise ValueError('Unrecognized explicit context parent lineage')


def _materialize_parent(members, destination):
    """Make only the explicit linked-parent scientific view, outside the result."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Parent data destination already exists')
    _, _, prefix = _capsule_identity(members)
    for name, data in members.items():
        if name.startswith(prefix):
            if not _safe(name):
                raise ValueError('Unsafe linked-parent member')
            _write(destination/name[len(prefix):], data)
    if not (destination/'mixed_linked_recovery.json').is_file():
        raise ValueError('Missing declared linked-parent scientific view')
    return destination


def _verify_previous_context(members, linked_parent, destination):
    """Replay the preserved C86 failure with trusted current code only."""
    from nasolve.cif_mixed_context import read_mixed_context
    if _capsule_identity(members)[0] != 'C86':
        raise ValueError('Previous context replay requires the declared C86 return')
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Previous context destination already exists')
    prefix = 'mixed_context/'
    for name, data in members.items():
        if name.startswith(prefix):
            if not _safe(name):
                raise ValueError('Unsafe previous context member')
            _write(destination/name[len(prefix):], data)
    if not (destination/'mixed_context.json').is_file():
        raise ValueError('Missing declared C86 context report')
    result = read_mixed_context(destination, linked_parent_directory=linked_parent)
    if (result.get('policy_id') != 'cif-mixed-linked-context-v1' or result.get('status') != 'REVIEW'
            or result.get('new_native_calls') != 1 or result.get('qualification') != {'status': 'NOT_RUN'}
            or result.get('native_active') != {'status': 'NOT_RUN'}):
        raise ValueError('Previous context verdict or execution differs')
    data = members['mixed_context/mixed_context.json']
    return {'artifact': {'anchor': 'parent_review', 'path': 'mixed_context/mixed_context.json',
        'sha256': _sha(data), 'size': len(data)}, 'policy_id': result['policy_id'],
        'status': result['status'], 'historical_native_calls': result['new_native_calls'],
        'new_native_calls': 0, 'scope': 'SAVED_C86_FAILURE_REPLAY; CAPTURED_PROGRAMS_NOT_EXECUTED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, required=True, help='Exact verified C85 or C86 ZIP; captured programs stay data')
    parser.add_argument('--phenix-root', type=Path, default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--inspect-only', action='store_true', help='Prepare explicit context candidates without an SDK process')
    parser.add_argument('--timeout-seconds', type=int, default=60, help='Deadline 1–60 seconds for each fixed native read')
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 60:
        parser.error('The native deadline must be from 1 to 60 seconds')
    session = None
    receipt = {'schema_version': 1, 'kind': 'mixed-context-probe',
        'delivery_prefix': BUNDLE['delivery_prefix'] if isinstance(BUNDLE, dict) else None,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'build': BUNDLE,
        'analysis_completed': False, 'requires_cif_review': False, 'automatic_adoption': False,
        'policy_authority': 'NARestraints', 'coot_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
        'captured_code_execution': 'NOT_RUN', 'generation_execution': 'NOT_RUN', 'model_optimization_requested': False,
        'refinement': 'NOT_RUN', 'mtz_used': False, 'production_checkpoint': 'NOT_CREATED'}
    try:
        runtime_members = _runtime_members()
        for package in ['Bio', 'numpy', 'openpyxl']:
            __import__(package)
        parent = args.output_parent.expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-context-', dir=parent)).resolve()
        runtime = session/'runtime'
        _isolate(runtime, session, runtime_members)
        import nasolve, restraints
        for package in [nasolve, restraints]:
            if not Path(package.__file__).resolve().is_relative_to(runtime):
                raise ValueError('Probe imported an ambient runtime')
        members = _read_capsule(args.review_zip.expanduser().resolve(strict=True))
        from nasolve.cif_review_transport import stage_review_members, staged_review_members_match
        stage_review_members(members, session/'inputs/review', indexed=True)
        lineage, digest, _ = _capsule_identity(members)
        receipt['parent_review'] = {'historical_path': str(args.review_zip), 'sha256': digest,
            'payload_count': len(members)-1, 'preserved': True,
            'scope': 'EXACT_'+lineage+'_PARENT; INDEXED_OPAQUE_TRANSPORT; CAPTURED_CODE_NOT_EXECUTED'}
        phenix = None
        if not args.inspect_only:
            from nasolve.config import load_config
            from nasolve.phenix_runtime import discover_phenix
            environment = {k: v for k, v in os.environ.items() if k not in NATIVE_OVERRIDES}
            phenix = discover_phenix(load_config(), explicit=args.phenix_root, environ=environment)
            receipt['phenix'] = {'version': phenix.version, 'historical_root': str(phenix.root),
                'source': phenix.source, 'executables': {n: {'historical_path': str(p), 'sha256': _sha(p.read_bytes())}
                    for n, p in phenix.executables.items() if n == 'phenix.python'}}
        from nasolve.cif_mixed_context import audit_mixed_context, read_mixed_context
        print('Explicit mixed-model DNA context:', BUNDLE['delivery_prefix'], flush=True)
        print('Preserving coordinates, numerical targets and the declared NARestraints policy.', flush=True)
        with tempfile.TemporaryDirectory(prefix='nasolve-mixed-context-parent-') as temporary:
            linked_parent = _materialize_parent(members, Path(temporary).resolve()/'data')
            if lineage == 'C86':
                receipt['previous_context'] = _verify_previous_context(
                    members, linked_parent, Path(temporary).resolve()/'previous_context')
            result = audit_mixed_context(linked_parent, phenix, session/'mixed_context',
                timeout_seconds=args.timeout_seconds)
            if read_mixed_context(session/'mixed_context', linked_parent_directory=linked_parent) != result:
                raise ValueError('Portable context report differs')
        report_bytes = (session/'mixed_context/mixed_context.json').read_bytes()
        receipt['mixed_context'] = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_context'},
            'report_sha256': _sha(report_bytes), 'report_size': len(report_bytes), 'status': result['status'],
            'targets': result['targets'], 'new_native_calls': result['new_native_calls']}
        if not staged_review_members_match(members, session/'inputs/review'):
            raise ValueError('Preserved parent review differs')
        for name, data in runtime_members.items():
            if (runtime/name).read_bytes() != data:
                raise ValueError('Bundled runtime changed')
        receipt.update(analysis_completed=True, frozen_runtime_preserved=True, parent_review_preserved=True)
        _save_receipt(session, receipt)
        print('Selected components:', ', '.join(result.get('targets', [])), flush=True)
        print('Mixed context:', result['status'], '; new native calls:', result['new_native_calls'], flush=True)
        if result.get('error'):
            print('Follow-up:', result['error'], flush=True)
        print('Diagnostic: REVIEW (explicit context mechanics; source-state findings and full-run qualification remain separate)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Mixed context test stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None:
            try:
                print('REVIEW ZIP:', _report_failure(session, receipt, exc), flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
