import copy
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from nasolve.construct_registration import (
    ConstructRegistrationError,
    build_construct_registration,
    build_identity_registration,
    expand_logical_sites,
    freeze_construct_registration,
    load_construct_registration,
    logical_inventory_by_copy,
    validate_construct_registration,
)
from nasolve.model_assessment import inspect_pdb

from .helpers import pdb_record


CODES = {"DA", "DC", "DG", "DT"}


def target(*rows):
    return {
        "schema_version": 1,
        "kind": "sequence-family-target",
        "reference": {
            "id": "registration-fixture",
            "version": "1",
            "content_sha256": "a" * 64,
        },
        "sites": [
            {
                "site": site,
                "residue_code": code,
                "source": "family_reference",
                "assignments": [
                    {
                        "source": "family_reference",
                        "residue_code": code,
                    }
                ],
            }
            for site, code in rows
        ],
    }


def assessment(root: Path, residues):
    model = root / "model.pdb"
    model.write_text(
        "".join(
            pdb_record(
                "ATOM",
                serial,
                "C1'",
                code,
                chain,
                resid,
                element="C",
            )
            for serial, (chain, resid, code) in enumerate(residues, 1)
        )
        + "END\n",
        encoding="utf-8",
    )
    return inspect_pdb(model, polymer_ligand_codes=CODES)


