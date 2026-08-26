import tempfile
import unittest
from pathlib import Path

from nasolve.config import AppConfig, CootSettings
from nasolve.coot_runtime import discover_coot, installation_from_candidate

from .helpers import make_coot


class CootRuntimeTests(unittest.TestCase):
    def test_validates_version_and_embedded_python(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = make_coot(Path(directory))
            installation = installation_from_candidate(executable)
            self.assertEqual(installation.version, "1.1.10")
            self.assertEqual(installation.executable, executable.resolve())

    def test_saved_path_is_revalidated(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = make_coot(Path(directory))
            config = AppConfig(coot=CootSettings(executable=str(executable)))
            installation = discover_coot(config, environ={"PATH": ""}, candidates=[])
            self.assertEqual(installation.source, "saved configuration")


if __name__ == "__main__":
    unittest.main()
