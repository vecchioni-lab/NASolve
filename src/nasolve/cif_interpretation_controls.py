"""Bounded reader-control roles shared by captured evidence and preparation.

Controls never enter the geometric restraint compiler. The native PHIL parser
remains the consumer; this module only admits the four reviewed False settings.
"""
from .cif_dictionary_sites import _need, _read
from .cif_na_policy import _parse

POLICY_ID = 'cif-captured-reader-control-handoff-v1'
DICTIONARY_PARENT_POLICY_ID = 'cif-typed-native-dictionary-parent-v1'
NCS = 'pdb_interpretation.use_ncs_to_build_restraints'

CONTROLS = frozenset(('pdb_interpretation.sort_atoms',
    'pdb_interpretation.restraints_library.cdl',
    'pdb_interpretation.restraints_library.cdl_nucleotides.enable',
    'pdb_interpretation.use_ncs_to_build_restraints'))


def control_definitions(data, seen):
    # Reuse the maintained bounded parser; the wrapper permits flat PHIL.
    nodes, _ = _parse('capture_controls {\n'+data.decode('utf-8')+'\n}\n')
    containers = {''} | {
        '.'.join(key.split('.')[:i]) for key in CONTROLS
        for i in range(1, len(key.split('.')))}
    values = {}; mappings = []
    for node in nodes:
        path = node['path']
        _need(path == 'capture_controls' or path.startswith('capture_controls.'),
              'Control escaped its parser scope')
        source_path = path.removeprefix('capture_controls').removeprefix('.')
        normalized = '' if source_path == 'refinement' else source_path.removeprefix('refinement.')
        _need(normalized in containers, 'Unsupported interpretation control scope')
        for key, value in node['fields'].items():
            source = '.'.join(part for part in (source_path, key) if part)
            target = source.removeprefix('refinement.')
            _need(target in CONTROLS and value == 'False',
                  'Unsupported interpretation control or value')
            _need(target not in seen, 'Repeated interpretation control')
            seen.add(target); values[target] = False
            mappings.append(dict(source=source, interpreter=target, value_tokens=['False']))
    _need(values, 'Empty interpretation control input')
    return values, mappings


def control_fields(paths, policy, *, prefix='inputs/'):
    """Freeze an explicit nonempty ordered role, or preserve exact legacy absence."""
    _need(isinstance(paths, (list, tuple)), 'Require ordered interpretation controls')
    if policy is None:
        _need(not paths, 'Interpretation controls require an explicit reader-control policy')
        return {}
    _need(policy == POLICY_ID and paths, 'Unknown or empty reader-control policy')
    seen = set()
    for path in paths:
        control_definitions(_read(path), seen)
    return {'interpretation_controls': dict(policy_id=POLICY_ID,
        phils=[prefix+f'reader_controls/{i:03}.phil' for i in range(len(paths))])}


def control_inputs(root, controls, *, prefix='inputs/'):
    """Reopen the frozen role with its exact layout and bounded definitions."""
    if 'interpretation_controls' not in controls:
        return [], {}
    role = controls['interpretation_controls']
    _need(isinstance(role, dict) and set(role) == {'policy_id', 'phils'}
          and role['policy_id'] == POLICY_ID, 'Invalid interpretation control role')
    names = role['phils']
    _need(isinstance(names, list) and names
          and names == [prefix+f'reader_controls/{i:03}.phil' for i in range(len(names))],
          'Interpretation control layout or order differs')
    seen = set(); values = {}; paths = [root/name for name in names]
    for path in paths:
        parsed, _ = control_definitions(_read(path), seen)
        values.update(parsed)
    return paths, values


def control_kwargs(root, controls, *, prefix='inputs/'):
    paths, _ = control_inputs(root, controls, prefix=prefix)
    return {} if not paths else dict(interpretation_control_phils=paths, reader_control_policy=POLICY_ID)


def reject_shadow_controls(phils):
    """In the explicit role mode no other PHIL may redeclare these settings."""
    for path in phils:
        nodes, _ = _parse('handoff {\n'+_read(path).decode('utf-8')+'\n}\n')
        for node in nodes:
            scope = node['path'].removeprefix('handoff').removeprefix('.')
            for key in node['fields']:
                target = '.'.join(p for p in (scope, key) if p).removeprefix('refinement.')
                _need(target not in CONTROLS, 'Conflicting interpretation control outside its declared role')
