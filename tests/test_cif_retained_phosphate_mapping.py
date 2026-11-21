"""Use captured model-to-dictionary bindings, never an OP3/O3T name guess."""
from copy import deepcopy

import pytest

from .test_cif_retained_phosphate_context import background_case,context
from .test_cif_native_context import audit,failures


def mapped_case(alias='O3T'):
    values=background_case()
    for native in values[:2]:
        native['atom_name_mapping_policy']='cif-native-observed-atom-name-mapping-v1'
        for row in native['monomer_mappings']['rows']:
            atoms=[a for a in native['atoms'] if a['identity']['chain_id']+':'+a['identity']['resseq'].strip()==row['site']]
            row['resname']=atoms[0]['identity']['resname']
            definition=row['metadata']['effective_definition']
            if not definition:
                definition.update(atoms=[dict(atom_id=a['atom_id'],type_symbol=a['element']) for a in atoms],bonds=[])
            for a in atoms:
                if a['atom_id']=='keepH':a['element']='H'
                next(d for d in definition['atoms'] if d['atom_id']==a['atom_id'])['type_symbol']=a['element']
            names={a['atom_id']:alias if row['site']=='A:3' and a['atom_id']=='OP3' else a['atom_id'] for a in atoms}
            if row['site']=='A:3':
                for category in ['atoms','bonds']:
                    for d in definition[category]:
                        for key in d:
                            if key.startswith('atom_id') and d[key]=='OP3':d[key]=alias
            row['atom_name_mapping']=dict(status='RECORDED',mon_lib_names_available=False,
                aliases={a:b for a,b in names.items() if a!=b},duplicates=[],unexpected=[],
                active=[dict(model_i_seq=a['i_seq'],model_atom_id=a['atom_id'],mon_lib_name=None) for a in atoms],
                expected=[dict(model_i_seq=a['i_seq'],model_atom_id=a['atom_id'],dictionary_atom_id=names[a['atom_id']]) for a in atoms])
    c=context();c['policy_id']='cif-explicit-site-native-context-v4'
    return values,c


@pytest.mark.parametrize('alias',['O3T','Q7','TERMINAL_O'])
def test_observed_background_names_pass_without_a_literal_alias_whitelist(alias):
    values,c=mapped_case(alias);before=deepcopy(values)
    assert audit(values,context())['status']=='REVIEW'  # Literal v3 remains unchanged.
    result=audit(values,c)
    assert result['status']=='LINKED_MECHANICS_PASS',failures(result)
    check=next(r for r in result['checks'] if r['check']=='declared-terminal-coordinate-phosphates')
    assert check['retained_atom_name_bindings']['A:3']['OP3']==alias
    assert values==before and not result['automatic_adoption']


@pytest.mark.parametrize('defect',['missing_mapping','policy','alias_missing','alias_wrong','index','duplicate',
    'changed_binding','changed_definition','unmodelled_hydrogen','wrong_element','unsupported','missing_site','wrong_atom_order'])
def test_alias_evidence_cannot_hide_chemical_or_binding_changes(defect):
    values,c=mapped_case();before,after=values[:2];row=after['monomer_mappings']['rows'][2];mapping=row['atom_name_mapping']
    if defect=='missing_mapping':row.pop('atom_name_mapping')
    if defect=='policy':after['atom_name_mapping_policy']='unknown'
    if defect=='alias_missing':mapping['aliases']={}
    if defect=='alias_wrong':mapping['aliases']['OP3']='OP2'
    if defect=='index':mapping['expected'][-1]['model_i_seq']=0
    if defect=='duplicate':mapping['expected'].append(dict(mapping['expected'][0]))
    if defect=='changed_binding':
        old=before['monomer_mappings']['rows'][2]['atom_name_mapping'];old['aliases']={}
        next(a for a in old['expected'] if a['model_atom_id']=='OP3')['dictionary_atom_id']='OP3'
    if defect=='changed_definition':row['metadata']['effective_definition']['atoms'][1]['charge']='-1'
    if defect=='unmodelled_hydrogen':row['metadata']['effective_definition']['atoms'].append(dict(atom_id='HNEW',type_symbol='H'))
    if defect=='wrong_element':next(a for a in row['metadata']['effective_definition']['atoms'] if a['atom_id']=='O3T')['type_symbol']='S'
    if defect=='unsupported':row['atom_name_mapping']=dict(status='UNSUPPORTED',missing_fields=['expected_atoms'])
    if defect=='missing_site':after['monomer_mappings']['rows'].pop(0)
    if defect=='wrong_atom_order':after['atoms'][0]['i_seq']=True
    if defect=='wrong_atom_order':
        from nasolve.cif_native_context import declared_phosphate_check
        check=declared_phosphate_check(after,values[2],values[3],retained=c['retained_terminal_phosphates'],baseline=before,mapped=True)
        assert check['status']=='REVIEW'
    else:
        assert audit(values,c)['status']=='REVIEW'


def test_native_options_are_frozen_by_context_version():
    from nasolve.cif_native_context import native_context_options
    c=context();assert native_context_options(c)==dict(full_monomer_inventory=True)
    c['policy_id']='cif-explicit-site-native-context-v4'
    assert native_context_options(c)==dict(full_monomer_inventory=True,atom_name_mapping=True)
