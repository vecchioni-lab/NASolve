"""Expose scale leverage without selecting observations or changing science."""
import copy
import hashlib
import json
import math
import pytest
from nasolve.metal.fit_diagnostics import summarize
from tests.test_metal_fdp import reflection_evidence, prepared, native_result


def case():
    # The first free reflection dominates sum(Fmodel**2), but is weakly observed.
    rr=reflection_evidence([[[1,0,0],1.,1.,True],[[2,0,0],10.,1.,True],[[3,0,0],20.,1.,True],[[4,0,0],10.,1.,False]])
    rows=[[[1,0,0],50.,100.,0.],[[2,0,0],25.,10.,0.],[[3,0,0],16.,20.,0.],[[4,0,0],12.,10.,0.]]
    k=600/10500
    capture=dict(protocol='metal-fit-diagnostics-v1',implementation_sha256='a'*64,rows=rows,
                 work_scale=1.,free_scale=k)
    rf=(abs(1-100*k)+abs(10-10*k)+abs(20-20*k))/31
    return capture,rr,0.,rf


def test_scale_dominance_is_separate_from_residual_rank_and_never_replaces_r():
    c,r,rw,rf=case();original=copy.deepcopy((c,r))
    out=summarize(c,r,rw,rf)
    assert (c,r)==original
    assert out['free']['r_native']==pytest.approx(rf)
    top=out['free']['highest_scale_leverage'][0]
    assert top['indices']==[[1,0,0]]
    assert top['scale_denominator_fraction']==pytest.approx(10000/10500)
    assert top['remaining_scalar_sensitivity']['r']==pytest.approx(0)
    assert top['remaining_scalar_sensitivity']['used_for_refinement'] is False
    assert out['automatic_exclusion'] is False
    assert out['scientific_acceptance']=='NOT_ASSESSED'


@pytest.mark.parametrize('change',['missing','duplicate','order','nan','scale','r','implementation','d','bool'])
def test_inconsistent_evidence_fails(change):
    c,r,rw,rf=case()
    if change=='missing':c['rows'].pop()
    if change=='duplicate':c['rows'][1][0]=[1,0,0]
    if change=='order':c['rows'].reverse()
    if change=='nan':c['rows'][0][2]=float('nan')
    if change=='scale':c['free_scale']=-1
    if change=='r':rf+=.1
    if change=='implementation':c['implementation_sha256']='invalid'
    if change=='d':c['rows'][0][1]=0.
    if change=='bool':c['rows'][0][2]=True
    with pytest.raises(ValueError):summarize(c,r,rw,rf)


def test_friedel_mates_share_diagnostic_group_but_keep_observations():
    c,r,rw,rf=case();r['rows'].insert(0,[[-1,0,0],1.,1.,True]);c['rows'].insert(0,[[-1,0,0],50.,100.,0.])
    c['free_scale']=700/20500
    rf=(2*abs(1-100*c['free_scale'])+30*(1-c['free_scale']))/32
    out=summarize(c,r,rw,rf)
    group=out['free']['highest_scale_leverage'][0]
    assert group['indices']==[[-1,0,0],[1,0,0]]
    assert out['free']['count']==4 and group['remaining_scalar_sensitivity']['count']==2


def test_zero_calculated_intensity_and_empty_partition_stay_explicit():
    c,r,rw,rf=case();r['rows']=[r['rows'][-1]];c['rows']=[[[4,0,0],12.,0.,0.]]
    c['free_scale']=None
    out=summarize(c,r,1.,None)
    assert out['free']['count']==0 and out['free']['r_native'] is None
    assert out['work']['highest_scale_leverage'][0]['scale_denominator_fraction'] is None
    assert out['work']['highest_scale_leverage'][0]['remaining_scalar_sensitivity']['r'] is None


