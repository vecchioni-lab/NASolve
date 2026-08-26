"""NASolve command-line interface."""

from __future__ import annotations

import argparse
import importlib.metadata
import sys
from pathlib import Path

from .config import ConfigError, default_config_path, load_config, save_config
from .phenix_runtime import (
    PhenixDiscoveryError,
    discover_phenix,
    installation_from_candidate,
    remember_phenix,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nasolve", description="Guarded nucleic-acid structure solution")
    parser.add_argument("--phenix-root", help="one-run Phenix root, phenix_env.sh, or executable override")
    subparsers = parser.add_subparsers(dest="command", required=True)
    configure = subparsers.add_parser("configure", help="save external-tool configuration")
    configure_sub = configure.add_subparsers(dest="configure_target", required=True)
    phenix = configure_sub.add_parser("phenix", help="discover, validate, and remember Phenix")
    phenix.add_argument("path", nargs="?", help="Phenix root, phenix_env.sh, or phenix executable")
    subparsers.add_parser("check", help="validate NASolve's runtime without solving a structure")
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
    return 0 if na_version != "not installed" else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "configure" and args.configure_target == "phenix":
        return _configure_phenix(args.path)
    if args.command == "check":
        return _check(args.phenix_root)
    return 2
