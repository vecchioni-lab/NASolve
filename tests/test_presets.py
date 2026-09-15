import hashlib
import json
import shutil
import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from nasolve.presets import PresetError, ProjectPreset, load_preset
from nasolve import presets


MINIMAL = 'schema_version = 1\nid = "custom"\nversion = "2.0"\n'


def write_preset(root: Path, contents: str = MINIMAL) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "project.toml"
    path.write_text(contents, encoding="utf-8")
    return path


def test_packaged_preset_declares_existing_standard_policy():
    preset = load_preset()
    assert isinstance(preset, ProjectPreset)
    assert preset.id == "5w6w"
    assert preset.version == "1.1.0"
    assert preset.terminal_phosphate_sites == ("D:1",)
    assert preset.source.name == "5w6w.toml"
    assert preset.root == preset.source.parent
    assert preset.automr_defaults == {
        "mode": "standard", "frame": "W", "mirror": False,
        "allow_p1_standard": False,
    }
    assert preset.to_dict()["autorefine"] == {"recipe": "AutoRefine/default", "cycles": 5}
    assert preset.to_dict()["autosol"] == {"policy": "when-anomalous", "on_unaccepted": "inspect"}
    assert preset.sha256 == hashlib.sha256(preset.source.read_bytes()).hexdigest()
    assert preset.resources == {}
    assert str(preset.root) not in json.dumps(preset.to_dict())


def test_custom_preset_resolves_defaults_and_freezes_resources(tmp_path):
    path = write_preset(tmp_path, MINIMAL + '''
[automr]
pair = " E : iC "
mirror = true
allow_p1_standard = true
[postmr]
modified_pairs_only = true
[resources]
sequence = "files/sequence.txt"
''')
    resource = tmp_path / "files" / "sequence.txt"
    resource.parent.mkdir()
    resource.write_bytes(b">A\nACGT\n")
    preset = load_preset(path)
    original = preset.to_dict()
    assert preset.automr_defaults["pair"] == "E:iC"
    assert preset.automr_defaults["mirror"] is True
    assert preset.automr_defaults["allow_p1_standard"] is True
    assert original["postmr"]["modified_pairs_only"] is True
    assert preset.resources == {"sequence": resource.resolve()}
    assert original["resources"]["sequence"] == {
        "relative_path": "files/sequence.txt",
        "sha256": hashlib.sha256(b">A\nACGT\n").hexdigest(),
        "size": 8,
    }
    path.write_text("changed", encoding="utf-8")
    resource.write_bytes(b"changed")
    assert preset.to_dict() == original
    assert preset.resource_bytes == {"sequence": b">A\nACGT\n"}
    assert preset.sha256 == hashlib.sha256(preset.source_bytes).hexdigest()
    preset.automr_defaults["mirror"] = False
    preset.resources.clear()
    preset.resource_bytes.clear()
    original["automr"]["frame"] = "3GBI"
    assert preset.automr_defaults["mirror"] is True
    assert preset.automr_defaults["frame"] == "W"
    assert preset.resources == {"sequence": resource.resolve()}
    with pytest.raises(FrozenInstanceError):
        preset.id = "changed"


def test_portable_identity_survives_relocation_and_removed_original(tmp_path):
    source = tmp_path / "original"
    path = write_preset(source, MINIMAL + '[resources]\nsequence = "sequence.txt"\n')
    (source / "sequence.txt").write_bytes(b">A\nACGT\n")
    before = load_preset(path)
    destination = tmp_path / "relocated"
    shutil.copytree(source, destination)
    shutil.rmtree(source)
    after = load_preset(destination / "project.toml")
    assert before.to_dict() == after.to_dict()
    assert before.config_sha256 == after.config_sha256
    assert before.resources != after.resources
    assert after.resources["sequence"].is_file()
    (destination / "sequence.txt").write_bytes(b">A\nTGCA\n")
    changed_resource = load_preset(destination / "project.toml")
    assert after.sha256 == changed_resource.sha256
    assert after.config_sha256 != changed_resource.config_sha256


def test_configuration_hash_ignores_toml_formatting_and_resolves_defaults(tmp_path):
    a = load_preset(write_preset(tmp_path / "a"))
    b = load_preset(write_preset(tmp_path / "b", '# Comment\n' + MINIMAL + '''
[autorefine]
cycles = 5
recipe = "AutoRefine/default"
[automr]
frame = "W"
mode = "standard"
'''))
    assert a.sha256 != b.sha256
    assert a.config_sha256 == b.config_sha256


@pytest.mark.parametrize("field", [
    'schema_version = 2', 'schema_version = true', 'schema_version = 1.0',
    'schema_version = "1"', 'schema_version = 0',
])
def test_rejects_unsupported_schema_versions_and_wrong_types(tmp_path, field):
    path = write_preset(tmp_path, MINIMAL.replace("schema_version = 1", field))
    with pytest.raises(PresetError, match="schema_version"):
        load_preset(path)


