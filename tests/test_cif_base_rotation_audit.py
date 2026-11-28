"""Graph-selected diagnostic rotations preserve the scaffold and expose torque conflicts."""
from copy import deepcopy
import math
import pytest
from tests.test_cif_fragment_restoration import fixture


@pytest.mark.parametrize(('anchor','element'),[('NX','N'),('CX','C'),('MIS','C')])
def test_graph_selection_has_no_component_or_attachment_name_allowlist(tmp_path,anchor,element):
    from nasolve.cif_base_rotation_audit import plan_base_rotations,rotate_group
    _,_,_,native,_=fixture(tmp_path,anchor,element);points=native['geometry']['sites_cart_exact']
    # A named custom distance is not required: select the site from a real captured outlier.
    native['geometry']['proxy_details']['bond_simple']=[{'i_seqs':[11,12],'distance_ideal':1.,'weight':100.,'origin_id':0,'atoms':[native['atoms'][i]['label'] for i in [11,12]]}]
    native['geometry']['proxy_counts']['bond_simple']=1
    before=deepcopy(native);p=plan_base_rotations(native,points)
    assert native==before and p['selected_sites']==['Z:9'] and len(p['groups'])==1
    g=p['groups'][0];assert g['attachment_atom']==anchor and set(g['i_seqs'])=={11,12,13}
    moved=rotate_group(points,g,math.pi/3);assert points==before['geometry']['sites_cart_exact']
    assert moved[:11]==points[:11] and moved[11]==points[11]
    assert moved[12]!=points[12]
    for i in g['i_seqs']:
        for j in g['i_seqs']+[g['origin_index']]:assert math.dist(moved[i],moved[j])==pytest.approx(math.dist(points[i],points[j]),abs=1e-12)


@pytest.mark.parametrize('defect',['multi_attachment','disconnected','sugar','altloc','duplicate','nonfinite','axis'])
def test_unsupported_context_is_recorded_or_refused_without_silent_reselection(tmp_path,defect):
    from nasolve.cif_base_rotation_audit import plan_base_rotations
    _,_,_,n,_=fixture(tmp_path);p=deepcopy(n['geometry']['sites_cart_exact'])
    n['geometry']['proxy_details']['bond_simple']=[{'i_seqs':[11,12],'distance_ideal':1.,'weight':100.,'origin_id':0,'atoms':[n['atoms'][i]['label'] for i in [11,12]]}]
    n['geometry']['proxy_counts']['bond_simple']=1
    d=n['monomer_mappings']['rows'][0]['metadata']['effective_definition']
    if defect=='multi_attachment':d['bonds'].append({'atom_id_1':'QZ','atom_id_2':"C2'",'type':'single'})
    if defect=='disconnected':d['bonds'].pop()
    if defect=='sugar':d['bonds'][7]['type']='aromatic'
    if defect=='altloc':n['atoms'][12]['identity']['altloc']='A'
    if defect=='duplicate':n['atoms'][13]['atom_id']=n['atoms'][12]['atom_id']
    if defect=='nonfinite':p[12][0]=float('nan')
    if defect=='axis':p[11]=p[7].copy()
    if defect in {'duplicate','nonfinite'}:
        with pytest.raises(ValueError):plan_base_rotations(n,p)
    else:
        result=plan_base_rotations(n,p);assert result['groups']==[] and result['unsupported_sites'][0]['site']=='Z:9'


def problem():
    points=[[0.,0.,0.],[0.,0.,1.],[1.,.3,1.4],[.4,1.2,1.7]]
    group={'site':'ZZ:17','i_seqs':[1,2,3],'origin_index':0,'attachment_index':1}
    return points,{'groups':[group],'selected_sites':['ZZ:17']}


