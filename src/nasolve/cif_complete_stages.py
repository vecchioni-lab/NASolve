"""Bound the original working files of a mixed complete dictionary request.

An attribution stage is a bounded proof in its own right. The complete owner
keeps all original paths, including partial outputs from a stopped attempt.
The aggregate raw envelope is that of the existing complete parent and its
children. No individual science proof or temporary archive view gets larger.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import os
import re

from . import cif_component_runtime as trees
from .cif_dictionary_sites import _need
from .cif_repair_chain import MAX_BONDS, MAX_PLANES
from .cif_review_transport import _strict
from .cif_runtime_evidence import _file_index

POLICY_ID = 'cif-complete-request-staged-artifacts-v5'
EXECUTION = 'repair/attempts/attempt-0001/execution/'
_PROOF_LIMITS = {'plane': MAX_PLANES, 'bond': MAX_BONDS}


def stage_root(name):
    """Fixed producer paths, independent of chemical names and outcomes."""
    if not name.startswith(EXECUTION):
        return None
    pieces = name[len(EXECUTION):].split('/')
    if len(pieces) < 2:
        return None
    first = pieces[0]
    if first == 'native':
        if len(pieces) >= 3 and (pieces[1] == 'baseline' or re.fullmatch(r'[0-9]{3}', pieces[1])):
            return EXECUTION + first + '/' + pieces[1]
        return None
    if first in {'attribution', 'original-gradient', 'repaired-gradient'}:
        return EXECUTION + first
    match = re.fullmatch(r'(plane|bond)-attribution-([0-9]{3})', first)
    if match and int(match[2]) < _PROOF_LIMITS[match[1]]:
        return EXECUTION + first
    return None


class AttemptBounds:
    """Charge the original complete envelope and the individual producer before I/O."""

    def __init__(self, prefixes):
        self.prefixes = prefixes
        self.max_files = (1 + len(prefixes)) * trees.MAX_FILES
        self.max_bytes = (1 + len(prefixes)) * trees.MAX_BYTES
        self.files = Counter()
        self.sizes = Counter()
        self.count = 0
        self.size = 0

    def charge(self, name, size):
        owner = stage_root(name) or next((p for p in self.prefixes if name.startswith(p)), '')
        self.count += 1
        self.size += size
        self.files[owner] += 1
        self.sizes[owner] += size
        _need(0 <= size <= trees.MAX_FILE_BYTES and self.count <= self.max_files
              and self.size <= self.max_bytes and self.files[owner] <= trees.MAX_FILES
              and self.sizes[owner] <= trees.MAX_BYTES, 'Complete evidence exceeds frozen bounds')


def read_sized(path, size):
    """Limit the actual read even if a working file grows after inspection."""
    path = Path(path).absolute()
    _need(0 <= size <= trees.MAX_FILE_BYTES and path.is_file()
          and not any(p.is_symlink() for p in (path,*path.parents)),
          'Unsafe or oversized complete evidence file')
    with path.open('rb') as handle:
        _need(os.fstat(handle.fileno()).st_size == size, 'Complete evidence size changed')
        data = handle.read(size+1)
    _need(len(data) == size, 'Complete evidence changed while reading')
    return data


def working_inventory(root, prefixes, *, expected=None):
    """Hash each raw file independently. Empty directories and partial jobs survive."""
    root = Path(root).absolute()
    _need(root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)), 'Unsafe complete evidence root')
    bounds = AttemptBounds(prefixes)
    files = {}
    directories = []
    expected_dirs = set(expected['directories']) if expected is not None else None
    pending = [root]
    while pending:
        directory = pending.pop()
        _need(not any(p.is_symlink() for p in (directory, *directory.parents)), 'Unsafe complete evidence directory')
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                name = path.relative_to(root).as_posix()
                _need(_strict(name) and not entry.is_symlink(), 'Unsafe complete evidence member')
                if entry.is_dir(follow_symlinks=False):
                    if expected_dirs is not None:
                        _need(name in expected_dirs, 'Unexpected staged working directory')
                    directories.append(name)
                    _need(len(directories) <= 4*bounds.max_files + int(expected is not None), 'Complete directory count exceeds frozen bounds')
                    pending.append(path)
                else:
                    _need(entry.is_file(follow_symlinks=False), 'Nonregular complete evidence member')
                    size = entry.stat(follow_symlinks=False).st_size
                    if expected is None:
                        bounds.charge(name, size)
                    else:
                        ref = expected['files'].get(name)
                        _need(ref is not None and ref['size'] == size, 'Changed staged working file or size')
                    data = read_sized(path, size)
                    files[name] = {'size':size, 'sha256':sha256(data).hexdigest()}
    directories.sort()
    inventory = {'files':files, 'directories':directories}
    if expected is None:
        _file_index(files, directories, max_files=bounds.max_files)
    else:
        _need(inventory == expected, 'Staged working view differs from its verified contents')
    return inventory
