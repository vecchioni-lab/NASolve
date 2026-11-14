"""A resolved middle scale must qualify without relaxing derivative evidence."""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import subprocess

import pytest

from nasolve import cif_mixed_endpoint_window as policy
from tests.test_cif_mixed_endpoint import (
    coherent_torsion_parent, refinement_fixture, original_boundary_fixture,
    _endpoint_parent_bytes, _rebind_endpoint_artifact, C92_PARENT_SHA256, C91_PARENT_SHA256,
)


def narrow_window():
    """Analytic cubic with cancellation; no crystallographic/model coordinates."""
    points=[[1.1,.55,1.1/3.]]
    direction=[-1/math.sqrt(3),1/math.sqrt(3),-1/math.sqrt(3)]
    gradient=[1000.,2000.,999.]
    def evaluate(p):
        delta=[x-y for q,r in zip(p,points) for x,y in zip(q,r)]
        t=math.fsum(x*y for x,y in zip(direction,delta))
        return {'target':math.fsum(x*y for x,y in zip(gradient,delta))+3.e10*t**3,
                'gradient':[g+9.e10*t*t*d for g,d in zip(gradient,direction)]}
    return points,direction,evaluate


def current_fixture():
    cases,plan,family,local=refinement_fixture()
    plan.update(policy_id=policy.POLICY_ID,step_sizes=list(policy.STEPS))
    return cases,plan,family,local


def test_missing_middle_scale_resolves_a_real_sampling_gap_without_changing_tolerance():
    from nasolve.cif_mixed_endpoint import refine_direction as previous
    points,direction,evaluate=narrow_window();before=deepcopy(points)
    old=previous(evaluate,points,direction,evaluate(points))
    result=policy.refine_direction(evaluate,points,direction,evaluate(points))
    assert old['consistent'] is False
    assert [s['consistent'] for s in old['samples']]==[False,True,False,False,False,False]
    assert result['consistent'] is True
    passing=[s['step'] for s in result['samples'] if s['consistent']]
    assert passing==[3.e-8,1.e-8]
    assert result['tolerance']==old['tolerance']=={'absolute':1e-4,'relative':1e-4}
    assert points==before
    assert {s['step'] for s in old['samples']} < {s['step'] for s in result['samples']}
    # The unresolved tiny steps remain failures even if arithmetic is close.
    assert any(not s['guards']['representation_uncertainty_resolved'] for s in result['samples'][3:])


@pytest.mark.parametrize('mode',['wrong_gradient','unrepresentable','nonfinite'])
def test_a_middle_step_cannot_rescue_wrong_or_unresolved_evidence(mode):
    points,direction,evaluate=narrow_window();base=evaluate(points)
    if mode=='wrong_gradient':base['gradient'][0]+=100.
    elif mode=='unrepresentable':
        points=[[1.e20,1.e20,1.e20]]
        evaluate=lambda p:{'target':math.fsum(v for q in p for v in q),'gradient':[1.,1.,1.]}
        base=evaluate(points)
    else:base['gradient'][0]=float('nan')
    if mode=='nonfinite':
        with pytest.raises(ValueError):policy.refine_direction(evaluate,points,direction,base)
    else:assert policy.refine_direction(evaluate,points,direction,base)['consistent'] is False


def test_current_audit_replays_every_new_observation_in_canonical_case_order():
    cases,plan,family,local=current_fixture()
    result=policy.audit_endpoint_refinement(family,local,cases,plan)
    assert result['status']=='ADAPTIVE_ENDPOINT_DERIVATIVES_PASS'
    assert result['evaluation_calls']==len(result['observations'])==78
    assert result['step_sizes']==[1.e-7,3.e-8,1.e-8,3.e-9,1.e-9,3.e-10,1.e-10]
    assert policy.replay_endpoint_refinement(result,json.loads(json.dumps(cases,sort_keys=True)),plan)['status']==result['status']
    assert policy.MAX_DIRECTIONS==120 and policy.MAX_EVALUATIONS==2000
    assert 48+policy.MAX_DIRECTIONS*(2+2*len(policy.STEPS))<=policy.MAX_EVALUATIONS


@pytest.mark.parametrize('defect',['middle_target','middle_request','middle_step','declared_grid','tolerance','guard','drop','extra','count','old_scope'])
def test_new_reader_does_not_accept_rebound_middle_sample_or_coverage_claims(defect):
    cases,plan,family,local=current_fixture()
    result=policy.audit_endpoint_refinement(family,local,cases,plan)
    if defect=='middle_target':result['observations'][50]['value']['target']+=1.
    elif defect=='middle_request':result['observations'][50]['request']['points_sha256']='a'*64
    elif defect=='middle_step':result['families'][0]['evidence']['samples'][1]['step']=2.e-8
    elif defect=='declared_grid':result['step_sizes'][1]=2.e-8
    elif defect=='tolerance':result['families'][0]['evidence']['tolerance']['absolute']+=1.e-9
    elif defect=='guard':result['families'][0]['evidence']['samples'][1]['guards']['representation_uncertainty_resolved']=False
    elif defect=='drop':result['observations'].pop(50)
    elif defect=='extra':result['observations'].append(deepcopy(result['observations'][50]))
    elif defect=='count':result['evaluation_calls']-=1
    else:result['summary']['retained_original_passing_directions']+=1
    with pytest.raises(ValueError):policy.replay_endpoint_refinement(result,cases,plan)


