"""Annotated CCD-in-FASTA contract; fake coordinate records are not scientific runs."""
import json
from pathlib import Path

import pytest

from nasolve.sequence_syntax import (
    SequenceSyntaxError, canonical_sequence, parse_sequence_tokens,
    sequence_length, sequence_residue_codes,
)
from nasolve.automr_input import (
    AutoMRInputError, read_intent, read_sequence_file, _validated_sequences,
)
from nasolve.automr import _validate_edit_targets
from nasolve.model_assessment import inspect_pdb
from nasolve.postmr import PostMRPreparationError, build_mutation_plan
from nasolve.sequence_reference import (
    parse_sequence_reference, compile_sequence_family_targets,
    SequenceReferenceError,
)
from nasolve.campaign_threads import parse_sequence_threads, SequenceThreadError
from tests.helpers import pdb_record


LIGANDS = {"DA", "DC", "DG", "DT", "5CM", "DZ", "DP", "A1AAZ", "A", "1AP"}
EXAMPLE = "CCGC(5CM)AA(DZ)TGC(A1AAZ)"


def installed_stub(monkeypatch):
    monkeypatch.setattr("nasolve.residue_aliases.known_ligand_codes", lambda: frozenset(LIGANDS))


def synthetic_model(path: Path, n: int) -> Path:
    path.write_text("".join(
        pdb_record("ATOM", i, "C1'", "DC", "A", i, element="C")
        for i in range(1, n + 1)
    ) + "END\n")
    return path


def test_exact_requested_example_has_twelve_sites_and_preserves_five_letter_code():
    tokens = parse_sequence_tokens(EXAMPLE, valid_ligand_codes=LIGANDS)
    assert len(tokens) == 12
    assert tokens == (
        "C", "C", "G", "C", "(5CM)", "A", "A", "(DZ)", "T", "G", "C", "(A1AAZ)",
    )
    assert sequence_length(EXAMPLE, valid_ligand_codes=LIGANDS) == 12
    assert sequence_residue_codes(EXAMPLE, "DNA", valid_ligand_codes=LIGANDS) == (
        "DC", "DC", "DG", "DC", "5CM", "DA", "DA", "DZ", "DT", "DG", "DC", "A1AAZ",
    )
    assert canonical_sequence("cCgC(5cm) aa(dz)tgc(A1aaz)", valid_ligand_codes=LIGANDS) == EXAMPLE


def test_single_letter_and_literal_parentheses_have_distinct_semantics():
    assert sequence_residue_codes("A(A)G", "DNA", valid_ligand_codes=LIGANDS) == ("DA", "A", "DG")
    assert sequence_residue_codes("A(A)G", "RNA", valid_ligand_codes=LIGANDS) == ("A", "A", "G")


@pytest.mark.parametrize("bad", [
    "A(DZ", "A()C", "A((DZ))C", "A(DZ))C", "A(D-Z)C", "A(1AP!)C",
    "A(ABCDEF)C", "A(Z)C", "A(ZZZ)C", "AN(C)", "A[DZ]C", "A)C",
])
def test_invalid_or_unknown_tokens_are_rejected_without_guesses(bad):
    with pytest.raises(SequenceSyntaxError):
        parse_sequence_tokens(bad, valid_ligand_codes=LIGANDS)


def test_wrong_polymer_symbol_fails_but_explicit_residue_identity_is_retained():
    with pytest.raises(SequenceSyntaxError, match="DNA"):
        sequence_residue_codes("AU", "DNA", valid_ligand_codes=LIGANDS)
    with pytest.raises(SequenceSyntaxError, match="RNA"):
        sequence_residue_codes("AT", "RNA", valid_ligand_codes=LIGANDS)
    assert sequence_residue_codes("A(DZ)U", "RNA", valid_ligand_codes=LIGANDS) == ("A", "DZ", "U")


def test_plain_sequences_never_need_a_ligand_registry(monkeypatch):
    def unavailable():
        raise AssertionError("Ordinary DNA FASTA must not consult NARestraints")
    monkeypatch.setattr("nasolve.residue_aliases.known_ligand_codes", unavailable)
    assert canonical_sequence("a C g\nt", context="simple") == "ACGT"
    assert sequence_length("ACGT") == 4


def test_inline_and_chain_labelled_fasta_share_the_same_grammar(tmp_path, monkeypatch):
    installed_stub(monkeypatch)
    fasta = tmp_path / "construct.fasta"
    fasta.write_text(">A\nCCGC(5CM)AA\n(DZ)TGC(A1AAZ)\n>B\nG(5CM)C\n")
    expected = {"A": EXAMPLE, "B": "G(5CM)C"}
    assert read_sequence_file(fasta) == expected
    listed = tmp_path / "construct.txt"
    listed.write_text("A = " + EXAMPLE.lower() + "\nB = G(5CM)C\n")
    assert read_sequence_file(listed) == expected
    ini = tmp_path / "nasolve.txt"
    ini.write_text("[automr]\nmode = nonstandard\n[sequences]\nA = " + EXAMPLE + "\n")
    assert read_intent(ini).sequences == {"A": EXAMPLE}
    assert _validated_sequences({"A": EXAMPLE.lower()}, "inline", LIGANDS) == {"A": EXAMPLE}


