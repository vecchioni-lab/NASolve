"""Small deterministic least-squares solver for explicit recipe geometry only.

This objective contains no diffraction, covalent, nonbonded or inherited PHIL
terms. It must not be presented as native whole-model geometry minimization.
"""
import math

from .binding import Atom, AtomKey
from .preview import _measurement
from .recipe import RecipeError


STEP = 1e-5  # Cartesian finite-difference step, angstrom.


def _rank(matrix):
    """Pivoted column orthogonalization; a local sensitivity diagnostic only."""
    columns = [list(c) for c in zip(*matrix)]
    scale = max((math.hypot(*c) for c in columns), default=0.)
    rank = 0
    while columns:
        pivot = max(range(len(columns)), key=lambda i: math.hypot(*columns[i]))
        vector = columns.pop(pivot)
        norm = math.hypot(*vector)
        if norm <= max(1e-8, scale * 1e-6):
            break
        unit = [v/norm for v in vector]
        columns = [[v-math.fsum(a*b for a, b in zip(c, unit))*u for v, u in zip(c, unit)] for c in columns]
        rank += 1
    return rank


def _solve(matrix, vector):
    """Partial-pivot elimination for the damped positive-definite normal system."""
    rows = [list(row) + [v] for row, v in zip(matrix, vector)]
    n = len(rows)
    for i in range(n):
        pivot = max(range(i, n), key=lambda j: abs(rows[j][i]))
        rows[i], rows[pivot] = rows[pivot], rows[i]
        if rows[i][i] == 0:
            raise RecipeError('Singular damped geometry system')
        for j in range(i+1, n):
            factor = rows[j][i]/rows[i][i]
            for k in range(i+1, n+1):
                rows[j][k] -= factor*rows[i][k]
    answer = [0.]*n
    for i in reversed(range(n)):
        answer[i] = (rows[i][n]-math.fsum(rows[i][j]*answer[j] for j in range(i+1, n)))/rows[i][i]
    if not all(math.isfinite(x) for x in answer):
        raise RecipeError('Nonfinite geometry step')
    return answer


class Problem:
    def __init__(self, preview, mobile):
        self.atoms = [Atom(key=AtomKey(**a['key']), element=a['element'], xyz=a['xyz']) for a in preview['inputs']['model']['atoms']]
        lookup = {a.key: i for i, a in enumerate(self.atoms)}
        nodes = {r['node_id']: lookup[AtomKey(**r['atom']['key'])] for r in preview['nodes']}
        self.mobile = [nodes[n] for n in mobile]
        self.rows = [r for r in preview['restraints'] if r['enabled']]
        self.indices = [[nodes[n] for n in r['node_ids']] for r in self.rows]
        self.start = [v for i in self.mobile for v in self.atoms[i].xyz]

    def points(self, x):
        points = [list(a.xyz) for a in self.atoms]
        for offset, index in enumerate(self.mobile):
            points[index] = x[3*offset:3*offset+3]
        return points

    def residuals(self, x):
        points = self.points(x)
        values = []
        for row, indices in zip(self.rows, self.indices):
            atoms = [Atom(key=self.atoms[i].key, element=self.atoms[i].element, xyz=points[i]) for i in indices]
            measured, issues = _measurement(row['kind'], atoms)
            if issues or (row['kind'] == 'distance' and measured == 0):
                raise RecipeError('Undefined recipe geometry: ' + row['restraint_id'])
            residual = (measured-row['target'])/row['sigma']
            if not math.isfinite(residual) or abs(residual) > 1e100:
                raise RecipeError('Recipe residual exceeds supported numerical range')
            values.append(residual)
        return values

    def jacobian(self, x):
        columns = []
        for i in range(len(x)):
            plus, minus = list(x), list(x)
            plus[i] += STEP
            minus[i] -= STEP
            columns.append([(a-b)/(2*STEP) for a, b in zip(self.residuals(plus), self.residuals(minus))])
        return [list(row) for row in zip(*columns)]

    def summary(self, x):
        residuals = self.residuals(x)
        rank = _rank(self.jacobian(x))
        return {'objective': math.fsum(r*r for r in residuals),
                'maximum_absolute_z': max(map(abs, residuals)),
                'local_jacobian_rank': rank,
                'local_unconstrained_dimensions': len(x)-rank,
                'restraints': [dict(restraint_id=row['restraint_id'], kind=row['kind'], unit=row['unit'],
                                    target=row['target'], sigma=row['sigma'],
                                    measured=row['target']+r*row['sigma'], z=r)
                               for row, r in zip(self.rows, residuals)]}

    def optimize(self, max_iterations, max_shift):
        x = list(self.start)
        damping = 1e-3
        history = []
        stop = 'ITERATION_LIMIT'
        for iteration in range(max_iterations):
            residuals, jacobian = self.residuals(x), self.jacobian(x)
            objective = math.fsum(r*r for r in residuals)
            columns = list(zip(*jacobian))
            gradient = [math.fsum(a*b for a, b in zip(c, residuals)) for c in columns]
            if max(map(abs, gradient)) <= 1e-7:
                stop = 'SMALL_LOCAL_GRADIENT'
                break
            matrix = [[math.fsum(a*b for a, b in zip(c, d)) for d in columns] for c in columns]
            for i in range(len(x)):
                matrix[i][i] += damping*max(matrix[i][i], 1.)
            step = _solve(matrix, [-g for g in gradient])
            largest = max(math.hypot(*step[i:i+3]) for i in range(0, len(x), 3))
            scale = min(1., .25/largest) if largest else 1.
            candidate = [a+scale*b for a, b in zip(x, step)]
            for i in range(0, len(x), 3):
                delta = [candidate[i+j]-self.start[i+j] for j in range(3)]
                length = math.hypot(*delta)
                if length > max_shift:
                    candidate[i:i+3] = [self.start[i+j]+max_shift/length*delta[j] for j in range(3)]
            # An undefined trial step is rejected without changing the current x.
            try:
                candidate_objective = math.fsum(r*r for r in self.residuals(candidate))
            except RecipeError:
                candidate_objective = None
            accepted = candidate_objective is not None and candidate_objective < objective
            history.append({'iteration': iteration+1, 'objective_before': objective,
                            'candidate_objective': candidate_objective, 'accepted': accepted, 'damping': damping})
            if accepted:
                x = candidate
                damping = max(1e-12, damping/3.)
            else:
                damping *= 10.
                if damping > 1e12:
                    stop = 'NO_DECREASING_BOUNDED_STEP'
                    break
        return x, {'stopping': stop, 'iterations': len(history), 'history': history,
                   'finite_difference_step_A': STEP, 'maximum_step_A': .25,
                   'method': 'damped-finite-difference-least-squares-v1'}
