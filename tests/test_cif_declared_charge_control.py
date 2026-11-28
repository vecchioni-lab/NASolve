"""Source-declared charge population is separate from raw reader acceptance."""
from copy import deepcopy
from types import SimpleNamespace
import pytest


class Bond(list):
    def __init__(self,atoms,order):super().__init__(atoms);self.order=order


class Molecule(list):
    charge=0
    def GetOriginalFormat(self):return self.format


def fixture(code='Q17'):
    m=Molecule([SimpleNamespace(name=n,symbol=e,charge=0,xyz=SimpleNamespace(x=x,y=0.,z=0.),chiral='',volume_sign=s)
        for n,e,x,s in [(' P  ','P',0.,'both'),('Oa','O',1.,None),('Ob','O',-1.,None)]])
    m.format='CIF';m.charge=0;m.bonds=[Bond([m[0],m[1]],2),Bond([m[0],m[2]],1)]
    expected={'component':code,'dialect':'MONOMER_LIBRARY_CIF','elements':{'P':'P','Oa':'O','Ob':'O'},
        'charges':{'P':0,'Oa':0,'Ob':-1},'coordinates':{'P':[0.,0.,0.],'Oa':[1.,0.,0.],'Ob':[-1.,0.,0.]},
        'bonds':[{'atoms':['Oa','P'],'order':2},{'atoms':['Ob','P'],'order':1}]}
    return m,expected


@pytest.mark.parametrize('code',['Q17','R29'])
def test_population_copies_exact_source_charges_by_identity_and_preserves_other_fields(code):
    from nasolve.cif_declared_charge_control import control_declared_charges,native_inventory
    m,e=fixture(code);m.reverse();before=native_inventory(m)
    r=control_declared_charges(m,e)
    assert r['status']=='DECLARED_CHARGE_CONTROL_PASS' and r['action']=='POPULATED_FROM_EXPLICIT_SOURCE'
    assert r['before']==before and r['after']==native_inventory(m)
    assert r['changed_atoms']==['Ob'] and m.charge==-1
    assert all(r['checks'].values()) and m[0].name=='Ob'
    assert r['after']['atoms'][2]['native_volume_sign']=='both'


@pytest.mark.parametrize('dialect',['MONOMER_LIBRARY_CIF','CHEMICAL_COMPONENTS_CIF'])
def test_already_preserved_charge_control_does_not_rewrite_atoms(dialect):
    from nasolve.cif_declared_charge_control import control_declared_charges,native_inventory
    m,e=fixture();e['dialect']=dialect;m.format='CIF' if dialect=='MONOMER_LIBRARY_CIF' else 'CHEMICAL COMPONENTS'
    m[2].charge=-1;m.charge=-1;before=native_inventory(m)
    r=control_declared_charges(m,e)
    assert r['status']=='DECLARED_CHARGE_CONTROL_PASS' and r['action']=='ALREADY_PRESERVED'
    assert r['changed_atoms']==[] and native_inventory(m)==before


@pytest.mark.parametrize('defect',['source_missing_charge','fractional','bool','large','charge_alias_type','native_conflict',
                                  'partial_native','molecule_total','ccd_missing_charge','route','atom','duplicate','element',
                                  'bond','duplicate_bond','coordinates','nonfinite'])
def test_ambiguous_charge_or_changed_graph_is_blocked_before_any_assignment(defect):
    from nasolve.cif_declared_charge_control import control_declared_charges,native_inventory
    m,e=fixture()
    if defect=='source_missing_charge':e['charges'].pop('Ob')
    if defect=='fractional':e['charges']['Ob']=-.5
    if defect=='bool':e['charges']['Ob']=True
    if defect=='large':e['charges']['Ob']=-5
    if defect=='charge_alias_type':e['charges']['Ob']='-1'
    if defect=='native_conflict':m[2].charge=1;m.charge=1
    if defect=='partial_native':m[0].charge=1;m.charge=1
    if defect=='molecule_total':m.charge=2
    if defect=='ccd_missing_charge':m.format='CHEMICAL COMPONENTS';e['dialect']='CHEMICAL_COMPONENTS_CIF'
    if defect=='route':m.format='PDB'
    if defect=='atom':m[2].name='OTHER'
    if defect=='duplicate':m[2].name='Oa'
    if defect=='element':m[2].symbol='N'
    if defect=='bond':m.bonds[0].order=1
    if defect=='duplicate_bond':m.bonds.append(m.bonds[0])
    if defect=='coordinates':m[2].xyz.x=2.
    if defect=='nonfinite':e['coordinates']['Ob'][0]=float('inf')
    before=native_inventory(m);r=control_declared_charges(m,e)
    assert r['status']=='BLOCKED' and native_inventory(m)==before


def test_unexpected_effects_of_a_native_charge_setter_fail_control():
    from nasolve.cif_declared_charge_control import control_declared_charges
    m,e=fixture()
    class BadAtom(SimpleNamespace):
        def __setattr__(self,name,value):
            super().__setattr__(name,value)
            if name=='charge' and value==-1:self.xyz.x+=.1
    m[2]=BadAtom(**vars(m[2]));m.bonds[1][1]=m[2]
    r=control_declared_charges(m,e)
    assert r['status']=='REVIEW' and r['checks']['other_native_fields_preserved'] is False
