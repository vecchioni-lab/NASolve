#!/usr/bin/env python3
"""Prepare isolated numerical candidates from exact declared chemical graphs."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import zipfile

BUNDLE = None  # @bundle-metadata@
RUNTIME_BASE64 = None  # @runtime-base64@
REVIEW_SHA256 = '49981767cfd424532e14ac637ca01f5923de967d8cc7a6c8c0f94531b8ca1306'
CEDAR27_SHA256 = 'c43ede693180dd8b5ba7cbcfa33cf89c8167d185e50f81ca6f12299a529feec1'
CURRENT_TRIAL_PREFIX = 'geometry_trial/cif-fixed-geometry-hlr66wod'
CURRENT_READBACK_PREFIX = 'native_roundtrip/cif-native-0ogbolg7'
CURRENT_SOURCE_SHA256 = {
    'geometry_worker.py':'348a28b7a85883eb1bdf6767a75cb4d6db6c500d82539ca734d8d7ea6ad9f47f',
    'corrected_geometry_core.py':'c2152eaf87e1fd8f15f14afb593a8c6fa014f382c3f438645f6ea43f667b2be1',
}
ORDER_PREFIX = 'native_correction/cif-corrected-gradient-vcd7r2mp'
CORRECTION_PREFIX = 'native_correction/cif-corrected-gradient-noumvj1o'
CAPTURE_PREFIX = 'native_parallelity/cif-parallelity-audit-fzeylrjo'
GEOMETRY_BUNDLE_PREFIX = 'inputs/review/inputs/review'
GEOMETRY_PREFIX = 'geometry_trial/cif-fixed-geometry-t2c9xuw6'
READBACK_PREFIX = 'native_roundtrip/cif-native-wd459r67'
PREVIOUS_TRIAL_PREFIX = 'geometry_trial/cif-fixed-geometry-bi2dftve'
PREVIOUS_READBACK_PREFIX = 'native_roundtrip/cif-native-6h3yugfv'
CAPTURED_TRIAL_SOURCE_SHA256 = {
    'geometry_worker.py':'904c9ac79f213ef2f299b1459b6f4722b8b38ec7f3b73003dafc0c0f8f021f4a',
    'corrected_geometry_core.py':'454bb9fb9db2ad7277f084453ec278dd61d7be36efd7d6d97290fa451f7720f9',
}
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_numerical_recovery_review.zip')
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


def _read_cedar26(members):
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
    return prior,geometry,coordinates


def _read_cedar27(members):
    _verify_manifest(members,980);prior=json.loads(members['probe_receipt.json'])
    if (prior.get('kind')!='cif-corrected-na-geometry-probe' or prior.get('delivery_prefix')!='27_Cedar'
            or prior.get('status')!='REVIEW' or prior.get('analysis_completed') is not True
            or prior.get('native_execution')!='COMPLETED' or prior.get('model_optimization')!='EXPLICIT_BOUNDED_TRIAL'
            or prior.get('original_archive_preserved') is not True or prior.get('frozen_inputs_preserved') is not True
            or prior.get('prerequisite_mechanics_replayed') is not True or prior.get('automatic_adoption') is not False
            or prior.get('policy_authority')!='NARestraints' or prior.get('installed_phenix_edits')!='NOT_RUN'
            or prior.get('policy_recompilation')!='NOT_RUN' or prior.get('dictionary_generation')!='NOT_RUN'
            or prior.get('convergence')!='NOT_CONVERGED_LIMIT' or prior.get('prior_convergence')!='NOT_CONVERGED_ERROR'
            or prior.get('starting_coordinates')!='CAPTURED_INITIAL'
            or prior.get('endpoint_derivative_qualification')!='SAMPLED_NATIVE_DERIVATIVES_PASS'):
        raise ValueError('Require preserved completed Cedar 27 limit/derivative/mechanics evidence')
    frozen={n.removeprefix('inputs/review/'):data for n,data in members.items() if n.startswith('inputs/review/')}
    qualified,old_geometry,coordinates=_read_cedar26(frozen)
    audit=qualified['native_correction_audit'];proof=audit['result']
    trial=prior['geometry_trial'];readback=prior['native_roundtrip'];result=trial['result']
    for receipt,prefix in [(trial,PREVIOUS_TRIAL_PREFIX),(readback,PREVIOUS_READBACK_PREFIX)]:_native_artifacts(members,receipt,prefix)
    if (trial!=json.loads(members[PREVIOUS_TRIAL_PREFIX+'/geometry_receipt.json'])
            or result!=json.loads(members[PREVIOUS_TRIAL_PREFIX+'/geometry_result.json'])
            or readback!=json.loads(members[PREVIOUS_READBACK_PREFIX+'/native_receipt.json'])):
        raise ValueError('Inconsistent saved corrected trial receipt/result')
    for name,digest in CAPTURED_TRIAL_SOURCE_SHA256.items():
        if _sha(members[PREVIOUS_TRIAL_PREFIX+'/'+name])!=digest:raise ValueError('Captured corrected-trial source differs')
    if (members[PREVIOUS_TRIAL_PREFIX+'/correction_core.py']!=frozen[ORDER_PREFIX+'/correction_core.py']
            or members[PREVIOUS_TRIAL_PREFIX+'/native_worker.py']!=members[PREVIOUS_READBACK_PREFIX+'/native_worker.py']
            or json.loads(members[PREVIOUS_TRIAL_PREFIX+'/gradient_validation.json'])!=proof):
        raise ValueError('Saved trial did not preserve its qualified correction evidence')
    expected=json.loads(members[PREVIOUS_TRIAL_PREFIX+'/expected_inventory.json'])
    if expected!=json.loads(frozen[ORDER_PREFIX+'/expected_inventory.json']):raise ValueError('Saved trial manager differs')
    actual=json.loads(members[PREVIOUS_TRIAL_PREFIX+'/native_validation.json'])
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):raise ValueError('Saved trial bootstrap differs')
    signature=lambda receipt:[(r['role'],r['sha256'],r['size']) for r in receipt['inputs']]
    if signature(trial)!=signature(audit) or signature(readback)[1:]!=signature(trial)[1:]:raise ValueError('Saved trial native inputs differ')
    mechanics=prior['native_mechanics']
    if (mechanics!=json.loads(members['native_mechanics.json']) or not mechanics.get('mechanics_checks_pass')
            or len(mechanics['checks'])!=17 or len({r['check'] for r in mechanics['checks']})!=17
            or any(r['status']!='PASS' for r in mechanics['checks'])):raise ValueError('Saved candidate native mechanics are not qualified')
    if (result.get('status')!='REVIEW' or result.get('policy_id')!='cif-fixed-na-corrected-geometry-trial-v1'
            or result.get('captured_inventory_matches') is not True or result.get('qualified_initial_snapshot_matches') is not True
            or result.get('correction_policy_id')!='native-parallelity-both-first-planes-v1' or result.get('policy_inventory') is not True
            or result.get('endpoint_derivative_qualification')!='SAMPLED_NATIVE_DERIVATIVES_PASS'
            or result.get('constraint_signature_before')!=proof['constraint_signature_before']
            or result.get('constraint_signature_after')!=proof['constraint_signature_before']):raise ValueError('Incomplete saved corrected endpoint')
    for name,old in [('installed_optimizer_sources','installed_numeric_sources'),('installed_adapter_sources','installed_adapter_sources'),('installed_parallelity_sources','installed_parallelity_sources')]:
        if result[name]!=proof[old]:raise ValueError('Saved corrected trial source identities differ')
    if (prior['prior_archive']['sha256']!=result['derivative_validation_archive']
            or prior['prior_archive']['verified_payloads']!=857
            or _sha(members['candidate/corrected_geometry_model.pdb'])!=prior['serialization']['candidate_sha256']
            or readback['inputs'][0]['sha256']!=prior['serialization']['candidate_sha256']):raise ValueError('Saved endpoint provenance differs')
    for row in result['installed_parallelity_sources']:
        data=members[PREVIOUS_TRIAL_PREFIX+'/installed_source/'+row['path']]
        if len(data)!=row['bytes'] or _sha(data)!=row['sha256']:raise ValueError('Saved installed plane source differs')
    return members,qualified,prior,coordinates



def _read_cedar28(members):
    _verify_manifest(members,1104);current=json.loads(members['probe_receipt.json'])
    if (current.get('kind')!='cif-corrected-na-geometry-continuation-probe' or current.get('delivery_prefix')!='28_Cedar'
            or current.get('status')!='REVIEW' or current.get('analysis_completed') is not True
            or current.get('native_execution')!='COMPLETED' or current.get('model_optimization')!='EXPLICIT_BOUNDED_TRIAL'
            or current.get('original_archive_preserved') is not True or current.get('frozen_inputs_preserved') is not True
            or current.get('automatic_adoption') is not False or current.get('policy_authority')!='NARestraints'
            or current.get('installed_phenix_edits')!='NOT_RUN' or current.get('policy_recompilation')!='NOT_RUN'
            or current.get('dictionary_generation')!='NOT_RUN' or current.get('convergence')!='NOT_CONVERGED_LIMIT'
            or current.get('prior_convergence')!='NOT_CONVERGED_LIMIT'
            or current.get('starting_coordinates')!='SAVED_FULL_PRECISION_ENDPOINT'
            or current.get('endpoint_derivative_qualification')!='SAMPLED_NATIVE_DERIVATIVES_PASS'):
        raise ValueError('Require completed qualified Cedar 28 limit evidence')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    _,qualified,previous,coordinates=_read_cedar27(nested)
    proof=qualified['native_correction_audit']['result'];trial=current['geometry_trial'];readback=current['native_roundtrip'];q=trial['result']
    for receipt,prefix in [(trial,CURRENT_TRIAL_PREFIX),(readback,CURRENT_READBACK_PREFIX)]:_native_artifacts(members,receipt,prefix)
    if (trial!=json.loads(members[CURRENT_TRIAL_PREFIX+'/geometry_receipt.json'])
            or q!=json.loads(members[CURRENT_TRIAL_PREFIX+'/geometry_result.json'])
            or readback!=json.loads(members[CURRENT_READBACK_PREFIX+'/native_receipt.json'])):raise ValueError('Inconsistent continuation receipt/result')
    for name,digest in CURRENT_SOURCE_SHA256.items():
        if _sha(members[CURRENT_TRIAL_PREFIX+'/'+name])!=digest:raise ValueError('Captured continuation source differs')
    if (members[CURRENT_TRIAL_PREFIX+'/correction_core.py']!=nested[PREVIOUS_TRIAL_PREFIX+'/correction_core.py']
            or members[CURRENT_TRIAL_PREFIX+'/native_worker.py']!=members[CURRENT_READBACK_PREFIX+'/native_worker.py']
            or json.loads(members[CURRENT_TRIAL_PREFIX+'/gradient_validation.json'])!=proof
            or json.loads(members[CURRENT_TRIAL_PREFIX+'/continuation_validation.json'])!=previous['geometry_trial']['result']):
        raise ValueError('Continuation did not preserve its qualified source/endpoint evidence')
    expected=json.loads(members[CURRENT_TRIAL_PREFIX+'/expected_inventory.json'])
    if expected!=json.loads(nested[PREVIOUS_TRIAL_PREFIX+'/expected_inventory.json']):raise ValueError('Continuation manager differs')
    actual=json.loads(members[CURRENT_TRIAL_PREFIX+'/native_validation.json'])
    if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):raise ValueError('Continuation bootstrap differs')
    signature=lambda r:[(x['role'],x['sha256'],x['size']) for x in r['inputs']]
    if signature(trial)!=signature(previous['geometry_trial']) or signature(readback)[1:]!=signature(trial)[1:]:raise ValueError('Continuation native inputs differ')
    if (q.get('policy_id')!='cif-fixed-na-corrected-geometry-continuation-v1' or q.get('status')!='REVIEW'
            or q.get('qualified_initial_snapshot_matches') is not True or q.get('qualified_continuation_snapshot_matches') is not True
            or q.get('policy_inventory') is not True or q.get('correction_policy_id')!='native-parallelity-both-first-planes-v1'
            or q.get('endpoint_derivative_qualification')!='SAMPLED_NATIVE_DERIVATIVES_PASS'
            or q.get('constraint_signature_before')!=proof['constraint_signature_before']
            or q.get('constraint_signature_after')!=proof['constraint_signature_before']):raise ValueError('Incomplete qualified continuation endpoint')
    for name,old in [('installed_optimizer_sources','installed_numeric_sources'),('installed_adapter_sources','installed_adapter_sources'),('installed_parallelity_sources','installed_parallelity_sources')]:
        if q[name]!=proof[old]:raise ValueError('Continuation source identities differ')
    cont=q['continuation'];old=previous['geometry_trial']['result'];oldstop=old['stopping']
    if (current['prior_archive']['sha256']!=CEDAR27_SHA256 or current['prior_archive']['verified_payloads']!=980
            or cont!=current['continuation'] or cont['archive_sha256']!=CEDAR27_SHA256
            or cont['prior_stopping']!=oldstop or cont['prior_total_iterations']!=oldstop['iterations'] or cont['prior_total_calls']!=oldstop['calls']
            or cont['optimizer_history']!='FRESH_LBFGS_FROM_SAVED_COORDINATES'
            or cont['total_iterations']!=cont['prior_total_iterations']+q['stopping']['iterations']
            or cont['total_calls']!=cont['prior_total_calls']+q['stopping']['calls']
            or q['derivative_validation_archive']!=old['derivative_validation_archive']):raise ValueError('Continuation lineage differs')
    for field in ['target','gradient_norm']:
        if q['initial'][field]!=old['final'][field]:raise ValueError('Continuation did not start at the saved endpoint')
    mechanics=current['native_mechanics']
    if (mechanics!=json.loads(members['native_mechanics.json']) or not mechanics.get('mechanics_checks_pass')
            or len(mechanics['checks'])!=17 or len({r['check'] for r in mechanics['checks']})!=17
            or any(r['status']!='PASS' for r in mechanics['checks'])):raise ValueError('Continuation native mechanics unqualified')
    if (_sha(members['candidate/continued_geometry_model.pdb'])!=current['serialization']['candidate_sha256']
            or readback['inputs'][0]['sha256']!=current['serialization']['candidate_sha256']):raise ValueError('Continuation serialization differs')
    for row in q['installed_parallelity_sources']:
        data=members[CURRENT_TRIAL_PREFIX+'/installed_source/'+row['path']]
        if len(data)!=row['bytes'] or _sha(data)!=row['sha256']:raise ValueError('Continuation installed source differs')
    return members,qualified,current



ROTATION_PREFIX = "native_rotation/cif-base-rotation-qin0vytg"
ROTATION_SOURCE_SHA256 = {'rotation_core.py': '48a0502f9c75562ade176b64b8859d44c4e29e660a08cb59121a55e62bdc7cbb', 'correction_core.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f', 'gradient_core.py': 'a4d6571512313ae7ce8522668bd152ea806c5478803b74e296822bc313f275cc', 'scalar_geometry_core.py': 'f0daab5796a2e22102e5cb66ca59fcf0c0397a4b270f0c561645109cbcda1116', 'corrected_geometry_core.py': 'c2152eaf87e1fd8f15f14afb593a8c6fa014f382c3f438645f6ea43f667b2be1', 'rotation_worker_py': '9d1cecc41fd176ba822d77f96fe5de3afc2390d2be602b81a4d42059efd77a71', 'native_worker_py': '9be6157312896609f51165adc6e5579365fa261709ac7633420bbea798373e78'}

def _read_cedar29_members(members):
    from nasolve.cif_numerical_recovery import validate_rotation_evidence, _same
    from nasolve.cif_base_rotation_audit import plan_base_rotations
    from nasolve.cif_corrected_geometry import validate_continuation
    _verify_manifest(members,1173)
    nested={n.removeprefix('inputs/review/'):data for n,data in members.items() if n.startswith('inputs/review/')}
    _,qualified,prior=_read_cedar28(nested)
    current=json.loads(members['probe_receipt.json']);audit=current['native_rotation_audit'];result=audit['result']
    if (current.get('kind')!='cif-fixed-na-base-rotation-probe' or current.get('delivery_prefix')!='29_Cedar'
            or current.get('status')!='REVIEW' or current.get('analysis_completed') is not True
            or current.get('native_execution')!='COMPLETED' or current.get('model_editing')!='NOT_RUN'
            or current.get('model_optimization')!='NOT_RUN' or current.get('automatic_adoption') is not False
            or any(current.get(k)!='NOT_RUN' for k in ['dictionary_generation','policy_recompilation','readyset_retry','refinement','installed_phenix_edits'])
            or any(current.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or current.get('policy_authority')!='NARestraints' or current.get('rotation_derivative_qualification')!='SAMPLED_ROTATION_DERIVATIVES_PASS'
            or current['prior_archive']['sha256']!='1f553b4e57e75afbd8e29824600d470825a2b428c231a6bd0365c4319b05fb6c'
            or current['prior_archive']['verified_payloads']!=1104):raise ValueError('Require completed qualified Cedar 29 orientation evidence')
    _native_artifacts(members,audit,ROTATION_PREFIX)
    if (audit!=json.loads(members[ROTATION_PREFIX+'/rotation_receipt.json'])
            or result!=json.loads(members[ROTATION_PREFIX+'/rotation_result.json'])):raise ValueError('Inconsistent rotation receipt/result')
    for name,digest in ROTATION_SOURCE_SHA256.items():
        name={'rotation_worker_py':'rotation_worker.py','native_worker_py':'native_worker.py'}.get(name,name)
        if _sha(members[ROTATION_PREFIX+'/'+name])!=digest:raise ValueError('Captured rotation source changed')
    expected=json.loads(members[ROTATION_PREFIX+'/expected_inventory.json'])
    actual=json.loads(members[ROTATION_PREFIX+'/native_validation.json'])
    spec=json.loads(members[ROTATION_PREFIX+'/rotation_spec.json']);proof=qualified['native_correction_audit']['result'];saved=prior['geometry_trial']['result']
    if (expected!=json.loads(nested[CURRENT_TRIAL_PREFIX+'/expected_inventory.json'])
            or any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy'])
            or json.loads(members[ROTATION_PREFIX+'/gradient_validation.json'])!=proof
            or json.loads(members[ROTATION_PREFIX+'/endpoint_validation.json'])!=saved):raise ValueError('Rotation did not preserve qualified manager/endpoint evidence')
    if not _same(current['rotation_plan'],plan_base_rotations(expected,saved['final_sites_cart'])) or spec['plan']!=current['rotation_plan'] or json.loads(members['base_rotation_plan.json'])!=current['rotation_plan']:raise ValueError('Rotation graph plan differs')
    if spec['correction_core_sha256']!=_sha(members[ROTATION_PREFIX+'/correction_core.py']):raise ValueError('Rotation correction identity differs')
    signature=lambda a:[(r['role'],r['sha256'],r['size']) for r in a['inputs']]
    if signature(audit)!=signature(prior['geometry_trial']):raise ValueError('Rotation inputs differ from saved manager')
    for k in ['installed_numeric_sources','installed_adapter_sources','installed_parallelity_sources']:
        if result[k]!=proof[k]:raise ValueError('Rotation native source identities differ')
    for row in result['installed_parallelity_sources']:
        data=members[ROTATION_PREFIX+'/installed_source/'+row['path']]
        if len(data)!=row['bytes'] or _sha(data)!=row['sha256']:raise ValueError('Rotation installed source payload differs')
    validate_continuation(saved,proof,expected['atom_count'])
    validate_rotation_evidence(result,current['rotation_plan'],saved,proof['constraint_signature_before'])
    return qualified,prior,current


CEDAR30_SHA256 = '0469d2b1da39771f910b6721b73484a956d3485e95379df657aac32fc9f56e43'
CEDAR30_BUILD_SHA256 = '11b0ff696b1e21ab50363a60e8e40eab74f60edfcaa589d59b3d8b72dc086ed8'
CEDAR30_GRAPH_SHA256 = 'c278ce02a62be9170a19daaf8fd189e742e8ebfa9d650bb809de01bf065e2057'
CEDAR30_RECOVERY_PREFIX = 'generation/cif-numerical-recovery-w7lb3ylz'
CEDAR30_GENERATION_PREFIX = CEDAR30_RECOVERY_PREFIX+'/generation/cif-generation-0qssnat0'
CEDAR31_SHA256 = 'ee01c4a3275b3448fcca392545aeee0e4c70b9e5338af71a5f8baf553c160262'
CEDAR31_BUILD_SHA256 = 'cd9888888f309b8e5ee4bce15e12c1893b1cd1a2588dfb66ce015bc24ba4e5f0'
CEDAR31_CASES = {
    'DP': ('generation/cif-numerical-recovery-tqlk3s6o', 'cif-generation-bm5va9m2',
           'b8b1287b91008ad13829677a54997920cd7b0f8e02e0d9a96797226afd265708'),
    'PDU': ('generation/cif-numerical-recovery-t1g4nh0w', 'cif-generation-52bttx4f',
            'ac4d8854e0154d6a694d59473a8b47859b370df0c068f3929b6f2b1e5cba26b4'),
}
PDU_SOURCE_SHA256 = 'cd192f18964a28c628544ae1c0b4b1f2aed124e1b90a21b9c6ca0aa4458c0292'
CEDAR32_SHA256 = '285d74e1927791c11eadddf81c8ee93f54a5a4feb9dd410511e0ccf97cd46342'
CEDAR32_BUILD_SHA256 = '9781e61cd6d84567998dde9957eee776ac2559796bc7d2049f3eee7ae9ec6db9'
CEDAR33_SHA256 = '1ebb70ca3d47696208b050ecf19f0e62c9e86a9174e9c67a10a13d28fb9971dd'
CEDAR33_BUILD_SHA256 = '50a102ea4785867fb3164861f9794cfcbbdc33d51c785e2e243f1fc7adaddc5e'
CEDAR33_CASES = {
    'DP':('generation/cif-numerical-recovery-d9_k11qs','cif-generation-4er4oy9t',
          '6b914d7fed9a98e30ed68b2381507e6d5bb0dc9b351fee48d42ced085c9501fa'),
    'PDU':('generation/cif-numerical-recovery-wgp6l12j','cif-generation-afxengms',
           'ac4d8854e0154d6a694d59473a8b47859b370df0c068f3929b6f2b1e5cba26b4'),
}
CEDAR33_OPTIONS_SHA256 = 'e7bdf4ac2b9dea237f6c29b8015fa665834c435173c1d0662ed4d51b384e6dbd'
CEDAR33_PDU_CANDIDATE_SHA256 = '10798e337cfa4804601595244581a03745b7893514ce1cb02cde9be426fcf88a'
CEDAR34_SHA256 = 'a4a50a84eb2cebe17230230c50f533eb9acc899084b5e989d95b366cc3f783b5'
CEDAR34_BUILD_SHA256 = '6b96148da00d4eb15021600a772e6f0cfd7a107aa4fda709b6266f27d281542c'
CEDAR34_WORKER_SHA256 = '610d649a34ac7cca15222083eea8984e50a22c9fc19713c3329ed2c76800567b'
CEDAR35_SHA256 = '631cecd47157444e82af23b69e76d581cbfdf5db8276c757b5701379daaea8dc'
CEDAR35_BUILD_SHA256 = 'e76d8369c3141d724cb1105b2f6170324f77ffc6285d2b9931c19be9b7d9135d'
CEDAR36_SHA256 = '23790f7fc3b7a507e7d7f88f861451ce1897dd92097b4e38b52efc9361f1bf94'
CEDAR36_BUILD_SHA256 = 'c20f2849675a551535eb9df971bf746e39210ff7b2f642a2d8994bb0910a5768'
CEDAR36_WORKER_SHA256 = 'c889ec29a61bc3111991986bf25b92342b766c09e25bed2c202fcc6c7488290f'
CEDAR36_CONSUMER_SHA256 = {'DP':'4648c37ce867cce5a285d5f31a394a334b2cb9e347936511525a947927798bfa',
                          'PDU':'ac4d8854e0154d6a694d59473a8b47859b370df0c068f3929b6f2b1e5cba26b4'}
CEDAR36_READER_SOURCES = {
    'elbow/chemistry/any_chemical_format_reader.py':'17c4cc38484f8f5ddea90ae3d9a04e07c73ee18ccb722ad574c753bdb9b1cbd4',
    'elbow/formats/monomer_library_cif_parser.py':'f689ede2d465084abd0dc5313bf5e2dbc84dc9621d2f48969e3aef31bf161259',
}
CEDAR37_SHA256 = '99a47b583d5fbc3fd0a32da492b1bfa07d5e3148a52306e5c68501049ea53106'
CEDAR37_BUILD_SHA256 = '61b0309dcf3f6f512a3a0193accdb125766de9e569af4d1fc44091d31201e368'
CEDAR37_WORKER_SHA256 = '72e02c470d52df6eeb13d72d2c10e09293dcb50544653b66204553277a72d8f2'
CEDAR37_CONSUMER_SHA256 = {'DP':'071486fd8113788b4d1125126fa8167804a7c953dd27ccfb68e273058d94aed7',
                          'PDU':'ac4d8854e0154d6a694d59473a8b47859b370df0c068f3929b6f2b1e5cba26b4'}
CEDAR38_SHA256 = 'dc85d4e04f295e67d17f9721ca7e577b394a12026d7bf1338f703207a68004ac'
CEDAR38_BUILD_SHA256 = 'b85f2016d33e14ab821d92446901bff7553b71eda357d2780a03ea24f4cdbb70'
CEDAR38_RESOURCE_WORKER_SHA256 = '09f31cede7d53ceef3bfcbb2c9d6635a65740c6bfdcb47cdeed95c5f90fff834'
CEDAR38_NATIVE_WORKER_SHA256 = '9be6157312896609f51165adc6e5579365fa261709ac7633420bbea798373e78'
CEDAR39_SHA256 = '1661c270c083be1a78f21f9d8e870da9042ba8f3ceff3e050aa430cceb7462f1'
CEDAR39_BUILD_SHA256 = 'eea1125f940eb6cd45b6558dad462be3fd3420184e52d8bdf6ca084142288b59'
CEDAR39_CATALOGUE_WORKER_SHA256 = 'ddb761ddc5cc405a40d06ab15f98eebfe224fd2114435d2d9f08de757ee60ee0'
CEDAR39_CCD_SHA256 = {'PDU':'98421454d759d217f48dc7cec1daa3d8ded6b7a64503486c8fd8b4e46e717258',
                      '5PC':'b0adede0c334091261cba543d9848c47165d8fdf3d46baf22b064e455bf38025'}
CEDAR42_SHA256 = '668a253670b79ad472184fb4e7f92feca5cacb30ce369d124dcc27963e960f77'
CEDAR42_BUILD_SHA256 = '4f2eb1b482fcf382f9bbaf27a8eb8d49a8dae670a7988f8d06cf2a95694c00ca'
CEDAR42_WORKER_SHA256 = '6bf5696e7c0ba1d3302281f5ee32160dd7c80a475a8ace3314e7cfa8fb887705'
CEDAR42_NATIVE_WORKER_SHA256 = '9be6157312896609f51165adc6e5579365fa261709ac7633420bbea798373e78'
CEDAR42_NATIVE_PREFIX = {'PDU':'readyset_controls/native/PDU/cif-native-0qfexcli','5PC':'readyset_controls/native/5PC/cif-native-l546wyy6'}
CEDAR42_CANDIDATE_SHA256 = {'PDU':'576d2601c34f3bee99473368e4a17657890d2b538e556c08318e0e760d09e2ae','5PC':'dc89031959b3fc95710675f64c6466472f22519491d4aabacbc072c6f9fc1ef7'}
CEDAR43_SHA256 = '00456d4c8223176a44d4fccf602876de81fbf2a949c5098b52061ce1c6654c09'
CEDAR43_BUILD_SHA256 = '97394da562e14f30e861d3e0b79892a288e67e4d273e8b71f84df52e3155b990'
CEDAR43_WORKER_SHA256 = '69bb1a3afd353e48c8633511197e9044f42cf5739e4805844a1dc04617dfc10b'
CEDAR43_NATIVE_PREFIX = {'PDU':'torsion_conditioning/PDU/cif-dihedral-conditioning-lz377mtf',
                         '5PC':'torsion_conditioning/5PC/cif-dihedral-conditioning-bl52r2wz'}
CEDAR44_SHA256 = 'cbf3d03755875b63f4b00544fa63ad4a515dd06f38a2b49c3bc6cfffa7ab619f'
CEDAR44_BUILD_SHA256 = '11d156c514857325f7874c430577a38ff6bd988d69ce31d353f8491eca65c816'
CEDAR44_NATIVE_PREFIX = {
    '5PC':{'original_native':'linear_torsion_native/original/5PC/cif-native-ephlzfns',
           'candidate_native':'linear_torsion_native/candidate/5PC/cif-native-1580_1g4'},
    'PDU':{'original_native':'linear_torsion_native/original/PDU/cif-native-jeqctu2o',
           'candidate_native':'linear_torsion_native/candidate/PDU/cif-native-6kr31hkw'}}
CEDAR44_CANDIDATE_SHA256 = {'PDU':'8a200874f62fdbe312e9bf622893714d4a80267b7647ace4476159bc69b5c426',
                           '5PC':'f75a0595fd9aa8b39fd77fffb2d6351f0d0716bfe4cc3c2539cd8dfdc56a99e1'}
CEDAR45_SHA256='9d3d5231bd929b45b16cffea07108a392bfbb90111baa57ba13cffd0c3bdc035'
CEDAR45_BUILD_SHA256='dd28c12591458c674141cccb58c8e2717cc046583816484b8d29059274af4147'
CEDAR45_WORKER_SHA256='a97a9e2094b322f060e4498224ebad8a6f957bc361281ba1dfd1c3f19930e2ea'
CEDAR45_NATIVE_PREFIX={'5PC':'linear_torsion_impact/5PC/cif-linear-torsion-impact-clgqjjr9',
                       'PDU':'linear_torsion_impact/PDU/cif-linear-torsion-impact-h0c2_u5h'}
CEDAR46_SHA256='4900b032e1e0fa2af30e7260bc0974511755afd97eb9643b24bf6f5ac58c3637'
CEDAR46_BUILD_SHA256='65ce32505f80abfe115184fdf1f8724e1d39cb2dd2844e47f8bfc2aa64c2d04e'
CEDAR46_WORKER_SHA256='d88fc60c8cb9f0c7a707f3a9f28f8bd6e843349d8c3ecd175eb71416fc458185'
CEDAR46_HELPER_SHA256={'impact_core.py':'ba0677dc0eb8ebf5324943393b2065f3c5c2d70eb681b356e9193017b1b057c4',
    'gradient_core.py':'a4d6571512313ae7ce8522668bd152ea806c5478803b74e296822bc313f275cc',
    'cache_core.py':'33cb1bf09f7ecf4752cd379bfa51c91d516addcc347e905e83b148f0a5e27181'}
CEDAR46_NATIVE_PREFIX={'5PC':'linear_torsion_impact/5PC/cif-linear-torsion-impact-j8vbc22s',
                       'PDU':'linear_torsion_impact/PDU/cif-linear-torsion-impact-lpbwbgcw'}
CEDAR47_SHA256='a7bbcac7868ecaba68c639d341bdc7a8ac69a53b9124c78a60896a64a4640461'
CEDAR47_BUILD_SHA256='618afc135dca4d4b10e5ecf10a83d4136bed6baea623cef39cbba2d8b7e73921'
CEDAR47_WORKER_SHA256='4850bc709c34f4ed887af269b8e62cd7aa2888a46395aa07e2e4b4d2e62ca72e'
CEDAR47_SOURCE_SHA256={'DP':'071486fd8113788b4d1125126fa8167804a7c953dd27ccfb68e273058d94aed7',
    'PDU':'ac4d8854e0154d6a694d59473a8b47859b370df0c068f3929b6f2b1e5cba26b4',
    '5PC':'c71018468c0817ef6398bb3ce690968f05d02b76a4fbba2f6094af3315f3cdf4'}
CEDAR48_SHA256='27836a06ebc51aa2fdbc0911d48ddafa921b6bb5cb9bc83133e494d84f76a08c'
CEDAR48_BUILD_SHA256='95f048475918acd433e18304be332824bebcfe9d2aba2889b642a3890408aaa8'
CEDAR48_WORKER_SHA256='8acfb6b6070d52d683a9bbb7c0712d3b27347471e93d857703df39872079e741'
CEDAR48_BACKEND_SHA256='219938312d5c9c8c0a3cc27b1a225ff9ecb71bec1c2128d39ebf70918f298f96'
CEDAR49_SHA256='da403d76e1e5070f782afce5ce825b4eb0b659b2dd6a138d7adbc13ce410b895'
CEDAR49_BUILD_SHA256='5b4dd47130d0ce6dd92af0456c6f2135989e65d78bf6a01ea7b4433d75b3f2bc'
CEDAR49_WORKER_SHA256='5c3795c0e77625e0743e20ddbedff66cf15f13f38313099b2546fe656d9b93f8'
CEDAR50_SHA256='8e62fcbb8040c8c348ce2d1f316091b73cdc9f301e50fc9ec5b6647a9a66b7d9'
CEDAR50_BUILD_SHA256='f7b09e98c34e1d140a103661a8edcc91b517ab3d773fec95181ff15b3d7fd1f2'
CEDAR50_WORKER_SHA256='3577659c40015d2e1906baece163360b217b9c11dbff8ed18b17ea48068cdc28'
CEDAR51_SHA256='ee2e07a200d3bdfe2789f0523bba5f74d6af78fd4279dd8e5012c4590cf9627d'
CEDAR51_BUILD_SHA256='1942d1e41d316eb508df6d14cc7c15b96c92ebb1e8a0b825c1fa960a1d70907e'
CEDAR51_WORKER_SHA256='a18d5d3835467e7572a2ad4a79a28fe456412e1d380c9aef7ae27f5e2f715d70'
CEDAR52_SHA256='21d97cf95df2b15fd0c989d7372e1c8538d58b9d152571e010a178b56f275acc'
CEDAR52_BUILD_SHA256='f0fc6c15852766d0a73a0b9f02d21e6b8b9cd685da5f737a7384cdc9648e47b3'
CEDAR52_WORKER_SHA256='2a30ca44562841004c68f25b979b9723740b54ba589649e5ccb1f1aa1f1c8158'
CEDAR41_SHA256 = '7d24e6db59fa814ccd93099d9676f569047147fcb8ab154e05c4980d16a94bd3'
CEDAR41_BUILD_SHA256 = '0b94d54d60f0153cc46a518507c36af947479da0275b6546a5f8ed50ea42d0aa'
CEDAR41_WORKER_SHA256 = '9af880ed950dfb66388fa7af40dadc7a4530b88b4553e0b88c0f95b284b430e8'
READYSET_OPTIONS_PARSER_SHA256 = 'e7bdf4ac2b9dea237f6c29b8015fa665834c435173c1d0662ed4d51b384e6dbd'
CEDAR40_SHA256 = '976fd33904b8e00d6953e85648ed855cf9106aa56f64ae8dbc9ef97cc32b3f87'
CEDAR40_BUILD_SHA256 = '1802b0da1a6b1e979ea8c55f0f500b7efe258adfd3ea7de75d38572d7a9ab465'
CEDAR40_WORKER_SHA256 = '207cb1e9f141a49fc070c15fb96a6f35ef6f5bc181f2b4e01bd44e3101d80b9a'
CEDAR38_MONOMER_SOURCES = {
    'mmtbx/monomer_library/server.py':'ee7c6d95d5d8ebf7fa055274935424914b53f18d92843045dd7a13ac0d029aaa',
    'mmtbx/monomer_library/cif_types.py':'4b2dbeae99a931510a2f96023b772f04d69c083a8719925c33c45d942f0da4fd',
}
CEDAR34_CHIRAL_SOURCES = {
    'elbow/utilities/Utilities.py':'74c6c8713e8c7f6aa30e6cea06e24fffa6399497c37e05dc5a33300f45199108',
    'elbow/chemistry/MoleculeClass.py':'fdc6ec851449c2cd1d947977209a92e9f691ebfe2aee5823cada361bc7e69e48',
    'elbow/chemistry/TopologyMixins.py':'701214ece8611674b766c4359041f7b3c32b4f55ea02e66207d496b0df5a21bc',
    'elbow/chemistry/ChiralClass.py':'6276fb3d92d71c4b2156b50d7e844f40c0747b8ede19d566214cfe8774ad49de',
}
ELBOW_SOURCE_SHA256 = {
    'elbow/utilities/Utilities.py':'74c6c8713e8c7f6aa30e6cea06e24fffa6399497c37e05dc5a33300f45199108',
    'elbow/utilities/optimisation_manager.py':'92c11aa41be2823726448e7c541dc8a2145c195593da98f4b50742b367adcadf',
    'elbow/command_line/builder.py':'7b2c0caf2f061d7fff65633da3add4e1b5176710ac2f7fee6c81a14c99789afd',
    'elbow/chemistry/any_chemical_format_reader.py':'17c4cc38484f8f5ddea90ae3d9a04e07c73ee18ccb722ad574c753bdb9b1cbd4',
}


def _source_view(members):
    prefix=''
    while True:
        header=json.loads(members['probe_receipt.json'])
        if header.get('delivery_prefix') not in {'30_Cedar','31_Cedar','32_Cedar','33_Cedar','34_Cedar','35_Cedar','36_Cedar','37_Cedar','38_Cedar','39_Cedar','40_Cedar','41_Cedar','42_Cedar','43_Cedar','44_Cedar','45_Cedar','46_Cedar','47_Cedar','48_Cedar','49_Cedar','50_Cedar','51_Cedar','52_Cedar'} or header.get('kind')!='cif-source-graph-numerical-recovery-probe':
            return members,prefix
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
        prefix+='inputs/review/'


def _read_cedar30_members(members):
    _verify_manifest(members,1185)
    current=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(current['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR30_BUILD_SHA256
            or current.get('kind')!='cif-source-graph-numerical-recovery-probe' or current.get('delivery_prefix')!='30_Cedar'
            or current.get('status')!='REVIEW' or current.get('analysis_completed') is not True
            or current.get('automatic_adoption') is not False or current.get('policy_authority')!='NARestraints'
            or any(current.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(current.get(k)!='NOT_RUN' for k in ['model_editing','model_optimization','native_execution','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry'])
            or current.get('dictionary_generation')!='REVIEW_REQUIRED'
            or current['prior_archive']['sha256']!=REVIEW_SHA256 or current['prior_archive']['verified_payloads']!=1173):
        raise ValueError('Require the intact reviewed Cedar 30 generation failure')
    source,_=_source_view(members);qualified,prior,rotation=_read_cedar29_members(source)
    candidates=current['candidates']
    if set(candidates)!={'DP'}:raise ValueError('Prior candidate scope changed')
    candidate=candidates['DP'];generation=candidate['generation']
    if (candidate!=json.loads(members[CEDAR30_RECOVERY_PREFIX+'/numerical_recovery_receipt.json'])
            or generation!=json.loads(members[CEDAR30_GENERATION_PREFIX+'/generation_receipt.json'])):
        raise ValueError('Prior generation receipt/result differ')
    for prefix,receipt in [(CEDAR30_RECOVERY_PREFIX,candidate),(CEDAR30_GENERATION_PREFIX,generation)]:
        for row in receipt['outputs']:
            if row.get('anchor')!='candidate_directory' or not _safe(row.get('path')):raise ValueError('Unsafe prior generation anchor')
            data=members[prefix+'/'+row['path']]
            if len(data)!=row['size'] or _sha(data)!=row['sha256']:raise ValueError('Prior generation artifact changed')
    if (candidate.get('status')!='REJECTED' or not candidate.get('source_preserved')
            or generation.get('status')!='FAILED' or generation['execution'].get('status')!='FAILED'
            or generation['execution'].get('returncode')!=1 or not generation.get('source_preserved') or not generation.get('frozen_source_preserved')
            or any(n.startswith('generation/') and n.endswith('/candidate.cif') for n in members)):
        raise ValueError('Prior failure phase or source preservation changed')
    original=members[CEDAR30_RECOVERY_PREFIX+'/original/source.cif']
    if original!=source[ROTATION_PREFIX+'/inputs/004_dictionary.cif']:raise ValueError('Prior DP source differs from frozen manager')
    graph=members[CEDAR30_RECOVERY_PREFIX+'/graph/source.cif']
    if (_sha(graph)!=CEDAR30_GRAPH_SHA256
            or graph!=members[CEDAR30_GENERATION_PREFIX+'/source.cif']):raise ValueError('Prior source graph export changed')
    log=members[CEDAR30_GENERATION_PREFIX+'/elbow.log'].decode()
    if "AttributeError: 'empty' object has no attribute 'pdbx_model_Cartn_x_ideal'" not in log:
        raise ValueError('Prior installed input-parser evidence differs')
    return qualified,prior,rotation


def _read_cedar31_members(members):
    _verify_manifest(members,1209)
    current=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(current['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR31_BUILD_SHA256
            or current.get('kind')!='cif-source-graph-numerical-recovery-probe' or current.get('delivery_prefix')!='31_Cedar'
            or current.get('status')!='REVIEW' or current.get('analysis_completed') is not True
            or current.get('automatic_adoption') is not False or current.get('policy_authority')!='NARestraints'
            or any(current.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(current.get(k)!='NOT_RUN' for k in ['model_editing','model_optimization','native_execution','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry'])
            or current.get('dictionary_generation')!='REVIEW_REQUIRED'
            or current['prior_archive']['sha256']!=CEDAR30_SHA256 or current['prior_archive']['verified_payloads']!=1185):
        raise ValueError('Require the intact reviewed Cedar 31 generation failures')
    nested={n.removeprefix('inputs/review/'):data for n,data in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar30_members(nested)
    source,_=_source_view(members)
    if set(current['candidates'])!=set(CEDAR31_CASES):raise ValueError('Prior independent candidate scope changed')
    for code,(prefix,generatedir,graph_sha) in CEDAR31_CASES.items():
        gp=prefix+'/generation/'+generatedir;c=current['candidates'][code];g=c['generation']
        if c!=json.loads(members[prefix+'/numerical_recovery_receipt.json']) or g!=json.loads(members[gp+'/generation_receipt.json']):
            raise ValueError('Prior independent generation receipt/result differ')
        missing=set()
        for pre,receipt in [(prefix,c),(gp,g)]:
            for row in receipt['outputs']:
                if row.get('anchor')!='candidate_directory' or not _safe(row.get('path')):raise ValueError('Unsafe prior generation artifact')
                name=pre+'/'+row['path']
                if name not in members and name in {gp+'/candidate.options.pickle',gp+'/candidate.pickle'}:
                    missing.add(name);continue
                if name not in members or len(members[name])!=row['size'] or _sha(members[name])!=row['sha256']:
                    raise ValueError('Prior independent generation artifact changed')
        expected_missing={gp+'/candidate.options.pickle',gp+'/candidate.pickle'} if code=='PDU' else set()
        if (missing!=expected_missing or c.get('status')!='REJECTED' or not c.get('source_preserved')
                or g.get('status')!='FAILED' or g['execution'].get('status')!='FAILED' or g['execution'].get('returncode')!=1
                or not g.get('source_preserved') or not g.get('frozen_source_preserved')
                or any(n.startswith(prefix+'/') and n.endswith('/candidate.cif') for n in members)):
            raise ValueError('Prior independent failure phase or source preservation differs')
        graph=members[prefix+'/graph/source.cif']
        if (_sha(graph)!=graph_sha or graph!=members[gp+'/source.cif']
                or graph!=members['graph_preview/'+code+'/source.cif']):raise ValueError('Prior independent graph export changed')
        original=members[prefix+'/original/source.cif'];log=members[gp+'/elbow.log'].decode()
        if code=='DP':
            if (original!=source[ROTATION_PREFIX+'/inputs/004_dictionary.cif']
                    or "AttributeError: 'empty' object has no attribute 'alt_atom_id'" not in log):
                raise ValueError('Prior DP source or input-parser evidence differs')
        else:
            control=json.loads(members['component_controls/PDU_control.json'])
            if (_sha(original)!=PDU_SOURCE_SHA256 or original!=members['component_controls/sources/PDU.cif']
                    or control!=current['component_controls']['PDU'] or control.get('graph_status')!='PASS'
                    or control.get('policy_status')!='PASS' or control.get('source_sha256')!=PDU_SOURCE_SHA256
                    or members[gp+'/candidate.elbow_opt.xyz']!=b''
                    or not all(marker in log for marker in ['38 atoms','39 bonds','3 chirals : R S R','geometry not converged',
                        "UnboundLocalError: cannot access local variable 'smc'"])):
                raise ValueError('Prior PDU source or optimizer-restart evidence differs')
    return qualified,prior,rotation


def _read_cedar32_members(members):
    _verify_manifest(members,1229)
    r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR32_BUILD_SHA256
            or r.get('delivery_prefix')!='32_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True
            or r.get('native_execution')!='READ_ONLY_INPUT_CHECKS' or r.get('requested_action')!='NATIVE_READ_ONLY_CONTRACT'
            or r.get('automatic_adoption') is not False or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry'])
            or r['prior_archive']['sha256']!=CEDAR31_SHA256 or r['prior_archive']['verified_payloads']!=1209):
        raise ValueError('Require the exact returned Cedar 32 read-only contract')
    nested={n.removeprefix('inputs/review/'):v for n,v in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar31_members(nested)
    c=r['installed_elbow_contract'];directory=c['source_directory']
    if directory.get('anchor')!='probe_directory' or not _safe(directory.get('path')):raise ValueError('Unsafe installed contract directory')
    prefix=directory['path'];stored=json.loads(members[prefix+'/source_capture.json'])
    if stored!={k:v for k,v in c.items() if k!='source_directory'}:raise ValueError('Installed source capture receipt differs')
    if (c.get('status')!='CAPTURED_NOT_QUALIFIED' or c.get('captured_code_execution')!='NOT_RUN'
            or c.get('installed_phenix_edits')!='NOT_RUN' or c.get('pickle_loading')!='NOT_RUN'
            or len(c['sources'])!=4 or {row['snapshot']['path'] for row in c['sources']}!=set(ELBOW_SOURCE_SHA256)):
        raise ValueError('Installed source capture scope differs')
    for row in c['sources']:
        name=row['snapshot']['path']
        if (row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='contract_directory'
                or row['path']!='lib/python3.11/site-packages/'+name or row['sha256']!=ELBOW_SOURCE_SHA256[name]):
            raise ValueError('Installed eLBOW source identity differs')
        data=members[prefix+'/'+name]
        if len(data)!=row['size'] or _sha(data)!=row['sha256']:raise ValueError('Captured eLBOW source changed')
    if set(r['native_input_checks'])!={'DP','PDU'}:raise ValueError('Read-only input scope differs')
    for code,check in r['native_input_checks'].items():
        directory=check['directory'];pre=directory['path']
        if directory.get('anchor')!='probe_directory' or not _safe(pre):raise ValueError('Unsafe read-only input directory')
        if json.loads(members[pre+'/input_receipt.json'])!={k:v for k,v in check.items() if k!='directory'}:raise ValueError('Read-only receipt differs')
        if (any(check.get(k) is not True for k in ['source_preserved','frozen_source_preserved','executable_preserved'])
                or check.get('dictionary_generation')!='NOT_RUN' or check.get('model_optimization')!='NOT_RUN'
                or check.get('automatic_adoption') is not False):raise ValueError('Read-only input integrity/scope differs')
        for row in check['outputs']:
            if row.get('anchor')!='contract_directory' or not _safe(row.get('path')):raise ValueError('Unsafe input-check output')
            data=members[pre+'/'+row['path']]
            if len(data)!=row['size'] or _sha(data)!=row['sha256']:raise ValueError('Read-only input output changed')
        if members[pre+'/source.cif']!=members['graph_preview/'+code+'/source.cif']:raise ValueError('Read-only graph input differs')
        log=members[pre+'/elbow_read_only.log'].decode()
        expected=('REVIEW',1) if code=='DP' else ('PARSER_READ_ONLY_PASS',0)
        if (check['status'],check['execution']['returncode'])!=expected:raise ValueError('Read-only input outcome differs')
        if code=='DP' and "has no attribute 'pdbx_aromatic_flag'" not in log:raise ValueError('DP dialect mismatch evidence differs')
    return qualified,prior,rotation


def _returned_outputs(members,prefix,rows,anchor,*,excluded_pickles=False):
    for row in rows:
        if row.get('anchor')!=anchor or not _safe(row.get('path')):raise ValueError('Unsafe returned artifact reference')
        name=prefix+'/'+row['path']
        if Path(name).suffix in {'.pickle','.pkl'}:
            if not excluded_pickles or name in members:raise ValueError('Serialized molecule output must stay excluded')
            continue
        if len(members[name])!=row['size'] or _sha(members[name])!=row['sha256']:
            raise ValueError('Returned artifact integrity differs')


def _read_cedar33_members(members):
    _verify_manifest(members,1288);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR33_BUILD_SHA256
            or r.get('delivery_prefix')!='33_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True
            or r.get('requested_action')!='SINGLE_BLOCK_NUMERICAL_GENERATION'
            or r.get('native_execution')!='READ_ONLY_INPUT_CHECKS_AND_NUMERICAL_GENERATION'
            or r.get('dictionary_generation')!='REVIEW_REQUIRED' or r.get('automatic_adoption') is not False
            or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['model_editing','model_optimization','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry'])
            or r['prior_archive']['sha256']!=CEDAR32_SHA256 or r['prior_archive']['verified_payloads']!=1229
            or set(r['candidates'])!=set(CEDAR33_CASES) or set(r['native_input_checks'])!=set(CEDAR33_CASES)
            or set(r['single_block_options'])!=set(CEDAR33_CASES)):
        raise ValueError('Require the exact returned Cedar 33 bounded trial')
    nested={n.removeprefix('inputs/review/'):v for n,v in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar32_members(nested)
    parent=json.loads(nested['probe_receipt.json'])
    if r['installed_elbow_contract']!=parent['installed_elbow_contract']:
        raise ValueError('Returned installed source contract differs')
    prefix=r['installed_elbow_contract']['source_directory']['path']
    for name in [*ELBOW_SOURCE_SHA256,'source_capture.json']:
        if members[prefix+'/'+name]!=nested[prefix+'/'+name]:raise ValueError('Returned source capture bytes differ')
    if (r['single_block_control'].get('steps')!=180 or r['single_block_control'].get('source_contract_archive')!=CEDAR32_SHA256
            or r['single_block_control'].get('tolerance')!='UNCHANGED'):
        raise ValueError('Returned explicit block control differs')
    original_view,_=_source_view(members)
    for code,(pre,generatedir,consumer_sha) in CEDAR33_CASES.items():
        check=r['native_input_checks'][code];directory=check['directory']
        if directory.get('anchor')!='probe_directory' or not _safe(directory.get('path')):raise ValueError('Unsafe input-check directory')
        cp=directory['path']
        if (check.get('status')!='PARSER_READ_ONLY_PASS' or check['execution'].get('returncode')!=0
                or check.get('dictionary_generation')!='NOT_RUN' or check.get('model_optimization')!='NOT_RUN'
                or check.get('automatic_adoption') is not False
                or any(check.get(k) is not True for k in ['source_preserved','frozen_source_preserved','executable_preserved'])
                or json.loads(members[cp+'/input_receipt.json'])!={k:v for k,v in check.items() if k!='directory'}):
            raise ValueError('Returned read-only input evidence differs')
        _returned_outputs(members,cp,check['outputs'],'contract_directory')
        consumer=members['consumer_preview/'+code+'/source.cif']
        if (_sha(consumer)!=consumer_sha or consumer!=members[cp+'/source.cif'] or consumer!=members[pre+'/consumer/source.cif']):
            raise ValueError('Returned consumer input differs')
        options=r['single_block_options'][code];op=options['directory']
        if op.get('anchor')!='probe_directory' or not _safe(op.get('path')):raise ValueError('Unsafe options directory')
        od=op['path'];row=options['source']
        if (options.get('status')!='SINGLE_BLOCK_OPTIONS_PASS' or options.get('steps')!=180 or options.get('effective_blocks')!=1
                or options.get('tolerance') is not False or options.get('optimization_execution')!='NOT_RUN'
                or options.get('captured_code_execution')!='NOT_RUN' or options.get('convergence_claimed') is not False
                or row.get('anchor')!='phenix_installation' or row.get('path')!='lib/python3.11/site-packages/elbow/utilities/options_parser.py'
                or row['sha256']!=CEDAR33_OPTIONS_SHA256 or _sha(members[od+'/options_parser.py.txt'])!=row['sha256']
                or len(members[od+'/options_parser.py.txt'])!=row['size']
                or json.loads(members[od+'/options_receipt.json'])!={k:v for k,v in options.items() if k!='directory'}):
            raise ValueError('Returned single-block option proof differs')
        parsed=json.loads(members[od+'/options_result.json'])
        if parsed['steps']!=180 or parsed['macro_override']!=options['macro_override'] or parsed['tolerance'] is not False or parsed['module_sha256']!=row['sha256']:
            raise ValueError('Actual installed option-parser evidence differs')
        c=r['candidates'][code];g=c['generation'];gp=pre+'/generation/'+generatedir
        if (c!=json.loads(members[pre+'/numerical_recovery_receipt.json'])
                or g!=json.loads(members[gp+'/generation_receipt.json'])
                or c.get('source_preserved') is not True or g.get('source_preserved') is not True
                or g.get('frozen_source_preserved') is not True or c.get('automatic_adoption') is not False
                or g.get('optimization_control',{}).get('single_block_steps')!=180):
            raise ValueError('Returned numerical candidate receipt differs')
        for prefix,rows in [(pre,c['outputs']),(gp,g['outputs'])]:
            _returned_outputs(members,prefix,rows,'candidate_directory',excluded_pickles=True)
        original=(original_view[ROTATION_PREFIX+'/inputs/004_dictionary.cif'] if code=='DP' else members['component_controls/sources/PDU.cif'])
        if (members[pre+'/original/source.cif']!=original or _sha(original)!=c['source_sha256']
                or len(original)!=c['source_size'] or members[pre+'/graph/source.cif']!=members['graph_preview/'+code+'/source.cif']
                or members[gp+'/source.cif']!=consumer):raise ValueError('Returned source/graph/consumer lineage differs')
        log=members[gp+'/elbow.log'].decode()
        if code=='DP':
            if (c.get('status')!='REJECTED' or g['execution'].get('status')!='FAILED' or g['execution'].get('returncode')!=1
                    or any(t not in log for t in ['Chiralise','ChiralClass.py','assert len(atoms) in [4,5]','AssertionError'])
                    or c.get('candidate') is not None or gp+'/candidate.cif' in members):
                raise ValueError('DP preparatory chirality failure evidence differs')
        else:
            if (c.get('status')!='CANDIDATE_REVIEW' or g['execution'].get('status')!='COMPLETED' or g['execution'].get('returncode')!=0
                    or g.get('optimization_stopping',{}).get('status')!='NOT_CONVERGED_REPORTED'
                    or 'geometry not converged' not in log or _sha(members[gp+'/candidate.cif'])!=CEDAR33_PDU_CANDIDATE_SHA256):
                raise ValueError('PDU nonconverged candidate evidence differs')
    return qualified,prior,rotation


def _read_cedar34_members(members):
    _verify_manifest(members,1320);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR34_BUILD_SHA256
            or r.get('delivery_prefix')!='34_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True
            or r.get('requested_action')!='READ_ONLY_STEREOCHEMISTRY_AUDIT'
            or r.get('native_execution')!='INSTALLED_READER_CHIRALITY_CONTROLS' or r.get('automatic_adoption') is not False
            or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry'])
            or r['prior_archive']['sha256']!=CEDAR33_SHA256 or r['prior_archive']['verified_payloads']!=1288
            or set(r['installed_chirality_controls'])!={'DP','PDU'}):
        raise ValueError('Require the exact returned Cedar 34 stereo controls')
    nested={n.removeprefix('inputs/review/'):v for n,v in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar33_members(nested)
    for code,control in r['installed_chirality_controls'].items():
        directory=control['directory']
        if directory.get('anchor')!='probe_directory' or not _safe(directory.get('path')):raise ValueError('Unsafe returned stereo directory')
        pre=directory['path'];result=control['result']
        if (json.loads(members[pre+'/chirality_receipt.json'])!={k:v for k,v in control.items() if k!='directory'}
                or result!=json.loads(members[pre+'/chirality_result.json'])
                or control.get('constructor_scope')!='READER_CHIRALS_TRUE_NOT_FULL_BUILDER_REPLAY'
                or control.get('source_preserved') is not True or control.get('installed_sources_preserved') is not True
                or any(control.get(k)!='NOT_RUN' for k in ['dictionary_generation','installed_phenix_edits','captured_code_execution','pickle_loading'])
                or control.get('automatic_adoption') is not False or control['declared_marker_conflicts']):
            raise ValueError('Returned stereo receipt or scope differs')
        if (len(control['sources'])!=4 or {row['snapshot']['path'] for row in control['sources']}!={n+'.txt' for n in CEDAR34_CHIRAL_SOURCES}):
            raise ValueError('Returned chirality source scope differs')
        for row in control['sources']:
            name=row['snapshot']['path'].removesuffix('.txt')
            if (row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='chirality_directory'
                    or row['path']!='lib/python3.11/site-packages/'+name or row['sha256']!=CEDAR34_CHIRAL_SOURCES[name]
                    or _sha(members[pre+'/'+name+'.txt'])!=row['sha256'] or len(members[pre+'/'+name+'.txt'])!=row['size']):
                raise ValueError('Returned installed chirality source differs')
        if _sha(members[pre+'/chirality_worker.py'])!=CEDAR34_WORKER_SHA256:raise ValueError('Returned constructor worker differs')
        consumer=members['consumer_preview/'+code+'/source.cif']
        if consumer!=nested['consumer_preview/'+code+'/source.cif'] or consumer!=members[pre+'/source.cif']:
            raise ValueError('Returned stereo consumer input differs')
        inventory=r['source_stereo_inventories'][code]
        if control['source_inventory']!=inventory or inventory['source_sha256']!=_sha(consumer):raise ValueError('Returned stereo source inventory differs')
        observed={row['atom']:row['native_chiral_marker'] for row in result['reader_atoms']}
        if len(observed)!=len(result['reader_atoms']) or set(observed)!=set(inventory['atoms']):raise ValueError('Returned stereo atom inventory differs')
        if code=='DP':
            if (control['status']!='REVIEW' or len(observed)!=35 or set(control['unknown_inputs_marked_chiral'])!=set(observed)
                    or any(v!='?' for v in observed.values()) or result['constructor_probe']['status']!='EXCEPTION'
                    or result['constructor_probe']['exception_type']!='AssertionError'
                    or 'assert len(atoms) in [4,5]' not in result['constructor_probe']['traceback']):
                raise ValueError('Returned DP unknown-marker constructor evidence differs')
        else:
            if (control['status']!='READER_MARKERS_PASS' or control['unknown_inputs_marked_chiral'] or len(observed)!=38
                    or result['constructor_probe']!={'status':'COMPLETED','atom_count':38}
                    or any((observed[n]!=a['declared_stereo'] if a['declared_stereo'] in {'R','S'} else bool(observed[n]))
                           for n,a in inventory['atoms'].items())):
                raise ValueError('Returned PDU source marker/control evidence differs')
    for code in ['DP','PDU']:
        if r['saved_optimizer_trajectories'][code]!=json.loads(members['stereochemistry/'+code+'_trajectory.json']):
            raise ValueError('Returned saved trajectory summary differs')
    if r['saved_candidate_stereochemistry']['PDU']!=json.loads(members['stereochemistry/PDU_candidate.json']):
        raise ValueError('Returned saved candidate stereo summary differs')
    # Legacy optimization_execution=NOT_RUN did not instrument the constructor's
    # internal ChiralClass.Optimise calls. Never use it as no-optimization proof.
    return qualified,prior,rotation


def _read_cedar35_members(members):
    _verify_manifest(members,1327);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR35_BUILD_SHA256
            or r.get('delivery_prefix')!='35_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not False
            or r.get('requested_action')!='SOURCE_DIALECT_READER_AUDIT'
            or r.get('error')!='Output parent cannot traverse a symlink'
            or r.get('automatic_adoption') is not False or r.get('policy_authority')!='NARestraints'
            or r.get('consumer_preparations')!={}
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['native_execution','dictionary_generation','model_editing','model_optimization',
                'native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits',
                'readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR34_SHA256 or r['prior_archive']['verified_payloads']!=1320):
        raise ValueError('Require the exact returned Cedar 35 pre-native portability failure')
    added={'manifest.json','probe_receipt.json','numerical_recovery_plan.json','component_controls/PDU_control.json',
           'component_controls/sources/PDU.cif','graph_preview/DP/source.cif','graph_preview/PDU/source.cif'}
    if {n for n in members if not n.startswith('inputs/review/')}!=added:
        raise ValueError('Returned preflight contains unexpected outputs')
    nested,_=_source_reader_evidence(members);parent=json.loads(nested['probe_receipt.json'])
    qualified,prior,rotation=_read_cedar34_members(nested)
    for key in ['graph_preparations','component_controls','source_plan','prior_rotation_evidence_recomputed']:
        if r[key]!=parent[key]:raise ValueError('Returned preflight changed prior preparation or policy evidence')
    for name in added-{'manifest.json','probe_receipt.json'}:
        if members[name]!=nested[name]:raise ValueError('Returned preflight input or preparation differs')
    return qualified,prior,rotation


def _read_cedar36_members(members):
    _verify_manifest(members,1355);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR36_BUILD_SHA256
            or r.get('delivery_prefix')!='36_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True
            or r.get('requested_action')!='SOURCE_DIALECT_READER_AUDIT' or r.get('native_execution')!='SOURCE_READER_DIALECT_CONTROLS'
            or r.get('automatic_adoption') is not False or r.get('policy_authority')!='NARestraints'
            or set(r['source_reader_audits'])!={'DP','PDU'}
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR35_SHA256 or r['prior_archive']['verified_payloads']!=1327):
        raise ValueError('Require the exact returned Cedar 36 source-reader controls')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar35_members(nested);old,_=_source_reader_evidence(nested);previous=json.loads(old['probe_receipt.json'])
    for key in ['saved_optimizer_trajectories','saved_candidate_stereochemistry']:
        if r[key]!=previous[key]:raise ValueError('Returned source-reader action changed saved stereo evidence')
    for code,row in r['source_reader_audits'].items():
        ref=row['directory']
        if ref.get('anchor')!='probe_directory' or not _safe(ref.get('path')):raise ValueError('Unsafe returned reader directory')
        pre=ref['path'];result=row['result'];consumer=members['consumer_preview/'+code+'/source.cif']
        if (json.loads(members[pre+'/reader_receipt.json'])!={k:v for k,v in row.items() if k!='directory'}
                or result!=json.loads(members[pre+'/reader_result.json']) or result.get('execution')!='COMPLETED'
                or _sha(members[pre+'/reader_worker.py'])!=CEDAR36_WORKER_SHA256
                or consumer!=members[pre+'/source.cif'] or _sha(consumer)!=CEDAR36_CONSUMER_SHA256[code]
                or row.get('policy_id')!='cif-installed-source-reader-inventory-v1'
                or row['source_sha256']!=_sha(consumer) or row.get('source_preserved') is not True
                or row.get('installed_sources_preserved') is not True or row.get('automatic_adoption') is not False
                or any(row.get(k)!='NOT_RUN' for k in ['dictionary_generation','independent_absolute_cip_validation',
                    'signed_stereo_native_qualification','installed_phenix_edits','captured_code_execution','pickle_loading'])
                or any(row.get(k)!='NOT_REQUESTED' for k in ['chiral_constructor','whole_molecule_optimization'])
                or row.get('parser_internal_operations')!='NOT_INSTRUMENTED'
                or row.get('declared_charge_control_requested') is not None):
            raise ValueError('Returned reader input, worker, receipt or execution scope differs')
        if len(row['sources'])!=2 or {s['snapshot']['path'] for s in row['sources']}!={n+'.txt' for n in CEDAR36_READER_SOURCES}:
            raise ValueError('Returned reader source scope differs')
        for source in row['sources']:
            name=source['snapshot']['path'].removesuffix('.txt');data=members[pre+'/'+name+'.txt']
            if (source.get('anchor')!='phenix_installation' or source['snapshot'].get('anchor')!='reader_directory'
                    or source['path']!='lib/python3.11/site-packages/'+name or source['sha256']!=CEDAR36_READER_SOURCES[name]
                    or _sha(data)!=source['sha256'] or len(data)!=source['size']):
                raise ValueError('Returned reader source snapshot differs')
        expected={k:True for k in ['reader_route','atom_identities','atom_elements','atom_charge_values','source_coordinates','declared_bond_orders']}
        if code=='DP':expected.update(atom_charge_values=False,declared_bond_orders=False)
        if row['checks']!=expected or row['status']!=('REVIEW' if code=='DP' else 'READER_ROUTE_AND_INVENTORY_PASS'):
            raise ValueError('Returned raw reader findings differ')
    return qualified,prior,rotation


def _read_cedar37_members(members):
    _verify_manifest(members,1387);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR37_BUILD_SHA256
            or r.get('delivery_prefix')!='37_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True
            or r.get('requested_action')!='SOURCE_DIALECT_DECLARED_CHARGE_CONTROL' or r.get('native_execution')!='SOURCE_READER_AND_DECLARED_CHARGE_CONTROLS'
            or r.get('automatic_adoption') is not False or r.get('policy_authority')!='NARestraints'
            or set(r['source_reader_audits'])!={'DP','PDU'}
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR36_SHA256 or r['prior_archive']['verified_payloads']!=1355):
        raise ValueError('Require the exact returned Cedar 37 source-reader and charge controls')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar36_members(nested);old,_=_source_reader_evidence(nested);previous=json.loads(old['probe_receipt.json'])
    for key in ['saved_optimizer_trajectories','saved_candidate_stereochemistry']:
        if r[key]!=previous[key]:raise ValueError('Returned source-reader action changed saved stereo evidence')
    sources_expected={**CEDAR36_READER_SOURCES,**{k:CEDAR34_CHIRAL_SOURCES[k] for k in ['elbow/utilities/Utilities.py','elbow/chemistry/MoleculeClass.py']}}
    if r.get('declared_charge_control_requested') is not True:raise ValueError('Missing returned declared-charge action')
    for code,row in r['source_reader_audits'].items():
        ref=row['directory']
        if ref.get('anchor')!='probe_directory' or not _safe(ref.get('path')):raise ValueError('Unsafe returned reader directory')
        pre=ref['path'];result=row['result'];consumer=members['consumer_preview/'+code+'/source.cif']
        if (json.loads(members[pre+'/reader_receipt.json'])!={k:v for k,v in row.items() if k!='directory'}
                or result!=json.loads(members[pre+'/reader_result.json']) or result.get('execution')!='COMPLETED'
                or _sha(members[pre+'/reader_worker.py'])!=CEDAR37_WORKER_SHA256
                or consumer!=members[pre+'/source.cif'] or _sha(consumer)!=CEDAR37_CONSUMER_SHA256[code]
                or row.get('policy_id')!='cif-installed-source-reader-inventory-v1'
                or row['source_sha256']!=_sha(consumer) or row.get('source_preserved') is not True
                or row.get('installed_sources_preserved') is not True or row.get('automatic_adoption') is not False
                or any(row.get(k)!='NOT_RUN' for k in ['dictionary_generation','independent_absolute_cip_validation',
                    'signed_stereo_native_qualification','installed_phenix_edits','captured_code_execution','pickle_loading'])
                or any(row.get(k)!='NOT_REQUESTED' for k in ['chiral_constructor','whole_molecule_optimization'])
                or row.get('parser_internal_operations')!='NOT_INSTRUMENTED'
                or row.get('declared_charge_control_requested') is not True):
            raise ValueError('Returned reader input, worker, receipt or execution scope differs')
        if len(row['sources'])!=4 or {s['snapshot']['path'] for s in row['sources']}!={n+'.txt' for n in sources_expected}:
            raise ValueError('Returned reader source scope differs')
        for source in row['sources']:
            name=source['snapshot']['path'].removesuffix('.txt');data=members[pre+'/'+name+'.txt']
            if (source.get('anchor')!='phenix_installation' or source['snapshot'].get('anchor')!='reader_directory'
                    or source['path']!='lib/python3.11/site-packages/'+name or source['sha256']!=sources_expected[name]
                    or _sha(data)!=source['sha256'] or len(data)!=source['size']):
                raise ValueError('Returned reader source snapshot differs')
        expected={k:True for k in ['reader_route','atom_identities','atom_elements','atom_charge_values','source_coordinates','declared_bond_orders']}
        if code=='DP':expected.update(atom_charge_values=False)
        if row['checks']!=expected or row['status']!=('REVIEW' if code=='DP' else 'READER_ROUTE_AND_INVENTORY_PASS'):
            raise ValueError('Returned raw reader findings differ')
        control=row['declared_charge_control'];qualification=row['declared_charge_qualification']
        before,after=control['before'],control['after']
        wanted={**{k:True for k in expected},'molecule_total_charge':True,'other_native_fields_preserved':True}
        if (control!=result.get('declared_charge_control') or control.get('status')!='DECLARED_CHARGE_CONTROL_PASS'
                or control.get('policy_id')!='cif-explicit-source-formal-charge-control-v1'
                or control.get('action')!=('POPULATED_FROM_EXPLICIT_SOURCE' if code=='DP' else 'ALREADY_PRESERVED')
                or control.get('source_total_charge')!=(-2 if code=='DP' else 0)
                or control.get('changed_atoms')!=(['OP2','OP3'] if code=='DP' else [])
                or before['atoms']!=result['atoms'] or before['bonds']!=result['bonds']
                or before['bonds']!=after['bonds']
                or [{k:v for k,v in a.items() if k!='native_atom_charge'} for a in before['atoms']]!=
                   [{k:v for k,v in a.items() if k!='native_atom_charge'} for a in after['atoms']]
                or after['molecule_charge']!=control['source_total_charge']
                or qualification.get('status')!='DECLARED_CHARGE_CONTROL_PASS' or qualification.get('checks')!=wanted
                or qualification.get('raw_reader_checks_retained') is not True or qualification.get('scientific_approval')!='NOT_RUN'
                or control.get('automatic_adoption') is not False
                or any(control.get(k)!='NOT_RUN' for k in ['dictionary_generation','independent_absolute_cip_validation'])
                or control.get('optimization')!='NOT_REQUESTED'):
            raise ValueError('Returned declared-charge control or its preserved raw inventory differs')
    return qualified,prior,rotation


def _check_captured_triple_case(members,code,label,row):
    ref=row['directory']
    if ref.get('anchor')!='triple_control_directory' or not _safe(ref.get('path')):raise ValueError('Unsafe returned triple-case directory')
    pre='triple_controls/'+ref['path'];native=row['interpretation'];report=native.get('native_validation') or {}
    if (native!=json.loads(members[pre+'/native_receipt.json']) or report!=json.loads(members[pre+'/native_validation.json'])
            or _sha(members[pre+'/native_worker.py'])!=CEDAR38_NATIVE_WORKER_SHA256
            or any(native.get(k) is not True for k in ['source_preserved','frozen_inputs_preserved'])
            or native.get('automatic_adoption') is not False
            or any(native.get(k)!='NOT_RUN' for k in ['optimization','model_editing','readyset_retry','scientific_approval'])
            or report.get('restraint_policy',{}).get('secondary_structure_enabled') is not False):
        raise ValueError('Returned native triple-case scope, worker or receipt differs')
    from collections import Counter
    roles={'model':1,'phil':1,**({'dictionary':1} if label=='saved_candidate' else {})}
    if Counter(r['role'] for r in native['inputs'])!=roles:raise ValueError('Returned isolated native input roles differ')
    _returned_outputs(members,pre,native['inputs']+native['outputs'],'native_directory')
    for r in native['inputs']:
        if r['role']=='model' and members[pre+'/'+r['path']]!=members['triple_controls/models/'+code+'/source_seed.pdb']:raise ValueError('Returned native control model differs')
        if r['role']=='phil' and members[pre+'/'+r['path']]!=members['triple_controls/policies/'+code+'/isolated_component.phil']:raise ValueError('Returned native control policy differs')
        if r['role']=='dictionary' and r['sha256']!=CEDAR33_PDU_CANDIDATE_SHA256:raise ValueError('Returned saved dictionary differs')
    if label=='installed_lookup':
        if (native.get('status')!='FAILED' or report.get('status')!='FAILED' or native['execution'].get('returncode')!=2
                or native['execution'].get('status')!='FAILED' or row['triple_screen'].get('status')!='NOT_RUN'
                or native.get('dictionary_source_policy')!='INSTALLED_LIBRARY_ONLY'
                or 'unknown nonbonded energy type symbols: '+('38' if code=='PDU' else '39') not in native.get('error','')):
            raise ValueError('Returned missing monomer evidence differs')
    elif (native.get('status')!='REVIEW' or report.get('status')!='REVIEW' or native['execution'].get('returncode')!=0
            or native['execution'].get('status')!='COMPLETED' or row['triple_screen'].get('status')!='REVIEW'
            or row['triple_screen'].get('target_screen')!='PASS' or row['triple_screen'].get('coordinate_screen')!='PASS'
            or len(row['triple_screen'].get('linear_axis_torsions',[]))!=6):
        raise ValueError('Returned active PDU triple/torsion findings differ')


def _read_cedar38_members(members):
    _verify_manifest(members,1446);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR38_BUILD_SHA256
            or r.get('delivery_prefix')!='38_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='INSTALLED_TRIPLE_BOND_AUDIT' or r.get('native_execution')!='INSTALLED_COMPONENT_AND_TRIPLE_PROXY_CONTROLS'
            or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR37_SHA256 or r['prior_archive']['verified_payloads']!=1387):
        raise ValueError('Require the exact returned Cedar 38 isolated monomer/triple evidence')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar37_members(nested)
    audit=r['triple_bond_audit']
    if (audit!=json.loads(members['triple_controls/triple_control_receipt.json']) or set(audit['cases'])!={'PDU','5PC'}
            or any(audit.get(k)!='NOT_RUN' for k in ['model_optimization','dictionary_generation','readyset','refinement','scientific_approval'])
            or audit.get('automatic_adoption') is not False):raise ValueError('Returned triple-audit scope or receipt differs')
    for code,case in audit['cases'].items():
        pre='triple_controls/resources/'+code;resource=case['installed_resource']
        if (resource!=json.loads(members[pre+'/component_receipt.json']) or resource['result']!=json.loads(members[pre+'/component_result.json'])
                or _sha(members[pre+'/component_worker.py'])!=CEDAR38_RESOURCE_WORKER_SHA256
                or resource.get('installed_sources_preserved') is not True
                or resource['result'].get('status')!='UNSUPPORTED' or resource['result'].get('error')!='Missing requested installed component'
                or resource['result'].get('resource') is not None
                or set(case['native'])!=({'installed_lookup','saved_candidate'} if code=='PDU' else {'installed_lookup'})):
            raise ValueError('Returned absent monomer resource or case scope differs')
        if len(resource['sources'])!=2 or {s['snapshot']['path'] for s in resource['sources']}!={n+'.txt' for n in CEDAR38_MONOMER_SOURCES}:
            raise ValueError('Returned monomer API scope differs')
        for source in resource['sources']:
            name=source['snapshot']['path'].removesuffix('.txt');data=members[pre+'/'+source['snapshot']['path']]
            if (name not in CEDAR38_MONOMER_SOURCES or source.get('anchor')!='phenix_installation'
                    or source['snapshot'].get('anchor')!='component_directory' or source['path']!='lib/python3.11/site-packages/'+name
                    or source['sha256']!=CEDAR38_MONOMER_SOURCES[name] or _sha(data)!=source['sha256'] or len(data)!=source['size']):
                raise ValueError('Returned selected monomer API differs')
        for label,row in case['native'].items():_check_captured_triple_case(members,code,label,row)
    return qualified,prior,rotation


def _check_source_snapshots(members,prefix,rows,anchor):
    for row in rows:
        if row.get('anchor')!='phenix_installation' or not _safe(row.get('path')):
            raise ValueError('Unsafe captured installation source')
        _returned_outputs(members,prefix,[{**row,**row['snapshot']}],anchor)


def _check_catalogue_return(members,r):
    cat=r['installed_source_catalogue'];pre='installed_source_catalogue'
    if (cat!=json.loads(members[pre+'/source_catalogue_receipt.json'])
            or cat['native_resources']!=json.loads(members[pre+'/source_catalogue_result.json'])
            or _sha(members[pre+'/source_catalogue_worker.py'])!=CEDAR39_CATALOGUE_WORKER_SHA256
            or cat.get('policy_id')!='cif-installed-monomer-ccd-source-catalogue-v1'
            or cat.get('automatic_adoption') is not False or cat.get('route_helpers')!='STATIC_SOURCE_CAPTURE_ONLY_NOT_EXECUTED'
            or any(cat.get(k)!='NOT_RUN' for k in ['readyset_execution','dictionary_generation','optimization','mapped_smiles_graph_comparison'])
            or set(cat['components'])!={'PDU','5PC'} or set(r['installed_ccd_reader_audits'])!={'PDU','5PC'}):
        raise ValueError('Returned installed source scope or worker differs')
    resources=cat['native_resources']
    if (set(resources['lookups'])!={'PDU','5PC'} or set(resources['canonical_controls'])!={'DG','DC'}
            or resources.get('automatic_adoption') is not False
            or any(resources.get(k)!='NOT_RUN' for k in ['readyset','dictionary_generation','optimization'])
            or any(set(v)!={'direct','wrapped'} or any(x.get('status')!='MISSING' for x in v.values()) for v in resources['lookups'].values())
            or any(v.get('status')!='RECORDED' for v in resources['canonical_controls'].values())):
        raise ValueError('Returned missing and canonical monomer context differs')
    _check_source_snapshots(members,pre,cat['sources']+[cat['readyset_dispatcher']],'catalogue_directory')
    for code,case in cat['components'].items():
        resource=case['resource'];comp=case['comparison'];row=r['installed_ccd_reader_audits'][code]
        _check_source_snapshots(members,pre,[resource],'catalogue_directory')
        directory=row['directory']
        if directory.get('anchor')!='probe_directory' or directory.get('path')!='installed_ccd_readers/'+code:
            raise ValueError('Unsafe returned installed CCD reader directory')
        readerpre=directory['path']
        if (case.get('status')!='RECORDED' or resource['sha256']!=CEDAR39_CCD_SHA256[code]
                or comp.get('chemical_declarations')!='EXACT_DECLARATIONS' or comp.get('descriptor_text_comparison')!='TEXT_IDENTICAL'
                or comp.get('mapped_smiles_graph_comparison')!='NOT_RUN' or comp.get('dictionary_parameterization')!='UNASSESSED'
                or {k:v for k,v in row.items() if k!='directory'}!=json.loads(members[readerpre+'/reader_receipt.json'])
                or row['result']!=json.loads(members[readerpre+'/reader_result.json'])
                or _sha(members[readerpre+'/reader_worker.py'])!=CEDAR37_WORKER_SHA256
                or members[readerpre+'/source.cif']!=members[pre+'/'+resource['snapshot']['path']]
                or row.get('source_sha256')!=resource['sha256'] or row.get('automatic_adoption') is not False
                or row.get('status')!='READER_ROUTE_AND_INVENTORY_PASS' or row.get('chiral_constructor')!='NOT_REQUESTED'
                or row.get('expected_dialect')!='CHEMICAL_COMPONENTS_CIF'
                or any(row.get(k)!='NOT_RUN' for k in ['dictionary_generation','installed_phenix_edits','captured_code_execution','pickle_loading'])
                or set(row['checks'])!={'atom_identities','atom_elements','atom_charge_values','source_coordinates','declared_bond_orders','reader_route'}
                or any(v is not True for v in row['checks'].values())):
            raise ValueError('Returned installed CCD declaration or reader evidence differs')
        _check_source_snapshots(members,readerpre,row['sources'],'reader_directory')


def _read_cedar39_members(members):
    _verify_manifest(members,1486);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR39_BUILD_SHA256
            or r.get('delivery_prefix')!='39_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='INSTALLED_MONOMER_CCD_SOURCE_AUDIT'
            or r.get('native_execution')!='INSTALLED_MONOMER_CCD_SOURCE_CONTROLS' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR38_SHA256 or r['prior_archive']['verified_payloads']!=1446):
        raise ValueError('Require exact returned Cedar 39 source evidence')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar38_members(nested)
    _check_catalogue_return(members,r)
    return qualified,prior,rotation


def _check_readyset_source_return(members,r,parent):
    audit=r['readyset_source_audit'];pre='readyset_sources'
    if (audit!=json.loads(members[pre+'/readyset_source_receipt.json'])
            or _sha(members[pre+'/descriptor_worker.py'])!=CEDAR40_WORKER_SHA256
            or audit.get('policy_id')!='cif-readyset-source-and-descriptor-selection-v1'
            or audit.get('automatic_adoption') is not False
            or any(audit.get(k)!='NOT_RUN' for k in ['readyset_execution','dictionary_generation','optimization','mapped_smiles_graph_comparison'])
            or audit.get('numerical_restraints')!='UNASSESSED' or set(audit['components'])!={'PDU','5PC'}):
        raise ValueError('Returned ReadySet source/selection scope differs')
    _check_source_snapshots(members,pre,audit['sources'],'readyset_audit_directory')
    static=audit['static_readyset']
    if (static.get('static_analysis_is_execution_proof') is not False or static.get('readyset_execution')!='NOT_RUN'
            or static.get('coverage_complete') is not True or len(static['sources'])!=24
            or static['entrypoint']!={'anchor':'phenix_installation','path':'lib/python3.11/site-packages/elbow/command_line/ready_set.py'}
            or any(row not in audit['sources'] for row in static['sources'])):
        raise ValueError('Returned ReadySet static coverage differs')
    selected=json.loads(members[pre+'/descriptor_result.json'])
    if set(selected)!={'PDU','5PC'}:raise ValueError('Returned selected-descriptor component scope differs')
    for code,row in audit['components'].items():
        source=parent['installed_source_catalogue']['components'][code]
        matches=[d for d in source['comparison']['descriptors'] if d['descriptor']==row.get('selected_smiles')]
        if (row.get('status')!='SELECTED_DESCRIPTOR_MATCH' or not matches or row.get('matching_descriptors')!=matches
                or row.get('ccd_path')!=source['resource']['path'] or row.get('mapped_smiles_graph_comparison')!='NOT_RUN'
                or row.get('numerical_restraints')!='UNASSESSED'
                or selected[code]!={'ccd_path':row['ccd_path'],'selected_smiles':row['selected_smiles']}):
            raise ValueError('Returned native descriptor selection differs from its source record')


def _read_cedar40_members(members):
    _verify_manifest(members,1529);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR40_BUILD_SHA256
            or r.get('delivery_prefix')!='40_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='READYSET_SOURCE_AND_DESCRIPTOR_AUDIT'
            or r.get('native_execution')!='INSTALLED_CCD_DESCRIPTOR_SELECTION_ONLY' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR39_SHA256 or r['prior_archive']['verified_payloads']!=1486):
        raise ValueError('Require exact returned Cedar 40 source/descriptor evidence')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar39_members(nested)
    _check_readyset_source_return(members,r,json.loads(nested['probe_receipt.json']))
    return qualified,prior,rotation


def _check_readyset_generation_return(members,r):
    """C41's successful receipt process contains two failed native API calls."""
    from nasolve.cif_readyset_generation_audit import ACTIONS
    audit=r['readyset_generation_audit'];pre='readyset_controls'
    if (audit!=json.loads(members[pre+'/readyset_control_receipt.json'])
            or audit.get('policy_id')!='cif-isolated-readyset-call-and-triple-restraint-audit-v1'
            or audit.get('status')!='REVIEW' or audit.get('automatic_adoption') is not False
            or audit.get('native_execution')!='ISOLATED_READYSET_GENERATION_AND_TRIPLE_PROXY_CONTROLS'
            or any(audit.get(k)!='NOT_RUN' for k in ['experimental_model_changes','refinement','scientific_approval'])
            or set(audit['cases'])!={'PDU','5PC'}):raise ValueError('Returned isolated ReadySet scope differs')
    for code,case in audit['cases'].items():
        g=case['generation'];directory=pre+'/generation/'+code
        if (g.get('directory')!={'anchor':'readyset_control_directory','path':'generation/'+code}
                or {k:v for k,v in g.items() if k!='directory'}!=json.loads(members[directory+'/readyset_generation_receipt.json'])
                or g['result']!=json.loads(members[directory+'/readyset_result.json'])
                or g['trace']!=json.loads(members[directory+'/call_trace.json'])
                or _sha(members[directory+'/readyset_worker.py'])!=CEDAR41_WORKER_SHA256
                or g.get('actions')!=ACTIONS or g['execution'].get('status')!='COMPLETED' or g['execution'].get('returncode')!=0
                or g['result'].get('execution')!='EXCEPTION' or g['result'].get('exception_type')!='SystemExit'
                or g['result'].get('message')!='2' or '--ready_set.input.output_file_name' not in g['result'].get('traceback','')
                or g['trace'].get('argument_overrides')!='NONE' or g['trace'].get('truncated') is not False
                or case.get('native_triple_screen')!={'status':'NOT_RUN'} or 'native_interpretation' in case):
            raise ValueError('Returned worker success must retain native ReadySet failure')
        _check_source_snapshots(members,directory,g['sources'],'readyset_directory')
        _returned_outputs(members,directory,g['outputs'],'readyset_directory')
        _returned_outputs(members,directory,g['excluded_serialized_outputs'],'readyset_directory',excluded_pickles=True)
        candidate=g['candidate'];source=members['component_controls/sources/'+code+'.cif']
        if (candidate.get('status')!='RECORDED' or candidate.get('path')!=code+'.cif'
                or 'classification' in candidate or case.get('source_sha256')!=_sha(source)):
            raise ValueError('Returned source copy is not a completed numerical candidate')
        _returned_outputs(members,directory,[candidate],'readyset_directory')
        if members[directory+'/'+candidate['path']]!=source:raise ValueError('Returned preparatory CIF differs from its public source')
        calls=g['trace']['events']
        if (len(calls)!=1 or calls[0].get('api')!='ELBOW_BUILDER' or calls[0].get('args')!=[]
                or calls[0].get('kwargs')!={'file':code+'.cif','id':code,'output':code,'silent':True}
                or calls[0].get('status')!='EXCEPTION' or calls[0].get('exception_type')!='SystemExit'
                or calls[0].get('message')!='2' or calls[0].get('caller')!={'anchor':'phenix_installation',
                    'path':'lib/python3.11/site-packages/elbow/scripts/elbow_on_pdb_file.py','line':779}):
            raise ValueError('Returned preparatory builder call differs')


