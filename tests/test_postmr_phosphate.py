"""PostMR regressions using synthetic coordinates and a mocked ReadySet process."""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nasolve.postmr import PostMRPreparationError, _run_readyset, prepare_postmr
from nasolve.run_context import resolve_artifact_path

from .helpers import make_postmr_report
from .test_phosphate import atom, phosphate, without_extra


def extra_sites(text):
    return {
        f"{line[21]}:{line[22:27].strip()}"
        for line in text.splitlines()
        if line.startswith(("ATOM  ", "HETATM"))
        and line[12:16].strip() in {"OP3", "O3P"}
    }


class PostMRPhosphateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def model_records(self):
        return [
            *phosphate(), "TER\n",
            *phosphate(chain="B", number=4, previous=3, residue="OHU", start=21, shift=20),
            "TER\n",
            *phosphate(chain="D", number=1, residue="DC", start=41, shift=40, terminal=True),
            "TER\n", "END\n",
        ]

    def readyset_process(self, transform=lambda content: content):
        def run(command, *, cwd, **_kwargs):
            model = Path(command[1])
            output = Path(cwd) / f"{model.stem}.updated.pdb"
            output.write_text(transform(model.read_text()))
            return SimpleNamespace(returncode=0, stdout="Mock ReadySet completed\n")

        return run

    def create_run(self):
        model = self.root / "source.pdb"
        model.write_text("".join(self.model_records()))
        run = self.root / "run_001"
        report_path = make_postmr_report(run, model)
        report = json.loads(report_path.read_text())
        report["frame"] = None
        report["post_mr_plan"] = {"sequences": {}, "standard_pair": None, "mutations": {}}
        report_path.write_text(json.dumps(report))
        return model, run

    def builder(self, calls):
        def build(prepared, compatibility, pairs, output):
            calls.append(prepared.read_text())
            self.assertEqual(extra_sites(prepared.read_text()), {"D:1"})
            self.assertEqual(extra_sites(compatibility.read_text()), {"D:1"})
            pairs.write_text("")
            return {"retained_pair_count": 0, "retained_pairs": [], "modified_sites": ["A:12", "B:4"]}

        return build

    def test_cleanup_precedes_restraints_and_preserves_raw_models(self):
        source, run = self.create_run()
        original = source.read_text()
        calls = []
        with patch("nasolve.postmr.subprocess.run", side_effect=self.readyset_process()):
            result = prepare_postmr(
                run, self.root / "phenix.ready_set", modified_pairs_only=True,
                modified_pair_builder=self.builder(calls),
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(source.read_text(), original)
        self.assertEqual((run / "Phaser" / "mr_solution.pdb").read_text(), original)
        self.assertEqual((result.postmr_directory / "Model" / "mr_solution.pdb").read_text(), original)
        self.assertEqual((result.postmr_directory / "Model" / "after_coot.pdb").read_text(), original)
        self.assertEqual(extra_sites(result.model_path.read_text()), {"D:1"})
        report = json.loads(result.report_path.read_text())
        audit = report["phosphate_cleanup"]
        self.assertEqual({item["site"] for item in audit["before_restraints"]["removed"]}, {"A:12", "B:4"})
        self.assertEqual(audit["after_readyset"]["removed"], [])
        self.assertTrue({"A:12", "B:4"}.issubset(
            {item["site"] for item in audit["after_readyset"]["checked"]}
        ))

    def test_reused_input_serials_reach_readyset_with_only_internal_extras_removed(self):
        source, run = self.create_run()
        records = source.read_text().splitlines(keepends=True)
        original = "".join(line[:6] + "    0" + line[11:]
                           if line.startswith(("ATOM  ", "HETATM")) else line
                           for line in records)
        source.write_text(original)
        (run / "Phaser" / "mr_solution.pdb").write_text(original)
        calls = []
        with patch("nasolve.postmr.subprocess.run", side_effect=self.readyset_process()):
            result = prepare_postmr(
                run, self.root / "phenix.ready_set", modified_pairs_only=True,
                modified_pair_builder=self.builder(calls),
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(extra_sites(result.model_path.read_text()), {"D:1"})
        self.assertEqual(source.read_text(), original)
        self.assertEqual((result.postmr_directory / "Model" / "after_coot.pdb").read_text(), original)

    def test_readyset_reintroduced_extras_cleaned_before_count_guard_with_raw_output_preserved(self):
        source, run = self.create_run()
        internal_extras = {
            (line[21], line[22:27]): line for line in self.model_records()
            if line.startswith(("ATOM  ", "HETATM"))
            and line[12:16].strip() == "OP3" and line[21] in "AB"
        }

        def reintroduce(content):
            self.assertEqual(extra_sites(content), {"D:1"})
            records = []
            for line in content.splitlines(keepends=True):
                records.append(line)
                if line.startswith(("ATOM  ", "HETATM")) and line[12:16].strip() == "P":
                    extra = internal_extras.get((line[21], line[22:27]))
                    if extra is not None:
                        records.append(extra)
            return "".join(records)

        with patch("nasolve.postmr.subprocess.run", side_effect=self.readyset_process(reintroduce)):
            result = prepare_postmr(
                run, self.root / "phenix.ready_set", modified_pairs_only=True,
                modified_pair_builder=self.builder([]),
            )
        report = json.loads(result.report_path.read_text())
        raw = Path(report["readyset"]["updated_model"])
        checked_reference = report["readyset"]["phosphate_checked_model"]
        self.assertEqual(checked_reference["anchor"], "run")
        checked = resolve_artifact_path(checked_reference, run)
        self.assertIsNotNone(checked)
        self.assertEqual(checked_reference["sha256"], hashlib.sha256(checked.read_bytes()).hexdigest())
        self.assertNotEqual(raw, checked)
        self.assertEqual(extra_sites(raw.read_text()), {"A:12", "B:4", "D:1"})
        self.assertEqual(extra_sites(checked.read_text()), {"D:1"})
        self.assertEqual(result.model_path.read_text(), checked.read_text())
        self.assertEqual(extra_sites(source.read_text()), {"A:12", "B:4", "D:1"})
        self.assertEqual(
            {item["site"] for item in report["phosphate_cleanup"]["after_readyset"]["removed"]},
            {"A:12", "B:4"},
        )
        checked_bytes = checked.read_bytes()
        relocated_run = self.root / "relocated" / "run_001"
        shutil.copytree(run, relocated_run)
        shutil.rmtree(run)
        source.unlink()
        relocated_checked = resolve_artifact_path(checked_reference, relocated_run)
        self.assertEqual(relocated_checked, (relocated_run / checked_reference["relative_path"]).resolve())
        self.assertEqual(relocated_checked.read_bytes(), checked_bytes)
        relocated_checked.write_bytes(checked_bytes + b"REMARK altered after relocation\n")
        self.assertIsNone(resolve_artifact_path(checked_reference, relocated_run))

    def readyset_input(self):
        model = self.root / "prepared_model.pdb"
        model.write_text("".join(without_extra(phosphate()) + ["END\n"]))
        directory = self.root / "ReadySet"
        directory.mkdir()
        return model, directory

    def test_readyset_must_preserve_repaired_site_link_when_no_extra_is_present(self):
        model, directory = self.readyset_input()
        original = model.read_text()
        incoming = phosphate()[0]
        displaced = atom(1, "O3'", "DT", "A", 11, (-4, 0, 0), record="ATOM")
        with patch("nasolve.postmr.subprocess.run", side_effect=self.readyset_process(
            lambda content: content.replace(incoming, displaced)
        )):
            with self.assertRaisesRegex(PostMRPreparationError, "phosphate"):
                _run_readyset(
                    model, self.root / "phenix.ready_set", directory, None, None,
                    phosphate_sites=("A:12",),
                )
        self.assertEqual(model.read_text(), original)
        self.assertIn(displaced, (directory / "prepared_model.updated.pdb").read_text())

    def test_op3_cleanup_does_not_mask_other_readyset_atom_additions(self):
        model, directory = self.readyset_input()
        extra = next(line for line in phosphate() if line[12:16].strip() == "OP3")
        unexpected = atom(98, "O", "HOH", "Z", 99, (40, 0, 0))
        with patch("nasolve.postmr.subprocess.run", side_effect=self.readyset_process(
            lambda content: content.replace("END\n", extra + unexpected + "END\n")
        )):
            with self.assertRaisesRegex(PostMRPreparationError, "atom count"):
                _run_readyset(
                    model, self.root / "phenix.ready_set", directory, None, None,
                    phosphate_sites=("A:12",),
                )
        raw = (directory / "prepared_model.updated.pdb").read_text()
        self.assertIn(extra, raw)
        self.assertIn(unexpected, raw)
