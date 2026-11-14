#!/usr/bin/env python3
"""Explicit reviewed 5CM preparation and installed terminal-resource evidence."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import zipfile

BUNDLE = None  # @bundle-metadata@
RUNTIME_BASE64 = None  # @runtime-base64@
ARCHIVE_SHA256 = 'db9f39ff423f0331ab26e4e3b7e65b176a767c5d64b0c698ce043f552f9dcb2a'
SOURCE_MEMBER = 'baseline/inputs/runtime_sources/3_5CM.cif'
NATIVE_OVERRIDES = {'PYTHONPATH','PYTHONHOME','PHENIX','PHENIX_ROOT','PHENIX_VERSION','LIBTBX_BUILD','LIBTBX_DIST','BOOST_ADAPTBX_FPE_DEFAULT'}


def _sha(data): return hashlib.sha256(data).hexdigest()


def _json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle:
        json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def _safe_name(name):
    return isinstance(name,str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(p not in {'','.','..'} for p in name.split('/'))


def _runtime_members():
    data=base64.b64decode(RUNTIME_BASE64,validate=True)
    if _sha(data)!=BUNDLE['runtime_archive_sha256']:raise ValueError('Embedded runtime checksum mismatch')
    members={}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            if not _safe_name(entry.filename) or entry.filename in members or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Unsafe or duplicate runtime member')
            members[entry.filename]=archive.read(entry)
    if set(members)!=set(BUNDLE['runtime_files']):raise ValueError('Runtime inventory mismatch')
    for name,payload in members.items():
        row=BUNDLE['runtime_files'][name]
        if _sha(payload)!=row['sha256'] or len(payload)!=row['size']:raise ValueError('Runtime file integrity mismatch')
    return members


def _review_source(path,session):
    original=path.read_bytes()
    if _sha(original)!=ARCHIVE_SHA256:raise ValueError('Require the exact hash-bound Cedar 09 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        names=archive.namelist();manifest=json.loads(archive.read('manifest.json'))
        if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'manifest.json'} or len(manifest)!=207:raise ValueError('Unexpected Cedar 09 payload inventory')
        for entry in archive.infolist():
            name=entry.filename
            if not _safe_name(name) or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Unsafe review path')
            payload=archive.read(entry)
            if name!='manifest.json' and (_sha(payload)!=manifest[name]['sha256'] or len(payload)!=manifest[name]['bytes']):raise ValueError('Review payload integrity mismatch')
        prior=json.loads(archive.read('probe_receipt.json'))
        if prior.get('kind')!='cif-linked-native-probe' or prior.get('delivery_prefix')!='09_Cedar' or prior.get('original_archive_preserved') is not True:raise ValueError('Require the preserved Cedar 09 diagnostic receipt')
        payload=archive.read(SOURCE_MEMBER)
    source=session/'inputs/5CM_source.cif';source.parent.mkdir()
    with source.open('xb') as handle:handle.write(payload)
    return source,original,{'sha256':ARCHIVE_SHA256,'size':len(original),'verified_payloads':207,
        'source_member':SOURCE_MEMBER,'source_sha256':_sha(payload),'prior_status':prior.get('status'),
        'prior_build':{key:prior['build'].get(key) for key in ['nasolve_source','narestraints_source']}}


def _review_zip(session):
    token=session.name.rsplit('-',1)[-1]
    destination=session/(BUNDLE['delivery_prefix']+'_'+token+'_cif_terminal_review.zip')
    files={}
    for path in sorted(session.rglob('*')):
        if path==destination or path.is_relative_to(session/'runtime'):continue
        if path.is_symlink():raise ValueError('Unexpected output symlink')
        if path.is_file() and path.suffix not in {'.pyc','.pkl','.pickle'}:files[path.relative_to(session).as_posix()]=path.read_bytes()
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps({name:{'sha256':_sha(data),'bytes':len(data)} for name,data in files.items()},indent=2))
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/09_Cedar_cif-linked-probe-nn9cyghr/09_Cedar_nn9cyghr_cif_linked_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',default=str(Path.home()/'Applications/phenix-2.2.1-6174'))
    parser.add_argument('--timeout-seconds',type=float,default=120)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None
    receipt={'schema_version':1,'kind':'cif-terminal-source-review','build':BUNDLE,
        'delivery_prefix':BUNDLE['delivery_prefix'],'status':'FAILED','automatic_adoption':False,
        'model_editing':'NOT_RUN','model_optimization':'NOT_RUN','readyset_retry':'NOT_RUN',
        'refinement':'NOT_RUN','scientific_approval':'NOT_RUN','native_terminal_resources':'NOT_RUN',
        'terminal_recipe_implementation':'NOT_RUN','native_5cm_bundle_validation':'NOT_RUN'}
    try:
        members=_runtime_members();path=args.review_zip.expanduser().resolve(strict=True)
        parent=args.output_parent.expanduser().resolve()
        if parent==path.parent or parent.is_relative_to(path.parent):raise ValueError('Output must be outside the original diagnostic directory')
        parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-terminal-probe-',dir=parent))
        for name,data in members.items():
            target=session/'runtime'/PurePosixPath(name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_doctor_repair import prepare_dictionary
        from nasolve.cif_terminal_resources import inspect_terminal_resources
        from nasolve.phenix_runtime import installation_from_candidate
        print('CIF terminal-source review:',BUNDLE['delivery_prefix'],flush=True)
        source,original,receipt['prior_archive']=_review_source(path,session)
        output=session/'5cm_preparation';output.mkdir()
        print('Preparing the explicit reviewed 5CM derivative.',flush=True)
        prepared=prepare_dictionary(source,output/'5CM_candidate.cif',recipe='5cm-reviewed-torsion-v1')
        _json(output/'preparation_receipt.json',prepared);receipt['five_cm_preparation']=prepared
        if args.inspect_only:receipt['status']='PREPARED_REVIEW_NATIVE_NOT_RUN'
        else:
            environment={key:value for key,value in os.environ.items() if key not in NATIVE_OVERRIDES}
            phenix=installation_from_candidate(args.phenix_root,base_environment=environment)
            executable=phenix.executables.get('phenix.python')
            if not executable:raise ValueError('Selected installation requires phenix.python')
            print('Recording installed 5*END and canonical DG control.',flush=True)
            native=inspect_terminal_resources(session/'terminal_resources',executable,
                environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=args.timeout_seconds)
            receipt['native_terminal_resources']=native
            receipt['status']='PREPARATION_AND_RESOURCES_REVIEW' if native['status']=='REVIEW' else 'NATIVE_RESOURCES_REVIEW'
            if native['status']!='REVIEW':print('Native terminal resources require review:',native.get('error') or (native.get('native_resources') or {}).get('error') or native['status'],flush=True)
        if path.read_bytes()!=original:raise ValueError('Original review ZIP changed')
        receipt['original_archive_preserved']=True
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic:',receipt['status'],flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Separate dictionary candidate and resource evidence only; no model changes, optimization, refinement or adoption.',flush=True)
        return 0 if receipt['status'] in {'PREPARATION_AND_RESOURCES_REVIEW','PREPARED_REVIEW_NATIVE_NOT_RUN'} else 2
    except (Exception,KeyboardInterrupt) as exc:
        receipt.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
        if session is not None:
            target=session/'probe_receipt.json'
            if not target.exists():_json(target,receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print(receipt['error'],file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