def _read_cedar41_members(members):
    _verify_manifest(members,1624);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR41_BUILD_SHA256
            or r.get('delivery_prefix')!='41_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='ISOLATED_READYSET_GENERATION_AUDIT'
            or r.get('native_execution')!='ISOLATED_READYSET_GENERATION_AND_TRIPLE_PROXY_CONTROLS'
            or r.get('dictionary_generation')!='ISOLATED_READYSET_REQUESTED' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR40_SHA256 or r['prior_archive']['verified_payloads']!=1529):
        raise ValueError('Require exact returned Cedar 41 failed ReadySet controls')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar40_members(nested)
    _check_readyset_generation_return(members,r)
    return qualified,prior,rotation


def _replay_readyset_generation_return(members,frozen,sources):
    from nasolve.cif_readyset_generation_audit import audit_readyset_controls,classify_readyset_candidate
    from nasolve.cif_triple_bond_audit import audit_triple_bonds
    r=json.loads(members['probe_receipt.json']);result={}
    with tempfile.TemporaryDirectory(prefix='cif-readyset-return-') as owned:
        plan=Path(owned).resolve(strict=True)/'replay'
        report=audit_readyset_controls(sources,plan)
        for code,case in r['readyset_generation_audit']['cases'].items():
            g=case['generation'];pre='readyset_controls/generation/'+code
            candidate=frozen/pre/(code+'.cif');source=sources[code]
            screen=audit_triple_bonds(source,code,dictionary=candidate)
            if not _evidence_equal(screen,case['dictionary_triple_screen']):raise ValueError('Returned source-copy triple screen does not replay')
            prepared=report['cases'][code]['model_preparation']
            if prepared!=case['model_preparation']:raise ValueError('Returned ReadySet source models do not replay')
            for name in ['complete_source_seed.pdb','source_seed.pdb','isolated_component.phil']:
                if (plan/'models'/code/name).read_bytes()!=members['readyset_controls/models/'+code+'/'+name]:
                    raise ValueError('Returned ReadySet fixed seed/policy bytes do not replay')
            if (r['delivery_prefix']=='41_Cedar' and candidate.read_bytes()!=source.read_bytes()) or members[pre+'/source_seed.pdb']!=members['readyset_controls/models/'+code+'/source_seed.pdb']:
                raise ValueError('Returned preparatory source copy changed')
            result[code]={'worker_process':g['execution']['status'],'readyset_execution':g['result']['execution'],
                'exception_type':g['result'].get('exception_type'),'exception_message':g['result'].get('message'),
                'builder_call':g['trace']['events'][0],**classify_readyset_candidate(g,source.read_bytes(),candidate.read_bytes()),
                'source_seed_models_replayed':True,'dictionary_triple_screen':screen,'native_triple_screen':{'status':'NOT_RUN'},
                'historical_floppy_geometry_cause':'NOT_ESTABLISHED','captured_code_execution':'NOT_RUN'}
            if 'native_interpretation' in case:
                active=audit_triple_bonds(source,code,native=case['native_interpretation']['native_validation'])
                if not _evidence_equal(active,case['native_triple_screen']):raise ValueError('Returned active native triple screen does not replay')
                result[code]['native_triple_screen']=active
    return result


