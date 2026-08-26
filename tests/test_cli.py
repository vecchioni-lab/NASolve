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


if __name__ == "__main__":
    unittest.main()
