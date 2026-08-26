"""Post-MR model preparation, restraint generation, and ReadySet execution."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from .curated_ligands import CURATED_LIGANDS, curated_dictionary
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


def _read_report(run_directory: Path) -> tuple[Path, dict[str, object]]:
    run = run_directory.expanduser().resolve()
    report_path = run if run.name == "report.json" else run / "report.json"
    run = report_path.parent
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PostMRPreparationError(f"Could not read AutoMR report {report_path}: {exc}") from exc
    if report.get("workflow") != "automr" or report.get("stage") != "phaser":
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


def _rewrite_sites(source: Path, destination: Path, replacements: Mapping[str, str]) -> None:
    keyed = {_site_parts(site): code for site, code in replacements.items()}
    changed = {site: 0 for site in replacements}
    output: list[str] = []
    for line in _coordinate_records(source):
        identity = _record_identity(line)
        if identity is not None:
            key = (identity[0], identity[1])
            if key in keyed:
                site = f"{key[0]}:{key[1]}"
                line = line[:17] + f"{keyed[key]:>3s}" + line[20:]
                changed[site] += 1
        output.append(line)
    missing = [site for site, count in changed.items() if count == 0]
    if missing:
        raise PostMRPreparationError(
            "Could not rewrite absent site(s): " + ", ".join(missing)
        )
    destination.write_text("".join(output), encoding="utf-8")


def _rewrite_codes(source: Path, destination: Path, code_map: Mapping[str, str]) -> None:
    output: list[str] = []
    for line in _coordinate_records(source):
        identity = _record_identity(line)
        if identity is not None and identity[2] in code_map:
            line = line[:17] + f"{code_map[identity[2]]:>3s}" + line[20:]
        output.append(line)
    destination.write_text("".join(output), encoding="utf-8")


def _target_sites(report: Mapping[str, object]) -> OrderedDict[str, str]:
    plan = report.get("post_mr_plan")
    if not isinstance(plan, Mapping):
        raise PostMRPreparationError("Frozen report is missing its post-MR plan")
    sequences = plan.get("sequences")
    if isinstance(sequences, Mapping) and sequences:
        raise PostMRPreparationError(
            "Full-sequence mutation is not enabled yet; use explicit [mutations] sites"
        )
    targets: OrderedDict[str, str] = OrderedDict()
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
        if not isinstance(codes, list) or len(codes) != 2 or not all(isinstance(code, str) for code in codes):
            raise PostMRPreparationError("Standard PostMR plan has no ordered ligand-code pair")
        requested = standard_pair.get("requested")
        requested_tokens = requested.split(":") if isinstance(requested, str) else []
        # Runs frozen before the 8RO correction recorded E as the compatibility
        # label DE. Migrate only that known legacy combination; all other
        # frozen ligand codes remain authoritative.
        if len(requested_tokens) == 2:
            codes = [
                "8RO" if token.strip() == "E" and code == "DE" else code
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
            if request.get("requested") == "E" and code == "DE":
                code = "8RO"
            targets[site] = code
    return targets


def build_mutation_plan(report: Mapping[str, object], model: Path) -> tuple[MutationAction, ...]:
    actions: list[MutationAction] = []
    for site, target in _target_sites(report).items():
        current = residue_name(model, site)
        if current == target:
            method = "none"
        elif target in CURATED_LIGANDS and current in CURATED_LIGANDS[target].accepted_model_labels:
            method = "curated-label-normalization"
        elif target in _COOT_BASES:
            method = "coot-mutate-base"
        else:
            raise PostMRPreparationError(
                f"Mutation {site} {current}->{target} needs a curated template or dictionary; "
                "automatic coordinate construction is not configured"
            )
        actions.append(MutationAction(site, current, target, method))
    return tuple(actions)


def _coot_script(input_model: Path, output_model: Path, actions: tuple[MutationAction, ...]) -> str:
    lines = [
        "import coot",
        f"imol = coot.handle_read_draw_molecule({json.dumps(str(input_model))})",
        "if imol < 0:",
        "    raise RuntimeError('Coot could not read the PostMR model')",
    ]
    for action in actions:
        chain, resid = _site_parts(action.site)
        try:
            residue_number = int(resid)
        except ValueError as exc:
            raise PostMRPreparationError(
                f"Coot mutation currently requires an integer residue number: {action.site}"
            ) from exc
        lines.extend([
            f"status = coot.mutate_base(imol, {chain!r}, {residue_number}, '', {action.after!r})",
            f"print('NASOLVE_COOT_MUTATE', {action.site!r}, status)",
            "if status != 1:",
            f"    raise RuntimeError('Coot mutation failed at {action.site}')",
        ])
    lines.extend([
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
) -> tuple[Path, Path]:
    script = coot_directory / "mutate.py"
    log = coot_directory / "coot.log"
    backups = coot_directory / "backups"
    backups.mkdir()
    script.write_text(_coot_script(input_model, output_model, actions), encoding="utf-8")
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


def _default_narestraints_builder(pdb: Path, pairs: Path, output: Path) -> None:
    try:
        from restraints.base_pairs import read_base_pair_file
        from restraints.builder import build_phil_from_pdb
    except ImportError as exc:
        raise PostMRPreparationError("NARestraints is not installed") from exc
    build_phil_from_pdb(pdb, read_base_pair_file(pairs), output, include_stacking=True)


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
    data_root: Path | None = None,
    narestraints_builder: Callable[[Path, Path, Path], None] | None = None,
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
    coot_actions = tuple(action for action in actions if action.method == "coot-mutate-base")
    coot_log: Path | None = None
    after_coot = model_dir / "after_coot.pdb"
    if coot_actions:
        if coot_executable is None:
            sites = ", ".join(action.site for action in coot_actions)
            raise PostMRPreparationError(
                f"Coot is required for canonical mutation site(s) {sites}"
            )
        _, coot_log = _run_coot(
            original, after_coot, coot_actions, coot_executable, coot_dir, environment
        )
    else:
        shutil.copyfile(original, after_coot)

    label_changes = {
        action.site: action.after
        for action in actions
        if action.method == "curated-label-normalization"
    }
    prepared = model_dir / "prepared_model.pdb"
    if label_changes:
        _rewrite_sites(after_coot, prepared, label_changes)
    else:
        shutil.copyfile(after_coot, prepared)
    for action in actions:
        if residue_name(prepared, action.site) != action.after:
            raise PostMRPreparationError(
                f"Prepared model does not contain {action.after} at {action.site}"
            )

    restraint_paths: list[Path] = []
    frame = report.get("frame")
    frame_name = frame.get("name") if isinstance(frame, Mapping) else None
    if isinstance(frame_name, str):
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
        compatibility = restraints_dir / "narestraints_input.pdb"
        compatibility_codes = {
            code: ligand.narestraints_label for code, ligand in CURATED_LIGANDS.items()
        }
        _rewrite_codes(prepared, compatibility, compatibility_codes)
        narestraints = restraints_dir / "narestraints_Std_padd.eff"
        (narestraints_builder or _default_narestraints_builder)(
            compatibility, pair_file, narestraints
        )
        if not narestraints.is_file():
            raise PostMRPreparationError("NARestraints did not create its expected output")
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
            source = curated_dictionary(code, data_root)
        except (KeyError, FileNotFoundError) as exc:
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
        },
        "restraints": [str(path) for path in restraint_paths],
        "readyset": {
            "command": readyset_command,
            "hydrogens": False,
            "log": str(readyset_log),
            "updated_model": str(updated),
            "generated_ligand_cif": str(generated_cif) if generated_cif else None,
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
    "MutationAction",
    "PostMRPreparationError",
    "PostMRResult",
    "build_mutation_plan",
    "prepare_postmr",
    "residue_name",
]
