"""Independent decimal reference for ordinary positive-period torsions.

The energy is expressed directly through normalized plane normals. Forward
automatic differentiation of that expression does not reuse the native angle
or Cartesian-gradient formula. This is diagnostic evidence, never an evaluator
replacement or an endpoint qualification policy.
"""
from decimal import Context, Decimal, localcontext
from functools import lru_cache
import math

POLICY_ID = 'cif-independent-decimal-periodic-torsion-v1'
PRECISIONS = (60, 90)
STEPS = ('1e-24', '1e-26')


def _need(value):
    if not value:
        raise ValueError('Unsupported or incomplete torsion precision evidence')


def _exact(value):
    _need(type(value) in (int, float) and math.isfinite(value))
    return Decimal.from_float(value) if type(value) is float else Decimal(value)


def _validate(points, proxy, digits):
    _need(type(digits) is int and 50 <= digits <= 120)
    _need(len(points) == 4 and all(len(p) == 3 for p in points))
    converted = [[_exact(v) for v in p] for p in points]
    _need(type(proxy['periodicity']) is int and 1 <= proxy['periodicity'] <= 12
          and _exact(proxy['weight']) > 0 and abs(_exact(proxy['angle_ideal'])) <= 3600
          and proxy.get('alt_angle_ideals') in (None, [])
          and proxy.get('limit', -1.) == -1. and proxy.get('top_out', False) is False
          and proxy.get('slack', 0.) == 0. and proxy.get('symmetry', 'NONE') == 'NONE')
    return converted


def _atan_small(x):
    term = total = x
    square = x*x
    for k in range(1, 1000):
        term *= -square
        updated = total + term/(2*k+1)
        if updated == total:
            return total
        total = updated
    raise ValueError('Decimal arctangent failed to converge')


@lru_cache(maxsize=16)
def _pi(digits):
    with localcontext(Context(prec=digits)):
        # Machin identity; no binary floating-point pi enters the reference.
        return 16*_atan_small(Decimal(1)/5)-4*_atan_small(Decimal(1)/239)


def _atan(x, pi):
    if x < 0:
        return -_atan(-x, pi)
    if x > 1:
        return pi/2-_atan(1/x, pi)
    factor = 1
    while x > Decimal('0.125'):
        x /= 1+(1+x*x).sqrt()
        factor *= 2
    return factor*_atan_small(x)


def _atan2(y, x, pi):
    if x > 0:
        return _atan(y/x, pi)
    if x < 0:
        return _atan(y/x, pi)+(pi if y >= 0 else -pi)
    _need(y != 0)
    return pi/2 if y > 0 else -pi/2


def _sincos(x, pi):
    x %= 2*pi
    if x > pi:
        x -= 2*pi
    if x < -pi:
        x += 2*pi
    sin_term = sine = x
    cos_term = cosine = Decimal(1)
    for k in range(1, 1000):
        sin_term *= -x*x/((2*k)*(2*k+1))
        cos_term *= -x*x/((2*k-1)*(2*k))
        new_sine, new_cosine = sine+sin_term, cosine+cos_term
        if (new_sine, new_cosine) == (sine, cosine):
            return sine, cosine
        sine, cosine = new_sine, new_cosine
    raise ValueError('Decimal trigonometric series failed to converge')


class _Dual:
    """A scalar and its Cartesian derivatives; width zero evaluates only energy."""
    def __init__(self, value, derivative):
        self.value, self.derivative = value, tuple(derivative)

    def constant(self, value):
        return value if isinstance(value, _Dual) else _Dual(Decimal(value), (Decimal(0),)*len(self.derivative))

    def __add__(self, other):
        other = self.constant(other)
        return _Dual(self.value+other.value, [a+b for a,b in zip(self.derivative, other.derivative)])

    __radd__ = __add__

    def __neg__(self):
        return _Dual(-self.value, [-x for x in self.derivative])

    def __sub__(self, other):
        return self + -self.constant(other)

    def __rsub__(self, other):
        return self.constant(other) + -self

    def __mul__(self, other):
        other = self.constant(other)
        return _Dual(self.value*other.value, [a*other.value+self.value*b for a,b in zip(self.derivative, other.derivative)])

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = self.constant(other)
        quotient = self.value/other.value
        return _Dual(quotient, [(a-quotient*b)/other.value for a,b in zip(self.derivative, other.derivative)])

    def sqrt(self):
        root = self.value.sqrt()
        return _Dual(root, [v/(2*root) for v in self.derivative])


