"""Synthetic objectives: replay must distinguish bad derivatives from bad evidence."""
from copy import deepcopy
import math
from unittest.mock import patch
import pytest
from tests.test_cif_captured_geometry import native


def capture(wrong_gradient=False):
    from nasolve.cif_gradient_audit import audit_gradients, FAMILIES
    from nasolve.cif_mixed_gradient import _manager_digest
    from nasolve.cif_native_gradients import POLICY_ID, NUMERIC_MODULES
    n=native();points=n['geometry']['sites_cart_exact']
    n['geometry'].update(simple_bonds=deepcopy(n['geometry']['proxy_details']['bond_simple']),asu_bonds=[])
    n['monomer_mappings']={};n['installed_api_sources']=[]
    n['restraint_policy']={'secondary_structure_enabled':False,'origin_ids':{
        'edits':4,'hydrogen bonds':2,'basepair stacking':6,'basepair parallelity':7,'basepair planarity':9}}
    baselines={f:[] for f in FAMILIES}
    def evaluate(p,f):
        active=f in ('all','bond')
        r={'target':float(sum(x*x for xyz in p for x in xyz)) if active else 0.,
           'gradient':[(3. if wrong_gradient else 2.)*x if active else 0. for xyz in p for x in xyz],
           'proxy_counts':{'n_bond_proxies':1 if active else None}}
        if p==points:baselines[f].append(deepcopy(r))
        return r
    raw=evaluate(points,'all');baselines['all'].clear()
    energy={**raw,'gradient_norm':math.sqrt(sum(x*x for x in raw['gradient'])),'terms':{'bond_residual_sum':raw['target']}}
    sources=[{'module':m,'historical_path':'/unavailable/'+m,'sha256':'a'*64} for m in NUMERIC_MODULES]
    n['energy_inventory']={'policy_id':'cif-fixed-native-usability-energy-v1','status':'RECORDED','normalization':False,
        'evaluation_calls':2,'snapshots':[deepcopy(energy),deepcopy(energy)],'installed_sources':sources[:3]}
    audit=audit_gradients(evaluate,{'initial':points},[0,1],references={'initial':{k:energy[k] for k in ('target','gradient_norm')}},max_calls=2000)
    n['gradient_inventory']={'schema_version':1,'policy_id':POLICY_ID,'status':'RECORDED','normalization':False,
        'symmetry_scope':'IDENTITY_ONLY','parallelity_scope':'NO_PARALLELITY','selected_indices':[0,1],
        'coordinates_unchanged':True,'special_position_indices':[],
        'constraint_signature_before':'b'*64,'constraint_signature_after':'b'*64,
        'manager_sha256':_manager_digest(n),'installed_numeric_sources':sources,'installed_numeric_sources_after':deepcopy(sources),
        'gradient_audit':audit,'baseline_evaluations':baselines}
    return n


@pytest.mark.parametrize('wrong',[False,True])
def test_saved_numbers_recompute_good_and_bad_derivatives_without_execution(wrong):
    from nasolve.cif_native_gradients import review_native_gradients
    n=capture(wrong);before=deepcopy(n)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):r=review_native_gradients(n)
    assert n==before and r['sampled_derivatives_pass'] is (not wrong)
    assert r['native_execution']=='NOT_RUN' and r['model_optimization']=='NOT_RUN'
    assert r['chemical_qualification']=='NOT_ESTABLISHED' and not r['automatic_adoption']
    assert r['family_checks']['bond'] is (not wrong)
    assert r['evaluation_calls']==n['gradient_inventory']['gradient_audit']['evaluation_calls']


@pytest.mark.parametrize('defect',['policy','schema_bool','missing','normalization','indices','indices_bool','bounds',
 'signature','coordinates','manager','sources','sources_missing','source_hash','energy_source','energy_gradient',
 'energy_counts','energy_terms','proxy_count_bool','special','symmetry','parallelity','fixed_policy','target','flags','step','count','budget','baseline','extra_baseline','nan'])
