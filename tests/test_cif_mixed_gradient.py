"""Fresh initial mixed-manager derivative qualification, with immutable inputs."""
from copy import deepcopy
from pathlib import Path
import json
import pytest


def initial_numerical_evidence(*,biased=False):
    """A real sampled initial-only polynomial and independent plane control."""
    from types import SimpleNamespace as NS
    from nasolve.cif_gradient_audit import audit_gradients,FAMILIES
    from nasolve.cif_parallelity_audit import toy_planes
    from nasolve.cif_parallelity_correction import audit_plane_orders,plane_order_evaluator
    from tests.test_cif_parallelity_correction import Vec
    from tests.test_cif_plane_order_correction import OrderAPI
    toy=toy_planes()[0];points=deepcopy(toy['points'])
    weights={family:i+1 for i,family in enumerate(FAMILIES[1:])}
    def evaluate(coordinates,family):
        weight=sum(weights.values()) if family=='all' else weights[family]
        gradient=[2*weight*value for point in coordinates for value in point]
        if biased and family=='parallelity':gradient[0]+=.2
        return {'target':weight*sum(value*value for point in coordinates for value in point),'gradient':gradient,'proxy_counts':{}}
    gradient=audit_gradients(evaluate,{'initial':points},[0],max_calls=2000)
    planes=audit_plane_orders(plane_order_evaluator(OrderAPI(isotropic=True),NS(vec3_double=Vec,size_t=list)),
        {'initial':points},[toy['proxy']],max_pairs=5000)
    return points,gradient,planes,toy['proxy']


def mixed_initial_result(*,biased=False):
    from nasolve.cif_mixed_gradient import POLICY_ID
    from nasolve.cif_parallelity_correction import ORDER_CORRECTION_ID
    points,gradient,planes,proxy=initial_numerical_evidence(biased=biased)
    families=gradient['cases']['initial']['families']
    baseline=deepcopy(families['all']['baseline']);baseline.update(proxy_counts={},terms={})
    expected={'atom_count':len(points),'geometry':{'sites_cart_exact':points,
        'proxy_details':{'parallelity':[deepcopy(proxy)]}},'energy_inventory':{'snapshots':[baseline,deepcopy(baseline)]}}
    repeat={name:[{k:deepcopy(v) for k,v in family['baseline'].items() if k in {'target','gradient','proxy_counts'}}
        for _ in range(3 if name=='all' else 2)] for name,family in families.items()}
    for rows in repeat.values():
        for row in rows:row.setdefault('proxy_counts',{})
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','scientific_qualification':'NOT_ASSESSED',
        'analysis_completed':True,'normalization':False,
        'model_optimization':'NOT_RUN','automatic_adoption':False,'correction_policy_id':ORDER_CORRECTION_ID,
        'constraint_signature_before':'a'*64,'constraint_signature_after':'a'*64,'selected_indices':[0],
        'gradient_audit':gradient,'plane_order_audit':planes,'native_parallelity_proxies':[deepcopy(proxy)],
        'raw_snapshot':deepcopy(baseline),'correction_statistics':{'max_energy_change':0.0,
            'max_plane_residual_difference':0.0,'correction_evaluations':gradient['evaluation_calls']},
        'baseline_evaluations':repeat},expected


@pytest.mark.parametrize('biased',[False,True])
def test_initial_only_validator_recomputes_real_sampled_evidence_and_retains_honest_review(biased):
    from nasolve.cif_mixed_gradient import _validate_result
    result,expected=mixed_initial_result(biased=biased)
    old=deepcopy(result),deepcopy(expected)
    qualification=_validate_result(result,expected,[0])
    assert qualification['sampled_derivatives_pass'] is (not biased)
    assert qualification['status']==('REVIEW' if biased else 'MIXED_INITIAL_DERIVATIVES_PASS')
    assert (result,expected)==old


@pytest.mark.parametrize('defect',['policy','history_case','family','sample_number','sample_bound','gradient_length',
    'raw_target','raw_gradient','energy_changed','static_constraints','native_plane','plane_sample','plane_summary',
    'rotation','missing_rotation','selected','energy_budget','plane_budget','plane_pair_count','optimization','adoption',
    'repeat_gradient','repeat_count','failed_result','scientific_label','evaluation_count'])
