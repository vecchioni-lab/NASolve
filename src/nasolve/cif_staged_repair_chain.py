"""Store each native repair proof in its own verified archive.

The existing chemistry readers work on one temporary stage at a time. Only
the model, ordered PHIL files and dictionary endpoints have persistent paths.
"""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_component_runtime import _bounded_inventory, _tree, MAX_FILES, MAX_BYTES, MAX_FILE_BYTES
from .cif_dictionary_store import _bytes
from .cif_mixed_geometry import _ref
from .cif_repair_chain import (
    ANCHOR, REPORT, STAGED_POLICY_ID, _FIXED, _check_controls, _exact,
    _need, _stage_names, _verify_stages,
)
from .cif_runtime_evidence import expanded_repair_stage, pack_runtime_evidence


def _inventory(root):
    files = _bounded_inventory(root, max_files=MAX_FILES, max_bytes=MAX_BYTES)
    dirs = sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())
    return files, dirs


def _pack_path(root, name):
    return root/'proofs'/(name + '.zip')


def _derive(root, controls, visit, *, write_file=None):
    _check_controls(controls)
    names = _stage_names(controls)
    packs = {name: _ref(_pack_path(root, name), root, ANCHOR) for name in names}
    steps = []
    endpoints = {}
    expected = {entry['path'] for entry in packs.values()}
    if 'bond_count' in controls:
        expected.update('library/' + path for path in _tree(root/'library'))

    @contextmanager
    def open_stage(name):
        with expanded_repair_stage(_pack_path(root, name), packs[name]['sha256']) as view:
            yield view/'evidence'

    def endpoint(name, original):
        relative = 'endpoints/' + name
        target = root/relative
        if write_file is not None:
            write_file(target, original.read_bytes())
        _need(target.read_bytes() == original.read_bytes(), 'Repair endpoint differs from its verified capture')
        expected.add(relative)
        return target

    def record(step):
        steps.append(dict(stage=step.stage, **step.references(step.directory, 'repair_stage_directory')))
        if step.first:
            model = step.before[1]
            endpoints['model'] = endpoint('model' + model.suffix, model)
            endpoints['phils'] = [endpoint(f'phil-{i:03d}.phil', p) for i,p in enumerate(step.before[3])]
            endpoints['before_dictionaries'] = [endpoint(f'before-{i:03d}.cif', p) for i,p in enumerate(step.before[2])]
        if step.last:
            endpoints['after_dictionaries'] = [endpoint(f'after-{i:03d}.cif', p) for i,p in enumerate(step.after[2])]
        if visit is not None:
            visit(step)

    attributed = _verify_stages(controls, open_stage, root/'library', record)
    inventory, directories = _inventory(root)
    remaining = set(inventory) - {REPORT}
    expected_dirs = {str(parent) for name in expected for parent in Path(name).parents if str(parent) != '.'}
    _need(remaining == expected and set(directories) == expected_dirs, 'Unexpected staged repair chain members')
    report = dict(_FIXED, policy_id=STAGED_POLICY_ID, controls=controls, steps=steps, archives=packs,
                  all_steps_attributed=attributed, status='ATTRIBUTED_REPAIR_CHAIN' if attributed else 'REVIEW',
                  outputs=[_ref(root/name,root,ANCHOR) for name in sorted(expected)])
    return dict(endpoints, report=report)


def inspect_staged_chain(root, saved, visit):
    before = _inventory(root)
    result = _derive(root, saved['controls'], visit)
    _need(_exact(result['report'], saved) and _inventory(root) == before,
          'Staged repair evidence or its report does not reproduce')
    return result


def write_staged_chain(output, sources, controls):
    """Verify fresh, separate archives and recheck their original owners before publishing."""
    _check_controls(controls)
    output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='.staged-repairs-',dir=output.parent) as temporary:
        root = Path(temporary)/'chain'
        root.mkdir()
        pins = {}
        file_count = byte_count = 0

        def reserve(size):
            nonlocal file_count, byte_count
            _need(file_count < MAX_FILES and size <= MAX_FILE_BYTES and byte_count + size <= MAX_BYTES,
                  'Staged repair publication exceeds its file or byte allowance')
            file_count += 1
            byte_count += size

        def write_file(target, data):
            reserve(len(data))
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(data)

        # Hold only hashes for previously visited sources.
        for name in _stage_names(controls):
            source = sources[name]
            pins[name] = _inventory(source)
            archive = _pack_path(root, name)
            archive.parent.mkdir(parents=True,exist_ok=True)
            pending = root.parent/'next-stage.zip'
            meta = pack_runtime_evidence(source, pending, expected_inventory=pins[name])
            reserve(meta['archive_bytes'])
            pending.rename(archive)
        if 'library' in sources:
            source = sources['library']
            pins['library'] = _inventory(source)
            for name,data in _tree(source).items():
                dest = root/'library'/name
                write_file(dest, data)
            _need(_inventory(root/'library') == pins['library'], 'Energy library changed during freezing')
        result = _derive(root, controls, None, write_file=write_file)
        write_file(root/REPORT, _bytes(result['report']))
        # The report itself counts toward the same outer file and byte limits.
        sealed_files, sealed_directories = _inventory(root)
        del sealed_files[REPORT]
        _need(all(_inventory(source) == pins[name] for name,source in sources.items()),
              'Repair evidence changed during freezing')
        # Exclusive reservation protects even an empty concurrent destination.
        # An interrupted transfer has no completion record until its last move.
        output.mkdir(exist_ok=False)
        for child in root.iterdir():
            if child.name != REPORT:
                child.rename(output/child.name)
        _need(_inventory(output) == (sealed_files, sealed_directories),
              'Staged repair evidence changed during transfer')
        (root/REPORT).rename(output/REPORT)
    return result['report']
