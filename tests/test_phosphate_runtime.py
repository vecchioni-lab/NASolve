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
