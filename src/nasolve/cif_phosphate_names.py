"""Explicit source-owned phosphate names; no atom renaming or chemistry inference."""
POLICY_ID = 'cif-source-phosphate-aliases-v1'


def phosphate_names(values, *, leaving_required=True):
    from .cif_linked_preparation import atom_rows
    atoms = atom_rows(values)
    bonds = {frozenset((a,b)) for a,b in zip(values.get('_chem_comp_bond.atom_id_1', []),
        values.get('_chem_comp_bond.atom_id_2', []))}
    if atoms.get('P', {}).get('type_symbol', '').upper() != 'P':
        raise ValueError('Missing source phosphorus')
    result = {}
    for role, alternatives in [('OP1', {'OP1','O1P'}), ('OP2', {'OP2','O2P'}), ('OP3', {'OP3','O3P'})]:
        found = alternatives & atoms.keys()
        if not found and role == 'OP3' and not leaving_required: continue
        if len(found) != 1: raise ValueError('Missing or ambiguous source phosphate name: '+role)
        name = found.pop()
        heavy = {next(iter(pair-{name})) for pair in bonds if name in pair
            and len(pair) == 2 and atoms.get(next(iter(pair-{name})), {}).get('type_symbol', '').upper() not in {'H','D'}}
        if atoms[name].get('type_symbol', '').upper() != 'O' or heavy != {'P'}:
            raise ValueError('Source phosphate alias is not a terminal P-bound oxygen: '+name)
        result[role] = name
    return result
