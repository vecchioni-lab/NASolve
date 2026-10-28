"""Read-only comparison of declared source links with preserved native evidence."""
from __future__ import annotations

from collections import Counter
import json
from math import isfinite
from pathlib import Path

from .cif_attachment_links import inspect_attachment_links, _input
from .cif_attachment_sites import _model, _pairs
from .cif_catalogue import _digest
from .cif_linked_preparation import component_values
from .cif_native_validation import NATIVE_POLICY_ID, _NATIVE_WORKER, _check_native_report

POLICY_ID = 'cif-source-native-link-audit-v1'
MAX_RECEIPT_BYTES = 16 * 1024 * 1024
# Coordinate conversion roundoff only, far below the PDB 0.001 A grid.
COORDINATE_ROUNDOFF_A = 1e-9


def _nonfinite(value):
    raise ValueError('Nonfinite native JSON value: ' + value)


def _json(data):
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=_nonfinite)


def _capture(path, model):
    path = Path(path).expanduser().resolve(strict=True)
    if path.stat().st_size > MAX_RECEIPT_BYTES:
        raise ValueError('Native receipt size limit exceeded')
    snapshots = {path: path.read_bytes()}
    receipt = _json(snapshots[path])
    if (type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1
            or receipt.get('audit_kind') != 'cif_native_bundle_inspection'
            or receipt.get('policy_id') != NATIVE_POLICY_ID
            or receipt.get('status') not in {'REVIEW', 'FAILED', 'UNSUPPORTED'}
            or receipt.get('source_preserved') is not True
            or receipt.get('frozen_inputs_preserved') is not True or receipt.get('symlink_outputs') != []
            or receipt.get('automatic_adoption') is not False
            or any(receipt.get(k) != 'NOT_RUN' for k in ('scientific_approval', 'optimization', 'model_editing', 'readyset_retry'))):
        raise ValueError('Require a preserved read-only native capture receipt')
    execution = receipt.get('execution', {})
    rc = execution.get('returncode')
    if (type(rc) is not int or execution.get('status') not in {'COMPLETED', 'FAILED'}
            or (execution['status'] == 'COMPLETED') != (rc == 0)
            or (receipt['status'] == 'REVIEW') != (rc == 0)):
        raise ValueError('Incomplete or inconsistent native execution receipt')
    records = {}
    for kind in ('inputs', 'outputs'):
        rows = receipt.get(kind)
        if not isinstance(rows, list) or not rows:
            raise ValueError('Missing native artifact inventory')
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or row.get('anchor') != 'native_directory':
                raise ValueError('Invalid native artifact anchor')
            ref = {key: row.get(key) for key in ('path', 'sha256', 'size')}
            if not isinstance(ref['path'], str) or ref['path'] in seen:
                raise ValueError('Duplicate or invalid native artifact path')
            seen.add(ref['path'])
            selected = _input(path.parent, dict(ref, anchor='manifest_directory'), snapshots)
            if kind == 'outputs': records[ref['path']] = snapshots[selected]
    for row in receipt['inputs']:
        if row['path'] not in records or _digest(records[row['path']]) != {k: row[k] for k in ('sha256','size')}:
            raise ValueError('Native input missing from preserved output inventory')
    for name in ('native_spec.json', 'native_worker.py', 'native_validation.json', 'native.log'):
        if name not in records:
            raise ValueError('Missing required native artifact: ' + name)
    spec = _json(records['native_spec.json'])
    worker = _NATIVE_WORKER
    if 'atom_name_mapping' in spec:
        from .cif_native_atom_mapping import native_mapping_worker, POLICY_ID as mapping_policy
        if spec['atom_name_mapping'] is not True or receipt.get('atom_name_mapping_policy') != mapping_policy:
            raise ValueError('Invalid native atom mapping request/policy')
        worker = native_mapping_worker(worker)
    elif 'atom_name_mapping_policy' in receipt:
        raise ValueError('Unrequested native atom mapping policy')
    if records['native_worker.py'] != worker.encode():
        raise ValueError('Require a maintained native inventory worker')
    roles = {'model': [], 'dictionary': [], 'phil': []}
    for i, row in enumerate(receipt['inputs']):
        if type(row.get('input_index')) is not int or row['input_index'] != i or row.get('role') not in roles:
            raise ValueError('Invalid native input role/order')
        roles[row['role']].append(row['path'])
    if (len(roles['model']) != 1 or spec.get('model') != roles['model'][0]
            or spec.get('dictionaries') != roles['dictionary'] or spec.get('phil_files') != roles['phil']
            or spec.get('policy_id') != NATIVE_POLICY_ID or spec.get('inventory_detail') != 'linked'
            or spec.get('phil_namespace_policy') != receipt.get('phil_namespace_policy')
            or records[roles['model'][0]] != model):
        raise ValueError('Native spec/model differs from explicit captured inputs')
    installed = receipt.get('dictionary_source_policy') == 'INSTALLED_LIBRARY_ONLY'
    if (receipt.get('dictionary_source_policy') not in {'INSTALLED_LIBRARY_ONLY','EXPLICIT_DICTIONARIES'}
            or spec.get('installed_library_only', False) is not installed
            or installed != (not roles['dictionary'])):
        raise ValueError('Inconsistent native dictionary authority')
    native = _json(records['native_validation.json'])
    if native.get('atom_name_mapping_policy') != receipt.get('atom_name_mapping_policy'):
        raise ValueError('Native atom mapping policy differs from receipt')
    if native != receipt.get('native_validation'):
        raise ValueError('Native report differs from embedded receipt')
    if type(native.get('schema_version')) is not int or native.get('automatic_adoption') is not False:
        raise ValueError('Invalid native report schema/adoption claim')
    _check_native_report(native, len(roles['dictionary']))
    if native['status'] == 'REVIEW' and (
            [r.get('input') for r in native['dictionary_loading']] != roles['dictionary']
            or [r.get('input') for r in native.get('phil_adaptations',[])] != roles['phil']):
        raise ValueError('Native consumed inputs differ from the selected dictionary/PHIL order')
    if native['status'] != receipt['status'] or not isinstance(receipt.get('phenix_version'), str) or not receipt['phenix_version'].strip():
        raise ValueError('Native report status/version differs from receipt')
    return receipt, native, snapshots


