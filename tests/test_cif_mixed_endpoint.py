"""Independent regressions for saved-endpoint finite-step qualification."""
from copy import deepcopy
import math
import pytest


@pytest.mark.parametrize('sigma,expected_flags,qualified',[(1.e-7,[False,False,False,True,True,True],True),(1.e-8,[False,False,False,False,False,True],False)])
def test_boundary_refinement_requires_two_new_adjacent_guarded_samples(sigma,expected_flags,qualified):
    from nasolve.cif_mixed_endpoint import refine_direction
    points=[[sigma,0.,0.]];direction=[1.,0.,0.]
    def evaluate(p):
        x=p[0][0];value=math.exp(-(x/sigma)**2)
        return {'target':value,'gradient':[-2*x*value/(sigma*sigma),0.,0.]}
    baseline=evaluate(points);before=deepcopy(points)
    result=refine_direction(evaluate,points,direction,baseline)
    assert result['consistent'] is qualified and points==before
    assert [s['step'] for s in result['samples']]==[1.e-7,1.e-8,3.e-9,1.e-9,3.e-10,1.e-10]
    assert all(s['guards']['representable_displacement'] for s in result['samples'])
    assert [s['consistent'] for s in result['samples']]==expected_flags
    assert result['tolerance']=={'absolute':1e-4,'relative':1e-4}


@pytest.mark.parametrize('mode',['wrong_gradient','unrepresentable','nonfinite'])
def test_finer_steps_do_not_rescue_wrong_gradients_or_unrepresentable_points(mode):
    from nasolve.cif_mixed_endpoint import refine_direction
    points=[[1.e20 if mode=='unrepresentable' else 1.,0.,0.]]
    def evaluate(p):
        x=p[0][0]
        return {'target':x*x,'gradient':[float('nan') if mode=='nonfinite' else 3*x if mode=='wrong_gradient' else 2*x,0.,0.]}
    if mode=='nonfinite':
        with pytest.raises(ValueError):refine_direction(evaluate,points,[1.,0.,0.],evaluate(points))
    else:
        result=refine_direction(evaluate,points,[1.,0.,0.],evaluate(points))
        assert result['consistent'] is False
        if mode=='unrepresentable':assert all(not s['guards']['representable_displacement'] for s in result['samples'])


def test_finite_native_targets_cannot_overflow_into_a_nominal_passing_comparison():
    from nasolve.cif_mixed_endpoint import refine_direction
    def evaluate(p):return {'target':1.e308 if p[0][0]>1. else -1.e308}
    with pytest.raises(ValueError):refine_direction(evaluate,[[1.,0.,0.]],[1.,0.,0.],{'target':0.,'gradient':[1.,0.,0.]})


def refinement_fixture():
    from nasolve.cif_mixed_endpoint import FAMILIES
    points=[[1.,.2,.3],[.7,.4,.5],[.2,.8,.1],[.9,.1,.6]]
    cases={label:deepcopy(points) for label in ['initial','full_precision','pdb_rounded']}
    proxy={'i_seqs':[0,1,2,3],'angle_ideal':27.,'weight':.3,'periodicity':3,'alt_angle_ideals':None,'origin_id':0}
    def family(p,name):
        w=7. if name=='all' else 1.
        return {'target':w*math.fsum(x*x for q in p for x in q),'gradient':[2*w*x for q in p for x in q]}
    def local(p,selector):
        v={'target':.3*math.fsum(x*x for q in p for x in q),'gradient':[.6*x for q in p for x in q]}
        return {'single_target':v['target'],'accumulated_target':v['target'],'single_gradient':v['gradient'],
            'accumulated_gradient':v['gradient'].copy(),'native_angle_defined':True,'native_angle_degrees':42.,'status':'FINITE'}
    direction=[1.]+[0.]*11
    plan={'prerequisites':{'full_native_family_coverage':True},'references':{label:{name:family(p,name) for name in FAMILIES} for label,p in cases.items()},
        'local':[{'case':'full_precision','proxy':proxy,'order':'forward','direction':'atom_0_axis_0','vector':direction,
            'expected_baseline':local(points,{}),'original_direction_sha256':'b'*64}],
        'families':[{'case':'full_precision','family':'all','direction':'atom_0_axis_0','vector':direction,'original_direction_sha256':'a'*64}],
        'retained_original_passing_directions':335,'original_direction_count':336}
    return cases,plan,family,local


