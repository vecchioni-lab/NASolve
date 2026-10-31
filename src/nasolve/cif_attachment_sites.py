"""Read-only single-site source projections, never native linkage authorization."""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import re

from .cif_attachment_profiles import inspect_attachment_profile
from .cif_catalogue import MAX_SOURCE_BYTES, _digest
from .cif_linked_preparation import component_values, _prune
from .cif_stereochemistry_audit import _graph, _stereo
from .ligand_profiles import _blocks

POLICY_ID = 'cif-explicit-attachment-site-v1'
STATE_POLICY_ID = 'cif-explicit-attachment-site-v2'


def _neutral_hydroxyl_hydrogens(atom, elements, bonds, charges, neighbors):
    """Existing neutral source-port state, shared with explicit native preparation."""
    hydrogens = {a for a in neighbors[atom] if elements[a] in {'H', 'D'}}
    if (charges[atom] != 0 or len(hydrogens) != 1
            or any(charges[h] != 0 or neighbors[h] != {atom}
                   or bonds[tuple(sorted((h, atom)))] != 'SINGLE' for h in hydrogens)):
        return None
    return hydrogens


def _site(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_]:-?(0|[1-9][0-9]*)', value):
        raise ValueError('Require an exact supported PDB chain:residue selector')
    if value.endswith(':-0'):
        raise ValueError('Noncanonical PDB residue selector')
    return value


