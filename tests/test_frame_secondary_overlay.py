"""Regression for run-local Saenger replacement at modified W-frame sites.

Uses the *real committed* NARestraints workbook and the packaged W template.
No fixture swaps a modified pair's identity or stubs its atom-role generator.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from nasolve.frame_postmr import restraint_data_directory
from nasolve.frame_secondary_overlay import (
    FrameSecondaryOverlayError, prepare_frame_modified_secondary_overlay,
)
from nasolve.postmr import _patch_narestraints_records
from restraints.base_pairs import read_base_pair_file
from restraints.residue_library import load_residue_records

from .helpers import pdb_record


_W_RESOURCE = restraint_data_directory()
_NA_ROLES = (
    "C2", "N1", "N2", "N3", "N4", "N6", "C4", "C5", "C6",
    "C7", "C8", "N7", "N9", "O2", "O4", "O6",
)


def _sample_model(path: Path, *, changed: bool = True,
                  unknown: bool = False, incompatible: bool = False,
                  mixed: bool = False) -> None:
    records = load_residue_records()
    specifications = [
        ("A", 7, "ZZZ" if unknown else "5CM" if changed else "DC"),
        ("C", 9, "DA" if incompatible else "DG"),
        ("A", 19, "DF" if changed else "DT"),
        ("D", 4, "DA"),
        # The standard A:12/B:4 pair is handled independently by Std_padd.
        ("A", 12, "DZ"),
        ("B", 4, "DP"),
    ]
    if mixed:
        # Same W model, four *different* named families present at once,
        # including the central Z:P pair already covered by Std_padd.
        # G:C -> B:S and C:G -> K:X retain actual role orientation;
        # A:T -> D:T uses the distinct diaminopurine recipe.
        specifications.extend([
            ("A", 5, "1AP"), ("C", 11, "DT"),
            ("A", 6, "IGU"), ("C", 10, "S6G"),
            ("A", 20, "CGY"), ("D", 3, "DX"),
        ])
    output = []
    serial = 0
    for chain, site, code in specifications:
        record = next(
            (r for r in records if r.get("Ligand code") == code),
            None,
        )
        atoms = {"C1'", "C2'", "O4'", "S1", "S2"}
        if record is not None:
            atoms.update(
                record[role].strip()
                for role in _NA_ROLES
                if isinstance(record.get(role), str) and record[role].strip()
            )
        for atom in sorted(atoms):
            serial += 1
            first = atom[0].upper()
            output.append(pdb_record(
                "ATOM" if code in {"DA", "DC", "DG", "DT"} else "HETATM",
                serial, atom, code, chain, site,
                element=first if first in {"C", "N", "O", "S", "P"} else "C",
                x=float(serial % 10),
            ))
    path.write_text("".join(output) + "END\n", encoding="utf-8")


def _run(tmp_path: Path, *, changed: bool = True,
         unknown: bool = False, incompatible: bool = False,
         mixed: bool = False):
    model = tmp_path / "input.pdb"
    _sample_model(model, changed=changed, unknown=unknown,
                  incompatible=incompatible, mixed=mixed)
    source = _W_RESOURCE / "5W6W_secondary_structure.eff"
    secondary = tmp_path / "5W6W_secondary_structure.eff"
    pair_file = tmp_path / "Std_padd.txt"
    pair_file.write_text(
        (_W_RESOURCE / "5W6W_Std_padd.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return model, source, secondary, pair_file


def test_two_modified_scaffold_pairs_are_replaced_by_atom_role_recipes(tmp_path):
    model, source, secondary, pair_file = _run(tmp_path)
    original_text = source.read_text(encoding="utf-8")
    original_pair = pair_file.read_text(encoding="utf-8")

    result = prepare_frame_modified_secondary_overlay(
        model, model, source, secondary, pair_file,
        patch_records=_patch_narestraints_records,
    )

    assert result["mode"] == "modified-frame-pairs-to-narestraints"
    assert result["base_pair_count"] == 17
    assert result["retained_saenger_count"] == 15
    assert result["replaced_saenger_count"] == 2
    assert result["explicit_new_pair_count"] == 2
    modified = {frozenset(x["sites"]): x for x in result["replacements"]}
    c_g = modified[frozenset(("A:7", "C:9"))]
    t_a = modified[frozenset(("A:19", "D:4"))]
    assert c_g["prepared_codes"] == ["5CM", "DG"]
    assert c_g["base_classes"] == ["C", "G"]
    assert c_g["old_saenger_class"] == 19
    assert c_g["narestraints_recipe"] == "GC"
    assert c_g["explicit_bond_count"] == 3
    assert t_a["prepared_codes"] == ["DF", "DA"]
    assert t_a["base_classes"] == ["T", "A"]
    assert t_a["old_saenger_class"] == 20
    assert t_a["narestraints_recipe"] == "AT"
    assert t_a["explicit_bond_count"] == 2
    assert result["workbook_compatibility_corrections"] == [{
        "ligand_code": "DF", "canonical_atom": "O2",
        "before": "S2", "after": "S1", "scope": "process-local",
    }]

    effective = secondary.read_text(encoding="utf-8")
    assert effective.count("base_pair {") == 15
    assert "base1 = chain 'A' and resid 19" not in effective
    assert "base1 = chain 'A' and resid 7" not in effective
    assert "base1 = chain 'A' and resid 3" in effective
    assert "base1 = chain 'A' and resid 4" in effective
    assert "secondary_structure" in effective
    assert "saenger_class = 20" in effective
    assert "saenger_class = 19" in effective

    stretches = read_base_pair_file(pair_file)
    assert len(stretches) == 3
    assert sum(len(x.pairs()) for x in stretches) == 5
    added_pairs = {
        (
            f"{pair.base1.chain}:{pair.base1.resid}",
            f"{pair.base2.chain}:{pair.base2.resid}",
        )
        for stretch in stretches[1:]
        for pair in stretch.pairs()
    }
    assert added_pairs == {("A:7", "C:9"), ("A:19", "D:4")}
    assert source.read_text(encoding="utf-8") == original_text
    assert original_pair == "A 11:13\nB 5:3\n"
    assert "A 11:13\nB 5:3" in pair_file.read_text()


def test_unmodified_scaffold_stays_byte_equivalent_even_with_modified_std_pair(tmp_path):
    model, source, secondary, pair_file = _run(tmp_path, changed=False)
    old_pair = pair_file.read_bytes()
    result = prepare_frame_modified_secondary_overlay(
        model, model, source, secondary, pair_file,
        patch_records=_patch_narestraints_records,
    )
    assert result["mode"] == "no-modified-frame-overlap"
    assert result["replaced_saenger_count"] == 0
    assert result["retained_saenger_count"] == 17
    assert secondary.read_bytes() == source.read_bytes()
    assert pair_file.read_bytes() == old_pair


@pytest.mark.parametrize("unknown,incompatible", [(True, False), (False, True)])
def test_unknown_chemistry_fails_without_writing_secondary_or_pairs(
    tmp_path, unknown, incompatible,
):
    model, source, secondary, pair_file = _run(
        tmp_path, unknown=unknown, incompatible=incompatible,
    )
    before = pair_file.read_bytes()
    with pytest.raises(FrameSecondaryOverlayError, match="Cannot replace Saenger"):
        prepare_frame_modified_secondary_overlay(
            model, model, source, secondary, pair_file,
            patch_records=_patch_narestraints_records,
        )
    assert not secondary.exists()
    assert pair_file.read_bytes() == before


def test_malformed_frame_pair_fails_closed(tmp_path):
    model, source, secondary, pair_file = _run(tmp_path)
    malformed = tmp_path / "bad-secondary.eff"
    malformed.write_text(source.read_text() + "\nbase_pair { base1 = A\n")
    with pytest.raises(FrameSecondaryOverlayError, match="unparsed base_pair"):
        prepare_frame_modified_secondary_overlay(
            model, model, malformed, secondary, pair_file,
            patch_records=_patch_narestraints_records,
        )
    assert not secondary.exists()


def test_existing_explicit_pair_does_not_get_duplicated(tmp_path):
    model, source, secondary, pair_file = _run(tmp_path)
    with pair_file.open("a", encoding="utf-8") as fh:
        fh.write("\nA 7\nC 9\n")
    before = pair_file.read_text()
    result = prepare_frame_modified_secondary_overlay(
        model, model, source, secondary, pair_file,
        patch_records=_patch_narestraints_records,
    )
    assert result["replaced_saenger_count"] == 2
    assert result["explicit_new_pair_count"] == 1
    assert pair_file.read_text().count("A 7\nC 9") == 1
    assert pair_file.read_text() != before
    assert sum(len(s.pairs()) for s in read_base_pair_file(pair_file)) == 5


def test_four_named_families_plus_modified_context_share_one_overlay(tmp_path):
    """One run may contain Z:P, D:T, B:S, K:X, 5CM:G and DF:A together.

    This is a workbook/atom-role regression, not a native test of missing
    IGU/CGY/DX ligand CIFs or experimental chemistry.
    """
    model, source, secondary, pair_file = _run(tmp_path, mixed=True)
    before_secondary = source.read_bytes()

    result = prepare_frame_modified_secondary_overlay(
        model, model, source, secondary, pair_file,
        patch_records=_patch_narestraints_records,
    )
    assert (result["base_pair_count"], result["retained_saenger_count"],
            result["replaced_saenger_count"], result["explicit_new_pair_count"]) == (
                17, 12, 5, 5,
            )
    replacements = {frozenset(item["sites"]): item for item in result["replacements"]}
    expected = {
        frozenset(("A:5", "C:11")): (["1AP", "DT"], "D_T"),
        frozenset(("A:6", "C:10")): (["IGU", "S6G"], "GC"),
        frozenset(("A:20", "D:3")): (["CGY", "DX"], "GC"),
        frozenset(("A:7", "C:9")): (["5CM", "DG"], "GC"),
        frozenset(("A:19", "D:4")): (["DF", "DA"], "AT"),
    }
    assert set(replacements) == set(expected)
    for pair, (codes, recipe) in expected.items():
        assert replacements[pair]["prepared_codes"] == codes
        assert replacements[pair]["narestraints_recipe"] == recipe
        assert replacements[pair]["explicit_bond_count"] >= 1
    assert secondary.read_text().count("base_pair {") == 12
    assert source.read_bytes() == before_secondary
    assert sum(len(s.pairs()) for s in read_base_pair_file(pair_file)) == 8
    # A:12/B:4 Z:P stays in the original three-pair Std_padd stretch.
    assert "A 11:13\\nB 5:3" in pair_file.read_text()
