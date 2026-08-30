"""NASolve command-line interface."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from typing import Mapping

from .autorefine import AutoRefineError, execute_autorefine
from .autosol import AutoSolPreparationError, execute_autosol
from .automr import AutoMRInputError, ModelAssessmentError, prepare_automr
from .checkpoints import (
    CheckpointError,
    add_checkpoint,
    list_checkpoints,
    select_checkpoint,
)
from .config import AppConfig, ConfigError, default_config_path, load_config, save_config
from .coot_runtime import (
    CootDiscoveryError,
    discover_coot,
    installation_from_candidate as coot_from_candidate,
    remember_coot,
)
from .coot_view import CootViewError, launch_coot_view, resolve_run
from .phenix_runtime import (
    PhenixDiscoveryError,
    discover_phenix,
    installation_from_candidate,
    remember_phenix,
)
from .phaser import PhaserExecutionError, execute_phaser
from .postmr import PostMRPreparationError, prepare_postmr
from .refine_doctor import RefineDoctorError, execute_refine_doctor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nasolve", description="Guarded nucleic-acid structure solution")
    parser.add_argument("--phenix-root", help="one-run Phenix root, phenix_env.sh, or executable override")
    subparsers = parser.add_subparsers(dest="command", required=True)
    configure = subparsers.add_parser("configure", help="save external-tool configuration")
    configure_sub = configure.add_subparsers(dest="configure_target", required=True)
    phenix = configure_sub.add_parser("phenix", help="discover, validate, and remember Phenix")
    phenix.add_argument("path", nargs="?", help="Phenix root, phenix_env.sh, or phenix executable")
    coot = configure_sub.add_parser("coot", help="discover, validate, and remember Coot")
    coot.add_argument("path", nargs="?", help="Coot executable or installation directory")
    workspace = subparsers.add_parser(
        "workspace", help="remember or inspect the active dataset/run on this computer"
    )
    workspace_sub = workspace.add_subparsers(dest="workspace_action", required=True)
    workspace_use = workspace_sub.add_parser(
        "use", help="make a dataset or completed run the active target"
    )
    workspace_use.add_argument("target", type=Path)
    workspace_sub.add_parser("status", help="show the active dataset and run")
    workspace_sub.add_parser("clear", help="forget the active dataset and run")
    subparsers.add_parser("check", help="validate NASolve's runtime without solving a structure")
    automr = subparsers.add_parser(
        "automr", help="validate and freeze molecular-replacement inputs"
    )
    automr.add_argument(
        "dataset", nargs="?", type=Path,
        help="dataset directory (default: active workspace, then current directory)",
    )
    frames = automr.add_mutually_exclusive_group()
    frames.add_argument(
        "-W", "--w-frame", dest="frame", action="store_const", const="W",
        help="use the standard 5W6W/W frame",
    )
    frames.add_argument(
        "-3GBI", dest="frame", action="store_const", const="3GBI",
        help="use the standard 3GBI frame",
    )
    frames.add_argument("--frame", help="standard frame name (W, 5W6W, or 3GBI)")
    automr.add_argument("--pair", help="ordered standard-site pair, for example D:T")
    automr.add_argument(
        "--allow-p1-standard", action="store_true",
        help="strongly discouraged: allow a standard frame in P1 using three MR copies",
    )
    automr.add_argument(
        "--config", type=Path,
        help="input file (default: DATASET/nasolve.txt; generated there when absent)",
    )
    automr.add_argument(
        "--frames-dir", type=Path,
        help="approved MR frame directory (normally discovered from the repository/package)",
    )
    automr.add_argument(
        "--execute", action="store_true",
        help="run Phenix Phaser after the guarded preflight",
    )
    automr.add_argument(
        "--mirror", action="store_true",
        help="mirror the selected D/L nucleic-acid model with NARestraints before MR",
    )
    postmr = subparsers.add_parser(
        "postmr", help="prepare an accepted Phaser solution for refinement"
    )
    postmr.add_argument(
        "run", nargs="?", type=Path,
        help="completed AutoMR run directory (default: active workspace run)",
    )
    postmr.add_argument("--coot", help="one-run Coot executable override")
    postmr.add_argument(
        "--allow-mr-review", action="store_true",
        help="explicitly continue from a TFZ 7.0-7.99 MR_REVIEW result",
    )
    postmr.add_argument(
        "--modified-pairs-only",
        action="store_true",
        help="guess base pairs and restrain only pairs containing a modified nucleotide",
    )
    autosol = subparsers.add_parser(
        "autosol", help="run guarded MR-SAD phasing when PostMR finds a heavy atom"
    )
    autosol.add_argument(
        "run", nargs="?", type=Path,
        help="completed POSTMR_READY run directory (default: active workspace run)",
    )
    autorefine = subparsers.add_parser(
        "autorefine", help="run one quiet, checkpointed Phenix refinement round"
    )
    autorefine.add_argument(
        "run", nargs="?", type=Path,
        help="completed PostMR/AutoSol run directory (default: active workspace run)",
    )
    autorefine.add_argument(
        "--from", dest="from_checkpoint",
        help="checkpoint ID or bookmark to branch from (default: current)",
    )
    autorefine.add_argument(
        "--recipe", default="AutoRefine/default",
        help="refinement recipe label recorded in provenance",
    )
    autorefine.add_argument(
        "--cycles", type=int, default=5,
        help="number of refinement macrocycles (default: 5)",
    )
    doctor = subparsers.add_parser(
        "refine-doctor",
        aliases=["refine_doctor"],
        help="audit and triage a refinement with bounded checkpoint branches",
    )
    doctor.add_argument(
        "run", nargs="?", type=Path,
        help="completed PostMR/AutoRefine run directory (default: active workspace run)",
    )
    doctor.add_argument(
        "--from", dest="from_checkpoint",
        help="checkpoint ID or bookmark to diagnose (default: current)",
    )
    doctor.add_argument(
        "--cycles", type=int, default=3,
        help="macrocycles per bounded diagnostic branch (default: 3)",
    )
    checkpoints = subparsers.add_parser(
        "checkpoints", help="list, bookmark, import, or select refinement checkpoints"
    )
    checkpoint_sub = checkpoints.add_subparsers(dest="checkpoint_action", required=True)
    checkpoint_list = checkpoint_sub.add_parser("list", help="list the checkpoint tree")
    checkpoint_list.add_argument("run", nargs="?", type=Path)
    checkpoint_add = checkpoint_sub.add_parser(
        "add", help="bookmark the current checkpoint or import a manual model"
    )
    checkpoint_add.add_argument("run", nargs="?", type=Path)
    checkpoint_add.add_argument("--name", required=True, help="user-visible checkpoint name")
    checkpoint_add.add_argument("--model", type=Path, help="manual PDB model to import")
    checkpoint_add.add_argument(
        "--mtz", type=Path,
        help="deliberate replacement observation MTZ for an imported model",
    )
    checkpoint_add.add_argument(
        "--from", dest="from_checkpoint",
        help="parent checkpoint ID or bookmark (default: current)",
    )
    checkpoint_use = checkpoint_sub.add_parser("use", help="select a reusable checkpoint")
    checkpoint_use.add_argument(
        "run_or_checkpoint",
        help="run path, or checkpoint ID/bookmark when an active run is selected",
    )
    checkpoint_use.add_argument(
        "checkpoint", nargs="?",
        help="checkpoint ID/bookmark when an explicit run path is supplied",
    )
    show = subparsers.add_parser(
        "show", help="open a completed run stage in an isolated graphical Coot session"
    )
    show.add_argument(
        "target", nargs="?",
        help="run directory, 'last', or omit to use the active workspace run",
    )
    show.add_argument(
        "dataset", nargs="?", type=Path,
        help="dataset directory required by 'show last'",
    )
    show.add_argument(
        "--stage", choices=("automr", "postmr", "autosol", "autorefine"),
        help="view a specific completed stage instead of the most advanced one",
    )
    show.add_argument(
        "--checkpoint",
        help="open a specific refinement checkpoint without selecting it",
    )
    show.add_argument("--coot", help="one-run Coot executable override")
    return parser


def _narestraints_version() -> str:
    try:
        return importlib.metadata.version("NARestraints")
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def _run_report_path(path: Path) -> Path:
    selected = path.expanduser().resolve()
    return selected if selected.name == "report.json" else selected / "report.json"


def _workspace_dataset(
    explicit: Path | None,
    config: AppConfig,
    *,
    current_directory_fallback: bool = True,
) -> Path:
    value: Path | None = explicit
    if value is None and config.workspace.dataset:
        value = Path(config.workspace.dataset)
    if value is None and current_directory_fallback:
        value = Path(".")
    if value is None:
        raise ConfigError(
            "No active dataset. Run 'nasolve workspace use DATASET' or pass a path."
        )
    dataset = value.expanduser().resolve()
    if not dataset.is_dir():
        raise ConfigError(f"Workspace dataset does not exist: {dataset}")
    return dataset


def _workspace_run(explicit: Path | None, config: AppConfig) -> Path:
    value = explicit or (Path(config.workspace.run) if config.workspace.run else None)
    if value is None:
        raise ConfigError(
            "No active run. Run 'nasolve workspace use RUN' or pass a run path."
        )
    report_path = _run_report_path(value)
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Active run has no readable report: {report_path}") from exc
    if not isinstance(report, Mapping):
        raise ConfigError(f"Active run report is not a JSON object: {report_path}")
    if report.get("workflow") != "automr":
        raise ConfigError(f"Active run is not a NASolve AutoMR run: {report_path.parent}")
    return report_path.parent


def _remember_workspace(config: AppConfig, run: Path) -> None:
    resolved = run.expanduser().resolve()
    config.workspace.run = str(resolved)
    config.workspace.dataset = str(
        resolved.parent.parent if resolved.parent.name == "AutoMR" else resolved.parent
    )


def _workspace(args: argparse.Namespace) -> int:
    try:
        config = load_config()
        if args.workspace_action == "clear":
            config.workspace.dataset = None
            config.workspace.run = None
            saved_at = save_config(config)
            print("Active NASolve workspace cleared.")
            print(f"Saved: {saved_at}")
            return 0
        if args.workspace_action == "use":
            target = args.target.expanduser().resolve()
            report_path = _run_report_path(target)
            if report_path.is_file():
                run = _workspace_run(target, config)
                _remember_workspace(config, run)
            else:
                if not target.is_dir():
                    raise ConfigError(f"Workspace target does not exist: {target}")
                config.workspace.dataset = str(target)
                config.workspace.run = None
            saved_at = save_config(config)
            print(f"Active dataset: {config.workspace.dataset}")
            print(f"Active run: {config.workspace.run or 'none'}")
            print(f"Saved: {saved_at}")
            return 0
        print(f"Active dataset: {config.workspace.dataset or 'none'}")
        print(f"Active run: {config.workspace.run or 'none'}")
        print(f"Configuration: {default_config_path()}")
        return 0
    except ConfigError as exc:
        print(f"Workspace error: {exc}", file=sys.stderr)
        return 2


def _configure_phenix(path: str | None) -> int:
    candidate = path
    if not candidate:
        if not sys.stdin.isatty():
            print("Phenix path is required in non-interactive mode.", file=sys.stderr)
            return 2
        candidate = input("Phenix installation folder or phenix_env.sh: ").strip()
    try:
        installation = installation_from_candidate(candidate)
        config = load_config()
        remember_phenix(config, installation)
        saved_at = save_config(config)
    except (ConfigError, PhenixDiscoveryError) as exc:
        print(f"Phenix configuration failed: {exc}", file=sys.stderr)
        return 1
    print(f"Phenix {installation.version}: OK")
    print(f"Source: {installation.source}")
    print(f"Root: {installation.root}")
    print(f"Saved: {saved_at}")
    return 0


def _configure_coot(path: str | None) -> int:
    candidate = path
    if not candidate:
        if not sys.stdin.isatty():
            print("Coot path is required in non-interactive mode.", file=sys.stderr)
            return 2
        candidate = input("Coot executable or installation folder: ").strip()
    try:
        installation = coot_from_candidate(candidate)
        config = load_config()
        remember_coot(config, installation)
        saved_at = save_config(config)
    except (ConfigError, CootDiscoveryError) as exc:
        print(f"Coot configuration failed: {exc}", file=sys.stderr)
        return 1
    print(f"Coot {installation.version}: OK")
    print(f"Executable: {installation.executable}")
    print(f"Saved: {saved_at}")
    return 0


def _check(explicit: str | None) -> int:
    print(f"Python {sys.version.split()[0]}: OK")
    na_version = _narestraints_version()
    print(f"NARestraints {na_version}: " + ("OK" if na_version != "not installed" else "MISSING"))
    try:
        config = load_config()
        installation = discover_phenix(config, explicit=explicit)
        saved_at = None
        if explicit is None:
            remember_phenix(config, installation)
            saved_at = save_config(config)
    except (ConfigError, PhenixDiscoveryError) as exc:
        print(f"Phenix: NOT CONFIGURED\n{exc}")
        print(f"Configuration file: {default_config_path()}")
        return 1
    print(f"Phenix {installation.version}: OK")
    print(f"Source: {installation.source}")
    for name, executable in installation.executables.items():
        print(f"  {name}: {executable}")
    if saved_at:
        print(f"Remembered: {saved_at}")
    try:
        coot = discover_coot(config)
        remember_coot(config, coot)
        save_config(config)
    except CootDiscoveryError as exc:
        print("Coot: NOT CONFIGURED (needed only when PostMR must mutate supported bases)")
        print(str(exc))
    else:
        print(f"Coot {coot.version}: OK")
        print(f"  coot: {coot.executable}")
    return 0 if na_version != "not installed" else 1


def _automr(args: argparse.Namespace) -> int:
    try:
        config = load_config()
        dataset = _workspace_dataset(args.dataset, config)
        installation = discover_phenix(config, explicit=args.phenix_root)
        if args.phenix_root is None:
            remember_phenix(config, installation)
            save_config(config)
        result = prepare_automr(
            dataset,
            config_path=args.config,
            frame_override=args.frame,
            pair_override=args.pair,
            frames_dir=args.frames_dir,
            allow_p1_standard=args.allow_p1_standard,
            mirror=args.mirror,
            mtz_dump_executable=installation.executables.get("phenix.mtz.dump"),
            phenix_environment=installation.environment,
        )
        _remember_workspace(config, result.run_directory)
        save_config(config)
        if args.execute:
            phaser = execute_phaser(
                result.report_path,
                installation.executables["phenix.phaser"],
                environment=installation.environment,
                phenix_version=installation.version,
            )
    except (
        AutoMRInputError,
        ModelAssessmentError,
        ConfigError,
        PhenixDiscoveryError,
        PhaserExecutionError,
    ) as exc:
        print(f"AutoMR input error: {exc}", file=sys.stderr)
        return 2
    if args.execute:
        print(f"{phaser.status}: {phaser.message}")
        print("Phaser executed: yes")
        print(f"Run directory: {phaser.run_directory}")
        print(f"Phaser log: {phaser.log_path}")
        print(f"Report: {phaser.report_path}")
        if phaser.solution_pdb:
            print(f"MR model: {phaser.solution_pdb}")
        if phaser.solution_mtz:
            print(f"MR reflections: {phaser.solution_mtz}")
        return phaser.exit_code
    print(f"{result.status}: {result.message}")
    print("Phaser executed: no (preflight milestone)")
    print(f"Run directory: {result.run_directory}")
    print(f"Report: {result.report_path}")
    if result.generated_config:
        print(f"Generated: {dataset / 'nasolve.txt'}")
    return 0


def _postmr(args: argparse.Namespace) -> int:
    try:
        config = load_config()
        run = _workspace_run(args.run, config)
        phenix = discover_phenix(config, explicit=args.phenix_root)
        if args.phenix_root is None:
            remember_phenix(config, phenix)
        coot = None
        try:
            coot = discover_coot(config, explicit=args.coot)
        except CootDiscoveryError:
            if args.coot:
                raise
        else:
            remember_coot(config, coot)
        save_config(config)
        result = prepare_postmr(
            run,
            phenix.executables["phenix.ready_set"],
            coot_executable=coot.executable if coot else None,
            environment=phenix.environment,
            allow_mr_review=args.allow_mr_review,
            modified_pairs_only=args.modified_pairs_only,
        )
    except (
        ConfigError,
        CootDiscoveryError,
        PhenixDiscoveryError,
        PostMRPreparationError,
    ) as exc:
        print(f"PostMR preparation error: {exc}", file=sys.stderr)
        return 2
    print(f"{result.status}: {result.message}")
    print(f"Run directory: {result.run_directory}")
    print(f"Prepared model: {result.model_path}")
    print(f"ReadySet log: {result.readyset_log}")
    for restraint in result.restraint_paths:
        print(f"Restraint: {restraint}")
    print(f"Report: {result.report_path}")
    return 0


def _autosol(args: argparse.Namespace) -> int:
    try:
        config = load_config()
        run = _workspace_run(args.run, config)
        phenix = discover_phenix(config, explicit=args.phenix_root)
        if args.phenix_root is None:
            remember_phenix(config, phenix)
            save_config(config)
        autosol_executable = phenix.executables.get("phenix.autosol")
        mtz_dump_executable = phenix.executables.get("phenix.mtz.dump")
        if autosol_executable is None:
            raise AutoSolPreparationError(
                "The discovered Phenix installation has no phenix.autosol executable"
            )
        if mtz_dump_executable is None:
            raise AutoSolPreparationError(
                "AutoSol validation requires phenix.mtz.dump"
            )
        result = execute_autosol(
            run,
            autosol_executable,
            mtz_dump_executable,
            environment=phenix.environment,
        )
    except (
        AutoSolPreparationError,
        ConfigError,
        PhenixDiscoveryError,
    ) as exc:
        print(f"AutoSol preparation error: {exc}", file=sys.stderr)
        return 2
    print(f"{result.status}: {result.message}")
    print(f"Run directory: {result.run_directory}")
    print(f"AutoSol log: {result.log_path}")
    if result.heavy_atom_model:
        print(f"Heavy-atom model: {result.heavy_atom_model}")
    if result.refinement_data:
        print(f"Refinement data: {result.refinement_data}")
    if result.matched_distance is not None:
        print(f"Matched HA distance: {result.matched_distance:.3f} A")
    if result.status != "AUTOSOL_READY":
        print("Refinement continuation: yes, without automatically approved AutoSol phases")
    print(f"Report: {result.report_path}")
    return 0


def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty() or "NO_COLOR" in os.environ:
        return text
    return f"\033[{code}m{text}\033[0m"


def _status_text(status: str, *, current: bool = False) -> str:
    colors = {
        "READY": "32",
        "SUCCESS": "32",
        "USER_APPROVED": "32",
        "REVIEW": "33",
        "FAILED": "31",
    }
    marker = _color(">", "36") if current else " "
    return f"{marker} {_color(status, colors.get(status, '0'))}"


def _format_metric(value: object, digits: int = 3) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "—"


def _autorefine(args: argparse.Namespace) -> int:
    try:
        config = load_config()
        run = _workspace_run(args.run, config)
        phenix = discover_phenix(config, explicit=args.phenix_root)
        if args.phenix_root is None:
            remember_phenix(config, phenix)
            save_config(config)
        mtz_dump = phenix.executables.get("phenix.mtz.dump")
        if mtz_dump is None:
            raise AutoRefineError("AutoRefine requires phenix.mtz.dump")

        def progress(checkpoint_id: str, log_path: Path) -> None:
            print(f"AutoRefine {checkpoint_id} started; full output: {log_path}")

        result = execute_autorefine(
            run,
            phenix.executables["phenix.refine"],
            mtz_dump,
            environment=phenix.environment,
            from_checkpoint=args.from_checkpoint,
            recipe=args.recipe,
            macro_cycles=args.cycles,
            progress=progress,
        )
    except (AutoRefineError, ConfigError, PhenixDiscoveryError) as exc:
        print(f"AutoRefine error: {exc}", file=sys.stderr)
        return 2
    status_color = (
        "32" if result.status == "AUTOREFINE_READY"
        else "33" if result.status in {"AUTOREFINE_REVIEW", "AUTOREFINE_ANOMALOUS_FALLBACK"}
        else "31"
    )
    print(f"\n{_color(result.status, status_color)}: {result.message}")
    print(f"Checkpoint: {result.checkpoint_id} (parent: {result.parent_checkpoint})")
    print("Cycles: " + str(args.cycles))
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    inputs = payload.get("inputs", {})
    refinement = payload.get("refinement", {})
    if isinstance(inputs, dict) and isinstance(refinement, dict):
        print("Target: Automatic")
        print("Observations: " + ",".join(inputs.get("observation_labels", [])))
        phase_labels = inputs.get("phase_labels", [])
        print("Phases: " + (",".join(phase_labels) if phase_labels else "none"))
        selections = refinement.get("anomalous_selections", [])
        print("Anomalous: " + ("; ".join(selections) if selections else "off"))
    stats = result.statistics
    print("\n                 Initial    Final")
    print(
        "Rwork           "
        f"{_format_metric(stats.get('initial_r_work')):>9}"
        f"{_format_metric(stats.get('r_work')):>9}"
    )
    print(
        "Rfree           "
        f"{_format_metric(stats.get('initial_r_free')):>9}"
        f"{_format_metric(stats.get('r_free')):>9}"
    )
    print(f"Rfree - Rwork   {'':>9}{_format_metric(stats.get('r_free_minus_r_work')):>9}")
    print(f"Clashscore      {'':>9}{_format_metric(stats.get('clashscore'), 2):>9}")
    bond = _format_metric(stats.get("bond_rmsd"), 3)
    angle = _format_metric(stats.get("angle_rmsd"), 2)
    print(f"Bond RMSD       {'':>9}{(bond + ' A') if bond != '—' else bond:>9}")
    print(f"Angle RMSD      {'':>9}{(angle + ' deg') if angle != '—' else angle:>9}")
    anomalous_stats = stats.get("anomalous_scatterers")
    if isinstance(anomalous_stats, list) and anomalous_stats:
        print("\nAnomalous-scatterer strength:")
        for item in anomalous_stats:
            if not isinstance(item, dict):
                continue
            label = f"{item.get('site')} {item.get('atom_name')} ({item.get('element')})"
            wavelength = _format_metric(item.get("wavelength"), 6)
            refined_fdp = _format_metric(item.get("refined_f_double_prime"), 3)
            calculated_fdp = _format_metric(item.get("calculated_f_double_prime"), 3)
            occupancy = _format_metric(item.get("model_occupancy"), 3)
            apparent = _format_metric(item.get("apparent_anomalous_occupancy"), 3)
            b_factor = _format_metric(item.get("b_factor"), 2)
            expected_at_occ = _format_metric(
                item.get("calculated_f_double_prime_at_occupancy"), 3
            )
            print(f"  {label}: wavelength {wavelength} A")
            print(f"    f'' refined {refined_fdp}; calculated {calculated_fdp} e-")
            print(
                f"    occupancy {occupancy}; calculated f'' x occupancy "
                f"{expected_at_occ}; apparent anomalous occupancy {apparent}"
            )
            resolution = item.get("resolution_limit")
            if isinstance(resolution, (int, float)):
                expected_edge = _format_metric(
                    item.get("calculated_contribution_at_resolution_limit"), 3
                )
                refined_edge = _format_metric(
                    item.get("refined_contribution_at_resolution_limit"), 3
                )
                print(
                    f"    B {b_factor} A^2; at {resolution:.3f} A: "
                    f"calculated {expected_edge}, refined {refined_edge} e-"
                )
    series = stats.get("cycle_series")
    if isinstance(series, list) and series:
        work_trend = " -> ".join(
            _format_metric(item.get("r_work"))
            for item in series if isinstance(item, dict)
        )
        free_trend = " -> ".join(
            _format_metric(item.get("r_free"))
            for item in series if isinstance(item, dict)
        )
        print(f"\nRwork trend: {work_trend}")
        print(f"Rfree trend: {free_trend}")
    diagnostics = stats.get("diagnostics")
    if isinstance(diagnostics, list) and diagnostics:
        print("\nActionable Phenix messages:")
        for message in diagnostics[:5]:
            print(f"  - {message}")
        if len(diagnostics) > 5:
            print(f"  - {len(diagnostics) - 5} more in the full log")
    if result.model_path:
        print(f"\nRefined model: {result.model_path}")
    if result.model_cif:
        print(f"Refined model mmCIF: {result.model_cif}")
    if result.reflection_cif:
        print(f"Reflections mmCIF: {result.reflection_cif}")
    if result.map_coefficients:
        print(f"Map coefficients: {result.map_coefficients}")
    print(f"Full log: {result.log_path}")
    print(f"Report: {result.report_path}")
    if result.selected_as_current:
        print(_color("Current checkpoint updated.", "32"))
    else:
        print("Current checkpoint unchanged; inspect or select this result explicitly.")
    return result.exit_code


def _refine_doctor(args: argparse.Namespace) -> int:
    try:
        config = load_config()
        run = _workspace_run(args.run, config)
        phenix = discover_phenix(config, explicit=args.phenix_root)
        if args.phenix_root is None:
            remember_phenix(config, phenix)
            save_config(config)
        mtz_dump = phenix.executables.get("phenix.mtz.dump")
        if mtz_dump is None:
            raise RefineDoctorError("Refine Doctor requires phenix.mtz.dump")

        def progress(recipe: str, checkpoint: str, log_path: Path) -> None:
            short_recipe = recipe.rsplit("/", 1)[-1]
            print(
                _color(f"Refine Doctor: {short_recipe} -> {checkpoint}", "36")
                + f"; full output: {log_path}"
            )

        result = execute_refine_doctor(
            run,
            phenix.executables["phenix.refine"],
            mtz_dump,
            environment=phenix.environment,
            from_checkpoint=args.from_checkpoint,
            macro_cycles=args.cycles,
            progress=progress,
        )
    except (RefineDoctorError, ConfigError, PhenixDiscoveryError) as exc:
        print(f"Refine Doctor error: {exc}", file=sys.stderr)
        return 2
    colors = {
        "REFINE_DOCTOR_GOOD_ENOUGH": "32",
        "REFINE_DOCTOR_RECOMMEND": "36",
        "REFINE_DOCTOR_REVIEW": "33",
        "REFINE_DOCTOR_FLAG_REPAIR_REQUIRED": "31",
    }
    print(f"\n{_color(result.status, colors.get(result.status, '0'))}: {result.message}")
    print(f"Source checkpoint: {result.source_checkpoint}")
    print(
        "Current checkpoint: preserved"
        if result.current_checkpoint_preserved else "Current checkpoint: CHANGED"
    )
    details = result.audit.details
    free_groups = details.get("free_independent_groups")
    fraction = details.get("free_fraction")
    fraction_text = f"{100 * fraction:.1f}%" if isinstance(fraction, (int, float)) else "—"
    print(
        f"Free-R audit: {result.audit.status}; independent free groups "
        f"{free_groups if isinstance(free_groups, int) else '—'} ({fraction_text})"
    )
    for warning in result.audit.warnings:
        print(f"  - {warning}")

    if result.benchmark:
        print("\nStored anomalous benchmark:")
        for item in result.benchmark:
            print(
                f"  {item.get('site')} {item.get('atom_name')}: "
                f"f'' refined {_format_metric(item.get('refined_f_double_prime'))}; "
                f"calculated {_format_metric(item.get('calculated_f_double_prime'))}; "
                f"occupancy {_format_metric(item.get('model_occupancy'))}; "
                f"B {_format_metric(item.get('b_factor'), 2)} A^2 "
                f"[{item.get('source_checkpoint')}]"
            )

    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates")
    if isinstance(candidates, list) and candidates:
        print("\nCheckpoint    Rwork   Rfree     Gap  Recipe")
        for item in candidates:
            if not isinstance(item, dict):
                continue
            marker = ">" if item.get("checkpoint") == result.recommended_checkpoint else " "
            print(
                f"{marker} {str(item.get('checkpoint')):<11} "
                f"{_format_metric(item.get('r_work')):>6} "
                f"{_format_metric(item.get('r_free')):>7} "
                f"{_format_metric(item.get('r_free_minus_r_work')):>7}  "
                f"{item.get('recipe')}"
            )
    print(f"\nRecommendation: {result.recommendation}")
    if result.recommended_checkpoint:
        inspect_command = (
            f"nasolve show {result.run_directory} "
            f"--checkpoint {result.recommended_checkpoint}"
        )
        select_command = (
            f"nasolve checkpoints use {result.run_directory} "
            f"{result.recommended_checkpoint}"
        )
        print(
            "Select after map/model inspection: "
            + select_command
        )
    print(f"Free-R audit log: {result.audit.log_path}")
    print(f"Report: {result.report_path}")
    if result.recommended_checkpoint:
        if sys.stdin.isatty():
            while True:
                answer = input(
                    f"\nUse {result.recommended_checkpoint} as the current checkpoint? "
                    "[y/N/i=inspection commands]: "
                ).strip().casefold()
                if answer in {"y", "yes"}:
                    try:
                        selected = select_checkpoint(
                            result.run_directory, result.recommended_checkpoint
                        )
                    except CheckpointError as exc:
                        print(f"Checkpoint error: {exc}", file=sys.stderr)
                        return 2
                    print(_color(f"Current checkpoint: {selected.checkpoint_id}", "36"))
                    break
                if answer in {"", "n", "no", "i", "inspect"}:
                    print("Current checkpoint unchanged.")
                    print("Inspect without selecting:")
                    print(f"  {inspect_command}")
                    print("Select later:")
                    print(f"  {select_command}")
                    print("Return to the diagnosed source if needed:")
                    print(
                        f"  nasolve checkpoints use {result.run_directory} "
                        f"{result.source_checkpoint}"
                    )
                    break
                print("Please enter y, n, or i.")
        else:
            print("Inspect without selecting:")
            print(f"  {inspect_command}")
            print("Select later:")
            print(f"  {select_command}")
    return result.exit_code


def _checkpoints(args: argparse.Namespace) -> int:
    try:
        config = load_config()
        if args.checkpoint_action == "use":
            if args.checkpoint is None:
                explicit_run = None
                checkpoint = args.run_or_checkpoint
            else:
                explicit_run = Path(args.run_or_checkpoint)
                checkpoint = args.checkpoint
        else:
            explicit_run = args.run
            checkpoint = None
        run = _workspace_run(explicit_run, config)
        if args.checkpoint_action == "list":
            records, current, bookmarks = list_checkpoints(run)
            names_by_id: dict[str, list[str]] = {}
            for name, target in bookmarks.items():
                names_by_id.setdefault(target, []).append(name)
            print("  Status         Checkpoint   Parent        Rwork/Rfree    Recipe")
            for record in records:
                marker = _status_text(
                    record.status, current=record.checkpoint_id == current
                )
                values = (
                    f"{_format_metric(record.metrics.get('r_work'))}/"
                    f"{_format_metric(record.metrics.get('r_free'))}"
                )
                aliases = names_by_id.get(record.checkpoint_id, [])
                label = f" [{', '.join(aliases)}]" if aliases else ""
                print(
                    f"{marker} {record.checkpoint_id:<12} "
                    f"{(record.parent or '—'):<13} {values:<14} "
                    f"{record.recipe}{label}"
                )
            return 0
        if args.checkpoint_action == "add":
            record = add_checkpoint(
                run,
                name=args.name,
                model=args.model,
                reflections=args.mtz,
                parent=args.from_checkpoint,
            )
            action = "Imported" if args.model else "Bookmarked"
            print(f"{action}: {args.name} -> {record.checkpoint_id}")
            if args.model:
                print("Status: REVIEW (select explicitly after inspection)")
            return 0
        if args.checkpoint_action == "use":
            assert isinstance(checkpoint, str)
            record = select_checkpoint(run, checkpoint)
            print(_color(f"Current checkpoint: {record.checkpoint_id}", "36"))
            print(f"Status: {record.status}")
            print(f"Model: {record.model}")
            return 0
    except (CheckpointError, ConfigError) as exc:
        print(f"Checkpoint error: {exc}", file=sys.stderr)
        return 2
    return 2


def _show(args: argparse.Namespace) -> int:
    try:
        config = load_config()
        if args.target is None:
            run = _workspace_run(None, config)
        else:
            dataset = args.dataset
            if str(args.target).casefold() == "last" and dataset is None:
                dataset = _workspace_dataset(
                    None, config, current_directory_fallback=False
                )
            run = resolve_run(args.target, dataset)
        coot = discover_coot(config, explicit=args.coot)
        remember_coot(config, coot)
        save_config(config)
        result = launch_coot_view(
            run,
            coot.executable,
            stage=args.stage,
            checkpoint=args.checkpoint,
        )
    except (ConfigError, CootDiscoveryError, CootViewError) as exc:
        print(f"Coot view error: {exc}", file=sys.stderr)
        return 2
    print(f"Opened {result.stage}: {result.model_path.name} + {result.map_path.name}")
    for extra in result.extra_model_paths:
        print(f"Additional model: {extra}")
    print(f"Coot working directory: {result.working_directory}")
    print(f"Coot log: {result.log_path}")
    print(f"PID: {result.pid}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "configure" and args.configure_target == "phenix":
        return _configure_phenix(args.path)
    if args.command == "configure" and args.configure_target == "coot":
        return _configure_coot(args.path)
    if args.command == "workspace":
        return _workspace(args)
    if args.command == "check":
        return _check(args.phenix_root)
    if args.command == "automr":
        return _automr(args)
    if args.command == "postmr":
        return _postmr(args)
    if args.command == "autosol":
        return _autosol(args)
    if args.command == "autorefine":
        return _autorefine(args)
    if args.command in {"refine-doctor", "refine_doctor"}:
        return _refine_doctor(args)
    if args.command == "checkpoints":
        return _checkpoints(args)
    if args.command == "show":
        return _show(args)
    return 2
