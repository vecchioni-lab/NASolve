"""Synthetic controls for recipe identity, exact role binding and read-only preview."""
from copy import deepcopy
from dataclasses import replace
import math

import pytest

from nasolve.metal import Atom, AtomKey, ModelSnapshot, Recipe, RecipeError, RoleMap, preview


def recipe_document():
    return {
        'kind': 'metal-restraint-recipe', 'schema_version': 1,
        'id': 'bridge', 'name': 'Synthetic bridge', 'revision': 1,
        'nodes': [
            {'id': 'left', 'kind': 'donor', 'residue_slot': 'base1', 'role': 'O4'},
            {'id': 'metal1', 'kind': 'metal', 'element': 'Au'},
            {'id': 'right', 'kind': 'donor', 'residue_slot': 'base2', 'role': 'N3'},
        ],
        'sets': [{'id': 'coordination', 'name': 'Coordination', 'enabled': True}],
        'restraints': [
            {'id': 'distance1', 'set_id': 'coordination', 'kind': 'distance',
             'nodes': ['left', 'metal1'], 'enabled': True, 'target': 2.0, 'sigma': 0.1,
             'unit': 'angstrom', 'source': {'kind': 'user', 'note': 'Synthetic test only'}},
            {'id': 'angle1', 'set_id': 'coordination', 'kind': 'angle',
             'nodes': ['left', 'metal1', 'right'], 'enabled': True,
             'target': 90.0, 'sigma': 3.0, 'unit': 'degree',
             'source': {'kind': 'user', 'note': 'Synthetic test only'}},
        ],
        'extensions': {'chemistry_note': 'Numerical test; no chemical qualification'},
    }


def atom_key(chain, residue, component, name, **kw):
    return AtomKey(model_id='1', chain_id=chain, residue_id=str(residue),
                   component_id=component, atom_name=name, **kw)


def model_inputs():
    left = Atom(atom_key('A', 12, 'Q17', 'S9'), 'S', (2.0, 0.0, 0.0))
    right = Atom(atom_key('B', 4, 'DT', 'N3'), 'N', (0.0, 2.0, 0.0))
    metal = Atom(atom_key('B', 101, 'AU', 'AU'), 'Au', (0.0, 0.0, 0.0))
    model = ModelSnapshot((left, right, metal), source_sha256='a' * 64,
                          checkpoint_id='refine-001')
    roles = RoleMap([
        {'Ligand code': 'Q17', 'O4': 'S9', 'N3': 'N8', "C5'": "C5'"},
        {'Ligand code': 'DT', 'N3': 'N3'},
    ], source_sha256='b' * 64, source_label='synthetic role-map fixture')
    return model, roles, {'base1': left.key.residue(), 'base2': right.key.residue()}, {'metal1': metal.key}


def build(document=None, **changes):
    model, roles, residues, atoms = model_inputs()
    arguments = dict(model=model, roles=roles, residue_slots=residues, atom_bindings=atoms)
    arguments.update(changes)
    return preview(Recipe(document or recipe_document()), **arguments)


def test_role_resolves_to_actual_name_and_element_and_keeps_measurements_separate():
    result = build()
    left = result['nodes'][0]
    assert left['node_id'] == 'left'
    assert left['atom']['key']['atom_name'] == 'S9'
    assert left['atom']['element'] == 'S'
    assert left['role'] == 'O4'
    distance, angle = result['restraints']
    assert distance['measured'] == 2.0
    assert distance['target'] == 2.0
    assert angle['measured'] == 90.0
    assert result['status'] == 'resolved'
    assert result['native_ready'] is False
    assert distance['node_ids'] == ['left', 'metal1']


def test_round_trip_is_immutable_and_preserves_optional_extensions():
    raw = recipe_document()
    raw['nodes'][0]['extensions'] = {'future_annotation': ['kept']}
    recipe = Recipe(raw)
    saved = recipe.to_json()
    raw['nodes'][0]['role'] = 'WRONG'
    returned = recipe.to_dict()
    returned['nodes'].clear()
    assert Recipe.from_json(saved).to_json() == saved
    assert Recipe.from_json(saved).sha256 == recipe.sha256
    assert recipe.to_dict()['nodes'][0]['role'] == 'O4'
    assert recipe.to_dict()['nodes'][0]['extensions']['future_annotation'] == ['kept']


