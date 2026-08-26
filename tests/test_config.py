import json
import tempfile
import unittest
from pathlib import Path

from nasolve.config import AppConfig, CootSettings, PhenixSettings, load_config, save_config


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
            )
            self.assertEqual(save_config(original, path), path)
            loaded = load_config(path)
            self.assertEqual(loaded.phenix.root, "/opt/phenix")
            self.assertEqual(loaded.phenix.version, "1.2.3")
            self.assertEqual(loaded.coot.executable, "/opt/coot")
            self.assertEqual(loaded.coot.version, "1.1.10")
            self.assertEqual(json.loads(path.read_text())["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
