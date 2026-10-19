"""Source-graph and NARestraints role controls without a crystallographic model.

Synthetic partner roles exercise the recipe compiler only. They do not infer
experimental pairing or establish native/achieved geometry qualification.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from .cif_doctor import assess_dictionaries, _ORDERS
from .cif_linked_preparation import component_values, atom_rows, hydrogen_neighbors

POLICY_ID = 'cif-explicit-component-policy-control-v1'


def assess_component_control(source, code, *, records=None):
    from restraints.residue_library import load_residue_records, heterocycle_atom_names
    from restraints.builder import pair_residue_from_pdb
    from restraints.phenix import PairResidue, generate_pair_restraints
    from restraints.recipe_library import recipe_for
    from restraints.stacking import _manual_parallelity, _PLANE_ATOMS_BY_BASE_CLASS
    from .cif_na_policy import _requests
    source = Path(source).resolve(strict=True);original = source.read_bytes()
    assessment = assess_dictionaries([source], stage='component-control-source')
    selected = [c for c in assessment['components'] if c['component_id'] == code]
    if len(selected) != 1 or len(assessment['components']) != 1 or selected[0]['verdicts']['graph'] != 'PASS':
        raise ValueError('Require one exact graph-valid component control')
    records = load_residue_records() if records is None else records
    matches = [r for r in records if r['Ligand code'] == code]
    if len(matches) != 1:
        raise ValueError('Component control requires one unambiguous NARestraints record')
    record = matches[0];values = component_values(source, code);atoms = atom_rows(values)
    inventory = selected[0]['inventory'];known = heterocycle_atom_names(record)
    missing = sorted({str(v).strip() for v in known if str(v).strip() not in atoms})
    # Exercise the library's actual mapping function with identities only.
    # No zero-filled or experimental coordinates enter this compiler control.
    identity = SimpleNamespace(get_resname=lambda: code, has_id=lambda name: name in atoms,
        id=('', 1, ''), get_parent=lambda: SimpleNamespace(get_id=lambda: 'A'))
    mapped = pair_residue_from_pdb([record], identity)
    names = dict(mapped.atoms)
    bonds = inventory['bond_orders']
    attached = [r for r in bonds if "C1'" in r['atoms'] and any(a not in {"C1'", "C2'", "O4'"} and atoms[a]['type_symbol'].upper() not in {'H','D'} for a in r['atoms'])]
    attachment = None
    if len(attached) == 1:
        edge = attached[0];other = next(a for a in edge['atoms'] if a != "C1'")
        orders = {_ORDERS.get(v.upper(), v.upper()) for v in edge['declarations'].values()}
        attachment = {'sugar_atom': "C1'", 'base_atom': other, 'order': next(iter(orders)) if len(orders) == 1 else 'AMBIGUOUS'}
    report = {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW', 'component': code,
        'source_sha256': sha256(original).hexdigest(), 'source_size': len(original),
        'graph_status': selected[0]['verdicts']['graph'], 'source_assessment': assessment,
        'atom_count': inventory['atom_count'], 'heavy_atom_count': inventory['heavy_atom_count'], 'bond_count': inventory['bond_count'],
        'declared_type': values.get('_chem_comp.type', values.get('_chem_comp.group', ['?']))[0],
        'declared_formal_charge': values.get('_chem_comp.pdbx_formal_charge', ['?'])[0],
        'atom_stereo': {a['atom_id']: next(iter(a['stereo_declarations'].values())) for a in inventory['atoms']
                        if a['stereo_declarations'] and set(a['stereo_declarations'].values()) not in ({'N'}, {'?'}, {'.'})},
        'triple_bonds': sorted(sorted(r['atoms']) for r in bonds if {_ORDERS.get(v.upper(), v.upper()) for v in r['declarations'].values()} == {'TRIPLE'}),
        'glycosidic_attachment': attachment, 'outgoing_oxygen_hydrogens': hydrogen_neighbors(values, "O3'"),
        'policy_authority': 'NARestraints', 'mapped_base_class': mapped.base_class, 'named_mappings': names,
        'source_sheet': record['Source sheet'], 'missing_mapped_atoms': missing, 'policy_status': 'REVIEW', 'policy_controls': {},
        'native_proxy_validation': 'NOT_RUN', 'model_editing': 'NOT_RUN', 'model_optimization': 'NOT_RUN', 'automatic_adoption': False,
        'limitations': ['Role-template partner controls are compiler checks, not observed pairs, native proxies or achieved geometry.',
            'Source graph/ideal-coordinate consistency is not a complete numerical dictionary or chemical qualification.',
            'This control does not insert a residue into the frozen scaffold or choose a protonation/tautomer state.']}
    if missing:
        return report
    candidates = [(base, recipe_for(mapped.base_class, base)) for base in _PLANE_ATOMS_BY_BASE_CLASS]
    partners = [(base, recipe) for base, recipe in candidates if recipe is not None and not recipe.noncanonical]
    if not partners:
        report['policy_status'] = 'UNSUPPORTED';return report
    base, recipe = partners[0]
    partner = PairResidue('B', '1', {a: a for a in _PLANE_ATOMS_BY_BASE_CLASS[base]}, base)
    native_atoms = []
    for chain, labels in [('A', list(atoms)), ('B', list(partner.atoms))]:
        for name in labels:
            native_atoms.append({'i_seq': len(native_atoms), 'atom_id': name, 'label': f'CONTROL:{chain}:1:{name}',
                                 'identity': {'chain_id': chain, 'resseq': '1'}})
    def wrap(body):
        return 'refinement {\n geometry_restraints {\n edits {\n'+body+'\n }\n }\n}\n'
    try:
        pair = generate_pair_restraints(mapped, partner, parallels=True, planes=False)
        if pair is None:
            raise ValueError('Configured pair could not compile')
        requests = _requests(wrap(pair), native_atoms)
        stack_text = [_manual_parallelity(mapped, partner), _manual_parallelity(partner, mapped)]
        stacks = [_requests(wrap(text), native_atoms)[0] for text in stack_text]
        groups = {kind: [r for r in requests if r['kind'] == kind] for kind in ['bond', 'angle', 'parallelity']}
        actual = {a['i_seq']: a for a in native_atoms}
        report['policy_controls'] = {'scope': 'SYNTHETIC_PARTNER_ROLES_COMPILER_ONLY', 'partner_class': base,
            'pair_recipe': recipe.name, 'pair_requests': groups,
            'pair_contact_atoms': [[actual[i]['atom_id'] for i in r['i_seqs']] for r in groups['bond']],
            'stack_requests': stacks, 'component_stack_plane_atoms': [actual[i]['atom_id'] for i in stacks[0]['i_seqs']],
            'pair_phil': wrap(pair), 'stack_phils': [wrap(text) for text in stack_text]}
        report['policy_status'] = 'PASS'
    except ValueError as exc:
        report['policy_error'] = str(exc)
    if source.read_bytes() != original:
        raise ValueError('Component control source changed')
    return report
