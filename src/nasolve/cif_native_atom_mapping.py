"""Capture native name bindings without treating aliases as chemical authority."""
from inspect import getsource

POLICY_ID = 'cif-native-observed-atom-name-mapping-v1'


def capture_atom_name_mapping(mm):
    """Runs inside the isolated native worker, using the actual mapping object."""
    fields = ('expected_atoms', 'unexpected_atoms', 'duplicate_atoms',
              'atom_names_mappings', 'active_atoms', 'mon_lib_names')
    missing = [name for name in fields if not hasattr(mm, name)]
    if missing:
        return {'status': 'UNSUPPORTED', 'missing_fields': missing}
    names = mm.mon_lib_names
    if names is not None and len(names) != len(mm.active_atoms):
        raise ValueError('Native mon_lib_names and active atoms disagree')
    def binding(name, atom):
        return {'dictionary_atom_id': name, 'model_i_seq': int(atom.i_seq),
                'model_atom_id': atom.name.strip()}
    return {
        'status': 'RECORDED', 'aliases': dict(mm.atom_names_mappings),
        'mon_lib_names_available': names is not None,
        'active': [{'model_i_seq': int(a.i_seq), 'model_atom_id': a.name.strip(),
                    'mon_lib_name': names[i] if names is not None else None}
                   for i, a in enumerate(mm.active_atoms)],
        'expected': [binding(k, a) for k, a in sorted(mm.expected_atoms.items())],
        'unexpected': [binding(k, a) for k, a in sorted(mm.unexpected_atoms.items())],
        'duplicates': [binding(k, a) for k, atoms in sorted(mm.duplicate_atoms.items()) for a in atoms],
    }


def native_mapping_worker(base):
    """Opt-in extension: the historical base-worker bytes remain unchanged."""
    header = 'try:\n    from iotbx import phil\n'
    row = '            rows.append(entry)\n'
    if base.count(header) != 1 or base.count(row) != 1:
        raise ValueError('Unsupported base native worker for atom mapping')
    extended = base.replace(header, getsource(capture_atom_name_mapping) + '\n'
                            + 'report["atom_name_mapping_policy"] = ' + repr(POLICY_ID) + '\n\n' + header)
    return extended.replace(row, '            entry["atom_name_mapping"] = capture_atom_name_mapping(mm)\n' + row)


def bound_name_mappings(native, keys):
    """Validate every reported index/name against the bound model and definition.

    Intermediate mon_lib_names may differ from final expected_atoms. They are
    preserved observations, never a substitute for the final index binding.
    """
    if native.get('atom_name_mapping_policy') != POLICY_ID:
        raise ValueError('Missing native atom mapping policy')
    rows = native.get('monomer_mappings', {}).get('rows', [])
    maps, unsupported, seen, summary = {}, [], set(), []
    for row in rows:
        site, code = row['site'], row['resname']
        if site in seen:
            raise ValueError('Duplicate native atom mapping site')
        seen.add(site)
        m = row.get('atom_name_mapping', {})
        if m.get('status') == 'UNSUPPORTED':
            if not isinstance(m.get('missing_fields'), list) or not m['missing_fields']:
                raise ValueError('Unsupported mapping must name unavailable fields')
            unsupported.append({'site': site, 'missing_fields': m['missing_fields']})
            continue
        if m.get('status') != 'RECORDED' or type(m.get('mon_lib_names_available')) is not bool:
            raise ValueError('Incomplete native atom name mapping')
        actual = {i for i, key in enumerate(keys) if key[:2] == (site, code)}
        if not actual:
            raise ValueError('Native mapping site not present in the model')
        def index(item):
            i = item['model_i_seq']
            if (type(i) is not int or i not in actual or item['model_atom_id'] != keys[i][2]):
                raise ValueError('Native mapping atom identity/index disagreement')
            return i
        active = m['active']
        ids = [index(a) for a in active]
        if len(set(ids)) != len(ids) or set(ids) != actual:
            raise ValueError('Native active mapping does not cover the exact model site')
        for a in active:
            name = a['mon_lib_name']
            if name is not None and (not m['mon_lib_names_available'] or not isinstance(name, str) or not name):
                raise ValueError('Invalid native monomer-library name observation')
        if m['duplicates']:
            raise ValueError('Duplicate native atom bindings cannot be reconciled')
        aliases = m['aliases']
        if (not isinstance(aliases, dict) or set(aliases) - {keys[i][2] for i in actual}
                or any(not isinstance(k,str) or not isinstance(v,str) or not k or not v or k == v for k,v in aliases.items())):
            raise ValueError('Native aliases must identify distinct bound atom names')
        definition = row['metadata']['effective_definition']['atoms']
        atoms = {a['atom_id']: a for a in definition}
        if len(atoms) != len(definition):
            raise ValueError('Duplicate effective atom definition')
        bound, used_indices, used_names = {}, set(), set()
        for category in ('expected', 'unexpected'):
            for item in m[category]:
                i = index(item); name = item['dictionary_atom_id']; literal = item['model_atom_id']
                if (not isinstance(name, str) or not name or i in used_indices or name in used_names
                        or aliases.get(literal,literal) != name):
                    raise ValueError('Ambiguous or contradictory native alias binding')
                used_indices.add(i); used_names.add(name)
                if (name in atoms) != (category == 'expected'):
                    raise ValueError('Native expected/unexpected definition disagreement')
                if category == 'expected':
                    if atoms[name]['type_symbol'].strip().upper() != native['atoms'][i]['element'].strip().upper():
                        raise ValueError('Native alias changes the model element')
                    bound[literal] = name
        if used_indices != actual:
            raise ValueError('Native final bindings omit model atoms')
        maps[site] = bound
        summary.append({'site':site, 'component':code, 'bound_atom_count':len(bound),
                        'aliases':{k:v for k,v in bound.items() if k != v},
                        'unexpected_count':len(m['unexpected']),
                        'mon_lib_names_available':m['mon_lib_names_available']})
    if seen != {k[0] for k in keys}:
        raise ValueError('Native atom mappings omit or add model sites')
    return {'policy_id':POLICY_ID, 'status':'UNSUPPORTED' if unsupported else 'RECORDED',
            'alias_count':sum(len(row['aliases']) for row in summary), 'sites':summary,
            'unsupported':unsupported, 'chemical_authority':'NOT_GRANTED'}, maps
