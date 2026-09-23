"""Unit tests for the opt-in sequence-reference target compiler (no tools)."""
import copy
import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from nasolve.sequence_reference import (
    SequenceReferenceError,
    compare_sequence_family_inventory,
    compile_sequence_family_targets,
    load_sequence_reference,
    parse_sequence_reference,
)

REFERENCE = (
    Path(__file__).resolve().parents[1] / 'src' / 'nasolve' / 'data'
    / 'sequence_references' / 'w-metal-scaffold.json'
)


def payload():
    return json.loads(REFERENCE.read_text(encoding='utf-8'))


def baseline(reference):
    rows = compile_sequence_family_targets(reference)['sites']
    return {row['site']: row['residue_code'] for row in rows}


class SequenceReferenceTests(unittest.TestCase):
    def test_reference_has_explicit_42_sites_and_original_chain_c_numbering(self):
        ref = load_sequence_reference(REFERENCE)
        self.assertEqual(len(ref.sites), 42)
        self.assertIn('C:8', ref.sites)
        self.assertIn('C:14', ref.sites)
        self.assertNotIn('C:1', ref.sites)
        self.assertEqual(ref.identifier, 'w-metal-scaffold')
        self.assertEqual(len(ref.content_sha256), 64)

    def test_original_scaffold_requires_only_the_two_reference_substitutions(self):
        ref = load_sequence_reference(REFERENCE)
        # Literal sequences from the reviewed original-5W6W inventory, not
        # a copy of the target resource with two deliberately changed entries.
        code = {'A': 'DA', 'C': 'DC', 'G': 'DG', 'T': 'DT'}
        model = {}
        for chain, start, sequence in (
            ('A', 1, 'GAGCAGCCTGTACGGACATCA'), ('B', 1, 'CCGTACA'),
            ('C', 8, 'GGCTGCT'), ('D', 1, 'CTGATGT'),
        ):
            model.update({f'{chain}:{start + offset}': code[base]
                          for offset, base in enumerate(sequence)})
        frozen = dict(model)
        report = compare_sequence_family_inventory(
            ref, model, dataset_site_codes={'A:12': 'DA', 'B:4': 'DT'}
        )
        self.assertEqual(report['target_count'], 42)
        self.assertEqual(report['differences'], [
            {'site': 'A:13', 'before': 'DC', 'after': 'DT', 'source': 'family_reference'},
            {'site': 'B:3', 'before': 'DG', 'after': 'DA', 'source': 'family_reference'},
        ])
        self.assertEqual(model, frozen)

    def test_already_matching_scaffold_needs_no_identity_changes(self):
        ref = load_sequence_reference(REFERENCE)
        report = compare_sequence_family_inventory(ref, baseline(ref))
        self.assertTrue(report['matches'])
        self.assertEqual(report['differences'], [])

    def test_dataset_sequence_overrides_thread_sequence_only_on_declared_chains(self):
        ref = load_sequence_reference(REFERENCE)
        rows = {row['site']: row for row in compile_sequence_family_targets(
            ref, thread_sequences={'B': 'AAAAAAA'}, dataset_sequences={'B': 'GGGGGGG'}
        )['sites']}
        self.assertEqual(rows['B:3']['residue_code'], 'DG')
        self.assertEqual(rows['B:3']['source'], 'dataset_sequence')
        self.assertEqual([x['source'] for x in rows['B:3']['assignments']],
                         ['family_reference', 'thread_sequence', 'dataset_sequence'])
        self.assertEqual(rows['A:13']['residue_code'], 'DT')
        self.assertEqual(rows['A:13']['source'], 'family_reference')

    def test_site_chemistry_survives_plain_sequence_and_dataset_site_wins(self):
        ref = load_sequence_reference(REFERENCE)
        target = compile_sequence_family_targets(
            ref, dataset_sequences={'A': 'G' * 21, 'B': 'G' * 7},
            thread_site_codes={'A:12': '1AP', 'B:4': 'DT'},
            dataset_site_codes={'B:4': 'S6G'},
        )
        rows = {row['site']: row for row in target['sites']}
        self.assertEqual(rows['A:12']['residue_code'], '1AP')
        self.assertEqual(rows['A:12']['source'], 'thread_site_chemistry')
        self.assertEqual(rows['B:4']['residue_code'], 'S6G')
        self.assertEqual([x['residue_code'] for x in rows['B:4']['assignments']],
                         ['DT', 'DG', 'DT', 'S6G'])

    def test_dataset_can_explicitly_replace_inherited_modification_with_canonical(self):
        ref = load_sequence_reference(REFERENCE)
        rows = {row['site']: row for row in compile_sequence_family_targets(
            ref, thread_site_codes={'A:12': '1AP'}, dataset_site_codes={'A:12': 'DA'}
        )['sites']}
        self.assertEqual(rows['A:12']['residue_code'], 'DA')
        self.assertEqual(rows['A:12']['source'], 'dataset_site_chemistry')
        self.assertEqual(rows['A:12']['assignments'][1]['residue_code'], '1AP')

    def test_chain_c_overlay_keeps_residue_ids(self):
        ref = load_sequence_reference(REFERENCE)
        rows = {row['site']: row for row in compile_sequence_family_targets(
            ref, dataset_sequences={'C': 'AAAAAAA'}
        )['sites']}
        self.assertEqual(rows['C:8']['residue_code'], 'DA')
        self.assertEqual(rows['C:14']['residue_code'], 'DA')
        self.assertNotIn('C:1', rows)

    def test_wrong_numbering_is_not_silently_aligned(self):
        ref = load_sequence_reference(REFERENCE)
        model = baseline(ref)
        model['C:1'] = model.pop('C:8')
        with self.assertRaisesRegex(SequenceReferenceError, 'correspondence differs'):
            compare_sequence_family_inventory(ref, model)

    def test_missing_or_extra_model_sites_fail(self):
        ref = load_sequence_reference(REFERENCE)
        for extra in (False, True):
            with self.subTest(extra=extra):
                model = baseline(ref)
                if extra:
                    model['Z:1'] = 'DA'
                else:
                    del model['D:1']
                with self.assertRaises(SequenceReferenceError):
                    compare_sequence_family_inventory(ref, model)

    def test_bad_overlays_fail_without_changing_inputs(self):
        ref = load_sequence_reference(REFERENCE)
        for kw in (
            {'dataset_sequences': {'Z': 'AAAAAAA'}},
            {'dataset_sequences': {'B': 'AAA'}},
            {'thread_sequences': {'B': 'CCCCCCU'}},
            {'thread_sequences': {'B': 'CCCCCCN'}},
            {'dataset_site_codes': {'Z:1': 'DA'}},
            {'thread_site_codes': {'C:1': 'DG'}},
            {'dataset_site_codes': {'A:12': 'base /tmp/x'}},
            {'dataset_site_codes': {'A:12': True}},
            {'dataset_site_codes': {'A:12': 'da'}},
            {'dataset_sequences': []},
            {'thread_site_codes': 'A:12'},
        ):
            with self.subTest(kw=kw):
                original = copy.deepcopy(kw)
                with self.assertRaises(SequenceReferenceError):
                    compile_sequence_family_targets(ref, **kw)
                self.assertEqual(kw, original)

    def test_bad_reference_contracts_fail(self):
        original = payload()
        cases = []
        for key, value in [('schema_version', True), ('schema_version', 2),
                           ('kind', 'all-campaign-families'), ('id', ''), ('chains', [])]:
            p = copy.deepcopy(original); p[key] = value; cases.append(p)
        p = copy.deepcopy(original); p['unrecognized'] = True; cases.append(p)
        for key, value in [('residue_ids', ['1'] * 21), ('residue_ids', list(range(21))),
                           ('sequence', 'NNN'), ('polymer', 'unknown'), ('chain', 'AA')]:
            p = copy.deepcopy(original); p['chains'][0][key] = value; cases.append(p)
        p = copy.deepcopy(original); p['chains'].append(p['chains'][0]); cases.append(p)
        for p in cases:
            with self.subTest(p=p):
                with self.assertRaises(SequenceReferenceError):
                    parse_sequence_reference(p)

    def test_rna_and_insertion_codes_have_explicit_meaning(self):
        ref = parse_sequence_reference({
            'schema_version': 1, 'kind': 'sequence-defined-reference',
            'id': 'rna-example', 'version': '1.0.0',
            'chains': [{'chain': 'X', 'residue_ids': ['-1', '1A', '7'],
                        'polymer': 'RNA', 'sequence': 'ACU'}],
        })
        self.assertEqual(baseline(ref), {'X:-1': 'A', 'X:1A': 'C', 'X:7': 'U'})
        with self.assertRaises(SequenceReferenceError):
            compile_sequence_family_targets(ref, dataset_sequences={'X': 'ACT'})

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'duplicate.json'
            path.write_text('{"schema_version": 1, "schema_version": 2}')
            with self.assertRaisesRegex(SequenceReferenceError, 'Duplicate JSON key'):
                load_sequence_reference(path)

    def test_reference_fingerprint_is_semantic_and_detects_field_changes(self):
        ref = load_sequence_reference(REFERENCE)
        p = payload()
        p['chains'][0]['sequence'] = p['chains'][0]['sequence'].lower()
        self.assertEqual(parse_sequence_reference(p).content_sha256, ref.content_sha256)
        p['chains'][0]['sequence'] = 'A' * 21
        self.assertNotEqual(parse_sequence_reference(p).content_sha256, ref.content_sha256)
        with self.assertRaisesRegex(SequenceReferenceError, 'fingerprint'):
            compile_sequence_family_targets(replace(ref, content_sha256='0' * 64))

    def test_compilation_is_deterministic_and_does_not_share_mutable_inputs(self):
        ref = load_sequence_reference(REFERENCE)
        overlay = {'A:12': '1AP'}
        first = compile_sequence_family_targets(ref, dataset_site_codes=overlay)
        second = compile_sequence_family_targets(ref, dataset_site_codes=overlay)
        self.assertEqual(first, second)
        first['sites'][0]['assignments'][0]['residue_code'] = 'ZZZ'
        self.assertNotEqual(first, second)
        self.assertEqual(overlay, {'A:12': '1AP'})

    def test_reference_name_never_adds_metal_or_terminal_geometry(self):
        ref = load_sequence_reference(REFERENCE)
        target = compile_sequence_family_targets(ref)
        self.assertEqual(set(target), {'schema_version', 'kind', 'reference', 'sites'})
        self.assertEqual(len(target['sites']), 42)
        self.assertEqual(set(x['residue_code'] for x in target['sites']),
                         {'DA', 'DC', 'DG', 'DT'})


if __name__ == '__main__':
    unittest.main()
