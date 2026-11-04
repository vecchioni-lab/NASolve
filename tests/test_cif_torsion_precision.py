"""Independent high-precision evidence must not qualify a native endpoint."""
from copy import deepcopy
from decimal import Decimal, localcontext
import math
import pytest
from nasolve.cif_torsion_precision import evaluate_torsion, audit_precision


def fixture():
    return [[0.,1.,0.],[0.,0.,0.],[1.,0.,0.],[1.,0.,1.]], {
        'angle_ideal':0.,'weight':1.,'periodicity':1,'alt_angle_ideals':None,
        'limit':-1.,'top_out':False,'slack':0.,'symmetry':'NONE'}


@pytest.mark.parametrize('period,target,end_y', [(1,'9600','-9600'),(2,'4800','0'),(3,str(Decimal(9600)/9),'3200')])
def test_right_angle_has_known_periodic_energy_and_cartesian_derivative(period,target,end_y):
    points,proxy=fixture();proxy['periodicity']=period
    r=evaluate_torsion(points,proxy,digits=80)
    assert r['status']=='DEFINED'
    assert abs(Decimal(r['angle_degrees'])-90)<Decimal('1e-65')
    assert abs(Decimal(r['target'])-Decimal(target))<Decimal('1e-20')
    assert abs(Decimal(r['gradient'][10])-Decimal(end_y))<Decimal('1e-65')
    assert abs(Decimal(r['gradient'][11]))<Decimal('1e-65')


def test_exact_binary_inputs_are_preserved_and_decimal_context_is_private():
    points,proxy=fixture();points[0][0]=.1
    with localcontext() as context:
        context.prec=6
        r=evaluate_torsion(points,proxy,digits=80)
        assert context.prec==6
    assert r==evaluate_torsion(points,proxy,digits=80)
    assert r['input_coordinates_exact'][0][0]==str(Decimal.from_float(.1))
    assert r['input_coordinates_exact'][0][0]!='0.1'


def test_known_energy_minimum_and_exact_collinearity_are_distinct():
    points,proxy=fixture();proxy['angle_ideal']=90.
    r=evaluate_torsion(points,proxy,digits=80)
    assert abs(Decimal(r['target']))<Decimal('1e-65')
    assert max(abs(Decimal(x)) for x in r['gradient'])<Decimal('1e-65')
    points[0]=[-1.,0.,0.]
    r=evaluate_torsion(points,proxy,digits=80)
    assert r['status']=='UNDEFINED_COLLINEAR' and 'gradient' not in r


@pytest.mark.parametrize('defect',['alternate','period_zero','period_fraction','period_bool','weight','top_out','slack','symmetry','limit','nan','shape','precision'])
def test_unsupported_functions_and_bad_inputs_are_refused(defect):
    points,proxy=fixture();digits=80
    if defect=='alternate':proxy['alt_angle_ideals']=[30.]
    elif defect=='period_zero':proxy['periodicity']=0
    elif defect=='period_fraction':proxy['periodicity']=1.5
    elif defect=='period_bool':proxy['periodicity']=True
    elif defect=='weight':proxy['weight']=-1.
    elif defect=='top_out':proxy['top_out']=True
    elif defect=='slack':proxy['slack']=1.
    elif defect=='symmetry':proxy['symmetry']='TRANSLATED'
    elif defect=='limit':proxy['limit']=1.
    elif defect=='nan':points[0][0]=math.nan
    elif defect=='shape':points[0].pop()
    else:digits=20
    with pytest.raises(ValueError):evaluate_torsion(points,proxy,digits=digits)


def test_translation_and_quarter_turn_preserve_energy_and_rotate_gradient():
    points,proxy=fixture();proxy['angle_ideal']=17.
    base=evaluate_torsion(points,proxy,digits=80)
    moved=[[-y+8,x+16,z-32] for x,y,z in points]
    r=evaluate_torsion(moved,proxy,digits=80)
    assert r['target']==base['target']
    a=list(map(Decimal,base['gradient']));b=list(map(Decimal,r['gradient']))
    with localcontext() as context:
        context.prec=90
        expected=[v for i in range(0,12,3) for v in [-a[i+1],a[i],a[i+2]]]
        assert max(abs(x-y) for x,y in zip(b,expected))<Decimal('1e-65')


