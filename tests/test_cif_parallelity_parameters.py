"""Refuse malformed native planes before executing their native kernels."""
from copy import deepcopy
import json
from types import SimpleNamespace as NS
import pytest
from tests.test_cif_parallelity_kernel import setup, Buffer, adapted


@pytest.mark.parametrize('field,value', [
    ('i_seqs', [0, 1, 99]), ('j_seqs', [-1, 2, 3]),
    ('i_seqs', [0, 0, 2]), ('j_seqs', [0, 1]),
    ('i_seqs', [False, 1, 2]), ('weight', 0.),
    ('weight', float('inf')), ('weight', True),
    ('target_angle_deg', float('nan')), ('slack', -1.),
    ('slack', 91.), ('limit', .5), ('limit', float('inf')),
    ('top_out', 1), ('origin_id', True), ('origin_id', 256),
    ('sym_ops', ['x,y,z']),
])
def test_invalid_parameters_never_enter_native_kernel(field, value):
    points, p, gr, flex = setup()
    setattr(p, field, value)
    def forbidden(**kwargs):
        raise AssertionError('native code entered before validation')
    gr.parallelity_residual_sum = forbidden
    kernel = adapted(gr, flex)
    buffer = Buffer([(.1, .2, .3)]*len(points))
    original = deepcopy(buffer)
    with pytest.raises(ValueError):
        kernel(sites_cart=Buffer(points), proxies=[p], gradient_array=buffer)
    assert buffer == original and kernel.statistics()['successful_calls'] == 0


@pytest.mark.parametrize('field', ['i_seqs', 'j_seqs', 'weight', 'target_angle_deg',
                                  'slack', 'limit', 'top_out', 'origin_id', 'sym_ops'])
def test_missing_native_parameter_is_not_assumed_to_be_default(field):
    points, p, gr, flex = setup(); delattr(p, field)
    gr.parallelity_residual_sum = lambda **kw: pytest.fail('native called')
    with pytest.raises(ValueError):
        adapted(gr, flex)(sites_cart=Buffer(points), proxies=[p], gradient_array=None)


def test_complete_parameter_capture_preserves_order_values_and_detaches_storage():
    from nasolve.cif_parallelity_kernel import parallelity_parameters
    points, p, gr, flex = setup()
    second = deepcopy(p); second.limit=2.5; second.top_out=True; second.origin_id=255
    second.i_seqs, second.j_seqs = second.j_seqs, second.i_seqs
    saved = deepcopy([vars(p), vars(second)])
    rows = parallelity_parameters([p,second], site_count=len(points))
    assert rows == saved and json.loads(json.dumps(rows,allow_nan=False)) == rows
    rows[0]['i_seqs'][0]=8; rows[1]['limit']=100.
    assert [vars(p), vars(second)] == saved


def test_capture_keeps_explicit_empty_symmetry_distinct_from_none():
    from nasolve.cif_parallelity_kernel import parallelity_parameters
    points, p, gr, flex = setup(); other=deepcopy(p);other.sym_ops=[]
    rows=parallelity_parameters([p,other],site_count=len(points))
    assert rows[0]['sym_ops'] is None and rows[1]['sym_ops']==[]


@pytest.mark.parametrize('count', [-1, True, 1.5])
def test_capture_requires_an_explicit_nonnegative_site_count(count):
    from nasolve.cif_parallelity_kernel import parallelity_parameters
    with pytest.raises(ValueError):parallelity_parameters([],site_count=count)


def test_capture_preserves_multiple_restraints_and_shared_atoms():
    from nasolve.cif_parallelity_kernel import parallelity_parameters
    points,p,gr,flex=setup(); p.j_seqs=[1,4,5]
    rows=parallelity_parameters([p,p],site_count=len(points))
    assert len(rows)==2 and rows[0]==rows[1] and rows[0]['j_seqs']==[1,4,5]
    assert parallelity_parameters([],site_count=0)==[]
