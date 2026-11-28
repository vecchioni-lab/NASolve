"""Bounded ordinary ReadySet and fixed native reads of a constructed fixture.

The fixture supplies immutable coordinates, sources and explicit NAR intent.
This diagnostic records supplier/generator changes; it neither repairs chemical
state nor adopts a dictionary, model or production checkpoint.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import time

POLICY_ID = 'cif-mixed-pair-native-membership-v1'
ANCHOR = 'mixed_native_directory'
CANONICAL = {'DA', 'DC', 'DG', 'DT'}


def _safe(name):
    return (isinstance(name, str) and bool(name) and not name.startswith('/')
        and '\\' not in name and ':' not in name
        and not any(ord(c) < 32 or ord(c) == 127 for c in name)
        and all(p not in {'', '.', '..'} for p in name.split('/')))


def _ref(path, root):
    path, root = Path(path), Path(root)
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Mixed native artifact cannot traverse a symlink')
    name = path.relative_to(root).as_posix()
    if not _safe(name): raise ValueError('Unsafe mixed native artifact')
    data = path.read_bytes()
    return {'anchor': ANCHOR, 'path': name, 'sha256': sha256(data).hexdigest(), 'size': len(data)}


def _resolve(root, ref):
    if not isinstance(ref, dict) or ref.get('anchor') != ANCHOR or not _safe(ref.get('path')):
        raise ValueError('Unsafe mixed native reference')
    path = root / ref['path']
    if _ref(path, root) != ref: raise ValueError('Mixed native artifact bytes differ')
    return path


def _dump(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def _publish(output, report):
    if any(p.is_symlink() for p in output.rglob('*')): raise ValueError('Unexpected mixed native output symlink')
    report['outputs'] = [_ref(p, output) for p in sorted(output.rglob('*'))
        if p.is_file() and p != output / 'mixed_native.json']
    # Serialized native output is opaque, never loaded. It is deliberately
    # excluded from the returned capsule by the existing review transport.
    report['outputs'] = [r for r in report['outputs'] if Path(r['path']).suffix not in {'.pickle', '.pkl', '.pyc'}]
    _dump(output / 'mixed_native.json', report)
    read_mixed_native(output)
    return report


def _native_ok(capture):
    native = capture.get('native_validation') or {}
    return (capture.get('execution', {}).get('status') == 'COMPLETED'
        and capture['execution'].get('returncode') == 0
        and capture.get('source_preserved') is True and capture.get('frozen_inputs_preserved') is True
        and capture.get('symlink_outputs') == [] and native.get('status') == 'REVIEW'
        and native.get('fatal_problems') is None and native.get('unused_definitions') == []
        and native.get('unsupported_fields') == [] and native.get('inventory_detail') == 'linked')


def qualify_mixed_native(before, after, model, active_phil, plan, sources, dictionaries=(), *, site_projections=None):
    """Compare active NAR membership using freshly resolved native atom indices.

    PDB-order request indices from the compiler are never native indices. The
    exact frozen PHIL is resolved against the first native inventory, then the
    established membership qualifier proves the complete before/after delta.
    """
    from .cif_na_policy import _requests, qualify_na_policy
    from .cif_fragment_restoration import _model
    from .cif_fixed_geometry import _fixed_policy
    from .cif_candidate_usability import energy_inventory_checks
    from .cif_linked_qualification import native_backbone_links
    from .cif_construction_native import NATIVE_KINDS, _triple_readback
    checks = {}; triples = {}; membership = {'status': 'NOT_RUN'}; error = None
    try:
        _model(before, Path(model), coordinates_match=True)
        _model(after, Path(model), coordinates_match=True)
        checks['exact_native_models'] = True
        for label, record in [('baseline', before), ('active', after)]:
            points = record['geometry'].get('sites_cart_exact')
            checks[label + ':native_coordinate_roundtrip'] = (isinstance(points, list) and len(points) == len(record['atoms'])
                and all(len(p) == len(a['xyz']) == 3 and all(type(x) in (int, float) and math.isfinite(x)
                    and abs(x-y) <= 1e-12 for x, y in zip(p, a['xyz'])) for p, a in zip(points, record['atoms'])))
        checks['secondary_structure_guessing_disabled'] = _fixed_policy(before) and _fixed_policy(after)
        requests = _requests(Path(active_phil).read_text(), before['atoms'])
        checks['active_requests_present'] = bool(requests)
        checks['declared_pair_stack_parallelity_count'] = sum(r['kind'] == 'parallelity' for r in requests) == len(plan['all_pairs']) + len(plan['stack_edges'])
        policy = {'compiled_requests': requests}
        membership = qualify_na_policy(before, after, policy)
        checks['exact_narestraints_membership_and_unaffected_proxies'] = membership['mechanics_checks_pass'] is True
        expected_links = {tuple(edge) for edge in plan['stack_edges']}
        first, second = native_backbone_links(before), native_backbone_links(after)
        checks['all_declared_backbone_links_exact'] = set(first) == expected_links and first == second
        for label, record in [('baseline', before), ('active', after)]:
            checks[label + ':complete_interpretation'] = (record.get('status') == 'REVIEW'
                and record.get('fatal_problems') is None and record.get('unused_definitions') == []
                and record.get('unsupported_fields') == [] and record.get('inventory_detail') == 'linked')
            details = record['geometry']['proxy_details']
            from .cif_terminal_qualification import _proxy_subset
            for kind in NATIVE_KINDS: _proxy_subset(record, set(), kind)
            checks[label + ':named_proxy_identity_binding'] = True
            checks[label + ':complete_proxy_inventory'] = (set(details) == NATIVE_KINDS
                and all(record['geometry']['proxy_counts'].get(k) == len(v) for k, v in details.items()))
            checks.update({label + ':' + k: v for k, v in energy_inventory_checks(record).items()})
            rows = record['monomer_mappings']['rows']
            mapping = {r['site']: r for r in rows}
            checks[label + ':exact_monomer_sites'] = (len(rows) == len(mapping)
                and {s: r['resname'].strip() for s, r in mapping.items()} == plan['target_site_components'])
            checks[label + ':complete_heavy_sites'] = all(r.get(k, {}).get('status') == 'RECORDED'
                and r[k]['atom_ids'] == [] for r in rows for k in ['missing_non_hydrogen_atoms', 'unexpected_atoms'])
            checks[label + ':dna_classification'] = all(r['metadata'].get('group') == 'DNA'
                and r['metadata'].get('classification') == {'status': 'RECORDED', 'value': 'DNA'} for r in rows)
            finite = True
            for kind, proxies in details.items():
                for row in proxies:
                    weights = row.get('weights', [row.get('weight')])
                    finite &= all(type(w) in (int, float) and math.isfinite(w)
                        and (w > 0 or kind == 'const_dihedral' and w == 0 and row.get('periodicity') == 0) for w in weights)
                    keys = [] if kind == 'planarity' else ['distance_ideal'] if kind in {'bond_simple', 'bond_asu'} else ['angle_ideal'] if kind in {'angle', 'dihedral', 'const_dihedral'} else ['volume_ideal'] if kind == 'chirality' else ['target_angle_deg']
                    finite &= all(type(row.get(k)) in (int, float) and math.isfinite(row[k]) for k in keys)
            checks[label + ':finite_positive_parameters'] = finite
        from .ligand_profiles import dictionary_component_codes
        from .cif_terminal_qualification import definition_projection_checks
        projection_files = {}
        for dictionary in dictionaries:
            for code in dictionary_component_codes(Path(dictionary)):
                if code in projection_files: raise ValueError('Ambiguous effective native dictionary component')
                projection_files[code] = Path(dictionary)
        projections = {site: (projection_files[code], code) for site, code in plan['target_site_components'].items()
            if code in projection_files}
        checks['explicit_effective_dictionary_coverage'] = set(projection_files) >= set(sources) - CANONICAL
        if site_projections is not None:
            valid = (isinstance(site_projections, dict) and bool(site_projections)
                and all(site in projections and isinstance(item, (list, tuple)) and len(item) == 2
                    and item[1] == plan['target_site_components'][site]
                    and dictionary_component_codes(Path(item[0])) == {item[1]}
                    for site, item in site_projections.items()))
            checks['explicit_site_projection_scope'] = valid
            if not valid: raise ValueError('Explicit site projection differs from the declared component/site')
            projections.update({site: (Path(path), code) for site, (path, code) in site_projections.items()})
        projection_checks = definition_projection_checks(after, projections)
        checks['exact_explicit_effective_definitions'] = bool(projection_checks) and all(r['status'] == 'PASS' for r in projection_checks)
        for code in ['PDU', '5PC']:
            for site, component in plan['target_site_components'].items():
                if component != code: continue
                triples[site] = _triple_readback(sources[code], code, after, site)
                checks['declared_triple_targets:' + site] = (bool(triples[site]['triple_bonds'])
                    and triples[site]['target_screen'] == 'PASS')
        checks['same_installed_api_sources'] = before['installed_api_sources'] == after['installed_api_sources']
    except (KeyError, TypeError, ValueError, OSError, IndexError, StopIteration, OverflowError) as exc:
        checks['complete_native_evidence'] = False
        error = type(exc).__name__ + ': ' + str(exc)
    passed = bool(checks) and all(v is True for v in checks.values())
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'MIXED_NATIVE_MEMBERSHIP_PASS' if passed else 'REVIEW',
        'mechanics_checks_pass': passed, 'checks': checks, 'membership': membership, 'triple_readback': triples,
        'error': error, 'request_index_basis': 'RESOLVED_FRESH_NATIVE_ATOMS; COMPILER_PDB_INDICES_NOT_REUSED',
        'policy_authority': 'NARestraints', 'scientific_qualification': 'NOT_ASSESSED', 'automatic_adoption': False}


def select_native_dictionaries(dictionaries, sources):
    """Keep exact canonical CCD graphs as data, with installed numeric authority.

    This only omits a whole single-component unparameterized canonical source;
    it never rewrites a mixed container or substitutes a modified component.
    """
    from .ligand_profiles import dictionary_component_codes, _parameterized_codes
    native_dictionaries = []; installed_canonical = []
    for path in dictionaries:
        codes = dictionary_component_codes(path)
        if codes and codes <= CANONICAL and not _parameterized_codes(path):
            if len(codes) != 1 or path.read_bytes() != sources[next(iter(codes))].read_bytes():
                raise ValueError('Unparameterized canonical input is not one exact frozen source')
            installed_canonical.extend(sorted(codes))
        else: native_dictionaries.append(path)
    return native_dictionaries, sorted(installed_canonical)


def compare_effective_chemistry(sources, dictionaries):
    """Recompute source/effective declarations without ranking native energy."""
    from .ligand_profiles import dictionary_component_codes, _parameterized_codes
    from .cif_generation import inspect_component_generation
    parameterized = set().union(*(_parameterized_codes(p) for p in dictionaries))
    comparisons = {}
    for code, source in sources.items():
        definitions = [p for p in dictionaries if code in dictionary_component_codes(p)]
        if len(definitions) != 1:
            comparisons[code] = {'status': 'REVIEW', 'error': 'Missing or ambiguous effective definition'}
        elif code in CANONICAL and code not in parameterized:
            comparisons[code] = {'status': 'INSTALLED_CANONICAL_NUMERICS_PENDING_NATIVE_READBACK',
                'source_graph_retained': definitions[0].read_bytes() == source.read_bytes()}
        else: comparisons[code] = inspect_component_generation(source, definitions[0], code)
    return comparisons


def _chemistry_pass(comparisons):
    return bool(comparisons) and all(r.get('status') == 'CANDIDATE_REVIEW'
        or r.get('status') == 'INSTALLED_CANONICAL_NUMERICS_PENDING_NATIVE_READBACK'
        and r.get('source_graph_retained') is True for r in comparisons.values())


def audit_mixed_native(fixture_directory, phenix, output, *, timeout_seconds=600):
    """One bounded ordinary ReadySet call and at most two fixed native reads.

    The selected source files are supplied individually with ordinary arguments.
    No source state, derivative, header or target is repaired here. A successful
    membership check cannot conceal supplier/generator chemical differences.
    """
    from .cif_mixed_pair_fixture import read_mixed_pair_fixture, _read_artifact
    from .cif_explicit_na_policy import read_explicit_na_policy
    from .cif_postmr_readyset import _atoms
    from .ligand_profiles import effective_restraints, _parameterized_codes, dictionary_component_codes
    from .postmr import _run_readyset, PostMRPreparationError
    from .cif_generation import _terminate_owned_group, inspect_component_generation
    from .cif_native_validation import inspect_native_bundle

    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
        raise ValueError('Require an integer ReadySet deadline from 1 to 600 seconds')
    fixture_directory, output = Path(fixture_directory), Path(output).absolute()
    if (output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents)
            or output.resolve().is_relative_to(fixture_directory.resolve())):
        raise ValueError('Require a fresh separate mixed native output')
    fixture = read_mixed_pair_fixture(fixture_directory)
    if fixture['status'] not in {'MIXED_PAIR_CONSTRUCTION_PASS', 'MIXED_PAIR_CONSTRUCTION_PASS_WITH_NOTES'}:
        raise ValueError('Require a completed verified mixed construction')
    compiled = read_explicit_na_policy(fixture_directory / 'explicit_policy')
    if compiled != fixture['policy_compilation']: raise ValueError('Fixture policy differs')
    source_model = _read_artifact(fixture_directory, fixture['outputs']['model'])
    originals = {source_model: source_model.read_bytes()}
    original_sources = {c: _read_artifact(fixture_directory, r['source']) for c, r in fixture['source_bindings'].items()}
    if set(original_sources) != set(fixture['plan']['target_site_components'].values()):
        raise ValueError('Fixture source scope differs from actual model')
    originals.update({p: p.read_bytes() for p in original_sources.values()})
    policy_source = fixture_directory / 'explicit_policy' / compiled['compiled_phil']['path']
    originals[policy_source] = policy_source.read_bytes()
    output.mkdir(parents=True); inputs = output / 'inputs'; inputs.mkdir()
    model = inputs / 'constructed.pdb'; model.write_bytes(originals[source_model])
    sources = {}
    for code, path in sorted(original_sources.items()):
        target = inputs / (code + '.cif'); target.write_bytes(originals[path]); sources[code] = target
    active = inputs / 'explicit_na_policy.phil'; active.write_bytes(originals[policy_source])
    disabled = inputs / 'secondary_disabled.phil'
    disabled.write_text('refinement {\n pdb_interpretation.secondary_structure {\n  enabled = False\n }\n}\n')
    _dump(inputs / 'plan.json', fixture['plan'])
    _dump(inputs / 'fixture_receipt.json', fixture)
    report = {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'PREPARED_ONLY',
        'scope': 'PRESERVED_EIGHT_PAIR_CONSTRUCTION; ORDINARY_SOURCE_NUMERICAL_HANDOFF_AND_FIXED_MEMBERSHIP',
        'inputs': {'model': _ref(model, output), 'active_policy': _ref(active, output), 'disabled_policy': _ref(disabled, output),
            'plan': _ref(inputs / 'plan.json', output), 'fixture_receipt': _ref(inputs / 'fixture_receipt.json', output),
            'sources': {c: _ref(p, output) for c, p in sources.items()}},
        'source_authorities': {c: r['authority'] for c, r in fixture['source_bindings'].items()},
        'readyset': {'execution': {'status': 'NOT_RUN'}, 'invocation': 'ORDINARY_DISPATCHER_AND_ARGUMENTS; ONE_SOURCE_COMPONENT_PER_ARGUMENT'},
        'native_baseline': {'status': 'NOT_RUN'}, 'native_active': {'status': 'NOT_RUN'},
        'qualification': {'status': 'NOT_RUN'}, 'chemical_comparisons': {},
        'deadlines': {'readyset_seconds': timeout_seconds, 'each_native_seconds': min(timeout_seconds, 60), 'maximum_native_calls': 2},
        'new_readyset_calls': 0, 'new_native_calls': 0, 'source_inputs_preserved': True,
        'requested_actions': {'hydrogens': False, 'ligands': True, 'optimise_ligand_geometry': False},
        'native_internal_operations': 'NOT_EXHAUSTIVELY_INSTRUMENTED',
        'coot_execution': 'NOT_RUN', 'model_optimization_requested': False, 'refinement': 'NOT_RUN',
        'production_checkpoint': 'NOT_CREATED', 'scientific_qualification': 'NOT_ASSESSED', 'mtz_used': False,
        'requires_cif_review': False, 'automatic_adoption': False, 'policy_authority': 'NARestraints',
        'coordinate_decision': {'status': 'CONTINUE_WITH_NOTES', 'selected': 'verified_constructed_model',
            'native_usable': 'NOT_YET_QUALIFIED', 'requires_cif_review': False, 'automatic_adoption': False}}
    if phenix is None: return _publish(output, report)
    run = output / 'readyset'; run.mkdir()
    executable = Path(phenix.executables['phenix.ready_set']).resolve(strict=True)
    executable_sha = sha256(executable.read_bytes()).hexdigest()
    report['phenix_version'] = phenix.version
    report['readyset']['dispatcher'] = {'historical_path': str(executable), 'sha256': executable_sha}
    def execute(command, **kwargs):
        report['new_readyset_calls'] += 1
        report['readyset']['command'] = command
        started = time.monotonic(); env = dict(kwargs.get('env') or {})
        env.pop('READY_SET_LIGAND_CACHE_DIRECTORY', None)
        with (run / 'dispatcher.log').open('xb') as log:
            process = subprocess.Popen(command, cwd=run, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name == 'posix')
            try:
                rc = process.wait(timeout=timeout_seconds)
                status = 'COMPLETED' if rc == 0 else 'FAILED'
            except subprocess.TimeoutExpired:
                _terminate_owned_group(process); rc = process.returncode; status = 'TIMED_OUT'
            except BaseException:
                _terminate_owned_group(process); raise
        report['readyset']['execution'] = {'status': status, 'returncode': rc,
            'timeout_seconds': timeout_seconds, 'elapsed_seconds': round(time.monotonic() - started, 6)}
        return subprocess.CompletedProcess(command, rc, (run / 'dispatcher.log').read_text(errors='replace'))
    try:
        checked, log, generated, command, phosphate = _run_readyset(model, executable, run,
            tuple(sources.values()), phenix.environment, process_runner=execute)
        report['readyset'].update(model=_ref(checked, output), log=_ref(log, output), phosphate_audit=phosphate,
            raw_generated_dictionary=_ref(generated, output) if generated else None)
        report['readyset']['unchanged_named_heavy_coordinates'] = _atoms(checked) == _atoms(model)
        if not report['readyset']['unchanged_named_heavy_coordinates']:
            raise ValueError('ReadySet changed the frozen constructed heavy atoms')
        effective = output / 'effective'; effective.mkdir(); audits = []
        _, dictionaries = effective_restraints(list(sources.values()), generated, effective,
            normalize_effective=True, audit=audits, prefer_parameterized_inputs=True)
        report['effective_dictionary_audits'] = audits
        report['effective_dictionaries'] = [_ref(p, output) for p in dictionaries]
        parameterized = set().union(*(_parameterized_codes(p) for p in dictionaries))
        report['effective_parameterized_components'] = sorted(parameterized)
        native_dictionaries, installed_canonical = select_native_dictionaries(dictionaries, sources)
        report['native_dictionary_selection'] = {
            'policy': 'EXPLICIT_EFFECTIVE_NUMERICS; EXACT_UNPARAMETERIZED_CANONICAL_SOURCE_GRAPHS_REMAIN_DATA',
            'installed_canonical_components': sorted(installed_canonical),
            'dictionaries': [_ref(p, output) for p in native_dictionaries],
            'mixed_component_files_rewritten': False}
        # Known canonical monomers may be provided by the installed library;
        # source-only modified components must have explicit numerical rows.
        required = set(sources) - CANONICAL
        report['required_modified_parameterization'] = {'components': sorted(required),
            'missing': sorted(required - parameterized), 'canonical_source_graphs_are_not_numerics': True}
        report['chemical_comparisons'] = compare_effective_chemistry(sources, dictionaries)
        if required - parameterized:
            raise ValueError('ReadySet did not provide complete numerical rows for every modified component')
        common = dict(environment=phenix.environment, phenix_version=phenix.version,
            timeout_seconds=min(timeout_seconds, 60), inventory_detail='linked', policy_inventory=True,
            energy_inventory=True, phil_namespace_policy='refinement-root-to-interpreter-v1')
        captures = []
        for key, files in [('native_baseline', [disabled]), ('native_active', [active])]:
            capture = inspect_native_bundle(checked, native_dictionaries, output / key,
                phenix.executables['phenix.python'], phil_files=files, **common)
            if 'returncode' in capture.get('execution', {}): report['new_native_calls'] += 1
            report[key] = {'directory': {'anchor': ANCHOR, 'path': Path(capture['native_directory']).relative_to(output).as_posix()}, **capture}
            captures.append(capture)
            if not _native_ok(capture): break
        if len(captures) == 2 and all(_native_ok(c) for c in captures):
            qualification = qualify_mixed_native(*(c['native_validation'] for c in captures), checked, active, fixture['plan'], sources, native_dictionaries)
            report['qualification'] = qualification
            chemistry_ok = _chemistry_pass(report['chemical_comparisons'])
            report['source_chemistry_comparisons_pass'] = chemistry_ok
            if qualification['mechanics_checks_pass'] and chemistry_ok:
                report['status'] = 'MIXED_NATIVE_MEMBERSHIP_PASS'
        if report['status'] != 'MIXED_NATIVE_MEMBERSHIP_PASS': report['status'] = 'REVIEW'
    except (PostMRPreparationError, ValueError, OSError) as exc:
        report.update(status='REVIEW', error_type=type(exc).__name__, error=str(exc))
    if sha256(executable.read_bytes()).hexdigest() != executable_sha:
        raise ValueError('ReadySet dispatcher changed')
    report['source_inputs_preserved'] = all(p.read_bytes() == data for p, data in originals.items())
    frozen = [model, active, *sources.values()]
    report['frozen_inputs_preserved'] = all(_ref(p, output) in [report['inputs']['model'], report['inputs']['active_policy'], *report['inputs']['sources'].values()] for p in frozen)
    if not report['source_inputs_preserved'] or not report['frozen_inputs_preserved']:
        raise ValueError('Mixed native input changed')
    return _publish(output, report)


def read_mixed_native(directory):
    """Verify portable frozen artifacts; never execute saved Python or host paths."""
    root = Path(directory)
    if any(p.is_symlink() for p in [root, *root.parents]): raise ValueError('Unsafe mixed native directory')
    record = root / 'mixed_native.json'
    if record.is_symlink(): raise ValueError('Unsafe mixed native report')
    report = json.loads(record.read_bytes())
    if (report.get('policy_id') != POLICY_ID or report.get('status') not in {'PREPARED_ONLY', 'MIXED_NATIVE_MEMBERSHIP_PASS', 'REVIEW'}
            or report.get('automatic_adoption') is not False or report.get('requires_cif_review') is not False
            or report.get('scientific_qualification') != 'NOT_ASSESSED' or report.get('production_checkpoint') != 'NOT_CREATED'
            or report.get('coot_execution') != 'NOT_RUN' or report.get('refinement') != 'NOT_RUN' or report.get('mtz_used') is not False):
        raise ValueError('Mixed native report claims unsupported scope')
    outputs = report['outputs']
    if len({r['path'] for r in outputs}) != len(outputs): raise ValueError('Duplicate mixed native artifact')
    for ref in outputs: _resolve(root, ref)
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink(): raise ValueError('Mixed native output contains a symlink')
        if path.is_file() and path != record and path.suffix not in {'.pickle', '.pkl', '.pyc'}:
            actual.add(path.relative_to(root).as_posix())
    if actual != {r['path'] for r in outputs}: raise ValueError('Mixed native output inventory differs')
    refs = report['inputs']
    fixture = json.loads(_resolve(root, refs['fixture_receipt']).read_bytes())
    plan = json.loads(_resolve(root, refs['plan']).read_bytes())
    if (fixture.get('status') not in {'MIXED_PAIR_CONSTRUCTION_PASS', 'MIXED_PAIR_CONSTRUCTION_PASS_WITH_NOTES'}
            or plan != fixture.get('plan') or fixture.get('policy_compilation', {}).get('pair_count') != 20
            or fixture['policy_compilation'].get('stack_count') != 38):
        raise ValueError('Mixed native frozen fixture/plan differs')
    def same_data(ref, parent):
        return ref.get('sha256') == parent.get('sha256') and ref.get('size') == parent.get('size')
    if (not same_data(refs['model'], fixture['outputs']['model'])
            or not same_data(refs['active_policy'], fixture['policy_compilation']['compiled_phil'])
            or set(refs['sources']) != set(fixture['source_bindings'])
            or any(not same_data(r, fixture['source_bindings'][c]['source']) for c, r in refs['sources'].items())):
        raise ValueError('Mixed native frozen operational bytes differ from their fixture')
    if report['status'] == 'PREPARED_ONLY':
        if (report.get('new_readyset_calls') != 0 or report.get('new_native_calls') != 0
                or report.get('qualification') != {'status': 'NOT_RUN'}
                or report['readyset']['execution']['status'] != 'NOT_RUN'):
            raise ValueError('Prepared mixed native report claims execution')
    if report.get('new_native_calls') or report['status'] == 'MIXED_NATIVE_MEMBERSHIP_PASS':
        if (not report.get('effective_dictionaries') or not report.get('native_dictionary_selection')
                or set(report.get('chemical_comparisons', {})) != set(refs['sources'])):
            raise ValueError('Incomplete mixed native effective source evidence')
    if report['status'] == 'MIXED_NATIVE_MEMBERSHIP_PASS':
        if (report.get('new_readyset_calls') != 1 or report.get('new_native_calls') != 2
                or report.get('source_chemistry_comparisons_pass') is not True
                or report['qualification'].get('mechanics_checks_pass') is not True
                or report['readyset']['execution'].get('status') != 'COMPLETED'
                or report['readyset'].get('unchanged_named_heavy_coordinates') is not True
                or not all(_native_ok(report[k]) for k in ['native_baseline', 'native_active'])):
            raise ValueError('Incomplete mixed native PASS evidence')
    if 'effective_dictionaries' in report:
        from .cif_postmr_cached_model import cached_preparation_replays
        effective = [_resolve(root, r) for r in report['effective_dictionaries']]
        sources = {c: _resolve(root, r) for c, r in refs['sources'].items()}
        comparisons = compare_effective_chemistry(sources, effective)
        if not cached_preparation_replays(report['chemical_comparisons'], comparisons):
            raise ValueError('Mixed native chemical comparison does not reproduce')
        if 'source_chemistry_comparisons_pass' in report and report['source_chemistry_comparisons_pass'] != _chemistry_pass(comparisons):
            raise ValueError('Mixed native chemical qualification flag differs')
        if 'native_dictionary_selection' in report:
            selected, canonical = select_native_dictionaries(effective, sources)
            selection = report['native_dictionary_selection']
            if (selection['dictionaries'] != [_ref(p, root) for p in selected]
                    or selection['installed_canonical_components'] != canonical):
                raise ValueError('Mixed native selected numerical authority differs')
    if report.get('new_native_calls'):
        from .cif_native_validation import _NATIVE_WORKER, NATIVE_POLICY_ID
        from .cif_candidate_usability import native_energy_worker
        captures = []
        for key in ['native_baseline', 'native_active']:
            capture = report[key]
            if 'directory' not in capture: continue
            folder = root / capture['directory']['path']
            if (capture['directory'].get('anchor') != ANCHOR or not _safe(capture['directory'].get('path'))
                    or json.loads((folder / 'native_receipt.json').read_bytes()) != {k: v for k, v in capture.items() if k != 'directory'}
                    or (folder / 'native_worker.py').read_bytes() != native_energy_worker(_NATIVE_WORKER).encode()):
                raise ValueError('Saved mixed native worker or receipt differs')
            from .cif_candidate_usability import native_energy_worker
            frozen_model = _resolve(root, report['readyset']['model'])
            frozen_dictionaries = [_resolve(root, r) for r in report['native_dictionary_selection']['dictionaries']]
            frozen_phil = _resolve(root, refs['disabled_policy'] if key == 'native_baseline' else refs['active_policy'])
            expected_inputs = [('model', frozen_model), *[('dictionary', p) for p in frozen_dictionaries], ('phil', frozen_phil)]
            actual_inputs = capture.get('inputs', [])
            if len(expected_inputs) != len(actual_inputs): raise ValueError('Saved mixed native input count differs')
            for index, ((role, expected), ref) in enumerate(zip(expected_inputs, actual_inputs)):
                if (ref.get('anchor') != 'native_directory' or not _safe(ref.get('path'))
                        or ref.get('input_index') != index or ref.get('role') != role):
                    raise ValueError('Saved mixed native input role or reference differs')
                data = (folder / ref['path']).read_bytes()
                if (data != expected.read_bytes() or len(data) != ref.get('size')
                        or sha256(data).hexdigest() != ref.get('sha256')):
                    raise ValueError('Saved mixed native input bytes differ')
            expected_spec = {'policy_id': NATIVE_POLICY_ID, 'model': actual_inputs[0]['path'],
                'dictionaries': [r['path'] for r in actual_inputs if r['role'] == 'dictionary'],
                'phil_files': [actual_inputs[-1]['path']], 'phil_namespace_policy': 'refinement-root-to-interpreter-v1',
                'inventory_detail': 'linked', 'policy_inventory': True, 'energy_inventory': True}
            if json.loads((folder / 'native_spec.json').read_bytes()) != expected_spec:
                raise ValueError('Saved mixed native input specification differs')
            if (folder / 'native_validation.json').is_file():
                if json.loads((folder / 'native_validation.json').read_bytes()) != capture.get('native_validation'):
                    raise ValueError('Saved mixed native validation differs')
            if _native_ok(capture): captures.append(capture['native_validation'])
        if len(captures) == 2:
            dictionaries = [_resolve(root, r) for r in report['native_dictionary_selection']['dictionaries']]
            replay = qualify_mixed_native(*captures, _resolve(root, report['readyset']['model']),
                _resolve(root, refs['active_policy']), plan,
                {c: _resolve(root, r) for c, r in refs['sources'].items()}, dictionaries)
            if replay != report['qualification']: raise ValueError('Mixed native qualification does not reproduce')
    for ref in [refs[k] for k in ['model', 'active_policy', 'disabled_policy', 'plan', 'fixture_receipt']]: _resolve(root, ref)
    for ref in refs['sources'].values(): _resolve(root, ref)
    return report
