"""Explicit custom files reuse frozen-source ownership without claiming chemistry."""
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from nasolve import cif_acquisition_sources as m
from nasolve.campaign_records import write_record
from tests.test_cif_acquisition_sources import dictionary, inventory, sources
from tests.test_cif_complete_request import case


def forbidden(*args, **kwargs):
    raise AssertionError('Explicit or cold input must not discover or execute')


@pytest.mark.parametrize('code', ['DY', 'Q17'])
def test_unregistered_explicit_source_relocates_without_lookup(tmp_path, monkeypatch, code):
    import nasolve.curated_ligands as ligands
    source=tmp_path/'custom.cif';source.write_text(dictionary(code))
    monkeypatch.setattr(m,'ligand_source',forbidden)
    monkeypatch.setattr(ligands,'_registered_record',forbidden)
    out=tmp_path/'selection'
    with patch('subprocess.Popen',side_effect=forbidden):
        report=m.freeze_acquisition_sources([code],out,explicit_sources={code:source})
    assert report['policy_id']=='cif-acquisition-explicit-sources-v1'
    assert report['explicit_components']==[code]
    assert report['sources'][code]['source_kind']=='explicit-file'
    assert report['sources'][code]['source_authority']=='EXPLICIT'
    assert report['native_validation']=='NOT_RUN' and report['scientific_qualification']=='NOT_ASSESSED'
    assert report['automatic_adoption'] is False and report['retry_authorized'] is False
    assert report['dictionary_generation']=='NOT_RUN'
    before=inventory(out);source.unlink();moved=out.rename(tmp_path/'relocated')
    with patch('subprocess.Popen',side_effect=forbidden):
        result=m.read_acquisition_sources(moved)
    assert result['report']==report and inventory(moved)==before
    assert result['sources'][code]['source'].read_text()==dictionary(code)


def test_mixed_batch_preserves_ordinary_choices_and_explicit_bytes(sources, monkeypatch):
    _,data,ready,ccd,out=sources
    custom=data/'hand-picked.cif';custom.write_text(dictionary('ZZZ')+'# explicit choice\n')
    select=m.ligand_source;seen=[]
    def ordinary(code,*args,**kwargs):
        assert code!='ZZZ';seen.append(code);return select(code,*args,**kwargs)
    monkeypatch.setattr(m,'ligand_source',ordinary)
    r=m.freeze_acquisition_sources(['ZZZ','YYY','DE'],out,data_root=data,
        ready_set_executable=ready,explicit_sources={'ZZZ':custom})
    assert r['explicit_components']==['ZZZ'] and set(seen)=={'DE','YYY'}
    assert {c:x['source_kind'] for c,x in r['sources'].items()}=={
        'DE':'curated','YYY':'installed-phenix-ccd','ZZZ':'explicit-file'}
    assert (out/'sources/ZZZ.cif').read_bytes()==custom.read_bytes()
    assert (data/'ligands/ZZZ.cif').read_text()==dictionary('ZZZ')


@pytest.mark.parametrize('defect',['empty','list','extra_code','lowercase','curated','none_path',
    'missing','directory','symlink','parent_symlink','wrong_component'])
def test_invalid_explicit_choice_refuses_before_publication(sources, monkeypatch, defect):
    _,data,ready,ccd,out=sources
    source=data/'ligands/ZZZ.cif';choices={'ZZZ':source};codes=['ZZZ']
    if defect=='empty':choices={}
    elif defect=='list':choices=[('ZZZ',source)]
    elif defect=='extra_code':choices['YYY']=ccd
    elif defect=='lowercase':choices={'zzz':source}
    elif defect=='curated':codes=['DE'];choices={'DE':data/'ligands/DE.cif'}
    elif defect=='none_path':choices['ZZZ']=None
    elif defect=='missing':source.unlink()
    elif defect=='directory':choices['ZZZ']=data
    elif defect=='symlink':
        link=data/'link.cif';link.symlink_to(source);choices['ZZZ']=link
    elif defect=='parent_symlink':
        link=data/'link';link.symlink_to(source.parent,target_is_directory=True);choices['ZZZ']=link/source.name
    else:source.write_text(dictionary('XXX'))
    monkeypatch.setattr(m,'ligand_source',forbidden)
    with pytest.raises((ValueError,TypeError,OSError)):
        m.freeze_acquisition_sources(codes,out,explicit_sources=choices)
    assert not out.exists()


@pytest.mark.parametrize('stage',['validation','before_copy','after_copy'])
def test_explicit_source_changes_do_not_publish_completion(tmp_path, monkeypatch, stage):
    source=tmp_path/'custom.cif';source.write_text(dictionary('ZZZ'));out=tmp_path/'selection'
    if stage=='validation':
        validate=m.validate_ligand_dictionary
        def changed(code,path):
            validate(code,path);source.write_text(dictionary('ZZZ')+'# changed\n')
        monkeypatch.setattr(m,'validate_ligand_dictionary',changed)
    else:
        read=m._read;count=0
        def changed(path):
            nonlocal count
            data=read(path)
            if Path(path)==source:
                count+=1
                if count==(2 if stage=='before_copy' else 3):
                    source.write_text(dictionary('ZZZ')+'# changed\n')
            return data
        monkeypatch.setattr(m,'_read',changed)
    with pytest.raises(ValueError):m.freeze_acquisition_sources(['ZZZ'],out,explicit_sources={'ZZZ':source})
    assert not (out/'source_selection.json').exists()
    if stage=='after_copy':
        assert (out/'sources/ZZZ.cif').read_text()==dictionary('ZZZ')
        before=inventory(out)
        with pytest.raises(FileExistsError):m.freeze_acquisition_sources(['ZZZ'],out,explicit_sources={'ZZZ':source})
        assert inventory(out)==before


