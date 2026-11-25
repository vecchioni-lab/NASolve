from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json

import pytest

from nasolve.autorefine import (
    AutoRefineError, ReflectionPlan, ReflectionSelectorPolicy,
    LEGACY_EXPLICIT, DATA_MANAGER_FILE_SCOPED, write_recipe_parameters,
)
from nasolve.metal.context import parse_pdb
from nasolve.metal.export import atom_selection
from nasolve.refinement_parameter_scope import ParameterScope, make_scope, scope_digest


def source(*, chain='K', name='N3'):
    specs = [('', 12, 'A', 'ZZ1', "C1'", 'A', 'SID1', 'C'),
             ('', 12, 'A', 'ZZ1', "C1'", 'B', 'SID1', 'C'),
             (chain, 4, '', 'ZZ2', name, '', 'SID2', 'N'),
             ('M', 1, '', 'AU', 'AU', '', '', 'AU')]
    return (''.join(
        f'HETATM{i:5d} {atom:>4s}{alt:1s}{resn:>3s} {ch:1s}{resid:4d}{ins:1s}   '
        f'{float(i):8.3f}{0.:8.3f}{0.:8.3f}{1.:6.2f}{200.:6.2f}      {seg:4s}{el:>2s}  \n'
        for i, (ch, resid, ins, resn, atom, alt, seg, el) in enumerate(specs, 1)) + 'END\n').encode()


def scope(raw=None, **changes):
    raw = source() if raw is None else raw
    parsed = parse_pdb(raw)
    atoms = [dict(label=f'caller-native-label-{i}', scattering_type=a.element,
                  xyz=list(a.xyz), B=200., Q=1., f_prime=0., f_double_prime=0.)
             for i, a in enumerate(parsed.snapshot.atoms)]
    kwargs = dict(source_model_sha256=sha256(raw).hexdigest(), initial_atoms=atoms,
                  xyz_indices=[0, 2, 3], adp_groups=[[0, 2], [1]], real_space=False)
    kwargs.update(changes)
    packet = make_scope(**kwargs)
    return ParameterScope(packet, expected_sha256=scope_digest(packet))


def kwargs():
    return dict(selector_policy=ReflectionSelectorPolicy('2.2.1-6174', DATA_MANAGER_FILE_SCOPED),
        observations=Path('/tmp/scope-writer-compat.mtz'),
        reflection_plan=ReflectionPlan(('F', 'SIGF'), 'FreeR_flag', 0, False, (), None, False, False, None),
        macro_cycles=5, processor_count=1, anomalous_atom_selections=(),
        real_space_sites=False, adp_mode='group', refine_occupancies=False,
        anomalous_mode='off')


def write(tmp_path, **changes):
    values=kwargs(); values.update(parameter_scope=scope(), scope_model=source()); values.update(changes)
    target=tmp_path/'recipe.params'
    result=write_recipe_parameters(target, **values)
    return target.read_text(), result


def test_scoped_writer_constructs_exact_fields_and_protection_controls(tmp_path):
    text, strategies = write(tmp_path)
    assert strategies == ('individual_sites', 'group_adp')
    keys = [a.key for a in parse_pdb(source()).snapshot.atoms]
    union = lambda ids: ' or '.join('('+atom_selection(keys[i])+')' for i in ids)
    assert 'individual = '+json.dumps(union([0, 2, 3])) in text
    assert 'group = '+json.dumps(union([0, 2])) in text
    assert 'group = '+json.dumps(union([1])) in text
    assert 'group_adp_refinement_mode = group_selection' in text
    assert 'individual = all' not in text and 'group = all' not in text
    assert 'apply_overall_isotropic_scale_to_adp = False' in text
    assert 'apply_back_trace = False' in text
    assert 'find_and_add_hydrogens = False' in text
    assert 'pdb_interpretation.sort_atoms = False' in text
    assert 'target = "auto"' in text and 'bulk_solvent_and_scale = False' not in text
    assert 'optimize_xyz_weight = True' in text
    assert 'optimize_adp_weight = True' in text
    assert '*occupancies' not in text and '*group_anomalous' not in text


@pytest.mark.parametrize('change', [
    {'parameter_scope': None}, {'scope_model': None}, {'parameter_scope': {}},
    {'scope_model': 'not bytes'}, {'scope_model': source()+b'REMARK changed\n'},
    {'adp_mode': 'none'}, {'adp_mode': 'individual'}, {'refine_coordinates': False},
    {'refine_coordinates': 1}, {'refine_occupancies': True}, {'refine_occupancies': 0},
    {'real_space_sites': True}, {'real_space_sites': 0}, {'anomalous_mode': 'refine'},
    {'anomalous_mode': 'fdp-only'}, {'counted_protocol': 'counted-xyz-fixed-unit-v1'},
])
def test_incompatible_scope_refused_without_touching_output(tmp_path, change):
    path=tmp_path/'recipe.params'; path.write_text('existing exact recipe\n')
    with pytest.raises(AutoRefineError):
        write(tmp_path, **change)
    assert path.read_text() == 'existing exact recipe\n'


