import copy
import json

import pytest

from nasolve.topostitch import DuplexEnd, propose_connections


HASH = "a" * 64


def end(name, sequence="GA", x=0.0, polarity="5prime", state="available"):
    return DuplexEnd(name, sequence, polarity, (x, 0.0, 0.0), state)


def scan(ends, **kwargs):
    return propose_connections(ends, source_model_sha256=HASH,
                               max_distance_angstrom=20.0, **kwargs)


def test_complementary_ends_produce_review_only_antiparallel_pairing():
    result = scan([end("left"), end("right", "TC", 10)])
    candidate, = result["candidates"]
    assert candidate["ends"] == ["left", "right"]
    assert candidate["residue_pairs"] == [[0, 1], [1, 0]]
    assert candidate["distance_angstrom"] == 10
    assert candidate["edge_type"] == "base_pairing"
    assert candidate["geometry_validated"] is False
    assert result["selected_candidate"] is None
    assert result["runtime_authority"] is False
    assert result["inspection_required"] is True
    assert result["source_model_sha256"] == HASH
    assert result["source_bytes_verified"] is False


def test_nearest_noncomplementary_end_is_not_selected():
    result = scan([end("a"), end("b", "AA", 1), end("c", "TC", 10)])
    assert [c["ends"] for c in result["candidates"]] == [["a", "c"]]


def test_competing_partners_remain_unselected_including_shared_partner():
    result = scan([end("a"), end("b", "TC", 1), end("c", "TC", 2)])
    assert len(result["candidates"]) == 2
    assert all(e["status"] == "COMPETING_CANDIDATES" for e in result["ends"])
    assert result["selected_candidate"] is None


@pytest.mark.parametrize("state", ["connected", "free", "unknown"])
def test_known_connections_free_ends_and_uncertain_boundaries_are_not_repaired(state):
    result = scan([end("a", state=state), end("b", "TC", 2)])
    assert result["candidates"] == []
    assert result["ends"][0]["status"] == "EXCLUDED"
    assert result["ends"][0]["reason"] == state


def test_polarity_length_register_and_distance_are_not_silently_changed():
    for other in [end("b", "TC", 2, "3prime"), end("b", "TTC", 2),
                  end("b", "CT", 2), end("b", "TC", 21)]:
        assert scan([end("a"), other])["candidates"] == []
    assert len(scan([end("a"), end("b", "TC", 20)])["candidates"]) == 1
    assert len(scan([end("a", polarity="3prime"),
                     end("b", "TC", 10, "3prime")])["candidates"]) == 1


def test_unknown_chemistry_is_excluded_not_guessed():
    result = scan([end("a", None), end("b", "TC", 2)])
    assert result["candidates"] == []
    assert result["ends"][0]["reason"] == "unknown_sequence"


def test_empty_inventory_and_single_end_are_valid_no_candidate_results():
    assert scan([])["candidates"] == []
    assert scan([end("a")])["ends"][0]["status"] == "NO_CANDIDATE"


def test_deterministic_json_no_mutation_and_input_fingerprint():
    ends = [end("z", "TC", 2), end("a")]
    before = copy.deepcopy(ends)
    a, b = scan(ends), scan(list(reversed(ends)))
    assert a == b and ends == before
    assert json.loads(json.dumps(a, allow_nan=False)) == a
    assert a["input_sha256"] != scan([end("z", "TC", 3), end("a")])["input_sha256"]


@pytest.mark.parametrize("kwargs", [
    {"end_id": ""}, {"end_id": "a b"}, {"sequence": "G(N)"},
    {"sequence": ""}, {"sequence": "ga"}, {"sequence": 12},
    {"polarity": "unknown"}, {"position": (0, 0)},
    {"position": (True, 0, 0)}, {"position": (float("nan"), 0, 0)},
    {"position": (float("inf"), 0, 0)}, {"state": "guess"},
])
def test_invalid_end_records_fail_before_inference(kwargs):
    values = dict(end_id="a", sequence="GA", polarity="5prime",
                  position=(0, 0, 0), state="available")
    values.update(kwargs)
    with pytest.raises(ValueError):
        DuplexEnd(**values)


@pytest.mark.parametrize("distance", [0, -1, True, float("nan"), float("inf"), "20"])
def test_invalid_search_bounds_fail(distance):
    with pytest.raises(ValueError):
        propose_connections([], source_model_sha256=HASH,
                            max_distance_angstrom=distance)


@pytest.mark.parametrize("hash_value", ["", "a" * 63, "x" * 64, None])
def test_invalid_provenance_hash_fails(hash_value):
    with pytest.raises(ValueError):
        propose_connections([], source_model_sha256=hash_value,
                            max_distance_angstrom=20)


def test_duplicate_end_ids_and_nonrecords_fail():
    for ends in [[end("a"), end("a", "TC", 2)], [object()]]:
        with pytest.raises(ValueError):
            scan(ends)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_budget_fails(limit):
    with pytest.raises(ValueError):
        scan([], max_pairs=limit)


def test_budget_exhaustion_does_not_masquerade_as_unique_connection():
    with pytest.raises(ValueError, match="budget"):
        scan([end("a"), end("b", "TC", 1), end("c", "TC", 2)], max_pairs=1)


def test_list_position_is_copied_into_immutable_record():
    coords = [0., 0., 0.]
    item = DuplexEnd("a", "GA", "5prime", coords)
    coords[0] = 999
    assert item.position == (0., 0., 0.)
