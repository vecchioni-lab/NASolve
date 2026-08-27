"""NASolve command-line interface."""

from __future__ import annotations

import argparse
import importlib.metadata
import sys
from pathlib import Path

from .automr import AutoMRInputError, ModelAssessmentError, prepare_automr
from .config import ConfigError, default_config_path, load_config, save_config
from .coot_runtime import (
    CootDiscoveryError,
    discover_coot,
    installation_from_candidate as coot_from_candidate,
    remember_coot,
)
from .phenix_runtime import (
    PhenixDiscoveryError,
    discover_phenix,
    installation_from_candidate,
    remember_phenix,
)
from .phaser import PhaserExecutionError, execute_phaser
from .postmr import PostMRPreparationError, prepare_postmr


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
    subparsers.add_parser("check", help="validate NASolve's runtime without solving a structure")
    automr = subparsers.add_parser(
        "automr", help="validate and freeze molecular-replacement inputs"
    )
    automr.add_argument(
        "dataset", nargs="?", default=Path("."), type=Path,
        help="dataset directory (default: current directory)",
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
    postmr = subparsers.add_parser(
        "postmr", help="prepare an accepted Phaser solution for refinement"
    )
    postmr.add_argument("run", type=Path, help="completed AutoMR run directory")
    postmr.add_argument("--coot", help="one-run Coot executable override")
    postmr.add_argument(
        "--allow-mr-review", action="store_true",
        help="explicitly continue from a TFZ 7.0-7.99 MR_REVIEW result",
    )
    return parser


def _narestraints_version() -> str:
    try:
        return importlib.metadata.version("NARestraints")
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


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
        installation = discover_phenix(config, explicit=args.phenix_root)
        if args.phenix_root is None:
            remember_phenix(config, installation)
            save_config(config)
        result = prepare_automr(
            args.dataset,
            config_path=args.config,
            frame_override=args.frame,
            pair_override=args.pair,
            frames_dir=args.frames_dir,
            allow_p1_standard=args.allow_p1_standard,
            mtz_dump_executable=installation.executables.get("phenix.mtz.dump"),
            phenix_environment=installation.environment,
        )
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
        print(f"Generated: {args.dataset.expanduser().resolve() / 'nasolve.txt'}")
    return 0


def _postmr(args: argparse.Namespace) -> int:
    try:
        config = load_config()
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
            args.run,
            phenix.executables["phenix.ready_set"],
            coot_executable=coot.executable if coot else None,
            environment=phenix.environment,
            allow_mr_review=args.allow_mr_review,
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "configure" and args.configure_target == "phenix":
        return _configure_phenix(args.path)
    if args.command == "configure" and args.configure_target == "coot":
        return _configure_coot(args.path)
    if args.command == "check":
        return _check(args.phenix_root)
    if args.command == "automr":
        return _automr(args)
    if args.command == "postmr":
        return _postmr(args)
    return 2
