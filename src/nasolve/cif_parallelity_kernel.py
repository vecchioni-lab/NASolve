"""Explicit callable for complete native parallelity force accumulation.

This module never installs a hook. A caller must own and qualify the native
process, bind the exact native implementation, and restore any temporary binding.
No ordinary refinement option or automatic compatibility policy is implied.
"""
import math
from types import SimpleNamespace

from .cif_parallelity_correction import correct_parallelity_gradient

POLICY_ID = 'native-parallelity-kernel-adapter-v1'


def parallelity_parameters(proxies, *, site_count):
    """Copy every consumed parameter for the supported Cartesian interface.

    Preserve ordered memberships, repeated restraints and shared atoms. Missing
    fields are unsupported, not assumed native defaults. The returned plain rows
    may be recorded with a caller's exact atom ordering and source identity; they
    do not themselves qualify a native version or approve chemical targets.
    """
    if type(site_count) is not int or site_count < 0:
        raise ValueError('Require a nonnegative native site count')
    rows = []
    try:
        for proxy in proxies:
            row = {key: list(getattr(proxy, key)) for key in ('i_seqs', 'j_seqs')}
            for indices in (row['i_seqs'], row['j_seqs']):
                if (len(indices) < 3
                        or any(type(i) is not int or not 0 <= i < site_count for i in indices)
                        or len(set(indices)) != len(indices)):
                    raise ValueError('Require unambiguous plane indices')
            for key in ('weight', 'target_angle_deg', 'slack', 'limit'):
                value = getattr(proxy, key)
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError('Require finite native plane parameters')
                row[key] = value
            # These bounds are the native proxy constructor contract, not new
            # scientific acceptance thresholds or target retuning.
            if row['weight'] <= 0 or not 0 <= row['slack'] <= 90 or row['limit'] < 1:
                raise ValueError('Invalid native plane parameter bounds')
            row['top_out'], row['origin_id'] = proxy.top_out, proxy.origin_id
            if (type(row['top_out']) is not bool or type(row['origin_id']) is not int
                    or not 0 <= row['origin_id'] <= 255):
                raise ValueError('Invalid native plane mode or origin')
            sym_ops = proxy.sym_ops
            row['sym_ops'] = None if sym_ops is None else list(sym_ops)
            if row['sym_ops']:
                raise ValueError('Symmetry-bearing plane correction is unsupported')
            rows.append(row)
    except (AttributeError, TypeError) as exc:
        raise ValueError('Incomplete native parallelity interface') from exc
    return rows


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
        # Validate indices and the complete native parameter interface before
        # entering compiled code, which cannot safely inspect malformed indices.
        parallelity_parameters(proxies, site_count=count)
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
