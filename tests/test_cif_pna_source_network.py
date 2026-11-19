"""A source graph package is chemical input, never a numerical dictionary."""
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from .test_cif_pna_operations import case, edit_manifest, edit_context
from .test_cif_catalogue import snapshot


def api():
    from nasolve.cif_pna_source_network import prepare_pna_source_network, read_pna_source_network
    return prepare_pna_source_network, read_pna_source_network


def make(root, **kwargs):
    inputs = root/'inputs'; inputs.mkdir()
    manifest, names = case(inputs, **kwargs)
    return manifest, names, root/'network'


@pytest.mark.parametrize('renamed,isotope,count', [(False,'H',2),(True,'H',2),(False,'D',2),(False,'H',3)])
def test_materialized_graph_keeps_exact_source_state_and_site_identity(tmp_path, renamed, isotope, count):
    prepare, read = api()
    manifest, names, output = make(tmp_path, renamed=renamed, isotope=isotope, count=count)
    before = snapshot(manifest.parent)
    with patch('subprocess.Popen', side_effect=AssertionError('no native execution')):
        receipt = prepare(manifest, output)
        assert read(output) == receipt
    graph = json.loads((output/'source-network.json').read_text())
    atoms = {(a['site'], a['atom_id']): a for a in graph['atoms']}
    assert len(atoms) == len(graph['atoms'])
    assert ('A:1', names['0N']) in atoms and ('A:2', names['0N']) in atoms
    assert ('A:1', names['0OH']) not in atoms
    assert ('A:2', names['0H0']) not in atoms
    assert atoms[(f'A:{count}',names['0H1'])]['element'] == isotope
    assert all(atoms[(f'A:{i+1}',names['0F'])]['source_stereo_declaration']=='R' for i in range(count))
    links = [b for b in graph['bonds'] if b['authority']=='EXPLICIT_AMIDE_OPERATION']
    assert len(links)==count-1
    assert links[0]['atoms']==[['A:1',names['0A']],['A:2',names['0N']]]
    assert all(b['order']=='SINGLE' for b in links)
    assert graph['total_formal_charge']==0
    assert graph['coordinates']=='NOT_ASSIGNED' and graph['numerical_restraints']=='NOT_ASSIGNED'
    assert graph['final_stereochemistry']=='NOT_ASSIGNED'
    assert receipt['status']=='PREPARED_REVIEW' and not receipt['automatic_adoption']
    assert snapshot(manifest.parent)==before
    assert str(tmp_path) not in (output/'preparation-receipt.json').read_text()


@pytest.mark.parametrize('mode', ['charged_reaction','missing_operation','nonreciprocal','mismatched_candidate','furanose'])
def test_no_output_for_unqualified_network(tmp_path, mode):
    prepare, _ = api()
    if mode=='furanose':
        from .test_cif_attachment_links import case as dna_case
        inputs=tmp_path/'inputs';inputs.mkdir();manifest=dna_case(inputs);output=tmp_path/'network'
    else:
        manifest, _, output=make(tmp_path, charge=1 if mode=='charged_reaction' else 0)
        if mode=='missing_operation':
            edit_context(manifest,1,lambda d:[d['ports']['amine'].pop(k) for k in ['operation','leaving_atom']])
        if mode=='nonreciprocal': edit_context(manifest,1,lambda d:d['ports'].update(amine={'state':'source'}))
        if mode=='mismatched_candidate':
            from .test_cif_attachment_links import record
            p=manifest.parent/'candidate-1.cif';p.write_text(p.read_text().replace(' R',' S'))
            edit_manifest(manifest,lambda d:d['sites'][1].update(candidate=record(p,manifest.parent)))
    with pytest.raises(ValueError): prepare(manifest,output)
    assert not output.exists()


def test_existing_output_and_source_tree_are_never_modified(tmp_path):
    prepare, _ = api(); manifest, _, output=make(tmp_path)
    output.mkdir(); (output/'keep').write_text('owned by someone else')
    before=snapshot(tmp_path)
    with pytest.raises(FileExistsError): prepare(manifest,output)
    with pytest.raises(ValueError): prepare(manifest,manifest.parent/'nested')
    assert snapshot(tmp_path)==before


def test_symlink_output_is_rejected(tmp_path):
    prepare, _ = api(); manifest, _, output=make(tmp_path)
    target=tmp_path/'target';target.mkdir();output.symlink_to(target,target_is_directory=True)
    with pytest.raises((ValueError,FileExistsError)):prepare(manifest,output)
    assert not list(target.iterdir())


