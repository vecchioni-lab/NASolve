"""Fresh combined DNA staging must preserve donors and real end chemistry."""

from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from nasolve.automr_input import read_intent, resolve_automr_input
from nasolve.synthetic_dna import (
    ANNOTATED_SEQUENCES, CHAIN_IDS, FIVE_PRIME_SITES, PAIR_SITES,
    SyntheticDNAError, prepare_free_five_prime_model, stage_synthetic_dna,
    validate_synthetic_dna_inputs,
)


REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture
def sources(tmp_path):
    repo = tmp_path / "repository"
    for relative in ("MR_frames/5W6W/5W6W_noPO4.pdb", "MR_frames/5W6W/C_G.pdb",
                     "docs/recipes/synthetic-dna-combined.toml"):
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY / relative, destination)
    donor = tmp_path / "donor"
    donor.mkdir()
    # This is a staging fixture only, deliberately not valid diffraction data.
    (donor / "staraniso_alldata-unique.mtz").write_bytes(b"MTZ staging-signature-fixture")
    (donor / "Data_1_autoPROC_STARANISO_all.cif").write_text("data_test\n")
    (donor / "summary.html").write_text("<html>donor fixture</html>\n")
    return repo, donor, tmp_path / "outputs"


def _coordinates(data):
    return {int(line[6:11]): line for line in data.decode().splitlines(keepends=True)
            if line.startswith(("ATOM  ", "HETATM"))}


def test_actual_w_fixture_becomes_free_five_prime_without_changing_other_coordinates():
    original = (REPOSITORY / "MR_frames/5W6W/5W6W_noPO4.pdb").read_bytes()
    prepared, deleted = prepare_free_five_prime_model(original)
    assert {(row["site"], row["atom"]) for row in deleted} == {
        (site, atom) for site in ("B:1", "C:8") for atom in ("P", "OP1", "OP2")
    }
    before = _coordinates(original)
    after = _coordinates(prepared)
    removed = {row["serial"] for row in deleted}
    assert after == {serial: row for serial, row in before.items() if serial not in removed}
    assert len(after) == len(before) - 6
    for line in prepared.decode().splitlines():
        if line.startswith("CONECT"):
            refs = {int(line[i:i + 5]) for i in range(6, len(line), 5) if line[i:i + 5].strip()}
            assert not refs & removed
    assert all(row["site"] in FIVE_PRIME_SITES for row in deleted)


def test_full_combined_targets_and_explicit_end_and_autosol_policy(sources):
    repo, donor, output = sources
    preserved = {path: path.read_bytes() for path in (*donor.iterdir(), repo / "MR_frames/5W6W/5W6W_noPO4.pdb")}
    staged = stage_synthetic_dna(repo, donor, output)
    root = Path(staged["root"])
    assert staged["synthetic"] is True
    assert staged["target_count"] == 42
    assert staged["native_tools"] == "NOT_RUN"
    assert staged["validation"]["autosol"] == "DISABLED"
    assert staged["chemistry"]["terminal_phosphate_sites"] == []
    targets = {row["site"]: row["residue_code"] for row in staged["target_sites"]}
    for pair in PAIR_SITES:
        assert [targets[site] for site in pair["sites"]] == pair["codes"]
    assert targets["C:10"] == "IMC"
    assert "S6G" not in targets.values()
    assert targets["A:13"] == "DT" and targets["B:3"] == "DA"
    assert {chain: sum(site.startswith(chain + ":") for site in targets) for chain in CHAIN_IDS} == {
        "A": 21, "B": 7, "C": 7, "D": 7,
    }
    configuration = (root / "dataset/nasolve.txt").read_text()
    assert "five_prime_phosphate_sites =\n" in configuration
    assert "force =" not in configuration
    for chain, sequence in ANNOTATED_SEQUENCES.items():
        assert f"{chain} = {sequence}\n" in configuration
    assert all(path.read_bytes() == content for path, content in preserved.items())
    disk = json.loads((root / "synthetic-inputs.json").read_text())
    assert "root" not in disk and "dataset" not in disk
    assert all(item["anchor"] == "output" for item in disk["artifacts"].values())
    assert (root / "dataset/staraniso_alldata-unique.mtz").read_bytes() == preserved[donor / "staraniso_alldata-unique.mtz"]


def test_configuration_uses_normal_input_resolver_without_implicit_d1_phosphate(sources):
    repo, donor, output = sources
    staged = stage_synthetic_dna(repo, donor, output)
    dataset = Path(staged["dataset"])
    intent = read_intent(dataset / "nasolve.txt")
    assert intent.op3_sites_explicit is True
    assert intent.allow_op3_sites == ()
    resolved = resolve_automr_input(dataset, intent, frames_dir=repo / "MR_frames")
    assert resolved.allow_op3_sites == ()
    assert resolved.phosphate_intent["source"] == "dataset"
    assert resolved.model.name == "synthetic_search_W_free5OH.pdb"
    assert resolved.sequences == ANNOTATED_SEQUENCES


