#!/usr/bin/env python3
"""Recover deficient numerical dictionaries through the shared source-native route.

This is an isolated dictionary trial. The preserved mixed model and original
numerical definitions remain inputs; no linked adoption is requested.
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
REVIEW_SHA256 = '7ca288cfc14ac79174598e886f49f4c35a9cef2cbadc2d7ee13821f12f660b31'
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
    suffix = '_failure_review.zip' if receipt_only else '_mixed_recovery_review.zip'
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
    """Verify the known C82 return before exposing any saved data to readers.

    C82 includes two 20 MiB reports. Its explicit 128 MiB total / 32 MiB member
    limits preserve those real artifacts without relaxing embedded-runtime bounds.
    """
    from nasolve.cif_review_transport import is_safe_review_member, _parse_json
    original = path.read_bytes()
    if _sha(original) != REVIEW_SHA256:
        raise ValueError('Require the exact verified C82 mixed-native review ZIP')
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
    main = _parse_json(members['mixed_native/mixed_native.json'])
    if (receipt.get('kind') != 'mixed-eight-pair-native-probe' or receipt.get('delivery_prefix') != '82_Cedar'
            or receipt.get('analysis_completed') is not True or main.get('status') != 'REVIEW'
            or receipt.get('mixed_native') != {'directory': {'anchor': 'probe_directory', 'path': 'mixed_native'}, **main}):
        raise ValueError('Require the exact completed C82 mixed-native evidence')
    if path.read_bytes() != original:
        raise ValueError('Review archive changed while reading')
    return members


def _materialize_native(members, destination):
    """Make an owned shallow data view; captured programs are never executed."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Parent data destination already exists')
    prefix = 'mixed_native/'
    for name, data in members.items():
        if name.startswith(prefix) and _safe(name):
            _write(destination/name[len(prefix):], data)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, required=True, help='Exact verified C82 ZIP; captured programs stay data')
    parser.add_argument('--phenix-root', type=Path, default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--inspect-only', action='store_true', help='Verify and stage source-bound recovery without an SDK process')
    parser.add_argument('--single-block-steps', type=int, default=180, help='Native dictionary optimization steps, 1–600')
    parser.add_argument('--timeout-seconds', type=int, default=600, help='Builder deadline 1–600 seconds; isolated reads at most 60 seconds each')
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 600 or not 1 <= args.single_block_steps <= 600:
        parser.error('Step and deadline values must be from 1 to 600')
    session = None
    receipt = {'schema_version': 1, 'kind': 'mixed-deficient-numerics-recovery-probe',
        'delivery_prefix': BUNDLE['delivery_prefix'] if isinstance(BUNDLE, dict) else None,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'build': BUNDLE,
        'analysis_completed': False, 'requires_cif_review': False, 'automatic_adoption': False,
        'policy_authority': 'NARestraints', 'coot_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
        'captured_code_execution': 'NOT_RUN', 'model_optimization_requested': False,
        'refinement': 'NOT_RUN', 'mtz_used': False, 'production_checkpoint': 'NOT_CREATED'}
    try:
        runtime_members = _runtime_members()
        for package in ['Bio', 'numpy', 'openpyxl']:
            __import__(package)
        parent = args.output_parent.expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-recovery-', dir=parent)).resolve()
        runtime = session/'runtime'
        _isolate(runtime, session, runtime_members)
        import nasolve, restraints
        for package in [nasolve, restraints]:
            if not Path(package.__file__).resolve().is_relative_to(runtime):
                raise ValueError('Probe imported an ambient runtime')
        members = _read_capsule(args.review_zip.expanduser().resolve(strict=True))
        from nasolve.cif_review_transport import stage_review_members, staged_review_members_match
        stage_review_members(members, session/'inputs/review', indexed=True)
        receipt['parent_review'] = {'historical_path': str(args.review_zip), 'sha256': REVIEW_SHA256,
            'payload_count': len(members)-1, 'preserved': True,
            'scope': 'EXACT_C82_PARENT; INDEXED_OPAQUE_TRANSPORT; CAPTURED_CODE_NOT_EXECUTED'}
        phenix = None
        if not args.inspect_only:
            from nasolve.config import load_config
            from nasolve.phenix_runtime import discover_phenix
            environment = {k: v for k, v in os.environ.items() if k not in NATIVE_OVERRIDES}
            phenix = discover_phenix(load_config(), explicit=args.phenix_root, environ=environment)
            receipt['phenix'] = {'version': phenix.version, 'historical_root': str(phenix.root),
                'source': phenix.source, 'executables': {n: {'historical_path': str(p), 'sha256': _sha(p.read_bytes())}
                    for n, p in phenix.executables.items() if n in {'phenix.python','phenix.elbow'}}}
        from nasolve.cif_mixed_recovery import audit_mixed_recovery, read_mixed_recovery
        from nasolve.cif_mixed_native import read_mixed_native
        print('Source-bound deficient-numerics recovery:', BUNDLE['delivery_prefix'], flush=True)
        print('Selecting deficient components by numerical evidence; retaining the mixed model and original definitions.', flush=True)
        # The full parent remains indexed. Its large scientific read view is
        # temporary and does not recursively duplicate reports in the new ZIP.
        with tempfile.TemporaryDirectory(prefix='nasolve-mixed-recovery-parent-') as temporary:
            view = _materialize_native(members, Path(temporary).resolve()/'data')
            read_mixed_native(view)
            result = audit_mixed_recovery(view, phenix, session/'mixed_recovery',
                single_block_steps=args.single_block_steps, timeout_seconds=args.timeout_seconds)
        if read_mixed_recovery(session/'mixed_recovery') != result:
            raise ValueError('Portable recovery report differs after parent view removal')
        receipt['mixed_recovery'] = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_recovery'}, **result}
        if not staged_review_members_match(members, session/'inputs/review'):
            raise ValueError('Preserved parent review differs')
        for name, data in runtime_members.items():
            if (runtime/name).read_bytes() != data:
                raise ValueError('Bundled runtime changed')
        receipt.update(analysis_completed=True, frozen_runtime_preserved=True, parent_review_preserved=True)
        _save_receipt(session, receipt)
        print('Selected components:', ', '.join(result.get('components', {})), flush=True)
        print('Isolated recovery:', result['status'], flush=True)
        if result.get('error'):
            print('Follow-up:', result['error'], flush=True)
        print('Diagnostic: REVIEW (separate source-bound candidates; linked adoption and full-run qualification remain open)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Mixed recovery test stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None:
            try:
                print('REVIEW ZIP:', _report_failure(session, receipt, exc), flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
