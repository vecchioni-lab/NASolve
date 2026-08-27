"""Curated and compatibility residues used during guarded model preparation.

These entries are deliberately small and explicit.  NASolve does not run
eLBOW for every residue: a reviewed dictionary is bundled once and copied
into each run that needs it.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AtomSubstitution:
    parent_atom: str
    target_atom: str
    anchor_atom: str


@dataclass(frozen=True)
class CuratedLigand:
    code: str
    dictionary_filename: str
    accepted_model_labels: tuple[str, ...]
    narestraints_label: str
    description: str
    parent_code: str | None = None
    deposition_code: str | None = None
    required_bonds: tuple[tuple[str, str], ...] = ()
    forbidden_bonds: tuple[tuple[str, str], ...] = ()
    atom_substitutions: tuple[AtomSubstitution, ...] = ()


CURATED_LIGANDS: dict[str, CuratedLigand] = {
    "DE": CuratedLigand(
        code="DE",
        dictionary_filename="DE.cif",
        accepted_model_labels=("DE",),
        narestraints_label="DE",
        description="4-thiothymidine under the laboratory PDB-compatible label DE",
        parent_code="DT",
        required_bonds=(("C4", "S4"),),
        forbidden_bonds=(("N3", "S4"),),
        atom_substitutions=(AtomSubstitution("O4", "S4", "C4"),),
    ),
    "DF": CuratedLigand(
        code="DF",
        dictionary_filename="DF.cif",
        accepted_model_labels=("DF",),
        narestraints_label="DF",
        description="2-thiothymidine under the laboratory PDB-compatible label DF",
        parent_code="DT",
        deposition_code="A1AAZ",
        required_bonds=(("C2", "S1"),),
        forbidden_bonds=(("N3", "S1"),),
        atom_substitutions=(AtomSubstitution("O2", "S1", "C2"),),
    ),
    "1AP": CuratedLigand(
        code="1AP",
        dictionary_filename="1AP.cif",
        accepted_model_labels=("1AP",),
        narestraints_label="1AP",
        description="2,6-diaminopurine nucleotide",
        parent_code="DA",
        deposition_code="1AP",
    ),
    "S6G": CuratedLigand(
        code="S6G",
        dictionary_filename="S6G.cif",
        accepted_model_labels=("S6G",),
        narestraints_label="S6G",
        description="6-thio-2'-deoxyguanosine-5'-monophosphate",
        parent_code="DG",
        deposition_code="S6G",
        required_bonds=(("C6", "S6"),),
        forbidden_bonds=(("N1", "S6"),),
        atom_substitutions=(AtomSubstitution("O6", "S6", "C6"),),
    ),
}

CURATED_LIGAND_CODES = frozenset(CURATED_LIGANDS)


def ligand_data_directory(data_root: Path | None = None) -> Path:
    if data_root is not None:
        return Path(data_root) / "ligands"
    return Path(__file__).resolve().parent / "data" / "ligands"


def curated_dictionary(code: str, data_root: Path | None = None) -> Path:
    try:
        ligand = CURATED_LIGANDS[code]
    except KeyError as exc:
        raise KeyError(f"No curated NASolve ligand is registered for {code}") from exc
    path = ligand_data_directory(data_root) / ligand.dictionary_filename
    if not path.is_file():
        raise FileNotFoundError(
            f"Curated dictionary for {code} is missing: {path}"
        )
    return path


def _dictionary_bonds(path: Path) -> set[frozenset[str]]:
    """Read the atom pairs from a CIF ``_chem_comp_bond`` loop."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "loop_":
            continue
        headers: list[str] = []
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].lstrip().startswith("_"):
            headers.append(lines[cursor].strip())
            cursor += 1
        atom_1 = "_chem_comp_bond.atom_id_1"
        atom_2 = "_chem_comp_bond.atom_id_2"
        if atom_1 not in headers or atom_2 not in headers:
            continue
        first_index = headers.index(atom_1)
        second_index = headers.index(atom_2)
        bonds: set[frozenset[str]] = set()
        while cursor < len(lines):
            row = lines[cursor].strip()
            if not row or row == "#" or row == "loop_" or row.startswith("data_"):
                break
            if row.startswith("_"):
                break
            # ``posix=False`` preserves unquoted prime atom names such as
            # O5', which occur in older eLBOW dictionaries.
            fields = shlex.split(row, comments=True, posix=False)
            if len(fields) > max(first_index, second_index):
                atoms = []
                for field_index in (first_index, second_index):
                    atom = fields[field_index]
                    if (
                        len(atom) >= 2
                        and atom[0] == atom[-1]
                        and atom[0] in {"'", '"'}
                    ):
                        atom = atom[1:-1]
                    atoms.append(atom)
                bonds.add(frozenset(atoms))
            cursor += 1
        return bonds
    raise ValueError(f"Dictionary has no _chem_comp_bond loop: {path}")


def validate_curated_dictionary(code: str, path: Path) -> None:
    """Reject a packaged dictionary whose reviewed local topology changed."""
    try:
        ligand = CURATED_LIGANDS[code]
    except KeyError as exc:
        raise KeyError(f"No curated NASolve ligand is registered for {code}") from exc
    bonds = _dictionary_bonds(path)
    missing = [pair for pair in ligand.required_bonds if frozenset(pair) not in bonds]
    forbidden = [pair for pair in ligand.forbidden_bonds if frozenset(pair) in bonds]
    if missing or forbidden:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join("-".join(pair) for pair in missing))
        if forbidden:
            details.append("forbidden " + ", ".join("-".join(pair) for pair in forbidden))
        raise ValueError(
            f"Curated dictionary {code} failed topology validation: {'; '.join(details)}"
        )


__all__ = [
    "CURATED_LIGAND_CODES",
    "CURATED_LIGANDS",
    "AtomSubstitution",
    "CuratedLigand",
    "curated_dictionary",
    "ligand_data_directory",
    "validate_curated_dictionary",
]
