"""Working reconstruction must budget and own all nested proof views."""
from unittest.mock import patch

import pytest
from nasolve import cif_runtime_evidence as evidence
from tests.test_cif_runtime_evidence import source


def archive(tmp_path):
    root=source(tmp_path);out=tmp_path/'working.zip'
    packed=evidence.pack_runtime_evidence(root,out)
    return out,packed


def test_one_explicit_working_view_retains_two_runtime_layers_and_cleans_all(tmp_path):
    out,packed=archive(tmp_path);digest=packed['archive_sha256'];views=[]
    with evidence.expanded_working_evidence(out,digest) as working:
        views.append(working)
        assert evidence._ACTIVE_DEPTH.get()==0
        assert evidence._ACTIVE_BYTES.get()==packed['unique_bytes']
        with evidence.expanded_runtime_evidence(out,digest) as first:
            views.append(first)
            with evidence.expanded_runtime_evidence(out,digest) as second:
                views.append(second)
                assert evidence._ACTIVE_DEPTH.get()==2
                assert evidence._ACTIVE_BYTES.get()==packed['unique_bytes']
                assert (working/'evidence/a/report.json').stat().st_ino==(second/'evidence/a/report.json').stat().st_ino
                with pytest.raises(ValueError,match='depth'):
                    with evidence.expanded_runtime_evidence(out,digest):pytest.fail('Third runtime proof layer')
        assert working.exists() and all(not p.exists() for p in views[1:])
    assert all(not p.exists() for p in views)
    assert evidence._ACTIVE_BYTES.get()==0 and evidence._ACTIVE_DEPTH.get()==0
    assert evidence._ACTIVE_OBJECTS.get() is None


@pytest.mark.parametrize('outer',['runtime','working'])
def test_working_view_is_root_only_not_a_nesting_escape(tmp_path,outer):
    out,packed=archive(tmp_path);digest=packed['archive_sha256']
    owner=evidence.expanded_runtime_evidence if outer=='runtime' else evidence.expanded_working_evidence
    with owner(out,digest):
        with pytest.raises(ValueError,match='outer|root'):
            with evidence.expanded_working_evidence(out,digest):pytest.fail('Nested working view')


def test_working_and_nested_runtime_share_one_physical_allowance(tmp_path,monkeypatch):
    out,packed=archive(tmp_path);other=tmp_path/'other';other.mkdir();(other/'new').write_bytes(b'new bytes')
    extra=tmp_path/'extra.zip';extra_packed=evidence.pack_runtime_evidence(other,extra)
    monkeypatch.setattr(evidence,'MAX_ACTIVE_BYTES',packed['unique_bytes'])
    with evidence.expanded_working_evidence(out,packed['archive_sha256']):
        with pytest.raises(ValueError,match='temporary'):
            with evidence.expanded_runtime_evidence(extra,extra_packed['archive_sha256']):pytest.fail('Exceeded shared bytes')
    assert evidence._ACTIVE_BYTES.get()==0


def test_failed_or_interrupted_working_view_releases_budget_and_temporary_paths(tmp_path):
    out,packed=archive(tmp_path);digest=packed['archive_sha256'];views=[]
    with pytest.raises(RuntimeError,match='reader stopped'):
        with evidence.expanded_working_evidence(out,digest) as working:
            views.append(working)
            with evidence.expanded_runtime_evidence(out,digest) as nested:
                views.append(nested)
                raise RuntimeError('reader stopped')
    assert all(not p.exists() for p in views)
    with pytest.raises(ValueError):
        with evidence.expanded_working_evidence(out,'0'*64):pytest.fail('Bad archive digest')
    with evidence.expanded_working_evidence(out,digest) as fresh:assert fresh.exists()
    assert evidence._ACTIVE_BYTES.get()==0 and evidence._ACTIVE_OBJECTS.get() is None


def test_working_copy_fallback_cannot_bypass_byte_accounting(tmp_path,monkeypatch):
    out,packed=archive(tmp_path)
    monkeypatch.setattr(evidence,'MAX_ACTIVE_BYTES',packed['unique_bytes'])
    with patch.object(evidence.os,'link',side_effect=OSError('no hard links')):
        with pytest.raises(ValueError,match='temporary'):
            with evidence.expanded_working_evidence(out,packed['archive_sha256']):pytest.fail('Uncharged copies')
    assert evidence._ACTIVE_BYTES.get()==0 and evidence._ACTIVE_DEPTH.get()==0
