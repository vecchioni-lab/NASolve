import pytest

from .test_phosphate_restraints import inspection


def test_native_selections_keep_exactly_the_complete_individual_forces():
    from nasolve.cif_phosphate_runtime import project_phosphate_terms
    obs = inspection()
    terms = obs["native_reference_links"]["groups"][0]["terms"]
    labels = [("X:8","RX9",n) for n in ("C4'", "C3'", "O3'")] + [
              ("Y:14","Q2",n) for n in ("P","OP1","OP2","O5'","C5'")]
    all_terms = project_phosphate_terms(obs, terms, labels)
    assert len(all_terms) == 7
    selected = list(reversed([a for a in labels if a[2] != "OP2"]))
    rows = project_phosphate_terms(obs, terms, selected)
    assert len(rows) == 6 and [r[0] for r in rows] == [r[0] for r in all_terms
            if all(labels[i][2] != "OP2" for i in r[1])]
    for term, indices in rows:
        assert [selected[i][2] for i in indices] == [name for _, name in term["atoms"]]
    assert project_phosphate_terms(obs, terms, [a for a in labels if a[0] == "X:8"]) == []
    with pytest.raises(ValueError, match="ambiguous|duplicate"):
        project_phosphate_terms(obs, terms, [*labels, labels[0]])

def test_joint_phosphates_require_distinct_ends_in_one_registered_model():
    from copy import deepcopy
    from nasolve.cif_phosphate_runtime import RegisteredPhosphateRuntime

    def registration(identifier, donor, acceptor):
        return {
            "model_sha256": "a" * 64,
            "registered_continuation": {
                "continuation_id": identifier, "registered_graph_sha256": "b" * 64,
                "copy_id": "A", "sources": {"registration_sha256": "c" * 64},
            },
            "o3": [donor, "DA", "O3'"], "phosphate": [acceptor, "DC", "P"],
        }

    with pytest.raises(ValueError, match="At least one"):
        RegisteredPhosphateRuntime.check_group([])
    one = registration(11, "K:21", "K:10")
    two = registration(17, "K:10", "J:33")
    # Adjacent links can share a nucleotide on opposite chemical ends.
    assert RegisteredPhosphateRuntime.check_group([one, two]) == (11, 17)
    for path, value, message in [
        (("registered_continuation", "continuation_id"), 11, "ID"),
        (("registered_continuation", "registered_graph_sha256"), "d" * 64, "registration"),
        (("registered_continuation", "sources"), {"registration_sha256": "e" * 64}, "registration"),
        (("model_sha256",), "f" * 64, "model"),
        (("o3", 0), "K:21", "O3"),
        (("phosphate", 0), "K:10", "phosphorus"),
    ]:
        changed = deepcopy(two)
        target = changed if len(path) == 1 else changed[path[0]]
        target[path[-1]] = value
        with pytest.raises(ValueError, match=message):
            RegisteredPhosphateRuntime.check_group([one, changed])
