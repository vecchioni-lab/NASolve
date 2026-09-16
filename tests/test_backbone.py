import json
import tempfile
import unittest
from pathlib import Path

from nasolve.backbone import (
    BackboneError,
    ensure_five_prime_phosphates,
    make_backbone_policy,
    requested_backbone_policy,
    validate_backbone_sites,
)

from .helpers import pdb_record


def atom(serial, name, residue, chain, number, xyz, *, record="ATOM"):
    return pdb_record(
        record,
        serial,
        name,
        residue,
        chain,
        number,
        element="P" if name == "P" else "O" if name.startswith("O") else "C",
        x=xyz[0],
        y=xyz[1],
        z=xyz[2],
    )


def terminal_without_phosphate():
    return [
        atom(1, "O5'", "DC", "D", 1, (0.0, 0.0, 0.0)),
        atom(2, "C5'", "DC", "D", 1, (-1.4, 0.0, 0.0)),
        atom(3, "C4'", "DC", "D", 1, (-2.1, 1.1, 0.0)),
        atom(4, "O3'", "DC", "D", 1, (-3.0, 0.0, 1.0)),
        "TER\n",
        "END\n",
    ]


class BackbonePolicyTests(unittest.TestCase):
    def test_site_modes_are_explicit_and_small(self):
        self.assertEqual(
            validate_backbone_sites({"A:12": "experimental-passthrough", "B:4": "standard"}),
            {"A:12": "experimental_passthrough", "B:4": "standard"},
        )
        with self.assertRaises(BackboneError):
            validate_backbone_sites({"A:12": "gna"})

    def test_frozen_policy_round_trip(self):
        policy = make_backbone_policy({"A:12": "experimental_passthrough"}, allow_unreviewed=True)
        report = {"post_mr_plan": {"backbone_policy": policy}}
        self.assertEqual(requested_backbone_policy(report), policy)
        self.assertEqual(policy["experimental_passthrough_sites"], ["A:12"])


class TerminalPhosphateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_ensure(self, records):
        source = self.root / "source.pdb"
        output = self.root / "output.pdb"
        source.write_text("".join(records), encoding="utf-8")
        before = source.read_bytes()
        report = ensure_five_prime_phosphates(source, output, ("D:1",))
        self.assertEqual(source.read_bytes(), before)
        return report, output.read_text(encoding="utf-8")

    def test_constructs_whole_missing_terminal_phosphate(self):
        report, text = self.run_ensure(terminal_without_phosphate())
        self.assertEqual(report["constructed"][0]["added"], ["P", "OP1", "OP2", "OP3"])
        names = [
            line[12:16].strip()
            for line in text.splitlines()
            if line.startswith(("ATOM  ", "HETATM")) and line[21:22] == "D" and line[22:26].strip() == "1"
        ]
        for name in ("P", "OP1", "OP2", "OP3", "O5'", "C5'"):
            self.assertIn(name, names)

    def test_completes_only_missing_op3(self):
        records = terminal_without_phosphate()
        records[1:1] = [
            atom(20, "P", "DC", "D", 1, (1.6, 0.0, 0.0)),
            atom(21, "OP1", "DC", "D", 1, (2.1, 1.4, 0.0)),
            atom(22, "OP2", "DC", "D", 1, (2.1, -0.7, 1.2)),
        ]
        report, text = self.run_ensure(records)
        self.assertEqual(report["completed"][0]["added"], ["OP3"])
        self.assertEqual(text.count(" OP3 "), 1)

    def test_partial_unknown_terminal_group_fails_closed(self):
        records = terminal_without_phosphate()
        records.insert(1, atom(20, "P", "DC", "D", 1, (1.6, 0.0, 0.0)))
        source = self.root / "source.pdb"
        output = self.root / "output.pdb"
        source.write_text("".join(records), encoding="utf-8")
        with self.assertRaises(BackboneError):
            ensure_five_prime_phosphates(source, output, ("D:1",))
        self.assertFalse(output.exists())

    def test_builder_report_is_json_serializable(self):
        report, _ = self.run_ensure(terminal_without_phosphate())
        json.dumps(report)


if __name__ == "__main__":
    unittest.main()
