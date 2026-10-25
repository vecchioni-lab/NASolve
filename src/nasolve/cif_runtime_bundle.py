"""Portable activation of an independently qualified model/restraint selection.

The trusted orchestration supplies verified native/optimizer evidence. This
adapter replays serialization, fixed-manager readback and the automatic choice,
then freezes exact resources for ordinary read-only CIF Doctor consumption. It
does not acquire chemistry, invoke native tools, adopt a checkpoint or refine.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath
import re
from tempfile import TemporaryDirectory

from .cif_candidate_usability import energy_inventory_checks
from .cif_captured_geometry import review_captured_geometry
from .cif_effective_source_recovery import mechanics_can_continue
from .cif_fixed_geometry import (_fixed_policy, qualify_fixed_policy_geometry,
    review_fixed_coordinates, write_geometry_candidate)
from .cif_fragment_restoration import _model
from .cif_scaffold_candidate import select_scaffold_geometry

POLICY_ID = 'cif-qualified-runtime-bundle-v1'
MANIFEST_FILE = 'runtime_bundle.json'
ANCHOR = 'runtime_bundle'
MAX_JSON_BYTES = 64 * 1024 * 1024


def _digest(path): return sha256(Path(path).read_bytes()).hexdigest()


def _json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')


def _load_json(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink(): raise ValueError('Runtime bundle JSON must be a regular file')
    data = path.read_bytes()
    if len(data) > MAX_JSON_BYTES: raise ValueError('Runtime bundle JSON exceeds its supported size')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate runtime bundle JSON field')
            result[key] = value
        return result
    try:
        result = json.loads(data, object_pairs_hook=unique,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite runtime evidence')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Unreadable runtime bundle JSON') from exc
    if not isinstance(result, dict): raise ValueError('Runtime bundle JSON must be an object')
    return result


def _reference(path, root, **extra):
    path = Path(path); data = path.read_bytes()
    return {'anchor': ANCHOR, 'relative_path': path.relative_to(root).as_posix(),
        'sha256': sha256(data).hexdigest(), 'size': len(data), **extra}


def _resolve_reference(root, reference):
    if not isinstance(reference, dict) or reference.get('anchor') != ANCHOR:
        raise ValueError('Runtime resource needs its declared bundle anchor')
    name = reference.get('relative_path')
    if (not isinstance(name, str) or name.startswith('/') or '\\' in name or ':' in name
            or any(part in {'', '.', '..'} for part in name.split('/'))):
        raise ValueError('Runtime resource path must remain relative to its bundle')
    path = root/PurePosixPath(name)
    if (any(p.is_symlink() for p in [path, *path.parents])
            or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
        raise ValueError('Runtime resource is missing, symlinked or outside its bundle')
    digest, size = reference.get('sha256'), reference.get('size')
    if (not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None
            or type(size) is not int or size < 0 or path.stat().st_size != size or _digest(path) != digest):
        raise ValueError('Runtime resource checksum or size changed')
    return path


def _source_input_checks(model, dictionaries, phils, records):
    expected = [('model', Path(model)), *[('dictionary', Path(p)) for p in dictionaries], *[('phil', Path(p)) for p in phils]]
    if not isinstance(records, list) or len(records) != len(expected):
        raise ValueError('Require the complete ordered source-capture input inventory')
    for row, (role, path) in zip(records, expected):
        if (not isinstance(row, dict) or row.get('role') != role or row.get('sha256') != _digest(path)
                or type(row.get('size')) is not int or row['size'] != path.stat().st_size):
            raise ValueError('Selected resource differs from its verified source-capture input')


def _native_model_checks(native, model):
    _model(native, Path(model), coordinates_match=True)
    if (native.get('status') != 'REVIEW' or native.get('inventory_detail') != 'linked'
            or native.get('fatal_problems') is not None or native.get('unused_definitions') != []
            or native.get('unsupported_fields') != [] or not _fixed_policy(native)
            or not native.get('installed_api_sources') or native.get('atom_count') != len(native['atoms'])):
        raise ValueError('Selected native manager is incomplete or has competing secondary-structure policy')
    points = native['geometry']['sites_cart_exact']
    if (len(points) != len(native['atoms']) or any(len(p) != 3 or len(a['xyz']) != 3
            or any(type(x) not in (int, float) or type(y) not in (int, float)
                or not math.isfinite(x) or not math.isfinite(y) or abs(x-y) > 1e-12
                for x, y in zip(p, a['xyz'])) for p, a in zip(points, native['atoms']))):
        raise ValueError('Selected native coordinates do not roundtrip to the preserved model')


def _verify_activation(model, dictionaries, phils, decision, native_validation, provenance):
    """Replay evidence supplied by a separately verified native orchestration."""
    try:
        initial_model = Path(provenance['initial_model']); initial = provenance['initial_native_validation']
        qualification = provenance['initial_qualification']; trial = provenance.get('trial')
        source = provenance['source_archive']
        if (not isinstance(source, dict) or re.fullmatch('[0-9a-f]{64}', source.get('sha256', '')) is None
                or not isinstance(source.get('delivery_prefix'), str) or not source['delivery_prefix']):
            raise ValueError('Require the verified source archive identity')
        _source_input_checks(model, dictionaries, phils, provenance['source_inputs'])
        _native_model_checks(initial, initial_model); _native_model_checks(native_validation, model)
        if (qualification.get('policy_id') != 'cif-qualified-scaffold-candidate-v1'
                or qualification.get('native_usable') is not True or not mechanics_can_continue(qualification)
                or qualification.get('model_sha256') != _digest(initial_model)
                or not all(energy_inventory_checks(initial).values())):
            raise ValueError('Require independently usable, hash-bound initial scaffold evidence')
        mechanics = full = rounded = serialized = None
        if trial is not None and provenance.get('serialization') is not None:
            result = trial.get('result', {})
            with TemporaryDirectory(prefix='cif-runtime-serialization-') as temporary:
                written = Path(temporary).resolve()/'endpoint.pdb'
                serialized = write_geometry_candidate(initial_model, written, initial, result['final_sites_cart'])
                reported = provenance['serialization']
                fields = ['source_preserved', 'source_sha256', 'candidate_sha256', 'atom_count',
                    'atom_correspondence', 'metadata_and_headers_preserved']
                if any(reported.get(k) != serialized[k] for k in fields):
                    raise ValueError('Reported serialization does not reproduce the exact selected endpoint')
                if decision.get('selected_candidate') == 'qualified_geometry_endpoint' and written.read_bytes() != Path(model).read_bytes():
                    raise ValueError('Selected endpoint bytes do not reproduce saved full precision')
                mechanics = qualify_fixed_policy_geometry(initial, native_validation, written, serialized)
            full = review_fixed_coordinates(initial, result['final_sites_cart'])
            rounded = review_captured_geometry(native_validation)
            initial_target = initial['energy_inventory']['snapshots'][0]['target']
            if not math.isclose(initial_target, result['initial']['target'], rel_tol=1e-10, abs_tol=1e-8):
                raise ValueError('The trial did not begin at the verified replacement objective')
        recomputed = select_scaffold_geometry(qualification, trial, mechanics, full, serialized,
            atom_count=initial['atom_count'], rounded_geometry_review=rounded)
        if recomputed != decision:
            raise ValueError('Runtime activation decision does not reproduce verified selection evidence')
        if recomputed['selected_candidate'] == 'verified_initial_scaffold':
            if Path(model).read_bytes() != initial_model.read_bytes():
                raise ValueError('Automatic fallback must preserve the verified initial model bytes')
            same = qualify_fixed_policy_geometry(initial, native_validation, model, {'candidate_sha256': _digest(model)})
            if not same['mechanics_checks_pass']:
                raise ValueError('Automatic fallback changed its verified fixed native bundle')
        elif recomputed['selected_candidate'] != 'qualified_geometry_endpoint' or not mechanics['mechanics_checks_pass']:
            raise ValueError('No qualified runtime selection is available')
        return recomputed
    except (KeyError, TypeError, IndexError, OSError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete or changed runtime activation evidence') from exc


def prepare_runtime_bundle(model, dictionaries, phils, output, *, decision, native_validation, provenance):
    """Copy one verified selection into an exclusive portable runtime layout."""
    model, output = Path(model), Path(output).expanduser().absolute()
    dictionaries, phils = list(map(Path, dictionaries)), list(map(Path, phils))
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    if any(p.is_symlink() for p in output.parents): raise ValueError('Output parent cannot traverse a symlink')
    paths = [model, *dictionaries, *phils, Path(provenance['initial_model'])]
    if (not dictionaries or not phils or len({p.resolve() for p in paths[:-1]}) != len(paths)-1
            or any(output.resolve() == p.parent.resolve() or p.parent.resolve() in output.resolve().parents for p in paths)):
        raise ValueError('Require distinct explicit resources and a separate activation directory')
    original = [p.read_bytes() for p in paths]
    chosen = _verify_activation(model, dictionaries, phils, decision, native_validation, provenance)
    # JSON freezes evidence as data. No captured code, absolute reference or
    # executable path is evaluated by the runtime loader.
    evidence = deepcopy({k: v for k, v in provenance.items() if k != 'initial_model'})
    evidence.update(schema_version=1, policy_id=POLICY_ID, decision=chosen, native_validation=native_validation)
    output.mkdir(parents=True)
    target = output/'model/model.pdb'; target.parent.mkdir(); target.write_bytes(model.read_bytes())
    resources = {'model': _reference(target, output), 'dictionaries': [], 'phils': []}
    for key, folder, supplied in [('dictionaries', 'dictionaries', dictionaries), ('phils', 'parameters', phils)]:
        directory = output/folder; directory.mkdir()
        for i, path in enumerate(supplied):
            name = re.sub(r'[^A-Za-z0-9._-]', '_', path.name)
            if not name or len(name) > 160: raise ValueError('Unsupported runtime resource filename')
            target = directory/f'{i:03d}_{name}'; target.write_bytes(path.read_bytes())
            resources[key].append(_reference(target, output, source_name=path.name))
    directory = output/'evidence'; directory.mkdir()
    target = directory/'initial_model.pdb'; target.write_bytes(Path(provenance['initial_model']).read_bytes())
    evidence['initial_model'] = _reference(target, output)
    target = directory/'activation_evidence.json'; target.write_bytes(_json_bytes(evidence))
    manifest = {'schema_version': 1, 'policy_id': POLICY_ID, 'manifest_file': MANIFEST_FILE,
        'scope': 'PORTABLE_QUALIFIED_RUNTIME_BUNDLE', 'status': 'ACTIVATED_WITH_NOTES',
        'resources': resources, 'evidence': _reference(target, output), 'decision': chosen,
        'source_archive': deepcopy(provenance['source_archive']), 'native_evidence': 'VERIFIED_SOURCE_CAPTURE',
        'requires_cif_review': False, 'scientific_approval': 'NOT_RUN', 'automatic_adoption': False,
        'production_consumption': 'PUBLIC_CIF_DOCTOR_BUNDLE_ASSESSMENT', 'checkpoint_adoption': 'NOT_RUN',
        'automatic_acquisition': 'NOT_RUN', 'model_optimization': 'NOT_RUN'}
    if original != [p.read_bytes() for p in paths]: raise ValueError('Source changed during runtime activation')
    (output/MANIFEST_FILE).write_bytes(_json_bytes(manifest))
    resolve_runtime_bundle(output/MANIFEST_FILE)
    return manifest


def resolve_runtime_bundle(manifest):
    """Resolve only declared anchored resources and replay the stored selection."""
    supplied = Path(manifest).expanduser().absolute()
    path = supplied/MANIFEST_FILE if supplied.is_dir() else supplied
    if any(p.is_symlink() for p in [path, *path.parents]): raise ValueError('Runtime manifest cannot traverse a symlink')
    root = path.parent
    try:
        value = _load_json(path); before = path.read_bytes()
        from .cif_mixed_runtime_bundle import POLICY_ID as MIXED_POLICY, resolve_mixed_runtime_bundle
        if value.get('policy_id') == MIXED_POLICY:
            return resolve_mixed_runtime_bundle(path, value)
        if (value.get('schema_version') != 1 or value.get('policy_id') != POLICY_ID
                or value.get('manifest_file') != path.name or value.get('scope') != 'PORTABLE_QUALIFIED_RUNTIME_BUNDLE'
                or value.get('status') != 'ACTIVATED_WITH_NOTES' or value.get('requires_cif_review') is not False
                or value.get('automatic_adoption') is not False or value.get('scientific_approval') != 'NOT_RUN'
                or value.get('native_evidence') != 'VERIFIED_SOURCE_CAPTURE'
                or value.get('production_consumption') != 'PUBLIC_CIF_DOCTOR_BUNDLE_ASSESSMENT'
                or any(value.get(key) != 'NOT_RUN' for key in ['checkpoint_adoption', 'automatic_acquisition', 'model_optimization'])):
            raise ValueError('Unsupported runtime bundle policy or schema')
        refs = value['resources']
        if (not isinstance(refs.get('dictionaries'), list) or not refs['dictionaries']
                or not isinstance(refs.get('phils'), list) or not refs['phils']):
            raise ValueError('Runtime bundle omits its ordered complete resources')
        references = [refs['model'], *refs['dictionaries'], *refs['phils'], value['evidence']]
        names = [r['relative_path'] for r in references]
        if len(names) != len(set(names)): raise ValueError('Runtime resources cannot alias one another')
        model = _resolve_reference(root, refs['model'])
        dictionaries = [_resolve_reference(root, r) for r in refs['dictionaries']]
        phils = [_resolve_reference(root, r) for r in refs['phils']]
        evidence_path = _resolve_reference(root, value['evidence']); evidence = _load_json(evidence_path)
        if evidence.get('schema_version') != 1 or evidence.get('policy_id') != POLICY_ID:
            raise ValueError('Unsupported runtime selection evidence')
        initial_reference = evidence['initial_model']
        initial_model = _resolve_reference(root, initial_reference)
        if initial_reference['relative_path'] in names: raise ValueError('Initial evidence cannot alias a selected runtime resource')
        provenance = {**evidence, 'initial_model': initial_model}
        if evidence.get('decision') != value['decision'] or evidence.get('source_archive') != value['source_archive']:
            raise ValueError('Manifest selection differs from its bound evidence')
        _verify_activation(model, dictionaries, phils, value['decision'], evidence['native_validation'], provenance)
        for row in [*references, initial_reference]: _resolve_reference(root, row)
        if path.read_bytes() != before: raise ValueError('Runtime manifest changed during resolution')
        return {'model': model, 'dictionaries': dictionaries, 'phils': phils, 'manifest': value, 'manifest_path': path}
    except (KeyError, TypeError, IndexError, OSError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete, unsafe or changed runtime bundle') from exc


def assess_runtime_bundle(manifest):
    """Use the ordinary read-only assessor on the exact activated resources."""
    from .cif_doctor import assess_dictionaries
    resolved = resolve_runtime_bundle(manifest); value = resolved['manifest']
    paths = [*resolved['dictionaries'], *resolved['phils']]
    references = [*value['resources']['dictionaries'], *value['resources']['phils']]
    assessment = assess_dictionaries(paths, stage='effective', model=resolved['model'])
    if (len(assessment.get('inputs', [])) != len(references)
            or any(a.get('sha256') != r['sha256'] for a, r in zip(assessment['inputs'], references))
            or assessment.get('model', {}).get('sha256') != value['resources']['model']['sha256']):
        raise ValueError('Ordinary assessor did not consume the exact activated runtime bundle')
    for descriptor, reference in zip(assessment['inputs'], references): descriptor['frozen_reference'] = deepcopy(reference)
    assessment['model']['frozen_reference'] = deepcopy(value['resources']['model'])
    from .cif_mixed_runtime_bundle import POLICY_ID as MIXED_POLICY, verify_mixed_runtime_resources
    if value['policy_id'] == MIXED_POLICY:
        verify_mixed_runtime_resources(resolved['manifest_path'], value)
    else:
        after = resolve_runtime_bundle(resolved['manifest_path'])
        if after['manifest'] != value: raise ValueError('Runtime bundle changed during read-only assessment')
    assessment['bundle_context'] = {'schema_version': 1, 'policy_id': value['policy_id'],
        'manifest': {'anchor': ANCHOR, 'relative_path': value['manifest_file'], 'sha256': _digest(resolved['manifest_path']),
            'size': resolved['manifest_path'].stat().st_size},
        'model': deepcopy(value['resources']['model']), 'effective_restraints': deepcopy(references),
        'decision': deepcopy(value['decision']), 'native_evidence': value['native_evidence'],
        'read_only': True, 'requires_cif_review': False, 'automatic_acquisition': 'NOT_RUN',
        'checkpoint_adoption': 'NOT_RUN', 'scientific_approval': 'NOT_RUN'}
    from .cif_doctor_selection import assessment_report_summary
    summary = assessment_report_summary(assessment)
    selection = value['decision']; stopping = selection.get('stopping') or {}
    selected_name = selection.get('selected_candidate', selection.get('selected'))
    selected = ('the verified geometry endpoint' if selected_name == 'qualified_geometry_endpoint'
                else 'the verified starting model')
    text = f'NASolve activated {selected} with its exact verified restraint bundle. '
    if stopping.get('native_criterion_met') is True:
        text += 'The bounded geometry trial met its native stopping criterion. '
    elif stopping.get('reason') in {'max_iterations', 'max_calls'}:
        text += 'The bounded geometry trial reached its recorded limit; the usable selection was retained. '
    elif stopping:
        text += 'The bounded geometry trial stopped before convergence; its usable selection was retained. '
    text += 'Dictionary findings and unresolved chemistry or geometry notes remain recorded. CIF inspection is not required.'
    summary.update(text=text, native_selection='VERIFIED_SOURCE_CAPTURE', native_selection_executed=False,
        selected_candidate=selected_name, stopping=deepcopy(selection.get('stopping')),
        notes=deepcopy(selection['notes']), native_evidence=value['native_evidence'], checkpoint_adoption='NOT_RUN')
    if value['policy_id'] == MIXED_POLICY:
        summary.update(scientific_qualification='NOT_ASSESSED', source_chemical_findings=value['qualification']['source_chemical_findings'])
    assessment['requires_cif_review'] = False
    assessment['solution_report'] = summary
    return assessment
