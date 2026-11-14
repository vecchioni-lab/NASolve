"""Plan declaration-based torsion omissions across an ordered explicit bundle.

No native process executes here. The separate numerical chain gate reuses exact
single-component inventory/energy gates; callers must authenticate captures and
kernel execution before supplying their inventories and numerical references.
"""
from pathlib import Path
import math
import tempfile

from .cif_mixed_geometry import _ref as _reference, _load, _dump
from .cif_fana_junction import _path
from .ligand_profiles import dictionary_component_codes
from .cif_stereochemistry_audit import _values, _graph
from .cif_linear_torsion_candidate import T, _columns, _linear_triples, prepare_linear_torsion_candidate
from .cif_triple_bond_audit import _key, _rows
from .cif_linked_linear_torsion import _exact
from .cif_captured_mixed_gradients import _inputs as _captured_inputs

POLICY_ID = 'cif-declared-linear-torsion-bundle-v1'
REPORT = 'linear_torsion_bundle.json'
ANCHOR = 'linear_torsion_bundle_directory'
MAX_DICTIONARIES, MAX_COMPONENTS, MAX_STEPS = 64, 128, 32


def _need(value):
    if not value:
        raise ValueError('Linear torsion bundle evidence does not reproduce')


def _ref(path, root):
    return _reference(path, root, ANCHOR)


def _codes(codes):
    _need(isinstance(codes, (list, tuple)) and 1 <= len(codes) <= MAX_COMPONENTS
          and all(isinstance(c, str) and c and c == c.strip() for c in codes)
          and len(set(codes)) == len(codes))
    return sorted(codes)


def _graph_checked(values):
    a, b = '_chem_comp_atom.', '_chem_comp_bond.'
    _columns(values, a, ['atom_id', 'type_symbol'])
    _columns(values, b, ['atom_id_1', 'atom_id_2'])
    ids = values[a+'atom_id']
    pairs = [tuple(sorted(p)) for p in zip(values[b+'atom_id_1'], values[b+'atom_id_2'])]
    _need(len(ids) == len(set(ids)) and len(pairs) == len(set(pairs))
          and all(x != y and x in ids and y in ids for x, y in pairs))
    return _graph(values)


def _build(paths, codes, root):
    root.mkdir(parents=True, exist_ok=True)
    inputs = []
    for i, path in enumerate(paths):
        out = root/'inputs'/f'{i:03d}.cif';out.parent.mkdir(exist_ok=True)
        out.write_bytes(path.read_bytes());inputs.append(_ref(out, root))
    current = [root/r['path'] for r in inputs]
    providers = {c: [] for c in codes}
    for i, path in enumerate(current):
        for c in dictionary_component_codes(path) & set(codes):providers[c].append(i)
    _need(all(len(v) <= 1 for v in providers.values()))
    scans, selected = {}, []
    for code in codes:
        indices = providers[code]
        if not indices:
            scans[code] = {'component':code, 'status':'NO_EXPLICIT_DICTIONARY'}
            continue
        i = indices[0]; values = _values(current[i], code)
        graph = _graph_checked(values)
        row = {'component':code, 'dictionary_index':i, 'status':'NO_DECLARED_TRIPLE'}
        if 'TRIPLE' in graph[1].values():
            linear, _ = _linear_triples(values)
            row['declared_linear_angles'] = linear
            keys = {_key(r['atoms']) for r in linear}
            torsion_columns = {k:v for k,v in values.items() if k.startswith(T)}
            if torsion_columns:
                _columns(values, T, ['comp_id','id','atom_id_1','atom_id_2','atom_id_3','atom_id_4','value_angle','value_angle_esd','period'])
            matching = [r for r in _rows(values, 'tor', 4)
                        if any(_key(r['atoms'][j:j+3]) in keys for j in (0, 1))]
            row['status'] = 'PLANNED' if matching else 'NO_MATCHING_TORSIONS'
            if matching:selected.append((i, code))
        scans[code] = row
    _need(len(selected) <= MAX_STEPS)
    steps = []
    for ordinal, (i, code) in enumerate(sorted(selected)):
        source = current[i];candidate = root/'steps'/f'{ordinal:03d}.cif'
        before = [_ref(p, root) for p in current]
        plan = prepare_linear_torsion_candidate(source, code, candidate)
        current[i] = candidate
        steps.append({'ordinal':ordinal, 'dictionary_index':i, 'component':code,
                      'source':_ref(source, root), 'candidate':_ref(candidate, root), 'plan':plan,
                      'dictionaries_before':before, 'dictionaries_after':[_ref(p, root) for p in current]})
    report = {'schema_version':1, 'policy_id':POLICY_ID,
              'status':'CANDIDATE_REVIEW' if steps else 'NO_CANDIDATE',
              'modeled_components':codes, 'inputs':inputs, 'scan':[scans[c] for c in codes],
              'steps':steps, 'final_dictionaries':[_ref(p, root) for p in current],
              'selection':'EXPLICIT_GRAPH_AND_LINEAR_TARGETS; NO_COORDINATES_OR_COMPONENT_ALLOWLIST',
              'bounds':{'dictionaries':MAX_DICTIONARIES, 'components':MAX_COMPONENTS, 'steps':MAX_STEPS},
              'native_qualification':'NOT_RUN', 'derivative_qualification':'NOT_RUN',
              'chemical_qualification':'NOT_ASSESSED', 'automatic_adoption':False,
              'model_editing':'NOT_RUN', 'optimization':'NOT_RUN', 'installed_library_editing':'NOT_RUN'}
    report['outputs'] = [_ref(p, root) for p in sorted(root.rglob('*')) if p.is_file()]
    report['directories'] = sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())
    return report


