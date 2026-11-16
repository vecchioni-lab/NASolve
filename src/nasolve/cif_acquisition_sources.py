"""Freeze ordinary component source selection before numerical acquisition.

This stage uses the existing curated/local/configured-CCD precedence. It starts
no native job and supplies neither scientific qualification nor retry authority.
Partial output is preserved; every call needs a fresh destination.
"""
from collections.abc import Mapping
from hashlib import sha256
import os
from pathlib import Path
import re

from .campaign_records import _sync_directory, read_record, write_record
from .cif_dictionary_sites import _read
from .cif_dictionary_store import _bytes
from .cif_repair_attempt import _root, _members
from .curated_ligands import (
    CURATED_LIGANDS, LigandDictionarySource, ligand_source, validate_ligand_dictionary,
)

POLICY_ID = 'cif-acquisition-source-selection-v1'
EXPLICIT_POLICY_ID = 'cif-acquisition-explicit-sources-v1'
ANCHOR = 'source_selection_directory'


def _need(value, message):
    if not value:
        raise ValueError(message)


def _codes(codes):
    _need(isinstance(codes, (list, tuple)) and 1 <= len(codes) <= 16
        and all(isinstance(code, str) and re.fullmatch(r'[A-Z0-9]{1,3}', code) for code in codes),
        'Require one to sixteen explicit PDB component codes')
    _need(len(set(codes)) == len(codes), 'Duplicate source component')
    return sorted(codes)


def _explicit_codes(codes, explicit):
    selected = _codes(explicit)
    _need(set(selected) <= set(codes), 'Explicit source is outside the requested component set')
    _need(not set(selected).intersection(CURATED_LIGANDS), 'Explicit sources cannot override curated components')
    return selected


def _authority(code, authority, kind, *, explicit=False):
    if explicit:
        _need(code not in CURATED_LIGANDS and (authority, kind) == ('EXPLICIT', 'explicit-file'),
            'Source authority/kind differs from explicit file selection')
        return
    allowed = {('CURATED', 'curated')} if code in CURATED_LIGANDS else {
        ('EXPLICIT', 'local-verified'), ('NATIVE', 'installed-phenix-ccd')}
    _need((authority, kind) in allowed, 'Source authority/kind differs from ordinary selection')


def _reference(root, code):
    relative = f'sources/{code}.cif'
    data = _read(root/relative)
    return dict(anchor=ANCHOR, path=relative, sha256=sha256(data).hexdigest(), size=len(data))


def _report(codes, sources, explicit=()):
    result = dict(schema_version=1, policy_id=EXPLICIT_POLICY_ID if explicit else POLICY_ID, status='SOURCES_FROZEN',
        components=codes, sources=sources, native_validation='NOT_RUN',
        scientific_qualification='NOT_ASSESSED', automatic_adoption=False,
        retry_authorized=False, dictionary_generation='NOT_RUN')
    if explicit:
        result['explicit_components'] = list(explicit)
    return result


def read_acquisition_sources(directory):
    """Read exact frozen sources without rediscovery, SDK access or any writes.

    Historical paths explain where selection occurred; only anchored frozen
    references are operational. Current source validators still apply, but no
    live registry lookup or assertion of native usability is made.
    """
    root = _root(directory)
    _members(root, {'source_selection.json'}, {'sources'})
    original = _read(root/'source_selection.json')
    record = read_record(root/'source_selection.json')
    codes = _codes(record.get('components'))
    explicit = (_explicit_codes(codes, record.get('explicit_components'))
        if record.get('policy_id') == EXPLICIT_POLICY_ID else [])
    _members(root/'sources', {f'{code}.cif' for code in codes}, set())
    rows = record.get('sources')
    _need(isinstance(rows, dict) and set(rows) == set(codes), 'Source component inventory differs')
    result = {}
    for code in codes:
        row = rows[code]
        _need(isinstance(row, dict) and set(row) == {
            'source_authority', 'source_kind', 'artifact', 'historical_path', 'historical_path_role'},
            'Unexpected source selection fields')
        _authority(code, row['source_authority'], row['source_kind'], explicit=code in explicit)
        _need(isinstance(row['historical_path'], str) and Path(row['historical_path']).is_absolute()
            and row['historical_path_role'] == 'PROVENANCE_ONLY', 'Invalid historical source provenance')
        _need(row['artifact'] == _reference(root, code), 'Frozen source reference or bytes differ')
        source = root/'sources'/f'{code}.cif'
        validate_ligand_dictionary(code, source)
        result[code] = dict(source=source, source_authority=row['source_authority'], source_kind=row['source_kind'])
    _need({p.name for p in root.iterdir()} == {'source_selection.json', 'sources'}
        and {p.name for p in (root/'sources').iterdir()} == {f'{code}.cif' for code in codes},
        'Unbound source selection artifact')
    _need(_read(root/'source_selection.json') == original
        and all(rows[code]['artifact'] == _reference(root, code) for code in codes),
        'Frozen evidence changed during readback')
    expected = _report(codes, rows, explicit)
    _need(_bytes({k:v for k,v in record.items() if k != 'record_sha256'}) == _bytes(expected),
        'Source selection claims differ from frozen evidence')
    return dict(report=record, sources=result)


