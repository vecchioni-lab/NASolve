"""Lossless, round-local spelling of the existing full-model PHIL policy.

Historical preparation inputs and native workers stay byte-identical. This is
one exact generated-policy adapter, not a general PHIL parser or chemistry rule.
"""
import re

from .campaign_records import path_in, read_record, write_record
from .cif_native_monomers import FULL_MODEL_PHIL

POLICY_ID = 'refinement-full-model-namespace-v1'
_SOURCE = FULL_MODEL_PHIL.encode('utf-8')
_EXECUTION = b'refinement {\n' + _SOURCE + b'}\n'


def _directory(checkpoint):
    if not isinstance(checkpoint, str) or re.fullmatch(r'refine-[0-9]{3,}', checkpoint) is None:
        raise ValueError('Refinement input adaptation requires a numbered refinement checkpoint')
    return 'AutoRefine/round_' + checkpoint.split('-')[1]


def _bound_path(reference, description, run):
    from .checkpoints import _ref_path
    path = _ref_path(reference, description, run)
    if (not isinstance(reference, dict) or type(reference.get('size')) is not int
            or reference['size'] != path.stat().st_size):
        raise ValueError('Refinement input reference size differs: ' + description)
    return path


def validate_refinement_inputs(run, restraints, reference, *, checkpoint):
    """Check ordered source membership, portable copies and exact derived bytes."""
    from .checkpoints import _ref_path
    directory = _directory(checkpoint)
    relative = directory + '/refinement_inputs.json'
    if (not isinstance(reference, dict) or reference.get('anchor') != 'run'
            or reference.get('relative_path') != relative):
        raise ValueError('Refinement input receipt must belong to its exact round')
    receipt = path_in(run, relative)
    if _bound_path(reference, 'refinement input receipt', run) != receipt:
        raise ValueError('Refinement input receipt changed location')
    record = read_record(receipt)
    if (set(record) != {'schema_version', 'policy_id', 'checkpoint', 'adaptations', 'record_sha256'}
            or type(record['schema_version']) is not int or record['schema_version'] != 1
            or record['policy_id'] != POLICY_ID or record['checkpoint'] != checkpoint
            or not isinstance(record['adaptations'], list) or not record['adaptations']
            or not isinstance(restraints, list)):
        raise ValueError('Unsupported refinement input adaptation')
    paths = [_ref_path(ref, 'refinement restraint', run) for ref in restraints]
    expected = [index for index, path in enumerate(paths) if path.read_bytes() == _SOURCE]
    actual = []
    for row in record['adaptations']:
        if (not isinstance(row, dict) or set(row) != {'index', 'source', 'execution'}
                or type(row['index']) is not int or row['index'] not in range(len(paths))):
            raise ValueError('Malformed refinement input adaptation row')
        index = row['index']; actual.append(index)
        source = _bound_path(row['source'], 'refinement input source', run)
        execution_ref = row['execution']
        execution_relative = directory + '/refinement_inputs/' + f'{index:03d}.phil'
        if (source != paths[index] or source.read_bytes() != _SOURCE
                or not isinstance(execution_ref, dict) or execution_ref.get('anchor') != 'run'
                or execution_ref.get('relative_path') != execution_relative):
            raise ValueError('Refinement input adaptation differs from its ordered source')
        execution = path_in(run, execution_relative)
        if (_bound_path(execution_ref, 'refinement input copy', run) != execution
                or execution.read_bytes() != _EXECUTION):
            raise ValueError('Refinement input copy is not the exact namespace derivative')
    if actual != expected:
        raise ValueError('Refinement input adaptation coverage/order differs')
    return record


def prepare_refinement_inputs(run, restraints, *, checkpoint):
    """Keep order and every original input; wrap only the known generated policy."""
    from .checkpoints import _file_reference, _ref_path
    directory = _directory(checkpoint)
    paths = [_ref_path(ref, 'refinement restraint', run) for ref in restraints]
    execution = list(paths); rows = []
    for index, path in enumerate(paths):
        if path.read_bytes() != _SOURCE:
            continue
        target = path_in(run, directory + '/refinement_inputs/' + f'{index:03d}.phil')
        target.parent.mkdir(exist_ok=True)
        with target.open('xb') as handle:
            handle.write(_EXECUTION)
        rows.append(dict(index=index, source=_file_reference(path, run),
                         execution=_file_reference(target, run)))
        execution[index] = target
    if not rows:
        return execution, None
    receipt = path_in(run, directory + '/refinement_inputs.json')
    write_record(receipt, dict(schema_version=1, policy_id=POLICY_ID,
                              checkpoint=checkpoint, adaptations=rows))
    reference = _file_reference(receipt, run)
    validate_refinement_inputs(run, restraints, reference, checkpoint=checkpoint)
    return execution, reference


def validate_checkpoint_refinement_inputs(run, item):
    """Read the optional execution evidence without changing inherited restraints."""
    outputs = item.get('outputs')
    if isinstance(outputs, dict) and 'refinement_inputs' in outputs:
        return validate_refinement_inputs(run, item.get('restraints'),
            outputs['refinement_inputs'], checkpoint=item.get('id'))
