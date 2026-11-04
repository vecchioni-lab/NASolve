"""Source names select graph roles; no atom renaming or generic protonation repair."""
from copy import deepcopy
import pytest
from tests.test_cif_linked_preparation import fixture
from tests.test_cif_preparation_qualification import qualification,POLICY
from nasolve.cif_linked_preparation import component_values,_render,prepare_linked_component
from nasolve.cif_phosphate_names import phosphate_names,POLICY_ID


def inputs(tmp_path):
    s,c,m,contexts=fixture(tmp_path)
    names={'OP1':'O1P','OP2':'O2P','OP3':'O3P'}
    for p in (s,c):
        v=component_values(p,'ZZZ');v['_chem_comp.group']=['DNA']
        for key,column in v.items():
            if 'atom_id' in key:v[key]=[names.get(x,x) for x in column]
        p.write_text(_render(v,'ZZZ'))
    lines=[]
    for line in m.read_text().splitlines(keepends=True):
        if line.startswith(('ATOM  ','HETATM')):
            if line[21:26].strip()!='A   2':line=line[:17]+'AAA'+line[20:]
            atom=line[12:16].strip();line=line[:12]+names.get(atom,atom).rjust(4)+line[16:]
        lines.append(line)
    m.write_text(''.join(lines))
    return s,c,m,[contexts[0]]


def test_explicit_alias_adapter_preserves_source_names_and_nonleaving_proton(tmp_path):
    s,c,m,contexts=inputs(tmp_path);before=[p.read_bytes() for p in (s,c,m)]
    q=qualification(s,c,'ZZZ')
    with pytest.raises(ValueError,match='atom convention'):
        prepare_linked_component(s,c,m,contexts,tmp_path/'old',code='ZZZ',native_qualification=q,bond_representation_policy=POLICY)
    r=prepare_linked_component(s,c,m,contexts,tmp_path/'out',code='ZZZ',native_qualification=q,
        bond_representation_policy=POLICY,phosphate_atom_policy=POLICY_ID)
    site=r['sites'][0]
    assert site['deleted_atoms']==['O3P','leaveH']
    assert site['retained_op2_hydrogens']==['keepH'] and 'O2P' in site['expected_atoms']
    assert 'OP2' not in site['expected_atoms'] and 'oddH' in site['expected_atoms']
    assert r['phosphate_names']=={'OP1':'O1P','OP2':'O2P','OP3':'O3P'}
    assert before==[p.read_bytes() for p in (s,c,m)]


@pytest.mark.parametrize('defect',['missing','ambiguous','wrong_element','other_neighbor','no_phosphorus'])
def test_names_alone_do_not_authorize_phosphate_roles(tmp_path,defect):
    s,c,m,contexts=inputs(tmp_path);v=component_values(s,'ZZZ')
    if defect=='missing':v['_chem_comp_atom.atom_id'][v['_chem_comp_atom.atom_id'].index('O2P')]='XYZ'
    if defect=='ambiguous':
        for k,col in list(v.items()):
            if k.startswith('_chem_comp_atom.'):
                col.append('OP2' if k.endswith('.atom_id') else col[v['_chem_comp_atom.atom_id'].index('O2P')])
    if defect=='wrong_element':v['_chem_comp_atom.type_symbol'][v['_chem_comp_atom.atom_id'].index('O2P')]='N'
    if defect=='other_neighbor':
        v['_chem_comp_bond.atom_id_1'].append('O2P');v['_chem_comp_bond.atom_id_2'].append("C5'")
    if defect=='no_phosphorus':v['_chem_comp_atom.type_symbol'][0]='C'
    with pytest.raises(ValueError):phosphate_names(v)


@pytest.mark.parametrize('defect',['unknown_policy','no_qualification','terminal_context','charged_leaving','bridged_leaving','retained_leaving'])
def test_unsupported_alias_operations_do_not_publish(tmp_path,defect):
    s,c,m,contexts=inputs(tmp_path)
    policy=POLICY_ID
    if defect=='unknown_policy':policy='guess'
    if defect=='terminal_context':contexts[0].update(incoming_site=None,five_prime_state='phosphate')
    if defect=='charged_leaving':
        for p in (s,c):
            v=component_values(p,'ZZZ');v['_chem_comp_atom.charge'][v['_chem_comp_atom.atom_id'].index('O3P')]='-1';p.write_text(_render(v,'ZZZ'))
    if defect=='bridged_leaving':
        for p in (s,c):
            v=component_values(p,'ZZZ');v['_chem_comp_bond.atom_id_2'][v['_chem_comp_bond.atom_id_2'].index('leaveH')]="C5'";p.write_text(_render(v,'ZZZ'))
    if defect=='retained_leaving':
        text=m.read_text();line=next(l for l in text.splitlines() if l.startswith('HETATM') and l[17:20]=='ZZZ');m.write_text(text+line[:12]+' O3P'+line[16:]+'\n')
    q=None if defect=='no_qualification' else qualification(s,c,'ZZZ')
    with pytest.raises(ValueError):prepare_linked_component(s,c,m,contexts,tmp_path/'out',code='ZZZ',native_qualification=q,
        bond_representation_policy=POLICY if q else None,phosphate_atom_policy=policy)
    assert not (tmp_path/'out').exists()
