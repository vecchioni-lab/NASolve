"""Offline, source-bound workbench catalog and immutable navigation snapshots.

Dataset mounts are explicit caller-owned locations, never persisted here. Opening
replays scientific evidence; selecting only navigates that verified snapshot.
"""
from dataclasses import dataclass, field
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

from ..run_context import dataset_directory
from .binding import AtomKey
from .context import _reference, parse_pdb
from .fdp_compare import verify_comparison
from .fdp_scan import verify_scan
from .geometry import verify_geometry
from .materialize import _json, _source
from .recipe import RecipeError, canonical, digest, text
from .reference import verify_reference_comparison

PROTOCOL = 'metal-workbench-v1'
LEVELS = ('dataset_id', 'structure_id', 'hypothesis_id', 'site_id', 'result_id', 'row_id')
RESULTS = {'fdp-comparison': verify_comparison, 'fdp-scan': verify_scan,
           'reference-comparison': verify_reference_comparison}


def _fields(value, names, label):
    if not isinstance(value, dict) or set(value) != set(names):
        raise RecipeError(label + ': unexpected or missing fields')


def _items(items, id_key, label, *, empty=True):
    if not isinstance(items, list) or not (0 if empty else 1) <= len(items) <= 1024:
        raise RecipeError(label + ': require a bounded explicit list (maximum 1024)')
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise RecipeError(label + ': require objects')
        value = item.get(id_key)
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
            raise RecipeError(label + ': require a stable identifier')
        if value in seen:
            raise RecipeError(label + ': duplicate identifier ' + value)
        seen.add(value)
        text(item.get('label'), label + ' label')
    return items


def _path(ref, anchor, root, *, captured):
    names = {'anchor', 'relative_path'} | ({'sha256', 'size'} if captured else set())
    _fields(ref, names, anchor + ' reference')
    value = ref['relative_path']
    if ref['anchor'] != anchor or not isinstance(value, str) or not value:
        raise RecipeError('Require an explicit ' + anchor + ' reference')
    path = PurePosixPath(value)
    if (path.is_absolute() or PureWindowsPath(value).drive or '\\' in value
            or any(p in ('', '.', '..') for p in value.split('/'))):
        raise RecipeError('Reference must be a normalized relative path')
    candidate = root.joinpath(*path.parts)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise RecipeError('Reference escapes its declared anchor')
    if any(p.is_symlink() for p in [candidate, *candidate.parents] if p != root and p.is_relative_to(root)):
        raise RecipeError('Workbench references must not traverse symlinks')
    return candidate


def _artifact(ref, run, verifier, *, captured, watched):
    path = _path(ref, 'run', run, captured=captured)
    if path.name != 'manifest.json':
        raise RecipeError('Require an explicit artifact manifest.json')
    if captured:
        _source(ref, run)
    doc = verifier(run, path.parent)
    actual = _reference(path, run)
    if canonical(_json(_source(actual, run))) != canonical(doc):
        raise RecipeError('Artifact changed during workbench verification')
    if captured and actual != ref:
        raise RecipeError('Workbench artifact reference changed')
    watched.append((run, actual))
    return actual, doc


def _result_rows(kind, report):
    if kind == 'fdp-comparison':
        return [(r['row_id'], r['key'], r) for r in report['rows']]
    if kind == 'reference-comparison':
        return [(r['node_id'], r['candidate']['key'], r) for r in report['nodes']]
    rows = []
    for point in report['points']:
        for site in point['sites']:
            data = dict(site, point_id=point['point_id'], state=point['state'],
                        trial_id=point['trial_id'], trial_manifest=point['trial'],
                        occupancy_vector=point['occupancies'], wavelength_A=point['wavelength_A'],
                        settings=report['fixed_settings'])
            rows.append((digest([point['point_id'], site['node_id']]), site['key'], data))
    return rows


def _result_geometry(kind, doc, report, run):
    if kind == 'fdp-comparison':
        return report['comparison_basis']['parent']['manifest']
    if kind == 'reference-comparison':
        return doc['parent']
    plan = _json(_source(doc['plan'], run))
    trial = _json(_source(plan['seed'], run))
    return trial['parent']['manifest']


