"""Check a returned wwPDB geometry table against the actual coordinate files."""
import gzip
import json

import pytest

from nasolve.cli import main

gemmi = pytest.importorskip("gemmi")


def write_block(path, categories):
    doc = gemmi.cif.Document()
    block = doc.add_new_block("test")
    for name, rows in categories.items():
        block.set_mmcif_category(name, {key: [row[key] for row in rows] for key in rows[0]})
    doc.write_file(str(path))
    return path


def coordinates(path, *, distance="1.600", entry="TEST", author="103", insertion=None,
                alternates=None, element="C", occupancy="1"):
    names = ("C3'", "C2'", "O3'")
    positions = (("0", "0"), (distance, "0"), ("0", "1.42"))
    atoms = []
    for index, (name, (x, y)) in enumerate(zip(names, positions)):
        atoms.append({
            "id": str(index + 1), "type_symbol": element if name == "C2'" else name[0],
            "label_atom_id": name, "label_alt_id": alternates[index] if alternates else False,
            "label_comp_id": "DT", "label_asym_id": "L", "label_seq_id": "2", "label_entity_id": "1",
            "auth_asym_id": "C", "auth_seq_id": author, "pdbx_PDB_ins_code": insertion,
            "pdbx_PDB_model_num": "1", "Cartn_x": x, "Cartn_y": y, "Cartn_z": "0.0",
            "occupancy": occupancy if name == "C2'" else "1",
        })
    return write_block(path, {
        "_entry.": [{"id": entry}],
        "_entity_poly.": [{"entity_id": "1", "type": "polydeoxyribonucleotide"}],
        "_struct_asym.": [{"id": "L", "entity_id": "1"}],
        "_atom_site.": atoms,
    })


def validation(path, *, entry="TEST", rows=True, alt=None, bond_count=None):
    instance = {
        "id": "14", "PDB_model_num": "1", "entity_id": "1", "label_asym_id": "L",
        "label_seq_id": "2", "label_comp_id": "DT", "auth_asym_id": "C", "auth_seq_id": "103",
        "PDB_ins_code": None, "label_alt_id": alt or False,
        "count_bond_outliers": str(int(rows)) if bond_count is None else str(bond_count),
        "count_angle_outliers": str(int(rows)),
    }
    categories = {"_pdbx_vrpt_summary.": [{"entry_id": entry}], "_pdbx_vrpt_model_instance.": [instance]}
    if rows:
        categories["_pdbx_vrpt_instance_intra_bond_outliers."] = [{
            "ordinal": "1", "instance_id": "14", "atom_1": "C3'", "atom_2": "C2'",
            "obs": "1.600", "mean": "1.500", "stdev": "0.015", "Z": "6.67",
        }]
        categories["_pdbx_vrpt_instance_intra_angle_outliers."] = [{
            "ordinal": "1", "instance_id": "14", "atom_1": "C2'", "atom_2": "C3'", "atom_3": "O3'",
            "obs": "90.00", "mean": "100.0", "stdev": "1.5", "Z": "-6.67",
        }]
    return write_block(path, categories)


def replace_category(path, name, columns):
    doc = gemmi.cif.read_file(str(path))
    doc.sole_block().set_mmcif_category(name, columns)
    doc.write_file(str(path))


def run(source, report, candidate=None, *, family="all", as_json=True):
    args = ["cif-doctor", "deposition-geometry", str(source), "--validation", str(report), "--family", family]
    if candidate:
        args.extend(["--candidate", str(candidate)])
    if as_json:
        args.append("--json")
    return main(args)


def test_remeasures_original_and_revision_on_the_reported_reference(tmp_path, capsys):
    original = coordinates(tmp_path / "source.cif")
    candidate = coordinates(tmp_path / "candidate.cif", distance="1.52")
    returned = validation(tmp_path / "return.cif")
    before = {p: p.read_bytes() for p in (original, candidate, returned)}
    assert run(original, returned, candidate) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "REMEASURED" and report["entry_id"] == "TEST"
    assert report["supported_terms"] == report["reproduced_terms"] == 2
    bond, angle = report["terms"]
    assert bond["instance"]["label_asym_id"] == "L" and bond["instance"]["auth_seq_id"] == "103"
    assert bond["reported_z"] == 6.67 and bond["source"]["measured"] == pytest.approx(1.6)
    assert bond["candidate"]["measured"] == pytest.approx(1.52)
    assert bond["candidate"]["in_report_widths"] == pytest.approx(4 / 3)
    assert angle["candidate"]["measured"] == pytest.approx(90)
    assert all(len(report[key]) == 64 for key in ("reference_sha256", "candidate_sha256", "validation_sha256"))
    assert run(original, returned, candidate, as_json=False) == 0
    assert "1.520" in capsys.readouterr().out
    assert all(p.read_bytes() == content for p, content in before.items())


