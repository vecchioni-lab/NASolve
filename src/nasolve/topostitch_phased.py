"""Source-bound experimental phases and fixed scattering for local refinement.

This observer supplies no force, optimizer, phase estimate or anomalous fit.
Native imports are delayed until a requested phased execution is admitted.
"""
from __future__ import annotations

from hashlib import sha256
import math
import importlib
from pathlib import Path
import re

from .topostitch_inspect import _keys
from .topostitch_recipe import model_atom_rows, recipe_digest


def validate_spec(spec):
    _keys(spec, {'target', 'phase_labels', 'fixed_scattering_groups'})
    if spec['target'] != 'mlhl':
        raise ValueError('Phased local refinement requires explicit MLHL')
    labels = spec['phase_labels']
    if (not isinstance(labels, list) or len(labels) != 4 or
            any(not isinstance(s, str) or not re.fullmatch(r'[A-Za-z0-9_]+', s) for s in labels)
            or len(set(labels)) != 4):
        raise ValueError('Require four distinct explicit HL labels')
    groups = spec['fixed_scattering_groups']
    if not isinstance(groups, list) or not 1 <= len(groups) <= 1000:
        raise ValueError('Require explicit fixed scattering groups')
    for group in groups:
        _keys(group, {'selection', 'f_prime', 'f_double_prime'})
        selection = group['selection']
        if (not isinstance(selection, str) or not selection.strip() or len(selection) > 4096
                or any(ord(c) < 32 or ord(c) > 126 for c in selection)):
            raise ValueError('Require a single-line native atom selection')
        _fixed_values(group)


def _fixed_values(row):
    if any(type(row[k]) not in (int, float) or not math.isfinite(row[k])
           for k in ('f_prime', 'f_double_prime')) or row['f_double_prime'] != 0:
        raise ValueError('MLHL geometry requires finite fixed f-prime and zero f-double-prime')


def validate_scattering(packet, source):
    _keys(packet, {'schema_version', 'kind', 'model_sha256', 'atoms'})
    if (type(packet['schema_version']) is not int or packet['schema_version'] != 1
            or packet['kind'] != 'topostitch-fixed-scattering'
            or packet['model_sha256'] != sha256(source).hexdigest()):
        raise ValueError('Fixed scattering requires its exact source model')
    rows = model_atom_rows(source)
    if not isinstance(packet['atoms'], list) or len(packet['atoms']) != len(rows):
        raise ValueError('Require complete source-ordered scattering identities')
    for expected, atom in zip(rows, packet['atoms']):
        _keys(atom, {'identity', 'f_prime', 'f_double_prime'})
        if atom['identity'] != expected:
            raise ValueError('Fixed scattering atom identity differs from source')
        _fixed_values(atom)


