"""Read chemistry while Phenix still owns the effective monomer objects."""
from copy import deepcopy
from hashlib import sha256
import json
import sys
from types import SimpleNamespace as NS

import pytest

from nasolve import cif_native_parent_chemistry as chemistry


class Mapping:
    def summary(self):
        return object()


def test_returned_summaries_bind_the_native_mappings_in_order():
    a, b = Mapping(), Mapping()
    with chemistry._capture_returns(Mapping.summary) as pairs:
        summaries = [x.summary() for x in (a, b)]
    assert sys.getprofile() is None
    assert chemistry._matching_mappings(pairs, summaries) == [a, b]
    for invalid in (summaries[::-1], summaries[:1], [object(), object()]):
        with pytest.raises(ValueError, match="summaries"):
            chemistry._matching_mappings(pairs, invalid)
    with pytest.raises(ValueError):
        chemistry._matching_mappings([], [])


def test_leave_foreign_profiler_alone_even_when_original_error_propagates():
    previous = sys.getprofile()
    def foreign(*args):
        pass
    try:
        sys.setprofile(foreign)
        with pytest.raises(ValueError, match="profiler"):
            with chemistry._capture_returns(Mapping.summary):
                pytest.fail("Existing profiling callback was replaced")
        assert sys.getprofile() is foreign
        sys.setprofile(None)
        with pytest.raises(LookupError, match="original"):
            with chemistry._capture_returns(Mapping.summary):
                sys.setprofile(foreign)
                raise LookupError("original failure")
        assert sys.getprofile() is foreign
    finally:
        sys.setprofile(previous)


def test_foreign_replacement_cannot_yield_a_successful_observation():
    previous = sys.getprofile()
    def replacement(*args):
        pass
    try:
        with pytest.raises(ValueError, match="ownership"):
            with chemistry._capture_returns(Mapping.summary):
                sys.setprofile(replacement)
        assert sys.getprofile() is replacement
    finally:
        sys.setprofile(previous)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


@pytest.fixture
def original():
    names = {"hydrogen bonds": 2, "edits": 4, "basepair stacking": 6,
             "basepair parallelity": 7, "basepair planarity": 9}
    geometry = {"proxy_details": {k: [] for k in chemistry._PROXY_FAMILIES},
                "custom_proxy_requests": []}
    geometry["proxy_details"]["bond_simple"].append(
        {"origin_id": 0, "i_seqs": [0, 1], "atoms":["P", "O"], "weight": 400.0,
         "distance_ideal": 1.6, "symmetry_operation": None})
    geometry["proxy_counts"] = {k: len(v) for k, v in geometry["proxy_details"].items()}
    geometry["proxy_count_status"] = {k: "RECORDED" for k in chemistry._PROXY_STATUS_FAMILIES}
    atom_list = [{"i_seq": i, "label": name, "xyz": [float(i), 0.0, 0.0]}
                 for i, name in enumerate(("P", "O"))]
    components = {"status": "RECORDED", "rows": [{"site": "A:1",
        "literal_identity": {"status":"RECORDED"}, "chem_mod_ids":{"status":"RECORDED","ids":["5*END"]},
        "metadata": {"status": "RECORDED", "effective_definition":{
                     **{k:[] for k in chemistry._COMPONENT_CATEGORIES}, "atoms":[{"atom_id":"P"}]},
                     "formal_charge_readback": {"status": "UNSUPPORTED"}}}]}
    return {"status": "REVIEW", "fatal_problems": None, "inventory_detail": "linked", "unused_definitions": [],
            "unsupported_fields": [], "atom_count": 2, "atoms": atom_list,
            "restraint_policy": {"origin_ids": names, "secondary_structure_enabled": False},
            "geometry": geometry, "monomer_mappings": components}


def bound_to(payload, *, record_changes=None):
    record = {"anchor":"literal_na_input_directory", "path":"native/native_validation.json",
              "sha256":sha256(payload).hexdigest(),"size":len(payload)}
    record.update(record_changes or {})
    report = canonical({"policy_id":"cif-typed-native-literal-inputs-v1", "files":[record],
                        "compilation":{"policy_id":"narestraints-explicit-membership-v1",
                                       "compiled_requests":[],"policy_authority":"NARestraints"}})
    return NS(source_report_json=report), sha256(report).hexdigest()