def test_edit_and_remove_are_new_revisions_without_changing_stable_ids():
    original = Recipe(recipe_document())
    row = original.to_dict()['restraints'][0]
    row['target'] = 2.2
    changed = original.with_restraint(row)
    assert original.to_dict()['restraints'][0]['target'] == 2.0
    assert changed.to_dict()['revision'] == 2
    assert changed.to_dict()['nodes'] == original.to_dict()['nodes']
    assert changed.sha256 != original.sha256
    assert changed.with_restraint(row).sha256 == changed.sha256
    removed = changed.without_restraint('distance1')
    assert removed.to_dict()['revision'] == 3
    assert [r['id'] for r in removed.to_dict()['restraints']] == ['angle1']
    with pytest.raises(RecipeError, match='Unknown restraint'):
        removed.without_restraint('distance1')


@pytest.mark.parametrize('field,value', [
    ('target', float('nan')), ('sigma', float('inf')), ('sigma', 0),
    ('sigma', -1), ('target', -1), ('target', True), ('unit', 'degree'),
    ('nodes', ['left', 'missing']), ('nodes', ['left', 'left']),
    ('enabled', 'false'), ('set_id', 'missing'),
])
def test_invalid_restraints_fail_before_preview(field, value):
    document = recipe_document()
    document['restraints'][0][field] = value
    with pytest.raises(RecipeError):
        Recipe(document)


@pytest.mark.parametrize('change', ['duplicate_node', 'duplicate_restraint', 'duplicate_set',
                                    'version', 'revision_bool', 'unknown_field', 'angle_range'])
def test_recipe_schema_refuses_ambiguous_or_unsupported_documents(change):
    document = recipe_document()
    if change.startswith('duplicate_'):
        key = {'duplicate_node': 'nodes', 'duplicate_restraint': 'restraints', 'duplicate_set': 'sets'}[change]
        document[key].append(deepcopy(document[key][0]))
    elif change == 'version': document['schema_version'] = 2
    elif change == 'revision_bool': document['revision'] = True
    elif change == 'unknown_field': document['launch_refinement'] = True
    else: document['restraints'][1]['target'] = 181
    with pytest.raises(RecipeError):
        Recipe(document)


def test_duplicate_json_keys_are_not_silently_reinterpreted():
    with pytest.raises(RecipeError, match='Duplicate JSON key'):
        Recipe.from_json('{"kind":"metal-restraint-recipe","kind":"other"}')


def test_unset_target_and_missing_donor_are_saved_and_local_to_affected_rows():
    document = recipe_document()
    document['restraints'][0].update(target=None, sigma=None, source=None)
    recipe = Recipe.from_json(Recipe(document).to_json())
    model, roles, residues, atoms = model_inputs()
    del residues['base2']
    result = preview(recipe, model=model, roles=roles, residue_slots=residues, atom_bindings=atoms)
    distance, angle = result['restraints']
    assert distance['measured'] == 2.0
    assert set(distance['issues']) == {'missing_target', 'missing_sigma', 'missing_source'}
    assert angle['measured'] is None
    assert angle['status'] == 'incomplete'
    assert result['nodes'][2]['issues'] == ['missing_residue_binding']


def test_disabled_sets_are_retained_without_blocking_enabled_restraints():
    document = recipe_document()
    document['sets'].append({'id': 'later', 'name': 'Later', 'enabled': False})
    document['restraints'][1]['set_id'] = 'later'
    model, roles, residues, atoms = model_inputs()
    del residues['base2']
    result = build(document, residue_slots=residues)
    assert result['restraints'][1]['status'] == 'disabled'
    assert result['status'] == 'resolved'
    document['sets'][0]['enabled'] = False
    assert build(document)['status'] == 'draft'


def test_ambiguous_component_records_and_coordinate_matches_are_not_guessed():
    model, roles, residues, atoms = model_inputs()
    conflict = RoleMap([{'Ligand code': 'Q17', 'O4': 'S9'},
                        {'Ligand code': 'Q17', 'O4': 'OTHER'},
                        {'Ligand code': 'DT', 'N3': 'N3'}],
                       source_sha256='b' * 64, source_label='conflict fixture')
    assert build(roles=conflict)['nodes'][0]['issues'] == ['ambiguous_role_record']
    duplicate = replace(model, atoms=(*model.atoms, model.atoms[0]))
    assert build(model=duplicate)['nodes'][0]['issues'] == ['ambiguous_atom']
    assert build(model=duplicate)['nodes'][1]['status'] == 'resolved'