def test_independent_differences_reversal_and_precision_preserve_native_mismatch():
    points,proxy=fixture();points[0]=[-1.,1e-8,0.];proxy['angle_ideal']=17.
    original=deepcopy((points,proxy))
    ref=evaluate_torsion(points,proxy,digits=90)
    g=list(map(float,ref['gradient']));reverse=[v for i in [9,6,3,0] for v in g[i:i+3]]
    native={order:{'single_target':float(ref['target']),'accumulated_target':float(ref['target']),
        'single_gradient':values.copy(),'accumulated_gradient':values.copy()}
        for order,values in [('forward',g),('reversed',reverse)]}
    native['forward']['single_gradient'][0]+=1
    r=audit_precision(points,proxy,native)
    assert r['precision_stable'] and r['reversal_consistent'] and r['finite_differences_consistent']
    assert not r['native_comparisons']['forward']['single']['gradient_consistent']
    assert r['native_comparisons']['reversed']['single']['gradient_consistent']
    assert r['endpoint_requalification']=='NOT_RUN' and not r['automatic_adoption']
    assert len(r['binary64_input_sensitivity']['samples'])==24
    assert Decimal(r['binary64_input_sensitivity']['maximum_gradient_component_difference'])>0
    assert (points,proxy)==original


def test_missing_order_and_nonfinite_native_evidence_cannot_claim_agreement():
    points,proxy=fixture()
    with pytest.raises(ValueError):audit_precision(points,proxy,{})



@pytest.mark.parametrize('z,angle', [(1.,90),(-1.,-90)])
def test_orientation_and_nonzero_ideal_have_known_energy(z,angle):
    points,proxy=fixture();points[-1][-1]=z;proxy['angle_ideal']=30.*z
    r=evaluate_torsion(points,proxy,digits=90)
    assert abs(Decimal(r['angle_degrees'])-angle)<Decimal('1e-75')
    assert abs(Decimal(r['target'])-4800)<Decimal('1e-75')


@pytest.mark.parametrize('field',['single_target','single_gradient'])
def test_nonfinite_native_comparison_is_refused(field):
    points,proxy=fixture();base={'single_target':1.,'accumulated_target':1.,'single_gradient':[0.]*12,'accumulated_gradient':[0.]*12}
    native={'forward':deepcopy(base),'reversed':deepcopy(base)}
    if field.endswith('gradient'):native['forward'][field][0]=math.inf
    else:native['forward'][field]=math.inf
    with pytest.raises(ValueError):audit_precision(points,proxy,native)


def test_one_ulp_displacement_text_is_exact_even_at_zero():
    points,proxy=fixture()
    base={'single_target':9600.,'accumulated_target':9600.,'single_gradient':[0.]*12,'accumulated_gradient':[0.]*12}
    r=audit_precision(points,proxy,{'forward':base,'reversed':deepcopy(base)})
    samples=[v for v in r['binary64_input_sensitivity']['samples'] if v['axis']==0]
    assert len(samples)==2
    for sample in samples:
        exact=Decimal.from_float(math.nextafter(0.,math.inf if sample['direction']>0 else -math.inf))
        assert sample['coordinate_delta_exact']==str(exact)


def test_native_comparison_keeps_the_existing_maximum_tolerance_rule():
    from nasolve.cif_torsion_precision import _comparison
    # At magnitude 100 the two allowances are each about 1e-8. Adding them
    # would incorrectly admit a 1.5e-8 discrepancy under the strict policy.
    r=_comparison(['100'],['100.000000015'],'1e-8','1e-10')
    assert not r['consistent']