def test_new_raw_replay_is_canonical_even_when_json_sorts_coordinate_cases():
    from nasolve.cif_mixed_endpoint import audit_endpoint_refinement,replay_endpoint_refinement
    cases,plan,family,local=refinement_fixture();result=audit_endpoint_refinement(family,local,cases,plan)
    assert result['status']=='ADAPTIVE_ENDPOINT_DERIVATIVES_PASS'
    assert result['evaluation_calls']==len(result['observations'])==74
    assert result['model_optimization']=='NOT_RUN' and not result['automatic_adoption']
    import json
    sorted_cases=json.loads(json.dumps(cases,sort_keys=True))
    assert replay_endpoint_refinement(result,sorted_cases,plan)['status']=='ADAPTIVE_ENDPOINT_DERIVATIVES_PASS'


@pytest.mark.parametrize('defect',['gradient','target','request','step','guard','summary','count','drop','extra','order','scope'])
def test_raw_endpoint_reader_recomputes_every_sample_guard_request_and_summary(defect):
    from nasolve.cif_mixed_endpoint import audit_endpoint_refinement,replay_endpoint_refinement
    cases,plan,family,local=refinement_fixture();result=audit_endpoint_refinement(family,local,cases,plan)
    if defect=='gradient':result['observations'][0]['value']['gradient'][0]+=1.
    elif defect=='target':result['observations'][48]['value']['target']+=1.
    elif defect=='request':result['observations'][0]['request']['points_sha256']='c'*64
    elif defect=='step':result['families'][0]['evidence']['samples'][0]['step']*=2.
    elif defect=='guard':result['local'][0]['single']['samples'][0]['guards']['target_resolution_resolved']=False
    elif defect=='summary':result['summary']['sampled_derivatives_pass']=False
    elif defect=='count':result['evaluation_calls']+=1
    elif defect=='drop':result['observations'].pop()
    elif defect=='extra':result['observations'].append(deepcopy(result['observations'][0]))
    elif defect=='order':result['local'][0]['selection']['order']='reversed'
    else:result['automatic_adoption']=True
    with pytest.raises(ValueError):replay_endpoint_refinement(result,cases,plan)


@pytest.mark.parametrize('mode',['wrong_gradient','undefined_perturbation','container_disagreement','unsupported_coverage','snapshot_drift','mutated_points'])
def test_fresh_endpoint_evidence_does_not_promote_unsupported_or_drifting_kernels(mode):
    from nasolve.cif_mixed_endpoint import audit_endpoint_refinement
    cases,plan,family,local=refinement_fixture();original=local
    if mode=='unsupported_coverage':plan['prerequisites']['full_native_family_coverage']=False
    elif mode=='snapshot_drift':plan['references']['initial']['all']['target']+=1.
    def controlled(p,selector):
        result=original(p,selector)
        if mode=='wrong_gradient':
            result['single_gradient'][0]+=1.;result['accumulated_gradient'][0]+=1.
        elif mode=='undefined_perturbation' and p!=cases['full_precision']:result['native_angle_defined']=False
        elif mode=='container_disagreement' and p!=cases['full_precision']:result['accumulated_target']+=1.
        elif mode=='mutated_points':p[0][0]+=1.
        return result
    before=deepcopy(cases)
    if mode in ['undefined_perturbation','container_disagreement','mutated_points']:
        with pytest.raises(ValueError):audit_endpoint_refinement(family,controlled,cases,plan)
    else:assert audit_endpoint_refinement(family,controlled,cases,plan)['status']=='REVIEW'
    assert cases==before


def original_boundary_fixture():
    from nasolve.cif_gradient_audit import audit_gradients
    from nasolve.cif_mixed_endpoint import FAMILIES
    cases,_,family,_=refinement_fixture();labels=['full_precision','pdb_rounded']
    references={name:{'target':family(cases[name],'all')['target'],'gradient_norm':math.sqrt(math.fsum(x*x for x in family(cases[name],'all')['gradient']))} for name in labels}
    audit=audit_gradients(family,{name:cases[name] for name in labels},[0],references=references)
    row=audit['cases']['full_precision']['families']['all']['directions'][0]
    for sample in row['samples']:
        sample['plus_target']=sample['minus_target']+2*sample['step']*(row['analytical']+1.)
        sample['numerical']=(sample['plus_target']-sample['minus_target'])/(2*sample['step'])
        sample['absolute_error']=abs(sample['numerical']-row['analytical'])
        sample['bound']=1e-4+1e-4*max(abs(sample['numerical']),abs(row['analytical']))
        sample['consistent']=sample['absolute_error']<=sample['bound']
        assert not sample['consistent']
    row['status']='REVIEW';audit['cases']['full_precision']['families']['all']['sampled_directions_consistent']=False
    audit['cases']['full_precision']['sampled_gradients_consistent']=False
    geometry={'endpoint_gradient_audit':audit,'final':references['full_precision'],'serialized':references['pdb_rounded']}
    initial={'selected_indices':[0],'gradient_audit':{'cases':{'initial':{'families':{name:{'baseline':family(cases['initial'],name)} for name in FAMILIES}}}}}
    torsion={'positive_constant_count':0,'audit':{'cases':{name:{'proxies':[],'attribution':{'all':True},'summary':{'group_sampled_agreement':True},'saved_family_match':True} for name in cases}}}
    return geometry,initial,torsion,cases


