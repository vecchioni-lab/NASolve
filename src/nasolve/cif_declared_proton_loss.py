"""Explicit imide proton-loss source derivation, never inferred metal chemistry.

Return a separately named chemical source and its delta, without writing files,
assigning numerical restraints or activating a mutation. The caller owns intent,
site binding and preservation of the original source. Native generation and
linked metal-state qualification remain separate gates.
"""
from collections import Counter
from hashlib import sha256
from math import isfinite
from pathlib import Path
import re

from .cif_attachment_sites import _projection_values
from .cif_linked_preparation import _prune
from .cif_reference_composition import _flag
from .cif_stereochemistry_audit import _values, _graph, _stereo
from .ligand_profiles import _emit

POLICY_ID = 'cif-declared-imide-proton-loss-v1'
_A, _B = '_chem_comp_atom.', '_chem_comp_bond.'


def _imide(values, donor, hydrogen, elements, bonds, charges, neighbors):
    """Bounded neutral N(H) between two C(=O/S) groups, by graph only."""
    def order(a, b):
        return bonds.get(tuple(sorted((a, b))))

    if (elements.get(donor) != 'N' or elements.get(hydrogen) not in {'H', 'D'}
            or charges[donor] != 0 or charges[hydrogen] != 0
            or neighbors[hydrogen] != {donor} or len(neighbors[donor]) != 3
            or order(donor, hydrogen) != 'SINGLE'):
        raise ValueError('Require an explicitly selected neutral imide N-H/D source bond')
    carbons = neighbors[donor] - {hydrogen}
    if len(carbons) != 2 or any(elements[c] != 'C' or charges[c] != 0
                              or order(donor, c) != 'SINGLE' for c in carbons):
        raise ValueError('Require two neutral carbonyl/thione carbon neighbors')
    reactive = {donor, hydrogen} | carbons
    attachments = []
    for carbon in sorted(carbons):
        ends = [n for n in neighbors[carbon] if elements[n] in {'O', 'S'} and order(carbon, n) == 'DOUBLE']
        if len(ends) != 1 or len(neighbors[carbon]) != 3:
            raise ValueError('Require explicit imide carbonyl/thione valence')
        end = ends[0]
        other = neighbors[carbon] - {donor, end}
        if (charges[end] != 0 or neighbors[end] != {carbon} or len(other) != 1
                or any(elements[n] in {'H', 'D'} or order(carbon, n) != 'SINGLE' for n in other)):
            raise ValueError('Unsupported carbonyl/thione neighborhood')
        reactive.add(end)
        attachments.append(dict(carbon=carbon, terminal=end, element=elements[end]))
    stereo = _stereo(values)
    ids = values[_A+'atom_id']
    for atom in reactive:
        i = ids.index(atom)
        if (stereo[atom] != 'N'
                or _flag(values, _A, ('aromatic', 'pdbx_aromatic_flag'), i, {'Y', 'N'}) != 'N'):
            raise ValueError('Require explicit nonaromatic, unstereogenic reactive atoms')
    for i, pair in enumerate(zip(values[_B+'atom_id_1'], values[_B+'atom_id_2'])):
        if set(pair) & carbons or donor in pair or hydrogen in pair:
            if (_flag(values, _B, ('aromatic', 'pdbx_aromatic_flag'), i, {'Y', 'N'}) != 'N'
                    or _flag(values, _B, ('stereo_config', 'pdbx_stereo_config'), i, {'N'}) not in {'N', '?'}):
                raise ValueError('Unsupported reactive bond representation')
    return attachments


