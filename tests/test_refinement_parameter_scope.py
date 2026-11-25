from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from nasolve.refinement_parameter_scope import ParameterScope, make_scope, scope_digest
from nasolve.refinement_parameter_native import observe_xyz, observe_group, capture_atoms, bind_scope


def atoms():
    return [dict(label=f'atom-{i}', scattering_type=symbol, xyz=[float(i), 2., 3.],
                 B=b, Q=q, f_prime=fp, f_double_prime=fdp)
            for i, (symbol, b, q, fp, fdp) in enumerate([
                ('N', 170., 1., .1, 0.), ('O', 400., .8, .2, 0.),
                ('Ag', 220., .4, -1., -2.), ('Hg', 310., .6, -8., 0.)])]


def packet():
    return make_scope(source_model_sha256='a'*64, initial_atoms=atoms(),
                      xyz_indices=[0, 1, 2], adp_groups=[[0], [1]])


def guard(record=None):
    record = packet() if record is None else record
    return ParameterScope(record, expected_sha256=scope_digest(record))


def compiled():
    return dict(strategy=['individual_sites', 'group_adp'],
        modes={k: k in ('individual_sites', 'group_adp') for k in
               ('individual_sites', 'torsion_angles', 'rigid_body', 'individual_adp',
                'group_adp', 'tls', 'occupancies', 'group_anomalous')},
        xyz_indices=[0, 1, 2], adp_groups=[[0], [1]], apply_adp_backtrace=False,
        apply_overall_adp_scale=False, refining_scattering=False)


def gradients():
    return [{k: k == 'site' and i < 3 for k in ('site', 'u_iso', 'u_aniso', 'occupancy', 'fp', 'fdp')}
            for i in range(4)]


def test_non_ft_mixed_scope_preserves_high_b_and_negative_scattering():
    g = guard()
    changed = atoms()
    changed[0]['B'] = 450.
    changed[1]['B'] = 125.
    changed[2]['xyz'][0] += .9  # mobile metal, still fixed B/Q/f′/f″
    result = g.state(changed)
    assert result['max_displacement_A'] == pytest.approx(.9)
    assert result['max_B_change_A2'] == 280.
    assert g.record()['initial_atoms'][2]['f_double_prime'] == -2.
    assert g.compiled(**compiled())['adp_groups'] == 2
    assert g.xyz_parameters(gradient_flags=gradients(), parameter_count=9)['parameter_count'] == 9
    assert g.group_parameters(selections=[[0], [1]], refine_adp=True,
                              refine_occ=False, parameter_count=2)['parameter_count'] == 2


@pytest.mark.parametrize('index,field,value', [
    (3, 'xyz', [4., 2., 3.]), (2, 'B', 221.), (3, 'B', 311.),
    (0, 'Q', .9), (2, 'Q', .5), (0, 'f_prime', .2), (2, 'f_double_prime', -1.),
    (3, 'label', 'different'), (2, 'scattering_type', 'Au'),
    (0, 'xyz', [float('nan'), 0., 0.]), (1, 'B', float('inf')),
    (0, 'Q', True), (0, 'B', -1.), (0, 'Q', 1.2), (0, 'xyz', [1., 2.])])
def test_protected_and_invalid_state_refused(index, field, value):
    rows = atoms(); rows[index][field] = value
    with pytest.raises(ValueError):
        guard().state(rows)


def test_initialization_protects_even_free_coordinates_and_b():
    rows = atoms(); rows[0]['xyz'][0] += .1
    with pytest.raises(ValueError, match='XYZ'):
        guard().state(rows, initial=True)
    rows = atoms(); rows[1]['B'] += 1
    with pytest.raises(ValueError, match='B'):
        guard().state(rows, initial=True)


@pytest.mark.parametrize('mutate', [
    lambda r: r.reverse(), lambda r: r.pop(), lambda r: r.append(deepcopy(r[0])),
    lambda r: r[0].update(label=r[1]['label']), lambda r: r[0].update(extra=1)])
