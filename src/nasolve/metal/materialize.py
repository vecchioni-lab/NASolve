"""Add explicit metal sites in independent, replayable review bundles.

No coordinate inference, optimization, checkpoint adoption or native job occurs.
The parent atomic records are retained verbatim. Serialized coordinates, not
unrounded requested values, own every exported restraint and downstream preview.
"""
import hashlib
import json
import math
from pathlib import Path
import re

from ..run_context import resolve_artifact_path
from .binding import AtomKey, RoleMap
from .context import MetalContext, _reference, parse_pdb
from .export import export_restraints
from .recipe import Recipe, RecipeError, canonical, checksum, digest, number, text, _fields, _json_object


FILES = {'context': 'parent-context.json', 'report': 'parent-report.json',
         'recipe': 'recipe.json', 'placement': 'placement.json', 'model': 'model.pdb',
         'preview': 'preview.json', 'restraints': 'restraints.phil'}
PROTOCOL = 'metal-materialization-v1'


def _json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_json_object)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise RecipeError(f'Invalid hypothesis JSON: {exc}') from exc


def _json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def _source(ref, run):
    if not isinstance(ref, dict) or ref.get('anchor') not in {'run', 'dataset', 'repository'}:
        raise RecipeError('Hypothesis inputs require declared portable anchors')
    checksum(ref.get('sha256'), 'input checksum')
    path = resolve_artifact_path(ref, run)
    if path is None:
        raise RecipeError('Hypothesis input missing or checksum changed')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref['sha256'] or len(raw) != ref.get('size'):
        raise RecipeError('Hypothesis input changed during read')
    return raw


def _sources(context, *, report=None):
    sources = context.to_dict()['sources']
    model = _source(sources['model'], context.run)
    _source(sources['observations'], context.run)
    for ref in sources['restraints'] + ([sources['phases']] if sources['phases'] else []):
        _source(ref, context.run)
    if report is None:
        report = _source(sources['report'], context.run)
    if hashlib.sha256(report).hexdigest() != sources['report']['sha256']:
        raise RecipeError('Frozen parent report checksum changed')
    return model, report