def test_equivalent_descriptive_records_reuse_existing_component_resolution():
    model, roles, residues, atoms = model_inputs()
    records = roles.records()
    alias = deepcopy(records[0]); alias.update(Name='Another description', Notes='Alias')
    records.append(alias)
    role_map = RoleMap(records, source_sha256='b' * 64, source_label='alias fixture')
    result = build(roles=role_map)
    assert result['nodes'][0]['status'] == 'resolved'
    assert result['nodes'][0]['role_resolution']['matching_records'] == 2


@pytest.mark.parametrize('field,value', [('model_id', '2'), ('chain_id', 'AA'),
    ('residue_id', '-12'), ('insertion_code', 'A'), ('component_id', 'OTHER'),
    ('altloc', 'A'), ('segment_id', 'second')])
def test_identity_fields_require_exact_binding(field, value):
    model, roles, residues, atoms = model_inputs()
    key = replace(model.atoms[0].key, **{field: value})
    altered = replace(model, atoms=(replace(model.atoms[0], key=key), *model.atoms[1:]))
    assert build(model=altered)['nodes'][0]['issues'] == ['missing_atom']
    if field != 'component_id':
        residues['base1'] = key.residue()
        assert build(model=altered, residue_slots=residues)['nodes'][0]['status'] == 'resolved'


def test_prime_names_are_not_normalized_and_concrete_only_nodes_are_supported():
    document = recipe_document()
    document['nodes'][0] = {'id': 'left', 'kind': 'atom'}
    model, roles, residues, atoms = model_inputs()
    key = replace(model.atoms[0].key, atom_name="C5'")
    altered = replace(model, atoms=(replace(model.atoms[0], key=key, element='C'), *model.atoms[1:]))
    atoms['left'] = key
    residues.pop('base1')
    result = build(document, model=altered, residue_slots=residues, atom_bindings=atoms)
    assert result['nodes'][0]['scope'] == 'concrete_only'
    assert result['nodes'][0]['atom']['key']['atom_name'] == "C5'"
    atoms['left'] = replace(key, atom_name='C5')
    assert build(document, model=altered, residue_slots=residues, atom_bindings=atoms)['nodes'][0]['issues'] == ['missing_atom']


def test_placeholders_and_species_mismatch_never_materialize_atoms():
    model, roles, residues, atoms = model_inputs()
    assert build(atom_bindings={})['nodes'][1]['issues'] == ['missing_atom_binding']
    document = recipe_document(); document['nodes'][1]['element'] = 'Ag'
    assert build(document)['nodes'][1]['issues'] == ['metal_element_mismatch']
    assert model.atoms[2].element == 'Au'


def test_nonidentity_symmetry_is_explicitly_unqualified_in_first_preview():
    model, roles, residues, atoms = model_inputs()
    key = replace(model.atoms[0].key, symmetry='-x,y,-z')
    altered = replace(model, atoms=(replace(model.atoms[0], key=key), *model.atoms[1:]))
    residues['base1'] = key.residue()
    assert build(model=altered, residue_slots=residues)['nodes'][0]['issues'] == ['unsupported_symmetry']


def test_degenerate_angle_and_two_nodes_bound_to_one_atom_are_explained():
    model, roles, residues, atoms = model_inputs()
    coincident = replace(model, atoms=(replace(model.atoms[0], xyz=(0, 0, 0)), *model.atoms[1:]))
    assert 'undefined_angle' in build(model=coincident)['restraints'][1]['issues']
    document = recipe_document()
    document['nodes'][2] = {'id': 'right', 'kind': 'atom'}
    residues.pop('base2'); atoms['right'] = model.atoms[0].key
    result = build(document, residue_slots=residues, atom_bindings=atoms)
    assert 'same_atom_endpoints' in result['restraints'][1]['issues']