def test_right_handed_rotation_has_an_independent_known_coordinate_oracle():
    from nasolve.cif_base_rotation_audit import rotate_group
    points=[[0.,0.,0.],[0.,0.,1.],[1.,0.,1.],[0.,1.,2.]]
    group={'i_seqs':[1,2,3],'origin_index':0,'attachment_index':1}
    moved=rotate_group(points,group,math.pi/2)
    assert moved[2]==pytest.approx([0.,1.,1.],abs=1e-14)
    assert moved[3]==pytest.approx([-1.,0.,2.],abs=1e-14)


def polynomial(points,family):
    from nasolve.cif_gradient_audit import FAMILIES
    w=sum(range(1,8)) if family=='all' else FAMILIES.index(family)
    flat=[v for p in points for v in p]
    return {'target':w*sum((i+1)*v*v for i,v in enumerate(flat)),
            'gradient':[2*w*(i+1)*v for i,v in enumerate(flat)],'proxy_counts':{'n_nonbonded_proxies':5}}


@pytest.mark.parametrize('biased',[False,True])
def test_rotational_chain_rule_finite_differences_and_family_cancellation(biased):
    from nasolve.cif_base_rotation_audit import audit_base_rotations
    points,plan=problem();saved=deepcopy(points)
    def evaluate(x,f):
        r=polynomial(x,f)
        if biased and f in {'all','parallelity'}:r['gradient'][6]+=9.
        return r
    r=audit_base_rotations(evaluate,{'full_precision':points},plan)
    c=r['cases']['full_precision'];g=c['groups'][0]
    assert r['analysis_completed'] and r['model_optimization']=='NOT_RUN' and points==saved
    assert c['sampled_rotation_derivatives_consistent'] is (not biased)
    assert [v['angle_degrees'] for v in g['profile']]==[-180,-90,-30,-10,0,10,30,90,180]
    assert g['periodic_energy_consistent'] and g['max_rigid_distance_change']<1e-12
    assert all(v['target_additivity']['consistent'] for v in g['profile'])
    assert all(len(v['derivative']['samples'])==4 for v in g['profile'])
    assert set(g['zero_angle_family_derivatives'])=={'bond','angle','dihedral','chirality','planarity','parallelity','nonbonded'}
    assert r['evaluation_calls']<=3000 and r['automatic_adoption'] is False
    assert g['lowest_sampled_target']['interpretation']=='DIAGNOSTIC_SAMPLE_NOT_A_CANDIDATE_OR_OPTIMUM'


@pytest.mark.parametrize('defect',['budget','drift','bad_gradient','changed_snapshot','bad_plan'])
def test_drift_budgets_and_changed_endpoint_cannot_be_qualified(defect):
    from nasolve.cif_base_rotation_audit import audit_base_rotations
    points,plan=problem();calls=0
    def evaluate(x,f):
        nonlocal calls
        calls+=1;r=polynomial(x,f)
        if defect=='drift':r['target']+=calls*.01
        if defect=='bad_gradient':r['gradient'][0]=float('inf')
        return r
    kwargs={}
    if defect=='budget':kwargs['max_calls']=5
    if defect=='changed_snapshot':kwargs['references']={'full_precision':{'target':-2.,'gradient':[0.]*12}}
    if defect=='bad_plan':plan['groups'][0]['i_seqs']=[True,2,3]
    if defect in {'budget','bad_gradient','bad_plan'}:
        with pytest.raises(ValueError):audit_base_rotations(evaluate,{'full_precision':points},plan,**kwargs)
    else:
        r=audit_base_rotations(evaluate,{'full_precision':points},plan,**kwargs)
        assert not r['cases']['full_precision']['sampled_rotation_derivatives_consistent']


