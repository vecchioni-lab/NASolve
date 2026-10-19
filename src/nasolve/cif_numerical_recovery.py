"""Separate numerical candidates from exact source chemistry and source coordinates.

Selection uses declared restraint contradictions, never a residue allowlist or
an experimental model fit. No native dictionary replacement is performed here.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re
from tempfile import mkdtemp

from .cif_doctor import assess_dictionaries, compare_dictionaries, _number
from .cif_generation import (generate_elbow_candidate, inspect_component_generation,
                             _ideal_seed, _CHEMICAL_FIELDS, _explicit_formal_charges)
from .ligand_profiles import _blocks, _emit

POLICY_ID = 'cif-source-graph-numerical-recovery-v1'


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _same(a, b):
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(_same(v, b[k]) for k, v in a.items())
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if type(a) is float:
        return type(b) in (int, float) and math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, abs_tol=1e-8, rel_tol=1e-10)
    return a == b


def validate_rotation_evidence(result, plan, saved, signature):
    """Recompute saved finite differences; trust neither flags nor minima claims."""
    from .cif_base_rotation_audit import ANGLES, STEPS, FAMILIES
    try:
        _need(result['analysis_completed'] and result['rotation_derivative_qualification'] == 'SAMPLED_ROTATION_DERIVATIVES_PASS', 'Rotation derivative qualification is incomplete')
        _need(result['constraint_signature_before'] == result['constraint_signature_after'] == signature, 'Rotation static constraints differ')
        _need(set(result['cases']) == {'full_precision', 'pdb_rounded'}, 'Require both saved coordinate precisions')
        groups = plan['groups']
        _need(1 <= len(groups) <= 6 and len({g['site'] for g in groups}) == len(groups), 'Invalid rotation groups')
        expected_calls = 17 + 2 * (16 + len(groups) * (8*8 + 9*8 + 7*8))
        _need(result['preflight_evaluations'] == 17 and result['evaluation_calls'] == expected_calls <= 3000
              and result['audit_evaluation_calls'] == expected_calls - 17 and result['max_evaluation_calls'] == 3000, 'Rotation evaluation accounting differs')
        directions = 0
        def derivative(row):
            nonlocal directions
            values = row['samples']
            _need([v['step_radians'] for v in values] == list(STEPS), 'Missing rotation derivative steps')
            analytic = row['analytical_per_radian']
            _need(type(analytic) in (float, int) and math.isfinite(analytic), 'Nonfinite rotation derivative')
            flags = []
            for v in values:
                numeric = (v['plus_target'] - v['minus_target']) / (2*v['step_radians'])
                error = abs(numeric - analytic)
                bound = 1e-4 + 1e-4 * max(abs(numeric), abs(analytic))
                flag = math.isfinite(numeric) and error <= bound
                _need(_same(numeric, v['numerical']) and _same(error, v['absolute_error']) and _same(bound, v['bound']) and v['consistent'] is flag, 'Raw rotation derivative evidence differs')
                flags.append(flag)
            consistent = any(flags[i] and flags[i+1] for i in range(3))
            _need(consistent and row['consistent'] is consistent, 'Rotation derivative requires review')
            directions += 1
        for label, case in result['cases'].items():
            _need(all(case[k] is True for k in ['captured_snapshot_matches', 'baseline_repeats_consistent', 'sampled_rotation_derivatives_consistent']), 'Rotation controls require review')
            _need(set(case['baseline']) == set(FAMILIES), 'Missing rotation category baselines')
            for f, value in case['baseline'].items():
                old = saved['endpoint_gradient_audit']['cases'][label]['families'][f]['baseline']
                _need(_same(value['target'], old['target']) and _same(value['gradient'], old['gradient']), 'Rotation saved endpoint snapshot differs')
            _need([g['site'] for g in case['groups']] == [g['site'] for g in groups], 'Rotation group plan differs')
            baseline = case['baseline']['all']['target']
            for group in case['groups']:
                profile = group['profile']
                _need([v['angle_degrees'] for v in profile] == list(ANGLES), 'Rotation angular grid differs')
                _need(group['periodic_energy_consistent'] and _same(profile[0]['target'], profile[-1]['target'])
                      and 0 <= group['max_rigid_distance_change'] <= 1e-9, 'Rotation rigid/periodic controls differ')
                for v in profile:
                    _need(_same(v['change_from_baseline'], v['target'] - baseline)
                          and set(v['families']) == set(FAMILIES), 'Rotation profile/category inventory differs')
                    total = math.fsum(v['families'][f]['target'] for f in FAMILIES[1:])
                    _need(v['target_additivity']['consistent'] and _same(total, v['target'])
                          and _same(total, v['target_additivity']['sum_controls']), 'Rotation target additivity differs')
                    grad = v['gradient_additivity']
                    _need(grad['consistent'] and 0 <= grad['difference_norm'] <= 1e-8 + 1e-10*max(1., v['families']['all']['gradient_norm']), 'Rotation gradient additivity differs')
                    _need(_same(v['derivative']['analytical_per_radian'], v['families']['all']['rotational_derivative_per_radian']), 'Rotation slope summary differs')
                    derivative(v['derivative'])
                _need(set(group['zero_angle_family_derivatives']) == set(FAMILIES[1:]), 'Missing isolated category derivatives')
                zero = profile[list(ANGLES).index(0)]
                for f, row in group['zero_angle_family_derivatives'].items():
                    _need(_same(row['analytical_per_radian'], zero['families'][f]['rotational_derivative_per_radian']), 'Rotation family slope differs')
                    derivative(row)
                low = min(profile, key=lambda v: v['target']);summary = group['lowest_sampled_target']
                _need(summary['angle_degrees'] == low['angle_degrees'] and _same(summary['target'], low['target'])
                      and _same(summary['change_from_baseline'], low['change_from_baseline'])
                      and summary['interpretation'] == 'DIAGNOSTIC_SAMPLE_NOT_A_CANDIDATE_OR_OPTIMUM', 'Rotation minimum summary differs')
        return {'directions_passed': directions, 'finite_difference_samples': 4*directions,
                'interpretation': 'SAMPLED_DERIVATIVES_ONLY_NOT_A_MINIMUM_OR_CHEMISTRY_PROOF'}
    except (KeyError, TypeError, IndexError, OverflowError) as exc:
        raise ValueError('Incomplete saved rotation evidence') from exc


def plan_numerical_recovery(native, dictionaries, *, components=None):
    """Select complete source components with a declared plane/angle conflict."""
    paths = [Path(p).resolve(strict=True) for p in dictionaries]
    _need(len(paths) == len(set(paths)), 'Duplicate dictionary inputs')
    assessment = assess_dictionaries(paths, stage='numerical-recovery-source')
    selected, blocked, unchanged, deferred = [], [], [], []
    if components is not None:
        _need(components and len(set(components)) == len(components), 'Require unique explicit component selection')
    seen = set()
    for component in assessment['components']:
        code = component['component_id'];index = component['input_index']
        findings = [f for f in component['findings'] if f['code'] == 'plane-angle-compatibility' and f['status'] == 'REVIEW']
        if not findings:
            unchanged.append(code);continue
        if components is not None and code not in components:
            deferred.append({'component': code, 'findings': findings, 'reason': 'Outside explicit candidate selection'});continue
        if (code in seen or len([c for c in assessment['components'] if c['component_id'] == code]) != 1
                or len([c for c in assessment['components'] if c['input_index'] == index]) != 1
                or component['verdicts']['graph'] != 'PASS'):
            blocked.append({'component': code, 'reason': 'Require one independent graph-valid source component'});continue
        seen.add(code);rows = [r for r in native['monomer_mappings']['rows'] if r['resname'] == code]
        if not rows or len({r['site'] for r in rows}) != len(rows):
            blocked.append({'component': code, 'reason': 'Missing or ambiguous model context'});continue
        payload = paths[index].read_bytes()
        selected.append({'component': code, 'input_index': index, 'source_sha256': sha256(payload).hexdigest(),
                         'source_size': len(payload), 'sites': sorted(r['site'] for r in rows),
                         'site_modifiers': {r['site']: r['chem_mod_ids'] for r in rows}, 'findings': findings})
    if components is not None:
        for code in set(components) - {r['component'] for r in selected} - {r['component'] for r in blocked}:
            blocked.append({'component': code, 'reason': 'No eligible source conflict in declared inputs'})
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW', 'selected': selected,
            'explicit_components': components, 'deferred_components': deferred,
            'recovery_codes': sorted(r['component'] for r in selected), 'blocked': blocked,
            'unchanged_components': sorted(set(unchanged)), 'automatic_adoption': False,
            'selection': 'Declared source plane/angle conflict, independent of model residual or component code.',
            'linked_site_validation': 'NOT_RUN', 'native_proxy_validation': 'NOT_RUN',
            'limitations': ['A source contradiction motivates regeneration, not chemical approval or replacement targets.',
                           'Existing modifiers are recorded, not composed or adopted by this candidate-only slice.']}


def prepare_graph_generation_source(source, code, output):
    """Remove numerical parameters; preserve declarations and explicit seed origin.

    Curated atom x/y/z may seed naming/initial geometry when complete ideal
    coordinates are absent. They are not asserted to be independent ideal
    coordinates, and no experimental model is read or used for targets.
    """
    source, output = Path(source).resolve(strict=True), Path(output).absolute()
    _need(re.fullmatch(r'[A-Za-z0-9]{1,3}', code), 'Unsupported component identifier')
    if output.exists() or output.is_symlink():
        raise FileExistsError('Graph source output already exists')
    _need(output.resolve() != source, 'Output must be separate from source')
    _need(not any(p.is_symlink() for p in output.parents), 'Output parent cannot traverse a symlink')
    original = source.read_bytes();before = assess_dictionaries([source], stage='numerical-recovery-source')
    _need(len(before['components']) == 1 and before['components'][0]['component_id'] == code
          and before['components'][0]['verdicts']['graph'] == 'PASS', 'Require one graph-valid source component')
    from .cif_linked_preparation import component_values
    values = {k.lower(): v for k,v in component_values(source, code).items()}
    atom = '_chem_comp_atom.';bond = '_chem_comp_bond.';chir = '_chem_comp_chir.'
    count = len(values[atom+'atom_id'])
    ideal = [atom+'pdbx_model_cartn_'+a+'_ideal' for a in 'xyz'];declared = [atom+a for a in 'xyz']
    if any(k in values for k in ideal):
        keys = ideal;origin = 'SOURCE_IDEAL_COORDINATES'
    else:
        keys = declared;origin = 'SOURCE_DECLARED_COORDINATES_NOT_INDEPENDENT_IDEAL'
    _need(all(k in values and len(values[k]) == count for k in keys), 'Require one complete declared coordinate family')
    for i in range(count):
        for k in keys:
            value = _number(values[k][i]);_need(value is not None and math.isfinite(value), 'Missing or nonfinite source coordinate')
        charges = [_number(values[k][i]) for k in [atom+'charge', atom+'pdbx_formal_charge'] if k in values]
        _need(charges and all(c is not None and c.is_integer() and abs(c) <= 9 for c in charges)
              and len(set(charges)) == 1, 'Require unambiguous explicit integer formal charges')
    graph = {'data_': 'comp_'+code, '_chem_comp.id': [code]}
    atom_fields = {'comp_id', 'atom_id', 'alt_atom_id', 'type_symbol', 'charge', 'pdbx_formal_charge',
                   'partial_charge', 'pdbx_aromatic_flag', 'aromatic', 'pdbx_stereo_config',
                   'stereo_config', 'pdbx_leaving_atom_flag'}
    bond_fields = {'comp_id', 'atom_id_1', 'atom_id_2', 'value_order', 'type',
                   'pdbx_aromatic_flag', 'aromatic', 'pdbx_stereo_config', 'stereo_config'}
    chir_fields = {'comp_id', 'id', 'atom_id_centre', 'atom_id_1', 'atom_id_2', 'atom_id_3', 'volume_sign'}
    for key, column in values.items():
        if key.startswith(atom) and key[len(atom):] in atom_fields:
            graph[key] = column
        elif key.startswith(bond) and key[len(bond):] in bond_fields:
            graph[key] = column
        elif key.startswith(chir) and key[len(chir):] in chir_fields:
            graph[key] = column
        elif key in {'_chem_comp.type', '_chem_comp.group', '_chem_comp.name', '_chem_comp.three_letter_code'}:
            graph[key] = column
    # mmCIF is case insensitive, but installed eLBOW accesses CCD atom-row
    # attributes using the canonical mixed-case Cartn spelling. Keep internal
    # lookup normalized while emitting the external consumer's exact contract.
    emitted_ideal = [atom+'pdbx_model_Cartn_'+axis+'_ideal' for axis in 'xyz']
    for k, target in zip(keys, emitted_ideal):
        graph[target] = values[k]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as handle:
        handle.write(_emit(graph))
    # Both exact parsed graph comparison and the generator's strict seed adapter
    # must succeed. The full original, dropped metadata and raw comparison persist.
    comparison = compare_dictionaries([source], [output])
    changes = [r for r in comparison['differences'] if r['component_id'] == code and r['field'] in _CHEMICAL_FIELDS]
    _need(not changes, 'Graph source changed chemical declarations')
    _ideal_seed(output, code)
    _need(source.read_bytes() == original, 'Original source changed during preparation')
    payload = output.read_bytes()
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'component': code, 'status': 'SOURCE_REVIEW',
            'source_sha256': sha256(original).hexdigest(), 'source_size': len(original),
            'graph_source_sha256': sha256(payload).hexdigest(), 'graph_source_size': len(payload),
            'source_preserved': True, 'coordinate_origin': origin, 'experimental_model_used': False,
            'coordinate_tag_serialization': 'CCD_CANONICAL_CARTN_CASE',
            'coordinate_input_fields': keys, 'coordinate_output_fields': emitted_ideal,
            'numerical_parameters': 'REMOVED_FOR_INDEPENDENT_GENERATION',
            'removed_fields': sorted(set(values)-{k.lower() for k in graph}),
            'chemical_comparison': {'status': 'EXACT_DECLARATIONS', 'fields': sorted(_CHEMICAL_FIELDS), 'comparison': comparison},
            'limitations': ['Seed coordinates supply naming/initial geometry only; they are not independent validation or final restraint targets.',
                           'Original aliases/descriptors/numerical targets remain in the frozen source, never a chemical authority inferred from a model.']}


def generate_numerical_recovery(source, code, output_parent, executable, *, environment, phenix_version, timeout_seconds=600):
    """Run existing eLBOW isolation/chemistry guards against a graph-only seed."""
    source = Path(source).resolve(strict=True);parent = Path(output_parent).resolve()
    _need(parent != source.parent and source.parent not in parent.parents, 'Output must be outside original source directory')
    original = source.read_bytes();parent.mkdir(parents=True, exist_ok=True)
    work = Path(mkdtemp(prefix='cif-numerical-recovery-', dir=parent));frozen = work/'original/source.cif'
    frozen.parent.mkdir();frozen.write_bytes(original)
    result = {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'FAILED', 'component': code,
              'candidate_directory': str(work), 'source_sha256': sha256(original).hexdigest(),
              'source_size': len(original), 'automatic_adoption': False, 'model_editing': 'NOT_RUN',
              'model_optimization': 'NOT_RUN', 'native_proxy_validation': 'NOT_RUN', 'linked_site_validation': 'NOT_RUN'}
    try:
        graph = work/'graph/source.cif'
        result['graph_preparation'] = prepare_graph_generation_source(frozen, code, graph)
        generation = generate_elbow_candidate(graph, code, work/'generation', executable,
            environment=environment, phenix_version=phenix_version, timeout_seconds=timeout_seconds)
        result['generation'] = generation
        if generation['status'] == 'CANDIDATE_REVIEW':
            candidate = Path(generation['candidate_directory'])/'candidate.cif'
            inspection = inspect_component_generation(frozen, candidate, code)
            result['original_source_inspection'] = inspection;result['status'] = inspection['status']
            left = inspection['source_assessment']['components']
            right = inspection['generated_assessment']['components']
            if len(left) == len(right) == 1:
                charges = _explicit_formal_charges(left[0])
                generated_charges = _explicit_formal_charges(right[0])
                preserved = bool(charges) and charges == generated_charges
                result['formal_charge_evidence'] = {'status': 'PASS' if preserved else 'REVIEW',
                    'source_explicit_formal_charges': charges, 'candidate_explicit_formal_charges': generated_charges,
                    'partial_charge_substituted': False}
                if not preserved:
                    result.update(status='REJECTED', error='Source formal-charge declarations changed or disappeared')
            result['candidate'] = {'anchor': 'candidate_directory', 'path': candidate.relative_to(work).as_posix(),
                                   'sha256': sha256(candidate.read_bytes()).hexdigest(), 'size': candidate.stat().st_size}
        else:
            result['status'] = 'REJECTED'
            result['original_source_inspection'] = inspect_component_generation(frozen,
                Path(generation['candidate_directory'])/'candidate.cif' if (Path(generation['candidate_directory'])/'candidate.cif').is_file() else None, code)
    except (OSError, ValueError) as exc:
        result.update(status='REJECTED', error=type(exc).__name__+': '+str(exc))
    result['source_preserved'] = source.read_bytes() == original and frozen.read_bytes() == original
    if not result['source_preserved']:
        result.update(status='REJECTED', error='Original or frozen source changed')
    result['outputs'] = [{'anchor': 'candidate_directory', 'path': p.relative_to(work).as_posix(),
        'sha256': sha256(p.read_bytes()).hexdigest(), 'size': p.stat().st_size} for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):
        result.update(status='REJECTED', error='Unexpected candidate symlink')
    (work/'numerical_recovery_receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+'\n')
    return result
