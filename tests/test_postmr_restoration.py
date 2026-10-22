"""Ordinary Coot construction regressions; no installed native tools."""
from math import dist
from pathlib import Path
import shutil

import pytest

from nasolve.postmr import MutationAction, _restore_shared_parent_coordinates
from tests.test_cif_fragment_restoration import fixture, SCAFFOLD


def inputs(tmp_path, *, free_oh=False):
    raw, _, parent, native, expected = fixture(tmp_path)
    raw.write_text('HEADER retained header\n' + raw.read_text().replace(' ZZZ ', '  DP '))
    parent.write_text(parent.read_text().replace('  DC ', '  DG '))
    definition = native['monomer_mappings']['rows'][0]['metadata']['effective_definition']
    dictionary = tmp_path/'source.cif'
    atoms = definition['atoms']
    bonds = definition['bonds']
    dictionary.write_text('data_DP\n_chem_comp.id DP\n_chem_comp.type "DNA LINKING"\n'
        'loop_\n_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n_chem_comp_atom.type_symbol\n'
        + ''.join(f'DP "{a["atom_id"]}" {a["type_symbol"]}\n' for a in atoms)
        + '#\nloop_\n_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n_chem_comp_bond.value_order\n'
        + ''.join(f'"{b["atom_id_1"]}" "{b["atom_id_2"]}" SING\n' for b in bonds) + '#\n')
    if free_oh:
        for model in (raw,parent):
            model.write_text(''.join(l for l in model.read_text().splitlines(keepends=True)
                if not (l.startswith(('ATOM','HETATM')) and l[12:16].strip() in {'P','OP1','OP2'})))
    action = MutationAction('Z:9','DG','DP','coot-parent-overlap',parent_code='DG')
    return raw,parent,dictionary,action,expected


def rows(path):
    return {l[12:16].strip(): l for l in path.read_text().splitlines(keepends=True)
            if l.startswith(('ATOM','HETATM'))}


def xyz(line):
    return tuple(float(line[i:i+8]) for i in (30,38,46))


@pytest.mark.parametrize('free_oh', [False, True])
def test_ordinary_restoration_transports_complete_base_instead_of_copying_shared_names(tmp_path,free_oh):
    raw,parent,dictionary,action,expected = inputs(tmp_path,free_oh=free_oh)
    snapshots = {p:p.read_bytes() for p in (raw,parent,dictionary)}
    output = tmp_path/'restored.pdb'
    receipt = _restore_shared_parent_coordinates(raw,output,(action,),{'Z:9':parent},{'DP':dictionary})['Z:9']
    actual, old, canonical = rows(output), rows(raw), rows(parent)
    for name in ('NX','C2','QZ'):
        assert xyz(actual[name]) == expected[name]
    for name in set(SCAFFOLD)&actual.keys():
        assert xyz(actual[name]) == xyz(canonical[name])
    for name in actual:
        assert actual[name][:30]+actual[name][54:] == old[name][:30]+old[name][54:]
    assert output.read_text().startswith('HEADER retained header\n')
    assert all(p.read_bytes()==before for p,before in snapshots.items())
    assert receipt['status']=='GRAPH_FRAGMENT_RESTORED'
    assert receipt['fragment_atoms']==['C2','NX','QZ']
    assert receipt['rotation_determinant']==pytest.approx(1.)
    assert receipt['max_fragment_distance_change']<=.002
    assert receipt['attachment_orientation_preserved'] is True


@pytest.mark.parametrize('problem', ['bridge','missing_base','duplicate','alias_duplicate','altloc','hydrogen','missing_source','bad_frame','wrong_parent','element','missing_sugar','missing_parent'])
def test_unsupported_or_ambiguous_context_retains_entire_raw_site_without_user_gate(tmp_path,problem):
    raw,parent,dictionary,action,_ = inputs(tmp_path)
    if problem=='bridge':
        dictionary.write_text(dictionary.read_text().replace('#\n', '#\n',1).rstrip('#\n')+'\n"QZ" "C2\'" SING\n#\n')
    elif problem=='missing_base':
        raw.write_text(''.join(l for l in raw.read_text().splitlines(keepends=True) if l[12:16].strip()!='QZ'))
    elif problem in {'duplicate','alias_duplicate','hydrogen'}:
        line=next(l for l in raw.read_text().splitlines(keepends=True) if l[12:16].strip()=='OP1')
        if problem=='alias_duplicate':line=line[:12]+' O1P'+line[16:]
        if problem=='hydrogen':line=line[:12]+' HX '+line[16:76]+' H'+line[78:]
        raw.write_text(raw.read_text()+line)
    elif problem=='altloc':
        raw.write_text(raw.read_text().replace('  NX ', '  NXA'))
    elif problem=='missing_source':dictionary.unlink()
    elif problem=='bad_frame':
        raw.write_text(raw.read_text().replace('   0.000   1.500   0.000','   2.000   0.000   0.000'))
    elif problem=='missing_parent':parent.unlink()
    elif problem=='wrong_parent':parent.write_text(parent.read_text().replace('  DG ','  DT '))
    elif problem=='element':raw.write_text(raw.read_text().replace('           N\n','           C\n'))
    elif problem=='missing_sugar':
        raw.write_text(''.join(l for l in raw.read_text().splitlines(keepends=True) if l[12:16].strip()!="C3'"))
    output=tmp_path/'retained.pdb'
    receipt=_restore_shared_parent_coordinates(raw,output,(action,),{'Z:9':parent},{'DP':dictionary})['Z:9']
    assert output.read_bytes()==raw.read_bytes()
    assert receipt['status']=='RAW_SITE_RETAINED' and receipt['requires_cif_review'] is False
    assert receipt['notes'] and receipt['reason']


