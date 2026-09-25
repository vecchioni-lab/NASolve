import unittest

from nasolve.campaign_threads import (
    SequenceThreadError,
    membership_by_dataset,
    parse_sequence_threads,
)


class CampaignThreadTests(unittest.TestCase):
    def test_parses_explicit_membership_and_overlays(self):
        threads = parse_sequence_threads(b"""
schema_version = 1

[sequence_threads.willow]
datasets = ["B", "A"]
sequence_reference = "w-metal-scaffold"

[sequence_threads.willow.sequences]
B = "ccccccc"

[sequence_threads.willow.site_codes]
"A:13" = "1AP"
""")
        self.assertEqual(list(threads), ["willow"])
        thread = threads["willow"]
        self.assertEqual(thread["datasets"], ["A", "B"])
        self.assertEqual(thread["sequences"], {"B": "CCCCCCC"})
        self.assertEqual(thread["site_codes"], {"A:13": "1AP"})
        membership = membership_by_dataset(threads)
        self.assertEqual(membership["A"]["id"], "willow")
        self.assertEqual(membership["B"]["id"], "willow")

    def test_rejects_ambiguous_membership_unknown_reference_and_bad_overlay(self):
        cases = [
            b"""
schema_version = 1
[sequence_threads.one]
datasets = ["A"]
sequence_reference = "w-metal-scaffold"
[sequence_threads.two]
datasets = ["A"]
sequence_reference = "w-metal-scaffold"
""",
            b"""
schema_version = 1
[sequence_threads.one]
datasets = ["A"]
sequence_reference = "future-reference"
""",
            b"""
schema_version = 1
[sequence_threads.one]
datasets = ["A"]
sequence_reference = "w-metal-scaffold"
[sequence_threads.one.site_codes]
"A:13" = "da"
""",
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(SequenceThreadError):
                parse_sequence_threads(payload)

    def test_empty_file_and_unknown_fields_fail_closed(self):
        for payload in (
            b"",
            b"schema_version = 2\n",
            b"schema_version = 1\nunknown = true\n",
            b"""
schema_version = 1
[sequence_threads.bad]
datasets = []
sequence_reference = "w-metal-scaffold"
""",
        ):
            with self.subTest(payload=payload), self.assertRaises(SequenceThreadError):
                parse_sequence_threads(payload)


if __name__ == "__main__":
    unittest.main()
