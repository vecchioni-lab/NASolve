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


def asu_capture():
    """Synthetic simple plus inversion-self-image arithmetic; not native evidence."""
    from nasolve.cif_native_asu import POLICY_ID, membership_digest
    n=capture();g=[64.,0.,0.,-128.,0.,0.,0.,0.,0.,0.,0.,0.]
    identity=[1.,0.,0.,0.,1.,0.,0.,0.,1.];negative=[-v for v in identity]
    table=[['simple',0,1,0,2.],['asu',1,1,1,3.]]
    maps=[[1,0,identity,[0.,0.,0.],identity],[1,1,negative,[0.,0.,0.],negative]]
    cell=[10.,10.,10.,90.,90.,90.]
    observations=dict(membership_sha256=membership_digest(table,maps,cell),target=24.,gradient=g,
        proxy_counts={'n_nonbonded_proxies':2},nonbonded_target=24.,nonbonded_gradient=g,
        kernels=[[16.,64.,0.,0.],[16.,-64.,0.,0.]])
    n['nonbonded_inventory']=dict(schema_version=1,policy_id=POLICY_ID,status='RECORDED',normalization=False,
        symmetry_scope='DIRECTED_ASU_AND_IDENTITY_SIMPLE',evaluation_calls=2,pair_kernel_calls=6,max_pair_kernel_calls=20000,
        pair_columns=['kind','i_seq','j_seq','j_sym','vdw_distance'],kernel_columns=['raw_residual','gradient_0_x','gradient_0_y','gradient_0_z'],
        pairs=table,mappings=maps,unit_cell=cell,function_parameters={'class':'prolsq_repulsion_function','c_rep':16.,'k_rep':1.,'irexp':1.,'rexp':4.},
        snapshots=[deepcopy(observations),deepcopy(observations)])
    for e in n['energy_inventory']['snapshots']:
        e.update(target=24.,gradient=g,gradient_norm=math.hypot(*g));e['terms']['nonbonded_residual_sum']=24.
    return n


def test_explicit_asu_mode_replays_inversion_self_image_without_changing_legacy():
    from nasolve.cif_native_nonbonded import review_native_nonbonded
    n=asu_capture();before=deepcopy(n)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):r=review_native_nonbonded(n)
    assert n==before and r['total_residual']==24. and r['pair_count']==2
    assert r['asu_pair_count']==1 and r['self_image_pair_count']==1
    row=next(p for p in r['measurements'] if p['kind']=='asu')
    assert row['raw_residual']==16. and row['residual']==8. and row['i_seqs']==[1,1]
    assert row['distance']==2. and row['image_j']==1 and not r['automatic_adoption']
    assert review_native_nonbonded(capture())['symmetry_scope']=='IDENTITY_ONLY'


@pytest.mark.parametrize('defect',['schema_bool','scope','pair_columns','kernel_columns','row_shape','index_bool','image_bool',
    'unknown_kind','simple_self','simple_image','missing_mapping','duplicate_mapping','mapping_index','bad_rotation','bad_inverse',
    'cell_length','cell_angle','cell_nonfinite','vdw','pair_nonfinite','raw_energy','raw_gradient','container_energy','container_gradient',
    'repeat','membership','kernel_budget','kernel_count','row_limit','manager_energy','function','unrequested_mapping'])
def test_asu_evidence_tampering_is_refused(defect):
    from nasolve.cif_native_nonbonded import review_native_nonbonded
    n=asu_capture();q=n['nonbonded_inventory'];s=q['snapshots'][0]
    if defect=='schema_bool':q['schema_version']=True
    elif defect=='scope':q['symmetry_scope']='IDENTITY_ONLY'
    elif defect=='pair_columns':q['pair_columns'].reverse()
    elif defect=='kernel_columns':q['kernel_columns'].reverse()
    elif defect=='row_shape':q['pairs'][0].append(1)
    elif defect=='index_bool':q['pairs'][0][1]=True
    elif defect=='image_bool':q['pairs'][1][3]=True
    elif defect=='unknown_kind':q['pairs'][0][0]='distance_guess'
    elif defect=='simple_self':q['pairs'][0][2]=0
    elif defect=='simple_image':q['pairs'][0][3]=1
    elif defect=='missing_mapping':q['mappings'].pop()
    elif defect=='duplicate_mapping':q['mappings'].append(deepcopy(q['mappings'][0]))
    elif defect=='mapping_index':q['mappings'][0][0]=99
    elif defect=='bad_rotation':q['mappings'][0][2][0]=2.
    elif defect=='bad_inverse':q['mappings'][0][4][0]=2.
    elif defect=='cell_length':q['unit_cell'][0]=0.
    elif defect=='cell_angle':q['unit_cell'][3]=180.
    elif defect=='cell_nonfinite':q['unit_cell'][0]=float('nan')
    elif defect=='vdw':q['pairs'][0][-1]=0.
    elif defect=='pair_nonfinite':q['pairs'][0][-1]=float('nan')
    elif defect=='raw_energy':s['kernels'][0][0]+=1.
    elif defect=='raw_gradient':s['kernels'][0][1]+=1.
    elif defect=='container_energy':s['nonbonded_target']+=1.
    elif defect=='container_gradient':s['nonbonded_gradient']=s['nonbonded_gradient'][:-1]
    elif defect=='repeat':q['snapshots'][1]['kernels'][0][0]+=1.
    elif defect=='membership':s['membership_sha256']='0'*64
    elif defect=='kernel_budget':q['max_pair_kernel_calls']=20001
    elif defect=='kernel_count':q['pair_kernel_calls']=5
    elif defect=='row_limit':q['pairs']*=5000
    elif defect=='manager_energy':n['energy_inventory']['snapshots'][0]['target']+=1.
    elif defect=='function':q['function_parameters']['class']='gaussian'
    elif defect=='unrequested_mapping':q['mappings'].append([2,0,[1.,0.,0.,0.,1.,0.,0.,0.,1.],[0.,0.,0.],[1.,0.,0.,0.,1.,0.,0.,0.,1.]])
    with pytest.raises(ValueError):review_native_nonbonded(n)


