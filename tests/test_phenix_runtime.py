import os
import stat
import tempfile
import unittest
from pathlib import Path

from nasolve.config import AppConfig
from nasolve.phenix_runtime import (
    OPTIONAL_PROGRAMS,
    REQUIRED_PROGRAMS,
    discover_phenix,
    installation_from_candidate,
)


class PhenixRuntimeTests(unittest.TestCase):
    def fake_install(self, root: Path) -> Path:
        bin_dir = root / "bin"
        bin_dir.mkdir(parents=True)
        for name in (*REQUIRED_PROGRAMS, *OPTIONAL_PROGRAMS, "phenix.version"):
            path = bin_dir / name
            text = "#!/bin/sh\necho 'Phenix 9.8.7'\n" if name == "phenix.version" else "#!/bin/sh\nexit 0\n"
            path.write_text(text)
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return bin_dir

    def test_installation_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fake_install(root)
            installation = installation_from_candidate(root, base_environment={"PATH": ""})
            self.assertEqual(installation.version, "9.8.7")
            self.assertEqual(installation.root, root.resolve())
            self.assertIn("phenix.mtz.dump", installation.executables)
            self.assertIn("phenix.autosol", installation.executables)

    def test_path_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = self.fake_install(root)
            env = {"PATH": str(bin_dir)}
            installation = discover_phenix(AppConfig(), environ=env)
            self.assertEqual(installation.source, "PATH")
            self.assertEqual(installation.version, "9.8.7")

    def test_standard_location_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "phenix-9.8.7"
            self.fake_install(root)
            installation = discover_phenix(
                AppConfig(), environ={"PATH": ""}, standard_candidates=[root]
            )
            self.assertTrue(installation.source.startswith("standard location"))
            self.assertEqual(installation.version, "9.8.7")


if __name__ == "__main__":
    unittest.main()