def _identity(row):
    ident = row['identity']
    if any(ident.get(key, '').strip() for key in ('model_id','icode','altloc')):
        raise ValueError('Unsupported native model/conformer identity')
    site = (ident['chain_id'].strip() or '_') + ':' + ident['resseq'].strip()
    return site, ident['resname'].strip(), row['atom_id']


def _xyz_match(actual, expected):
    return (isinstance(actual, list) and len(actual) == 3
            and all(type(x) in (int,float) and isfinite(x) and abs(x-y) <= COORDINATE_ROUNDOFF_A
                    for x,y in zip(actual,expected)))


def _native_atoms(native, payload):
    expected = {}
    _model(payload)  # Reuse the strict supported PDB identity contract.
    for line in payload.decode().splitlines():
        if line[:6] not in {'ATOM  ', 'HETATM'}: continue
        key = ((line[21:22].strip() or '_') + ':' + str(int(line[22:26])), line[17:20].strip(), line[12:16].strip())
        expected[key] = (line[76:78].strip().upper(), [float(line[i:i+8]) for i in (30,38,46)], float(line[54:60]))
    atoms = native.get('atoms', [])
    if len(atoms) != len(expected) or native.get('atom_count') != len(atoms):
        raise ValueError('Native atom count differs from bound model')
    keys, labels = [], []
    for i, row in enumerate(atoms):
        key = _identity(row)
        if (type(row.get('i_seq')) is not int or row['i_seq'] != i or key in keys
                or key not in expected or not isinstance(row.get('label'), str) or row['label'] in labels
                or row.get('element','').strip().upper() != expected[key][0]
                or not _xyz_match(row.get('xyz'),expected[key][1])
                or type(row.get('occupancy')) not in (int,float) or row['occupancy'] != expected[key][2]):
            raise ValueError('Native atom identity/coordinates differ from bound model')
        keys.append(key);labels.append(row['label'])
    return keys, labels


def _links(native, keys, labels, selected):
    geometry = native['geometry']
    sites = geometry.get('sites_cart_exact')
    if (geometry.get('status') != 'RECORDED' or not isinstance(sites,list) or len(sites)!=len(keys)
            or any(not _xyz_match(x,a['xyz']) for x,a in zip(sites,native['atoms']))):
        raise ValueError('Native geometry coordinates differ from bound model')
    links, symmetry = [], []
    for kind in ('simple','asu'):
        rows = geometry[kind + '_bonds']
        if (geometry.get('proxy_counts',{}).get('bond_' + kind) != len(rows)
                or geometry.get('proxy_details',{}).get('bond_' + kind) != rows):
            raise ValueError('Native bond inventories disagree')
        for row in rows:
            ids = row['i_seqs']
            if (len(ids) != 2 or any(type(i) is not int or not 0 <= i < len(keys) for i in ids)
                    or row.get('atoms') != [labels[i] for i in ids]):
                raise ValueError('Native proxy atom indices/labels disagree')
            ends = [keys[i] for i in ids]
            if not any(e[0] in selected for e in ends): continue
            if kind == 'asu' or row.get('symmetry_operation') not in (None, 'x,y,z'):
                symmetry.append(row);continue
            if ends[0][0] == ends[1][0]: continue
            target, weight = row.get('distance_ideal'), row.get('weight')
            if any(type(v) not in (int,float) or not isfinite(v) or v <= 0 for v in (target,weight)):
                raise ValueError('Native link target/weight must be finite and positive')
            links.append({'endpoints': [list(e) for e in sorted(ends)], 'distance_ideal': target, 'weight': weight,
                          'origin_id': row.get('origin_id')})
    return links, symmetry


