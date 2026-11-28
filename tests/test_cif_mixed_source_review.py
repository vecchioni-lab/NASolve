"""Current chemical declarations must not inherit historical verdicts."""
from copy import deepcopy
import json
import subprocess

import pytest

from nasolve.cif_mixed_context import _prepare_component, _ref, _select_context
from nasolve.cif_linked_preparation import component_values, _prune, _render
from nasolve.cif_mixed_source_review import review_verified_context
from tests.test_cif_mixed_context import context_fixture


def case(tmp_path, change=None):
    root = tmp_path.resolve(); parent = root/'parent'; parent.mkdir()
    context = root/'context'; context.mkdir()
    model, plan, sources, dictionaries, before, after, providers = context_fixture(parent)
    for code, path in providers.items():
        values = component_values(path, code)
        values['_chem_comp_atom.charge'] = ['0']*len(values['_chem_comp_atom.atom_id'])
        if code == 'Q17':
            if change == 'sugar':
                pairs = list(zip(values['_chem_comp_bond.atom_id_1'], values['_chem_comp_bond.atom_id_2']))
                index = next(i for i, pair in enumerate(pairs) if set(pair) == {"C1'", "C2'"})
                values['_chem_comp_bond.value_order'][index] = 'AROM'
                values['_chem_comp_bond.type'][index] = 'aromatic'
            elif change == 'phosphate':
                # An OP2-attached H loss is separate from an internal OP3 deletion.
                values = _prune(values, {'HOP2'}, outgoing=False)
                values['_chem_comp_atom.charge'][values['_chem_comp_atom.atom_id'].index('OP2')] = '-1'
            elif change == 'partial':
                values['_chem_comp_atom.partial_charge'] = ['?']*len(values['_chem_comp_atom.atom_id'])
                values['_chem_comp_atom.partial_charge'][values['_chem_comp_atom.atom_id'].index('OP2')] = '-0.4'
        path.write_text(_render(values, code))
    selection = _select_context(model, plan, sources, dictionaries, before, after)
    prepared = context/'prepared'
    receipt = _prepare_component(sources['Q17'], providers['Q17'], model, selection['contexts']['Q17'],
                                 prepared, code='Q17', normalize_group=True)
    parent_report = parent/'mixed_linked_recovery.json'
    parent_report.write_text(json.dumps({'bundle': {'preparations': {}}}))
    refs = [_ref(prepared/'base_dictionary.cif', context), _ref(providers['V29'], parent, parent=True)]
    report = {
        'inputs': {'sources': {c: _ref(p, parent, parent=True) for c, p in sources.items()},
                   'linked_parent_report': _ref(parent_report, parent, parent=True)},
        'bundle': {
            'effective_dictionaries': refs, 'installed_canonical_components': [],
            'preparations': {'Q17': {'receipt': receipt}},
            'site_projections': {row['site']: {'component': 'Q17', 'dictionary': _ref(
                prepared/('projected_'+row['site'].replace(':', '_')+'.cif'), context)} for row in receipt['sites']},
            'preserved_source_findings': {code: {'status': 'REJECTED', 'source_sha256': _ref(p, parent, parent=True)['sha256'],
                'rejection_reasons': ['historical-generated-state-changed']} for code, p in sources.items()},
        },
    }
    (context/'mixed_context.json').write_text(json.dumps(report))
    return context, parent, report


