"""Transport failure preserves the original exception and a usable diagnostic."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import json,sys
import pytest
from tests.test_cedar65_delivery import template
import nasolve.cif_review_transport as transport


@pytest.mark.parametrize('defect',['complete','missing','partial','collection','writer','unsafe'])
def test_failure_report_can_archive_verified_input_without_traversing_history(tmp_path,monkeypatch,defect):
    m=template();m.BUNDLE={'delivery_prefix':'78_Cedar'}
    session=tmp_path/'78_Cedar-session-token';session.mkdir();review=tmp_path/'original.zip';review.write_bytes(b'ORIGINAL ZIP')
    members={'inputs/review/'*90+'native/model.pdb':b'UNCHANGED MODEL','manifest.json':b'UNCHANGED PARENT MANIFEST'}
    if defect in {'complete','collection','writer'}:transport.stage_review_members(members,session/'inputs/review',indexed=True)
    if defect=='partial':
        p=session/'inputs/review/.review-transport/objects/partial.bin';p.parent.mkdir(parents=True);p.write_bytes(b'PARTIAL')
    if defect in {'collection','writer'}:
        def fail(*args):raise OSError(63,'File name too long')
        monkeypatch.setattr(m,'_review_zip',fail)
    if defect=='writer':monkeypatch.setattr(m.zipfile,'ZipFile',lambda *a,**kw:(_ for _ in ()).throw(OSError('NO SPACE')))
    if defect=='unsafe':members={'../outside':b'unsafe'}
    receipt={'native_execution':'NOT_RUN','requires_cif_review':False}
    result=m._report_probe_failure(session,receipt,members,review,b'ORIGINAL ZIP',OSError(63,'ORIGINAL FAILURE'))
    assert receipt['analysis_completed'] is False and receipt['original_archive_preserved']
    assert 'ORIGINAL FAILURE' in receipt['error'] and receipt['error_type']=='OSError'
    assert receipt['native_execution']=='NOT_RUN' and not receipt['requires_cif_review']
    assert receipt['frozen_inputs_preserved'] is (defect in {'complete','collection','writer'})
    assert json.loads((session/'probe_receipt.json').read_bytes())==receipt
    if defect=='writer':
        assert result is None and 'failure_archive_error' in receipt
        return
    with ZipFile(result) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert len(manifest)+1==len(z.namelist())
        for name,ref in manifest.items():assert sha256(z.read(name)).hexdigest()==ref['sha256']
        if defect!='unsafe':
            for name,data in members.items():assert z.read('inputs/review/'+name)==data
        else:assert z.namelist()==['probe_receipt.json','manifest.json']


def test_main_staging_error_still_emits_capsule_and_original_error(tmp_path,monkeypatch,capsys):
    m=template();m.BUNDLE={'delivery_prefix':'78_Cedar','component_controls':[]}
    review=tmp_path/'source/review.zip';review.parent.mkdir();review.write_bytes(b'ORIGINAL ZIP')
    members={'inputs/review/'*90+'native/model.pdb':b'FROZEN','manifest.json':b'PARENT MANIFEST'}
    monkeypatch.setattr(m,'_runtime_members',lambda:{})
    monkeypatch.setattr(m,'_read_capsule',lambda path:(members,{},{},{},b'ORIGINAL ZIP'))
    def failed_stage(members,target,**kwargs):
        assert kwargs['indexed'] is True
        p=target/'.review-transport/objects/partial.bin';p.parent.mkdir(parents=True);p.write_bytes(b'PARTIAL')
        raise OSError(63,'SIMULATED MAC PATH LIMIT')
    monkeypatch.setattr(transport,'stage_review_members',failed_stage)
    monkeypatch.setattr(sys,'path',list(sys.path));monkeypatch.setattr(sys,'argv',['probe','--review-zip',str(review),'--output-parent',str(tmp_path/'out'),'--component','DP','--postmr-cached-model-only','--inspect-only'])
    assert m.main()==2
    captured=capsys.readouterr();assert 'SIMULATED MAC PATH LIMIT' in captured.err and 'Traceback' not in captured.err
    assert 'REVIEW ZIP:' in captured.out
    archive=next((tmp_path/'out').glob('*/*_failure_review.zip'))
    with ZipFile(archive) as z:
        receipt=json.loads(z.read('probe_receipt.json'))
        assert receipt['native_execution']=='NOT_RUN' and receipt['frozen_inputs_preserved'] is False
        for name,data in members.items():assert z.read('inputs/review/'+name)==data


def test_main_with_long_history_survives_a_mac_path_limit(tmp_path,monkeypatch,capsys):
    from tests.test_cif_review_indexed import limit_paths
    m=template();m.BUNDLE={'delivery_prefix':'78_Cedar','component_controls':[]}
    review=tmp_path/'source/review.zip';review.parent.mkdir();review.write_bytes(b'ORIGINAL ZIP')
    members={'inputs/review/'*90+'native/model.pdb':b'FROZEN','manifest.json':b'PARENT MANIFEST'}
    monkeypatch.setattr(m,'_runtime_members',lambda:{})
    monkeypatch.setattr(m,'_read_capsule',lambda path:(members,{},{},{},b'ORIGINAL ZIP'))
    def stop_after_stage(*args):raise ValueError('BOUNDED POST-STAGING TEST')
    monkeypatch.setattr(m,'_source_view',stop_after_stage)
    monkeypatch.setattr(sys,'path',list(sys.path));monkeypatch.setattr(sys,'argv',['probe','--review-zip',str(review),'--output-parent',str(tmp_path/'out'),'--component','DP','--postmr-cached-model-only','--inspect-only'])
    seen=limit_paths(monkeypatch)
    assert m.main()==2 and max(seen)<1024
    captured=capsys.readouterr();assert 'BOUNDED POST-STAGING TEST' in captured.err and 'REVIEW ZIP:' in captured.out
    archive=next((tmp_path/'out').glob('*/*_review.zip'))
    with ZipFile(archive) as z:
        receipt=json.loads(z.read('probe_receipt.json'))
        assert receipt['native_execution']=='NOT_RUN' and receipt['frozen_inputs_preserved'] is True
        for name,data in members.items():assert z.read('inputs/review/'+name)==data
