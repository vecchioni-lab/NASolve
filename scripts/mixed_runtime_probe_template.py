#!/usr/bin/env python3
"""Activate the qualified mixed endpoint through the ordinary runtime reader.

No native discovery, generator, optimizer or production adoption. The exact
parent is preserved once; captured programs remain data and are never run.
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
REVIEW_SHA256 = '570ebe89210def4a420c155b60f7ddf998d152c133edc4d5ff955713f77a6e94'


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
    if set(members) != set(BUNDLE['runtime_files']):
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


def _review_zip(session, *, receipt_only=False):
    token = session.name.rsplit('-', 1)[-1]
    destination = session/(BUNDLE['delivery_prefix']+'_'+token+('_failure_review.zip' if receipt_only else '_mixed_runtime_review.zip'))
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, required=True, help='Exact verified returned C94 ZIP')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    args = parser.parse_args()
    session = None
    receipt = {'schema_version': 1, 'kind': 'mixed-runtime-probe',
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
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-runtime-', dir=parent)).resolve()
        runtime = session/'runtime'
        _isolate(runtime, session, runtime_members)
        import nasolve, restraints
        if any(not Path(package.__file__).resolve().is_relative_to(runtime) for package in [nasolve, restraints]):
            raise ValueError('Probe imported an ambient runtime')
        source = args.review_zip.expanduser().resolve(strict=True)
        if source.stat().st_size > 32*1024*1024 or _sha(source.read_bytes()) != REVIEW_SHA256:
            raise ValueError('Require the exact bounded returned C94 ZIP')
        print('Qualified mixed runtime handoff:', BUNDLE['delivery_prefix'], flush=True)
        print('Freezing the exact selected model, dictionaries and NARestraints policy for the ordinary bundle reader.', flush=True)
        from nasolve.cif_mixed_runtime_bundle import prepare_mixed_runtime_bundle
        from nasolve.cif_runtime_bundle import assess_runtime_bundle
        output = session/'runtime_bundle'
        manifest = prepare_mixed_runtime_bundle(source, output, source_sha256=REVIEW_SHA256)
        # Rename this owned output before the public reader consumes it. No old
        # destination remains; original user files and historical runs stay intact.
        relocated = session/'activated_bundle'
        output.rename(relocated)
        print('Reading the relocated bundle through ordinary CIF Doctor assessment.', flush=True)
        assessment = assess_runtime_bundle(relocated)
        _write(session/'ordinary_assessment.json', assessment)
        expected = manifest['resources']
        if (assessment['model']['sha256'] != expected['model']['sha256']
            or [r['sha256'] for r in assessment['inputs']] != [r['sha256'] for r in expected['dictionaries']+expected['phils']]
            or assessment['requires_cif_review'] is not False
            or assessment['solution_report']['selected_candidate'] != 'qualified_geometry_endpoint'):
            raise ValueError('Ordinary assessment did not consume the exact selected runtime inputs')
        if _sha(source.read_bytes()) != REVIEW_SHA256 or any((runtime/n).read_bytes() != d for n, d in runtime_members.items()):
            raise ValueError('Source capsule or isolated runtime changed')
        receipt.update(analysis_completed=True, frozen_runtime_preserved=True, parent_review_preserved=True,
            mixed_runtime={'status': 'MIXED_RUNTIME_HANDOFF_PASS',
                'manifest': {'anchor': 'probe_directory', 'path': 'activated_bundle/runtime_bundle.json',
                    'sha256': _sha((relocated/'runtime_bundle.json').read_bytes()), 'size': (relocated/'runtime_bundle.json').stat().st_size},
                'parent_archive_sha256': REVIEW_SHA256, 'parent_preservation': 'EXACT_OPAQUE_ZIP_ONCE_IN_BUNDLE',
                'model_sha256': expected['model']['sha256'], 'dictionary_count': len(expected['dictionaries']),
                'parameter_count': len(expected['phils']), 'atom_count': manifest['qualification']['atom_count'],
                'relocated_before_public_assessment': True, 'ordinary_assessment_status': assessment['status'],
                'coordinate_decision': manifest['decision'], 'new_native_calls': 0})
        _save_receipt(session, receipt)
        print('Mixed runtime handoff: MIXED_RUNTIME_HANDOFF_PASS ; new native calls: 0', flush=True)
        print('Ordinary resources:', len(expected['dictionaries']), 'dictionaries /', len(expected['phils']), 'parameter files', flush=True)
        print('Automatic coordinate decision:', manifest['decision']['status'], '; selected:', manifest['decision']['selected'], flush=True)
        print('Runtime bundle:', relocated/'runtime_bundle.json', flush=True)
        print('Diagnostic: REVIEW (ordinary bundle handoff; scientific and diffraction-run qualification remain separate)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Mixed runtime handoff stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None:
            receipt.update(analysis_completed=False, error_type=type(exc).__name__, error=str(exc))
            try:
                _save_receipt(session, receipt)
                try:
                    archive = _review_zip(session)
                except Exception as collection_error:
                    receipt['archive_collection_error'] = str(collection_error)
                    _save_receipt(session, receipt)
                    archive = _review_zip(session, receipt_only=True)
                print('REVIEW ZIP:', archive, flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())


