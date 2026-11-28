"""Hydrogen inventory is evidence, not a protonation or alias permission."""
from copy import deepcopy
import pytest


def example():
    source={'C':'C','N':'N','O':'O','H1':'H','H2':'H','HN':'H'}
    edges=[('C','N'),('C','O'),('C','H1'),('C','H2'),('N','HN')]
    target={'atoms':[{'atom_id':a,'type_symbol':e} for a,e in source.items()],
            'bonds':[{'atom_id_1':a,'atom_id_2':b} for a,b in edges]}
    return source,edges,target,{'C':'C','N':'N','O':'O'}


def compare(args):
    from nasolve.cif_native_hydrogens import compare_hydrogen_inventory
    return compare_hydrogen_inventory(*args)


def rename(target,old,new):
    for atom in target['atoms']:
        if atom['atom_id']==old:atom['atom_id']=new
    for bond in target['bonds']:
        for key in ('atom_id_1','atom_id_2'):
            if bond[key]==old:bond[key]=new


def test_equal_counts_with_different_labels_are_not_inferred_aliases():
    args=example();rename(args[2],'C','CX');args[3]['C']='CX'
    rename(args[2],'H1','HX');before=deepcopy(args);r=compare(args)
    assert r['inventory_status']=='MATCH' and r['name_status']=='DIFFERENT'
    assert r['groups'][0]['source_hydrogens']==['H1','H2']
    assert r['groups'][0]['native_hydrogens']==['H2','HX']
    assert r['chemical_authority']=='NOT_GRANTED' and not r['hydrogen_aliases_inferred']
    assert args==before


@pytest.mark.parametrize('change',['removed','added','isotope','moved','same_count_swap'])
def test_hydrogen_state_differences_remain_visible(change):
    args=example();target=args[2]
    if change=='removed':
        target['atoms']=[a for a in target['atoms'] if a['atom_id']!='H1']
        target['bonds']=[b for b in target['bonds'] if 'H1' not in b.values()]
    if change=='added':
        target['atoms'].append({'atom_id':'HO','type_symbol':'H'})
        target['bonds'].append({'atom_id_1':'O','atom_id_2':'HO'})
    if change=='isotope':next(a for a in target['atoms'] if a['atom_id']=='H1')['type_symbol']='D'
    if change in {'moved','same_count_swap'}:
        next(b for b in target['bonds'] if b['atom_id_2']=='H1')['atom_id_1']='N'
        if change=='same_count_swap':next(b for b in target['bonds'] if b['atom_id_2']=='HN')['atom_id_1']='C'
    r=compare(args);assert r['status']=='RECORDED' and r['inventory_status']=='DIFFERENT'
    if change=='same_count_swap':
        assert all(g['count_status']=='MATCH' for g in r['groups'])
        assert len(r['same_name_attachment_changes'])==2


@pytest.mark.parametrize('defect',['missing_bonds','missing_atoms','orphan','multiple_parents','hydrogen_parent','duplicate_bond','unknown_endpoint','self_bond','unbound_source','unbound_native','wrong_heavy_element'])
def test_incomplete_or_ambiguous_inventory_cannot_look_equal(defect):
    args=example();target=args[2]
    if defect=='missing_bonds':target.pop('bonds')
    elif defect=='missing_atoms':target.pop('atoms')
    elif defect=='orphan':target['bonds']=[b for b in target['bonds'] if 'H1' not in b.values()]
    elif defect=='multiple_parents':target['bonds'].append({'atom_id_1':'N','atom_id_2':'H1'})
    elif defect=='hydrogen_parent':next(b for b in target['bonds'] if b['atom_id_2']=='H1')['atom_id_1']='HN'
    elif defect=='duplicate_bond':target['bonds'].append(deepcopy(target['bonds'][0]))
    elif defect=='unknown_endpoint':target['bonds'][0]['atom_id_1']='ABSENT'
    elif defect=='self_bond':target['bonds'][0]['atom_id_1']=target['bonds'][0]['atom_id_2']
    elif defect=='unbound_source':args[3].pop('O')
    elif defect=='unbound_native':target['atoms'].append({'atom_id':'EXTRA','type_symbol':'C'})
    elif defect=='wrong_heavy_element':target['atoms'][0]['type_symbol']='N'
    r=compare(args);assert r['status']=='UNSUPPORTED' and r['inventory_status']=='NOT_ASSESSED'