def _check_completed_readyset_return(members,r):
    from nasolve.cif_readyset_generation_audit import ACTIONS
    audit=r['readyset_generation_audit'];pre='readyset_controls'
    if (audit!=json.loads(members[pre+'/readyset_control_receipt.json'])
            or audit.get('policy_id')!='cif-isolated-readyset-call-and-triple-restraint-audit-v2'
            or audit.get('status')!='REVIEW' or audit.get('automatic_adoption') is not False
            or audit.get('native_execution')!='ISOLATED_READYSET_GENERATION_AND_TRIPLE_PROXY_CONTROLS'
            or any(audit.get(k)!='NOT_RUN' for k in ['experimental_model_changes','refinement','scientific_approval'])
            or set(audit['cases'])!={'PDU','5PC'}):raise ValueError('Returned completed ReadySet scope differs')
    for code,c in audit['cases'].items():
        g=c['generation'];directory=pre+'/generation/'+code
        if (g.get('directory')!={'anchor':'readyset_control_directory','path':'generation/'+code}
                or {k:v for k,v in g.items() if k!='directory'}!=json.loads(members[directory+'/readyset_generation_receipt.json'])
                or g['result']!=json.loads(members[directory+'/readyset_result.json']) or g['trace']!=json.loads(members[directory+'/call_trace.json'])
                or _sha(members[directory+'/readyset_worker.py'])!=CEDAR42_WORKER_SHA256
                or g['actions']!=ACTIONS or g['execution'].get('status')!='COMPLETED' or g['execution'].get('returncode')!=0
                or g['result'].get('execution')!='COMPLETED' or g['result'].get('effective_actions')!=ACTIONS
                or g['result'].get('process_argv_policy')!='EXPLICIT_API_ARGUMENTS_NO_PROCESS_OPTIONS' or len(g['result'].get('process_argv',[]))!=1
                or g['trace'].get('argument_overrides')!='NONE' or g['trace'].get('truncated') is not False):
            raise ValueError('Returned ReadySet completion or argument isolation differs')
        _check_source_snapshots(members,directory,g['sources'],'readyset_directory')
        _returned_outputs(members,directory,g['outputs'],'readyset_directory')
        _returned_outputs(members,directory,g['excluded_serialized_outputs'],'readyset_directory',excluded_pickles=True)
        candidate=g['candidate'];_returned_outputs(members,directory,[candidate],'readyset_directory')
        if (candidate.get('status')!='RECORDED' or candidate.get('path')!=code+'.cif' or candidate.get('source_bytes_match') is not False
                or candidate.get('classification')!='COMPLETED_READYSET_OUTPUT' or candidate.get('generation_claim')!='COMPLETED_READYSET_OUTPUT'
                or candidate['sha256']!=CEDAR42_CANDIDATE_SHA256[code]):raise ValueError('Returned generated dictionary differs')
        calls=g['trace']['events']
        if (len(calls)!=1 or calls[0].get('api')!='ELBOW_BUILDER' or calls[0].get('status')!='RETURNED'
                or calls[0].get('args')!=[] or calls[0].get('kwargs')!={'file':code+'.cif','id':code,'output':code,'silent':True}
                or calls[0].get('process_argv')!=g['result']['process_argv']):raise ValueError('Returned preparatory builder success differs')
        n=c['native_interpretation'];np=CEDAR42_NATIVE_PREFIX[code];v=n['native_validation']
        if (n!=json.loads(members[np+'/native_receipt.json']) or v!=json.loads(members[np+'/native_validation.json'])
                or _sha(members[np+'/native_worker.py'])!=CEDAR42_NATIVE_WORKER_SHA256
                or n.get('policy_id')!='cif-native-bundle-inventory-v1' or n.get('status')!='REVIEW'
                or n['execution'].get('status')!='COMPLETED' or n['execution'].get('returncode')!=0
                or n.get('source_preserved') is not True or n.get('frozen_inputs_preserved') is not True
                or v.get('status')!='REVIEW' or v.get('fatal_problems') is not None or v.get('unused_definitions') or v.get('unsupported_fields')
                or v.get('atom_count')!=23 or len(v.get('atoms',[]))!=23 or v.get('restraint_policy',{}).get('secondary_structure_enabled') is not False
                or sorted(x['role'] for x in n['inputs'])!=['dictionary','model','phil']):raise ValueError('Returned isolated native interpretation differs')
        _returned_outputs(members,np,n['inputs'],'native_directory');_returned_outputs(members,np,n['outputs'],'native_directory')
        selected=[x for x in n['inputs'] if x['role']=='dictionary'][0]
        if members[np+'/'+selected['path']]!=members[directory+'/'+candidate['path']]:raise ValueError('Native control did not use the generated dictionary')
        if (any(c[k].get('status')!='REVIEW' or c[k].get('target_screen')!='PASS' for k in ['dictionary_triple_screen','native_triple_screen'])
                or len(c['dictionary_triple_screen'].get('linear_axis_torsions',[]))!=6
                or len(c['native_triple_screen'].get('linear_axis_torsions',[]))!=3):raise ValueError('Returned passing triple targets must retain torsion reviews')


