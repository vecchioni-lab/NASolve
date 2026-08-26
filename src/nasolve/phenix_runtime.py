"""Discovery and validation of arbitrary local Phenix installations."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .config import AppConfig, PhenixSettings


REQUIRED_PROGRAMS = ("phenix.phaser", "phenix.ready_set", "phenix.refine")
OPTIONAL_PROGRAMS = ("phenix.mtz.dump",)
VERSION_PROGRAM = "phenix.version"


class PhenixDiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhenixInstallation:
    root: Path | None
    setup_script: Path | None
    version: str
    executables: dict[str, Path]
    environment: dict[str, str]
    source: str


def _environment_from_setup(
    setup_script: Path,
    base_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Source Phenix safely in bash and capture its resulting environment."""
    script = setup_script.expanduser().resolve()
    if not script.is_file():
        raise PhenixDiscoveryError(f"Phenix environment script does not exist: {script}")
    base = dict(os.environ if base_environment is None else base_environment)
    command = ['source "$1" >/dev/null 2>&1 && env -0', "nasolve", str(script)]
    try:
        result = subprocess.run(
            ["/bin/bash", "-c", *command], env=base, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PhenixDiscoveryError(f"Could not load {script}: {exc}") from exc
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise PhenixDiscoveryError(f"Could not source {script}: {detail or 'unknown error'}")
    captured: dict[str, str] = {}
    for item in result.stdout.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        captured[key.decode(errors="surrogateescape")] = value.decode(errors="surrogateescape")
    return captured


def _find_setup_script(root: Path) -> Path | None:
    direct = [root / "phenix_env.sh", root / "build" / "phenix_env.sh"]
    for candidate in direct:
        if candidate.is_file():
            return candidate.resolve()
    # A user-selected installation root is bounded enough for a fallback scan.
    try:
        return next((p.resolve() for p in root.rglob("phenix_env.sh") if p.is_file()), None)
    except OSError:
        return None


def _version_text(executables: Mapping[str, Path], environment: Mapping[str, str]) -> str:
    version_executable = executables.get(VERSION_PROGRAM)
    attempts: list[list[str]] = []
    if version_executable:
        attempts.append([str(version_executable)])
    attempts.append([str(executables["phenix.phaser"]), "--version"])
    for command in attempts:
        try:
            result = subprocess.run(
                command, env=dict(environment), text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False, timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        output = " ".join(line.strip() for line in result.stdout.splitlines() if line.strip())
        if output:
            match = re.search(r"(?:Phenix\s*)?(\d+\.\d+(?:\.\d+)?(?:[-._]\w+)?)", output, re.I)
            return match.group(1) if match else output[:160]
    return "unknown"


def _from_environment(
    environment: Mapping[str, str],
    source: str,
    root: Path | None = None,
    setup_script: Path | None = None,
) -> PhenixInstallation:
    path_value = environment.get("PATH", "")
    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for program in (*REQUIRED_PROGRAMS, *OPTIONAL_PROGRAMS, VERSION_PROGRAM):
        found = shutil.which(program, path=path_value)
        if found:
            resolved[program] = Path(found).resolve()
        elif program in REQUIRED_PROGRAMS:
            missing.append(program)
    if missing:
        raise PhenixDiscoveryError(f"Missing required Phenix program(s): {', '.join(missing)}")
    version = _version_text(resolved, environment)
    inferred_root = root
    if inferred_root is None:
        phaser = resolved["phenix.phaser"]
        inferred_root = phaser.parent.parent if phaser.parent.name == "bin" else phaser.parent
    return PhenixInstallation(
        root=inferred_root.resolve() if inferred_root else None,
        setup_script=setup_script.resolve() if setup_script else None,
        version=version,
        executables=resolved,
        environment=dict(environment),
        source=source,
    )


def installation_from_candidate(
    candidate: str | Path,
    source: str = "explicit",
    base_environment: Mapping[str, str] | None = None,
) -> PhenixInstallation:
    """Validate an install root, phenix_env.sh, or phenix executable."""
    path = Path(candidate).expanduser().resolve()
    base = dict(os.environ if base_environment is None else base_environment)
    if path.is_file() and path.name == "phenix_env.sh":
        environment = _environment_from_setup(path, base)
        return _from_environment(environment, source, path.parent, path)
    if path.is_file() and path.name.startswith("phenix."):
        base["PATH"] = os.pathsep.join([str(path.parent), base.get("PATH", "")])
        return _from_environment(base, source, path.parent.parent, None)
    if not path.is_dir():
        raise PhenixDiscoveryError(
            "Expected a Phenix installation folder, phenix_env.sh, or phenix executable: " + str(path)
        )
    setup = _find_setup_script(path)
    if setup:
        environment = _environment_from_setup(setup, base)
        return _from_environment(environment, source, path, setup)
    likely_bins = [path / "bin", path / "build" / "bin", path]
    for bin_dir in likely_bins:
        if (bin_dir / "phenix.phaser").is_file():
            base["PATH"] = os.pathsep.join([str(bin_dir), base.get("PATH", "")])
            return _from_environment(base, source, path, None)
    raise PhenixDiscoveryError(f"No usable Phenix environment found beneath {path}")


def standard_install_candidates(
    environ: Mapping[str, str] | None = None,
) -> list[Path]:
    """Return bounded, platform-standard Phenix installation candidates."""
    env = dict(os.environ if environ is None else environ)
    home = Path(env.get("HOME", str(Path.home()))).expanduser()
    patterns: list[tuple[Path, str]]
    if sys.platform == "darwin":
        patterns = [
            (Path("/Applications"), "phenix-*"),
            (Path("/Applications"), "Phenix*"),
            (home / "Applications", "phenix-*"),
        ]
    elif os.name == "nt":
        patterns = []
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            if env.get(variable):
                patterns.append((Path(env[variable]), "phenix-*"))
    else:
        patterns = [
            (Path("/opt"), "phenix-*"),
            (Path("/usr/local"), "phenix-*"),
            (home / "opt", "phenix-*"),
        ]
    found: set[Path] = set()
    for parent, pattern in patterns:
        try:
            found.update(path.resolve() for path in parent.glob(pattern) if path.is_dir())
        except OSError:
            continue
    return sorted(found)


def _version_key(installation: PhenixInstallation) -> tuple[int, ...]:
    numbers = tuple(int(value) for value in re.findall(r"\d+", installation.version))
    return numbers or (0,)


def discover_phenix(
    config: AppConfig,
    explicit: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    standard_candidates: list[Path] | None = None,
) -> PhenixInstallation:
    """Discover Phenix in deterministic precedence order and revalidate it."""
    env = dict(os.environ if environ is None else environ)
    attempts: list[tuple[str, str | Path]] = []
    if explicit:
        attempts.append(("command-line override", explicit))
    if env.get("NASOLVE_PHENIX_ROOT"):
        attempts.append(("NASOLVE_PHENIX_ROOT", env["NASOLVE_PHENIX_ROOT"]))
    saved = config.phenix
    saved_candidate = saved.setup_script or saved.root or saved.executables.get("phenix.phaser")
    if saved_candidate:
        attempts.append(("saved configuration", saved_candidate))

    errors: list[str] = []
    for source, candidate in attempts:
        try:
            return installation_from_candidate(candidate, source, env)
        except PhenixDiscoveryError as exc:
            errors.append(f"{source}: {exc}")

    try:
        return _from_environment(env, "PATH")
    except PhenixDiscoveryError as exc:
        errors.append(f"PATH: {exc}")

    valid_standard: list[PhenixInstallation] = []
    candidates = standard_install_candidates(env) if standard_candidates is None else standard_candidates
    for candidate in candidates:
        try:
            valid_standard.append(
                installation_from_candidate(candidate, f"standard location ({candidate})", env)
            )
        except PhenixDiscoveryError:
            continue
    if valid_standard:
        # Multiple installed versions are normal; prefer the highest validated version.
        return max(valid_standard, key=lambda item: (_version_key(item), str(item.root or "")))
    errors.append("standard locations: no valid Phenix installation found")
    detail = "\n  - ".join(errors)
    raise PhenixDiscoveryError(
        "Phenix could not be discovered. Run 'nasolve configure phenix PATH'."
        + (f"\nAttempts:\n  - {detail}" if detail else "")
    )


def remember_phenix(config: AppConfig, installation: PhenixInstallation) -> None:
    config.phenix = PhenixSettings(
        root=str(installation.root) if installation.root else None,
        setup_script=str(installation.setup_script) if installation.setup_script else None,
        version=installation.version,
        executables={name: str(path) for name, path in installation.executables.items()},
        validated_utc=datetime.now(timezone.utc).isoformat(),
    )
