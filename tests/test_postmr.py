import json
import shutil
import tempfile
import unittest
from pathlib import Path

from nasolve.curated_ligands import validate_curated_dictionary
from nasolve.postmr import (
    MutationAction,
    PostMRPreparationError,
    _coot_script,
    _patch_narestraints_records,
    _restore_shared_parent_coordinates,
    build_mutation_plan,
    prepare_postmr,
    residue_name,
    scan_anomalous_candidates,
)

from .helpers import make_postmr_report, make_ready_set, pdb_record


PROTECTED_PARENT_ATOMS = (
    "P",
    "OP1",
    "OP2",
    "O5'",
    "C5'",
    "C4'",
    "O4'",
    "C3'",
    "O3'",
    "C2'",
    "C1'",
)


def postmr_model_text(first: str = "DE", second: str = "DG") -> str:
    return "".join([
        pdb_record("HETATM", 1, "P", first, "A", 12),
        pdb_record("ATOM", 2, "P", second, "B", 4),
        pdb_record("HETATM", 3, "MG", "MG", "A", 50, element="MG"),
        "END\n",
    ])


def make_data_root(root: Path) -> Path:
    data = root / "data"
    ligands = data / "ligands"
    restraints = data / "restraints"
    ligands.mkdir(parents=True)
    restraints.mkdir()
    (ligands / "DE.cif").write_text(
        "data_comp_DE\nloop_\n_chem_comp_bond.comp_id\n"
        "_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n"
        "DE C4 S4\nDE P O5'\n#\n"
    )
    package = Path(__file__).parents[1] / "src" / "nasolve" / "data" / "restraints"
    for name in ("5W6W_Std_padd.txt", "5W6W_secondary_structure.eff"):
        shutil.copyfile(package / name, restraints / name)
    return data


