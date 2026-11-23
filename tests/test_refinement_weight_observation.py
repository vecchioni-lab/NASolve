"""Native log summaries retain weighting evidence without inventing fixed policy."""
from hashlib import sha256
import pytest
from nasolve.refinement_weight_observation import observe_native_xyz_weights


def log(weights=(('618.328357','.500','1.000'),('275.311497','.795','1.000'))):
    lines=['Starting phenix.python', '  wxc_scale = 0.5', '  fix_wxc = None']
    for i,(w,s,c) in enumerate(weights,1):
        lines += [f'*** REFINEMENT MACRO_CYCLE {i} OF {len(weights)} ***',
            '====== Compute data/restraints target weights ======',
            '| XYZ refinement: T = Eexperimental * wxc * wxc_scale + Echem * wc |',
            f'| wxc = {w}    wxc_scale = {s}    wc = {c} |',
            '| wxu = 1.000 wxu_scale = 1.000 wu = 0.000 |']
    return ('\n'.join(lines+['Job complete','wall clock time: 5 seconds'])+'\n').encode()


def observe(raw, cycles=2):
    return observe_native_xyz_weights(raw, expected_log_sha256=sha256(raw).hexdigest(), expected_cycles=cycles)


def test_adaptive_weights_are_observed_with_exact_source_lines_and_rounding_limits():
    raw=log(); result=observe(raw)
    assert [r['printed_data_factor']for r in result['cycles']]==pytest.approx([309.1641785,218.872640115])
    assert not result['identical_printed_weights']
    for row in result['cycles']:
        assert row['printed']['wxc'] in raw.decode().splitlines()[row['line']-1]
    assert result['log_sha256']==sha256(raw).hexdigest()
    assert result['rounded_display_values'] and result['log_completion_observed']
    assert not any(result[k] for k in ('native_policy_inferred','runtime_authority','scientific_acceptance'))


def test_equal_printed_values_and_zero_chemistry_do_not_infer_fixed_native_policy():
    result=observe(log((('1.0','1.0','1.0'),('1.0','1.0','1.0'))))
    assert result['identical_printed_weights'] and not result['native_policy_inferred']
    row=observe(log((('2E+1','5e-1','0'),)),cycles=1)['cycles'][0]
    assert row['printed_data_factor']==10 and row['printed_data_to_chemistry_ratio'] is None


@pytest.mark.parametrize('mutate', [
    lambda b:b.replace(b'Job complete',b''),
    lambda b:b+b,
    lambda b:b.replace(b'CYCLE 2 OF 2',b'CYCLE 1 OF 2'),
    lambda b:b.replace(b'CYCLE 2 OF 2',b'CYCLE 2 OF 3'),
    lambda b:b.replace(b'| wxc = 275.311497    wxc_scale = .795    wc = 1.000 |',b''),
    lambda b:b.replace(b'| wxc = 618.328357',b'| wxc = nan'),
    lambda b:b.replace(b'| wxc = 618.328357',b'| wxc = -1'),
    lambda b:b.replace(b'| wxc = 618.328357',b'| wxc = 1e999'),
    lambda b:b.replace(b'Eexperimental * wxc * wxc_scale',b'Exray + Eneutron'),
    lambda b:b.replace(b'| wxc = 618.328357    wxc_scale = .500    wc = 1.000 |',
        b'| wxc = 618.328357    wxc_scale = .500    wc = 1.000 |\n| wxc = 1 wxc_scale = 1 wc = 1 |'),
])
def test_incomplete_ambiguous_or_unsupported_logs_refuse(mutate):
    with pytest.raises(ValueError):observe(mutate(log()))


@pytest.mark.parametrize('count',[True,0,1001,2.0])
def test_caller_must_declare_exact_cycle_scope(count):
    with pytest.raises(ValueError):observe(log(),cycles=count)


def test_changed_log_checksum_refuses_even_when_printed_weights_are_unchanged():
    raw=log()
    with pytest.raises(ValueError,match='checksum'):
        observe_native_xyz_weights(raw+b'changed context',expected_log_sha256=sha256(raw).hexdigest(),expected_cycles=2)
    with pytest.raises(ValueError,match='UTF-8'):observe(b'\xff')
