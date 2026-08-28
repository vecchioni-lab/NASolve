import unittest

from nasolve.cli import build_parser


class CLITests(unittest.TestCase):
    def test_standard_frame_shortcuts(self):
        parser = build_parser()
        w = parser.parse_args(["automr", "dataset", "-W", "--pair", "D:T"])
        self.assertEqual((w.command, w.frame, w.pair), ("automr", "W", "D:T"))
        three_gbi = parser.parse_args(["automr", "dataset", "-3GBI", "--pair", "D:T"])
        self.assertEqual(three_gbi.frame, "3GBI")
        shunted = parser.parse_args([
            "automr", "dataset", "-W", "--pair", "D:T", "--allow-p1-standard",
            "--execute",
        ])
        self.assertTrue(shunted.allow_p1_standard)
        self.assertTrue(shunted.execute)
        mirrored = parser.parse_args([
            "automr", "dataset", "-W", "--pair", "D:T", "--mirror",
        ])
        self.assertTrue(mirrored.mirror)

    def test_postmr_command(self):
        parser = build_parser()
        args = parser.parse_args([
            "postmr", "run_004", "--allow-mr-review", "--modified-pairs-only",
        ])
        self.assertEqual(args.command, "postmr")
        self.assertTrue(args.allow_mr_review)
        self.assertTrue(args.modified_pairs_only)

    def test_autosol_command(self):
        parser = build_parser()
        args = parser.parse_args(["autosol", "run_001"])
        self.assertEqual(args.command, "autosol")
        self.assertEqual(str(args.run), "run_001")

    def test_autorefine_and_checkpoint_commands(self):
        parser = build_parser()
        refine = parser.parse_args([
            "autorefine", "run_001", "--from", "clean", "--cycles", "5",
        ])
        self.assertEqual(refine.command, "autorefine")
        self.assertEqual(refine.from_checkpoint, "clean")
        self.assertEqual(refine.cycles, 5)
        doctor = parser.parse_args([
            "refine-doctor", "run_001", "--from", "refine-003", "--cycles", "3",
        ])
        self.assertEqual(doctor.command, "refine-doctor")
        self.assertEqual(doctor.from_checkpoint, "refine-003")
        self.assertEqual(doctor.cycles, 3)
        listing = parser.parse_args(["checkpoints", "list", "run_001"])
        self.assertEqual(listing.checkpoint_action, "list")
        add = parser.parse_args([
            "checkpoints", "add", "run_001", "--name", "after coot",
            "--model", "fixed.pdb",
        ])
        self.assertEqual(add.name, "after coot")
        self.assertEqual(str(add.model), "fixed.pdb")
        use = parser.parse_args(["checkpoints", "use", "run_001", "refine-001"])
        self.assertEqual(use.checkpoint, "refine-001")
        show = parser.parse_args(["show", "last", "dataset", "--stage", "autosol"])
        self.assertEqual(show.target, "last")
        self.assertEqual(str(show.dataset), "dataset")
        self.assertEqual(show.stage, "autosol")
        inspect = parser.parse_args([
            "show", "run_001", "--checkpoint", "refine-005",
        ])
        self.assertEqual(inspect.checkpoint, "refine-005")


if __name__ == "__main__":
    unittest.main()
