"""Native representation changes must not disable active chemistry checks."""
from copy import deepcopy
import math
import pytest
from tests.test_cif_candidate_usability import native_case
from tests.test_cif_stereochemistry_audit import write


@pytest.mark.parametrize('change,accepted',[(0.,True),(2e-15,True),(2e-7,False),(float('nan'),False)])
def test_native_cartesian_roundtrip_is_bounded_and_finite(tmp_path,change,accepted):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    s,c,m,n=native_case(tmp_path)
    n['geometry']['sites_cart_exact']=deepcopy(n['geometry']['sites_cart_exact']);n['geometry']['sites_cart_exact'][0][0]+=change
    q=qualify_candidate_native(s,c,m,'Q17',n)
    assert q['native_usable'] is accepted
    assert q['checks']['native_coordinate_roundtrip'] is accepted
    if accepted:assert 'native_coordinate_roundtrip' in q['evidence']


def constant_case(tmp_path):
    from nasolve.cif_stereochemistry_audit import _values
    from nasolve.cif_terminal_qualification import _rows
    s,c,m,n=native_case(tmp_path);v=_values(s,'Q17');t='_chem_comp_tor.'
    row=dict(comp_id='Q17',id='ARBITRARY_CONSTANT',atom_id_1='O',atom_id_2='CTR',atom_id_3='N',atom_id_4='C',value_angle='37',value_angle_esd='0',period='0')
    v.update({t+k:[x] for k,x in row.items()});write(s,v);write(c,v)
    n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions']=_rows(v,'_chem_comp_tor')
    names=[a['atom_id'] for a in n['atoms']];ns=['O','CTR','N','C']
    proxy={'i_seqs':[names.index(a) for a in ns],'atoms':['A:1:Q17:'+a for a in ns],
        'angle_ideal':37.,'weight':0.,'periodicity':0,'origin_id':0}
    n['geometry']['proxy_details']['const_dihedral']=[proxy];n['geometry']['proxy_counts']['const_dihedral']=1
    return s,c,m,n


@pytest.mark.parametrize('order',[(0,1,2,3),(3,1,2,0),(0,2,1,3),(3,2,1,0)])
def test_declared_zero_esd_constant_rows_survive_native_signed_permutations(tmp_path,order):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    s,c,m,n=constant_case(tmp_path);r=n['geometry']['proxy_details']['const_dihedral'][0]
    for k in ['i_seqs','atoms']:r[k]=[r[k][i] for i in order]
    if order in [(3,1,2,0),(0,2,1,3)]:r['angle_ideal']*=-1
    q=qualify_candidate_native(s,c,m,'Q17',n)
    assert q['native_usable'],q['checks']
    assert len(q['evidence']['native_constant_torsions'])==1


@pytest.mark.parametrize('defect',['weight','period','target','missing','ordinary_zero','bad_declaration'])
def test_zero_constant_exception_requires_exact_declared_zero_semantics(tmp_path,defect):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    from nasolve.cif_stereochemistry_audit import _values
    s,c,m,n=constant_case(tmp_path);g=n['geometry'];r=g['proxy_details']['const_dihedral'][0]
    if defect=='weight':r['weight']=1.
    if defect=='period':r['periodicity']=1
    if defect=='target':r['angle_ideal']+=1
    if defect=='missing':g['proxy_details']['const_dihedral']=[];g['proxy_counts']['const_dihedral']=0
    if defect=='ordinary_zero':
        g['proxy_details']['bond_simple'][0]['weight']=0
    if defect=='bad_declaration':
        v=_values(c,'Q17');v['_chem_comp_tor.period']=['1'];write(s,v);write(c,v)
        n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions'][0]['period']='1'
    assert not qualify_candidate_native(s,c,m,'Q17',n)['native_usable']


@pytest.mark.parametrize('order',[(3,1,2,0),(0,2,1,3),(3,2,1,0)])
def test_fixed_signature_normalizes_native_signed_torsion_order(tmp_path,order):
    from nasolve.cif_candidate_usability import covalent_proxy_signature
    *_,a=constant_case(tmp_path);b=deepcopy(a);r=b['geometry']['proxy_details']['const_dihedral'][0]
    for k in ['i_seqs','atoms']:r[k]=[r[k][i] for i in order]
    if order!=(3,2,1,0):r['angle_ideal']*=-1
    assert covalent_proxy_signature(a)==covalent_proxy_signature(b)


@pytest.mark.parametrize('period,accepted',[(1,True),(1.5,False)])
def test_active_torsion_period_is_not_silently_truncated(tmp_path,period,accepted):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    from nasolve.cif_stereochemistry_audit import _values
    s,c,m,n=constant_case(tmp_path);v=_values(c,'Q17');v['_chem_comp_tor.value_angle_esd']=['10'];v['_chem_comp_tor.period']=['1'];write(s,v);write(c,v)
    row=n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions'][0];row.update(value_angle_esd='10',period='1')
    g=n['geometry'];proxy=g['proxy_details']['const_dihedral'].pop();proxy.update(weight=.01,periodicity=period)
    g['proxy_counts']['const_dihedral']=0;g['proxy_details']['dihedral']=[proxy];g['proxy_counts']['dihedral']=1
    assert qualify_candidate_native(s,c,m,'Q17',n)['native_usable'] is accepted
