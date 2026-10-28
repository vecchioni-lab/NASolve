"""Full-model recipe uses NAR roles; artificial sources test selector binding only."""
from pathlib import Path
import json
import pytest
from .helpers import make_dataset


def test_input_card_freezes_full_model_scope(tmp_path):
    from nasolve.automr_input import read_intent, resolve_automr_input, format_intent
    from nasolve.automr import _post_mr_plan
    root=make_dataset(tmp_path/'data')
    card=root/'nasolve.txt'
    card.write_text('[automr]\nmode = nonstandard\nrestraint_scope = all\n')
    intent=read_intent(card)
    resolved=resolve_automr_input(root,intent)
    assert resolved.restraint_scope=='all'
    assert _post_mr_plan(resolved)['restraint_scope']=='all'
    card.write_text(format_intent(resolved))
    assert read_intent(card).restraint_scope=='all'


@pytest.mark.parametrize('value',['ALL','pairs','modified',True,3,''])
def test_invalid_scope_rejected(value,tmp_path):
    from nasolve.automr_input import AutoMRIntent, resolve_automr_input, AutoMRInputError
    with pytest.raises(AutoMRInputError,match='restraint_scope'):
        resolve_automr_input(make_dataset(tmp_path/'data'),AutoMRIntent(restraint_scope=value))


def test_dictionary_lookup_does_not_require_a_d_sugar_construction_parent(tmp_path,monkeypatch):
    from restraints import residue_library
    from nasolve.curated_ligands import ligand_source, ligand_definition
    monkeypatch.setattr(residue_library,'load_residue_records',lambda:[{'Ligand code':'0DC','Sugar Type':'L-DNA','Source sheet':'cytosine','Base Analog':'C','N1':'N1'}])
    folder=tmp_path/'ligands';folder.mkdir();(folder/'0DC.cif').write_text('source')
    assert ligand_source('0DC',tmp_path).path==folder/'0DC.cif'
    with pytest.raises(ValueError,match='construction sugar'):
        ligand_definition('0DC')


def fixture(tmp_path):
    from restraints.mirror_pdb import mirror_pdb
    from restraints.builder import pair_residue_from_pdb
    from restraints.residue_library import load_residue_records
    from nasolve.cif_explicit_na_policy import _model
    model=tmp_path/'L.pdb'
    mirror_pdb(Path(__file__).parents[1]/'MR_frames/3GBI/C_C.pdb',model)
    _,_,residues,codes,_,_=_model(model)
    folder=tmp_path/'data/ligands';folder.mkdir(parents=True)
    records=load_residue_records()
    for code in set(codes.values()):
        residue=next(r for s,r in residues.items() if codes[s]==code)
        names=sorted(set(pair_residue_from_pdb(records,residue).atoms.values()))
        text=f'data_{code}\n_chem_comp.id {code}\nloop_\n_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n_chem_comp_atom.type_symbol\n'
        text+=''.join(f'{code} {n} {n[0]}\n' for n in names)
        text+='loop_\n_chem_comp_bond.comp_id\n_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n_chem_comp_bond.value_order\n'
        text+=''.join(f'{code} {a} {b} SING\n' for a,b in zip(names,names[1:]))
        (folder/(code+'.cif')).write_text(text)
    return model,tmp_path/'data'


def test_full_model_l_recipe_uses_all_chains_and_reports_unpaired_sites(tmp_path):
    from nasolve.full_model_restraints import prepare_full_model_restraints
    from nasolve.cif_explicit_na_policy import read_explicit_na_policy
    model,data=fixture(tmp_path);before=model.read_bytes()
    result=prepare_full_model_restraints(model,tmp_path/'policy',data_root=data)
    assert result['mode']=='full-model'
    assert result['include_stacking'] is True
    assert result['mapped_site_count']==42
    assert result['retained_pair_count']==18
    assert result['stack_count']==38
    assert len(result['unpaired_sites'])==6
    assert result['symmetry_pairs']=='NOT_SEARCHED'
    assert result['automatic_adoption'] is False
    assert model.read_bytes()==before
    policy=read_explicit_na_policy(tmp_path/'policy/compiled')
    assert policy['request_counts']=={'angle':76,'bond':46,'parallelity':56}
    assert 'enabled = False' in (tmp_path/'policy/compiled/explicit_na_policy.phil').read_text()
    with pytest.raises(FileExistsError):
        prepare_full_model_restraints(model,tmp_path/'policy',data_root=data)


def test_unsupported_mapped_site_cannot_disappear_silently(tmp_path):
    from nasolve.full_model_restraints import prepare_full_model_restraints
    model,data=fixture(tmp_path)
    model.write_text(model.read_text().replace('0DG','ZZZ'))
    with pytest.raises(ValueError,match='NARestraints'):
        prepare_full_model_restraints(model,tmp_path/'policy',data_root=data)


def test_no_pairs_is_explicitly_blocked(tmp_path,monkeypatch):
    from nasolve.full_model_restraints import prepare_full_model_restraints
    from restraints import guesser
    model,data=fixture(tmp_path)
    monkeypatch.setattr(guesser,'guess_pairs',lambda *a,**kw:([],['nothing']))
    with pytest.raises(ValueError,match='No base pairs'):
        prepare_full_model_restraints(model,tmp_path/'policy',data_root=data)