@pytest.mark.parametrize('mode', ['graph','forged_graph','forged_report','receipt','bool_schema','extra','missing','input','symlink','nested_symlink'])
def test_saved_pass_never_authorizes_changed_package(tmp_path,mode):
    prepare, read=api(); manifest, _, output=make(tmp_path); prepare(manifest,output)
    receipt_path=output/'preparation-receipt.json';receipt=json.loads(receipt_path.read_text())
    if mode in {'graph','forged_graph'}:
        p=output/'source-network.json';v=json.loads(p.read_text());v['atoms'][0]['formal_charge']=1;p.write_text(json.dumps(v))
    if mode=='forged_report':
        p=output/'link-report.json';v=json.loads(p.read_text());v['automatic_adoption']=True;p.write_text(json.dumps(v))
    if mode in {'forged_graph','forged_report'}:
        receipt['files'][p.name].update(sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
    if mode=='receipt':receipt['automatic_adoption']=True
    if mode=='bool_schema':receipt['schema_version']=True
    if mode=='extra':(output/'unexpected.txt').write_text('extra')
    if mode=='missing':(output/'source-network.json').unlink()
    if mode=='input':(output/'inputs/source.cif').write_text('different')
    if mode=='symlink':
        p=output/'source-network.json';p.rename(tmp_path/'outside.json');p.symlink_to(tmp_path/'outside.json')
    if mode=='nested_symlink':
        p=output/'inputs';p.rename(tmp_path/'outside');p.symlink_to(tmp_path/'outside',target_is_directory=True)
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):read(output)


def test_no_candidates_required_and_relocation_needs_only_declared_inputs(tmp_path):
    prepare,read=api();manifest,_,output=make(tmp_path)
    edit_manifest(manifest,lambda d:[s.pop('candidate') for s in d['sites']])
    receipt=prepare(manifest,output)
    moved=tmp_path/'moved';output.rename(moved)
    import shutil
    shutil.rmtree(manifest.parent)
    before=snapshot(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('cold read')):
        assert read(moved)==receipt
    assert snapshot(moved)==before and not output.exists()


def test_partial_write_is_preserved_and_cannot_be_retried_in_place(tmp_path):
    prepare,read=api();manifest,_,output=make(tmp_path)
    from nasolve.cif_attachment_links import inspect_attachment_links
    calls=[]
    def interrupted(path):
        calls.append(path)
        if len(calls)==2:raise RuntimeError('simulated interruption after copying')
        return inspect_attachment_links(path)
    with patch('nasolve.cif_pna_source_network.inspect_attachment_links',side_effect=interrupted):
        with pytest.raises(RuntimeError):prepare(manifest,output)
    before=snapshot(output)
    assert before and not (output/'preparation-receipt.json').exists()
    with pytest.raises(ValueError):read(output)
    with pytest.raises(FileExistsError):prepare(manifest,output)
    assert snapshot(output)==before
    assert prepare(manifest,tmp_path/'fresh')['status']=='PREPARED_REVIEW'


def test_input_change_during_copy_cannot_publish_a_receipt(tmp_path):
    prepare,_=api();manifest,_,output=make(tmp_path)
    from nasolve.cif_attachment_links import inspect_attachment_links
    def mutated(path):
        result=inspect_attachment_links(path)
        if Path(path).parent.name=='inputs' and Path(path)!=manifest:
            source=manifest.parent/'source.cif';source.write_bytes(source.read_bytes()+b'\n# concurrent change\n')
        return result
    with patch('nasolve.cif_pna_source_network.inspect_attachment_links',side_effect=mutated):
        with pytest.raises(ValueError,match='changed'):prepare(manifest,output)
    assert output.exists() and not (output/'preparation-receipt.json').exists()


def test_disconnected_declared_dimers_require_separate_packages(tmp_path):
    prepare,_=api()
    from .test_cif_attachment_links import record
    inputs=tmp_path/'inputs';inputs.mkdir()
    entries=[];models=[];book=None
    for offset in (0,2):
        folder=inputs/str(offset);folder.mkdir();manifest,_=case(folder)
        data=json.loads(manifest.read_text());book=folder/data['workbook']['path']
        for i,entry in enumerate(data['sites']):
            context=folder/entry['context']['path'];c=json.loads(context.read_text())
            c['site']=f'A:{i+1+offset}'
            for port in c['ports'].values():
                if port['state']=='linked':port['partner']['site']='A:'+str(int(port['partner']['site'][2:])+offset)
            context.write_text(json.dumps(c))
            entries.append({'component':entry['component'],**{k:record(folder/entry[k]['path'],inputs)
                for k in ('source','candidate','context')}})
        for line in (folder/data['model']['path']).read_text().splitlines(True):
            if line.startswith('HETATM'):
                models.append(line[:22]+f'{int(line[22:26])+offset:4d}'+line[26:])
    model=inputs/'model.pdb';model.write_text(''.join(models)+'END\n')
    manifest=inputs/'links.json';manifest.write_text(json.dumps({'schema_version':1,
        'model':record(model,inputs),'workbook':record(book,inputs),'sites':entries}))
    with pytest.raises(ValueError,match='one connected'):prepare(manifest,tmp_path/'network')
    assert not (tmp_path/'network').exists()
