"""Compare graph-selected linear neighborhoods with explicit numerical references.

Reference equilibrium lengths are model predictions, not experimental observations
or calibrated CIF targets. This module neither runs a provider nor approves its
provenance. Separate candidates require explicit bond selection; ordinary repair
and historical triple-screen policies remain unchanged.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path

from .cif_stereochemistry_audit import _values, _graph, _stereo
from .cif_triple_bond_audit import _numeric, _rows
from .ligand_profiles import _blocks, _emit

QUERY_POLICY = 'cif-source-linear-bond-query-v1'
REFERENCE_POLICY = 'cif-mmff-linear-bond-reference-v1'
ENERGY_REFERENCE_POLICY = 'cif-energy-library-linear-bond-reference-v1'
POLICY_ID = 'cif-linear-bond-reference-comparison-v1'
CANDIDATE_POLICY = 'cif-linear-bond-reference-candidate-v1'
_B = '_chem_comp_bond.'


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _pair(value):
    _need(isinstance(value, (list, tuple)) and len(value) == 2
          and all(isinstance(x, str) and x for x in value) and value[0] != value[1],
          'Require two distinct explicit atom names')
    return tuple(sorted(value))


def linear_bond_query(source, code):
    """Select every explicit triple and its heavy-atom single-bond neighbors.

    Complete source atom identities, orders, charges and stereo declarations bind
    the query. Coordinates and experimental models are deliberately not inputs.
    Unknown chemical orders or charges cannot silently become provider defaults.
    """
    source = Path(source); original = source.read_bytes(); values = _values(source, code)
    elements, orders, charges, neighbors = _graph(values); stereo = _stereo(values)
    _need(all(o in {'SINGLE', 'DOUBLE', 'TRIPLE', 'AROMATIC'} for o in orders.values()),
          'Reference query requires supported explicit source bond orders')
    _need(all(type(c) in (int, float) and math.isfinite(c) and c == int(c) for c in charges.values()),
          'Reference query requires explicit integer source formal charges')
    triples = {pair for pair, order in orders.items() if order == 'TRIPLE'}
    selected = triples | {tuple(sorted((a, n))) for pair in triples for a in pair
                          for n in neighbors[a] if orders[tuple(sorted((a, n)))] == 'SINGLE'
                          and elements[n] not in {'H', 'D'}}
    _need(source.read_bytes() == original, 'Source changed during reference-query preparation')
    return dict(policy_id=QUERY_POLICY, component=code, source_sha256=sha256(original).hexdigest(),
                atoms=[dict(id=n, element=elements[n], charge=int(charges[n]), stereo=stereo[n])
                       for n in sorted(elements)],
                bonds=[dict(atoms=list(pair), order=order) for pair, order in sorted(orders.items())],
                selected_bonds=[list(pair) for pair in sorted(selected)],
                coordinate_input='NOT_USED', stereochemistry_inference='NOT_RUN')


def _reference_rows(query, reference):
    _need(isinstance(reference, dict) and reference.get('policy_id') in {REFERENCE_POLICY, ENERGY_REFERENCE_POLICY}
          and reference.get('status') == 'RECORDED' and reference.get('query') == query,
          'Reference does not bind the exact source query')
    provider = reference.get('provider', {})
    energy = reference['policy_id'] == ENERGY_REFERENCE_POLICY
    expected_provider = 'Phenix/energy-library' if energy else 'RDKit/MMFF94s'
    _need(isinstance(provider, dict) and provider.get('name') == expected_provider and isinstance(provider.get('version'), str)
          and bool(provider['version'].strip()), 'Require an explicit supported reference model/version')
    _need(reference.get('chemical_approval') == 'NOT_ASSESSED'
          and reference.get('automatic_adoption') is False, 'Reference must not claim chemical approval')
    rows = reference.get('bonds'); _need(isinstance(rows, list), 'Missing reference bond rows')
    result = {}
    for row in rows:
        _need(isinstance(row, dict), 'Invalid reference row')
        pair = _pair(row.get('atoms'))
        _need(pair not in result, 'Duplicate reference bond')
        if energy and row.get('status') == 'UNSUPPORTED':
            _need(isinstance(row.get('reason'), str) and bool(row['reason'])
                  and set(row) == {'atoms', 'status', 'reason'}, 'Malformed unsupported reference')
            result[pair] = row
            continue
        _need(_positive(row.get('force_constant')) and _positive(row.get('equilibrium_angstrom')),
              'Reference requires positive finite parameters')
        if energy:
            types = _source_energy_types(query)
            orders = {tuple(r['atoms']): r['order'] for r in query['bonds']}
            typed = [types.get(a) for a in pair]
            _need(orders.get(pair) == 'SINGLE' and 'CSP' in typed
                  and any(t in {'CH1', 'CH2', 'CH3', 'CT'} for t in typed),
                  'Energy reference is outside the supported source neighborhood')
            _need(row.get('status') == 'SUPPORTED' and row.get('bond_type') == 'SINGLE'
                  and row.get('atom_types') == [types.get(a) for a in pair]
                  and _positive(row.get('reference_esd_angstrom')), 'Invalid source-typed energy reference')
            raw = row.get('library_bond_row', {})
            _need(isinstance(raw, dict) and {raw.get('atom_type_1'), raw.get('atom_type_2')} == set(row['atom_types'])
                  and isinstance(raw.get('type'), str) and raw['type'].lower() == 'single'
                  and _numeric(raw.get('length')) == row['equilibrium_angstrom']
                  and _numeric(raw.get('value_esd')) == row['reference_esd_angstrom']
                  and _numeric(raw.get('const')) == row['force_constant'], 'Library row and reference differ')
        else:
            _need(type(row.get('bond_type')) is int and row['bond_type'] >= 0
                  and isinstance(row.get('atom_types'), list) and len(row['atom_types']) == 2
                  and all(type(x) is int and x > 0 for x in row['atom_types']), 'Invalid reference atom/bond types')
        result[pair] = row
    _need(set(result) == {tuple(p) for p in query['selected_bonds']},
          'Reference must cover exactly the complete selected neighborhood')
    return result


def compare_linear_bond_reference(source, dictionary, code, reference):
    """Report every difference; set no new acceptance or repair threshold.

    Dividing by the dictionary ESD describes its declared restraint scale. It is
    not a statistical Z score against MMFF, whose prediction uncertainty is not
    supplied. Returned agreement never establishes chemical approval.
    """
    source, dictionary = Path(source), Path(dictionary)
    frozen = source.read_bytes(), dictionary.read_bytes()
    query = linear_bond_query(source, code); support = _reference_rows(query, reference)
    sv, dv = _values(source, code), _values(dictionary, code)
    source_graph = _graph(sv)
    _need(source_graph == _graph(dv), 'Source and dictionary chemical graphs differ')
    if reference['policy_id'] == ENERGY_REFERENCE_POLICY:
        _need(reference.get('dictionary_atom_types') == _dictionary_types(dv),
              'Energy reference dictionary atom types differ')
    rows = _rows(dv, 'bond', 2); observations = []
    for pair in query['selected_bonds']:
        key = tuple(pair); matches = [r for r in rows if _pair(r['atoms']) == key]
        _need(len(matches) == 1, 'Require one exact dictionary bond row')
        target = _numeric(matches[0].get('value_dist')); esd = _numeric(matches[0].get('value_dist_esd'))
        _need(_positive(target) and _positive(esd), 'Require positive finite dictionary target and ESD')
        row = support[key]
        if row.get('status') == 'UNSUPPORTED':
            observations.append(dict(atoms=pair, declared_order=source_graph[1][key], target_angstrom=target,
                                     dictionary_esd_angstrom=esd, reference_equilibrium_angstrom=None,
                                     reference_status='UNSUPPORTED', reason=row['reason']))
            continue
        equilibrium = row['equilibrium_angstrom']; difference = target-equilibrium
        scaled_difference = difference/esd
        _need(math.isfinite(difference) and math.isfinite(scaled_difference),
              'Reference discrepancy cannot be represented finitely')
        observations.append(dict(atoms=pair, declared_order=source_graph[1][key], target_angstrom=target,
                                 reference_status='SUPPORTED', reference_esd_angstrom=row.get('reference_esd_angstrom'),
                                 dictionary_esd_angstrom=esd, reference_equilibrium_angstrom=equilibrium,
                                 target_minus_reference_angstrom=difference,
                                 difference_over_dictionary_esd=scaled_difference,
                                 reference_force_constant=row['force_constant']))
    _need((source.read_bytes(), dictionary.read_bytes()) == frozen, 'Reference comparison inputs changed')
    return dict(schema_version=1, policy_id=POLICY_ID, status='COMPARISON_ONLY', component=code,
                source_sha256=query['source_sha256'], dictionary_sha256=sha256(frozen[1]).hexdigest(),
                reference_sha256=sha256(json.dumps(reference, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                bonds=observations, provider=deepcopy(reference['provider']),
                provider_provenance='SUPPLIED_REFERENCE_NOT_AUTHENTICATED_BY_COMPARISON',
                reference_uncertainty='PER_ROW_LIBRARY_ESD' if reference['policy_id'] == ENERGY_REFERENCE_POLICY else 'NOT_PROVIDED', chemical_approval='NOT_ASSESSED',
                acceptance_threshold='NOT_ASSIGNED', automatic_adoption=False,
                coordinate_input='NOT_USED', source_and_dictionary_preserved=True)


def prepare_linear_bond_candidate(source, dictionary, code, reference, output, *, bonds):
    """Write only explicitly selected equilibrium lengths to a fresh candidate.

    Preserve every ESD, chemical declaration, coordinate and other restraint.
    Neither the supplied reference nor the existing ESD is qualified here; the
    result cannot enter ordinary automatic repair without further evidence.
    """
    source, dictionary = Path(source).resolve(strict=True), Path(dictionary).resolve(strict=True)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    _need(output not in {source, dictionary} and not any(p.is_symlink() for p in output.parents),
          'Require a fresh separate candidate without symlink parents')
    _need(isinstance(bonds, (list, tuple)) and bool(bonds), 'Require explicit nonempty bond selection')
    pairs = [_pair(p) for p in bonds]
    _need(len(set(pairs)) == len(pairs), 'Duplicate candidate bond selection')
    frozen = source.read_bytes(), dictionary.read_bytes()
    comparison = compare_linear_bond_reference(source, dictionary, code, reference)
    available = {tuple(r['atoms']): r for r in comparison['bonds']}
    _need(set(pairs) <= set(available), 'Candidate selection is outside the source linear neighborhood')
    _need(all(available[p]['reference_equilibrium_angstrom'] is not None for p in pairs),
          'Selected bond has no supported numerical reference')
    changes = {p: available[p] for p in pairs
               if available[p]['target_angstrom'] != available[p]['reference_equilibrium_angstrom']}
    _need(bool(changes), 'Selected reference produces no target change')
    expected, rendered, applied = [], [], set()
    for block in _blocks(dictionary):
        values = deepcopy(block.values)
        columns = {k.lower(): k for k in values if k.lower().startswith(_B)}
        changed = False
        if columns:
            required = {_B+k for k in ('comp_id', 'atom_id_1', 'atom_id_2', 'value_dist', 'value_dist_esd')}
            _need(required <= set(columns) and len({len(values[k]) for k in columns.values()}) == 1,
                  'Require complete unambiguous bond columns')
            for i, component in enumerate(values[columns[_B+'comp_id']]):
                if component != code:
                    continue
                pair = _pair([values[columns[_B+'atom_id_'+str(j)]][i] for j in (1, 2)])
                if pair not in changes:
                    continue
                _need(pair not in applied, 'Ambiguous selected bond across blocks')
                _need(not any('value_dist_nucleus' in k for k in columns),
                      'Separate nuclear-distance targets require independent qualification')
                values[columns[_B+'value_dist']][i] = repr(float(changes[pair]['reference_equilibrium_angstrom']))
                applied.add(pair); changed = True
        expected.append(values); rendered.append(_emit(values) if changed else block.text)
    _need(applied == set(changes), 'Candidate target selection was not applied exactly')
    _need((source.read_bytes(), dictionary.read_bytes()) == frozen, 'Candidate inputs changed before writing')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(''.join(rendered))
    _need([b.values for b in _blocks(output)] == expected, 'Candidate exceeded exact target-change allowlist')
    _need((source.read_bytes(), dictionary.read_bytes()) == frozen, 'Candidate inputs changed during writing')
    return dict(schema_version=1, policy_id=CANDIDATE_POLICY, status='CANDIDATE_REVIEW', component=code,
                source_sha256=comparison['source_sha256'], dictionary_sha256=comparison['dictionary_sha256'],
                reference_sha256=comparison['reference_sha256'], candidate_sha256=sha256(output.read_bytes()).hexdigest(),
                changes=[changes[p] for p in sorted(changes)], parsed_allowlist_pass=True,
                provider_provenance=comparison['provider_provenance'], source_preserved=True,
                esd_policy='EXISTING_ESDS_UNCHANGED_NOT_NEWLY_CALIBRATED', model_editing='NOT_RUN',
                scientific_approval='NOT_ASSESSED', native_validation='NOT_RUN', automatic_adoption=False)



def _dictionary_types(values):
    names = values['_chem_comp_atom.atom_id']
    types = values.get('_chem_comp_atom.type_energy', [None]*len(names))
    _need(len(types) == len(names), 'Incomplete dictionary atom types')
    return dict(zip(names, types))


def _source_energy_types(query):
    """Recognize neutral sp and saturated carbon types from explicit valence.

    The labels follow the supplied energy library's documented atom-type
    vocabulary. No bond order, hydrogen, charge, aromaticity or hand is inferred.
    Every recognized atom still needs an exact matching library definition.
    """
    atoms = {r['id']: r for r in query['atoms']}
    bonds = {tuple(r['atoms']): r['order'] for r in query['bonds']}
    neighbors = {a: set() for a in atoms}
    for a, b in bonds:
        neighbors[a].add(b); neighbors[b].add(a)
    types = {}
    for atom, row in atoms.items():
        if row['element'] != 'C' or row['charge'] != 0:
            continue
        adjacent = neighbors[atom]
        orders = [bonds[tuple(sorted((atom, n)))] for n in adjacent]
        hydrogens = [n for n in adjacent if atoms[n]['element'] in {'H', 'D'}]
        if any(len(neighbors[n]) != 1 or atoms[n]['charge'] != 0 for n in hydrogens):
            continue
        if len(adjacent) == 2 and sorted(orders) == ['SINGLE', 'TRIPLE'] and not hydrogens:
            partner = next(n for n in adjacent if bonds[tuple(sorted((atom, n)))] == 'TRIPLE')
            partner_orders = sorted(bonds[tuple(sorted((partner, n)))] for n in neighbors[partner])
            normal_partner = ((atoms[partner]['element'] == 'C' and partner_orders == ['SINGLE', 'TRIPLE'])
                              or (atoms[partner]['element'] == 'N' and partner_orders == ['TRIPLE']))
            if normal_partner and atoms[partner]['charge'] == 0:
                types[atom] = 'CSP'
        elif len(adjacent) == 4 and orders == ['SINGLE']*4 and len(hydrogens) <= 3:
            types[atom] = 'CH'+str(len(hydrogens)) if hydrogens else 'CT'
    return types


def _library_table(blocks, category, fields):
    stem = '_lib_'+category+'.'; rows = []
    for block in blocks:
        columns = {k.lower()[len(stem):]: v for k, v in block.values.items()
                   if k.lower().startswith(stem)}
        if not columns:
            continue
        _need(set(fields) <= set(columns) and len({len(v) for v in columns.values()}) == 1,
              'Incomplete energy-library table')
        rows.extend({k: v[i] for k, v in columns.items()} for i in range(len(next(iter(columns.values())))))
    _need(bool(rows), 'Missing energy-library table')
    return rows


def energy_library_linear_reference(source, dictionary, code, library):
    """Read exact sp-carbon/sp3-carbon single-bond rows from a supplied library.

    Require explicit source valence, agreeing dictionary energy types and unique
    carbon/valency/hybridization definitions. Wildcards, synonyms, missing ESDs
    and other neighborhoods remain unsupported. File provenance is recorded;
    selected-installation authentication belongs to the caller, not this reader.
    """
    paths = [Path(p) for p in (source, dictionary, library)]; frozen = [p.read_bytes() for p in paths]
    query = linear_bond_query(source, code); sv, dv = _values(source, code), _values(dictionary, code)
    _need(_graph(sv) == _graph(dv), 'Source and dictionary chemical graphs differ')
    types = _source_energy_types(query); dictionary_types = _dictionary_types(dv)
    blocks = _blocks(Path(library))
    atoms = _library_table(blocks, 'atom', ['type', 'element', 'valency', 'sp'])
    bonds = _library_table(blocks, 'bond', ['atom_type_1', 'atom_type_2', 'type', 'length', 'value_esd', 'const'])
    orders = {tuple(r['atoms']): r['order'] for r in query['bonds']}; result = []
    for pair in query['selected_bonds']:
        row = dict(atoms=pair, status='UNSUPPORTED', reason='OUTSIDE_NEUTRAL_SP_SP3_SINGLE_BOND_SCOPE')
        result.append(row); typed = [types.get(a) for a in pair]
        if orders[tuple(pair)] != 'SINGLE' or 'CSP' not in typed or not any(t in {'CH1', 'CH2', 'CH3', 'CT'} for t in typed):
            continue
        if typed != [dictionary_types.get(a) for a in pair]:
            row['reason'] = 'SOURCE_AND_DICTIONARY_ENERGY_TYPES_DIFFER'; continue
        definitions = [[a for a in atoms if a['type'] == t] for t in typed]
        if any(len(d) != 1 or d[0]['element'].upper() != 'C' or _numeric(d[0]['valency']) != 4
               or _numeric(d[0]['sp']) != (1 if t == 'CSP' else 3) for t, d in zip(typed, definitions)):
            row['reason'] = 'MISSING_OR_CONFLICTING_LIBRARY_ATOM_TYPE'; continue
        matches = [b for b in bonds if {b['atom_type_1'], b['atom_type_2']} == set(typed) and b['type'].lower() == 'single']
        if len(matches) != 1:
            row['reason'] = 'NO_UNIQUE_EXACT_LIBRARY_BOND'; continue
        raw = matches[0]; target, sigma, constant = [_numeric(raw[k]) for k in ('length', 'value_esd', 'const')]
        if not all(_positive(v) for v in (target, sigma, constant)):
            row['reason'] = 'MISSING_POSITIVE_LIBRARY_PARAMETERS'; continue
        row.clear(); row.update(atoms=pair, status='SUPPORTED', atom_types=typed, bond_type='SINGLE',
                                force_constant=constant, equilibrium_angstrom=target,
                                reference_esd_angstrom=sigma, library_bond_row=deepcopy(raw))
    _need([p.read_bytes() for p in paths] == frozen, 'Energy-reference input changed during reading')
    return dict(policy_id=ENERGY_REFERENCE_POLICY, status='RECORDED', query=query,
                provider=dict(name='Phenix/energy-library', version='EXPLICIT_FILE_SHA256',
                              library_sha256=sha256(frozen[2]).hexdigest()),
                dictionary_atom_types=dictionary_types, bonds=result,
                provider_provenance='SUPPLIED_LIBRARY_NOT_INSTALLATION_AUTHENTICATED',
                chemical_approval='NOT_ASSESSED', automatic_adoption=False)