def freeze_acquisition_sources(codes, output, *, data_root=None, ready_set_executable=None,
                               explicit_sources=None):
    """Select and freeze a complete declared source set, retaining all partial work.

    Missing/ambiguous/invalid sources fail before publication. Every selected
    path, authority and byte string is rechecked across the whole batch before
    completion; a change requires a fresh call and fresh destination. A later
    numerical acquisition consumes the returned reader's exact source/authority,
    rather than rediscovering that code. This is not a full acquisition request.

    Optional ``explicit_sources`` maps a nonempty subset of non-curated codes to
    exact source files. These choices bypass registry/discovery, not identity or
    downstream chemistry validation. The mapping is captured at entry; original
    files are rechecked throughout freezing. Other codes keep ordinary precedence.
    Explicit files get a distinct policy/kind, never numerical qualification or
    implicit registration. Composition evidence, if any, is separate authority.
    """
    root = _root(output)
    if root.exists():
        raise FileExistsError(root)
    codes = _codes(codes)
    explicit = []; paths = {}
    if explicit_sources is not None:
        _need(isinstance(explicit_sources, Mapping), 'Explicit sources must map codes to file paths')
        choices = dict(explicit_sources)
        explicit = _explicit_codes(codes, list(choices))
        for code in explicit:
            _need(isinstance(choices[code], (str, os.PathLike)), 'Explicit source requires a file path')
            paths[code] = Path(choices[code]).absolute()
    selected = {}; originals = {}
    def select(code):
        choice = (LigandDictionarySource(code, paths[code], 'EXPLICIT', 'explicit-file')
            if code in paths else ligand_source(code, data_root, ready_set_executable=ready_set_executable))
        _need(choice.code == code, 'Selected source component differs')
        _authority(code, choice.authority, choice.kind, explicit=code in paths)
        return choice
    for code in codes:
        choice = select(code)
        data = _read(choice.path)
        validate_ligand_dictionary(code, choice.path)
        _need(_read(choice.path) == data, 'Source changed during validation')
        selected[code] = choice; originals[code] = data
    def unchanged():
        for code, choice in selected.items():
            _need(select(code) == choice and _read(choice.path) == originals[code],
                'Source selection changed during freezing')
    unchanged()
    root.mkdir(parents=True, exist_ok=False)
    _sync_directory(root.parent)
    (root/'sources').mkdir()
    _sync_directory(root)
    rows = {}
    for code, choice in selected.items():
        target = root/'sources'/f'{code}.cif'
        with target.open('xb') as handle:
            handle.write(originals[code]); handle.flush(); os.fsync(handle.fileno())
        rows[code] = dict(source_authority=choice.authority, source_kind=choice.kind,
            artifact=_reference(root, code), historical_path=str(Path(choice.path).absolute()),
            historical_path_role='PROVENANCE_ONLY')
    _sync_directory(root/'sources')
    unchanged()
    _need(all(_read(root/'sources'/f'{code}.cif') == data for code,data in originals.items()),
        'Frozen source changed before completion')
    write_record(root/'source_selection.json', _report(codes, rows, explicit))
    return read_acquisition_sources(root)['report']
