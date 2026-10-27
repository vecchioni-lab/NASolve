"""Immutable metal-only recipe preparation with bounded moves and exact replay."""
from pathlib import Path
import math
import re

from .binding import AtomKey, ResidueKey, RoleMap
from .context import _reference, parse_pdb
from .export import export_restraints
from .geometry_solver import Problem
from .materialize import _json, _json_bytes, _source, verify_hypothesis
from .preview import preview
from .recipe import Recipe, RecipeError, canonical, digest, number, _fields


PROTOCOL = 'metal-recipe-geometry-v1'
FILES = {'parameters': 'parameters.json', 'result': 'result.json', 'model': 'model.pdb',
         'preview': 'preview.json', 'restraints': 'restraints.phil'}


def _parameters(parent, value):
    _fields(value, {'mobile_nodes', 'max_iterations', 'max_shift_A'}, set(), 'geometry parameters')
    metals = {s['node_id'] for s in parent['sites']}
    available = metals - set(parent['unrestrained_metal_nodes'])
    mobile = value['mobile_nodes']
    if (not isinstance(mobile, list) or not mobile or len(mobile) > 12
            or any(not isinstance(n, str) for n in mobile) or len(set(mobile)) != len(mobile)
            or set(mobile) - available):
        raise RecipeError('Select 1 to 12 distinct restrained metal nodes; floating sites stay fixed')
    iterations = value['max_iterations']
    if type(iterations) is not int or not 1 <= iterations <= 300:
        raise RecipeError('Require 1 to 300 geometry iterations')
    shift = number(value['max_shift_A'], 'max_shift_A')
    if not .001 <= shift <= 5.:
        raise RecipeError('Require a metal displacement limit between 0.001 and 5 angstrom')
    return dict(mobile_nodes=sorted(mobile), max_iterations=iterations, max_shift_A=shift)


def _serialize(raw, problem, x):
    indices = {index: x[3*i:3*i+3] for i, index in enumerate(problem.mobile)}
    lines = raw.decode('ascii').splitlines(keepends=True)
    atom_index = 0
    for i, line in enumerate(lines):
        if line[:6].strip() not in {'ATOM', 'HETATM'}:
            continue
        if atom_index in indices:
            fields = ''.join(f'{v:8.3f}' for v in indices[atom_index])
            if len(fields) != 24:
                raise RecipeError('Prepared coordinates exceed PDB width')
            lines[i] = line[:30] + fields + line[54:]
        atom_index += 1
    result = ''.join(lines).encode('ascii')
    before, after = parse_pdb(raw), parse_pdb(result)
    if before.to_dict()['atomic_state'] != after.to_dict()['atomic_state']:
        raise RecipeError('Geometry preparation changed atomic state')
    for i, (a, b) in enumerate(zip(before.snapshot.atoms, after.snapshot.atoms)):
        if a.key != b.key or a.element != b.element or (i not in indices and a != b):
            raise RecipeError('Geometry preparation changed a fixed atom')
    return result


def _preview(parent_preview, model):
    inputs = parent_preview['inputs']
    roles = inputs['roles']
    roles = RoleMap(roles['records'], source_sha256=roles['source_sha256'], source_label=roles['source_label'])
    result = preview(Recipe(inputs['recipe']), model=parse_pdb(model).snapshot, roles=roles,
                     residue_slots={k: ResidueKey(**v) for k, v in inputs['residue_slots'].items()},
                     atom_bindings={k: AtomKey(**v) for k, v in inputs['atom_bindings'].items()})
    result['context_id'] = parent_preview['context_id']
    return result


def _prepare(run, parent, parameters):
    parameters = _parameters(parent, parameters)
    source = _source(parent['files']['model'], run)
    parent_preview = _json(_source(parent['files']['preview'], run))
    problem = Problem(parent_preview, parameters['mobile_nodes'])
    if len(problem.rows) > 256:
        raise RecipeError('Recipe geometry supports at most 256 active restraints')
    initial = problem.summary(problem.start)
    x, optimization = problem.optimize(parameters['max_iterations'], parameters['max_shift_A'])
    full_precision = problem.summary(x)
    candidate = _serialize(source, problem, x)
    imported = parse_pdb(candidate)
    rounded = [v for i in problem.mobile for v in imported.snapshot.atoms[i].xyz]
    reason = None
    shifts = [math.dist(problem.start[i:i+3], rounded[i:i+3]) for i in range(0, len(x), 3)]
    if max(shifts) > parameters['max_shift_A'] + 1e-12:
        reason = 'PDB_ROUNDING_EXCEEDS_DISPLACEMENT_LIMIT'
    for index in problem.mobile:
        if any(index != j and math.dist(imported.snapshot.atoms[index].xyz, a.xyz) < 1e-6
               for j, a in enumerate(imported.snapshot.atoms)):
            reason = 'COINCIDENT_SERIALIZED_SITE'
    try:
        rounded_summary = problem.summary(rounded)
    except RecipeError:
        rounded_summary = None
        reason = 'UNDEFINED_SERIALIZED_GEOMETRY'
    if reason is None and rounded_summary['objective'] > initial['objective']:
        reason = 'SERIALIZED_OBJECTIVE_INCREASE'
    if reason is None and candidate == source:
        reason = 'NO_SERIALIZED_CHANGE'
    model = source if reason is not None else candidate
    final_x = problem.start if reason is not None else rounded
    final_preview = _preview(parent_preview, model)
    selection = 'parent_coordinates' if reason is not None else 'proposed_metal_coordinates'
    result = {'objective_scope': 'enabled_recipe_distances_and_angles_only',
              'selection': selection, 'retained_parent_reason': reason,
              'initial': initial, 'full_precision': full_precision,
              'rounded_candidate': rounded_summary, 'selected': problem.summary(final_x),
              'optimization': optimization,
              'full_precision_mobile_xyz': [x[i:i+3] for i in range(0, len(x), 3)],
              'selected_metal_shifts_A': {n: math.dist(problem.start[3*i:3*i+3], final_x[3*i:3*i+3])
                                        for i, n in enumerate(parameters['mobile_nodes'])},
              'fixed_state': 'all other XYZ; all occupancy, B and ANISOU; elements and identities',
              'inherited_restraints': 'preserved through parent; not in this objective',
              'chemical_qualification': 'NOT_ASSESSED', 'native_execution': 'NOT_RUN',
              'diffraction_refinement': 'NOT_RUN', 'automatic_checkpoint_selection': False}
    return {'parameters': _json_bytes(parameters), 'result': _json_bytes(result), 'model': model,
            'preview': _json_bytes(final_preview), 'restraints': export_restraints(final_preview).encode()}


