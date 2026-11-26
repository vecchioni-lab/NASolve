"""Read-only input-role review of a receipt from an independent ordinary owner.

This does not replay that owner's runtime, admit its scientific endpoint, or
teach the local checkpoint reader a newer policy. Digests detect changed bytes;
they are not a substitute for the source owner's execution validation.
"""
from hashlib import sha256
import json
from pathlib import Path
import re

from .campaign_records import read_record
from .checkpoints import registry_path
from .metal.context import _reference, _metadata_snapshot, _check_original_sources
from .refinement_mixed_parent import _file, _need
from .refinement_parameter_scope import scope_digest
from .refinement_command_binding import _plan

POLICY_ID = 'ordinary-parent-transfer-review-v1'
_SOURCE_POLICY = 'round-local-registered-phosphate-set-execution-v12'


def inspect_parent_transfer(run, capture_file, *, expected_sha256, expected_owner_revision):
    """Review exact files/roles, never execute capture-supplied code or commands.

    The caller obtains and pins the capture from the trusted installed source
    owner. This receiver independently verifies current file identities, original
    sources and the described ordinary records. It returns review-only data;
    runtime/force replay, numerical diffraction admission and a new child remain
    separate requirements even when phases are present.
    """
    run = registry_path(Path(run)).parent.parent
    path = Path(capture_file).expanduser().resolve()
    raw = path.read_bytes()
    _need(isinstance(expected_sha256, str) and sha256(raw).hexdigest() == expected_sha256,
          'Transfer capture checksum differs')
    record = json.loads(raw)
    _need(isinstance(record, dict) and type(record.get('schema_version')) is int
          and record['schema_version'] == 1 and record.get('kind') == 'ordinary-parent-transfer-capture',
          'Unsupported parent transfer capture')
    owner = record.get('owner', {})
    _need(isinstance(expected_owner_revision, str) and re.fullmatch('[0-9a-f]{40}', expected_owner_revision)
          and owner.get('source_revision') == expected_owner_revision,
          'Transfer differs from the independently pinned source owner')
    _need(owner.get('methods') == ['read_registry','resolve_checkpoint','inherited_paths',
                                   'validate_checkpoint_execution','read_execution_request'],
          'Transfer lacks the declared source-owner read sequence')
    _need(record.get('native_ready') is False and record.get('scientific_approval') == 'NOT_ASSESSED',
          'Transfer capture cannot grant native or scientific approval')
    before = _metadata_snapshot(run)
    references = []
    def resolve(ref, role):
        value = _file(ref, role, run)
        references.append((ref, role, value))
        return value
    def identity(ref, role):
        return _reference(resolve(ref, role), run)
    records = record['records']
    _need(resolve(records['report'], 'source report') == run/'report.json'
          and resolve(records['registry'], 'source registry') == registry_path(run),
          'Transfer metadata belongs to another run')
    report = json.loads((run/'report.json').read_bytes())
    registry = json.loads(registry_path(run).read_bytes())
    chosen = [r for r in registry['checkpoints'] if r.get('id') == record['checkpoint']['id']]
    _need(len(chosen) == 1, 'Transfer checkpoint is missing or ambiguous')
    selected = chosen[0]
    _need({k:selected[k] for k in ('id','parent','status','usable')} == record['checkpoint']
          and selected['usable'] is True, 'Transfer checkpoint identity/state differs')
    sources = record['sources']; resolved = {}
    for key in ('model','observations','phases'):
        expected = sources[key]
        if expected is None:
            _need(key == 'phases' and selected.get(key) is None, 'Unexpected absent source input')
            resolved[key] = None
        else:
            _need(identity(selected[key], 'checkpoint '+key) == identity(expected, 'captured '+key),
                  'Transferred '+key+' differs from checkpoint')
            resolved[key] = resolve(expected, key)
    _need([identity(r, 'checkpoint restraint') for r in selected['restraints']]
          == [identity(r, 'captured restraint') for r in sources['restraints']],
          'Transferred inherited restraint order differs')
    resolved['restraints'] = [resolve(r, 'inherited restraint') for r in sources['restraints']]
    resolved['phase_metadata'] = record['phase_metadata']
    _need(selected.get('phases') == record['phase_metadata'], 'Transferred phase metadata differs')
    _check_original_sources(run, report, resolved, sources)
    execution = read_record(resolve(records['execution'], 'source execution outcome'))
    request = read_record(resolve(records['request'], 'source execution request'))
    _need(identity(selected['outputs']['parallelity_execution'], 'checkpoint execution')
          == identity(records['execution'], 'captured execution'), 'Transferred execution reference differs')
    _need(execution['checkpoint'] == request['checkpoint'] == selected['id']
          and identity(execution['request'], 'execution request') == identity(records['request'], 'captured request'),
          'Transferred request belongs to another checkpoint')
    _need(request['policy_id'] == execution['policy_id'] == _SOURCE_POLICY,
          'Unqualified source policy for this input-role review')
    declared = record['source_execution']
    _need({k:request[k] for k in ('policy_id','parent','inputs','command')} == declared
          and request['parent'] == selected['parent'], 'Transferred source request changed')
    inputs = request['inputs']
    _need(isinstance(inputs, list) and len(inputs) >= 4, 'Incomplete source input inventory')
    actual = [identity(r, 'source execution input') for r in inputs]
    ancestors = [r for r in registry['checkpoints'] if r.get('id') == selected['parent']]
    _need(len(ancestors) == 1, 'Missing source starting checkpoint')
    starting = identity(ancestors[0]['model'], 'source starting model')
    inherited = [identity(r, 'inherited restraint') for r in sources['restraints']]
    phosphate = request['phosphate']
    bond = identity(phosphate['bond'], 'runtime-generated crystal bond')
    _need(actual == [identity(sources['observations'], 'original observations'), starting,
                     *inherited, bond, *([identity(sources['phases'], 'source phases')] if sources['phases'] else []), actual[-1]],
          'Source execution order differs from observations/model/inherited/crystal-bond/policy roles')
    _need(actual[-1] not in actual[:-1], 'Source policy must be a distinct input')
    for role, ref in phosphate['sources'].items():
        _need(role in ('registration','discovery','continuations'), 'Unknown crystal source role')
        resolve(ref, 'phosphate '+role)
    _need(set(phosphate['sources']) == {'registration','discovery','continuations'},
          'Incomplete runtime-owned crystal source set')
    roles = ['original_observations','source_starting_model',*(['inherited_restraint']*len(inherited)),
             'runtime_generated_crystal_bond',*(['source_phases'] if sources['phases'] else []),'source_scientific_policy']
    command = request['command']
    _need(isinstance(command, list) and all(isinstance(v, str) for v in command),
          'Require a declared source command')
    plan = _plan(command, len(inputs))
    selectors = dict(data_labels=list(plan.observation_labels), free_label=plan.free_r_label,
                     test_flag_value=plan.free_r_test_value)
    _need(bool(plan.phase_file) == bool(sources['phases']),
          'Declared command phase presence differs from source')
    if sources['phases'] is not None:
        _need(list(plan.phase_labels) == record['phase_metadata']['labels'],
              'Declared command phase labels differ from source')
    # Recheck bytes after classification; no runtime was replayed in this receiver.
    for ref, role, old in references:
        _need(_file(ref, role, run) == old, 'Transferred source identity changed during review')
    _need(_metadata_snapshot(run) == before and path.read_bytes() == raw, 'Transfer changed during review')
    holds = ['SOURCE_OWNER_REPLAY_REQUIRED_FOR_EXECUTION','NUMERICAL_DIFFRACTION_ADMISSION_REQUIRED',
             'NEW_MIXED_CHILD_POLICY_REQUIRED']
    if sources['phases'] is None:holds.append('NO_APPROVED_AUTOSOL_HL')
    return dict(schema_version=1, policy_id=POLICY_ID, status='INPUT_ROLES_REVIEWED_NOT_ADMITTED',
        capture_sha256=expected_sha256, source_owner_revision=expected_owner_revision,
        checkpoint=dict(record['checkpoint']), current_endpoint=sources['model'],
        source_starting_model=inputs[1], original_observations=sources['observations'],
        phase_source=sources['phases'], phase_metadata=record['phase_metadata'], declared_selectors=selectors,
        inherited_restraints=sources['restraints'],
        source_execution_roles=[dict(index=i,role=role,reference=ref) for i,(role,ref) in enumerate(zip(roles,inputs))],
        runtime_owned=dict(owner='registered-phosphate',intent_request=records['request'],
                           intent_sha256=scope_digest(phosphate),generated_bond=phosphate['bond'],
                           disposition='REGENERATE_THROUGH_SOURCE_OWNER_FOR_NEW_CHILD'),
        native_ready=False,checkpoint_adoption=False,scientific_approval='NOT_ASSESSED',
        source_owner_replayed=False,holds=holds)
