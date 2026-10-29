"""Count evidence distinguishes explicit atoms, Q-weighting and proxy responses."""
import copy
import json
import pytest
from nasolve.metal.recipe import RecipeError
from nasolve.metal.fdp_count import summarize_count, capture_count, verify_count


def result(elements=('Ag',)*6, occupancy=1., fdp=7.):
    return dict(wavelength_A=2.1, freeze_audit='PASS', sites=[dict(node_id=f'm{i}',element=e,
        occupancy=occupancy,b_iso=300.,f_double_prime=fdp,reference_f_double_prime=7. if e=='Ag' else 10.)
        for i,e in enumerate(elements,1)])


def groups(nodes=None,representation='explicit-sites'):
    return {'cluster':dict(nodes=nodes or [f'm{i}' for i in range(1,7)],representation=representation)}


def test_six_explicit_atoms_use_wavelength_reference_and_q_weighted_sums():
    doc=summarize_count(result(),groups());g=doc['groups'][0];e=g['elements'][0]
    assert g['modeled_site_count']==6
    assert e['q_weighted_fdp_e']==42 and e['q_weighted_reference_e']==42
    assert e['effective_atom_equivalents']==6 and e['response_ratio']==1
    assert g['integer_count_estimate'] is None
    half=summarize_count(result(occupancy=.5),groups())['groups'][0]['elements'][0]
    assert half['effective_atom_equivalents']==3 and half['response_ratio']==1
    assert half['occupancy_sum']==3  # Six half-occupied atoms, not three proven atoms.


def test_unresolved_proxy_and_resolved_sites_do_not_mean_the_same_thing():
    doc=summarize_count(result(('Ag',),fdp=42),groups(['m1'],'unresolved-proxy'))
    g=doc['groups'][0];assert g['modeled_site_count']==1 and g['elements'][0]['effective_atom_equivalents']==6
    assert g['representation']=='unresolved-proxy' and g['integer_count_estimate'] is None
    with pytest.raises(RecipeError):summarize_count(result(),groups(representation='unresolved-proxy'))


def test_mixed_elements_keep_separate_denominators_and_neighbor_exclusions():
    r=result(('Au','Ag','Ag'),fdp=7.)
    r['sites'][0]['f_double_prime']=10.
    r['sites'][2]['f_double_prime']=99.
    d=summarize_count(r,groups(['m1','m2']))
    assert d['excluded_fitted_nodes']==['m3']
    g=d['groups'][0]
    assert g['q_weighted_fdp_e']==17 and g['q_weighted_reference_e']==17
    assert g['response_ratio']==1
    assert {e['element']:e['effective_atom_equivalents'] for e in g['elements']}=={'Au':1,'Ag':1}


def test_negative_and_zero_reference_stay_explicit_without_clipping():
    r=result(('Ag',),fdp=-2.)
    g=summarize_count(r,groups(['m1']))['groups'][0]
    assert g['elements'][0]['effective_atom_equivalents']<0
    assert 'NEGATIVE_FDP' in g['warnings']
    r['sites'][0]['reference_f_double_prime']=0.
    e=summarize_count(r,groups(['m1']))['groups'][0]['elements'][0]
    assert e['response_ratio'] is None and e['effective_atom_equivalents'] is None


@pytest.mark.parametrize('nodes',[[],['m1','m1'],['missing'],['m1','background:I']])
def test_invalid_or_partially_fitted_groups_are_not_silently_summed(nodes):
    with pytest.raises(RecipeError):summarize_count(result(),{'cluster':dict(nodes=nodes,representation='explicit-sites')})


def test_saved_count_report_uses_verified_source_and_detects_changed_report(tmp_path,monkeypatch):
    from tests.test_metal_fdp_endpoint import endpoint
    from nasolve.metal.fdp import run_fdp
    c,h,x,n=endpoint(tmp_path,monkeypatch)
    run_fdp(c.run,'Metal/xyz_001',native=n,fit_nodes=[f'm{i}' for i in range(1,7)],metal_b_policy='donor-mean')
    doc=capture_count(c.run,'Metal/fdp_001',groups())
    assert verify_count(c.run,'Metal/fdp_count_001')==doc
    path=c.run/doc['files']['report']['relative_path'];r=json.loads(path.read_text())
    assert r['source_trial_id'] and r['source_parent']['xyz_trial_id']==x['trial_id']
    r['groups'][0]['modeled_site_count']=7;path.write_text(json.dumps(r))
    with pytest.raises(RecipeError):verify_count(c.run,'Metal/fdp_count_001')


