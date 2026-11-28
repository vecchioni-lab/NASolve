"""Resolution evidence is separate from coordinate adoption."""
import json
from pathlib import Path
import subprocess
import pytest
from nasolve.cif_recovered_resolution import audit_recovered_resolution, read_recovered_resolution, REPORT


def parent_fixture(tmp_path, monkeypatch):
    from tests.test_cif_recovered_torsion import failed_parent
    from nasolve.cif_recovered_torsion import audit_recovered_torsions
    geometry, gradient, recovery, sdk, phenix = failed_parent(tmp_path, monkeypatch)
    torsion = tmp_path/'c101'
    report = audit_recovered_torsions(geometry, gradient, recovery, phenix, torsion, timeout_seconds=30)
    assert report['status'] == 'RECOVERED_MIXED_TORSION_AUDIT_COMPLETE'
    return torsion, geometry, gradient, recovery, sdk, phenix


def read(out, parents):
    return read_recovered_resolution(out, torsion_directory=parents[0], geometry_directory=parents[1],
        gradient_directory=parents[2], recovery_directory=parents[3])


@pytest.mark.parametrize('seconds',[0,601,True,1.5])
def test_deadline_precedes_parent_reads(tmp_path, seconds):
    with pytest.raises(ValueError): audit_recovered_resolution(*[tmp_path/str(i) for i in range(4)], None, tmp_path/'out', timeout_seconds=seconds)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('mode',['prepare','complete','manager','source','timeout','missing_result','launch'])
def test_fixed_worker_preserves_selection_and_replays_after_relocation(tmp_path, monkeypatch, mode):
    from nasolve.cif_mixed_endpoint_window import _WORKER
    from tests.test_cif_mixed_torsion import parent_files
    *parents,sdk,phenix = parent_fixture(tmp_path,monkeypatch)
    before = parent_files(*parents)
    if mode == 'manager': phenix.environment['EXPLICIT_C90_MISMATCH']='1'
    elif mode == 'source':
        p=sdk/'cctbx/geometry_restraints/__init__.py';p.write_bytes(p.read_bytes()+b'\n# SOURCE_DRIFT\n')
    elif mode == 'timeout': phenix.environment['EXPLICIT_C91_TIMEOUT']='1'
    elif mode == 'launch':
        def fail(*a,**kw):raise OSError('EXPLICIT_LAUNCH_FAILURE')
        monkeypatch.setattr(subprocess,'Popen',fail)
    elif mode == 'missing_result':
        original=subprocess.Popen
        class Missing:
            def __init__(self,p,job):self.process,self.job=p,job
            def __getattr__(self,n):return getattr(self.process,n)
            def wait(self,**kwargs):
                code=self.process.wait(**kwargs);assert code==0
                (self.job/'endpoint_result.json').unlink();return code
        monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:Missing(original(*a,**kw),Path(kw['cwd'])))
    out=tmp_path/'resolution'
    report=audit_recovered_resolution(*parents,None if mode=='prepare' else phenix,out,timeout_seconds=1 if mode=='timeout' else 30)
    assert report['new_native_calls']==(0 if mode in {'prepare','launch'} else 1)
    assert report['maximum_native_calls']==1
    assert report['coordinate_decision']['selected']=='verified_recovered_model'
    assert not report['coordinate_decision']['endpoint_usable']
    assert report['endpoint_requalification']==report['model_optimization']=='NOT_RUN'
    assert not report['automatic_adoption'] and not report['requires_cif_review']
    assert (out/'job/endpoint_worker.py').read_text()==_WORKER
    assert not (out/'candidate').exists() and not (out/'job/fake_optimizer_called').exists()
    assert all(p.read_bytes()==data for p,data in before.items())
    if mode=='complete':
        assert report['status']=='RECOVERED_RESOLUTION_AUDIT_COMPLETE',report
        assert report['qualification']['status']=='ADAPTIVE_ENDPOINT_DERIVATIVES_PASS'
        assert report['summary']['failed_prerequisites']==[]
    else:
        assert report['status']==('PREPARED_ONLY' if mode=='prepare' else 'REVIEW')
        assert report['execution']['status']=={'prepare':'NOT_RUN','manager':'FAILED','source':'FAILED','timeout':'TIMED_OUT','missing_result':'COMPLETED','launch':'LAUNCH_FAILED'}[mode]
    moved=tmp_path/'relocated';moved.mkdir();new=[]
    for name,p in zip(['torsion','geometry','gradient','recovery'],parents):p.rename(moved/name);new.append(moved/name)
    out.rename(moved/'resolution');out=moved/'resolution'
    import shutil
    shutil.rmtree(sdk)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('Reader launched an SDK'))
    assert read(out,new)==report


