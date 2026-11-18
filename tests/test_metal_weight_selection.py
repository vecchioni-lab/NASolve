"""A completed XYZ search must expose native Rfree fallback and its scope."""
import copy
import json
from types import SimpleNamespace as S
import pytest
from nasolve.metal.weight_selection import observe, summarize, FIELDS


def harness(*, bonds=(.08,.07), angles=(1.,1.), rf=(.3,.32), r_free_only=False):
    trials=[dict(rw=r-.02,rf=r,rfrw=.02,b=b,a=a,clsc=99999,rama=0.,rota=0.,cbet=0.,w=float(i+1))
            for i,(b,a,r)in enumerate(zip(bonds,angles,rf))]
    class Scorer:
        def __init__(self):
            self.finalized=False;self.r_free_only=r_free_only;self.eps=1e-4
            for f in FIELDS:setattr(self,f,[t[f]for t in trials])
            self.sites_frac_all=[[(i*.1,0.,0.)]for i in range(len(trials))]
        def _select(self,sel):
            if not any(sel):sel=[abs(r-min(self.rf))<1e-4 for r in self.rf]
            for f in (*FIELDS,'sites_frac_all'):
                setattr(self,f,[v for v,keep in zip(getattr(self,f),sel)if keep])
        def finalize(self,r_free_range_width,r_free_r_work_gap,bond_rmsd,angle_rmsd):
            if self.finalized:return
            self.finalized=True
            if len(self.w)==1:return
            if self.r_free_only:
                self._select([b<=.029 and r<=min(self.rf)+1e-6 for b,r in zip(self.b,self.rf)])
            else:
                self._select([b<=bond_rmsd and a<=angle_rmsd and gap<=r_free_r_work_gap/100
                              and r<=min(self.rf)+r_free_range_width/100
                              for b,a,gap,r in zip(self.b,self.a,self.rfrw,self.rf)])
                scores=[round(a+b+c,1)for a,b,c in zip(self.rama,self.rota,self.cbet)]
                self._select([s<=min(scores)for s in scores])
                self._select([abs(r-min(self.rf))<=self.eps for r in self.rf])
                self._select([abs(r-min(self.rfrw))<=self.eps for r in self.rfrw])
    class Run:
        def __init__(self,macro_cycle):
            self.wx_scale=.5;self.scorer=Scorer()
            self.scorer.finalize(5.,5.,.015,2.)
            self.scorer.finalize(5.,5.,.015,2.) # Native finalized calls are no-ops.
    module=S(run_all=Run,xyz_refinement_scorer=Scorer)
    context=observe(_module=module,_source_hashes={'xyz_reciprocal_space':'a'*64})
    return module,context


def capture(cycles=1, **kwargs):
    m,o=harness(**kwargs);plain=m.run_all(1)
    bindings=(m.run_all.__init__,m.xyz_refinement_scorer.finalize,m.xyz_refinement_scorer._select)
    with o:
        for cycle in range(1,cycles+1):observed=m.run_all(cycle)
    assert bindings==(m.run_all.__init__,m.xyz_refinement_scorer.finalize,m.xyz_refinement_scorer._select)
    assert vars(plain.scorer)==vars(observed.scorer)
    return o.receipt()


def test_reports_geometry_failure_fallback_without_accepting_model():
    e=capture();out=summarize(e);d=out['decisions'][0]
    assert d['mode']=='RFREE_FALLBACK'and d['initial_eligible_count']==0
    assert d['selected_trial']['w']==1 and d['selected_trial']['rf']==.3
    assert 'not final'in out['r_factor_scope']
    assert out['scientific_acceptance']=='NOT_ASSESSED'
    assert out['automatic_checkpoint_selection']is False
    assert 'covalent-only' in out['metric_scope']


def test_geometry_eligible_candidate_beats_lower_rfree_and_native_state_is_unchanged():
    out=summarize(capture(bonds=(.08,.01)))
    d=out['decisions'][0]
    assert d['mode']=='NATIVE_CRITERIA'and d['initial_eligible_count']==1
    assert d['selected_trial']['w']==2 and d['selected_trial']['rf']==.32


def test_singleton_is_not_evidence_that_geometry_criteria_passed():
    d=summarize(capture(bonds=(.08,),angles=(8.,),rf=(.3,)))['decisions'][0]
    assert d['mode']=='SINGLE_TRIAL'and d['initial_eligible_count']is None


@pytest.mark.parametrize('bonds,mode',[((.01,.01),'NATIVE_CRITERIA'),((.08,.08),'RFREE_FALLBACK')])
def test_rfree_only_native_branch(bonds,mode):
    d=summarize(capture(bonds=bonds,r_free_only=True))['decisions'][0]
    assert d['mode']==mode and d['selected_trial']['w']==1


