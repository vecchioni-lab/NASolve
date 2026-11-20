"""Typed coordination never masks an unrequested native covalent interaction."""
from copy import deepcopy
from hashlib import sha256

import pytest

from nasolve.cif_topology_gate import review_native_topology
from nasolve.metal import Recipe, RecipeError
from nasolve.metal.binding import Atom, AtomKey, ModelSnapshot
from nasolve.metal.preview import preview
from tests.test_cif_topology_gate import paired, sync
from tests.test_metal_materialize import atom


def fixture(tmp_path, *, cluster=False):
    n, payload, expected, policy, phil = paired(tmp_path)
    count = len(n['atoms'])
    for a in n['atoms']:
        for field in ('model_id','icode','altloc'):
            a['identity'].setdefault(field,'')
    payload = payload.removesuffix(b'END\n') + atom(count+1, 'HG', 'HG', 'M', 1, (1, 2, 3), 'HG').encode() + b'END\n'
    n['atoms'].append(dict(i_seq=count, atom_id='HG', label='pdb="  HG  HG M   1 "',
        element='HG', xyz=[1., 2., 3.], occupancy=1., identity=dict(model_id='', chain_id='M',
        resseq='   1', resname=' HG', icode='', altloc='')))
    if cluster:
        second=deepcopy(n['atoms'][-1]);second.update(i_seq=count+1,atom_id='HG2',label='pdb=" HG2  HG M   1 "',xyz=[2.,2.,3.])
        n['atoms'].append(second)
        payload=payload.removesuffix(b'END\n')+atom(count+2,'HG2','HG','M',1,(2,2,3),'HG').encode()+b'END\n'
    n['atom_count'] = len(n['atoms'])
    n['geometry']['sites_cart_exact'] = [a['xyz'] for a in n['atoms']]
    keys = [AtomKey(model_id='1', chain_id=a['identity']['chain_id'], residue_id=a['identity']['resseq'].strip(),
        component_id=a['identity']['resname'].strip(), atom_name=a['atom_id']) for a in n['atoms']]
    doc = dict(kind='metal-restraint-recipe', schema_version=1, id='typed-contact', revision=1,
        name='Synthetic explicit coordination', nodes=[dict(id='m', kind='metal', element='Hg'),
            dict(id='a', kind='atom'), dict(id='b', kind='atom')],
        sets=[dict(id='s', name='Contacts', enabled=True)], restraints=[])
    for name, nodes, kind, target, sigma, unit in [
            ('ma', ['m','a'], 'distance', 2.1, .02, 'angstrom'),
            ('mb', ['m','b'], 'distance', 2.1, .02, 'angstrom'),
            ('angle', ['a','m','b'], 'angle', 180., 2., 'degree')]:
        doc['restraints'].append(dict(id=name, nodes=nodes, kind=kind, target=target,
            sigma=sigma, unit=unit, enabled=True, set_id='s', source=dict(kind='user', note='Control')))
    if cluster:
        doc['nodes'].append(dict(id='m2',kind='metal',element='Hg'))
        term=deepcopy(doc['restraints'][0]);term.update(id='mm',nodes=['m','m2'])
        doc['restraints'].append(term)
    snapshot = ModelSnapshot(tuple(Atom(k,a['element'].title(),tuple(a['xyz'])) for k,a in zip(keys,n['atoms'])),
        sha256(payload).hexdigest(), 'synthetic')
    bindings=dict(m=keys[count],a=keys[0],b=keys[count-1])
    if cluster:bindings['m2']=keys[count+1]
    p = preview(Recipe(doc), model=snapshot, residue_slots={}, atom_bindings=bindings)
    for other in ([0,count-1,count+1] if cluster else [0,count-1]):
        indices = [count, other]
        selections = []
        for i in indices:
            k = keys[i]
            selections.append(f"chain {k.chain_id} and resid {k.residue_id} and resname {k.component_id} and name {k.atom_name} and altloc ' ' and segid '    '")
        q = dict(kind='bond', action='add', i_seqs=indices, atoms=[n['atoms'][i]['label'] for i in indices],
                 selections=selections, distance_ideal=2.1, weight=2500.)
        n['geometry']['custom_proxy_requests'].append(q)
        n['geometry']['proxy_details']['bond_simple'].append(dict(
            i_seqs=indices, atoms=q['atoms'][:], distance_ideal=2.1, weight=2500., origin_id=41, symmetry_operation=None))
    sync(n)
    return n,payload,expected,policy,phil,p


def declared(n, payload, p):
    from nasolve.metal.coordination_topology import describe_coordination_bonds
    return describe_coordination_bonds(p,n,payload,edit_origin_id=41)


def review(f, bonds):
    n,payload,expected,policy,phil,_ = f
    return review_native_topology(n,payload,expected,na_policy=policy,na_phil=phil,coordination_bonds=bonds)


def test_metal_contacts_and_nar_remain_distinct_from_covalent_links(tmp_path):
    f=fixture(tmp_path);n,payload,expected,policy,phil,p=f;before=deepcopy(f)
    old=review_native_topology(n,payload,expected,na_policy=policy,na_phil=phil)
    assert old['link_status']=='REVIEW' and len(old['unexpected_links'])==2
    assert old['schema_version']==1 and 'coordination_restraints' not in old
    bonds=declared(n,payload,p);result=review(f,bonds)
    assert result['link_status']=='MATCH' and len(result['links'])==1
    assert len(result['soft_restraints'])==len(result['coordination_restraints'])==2
    assert [r['term_id'] for r in bonds]==['ma','mb']
    assert result['coordination_angles']=='NOT_ASSESSED'
    assert result['chemical_qualification']=='NOT_ESTABLISHED' and not result['automatic_adoption']
    assert f==before
    bonds[0]['request']['weight']=1.
    assert result['coordination_restraints'][0]['request']['weight']==2500.


