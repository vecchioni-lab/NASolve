#!/usr/bin/env python3
"""Audit graph-selected base orientations under the qualified fixed NA policy."""
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
REVIEW_SHA256 = '1f553b4e57e75afbd8e29824600d470825a2b428c231a6bd0365c4319b05fb6c'
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
    destination = session / (BUNDLE['delivery_prefix']+'_'+token+'_cif_base_rotation_review.zip')
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



def _read_capsule(path,expected_sha=None):
    original=path.read_bytes()
    if _sha(original)!=(expected_sha or REVIEW_SHA256):raise ValueError('Require the exact verified Cedar 28 review ZIP')
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        entries=z.infolist();names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or any(not _safe(e.filename) or stat.S_ISLNK(e.external_attr>>16) for e in entries):raise ValueError('Unsafe or duplicate review member')
        members={e.filename:z.read(e) for e in entries}
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
    return members,qualified,current,original


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-zip',type=Path,default=Path.home()/'NASolve-live-tests/28_Cedar_cif-geometry-continuation-r6y0ddit/28_Cedar_r6y0ddit_cif_geometry_continuation_review.zip')
    parser.add_argument('--output-parent',type=Path,default=Path.home()/'NASolve-live-tests')
    parser.add_argument('--phenix-root',type=Path,default=Path.home()/'Applications/phenix-2.2.1-6174')
    parser.add_argument('--timeout-seconds',type=int,default=1200)
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();session=None;original=None;review=None;members=None
    receipt={'schema_version':1,'kind':'cif-fixed-na-base-rotation-probe','delivery_prefix':BUNDLE['delivery_prefix'],'build':BUNDLE,
        'status':'REVIEW','native_execution':'NOT_RUN','model_editing':'NOT_RUN','model_optimization':'NOT_RUN',
        'dictionary_generation':'NOT_RUN','policy_recompilation':'NOT_RUN','readyset_retry':'NOT_RUN','refinement':'NOT_RUN',
        'scientific_approval':'NOT_RUN','automatic_adoption':False,'diffraction_data':'NOT_READ','policy_authority':'NARestraints',
        'installed_phenix_edits':'NOT_RUN','rotation_derivative_qualification':'NOT_RUN',
        'limits':{'max_groups':6,'max_energy_evaluations':3000,'timeout_seconds':args.timeout_seconds},
        'limitations':['Temporary independent base rotations are evaluations, not optimized/adoptable models.',
            'Targets, weights, dictionaries, static proxies and NARestraints pairing/stacking policy remain fixed.',
            'An angular grid is not a minimization or complete search; no coupled base/backbone motions are tested.',
            'Internal base geometry stays fixed, so internal parameter conflicts remain separate.',
            'Native mechanics, sampled rotational derivatives and scientific qualification are independent.']}
    try:
        if not 1<=args.timeout_seconds<=3600:raise ValueError('Invalid timeout bound')
        runtime=_runtime_members();review=args.review_zip.expanduser().resolve(strict=True);parent=args.output_parent.expanduser().resolve()
        if parent==review.parent or parent.is_relative_to(review.parent):raise ValueError('Output must be outside preserved input directory')
        members,qualified,prior,original=_read_capsule(review);parent.mkdir(parents=True,exist_ok=True)
        session=Path(tempfile.mkdtemp(prefix=BUNDLE['delivery_prefix']+'_cif-base-rotation-',dir=parent))
        _materialize(runtime,session/'runtime');frozen=session/'inputs/review';_materialize(members,frozen)
        sys.path[:0]=[str(session/'runtime/src'),str(session/'runtime')];sys.dont_write_bytecode=True
        from nasolve.cif_corrected_geometry import validate_continuation
        from nasolve.cif_fixed_geometry import qualify_fixed_policy_geometry,classify_stopping,review_fixed_coordinates
        from nasolve.cif_base_rotation_audit import plan_base_rotations,run_native_base_rotation_audit,ANGLES
        expected=json.loads(members[CURRENT_TRIAL_PREFIX+'/expected_inventory.json'])
        proof=qualified['native_correction_audit']['result'];saved=prior['geometry_trial']['result']
        validate_continuation(saved,proof,expected['atom_count'])
        if _sha(runtime['src/nasolve/cif_parallelity_correction.py'])!=_sha(members[CURRENT_TRIAL_PREFIX+'/correction_core.py']):raise ValueError('Qualified correction source changed')
        replay=qualify_fixed_policy_geometry(expected,prior['native_roundtrip']['native_validation'],
            frozen/'candidate/continued_geometry_model.pdb',prior['serialization'])
        if replay!=prior['native_mechanics'] or not replay['mechanics_checks_pass']:raise ValueError('Native mechanics prerequisite does not replay')
        if classify_stopping(saved['stopping'])!='NOT_CONVERGED_LIMIT':raise ValueError('Prior stopping evidence does not replay')
        plan=plan_base_rotations(expected,saved['final_sites_cart']);receipt['rotation_plan']=plan
        _json(session/'base_rotation_plan.json',plan)
        _json(session/'full_precision_geometry_review.json',review_fixed_coordinates(expected,saved['final_sites_cart']))
        receipt.update(prior_archive={'sha256':_sha(original),'bytes':len(original),'verified_payloads':1104},
            prior_convergence=prior['convergence'],prior_stopping=saved['stopping'],prior_continuation=saved['continuation'],
            prerequisite_mechanics_replayed=True,derivative_precondition='SAMPLED_NATIVE_DERIVATIVES_PASS',
            correction_policy_id='native-parallelity-both-first-planes-v1',angles_degrees=list(ANGLES),
            objective='UNCHANGED_NATIVE_UNNORMALIZED_FIXED_NA_POLICY')
        receipt['selected_native_receipt']={'anchor':'probe_directory','path':'inputs/review/'+CURRENT_TRIAL_PREFIX+'/geometry_receipt.json'}
        print('Fixed NARestraints base-orientation audit:',BUNDLE['delivery_prefix'],flush=True)
        print('Graph-selected bases:',', '.join(plan['selected_sites']) or 'none supported',flush=True)
        print('Temporary rotations only; preserving all chemical definitions and pairing/stacking targets.',flush=True)
        if not args.inspect_only and plan['groups']:
            from nasolve.phenix_runtime import installation_from_candidate
            phenix=installation_from_candidate(args.phenix_root,base_environment={k:v for k,v in os.environ.items() if k not in NATIVE_OVERRIDES})
            capture={**prior['geometry_trial'],'native_validation':expected}
            numeric_capture={**capture,'native_validation':{'installed_api_sources':proof['installed_numeric_sources']}}
            adapter_capture={**capture,'native_validation':{'installed_api_sources':proof['installed_adapter_sources']}}
            fingerprints=_fingerprints(phenix,capture);numeric=_fingerprints(phenix,numeric_capture);adapters=_fingerprints(phenix,adapter_capture)
            receipt.update(installed_api_sources=fingerprints,installed_numeric_sources=numeric,installed_adapter_sources=adapters)
            root=frozen/CURRENT_TRIAL_PREFIX
            def paths(role):return [root/PurePosixPath(r['path']) for r in capture['inputs'] if r['role']==role]
            receipt['native_execution']='ATTEMPTED'
            audit=run_native_base_rotation_audit(paths('model')[0],paths('dictionary'),paths('phil'),expected,saved,
                {'result':proof,'correction_core_sha256':_sha((root/'correction_core.py').read_bytes())},plan,
                session/'native_rotation',phenix.executables['phenix.python'],environment=phenix.environment,
                phenix_version=phenix.version,timeout_seconds=args.timeout_seconds)
            receipt['native_rotation_audit']=audit;receipt['native_execution']=audit['execution']['status']
            if audit['status']!='REVIEW':raise ValueError('Native rotation audit did not complete; inspect retained evidence')
            result=audit['result'];receipt['rotation_derivative_qualification']=result['rotation_derivative_qualification']
            print('Fresh native manager and source checks: PASS',flush=True)
            print('Rotation derivative qualification:',result['rotation_derivative_qualification'],flush=True)
            for label,case in result['cases'].items():
                print(label,'sampled rotations:',case['sampled_rotation_derivatives_consistent'],flush=True)
                for group in case['groups']:
                    sample=group['lowest_sampled_target']
                    print(group['site'],'lowest angular sample:',sample['angle_degrees'],'degrees; target',sample['target'],'; change',sample['change_from_baseline'],flush=True)
            print('Native energy evaluations:',result['evaluation_calls'],'/',result['max_evaluation_calls'],flush=True)
            if (_fingerprints(phenix,capture)!=fingerprints or _fingerprints(phenix,numeric_capture)!=numeric
                    or _fingerprints(phenix,adapter_capture)!=adapters):raise ValueError('Installed sources changed')
        if any((frozen/PurePosixPath(n)).read_bytes()!=d for n,d in members.items()):raise ValueError('Frozen source evidence changed')
        if review.read_bytes()!=original:raise ValueError('Original review ZIP changed')
        receipt.update(analysis_completed=True,original_archive_preserved=True,frozen_inputs_preserved=True)
        _json(session/'probe_receipt.json',receipt)
        print('Diagnostic: REVIEW (orientation/source evidence; no optimization or adoption)',flush=True)
        print('REVIEW ZIP:',_review_zip(session),flush=True);return 2
    except Exception as exc:
        receipt.update(analysis_completed=False,error=str(exc))
        if session:
            receipt['original_archive_preserved']=bool(original is not None and review and review.read_bytes()==original)
            receipt['frozen_inputs_preserved']=bool(members is not None and all((session/'inputs/review'/PurePosixPath(n)).is_file()
                and (session/'inputs/review'/PurePosixPath(n)).read_bytes()==d for n,d in members.items()))
            if not (session/'probe_receipt.json').exists():_json(session/'probe_receipt.json',receipt)
            print('REVIEW ZIP:',_review_zip(session),flush=True)
        print('Base-orientation audit stopped:',str(exc),file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())
