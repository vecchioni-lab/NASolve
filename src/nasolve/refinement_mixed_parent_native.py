"""Native source/policy checks for explicit ordinary mixed-parent admission."""
import math
from types import SimpleNamespace

from .refinement_command_binding import _check_policy
from .refinement_parameter_native import bind_scope, capture_atoms


def check_policy(policy, source, scope, paths, selectors):
    """Validate declared child selectors and all fixed scattering before hooks."""
    from iotbx import pdb
    plan = SimpleNamespace(observation_labels=selectors['data_labels'],
                           free_r_label=selectors['free_label'], phase_labels=selectors['phase_labels'])
    extracted = _check_policy(policy, plan, str(paths['observations']), str(paths['phases']),
                              expected_target='mlhl')
    p = extracted.refinement
    if (p.main.target != 'mlhl' or p.main.use_experimental_phases is not True
            or type(p.main.nproc) is not int or p.main.nproc != 1):
        raise ValueError('Mixed child requires explicit MLHL, experimental phases and one process')
    data = extracted.data_manager.fmodel.xray_data
    free = data.r_free_flags
    if (free.generate or free.ignore_r_free_flags or not free.required
            or type(free.test_flag_value) is not int or free.test_flag_value != selectors['test_flag_value']):
        raise ValueError('Child policy differs from original Free-R test assignment')
    if (data.force_anomalous_flag_to_be_equal_to is not False or data.outliers_rejection
            or data.high_resolution is not None or data.low_resolution is not None
            or data.sigma_fobs_rejection_criterion is not None or data.sigma_iobs_rejection_criterion is not None):
        raise ValueError('Child policy must retain the complete explicitly merged observations')
    if p.group_anomalous.find_automatically:
        raise ValueError('Mixed child requires declared fixed scattering groups')
    inp = pdb.input(source_info='ordinary mixed parent', lines=source.decode('ascii').splitlines())
    hierarchy = inp.construct_hierarchy(sort_atoms=False)
    xs = inp.xray_structure_simple()
    cache = hierarchy.atom_selection_cache()
    seen = set()
    for group in p.refine.anomalous_scatterers.group:
        if (group.selection is None or group.refine or
                any(type(v) not in (float, int) or not math.isfinite(v)
                    for v in (group.f_prime, group.f_double_prime)) or group.f_double_prime != 0):
            raise ValueError('MLHL geometry requires explicit fixed f-prime and zero f-double-prime groups')
        indices = list(cache.iselection(group.selection))
        if not indices or seen.intersection(indices):
            raise ValueError('Fixed scattering groups must be nonempty and disjoint')
        seen.update(indices)
        for index in indices:
            xs.scatterers()[index].fp = group.f_prime
            xs.scatterers()[index].fdp = group.f_double_prime
    if seen != set(range(len(xs.scatterers()))):
        raise ValueError('Fixed scattering groups must cover every source atom')
    record = scope.record()
    expected = [{k:r[k] for k in ('label','scattering_type','f_prime','f_double_prime')}
                for r in record['initial_atoms']]
    model = SimpleNamespace(get_hierarchy=lambda:hierarchy, get_xray_structure=lambda:xs)
    bind_scope(source, model, expected_scattering=expected, xyz_indices=record['xyz_indices'],
               adp_groups=record['adp_groups'])
    scope.state(capture_atoms(xs), initial=True)
