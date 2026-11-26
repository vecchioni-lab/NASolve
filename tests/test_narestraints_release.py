from io import BytesIO
import json
from urllib.error import URLError

import pytest


@pytest.mark.parametrize(("installed","tag","phrase"), [
    ("1.1.4","v1.1.4","up to date"), ("1.9.0","v1.10.0","update available"),
    ("1.1.4rc1","v1.1.4","update available"), ("1.2.0.dev1","v1.1.4","ahead"),
    ("not installed","v1.1.4","install"), ("unversioned","v1.1.4","could not compare"),
])
def test_latest_release_reports_the_installed_version(monkeypatch, installed, tag, phrase):
    from nasolve import narestraints_release as release
    def reply(request, *, timeout):
        assert request.full_url == "https://api.github.com/repos/vecchioni-lab/NARestraints/releases/latest"
        assert 0 < timeout <= 5
        return BytesIO(json.dumps({"tag_name":tag,"draft":False,"prerelease":False}).encode())
    monkeypatch.setattr(release, "urlopen", reply)
    assert phrase in release.release_status(installed).lower()


@pytest.mark.parametrize("body", [b"{}", b"broken", b"x" * 262145,
    b'{"tag_name":"unstable","draft":false,"prerelease":false}',
    b'{"tag_name":"v1.2.0","draft":true,"prerelease":false}',
    b'{"tag_name":"v1.2.0rc1","draft":false,"prerelease":true}'],
    ids=["empty","invalid-json","oversize","invalid-tag","draft","prerelease"])
def test_unusable_release_never_blocks_the_local_check(monkeypatch, body):
    from nasolve import narestraints_release as release
    monkeypatch.setattr(release,"urlopen",lambda *a,**kw: BytesIO(body))
    assert "unavailable" in release.release_status("1.1.4")


def test_offline_check_skips_network_and_online_check_survives_timeout(monkeypatch,capsys):
    from nasolve import cli, narestraints_release as release
    calls=[]
    def offline(*args,**kwargs):
        calls.append(1)
        raise URLError("offline")
    def missing(*args,**kwargs):
        raise cli.PhenixDiscoveryError("intentionally unavailable")
    monkeypatch.setattr(release,"urlopen",offline)
    monkeypatch.setattr(cli,"discover_phenix",missing)
    monkeypatch.setattr(cli,"_narestraints_version",lambda:"1.1.4")
    assert cli.main(["check","--offline"])==1
    assert not calls and "1.1.4" in capsys.readouterr().out
    assert cli.main(["check"])==1
    assert calls==[1] and "unavailable" in capsys.readouterr().out
