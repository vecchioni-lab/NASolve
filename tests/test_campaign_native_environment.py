"""Opt-in source shuttles bootstrap imports before cleaning native overrides."""
import os
import sys

import pytest

from nasolve import campaign_worker


@pytest.mark.parametrize("enabled", [False, True])
def test_worker_environment_isolation_is_explicit_and_retains_import_paths(monkeypatch, enabled):
    overrides = ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CCP4", "CLIBD_MON", "LIBMOL_ROOT",
                 "__PYVENV_LAUNCHER__", "PYTHONEXECUTABLE", "PYTHONUSERBASE")
    for name in overrides:
        monkeypatch.setenv(name, "inherited-override")
    if enabled:
        monkeypatch.setenv("NASOLVE_NATIVE_ENV_ISOLATION", "1")
    else:
        monkeypatch.delenv("NASOLVE_NATIVE_ENV_ISOLATION", raising=False)
    monkeypatch.setattr(sys, "argv", ["campaign_worker", "job.json"])
    paths = list(sys.path)
    observed = {}
    def execute_job(path):
        observed.update({name: os.environ.get(name) for name in overrides})
        assert list(sys.path) == paths
        return 0
    monkeypatch.setattr(campaign_worker, "execute_job", execute_job)
    assert campaign_worker.main() == 0
    assert observed == {name: None if enabled else "inherited-override" for name in overrides}