def test_phosphate_aliases_and_terminal_oxygen_are_backbone_not_base(tmp_path):
    raw,parent,dictionary,action,_=inputs(tmp_path)
    for model in (raw,parent):
        line=next(l for l in model.read_text().splitlines(keepends=True) if l[12:16].strip()=='OP1')
        terminal=line[:12]+' OP3'+line[16:]
        model.write_text(model.read_text().replace(' OP1',' O1P').replace(' OP2',' O2P')+terminal)
    text=dictionary.read_text().replace('#\nloop_','DP OP3 O\n#\nloop_',1)
    dictionary.write_text(text.rstrip('#\n')+'\nP OP3 SING\n#\n')
    output=tmp_path/'restored.pdb'
    r=_restore_shared_parent_coordinates(raw,output,(action,),{'Z:9':parent},{'DP':dictionary})['Z:9']
    assert r['status']=='GRAPH_FRAGMENT_RESTORED' and 'OP3' in r['scaffold_atoms']
    assert xyz(rows(output)['OP3'])==xyz(rows(parent)['OP3'])


def test_outside_sites_metadata_and_existing_inputs_preserved(tmp_path):
    raw,parent,dictionary,action,_=inputs(tmp_path)
    extra=''.join(l[:22]+'  10'+l[26:] for l in raw.read_text().splitlines(keepends=True) if l.startswith('HETATM'))
    raw.write_text(raw.read_text()+extra+'REMARK untouched tail\n')
    output=tmp_path/'restored.pdb'
    _restore_shared_parent_coordinates(raw,output,(action,),{'Z:9':parent},{'DP':dictionary})
    assert output.read_text().endswith(extra+'REMARK untouched tail\n')


def test_existing_output_is_preserved(tmp_path):
    raw,parent,dictionary,action,_=inputs(tmp_path);out=tmp_path/'output.pdb';out.write_text('KEEP')
    with pytest.raises(FileExistsError):
        _restore_shared_parent_coordinates(raw,out,(action,),{'Z:9':parent},{'DP':dictionary})
    assert out.read_text()=='KEEP'


def test_public_source_partition_uses_graph_and_rejects_bridged_atl():
    from nasolve.postmr_restoration import source_graph_fragment
    public=Path(__file__).parent/'fixtures'/'public_ccd'
    for code in ('PDU','5PC'):
        report=source_graph_fragment(public/f'{code}.cif',code)
        assert report['attachment_atom']=='N1'
        assert report['frame_atoms']==["C1'","O4'","C2'"]
        assert ({'C5A','C5B','C5M'} if code=='PDU' else {'C7','C8','C9'}) <= set(report['fragment_atoms'])
        assert 'OP3' in report['scaffold_atoms']
    with pytest.raises(ValueError,match='classification|attachment|sugar'):
        source_graph_fragment(public/'ATL.cif','ATL')


def test_unmatched_declared_terminal_oxygen_retains_entire_raw_site(tmp_path):
    raw,parent,dictionary,action,_=inputs(tmp_path)
    line=next(l for l in raw.read_text().splitlines(keepends=True) if l[12:16].strip()=='OP1')
    raw.write_text(raw.read_text()+line[:12]+' OP3'+line[16:])
    text=dictionary.read_text().replace('#\nloop_','DP OP3 O\n#\nloop_',1)
    dictionary.write_text(text.rstrip('#\n')+'\nP OP3 SING\n#\n')
    output=tmp_path/'restored.pdb'
    report=_restore_shared_parent_coordinates(raw,output,(action,),{'Z:9':parent},{'DP':dictionary})['Z:9']
    assert report['status']=='RAW_SITE_RETAINED'
    assert output.read_bytes()==raw.read_bytes()
    assert 'Parent lacks' in report['reason']


