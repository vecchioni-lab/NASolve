"""Report hydrogen attachment/count differences without assigning protonation."""
from collections import Counter

POLICY_ID = 'cif-native-bound-hydrogen-inventory-v1'
_HYDROGEN = {'H', 'D', 'T'}


def compare_hydrogen_inventory(source, source_bonds, native, observed_names):
    """Compare retained source and effective inventories through observed heavy atoms.

    Equal counts with different H labels are observations, not inferred aliases.
    Charge, bond order, stereochemistry and permission to change state are outside
    this inventory. All heavy atoms must be bound before a comparison is claimed.
    """
    result = {'policy_id': POLICY_ID, 'status': 'UNSUPPORTED',
              'inventory_status': 'NOT_ASSESSED', 'name_status': 'NOT_ASSESSED',
              'groups': [], 'same_name_attachment_changes': [], 'limitations': [],
              'chemical_authority': 'NOT_GRANTED', 'hydrogen_aliases_inferred': False}
    atoms = native.get('atoms')
    bonds = native.get('bonds')
    if not isinstance(atoms, list) or not isinstance(bonds, list):
        result['limitations'].append('Native atom/bond inventory is unavailable.')
        return result
    target = {a['atom_id']: a['type_symbol'].strip().upper() for a in atoms}
    if len(target) != len(atoms):
        raise ValueError('Duplicate native atom in hydrogen inventory')
    source = {a: e.strip().upper() for a, e in source.items()}
    names = {a: observed_names.get(a, a) for a in source}
    if len(set(names.values())) != len(names):
        raise ValueError('Observed names collapse source hydrogen inventory')
    heavy = {a for a, e in source.items() if e not in _HYDROGEN}
    bound = {a: observed_names[a] for a in heavy if a in observed_names
             and observed_names[a] in target and target[observed_names[a]] == source[a]}
    missing_source = sorted(heavy - bound.keys())
    missing_native = sorted({a for a,e in target.items() if e not in _HYDROGEN} - set(bound.values()))
    result['unbound_source_heavy_atoms'] = missing_source
    result['unbound_native_heavy_atoms'] = missing_native
    if missing_source or missing_native:
        result['limitations'].append('Heavy-atom bindings do not cover both complete inventories.')
        return result

    def attachments(elements, edges, label):
        adjacency = {a: [] for a in elements}
        seen = set()
        for a, b in edges:
            pair = tuple(sorted((a, b)))
            if a == b or a not in elements or b not in elements or pair in seen:
                result['limitations'].append(label + ' bond inventory is ambiguous or inconsistent.')
                return None
            seen.add(pair); adjacency[a].append(b); adjacency[b].append(a)
        parents = {}
        for a, e in elements.items():
            if e not in _HYDROGEN:
                continue
            neighbors = adjacency[a]
            if len(neighbors) != 1 or elements[neighbors[0]] in _HYDROGEN:
                result['limitations'].append(label + ' hydrogen ' + a + ' lacks one unambiguous heavy-atom parent.')
                return None
            parents[a] = neighbors[0]
        return parents

    source_parent = attachments(source, source_bonds, 'Source')
    native_parent = attachments(target, [(b['atom_id_1'], b['atom_id_2']) for b in bonds], 'Native')
    if source_parent is None or native_parent is None:
        return result
    count_differences = name_differences = False
    for a, b in sorted(bound.items()):
        source_h = sorted(h for h, parent in source_parent.items() if parent == a)
        native_h = sorted(h for h, parent in native_parent.items() if parent == b)
        if not source_h and not native_h:
            continue
        left, right = Counter(source[h] for h in source_h), Counter(target[h] for h in native_h)
        counts_match = left == right
        names_match = sorted(names[h] for h in source_h) == native_h
        count_differences |= not counts_match
        name_differences |= not names_match
        result['groups'].append({'source_heavy_atom': a, 'native_heavy_atom': b,
            'source_hydrogens': source_h, 'native_hydrogens': native_h,
            'source_isotope_counts': dict(sorted(left.items())), 'native_isotope_counts': dict(sorted(right.items())),
            'count_status': 'MATCH' if counts_match else 'DIFFERENT',
            'name_status': 'MATCH' if names_match else 'DIFFERENT'})
    for h, parent in sorted(source_parent.items()):
        native_h = names[h]
        if native_h in native_parent and bound[parent] != native_parent[native_h]:
            result['same_name_attachment_changes'].append({'source_hydrogen': h, 'native_hydrogen': native_h,
                'source_parent_in_native_names': bound[parent], 'native_parent': native_parent[native_h]})
    result.update(status='RECORDED',
        inventory_status='DIFFERENT' if count_differences or result['same_name_attachment_changes'] else 'MATCH',
        name_status='DIFFERENT' if name_differences else 'MATCH')
    result['limitations'].append('Equal hydrogen counts do not establish protonation, formal charge, stereochemistry or individual hydrogen-name equivalence.')
    return result
