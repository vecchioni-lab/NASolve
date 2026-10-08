"""Paired W Z:P and annotated off-pair sequence targets.

This is a synthetic identity/intent/plan check, not Phenix/Coot refinement.
The base partner choices preserve plausible pairing rather than manufacturing
mismatched sites merely to exercise the new parser.
"""
from pathlib import Path
import pytest
from nasolve.automr_input import read_intent
from nasolve.component_normalization import target_changes
from nasolve.curated_ligands import CURATED_LIGANDS, PDB_DEPOSITION_ALIASES
from nasolve.postmr import PostMRPreparationError, build_mutation_plan
from nasolve.residue_aliases import resolve_ligand
from nasolve.sequence_syntax import sequence_length, sequence_residue_codes
from nasolve.sequence_reference import load_sequence_reference, compile_sequence_family_targets
from tests.helpers import pdb_record

BASE_SEQUENCES = {
    "A": "GAGCAGCCTGTATGGACATCA",
    "B": "CCATACA",
    "C": "GGCTGCT",
    "D": "CTGATGT",
}
ANNOTATED_A = "GAGCAG(5CM)CTGTATGGACA(A1AAZ)CA"
ANNOTATED_C = "G(DG)CTGCT"
SEQUENCES = {**BASE_SEQUENCES, "A": ANNOTATED_A, "C": ANNOTATED_C}
NORMAL_CODES = {"A": "DA", "C": "DC", "G": "DG", "T": "DT"}
STARTS = {"A": 1, "B": 1, "C": 8, "D": 1}
PAIR_SITES = {"A:12": "DZ", "B:4": "DP"}


def _model(tmp_path):
    lines = []
    for chain, sequence in BASE_SEQUENCES.items():
        for resid, base in enumerate(sequence, STARTS[chain]):
            lines.append(pdb_record(
                "ATOM", len(lines) + 1, "C1'", NORMAL_CODES[base], chain, resid, element="C"
            ))
    model = tmp_path / "search.pdb"
    model.write_text("".join(lines) + "END\n")
    return model


def _report():
    return {
        "frame": {"name": "W"},
        "post_mr_plan": {
            "sequences": dict(SEQUENCES),
            "standard_pair": {"requested": "Z:P", "ligand_codes": ["DZ", "DP"]},
            "mutations": {},
        },
        "model_assessment": {"polymer_residue_ids_by_chain": {
            chain: [str(i) for i in range(STARTS[chain], STARTS[chain] + len(seq))]
            for chain, seq in BASE_SEQUENCES.items()
        }},
    }


def test_all_pairs_are_declared_at_correct_numbered_sites(tmp_path):
    assert len(BASE_SEQUENCES["A"]) == sequence_length(ANNOTATED_A) == 21
    assert len(BASE_SEQUENCES["C"]) == sequence_length(ANNOTATED_C) == 7
    codes_a = sequence_residue_codes(ANNOTATED_A, "DNA")
    codes_c = sequence_residue_codes(ANNOTATED_C, "DNA")
    assert codes_a[6] == "5CM"                 # A:7, paired with C:9 DG
    assert codes_a[18] == "A1AAZ"             # A:19, prepared DF, paired with D:4 DA
    assert codes_c[1] == "DG"                 # Explicit TWO-character token at C:9
    assert codes_a[3] == "DC"                 # A:4 remains C, paired with C:12 G
    assert codes_c[4] == "DG"                 # C:12 is G
    model = _model(tmp_path)
    before = model.read_bytes()
    actions = build_mutation_plan(_report(), model)
    assert model.read_bytes() == before
    assert len(actions) == 42
    by_site = {action.site: action for action in actions}
    assert len(by_site) == 42
    for site, target, method, parent in (
        ("A:7", "5CM", "coot-parent-overlap", "DC"),
        ("C:9", "DG", "none", None),
        ("A:19", "DF", "coot-parent-overlap", "DT"),
        ("D:4", "DA", "none", None),
        ("A:4", "DC", "none", None),
        ("C:12", "DG", "none", None),
        ("A:12", "DZ", "coot-parent-overlap", "DC"),
        ("B:4", "DP", "coot-parent-overlap", "DG"),
    ):
        action = by_site[site]
        assert (action.after, action.method, action.parent_code) == (
            target, method, parent), site
    assert by_site["A:19"].deposition_code == "A1AAZ"
    assert target_changes({"A:7": "5CM", "A:19": "A1AAZ"}) == [{
        "site": "A:19", "requested_code": "A1AAZ", "prepared_code": "DF",
        "basis": "reviewed-deposition-to-pdb-code",
    }]


def test_standard_W_config_and_family_compiler_preserve_pair_precedence(tmp_path):
    text = (
        "[automr]\nmode = standard\nframe = W\npair = Z:P\n"
        "sequence_reference = w-metal-scaffold\n[sequences]\n"
        f"A = {ANNOTATED_A}\nC = {ANNOTATED_C}\n"
    )
    cfg = tmp_path / "nasolve.txt"
    cfg.write_text(text)
    intent = read_intent(cfg)
    assert intent.pair == "Z:P" and intent.sequences == {
        "A": ANNOTATED_A, "C": ANNOTATED_C,
    }
    resource = Path(__file__).resolve().parents[1] / (
        "src/nasolve/data/sequence_references/w-metal-scaffold.json"
    )
    reference = load_sequence_reference(resource)
    target = compile_sequence_family_targets(
        reference,
        dataset_sequences=intent.sequences,
        dataset_site_codes=PAIR_SITES,
    )
    sites = {row["site"]: row for row in target["sites"]}
    assert len(sites) == 42
    for site, code in {
        "A:7": "5CM", "C:9": "DG", "A:19": "A1AAZ", "D:4": "DA",
        "A:4": "DC", "C:12": "DG", "A:12": "DZ", "B:4": "DP",
    }.items():
        assert sites[site]["residue_code"] == code
    assert sites["A:12"]["source"] == "dataset_site_chemistry"
    assert sites["A:19"]["source"] == "dataset_sequence"


def test_registered_deposition_alias_is_reviewed_not_general():
    assert PDB_DEPOSITION_ALIASES == {"A1AAZ": "DF"}
    assert CURATED_LIGANDS["DF"].deposition_code == "A1AAZ"
    requested = resolve_ligand("A1AAZ")
    assert requested.ligand_code == "A1AAZ" and requested.used_alias is False


def test_unrelated_registered_five_character_code_still_stops(tmp_path, monkeypatch):
    monkeypatch.setattr("nasolve.residue_aliases.known_ligand_codes",
                        lambda: frozenset({"DZ", "5CM", "A1AAZ", "ABCDE", "DG"}))
    model = _model(tmp_path)
    report = _report()
    report["post_mr_plan"]["sequences"]["A"] = ANNOTATED_A.replace("(A1AAZ)", "(ABCDE)")
    with pytest.raises(PostMRPreparationError, match="ABCDE.*three-character PDB"):
        build_mutation_plan(report, model)
    assert "ABCDE" not in model.read_text()


def test_annotation_overrides_are_scoped_to_explicit_sites(tmp_path):
    model = _model(tmp_path)
    report = _report()
    report["post_mr_plan"]["mutations"]["A:7"] = {
        "requested": "DG", "ligand_code": "DG"}
    actions = build_mutation_plan(report, model)
    sites = {a.site: a.after for a in actions}
    assert sites["A:7"] == "DG"
    assert sites["A:19"] == "DF" and sites["C:9"] == "DG"
    assert sites["A:12"] == "DZ" and sites["B:4"] == "DP"