def test_initial_result_refuses_forged_or_unbound_numeric_evidence(defect):
    from nasolve.cif_mixed_gradient import _validate_result
    result,expected=mixed_initial_result()
    family=result['gradient_audit']['cases']['initial']['families']['all']
    if defect=='policy':result['policy_id']='OLD_UNRELATED_MANAGER'
    elif defect=='history_case':result['gradient_audit']['cases']['saved_endpoint']=deepcopy(result['gradient_audit']['cases']['initial'])
    elif defect=='family':result['gradient_audit']['cases']['initial']['families'].pop('angle')
    elif defect=='sample_number':family['directions'][0]['samples'][0]['numerical']+=1.
    elif defect=='sample_bound':family['directions'][0]['samples'][0]['bound']*=100
    elif defect=='gradient_length':family['baseline']['gradient'].pop()
    elif defect=='raw_target':result['raw_snapshot']['target']+=1.
    elif defect=='raw_gradient':result['raw_snapshot']['gradient'][0]+=1.
    elif defect=='energy_changed':result['correction_statistics']['max_energy_change']=.01
    elif defect=='static_constraints':result['constraint_signature_after']='b'*64
    elif defect=='native_plane':result['native_parallelity_proxies'][0]['weight']*=2
    elif defect=='plane_sample':result['plane_order_audit']['cases']['initial']['proxies'][0]['original']['directions'][0]['samples'][0]['order_safe']['plus_target']+=1.
    elif defect=='plane_summary':result['plane_order_audit']['cases']['initial']['summary']['orders']+=2
    elif defect=='rotation':result['plane_order_audit']['rotation_controls'][0]['rotation_gradient_consistent']=False
    elif defect=='missing_rotation':result['plane_order_audit']['rotation_controls'].pop()
    elif defect=='selected':result['selected_indices']=[1]
    elif defect=='energy_budget':result['gradient_audit']['max_evaluation_calls']=2001
    elif defect=='plane_budget':result['plane_order_audit']['max_evaluation_pairs']=5001
    elif defect=='plane_pair_count':result['plane_order_audit']['evaluation_pairs']+=1
    elif defect=='optimization':result['model_optimization']='RUN'
    elif defect=='adoption':result['automatic_adoption']=True
    elif defect=='repeat_gradient':result['baseline_evaluations']['all'][1]['gradient'][0]+=1.
    elif defect=='repeat_count':result['baseline_evaluations']['all'].pop()
    elif defect=='failed_result':result['status']='FAILED'
    elif defect=='scientific_label':result['scientific_qualification']='APPROVED'
    else:result['correction_statistics']['correction_evaluations']+=1
    with pytest.raises(ValueError):_validate_result(result,expected,[0])


@pytest.mark.parametrize('seconds',[0,601,True,1.5])
def test_mixed_initial_gradient_timeout_is_bounded_before_any_parent_read(tmp_path,seconds):
    from nasolve.cif_mixed_gradient import audit_mixed_initial_gradients
    with pytest.raises(ValueError):
        audit_mixed_initial_gradients(tmp_path/'context',tmp_path/'linked',None,tmp_path/'out',timeout_seconds=seconds)
    assert not (tmp_path/'out').exists()


def anchored_initial_parent(tmp_path,monkeypatch):
    """Fake only prior qualification; stage and replay maintained job inputs."""
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_mixed_gradient import _ref
    context=tmp_path/'context';context.mkdir();linked=tmp_path/'linked';linked.mkdir()
    _,native,model,_,dictionary=case(context)
    native.update(schema_version=1,policy_id='cif-native-bundle-inventory-v1')
    native['installed_api_sources']=[{'module':'EXPLICIT_FAKE_INTERPRETER','sha256':'a'*64}]
    native['energy_inventory']['installed_sources']=[{'module':'EXPLICIT_FAKE_NUMERIC','sha256':'b'*64}]
    native['geometry'].update(status='RECORDED',custom_proxy_requests=[])
    proxy={'i_seqs':[0,1,2,3],'j_seqs':[4,5,6,7],'weight':3.7,'target_angle_deg':0.,
        'slack':0.,'top_out':False,'origin_id':0}
    proxy.update(atoms=[native['atoms'][i]['label'] for i in proxy['i_seqs']],
        j_atoms=[native['atoms'][i]['label'] for i in proxy['j_seqs']])
    native['geometry']['proxy_details']['parallelity']=[proxy]
    native['geometry']['proxy_counts']['parallelity']=1
    for atom in native['atoms']:
        atom.update(atom_name_field=f'{atom["atom_id"]:>4}',occupancy=1.)
    phil=context/'explicit.phil';phil.write_text('refinement.pdb_interpretation.secondary_structure.enabled = False\n')
    report=context/'mixed_context.json';report.write_text(json.dumps({'status':'MIXED_CONTEXT_MECHANICS_PASS',
        'source_findings':{'status':'REVIEW','message':'Inherited source state remains a note.'}}))
    parent=linked/'mixed_linked_recovery.json';parent.write_text('{"status":"REVIEW"}\n')
    capture=context/'saved_active.json';capture.write_text(json.dumps(native))
    def inputs(context_root,linked_root):
        context_root,linked_root=Path(context_root),Path(linked_root)
        report=context_root/'mixed_context.json';parent=linked_root/'mixed_linked_recovery.json'
        model=context_root/'model.pdb';dictionary=context_root/'projected.cif';phil=context_root/'explicit.phil';capture=context_root/'saved_active.json'
        bound=lambda p:_ref(p,context_root,'context_directory')
        bindings={'context_report':bound(report),'linked_parent_report':_ref(parent,linked_root,'linked_parent_directory'),
            'active_capture':bound(capture),'model':bound(model),'dictionaries':[bound(dictionary)],'phils':[bound(phil)]}
        return json.loads(report.read_bytes()),model,[dictionary],[phil],json.loads(capture.read_bytes()),bindings
    monkeypatch.setattr('nasolve.cif_mixed_gradient._inputs',inputs)
    return context,linked


