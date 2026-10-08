"""Exact prepared-component conversions, independent of external programs."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from nasolve.component_normalization import (
    BASE_ELEMENTS, BACKBONE_ELEMENTS, POLICY, PREFERRED_COMPONENTS,
    normalize_model, preparation_targets, preferred_component, target_changes,
)


def atom(serial=1, name="C1'", code="1W5", element="C", chain="A", resid=12,
         alt="", insertion="", charge="", kind="HETATM"):
    return (f"{kind:<6}{serial:5d} {name:>4}{alt:1}{code:>3} {chain:1}{resid:4d}{insertion:1}   "
            f"{1.234:8.3f}{2.345:8.3f}{3.456:8.3f}{0.65:6.2f}{42.67:6.2f}"
            f"          {element:>2}{charge:>2}\n")


def model(tmp_path, text):
    path = tmp_path / "raw.pdb"
    path.write_text(text)
    return path


@pytest.mark.parametrize("source,target", list(PREFERRED_COMPONENTS.items()))
def test_full_identity_map_preserves_coordinates_and_original_bytes(tmp_path, source, target):
    elements = {**BACKBONE_ELEMENTS, **BASE_ELEMENTS[target]}
    raw = "CRYST1 preserved header\n" + "".join(
        atom(i, name, source, element, charge="2+")
        for i, (name, element) in enumerate(elements.items(), 1)) + "END\n"
    path = model(tmp_path, raw)
    output = tmp_path / "normalized.pdb"
    event = normalize_model(path, output, {"A:12": (source, target)})
    assert path.read_text() == raw
    before = [v for v in raw.splitlines() if v.startswith("HETATM")]
    after = [v for v in output.read_text().splitlines() if v.startswith("HETATM")]
    assert len(before) == len(after) == 23
    assert all(b[30:76] == a[30:76] for b, a in zip(before, after))
    assert all(a[17:20].strip() == target and not a[78:80].strip() for a in after)
    assert event["source_sha256"] == sha256(raw.encode()).hexdigest()
    assert event["output_sha256"] == sha256(output.read_bytes()).hexdigest()
    assert event["policy"] == POLICY
    assert event["mapped_xyz_occupancy_b_preserved"] is True
    assert event["conversions"][0]["unobserved_dictionary_heavy_atoms"] == []
    assert output.read_text().startswith("CRYST1 preserved header\n")


@pytest.mark.parametrize("code", ["DZ", "DP", "1AP", "DE", "DF", "8RO", "1W0", "5CM", "XXX"])
def test_no_other_identity_is_reclassified(code):
    assert preferred_component(code) == code


def test_target_mapping_preserves_raw_intent_and_explicit_other_targets(tmp_path):
    source = model(tmp_path, atom(code="1W5") + atom(2, code="1WA", chain="B", resid=4))
    targets = {"A:12": "DC", "C:2": "1WA"}
    before = deepcopy(targets)
    result = preparation_targets(targets, source)
    assert result == {"A:12": "DC", "C:2": "DP", "B:4": "DP"}
    assert targets == before
    assert target_changes(targets) == [{"site": "C:2", "requested_code": "1WA", "prepared_code": "DP"}]


@pytest.mark.parametrize("name,element", [("HN3", "H"), ("HO6", "H"), ("D6", "D"), ("H2'", "")])
def test_source_hydrogens_are_not_carried_into_different_target_state(tmp_path, name, element):
    raw = atom(code="1WA", charge="2+") + atom(2, name, "1WA", element) + "CONECT    1    2\nEND\n"
    source = model(tmp_path, raw)
    output = tmp_path / "prepared.pdb"
    audit = normalize_model(source, output, {"A:12": ("1WA", "DP")})
    assert len([v for v in output.read_text().splitlines() if v.startswith("HETATM")]) == 1
    assert "CONECT" not in output.read_text()
    assert len(audit["conversions"][0]["removed_hydrogens"]) == 1
    assert audit["conversions"][0]["cleared_formal_charge_count"] == 1
    assert source.read_text() == raw


@pytest.mark.parametrize("alias,expected", [("O1P", "OP1"), ("O2P", "OP2"), ("O3P", "OP3")])
def test_only_declared_phosphate_spelling_aliases_change_atom_names(tmp_path, alias, expected):
    source = model(tmp_path, atom(name=alias, element="O"))
    output = tmp_path / "prepared.pdb"
    normalize_model(source, output, {"A:12": ("1W5", "DZ")})
    assert output.read_text()[12:16].strip() == expected
    assert output.read_text()[30:76] == source.read_text()[30:76]


def test_alternates_and_insertion_codes_are_preserved(tmp_path):
    raw = atom(1, alt="A", insertion="B") + atom(2, alt="B", insertion="B")
    source = model(tmp_path, raw)
    output = tmp_path / "prepared.pdb"
    audit = normalize_model(source, output, {"A:12B": ("1W5", "DZ")})
    assert [line[16] for line in output.read_text().splitlines()] == ["A", "B"]
    assert all(line[26] == "B" for line in output.read_text().splitlines())
    assert audit["conversions"][0]["site"] == "A:12B"


def test_unrelated_atoms_and_external_connectivity_are_preserved(tmp_path):
    external = atom(3, name="P", code="DC", chain="B", resid=1, element="P")
    source = model(tmp_path, atom(1) + atom(2, name="C2'") + external +
                   "CONECT    1    2    3\nCONECT    3    1\nEND\n")
    output = tmp_path / "prepared.pdb"
    result = normalize_model(source, output, {"A:12": ("1W5", "DZ")})
    assert external in output.read_text()
    assert "CONECT    1    3\nCONECT    3    1\n" in output.read_text()
    assert result["removed_source_connectivity_references"] == 1


def test_companion_tensor_and_ter_are_not_left_under_source_name(tmp_path):
    text = atom() + atom(kind="ANISOU") + "TER       2      1W5 A  12 \nEND\n"
    source = model(tmp_path, text)
    output = tmp_path / "prepared.pdb"
    normalize_model(source, output, {"A:12": ("1W5", "DZ")})
    assert "1W5" not in output.read_text()
    assert "ANISOU" in output.read_text() and "TER" in output.read_text()


@pytest.mark.parametrize("text,conversions,message", [
    (atom(name="MYST", element="C"), {"A:12": ("1W5", "DZ")}, "mapping"),
    (atom(name="C1", element="N"), {"A:12": ("1W5", "DZ")}, "expected"),
    (atom() + atom(2), {"A:12": ("1W5", "DZ")}, "Duplicate"),
    (atom(name="O1P", element="O") + atom(2, name="OP1", element="O"), {"A:12": ("1W5", "DZ")}, "collide"),
    (atom(), {"A:12": ("1W5", "DP")}, "Unreviewed"),
    (atom(), {"B:4": ("1WA", "DP")}, "No mapped"),
    (atom() + atom(2, name="C2'", code="DZ"), {"A:12": ("1W5", "DZ")}, "Mixed"),
    ("MODEL        1\n" + atom() + "ENDMDL\nMODEL        2\nENDMDL\n", {"A:12": ("1W5", "DZ")}, "one coordinate"),
])
def test_unsupported_identity_changes_stop_before_publishing_a_derivative(tmp_path, text, conversions, message):
    source = model(tmp_path, text)
    output = tmp_path / "prepared.pdb"
    with pytest.raises(ValueError, match=message):
        normalize_model(source, output, conversions)
    assert source.read_text() == text and not output.exists()


def test_existing_derivatives_and_originals_are_never_overwritten(tmp_path):
    source = model(tmp_path, atom())
    with pytest.raises(ValueError, match="new derivative"):
        normalize_model(source, source, {"A:12": ("1W5", "DZ")})
    output = tmp_path / "prepared.pdb"
    output.write_text("keep")
    with pytest.raises(ValueError, match="new derivative"):
        normalize_model(source, output, {"A:12": ("1W5", "DZ")})
    assert output.read_text() == "keep"


def test_missing_optional_terminal_atoms_are_reported_not_invented(tmp_path):
    source = model(tmp_path, atom())
    output = tmp_path / "prepared.pdb"
    result = normalize_model(source, output, {"A:12": ("1W5", "DZ")})
    assert "OP3" in result["conversions"][0]["unobserved_dictionary_heavy_atoms"]
    assert len(output.read_text().splitlines()) == 1
    assert result["structurally_approved"] is False


def test_empty_conversion_is_a_byte_identical_copy_including_metadata(tmp_path):
    raw = atom() + "MASTER kept as supplied\nSEQRES   1 A    1  1W5\nEND\n"
    source = model(tmp_path, raw)
    output = tmp_path / 'same.pdb'
    audit = normalize_model(source, output, {})
    assert source.read_bytes() == output.read_bytes()
    assert audit['conversions'] == []


def test_link_endpoints_relabel_without_moving_other_fields(tmp_path):
    chars=list(' '*80)
    for start,text in ((0,'LINK  '),(12," C1'"),(17,'1W5'),(21,'A'),(22,'  12'),
                       (42,' P  '),(47,' DC'),(51,'B'),(52,'   1')):
        chars[start:start+len(text)] = text
    link=''.join(chars)+'\n'
    source=model(tmp_path,atom()+atom(2,'P','DC','P',chain='B',resid=1)+link)
    output=tmp_path/'linked.pdb'
    normalize_model(source,output,{'A:12':('1W5','DZ')})
    result=next(line for line in output.read_text().splitlines() if line.startswith('LINK'))
    assert result[17:20].strip()=='DZ'
    assert result[47:50].strip()=='DC'
