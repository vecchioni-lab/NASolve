"""Receiving shared owners must not substitute newer live helper bytes."""

from hashlib import sha256

import pytest

from nasolve import refinement_parallelity as runtime


@pytest.mark.parametrize("version", range(3, 13))
def test_received_runtime_retains_qualified_payload(version):
    policy = getattr(runtime, f"V{version}_POLICY_ID")
    actual = runtime._code(policy)
    assert {name: sha256(data).hexdigest() for name, data in actual.items()} == runtime._expected_code(policy)


@pytest.mark.parametrize("version", (10, 11, 12))
def test_phosphate_runtime_preserves_original_recipe_after_live_upgrade(version):
    policy = getattr(runtime, f"V{version}_POLICY_ID")
    actual = runtime._code(policy)
    recipe = actual["code/_nasolve_refinement/topostitch_native_recipe.py"]
    assert sha256(recipe).hexdigest() == "1739b2a7cf11d802bfa9293d7b79b9edcf7bb1ad868b53d4c1b1996b461d7748"