class PostMRTests(unittest.TestCase):
    def test_w_frame_keeps_de_and_runs_readyset_without_coot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdb"
            source.write_text(postmr_model_text())
            run = root / "run_004"
            make_postmr_report(run, source)
            calls = []

            def fake_builder(pdb: Path, pairs: Path, output: Path) -> None:
                calls.append((pdb.read_text(), pairs.read_text()))
                output.write_text("geometry_restraints.edits {}\n")

            result = prepare_postmr(
                run,
                make_ready_set(root),
                data_root=make_data_root(root),
                narestraints_builder=fake_builder,
            )
            self.assertEqual(result.status, "POSTMR_READY")
            self.assertEqual(residue_name(result.model_path, "A:12"), "DE")
            self.assertEqual(residue_name(result.model_path, "B:4"), "DG")
            self.assertIn(" DE ", calls[0][0])
            self.assertEqual(calls[0][1], "A 11:13\nB 5:3\n")
            self.assertFalse((result.postmr_directory / "Coot" / "coot.log").exists())
            readyset = (result.postmr_directory / "ReadySet" / "ready_set.log").read_text()
            self.assertIn("user provided restraints", readyset)
            report = json.loads((run / "report.json").read_text())
            self.assertEqual(report["stage"], "postmr")
            self.assertEqual(report["postmr"]["mutation_actions"][0]["method"], "none")
            self.assertIsNone(report["postmr"]["component_identity"]["DE"]["deposition_code"])

    def test_secondary_template_has_base_pairs_but_no_stacking_pairs(self):
        template = (
            Path(__file__).parents[1]
            / "src" / "nasolve" / "data" / "restraints"
            / "5W6W_secondary_structure.eff"
        ).read_text()
        self.assertEqual(template.count("base_pair {"), 17)
        self.assertNotIn("stacking_pair", template)
        self.assertNotIn("file_name", template)
        self.assertNotIn("unit_cell", template)

    def test_legacy_e_8ro_report_is_migrated_to_de(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdb"
            source.write_text(postmr_model_text())
            run = root / "run_legacy"
            make_postmr_report(run, source, first="8RO")

            def fake_builder(_pdb: Path, _pairs: Path, output: Path) -> None:
                output.write_text("geometry_restraints.edits {}\n")

            result = prepare_postmr(
                run,
                make_ready_set(root),
                data_root=make_data_root(root),
                narestraints_builder=fake_builder,
            )
            self.assertEqual(residue_name(result.model_path, "A:12"), "DE")

    def test_fd_pair_uses_canonical_parents_and_dictionary_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model.pdb"
            model.write_text(postmr_model_text("DC", "DG"))
            run = root / "run"
            report_path = make_postmr_report(
                run,
                model,
                first="DF",
                second="1AP",
                requested="F:D",
            )
            report = json.loads(report_path.read_text())
            actions = build_mutation_plan(report, model)
            self.assertEqual(
                [
                    (action.site, action.after, action.method, action.parent_code)
                    for action in actions
                ],
                [
                    ("A:12", "DF", "coot-parent-overlap", "DT"),
                    ("B:4", "1AP", "coot-parent-overlap", "DA"),
                ],
            )
            self.assertEqual(actions[0].deposition_code, "A1AAZ")
            self.assertEqual(actions[1].deposition_code, "1AP")

            script = _coot_script(
                model,
                root / "raw.pdb",
                actions,
                {"DF": root / "DF.cif", "1AP": root / "1AP.cif"},
                {"A:12": root / "A12-DT.pdb", "B:4": root / "B4-DA.pdb"},
            )
            self.assertIn("mutate_base(imol, 'A', 12, '', 'DT')", script)
            self.assertIn("mutate_base(imol, 'B', 4, '', 'DA')", script)
            self.assertIn("get_monomer_from_dictionary('DF', 0)", script)
            self.assertIn("get_monomer_from_dictionary('1AP', 0)", script)
            self.assertIn("overlap_ligands_py", script)
            self.assertIn("add_ligand_delete_residue_copy_molecule", script)
            self.assertIn("ligand_imol, 'A', 1", script)
            self.assertIn("delete_hydrogen_atoms", script)

    def test_shared_parent_coordinates_are_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent.pdb"
            raw = root / "raw.pdb"
            output = root / "restored.pdb"
            parent_lines = []
            raw_lines = []
            for serial, atom in enumerate(PROTECTED_PARENT_ATOMS, 1):
                element = "P" if atom == "P" else atom[0]
                raw_atom = {"OP1": "O1P", "OP2": "O2P"}.get(atom, atom)
                parent_lines.append(
                    pdb_record(
                        "ATOM",
                        serial,
                        atom,
                        "DT",
                        "A",
                        12,
                        element=element,
                        x=float(serial),
                        y=float(serial + 1),
                        z=float(serial + 2),
                        occupancy=0.75,
                        b_factor=17.0,
                    )
                )
                raw_lines.append(
                    pdb_record(
                        "HETATM",
                        serial,
                        raw_atom,
                        "DF",
                        "A",
                        12,
                        element=element,
                        x=float(serial + 100),
                        y=float(serial + 101),
                        z=float(serial + 102),
                    )
                )
            parent_lines.extend([
                pdb_record(
                    "ATOM", 90, "C2", "DT", "A", 12, element="C", x=10.0,
                    occupancy=0.75, b_factor=17.0,
                ),
                pdb_record(
                    "ATOM", 91, "O2", "DT", "A", 12, element="O", x=11.0,
                    occupancy=0.50, b_factor=33.0,
                ),
            ])
            raw_lines.extend([
                pdb_record(
                    "HETATM", 90, "C2", "DF", "A", 12, element="C",
                    x=100.0, y=100.0,
                ),
                pdb_record(
                    "HETATM", 99, "S1", "DF", "A", 12, element="S",
                    x=100.0, y=102.0,
                ),
            ])
            parent.write_text("".join(parent_lines) + "END\n")
            raw.write_text("".join(raw_lines) + "END\n")
            action = MutationAction(
                "A:12",
                "DC",
                "DF",
                "coot-parent-overlap",
                parent_code="DT",
                deposition_code="A1AAZ",
            )
            restoration = _restore_shared_parent_coordinates(
                raw,
                output,
                (action,),
                {"A:12": parent},
            )
            records = {
                line[12:16].strip(): line
                for line in output.read_text().splitlines()
                if line.startswith(("ATOM", "HETATM"))
            }
            self.assertEqual(float(records["P"][30:38]), 1.0)
            self.assertEqual(float(records["P"][54:60]), 0.75)
            self.assertEqual(float(records["P"][60:66]), 17.0)
            self.assertEqual(float(records["O1P"][30:38]), 2.0)
            self.assertEqual(float(records["O2P"][30:38]), 3.0)
            self.assertEqual(float(records["S1"][30:38]), 12.0)
            self.assertEqual(float(records["S1"][38:46]), 0.0)
            self.assertEqual(float(records["S1"][54:60]), 0.50)
            self.assertEqual(float(records["S1"][60:66]), 33.0)
            self.assertEqual(restoration["A:12"]["count"], 12)
            self.assertEqual(
                restoration["A:12"]["substitutions"],
                [{
                    "parent_atom": "O2",
                    "target_atom": "S1",
                    "anchor_atom": "C2",
                    "bond_length": 2.0,
                    "placement": "canonical-parent-vector",
                }],
            )

    def test_curated_topology_validation_rejects_missing_or_forbidden_bonds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing.cif"
            missing.write_text(
                "data_DF\nloop_\n_chem_comp_bond.atom_id_1\n"
                "_chem_comp_bond.atom_id_2\nC2 N3\n#\n"
            )
            with self.assertRaisesRegex(ValueError, "missing C2-S1"):
                validate_curated_dictionary("DF", missing)

            forbidden = root / "forbidden.cif"
            forbidden.write_text(
                "data_DF\nloop_\n_chem_comp_bond.atom_id_1\n"
                "_chem_comp_bond.atom_id_2\nC2 S1\nN3 S1\n#\n"
            )
            with self.assertRaisesRegex(ValueError, "forbidden N3-S1"):
                validate_curated_dictionary("DF", forbidden)

    def test_s6g_sulfur_is_projected_along_parent_o6_vector(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent-dg.pdb"
            raw = root / "raw-s6g.pdb"
            output = root / "restored-s6g.pdb"
            parent_lines = []
            raw_lines = []
            for serial, atom in enumerate(PROTECTED_PARENT_ATOMS, 1):
                element = "P" if atom == "P" else atom[0]
                parent_lines.append(
                    pdb_record("ATOM", serial, atom, "DG", "B", 4, element=element)
                )
                raw_lines.append(
                    pdb_record(
                        "HETATM", serial, atom, "S6G", "B", 4,
                        element=element, x=100.0,
                    )
                )
            parent_lines.extend([
                pdb_record("ATOM", 90, "C6", "DG", "B", 4, element="C", x=5.0),
                pdb_record(
                    "ATOM", 91, "O6", "DG", "B", 4, element="O", x=5.0, y=1.0,
                    occupancy=0.60, b_factor=24.0,
                ),
            ])
            raw_lines.extend([
                pdb_record(
                    "HETATM", 90, "C6", "S6G", "B", 4,
                    element="C", x=100.0, y=100.0,
                ),
                pdb_record(
                    "HETATM", 91, "S6", "S6G", "B", 4,
                    element="S", x=98.0, y=100.0,
                ),
            ])
            parent.write_text("".join(parent_lines) + "END\n")
            raw.write_text("".join(raw_lines) + "END\n")
            action = MutationAction(
                "B:4", "DG", "S6G", "coot-parent-overlap",
                parent_code="DG", deposition_code="S6G",
            )
            restoration = _restore_shared_parent_coordinates(
                raw, output, (action,), {"B:4": parent}
            )
            records = {
                line[12:16].strip(): line
                for line in output.read_text().splitlines()
                if line.startswith(("ATOM", "HETATM"))
            }
            self.assertEqual(float(records["S6"][30:38]), 5.0)
            self.assertEqual(float(records["S6"][38:46]), 2.0)
            self.assertEqual(float(records["S6"][54:60]), 0.60)
            self.assertEqual(
                restoration["B:4"]["substitutions"][0]["placement"],
                "canonical-parent-vector",
            )

    def test_legacy_df_narestraints_atom_mapping_is_patched_process_locally(self):
        original = [
            {"Ligand code": "DF", "Base Analog": "T", "O2": "S2"},
            {"Ligand code": "1AP", "Base Analog": "D", "N2": "N2"},
        ]
        patched, corrections = _patch_narestraints_records(original, {"DF", "1AP"})
        self.assertEqual(original[0]["O2"], "S2")
        self.assertEqual(patched[0]["O2"], "S1")
        self.assertEqual(
            corrections,
            [{
                "ligand_code": "DF",
                "canonical_atom": "O2",
                "before": "S2",
                "after": "S1",
                "scope": "process-local",
            }],
        )

        already_fixed, corrections = _patch_narestraints_records(
            [{"Ligand code": "DF", "O2": "S1"}], {"DF"}
        )
        self.assertEqual(already_fixed[0]["O2"], "S1")
        self.assertEqual(corrections, [])

        s6g, corrections = _patch_narestraints_records(
            [{"Ligand code": "S6G", "C5": "C5 "}], {"S6G"}
        )
        self.assertEqual(s6g[0]["C5"], "C5")
        self.assertEqual(corrections[0]["before"], "C5 ")
        self.assertEqual(corrections[0]["after"], "C5")

    def test_q_uses_s6g_dictionary_overlap_from_dg_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model.pdb"
            model.write_text(postmr_model_text("DC", "DG"))
            run = root / "run"
            report_path = make_postmr_report(
                run,
                model,
                first="DC",
                second="S6G",
                requested="C:Q",
            )
            report = json.loads(report_path.read_text())
            actions = build_mutation_plan(report, model)
            self.assertEqual(actions[0].method, "none")
            self.assertEqual(
                (actions[1].after, actions[1].method, actions[1].parent_code),
                ("S6G", "coot-parent-overlap", "DG"),
            )

    def test_q_ic_pair_uses_dg_and_dc_parents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model.pdb"
            model.write_text(postmr_model_text("DC", "DG"))
            run = root / "run"
            report_path = make_postmr_report(
                run,
                model,
                first="S6G",
                second="C38",
                requested="Q:iC",
            )
            actions = build_mutation_plan(json.loads(report_path.read_text()), model)
            self.assertEqual(
                [(action.after, action.parent_code) for action in actions],
                [("S6G", "DG"), ("C38", "DC")],
            )

    def test_c38_iodine_is_projected_outward_from_c5(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent-dc.pdb"
            raw = root / "raw-c38.pdb"
            output = root / "restored-c38.pdb"
            dictionary = root / "C38.cif"
            dictionary.write_text(
                "data_C38\nloop_\n"
                "_chem_comp_atom.comp_id\n"
                "_chem_comp_atom.atom_id\n"
                "_chem_comp_atom.pdbx_model_Cartn_x_ideal\n"
                "_chem_comp_atom.pdbx_model_Cartn_y_ideal\n"
                "_chem_comp_atom.pdbx_model_Cartn_z_ideal\n"
                "C38 C5 0.0 0.0 0.0\n"
                "C38 I 0.0 2.095 0.0\n#\n"
            )
            parent_lines = []
            raw_lines = []
            for serial, atom in enumerate(PROTECTED_PARENT_ATOMS, 1):
                element = "P" if atom == "P" else atom[0]
                parent_lines.append(
                    pdb_record("ATOM", serial, atom, "DC", "B", 4, element=element)
                )
                raw_lines.append(
                    pdb_record(
                        "HETATM", serial, atom, "C38", "B", 4,
                        element=element, x=100.0,
                    )
                )
            parent_lines.extend([
                pdb_record("ATOM", 90, "C4", "DC", "B", 4, element="C", x=-1.0),
                pdb_record(
                    "ATOM", 91, "C5", "DC", "B", 4, element="C", y=1.0,
                    occupancy=0.65, b_factor=27.0,
                ),
                pdb_record("ATOM", 92, "C6", "DC", "B", 4, element="C", x=1.0),
            ])
            raw_lines.extend([
                pdb_record("HETATM", 90, "C4", "C38", "B", 4, element="C"),
                pdb_record(
                    "HETATM", 91, "C5", "C38", "B", 4,
                    element="C", x=100.0, y=100.0,
                ),
                pdb_record(
                    "HETATM", 93, "I", "C38", "B", 4,
                    element="I", x=101.514, y=100.0,
                ),
                pdb_record("HETATM", 92, "C6", "C38", "B", 4, element="C"),
            ])
            parent.write_text("".join(parent_lines) + "END\n")
            raw.write_text("".join(raw_lines) + "END\n")
            action = MutationAction(
                "B:4", "DG", "C38", "coot-parent-overlap",
                parent_code="DC", deposition_code="C38",
            )
            restoration = _restore_shared_parent_coordinates(
                raw,
                output,
                (action,),
                {"B:4": parent},
                {"C38": dictionary},
            )
            records = {
                line[12:16].strip(): line
                for line in output.read_text().splitlines()
                if line.startswith(("ATOM", "HETATM"))
            }
            self.assertAlmostEqual(float(records["I"][30:38]), 0.0, places=3)
            self.assertAlmostEqual(float(records["I"][38:46]), 3.095, places=3)
            self.assertEqual(float(records["I"][54:60]), 0.65)
            self.assertEqual(float(records["I"][60:66]), 27.0)
            self.assertEqual(
                restoration["B:4"]["substitutions"][0]["placement"],
                "canonical-ring-outward-bisector",
            )
            self.assertEqual(
                restoration["B:4"]["substitutions"][0]["bond_length_source"],
                "dictionary-ideal-coordinates",
            )

    def test_anomalous_scan_is_element_driven_and_nucleotide_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "heavy-atoms.pdb"
            model.write_text("".join([
                pdb_record("HETATM", 1, "C1'", "C38", "A", 12, element="C"),
                pdb_record("HETATM", 2, "O4'", "C38", "A", 12, element="O"),
                pdb_record("HETATM", 3, "I", "C38", "A", 12, element="I"),
                pdb_record("HETATM", 4, "C1'", "NEW", "B", 4, element="C"),
                pdb_record("HETATM", 5, "C3'", "NEW", "B", 4, element="C"),
                pdb_record("HETATM", 6, "BR", "NEW", "B", 4, element=""),
                pdb_record("HETATM", 7, "I", "IOD", "C", 1, element="I"),
                pdb_record("HETATM", 8, "S6", "S6G", "D", 4, element="S"),
                "END\n",
            ]))
            candidates = scan_anomalous_candidates(model)
            self.assertEqual(
                [(item["site"], item["element"], item["element_source"]) for item in candidates],
                [
                    ("A:12", "I", "pdb-element-column"),
                    ("B:4", "BR", "atom-name-fallback"),
                ],
            )

    def test_review_result_requires_explicit_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdb"
            source.write_text(postmr_model_text())
            run = root / "run"
            report_path = make_postmr_report(run, source)
            report = json.loads(report_path.read_text())
            report["status"] = "MR_REVIEW"
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(PostMRPreparationError, "--allow-mr-review"):
                prepare_postmr(
                    run,
                    make_ready_set(root),
                    data_root=make_data_root(root),
                    narestraints_builder=lambda *_: None,
                )

    def test_completed_postmr_reports_clear_non_overwrite_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdb"
            source.write_text(postmr_model_text())
            run = root / "run"
            report_path = make_postmr_report(run, source)
            report = json.loads(report_path.read_text())
            report["stage"] = "postmr"
            report["status"] = "POSTMR_READY"
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(
                PostMRPreparationError, "PostMR is already complete"
            ):
                prepare_postmr(
                    run,
                    make_ready_set(root),
                    data_root=make_data_root(root),
                    narestraints_builder=lambda *_: None,
                )


if __name__ == "__main__":
    unittest.main()