def test_initial_inspection_stages_trusted_audit_and_relocates_without_native_processes(tmp_path,monkeypatch):
    from nasolve.cif_mixed_gradient import audit_mixed_initial_gradients,read_mixed_initial_gradients
    context,linked=anchored_initial_parent(tmp_path,monkeypatch)
    before={p:p.read_bytes() for root in [context,linked] for p in root.rglob('*') if p.is_file()}
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('inspect-only launched a process'))
    output=tmp_path/'audit';result=audit_mixed_initial_gradients(context,linked,None,output)
    assert result['status']=='PREPARED_ONLY' and result['new_native_calls']==0
    assert result['maximum_native_calls']==1 and result['maximum_energy_calls']==2000 and result['maximum_plane_pairs']==5000
    assert result['preparation']['required_plane_pairs']==364
    assert result['initial_coordinates_only'] and not result['automatic_adoption'] and not result['requires_cif_review']
    assert result['coordinate_decision']['selected']=='verified_constructed_model'
    assert result['coordinate_decision']['native_usable'] is True
    assert all(p.read_bytes()==data for p,data in before.items())
    new_context=tmp_path/'moved_context';new_linked=tmp_path/'moved_linked';new_output=tmp_path/'moved_audit'
    context.rename(new_context);linked.rename(new_linked);output.rename(new_output)
    assert read_mixed_initial_gradients(new_output,context_directory=new_context,linked_parent_directory=new_linked)==result


@pytest.mark.parametrize('defect',['worker','core','spec','plan','input','parent_report','context_report','count',
    'decision','adoption','generation','maximum_calls','status','qualification','extra'])
def test_initial_reader_rejects_rebound_recipe_and_scope_tampering(tmp_path,monkeypatch,defect):
    from nasolve.cif_mixed_gradient import audit_mixed_initial_gradients,read_mixed_initial_gradients,REPORT,_ref
    context,linked=anchored_initial_parent(tmp_path,monkeypatch);output=tmp_path/'audit'
    report=audit_mixed_initial_gradients(context,linked,None,output)
    if defect in {'worker','core','spec','plan','input'}:
        if defect=='worker':ref=report['preparation']['worker']
        elif defect=='core':ref=report['preparation']['cores']['correction_core.py']
        elif defect=='spec':ref=report['preparation']['gradient_spec']
        elif defect=='plan':ref=report['preparation']['probe_plan']
        else:ref=report['preparation']['inputs'][0]['artifact']
        path=output/ref['path']
        if defect=='spec':
            value=json.loads(path.read_bytes());value['max_energy_calls']=3000;path.write_text(json.dumps(value))
        elif defect=='plan':
            value=json.loads(path.read_bytes());value['selected_indices']=[];path.write_text(json.dumps(value))
        else:path.write_bytes(path.read_bytes()+b'\nUNBOUND_CHANGE\n')
        updated=_ref(path,output);report['outputs']=[updated if row['path']==ref['path'] else row for row in report['outputs']]
        ref.update(updated)
    elif defect=='parent_report':
        path=linked/'mixed_linked_recovery.json';path.write_bytes(path.read_bytes()+b'\n')
    elif defect=='context_report':
        path=context/'mixed_context.json';value=json.loads(path.read_bytes());value['source_findings']['status']='APPROVED';path.write_text(json.dumps(value))
    elif defect=='count':report['new_native_calls']=1
    elif defect=='decision':report['coordinate_decision']['selected']='invented_endpoint'
    elif defect=='adoption':report['automatic_adoption']=True
    elif defect=='generation':report['dictionary_generation']='RUN'
    elif defect=='maximum_calls':report['maximum_energy_calls']=3000
    elif defect=='status':report['status']='MIXED_INITIAL_DERIVATIVES_PASS'
    elif defect=='qualification':
        path=output/'forged_qualification.json';path.write_text(json.dumps({'sampled_derivatives_pass':True}))
        report['qualification']={'artifact':_ref(path,output)};report['outputs'].append(_ref(path,output))
    else:(output/'unbound.txt').write_text('EXTRA')
    (output/REPORT).write_text(json.dumps(report))
    with pytest.raises(ValueError):read_mixed_initial_gradients(output,context_directory=context,linked_parent_directory=linked)