def _read_cedar42_members(members):
    _verify_manifest(members,1747);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR42_BUILD_SHA256
            or r.get('delivery_prefix')!='42_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='ISOLATED_READYSET_GENERATION_AUDIT'
            or r.get('native_execution')!='ISOLATED_READYSET_GENERATION_AND_TRIPLE_PROXY_CONTROLS'
            or r.get('dictionary_generation')!='ISOLATED_READYSET_REQUESTED' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR41_SHA256 or r['prior_archive']['verified_payloads']!=1624):
        raise ValueError('Require exact returned Cedar 42 completed isolated controls')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar41_members(nested);_check_completed_readyset_return(members,r)
    return qualified,prior,rotation


def _check_conditioning_return(members,r):
    from nasolve.cif_dihedral_conditioning import POLICY_ID,replay_conditioning_evidence
    a=r['torsion_conditioning_audit'];replayed={}
    if (a.get('policy_id')!=POLICY_ID or a.get('status')!='REVIEW' or set(a.get('cases',{}))!={'PDU','5PC'}
            or a.get('restraint_changes')!='NONE' or a.get('automatic_adoption') is not False
            or a.get('native_execution')!='ISOLATED_DIHEDRAL_CONDITIONING_ONLY'
            or any(a.get(k)!='NOT_RUN' for k in ['dictionary_generation','readyset','model_optimization','scientific_approval'])):
        raise ValueError('Require original fixed conditioning scope')
    if json.loads(members['torsion_conditioning_receipt.json'])!=a:raise ValueError('Conditioning receipt differs')
    previous=json.loads(members['inputs/review/probe_receipt.json'])['readyset_generation_audit']['cases']
    for code,c in a['cases'].items():
        n=c['native'];p=CEDAR43_NATIVE_PREFIX[code];x=n['result'];old=previous[code]['native_interpretation']
        if (c['candidate_sha256']!=CEDAR42_CANDIDATE_SHA256[code]
                or n.get('status')!='REVIEW' or n['execution'].get('status')!='COMPLETED' or n['execution'].get('returncode')!=0
                or n.get('source_preserved') is not True or n.get('frozen_inputs_preserved') is not True
                or n.get('automatic_adoption') is not False or n.get('restraint_changes')!='NONE'
                or x.get('captured_inventory_matches') is not True
                or x['constraint_signature_before']!=x['constraint_signature_after']
                or x['max_evaluation_pairs']!=3000 or not 0<x['evaluation_pairs']<=3000
                or len(c['proxies'])!=3 or len(x['installed_numeric_sources'])!=6
                or _sha(members[p+'/conditioning_worker.py'])!=CEDAR43_WORKER_SHA256
                or _sha(members[p+'/native_worker.py'])!=CEDAR42_NATIVE_WORKER_SHA256
                or json.loads(members[p+'/expected_inventory.json'])!=old['native_validation']
                or json.loads(members[p+'/conditioning_receipt.json'])!=n
                or json.loads(members[p+'/conditioning_result.json'])!=x):
            raise ValueError('Returned native conditioning execution differs')
        spec=json.loads(members[p+'/conditioning_spec.json'])
        if (spec['coordinate_cases']!=c['coordinate_cases'] or spec['proxies']!=c['proxies']
                or [(v['module'],v['sha256']) for v in spec['expected_numeric_sources']]!=[(v['module'],v['sha256']) for v in x['installed_numeric_sources']]):
            raise ValueError('Returned conditioning specification differs')
        _returned_outputs(members,p,n['inputs'],'native_directory');_returned_outputs(members,p,n['outputs'],'native_directory')
        for row in n['inputs']:
            matches=[v for v in old['inputs'] if v['role']==row['role']]
            if len(matches)!=1 or row['sha256']!=matches[0]['sha256']:raise ValueError('Conditioning scientific input differs')
        for row in x['installed_dihedral_sources']:
            if row['status']=='RECORDED' and _sha(members[p+'/installed_source/'+row['path']])!=row['sha256']:
                raise ValueError('Captured installed dihedral source differs')
        if (c['source_state_review']['source_charge_sum']!=0 or c['source_state_review']['generated_charge_sum']!=-2
                or len(c['source_state_review']['missing_source_atoms'])!=2 or c['source_state_review']['status']!='REVIEW'):
            raise ValueError('Open chemical-state findings were hidden')
        replayed[code]=replay_conditioning_evidence(x,c['coordinate_cases'],c['proxies'])
    return replayed


def _read_cedar43_members(members):
    _verify_manifest(members,1794);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR43_BUILD_SHA256
            or r.get('delivery_prefix')!='43_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='ISOLATED_DIHEDRAL_CONDITIONING_AUDIT'
            or r.get('native_execution')!='ISOLATED_DIHEDRAL_CONDITIONING_ONLY' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR42_SHA256 or r['prior_archive']['verified_payloads']!=1747):
        raise ValueError('Require exact returned Cedar 43 fixed conditioning controls')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar42_members(nested);_check_conditioning_return(members,r)
    return qualified,prior,rotation


def _check_linear_torsion_candidate_return(members,r):
    from nasolve.cif_linear_torsion_candidate import POLICY_ID,qualify_linear_torsion_candidate
    a=r['linear_torsion_candidate_audit'];replayed={}
    if (a.get('policy_id')!=POLICY_ID or a.get('status')!='REVIEW' or set(a.get('cases',{}))!={'PDU','5PC'}
            or a.get('native_execution')!='ISOLATED_TORSION_OMISSION_INVENTORIES' or a.get('automatic_adoption') is not False
            or a.get('restraint_changes')!='SEPARATE_CANDIDATE_TORSION_OMISSIONS_ONLY'
            or any(a.get(k)!='NOT_RUN' for k in ['dictionary_generation','readyset','model_optimization','model_editing','scientific_approval'])
            or json.loads(members['linear_torsion_candidate_receipt.json'])!=a):
        raise ValueError('Require exact separate candidate inventory scope')
    previous=json.loads(members['inputs/review/probe_receipt.json'])['torsion_conditioning_audit']['cases']
    for code,c in a['cases'].items():
        plan=c['plan'];candidate=c['candidate'];old=previous[code]
        if (plan.get('removed_torsion_count')!=6 or plan.get('parsed_allowlist_pass') is not True
                or plan.get('source_preserved') is not True or plan.get('automatic_adoption') is not False
                or plan.get('selection_coordinates')!='NOT_USED' or c.get('original_inventory_matches') is not True
                or plan['source_sha256']!=CEDAR42_CANDIDATE_SHA256[code] or plan['candidate_sha256']!=CEDAR44_CANDIDATE_SHA256[code]
                or candidate['path']!='linear_torsion_candidates/'+code+'/'+code+'_linear_torsion_candidate.cif'
                or candidate['anchor']!='probe_directory' or candidate['sha256']!=plan['candidate_sha256']
                or _sha(members[candidate['path']])!=candidate['sha256'] or len(members[candidate['path']])!=candidate['size']
                or c['source_state_review']!=old['source_state_review']):raise ValueError('Candidate plan, artifact or open state differs')
        for role in ['original_native','candidate_native']:
            n=c[role];p=CEDAR44_NATIVE_PREFIX[code][role]
            if (n.get('status')!='REVIEW' or n['execution'].get('status')!='COMPLETED' or n['execution'].get('returncode')!=0
                    or n.get('source_preserved') is not True or n.get('frozen_inputs_preserved') is not True
                    or n.get('automatic_adoption') is not False
                    or any(n.get(k)!='NOT_RUN' for k in ['optimization','model_editing','readyset_retry','scientific_approval'])
                    or _sha(members[p+'/native_worker.py'])!=CEDAR42_NATIVE_WORKER_SHA256
                    or json.loads(members[p+'/native_receipt.json'])!=n
                    or json.loads(members[p+'/native_validation.json'])!=n['native_validation']):raise ValueError('Returned native inventory differs')
            _returned_outputs(members,p,n['inputs'],'native_directory');_returned_outputs(members,p,n['outputs'],'native_directory')
            dictionary=[v for v in n['inputs'] if v['role']=='dictionary']
            expected_sha=plan['source_sha256'] if role=='original_native' else plan['candidate_sha256']
            if len(dictionary)!=1 or dictionary[0]['sha256']!=expected_sha:raise ValueError('Native inventory dictionary differs')
            for field in ['model','phil']:
                rows=[v for v in n['inputs'] if v['role']==field];prior=[v for v in old['native']['inputs'] if v['role']==field]
                if len(rows)!=1 or len(prior)!=1 or rows[0]['sha256']!=prior[0]['sha256']:raise ValueError('Native model or policy input differs')
        expected=json.loads(members['inputs/review/'+CEDAR43_NATIVE_PREFIX[code]+'/expected_inventory.json'])
        before=c['original_native']['native_validation'];after=c['candidate_native']['native_validation']
        if any(before.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):
            raise ValueError('Original manager differs from verified conditioning manager')
        q=qualify_linear_torsion_candidate(before,after,plan)
        if q!=c['native_mechanics'] or not q['mechanics_checks_pass'] or q['removed_native_proxy_counts']!={'dihedral':3,'const_dihedral':0}:
            raise ValueError('Candidate exact omission does not replay')
        for key in ['dictionary_triple_screen','native_triple_screen']:
            if c[key].get('target_screen')!='PASS' or c[key].get('linear_axis_torsions')!=[]:raise ValueError('Candidate triple terms or omission differs')
        replayed[code]=q
    return replayed


def _read_cedar44_members(members):
    _verify_manifest(members,1847);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR44_BUILD_SHA256
            or r.get('delivery_prefix')!='44_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='ISOLATED_LINEAR_TORSION_CANDIDATE'
            or r.get('native_execution')!='ISOLATED_TORSION_OMISSION_INVENTORIES' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR43_SHA256 or r['prior_archive']['verified_payloads']!=1794):
        raise ValueError('Require exact returned Cedar 44 candidate/native inventories')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar43_members(nested);_check_linear_torsion_candidate_return(members,r)
    return qualified,prior,rotation


def _replay_linear_torsion_candidate_return(members,frozen,sources,output):
    from nasolve.cif_linear_torsion_candidate import prepare_linear_torsion_candidate
    from nasolve.cif_triple_bond_audit import audit_triple_bonds
    r=json.loads(members['probe_receipt.json']);checks=_check_linear_torsion_candidate_return(members,r);result={}
    for code,c in r['linear_torsion_candidate_audit']['cases'].items():
        p=CEDAR44_NATIVE_PREFIX[code]['original_native'];row=next(v for v in c['original_native']['inputs'] if v['role']=='dictionary')
        original=frozen/p/row['path'];candidate=frozen/c['candidate']['path'];replayed=output/code/'candidate.cif'
        plan=prepare_linear_torsion_candidate(original,code,replayed)
        if plan!=c['plan'] or replayed.read_bytes()!=candidate.read_bytes():raise ValueError('Candidate parsed allowlist/bytes do not replay')
        dictionary=audit_triple_bonds(sources[code],code,dictionary=candidate)
        native=audit_triple_bonds(sources[code],code,native=c['candidate_native']['native_validation'])
        if dictionary!=c['dictionary_triple_screen'] or native!=c['native_triple_screen']:raise ValueError('Candidate triple screens do not replay')
        result[code]={'mechanics':checks[code],'candidate_bytes_reproduced':True,'parsed_allowlist_replayed':True,
            'dictionary_target_screen':dictionary['target_screen'],'native_target_screen':native['target_screen'],
            'source_state_review':c['source_state_review'],'captured_code_execution':'NOT_RUN'}
    return result


def _check_impact_return(members,r,*,cache=False):
    from nasolve.cif_linear_torsion_impact import POLICY_ID,replay_impact_evidence
    if cache:
        from nasolve.cif_nonbonded_cache_audit import replay_cache_impact_evidence
    a=r['linear_torsion_impact_audit'];proof={}
    if (a.get('policy_id')!=POLICY_ID or a.get('status')!='REVIEW' or set(a.get('cases',{}))!={'PDU','5PC'}
            or a.get('native_execution')!='ISOLATED_FIXED_COORDINATE_TORSION_IMPACT' or a.get('automatic_adoption') is not False
            or a.get('restraint_changes')!='NONE; SAVED_SEPARATE_CANDIDATES_EVALUATED'
            or any(a.get(k)!='NOT_RUN' for k in ['dictionary_generation','readyset','model_optimization','model_editing','scientific_approval'])
            or json.loads(members['linear_torsion_impact_receipt.json'])!=a):raise ValueError('Require fixed-coordinate impact scope')
    if cache and a.get('cache_policy_id')!='cif-native-nonbonded-cache-proof-v1':raise ValueError('Missing returned cache policy')
    prior=json.loads(members['inputs/review/'*(2 if cache else 1)+'probe_receipt.json'])['linear_torsion_candidate_audit']['cases']
    for code,c in a['cases'].items():
        n=c['native'];p=(CEDAR46_NATIVE_PREFIX if cache else CEDAR45_NATIVE_PREFIX)[code];x=n['result'];old=prior[code]
        if (n.get('status')!='REVIEW' or n['execution'].get('status')!='COMPLETED' or n['execution'].get('returncode')!=0
                or any(n.get(k) is not True for k in ['source_preserved','frozen_inputs_preserved'])
                or n.get('automatic_adoption') is not False or any(n.get(k)!='NOT_RUN' for k in ['model_optimization','model_editing','dictionary_generation','readyset','scientific_approval'])
                or x.get('captured_inventories_match') is not True or x.get('analysis_completed') is not True
                or x['constraint_signatures_before']!=x['constraint_signatures_after'] or set(x['constraint_signatures_before'])!={'original','candidate'}
                or x['evaluation_calls']!=(1716 if cache else 1620) or x['max_evaluation_calls']!=2000 or x.get('normalization') is not False
                or c['candidate_sha256']!=CEDAR44_CANDIDATE_SHA256[code] or c['source_state_review']!=old['source_state_review']
                or _sha(members[p+'/impact_worker.py'])!=(CEDAR46_WORKER_SHA256 if cache else CEDAR45_WORKER_SHA256)
                or json.loads(members[p+'/impact_receipt.json'])!=n or json.loads(members[p+'/impact_result.json'])!=x):
            raise ValueError('Returned native impact execution differs')
        spec=json.loads(members[p+'/impact_spec.json'])
        if cache:
            if spec.get('cache_preflight') is not True or n.get('cache_preflight_requested') is not True:raise ValueError('Returned cache action differs')
            for name,digest in CEDAR46_HELPER_SHA256.items():
                if _sha(members[p+'/'+name])!=digest:raise ValueError('Returned cache helper differs')
            captured=x.get('installed_cache_sources',[])
            if len(captured)!=4 or {v.get('path') for v in captured}!={'installed_source/'+name for name in ['manager.py','energies.py','nonbonded.h','nonbonded_bpl.cpp']}:
                raise ValueError('Incomplete returned installed cache source scope')
            for row in captured:
                if (row.get('status')!='RECORDED' or not _safe(row.get('path')) or _sha(members[p+'/'+row['path']])!=row['sha256']
                        or len(members[p+'/'+row['path']])!=row['bytes']):raise ValueError('Returned installed cache source changed')
        if (spec['coordinate_cases']!=c['coordinate_cases'] or spec['selected_indices']!=c['selected_indices'] or spec['removed_references']!=c['removed_references']
                or [(v['module'],v['sha256']) for v in spec['expected_numeric_sources']]!=[(v['module'],v['sha256']) for v in x['installed_numeric_sources']]):
            raise ValueError('Returned numerical impact specification differs')
        _returned_outputs(members,p,n['inputs'],'native_directory');_returned_outputs(members,p,n['outputs'],'native_directory')
        for phase in ['original','candidate']:
            expected=old[phase+'_native']['native_validation'];captured=json.loads(members[p+'/'+phase+'/expected_inventory.json'])
            if captured!=expected or _sha(members[p+'/'+phase+'/native_worker.py'])!=CEDAR42_NATIVE_WORKER_SHA256:raise ValueError('Captured impact manager differs')
            actual=json.loads(members[p+'/'+phase+'/native_validation.json'])
            if any(actual.get(k)!=expected.get(k) for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']):raise ValueError('Impact manager inventory did not match')
            for row in [v for v in n['inputs'] if v['phase']==phase]:
                matched=[v for v in old[phase+'_native']['inputs'] if v['role']==row['role']]
                if len(matched)!=1 or row['sha256']!=matched[0]['sha256']:raise ValueError('Impact scientific input differs')
        replay=replay_cache_impact_evidence if cache else replay_impact_evidence
        proof[code]=replay(x,c['coordinate_cases'],c['selected_indices'],c['removed_references'])
    return proof


def _read_cedar45_members(members):
    _verify_manifest(members,1910);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR45_BUILD_SHA256
            or r.get('delivery_prefix')!='45_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='ISOLATED_LINEAR_TORSION_NUMERICAL_IMPACT'
            or r.get('native_execution')!='ISOLATED_FIXED_COORDINATE_TORSION_IMPACT' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR44_SHA256 or r['prior_archive']['verified_payloads']!=1847):raise ValueError('Require exact returned Cedar 45 impact review')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar44_members(nested);_check_impact_return(members,r)
    return qualified,prior,rotation


def _read_cedar46_members(members):
    _verify_manifest(members,1983);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR46_BUILD_SHA256
            or r.get('delivery_prefix')!='46_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='ISOLATED_NONBONDED_CACHE_PROOF_AND_IMPACT'
            or r.get('native_execution')!='ISOLATED_FIXED_COORDINATE_TORSION_IMPACT' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR45_SHA256 or r['prior_archive']['verified_payloads']!=1910):raise ValueError('Require exact returned Cedar 46 cache review')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar45_members(nested);_check_impact_return(members,r,cache=True)
    return qualified,prior,rotation


def _check_index_capture(members,n,p,spec,*,integer_keys=False):
    """Replay C51's failed observation, including the selected producer sources."""
    import ast
    from nasolve.cif_constructor_index_basis import SOURCE_PATHS,POLICY_ID,INTEGER_KEYS_POLICY_ID
    t=n['result']['constructor_trace'];rows=n.get('index_sources',[])
    if (len(rows)!=2 or {v['snapshot']['path'] for v in rows}!={'index_sources/'+v+'.txt' for v in SOURCE_PATHS}
            or spec.get('index_sources')!=rows or t.get('index_sources')!=rows
            or t.get('index_policy_id')!=(INTEGER_KEYS_POLICY_ID if integer_keys else POLICY_ID)):raise ValueError('Prior index-source scope changed')
    pins={}
    for row in rows:
        snapshot=row['snapshot'];data=members[p+'/'+snapshot['path']]
        if (row.get('anchor')!='phenix_installation' or snapshot.get('anchor')!='constructor_directory'
                or not _safe(row['path']) or not _safe(snapshot['path'])
                or _sha(data)!=row['sha256'] or len(data)!=row['size']):raise ValueError('Prior index source changed')
        pins[row['path']]=(row,ast.parse(data))
    factories=t.get('index_method_sources',[])
    if len(factories)!=1 or factories[0].get('method')!='geometry_manager.run':raise ValueError('Prior index factory changed')
    parameters=[e.get('mapping',{}).get('index_basis',{}) for e in t['events']
        if e.get('method')=='ChiralClass.GetRestrainedParameters' and e.get('phase')=='exit']
    if len(parameters)!=3:raise ValueError('Prior index parameter scope changed')
    methods=factories+[v.get('restraint_method',{}) for v in parameters]
    if integer_keys:
        for basis in parameters:
            rows=basis.get('integer_key_methods',[])
            if len(rows)!=2 or {v.get('method') for v in rows}!={'RestraintClass.get_key','RestraintClass.GetCoordinates'}:raise ValueError('Prior integer-key method scope changed')
            methods.extend(rows)
    for method in methods:
        pin=pins.get(method.get('path'));parts=method.get('method','').split('.')
        if pin is None or len(parts)!=2:raise ValueError('Prior index method changed')
        row,tree=pin;module='elbow.cctbx_api.'+row['path'].split('/')[-1].removesuffix('.py')
        definitions=([v for v in tree.body if isinstance(v,ast.FunctionDef)] if parts[0]=='geometry_manager' else
            [v for cls in tree.body if isinstance(cls,ast.ClassDef) and cls.name==parts[0] for v in cls.body if isinstance(v,ast.FunctionDef)])
        if (method.get('module')!=module or method.get('sha256')!=row['sha256']
                or sum(v.name==parts[1] and v.lineno==method.get('definition_line') for v in definitions)!=1):
            raise ValueError('Prior index method definition changed')