def test_cli_requires_explicit_source_and_reports_count_without_native_discovery(tmp_path,monkeypatch,capsys):
    from nasolve.cli import build_parser,main
    from nasolve.metal import cli
    from tests.test_metal_fdp_endpoint import endpoint
    from nasolve.metal.fdp import run_fdp
    parser=build_parser()
    assert parser.parse_args(['metal','fdp','run','--xyz','Metal/xyz_001','--fit','m1']).xyz.name=='xyz_001'
    with pytest.raises(SystemExit):parser.parse_args(['metal','fdp','run','--xyz','x','--geometry','g','--fit','m1'])
    c,h,x,n=endpoint(tmp_path,monkeypatch)
    run_fdp(c.run,'Metal/xyz_001',native=n,fit_nodes=[f'm{i}' for i in range(1,7)],metal_b_policy='donor-mean')
    path=tmp_path/'groups.json';path.write_text(json.dumps(groups()))
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**kw:pytest.fail('Count replay must be offline'))
    assert main(['metal','count-fdp',str(c.run),'--trial','Metal/fdp_001','--groups',str(path)])==0
    assert '6 modeled sites' in capsys.readouterr().out
    assert main(['metal','verify-fdp-count',str(c.run),'--count-report','Metal/fdp_count_001'])==0


def test_overlapping_groups_remain_separate_and_report_source_convergence():
    r=result();r['convergence']='NOT_INDEPENDENTLY_ASSESSED'
    d=summarize_count(r,{'left':dict(nodes=['m1','m2'],representation='explicit-sites'),
                         'right':dict(nodes=['m2','m3'],representation='explicit-sites')})
    assert len(d['groups'])==2 and d['overlap_policy']=='groups_may_overlap_never_sum_groups'
    assert d['convergence']=='NOT_INDEPENDENTLY_ASSESSED'
    assert 'total_atom_count' not in d


def test_count_bundle_relocates_with_source_removed_and_no_native_execution(tmp_path,monkeypatch):
    import os,shutil,subprocess,sys
    from pathlib import Path
    from tests.test_metal_fdp_endpoint import endpoint
    from nasolve.metal.fdp import run_fdp
    old=tmp_path/'old';c,h,x,n=endpoint(old,monkeypatch)
    run_fdp(c.run,'Metal/xyz_001',native=n,fit_nodes=[f'm{i}' for i in range(1,7)],metal_b_policy='donor-mean')
    doc=capture_count(c.run,'Metal/fdp_001',groups())
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',old/'src',ignore=shutil.ignore_patterns('__pycache__'))
    moved=tmp_path/'moved';old.rename(moved)
    code="from nasolve.metal.fdp_count import verify_count;print(verify_count('dataset/AutoMR/run_001','Metal/fdp_count_001')['report_id'])"
    done=subprocess.run([sys.executable,'-B','-c',code],cwd=moved,
        env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
    assert done.returncode==0,done.stderr
    assert done.stdout.strip()==doc['report_id'] and not old.exists()


def test_early_schema_one_count_without_repeated_convergence_still_replays(tmp_path,monkeypatch):
    from tests.test_metal_fdp_endpoint import endpoint
    from nasolve.metal.fdp import run_fdp
    from nasolve.metal.context import _reference
    from nasolve.metal.materialize import _json_bytes
    from nasolve.metal.recipe import digest
    c,h,x,n=endpoint(tmp_path,monkeypatch)
    run_fdp(c.run,'Metal/xyz_001',native=n,fit_nodes=[f'm{i}' for i in range(1,7)],metal_b_policy='donor-mean')
    doc=capture_count(c.run,'Metal/fdp_001',groups())
    path=c.run/doc['files']['report']['relative_path'];r=json.loads(path.read_text());r.pop('convergence')
    path.write_bytes(_json_bytes(r));doc['files']['report']=_reference(path,c.run)
    doc.pop('report_id');doc['report_id']=digest(doc)
    (path.parent/'manifest.json').write_bytes(_json_bytes(doc))
    assert verify_count(c.run,'Metal/fdp_count_001')==doc
