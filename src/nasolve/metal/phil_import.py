"""Offline import of an explicit, deliberately narrow PHIL edits subset.

Selectors are historical text, never evaluated. Every selector must be mapped
explicitly to a logical node before reuse against a new, verified inventory.
Unknown native semantics are rejected rather than approximated or discarded.
"""
import hashlib
import json
import re

from .recipe import Recipe, RecipeError, number, text

PROTOCOL = 'metal-phil-import-v1'


def _line(line):
    quote = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif quote and char == '\\':
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char == '#':
            return line[:index].strip()
        elif char in ('"', "'") and (index == 0 or line[index-1].isspace() or line[index-1] == '='):
            quote = char
    if quote:
        raise RecipeError('Unclosed PHIL quote; multiline values are unsupported')
    return line.strip()


def _selector(value, aliases, used=None):
    visited = set()
    while value.startswith('$'):
        name = value[1:]
        if name not in aliases or name in visited:
            raise RecipeError('Unknown, cyclic or compound PHIL variable')
        visited.add(name)
        if used is not None:
            used.add(name)
        value = aliases[name]
    if value.startswith('"'):
        try:
            value = json.loads(value)
        except ValueError as exc:
            raise RecipeError('Unsupported quoted PHIL selector') from exc
    elif value.startswith("'"):
        if len(value) < 2 or value[-1] != "'" or '\\' in value:
            raise RecipeError('Unsupported quoted PHIL selector')
        value = value[1:-1]
    text(value, 'selector')
    if '$' in value or value in {'None', 'Auto'} or any(c in value for c in '{}\\'):
        raise RecipeError('Require a literal selector or one complete local variable')
    return value


def inspect_restraints(raw):
    """Return an unbound import record; no model lookup, file I/O or execution.

    Accept one multiline refinement.geometry_restraints.edits scope containing
    scalar local selection aliases and add-only bonds/angles. Preserve endpoint
    order, numeric targets and sigma. Nonidentity symmetry, slack and every
    unrecognized field/scope/directive fail closed. Limits bound parser work.
    """
    if not isinstance(raw, bytes) or not raw or len(raw) > 131072:
        raise RecipeError('Require 1–131072 bytes of UTF-8 PHIL edits')
    try:
        source = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise RecipeError('Require UTF-8 PHIL edits') from exc
    aliases, blocks = {}, []
    state, current = 'start', None
    for index, original in enumerate(source.splitlines(), 1):
        line = _line(original)
        if not line:
            continue
        if state == 'start' and re.fullmatch(r'refinement\.geometry_restraints\.edits\s*\{', line):
            state = 'root'
        elif state == 'root' and re.fullmatch(r'(bond|angle)\s*\{', line):
            current = {'kind': line.split('{')[0].strip(), 'fields': {}}
            state = 'term'
        elif line == '}' and state == 'term':
            blocks.append(current)
            if len(blocks) > 512:
                raise RecipeError('At most 512 restraint terms per import')
            current, state = None, 'root'
        elif line == '}' and state == 'root':
            state = 'done'
        elif state in {'root', 'term'}:
            match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)', line)
            if not match or any(c in line for c in '{}'):
                raise RecipeError(f'Unsupported PHIL statement on line {index}')
            name, value = match.groups()
            fields = aliases if state == 'root' else current['fields']
            if name in fields:
                raise RecipeError(f'Duplicate PHIL field: {name}')
            fields[name] = value.strip()
            if len(fields) > 512:
                raise RecipeError('Too many PHIL fields')
        else:
            raise RecipeError(f'Unsupported PHIL scope or trailing content on line {index}')
    if state != 'done' or not blocks:
        raise RecipeError('Require a complete nonempty PHIL edits scope')
    # Validate even unused aliases; never pass them to native software.
    for value in aliases.values():
        _selector(value, aliases)
    selectors, terms, used = [], [], set()
    for index, block in enumerate(blocks, 1):
        kind, fields = block['kind'], block['fields']
        count = 2 if kind == 'bond' else 3
        target = 'distance_ideal' if kind == 'bond' else 'angle_ideal'
        endpoints = [f'atom_selection_{i}' for i in range(1, count+1)]
        required = {'action', 'sigma', target, *endpoints}
        optional = {'symmetry_operation', 'slack'} if kind == 'bond' else set()
        if not required <= fields.keys() or fields.keys() - required - optional:
            raise RecipeError(f'{kind}: missing or unsupported fields')
        if fields['action'] not in {'add', '*add'}:
            raise RecipeError('Only add restraints are supported')
        if any(fields.get(key, 'None') != 'None' for key in optional):
            raise RecipeError('Nonidentity symmetry or slack is unsupported')
        try:
            ideal, sigma = (number(float(fields[k]), k) for k in (target, 'sigma'))
        except (ValueError, OverflowError) as exc:
            raise RecipeError('Require finite numeric target and sigma') from exc
        if sigma <= 0 or (ideal <= 0 if kind == 'bond' else not 0 <= ideal <= 180):
            raise RecipeError('Target or sigma outside allowed range')
        ids = []
        for endpoint in endpoints:
            selection = _selector(fields[endpoint], aliases, used)
            found = next((s for s in selectors if s['selection'] == selection), None)
            if found is None:
                found = {'id': f's{len(selectors)+1}', 'selection': selection}
                selectors.append(found)
            ids.append(found['id'])
        if len(set(ids)) != len(ids):
            raise RecipeError('Repeated selector in a restraint')
        terms.append(dict(id=f'r{index}', kind='distance' if kind == 'bond' else 'angle',
                          selectors=ids, target=ideal, sigma=sigma,
                          unit='angstrom' if kind == 'bond' else 'degree'))
    if used != set(aliases):
        raise RecipeError('Unused root fields are unsupported; only referenced selection aliases are accepted')
    return dict(kind='metal-restraint-import', schema_version=1, protocol=PROTOCOL,
                source_sha256=hashlib.sha256(raw).hexdigest(), source_size=len(raw),
                source_text=source, selectors=selectors, restraints=terms,
                status='UNBOUND', native_ready=False)


def import_recipe(raw, nodes, *, recipe_id, name):
    """Rebind every historical selector to an explicitly supplied recipe node.

    Node mappings can declare donor roles, exact-bound atoms or metal elements.
    This does not resolve the old selectors or assert equivalence with new ones.
    Ordinary preview/materialization must bind and validate the new inventory.
    """
    draft = inspect_restraints(raw)
    if not isinstance(nodes, dict) or set(nodes) != {s['id'] for s in draft['selectors']}:
        raise RecipeError('Map every imported selector exactly once')
    if any(not isinstance(n, dict) or 'id' not in n for n in nodes.values()):
        raise RecipeError('Each selector requires a complete explicit node object')
    # Recipe validation checks node IDs, unique identities, types and all terms.
    rows = [nodes[s['id']] for s in draft['selectors']]
    terms = [dict(id=r['id'], kind=r['kind'], nodes=[nodes[s]['id'] for s in r['selectors']],
                  set_id='imported', enabled=True, target=r['target'], sigma=r['sigma'], unit=r['unit'],
                  source=dict(kind='user', note='Imported PHIL target; explicit logical rebinding; chemistry unqualified'))
             for r in draft['restraints']]
    return Recipe(dict(kind='metal-restraint-recipe', schema_version=1, id=recipe_id,
                       name=name, revision=1, nodes=rows,
                       sets=[dict(id='imported', name='Imported restraints', enabled=True)], restraints=terms,
                       extensions=dict(phil_import=dict(draft, node_mapping=nodes))))