def test_declared_real_space_does_not_claim_execution(tmp_path):
    text, strategies=write(tmp_path, parameter_scope=scope(real_space=True), real_space_sites=True)
    assert strategies == ('individual_sites', 'individual_sites_real_space', 'group_adp')
    assert 'group_adp_refinement_mode = group_selection' in text


def test_optional_api_leaves_ordinary_byte_output_exact(tmp_path):
    values=kwargs()
    path=tmp_path/'ordinary.params'
    write_recipe_parameters(path, **values)
    before=path.read_bytes()
    write_recipe_parameters(path, **values, parameter_scope=None, scope_model=None)
    assert path.read_bytes() == before
    assert b'individual = all' in before and b'group = all' in before
    assert b'apply_back_trace' not in before and b'sort_atoms' not in before


@pytest.mark.parametrize('fp,fdp', [(-8., 3.), (-8.100181579589844, 3.123456789012345)])
def test_fixed_anomalous_values_have_no_refinement_flags_in_scoped_writer(tmp_path, fp, fdp):
    values=kwargs(); plan=replace(values['reflection_plan'], anomalous=True,
                                 observation_labels=('F(+)', 'SIGF(+)', 'F(-)', 'SIGF(-)'))
    selection=atom_selection(parse_pdb(source()).snapshot.atoms[3].key)
    text, strategies=write(tmp_path, reflection_plan=plan, anomalous_mode='fixed',
        anomalous_atom_selections=[selection], anomalous_groups={selection:{'f_prime':fp, 'f_double_prime':fdp}})
    assert 'refine = None' in text
    assert f'f_prime = {fp!r}' in text and f'f_double_prime = {fdp!r}' in text
    assert 'group_anomalous' not in strategies


def test_fixed_scattering_still_requires_anomalous_data(tmp_path):
    with pytest.raises(AutoRefineError, match='anomalous observations'):
        write(tmp_path, anomalous_mode='fixed')
    assert not (tmp_path/'recipe.params').exists()


def test_scoped_writer_preserves_explicit_phase_file_and_target_policy(tmp_path):
    from pathlib import Path
    plan=replace(kwargs()['reflection_plan'], phase_file=Path('/tmp/original-phases.mtz'),
                 phase_labels=('HLA', 'HLB', 'HLC', 'HLD'))
    text, _=write(tmp_path, reflection_plan=plan)
    assert 'original-phases.mtz' in text and 'HLA,HLB,HLC,HLD' in text
    assert 'use_experimental_phases' not in text and 'target = "auto"' in text


@pytest.mark.parametrize('field,value', [('xyz', [99., 0., 0.]), ('B', 199.), ('Q', .5)])
def test_source_state_mismatch_refused(tmp_path, field, value):
    rows=scope().record()['initial_atoms']; rows[0][field]=value
    with pytest.raises(AutoRefineError, match='source XYZ/B/Q'):
        write(tmp_path, parameter_scope=scope(initial_atoms=rows))
    assert not (tmp_path/'recipe.params').exists()


def test_source_inventory_mismatch_refused(tmp_path):
    rows=scope().record()['initial_atoms'] + [dict(scope().record()['initial_atoms'][0], label='extra')]
    with pytest.raises(AutoRefineError, match='inventory'):
        write(tmp_path, parameter_scope=scope(initial_atoms=rows))


def test_case_normalized_native_identity_ambiguity_refused(tmp_path):
    raw=source()
    lines=raw.decode().splitlines()
    # The same atom identity distinguished only by case is ambiguous to native selection.
    new=lines[2][:21]+'k'+lines[2][22:]
    raw=('\n'.join(lines[:-1]+[new, 'END'])+'\n').encode()
    with pytest.raises(AutoRefineError, match='ambiguous'):
        write(tmp_path, scope_model=raw, parameter_scope=scope(raw))


def test_unsafe_selection_token_refused(tmp_path):
    raw=source(name='N"3')
    with pytest.raises(AutoRefineError, match='selector'):
        write(tmp_path, scope_model=raw, parameter_scope=scope(raw))


def test_source_anisou_needs_separate_policy(tmp_path):
    raw=source(); line=raw.decode().splitlines()[0]
    anisou='ANISOU'+line[6:28]+''.join(f'{v:7d}' for v in (1000,1000,1000,0,0,0))+line[70:]
    raw=raw.replace(b'END\n', (anisou+'\nEND\n').encode())
    with pytest.raises(AutoRefineError, match='isotropic'):
        write(tmp_path, scope_model=raw, parameter_scope=scope(raw))
