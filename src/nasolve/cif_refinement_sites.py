"""Compact observations of selected sites in the actual Phenix model.

The caller qualifies native sources and owns execution. These observations do not
change restraints, retain a second whole-model inventory or approve chemistry.
"""
from contextlib import contextmanager
import math
import re

from .cif_refinement_output import _digest, _hierarchy

POLICY_ID = 'native-refinement-selected-sites-v1'
_KINDS = {
    'bond_simple': ('distance_ideal', 'weight', 'origin_id'),
    'angle': ('angle_ideal', 'weight', 'origin_id'),
    'dihedral': ('angle_ideal', 'weight', 'periodicity', 'origin_id'),
    'const_dihedral': ('angle_ideal', 'weight', 'periodicity', 'origin_id'),
    'chirality': ('volume_ideal', 'both_signs', 'weight', 'origin_id'),
    'planarity': ('weights', 'origin_id'),
    'parallelity': ('weight', 'target_angle_deg', 'slack', 'top_out', 'origin_id'),
}
_BOND_FIELDS = ('atom_id_1', 'atom_id_2', 'type', 'value_dist', 'value_dist_esd')


def _need(value, message):
    if not value:
        raise ValueError(message)


def validate_sites(sites):
    """Validate explicit source-selected scope, without guessing residue families."""
    _need(isinstance(sites, list) and len(sites) <= 1024, 'Unsupported selected-site scope')
    names = []
    for row in sites:
        _need(isinstance(row, dict) and set(row) == {'site', 'component'}
              and isinstance(row['site'], str)
              and re.fullmatch(r'[A-Za-z0-9_]:-?(0|[1-9][0-9]*)', row['site'])
              and not row['site'].endswith(':-0')
              and isinstance(row['component'], str)
              and re.fullmatch(r'[A-Za-z0-9]{1,3}', row['component']), 'Malformed selected-site identity')
        names.append(row['site'])
    _need(names == sorted(set(names)), 'Selected sites must be distinct and ordered')
    return sites


def unavailable(sites, reason):
    validate_sites(sites)
    return dict(policy_id=POLICY_ID, status='UNASSESSED', sites=[dict(row) for row in sites], reason=reason,
                scientific_approval='NOT_RUN')


def _identity(atom):
    labels = atom.fetch_labels()
    identity = {key: getattr(labels, key) for key in
                ('model_id', 'chain_id', 'resseq', 'icode', 'resname', 'altloc')}
    _need(not any(identity[k].strip() for k in ('model_id', 'icode', 'altloc')),
          'Selected observation needs an unambiguous model/conformer')
    site = (identity['chain_id'].strip() or '_') + ':' + identity['resseq'].strip()
    return site, identity


def _plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return [_plain(v) for v in value]


