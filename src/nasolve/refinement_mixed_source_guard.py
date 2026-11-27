"""Source-bound mixed observation usable by an ordinary or frozen native owner.

The caller authenticates parent ancestry and supplies the immutable input recheck.
This class adds source atom/crystal checks to the existing runtime lifecycle; it
does not read registries, allocate work, supply forces or adopt outputs.
"""
from hashlib import sha256

from .refinement_diffraction_observation import _same_cell
from .refinement_mixed_runtime import MixedRuntimeGuard
from .refinement_parameter_native import bind_scope


class SourceMixedGuard(MixedRuntimeGuard):
    def __init__(self, scope, diffraction, *, source, crystal, recheck, **runtime):
        if not callable(recheck):
            raise ValueError('Require the owning input recheck')
        super().__init__(scope, diffraction, **runtime)
        if type(source) is not bytes or sha256(source).hexdigest() != scope.record()['source_model_sha256']:
            raise ValueError('Mixed source differs from the declared model')
        self._source_bytes, self._source_crystal, self._source_recheck = source, crystal, recheck

    def __enter__(self):
        self._source_recheck()
        return super().__enter__()

    def _model(self, driver, *, initial=False):
        if initial:
            record = self.scope.record()
            expected = [{k:r[k] for k in ('label', 'scattering_type', 'f_prime', 'f_double_prime')}
                        for r in record['initial_atoms']]
            bind_scope(self._source_bytes, driver.model, expected_scattering=expected,
                       xyz_indices=record['xyz_indices'], adp_groups=record['adp_groups'])
        return super()._model(driver, initial=initial)

    def _target(self, fm, target):
        crystal = self._source_crystal
        for obj in (fm.xray_structure, fm.f_obs(), target.core.f_obs):
            if (obj.space_group() != crystal.space_group()
                    or not _same_cell(obj.unit_cell().parameters(), crystal.unit_cell().parameters(),
                                      self._cell_roundoff_ulps)):
                raise ValueError('Active target crystal differs from admitted source')
        super()._target(fm, target)

    def finish(self, driver, *, dry_run):
        try:
            self._source_recheck()
            return super().finish(driver, dry_run=dry_run)
        except BaseException as exc:
            self._fail(exc)
            raise
