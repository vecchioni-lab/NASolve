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


if __name__ == "__main__":
    unittest.main()
