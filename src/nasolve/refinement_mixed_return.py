"""Post-exit observation of an existing mixed guard's exact returned driver.

No replay, file export, process-closure proof or checkpoint adoption. The numbered
owner separately binds synchronized written output and its frozen command.
"""
from copy import deepcopy
import os

from .refinement_parameter_native import observe_model
from .refinement_parameter_scope import scope_digest
from .refinement_diffraction_observation import observe_diffraction

POLICY_ID = 'ordinary-mixed-return-observation-v1'


def observe_return(parent, driver, *, guard):
    """Verify the same completed state after callbacks restore; do not alter it.

    Permitted XYZ/B motion during refinement is not permission to change the
    returned state after finish. Compare its full-precision digest exactly, then
    reuse source/witness/target checks and revalidate ordinary parent ancestry.
    This observation is call-local evidence for the existing output owner.
    """
    from .refinement_mixed_parent import _ParentGuard, _need
    _need(isinstance(guard, _ParentGuard) and guard._parent is parent,
          'Return requires this exact parent-bound guard')
    record = guard.summary()
    _need(record['status'] == 'OBSERVED' and record['bindings_restored'] is True
          and guard._finished and guard._pid == os.getpid(),
          'Return requires completed guard exit with restored callbacks in this process')
    _need(driver is guard._driver, 'Return requires the exact observed driver')
    _need(all(getattr(cls, name) is guard._originals[role]
              for role, (cls, name) in guard._hooks.items()),
          'Native callback changed after guard exit')
    guard._verify()
    parent._recheck()
    fm = driver.fmodels.fmodel_xray()
    _need(driver.fmodels.fmodel_neutron() is None, 'Unexpected returned neutron model')
    _need(type(driver.params.main.nproc) is int and driver.params.main.nproc == 1,
          'Returned process policy changed')
    current = observe_model(guard.scope, driver.model, fm, driver.params)
    _need(current == record['final'], 'Returned atomic state differs from the completed guard state')
    _need(driver.iparams.refinement.dry_run is record['dry_run'], 'Returned execution mode changed')
    _need(record['dry_run'] or driver.macro_cycle == record['macro_cycles'] == driver.params.main.number_of_macro_cycles,
          'Returned macrocycle count changed')
    diffraction = observe_diffraction(guard.diffraction, fm,
                                     cell_roundoff_ulps=guard._cell_roundoff_ulps)
    # This reuses both the original guard target check (including a normalization
    # witness when selected) and the parent's independently read source crystal.
    guard._target(fm, fm.target_functor(alpha_beta=fm.alpha_beta()))
    parent._recheck()
    guard._verify()
    _need(guard.summary() == record, 'Post-exit observation changed guard evidence')
    result = dict(schema_version=1, policy_id=POLICY_ID, status='OBSERVED_NOT_ADOPTED',
        checkpoint_id=parent._receipt['checkpoint_id'], parent_request=parent._receipt['request'],
        parent_binding_sha256=scope_digest(parent.receipt()), guard_sha256=scope_digest(record),
        sources=parent._receipt['sources'], derived_policy_sha256=parent._receipt['composition']['result_sha256'],
        state=current, diffraction=diffraction, dry_run=record['dry_run'], macro_cycles=record['macro_cycles'],
        callbacks_restored=True, exact_returned_driver=True, parent_sources_unchanged=True,
        written_output='SEPARATE_OWNER_REQUIRED', process_closure='SEPARATE_OWNER_REQUIRED',
        scientific_approval='NOT_RUN', checkpoint_adoption=False)
    return deepcopy(result)