def prepare_linear_torsion_bundle(dictionaries, modeled_components, output):
    """Freeze inputs and every intermediate candidate; refuse before reservation.

    Explicit modeled providers are scanned. Components supplied only by the
    installed library are recorded as unassessed, never rewritten or called clean.
    Ambiguous providers or unsupported declared-linear chemistry refuse the plan.
    """
    _need(isinstance(dictionaries, (list, tuple)) and 1 <= len(dictionaries) <= MAX_DICTIONARIES)
    paths = [_path(p) for p in dictionaries];codes = _codes(modeled_components)
    _need(len(set(paths)) == len(paths))
    root = Path(output).expanduser().absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root, *root.parents])
          and not any(p.is_relative_to(root) for p in paths))
    originals = [p.read_bytes() for p in paths]
    with tempfile.TemporaryDirectory(prefix='linear-bundle-preflight-') as temporary:
        staging = Path(temporary).resolve();report = _build(paths, codes, staging)
        _need([p.read_bytes() for p in paths] == originals)
        root.mkdir(parents=True, exist_ok=False)
        for ref in report['outputs']:
            destination = root/ref['path'];destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:stream.write((staging/ref['path']).read_bytes())
    _dump(root/REPORT, report)
    _need([p.read_bytes() for p in paths] == originals)
    return read_linear_torsion_bundle(root)


def read_linear_torsion_bundle(directory):
    """Rebuild all candidate bytes and the complete plan without original paths."""
    try:
        root = _path(directory, directory=True)
        _need(not any(p.is_symlink() for p in [root, *root.parents])
              and not any(p.is_symlink() for p in root.rglob('*')))
        report = _load(root/REPORT);codes = _codes(report['modeled_components']);refs = report['inputs']
        _need(isinstance(refs, list) and 1 <= len(refs) <= MAX_DICTIONARIES)
        paths = []
        for i, ref in enumerate(refs):
            path = root/'inputs'/f'{i:03d}.cif';_need(_ref(path, root) == ref);paths.append(path)
        with tempfile.TemporaryDirectory(prefix='linear-bundle-replay-') as temporary:
            replay = Path(temporary).resolve();derived = _build(paths, codes, replay)
            _need(_exact(report, derived))
            for ref in derived['outputs']:_need(_ref(root/ref['path'], root) == ref)
        _need({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
              == {r['path'] for r in report['outputs']} | {REPORT})
        _need(sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()) == report['directories'])
        return report
    except (KeyError, TypeError, IndexError, OverflowError) as exc:
        raise ValueError('Incomplete linear torsion bundle') from exc


