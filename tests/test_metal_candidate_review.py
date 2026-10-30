"""Cross-geometry reviews keep grouped endpoints distinct from matched sensitivity."""
import copy
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from nasolve.metal import fdp
from nasolve.metal.candidate_review import build_review, verify_review
from nasolve.metal.context import _reference
from nasolve.metal.fdp_compare import build_comparison
from nasolve.metal.materialize import _json_bytes
from nasolve.metal.recipe import RecipeError, digest
from tests.test_metal_xyz import fake_execution
from tests.test_metal_fdp import native_result


def cases(tmp_path, monkeypatch, *, second=None):
    from nasolve.metal import xyz
    xyz,c,h,ref,native=fake_execution(tmp_path,monkeypatch)
    for name in ('inspect_observations','reference_scattering','audit_free_r_flags'):
        monkeypatch.setattr(fdp,name,getattr(xyz,name))
    def fit(directory,*args):
        plan=json.loads((directory/'plan.json').read_text());raw=(directory/'input.pdb').read_bytes()
        e=native_result(plan,raw)
        for group in e['groups']:
            if group['refine_fdp']:
                value=-2. if group['element']=='Au' else 4.
                group['f_double_prime']=value
                for i in group['indices']:e['atoms'][i]['fdp']=value
        (directory/'final.pdb').write_bytes(raw)
        (directory/'native-result.json.gz').write_bytes(gzip.compress(_json_bytes(e)))
        return e
    monkeypatch.setattr(fdp,'_native',fit)
    paths=[]
    for i,cycles in enumerate((3,10)):
        doc=xyz.run_xyz(c.run,'Metal/hypothesis_001',native=native,phases=ref,
                       phase_labels=['HLAM','HLBM','HLCM','HLDM'],cycles=cycles)
        options=dict(fit_nodes=['m1','m2'],metal_b_policy='keep')
        if i and second:options.update(second)
        fd=fdp.run_fdp(c.run,Path(doc['files']['result.json']['relative_path']).parent,native=native,**options)
        paths.append(Path(fd['files']['result.json']['relative_path']).parent)
    return c,paths


def report(run,doc):return json.loads((run/doc['files']['report']['relative_path']).read_text())


def test_grouped_review_preserves_stage_metrics_and_strict_comparison(tmp_path,monkeypatch):
    c,paths=cases(tmp_path,monkeypatch)
    before={str(p.relative_to(c.run)):p.read_bytes() for p in c.run.rglob('*') if p.is_file()}
    with pytest.raises(RecipeError,match='same geometry'):build_comparison(c.run,paths)
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw:pytest.fail('Review must be offline'))
    doc=build_review(c.run,paths);data=report(c.run,doc)
    assert len(data['candidates'])==2
    for row in data['candidates']:
        assert len(row['anomalous']['sites'])==2
        assert row['anomalous']['sites'][0]['fdp_ratio']==pytest.approx(-2/3)
        assert row['anomalous']['sites'][0]['f_double_prime']==-2
        assert row['geometry']['maps'] is None and row['anomalous']['map'] is None
        assert row['geometry']['fit']['scientific_acceptance']=='NOT_ASSESSED'
        assert row['anomalous']['fit']['scientific_acceptance']=='NOT_ASSESSED'
        assert row['geometry']['recipe_geometry']['protocol']=='metal-recipe-endpoint-v1'
    assert 'xyz_options' in data['candidates'][1]['changed_from_first']
    assert data['scientific_acceptance']=='NOT_ASSESSED'
    assert data['automatic_checkpoint_selection'] is False
    assert data['controlled_sensitivity']=='NOT_ESTABLISHED'
    assert verify_review(c.run,'Metal/candidate_review_001')==doc
    assert all((c.run/p).read_bytes()==v for p,v in before.items())


def test_free_flag_mismatch_rejected_before_allocation(tmp_path,monkeypatch):
    c,paths=cases(tmp_path,monkeypatch,second={'free_r_test_value':1})
    with pytest.raises(RecipeError,match='observation|protocol'):build_review(c.run,paths)
    assert not list((c.run/'Metal').glob('candidate_review_*'))


@pytest.mark.parametrize('selection',[[],[0],[0,0],list(range(33))])
def test_invalid_inventory_never_allocates(tmp_path,monkeypatch,selection):
    c,paths=cases(tmp_path,monkeypatch)
    with pytest.raises(RecipeError):build_review(c.run,[paths[i%2] for i in selection])
    assert not list((c.run/'Metal').glob('candidate_review_*'))


@pytest.mark.parametrize('change',['report','manifest','input','extra','symlink'])
def test_rehashed_tampering_rejected(tmp_path,monkeypatch,change):
    c,paths=cases(tmp_path,monkeypatch);doc=build_review(c.run,paths)
    d=c.run/'Metal/candidate_review_001'
    if change=='report':
        data=report(c.run,doc);data['candidates'][0]['anomalous']['sites'][0]['fdp_ratio']=99
        (d/'report.json').write_bytes(_json_bytes(data));doc['files']['report']=_reference(d/'report.json',c.run)
    elif change=='manifest':doc['scientific_acceptance']='ACCEPTED'
    elif change=='input':(c.run/paths[0]/'result.json').write_text('{}')
    elif change=='extra':(d/'unexpected').write_text('extra')
    else:
        original=d/'report.json';target=tmp_path/'report.json';original.rename(target);original.symlink_to(target)
    doc.pop('review_id');doc['review_id']=digest(doc);(d/'manifest.json').write_bytes(_json_bytes(doc))
    with pytest.raises(RecipeError):verify_review(c.run,d)


