"""Frozen explicit PNA source networks, without coordinates or numerical targets."""
from __future__ import annotations

import json
from pathlib import Path

from .cif_attachment_links import inspect_attachment_links, _input, MAX_TOTAL_INPUT_BYTES
from .cif_attachment_sites import _pairs
from .cif_catalogue import _digest
from .cif_linked_preparation import component_values
from .cif_pna_operations import POLICY_ID as OPERATION_POLICY, PROFILE_ID
from .cif_stereochemistry_audit import _graph, _stereo

POLICY_ID = 'cif-explicit-pna-source-network-v1'
RECEIPT = 'preparation-receipt.json'


def _json(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'


def _load(path):
    return json.loads(path.read_text(), object_pairs_hook=_pairs)


def _inputs(manifest, report):
    original = manifest.read_bytes()
    if (_digest(original) != {k: report['manifest'][k] for k in ('sha256', 'size')}
            or _json(json.loads(original, object_pairs_hook=_pairs)) != _json(report['input_manifest'])):
        raise ValueError('Source-network manifest changed during inspection')
    snapshots = {manifest: original}
    declaration = report['input_manifest']
    records = [declaration['model'], declaration['workbook']]
    records += [entry[role] for entry in declaration['sites']
                for role in ('source', 'context', 'candidate') if role in entry]
    for record in records:
        _input(manifest.parent, record, snapshots)
    return snapshots


def _network(manifest, report):
    if (report['plan_status'] != 'PROPOSED' or report['binding_status'] != 'BOUND'
            or report['permitted_source_projections'] is None):
        raise ValueError('Require a completely proposed reciprocal source network')
    atoms, bonds, sites = [], [], {}
    sources = {entry['component']: manifest.parent / entry['source']['path']
               for entry in report['input_manifest']['sites']}
    for site, inspection in report['site_reports'].items():
        if inspection['source_profile']['matched_profile'] != PROFILE_ID:
            raise ValueError('Source-network preparation currently requires explicit PNA profiles')
        plan = inspection['permitted_source_projection']
        operations = plan.get('chemical_state_operations', [])
        if not operations or any(op['policy_id'] != OPERATION_POLICY for op in operations):
            raise ValueError('Require explicit neutral PNA amide operations at every selected site')
        code = inspection['component']
        values = component_values(sources[code], code)
        elements, source_bonds, charges, _ = _graph(values)
        stereo = _stereo(values)
        retained = set(plan['retained_atoms'])
        sites[site] = {'component': code, 'source': report['source_authorities'][code],
                       'projection': plan}
        atoms.extend({'site': site, 'component': code, 'atom_id': atom,
                      'element': elements[atom], 'formal_charge': charges[atom],
                      'source_stereo_declaration': stereo[atom]} for atom in sorted(retained))
        # Preserve explicit bond representation/stereo flags as declarations;
        # never perceive aromaticity or copy isolated numerical bond targets.
        prefix = '_chem_comp_bond.'
        annotations = {}
        for i, (a, b) in enumerate(zip(values[prefix+'atom_id_1'], values[prefix+'atom_id_2'])):
            annotations[tuple(sorted((a, b)))] = {
                key[len(prefix):]: column[i] for key, column in values.items()
                if key in {prefix+'pdbx_aromatic_flag', prefix+'pdbx_stereo_config', prefix+'stereo_config'}}
        for pair, order in sorted(source_bonds.items()):
            if set(pair) <= retained:
                bonds.append({'atoms': [[site, a] for a in pair], 'order': order,
                              'authority': 'RETAINED_SOURCE', 'source_declarations': annotations[pair]})
    for link in report['links']:
        if link['kind'] != 'carboxyl_amine' or link['symmetry_operation'] != 'x,y,z':
            raise ValueError('Require explicitly reciprocal identity-symmetry amide links')
        bonds.append({'atoms': [[e['site'], e['atom_id']] for e in link['endpoints']],
                      'order': link['bond_order'], 'authority': 'EXPLICIT_AMIDE_OPERATION',
                      'operation_policy': OPERATION_POLICY})
    neighbors = {(a['site'], a['atom_id']): set() for a in atoms}
    seen = set()
    for bond in bonds:
        a, b = map(tuple, bond['atoms'])
        pair = frozenset((a, b))
        if a == b or a not in neighbors or b not in neighbors or pair in seen:
            raise ValueError('Invalid or duplicate source-network edge')
        neighbors[a].add(b); neighbors[b].add(a); seen.add(pair)
    visited, pending = set(), [next(iter(neighbors))]
    while pending:
        atom = pending.pop()
        if atom not in visited:
            visited.add(atom); pending.extend(neighbors[atom] - visited)
    if visited != neighbors.keys():
        raise ValueError('Require one connected explicit PNA source network')
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'scope': 'EXPLICIT_LINKED_SOURCE_GRAPH',
            'atoms': atoms, 'bonds': bonds, 'sites': sites,
            'total_formal_charge': sum(a['formal_charge'] for a in atoms),
            'coordinates': 'NOT_ASSIGNED', 'native_energy_types': 'NOT_ASSIGNED',
            'numerical_restraints': 'NOT_ASSIGNED', 'final_stereochemistry': 'NOT_ASSIGNED',
            'automatic_adoption': False,
            'limitations': [
                'Source stereo labels and parent descriptors are provenance, not assigned linked CIP or geometry.',
                'Model atoms bind declared sites; coordinates and inter-site distances do not choose chemistry.',
                'Frozen CIFs retain parent evidence; they are not generated linked numerical dictionaries.',
                'A future generator must preserve this graph and independently qualify linked numerical restraints.']}