@pytest.mark.parametrize('defect',['version','executable','torsion_bytes','prepared_torsion'])
def test_changed_consumer_or_unverified_torsion_cannot_start(tmp_path,monkeypatch,defect):
    *parents,_,phenix=parent_fixture(tmp_path,monkeypatch)
    if defect=='version':phenix.version='CHANGED'
    elif defect=='executable':phenix.executables['phenix.python']=str(parents[3]/'projected.cif')
    elif defect=='torsion_bytes':
        p=parents[0]/'job/torsion_result.json';p.write_bytes(p.read_bytes()+b'CHANGED')
    else:
        from nasolve.cif_recovered_torsion import audit_recovered_torsions
        parents[0]=tmp_path/'prepared'
        audit_recovered_torsions(*parents[1:],None,parents[0])
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('Bad precondition launched'))
    with pytest.raises(ValueError):audit_recovered_resolution(*parents,phenix,tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('mode',['existing','symlink','inside_parent'])
def test_output_preserves_prior_attempts(tmp_path,mode):
    parents=[tmp_path/str(i) for i in range(4)]
    for p in parents:p.mkdir()
    protected=tmp_path/'protected';protected.mkdir();(protected/'keep').write_text('KEEP')
    if mode=='existing':out=protected
    elif mode=='symlink':
        alias=tmp_path/'alias';alias.symlink_to(protected,target_is_directory=True);out=alias/'out'
    else:out=parents[0]/'out'
    with pytest.raises(ValueError):audit_recovered_resolution(*parents,None,out)
    assert (protected/'keep').read_text()=='KEEP' and all(not (p/'out').exists() for p in parents)


def rebind(value,relative,data):
    from hashlib import sha256
    if isinstance(value,dict):
        if value.get('path')==relative and 'sha256' in value:value.update(size=len(data),sha256=sha256(data).hexdigest())
        for child in value.values():rebind(child,relative,data)
    elif isinstance(value,list):
        for child in value:rebind(child,relative,data)


@pytest.mark.parametrize('defect',['worker','core','plan','spec','dictionary','model','decision','scope','adoption','schema','calls','archive','parent_binding','extra'])
def test_reader_rejects_rebound_recipe_and_authority_changes(tmp_path,monkeypatch,defect):
    *parents,_,_=parent_fixture(tmp_path,monkeypatch);out=tmp_path/'out'
    report=audit_recovered_resolution(*parents,None,out)
    inputs=report['preparation']['native_preparation']['inputs']
    paths={'worker':'job/endpoint_worker.py','core':'job/endpoint_core.py','plan':'refinement_plan.json','spec':'job/endpoint_spec.json',
        'dictionary':inputs[1]['artifact']['path'],'model':inputs[0]['artifact']['path']}
    if defect in paths:
        p=out/paths[defect];p.write_bytes(p.read_bytes()+b' ');rebind(report,paths[defect],p.read_bytes())
    elif defect=='decision':report['coordinate_decision']['selected']='qualified_geometry_endpoint'
    elif defect=='scope':report['endpoint_requalification']='PASS'
    elif defect=='adoption':report['automatic_adoption']=True
    elif defect=='schema':report['schema_version']=True
    elif defect=='calls':report['maximum_native_calls']=True
    elif defect=='archive':report['parent_archive_sha256']='0'*64
    elif defect=='parent_binding':report['inputs']['torsion_result']['anchor']='recovered_geometry_directory'
    else:(out/'extra.json').write_text('{}')
    (out/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('Reader launched'))
    with pytest.raises(ValueError):read(out,parents)


@pytest.mark.parametrize('defect',['consumer','observation','step','summary','qualification'])
def test_completed_receipt_rejects_forged_numerics_and_summary(tmp_path,monkeypatch,defect):
    *parents,_,phenix=parent_fixture(tmp_path,monkeypatch);out=tmp_path/'out'
    report=audit_recovered_resolution(*parents,phenix,out,timeout_seconds=30)
    assert report['status']=='RECOVERED_RESOLUTION_AUDIT_COMPLETE'
    if defect=='consumer':report['executable_sha256']='0'*64
    elif defect=='summary':report['summary']['passing_local_directions']+=1
    elif defect=='qualification':report['qualification']['status']='REVIEW'
    else:
        p=out/'job/endpoint_result.json';v=json.loads(p.read_bytes())
        if defect=='observation':v['audit']['observations'][0]['value']['target']+=1
        else:v['audit']['step_sizes'][1]=2e-8
        p.write_text(json.dumps(v));rebind(report,'job/endpoint_result.json',p.read_bytes())
    (out/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('Reader launched'))
    with pytest.raises(ValueError):read(out,parents)


def test_fine_sample_passes_do_not_clear_failed_reversal_or_group_prerequisites():
    from tests.test_cif_mixed_endpoint_window import current_fixture
    from nasolve.cif_mixed_endpoint_window import audit_endpoint_refinement,replay_endpoint_refinement
    from nasolve.cif_recovered_resolution import _summary
    cases,plan,family,local=current_fixture()
    plan['prerequisites'].update({'full_precision:0:forward':False,'full_precision:group_samples':False})
    raw=audit_endpoint_refinement(family,local,cases,plan)
    assert raw['status']=='REVIEW'
    assert replay_endpoint_refinement(raw,cases,plan)['status']=='REVIEW'
    summary=_summary(raw,plan)
    assert summary['passing_local_directions']==summary['refined_local_directions']
    assert summary['passing_family_directions']==summary['refined_family_directions']
    assert summary['failed_prerequisites']==['full_precision:0:forward','full_precision:group_samples']
    assert not summary['sampled_derivatives_pass'] and summary['endpoint_requalification']=='NOT_RUN'


@pytest.mark.parametrize('mode',['consistent','mismatch','one_order','conflicting_repeat'])
def test_fresh_reversal_uses_atom_block_permutation_and_retains_disagreement(mode):
    from copy import deepcopy
    from nasolve.cif_recovered_resolution import _summary
    forward=[float(i) for i in range(1,13)];reverse=[v for i in [9,6,3,0] for v in forward[i:i+3]]
    if mode=='mismatch':reverse[0]+=1e-4
    rows=[]
    for order,gradient in [('forward',forward),('reversed',reverse)]:
        if mode=='one_order' and order=='reversed':continue
        rows.append({'selection':{'case':'full_precision','proxy':{'i_seqs':[0,1,2,3]},'order':order},
            'baseline':{'single_target':1.,'accumulated_target':1.,'single_gradient':gradient,'accumulated_gradient':gradient.copy()},
            'checks':{},'single':{'consistent':True},'accumulated':{'consistent':True}})
    if mode=='conflicting_repeat':
        row=deepcopy(rows[0]);row['baseline']['single_target']+=1;rows.append(row)
    audit={'local':rows,'families':[],'summary':{},'checks':{}}
    if mode=='conflicting_repeat':
        with pytest.raises(ValueError):_summary(audit,{'prerequisites':{}})
    else:
        result=_summary(audit,{'prerequisites':{}})['fresh_local_reversals'][0]
        assert result['status']=={'consistent':'PASS','mismatch':'REVIEW','one_order':'NOT_SAMPLED_IN_BOTH_ORDERS'}[mode]
        if mode!='one_order':
            assert all(v['consistent'] is (mode=='consistent') for v in result['comparisons'].values())



def test_native_resolution_worker_revisits_both_orders_but_never_adopts(tmp_path,monkeypatch):
    from tests import test_cif_dihedral_conditioning as fake_module
    original='    def residual(self):return self.proxy.weight*sum(v*v for i in self.proxy.i_seqs for v in self.points[i])'
    replacement="""    def residual(self):
        value=self.proxy.weight*sum(v*v for i in self.proxy.i_seqs for v in self.points[i])
        import os,json
        from pathlib import Path
        if os.environ.get('EXPLICIT_C102_COARSE_FAILURE') and len(self.points)==4 and Path('torsion_spec.json').is_file():
            spec=json.loads(Path('torsion_spec.json').read_bytes());references=[]
            for points in spec['coordinate_cases'].values():
                for row in spec['selection']['selected']:
                    selected=[points[i] for i in row['proxy']['i_seqs']]
                    references.extend([selected,selected[::-1]])
            current=[list(p) for p in self.points]
            nearest=min(references,key=lambda rows:sum((a-b)**2 for p,q in zip(current,rows) for a,b in zip(p,q)))
            if current[0][0]>nearest[0][0]:value+=1.
        return value"""
    assert original in fake_module._FAKE_DIHEDRAL_API
    monkeypatch.setattr(fake_module,'_FAKE_DIHEDRAL_API',fake_module._FAKE_DIHEDRAL_API.replace(original,replacement))
    from tests.test_cif_recovered_torsion import failed_parent
    from nasolve.cif_recovered_torsion import audit_recovered_torsions
    geometry,gradient,recovery,_,phenix=failed_parent(tmp_path,monkeypatch)
    phenix.environment['EXPLICIT_C102_COARSE_FAILURE']='1';torsion=tmp_path/'c101'
    parent=audit_recovered_torsions(geometry,gradient,recovery,phenix,torsion,timeout_seconds=30)
    assert any(not v['local_sampled_agreement'] for v in parent['summary']['cases'].values())
    del phenix.environment['EXPLICIT_C102_COARSE_FAILURE']
    parents=[torsion,geometry,gradient,recovery];out=tmp_path/'resolution'
    report=audit_recovered_resolution(*parents,phenix,out,timeout_seconds=30)
    assert report['status']=='RECOVERED_RESOLUTION_AUDIT_COMPLETE'
    assert report['summary']['refined_local_directions']>0
    assert report['summary']['passing_local_directions']==report['summary']['refined_local_directions']
    assert all(r['orders_observed']==['forward','reversed'] and r['status']=='PASS' for r in report['summary']['fresh_local_reversals'])
    assert report['coordinate_decision']['selected']=='verified_recovered_model' and report['endpoint_requalification']=='NOT_RUN'
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:pytest.fail('Reader launched'))
    assert read(out,parents)==report
