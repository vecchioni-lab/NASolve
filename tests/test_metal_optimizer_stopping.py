"""Completed native jobs must not hide internal optimizer errors."""
import copy
from types import SimpleNamespace as S
import pytest
from nasolve.metal.optimizer_stopping import observe, summarize

class Evaluator:
    refine_xyz=True
    refine_adp=False


def harness(reason='traditional_convergence_test',error=None,iterations=3,limit=25):
    calls=[]
    def run(target_evaluator,termination_params=None,use_fortran=False,log=None):
        calls.append((target_evaluator,termination_params,use_fortran))
        if log is not None:
            log.write('ordinary progress\n')
            if reason:log.write('lbfgs minimizer stop: '+reason+'\n')
            if error:log.write('lbfgs minimizer exception: '+error+'\n')
        return S(iter=lambda:iterations,nfun=lambda:iterations+2,error=error,is_unusual_error=True if error else None)
    module=S(run=run)
    context=observe(_lbfgs=module,_minimizer_type=Evaluator,_source_hashes={k:'a'*64 for k in ('lbfgs_python','minimization_python','lbfgs_kernel')})
    params=S(max_iterations=limit,max_calls=None,traditional_convergence_test=True,traditional_convergence_test_eps=1e-5)
    return context,module,run,Evaluator(),params,calls


def capture(**kwargs):
    context,module,original,e,p,calls=harness(**kwargs)
    with context:module.run(target_evaluator=e,termination_params=p,use_fortran=False)
    assert module.run is original and calls==[(e,p,False)]
    return context.receipt()


def test_native_swallowed_line_search_error_is_preserved_not_convergence():
    e=capture(reason=None,error='lbfgs error: Line search failed: The step is at the lower bound stpmin().',iterations=257,limit=1000)
    r=summarize(e,required_kinds={'XYZ'})
    assert r['calls'][0]['status']=='NOT_CONVERGED_ERROR'
    assert r['calls'][0]['native_error']==e['calls'][0]['error']
    assert r['calls'][0]['is_unusual_error'] is True
    assert r['needs_review'] and r['selected_endpoint_attribution']=='NOT_ASSESSED'
    assert r['scientific_acceptance']=='NOT_ASSESSED'

@pytest.mark.parametrize('kw,wanted',[
 ({},'NATIVE_CRITERION_MET'),
 ({'reason':'max_iterations','iterations':25},'NOT_CONVERGED_LIMIT'),
 ({'reason':None},'NOT_ASSESSED'),
 ({'reason':'max_calls'},'NOT_CONVERGED_LIMIT'),
 ({'reason':None,'error':'rounding errors'},'NOT_CONVERGED_ERROR')])
def test_reuses_conservative_stopping_categories(kw,wanted):
    r=summarize(capture(**kw),required_kinds={'XYZ'})
    assert r['calls'][0]['status']==wanted
    assert r['convergence']=='NOT_INDEPENDENTLY_ASSESSED'


def test_error_has_priority_over_iteration_limit():
    r=summarize(capture(reason='max_iterations',iterations=25,error='native error'))
    assert r['calls'][0]['status']=='NOT_CONVERGED_ERROR'


def test_unrelated_optimizers_not_observed_and_original_log_preserved():
    import io
    context,module,original,e,p,calls=harness();log=io.StringIO()
    with context:
        module.run(target_evaluator=object(),termination_params=p)
        module.run(e,p,False,log)
    assert len(context.receipt()['calls'])==1
    assert 'ordinary progress' in log.getvalue() and 'traditional_convergence_test' in log.getvalue()


def test_restores_on_exception_without_suppressing_it():
    context,module,original,e,p,calls=harness()
    with pytest.raises(RuntimeError,match='caller failed'):
        with context:
            module.run(e,p)
            raise RuntimeError('caller failed')
    assert module.run is original
    assert context.receipt()['binding_restored'] is True
    assert context.receipt()['capture_complete'] is False
    with pytest.raises(ValueError):summarize(context.receipt())


def test_ownership_loss_does_not_overwrite_foreign_hook():
    context,module,original,e,p,calls=harness();foreign=lambda:None
    with pytest.raises(ValueError,match='ownership'):
        with context:module.run=foreign
    assert module.run is foreign and not context.receipt()['binding_restored']


@pytest.mark.parametrize('change',['hash','complete','restored','sequence','bool_count','negative_count','kind','criterion','error','missing_kind'])
def test_bad_evidence_rejected(change):
    e=capture();required={'XYZ'}
    if change=='hash':e['native_sources']['lbfgs_python']='bad'
    if change=='complete':e['capture_complete']=False
    if change=='restored':e['binding_restored']=False
    if change=='sequence':e['calls'][0]['sequence']=2
    if change=='bool_count':e['calls'][0]['iterations']=True
    if change=='negative_count':e['calls'][0]['function_evaluations']=-1
    if change=='kind':e['calls'][0]['kind']='unknown'
    if change=='criterion':e['calls'][0]['native_criterion_met']=False
    if change=='error':e['calls'][0]['error']=False
    if change=='missing_kind':required={'XYZ','ADP'}
    with pytest.raises(ValueError):summarize(e,required_kinds=required)


