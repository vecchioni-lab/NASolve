"""Explicit callable for complete native parallelity force accumulation.

This module never installs a hook. A caller must own and qualify the native
process, bind the exact native implementation, and restore any temporary binding.
No ordinary refinement option or automatic compatibility policy is implied.
"""
import math
from types import SimpleNamespace

from .cif_parallelity_correction import correct_parallelity_gradient

POLICY_ID = 'native-parallelity-kernel-adapter-v1'


class ParallelityKernel:
    """Preserve the native score and add checked forces to the supplied buffer.

    Only the keyword Cartesian interface is supported. Unit-cell/symmetry planes
    need another implementation. The existing both-first-planes correction owns
    proxy validation and numerical semantics; historical correction bytes stay
    unchanged. Counters are process-local observations, not execution receipts.
    """

    def __init__(self, gr, flex):
        self._flex = flex
        self._api = SimpleNamespace(**{name: getattr(gr, name) for name in (
            'parallelity', 'parallelity_proxy', 'parallelity_residual_sum')})
        if not all(callable(fn) for fn in vars(self._api).values()):
            raise ValueError('Require the explicit native parallelity interfaces')
        self._gradient_calls = self._energy_calls = self._max_proxies = 0

    def statistics(self):
        return dict(policy_id=POLICY_ID,
                    successful_calls=self._gradient_calls + self._energy_calls,
                    gradient_calls=self._gradient_calls,
                    energy_only_calls=self._energy_calls,
                    maximum_proxy_count=self._max_proxies)

    def __call__(self, *, sites_cart, proxies, gradient_array, unit_cell=None):
        if unit_cell is not None:
            raise ValueError('Unit-cell parallelity kernel is unsupported')
        count = len(sites_cart)
        points = [list(p) for p in sites_cart]
        if any(len(p) != 3 or not all(math.isfinite(x) for x in p) for p in points):
            raise ValueError('Require complete finite Cartesian sites')
        if gradient_array is not None and len(gradient_array) not in (0, count):
            raise ValueError('Incomplete caller gradient buffer')
        gradients = gradient_array is not None and len(gradient_array) != 0
        if gradients and (gradient_array is sites_cart or gradient_array.id() == sites_cart.id()):
            raise ValueError('Sites and gradients must have separate storage')
        incoming = list(gradient_array.as_double()) if gradients else []
        if not all(math.isfinite(x) for x in incoming):
            raise ValueError('Nonfinite incoming gradient')
        # Never allow a failed native call/check to partially modify forces that
        # earlier restraints already added to the caller's array.
        buffer = self._flex.vec3_double(count, (0., 0., 0.))
        target = float(self._api.parallelity_residual_sum(
            sites_cart=sites_cart, proxies=proxies, gradient_array=buffer))
        if not math.isfinite(target):
            raise ValueError('Nonfinite native parallelity target')
        if count:
            corrected = correct_parallelity_gradient(
                self._api, self._flex, proxies, points, list(buffer.as_double()),
                native_residual=target, plane_order_safe=True)['gradient']
        elif len(proxies) or target != 0.:
            raise ValueError('Nonempty parallelity on an empty model')
        else:
            corrected = []
        if gradients:
            values = [math.fsum((a, b)) for a, b in zip(incoming, corrected)]
            if len(values) != 3*count or not all(math.isfinite(x) for x in values):
                raise ValueError('Invalid accumulated parallelity gradient')
            complete = self._flex.vec3_double([values[i:i+3] for i in range(0, len(values), 3)])
            gradient_array.set_selected(self._flex.size_t(range(count)), complete)
            self._gradient_calls += 1
        else:
            self._energy_calls += 1
        self._max_proxies = max(self._max_proxies, len(proxies))
        return target
