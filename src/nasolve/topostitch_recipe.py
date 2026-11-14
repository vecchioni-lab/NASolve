"""Freeze complete canonical pair recipes for an explicit image-energy diagnostic.

This prepares data only. It neither chooses a connection nor adds chemical bonds,
changes native exclusions, optimizes coordinates or attaches a Phenix callback.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path
import re

from .topostitch_coordinates import ResidueSite, _CANONICAL, _read_atoms, _residue
from .topostitch_periodic import crystal_from_pdb_bytes
from .topostitch_transport import crystallographic_image

KIND = 'topostitch-canonical-image-recipe'
POLICY = {'normalization': 'UNNORMALIZED_ADDITIVE_PAIR_ENERGY',
          'native_bonded_tables_changed': False, 'native_exclusions_changed': False,
          'new_covalent_links': False, 'native_callback_attached': False}


def recipe_digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class PairImage:
    pair_id: str
    source: ResidueSite
    target: ResidueSite
    target_operator_xyz: str
    purpose: str = 'selected'

    def __post_init__(self):
        if not isinstance(self.pair_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', self.pair_id):
            raise ValueError('Require a short explicit pair identifier')
        if not all(isinstance(s, ResidueSite) for s in (self.source, self.target)) or self.source == self.target:
            raise ValueError('Require two distinct explicit canonical residue sites')
        if self.purpose not in ('selected', 'core'):
            raise ValueError('Pair purpose must be selected or core')
        if not isinstance(self.target_operator_xyz, str) or not self.target_operator_xyz.strip():
            raise ValueError('Require an explicit target image')


def model_atom_rows(data):
    """Keep native PDB order and exact names; no serial-number/index inference."""
    _read_atoms(data)  # Shared single-model and finite-coordinate validation.
    rows = []
    for line in data.decode('ascii').splitlines():
        if line[:6] not in ('ATOM  ', 'HETATM'):
            continue
        rows.append({'chain': line[21:22].strip(), 'residue_number': int(line[22:26]),
                     'insertion_code': line[26:27].strip(), 'residue_code': line[17:20].strip(),
                     'atom_name': line[12:16].strip(), 'altloc': line[16:17].strip()})
    keys = [tuple(row.values()) for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate model atom identities are unsupported')
    return rows


def _library():
    from restraints import phenix, residue_library
    from restraints.recipe_library import recipe_for
    records = residue_library.load_residue_records()
    maps, required, counts = {}, {}, {}
    for name, categories in (('AT', 'AT'), ('GC', 'GC')):
        recipe = recipe_for(*categories)
        if recipe is None or recipe.name != name or recipe.noncanonical:
            raise ValueError('Require compatible canonical NARestraints recipes')
        counts[name] = {'bond': len(getattr(phenix, name+'_BONDS')),
                        'angle': len(getattr(phenix, name+'_ANGLE_RESTRAINTS')),
                        'planarity': 1, 'parallelity': 1}
        for category in categories:
            roles = set(getattr(phenix, name+'_PARALLEL_'+category))
            for key, n in ((name+'_BONDS', 2), (name+'_ANGLE_RESTRAINTS', 3)):
                for row in getattr(phenix, key):
                    if len(row) != n+2 or any(type(v) not in (int,float) or not math.isfinite(v) or v <= 0 for v in row[n:]):
                        raise ValueError('Unsupported canonical recipe table')
                    for ref in row[:n]:
                        parts = ref.split('.')
                        if len(parts) != 2 or parts[0] not in categories:
                            raise ValueError('Unsupported canonical atom role')
                        if parts[0] == category:
                            roles.add(parts[1])
            code = 'D'+category
            matches = [r for r in records if r.get('Ligand code') == code]
            if len(matches) != 1 or matches[0].get('Base Analog') != category:
                raise ValueError('Require one canonical library record for '+code)
            mapping = {}
            for role in sorted(roles):
                atom = matches[0].get(role)
                if not isinstance(atom, str) or not re.fullmatch(r"[A-Za-z0-9']{1,4}", atom.strip()):
                    raise ValueError('Missing or unsupported canonical atom role '+code+'.'+role)
                mapping[role] = atom.strip()
            if len(set(mapping.values())) != len(mapping):
                raise ValueError('Ambiguous canonical atom-role mapping for '+code)
            maps[code], required[code] = mapping, sorted(roles)
    return phenix, maps, required, counts


def prepare_pair_recipe(model_path, pairs, *, expected_sha256, max_pairs=1000):
    """Prepare one complete, hash-bound packet; all topology is caller-declared.

    Requires the topology extra and installed NARestraints. Virtual L/R labels
    exist only in emitted selection recipes, never in a scattering model. No
    output is written. Explicit model paths remain required when consuming it.
    """
    if type(max_pairs) is not int or not 1 <= max_pairs <= 1000:
        raise ValueError('Require a pair budget from 1 to 1000')
    pairs = tuple(pairs)
    if not 1 <= len(pairs) <= max_pairs or any(not isinstance(p, PairImage) for p in pairs):
        raise ValueError('Require bounded explicit PairImage requests')
    path = Path(model_path)
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Source model checksum mismatch')
    inventory = _read_atoms(data)
    ledger = model_atom_rows(data)
    gemmi, cell, group = crystal_from_pdb_bytes(data)
    phenix, maps, required, counts = _library()
    result, seen_ids, seen_edges = [], set(), set()
    for request in pairs:
        if request.pair_id in seen_ids:
            raise ValueError('Duplicate pair identifier')
        seen_ids.add(request.pair_id)
        # Factory verifies group membership while retaining whole-cell shifts.
        crystallographic_image(cell.parameters, group, request.target_operator_xyz)
        op = gemmi.Op(request.target_operator_xyz)
        key = (request.source, request.target, op.triplet())
        inverse = (request.target, request.source, op.inverse().triplet())
        if key in seen_edges or inverse in seen_edges:
            raise ValueError('Duplicate or reciprocal pair image would double its weight')
        seen_edges.add(key)
        categories, residues, role_indices = [], [], {}
        for role, site in zip(('L','R'), (request.source, request.target)):
            category, present = _residue(inventory, site)
            code = 'D'+category
            raw_rows = next(iter(inventory[site].values()))
            if any(row[4] != 1 for row in raw_rows):
                raise ValueError('Recipe binding requires full occupancy at selected residues')
            missing = set(maps[code].values()) - set(present)
            if missing:
                raise ValueError('Require complete canonical plane/contact atoms: '+','.join(sorted(missing)))
            indices = [i for i, row in enumerate(ledger) if all(row[k] == v for k,v in asdict(site).items())]
            actual_names = {ledger[i]['atom_name'] for i in indices}
            if not set(maps[code].values()) <= actual_names:
                raise ValueError('Require exact native atom names; normalize legacy names upstream')
            role_indices[role] = indices
            residues.append(phenix.PairResidue(role, '1', maps[code], category))
            categories.append(category)
        name = 'AT' if set(categories) == {'A','T'} else 'GC' if set(categories) == {'G','C'} else None
        if name is None:
            raise ValueError('Only canonical AT and GC pairs are supported')
        body = phenix.generate_pair_restraints(*residues, parallels=True, planes=True)
        if not body:
            raise ValueError('Complete canonical recipe was not generated')
        text = 'geometry_restraints.edits {\n'+body+'\n}\n'
        result.append({'pair_id': request.pair_id, 'purpose': request.purpose,
            'sites': [asdict(request.source), asdict(request.target)], 'recipe': name,
            'target_operator_xyz': op.triplet(), 'role_indices': role_indices,
            'expected_counts': counts[name], 'phil': text,
            'phil_sha256': sha256(text.encode()).hexdigest()})
    effective = {'atom_roles': maps, 'required_roles': required,
                 'emitted_recipes': [p['phil'] for p in result]}
    packet = {'schema_version': 1, 'kind': KIND, 'source_model_sha256': expected_sha256,
        'atom_count': len(ledger), 'atom_identities': ledger,
        'crystal': {'cell_parameters': list(cell.parameters), 'space_group': group},
        'library': {'name':'NARestraints', 'version':version('NARestraints'),
            'formatter_sha256': sha256(Path(phenix.__file__).read_bytes()).hexdigest(),
            'effective_sha256': recipe_digest(effective), 'effective': effective},
        'pairs': result, 'policy': dict(POLICY), 'runtime_authority': False,
        'scientific_acceptance': False, 'connection_capacity_validated': False,
        'limitations': ['Explicit canonical pairs only; no topology or partner inference',
            'Additive pair energies do not reproduce native bond-edit exclusions',
            'No stacking, covalent closure, movement mask or refinement integration',
            'No connection capacity, packing, density or scientific approval']}
    if path.read_bytes() != data:
        raise ValueError('Source model changed during recipe preparation')
    return packet