def test_audited_fdp_retains_diagnostics_and_legacy_stays_unchanged(tmp_path):
    from nasolve.metal.fdp import audit_result
    _,_,plan,model=prepared(tmp_path);native=native_result(plan,model)
    old=audit_result(plan,model,native)
    assert 'fit_diagnostics' not in old
    c,r,rw,rf=case();native.update(reflection_before=r,reflection_after=r,r_work=rw,r_free=rf,fit_diagnostics=c)
    out=audit_result(plan,model,native)
    assert out['fit_diagnostics']['free']['count']==3
    assert out['freeze_audit']=='PASS' and out['scientific_acceptance']=='NOT_ASSESSED'
    native['fit_diagnostics']['rows'][0][2]+=10.
    with pytest.raises(ValueError):audit_result(plan,model,native)


def test_native_capture_is_read_only_and_preserves_complex_amplitudes():
    from types import SimpleNamespace
    from nasolve.metal.fit_diagnostics import capture
    class Array:
        def indices(self):return [(2,0,0),(1,0,0)]
        def data(self):return [3+4j,1-2j]
        def d_spacings(self):return SimpleNamespace(data=lambda:[10.,20.])
    f=SimpleNamespace(f_model=lambda:Array(),f_obs=lambda:Array(),scale_k1_w=lambda:1.,scale_k1_t=lambda:2.)
    result=capture(f)
    assert result['rows']==[[[1,0,0],20.,1.,-2.],[[2,0,0],10.,3.,4.]]
    assert len(result['implementation_sha256'])==64


@pytest.mark.parametrize('kind',['xyz','fdp'])
def test_new_bundle_replays_after_source_and_data_are_relocated(tmp_path,monkeypatch,kind):
    import gzip,os,shutil,subprocess,sys
    from pathlib import Path
    from nasolve.metal.recipe import digest
    old=tmp_path/'old'
    if kind=='xyz':
        from tests.test_metal_xyz import fake_execution
        module,c,h,ref,native=fake_execution(old,monkeypatch)
    else:
        from tests.test_metal_fdp import fake_execution
        module,c,g,native=fake_execution(old,monkeypatch)
    fake=module._native
    def enriched(directory,native,timeout):
        e=fake(directory,native,timeout)
        rr=e['reflection_after']['rows']
        e.update(r_work=0.,r_free=0.,fit_diagnostics=dict(protocol='metal-fit-diagnostics-v1',implementation_sha256='a'*64,
            work_scale=1.,free_scale=1.,rows=[[r[0],10.,r[1],0.] for r in rr]))
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()))
        return e
    monkeypatch.setattr(module,'_native',enriched)
    if kind=='xyz':
        doc=module.run_xyz(c.run,'Metal/hypothesis_001',native=native,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'])
        assert 'recipe-geometry.json' in doc['files']
    else:doc=module.run_fdp(c.run,'Metal/geometry_001',native=native,fit_nodes=['m1'])
    source=Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source,old/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved=tmp_path/'moved';old.rename(moved)
    code=f"from nasolve.metal.{kind} import verify_{kind};import sys;print(verify_{kind}(sys.argv[1],'Metal/{kind}_001')['trial_id'])"
    done=subprocess.run([sys.executable,'-B','-c',code,str(moved/'dataset/AutoMR/run_001')],cwd=moved,
        env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=20)
    assert done.returncode==0,done.stderr
    assert done.stdout.strip()==doc['trial_id'] and not old.exists()
    # Changing a derived diagnostic, even with refreshed file/manifest hashes,
    # must fail derivation replay rather than becoming a new trusted result.
    from nasolve.metal.context import _reference
    run=moved/'dataset/AutoMR/run_001';directory=run/f'Metal/{kind}_001'
    filename='recipe-geometry.json' if kind=='xyz' else 'result.json'
    path=directory/filename;value=json.loads(path.read_text())
    if kind=='xyz':value['maximum_absolute_sigma_deviation']=999.
    else:value['fit_diagnostics']['free']['r_native']=.9
    from nasolve.metal.materialize import _json_bytes
    path.write_bytes(_json_bytes(value));doc['files'][filename]=_reference(path,run)
    doc.pop('trial_id');doc['trial_id']=digest(doc);(directory/'manifest.json').write_bytes(_json_bytes(doc))
    with pytest.raises(ValueError):getattr(module,'verify_'+kind)(run,f'Metal/{kind}_001')