def test_original_boundary_selection_preserves_all_old_positive_directions_and_exact_names():
    from nasolve.cif_mixed_endpoint import refinement_plan
    args=original_boundary_fixture();before=deepcopy(args);plan=refinement_plan(*args)
    assert len(plan['families'])==1 and not plan['local']
    selected=plan['families'][0]
    assert (selected['case'],selected['family'],selected['direction'])==('full_precision','all','full_gradient')
    assert plan['retained_original_passing_directions']+1==plan['original_direction_count']==96
    assert args==before


@pytest.mark.parametrize('defect',['drop_direction','direction_name','analytical','old_numerical','old_bound','old_flag','old_family_status','old_case_status',
    'snapshot_target','snapshot_norm','snapshot_comparison','gradient_additivity_record','calls','call_limit_bool','target_bool','target_nan','positive_constant'])
def test_old_positive_scope_cannot_be_relabeled_or_bypassed_by_fine_evidence(defect):
    from nasolve.cif_mixed_endpoint import refinement_plan
    geometry,initial,torsion,cases=original_boundary_fixture();audit=geometry['endpoint_gradient_audit'];case=audit['cases']['full_precision'];family=case['families']['all'];d=family['directions'][0]
    if defect=='drop_direction':family['directions'].pop()
    elif defect=='direction_name':d['direction']='invented_gradient'
    elif defect=='analytical':d['analytical']+=1.
    elif defect=='old_numerical':d['samples'][0]['numerical']+=1.
    elif defect=='old_bound':d['samples'][0]['bound']*=100.
    elif defect=='old_flag':d['samples'][0]['consistent']=True
    elif defect=='old_family_status':family['sampled_directions_consistent']=True
    elif defect=='old_case_status':case['sampled_gradients_consistent']=True
    elif defect=='snapshot_target':geometry['final']['target']+=1.
    elif defect=='snapshot_norm':geometry['final']['gradient_norm']+=1.
    elif defect=='snapshot_comparison':case['captured_snapshot_match']['comparisons']['target']['captured']+=1.
    elif defect=='gradient_additivity_record':case['gradient_additivity']['difference_norm']+=1.
    elif defect=='calls':audit['evaluation_calls']+=1
    elif defect=='call_limit_bool':audit['max_evaluation_calls']=True
    elif defect=='target_bool':d['samples'][0]['plus_target']=True
    elif defect=='target_nan':d['samples'][0]['plus_target']=float('nan')
    else:
        torsion['positive_constant_count']=1
        assert refinement_plan(geometry,initial,torsion,cases)['prerequisites']['full_native_family_coverage'] is False
        return
    with pytest.raises(ValueError):refinement_plan(geometry,initial,torsion,cases)


# Integration regressions for the maintained C92 worker and saved reader.
import shutil
import subprocess
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

C92_PARENT_SHA256 = 'e'*64
C91_PARENT_SHA256 = 'd'*64


def _rebind_endpoint_artifact(value, relative, data, anchor):
    if isinstance(value, dict):
        if value.get('anchor') == anchor and value.get('path') == relative:
            value.update(size=len(data), sha256=sha256(data).hexdigest())
        for child in value.values(): _rebind_endpoint_artifact(child, relative, data, anchor)
    elif isinstance(value, list):
        for child in value: _rebind_endpoint_artifact(child, relative, data, anchor)


