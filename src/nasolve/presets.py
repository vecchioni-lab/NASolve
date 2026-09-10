"""Strict, portable project policies for campaign planning.

Schema 1 describes only the existing standard W stage path. It cannot supply
commands, Doctor trials, or arbitrary refinement recipes. Loading a preset is
read-only and does not discover external scientific programs or run a stage.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


class PresetError(ValueError):
    """A preset is malformed, unsupported, unreadable, or unsafe."""


@dataclass(frozen=True)
class ProjectPreset:
    """An immutable snapshot of policy, source bytes, and declared resources.

    Mapping properties return fresh dictionaries so callers cannot change the
    loaded policy or its identity. Absolute paths are runtime locators only;
    serialized records and the configuration fingerprint are portable.
    """

    source: Path
    root: Path
    sha256: str
    id: str
    version: str
    source_bytes: bytes = field(repr=False)
    _policy_json: str = field(repr=False)
    _resource_paths: tuple[tuple[str, Path], ...] = field(repr=False)
    _resource_contents: tuple[tuple[str, bytes], ...] = field(repr=False)

    @property
    def automr_defaults(self) -> dict[str, Any]:
        return json.loads(self._policy_json)["automr"]

    @property
    def resources(self) -> dict[str, Path]:
        return dict(self._resource_paths)

    @property
    def resource_bytes(self) -> dict[str, bytes]:
        """Exact resource bytes whose checksums appear in ``to_dict()``."""
        return dict(self._resource_contents)

    @property
    def config_sha256(self) -> str:
        """Hash resolved policy and resources, independent of source location."""
        return hashlib.sha256(self._policy_json.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        result = json.loads(self._policy_json)
        result.update(
            source=self.source.name,
            sha256=self.sha256,
            config_sha256=self.config_sha256,
        )
        return result


_TOP_LEVEL = {
    "schema_version", "id", "version", "description", "automr", "postmr",
    "autosol", "autorefine", "resources",
}
_DEFAULTS: dict[str, dict[str, Any]] = {
    "automr": {
        "mode": "standard", "frame": "W", "mirror": False,
        "allow_p1_standard": False,
    },
    "postmr": {"modified_pairs_only": False},
    "autosol": {"policy": "when-anomalous", "on_unaccepted": "inspect"},
    "autorefine": {"recipe": "AutoRefine/default", "cycles": 5},
}


def _reject_nonfinite(value: Any, location: str = "preset") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise PresetError(f"{location} must not contain nonfinite numbers")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite(item, f"{location}.{key}")
    elif isinstance(value, list):
        for item in value:
            _reject_nonfinite(item, location)


def _unknown_keys(table: dict[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise PresetError(f"Unknown {location} field(s): {', '.join(unknown)}")


def _text(value: Any, location: str, *, empty: bool = False) -> str:
    if type(value) is not str or (not empty and not value.strip()):
        raise PresetError(f"{location} must be a {'nonempty ' if not empty else ''}string")
    return value


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if type(value) is not dict:
        raise PresetError(f"{name} must be a TOML table")
    return value


def _open_snapshot(path: Path) -> int:
    """Open the resolved pathname without following newly introduced symlinks.

    On platforms with openat support, every directory is held by descriptor
    while its child is opened. Thus replacement of an ancestor cannot redirect
    a resource read outside the root checked during resolution.
    """
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"):
        directory_access = getattr(os, "O_PATH", getattr(os, "O_SEARCH", os.O_RDONLY))
        directory_flags = directory_access | os.O_DIRECTORY | os.O_NOFOLLOW
        parent = os.open(path.anchor, directory_flags)
        try:
            for component in path.parts[1:-1]:
                child = os.open(component, directory_flags, dir_fd=parent)
                os.close(parent)
                parent = child
            return os.open(path.name, flags | os.O_NOFOLLOW, dir_fd=parent)
        finally:
            os.close(parent)
    return os.open(path, flags)


def _read_file(path: Path, label: str) -> bytes:
    """Read a regular file once, detecting replacement during the snapshot."""
    try:
        descriptor = _open_snapshot(path)
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise PresetError(f"{label} must be an existing regular file: {path}")
            handle = os.fdopen(descriptor, "rb")
        except BaseException:
            os.close(descriptor)
            raise
        with handle:
            if path.resolve(strict=True) != path:
                raise PresetError(f"{label} changed while being opened: {path}")
            contents = handle.read()
            after = os.fstat(handle.fileno())
        current = path.stat()
        if path.resolve(strict=True) != path:
            raise PresetError(f"{label} changed while being read: {path}")
    except (OSError, RuntimeError) as exc:
        raise PresetError(f"Cannot read {label} {path}: {exc}") from exc
    identity = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise PresetError(f"{label} changed while being read: {path}")
    return contents


def _resource_path(root: Path, value: Any, name: str) -> tuple[str, Path]:
    value = _text(value, f"resources.{name}")
    relative = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        relative.is_absolute() or windows.drive or windows.root
        or "\\" in value or ".." in relative.parts or "\x00" in value
        or str(relative) == "."
    ):
        raise PresetError(f"resources.{name} must be a relative path under the preset root")
    try:
        path = (root / relative).resolve(strict=True)
        path.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PresetError(
            f"resources.{name} must name an existing file under the preset root: {value}"
        ) from exc
    return relative.as_posix(), path


def load_preset(source: str | Path = "5w6w") -> ProjectPreset:
    """Load builtin ``5w6w`` or a TOML file with resources relative to its root.

    Schema version, id, and version are required. Omitted stage tables or
    fields use the bounded schema-1 defaults. Ordered pair tokens are checked
    for syntax here; the existing AutoMR resolver validates their chemistry.
    """
    if not isinstance(source, (str, Path)):
        raise PresetError("Preset source must be a builtin name or TOML file path")
    try:
        if source == "5w6w":
            path = Path(__file__).parent / "data" / "presets" / "5w6w.toml"
        else:
            path = Path(source).expanduser()
        path = path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PresetError(f"Cannot locate preset {source!s}: {exc}") from exc
    contents = _read_file(path, "Preset")
    try:
        data = tomllib.loads(contents.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PresetError(f"Invalid preset TOML in {path.name}: {exc}") from exc
    _reject_nonfinite(data)
    _unknown_keys(data, _TOP_LEVEL, "preset")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise PresetError("Unsupported preset schema_version; expected integer 1")
    preset_id = _text(data.get("id"), "id")
    version = _text(data.get("version"), "version")
    policy: dict[str, Any] = {
        "schema_version": 1, "id": preset_id, "version": version,
        "description": _text(data.get("description", ""), "description", empty=True),
    }
    for name, defaults in _DEFAULTS.items():
        supplied = _table(data, name)
        allowed = set(defaults) | ({"pair"} if name == "automr" else set())
        _unknown_keys(supplied, allowed, name)
        resolved = {**defaults, **supplied}
        for key, default in defaults.items():
            value = resolved[key]
            if type(value) is not type(default):
                raise PresetError(f"{name}.{key} must be {type(default).__name__}")
            if type(default) is not bool and value != default:
                raise PresetError(f"Unsupported {name}.{key}: expected {default!r}")
        if name == "automr" and "pair" in resolved:
            pair = _text(resolved["pair"], "automr.pair")
            parts = [part.strip() for part in pair.split(":")]
            if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9]+", part) for part in parts):
                raise PresetError("automr.pair must contain two residue tokens: FIRST:SECOND")
            resolved["pair"] = ":".join(parts)
        policy[name] = resolved

    root = path.parent
    resource_paths = []
    resource_contents = []
    resource_records = {}
    for name, value in sorted(_table(data, "resources").items()):
        _text(name, "resource name")
        relative, resource = _resource_path(root, value, name)
        resource_data = _read_file(resource, f"Resource {name!r}")
        resource_paths.append((name, resource))
        resource_contents.append((name, resource_data))
        resource_records[name] = {
            "relative_path": relative,
            "sha256": hashlib.sha256(resource_data).hexdigest(),
            "size": len(resource_data),
        }
    policy["resources"] = resource_records
    return ProjectPreset(
        source=path, root=root, sha256=hashlib.sha256(contents).hexdigest(),
        id=preset_id, version=version, source_bytes=contents,
        _policy_json=json.dumps(policy, sort_keys=True, separators=(",", ":"), allow_nan=False),
        _resource_paths=tuple(resource_paths), _resource_contents=tuple(resource_contents),
    )


__all__ = ["PresetError", "ProjectPreset", "load_preset"]