def test_legacy_positive_scope_and_exact_failed_direction_are_unchanged():
    from nasolve.cif_mixed_endpoint import refinement_plan as previous
    args=original_boundary_fixture();before=deepcopy(args)
    old=previous(*args);new=policy.refinement_plan(*args)
    assert new['families']==old['families'] and new['local']==old['local']
    assert new['original_direction_count']==old['original_direction_count']==96
    assert new['retained_original_passing_directions']==old['retained_original_passing_directions']==95
    assert new['references']==old['references'] and new['prerequisites']==old['prerequisites']
    assert new['policy_id']!=old['policy_id'] and args==before


def read(output,parents):
    return policy.read_saved_mixed_endpoint(output,torsion_directory=parents[0],geometry_directory=parents[1],
        gradient_directory=parents[2],context_directory=parents[3],linked_parent_directory=parents[4],
        parent_archive_sha256=C92_PARENT_SHA256)


@pytest.mark.parametrize('mode',['correct','manager','source','missing_result','timeout','launch_failure','readback_failure'])
def test_actual_window_worker_preserves_all_inputs_and_selects_only_qualified_native_readback(tmp_path,monkeypatch,mode):
    *parents,sdk,phenix=coherent_torsion_parent(tmp_path,monkeypatch)
    before=_endpoint_parent_bytes(*parents);original_popen=subprocess.Popen
    if mode=='manager':phenix.environment['EXPLICIT_C90_MISMATCH']='1'
    elif mode=='source':
        p=sdk/'cctbx/geometry_restraints/__init__.py';p.write_bytes(p.read_bytes()+b'\n# EXPLICIT_C93_SOURCE_DRIFT\n')
    elif mode=='timeout':phenix.environment['EXPLICIT_C91_TIMEOUT']='1'
    elif mode=='launch_failure':
        def fail(*args,**kwargs):raise OSError('EXPLICIT_C93_LAUNCH_FAILURE')
        monkeypatch.setattr(subprocess,'Popen',fail)
    elif mode=='readback_failure':
        def fail_readback(command,**kwargs):
            if 'native_worker.py' in command:kwargs={**kwargs,'env':{**kwargs['env'],'EXPLICIT_C90_MISMATCH':'1'}}
            return original_popen(command,**kwargs)
        monkeypatch.setattr(subprocess,'Popen',fail_readback)
    elif mode=='missing_result':
        class Missing:
            def __init__(self,p,cwd):self.p,self.cwd=p,Path(cwd)
            def __getattr__(self,n):return getattr(self.p,n)
            def wait(self,**kwargs):
                code=self.p.wait(**kwargs)
                for p in self.cwd.glob('*result.json'):p.unlink()
                return code
        monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:Missing(original_popen(*a,**k),k['cwd']))
    output=tmp_path/'window'
    report=policy.qualify_saved_mixed_endpoint(*parents,phenix,output,parent_archive_sha256=C92_PARENT_SHA256,
        timeout_seconds=1 if mode=='timeout' else 30)
    assert report['model_optimization']=='NOT_RUN' and not report['automatic_adoption'] and not report['requires_cif_review']
    assert all(p.read_bytes()==data for p,data in before.items())
    assert not any(p.name=='fake_optimizer_called' for p in output.rglob('*'))
    if mode=='correct':
        assert report['status']=='MIXED_ENDPOINT_QUALIFIED',report
        assert report['new_native_calls']==2 and report['coordinate_decision']['selected']=='qualified_geometry_endpoint'
        saved=json.loads((output/'job/endpoint_result.json').read_bytes())
        assert saved['audit']['step_sizes']==list(policy.STEPS)
        moved=tmp_path/'moved';moved.mkdir();new_parents=[]
        for name,p in zip(['torsion','geometry','gradient','context','linked'],parents):p.rename(moved/name);new_parents.append(moved/name)
        output.rename(moved/'window');output=moved/'window';parents=new_parents;shutil.rmtree(sdk)
    else:
        assert report['status']=='REVIEW' and report['coordinate_decision']['selected']=='verified_constructed_model'
        assert report['coordinate_decision']['continue_solving'] is True
        assert report['new_native_calls']==(0 if mode=='launch_failure' else 2 if mode=='readback_failure' else 1)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('saved reader launched a process'))
    assert read(output,parents)==report


