"""Bind an admitted request to a complete, nonexecuted child command.

Uses the existing request reader, anchored input resolver and ordinary command
builder. The source owner still admits the parent/endpoint and original scientific
meaning; this adapter checks exact files, order, selectors and policy derivation.
It creates no files, numbered checkpoint, runtime policy or process. In particular,
it does not qualify mixed XYZ/group-B execution under a historical runtime.
"""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

from .autorefine import ReflectionPlan, build_refine_command
from .refinement_inputs import _bound_path
from .refinement_parallelity import read_execution_request
from .refinement_parameter_files import rebind_miller_files
from .refinement_parameter_composition import _definitions

POLICY_ID = 'declared-refinement-command-binding-v1'


def _portable(reference):
    if (not isinstance(reference, dict)
            or reference.get('anchor') not in ('run', 'dataset', 'repository')
            or not isinstance(reference.get('relative_path'), str)
            or not reference['relative_path'] or reference['relative_path'].startswith('/')
            or '..' in reference['relative_path'].split('/')):
        raise ValueError('Command inputs require declared portable references')


def _plan(command, count):
    """Recognize only the complete existing ordinary command shape."""
    tail = command[1 + count:]
    if not tail or tail[0] != '--overwrite':
        raise ValueError('Unknown complete refinement command layout')
    values = {}
    for token in tail[1:]:
        key, separator, value = token.partition('=')
        if not separator or key in values:
            raise ValueError('Unknown or duplicate refinement command argument')
        values[key] = value
    try:
        labels = tuple(values['xray_data.labels'].split(','))
        free = values['xray_data.r_free_flags.label']
        test = int(values['xray_data.r_free_flags.test_flag_value'])
        anomalous = values['xray_data.force_anomalous_flag_to_be_equal_to']
        if (not all(labels) or not free or free.lower() == 'saflags'
                or anomalous not in ('True', 'False')):
            raise ValueError('Invalid observation/Free-R command selectors')
        phase = values.get('experimental_phases.file_name')
        phase_labels = tuple(values.get('experimental_phases.labels', '').split(',')) if phase else ()
        if phase and (len(phase_labels) != 4 or not all(phase_labels)):
            raise ValueError('Incomplete experimental-phase command selectors')
        if phase and (count < 4 or phase != command[count - 1]):
            raise ValueError('Phase command differs from the declared positional input')
        plan = ReflectionPlan(labels, free, test, anomalous == 'True', phase_labels,
                              Path(phase) if phase else None, False, False, None)
        restraints = [Path(p) for p in command[3:count - (1 if phase else 0)]]
        expected = build_refine_command(Path(command[0]), Path(command[2]),
            Path(command[1]), restraints, Path(command[count]), plan)
        # Source executable is historical provenance; only the arguments define
        # this supported shape. No native tool is invoked or discovered here.
        if expected[1:] != command[1:]:
            raise ValueError('Command differs from the supported ordinary argument policy')
        return plan
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError('Incomplete declared refinement command') from exc


def _check_policy(policy, plan, observation, phase, *, expected_target="auto"):
    """Require explicit selector agreement and no hidden extra file dependencies."""
    from iotbx import phil
    from iotbx.cli_parser import CCTBXParser
    from phenix.programs.phenix_refine import Program
    import io
    parser = CCTBXParser(program_class=Program, logger=io.StringIO())
    master = parser.master_phil
    master.adopt_scope(parser.data_manager.master_phil)
    path_fields = {row.path for row in master.all_definitions()
                   if str(row.object.type) == 'path'}
    tree = phil.parse(policy.decode('ascii'), process_includes=False)
    definitions = list(_definitions(tree))
    # The qualified ordinary writer names inputs in DataManager; other explicit
    # file/output locations require their own owner, not guessed replacement.
    for item in definitions:
        name = item.full_path()
        leaf = name.rsplit('.', 1)[-1]
        if ((name in path_fields or leaf in ('file', 'file_name', 'file_names', 'directory', 'prefix', 'filename'))
                and name != 'data_manager.miller_array.file'
                and [w.value for w in item.words] != ['None']):
            raise ValueError('Additional policy file/output dependency needs an explicit owner: ' + name)
        if name == 'refinement.main.target' and [w.value for w in item.words] != [expected_target]:
            raise ValueError('Command target differs from the declared policy target')
    extracted = master.fetch(source=tree).extract()
    arrays = getattr(getattr(extracted, 'data_manager', None), 'miller_array', None)
    if arrays is None:
        raise ValueError('Missing DataManager source selectors')
    if not isinstance(arrays, list):
        arrays = [arrays]
    actual = []
    for row in arrays:
        rows = row.labels if isinstance(row.labels, list) else [row.labels]
        actual.append((row.file, [entry.name for entry in rows]))
    expected = [(observation, [','.join(plan.observation_labels), plan.free_r_label])]
    if phase:
        expected.append((phase, [','.join(plan.phase_labels)]))
    if actual != expected:
        raise ValueError('Parameter selectors differ from the exact command inputs/labels/order')
    return extracted


