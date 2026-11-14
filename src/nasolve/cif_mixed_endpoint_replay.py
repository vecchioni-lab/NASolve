"""Portable saved C93 readback, preserving the original recipe and evidence.

The C93 producer/worker/reader remain unchanged. This explicit adapter retains
their envelope, source, derivative, serializer and native-mechanics checks;
only derived Cartesian report comparisons use the bounded shared policy.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import math
import tempfile

from . import cif_mixed_endpoint_window as window
from .cif_geometry_report_replay import compare_geometry_reports

POLICY_ID = 'cif-saved-endpoint-portable-replay-v1'
REPORT = 'mixed_endpoint_saved_replay.json'


def _need(value):
    if not value:
        raise ValueError('Saved endpoint portable replay does not reproduce')


def _analysis(root, parents, report, expected, proof, cases, plan, geometry, model, cifs, phils):
    from .cif_mixed_geometry import _decision
    from .cif_fixed_geometry import write_geometry_candidate, review_fixed_coordinates, qualify_fixed_policy_geometry
    from .cif_captured_geometry import review_captured_geometry
    from .cif_mixed_linked_recovery import _capture

    qualification = {'status': 'NOT_RUN'}
    checks, comparisons = {}, {}
    summary, capture = None, None
    count = int('returncode' in report['execution'])
    candidate = root/'candidate/saved_mixed_endpoint.pdb'
    if 'receipt' in report['native_readback']:
        ref = report['native_readback']['receipt']
        window._resolve(root, *parents, ref)
        capture = _capture(root, {**ref, 'anchor': 'mixed_linked_recovery_directory'}, candidate, cifs, phils)
        count += int('returncode' in capture.get('execution', {}))
        _need(capture['phenix_version'] == report['phenix_version']
              and capture['executable_sha256'] == report['executable_sha256']
              and capture['execution']['timeout_seconds'] == min(report['timeout_seconds'], 60))
    _need(report['new_native_calls'] == count and count <= 2)
    if report['execution']['status'] == 'COMPLETED':
        try:
            qualification = window._validate_result(root, window._load(root/'job/endpoint_result.json'), expected, proof, cases, plan)
        except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, ZeroDivisionError) as exc:
            qualification = {'status': 'REVIEW', 'finding_type': type(exc).__name__, 'finding': 'ADAPTIVE_EVIDENCE_INCOMPLETE'}
        checks['qualified_endpoint_derivatives'] = qualification['status'] == 'ADAPTIVE_ENDPOINT_DERIVATIVES_PASS'
        if checks['qualified_endpoint_derivatives']:
            summary = deepcopy(qualification['summary'])
            try:
                with tempfile.TemporaryDirectory(prefix='endpoint-replay-serialization-') as temporary:
                    path = Path(temporary).resolve()/'model.pdb'
                    serialization = write_geometry_candidate(model, path, expected, cases['full_precision'])
                    _need(path.read_bytes() == candidate.read_bytes()
                          and window._load(root/'serialization.json') == serialization)
                comparisons['full_precision'] = compare_geometry_reports(
                    window._load(root/'full_precision_geometry.json'), review_fixed_coordinates(expected, cases['full_precision']))
                _need(comparisons['full_precision']['consistent'])
                checks['exact_identity_serialization'] = True
            except (OSError, ValueError, KeyError, TypeError, IndexError):
                checks['exact_identity_serialization'] = False
            checks['fixed_native_mechanics'] = False
            checks['fresh_rounded_target'] = False
            if (capture is not None and capture.get('status') == 'REVIEW'
                    and capture['execution'].get('status') == 'COMPLETED' and capture['execution'].get('returncode') == 0):
                try:
                    after = capture['native_validation']
                    mechanics = qualify_fixed_policy_geometry(expected, after, candidate, window._load(root/'serialization.json'))
                    _need(window._load(root/'native_mechanics.json') == mechanics)
                    comparisons['pdb_rounded'] = compare_geometry_reports(
                        window._load(root/'rounded_geometry.json'), review_captured_geometry(after))
                    _need(comparisons['pdb_rounded']['consistent'])
                    checks['fixed_native_mechanics'] = mechanics['mechanics_checks_pass'] is True
                    checks['fresh_rounded_target'] = window._close(after['energy_inventory']['snapshots'][0]['target'], geometry['serialized']['target'])
                except (OSError, ValueError, KeyError, TypeError, IndexError):
                    pass
            checks['nonworse_fixed_objective'] = all(geometry[key]['target'] <= geometry['initial']['target']
                + 1e-8 + 1e-10*abs(geometry['initial']['target']) for key in ['final', 'serialized'])
            summary['endpoint_native_readback'] = 'PASS' if checks['fixed_native_mechanics'] and checks['fresh_rounded_target'] else 'REVIEW'
        elif capture is not None:
            _need(False)
    elif capture is not None:
        _need(False)
    return qualification, _decision(checks, deepcopy(geometry['stopping'])), summary, comparisons


def replay_saved_endpoint_window(directory, *, torsion_directory, geometry_directory, gradient_directory,
                                 context_directory, linked_parent_directory, parent_archive_sha256):
    """Recompute a saved verdict without discovery, subprocesses or input writes.

    The caller must bind the outer review archive. The scientific parent is
    the C91 digest already required by the original C93 contract. Preparation
    is rebuilt by the unchanged C93 module, keeping captured code data-only.
    """
    root = Path(directory)
    parents = tuple(map(Path, (torsion_directory, geometry_directory, gradient_directory,
                              context_directory, linked_parent_directory)))
    report = window._load(root/window.REPORT)
    _need(not any(p.is_symlink() for p in [root, *root.parents]))
    _need(window._digest(parent_archive_sha256) and report['parent_archive_sha256'] == parent_archive_sha256
        and type(report['schema_version']) is int and report['schema_version'] == 1
        and report['policy_id'] == window.POLICY_ID and report['status'] in {'PREPARED_ONLY', 'REVIEW', 'MIXED_ENDPOINT_QUALIFIED'}
        and type(report['maximum_native_calls']) is int and report['maximum_native_calls'] == 2
        and type(report['new_native_calls']) is int and 0 <= report['new_native_calls'] <= 2
        and type(report['timeout_seconds']) is int and 1 <= report['timeout_seconds'] <= 600
        and report['maximum_evaluation_calls'] == window.MAX_EVALUATIONS
        and report['maximum_refined_directions'] == window.MAX_DIRECTIONS
        and report['parent_archive_verification'] == 'CALLER_VERIFIED_EXACT_C91_CAPSULE_BYTES; SCIENCE_BOUND_BY_MAINTAINED_PARENT_READERS'
        and report['scientific_qualification'] == 'NOT_ASSESSED' and report['automatic_adoption'] is False
        and report['requires_cif_review'] is False and report['policy_authority'] == 'NARestraints'
        and report['source_chemical_findings'] == 'PRESERVED_IN_BOUND_CONTEXT; NOT_PROMOTED_BY_ENDPOINT_QUALIFICATION'
        and all(report[k] == 'NOT_RUN' for k in ['model_optimization', 'dictionary_generation', 'readyset_execution',
            'coot_execution', 'refinement', 'cache_writes', 'captured_code_execution']))
    refs = report['outputs']
    _need(len(refs) == len({r['path'] for r in refs}) and all(r['anchor'] == window.ANCHOR for r in refs))
    for ref in refs:
        window._resolve(root, *parents, ref)
    actual = set()
    for path in root.rglob('*'):
        _need(not path.is_symlink())
        if path.is_file() and path != root/window.REPORT and path.suffix not in {'.pkl', '.pickle', '.pyc'}:
            actual.add(path.relative_to(root).as_posix())
    _need(actual == {r['path'] for r in refs})
    source, model, cifs, phils, expected, proof, cases, references, selection, geometry, plan, bindings = window._inputs(*parents, parent_archive_sha256)
    _need(report['inputs'] == bindings and report['original_coordinate_decision'] == source['coordinate_decision']
          and report['original_geometry_qualification'] == source['original_geometry_qualification'])
    with tempfile.TemporaryDirectory(prefix='endpoint-replay-recipe-') as temporary:
        replay = Path(temporary).resolve()
        preparation = window._prepare(replay, model, cifs, phils, expected, proof, cases, references, selection, plan)
        _need(preparation == report['preparation'])
        for path in replay.rglob('*'):
            if path.is_file():
                _need((root/path.relative_to(replay)).read_bytes() == path.read_bytes())
    execution = report['execution']
    if report['new_native_calls'] == 0:
        _need((report['status'] == 'PREPARED_ONLY' and execution == {'status': 'NOT_RUN'})
              or (report['status'] == 'REVIEW' and execution['status'] == 'LAUNCH_FAILED' and isinstance(execution['error'], str)))
    else:
        _need(report['status'] != 'PREPARED_ONLY' and execution['status'] in {'COMPLETED', 'FAILED', 'TIMED_OUT', 'WAIT_FAILED'}
            and type(execution['returncode']) is int
            and (execution['status'] != 'COMPLETED' or execution['returncode'] == 0)
            and (execution['status'] != 'FAILED' or execution['returncode'] != 0)
            and type(execution['elapsed_seconds']) in (int, float) and math.isfinite(execution['elapsed_seconds'])
            and execution['elapsed_seconds'] >= 0 and window._digest(report['executable_sha256'])
            and isinstance(report['phenix_version'], str) and bool(report['phenix_version']))
    comparisons = {}
    if report['status'] == 'PREPARED_ONLY':
        _need(report['qualification'] == {'status': 'NOT_RUN'} and report['native_readback'] == {'status': 'NOT_RUN'}
              and report['coordinate_decision'] == source['coordinate_decision'])
    else:
        qualification, decision, summary, comparisons = _analysis(
            root, parents, report, expected, proof, cases, plan, geometry, model, cifs, phils)
        _need(report['qualification'] == qualification and report['coordinate_decision'] == decision
              and report.get('summary') == summary
              and (report['status'] == 'MIXED_ENDPOINT_QUALIFIED') is decision['endpoint_usable'])
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'SAVED_ENDPOINT_REPLAY_PASS',
        'source_report': window._ref(root/window.REPORT, root), 'scientific_parent_archive_sha256': parent_archive_sha256,
        'original_status': report['status'], 'qualification': deepcopy(report['qualification']),
        'summary': deepcopy(report.get('summary')), 'coordinate_decision': deepcopy(report['coordinate_decision']),
        'descriptive_geometry_replay': comparisons, 'saved_native_calls': report['new_native_calls'],
        'new_native_calls': 0, 'model_optimization': 'NOT_RUN', 'captured_code_execution': 'NOT_RUN',
        'dictionary_generation': 'NOT_RUN', 'cache_writes': 'NOT_RUN', 'production_checkpoint': 'NOT_CREATED',
        'automatic_adoption': False, 'requires_cif_review': False, 'scientific_qualification': 'NOT_ASSESSED'}
