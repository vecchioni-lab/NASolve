"""Portable activation preserves the qualified selection and every resource byte."""
from copy import deepcopy
from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
import shutil

import pytest


def case(tmp_path, *, fallback=False):
    from tests.test_cif_scaffold_candidate import native_case
    from nasolve.cif_scaffold_candidate import qualify_scaffold_candidate, select_scaffold_geometry
    from nasolve.cif_fixed_geometry import write_geometry_candidate, review_fixed_coordinates, qualify_fixed_policy_geometry
    from nasolve.cif_captured_geometry import review_captured_geometry
    from nasolve.cif_gradient_audit import audit_gradients, FAMILIES
    tmp_path.mkdir(exist_ok=True)
    a, initial, model, preparation = native_case(tmp_path)
    for n in [a, initial]:
        n.update(schema_version=1, policy_id='cif-native-bundle-inventory-v1')
        n['geometry']['status'] = 'RECORDED'
    weights = {name: i + 1 for i, name in enumerate(FAMILIES[1:])}
    def evaluate(points, family):
        w = sum(weights.values()) if family == 'all' else weights[family]
        return {'target': w * sum(v*v for p in points for v in p), 'gradient': [2*w*v for p in points for v in p]}
    raw = evaluate(initial['geometry']['sites_cart_exact'], 'all')
    raw['gradient_norm'] = sum(x*x for x in raw['gradient']) ** .5
    initial['energy_inventory']['snapshots'] = [deepcopy(raw), deepcopy(raw)]
    qualification = qualify_scaffold_candidate(a, initial, model, preparation, tmp_path, code='ZZZ')
    assert qualification['native_usable']
    final = [[.99*x for x in p] for p in initial['geometry']['sites_cart_exact']]
    endpoint = tmp_path/'endpoint.pdb'
    serialization = write_geometry_candidate(model, endpoint, initial, final)
    native = deepcopy(initial)
    for atom, p in zip(native['atoms'], final): atom['xyz'] = [round(x, 3) for x in p]
    native['geometry']['sites_cart_exact'] = [list(a['xyz']) for a in native['atoms']]
    audit = audit_gradients(evaluate, {'full_precision': final, 'pdb_rounded': native['geometry']['sites_cart_exact']}, [0], max_calls=2000)
    result = {'policy_id': 'cif-fixed-na-corrected-geometry-trial-v1', 'captured_inventory_matches': True,
        'qualified_initial_snapshot_matches': True, 'normalization': False, 'starting_coordinates': 'CAPTURED_INITIAL',
        'constraint_signature_before': 'c'*64, 'constraint_signature_after': 'c'*64,
        'initial': raw, 'final': audit['cases']['full_precision']['families']['all']['baseline'],
        'serialized': audit['cases']['pdb_rounded']['families']['all']['baseline'], 'final_sites_cart': final,
        'endpoint_gradient_audit': audit, 'endpoint_derivative_qualification': 'SAMPLED_NATIVE_DERIVATIVES_PASS',
        'stopping': {'reason': 'max_iterations', 'native_criterion_met': False, 'error': None}}
    trial = {'status': 'REVIEW', 'execution': {'status': 'COMPLETED', 'returncode': 0},
        'source_preserved': True, 'frozen_inputs_preserved': True, 'result': result}
    mechanics = qualify_fixed_policy_geometry(initial, native, endpoint, serialization)
    full = review_fixed_coordinates(initial, final); rounded = review_captured_geometry(native)
    decision = select_scaffold_geometry(qualification, trial, mechanics, full, serialization,
        atom_count=initial['atom_count'], rounded_geometry_review=rounded)
    assert decision['selected_candidate'] == 'qualified_geometry_endpoint'
    selected = endpoint
    if fallback:
        selected = model; native = deepcopy(initial); trial = None; serialization = None
        decision = select_scaffold_geometry(qualification, None, None, None, None, atom_count=initial['atom_count'])
    dictionary = tmp_path/'projected.cif'
    phil = tmp_path/'policy.phil'; phil.write_text('pdb_interpretation.secondary_structure {\n enabled = False\n}\n')
    provenance = {'initial_model': model, 'initial_native_validation': initial, 'initial_qualification': qualification,
        'trial': trial, 'serialization': serialization, 'source_archive': {'delivery_prefix': '60_Cedar', 'sha256': 'a'*64},
        'source_inputs': [{'role': role, 'sha256': sha256(p.read_bytes()).hexdigest(), 'size': p.stat().st_size}
            for role, p in [('model', selected), ('dictionary', dictionary), ('phil', phil)]]}
    return selected, [dictionary], [phil], decision, native, provenance


def activate(tmp_path, *, fallback=False):
    from nasolve.cif_runtime_bundle import prepare_runtime_bundle
    values = case(tmp_path/'inputs', fallback=fallback)
    model, cifs, phils, decision, native, provenance = values
    out = tmp_path/'bundle'
    manifest = prepare_runtime_bundle(model, cifs, phils, out, decision=decision,
        native_validation=native, provenance=provenance)
    return out, manifest, values


