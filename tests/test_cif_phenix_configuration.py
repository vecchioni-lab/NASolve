"""Current settings come from one selected SDK, not historical test capsules."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import shutil

import pytest

from nasolve.phenix_runtime import PhenixInstallation
from nasolve.cif_postmr_cache import _API, _ENERGY, verify_current_consumer
from nasolve.cif_source_candidate import SOURCE_PATHS
from nasolve.cif_generation_acquisition import generation_dictionary_options
from tests.test_cif_complete_request import case
from tests.test_cif_model_context import bind
from tests.test_cif_repair_attempt import inventory


def sdk_at(root, layout='lib/python3.11/site-packages'):
    site = root/layout
    for name in (*_API, *_ENERGY, *SOURCE_PATHS):
        p = site/name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('# Synthetic selected SDK: '+name+'\n')
    executables = {}
    for name in ('phenix.python', 'phenix.elbow', 'phenix.ready_set'):
        p = root/'bin'/name; p.parent.mkdir(exist_ok=True)
        p.write_text('# Synthetic dispatcher: '+name+'\n'); p.chmod(0o755)
        executables[name] = p
    return PhenixInstallation(root, None, '2.2.1', executables,
                              {'NASOLVE_TEST_SECRET':'keep-this-live-only'}, 'explicit'), site


def configure(sdk, **options):
    from nasolve.cif_phenix_configuration import configure_dictionary_engine
    return configure_dictionary_engine(sdk, expected_dialect='CHEMICAL_COMPONENTS_CIF', **options)


@pytest.mark.parametrize('layout', ['lib/python3.11/site-packages', 'lib/python3.12/site-packages',
                                  'lib64/python3.10/site-packages'])
def test_current_configuration_is_read_only_and_uses_selected_maintained_scope(tmp_path, layout):
    sdk, site = sdk_at(tmp_path/'selected', layout); before = inventory(sdk.root)
    with patch('subprocess.Popen', side_effect=AssertionError('Configuration must not execute')):
        result = configure(sdk)
    assert inventory(sdk.root) == before and result == configure(sdk)
    assert result.ready_set_executable == sdk.executables['phenix.ready_set']
    assert verify_current_consumer(sdk, result.ready_set_executable, result.consumer)
    assert len(result.consumer['api_sources']) == 8 and len(result.consumer['energy_sources']) == 3
    assert result.consumer['executable_sha256'] == sha256(sdk.executables['phenix.python'].read_bytes()).hexdigest()
    options = generation_dictionary_options(result.generation)
    assert options['recipe'] == dict(policy_id='cif-source-preserving-generation-recipe-v1',
                                    expected_dialect='CHEMICAL_COMPONENTS_CIF', single_block_steps=180)
    assert options['generator']['name'] == 'phenix.elbow.source-preserving'
    assert {p['path'] for p in result.generation['prior_sources']} == {
        (site/name).relative_to(sdk.root).as_posix() for name in SOURCE_PATHS}
    assert len(result.generation['api_sources']) == 1
    assert result.generation['api_sources'][0]['path'].endswith('/iotbx/phil.py')
    assert result.generation['installation_root'] == sdk.root
    assert 'keep-this-live-only' not in repr(result)


def test_configuration_copies_environment_and_keeps_representation_permission_explicit(tmp_path):
    sdk, _ = sdk_at(tmp_path/'sdk'); original = deepcopy(sdk)
    result = configure(sdk, single_block_steps=91, timeout_seconds=72.5, max_attempts=3,
                       bond_representation_policy='cif-source-declared-neutral-purine-aromatic-v1',
                       source_input_policy='cif-source-reader-preparation-v1')
    g = result.generation
    assert g['single_block_steps'] == 91 and g['timeout_seconds'] == 72.5 and g['max_attempts'] == 3
    assert generation_dictionary_options(g)['recipe']['bond_representation_policy'] == g['bond_representation_policy']
    assert generation_dictionary_options(g)['recipe']['source_input_policy'] == 'cif-source-reader-preparation-v1'
    g['environment']['NASOLVE_TEST_SECRET'] = 'caller-change'
    g['prior_sources'][0]['sha256'] = '0'*64
    assert sdk == original and configure(sdk).generation['environment'] == sdk.environment
    assert 'bond_representation_policy' not in generation_dictionary_options(configure(sdk).generation)['recipe']


@pytest.mark.parametrize('field,value', [('single_block_steps', True), ('single_block_steps', 601),
    ('timeout_seconds', 0), ('timeout_seconds', float('nan')), ('timeout_seconds', 601),
    ('max_attempts', 0), ('max_attempts', True), ('bond_representation_policy', 'invented-policy')])
def test_existing_recipe_validator_rejects_invalid_controls_without_writes(tmp_path, field, value):
    sdk, _ = sdk_at(tmp_path/'sdk'); before = inventory(sdk.root)
    with pytest.raises(ValueError): configure(sdk, **{field:value})
    assert inventory(sdk.root) == before


@pytest.mark.parametrize('defect', ['missing-api', 'missing-energy', 'missing-prior', 'ambiguous',
    'missing-python', 'outside-python', 'outside-ready', 'outside-elbow', 'source-symlink',
    'outside-library', 'unknown-version', 'blank-version', 'missing-root', 'bad-environment'])
def test_incomplete_or_unselected_sdk_refuses_without_changes(tmp_path, defect):
    sdk, site = sdk_at(tmp_path/'sdk')
    if defect.startswith('missing-') and defect != 'missing-root':
        p = {'missing-api':site/_API[0], 'missing-energy':site/_ENERGY[0],
             'missing-prior':site/SOURCE_PATHS[0], 'missing-python':sdk.executables['phenix.python']}[defect]
        p.unlink()
    elif defect == 'ambiguous': sdk_at(tmp_path/'sdk', 'lib/python3.12/site-packages')
    elif defect.startswith('outside-') and defect != 'outside-library':
        key = {'outside-python':'phenix.python','outside-ready':'phenix.ready_set','outside-elbow':'phenix.elbow'}[defect]
        outside = tmp_path/'other'; outside.write_text('outside')
        sdk.executables[key].unlink(); sdk.executables[key].symlink_to(outside)
    elif defect == 'source-symlink':
        p = site/_API[0]; target = site/'pinned.py'; p.rename(target); p.symlink_to(target)
    elif defect == 'outside-library':
        target = tmp_path/'outside-site'; site.rename(target); site.symlink_to(target, target_is_directory=True)
    elif defect == 'unknown-version': sdk = replace(sdk, version='unknown')
    elif defect == 'blank-version': sdk = replace(sdk, version='  ')
    elif defect == 'missing-root': sdk = replace(sdk, root=None)
    elif defect == 'bad-environment': sdk = replace(sdk, environment={'key':None})
    before = inventory(tmp_path)
    with pytest.raises((ValueError, OSError)): configure(sdk)
    assert inventory(tmp_path) == before


def test_internal_library_alias_does_not_invent_a_second_installation(tmp_path):
    sdk, site = sdk_at(tmp_path/'sdk'); (sdk.root/'lib64').symlink_to(sdk.root/'lib', target_is_directory=True)
    # Selected dispatchers may themselves be internal aliases, as supported by discovery.
    p = sdk.executables['phenix.python']; real = p.with_name('native-python'); p.rename(real); p.symlink_to(real)
    result = configure(sdk)
    assert result.generation['python_executable'] == real
    assert verify_current_consumer(sdk, result.ready_set_executable, result.consumer)


@pytest.mark.parametrize('changed', ['api', 'energy', 'prior', 'ready', 'elbow', 'python', 'layout', 'environment'])
def test_change_during_configuration_never_returns_mixed_identity(tmp_path, monkeypatch, changed):
    from nasolve import cif_phenix_configuration as m
    sdk, site = sdk_at(tmp_path/'sdk'); validate = m.generation_dictionary_options
    def mutate(g):
        result = validate(g)
        if changed == 'layout': sdk_at(sdk.root, 'lib/python3.12/site-packages')
        elif changed == 'environment': sdk.environment['NASOLVE_TEST_SECRET'] = 'changed'
        else:
            p = {'api':site/_API[0], 'energy':site/_ENERGY[0], 'prior':site/SOURCE_PATHS[-1],
                 **{k:sdk.executables['phenix.'+k] for k in ('ready_set','elbow','python')}}[
                     'ready_set' if changed == 'ready' else changed]
            p.write_bytes(p.read_bytes()+b'# changed\n')
        return result
    monkeypatch.setattr(m, 'generation_dictionary_options', mutate)
    with pytest.raises(ValueError): configure(sdk)


def test_existing_request_freezes_identity_without_live_environment_and_replays_cold(case, tmp_path):
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    from nasolve.cif_complete_request import inspect_dictionary_request
    _, args, request, _, _, _, _ = case
    args = bind(args); sdk, _ = sdk_at(tmp_path/'current-sdk')
    profile = configure(sdk, max_attempts=1)
    items = [dict(code=item['code'], generation=profile.generation) for item in args['components']]
    with patch('subprocess.Popen', side_effect=AssertionError('Initialization must not execute')):
        initialize_postmr_dictionary_request(args['model'], args['model_context']['intent'], items,
            tmp_path/'current-sources', request, consumer=profile.consumer,
            ready_set_executable=profile.ready_set_executable, supplementary_phils=[],
            data_root=tmp_path/'data')
    frozen = (request/'request.json').read_text()
    assert 'keep-this-live-only' not in frozen and 'NASOLVE_TEST_SECRET' not in frozen
    assert str(sdk.root) not in frozen
    before = inventory(request); moved = request.rename(tmp_path/'moved-request')
    shutil.rmtree(sdk.root)
    with patch('subprocess.Popen', side_effect=AssertionError('Cold inspection must not execute')):
        state = inspect_dictionary_request(moved)
    assert state['availability'] == 'AVAILABLE' and not state['attempts']
    assert inventory(moved) == before


def test_relocated_installation_derives_same_recipe_and_consumer_without_old_path(tmp_path):
    sdk, _ = sdk_at(tmp_path/'original'); old = configure(sdk)
    moved = sdk.root.rename(tmp_path/'relocated')
    sdk = replace(sdk, root=moved, executables={k:moved/p.relative_to(sdk.root) for k,p in sdk.executables.items()})
    fresh = configure(sdk)
    assert not (tmp_path/'original').exists()
    assert fresh.consumer == old.consumer
    assert generation_dictionary_options(fresh.generation) == generation_dictionary_options(old.generation)
    from nasolve.cif_acquisition_attempt import _generation_binding
    assert _generation_binding(fresh.generation) == _generation_binding(old.generation)


@pytest.mark.parametrize('defect', ['partial-library', 'source-parent-escape', 'empty-dialect'])
def test_partial_shadow_library_or_escaping_source_is_not_silently_selected(tmp_path, defect):
    from nasolve.cif_phenix_configuration import configure_dictionary_engine
    sdk, site = sdk_at(tmp_path/'sdk')
    if defect == 'partial-library':
        p = sdk.root/'lib/python3.13/site-packages/iotbx/phil.py'
        p.parent.mkdir(parents=True); p.write_bytes((site/_API[0]).read_bytes())
    elif defect == 'source-parent-escape':
        p = site/'elbow'; outside = tmp_path/'outside'; p.rename(outside); p.symlink_to(outside, target_is_directory=True)
    before = inventory(tmp_path)
    with pytest.raises(ValueError):
        configure_dictionary_engine(sdk, expected_dialect='' if defect == 'empty-dialect' else 'CHEMICAL_COMPONENTS_CIF')
    assert inventory(tmp_path) == before
