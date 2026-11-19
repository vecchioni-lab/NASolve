"""Frozen explicit canonical seeds within the existing PostMR construction stage.

No subprocess, retry, source selection or native qualification is owned here.
Cold readback reproduces only the pure coordinate construction from saved inputs.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from .campaign_records import path_in, read_record, write_record
from .cif_dictionary_sites import _read
from .cif_dictionary_store import _snapshot_destination
from .postmr_canonical_seed import canonical_parent_seed

POLICY_ID = 'postmr-explicit-canonical-parent-input-v1'
ANCHOR = 'canonical_parent_input'
REPORT = 'canonical_input.json'


def canonical_input_plan(actions, dictionaries, passthrough_sites=()):
    """Validate explicit site choices without allocating output or guessing sources."""
    by_site = {a.site: a for a in actions}
    if not dictionaries or len(by_site) != len(actions) or set(dictionaries) - by_site.keys():
        raise ValueError('Canonical seed choices require distinct declared construction sites')
    result = []
    for action in actions:
        if action.site not in dictionaries:
            continue
        if (action.method != 'coot-parent-overlap' or action.parent_code not in {'DA', 'DC', 'DG', 'DT'}
                or action.before == action.parent_code or action.site in passthrough_sites):
            raise ValueError('Canonical seed choice requires an eligible modified-parent overlap')
        paths = dictionaries[action.site]
        if not isinstance(paths, (tuple, list)) or len(paths) != 2:
            raise ValueError('Supply the source and canonical dictionary paths for each seed site')
        result.append((action, Path(paths[0]), Path(paths[1])))
    return result


def _reference(root, path):
    data = _read(path)
    return dict(anchor=ANCHOR, path=path.relative_to(root).as_posix(),
                sha256=sha256(data).hexdigest(), size=len(data))


def _resolve(root, reference):
    if not isinstance(reference, dict) or reference.get('anchor') != ANCHOR:
        raise ValueError('Canonical seed input needs its declared local anchor')
    path = path_in(root, reference.get('path'))
    if _reference(root, path) != reference:
        raise ValueError('Canonical seed input checksum differs')
    return path


def prepare_canonical_parent_input(model, plan, output):
    """Freeze explicit inputs and return a validated seed inside fresh Coot work."""
    output = _snapshot_destination(output)
    paths = [Path(model), *[p for _, source, template in plan for p in (source, template)]]
    originals = {p: _read(p) for p in paths}
    if not plan or any(output == p or output in p.parents for p in paths):
        raise ValueError('Require a fresh canonical seed destination separate from inputs')
    output.mkdir(parents=True)
    def put(name, data):
        path = output / name
        with path.open('xb') as handle:
            handle.write(data)
        return path
    try:
        current = originals[Path(model)]
        initial = _reference(output, put('input.pdb', current))
        frozen = {}
        def dictionary(path):
            data = originals[path]; digest = sha256(data).hexdigest()
            if digest not in frozen:
                frozen[digest] = put('dictionary-' + digest + '.cif', data)
            return frozen[digest]
        steps = []
        for action, source, template in plan:
            source, template = dictionary(source), dictionary(template)
            data, proof = canonical_parent_seed(current, action.site, source, action.before,
                                                template, action.parent_code)
            current = data
            steps.append(dict(action=asdict(action), source=_reference(output, source),
                              template=_reference(output, template),
                              output=dict(sha256=sha256(current).hexdigest(), size=len(current)), proof=proof))
        final = put('canonical.pdb', current)
        write_record(output / REPORT, dict(schema_version=1, policy_id=POLICY_ID,
            input=initial, steps=steps, model=_reference(output, final)))
        return read_canonical_parent_input(output)
    finally:
        if any(_read(p) != data for p, data in originals.items()):
            raise ValueError('Original canonical construction input changed')


def read_canonical_parent_input(directory):
    """Validate saved seed bytes and proofs without native execution or writes."""
    from .postmr import MutationAction
    root = Path(directory)
    record = read_record(path_in(root, REPORT))
    if (set(record) != {'schema_version', 'policy_id', 'input', 'steps', 'model', 'record_sha256'}
            or type(record['schema_version']) is not int or record['schema_version'] != 1
            or record['policy_id'] != POLICY_ID or not isinstance(record['steps'], list)
            or not record['steps']):
        raise ValueError('Unsupported canonical input receipt')
    current = _read(_resolve(root, record['input']))
    dictionaries = {}
    for step in record['steps']:
        if not isinstance(step, dict) or set(step) != {'action', 'source', 'template', 'output', 'proof'}:
            raise ValueError('Incomplete canonical input step')
        try:
            action = MutationAction(**step['action'])
        except (TypeError, KeyError) as exc:
            raise ValueError('Invalid canonical input action') from exc
        if asdict(action) != step['action'] or action.site in dictionaries:
            raise ValueError('Ambiguous canonical input actions')
        source, template = [_resolve(root, step[k]) for k in ('source', 'template')]
        dictionaries[action.site] = (source, template)
        canonical_input_plan((action,), {action.site: (source, template)})
        data, proof = canonical_parent_seed(current, action.site, source, action.before,
                                            template, action.parent_code)
        if step['output'] != dict(sha256=sha256(data).hexdigest(), size=len(data)) or step['proof'] != proof:
            raise ValueError('Saved canonical seed differs from its pure construction proof')
        current = data
    final = _resolve(root, record['model'])
    if _read(final) != current:
        raise ValueError('Canonical construction result is not its final recorded seed')
    return dict(model=final, directory=root, receipt=record)
