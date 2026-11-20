"""Explicit metal-contact authority for the shared cross-site topology review.

This is a declaration adapter, not a native capture authenticator or geometry
acceptance gate. Source/capture integrity belongs to its caller. Angles and
nonmetal distances remain available through describe_native_terms; they are not
classified as coordination bonds here.
"""
from hashlib import sha256
import json

from ..cif_attachment_native import _native_atoms
from .binding import AtomKey
from .export import _replay, atom_selection
from .native_terms import describe_native_terms
from .recipe import RecipeError, canonical


def describe_coordination_bonds(preview, native, model_payload, *, edit_origin_id):
    """Project enabled, metal-containing recipe distances onto native identities.

    The complete inventory is bound by the existing native-terms adapter. Exact
    selectors come from the PHIL exporter, never from a distance or element
    guess. The explicit edit origin must come from the caller's authenticated
    native policy; the shared topology checker verifies its captured value.
    """
    try:
        if type(edit_origin_id) is not int or edit_origin_id < 0:
            raise ValueError('Require an explicit native edit origin')
        if (not isinstance(model_payload, bytes)
                or sha256(model_payload).hexdigest() != preview['inputs']['model']['source_sha256']):
            raise ValueError('Model bytes differ from the recipe source')
        _native_atoms(native, model_payload)
        if any(line[72:76].strip() for line in model_payload.decode().splitlines()
               if line[:6] in {'ATOM  ', 'HETATM'}):
            raise ValueError('Segment identities are not available in this native capture')
        atoms = native['atoms']
        inventory = []
        for i, atom in enumerate(atoms):
            key = atom['identity']
            if atom['i_seq'] != i or type(atom['i_seq']) is not int:
                raise ValueError('Native atom order differs from indices')
            inventory.append(dict(identity=dict(chain=key['chain_id'].strip(),
                residue_number=int(key['resseq']), insertion_code=key['icode'].strip(),
                residue_code=key['resname'].strip(), atom_name=atom['atom_id'],
                altloc=key['altloc'].strip()), element=atom['element'],
                model_id=key['model_id'].strip(), segment_id=''))
        declaration = describe_native_terms(preview, inventory)
        indices = {label: i for i, label in enumerate(declaration['atom_labels'])}
        bound = _replay(preview)
        nodes = {n['node_id']: n for n in bound['nodes']}
        roles = {n['id']: n['kind'] for n in bound['inputs']['recipe']['nodes']}
        restraints = {r['restraint_id']: r for r in bound['restraints']}
        result = []
        for term in declaration['requested']:
            row = restraints[term['term_id']]
            kinds = [roles[n] for n in row['node_ids']]
            if term['kind'] != 'bond' or 'metal' not in kinds:
                continue
            ids = [indices[a['atom']] for a in term['atoms']]
            keys = [AtomKey(**nodes[n]['atom']['key']) for n in row['node_ids']]
            result.append(dict(kind='metal_coordination', term_id=term['term_id'],
                roles=kinds, origin_id=edit_origin_id,
                endpoints=[[(k.chain_id or '_') + ':' + k.residue_id,
                            k.component_id, k.atom_name] for k in keys],
                request=dict(kind='bond', action='add', i_seqs=ids,
                    atoms=[atoms[i]['label'] for i in ids],
                    selections=[atom_selection(k) for k in keys],
                    distance_ideal=term['parameters']['ideal'],
                    weight=term['parameters']['weight'])))
        # Round-trip to detach all returned content from caller-owned objects.
        return json.loads(canonical(result))
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError('Cannot declare coordination topology: ' + str(exc)) from exc
