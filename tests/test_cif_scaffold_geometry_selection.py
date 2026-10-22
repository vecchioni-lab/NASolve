"""A failed/nonconverged coordinate trial never discards a usable fixed bundle."""
from copy import deepcopy
from nasolve.cif_gradient_audit import audit_gradients,FAMILIES
import pytest


def case(rounded_points=None):
    weights={f:i+1 for i,f in enumerate(FAMILIES[1:])}
    def evaluate(points,family):
        w=sum(weights.values()) if family=='all' else weights[family]
        return {'target':w*sum(v*v for p in points for v in p),'gradient':[2*w*v for p in points for v in p]}
    points=[[.2,.1,.3],[.4,.1,.2]];audit=audit_gradients(evaluate,{'full_precision':points,'pdb_rounded':points if rounded_points is None else rounded_points},[0],max_calls=2000)
    baseline=audit['cases']['full_precision']['families']['all']['baseline'];initial={**baseline,'target':baseline['target']+1}
    q={'policy_id':'cif-qualified-scaffold-candidate-v1','component':'ZZZ','model_sha256':'a'*64,'native_usable':True,
       'status':'SCAFFOLD_CANDIDATE_MECHANICS_PASS','checks':[{'check':'trusted-initial-context','status':'PASS'}]}
    result={'policy_id':'cif-fixed-na-corrected-geometry-trial-v1','captured_inventory_matches':True,'qualified_initial_snapshot_matches':True,
       'normalization':False,'starting_coordinates':'CAPTURED_INITIAL','constraint_signature_before':'c'*64,'constraint_signature_after':'c'*64,
       'initial':initial,'final':baseline,'serialized':audit['cases']['pdb_rounded']['families']['all']['baseline'],'final_sites_cart':points,'endpoint_gradient_audit':audit,
       'endpoint_derivative_qualification':'SAMPLED_NATIVE_DERIVATIVES_PASS','stopping':{'reason':'max_iterations','native_criterion_met':False,'error':None}}
    trial={'status':'REVIEW','execution':{'status':'COMPLETED','returncode':0},'source_preserved':True,'frozen_inputs_preserved':True,'result':result}
    mechanics={'mechanics_checks_pass':True,'checks':[{'check':'trusted-roundtrip','status':'PASS'}]}
    review={'analysis_completed':True,'atom_count':2,'summary':{'chirality':{'sign_conflicts':0}}}
    serialization={'source_preserved':True,'source_sha256':'a'*64,'candidate_sha256':'b'*64,'atom_count':2,
       'atom_correspondence':'EXACT_IDENTITY_BIJECTION','metadata_and_headers_preserved':True}
    return q,trial,mechanics,review,serialization


@pytest.mark.parametrize('defect',['none','nonconverged_error','pucker_note','failed_worker','timeout','changed_inputs','mechanics','hand_inversion','rounded_hand_inversion','derivative','forged_sample','signature','higher_target','nan','model_binding','identity'])
def test_selects_qualified_endpoint_or_usable_initial_without_student_gate(defect):
    from nasolve.cif_scaffold_candidate import select_scaffold_geometry
    q,t,m,r,s=case();v=t['result']
    if defect=='nonconverged_error':v['stopping'].update(reason='unreported',error='rounding errors prevent progress')
    if defect=='pucker_note':r['sugar_pucker']='CHANGED_UNASSESSED'
    if defect=='failed_worker':t['status']='FAILED'
    if defect=='timeout':t['execution']['status']='TIMED_OUT'
    if defect=='changed_inputs':t['frozen_inputs_preserved']=False
    if defect=='mechanics':m['checks'][0]['status']='REVIEW'
    if defect=='hand_inversion':r['summary']['chirality']['sign_conflicts']=1
    if defect=='derivative':v['endpoint_derivative_qualification']='DERIVATIVE_REVIEW'
    if defect=='forged_sample':v['endpoint_gradient_audit']['cases']['full_precision']['families']['all']['directions'][0]['samples'][0]['plus_target']+=1
    if defect=='signature':v['constraint_signature_after']='d'*64
    if defect=='higher_target':v['final']={**v['final'],'target':v['initial']['target']+1}
    if defect=='nan':v['final_sites_cart'][0][0]=float('nan')
    if defect=='model_binding':s['source_sha256']='f'*64
    if defect=='identity':s['atom_correspondence']='POSITION_ONLY'
    rounded=deepcopy(r)
    if defect=='rounded_hand_inversion':rounded['summary']['chirality']['sign_conflicts']=1
    d=select_scaffold_geometry(q,t,m,r,s,atom_count=2,rounded_geometry_review=rounded)
    assert d['selected_candidate']==('qualified_geometry_endpoint' if defect in {'none','nonconverged_error','pucker_note'} else 'verified_initial_scaffold'),d
    assert d['continue_solving'] and d['status']=='CONTINUE_WITH_NOTES'
    assert not d['requires_cif_review'] and not d['automatic_adoption']


def test_failed_trial_can_return_usable_initial_without_any_endpoint():
    from nasolve.cif_scaffold_candidate import select_scaffold_geometry
    q,*_=case();d=select_scaffold_geometry(q,None,None,None,None,atom_count=2)
    assert d['selected_candidate']=='verified_initial_scaffold' and d['continue_solving']


def test_unverified_initial_is_not_invented_as_a_fallback():
    from nasolve.cif_scaffold_candidate import select_scaffold_geometry
    q,*_=case();q['native_usable']=False
    with pytest.raises(ValueError):select_scaffold_geometry(q,None,None,None,None,atom_count=2)


def test_written_pdb_must_not_worsen_the_same_fixed_objective():
    from nasolve.cif_scaffold_candidate import select_scaffold_geometry
    q,t,m,r,s=case([[.201,.1,.3],[.4,.1,.2]])
    result=t['result'];result['initial']['target']=(result['final']['target']+result['serialized']['target'])/2
    assert result['final']['target']<result['initial']['target']<result['serialized']['target']
    d=select_scaffold_geometry(q,t,m,r,s,atom_count=2,rounded_geometry_review=r)
    assert d['selected_candidate']=='verified_initial_scaffold'
