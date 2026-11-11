"""Whole-plane attribution is distinct from native provenance or derivatives."""
from copy import deepcopy
import math
import pytest
from tests.test_cif_plane_native import fixture


def case(tmp_path):
    args=list(fixture(tmp_path));before,after=args[:2]
    points=[[float(i),.2,.3] for i in range(8)]
    for native in (before,after):
        native['geometry']['sites_cart_exact']=deepcopy(points)
        for a in native['atoms']:a['xyz']=deepcopy(points[a['i_seq']])
    refs={};gradients=[]
    for label,native,n,target in [('before',before,3,2.),('after',after,4,5.)]:
        proxy=deepcopy(native['geometry']['proxy_details']['planarity'][0])
        gradient=[.1*(i+1) for i in range(3*n)]
        if label=='after':gradient[:9]=[v+.25 for v in gradient[:9]]
        evaluation=dict(single_target=target,accumulated_target=target,single_gradient=gradient,accumulated_gradient=gradient)
        refs[label]=dict(proxy=proxy,sites_cart=[points[i] for i in proxy['i_seqs']],symmetry_operations=None,evaluations=[deepcopy(evaluation),deepcopy(evaluation)])
        full=[1.]*24
        for i,v in enumerate(gradient):full[i]+=v
        snapshot=dict(target=3.+target,gradient=full,gradient_norm=math.hypot(*full),
            terms=dict(bond_residual_sum=3.,dihedral_residual_sum=0.,planarity_residual_sum=target),
            proxy_counts=dict(n_bond_proxies=10,n_dihedral_proxies=0,n_planarity_proxies=2))
        native['energy_inventory']=dict(policy_id='cif-fixed-native-usability-energy-v1',status='RECORDED',normalization=False,evaluation_calls=2,
            snapshots=[deepcopy(snapshot),deepcopy(snapshot)],installed_sources=[dict(module='cctbx.geometry_restraints.'+name,sha256='a'*64,historical_path='/old/'+name) for name in ('flags','energies','manager')])
    return args,[refs]


def qualify(args,references):
    from nasolve.cif_plane_energy import qualify_linked_plane_energy
    return qualify_linked_plane_energy(*args,references)


def test_whole_groups_include_changed_forces_on_original_members(tmp_path):
    args,refs=case(tmp_path);old=deepcopy(args[:2]);original=deepcopy(refs)
    result=qualify(args,refs)
    assert result['numerical_checks_pass'] and result['changed_plane_count']==1
    assert result['whole_plane_target_delta']==result['target_delta']==3.
    assert result['gradient_delta_error_norm']<1e-14
    assert result['derivative_qualification']=='NOT_RUN' and not result['automatic_adoption']
    assert args[:2]==old and refs==original


@pytest.mark.parametrize('defect',['unaffected_term','count','term_sum','gradient','repeat','reference_target','reference_gradient','new_atom_only'])
def test_unexplained_or_partial_numerical_delta_never_qualifies(tmp_path,defect):
    args,refs=case(tmp_path);snap=args[1]['energy_inventory']['snapshots']
    if defect=='unaffected_term':
        for s in snap:s['terms']['bond_residual_sum']+=1;s['terms']['planarity_residual_sum']-=1
    elif defect=='count':
        for s in snap:s['proxy_counts']['n_bond_proxies']+=1
    elif defect=='term_sum':
        for s in snap:s['target']+=1
    elif defect=='gradient':
        for s in snap:s['gradient'][22]+=.5;s['gradient_norm']=math.hypot(*s['gradient'])
    elif defect=='repeat':snap[1]['terms']['bond_residual_sum']+=1
    else:
        for e in refs[0]['after']['evaluations']:
            if defect=='reference_target':e['single_target']=e['accumulated_target']=4.
            elif defect=='reference_gradient':e['single_gradient']=e['accumulated_gradient']=[0.]*12
            else:
                # The old members also change forces. Cancelling them by copying
                # the old gradient is not a complete new-plane evaluation.
                e['single_gradient'][:9]=refs[0]['before']['evaluations'][0]['single_gradient']
                e['accumulated_gradient']=list(e['single_gradient'])
    assert not qualify(args,refs)['numerical_checks_pass']


@pytest.mark.parametrize('defect',['missing','extra','coordinates','weights','label','symmetry','partial_symmetry',
    'missing_side','nonfinite','negative','short_gradient','extra_field','source_pins','native_change','unknown_proxy'])
def test_unbound_whole_plane_evidence_is_refused(tmp_path,defect):
    args,refs=case(tmp_path);ref=refs[0]['after']
    if defect=='missing':refs.clear()
    elif defect=='extra':refs.append(deepcopy(refs[0]))
    elif defect=='coordinates':ref['sites_cart'][0][0]+=1
    elif defect=='weights':ref['proxy']['weights'][0]+=1
    elif defect=='label':ref['proxy']['atoms'][0]='wrong'
    elif defect=='symmetry':ref['symmetry_operations']=['x+1,y,z']*4
    elif defect=='partial_symmetry':ref['symmetry_operations']=[]
    elif defect=='missing_side':refs[0].pop('before')
    elif defect=='nonfinite':ref['evaluations'][0]['single_target']=float('nan')
    elif defect=='negative':ref['evaluations'][0]['single_target']=-1.
    elif defect=='short_gradient':ref['evaluations'][0]['single_gradient'].pop()
    elif defect=='extra_field':ref['evaluations'][0]['extra']=1
    elif defect=='source_pins':args[1]['energy_inventory']['installed_sources'][0]['sha256']='0'*64
    elif defect=='native_change':args[1]['monomer_mappings']['rows'][1]['metadata']['changed']=True
    elif defect=='unknown_proxy':
        for n in args[:2]:n['geometry']['proxy_details']['planarity'][0]['sym_ops']=['x,y,z']*len(n['geometry']['proxy_details']['planarity'][0]['i_seqs'])
    with pytest.raises(ValueError):qualify(args,refs)


def test_canonical_plane_order_preserves_index_weight_associations(tmp_path):
    args,refs=case(tmp_path)
    for native in args[:2]:
        p=native['geometry']['proxy_details']['planarity'][0]
        for name in ('i_seqs','atoms','weights'):p[name].reverse()
    assert qualify(args,refs)['numerical_checks_pass']


def test_explicit_identity_symmetry_is_allowed_without_transforming_sites(tmp_path):
    args,refs=case(tmp_path)
    for ref in refs[0].values():ref['symmetry_operations']=['x,y,z']*len(ref['proxy']['i_seqs'])
    assert qualify(args,refs)['numerical_checks_pass']


def test_saved_numeric_evidence_relocates_without_original_source(tmp_path):
    old=tmp_path/'old';old.mkdir();args,refs=case(old);expected=qualify(args,refs)
    new=old.rename(tmp_path/'new');assert not old.exists()
    for i in (2,3,4,6):args[i]=new/args[i].name
    assert qualify(args,refs)==expected