def test_scope_conflict_stops_before_postmr_directory(tmp_path):
    from nasolve.postmr import prepare_postmr, PostMRPreparationError
    from .helpers import make_postmr_report, model_text
    model=tmp_path/"model.pdb";model.write_text(model_text())
    run=tmp_path/"run";make_postmr_report(run,model)
    with pytest.raises(PostMRPreparationError,match='modified-pairs-only'):
        prepare_postmr(run,Path('/missing'),restraint_scope='all',modified_pairs_only=True)
    assert not (run/'PostMR').exists()


def test_postmr_uses_frozen_all_card_without_frame_resources(tmp_path,monkeypatch):
    from nasolve.postmr import prepare_postmr
    from .helpers import make_postmr_report
    import shutil
    model,data=fixture(tmp_path)
    run=tmp_path/'run';report_path=make_postmr_report(run,model)
    report=json.loads(report_path.read_text())
    report['frame']=None
    report['post_mr_plan']={'sequences':{},'standard_pair':None,'mutations':{},'restraint_scope':'all'}
    report_path.write_text(json.dumps(report))
    def ready(model,exe,out,cifs,env,**kwargs):
        updated=out/'updated.pdb';shutil.copyfile(model,updated)
        log=out/'ready_set.log';log.write_text('fixture; no native execution')
        return updated,log,None,['fixture'],{'removed':[]}
    monkeypatch.setattr('nasolve.postmr._run_readyset',ready)
    result=prepare_postmr(run,Path('/missing'),data_root=data)
    payload=json.loads((run/'PostMR/report.json').read_text())
    nar=payload['narestraints']
    assert nar['mode']=='full-model' and nar['retained_pair_count']==18
    assert nar['scope_source']=='frozen-input-card'
    assert nar['restraint_file']['anchor']=='run'
    assert (run/nar['restraint_file']['relative_path']).is_file()
    assert all('5W6W' not in str(v) for v in payload['restraints'])


def test_defaults_do_not_add_a_scope_field(tmp_path):
    from nasolve.automr_input import AutoMRIntent, resolve_automr_input, format_intent
    from nasolve.automr import _post_mr_plan
    resolved=resolve_automr_input(make_dataset(tmp_path/'data'),AutoMRIntent())
    assert 'restraint_scope' not in format_intent(resolved)
    assert 'restraint_scope' not in _post_mr_plan(resolved)


def test_cli_exposes_explicit_scope():
    from nasolve.cli import build_parser
    assert build_parser().parse_args(['postmr','run','--restraint-scope','all']).restraint_scope=='all'


def test_full_model_policy_replays_after_relocation(tmp_path):
    from nasolve.full_model_restraints import prepare_full_model_restraints
    from nasolve.cif_explicit_na_policy import read_explicit_na_policy
    import shutil
    original=tmp_path/'original';original.mkdir()
    model,data=fixture(original)
    prepare_full_model_restraints(model,original/'policy',data_root=data)
    expected=read_explicit_na_policy(original/'policy/compiled')
    relocated=tmp_path/'relocated';original.rename(relocated)
    assert not original.exists()
    assert read_explicit_na_policy(relocated/'policy/compiled')==expected


def test_ter_boundary_does_not_gain_a_stack(tmp_path):
    from nasolve.full_model_restraints import prepare_full_model_restraints
    model,data=fixture(tmp_path)
    lines=model.read_text().splitlines(keepends=True)
    index=next(i for i,line in enumerate(lines) if line[:6].strip() in {'ATOM','HETATM'} and line[21]=='A' and line[22:26].strip()=='110')
    lines.insert(index,'TER\n');model.write_text(''.join(lines))
    result=prepare_full_model_restraints(model,tmp_path/'policy',data_root=data)
    assert result['stack_count']==37
    compiled=json.loads((tmp_path/'policy/compiled/explicit_na_policy.json').read_text())
    assert ['A:109','A:110'] not in compiled['stacks']


def test_guesser_failure_restores_nar_loader(tmp_path,monkeypatch):
    from nasolve.full_model_restraints import prepare_full_model_restraints
    from restraints import guesser
    model,data=fixture(tmp_path);loader=guesser.load_residue_records
    def failure(*a,**kw):raise ValueError('fixture guess failure')
    monkeypatch.setattr(guesser,'guess_pairs',failure)
    with pytest.raises(ValueError,match='fixture guess failure'):
        prepare_full_model_restraints(model,tmp_path/'policy',data_root=data)
    assert guesser.load_residue_records is loader


@pytest.mark.parametrize('value',[{},[],False,'pairs'])
def test_invalid_frozen_scope_is_not_ignored(tmp_path,value):
    from nasolve.postmr import prepare_postmr,PostMRPreparationError
    from .helpers import make_postmr_report,model_text
    model=tmp_path/'model.pdb';model.write_text(model_text())
    run=tmp_path/'run';path=make_postmr_report(run,model)
    report=json.loads(path.read_text());report['post_mr_plan']['restraint_scope']=value;path.write_text(json.dumps(report))
    with pytest.raises(PostMRPreparationError,match='restraint scope'):
        prepare_postmr(run,Path('/missing'))
    assert not (run/'PostMR').exists()
