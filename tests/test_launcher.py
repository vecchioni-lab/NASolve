import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
LAUNCHER = REPOSITORY / "nasolve"


@unittest.skipIf(os.name == "nt", "the source launcher is a POSIX shell script")
class SourceLauncherTests(unittest.TestCase):
    def test_launcher_imports_checkout_from_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            working_directory = Path(directory) / "unrelated directory"
            working_directory.mkdir()
            (working_directory / "nasolve.py").write_text(
                "print('SHADOW_MODULE_EXECUTED')\n"
            )
            launcher_link = Path(directory) / "linked nasolve"
            launcher_link.symlink_to(LAUNCHER)
            environment = os.environ.copy()
            environment["NASOLVE_PYTHON"] = sys.executable
            environment["PYTHONPATH"] = ""

            completed = subprocess.run(
                [str(launcher_link), "--help"],
                cwd=working_directory,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("usage: nasolve", completed.stdout)
            self.assertNotIn("SHADOW_MODULE_EXECUTED", completed.stdout)

    def test_default_interpreter_preserves_arguments_cwd_and_pythonpath(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working_directory = root / "working directory"
            working_directory.mkdir()
            checkout = root / "checkout with spaces"
            checkout.mkdir()
            checkout_launcher = checkout / "nasolve"
            shutil.copy2(LAUNCHER, checkout_launcher)
            (checkout / "src").mkdir()
            launcher_link = root / "bin" / "nasolve"
            launcher_link.parent.mkdir()
            launcher_link.symlink_to(checkout_launcher)
            fake_python = checkout / ".venv" / "bin" / "python"
            fake_python.parent.mkdir(parents=True)
            fake_python.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "Path(os.environ['NASOLVE_CAPTURE_ARGUMENTS']).write_text("
                "json.dumps(sys.argv[1:]))\n"
                "Path(os.environ['NASOLVE_CAPTURE_PYTHONPATH']).write_text("
                "os.environ['PYTHONPATH'])\n"
                "Path(os.environ['NASOLVE_CAPTURE_CWD']).write_text(os.getcwd())\n"
            )
            fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)
            arguments_path = root / "arguments.txt"
            pythonpath_path = root / "pythonpath.txt"
            cwd_path = root / "cwd.txt"
            environment = os.environ.copy()
            environment.pop("NASOLVE_PYTHON", None)
            environment.update(
                {
                    "NASOLVE_CAPTURE_ARGUMENTS": str(arguments_path),
                    "NASOLVE_CAPTURE_PYTHONPATH": str(pythonpath_path),
                    "NASOLVE_CAPTURE_CWD": str(cwd_path),
                    "PYTHONPATH": "/existing/python path",
                    "PATH": f"{launcher_link.parent}{os.pathsep}{environment['PATH']}",
                }
            )

            completed = subprocess.run(
                ["nasolve", "workspace", "use", "dataset with spaces"],
                cwd=working_directory,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            arguments = json.loads(arguments_path.read_text())
            self.assertEqual(arguments[0], "-c")
            self.assertIn("sys.path[:]", arguments[1])
            self.assertEqual(
                Path(arguments[2]).resolve(),
                (checkout / "src").resolve(),
            )
            self.assertEqual(arguments[-3:], ["workspace", "use", "dataset with spaces"])
            injected_path, existing_path = pythonpath_path.read_text().split(
                os.pathsep, 1
            )
            self.assertEqual(
                Path(injected_path).resolve(),
                (checkout / "src").resolve(),
            )
            self.assertEqual(existing_path, "/existing/python path")
            self.assertEqual(
                Path(cwd_path.read_text().strip()).resolve(),
                working_directory.resolve(),
            )

    def test_launcher_reports_a_missing_interpreter_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid_values = (
                root / "missing python",
                root / "python directory",
                root / "non-executable python",
            )
            invalid_values[1].mkdir()
            invalid_values[2].write_text("not an interpreter\n")
            for invalid in invalid_values:
                with self.subTest(invalid=invalid):
                    environment = os.environ.copy()
                    environment["NASOLVE_PYTHON"] = str(invalid)

                    completed = subprocess.run(
                        [str(LAUNCHER), "--help"],
                        env=environment,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                    )

                    self.assertEqual(completed.returncode, 127)
                    self.assertIn(
                        "Python interpreter is not executable", completed.stderr
                    )


if __name__ == "__main__":
    unittest.main()
