"""Create-only byte evidence for a completed, verified-stopped child process.

This bounded Python owner does not validate crystallographic output semantics,
change trial admission, freeze files at the OS level, or authorize retirement.
"""
from .child_process import inspect_child, _root, _file, _inputs, _need
from .compact import read_projection
from .recipe import checksum
from .storage import _snapshot, _hash
from .. import campaign_records as records

KIND = 'metal-fdp-child-output-evidence'
REQUIRED_OUTPUTS = frozenset({'native-result.json.gz', 'final.pdb', 'effective-final.phil'})
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
MAX_BYTES = 1024 ** 3
MAX_RECORD_BYTES = 1024 * 1024
JOB = {'anchor': 'child', 'relative_path': 'native/fdp/job'}


def _completed(root, request_id):
    report = inspect_child(root, request_id=request_id)
    outcome = report['outcome']
    _need(report['status'] == 'COMPLETED' and report['stopped_verified']
          and outcome and outcome.get('stopped_verified') is True
          and outcome.get('parent_transport_verified') is True,
          'Output evidence requires a completed verified-stopped child')
    return outcome['record_sha256']


def _inventory(root, request_id, max_bytes):
    _need(type(max_bytes) is int and 0 < max_bytes <= MAX_BYTES, 'Invalid output byte budget')
    outcome_id = _completed(root, request_id)
    job = _root(root / JOB['relative_path'])
    states = _snapshot(job)
    _need(REQUIRED_OUTPUTS <= states.keys()
          and all(states[name][2] > 0 for name in REQUIRED_OUTPUTS),
          'Missing or empty required native output')
    total = sum(state[2] for state in states.values())
    _need(total <= max_bytes, 'Output inventory exceeds byte budget')
    request = read_projection(_file(root/'inputs', 'request.json'), max_projection_bytes=MAX_RECORD_BYTES)
    _inputs(job, request['files'])
    files = {name: {'sha256': _hash(_file(job, name), state), 'size': state[2]}
             for name, state in sorted(states.items())}
    _need(_snapshot(job) == states, 'Output inventory changed during inspection')
    _need(_completed(root, request_id) == outcome_id, 'Child outcome changed during inventory')
    return dict(kind=KIND, schema_version=1, request_id=request_id,
                outcome_sha256=outcome_id, job=dict(JOB), files=files,
                required_outputs=sorted(REQUIRED_OUTPUTS), total_bytes=total,
                max_bytes=max_bytes, scientific_acceptance='NOT_ASSESSED',
                retirement_authorized=False)


def freeze_child_outputs(directory, *, request_id, max_bytes=DEFAULT_MAX_BYTES):
    """Seal exact present bytes once; required names mean presence, not validity.

    All job files are inventoried, including inputs and logs. A failed, timed-out,
    live, uncertain, incomplete or changed child is never given this receipt.
    """
    root = _root(directory)
    target = root/'outputs.json'
    _need(not target.exists() and not target.is_symlink(), 'Output evidence already exists')
    value = _inventory(root, request_id, max_bytes)
    record = records.write_record(target, value)
    return inspect_child_outputs(root, request_id=request_id, output_id=record['record_sha256'])


def inspect_child_outputs(directory, *, request_id, output_id):
    """Verify an independently pinned receipt and exact current bytes, read-only."""
    checksum(output_id, 'independent output evidence identity')
    root = _root(directory)
    target = _file(root, 'outputs.json')
    _need(target.stat().st_size <= MAX_RECORD_BYTES, 'Output evidence record exceeds byte budget')
    record = records.read_record(target)
    _need(record['record_sha256'] == output_id, 'Output evidence identity changed')
    _need(record.get('kind') == KIND and type(record.get('schema_version')) is int
          and record['schema_version'] == 1 and record.get('request_id') == request_id,
          'Unsupported or mismatched output evidence')
    current = _inventory(root, request_id, record.get('max_bytes'))
    _need({key: value for key, value in record.items() if key != 'record_sha256'} == current,
          'Output evidence or files changed')
    return record
