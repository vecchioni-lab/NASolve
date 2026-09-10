import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nasolve.campaigns import CampaignError, campaign_status, plan_campaign

from .helpers import make_dataset, model_text


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "campaign"
        self.root.mkdir()
        self.frames = self.base / "MR_frames"
        self.catalogue = self.frames / "5W6W"
        self.catalogue.mkdir(parents=True)
        (self.catalogue / "C_G.pdb").write_text(model_text())
        (self.catalogue / "seq_base.txt").write_text("ACGT\n")
        self.preset_root = self.base / "preset"
        self.preset_root.mkdir()
        self.preset = self.preset_root / "project.toml"
        self.write_preset()

    def write_preset(self, automr='pair = "C:G"\n', extra=""):
        self.preset.write_text(
            'schema_version = 1\nid = "fixture"\nversion = "1.0"\n'
            + "[automr]\n" + automr + extra
        )

    def dataset(self, name, config=None, content=None):
        dataset = make_dataset(self.root / name, include_model=False)
        (dataset / "staraniso-alldata.mtz").write_bytes(
            name.encode() if content is None else content
        )
        if config is not None:
            (dataset / "nasolve.txt").write_text(config)
        return dataset

    def plan(self, **kwargs):
        return plan_campaign(self.root, preset=self.preset,
                             frames_directory=self.frames, **kwargs)

    def state_path(self):
        return self.root / "NASolveCampaign" / "plan.json"

    def rewrite_state(self, mutate, resign=False):
        state = json.loads(self.state_path().read_text())
        mutate(state)
        if resign:
            state.pop("fingerprint", None)
            state["fingerprint"] = hashlib.sha256(json.dumps(
                state, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ).encode()).hexdigest()
        self.state_path().write_text(json.dumps(state))

    def test_plans_without_subprocesses_dataset_writes_or_workspace_selection(self):
        dataset = self.dataset("QiC")
        before = {path.name: path.read_bytes() for path in dataset.iterdir()}
        with patch("subprocess.run", side_effect=AssertionError("No external programs")), \
                patch("subprocess.Popen", side_effect=AssertionError("No external programs")):
            plan = self.plan()
            status = campaign_status(self.root)
        self.assertEqual(plan["state"], "PLANNED")
        self.assertEqual(plan["validation_scope"], "input_and_model_selection")
        self.assertEqual(plan["counts"], {"total": 1, "discovered": 1, "blocked": 0,
                                          "duplicate_groups": 0})
        self.assertEqual(status["integrity"], "OK")
        self.assertEqual(before, {path.name: path.read_bytes() for path in dataset.iterdir()})
        self.assertFalse((dataset / "AutoMR").exists())
        self.assertFalse((dataset / "nasolve.txt").exists())
        self.assertIsNone(plan["datasets"][0]["effective_config"]["config_source"])
        self.assertNotIn("plan_path", json.loads(self.state_path().read_text()))
        self.assertNotIn(str(self.base), self.state_path().read_text())

    def test_partial_ambiguous_and_invalid_datasets_are_isolated(self):
        self.dataset("good")
        partial = self.root / "partial"
        partial.mkdir()
        (partial / "summary.html").write_text("summary")
        ambiguous = self.dataset("ambiguous")
        (ambiguous / "staraniso_alldata-unique.mtz").write_bytes(b"other")
        self.dataset("invalid", "[automr]\nmisspelled = true\n")
        entries = {entry["id"]: entry for entry in self.plan()["datasets"]}
        self.assertEqual(list(entries), ["ambiguous", "good", "invalid", "partial"])
        self.assertEqual(entries["good"]["status"], "DISCOVERED")
        for name, reason in (("partial", "Missing required reflection"),
                             ("ambiguous", "Ambiguous STARANISO"),
                             ("invalid", "Unknown [automr]")):
            self.assertEqual(entries[name]["status"], "BLOCKED")
            self.assertIn(reason, entries[name]["diagnostic"])
        self.assertEqual(campaign_status(self.root)["integrity"], "OK")

    def test_discovery_is_direct_child_and_excludes_runs_environments_and_symlinks(self):
        self.dataset("yes")
        for name in ("AutoMR", "PostMR", "AutoSol", "AutoRefine", "CootGUI",
                     "RefineDoctor", "env", "venv", ".venv"):
            make_dataset(self.root / name)
        unusual_env = make_dataset(self.root / "python-runtime")
        (unusual_env / "pyvenv.cfg").write_text("home = runtime")
        conda = make_dataset(self.root / "other-runtime")
        (conda / "conda-meta").mkdir()
        make_dataset(self.root / "collection" / "nested")
        (self.root / "alias").symlink_to(self.root / "yes", target_is_directory=True)
        (self.root / "unrelated").mkdir()
        self.assertEqual([entry["id"] for entry in self.plan()["datasets"]], ["yes"])

    def test_dataset_config_precedence_preserves_explicit_false_and_alias_selection(self):
        self.write_preset('pair = "C:G"\nmirror = true\nallow_p1_standard = true\n')
        (self.catalogue / "E_G.pdb").write_text(model_text() + "REMARK exact\n")
        self.dataset("explicit", "[automr]\nframe = 5W6W\npair = DE:DG\n"
                     "mirror = false\nallow_p1_standard = false\n")
        self.dataset("omitted", "[automr]\npair = D:T\n")
        entries = {entry["id"]: entry for entry in self.plan()["datasets"]}
        explicit = entries["explicit"]["effective_config"]
        self.assertEqual(explicit["frame"], "W")
        self.assertFalse(explicit["mirror"])
        self.assertFalse(explicit["allow_p1_standard"])
        self.assertTrue(explicit["exact_pair_model"])
        self.assertEqual(explicit["model_name"], "E_G.pdb")
        self.assertEqual([item["ligand_code"] for item in explicit["pair_ligands"]], ["DE", "DG"])
        omitted = entries["omitted"]["effective_config"]
        self.assertTrue(omitted["mirror"])
        self.assertTrue(omitted["allow_p1_standard"])
        self.assertFalse(omitted["exact_pair_model"])
        self.assertEqual(omitted["model_name"], "C_G.pdb")

    def test_builtin_requires_dataset_pair_and_rejects_unsupported_mode_or_frame(self):
        self.dataset("good", "[automr]\npair = C:G\n")
        self.dataset("missing")
        self.dataset("nonstandard", "[automr]\nmode = nonstandard\n")
        self.dataset("wrong_frame", "[automr]\nframe = 3GBI\npair = C:C\n")
        plan = plan_campaign(self.root, frames_directory=self.frames)
        entries = {entry["id"]: entry for entry in plan["datasets"]}
        self.assertEqual(entries["good"]["status"], "DISCOVERED")
        self.assertIn("ordered pair", entries["missing"]["diagnostic"])
        for name in ("nonstandard", "wrong_frame"):
            self.assertEqual(entries[name]["status"], "BLOCKED")
            self.assertIn("only standard W/5W6W", entries[name]["diagnostic"])

    def test_unknown_chemistry_is_local_and_explicit_model_does_not_bypass_guards(self):
        self.dataset("unknown", "[automr]\npair = UNRECOGNIZED:DG\n")
        self.dataset("custom", "[automr]\nmodel = custom.pdb\n")
        self.dataset("good")
        entries = {entry["id"]: entry for entry in self.plan()["datasets"]}
        self.assertEqual(entries["good"]["status"], "DISCOVERED")
        self.assertIn("Unknown ligand code", entries["unknown"]["diagnostic"])
        self.assertIn("remove model", entries["custom"]["diagnostic"])

    def test_multiple_mutation_sites_use_the_canonical_config_parser(self):
        self.dataset("dataset", "[automr]\npair = C:G\n[mutations]\nA:8 = E\nA:9 = F\n")
        entry = self.plan()["datasets"][0]
        self.assertEqual(entry["status"], "DISCOVERED")
        self.assertEqual(set(entry["effective_config"]["mutations"]), {"A:8", "A:9"})
        self.assertEqual(campaign_status(self.root)["integrity"], "OK")

    def test_duplicate_authoritative_reflections_are_reported_without_collapsing(self):
        self.dataset("z", content=b"duplicate")
        self.dataset("a", content=b"duplicate")
        self.dataset("independent", content=b"different")
        plan = self.plan()
        entries = {entry["id"]: entry for entry in plan["datasets"]}
        self.assertEqual(plan["counts"]["total"], 3)
        self.assertEqual(plan["counts"]["duplicate_groups"], 1)
        self.assertEqual(entries["z"]["duplicate_of"], "a")
        self.assertIsNone(entries["a"]["duplicate_of"])
        self.assertEqual(entries["a"]["duplicate_group"], ["a", "z"])
        self.assertEqual(entries["independent"]["duplicate_group"], [])
        self.assertEqual(campaign_status(self.root)["integrity"], "OK")

    def test_explicit_selection_is_exact_and_deterministic(self):
        self.dataset("c")
        self.dataset("a")
        self.dataset("b")
        plan = self.plan(datasets=("c", "a"))
        self.assertEqual([entry["id"] for entry in plan["datasets"]], ["a", "c"])

    def test_unsafe_missing_recursive_or_duplicate_explicit_selection_is_rejected(self):
        self.dataset("valid")
        (self.root / "alias").symlink_to(self.root / "valid", target_is_directory=True)
        for requested in (("../valid",), ("/valid",), ("C:\\valid",), ("a/b",),
                          ("AutoMR",), ("missing",), ("alias",), ("valid", "valid"), ()):
            with self.subTest(requested=requested), self.assertRaises(CampaignError):
                self.plan(datasets=requested)
            self.assertFalse((self.root / "NASolveCampaign").exists())

    def test_unsafe_discovered_dataset_name_fails_before_publication(self):
        self.dataset("D:T")
        with self.assertRaisesRegex(CampaignError, "Invalid dataset name"):
            self.plan()
        self.assertFalse((self.root / "NASolveCampaign").exists())

    def test_unsafe_discovery_filename_produces_a_readable_blocked_record(self):
        dataset = self.dataset("dataset")
        (dataset / "Data\\_1_extra.cif").write_text("data_extra")
        entry = self.plan()["datasets"][0]
        self.assertEqual(entry["status"], "BLOCKED")
        self.assertIn("safe relative path", entry["diagnostic"])
        self.assertEqual(campaign_status(self.root)["integrity"], "OK")

    def test_explicit_empty_dataset_is_blocked_and_empty_campaign_is_rejected(self):
        empty = self.root / "empty"
        empty.mkdir()
        plan = self.plan(datasets=("empty",))
        self.assertEqual(plan["datasets"][0]["status"], "BLOCKED")
        other = self.base / "no-datasets"
        other.mkdir()
        with self.assertRaisesRegex(CampaignError, "No dataset candidates"):
            plan_campaign(other)
        self.assertFalse((other / "NASolveCampaign").exists())

    def test_explicit_frames_directory_never_falls_back_and_environment_is_ignored(self):
        self.dataset("dataset")
        missing = self.base / "missing-frames"
        with self.assertRaises(CampaignError):
            plan_campaign(self.root, preset=self.preset, frames_directory=missing)
        with patch.dict(os.environ, {"NASOLVE_MR_FRAMES": str(missing)}):
            result = self.plan()
        self.assertEqual(result["datasets"][0]["status"], "DISCOVERED")
        self.assertEqual(result["datasets"][0]["effective_config"]["model_name"], "C_G.pdb")

    def test_empty_model_and_malformed_unicode_config_are_blocked(self):
        invalid = self.dataset("unicode")
        (invalid / "nasolve.txt").write_bytes(b"\xff")
        self.dataset("empty_model")
        (self.catalogue / "C_G.pdb").write_bytes(b"")
        entries = {entry["id"]: entry for entry in self.plan()["datasets"]}
        self.assertEqual(entries["unicode"]["status"], "BLOCKED")
        self.assertIn("decode", entries["unicode"]["diagnostic"])
        self.assertIn("model is empty", entries["empty_model"]["diagnostic"])

    def test_existing_state_directory_file_or_dangling_link_is_never_overwritten(self):
        self.dataset("dataset")
        plan = self.plan()
        before = self.state_path().read_bytes()
        with self.assertRaisesRegex(CampaignError, "refusing to overwrite"):
            self.plan()
        self.assertEqual(self.state_path().read_bytes(), before)
        self.assertEqual(campaign_status(self.root)["fingerprint"], plan["fingerprint"])
        for name, kind in (("file", "file"), ("directory", "directory"), ("link", "link")):
            root = self.base / name
            root.mkdir()
            path = root / "NASolveCampaign"
            if kind == "file":
                path.write_text("owned")
            elif kind == "directory":
                path.mkdir()
            else:
                path.symlink_to(self.base / "nonexistent")
            with self.subTest(kind=kind), self.assertRaisesRegex(CampaignError, "overwrite"):
                plan_campaign(root)

    def test_publication_failure_cleans_only_its_own_outputs(self):
        self.dataset("dataset")
        unrelated = self.root / "keep.txt"
        unrelated.write_text("owned by user")
        with patch("nasolve.campaigns.os.link", side_effect=OSError("cannot publish")):
            with self.assertRaisesRegex(CampaignError, "cannot publish"):
                self.plan()
        self.assertEqual(unrelated.read_text(), "owned by user")
        self.assertFalse((self.root / "NASolveCampaign").exists())
        self.assertFalse(list(self.root.glob(".nasolve-campaign-*")))
        self.assertEqual(self.plan()["counts"]["discovered"], 1)

    def test_status_is_read_only_and_does_not_adopt_new_datasets_or_outputs(self):
        dataset = self.dataset("planned")
        self.plan()
        before = self.state_path().read_bytes()
        self.dataset("new-dataset")
        make_dataset(dataset / "AutoMR" / "run_001")
        (dataset / "irrelevant.txt").write_text("added later")
        with patch("pathlib.Path.write_text", side_effect=AssertionError("Read only")), \
                patch("pathlib.Path.write_bytes", side_effect=AssertionError("Read only")):
            status = campaign_status(self.root)
        self.assertEqual(status["integrity"], "OK")
        self.assertEqual([entry["id"] for entry in status["datasets"]], ["planned"])
        self.assertEqual(self.state_path().read_bytes(), before)

    def test_added_config_and_new_ambiguous_discovery_candidates_are_drift(self):
        first = self.dataset("config")
        second = self.dataset("ambiguous")
        self.plan()
        (first / "nasolve.txt").write_text("[automr]\npair = E:G\n")
        (second / "Data_1_new.cif").write_text("metadata")
        status = campaign_status(self.root)
        self.assertEqual(status["integrity"], "DRIFT")
        for entry in status["datasets"]:
            self.assertEqual(entry["integrity"], "DRIFT")
            self.assertIn("Discovery inventory changed", str(entry["integrity_issues"]))

    def test_changed_input_model_sequence_and_preset_resources_are_detected(self):
        self.write_preset(extra='\n[resources]\nrestraints = "restraints.eff"\n')
        (self.preset_root / "restraints.eff").write_bytes(b"restraint content")
        dataset = self.dataset("dataset")
        plan = self.plan()
        entry = plan["datasets"][0]
        targets = [entry["inputs"]["model"], entry["inputs"]["frame_sequence"],
                   plan["preset"]["resources"]["restraints"], plan["preset"]["source"]]
        for reference in targets:
            path = self.root / reference["relative_path"]
            original = path.read_bytes()
            path.write_bytes(b"tampered")
            with self.subTest(reference=reference):
                status = campaign_status(self.root)
                self.assertEqual(status["integrity"], "DRIFT")
            path.write_bytes(original)
        (dataset / "staraniso-alldata.mtz").write_bytes(b"changed")
        self.assertEqual(campaign_status(self.root)["datasets"][0]["integrity"], "DRIFT")

    def test_missing_input_and_symlink_escape_are_detected_without_basename_search(self):
        dataset = self.dataset("dataset")
        self.plan()
        reflection = dataset / "staraniso-alldata.mtz"
        original = reflection.read_bytes()
        reflection.unlink()
        other = self.root / "elsewhere"
        other.mkdir()
        (other / reflection.name).write_bytes(original)
        self.assertIn("Missing frozen file", str(campaign_status(self.root)))
        outside = self.base / "outside.mtz"
        outside.write_bytes(original)
        reflection.symlink_to(outside)
        self.assertIn("escapes its declared anchor", str(campaign_status(self.root)))

    def test_input_symlink_escape_is_local_blocker_during_planning(self):
        dataset = self.dataset("unsafe")
        reflection = dataset / "staraniso-alldata.mtz"
        reflection.unlink()
        outside = self.base / "outside.mtz"
        outside.write_bytes(b"mtz")
        reflection.symlink_to(outside)
        self.dataset("good")
        entries = {entry["id"]: entry for entry in self.plan()["datasets"]}
        self.assertEqual(entries["good"]["status"], "DISCOVERED")
        self.assertEqual(entries["unsafe"]["status"], "BLOCKED")
        self.assertIn("escapes its declared anchor", entries["unsafe"]["diagnostic"])

    def test_status_rejects_symlink_escape_to_identical_content_inside_campaign(self):
        first = self.dataset("first", content=b"identical")
        second = self.dataset("second", content=b"identical")
        plan = self.plan()
        reflection = first / "staraniso-alldata.mtz"
        reflection.unlink()
        reflection.symlink_to(second / reflection.name)
        status = campaign_status(self.root)
        self.assertEqual(status["datasets"][0]["integrity"], "DRIFT")
        self.assertIn("escapes its declared anchor", str(status["datasets"][0]["integrity_issues"]))
        model = self.root / plan["datasets"][0]["inputs"]["model"]["relative_path"]
        same_model = first / "model.pdb"
        same_model.write_bytes(model.read_bytes())
        model.unlink()
        model.symlink_to(same_model)
        status = campaign_status(self.root)
        self.assertEqual(status["datasets"][1]["integrity"], "DRIFT")
        self.assertIn("escapes its declared anchor", str(status["datasets"][1]["integrity_issues"]))

    def test_whole_campaign_relocates_after_original_preset_and_catalogue_are_removed(self):
        self.write_preset(extra='\n[resources]\nrestraints = "restraints.eff"\n')
        (self.preset_root / "restraints.eff").write_bytes(b"restraints")
        self.dataset("dataset", "[automr]\npair = C:G\n")
        original = self.plan()
        moved = self.base / "relocated" / "campaign"
        moved.parent.mkdir()
        shutil.move(str(self.root), moved)
        shutil.rmtree(self.preset_root)
        shutil.rmtree(self.frames)
        self.assertFalse(self.root.exists())
        status = campaign_status(moved)
        self.assertEqual(status["integrity"], "OK")
        self.assertEqual(status["fingerprint"], original["fingerprint"])
        self.assertEqual(status["plan_path"], str(moved / "NASolveCampaign" / "plan.json"))

    def test_fingerprint_is_deterministic_and_includes_effective_inventory(self):
        self.dataset("dataset")
        first = self.plan()
        second_root = self.base / "second-campaign"
        make_dataset(second_root / "dataset", include_model=False)
        (second_root / "dataset" / "staraniso-alldata.mtz").write_bytes(b"dataset")
        second = plan_campaign(second_root, preset=self.preset, frames_directory=self.frames)
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.rewrite_state(lambda value: value["datasets"][0]["effective_config"].update(mirror=True))
        with self.assertRaisesRegex(CampaignError, "fingerprint mismatch"):
            campaign_status(self.root)

    def test_malformed_state_is_rejected_even_when_fingerprint_is_recomputed(self):
        self.dataset("dataset")
        self.plan()
        original = self.state_path().read_bytes()
        mutations = [
            lambda value: value.update(schema_version=True),
            lambda value: value.update(state="SOLVED"),
            lambda value: value.update(datasets={}),
            lambda value: value["counts"].update(total=True),
            lambda value: value["datasets"][0].update(relative_path="../dataset"),
            lambda value: value["datasets"][0].update(status="DEPOSIT_READY"),
            lambda value: value["datasets"][0].update(config_present="false"),
            lambda value: value["datasets"][0].update(inputs=[]),
            lambda value: value["datasets"][0]["inputs"]["model"].update(anchor="repository"),
            lambda value: value["datasets"][0]["inputs"]["model"].update(relative_path="../outside"),
            lambda value: value["datasets"][0]["inputs"]["model"].update(sha256="bad"),
            lambda value: value["datasets"][0]["inputs"]["model"].update(size=-1),
            lambda value: value["datasets"][0]["effective_config"].update(mirror="false"),
            lambda value: value["datasets"][0].update(duplicate_of="missing"),
            lambda value: value["datasets"][0].pop("duplicate_of"),
            lambda value: value["preset"].update(config_sha256="0" * 64),
        ]
        for index, mutate in enumerate(mutations):
            self.state_path().write_bytes(original)
            self.rewrite_state(mutate, resign=True)
            with self.subTest(index=index), self.assertRaises(CampaignError):
                campaign_status(self.root)

    def test_invalid_json_duplicate_fields_and_missing_plan_are_clear_errors(self):
        with self.assertRaisesRegex(CampaignError, "Cannot read campaign plan"):
            campaign_status(self.root)
        self.dataset("dataset")
        self.plan()
        for contents in ("{", "[]", '{"schema_version": 1, "schema_version": 1}'):
            self.state_path().write_text(contents)
            with self.subTest(contents=contents), self.assertRaises(CampaignError):
                campaign_status(self.root)


if __name__ == "__main__":
    unittest.main()
