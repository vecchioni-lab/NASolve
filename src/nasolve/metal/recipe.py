"""Versioned, immutable metal-restraint recipes, independent of any GUI toolkit.

A valid draft may lack numerical targets. Validation checks representation and
references; it does not approve chemistry or authorize native refinement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
import re
from typing import Any, Mapping


class RecipeError(ValueError):
    """A recipe or explicit preview input is malformed or unsupported."""


def canonical(value: Any) -> str:
    def check(item):
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise RecipeError('JSON object keys must be strings')
            for child in item.values():
                check(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check(child)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise RecipeError('Require JSON-compatible values')
    check(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, OverflowError) as exc:
        raise RecipeError('Require finite JSON values') from exc


def digest(value: Any) -> str:
    return sha256(canonical(value).encode('utf-8')).hexdigest()


def text(value: Any, label: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()) or any(ord(c) < 32 for c in value):
        raise RecipeError(f'{label}: require text without control characters')
    return value


def number(value: Any, label: str) -> float:
    if type(value) not in (int, float):
        raise RecipeError(f'{label}: require a finite number')
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise RecipeError(f'{label}: require a finite number') from exc
    if not math.isfinite(result):
        raise RecipeError(f'{label}: require a finite number')
    return result


def checksum(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise RecipeError(f'{label}: require a lowercase SHA-256')
    return value


def element(value: Any) -> str:
    # Explicit element labels only. No oxidation state, chemistry or target is inferred.
    symbols = ('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn '
               'Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce '
               'Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At '
               'Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn '
               'Nh Fl Mc Lv Ts Og D').split()
    if not isinstance(value, str) or value not in symbols:
        raise RecipeError('Require an explicit element symbol with standard capitalization')
    return value


def _fields(row: Any, required: set[str], optional: set[str], label: str) -> None:
    if not isinstance(row, dict) or not required <= row.keys() or row.keys() - required - optional:
        raise RecipeError(f'{label}: missing or unsupported fields; optional metadata belongs in extensions')
    if 'extensions' in row and not isinstance(row['extensions'], dict):
        raise RecipeError(f'{label}.extensions must be an object')


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value):
        raise RecipeError(f'{label}: require a stable identifier')
    return value


def _boolean(value: Any, label: str) -> None:
    if type(value) is not bool:
        raise RecipeError(f'{label}: require true or false')


def _unique(rows: list[dict], label: str) -> set[str]:
    ids = [_identifier(row.get('id'), label) if isinstance(row, dict) else None for row in rows]
    if None in ids or len(ids) != len(set(ids)):
        raise RecipeError(f'{label}: duplicate or malformed identifiers')
    return set(ids)


def _document(document: Mapping[str, Any]) -> dict:
    # JSON round trip owns every nested object, so GUI dictionaries cannot mutate a saved recipe.
    doc = json.loads(canonical(document))
    _fields(doc, {'kind', 'schema_version', 'id', 'name', 'revision', 'nodes', 'sets', 'restraints'},
            {'extensions'}, 'recipe')
    if doc['kind'] != 'metal-restraint-recipe' or type(doc['schema_version']) is not int or doc['schema_version'] != 1:
        raise RecipeError('Unsupported metal recipe schema; backend update required')
    _identifier(doc['id'], 'recipe.id')
    text(doc['name'], 'recipe.name')
    if type(doc['revision']) is not int or doc['revision'] < 1:
        raise RecipeError('recipe.revision must be a positive integer')
    for key in ('nodes', 'sets', 'restraints'):
        if not isinstance(doc[key], list):
            raise RecipeError(f'recipe.{key} must be a list')
    node_ids = _unique(doc['nodes'], 'nodes')
    set_ids = _unique(doc['sets'], 'sets')
    _unique(doc['restraints'], 'restraints')
    for node in doc['nodes']:
        kind = node.get('kind')
        if not isinstance(kind, str):
            raise RecipeError('Unsupported node kind')
        extra = {'donor': {'residue_slot', 'role'}, 'metal': {'element'}, 'atom': set()}.get(kind)
        if extra is None:
            raise RecipeError('Unsupported node kind')
        _fields(node, {'id', 'kind'} | extra, {'label', 'extensions'}, 'node')
        if 'label' in node:
            text(node['label'], 'node.label')
        if kind == 'donor':
            _identifier(node['residue_slot'], 'residue_slot')
            text(node['role'], 'role')
        elif kind == 'metal':
            element(node['element'])
    for group in doc['sets']:
        _fields(group, {'id', 'name', 'enabled'}, {'extensions'}, 'set')
        text(group['name'], 'set.name')
        _boolean(group['enabled'], 'set.enabled')
    for restraint in doc['restraints']:
        _fields(restraint, {'id', 'set_id', 'kind', 'nodes', 'enabled', 'target', 'sigma', 'unit', 'source'},
                {'extensions'}, 'restraint')
        kind = restraint['kind']
        if kind not in ('distance', 'angle'):
            raise RecipeError('Only explicit distances and angles are supported')
        endpoints = restraint['nodes']
        if (not isinstance(endpoints, list) or len(endpoints) != (2 if kind == 'distance' else 3)
                or any(not isinstance(n, str) or n not in node_ids for n in endpoints)
                or len(set(endpoints)) != len(endpoints)):
            raise RecipeError('Restraint endpoints must be distinct existing node IDs')
        if not isinstance(restraint['set_id'], str) or restraint['set_id'] not in set_ids:
            raise RecipeError('Restraint requires an existing set ID')
        _boolean(restraint['enabled'], 'restraint.enabled')
        if restraint['unit'] != ('angstrom' if kind == 'distance' else 'degree'):
            raise RecipeError('Restraint unit does not match its kind')
        for key in ('target', 'sigma'):
            if restraint[key] is not None:
                restraint[key] = number(restraint[key], key)
                if restraint[key] <= 0 and not (key == 'target' and kind == 'angle' and restraint[key] == 0):
                    raise RecipeError(f'{kind} {key} is outside its allowed range')
        if kind == 'angle' and restraint['target'] is not None and restraint['target'] > 180:
            raise RecipeError('Angle target must lie between 0 and 180 degrees')
        source = restraint['source']
        if source is not None:
            _fields(source, {'kind', 'note'}, {'extensions'}, 'source')
            if source['kind'] not in ('user', 'reference', 'library'):
                raise RecipeError('Unsupported target source kind')
            text(source['note'], 'source.note')
    return doc


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecipeError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


@dataclass(frozen=True, init=False)
class Recipe:
    """Immutable document with stable graph IDs and deterministic JSON/hash.

    Editing returns a new revision. This document hash is not a native-result
    cache key: diffraction inputs, effective parameters and software are absent.
    """
    _json: str = field(repr=False)

    def __init__(self, document: Mapping[str, Any]):
        object.__setattr__(self, '_json', canonical(_document(document)))

    @classmethod
    def from_json(cls, value: str) -> Recipe:
        try:
            document = json.loads(value, object_pairs_hook=_json_object)
        except (ValueError, TypeError) as exc:
            raise RecipeError(str(exc)) from exc
        return cls(document)

    def to_dict(self) -> dict:
        return json.loads(self._json)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, allow_nan=False) + '\n'

    @property
    def sha256(self) -> str:
        return sha256(self._json.encode('utf-8')).hexdigest()

    def _with_item(self, collection: str, item: Mapping[str, Any]) -> Recipe:
        doc = self.to_dict()
        row = json.loads(canonical(item))
        if not isinstance(row, dict) or 'id' not in row:
            raise RecipeError(f'{collection} item must have an ID')
        for i, existing in enumerate(doc[collection]):
            if existing['id'] == row['id']:
                doc[collection][i] = row
                break
        else:
            doc[collection].append(row)
        candidate = Recipe(doc)
        if candidate._json == self._json:
            return self
        doc = candidate.to_dict()
        doc['revision'] += 1
        return Recipe(doc)

    def _without_item(self, collection: str, item_id: str, label: str) -> Recipe:
        doc = self.to_dict()
        rows = [r for r in doc[collection] if r['id'] != item_id]
        if len(rows) == len(doc[collection]):
            raise RecipeError(f'Unknown {label}: {item_id}')
        doc[collection] = rows
        doc['revision'] += 1
        # Referenced nodes/sets cannot be removed by silently cascading edits.
        return Recipe(doc)

    def with_node(self, node: Mapping[str, Any]) -> Recipe:
        return self._with_item('nodes', node)

    def without_node(self, node_id: str) -> Recipe:
        return self._without_item('nodes', node_id, 'node')

    def with_set(self, group: Mapping[str, Any]) -> Recipe:
        return self._with_item('sets', group)

    def without_set(self, set_id: str) -> Recipe:
        return self._without_item('sets', set_id, 'set')

    def with_restraint(self, restraint: Mapping[str, Any]) -> Recipe:
        """Add or replace one stable-ID row, retaining every other row's order."""
        return self._with_item('restraints', restraint)

    def without_restraint(self, restraint_id: str) -> Recipe:
        return self._without_item('restraints', restraint_id, 'restraint')
