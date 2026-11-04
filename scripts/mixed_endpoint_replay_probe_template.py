#!/usr/bin/env python3
"""Replay the exact C93 endpoint with portable descriptive geometry checks.

No native discovery, generator, optimizer or production adoption. The exact
parent is preserved once; captured programs remain data and are never run.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
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
REVIEW_SHA256 = '78ced78169afd096b5fa835c82036cd8d27b841f98153cf84cac2092e762b10f'
SUPPORT_PATH = 'support/c93_endpoint_ferry.py'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe(name):
    return (isinstance(name, str) and bool(name) and not name.startswith('/')
        and '\\' not in name and ':' not in name and not any(ord(c) < 32 or ord(c) == 127 for c in name)
        and all(p not in {'', '.', '..'} for p in name.split('/')))


def _runtime_members():
    if not isinstance(BUNDLE, dict) or not isinstance(RUNTIME_BASE64, str):
        raise ValueError('Use the assembled probe, not its template')
    data = base64.b64decode(RUNTIME_BASE64, validate=True)
    if _sha(data) != BUNDLE['runtime_archive_sha256']:
        raise ValueError('Runtime archive checksum differs')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if (len(entries) > 512 or len(entries) != len({e.filename for e in entries})
            or sum(e.file_size for e in entries) > 32*1024*1024
            or any(not _safe(e.filename) or e.is_dir() or e.flag_bits & 1
                or stat.S_IFMT(e.external_attr >> 16) not in {0, stat.S_IFREG}
                or e.file_size > 8*1024*1024 for e in entries)):
            raise ValueError('Unsafe or oversized runtime archive')
        members = {e.filename: archive.read(e) for e in entries}
    if set(members) != set(BUNDLE['runtime_files']) or SUPPORT_PATH not in members:
        raise ValueError('Incomplete replay runtime')
    for name, value in members.items():
        ref = BUNDLE['runtime_files'][name]
        if (not isinstance(ref, dict) or type(ref.get('size')) is not int
            or ref != {'size': len(value), 'sha256': _sha(value)}):
            raise ValueError('Runtime member checksum differs')
    return members


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    with path.open('xb') as handle:
        handle.write(data)


def _isolate(runtime, session, members):
    if any(n == p or n.startswith(p+'.') for n in sys.modules for p in ['nasolve', 'restraints']):
        raise ValueError('Start the probe in a fresh Python process')
    _write(session/'runtime-config.json', {'schema_version': 1})
    for name, data in members.items():
        _write(runtime/name, data)
    sys.path[:0] = [str(runtime/'src'), str(runtime)]
    os.environ['PYTHONPATH'] = os.pathsep.join(sys.path[:2])
    os.environ['NASOLVE_CONFIG_FILE'] = str(session/'runtime-config.json')
    os.environ['NASOLVE_NATIVE_ENV_ISOLATION'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    sys.dont_write_bytecode = True


def _support(runtime):
    # This is current, checksummed build support; never code from a review ZIP.
    spec = importlib.util.spec_from_file_location('_nasolve_c93_ferry_support', runtime/SUPPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_capsule(path, support):
    from nasolve.cif_review_transport import _parse_json
    original = path.read_bytes()
    members = support._archive_members(original, REVIEW_SHA256)
    receipt = _parse_json(members['probe_receipt.json'])
    data = members['mixed_endpoint_window/mixed_endpoint_window_qualification.json']
    report = _parse_json(data)
    expected = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_endpoint_window'},
        'report_sha256': _sha(data), 'report_size': len(data), 'status': 'MIXED_ENDPOINT_QUALIFIED', 'new_native_calls': 2}
    if (type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1
        or receipt.get('kind') != 'mixed-endpoint-window-probe' or receipt.get('delivery_prefix') != '93_Cedar'
        or receipt.get('analysis_completed') is not True or receipt.get('automatic_adoption') is not False
        or receipt.get('requires_cif_review') is not False or receipt.get('mixed_endpoint_window') != expected
        or type(receipt.get('mixed_endpoint_window', {}).get('new_native_calls')) is not int
        or receipt.get('parent_review_preserved') is not True or receipt.get('frozen_runtime_preserved') is not True
        or receipt.get('model_optimization_requested') is not False or receipt.get('captured_code_execution') != 'NOT_RUN'
        or type(report.get('schema_version')) is not int or report['schema_version'] != 1
        or report.get('policy_id') != 'cif-mixed-saved-endpoint-resolution-window-v1'
        or report.get('status') != 'MIXED_ENDPOINT_QUALIFIED'
        or type(report.get('new_native_calls')) is not int or report['new_native_calls'] != 2
        or report.get('parent_archive_sha256') != support.SCIENCE_PARENT_SHA256
        or report.get('automatic_adoption') is not False or report.get('requires_cif_review') is not False
        or report.get('scientific_qualification') != 'NOT_ASSESSED'):
        raise ValueError('Require the exact completed C93 endpoint evidence')
    parent = support._bound_member(members, receipt.get('parent_review', {}).get('artifact'), anchor='probe_directory')
    if receipt.get('parent_review', {}).get('preserved') is not True or _sha(parent) != support.REVIEW_SHA256:
        raise ValueError('C93/C92 parent binding differs')
    with tempfile.TemporaryDirectory(prefix='endpoint-replay-envelope-') as temporary:
        nested = Path(temporary).resolve()/'parent.zip'
        _write(nested, parent)
        prior = support._read_capsule(nested)
    if (type(receipt['parent_review'].get('payload_count')) is not int
        or receipt['parent_review']['payload_count'] != len(prior)-1 or path.read_bytes() != original):
        raise ValueError('C93 parent inventory or source changed')
    return members, prior


def _stage_window(members, destination):
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Saved endpoint destination already exists')
    selected = {n[len('mixed_endpoint_window/'):]: d for n, d in members.items() if n.startswith('mixed_endpoint_window/')}
    if 'mixed_endpoint_window_qualification.json' not in selected or not all(_safe(n) for n in selected):
        raise ValueError('Missing or unsafe saved endpoint view')
    for name, data in selected.items():
        _write(destination/name, data)


def _review_zip(session, *, receipt_only=False):
    token = session.name.rsplit('-', 1)[-1]
    destination = session/(BUNDLE['delivery_prefix']+'_'+token+('_failure_review.zip' if receipt_only else '_mixed_endpoint_replay_review.zip'))
    if receipt_only:
        files = {'probe_receipt.json': (session/'probe_receipt.json').read_bytes()}
    else:
        from nasolve.cif_review_transport import review_archive_files
        files = review_archive_files(session, destination)
    manifest = json.dumps({n: {'sha256': _sha(d), 'bytes': len(d)} for n, d in files.items()}, indent=2).encode()
    if (len(files)+1 > 1024 or sum(map(len, files.values()))+len(manifest) > 128*1024*1024
        or any(len(d) > 32*1024*1024 for d in [*files.values(), manifest])):
        raise ValueError('Replay output exceeds the unchanged archive bounds')
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', manifest)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, required=True, help='Exact returned C93 ZIP')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    args = parser.parse_args()
    session, support = None, None
    receipt = {'schema_version': 1, 'kind': 'mixed-endpoint-replay-probe',
        'delivery_prefix': BUNDLE['delivery_prefix'] if isinstance(BUNDLE, dict) else None,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'build': BUNDLE,
        'analysis_completed': False, 'requires_cif_review': False, 'automatic_adoption': False,
        'policy_authority': 'NARestraints', 'new_native_calls': 0, 'captured_code_execution': 'NOT_RUN',
        'model_optimization_requested': False, 'dictionary_generation': 'NOT_RUN', 'cache_writes': 'NOT_RUN',
        'coot_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN', 'refinement': 'NOT_RUN',
        'production_checkpoint': 'NOT_CREATED', 'mtz_used': False}
    try:
        runtime_members = _runtime_members()
        for package in ['Bio', 'numpy', 'openpyxl']:
            __import__(package)
        parent = args.output_parent.expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-endpoint-replay-', dir=parent)).resolve()
        runtime = session/'runtime'
        _isolate(runtime, session, runtime_members)
        import nasolve, restraints
        if any(not Path(package.__file__).resolve().is_relative_to(runtime) for package in [nasolve, restraints]):
            raise ValueError('Probe imported an ambient runtime')
        support = _support(runtime)
        source = args.review_zip.expanduser().resolve(strict=True)
        members, prior = _read_capsule(source, support)
        original = source.read_bytes()
        if _sha(original) != REVIEW_SHA256:
            raise ValueError('C93 archive changed before preservation')
        _write(session/'inputs/parent_review.zip', original)
        receipt['parent_review'] = {'artifact': {'anchor': 'probe_directory', 'path': 'inputs/parent_review.zip',
            'sha256': REVIEW_SHA256, 'size': len(original)}, 'historical_path': str(args.review_zip),
            'payload_count': len(members)-1, 'preserved': True, 'scope': 'EXACT_C93_ZIP_OPAQUE; CAPTURED_CODE_NOT_EXECUTED'}
        print('Portable saved-endpoint replay:', BUNDLE['delivery_prefix'], flush=True)
        print('Recomputing saved evidence; exact chemistry and native proxies, no new Phenix or optimization.', flush=True)
        from nasolve.cif_mixed_endpoint_replay import replay_saved_endpoint_window, REPORT
        with tempfile.TemporaryDirectory(prefix='nasolve-endpoint-replay-data-') as temporary:
            data_root = Path(temporary).resolve()
            views = support._materialize_inputs(prior, data_root/'parents')
            window = data_root/'window'
            _stage_window(members, window)
            before = {p.relative_to(data_root).as_posix(): _sha(p.read_bytes()) for p in data_root.rglob('*') if p.is_file()}
            result = replay_saved_endpoint_window(window, torsion_directory=views[1], geometry_directory=views[2],
                gradient_directory=views[3], context_directory=views[4], linked_parent_directory=views[5],
                parent_archive_sha256=support.SCIENCE_PARENT_SHA256)
            after = {p.relative_to(data_root).as_posix(): _sha(p.read_bytes()) for p in data_root.rglob('*') if p.is_file()}
            if before != after:
                raise ValueError('Saved scientific evidence changed during replay')
            receipt['staged_scientific_files_preserved'] = len(before)
        _write(session/'saved_replay'/REPORT, result)
        data = (session/'saved_replay'/REPORT).read_bytes()
        receipt['saved_endpoint_replay'] = {'directory': {'anchor': 'probe_directory', 'path': 'saved_replay'},
            'report_sha256': _sha(data), 'report_size': len(data), 'status': result['status'], 'new_native_calls': 0}
        if source.read_bytes() != original or (session/'inputs/parent_review.zip').read_bytes() != original:
            raise ValueError('Original or preserved C93 ZIP changed')
        if any((runtime/n).read_bytes() != d for n, d in runtime_members.items()):
            raise ValueError('Bundled runtime changed')
        receipt.update(analysis_completed=True, frozen_runtime_preserved=True, parent_review_preserved=True)
        support._save_receipt(session, receipt)
        print('Saved endpoint replay:', result['status'], '; new native calls:', result['new_native_calls'], flush=True)
        decision = result['coordinate_decision']
        print('Automatic coordinate decision:', decision['status'], '; selected:', decision['selected'], flush=True)
        print('Diagnostic: REVIEW (saved evidence reproduced; scientific and ordinary full-run qualification remain separate)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Saved endpoint replay stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None and support is not None:
            receipt.update(analysis_completed=False, error_type=type(exc).__name__, error=str(exc))
            try:
                support._save_receipt(session, receipt)
                try:
                    archive = _review_zip(session)
                except Exception as collection_error:
                    receipt['archive_collection_error'] = str(collection_error)
                    support._save_receipt(session, receipt)
                    archive = _review_zip(session, receipt_only=True)
                print('REVIEW ZIP:', archive, flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
