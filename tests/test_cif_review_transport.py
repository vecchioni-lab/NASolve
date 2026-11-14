"""Opaque diagnostic names survive portable staging without loosening CIF refs."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

from nasolve.cif_review_transport import (
    POLICY_ID, is_safe_review_member, read_staged_review_member,
    review_archive_files, stage_review_members,
)

BACKUP = ('postmr_construction/model/Coot/backups/'
          'Copy_of_4_with_A7_replaced_Thu_Oct_22_15:40:11_2026_modification_0.pdb.gz')
OPAQUE = b'NOT A GZIP STREAM: diagnostic bytes must never be interpreted\x00\xff'


def owned_case(tmp_path):
    session = tmp_path / 'session'
    target = session / 'inputs/review'
    members = {
        'manifest.json': b'{"historical": "manifest bytes stay exact"}\n',
        'probe_receipt.json': b'{"explicit_fake": true}\n',
        'native/input.cif': b'data_EXPLICIT_FAKE\n',
        BACKUP: OPAQUE,
    }
    mapping = stage_review_members(members, target)
    return session, target, members, mapping


@pytest.mark.parametrize('prefix', ['', 'inputs/review/', 'inputs/review/' * 5])
def test_only_historical_logical_backup_grammar_has_colon_exception(prefix):
    assert is_safe_review_member(prefix + BACKUP)
    assert is_safe_review_member('native/inputs/000_dictionary.cif')
    assert not is_safe_review_member('native/inputs/PDU:descriptor.cif')


@pytest.mark.parametrize('bad', [
    '', '/absolute.pdb', '../outside.pdb', 'a/../b', 'a//b', 'a/./b', 'a\\b',
    'C:/drive.pdb', 'a\x00b', 'a\nb', '.review-transport/index.json',
    'a/.review-transport/index.json', '.REVIEW-TRANSPORT/index.json',
    'a/.Review-Transport/index.json',
    BACKUP.replace('postmr_construction/', 'other/'),
    BACKUP.replace('backups/', '../backups/'),
    BACKUP.replace('15:40:11', '25:40:11'),
    BACKUP.replace('15:40:11', '15:60:11'),
    BACKUP.replace('_Thu_Oct_', '_Whatever_Oct_'),
    BACKUP.replace('.pdb.gz', '.py.gz'),
    BACKUP.replace('_modification_0', '_modification_00'),
    'inputs/review/' + BACKUP + '/extra',
])
def test_unsafe_or_unrelated_colon_paths_are_rejected_before_writing(tmp_path, bad):
    assert not is_safe_review_member(bad)
    target = tmp_path / 'staged'
    with pytest.raises(ValueError): stage_review_members({bad: b'data'}, target)
    assert not target.exists()


def test_historical_payloads_and_manifest_restore_exactly_without_colon_disk_names(tmp_path):
    session, target, members, mapping = owned_case(tmp_path)
    assert mapping['native/input.cif'] == 'native/input.cif'
    assert mapping[BACKUP] == '.review-transport/objects/' + sha256(BACKUP.encode()).hexdigest() + '.pdb.gz'
    assert all(':' not in p.relative_to(target).as_posix() for p in target.rglob('*'))
    assert {n: read_staged_review_member(target, n) for n in members} == members
    files = review_archive_files(session, session / 'review.zip')
    assert files == {'inputs/review/' + n: d for n, d in members.items()}
    assert not any('.review-transport' in n for n in files)
    assert files['inputs/review/manifest.json'] == members['manifest.json']


def test_nesting_and_relocation_survive_another_generation(tmp_path):
    session, target, members, _ = owned_case(tmp_path / 'original')
    moved = tmp_path / 'relocated/session'
    shutil.copytree(session, moved)
    shutil.rmtree(session.parent)
    assert read_staged_review_member(moved / 'inputs/review', BACKUP) == OPAQUE
    first = review_archive_files(moved, moved / 'first.zip')
    second = tmp_path / 'second'
    stage_review_members(first, second / 'inputs/review')
    shutil.rmtree(moved.parent)
    assert read_staged_review_member(second / 'inputs/review', 'inputs/review/' + BACKUP) == OPAQUE
    final = review_archive_files(second, second / 'second.zip')
    assert final == {'inputs/review/' + n: d for n, d in first.items()}
    assert final['inputs/review/inputs/review/manifest.json'] == members['manifest.json']


@pytest.mark.parametrize('members', [
    {'a': b'x', 'a/b': b'y'}, {'a/b': b'x', 'a': b'y'},
    {'DG.cif': b'x', 'dg.cif': b'y'},
    {'caf\u00e9.cif': b'x', 'cafe\u0301.cif': b'y'},
    {'FILE': b'x', 'file/nested': b'y'},
])
def test_file_directory_case_and_unicode_alias_collisions_reject(tmp_path, members):
    with pytest.raises(ValueError, match='collision|Colliding'):
        stage_review_members(members, tmp_path / 'staged')
    assert not (tmp_path / 'staged').exists()


def test_staging_never_overwrites_existing_owned_content(tmp_path):
    target = tmp_path / 'staged'; target.mkdir(); (target / 'existing').write_bytes(b'keep')
    with pytest.raises(ValueError, match='fresh empty'):
        stage_review_members({'new': b'x'}, target)
    assert list(target.iterdir()) == [target / 'existing']
    assert (target / 'existing').read_bytes() == b'keep'


def test_nonbytes_mapping_is_not_a_payload(tmp_path):
    with pytest.raises(ValueError): stage_review_members({'payload': 'text'}, tmp_path / 'staged')


@pytest.mark.parametrize('defect', ['hash', 'size', 'logical_name', 'physical_name', 'fields', 'missing_row', 'payload', 'extra_file', 'extra_directory'])
def test_staged_transport_index_and_payload_mutations_cannot_archive(tmp_path, defect):
    session, target, _, mapping = owned_case(tmp_path)
    index_path = target / '.review-transport/index.json'
    index = json.loads(index_path.read_bytes()); row = index['members'][BACKUP]
    if defect == 'hash': row['sha256'] = '0' * 64
    if defect == 'size': row['size'] += 1
    if defect == 'logical_name': index['members'][BACKUP.replace('_0.pdb.gz', '_1.pdb.gz')] = index['members'].pop(BACKUP)
    if defect == 'physical_name': row['physical'] = '.review-transport/objects/elsewhere.pdb.gz'
    if defect == 'fields': row['surprise'] = True
    if defect == 'missing_row': index['members'].clear()
    if defect == 'payload': (target / mapping[BACKUP]).write_bytes(b'changed')
    if defect == 'extra_file': (target / '.review-transport/unexpected').write_bytes(b'changed')
    if defect == 'extra_directory': (target / '.review-transport/unexpected').mkdir()
    index_path.write_text(json.dumps(index))
    with pytest.raises(ValueError): read_staged_review_member(target, BACKUP)
    with pytest.raises(ValueError): review_archive_files(session, session / 'review.zip')


@pytest.mark.parametrize('defect', ['root', 'ordinary', 'ordinary_parent', 'object', 'metadata', 'index'])
def test_staged_files_and_metadata_do_not_follow_symlinks(tmp_path, defect):
    session, target, _, mapping = owned_case(tmp_path)
    outside = tmp_path / 'outside'; outside.mkdir(); (outside / 'payload').write_bytes(b'outside')
    if defect == 'root':
        original = tmp_path / 'original'; target.rename(original); target.symlink_to(original, target_is_directory=True)
    elif defect == 'ordinary':
        p = target / 'native/input.cif'; p.unlink(); p.symlink_to(outside / 'payload')
    elif defect == 'ordinary_parent':
        shutil.rmtree(target / 'native'); (target / 'native').symlink_to(outside, target_is_directory=True)
    elif defect == 'object':
        p = target / mapping[BACKUP]; p.unlink(); p.symlink_to(outside / 'payload')
    elif defect == 'metadata':
        original = tmp_path / 'metadata'; (target / '.review-transport').rename(original); (target / '.review-transport').symlink_to(original, target_is_directory=True)
    elif defect == 'index':
        p = target / '.review-transport/index.json'; original = tmp_path / 'index'; p.rename(original); p.symlink_to(original)
    with pytest.raises(ValueError):
        read_staged_review_member(target, 'native/input.cif' if defect in {'ordinary', 'ordinary_parent'} else BACKUP)
    with pytest.raises(ValueError): review_archive_files(session, session / 'review.zip')


def test_staging_root_cannot_itself_be_a_symlink(tmp_path):
    actual = tmp_path / 'actual'; actual.mkdir(); alias = tmp_path / 'alias'; alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError): stage_review_members({'file': b'payload'}, alias)
    assert not list(actual.iterdir())


def test_new_owned_backups_normalize_and_archive_explicit_provenance(tmp_path):
    session, _, original, _ = owned_case(tmp_path)
    backup = session / BACKUP; backup.parent.mkdir(parents=True); backup.write_bytes(b'new opaque diagnostic')
    files = review_archive_files(session, session / 'review.zip')
    safe = BACKUP.replace(':', '_')
    assert not backup.exists() and (session / safe).read_bytes() == b'new opaque diagnostic'
    assert BACKUP not in files and files[safe] == b'new opaque diagnostic'
    assert files['inputs/review/' + BACKUP] == original[BACKUP]
    assert json.loads(files['postmr_construction/diagnostic_transport.json']) == {
        'policy_id': POLICY_ID, 'normalized_owned_backups': [{
            'original_name': BACKUP, 'path': safe,
            'sha256': sha256(b'new opaque diagnostic').hexdigest(), 'size': 21,
        }],
    }
    assert review_archive_files(session, session / 'review.zip') == files


@pytest.mark.parametrize('defect', ['payload', 'original_name', 'path', 'sha256', 'size', 'extra_field'])
def test_owned_normalization_provenance_is_bound_to_names_and_bytes(tmp_path, defect):
    session = tmp_path / 'session'; p = session / BACKUP; p.parent.mkdir(parents=True); p.write_bytes(OPAQUE)
    review_archive_files(session, session / 'review.zip')
    provenance = session / 'postmr_construction/diagnostic_transport.json'; value = json.loads(provenance.read_bytes()); row = value['normalized_owned_backups'][0]
    if defect == 'payload': (session / row['path']).write_bytes(b'changed')
    if defect == 'original_name': row['original_name'] = 'arbitrary:backup.gz'
    if defect == 'path': row['path'] = 'outside.gz'
    if defect == 'sha256': row['sha256'] = '0' * 64
    if defect == 'size': row['size'] += 1
    if defect == 'extra_field': row['unexpected'] = True
    provenance.write_text(json.dumps(value))
    with pytest.raises(ValueError): review_archive_files(session, session / 'review.zip')


def test_owned_normalization_collision_fails_before_moving_any_backup(tmp_path):
    session = tmp_path / 'session'; backup = session / BACKUP; backup.parent.mkdir(parents=True); backup.write_bytes(OPAQUE)
    safe = session / BACKUP.replace(':', '_'); safe.write_bytes(b'keep')
    with pytest.raises(ValueError, match='collision'):
        review_archive_files(session, session / 'review.zip')
    assert backup.read_bytes() == OPAQUE and safe.read_bytes() == b'keep'
    assert not (session / 'postmr_construction/diagnostic_transport.json').exists()


def test_unindexed_nested_legacy_backups_are_not_reinterpreted_as_new_owned_files(tmp_path):
    session = tmp_path / 'session'; backup = session / 'inputs/review' / BACKUP; backup.parent.mkdir(parents=True); backup.write_bytes(OPAQUE)
    with pytest.raises(ValueError, match='unindexed'):
        review_archive_files(session, session / 'review.zip')
    assert backup.read_bytes() == OPAQUE


def test_archive_collection_keeps_existing_exclusions_and_rejects_new_unsafe_names(tmp_path):
    session = tmp_path / 'session'; session.mkdir()
    for name in ['keep.txt', 'ignore.pyc', 'ignore.pkl', 'ignore.pickle', 'review.zip']:
        (session / name).write_bytes(name.encode())
    (session / 'runtime').mkdir(); (session / 'runtime/skip.py').write_bytes(b'never archive runtime')
    assert review_archive_files(session, session / 'review.zip') == {'keep.txt': b'keep.txt'}
    (session / 'arbitrary:bad').write_bytes(b'unsafe')
    with pytest.raises(ValueError): review_archive_files(session, session / 'review.zip')


def test_archive_destination_and_reserved_namespace_are_owned(tmp_path):
    session = tmp_path / 'session'; session.mkdir()
    with pytest.raises(ValueError): review_archive_files(session, tmp_path / 'elsewhere.zip')
    (session / '.review-transport').mkdir()
    with pytest.raises(ValueError): review_archive_files(session, session / 'review.zip')


def test_session_parent_alias_keeps_destination_identity_without_hiding_owned_symlinks(tmp_path):
    real = tmp_path / 'real'; real.mkdir()
    alias = tmp_path / 'alias'; alias.symlink_to(real, target_is_directory=True)
    session = alias / 'session'; session.mkdir(); (session / 'keep').write_bytes(b'keep')
    assert review_archive_files(session, session / 'out.zip') == {'keep': b'keep'}
    destination = real / 'session/out.zip'; destination.symlink_to(tmp_path / 'elsewhere')
    with pytest.raises(ValueError, match='symlink'):
        review_archive_files(session, session / 'out.zip')
    destination.unlink()
    (session / 'internal').mkdir(); (session / 'owned_alias').symlink_to(session / 'internal', target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        review_archive_files(session, session / 'owned_alias/out.zip')


def test_empty_reserved_case_alias_directory_is_rejected_during_collection(tmp_path):
    session = tmp_path / 'session'; session.mkdir(); (session / '.REVIEW-TRANSPORT').mkdir()
    with pytest.raises(ValueError, match='namespace'):
        review_archive_files(session, session / 'review.zip')


def test_duplicate_local_index_keys_are_not_ambiguous_transport_bindings(tmp_path):
    session, target, _, _ = owned_case(tmp_path)
    index = target / '.review-transport/index.json'; text = index.read_text()
    text = text.replace('"policy_id":', '"policy_id": "ignored duplicate", "policy_id":')
    index.write_text(text)
    with pytest.raises(ValueError, match='Duplicate'):
        review_archive_files(session, session / 'review.zip')