@pytest.mark.parametrize('defect',['worker','core','plan','spec','policy','parent','approval'])
def test_window_reader_rejects_changed_recipes_and_status_scope(tmp_path,monkeypatch,defect):
    *parents,_,_=coherent_torsion_parent(tmp_path,monkeypatch);output=tmp_path/'window'
    report=policy.qualify_saved_mixed_endpoint(*parents,None,output,parent_archive_sha256=C92_PARENT_SHA256)
    before=_endpoint_parent_bytes(*parents)
    relative={'worker':'job/endpoint_worker.py','core':'job/endpoint_core.py','plan':'refinement_plan.json','spec':'job/endpoint_spec.json'}.get(defect)
    if relative:
        p=output/relative;p.write_bytes(p.read_bytes()+b'\nEXPLICIT_CHANGED_WINDOW_RECIPE\n')
        _rebind_endpoint_artifact(report,relative,p.read_bytes(),policy.ANCHOR)
    elif defect=='policy':report['policy_id']='cif-mixed-saved-endpoint-qualification-v1'
    elif defect=='parent':report['parent_archive_sha256']='a'*64
    else:report['requires_cif_review']=True
    (output/policy.REPORT).write_text(json.dumps(report))
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('reader launched a process'))
    with pytest.raises(ValueError):read(output,parents)
    assert all(p.read_bytes()==data for p,data in before.items())


def test_window_worker_refines_both_native_orders_of_local_boundary_evidence(tmp_path, monkeypatch):
    """Exercise the local worker path using genuine captured negative evidence.

    The explicit fake native API can simulate a coarse local finite-difference
    failure under one environment flag. Its source bytes and exact baseline
    remain unchanged across the initial qualification, C91 capture and C92 run.
    No production evaluator, worker or result arithmetic is mocked.
    """
    from tests import test_cif_dihedral_conditioning as fake_module
    from nasolve.cif_mixed_torsion import audit_mixed_torsions
    from nasolve.cif_mixed_endpoint_window import qualify_saved_mixed_endpoint
    original = '    def residual(self):return self.proxy.weight*sum(v*v for i in self.proxy.i_seqs for v in self.points[i])'
    replacement = '''    def residual(self):
        value=self.proxy.weight*sum(v*v for i in self.proxy.i_seqs for v in self.points[i])
        import os,json
        from pathlib import Path
        if os.environ.get('EXPLICIT_FAKE_LOCAL_BOUNDARY') and len(self.points)==4 and Path('torsion_spec.json').is_file():
            spec=json.loads(Path('torsion_spec.json').read_bytes());references=[]
            for points in spec['coordinate_cases'].values():
                for row in spec['selection']['selected']:
                    selected=[points[i] for i in row['proxy']['i_seqs']]
                    references.extend([selected,selected[::-1]])
            current=[list(p) for p in self.points]
            nearest=min(references,key=lambda rows:sum((a-b)**2 for p,q in zip(current,rows) for a,b in zip(p,q)))
            if current[0][0]>nearest[0][0]:value+=1.
        return value'''
    assert original in fake_module._FAKE_DIHEDRAL_API
    monkeypatch.setattr(fake_module, '_FAKE_DIHEDRAL_API', fake_module._FAKE_DIHEDRAL_API.replace(original,replacement))
    _, geometry, gradient, context, linked, _, phenix = coherent_torsion_parent(tmp_path,monkeypatch)
    phenix.environment['EXPLICIT_FAKE_LOCAL_BOUNDARY']='1'
    torsion=tmp_path/'torsion_boundary'
    captured=audit_mixed_torsions(geometry,gradient,context,linked,phenix,torsion,
        parent_archive_sha256=C91_PARENT_SHA256,timeout_seconds=30)
    assert captured['status']=='MIXED_TORSION_AUDIT_COMPLETE'
    assert any(not row['local_sampled_agreement'] for row in captured['summary']['cases'].values())
    del phenix.environment['EXPLICIT_FAKE_LOCAL_BOUNDARY']
    parents=[torsion,geometry,gradient,context,linked];before=_endpoint_parent_bytes(*parents)
    output=tmp_path/'endpoint_local'
    report=qualify_saved_mixed_endpoint(*parents,phenix,output,parent_archive_sha256=C92_PARENT_SHA256,timeout_seconds=30)
    assert report['status']=='MIXED_ENDPOINT_QUALIFIED',report
    assert report['new_native_calls']==2
    assert report['summary']['refined_local_directions']>0
    result=json.loads((output/'job/endpoint_result.json').read_bytes())
    rows=result['audit']['local'];assert {r['selection']['order'] for r in rows}=={'forward','reversed'}
    assert all(r['single']['consistent'] and r['accumulated']['consistent'] and all(r['checks'].values()) for r in rows)
    assert all(path.read_bytes()==data for path,data in before.items())
    assert not any(p.name=='fake_optimizer_called' for p in output.rglob('*'))
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('reader launched a native process'))
    assert read(output,parents)==report