def policy_text(spec, phase_path):
    """Return only the additional explicit phase/fixed-scattering policy."""
    # Phenix 2.2 formats next-run .def selectors before comparing them literally
    # to live groups; harmless quoted whitespace can abort an otherwise finished
    # writer. Formatting also rounds fixed f-prime. Replay uses our frozen inputs
    # and request, not optional next-run defaults; retain all final-state guards.
    validate_spec(spec)
    quote = lambda s: '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    lines = ['data_manager { miller_array {', 'file = ' + quote(phase_path),
             'labels { name = ' + quote(','.join(spec['phase_labels'])) + ' }', '}}',
             'refinement {', 'output { write_def_file = False }', 'main { target = mlhl', 'use_experimental_phases = True', '}',
             'group_anomalous { find_automatically = False }',
             'refine { anomalous_scatterers {']
    for group in spec['fixed_scattering_groups']:
        lines += ['group {', 'selection = ' + quote(group['selection']),
                  'f_prime = ' + repr(group['f_prime']), 'f_double_prime = 0',
                  'refine = None', '}']
    return '\n'.join(lines + ['}}}', ''])


def _indexed(indices, values, role):
    if len(indices) != len(values) or not indices:
        raise ValueError('Empty or mismatched ' + role)
    result = {}
    for h, value in zip(indices, values):
        if len(h) != 3 or any(type(v) is not int for v in h) or tuple(h) in result:
            raise ValueError('Duplicate or invalid indices in ' + role)
        result[tuple(h)] = value
    return result


def compare_native_state(reference, observed):
    """Compare effective target/indexed HL/fixed scattering, not PHIL intent."""
    if observed['target'] != 'mlhl' or observed['anomalous'] is not False:
        raise ValueError('Native target is not non-anomalous MLHL')
    if observed['use_experimental_phases'] is not True:
        raise ValueError('Native experimental phases are disabled')
    if observed['strategy'] != ['individual_sites'] or observed['refining_scattering']:
        raise ValueError('Native strategy permits scattering or non-coordinate refinement')
    expected_hl = _indexed(*reference['hl'], 'source phases')
    actual_hl = _indexed(*observed['hl'], 'native phases')
    if actual_hl != expected_hl or any(len(v) != 4 or any(not math.isfinite(x) for x in v)
                                      for v in actual_hl.values()):
        raise ValueError('Native indexed experimental phases differ from source')
    expected_flags = _indexed(*reference['flags'], 'source Free-R flags')
    actual_flags = _indexed(*observed['flags'], 'native Free-R flags')
    if (actual_flags != expected_flags or set(actual_hl) != set(actual_flags)
            or any(type(v) is not bool for v in actual_flags.values())
            or not any(actual_flags.values()) or all(actual_flags.values())):
        raise ValueError('Native original HKL/Free-R assignment differs')
    if observed['scattering'] != reference['scattering']:
        raise ValueError('Native atom-keyed fixed scattering differs from source')
    return dict(target='mlhl', source_hl_exact=True, source_flags_exact=True,
                fixed_scattering_exact=True, phase_count=len(actual_hl),
                atom_count=len(reference['scattering']),
                source_contract_sha256=recipe_digest(reference))


class NativePhasedGuard:
    """Read input arrays independently and inspect the initialized native driver.

    Source amplitudes must be positive, unique merged amplitudes with sigmas.
    Bijvoet averaging is explicit; no other filtering or phase substitution is
    permitted. Full native states are returned to the existing job recorder.
    """
    def __init__(self, spec, files, controls, scattering, source):
        from iotbx import reflection_file_reader
        validate_spec(spec); validate_scattering(scattering, source)
        self.spec = spec
        self.scattering = scattering
        self.source = source
        names = ('iotbx.reflection_file_reader', 'mmtbx.f_model.f_model',
                 'mmtbx.refinement.targets', 'cctbx.xray.target_functors')
        self._native_sources = {name: Path(importlib.import_module(name).__file__).resolve() for name in names}
        self._native_hashes = {name: sha256(path.read_bytes()).hexdigest() for name,path in self._native_sources.items()}

        def array(path, labels):
            matches = [a for a in reflection_file_reader.any_reflection_file(str(path)).as_miller_arrays()
                       if a.info().labels == labels]
            if len(matches) != 1:
                raise ValueError('Require exactly the requested native reflection labels')
            a = matches[0].map_to_asu()
            if not a.is_unique_set_under_symmetry():
                raise ValueError('Source reflections must be unique under symmetry')
            return a

        fo = array(files['data'], controls['data_labels'].split(','))
        flags = array(files['data'], [controls['free_label']])
        hl = array(files['phases'], spec['phase_labels'])
        if not fo.is_xray_amplitude_array() or fo.sigmas() is None:
            raise ValueError('Phased local scope requires measured amplitudes with sigmas')
        if fo.anomalous_flag():
            fo = fo.average_bijvoet_mates().map_to_asu()
        if flags.anomalous_flag() or hl.anomalous_flag() or not hl.is_hendrickson_lattman_array():
            raise ValueError('Require non-anomalous source flags and HL quartet')
        for a in (flags, hl):
            if (a.space_group() != fo.space_group() or
                    not a.unit_cell().is_similar_to(fo.unit_cell(),
                        relative_length_tolerance=1e-10, absolute_angle_tolerance=1e-10)):
                raise ValueError('Source diffraction arrays have different crystals')
        indices = list(map(list, fo.indices()))
        flag_lookup = _indexed(list(map(list, flags.indices())), list(flags.data()), 'source flags')
        hl_lookup = _indexed(list(map(list, hl.indices())), [list(v) for v in hl.data()], 'source HL')
        if set(map(tuple, indices)) != set(hl_lookup) or any(tuple(h) not in flag_lookup for h in indices):
            raise ValueError('Source phases/flags do not cover the complete observation set')
        if any(type(v) is not int for v in flag_lookup.values()):
            raise ValueError('Require integer source Free-R flags')
        flag_values = [flag_lookup[tuple(h)] == controls['test_flag_value'] for h in indices]
        self.observations = [[h, float(f), float(s), b] for h,f,s,b in
                             zip(indices, fo.data(), fo.sigmas(), flag_values)]
        if any(not math.isfinite(v) or v <= 0 for r in self.observations for v in r[1:3]):
            raise ValueError('Source amplitudes/sigmas require explicit positive-data qualification')
        self.crystal = fo.crystal_symmetry()
        self.reference = dict(hl=[indices, [hl_lookup[tuple(h)] for h in indices]],
            flags=[indices, flag_values], scattering=scattering['atoms'])

    def observe(self, model, fm, params):
        from .topostitch_native_recipe import native_atom_identities
        from .topostitch_phosphate import _verify_observations
        if {name: sha256(path.read_bytes()).hexdigest() for name,path in self._native_sources.items()} != self._native_hashes:
            raise ValueError('Native phased reader or target source changed')
        atoms = list(model.get_hierarchy().atoms())
        identities = native_atom_identities(model.get_hierarchy())
        xs = model.get_xray_structure()
        if identities != model_atom_rows(self.source):
            raise ValueError('Native phased atom ordering differs from the bound source')
        # Model and diffraction managers must describe the same scattering state.
        for other in (xs, fm.xray_structure):
            if other.space_group() != self.crystal.space_group():
                raise ValueError('Native phased space group differs')
            if any(abs(a-b) > t for a,b,t in zip(other.unit_cell().parameters(),
                    self.crystal.unit_cell().parameters(), [.00051]*3 + [.0051]*3)):
                raise ValueError('Native phased cell differs beyond source PDB precision')
        expected = self.reference['scattering']
        hits = [0]*len(atoms)
        groups = list(model.get_anomalous_scatterer_groups())
        if len(groups) != len(self.spec['fixed_scattering_groups']):
            raise ValueError('Native fixed scattering group inventory differs')
        for group, live in zip(self.spec['fixed_scattering_groups'], groups):
            mask = list(model.selection(group['selection']))
            if len(mask) != len(atoms) or not any(mask):
                raise ValueError('Empty or invalid fixed scattering selection')
            if (live.selection_string != group['selection'] or
                    list(live.iselection) != [i for i, yes in enumerate(mask) if yes] or
                    live.f_prime != group['f_prime'] or live.f_double_prime != 0 or
                    live.refine_f_prime or live.refine_f_double_prime):
                raise ValueError('Native fixed scattering group policy differs')
            for i, selected in enumerate(mask):
                if selected:
                    hits[i] += 1
                    if any(expected[i][k] != group[k] for k in ('f_prime', 'f_double_prime')):
                        raise ValueError('Scattering selection differs from atom-keyed expectation')
        if any(n != 1 for n in hits):
            raise ValueError('Fixed scattering selections overlap or leave atoms uncovered')
        states = []; species = []
        for structure in (xs, fm.xray_structure):
            scatterers = list(structure.scatterers())
            if len(scatterers) != len(atoms) or any(a.id_str() != s.label for a,s in zip(atoms,scatterers)):
                raise ValueError('Native scattering identity/order differs')
            species.append([s.scattering_type for s in scatterers])
            states.append([dict(identity=k, f_prime=float(s.fp), f_double_prime=float(s.fdp))
                           for k,s in zip(identities, scatterers)])
        if states[0] != states[1] or species[0] != species[1]:
            raise ValueError('Model and diffraction scattering state differ')
        hl = fm.hl_coeffs()
        if hl is None:
            raise ValueError('Native experimental phases are missing')
        fo, flags = fm.f_obs(), fm.r_free_flags()
        if list(fo.indices()) != list(flags.indices()) or list(hl.indices()) != list(fo.indices()):
            raise ValueError('Native observation/flag/phase ordering differs')
        snapshot = dict(target=fm.target_name, anomalous=fo.anomalous_flag(),
            use_experimental_phases=params.main.use_experimental_phases,
            strategy=list(params.refine.strategy),
            refining_scattering=any(g.refine_f_prime or g.refine_f_double_prime
                                   for g in model.get_anomalous_scatterer_groups()),
            hl=[list(map(list, hl.indices())), [list(v) for v in hl.data()]],
            flags=[list(map(list, flags.indices())), list(flags.data())], scattering=states[0],
            scattering_types=species[0], native_sources=self._native_hashes)
        audit = compare_native_state(self.reference, snapshot)
        native = [[list(h), float(f), float(s), bool(b)] for h,f,s,b in
                  zip(fo.indices(), fo.data(), fo.sigmas(), flags.data())]
        by_hkl = {tuple(r[0]): r for r in native}
        ordered = [by_hkl[tuple(r[0])] for r in self.observations]
        audit['source_observations'] = _verify_observations(self.observations, ordered)
        return snapshot, audit

    def observe_target(self, minimizer, params):
        """Verify the actual MLHL target object used by a coordinate evaluation."""
        fm = minimizer.fmodels.fmodel_xray()
        functor = minimizer.fmodels.target_functor_xray
        core = functor.core
        if (not minimizer.refine_xyz or minimizer.refine_adp or functor.manager is not fm
                or getattr(core, 'spacialization', None) != 'hl'
                or getattr(core, 'experimental_phases', None) is None):
            raise ValueError('Coordinate optimizer does not hold the admitted MLHL target')
        phases = core.experimental_phases
        if _indexed(list(map(list, phases.indices())), [list(v) for v in phases.data()], 'target phases') != _indexed(*self.reference['hl'], 'source phases'):
            raise ValueError('Actual coordinate target uses different experimental phases')
        flags = core.r_free_flags
        if _indexed(list(map(list, flags.indices())), list(flags.data()), 'target flags') != _indexed(*self.reference['flags'], 'source flags'):
            raise ValueError('Actual coordinate target uses different Free-R assignments')
        fo = core.f_obs
        if list(fo.indices()) != list(phases.indices()) or list(fo.indices()) != list(flags.indices()):
            raise ValueError('Actual coordinate target arrays are not index-aligned')
        from .topostitch_phosphate import _verify_observations
        rows = {tuple(h): [list(h), float(f), float(s), bool(b)] for h,f,s,b in
                zip(fo.indices(), fo.data(), fo.sigmas(), flags.data())}
        if set(rows) != {tuple(r[0]) for r in self.observations}:
            raise ValueError('Actual coordinate target observation indices differ')
        _verify_observations(self.observations, [rows[tuple(r[0])] for r in self.observations])
        return self.observe(minimizer.model, fm, params)
