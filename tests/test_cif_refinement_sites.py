"""Compact observation preserves native objects, exact scope and full precision."""
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from nasolve.cif_refinement_sites import observe_monomers, validate_snapshot, unavailable, validate_sites
from tests.test_cif_refinement_output import Atom

SITES=[dict(site='A:1',component='Q17')]


def model():
    atoms=[]
    for i,(name,xyz) in enumerate(zip(['L','X','Y','R','U'],[(-1.4,0.,0.),(0.,0.,0.),(1.2,0.,0.),(2.6,.312345,0.),(8.,9.,10.)])):
        a=Atom(str(i));a.i_seq=i;a.name=name;a.xyz=xyz
        a.fetch_labels=lambda i=i:NS(model_id='',chain_id='A',resseq='1' if i<4 else '2',icode='',resname='Q17',altloc='')
        atoms.append(a)
    class Mapping:
        def __init__(self,selected):
            self.pdb_residue=NS(atoms=lambda:selected)
            self.monomer=NS(bond_list=[NS(atom_id_1='X',atom_id_2='Y',type='triple',value_dist=1.2,value_dist_esd=.02)])
            self.calls=0
        def summary(self):
            self.calls+=1
            self.result=NS(expected_atoms=list(self.pdb_residue.atoms()),unexpected_atoms=[])
            return self.result
    selected=Mapping(atoms[:4]);unrelated=Mapping(atoms[4:])
    bond=NS(i_seqs=[1,2],distance_ideal=1.2,weight=2500.,origin_id=0)
    cross=NS(i_seqs=[3,4],distance_ideal=1.4,weight=2500.,origin_id=0)
    pairs=NS(bond_proxies=NS(simple=[bond,cross],asu=[]))
    geo=NS(pair_proxies=lambda **kw:pairs,angle_proxies=[NS(i_seqs=[0,1,2],angle_ideal=180.,weight=1/9,origin_id=0),NS(i_seqs=[1,2,3],angle_ideal=180.,weight=1/9,origin_id=0)],
        dihedral_proxies=[],const_dihedral_proxies=[],chirality_proxies=[],planarity_proxies=[],parallelity_proxies=[])
    hierarchy=NS(atoms=lambda:atoms)
    m=NS(get_hierarchy=lambda:hierarchy,get_sites_cart=lambda:[a.xyz for a in atoms],restraints_manager=NS(geometry=geo))
    return m,Mapping,selected,unrelated,atoms


def capture():
    m,klass,selected,unrelated,atoms=model()
    with observe_monomers(klass,SITES) as observer:
        m._all_monomer_mappings=[selected.summary(),unrelated.summary()]
        result=observer.snapshot(m)
    return result,[a.id_str() for a in atoms]


def test_original_summary_and_model_are_preserved_with_only_selected_local_restraints():
    m,klass,selected,unrelated,atoms=model();original=klass.summary
    with observe_monomers(klass,SITES) as observer:
        summary=selected.summary();m._all_monomer_mappings=[summary,unrelated.summary()]
        assert summary is selected.result and selected.calls==unrelated.calls==1
        assert len(observer.mappings)==1
        result=observer.snapshot(m)
        assert result['atoms'][3]['xyz'][1]==.312345
        assert result['geometry']['full_proxy_counts']['bond_simple']==2
        assert len(result['geometry']['proxy_details']['bond_simple'])==1
        assert result['full_atom_count']==5 and len(result['atoms'])==4
        assert validate_snapshot(result,SITES,[a.id_str() for a in atoms]) is result
    assert klass.summary is original and selected.calls==unrelated.calls==1


@pytest.mark.parametrize('failure',['raise','foreign_binding','equal_summary','lost_summary','changed_coordinates'])
def test_binding_or_identity_failure_cannot_be_borrowed_from_another_model(failure):
    m,klass,selected,_,atoms=model();original=klass.summary
    with pytest.raises((ValueError,RuntimeError)):
        with observe_monomers(klass,SITES) as observer:
            m._all_monomer_mappings=[selected.summary()]
            if failure=='raise':raise RuntimeError('interruption')
            if failure=='foreign_binding':klass.summary=lambda x:None
            elif failure=='equal_summary':m._all_monomer_mappings=[deepcopy(m._all_monomer_mappings[0])]
            elif failure=='lost_summary':m._all_monomer_mappings=[]
            else:m.get_sites_cart=lambda:[(9.,9.,9.)]*len(atoms)
            observer.snapshot(m)
    assert klass.summary is original


def test_optional_observation_failure_does_not_change_the_native_summary():
    m,klass,selected,_,_=model()
    original=klass.summary
    with observe_monomers(klass,SITES) as observer:
        selected.pdb_residue=NS(atoms=lambda:[])  # A synthetic unsupported observer interface.
        expected=selected.summary()
        assert expected is selected.result
        m._all_monomer_mappings=[expected]
        with pytest.raises(ValueError):observer.snapshot(m)
    assert klass.summary is original


@pytest.mark.parametrize('defect',['index','label','coordinate','scope','state','definition','count','proxy_atom','cross_site','nonfinite','extra_field'])
def test_saved_observation_cannot_change_membership_or_claim_another_state(defect):
    record,labels=capture();expected_state=record['model_state_sha256']
    if defect=='index':record['atoms'][0]['i_seq']=4
    elif defect=='label':record['atoms'][0]['label']='other'
    elif defect=='coordinate':record['atoms'][0]['xyz']=[0.,0.]
    elif defect=='scope':record['sites'][0]['component']='PDU'
    elif defect=='state':record['model_state_sha256']='f'*64
    elif defect=='definition':record['monomer_mappings']['rows']=[]
    elif defect=='count':record['geometry']['full_proxy_counts']['angle']=0
    elif defect=='proxy_atom':record['geometry']['proxy_details']['angle'][0]['atoms'][0]='wrong'
    elif defect=='cross_site':record['geometry']['proxy_details']['bond_simple'][0]['i_seqs']=[1,4]
    elif defect=='nonfinite':record['geometry']['proxy_details']['bond_simple'][0]['weight']=float('nan')
    else:record['actual_refinement_approved']=True
    with pytest.raises(ValueError):validate_snapshot(record,[dict(site='A:1',component='Q17')],labels,model_state=expected_state)


@pytest.mark.parametrize('scope',[None,{},[dict(site='A:01',component='Q17')],[dict(site='A:-0',component='Q17')],SITES+SITES])
def test_selected_scope_is_explicit_and_canonical(scope):
    with pytest.raises(ValueError):validate_sites(scope)


def test_unavailable_observation_cannot_be_promoted_to_native_approval():
    record=unavailable(SITES,'Required final definition was not available')
    assert validate_snapshot(record,SITES,[])['status']=='UNASSESSED'
    record['scientific_approval']='PASS'
    with pytest.raises(ValueError):validate_snapshot(record,SITES,[])


def test_observation_scope_is_a_copy_not_mutable_caller_state():
    scope=deepcopy(SITES);m,klass,selected,_,atoms=model()
    with observe_monomers(klass,scope) as observer:
        scope[0]['component']='PDU'
        m._all_monomer_mappings=[selected.summary()]
        record=observer.snapshot(m)
        assert record['sites']==SITES
        record['sites'][0]['component']='PDU'
        assert observer.snapshot(m)['sites']==SITES
    missing=unavailable(SITES,'not available');missing['sites'][0]['component']='PDU'
    assert SITES==[dict(site='A:1',component='Q17')]
