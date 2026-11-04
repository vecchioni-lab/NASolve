#!/usr/bin/env python3
"""Read the verified eight-pair construction through ordinary ReadySet and native restraints.

This is an MTZ-free fixed-model diagnostic. No Coot construction, model
optimization, refinement or production checkpoint is requested.
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
REVIEW_SHA256 = 'ab023d3df1269d83634b764e6ce12b711e49e22f485c4d61db51b45af0aecca7'
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
    suffix = '_failure_review.zip' if receipt_only else '_mixed_native_review.zip'
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
    """Read the exact independently verified C81 return as data only."""
    from nasolve.cif_review_transport import is_safe_review_member
    original = path.read_bytes()
    if _sha(original) != REVIEW_SHA256:
        raise ValueError('Require the exact verified C81 mixed-pair review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries = archive.infolist()
        if (len(entries) > 512 or len(entries) != len({e.filename for e in entries})
                or sum(e.file_size for e in entries) > 32 * 1024 * 1024
                or any(not is_safe_review_member(e.filename) or e.is_dir() or e.flag_bits & 1
                       or stat.S_IFMT(e.external_attr >> 16) not in {0, stat.S_IFREG}
                       or e.file_size > 8 * 1024 * 1024 for e in entries)):
            raise ValueError('Unsafe or oversized review archive')
        members = {entry.filename: archive.read(entry) for entry in entries}
    from nasolve.cif_review_transport import _parse_json
    manifest = _parse_json(members['manifest.json'])
    if set(manifest) != set(members) - {'manifest.json'}:
        raise ValueError('Review inventory differs')
    for name, ref in manifest.items():
        if ref != {'sha256': _sha(members[name]), 'bytes': len(members[name])}:
            raise ValueError('Review member checksum differs')
    receipt = _parse_json(members['probe_receipt.json'])
    if (receipt.get('kind') != 'mixed-eight-pair-construction-probe'
            or receipt.get('delivery_prefix') != '81_Cedar' or receipt.get('analysis_completed') is not True
            or receipt.get('mixed_pair_fixture', {}).get('status') != 'MIXED_PAIR_CONSTRUCTION_PASS'):
        raise ValueError('Require completed C81 mixed construction evidence')
    if path.read_bytes() != original:
        raise ValueError('Review archive changed while reading')
    return members


def _materialize_fixture(members, destination):
    """Materialize bounded scientific data; captured programs stay opaque."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Fixture destination already exists')
    suffixes = {'.json', '.pdb', '.cif', '.phil', '.eff', '.txt', '.log'}
    prefix = 'postmr_construction/'
    for name, data in members.items():
        if name.startswith(prefix) and _safe(name) and Path(name).suffix in suffixes:
            _write(destination/name[len(prefix):], data)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, required=True, help='Exact verified C81 review ZIP; read as data only')
    parser.add_argument('--phenix-root', type=Path, default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--inspect-only', action='store_true', help='Stage and check fixed inputs without Phenix or ReadySet')
    parser.add_argument('--timeout-seconds', type=int, default=600, help='ReadySet deadline 1–600 seconds; each native read at most 60 seconds')
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 600:
        parser.error('--timeout-seconds must be from 1 to 600')
    session = None
    receipt = {'schema_version': 1, 'kind': 'mixed-eight-pair-native-probe',
        'delivery_prefix': BUNDLE['delivery_prefix'] if isinstance(BUNDLE, dict) else None,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'build': BUNDLE,
        'analysis_completed': False, 'requires_cif_review': False, 'automatic_adoption': False,
        'policy_authority': 'NARestraints', 'coot_execution': 'NOT_RUN',
        'captured_code_execution': 'NOT_RUN', 'model_optimization_requested': False,
        'refinement': 'NOT_RUN', 'mtz_used': False, 'production_checkpoint': 'NOT_CREATED'}
    try:
        runtime_members = _runtime_members()
        for package in ['Bio', 'numpy', 'openpyxl']:
            __import__(package)
        parent = args.output_parent.expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-native-', dir=parent)).resolve()
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
            'scope': 'EXACT_C81_PARENT; INDEXED_OPAQUE_TRANSPORT; CAPTURED_CODE_NOT_EXECUTED'}
        fixture = _materialize_fixture(members, session/'fixture')
        from nasolve.cif_mixed_pair_fixture import read_mixed_pair_fixture
        report = read_mixed_pair_fixture(fixture)
        if report != json.loads(members['postmr_construction/mixed_pair_fixture.json']):
            raise ValueError('Frozen fixture reconstruction differs')
        receipt['construction_status'] = report['status']
        phenix = None
        if not args.inspect_only:
            from nasolve.config import load_config
            from nasolve.phenix_runtime import discover_phenix
            environment = {k: v for k, v in os.environ.items() if k not in NATIVE_OVERRIDES}
            phenix = discover_phenix(load_config(), explicit=args.phenix_root, environ=environment)
            receipt['phenix'] = {'version': phenix.version, 'historical_root': str(phenix.root),
                'source': phenix.source, 'executables': {n: {'historical_path': str(p), 'sha256': _sha(p.read_bytes())}
                    for n, p in phenix.executables.items() if n in {'phenix.python','phenix.ready_set'}}}
        from nasolve.cif_mixed_native import audit_mixed_native, read_mixed_native
        print('Mixed-pair ReadySet/native readback:', BUNDLE['delivery_prefix'], flush=True)
        print('Preserving C81 coordinates and source authority; NARestraints controls all declared pairs/stacks.', flush=True)
        result = audit_mixed_native(fixture, phenix, session/'mixed_native', timeout_seconds=args.timeout_seconds)
        if read_mixed_native(session/'mixed_native') != result:
            raise ValueError('Portable mixed-native report differs')
        receipt['mixed_native'] = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_native'}, **result}
        if not staged_review_members_match(members, session/'inputs/review'):
            raise ValueError('Preserved parent review differs')
        for name, data in runtime_members.items():
            if (runtime/name).read_bytes() != data:
                raise ValueError('Bundled runtime changed')
        receipt.update(analysis_completed=True, frozen_runtime_preserved=True, parent_review_preserved=True)
        _save_receipt(session, receipt)
        print('Mixed native readback:', result['status'], flush=True)
        if result.get('error'):
            print('Follow-up:', result['error'], flush=True)
        print('Diagnostic: REVIEW (fixed mixed-model mechanics; chemistry and full-run qualification remain separate)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Mixed native test stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None:
            try:
                print('REVIEW ZIP:', _report_failure(session, receipt, exc), flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
