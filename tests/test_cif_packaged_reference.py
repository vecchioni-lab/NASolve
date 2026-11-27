"""Packaged chemical sources stay distinct from runtime dictionaries and aliases."""
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
import json
import zipfile

import pytest

ROOT = files('nasolve').joinpath('data/chemical_references')
TEMPLATE = Path(__file__).parent/'fixtures/chemical_reference_DT.cif'


@pytest.mark.parametrize("component", ["5CM", "DP", "DZ"])
def test_installed_ligand_keeps_its_source_history(component):
    ligands = files("nasolve").joinpath("data", "ligands")
    history = json.loads(ligands.joinpath(component + ".provenance.json").read_bytes())
    dictionary = ligands.joinpath(component + ".cif").read_bytes()
    assert history.get("packaged_sha256", history.get("sha256")) == sha256(dictionary).hexdigest()
    assert len(history["source_git_blob"]) == 40


def test_packaged_reference_keeps_exact_source_and_honest_scope():
    from nasolve.cif_packaged_reference import read_packaged_reference
    result=read_packaged_reference('DY')
    assert result['definition']==ROOT.joinpath('DY.cif').read_bytes()
    assert result['metadata']==json.loads(ROOT.joinpath('DY.json').read_text())
    for key,name in [('source','DY.cif'),('manifest','DY.json')]:
        data=ROOT.joinpath(name).read_bytes()
        assert result[key]==dict(anchor='nasolve:data/chemical_references',path=name,sha256=sha256(data).hexdigest(),size=len(data))
    assert result['native_qualification']=='NOT_RUN' and result['automatic_adoption'] is False
    assert '/Users/' not in str(result['source']) and '/private/' not in str(result['manifest'])


def test_packaged_composition_reuses_the_existing_exact_chemistry(tmp_path):
    from nasolve.cif_packaged_reference import compose_packaged_dna_source
    from nasolve.cif_reference_composition import compose_dna_source
    reference=tmp_path/'reference.cif';reference.write_bytes(ROOT.joinpath('DY.cif').read_bytes())
    expected,proof=compose_dna_source(TEMPLATE,'DT',reference,'DY',component='DY')
    data,report=compose_packaged_dna_source(TEMPLATE,'DT','DY',component='DY')
    assert data==expected and report['composition']==proof
    assert report['component']=='DY' and report['source']['sha256']==proof['source_pins']['reference']['sha256']
    assert report['output_sha256']==sha256(data).hexdigest()
    assert report['native_qualification']=='NOT_RUN' and report['automatic_adoption'] is False
    assert '/Users/' not in str(report) and '/private/' not in str(report)


@pytest.mark.parametrize('code',['../DY','dy','DY.cif','Y','YTR','TOOLONG','',None])
def test_reference_lookup_is_exact_and_has_no_implicit_alias(code):
    from nasolve.cif_packaged_reference import read_packaged_reference
    with pytest.raises((ValueError,FileNotFoundError)):read_packaged_reference(code)


def local_package(tmp_path,monkeypatch,code='DY'):
    import nasolve.cif_packaged_reference as module
    root=tmp_path/'package/data/chemical_references';root.mkdir(parents=True)
    metadata=json.loads(ROOT.joinpath('DY.json').read_text())
    data=ROOT.joinpath('DY.cif').read_bytes().replace(b'DY',code.encode())
    metadata['identity']['laboratory_code']=code
    metadata['definition'].update(path=code+'.cif',sha256=sha256(data).hexdigest())
    (root/(code+'.cif')).write_bytes(data);(root/(code+'.json')).write_text(json.dumps(metadata))
    monkeypatch.setattr(module.resources,'files',lambda name:root.parent.parent)
    return root,metadata,module


def test_other_packaged_code_uses_the_same_rule_and_metadata_cannot_activate_it(tmp_path,monkeypatch):
    root,metadata,module=local_package(tmp_path,monkeypatch,'Q17')
    metadata['qualification'].update(mutation_enabled=True,refinement_restraints='CLAIMED_BY_METADATA')
    (root/'Q17.json').write_text(json.dumps(metadata))
    loaded=module.read_packaged_reference('Q17')
    data,report=module.compose_packaged_dna_source(TEMPLATE,'DT','Q17',component='Q18')
    assert loaded['native_qualification']=='NOT_RUN' and loaded['automatic_adoption'] is False
    assert report['component']=='Q18' and report['composition']['source_pins']['reference']['component']=='Q17'
    assert b'Q18' in data and report['native_qualification']=='NOT_RUN'


@pytest.mark.parametrize('defect',['hash','path','anchor','identity','schema','kind','component'])
def test_invalid_package_evidence_refuses_without_search_or_generation(tmp_path,monkeypatch,defect):
    root,metadata,module=local_package(tmp_path,monkeypatch)
    if defect=='hash':metadata['definition']['sha256']='0'*64
    elif defect=='path':metadata['definition']['path']='../DY.cif'
    elif defect=='anchor':metadata['definition']['anchor']='absolute'
    elif defect=='identity':metadata['identity']['laboratory_code']='OTHER'
    elif defect=='schema':metadata['schema_version']=True
    elif defect=='kind':metadata['kind']='runtime numerical dictionary'
    else:
        data=(root/'DY.cif').read_bytes().replace(b'DY',b'ZZZ');(root/'DY.cif').write_bytes(data)
        metadata['definition']['sha256']=sha256(data).hexdigest()
    (root/'DY.json').write_text(json.dumps(metadata))
    before={p:p.read_bytes() for p in root.iterdir()}
    with pytest.raises(ValueError):module.read_packaged_reference('DY')
    assert before=={p:p.read_bytes() for p in root.iterdir()}


def test_zip_resource_composition_returns_no_extraction_path(tmp_path,monkeypatch):
    import nasolve.cif_packaged_reference as module
    expected=module.compose_packaged_dna_source(TEMPLATE,'DT','DY',component='DY')
    archive=tmp_path/'resources.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for name in ['DY.cif','DY.json']:z.writestr('nasolve/data/chemical_references/'+name,ROOT.joinpath(name).read_bytes())
    with zipfile.ZipFile(archive) as z:
        monkeypatch.setattr(module.resources,'files',lambda name:zipfile.Path(z,'nasolve/'))
        actual=module.compose_packaged_dna_source(TEMPLATE,'DT','DY',component='DY')
    assert actual==expected
    assert str(tmp_path) not in str(actual[1])


def test_manifest_changed_during_composition_cannot_publish_a_source(tmp_path,monkeypatch):
    root,metadata,module=local_package(tmp_path,monkeypatch)
    import nasolve.cif_reference_composition as composition
    original=composition.compose_dna_source
    template_bytes=TEMPLATE.read_bytes()
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        metadata['provenance']['date']='changed during composition'
        (root/'DY.json').write_text(json.dumps(metadata))
        return result
    monkeypatch.setattr(composition,'compose_dna_source',changed)
    with pytest.raises(ValueError,match='changed during composition'):
        module.compose_packaged_dna_source(TEMPLATE,'DT','DY',component='DY')
    assert TEMPLATE.read_bytes()==template_bytes
