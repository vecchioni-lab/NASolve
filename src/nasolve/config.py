"""Persistent, user-level NASolve configuration."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping


class ConfigError(RuntimeError):
    """Raised when NASolve's saved configuration cannot be read or written."""


@dataclass
class PhenixSettings:
    root: str | None = None
    setup_script: str | None = None
    version: str | None = None
    executables: dict[str, str] = field(default_factory=dict)
    validated_utc: str | None = None


@dataclass
class AppConfig:
    schema_version: int = 1
    phenix: PhenixSettings = field(default_factory=PhenixSettings)


def default_config_path(
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return a platform-appropriate user config path without external packages."""
    env = os.environ if environ is None else environ
    override = env.get("NASOLVE_CONFIG_FILE")
    if override:
        return Path(override).expanduser()

    user_home = Path.home() if home is None else home
    if sys.platform == "darwin":
        return user_home / "Library" / "Application Support" / "NASolve" / "config.json"
    if os.name == "nt":
        base = Path(env.get("APPDATA", user_home / "AppData" / "Roaming"))
        return base / "NASolve" / "config.json"
    base = Path(env.get("XDG_CONFIG_HOME", user_home / ".config"))
    return base / "nasolve" / "config.json"


def load_config(path: Path | None = None) -> AppConfig:
    config_path = default_config_path() if path is None else Path(path)
    if not config_path.exists():
        return AppConfig()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        phenix_payload = payload.get("phenix", {})
        return AppConfig(
            schema_version=int(payload.get("schema_version", 1)),
            phenix=PhenixSettings(
                root=phenix_payload.get("root"),
                setup_script=phenix_payload.get("setup_script"),
                version=phenix_payload.get("version"),
                executables=dict(phenix_payload.get("executables", {})),
                validated_utc=phenix_payload.get("validated_utc"),
            ),
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read NASolve configuration {config_path}: {exc}") from exc


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    """Atomically save configuration so interruption cannot leave half a file."""
    config_path = default_config_path() if path is None else Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(asdict(config), indent=2, sort_keys=True) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=config_path.parent,
            prefix=".nasolve-", suffix=".tmp", delete=False,
        ) as handle:
            handle.write(data)
            temporary = Path(handle.name)
        os.replace(temporary, config_path)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise ConfigError(f"Could not save NASolve configuration {config_path}: {exc}") from exc
    return config_path