def test_inventory_and_order_refused(mutate):
    rows = atoms(); mutate(rows)
    with pytest.raises(ValueError):
        guard().state(rows)


@pytest.mark.parametrize('key,value', [
    ('source_model_sha256', '/tmp/model.pdb'), ('xyz_indices', [True]),
    ('xyz_indices', [1, 0]), ('xyz_indices', [0, 0]), ('xyz_indices', [4]),
    ('xyz_indices', []), ('adp_groups', []), ('adp_groups', [[0], [0, 1]]),
    ('adp_groups', [[2, 1]]), ('adp_groups', [[0], []]), ('real_space', 1)])
def test_invalid_declarations_refused(key, value):
    p = packet(); p[key] = value
    with pytest.raises(ValueError):
        guard(p)


def test_record_is_detached_and_digest_is_authoritative():
    p = packet(); expected = scope_digest(p)
    g = ParameterScope(p, expected_sha256=expected)
    p['xyz_indices'].append(3)
    with pytest.raises(ValueError, match='checksum'):
        ParameterScope(p, expected_sha256=expected)
    returned = g.record(); returned['initial_atoms'][0]['B'] = 1
    assert g.record()['initial_atoms'][0]['B'] == 170.
    assert g.record()['xyz_indices'] == [0, 1, 2]


@pytest.mark.parametrize('key,value', [('schema_version', True), ('schema_version', 2),
                                      ('policy_id', 'metal-phased-xyz-v1'), ('extra', 1)])
def test_no_legacy_relabelling_or_unknown_schema(key, value):
    p = packet(); p[key] = value
    with pytest.raises(ValueError):
        guard(p)


@pytest.mark.parametrize('key,value', [
    ('strategy', ['individual_sites', 'individual_adp']),
    ('strategy', ['individual_sites', 'group_adp', 'occupancies']),
    ('xyz_indices', [0, 1, 2, 3]), ('adp_groups', [[0, 1]]),
    ('adp_groups', [[1], [0]]), ('adp_groups', [[0], [1], [2]]),
    ('apply_adp_backtrace', True), ('apply_overall_adp_scale', True),
    ('refining_scattering', True)])
def test_compiled_scope_changes_refused(key, value):
    args = compiled(); args[key] = value
    with pytest.raises(ValueError):
        guard().compiled(**args)


@pytest.mark.parametrize('mode', ['individual_adp', 'tls', 'occupancies', 'group_anomalous',
                                 'torsion_angles', 'rigid_body'])
def test_unexpected_active_mode_refused(mode):
    args = compiled(); args['modes'][mode] = True
    with pytest.raises(ValueError, match='mode'):
        guard().compiled(**args)


def test_optional_real_space_is_explicit_not_implied():
    p = packet(); p['real_space'] = True
    args = compiled()
    with pytest.raises(ValueError, match='strategy'):
        guard(p).compiled(**args)
    args['strategy'].insert(1, 'individual_sites_real_space')
    guard(p).compiled(**args)


@pytest.mark.parametrize('field', ['u_iso', 'u_aniso', 'occupancy', 'fp', 'fdp'])
def test_actual_xyz_cannot_free_other_parameters(field):
    flags = gradients(); flags[2][field] = True
    with pytest.raises(ValueError, match='unexpected parameter'):
        guard().xyz_parameters(gradient_flags=flags, parameter_count=10)


@pytest.mark.parametrize('mutate,count', [
    (lambda f: f[3].update(site=True), 12), (lambda f: f[0].update(site=False), 6),
    (lambda f: f.pop(), 9), (lambda f: f[0].update(site=1), 9), (lambda f: None, 8)])
def test_actual_xyz_scope_and_vector_size_refused(mutate, count):
    flags = gradients(); mutate(flags)
    with pytest.raises(ValueError):
        guard().xyz_parameters(gradient_flags=flags, parameter_count=count)


@pytest.mark.parametrize('key,value', [('selections', [[0, 1]]), ('selections', [[False], [True]]), ('refine_adp', False),
                                    ('refine_occ', True), ('parameter_count', 3)])