def test_optional_launch_failure_retains_the_verified_model_with_notes(tmp_path,monkeypatch):
    import os,sys
    from types import SimpleNamespace as NS
    from nasolve.cif_mixed_gradient import audit_mixed_initial_gradients,read_mixed_initial_gradients
    context,linked=anchored_initial_parent(tmp_path,monkeypatch)
    def failed(*args,**kwargs):raise OSError('EXPLICIT_FAKE_LAUNCH_FAILURE')
    monkeypatch.setattr('subprocess.Popen',failed)
    phenix=NS(executables={'phenix.python':sys.executable},version='EXPLICIT_FAKE',environment=dict(os.environ))
    result=audit_mixed_initial_gradients(context,linked,phenix,tmp_path/'audit')
    assert result['status']=='REVIEW' and result['new_native_calls']==0
    assert result['coordinate_decision']['selected']=='verified_constructed_model'
    assert not result['requires_cif_review'] and result['qualification']=={'status':'NOT_RUN'}
    assert read_mixed_initial_gradients(tmp_path/'audit',context_directory=context,linked_parent_directory=linked)==result


def fake_sdk_parent(tmp_path,monkeypatch,mode):
    """Exercise the new maintained worker against an explicit analytic SDK."""
    from hashlib import sha256
    from tests.test_cif_fixed_geometry import worker_fixture
    from tests.test_cif_parallelity_audit import _FAKE_PLANE_API,evaluate
    from nasolve.cif_mixed_gradient import _NUMERIC,_ADAPTERS
    context,linked=anchored_initial_parent(tmp_path,monkeypatch)
    native=json.loads((context/'saved_active.json').read_bytes())
    proxy={'i_seqs':[0,1,2],'j_seqs':[3,4,5,6],'weight':2.7,'target_angle_deg':0.,
        'slack':0.,'limit':1.,'top_out':False,'origin_id':0}
    expected_proxy={**proxy,'atoms':[native['atoms'][i]['label'] for i in proxy['i_seqs']],
        'j_atoms':[native['atoms'][i]['label'] for i in proxy['j_seqs']]}
    for kind in native['geometry']['proxy_details']:native['geometry']['proxy_details'][kind]=[]
    native['geometry']['proxy_details']['parallelity']=[expected_proxy]
    native['geometry']['simple_bonds']=[];native['geometry']['asu_bonds']=[]
    native['geometry']['proxy_counts']={k:len(v) for k,v in native['geometry']['proxy_details'].items()}
    seed=worker_fixture(tmp_path/'fake_sdk',native,'limit')
    kinds=['bond','angle','dihedral','chirality','planarity','parallelity','nonbonded']
    (seed/'cctbx/geometry_restraints/flags.py').write_text('class flags:\n def __init__(self,default=False):\n'+''.join(f'  self.{k}=default\n' for k in kinds))
    (seed/'cctbx/array_family/flex.py').write_text('from fake_arrays import Vec\ndef vec3_double(values,fill=None):return Vec([fill]*values if isinstance(values,int) else values)\ndef size_t(v):return list(v)\n')
    api=_FAKE_PLANE_API.replace('BROKEN = False','BROKEN = True').replace('def parallelity_proxy(**kw):return NS(**kw,sym_ops=None)',
        "def parallelity_proxy(**kw):\n p=kw.pop('proxy',None);values={k:v for k,v in vars(p).items() if k!='sym_ops'} if p else {};values.update(kw);return NS(**values,sym_ops=None)")
    (seed/'cctbx/geometry_restraints/__init__.py').write_text(api)
    for name in ['parallelity.h','parallelity_bpl.cpp']:(seed/'cctbx/geometry_restraints'/name).write_text('EXPLICIT_FAKE_'+name+'\n')
    manager='''from types import SimpleNamespace as NS
from cctbx import geometry_restraints as gr
from cctbx.array_family import flex
class Geo:
    site_symmetry_table=NS(special_position_indices=lambda:[])
    angle_proxies=[];dihedral_proxies=[];const_dihedral_proxies=[];chirality_proxies=[];planarity_proxies=[]
    parallelity_proxies=gr.shared_parallelity_proxy([gr.parallelity_proxy(**PROXY)])
    def pair_proxies(self,sites_cart):return NS(bond_proxies=NS(simple=[],asu=[]))
    def energies_sites(self,sites_cart,flags,compute_gradients,normalization):
        assert compute_gradients and normalization is False
        coefficient=sum(1 for k in KINDS if getattr(flags,k))
        gradient=flex.vec3_double(len(sites_cart),(0.,0.,0.));parallel=0.
        if flags.parallelity:parallel=gr.parallelity_residual_sum(sites_cart,self.parallelity_proxies,gradient)
        for i,point in enumerate(sites_cart):gradient[i]=tuple(a+2*coefficient*v for a,v in zip(gradient[i],point))
        return NS(target=coefficient*sum(v*v for p in sites_cart for v in p)+parallel,gradients=gradient,
            parallelity_residual_sum=parallel,n_parallelity_proxies=len(self.parallelity_proxies) if flags.parallelity else 0)
'''.replace('PROXY',repr(proxy)).replace('KINDS',repr([k for k in kinds if k!='parallelity']))
    (seed/'cctbx/geometry_restraints/manager.py').write_text(manager)
    def fingerprint(name):
        suffix=name.replace('.','/')+'.py';p=seed/suffix
        return {'module':name,'historical_path':str(p),'sha256':sha256(p.read_bytes()).hexdigest()}
    native['energy_inventory']['installed_sources']=[fingerprint(n) for n in ['cctbx.geometry_restraints.flags','cctbx.geometry_restraints.energies','cctbx.geometry_restraints.manager']]
    points=native['geometry']['sites_cart_exact'];plane=evaluate(points,proxy,broken=True)
    raw=[12*x+g for x,g in zip([v for p in points for v in p],plane['accumulated_gradient'])]
    from math import sqrt,fsum
    snapshot={'target':6*sum(v*v for p in points for v in p)+plane['accumulated_target'],
        'gradient':raw,'gradient_norm':sqrt(fsum(x*x for x in raw)),
        'terms':{'parallelity_residual_sum':plane['accumulated_target']},'proxy_counts':{'n_parallelity_proxies':1}}
    native['energy_inventory']['snapshots']=[snapshot,deepcopy(snapshot)]
    (context/'saved_active.json').write_text(json.dumps(native))
    bootstrap='''import json,os
from pathlib import Path
from cctbx.array_family import flex
from cctbx.geometry_restraints.manager import Geo
report=json.loads(Path(os.environ['EXPLICIT_FAKE_NATIVE']).read_text())
if MODE=='manager':report['atoms'][0]['atom_id']='CHANGED'
sites=flex.vec3_double(report['geometry']['sites_cart_exact']);geo=Geo()
Path('native_validation.json').write_text(json.dumps(report))
'''.replace('MODE',repr(mode))
    import nasolve.cif_native_validation as native_module
    monkeypatch.setattr(native_module,'_NATIVE_WORKER',bootstrap)
    # Energy inventory insertion is separately tested; this explicit fake
    # bootstrap already supplies the two analytic raw snapshots above.
    monkeypatch.setattr('nasolve.cif_candidate_usability.native_energy_worker',lambda base:base)
    if mode=='timeout':
        import nasolve.cif_mixed_gradient as module
        monkeypatch.setattr(module,'_WORKER','import time\ntime.sleep(30)\n')
    return context,linked,seed