def _dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def _energy(points, proxy, pi, *, gradients):
    width = 12 if gradients else 0
    sites = [[_Dual(v, [Decimal(3*i+j == k) for k in range(width)]) for j,v in enumerate(p)] for i,p in enumerate(points)]
    a, axis, b = [[x-y for x,y in zip(sites[i],sites[j])] for i,j in [(0,1),(2,1),(2,3)]]
    left, right = _cross(a,axis), _cross(axis,b)
    ll, rr, aa = _dot(left,left), _dot(right,right), _dot(axis,axis)
    if ll.value == 0 or rr.value == 0 or aa.value == 0:
        return None
    denominator = ll.sqrt()*rr.sqrt()
    cosine = _dot(left,right)/denominator
    sine = _dot(axis,_cross(left,right))/(aa.sqrt()*denominator)
    ideal_sine, ideal_cosine = _sincos(_exact(proxy['angle_ideal'])*pi/180, pi)
    real = cosine*ideal_cosine+sine*ideal_sine
    imaginary = sine*ideal_cosine-cosine*ideal_sine
    # Integer complex powers implement cos(n*(model-ideal)), without an angle
    # branch, native acos, or a copied native grad_delta expression.
    power_real, power_imaginary = real.constant(1), real.constant(0)
    for _ in range(proxy['periodicity']):
        power_real, power_imaginary = (power_real*real-power_imaginary*imaginary,
                                      power_real*imaginary+power_imaginary*real)
    energy = (1-power_real)*(9600*_exact(proxy['weight'])/(proxy['periodicity']**2))
    geometry = {'angle_degrees':_atan2(sine.value,cosine.value,pi)*180/pi,
                'minimum_plane_sine':min((ll.value/(_dot(a,a).value*aa.value)).sqrt(),
                                        (rr.value/(_dot(b,b).value*aa.value)).sqrt())}
    return energy, geometry


def evaluate_torsion(points, proxy, *, digits=90):
    """Evaluate exact binary inputs using a fixed, private decimal context."""
    converted = _validate(points,proxy,digits)
    result = {'status':'UNDEFINED_COLLINEAR','digits':digits,
              'input_coordinates_exact':[[str(v) for v in p] for p in converted],
              'input_angle_ideal_exact':str(_exact(proxy['angle_ideal'])),
              'input_weight_exact':str(_exact(proxy['weight']))}
    with localcontext(Context(prec=digits)):
        value = _energy(converted,proxy,_pi(digits),gradients=True)
        if value is None:
            return result
        energy, geometry = value
        result.update(status='DEFINED',target=str(energy.value),gradient=[str(v) for v in energy.derivative],
                      gradient_norm=str(sum(v*v for v in energy.derivative).sqrt()),
                      **{key:str(v) for key,v in geometry.items()})
    return result


def _comparison(a, b, absolute='1e-30', relative='1e-30'):
    a,b = list(map(Decimal,a)),list(map(Decimal,b))
    _need(len(a) == len(b) and len(a) > 0)
    errors = [abs(x-y) for x,y in zip(a,b)]
    bounds = [max(Decimal(absolute),Decimal(relative)*max(abs(x),abs(y))) for x,y in zip(a,b)]
    return {'consistent':all(x<=y for x,y in zip(errors,bounds)),
            'maximum_absolute_difference':str(max(errors)),
            'absolute_tolerance':absolute,'relative_tolerance':relative}