def _check_constructor_return(members,r,*,backend=False,trace=False,control=False,mapping=False,index=False,integer_keys=False):
    """Replay original C47/C48 snapshots without running captured code or resuming them."""
    from nasolve.cif_source_constructor import qualify_constructor_evidence,SOURCE_PATHS,POLICY_ID,BACKEND_POLICY_ID,native_cctbx_reference
    a=r['source_constructor_audit'];replayed={};execution='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS' if index else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_MAPPING' if mapping else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_TRACE' if trace else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_HANDOFF' if backend else 'SOURCE_NATIVE_CONSTRUCTOR_HANDOFF'
    if (json.loads(members['source_constructor_receipt.json'])!=a or a.get('policy_id')!=POLICY_ID
            or set(a.get('cases',{}))!={'DP','PDU','5PC'} or a.get('status')!='REVIEW'
            or a.get('native_execution')!=execution or a.get('automatic_adoption') is not False
            or a.get('constructor_local_optimization')!='NATIVE_INTERNALS_NOT_INSTRUMENTED'
            or a.get('whole_molecule_optimization')!='NOT_REQUESTED'
            or any(a.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','absolute_cip_assignment'])):
        raise ValueError('Require the original source-constructor handoff')
    if backend and (a.get('backend_policy_id')!=BACKEND_POLICY_ID or a.get('native_backend_selection')!='EXPLICIT_NATIVE_CCTBX'):raise ValueError('Require explicit prior CCTBX preparation')
    with tempfile.TemporaryDirectory(prefix='nasolve-constructor-replay-') as temporary:
        for code,c in a['cases'].items():
            n=c['control_native' if control else 'native'];p=('source_constructor_control/' if control else 'source_constructor/')+code;dialect='MONOMER_LIBRARY_CIF' if code=='DP' else 'CHEMICAL_COMPONENTS_CIF'
            if (n.get('directory')!={'anchor':'probe_directory','path':p} or n.get('component')!=code
                    or n.get('policy_id')!=POLICY_ID or n.get('expected_dialect')!=dialect or c.get('reader_dialect')!=dialect
                    or n.get('source_preserved') is not True or n.get('status')!='REVIEW' or n.get('automatic_adoption') is not False
                    or n.get('execution',{}).get('status')!='COMPLETED' or n['execution'].get('returncode')!=0
                    or type(n['execution'].get('timeout_seconds')) not in (int,float) or not 0<n['execution']['timeout_seconds']<=(30 if trace else 60)
                    or any(n.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','whole_builder_replay','absolute_cip_assignment',
                        'installed_phenix_edits','captured_code_execution','pickle_loading'])
                    or n.get('whole_molecule_optimization')!='NOT_REQUESTED'
                    or n.get('constructor_local_optimization')!='NATIVE_INTERNALS_NOT_INSTRUMENTED'
                    or _sha(members[p+'/constructor_worker.py'])!=(CEDAR52_WORKER_SHA256 if integer_keys and not control else CEDAR51_WORKER_SHA256 if index and not control else CEDAR50_WORKER_SHA256 if mapping and not control else CEDAR49_WORKER_SHA256 if trace and not control else CEDAR48_WORKER_SHA256 if backend else CEDAR47_WORKER_SHA256)
                    or json.loads(members[p+'/constructor_receipt.json'])!={k:v for k,v in n.items() if k!='directory'}
                    or json.loads(members[p+'/constructor_result.json'])!=n['result']
                    or (not backend and 'after_format' in n['result']['constructor'])):raise ValueError('Returned constructor execution changed')
            consumer=c['consumer'];data=members[p+'/source.cif'];spec=json.loads(members[p+'/constructor_spec.json'])
            if (consumer.get('anchor')!='probe_directory' or not _safe(consumer['path'])
                    or members[consumer['path']]!=data or _sha(data)!=CEDAR47_SOURCE_SHA256[code]
                    or consumer['sha256']!=n['source_sha256'] or consumer['sha256']!=_sha(data) or consumer['size']!=len(data)
                    or spec.get('component')!=code or (spec.get('native_cctbx') is not True if backend else spec.get('native_cctbx') is not None)
                    or (spec.get('trace_sources') is None if trace and not control else spec.get('trace_sources') is not None)
                    or (spec.get('coordinate_mapping') is not True if mapping and not control else spec.get('coordinate_mapping') is not None)
                    or (spec.get('index_basis') is not True or spec.get('index_sources')!=n.get('index_sources') if index and not control else spec.get('index_basis') is not None or spec.get('index_sources') is not None)
                    or (spec.get('integer_keys') is not True if integer_keys and not control else spec.get('integer_keys') is not None)
                    or spec.get('source_setup') is not None or spec.get('setup_sources') is not None or n.get('setup_sources') is not None):raise ValueError('Returned constructor source/preparation changed')
            rows=n['sources']
            if (len(rows)!=len(SOURCE_PATHS) or {v['snapshot']['path'] for v in rows}!={v+'.txt' for v in SOURCE_PATHS}):
                raise ValueError('Returned constructor source scope changed')
            for row in rows:
                snapshot=row['snapshot'];payload=members[p+'/'+snapshot['path']]
                if (row.get('anchor')!='phenix_installation' or snapshot.get('anchor')!='constructor_directory'
                        or not _safe(row['path']) or _sha(payload)!=row['sha256'] or len(payload)!=row['size']):
                    raise ValueError('Returned constructor API source changed')
            if backend:
                b=n['result']['backend_control'];backend_rows=b['sources']
                if len(backend_rows)!=1 or b['reference']!=native_cctbx_reference(members[p+'/elbow/utilities/Utilities.py.txt']):raise ValueError('Prior backend reference changed')
                row=backend_rows[0];payload=members[p+'/'+row['snapshot']['path']]
                if (row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='constructor_directory'
                        or not _safe(row['path']) or not _safe(row['snapshot']['path'])
                        or not row['path'].endswith('/elbow/cctbx_api/CCTBXMixins.py')
                        or _sha(payload)!=row['sha256'] or row['sha256']!=CEDAR48_BACKEND_SHA256 or len(payload)!=row['size']):raise ValueError('Prior backend API source changed')
                if set(b.get('methods',{}))!={'SetCCTBX','GetCCTBX'} or any(v.get('path')!=row['path'] or v.get('sha256')!=row['sha256']
                        or v.get('module')!='elbow.cctbx_api.CCTBXMixins' or v.get('selected_source') is not True for v in b['methods'].values()):raise ValueError('Prior backend method source changed')
            if trace and not control:
                from nasolve.cif_constructor_trace import analyze_constructor_trace,POLICY_ID as TRACE_POLICY
                t=n['result']['constructor_trace']
                expected_sources=[row for row in rows if row['path'].endswith('/elbow/chemistry/ChiralClass.py')]+backend_rows
                if (a.get('trace_policy_id')!=TRACE_POLICY or a.get('observer_control')!='FRESH_UNOBSERVED_AND_OBSERVED_RUNS'
                        or a.get('native_internal_observation')!='METHOD_BOUNDARIES_ONLY'
                        or spec.get('trace_sources')!=expected_sources
                        or (t.get('mapping_policy_id')!='cif-native-local-coordinate-mapping-v1' if mapping else t.get('mapping_policy_id') is not None)
                        or (t.get('index_policy_id')!=('cif-native-integer-restraint-keys-v2' if integer_keys else 'cif-native-named-restraint-index-basis-v1') if index else t.get('index_policy_id') is not None)
                        or t.get('before')!=n['result']['constructor']['promoted'] or t.get('after')!=n['result']['constructor']['after']):
                    raise ValueError('Prior native boundary scope/endpoints changed')
                pins={row['path']:row for row in rows+backend_rows}
                if len(t.get('method_sources',[]))!=(11 if mapping else 8) or set(t.get('hooks',[]))!={v['method'] for v in t['method_sources']}:
                    raise ValueError('Prior native method scope changed')
                for v in t['method_sources']:
                    row=pins.get(v.get('path'));name=v.get('method','').split('.')
                    if row is None or len(name)!=2 or row['sha256']!=v.get('sha256') or v.get('module')!='elbow.'+row['path'].split('/elbow/')[-1].removesuffix('.py').replace('/','.'):
                        raise ValueError('Prior trace method source changed')
                    tree=__import__('ast').parse(members[p+'/'+row['snapshot']['path']]);definitions=[node for cls in tree.body if isinstance(cls,__import__('ast').ClassDef) and cls.name==name[0]
                        for node in cls.body if isinstance(node,__import__('ast').FunctionDef) and node.name==name[1] and node.lineno==v.get('definition_line')]
                    if len(definitions)!=1:raise ValueError('Prior native method definition changed')
            if index and not control:_check_index_capture(members,n,p,spec,integer_keys=integer_keys)
            if not n['outputs'] or len({v['path'] for v in n['outputs']})!=len(n['outputs']):raise ValueError('Incomplete constructor outputs')
            for row in n['outputs']:
                if row.get('anchor')!='constructor_directory' or not _safe(row['path']):raise ValueError('Invalid constructor output anchor')
                payload=members[p+'/'+row['path']]
                if _sha(payload)!=row['sha256'] or len(payload)!=row['size']:raise ValueError('Returned constructor output changed')
            source=Path(temporary)/(code+'.cif');source.write_bytes(data)
            q=qualify_constructor_evidence(source,code,n['result'],dialect,native_cctbx=backend)
            if q!=n['qualification'] or q['constructor_status']!=('COMPLETED' if backend else 'EXCEPTION') or q['checks_pass']:
                raise ValueError('Original constructor exception/gates do not replay')
            if trace and not control and analyze_constructor_trace(source,code,n['result']['constructor_trace'])!=n['trace_analysis']:raise ValueError('Prior trace findings do not replay')
            if mapping and not control:
                from nasolve.cif_constructor_mapping import analyze_constructor_mapping
                if analyze_constructor_mapping(source,code,n['result']['constructor_trace'])!=n['mapping_analysis']:raise ValueError('Prior mapping findings do not replay')
            if index and not control:
                from nasolve.cif_constructor_index_basis import analyze_index_basis
                if analyze_index_basis(source,code,n['result']['constructor_trace'])!=n['index_analysis']:raise ValueError('Prior named-index findings do not replay')
            replayed[code]={'qualification':q,'exception_type':n['result']['constructor'].get('exception_type'),
                'message':n['result']['constructor'].get('message'),'source_sha256':_sha(data),'failed_checks':[k for k,v in q['checks'].items() if not v]}
    return replayed


def _read_cedar47_members(members):
    _verify_manifest(members,2036);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR47_BUILD_SHA256
            or r.get('delivery_prefix')!='47_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='SOURCE_NATIVE_CONSTRUCTOR_HANDOFF'
            or r.get('native_execution')!='SOURCE_NATIVE_CONSTRUCTOR_HANDOFF' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR46_SHA256 or r['prior_archive']['verified_payloads']!=1983):raise ValueError('Require exact returned Cedar 47 constructor review')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar46_members(nested);_check_constructor_return(members,r)
    return qualified,prior,rotation


def _read_cedar48_members(members):
    _verify_manifest(members,2092);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR48_BUILD_SHA256
            or r.get('delivery_prefix')!='48_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_HANDOFF'
            or r.get('native_execution')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_HANDOFF' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR47_SHA256 or r['prior_archive']['verified_payloads']!=2036):raise ValueError('Require exact returned Cedar 48 constructor review')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar47_members(nested);_check_constructor_return(members,r,backend=True)
    return qualified,prior,rotation


def _check_constructor_trace_return(members,r,*,mapping=False,index=False,integer_keys=False):
    from nasolve.cif_constructor_trace import compare_constructor_runs
    observed=_check_constructor_return(members,r,backend=True,trace=True,mapping=mapping,index=index,integer_keys=integer_keys)
    controls=_check_constructor_return(members,r,backend=True,trace=True,control=True,mapping=mapping,index=index,integer_keys=integer_keys)
    previous=json.loads(members['inputs/review/probe_receipt.json'])['source_constructor_audit']['cases']
    for code,c in r['source_constructor_audit']['cases'].items():
        comparison=compare_constructor_runs(c['control_native'],c['native'],previous[code]['native'])
        if comparison!=c['observer_comparison'] or not comparison['checks_pass'] or not comparison['previous_endpoint_match']:
            raise ValueError('Prior fresh native comparisons do not replay')
        if mapping:observed[code]['mapping_analysis']=c['native']['mapping_analysis']
        if index:observed[code]['index_analysis']=c['native']['index_analysis']
        observed[code].update(trace_analysis=c['native']['trace_analysis'],observer_comparison=comparison,control_qualification=controls[code]['qualification'])
    return observed


def _read_cedar49_members(members):
    _verify_manifest(members,2190);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR49_BUILD_SHA256
            or r.get('delivery_prefix')!='49_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_TRACE'
            or r.get('native_execution')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_TRACE' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR48_SHA256 or r['prior_archive']['verified_payloads']!=2092):raise ValueError('Require exact returned Cedar 49 trace review')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar48_members(nested);_check_constructor_trace_return(members,r)
    return qualified,prior,rotation


def _read_cedar50_members(members):
    _verify_manifest(members,2288);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR50_BUILD_SHA256
            or r.get('delivery_prefix')!='50_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_MAPPING'
            or r.get('native_execution')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_MAPPING' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR49_SHA256 or r['prior_archive']['verified_payloads']!=2190):raise ValueError('Require exact returned Cedar 50 mapping review')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar49_members(nested);_check_constructor_trace_return(members,r,mapping=True)
    return qualified,prior,rotation

def _read_cedar51_members(members):
    _verify_manifest(members,2395);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR51_BUILD_SHA256
            or r.get('delivery_prefix')!='51_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS'
            or r.get('native_execution')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR50_SHA256 or r['prior_archive']['verified_payloads']!=2288):raise ValueError('Require exact returned Cedar 51 named-index review')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar50_members(nested);_check_constructor_trace_return(members,r,mapping=True,index=True)
    return qualified,prior,rotation

def _read_cedar52_members(members):
    _verify_manifest(members,2502);r=json.loads(members['probe_receipt.json'])
    if (_sha(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode())!=CEDAR52_BUILD_SHA256
            or r.get('delivery_prefix')!='52_Cedar' or r.get('kind')!='cif-source-graph-numerical-recovery-probe'
            or r.get('status')!='REVIEW' or r.get('analysis_completed') is not True or r.get('automatic_adoption') is not False
            or r.get('requested_action')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS'
            or r.get('native_execution')!='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS' or r.get('policy_authority')!='NARestraints'
            or any(r.get(k) is not True for k in ['original_archive_preserved','frozen_inputs_preserved','prerequisite_mechanics_replayed'])
            or any(r.get(k)!='NOT_RUN' for k in ['dictionary_generation','model_editing','model_optimization','native_proxy_validation',
                'linked_site_validation','policy_recompilation','refinement','installed_phenix_edits','readyset_retry','scientific_approval'])
            or r['prior_archive']['sha256']!=CEDAR51_SHA256 or r['prior_archive']['verified_payloads']!=2395):raise ValueError('Require exact returned Cedar 52 integer-key review')
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    qualified,prior,rotation=_read_cedar51_members(nested);_check_constructor_trace_return(members,r,mapping=True,index=True,integer_keys=True)
    return qualified,prior,rotation


def _source_reader_evidence(members):
    """Reach the verified C34 constructor evidence without dropping wrappers."""
    prefix=''
    while json.loads(members['probe_receipt.json']).get('delivery_prefix') in {'35_Cedar','36_Cedar','37_Cedar','38_Cedar','39_Cedar','40_Cedar','41_Cedar','42_Cedar','43_Cedar','44_Cedar','45_Cedar','46_Cedar','47_Cedar','48_Cedar','49_Cedar','50_Cedar','51_Cedar','52_Cedar'}:
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
        prefix+='inputs/review/'
    return members,prefix


