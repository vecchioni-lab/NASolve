#!/usr/bin/env python3
"""Bound one geometry-only trial with the native-qualified plane-gradient correction."""
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
REVIEW_SHA256 = 'ba15d9f2d71db8b8defd7bcbbab854cffa841d210ee51b98daa736142cde5b7d'
ORDER_PREFIX = 'native_correction/cif-corrected-gradient-vcd7r2mp'
CORRECTION_PREFIX = 'native_correction/cif-corrected-gradient-noumvj1o'
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_corrected_geometry_review.zip')
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


def _read_cedar24(members):
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
    return prior,geometry,coordinates


def _read_cedar25(members):
    _verify_manifest(members,794);prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-native-corrected-gradient-probe' or prior.get('delivery_prefix')!='25_Cedar'
            or prior.get('status')!='REVIEW' or prior.get('analysis_completed') is not True
            or prior.get('original_archive_preserved') is not True or prior.get('frozen_inputs_preserved') is not True
            or prior.get('native_execution')!='COMPLETED' or prior.get('model_optimization')!='NOT_RUN'
            or prior.get('installed_phenix_edits')!='NOT_RUN' or prior.get('automatic_adoption') is not False
            or prior.get('policy_authority')!='NARestraints' or prior.get('prerequisite_mechanics_replayed') is not True
            or prior.get('prior_convergence')!='NOT_CONVERGED_ERROR'):
        raise ValueError('Require preserved completed Cedar 25 evidence')
    audit=prior['native_correction_audit'];result=audit['result'];_native_artifacts(members,audit,CORRECTION_PREFIX)
    if audit!=json.loads(members[CORRECTION_PREFIX+'/correction_receipt.json']) or result!=json.loads(members[CORRECTION_PREFIX+'/correction_result.json']):raise ValueError('Inconsistent captured correction receipt/result')
    if (result.get('policy_id')!='cif-fixed-native-corrected-gradient-audit-v1' or result.get('correction_policy_id')!='native-parallelity-complete-accumulation-v1'
            or result.get('status')!='REVIEW' or not result.get('analysis_completed') or not result.get('captured_inventory_matches')
            or result.get('model_optimization')!='NOT_RUN' or result.get('automatic_adoption') is not False
            or result.get('correction_qualification')!=prior.get('correction_qualification')
            or result.get('correction_qualification') not in {'DERIVATIVE_REVIEW','SAMPLED_NATIVE_DERIVATIVES_PASS'}
            or set(result.get('cases',{}))!={'initial','full_precision','pdb_rounded'}
            or not 0<result.get('evaluation_calls',0)<=5500 or result.get('correction_statistics',{}).get('max_energy_change')!=0.
            or not result.get('constraint_signature_before') or result['constraint_signature_before']!=result.get('constraint_signature_after')):
        raise ValueError('Incomplete corrected-gradient prerequisite')
    frozen={n.removeprefix('inputs/review/'):data for n,data in members.items() if n.startswith('inputs/review/')}
    previous,geometry,coordinates=_read_cedar24(frozen)
    expected=json.loads(members[CORRECTION_PREFIX+'/expected_inventory.json']);actual=json.loads(members[CORRECTION_PREFIX+'/native_validation.json'])
    if expected!=json.loads(frozen[CAPTURE_PREFIX+'/expected_inventory.json']):raise ValueError('Captured correction manager differs')
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):raise ValueError('Captured correction inventory differs')
    old=previous['native_parallelity_audit'];old_result=old['result'];capture=json.loads(members[CORRECTION_PREFIX+'/correction_spec.json'])
    signature=lambda receipt:[(r['role'],r['sha256'],r['size']) for r in receipt['inputs']]
    if (signature(audit)!=signature(old) or capture['coordinate_cases']!=coordinates
            or result['constraint_signature_before']!=old_result['constraint_signature_before']
            or any(result[key]!=old_result[key] for key in ['installed_numeric_sources','installed_adapter_sources','installed_parallelity_sources'])):
        raise ValueError('Correction coordinates, inputs or sources differ')
    for label,case in result['cases'].items():
        if set(case['families'])!={'all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded'}:raise ValueError('Incomplete captured category inventory')
        baseline=case['families']['parallelity']['baseline'];detail=baseline['parallelity_correction']
        if any(len(detail[key])!=3*expected['atom_count'] for key in ['plane_gradient','native_plane_gradient']):raise ValueError('Incomplete captured plane arrays')
        raw=result['raw_baseline_checks'][label]
        if not raw['captured_raw_baseline_match'] or raw['target']!=capture['raw_references'][label]['target']:raise ValueError('Captured raw baseline differs')
    for row in result['installed_parallelity_sources']:
        data=members[CORRECTION_PREFIX+'/installed_source/'+row['path']]
        if len(data)!=row['bytes'] or _sha(data)!=row['sha256']:raise ValueError('Captured correction plane source differs')
    return prior,geometry,coordinates


