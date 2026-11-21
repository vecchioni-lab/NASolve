"""A portable copy retains exact native mechanics and the serialized objective."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from tests.test_cif_candidate_usability import native_case


@pytest.mark.parametrize('defect', ['none', 'target', 'not_repeated', 'not_finite',
    'missing_policy', 'guessed_ss', 'definition', 'missing_proxy', 'moved_coordinate',
    'api', 'fatal', 'missing_energy'])
def test_readback_requires_exact_native_bundle_and_unchanged_fixed_objective(tmp_path, defect):
    path = Path(__file__).parents[1] / 'scripts/cif_numerical_recovery_probe_template.py'
    spec = importlib.util.spec_from_file_location('cedar61readback', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, _, model, expected = native_case(tmp_path)
    native = deepcopy(expected)
    if defect == 'target':
        for row in native['energy_inventory']['snapshots']: row['target'] += 1
    if defect == 'not_repeated': native['energy_inventory']['snapshots'][1]['target'] += 1
    if defect == 'not_finite': native['energy_inventory']['snapshots'][0]['gradient'][0] = float('nan')
    if defect == 'missing_policy': native['restraint_policy']['origin_ids'].pop('edits')
    if defect == 'guessed_ss': native['restraint_policy']['secondary_structure_enabled'] = True
    if defect == 'definition': native['monomer_mappings']['rows'][0]['metadata']['group'] = 'BAD'
    if defect == 'missing_proxy': native['geometry']['proxy_details']['bond_simple'].pop()
    if defect == 'moved_coordinate': native['geometry']['sites_cart_exact'][0][0] += .01
    if defect == 'api': native['installed_api_sources'] = [{'sha256': 'bad'}]
    if defect == 'fatal': native['fatal_problems'] = 'unknown component'
    if defect == 'missing_energy': native.pop('energy_inventory')
    result = module._runtime_readback_checks(expected, native, model, 5.)
    assert result['native_usable'] is (defect == 'none')
    assert result['requires_cif_review'] is False
    assert result['model_optimization'] == 'NOT_RUN'