@pytest.mark.parametrize('defect',['old_policy','unknown_policy','dropped','empty','extra','curated',
    'authority','kind','old_kind','qualification','extra_claim'])
def test_resigned_explicit_claims_must_match_selected_sources(tmp_path, defect):
    source=tmp_path/'source.cif';source.write_text(dictionary('ZZZ'));out=tmp_path/'selection'
    r=m.freeze_acquisition_sources(['ZZZ'],out,explicit_sources={'ZZZ':source})
    if defect=='old_policy':r['policy_id']=m.POLICY_ID
    elif defect=='unknown_policy':r['policy_id']='future'
    elif defect=='dropped':r.pop('explicit_components')
    elif defect=='empty':r['explicit_components']=[]
    elif defect=='extra':r['explicit_components']=['YYY','ZZZ']
    elif defect=='curated':r['explicit_components']=['DE']
    elif defect=='authority':r['sources']['ZZZ']['source_authority']='NATIVE'
    elif defect=='kind':r['sources']['ZZZ']['source_kind']='installed-phenix-ccd'
    elif defect=='old_kind':r['sources']['ZZZ']['source_kind']='local-verified'
    elif defect=='qualification':r['native_validation']='PASS'
    else:r['composition_qualified']=True
    write_record(out/'source_selection.json',r,replace=True)
    with pytest.raises(ValueError):m.read_acquisition_sources(out)


def test_complete_request_accepts_explicit_sources_without_another_owner(case, tmp_path, monkeypatch):
    complete,args,out,_,_,_,calls=case
    selected=m.read_acquisition_sources(args['source_selection'])
    custom=tmp_path/'custom-sources';custom.mkdir()
    choices={}
    for code,item in selected['sources'].items():
        choices[code]=custom/f'{code}.cif';choices[code].write_bytes(item['source'].read_bytes())
    explicit=tmp_path/'explicit';m.freeze_acquisition_sources(list(choices),explicit,explicit_sources=choices)
    args['source_selection']=explicit
    monkeypatch.setattr(m,'ligand_source',forbidden)
    with patch('subprocess.Popen',side_effect=forbidden):
        complete.initialize_dictionary_request(output=out,**args)
    frozen=m.read_acquisition_sources(out/'inputs/sources')['report']
    assert frozen['policy_id']=='cif-acquisition-explicit-sources-v1'
    shutil.rmtree(custom);shutil.rmtree(explicit)
    moved=out.rename(tmp_path/'relocated-request');before=inventory(moved)
    with patch('subprocess.Popen',side_effect=forbidden):
        state=complete.inspect_dictionary_request(moved)
    assert state['availability']=='AVAILABLE' and not state['attempts'] and not calls
    assert m.read_acquisition_sources(moved/'inputs/sources')['report']==frozen
    assert inventory(moved)==before


def test_packaged_composed_source_enters_same_freezer(tmp_path,monkeypatch):
    from nasolve.cif_packaged_reference import compose_packaged_dna_source
    data,proof=compose_packaged_dna_source(Path(__file__).parent/'fixtures/chemical_reference_DT.cif',
        'DT','DY',component='DY')
    source=tmp_path/'composed.cif';source.write_bytes(data)
    monkeypatch.setattr(m,'ligand_source',forbidden)
    out=tmp_path/'selection'
    with patch('subprocess.Popen',side_effect=forbidden):
        r=m.freeze_acquisition_sources(['DY'],out,explicit_sources={'DY':source})
    assert (out/'sources/DY.cif').read_bytes()==data
    assert r['sources']['DY']['artifact']['sha256']==proof['output_sha256']
    assert r['native_validation']=='NOT_RUN'


def test_custom_choice_cannot_mask_a_missing_curated_source(sources):
    _,data,ready,ccd,out=sources
    (data/'ligands/DE.cif').unlink()
    with pytest.raises(FileNotFoundError):
        m.freeze_acquisition_sources(['DE','ZZZ'],out,data_root=data,ready_set_executable=ready,
            explicit_sources={'ZZZ':data/'ligands/ZZZ.cif'})
    assert not out.exists()


def test_explicit_inventory_is_sorted_and_strict_on_readback(tmp_path):
    paths={}
    for code in ['ZZZ','YYY']:
        paths[code]=tmp_path/f'{code}.cif';paths[code].write_text(dictionary(code))
    out=tmp_path/'selection'
    r=m.freeze_acquisition_sources(list(paths),out,explicit_sources=paths)
    assert r['explicit_components']==r['components']==['YYY','ZZZ']
    r['explicit_components'].reverse()
    write_record(out/'source_selection.json',r,replace=True)
    with pytest.raises(ValueError):m.read_acquisition_sources(out)
