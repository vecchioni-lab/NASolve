"""Post-MR model preparation, restraint generation, and ReadySet execution."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import dist, sqrt
from pathlib import Path
from typing import Callable, Mapping

from .curated_ligands import (
    CURATED_LIGANDS,
    curated_dictionary,
    dictionary_ideal_bond_length,
    validate_curated_dictionary,
)
from .frame_postmr import frame_postmr_spec, restraint_data_directory
from .model_assessment import file_sha256


class PostMRPreparationError(RuntimeError):
    """Raised when a Phaser solution cannot be prepared safely."""


@dataclass(frozen=True)
class MutationAction:
    site: str
    before: str
    after: str
    method: str
    parent_code: str | None = None
    deposition_code: str | None = None


@dataclass(frozen=True)
class PostMRResult:
    status: str
    message: str
    run_directory: Path
    postmr_directory: Path
    report_path: Path
    model_path: Path
    readyset_log: Path
    restraint_paths: tuple[Path, ...]


_COOT_BASES = frozenset({"DA", "DC", "DG", "DT", "A", "C", "G", "U"})
_MIRRORED_CANONICAL_CODES = {
    "DA": "0DA", "DC": "0DC", "DG": "0DG", "DT": "0DT",
    "A": "0A", "C": "0C", "G": "0G", "U": "0U",
}
_CANONICAL_NUCLEOTIDE_CODES = frozenset({
    "DA", "DC", "DG", "DT", "DU", "A", "C", "G", "U",
    *_MIRRORED_CANONICAL_CODES.values(),
})
_DNA_SEQUENCE_CODES = {"A": "DA", "C": "DC", "G": "DG", "T": "DT"}
_RNA_SEQUENCE_CODES = {"A": "A", "C": "C", "G": "G", "U": "U"}
DEFAULT_ANOMALOUS_ELEMENTS = frozenset({"I", "BR", "SE"})
_REQUIRED_PARENT_ATOM_GROUPS = (
    frozenset({"P"}),
    frozenset({"OP1", "O1P"}),
    frozenset({"OP2", "O2P"}),
    frozenset({"O5'"}),
    frozenset({"C5'"}),
    frozenset({"C4'"}),
    frozenset({"O4'"}),
    frozenset({"C3'"}),
    frozenset({"O3'"}),
    frozenset({"C2'"}),
    frozenset({"C1'"}),
)


def _read_report(run_directory: Path) -> tuple[Path, dict[str, object]]:
    run = run_directory.expanduser().resolve()
    report_path = run if run.name == "report.json" else run / "report.json"
    run = report_path.parent
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PostMRPreparationError(f"Could not read AutoMR report {report_path}: {exc}") from exc
    if report.get("workflow") != "automr":
        raise PostMRPreparationError("PostMR requires a completed Phaser report")
    if report.get("stage") == "postmr" and report.get("status") == "POSTMR_READY":
        raise PostMRPreparationError(
            f"PostMR is already complete; refusing to overwrite {run / 'PostMR'}"
        )
    if report.get("stage") != "phaser":
        raise PostMRPreparationError("PostMR requires a completed Phaser report")
    return run, report


def _solution_model(run: Path, report: Mapping[str, object]) -> Path:
    execution = report.get("execution")
    if isinstance(execution, Mapping):
        phaser = execution.get("phaser")
        if isinstance(phaser, Mapping) and isinstance(phaser.get("solution_pdb"), str):
            candidate = Path(phaser["solution_pdb"]).expanduser()
            if candidate.is_file():
                return candidate.resolve()
    fallback = run / "Phaser" / "mr_solution.pdb"
    if fallback.is_file():
        return fallback.resolve()
    raise PostMRPreparationError("The Phaser solution PDB is missing")


def _site_parts(site: str) -> tuple[str, str]:
    if site.count(":") != 1:
        raise PostMRPreparationError(f"Invalid mutation site {site!r}")
    chain, resid = (part.strip() for part in site.split(":", 1))
    if not chain or not resid:
        raise PostMRPreparationError(f"Invalid mutation site {site!r}")
    return chain, resid


def _coordinate_records(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError as exc:
        raise PostMRPreparationError(f"Could not read coordinate model {path}: {exc}") from exc


def _record_identity(line: str) -> tuple[str, str, str] | None:
    if line[0:6].strip().upper() not in {"ATOM", "HETATM"} or len(line) < 27:
        return None
    chain = line[21:22].strip() or "_"
    resid = line[22:26].strip() + line[26:27].strip()
    residue = line[17:20].strip()
    return chain, resid, residue


def residue_name(path: Path, site: str) -> str:
    chain, resid = _site_parts(site)
    names = {
        identity[2]
        for line in _coordinate_records(path)
        if (identity := _record_identity(line)) is not None
        and identity[0] == chain
        and identity[1] == resid
    }
    if not names:
        raise PostMRPreparationError(f"Mutation target {site} is absent from {path.name}")
    if len(names) != 1:
        raise PostMRPreparationError(
            f"Mutation target {site} has multiple residue names: {', '.join(sorted(names))}"
        )
    return next(iter(names))


def _rewrite_codes(source: Path, destination: Path, code_map: Mapping[str, str]) -> None:
    output: list[str] = []
    for line in _coordinate_records(source):
        identity = _record_identity(line)
        if identity is not None and identity[2] in code_map:
            line = line[:17] + f"{code_map[identity[2]]:>3s}" + line[20:]
        output.append(line)
    destination.write_text("".join(output), encoding="utf-8")


def _chain_is_rna(model: Path, chain: str, residue_ids: set[str]) -> bool:
    atom_names = {
        line[12:16].strip()
        for line in _coordinate_records(model)
        if (identity := _record_identity(line)) is not None
        and identity[0] == chain
        and identity[1] in residue_ids
    }
    return "O2'" in atom_names


def _sequence_targets(
    report: Mapping[str, object],
    model: Path,
    sequences: Mapping[str, object],
) -> OrderedDict[str, str]:
    assessment = report.get("model_assessment")
    residue_ids_by_chain = (
        assessment.get("polymer_residue_ids_by_chain")
        if isinstance(assessment, Mapping) else None
    )
    if not isinstance(residue_ids_by_chain, Mapping):
        raise PostMRPreparationError(
            "Full-sequence mutation requires the frozen polymer-residue inventory"
        )
    targets: OrderedDict[str, str] = OrderedDict()
    for chain, sequence_value in sequences.items():
        if not isinstance(chain, str) or not isinstance(sequence_value, str):
            raise PostMRPreparationError("Malformed frozen sequence plan")
        residue_values = residue_ids_by_chain.get(chain)
        if not isinstance(residue_values, list) or not all(
            isinstance(value, str) for value in residue_values
        ):
            raise PostMRPreparationError(
                f"Sequence chain {chain!r} has no frozen residue inventory"
            )
        sequence = sequence_value.upper()
        if len(sequence) != len(residue_values):
            raise PostMRPreparationError(
                f"Sequence for chain {chain} has length {len(sequence)}, but the "
                f"frozen model inventory contains {len(residue_values)} residues"
            )
        is_rna = _chain_is_rna(model, chain, set(residue_values))
        mapping = _RNA_SEQUENCE_CODES if is_rna else _DNA_SEQUENCE_CODES
        incompatible = sorted(set(sequence) - set(mapping))
        if incompatible:
            polymer = "RNA" if is_rna else "DNA"
            raise PostMRPreparationError(
                f"Sequence for {polymer} chain {chain} contains incompatible symbol(s): "
                + ", ".join(incompatible)
            )
        for resid, symbol in zip(residue_values, sequence):
            targets[f"{chain}:{resid}"] = mapping[symbol]
    return targets


def _target_sites(
    report: Mapping[str, object],
    model: Path,
) -> OrderedDict[str, str]:
    plan = report.get("post_mr_plan")
    if not isinstance(plan, Mapping):
        raise PostMRPreparationError("Frozen report is missing its post-MR plan")
    sequences = plan.get("sequences")
    targets = (
        _sequence_targets(report, model, sequences)
        if isinstance(sequences, Mapping) and sequences
        else OrderedDict()
    )
    standard_pair = plan.get("standard_pair")
    if isinstance(standard_pair, Mapping):
        frame = report.get("frame")
        frame_name = frame.get("name") if isinstance(frame, Mapping) else None
        if not isinstance(frame_name, str):
            raise PostMRPreparationError("Standard PostMR run has no frame name")
        try:
            spec = frame_postmr_spec(frame_name)
        except KeyError as exc:
            raise PostMRPreparationError(str(exc)) from exc
        codes = standard_pair.get("ligand_codes")
        if (
            not isinstance(codes, list)
            or len(codes) != 2
            or not all(isinstance(code, str) for code in codes)
        ):
            raise PostMRPreparationError("Standard PostMR plan has no ordered ligand-code pair")
        requested = standard_pair.get("requested")
        requested_tokens = requested.split(":") if isinstance(requested, str) else []
        # Normalize only known historical aliases.  Official CCD 8RO has a
        # different sulfur-ring topology, so NASolve's 4-thiothymidine remains
        # the laboratory PDB-compatible component DE throughout refinement.
        if len(requested_tokens) == 2:
            codes = [
                (
                    "DE"
                    if token.strip() == "E" and code in {"DE", "8RO"}
                    else "DF"
                    if token.strip() == "F" and code in {"DF", "A1AAZ"}
                    else code
                )
                for token, code in zip(requested_tokens, codes)
            ]
        targets[spec.sites[0].text] = codes[0]
        targets[spec.sites[1].text] = codes[1]
    mutations = plan.get("mutations")
    if isinstance(mutations, Mapping):
        for site, request in mutations.items():
            if not isinstance(site, str) or not isinstance(request, Mapping):
                raise PostMRPreparationError("Malformed explicit mutation plan")
            code = request.get("ligand_code")
            if not isinstance(code, str):
                raise PostMRPreparationError(f"Mutation {site} has no ligand code")
            if request.get("requested") == "E" and code in {"DE", "8RO"}:
                code = "DE"
            elif request.get("requested") == "F" and code in {"DF", "A1AAZ"}:
                code = "DF"
            targets[site] = code
    inputs = report.get("inputs")
    if isinstance(inputs, Mapping) and inputs.get("mirror") is True:
        targets = OrderedDict(
            (site, _MIRRORED_CANONICAL_CODES.get(code, code))
            for site, code in targets.items()
        )
    return targets


def build_mutation_plan(report: Mapping[str, object], model: Path) -> tuple[MutationAction, ...]:
    actions: list[MutationAction] = []
    for site, target in _target_sites(report, model).items():
        current = residue_name(model, site)
        parent_code: str | None = None
        deposition_code: str | None = None
        if current == target:
            method = "none"
        elif target in _MIRRORED_CANONICAL_CODES.values():
            raise PostMRPreparationError(
                f"Mirrored mutation {site} {current}->{target} requires the guarded "
                "unmirror/Coot/remirror pathway, which is not configured yet"
            )
        elif target in CURATED_LIGANDS:
            ligand = CURATED_LIGANDS[target]
            if ligand.parent_code is None:
                raise PostMRPreparationError(
                    f"Curated mutation {site} {current}->{target} has no canonical parent"
                )
            method = "coot-parent-overlap"
            parent_code = ligand.parent_code
            deposition_code = ligand.deposition_code
        elif target in _COOT_BASES:
            method = "coot-mutate-base"
        else:
            raise PostMRPreparationError(
                f"Mutation {site} {current}->{target} needs a curated template or dictionary; "
                "automatic coordinate construction is not configured"
            )
        if target in CURATED_LIGANDS:
            deposition_code = CURATED_LIGANDS[target].deposition_code
        actions.append(
            MutationAction(
                site,
                current,
                target,
                method,
                parent_code=parent_code,
                deposition_code=deposition_code,
            )
        )
    return tuple(actions)


def _coot_script(
    input_model: Path,
    output_model: Path,
    actions: tuple[MutationAction, ...],
    dictionary_paths: Mapping[str, Path],
    parent_models: Mapping[str, Path],
) -> str:
    lines = [
        "import coot",
    ]
    for code, dictionary in dictionary_paths.items():
        lines.extend([
            f"dictionary_status = coot.read_cif_dictionary({json.dumps(str(dictionary))})",
            f"print('NASOLVE_DICTIONARY', {code!r}, dictionary_status)",
            "if not dictionary_status:",
            f"    raise RuntimeError('Coot could not load the {code} dictionary')",
        ])
    lines.extend([
        f"imol = coot.handle_read_draw_molecule({json.dumps(str(input_model))})",
        "if imol < 0:",
        "    raise RuntimeError('Coot could not read the PostMR model')",
    ])
    for action in actions:
        chain, resid = _site_parts(action.site)
        try:
            residue_number = int(resid)
        except ValueError as exc:
            raise PostMRPreparationError(
                f"Coot mutation currently requires an integer residue number: {action.site}"
            ) from exc
        if action.method == "coot-mutate-base":
            lines.extend([
                (
                    "status = coot.mutate_base("
                    f"imol, {chain!r}, {residue_number}, '', {action.after!r})"
                ),
                f"print('NASOLVE_COOT_MUTATE', {action.site!r}, status)",
                "if status != 1:",
                f"    raise RuntimeError('Coot mutation failed at {action.site}')",
            ])
            continue
        if action.method != "coot-parent-overlap" or action.parent_code is None:
            raise PostMRPreparationError(
                f"Unsupported Coot mutation method {action.method!r} at {action.site}"
            )
        if action.before != action.parent_code:
            lines.extend([
                (
                    "status = coot.mutate_base("
                    f"imol, {chain!r}, {residue_number}, '', {action.parent_code!r})"
                ),
                f"print('NASOLVE_PARENT_MUTATE', {action.site!r}, {action.parent_code!r}, status)",
                "if status != 1:",
                f"    raise RuntimeError('Coot parent mutation failed at {action.site}')",
            ])
        lines.extend([
            f"coot.write_pdb_file(imol, {json.dumps(str(parent_models[action.site]))})",
            f"ligand_imol = coot.get_monomer_from_dictionary({action.after!r}, 0)",
            f"print('NASOLVE_MONOMER', {action.after!r}, ligand_imol)",
            "if ligand_imol < 0:",
            f"    raise RuntimeError('Coot could not build {action.after} from its dictionary')",
            (
                "overlap_status = coot.overlap_ligands_py("
                f"ligand_imol, imol, {chain!r}, {residue_number})"
            ),
            f"print('NASOLVE_OVERLAP', {action.site!r}, overlap_status)",
            "if not overlap_status:",
            f"    raise RuntimeError('Coot overlap failed at {action.site}')",
            (
                "replacement_imol = coot.add_ligand_delete_residue_copy_molecule("
                f"ligand_imol, 'A', 1, imol, {chain!r}, {residue_number})"
            ),
            f"print('NASOLVE_REPLACEMENT', {action.site!r}, replacement_imol)",
            "if replacement_imol < 0:",
            f"    raise RuntimeError('Coot replacement failed at {action.site}')",
            "imol = replacement_imol",
            f"result_name = coot.residue_name(imol, {chain!r}, {residue_number}, '')",
            f"print('NASOLVE_RESULT', {action.site!r}, result_name)",
            f"if result_name != {action.after!r}:",
            f"    raise RuntimeError('Coot produced the wrong residue at {action.site}')",
        ])
    lines.extend([
        "removed_hydrogens = coot.delete_hydrogen_atoms(imol)",
        "print('NASOLVE_REMOVED_HYDROGENS', removed_hydrogens)",
        f"coot.write_pdb_file(imol, {json.dumps(str(output_model))})",
        "coot.coot_no_state_real_exit(0)",
        "",
    ])
    return "\n".join(lines)


def _run_coot(
    input_model: Path,
    output_model: Path,
    actions: tuple[MutationAction, ...],
    coot_executable: Path,
    coot_directory: Path,
    environment: Mapping[str, str] | None,
    dictionary_paths: Mapping[str, Path],
    parent_models: Mapping[str, Path],
) -> tuple[Path, Path]:
    script = coot_directory / "mutate.py"
    log = coot_directory / "coot.log"
    backups = coot_directory / "backups"
    backups.mkdir()
    script.write_text(
        _coot_script(
            input_model,
            output_model,
            actions,
            dictionary_paths,
            parent_models,
        ),
        encoding="utf-8",
    )
    env = dict(os.environ if environment is None else environment)
    env["COOT_BACKUP_DIR"] = str(backups)
    env["NASOLVE_COOT_INPUT"] = str(input_model)
    env["NASOLVE_COOT_OUTPUT"] = str(output_model)
    env["NASOLVE_COOT_PLAN"] = json.dumps([asdict(action) for action in actions])
    command = [
        str(coot_executable),
        "--no-graphics",
        "--no-state-script",
        "--no-startup-scripts",
        "--no-guano",
        "--script",
        str(script),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=coot_directory,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except OSError as exc:
        raise PostMRPreparationError(f"Could not launch Coot: {exc}") from exc
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode or not output_model.is_file():
        raise PostMRPreparationError(
            f"Coot mutation failed with status {completed.returncode}; inspect {log}"
        )
    return script, log


def _atom_identity(line: str) -> tuple[str, str, str, str] | None:
    identity = _record_identity(line)
    if identity is None or len(line) < 17:
        return None
    atom_name = line[12:16].strip()
    alternate = line[16:17].strip()
    return identity[0], identity[1], atom_name, alternate


def _canonical_atom_name(atom_name: str) -> str:
    return {"O1P": "OP1", "O2P": "OP2"}.get(atom_name, atom_name)


def _atom_element(line: str) -> str:
    return _atom_element_with_source(line)[0]


def _atom_element_with_source(line: str) -> tuple[str, str]:
    if len(line) >= 78 and line[76:78].strip():
        return line[76:78].strip().upper(), "pdb-element-column"
    letters = "".join(
        character for character in line[12:16] if character.isalpha()
    ).upper()
    for two_letter in ("BR", "SE"):
        if letters.startswith(two_letter):
            return two_letter, "atom-name-fallback"
    return letters[:1], "atom-name-fallback"


def _atom_coordinates(line: str) -> tuple[float, float, float]:
    try:
        return tuple(float(line[start:end]) for start, end in ((30, 38), (38, 46), (46, 54)))
    except ValueError as exc:
        raise PostMRPreparationError("Invalid coordinates in Coot PDB output") from exc


def scan_anomalous_candidates(
    path: Path,
    elements: frozenset[str] = DEFAULT_ANOMALOUS_ELEMENTS,
) -> list[dict[str, object]]:
    """Find configured anomalous elements within nucleotide-like residues."""
    normalized = frozenset(element.strip().upper() for element in elements)
    residues: dict[tuple[str, str, str], list[str]] = {}
    for line in _coordinate_records(path):
        identity = _record_identity(line)
        if identity is not None:
            residues.setdefault(identity, []).append(line)

    candidates: list[dict[str, object]] = []
    for (chain, resid, residue), lines in residues.items():
        atom_names = {
            atom[2]
            for line in lines
            if (atom := _atom_identity(line)) is not None
        }
        nucleotide_like = "C1'" in atom_names and bool(
            atom_names & {"C2'", "C3'", "O4'"}
        )
        if not nucleotide_like:
            continue
        for line in lines:
            atom = _atom_identity(line)
            if atom is None:
                continue
            element, source = _atom_element_with_source(line)
            if element not in normalized:
                continue
            candidates.append({
                "site": f"{chain}:{resid}",
                "residue": residue,
                "atom_name": atom[2],
                "alternate": atom[3] or None,
                "element": element,
                "element_source": source,
                "coordinates": [round(value, 3) for value in _atom_coordinates(line)],
            })
    return candidates


def _unique_named_atom(
    atoms: Mapping[tuple[str, str, str, str], str],
    chain: str,
    resid: str,
    atom_name: str,
    context: str,
) -> tuple[tuple[str, str, str, str], str]:
    matches = [
        (key, line)
        for key, line in atoms.items()
        if key[:3] == (chain, resid, atom_name)
    ]
    if len(matches) != 1:
        raise PostMRPreparationError(
            f"Expected one {atom_name} atom at {chain}:{resid} in {context}, "
            f"found {len(matches)}"
        )
    return matches[0]


def _restore_shared_parent_coordinates(
    raw_model: Path,
    output_model: Path,
    actions: tuple[MutationAction, ...],
    parent_models: Mapping[str, Path],
    dictionary_paths: Mapping[str, Path] | None = None,
) -> dict[str, object]:
    """Restore coordinates for atoms shared with each clean canonical parent."""
    modified = tuple(action for action in actions if action.method == "coot-parent-overlap")
    raw_records = _coordinate_records(raw_model)
    raw_atoms = {
        atom: line
        for line in raw_records
        if (atom := _atom_identity(line)) is not None
    }
    parent_atoms: dict[tuple[str, str, str, str], str] = {}
    parent_names: dict[str, set[str]] = {}
    for action in modified:
        parent_path = parent_models[action.site]
        if not parent_path.is_file():
            raise PostMRPreparationError(
                f"Coot did not write the canonical-parent snapshot for {action.site}"
            )
        chain, resid = _site_parts(action.site)
        names: set[str] = set()
        for line in _coordinate_records(parent_path):
            atom = _atom_identity(line)
            if atom is not None and atom[:2] == (chain, resid):
                parent_atoms[atom] = line
                names.add(atom[2])
        missing_parent = sorted(
            "/".join(sorted(group))
            for group in _REQUIRED_PARENT_ATOM_GROUPS
            if names.isdisjoint(group)
        )
        if missing_parent:
            raise PostMRPreparationError(
                f"Canonical parent at {action.site} is missing protected atom(s): "
                + ", ".join(missing_parent)
            )
        parent_names[action.site] = names

    parent_atoms_by_canonical_name: dict[
        tuple[str, str, str, str], str
    ] = {}
    for atom, line in parent_atoms.items():
        canonical_atom = (
            atom[0], atom[1], _canonical_atom_name(atom[2]), atom[3]
        )
        if canonical_atom in parent_atoms_by_canonical_name:
            raise PostMRPreparationError(
                f"Canonical parent has duplicate atom aliases at {atom[0]}:{atom[1]}: "
                f"{atom[2]}"
            )
        parent_atoms_by_canonical_name[canonical_atom] = line

    substitution_positions: dict[
        tuple[str, str, str, str],
        tuple[tuple[float, float, float], str],
    ] = {}
    substitution_reports: dict[str, list[dict[str, object]]] = {
        action.site: [] for action in modified
    }
    for action in modified:
        chain, resid = _site_parts(action.site)
        ligand = CURATED_LIGANDS[action.after]
        for substitution in ligand.atom_substitutions:
            _, parent_anchor = _unique_named_atom(
                parent_atoms,
                chain,
                resid,
                substitution.anchor_atom,
                "canonical parent",
            )
            _, parent_replaced = _unique_named_atom(
                parent_atoms,
                chain,
                resid,
                substitution.parent_atom,
                "canonical parent",
            )
            _, raw_anchor = _unique_named_atom(
                raw_atoms,
                chain,
                resid,
                substitution.anchor_atom,
                "raw Coot model",
            )
            target_key, raw_target = _unique_named_atom(
                raw_atoms,
                chain,
                resid,
                substitution.target_atom,
                "raw Coot model",
            )
            raw_bond_length = dist(
                _atom_coordinates(raw_anchor), _atom_coordinates(raw_target)
            )
            if not 0.5 <= raw_bond_length <= 3.0:
                raise PostMRPreparationError(
                    f"Implausible {substitution.anchor_atom}-{substitution.target_atom} "
                    f"distance {raw_bond_length:.3f} at {action.site}"
                )
            anchor_xyz = _atom_coordinates(parent_anchor)
            replaced_xyz = _atom_coordinates(parent_replaced)
            direction = tuple(b - a for a, b in zip(anchor_xyz, replaced_xyz))
            direction_length = sqrt(sum(value * value for value in direction))
            if direction_length < 0.5:
                raise PostMRPreparationError(
                    f"Invalid parent {substitution.anchor_atom}-{substitution.parent_atom} "
                    f"vector at {action.site}"
                )
            target_xyz = tuple(
                anchor + raw_bond_length * vector / direction_length
                for anchor, vector in zip(anchor_xyz, direction)
            )
            substitution_positions[target_key] = (target_xyz, parent_replaced)
            substitution_reports[action.site].append({
                "parent_atom": substitution.parent_atom,
                "target_atom": substitution.target_atom,
                "anchor_atom": substitution.anchor_atom,
                "bond_length": round(raw_bond_length, 3),
                "placement": "canonical-parent-vector",
            })
        for substituent in ligand.ring_substituents:
            _, parent_anchor = _unique_named_atom(
                parent_atoms,
                chain,
                resid,
                substituent.anchor_atom,
                "canonical parent",
            )
            parent_neighbor_lines = [
                _unique_named_atom(
                    parent_atoms,
                    chain,
                    resid,
                    neighbor,
                    "canonical parent",
                )[1]
                for neighbor in substituent.ring_neighbors
            ]
            _, raw_anchor = _unique_named_atom(
                raw_atoms,
                chain,
                resid,
                substituent.anchor_atom,
                "raw Coot model",
            )
            target_key, raw_target = _unique_named_atom(
                raw_atoms,
                chain,
                resid,
                substituent.target_atom,
                "raw Coot model",
            )
            if dictionary_paths is None or action.after not in dictionary_paths:
                raise PostMRPreparationError(
                    f"Ideal-coordinate dictionary is required to place "
                    f"{substituent.target_atom} at {action.site}"
                )
            try:
                bond_length = dictionary_ideal_bond_length(
                    dictionary_paths[action.after],
                    substituent.anchor_atom,
                    substituent.target_atom,
                )
            except (OSError, ValueError) as exc:
                raise PostMRPreparationError(str(exc)) from exc
            if not (
                substituent.minimum_bond_length
                <= bond_length
                <= substituent.maximum_bond_length
            ):
                raise PostMRPreparationError(
                    f"Implausible ideal {substituent.anchor_atom}-"
                    f"{substituent.target_atom} distance {bond_length:.3f} "
                    f"at {action.site}"
                )
            anchor_xyz = _atom_coordinates(parent_anchor)
            neighbor_coordinates = [
                _atom_coordinates(line) for line in parent_neighbor_lines
            ]
            midpoint = tuple(
                sum(coordinate[axis] for coordinate in neighbor_coordinates) / 2.0
                for axis in range(3)
            )
            direction = tuple(
                anchor - center for anchor, center in zip(anchor_xyz, midpoint)
            )
            direction_length = sqrt(sum(value * value for value in direction))
            if direction_length < 0.5:
                names = "/".join(substituent.ring_neighbors)
                raise PostMRPreparationError(
                    f"Invalid parent {names}-{substituent.anchor_atom} ring geometry "
                    f"at {action.site}"
                )
            target_xyz = tuple(
                anchor + bond_length * vector / direction_length
                for anchor, vector in zip(anchor_xyz, direction)
            )
            substitution_positions[target_key] = (target_xyz, parent_anchor)
            substitution_reports[action.site].append({
                "target_atom": substituent.target_atom,
                "anchor_atom": substituent.anchor_atom,
                "ring_neighbors": list(substituent.ring_neighbors),
                "bond_length": round(bond_length, 3),
                "bond_length_source": "dictionary-ideal-coordinates",
                "placement": "canonical-ring-outward-bisector",
            })

    restored: dict[str, list[str]] = {action.site: [] for action in modified}
    output: list[str] = []
    for line in raw_records:
        atom = _atom_identity(line)
        if atom is not None and atom in substitution_positions:
            coordinates, parent_replaced = substitution_positions[atom]
            line = (
                line[:30]
                + "".join(f"{value:8.3f}" for value in coordinates)
                + parent_replaced[54:66]
                + line[66:]
            )
        elif atom is not None and (
            parent := parent_atoms_by_canonical_name.get((
                atom[0], atom[1], _canonical_atom_name(atom[2]), atom[3]
            ))
        ) is not None:
            if _atom_element(line) == _atom_element(parent):
                line = line[:30] + parent[30:66] + line[66:]
                site = f"{atom[0]}:{atom[1]}"
                restored[site].append(atom[2])
        output.append(line)

    for action in modified:
        restored_names = set(restored[action.site])
        missing_protected = sorted(
            "/".join(sorted(group))
            for group in _REQUIRED_PARENT_ATOM_GROUPS
            if restored_names.isdisjoint(group)
        )
        if missing_protected:
            raise PostMRPreparationError(
                f"Modified residue at {action.site} lost protected parent atom(s): "
                + ", ".join(missing_protected)
            )
    output_model.write_text("".join(output), encoding="utf-8")
    return {
        site: {
            "count": len(set(names)),
            "atoms": sorted(set(names)),
            "parent_atom_count": len(parent_names[site]),
            "substitutions": substitution_reports[site],
        }
        for site, names in restored.items()
    }


def _restore_canonical_mutation_backbones(
    source_model: Path,
    mutated_model: Path,
    output_model: Path,
    actions: tuple[MutationAction, ...],
) -> dict[str, object]:
    """Keep the original sugar/phosphate while allowing Coot to replace bases."""
    canonical_actions = tuple(
        action for action in actions if action.method == "coot-mutate-base"
    )
    if not canonical_actions:
        shutil.copyfile(mutated_model, output_model)
        return {}
    protected_names = {
        _canonical_atom_name(name)
        for group in _REQUIRED_PARENT_ATOM_GROUPS
        for name in group
    }
    source_atoms = {
        (atom[0], atom[1], _canonical_atom_name(atom[2]), atom[3]): line
        for line in _coordinate_records(source_model)
        if (atom := _atom_identity(line)) is not None
    }
    mutated_records = _coordinate_records(mutated_model)
    mutated_atoms = {
        (atom[0], atom[1], _canonical_atom_name(atom[2]), atom[3]): line
        for line in mutated_records
        if (atom := _atom_identity(line)) is not None
    }
    replacements: dict[tuple[str, str, str, str], str] = {}
    reports: dict[str, object] = {}
    for action in canonical_actions:
        chain, resid = _site_parts(action.site)
        expected = {
            key: line
            for key, line in source_atoms.items()
            if key[:2] == (chain, resid) and key[2] in protected_names
        }
        if not expected:
            raise PostMRPreparationError(
                f"Canonical mutation at {action.site} has no protected backbone atoms"
            )
        missing = sorted(
            key[2] for key in expected if key not in mutated_atoms
        )
        if missing:
            raise PostMRPreparationError(
                f"Canonical mutation at {action.site} lost original backbone atom(s): "
                + ", ".join(missing)
            )
        restored: list[str] = []
        for key, source_line in expected.items():
            mutated_line = mutated_atoms[key]
            if _atom_element(source_line) != _atom_element(mutated_line):
                raise PostMRPreparationError(
                    f"Canonical mutation changed the element of {key[2]} at {action.site}"
                )
            replacements[key] = source_line
            restored.append(key[2])
        reports[action.site] = {
            "source": "pre-Coot input model",
            "count": len(set(restored)),
            "atoms": sorted(set(restored)),
        }
    output: list[str] = []
    for line in mutated_records:
        atom = _atom_identity(line)
        key = (
            atom[0], atom[1], _canonical_atom_name(atom[2]), atom[3]
        ) if atom is not None else None
        source_line = replacements.get(key) if key is not None else None
        if source_line is not None:
            line = line[:30] + source_line[30:66] + line[66:]
        output.append(line)
    output_model.write_text("".join(output), encoding="utf-8")
    return reports


def _patch_narestraints_records(
    records: list[dict[str, object]],
    required_codes: set[str],
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    """Apply reviewed, process-local corrections to NARestraints records."""
    patched = [dict(record) for record in records]
    corrections: list[dict[str, str]] = []
    correction_specs = (
        ("DF", "O2", "S1", frozenset({"S1", "S2"})),
        ("S6G", "C5", "C5", frozenset({"C5", "C5 "})),
    )
    for code, canonical_atom, expected, accepted in correction_specs:
        if code not in required_codes:
            continue
        matches = [
            record
            for record in patched
            if str(record.get("Ligand code")) == code
        ]
        if len(matches) != 1:
            raise PostMRPreparationError(
                f"NARestraints must contain exactly one {code} record, "
                f"found {len(matches)}"
            )
        record = matches[0]
        existing = str(record.get(canonical_atom))
        if existing not in accepted:
            choices = " or ".join(repr(value) for value in sorted(accepted))
            raise PostMRPreparationError(
                f"Unexpected NARestraints {code} mapping "
                f"{canonical_atom}->{existing!r}; expected {choices}"
            )
        if existing != expected:
            record[canonical_atom] = expected
            corrections.append({
                "ligand_code": code,
                "canonical_atom": canonical_atom,
                "before": existing,
                "after": expected,
                "scope": "process-local",
            })
    return patched, corrections


def _default_narestraints_builder(
    pdb: Path,
    pairs: Path,
    output: Path,
) -> list[dict[str, str]]:
    try:
        from restraints import builder
        from restraints.base_pairs import read_base_pair_file
        from restraints.residue_library import load_residue_records
    except ImportError as exc:
        raise PostMRPreparationError("NARestraints is not installed") from exc
    required_codes = {
        identity[2]
        for line in _coordinate_records(pdb)
        if (identity := _record_identity(line)) is not None
    }
    records, corrections = _patch_narestraints_records(
        load_residue_records(), required_codes
    )
    original_loader = builder.load_residue_records
    builder.load_residue_records = lambda: records
    try:
        builder.build_phil_from_pdb(
            pdb,
            read_base_pair_file(pairs),
            output,
            include_stacking=True,
        )
    finally:
        builder.load_residue_records = original_loader
    return corrections


def _modified_nucleotide_sites(path: Path) -> set[str]:
    residues: dict[tuple[str, str, str], set[str]] = {}
    for line in _coordinate_records(path):
        identity = _record_identity(line)
        atom = _atom_identity(line)
        if identity is not None and atom is not None:
            residues.setdefault(identity, set()).add(atom[2])
    return {
        f"{chain}:{resid}"
        for (chain, resid, residue), atom_names in residues.items()
        if residue not in _CANONICAL_NUCLEOTIDE_CODES
        and "C1'" in atom_names
        and bool(atom_names & {"C2'", "C3'", "O4'"})
    }


def _candidate_site(residue: object) -> str:
    chain = getattr(residue, "chain", None)
    resid = getattr(residue, "resid", None)
    if not isinstance(chain, str) or not isinstance(resid, str):
        raise PostMRPreparationError("NARestraints guesser returned a malformed residue")
    return f"{chain}:{resid}"


def _default_modified_pair_restraints_builder(
    prepared_pdb: Path,
    compatibility_pdb: Path,
    pair_output: Path,
    restraint_output: Path,
) -> dict[str, object]:
    try:
        from restraints import builder, guesser
        from restraints.base_pairs import read_base_pair_file
        from restraints.residue_library import load_residue_records
    except ImportError as exc:
        raise PostMRPreparationError("NARestraints is not installed") from exc
    modified_sites = _modified_nucleotide_sites(prepared_pdb)
    required_codes = {
        identity[2]
        for line in _coordinate_records(compatibility_pdb)
        if (identity := _record_identity(line)) is not None
    }
    records, corrections = _patch_narestraints_records(
        load_residue_records(), required_codes
    )
    original_builder_loader = builder.load_residue_records
    original_guesser_loader = guesser.load_residue_records
    builder.load_residue_records = lambda: records
    guesser.load_residue_records = lambda: records
    try:
        candidates, warnings = guesser.guess_pairs(
            compatibility_pdb,
            allow_noncanonical=True,
        )
        selected = [
            candidate
            for candidate in candidates
            if _candidate_site(candidate.first) in modified_sites
            or _candidate_site(candidate.second) in modified_sites
        ]
        guesser.write_guess(pair_output, selected)
        if selected:
            builder.build_phil_from_pdb(
                compatibility_pdb,
                read_base_pair_file(pair_output),
                restraint_output,
                include_stacking=False,
            )
    finally:
        builder.load_residue_records = original_builder_loader
        guesser.load_residue_records = original_guesser_loader
    return {
        "mode": "modified-pairs-only",
        "modified_sites": sorted(modified_sites),
        "allow_noncanonical_guessing": True,
        "include_stacking": False,
        "guesser_warnings": list(warnings),
        "guessed_pair_count": len(candidates),
        "retained_pair_count": len(selected),
        "retained_pairs": [
            {
                "first": _candidate_site(candidate.first),
                "second": _candidate_site(candidate.second),
                "recipe": str(candidate.recipe),
                "score": float(candidate.score),
                "noncanonical": bool(candidate.noncanonical),
            }
            for candidate in selected
        ],
        "compatibility_corrections": corrections,
    }


def _selection_site(text: str, base: str) -> str | None:
    match = re.search(
        rf"\b{re.escape(base)}\s*=\s*chain\s+['\"]?([^\s'\"]+)['\"]?"
        rf"\s+and\s+resid\s+([^\s}}]+)",
        text,
        re.I,
    )
    return f"{match.group(1)}:{match.group(2)}" if match else None


def _filter_scaffold_overlaps(
    source: Path,
    destination: Path,
    retained_pairs: list[Mapping[str, object]],
) -> dict[str, object]:
    """Remove project-EFF base-pair blocks superseded by generated PHIL pairs."""
    overlaps = {
        frozenset((str(pair["first"]), str(pair["second"])))
        for pair in retained_pairs
        if isinstance(pair.get("first"), str) and isinstance(pair.get("second"), str)
    }
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    removed: list[dict[str, str]] = []
    index = 0
    while index < len(lines):
        if not re.search(r"\bbase_pair\s*\{", lines[index]):
            output.append(lines[index])
            index += 1
            continue
        block: list[str] = []
        depth = 0
        started = False
        while index < len(lines):
            line = lines[index]
            block.append(line)
            depth += line.count("{") - line.count("}")
            started = started or "{" in line
            index += 1
            if started and depth == 0:
                break
        text = "".join(block)
        first = _selection_site(text, "base1")
        second = _selection_site(text, "base2")
        if first is not None and second is not None and frozenset((first, second)) in overlaps:
            removed.append({"first": first, "second": second})
        else:
            output.extend(block)
    destination.write_text("".join(output), encoding="utf-8")
    return {
        "source": str(source.resolve()),
        "output": str(destination.resolve()),
        "generated_phil_is_authoritative": True,
        "removed_overlap_count": len(removed),
        "removed_overlaps": removed,
    }


def _atom_counts(path: Path) -> tuple[int, int, int]:
    atoms = heteroatoms = hydrogens = 0
    for line in _coordinate_records(path):
        record = line[0:6].strip().upper()
        if record not in {"ATOM", "HETATM"}:
            continue
        atoms += 1
        heteroatoms += record == "HETATM"
        element = line[76:78].strip().upper() if len(line) >= 78 else ""
        atom_name = line[12:16].strip().upper()
        if element == "H" or (not element and atom_name.startswith("H")):
            hydrogens += 1
    return atoms, heteroatoms, hydrogens


def _run_readyset(
    model: Path,
    ready_set_executable: Path,
    readyset_directory: Path,
    ligand_cif: Path | None,
    environment: Mapping[str, str] | None,
) -> tuple[Path, Path, Path | None, list[str]]:
    command = [
        str(ready_set_executable),
        str(model),
        "ready_set.actions.hydrogens=False",
        "ready_set.actions.ligands=True",
        "ready_set.actions.optimise_ligand_geometry=False",
    ]
    if ligand_cif is not None:
        command.append(f"ready_set.input.cif_file_name={ligand_cif}")
    log = readyset_directory / "ready_set.log"
    try:
        completed = subprocess.run(
            command,
            cwd=readyset_directory,
            env=dict(environment) if environment is not None else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except OSError as exc:
        raise PostMRPreparationError(f"Could not launch ReadySet: {exc}") from exc
    log.write_text(completed.stdout, encoding="utf-8")
    updated = readyset_directory / f"{model.stem}.updated.pdb"
    generated_cif = readyset_directory / f"{model.stem}.ligands.cif"
    if completed.returncode or not updated.is_file():
        raise PostMRPreparationError(
            f"ReadySet failed with status {completed.returncode}; inspect {log}"
        )
    before = _atom_counts(model)
    after = _atom_counts(updated)
    if after[2]:
        raise PostMRPreparationError(
            f"ReadySet added {after[2]} hydrogen atom(s) despite hydrogens=False"
        )
    if after[:2] != before[:2]:
        raise PostMRPreparationError(
            "ReadySet changed the total or HETATM atom count unexpectedly"
        )
    return updated, log, generated_cif if generated_cif.is_file() else None, command


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_postmr(
    run_directory: Path,
    ready_set_executable: Path,
    *,
    coot_executable: Path | None = None,
    environment: Mapping[str, str] | None = None,
    allow_mr_review: bool = False,
    modified_pairs_only: bool = False,
    data_root: Path | None = None,
    narestraints_builder: Callable[[Path, Path, Path], object] | None = None,
    modified_pair_builder: Callable[[Path, Path, Path, Path], object] | None = None,
) -> PostMRResult:
    """Prepare a completed Phaser solution without modifying the MR outputs."""
    run, report = _read_report(run_directory)
    mr_status = report.get("status")
    if mr_status == "MR_REVIEW" and not allow_mr_review:
        raise PostMRPreparationError(
            "MR_REVIEW requires explicit --allow-mr-review before PostMR preparation"
        )
    if mr_status not in ({"MR_SUCCESS", "MR_REVIEW"} if allow_mr_review else {"MR_SUCCESS"}):
        raise PostMRPreparationError(f"PostMR requires an accepted Phaser result, not {mr_status}")
    source_model = _solution_model(run, report)
    postmr = run / "PostMR"
    try:
        postmr.mkdir()
    except FileExistsError as exc:
        raise PostMRPreparationError(
            f"PostMR directory already exists; refusing to overwrite {postmr}"
        ) from exc
    model_dir = postmr / "Model"
    coot_dir = postmr / "Coot"
    restraints_dir = postmr / "Restraints"
    readyset_dir = postmr / "ReadySet"
    for directory in (model_dir, coot_dir, restraints_dir, readyset_dir):
        directory.mkdir()

    original = model_dir / "mr_solution.pdb"
    shutil.copyfile(source_model, original)
    actions = build_mutation_plan(report, original)
    target_curated_codes = sorted({
        action.after for action in actions if action.after in CURATED_LIGANDS
    })
    curated_sources: dict[str, Path] = {}
    for code in target_curated_codes:
        try:
            dictionary = curated_dictionary(code, data_root).resolve()
            validate_curated_dictionary(code, dictionary)
        except (KeyError, FileNotFoundError, ValueError) as exc:
            raise PostMRPreparationError(str(exc)) from exc
        curated_sources[code] = dictionary

    coot_actions = tuple(
        action
        for action in actions
        if action.method in {"coot-mutate-base", "coot-parent-overlap"}
    )
    overlap_actions = tuple(
        action for action in coot_actions if action.method == "coot-parent-overlap"
    )
    canonical_actions = tuple(
        action for action in coot_actions if action.method == "coot-mutate-base"
    )
    coot_log: Path | None = None
    coordinate_restoration: dict[str, object] = {}
    after_coot = model_dir / "after_coot.pdb"
    if coot_actions:
        if coot_executable is None:
            sites = ", ".join(action.site for action in coot_actions)
            raise PostMRPreparationError(
                f"Coot is required for supported mutation site(s) {sites}"
            )
        raw_after_coot = model_dir / "after_coot_raw.pdb"
        parent_models = {
            action.site: coot_dir
            / f"parent_{action.site.replace(':', '_')}_{action.parent_code}.pdb"
            for action in overlap_actions
        }
        coot_dictionaries = {
            action.after: curated_sources[action.after] for action in overlap_actions
        }
        _, coot_log = _run_coot(
            original,
            raw_after_coot,
            coot_actions,
            coot_executable,
            coot_dir,
            environment,
            coot_dictionaries,
            parent_models,
        )
        geometry_after_coot = model_dir / "after_coot_geometry.pdb"
        if overlap_actions:
            coordinate_restoration = _restore_shared_parent_coordinates(
                raw_after_coot,
                geometry_after_coot,
                overlap_actions,
                parent_models,
                curated_sources,
            )
        else:
            shutil.copyfile(raw_after_coot, geometry_after_coot)
        if canonical_actions:
            canonical_restoration = _restore_canonical_mutation_backbones(
                original,
                geometry_after_coot,
                after_coot,
                canonical_actions,
            )
            coordinate_restoration.update(canonical_restoration)
        else:
            shutil.copyfile(geometry_after_coot, after_coot)
    else:
        shutil.copyfile(original, after_coot)

    prepared = model_dir / "prepared_model.pdb"
    shutil.copyfile(after_coot, prepared)
    for action in actions:
        if residue_name(prepared, action.site) != action.after:
            raise PostMRPreparationError(
                f"Prepared model does not contain {action.after} at {action.site}"
            )

    restraint_paths: list[Path] = []
    narestraints_report: dict[str, object] = {
        "mode": "none",
        "compatibility_corrections": [],
    }
    frame = report.get("frame")
    frame_name = frame.get("name") if isinstance(frame, Mapping) else None
    compatibility = restraints_dir / "narestraints_input.pdb"
    compatibility_codes = {
        code: ligand.narestraints_label for code, ligand in CURATED_LIGANDS.items()
    }
    if modified_pairs_only:
        _rewrite_codes(prepared, compatibility, compatibility_codes)
        pair_file = restraints_dir / "guessed_modified_pairs.txt"
        narestraints = restraints_dir / "narestraints_modified_pairs.phil"
        try:
            builder_result = (
                modified_pair_builder or _default_modified_pair_restraints_builder
            )(prepared, compatibility, pair_file, narestraints)
        except PostMRPreparationError:
            raise
        except Exception as exc:
            raise PostMRPreparationError(f"NARestraints pair guessing failed: {exc}") from exc
        if not isinstance(builder_result, Mapping):
            raise PostMRPreparationError(
                "Modified-pair NARestraints builder returned no structured report"
            )
        narestraints_report = dict(builder_result)
        narestraints_report.setdefault("mode", "modified-pairs-only")
        narestraints_report["pair_file"] = str(pair_file)
        narestraints_report["restraint_file"] = (
            str(narestraints) if narestraints.is_file() else None
        )
        retained_count = narestraints_report.get("retained_pair_count")
        if (
            not isinstance(retained_count, int)
            or isinstance(retained_count, bool)
            or retained_count < 0
        ):
            raise PostMRPreparationError(
                "Modified-pair NARestraints report has no valid retained-pair count"
            )
        if retained_count and not narestraints.is_file():
            raise PostMRPreparationError(
                "NARestraints retained modified pairs but did not create its expected output"
            )
        if narestraints.is_file():
            restraint_paths.append(narestraints)
        if isinstance(frame_name, str):
            try:
                spec = frame_postmr_spec(frame_name)
            except KeyError as exc:
                raise PostMRPreparationError(str(exc)) from exc
            secondary_source = restraint_data_directory(data_root) / spec.secondary_structure_file
            if not secondary_source.is_file():
                raise PostMRPreparationError(
                    f"Packaged restraint resources are missing for frame {frame_name}"
                )
            secondary = restraints_dir / spec.secondary_structure_file
            retained_pairs = narestraints_report.get("retained_pairs")
            if not isinstance(retained_pairs, list) or not all(
                isinstance(pair, Mapping) for pair in retained_pairs
            ):
                raise PostMRPreparationError(
                    "Modified-pair report has no structured retained-pair list"
                )
            overlay = _filter_scaffold_overlaps(
                secondary_source,
                secondary,
                retained_pairs,  # type: ignore[arg-type]
            )
            narestraints_report["project_scaffold"] = overlay
            restraint_paths.append(secondary)
    elif isinstance(frame_name, str):
        try:
            spec = frame_postmr_spec(frame_name)
        except KeyError as exc:
            raise PostMRPreparationError(str(exc)) from exc
        resource_dir = restraint_data_directory(data_root)
        pair_source = resource_dir / spec.pair_file
        secondary_source = resource_dir / spec.secondary_structure_file
        if not pair_source.is_file() or not secondary_source.is_file():
            raise PostMRPreparationError(
                f"Packaged restraint resources are missing for frame {frame_name}"
            )
        pair_file = restraints_dir / "Std_padd.txt"
        secondary = restraints_dir / spec.secondary_structure_file
        shutil.copyfile(pair_source, pair_file)
        shutil.copyfile(secondary_source, secondary)
        _rewrite_codes(prepared, compatibility, compatibility_codes)
        narestraints = restraints_dir / "narestraints_Std_padd.phil"
        try:
            builder_result = (narestraints_builder or _default_narestraints_builder)(
                compatibility, pair_file, narestraints
            )
        except PostMRPreparationError:
            raise
        except Exception as exc:
            raise PostMRPreparationError(f"NARestraints failed: {exc}") from exc
        if isinstance(builder_result, list) and all(
            isinstance(item, dict) for item in builder_result
        ):
            narestraints_report["compatibility_corrections"] = builder_result
        if not narestraints.is_file():
            raise PostMRPreparationError("NARestraints did not create its expected output")
        narestraints_report.update({
            "mode": "frame-template",
            "frame": frame_name,
            "pair_file": str(pair_file),
            "restraint_file": str(narestraints),
            "include_stacking": True,
            "secondary_structure_file": str(secondary),
        })
        restraint_paths.extend([narestraints, secondary])

    residue_codes = {
        identity[2]
        for line in _coordinate_records(prepared)
        if (identity := _record_identity(line)) is not None
    }
    curated_codes = sorted(residue_codes & set(CURATED_LIGANDS))
    copied_cifs: list[Path] = []
    for code in curated_codes:
        try:
            source = curated_sources.get(code) or curated_dictionary(code, data_root).resolve()
            validate_curated_dictionary(code, source)
        except (KeyError, FileNotFoundError, ValueError) as exc:
            raise PostMRPreparationError(str(exc)) from exc
        destination = restraints_dir / source.name
        shutil.copyfile(source, destination)
        copied_cifs.append(destination)
        restraint_paths.append(destination)
    readyset_cif: Path | None = None
    if copied_cifs:
        readyset_cif = restraints_dir / "curated_ligands.cif"
        readyset_cif.write_text(
            "\n".join(path.read_text(encoding="utf-8").rstrip() for path in copied_cifs) + "\n",
            encoding="utf-8",
        )

    updated, readyset_log, generated_cif, readyset_command = _run_readyset(
        prepared,
        ready_set_executable.expanduser().resolve(),
        readyset_dir,
        readyset_cif,
        environment,
    )
    final_model = model_dir / "readyset_model.pdb"
    shutil.copyfile(updated, final_model)
    for action in actions:
        if residue_name(final_model, action.site) != action.after:
            raise PostMRPreparationError(
                f"ReadySet output lost {action.after} at {action.site}"
            )
    anomalous_candidates = scan_anomalous_candidates(final_model)

    postmr_payload = {
        "status": "POSTMR_READY",
        "message": "Post-MR model, restraints, and ReadySet outputs are ready for refinement",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_model": str(source_model),
        "input_sha256": file_sha256(source_model),
        "mutation_actions": [asdict(action) for action in actions],
        "coot": {
            "ran": bool(coot_actions),
            "executable": str(coot_executable) if coot_executable else None,
            "log": str(coot_log) if coot_log else None,
            "shared_parent_coordinates_restored": coordinate_restoration,
        },
        "component_identity": {
            code: {
                "refinement_code": code,
                "deposition_code": CURATED_LIGANDS[code].deposition_code,
                "description": CURATED_LIGANDS[code].description,
            }
            for code in curated_codes
        },
        "restraints": [str(path) for path in restraint_paths],
        "narestraints": narestraints_report,
        "readyset": {
            "command": readyset_command,
            "hydrogens": False,
            "log": str(readyset_log),
            "updated_model": str(updated),
            "generated_ligand_cif": str(generated_cif) if generated_cif else None,
        },
        "anomalous": {
            "trigger_elements": sorted(DEFAULT_ANOMALOUS_ELEMENTS),
            "autosol_required": bool(anomalous_candidates),
            "candidates": anomalous_candidates,
        },
        "prepared_model": str(final_model),
        "prepared_sha256": file_sha256(final_model),
    }
    postmr_report = postmr / "report.json"
    _write_json(postmr_report, postmr_payload)
    (postmr / "postmr.log").write_text(
        "\n".join([
            "NASolve PostMR preparation",
            "Status: POSTMR_READY",
            f"Input model: {source_model}",
            *(
                f"Mutation: {action.site} {action.before}->{action.after} ({action.method})"
                for action in actions
            ),
            f"Coot executed: {'yes' if coot_actions else 'no'}",
            f"NARestraints mode: {narestraints_report['mode']}",
            "ReadySet hydrogens: False",
            f"Prepared model: {final_model}",
            "",
        ]),
        encoding="utf-8",
    )
    report["stage"] = "postmr"
    report["status"] = "POSTMR_READY"
    report["message"] = postmr_payload["message"]
    report["updated_utc"] = postmr_payload["created_utc"]
    report["postmr"] = postmr_payload
    _write_json(run / "report.json", report)
    return PostMRResult(
        status="POSTMR_READY",
        message=postmr_payload["message"],
        run_directory=run,
        postmr_directory=postmr,
        report_path=postmr_report,
        model_path=final_model,
        readyset_log=readyset_log,
        restraint_paths=tuple(restraint_paths),
    )


__all__ = [
    "DEFAULT_ANOMALOUS_ELEMENTS",
    "MutationAction",
    "PostMRPreparationError",
    "PostMRResult",
    "build_mutation_plan",
    "prepare_postmr",
    "residue_name",
    "scan_anomalous_candidates",
]