def test_binds_source_native_bytes_to_original_compiler_report(original):
    data = canonical(original)
    bound, pin = bound_to(data)
    before, policy = chemistry._source_observation(bound, pin, data)
    assert before == original and policy["policy_authority"] == "NARestraints"
    with pytest.raises(ValueError):
        chemistry._source_observation(bound, "0"*64, data)
    with pytest.raises(ValueError):
        chemistry._source_observation(bound, pin, data + b" ")
    for changes in ({"anchor":"other"}, {"path":"elsewhere/native_validation.json"}, {"size":10}):
        wrong, pinned = bound_to(data,record_changes=changes)
        with pytest.raises(ValueError):
            chemistry._source_observation(wrong,pinned,data)


def test_actual_component_terms_and_all_proxy_families_are_compared(original):
    policy = {"compiled_requests":[]}
    live = {k:deepcopy(original[k]) for k in ("restraint_policy","geometry","atom_count","atoms","unsupported_fields")}
    components = deepcopy(original["monomer_mappings"])
    result = chemistry._compare(original, live, components, policy)
    assert result["status"] == "MATCH" and result["residues"] == 1
    assert result["sites_without_full_formal_charge_readback"] == ["A:1"]
    assert result["proxy_families"]["bond_simple"]["unchanged"] == 1
    assert result["scientific_acceptance"] is False
    changed = deepcopy(components)
    changed["rows"][0]["chem_mod_ids"]["ids"] = []
    with pytest.raises(ValueError, match="A:1"):
        chemistry._compare(original, live, changed, policy)
    bad = deepcopy(live)
    bad["geometry"]["proxy_details"]["bond_simple"][0]["weight"] = 399.999
    with pytest.raises(chemistry.NativeParentChemistryMismatch, match="bond_simple") as exc:
        chemistry._compare(original, bad, components, policy)
    changed_weight = exc.value.differences["restraint_families"]["bond_simple"]
    assert changed_weight["changed_with_identical_atoms_and_origin"] == 1
    assert changed_weight["first_example"]["parameters"] == {"weight":{"source":400.0,"live":399.999}}
    bad = deepcopy(live)
    del bad["geometry"]["proxy_details"]["chirality"]
    with pytest.raises(ValueError, match="families"):
        chemistry._compare(original, bad, components, policy)
    bad = deepcopy(live)
    bad["restraint_policy"]["origin_ids"]["edits"] = 77
    with pytest.raises(ValueError, match="origin"):
        chemistry._compare(original, bad, components, policy)
    bad = deepcopy(live)
    bad["atoms"][0]["xyz"][0] += 0.01
    with pytest.raises(ValueError, match="coordinates"):
        chemistry._compare(original, bad, components, policy)


def test_optional_live_comparison_does_not_make_an_execution_receipt(original):
    for key, value in (("unsupported_fields", ["missing type"]), ("fatal_problems", "untyped atom"),
                       ("unused_definitions", ["different control"]), ("inventory_detail", "component-only")):
        bad=dict(original, **{key:value})
        raw=canonical(bad)
        bound,pin=bound_to(raw)
        with pytest.raises(ValueError):
            chemistry._source_observation(bound,pin,raw)


def test_repeated_same_atom_terms_do_not_supply_a_unique_difference_example():
    check = {"missing": 1, "extra": 1, "unmatched_requests": []}
    earlier = {"origin_id": 0, "atoms": ["P", "O"], "weight": 5.0}
    changed = dict(earlier, weight=4.0)
    result = chemistry._restraint_difference(check, [earlier, earlier], [changed])
    assert result["first_example"] is None
    assert result["changed_with_identical_atoms_and_origin"] == 0


@pytest.mark.parametrize("changed", [{"slack": 0.1}, {"top_out": True}])
def test_compiled_parallelity_keeps_its_force_law(original, changed):
    request = {"kind": "parallelity", "action": "add", "atoms":["A", "B", "C"], "i_seqs":[0,1,2],
               "j_atoms":["D", "E", "F"], "j_seqs":[3,4,5], "target_angle_deg":0.0, "weight":100.0}
    policy = {"compiled_requests":[request]}
    original["atoms"] = [{"i_seq": i, "label": a, "xyz":[float(i),0.0,0.0]} for i,a in enumerate("ABCDEF")]
    original["atom_count"] = 6
    live=deepcopy(original)
    live["geometry"]["custom_proxy_requests"]=[request]
    physical={k:v for k,v in request.items() if k not in ("kind","action")}
    physical.update(origin_id=4, slack=0.0, top_out=False)
    live["geometry"]["proxy_details"]["parallelity"]=[physical]
    live["geometry"]["proxy_counts"]["parallelity"]=1
    assert chemistry._compare(original,live,original["monomer_mappings"],policy)["status"]=="MATCH"
    physical.update(changed)
    with pytest.raises(ValueError, match="slack or top-out"):
        chemistry._compare(original,live,original["monomer_mappings"],policy)