@pytest.mark.parametrize('mode',['correct','endpoint','source','timeout','numeric','adapter','cpp','manager'])
def test_native_rotation_worker_matches_qualified_sources_and_never_optimizes(tmp_path,monkeypatch,mode):
    import os,sys,json
    from pathlib import Path
    from nasolve.cif_fixed_geometry import run_fixed_geometry
    import nasolve.cif_base_rotation_audit as rotation
    from tests.test_cif_corrected_geometry import native_fixture
    model,dictionary,native,seed,config=native_fixture(tmp_path,monkeypatch,'limit')
    native['geometry']['proxy_details']['bond_simple']=[{'i_seqs':[11,12],'distance_ideal':1.,'weight':100.,'origin_id':0,
        'atoms':[native['atoms'][i]['label'] for i in [11,12]]}]
    native['geometry']['proxy_counts']['bond_simple']=1
    environment={**os.environ,'PYTHONPATH':str(seed)}
    first=run_fixed_geometry(model,[dictionary],[],native,tmp_path/'first',sys.executable,environment=environment,
        phenix_version='EXPLICIT_FAKE',max_iterations=5,timeout_seconds=30,policy_inventory=True,validated_correction=config)
    assert first['status']=='REVIEW',first
    prior=first['result'];plan=rotation.plan_base_rotations(native,prior['final_sites_cart']);assert plan['groups']
    if mode=='source':config['correction_core_sha256']='0'*64
    if mode=='endpoint':prior['final_sites_cart'][12][0]+=.001
    for name,field,oldfield in [('numeric','installed_optimizer_sources','installed_numeric_sources'),
            ('adapter','installed_adapter_sources','installed_adapter_sources'),('cpp','installed_parallelity_sources','installed_parallelity_sources')]:
        if mode==name:config['result'][oldfield][0]['sha256']='0'*64;prior[field][0]['sha256']='0'*64
    if mode=='manager':
        import nasolve.cif_native_validation as native_module
        monkeypatch.setattr(native_module,'_NATIVE_WORKER',native_module._NATIVE_WORKER.replace("sites=flex.vec3_double", "report['atom_count']+=1\nsites=flex.vec3_double"))
    if mode=='timeout':monkeypatch.setattr(rotation,'_ROTATION_WORKER','import time\ntime.sleep(30)\n')
    if mode=='source':
        with pytest.raises(ValueError):rotation.run_native_base_rotation_audit(model,[dictionary],[],native,prior,config,plan,tmp_path/'out',sys.executable,environment=environment,phenix_version='EXPLICIT_FAKE')
        return
    if mode=='endpoint':plan=rotation.plan_base_rotations(native,prior['final_sites_cart'])
    result=rotation.run_native_base_rotation_audit(model,[dictionary],[],native,prior,config,plan,tmp_path/'out',sys.executable,
        environment=environment,phenix_version='EXPLICIT_FAKE',timeout_seconds=1 if mode=='timeout' else 30)
    assert result['source_preserved'] and result['frozen_inputs_preserved']
    work=Path(result['native_directory']);assert not (work/'fake_optimizer_called').exists()
    assert json.loads((work/'rotation_receipt.json').read_text())==result
    assert result['status']==('REVIEW' if mode=='correct' else 'FAILED'),result
    if mode=='correct':
        q=result['result'];assert q['rotation_derivative_qualification']=='SAMPLED_ROTATION_DERIVATIVES_PASS'
        assert q['qualified_endpoint_family_snapshots_match'] and q['preflight_evaluations']==17
        assert q['evaluation_calls']==q['preflight_evaluations']+q['audit_evaluation_calls']<3000
        assert q['constraint_signature_before']==q['constraint_signature_after']==prior['constraint_signature_before']
        assert all(v['selected_scalar_measurements'] for c in q['cases'].values() for g in c['groups'] for v in g['profile'])
    elif mode=='endpoint':assert 'Saved endpoint target or complete family gradient differs' in result['result']['error']
    elif mode=='timeout':assert result['execution']['status']=='TIMED_OUT'
    else:
        assert {'numeric':'Qualified numerical sources','adapter':'Qualified adapters','cpp':'Qualified native plane source','manager':'Native manager changed'}[mode] in result['result']['error']