def _definitions(plan, native, root, snapshots, name_maps=None):
    rows = native.get('monomer_mappings',{}).get('rows',[])
    by_site = {}
    for row in rows:
        if row['site'] in by_site: raise ValueError('Duplicate native monomer mapping')
        by_site[row['site']] = row
    result = {}
    for site, report in plan['site_reports'].items():
        row = by_site.get(site,{})
        meta = row.get('metadata',{})
        definition = meta.get('effective_definition',{})
        actual_rows = definition.get('atoms') or []
        actual = {a['atom_id']: a for a in actual_rows}
        if len(actual) != len(actual_rows): raise ValueError('Duplicate effective atom definition')
        projection = report['permitted_source_projection']
        entry = next(e for e in plan['input_manifest']['sites'] if _json(snapshots[root/e['context']['path']])['site'] == site)
        values = component_values(root/entry['source']['path'], report['component'])
        source = dict(zip(values['_chem_comp_atom.atom_id'], values['_chem_comp_atom.type_symbol']))
        declared = set(projection['retained_atoms']) if projection else set()
        names = {a: (name_maps or {}).get(site, {}).get(a, a) for a in declared}
        if len(set(names.values())) != len(names):
            raise ValueError('Native aliases collapse distinct source atoms')
        expected = set(names.values())
        source = {names[a]: source[a] for a in declared}
        missing, extra = sorted(expected-actual.keys()), sorted(actual.keys()-expected)
        bad_elements = sorted(a for a in expected & actual.keys() if actual[a].get('type_symbol','').upper() != source[a].upper())
        charges, unknown = [], []
        for atom, charge in (projection or {}).get('retained_formal_charges',{}).items():
            observed = actual.get(names[atom],{}).get('charge')
            try:
                if type(observed) is bool: raise ValueError()
                number = float(observed)
                if not isfinite(number): raise ValueError()
            except (ValueError,TypeError): unknown.append(atom)
            else:
                if number != charge: charges.append({'atom_id':atom,'source':charge,'native':observed})
        literal = row.get('literal_identity',{})
        identity_ok = (row.get('resname') == report['component'] and literal.get('status') == 'RECORDED'
                       and _identity({'identity':literal,'atom_id':''})[:2] == (site,report['component']))
        clean_mapping = all(row.get(k,{}).get('status') == 'RECORDED' and row[k].get('atom_ids') == []
                            for k in ('unexpected_atoms','missing_non_hydrogen_atoms'))
        bonds = definition.get('bonds')
        # Names change only through the optional, index-bound observed mapping.
        # Protonation and atoms absent from the model are never inferred.
        expected_bonds = Counter(tuple(sorted((names[a],names[b]))) for a,b in zip(values.get('_chem_comp_bond.atom_id_1',[]),values.get('_chem_comp_bond.atom_id_2',[])) if a in declared and b in declared)
        actual_bonds = Counter(tuple(sorted((b['atom_id_1'],b['atom_id_2']))) for b in bonds or [])
        atoms_match = bool(projection) and identity_ok and clean_mapping and not missing and not extra and not bad_elements
        result[site] = {'component':report['component'], 'status':'MATCH' if atoms_match and bonds is not None and expected_bonds == actual_bonds and not charges else 'REVIEW',
            'missing_atoms':missing,'extra_atoms':extra,'wrong_elements':bad_elements,'literal_identity_matches':identity_ok,
            'model_mapping_complete':clean_mapping,'source_bond_adjacency_matches':bonds is not None and expected_bonds == actual_bonds,
            'group_observed':meta.get('group'),'classification_observed':meta.get('classification'),
            'energy_types_observed':{a:actual[a].get('type_energy') for a in sorted(actual)},
            'energy_type_authority':'NOT_QUALIFIED', 'formal_charge_status':'CONTRADICTION' if charges else 'UNSUPPORTED' if unknown else 'MATCH' if projection else 'NOT_ASSESSED',
            'formal_charge_contradictions':charges,'unavailable_formal_charge_atoms':sorted(unknown),'partial_charge_substituted':False}
        if name_maps is not None:
            result[site]['atom_name_aliases'] = {k:v for k,v in names.items() if k != v}
            result[site]['source_atoms_without_model_binding'] = sorted(declared - name_maps.get(site,{}).keys())
    return result


