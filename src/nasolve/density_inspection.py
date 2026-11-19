"""Offline two-state density presentation, extracted from the W143 study.

The caller owns source verification, map/model correspondence and mesh production.
This module validates display data and embeds it; it never resolves scientific
inputs, reads coefficients, launches tools, calculates density or selects a model.
The legacy scene slots ``native``/``full`` are presentation slots, not claims about
refinement or scientific quality. Human labels are supplied separately.
"""
from __future__ import annotations

import base64
import gzip
import html
from importlib.resources import files
import json
import math
from pathlib import Path
import re


_STATES = ('native', 'full')
_LEVELS = {('2mFo-DFc', i / 2) for i in range(2, 13)} | {
    ('mFo-DFc', sign * i / 2) for i in range(3, 13) for sign in (-1, 1)
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1e8


def _vector(value):
    return isinstance(value, list) and len(value) == 3 and all(_finite(x) for x in value)


def _text(value, name, limit=8000):
    _require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit,
             f'{name} must be nonempty bounded text')
    return value


def _display_scene(scene):
    """Copy JSON data and reject unsafe or incomplete display geometry."""
    try:
        raw = json.dumps(scene, allow_nan=False, separators=(',', ':'))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('Display scene must contain finite JSON data') from exc
    _require(len(raw) <= 64_000_000, 'Display scene exceeds the 64 MB bound')
    data = json.loads(raw)
    _require(isinstance(data, dict) and data.get('kind') == 'local-backbone-density-display'
             and type(data.get('schema_version')) is int and data['schema_version'] == 1,
             'Unsupported density display scene')
    _require(_vector(data.get('center')), 'Display center must be three finite coordinates')
    _require(_vector(data.get('extent')) and all(.1 <= x <= 1e6 for x in data['extent']),
             'Display extent must be positive and bounded')
    atoms = data.get('atoms')
    _require(isinstance(atoms, list) and 1 <= len(atoms) <= 500,
             'Display requires 1–500 atoms')
    identities = set()
    for atom in atoms:
        _require(isinstance(atom, dict), 'Invalid display atom')
        _text(atom.get('label'), 'Atom label', 300)
        _text(atom.get('element'), 'Element', 3)
        identity = json.dumps(atom.get('key'), sort_keys=True)
        _require(atom.get('key') is not None and identity not in identities,
                 'Display atom identities must be present and unique')
        identities.add(identity)
        _require(all(_vector(atom.get(state)) for state in _STATES),
                 'Each atom requires both finite coordinate states')
        # Report actual supplied-coordinate movement, never a caller's stale value.
        atom['movement_A'] = math.dist(atom['native'], atom['full'])
    bonds = data.get('bonds')
    _require(isinstance(bonds, list) and len(bonds) <= 2000, 'Invalid display bonds')
    seen = set()
    for bond in bonds:
        pair = bond.get('indices') if isinstance(bond, dict) else None
        _require(isinstance(pair, list) and len(pair) == 2 and
                 all(type(i) is int and 0 <= i < len(atoms) for i in pair) and pair[0] != pair[1],
                 'Bond endpoints must be two distinct display atom indices')
        key = tuple(sorted(pair))
        _require(key not in seen, 'Duplicate display bond')
        seen.add(key)
        _require(all(math.dist(atoms[pair[0]][s], atoms[pair[1]][s]) > 1e-8 for s in _STATES),
                 'A displayed bond has coincident endpoints')
    layers = data.get('layers')
    _require(isinstance(layers, dict) and set(layers) == set(_STATES),
             'Both display map slots must be explicit')
    total_vertices = total_triangles = 0
    for state in _STATES:
        meshes = layers[state]
        _require(isinstance(meshes, list) and len(meshes) in (0, 31),
                 'A map slot must be unavailable or contain all 31 contour meshes')
        choices = set()
        for mesh in meshes:
            _require(isinstance(mesh, dict) and isinstance(mesh.get('type'), str) and
                     _finite(mesh.get('level')), 'Invalid contour description')
            choice = (mesh['type'], mesh['level'])
            _require(choice in _LEVELS and choice not in choices, 'Duplicate or unsupported contour level')
            choices.add(choice)
            vertices, triangles = mesh.get('vertices'), mesh.get('triangles')
            _require(isinstance(vertices, list) and len(vertices) % 3 == 0 and
                     all(_finite(v) for v in vertices), 'Invalid contour vertices')
            count = len(vertices) // 3
            _require(isinstance(triangles, list) and len(triangles) % 3 == 0 and
                     all(type(i) is int and 0 <= i < count for i in triangles),
                     'Invalid contour triangle indices')
            total_vertices += count
            total_triangles += len(triangles) // 3
        _require(not meshes or choices == _LEVELS, 'Incomplete saved contour choices')
    _require(total_vertices <= 250_000 and total_triangles <= 500_000,
             'Display mesh budget exceeded')
    samples = data.get('atom_samples', {})
    _require(isinstance(samples, dict) and set(samples) <= set(_STATES), 'Invalid sample states')
    for state, maps in samples.items():
        _require(isinstance(maps, dict) and set(maps) <= {'2mFo-DFc', 'mFo-DFc'},
                 'Unsupported sampled map type')
        for values in maps.values():
            _require(bool(layers[state]) and isinstance(values, list) and len(values) == len(atoms)
                     and all(_finite(v) for v in values), 'Samples require a saved map and one finite value per atom')
    data['atom_samples'] = samples
    return data


def density_inspection_html(scene, *, title, subtitle, source_note, frame_note,
                            model_labels=('Reference', 'Comparison')):
    """Render supplied two-state display data as a self-contained offline page.

    Notes are escaped plain text supplied by the calling workflow, not evidence
    authenticated by this renderer. Empty map slots remain explicitly unavailable.
    Numeric meshes and coordinates are preserved; movement is measured directly
    from the supplied coordinates. No alignment or scientific acceptance occurs.
    """
    data = _display_scene(scene)
    for name, value in (('title', title), ('subtitle', subtitle),
                        ('source_note', source_note), ('frame_note', frame_note)):
        _text(value, name)
    _require(isinstance(model_labels, (list, tuple)) and len(model_labels) == 2,
             'Supply two model labels')
    labels = dict(zip(_STATES, [_text(v, 'Model label', 120) for v in model_labels]))
    data['display_labels'] = labels
    payload = json.dumps(data, allow_nan=False, separators=(',', ':')).encode('utf-8')
    replacements = {
        '__PACKED_SCENE__': base64.b64encode(gzip.compress(payload, mtime=0)).decode('ascii'),
        '__TITLE__': html.escape(title), '__SUBTITLE__': html.escape(subtitle),
        '__SOURCE_NOTE__': html.escape(source_note), '__FRAME_NOTE__': html.escape(frame_note),
        '__NATIVE_LABEL__': html.escape(labels['native']), '__FULL_LABEL__': html.escape(labels['full']),
    }
    template = files('nasolve').joinpath('data/density-inspection.html').read_text(encoding='utf-8')
    _require(all(token in template for token in replacements), 'Incomplete installed density template')
    # One substitution pass: a caller's text cannot become another template token.
    return re.sub('|'.join(re.escape(k) for k in replacements),
                  lambda match: replacements[match.group()], template)


def write_density_inspection(scene, output_path, **presentation):
    """Write a new offline view, refusing replacement and validating before I/O."""
    page = density_inspection_html(scene, **presentation)
    with Path(output_path).open('x', encoding='utf-8') as stream:
        stream.write(page)


__all__ = ['density_inspection_html', 'write_density_inspection']