@pytest.mark.parametrize('change',['mask','fallback','subset','choice','gap','nan','hash','criteria','stages','complete','restored','boolean_index','mode','scale','epsilon'])
def test_resealed_contradictory_evidence_is_rejected(change):
    e=capture();d=e['decisions'][0]
    if change=='mask':d['steps'][0]['requested_mask'][0]=True
    if change=='fallback':d['steps'][0]['fallback']=False
    if change=='subset':d['steps'][0]['remaining_indices']=[1]
    if change=='choice':d['selected_index']=1
    if change=='gap':d['trials'][0]['rfrw']=.2
    if change=='nan':d['trials'][0]['b']=float('nan')
    if change=='hash':e['native_sources']['xyz_reciprocal_space']='bad'
    if change=='criteria':d['criteria']['bond_rmsd']=1
    if change=='stages':d['steps'].pop()
    if change=='complete':e['capture_complete']=False
    if change=='restored':e['binding_restored']=False
    if change=='boolean_index':d['selected_index']=False
    if change=='mode':d['r_free_only']=True
    if change=='scale':d['wx_scale']=0
    if change=='epsilon':d['eps']=.1
    with pytest.raises(ValueError):summarize(e)


def test_exception_restores_owned_bindings_and_preserves_primary():
    m,o=harness();before=m.run_all.__init__;primary=RuntimeError('native failed')
    with pytest.raises(RuntimeError)as exc:
        with o:
            m.run_all(1)
            raise primary
    assert exc.value is primary and m.run_all.__init__ is before
    assert not o.receipt()['capture_complete']


def test_foreign_hook_not_overwritten_on_exit():
    m,o=harness();foreign=lambda *a,**k:None
    with pytest.raises(ValueError,match='ownership'):
        with o:m.xyz_refinement_scorer._select=foreign
    assert m.xyz_refinement_scorer._select is foreign


def test_nested_observer_rejected_without_displacing_owner():
    m,o=harness();other=observe(_module=m,_source_hashes={'xyz_reciprocal_space':'a'*64})
    with o:
        with pytest.raises(ValueError,match='owned'):
            with other:pass
        m.run_all(1)
    assert summarize(o.receipt())['trial_count']==2


def test_xyz_audit_legacy_unchanged_and_new_single_trial_visible(tmp_path):
    from tests.test_metal_xyz import prepared,evidence
    xyz,c,h,raw,plan,ref=prepared(tmp_path);native=evidence(plan,raw)
    old=xyz.audit_result(plan,raw,native,raw)
    native['weight_selection']=capture(cycles=plan['policy']['cycles'],bonds=(.08,),angles=(8.,),rf=(.3,))
    new=xyz.audit_result(plan,raw,native,raw)
    assert new['weight_selection']['decisions'][0]['mode']=='SINGLE_TRIAL'
    assert new['fdp_quantitation_ready']is False
    new.pop('weight_selection');assert new==old


def test_sidecar_missing_changed_or_orphan_rejected(tmp_path):
    from nasolve.metal.weight_selection import verify_file
    e={'weight_selection':capture()};p=tmp_path/'weight-selection.json'
    verify_file({},tmp_path)
    with pytest.raises(ValueError):verify_file(e,tmp_path)
    p.write_text(json.dumps(e['weight_selection']));verify_file(e,tmp_path)
    with pytest.raises(ValueError):verify_file({},tmp_path)
    e['weight_selection']['decisions'][0]['trials'][0]['w']=.5
    with pytest.raises(ValueError):verify_file(e,tmp_path)


def test_receipt_relocates_without_original_and_false_summary_rejected(tmp_path,monkeypatch):
    import gzip,os,shutil,subprocess,sys
    from pathlib import Path
    from tests.test_metal_xyz import fake_execution
    from nasolve.metal.context import _reference
    from nasolve.metal.recipe import digest,RecipeError
    old=tmp_path/'original';xyz,c,h,ref,n=fake_execution(old,monkeypatch);fake=xyz._native
    def enriched(directory,native,timeout):
        e=fake(directory,native,timeout);receipt=capture(cycles=3,bonds=(.08,),angles=(8.,),rf=(.3,))
        e['weight_selection']=receipt
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()))
        (directory/'weight-selection.json').write_text(json.dumps(receipt))
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
    value['weight_selection']['decisions'][0]['mode']='NATIVE_CRITERIA';p.write_text(json.dumps(value))
    manifest=json.loads((directory/'manifest.json').read_text());manifest['files']['result.json']=_reference(p,run)
    manifest.pop('trial_id');manifest['trial_id']=digest(manifest);(directory/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(RecipeError,match='XYZ audit changed'):xyz.verify_xyz(run,'Metal/xyz_001')


@pytest.mark.parametrize('mismatch',['cycle','missing_cycle','unexpected_search'])
def test_xyz_rejects_selection_history_outside_requested_protocol(tmp_path,mismatch):
    from tests.test_metal_xyz import prepared,evidence
    from nasolve.metal.recipe import RecipeError
    xyz,c,h,raw,plan,ref=prepared(tmp_path);native=evidence(plan,raw)
    cycles=plan['policy']['cycles'];kwargs=dict(bonds=(.08,),angles=(8.,),rf=(.3,))
    if mismatch=='missing_cycle':cycles-=1
    if mismatch=='unexpected_search':kwargs={}
    receipt=capture(cycles=cycles,**kwargs)
    if mismatch=='cycle':receipt['decisions'][-1]['cycle']+=1
    native['weight_selection']=receipt
    with pytest.raises(RecipeError,match='weight'):
        xyz.audit_result(plan,raw,native,raw)