def test_six_site_nonplanar_cluster_and_mixed_species_have_no_three_site_limit():
    document = recipe_document()
    xyz = [(2, 0, 0), (-2, 0, 0), (0, 2, 0), (0, -2, 0), (0, 0, 2), (0, 0, -2)]
    document['nodes'] = [{'id': f'm{i}', 'kind': 'metal', 'element': 'Au' if i % 2 else 'Ag'} for i in range(6)]
    document['restraints'] = [dict(document['restraints'][0], nodes=['m0', 'm4'])]
    atoms = tuple(Atom(atom_key('C', i + 1, 'MET', f'M{i}'), n['element'], p)
                  for i, (n, p) in enumerate(zip(document['nodes'], xyz)))
    model = ModelSnapshot(atoms, source_sha256='c' * 64)
    _, roles, _, _ = model_inputs()
    result = preview(Recipe.from_json(Recipe(document).to_json()), model=model, roles=roles,
                     residue_slots={}, atom_bindings={f'm{i}': a.key for i, a in enumerate(atoms)})
    assert result['restraints'][0]['measured'] == pytest.approx(math.sqrt(8))
    assert len(result['nodes']) == 6


def test_preview_is_deterministic_with_frozen_inputs_and_no_call_or_file_side_effect(monkeypatch):
    import builtins
    import subprocess
    model, roles, residues, atoms = model_inputs()
    recipe = Recipe(recipe_document())
    original = (recipe.to_json(), model.fingerprint, roles.fingerprint, deepcopy(residues), deepcopy(atoms))
    def forbidden(*args, **kwargs):
        raise AssertionError('Preview attempted external execution or file I/O')
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    first = preview(recipe, model=model, roles=roles, residue_slots=residues, atom_bindings=atoms)
    second = preview(recipe, model=model, roles=roles, residue_slots=dict(reversed(list(residues.items()))), atom_bindings=atoms)
    assert first == second
    assert original == (recipe.to_json(), model.fingerprint, roles.fingerprint, residues, atoms)
    assert first['inputs']['model']['source_sha256'] == 'a' * 64
    assert first['inputs']['roles']['source_sha256'] == 'b' * 64
    first['nodes'][0]['atom']['xyz'][0] = 999
    assert model.atoms[0].xyz == (2.0, 0.0, 0.0)


def test_preview_fingerprint_changes_with_coordinates_roles_or_binding_source():
    model, roles, residues, atoms = model_inputs()
    first = build()['input_sha256']
    moved = replace(model, atoms=(replace(model.atoms[0], xyz=(2.1, 0, 0)), *model.atoms[1:]))
    assert build(model=moved)['input_sha256'] != first
    assert build(model=replace(model, source_sha256='c' * 64))['input_sha256'] != first
    changed_roles = RoleMap(roles.records(), source_sha256='d' * 64, source_label='different source')
    assert build(roles=changed_roles)['input_sha256'] != first


def test_unknown_bindings_are_not_silently_dropped():
    model, roles, residues, atoms = model_inputs()
    atoms['typo'] = model.atoms[2].key
    with pytest.raises(RecipeError, match='Unknown atom binding'):
        build(atom_bindings=atoms)


@pytest.mark.parametrize('count', [0, 1, 2, 3])
def test_zero_through_three_metal_recipe_graphs_round_trip(count):
    document = recipe_document()
    document['nodes'] = [{'id': f'm{i}', 'kind': 'metal', 'element': 'Au'} for i in range(count)]
    document['restraints'] = []
    assert len(Recipe.from_json(Recipe(document).to_json()).to_dict()['nodes']) == count


def test_independent_panel_edits_share_stable_ids_and_retain_previous_snapshot():
    recipe = Recipe(recipe_document())
    model, roles, residues, atoms = model_inputs()
    before = preview(recipe, model=model, roles=roles, residue_slots=residues, atom_bindings=atoms)
    hidden = recipe.with_set({'id': 'coordination', 'name': 'Coordination', 'enabled': False})
    after = preview(hidden, model=model, roles=roles, residue_slots=residues, atom_bindings=atoms)
    assert after['nodes'] == before['nodes']
    assert [r['restraint_id'] for r in after['restraints']] == [r['restraint_id'] for r in before['restraints']]
    assert after['status'] == 'draft' and before['status'] == 'resolved'
    assert after['inputs']['model_inventory_sha256'] == before['inputs']['model_inventory_sha256']
    assert hidden.sha256 != recipe.sha256
    invalid = recipe.to_dict(); invalid['camera'] = {'zoom': 4}
    with pytest.raises(RecipeError):
        Recipe(invalid)


