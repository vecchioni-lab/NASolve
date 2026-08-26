"""Discovery and validation of a command-line Coot installation."""

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

from .config import AppConfig, CootSettings


class CootDiscoveryError(RuntimeError):
    """Raised when no usable headless Coot runtime can be found."""


@dataclass(frozen=True)
class CootInstallation:
    executable: Path
    version: str
    source: str


_PYTHON_MARKER = "NASOLVE_COOT_PYTHON_OK"


def _candidate_executable(candidate: str | Path) -> Path:
    path = Path(candidate).expanduser()
    if path.is_file():
        return path.resolve()
    if path.is_dir():
        for relative in ("coot", "bin/coot"):
            executable = path / relative
            if executable.is_file():
                return executable.resolve()
    raise CootDiscoveryError(f"Coot executable does not exist: {path}")


def installation_from_candidate(
    candidate: str | Path,
    source: str = "explicit",
    environment: Mapping[str, str] | None = None,
) -> CootInstallation:
    executable = _candidate_executable(candidate)
    env = dict(os.environ if environment is None else environment)
    try:
        version_result = subprocess.run(
            [str(executable), "--version"],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CootDiscoveryError(f"Could not run {executable}: {exc}") from exc
    if version_result.returncode:
        raise CootDiscoveryError(
            f"Coot --version exited with status {version_result.returncode}"
        )
    version_text = version_result.stdout.strip()
    match = re.search(r"\b(\d+\.\d+(?:\.\d+)?)\b", version_text)
    version = match.group(1) if match else (version_text.splitlines()[0] if version_text else "unknown")

    probe = (
        'import coot; print("NASOLVE_COOT_PYTHON_OK"); '
        "coot.coot_no_state_real_exit(0)"
    )
    try:
        probe_result = subprocess.run(
            [
                str(executable),
                "--no-graphics",
                "--no-state-script",
                "--no-startup-scripts",
                "--no-guano",
                "--command",
                probe,
            ],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CootDiscoveryError(f"Could not validate Coot's embedded Python: {exc}") from exc
    if probe_result.returncode or _PYTHON_MARKER not in probe_result.stdout:
        raise CootDiscoveryError(
            "Coot is installed but its headless embedded-Python interface failed validation"
        )
    return CootInstallation(executable, version, source)


def standard_candidates() -> list[Path]:
    candidates: list[Path] = []
    on_path = shutil.which("coot")
    if on_path:
        candidates.append(Path(on_path))
    if sys.platform == "darwin":
        candidates.extend([Path("/opt/homebrew/bin/coot"), Path("/usr/local/bin/coot")])
    elif os.name != "nt":
        candidates.extend([Path("/usr/bin/coot"), Path("/usr/local/bin/coot")])
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.expanduser())
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def discover_coot(
    config: AppConfig,
    explicit: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    candidates: list[Path] | None = None,
) -> CootInstallation:
    env = dict(os.environ if environ is None else environ)
    attempts: list[tuple[str, str | Path]] = []
    if explicit:
        attempts.append(("command-line override", explicit))
    if env.get("NASOLVE_COOT"):
        attempts.append(("NASOLVE_COOT", env["NASOLVE_COOT"]))
    if config.coot.executable:
        attempts.append(("saved configuration", config.coot.executable))
    attempts.extend(
        ("PATH" if index == 0 and shutil.which("coot", path=env.get("PATH")) else "standard location", path)
        for index, path in enumerate(standard_candidates() if candidates is None else candidates)
    )
    errors: list[str] = []
    for source, candidate in attempts:
        try:
            return installation_from_candidate(candidate, source, env)
        except CootDiscoveryError as exc:
            errors.append(f"{source}: {exc}")
    detail = "\n  - ".join(errors) if errors else "no candidates found"
    raise CootDiscoveryError(
        "Coot could not be discovered. Run 'nasolve configure coot PATH'."
        f"\nAttempts:\n  - {detail}"
    )


def remember_coot(config: AppConfig, installation: CootInstallation) -> None:
    config.coot = CootSettings(
        executable=str(installation.executable),
        version=installation.version,
        validated_utc=datetime.now(timezone.utc).isoformat(),
    )


__all__ = [
    "CootDiscoveryError",
    "CootInstallation",
    "discover_coot",
    "installation_from_candidate",
    "remember_coot",
    "standard_candidates",
]
