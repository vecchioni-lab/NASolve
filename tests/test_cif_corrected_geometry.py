"""A corrected trial requires real derivative evidence before optimization."""
from copy import deepcopy
from types import SimpleNamespace as NS
import hashlib,json,math,os,sys
from pathlib import Path
import pytest
from nasolve.cif_gradient_audit import audit_gradients
from nasolve.cif_parallelity_correction import audit_plane_orders,plane_order_evaluator
from tests.test_cif_parallelity_correction import Vec
from tests.test_cif_plane_order_correction import OrderAPI


def qualified_result(points=None):
    from nasolve.cif_parallelity_audit import toy_planes
    from nasolve.cif_gradient_audit import FAMILIES
    toy=toy_planes()[0];points=toy['points'] if points is None else points;weights={f:i+1 for i,f in enumerate(FAMILIES[1:])}
    def evaluate(x,family):
        w=sum(weights.values()) if family=='all' else weights[family]
        return {'target':w*sum(v*v for p in x for v in p),'gradient':[2*w*v for p in x for v in p]}
    cases={k:points for k in ['initial','full_precision','pdb_rounded']}
    q=audit_gradients(evaluate,cases,[0],max_calls=5500)
    q.update(status='REVIEW',policy_id='cif-fixed-native-plane-order-gradient-audit-v1',
        correction_policy_id='native-parallelity-both-first-planes-v1',correction_qualification='SAMPLED_NATIVE_DERIVATIVES_PASS',
        plane_order_safe=True,normalization=False,captured_inventory_matches=True,
        constraint_signature_before='1'*64,constraint_signature_after='1'*64,
        installed_numeric_sources=[],installed_adapter_sources=[],installed_parallelity_sources=[])
    q['plane_order_audit']=audit_plane_orders(plane_order_evaluator(OrderAPI(isotropic=True),NS(vec3_double=Vec,size_t=list)),cases,[toy['proxy']])
    return q,len(points)


