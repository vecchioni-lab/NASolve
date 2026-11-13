"""Background terminal phosphates need explicit intent and unchanged native chemistry."""
from copy import deepcopy
import shutil

import pytest

from .test_cif_native_context import native_case, audit, failures

POLICY='cif-explicit-site-native-context-v3'


def context():
    return dict(policy_id=POLICY,monomer_inventory='full_model',custom_restraints='required',
        retained_terminal_phosphates=[dict(site='A:3',component='DG',outgoing_site=None)])


def background_case():
    values=native_case(terminal=True)
    values[2].pop()  # It belongs to the unchanged background, not a replaced dictionary.
    return values


def test_explicit_background_phosphate_preserves_existing_native_definition():
    values=background_case();before=deepcopy(values)
    assert audit(values)['status']=='REVIEW'
    result=audit(values,context())
    assert result['status']=='LINKED_MECHANICS_PASS',failures(result)
    check=next(c for c in result['checks'] if c['check']=='declared-terminal-coordinate-phosphates')
    assert check['declared_terminal_sites']==['A:3']
    assert check['retained_terminal_sites']==['A:3']
    assert values==before and not result['automatic_adoption']


@pytest.mark.parametrize('defect',['undeclared','wrong_site','wrong_component','incoming','outgoing',
    'missing_coordinate','wrong_element','alias','changed_definition','missing_definition','overlap'])
def test_background_permission_cannot_hide_changed_or_undeclared_chemistry(defect):
    values=background_case();before,after,plans,links,ends=values;c=context()
    if defect=='undeclared':c.pop('retained_terminal_phosphates');c['policy_id']='cif-explicit-site-native-context-v2'
    if defect=='wrong_site':c['retained_terminal_phosphates'][0]['site']='B:3'
    if defect=='wrong_component':c['retained_terminal_phosphates'][0]['component']='DA'
    if defect=='incoming':links.append(('A:2','A:3'))
    if defect=='outgoing':c['retained_terminal_phosphates'][0]['outgoing_site']='A:1'
    if defect=='missing_coordinate':after['atoms']=[a for a in after['atoms'] if a['atom_id']!='OP3']
    if defect=='wrong_element':next(a for a in after['atoms'] if a['atom_id']=='OP3')['element']='S'
    if defect=='alias':next(a for a in after['atoms'] if a['atom_id']=='OP3')['atom_id']='O3P'
    definition=after['monomer_mappings']['rows'][2]['metadata']['effective_definition']
    if defect=='changed_definition':definition['atoms'][1]['charge']='-1'
    if defect=='missing_definition':after['monomer_mappings']['rows'][2]['metadata'].pop('effective_definition')
    if defect=='overlap':plans.append(native_case(terminal=True)[2][-1])
    assert audit(values,c)['status']=='REVIEW'


@pytest.mark.parametrize('defect',['empty','duplicate','extra','missing','bad_component','bad_site','self_link','old_policy','wrong_inventory'])
def test_context_schema_refuses_ambiguous_or_legacy_permission(defect):
    from nasolve.cif_native_context import validate_native_context
    c=context();row=c['retained_terminal_phosphates'][0]
    if defect=='empty':c['retained_terminal_phosphates']=[]
    if defect=='duplicate':c['retained_terminal_phosphates'].append(dict(row))
    if defect=='extra':row['allow_any_phosphate']=True
    if defect=='missing':row.pop('component')
    if defect=='bad_component':row['component']=''
    if defect=='bad_site':row['site']='A:*'
    if defect=='self_link':row['outgoing_site']=row['site']
    if defect=='old_policy':c['policy_id']='cif-explicit-site-native-context-v2'
    if defect=='wrong_inventory':c['monomer_inventory']='selected_only'
    with pytest.raises(ValueError):validate_native_context(c)


def test_declarations_come_from_frozen_intent_and_survive_relocation(tmp_path):
    from .test_cif_model_context import model,report
    from nasolve.cif_model_context import derive_prepared_model_context,validate_prepared_model_context
    from nasolve.cif_native_context import prepared_native_context
    old=tmp_path/'old';old.mkdir();p=model(old/'model.pdb',chains=(('A','ZZZ'),('B','DG')))
    bound=derive_prepared_model_context(p,report('A:1','B:1'),['ZZZ'])
    result=prepared_native_context(p,bound,custom_restraints='absent')
    assert result['policy_id']=='cif-explicit-site-native-context-v4'
    legacy=prepared_native_context(p,bound,custom_restraints='absent',retained_policy=POLICY)
    assert legacy==dict(result,policy_id=POLICY)
    assert result['retained_terminal_phosphates']==[dict(site='B:1',component='DG',outgoing_site='B:9')]
    new=tmp_path/'new';shutil.move(old,new);assert not old.exists()
    assert prepared_native_context(new/'model.pdb',validate_prepared_model_context(new/'model.pdb',bound),custom_restraints='absent')==result
    all_selected=derive_prepared_model_context(new/'model.pdb',report('A:1','B:1'),['ZZZ','DG'])
    assert prepared_native_context(new/'model.pdb',all_selected,custom_restraints='absent')==dict(
        policy_id='cif-explicit-site-native-context-v2',monomer_inventory='full_model',custom_restraints='absent')
