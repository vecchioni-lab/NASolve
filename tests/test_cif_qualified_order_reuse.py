"""A previously qualified numerical dictionary can travel into a fresh ordinary request."""
from copy import deepcopy
from hashlib import sha256
import shutil

import pytest

from tests.test_cif_candidate_usability import native_case


@pytest.mark.parametrize("change", ("none", "ordinary_hit", "different_consumer", "changed_projection", "different_producer", "no_generation_record", "malformed_execution"))
def test_ordinary_lookup_accepts_only_the_exact_source_order_projection(tmp_path, change):
    from nasolve.cif_acquisition_recovery import freeze_connected_order_snapshot
    from nasolve.cif_candidate_usability import qualify_candidate_native
    from nasolve.cif_dictionary_store import make_dictionary_request, publish_dictionary, resolve_dictionary_snapshot
    from nasolve.cif_generation_acquisition import POLICY_ID as ACQUISITION, generation_dictionary_options
    from nasolve.cif_generation_input import CONNECTED_INPUT_POLICY, POLICY_ID, source_input_files
    from nasolve.cif_purine_representation import EXACT_POLICY_ID

    source, candidate, model, native = native_case(tmp_path)
    code = "Q17"
    authority = "EXPLICIT"
    consumer = dict(name="test-native-reader",version="1",sha256="a"*64)
    pin = dict(anchor="phenix_installation",path="worker.py",sha256=sha256(b"worker").hexdigest(),size=6)
    generation = dict(installation_root=tmp_path/"sdk", python_executable=tmp_path/"python",
                      elbow_executable=tmp_path/"elbow", environment={}, phenix_version="first", expected_dialect="CHEMICAL_COMPONENTS_CIF", single_block_steps=12,
                      api_sources=[pin], prior_sources=[pin], source_input_policy=POLICY_ID, bond_representation_policy=EXACT_POLICY_ID)
    normal = make_dictionary_request(source,code,source_authority=authority,**generation_dictionary_options(generation))
    alternate = dict(normal,recipe=dict(normal["recipe"],source_input_policy=CONNECTED_INPUT_POLICY))
    qualification = qualify_candidate_native(source,candidate,model,code,native,bond_representation_policy=EXACT_POLICY_ID)
    projection,_ = source_input_files(source.read_bytes(),code,policy=CONNECTED_INPUT_POLICY)
    provenance = dict(converged=None,stopping="NOT_REPORTED",notes=[],generation_acquisition=dict(
        policy_id=ACQUISITION, request=deepcopy(alternate),consumer=consumer,source_preparation=projection,
        generation_status="CANDIDATE_REVIEW",execution=dict(status="COMPLETED")))
    if change == "changed_projection":
        projection["consumer"]["sha256"] = "9"*64
    if change == "malformed_execution":
        provenance["generation_acquisition"]["execution"] = "COMPLETED"
    if change == "no_generation_record":
        del provenance["generation_acquisition"]
    store = tmp_path/"store"
    publish_dictionary(store,alternate,source,candidate,qualification,consumer=consumer,provenance=provenance)
    if change=="ordinary_hit":
        publish_dictionary(store,normal,source,candidate,qualification,consumer=consumer,provenance=dict(converged=None,stopping="NOT_REPORTED",notes=[]))
    if change=="different_consumer":
        consumer = dict(consumer,version="other")
    if change=="different_producer":
        generation["phenix_version"] = "other"
    target = tmp_path/"staged"
    kept = freeze_connected_order_snapshot(source,code,authority,generation,consumer,store,target)
    if change!="none":
        assert kept is None
        return
    assert kept == target
    shutil.rmtree(store)
    source.unlink()
    assert resolve_dictionary_snapshot(target)["manifest"]["request"] == alternate