def bind_command(run, *, request_reference, source_checkpoint, endpoint_reference,
                 parameters_reference, parameter_receipt, executable):
    """Return (argv, ordered input Paths, compact binding receipt), without writes.

    Call after the source owner admits the exact ordinary parent and its returned
    endpoint. ``endpoint_reference`` is that returned model, never an inferred
    replay of the source request's starting model. The new parameter file must
    already exist and exactly replay ``rebind_miller_files``. This first boundary
    supports ordinary DataManager policies and separate optional HL input only;
    additional overrides, alternate command shapes, nested policy file references
    and changed scientific recipes refuse. Restraint contents are inherited,
    checksummed opaque inputs whose chemical/file admission remains with their
    existing owners. Current executable qualification remains with the caller.

    The caller must revalidate and freeze through the existing numbered owner
    before dispatch; a returned argv is a proposal, not execution authorization.
    """
    run = Path(run).expanduser().resolve()
    for ref in (request_reference, endpoint_reference, parameters_reference):
        _portable(ref)
    request = read_execution_request(run, request_reference, checkpoint=source_checkpoint)
    refs = request['inputs']
    if len(refs) < 3:
        raise ValueError('Require observations, source model and policy in the checked request')
    for ref in refs:
        _portable(ref)
    paths = [_bound_path(ref, 'declared command input', run) for ref in refs]
    command = request['command']
    old = command[1:1 + len(paths)]
    if (len(old) != len(paths) or len(set(old)) != len(old)
            or len(set(paths)) != len(paths)
            or any(not Path(value).is_absolute() for value in old)):
        raise ValueError('Require unique declared positional command input identities')
    plan = _plan(command, len(paths))
    phase_index = len(paths) - 2 if plan.phase_file is not None else None
    expected_bindings = [dict(historical_file=old[i], resolved_file=str(paths[i]),
        sha256=refs[i]['sha256'], source_reference=refs[i])
        for i in [0, *([phase_index] if phase_index is not None else [])]]
    if not isinstance(parameter_receipt, dict) or parameter_receipt.get('bindings') != expected_bindings:
        raise ValueError('Parameter binding receipt differs from exact checked inputs')
    raw = paths[-1].read_bytes()
    derived, replay = rebind_miller_files(raw, expected_policy_sha256=refs[-1]['sha256'], bindings=expected_bindings)
    if replay != parameter_receipt:
        raise ValueError('Parameter derivation receipt failed exact replay')
    parameters = _bound_path(parameters_reference, 'derived child parameters', run)
    endpoint = _bound_path(endpoint_reference, 'admitted returned endpoint', run)
    if parameters in paths or parameters == endpoint:
        raise ValueError('Child policy must be a separate declared file')
    if parameters.read_bytes() != derived:
        raise ValueError('Child policy differs from the exact approved file derivative')
    _check_policy(raw, plan, old[0], old[phase_index] if phase_index is not None else None)
    _check_policy(derived, plan, str(paths[0]), str(paths[phase_index]) if phase_index is not None else None)
    target = Path(executable).expanduser().resolve()
    if not target.is_file():
        raise ValueError('Require an explicit available refinement executable')
    new_plan = replace(plan, phase_file=paths[phase_index] if phase_index is not None else None)
    restraints = paths[2:phase_index if phase_index is not None else -1]
    result = build_refine_command(target, endpoint, paths[0], restraints, parameters, new_plan)
    inputs = [paths[0], endpoint, *restraints,
              *([paths[phase_index]] if phase_index is not None else []), parameters]
    file_keys = ('xray_data.file_name=', 'xray_data.r_free_flags.file_name=', 'experimental_phases.file_name=')
    retained = lambda cmd: [a for a in cmd[1 + len(paths):] if not a.startswith(file_keys)]
    if retained(result) != retained(command):
        raise ValueError('Binding changed scientific command arguments')
    # Verify source/file bytes again before returning; execution owner still
    # closes the later check-to-use interval through its existing frozen request.
    read_execution_request(run, request_reference, checkpoint=source_checkpoint)
    _bound_path(endpoint_reference, 'returned endpoint', run)
    _bound_path(parameters_reference, 'child policy', run)
    receipt = dict(schema_version=1, policy_id=POLICY_ID,
        source_checkpoint=source_checkpoint, source_request=request_reference,
        endpoint=endpoint_reference, parameters=parameters_reference,
        inputs=[refs[0], endpoint_reference, *refs[2:-1], parameters_reference],
        parameter_derivation=parameter_receipt,
        command_sha256=sha256(json.dumps(result, separators=(',', ':')).encode()).hexdigest(),
        executable=str(target), has_phases=phase_index is not None,
        non_file_arguments_unchanged=True,
        status='COMMAND_BOUND_NOT_EXECUTED',
        limit='Source owner admits endpoint/science; versioned execution and checkpoint closure remain required')
    return result, inputs, json.loads(json.dumps(receipt, allow_nan=False))
