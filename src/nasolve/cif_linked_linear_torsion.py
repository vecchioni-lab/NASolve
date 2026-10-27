"""Exact linked-manager inventory delta for a declaration-based omission candidate.

This is an inventory gate, not energy, derivative or scientific qualification.
The candidate applies to every modeled occurrence of the named component.
"""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_linear_torsion_candidate import T, prepare_linear_torsion_candidate
from .cif_triple_bond_audit import _key, _numeric
from .cif_stereochemistry_audit import _values
from .cif_recovered_precision import inspect_declared_axis

POLICY_ID = 'cif-linked-linear-torsion-inventory-v1'
_IDENTITY = ('model_id', 'chain_id', 'resseq', 'icode', 'altloc', 'resname')


def _need(value, message):
    if not value:
        raise ValueError(message)


def _exact(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def _identity(row):
    _need(all(isinstance(row.get(k), str) for k in _IDENTITY), 'Incomplete literal residue identity')
    return tuple(row[k].strip() for k in _IDENTITY)


def _torsion(row):
    return _key([row['atom_id_' + str(i)] for i in range(1, 5)])


def qualify_linked_linear_torsion_candidate(before, after, source, component, candidate):
    """Rebuild the complete plan, then allow only its definition/proxy removals.

    Inputs are verified native inventories captured with identical ordered model,
    dictionary and PHIL inputs except for the named dictionary replacement. Caller
    must validate capture/input provenance. This function checks dictionary bytes
    and native inventory contents; it does not authenticate native execution.
    Temporary plan construction never changes the supplied artifacts.
    """
    source, candidate = Path(source), Path(candidate)
    original, proposed = source.read_bytes(), candidate.read_bytes()
    with TemporaryDirectory(prefix='nasolve-linear-plan-') as scratch:
        rebuilt = Path(scratch).resolve() / 'candidate.cif'
        plan = prepare_linear_torsion_candidate(source, component, rebuilt)
        _need(proposed == rebuilt.read_bytes(),
              'Candidate differs from the complete declaration-based omission plan')
    _need(source.read_bytes() == original and candidate.read_bytes() == proposed, 'Dictionary changed during qualification')
    requested = {_torsion({k[len(T):]: v for k, v in row.items()}): row for row in plan['removed_torsions']}
    values = _values(source, component)
    expected = deepcopy(before)
    for native in (before, after):
        _need(native.get('status') == 'REVIEW' and native.get('fatal_problems') is None
              and native.get('unsupported_fields') == [] and native.get('unused_definitions') == [],
              'Require complete, supported native inventories')
        _need(native.get('inventory_detail') == 'linked', 'Require linked native detail')

    def omit(definition):
        kept, seen = [], []
        for row in definition['torsions']:
            key = _torsion(row)
            if key not in requested:
                kept.append(row)
                continue
            planned = requested[key]
            proxy = {'angle_ideal': _numeric(planned[T+'value_angle']),
                     'weight': 1 / _numeric(planned[T+'value_angle_esd']) ** 2,
                     'periodicity': _numeric(planned[T+'period'])}
            declaration = inspect_declared_axis(values, list(key), definition, proxy)
            _need(declaration['status'] == 'DECLARED_LINEAR_ROW_MATCH',
                  'Native triple/linear declarations differ from the omission prerequisites')
            for field in ('id', 'value_angle', 'value_angle_esd', 'period'):
                value = planned[T + field]
                if field != 'id':
                    value = _numeric(value)
                _need(row[field] == value, 'Native effective torsion differs from planned parameters')
            seen.append(key)
        _need(len(seen) == len(requested) and set(seen) == set(requested),
              'Complete planned definition membership is missing or ambiguous')
        definition['torsions'] = kept

    providers = [m for row in expected['dictionary_loading'] for m in row['component_metadata'] if m['id'] == component]
    _need(len(providers) == 1, 'Require one native dictionary provider for the component')
    omit(providers[0]['effective_definition'])
    mappings = expected['monomer_mappings']['rows']
    identities = [_identity(row['literal_identity']) for row in mappings]
    _need(len(set(identities)) == len(identities), 'Ambiguous native residue mappings')
    selected = {}
    for row, identity in zip(mappings, identities):
        if identity[-1] == component:
            omit(row['metadata']['effective_definition'])
            selected[identity] = row
    _need(selected, 'No modeled occurrence of the component')
    index, names = {}, {site: {} for site in selected}
    for atom in before['atoms']:
        i = atom['i_seq']
        _need(type(i) is int and i not in index, 'Duplicate or invalid native atom index')
        identity = _identity(atom['identity'])
        index[i] = (identity, atom['atom_id'])
        if identity in names:
            _need(atom['atom_id'] not in names[identity], 'Ambiguous modeled atom identity')
            names[identity][atom['atom_id']] = i
    active = {(site, key) for site in selected for key in requested if all(n in names[site] for n in key)}
    _need(active, 'No active planned omissions')
    seen, counts = [], {}
    for kind in ('dihedral', 'const_dihedral'):
        kept, count = [], 0
        for row in expected['geometry']['proxy_details'][kind]:
            atoms = [index[i] for i in row['i_seqs']]
            key = _key([a[1] for a in atoms])
            site = atoms[0][0]
            if all(a[0] == site for a in atoms) and (site, key) in active:
                planned = requested[key]
                _need(row['angle_ideal'] == _numeric(planned[T+'value_angle'])
                      and row['weight'] == 1 / _numeric(planned[T+'value_angle_esd']) ** 2
                      and row['periodicity'] == _numeric(planned[T+'period'])
                      and row.get('alt_angle_ideals') is None and row.get('origin_id') == 0,
                      'Planned proxy parameters or origin differ')
                seen.append((site, key)); count += 1
            else:
                kept.append(row)
        expected['geometry']['proxy_details'][kind] = kept
        expected['geometry']['proxy_counts'][kind] -= count
        counts[kind] = count
    _need(len(seen) == len(active) and set(seen) == active, 'Active planned proxy membership is missing or ambiguous')
    # Energy observations necessarily change and belong to the next, separate gate.
    # No other inventory category is ignored, including unknown future categories.
    expected.pop('energy_inventory', None)
    actual = deepcopy(after)
    actual.pop('energy_inventory', None)
    checks = {key: key in actual and key in expected and _exact(actual[key], expected[key])
              for key in sorted(set(actual) | set(expected))}
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW',
            'inventory_checks_pass': all(checks.values()), 'checks': checks, 'plan': plan,
            'component': component, 'modeled_occurrences': len(selected),
            'removed_effective_torsions': len(selected) * len(requested),
            'removed_native_proxy_counts': counts, 'energy_delta_qualification': 'NOT_RUN',
            'derivative_qualification': 'NOT_RUN', 'scientific_approval': 'NOT_RUN',
            'model_editing': 'NOT_RUN', 'optimization': 'NOT_RUN', 'automatic_adoption': False}