def test_xyz_audit_preserves_legacy_and_adds_stopping_review(tmp_path):
    from tests.test_metal_xyz import prepared,evidence
    xyz,c,h,raw,plan,ref=prepared(tmp_path);native=evidence(plan,raw)
    old=xyz.audit_result(plan,raw,native,raw);assert 'optimizer_stopping'not in old
    e=capture(reason=None,error='line search failure');adp=copy.deepcopy(e['calls'][0]);adp.update(sequence=2,kind='ADP');e['calls'].append(adp)
    native['optimizer_stopping']=e
    new=xyz.audit_result(plan,raw,native,raw)
    assert new['optimizer_stopping']['needs_review']
    assert new['fdp_quantitation_ready']is False and new['scientific_acceptance']=='NOT_ASSESSED'
    new.pop('optimizer_stopping');assert new==old


def test_sidecar_must_match_and_cannot_float_without_native_receipt(tmp_path):
    import json
    from nasolve.metal.optimizer_stopping import verify_file
    e={'optimizer_stopping':capture()};p=tmp_path/'optimizer-stopping.json'
    with pytest.raises(ValueError):verify_file(e,tmp_path)
    p.write_text(json.dumps(e['optimizer_stopping']));verify_file(e,tmp_path)
    with pytest.raises(ValueError):verify_file({},tmp_path)
    altered=copy.deepcopy(e);altered['optimizer_stopping']['calls'][0]['iterations']+=1
    with pytest.raises(ValueError):verify_file(altered,tmp_path)


def test_new_receipt_relocates_and_resealed_summary_tampering_is_rejected(tmp_path,monkeypatch):
    import gzip,json,os,shutil,subprocess,sys
    from pathlib import Path
    from tests.test_metal_xyz import fake_execution
    from nasolve.metal.context import _reference
    from nasolve.metal.recipe import digest,RecipeError
    old=tmp_path/'original';xyz,c,h,ref,n=fake_execution(old,monkeypatch);fake=xyz._native
    def enriched(directory,native,timeout):
        e=fake(directory,native,timeout);receipt=capture(reason=None,error='native line search failure')
        adp=copy.deepcopy(receipt['calls'][0]);adp.update(sequence=2,kind='ADP');receipt['calls'].append(adp)
        e['optimizer_stopping']=receipt
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()))
        (directory/'optimizer-stopping.json').write_text(json.dumps(receipt))
        return e
    monkeypatch.setattr(xyz,'_native',enriched)
    doc=xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'])
    assert xyz.verify_xyz(c.run,'Metal/xyz_001')==doc
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',old/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved=tmp_path/'relocated';old.rename(moved);run=moved/'dataset/AutoMR/run_001'
    script="from nasolve.metal.xyz import verify_xyz;import sys;print(verify_xyz(sys.argv[1],'Metal/xyz_001')['trial_id'])"
    result=subprocess.run([sys.executable,'-B','-c',script,str(run)],cwd=moved,env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,check=True)
    assert result.stdout.strip()==doc['trial_id']and not old.exists()
    directory=run/'Metal/xyz_001';p=directory/'result.json';value=json.loads(p.read_text())
    value['optimizer_stopping']['calls'][0]['status']='NATIVE_CRITERION_MET';p.write_text(json.dumps(value))
    manifest=json.loads((directory/'manifest.json').read_text());manifest['files']['result.json']=_reference(p,run)
    manifest.pop('trial_id');manifest['trial_id']=digest(manifest);(directory/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(RecipeError,match='XYZ audit changed'):xyz.verify_xyz(run,'Metal/xyz_001')


def test_receipt_write_failure_keeps_primary_native_exception(tmp_path,monkeypatch):
    from nasolve.metal._xyz_native import _run_observed
    from pathlib import Path
    context,module,original,e,p,calls=harness()
    primary=RuntimeError('primary native failure')
    def fail():raise primary
    def no_write(*args,**kwargs):raise OSError('disk full')
    monkeypatch.setattr(Path,'write_text',no_write)
    with pytest.raises(RuntimeError,match='primary native failure')as caught:
        _run_observed(fail,context,tmp_path/'receipt.json')
    assert caught.value is primary and module.run is original
    assert any('disk full'in note for note in primary.__notes__)


def test_receipt_write_failure_after_success_still_fails(tmp_path,monkeypatch):
    from nasolve.metal._xyz_native import _run_observed
    from pathlib import Path
    context,module,original,e,p,calls=harness()
    def no_write(*args,**kwargs):raise OSError('disk full')
    monkeypatch.setattr(Path,'write_text',no_write)
    with pytest.raises(OSError,match='disk full'):
        _run_observed(lambda:None,context,tmp_path/'receipt.json')
    assert module.run is original


def test_preexisting_callable_is_explicitly_not_authenticated():
    context,module,original,e,p,calls=harness()
    def foreign(*args,**kwargs):return original(*args,**kwargs)
    import functools
    module.run=functools.wraps(original)(foreign)
    with context:module.run(e,p)
    receipt=context.receipt();assert module.run is foreign
    assert receipt['entry_binding_authentication']=='NOT_ASSESSED'
    assert summarize(receipt)['entry_binding_authentication']=='NOT_ASSESSED'
