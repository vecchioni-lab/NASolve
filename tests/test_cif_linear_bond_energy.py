"""Native target changes must explain the complete energy and force difference."""
from copy import deepcopy
import math
import pytest
from tests.test_cif_linear_bond_native import fixture


def case(tmp_path):
    args=list(fixture(tmp_path));references=[]
    for side,native,offset in [('before',args[0],0),('after',args[1],1)]:
        full=[1.]*36;total=0.
        for j,index in enumerate((2,5)):
            proxy=native['geometry']['proxy_details']['bond_simple'][index]
            # Deliberately synthetic raw observations, not a harmonic model.
            target=2.+j+offset;gradient=[.1*(i+1+offset) for i in range(6)]
            for i,atom in enumerate(proxy['i_seqs']):
                for axis in range(3):full[3*atom+axis]+=gradient[3*i+axis]
            total+=target
            if side=='before':references.append({})
            evaluation=dict(single_target=target,accumulated_target=target,single_gradient=gradient,accumulated_gradient=gradient)
            references[j][side]=dict(proxy=deepcopy(proxy),sites_cart=[deepcopy(native['geometry']['sites_cart_exact'][i]) for i in proxy['i_seqs']],
                native_parameters=dict(slack=0.,limit=-1.,top_out=False),evaluations=[deepcopy(evaluation),deepcopy(evaluation)])
        snapshot=dict(target=3.+total,gradient=full,gradient_norm=math.hypot(*full),
            terms=dict(bond_residual_sum=total,dihedral_residual_sum=0.,planarity_residual_sum=3.),
            proxy_counts=dict(n_bond_proxies=9,n_dihedral_proxies=0,n_planarity_proxies=1))
        native['energy_inventory']=dict(policy_id='cif-fixed-native-usability-energy-v1',status='RECORDED',normalization=False,evaluation_calls=2,
            snapshots=[deepcopy(snapshot),deepcopy(snapshot)],installed_sources=[dict(module='cctbx.geometry_restraints.'+n,sha256='a'*64,historical_path='/old/'+n) for n in ('flags','energies','manager')])
    return args,references


def qualify(args,refs):
    from nasolve.cif_linear_bond_energy import qualify_linked_linear_bond_energy
    return qualify_linked_linear_bond_energy(*args,refs,bonds=[['Y','R']])


def test_every_changed_bond_explains_full_energy_and_gradient_difference(tmp_path):
    args,refs=case(tmp_path);original=deepcopy((args[:2],refs));r=qualify(args,refs)
    assert r['numerical_checks_pass'] and r['changed_bond_count']==2
    assert r['bond_target_delta']==r['target_delta']==2.
    assert r['gradient_delta_error_norm']<1e-14
    assert r['derivative_qualification']=='NOT_RUN' and not r['automatic_adoption']
    assert (args[:2],refs)==original


@pytest.mark.parametrize('defect',['unaffected_term','count','sum','gradient','repeat','local_target','local_gradient','local_repeat','container'])
def test_unexplained_total_or_local_difference_never_passes(tmp_path,defect):
    args,refs=case(tmp_path);snap=args[1]['energy_inventory']['snapshots']
    if defect=='unaffected_term':
        for s in snap:s['terms']['planarity_residual_sum']+=1;s['terms']['bond_residual_sum']-=1
    elif defect=='count':
        for s in snap:s['proxy_counts']['n_bond_proxies']+=1
    elif defect=='sum':
        for s in snap:s['target']+=1
    elif defect=='gradient':
        for s in snap:s['gradient'][-1]+=.1;s['gradient_norm']=math.hypot(*s['gradient'])
    elif defect=='repeat':snap[1]['terms']['bond_residual_sum']+=1
    elif defect=='local_repeat':refs[0]['after']['evaluations'][1]['single_target']+=1
    else:
        for r in refs[0]['after']['evaluations']:
            if defect=='local_target':r['single_target']=r['accumulated_target']=8.
            elif defect=='container':r['accumulated_gradient'][0]+=.1
            else:r['single_gradient']=r['accumulated_gradient']=[0.]*6
    assert not qualify(args,refs)['numerical_checks_pass']


@pytest.mark.parametrize('defect',['missing','extra','coordinates','proxy','unknown_proxy','options_missing','options_changed','option_type','nonfinite','short_gradient','native_source','native_change','symmetry'])
def test_unbound_or_incomplete_energy_evidence_refuses(tmp_path,defect):
    args,refs=case(tmp_path);ref=refs[0]['after']
    if defect=='missing':refs.pop()
    elif defect=='extra':refs.append(deepcopy(refs[0]))
    elif defect=='coordinates':ref['sites_cart'][0][0]+=1
    elif defect=='proxy':ref['proxy']['weight']=100.
    elif defect=='unknown_proxy':
        for n in args[:2]:
            for rows in (n['geometry']['simple_bonds'],n['geometry']['proxy_details']['bond_simple']):rows[2]['unrecorded_feature']=True
    elif defect=='options_missing':ref.pop('native_parameters')
    elif defect=='options_changed':ref['native_parameters']['slack']=.01
    elif defect=='option_type':ref['native_parameters']['top_out']=0
    elif defect=='nonfinite':ref['evaluations'][0]['single_target']=float('nan')
    elif defect=='short_gradient':ref['evaluations'][0]['single_gradient'].pop()
    elif defect=='native_source':args[1]['energy_inventory']['installed_sources'][0]['sha256']='b'*64
    elif defect=='native_change':args[1]['geometry']['proxy_details']['parallelity']=[]
    elif defect=='symmetry':
        for n in args[:2]:
            for rows in (n['geometry']['simple_bonds'],n['geometry']['proxy_details']['bond_simple']):rows[2]['symmetry_operation']='x,y,z'
    with pytest.raises(ValueError):qualify(args,refs)


def test_recorded_non_harmonic_options_are_preserved_without_inventing_a_spring(tmp_path):
    args,refs=case(tmp_path)
    for pair in refs:
        for side in pair.values():side['native_parameters']=dict(slack=.01,limit=.3,top_out=True)
    assert qualify(args,refs)['numerical_checks_pass']


def test_energy_readback_survives_input_relocation(tmp_path):
    old=tmp_path/'old';old.mkdir();args,refs=case(old);expected=qualify(args,refs);new=old.rename(tmp_path/'new')
    for i in (2,3,6):args[i]=new/args[i].name
    assert not old.exists() and qualify(args,refs)==expected
