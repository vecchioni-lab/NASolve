"""Synthetic connectivity regressions; no experimental coordinate files are used."""

import tempfile
import unittest
from pathlib import Path

from nasolve.phosphate import PhosphateError, sanitize_phosphates

from .helpers import pdb_record


def atom(
    serial, name, residue, chain, number, xyz, *, insertion=" ", altloc=" ",
    record="HETATM",
):
    line = pdb_record(
        record, serial, name, residue, chain, number,
        element="P" if name == "P" else name[0],
        x=xyz[0], y=xyz[1], z=xyz[2],
    )
    return line[:16] + altloc + line[17:26] + insertion + line[27:]


def phosphate(
    *, chain="A", number=12, previous=11, insertion=" ", residue="1AP",
    start=1, shift=0.0, terminal=False, alias=False,
):
    """One bonded phosphate, flanking backbone atoms, and an extra OP3."""
    aliases = {"OP1": "O1P", "OP2": "O2P", "OP3": "O3P",
               "O5'": "O5*", "O3'": "O3*"} if alias else {}
    records = []

    def add(serial, name, code, resid, xyz, *, ins=" ", kind="HETATM"):
        records.append(atom(
            serial, aliases.get(name, name), code, chain, resid,
            (xyz[0], xyz[1] + shift, xyz[2]), insertion=ins, record=kind,
        ))

    if not terminal:
        add(start, "O3'", "DT", previous, (-0.53, -0.76, -1.308), kind="ATOM")
    for index, (name, xyz) in enumerate([
        ("P", (0.0, 0.0, 0.0)),
        ("OP1", (-0.5, 1.4, 0.0)),
        ("OP2", (-0.5, -0.7, 1.212)),
        ("O5'", (1.6, 0.0, 0.0)),
        ("OP3", (-0.5, -0.9, -1.2)),
        ("C5'", (2.9, 0.0, 0.0)),
        ("C4'", (3.7, 1.2, 0.0)),
        ("C3'", (4.2, 0.0, 1.2)),
        ("O3'", (5.0, 0.0, 0.0)),
        ("C1'", (3.4, 2.1, 1.0)),
        ("N1", (3.4, 3.4, 1.0)),
    ], 1):
        add(start + index, name, residue, number, xyz, ins=insertion)
    add(start + 12, "P", "DC", number + 1, (6.6, 0.0, 0.0), kind="ATOM")
    return records


def without_extra(records):
    return [line for line in records if line[12:16].strip() not in {"OP3", "O3P"}]


class PhosphateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def run_cleanup(self, records, **kwargs):
        source = self.root / "raw.pdb"
        output = self.root / "cleaned.pdb"
        original = "".join(records)
        source.write_text(original)
        report = sanitize_phosphates(source, output, **kwargs)
        self.assertEqual(source.read_text(), original)
        return report, output.read_text()

    def assert_rejected(self, records, **kwargs):
        source = self.root / "invalid.pdb"
        output = self.root / "rejected.pdb"
        original = "".join(records)
        source.write_text(original)
        with self.assertRaises(PhosphateError):
            sanitize_phosphates(source, output, **kwargs)
        self.assertEqual(source.read_text(), original)

    def test_internal_extras_removed_and_terminal_and_all_other_records_preserved(self):
        first = phosphate()
        second = phosphate(chain="B", number=4, previous=3, residue="OHU", start=21, shift=20)
        terminal = phosphate(chain="D", number=1, residue="DC", start=41, shift=40, terminal=True)
        unrelated = atom(99, "MG", "MG", "Z", 1, (80, 0, 0))
        records = ["REMARK synthetic phosphate regression\n", *first, "TER\n",
                   *second, "TER\n", *terminal, "TER\n", unrelated, "END\n"]
        report, cleaned = self.run_cleanup(records)
        self.assertEqual({row["site"] for row in report["removed"]}, {"A:12", "B:4"})
        self.assertEqual({row["atom"] for row in report["removed"]}, {"OP3"})
        self.assertEqual({row["site"] for row in report["retained"]}, {"D:1"})
        expected = ["REMARK synthetic phosphate regression\n", *without_extra(first), "TER\n",
                    *without_extra(second), "TER\n", *terminal, "TER\n", unrelated, "END\n"]
        self.assertEqual(cleaned, "".join(expected))

    def test_numbering_gaps_and_insertion_codes_do_not_define_connectivity(self):
        records = phosphate(previous=3, number=12, insertion="B") + ["END\n"]
        report, cleaned = self.run_cleanup(records)
        self.assertEqual([row["site"] for row in report["removed"]], ["A:12B"])
        self.assertEqual(cleaned, "".join(without_extra(records)))

    def test_reused_serials_do_not_prevent_unambiguous_coordinate_cleanup(self):
        records = [
            *phosphate(), "TER\n",
            *phosphate(chain="B", number=4, previous=3, residue="OHU", shift=20),
            "TER\n",
            *phosphate(chain="D", number=1, residue="DC", shift=40, terminal=True),
            "END\n",
        ]
        # Model merges can retain per-monomer numbering. Even serial zero does
        # not obscure the actual chain/residue/name/alternate atom identity.
        for serial in ("    0", "    6"):
            with self.subTest(serial=serial):
                raw = [line[:6] + serial + line[11:]
                       if line.startswith(("ATOM  ", "HETATM")) else line
                       for line in records]
                report, cleaned = self.run_cleanup(raw)
                self.assertEqual({row["site"] for row in report["removed"]}, {"A:12", "B:4"})
                expected = "".join(line for line in raw if not (
                    line.startswith(("ATOM  ", "HETATM")) and line[21] in "AB"
                    and line[12:16].strip() == "OP3"
                ))
                self.assertEqual(cleaned, expected)

    def test_reused_serial_removes_only_matching_atom_bookkeeping(self):
        records = phosphate()
        extra = next(line for line in records if line[12:16].strip() == "OP3")
        unrelated = atom(6, "O", "HOH", "Z", 99, (80, 0, 0))
        bookkeeping = []
        removed = []
        for record in ("ANISOU", "SIGATM", "SIGUIJ"):
            removed.append(record + extra[6:])
            bookkeeping += [removed[-1], record + unrelated[6:]]
        records += [unrelated, *bookkeeping, "END\n"]
        _, cleaned = self.run_cleanup(records)
        self.assertEqual(cleaned, "".join(line for line in records
                         if line != extra and line not in removed))

    def test_reused_serial_in_conect_still_requires_inspection(self):
        for connection in ("CONECT    6    2\n", "CONECT    2    6\n"):
            with self.subTest(connection=connection):
                records = phosphate() + [
                    atom(6, "O", "HOH", "Z", 99, (80, 0, 0)),
                    connection, "END\n",
                ]
                self.assert_rejected(records)

    def test_unrelated_unique_conect_survives_other_reused_serials(self):
        records = phosphate() + [
            atom(6, "O", "HOH", "Z", 99, (80, 0, 0)),
            "CONECT   10   13\n", "END\n",
        ]
        _, cleaned = self.run_cleanup(records)
        self.assertEqual(cleaned, "".join(without_extra(records)))

    def test_atom_bookkeeping_identity_includes_model_and_ter_context(self):
        first = phosphate()
        extra = next(line for line in first if line[12:16].strip() == "OP3")
        anisou = "ANISOU" + extra[6:]
        for boundary, prefix, suffix in (
            ("TER\n", [], []),
            ("ENDMDL\nMODEL        2\n", ["MODEL        1\n"], ["ENDMDL\n"]),
        ):
            with self.subTest(boundary=boundary):
                # A separate segment/model has an isolated same-named atom;
                # it is outside nucleotide cleanup and keeps its own ANISOU.
                records = [*prefix, *first, anisou, boundary, extra, anisou, *suffix, "END\n"]
                _, cleaned = self.run_cleanup(records)
                expected = [*prefix, *without_extra(first), boundary, extra, anisou, *suffix, "END\n"]
                self.assertEqual(cleaned, "".join(expected))

    def test_conect_with_duplicated_phosphorus_endpoint_is_ambiguous(self):
        self.assert_rejected(phosphate() + [
            atom(2, "O", "HOH", "Z", 99, (80, 0, 0)),
            "CONECT    6    2\n", "END\n",
        ])

    def test_legacy_atom_aliases_are_cleaned_without_renaming_survivors(self):
        records = phosphate(alias=True) + ["END\n"]
        report, cleaned = self.run_cleanup(records)
        self.assertEqual([row["atom"] for row in report["removed"]], ["O3P"])
        self.assertEqual(cleaned, "".join(without_extra(records)))

    def test_ter_break_preserves_terminal_extra_even_when_other_segment_is_close(self):
        records = phosphate()
        records.insert(1, "TER\n")
        report, cleaned = self.run_cleanup(records)
        self.assertEqual(report["removed"], [])
        self.assertEqual([row["site"] for row in report["retained"]], ["A:12"])
        self.assertEqual(cleaned, "".join(records))

    def test_models_do_not_supply_each_others_incoming_bond(self):
        records = phosphate()
        records = ["MODEL        1\n", records[0], "ENDMDL\n",
                   "MODEL        2\n", *records[1:], "ENDMDL\n", "END\n"]
        report, cleaned = self.run_cleanup(records)
        self.assertEqual(report["removed"], [])
        self.assertEqual(cleaned, "".join(records))

    def test_missing_remaining_phosphate_atoms_fail_without_guessing_coordinates(self):
        for missing in ("P", "OP1", "OP2", "O5'"):
            with self.subTest(missing=missing):
                records = [line for line in phosphate() if not (
                    line[22:26].strip() == "12" and line[12:16].strip() == missing
                )]
                self.assert_rejected(records)

    def test_duplicate_remaining_oxygen_alias_is_ambiguous(self):
        records = phosphate()
        records.insert(4, atom(98, "O1P", "1AP", "A", 12, (-0.5, 1.4, 0.0)))
        self.assert_rejected(records)

    def test_invalid_retained_bond_stops_cleanup(self):
        records = phosphate()
        records = [
            atom(5, "O5'", "1AP", "A", 12, (3.2, 0, 0))
            if line[12:16].strip() == "O5'" else line
            for line in records
        ]
        self.assert_rejected(records)

    def test_two_incoming_oxygen_candidates_fail_closed(self):
        records = phosphate()
        records.insert(1, atom(98, "O3'", "DG", "A", 10, (-1.6, 0, 0), record="ATOM"))
        self.assert_rejected(records)

    def test_alternate_phosphate_atoms_are_not_arbitrarily_selected(self):
        records = phosphate()
        index = next(i for i, line in enumerate(records) if line[12:16].strip() == "OP1")
        records[index:index + 1] = [
            atom(3, "OP1", "1AP", "A", 12, (-0.5, 1.4, 0), altloc="A"),
            atom(98, "OP1", "1AP", "A", 12, (-0.5, 1.3, 0.2), altloc="B"),
        ]
        self.assert_rejected(records)

    def test_reference_connection_prevents_damaged_link_being_classified_terminal(self):
        reference = self.root / "reference.pdb"
        reference.write_text("".join(phosphate()))
        damaged = phosphate()
        damaged[0] = atom(1, "O3'", "DT", "A", 11, (-4, 0, 0), record="ATOM")
        self.assert_rejected(damaged, reference_model=reference)

    def test_reference_outgoing_connection_must_also_survive(self):
        reference = self.root / "reference.pdb"
        reference.write_text("".join(phosphate()))
        damaged = phosphate()
        damaged[-1] = atom(13, "P", "DC", "A", 13, (9, 0, 0), record="ATOM")
        self.assert_rejected(damaged, reference_model=reference)

    def test_reference_terminal_cannot_gain_an_incoming_contact_silently(self):
        reference = self.root / "terminal_reference.pdb"
        reference.write_text("".join(phosphate(terminal=True)))
        self.assert_rejected(phosphate(), reference_model=reference)

    def test_unrelated_ligand_atom_named_op3_is_outside_nucleotide_cleanup(self):
        records = [
            atom(1, "OP3", "XYZ", "L", 1, (0, 0, 0)),
            atom(2, "C7", "XYZ", "L", 1, (1.4, 0, 0)),
            "END\n",
        ]
        report, cleaned = self.run_cleanup(records)
        self.assertEqual(report["removed"], [])
        self.assertEqual(report["checked"], [])
        self.assertEqual(cleaned, "".join(records))

    def test_check_sites_revalidate_after_op3_was_already_removed(self):
        reference = self.root / "prepared.pdb"
        reference.write_text("".join(without_extra(phosphate())))
        records = without_extra(phosphate())
        report, cleaned = self.run_cleanup(records, reference_model=reference, check_sites=("A:12",))
        self.assertEqual(report["removed"], [])
        self.assertIn("A:12", {row["site"] for row in report["checked"]})
        self.assertEqual(cleaned, "".join(records))
        damaged = [line for line in records if line[12:16].strip() != "OP2"]
        self.assert_rejected(damaged, reference_model=reference, check_sites=("A:12",))

    def test_deleted_anisou_and_conect_references_are_removed_but_other_records_remain(self):
        records = phosphate()
        op3 = next(line for line in records if line[12:16].strip() == "OP3")
        op1 = next(line for line in records if line[12:16].strip() == "OP1")
        anisou_extra = "ANISOU" + op3[6:28] + "   1000   1000   1000      0      0      0       O\n"
        anisou_kept = "ANISOU" + op1[6:28] + "   1000   1000   1000      0      0      0       O\n"
        records += [anisou_extra, anisou_kept, "CONECT    2    3    4    5    6\n",
                    "CONECT    6    2\n", "CONECT   10   13\n", "END\n"]
        _, cleaned = self.run_cleanup(records)
        self.assertNotIn(anisou_extra, cleaned)
        self.assertIn(anisou_kept, cleaned)
        self.assertIn("CONECT   10   13\n", cleaned)
        connections = [line for line in cleaned.splitlines() if line.startswith("CONECT")]
        serials = [int(line[start:start + 5]) for line in connections
                   for start in range(6, len(line), 5) if line[start:start + 5].strip()]
        self.assertNotIn(6, serials)
        self.assertEqual([line for line in cleaned.splitlines(keepends=True)
                          if line.startswith(("ATOM  ", "HETATM"))], without_extra(phosphate()))

    def test_explicit_cross_chain_phosphate_link_requires_review(self):
        records = phosphate(terminal=True)
        other = atom(98, "O3'", "DT", "B", 11, (-0.53, -0.76, -1.308), record="ATOM")
        fields = list(" " * 80)
        fields[:6] = "LINK  "
        fields[12:16] = " O3'"
        fields[17:20] = " DT"
        fields[21] = "B"
        fields[22:26] = "  11"
        fields[42:46] = "   P"
        fields[47:50] = "1AP"
        fields[51] = "A"
        fields[52:56] = "  12"
        self.assert_rejected(["".join(fields) + "\n", *records, "TER\n", other, "END\n"])