@pytest.mark.parametrize("source_changes,candidate_changes,expected", [
    ({"distance": "1.610"}, {}, "SOURCE_MISMATCH"),
    ({"alternates": ["A", "B", "A"]}, {}, "SOURCE_UNMEASURED"),
    ({}, {"author": "110"}, "CANDIDATE_UNMEASURED"),
    ({}, {"insertion": "A"}, "CANDIDATE_UNMEASURED"),
    ({}, {"element": "N"}, "CANDIDATE_UNMEASURED"),
    ({}, {"occupancy": "0"}, "CANDIDATE_UNMEASURED"),
])
def test_mismatched_source_or_candidate_is_visible(tmp_path, capsys, source_changes, candidate_changes, expected):
    original = coordinates(tmp_path / "src.cif", **source_changes)
    candidate = coordinates(tmp_path / "new.cif", **candidate_changes)
    returned = validation(tmp_path / "vrpt.cif")
    assert run(original, returned, candidate) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "REVIEW"
    assert report["terms"][0]["status"] == expected and report["terms"][0]["candidate"] is None


def test_empty_reporting_and_inconsistent_counts_or_entry_are_distinct(tmp_path, capsys):
    original = coordinates(tmp_path / "src.cif")
    empty = validation(tmp_path / "empty.cif", rows=False)
    assert run(original, empty) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "NO_REPORTED_TERMS"
    different = validation(tmp_path / "different.cif", entry="DIFFERENT")
    assert run(original, different) == 1 and "entry" in capsys.readouterr().err.lower()
    truncated = validation(tmp_path / "truncated.cif", rows=False, bond_count=1)
    assert run(original, truncated) == 1 and "count" in capsys.readouterr().err.lower()


def test_explicit_alternate_can_use_shared_atoms_and_gzip_input(tmp_path, capsys):
    original = coordinates(tmp_path / "src.cif", alternates=["A", False, "A"])
    returned = validation(tmp_path / "vrpt.cif", alt="A")
    packed = tmp_path / "vrpt.cif.gz"
    packed.write_bytes(gzip.compress(returned.read_bytes()))
    assert run(original, packed) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["reproduced_terms"] == 2 and report["terms"][0]["instance"]["alt_id"] == "A"


def test_deposition_identifier_requires_an_explicit_consistent_mapping(tmp_path, capsys):
    original = coordinates(tmp_path / "3LNA.cif", entry="D_TEST")
    returned = validation(tmp_path / "report.cif")
    mapping = {"database_id": ["PDB", "WWPDB"], "database_code": ["TEST", "D_TEST"]}
    replace_category(original, "_database_2.", mapping)
    assert run(original, returned) == 0
    assert json.loads(capsys.readouterr().out)["reproduced_terms"] == 2
    mapping["database_code"][1] = "D_DIFFERENT"
    replace_category(original, "_database_2.", mapping)
    assert run(original, returned) == 1 and "entry" in capsys.readouterr().err.lower()


def test_source_disagreement_withholds_candidate_until_scope_is_explicit(tmp_path, capsys):
    original = coordinates(tmp_path / "source.cif")
    candidate = coordinates(tmp_path / "candidate.cif", distance="1.52")
    returned = validation(tmp_path / "report.cif")
    replace_category(returned, "_pdbx_vrpt_instance_mogul_bond_outliers.", {
        "ordinal": ["1"], "instance_id": ["14"], "atom_1": ["C3'"], "atom_2": ["C2'"],
        "obsval": ["1.63"], "mean": ["1.52"], "stdev": ["0.02"], "Zscore": ["5.5"],
    })
    assert run(original, returned, candidate) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["families"]["standard"]["source_reproduced"] == 2
    assert report["families"]["mogul"]["source_reproduced"] == 0
    assert all(term["candidate"] is None for term in report["terms"])
    assert run(original, returned, candidate, family="standard") == 0
    selected = json.loads(capsys.readouterr().out)
    assert selected["family"] == "standard" and selected["supported_terms"] == 2
    assert selected["families"]["standard"]["candidate_measured"] == 2
    assert all(term["candidate"] for term in selected["terms"])


@pytest.mark.parametrize("error", ["missing observation", "zero width", "duplicate reversed bond", "unknown instance"])
def test_incomplete_or_ambiguous_report_does_not_score_coordinates(tmp_path, capsys, error):
    source = coordinates(tmp_path / "source.cif")
    returned = validation(tmp_path / "report.cif")
    category = "_pdbx_vrpt_instance_intra_bond_outliers."
    columns = gemmi.cif.read_file(str(returned)).sole_block().get_mmcif_category(category)
    if error == "missing observation":
        columns["obs"] = [None]
    elif error == "zero width":
        columns["stdev"] = ["0"]
    elif error == "unknown instance":
        columns["instance_id"] = ["42"]
    else:
        columns = {k: v * 2 for k, v in columns.items()}
        columns["atom_1"][1], columns["atom_2"][1] = columns["atom_2"][0], columns["atom_1"][0]
    replace_category(returned, category, columns)
    assert run(source, returned) == 1
    assert capsys.readouterr().err