@pytest.mark.parametrize('fallback', [False, True])
def test_qualified_activation_preserves_model_resources_order_and_notes(tmp_path, fallback):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    out, manifest, values = activate(tmp_path, fallback=fallback)
    model, cifs, phils, decision, _, _ = values
    r = resolve_runtime_bundle(out/manifest['manifest_file'])
    assert r['model'].read_bytes() == model.read_bytes()
    assert [p.read_bytes() for p in r['dictionaries']] == [p.read_bytes() for p in cifs]
    assert [p.read_bytes() for p in r['phils']] == [p.read_bytes() for p in phils]
    assert manifest['decision'] == decision
    assert not manifest['requires_cif_review'] and manifest['scientific_approval'] == 'NOT_RUN'
    assert manifest['automatic_adoption'] is False
    refs = [manifest['resources']['model'], *manifest['resources']['dictionaries'], *manifest['resources']['phils'], manifest['evidence']]
    assert all(a['anchor'] == 'runtime_bundle' and not a['relative_path'].startswith('/') for a in refs)


def test_bundle_resolves_and_assesses_after_original_inputs_are_gone(tmp_path):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle, assess_runtime_bundle
    out, _, _ = activate(tmp_path)
    moved = tmp_path/'relocated'; shutil.move(out, moved); shutil.rmtree(tmp_path/'inputs')
    r = resolve_runtime_bundle(moved)
    assert r['model'].is_file() and r['manifest_path'].parent == moved
    before = {p.relative_to(moved).as_posix(): p.read_bytes() for p in moved.rglob('*') if p.is_file()}
    assessment = assess_runtime_bundle(moved)
    assert assessment['audit_kind'] == 'cif_restraint_assessment'
    assert assessment['bundle_context']['read_only'] and not assessment['bundle_context']['requires_cif_review']
    assert assessment['requires_cif_review'] is False
    assert assessment['solution_report']['selected_candidate'] == 'qualified_geometry_endpoint'
    assert assessment['solution_report']['stopping']['reason'] == 'max_iterations'
    assert assessment['solution_report']['pdf_status'] == 'PLANNED'
    assert assessment['model']['sha256'] == r['manifest']['resources']['model']['sha256']
    assert [a['sha256'] for a in assessment['inputs']] == [a['sha256'] for a in [*r['manifest']['resources']['dictionaries'], *r['manifest']['resources']['phils']]]
    assert before == {p.relative_to(moved).as_posix(): p.read_bytes() for p in moved.rglob('*') if p.is_file()}


@pytest.mark.parametrize('changed', ['model', 'dictionary', 'phil'])
def test_assessment_detects_resource_changes_during_read(tmp_path, monkeypatch, changed):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle, assess_runtime_bundle
    from nasolve import cif_doctor
    out, _, _ = activate(tmp_path)
    resolved = resolve_runtime_bundle(out)
    target = resolved['model'] if changed == 'model' else resolved['dictionaries'][0] if changed == 'dictionary' else resolved['phils'][0]
    original = cif_doctor.assess_dictionaries
    def assessed(*args, **kwargs):
        result = original(*args, **kwargs)
        target.write_bytes(target.read_bytes() + b'\n# changed during assessment\n')
        return result
    monkeypatch.setattr(cif_doctor, 'assess_dictionaries', assessed)
    with pytest.raises(ValueError): assess_runtime_bundle(out)


@pytest.mark.parametrize('defect', ['decision', 'model_binding', 'dictionary_binding', 'parameter_binding', 'selected_coordinates',
    'native_target', 'native_definition', 'native_policy', 'trial_derivative', 'serialization', 'initial_qualification', 'source_archive'])
def test_activation_recomputes_selection_and_native_evidence_before_writing(tmp_path, defect):
    from nasolve.cif_runtime_bundle import prepare_runtime_bundle
    model, cifs, phils, decision, native, provenance = case(tmp_path/'inputs')
    if defect == 'decision': decision['selected_candidate'] = 'verified_initial_scaffold'
    if defect == 'model_binding': provenance['source_inputs'][0]['sha256'] = '0'*64
    if defect == 'dictionary_binding': cifs[0].write_text(cifs[0].read_text() + '# changed\n')
    if defect == 'parameter_binding': phils[0].write_text('pdb_interpretation.secondary_structure.enabled = True\n')
    if defect == 'selected_coordinates': native['atoms'][0]['xyz'][0] += 1
    if defect == 'native_target': native['geometry']['proxy_details']['bond_simple'][0]['distance_ideal'] += 1
    if defect == 'native_definition': native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['changed'] = []
    if defect == 'native_policy': native['restraint_policy']['secondary_structure_enabled'] = True
    if defect == 'trial_derivative': provenance['trial']['result']['endpoint_gradient_audit']['cases']['full_precision']['families']['all']['directions'][0]['samples'][0]['plus_target'] += 1
    if defect == 'serialization': provenance['serialization']['candidate_sha256'] = 'f'*64
    if defect == 'initial_qualification': provenance['initial_qualification']['native_usable'] = False
    if defect == 'source_archive': provenance['source_archive']['sha256'] = 'not-a-hash'
    with pytest.raises(ValueError):
        prepare_runtime_bundle(model, cifs, phils, tmp_path/'bundle', decision=decision, native_validation=native, provenance=provenance)
    assert not (tmp_path/'bundle').exists()