def test_relocated_source_and_data_replay_without_original_paths_or_native(tmp_path,monkeypatch):
    c,paths=cases(tmp_path/'old',monkeypatch);doc=build_review(c.run,paths)
    old=tmp_path/'old';source=Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source,old/'src',ignore=shutil.ignore_patterns('__pycache__'))
    relative=c.run.relative_to(old);new=tmp_path/'moved';old.rename(new)
    code='''import subprocess,sys
from pathlib import Path
from nasolve.metal.candidate_review import verify_review
from nasolve.metal import fdp,xyz
def forbidden(*a,**kw):raise AssertionError("Offline replay invoked native")
subprocess.run=forbidden;fdp._native=forbidden;xyz._native=forbidden
assert verify_review(Path(sys.argv[1]),"Metal/candidate_review_001")["review_id"]==sys.argv[2]
print("relocated review PASS")
'''
    env=dict(os.environ,PYTHONPATH=str(new/'src'),PYTHONDONTWRITEBYTECODE='1')
    out=subprocess.run([sys.executable,'-B','-c',code,str(new/relative),doc['review_id']],env=env,cwd=new,text=True,capture_output=True)
    assert out.returncode==0,out.stderr
    assert not old.exists()

@pytest.mark.parametrize('field',['observations','metadata','reflection_input_hash','geometry_phases',
                                 'geometry_worker_sha256','native_source_hashes','phase_metadata'])
def test_review_rejects_unmatched_scientific_controls(tmp_path,monkeypatch,field):
    from nasolve.metal import candidate_review as review
    c,paths=cases(tmp_path,monkeypatch)
    values=[review._load_candidate(c.run,p) for p in paths]
    values[1]['common'][field]={'changed':'control'}
    monkeypatch.setattr(review,'_load_candidate',lambda run,path:values[paths.index(path)])
    with pytest.raises(RecipeError,match='share observations'):review.build_review(c.run,paths)
    assert not list((c.run/'Metal').glob('candidate_review_*'))


def test_shared_element_reference_mismatch_is_not_normalized_away(tmp_path,monkeypatch):
    from nasolve.metal import candidate_review as review
    c,paths=cases(tmp_path,monkeypatch)
    values=[review._load_candidate(c.run,p) for p in paths]
    values[1]['references'][0]['f_double_prime']+=1
    monkeypatch.setattr(review,'_load_candidate',lambda run,path:values[paths.index(path)])
    with pytest.raises(RecipeError,match='conflicting wavelength'):review.build_review(c.run,paths)


def test_different_fitted_membership_is_explicit_without_implicit_site_matching(tmp_path,monkeypatch):
    c,paths=cases(tmp_path,monkeypatch,second={'fit_nodes':['m1']})
    data=report(c.run,build_review(c.run,paths))
    assert [r['anomalous']['fitted_site_count'] for r in data['candidates']]==[2,1]
    assert 'groups' in data['candidates'][1]['changed_from_first']
    assert data['automatic_checkpoint_selection'] is False


def test_zero_expected_response_remains_undefined(tmp_path,monkeypatch):
    from nasolve.metal import candidate_review as review
    c,paths=cases(tmp_path,monkeypatch)
    original=review._load_trial
    def zero(run,path):
        value=original(run,path)
        value['result']['sites'][0]['reference_f_double_prime']=0.
        return value
    monkeypatch.setattr(review,'_load_trial',zero)
    data=review._load_candidate(c.run,paths[0])['row']
    assert data['anomalous']['sites'][0]['fdp_ratio'] is None
    assert data['anomalous']['sites'][0]['normalization_status']=='ZERO_REFERENCE'


def test_recipe_geometry_parent_is_not_presented_as_refined_xyz(tmp_path,monkeypatch):
    from tests.test_metal_fdp_compare import trials
    c,paths=trials(tmp_path,monkeypatch)
    with pytest.raises(RecipeError,match='XYZ|xyz'):build_review(c.run,paths[:2])
    assert not list((c.run/'Metal').glob('candidate_review_*'))


def test_source_change_during_publication_leaves_failed_numbered_attempt(tmp_path,monkeypatch):
    from nasolve.metal import candidate_review as review
    c,paths=cases(tmp_path,monkeypatch);original=review._load_candidates;calls=0
    def changing(run,items):
        nonlocal calls
        calls+=1;data=original(run,items)
        if calls==2:data[0]['row']['conditions']['xyz_options']['cycles']=9
        return data
    monkeypatch.setattr(review,'_load_candidates',changing)
    with pytest.raises(RecipeError,match='changed during'):review.build_review(c.run,paths)
    assert (c.run/'Metal/candidate_review_001/failure.json').is_file()
    assert not (c.run/'Metal/candidate_review_001/manifest.json').exists()
    monkeypatch.setattr(review,'_load_candidates',original)
    doc=review.build_review(c.run,paths)
    assert 'candidate_review_002' in doc['files']['report']['relative_path']