@pytest.mark.parametrize('policy,inventory', [('unknown',True),(True,True),('cif-native-nonbonded-asu-attribution-v1',False)])
def test_asu_request_policy_is_validated_before_output(tmp_path,policy,inventory):
    from nasolve.cif_native_validation import inspect_native_bundle
    with pytest.raises(ValueError):inspect_native_bundle(tmp_path/'model',[],tmp_path/'out',tmp_path/'python',environment={},phenix_version='FAKE',
        inventory_detail='linked',energy_inventory=True,nonbonded_inventory=inventory,nonbonded_policy=policy)
    assert not (tmp_path/'out').exists()


def test_asu_worker_is_explicit_and_legacy_worker_bytes_stay_exact():
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_nonbonded import native_nonbonded_worker
    from nasolve.cif_native_asu import POLICY_ID
    base=native_energy_worker(_NATIVE_WORKER)
    legacy=native_nonbonded_worker(base)
    extended=native_nonbonded_worker(base,policy=POLICY_ID)
    assert extended!=legacy and native_nonbonded_worker(base,policy=None)==legacy
    assert 'capture_asu_pairs' in extended and 'capture_asu_pairs' not in legacy
    compile(extended,'asu_worker.py','exec')
    with pytest.raises(ValueError):native_nonbonded_worker(base,policy='unknown')
    with pytest.raises(ValueError):native_nonbonded_worker(extended,policy=POLICY_ID)


def test_missing_or_null_pair_inventory_retains_value_error_contract():
    from nasolve.cif_native_nonbonded import review_native_nonbonded
    for value in (None, [], "bad"):
        n=capture();n['nonbonded_inventory']=value
        with pytest.raises(ValueError):review_native_nonbonded(n)


def test_asu_capture_refuses_oversized_native_membership_before_pair_kernels(monkeypatch):
    from types import SimpleNamespace
    from nasolve.cif_native_asu import capture_asu_pairs
    import sys
    class Function: pass
    def forbidden(**kwargs):raise AssertionError('No pair kernel may run after an oversized inventory')
    gr=SimpleNamespace(prolsq_repulsion_function=Function,nonbonded_prolsq=forbidden)
    flags=SimpleNamespace(flags=lambda **kwargs:None)
    gr.flags=flags
    monkeypatch.setitem(sys.modules,'cctbx',SimpleNamespace(geometry_restraints=gr))
    monkeypatch.setitem(sys.modules,'cctbx.array_family',SimpleNamespace(flex=SimpleNamespace(vec3_double=lambda p:p)))
    monkeypatch.setitem(sys.modules,'cctbx.geometry_restraints',gr)
    energy=SimpleNamespace(nonbonded_proxies=SimpleNamespace(simple=range(10000),asu=[]),nonbonded_function=Function())
    calls=[]
    geo=SimpleNamespace(energies_sites=lambda **kwargs:(calls.append(kwargs) or energy))
    with pytest.raises(RuntimeError,match='bounded kernel allowance'):capture_asu_pairs(geo,[[0.,0.,0.]])
    assert len(calls)==1


def test_basic_native_reader_does_not_import_optional_asu_extension(tmp_path):
    import builtins
    from nasolve.cif_native_validation import inspect_native_bundle
    original=builtins.__import__
    def guarded(name,*args,**kwargs):
        if name=='cif_native_asu':raise AssertionError('Legacy basic capture imported optional ASU dependencies')
        return original(name,*args,**kwargs)
    with patch('builtins.__import__',side_effect=guarded),pytest.raises(FileNotFoundError):
        inspect_native_bundle(tmp_path/'absent_model',[],tmp_path/'out',tmp_path/'python',
            environment={},phenix_version='FAKE',installed_library_only=True)
    assert not (tmp_path/'out').exists()