class _Observer:
    def __init__(self, sites):
        self.sites = [dict(row) for row in validate_sites(sites)]
        self.names = {row['site'] for row in sites}
        self.mappings = {}
        self.error = None

    def retain(self, mapping, summary):
        """Retain only selected definitions; the original summary is returned intact."""
        try:
            atoms = list(mapping.pdb_residue.atoms())
            if not atoms:
                return
            # Ignore unrelated conformers rather than enlarging diagnostic scope.
            labels = atoms[0].fetch_labels()
            site = (labels.chain_id.strip() or '_') + ':' + labels.resseq.strip()
            if site not in self.names:
                return
            _identity(atoms[0])
            _need(len(self.mappings) < max(1, 16 * len(self.names)),
                  'Selected definition observation allowance exceeded')
            self.mappings[id(summary)] = (summary, mapping)
        except (AttributeError, TypeError, ValueError, OverflowError) as exc:
            self.error = type(exc).__name__ + ': ' + str(exc)

    def snapshot(self, model):
        """Observe the current manager, retaining global indices and full precision."""
        _need(self.error is None, 'Selected definition observation unavailable: ' + str(self.error))
        hierarchy = model.get_hierarchy()
        state = _digest(_hierarchy(model))
        geometry = model.restraints_manager.geometry
        atoms = list(hierarchy.atoms())
        coordinates = list(model.get_sites_cart())
        _need(len(atoms) == len(coordinates), 'Native model atom/coordinate count differs')
        selected = []; by_index = {}
        for index, atom in enumerate(atoms):
            labels = atom.fetch_labels()
            site = (labels.chain_id.strip() or '_') + ':' + labels.resseq.strip()
            if site not in self.names or atom.element.strip().upper() in {'H', 'D'}:
                continue
            site, identity = _identity(atom)
            _need(int(atom.i_seq) == index and all(abs(a-b) <= 1e-9 for a,b in zip(atom.xyz,coordinates[index])),
                  'Selected hierarchy/manager coordinates or indices disagree')
            selected.append(dict(i_seq=index, atom_id=atom.name.strip(), label=atom.id_str(),
                identity=identity, element=atom.element.strip().upper(), xyz=list(coordinates[index]),
                occupancy=float(atom.occ)))
            by_index[index] = site
        rows = []
        for summary in model._all_monomer_mappings or []:
            associated = list(summary.expected_atoms) + list(summary.unexpected_atoms)
            if not associated:
                continue
            labels = associated[0].fetch_labels()
            site = (labels.chain_id.strip() or '_') + ':' + labels.resseq.strip()
            if site not in self.names:
                continue
            retained = self.mappings.get(id(summary))
            _need(retained is not None and retained[0] is summary,
                  'Final native summary lacks its exact observed definition: ' + site)
            monomer = retained[1].monomer
            rows.append(dict(site=site, metadata=dict(effective_definition=dict(bonds=[
                {key: _plain(getattr(bond, key, None)) for key in _BOND_FIELDS}
                for bond in monomer.bond_list]))))
        _need(sorted(r['site'] for r in rows) == sorted(self.names),
              'Final native definition coverage differs from selected sites')
        pairs = geometry.pair_proxies(sites_cart=model.get_sites_cart())
        bonds = pairs.bond_proxies
        groups = {'bond_simple': bonds.simple}
        groups.update({kind:getattr(geometry, kind + '_proxies') for kind in _KINDS if kind != 'bond_simple'})
        details = {}; counts = {}
        def included(indices):
            return bool(indices) and all(i in by_index for i in indices) and len({by_index[i] for i in indices}) == 1
        def endpoints(indices):
            return dict(i_seqs=indices, atoms=[atoms[i].id_str() for i in indices])
        for kind, proxies in groups.items():
            counts[kind] = 0 if proxies is None else len(proxies)
            kept = []
            for proxy in proxies or []:
                indices = [int(i) for i in proxy.i_seqs]
                others = [int(i) for i in getattr(proxy, 'j_seqs', [])]
                if not included(indices + others):
                    continue
                row = endpoints(indices)
                row.update({key:_plain(getattr(proxy,key,None)) for key in _KINDS[kind]})
                if kind == 'bond_simple':
                    operator = getattr(proxy, 'rt_mx_ji', None)
                    row['symmetry_operation'] = None if operator is None else str(operator)
                if kind == 'parallelity':
                    row.update(j_seqs=others, j_atoms=[atoms[i].id_str() for i in others])
                kept.append(row)
            details[kind] = kept
        details['bond_asu'] = []; counts['bond_asu'] = len(bonds.asu)
        for proxy in bonds.asu:
            indices = [int(proxy.i_seq), int(proxy.j_seq)]
            if included(indices):
                details['bond_asu'].append(dict(endpoints(indices), j_sym=int(proxy.j_sym),
                    distance_ideal=float(proxy.distance_ideal), weight=float(proxy.weight)))
        _need(model.get_hierarchy() is hierarchy and model.restraints_manager.geometry is geometry
              and _digest(_hierarchy(model)) == state, 'Observation changed native model or geometry owner')
        result = dict(policy_id=POLICY_ID, status='OBSERVED', sites=[dict(row) for row in self.sites],
            scope='ACTUAL_NATIVE_MANAGER_INTRA_SITE_HEAVY_ATOMS',
            coordinate_precision='FULL_NATIVE', model_state_sha256=state, full_atom_count=len(atoms),
            atoms=selected, monomer_mappings=dict(rows=rows),
            geometry=dict(proxy_details=details, full_proxy_counts=counts),
            definition_binding='EXACT_OBSERVED_SUMMARY_OBJECT', scientific_approval='NOT_RUN')
        validate_snapshot(result,self.sites,[atom.id_str() for atom in atoms],model_state=state)
        return result


