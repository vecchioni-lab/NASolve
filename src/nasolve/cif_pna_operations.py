"""Bounded neutral PNA amide source projections; no protonation inference."""
from __future__ import annotations

POLICY_ID = 'neutral-pna-amide-v1'
PROFILE_ID = 'uncapped-aminoethylglycine-pna-core-v1'


def plan_amide_deletion(port, intent, profile, elements, bonds, charges, neighbors):
    """Return exact deletions, or None when explicit source state is unsupported.

    The source graph owns the atoms/state; the caller selects an exact leaving
    atom under this named policy. No dictionary, coordinate or charge is edited.
    A reciprocal partner contract and native/numerical checks remain separate.
    """
    if intent['operation'] != POLICY_ID or profile['matched_profile'] != PROFILE_ID:
        raise ValueError('Unsupported PNA chemical-state operation or source profile')
    binding = profile['bindings']
    leaving = intent['leaving_atom']
    if not isinstance(leaving, str):
        raise ValueError('Require an exact PNA leaving-atom identity')
    atom = profile['ports'][port]['atom_id']

    def single_hydrogens(parent, count):
        hydrogens = {a for a in neighbors[parent] if elements[a] in {'H', 'D'}}
        if (len(hydrogens) != count
                or any(charges[h] != 0 or neighbors[h] != {parent}
                       or bonds[tuple(sorted((h, parent)))] != 'SINGLE' for h in hydrogens)):
            return None
        return hydrogens

    if port == 'amine':
        if elements.get(leaving) not in {'H', 'D'} or leaving not in neighbors[atom]:
            raise ValueError('Chosen PNA amine leaving atom is not a source-bound H/D')
        hydrogens = single_hydrogens(atom, 2)
        if (charges[atom] != 0 or hydrogens is None
                or neighbors[atom] != {binding['amino_c']} | hydrogens):
            return None
        removed = {leaving}
    elif port == 'carboxyl':
        if leaving != binding['acid_o']:
            raise ValueError('Chosen PNA carboxyl leaving atom is not the source hydroxyl oxygen')
        oxygen = binding['carboxyl_o']
        hydrogens = single_hydrogens(leaving, 1)
        if (any(charges[a] != 0 for a in (atom, leaving, oxygen))
                or hydrogens is None or neighbors[leaving] != {atom} | hydrogens
                or neighbors[oxygen] != {atom}
                or neighbors[atom] != {binding['glycine_c'], oxygen, leaving}):
            return None
        removed = {leaving} | hydrogens
    else:
        raise ValueError('PNA amide operation requires an amine or carboxyl port')
    return removed
