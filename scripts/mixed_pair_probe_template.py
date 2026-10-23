#!/usr/bin/env python3
"""Construct the declared eight-pair fixture and compile its NARestraints policy.

This is an MTZ-free construction test. No Phaser result, native membership,
optimization, refinement or production checkpoint is manufactured.
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
    suffix = '_failure_review.zip' if receipt_only else '_mixed_pair_review.zip'
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


def _readyset_dispatcher(root):
    root = root.expanduser().resolve(strict=True)
    candidates = {p.resolve() for p in [root/'bin/phenix.ready_set', root/'build/bin/phenix.ready_set', root/'phenix.ready_set'] if p.is_file()}
    if len(candidates) != 1:
        raise ValueError('Require one ReadySet dispatcher under the explicit Phenix root')
    return next(iter(candidates))


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phenix-root', type=Path, default=Path.home()/'Applications/phenix-2.2.1-6174',
                        help='Installation used for read-only ordinary CCD source selection; ReadySet is not run')
    parser.add_argument('--coot', help='Explicit Coot executable if discovery needs an override')
    parser.add_argument('--output-parent', type=Path, default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--inspect-only', action='store_true', help='Freeze sources and the complete explicit fixture plan without Coot')
    parser.add_argument('--timeout-seconds', type=int, default=600, help='One Coot construction deadline, 1–600 seconds')
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 600:
        parser.error('--timeout-seconds must be from 1 to 600')
    session = None
    receipt = {'schema_version': 1, 'kind': 'mixed-eight-pair-construction-probe',
               'delivery_prefix': BUNDLE['delivery_prefix'] if isinstance(BUNDLE, dict) else None,
               'created_utc': datetime.now(timezone.utc).isoformat(), 'build': BUNDLE,
               'analysis_completed': False, 'requires_cif_review': False,
               'automatic_adoption': False, 'policy_authority': 'NARestraints',
               'phenix_execution': 'NOT_RUN', 'readyset_execution': 'NOT_RUN',
               'native_membership': 'NOT_ASSESSED', 'model_optimization': 'NOT_RUN',
               'refinement': 'NOT_RUN', 'mtz_used': False, 'production_checkpoint': 'NOT_CREATED'}
    try:
        members = _runtime_members()
        for package in ['Bio', 'numpy', 'openpyxl']:
            __import__(package)
        parent = args.output_parent.expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_mixed-pair-', dir=parent)).resolve()
        runtime = session/'runtime'
        _isolate(runtime, session, members)
        import nasolve, restraints
        for package in [nasolve, restraints]:
            if not Path(package.__file__).resolve().is_relative_to(runtime):
                raise ValueError('Probe imported an ambient runtime')
        dispatcher = _readyset_dispatcher(args.phenix_root)
        receipt['source_installation'] = {'historical_root': str(args.phenix_root.expanduser().resolve()),
            'role': 'SOURCE_SELECTION_ONLY; NO_PHENIX_VERSION_OR_READYSET_PROCESS', 'dispatcher_sha256': _sha(dispatcher.read_bytes())}
        environment = {k: v for k, v in os.environ.items() if k not in NATIVE_OVERRIDES}
        coot = None
        if not args.inspect_only:
            from nasolve.config import load_config
            from nasolve.coot_runtime import discover_coot
            coot = discover_coot(load_config(), explicit=args.coot, environ=environment)
            receipt['coot_runtime'] = {'historical_executable': str(coot.executable), 'version': coot.version,
                'source': coot.source, 'sha256': _sha(coot.executable.read_bytes()),
                'discovery': 'ORDINARY_VERSION_AND_EMBEDDED_PYTHON_PROBES; SEPARATE_FROM_ONE_CONSTRUCTION'}
        from nasolve.cif_mixed_pair_fixture import run_mixed_pair_fixture, read_mixed_pair_fixture
        print('Explicit eight-pair construction:', BUNDLE['delivery_prefix'], flush=True)
        print('Requested pairs: K:X, D:T, Z:P, B:S, PDU:A, 5PC:G, 5CM:Q, F:A', flush=True)
        print('Freezing declared frame topology and ordinary sources; one bounded Coot construction.'
              if coot else 'Inspect-only: freezing the declared plan and ordinary sources; no native process.', flush=True)
        report = run_mixed_pair_fixture(runtime/'MR_frames/5W6W/C_G.pdb',
            runtime/'src/nasolve/data/restraints/5W6W_secondary_structure.eff',
            runtime/'src/nasolve/data/restraints/5W6W_Std_padd.txt', dispatcher,
            session/'postmr_construction', coot_executable=coot.executable if coot else None,
            environment=environment, coot_version=coot.version if coot else None,
            inspect_only=args.inspect_only, timeout_seconds=args.timeout_seconds)
        if read_mixed_pair_fixture(session/'postmr_construction') != report:
            raise ValueError('Portable mixed-fixture report differs')
        receipt['mixed_pair_fixture'] = {'directory': {'anchor': 'probe_directory', 'path': 'postmr_construction'}, **report}
        receipt['model_optimization'] = report['model_optimization']
        atl = runtime/'controls/ATL.cif'
        if atl.is_file():
            from nasolve.postmr_restoration import source_graph_fragment
            _write(session/'independent_control/ATL.cif', atl.read_bytes())
            control = {'component': 'ATL', 'scope': 'INDEPENDENT_SOURCE_GRAPH_ONLY; NOT_A_NINTH_PAIR',
                       'coot_execution': 'NOT_RUN', 'sha256': _sha(atl.read_bytes())}
            try:
                control.update(graph=source_graph_fragment(atl, 'ATL'), status='GRAPH_RECORDED')
            except ValueError as exc:
                control.update(status='UNSUPPORTED_GRAPH_CONTEXT_RECORDED', note=str(exc))
            receipt['atl_control'] = control
        if coot and _sha(coot.executable.read_bytes()) != receipt['coot_runtime']['sha256']:
            raise ValueError('Coot executable changed during construction')
        for name, data in members.items():
            if (runtime/name).read_bytes() != data:
                raise ValueError('Bundled runtime or source frame changed')
        receipt.update(analysis_completed=report.get('analysis_completed') is True,
                       frozen_runtime_preserved=True)
        if report.get('error'):
            print('Construction follow-up:', report['error'], flush=True)
        _save_receipt(session, receipt)
        print('Mixed-pair fixture:', report['status'], flush=True)
        print('Diagnostic: REVIEW (construction and PDB selector evidence; native membership and full run remain open)', flush=True)
        print('REVIEW ZIP:', _review_zip(session), flush=True)
        return 2
    except Exception as exc:
        print('Mixed-pair test stopped:', str(exc), file=sys.stderr, flush=True)
        if session is not None:
            try:
                archive = _report_failure(session, receipt, exc)
                print('REVIEW ZIP:', archive, flush=True)
            except Exception as reporting_error:
                print('Failure reporting also stopped:', str(reporting_error), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