def coherent_torsion_parent(tmp_path, monkeypatch):
    """Run genuine C89/C90/C91 workers with an explicit analytic fake SDK.

    The older fixture retains an arithmetically damaged coarse sample. Repair
    that artificial fixture into coherent negative coarse evidence before C91
    freezes it: one named direction has four honest recorded REVIEW flags.
    New C92 native evaluations still use the original analytic SDK potential.
    """
    from tests.test_cif_mixed_torsion import qualified_failed_endpoint_parent
    from nasolve.cif_mixed_torsion import audit_mixed_torsions
    from nasolve.cif_mixed_geometry import REPORT as GEOMETRY_REPORT, ANCHOR as GEOMETRY_ANCHOR
    geometry, gradient, context, linked, sdk, phenix = qualified_failed_endpoint_parent(tmp_path, monkeypatch)
    path = geometry/'job/geometry_result.json'; result = json.loads(path.read_bytes())
    audit = result['endpoint_gradient_audit']; case = audit['cases']['full_precision']
    family = case['families']['dihedral']; direction = family['directions'][0]
    for sample in direction['samples']:
        sample['plus_target'] = sample['minus_target'] + 2*sample['step']*(direction['analytical']+1.)
        sample['numerical'] = (sample['plus_target']-sample['minus_target'])/(2*sample['step'])
        sample['absolute_error'] = abs(sample['numerical']-direction['analytical'])
        sample['bound'] = 1e-4+1e-4*max(abs(sample['numerical']), abs(direction['analytical']))
        sample['consistent'] = sample['absolute_error'] <= sample['bound']
        assert not sample['consistent']
    direction['status'] = 'REVIEW'
    family['sampled_directions_consistent'] = False
    case['sampled_gradients_consistent'] = False
    result['endpoint_derivative_qualification'] = 'DERIVATIVE_REVIEW'
    path.write_text(json.dumps(result))
    report_path = geometry/GEOMETRY_REPORT; report = json.loads(report_path.read_bytes())
    _rebind_endpoint_artifact(report, 'job/geometry_result.json', path.read_bytes(), GEOMETRY_ANCHOR)
    report_path.write_text(json.dumps(report))
    torsion = tmp_path/'torsion'
    report = audit_mixed_torsions(geometry, gradient, context, linked, phenix, torsion,
        parent_archive_sha256=C91_PARENT_SHA256, timeout_seconds=30)
    assert report['status'] == 'MIXED_TORSION_AUDIT_COMPLETE'
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    return torsion, geometry, gradient, context, linked, sdk, phenix


def _endpoint_parent_bytes(*directories):
    return {path: path.read_bytes() for directory in directories
        for path in directory.rglob('*') if path.is_file()}


def _read_endpoint(output, parents):
    from nasolve.cif_mixed_endpoint import read_saved_mixed_endpoint
    torsion, geometry, gradient, context, linked = parents
    return read_saved_mixed_endpoint(output, torsion_directory=torsion,
        geometry_directory=geometry, gradient_directory=gradient,
        context_directory=context, linked_parent_directory=linked,
        parent_archive_sha256=C92_PARENT_SHA256)


def test_endpoint_inspect_preserves_all_parent_bytes_and_relocates_without_sdk(tmp_path, monkeypatch):
    from nasolve.cif_mixed_endpoint import qualify_saved_mixed_endpoint
    torsion, geometry, gradient, context, linked, sdk, _ = coherent_torsion_parent(tmp_path, monkeypatch)
    parents = [torsion, geometry, gradient, context, linked]; before = _endpoint_parent_bytes(*parents)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('inspect launched a native process'))
    output = tmp_path/'endpoint'
    report = qualify_saved_mixed_endpoint(*parents, None, output, parent_archive_sha256=C92_PARENT_SHA256)
    assert report['status'] == 'PREPARED_ONLY' and report['new_native_calls'] == 0
    assert report['maximum_native_calls'] == 2
    assert report['model_optimization'] == 'NOT_RUN'
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert report['coordinate_decision']['continue_solving'] is True
    assert not report['requires_cif_review'] and not report['automatic_adoption']
    assert all(path.read_bytes() == data for path, data in before.items())
    moved = tmp_path/'relocated'; moved.mkdir()
    moved_parents = []
    for name, path in zip(['torsion', 'geometry', 'gradient', 'context', 'linked'], parents):
        path.rename(moved/name); moved_parents.append(moved/name)
    output.rename(moved/'endpoint'); shutil.rmtree(sdk)
    assert _read_endpoint(moved/'endpoint', moved_parents) == report


