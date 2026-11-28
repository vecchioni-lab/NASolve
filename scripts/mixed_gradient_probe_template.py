#!/usr/bin/env python3
"""Audit initial mixed-model native derivatives with unchanged NARestraints policy.

Fresh fixed-coordinate numerical evidence only; no geometry optimization,
chemical repair, refinement or production adoption.
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
REVIEW_SHA256 = '4ebc4cc10ce2115426c4ab8cf95d75375d8c018548bde53922749b28b120246b'
CONTEXT_PREFIX = 'inputs/review/mixed_context/'
PARENT_PREFIX = 'inputs/review/inputs/review/inputs/review/inputs/review/mixed_linked_recovery/'
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
    suffix = '_failure_review.zip' if receipt_only else '_mixed_gradient_review.zip'
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
        raise ValueError('Unbound C88 evidence reference')
    data = members.get(prefix+reference['path'])
    if not isinstance(data, bytes) or reference != {'anchor': anchor, 'path': reference['path'],
            'sha256': _sha(data), 'size': len(data)}:
        raise ValueError('C88 evidence reference bytes differ')
    return data


def _read_capsule(path):
    """Read the exact verified C88 return; captured programs remain data."""
    from nasolve.cif_review_transport import is_safe_review_member, _parse_json
    original = path.read_bytes()
    if _sha(original) != REVIEW_SHA256:
        raise ValueError('Require the exact verified C88 review ZIP')
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
    if not isinstance(manifest, dict) or set(manifest) != set(members)-{'manifest.json'}:
        raise ValueError('Review inventory differs')
    for name, ref in manifest.items():
        if (not isinstance(ref, dict) or type(ref.get('bytes')) is not int
                or ref != {'sha256': _sha(members[name]), 'bytes': len(members[name])}):
            raise ValueError('Review member checksum differs')
    receipt = _parse_json(members['probe_receipt.json'])
    envelope = receipt.get('saved_mixed_context', {})
    summary = _parse_json(_bound_member(members, envelope.get('artifact'), anchor='probe_directory'))
    report = _parse_json(_bound_member(members, summary.get('original_report'),
        anchor='parent_review', prefix='inputs/review/'))
    qualification = _parse_json(_bound_member(members, summary.get('qualification'),
        anchor='parent_review', prefix='inputs/review/'))
    if (receipt.get('schema_version') != 1 or receipt.get('kind') != 'mixed-context-probe'
            or receipt.get('delivery_prefix') != '88_Cedar' or receipt.get('analysis_completed') is not True
            or receipt.get('automatic_adoption') is not False or receipt.get('requires_cif_review') is not False
            or summary.get('schema_version') != 1 or summary.get('policy_id') != 'cif-saved-mixed-context-v1'
            or summary.get('context_policy_id') != 'cif-mixed-linked-context-v2'
            or summary.get('status') != 'MIXED_CONTEXT_MECHANICS_PASS'
            or type(summary.get('saved_native_calls')) is not int or summary['saved_native_calls'] != 2
            or type(summary.get('new_native_calls')) is not int or summary['new_native_calls'] != 0
            or summary.get('automatic_adoption') is not False or summary.get('requires_cif_review') is not False
            or summary.get('scientific_qualification') != 'NOT_ASSESSED'
            or summary.get('original_report', {}).get('path') != 'mixed_context/mixed_context.json'
            or summary.get('qualification', {}).get('path') != 'mixed_context/qualification.json'
            or envelope != {'artifact': envelope.get('artifact'), 'status': summary['status'],
                'saved_native_calls': 2, 'new_native_calls': 0}
            or envelope.get('artifact', {}).get('path') != 'saved_mixed_context.json'
            or report.get('policy_id') != summary['context_policy_id'] or report.get('status') != summary['status']
            or report.get('targets') != summary.get('targets')
            or qualification.get('status') != summary['status']
            or qualification.get('mechanics_checks_pass') is not True
            or summary.get('coordinate_decision', {}).get('status') != 'CONTINUE_WITH_NOTES'
            or summary.get('coordinate_decision', {}).get('native_usable') is not True):
        raise ValueError('Require the exact completed C88 context mechanics evidence')
    if path.read_bytes() != original:
        raise ValueError('Review archive changed while reading')
    return members


def _materialize_inputs(members, destination):
    """Create only the two explicit scientific views outside the result tree."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Gradient data destination already exists')
    views = [(CONTEXT_PREFIX, 'context', 'mixed_context.json'),
             (PARENT_PREFIX, 'linked_parent', 'mixed_linked_recovery.json')]
    for prefix, _, report in views:
        if prefix+report not in members:
            raise ValueError('Missing declared gradient scientific view')
        if any(not _safe(name) for name in members if name.startswith(prefix)):
            raise ValueError('Unsafe gradient scientific view member')
    for prefix, view, _ in views:
        for name, data in members.items():
            if name.startswith(prefix):
                _write(destination/view/name[len(prefix):], data)
    return destination/'context', destination/'linked_parent'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip', type=Path, required=True, help='Exact verified C88 ZIP; captured programs stay data')
    parser.add_argument('--phenix-root', type=Path, default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--inspect-only', action='store_true', help='Prepare fixed inputs without an SDK process')
    parser.add_argument('--timeout-seconds', type=int, default=600, help='Deadline 1–600 seconds for one initial-only audit')
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 600:
        parser.error('The native deadline must be from 1 to 600 seconds')
    session = None
    receipt = {'schema_version': 1, 'kind': 'mixed-gradient-probe',
        'delivery_prefix': BUNDLE['delivery_prefix'] if isinstance(BUNDLE, dict) else None,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'build': BUNDLE,
        'analysis_completed': False, 'requires_cif_review': False, 'automatic_adoption': False,
        'policy_authority': 'NARestraints', 'coot_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
        'captured_code_execution': 'NOT_RUN', 'generation_execution': 'NOT_RUN',
        'model_optimization_requested': False, 'refinement': 'NOT_RUN', 'mtz_used': False,
        'production_checkpoint': 'NOT_CREATED'}
    try:
        runtime_members = _runtime_members()
        for package in ['Bio', 'numpy', 'openpyxl']:
            __import__(package)
        parent = args.output_parent.expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-gradient-', dir=parent)).resolve()
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
            'scope': 'EXACT_C88_PARENT; INDEXED_OPAQUE_TRANSPORT; CAPTURED_CODE_NOT_EXECUTED'}
        phenix = None
        if not args.inspect_only:
            from nasolve.config import load_config
            from nasolve.phenix_runtime import discover_phenix
            environment = {k: v for k, v in os.environ.items() if k not in NATIVE_OVERRIDES}
            phenix = discover_phenix(load_config(), explicit=args.phenix_root, environ=environment)
            receipt['phenix'] = {'version': phenix.version, 'historical_root': str(phenix.root),
                'source': phenix.source, 'executables': {n: {'historical_path': str(p), 'sha256': _sha(p.read_bytes())}
                    for n, p in phenix.executables.items() if n == 'phenix.python'}}
        from nasolve.cif_mixed_gradient import audit_mixed_initial_gradients, read_mixed_initial_gradients
        print('Initial mixed-model gradient audit:', BUNDLE['delivery_prefix'], flush=True)
        print('Fixed coordinates, definitions and NARestraints targets; no optimization.', flush=True)
        with tempfile.TemporaryDirectory(prefix='nasolve-mixed-gradient-parent-') as temporary:
            context, linked_parent = _materialize_inputs(members, Path(temporary).resolve()/'data')
            result = audit_mixed_initial_gradients(context, linked_parent, phenix, session/'mixed_gradient',
                timeout_seconds=args.timeout_seconds)
            if read_mixed_initial_gradients(session/'mixed_gradient', context_directory=context,
                    linked_parent_directory=linked_parent) != result:
                raise ValueError('Portable mixed gradient report differs')
        data = (session/'mixed_gradient/mixed_initial_gradients.json').read_bytes()
        receipt['mixed_gradient'] = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_gradient'},
            'report_sha256': _sha(data), 'report_size': len(data), 'status': result['status'],
            'new_native_calls': result['new_native_calls']}
        if not staged_review_members_match(members, session/'inputs/review'):
            raise ValueError('Preserved parent review differs')
        for name, data in runtime_members.items():
            if (runtime/name).read_bytes() != data:
                raise ValueError('Bundled runtime changed')
        receipt.update(analysis_completed=True, frozen_runtime_preserved=True, parent_review_preserved=True)
        _save_receipt(session, receipt)
        print('Initial gradient qualification:', result['status'], '; new native calls:', result['new_native_calls'], flush=True)
        if result.get('error'):
            print('Follow-up:', result['error'], flush=True)
        print('Diagnostic: REVIEW (initial-only numerical evidence; optimization and full-run qualification remain separate)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Mixed gradient audit stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None:
            try:
                print('REVIEW ZIP:', _report_failure(session, receipt, exc), flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())


