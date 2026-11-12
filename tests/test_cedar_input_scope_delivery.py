"""One compatibility table for old Cedar input/action combinations.

Each template() creates a fresh module. These cases previously repeated the same
reader check in eleven delivery test functions; scientific receipt tests stay in
those files. Only identical input/action/expected-result rows were deduplicated.
"""
from types import SimpleNamespace
import pytest
from tests.test_cedar66_delivery import template


@pytest.mark.parametrize('delivery,action,allowed', [
    ('63_Cedar', 'saved_postmr_construction_native_only', False),
    ('64_Cedar', 'local_dictionary_reuse_only', False),
    ('64_Cedar', 'postmr_construction_native_only', False),
    ('64_Cedar', 'saved_native_usability_only', False),
    ('64_Cedar', 'saved_postmr_construction_native_only', True),
    ('65_Cedar', 'local_dictionary_reuse_only', True),
    ('65_Cedar', 'ordinary_acquisition_only', False),
    ('65_Cedar', 'saved_postmr_construction_native_only', False),
    ('66_Cedar', 'local_dictionary_reuse_only', False),
    ('66_Cedar', 'ordinary_acquisition_only', True),
    ('66_Cedar', 'source_reuse_qualification_only', False),
    ('67_Cedar', 'ordinary_acquisition_only', False),
    ('67_Cedar', 'source_reuse_qualification_only', True),
    ('69_Cedar', 'postmr_dictionary_reuse_only', False),
    ('70_Cedar', 'postmr_dictionary_reuse_only', True),
    ('70_Cedar', 'postmr_readyset_consumption_only', False),
    ('70_Cedar', 'saved_source_reuse_only', False),
    ('71_Cedar', 'postmr_dictionary_reuse_only', False),
    ('71_Cedar', 'postmr_readyset_consumption_only', True),
    ('72_Cedar', 'postmr_dictionary_reuse_only', False),
    ('72_Cedar', 'postmr_readyset_consumption_only', True),
    ('73_Cedar', 'postmr_dictionary_reuse_only', False),
    ('73_Cedar', 'postmr_readyset_consumption_only', True),
    ('74_Cedar', 'postmr_cached_model_only', False),
    ('74_Cedar', 'postmr_dictionary_reuse_only', False),
    ('74_Cedar', 'postmr_readyset_consumption_only', True),
    ('75_Cedar', 'postmr_cached_model_only', True),
    ('75_Cedar', 'postmr_readyset_consumption_only', False),
    ('76_Cedar', 'postmr_cached_model_only', True),
    ('76_Cedar', 'postmr_readyset_consumption_only', False),
    ('76_Cedar', 'saved_native_usability_only', False),
    ('77_Cedar', 'postmr_cached_model_only', False),
])
def test_delivery_action_requires_its_declared_input(delivery, action, allowed):
    module = template()
    args = SimpleNamespace(**{action: True})
    if allowed:
        module._check_constructor_input_mode(args, delivery)
    else:
        with pytest.raises(ValueError):
            module._check_constructor_input_mode(args, delivery)