class ConstructRegistrationTests(unittest.TestCase):
    def test_identity_fast_path_keeps_logical_sites_authoritative(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(
                root,
                [("A", 1, "DA"), ("A", 2, "DC"), ("B", 1, "DG")],
            )
            result = build_identity_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DT"), ("B:1", "DG")),
            )
            self.assertEqual(result["status"], "REGISTERED_COMPLETE")
            self.assertEqual(result["summary"]["complete_copy_ids"], ["copy_1"])
            self.assertEqual(result["identity"]["mismatch_count"], 1)
            self.assertEqual(
                result["identity"]["mismatches"][0],
                {
                    "copy_id": "copy_1",
                    "logical_site": "A:2",
                    "coordinate_site": "A:2",
                    "coordinate_residue_code": "DC",
                    "target_residue_code": "DT",
                },
            )
            self.assertTrue(
                result["semantics"]["coordinate_labels_are_representation_only"]
            )
            self.assertFalse(result["semantics"]["coordinate_edit_performed"])

    def test_explicit_registration_supports_chain_rename_and_number_offset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(
                root,
                [("M", 101, "DA"), ("M", 102, "DC"), ("Q", 37, "DG")],
            )
            result = build_construct_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC"), ("B:1", "DG")),
                {
                    "copy_1": {
                        "A:1": "M:101",
                        "A:2": "M:102",
                        "B:1": "Q:37",
                    }
                },
                source="guided-fixture",
            )
            self.assertEqual(result["status"], "REGISTERED_COMPLETE")
            mapping = {
                row["logical_site"]: row["coordinate_site"]
                for row in result["copies"][0]["mappings"]
            }
            self.assertEqual(
                mapping,
                {"A:1": "M:101", "A:2": "M:102", "B:1": "Q:37"},
            )
            self.assertEqual(result["identity"]["mismatch_count"], 0)

    def test_one_logical_strand_can_span_multiple_coordinate_chains(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(
                root,
                [("M", 5, "DA"), ("M", 6, "DC"), ("N", 1, "DG")],
            )
            result = build_construct_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC"), ("A:3", "DG")),
                {
                    "copy_1": {
                        "A:1": "M:5",
                        "A:2": "M:6",
                        "A:3": "N:1",
                    }
                },
                source="split-chain-fixture",
            )
            self.assertEqual(result["copies"][0]["status"], "COMPLETE")
            self.assertEqual(result["summary"]["unmapped_coordinate_sites"], [])

    def test_two_complete_copies_expand_one_logical_action_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(
                root,
                [
                    ("M", 1, "DA"),
                    ("M", 2, "DC"),
                    ("N", 1, "DA"),
                    ("N", 2, "DC"),
                ],
            )
            result = build_construct_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC")),
                {
                    "copy_1": {"A:1": "M:1", "A:2": "M:2"},
                    "copy_2": {"A:1": "N:1", "A:2": "N:2"},
                },
                source="multicopy-fixture",
            )
            self.assertEqual(result["status"], "REGISTERED_COMPLETE_MULTICOPY")
            expanded = expand_logical_sites(result, ["A:2"])
            self.assertEqual(
                expanded["targets"],
                [
                    {
                        "copy_id": "copy_1",
                        "logical_site": "A:2",
                        "coordinate_site": "M:2",
                    },
                    {
                        "copy_id": "copy_2",
                        "logical_site": "A:2",
                        "coordinate_site": "N:2",
                    },
                ],
            )
            self.assertEqual(expanded["skipped_partial_copy_ids"], [])
            self.assertFalse(expanded["semantics"]["coordinate_edit_performed"])

    def test_partial_copy_is_recorded_but_not_given_complete_copy_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(
                root,
                [
                    ("M", 1, "DA"),
                    ("M", 2, "DC"),
                    ("N", 1, "DA"),
                    ("N", 2, "DC"),
                ],
            )
            result = build_construct_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC")),
                {
                    "copy_1": {"A:1": "M:1", "A:2": "M:2"},
                    "copy_2": {"A:1": "N:1"},
                },
                source="partial-copy-fixture",
            )
            self.assertEqual(result["status"], "PARTIAL_COPY_PRESENT")
            self.assertEqual(result["summary"]["complete_copy_ids"], ["copy_1"])
            self.assertEqual(result["summary"]["partial_copy_ids"], ["copy_2"])
            self.assertEqual(result["summary"]["unmapped_coordinate_sites"], ["N:2"])
            self.assertEqual(
                result["copies"][1]["missing_logical_sites"],
                ["A:2"],
            )
            expanded = expand_logical_sites(result, ["A:1", "A:2"])
            self.assertEqual(
                [row["coordinate_site"] for row in expanded["targets"]],
                ["M:1", "M:2"],
            )
            self.assertEqual(expanded["skipped_partial_copy_ids"], ["copy_2"])

    def test_only_partial_copy_cannot_receive_logical_mutation_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(root, [("M", 1, "DA")])
            result = build_construct_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC")),
                {"copy_1": {"A:1": "M:1"}},
                source="partial-only-fixture",
            )
            self.assertEqual(result["status"], "PARTIAL_COPY_PRESENT")
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "No complete registered copy",
            ):
                expand_logical_sites(result, ["A:1"])

    def test_coordinate_site_cannot_be_assigned_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(root, [("M", 1, "DA"), ("M", 2, "DC")])
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "assigned more than once",
            ):
                build_construct_registration(
                    model,
                    target(("A:1", "DA"), ("A:2", "DC")),
                    {
                        "copy_1": {"A:1": "M:1", "A:2": "M:2"},
                        "copy_2": {"A:1": "M:1"},
                    },
                    source="bad-fixture",
                )

    def test_unknown_logical_or_coordinate_site_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(root, [("M", 1, "DA")])
            logical_target = target(("A:1", "DA"))
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "unknown logical sites",
            ):
                build_construct_registration(
                    model,
                    logical_target,
                    {"copy_1": {"A:2": "M:1"}},
                    source="bad-logical",
                )
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "absent coordinate site",
            ):
                build_construct_registration(
                    model,
                    logical_target,
                    {"copy_1": {"A:1": "M:2"}},
                    source="bad-coordinate",
                )

    def test_duplicate_assessed_atom_identity_stops_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model_path = root / "model.pdb"
            row = pdb_record("ATOM", 1, "C1'", "DA", "A", 1, element="C")
            model_path.write_text(row + row + "END\n", encoding="utf-8")
            model = inspect_pdb(model_path, polymer_ligand_codes=CODES)
            self.assertEqual(model.duplicate_atom_identities, 1)
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "Duplicate coordinate atom identities",
            ):
                build_identity_registration(model, target(("A:1", "DA")))

    def test_logical_inventory_is_read_only_and_can_exclude_partial_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(
                root,
                [
                    ("M", 1, "DA"),
                    ("M", 2, "DC"),
                    ("N", 1, "DG"),
                ],
            )
            result = build_construct_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DT")),
                {
                    "copy_1": {"A:1": "M:1", "A:2": "M:2"},
                    "copy_2": {"A:1": "N:1"},
                },
                source="inventory-fixture",
            )
            self.assertEqual(
                logical_inventory_by_copy(result),
                {
                    "copy_1": {"A:1": "DA", "A:2": "DC"},
                    "copy_2": {"A:1": "DG"},
                },
            )
            self.assertEqual(
                logical_inventory_by_copy(result, complete_only=True),
                {"copy_1": {"A:1": "DA", "A:2": "DC"}},
            )

    def test_frozen_registration_is_checksum_verified_and_schema_revalidated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run_001"
            (run / "Model").mkdir(parents=True)
            model = assessment(root, [("A", 1, "DA"), ("A", 2, "DC")])
            result = build_identity_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC")),
            )
            frozen = freeze_construct_registration(result, run)
            report = {"construct_registration": frozen}
            self.assertEqual(
                load_construct_registration(report, run),
                result,
            )

            artifact = run / frozen["artifact"]["relative_path"]
            artifact.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "missing or failed checksum|changed while being read",
            ):
                load_construct_registration(report, run)

            forged = artifact.read_bytes()
            report["construct_registration"]["artifact"].update(
                sha256=sha256(forged).hexdigest(),
                size=len(forged),
            )
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "Malformed construct-registration record",
            ):
                load_construct_registration(report, run)

    def test_freeze_refuses_to_overwrite_existing_registration_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run_001"
            (run / "Model").mkdir(parents=True)
            model = assessment(root, [("A", 1, "DA")])
            result = build_identity_registration(
                model,
                target(("A:1", "DA")),
            )
            freeze_construct_registration(result, run)
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "Could not freeze construct registration",
            ):
                freeze_construct_registration(result, run)

    def test_validator_requires_all_model_residues_to_be_accounted_for(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(
                root,
                [("A", 1, "DA"), ("A", 2, "DC"), ("Z", 9, "DG")],
            )
            result = build_construct_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC")),
                {"copy_1": {"A:1": "A:1", "A:2": "A:2"}},
                source="accounting-fixture",
            )
            self.assertEqual(result["summary"]["unmapped_coordinate_sites"], ["Z:9"])

            forged = copy.deepcopy(result)
            forged["summary"]["unmapped_coordinate_sites"] = []
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "Malformed registration summary",
            ):
                validate_construct_registration(forged)

    def test_record_validator_rejects_forged_completeness_or_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(root, [("A", 1, "DA"), ("A", 2, "DC")])
            result = build_identity_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC")),
            )

            forged = copy.deepcopy(result)
            forged["copies"][0]["status"] = "PARTIAL"
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "copy completeness is inconsistent",
            ):
                validate_construct_registration(forged)

            forged = copy.deepcopy(result)
            forged["copies"][0]["mappings"][0]["identity_relation"] = "DIFFERENT"
            with self.assertRaisesRegex(
                ConstructRegistrationError,
                "identity relation disagrees",
            ):
                validate_construct_registration(forged)

    def test_expansion_rejects_unknown_or_duplicate_logical_sites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = assessment(root, [("A", 1, "DA"), ("A", 2, "DC")])
            result = build_identity_registration(
                model,
                target(("A:1", "DA"), ("A:2", "DC")),
            )
            for sites in (["A:3"], ["A:1", "A:1"]):
                with self.subTest(sites=sites), self.assertRaisesRegex(
                    ConstructRegistrationError,
                    "Unknown or duplicate logical site",
                ):
                    expand_logical_sites(result, sites)


if __name__ == "__main__":
    unittest.main()
