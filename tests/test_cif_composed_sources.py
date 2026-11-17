"""Composition provenance travels with selected sources, without a new owner."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from nasolve import cif_acquisition_sources as m
from nasolve.campaign_records import write_record
from tests.test_cif_acquisition_sources import inventory, sources
from tests.test_cif_explicit_sources import forbidden
from tests.test_cif_reference_composition import inputs, compose
from tests.test_cif_complete_request import case


def selection(tmp_path, code='DY'):
    original=tmp_path/'original';original.mkdir()
    backbone,reference=inputs(original)
    payload,proof=compose(backbone,reference,code)
    source=original/'composed.cif';source.write_bytes(payload)
    choices={code:dict(backbone=(backbone,'DT'),reference=(reference,'DY'))}
    return source,choices,proof,tmp_path/'selection'


def freeze(source,choices,out):
    code=next(iter(choices))
    return m.freeze_acquisition_sources([code],out,explicit_sources={code:source},composition_inputs=choices)


@pytest.mark.parametrize('code',['DY','Q17'])
def test_composed_source_replays_after_originals_and_package_disappear(tmp_path,monkeypatch,code):
    source,choices,proof,out=selection(tmp_path,code)
    monkeypatch.setattr(m,'ligand_source',forbidden)
    with patch('subprocess.Popen',side_effect=forbidden):report=freeze(source,choices,out)
    assert report['policy_id']=='cif-acquisition-composed-sources-v1'
    assert report['compositions'][code]['proof']==proof
    assert report['scientific_qualification']=='NOT_ASSESSED' and report['automatic_adoption'] is False
    assert report['sources'][code]['source_kind']=='explicit-file'
    expected=source.read_bytes();before=inventory(out)
    shutil.rmtree(source.parent);out=out.rename(tmp_path/'relocated')
    import nasolve.cif_packaged_reference as packaged
    monkeypatch.setattr(packaged,'_directory',forbidden)
    with patch('subprocess.Popen',side_effect=forbidden):result=m.read_acquisition_sources(out)
    assert result['report']==report and result['sources'][code]['source'].read_bytes()==expected
    assert inventory(out)==before
    assert set(before)=={'source_selection.json',f'sources/{code}.cif',
        f'compositions/{code}/backbone.cif',f'compositions/{code}/reference.cif'}


@pytest.mark.parametrize('defect',['empty','not_mapping','not_explicit','extra_code','curated',
    'extra_role','missing_role','bad_role','bad_code','missing','symlink','wrong_identity','wrong_output'])
def test_bad_composition_inputs_never_publish(tmp_path,defect):
    source,choices,_,out=selection(tmp_path)
    explicit={'DY':source};codes=['DY']
    if defect=='empty':choices={}
    elif defect=='not_mapping':choices=[]
    elif defect=='not_explicit':explicit=None
    elif defect=='extra_code':choices['QQQ']=choices['DY']
    elif defect=='curated':choices={'DF':choices['DY']};codes=['DF'];explicit={'DF':source}
    elif defect=='extra_role':choices['DY']['ideal']=choices['DY']['reference']
    elif defect=='missing_role':choices['DY'].pop('backbone')
    elif defect=='bad_role':choices['DY']['reference']=str(source)
    elif defect=='bad_code':choices['DY']['reference']=(choices['DY']['reference'][0],'../DY')
    elif defect=='missing':choices['DY']['reference'][0].unlink()
    elif defect=='symlink':
        p=source.parent/'link.cif';p.symlink_to(choices['DY']['reference'][0]);choices['DY']['reference']=(p,'DY')
    elif defect=='wrong_identity':choices['DY']['reference']=(choices['DY']['reference'][0],'QQQ')
    else:source.write_bytes(source.read_bytes()+b'# not the composed output\n')
    with pytest.raises((ValueError,TypeError,OSError)):
        m.freeze_acquisition_sources(codes,out,explicit_sources=explicit,composition_inputs=choices)
    assert not out.exists()


@pytest.mark.parametrize('defect',['drop','old_policy','extra','input_bytes','input_pin','input_path',
    'role','proof','proof_boolean','output_bytes','missing','symlink','temporary'])
def test_resigned_record_cannot_invent_composition(tmp_path,defect):
    source,choices,_,out=selection(tmp_path);report=freeze(source,choices,out)
    row=report['compositions']['DY'];ref=out/'compositions/DY/reference.cif'
    if defect=='drop':report.pop('compositions')
    elif defect=='old_policy':report['policy_id']=m.EXPLICIT_POLICY_ID
    elif defect=='extra':row['qualified']=True
    elif defect=='input_bytes':ref.write_bytes(ref.read_bytes()+b'# changed\n')
    elif defect=='input_pin':
        ref.write_bytes(ref.read_bytes()+b'# changed\n')
        row['inputs']['reference']['artifact'].update(sha256=sha256(ref.read_bytes()).hexdigest(),size=ref.stat().st_size)
    elif defect=='input_path':row['inputs']['reference']['artifact']['path']='../../original/reference.cif'
    elif defect=='role':row['inputs']['reference']['component']='DT'
    elif defect=='proof':row['proof']['atom_origins']['N1']['role']='backbone'
    elif defect=='proof_boolean':row['proof']['automatic_adoption']=0
    elif defect=='output_bytes':
        p=out/'sources/DY.cif';p.write_bytes(p.read_bytes()+b'# changed\n')
        report['sources']['DY']['artifact'].update(sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
    elif defect=='missing':ref.unlink()
    elif defect=='symlink':ref.unlink();ref.symlink_to(choices['DY']['reference'][0])
    else:(out/'compositions/DY/.record-extra').write_text('extra')
    write_record(out/'source_selection.json',report,replace=True)
    with pytest.raises((ValueError,OSError)):m.read_acquisition_sources(out)


@pytest.mark.parametrize('stage',['compose','copy','readback'])
def test_changed_composition_input_is_detected(tmp_path,monkeypatch,stage):
    from nasolve import cif_reference_composition as compositor
    source,choices,_,out=selection(tmp_path);reference=choices['DY']['reference'][0]
    if stage=='compose':
        original=compositor.compose_dna_source
        def changed(*a,**kw):
            result=original(*a,**kw);reference.write_bytes(reference.read_bytes()+b'# changed\n');return result
        monkeypatch.setattr(compositor,'compose_dna_source',changed)
    elif stage=='copy':
        original=m._reference
        def changed(*a,**kw):
            result=original(*a,**kw);reference.write_bytes(reference.read_bytes()+b'# changed\n');return result
        monkeypatch.setattr(m,'_reference',changed)
    else:
        freeze(source,choices,out);reference=out/'compositions/DY/reference.cif'
        original=compositor.compose_dna_source
        def changed(*a,**kw):
            result=original(*a,**kw);reference.write_bytes(reference.read_bytes()+b'# changed\n');return result
        monkeypatch.setattr(compositor,'compose_dna_source',changed)
        with pytest.raises(ValueError):m.read_acquisition_sources(out)
        return
    with pytest.raises(ValueError):freeze(source,choices,out)
    assert not (out/'source_selection.json').exists()
    if out.exists():
        before=inventory(out)
        with pytest.raises(FileExistsError):freeze(source,choices,out)
        assert inventory(out)==before


def test_complete_owner_keeps_composition_without_sdk_or_originals(case,tmp_path,monkeypatch):
    complete,args,out,_,_,_,calls=case
    old=m.read_acquisition_sources(args['source_selection'])
    code=old['report']['components'][0]
    source,choices,_,selection_dir=selection(tmp_path,code)
    paths={c:row['source'] for c,row in old['sources'].items()};paths[code]=source
    m.freeze_acquisition_sources(list(paths),selection_dir,explicit_sources=paths,composition_inputs=choices)
    args=deepcopy(args);args['source_selection']=selection_dir
    for item in args['components']:
        if item['code']==code:item.pop('retained_snapshot')
    with patch('subprocess.Popen',side_effect=forbidden):complete.initialize_dictionary_request(output=out,**args)
    expected=m.read_acquisition_sources(out/'inputs/sources')['report']
    shutil.rmtree(source.parent);shutil.rmtree(selection_dir)
    moved=out.rename(tmp_path/'relocated-request');before=inventory(moved)
    monkeypatch.setattr(m,'ligand_source',forbidden)
    with patch('subprocess.Popen',side_effect=forbidden):state=complete.inspect_dictionary_request(moved)
    assert state['availability']=='AVAILABLE' and state['attempts']==[] and not calls
    assert m.read_acquisition_sources(moved/'inputs/sources')['report']==expected
    assert inventory(moved)==before


def test_composed_and_ordinary_sources_keep_existing_precedence(sources,tmp_path):
    _,data,ready,_,out=sources
    source,choices,_,_=selection(tmp_path)
    report=m.freeze_acquisition_sources(['DY','DE','YYY'],out,data_root=data,
        ready_set_executable=ready,explicit_sources={'DY':source},composition_inputs=choices)
    assert report['explicit_components']==['DY'] and set(report['compositions'])=={'DY'}
    assert {c:r['source_authority'] for c,r in report['sources'].items()}=={
        'DY':'EXPLICIT','DE':'CURATED','YYY':'NATIVE'}


def test_added_unbound_composition_file_during_readback_refuses(tmp_path,monkeypatch):
    from nasolve import cif_reference_composition as compositor
    source,choices,_,out=selection(tmp_path);freeze(source,choices,out)
    original=compositor.compose_dna_source
    def changed(*a,**kw):
        result=original(*a,**kw);(out/'compositions/DY/unbound.cif').write_text('extra');return result
    monkeypatch.setattr(compositor,'compose_dna_source',changed)
    with pytest.raises(ValueError):m.read_acquisition_sources(out)