def _plan(value, context, recipe):
    doc = _json(canonical(value))
    _fields(doc, {'kind', 'schema_version', 'context_id', 'recipe_sha256', 'sites', 'atoms'}, set(), 'placement')
    if doc['kind'] != 'metal-placement-plan' or type(doc['schema_version']) is not int or doc['schema_version'] != 1:
        raise RecipeError('Unsupported placement schema')
    if doc['context_id'] != context.to_dict()['context_id'] or doc['recipe_sha256'] != recipe.sha256:
        raise RecipeError('Placement belongs to a different context or recipe')
    metals = {n['id']: n['element'] for n in recipe.to_dict()['nodes'] if n['kind'] == 'metal'}
    if not metals or not isinstance(doc['sites'], list):
        raise RecipeError('Require at least one explicitly placed metal node')
    seen = set()
    model_ids = {a.key.model_id for a in context.imported.snapshot.atoms}
    occupied = {(a.key.chain_id.casefold(), a.key.residue_id) for a in context.imported.snapshot.atoms}
    for row in doc['sites']:
        _fields(row, {'node_id', 'key', 'xyz', 'occupancy', 'b_iso', 'formal_charge', 'source_note'}, set(), 'site')
        node = row['node_id']
        if not isinstance(node, str) or node not in metals or node in seen:
            raise RecipeError('Duplicate or unknown placed metal node')
        seen.add(node)
        try:
            key = AtomKey(**row['key'])
        except (TypeError, ValueError) as exc:
            raise RecipeError(f'Invalid placed atom identity: {exc}') from exc
        symbol = metals[node].upper()
        if (model_ids != {key.model_id} or key.symmetry != 'x,y,z'
                or not re.fullmatch(r'[A-Za-z0-9]', key.chain_id)
                or not re.fullmatch(r'[1-9][0-9]{0,3}', key.residue_id)
                or key.component_id != symbol or key.atom_name != symbol
                or key.altloc or key.insertion_code or key.segment_id):
            raise RecipeError('New sites require one canonical monatomic PDB residue, identity symmetry and no alternate/insertion/segment')
        identity = (key.chain_id.casefold(), key.residue_id)
        if identity in occupied:
            raise RecipeError('New site collides with an occupied residue identity')
        occupied.add(identity)
        row['key'] = key.to_dict()
        if not isinstance(row['xyz'], list) or len(row['xyz']) != 3:
            raise RecipeError('Require three Cartesian coordinates')
        row['xyz'] = [number(v, 'coordinate') for v in row['xyz']]
        if any(len(f'{v:8.3f}') != 8 for v in row['xyz']):
            raise RecipeError('Coordinate exceeds PDB field width')
        for field, maximum in [('occupancy', 1), ('b_iso', 999.99)]:
            value = number(row[field], field)
            if not 0 <= value <= maximum or not math.isclose(value, round(value, 2), rel_tol=0, abs_tol=1e-9):
                raise RecipeError(f'{field} requires a nonnegative, PDB-representable value within {maximum}')
            row[field] = value
        charge = row['formal_charge']
        if charge is not None and (type(charge) is not int or not -9 <= charge <= 9):
            raise RecipeError('formal_charge requires null or an integer from -9 to 9')
        text(row['source_note'], 'placement source_note')
    if seen != metals.keys():
        raise RecipeError('Every recipe metal requires an explicit placement')
    allowed = {n['id'] for n in recipe.to_dict()['nodes'] if n['kind'] == 'atom'}
    if not isinstance(doc['atoms'], dict) or doc['atoms'].keys() - allowed:
        raise RecipeError('Concrete bindings may name only atom nodes')
    try:
        doc['atoms'] = {k: AtomKey(**v).to_dict() for k, v in doc['atoms'].items()}
    except (TypeError, ValueError) as exc:
        raise RecipeError(f'Invalid concrete binding: {exc}') from exc
    return doc


def _render(raw, plan, recipe):
    if not raw.endswith(b'\n'):
        raise RecipeError('Source PDB must have newline-terminated records')
    lines = raw.decode('ascii').splitlines(keepends=True)
    kinds = [line[:6].strip() for line in lines]
    if 'MASTER' in kinds:
        raise RecipeError('PDB MASTER records require a qualified count-updating serializer')
    serials = []
    for line, kind in zip(lines, kinds):
        if kind in {'ATOM', 'HETATM', 'TER', 'ANISOU'}:
            if kind == 'TER' and not line[6:11].strip():
                continue  # ReadySet emits legal bare TER records.
            try:
                serials.append(int(line[6:11]))
            except ValueError as exc:
                raise RecipeError('Only decimal PDB serials are supported') from exc
    serial = max(serials, default=0)
    if serial < 0 or serial + len(plan['sites']) > 99999:
        raise RecipeError('No decimal PDB serials available for new sites')
    symbols = {n['id']: n['element'].upper() for n in recipe.to_dict()['nodes'] if n['kind'] == 'metal'}
    added = []
    for offset, row in enumerate(plan['sites'], 1):
        key = row['key']; xyz = row['xyz']; symbol = symbols[row['node_id']]
        charge = row['formal_charge']
        charge_text = '' if charge is None or charge == 0 else f'{abs(charge)}' + ('+' if charge > 0 else '-')
        added.append(f'HETATM{serial+offset:5d} {key["atom_name"]:>4s} {key["component_id"]:>3s} {key["chain_id"]}{int(key["residue_id"]):4d}    '
                     f'{xyz[0]:8.3f}{xyz[1]:8.3f}{xyz[2]:8.3f}{row["occupancy"]:6.2f}{row["b_iso"]:6.2f}          {symbol:>2s}{charge_text:>2s}\n')
    # Keep terminal records and all existing lines in their original order.
    index = next((i for i, kind in enumerate(kinds) if kind in {'ENDMDL', 'CONECT', 'END'}), len(lines))
    return ''.join(lines[:index] + added + lines[index:]).encode('ascii')


