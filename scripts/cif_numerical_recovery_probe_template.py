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


def _source_view(members):
    prefix=''
    while True:
        header=json.loads(members['probe_receipt.json'])
        if header.get('delivery_prefix') not in {'30_Cedar','31_Cedar'} or header.get('kind')!='cif-source-graph-numerical-recovery-probe':
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


def _read_capsule(path, expected_sha=None):
    original=path.read_bytes();digest=_sha(original)
    if digest not in ({expected_sha} if expected_sha else {REVIEW_SHA256,CEDAR30_SHA256,CEDAR31_SHA256}):
        raise ValueError('Require an exact verified Cedar 29, Cedar 30 or Cedar 31 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries=z.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):raise ValueError('Unsafe or duplicate review member')
        members={e.filename:z.read(e) for e in entries}
    header=json.loads(members['probe_receipt.json'])
    if header.get('delivery_prefix')=='31_Cedar':qualified,prior,rotation=_read_cedar31_members(members)
    elif header.get('delivery_prefix')=='30_Cedar':qualified,prior,rotation=_read_cedar30_members(members)
    else:qualified,prior,rotation=_read_cedar29_members(members)
    return members,qualified,prior,rotation,original


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    default_review={
        '32_Cedar':'NASolve-live-tests/31_Cedar_cif-numerical-recovery-95asqu3e/31_Cedar_95asqu3e_cif_numerical_recovery_review.zip',
        '31_Cedar':'NASolve-live-tests/30_Cedar_cif-numerical-recovery-_ixms4r3/30_Cedar__ixms4r3_cif_numerical_recovery_review.zip',
    }.get(BUNDLE['delivery_prefix'],'NASolve-live-tests/29_Cedar_cif-base-rotation-94wuz090/29_Cedar_94wuz090_cif_base_rotation_review.zip')
    parser.add_argument('--review-zip',type=Path,default=Path.home()/default_review)
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--component',action='append',help='Explicit component candidate selection; this reviewed slice defaults to DP')
    parser.add_argument('--timeout-seconds',type=int,default=600)
    parser.add_argument('--inspect-only',action='store_true')
    parser.add_argument('--native-contract-only',action='store_true',
                        help='Capture installed eLBOW sources and run read-only input checks; do not generate dictionaries')
    args=parser.parse_args();session=None;review=None;original=None;members=None
    receipt={'schema_version':1,'kind':'cif-source-graph-numerical-recovery-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','native_proxy_validation':'NOT_RUN','linked_site_validation':'NOT_RUN',
        'model_editing':'NOT_RUN','model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','policy_recompilation':'NOT_RUN',
        'readyset_retry':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'diffraction_data':'NOT_READ','policy_authority':'NARestraints','installed_phenix_edits':'NOT_RUN',
        'requested_action':'NATIVE_READ_ONLY_CONTRACT' if args.native_contract_only else 'INDEPENDENT_NUMERICAL_GENERATION',
        'limits':{'max_components':3,'generation_timeout_per_component':args.timeout_seconds,'read_only_timeout_per_component':min(args.timeout_seconds,60)},
        'limitations':['Separate dictionary candidates only; none is applied to a native manager or model.',
            'All original numerical targets remain in the frozen source. Replacement targets come only from independent generation.',
            'Declared source coordinates seed naming/initial geometry, not final restraint targets or independent validation.',
            'Chemical-state preservation, numerical checks, native proxy qualification and scientific approval are separate gates.',
            'Existing modifiers, pairing and stacking policy are recorded and unchanged; no modifier composition is attempted.']}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid timeout bound')
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
        if source_prefix and json.loads(members['probe_receipt.json'])['delivery_prefix']=='30_Cedar':
            previous_generation=json.loads(members['probe_receipt.json'])
            receipt['previous_generation']={'delivery_prefix':'30_Cedar','status':'FAILED_NO_CANDIDATE','phase':'INPUT_PARSER','native_returncode':1,
                'chemical_rejection':'NOT_ASSESSED','numerical_reviews':'NOT_ASSESSED','evidence':{'anchor':'probe_directory','path':'inputs/review/'+CEDAR30_GENERATION_PREFIX+'/elbow.log'}}
        elif source_prefix:
            receipt['previous_generation']={'delivery_prefix':'31_Cedar','status':'FAILED_NO_CANDIDATE',
                'cases':{code:{'phase':'INPUT_PARSER_MISSING_ALT_ATOM_ID' if code=='DP' else 'OPTIMIZER_RESTART_EMPTY_XYZ_UNBOUND_LOCAL',
                    'native_returncode':1,'chemical_rejection':'NOT_ASSESSED','numerical_reviews':'NOT_ASSESSED',
                    'evidence':{'anchor':'probe_directory','path':'inputs/review/'+prefix+'/generation/'+generatedir+'/elbow.log'}}
                    for code,(prefix,generatedir,_) in CEDAR31_CASES.items()},
                'pickle_evidence':'EXCLUDED_BY_PRIOR_SHUTTLE_NOT_LOADED'}
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
        print('Source-graph numerical recovery:',BUNDLE['delivery_prefix'],flush=True)
        print('Explicit candidates:',', '.join(plan['recovery_codes']),flush=True)
        print('Verified prior mechanics and rotational derivatives; no model optimization.',flush=True)
        receipt['graph_preparations']={}
        for item in plan['selected']:
            code=item['component'];source=cifs[item['input_index']]
            if _sha(source.read_bytes())!=item['source_sha256']:raise ValueError('Selected source changed')
            preparation=prepare_graph_generation_source(source,code,session/'graph_preview'/code/'source.cif')
            receipt['graph_preparations'][code]=preparation
        controls=BUNDLE.get('component_controls',[])
        if len(components)+len(controls)>3 or set(components)&{r['component'] for r in controls}:raise ValueError('Candidate and public-control scope exceeds bounds or overlaps')
        receipt['component_controls']={};sources={item['component']:cifs[item['input_index']] for item in plan['selected']}
        for control in controls:
            from nasolve.cif_component_controls import assess_component_control
            code=control['component'];data=runtime[control['path']]
            if len(data)!=control['size'] or _sha(data)!=control['sha256']:raise ValueError('Pinned public control changed')
            target=session/'component_controls/sources'/(code+'.cif');target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as handle:handle.write(data)
            report=assess_component_control(target,code);receipt['component_controls'][code]=report
            _json(session/'component_controls'/(code+'_control.json'),report)
            if report['policy_status']!='PASS':raise ValueError('Component control policy requires review: '+code)
            receipt['graph_preparations'][code]=prepare_graph_generation_source(target,code,session/'graph_preview'/code/'source.cif')
            sources[code]=target
            print('Public control:',code,'; graph',report['graph_status'],'; NARestraints class',report['mapped_base_class'],'; pairing/stacking compiler',report['policy_status'],flush=True)
        if not args.inspect_only:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            fingerprints=_fingerprints(phenix,{**capture,'native_validation':expected});receipt['installed_api_sources']=fingerprints
            elbow=phenix.executables.get('phenix.elbow')
            if not elbow or not Path(elbow).resolve().is_relative_to(Path(phenix.root).resolve()):raise ValueError('Require an installation-bound eLBOW')
            receipt['elbow_executable_sha256']=_sha(Path(elbow).read_bytes());receipt['phenix_version']=phenix.version
            if args.native_contract_only:
                from nasolve.cif_elbow_contract import capture_elbow_sources,verify_elbow_source_capture,audit_elbow_input
                source_directory=session/'native_contract/installed_sources'
                contract=capture_elbow_sources(phenix.root,fingerprints,source_directory,phenix_version=phenix.version)
                receipt['installed_elbow_contract']={'source_directory':{'anchor':'probe_directory','path':'native_contract/installed_sources'},**contract}
                receipt['native_input_checks']={}
                for code in sources:
                    result=audit_elbow_input(session/'graph_preview'/code/'source.cif',code,session/'native_contract/inputs',elbow,
                        environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=min(args.timeout_seconds,60))
                    receipt['native_input_checks'][code]={
                        'directory':{'anchor':'probe_directory','path':Path(result['candidate_directory']).relative_to(session).as_posix()},**result}
                    print(code,'read-only input:',result['status'],'; dictionary generation NOT_RUN',flush=True)
                verify_elbow_source_capture(phenix.root,contract,source_directory)
                receipt['native_execution']='READ_ONLY_INPUT_CHECKS'
            else:
                receipt['dictionary_generation']='ATTEMPTED';receipt['candidates']={}
                for code,source in sources.items():
                    print('Generating independent numerical candidate:',code,flush=True)
                    result=generate_numerical_recovery(source,code,session/'generation',elbow,
                        environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=args.timeout_seconds)
                    receipt['candidates'][code]=result
                    print(code,'candidate:',result['status'],flush=True)
                    inspection=result.get('original_source_inspection',{});assessment=inspection.get('generated_assessment') or {}
                    findings=[f for c in assessment.get('components',[]) for f in c['findings'] if f['rule_id']=='PLANE-01' and f['status']!='PASS']
                    if assessment:print(code,'retained plane/angle reviews:',len(findings),flush=True)
                    else:print(code,'numerical assessment: NOT_RUN (no generated dictionary)',flush=True)
                    print(code,'generator execution:',result.get('generation',{}).get('execution',{}).get('status','NOT_RUN'),flush=True)
                receipt['dictionary_generation']='COMPLETED' if all(r['status']=='CANDIDATE_REVIEW' for r in receipt['candidates'].values()) else 'REVIEW_REQUIRED'
            if _sha(Path(elbow).read_bytes())!=receipt['elbow_executable_sha256'] or _fingerprints(phenix,{**capture,'native_validation':expected})!=fingerprints:raise ValueError('Selected generator or installed source changed')
        if any((frozen/PurePosixPath(n)).read_bytes()!=d for n,d in members.items()):raise ValueError('Frozen evidence changed')
        if any((session/'component_controls/sources'/(c['component']+'.cif')).read_bytes()!=runtime[c['path']] for c in controls):raise ValueError('Frozen public control changed')
        if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW ('+('installed source/read-only input evidence' if args.native_contract_only else 'dictionary candidates only')+'; native/scientific qualification remains open)',flush=True)
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
