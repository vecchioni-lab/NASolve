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
class CootSettings:
    executable: str | None = None
    version: str | None = None
    validated_utc: str | None = None


@dataclass
class WorkspaceSettings:
    dataset: str | None = None
    run: str | None = None


@dataclass
class AppConfig:
    schema_version: int = 1
    phenix: PhenixSettings = field(default_factory=PhenixSettings)
    coot: CootSettings = field(default_factory=CootSettings)
    workspace: WorkspaceSettings = field(default_factory=WorkspaceSettings)


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
        if not isinstance(payload, Mapping):
            raise TypeError("configuration root must be a JSON object")
        phenix_payload = payload.get("phenix", {})
        coot_payload = payload.get("coot", {})
        workspace_payload = payload.get("workspace", {})
        if not isinstance(phenix_payload, Mapping):
            raise TypeError("phenix configuration must be a JSON object")
        if not isinstance(coot_payload, Mapping):
            raise TypeError("coot configuration must be a JSON object")
        if not isinstance(workspace_payload, Mapping):
            raise TypeError("workspace configuration must be a JSON object")
        workspace_dataset = workspace_payload.get("dataset")
        workspace_run = workspace_payload.get("run")
        if workspace_dataset is not None and not isinstance(workspace_dataset, str):
            raise TypeError("workspace dataset must be a string or null")
        if workspace_run is not None and not isinstance(workspace_run, str):
            raise TypeError("workspace run must be a string or null")
        executables = phenix_payload.get("executables", {})
        if not isinstance(executables, Mapping) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in executables.items()
        ):
            raise TypeError("phenix executables must be a string-to-string object")
        return AppConfig(
            schema_version=int(payload.get("schema_version", 1)),
            phenix=PhenixSettings(
                root=phenix_payload.get("root"),
                setup_script=phenix_payload.get("setup_script"),
                version=phenix_payload.get("version"),
                executables=dict(executables),
                validated_utc=phenix_payload.get("validated_utc"),
            ),
            coot=CootSettings(
                executable=coot_payload.get("executable"),
                version=coot_payload.get("version"),
                validated_utc=coot_payload.get("validated_utc"),
            ),
            workspace=WorkspaceSettings(
                dataset=workspace_dataset,
                run=workspace_run,
            ),
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read NASolve configuration {config_path}: {exc}") from exc


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    """Atomically save configuration so interruption cannot leave half a file."""
    config_path = default_config_path() if path is None else Path(path)
    temporary: Path | None = None
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(asdict(config), indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=config_path.parent,
            prefix=".nasolve-", suffix=".tmp", delete=False,
        ) as handle:
            handle.write(data)
            temporary = Path(handle.name)
        os.replace(temporary, config_path)
    except (OSError, TypeError) as exc:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise ConfigError(f"Could not save NASolve configuration {config_path}: {exc}") from exc
    return config_path
