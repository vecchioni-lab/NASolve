"""Explicit XYZ/group-B parameter protections, independent of a native executor.

The caller authenticates source/checkpoint/phase ancestry. This checker observes
an initialized all-isotropic state; it supplies no forces, callbacks, optimizer,
acceptance decision or automatic selection. Old refinement protocols are unchanged.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
import re

POLICY_ID = 'explicit-xyz-group-b-scope-v1'
_FIELDS = {'label', 'scattering_type', 'xyz', 'B', 'Q', 'f_prime', 'f_double_prime'}
_TOLERANCES = {'xyz': 1e-7, 'B': 1e-7, 'Q': 1e-12,
               'f_prime': 1e-12, 'f_double_prime': 1e-12}
_MODES = ('individual_sites', 'torsion_angles', 'rigid_body', 'individual_adp',
          'group_adp', 'tls', 'occupancies', 'group_anomalous')
_GRADIENTS = ('site', 'u_iso', 'u_aniso', 'occupancy', 'fp', 'fdp')


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def scope_digest(value):
    return sha256(_json(value).encode()).hexdigest()


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _atoms(rows):
    _need(isinstance(rows, list) and bool(rows), 'Require a complete nonempty atomic state')
    labels = set()
    for row in rows:
        _need(isinstance(row, dict) and set(row) == _FIELDS, 'Unexpected atomic state fields')
        for key in ('label', 'scattering_type'):
            _need(isinstance(row[key], str) and bool(row[key].strip()), 'Require explicit atom identity/type')
        _need(row['label'] not in labels, 'Duplicate atomic identity')
        labels.add(row['label'])
        _need(isinstance(row['xyz'], list) and len(row['xyz']) == 3
              and all(_number(v) for v in row['xyz']), 'Require finite Cartesian XYZ')
        _need(all(_number(row[k]) for k in ('B', 'Q', 'f_prime', 'f_double_prime')),
              'Require finite atomic B/Q/scattering values')
        _need(row['B'] >= 0 and 0 <= row['Q'] <= 1, 'Invalid isotropic B or occupancy')


def _indices(values, count, role, *, empty=False):
    _need(isinstance(values, list) and (empty or bool(values))
          and all(type(i) is int and 0 <= i < count for i in values)
          and values == sorted(set(values)), 'Require ordered unique ' + role + ' indices')


def _membership(xyz, groups, count):
    _indices(xyz, count, 'XYZ')
    _need(isinstance(groups, list) and bool(groups), 'Require explicit isotropic B groups')
    seen = set()
    for group in groups:
        _indices(group, count, 'group-B')
        _need(not seen.intersection(group), 'Overlapping isotropic B groups')
        seen.update(group)


def make_scope(*, source_model_sha256, initial_atoms, xyz_indices, adp_groups,
               real_space=False):
    """Freeze caller-authenticated initialized state and exact ordered selections.

    Atoms outside XYZ/groups are fixed in those fields. Every atom's Q, f′ and
    f″ is fixed. Groups may span arbitrary residues; there is no metal, chain,
    residue-name, atom-count or B-range heuristic. Negative fixed f″ is retained.
    The source digest identifies bytes, not checkpoint admission or availability.
    """
    _need(isinstance(source_model_sha256, str)
          and re.fullmatch(r'[0-9a-f]{64}', source_model_sha256), 'Require a source-model SHA-256')
    _need(type(real_space) is bool, 'Require an explicit real-space boolean')
    _atoms(initial_atoms)
    _membership(xyz_indices, adp_groups, len(initial_atoms))
    return deepcopy(dict(schema_version=1, policy_id=POLICY_ID,
        source_model_sha256=source_model_sha256, initial_atoms=initial_atoms,
        xyz_indices=xyz_indices, adp_groups=adp_groups, real_space=real_space))


class ParameterScope:
    """Detached immutable-in-practice observer with a caller-pinned packet digest.

    Receipts report only the observation made. Calling state() once does not
    prove continuous protection; the execution owner must observe all relevant
    stages/evaluations, actual parameter flags, export and known-stopped outcome.
    """
    def __init__(self, record, *, expected_sha256):
        _need(isinstance(record, dict) and set(record) == {
            'schema_version', 'policy_id', 'source_model_sha256', 'initial_atoms',
            'xyz_indices', 'adp_groups', 'real_space'}, 'Unexpected parameter-scope record')
        _need(type(record['schema_version']) is int and record['schema_version'] == 1
              and record['policy_id'] == POLICY_ID, 'Unsupported parameter-scope policy')
        rebuilt = make_scope(**{k: v for k, v in record.items()
                               if k not in ('schema_version', 'policy_id')})
        _need(scope_digest(rebuilt) == expected_sha256, 'Parameter-scope checksum mismatch')
        self._record = _json(rebuilt)
        self._digest = expected_sha256

    def record(self):
        return json.loads(self._record)

    def _receipt(self, observation, **details):
        return dict(policy_id=POLICY_ID, scope_sha256=self._digest,
                    observation=observation, **details)

    def state(self, atoms, *, initial=False):
        """Check a full-precision native snapshot, never a rounded output PDB."""
        _need(type(initial) is bool, 'Require an explicit initialization boolean')
        _atoms(atoms)
        packet = self.record()
        baseline = packet['initial_atoms']
        _need(len(atoms) == len(baseline), 'Atomic inventory changed')
        xyz = set(packet['xyz_indices'])
        adp = {i for group in packet['adp_groups'] for i in group}
        max_motion = max_b_change = 0.0
        for i, (old, new) in enumerate(zip(baseline, atoms)):
            _need(all(new[k] == old[k] for k in ('label', 'scattering_type')),
                  'Atomic identity/order/type changed')
            displacement = math.dist(old['xyz'], new['xyz'])
            if initial or i not in xyz:
                _need(displacement <= _TOLERANCES['xyz'], 'Protected XYZ changed: ' + old['label'])
            for key in ('B', 'Q', 'f_prime', 'f_double_prime'):
                if key != 'B' or initial or i not in adp:
                    _need(abs(new[key] - old[key]) <= _TOLERANCES[key],
                          'Protected ' + key + ' changed: ' + old['label'])
            max_motion = max(max_motion, displacement)
            max_b_change = max(max_b_change, abs(new['B'] - old['B']))
        return self._receipt('initial_state' if initial else 'atomic_state', atom_count=len(atoms),
            max_displacement_A=max_motion, max_B_change_A2=max_b_change,
            state_sha256=scope_digest(atoms))

    def compiled(self, *, strategy, modes, xyz_indices, adp_groups,
                 apply_adp_backtrace, apply_overall_adp_scale, refining_scattering):
        """Check effective compiled mode flags and exact group/coordinate membership."""
        packet = self.record()
        expected = ['individual_sites']
        if packet['real_space']:
            expected.append('individual_sites_real_space')
        expected.append('group_adp')
        _need(strategy == expected, 'Compiled strategy differs from parameter scope')
        _need(isinstance(modes, dict) and set(modes) == set(_MODES)
              and all(type(v) is bool for v in modes.values()), 'Incomplete compiled refinement flags')
        _need(modes == {k: k in ('individual_sites', 'group_adp') for k in _MODES},
              'Unexpected active parameter mode')
        _membership(xyz_indices, adp_groups, len(packet['initial_atoms']))
        _need(xyz_indices == packet['xyz_indices'] and adp_groups == packet['adp_groups'],
              'Compiled XYZ/group-B membership changed')
        _need(apply_adp_backtrace is False and apply_overall_adp_scale is False
              and refining_scattering is False, 'Protected ADP/scattering may change')
        return self._receipt('compiled_scope', xyz_atoms=len(xyz_indices), adp_groups=len(adp_groups))

    def xyz_parameters(self, *, gradient_flags, parameter_count):
        """Check flags on the actual reciprocal XYZ optimizer's scattering object."""
        packet = self.record()
        selected = set(packet['xyz_indices'])
        _need(isinstance(gradient_flags, list) and len(gradient_flags) == len(packet['initial_atoms']),
              'Incomplete optimizer gradient flags')
        for i, row in enumerate(gradient_flags):
            _need(isinstance(row, dict) and set(row) == set(_GRADIENTS)
                  and all(type(v) is bool for v in row.values()), 'Malformed optimizer gradient flags')
            _need(row == {k: k == 'site' and i in selected for k in _GRADIENTS},
                  'Actual XYZ optimizer includes an unexpected parameter')
        _need(type(parameter_count) is int and parameter_count == 3 * len(selected),
              'Actual XYZ optimizer parameter count changed')
        return self._receipt('reciprocal_xyz_parameters', parameter_count=parameter_count)

    def group_parameters(self, *, selections, refine_adp, refine_occ, parameter_count):
        """Group-B uses one shift per declared group, not one variable per atom."""
        packet = self.record()
        groups = packet['adp_groups']
        _membership(packet['xyz_indices'], selections, len(packet['initial_atoms']))
        _need(refine_adp is True and refine_occ is False, 'Unexpected group optimizer mode')
        _need(selections == groups, 'Actual group-B optimizer membership changed')
        _need(type(parameter_count) is int and parameter_count == len(groups),
              'Actual group-B parameter count changed')
        return self._receipt('group_b_parameters', parameter_count=parameter_count)
