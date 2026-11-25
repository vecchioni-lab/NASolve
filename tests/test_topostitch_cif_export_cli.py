"""The ordinary command must transport producer identity, not trust incoming bytes."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest
from nasolve.topostitch_recut_bundle import main
from tests.test_topostitch_cif_export import fixture


def command(tmp_path):
    root,original,kw,_,_=fixture(tmp_path)
    options=tmp_path/'options.json';values={k:v for k,v in kw.items() if k!='cedar_source'}
    options.write_text(json.dumps(values))
    output=tmp_path/'export'
    argv=[str(original),'--export-preview',str(root),'--export-options',str(options),
          '--cedar-source',str(kw['cedar_source']),'--out',str(output)]
    return argv,output,kw


def test_cli_producer_digest_replays_after_source_paths_are_removed(tmp_path,capsys):
    old=tmp_path/'old';old.mkdir();argv,out,kw=command(old)
    assert main(argv)==0
    handoff=json.loads(capsys.readouterr().out)
    assert handoff['kind']=='topostitch-whole-asym-export-handoff'
    ref=handoff['receipt'];assert ref['anchor']=='run' and ref['relative_path']=='export.json'
    assert ref['sha256']==sha256((out/'export.json').read_bytes()).hexdigest()
    assert not handoff['selection_applied']
    moved=tmp_path/'moved';moved.mkdir()
    shutil.move(out,moved/'packet');shutil.copytree(kw['cedar_source'],moved/'reader');shutil.rmtree(old)
    replay=['--replay-export',str(moved/'packet'),'--expected-export-sha256',ref['sha256'],
            '--cedar-source',str(moved/'reader')]
    assert main(replay)==0
    assert json.loads(capsys.readouterr().out)['receipt']==ref
    p=moved/'packet/export.json';p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(SystemExit) as exc:main(replay)
    assert exc.value.code==2 and 'receipt differs' in capsys.readouterr().err


@pytest.mark.parametrize('extra',[
    ['--describe-graph'],['--discovery','unused.json'],['--expected-export-sha256','0'*64]])
def test_export_refuses_mixed_modes_before_creating_output(tmp_path,extra):
    argv,out,_=command(tmp_path)
    with pytest.raises(SystemExit) as exc:main(argv+extra)
    assert exc.value.code==2 and not out.exists()


def test_replay_requires_external_digest_and_refuses_export_inputs(tmp_path):
    with pytest.raises(SystemExit) as exc:main(['--replay-export',str(tmp_path),'--cedar-source',str(tmp_path)])
    assert exc.value.code==2
    with pytest.raises(SystemExit) as exc:
        main(['original.cif','--replay-export',str(tmp_path),'--expected-export-sha256','0'*64,'--cedar-source',str(tmp_path)])
    assert exc.value.code==2


def test_cli_refuses_receipt_changed_between_production_and_handoff(tmp_path,monkeypatch,capsys):
    import nasolve.topostitch_cif_output as module
    argv,out,_=command(tmp_path);writer=module.write_whole_asym_cif
    def changed(*args,**kwargs):
        value=writer(*args,**kwargs);(out/'export.json').write_bytes(b'changed');return value
    monkeypatch.setattr(module,'write_whole_asym_cif',changed)
    with pytest.raises(SystemExit) as exc:main(argv)
    captured=capsys.readouterr()
    assert exc.value.code==2 and 'before handoff' in captured.err
    assert captured.out==''
