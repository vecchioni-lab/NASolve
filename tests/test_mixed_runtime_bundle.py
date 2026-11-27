"""The mixed worker must load from its small, declared native helper closure."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

import nasolve


def test_mixed_guard_does_not_require_checkpoint_or_gui_owners(tmp_path):
    package = Path(nasolve.__file__).parent
    destination = tmp_path / "native_worker"
    destination.mkdir()
    (destination / "__init__.py").touch()
    (destination / "metal").mkdir()
    (destination / "metal/__init__.py").touch()
    helpers = [
        "refinement_mixed_runtime.py", "refinement_parameter_scope.py",
        "refinement_parameter_native.py", "refinement_diffraction_observation.py",
        "refinement_normalization.py", "refinement_runtime_timing.py",
        "refinement_mixed_source_guard.py",
        "metal/recipe.py", "metal/_xyz_native.py", "metal/_diffraction_audit.py",
    ]
    for name in helpers:
        if (package / name).exists():
            shutil.copyfile(package / name, destination / name)
    code = """
from native_worker.refinement_mixed_runtime import MixedRuntimeGuard
from native_worker.refinement_diffraction_observation import DiffractionReference
from native_worker.refinement_normalization import NativeScaleWitness
from native_worker.refinement_mixed_source_guard import SourceMixedGuard
import sys
assert not any(name.startswith('nasolve') for name in sys.modules)
assert 'native_worker.metal.fdp' not in sys.modules
assert 'native_worker.metal.xyz' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(tmp_path)),
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
