"""Numerical attribution cannot turn changed or unbound chemistry into approval."""
from copy import deepcopy
import math
import pytest
from tests.test_cif_linked_linear_torsion import fixture


def case(tmp_path):
    before, after, source, candidate = fixture(tmp_path)
    for native in (before, after):
        native['geometry']['sites_cart_exact'] = [[float(i), .2, .3] for i in range(8)]
    proxy = deepcopy(before['geometry']['proxy_details']['dihedral'][0])
    gradient = [float(i)/10 for i in range(12)]
    reference = {'proxy_kind':'dihedral', 'proxy':proxy,
                 'sites_cart':[before['geometry']['sites_cart_exact'][i] for i in proxy['i_seqs']],
                 'evaluations':[dict(single_target=2., accumulated_target=2.,
                                     single_gradient=gradient, accumulated_gradient=gradient)]*2}
    for native, original in [(before, True), (after, False)]:
        g = ([x+1 for x in gradient]+[1.]*12) if original else [1.]*24
        snapshot = dict(target=7. if original else 5., gradient=g, gradient_norm=math.sqrt(sum(x*x for x in g)),
                        terms={'bond_residual_sum':3., 'dihedral_residual_sum':4. if original else 2.},
                        proxy_counts={'n_bond_proxies':10, 'n_dihedral_proxies':2 if original else 1})
        native['energy_inventory'] = dict(policy_id='cif-fixed-native-usability-energy-v1', status='RECORDED',
            normalization=False, evaluation_calls=2, snapshots=[deepcopy(snapshot),deepcopy(snapshot)],
            installed_sources=[dict(module='cctbx.geometry_restraints.'+name,sha256='a'*64,historical_path='/old/'+name)
                               for name in ['flags','energies','manager']])
    return before, after, source, candidate, [reference]


def qualify(args):
    from nasolve.cif_linked_torsion_energy import qualify_linked_torsion_energy
    before, after, source, candidate, references = args
    return qualify_linked_torsion_energy(before, after, source, 'Q17', candidate, references)


def test_exact_delta_is_attributed_without_adoption_or_derivative_claim(tmp_path):
    args=case(tmp_path);saved=deepcopy(args[:2]);refs=deepcopy(args[-1]);data=[p.read_bytes() for p in args[2:4]]
    result=qualify(args)
    assert result['numerical_checks_pass'] and result['removed_proxy_count']==1
    assert result['removed_target']==2. and result['target_delta']==2.
    assert result['derivative_qualification']=='NOT_RUN' and result['automatic_adoption'] is False
    assert result['scientific_approval']=='NOT_RUN' and result['optimization']=='NOT_RUN'
    assert args[:2]==saved and args[-1]==refs and [p.read_bytes() for p in args[2:4]]==data


@pytest.mark.parametrize('defect',['bond','count','term_set','total','gradient','repeat_term','repeat_count','reference_target','reference_gradient','reference_repeat'])
def test_unexplained_or_inconsistent_numerical_changes_fail(tmp_path,defect):
    args=case(tmp_path);snap=args[1]['energy_inventory']['snapshots'];ref=args[-1][0]
    if defect=='bond':
        for s in snap:s['terms']['bond_residual_sum']+=.5;s['terms']['dihedral_residual_sum']-=.5
    if defect=='count':
        for s in snap:s['proxy_counts']['n_bond_proxies']+=1
    if defect=='term_set':
        for s in snap:s['terms']['future_residual_sum']=0.
    if defect=='total':
        for s in snap:s['target']+=1
    if defect=='gradient':
        for s in snap:s['gradient'][20]+=.5;s['gradient_norm']=math.sqrt(sum(x*x for x in s['gradient']))
    if defect=='repeat_term':snap[1]['terms']['bond_residual_sum']+=1
    if defect=='repeat_count':snap[1]['proxy_counts']['n_bond_proxies']+=1
    if defect=='reference_target':
        ref['evaluations']=deepcopy(ref['evaluations'])
        for e in ref['evaluations']:e['single_target']=e['accumulated_target']=1.
    if defect=='reference_gradient':
        ref['evaluations']=deepcopy(ref['evaluations'])
        for e in ref['evaluations']:e['single_gradient']=e['accumulated_gradient']=[0.]*12
    if defect=='reference_repeat':
        ref['evaluations']=deepcopy(ref['evaluations']);ref['evaluations'][1]['single_target']=1.
    assert not qualify(args)['numerical_checks_pass']


@pytest.mark.parametrize('defect',['chemistry','coordinates','missing','duplicate','proxy','reference_coordinates','normalization','nonfinite','boolean','sources','extra_field'])
def test_unsupported_or_unbound_evidence_refuses(tmp_path,defect):
    args=case(tmp_path);e=args[1]['energy_inventory'];ref=args[-1][0]
    if defect=='chemistry':args[1]['restraint_policy']['secondary_structure_enabled']=True
    if defect=='coordinates':args[1]['geometry']['sites_cart_exact'][0][0]=99.
    if defect=='missing':args[-1].clear()
    if defect=='duplicate':args[-1].append(deepcopy(ref))
    if defect=='proxy':ref['proxy']['weight']=1.
    if defect=='reference_coordinates':ref['sites_cart'][0]=[99.,0.,0.]
    if defect=='normalization':e['normalization']=True
    if defect=='nonfinite':ref['evaluations'][0]['single_gradient'][0]=float('nan')
    if defect=='boolean':e['snapshots'][0]['proxy_counts']['n_bond_proxies']=True
    if defect=='sources':e['installed_sources'][0]['sha256']='b'*64
    if defect=='extra_field':e['snapshots'][0]['new_category']=[]
    with pytest.raises(ValueError):qualify(args)


def test_reversed_scattered_indices_are_scattered_by_identity(tmp_path):
    args=case(tmp_path);before,after,_,_,refs=args
    # Reorder all literal indices while retaining each residue's atom names.
    mapping={i:(i*3)%8 for i in range(8)}
    for native in (before,after):
        for atom in native['atoms']:atom['i_seq']=mapping[atom['i_seq']]
        for p in native['geometry']['proxy_details']['dihedral']:p['i_seqs']=[mapping[i] for i in p['i_seqs']]
        for snap in native['energy_inventory']['snapshots']:
            old=list(snap['gradient'])
            for i,j in mapping.items():snap['gradient'][3*j:3*j+3]=old[3*i:3*i+3]
    p=before['geometry']['proxy_details']['dihedral'][0];p['i_seqs'].reverse()
    refs[0]['proxy']=deepcopy(p);refs[0]['sites_cart']=[before['geometry']['sites_cart_exact'][i] for i in p['i_seqs']]
    for e in refs[0]['evaluations']:
        g=[float(i)/10 for i in range(12)]
        e['single_gradient']=e['accumulated_gradient']=[x for i in reversed(range(4)) for x in g[3*i:3*i+3]]
    assert qualify(args)['numerical_checks_pass']


def test_relocation_needs_no_historical_sdk_or_source_path(tmp_path):
    import shutil
    old=tmp_path/'old';old.mkdir();args=case(old);new=tmp_path/'new';shutil.move(old,new)
    args=(args[0],args[1],new/args[2].name,new/args[3].name,args[4])
    assert not old.exists() and qualify(args)['numerical_checks_pass']