def _ulp_sensitivity(points, proxy, baseline):
    """One representable coordinate step is a numerical, nonchemical control."""
    rows=[]
    for axis in range(12):
        value=float(points[axis//3][axis%3])
        for sign in [-1,1]:
            shifted=[p.copy() for p in points]
            after=math.nextafter(value,math.inf if sign>0 else -math.inf)
            _need(math.isfinite(after))
            shifted[axis//3][axis%3]=after
            observed=evaluate_torsion(shifted,proxy,digits=PRECISIONS[-1])
            # 1600 digits cover the full finite binary64 exponent range,
            # including exact subnormal displacement text at zero.
            with localcontext(Context(prec=1600)):
                exact_displacement=str(Decimal.from_float(after)-Decimal.from_float(value))
            row={'axis':axis,'direction':sign,'before_hex':value.hex(),'after_hex':after.hex(),
                 'coordinate_delta_exact':exact_displacement,
                 'status':observed['status']}
            if observed['status']=='DEFINED':
                row.update(target_difference=str(Decimal(observed['target'])-Decimal(baseline['target'])),
                           maximum_gradient_component_difference=_comparison(observed['gradient'],baseline['gradient'])['maximum_absolute_difference'])
            rows.append(row)
    return {'scope':'ONE_BINARY64_ULP; NONCHEMICAL_CONTROL','samples':rows,
            'maximum_gradient_component_difference':str(max(
                (Decimal(r['maximum_gradient_component_difference']) for r in rows if r['status']=='DEFINED'),default=Decimal(0)))}


def audit_precision(points, proxy, native_by_order):
    """Compare two precisions, independent differences and saved native values.

    Decimal finite differences are mathematical controls at much smaller steps;
    they do not reclassify any binary64 finite-difference observation.
    """
    _validate(points,proxy,PRECISIONS[-1])
    _need(set(native_by_order) == {'forward','reversed'})
    for native in native_by_order.values():
        for kind in ['single','accumulated']:
            _exact(native[kind+'_target'])
            _need(len(native[kind+'_gradient']) == 12)
            for value in native[kind+'_gradient']:
                _exact(value)
    result = {'schema_version':1,'policy_id':POLICY_ID,'precisions':list(PRECISIONS),
              'decimal_finite_difference_steps':list(STEPS),'orders':{},'native_comparisons':{},
              'endpoint_requalification':'NOT_RUN','automatic_adoption':False}
    with localcontext(Context(prec=PRECISIONS[-1])):
        for order, ordered in [('forward',points),('reversed',points[::-1])]:
            low, high = [evaluate_torsion(ordered,proxy,digits=n) for n in PRECISIONS]
            if low['status'] != 'DEFINED' or high['status'] != 'DEFINED':
                result.update(status='UNDEFINED_COLLINEAR',precision_stable=False,
                              reversal_consistent=False,finite_differences_consistent=False)
                result['orders'][order]={'references':[low,high]}
                continue
            stable = _comparison([low['target'],*low['gradient']],[high['target'],*high['gradient']])
            exact = [[Decimal(v) for v in p] for p in high['input_coordinates_exact']]
            differences = []
            for axis in range(12):
                samples=[]
                for step in STEPS:
                    h=Decimal(step); targets=[]
                    for sign in [1,-1]:
                        shifted=[p.copy() for p in exact];shifted[axis//3][axis%3]+=sign*h
                        value=_energy(shifted,proxy,_pi(PRECISIONS[-1]),gradients=False)
                        _need(value is not None);targets.append(value[0].value)
                    numerical=(targets[0]-targets[1])/(2*h)
                    samples.append({'step':step,'plus_target':str(targets[0]),'minus_target':str(targets[1]),
                                    'numerical':str(numerical),**_comparison([str(numerical)],[high['gradient'][axis]],'1e-20','1e-20')})
                differences.append({'axis':axis,'samples':samples,'consistent':all(r['consistent'] for r in samples)})
            result['orders'][order]={'references':[low,high],'precision_comparison':stable,'finite_differences':differences}
            native=native_by_order[order]; comparisons={}
            for kind in ['single','accumulated']:
                target=_comparison([str(_exact(native[kind+'_target']))],[high['target']],'1e-8','1e-10')
                gradient=_comparison([str(_exact(v)) for v in native[kind+'_gradient']],high['gradient'],'1e-8','1e-10')
                comparisons[kind]={'target_consistent':target['consistent'],'gradient_consistent':gradient['consistent'],
                                   'target':target,'gradient':gradient}
            result['native_comparisons'][order]=comparisons
        if result.get('status') == 'UNDEFINED_COLLINEAR':
            return result
        forward=result['orders']['forward']['references'][-1]; reverse=result['orders']['reversed']['references'][-1]
        reordered=[v for i in [9,6,3,0] for v in reverse['gradient'][i:i+3]]
        result['binary64_input_sensitivity']=_ulp_sensitivity(points,proxy,forward)
        result['reversal_comparison']=_comparison([forward['target'],*forward['gradient']],[reverse['target'],*reordered])
        result.update(status='DECIMAL_DIAGNOSTIC_COMPLETE',
                      precision_stable=all(row['precision_comparison']['consistent'] for row in result['orders'].values()),
                      reversal_consistent=result['reversal_comparison']['consistent'],
                      finite_differences_consistent=all(row['consistent'] for order in result['orders'].values() for row in order['finite_differences']))
    return result