def _receipt(manifest_name, files):
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'PREPARED_REVIEW',
            'manifest': {'anchor': 'preparation_directory', 'path': 'inputs/' + manifest_name},
            'network': 'source-network.json', 'inspection': 'link-report.json', 'files': files,
            'native_execution': 'NOT_RUN', 'native_qualification': 'NOT_ASSESSED',
            'numerical_restraints': 'NOT_ASSIGNED', 'automatic_adoption': False}


def _files(directory):
    files = {}
    total = 0
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlink in source-network package')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError('Nonregular source-network artifact')
        if path.name == RECEIPT and path.parent == directory:
            continue
        total += path.stat().st_size
        if total > 4 * MAX_TOTAL_INPUT_BYTES:
            raise ValueError('Source-network package size limit exceeded')
        files[path.relative_to(directory).as_posix()] = _digest(path.read_bytes())
    return files


def read_pna_source_network(directory):
    """Recompute the chemical input from its frozen authorities, without a native SDK."""
    directory = Path(directory).expanduser().absolute()
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError('Symlink in source-network package path')
    try:
        files = _files(directory)
        receipt_path = directory / RECEIPT
        if receipt_path.is_symlink() or receipt_path.stat().st_size > MAX_TOTAL_INPUT_BYTES:
            raise ValueError('Invalid source-network receipt')
        receipt = _load(receipt_path)
        relative = receipt['manifest']['path']
        if (not isinstance(relative, str) or len(relative.split('/')) != 2
                or not relative.startswith('inputs/') or relative.split('/')[1] in {'', '.', '..'}
                or '\\' in relative or ':' in relative):
            raise ValueError('Require an explicit frozen manifest reference')
        if _json(receipt) != _json(_receipt(relative.split('/')[1], files)):
            raise ValueError('Source-network receipt or artifact inventory differs')
        manifest = directory / relative
        report = inspect_attachment_links(manifest)
        inputs = _inputs(manifest, report)
        expected = {'inputs/' + p.relative_to(manifest.parent).as_posix() for p in inputs}
        expected |= {'source-network.json', 'link-report.json'}
        if set(files) != expected:
            raise ValueError('Undeclared or missing source-network artifact')
        if _json(_load(directory/'link-report.json')) != _json(report):
            raise ValueError('Saved link report differs from fresh source inspection')
        if _json(_load(directory/'source-network.json')) != _json(_network(manifest, report)):
            raise ValueError('Saved source network differs from explicit source operations')
        if files != _files(directory) or _json(receipt) != _json(_load(receipt_path)):
            raise ValueError('Source-network package changed during replay')
        return receipt
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Incomplete or invalid source-network package') from exc


def prepare_pna_source_network(manifest, output_directory):
    """Freeze one authorized connected network in a fresh directory; publish receipt last.

    No source/CIF/numerical dictionary is rewritten. Failed partial output is
    retained; retry requires a new output directory.
    """
    manifest = Path(manifest).expanduser().resolve(strict=True)
    output = Path(output_directory).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if (any(p.is_symlink() for p in output.parents)
            or output.is_relative_to(manifest.parent) or manifest.is_relative_to(output)):
        raise ValueError('Preparation output must be separate from preserved inputs and symlinks')
    report = inspect_attachment_links(manifest)
    inputs = _inputs(manifest, report)
    network = _network(manifest, report)
    if any(p.read_bytes() != data for p, data in inputs.items()):
        raise ValueError('Source-network input changed before preparation')
    output.mkdir(parents=True, exist_ok=False)
    for path, payload in inputs.items():
        target = output/'inputs'/path.relative_to(manifest.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(payload)
    # Reinspect the exact copy before publishing any completion marker.
    frozen = output/'inputs'/manifest.name
    if _json(inspect_attachment_links(frozen)) != _json(report):
        raise ValueError('Frozen source-network inspection differs')
    for name, value in [('source-network.json', network), ('link-report.json', report)]:
        with (output/name).open('x') as stream:
            stream.write(_json(value))
    if any(p.read_bytes() != data for p, data in inputs.items()):
        raise ValueError('Source-network input changed during preparation')
    receipt = _receipt(manifest.name, _files(output))
    with (output/RECEIPT).open('x') as stream:
        stream.write(_json(receipt))
    return read_pna_source_network(output)