@pytest.mark.parametrize('mode', ['correct', 'manager', 'source', 'timeout', 'missing_result'])
def test_saved_endpoint_actual_new_worker_and_conditional_native_readback(tmp_path, monkeypatch, mode):
    from nasolve.cif_mixed_endpoint import qualify_saved_mixed_endpoint
    torsion, geometry, gradient, context, linked, sdk, phenix = coherent_torsion_parent(tmp_path, monkeypatch)
    parents = [torsion, geometry, gradient, context, linked]; before = _endpoint_parent_bytes(*parents)
    if mode == 'manager': phenix.environment['EXPLICIT_C90_MISMATCH'] = '1'
    elif mode == 'source':
        path = sdk/'cctbx/geometry_restraints/__init__.py'
        path.write_bytes(path.read_bytes()+b'\n# EXPLICIT_C92_SOURCE_DRIFT\n')
    elif mode == 'timeout': phenix.environment['EXPLICIT_C91_TIMEOUT'] = '1'
    elif mode == 'missing_result':
        original_popen = subprocess.Popen
        class MissingResult:
            def __init__(self, process, work): self.process, self.work = process, work
            def __getattr__(self, name): return getattr(self.process, name)
            def wait(self, **kwargs):
                code = self.process.wait(**kwargs)
                # Delete only the newly produced C92 result, after the actual
                # worker ran. Initial frozen specs and old evidence stay intact.
                candidates = [p for p in self.work.glob('*result.json')]
                assert candidates, 'new worker did not publish a result'
                for path in candidates: path.unlink()
                return code
        monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw:
            MissingResult(original_popen(*a, **kw), Path(kw['cwd'])))
    output = tmp_path/'endpoint'
    report = qualify_saved_mixed_endpoint(*parents, phenix, output,
        parent_archive_sha256=C92_PARENT_SHA256, timeout_seconds=1 if mode == 'timeout' else 30)
    assert report['model_optimization'] == 'NOT_RUN'
    assert not report['automatic_adoption'] and not report['requires_cif_review']
    assert all(path.read_bytes() == data for path, data in before.items())
    assert not any(p.name == 'fake_optimizer_called' for p in output.rglob('*'))
    if mode == 'correct':
        assert report['status'] == 'MIXED_ENDPOINT_QUALIFIED', report
        assert report['qualification']['status'] == 'ADAPTIVE_ENDPOINT_DERIVATIVES_PASS', report
        assert report['new_native_calls'] == 2
        assert report['coordinate_decision']['selected'] == 'qualified_geometry_endpoint'
        assert report['coordinate_decision']['endpoint_usable'] is True
        assert all(report['coordinate_decision']['checks'].values())
        moved = tmp_path/'relocated'; moved.mkdir(); moved_parents = []
        for name, path in zip(['torsion', 'geometry', 'gradient', 'context', 'linked'], parents):
            path.rename(moved/name); moved_parents.append(moved/name)
        output.rename(moved/'endpoint'); shutil.rmtree(sdk)
        output, parents = moved/'endpoint', moved_parents
    else:
        assert report['status'] == 'REVIEW'
        assert report['new_native_calls'] == 1
        assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
        assert report['coordinate_decision']['continue_solving'] is True
        assert report['execution']['status'] == ('TIMED_OUT' if mode == 'timeout' else 'COMPLETED' if mode == 'missing_result' else 'FAILED')
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('saved reader launched a native process'))
    assert _read_endpoint(output, parents) == report


def test_endpoint_launch_failure_preserves_original_usable_decision_without_approval(tmp_path, monkeypatch):
    from nasolve.cif_mixed_endpoint import qualify_saved_mixed_endpoint
    torsion, geometry, gradient, context, linked, _, phenix = coherent_torsion_parent(tmp_path, monkeypatch)
    parents = [torsion, geometry, gradient, context, linked]; before = _endpoint_parent_bytes(*parents)
    def fail(*args, **kwargs): raise OSError('EXPLICIT_C92_LAUNCH_FAILURE')
    monkeypatch.setattr(subprocess, 'Popen', fail)
    report = qualify_saved_mixed_endpoint(*parents, phenix, tmp_path/'endpoint', parent_archive_sha256=C92_PARENT_SHA256)
    assert report['status'] == 'REVIEW' and report['new_native_calls'] == 0
    assert report['execution']['status'] == 'LAUNCH_FAILED'
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert report['coordinate_decision']['continue_solving'] is True
    assert not report['automatic_adoption'] and not report['requires_cif_review']
    assert all(path.read_bytes() == data for path, data in before.items())
    assert _read_endpoint(tmp_path/'endpoint', parents) == report