def test_unexpected_covalent_neighbor_stays_visible_and_declared_crosslink_survives(tmp_path):
    f=fixture(tmp_path);n,payload,expected,_,_,p=f;bonds=declared(n,payload,p)
    # A distinct inter-base C--C link is not authorized by nearby Hg contacts.
    ids=[1,len(n['atoms'])-3]
    extra=dict(i_seqs=ids,atoms=[n['atoms'][i]['label'] for i in ids],
        distance_ideal=1.43,weight=2500.,origin_id=0,symmetry_operation=None)
    n['geometry']['proxy_details']['bond_simple'].append(extra);sync(n)
    result=review(f,bonds)
    assert result['link_status']=='REVIEW' and len(result['unexpected_links'])==1
    endpoints=[dict(site=a['identity']['chain_id']+':'+a['identity']['resseq'].strip(),
        component=a['identity']['resname'].strip(),atom_id=a['atom_id']) for a in [n['atoms'][i] for i in ids]]
    expected.append(dict(endpoints=endpoints))
    result=review(f,bonds)
    assert result['link_status']=='MATCH' and len(result['links'])==2


@pytest.mark.parametrize('defect', ['origin','target','weight','duplicate','missing','symmetry',
    'request','request_duplicate','conflicting_request','endpoint','role','term_id','overlap','selection','origin_collision','boolean_index'])
def test_exact_binding_cannot_hide_conflicting_contacts(tmp_path,defect):
    f=fixture(tmp_path);n,payload,e,_,_,p=f;bonds=declared(n,payload,p)
    d=n['geometry']['proxy_details']['bond_simple'];contact=d[-2]
    if defect=='origin':contact['origin_id']=0
    elif defect=='target':contact['distance_ideal']+=.01
    elif defect=='weight':contact['weight']*=2
    elif defect=='duplicate':d.append(deepcopy(contact))
    elif defect=='missing':d.pop(-2)
    elif defect=='symmetry':contact['symmetry_operation']='-x,y,z'
    elif defect=='request':n['geometry']['custom_proxy_requests'].pop(-2)
    elif defect=='request_duplicate':n['geometry']['custom_proxy_requests'].append(deepcopy(bonds[0]['request']))
    elif defect=='conflicting_request':
        extra=deepcopy(bonds[0]['request']);extra['weight']*=2
        n['geometry']['custom_proxy_requests'].append(extra)
    elif defect=='endpoint':bonds[0]['endpoints'][1][-1]='WRONG'
    elif defect=='role':bonds[0]['roles']=['atom','atom']
    elif defect=='term_id':bonds[1]['term_id']=bonds[0]['term_id']
    elif defect=='overlap':e.append(dict(endpoints=[dict(zip(('site','component','atom_id'),a)) for a in bonds[0]['endpoints']]))
    elif defect=='selection':bonds[0]['request']['selections'][0]='all'
    elif defect=='origin_collision':n['restraint_policy']['origin_ids']['hydrogen bonds']=41
    elif defect=='boolean_index':bonds[0]['request']['i_seqs'][1]=False
    sync(n)
    with pytest.raises(ValueError):review(f,bonds)


@pytest.mark.parametrize('defect',['model','preview','element','index','coordinates','segment'])
def test_recipe_projection_is_bound_to_model_and_complete_native_inventory(tmp_path,defect):
    f=fixture(tmp_path);n,payload,_,_,_,p=f
    if defect=='model':payload+=b'REMARK changed\n'
    elif defect=='preview':p['restraints'][0]['node_ids'].reverse()
    elif defect=='element':n['atoms'][-1]['element']='AG'
    elif defect=='index':n['atoms'][0]['i_seq']=False
    elif defect=='coordinates':n['atoms'][0]['xyz'][0]+=1
    elif defect=='segment':
        lines=payload.decode().splitlines();lines[0]=lines[0][:72]+'TEST'+lines[0][76:]
        payload=('\n'.join(lines)+'\n').encode();p['inputs']['model']['source_sha256']=sha256(payload).hexdigest()
    with pytest.raises((RecipeError,ValueError)):declared(n,payload,p)


def test_same_residue_cluster_contact_is_checked_without_becoming_a_covalent_link(tmp_path):
    f=fixture(tmp_path,cluster=True);n,payload,_,_,_,p=f
    bonds=declared(n,payload,p);result=review(f,bonds)
    assert result['link_status']=='MATCH' and len(result['coordination_restraints'])==3
    assert bonds[-1]['roles']==['metal','metal']
    assert bonds[-1]['endpoints'][0][:2]==bonds[-1]['endpoints'][1][:2]
    n['geometry']['proxy_details']['bond_simple'][-1]['weight']*=2;sync(n)
    with pytest.raises(ValueError,match='realization'):review(f,bonds)


def test_unclaimed_metal_neighbor_and_omitted_declaration_are_not_exempt(tmp_path):
    f=fixture(tmp_path);n,payload,_,_,_,p=f
    bonds=declared(n,payload,p)
    result=review(f,bonds[:1])
    assert result['link_status']=='REVIEW' and len(result['unexpected_links'])==1
    extra=deepcopy(n['geometry']['proxy_details']['bond_simple'][-1])
    extra['i_seqs'][1]=1;extra['atoms'][1]=n['atoms'][1]['label']
    n['geometry']['proxy_details']['bond_simple'].append(extra);sync(n)
    assert len(review(f,bonds)['unexpected_links'])==1