def _read_capsule(path,expected_sha=None):
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or REVIEW_SHA256):raise ValueError('Require the exact verified Cedar 26 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries=archive.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):raise ValueError('Unsafe or duplicate review member')
        members={entry.filename:archive.read(entry) for entry in entries}
    _verify_manifest(members,857);prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-native-plane-order-gradient-probe' or prior.get('delivery_prefix')!='26_Cedar'
            or prior.get('status')!='REVIEW' or prior.get('analysis_completed') is not True
            or prior.get('original_archive_preserved') is not True or prior.get('frozen_inputs_preserved') is not True
            or prior.get('native_execution')!='COMPLETED' or prior.get('model_optimization')!='NOT_RUN'
            or prior.get('installed_phenix_edits')!='NOT_RUN' or prior.get('automatic_adoption') is not False
            or prior.get('policy_authority')!='NARestraints' or prior.get('prerequisite_mechanics_replayed') is not True
            or prior.get('prior_convergence')!='NOT_CONVERGED_ERROR'
            or prior.get('correction_qualification')!='SAMPLED_NATIVE_DERIVATIVES_PASS'):
        raise ValueError('Require preserved native-qualified Cedar 26 evidence')
    audit=prior['native_correction_audit'];result=audit['result'];_native_artifacts(members,audit,ORDER_PREFIX)
    if audit!=json.loads(members[ORDER_PREFIX+'/correction_receipt.json']) or result!=json.loads(members[ORDER_PREFIX+'/correction_result.json']):raise ValueError('Inconsistent qualified correction receipt/result')
    if (result.get('policy_id')!='cif-fixed-native-plane-order-gradient-audit-v1' or result.get('correction_policy_id')!='native-parallelity-both-first-planes-v1'
            or result.get('plane_order_safe') is not True or result.get('status')!='REVIEW'
            or result.get('correction_qualification')!='SAMPLED_NATIVE_DERIVATIVES_PASS'
            or result.get('analysis_completed') is not True or not result.get('captured_inventory_matches')
            or result.get('model_optimization')!='NOT_RUN' or result.get('automatic_adoption') is not False
            or set(result.get('cases',{}))!={'initial','full_precision','pdb_rounded'}
            or not 0<result.get('evaluation_calls',0)<=5500 or result.get('correction_statistics',{}).get('max_energy_change')!=0.
            or not result.get('plane_order_audit',{}).get('order_safe_qualified')
            or not result.get('constraint_signature_before') or result['constraint_signature_before']!=result.get('constraint_signature_after')):
        raise ValueError('Incomplete native-qualified derivative prerequisite')
    if any(not case.get('sampled_gradients_consistent') for case in result['cases'].values()):raise ValueError('Unqualified global/category derivative case')
    frozen={n.removeprefix('inputs/review/'):data for n,data in members.items() if n.startswith('inputs/review/')}
    previous,geometry,coordinates=_read_cedar25(frozen)
    expected=json.loads(members[ORDER_PREFIX+'/expected_inventory.json']);actual=json.loads(members[ORDER_PREFIX+'/native_validation.json'])
    if expected!=json.loads(frozen[CORRECTION_PREFIX+'/expected_inventory.json']):raise ValueError('Qualified native manager differs')
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):raise ValueError('Qualified native inventory differs')
    old=previous['native_correction_audit'];old_result=old['result'];spec=json.loads(members[ORDER_PREFIX+'/correction_spec.json'])
    signature=lambda receipt:[(r['role'],r['sha256'],r['size']) for r in receipt['inputs']]
    if (signature(audit)!=signature(old) or spec['coordinate_cases']!=coordinates
            or result['constraint_signature_before']!=old_result['constraint_signature_before']
            or any(result[k]!=old_result[k] for k in ['installed_numeric_sources','installed_adapter_sources','installed_parallelity_sources'])):
        raise ValueError('Qualified coordinates, inputs or source identities differ')
    for row in result['installed_parallelity_sources']:
        data=members[ORDER_PREFIX+'/installed_source/'+row['path']]
        if len(data)!=row['bytes'] or _sha(data)!=row['sha256']:raise ValueError('Qualified installed plane source differs')
    return members,prior,geometry,coordinates,original