@pytest.mark.parametrize("suffix,diagnostic", [
    ('extra = true\n', "Unknown preset"),
    ('[doctor]\npolicy = "auto"\n', "Unknown preset"),
    ('[automr]\nexecute = true\n', "Unknown automr"),
    ('[postmr]\ncommand = "anything"\n', "Unknown postmr"),
    ('[automr]\nmode = "nonstandard"\n', "Unsupported automr.mode"),
    ('[automr]\nframe = "3GBI"\n', "Unsupported automr.frame"),
    ('[automr]\nmirror = "false"\n', "automr.mirror must be bool"),
    ('[automr]\nallow_p1_standard = 1\n', "automr.allow_p1_standard must be bool"),
    ('[postmr]\nmodified_pairs_only = 0\n', "postmr.modified_pairs_only must be bool"),
    ('[autosol]\npolicy = "always"\n', "Unsupported autosol.policy"),
    ('[autosol]\non_unaccepted = "continue"\n', "Unsupported autosol.on_unaccepted"),
    ('[autorefine]\nrecipe = "arbitrary"\n', "Unsupported autorefine.recipe"),
    ('[autorefine]\ncycles = true\n', "autorefine.cycles must be int"),
    ('[autorefine]\ncycles = 1\n', "Unsupported autorefine.cycles"),
    ('[autorefine]\ncycles = 5.0\n', "autorefine.cycles must be int"),
    ('[autorefine]\ncycles = inf\n', "nonfinite"),
    ('[autorefine]\ncycles = nan\n', "nonfinite"),
    ('automr = "standard"\n', "automr must be a TOML table"),
    ('[automr]\npair = "E:G:Q"\n', "FIRST:SECOND"),
    ('[automr]\npair = "E:"\n', "FIRST:SECOND"),
    ('[automr]\npair = true\n', "automr.pair must be a nonempty string"),
    ('[resources]\nfile = 3\n', "resources.file must be a nonempty string"),
])
def test_rejects_unknown_fields_policies_and_wrong_types(tmp_path, suffix, diagnostic):
    with pytest.raises(PresetError, match=diagnostic):
        load_preset(write_preset(tmp_path, MINIMAL + suffix))


@pytest.mark.parametrize("contents", [
    '[broken', MINIMAL + 'id = "duplicate"\n',
    'id = "missing-schema"\nversion = "1"\n',
    'schema_version = 1\nversion = "1"\n',
    'schema_version = 1\nid = "test"\nversion = 1\n',
    'schema_version = 1\nid = ""\nversion = "1"\n',
])
def test_rejects_malformed_or_incomplete_toml(tmp_path, contents):
    with pytest.raises(PresetError):
        load_preset(write_preset(tmp_path, contents))


@pytest.mark.parametrize("resource", [
    "../outside.txt", "nested/../../outside.txt", "/tmp/outside.txt",
    "C:/outside.txt", "C:outside.txt", "\\\\server\\share\\file", ".", "",
    "nested\\outside.txt", "missing.txt",
])
def test_rejects_unsafe_and_missing_resources(tmp_path, resource):
    # JSON basic strings are also valid TOML for this set of path strings.
    path = write_preset(tmp_path / "preset", MINIMAL + f'[resources]\nfile = {json.dumps(resource)}\n')
    (tmp_path / "outside.txt").write_bytes(b"outside")
    with pytest.raises(PresetError, match="resources.file"):
        load_preset(path)


def test_rejects_symlink_escape_but_allows_contained_symlinks(tmp_path):
    root = tmp_path / "preset"
    path = write_preset(root, MINIMAL + '[resources]\nfile = "linked.txt"\n')
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside")
    linked = root / "linked.txt"
    linked.symlink_to(outside)
    with pytest.raises(PresetError, match="under the preset root"):
        load_preset(path)
    linked.unlink()
    local = root / "local.txt"
    local.write_bytes(b"inside")
    linked.symlink_to(local)
    assert load_preset(path).resource_bytes == {"file": b"inside"}


def test_rejects_directory_resource_unreadable_source_and_invalid_utf8(tmp_path):
    path = write_preset(tmp_path, MINIMAL + '[resources]\nfile = "directory"\n')
    (tmp_path / "directory").mkdir()
    with pytest.raises(PresetError, match="regular file"):
        load_preset(path)
    for source in (tmp_path, tmp_path / "missing.toml", 42):
        with pytest.raises(PresetError):
            load_preset(source)
    path.write_bytes(b"\xff")
    with pytest.raises(PresetError, match="Invalid preset TOML"):
        load_preset(path)


def test_expansion_errors_are_guarded(tmp_path, monkeypatch):
    def unavailable_home(path):
        raise RuntimeError("Could not determine home directory")
    monkeypatch.setattr(Path, "expanduser", unavailable_home)
    with pytest.raises(PresetError, match="Cannot locate preset"):
        load_preset("~unknown/project.toml")


@pytest.mark.skipif(os.open not in os.supports_dir_fd, reason="requires openat")
@pytest.mark.parametrize("replace_directory", [False, True])
def test_rejects_resource_symlink_replacement_before_open(tmp_path, monkeypatch, replace_directory):
    root = tmp_path / "preset"
    path = write_preset(root, MINIMAL + '[resources]\nfile = "files/sequence.txt"\n')
    directory = root / "files"
    directory.mkdir()
    resource = directory / "sequence.txt"
    resource.write_bytes(b"inside")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "sequence.txt").write_bytes(b"outside")
    ordinary_open = presets._open_snapshot

    def replace_then_open(candidate):
        if candidate == resource:
            if replace_directory:
                directory.rename(root / "original_files")
                directory.symlink_to(outside, target_is_directory=True)
            else:
                resource.unlink()
                resource.symlink_to(outside / "sequence.txt")
        return ordinary_open(candidate)

    monkeypatch.setattr(presets, "_open_snapshot", replace_then_open)
    with pytest.raises(PresetError, match="Cannot read Resource"):
        load_preset(path)