def _prepare(context, recipe, value, *, report=None):
    parent = context.to_dict()
    if (parent.get('kind') != 'metal-run-context' or type(parent.get('schema_version')) is not int
            or parent['schema_version'] != 1 or parent.get('protocol') != 'metal-run-context-v1'
            or parent.get('frame') != 'W' or parent.get('roles') != context.roles.to_dict()):
        raise RecipeError('Unsupported or inconsistent parent context')
    identity = dict(parent); identifier = identity.pop('context_id')
    if digest(identity) != identifier:
        raise RecipeError('Parent context fingerprint changed')
    raw, report = _sources(context, report=report)
    imported = parse_pdb(raw, checkpoint_id=parent['checkpoint_id'])
    if imported.to_dict() != context.imported.to_dict() or any(parent[k] != imported.to_dict()[k] for k in ('model', 'atomic_state')):
        raise RecipeError('Parent inventory differs from captured source')
    plan = _plan(value, context, recipe)
    model = _render(raw, plan, recipe)
    derived = parse_pdb(model)
    n = len(imported.snapshot.atoms)
    if (derived.snapshot.atoms[:n] != imported.snapshot.atoms
            or derived.to_dict()['atomic_state'][:n] != imported.to_dict()['atomic_state']):
        raise RecipeError('Materialization changed parent atomic state')
    coordinates = [a.xyz for a in derived.snapshot.atoms[:n]]
    for atom in derived.snapshot.atoms[n:]:
        if atom.xyz in coordinates:
            raise RecipeError('A serialized metal site coincides with another atom')
        coordinates.append(atom.xyz)
    # Reuse exact W role binding on the actual serialized output, without
    # pretending that this review artifact is a selected checkpoint.
    derived_context = MetalContext(context.run, derived, context.roles, context._document)
    bindings = {k: AtomKey(**v) for k, v in plan['atoms'].items()}
    bindings.update({row['node_id']: AtomKey(**row['key']) for row in plan['sites']})
    result = derived_context.preview(recipe, atom_bindings=bindings)
    if any(row['issues'] for row in result['nodes']):
        raise RecipeError('All hypothesis nodes must resolve to exact atoms')
    active = [r for r in result['restraints'] if r['enabled']]
    phil = export_restraints(result) if active else '# Unrestrained hypothesis; no recipe edits.\nrefinement.geometry_restraints.edits {}\n'
    sites = []
    for requested, atom, state in zip(plan['sites'], derived.snapshot.atoms[n:], derived.to_dict()['atomic_state'][n:]):
        sites.append({'node_id': requested['node_id'], 'key': atom.key.to_dict(), 'element': atom.element,
                      'xyz': list(atom.xyz), 'occupancy': state['occupancy'], 'b_iso': state['b_iso'],
                      'formal_charge': requested['formal_charge'],
                      'coordinate_rounding_A': [a-b for a, b in zip(atom.xyz, requested['xyz'])]})
    coverage = {node for row in active for node in row['node_ids']}
    unrestrained = sorted(row['node_id'] for row in sites if row['node_id'] not in coverage)
    content = {'context': _json_bytes(parent), 'report': report, 'recipe': recipe.to_json().encode(),
               'placement': _json_bytes(plan), 'model': model, 'preview': _json_bytes(result), 'restraints': phil.encode()}
    return content, sites, unrestrained


def _manifest(context, directory, sites, unrestrained):
    parent = context.to_dict()
    refs = {key: _reference(directory / name, context.run) for key, name in FILES.items()}
    sources = dict(parent['sources'], report=refs['report'])
    doc = {'kind': 'metal-hypothesis', 'schema_version': 1, 'protocol': PROTOCOL,
           'status': 'BUILT_REVIEW', 'native_ready': False,
           'parent': {key: parent[key] for key in ('context_id', 'dataset_id', 'run_id', 'checkpoint_id')},
           'inputs': sources, 'files': refs, 'sites': sites, 'unrestrained_metal_nodes': unrestrained}
    doc['hypothesis_id'] = digest(doc)
    return doc


