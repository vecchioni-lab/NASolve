"""Explicit PHIL restraint export from a revalidated coordinate preview.

Selectors include every supported atom identity field. Native consumption and
chemistry qualification are separate; export starts no process.
"""
import json
import re

from .binding import Atom, AtomKey, ModelSnapshot, ResidueKey, RoleMap
from .recipe import Recipe, RecipeError
from .preview import preview


def atom_selection(key: AtomKey) -> str:
    if key.symmetry != 'x,y,z':
        raise RecipeError('Nonidentity symmetry export is not supported')
    # Values are tokens in the atom-selection language before PHIL quoting.
    # Refuse quotes/backslashes rather than risk widening an exact selection.
    # MODEL identifiers in PDB text and CCTBX's implicit model ID differ. This
    # exporter is deliberately limited to a single-model inventory below.
    fields = [('chain', key.chain_id),
              ('resid', key.residue_id + key.insertion_code), ('resname', key.component_id),
              ('name', key.atom_name), ('altloc', key.altloc), ('segid', key.segment_id)]
    terms = []
    for name, value in fields:
        if value and re.fullmatch(r"[A-Za-z0-9_+-][A-Za-z0-9_+.'-]*", value) is None:
            raise RecipeError('Unsupported character in exact native atom selector')
        # Unquoted CCTBX tokens strip PDB padding; quoted strings retain it.
        # Prime marks within a token remain literal. Empty alternates/segments
        # need their native blank-field spelling, not an empty quoted string.
        token = value if value else ("'    '" if name == 'segid' else "' '")
        terms.append(f'{name} {token}')
    return ' and '.join(terms)


def _replay(result):
    try:
        inputs = result['inputs']
        source = inputs['model']
        model = ModelSnapshot(tuple(Atom(AtomKey(**a['key']), a['element'], tuple(a['xyz']))
                                    for a in source['atoms']), source['source_sha256'], source['checkpoint_id'])
        roles = inputs['roles']
        if roles is not None:
            roles = RoleMap(roles['records'], source_sha256=roles['source_sha256'], source_label=roles['source_label'])
        fresh = preview(Recipe(inputs['recipe']), model=model, roles=roles,
                        residue_slots={k: ResidueKey(**r) for k, r in inputs['residue_slots'].items()},
                        atom_bindings={k: AtomKey(**r) for k, r in inputs['atom_bindings'].items()})
        if fresh['input_sha256'] != result['input_sha256'] or any(fresh[k] != result[k] for k in ('status', 'nodes', 'restraints')):
            raise RecipeError('Preview changed; rebind before exporting')
        return fresh
    except (KeyError, TypeError, ValueError) as exc:
        raise RecipeError(f'Cannot export this preview: {exc}') from exc


def export_restraints(result: dict) -> str:
    result = _replay(result)
    if result['status'] != 'resolved':
        raise RecipeError('Export requires resolved enabled restraints with targets, sigma and provenance')
    inventory = result['inputs']['model']['atoms']
    if len({a['key']['model_id'] for a in inventory}) != 1:
        raise RecipeError('Native export requires a single-model inventory')
    keys = {row['node_id']: AtomKey(**row['atom']['key']) for row in result['nodes'] if row['atom']}
    lines = ['# Proposed metal restraints; export is not chemical or native qualification.',
             '# Preview input SHA-256: ' + result['input_sha256'], 'refinement.geometry_restraints.edits {']
    for row in result['restraints']:
        if not row['enabled']:
            continue
        kind = 'bond' if row['kind'] == 'distance' else 'angle'
        lines.extend([f'  # restraint {row["restraint_id"]}; set {row["set_id"]}', f'  {kind} {{', '    action = add'])
        for index, node in enumerate(row['node_ids'], 1):
            selected = keys[node]
            # CCTBX matches several fields case-insensitively. Refuse keys that
            # would become ambiguous even though the Python keys are distinct.
            folded = lambda key: tuple(str(value).casefold() for name, value in key.items() if name != 'model_id')
            if sum(folded(a['key']) == folded(selected.to_dict()) for a in inventory) != 1:
                raise RecipeError('Native selection is ambiguous after case normalization')
            lines.append(f'    atom_selection_{index} = ' + json.dumps(atom_selection(keys[node])))
        target = 'distance_ideal' if kind == 'bond' else 'angle_ideal'
        lines.extend([f'    {target} = {row["target"]:.12g}', f'    sigma = {row["sigma"]:.12g}', '  }'])
    lines.extend(['}', ''])
    return '\n'.join(lines)
