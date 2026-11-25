"""Exact source-bound selection text for the explicit XYZ/group-B writer.

This is serialization, not native binding or execution admission. The caller
must bind the scope to the initialized native model and observe compiled flags
and actual optimizers. Source/phase/restraint ownership stays with that caller.
"""
from dataclasses import dataclass
from hashlib import sha256
import math

from .refinement_parameter_scope import ParameterScope, scope_digest


@dataclass(frozen=True)
class ParameterSelectionText:
    xyz: str
    groups: tuple[str, ...]
    real_space: bool
    scope_sha256: str
    source_sha256: str


def selection_text(scope: ParameterScope, source: bytes) -> ParameterSelectionText:
    """Reuse the existing single-model PDB reader and exact native selector.

    Coordinates/B/Q must match the recorded initialization; native identity,
    scattering, effective selections and execution still require bind_scope and
    the read-only native observer. No paths are discovered or files modified.
    """
    from .metal.context import parse_pdb
    from .metal.export import atom_selection

    if not isinstance(scope, ParameterScope) or type(source) is not bytes:
        raise ValueError('Require a ParameterScope and exact source PDB bytes')
    packet = scope.record()
    if sha256(source).hexdigest() != packet['source_model_sha256']:
        raise ValueError('Parameter-scope source checksum mismatch')
    parsed = parse_pdb(source)
    atoms = parsed.snapshot.atoms
    state = parsed.to_dict()['atomic_state']
    if len(atoms) != len(packet['initial_atoms']):
        raise ValueError('Parameter-scope source atomic inventory differs')
    for atom, source_state, initial in zip(atoms, state, packet['initial_atoms']):
        if source_state['anisou'] is not None:
            raise ValueError('Parameter scope requires an all-isotropic source')
        if (math.dist(atom.xyz, initial['xyz']) > 1e-7
                or abs(source_state['b_iso'] - initial['B']) > 1e-7
                or abs(source_state['occupancy'] - initial['Q']) > 1e-12):
            raise ValueError('Parameter-scope source XYZ/B/Q differs from initialization')
    selectors = [atom_selection(atom.key) for atom in atoms]
    # Native selection normalizes case. Refuse ambiguous identities even if the
    # Python PDB reader can distinguish them; never broaden a protected mask.
    if len({s.casefold() for s in selectors}) != len(selectors):
        raise ValueError('Native selection is ambiguous after case normalization')

    def union(indices):
        return ' or '.join('(' + selectors[i] + ')' for i in indices)

    return ParameterSelectionText(union(packet['xyz_indices']),
        tuple(union(group) for group in packet['adp_groups']), packet['real_space'],
        scope_digest(packet), packet['source_model_sha256'])