@pytest.mark.parametrize('mode',['correct','manager','timeout'])
def test_owned_fake_sdk_job_runs_the_new_worker_and_never_optimizes(tmp_path,monkeypatch,mode):
    import os,sys
    from types import SimpleNamespace as NS
    from nasolve.cif_mixed_gradient import audit_mixed_initial_gradients,read_mixed_initial_gradients
    context,linked,seed=fake_sdk_parent(tmp_path,monkeypatch,mode)
    env={**os.environ,'PYTHONPATH':str(seed),'EXPLICIT_FAKE_NATIVE':str(context/'saved_active.json')}
    phenix=NS(executables={'phenix.python':sys.executable},version='EXPLICIT_FAKE',environment=env)
    result=audit_mixed_initial_gradients(context,linked,phenix,tmp_path/'audit',timeout_seconds=1 if mode=='timeout' else 30)
    assert result['new_native_calls']==1 and not result['automatic_adoption']
    assert result['status']==('MIXED_INITIAL_DERIVATIVES_PASS' if mode=='correct' else 'REVIEW'),result.get('error')
    assert result['execution']['status']=={'correct':'COMPLETED','manager':'FAILED','timeout':'TIMED_OUT'}[mode]
    assert not list(tmp_path.rglob('fake_optimizer_called'))
    assert result['coordinate_decision']['selected']=='verified_constructed_model'
    assert read_mixed_initial_gradients(tmp_path/'audit',context_directory=context,linked_parent_directory=linked)==result
    if mode=='correct':
        import shutil
        relocated=tmp_path/'relocated';relocated.mkdir()
        context.rename(relocated/'context');linked.rename(relocated/'linked');(tmp_path/'audit').rename(relocated/'audit')
        shutil.rmtree(seed)
        monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('saved reader launched an SDK'))
        assert read_mixed_initial_gradients(relocated/'audit',context_directory=relocated/'context',
            linked_parent_directory=relocated/'linked')==result