@contextmanager
def observe_monomers(mapping_class, sites):
    """Observe original summary creation; restore only this owner's binding."""
    observer = _Observer(sites)
    original = mapping_class.summary
    def observed(mapping):
        result = original(mapping)
        observer.retain(mapping, result)
        return result
    mapping_class.summary = observed
    try:
        yield observer
        _need(mapping_class.summary is observed, 'Native summary binding changed during observation')
    finally:
        if mapping_class.summary is observed:
            mapping_class.summary = original


def validate_phase_observation(record, sites, *, dry_run, labels):
    """Bind optional observations to the existing final-export state record."""
    validate_sites(sites)
    _need(record.get('chemistry_binding_restored') is True, 'Native summary binding was not restored')
    observation = record.get('chemistry_observation')
    written = record.get('chemistry_model')
    if not sites:
        _need(observation is None and written is None, 'Unrequested chemistry observation')
        return None
    state = None if dry_run else record['output_synchronization'][0]['hierarchy_after_sha256']
    validate_snapshot(observation, sites, labels, model_state=state)
    if dry_run or observation['status'] == 'UNASSESSED':
        _need(written is None, 'Unavailable observation cannot claim a written model')
    else:
        _need(isinstance(written,dict) and set(written) == {'sha256','size'}
              and isinstance(written['sha256'],str) and re.fullmatch('[0-9a-f]{64}',written['sha256'])
              and type(written['size']) is int and written['size'] > 0,
              'Selected observation lacks its written model identity')
    return observation


