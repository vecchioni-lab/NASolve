"""Explicit generation discovers optional native tools without adopting or saving."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from nasolve.cli import build_parser, main
from nasolve.config import AppConfig
from nasolve.phenix_runtime import (
    PhenixDiscoveryError, REQUIRED_PROGRAMS, discover_phenix,
)


NATIVE_OVERRIDES = (
    "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CCP4", "CLIBD_MON", "LIBMOL_ROOT",
    "__PYVENV_LAUNCHER__", "PYTHONEXECUTABLE", "PYTHONUSERBASE",
)


def _installation(tmp_path, *, elbow=True):
    executable = tmp_path / "native-bin" / "phenix.elbow"
    return SimpleNamespace(
        version="2.2.1-6174", environment={"PATH": "validated-native-path"},
        executables={"phenix.elbow": executable} if elbow else {},
    )


def _arguments(tmp_path, *extra):
    return ["--phenix-root", str(tmp_path / "explicit-phenix"), "cif-doctor",
            "generate-candidate", str(tmp_path / "source" / "source.cif"),
            "--code", "TST", "--output-parent", str(tmp_path / "candidates"), *extra]


def test_candidate_parser_requires_explicit_inputs_and_defaults_timeout():
    parser = build_parser()
    args = parser.parse_args(["cif-doctor", "generate-candidate", "source.cif",
                              "--code", "TST", "--output-parent", "candidates"])
    assert args.source == Path("source.cif")
    assert args.output_parent == Path("candidates")
    assert args.timeout_seconds == 600
    for arguments in (["cif-doctor", "generate-candidate", "source.cif"],
                      ["cif-doctor", "generate-candidate", "source.cif", "--code", "TST"]):
        with pytest.raises(SystemExit) as raised:
            parser.parse_args(arguments)
        assert raised.value.code == 2


@pytest.mark.parametrize("status, expected_exit", [
    ("CANDIDATE_REVIEW", 0), ("REJECTED", 2), ("FAILED", 2),
])
def test_candidate_dispatch_and_exit_status_preserve_configuration(tmp_path, monkeypatch, capsys,
                                                                  status, expected_exit):
    config_path = tmp_path / "config.json"
    saved = {"schema_version": 1,
             "phenix": {"root": "/previous/phenix", "executables": {}},
             "workspace": {"dataset": "/previous/dataset", "run": "/previous/run"}}
    config_path.write_text(json.dumps(saved))
    original = config_path.read_bytes()
    monkeypatch.setenv("NASOLVE_CONFIG_FILE", str(config_path))
    installation = _installation(tmp_path)
    receipt = {"schema_version": 1, "audit_kind": "cif_numerical_generation_candidate",
               "status": status, "automatic_adoption": False, "readyset_retry": "NOT_RUN",
               "candidate_directory": str(tmp_path / "fresh-candidate"),
               "receipt": {"anchor": "candidate_directory", "path": "generation_receipt.json"}}
    with patch("nasolve.cli.discover_phenix", return_value=installation) as discover, \
            patch("nasolve.cif_generation.generate_elbow_candidate", return_value=receipt) as generate, \
            patch("nasolve.cli.save_config") as save, \
            patch("nasolve.cli.remember_phenix") as remember:
        assert main(_arguments(tmp_path, "--timeout-seconds", "41", "--json")) == expected_exit
    assert json.loads(capsys.readouterr().out) == receipt
    config, = discover.call_args.args
    assert config.workspace.run == "/previous/run"
    assert discover.call_args.kwargs["explicit"] == str(tmp_path / "explicit-phenix")
    generate.assert_called_once_with(
        (tmp_path / "source" / "source.cif").resolve(), "TST", (tmp_path / "candidates").resolve(),
        installation.executables["phenix.elbow"], environment=installation.environment,
        phenix_version="2.2.1-6174", timeout_seconds=41,
    )
    save.assert_not_called()
    remember.assert_not_called()
    assert config_path.read_bytes() == original


def test_only_native_environment_copy_is_sanitized(tmp_path, monkeypatch, capsys):
    for name in NATIVE_OVERRIDES:
        monkeypatch.setenv(name, "caller-" + name)
    monkeypatch.setenv("PRESERVED_CUSTOM_SETTING", "preserve-me")
    before = dict(os.environ)
    config = AppConfig()
    installation = _installation(tmp_path)
    payload = {"status": "CANDIDATE_REVIEW", "automatic_adoption": False}
    with patch("nasolve.cli.load_config", return_value=config), \
            patch("nasolve.cli.discover_phenix", return_value=installation) as discover, \
            patch("nasolve.cif_generation.generate_elbow_candidate", return_value=payload):
        assert main(_arguments(tmp_path, "--json")) == 0
    base = discover.call_args.kwargs["environ"]
    assert all(name not in base for name in NATIVE_OVERRIDES)
    assert base["PRESERVED_CUSTOM_SETTING"] == "preserve-me"
    assert base["PATH"] == before["PATH"]
    assert dict(os.environ) == before
    assert json.loads(capsys.readouterr().out) == payload


def test_missing_optional_elbow_fails_without_generation_or_output(tmp_path, capsys):
    with patch("nasolve.cli.load_config", return_value=AppConfig()), \
            patch("nasolve.cli.discover_phenix", return_value=_installation(tmp_path, elbow=False)), \
            patch("nasolve.cif_generation.generate_elbow_candidate") as generate:
        assert main(_arguments(tmp_path, "--json")) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAILED"
    assert payload["execution"]["status"] == "NOT_RUN"
    assert "phenix.elbow" in payload["error"]
    generate.assert_not_called()
    assert not (tmp_path / "candidates").exists()


@pytest.mark.parametrize("failure", [PhenixDiscoveryError("No native installation"),
                                      OSError("Missing source"), ValueError("Unsupported input")])
def test_preexecution_errors_are_machine_readable_failed_results(tmp_path, capsys, failure):
    with patch("nasolve.cli.load_config", return_value=AppConfig()), \
            patch("nasolve.cli.discover_phenix", side_effect=failure), \
            patch("nasolve.cif_generation.generate_elbow_candidate") as generate:
        assert main(_arguments(tmp_path, "--json")) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAILED"
    assert payload["execution"]["status"] == "NOT_RUN"
    assert payload["automatic_adoption"] is False
    assert payload["error"] == str(failure)
    generate.assert_not_called()


@pytest.mark.parametrize("timeout", ["0", "-1"])
def test_invalid_timeout_is_rejected_before_native_discovery(tmp_path, capsys, timeout):
    with patch("nasolve.cli.discover_phenix") as discover:
        assert main(_arguments(tmp_path, "--timeout-seconds", timeout, "--json")) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "FAILED"
    discover.assert_not_called()


def test_text_result_calls_candidate_review_without_scientific_pass(tmp_path, capsys):
    payload = {"status": "CANDIDATE_REVIEW", "candidate_directory": str(tmp_path / "candidate"),
               "receipt": {"anchor": "candidate_directory", "path": "generation_receipt.json"}}
    with patch("nasolve.cli.load_config", return_value=AppConfig()), \
            patch("nasolve.cli.discover_phenix", return_value=_installation(tmp_path)), \
            patch("nasolve.cif_generation.generate_elbow_candidate", return_value=payload):
        assert main(_arguments(tmp_path)) == 0
    output = capsys.readouterr().out
    assert "CIF Doctor candidate: CANDIDATE_REVIEW" in output
    assert "generation_receipt.json" in output
    assert "review chemistry" in output
    assert "PASS" not in output


@pytest.mark.parametrize("provide_elbow", [False, True])
def test_elbow_discovery_is_optional_for_existing_phenix_installations(tmp_path, provide_elbow):
    install = tmp_path / "native"
    bin_dir = install / "bin"
    bin_dir.mkdir(parents=True)
    programs = [*REQUIRED_PROGRAMS, "phenix.version"]
    if provide_elbow:
        programs.append("phenix.elbow")
    for program in programs:
        executable = bin_dir / program
        executable.write_text("#!/bin/sh\necho 'Phenix 2.2.1-6174'\n")
        executable.chmod(0o755)
    installation = discover_phenix(AppConfig(), explicit=install, environ={"PATH": ""},
                                  standard_candidates=[])
    assert installation.version == "2.2.1-6174"
    assert set(REQUIRED_PROGRAMS) <= installation.executables.keys()
    assert ("phenix.elbow" in installation.executables) is provide_elbow


def test_elbow_from_another_installation_is_not_a_selected_installation_capability(tmp_path):
    install = tmp_path / "selected-native"
    bin_dir = install / "bin"
    bin_dir.mkdir(parents=True)
    for program in (*REQUIRED_PROGRAMS, "phenix.version"):
        executable = bin_dir / program
        executable.write_text("#!/bin/sh\necho 'Phenix 2.2.1-6174'\n")
        executable.chmod(0o755)
    foreign = tmp_path / "other-native" / "bin"
    foreign.mkdir(parents=True)
    elbow = foreign / "phenix.elbow"
    elbow.write_text("#!/bin/sh\nexit 0\n")
    elbow.chmod(0o755)
    installation = discover_phenix(AppConfig(), explicit=install, environ={"PATH": str(foreign)},
                                  standard_candidates=[])
    assert installation.version == "2.2.1-6174"
    assert "phenix.elbow" not in installation.executables