def test_invalid_or_relabelled_derivative_evidence_is_refused(defect):
    from nasolve.cif_native_gradients import review_native_gradients
    n=capture();q=n['gradient_inventory'];a=q['gradient_audit'];case=a['cases']['initial']
    if defect=='policy':q['policy_id']='wrong'
    if defect=='schema_bool':q['schema_version']=True
    if defect=='missing':q.pop('baseline_evaluations')
    if defect=='normalization':q['normalization']=True
    if defect=='indices':q['selected_indices']=[0,0]
    if defect=='indices_bool':q['selected_indices']=[False,1]
    if defect=='bounds':q['selected_indices']=[0,99]
    if defect=='signature':q['constraint_signature_after']='c'*64
    if defect=='coordinates':n['geometry']['sites_cart_exact'][0][0]=.1;n['atoms'][0]['xyz'][0]=.1
    if defect=='manager':n['monomer_mappings']['altered']=True
    if defect=='sources':q['installed_numeric_sources_after'][0]['sha256']='c'*64
    if defect=='sources_missing':q['installed_numeric_sources'].pop()
    if defect=='source_hash':q['installed_numeric_sources'][0]['sha256']='invalid'
    if defect=='energy_source':n['energy_inventory']['installed_sources']=[]
    if defect=='energy_gradient':
        for e in n['energy_inventory']['snapshots']:
            e['gradient'][0]=1.;e['gradient_norm']=math.sqrt(sum(x*x for x in e['gradient']))
    if defect=='energy_counts':n['energy_inventory']['snapshots'][1]['proxy_counts']['n_bond_proxies']=2
    if defect=='energy_terms':n['energy_inventory']['snapshots'][1]['terms']['bond_residual_sum']=1.
    if defect=='proxy_count_bool':q['baseline_evaluations']['bond'][0]['proxy_counts']['n_bond_proxies']=True
    if defect=='special':q['special_position_indices']=[0]
    if defect=='symmetry':q['symmetry_scope']='ASU'
    if defect=='parallelity':n['geometry']['proxy_details']['parallelity']=[{}]
    if defect=='fixed_policy':n['restraint_policy']['secondary_structure_enabled']=True
    if defect=='target':case['families']['bond']['directions'][0]['samples'][0]['plus_target']+=1.
    if defect=='flags':case['sampled_gradients_consistent']=False
    if defect=='step':case['families']['bond']['directions'][0]['samples'][0]['step']=.2
    if defect=='count':a['evaluation_calls']-=1
    if defect=='budget':a['max_evaluation_calls']=6000
    if defect=='baseline':q['baseline_evaluations']['all'][1]['gradient'][0]=5.
    if defect=='extra_baseline':q['baseline_evaluations']['bond'].append(q['baseline_evaluations']['bond'][0])
    if defect=='nan':case['families']['all']['baseline']['gradient'][0]=float('nan')
    with pytest.raises(ValueError):review_native_gradients(n)


@pytest.mark.parametrize('indices',[[],[True],[0,0],[-1],list(range(7)),[.5],'0'])
def test_invalid_probes_fail_before_outputs(tmp_path,indices):
    from nasolve.cif_native_validation import inspect_native_bundle
    with pytest.raises(ValueError):inspect_native_bundle(tmp_path/'model',[],tmp_path/'out',tmp_path/'python',environment={},phenix_version='FAKE',
        inventory_detail='linked',energy_inventory=True,policy_inventory=True,gradient_indices=indices)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('kw',[{}, {'inventory_detail':'linked'}, {'inventory_detail':'linked','energy_inventory':True},
 {'inventory_detail':'linked','energy_inventory':True,'policy_inventory':True,'nonbonded_inventory':True},
 {'inventory_detail':'linked','energy_inventory':True,'policy_inventory':True,'atom_name_mapping':True}])
def test_incompatible_capture_flags_fail_before_outputs(tmp_path,kw):
    from nasolve.cif_native_validation import inspect_native_bundle
    with pytest.raises(ValueError):inspect_native_bundle(tmp_path/'model',[],tmp_path/'out',tmp_path/'python',environment={},phenix_version='FAKE',gradient_indices=[0],**kw)
    assert not (tmp_path/'out').exists()


def test_extension_preserves_old_worker_bytes_and_isolated_helper_namespace():
    from nasolve.cif_native_gradients import native_gradient_worker
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_nonbonded import native_nonbonded_worker
    original=native_energy_worker(_NATIVE_WORKER);extended=native_gradient_worker(original)
    assert original==native_energy_worker(_NATIVE_WORKER) and 'gradient_inventory' not in original
    compile(extended,'worker.py','exec')
    for bad in [_NATIVE_WORKER,extended,native_nonbonded_worker(original)]:
        with pytest.raises(ValueError):native_gradient_worker(bad)


