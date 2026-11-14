"""Read-only dictionary-engine settings for an explicitly selected Phenix SDK.

Source fingerprints describe the installed implementation, not observed native
imports or scientific usability. Existing acquisition/native gates remain required.
No installation discovery, generation, model editing or attempt ownership occurs.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from .cif_acquisition_attempt import _generation_binding
from .cif_dictionary_sites import _consumer, _need
from .cif_elbow_contract import MAX_SOURCE_BYTES
from .cif_generation_acquisition import generation_dictionary_options
from .cif_postmr_cache import _API, _ENERGY, verify_current_consumer
from .cif_source_candidate import SOURCE_PATHS
from .phenix_runtime import PhenixInstallation


@dataclass(frozen=True)
class PhenixDictionaryConfiguration:
    """Live caller arguments; generation includes a private copy of the environment.

    This is not an artifact schema. Pass the values to the existing request APIs,
    which freeze identities and limits without serializing the live environment.
    """
    consumer: dict
    generation: dict = field(repr=False)
    ready_set_executable: Path


def _library(root):
    """Resolve one supported packaged scope, without scanning scientific inputs."""
    candidates = set()
    for directory in ('lib', 'lib64'):
        for site in (root/directory).glob('python*/site-packages'):
            resolved = site.resolve(strict=True)
            _need(resolved.is_dir() and resolved.is_relative_to(root)
                  and resolved.name == 'site-packages', 'Unselected packaged Phenix library')
            if any((resolved/name).exists() for name in (*_API, *_ENERGY, *SOURCE_PATHS)):
                candidates.add(resolved)
    _need(len(candidates) == 1, 'Require one unambiguous supported packaged Phenix library')
    return candidates.pop()


def _pin(path, root, *, source=False):
    _need(path.is_file() and not path.is_symlink()
          and path.resolve(strict=True).is_relative_to(root), 'Unselected or symlinked Phenix file')
    if source:
        _need(path.stat().st_size <= MAX_SOURCE_BYTES, 'Oversized installed Phenix source')
    data = path.read_bytes()
    _need(not source or len(data) <= MAX_SOURCE_BYTES, 'Oversized installed Phenix source')
    return dict(anchor='phenix_installation', path=path.relative_to(root).as_posix(),
                sha256=sha256(data).hexdigest(), size=len(data))


def configure_dictionary_engine(installation: PhenixInstallation, *, expected_dialect: str,
        single_block_steps=180, timeout_seconds=600, max_attempts=2,
        bond_representation_policy=None, source_input_policy=None) -> PhenixDictionaryConfiguration:
    """Derive existing consumer/generation arguments from the selected installation.

    The caller supplies an already discovered installation and an explicit source
    reader dialect. An explicit source_input_policy lets the existing owner derive
    and freeze the actual reader dialect from that source without changing its
    authority. No ambient SDK or historical validation capsule is consulted.
    Only one complete lib[64]/python*/site-packages scope is supported. File pins
    are rechecked before return; actual execution still verifies native bindings.

    This factory configures a new request. It does not renew a frozen request's
    recipe, producer identity, process ownership, allowance or retry permission.
    Existing explicit configurations and cache-only paths remain supported.
    """
    selected = deepcopy(installation)
    _need(selected.root is not None and isinstance(selected.version, str)
          and selected.version.strip().lower() not in {'', 'unknown'},
          'Require a selected Phenix root and known version')
    _need(isinstance(selected.environment, dict)
          and all(isinstance(k, str) and k and '=' not in k and '\0' not in k
                  and isinstance(v, str) and '\0' not in v
                  for k, v in selected.environment.items()), 'Invalid selected execution environment')
    root = Path(selected.root).expanduser().resolve(strict=True)
    _need(root.is_dir(), 'Selected Phenix root is not a directory')
    names = ('phenix.python', 'phenix.elbow', 'phenix.ready_set')
    _need(all(name in selected.executables for name in names), 'Selected Phenix lacks required dictionary dispatchers')
    dispatchers = {name:Path(selected.executables[name]).expanduser().resolve(strict=True) for name in names}
    dispatcher_pins = {name:_pin(path, root) for name, path in dispatchers.items()}
    site = _library(root)
    pins = {name:_pin(site/name, root, source=True) for name in (*_API, *_ENERGY, *SOURCE_PATHS)}
    # The maintained source-preserving builder uses the same iotbx library anchor.
    consumer = dict(name='Phenix/CCTBX', version=selected.version,
        executable_sha256=dispatcher_pins['phenix.python']['sha256'],
        api_sources=[{k:v for k, v in pins[name].items() if k != 'size'} for name in _API],
        energy_sources=[{k:v for k, v in pins[name].items() if k != 'size'} for name in _ENERGY])
    generation = dict(installation_root=root, python_executable=dispatchers['phenix.python'],
        elbow_executable=dispatchers['phenix.elbow'], api_sources=[pins['iotbx/phil.py']],
        prior_sources=[pins[name] for name in SOURCE_PATHS], environment=selected.environment,
        expected_dialect=expected_dialect, phenix_version=selected.version,
        single_block_steps=single_block_steps, timeout_seconds=timeout_seconds, max_attempts=max_attempts)
    if bond_representation_policy is not None:
        generation['bond_representation_policy'] = bond_representation_policy
    if source_input_policy is not None:
        generation['source_input_policy'] = source_input_policy
    _consumer(consumer)
    generation_dictionary_options(generation)
    _generation_binding(generation)
    verify_current_consumer(selected, dispatchers['phenix.ready_set'], consumer)
    _need(installation == selected and Path(selected.root).expanduser().resolve(strict=True) == root
          and _library(root) == site, 'Selected Phenix configuration changed while reading')
    for name, path in dispatchers.items():
        _need(Path(selected.executables[name]).expanduser().resolve(strict=True) == path
              and _pin(path, root) == dispatcher_pins[name], 'Selected Phenix dispatcher changed while reading')
    _need(all(_pin(site/name, root, source=True) == pin for name, pin in pins.items()),
          'Selected Phenix sources changed while reading')
    return PhenixDictionaryConfiguration(consumer, generation, dispatchers['phenix.ready_set'])