def _object(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError('Missing or unsupported attachment-context fields')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate attachment-context field: ' + key)
        result[key] = value
    return result


def _model(payload):
    """Strict initial PDB subset: no lossy collapse of model/conformer identity."""
    sites, closed = {}, set()
    current, ended = None, False
    for line in payload.decode('utf-8').splitlines():
        if line[:6].strip() in {'MODEL', 'ENDMDL'}:
            raise ValueError('Explicit MODEL records need a model-aware attachment selector')
        if line[:6].strip() == 'END':
            ended = True
        if line[:6].strip() == 'TER' and current is not None:
            closed.add(current)
            current = None
        if line[:6] not in {'ATOM  ', 'HETATM'}:
            continue
        if ended:
            raise ValueError('Coordinate record after PDB END')
        if len(line) < 78 or line[16:17].strip() or line[26:27].strip() or line[21:22] == '_':
            raise ValueError('Truncated PDB, alternate conformer, insertion code or literal underscore chain needs a reviewed selector')
        try:
            resid = str(int(line[22:26]))
            xyz = [float(line[i:i+8]) for i in (30, 38, 46)]
        except ValueError as exc:
            raise ValueError('Invalid PDB residue or coordinates') from exc
        if not all(math.isfinite(x) for x in xyz):
            raise ValueError('Nonfinite PDB coordinates')
        site = _site((line[21:22].strip() or '_') + ':' + resid)
        if site != current:
            if site in closed:
                raise ValueError('Noncontiguous or TER-separated repeated PDB site')
            if current is not None:
                closed.add(current)
            current = site
        atom, code, element = line[12:16].strip(), line[17:20].strip(), line[76:78].strip().upper()
        if not atom or not re.fullmatch('[A-Za-z0-9]{1,3}', code) or not re.fullmatch('[A-Z]{1,2}', element):
            raise ValueError('Require explicit PDB atom, component and element identity')
        row = sites.setdefault(site, {'component': code, 'atoms': {}})
        if row['component'] != code or atom in row['atoms']:
            raise ValueError('Ambiguous PDB site or duplicate atom: ' + site)
        row['atoms'][atom] = element
    if not sites:
        raise ValueError('Require a nonempty supported PDB model')
    return sites


def _tables(values):
    """Compare complete retained declarations, allowing only table row ordering."""
    result = {}
    for category in sorted({k.split('.')[0] for k in values if '.' in k}):
        fields = sorted(k for k in values if k.startswith(category + '.'))
        if len({len(values[k]) for k in fields}) != 1:
            raise ValueError('Ragged source-projection category: ' + category)
        result[category] = (tuple(fields), Counter(zip(*(values[k] for k in fields))))
    return result


def _projection_values(path, code):
    # component_values selects one component. Reject other blocks explicitly so
    # a second definition/modification cannot disappear from this exact check.
    for block in _blocks(path):
        values = block.values
        fields = {key for key in values if key != 'data_'}
        if not fields:
            continue
        if '_chem_comp_atom.comp_id' in values:
            if set(values['_chem_comp_atom.comp_id']) != {code}:
                raise ValueError('Unselected component in source projection')
        elif (values.get('_chem_comp.id') != [code]
              or any(not key.startswith('_chem_comp.') for key in fields)):
            raise ValueError('Unbound block/fields in source projection')
    return component_values(path, code)


def inspect_attachment_site(source, code, *, workbook, model, context, candidate=None):
    """Explain one explicitly selected site and optionally compare its projection.

    Neutral furanose ports and explicitly opted-in neutral PNA amide ports
    support bounded deletion planning. Other chemical states remain unresolved.
    A projection match is not native typing, partner chemistry or bond validation.
    The caller declares intended links; coordinates and residue adjacency do not.
    """
    paths = {key: Path(value).expanduser().resolve(strict=True) for key, value in
             {'source': source, 'workbook': workbook, 'model': model, 'context': context,
              **({'candidate': candidate} if candidate is not None else {})}.items()}
    for key in ('source', 'context', 'candidate'):
        if key in paths and paths[key].stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError('Oversized attachment-site ' + key)
    payloads = {key: path.read_bytes() for key, path in paths.items()}
    declaration = json.loads(payloads['context'], object_pairs_hook=_pairs)
    _object(declaration, ('schema_version', 'site', 'ports'))
    if type(declaration['schema_version']) is not int or declaration['schema_version'] != 1:
        raise ValueError('Unsupported attachment-context schema')
    selected = _site(declaration['site'])
    sites = _model(payloads['model'])
    if selected not in sites or sites[selected]['component'] != code:
        raise ValueError('Declared site does not match model component identity')
    profile = inspect_attachment_profile(paths['source'], code, workbook=paths['workbook'])
    report = {
        'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW', 'component': code,
        'inputs': {key: {'anchor': key + '_directory', 'path': path.name, **_digest(payloads[key])}
                   for key, path in paths.items()},
        'source_profile': profile, 'context': declaration, 'site': selected,
        'scope': 'ONE_EXPLICIT_PDB_SITE',
        'other_component_sites': sorted(s for s, row in sites.items() if row['component'] == code and s != selected),
        'model_atoms': dict(sorted(sites[selected]['atoms'].items())),
        'plan_status': 'UNRESOLVED', 'permitted_source_projection': None,
        'projection_check': {'status': 'NOT_ASSESSED' if candidate is not None else 'NOT_REQUESTED'},
        'review_reasons': [], 'partner_chemistry': 'NOT_ASSESSED',
        'native_qualification': 'NOT_ASSESSED', 'native_execution': 'NOT_RUN',
        'transformations': [], 'automatic_adoption': False,
        'limitations': [
            'One site only; partner identity/element checks do not qualify partner chemistry or a complete linkage.',
            'PDB without MODEL records, alternate conformers or insertion codes only; no symmetry links.',
            'Source-state retention and explicit neutral protonated furanose deletions only.',
            'PNA link states and free-5prime-OH reconstruction require separate chemical-state authority.',
            'Exact source-table projection is not a numerical dictionary, native type assignment or final stereochemical qualification.',
            'No distance, sequence, LINK/CONECT record or missing-atom heuristic selects a bond or leaving oxygen.',
        ],
    }
    if profile['topology_status'] != 'MATCH' or profile['review_reasons']:
        report['review_reasons'].append('SOURCE_PROFILE_UNRESOLVED')
    else:
        values = component_values(paths['source'], code)
        elements, bonds, charges, neighbors = _graph(values)
        stereo = _stereo(values)
        ports = declaration['ports']
        _object(ports, tuple(profile['ports']))
        removed, external, operations = set(), [], []
        expected_partner = {'phosphate': 'O', 'alcohol': 'P', 'amine': 'C', 'carboxyl': 'N'}
        for name, source_port in profile['ports'].items():
            intent = ports[name]
            if not isinstance(intent, dict):
                raise ValueError('Require an explicit port state')
            state = intent.get('state')
            if state == 'source':
                _object(intent, ('state',))
                continue
            if state == 'free_OH' and name == 'phosphate':
                _object(intent, ('state',))
                report['review_reasons'].append('FREE_OH_RECONSTRUCTION_NEEDS_HYDROGEN_AUTHORITY')
                continue
            if state != 'linked':
                raise ValueError('Unsupported attachment port state: ' + name)
            pna_operation = name in {'amine', 'carboxyl'} and 'operation' in intent
            extra = ('operation', 'leaving_atom') if pna_operation else (('leaving_atom',) if name == 'phosphate' else ())
            _object(intent, ('state', 'partner', 'symmetry_operation') + extra)
            if pna_operation:
                report['policy_id'] = STATE_POLICY_ID
                report['limitations'][2:4] = [
                    'Source-state retention, neutral furanose deletions and explicit neutral-pna-amide-v1 operations only.',
                    'Charged PNA reaction sites and free-5prime-OH reconstruction require separate chemical-state authority.',
                ]
            if intent['symmetry_operation'] != 'x,y,z':
                raise ValueError('Require explicitly declared identity-symmetry attachment')
            partner = intent['partner']
            _object(partner, ('site', 'component', 'atom_id'))
            partner_site = _site(partner['site'])
            partner_row = sites.get(partner_site, {})
            if (partner_site == selected or partner_row.get('component') != partner['component']
                    or not isinstance(partner['atom_id'], str)
                    or partner_row.get('atoms', {}).get(partner['atom_id']) != expected_partner[name]):
                raise ValueError('Declared partner absent, self-linked, wrong component or wrong element')
            external.append({'site_atom': source_port['atom_id'], 'partner': partner,
                             'bond_order': 'SINGLE', 'symmetry_operation': 'x,y,z'})
            if name in {'amine', 'carboxyl'}:
                if not pna_operation:
                    report['review_reasons'].append('PNA_LINK_STATE_AUTHORITY_REQUIRED')
                    continue
                from .cif_pna_operations import plan_amide_deletion, POLICY_ID as operation_policy
                deletion = plan_amide_deletion(name, intent, profile, elements, bonds, charges, neighbors)
                if deletion is None or stereo[source_port['atom_id']] not in {'N', '?'}:
                    report['review_reasons'].append('PNA_NEUTRAL_AMIDE_STATE_UNRESOLVED:' + name)
                    continue
                removed.update(deletion)
                operations.append({'policy_id': operation_policy, 'port': name,
                                   'site_atom': source_port['atom_id'], 'deleted_atoms': sorted(deletion),
                                   'added_atoms': [], 'formal_charge_changes': []})
                continue
            atom = source_port['atom_id']
            if name == 'phosphate':
                leaving = intent['leaving_atom']
                if (not isinstance(leaving, str) or elements.get(leaving) != 'O'
                        or {a for a in neighbors[leaving] if elements[a] not in {'H', 'D'}} != {atom}
                        or bonds.get(tuple(sorted((atom, leaving)))) != 'SINGLE'):
                    raise ValueError('Chosen leaving atom is not a terminal single-bonded phosphate oxygen')
                atom = leaving
            hydrogens = _neutral_hydroxyl_hydrogens(atom, elements, bonds, charges, neighbors)
            if hydrogens is None:
                report['review_reasons'].append('PORT_PROTONATION_AUTHORITY_REQUIRED:' + name)
                continue
            removed.update(hydrogens)
            if name == 'phosphate':
                removed.add(atom)
        if any(stereo[a] not in {'N', '?'} for a in removed):
            report['review_reasons'].append('LEAVING_ATOM_STEREO_AUTHORITY_REQUIRED')
        report['review_reasons'] = sorted(set(report['review_reasons']))
        if not report['review_reasons']:
            actual = sites[selected]['atoms']
            retained = elements.keys() - removed
            expected_heavy = {a for a in retained if elements[a] not in {'H', 'D'}}
            model_heavy = {a for a, element in actual.items() if element not in {'H', 'D'}}
            if (model_heavy != expected_heavy or set(actual) - retained
                    or any(elements[a] != e for a, e in actual.items())):
                raise ValueError('Model atom inventory contradicts the exact source projection; no atoms are silently added or deleted')
            expected = _prune(values, removed, outgoing=False)
            report['plan_status'] = 'PROPOSED'
            report['permitted_source_projection'] = {
                'deleted_atoms': sorted(removed), 'retained_atoms': sorted(retained), 'added_atoms': [],
                'deleted_bonds': [{'atoms': list(pair), 'order': order} for pair, order in sorted(bonds.items()) if set(pair) & removed],
                'formal_charge_changes': [], 'declared_external_bonds': external,
                'retained_formal_charges': {a: charges[a] for a in sorted(retained)},
                'retained_stereo_declarations': {a: stereo[a] for a in sorted(retained)},
                'table_rule': 'Preserve all columns and retained rows; delete rows referencing removed atoms and update existing atom counts only.',
                'native_energy_type_changes': 'NOT_ASSIGNED',
            }
            if operations:
                report['permitted_source_projection']['chemical_state_operations'] = operations
            if candidate is not None:
                wanted = _tables(expected)
                try:
                    found = _tables(_projection_values(paths['candidate'], code))
                except ValueError as exc:
                    report['projection_check'] = {'status': 'MISMATCH', 'reason': str(exc)}
                else:
                    changed = sorted(k for k in wanted.keys() | found.keys() if wanted.get(k) != found.get(k))
                    report['projection_check'] = {'status': 'MISMATCH' if changed else 'MATCH', 'changed_categories': changed}
    if any(path.read_bytes() != payloads[key] for key, path in paths.items()):
        raise ValueError('Attachment-site input changed during inspection')
    if (profile['source']['sha256'] != report['inputs']['source']['sha256']
            or profile['workbook']['sha256'] != report['inputs']['workbook']['sha256']):
        raise ValueError('Attachment-profile input changed before site binding')
    report['input_integrity'] = 'UNCHANGED'
    return report