def _manifest(run, directory, parent_ref, parent, content):
    result = _json(content['result'])
    doc = {'kind': 'metal-geometry-trial', 'schema_version': 1, 'protocol': PROTOCOL,
           'status': 'GEOMETRY_REVIEW', 'native_ready': False,
           'parent': dict(parent['parent'], hypothesis_id=parent['hypothesis_id'], manifest=parent_ref),
           'inputs': parent['inputs'], 'selection': result['selection'],
           'files': {key: _reference(directory/name, run) for key, name in FILES.items()}}
    doc['geometry_id'] = digest(doc)
    return doc


def _allocate(run):
    root = run/'Metal'
    if root.is_symlink():
        raise RecipeError('Metal output directory must not be a symlink')
    numbers = [int(m.group(1)) for p in root.iterdir() if (m := re.fullmatch(r'geometry_(\d{3,})', p.name))]
    index = max(numbers, default=0) + 1
    while True:
        directory = root/f'geometry_{index:03d}'
        try:
            directory.mkdir()
            return directory
        except FileExistsError:
            index += 1


def prepare_geometry(run, hypothesis, *, mobile_nodes=None, max_iterations=100, max_shift_A=1.):
    """Prepare a new metal-only review trial; never select a run checkpoint.

    Default mobile sites are all restrained metals. Explicit selections permit
    locking other sites. Floating sites cannot move without a declared target.
    """
    run = Path(run).expanduser().resolve()
    parent = verify_hypothesis(run, hypothesis)
    parent_path = run/Path(parent['files']['model']['relative_path']).parent/'manifest.json'
    parent_ref = _reference(parent_path, run)
    if mobile_nodes is None:
        mobile_nodes = sorted({s['node_id'] for s in parent['sites']} - set(parent['unrestrained_metal_nodes']))
    parameters = dict(mobile_nodes=mobile_nodes, max_iterations=max_iterations, max_shift_A=max_shift_A)
    content = _prepare(run, parent, parameters)
    directory = _allocate(run)
    try:
        for key, name in FILES.items():
            with (directory/name).open('xb') as handle:
                handle.write(content[key])
        _source(parent_ref, run)
        verify_hypothesis(run, parent_path.parent)
        result = _manifest(run, directory, parent_ref, parent, content)
        with (directory/'manifest.json').open('xb') as handle:
            handle.write(_json_bytes(result))
        return result
    except Exception as exc:
        with (directory/'failure.json').open('xb') as handle:
            handle.write(_json_bytes({'status': 'FAILED', 'error': str(exc)}))
        raise


def verify_geometry(run, directory):
    """Replay current trusted code and captured inputs, without a native job."""
    run = Path(run).expanduser().resolve()
    directory = Path(directory).expanduser()
    if not directory.is_absolute():
        directory = run/directory
    if directory.is_symlink() or directory.parent.is_symlink():
        raise RecipeError('Geometry directory must not be a symlink')
    directory = directory.resolve()
    if directory.parent != run/'Metal' or not re.fullmatch(r'geometry_[0-9]{3,}', directory.name):
        raise RecipeError('Require an explicit numbered geometry trial in this run')
    try:
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
            raise RecipeError('Geometry artifacts must be regular files, not symlinks')
        if {p.name for p in directory.iterdir()} != {'manifest.json', *FILES.values()}:
            raise RecipeError('Failed or unexpected geometry file inventory')
        doc = _json((directory/'manifest.json').read_bytes())
        parent_ref = doc['parent']['manifest']
        _source(parent_ref, run)
        if parent_ref.get('anchor') != 'run':
            raise RecipeError('Geometry parent must be in this run')
        parent_path = run/parent_ref['relative_path']
        parent = verify_hypothesis(run, parent_path.parent)
        if parent_ref != _reference(parent_path.parent/'manifest.json', run):
            raise RecipeError('Unexpected hypothesis manifest reference')
        if set(doc['files']) != set(FILES):
            raise RecipeError('Unexpected geometry files')
        content = {}
        for key, name in FILES.items():
            path = directory/name
            if path.is_symlink() or doc['files'][key] != _reference(path, run):
                raise RecipeError('Geometry file path or checksum changed')
            content[key] = _source(doc['files'][key], run)
        replayed = _prepare(run, parent, _json(content['parameters']))
        if content != replayed or canonical(doc) != canonical(_manifest(run, directory, parent_ref, parent, content)):
            raise RecipeError('Geometry differs from exact derivation replay')
        return doc
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError(f'Cannot verify geometry: {exc}') from exc