def test_source_hydrogen_ambiguity_is_also_unassessed():
    args=example();args[1].append(('O','H1'))
    assert compare(args)['status']=='UNSUPPORTED'


def test_order_does_not_change_inventory():
    args=example();expected=compare(args);args[1].reverse();args[2]['atoms'].reverse();args[2]['bonds'].reverse()
    assert compare(args)==expected


def test_explicitly_observed_hydrogen_alias_can_be_reported_without_inference():
    args=example();rename(args[2],'H1','HX');args[3]['H1']='HX'
    r=compare(args);assert r['inventory_status']==r['name_status']=='MATCH'
    assert not r['hydrogen_aliases_inferred']


def test_alias_cannot_collapse_distinct_hydrogens():
    args=example();args[3]['H1']='H2'
    with pytest.raises(ValueError,match='collapse'):compare(args)


def test_public_reader_exposes_inventory_without_promoting_label_difference(tmp_path):
    from tests.test_cif_native_atom_mapping import mapped_fixture
    from tests.test_cif_attachment_native import audit,rebind
    paths=mapped_fixture(tmp_path)
    def change(receipt):
        d=receipt['native_validation']['monomer_mappings']['rows'][0]['metadata']['effective_definition']
        atom=next(a['atom_id'] for a in d['atoms'] if a['type_symbol']=='H')
        rename(d,atom,'UNMODELLED_H_ALIAS')
    rebind(paths[1],change);r=audit(paths);h=r['mapped_definitions']['A:1']['hydrogen_inventory']
    assert h['inventory_status']=='MATCH' and h['name_status']=='DIFFERENT'
    assert r['mapped_definition_status']=='REVIEW' and r['status']=='REVIEW'


def test_public_reader_preserves_charge_review_when_hydrogen_counts_match(tmp_path):
    from tests.test_cif_native_atom_mapping import mapped_fixture
    from tests.test_cif_attachment_native import audit,rebind
    paths=mapped_fixture(tmp_path)
    def change(receipt):receipt['native_validation']['monomer_mappings']['rows'][0]['metadata']['effective_definition']['atoms'][0]['charge']=3
    rebind(paths[1],change);r=audit(paths)
    assert r['mapped_definitions']['A:1']['hydrogen_inventory']['inventory_status']=='MATCH'
    assert r['mapped_definitions']['A:1']['formal_charge_status']=='CONTRADICTION'
    assert r['mapped_definition_status']=='REVIEW'


def test_legacy_capture_has_no_new_hydrogen_inventory(tmp_path):
    from tests.test_cif_attachment_native import fixture,audit
    r=audit(fixture(tmp_path));assert 'mapped_definitions' not in r


def test_text_cli_reports_inventory_coverage(tmp_path,capsys):
    from tests.test_cif_native_atom_mapping import mapped_fixture
    from nasolve.cli import main
    paths=mapped_fixture(tmp_path)
    assert main(['cif-doctor','link-native',str(paths[0]),'--native-receipt',str(paths[1])])==2
    assert 'Hydrogen inventories: 2 recorded' in capsys.readouterr().out


def test_text_cli_does_not_report_zero_unavailable_when_mapping_is_missing(tmp_path,capsys):
    from tests.test_cif_native_atom_mapping import mapped_fixture
    from tests.test_cif_attachment_native import rebind
    from nasolve.cli import main
    paths=mapped_fixture(tmp_path)
    def change(receipt):
        receipt['native_validation']['monomer_mappings']['rows'][0]['atom_name_mapping']={'status':'UNSUPPORTED','missing_fields':['expected_atoms']}
    rebind(paths[1],change)
    assert main(['cif-doctor','link-native',str(paths[0]),'--native-receipt',str(paths[1])])==2
    assert 'Hydrogen inventories: not assessed' in capsys.readouterr().out
