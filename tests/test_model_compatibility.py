import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from nasolve.backbone import make_backbone_policy
from nasolve.model_assessment import inspect_pdb
from nasolve.model_compatibility import (
    ModelCompatibilityFactsError,
    build_model_compatibility_facts,
    freeze_model_compatibility_facts,
    load_model_compatibility_facts,
)
from nasolve.search_model_comparison import compare_search_model_to_target

from .helpers import pdb_record


def assessment(root: Path, name: str, residues, *, shift: float = 0.0):
    path = root / name
    path.write_text(
        "".join(
            pdb_record(
                "ATOM",
                serial,
                "C1'",
                code,
                chain,
                resid,
                element="C",
                x=serial + shift,
            )
            for serial, (chain, resid, code) in enumerate(residues, 1)
        )
        + "END\n"
    )
    return inspect_pdb(
        path,
        polymer_ligand_codes={"DA", "DC", "DG", "DT"},
    )


def target(*rows):
    return {
        "schema_version": 1,
        "kind": "sequence-family-target",
        "reference": {
            "id": "family",
            "version": "1",
            "content_sha256": "a" * 64,
        },
        "sites": [
            {
                "site": site,
                "residue_code": code,
                "source": source,
                "assignments": [
                    {"source": source, "residue_code": code},
                ],
            }
            for site, code, source in rows
        ],
    }


