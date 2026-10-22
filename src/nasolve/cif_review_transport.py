"""Portable transport for opaque Coot diagnostics in preserved review capsules.

Scientific references keep their stricter path rules. Only timestamped Coot
backup names have a logical-name exception; their gzip payloads are never opened.
Historical names and bytes return unchanged to the next archive, while newly
owned backups receive portable names with explicit normalization provenance.
"""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata

POLICY_ID = "cif-review-diagnostic-transport-v1"
_METADATA = ".review-transport"
_INDEX = "index.json"
_PROVENANCE = "postmr_construction/diagnostic_transport.json"
_BACKUP = re.compile(
    r"(?:inputs/review/)*postmr_construction/model/Coot/backups/"
    r"[A-Za-z0-9][A-Za-z0-9_.-]*_"
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)_"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)_"
    r"(?:0?[1-9]|[12][0-9]|3[01])_"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]_"
    r"(?:19|20)[0-9]{2}_modification_(?:0|[1-9][0-9]*)\.pdb\.gz\Z"
)
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _strict(name: object) -> bool:
    return (isinstance(name, str) and bool(name) and not name.startswith("/")
            and "\\" not in name and ":" not in name
            and not any(ord(c) < 32 or ord(c) == 127 for c in name)
            and all(p not in {"", ".", ".."} and p.casefold() != _METADATA for p in name.split("/")))


def is_safe_review_member(name: object) -> bool:
    """Accept strict relative files or the exact historical Coot backup grammar."""
    return _strict(name) or (isinstance(name, str) and _BACKUP.fullmatch(name) is not None)


def _alias(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def _unique(names) -> None:
    aliases = {}
    for name in names:
        alias = _alias(name)
        if alias in aliases:
            raise ValueError("Colliding diagnostic transport names")
        aliases[alias] = name
    for name in aliases:
        if any(str(p) in aliases for p in PurePosixPath(name).parents if str(p) != "."):
            raise ValueError("Diagnostic transport file/directory collision")


def _root(path: Path, *, create=False) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Diagnostic transport root cannot be a symlink")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise ValueError("Diagnostic transport root must be a directory")
    # Canonicalize an owned root, permitting system aliases such as macOS /var.
    return path.resolve()


def _path(root: Path, relative: str, *, owned_backup=False) -> Path:
    ordinary = relative.removeprefix(_METADATA + "/") if relative.startswith(_METADATA + "/") else relative
    if not _strict(ordinary) and not (owned_backup and not relative.startswith("inputs/review/") and _BACKUP.fullmatch(relative)):
        raise ValueError("Unsafe physical diagnostic path")
    path = root / PurePosixPath(relative)
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Diagnostic transport cannot traverse a symlink")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Diagnostic path escapes its owned root")
    return path


def _read(root: Path, relative: str, *, owned_backup=False) -> bytes:
    path = _path(root, relative, owned_backup=owned_backup)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("Require a regular diagnostic file")
        return handle.read()


def _parse_json(data: bytes):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate diagnostic transport JSON key")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique_object)


def _json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _row(logical: str, data: bytes) -> dict:
    return {"physical": _METADATA + "/objects/" + sha256(logical.encode()).hexdigest() + ".pdb.gz",
            "sha256": sha256(data).hexdigest(), "size": len(data)}