def inventory(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def component(review, code='Q17'):
    return next(row for row in review['components'] if row['component'] == code)


def differences(row, field):
    return next(d['changes'] for d in row['differences'] if d['field'] == field)


def test_recovered_declarations_do_not_inherit_old_rejection_and_reading_is_nonmutating(tmp_path, monkeypatch):
    context, parent, report = case(tmp_path)
    original = inventory(tmp_path)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Read-only audit launched a process'))
    review = review_verified_context(context, parent, report); row = component(review)
    assert row['historical_generation']['status'] == 'REJECTED'
    assert row['declaration_status'] == 'NO_DIFFERENCES_IN_COMPARED_FIELDS'
    assert row['differences'] == []
    assert row['source_graph_status'] == row['current_graph_status'] == 'PASS'
    contexts = {r['site']: r for r in row['site_contexts']}
    assert contexts['A:1']['five_prime_state'] == 'phosphate'
    assert contexts['A:1']['deleted_atoms'] == []
    assert contexts['A:2']['incoming_site'] == 'A:1'
    assert contexts['A:2']['deleted_atoms'] == ['HOP3', 'OP3']
    assert review['scientific_qualification'] == 'NOT_ASSESSED'
    assert review['source_state_repair'] == 'NOT_PERFORMED' and review['automatic_adoption'] is False
    assert inventory(tmp_path) == original


def test_sugar_bond_difference_survives_context_and_does_not_rewrite_source(tmp_path):
    context, parent, report = case(tmp_path, 'sugar'); original = inventory(tmp_path)
    review = review_verified_context(context, parent, report); row = component(review)
    changed = differences(row, 'bond_orders')
    assert changed == [{'key': "C1'|C2'", 'source_present': True, 'current_present': True,
                        'source': ['SINGLE'], 'current': ['AROMATIC']}]
    assert review['summary']['atom_bond_or_hydrogen_difference_components'] == ['Q17']
    assert inventory(tmp_path) == original


def test_op2_proton_and_charge_change_are_not_excused_by_declared_internal_op3_removal(tmp_path):
    context, parent, report = case(tmp_path, 'phosphate')
    row = component(review_verified_context(context, parent, report))
    assert differences(row, 'hydrogen_attachments') == [
        {'key': 'HOP2', 'source_present': True, 'current_present': False, 'source': ['OP2'], 'current': None}]
    charge = next(c for c in differences(row, 'declared_charge_fields') if c['key'] == 'OP2')
    assert charge['source'] == {'charge': '0'} and charge['current'] == {'charge': '-1'}
    assert row['site_contexts'][1]['deleted_atoms'] == ['HOP3', 'OP3']
    assert all('HOP2' not in s['deleted_atoms'] for s in row['site_contexts'])


def test_added_partial_charge_and_unknown_metadata_are_not_formal_charge_changes(tmp_path):
    context, parent, report = case(tmp_path, 'partial')
    review = review_verified_context(context, parent, report); row = component(review)
    assert row['changed_fields'] == ['declared_charge_fields']
    charge = next(c for c in differences(row, 'declared_charge_fields') if c['key'] == 'OP2')
    assert charge['source'] == {'charge': '0'}
    assert charge['current'] == {'charge': '0', 'partial_charge': '-0.4'}
    unknown = next(c for c in differences(row, 'declared_charge_fields') if c['key'] == 'P')
    assert unknown['current']['partial_charge'] is None
    assert review['summary']['atom_bond_or_hydrogen_difference_components'] == []
    assert review['summary']['other_declaration_difference_components'] == ['Q17']


def test_canonical_graph_agreement_cannot_claim_installed_numerical_agreement(tmp_path):
    context, parent, report = case(tmp_path)
    # Synthetic declared installed component: this inventory does not discover a library.
    report['bundle']['installed_canonical_components'] = ['V29']
    review = review_verified_context(context, parent, report)
    row = component(review, 'V29')
    assert row['comparison_scope'] == 'CANONICAL_GRAPH_INPUT_ONLY; INSTALLED_NUMERICS_NOT_COMPARED'
    assert review['summary']['explicit_components_compared'] == 1
    assert review['summary']['canonical_graph_only_components'] == ['V29']


@pytest.mark.parametrize('defect', ['source_bytes', 'current_bytes', 'projection_bytes', 'duplicate_provider',
                                  'missing_provider', 'missing_projection', 'duplicate_site'])
def test_changed_or_ambiguous_bound_inputs_cannot_receive_a_source_inventory(tmp_path, defect):
    context, parent, report = case(tmp_path)
    if defect == 'source_bytes': (parent/report['inputs']['sources']['Q17']['path']).write_bytes(b'changed')
    elif defect == 'current_bytes': (context/report['bundle']['effective_dictionaries'][0]['path']).write_bytes(b'changed')
    elif defect == 'projection_bytes': (context/report['bundle']['site_projections']['A:2']['dictionary']['path']).write_bytes(b'changed')
    elif defect == 'duplicate_provider': report['bundle']['effective_dictionaries'].append(deepcopy(report['bundle']['effective_dictionaries'][0]))
    elif defect == 'missing_provider': report['bundle']['effective_dictionaries'].pop()
    elif defect == 'missing_projection': report['bundle']['site_projections']['unexplained'] = deepcopy(report['bundle']['site_projections']['A:2'])
    elif defect == 'duplicate_site': report['bundle']['preparations']['Q17']['receipt']['sites'].append(
        deepcopy(report['bundle']['preparations']['Q17']['receipt']['sites'][0]))
    with pytest.raises(ValueError): review_verified_context(context, parent, report)


def test_source_inventory_is_stable_when_owned_views_are_relocated(tmp_path):
    original = tmp_path/'original'; original.mkdir()
    context, parent, report = case(original, 'sugar')
    first = review_verified_context(context, parent, report)
    moved = tmp_path/'relocated'; original.rename(moved)
    assert not original.exists()
    second = review_verified_context(moved/'context', moved/'parent', report)
    assert second == first
    assert str(original) not in json.dumps(second) and str(moved) not in json.dumps(second)