def test_failed_conditional_native_readback_keeps_constructed_model(tmp_path, monkeypatch):
    """Positive derivatives cannot bypass final exact native identity checks."""
    from nasolve.cif_mixed_endpoint import qualify_saved_mixed_endpoint
    torsion, geometry, gradient, context, linked, _, phenix = coherent_torsion_parent(tmp_path, monkeypatch)
    parents = [torsion, geometry, gradient, context, linked]; before = _endpoint_parent_bytes(*parents)
    original_popen = subprocess.Popen; commands = []
    def drift_only_readback(command, **kwargs):
        commands.append(list(command))
        if 'native_worker.py' in command:
            kwargs = dict(kwargs)
            kwargs['env'] = {**kwargs['env'], 'EXPLICIT_C90_MISMATCH': '1'}
        return original_popen(command, **kwargs)
    monkeypatch.setattr(subprocess, 'Popen', drift_only_readback)
    report = qualify_saved_mixed_endpoint(*parents, phenix, tmp_path/'endpoint',
        parent_archive_sha256=C92_PARENT_SHA256, timeout_seconds=30)
    assert len(commands) == report['new_native_calls'] == 2
    assert report['qualification']['status'] == 'ADAPTIVE_ENDPOINT_DERIVATIVES_PASS'
    assert report['status'] == 'REVIEW'
    assert report['coordinate_decision']['selected'] == 'verified_constructed_model'
    assert report['coordinate_decision']['endpoint_usable'] is False
    assert report['coordinate_decision']['continue_solving'] is True
    assert not report['requires_cif_review'] and not report['automatic_adoption']
    assert all(path.read_bytes() == data for path, data in before.items())
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('saved reader launched a native process'))
    assert _read_endpoint(tmp_path/'endpoint', parents) == report


@pytest.mark.parametrize('defect',['worker','core','plan','spec','prior_decision','prior_qualification','schema_bool','calls_bool','adoption','parent_sha'])
def test_saved_endpoint_reader_rejects_rebound_recipes_and_scope_changes(tmp_path, monkeypatch, defect):
    from nasolve.cif_mixed_endpoint import qualify_saved_mixed_endpoint,REPORT
    torsion,geometry,gradient,context,linked,_,_=coherent_torsion_parent(tmp_path,monkeypatch)
    parents=[torsion,geometry,gradient,context,linked];output=tmp_path/'endpoint'
    report=qualify_saved_mixed_endpoint(*parents,None,output,parent_archive_sha256=C92_PARENT_SHA256)
    before=_endpoint_parent_bytes(*parents)
    relative={'worker':'job/endpoint_worker.py','core':'job/endpoint_core.py','plan':'refinement_plan.json','spec':'job/endpoint_spec.json'}.get(defect)
    if relative:
        path=output/relative;path.write_bytes(path.read_bytes()+b'\nEXPLICIT_CHANGED_RECIPE\n')
        _rebind_endpoint_artifact(report,relative,path.read_bytes(),'mixed_endpoint_directory')
    elif defect=='prior_decision':report['original_coordinate_decision']['selected']='qualified_geometry_endpoint'
    elif defect=='prior_qualification':report['original_geometry_qualification']['status']='PASS'
    elif defect=='schema_bool':report['schema_version']=True
    elif defect=='calls_bool':report['new_native_calls']=False
    elif defect=='adoption':report['automatic_adoption']=True
    else:report['parent_archive_sha256']='a'*64
    (output/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('saved reader launched native code'))
    with pytest.raises(ValueError):_read_endpoint(output,parents)
    assert all(path.read_bytes()==data for path,data in before.items())



def test_actual_endpoint_worker_refines_both_orders_of_local_boundary_evidence(tmp_path, monkeypatch):
    """Exercise the local worker path using genuine captured negative evidence.

    The explicit fake native API can simulate a coarse local finite-difference
    failure under one environment flag. Its source bytes and exact baseline
    remain unchanged across the initial qualification, C91 capture and C92 run.
    No production evaluator, worker or result arithmetic is mocked.
    """
    from tests import test_cif_dihedral_conditioning as fake_module
    from nasolve.cif_mixed_torsion import audit_mixed_torsions
    from nasolve.cif_mixed_endpoint import qualify_saved_mixed_endpoint
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
    assert _read_endpoint(output,parents)==report