def _load_index(root: Path) -> dict:
    directory = root / _METADATA
    if not directory.exists() and not directory.is_symlink():
        return {}
    try:
        value = _parse_json(_read(root, _METADATA + "/" + _INDEX))
        if set(value) != {"policy_id", "members"} or value["policy_id"] != POLICY_ID or not isinstance(value["members"], dict) or not value["members"]:
            raise ValueError("Invalid diagnostic transport index")
        rows = value["members"]
        _unique(rows)
        expected = {_METADATA + "/" + _INDEX}
        for logical, row in rows.items():
            if not isinstance(logical, str) or not _BACKUP.fullmatch(logical) or not isinstance(row, dict) or set(row) != {"physical", "sha256", "size"}:
                raise ValueError("Invalid diagnostic transport index row")
            physical = _row(logical, b"")["physical"]
            if row["physical"] != physical or not isinstance(row["sha256"], str) or not _SHA.fullmatch(row["sha256"]) or type(row["size"]) is not int or row["size"] < 0:
                raise ValueError("Invalid diagnostic transport binding")
            data = _read(root, physical)
            if len(data) != row["size"] or sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("Staged diagnostic bytes changed")
            expected.add(physical)
        actual = set()
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError("Diagnostic transport metadata cannot contain symlinks")
            if path.is_file():
                actual.add(path.relative_to(root).as_posix())
            elif not path.is_dir() or path.relative_to(root).as_posix() != _METADATA + "/objects":
                raise ValueError("Unexpected diagnostic transport node")
        if actual != expected:
            raise ValueError("Unexpected diagnostic transport metadata inventory")
        return rows
    except (OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid diagnostic transport index") from exc


def stage_review_members(members: Mapping[str, bytes], target: Path) -> dict[str, str]:
    """Write a fresh owned copy without materializing historical colon names."""
    if not isinstance(members, Mapping) or any(not is_safe_review_member(n) or not isinstance(d, bytes) for n, d in members.items()):
        raise ValueError("Unsafe diagnostic review member")
    _unique(members)
    mapping = {n: _row(n, d)["physical"] if ":" in n else n for n, d in members.items()}
    _unique(mapping.values())
    root = _root(target, create=True)
    if any(root.iterdir()):
        raise ValueError("Review staging requires a fresh empty owned directory")
    rows = {}
    for logical, data in members.items():
        physical = mapping[logical]
        path = _path(root, physical)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(data)
        if physical != logical:
            rows[logical] = _row(logical, data)
    if rows:
        (root / _METADATA / _INDEX).write_bytes(_json_bytes({"policy_id": POLICY_ID, "members": rows}))
    return mapping


def read_staged_review_member(target: Path, logical: str) -> bytes:
    """Read an original logical member while checking its portable byte binding."""
    if not is_safe_review_member(logical):
        raise ValueError("Unsafe diagnostic review member")
    root = _root(target)
    if ":" not in logical:
        return _read(root, logical)
    rows = _load_index(root)
    if logical not in rows:
        raise ValueError("Missing staged logical diagnostic member")
    return _read(root, rows[logical]["physical"])


def _files(root: Path, destination: Path) -> list[Path]:
    result = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        if parent == root:
            dirs[:] = [d for d in dirs if d != "runtime"]
        for name in dirs + files:
            path = parent / name
            if path.is_symlink():
                raise ValueError("Unexpected output symlink")
            if name.casefold() == _METADATA:
                if name != _METADATA or not path.is_dir():
                    raise ValueError("Reserved diagnostic transport namespace")
                _load_index(parent)
        for name in files:
            path = parent / name
            if path == destination or path.suffix in {".pyc", ".pkl", ".pickle"}:
                continue
            if not path.is_file():
                raise ValueError("Unexpected output node")
            result.append(path)
    return sorted(result)


def _provenance_rows(root: Path) -> list[dict]:
    path = root / _PROVENANCE
    if not path.exists():
        return []
    try:
        value = _parse_json(_read(root, _PROVENANCE))
        if set(value) != {"policy_id", "normalized_owned_backups"} or value["policy_id"] != POLICY_ID or not isinstance(value["normalized_owned_backups"], list) or not value["normalized_owned_backups"]:
            raise ValueError("Invalid owned diagnostic normalization provenance")
        rows = value["normalized_owned_backups"]
        _unique(row["path"] for row in rows)
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"original_name", "path", "sha256", "size"}:
                raise ValueError("Invalid owned diagnostic normalization row")
            original = row["original_name"]
            if not isinstance(original, str) or original.startswith("inputs/review/") or not _BACKUP.fullmatch(original) or row["path"] != original.replace(":", "_"):
                raise ValueError("Invalid owned diagnostic normalization name")
            data = _read(root, row["path"])
            if type(row["size"]) is not int or len(data) != row["size"] or sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("Owned normalized diagnostic bytes changed")
        return rows
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid owned diagnostic normalization provenance") from exc


def review_archive_files(session: Path, destination: Path) -> dict[str, bytes]:
    """Collect logical archive bytes; normalize only this session's new backups.

    The caller writes the ZIP and its ordinary manifest. Portable staging indexes
    remain local metadata and are never inserted into preserved parent evidence.
    """
    root = _root(session)
    destination = Path(destination).absolute()
    if destination.is_symlink() or any(p.is_symlink() and p.resolve().is_relative_to(root) for p in destination.parents):
        raise ValueError("Review archive destination cannot traverse an owned symlink")
    # Resolve only the parent after checking owned links. External system aliases
    # such as /var may name the same session without changing its file identity.
    destination = destination.parent.resolve() / destination.name
    if not destination.is_relative_to(root):
        raise ValueError("Review archive destination must remain inside its session")
    paths = _files(root, destination)
    logical_files = {}
    metadata_roots = {root.joinpath(*p.relative_to(root).parts[:p.relative_to(root).parts.index(_METADATA)])
                      for p in paths if _METADATA in p.relative_to(root).parts}
    for metadata_root in sorted(metadata_roots):
        prefix = metadata_root.relative_to(root).as_posix()
        prefix = "" if prefix == "." else prefix + "/"
        rows = _load_index(metadata_root)
        for logical, row in rows.items():
            name = prefix + logical
            if not is_safe_review_member(name) or name in logical_files:
                raise ValueError("Unsafe or colliding restored diagnostic name")
            logical_files[name] = _read(metadata_root, row["physical"])
    ordinary = [p for p in paths if _METADATA not in p.relative_to(root).parts]
    rows = _provenance_rows(root)
    normalization = []
    for path in ordinary:
        name = path.relative_to(root).as_posix()
        if ":" in name:
            if name.startswith("inputs/review/") or not _BACKUP.fullmatch(name):
                raise ValueError("Unsafe unindexed diagnostic output")
            safe = name.replace(":", "_")
            target = _path(root, safe)
            if target.exists() or target.is_symlink():
                raise ValueError("Normalized diagnostic output collision")
            data = _read(root, name, owned_backup=True)
            normalization.append((path, target, {"original_name": name, "path": safe, "sha256": sha256(data).hexdigest(), "size": len(data)}))
        elif not _strict(name):
            raise ValueError("Unsafe diagnostic output name")
    proposed = list(logical_files) + [p.relative_to(root).as_posix().replace(":", "_") for p in ordinary]
    if normalization and not (root / _PROVENANCE).exists():
        proposed.append(_PROVENANCE)
    _unique(proposed)
    for source, target, row in normalization:
        source.rename(target)
        rows.append(row)
    if normalization:
        provenance = root / _PROVENANCE
        provenance.parent.mkdir(parents=True, exist_ok=True)
        provenance.write_bytes(_json_bytes({"policy_id": POLICY_ID, "normalized_owned_backups": rows}))
    for path in _files(root, destination):
        name = path.relative_to(root).as_posix()
        if _METADATA not in PurePosixPath(name).parts:
            logical_files[name] = _read(root, name)
    _unique(logical_files)
    return dict(sorted(logical_files.items()))