def _read_capsule(path, expected_sha=None):
    original=path.read_bytes();digest=_sha(original)
    if digest not in ({expected_sha} if expected_sha else {REVIEW_SHA256,CEDAR30_SHA256,CEDAR31_SHA256,CEDAR32_SHA256,CEDAR33_SHA256,CEDAR34_SHA256,CEDAR35_SHA256,CEDAR36_SHA256,CEDAR37_SHA256,CEDAR38_SHA256,CEDAR39_SHA256,CEDAR40_SHA256,CEDAR41_SHA256,CEDAR42_SHA256,CEDAR43_SHA256,CEDAR44_SHA256,CEDAR45_SHA256,CEDAR46_SHA256,CEDAR47_SHA256,CEDAR48_SHA256,CEDAR49_SHA256,CEDAR50_SHA256,CEDAR51_SHA256,CEDAR52_SHA256}):
        raise ValueError('Require an exact verified Cedar 29--52 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries=z.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):raise ValueError('Unsafe or duplicate review member')
        members={e.filename:z.read(e) for e in entries}
    header=json.loads(members['probe_receipt.json'])
    if header.get('delivery_prefix')=='52_Cedar':qualified,prior,rotation=_read_cedar52_members(members)
    elif header.get('delivery_prefix')=='51_Cedar':qualified,prior,rotation=_read_cedar51_members(members)
    elif header.get('delivery_prefix')=='50_Cedar':qualified,prior,rotation=_read_cedar50_members(members)
    elif header.get('delivery_prefix')=='49_Cedar':qualified,prior,rotation=_read_cedar49_members(members)
    elif header.get('delivery_prefix')=='48_Cedar':qualified,prior,rotation=_read_cedar48_members(members)
    elif header.get('delivery_prefix')=='47_Cedar':qualified,prior,rotation=_read_cedar47_members(members)
    elif header.get('delivery_prefix')=='46_Cedar':qualified,prior,rotation=_read_cedar46_members(members)
    elif header.get('delivery_prefix')=='45_Cedar':qualified,prior,rotation=_read_cedar45_members(members)
    elif header.get('delivery_prefix')=='44_Cedar':qualified,prior,rotation=_read_cedar44_members(members)
    elif header.get('delivery_prefix')=='43_Cedar':qualified,prior,rotation=_read_cedar43_members(members)
    elif header.get('delivery_prefix')=='42_Cedar':qualified,prior,rotation=_read_cedar42_members(members)
    elif header.get('delivery_prefix')=='41_Cedar':qualified,prior,rotation=_read_cedar41_members(members)
    elif header.get('delivery_prefix')=='40_Cedar':qualified,prior,rotation=_read_cedar40_members(members)
    elif header.get('delivery_prefix')=='39_Cedar':qualified,prior,rotation=_read_cedar39_members(members)
    elif header.get('delivery_prefix')=='38_Cedar':qualified,prior,rotation=_read_cedar38_members(members)
    elif header.get('delivery_prefix')=='37_Cedar':qualified,prior,rotation=_read_cedar37_members(members)
    elif header.get('delivery_prefix')=='36_Cedar':qualified,prior,rotation=_read_cedar36_members(members)
    elif header.get('delivery_prefix')=='35_Cedar':qualified,prior,rotation=_read_cedar35_members(members)
    elif header.get('delivery_prefix')=='34_Cedar':qualified,prior,rotation=_read_cedar34_members(members)
    elif header.get('delivery_prefix')=='33_Cedar':qualified,prior,rotation=_read_cedar33_members(members)
    elif header.get('delivery_prefix')=='32_Cedar':qualified,prior,rotation=_read_cedar32_members(members)
    elif header.get('delivery_prefix')=='31_Cedar':qualified,prior,rotation=_read_cedar31_members(members)
    elif header.get('delivery_prefix')=='30_Cedar':qualified,prior,rotation=_read_cedar30_members(members)
    else:qualified,prior,rotation=_read_cedar29_members(members)
    return members,qualified,prior,rotation,original


def _replay_charge_controls(members,frozen):
    from nasolve.cif_source_reader import source_reader_checks
    from nasolve.cif_stereochemistry_audit import _values,_graph
    result={}
    for code,row in json.loads(members['probe_receipt.json'])['source_reader_audits'].items():
        source=frozen/row['directory']['path']/'source.cif';control=row['declared_charge_control']
        before,after=control['before'],control['after'];raw=row['result']
        checks=source_reader_checks(source,code,{**raw,'atoms':after['atoms'],'bonds':after['bonds']},row['expected_dialect'])
        charges=_graph(_values(source,code))[2]
        checks['molecule_total_charge']=after['molecule_charge']==sum(charges.values())
        checks['other_native_fields_preserved']=(before['atoms']==raw['atoms'] and before['bonds']==raw['bonds']==after['bonds']
            and [{k:v for k,v in a.items() if k!='native_atom_charge'} for a in before['atoms']]==
                [{k:v for k,v in a.items() if k!='native_atom_charge'} for a in after['atoms']])
        changed=[a['atom'] for a,b in zip(before['atoms'],after['atoms']) if a['native_atom_charge']!=b['native_atom_charge']]
        if (checks!=row['declared_charge_qualification']['checks'] or not all(checks.values())
                or sorted(changed)!=sorted(control['changed_atoms']) or sum(charges.values())!=control['source_total_charge']):
            raise ValueError('Returned declared-charge inventory does not independently replay')
        result[code]={'checks':checks,'changed_atoms':changed,'action':control['action']}
    return result


def _run_triple_action(args,receipt,session,review,original,members,frozen,runtime,controls,sources,capture,expected):
    from nasolve.cif_triple_probe import run_triple_controls
    selected={r['component']:sources[r['component']] for r in controls}
    receipt['limitations']=['Isolated source-seed component controls only; no experimental model, links or diffraction are used.',
        'Installed library lookup and explicit-CIF replay do not reproduce the complete ReadySet pipeline.',
        'Triple-bond screening thresholds prompt review and never generate targets or authorize adoption.',
        'Saved nonconverged PDU candidate and ambiguous 5PC NARestraints role records remain unqualified.']
    if set(selected)!={'PDU','5PC'}:raise ValueError('This reviewed triple-bond slice requires the explicit PDU and 5PC public controls')
    reader_members,reader_prefix=_source_reader_evidence(members)
    root=frozen/reader_prefix/'inputs/review'
    pre,generatedir,_=CEDAR33_CASES['PDU'];candidate=root/pre/'generation'/generatedir/'candidate.cif'
    if _sha(candidate.read_bytes())!=CEDAR33_PDU_CANDIDATE_SHA256:raise ValueError('Saved PDU dictionary candidate changed')
    receipt['triple_candidate_lineage']={'anchor':'probe_directory','path':candidate.relative_to(session).as_posix(),
        'sha256':CEDAR33_PDU_CANDIDATE_SHA256,'convergence':'NOT_CONVERGED_REPORTED','adoption':False}
    phenix=None;fingerprints=[]
    if not args.inspect_only:
        from nasolve.phenix_runtime import installation_from_candidate
        from nasolve.cif_source_reader import verify_source_reader_capture
        phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
        fingerprints=_fingerprints(phenix,{**capture,'native_validation':expected});receipt['installed_api_sources']=fingerprints
        for row in json.loads(members['probe_receipt.json'])['source_reader_audits'].values():
            verify_source_reader_capture(phenix.root,row,frozen/row['directory']['path'])
        receipt['phenix_version']=phenix.version
    print('Checking declared triple bonds at fixed isolated source-seed coordinates.',flush=True)
    report=run_triple_controls(selected,{'PDU':candidate},session/'triple_controls',phenix=phenix,
        api_sources=fingerprints,timeout_seconds=min(args.timeout_seconds,60))
    receipt['triple_bond_audit']=report;receipt['native_execution']=report['native_execution']
    if phenix:
        if _fingerprints(phenix,{**capture,'native_validation':expected})!=fingerprints:raise ValueError('Selected native APIs changed')
        for row in json.loads(members['probe_receipt.json'])['source_reader_audits'].values():
            verify_source_reader_capture(phenix.root,row,frozen/row['directory']['path'])
    for code,case in report['cases'].items():
        for label,screen in case['offline'].items():
            print(code,label+':',screen['status'],'; linear-axis torsions',len(screen.get('linear_axis_torsions',[])),flush=True)
    if any((frozen/PurePosixPath(n)).read_bytes()!=d for n,d in members.items()):raise ValueError('Frozen evidence changed')
    if any((session/'component_controls/sources'/(c['component']+'.cif')).read_bytes()!=runtime[c['path']] for c in controls):raise ValueError('Frozen public control changed')
    if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
    receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
    _json(session/'probe_receipt.json',receipt)
    print('Diagnostic: REVIEW (isolated triple-bond mechanics; ReadySet and scientific qualification remain open)',flush=True)
    print('REVIEW ZIP:',_review_zip(session),flush=True);return 2


def _evidence_equal(a,b):
    if type(a) is float and type(b) is float:return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
    if type(a) is not type(b):return False
    if isinstance(a,dict):return set(a)==set(b) and all(_evidence_equal(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(_evidence_equal(x,y) for x,y in zip(a,b))
    return a==b


def _replay_triple_return(members,frozen,sources):
    from nasolve.cif_triple_bond_audit import audit_triple_bonds,write_component_control_model
    r=json.loads(members['probe_receipt.json']);ref=r['triple_candidate_lineage']
    if ref.get('anchor')!='probe_directory' or not _safe(ref.get('path')) or ref.get('adoption') is not False:
        raise ValueError('Unsafe saved candidate lineage')
    candidate=frozen/PurePosixPath(ref['path'])
    if _sha(candidate.read_bytes())!=CEDAR33_PDU_CANDIDATE_SHA256:raise ValueError('Saved candidate lineage differs')
    result={}
    for code,case in r['triple_bond_audit']['cases'].items():
        source=sources[code]
        if source.read_bytes()!=members['component_controls/sources/'+code+'.cif']:raise ValueError('Fresh public component differs from return')
        replay={'offline':{'public_source':audit_triple_bonds(source,code,dictionary=source)},'native':{}}
        if code=='PDU':replay['offline']['saved_candidate']=audit_triple_bonds(source,code,dictionary=candidate)
        if not _evidence_equal(replay['offline'],case['offline']):raise ValueError('Returned dictionary triple screens do not replay')
        with tempfile.TemporaryDirectory(prefix='cif-triple-return-') as owned:
            output=Path(owned).resolve(strict=True)/(code+'.pdb')
            preparation=write_component_control_model(source,code,output)
            if preparation!=case['model_preparation'] or output.read_bytes()!=members['triple_controls/models/'+code+'/source_seed.pdb']:
                raise ValueError('Returned fixed isolated source-seed model does not replay')
        for label,row in case['native'].items():
            if label=='saved_candidate':
                screen=audit_triple_bonds(source,code,native=row['interpretation']['native_validation'])
                if not _evidence_equal(screen,row['triple_screen']):raise ValueError('Captured active native triple screen does not replay')
                replay['native'][label]=screen
            else:replay['native'][label]=row['triple_screen']
        replay['source_seed_model_replayed']=True;result[code]=replay
    return result


def _run_catalogue_action(args,receipt,session,review,original,members,frozen,runtime,controls,sources,capture,expected):
    from nasolve.cif_installed_source_catalogue import audit_installed_sources,verify_installed_sources
    from nasolve.cif_installed_component import verify_component_capture
    from nasolve.cif_source_reader import audit_source_reader,verify_source_reader_capture
    selected={r['component']:sources[r['component']] for r in controls}
    if set(selected)!={'PDU','5PC'}:raise ValueError('This reviewed source slice requires PDU and 5PC public controls')
    receipt['limitations']=['Installed CCD chemistry and numerical monomer libraries are separate resource classes.',
        'Source/SMILES text comparison is not mapped-SMILES graph validation, native stereo or numerical qualification.',
        'Captured route helpers and dispatcher are read-only evidence; the complete ReadySet path is not executed.',
        'Saved PDU active targets remain accompanied by six linear-axis torsion reviews; no definition is changed.',
        'The two 5PC NARestraints records remain ambiguous; no pairing/stacking policy is selected.']
    receipt['prior_triple_evidence_replay']=_replay_triple_return(members,frozen,selected)
    print('Replayed saved native PDU triple membership and both missing monomer lookups.',flush=True)
    if not args.inspect_only:
        from nasolve.phenix_runtime import installation_from_candidate
        phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
        fingerprints=_fingerprints(phenix,{**capture,'native_validation':expected});receipt['installed_api_sources']=fingerprints;receipt['phenix_version']=phenix.version
        old=json.loads(members['probe_receipt.json']);parent_members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
        parent=json.loads(parent_members['probe_receipt.json']);parent_root=frozen/'inputs/review'
        resources=old['triple_bond_audit']['cases']
        for code,case in resources.items():verify_component_capture(phenix.root,case['installed_resource'],frozen/'triple_controls/resources'/code)
        for row in parent['source_reader_audits'].values():verify_source_reader_capture(phenix.root,row,parent_root/row['directory']['path'])
        proofs=resources['PDU']['installed_resource']['sources']+[s for s in parent['source_reader_audits']['PDU']['sources'] if s['path'].endswith('/elbow/utilities/Utilities.py')]
        catalogue=session/'installed_source_catalogue'
        result=audit_installed_sources(phenix.root,phenix.executables['phenix.python'],phenix.executables['phenix.ready_set'],
            fingerprints,proofs,selected,catalogue,environment=phenix.environment,timeout_seconds=min(args.timeout_seconds,30))
        receipt['installed_source_catalogue']=result;receipt['installed_ccd_reader_audits']={}
        for code,case in result['components'].items():
            print(code,'installed CCD:',case['status'],flush=True)
            print(code,'direct/wrapped monomer:',result['native_resources']['lookups'][code]['direct']['status'],
                  '/',result['native_resources']['lookups'][code]['wrapped']['status'],flush=True)
            if case['status']=='RECORDED':
                comparison=case['comparison']
                print(code,'declarations:',comparison['chemical_declarations'],'; SMILES text:',comparison['descriptor_text_comparison'],
                    '; numerical parameters:',comparison['dictionary_parameterization'],flush=True)
                source=catalogue/case['resource']['snapshot']['path'];output=session/'installed_ccd_readers'/code
                reader=audit_source_reader(phenix.root,phenix.executables['phenix.python'],fingerprints,source,code,output,
                    environment=phenix.environment,expected_dialect='CHEMICAL_COMPONENTS_CIF',timeout_seconds=min(args.timeout_seconds,30))
                receipt['installed_ccd_reader_audits'][code]={'directory':{'anchor':'probe_directory','path':output.relative_to(session).as_posix()},**reader}
                print(code,'installed CCD native reader:',reader['status'],'; declared orders:',reader['checks'].get('declared_bond_orders','NOT_RUN'),flush=True)
        verify_installed_sources(phenix.root,result,catalogue)
        for code,row in receipt['installed_ccd_reader_audits'].items():verify_source_reader_capture(phenix.root,row,session/'installed_ccd_readers'/code)
        for code,case in resources.items():verify_component_capture(phenix.root,case['installed_resource'],frozen/'triple_controls/resources'/code)
        for row in parent['source_reader_audits'].values():verify_source_reader_capture(phenix.root,row,parent_root/row['directory']['path'])
        if _fingerprints(phenix,{**capture,'native_validation':expected})!=fingerprints:raise ValueError('Selected native APIs changed')
        receipt['native_execution']='INSTALLED_MONOMER_CCD_SOURCE_CONTROLS'
    if any((frozen/PurePosixPath(n)).read_bytes()!=d for n,d in members.items()):raise ValueError('Frozen evidence changed')
    if any((session/'component_controls/sources'/(c['component']+'.cif')).read_bytes()!=runtime[c['path']] for c in controls):raise ValueError('Frozen public control changed')
    if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
    receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
    _json(session/'probe_receipt.json',receipt)
    print('Diagnostic: REVIEW (installed monomer/CCD source evidence; no ReadySet, generation or optimization)',flush=True)
    print('REVIEW ZIP:',_review_zip(session),flush=True);return 2


def _replay_catalogue_return(members,frozen,selected):
    from nasolve.cif_installed_source_catalogue import compare_installed_ccd
    from nasolve.cif_source_reader import source_reader_checks
    old=json.loads(members['probe_receipt.json']);result={}
    for code,case in old['installed_source_catalogue']['components'].items():
        source=frozen/'installed_source_catalogue'/case['resource']['snapshot']['path']
        comparison=compare_installed_ccd(selected[code],source,code)
        if not _evidence_equal(comparison,case['comparison']):raise ValueError('Installed CCD source comparison does not replay')
        row=old['installed_ccd_reader_audits'][code]
        checks=source_reader_checks(source,code,row['result'],row['expected_dialect'])
        if checks!=row['checks'] or not all(checks.values()):raise ValueError('Installed CCD native inventory does not replay')
        result[code]={'chemical_declarations':comparison['chemical_declarations'],
            'descriptor_text_comparison':comparison['descriptor_text_comparison'],
            'triple_bonds':comparison['triple_bonds'],'reader_checks':checks,
            'numerical_restraints':'UNASSESSED','mapped_smiles_graph_comparison':'NOT_RUN'}
    return result


def _run_readyset_source_action(args,receipt,session,review,original,members,frozen,runtime,controls,sources,capture,expected):
    from nasolve.cif_readyset_source_audit import audit_readyset_sources,verify_readyset_sources
    from nasolve.cif_installed_source_catalogue import verify_installed_sources
    from nasolve.cif_source_reader import verify_source_reader_capture
    selected={r['component']:sources[r['component']] for r in controls}
    if set(selected)!={'PDU','5PC'}:raise ValueError('This reviewed ReadySet source slice requires PDU and 5PC controls')
    old=json.loads(members['probe_receipt.json']);cat=old['installed_source_catalogue']
    parent_members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    receipt['prior_triple_evidence_replay']=_replay_triple_return(parent_members,frozen/'inputs/review',selected)
    receipt['prior_installed_source_replay']=_replay_catalogue_return(members,frozen,selected)
    receipt['limitations']=['The actual ReadySet dispatcher target and bounded literal-import source inventory are copied as text, never executed.',
        'Only the previously captured installed CCD filename/SMILES accessors run in the selected Phenix interpreter.',
        'Static source and descriptor selection are not executed ReadySet provenance or mapped-SMILES graph/numerical qualification.',
        'Saved PDU torsion reviews and ambiguous 5PC NARestraints records remain; no parameter, model or policy is changed.']
    print('Replayed installed CCD chemistry, raw reader inventories and saved triple-proxy evidence.',flush=True)
    if not args.inspect_only:
        from nasolve.phenix_runtime import installation_from_candidate
        phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
        fingerprints=_fingerprints(phenix,{**capture,'native_validation':expected})
        receipt.update(installed_api_sources=fingerprints,phenix_version=phenix.version)
        verify_installed_sources(phenix.root,cat,frozen/'installed_source_catalogue')
        for row in old['installed_ccd_reader_audits'].values():verify_source_reader_capture(phenix.root,row,frozen/row['directory']['path'])
        result=audit_readyset_sources(phenix.root,phenix.executables['phenix.python'],fingerprints,cat,session/'readyset_sources',
            environment=phenix.environment,timeout_seconds=min(args.timeout_seconds,30))
        receipt['readyset_source_audit']=result
        print('ReadySet source files:',len(result['static_readyset']['sources']),'; literal-import coverage:',result['static_readyset']['coverage_complete'],flush=True)
        print('ReadySet entrypoint:',result['static_readyset']['entrypoint']['path'],flush=True)
        for code,row in result['components'].items():
            labels=[d['program']+'/'+d['type'] for d in row['matching_descriptors']]
            print(code,'native SMILES selection:',row['status'],';',', '.join(labels),flush=True)
            print(code,'selected SMILES:',row['selected_smiles'],flush=True)
        verify_readyset_sources(phenix.root,result,session/'readyset_sources')
        verify_installed_sources(phenix.root,cat,frozen/'installed_source_catalogue')
        for row in old['installed_ccd_reader_audits'].values():verify_source_reader_capture(phenix.root,row,frozen/row['directory']['path'])
        if _fingerprints(phenix,{**capture,'native_validation':expected})!=fingerprints:raise ValueError('Selected native APIs changed')
        receipt['native_execution']='INSTALLED_CCD_DESCRIPTOR_SELECTION_ONLY'
    if any((frozen/PurePosixPath(n)).read_bytes()!=d for n,d in members.items()):raise ValueError('Frozen evidence changed')
    if any((session/'component_controls/sources'/(c['component']+'.cif')).read_bytes()!=runtime[c['path']] for c in controls):raise ValueError('Frozen public control changed')
    if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
    receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
    _json(session/'probe_receipt.json',receipt)
    print('Diagnostic: REVIEW (ReadySet source/descriptor evidence; no ReadySet execution, generation or optimization)',flush=True)
    print('REVIEW ZIP:',_review_zip(session),flush=True);return 2


def _run_readyset_generation_action(args,receipt,session,review,original,members,frozen,runtime,controls,sources,capture,expected):
    from nasolve.cif_readyset_generation_audit import audit_readyset_controls
    from nasolve.cif_readyset_source_audit import verify_readyset_sources
    from nasolve.cif_installed_source_catalogue import verify_installed_sources
    selected={r['component']:sources[r['component']] for r in controls}
    if set(selected)!={'PDU','5PC'}:raise ValueError('This reviewed isolated ReadySet slice requires PDU and 5PC controls')
    all_members,all_frozen=members,frozen
    if json.loads(members['probe_receipt.json'])['delivery_prefix']=='41_Cedar':
        receipt['prior_readyset_generation_replay']=_replay_readyset_generation_return(members,frozen,selected)
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
        frozen=frozen/'inputs/review'
    old=json.loads(members['probe_receipt.json'])
    parent_members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    parent=json.loads(parent_members['probe_receipt.json'])
    triple_members={n.removeprefix('inputs/review/'):d for n,d in parent_members.items() if n.startswith('inputs/review/')}
    receipt['prior_triple_evidence_replay']=_replay_triple_return(triple_members,frozen/'inputs/review/inputs/review',selected)
    receipt['prior_installed_source_replay']=_replay_catalogue_return(parent_members,frozen/'inputs/review',selected)
    receipt['prior_readyset_source_replay']={c:{'selected_smiles':r['selected_smiles'],'matching_descriptors':r['matching_descriptors'],
        'mapped_smiles_graph_comparison':'NOT_RUN'} for c,r in old['readyset_source_audit']['components'].items()}
    receipt['limitations']=['Separate fixed source-seed heavy-atom components; the frozen linked scaffold and its NARestraints policy are not changed.',
        'Selected ReadySet Python API runs with observed eLBOW/template calls; all original arguments/returns/exceptions are forwarded.',
        'AM1 ligand and final hydrogen optimization are disabled; other native internal geometry operations are not instrumented.',
        'Any generated dictionary and its raw chemistry/target differences remain candidates for review; no adoption or convergence claim.',
        'Heavy-only interpretation may retain a full-reference hydrogen-inventory review alongside independently screened triple targets.']
    phenix=None;fingerprints=[];proofs=[]
    if not args.inspect_only:
        from nasolve.phenix_runtime import installation_from_candidate
        from nasolve.cif_elbow_chirality import _library_anchor
        phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
        fingerprints=_fingerprints(phenix,{**capture,'native_validation':expected})
        receipt.update(installed_api_sources=fingerprints,phenix_version=phenix.version)
        verify_readyset_sources(phenix.root,old['readyset_source_audit'],frozen/'readyset_sources')
        verify_installed_sources(phenix.root,parent['installed_source_catalogue'],frozen/'inputs/review/installed_source_catalogue')
        proofmap={r['path']:r for r in old['readyset_source_audit']['sources']};site=_library_anchor(fingerprints)
        for name,digest in {**ELBOW_SOURCE_SHA256,'elbow/utilities/options_parser.py':READYSET_OPTIONS_PARSER_SHA256}.items():
            path=(site/name).as_posix()
            if path in proofmap and proofmap[path]['sha256']!=digest:raise ValueError('Captured ReadySet generator source differs')
            proofmap.setdefault(path,{'anchor':'phenix_installation','path':path,'sha256':digest})
        proofs=list(proofmap.values());receipt['dictionary_generation']='ISOLATED_READYSET_REQUESTED'
    print('Testing separate PDU/5PC ReadySet generation with unchanged native builder arguments.',flush=True)
    report=audit_readyset_controls(selected,session/'readyset_controls',phenix=phenix,api_sources=fingerprints,
        source_proofs=proofs,timeout_seconds=min(args.timeout_seconds,180))
    receipt['readyset_generation_audit']=report;receipt['native_execution']=report['native_execution']
    for code,case in report['cases'].items():
        generation=case['generation'];candidate=generation.get('candidate',{});native=generation.get('result',{})
        print(code,'worker:',generation['execution']['status'],'; ReadySet:',native.get('execution','NOT_RUN'),
            '; output:',candidate.get('classification',candidate.get('status','NOT_RUN')),flush=True)
        if native.get('execution')=='EXCEPTION':print(code,'ReadySet error:',native['exception_type'],native['message'],flush=True)
        for call in generation.get('trace',{}).get('events',[]):
            if call['api']=='ELBOW_BUILDER':
                kw=call['kwargs'];print(code,'builder:',call['status'],'; chemical_component:',kw.get('chemical_component','ABSENT'),
                    '; file:',kw.get('file','ABSENT'),'; smiles supplied:','smiles' in kw,'; opt:',kw.get('opt','ABSENT'),flush=True)
        for label in ['dictionary_triple_screen','native_triple_screen']:
            row=case.get(label,{});print(code,label+':',row.get('target_screen',row.get('status','NOT_RUN')),
                '; linear-axis torsions:',len(row.get('linear_axis_torsions',[])),flush=True)
    if phenix:
        verify_readyset_sources(phenix.root,old['readyset_source_audit'],frozen/'readyset_sources')
        verify_installed_sources(phenix.root,parent['installed_source_catalogue'],frozen/'inputs/review/installed_source_catalogue')
        if _fingerprints(phenix,{**capture,'native_validation':expected})!=fingerprints:raise ValueError('Selected native APIs changed')
    if any((all_frozen/PurePosixPath(n)).read_bytes()!=d for n,d in all_members.items()):raise ValueError('Frozen evidence changed')
    if any((session/'component_controls/sources'/(c['component']+'.cif')).read_bytes()!=runtime[c['path']] for c in controls):raise ValueError('Frozen public control changed')
    if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
    receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
    _json(session/'probe_receipt.json',receipt)
    print('Diagnostic: REVIEW (isolated ReadySet generation/native terms; no scaffold change or adoption)',flush=True)
    print('REVIEW ZIP:',_review_zip(session),flush=True);return 2


def _run_torsion_conditioning_action(args,receipt,session,review,original,members,frozen,controls,sources,numeric_sources,capture,expected):
    from nasolve.cif_dihedral_conditioning import run_native_dihedral_conditioning,dihedral_geometry
    from nasolve.cif_stereochemistry_audit import _values,_graph,_coordinates,audit_candidate_stereochemistry
    selected={r['component']:sources[r['component']] for r in controls}
    if set(selected)!={'PDU','5PC'}:raise ValueError('The reviewed torsion diagnostic requires both explicit controls')
    receipt['prior_readyset_generation_replay']=_replay_readyset_generation_return(members,frozen,selected)
    # Reach C40 through declared wrappers, retaining every original frozen path.
    view,viewroot=members,frozen
    while json.loads(view['probe_receipt.json'])['delivery_prefix'] in {'42_Cedar','41_Cedar'}:
        view={n.removeprefix('inputs/review/'):d for n,d in view.items() if n.startswith('inputs/review/')};viewroot=viewroot/'inputs/review'
    old=json.loads(view['probe_receipt.json']);catalogue={n.removeprefix('inputs/review/'):d for n,d in view.items() if n.startswith('inputs/review/')}
    triple={n.removeprefix('inputs/review/'):d for n,d in catalogue.items() if n.startswith('inputs/review/')}
    receipt['prior_triple_evidence_replay']=_replay_triple_return(triple,viewroot/'inputs/review/inputs/review',selected)
    receipt['prior_installed_source_replay']=_replay_catalogue_return(catalogue,viewroot/'inputs/review',selected)
    receipt['prior_readyset_source_replay']={c:{'selected_smiles':r['selected_smiles'],'matching_descriptors':r['matching_descriptors'],'mapped_smiles_graph_comparison':'NOT_RUN'} for c,r in old['readyset_source_audit']['components'].items()}
    receipt['limitations']=['Original dictionaries, generated chemical-state differences, native restraints and NARestraints authority remain unchanged.',
        'Selected heavy-atom torsions are evaluated at saved source seeds and generated dictionary full/rounded coordinates; no optimizer or model writer runs.',
        'Near-collinearity and sampled derivative evidence do not establish a historical cause or authorize removing restraints.',
        'Public neutral phosphate sources and generated minus-two charge states remain under separate review.']
    phenix=None
    if not args.inspect_only:
        from nasolve.phenix_runtime import installation_from_candidate
        phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
        receipt['installed_api_sources']=_fingerprints(phenix,{**capture,'native_validation':expected});receipt['phenix_version']=phenix.version
    report={'schema_version':1,'policy_id':'cif-native-linear-axis-dihedral-conditioning-v1','status':'REVIEW','cases':{},
        'native_execution':'NOT_RUN','dictionary_generation':'NOT_RUN','readyset':'NOT_RUN','model_optimization':'NOT_RUN',
        'restraint_changes':'NONE','scientific_approval':'NOT_RUN','automatic_adoption':False}
    for code,case in json.loads(members['probe_receipt.json'])['readyset_generation_audit']['cases'].items():
        native=case['native_interpretation']['native_validation'];np=frozen/CEDAR42_NATIVE_PREFIX[code]
        paths={row['role']:np/row['path'] for row in case['native_interpretation']['inputs']}
        dictionary=paths['dictionary'];sv,gv=_values(selected[code],code),_values(dictionary,code)
        se,_,sc,_=_graph(sv);ge,_,gc,_=_graph(gv);family,xyz=_coordinates(gv,source=False)
        atoms=native['atoms'];points=[[float(v) for v in xyz[a['atom_id']]] for a in atoms]
        coordinate_cases={'source_seed_native':[a['xyz'] for a in atoms],'generated_dictionary_full_precision':points,
            'generated_dictionary_pdb_rounded':[[float(f'{v:.3f}') for v in p] for p in points]}
        keys=['i_seqs','angle_ideal','weight','periodicity','alt_angle_ideals','origin_id']
        proxies=[{k:row['native_proxy'][k] for k in keys} for row in case['native_triple_screen']['linear_axis_torsions']]
        state={'source_charge_sum':sum(sc.values()) if all(v is not None for v in sc.values()) else None,
            'generated_charge_sum':sum(gc.values()) if all(v is not None for v in gc.values()) else None,
            'missing_source_atoms':sorted(set(se)-set(ge)),'extra_generated_atoms':sorted(set(ge)-set(se)),
            'source_relative_stereochemistry':audit_candidate_stereochemistry(selected[code],dictionary,code),
            'status':'REVIEW','chemical_state_selection':'NOT_RUN'}
        geometry={label:[dihedral_geometry([p[i] for i in row['i_seqs']]) for row in proxies] for label,p in coordinate_cases.items()}
        item={'candidate_sha256':_sha(dictionary.read_bytes()),'coordinate_origin':family,'coordinate_cases':coordinate_cases,
            'proxies':proxies,'geometry_preflight':geometry,'source_state_review':state,'native':{'status':'NOT_RUN'}}
        report['cases'][code]=item
        print(code,'fixed torsions:',len(proxies),'; source/generated charge:',state['source_charge_sum'],'/',state['generated_charge_sum'],flush=True)
        if phenix:
            print(code,'matching saved native manager before bounded torsion evaluations.',flush=True)
            result=run_native_dihedral_conditioning(paths['model'],dictionary,[paths['phil']],native,coordinate_cases,proxies,numeric_sources,
                session/'torsion_conditioning'/code,phenix.executables['phenix.python'],environment=phenix.environment,
                phenix_version=phenix.version,installation_root=phenix.root,timeout_seconds=min(args.timeout_seconds,180))
            item['native']=result
            if result['status']=='REVIEW':
                for label,row in result['result']['cases'].items():print(code,label,row['summary'],flush=True)
                print(code,'native single/container evaluation pairs:',result['result']['evaluation_pairs'],'/ 3000',flush=True)
            else:print(code,'native conditioning:',result['status'],result.get('error',result['execution']['status']),flush=True)
    if phenix:
        report['native_execution']='ISOLATED_DIHEDRAL_CONDITIONING_ONLY'
        if _fingerprints(phenix,{**capture,'native_validation':expected})!=receipt['installed_api_sources']:raise ValueError('Selected native APIs changed')
    receipt['torsion_conditioning_audit']=report;receipt['native_execution']=report['native_execution']
    if any((frozen/PurePosixPath(n)).read_bytes()!=d for n,d in members.items()) or review.read_bytes()!=original:raise ValueError('Original or frozen evidence changed')
    receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
    _json(session/'torsion_conditioning_receipt.json',report);_json(session/'probe_receipt.json',receipt)
    print('Diagnostic: REVIEW (fixed torsion numerical evidence; no generation, optimization or adoption)',flush=True)
    print('REVIEW ZIP:',_review_zip(session),flush=True);return 2


def _run_linear_torsion_candidate_action(args,receipt,session,review,original,members,frozen,controls,sources,capture,expected):
    from nasolve.cif_linear_torsion_candidate import POLICY_ID,prepare_linear_torsion_candidate,qualify_linear_torsion_candidate
    from nasolve.cif_triple_bond_audit import audit_triple_bonds
    from nasolve.cif_native_validation import inspect_native_bundle
    selected={r['component']:sources[r['component']] for r in controls}
    if set(selected)!={'PDU','5PC'}:raise ValueError('Require both reviewed public controls')
    returned=json.loads(members['probe_receipt.json'])
    receipt['prior_conditioning_replay']=_check_conditioning_return(members,returned)
    nested={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    receipt['prior_readyset_generation_replay']=_replay_readyset_generation_return(nested,frozen/'inputs/review',selected)
    view,viewroot=nested,frozen/'inputs/review'
    while json.loads(view['probe_receipt.json'])['delivery_prefix'] in {'42_Cedar','41_Cedar'}:
        view={n.removeprefix('inputs/review/'):d for n,d in view.items() if n.startswith('inputs/review/')};viewroot=viewroot/'inputs/review'
    catalogue={n.removeprefix('inputs/review/'):d for n,d in view.items() if n.startswith('inputs/review/')}
    triple={n.removeprefix('inputs/review/'):d for n,d in catalogue.items() if n.startswith('inputs/review/')}
    receipt['prior_triple_evidence_replay']=_replay_triple_return(triple,viewroot/'inputs/review/inputs/review',selected)
    receipt['prior_installed_source_replay']=_replay_catalogue_return(catalogue,viewroot/'inputs/review',selected)
    descriptor=json.loads(view['probe_receipt.json'])['readyset_source_audit']['components']
    receipt['prior_readyset_source_replay']={c:{'selected_smiles':r['selected_smiles'],'matching_descriptors':r['matching_descriptors'],
        'mapped_smiles_graph_comparison':'NOT_RUN'} for c,r in descriptor.items()}
    receipt['limitations']=['Separate dictionary candidates omit only torsions containing graph-declared triple-bond angles explicitly targeted at 180 degrees.',
        'Fresh original and candidate native inventories must differ only by the exact planned torsion rows/proxies; no native definition/proxy gate is relaxed.',
        'No energy minimization, model changes, charge/stereo repair, scientific approval or adoption. Other chemical-state and plane findings remain open.',
        'Correct sampled derivatives do not establish useful conditioning or explain the historical floppy PDU observation.']
    phenix=None
    if not args.inspect_only:
        from nasolve.phenix_runtime import installation_from_candidate
        phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
        receipt['installed_api_sources']=_fingerprints(phenix,{**capture,'native_validation':expected});receipt['phenix_version']=phenix.version
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','cases':{},'native_execution':'NOT_RUN',
        'dictionary_generation':'NOT_RUN','readyset':'NOT_RUN','model_optimization':'NOT_RUN','model_editing':'NOT_RUN',
        'scientific_approval':'NOT_RUN','automatic_adoption':False,'restraint_changes':'SEPARATE_CANDIDATE_TORSION_OMISSIONS_ONLY'}
    for code,old in returned['torsion_conditioning_audit']['cases'].items():
        prefix=frozen/CEDAR43_NATIVE_PREFIX[code];saved=json.loads((prefix/'expected_inventory.json').read_text())
        paths={row['role']:prefix/PurePosixPath(row['path']) for row in old['native']['inputs']}
        candidate=session/'linear_torsion_candidates'/code/(code+'_linear_torsion_candidate.cif')
        plan=prepare_linear_torsion_candidate(paths['dictionary'],code,candidate)
        screen=audit_triple_bonds(selected[code],code,dictionary=candidate)
        if plan['removed_torsion_count']!=6 or screen['target_screen']!='PASS' or screen['linear_axis_torsions']:
            raise ValueError('Candidate failed exact omission/triple-target preflight')
        item={'plan':plan,'candidate':{'anchor':'probe_directory','path':candidate.relative_to(session).as_posix(),
            'sha256':_sha(candidate.read_bytes()),'size':candidate.stat().st_size},'dictionary_triple_screen':screen,
            'source_state_review':old['source_state_review'],'original_native':{'status':'NOT_RUN'},'candidate_native':{'status':'NOT_RUN'},
            'native_mechanics':{'status':'NOT_RUN'}};report['cases'][code]=item
        print(code,'separate candidate:',plan['removed_torsion_count'],'torsion rows omitted; triple targets',screen['target_screen'],flush=True)
        if phenix:
            baseline=inspect_native_bundle(paths['model'],[paths['dictionary']],session/'linear_torsion_native/original'/code,
                phenix.executables['phenix.python'],environment=phenix.environment,phenix_version=phenix.version,
                timeout_seconds=min(args.timeout_seconds,60),phil_files=[paths['phil']],inventory_detail='linked',policy_inventory=True)
            item['original_native']=baseline
            fields=['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy','fatal_problems','unused_definitions','unsupported_fields']
            matched=(baseline['status']=='REVIEW' and baseline['execution']['returncode']==0
                and baseline['source_preserved'] and baseline['frozen_inputs_preserved']
                and all(baseline['native_validation'].get(k)==saved.get(k) for k in fields))
            item['original_inventory_matches']=matched
            print(code,'original native inventory:','PASS' if matched else 'REVIEW',flush=True)
            if matched:
                native=inspect_native_bundle(paths['model'],[candidate],session/'linear_torsion_native/candidate'/code,
                    phenix.executables['phenix.python'],environment=phenix.environment,phenix_version=phenix.version,
                    timeout_seconds=min(args.timeout_seconds,60),phil_files=[paths['phil']],inventory_detail='linked',policy_inventory=True)
                item['candidate_native']=native
                if native['status']=='REVIEW' and native['execution']['returncode']==0:
                    item['native_mechanics']=qualify_linear_torsion_candidate(saved,native['native_validation'],plan)
                    item['native_triple_screen']=audit_triple_bonds(selected[code],code,native=native['native_validation'])
                    q=item['native_mechanics'];ns=item['native_triple_screen']
                    if (sum(q['removed_native_proxy_counts'].values())!=3 or ns['target_screen']!='PASS' or ns['linear_axis_torsions']):
                        q['mechanics_checks_pass']=False;q['checks']['triple_targets_and_exact_omission']=False
                    print(code,'exact native omission:','PASS' if q['mechanics_checks_pass'] else 'REVIEW',
                        '; removed',q['removed_native_proxy_counts'],'; triple targets',ns['target_screen'],flush=True)
                else:print(code,'candidate native inventory:',native['status'],native.get('error',''),flush=True)
    if phenix:
        report['native_execution']='ISOLATED_TORSION_OMISSION_INVENTORIES'
        if _fingerprints(phenix,{**capture,'native_validation':expected})!=receipt['installed_api_sources']:raise ValueError('Selected native APIs changed')
    receipt['linear_torsion_candidate_audit']=report;receipt['native_execution']=report['native_execution']
    if any((frozen/PurePosixPath(n)).read_bytes()!=d for n,d in members.items()) or review.read_bytes()!=original:raise ValueError('Original or frozen evidence changed')
    receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
    _json(session/'linear_torsion_candidate_receipt.json',report);_json(session/'probe_receipt.json',receipt)
    print('Diagnostic: REVIEW (separate torsion candidates and exact native delta; no optimization or adoption)',flush=True)
    print('REVIEW ZIP:',_review_zip(session),flush=True);return 2


def _run_linear_torsion_impact_action(args,receipt,session,review,original,members,frozen,controls,sources,capture,expected):
    from nasolve.cif_linear_torsion_impact import POLICY_ID,removed_torsion_references,run_native_linear_torsion_impact
    selected={r['component']:sources[r['component']] for r in controls}
    if set(selected)!={'PDU','5PC'}:raise ValueError('Require both reviewed public controls')
    all_members,all_frozen=members,frozen
    if args.nonbonded_cache_audit_only:
        receipt['prior_impact_replay']=_check_impact_return(members,json.loads(members['probe_receipt.json']))
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')};frozen=frozen/'inputs/review'
    receipt['prior_candidate_replay']=_replay_linear_torsion_candidate_return(members,frozen,selected,session/'candidate_replay')
    c43={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')}
    receipt['prior_conditioning_replay']=_check_conditioning_return(c43,json.loads(c43['probe_receipt.json']))
    generated={n.removeprefix('inputs/review/'):d for n,d in c43.items() if n.startswith('inputs/review/')}
    receipt['prior_readyset_generation_replay']=_replay_readyset_generation_return(generated,frozen/'inputs/review/inputs/review',selected)
    view,viewroot=members,frozen
    while json.loads(view['probe_receipt.json'])['delivery_prefix'] in {'44_Cedar','43_Cedar','42_Cedar','41_Cedar'}:
        view={n.removeprefix('inputs/review/'):d for n,d in view.items() if n.startswith('inputs/review/')};viewroot=viewroot/'inputs/review'
    catalogue={n.removeprefix('inputs/review/'):d for n,d in view.items() if n.startswith('inputs/review/')}
    triple={n.removeprefix('inputs/review/'):d for n,d in catalogue.items() if n.startswith('inputs/review/')}
    receipt['prior_triple_evidence_replay']=_replay_triple_return(triple,viewroot/'inputs/review/inputs/review',selected)
    receipt['prior_installed_source_replay']=_replay_catalogue_return(catalogue,viewroot/'inputs/review',selected)
    descriptor=json.loads(view['probe_receipt.json'])['readyset_source_audit']['components']
    receipt['prior_readyset_source_replay']={c:{'selected_smiles':r['selected_smiles'],'matching_descriptors':r['matching_descriptors'],
        'mapped_smiles_graph_comparison':'NOT_RUN'} for c,r in descriptor.items()}
    receipt['limitations']=['The existing separate candidates are evaluated at exactly the same three saved coordinate cases as their originals.',
        'Numerical deltas must match the saved sum of omitted torsions; all unrelated family targets/gradients and native inventories stay fixed.',
        'A lower gradient norm is descriptive, not required: removal can expose previously cancelling contributions.',
        'No model optimization, chemical-state selection, scaffold change or adoption. Charge/stereo/5PC plane findings remain open.']
    phenix=None
    if not args.inspect_only:
        from nasolve.phenix_runtime import installation_from_candidate
        phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
        receipt['installed_api_sources']=_fingerprints(phenix,{**capture,'native_validation':expected});receipt['phenix_version']=phenix.version
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','cases':{},'native_execution':'NOT_RUN',
        'dictionary_generation':'NOT_RUN','readyset':'NOT_RUN','model_optimization':'NOT_RUN','model_editing':'NOT_RUN',
        'scientific_approval':'NOT_RUN','automatic_adoption':False,'restraint_changes':'NONE; SAVED_SEPARATE_CANDIDATES_EVALUATED'}
    if args.nonbonded_cache_audit_only:
        report['cache_policy_id']='cif-native-nonbonded-cache-proof-v1'
        receipt['limitations']+=['Pair-cache transitions require native single/container proof that changed pairs contribute exactly zero.',
            'The original count failures remain preserved. Only a separate settled-cache retry can pass the unchanged strict impact criteria.']
    prior=json.loads(members['probe_receipt.json'])['linear_torsion_candidate_audit']['cases']
    saved=json.loads(c43['probe_receipt.json'])['torsion_conditioning_audit']['cases']
    for code,c in prior.items():
        old=saved[code];points=old['coordinate_cases'];before=c['original_native']['native_validation'];after=c['candidate_native']['native_validation']
        selected_indices=sorted({i for p in old['proxies'] for i in p['i_seqs']})
        if len(selected_indices)>6:raise ValueError('Selected derivative probes exceed reviewed bound')
        references=removed_torsion_references(old['native']['result'],old['proxies'],before['atom_count'])
        prefix=frozen/CEDAR44_NATIVE_PREFIX[code]['original_native'];paths={v['role']:prefix/v['path'] for v in c['original_native']['inputs']}
        candidate=frozen/c['candidate']['path'];item={'coordinate_cases':points,'selected_indices':selected_indices,
            'removed_references':references,'source_state_review':c['source_state_review'],'candidate_sha256':_sha(candidate.read_bytes()),'native':{'status':'NOT_RUN'}}
        report['cases'][code]=item
        print(code,'fixed-coordinate impact:',len(points),'saved cases;',len(selected_indices),'graph-selected derivative atoms.',flush=True)
        if phenix:
            native=run_native_linear_torsion_impact(paths['model'],paths['dictionary'],candidate,[paths['phil']],{'original':before,'candidate':after},
                points,selected_indices,references,old['native']['result']['installed_numeric_sources'],session/'linear_torsion_impact'/code,
                phenix.executables['phenix.python'],environment=phenix.environment,phenix_version=phenix.version,installation_root=phenix.root,
                timeout_seconds=min(args.timeout_seconds,180),cache_preflight=args.nonbonded_cache_audit_only);item['native']=native
            if native['status']=='REVIEW':
                for label,row in native['result']['cases'].items():
                    if 'cache_preflight' in row:
                        cache=row['cache_preflight'];print(code,label,'cache proof:','PASS' if cache['checks_pass'] else 'REVIEW',
                            '; membership stable:',cache['post_preflight_membership_stable'],flush=True)
                    if 'baselines' not in row:
                        print(code,label,'strict impact NOT_RUN: cache preflight requires review.',flush=True);continue
                    b=row['baselines'];print(code,label,'numerical checks:','PASS' if row['numerical_checks_pass'] else 'REVIEW',
                        '; full gradient norm:',b['original']['all']['gradient_norm'],'->',b['candidate']['all']['gradient_norm'],flush=True)
                print(code,'native energy evaluations:',native['result']['evaluation_calls'],'/ 2000',flush=True)
                if args.nonbonded_cache_audit_only:print(code,'native pair kernels:',native['result']['pair_kernel_calls'],'/ 5000',flush=True)
            else:print(code,'native impact:',native['status'],native.get('error',native['execution']['status']),flush=True)
    if phenix:
        report['native_execution']='ISOLATED_FIXED_COORDINATE_TORSION_IMPACT'
        if _fingerprints(phenix,{**capture,'native_validation':expected})!=receipt['installed_api_sources']:raise ValueError('Selected native APIs changed')
    receipt['linear_torsion_impact_audit']=report;receipt['native_execution']=report['native_execution']
    if any((all_frozen/PurePosixPath(n)).read_bytes()!=d for n,d in all_members.items()) or review.read_bytes()!=original:raise ValueError('Original or frozen evidence changed')
    receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
    _json(session/'linear_torsion_impact_receipt.json',report);_json(session/'probe_receipt.json',receipt)
    print('Diagnostic: REVIEW (fixed-coordinate numerical impact; no optimization or adoption)',flush=True)
    print('REVIEW ZIP:',_review_zip(session),flush=True);return 2


def _run_source_constructor_action(args,receipt,session,review,original,members,frozen,sources,capture,expected):
    from nasolve.cif_elbow_input import prepare_elbow_source_dialect_input
    from nasolve.cif_source_constructor import audit_source_constructor,verify_constructor_capture,PRIOR_PATHS,POLICY_ID,BACKEND_POLICY_ID
    from nasolve.cif_source_reader import verify_source_reader_capture
    from nasolve.cif_elbow_chirality import verify_chirality_sources
    if set(sources)!={'DP','PDU','5PC'}:raise ValueError('Require the reviewed DP source and both public constructor controls')
    all_members,all_frozen=members,frozen;old_constructor=None;setup=args.source_constructor_setup_audit_only;index=args.source_constructor_index_basis_audit_only or setup;integer_keys=setup or index and json.loads(members['probe_receipt.json'])['delivery_prefix']=='51_Cedar';mapping=args.source_constructor_mapping_audit_only or index;trace=args.source_constructor_trace_audit_only or mapping;backend=args.source_constructor_backend_audit_only or trace
    if backend:
        old_constructor=json.loads(members['probe_receipt.json'])['source_constructor_audit']
        receipt['prior_constructor_replay']=(_check_constructor_trace_return(members,json.loads(members['probe_receipt.json']),mapping=index,index=integer_keys,integer_keys=setup) if mapping
            else _check_constructor_return(members,json.loads(members['probe_receipt.json']),backend=trace))
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')};frozen=frozen/'inputs/review'
    if setup:
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')};frozen=frozen/'inputs/review'
    if integer_keys:
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')};frozen=frozen/'inputs/review'
    if index:
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')};frozen=frozen/'inputs/review'
    if mapping:
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')};frozen=frozen/'inputs/review'
    if trace:
        members={n.removeprefix('inputs/review/'):d for n,d in members.items() if n.startswith('inputs/review/')};frozen=frozen/'inputs/review'
    receipt['prior_cache_impact_replay']=_check_impact_return(members,json.loads(members['probe_receipt.json']),cache=True)
    charge_members,charge_root=members,frozen
    while json.loads(charge_members['probe_receipt.json'])['delivery_prefix']!='37_Cedar':
        charge_members={n.removeprefix('inputs/review/'):d for n,d in charge_members.items() if n.startswith('inputs/review/')}
        charge_root=charge_root/'inputs/review'
    old_readers=json.loads(charge_members['probe_receipt.json'])['source_reader_audits']
    stereo_members,stereo_prefix=_source_reader_evidence(members);stereo_root=frozen/PurePosixPath(stereo_prefix)
    old_stereo=json.loads(stereo_members['probe_receipt.json'])['installed_chirality_controls']
    source_proof={row['path']:row for row in old_readers['DP']['sources']}
    source_proof.update({row['path']:row for row in old_stereo['DP']['sources']
        if row['path'].endswith(('/elbow/chemistry/TopologyMixins.py','/elbow/chemistry/ChiralClass.py'))})
    if len(source_proof)!=len(PRIOR_PATHS):raise ValueError('Incomplete saved constructor source proof')
    receipt['consumer_preparations']={};receipt['limitations']=[
        'Only temporary source reader, explicit declared-charge control, native class promotion and Chiralise are requested.',
        'Native Chiralise can optimize local chiral templates internally; those transitive operations are not instrumented.',
        'Source-relative signed volumes are not an independent absolute CIP assignment or complete builder qualification.',
        'No numerical dictionary generation, whole-molecule optimization request, scaffold change, new pairing/stacking policy or adoption.']
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','cases':{},'native_execution':'NOT_RUN',
        'dictionary_generation':'NOT_RUN','whole_molecule_optimization':'NOT_REQUESTED','model_editing':'NOT_RUN',
        'constructor_local_optimization':'NATIVE_INTERNALS_NOT_INSTRUMENTED','absolute_cip_assignment':'NOT_RUN','automatic_adoption':False}
    if backend:
        report.update(backend_policy_id=BACKEND_POLICY_ID,native_backend_selection='EXPLICIT_NATIVE_CCTBX')
        receipt['limitations'].append('The native reader CCTBX backend is explicitly selected before construction; its setter/getter sources and exact state delta are captured.')
    if trace:
        from nasolve.cif_constructor_trace import POLICY_ID as TRACE_POLICY
        report.update(trace_policy_id=TRACE_POLICY,observer_control='FRESH_UNOBSERVED_AND_OBSERVED_RUNS',native_internal_observation='METHOD_BOUNDARIES_ONLY')
        receipt['limitations'][1]='Local chiral-template method boundaries are observed; transitive optimizer kernels and other native internals are not instrumented.'
        receipt['limitations'].append('Method boundaries are observed without changing arguments or native kernels. First observed sign changes are not a causal defect or absolute CIP verdict; unobserved versus observed repeats are reported separately without resetting native random state.')
    if mapping:
        from nasolve.cif_constructor_mapping import POLICY_ID as MAPPING_POLICY
        report['mapping_policy_id']=MAPPING_POLICY
        if index:
            from nasolve.cif_constructor_index_basis import POLICY_ID as INDEX_POLICY,INTEGER_KEYS_POLICY_ID
            report['index_policy_id']=INTEGER_KEYS_POLICY_ID if integer_keys else INDEX_POLICY
            receipt['limitations'].append('Native restraint dictionary atom keys and returned vectors prove a named restraint order; coordinate getter order stays separate. Preserve legacy mapping/hand/metadata reviews and both source-sign interpretations; no native reindexing or chemical repair.')
        receipt['limitations'].append('Local coordinate getters/setters, native chirality proxy bases and post-optimizer index transfers are observed. Parent atoms may occupy different temporary frames; this is not a completed molecule or a causal-bug verdict. Existing metadata/hand gates remain active.')
    if setup:
        from nasolve.cif_constructor_setup import POLICY_ID as SETUP_POLICY
        report['setup_policy_id']=SETUP_POLICY
        receipt['limitations'].append('Call selected native Setup once before construction, following the captured builder sequence. Input-coordinate caching is preparation, not a full builder or a change to native targets/kernels. Original baseline findings remain preserved.')
    phenix=None
    if not args.inspect_only:
        from nasolve.phenix_runtime import installation_from_candidate
        phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
        receipt['installed_api_sources']=_fingerprints(phenix,{**capture,'native_validation':expected});receipt['phenix_version']=phenix.version
        if backend:
            for code,c in old_constructor['cases'].items():verify_constructor_capture(phenix.root,c['native'],all_frozen/c['native']['directory']['path'])
        for code,row in old_readers.items():verify_source_reader_capture(phenix.root,row,charge_root/row['directory']['path'])
        for code,row in old_stereo.items():verify_chirality_sources(phenix.root,row,stereo_root/row['directory']['path'])
    print('Testing the source-native reader, declared-charge transfer and temporary chiral constructor.',flush=True)
    for code,source in sources.items():
        consumer=session/'consumer_preview'/code/'source.cif'
        prepared=prepare_elbow_source_dialect_input(source,session/'graph_preview'/code/'source.cif',code,consumer)
        receipt['consumer_preparations'][code]=prepared
        if backend and _sha(consumer.read_bytes())!=old_constructor['cases'][code]['consumer']['sha256']:raise ValueError('Backend retry must start from the original source, not failed temporary coordinates')
        if code in old_readers and _sha(consumer.read_bytes())!=old_readers[code]['source_sha256']:raise ValueError('Constructor input differs from the qualified source reader input')
        item={'consumer':{'anchor':'probe_directory','path':consumer.relative_to(session).as_posix(),
            'sha256':_sha(consumer.read_bytes()),'size':consumer.stat().st_size},'reader_dialect':prepared['consumer_reader_dialect'],'native':{'status':'NOT_RUN'}}
        report['cases'][code]=item
        if trace:item['control_native']={'status':'NOT_RUN'}
        print(code,'source constructor input:',item['reader_dialect'],flush=True)
        if phenix:
            if trace:
                control_output=session/'source_constructor_control'/code
                control=audit_source_constructor(phenix.root,phenix.executables['phenix.python'],receipt['installed_api_sources'],consumer,code,control_output,
                    environment=phenix.environment,expected_dialect=item['reader_dialect'],prior_sources=list(source_proof.values()),timeout_seconds=min(args.timeout_seconds,30),native_cctbx=True,source_setup=setup,setup_reference_sha256=ELBOW_SOURCE_SHA256['elbow/command_line/builder.py'] if setup else None)
                item['control_native']={'directory':{'anchor':'probe_directory','path':control_output.relative_to(session).as_posix()},**control}
            output=session/'source_constructor'/code
            trace_sources=([r for r in old_constructor['cases'][code]['native']['sources'] if r['path'].endswith('/elbow/chemistry/ChiralClass.py')]
                +old_constructor['cases'][code]['native']['result']['backend_control']['sources']) if trace else ()
            native=audit_source_constructor(phenix.root,phenix.executables['phenix.python'],receipt['installed_api_sources'],consumer,code,output,
                environment=phenix.environment,expected_dialect=item['reader_dialect'],prior_sources=list(source_proof.values()),timeout_seconds=min(args.timeout_seconds,30 if trace else 60),native_cctbx=backend,trace_chirality=trace,trace_sources=trace_sources,coordinate_mapping=mapping,index_basis=index,integer_keys=integer_keys,source_setup=setup,setup_reference_sha256=ELBOW_SOURCE_SHA256['elbow/command_line/builder.py'] if setup else None)
            item['native']={'directory':{'anchor':'probe_directory','path':output.relative_to(session).as_posix()},**native}
            if trace:
                from nasolve.cif_constructor_trace import compare_constructor_runs
                item['observer_comparison']=compare_constructor_runs(control,native,old_constructor['cases'][code]['native'])
                print(code,'fresh observer comparison:',item['observer_comparison']['status'],flush=True)
                analysis=native.get('trace_analysis',{})
                print(code,'observed native calls:',analysis.get('call_count',0),'; trace:',analysis.get('status','NOT_RUN'),flush=True)
                for row in analysis.get('first_observed_hand_reviews',[]):print(code,row['centre'],'first observed review:',row['method'],row['phase'],flush=True)
                if mapping:
                    mq=native.get('mapping_analysis',{})
                    print(code,'local coordinate mapping:',mq.get('status','NOT_RUN'),'; native target/source signs:',mq.get('target_source_hands_preserved','NOT_RUN'),flush=True)
                    for row in mq.get('post_optimizer_transfers',[]):print(code,row['centre'],'sorted-index transfer:',row['matches_sorted_index_transfer'],'; local hand before/after:',row['local_source_hand_before'],row['local_source_hand_after'],flush=True)
            if setup:
                sq=native.get('setup_analysis',{})
                print(code,'native input setup:',sq.get('status','NOT_RUN'),'; cached source coordinates retained after constructor:',sq.get('cached_input_coordinates_preserved_after_constructor','NOT_RUN'),flush=True)
                print(code,'previous unprepared endpoint match:',item['observer_comparison']['previous_endpoint_match'],flush=True)
            if index:
                iq=native.get('index_analysis',{})
                print(code,'named restraint-index proof:',iq.get('status','NOT_RUN'),'; source target signs:',iq.get('target_source_hands_preserved','NOT_RUN'),flush=True)
                for row in iq.get('managers',[]):print(code,row['centre'],'restraint/evaluation order identical:',row['orders_identical'],'; source target signs:',row['target_source_hands_preserved'],flush=True)
            if native['status']=='REVIEW':
                q=native['qualification'];print(code,'native constructor:',q['constructor_status'],'; source handoff:',q['status'],flush=True)
                failed=[k for k,v in q['checks'].items() if not v]
                if failed:print(code,'handoff checks requiring review:',', '.join(failed),flush=True)
            else:print(code,'native constructor worker:',native['status'],native.get('error',native['execution']['status']),flush=True)
    if phenix:
        report['native_execution']='SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INPUT_SETUP' if setup else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS' if index else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_MAPPING' if mapping else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_TRACE' if trace else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_HANDOFF' if backend else 'SOURCE_NATIVE_CONSTRUCTOR_HANDOFF'
        for code,c in report['cases'].items():
            if c['native']['status']=='REVIEW':verify_constructor_capture(phenix.root,c['native'],session/c['native']['directory']['path'])
            if trace and c['control_native']['status']=='REVIEW':verify_constructor_capture(phenix.root,c['control_native'],session/c['control_native']['directory']['path'])
        for code,row in old_readers.items():verify_source_reader_capture(phenix.root,row,charge_root/row['directory']['path'])
        for code,row in old_stereo.items():verify_chirality_sources(phenix.root,row,stereo_root/row['directory']['path'])
        if _fingerprints(phenix,{**capture,'native_validation':expected})!=receipt['installed_api_sources']:raise ValueError('Selected native APIs changed')
    receipt['source_constructor_audit']=report;receipt['native_execution']=report['native_execution']
    if any((all_frozen/PurePosixPath(n)).read_bytes()!=d for n,d in all_members.items()) or review.read_bytes()!=original:raise ValueError('Original/frozen constructor prerequisite changed')
    receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
    _json(session/'source_constructor_receipt.json',report);_json(session/'probe_receipt.json',receipt)
    print('Diagnostic: REVIEW (source-native constructor handoff; full generation and scientific qualification remain open)',flush=True)
    print('REVIEW ZIP:',_review_zip(session),flush=True);return 2


def _check_constructor_input_mode(args,delivery):
    """Keep each supported constructor action bound to its reviewed input scope."""
    scopes={
        'source_constructor_audit_only':('46_Cedar',),
        'source_constructor_backend_audit_only':('47_Cedar',),
        'source_constructor_trace_audit_only':('48_Cedar',),
        'source_constructor_mapping_audit_only':('49_Cedar',),
        'source_constructor_index_basis_audit_only':('50_Cedar','51_Cedar'),
        'source_constructor_setup_audit_only':('52_Cedar',),
    }
    for option,inputs in scopes.items():
        if bool(getattr(args,option,False))!=(delivery in inputs):
            raise ValueError('Input '+delivery+' requires the matching explicit constructor action; mismatched '+option)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    default_review={
        '53_Cedar':'NASolve-live-tests/52_Cedar_cif-numerical-recovery-rjkwfcxk/52_Cedar_rjkwfcxk_cif_numerical_recovery_review.zip',
        '52_Cedar':'NASolve-live-tests/51_Cedar_cif-numerical-recovery-lnlj_8_6/51_Cedar_lnlj_8_6_cif_numerical_recovery_review.zip',
        '51_Cedar':'NASolve-live-tests/50_Cedar_cif-numerical-recovery-g03y7p0_/50_Cedar_g03y7p0__cif_numerical_recovery_review.zip',
        '50_Cedar':'NASolve-live-tests/49_Cedar_cif-numerical-recovery-izfiw4xk/49_Cedar_izfiw4xk_cif_numerical_recovery_review.zip',
        '49_Cedar':'NASolve-live-tests/48_Cedar_cif-numerical-recovery-5u8wjea_/48_Cedar_5u8wjea__cif_numerical_recovery_review.zip',
        '48_Cedar':'NASolve-live-tests/47_Cedar_cif-numerical-recovery-eq2g8v23/47_Cedar_eq2g8v23_cif_numerical_recovery_review.zip',
        '47_Cedar':'NASolve-live-tests/46_Cedar_cif-numerical-recovery-g9lvlci6/46_Cedar_g9lvlci6_cif_numerical_recovery_review.zip',
        '46_Cedar':'NASolve-live-tests/45_Cedar_cif-numerical-recovery-y8dnomjz/45_Cedar_y8dnomjz_cif_numerical_recovery_review.zip',
        '45_Cedar':'NASolve-live-tests/44_Cedar_cif-numerical-recovery-q8nw_af7/44_Cedar_q8nw_af7_cif_numerical_recovery_review.zip',
        '44_Cedar':'NASolve-live-tests/43_Cedar_cif-numerical-recovery-vitgl_98/43_Cedar_vitgl_98_cif_numerical_recovery_review.zip',
        '43_Cedar':'NASolve-live-tests/42_Cedar_cif-numerical-recovery-9s73mlh5/42_Cedar_9s73mlh5_cif_numerical_recovery_review.zip',
        '42_Cedar':'NASolve-live-tests/41_Cedar_cif-numerical-recovery-ofvcwzhl/41_Cedar_ofvcwzhl_cif_numerical_recovery_review.zip',
        '41_Cedar':'NASolve-live-tests/40_Cedar_cif-numerical-recovery-qnxdgivs/40_Cedar_qnxdgivs_cif_numerical_recovery_review.zip',
        '40_Cedar':'NASolve-live-tests/39_Cedar_cif-numerical-recovery-eum3w071/39_Cedar_eum3w071_cif_numerical_recovery_review.zip',
        '39_Cedar':'NASolve-live-tests/38_Cedar_cif-numerical-recovery-cg3nw4as/38_Cedar_cg3nw4as_cif_numerical_recovery_review.zip',
        '38_Cedar':'NASolve-live-tests/37_Cedar_cif-numerical-recovery-p7r95lko/37_Cedar_p7r95lko_cif_numerical_recovery_review.zip',
        '37_Cedar':'NASolve-live-tests/36_Cedar_cif-numerical-recovery-0_8wztk9/36_Cedar_0_8wztk9_cif_numerical_recovery_review.zip',
        '36_Cedar':'NASolve-live-tests/35_Cedar_cif-numerical-recovery-7c32qo4g/35_Cedar_7c32qo4g_cif_numerical_recovery_review.zip',
        '35_Cedar':'NASolve-live-tests/34_Cedar_cif-numerical-recovery-6j6_ppxr/34_Cedar_6j6_ppxr_cif_numerical_recovery_review.zip',
        '34_Cedar':'NASolve-live-tests/33_Cedar_cif-numerical-recovery-sw8kmgch/33_Cedar_sw8kmgch_cif_numerical_recovery_review.zip',
        '33_Cedar':'NASolve-live-tests/32_Cedar_cif-numerical-recovery-h_lbxjqc/32_Cedar_h_lbxjqc_cif_numerical_recovery_review.zip',
        '32_Cedar':'NASolve-live-tests/31_Cedar_cif-numerical-recovery-95asqu3e/31_Cedar_95asqu3e_cif_numerical_recovery_review.zip',
        '31_Cedar':'NASolve-live-tests/30_Cedar_cif-numerical-recovery-_ixms4r3/30_Cedar__ixms4r3_cif_numerical_recovery_review.zip',
    }.get(BUNDLE['delivery_prefix'],'NASolve-live-tests/29_Cedar_cif-base-rotation-94wuz090/29_Cedar_94wuz090_cif_base_rotation_review.zip')
    parser.add_argument('--review-zip',type=Path,default=Path.home()/default_review)
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--component',action='append',help='Explicit component candidate selection; this reviewed slice defaults to DP')
    parser.add_argument('--timeout-seconds',type=int,default=600)
    parser.add_argument('--inspect-only',action='store_true')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--native-contract-only',action='store_true',
                        help='Capture installed eLBOW sources and run read-only input checks; do not generate dictionaries')
    mode.add_argument('--single-block-steps',type=int,
                      help='Use verified Cedar 32 source semantics for one explicit bounded eLBOW block (1--600 steps)')
    mode.add_argument('--stereochemistry-audit-only',action='store_true',
                      help='Audit the saved Cedar 33 candidate and installed reader chirality; no numerical generation')
    mode.add_argument('--source-dialect-audit-only',action='store_true',
                      help='Preserve the original reader dialect and inspect native parsed inventory; no constructor or generation')
    mode.add_argument('--triple-bond-audit-only',action='store_true',
                      help='Audit installed component lookup and active triple-bond terms at fixed isolated seed coordinates; no generation')
    mode.add_argument('--installed-source-audit-only',action='store_true',
                      help='Read installed CCD/source metadata and direct/canonical monomer controls; no ReadySet or generation')
    mode.add_argument('--readyset-source-audit-only',action='store_true',
                      help='Capture installed ReadySet source text and native CCD SMILES selection; no ReadySet execution or generation')
    mode.add_argument('--readyset-generation-audit-only',action='store_true',
                      help='Run isolated heavy-atom ReadySet controls with observed eLBOW calls and candidate triple-proxy checks')
    mode.add_argument('--torsion-conditioning-audit-only',action='store_true',
                      help='Evaluate saved generated torsions under fixed native definitions; no ReadySet, generation or optimization')
    mode.add_argument('--linear-torsion-candidate-only',action='store_true',
                      help='Prepare separate graph-declared linear-torsion omission candidates and check exact native inventory deltas')
    mode.add_argument('--linear-torsion-impact-only',action='store_true',
                      help='Compare saved original/candidate numerical contributions at identical coordinates; no optimizer or generation')
    mode.add_argument('--nonbonded-cache-audit-only',action='store_true',
                      help='Prove zero-contribution pair-cache transitions, then repeat strict fixed-coordinate numerical checks')
    mode.add_argument('--source-constructor-setup-audit-only',action='store_true',
                      help='Use the selected native builder input-coordinate Setup before isolated construction after exact Cedar 52 replay')
    mode.add_argument('--source-constructor-index-basis-audit-only',action='store_true',
                      help='Prove native named restraint-array order after exact Cedar 50/51 replay; C51 uses integer-key/link evidence, extra controls remain read-only')
    mode.add_argument('--source-constructor-mapping-audit-only',action='store_true',
                      help='Observe named local coordinate/native chirality mapping after exact Cedar 49 replay')
    mode.add_argument('--source-constructor-trace-audit-only',action='store_true',
                      help='Observe local chiral boundaries after exact Cedar 48 replay; compare fresh unobserved/observed runs')
    mode.add_argument('--source-constructor-backend-audit-only',action='store_true',
                      help='Retry exact Cedar 47 original sources with the native reader CCTBX backend')
    mode.add_argument('--source-constructor-audit-only',action='store_true',
                      help='Test the source-native reader/declared-charge/chiral-constructor handoff; no dictionary generation')
    parser.add_argument('--declared-charge-control',action='store_true',
                        help='Explicitly test source-declared charges on the temporary native component, retaining raw reader evidence')
    args=parser.parse_args()
    constructor_action=args.source_constructor_setup_audit_only or args.source_constructor_audit_only or args.source_constructor_backend_audit_only or args.source_constructor_trace_audit_only or args.source_constructor_mapping_audit_only or args.source_constructor_index_basis_audit_only;session=None;review=None;original=None;members=None
    receipt={'schema_version':1,'kind':'cif-source-graph-numerical-recovery-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','native_proxy_validation':'NOT_RUN','linked_site_validation':'NOT_RUN',
        'model_editing':'NOT_RUN','model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','policy_recompilation':'NOT_RUN',
        'readyset_retry':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'diffraction_data':'NOT_READ','policy_authority':'NARestraints','installed_phenix_edits':'NOT_RUN',
        'requested_action':'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INPUT_SETUP' if args.source_constructor_setup_audit_only else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS' if args.source_constructor_index_basis_audit_only else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_MAPPING' if args.source_constructor_mapping_audit_only else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_TRACE' if args.source_constructor_trace_audit_only else 'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_HANDOFF' if args.source_constructor_backend_audit_only else 'SOURCE_NATIVE_CONSTRUCTOR_HANDOFF' if args.source_constructor_audit_only else 'ISOLATED_NONBONDED_CACHE_PROOF_AND_IMPACT' if args.nonbonded_cache_audit_only else 'ISOLATED_LINEAR_TORSION_NUMERICAL_IMPACT' if args.linear_torsion_impact_only else 'ISOLATED_LINEAR_TORSION_CANDIDATE' if args.linear_torsion_candidate_only else 'ISOLATED_DIHEDRAL_CONDITIONING_AUDIT' if args.torsion_conditioning_audit_only else 'ISOLATED_READYSET_GENERATION_AUDIT' if args.readyset_generation_audit_only else 'READYSET_SOURCE_AND_DESCRIPTOR_AUDIT' if args.readyset_source_audit_only else 'INSTALLED_MONOMER_CCD_SOURCE_AUDIT' if args.installed_source_audit_only else 'INSTALLED_TRIPLE_BOND_AUDIT' if args.triple_bond_audit_only else 'SOURCE_DIALECT_DECLARED_CHARGE_CONTROL' if args.declared_charge_control else 'SOURCE_DIALECT_READER_AUDIT' if args.source_dialect_audit_only else 'READ_ONLY_STEREOCHEMISTRY_AUDIT' if args.stereochemistry_audit_only else 'NATIVE_READ_ONLY_CONTRACT' if args.native_contract_only else 'SINGLE_BLOCK_NUMERICAL_GENERATION' if args.single_block_steps is not None else 'INDEPENDENT_NUMERICAL_GENERATION',
        'limits':{'max_components':3,'generation_timeout_per_component':args.timeout_seconds,'read_only_timeout_per_component':min(args.timeout_seconds,60),
                  'single_block_steps':args.single_block_steps},
        'limitations':['Separate dictionary candidates only; none is applied to a native manager or model.',
            'All original numerical targets remain in the frozen source. Replacement targets come only from independent generation.',
            'Declared source coordinates seed naming/initial geometry, not final restraint targets or independent validation.',
            'Chemical-state preservation, numerical checks, native proxy qualification and scientific approval are separate gates.',
            'Existing modifiers, pairing and stacking policy are recorded and unchanged; no modifier composition is attempted.']}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid timeout bound')
        if args.single_block_steps is not None and not 1<=args.single_block_steps<=600:raise ValueError('Invalid single-block step bound')
        components=args.component or ['DP']
        if not 1<=len(components)<=3 or len(set(components))!=len(components):raise ValueError('Require one to three unique explicit components')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        # Current bundled code is the only executable authority. Capsule Python
        # files are frozen evidence and are never imported or executed.
        parent.mkdir(parents=True,exist_ok=True);session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-numerical-recovery-',dir=parent))
        _materialize(runtime,session/'runtime');sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        members,qualified,prior,rotation,original=_read_capsule(review);_materialize(members,session/'inputs/review');frozen=session/'inputs/review'
        source_members,source_prefix=_source_view(members);source_root=frozen/PurePosixPath(source_prefix) if source_prefix else frozen
        reader_members,reader_prefix=_source_reader_evidence(members);reader_root=frozen/PurePosixPath(reader_prefix) if reader_prefix else frozen
        if source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='30_Cedar':
            previous_generation=json.loads(members['probe_receipt.json'])
            receipt['previous_generation']={'delivery_prefix':'30_Cedar','status':'FAILED_NO_CANDIDATE','phase':'INPUT_PARSER','native_returncode':1,
                'chemical_rejection':'NOT_ASSESSED','numerical_reviews':'NOT_ASSESSED','evidence':{'anchor':'probe_directory','path':'inputs/review/'+CEDAR30_GENERATION_PREFIX+'/elbow.log'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='31_Cedar':
            receipt['previous_generation']={'delivery_prefix':'31_Cedar','status':'FAILED_NO_CANDIDATE',
                'cases':{code:{'phase':'INPUT_PARSER_MISSING_ALT_ATOM_ID' if code=='DP' else 'OPTIMIZER_RESTART_EMPTY_XYZ_UNBOUND_LOCAL',
                    'native_returncode':1,'chemical_rejection':'NOT_ASSESSED','numerical_reviews':'NOT_ASSESSED',
                    'evidence':{'anchor':'probe_directory','path':'inputs/review/'+prefix+'/generation/'+generatedir+'/elbow.log'}}
                    for code,(prefix,generatedir,_) in CEDAR31_CASES.items()},
                'pickle_evidence':'EXCLUDED_BY_PRIOR_SHUTTLE_NOT_LOADED'}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='52_Cedar':
            receipt['previous_execution']={'delivery_prefix':'52_Cedar','native_execution':'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS',
                'index_status':'NINE_NATIVE_INTEGER_BINDINGS_PASS; EIGHT_SOURCE_TARGET_SIGNS_AGREE; DP_C1_PRIME_REVIEW',
                'constructor_status':'SIX_COMPLETED; FRESH_AND_PREVIOUS_ENDPOINTS_MATCH',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='51_Cedar':
            receipt['previous_execution']={'delivery_prefix':'51_Cedar','native_execution':'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_INDEX_BASIS',
                'constructor_status':'SIX_COMPLETED; FRESH_AND_PREVIOUS_ENDPOINTS_MATCH',
                'index_status':'NINE_EMPTY_ATOM_KEY_CAPTURES; NATIVE_KEYS_ARE_INTEGERS; OLD_FINDINGS_PRESERVED',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='50_Cedar':
            receipt['previous_execution']={'delivery_prefix':'50_Cedar','native_execution':'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_MAPPING',
                'constructor_status':'SIX_COMPLETED; THREE_FRESH_COMPARISONS_AND_PREVIOUS_ENDPOINTS_MATCH',
                'mapping_status':'18_GETTERS_AND_9_SETTERS_PASS; 9_SORTED_TRANSFERS_MATCH; PROXY_BASIS_REVIEW',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='49_Cedar':
            receipt['previous_execution']={'delivery_prefix':'49_Cedar','native_execution':'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_TRACE',
                'constructor_status':'SIX_COMPLETED; THREE_FRESH_COMPARISONS_MATCH; SOURCE_HANDEDNESS_REVIEW',
                'trace_status':'PDU_AND_5PC_OBSERVATION_REPLAY_PASS; DP_CHEMICAL_METADATA_REVIEW',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='48_Cedar':
            receipt['previous_execution']={'delivery_prefix':'48_Cedar','native_execution':'SOURCE_NATIVE_CCTBX_CONSTRUCTOR_HANDOFF',
                'constructor_status':'THREE_COMPLETED; SOURCE_HANDEDNESS_REVIEW',
                'backend_and_other_gates':'ALL_PASS; ORIGINAL_HAND_FINDINGS_PRESERVED',
                'failed_centres':{'DP':["C1'"],'PDU':["C1'","C3'","C4'"],'5PC':["C1'"]},
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='47_Cedar':
            receipt['previous_execution']={'delivery_prefix':'47_Cedar','native_execution':'SOURCE_NATIVE_CONSTRUCTOR_HANDOFF',
                'constructor_status':'THREE_EXCEPTIONS; CCTBX_BACKEND_NOT_SELECTED',
                'DP_PDU':'NOT_CHIRALISED; PARTIAL_COORDINATES_NOT_REUSED','5PC':'MISSING_LEGACY_OPTIMISEBFGS; PARTIAL_COORDINATES_NOT_REUSED',
                'raw_graph_charge_checks':'PASS; ORIGINAL_FAILURES_PRESERVED',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='46_Cedar':
            receipt['previous_execution']={'delivery_prefix':'46_Cedar','cache_proof':'BOTH_CONTROLS_ALL_THREE_CASES_PASS',
                'strict_numerical_retry':'ALL_SIX_CASES_PASS','chemical_state':'REVIEW; UNCHANGED',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='45_Cedar':
            receipt['previous_execution']={'delivery_prefix':'45_Cedar','native_execution':'ISOLATED_FIXED_COORDINATE_TORSION_IMPACT',
                'PDU':'ALL_THREE_CASES_PASS','5PC':'TWO_COUNT_REVIEW_CASES; ENERGY_GRADIENT_AND_DERIVATIVE_ARITHMETIC_PASS',
                'chemical_state':'REVIEW; UNCHANGED','evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='44_Cedar':
            receipt['previous_execution']={'delivery_prefix':'44_Cedar','native_execution':'ISOLATED_TORSION_OMISSION_INVENTORIES',
                'exact_native_omission':'BOTH_PASS; SIX_DEFINITION_ROWS_THREE_ACTIVE_PROXIES_EACH',
                'triple_targets':'BOTH_PASS; ALL_UNRELATED_TERMS_UNCHANGED','chemical_state':'REVIEW; UNCHANGED',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='43_Cedar':
            receipt['previous_execution']={'delivery_prefix':'43_Cedar','native_execution':'ISOLATED_DIHEDRAL_CONDITIONING_ONLY',
                'sampled_derivatives':'BOTH_CONTROLS_ALL_THREE_SAVED_CASES_PASS','near_collinear_torsions':'THREE_EACH_REMAIN_REVIEW',
                'chemical_state':'SOURCE_NEUTRAL_TO_GENERATED_MINUS_TWO_REMAINS_REVIEW',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='42_Cedar':
            receipt['previous_execution']={'delivery_prefix':'42_Cedar','readyset_execution':'BOTH_COMPLETED',
                'triple_target_screens':'BOTH_DICTIONARY_AND_NATIVE_PASS','linear_axis_torsions':'SIX_DICTIONARY_THREE_HEAVY_NATIVE_EACH',
                'chemical_state':'SOURCE_NEUTRAL_TO_GENERATED_MINUS_TWO_REMAINS_REVIEW',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='41_Cedar':
            receipt['previous_execution']={'delivery_prefix':'41_Cedar','worker_processes':'COMPLETED',
                'readyset_execution':'BOTH_SYSTEMEXIT_2_NESTED_OPTIONS_PARSER','surviving_cifs':'UNCHANGED_PUBLIC_SOURCE_COPIES',
                'native_triple_screens':'NOT_RUN','historical_floppy_geometry_cause':'NOT_ESTABLISHED',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='40_Cedar':
            receipt['previous_execution']={'delivery_prefix':'40_Cedar','native_execution':'INSTALLED_CCD_DESCRIPTOR_SELECTION_ONLY',
                'selected_descriptors':'BOTH_CACTVS_SMILES_CANONICAL','readyset_execution':'NOT_RUN',
                'static_source_files':24,'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='39_Cedar':
            receipt['previous_execution']={'delivery_prefix':'39_Cedar','installed_monomers':'BOTH_DIRECT_AND_WRAPPED_MISSING',
                'installed_CCDs':'EXACT_DECLARATIONS_AND_SMILES_TEXT; RAW_READER_INVENTORIES_PASS',
                'numerical_restraints':'UNASSESSED','readyset_execution':'NOT_RUN',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='38_Cedar':
            receipt['previous_execution']={'delivery_prefix':'38_Cedar','installed_monomer_lookup':'BOTH_MISSING_NATIVE_ENERGY_TYPES_UNKNOWN',
                'PDU_saved_candidate':'ACTIVE_TRIPLE_DISTANCE_AND_LINEAR_ANGLES_PASS; SIX_LINEAR_AXIS_TORSIONS_REVIEW',
                'coordinate_origin':'FIXED_ISOLATED_SOURCE_SEEDS; NOT_OPTIMIZED_CANDIDATE',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='37_Cedar':
            receipt['previous_execution']={'delivery_prefix':'37_Cedar','native_execution':'SOURCE_READER_AND_DECLARED_CHARGE_CONTROLS',
                'DP':'RAW_ORDERS_PASS_CHARGES_DIFFER; EXPLICIT_SOURCE_CHARGE_CONTROL_PASS',
                'PDU':'RAW_INVENTORY_AND_ALREADY_PRESERVED_CHARGE_CONTROL_PASS','dictionary_generation':'NOT_RUN',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='36_Cedar':
            receipt['previous_execution']={'delivery_prefix':'36_Cedar','native_execution':'SOURCE_READER_DIALECT_CONTROLS',
                'DP':'ROUTE_IDENTITIES_ELEMENTS_COORDINATES_PASS; ORDERS_AND_CHARGES_DIFFER',
                'PDU':'READER_ROUTE_AND_INVENTORY_PASS','dictionary_generation':'NOT_RUN',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='35_Cedar':
            receipt['previous_execution']={'delivery_prefix':'35_Cedar','phase':'PORTABLE_GRAPH_PREFLIGHT',
                'error':'Output parent cannot traverse a symlink','native_execution':'NOT_RUN','dictionary_generation':'NOT_RUN',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='34_Cedar':
            receipt['previous_execution']={'delivery_prefix':'34_Cedar','DP':'UNKNOWN_MARKERS_AND_CONSTRUCTOR_ASSERTION',
                'PDU':'KNOWN_MARKERS_AND_CONSTRUCTOR_COMPLETED',
                'constructor_internal_optimization':'LOCAL_CHIRAL_TEMPLATE_OPTIMIZATION_IN_NATIVE_SOURCE; LEGACY_NOT_RUN_FLAG_NOT_A_PROOF',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'}}
        elif source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='33_Cedar':
            receipt['previous_execution']={'delivery_prefix':'33_Cedar','DP':'PREPARATORY_CHIRALITY_FAILURE_NO_CANDIDATE',
                'PDU':'CANDIDATE_REVIEW_NOT_CONVERGED_REPORTED',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'},
                'pickle_evidence':'EXCLUDED_NOT_LOADED'}
        elif source_prefix:
            receipt['previous_execution']={'delivery_prefix':'32_Cedar','native_execution':'READ_ONLY_INPUT_CHECKS',
                'evidence':{'anchor':'probe_directory','path':'inputs/review/probe_receipt.json'},
                'DP':'READER_DIALECT_REVIEW','PDU':'PARSER_READ_ONLY_PASS'}
        if args.single_block_steps is not None and json.loads(members['probe_receipt.json'])['delivery_prefix']!='32_Cedar':
            raise ValueError('Single-block delivery requires the reviewed installed Cedar 32 source contract')
        if args.stereochemistry_audit_only != (json.loads(members['probe_receipt.json'])['delivery_prefix']=='33_Cedar'):
            raise ValueError('Cedar 33 is only supported by the explicit read-only stereochemistry action')
        input_delivery=json.loads(members['probe_receipt.json'])['delivery_prefix']
        _check_constructor_input_mode(args,input_delivery)
        if args.nonbonded_cache_audit_only != (input_delivery=='45_Cedar'):
            raise ValueError('Cedar 45 requires explicit nonbonded-cache proof and strict retry')
        if args.linear_torsion_impact_only != (input_delivery=='44_Cedar'):
            raise ValueError('Cedar 44 requires the explicit fixed-coordinate linear-torsion impact action')
        if args.linear_torsion_candidate_only != (input_delivery=='43_Cedar'):
            raise ValueError('Cedar 43 requires the explicit separate linear-torsion candidate action')
        if args.torsion_conditioning_audit_only != (input_delivery=='42_Cedar'):
            raise ValueError('Cedar 42 requires the explicit fixed torsion-conditioning audit')
        if args.readyset_generation_audit_only != (input_delivery in {'40_Cedar','41_Cedar'}):
            raise ValueError('Cedar 40--41 are only supported by the explicit isolated ReadySet generation audit')
        if args.readyset_source_audit_only != (input_delivery=='39_Cedar'):
            raise ValueError('Cedar 39 is only supported by the explicit ReadySet source/descriptor audit')
        if args.installed_source_audit_only != (input_delivery=='38_Cedar'):
            raise ValueError('Cedar 38 is only supported by the explicit installed monomer/CCD source audit')
        if args.triple_bond_audit_only != (input_delivery=='37_Cedar'):
            raise ValueError('Cedar 37 is only supported by the explicit installed triple-bond audit action')
        if args.source_dialect_audit_only != (input_delivery in {'34_Cedar','35_Cedar','36_Cedar'}):
            raise ValueError('Cedar 34--36 are only supported by the explicit source-dialect reader action')
        if args.declared_charge_control != (input_delivery=='36_Cedar') or args.declared_charge_control and not args.source_dialect_audit_only:
            raise ValueError('The declared-charge control requires the exact reviewed Cedar 36 return and explicit source-dialect action')
        from nasolve.cif_numerical_recovery import plan_numerical_recovery,prepare_graph_generation_source,generate_numerical_recovery,validate_rotation_evidence
        from nasolve.cif_fixed_geometry import qualify_fixed_policy_geometry
        expected=json.loads(source_members[ROTATION_PREFIX+'/expected_inventory.json']);saved=prior['geometry_trial']['result']
        proof=qualified['native_correction_audit']['result']
        validation=validate_rotation_evidence(rotation['native_rotation_audit']['result'],rotation['rotation_plan'],saved,proof['constraint_signature_before'])
        candidate=source_root/'inputs/review/candidate/continued_geometry_model.pdb'
        replay=qualify_fixed_policy_geometry(expected,prior['native_roundtrip']['native_validation'],candidate,prior['serialization'])
        if replay!=prior['native_mechanics'] or not replay['mechanics_checks_pass']:raise ValueError('Native mechanics prerequisite does not replay')
        capture=rotation['native_rotation_audit'];directory=source_root/ROTATION_PREFIX
        cifs=[directory/PurePosixPath(r['path']) for r in capture['inputs'] if r['role']=='dictionary']
        plan=plan_numerical_recovery(expected,cifs,components=components);_json(session/'numerical_recovery_plan.json',plan)
        if plan['blocked'] or not plan['selected']:raise ValueError('Explicit numerical recovery plan is blocked or empty')
        receipt.update(prior_archive={'sha256':_sha(original),'bytes':len(original),'verified_payloads':len(json.loads(members['manifest.json']))},
            prior_convergence=rotation['prior_convergence'],prior_stopping=rotation['prior_stopping'],prior_continuation=rotation['prior_continuation'],
            prerequisite_mechanics_replayed=True,prior_rotation_evidence_recomputed=validation,source_plan=plan)
        print('Native source-coordinate setup:' if args.source_constructor_setup_audit_only else 'Native named restraint-index basis:' if args.source_constructor_index_basis_audit_only else 'Native local coordinate/chirality mapping:' if args.source_constructor_mapping_audit_only else 'Native chiral boundary observation:' if args.source_constructor_trace_audit_only else 'Source-native CCTBX constructor retry:' if args.source_constructor_backend_audit_only else 'Source-native chiral constructor handoff:' if args.source_constructor_audit_only else 'Native pair-cache proof and strict impact retry:' if args.nonbonded_cache_audit_only else 'Fixed-coordinate torsion impact audit:' if args.linear_torsion_impact_only else 'Separate linear-torsion candidate audit:' if args.linear_torsion_candidate_only else 'Fixed native torsion-conditioning audit:' if args.torsion_conditioning_audit_only else 'Isolated ReadySet generation audit:' if args.readyset_generation_audit_only else 'ReadySet source/descriptor audit:' if args.readyset_source_audit_only else 'Source-dialect reader audit:' if args.source_dialect_audit_only else 'Source-graph numerical recovery:',BUNDLE['delivery_prefix'],flush=True)
        print('Preserved prerequisite component:' if args.nonbonded_cache_audit_only or args.linear_torsion_impact_only or args.linear_torsion_candidate_only or args.torsion_conditioning_audit_only or args.readyset_generation_audit_only else 'Explicit candidates:',', '.join(plan['recovery_codes']),flush=True)
        print('Verified prior mechanics and rotational derivatives; no model optimization.',flush=True)
        if constructor_action or args.declared_charge_control or args.triple_bond_audit_only or args.installed_source_audit_only or args.readyset_source_audit_only or args.readyset_generation_audit_only or args.torsion_conditioning_audit_only or args.linear_torsion_candidate_only or args.linear_torsion_impact_only or args.nonbonded_cache_audit_only:
            from nasolve.cif_source_reader import source_reader_checks
            receipt['prior_source_reader_replay']={}
            charge_members=members;charge_root=frozen
            while json.loads(charge_members['probe_receipt.json'])['delivery_prefix'] in {'38_Cedar','39_Cedar','40_Cedar','41_Cedar','42_Cedar','43_Cedar','44_Cedar','45_Cedar','46_Cedar','47_Cedar','48_Cedar','49_Cedar','50_Cedar','51_Cedar','52_Cedar'}:
                charge_members={n.removeprefix('inputs/review/'):d for n,d in charge_members.items() if n.startswith('inputs/review/')}
                charge_root=charge_root/'inputs/review'
            for code,row in json.loads(charge_members['probe_receipt.json'])['source_reader_audits'].items():
                previous_source=charge_root/row['directory']['path']/'source.cif'
                replayed=source_reader_checks(previous_source,code,row['result'],row['expected_dialect'])
                if replayed!=row['checks']:raise ValueError('Returned raw reader inventory does not replay')
                receipt['prior_source_reader_replay'][code]=replayed
            if args.declared_charge_control:receipt['declared_charge_control_requested']=True
            if constructor_action or args.triple_bond_audit_only or args.installed_source_audit_only or args.readyset_source_audit_only or args.readyset_generation_audit_only or args.torsion_conditioning_audit_only or args.linear_torsion_candidate_only or args.linear_torsion_impact_only or args.nonbonded_cache_audit_only:receipt['prior_declared_charge_replay']=_replay_charge_controls(charge_members,charge_root)
        receipt['graph_preparations']={}
        for item in plan['selected']:
            code=item['component'];source=cifs[item['input_index']]
            if _sha(source.read_bytes())!=item['source_sha256']:raise ValueError('Selected source changed')
            preparation=prepare_graph_generation_source(source,code,session/'graph_preview'/code/'source.cif')
            receipt['graph_preparations'][code]=preparation
        controls=BUNDLE.get('component_controls',[])
        if len(components)+len(controls)>(4 if args.source_constructor_index_basis_audit_only or args.source_constructor_setup_audit_only else 3) or set(components)&{r['component'] for r in controls}:raise ValueError('Candidate and public-control scope exceeds bounds or overlaps')
        receipt['component_controls']={};sources={item['component']:cifs[item['input_index']] for item in plan['selected']}
        receipt['independent_component_controls']=[]
        for control in controls:
            from nasolve.cif_component_controls import assess_component_control
            code=control['component'];data=runtime[control['path']]
            if len(data)!=control['size'] or _sha(data)!=control['sha256']:raise ValueError('Pinned public control changed')
            target=session/'component_controls/sources'/(code+'.cif');target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as handle:handle.write(data)
            report=assess_component_control(target,code,graph_only_if_ambiguous=(args.triple_bond_audit_only or args.installed_source_audit_only or args.readyset_source_audit_only or args.readyset_generation_audit_only or args.torsion_conditioning_audit_only or args.linear_torsion_candidate_only or args.linear_torsion_impact_only or args.nonbonded_cache_audit_only));receipt['component_controls'][code]=report
            independent=(args.source_constructor_index_basis_audit_only or args.source_constructor_setup_audit_only) and code not in {'PDU','5PC'}
            if independent:
                from nasolve.cif_stereochemistry_audit import reader_stereo_inventory
                report.update(scope='INDEPENDENT_PUBLIC_SOURCE_AND_COMPILER_CONTROL',source_stereo_inventory=reader_stereo_inventory(target,code),native_execution='NOT_RUN')
                receipt['independent_component_controls'].append(code)
            _json(session/'component_controls'/(code+'_control.json'),report)
            if report['policy_status']!='PASS' and not ((args.triple_bond_audit_only or args.installed_source_audit_only or args.readyset_source_audit_only or args.readyset_generation_audit_only or args.torsion_conditioning_audit_only or args.linear_torsion_candidate_only or args.linear_torsion_impact_only or args.nonbonded_cache_audit_only) and report['graph_status']=='PASS'):raise ValueError('Component control policy requires review: '+code)
            receipt['graph_preparations'][code]=prepare_graph_generation_source(target,code,session/'graph_preview'/code/'source.cif')
            if not independent:sources[code]=target
            print('Public control:',code,'; graph',report['graph_status'],'; NARestraints class',report['mapped_base_class'],'; pairing/stacking compiler',report['policy_status'],flush=True)
        if constructor_action:
            return _run_source_constructor_action(args,receipt,session,review,original,members,frozen,sources,capture,expected)
        if args.linear_torsion_impact_only or args.nonbonded_cache_audit_only:
            return _run_linear_torsion_impact_action(args,receipt,session,review,original,members,frozen,controls,sources,capture,expected)
        if args.linear_torsion_candidate_only:
            return _run_linear_torsion_candidate_action(args,receipt,session,review,original,members,frozen,controls,sources,capture,expected)
        if args.torsion_conditioning_audit_only:
            return _run_torsion_conditioning_action(args,receipt,session,review,original,members,frozen,controls,sources,proof['installed_numeric_sources'],capture,expected)
        if args.readyset_generation_audit_only:
            return _run_readyset_generation_action(args,receipt,session,review,original,members,frozen,runtime,controls,sources,capture,expected)
        if args.readyset_source_audit_only:
            return _run_readyset_source_action(args,receipt,session,review,original,members,frozen,runtime,controls,sources,capture,expected)
        if args.installed_source_audit_only:
            return _run_catalogue_action(args,receipt,session,review,original,members,frozen,runtime,controls,sources,capture,expected)
        if args.triple_bond_audit_only:
            return _run_triple_action(args,receipt,session,review,original,members,frozen,runtime,controls,sources,capture,expected)
        from nasolve.cif_elbow_input import prepare_elbow_ccd_input
        receipt['consumer_preparations']={}
        for code in sources:
            if args.source_dialect_audit_only:
                from nasolve.cif_elbow_input import prepare_elbow_source_dialect_input
                receipt['consumer_preparations'][code]=prepare_elbow_source_dialect_input(sources[code],session/'graph_preview'/code/'source.cif',code,session/'consumer_preview'/code/'source.cif')
                print(code,'source reader:',receipt['consumer_preparations'][code]['consumer_reader_dialect'],flush=True)
            else:
                receipt['consumer_preparations'][code]=prepare_elbow_ccd_input(session/'graph_preview'/code/'source.cif',code,session/'consumer_preview'/code/'source.cif')
        if args.stereochemistry_audit_only or args.source_dialect_audit_only:
            from nasolve.cif_stereochemistry_audit import reader_stereo_inventory,audit_candidate_stereochemistry,audit_optimizer_log
            from nasolve.cif_generation import inspect_component_generation
            receipt['source_stereo_inventories']={code:reader_stereo_inventory(session/'consumer_preview'/code/'source.cif',code) for code in sources}
            receipt['saved_candidate_stereochemistry']={};receipt['saved_optimizer_trajectories']={}
            trial_members=({n.removeprefix('inputs/review/'):d for n,d in reader_members.items() if n.startswith('inputs/review/')} if args.source_dialect_audit_only else members)
            trial_root=reader_root/'inputs/review' if args.source_dialect_audit_only else frozen
            for code,(pre,generatedir,_) in CEDAR33_CASES.items():
                if code not in sources:raise ValueError('Read-only stereo scope must preserve both reviewed cases')
                gp=pre+'/generation/'+generatedir
                if args.stereochemistry_audit_only and (session/'consumer_preview'/code/'source.cif').read_bytes()!=members['consumer_preview/'+code+'/source.cif']:
                    raise ValueError('Fresh stereo consumer differs from the reviewed trial')
                output=trial_root/gp/'candidate.cif'
                if output.is_file():
                    inspection=inspect_component_generation(trial_root/pre/'original/source.cif',output,code)
                    previous=json.loads(trial_members['probe_receipt.json'])['candidates'][code]['original_source_inspection']
                    if any(inspection[k]!=previous[k] for k in ['status','rejection_reasons','chemical_changes','bond_representation','numerical_issues']):
                        raise ValueError('Saved candidate numerical/chemical assessment does not replay')
                    result=audit_candidate_stereochemistry(trial_root/pre/'original/source.cif',output,code)
                    if args.source_dialect_audit_only and result!=json.loads(reader_members['probe_receipt.json'])['saved_candidate_stereochemistry'][code]:
                        raise ValueError('Returned saved candidate stereo evidence does not replay')
                    receipt['saved_candidate_stereochemistry'][code]=result
                    _json(session/'stereochemistry'/(code+'_candidate.json'),result)
                    print(code,'saved candidate stereo:',result['status'],'; absolute CIP assignment NOT_RUN',flush=True)
                trajectory=audit_optimizer_log(trial_members[gp+'/elbow.log'].decode())
                if args.source_dialect_audit_only and trajectory!=json.loads(reader_members['probe_receipt.json'])['saved_optimizer_trajectories'][code]:
                    raise ValueError('Returned saved trajectory evidence does not replay')
                receipt['saved_optimizer_trajectories'][code]=trajectory
                _json(session/'stereochemistry'/(code+'_trajectory.json'),trajectory)
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            fingerprints=_fingerprints(phenix,{**capture,'native_validation':expected});receipt['installed_api_sources']=fingerprints
            elbow=phenix.executables.get('phenix.elbow')
            if not elbow or not Path(elbow).resolve().is_relative_to(Path(phenix.root).resolve()):raise ValueError('Require an installation-bound eLBOW')
            receipt['elbow_executable_sha256']=_sha(Path(elbow).read_bytes());receipt['phenix_version']=phenix.version
            if args.source_dialect_audit_only:
                from nasolve.cif_elbow_chirality import verify_chirality_sources
                from nasolve.cif_elbow_contract import verify_elbow_source_capture
                from nasolve.cif_source_reader import audit_source_reader,verify_source_reader_capture
                previous=json.loads(reader_members['probe_receipt.json'])
                prior_contract=json.loads(trial_members['probe_receipt.json'])['installed_elbow_contract']
                old_readers=json.loads(members['probe_receipt.json']).get('source_reader_audits',{})
                for row in old_readers.values():verify_source_reader_capture(phenix.root,row,frozen/row['directory']['path'])
                verify_elbow_source_capture(phenix.root,prior_contract,trial_root/prior_contract['source_directory']['path'])
                for code,row in previous['installed_chirality_controls'].items():
                    verify_chirality_sources(phenix.root,row,reader_root/row['directory']['path'])
                receipt['source_reader_audits']={}
                for code in sources:
                    output=session/'native_source_reader'/code
                    result=audit_source_reader(phenix.root,phenix.executables['phenix.python'],fingerprints,
                        session/'consumer_preview'/code/'source.cif',code,output,environment=phenix.environment,
                        expected_dialect=receipt['consumer_preparations'][code]['consumer_reader_dialect'],timeout_seconds=min(args.timeout_seconds,30),
                        declared_charge_control=args.declared_charge_control,
                        charge_source_proof=[r for r in previous['installed_chirality_controls']['DP']['sources']
                            if r['path'].endswith(('/elbow/utilities/Utilities.py','/elbow/chemistry/MoleculeClass.py'))] if args.declared_charge_control else ())
                    receipt['source_reader_audits'][code]={'directory':{'anchor':'probe_directory','path':output.relative_to(session).as_posix()},**result}
                    print(code,'native source reader:',result['status'],'; execution',result['result']['execution'],flush=True)
                    if args.declared_charge_control:
                        print(code,'declared charge control:',result['declared_charge_qualification']['status'],
                              '; action',result['declared_charge_control'].get('action','NOT_RUN'),flush=True)
                for code,row in receipt['source_reader_audits'].items():verify_source_reader_capture(phenix.root,row,session/'native_source_reader'/code)
                for code,row in previous['installed_chirality_controls'].items():verify_chirality_sources(phenix.root,row,reader_root/row['directory']['path'])
                verify_elbow_source_capture(phenix.root,prior_contract,trial_root/prior_contract['source_directory']['path'])
                for row in old_readers.values():verify_source_reader_capture(phenix.root,row,frozen/row['directory']['path'])
                receipt['native_execution']='SOURCE_READER_AND_DECLARED_CHARGE_CONTROLS' if args.declared_charge_control else 'SOURCE_READER_DIALECT_CONTROLS'
            if args.stereochemistry_audit_only:
                from nasolve.cif_elbow_contract import verify_elbow_source_capture
                from nasolve.cif_elbow_chirality import audit_installed_chirality,verify_chirality_sources
                prior_contract=json.loads(members['probe_receipt.json'])['installed_elbow_contract']
                verify_elbow_source_capture(phenix.root,prior_contract,frozen/prior_contract['source_directory']['path'])
                receipt['installed_chirality_controls']={}
                for code in sources:
                    output=session/'native_stereochemistry'/code
                    result=audit_installed_chirality(phenix.root,phenix.executables['phenix.python'],fingerprints,
                        session/'consumer_preview'/code/'source.cif',code,output,environment=phenix.environment,
                        timeout_seconds=min(args.timeout_seconds,30))
                    receipt['installed_chirality_controls'][code]={'directory':{'anchor':'probe_directory','path':output.relative_to(session).as_posix()},**result}
                    print(code,'native reader stereo:',result['status'],'; constructor',result['result']['constructor_probe']['status'],flush=True)
                for code,result in receipt['installed_chirality_controls'].items():
                    verify_chirality_sources(phenix.root,result,session/'native_stereochemistry'/code)
                verify_elbow_source_capture(phenix.root,prior_contract,frozen/prior_contract['source_directory']['path'])
                receipt['native_execution']='INSTALLED_READER_CHIRALITY_CONTROLS'
            if args.single_block_steps is not None:
                from nasolve.cif_elbow_contract import verify_elbow_source_capture
                prior_contract=json.loads(members['probe_receipt.json'])['installed_elbow_contract']
                verify_elbow_source_capture(phenix.root,prior_contract,frozen/prior_contract['source_directory']['path'])
                receipt['single_block_control']={'steps':args.single_block_steps,'source_contract_archive':CEDAR32_SHA256,
                    'macro_restart':'AVOIDED_BY_INSTALLED_EXPLICIT_STEP_CONTROL','tolerance':'UNCHANGED','convergence':'NEVER_INFERRED_FROM_EXIT_ZERO'}
            if args.native_contract_only or args.single_block_steps is not None:
                from nasolve.cif_elbow_contract import capture_elbow_sources,verify_elbow_source_capture,audit_elbow_input
                source_directory=session/'native_contract/installed_sources'
                contract=capture_elbow_sources(phenix.root,fingerprints,source_directory,phenix_version=phenix.version)
                receipt['installed_elbow_contract']={'source_directory':{'anchor':'probe_directory','path':'native_contract/installed_sources'},**contract}
                receipt['native_input_checks']={}
                for code in sources:
                    result=audit_elbow_input(session/'consumer_preview'/code/'source.cif',code,session/'native_contract/inputs',elbow,
                        environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=min(args.timeout_seconds,60))
                    receipt['native_input_checks'][code]={
                        'directory':{'anchor':'probe_directory','path':Path(result['candidate_directory']).relative_to(session).as_posix()},**result}
                    print(code,'read-only input:',result['status'],'; dictionary generation NOT_RUN',flush=True)
                verify_elbow_source_capture(phenix.root,contract,source_directory)
                receipt['native_execution']='READ_ONLY_INPUT_CHECKS'
            if not args.native_contract_only and not args.stereochemistry_audit_only and not args.source_dialect_audit_only:
                receipt['dictionary_generation']='ATTEMPTED';receipt['candidates']={}
                receipt['single_block_options']={}
                for code,source in sources.items():
                    if args.single_block_steps is not None and receipt['native_input_checks'][code]['status']!='PARSER_READ_ONLY_PASS':
                        receipt['candidates'][code]={'status':'REJECTED','phase':'INPUT_PREFLIGHT_REVIEW','dictionary_generation':'NOT_RUN'}
                        print(code,'generation deferred: read-only input requires review',flush=True);continue
                    if args.single_block_steps is not None:
                        from nasolve.cif_elbow_contract import audit_single_block_options,verify_single_block_options
                        options_directory=session/'native_contract/options'/code
                        options=audit_single_block_options(phenix.root,phenix.executables['phenix.python'],fingerprints,
                            session/'consumer_preview'/code/'source.cif',code,receipt['native_input_checks'][code]['generator_capabilities'],
                            options_directory,environment=phenix.environment,steps=args.single_block_steps)
                        receipt['single_block_options'][code]={'directory':{'anchor':'probe_directory','path':options_directory.relative_to(session).as_posix()},**options}
                    print('Generating independent numerical candidate:',code,flush=True)
                    result=generate_numerical_recovery(source,code,session/'generation',elbow,
                        environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=args.timeout_seconds,
                        single_block_steps=args.single_block_steps)
                    if args.single_block_steps is not None:verify_single_block_options(phenix.root,options,options_directory)
                    if result.get('consumer_preparation',{}).get('consumer_sha256')!=receipt['consumer_preparations'][code]['consumer_sha256']:
                        raise ValueError('Generation reader input differs from the checked consumer projection')
                    receipt['candidates'][code]=result
                    print(code,'candidate:',result['status'],flush=True)
                    inspection=result.get('original_source_inspection',{});assessment=inspection.get('generated_assessment') or {}
                    findings=[f for c in assessment.get('components',[]) for f in c['findings'] if f['rule_id']=='PLANE-01' and f['status']!='PASS']
                    if assessment:print(code,'retained plane/angle reviews:',len(findings),flush=True)
                    else:print(code,'numerical assessment: NOT_RUN (no generated dictionary)',flush=True)
                    print(code,'generator execution:',result.get('generation',{}).get('execution',{}).get('status','NOT_RUN'),flush=True)
                    print(code,'optimizer stopping:',result.get('generation',{}).get('optimization_stopping',{}).get('status','NOT_RUN'),flush=True)
                receipt['dictionary_generation']='COMPLETED' if all(r['status']=='CANDIDATE_REVIEW' for r in receipt['candidates'].values()) else 'REVIEW_REQUIRED'
                if args.single_block_steps is not None:
                    verify_elbow_source_capture(phenix.root,contract,source_directory)
                    verify_elbow_source_capture(phenix.root,prior_contract,frozen/prior_contract['source_directory']['path'])
                    receipt['native_execution']='READ_ONLY_INPUT_CHECKS_AND_NUMERICAL_GENERATION'
            if _sha(Path(elbow).read_bytes())!=receipt['elbow_executable_sha256'] or _fingerprints(phenix,{**capture,'native_validation':expected})!=fingerprints:raise ValueError('Selected generator or installed source changed')
        if any((frozen/PurePosixPath(n)).read_bytes()!=d for n,d in members.items()):raise ValueError('Frozen evidence changed')
        if any((session/'component_controls/sources'/(c['component']+'.cif')).read_bytes()!=runtime[c['path']] for c in controls):raise ValueError('Frozen public control changed')
        if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW ('+('source-dialect reader evidence' if args.source_dialect_audit_only else 'read-only source/candidate stereochemistry' if args.stereochemistry_audit_only else 'installed source/read-only input evidence' if args.native_contract_only else 'dictionary candidates only')+'; native/scientific qualification remains open)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(original is not None and review and review.read_bytes()==original)
            receipt['frozen_inputs_preserved']=bool(members is not None and all((session/'inputs/review'/PurePosixPath(n)).is_file()
                and (session/'inputs/review'/PurePosixPath(n)).read_bytes()==d for n,d in members.items()))
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Numerical recovery stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())
