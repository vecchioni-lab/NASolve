"""Conservative, non-mutating assessment of PDB molecular-replacement models."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Collection

from .residue_aliases import LigandCodeError, known_ligand_codes


class ModelAssessmentError(RuntimeError):
    """Raised when a coordinate model is not usable as an MR input."""


@dataclass
class ModelAssessment:
    source: str
    sha256: str
    byte_size: int
    atom_count: int
    polymer_atom_count: int
    heteroatom_count: int
    polymer_residue_count: int
    modified_polymer_atom_count: int
    modified_polymer_residue_count: int
    hetero_residue_count: int
    nonpolymer_hetero_residue_count: int
    chains: list[str]
    polymer_residues_by_chain: dict[str, int]
    polymer_residue_ids_by_chain: dict[str, list[str]]
    duplicate_atom_identities: int
    missing_occupancies: int
    zero_occupancies: int
    minimum_occupancy: float | None
    maximum_occupancy: float | None
    malformed_coordinate_records: int
    heteroatoms_preserved: bool = False
    copied_model: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_pdb(
    path: Path,
    polymer_ligand_codes: Collection[str] | None = None,
) -> ModelAssessment:
    """Inspect coordinate identity, occupancies, residues, chains, and HETATMs."""
    source = path.expanduser().resolve()
    if not source.is_file():
        raise ModelAssessmentError(f"MR model does not exist: {source}")
    if source.suffix.casefold() != ".pdb":
        raise ModelAssessmentError("The current model-assessment layer accepts PDB files only")

    if polymer_ligand_codes is None:
        try:
            ligand_codes = known_ligand_codes()
        except LigandCodeError as exc:
            raise ModelAssessmentError(str(exc)) from exc
    else:
        ligand_codes = frozenset(str(code) for code in polymer_ligand_codes)

    atom_count = polymer_atoms = modified_polymer_atoms = heteroatoms = malformed = 0
    missing_occupancies = zero_occupancies = duplicates = 0
    occupancies: list[float] = []
    atom_identities: set[tuple[str, ...]] = set()
    polymer_residues: set[tuple[str, str, str]] = set()
    modified_polymer_residues: set[tuple[str, str, str]] = set()
    hetero_residues: set[tuple[str, str, str, str]] = set()
    nonpolymer_hetero_residues: set[tuple[str, str, str, str]] = set()
    chains: set[str] = set()

    try:
        lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise ModelAssessmentError(f"Could not read MR model {source}: {exc}") from exc
    for line in lines:
        record = line[0:6].strip().upper()
        if record not in {"ATOM", "HETATM"}:
            continue
        atom_count += 1
        if len(line) < 54:
            malformed += 1
            continue
        atom_name = line[12:16].strip()
        altloc = line[16:17].strip()
        residue_name = line[17:20].strip()
        chain = line[21:22].strip() or "_"
        residue_number = line[22:26].strip()
        insertion = line[26:27].strip()
        chains.add(chain)
        polymer_residue_key = (chain, residue_number, insertion)
        hetero_residue_key = (chain, residue_number, insertion, residue_name)
        identity = (record, chain, residue_number, insertion, residue_name, atom_name, altloc)
        if identity in atom_identities:
            duplicates += 1
        atom_identities.add(identity)
        if record == "ATOM":
            polymer_atoms += 1
            polymer_residues.add(polymer_residue_key)
        else:
            heteroatoms += 1
            hetero_residues.add(hetero_residue_key)
            if residue_name in ligand_codes:
                polymer_atoms += 1
                modified_polymer_atoms += 1
                polymer_residues.add(polymer_residue_key)
                modified_polymer_residues.add(polymer_residue_key)
            else:
                nonpolymer_hetero_residues.add(hetero_residue_key)

        occupancy_text = line[54:60].strip() if len(line) >= 60 else ""
        if not occupancy_text:
            missing_occupancies += 1
        else:
            try:
                occupancy = float(occupancy_text)
            except ValueError:
                missing_occupancies += 1
            else:
                occupancies.append(occupancy)
                if occupancy == 0:
                    zero_occupancies += 1

    if atom_count == 0:
        raise ModelAssessmentError(f"INVALID: {source.name} contains no ATOM or HETATM records")
    if polymer_atoms == 0:
        raise ModelAssessmentError(
            f"INVALID: {source.name} contains no recognized polymer residues"
        )

    residue_ids: dict[str, list[str]] = {}
    for chain, residue_number, insertion in polymer_residues:
        residue_ids.setdefault(chain, []).append(residue_number + insertion)
    for values in residue_ids.values():
        values.sort(key=lambda value: (int(value) if value.lstrip("-").isdigit() else 10**9, value))
    counts = {chain: len(values) for chain, values in residue_ids.items()}
    warnings: list[str] = []
    if malformed:
        warnings.append(f"{malformed} coordinate record(s) were too short to parse")
    if missing_occupancies:
        warnings.append(f"{missing_occupancies} atom(s) have missing or invalid occupancy")
    if zero_occupancies:
        warnings.append(f"{zero_occupancies} atom(s) have zero occupancy")
    if duplicates:
        warnings.append(f"{duplicates} duplicate atom identity/altloc record(s) were found")

    return ModelAssessment(
        source=str(source),
        sha256=file_sha256(source),
        byte_size=source.stat().st_size,
        atom_count=atom_count,
        polymer_atom_count=polymer_atoms,
        heteroatom_count=heteroatoms,
        polymer_residue_count=len(polymer_residues),
        modified_polymer_atom_count=modified_polymer_atoms,
        modified_polymer_residue_count=len(modified_polymer_residues),
        hetero_residue_count=len(hetero_residues),
        nonpolymer_hetero_residue_count=len(nonpolymer_hetero_residues),
        chains=sorted(residue_ids),
        polymer_residues_by_chain=dict(sorted(counts.items())),
        polymer_residue_ids_by_chain=dict(sorted(residue_ids.items())),
        duplicate_atom_identities=duplicates,
        missing_occupancies=missing_occupancies,
        zero_occupancies=zero_occupancies,
        minimum_occupancy=min(occupancies) if occupancies else None,
        maximum_occupancy=max(occupancies) if occupancies else None,
        malformed_coordinate_records=malformed,
        warnings=warnings,
    )


def copy_preserving_model(
    source: Path,
    destination: Path,
    assessment: ModelAssessment,
) -> ModelAssessment:
    """Copy the unmodified model and verify that every byte, including HETATMs, survived."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    copied_hash = file_sha256(destination)
    if copied_hash != assessment.sha256:
        raise ModelAssessmentError("Copied MR model checksum differs from the source")
    assessment.heteroatoms_preserved = True
    assessment.copied_model = str(destination.resolve())
    return assessment
