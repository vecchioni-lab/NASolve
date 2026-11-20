"""Bounded, lossless storage of the original working objects of a mixed attempt.

The retained owner needs the ordinary model, public runtime and process records
at their normal paths. Original native captures and intermediate repair proofs
can be read one authenticated file at a time, including from a relocated archive.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from pathlib import Path
import zlib

from . import cif_complete_stages as stages, cif_runtime_evidence as storage
from .cif_dictionary_sites import _need, _read
from .cif_review_transport import _alias, _strict

POLICY_ID = 'cif-complete-attempt-staged-working-archive-v1'
PACKED = stages.EXECUTION + '.nasolve-stage-objects'
_ACTIVE = ContextVar('complete_attempt_staged_read', default=None)


def _split(files):
    core = {name:ref for name,ref in files.items() if stages.stage_root(name) is None}
    sources = {ref['sha256']:name for name,ref in files.items()}
    core_sources = {ref['sha256']:name for name,ref in core.items()}
    cold = {identifier:name for identifier,name in sources.items() if identifier not in core_sources}
    return core, core_sources, cold


def _ref(data):
    return {'sha256':sha256(data).hexdigest(), 'size':len(data)}


def _verify(data, ref):
    _need(_ref(data) == ref, 'Staged working object differs from its recorded bytes')
    return data


def _original_layout(files, directories, prefixes):
    bounds = stages.AttemptBounds(prefixes)
    storage._file_index(files, directories, max_files=bounds.max_files)
    _need(all(_alias(n) != PACKED and not _alias(n).startswith(PACKED+'/') for n in (*files, *directories)),
          'Original attempt collides with its reserved working archive layout')
    for name, ref in files.items():
        bounds.charge(name, ref['size'])
    sizes = {ref['sha256']:ref['size'] for ref in files.values()}
    _need(all(sizes[ref['sha256']] == ref['size'] for ref in files.values()), 'Contradictory original object sizes')


def _unpack(payload, packed_name, expected):
    if packed_name.endswith('.deflate'):
        try:
            decoder = zlib.decompressobj()
            raw = decoder.decompress(payload, expected['size'] + 1)
        except zlib.error as exc:
            raise ValueError('Damaged staged working object') from exc
        _need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
              'Incomplete or oversized staged working object')
        return _verify(raw, expected)
    return _verify(payload, expected)


def encode(root, files, directories, prefixes):
    """Store each distinct original once. Keep public and process paths available."""
    _original_layout(files, directories, prefixes)
    core, hot_sources, cold = _split(files)
    projected = core.copy()
    objects = {}
    total = 0

    def store(data, ref):
        nonlocal total
        if ref['sha256'] not in objects:
            total += len(data)
            _need(total <= storage.MAX_ACTIVE_BYTES and len(objects)+3 <= 1024,
                  'Staged objects exceed shared archive/physical bounds')
            objects[ref['sha256']] = data

    for name in hot_sources.values():
        ref = files[name]
        store(_verify(stages.read_sized(root/name, ref['size']), ref), ref)
    for identifier, name in sorted(cold.items()):
        data = _verify(stages.read_sized(root/name, files[name]['size']), files[name])
        compressed = zlib.compress(data, level=9)
        if len(compressed) < len(data):
            payload, suffix = compressed, '.deflate'
        else:
            payload, suffix = data, '.raw'
        ref = _ref(payload)
        projected[f'{PACKED}/{identifier}{suffix}'] = ref
        store(payload, ref)
    dirs = sorted([*directories, PACKED]) if cold else directories
    return projected, dirs, objects


def validate_contents(index, objects, prefixes, finished):
    original = finished.get('artifacts') if isinstance(finished, dict) else None
    _need(isinstance(original, dict) and set(original) == {'files','directories'}
          and isinstance(original['files'], dict) and 'finished.json' not in original['files'],
          'Staged archive lacks its original completion inventory')
    finished_ref = index['files']['finished.json']
    files = dict(original['files'], **{'finished.json':finished_ref})
    dirs = original['directories']
    check_projection(index, objects, prefixes, files, dirs)
    return {'files':files, 'directories':dirs}


def check_projection(index, objects, prefixes, files, dirs):
    """Bind each packed object to an exact, independently supplied inventory."""
    _original_layout(files, dirs, prefixes)
    core, _, cold = _split(files)
    expected = core.copy()
    for identifier, name in cold.items():
        choices = [f'{PACKED}/{identifier}{suffix}' for suffix in ('.deflate', '.raw')]
        present = [p for p in choices if p in index['files']]
        _need(len(present) == 1, 'Missing or ambiguous staged original')
        packed = present[0]
        ref = index['files'][packed]
        data = objects[ref['sha256']]
        _need(not packed.endswith('.deflate') or len(data) < files[name]['size'],
              'Invalid staged compression binding')
        _unpack(data, packed, files[name])
        expected[packed] = ref
    _need(expected == index['files'] and index['directories'] == (sorted([*dirs, PACKED]) if cold else dirs),
          'Staged physical projection differs from its original inventory')


@contextmanager
def owner_view(root, index, original):
    """Only the verified archive decoder may supply a projected inventory."""
    physical = {'files':index['files'], 'directories':index['directories']}
    _, hot, _ = _split(original['files'])
    token = _ACTIVE.set((root, physical, original, hot))
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def view_inventory(root, prefixes):
    bound = _ACTIVE.get()
    if bound is None or Path(root).absolute() != bound[0]:
        return None
    root, physical, original, _ = bound
    # Authenticate the actual visible bytes again; a missing or changed working
    # file after opening the archive cannot be masked by the original inventory.
    stages.working_inventory(root, prefixes, expected=physical)
    return {'files':{name:ref.copy() for name,ref in original['files'].items()},
            'directories':original['directories'].copy()}


def read_member(root, name):
    """Read one original file from a verified staged or an ordinary working view."""
    root = Path(root).absolute()
    _need(_strict(name), 'Unsafe original working file')
    bound = _ACTIVE.get()
    if bound is None or root != bound[0]:
        return _read(root/name)
    _, physical, original, hot = bound
    _need(name in original['files'], 'Unrecorded original working member')
    expected = original['files'][name]
    identifier = expected['sha256']
    if identifier in hot:
        return _verify(stages.read_sized(root/hot[identifier], expected['size']), expected)
    for suffix in ('.deflate', '.raw'):
        packed = f'{PACKED}/{identifier}{suffix}'
        if packed in physical['files']:
            ref = physical['files'][packed]
            data = _verify(stages.read_sized(root/packed, ref['size']), ref)
            return _unpack(data, packed, expected)
    raise ValueError('Missing original working object')