@pytest.mark.parametrize('mode',['correct','bad_derivative','parallelity','special','asu','symmetry','moved','changed_sources','bounds'])
def test_worker_captures_real_control_flow_and_refuses_unsupported_managers(monkeypatch,mode):
    from types import SimpleNamespace as NS
    import sys
    import nasolve.cif_native_gradients as g
    n=capture(mode=='bad_derivative');q=n['gradient_inventory'];points=deepcopy(n['geometry']['sites_cart_exact'])
    class Flags:
        def __init__(self,default):self.default=default
    calls=[]
    def energy(**kw):
        f=kw['flags'];active=f.default or getattr(f,'bond',False);p=kw['sites_cart'];calls.append(p)
        vector=[(3. if mode=='bad_derivative' else 2.)*x if active else 0. for xyz in p for x in xyz]
        nb=NS(asu=[1] if mode=='asu' else [],simple=[NS(rt_mx_ji=NS(is_unit_mx=lambda:False))] if mode=='symmetry' else [])
        if mode=='moved':points[0][0]+=.1
        return NS(target=float(sum(x*x for xyz in p for x in xyz)) if active else 0.,
            gradients=NS(as_double=lambda:vector),n_bond_proxies=1 if active else None,nonbonded_proxies=nb)
    geo=NS(parallelity_proxies=[1] if mode=='parallelity' else [],
        site_symmetry_table=NS(special_position_indices=lambda:[0] if mode=='special' else []),energies_sites=energy)
    modules={'cctbx':NS(),'cctbx.array_family':NS(flex=NS(vec3_double=lambda p:p)),
             'cctbx.geometry_restraints':NS(flags=NS(flags=Flags))}
    for k,v in modules.items():monkeypatch.setitem(sys.modules,k,v)
    monkeypatch.setattr(g,'fixed_signature',lambda *a:'b'*64)
    sources=iter([q['installed_numeric_sources'],[] if mode=='changed_sources' else q['installed_numeric_sources']])
    monkeypatch.setattr(g,'_numeric_sources',lambda:next(sources))
    selected=[99] if mode=='bounds' else [0,1]
    if mode not in ('correct','bad_derivative'):
        with pytest.raises((ValueError,RuntimeError)):g._capture_gradients(geo,points,n,selected)
    else:
        n['gradient_inventory']=g._capture_gradients(geo,points,n,selected)
        report=g.review_native_gradients(n)
        assert report['sampled_derivatives_pass'] is (mode=='correct')
        assert len(calls)==report['evaluation_calls'] and points==n['geometry']['sites_cart_exact']


@pytest.mark.parametrize('mode',['correct','probes','missing_policy','worker','native_payload'])
def test_receipt_binds_derivative_request_and_exact_maintained_worker(tmp_path,mode):
    import json
    from tests.test_cif_attachment_native import fixture,rebind
    from nasolve.cif_attachment_native import _capture
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_gradients import native_gradient_worker
    manifest,path=fixture(tmp_path);spec_path=path.parent/'native_spec.json';spec=json.loads(spec_path.read_text())
    spec.update(energy_inventory=True,policy_inventory=True,gradient_indices=[0,1])
    if mode=='probes':spec['gradient_indices']=[1,2]
    if mode=='missing_policy':del spec['policy_inventory']
    spec_path.write_text(json.dumps(spec))
    worker=native_gradient_worker(native_energy_worker(_NATIVE_WORKER))
    (path.parent/'native_worker.py').write_text(worker+('wrong' if mode=='worker' else ''))
    n=capture();n.update(automatic_adoption=False,scientific_approval='NOT_RUN',model_editing='NOT_RUN',optimization='NOT_RUN',
        dictionary_loading=[],fatal_problems=None,unused_definitions=[],unsupported_fields=[])
    if mode=='native_payload':n['gradient_inventory']['gradient_audit']['cases']['initial']['sampled_gradients_consistent']=False
    rebind(path,lambda r:r.update(native_validation=n))
    payload=(manifest.parent/'model.pdb').read_bytes()
    if mode=='correct':assert _capture(path,payload)[1]==n
    else:
        with pytest.raises(ValueError):_capture(path,payload)
