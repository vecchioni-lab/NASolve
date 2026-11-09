"""A supplied parent allowance cannot renew an already observed deadline."""
import pytest
from nasolve.cif_outer_context import OuterAllowance


def test_constant_or_increasing_callback_cannot_renew_elapsed_time():
    clock=[0.];cap=[10.];budget=OuterAllowance(lambda:cap[0],lambda:clock[0])
    clock[0]=3;assert budget.remaining()==7
    cap[0]=100;clock[0]=9;assert budget.remaining()==1
    clock[0]=10
    with pytest.raises(TimeoutError):budget.remaining()


def test_callback_time_consumes_allowance_and_shrink_is_permanent():
    clock=[0.];cap=[10.]
    def callback():clock[0]+=2;return cap[0]
    budget=OuterAllowance(callback,lambda:clock[0]);assert budget.deadline==10
    cap[0]=3;assert budget.remaining()==1
    cap[0]=100
    with pytest.raises(TimeoutError):budget.remaining()


@pytest.mark.parametrize('value',[None,True,'1',float('nan'),float('inf')])
def test_invalid_callback_result_never_becomes_an_unbounded_allowance(value):
    with pytest.raises(ValueError):OuterAllowance(lambda:value,lambda:0.)


def test_absent_allowance_never_reads_clock():
    def clock():raise AssertionError('Unconfigured parent clock was read')
    assert OuterAllowance(None,clock).remaining() is None
