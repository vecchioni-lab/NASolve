"""Resolve caller-declared logical end roles through existing Pine registration.

Registration identifies sites; it does not prove pairing, chemical continuity,
strand direction, terminal status or equivalent periodic representations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from .construct_registration import validate_construct_registration
from .topostitch import DuplexEnd
from .topostitch_coordinates import EndAssignment, ResidueSite, _CANONICAL, _read_atoms


@dataclass(frozen=True)
class LogicalEndAssignment:
    end_id: str
    copy_id: str
    overhang_sites: tuple[str, ...]
    terminal_pair: tuple[str, str]
    inner_pair: tuple[str, str]
    polarity: str
    state: str = 'available'

    def __post_init__(self):
        DuplexEnd(self.end_id, None, self.polarity, (0, 0, 0), self.state)
        if not isinstance(self.copy_id, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', self.copy_id) is None:
            raise ValueError('Invalid logical assignment copy_id')
        for name in ('overhang_sites', 'terminal_pair', 'inner_pair'):
            sites = getattr(self, name)
            if (not isinstance(sites, (tuple, list)) or not sites
                    or any(not isinstance(s, str) or re.fullmatch(r'[^:\s]+:[^:\s]+', s) is None for s in sites)
                    or (name != 'overhang_sites' and len(sites) != 2)):
                raise ValueError(f'{name} requires explicit logical site identifiers')
            object.__setattr__(self, name, tuple(sites))
        sites = self.overhang_sites+self.terminal_pair+self.inner_pair
        if len(set(sites)) != len(sites):
            raise ValueError('Logical assignment contains overlapping or duplicate sites')


def _fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _coordinate_site(text):
    chain, resid = text.split(':')
    match = re.fullmatch(r'(-?(?:0|[1-9][0-9]*))([A-Za-z]?)', resid)
    if match is None:
        raise ValueError('Unsupported registered PDB residue identifier')
    return ResidueSite(chain, int(match[1]), match[2])


def resolve_registered_ends(model_path: Path, assignments, registration: dict, *,
                            expected_sha256: str) -> tuple[tuple[EndAssignment, ...], dict]:
    """Return resolved coordinate assignments and a complete mapping assessment.

    Missing mappings or identity conflicts leave an explicit unresolved end;
    unknown logical/copy identifiers and malformed source records are errors.
    A partially mapped copy stays incomplete even if selected end sites exist.
    The verified PDB bytes, not registration identity labels, supply actual codes.
    """
    if not isinstance(expected_sha256, str) or re.fullmatch(r'[0-9a-f]{64}', expected_sha256) is None:
        raise ValueError('Expected lowercase model SHA-256 checksum')
    registration = validate_construct_registration(registration)
    if registration['model']['sha256'] != expected_sha256:
        raise ValueError('Registration/model checksum mismatch')
    data = Path(model_path).read_bytes()
    if sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Source model checksum mismatch')
    atoms = _read_atoms(data)
    rows = list(assignments)
    if any(not isinstance(a, LogicalEndAssignment) for a in rows):
        raise ValueError('Expected LogicalEndAssignment records')
    if len({a.end_id for a in rows}) != len(rows):
        raise ValueError('Duplicate logical end identifier')
    overhangs = [(a.copy_id, s) for a in rows for s in a.overhang_sites]
    if len(set(overhangs)) != len(overhangs):
        raise ValueError('A logical overhang site cannot belong to multiple ends')
    rows.sort(key=lambda a: a.end_id)
    copies = {c['copy_id']: c for c in registration['copies']}
    known = set(registration['target']['sites'])
    resolved, evidence = [], []
    complete = True
    for row in rows:
        if row.copy_id not in copies:
            raise ValueError(f'Unknown registered copy: {row.copy_id}')
        requested = row.overhang_sites+row.terminal_pair+row.inner_pair
        if not set(requested) <= known:
            raise ValueError('Unknown logical site in end assignment')
        copy = copies[row.copy_id]
        if copy['status'] != 'COMPLETE':
            complete = False
        mapping = {r['logical_site']: r for r in copy['mappings']}
        sites, issues = {}, []
        for logical in requested:
            item = mapping.get(logical)
            reason = None
            if item is None:
                reason = 'MISSING_LOGICAL_MAPPING'
            else:
                try:
                    site = _coordinate_site(item['coordinate_site'])
                except ValueError:
                    reason = 'UNSUPPORTED_COORDINATE_IDENTIFIER'
                else:
                    groups = atoms.get(site)
                    if groups is None:
                        reason = 'MISSING_COORDINATE_SITE'
                    elif len(groups) != 1:
                        reason = 'AMBIGUOUS_COORDINATE_SITE'
                    else:
                        observed = {r[1] for r in next(iter(groups.values()))}
                        if observed != {item['coordinate_residue_code']}:
                            reason = 'COORDINATE_IDENTITY_MISMATCH'
                        elif item['identity_relation'] != 'SAME':
                            reason = 'TARGET_IDENTITY_MISMATCH'
                        elif item['target_residue_code'] not in _CANONICAL:
                            reason = 'UNSUPPORTED_CHEMISTRY'
                        else:
                            sites[logical] = site
            if reason:
                issues.append({'code': reason, 'logical_site': logical,
                               'coordinate_site': None if item is None else item['coordinate_site']})
        entry = {'end_id': row.end_id, 'copy_id': row.copy_id, 'copy_status': copy['status'],
                 'assessment': 'UNRESOLVED' if issues else 'RESOLVED', 'issues': issues,
                 'site_mapping': [{'logical_site': s, 'coordinate_site': asdict(sites[s])}
                                  for s in requested if s in sites]}
        if issues:
            complete = False
        else:
            resolved.append(EndAssignment(row.end_id,
                tuple(sites[s] for s in row.overhang_sites),
                tuple(sites[s] for s in row.terminal_pair),
                tuple(sites[s] for s in row.inner_pair), row.polarity, row.state))
        evidence.append(entry)
    logical_manifest = json.loads(json.dumps([asdict(a) for a in rows]))
    report = {'schema_version': 1, 'kind': 'topostitch-registration-end-map',
              'source_model_sha256': expected_sha256, 'source_bytes_verified': True,
              'registration_sha256': _fingerprint(registration),
              'logical_assignments': logical_manifest,
              'logical_assignments_sha256': _fingerprint(logical_manifest),
              'ends': evidence, 'coverage_complete': complete,
              'topology_inferred': False, 'periodic_site_images_resolved': False,
              'runtime_authority': False, 'changes': [],
              'limitations': ['Explicit logical topology; registration alone does not prove end geometry',
                              'Identity-image coordinate sites only; periodic cuts need a later realization adapter',
                              'No coordinate, target chemistry, registration or checkpoint edits']}
    return tuple(resolved), report