class ModelCompatibilityFactsTests(unittest.TestCase):
    def test_complete_target_joins_facts_without_producing_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = assessment(
                root,
                "source.pdb",
                [("A", 1, "DA"), ("A", 2, "DC")],
            )
            effective = assessment(
                root,
                "effective.pdb",
                [("A", 1, "DA"), ("A", 2, "DC")],
                shift=10.0,
            )
            comparison = compare_search_model_to_target(
                source,
                target(
                    ("A:1", "DA", "family_reference"),
                    ("A:2", "DT", "dataset_site_chemistry"),
                ),
            )
            frozen_comparison = {
                "schema_version": 1,
                "kind": "frozen-search-model-comparison",
                "artifact": {
                    "anchor": "run",
                    "relative_path": "Model/search_model_comparison.json",
                    "sha256": "b" * 64,
                    "size": 100,
                },
            }
            facts = build_model_compatibility_facts(
                source_assessment=source,
                effective_assessment=effective,
                model_provider={
                    "kind": "explicit-standard-model",
                    "selection": "user-forced",
                    "location": "dataset",
                    "selector": "alternate.pdb",
                    "frame": "W",
                },
                mode="standard",
                recipient_frame="W",
                mirror_transform_applied=True,
                comparison=comparison,
                comparison_artifact=frozen_comparison,
                terminal_phosphate_sites=("D:1",),
                phosphate_intent={
                    "schema_version": 1,
                    "source": "recipe",
                    "allow_op3_sites": ["D:1"],
                    "recipe": {"id": "5w6w"},
                },
                backbone_policy=make_backbone_policy({}),
                symmetry={
                    "evidence": {"normalized_class": "H3/R3"},
                    "mr_copies": 1,
                },
            )
            self.assertNotEqual(
                facts["candidate"]["source_model_sha256"],
                facts["candidate"]["effective_model_sha256"],
            )
            self.assertEqual(facts["candidate"]["polymer_residue_count"], 2)
            self.assertEqual(facts["candidate"]["chains"], [{
                "chain": "A",
                "residue_count": 2,
                "residue_ids": ["1", "2"],
            }])
            dimensions = facts["dimensions"]
            self.assertEqual(dimensions["frame_identity"]["relation"], "SAME")
            self.assertEqual(dimensions["site_set"]["relation"], "SAME")
            self.assertEqual(dimensions["residue_identity"]["relation"], "DIFFERENT")
            self.assertEqual(dimensions["residue_identity"]["mismatch_count"], 1)
            self.assertEqual(dimensions["construct_family"]["relation"], "UNKNOWN")
            self.assertEqual(
                dimensions["construct_family"]["recipient_reference"]["id"],
                "family",
            )
            self.assertEqual(dimensions["chirality"]["relation"], "UNKNOWN")
            self.assertTrue(dimensions["chirality"]["mirror_transform_applied"])
            self.assertEqual(
                dimensions["terminal_phosphate_chemistry"]["recipient_sites"],
                ["D:1"],
            )
            self.assertEqual(
                dimensions["symmetry_and_copy_number"]["recipient_symmetry_class"],
                "H3/R3",
            )
            self.assertEqual(
                facts["evidence"]["search_model_comparison"],
                frozen_comparison,
            )
            self.assertEqual(facts["semantics"], {
                "descriptive_only": True,
                "score": None,
                "overall_compatibility": None,
                "donor_eligibility": None,
                "automatic_reuse_authorized": False,
            })

    def test_no_complete_target_keeps_target_dependent_dimensions_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(root, "model.pdb", [("A", 1, "DA")])
            facts = build_model_compatibility_facts(
                source_assessment=model,
                effective_assessment=model,
                model_provider={
                    "kind": "explicit-nonstandard-model",
                    "selection": "user-forced",
                    "location": "dataset",
                    "selector": "model.pdb",
                },
                mode="nonstandard",
                recipient_frame=None,
                mirror_transform_applied=False,
                comparison=None,
                comparison_artifact=None,
                terminal_phosphate_sites=(),
                phosphate_intent={
                    "schema_version": 1,
                    "source": "none",
                    "allow_op3_sites": [],
                    "recipe": None,
                },
                backbone_policy=make_backbone_policy({
                    "A:1": "experimental_passthrough",
                }, allow_unreviewed=True),
                symmetry=None,
            )
            dimensions = facts["dimensions"]
            self.assertEqual(dimensions["frame_identity"]["relation"], "UNKNOWN")
            self.assertEqual(dimensions["site_set"]["relation"], "UNKNOWN")
            self.assertEqual(dimensions["residue_identity"]["relation"], "UNKNOWN")
            self.assertEqual(dimensions["construct_family"]["relation"], "UNKNOWN")
            self.assertEqual(
                dimensions["backbone_chemistry"]["experimental_passthrough_sites"],
                ["A:1"],
            )
            self.assertIsNone(
                dimensions["symmetry_and_copy_number"]["recipient_symmetry_class"]
            )

    def test_frozen_facts_reject_checksum_drift_and_resigned_score(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run_001"
            (run / "Model").mkdir(parents=True)
            model = assessment(root, "model.pdb", [("A", 1, "DA")])
            facts = build_model_compatibility_facts(
                source_assessment=model,
                effective_assessment=model,
                model_provider=None,
                mode="nonstandard",
                recipient_frame=None,
                mirror_transform_applied=False,
                comparison=None,
                comparison_artifact=None,
                terminal_phosphate_sites=(),
                phosphate_intent=None,
                backbone_policy=make_backbone_policy({}),
                symmetry=None,
            )
            frozen = freeze_model_compatibility_facts(facts, run)
            report = {
                "mode": "nonstandard",
                "frame": None,
                "inputs": {
                    "model_sha256": model.sha256,
                    "mirror": False,
                    "model_provider": None,
                },
                "model_assessment": model.to_dict(),
                "post_mr_plan": {
                    "allow_op3_sites": [],
                    "backbone_policy": make_backbone_policy({}),
                },
                "model_compatibility_facts": frozen,
            }
            self.assertEqual(load_model_compatibility_facts(report, run), facts)

            forged_report = json.loads(json.dumps(report))
            forged_report["inputs"]["model_sha256"] = "f" * 64
            with self.assertRaisesRegex(
                ModelCompatibilityFactsError,
                "source-model checksum",
            ):
                load_model_compatibility_facts(forged_report, run)

            forged_provider = json.loads(json.dumps(report))
            forged_provider["inputs"]["model_provider"] = {
                "kind": "forged-provider",
            }
            with self.assertRaisesRegex(
                ModelCompatibilityFactsError,
                "model-provider provenance",
            ):
                load_model_compatibility_facts(forged_provider, run)

            path = run / frozen["artifact"]["relative_path"]
            value = json.loads(path.read_text())
            value["semantics"]["score"] = 1
            data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
            path.write_bytes(data)
            with self.assertRaisesRegex(
                ModelCompatibilityFactsError,
                "missing or failed checksum|changed while being read",
            ):
                load_model_compatibility_facts(report, run)

            report["model_compatibility_facts"]["artifact"].update(
                sha256=sha256(data).hexdigest(),
                size=len(data),
            )
            with self.assertRaisesRegex(
                ModelCompatibilityFactsError,
                "must not contain a verdict or score",
            ):
                load_model_compatibility_facts(report, run)


if __name__ == "__main__":
    unittest.main()