@pytest.mark.parametrize('defect',['native_energy','numeric_pin','numeric_repeat','correction_core',
    'cpp_bytes','qualification','special_position','coordinates','counter'])
def test_completed_reader_replays_fresh_capture_sources_and_numeric_result_origins(tmp_path,monkeypatch,defect):
    import os,sys
    from types import SimpleNamespace as NS
    from nasolve.cif_mixed_gradient import audit_mixed_initial_gradients,read_mixed_initial_gradients,REPORT,_ref
    context,linked,seed=fake_sdk_parent(tmp_path,monkeypatch,'correct');output=tmp_path/'audit'
    phenix=NS(executables={'phenix.python':sys.executable},version='EXPLICIT_FAKE',
        environment={**os.environ,'PYTHONPATH':str(seed),'EXPLICIT_FAKE_NATIVE':str(context/'saved_active.json')})
    report=audit_mixed_initial_gradients(context,linked,phenix,output,timeout_seconds=30)
    assert report['status']=='MIXED_INITIAL_DERIVATIVES_PASS'
    if defect=='native_energy':
        path=output/'job/native_validation.json';value=json.loads(path.read_bytes())
        value['energy_inventory']['snapshots'][0]['target']+=1.;path.write_text(json.dumps(value))
    elif defect=='cpp_bytes':
        path=output/'job/installed_source/parallelity.h';path.write_bytes(path.read_bytes()+b'CHANGED\n')
    elif defect=='qualification':
        path=output/report['qualification']['artifact']['path'];value=json.loads(path.read_bytes())
        value['checks']['captured_raw_snapshot']=False;path.write_text(json.dumps(value))
        report['qualification']['artifact']=_ref(path,output)
    elif defect=='counter':
        report['new_native_calls']=0;path=None
    else:
        path=output/'job/gradient_result.json';value=json.loads(path.read_bytes())
        if defect=='numeric_pin':
            for field in ['installed_numeric_sources','installed_numeric_sources_after']:
                next(r for r in value[field] if r['module']=='cctbx.geometry_restraints.flags')['sha256']='0'*64
        elif defect=='numeric_repeat':value['installed_numeric_sources_after'][0]['sha256']='0'*64
        elif defect=='correction_core':value['correction_core_sha256']='0'*64
        elif defect=='special_position':value['special_position_indices']=[0]
        elif defect=='coordinates':value['coordinates_unchanged']=False
        path.write_text(json.dumps(value))
    if path is not None:
        updated=_ref(path,output);report['outputs']=[updated if row['path']==updated['path'] else row for row in report['outputs']]
    (output/REPORT).write_text(json.dumps(report))
    with pytest.raises(ValueError):read_mixed_initial_gradients(output,context_directory=context,linked_parent_directory=linked)
