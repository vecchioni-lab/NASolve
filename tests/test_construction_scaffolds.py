"""Temporary mutation hops are policy, not final-component inference."""

from copy import deepcopy
import sys
from types import ModuleType

import pytest

from nasolve.curated_ligands import CURATED_LIGANDS, ligand_definition, ligand_dictionary


HOPS = {"Z": "C", "P": "G", "D": "A", "B": "G", "S": "C",
        "I": "A", "X": "G", "K": "C", "unique": "C"}


def install_records(monkeypatch, records):
    package = ModuleType("restraints")
    library = ModuleType("restraints.residue_library")
    library.load_residue_records = lambda: records
    package.residue_library = library
    monkeypatch.setitem(sys.modules, "restraints", package)
    monkeypatch.setitem(sys.modules, "restraints.residue_library", library)


@pytest.mark.parametrize("sheet,base", HOPS.items())
@pytest.mark.parametrize("sugar,prefix", [("DNA", "D"), ("RNA", "")])
def test_explicit_sheet_hops_do_not_need_n9_or_family_inference(monkeypatch, sheet, base, sugar, prefix):
    record = {"Ligand code": "XYZ", "Name": "test component", "Sugar Type": sugar,
              "Source sheet": sheet, "Base Analog": sheet.upper()}
    before = deepcopy(record)
    install_records(monkeypatch, [record])
    result = ligand_definition("XYZ")
    assert result.parent_code == prefix + base
    assert result.code == result.deposition_code == result.narestraints_label == "XYZ"
    assert result.dictionary_filename == "XYZ.cif"
    assert record == before


@pytest.mark.parametrize("sheet,expected", [("Z", "DC"), ("P", "DG"), ("unique", "DC")])
def test_source_sheet_is_the_hop_authority_not_analog_or_atom_roles(monkeypatch, sheet, expected):
    install_records(monkeypatch, [{"Ligand code": "XYZ", "Sugar Type": "DNA",
        "Source sheet": sheet, "Base Analog": "A", "N9": "C99"}])
    assert ligand_definition("XYZ").parent_code == expected


@pytest.mark.parametrize("sheet,analog", [(None, None), ("future", "unknown"), ("", "")])
def test_unclassified_intermediate_defaults_to_cytosine(monkeypatch, sheet, analog):
    install_records(monkeypatch, [{"Ligand code": "XYZ", "Sugar Type": "DNA",
        "Source sheet": sheet, "Base Analog": analog}])
    assert ligand_definition("XYZ").parent_code == "DC"


@pytest.mark.parametrize("category,expected", [("Z", "DC"), ("P", "DG"), ("G", "DG"), ("T", "DT")])
def test_records_without_source_sheet_use_category_then_c_fallback(monkeypatch, category, expected):
    install_records(monkeypatch, [{"Ligand code": "XYZ", "Sugar Type": "DNA", "Base Analog": category}])
    assert ligand_definition("XYZ").parent_code == expected


@pytest.mark.parametrize("sheet,expected", [("adenine", "DA"), ("guanine", "DG"),
    ("cytosine", "DC"), ("thymine", "DT")])
def test_ordinary_sheet_routes_are_preserved(monkeypatch, sheet, expected):
    install_records(monkeypatch, [{"Ligand code": "XYZ", "Sugar Type": "DNA", "Source sheet": sheet}])
    assert ligand_definition("XYZ").parent_code == expected


def test_whitespace_case_and_rna_thymine_hop(monkeypatch):
    install_records(monkeypatch, [{"Ligand code": "XYZ", "Sugar Type": " rna ", "Source sheet": " thymine "}])
    assert ligand_definition("XYZ").parent_code == "U"


@pytest.mark.parametrize("sugar", [None, "", "PNA", "L-DNA"])
def test_unknown_sugar_is_not_reinterpreted_by_the_base_fallback(monkeypatch, sugar):
    install_records(monkeypatch, [{"Ligand code": "XYZ", "Sugar Type": sugar, "Source sheet": "Z"}])
    with pytest.raises(ValueError, match="Sugar Type"):
        ligand_definition("XYZ")


@pytest.mark.parametrize("records", [[], [{"Ligand code": "XYZ"}, {"Ligand code": "XYZ"}]])
def test_c_fallback_does_not_invent_a_missing_or_ambiguous_target(monkeypatch, records):
    install_records(monkeypatch, records)
    with pytest.raises(ValueError, match="Expected one NARestraints record"):
        ligand_definition("XYZ")


def test_curated_chemistry_routes_keep_precedence(monkeypatch):
    install_records(monkeypatch, [])
    expected = {"DE": "DT", "DF": "DT", "1AP": "DA", "S6G": "DG", "C38": "DC", "5IU": "DT"}
    for code, parent in expected.items():
        assert ligand_definition(code) is CURATED_LIGANDS[code]
        assert ligand_definition(code).parent_code == parent


def test_dz_hop_does_not_supply_a_missing_final_dictionary(monkeypatch, tmp_path):
    install_records(monkeypatch, [{"Ligand code": "DZ", "Sugar Type": "DNA", "Source sheet": "Z", "Base Analog": "Z"}])
    assert ligand_definition("DZ").parent_code == "DC"
    with pytest.raises(FileNotFoundError, match="Curated dictionary for DZ is missing"):
        ligand_dictionary("DZ", tmp_path)