def test_staging_and_validation_survive_original_source_removal_and_relocation(sources, tmp_path):
    repo, donor, output = sources
    staged = stage_synthetic_dna(repo, donor, output)
    relocated = tmp_path / "relocated-attempt"
    shutil.move(staged["root"], relocated)
    shutil.rmtree(repo)
    shutil.rmtree(donor)
    result = validate_synthetic_dna_inputs(relocated)
    assert result["target_count"] == 42
    assert result["native_tools"] == "NOT_RUN"


def test_missing_required_metadata_fails_without_basename_discovery(sources):
    repo, donor, output = sources
    (donor / "Data_1_autoPROC_STARANISO_all.cif").unlink()
    (donor / "summary.html").unlink()
    hidden = donor / "unrelated"
    hidden.mkdir()
    (hidden / "summary.html").write_text("must not discover")
    with pytest.raises(SyntheticDNAError, match="Missing/unreadable donor STARANISO CIF"):
        stage_synthetic_dna(repo, donor, output)
    assert not output.exists()


@pytest.mark.parametrize("bad_path", ["../other.mtz", "/absolute.mtz"])
def test_rejects_escaped_declared_donor_paths_before_output_allocation(sources, bad_path):
    repo, donor, output = sources
    with pytest.raises(SyntheticDNAError, match="declared relative path"):
        stage_synthetic_dna(repo, donor, output, mtz_relative_path=bad_path)
    assert not output.exists()


def test_rejects_invalid_mtz_missing_model_or_unsafe_output_before_allocating(sources):
    repo, donor, output = sources
    with pytest.raises(SyntheticDNAError, match="outside"):
        stage_synthetic_dna(repo, donor, repo / "new-run")
    (donor / "staraniso_alldata-unique.mtz").write_bytes(b"not MTZ")
    with pytest.raises(SyntheticDNAError, match="MTZ file signature"):
        stage_synthetic_dna(repo, donor, output)
    assert not output.exists()
    (donor / "staraniso_alldata-unique.mtz").write_bytes(b"MTZ staging-fixture")
    (repo / "MR_frames/5W6W/5W6W_noPO4.pdb").unlink()
    with pytest.raises(SyntheticDNAError, match="Missing/unreadable"):
        stage_synthetic_dna(repo, donor, output)
    assert not output.exists()


def test_rerun_allocates_new_attempt_and_hash_gate_rejects_mutation(sources):
    repo, donor, output = sources
    first = stage_synthetic_dna(repo, donor, output)
    second = stage_synthetic_dna(repo, donor, output)
    assert first["root"] != second["root"]
    root = Path(first["root"])
    mtz = root / "dataset/staraniso_alldata-unique.mtz"
    mtz.write_bytes(mtz.read_bytes() + b"altered")
    with pytest.raises(SyntheticDNAError, match="checksum mismatch"):
        validate_synthetic_dna_inputs(root)
    assert validate_synthetic_dna_inputs(Path(second["root"]))["status"] == "STAGED_INPUTS_VALIDATED"


def test_validation_rejects_forged_target_receipt_even_with_unchanged_files(sources):
    staged = stage_synthetic_dna(*sources)
    root = Path(staged["root"])
    path = root / "synthetic-inputs.json"
    receipt = json.loads(path.read_text())
    forged = deepcopy(receipt)
    next(row for row in forged["target_sites"] if row["site"] == "C:10")["residue_code"] = "S6G"
    path.write_text(json.dumps(forged))
    with pytest.raises(SyntheticDNAError, match="reviewed combined DNA recipe"):
        validate_synthetic_dna_inputs(root)


def test_input_model_ambiguity_and_ribose_are_rejected():
    original = (REPOSITORY / "MR_frames/5W6W/5W6W_noPO4.pdb").read_bytes()
    atom = next(row for row in original.splitlines(keepends=True) if row.startswith(b"ATOM  "))
    with pytest.raises(SyntheticDNAError, match="Ambiguous"):
        prepare_free_five_prime_model(original + atom)
    sugar = next(row for row in original.splitlines(keepends=True)
                 if row.startswith(b"ATOM  ") and row[12:16].strip() == b"C2'")
    ribose = original.replace(sugar, sugar[:12] + b" O2'" + sugar[16:], 1)
    with pytest.raises(SyntheticDNAError, match="complete DNA sugar"):
        prepare_free_five_prime_model(ribose)