def _run_trial(session,capture,phenix,iterations,timeout,receipt):
    from nasolve.cif_fixed_geometry import (run_fixed_geometry,write_geometry_candidate,
        review_fixed_coordinates,qualify_fixed_policy_geometry)
    from nasolve.cif_native_validation import inspect_native_bundle
    from nasolve.cif_captured_geometry import review_captured_geometry
    root=session/'inputs/review'/ORDER_PREFIX
    def paths(role):return [root/PurePosixPath(r['path']) for r in capture['inputs'] if r['role']==role]
    model=paths('model')[0];cifs=paths('dictionary');phils=paths('phil');before=capture['native_validation']
    _json(session/'initial_geometry_review.json',review_captured_geometry(before))
    print('Matching the verified NARestraints manager before one bounded geometry-only trial.',flush=True)
    receipt.update(native_execution='ATTEMPTED',model_optimization='EXPLICIT_BOUNDED_TRIAL')
    trial=run_fixed_geometry(model,cifs,phils,before,session/'geometry_trial',phenix.executables['phenix.python'],
        environment=phenix.environment,phenix_version=phenix.version,max_iterations=iterations,
        timeout_seconds=timeout,policy_inventory=True,validated_correction={
            'result':capture['result'],'archive_sha256':receipt['prior_archive']['sha256'],
            'correction_core_sha256':_sha((root/'correction_core.py').read_bytes())})
    receipt['geometry_trial']=trial;receipt['native_execution']=trial['execution']['status']
    if trial['status']!='REVIEW':raise ValueError('NA policy geometry trial did not complete; inspect retained worker evidence')
    result=trial['result'];receipt['convergence']=trial['convergence']
    receipt['endpoint_derivative_qualification']=result['endpoint_derivative_qualification']
    candidate=session/'candidate/corrected_geometry_model.pdb'
    serialization=write_geometry_candidate(model,candidate,before,result['final_sites_cart'])
    receipt['serialization']=serialization;_json(session/'serialization_review.json',serialization)
    full=review_fixed_coordinates(before,result['final_sites_cart'])
    _json(session/'full_precision_geometry_review.json',full)
    print('Checking serialized candidate identities, definitions and every fixed policy proxy.',flush=True)
    after=inspect_native_bundle(candidate,cifs,session/'native_roundtrip',phenix.executables['phenix.python'],
        environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=timeout,
        phil_files=phils,phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',policy_inventory=True)
    receipt['native_roundtrip']=after;receipt['native_execution']=after['execution']['status']
    if after['status']!='REVIEW' or after['execution'].get('returncode')!=0:
        raise ValueError('Serialized candidate did not complete native interpretation')
    mechanics=qualify_fixed_policy_geometry(before,after['native_validation'],candidate,serialization)
    receipt['native_mechanics']=mechanics;_json(session/'native_mechanics.json',mechanics)
    if not mechanics['mechanics_checks_pass']:raise ValueError('Geometry candidate changed native identities, definitions, proxies or policy')
    rounded=review_captured_geometry(after['native_validation'])
    _json(session/'rounded_native_geometry_review.json',rounded)
    receipt['geometry_summaries']={'full_precision':full['summary'],'serialized_native':rounded['summary']}
    if _sha(candidate.read_bytes())!=serialization['candidate_sha256']:raise ValueError('Geometry candidate changed')
    receipt['native_execution']='COMPLETED'
    print('Native mechanics checks: PASS',flush=True)
    print('Stopping evidence:',trial['convergence'],'('+result['stopping']['reason']+')',flush=True)
    print('Fixed-policy target:',result['initial']['target'],'->',result['final']['target'],flush=True)
    print('Gradient norm:',result['initial']['gradient_norm'],'->',result['final']['gradient_norm'],flush=True)
    print('Endpoint derivative qualification:',result['endpoint_derivative_qualification'],flush=True)
    for label,case in result['endpoint_gradient_audit']['cases'].items():
        print('endpoint '+label+':',{'sampled_gradients_consistent':case['sampled_gradients_consistent'],
            'families_requiring_review':[name for name,value in case['families'].items() if not value['sampled_directions_consistent']]},flush=True)
    print('Separate candidate:',candidate,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/26_Cedar_cif-plane-order-wn30xwws/26_Cedar_wn30xwws_cif_plane_order_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--max-iterations',type=int,default=1000)
    parser.add_argument('--timeout-seconds',type=int,default=1200)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;original=None;review=None;members=None
    receipt={'schema_version':1,'kind':'cif-corrected-na-geometry-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'SEPARATE_CANDIDATE_ONLY','model_optimization':'NOT_RUN',
        'dictionary_generation':'NOT_RUN','policy_recompilation':'NOT_RUN','readyset_retry':'NOT_RUN','refinement':'NOT_RUN',
        'scientific_approval':'NOT_RUN','automatic_adoption':False,'diffraction_data':'NOT_READ','policy_authority':'NARestraints',
        'installed_phenix_edits':'NOT_RUN','convergence':'NOT_ASSESSED','endpoint_derivative_qualification':'NOT_RUN',
        'starting_coordinates':'CAPTURED_INITIAL','limits':{'max_iterations':args.max_iterations,'max_calls':args.max_iterations*20,
            'timeout_seconds':args.timeout_seconds,'endpoint_gradient_audit_calls':4000}}
    try:
        if not 1<=args.max_iterations<=1000 or not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid iteration or timeout bound')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,prior,geometry,coordinates,original=_read_capsule(review);parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-corrected-geometry-',dir=parent))
        _materialize(runtime,session/'runtime');frozen=session/'inputs/review';_materialize(members,frozen)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_corrected_geometry import validate_gradient_qualification
        from nasolve.cif_fixed_geometry import qualify_fixed_policy_geometry,classify_stopping
        expected=json.loads(members[ORDER_PREFIX+'/expected_inventory.json']);audit=prior['native_correction_audit'];result=audit['result']
        validate_gradient_qualification(result,expected['atom_count'])
        if _sha(runtime['src/nasolve/cif_parallelity_correction.py'])!=_sha(members[ORDER_PREFIX+'/correction_core.py']):raise ValueError('Qualified correction source changed')
        candidate=frozen/'inputs/review/inputs/review'/GEOMETRY_BUNDLE_PREFIX/'candidate/na_policy_geometry_model.pdb'
        replay=qualify_fixed_policy_geometry(expected,geometry['native_roundtrip']['native_validation'],candidate,geometry['serialization'])
        if replay!=geometry['native_mechanics'] or not replay['mechanics_checks_pass']:raise ValueError('Native mechanics prerequisite does not replay')
        if classify_stopping(geometry['geometry_trial']['result']['stopping'])!='NOT_CONVERGED_ERROR':raise ValueError('Prior stopping evidence does not replay')
        receipt.update(prior_archive={'sha256':_sha(original),'bytes':len(original),'verified_payloads':857},
            prior_convergence='NOT_CONVERGED_ERROR',prerequisite_mechanics_replayed=True,derivative_precondition='SAMPLED_NATIVE_DERIVATIVES_PASS',
            correction_policy_id='native-parallelity-both-first-planes-v1',qualified_correction_source_sha256=_sha(members[ORDER_PREFIX+'/correction_core.py']),
            selected_native_receipt={'anchor':'probe_directory','path':'inputs/review/'+ORDER_PREFIX+'/correction_receipt.json'},
            objective='UNCHANGED_NATIVE_UNNORMALIZED_FIXED_NA_POLICY',limitations=[
                'One bounded geometry-only trial from the same initial coordinates as Cedar 22, with the qualified gradient correction.',
                'Native targets, weights, static proxy membership, dictionaries and compiled NARestraints policy remain fixed.',
                'No pair guessing, policy recompilation, dictionary generation, installed-Phenix edit, diffraction/refinement or adoption.',
                'Stopping, endpoint derivatives and native PDB mechanics are independent verdicts; target reduction alone approves none.',
                'Full-precision and PDB-rounded fixed-manager values stay separate; fresh-manager energies are not equated.',
                'Charge, pucker, absolute stereochemistry, complete geometry and experimental fit remain outside scientific approval.'])
        print('Corrected fixed NARestraints geometry trial:',BUNDLE['delivery_prefix'],flush=True)
        print('Replaying the original initial coordinates with the native-qualified plane-gradient policy.',flush=True)
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            capture={**audit,'native_validation':expected};native_sources=_fingerprints(phenix,capture)
            numeric_capture={**audit,'native_validation':{'installed_api_sources':result['installed_numeric_sources']}}
            adapter_capture={**audit,'native_validation':{'installed_api_sources':result['installed_adapter_sources']}}
            numeric=_fingerprints(phenix,numeric_capture);adapters=_fingerprints(phenix,adapter_capture)
            receipt.update(installed_api_sources=native_sources,installed_numeric_sources=numeric,installed_adapter_sources=adapters)
            _run_trial(session,capture,phenix,args.max_iterations,args.timeout_seconds,receipt)
            if (_fingerprints(phenix,capture)!=native_sources or _fingerprints(phenix,numeric_capture)!=numeric
                    or _fingerprints(phenix,adapter_capture)!=adapters):raise ValueError('Installed native sources changed')
        if any((frozen/PurePosixPath(name)).read_bytes()!=data for name,data in members.items()):raise ValueError('Frozen source evidence changed')
        if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (corrected fixed-policy geometry trial; scientific qualification remains open)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(original is not None and review and review.read_bytes()==original)
            receipt['frozen_inputs_preserved']=bool(members is not None and all((session/'inputs/review'/PurePosixPath(n)).is_file()
                and (session/'inputs/review'/PurePosixPath(n)).read_bytes()==data for n,data in members.items()))
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Corrected geometry trial stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())