def validate_snapshot(record, sites, labels, *, model_state=None):
    """Validate compact captured membership against the recorded full atom labels."""
    validate_sites(sites)
    _need(isinstance(record, dict) and record.get('policy_id') == POLICY_ID
          and record.get('sites') == sites and record.get('scientific_approval') == 'NOT_RUN',
          'Selected observation policy or requested scope differs')
    if record.get('status') == 'UNASSESSED':
        _need(set(record) == {'policy_id','status','sites','reason','scientific_approval'}
              and isinstance(record['reason'], str) and bool(record['reason']),
              'Malformed unavailable selected observation')
        return record
    fields = {'policy_id','status','sites','scope','coordinate_precision','model_state_sha256',
              'full_atom_count','atoms','monomer_mappings','geometry','definition_binding','scientific_approval'}
    _need(set(record) == fields and record['status'] == 'OBSERVED'
          and record['scope'] == 'ACTUAL_NATIVE_MANAGER_INTRA_SITE_HEAVY_ATOMS'
          and record['coordinate_precision'] == 'FULL_NATIVE'
          and record['definition_binding'] == 'EXACT_OBSERVED_SUMMARY_OBJECT'
          and isinstance(labels,list) and len(set(labels)) == len(labels)
          and all(isinstance(v,str) and v for v in labels)
          and type(record['full_atom_count']) is int and record['full_atom_count'] == len(labels)
          and isinstance(record['model_state_sha256'],str)
          and re.fullmatch('[0-9a-f]{64}',record['model_state_sha256']),
          'Malformed compact selected observation')
    if model_state is not None:
        _need(record['model_state_sha256'] == model_state, 'Selected observation differs from exported native state')
    names = {row['site'] for row in sites}; indices = {}; identities = set()
    _need(isinstance(record['atoms'],list), 'Missing selected atoms')
    for atom in record['atoms']:
        _need(isinstance(atom,dict) and set(atom) == {'i_seq','atom_id','label','identity','element','xyz','occupancy'},
              'Malformed selected atom')
        i = atom['i_seq']; identity = atom['identity']
        _need(type(i) is int and 0 <= i < len(labels) and i not in indices and atom['label'] == labels[i]
              and isinstance(identity,dict) and set(identity) == {'model_id','chain_id','resseq','icode','resname','altloc'}
              and all(isinstance(v,str) for v in identity.values())
              and not any(identity[k].strip() for k in ('model_id','icode','altloc')),
              'Selected atom identity/index differs')
        site = (identity['chain_id'].strip() or '_') + ':' + identity['resseq'].strip()
        key = (site,atom['atom_id'])
        _need(site in names and isinstance(atom['atom_id'],str) and atom['atom_id'] and key not in identities
              and isinstance(atom['element'],str) and atom['element'] and atom['element'] not in {'H','D'}
              and isinstance(atom['xyz'],list) and len(atom['xyz']) == 3
              and all(type(v) in (int,float) and math.isfinite(v) for v in [*atom['xyz'],atom['occupancy']]),
              'Selected heavy-atom inventory or coordinates differ')
        indices[i] = site; identities.add(key)
    _need([a['i_seq'] for a in record['atoms']] == sorted(indices), 'Selected atom order differs')
    mappings = record['monomer_mappings']
    _need(isinstance(mappings,dict) and set(mappings) == {'rows'} and isinstance(mappings['rows'],list),
          'Missing selected definitions')
    for row in mappings['rows']:
        _need(isinstance(row,dict) and set(row) == {'site','metadata'}
              and isinstance(row['metadata'],dict) and set(row['metadata']) == {'effective_definition'}
              and isinstance(row['metadata']['effective_definition'],dict)
              and set(row['metadata']['effective_definition']) == {'bonds'}, 'Malformed selected definition')
        bonds = row['metadata']['effective_definition']['bonds']
        _need(isinstance(bonds,list) and all(isinstance(b,dict) and set(b) == set(_BOND_FIELDS)
              and all(isinstance(b[k],str) and b[k] for k in ('atom_id_1','atom_id_2')) for b in bonds),
              'Malformed observed bond definition')
    _need(sorted(r['site'] for r in mappings['rows']) == sorted(names), 'Selected definition coverage differs')
    geometry = record['geometry']
    _need(isinstance(geometry,dict) and set(geometry) == {'proxy_details','full_proxy_counts'}, 'Malformed selected geometry')
    details, counts = geometry['proxy_details'], geometry['full_proxy_counts']
    _need(isinstance(details,dict) and isinstance(counts,dict) and set(details) == set(counts) == set(_KINDS)|{'bond_asu'},
          'Selected proxy categories differ')
    sizes = {'bond_simple':2,'bond_asu':2,'angle':3,'dihedral':4,'const_dihedral':4,'chirality':4}
    for kind, rows in details.items():
        _need(isinstance(rows,list) and type(counts[kind]) is int and counts[kind] >= len(rows), 'Selected proxy counts differ')
        for row in rows:
            _need(isinstance(row,dict) and isinstance(row.get('i_seqs'),list) and isinstance(row.get('atoms'),list),
                  'Malformed selected proxy')
            ids = row['i_seqs']; others = row.get('j_seqs',[])
            _need(isinstance(others,list) and ids and all(type(i) is int and i in indices for i in ids+others)
                  and len({indices[i] for i in ids+others}) == 1
                  and row['atoms'] == [labels[i] for i in ids]
                  and (kind not in sizes or len(ids) == sizes[kind]), 'Selected proxy endpoint identity differs')
            expected = {'i_seqs','atoms'} | (set(_KINDS[kind]) if kind in _KINDS else {'j_sym','distance_ideal','weight'})
            if kind == 'parallelity':
                expected |= {'j_seqs','j_atoms'}
                _need(others and row.get('j_atoms') == [labels[i] for i in others], 'Selected parallelity endpoints differ')
            if kind == 'bond_simple':
                expected.add('symmetry_operation')
            _need(set(row) == expected, 'Selected proxy fields differ')
    _digest(record)
    return record
