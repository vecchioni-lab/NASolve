"""Explicit ordinary parent binding for the existing mixed-refinement guard.

Read-only admission: no numbered run, executor, model adoption or chemistry
approval. A new, checksummed child request owns its scientific policy; historical
parent parameters and frozen workers are never reinterpreted or rewritten.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

from .checkpoints import read_registry, resolve_checkpoint, inherited_paths, registry_path
from .metal.context import (_metadata_snapshot, _reference, _check_original_sources,
                            _check_import_unchanged)
from .refinement_command_binding import _portable
from .refinement_inputs import _bound_path
from .refinement_parameter_scope import ParameterScope, scope_digest
from .refinement_parameter_files import rebind_miller_files
from .refinement_parameter_composition import compose_parameters
from .refinement_diffraction_source import read_source_arrays
from .refinement_diffraction_observation import (DiffractionReference, make_reference,
                                                _same_cell)
from .refinement_mixed_runtime import MixedRuntimeGuard

POLICY_ID = 'ordinary-mixed-parent-binding-v1'


def _need(value, message):
    if not value:
        raise ValueError(message)


def _file(reference, role, run):
    _portable(reference)
    return _bound_path(reference, role, run)


def _fields(record, names, role):
    _need(isinstance(record, dict) and set(record) == set(names.split()),
          'Unexpected ' + role + ' fields')


def _selectors(record):
    _fields(record, 'data_labels free_label test_flag_value phase_labels', 'source selector')
    for key, length in [('data_labels', None), ('phase_labels', 4)]:
        value = record[key]
        _need(isinstance(value, list) and value and (length is None or len(value) == length)
              and all(isinstance(x, str) and x.strip() == x and x and ',' not in x for x in value)
              and len(set(value)) == len(value), 'Require explicit unique source labels')
    _need(isinstance(record['free_label'], str) and record['free_label'].strip() == record['free_label']
          and record['free_label'] and record['free_label'].casefold() != 'saflags'
          and ',' not in record['free_label'], 'Require original Free-R label, not SAflags')
    _need(type(record['test_flag_value']) is int, 'Require explicit integer Free-R test value')


def _read_parent(run, request):
    before = _metadata_snapshot(run)
    actual_run, registry = read_registry(run)
    _need(actual_run == run, 'Ordinary run identity changed')
    selected = resolve_checkpoint(registry, request['checkpoint_id'])
    _need(selected.get('usable') is True, 'Ordinary parent is not usable')
    _need(selected['id'] == request['checkpoint_id'], 'Require an exact checkpoint ID, not a moving alias')
    paths = inherited_paths(selected, run)
    report = json.loads((run / 'report.json').read_text())
    sources = {key: _reference(paths[key], run) if paths[key] else None
               for key in ('model', 'observations', 'phases')}
    sources['restraints'] = [_reference(p, run) for p in paths['restraints']]
    sources['report'] = _reference(run / 'report.json', run)
    sources['registry'] = _reference(registry_path(run), run) if before[1] is not None else None
    _check_original_sources(run, report, paths, sources)
    _need(sources['phases'] is not None, 'Mixed MLHL parent requires approved AutoSol phases')
    _need(paths['phase_metadata']['labels'] == request['selectors']['phase_labels'],
          'Request phase labels differ from approved AutoSol source')
    # Compare resolved identities as well as bytes; equal bytes at another path
    # do not establish the same parent. Historical provenance fields are ignored.
    declared = request['parent']
    _fields(declared, 'model observations phases restraints report registry', 'parent')
    _need(isinstance(declared['restraints'], list), 'Require ordered parent restraints')
    for key in ('model', 'observations', 'phases', 'report', 'registry'):
        if sources[key] is None:
            _need(declared[key] is None, 'Parent registry presence differs')
        else:
            path = _file(declared[key], 'declared parent ' + key, run)
            _need(_reference(path, run) == sources[key], 'Declared parent ' + key + ' differs')
    _need([_reference(_file(ref, 'declared parent restraint', run), run)
           for ref in declared['restraints']] == sources['restraints'],
          'Declared parent restraints differ in membership or order')
    _check_import_unchanged(run, before, paths, sources)
    return before, paths, sources


def bind_mixed_parent(run, *, request_reference):
    """Bind an exact ordinary checkpoint, child policy, scope and source arrays.

    The explicit request has this module's policy ID and schema 1. All files use
    existing checksummed run/dataset/repository references. The parent is read
    through the ordinary registry owner, including its checked-execution reader.
    A missing registry is allowed only when that owner derives a valid PostMR
    root. An absent report, unapproved HL or private fit directory cannot enter.

    Return a BoundMixedParent with derived policy bytes and a guard factory.
    The existing execution owner must freeze these exact inputs/policy and retain
    chemistry, image forces, output and process closure. No default is activated.
    """
    run = registry_path(Path(run)).parent.parent
    request_path = _file(request_reference, 'mixed parent request', run)
    raw = request_path.read_bytes()
    _need(sha256(raw).hexdigest() == request_reference['sha256'], 'Mixed request changed during read')
    request = json.loads(raw)
    _fields(request, 'schema_version policy_id checkpoint_id parent selectors scope policy runtime', 'mixed request')
    _need(type(request['schema_version']) is int and request['schema_version'] == 1
          and request['policy_id'] == POLICY_ID, 'Unsupported mixed parent request')
    _need(isinstance(request['checkpoint_id'], str) and request['checkpoint_id'], 'Require exact parent checkpoint ID')
    _selectors(request['selectors'])
    _fields(request['policy'], 'source bindings', 'child policy')
    _fields(request['runtime'], 'cell_roundoff_ulps witness_native_normalization', 'runtime')
    before, paths, sources = _read_parent(run, request)
    scope = ParameterScope(request['scope'], expected_sha256=scope_digest(request['scope']))
    source = paths['model'].read_bytes()
    _need(scope.record()['source_model_sha256'] == sources['model']['sha256'], 'Scope differs from parent model')
    _need(scope.record()['real_space'] is False, 'Mixed parent scope excludes real-space refinement')
    policy_path = _file(request['policy']['source'], 'new child policy', run)
    original_policy = policy_path.read_bytes()
    _need(policy_path not in [paths['model'], paths['observations'], paths['phases'], *paths['restraints']],
          'New child policy must be separate from inherited scientific inputs')
    bindings = request['policy']['bindings']
    _need(isinstance(bindings, list) and len(bindings) == 2, 'Require explicit data and AutoSol file bindings')
    mapped = []
    for row, key in zip(bindings, ('observations', 'phases')):
        _fields(row, 'historical_file source_reference', 'file binding')
        path = _file(row['source_reference'], 'policy source', run)
        _need(_reference(path, run) == sources[key], 'Policy binding differs from parent ' + key)
        mapped.append(dict(row, resolved_file=str(path), sha256=sources[key]['sha256']))
    rebased, file_receipt = rebind_miller_files(original_policy,
        expected_policy_sha256=request['policy']['source']['sha256'], bindings=mapped)
    policy, composition = compose_parameters(rebased, expected_policy_sha256=sha256(rebased).hexdigest(),
                                            scope=scope, source=source)
    from .refinement_mixed_parent_native import check_policy
    check_policy(policy, source, scope, paths, request['selectors'])
    arrays = read_source_arrays(data_file=paths['observations'], phase_file=paths['phases'], **request['selectors'])
    from .metal._xyz_native import reflection_signature, phase_signature
    rows = arrays.observations
    fo = SimpleNamespace(indices=lambda:[r[0] for r in rows], data=lambda:[r[1] for r in rows],
                         sigmas=lambda:[r[2] for r in rows], anomalous_flag=lambda:False)
    flags = SimpleNamespace(indices=lambda:arrays.flags[0], data=lambda:arrays.flags[1])
    hl = SimpleNamespace(indices=lambda:arrays.hl[0], data=lambda:arrays.hl[1])
    observation, phases = json.loads(json.dumps([
        reflection_signature(SimpleNamespace(f_obs=lambda:fo, r_free_flags=lambda:flags)),
        phase_signature(hl)], allow_nan=False))
    record = make_reference(observations=observation, phases=phases,
        data_sha256=sources['observations']['sha256'], phases_sha256=sources['phases']['sha256'])
    diffraction = DiffractionReference(record, expected_sha256=scope_digest(record))
    # Validate runtime options before returning, without installing any callback.
    MixedRuntimeGuard(scope, diffraction, **request['runtime'])
    def recheck():
        _need(_file(request_reference, 'mixed request', run).read_bytes() == raw, 'Mixed request changed')
        _need(_file(request['policy']['source'], 'child policy', run).read_bytes() == original_policy,
              'Child policy changed')
        _check_import_unchanged(run, before, paths, sources)
        _read_parent(run, request)  # Revalidate checked ancestry as well as its direct files.
    recheck()
    receipt = dict(schema_version=1, policy_id=POLICY_ID, status='BOUND_NOT_EXECUTED',
        request=deepcopy(request_reference), checkpoint_id=request['checkpoint_id'], sources=sources,
        selectors=request['selectors'], scope_sha256=scope_digest(scope.record()),
        diffraction_sha256=scope_digest(record), file_derivation=file_receipt, composition=composition,
        runtime=request['runtime'], observations=observation['count'], free_count=observation['free_count'],
        phases=phases['count'], source_cell=list(arrays.crystal.unit_cell().parameters()),
        source_space_group=str(arrays.crystal.space_group()), scientific_approval='NOT_RUN',
        limit='Input/guard binding only; existing owner must freeze policy, forces, output and process closure')
    return BoundMixedParent(policy, receipt, scope, diffraction, arrays.crystal, source, recheck, request['runtime'])


class BoundMixedParent:
    """Call-local binding; compact receipt is provenance, not a replay executor."""
    def __init__(self, policy, receipt, scope, diffraction, crystal, source, recheck, runtime):
        self.policy = policy
        self._receipt = deepcopy(receipt)
        self._scope, self._diffraction, self._crystal = scope, diffraction, crystal
        self._source, self._recheck, self._runtime = source, recheck, deepcopy(runtime)

    def receipt(self):
        return deepcopy(self._receipt)

    def guard(self):
        self._recheck()
        return _ParentGuard(self)


class _ParentGuard(MixedRuntimeGuard):
    """Reuse the runtime lifecycle; add admitted source identity/crystal checks."""
    def __init__(self, parent):
        self._parent = parent
        super().__init__(parent._scope, parent._diffraction, **parent._runtime)

    def __enter__(self):
        self._parent._recheck()
        return super().__enter__()

    def _model(self, driver, *, initial=False):
        if initial:
            from .refinement_parameter_native import bind_scope
            record = self.scope.record()
            expected = [{k:r[k] for k in ('label', 'scattering_type', 'f_prime', 'f_double_prime')}
                        for r in record['initial_atoms']]
            bind_scope(self._parent._source, driver.model, expected_scattering=expected,
                       xyz_indices=record['xyz_indices'], adp_groups=record['adp_groups'])
        return super()._model(driver, initial=initial)

    def _target(self, fm, target):
        crystal = self._parent._crystal
        for obj in (fm.xray_structure, fm.f_obs(), target.core.f_obs):
            _need(obj.space_group() == crystal.space_group()
                  and _same_cell(obj.unit_cell().parameters(), crystal.unit_cell().parameters(),
                                 self._cell_roundoff_ulps), 'Active target crystal differs from admitted source')
        super()._target(fm, target)

    def finish(self, driver, *, dry_run):
        try:
            self._parent._recheck()
            return super().finish(driver, dry_run=dry_run)
        except BaseException as exc:
            self._fail(exc)
            raise

    def summary(self):
        result = super().summary()
        result['parent_binding'] = self._parent.receipt()
        return result
