"""Keep the public workflow examples usable as the CLI evolves."""
import json
from pathlib import Path

import pytest

from nasolve import __version__
from nasolve.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]


def test_released_commands_and_guide_paths():
    guide = json.loads((ROOT / "docs/current-behavior.json").read_text(encoding="utf-8"))
    assert guide["nasolve_version"] == __version__
    parser = build_parser()
    parser.parse_args(guide["install"]["check_argv"][1:])
    for key, workflow in guide["workflows"].items():
        entry, *arguments = workflow["argv"]
        assert entry in guide["install"]["entry_points"], key
        assert (ROOT / workflow["guide"].partition("#")[0]).is_file(), key
        if entry == "nasolve":
            parser.parse_args(arguments)


def test_documented_sticky_end_inspection(tmp_path, capsys):
    pytest.importorskip("gemmi")
    from nasolve.topostitch_inspect import main
    from .test_topostitch_inspect import inputs

    guide = json.loads((ROOT / "docs/current-behavior.json").read_text(encoding="utf-8"))
    entry, *arguments = guide["workflows"]["sticky_end_candidates"]["argv"]
    assert entry == "nasolve-topostitch-inspect"
    model, manifest, _ = inputs(tmp_path)
    paths = {"MODEL.pdb": str(model), "ENDS.json": str(manifest)}
    assert main([paths.get(arg, arg) for arg in arguments]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["periodic_screening"]["candidates"]
    assert result["changes"] == []
