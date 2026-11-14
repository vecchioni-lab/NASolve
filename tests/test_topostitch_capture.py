"""Distinct reconstruction regressions, independent of optional native imports."""
from copy import deepcopy
import pytest
from nasolve.topostitch_capture import compare_reconstructed_context


def capture():
    return dict(schema_version=1, status='REVIEW', automatic_adoption=False,
        optimization='NOT_RUN', model_editing='NOT_RUN', scientific_approval='NOT_RUN',
        fatal_problems=None, unused_definitions=[], unsupported_fields=[],
        atoms=[{'name': 'P', 'xyz': [1., 2., 3.]}], atom_count=1,
        monomer_mappings=[{'residue': 'DA'}], geometry={'bond': [1., 2.]},
        installed_api_sources=[dict(module='native', sha256='a'*64, historical_path='/old/api')],
        restraint_policy={'secondary_structure_enabled': False},
        full_monomer_inventory={'atom_types': ['P']},
        energy_inventory={'normalization': False, 'target': 2.},
        nonbonded_inventory={'policy_id': 'cif-native-nonbonded-asu-attribution-v1',
                             'pairs': [[0, 0, 'x+1,y,z']]},
        phil_adaptations=[{'input': 'inputs/001.phil'}], dictionary_loading=[],
        parameter_consumers=['native'])


def test_source_location_is_provenance_but_exact_bytes_are_checked():
    before=capture();after=deepcopy(before)
    after['installed_api_sources'][0]['historical_path']='/new/api'
    report=compare_reconstructed_context(before,after)
    assert report['status']=='INITIAL_OBSERVED_CONTEXT_MATCH'
    assert not report['complete_exclusion_policy_authenticated']
    assert not report['runtime_authority']
    after['installed_api_sources'][0]['sha256']='b'*64
    with pytest.raises(ValueError,match='installed_api_sources'):
        compare_reconstructed_context(before,after)


@pytest.mark.parametrize('field', ['atoms','monomer_mappings','geometry',
    'full_monomer_inventory','energy_inventory','nonbonded_inventory','phil_adaptations'])
def test_changed_observed_context_cannot_reuse_a_binding(field):
    before=capture();after=deepcopy(before)
    if isinstance(after[field],list): after[field].append({'changed': True})
    else: after[field]['changed']=True
    with pytest.raises(ValueError,match=field):compare_reconstructed_context(before,after)


@pytest.mark.parametrize('change', ['missing','nonfinite','normalized','secondary', 'identity_only', 'claim'])
def test_incomplete_or_different_policy_rejected_even_when_both_reports_match(change):
    report=capture()
    if change=='missing':del report['full_monomer_inventory']
    if change=='nonfinite':report['energy_inventory']['target']=float('nan')
    if change=='normalized':report['energy_inventory']['normalization']=True
    if change=='secondary':report['restraint_policy']['secondary_structure_enabled']=True
    if change=='identity_only':report['nonbonded_inventory']['policy_id']='identity-only'
    if change=='claim':report['optimization']='COMPLETED'
    with pytest.raises(ValueError):compare_reconstructed_context(report,deepcopy(report))


def test_no_silent_field_dropping_or_boolean_integer_aliasing():
    before=capture();after=deepcopy(before);after['new_policy']=False
    with pytest.raises(ValueError,match='new_policy'):compare_reconstructed_context(before,after)
    after=deepcopy(before);after['energy_inventory']['target']=True
    with pytest.raises(ValueError,match='energy_inventory'):compare_reconstructed_context(before,after)