@pytest.mark.parametrize('defect',['none','qualification','initial','family','sample','plane_sample','plane_case','rotation','signature','policy','gradient','empty'])
def test_trial_qualification_rechecks_samples_and_refuses_incomplete_proof(defect):
    from nasolve.cif_corrected_geometry import validate_gradient_qualification
    q,count=qualified_result()
    if defect=='qualification':q['correction_qualification']='DERIVATIVE_REVIEW'
    if defect=='initial':q['cases'].pop('initial')
    if defect=='family':q['cases']['initial']['families'].pop('angle')
    if defect=='sample':q['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1.
    if defect=='plane_sample':q['plane_order_audit']['cases']['initial']['proxies'][0]['original']['directions'][0]['samples'][0]['order_safe']['plus_target']+=1.
    if defect=='plane_case':q['plane_order_audit']['cases'].pop('initial')
    if defect=='rotation':q['plane_order_audit']['rotation_controls'][0]['rotation_gradient_consistent']=False
    if defect=='signature':q['constraint_signature_after']='2'*64
    if defect=='policy':q['correction_policy_id']='UNKNOWN'
    if defect=='gradient':q['cases']['initial']['families']['all']['baseline']['gradient'].pop()
    if defect=='empty':q['plane_order_audit']['cases']['initial']['proxies']=[]
    if defect=='none':assert validate_gradient_qualification(q,count) is True
    else:
        with pytest.raises(ValueError):validate_gradient_qualification(q,count)


def native_fixture(tmp_path,monkeypatch,mode):
    import nasolve.cif_native_validation as native_module
    import nasolve.cif_fixed_geometry as fixed_module
    from nasolve.cif_gradient_audit import fixed_signature
    from nasolve.cif_parallelity_correction import run_native_correction_audit
    from tests.test_cif_fixed_geometry import worker_fixture,policy_inventory
    from tests.test_cif_fragment_restoration import fixture
    from tests.test_cif_parallelity_audit import _FAKE_PLANE_API,evaluate as plane_evaluate
    protected=tmp_path/'protected';protected.mkdir();_,model,_,native,_=fixture(protected);policy_inventory(native)
    dictionary=protected/'fake.cif';dictionary.write_text('data_comp_ZZZ\n_chem_comp.id ZZZ\n')
    proxy={'i_seqs':[0,1,2],'j_seqs':[3,4,5,6],'weight':2.7,'target_angle_deg':0.,'slack':0.,'limit':1.,'top_out':False,'origin_id':4}
    native['geometry']['proxy_details']['parallelity']=[proxy]
    native['geometry']['proxy_counts']['parallelity']=1
    seed=worker_fixture(tmp_path/'fake',native,mode if mode in {'limit','rounding'} else 'converged')
    kinds=['bond','angle','dihedral','chirality','planarity','nonbonded']
    (seed/'cctbx/array_family/flex.py').write_text('from fake_arrays import Vec\ndef vec3_double(values,fill=None):return Vec([fill]*values if isinstance(values,int) else values)\ndef size_t(v):return list(v)\n')
    (seed/'cctbx/geometry_restraints/flags.py').write_text('class flags:\n def __init__(self,default=False):\n'+''.join(f'  self.{k}=default\n' for k in kinds+['parallelity']))
    api=_FAKE_PLANE_API.replace('BROKEN = False','BROKEN = True').replace('def parallelity_proxy(**kw):return NS(**kw,sym_ops=None)',
        "def parallelity_proxy(**kw):\n p=kw.pop('proxy',None);values={k:v for k,v in vars(p).items() if k!='sym_ops'} if p else {};values.update(kw);return NS(**values,sym_ops=None)")
    (seed/'cctbx/geometry_restraints/__init__.py').write_text(api)
    cpp=[]
    for name in ['parallelity.h','parallelity_bpl.cpp']:
        p=seed/'cctbx/geometry_restraints'/name;p.write_text('EXPLICIT_FAKE_'+name+'\n');data=p.read_bytes()
        cpp.append({'anchor':'native_geometry_module','path':name,'status':'RECORDED','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    bootstrap='''
import json
from pathlib import Path
from types import SimpleNamespace as NS
from cctbx import geometry_restraints as gr
from cctbx.array_family import flex
report=json.loads(Path('expected_inventory.json').read_text())
sites=flex.vec3_double(report['geometry']['sites_cart_exact'])
class Geo:
    site_symmetry_table=NS(special_position_indices=lambda:[])
    crystal_symmetry=NS(unit_cell=lambda:NS(parameters=lambda:(50.,51.,52.,90.,90.,90.)),space_group_info=lambda:'P 1')
    angle_proxies=[];dihedral_proxies=[];const_dihedral_proxies=[];chirality_proxies=[];planarity_proxies=[]
    parallelity_proxies=gr.shared_parallelity_proxy([gr.parallelity_proxy(**PROXY)])
    def pair_proxies(self,sites_cart):return NS(bond_proxies=NS(simple=[],asu=[]))
    def energies_sites(self,sites_cart,flags,compute_gradients,normalization):
        assert compute_gradients and normalization is False
        coefficient=sum(1 for k in KINDS if getattr(flags,k))
        gradient=flex.vec3_double(len(sites_cart),(0.,0.,0.));parallel=0.
        if flags.parallelity:parallel=gr.parallelity_residual_sum(sites_cart,self.parallelity_proxies,gradient)
        for i,point in enumerate(sites_cart):gradient[i]=tuple(a+2*coefficient*v for a,v in zip(gradient[i],point))
        if MODE=='endpoint' and flags.bond and sites_cart[0][0]<sites[0][0]-.05:gradient[0]=(gradient[0][0]+3.,*gradient[0][1:])
        return NS(target=coefficient*sum(v*v for p in sites_cart for v in p)+parallel,gradients=gradient,
                  parallelity_residual_sum=parallel,n_parallelity_proxies=len(self.parallelity_proxies) if flags.parallelity else None)
geo=Geo()
raise SystemExit(0)
'''.replace('PROXY',repr(proxy)).replace('KINDS',repr(kinds)).replace('MODE',repr(mode))
    monkeypatch.setattr(native_module,'_NATIVE_WORKER',bootstrap);monkeypatch.setattr(fixed_module,'_NATIVE_WORKER',bootstrap)
    sources=[(name,path) for name,path in [('scitbx.lbfgs','scitbx/lbfgs.py'),('cctbx.geometry_restraints.flags','cctbx/geometry_restraints/flags.py'),
        ('cctbx.geometry_restraints.manager','cctbx/geometry_restraints/manager.py'),('cctbx.geometry_restraints.energies','cctbx/geometry_restraints/energies.py'),
        ('scitbx_lbfgs_ext','scitbx_lbfgs_ext.py'),('cctbx_geometry_restraints_ext','cctbx_geometry_restraints_ext.py')]]
    fingerprints=lambda rows:[{'module':name,'sha256':hashlib.sha256((seed/path).read_bytes()).hexdigest()} for name,path in rows]
    numeric=fingerprints(sources);adapters=fingerprints([('cctbx.geometry_restraints','cctbx/geometry_restraints/__init__.py'),('cctbx.array_family.flex','cctbx/array_family/flex.py')])
    cases={name:deepcopy(native['geometry']['sites_cart_exact']) for name in ['initial','full_precision','pdb_rounded']}
    if mode=='baseline':cases['initial'][0][0]+=.1
    references={};captured={}
    for label,points in cases.items():
        plane=plane_evaluate(points,proxy,broken=True);raw=[12*v+g for point,gs in zip(points,[plane['accumulated_gradient'][i:i+3] for i in range(0,len(plane['accumulated_gradient']),3)]) for v,g in zip(point,gs)]
        references[label]={'target':6*sum(v*v for p in points for v in p)+plane['accumulated_target'],'gradient_norm':math.sqrt(math.fsum(g*g for g in raw))}
        captured[label]={'accumulated_residual':plane['accumulated_target'],'accumulated_gradient':plane['accumulated_gradient'],'manual_gradient':plane['single_gradient']}
    geo=NS(pair_proxies=lambda **kw:NS(bond_proxies=NS(simple=[],asu=[])),parallelity_proxies=[NS(**proxy)],
        **{kind+'_proxies':[] for kind in ['angle','dihedral','const_dihedral','chirality','planarity']})
    evidence=run_native_correction_audit(model,[dictionary],[],native,cases,references,captured,[0],numeric,adapters,cpp,fixed_signature(geo,[]),
        tmp_path/'proof',sys.executable,environment={**os.environ,'PYTHONPATH':str(seed)},phenix_version='EXPLICIT_FAKE',plane_order_safe=True)
    assert evidence['status']=='REVIEW' and evidence['result']['correction_qualification']=='SAMPLED_NATIVE_DERIVATIVES_PASS',evidence
    config={'result':evidence['result'],'archive_sha256':'1'*64,'correction_core_sha256':hashlib.sha256(Path(fixed_module.__file__).with_name('cif_parallelity_correction.py').read_bytes()).hexdigest()}
    if mode=='source':config['correction_core_sha256']='0'*64
    if mode=='proof':config['result']['cases']['initial']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1.
    if mode=='api':config['result']['installed_numeric_sources'][0]['sha256']='0'*64
    if mode=='adapter':config['result']['installed_adapter_sources'][0]['sha256']='0'*64
    if mode=='cpp':config['result']['installed_parallelity_sources'][0]['sha256']='0'*64
    if mode=='manager':monkeypatch.setattr(fixed_module,'_NATIVE_WORKER',bootstrap.replace('sites=flex.vec3_double',"report['atom_count']+=1\nsites=flex.vec3_double"))
    if mode=='timeout':monkeypatch.setattr(fixed_module,'_GEOMETRY_WORKER','import time\ntime.sleep(30)\n')
    return model,dictionary,native,seed,config


@pytest.mark.parametrize('mode',['converged','limit','rounding','source','proof','api','adapter','cpp','manager','baseline','endpoint','timeout'])
def test_corrected_native_trial_uses_qualified_gradients_and_keeps_actual_verdicts(tmp_path,monkeypatch,mode):
    from nasolve.cif_fixed_geometry import run_fixed_geometry
    model,dictionary,native,seed,config=native_fixture(tmp_path,monkeypatch,mode)
    kwargs=dict(environment={**os.environ,'PYTHONPATH':str(seed)},phenix_version='EXPLICIT_FAKE',max_iterations=5,
        timeout_seconds=1 if mode=='timeout' else 30,policy_inventory=True,validated_correction=config)
    if mode in {'source','proof'}:
        with pytest.raises(ValueError):run_fixed_geometry(model,[dictionary],[],native,tmp_path/'out',sys.executable,**kwargs)
        assert not list((tmp_path/'out').glob('*/fake_optimizer_called'));return
    r=run_fixed_geometry(model,[dictionary],[],native,tmp_path/'out',sys.executable,**kwargs)
    good=mode in {'converged','limit','rounding','endpoint'};assert r['status']==('REVIEW' if good else 'FAILED'),r
    assert r['source_preserved'] and r['frozen_inputs_preserved']
    work=Path(r['native_directory']);assert json.loads((work/'geometry_receipt.json').read_text())==r
    if good:
        q=r['result'];assert q['qualified_initial_snapshot_matches'] and (work/'fake_optimizer_called').exists()
        assert q['correction_policy_id']=='native-parallelity-both-first-planes-v1' and q['starting_coordinates']=='CAPTURED_INITIAL'
        assert q['constraint_signature_before']==q['constraint_signature_after']==config['result']['constraint_signature_before']
        assert q['endpoint_gradient_audit']['analysis_completed'] and q['endpoint_gradient_audit']['evaluation_calls']<=4000
        assert q['endpoint_derivative_qualification']==('DERIVATIVE_REVIEW' if mode=='endpoint' else 'SAMPLED_NATIVE_DERIVATIVES_PASS')
        assert r['convergence']=={'converged':'NATIVE_CRITERION_MET','endpoint':'NATIVE_CRITERION_MET','limit':'NOT_CONVERGED_LIMIT','rounding':'NOT_CONVERGED_ERROR'}[mode]
        assert q['initial']['target']>q['final']['target'] and 'native_gradient_norm' in q['final']
    else:
        assert not (work/'fake_optimizer_called').exists()
        if mode=='timeout':assert r['execution']['status']=='TIMED_OUT'
        else:
            messages={'api':'Qualified native numerical sources','adapter':'Qualified native adapters','cpp':'Qualified native plane source',
                'manager':'Captured native identities','baseline':'Qualified initial corrected snapshot'}
            assert messages[mode] in r['error']
