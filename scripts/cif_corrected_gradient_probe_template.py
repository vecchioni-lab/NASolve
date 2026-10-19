#!/usr/bin/env python3
"""Validate complete native plane-gradient accumulation with unchanged energies."""
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
REVIEW_SHA256 = 'a2f91570c103ce11900d48d89395af8de2d335e8610e85996e5bd73bd410e6fe'
CAPTURE_PREFIX = 'native_parallelity/cif-parallelity-audit-fzeylrjo'
GEOMETRY_BUNDLE_PREFIX = 'inputs/review/inputs/review'
GEOMETRY_PREFIX = 'geometry_trial/cif-fixed-geometry-t2c9xuw6'
READBACK_PREFIX = 'native_roundtrip/cif-native-wd459r67'
NATIVE_OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'PHENIX', 'PHENIX_ROOT', 'PHENIX_VERSION',
                    'LIBTBX_BUILD', 'LIBTBX_DIST', 'BOOST_ADAPTBX_FPE_DEFAULT'}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe(name):
    return isinstance(name, str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(
        p not in {'', '.', '..'} for p in name.split('/'))


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def _runtime_members():
    data = base64.b64decode(RUNTIME_BASE64, validate=True)
    if _sha(data) != BUNDLE['runtime_archive_sha256']:
        raise ValueError('Embedded runtime checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries = z.infolist()
        if len(entries) != len({e.filename for e in entries}) or any(
                not _safe(e.filename) or stat.S_ISLNK(e.external_attr >> 16) for e in entries):
            raise ValueError('Unsafe or duplicate runtime member')
        members = {e.filename: z.read(e) for e in entries}
    if set(members) != set(BUNDLE['runtime_files']):
        raise ValueError('Runtime inventory mismatch')
    for name, data in members.items():
        expected = BUNDLE['runtime_files'][name]
        if len(data) != expected['size'] or _sha(data) != expected['sha256']:
            raise ValueError('Runtime file integrity mismatch')
    return members


def _materialize(members, target):
    for name, data in members.items():
        if not _safe(name):
            raise ValueError('Unsafe materialization path')
        path = target / PurePosixPath(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(data)


def _review_zip(session):
    token = session.name.rsplit('-', 1)[-1]
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_corrected_gradient_review.zip')
    files = {}
    for path in sorted(session.rglob('*')):
        if path == destination or path.is_relative_to(session/'runtime'):
            continue
        if path.is_symlink():
            raise ValueError('Unexpected output symlink')
        if path.is_file() and path.suffix not in {'.pyc', '.pkl', '.pickle'}:
            files[path.relative_to(session).as_posix()] = path.read_bytes()
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', json.dumps({n: {'sha256': _sha(d), 'bytes': len(d)} for n,d in files.items()}, indent=2))
    return destination


def _fingerprints(phenix,capture):
    if not phenix.root or phenix.version!=capture['phenix_version']:
        raise ValueError('Selected Phenix differs from captured native version')
    executable=phenix.executables.get('phenix.python')
    if not executable or _sha(Path(executable).read_bytes())!=capture['executable_sha256']:
        raise ValueError('Phenix dispatcher changed since the captured bundle')
    historical=Path(capture['executable_provenance']).parent.parent;rows=[]
    for row in capture['native_validation']['installed_api_sources']:
        relative=Path(row['historical_path']).relative_to(historical).as_posix()
        if not _safe(relative):raise ValueError('Unsupported native source anchor')
        path=Path(phenix.root)/relative
        if not path.resolve().is_relative_to(Path(phenix.root).resolve()) or _sha(path.read_bytes())!=row['sha256']:
            raise ValueError('Installed native API source changed')
        rows.append({'anchor':'phenix_installation','path':relative,'sha256':row['sha256']})
    return rows


def _verify_manifest(members, count):
    manifest=json.loads(members['manifest.json'])
    if set(members)!=set(manifest)|{'manifest.json'} or len(manifest)!=count:
        raise ValueError('Unexpected preserved payload inventory')
    for name,row in manifest.items():
        if not _safe(name) or len(members[name])!=row['bytes'] or _sha(members[name])!=row['sha256']:
            raise ValueError('Preserved payload integrity mismatch')


def _native_artifacts(members, receipt, prefix, *, bytecode_excluded=False):
    from collections import Counter
    if (receipt.get('status')!='REVIEW' or receipt.get('execution',{}).get('status')!='COMPLETED'
            or receipt['execution'].get('returncode')!=0 or not receipt.get('source_preserved') or not receipt.get('frozen_inputs_preserved')):
        raise ValueError('Incomplete captured native execution')
    if Counter(row['role'] for row in receipt['inputs'])!={'model':1,'dictionary':19,'phil':13}:
        raise ValueError('Unexpected frozen native input roles')
    for row in receipt['inputs']+receipt['outputs']:
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')):
            raise ValueError('Unsupported native artifact anchor')
        name=prefix+'/'+row['path']
        if bytecode_excluded and name not in members and row in receipt['outputs'] and Path(row['path']).suffix=='.pyc':
            continue
        if name not in members or len(members[name])!=row['size'] or _sha(members[name])!=row['sha256']:
            raise ValueError('Captured native artifact mismatch')


def _read_capsule(path,expected_sha=None):
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or REVIEW_SHA256):raise ValueError('Require the exact verified Cedar 24 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries=archive.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):raise ValueError('Unsafe or duplicate review member')
        members={entry.filename:archive.read(entry) for entry in entries}
    _verify_manifest(members,732);prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-native-parallelity-audit-probe' or prior.get('delivery_prefix')!='24_Cedar'
            or prior.get('status')!='REVIEW' or prior.get('analysis_completed') is not True
            or prior.get('original_archive_preserved') is not True or prior.get('frozen_inputs_preserved') is not True
            or prior.get('native_execution')!='COMPLETED' or prior.get('model_optimization')!='NOT_RUN'
            or prior.get('automatic_adoption') is not False or prior.get('policy_authority')!='NARestraints'
            or prior.get('prerequisite_mechanics_replayed') is not True or prior.get('prior_convergence')!='NOT_CONVERGED_ERROR'):
        raise ValueError('Require preserved completed Cedar 24 evidence')
    audit=prior['native_parallelity_audit'];result=audit['result'];_native_artifacts(members,audit,CAPTURE_PREFIX)
    if audit!=json.loads(members[CAPTURE_PREFIX+'/parallelity_receipt.json']) or result!=json.loads(members[CAPTURE_PREFIX+'/parallelity_result.json']):raise ValueError('Inconsistent captured accumulation receipt/result')
    if (result.get('policy_id')!='cif-native-parallelity-accumulation-audit-v1' or result.get('status')!='REVIEW'
            or result.get('analysis_completed') is not True or not result.get('captured_inventory_matches')
            or result.get('model_optimization')!='NOT_RUN' or result.get('automatic_adoption') is not False
            or set(result.get('cases',{}))!={'full_precision','pdb_rounded'} or not 0<result.get('evaluation_pairs',0)<=7000
            or not result.get('constraint_signature_before') or result['constraint_signature_before']!=result.get('constraint_signature_after')):
        raise ValueError('Incomplete installed accumulation prerequisite')
    for case in [*result['cases'].values(),{'summary':result['toy_summary']}]:
        if not case['summary']['single_derivatives_consistent'] or not case['summary']['baseline_repeats_consistent']:raise ValueError('Individual-restraint derivatives are not qualified by prior audit')
    frozen={name.removeprefix('inputs/review/'):data for name,data in members.items() if name.startswith('inputs/review/')}
    _verify_manifest(frozen,670)
    geometry_members={name.removeprefix(GEOMETRY_BUNDLE_PREFIX+'/'):data for name,data in members.items() if name.startswith(GEOMETRY_BUNDLE_PREFIX+'/')}
    _verify_manifest(geometry_members,609);geometry=json.loads(geometry_members['probe_receipt.json'])
    if geometry.get('kind')!='cif-na-policy-geometry-probe' or geometry.get('convergence')!='NOT_CONVERGED_ERROR' or not geometry.get('analysis_completed') or geometry.get('automatic_adoption') is not False:raise ValueError('Invalid preserved geometry prerequisite')
    trial=geometry['geometry_trial'];readback=geometry['native_roundtrip']
    for receipt,prefix in [(trial,GEOMETRY_PREFIX),(readback,READBACK_PREFIX)]:_native_artifacts(geometry_members,receipt,prefix)
    if (trial!=json.loads(geometry_members[GEOMETRY_PREFIX+'/geometry_receipt.json'])
            or trial['result']!=json.loads(geometry_members[GEOMETRY_PREFIX+'/geometry_result.json'])
            or readback!=json.loads(geometry_members[READBACK_PREFIX+'/native_receipt.json'])):raise ValueError('Inconsistent preserved geometry evidence')
    mechanics=geometry['native_mechanics']
    if (mechanics!=json.loads(geometry_members['native_mechanics.json']) or not mechanics.get('mechanics_checks_pass')
            or len(mechanics['checks'])!=17 or len({r['check'] for r in mechanics['checks']})!=17 or any(r['status']!='PASS' for r in mechanics['checks'])):raise ValueError('Unresolved native mechanics prerequisite')
    expected=json.loads(members[CAPTURE_PREFIX+'/expected_inventory.json'])
    if expected!=json.loads(geometry_members[GEOMETRY_PREFIX+'/expected_inventory.json']):raise ValueError('Captured managers differ')
    actual=json.loads(members[CAPTURE_PREFIX+'/native_validation.json'])
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):raise ValueError('Captured native inventory differs')
    signature=lambda receipt:[(r['role'],r['sha256'],r['size']) for r in receipt['inputs']]
    if signature(audit)!=signature(trial):raise ValueError('Frozen native inputs differ')
    coordinates={'initial':expected['geometry']['sites_cart_exact'],'full_precision':trial['result']['final_sites_cart'],
                 'pdb_rounded':[[float('%.3f'%v) for v in p] for p in trial['result']['final_sites_cart']]}
    capture_spec=json.loads(members[CAPTURE_PREFIX+'/parallelity_spec.json'])
    if (capture_spec['coordinate_cases']!={k:coordinates[k] for k in ['full_precision','pdb_rounded']}
            or result['constraint_signature_before']!=trial['result']['constraint_signature_before']
            or result['installed_numeric_sources']!=trial['result']['installed_optimizer_sources']):raise ValueError('Coordinate or source prerequisites differ')
    if {r['path'] for r in result['installed_parallelity_sources']}!={'parallelity.h','parallelity_bpl.cpp'}:raise ValueError('Incomplete installed source inventory')
    for row in result['installed_parallelity_sources']:
        name=CAPTURE_PREFIX+'/installed_source/'+row['path']
        if row.get('status')!='RECORDED' or len(members[name])!=row['bytes'] or _sha(members[name])!=row['sha256']:raise ValueError('Unpinned installed plane source')
    for label in ['full_precision','pdb_rounded']:
        capture=result['full_batch_comparisons'][label]
        if not capture['manager_matches_batch'] or not capture['captured_snapshot_match'] or not capture['energy_agreement'] or len(capture['manual_gradient'])!=3*expected['atom_count']:raise ValueError('Incomplete native batch comparison')
    for field in ['initial','final','serialized']:
        if any(key not in trial['result'][field] for key in ['target','gradient_norm']):raise ValueError('Missing native raw baseline')
    return members,prior,geometry,coordinates,original


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/24_Cedar_cif-parallelity-audit-5a5xbuih/24_Cedar_5a5xbuih_cif_parallelity_audit_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--timeout-seconds',type=int,default=1200)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;review=None;original=None;members=None
    receipt={'schema_version':1,'kind':'cif-native-corrected-gradient-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
             'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'NOT_RUN','model_optimization':'NOT_RUN',
             'dictionary_generation':'NOT_RUN','policy_recompilation':'NOT_RUN','refinement':'NOT_RUN','diffraction_data':'NOT_READ',
             'scientific_approval':'NOT_RUN','automatic_adoption':False,'policy_authority':'NARestraints','installed_phenix_edits':'NOT_RUN'}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid native timeout')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,prior,geometry,coordinates,original=_read_capsule(review);parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-corrected-gradient-',dir=parent))
        _materialize(runtime,session/'runtime');frozen=session/'inputs/review';_materialize(members,frozen)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_fixed_geometry import qualify_fixed_policy_geometry,classify_stopping
        from nasolve.cif_gradient_audit import review_distance_groups
        from nasolve.cif_parallelity_correction import run_native_correction_audit,CORRECTION_POLICY_ID
        expected=json.loads(members[CAPTURE_PREFIX+'/expected_inventory.json']);audit=prior['native_parallelity_audit'];result=audit['result']
        candidate=frozen/GEOMETRY_BUNDLE_PREFIX/'candidate/na_policy_geometry_model.pdb'
        mechanics=qualify_fixed_policy_geometry(expected,geometry['native_roundtrip']['native_validation'],candidate,geometry['serialization'])
        if mechanics!=geometry['native_mechanics'] or not mechanics['mechanics_checks_pass']:raise ValueError('Native mechanics prerequisite does not replay')
        if classify_stopping(geometry['geometry_trial']['result']['stopping'])!='NOT_CONVERGED_ERROR':raise ValueError('Stopping evidence does not replay')
        groups=review_distance_groups(expected,coordinates['full_precision']);selected=groups['selected_indices']
        root=frozen/CAPTURE_PREFIX;paths=lambda role:[root/PurePosixPath(row['path']) for row in audit['inputs'] if row['role']==role]
        snapshots=geometry['geometry_trial']['result'];references={name:{k:snapshots[field][k] for k in ['target','gradient_norm']} for name,field in [('initial','initial'),('full_precision','final'),('pdb_rounded','serialized')]}
        receipt.update(prior_archive={'sha256':_sha(original),'bytes':len(original),'verified_payloads':732},
            prior_convergence='NOT_CONVERGED_ERROR',prerequisite_mechanics_replayed=True,correction_policy_id=CORRECTION_POLICY_ID,
            selected_indices=selected,coordinate_cases=list(coordinates),parallelity_proxy_count=len(expected['geometry']['proxy_details']['parallelity']),
            limitations=['Opt-in NASolve evaluation correction only; ordinary PostMR/refinement defaults remain unchanged.',
                         'Native energies, dictionaries, parameters, proxy membership and NARestraints policy remain fixed.',
                         'Fresh sampled derivative agreement cannot establish full gradient correctness, optimizer convergence or chemical qualification.',
                         'No optimization, new candidate, installed-Phenix edit, diffraction/refinement or adoption.'])
        print('Corrected fixed native gradient audit:',BUNDLE['delivery_prefix'],flush=True)
        print('Complete plane accumulation; checking initial, full-precision and PDB-rounded coordinates.',flush=True)
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            capture={**audit,'native_validation':expected};native_sources=_fingerprints(phenix,capture)
            numeric_capture={**audit,'native_validation':{'installed_api_sources':result['installed_numeric_sources']}}
            adapter_capture={**audit,'native_validation':{'installed_api_sources':result['installed_adapter_sources']}}
            numeric=_fingerprints(phenix,numeric_capture);adapters=_fingerprints(phenix,adapter_capture)
            receipt.update(installed_api_sources=native_sources,installed_numeric_sources=numeric,installed_adapter_sources=adapters,native_execution='ATTEMPTED')
            native=run_native_correction_audit(paths('model')[0],paths('dictionary'),paths('phil'),expected,coordinates,references,result['full_batch_comparisons'],selected,
                result['installed_numeric_sources'],result['installed_adapter_sources'],result['installed_parallelity_sources'],result['constraint_signature_before'],
                session/'native_correction',phenix.executables['phenix.python'],environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=args.timeout_seconds)
            receipt['native_correction_audit']=native;receipt['native_execution']=native['execution']['status']
            if native['status']!='REVIEW':raise ValueError('Corrected native audit did not complete; inspect retained worker evidence')
            if _fingerprints(phenix,capture)!=native_sources or _fingerprints(phenix,numeric_capture)!=numeric or _fingerprints(phenix,adapter_capture)!=adapters:raise ValueError('Installed sources changed')
            receipt['correction_qualification']=native['result']['correction_qualification']
            receipt['case_summary']={label:{'sampled_gradients_consistent':case['sampled_gradients_consistent'],
                'families_requiring_review':[name for name,value in case['families'].items() if not value['sampled_directions_consistent']],
                'baseline_repeats_consistent':case['baseline_repeats_consistent'],'target_additivity':case['target_additivity']['consistent'],
                'gradient_additivity':case['gradient_additivity']['consistent']} for label,case in native['result']['cases'].items()}
            for label,summary in receipt['case_summary'].items():print(label+':',summary,flush=True)
            print('Correction qualification:',receipt['correction_qualification'],flush=True)
            print('Native energy evaluations:',native['result']['evaluation_calls'],'/ 5500; energy change:',native['result']['correction_statistics']['max_energy_change'],flush=True)
        if review.read_bytes()!=original or any((frozen/PurePosixPath(name)).read_bytes()!=data for name,data in members.items()):raise ValueError('Original or frozen evidence changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (explicit accumulation correction; no optimization or adoption)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(review and original is not None and review.read_bytes()==original)
            receipt['frozen_inputs_preserved']=bool(members and all((session/'inputs/review'/PurePosixPath(name)).is_file() and (session/'inputs/review'/PurePosixPath(name)).read_bytes()==data for name,data in members.items()))
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Corrected native audit stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())
