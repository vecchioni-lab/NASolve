"""Captured pair geometry belongs to the written state, not merely matching XYZ."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest

from nasolve import refinement_pair_geometry as geometry
from nasolve.campaign_records import write_record
from nasolve.checkpoints import _file_reference
from nasolve.cif_runtime_evidence import pack_runtime_evidence
from nasolve.topostitch_recipe import recipe_digest
from tests.test_cif_counted_geometry import case, capture


def records(c):
    observed = capture(c)
    state = observed['native_state']
    native = dict(status='COMPLETE',dry_run=False,written_model=dict(model_state_sha256=state['hierarchy_sha256']),
        output_synchronization=[dict(write_completed=True,hierarchy_after_sha256=state['hierarchy_sha256'],
                                    scattering_sha256=state['scattering_sha256'])])
    lifetime = dict(status='COMPLETE',binding_restored=True,owner=c.owner.statistics(),
        pair_geometry_capture=dict(status='CAPTURED',record_sha256=recipe_digest(observed)))
    return observed,native,lifetime


def test_cold_report_uses_final_measurements_and_shared_prepared_inventory(case):
    observed,native,lifetime = records(case)
    result = geometry.review_capture(observed,case.prepared,native,lifetime)
    assert result['force_sites_sha256'] == observed['native_state']['force_sites_sha256']
    assert result['force_sites_sha256'] != case.prepared['native_observation']['native_state']['force_sites_sha256']
    summary = geometry.summary(result)
    assert summary['status']=='OBSERVED' and summary['covalent_geometry']=='UNASSESSED'
    assert summary['unclassified_observed_term_count']==2
    assert 'unclassified_native_terms' not in summary and 'pairs' not in summary
    assert summary['report_sha256']==recipe_digest(result)


@pytest.mark.parametrize('defect', ['hierarchy','scattering','writer','lifetime','inventory','providers','gradient','missing'])
def test_changed_final_proof_is_not_accepted_even_with_resealed_capture(case,defect):
    observed,native,lifetime = records(case)
    if defect in ('hierarchy','scattering'): observed['native_state'][defect+'_sha256']='0'*64
    elif defect=='writer': native['output_synchronization'][0]['write_completed']=False
    elif defect=='lifetime': lifetime['owner']['successful_calls']+=1
    elif defect=='inventory': observed['fixed_observation_sha256']='0'*64
    elif defect=='providers': observed['provider_selection_sha256']='0'*64
    elif defect=='gradient':
        observed['diagnostic_kernel_after']['gradient_calls']+=1
        observed['diagnostic_kernel_after']['successful_calls']+=1
    else: del observed['native_state']['scattering_sha256']
    lifetime['pair_geometry_capture']['record_sha256']=recipe_digest(observed)
    with pytest.raises(ValueError): geometry.review_capture(observed,case.prepared,native,lifetime)


def stored(case,tmp_path):
    observed,native,lifetime=records(case)
    run=tmp_path/'run';root='AutoRefine/round_001/parallelity_runtime'
    base=run/root;preparation=base/'preflight/preparation-work';preparation.mkdir(parents=True)
    (preparation/'prepared.json').write_text(json.dumps(case.prepared))
    archive=base/'preflight/prepared.zip';pack_runtime_evidence(preparation,archive)
    admission=dict(prepared_sha256=recipe_digest(case.prepared),prepared_archive=_file_reference(archive,run))
    write_record(base/'admission.json',admission)
    work=base/'refine/pair-geometry-work';work.mkdir(parents=True)
    (work/'capture.json').write_text(json.dumps(observed))
    (base/'refine/result.json').write_text(json.dumps(native))
    (base/'refine/counted.json').write_text(json.dumps(dict(lifetime=lifetime)))
    return run,root,dict(checkpoint='refine-001'),admission


def test_compact_capture_reads_after_move_and_preserves_prior_evidence(case,tmp_path):
    run,root,request,admission=stored(case,tmp_path)
    before_prepared=(run/root/'preflight/prepared.zip').read_bytes()
    expected=geometry.seal_pair_geometry(run,root,request,admission)
    assert not (run/root/'refine/pair-geometry-work').exists()
    assert (run/root/'preflight/prepared.zip').read_bytes()==before_prepared
    before={p.relative_to(run):(p.read_bytes(),p.stat().st_mtime_ns)for p in run.rglob('*')if p.is_file()}
    moved=run.with_name('moved');run.rename(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('cold read')):
        assert geometry.read_pair_geometry(moved,root,request)==expected
    assert all((moved/p).read_bytes()==data and (moved/p).stat().st_mtime_ns==mtime
               for p,(data,mtime)in before.items())
    archive=moved/root/'refine/pair-geometry.zip';archive.write_bytes(archive.read_bytes()+b'changed')
    with pytest.raises((ValueError,RuntimeError)): geometry.read_pair_geometry(moved,root,request)


def test_failed_archive_verification_preserves_raw_capture(case,tmp_path,monkeypatch):
    run,root,request,admission=stored(case,tmp_path)
    raw=run/root/'refine/pair-geometry-work/capture.json';original=raw.read_bytes()
    def refuse(*args,**kwargs): raise ValueError('archive verification refused')
    monkeypatch.setattr(geometry,'pack_runtime_evidence',refuse)
    with pytest.raises(ValueError,match='archive verification refused'):
        geometry.seal_pair_geometry(run,root,request,admission)
    assert raw.read_bytes()==original and not (run/root/'refine/pair-geometry.json').exists()