def derive_imide_anion_source(source, code, *, component, donor, hydrogen, operation):
    """Declare loss of one H+/D+ from a graph-qualified neutral imide nitrogen.

    A formal -1 change at the selected N is the localized anion representation,
    not a partial charge or a claim about charge localization in the complex.
    Remote source state, retained coordinates and bond orders are preserved.
    This explicit chemical operation does not infer pH, a metal, tautomerism,
    a coordination bond, native atom types or new restraint targets.
    """
    if operation != POLICY_ID:
        raise ValueError('Require the explicit imide proton-loss policy')
    if (not isinstance(component, str) or not re.fullmatch('[A-Z0-9]{1,3}', component)
            or component == code or not all(isinstance(x, str) and x for x in (donor, hydrogen))):
        raise ValueError('Require exact donor/H identities and a distinct output component')
    source = Path(source)
    if source.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Chemical source exceeds size bound')
    original = source.read_bytes()
    try:
        # Retain the established graph/duplicate checks and single-source boundary.
        original_values = _projection_values(source, code)
        values = _values(source, code)
        allowed = {'_chem_comp', '_chem_comp_atom', '_chem_comp_bond',
                   '_pdbx_chem_comp_descriptor', '_pdbx_chem_comp_identifier',
                   '_pdbx_chem_comp_audit', '_pdbx_chem_comp_pcm'}
        if (any(k.split('.')[0] not in allowed for k in values if k != 'data_')
                or any(k.startswith(_B+'value_dist') or k in {_A+'type_energy', _A+'partial_charge'} for k in values)):
            raise ValueError('Require a chemical source without numerical or unsupported chemistry categories')
        elements, bonds, charges, neighbors = _graph(values)
        if any(q is None or not isfinite(q) or not q.is_integer() or abs(q) > 4 for q in charges.values()):
            raise ValueError('Require complete unambiguous integer source formal charges')
        total = sum(int(q) for q in charges.values())
        declared_total = values.get('_chem_comp.pdbx_formal_charge')
        if declared_total is not None and (len(declared_total) != 1 or declared_total[0] != str(total)):
            raise ValueError('Source total formal charge differs from its atom charges')
        attachments = _imide(values, donor, hydrogen, elements, bonds, charges, neighbors)
        # Do not carry stale neutral SMILES, formula weights, publication identifiers
        # or release status into a different chemical identity.
        retained = {k: v for k, v in original_values.items() if k.startswith((_A, _B))}
        derived = _prune(retained, {hydrogen}, outgoing=False)
        ids = derived[_A+'atom_id']; index = ids.index(donor)
        for field in ('charge', 'pdbx_formal_charge'):
            if _A+field in derived:
                derived[_A+field][index] = '-1'
        for prefix in (_A, _B):
            derived[prefix+'comp_id'] = [component] * len(derived[prefix+'comp_id'])
        counts = Counter(e for n, e in elements.items() if n != hydrogen)
        formula = ' '.join(e + (str(counts[e]) if counts[e] != 1 else '')
                           for e in sorted(counts, key=lambda e: (e not in {'C', 'H'}, e)))
        metadata = {'data_': component, '_chem_comp.id': [component],
                    '_chem_comp.name': [f'Explicit imide proton-loss derivative of {code}'],
                    '_chem_comp.formula': [formula], '_chem_comp.pdbx_formal_charge': [str(total-1)],
                    '_chem_comp.number_atoms_all': [str(len(ids))],
                    '_chem_comp.number_atoms_nh': [str(sum(e not in {'H', 'D'} for n, e in elements.items() if n != hydrogen))]}
        for field in ('type', 'group'):
            if '_chem_comp.'+field in values:
                metadata['_chem_comp.'+field] = list(values['_chem_comp.'+field])
        payload = _emit({**metadata, **derived}).encode()
        report = dict(schema_version=1, policy_id=POLICY_ID, status='DECLARED_SOURCE_REQUIRES_QUALIFICATION',
            component=component, source=dict(component=code, sha256=sha256(original).hexdigest(), size=len(original)),
            donor=donor, removed_atoms=[hydrogen], carbonyl_thione_neighbors=attachments,
            released_species=dict(element=elements[hydrogen], formal_charge=1),
            formal_charge_changes=[dict(atom=donor, before=0, after=-1)], formal_charge_delta=-1,
            source_total_formal_charge=total, output_total_formal_charge=total-1,
            retained_atoms=ids, retained_bond_orders='UNCHANGED',
            retained_coordinates='PARENT_SEED_ONLY', retained_stereo='PARENT_DECLARATIONS_NOT_REASSIGNED',
            parent_only_categories=sorted({k.split('.')[0] for k in values if k.startswith('_pdbx_')}),
            output_sha256=sha256(payload).hexdigest(), output_size=len(payload),
            model_editing='NOT_RUN', metal_link='NOT_ASSIGNED', native_qualification='NOT_RUN',
            restraint_generation='NOT_RUN', linked_state_qualification='NOT_RUN', automatic_adoption=False)
        return payload, report
    finally:
        if source.read_bytes() != original:
            raise ValueError('Proton-loss source changed while reading')