def test_shared_construction_calls_ordinary_coot_and_graph_restoration(tmp_path,monkeypatch):
    from nasolve.postmr import construct_postmr_model
    raw,parent,dictionary,action,_=inputs(tmp_path)
    captured=[]
    def coot(model,output,actions,executable,coot_dir,environment,dictionaries,parents,**kwargs):
        assert model==parent and actions==(action,) and dictionaries=={'DP':dictionary}
        assert environment=={'FROZEN':'YES'} and kwargs=={'timeout_seconds':600}
        assert coot_dir.is_dir() and output.parent.is_dir()
        shutil.copyfile(raw,output)
        shutil.copyfile(parent,parents['Z:9'])
        log=coot_dir/'coot.log';log.write_text('controlled Coot')
        captured.append(output)
        return coot_dir/'mutate.py',log
    monkeypatch.setattr('nasolve.postmr._run_coot',coot)
    output=tmp_path/'owned'/'models'/'constructed.pdb'
    report=construct_postmr_model(parent,(action,),{'DP':dictionary},output,
        coot_executable=tmp_path/'coot',environment={'FROZEN':'YES'},timeout_seconds=600)
    assert captured==[report['raw_model']]
    assert report['model']==output and report['geometry_model'].is_file()
    assert report['coordinate_restoration']['Z:9']['status']=='GRAPH_FRAGMENT_RESTORED'
    assert xyz(rows(output)['C2'])!=(16.,24.,39.)


def test_ordinary_prepare_postmr_invokes_shared_construction_stage(tmp_path,monkeypatch):
    import nasolve.postmr as postmr
    from tests.test_postmr import postmr_model_text,make_data_root
    from tests.helpers import make_postmr_report,make_ready_set
    source=tmp_path/'source.pdb';source.write_text(postmr_model_text())
    run=tmp_path/'run';make_postmr_report(run,source)
    original=postmr.construct_postmr_model;calls=[]
    def shared(*args,**kwargs):
        calls.append((args,kwargs))
        return original(*args,**kwargs)
    monkeypatch.setattr(postmr,'construct_postmr_model',shared)
    def builder(_model,_pairs,output):output.write_text('geometry_restraints.edits {}\n')
    result=postmr.prepare_postmr(run,make_ready_set(tmp_path),data_root=make_data_root(tmp_path),
                               narestraints_builder=builder)
    assert result.status=='POSTMR_READY' and len(calls)==1
    assert calls[0][0][3].name=='after_coot.pdb'
    assert calls[0][1]['reference_model'].name=='mr_solution.pdb'


def test_shared_construction_noop_preserves_exact_input_and_refuses_overwrite(tmp_path):
    from nasolve.postmr import construct_postmr_model
    source=tmp_path/'input.pdb';source.write_bytes(b'HEADER exact bytes\r\nEND\r\n')
    output=tmp_path/'owned'/'copy.pdb'
    report=construct_postmr_model(source,(),{},output)
    assert output.read_bytes()==source.read_bytes() and report['raw_model'] is None
    with pytest.raises(FileExistsError):construct_postmr_model(source,(),{},output)


def test_shared_external_coot_timeout_is_explicit_and_records_output(tmp_path,monkeypatch):
    import subprocess
    from nasolve.postmr import _run_coot,PostMRPreparationError
    model=tmp_path/'input.pdb';model.write_text('END\n');directory=tmp_path/'coot';directory.mkdir()
    def timeout(command,**kwargs):
        assert kwargs['timeout']==600 and kwargs['cwd']==directory
        raise subprocess.TimeoutExpired(command,600,output=b'partial native output')
    monkeypatch.setattr('nasolve.postmr.subprocess.run',timeout)
    with pytest.raises(PostMRPreparationError,match='exceeded 600 seconds'):
        _run_coot(model,tmp_path/'output.pdb',(),tmp_path/'coot-bin',directory,None,{}, {},timeout_seconds=600)
    assert 'partial native output' in (directory/'coot.log').read_text()
    assert 'timed out' in (directory/'coot.log').read_text()


@pytest.mark.parametrize('seconds',[0,-1,float('nan'),True])
def test_invalid_coot_time_budget_is_rejected_before_creating_files(tmp_path,seconds):
    from nasolve.postmr import _run_coot,PostMRPreparationError
    with pytest.raises(PostMRPreparationError,match='finite and positive'):
        _run_coot(tmp_path/'input',tmp_path/'output',(),tmp_path/'coot',tmp_path/'missing',None,{}, {},timeout_seconds=seconds)
    assert not (tmp_path/'missing').exists()