def test_structural_edits_refuse_dangling_references_and_do_not_cascade():
    recipe = Recipe(recipe_document())
    with pytest.raises(RecipeError):
        recipe.without_node('left')
    with pytest.raises(RecipeError):
        recipe.without_set('coordination')
    draft = recipe.with_node({'id': 'm2', 'kind': 'metal', 'element': 'Ag'})
    assert len(draft.to_dict()['nodes']) == 4
    assert len(draft.without_node('m2').to_dict()['nodes']) == 3
    assert len(recipe.to_dict()['nodes']) == 3


@pytest.mark.parametrize('case', ['node_kind', 'metadata_keys', 'bad_element', 'bad_coordinate',
                                  'missing_source_hash', 'missing_role', 'missing_record'])
def test_bad_inputs_and_missing_mapping_details_have_explicit_outcomes(case):
    document = recipe_document()
    model, roles, residues, atoms = model_inputs()
    if case == 'missing_role':
        document['nodes'][0]['role'] = 'unknown'
        assert build(document)['nodes'][0]['issues'] == ['missing_role']
    elif case == 'missing_record':
        roles = RoleMap([], source_sha256='b' * 64, source_label='empty')
        assert build(roles=roles)['nodes'][0]['issues'] == ['missing_role_record']
    else:
        with pytest.raises(RecipeError):
            if case == 'node_kind':
                document['nodes'][0]['kind'] = []
                Recipe(document)
            elif case == 'metadata_keys':
                document['extensions'] = {1: 'numeric', '1': 'string'}
                Recipe(document)
            elif case == 'bad_element':
                replace(model.atoms[0], element='O4')
            elif case == 'bad_coordinate':
                replace(model.atoms[0], xyz=(0, float('inf'), 0))
            else:
                replace(model, source_sha256='missing')


def test_saved_recipe_and_explicit_preview_inputs_replay_after_source_checkout_is_gone(tmp_path):
    """Move an isolated source checkout and its synthetic data, then replay fresh."""
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import nasolve.metal
    import nasolve.component_records

    original = tmp_path / 'original-checkout'
    package = original / 'src' / 'nasolve'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('')
    shutil.copytree(Path(nasolve.metal.__file__).parent, package / 'metal',
                    ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(nasolve.component_records.__file__, package / 'component_records.py')
    (original / 'saved.json').write_text(json.dumps(build()))
    relocated = tmp_path / 'relocated-checkout'
    original.rename(relocated)
    assert not original.exists()
    code = '''
import json
from pathlib import Path
import nasolve.metal
from nasolve.metal import Atom, AtomKey, ModelSnapshot, Recipe, ResidueKey, RoleMap, preview
assert Path(nasolve.metal.__file__).resolve().is_relative_to(Path.cwd())
saved = json.loads(Path('saved.json').read_text())
i = saved['inputs']
m = i['model']; r = i['roles']
model = ModelSnapshot(tuple(Atom(AtomKey(**a['key']), a['element'], a['xyz']) for a in m['atoms']),
                      source_sha256=m['source_sha256'], checkpoint_id=m['checkpoint_id'])
roles = RoleMap(r['records'], source_sha256=r['source_sha256'], source_label=r['source_label'])
result = preview(Recipe(i['recipe']), model=model, roles=roles,
                 residue_slots={k: ResidueKey(**v) for k, v in i['residue_slots'].items()},
                 atom_bindings={k: AtomKey(**v) for k, v in i['atom_bindings'].items()})
assert result == saved
print('relocated preview reproduces exactly')
'''
    result = subprocess.run([sys.executable, '-B', '-c', code], cwd=relocated,
                            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(relocated / 'src')},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'relocated preview reproduces exactly'


@pytest.mark.parametrize('field,value', [('enabled', 1), ('target', True)])
def test_equal_numeric_values_cannot_bypass_edit_validation(field, value):
    document = recipe_document()
    document['restraints'][0]['target'] = 1.0
    recipe = Recipe(document)
    row = recipe.to_dict()['restraints'][0]
    row[field] = value
    with pytest.raises(RecipeError):
        recipe.with_restraint(row)


def test_metadata_type_change_is_a_real_revision_even_when_python_values_compare_equal():
    recipe = Recipe(recipe_document())
    row = recipe.to_dict()['restraints'][0]
    row['extensions'] = {'future_flag': 1}
    first = recipe.with_restraint(row)
    row['extensions']['future_flag'] = True
    second = first.with_restraint(row)
    assert second.sha256 != first.sha256
    assert second.to_dict()['revision'] == first.to_dict()['revision'] + 1
