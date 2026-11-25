"""Read-only Phenix adapter for the explicit XYZ/group-B scope checker.

No bindings are replaced and no refinement is started. The execution owner calls
these observations at initialization, stage boundaries and actual target calls.
Phases, Free-R, restraint/image forces, output synchronization and process state
remain independently owned. Observing native flags is not scientific acceptance.
"""
from hashlib import sha256
import math

from .refinement_parameter_scope import (
    ParameterScope, _GRADIENTS, _MODES, _need, _number, make_scope, scope_digest,
)


def capture_atoms(xray_structure):
    """Snapshot exact native Cartesian/isotropic state in native atom order."""
    cell = xray_structure.unit_cell()
    rows = []
    for atom in xray_structure.scatterers():
        _need(atom.flags.use_u_iso() and not atom.flags.use_u_aniso(),
              'Parameter scope requires all-isotropic native atoms')
        rows.append(dict(label=atom.label, scattering_type=atom.scattering_type,
            xyz=list(cell.orthogonalize(atom.site)), B=atom.u_iso * 8 * math.pi**2,
            Q=atom.occupancy, f_prime=atom.fp, f_double_prime=atom.fdp))
    return rows


def bind_scope(source, model, *, expected_scattering, xyz_indices, adp_groups,
               real_space=False):
    """Bind exact source PDB XYZ/B/Q and explicit caller-owned scattering values.

    This authenticates initialization against supplied bytes; the caller must
    authenticate those bytes/scattering references through the numbered input
    owner. It does not discover paths, read phase files or admit a checkpoint.
    """
    from iotbx import pdb
    _need(type(source) is bytes, 'Require exact source PDB bytes')
    source_input = pdb.input(source_info='parameter-scope source', lines=source.decode('ascii').splitlines())
    hierarchy = source_input.construct_hierarchy()
    _need(hierarchy.models_size() == 1 and model.get_hierarchy().models_size() == 1,
          'Require one explicit model')
    original = list(hierarchy.atoms())
    current = list(model.get_hierarchy().atoms())
    atoms = capture_atoms(model.get_xray_structure())
    _need(len(atoms) == len(original) == len(current) == len(expected_scattering),
          'Initialization changed source atomic inventory')
    scatterers = model.get_xray_structure().scatterers()
    for old, actual, row, scattering, native in zip(original, current, atoms, expected_scattering, scatterers):
        _need(old.id_str() == actual.id_str() == row['label'], 'Source/native identity or order changed')
        _need(old.element.strip().upper() == actual.element.strip().upper(), 'Source element changed')
        _need(native.element_symbol().strip().upper() == old.element.strip().upper(),
              'Native scattering element differs from source model')
        _need(not old.uij_is_defined(), 'Anisotropic source needs a separate policy')
        _need(math.dist(old.xyz, row['xyz']) <= 1e-7 and abs(old.b - row['B']) <= 1e-7
              and abs(old.occ - row['Q']) <= 1e-12, 'Native initialization changed source XYZ/B/Q')
        _need(isinstance(scattering, dict) and set(scattering) == {
            'label', 'scattering_type', 'f_prime', 'f_double_prime'}, 'Require complete explicit scattering references')
        _need(all(_number(scattering[k]) for k in ('f_prime', 'f_double_prime')),
              'Require finite explicit scattering references')
        _need(scattering == {k: row[k] for k in scattering}, 'Native initialized scattering differs from reference')
    record = make_scope(source_model_sha256=sha256(source).hexdigest(), initial_atoms=atoms,
                        xyz_indices=xyz_indices, adp_groups=adp_groups, real_space=real_space)
    return ParameterScope(record, expected_sha256=scope_digest(record))


def observe_model(scope, model, fmodel, params, *, initial=False):
    """Observe effective flags and both model/diffraction atomic states."""
    flags = model.refinement_flags
    groups = model.get_anomalous_scatterer_groups()
    compiled = scope.compiled(strategy=list(params.refine.strategy),
        modes={key: getattr(flags, key) for key in _MODES},
        xyz_indices=list(flags.sites_individual.iselection()),
        adp_groups=[list(group) for group in flags.adp_group],
        apply_adp_backtrace=params.bulk_solvent_and_scale.apply_back_trace,
        apply_overall_adp_scale=params.main.apply_overall_isotropic_scale_to_adp,
        refining_scattering=any(g.refine_f_prime or g.refine_f_double_prime for g in groups))
    model_xs, diffraction_xs = model.get_xray_structure(), fmodel.xray_structure
    _need(model_xs.unit_cell().parameters() == diffraction_xs.unit_cell().parameters()
          and model_xs.space_group() == diffraction_xs.space_group(), 'Model/diffraction crystal frames differ')
    atoms, diffraction = capture_atoms(model_xs), capture_atoms(diffraction_xs)
    _need([a.id_str() for a in model.get_hierarchy().atoms()] == [r['label'] for r in atoms],
          'Hierarchy/scattering atom identities differ')
    state = scope.state(atoms, initial=initial)
    scope.state(diffraction, initial=initial)
    _need(atoms == diffraction, 'Model and diffraction atomic states are unsynchronized')
    return dict(compiled=compiled, state=state)


def observe_xyz(scope, minimizer):
    """Call on the actual reciprocal minimizer; no detached proxy manager."""
    _need(minimizer.refine_xyz is True and minimizer.refine_adp is False,
          'Unexpected reciprocal optimizer mode')
    xs = minimizer.xray_structure
    state = scope.state(capture_atoms(xs))
    flags = [{key: getattr(atom.flags, 'grad_' + key)() for key in _GRADIENTS}
             for atom in xs.scatterers()]
    return dict(state=state, parameters=scope.xyz_parameters(
        gradient_flags=flags, parameter_count=xs.n_parameters()))


def observe_group(scope, minimizer):
    """Call on the actual group-B minimizer, whose vector has one shift/group."""
    parameters = scope.group_parameters(selections=[list(g) for g in minimizer.selections],
        refine_adp=minimizer.refine_adp, refine_occ=minimizer.refine_occ,
        parameter_count=len(minimizer.x))
    return dict(parameters=parameters, state=scope.state(capture_atoms(minimizer.fmodel.xray_structure)))