def test_reviewed_long_deposition_token_uses_df_without_truncation(tmp_path, monkeypatch):
    installed_stub(monkeypatch)
    path = synthetic_model(tmp_path / "model.pdb", 12)
    report = {
        "post_mr_plan": {"sequences": {"A": EXAMPLE}, "standard_pair": None, "mutations": {}},
        "model_assessment": {"polymer_residue_ids_by_chain": {"A": [str(i) for i in range(1, 13)]}},
    }
    # A1AAZ has a *reviewed* PDB-compatible code (DF); arbitrary 4/5-letter
    # target identities still have a separate fail-closed test.
    original = path.read_bytes()
    actions = build_mutation_plan(report, path)
    assert path.read_bytes() == original
    assert (actions[11].site, actions[11].after, actions[11].method) == (
        "A:12", "DF", "coot-parent-overlap",
    )
    assert actions[11].parent_code == "DT"
    assert actions[11].deposition_code == "A1AAZ"
    # A model whose targets fit PDB exercises the existing parent/scaffold route.
    report["post_mr_plan"]["sequences"]["A"] = EXAMPLE.replace("(A1AAZ)", "(DP)")
    actions = build_mutation_plan(report, path)
    assert len(actions) == 12
    assert (actions[4].site, actions[4].after, actions[4].method) == (
        "A:5", "5CM", "coot-parent-overlap",
    )
    assert (actions[7].site, actions[7].after, actions[7].method) == (
        "A:8", "DZ", "coot-parent-overlap",
    )
    assert (actions[11].site, actions[11].after) == ("A:12", "DP")
    assert all(action.site == f"A:{i}" for i, action in enumerate(actions, 1))


def test_explicit_mutation_remains_more_specific_than_annotated_chain(tmp_path, monkeypatch):
    installed_stub(monkeypatch)
    path = synthetic_model(tmp_path / "model.pdb", 3)
    report = {
        "post_mr_plan": {
            "sequences": {"A": "C(5CM)G"}, "standard_pair": None,
            "mutations": {"A:2": {"requested": "DP", "ligand_code": "DP"}},
        },
        "model_assessment": {"polymer_residue_ids_by_chain": {"A": ["1", "2", "3"]}},
    }
    actions = build_mutation_plan(report, path)
    assert [(a.site, a.after) for a in actions] == [
        ("A:1", "DC"), ("A:2", "DP"), ("A:3", "DG"),
    ]


def test_family_reference_overlay_counts_tokens_and_preserves_site_provenance(monkeypatch):
    installed_stub(monkeypatch)
    reference = parse_sequence_reference({
        "schema_version": 1, "kind": "sequence-defined-reference", "id": "annotated", "version": "1",
        "chains": [{
            "chain": "A", "residue_ids": [str(i) for i in range(1, 13)],
            "polymer": "DNA", "sequence": "C" * 12,
        }],
    })
    target = compile_sequence_family_targets(reference, dataset_sequences={"A": EXAMPLE})
    rows = {row["site"]: row for row in target["sites"]}
    assert len(rows) == 12
    assert rows["A:5"]["residue_code"] == "5CM"
    assert rows["A:8"]["residue_code"] == "DZ"
    assert rows["A:12"]["residue_code"] == "A1AAZ"
    assert rows["A:12"]["source"] == "dataset_sequence"
    assert [item["source"] for item in rows["A:12"]["assignments"]] == [
        "family_reference", "dataset_sequence",
    ]


def test_reference_itself_may_use_annotated_sequence(monkeypatch):
    installed_stub(monkeypatch)
    reference = parse_sequence_reference({
        "schema_version": 1, "kind": "sequence-defined-reference", "id": "annotated", "version": "1",
        "chains": [{"chain": "A", "residue_ids": ["1", "2", "3"],
                    "polymer": "DNA", "sequence": "C(5CM)T"}],
    })
    target = compile_sequence_family_targets(reference)
    assert [r["residue_code"] for r in target["sites"]] == ["DC", "5CM", "DT"]


def test_preflight_counts_residues_instead_of_characters(tmp_path, monkeypatch):
    installed_stub(monkeypatch)
    from nasolve.automr_input import AutoMRIntent, ResolvedAutoMRInput, DatasetFiles
    from nasolve.model_assessment import inspect_pdb
    from types import SimpleNamespace
    model = synthetic_model(tmp_path / "model.pdb", 12)
    assessment = inspect_pdb(model, polymer_ligand_codes=LIGANDS)
    resolved = SimpleNamespace(
        sequence_thread=None, sequences={"A": EXAMPLE}, mutations={}, frame=None,
        model_provider=None, allow_op3_sites=(), backbone_sites={},
    )
    _validate_edit_targets(resolved, assessment)
    resolved.sequences = {"A": "C" * 11}
    with pytest.raises(AutoMRInputError, match="length"):
        _validate_edit_targets(resolved, assessment)


def test_campaign_thread_sequences_retain_annotations(monkeypatch):
    installed_stub(monkeypatch)
    content = b'''schema_version = 1
[sequence_threads.w]
datasets = ["test"]
sequence_reference = "w-metal-scaffold"
[sequence_threads.w.sequences]
A = "CCGC(5CM)AA(DZ)TGC(A1AAZ)"
'''
    threads = parse_sequence_threads(content)
    assert threads["w"]["sequences"]["A"] == EXAMPLE
    with pytest.raises(SequenceThreadError):
        parse_sequence_threads(content.replace(b"(5CM)", b"(BAD)"))