@pytest.mark.parametrize('defect', ['model', 'dictionary', 'phil', 'evidence', 'absolute', 'traversal', 'wrong_anchor', 'duplicate',
    'version', 'policy', 'symlink', 'missing', 'forged_evidence', 'forged_decision', 'optimization_claim', 'production_claim', 'checkpoint_claim'])
def test_loader_refuses_stale_unsafe_or_incomplete_bundle(tmp_path, defect):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    out, manifest, _ = activate(tmp_path)
    path = out/manifest['manifest_file']
    refs = manifest['resources']
    if defect in {'model', 'dictionary', 'phil', 'evidence'}:
        row = refs['model'] if defect == 'model' else refs['dictionaries'][0] if defect == 'dictionary' else refs['phils'][0] if defect == 'phil' else manifest['evidence']
        (out/row['relative_path']).write_bytes(b'changed')
    if defect == 'absolute': refs['model']['relative_path'] = '/tmp/model.pdb'
    if defect == 'traversal': refs['model']['relative_path'] = '../model.pdb'
    if defect == 'wrong_anchor': refs['model']['anchor'] = 'absolute'
    if defect == 'duplicate': refs['phils'][0] = deepcopy(refs['dictionaries'][0])
    if defect == 'version': manifest['schema_version'] = 99
    if defect == 'policy': manifest['policy_id'] = 'unknown'
    if defect == 'optimization_claim': manifest['model_optimization'] = 'COMPLETED'
    if defect == 'production_claim': manifest['production_consumption'] = 'FULL_AUTOMATIC_POSTMR'
    if defect == 'checkpoint_claim': manifest['checkpoint_adoption'] = 'COMPLETED'
    if defect == 'symlink':
        row = refs['model']; actual = out/row['relative_path']; saved = out/'outside.pdb'; actual.rename(saved); actual.symlink_to(saved)
    if defect == 'missing': (out/refs['dictionaries'][0]['relative_path']).unlink()
    if defect == 'forged_evidence':
        p = out/manifest['evidence']['relative_path']; e = json.loads(p.read_text());e['initial_qualification']['native_usable'] = False
        p.write_text(json.dumps(e)); manifest['evidence']['sha256'] = sha256(p.read_bytes()).hexdigest();manifest['evidence']['size'] = p.stat().st_size
    if defect == 'forged_decision': manifest['decision']['endpoint_usable'] = False
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError): resolve_runtime_bundle(path)


def test_existing_destination_and_symlink_parent_are_not_modified(tmp_path):
    from nasolve.cif_runtime_bundle import prepare_runtime_bundle
    model, cifs, phils, decision, native, provenance = case(tmp_path/'inputs')
    existing = tmp_path/'existing'; existing.mkdir();(existing/'keep').write_text('mine')
    with pytest.raises(FileExistsError): prepare_runtime_bundle(model, cifs, phils, existing, decision=decision, native_validation=native, provenance=provenance)
    assert (existing/'keep').read_text() == 'mine'
    alias = tmp_path/'alias';alias.symlink_to(existing, target_is_directory=True)
    with pytest.raises(ValueError): prepare_runtime_bundle(model, cifs, phils, alias/'out', decision=decision, native_validation=native, provenance=provenance)
    assert not (existing/'out').exists()


def test_public_bundle_cli_uses_ordinary_assessor_without_native_discovery(tmp_path, monkeypatch):
    from nasolve.cli import main
    from nasolve import cif_runtime_bundle
    audit = {'audit_kind': 'cif_restraint_assessment', 'status': 'REVIEW', 'inputs': []}
    calls = []
    monkeypatch.setattr(cif_runtime_bundle, 'assess_runtime_bundle', lambda path: calls.append(path) or audit)
    monkeypatch.setattr('nasolve.cli.discover_phenix', lambda *a, **k: pytest.fail('offline bundle assessment must not discover Phenix'))
    with redirect_stdout(io.StringIO()) as stream:
        assert main(['cif-doctor', 'assess', '--bundle', str(tmp_path), '--json']) == 2
    assert calls == [tmp_path] and json.loads(stream.getvalue()) == audit


@pytest.mark.parametrize('extra', [['--run', '/a/run'], ['source.cif'], ['--model', 'model.pdb'], ['--checkpoint', 'postmr'], ['--stage', 'effective']])
def test_bundle_cli_rejects_ambiguous_sources(tmp_path, extra):
    from nasolve.cli import main
    assert main(['cif-doctor', 'assess', '--bundle', str(tmp_path), *extra]) == 1