def _load(definition, mounts, *, captured):
    """One schema/lineage path for capture and reopening; never search directories."""
    try:
        definition = json.loads(canonical(definition))
        _fields(definition, {'kind', 'schema_version', 'campaign_id', 'label', 'datasets'}, 'Workbench')
        kind = 'metal-workbench-catalog' if captured else 'metal-workbench-request'
        if definition['kind'] != kind or type(definition['schema_version']) is not int or definition['schema_version'] != 1:
            raise RecipeError('Unsupported workbench schema')
        _items([definition], 'campaign_id', 'campaign', empty=False)
        datasets = _items(definition['datasets'], 'dataset_id', 'datasets', empty=False)
        if not isinstance(mounts, dict) or set(mounts) != {d['dataset_id'] for d in datasets}:
            raise RecipeError('Supply exactly one explicit mount for every declared dataset')
        roots = {key: Path(value).expanduser().resolve() for key, value in mounts.items()}
        if any(not root.is_dir() for root in roots.values()):
            raise RecipeError('Dataset mount does not exist')
        if len(set(roots.values())) != len(roots):
            raise RecipeError('Different dataset IDs must not alias the same mount')
        rows, details, watched = [], [], []
        for dataset in datasets:
            _fields(dataset, {'dataset_id', 'label', 'structures'}, 'dataset')
            for structure in _items(dataset['structures'], 'structure_id', 'structures', empty=False):
                _fields(structure, {'structure_id', 'label', 'run', 'hypotheses'}, 'structure')
                run = _path(structure['run'], 'dataset', roots[dataset['dataset_id']], captured=False)
                if not run.is_dir():
                    raise RecipeError('Declared run directory does not exist')
                if dataset_directory(run) != roots[dataset['dataset_id']]:
                    raise RecipeError('Dataset mount must match the run context dataset root')
                for hypothesis in _items(structure['hypotheses'], 'hypothesis_id', 'hypotheses', empty=False):
                    _fields(hypothesis, {'hypothesis_id', 'label', 'geometry', 'sites', 'results'}, 'hypothesis')
                    geometry_ref, geometry = _artifact(hypothesis['geometry'], run, verify_geometry,
                                                       captured=captured, watched=watched)
                    hypothesis['geometry'] = geometry_ref
                    model = parse_pdb(_source(geometry['files']['model'], run))
                    inventory = {a.key for a in model.snapshot.atoms}
                    site_members = {}
                    for site in _items(hypothesis['sites'], 'site_id', 'sites'):
                        _fields(site, {'site_id', 'label', 'atoms'}, 'site')
                        if not isinstance(site['atoms'], list) or not 1 <= len(site['atoms']) <= 4096:
                            raise RecipeError('Site requires 1 to 4096 exact atom identities')
                        atoms = [AtomKey(**a) for a in site['atoms']]
                        if len(set(atoms)) != len(atoms) or any(a not in inventory for a in atoms):
                            raise RecipeError('Site atoms must be distinct exact members of the candidate model')
                        site['atoms'] = [a.to_dict() for a in atoms]
                        site_members[site['site_id']] = set(atoms)
                    scope = dict(dataset_id=dataset['dataset_id'], structure_id=structure['structure_id'],
                                 hypothesis_id=hypothesis['hypothesis_id'])
                    details.append(dict(scope, geometry_id=geometry['geometry_id'], parent=geometry['parent'],
                                        model=geometry['files']['model'], status=geometry['status']))
                    for result in _items(hypothesis['results'], 'result_id', 'results'):
                        _fields(result, {'result_id', 'label', 'kind', 'manifest'}, 'result')
                        if result['kind'] not in RESULTS:
                            raise RecipeError('Unsupported workbench result kind')
                        ref, doc = _artifact(result['manifest'], run, RESULTS[result['kind']],
                                             captured=captured, watched=watched)
                        result['manifest'] = ref
                        report = _json(_source(doc['files']['report'], run))
                        if _result_geometry(result['kind'], doc, report, run) != geometry_ref:
                            raise RecipeError('Result belongs to a different geometry')
                        result_scope = dict(scope, result_id=result['result_id'])
                        # Retain reports verbatim for pending points, controls and provenance.
                        details.append(dict(result_scope, kind=result['kind'], manifest=ref, report=report))
                        for source_id, key, data in _result_rows(result['kind'], report):
                            atom = AtomKey(**key)
                            if atom not in inventory:
                                raise RecipeError('Result atom is absent from the candidate')
                            row_id = digest(dict(campaign_id=definition['campaign_id'], **result_scope,
                                                 manifest=ref, source_row_id=source_id))
                            rows.append(dict(result_scope, row_id=row_id, source_row_id=source_id,
                                             result_kind=result['kind'],
                                             site_ids=[s for s, atoms in site_members.items() if atom in atoms], data=data))
        for run, ref in watched:
            _source(ref, run)
        definition['kind'] = 'metal-workbench-catalog'
        definition['catalog_id'] = digest(definition)
        return definition, rows, details
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError('Cannot load workbench: ' + str(exc)) from exc


def capture_catalog(request, mounts):
    """Freeze explicit artifact references after replay; returns a new JSON value."""
    catalog, _, _ = _load(request, mounts, captured=False)
    return catalog


def open_workbench(catalog, mounts):
    """Reverify all catalog evidence offline and return an immutable view snapshot."""
    if not isinstance(catalog, dict):
        raise RecipeError('Require a workbench catalog object')
    definition = dict(catalog)
    identity = definition.pop('catalog_id', None)
    if identity != digest(definition):
        raise RecipeError('Workbench catalog identity changed')
    rebuilt, rows, details = _load(definition, mounts, captured=True)
    if canonical(rebuilt) != canonical(catalog):
        raise RecipeError('Workbench catalog differs from replay')
    return Workbench(canonical(dict(kind='metal-workbench-snapshot', schema_version=1, protocol=PROTOCOL,
                                   catalog=rebuilt, rows=rows, details=details,
                                   scientific_acceptance='NOT_ASSESSED', automatic_checkpoint_selection=False)))


