"""Saved native replay uses data and maintained code, preserving raw failures."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from tests.test_cif_native_usability_representation import constant_case


def saved(tmp_path):
    from nasolve.cif_candidate_usability import native_energy_worker,reassess_complete_candidate
    from nasolve.cif_native_validation import _NATIVE_WORKER
    spec=importlib.util.spec_from_file_location('probe56',Path(__file__).parents[1]/'scripts/cif_numerical_recovery_probe_template.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    s,c,model,n=constant_case(tmp_path)
    (tmp_path/'source.cif').write_bytes(s.read_bytes());(tmp_path/'candidate.cif').write_bytes(c.read_bytes())
    s,c=tmp_path/'source.cif',tmp_path/'candidate.cif'
    n['geometry']['sites_cart_exact']=deepcopy(n['geometry']['sites_cart_exact']);n['geometry']['sites_cart_exact'][0][0]+=2e-15
    members={'saved/source.cif':s.read_bytes(),'saved/candidate.cif':c.read_bytes()};pins=[];proof=[]
    for module in ['flags','energies','manager']:
        data=b'# EXPLICIT FAKE NATIVE SOURCE: NOT EXECUTABLE EVIDENCE\n';path='site/cctbx/geometry_restraints/'+module+'.py';name='native_sources/'+module+'.py';members[name]=data
        pins.append({'anchor':'phenix_installation','path':path,'sha256':sha256(data).hexdigest(),'snapshot':{'anchor':'probe_directory','path':name}})
        proof.append({'module':'cctbx.geometry_restraints.'+module,'historical_path':'/FAKE_PHENIX/'+path,'sha256':sha256(data).hexdigest()})
    n['energy_inventory']['installed_sources']=proof
    old=reassess_complete_candidate(s,c,'Q17');old['policy_id']='cif-isolated-candidate-native-usability-v1'
    row={'candidate':{'anchor':'probe_directory','path':'saved/candidate.cif','size':len(c.read_bytes()),'sha256':sha256(c.read_bytes()).hexdigest()},
        'assessment':old,'coordinate_cases':{},'decision':{'status':'NO_USABLE_DICTIONARY','continue_solving':False}}
    for label in ['source_seed','generated_output']:
        prefix='native/'+label;inputs=[]
        for name,data,role in [('inputs/model.pdb',model.read_bytes(),'model'),('inputs/component.cif',c.read_bytes(),'dictionary')]:
            members[prefix+'/'+name]=data;inputs.append({'anchor':'native_directory','path':name,'size':len(data),'sha256':sha256(data).hexdigest(),'role':role})
        native={'directory':{'anchor':'probe_directory','path':prefix},'status':'REVIEW','source_preserved':True,'frozen_inputs_preserved':True,
            'execution':{'status':'COMPLETED','returncode':0,'timeout_seconds':60},'native_validation':deepcopy(n),'inputs':inputs,'outputs':[]}
        members[prefix+'/native_worker.py']=native_energy_worker(_NATIVE_WORKER).encode()
        members[prefix+'/native_spec.json']=json.dumps({'energy_inventory':True,'inventory_detail':'linked','policy_inventory':True}).encode()
        row['coordinate_cases'][label]={'native':native,'qualification':{'policy_id':'cif-isolated-candidate-native-usability-v1','native_usable':False,
            'checks':{'exact_native_sites':False},'evidence':{'error':'ZeroDivisionError: float division by zero'},'source_assessment':deepcopy(old)}}
    a={'policy_id':'cif-isolated-candidate-native-usability-v1','native_execution':'ISOLATED_CANDIDATE_NATIVE_USABILITY','scope':'ISOLATED_COMPONENT_ONLY',
        'automatic_adoption':False,'requires_cif_review':False,'energy_sources':pins,'cases':{'Q17':row}}
    r={'candidate_usability_audit':a,'prior_complete_candidate_replay':{'Q17':{'stopping':'NOT_CONVERGED_REPORTED'}}}
    return m,members,r


def refresh(members,r):
    for c in r['candidate_usability_audit']['cases'].values():
        for case in c['coordinate_cases'].values():
            n=case['native'];prefix=n['directory']['path'];members[prefix+'/native_validation.json']=json.dumps(n['native_validation']).encode()
            n['outputs']=[{'anchor':'native_directory','path':name[len(prefix)+1:],'size':len(data),'sha256':sha256(data).hexdigest()} for name,data in members.items() if name.startswith(prefix+'/') and not name.endswith('/native_receipt.json')]
            members[prefix+'/native_receipt.json']=json.dumps({k:v for k,v in n.items() if k!='directory'}).encode()
    members['candidate_usability_audit.json']=json.dumps(r['candidate_usability_audit']).encode();members['probe_receipt.json']=json.dumps(r).encode()


@pytest.mark.parametrize('defect',['none','worker','snapshot','spec','candidate_bytes','native_copy','execution','legacy_error','scope','unsafe_input','active_target','gradient'])
def test_saved_worker_and_sources_stay_pinned_while_verified_evidence_controls_selection(tmp_path,defect):
    m,members,r=saved(tmp_path);c=r['candidate_usability_audit']['cases']['Q17'];record=c['coordinate_cases']['source_seed'];n=record['native'];prefix=n['directory']['path']
    if defect=='worker':members[prefix+'/native_worker.py']=b'raise RuntimeError("CAPTURED CODE MUST NOT EXECUTE")\n'
    if defect=='snapshot':members['native_sources/manager.py']+=b'CHANGED'
    if defect=='spec':members[prefix+'/native_spec.json']=json.dumps({'energy_inventory':False}).encode()
    if defect=='candidate_bytes':members['saved/candidate.cif']+=b'CHANGED'
    if defect=='execution':n['execution']['returncode']=1
    if defect=='legacy_error':record['qualification']['evidence']['error']='HIDDEN'
    if defect=='scope':c['coordinate_cases'].pop('generated_output')
    if defect=='unsafe_input':n['inputs'][0]['path']='../escape'
    if defect=='active_target':n['native_validation']['geometry']['proxy_details']['angle'][0]['angle_ideal']+=1
    if defect=='gradient':n['native_validation']['energy_inventory']['snapshots'][0]['gradient'][0]+=1
    refresh(members,r)
    if defect=='native_copy':members[prefix+'/native_validation.json']=b'{}'
    if defect in {'none','active_target','gradient'}:
        out=m._replay_saved_usability(members)['Q17'];assert out['decision']['continue_solving'] is (defect=='none')
        assert out['legacy_decision']['status']=='NO_USABLE_DICTIONARY' and not out['decision']['requires_cif_review']
        assert out['decision']['linked_adoption']=='NOT_RUN'
    else:
        with pytest.raises((ValueError,KeyError)):m._replay_saved_usability(members)


@pytest.mark.parametrize('delivery,option',[('55_Cedar','saved_native_usability_only'),('54_Cedar','candidate_native_usability_only'),('53_Cedar','source_candidate_generation_only')])
def test_saved_action_never_repeats_generation_or_native_interpretation(tmp_path,delivery,option):
    m,_,_=saved(tmp_path);args=SimpleNamespace(**{option:True});m._check_constructor_input_mode(args,delivery)
    args.saved_native_usability_only=not getattr(args,'saved_native_usability_only',False)
    with pytest.raises(ValueError):m._check_constructor_input_mode(args,delivery)