def _inspect_native_attachment_links(manifest, native_receipt):
    """Audit exact source/native identities; never assign native typing authority."""
    manifest = Path(manifest).expanduser().resolve(strict=True)
    original = manifest.read_bytes();root = manifest.parent
    plan = inspect_attachment_links(manifest)
    if any(plan['manifest'][key] != value for key,value in _digest(original).items()):
        raise ValueError('Source manifest changed before native audit')
    snapshots = {manifest:original}
    for role in ('model','workbook'): _input(root,plan['input_manifest'][role],snapshots)
    for entry in plan['input_manifest']['sites']:
        for role in ('source','context','candidate'):
            if role in entry: _input(root,entry[role],snapshots)
    payload = snapshots[root/plan['input_manifest']['model']['path']]
    receipt,native,captured = _capture(native_receipt,payload)
    snapshots.update(captured)
    result = {'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','source_plan':plan,
        'native_receipt':{'anchor':'native_receipt_directory','path':next(iter(captured)).name,**_digest(next(iter(captured.values())))},
        'phenix_version':receipt['phenix_version'],'captured_execution':receipt['execution']['status'],
        'native_status':native['status'],'native_error':native.get('error'),
        'native_unsupported_fields':native.get('unsupported_fields',[]),
        'definition_scope':'EXACT_SOURCE_ATOM_NAMES_ELEMENTS_ADJACENCY_AND_AVAILABLE_FORMAL_CHARGES',
        'coordinate_roundoff_angstrom':COORDINATE_ROUNDOFF_A,
        'dictionary_source_policy':receipt['dictionary_source_policy'],
        'link_status':'NOT_ASSESSED','definition_status':'NOT_ASSESSED','links':[], 'definitions':{},
        'automatic_adoption':False,'native_execution':'NOT_RUN_BY_READER','native_qualification':'NOT_ASSESSED',
        'limitations':['Hash-bound capture replay is integrity evidence, not cryptographic proof of execution origin.',
            'Exact source names and adjacency only; native aliases and protonation changes need explicit policies.',
            'Observed atom types and positive link targets/weights do not qualify numerical or chemical correctness.',
            'No source repair, model editing, native execution or runtime adoption occurs.']}
    if native['status'] == 'REVIEW':
        if native.get('inventory_detail') != 'linked' or native.get('fatal_problems') is not None or native.get('unused_definitions'):
            raise ValueError('Incomplete native linked inventory')
        keys,labels = _native_atoms(native,payload)
        links,symmetry = _links(native,keys,labels,set(plan['covered_sites']))
        expected = Counter(tuple(sorted((e['site'],e['component'],e['atom_id']) for e in link['endpoints'])) for link in plan['links'])
        observed = Counter(tuple(tuple(e) for e in link['endpoints']) for link in links)
        result.update(links=links, symmetry_bonds_touching_selected_sites=symmetry,
            missing_links=[[list(p) for p in e] for e in (expected-observed).elements()],
            unexpected_links=[[list(p) for p in e] for e in (observed-expected).elements()],
            link_status='MATCH' if expected and expected==observed and not symmetry and plan['binding_status']=='BOUND' else 'REVIEW')
        result['definitions'] = _definitions(plan,native,root,snapshots)
        result['definition_status'] = 'MATCH' if plan['plan_status']=='PROPOSED' and all(row['status']=='MATCH' for row in result['definitions'].values()) else 'REVIEW'
        if receipt.get('atom_name_mapping_policy'):
            from .cif_native_atom_mapping import bound_name_mappings
            mapping, name_maps = bound_name_mappings(native, keys)
            result['limitations'].append('Mapped comparison uses only observed model-to-definition aliases; unmodelled names, hydrogens and protonation are not inferred.')
            result.update(atom_name_mapping=mapping, mapped_definitions={}, mapped_definition_status='NOT_ASSESSED')
            if mapping['status'] == 'RECORDED':
                result['mapped_definitions'] = _definitions(plan,native,root,snapshots,name_maps)
                result['mapped_definition_status'] = 'MATCH' if plan['plan_status']=='PROPOSED' and all(
                    row['status']=='MATCH' for row in result['mapped_definitions'].values()) else 'REVIEW'

    if any(path.read_bytes()!=data for path,data in snapshots.items()):
        raise ValueError('Native link audit evidence changed during inspection')
    result['input_integrity']='UNCHANGED'
    return result


def inspect_native_attachment_links(manifest, native_receipt):
    """Read a hash-bound capture as data; malformed structures fail closed."""
    try:
        return _inspect_native_attachment_links(manifest, native_receipt)
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise ValueError('Malformed native attachment evidence: ' + str(exc)) from exc
