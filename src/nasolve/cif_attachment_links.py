"""Read-only reciprocal source-port contracts for an explicitly closed site set."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import json
import re

from .cif_attachment_sites import inspect_attachment_site, STATE_POLICY_ID, _model, _object, _pairs
from .cif_catalogue import _digest

POLICY_ID = 'cif-reciprocal-source-links-v1'
MAX_SITES = 256
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_TOTAL_INPUT_BYTES = 128 * 1024 * 1024
_COMPLEMENT = {'alcohol': 'phosphate', 'phosphate': 'alcohol',
               'carboxyl': 'amine', 'amine': 'carboxyl'}


def _input(root, record, snapshots):
    _object(record, ('anchor', 'path', 'sha256', 'size'))
    name = record['path']
    if (record['anchor'] != 'manifest_directory' or not isinstance(name, str)
            or name.startswith('/') or '\\' in name or ':' in name
            or any(part in {'', '.', '..'} for part in name.split('/'))):
        raise ValueError('Require an explicit safe manifest-directory input reference')
    if (not isinstance(record['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', record['sha256'])
            or type(record['size']) is not int or record['size'] < 0):
        raise ValueError('Require explicit input SHA-256 and integer size')
    path = root
    for part in PurePosixPath(name).parts:
        path /= part
        if path.is_symlink():
            raise ValueError('Symlink in attachment-link input reference')
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError('Attachment-link input missing or outside its explicit anchor')
    if path not in snapshots:
        if sum(len(data) for data in snapshots.values()) + path.stat().st_size > MAX_TOTAL_INPUT_BYTES:
            raise ValueError('Attachment-link total input size limit exceeded')
        snapshots[path] = path.read_bytes()
    if _digest(snapshots[path]) != {'sha256': record['sha256'], 'size': record['size']}:
        raise ValueError('Attachment-link input hash/size differs from manifest')
    return path


def _reciprocal_links(sites):
    links, seen = [], set()
    for site, report in sorted(sites.items()):
        for name, port in report['source_profile']['ports'].items():
            intent = report['context']['ports'][name]
            if intent['state'] != 'linked':
                continue
            partner = intent['partner']
            if partner['site'] not in sites:
                raise ValueError('Declared partner lies outside the explicit site scope')
            other = sites[partner['site']]
            matches = [p for p, evidence in other['source_profile']['ports'].items()
                       if evidence['atom_id'] == partner['atom_id']]
            if len(matches) != 1 or matches[0] != _COMPLEMENT[name]:
                raise ValueError('Partner atom is not the complementary source-bound attachment port')
            other_port = matches[0]
            reverse = other['context']['ports'][other_port]
            expected = {'site': site, 'component': report['component'], 'atom_id': port['atom_id']}
            if reverse['state'] != 'linked' or reverse['partner'] != expected:
                raise ValueError('Attachment declarations are not reciprocal at both source ports')
            endpoints = [
                {'site': site, 'component': report['component'], 'port': name, 'atom_id': port['atom_id']},
                {'site': partner['site'], 'component': other['component'], 'port': other_port,
                 'atom_id': partner['atom_id']},
            ]
            # Order by chemical port role, never by residue numbering or distance.
            kind, first = ('alcohol_phosphate', 'alcohol') if name in {'alcohol', 'phosphate'} else ('carboxyl_amine', 'carboxyl')
            endpoints.sort(key=lambda endpoint: endpoint['port'] != first)
            key = tuple((endpoint['site'], endpoint['port']) for endpoint in endpoints)
            if key not in seen:
                seen.add(key)
                links.append({'kind': kind, 'endpoints': endpoints, 'bond_order': 'SINGLE',
                              'symmetry_operation': 'x,y,z', 'native_qualification': 'NOT_ASSESSED'})
    if not links:
        raise ValueError('Require at least one explicitly declared reciprocal link')
    return sorted(links, key=lambda link: tuple((e['site'], e['port']) for e in link['endpoints']))


def inspect_attachment_links(manifest):
    """Compose fresh C107 inspections, requiring both ends of every declared link.

    The manifest owns exact relative inputs and one source authority per code.
    A bound source network never grants native typing, linkage or adoption.
    """
    manifest = Path(manifest).expanduser().resolve(strict=True)
    if manifest.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError('Attachment-link manifest size limit exceeded')
    original = manifest.read_bytes()
    declaration = json.loads(original, object_pairs_hook=_pairs)
    _object(declaration, ('schema_version', 'model', 'workbook', 'sites'))
    if type(declaration['schema_version']) is not int or declaration['schema_version'] != 1:
        raise ValueError('Unsupported attachment-link manifest schema')
    entries = declaration['sites']
    if not isinstance(entries, list) or not 2 <= len(entries) <= MAX_SITES:
        raise ValueError('Require 2 to 256 explicitly selected attachment sites')
    root, snapshots = manifest.parent, {manifest: original}
    model = _input(root, declaration['model'], snapshots)
    workbook = _input(root, declaration['workbook'], snapshots)
    bound, authorities = [], {}
    for entry in entries:
        _object(entry, ('component', 'source', 'context'), ('candidate',))
        code = entry['component']
        if not isinstance(code, str) or not re.fullmatch('[A-Za-z0-9]{1,3}', code):
            raise ValueError('Require an exact supported PDB component code')
        paths = {role: _input(root, entry[role], snapshots) for role in ('source', 'context', 'candidate') if role in entry}
        identity = _digest(snapshots[paths['source']])
        if code in authorities and authorities[code] != identity:
            raise ValueError('Require one exact source authority per component code')
        authorities[code] = identity
        bound.append((code, paths))
    sites = {}
    for code, paths in bound:
        report = inspect_attachment_site(paths['source'], code, workbook=workbook, model=model,
                                         context=paths['context'], candidate=paths.get('candidate'))
        expected_context = json.loads(snapshots[paths['context']], object_pairs_hook=_pairs)
        if (report['component'] != code or report['context'] != expected_context
                or report['site'] != expected_context['site']):
            raise ValueError('Fresh site identity/context differs from manifest evidence')
        for role, path in {'model': model, 'workbook': workbook, **paths}.items():
            digest = _digest(snapshots[path])
            if any(report['inputs'][role][key] != value for key, value in digest.items()):
                raise ValueError('Fresh site input differs from manifest evidence')
        site = report['site']
        if site in sites:
            raise ValueError('Duplicate selected model site')
        sites[site] = report
    reasons = []
    source_bound = all(report['source_profile']['topology_status'] == 'MATCH'
                       and not report['source_profile']['review_reasons'] for report in sites.values())
    links = _reciprocal_links(sites) if source_bound else []
    if not source_bound:
        reasons.append('SOURCE_PORT_BINDING_UNRESOLVED')
    for site, report in sorted(sites.items()):
        if report['plan_status'] != 'PROPOSED':
            reasons.append('SITE_OPERATION_UNRESOLVED:' + site)
        if report['projection_check']['status'] == 'MISMATCH':
            reasons.append('CANDIDATE_PROJECTION_MISMATCH:' + site)
    candidate_states = [report['projection_check']['status'] for report in sites.values()]
    if 'MISMATCH' in candidate_states:
        projection_status = 'MISMATCH'
    elif 'NOT_ASSESSED' in candidate_states:
        projection_status = 'NOT_ASSESSED'
    elif all(state == 'NOT_REQUESTED' for state in candidate_states):
        projection_status = 'NOT_REQUESTED'
    else:
        projection_status = 'PARTIAL_MATCH' if 'NOT_REQUESTED' in candidate_states else 'MATCH'
    report = {
        'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW',
        'manifest': {'anchor': 'manifest_directory', 'path': manifest.name, **_digest(original)},
        'input_manifest': declaration, 'source_authorities': dict(sorted(authorities.items())),
        'scope': 'CLOSED_DECLARED_SITE_SET', 'covered_sites': sorted(sites),
        'unselected_model_sites': sorted(_model(snapshots[model]).keys() - sites.keys()),
        'site_reports': dict(sorted(sites.items())), 'links': links,
        'binding_status': 'BOUND' if source_bound else 'UNRESOLVED',
        'plan_status': 'UNRESOLVED' if reasons else 'PROPOSED', 'review_reasons': reasons,
        'projection_status': projection_status,
        'permitted_source_projections': None if reasons else {
            site: entry['permitted_source_projection'] for site, entry in sorted(sites.items())},
        'native_qualification': 'NOT_ASSESSED', 'native_execution': 'NOT_RUN',
        'transformations': [], 'automatic_adoption': False,
        'limits': {'sites': MAX_SITES, 'manifest_bytes': MAX_MANIFEST_BYTES, 'total_input_bytes': MAX_TOTAL_INPUT_BYTES},
        'limitations': [
            'Closed declared links only; unselected model sites and actual experimental connectivity are not qualified.',
            'Reciprocal graph-bound ports do not establish native atom types, distances, linkage targets or final stereochemistry.',
            'C107 source/protonation/selector limits apply; PNA operations and free-OH reconstruction remain unresolved.',
            'Candidate coverage is explicit; even complete source-table matches are not native numerical dictionaries.',
            'Source formula/descriptors remain parent provenance; no final linked chemical identity is generated.',
        ],
    }
    if any(site['policy_id'] == STATE_POLICY_ID for site in sites.values()):
        report['policy_id'] = 'cif-reciprocal-source-links-v2'
        report['limitations'][2] = ('Explicit neutral PNA amide operations require both source states; '
                                    'charged reaction sites and free-OH reconstruction remain unresolved.')
    if any(path.read_bytes() != data for path, data in snapshots.items()):
        raise ValueError('Attachment-link input changed during inspection')
    report['input_integrity'] = 'UNCHANGED'
    return report