@dataclass(frozen=True)
class Workbench:
    """In-memory verified snapshot. Reopen to refresh/check source availability.

    All returned values are detached copies. Navigation performs no file writes,
    native calls, checkpoint adoption, ranking, or scientific parameter changes.
    """
    _json: str = field(repr=False)

    def to_dict(self):
        return json.loads(self._json)

    def initial_selection(self):
        return dict(kind='metal-workbench-selection', schema_version=1,
                    catalog_id=self.to_dict()['catalog']['catalog_id'], **{k: None for k in LEVELS})

    def _context(self, selection):
        _fields(selection, set(self.initial_selection()), 'selection')
        empty = self.initial_selection()
        if (type(selection['schema_version']) is not int or
                any(selection[k] != empty[k] for k in ('kind', 'schema_version', 'catalog_id'))):
            raise RecipeError('Selection belongs to a different catalog or schema')
        for key in LEVELS:
            if selection[key] is not None and not isinstance(selection[key], str):
                raise RecipeError('Selection identifiers must be strings or null')
        catalog = self.to_dict()['catalog']
        options = dict(dataset_id=catalog['datasets'], structure_id=[], hypothesis_id=[], site_id=[], result_id=[])
        active = {}
        for level, child in [('dataset_id', 'structures'), ('structure_id', 'hypotheses'),
                              ('hypothesis_id', None)]:
            selected = selection[level]
            if selected is None:
                if any(selection[k] is not None for k in LEVELS[LEVELS.index(level)+1:]):
                    raise RecipeError('Selection requires its explicit parent scope')
                break
            match = next((item for item in options[level] if item[level] == selected), None)
            if match is None:
                raise RecipeError('Unknown selection: ' + level)
            active[level] = match
            if child:
                options[LEVELS[LEVELS.index(level)+1]] = match[child]
            else:
                options['site_id'], options['result_id'] = match['sites'], match['results']
        for level in ('site_id', 'result_id'):
            if selection[level] is not None:
                match = next((item for item in options[level] if item[level] == selection[level]), None)
                if match is None:
                    raise RecipeError('Unknown selection: ' + level)
                active[level] = match
        rows = self.to_dict()['rows']
        rows = [r for r in rows if all(selection[k] is None or r[k] == selection[k]
                for k in ('dataset_id', 'structure_id', 'hypothesis_id', 'result_id'))
                and (selection['site_id'] is None or selection['site_id'] in r['site_ids'])]
        if selection['row_id'] is not None:
            if selection['result_id'] is None or not any(r['row_id'] == selection['row_id'] for r in rows):
                raise RecipeError('Row selection does not belong to its current scope')
        return options, active, rows

    def select(self, selection, field, value):
        """Change one scope; clear dependent selections while keeping sibling scope."""
        self._context(selection)
        if field not in LEVELS[:-1]:
            raise RecipeError('Use select_row for a linked result row')
        new = dict(selection)
        if new[field] == value:
            return new
        new[field] = value
        if field in LEVELS[:3]:
            for key in LEVELS[LEVELS.index(field)+1:]:
                new[key] = None
        else:
            new['row_id'] = None
        self._context(new)
        return new

    def select_row(self, selection, row_id, *, site_id=None):
        """Navigate to a row's exact parents; resolve overlapping groups explicitly."""
        self._context(selection)
        row = next((r for r in self.to_dict()['rows'] if r['row_id'] == row_id), None)
        if row is None:
            raise RecipeError('Unknown workbench row')
        new = self.initial_selection()
        for key in ('dataset_id', 'structure_id', 'hypothesis_id', 'result_id', 'row_id'):
            new[key] = row[key]
        if site_id is not None:
            if site_id not in row['site_ids']:
                raise RecipeError('Row does not belong to the requested site')
            new['site_id'] = site_id
        elif (all(selection[k] == new[k] for k in LEVELS[:3])
              and selection['site_id'] in row['site_ids']):
            new['site_id'] = selection['site_id']
        elif len(row['site_ids']) == 1:
            new['site_id'] = row['site_ids'][0]
        self._context(new)
        return new

    def view(self, selection):
        """Return linked options, visible rows and unaltered saved result reports."""
        options, _, rows = self._context(selection)
        details = [d for d in self.to_dict()['details'] if all(selection[k] is None or d.get(k) == selection[k]
                   for k in ('dataset_id', 'structure_id', 'hypothesis_id'))
                   and ('result_id' not in d or selection['result_id'] is None or d['result_id'] == selection['result_id'])]
        return dict(kind='metal-workbench-view', schema_version=1, protocol=PROTOCOL,
                    selection=dict(selection), options={k: [{k: r[k], 'label': r['label']} for r in v]
                                                       for k, v in options.items()},
                    rows=rows, details=details,
                    selected_row=next((r for r in rows if r['row_id'] == selection['row_id']), None),
                    scientific_acceptance='NOT_ASSESSED', automatic_checkpoint_selection=False)
