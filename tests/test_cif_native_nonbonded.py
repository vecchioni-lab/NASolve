"""Native-pair evidence must explain the actual manager, not a distance guess."""
from copy import deepcopy
from unittest.mock import patch
import json
import math
import pytest
from tests.test_cif_captured_geometry import native


def capture():
    n=native();n['atoms'][1]['identity']['resseq']='10'
    # At distance 1, 16 * (2 - 1)**4 = 16; pair gradients are +/-64.
    pair={'i_seqs':[0,1],'vdw_distance':2.,'residual':16.,'gradient':[64.,0.,0.,-64.,0.,0.]}
    gradient=[64.,0.,0.,-64.,0.,0.,0.,0.,0.,0.,0.,0.]
    row={'target':18.,'gradient':gradient,'proxy_counts':{'n_nonbonded_proxies':2},
         'pairs':[pair,{'i_seqs':[0,2],'vdw_distance':.5,'residual':0.,'gradient':[0.]*6}],
         'nonbonded_target':16.,'nonbonded_gradient':gradient,
         'function_parameters':{'class':'prolsq_repulsion_function','c_rep':16.,'k_rep':1.,'irexp':1.,'rexp':4.},
         'nonbonded_membership':[{'i_seqs':[0,1],'vdw_distance':2.},{'i_seqs':[0,2],'vdw_distance':.5}]}
    e={'target':18.,'gradient':gradient,'gradient_norm':math.sqrt(sum(v*v for v in gradient)),
       'terms':{'nonbonded_residual_sum':16.},'proxy_counts':row['proxy_counts']}
    n['energy_inventory']={'policy_id':'cif-fixed-native-usability-energy-v1','status':'RECORDED','normalization':False,'evaluation_calls':2,'snapshots':[deepcopy(e),deepcopy(e)]}
    n['nonbonded_inventory']={'schema_version':1,'policy_id':'cif-native-nonbonded-attribution-v1','status':'RECORDED',
        'normalization':False,'symmetry_scope':'IDENTITY_ONLY','evaluation_calls':2,'pair_kernel_calls':6,'max_pair_kernel_calls':5000,
        'snapshots':[deepcopy(row),deepcopy(row)]}
    return n


def test_pairs_rank_actual_native_contributions_and_preserve_zero_rows():
    from nasolve.cif_native_nonbonded import review_native_nonbonded
    n=capture();before=deepcopy(n)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):r=review_native_nonbonded(n)
    assert n==before and r['status']=='REVIEW' and not r['automatic_adoption']
    assert r['pair_count']==2 and r['positive_residual_pairs']==1 and r['total_residual']==16.
    assert r['worst'][0]['distance']==1. and r['worst'][0]['sites']==['Z:9','Z:10']
    assert r['by_site_pair'][0]['residual']==16. and len(r['measurements'])==2
    assert r['native_execution']=='NOT_RUN' and r['chemical_qualification']=='NOT_ESTABLISHED'


@pytest.mark.parametrize('defect',['missing','policy','schema_bool','symmetry','count','duplicate','membership','sum','gradient','residual','coordinates','repeat','function','energy','nonfinite','kernel_count'])
def test_inconsistent_pair_evidence_is_refused(defect):
    from nasolve.cif_native_nonbonded import review_native_nonbonded
    n=capture();q=n['nonbonded_inventory'];row=q['snapshots'][0]
    if defect=='missing':n.pop('nonbonded_inventory')
    if defect=='policy':q['policy_id']='wrong'
    if defect=='schema_bool':q['schema_version']=True
    if defect=='symmetry':q['symmetry_scope']='ASU'
    if defect=='count':row['proxy_counts']['n_nonbonded_proxies']=3
    if defect=='duplicate':row['pairs'].append(deepcopy(row['pairs'][0]))
    if defect=='membership':row['nonbonded_membership'][0]['vdw_distance']=3.
    if defect=='sum':row['nonbonded_target']=17.
    if defect=='gradient':row['nonbonded_gradient'][0]=65.
    if defect=='residual':
        # Even a consistent forged sum must agree with coordinates/function.
        for r in q['snapshots']:r['pairs'][0]['residual']=17.;r['nonbonded_target']=17.
        for e in n['energy_inventory']['snapshots']:e['terms']['nonbonded_residual_sum']=17.
    if defect=='coordinates':n['geometry']['sites_cart_exact'][0]=[9.,0.,0.]
    if defect=='repeat':q['snapshots'][1]['target']=19.
    if defect=='function':row['function_parameters']['class']='unsupported'
    if defect=='energy':n['energy_inventory']['snapshots'][1]['terms']['nonbonded_residual_sum']=17.
    if defect=='nonfinite':row['pairs'][0]['gradient'][0]=float('nan')
    if defect=='kernel_count':q['pair_kernel_calls']=5
    with pytest.raises(ValueError):review_native_nonbonded(n)


def test_coincident_pair_uses_native_zero_gradient_convention_without_approval():
    from nasolve.cif_native_nonbonded import _pair_values
    d,r,g=_pair_values([0.,0.,0.],[0.,0.,0.],2.,{'c_rep':16.,'k_rep':1.,'irexp':1.,'rexp':4.})
    assert d==0 and r==256 and g==[0.]*6


@pytest.mark.parametrize('kw',[{'nonbonded_inventory':'yes'}, {'nonbonded_inventory':True},
 {'nonbonded_inventory':True,'energy_inventory':True},
 {'nonbonded_inventory':True,'energy_inventory':True,'inventory_detail':'linked','atom_name_mapping':True}])
def test_pair_capture_requires_explicit_compatible_flags_before_output(tmp_path,kw):
    from nasolve.cif_native_validation import inspect_native_bundle
    with pytest.raises(ValueError):inspect_native_bundle(tmp_path/'model',[],tmp_path/'out',tmp_path/'python',environment={},phenix_version='FAKE',**kw)
    assert not (tmp_path/'out').exists()


def test_worker_extension_preserves_legacy_energy_worker_and_guards_insertion():
    from nasolve.cif_native_nonbonded import native_nonbonded_worker
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_candidate_usability import native_energy_worker
    original=native_energy_worker(_NATIVE_WORKER);extended=native_nonbonded_worker(original)
    assert original==native_energy_worker(_NATIVE_WORKER) and 'nonbonded_inventory' not in original
    compile(extended,'native_worker.py','exec')
    with pytest.raises(ValueError):native_nonbonded_worker(_NATIVE_WORKER)
    with pytest.raises(ValueError):native_nonbonded_worker(extended)