def qualify_linear_torsion_bundle(directory, inventories, references):
    """Require exact inventory and energy attribution for every consecutive step.

    These are pure numerical/inventory gates. The caller must authenticate native
    captures against each ordered bundle, identical model/PHIL/namespace/consumer,
    and the execution/source pins that produced the single-proxy references.
    """
    from .cif_linked_torsion_energy import qualify_linked_torsion_energy
    root = _path(directory, directory=True);report = read_linear_torsion_bundle(root)
    steps = report['steps']
    _need(bool(steps) and isinstance(inventories, list) and isinstance(references, list)
          and len(inventories) == len(steps)+1 and len(references) == len(steps))
    try:
        modeled = sorted({a['identity']['resname'].strip() for a in inventories[0]['atoms']})
        _need(modeled == report['modeled_components'])
        qualifications = []
        for i, step in enumerate(steps):
            q = qualify_linked_torsion_energy(inventories[i], inventories[i+1],
                    root/step['source']['path'], step['component'], root/step['candidate']['path'], references[i])
            _need(q['numerical_checks_pass'] is True);qualifications.append(q)
        return {'schema_version':1, 'policy_id':POLICY_ID, 'status':'REVIEW',
                'bundle':_ref(root/REPORT, root), 'steps':qualifications,
                'numerical_checks_pass':True,
                'removed_proxy_count':sum(q['removed_proxy_count'] for q in qualifications),
                'target_delta':math.fsum(q['target_delta'] for q in qualifications),
                'native_execution_authentication':'CALLER_REQUIRED',
                'scope':'CONSECUTIVE_FIXED_COORDINATE_INVENTORY_AND_ENERGY_ONLY',
                'chemical_qualification':'NOT_ASSESSED', 'derivative_qualification':'NOT_RUN',
                'optimization':'NOT_RUN', 'automatic_adoption':False}
    except (KeyError, TypeError, IndexError, OverflowError) as exc:
        raise ValueError('Incomplete staged native evidence') from exc


def qualify_captured_linear_torsion_bundle(directory, native_receipts, references):
    """Authenticate each ordered native stage before exact numerical attribution.

    Kernel execution remains the caller's responsibility; the existing energy
    gate validates its complete repeated per-proxy numbers against native deltas.
    Returned stage anchors correspond to the supplied receipt parent directories.
    """
    root = _path(directory, directory=True);report = read_linear_torsion_bundle(root)
    stages = [report['inputs']] + [s['dictionaries_after'] for s in report['steps']]
    _need(bool(report['steps']) and isinstance(native_receipts, (list, tuple))
          and len(native_receipts) == len(stages))
    inventories, captures, initial = [], [], None
    for i, (receipt, stage) in enumerate(zip(native_receipts, stages)):
        path = _path(receipt);_need(path.name == 'native_receipt.json')
        capture, model, dictionaries, phils, native, _ = _captured_inputs(path.parent)
        _need([p.read_bytes() for p in dictionaries] == [(root/r['path']).read_bytes() for r in stage])
        context = {'model':model.read_bytes(), 'phils':[p.read_bytes() for p in phils],
                   **{k:capture[k] for k in ('phenix_version','executable_sha256',
                         'phil_namespace_policy','dictionary_source_policy')}}
        if initial is None:initial = context
        else:_need(context == initial)
        inventories.append(native)
        captures.append(_reference(path, path.parent, f'native_stage_{i:03d}_directory'))
    result = qualify_linear_torsion_bundle(root, inventories, references)
    result.update(native_execution_authentication='AUTHENTICATED_ORDERED_NATIVE_CAPTURES',
                  kernel_execution_authentication='CALLER_REQUIRED', native_captures=captures)
    return result