def _allocate(run):
    root = run / 'Metal'
    if root.is_symlink():
        raise RecipeError('Metal output directory must not be a symlink')
    root.mkdir(exist_ok=True)
    numbers = [int(m.group(1)) for p in root.iterdir() if (m := re.fullmatch(r'hypothesis_(\d{3,})', p.name))]
    number = max(numbers, default=0) + 1
    while True:
        directory = root / f'hypothesis_{number:03d}'
        try:
            directory.mkdir()
            return directory
        except FileExistsError:
            number += 1


def build_hypothesis(context: MetalContext, recipe: Recipe, placement: dict) -> dict:
    """Write one new review bundle. Invalid proposals allocate no directory.

    A failed write retains its numbered directory and cannot be mistaken for a
    completed hypothesis. No existing artifact or current pointer is rewritten.
    """
    content, sites, unrestrained = _prepare(context, recipe, placement)
    directory = _allocate(context.run)
    try:
        for key, name in FILES.items():
            with (directory / name).open('xb') as handle:
                handle.write(content[key])
        _sources(context)  # Recheck parent inputs immediately before publication.
        result = _manifest(context, directory, sites, unrestrained)
        with (directory / 'manifest.json').open('xb') as handle:
            handle.write(_json_bytes(result))
        return result
    except Exception as exc:
        with (directory / 'failure.json').open('x') as handle:
            json.dump({'status': 'FAILED', 'error': str(exc)}, handle)
        raise


def verify_hypothesis(run, directory) -> dict:
    """Verify exact sources, captured roles and replayed bytes without a job.

    The parent report is a frozen local snapshot: subsequent parent-stage status
    updates do not invalidate this hypothesis. Scientific inputs remain checked
    through their declared anchors. No live role workbook is consulted.
    """
    run = Path(run).expanduser().resolve()
    directory = Path(directory).expanduser()
    if not directory.is_absolute():
        directory = run / directory
    if directory.is_symlink() or directory.parent.is_symlink():
        raise RecipeError('Hypothesis directory must not be a symlink')
    directory = directory.resolve()
    if directory.parent != run / 'Metal' or not re.fullmatch(r'hypothesis_[0-9]{3,}', directory.name):
        raise RecipeError('Require an explicit numbered hypothesis in this run')
    try:
        if (directory / 'failure.json').exists():
            raise RecipeError('Hypothesis publication failed; retained files are diagnostic only')
        result = _json((directory / 'manifest.json').read_bytes())
        refs = result['files']
        if set(refs) != set(FILES):
            raise RecipeError('Unexpected hypothesis file inventory')
        content = {}
        for key, name in FILES.items():
            if (directory / name).is_symlink() or refs[key] != _reference(directory / name, run):
                raise RecipeError('Hypothesis artifact path or checksum changed')
            content[key] = _source(refs[key], run)
        parent = _json(content['context'])
        if parent['kind'] != 'metal-run-context' or parent['schema_version'] != 1 or parent['protocol'] != 'metal-run-context-v1':
            raise RecipeError('Unsupported parent context schema')
        imported = parse_pdb(_source(parent['sources']['model'], run), checkpoint_id=parent['checkpoint_id'])
        roles = parent['roles']
        context = MetalContext(run, imported, RoleMap(roles['records'], source_sha256=roles['source_sha256'], source_label=roles['source_label']), canonical(parent))
        replayed, sites, unrestrained = _prepare(context, Recipe.from_json(content['recipe']), _json(content['placement']), report=content['report'])
        if replayed != content or canonical(result) != canonical(_manifest(context, directory, sites, unrestrained)):
            raise RecipeError('Hypothesis differs from exact derivation replay')
        return result
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError(f'Cannot verify hypothesis: {exc}') from exc
