import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nasolve.config import (
    AppConfig,
    CootSettings,
    ConfigError,
    PhenixSettings,
    WorkspaceSettings,
    load_config,
    save_config,
)


class ConfigTests(unittest.TestCase):
    def test_missing_config_is_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.json")
            self.assertEqual(config.schema_version, 1)
            self.assertIsNone(config.phenix.root)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            original = AppConfig(
                phenix=PhenixSettings(root="/opt/phenix", version="1.2.3"),
                coot=CootSettings(executable="/opt/coot", version="1.1.10"),
                workspace=WorkspaceSettings(
                    dataset="/data/project/dataset",
                    run="/data/project/dataset/AutoMR/run_004",
                ),
            )
            self.assertEqual(save_config(original, path), path)
            loaded = load_config(path)
            self.assertEqual(loaded.phenix.root, "/opt/phenix")
            self.assertEqual(loaded.phenix.version, "1.2.3")
            self.assertEqual(loaded.coot.executable, "/opt/coot")
            self.assertEqual(loaded.coot.version, "1.1.10")
            self.assertEqual(loaded.workspace.dataset, "/data/project/dataset")
            self.assertEqual(
                loaded.workspace.run,
                "/data/project/dataset/AutoMR/run_004",
            )
            self.assertEqual(json.loads(path.read_text())["schema_version"], 1)

    def test_malformed_config_shapes_raise_config_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for payload in ([], {"workspace": []}, {"workspace": {"run": 123}}):
                path.write_text(json.dumps(payload))
                with self.subTest(payload=payload):
                    with self.assertRaises(ConfigError):
                        load_config(path)

    def test_config_directory_creation_failure_is_wrapped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "new" / "config.json"
            with patch("pathlib.Path.mkdir", side_effect=OSError("read only")):
                with self.assertRaisesRegex(ConfigError, "Could not save"):
                    save_config(AppConfig(), path)


if __name__ == "__main__":
    unittest.main()