def test_actual_group_scope_refused(key, value):
    args = dict(selections=[[0], [1]], refine_adp=True, refine_occ=False, parameter_count=2)
    args[key] = value
    with pytest.raises(ValueError):
        guard().group_parameters(**args)


def fake_xs():
    import math
    rows = []
    for i, a in enumerate(atoms()):
        flags = NS(use_u_iso=lambda: True, use_u_aniso=lambda: False)
        for key, value in gradients()[i].items():
            setattr(flags, 'grad_' + key, lambda v=value: v)
        rows.append(NS(label=a['label'], scattering_type=a['scattering_type'], site=a['xyz'],
                       u_iso=a['B']/(8*math.pi**2), occupancy=a['Q'], fp=a['f_prime'],
                       fdp=a['f_double_prime'], flags=flags,
                       element_symbol=lambda symbol=a['scattering_type']: symbol))
    return NS(scatterers=lambda: rows, unit_cell=lambda: NS(orthogonalize=lambda v: v),
              n_parameters=lambda: 9)


def test_native_optimizer_adapters_read_actual_objects():
    xs = fake_xs()
    xyz = NS(refine_xyz=True, refine_adp=False, xray_structure=xs)
    group = NS(refine_adp=True, refine_occ=False, selections=[[0], [1]], x=[0., 0.],
               fmodel=NS(xray_structure=xs))
    assert observe_xyz(guard(), xyz)['parameters']['parameter_count'] == 9
    assert observe_group(guard(), group)['parameters']['parameter_count'] == 2
    xs.scatterers()[2].fdp += 1.
    with pytest.raises(ValueError, match='f_double_prime'):
        observe_group(guard(), group)
    with pytest.raises(ValueError, match='f_double_prime'):
        observe_xyz(guard(), xyz)


def test_anisotropic_native_state_is_not_silently_isotropized():
    xs = fake_xs(); xs.scatterers()[0].flags.use_u_aniso = lambda: True
    with pytest.raises(ValueError, match='all-isotropic'):
        capture_atoms(xs)


def binding_objects(monkeypatch, scattering_type, element):
    import sys
    xs = fake_xs()
    xs.scatterers()[-1].scattering_type = scattering_type
    xs.scatterers()[-1].element_symbol = lambda: element
    original = []
    for row in atoms():
        original.append(NS(id_str=lambda r=row: r['label'], element=row['scattering_type'],
            xyz=row['xyz'], b=row['B'], occ=row['Q'], uij_is_defined=lambda: False))
    hierarchy = NS(models_size=lambda: 1, atoms=lambda: original)
    parser = NS(construct_hierarchy=lambda: hierarchy)
    monkeypatch.setitem(sys.modules, 'iotbx', NS(pdb=NS(input=lambda **kw: parser)))
    model = NS(get_hierarchy=lambda: hierarchy, get_xray_structure=lambda: xs)
    refs = [{k: r[k] for k in ('label', 'scattering_type', 'f_prime', 'f_double_prime')}
            for r in capture_atoms(xs)]
    return model, refs


def test_scattering_reference_cannot_override_source_element(monkeypatch):
    model, refs = binding_objects(monkeypatch, 'Au', 'Au')
    with pytest.raises(ValueError, match='scattering element'):
        bind_scope(b'source bytes', model, expected_scattering=refs,
                   xyz_indices=[0, 1, 2], adp_groups=[[0], [1]])


@pytest.mark.parametrize('scattering_type', ['Hg', 'Hg2+'])
def test_native_element_identity_allows_charge_annotation(monkeypatch, scattering_type):
    model, refs = binding_objects(monkeypatch, scattering_type, 'Hg')
    scope = bind_scope(b'source bytes', model, expected_scattering=refs,
                       xyz_indices=[0, 1, 2], adp_groups=[[0], [1]])
    assert scope.record()['initial_atoms'][-1]['scattering_type'] == scattering_type
