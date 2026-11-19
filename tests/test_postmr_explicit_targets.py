"""Explicit chemistry supplies a construction hop, never a fabricated NAR role."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve import postmr
from nasolve.cif_packaged_reference import compose_packaged_dna_source
from nasolve.cif_linked_preparation import component_values, _render
from tests.test_postmr import pdb_record


@pytest.fixture
def inputs(tmp_path):
    source=tmp_path/'source.cif'
    source.write_bytes(compose_packaged_dna_source(Path(__file__).parent/'fixtures/chemical_reference_DT.cif',
        'DT','DY',component='DY')[0])
    model=tmp_path/'model.pdb';model.write_text(pdb_record('ATOM',1,"C1'",'DA','A',1)+'END\n')
    report={'post_mr_plan':{'mutations':{'A:1':{'ligand_code':'DY'}}}}
    return source,model,report


def forbidden(*args,**kwargs):raise AssertionError('Explicit target must not consult registry or execute')


def test_explicit_target_plans_without_registry_and_keeps_identity_separate(inputs,monkeypatch):
    source,model,report=inputs;before=(source.read_bytes(),model.read_bytes(),deepcopy(report))
    monkeypatch.setattr(postmr,'ligand_definition',forbidden)
    with patch('subprocess.Popen',side_effect=forbidden):
        actions=postmr.build_mutation_plan(report,model,construction_sources={'DY':(source,'DT')})
    assert actions==(postmr.MutationAction('A:1','DA','DY','coot-parent-overlap',parent_code='DT'),)
    assert actions[0].deposition_code is None
    assert before==(source.read_bytes(),model.read_bytes(),report)


def test_frozen_source_is_consumed_after_original_disappears(inputs,tmp_path,monkeypatch):
    from nasolve.cif_acquisition_sources import freeze_acquisition_sources,read_acquisition_sources
    source,model,report=inputs
    frozen=tmp_path/'frozen';freeze_acquisition_sources(['DY'],frozen,explicit_sources={'DY':source})
    source.unlink();moved=frozen.rename(tmp_path/'moved')
    monkeypatch.setattr(postmr,'ligand_definition',forbidden)
    selected=read_acquisition_sources(moved)['sources']['DY']['source']
    assert postmr.build_mutation_plan(report,model,construction_sources={'DY':(selected,'DT')})[0].after=='DY'


def test_renamed_source_follows_same_construction_rule(inputs,monkeypatch):
    source,model,report=inputs;source.write_bytes(source.read_bytes().replace(b'DY',b'Q17'))
    report['post_mr_plan']['mutations']['A:1']['ligand_code']='Q17'
    monkeypatch.setattr(postmr,'ligand_definition',forbidden)
    action,=postmr.build_mutation_plan(report,model,construction_sources={'Q17':(source,'DC')})
    assert action.after=='Q17' and action.parent_code=='DC' and action.deposition_code is None


def test_ordinary_plans_and_registry_fallback_remain_unchanged(inputs,monkeypatch):
    source,model,report=inputs
    baseline=postmr.MutationAction('A:1','DA','DY','coot-parent-overlap',parent_code='DT',deposition_code='ABC')
    from types import SimpleNamespace
    monkeypatch.setattr(postmr,'ligand_definition',lambda code:SimpleNamespace(parent_code='DT',deposition_code='ABC'))
    assert postmr.build_mutation_plan(report,model)==(baseline,)
    assert postmr.build_mutation_plan(report,model,construction_sources=None)==(baseline,)


@pytest.mark.parametrize('defect',['empty','nonmapping','unrequested','lowercase','curated','canonical',
    'wrong_component','bad_parent','missing','symlink','partial_tuple','mirror_request',
    'rna_source','missing_stereo','mirror_source','conflicting_stereo','wrong_frame'])
def test_bad_source_or_hop_refuses_before_registry_or_output(inputs,tmp_path,monkeypatch,defect):
    source,model,report=inputs;choices={'DY':(source,'DT')}
    if defect=='empty':choices={}
    elif defect=='nonmapping':choices=[('DY',(source,'DT'))]
    elif defect=='unrequested':choices['Q17']=(source,'DT')
    elif defect=='lowercase':choices={'dy':(source,'DT')}
    elif defect in {'curated','canonical'}:
        code='DF' if defect=='curated' else 'DT';choices={code:(source,'DT')};report['post_mr_plan']['mutations']['A:1']['ligand_code']=code
    elif defect=='wrong_component':source.write_bytes(source.read_bytes().replace(b'DY',b'Q17'))
    elif defect=='bad_parent':choices['DY']=(source,'DG')
    elif defect=='missing':source.unlink()
    elif defect=='symlink':
        alias=tmp_path/'alias.cif';alias.symlink_to(source);choices['DY']=(alias,'DT')
    elif defect=='partial_tuple':choices['DY']=(source,)
    elif defect=='mirror_request':report['inputs']={'mirror':True}
    else:
        values=component_values(source,'DY');key='_chem_comp_atom.pdbx_stereo_config';ids=values['_chem_comp_atom.atom_id']
        if defect=='rna_source':values['_chem_comp.type']=['RNA LINKING']
        elif defect=='missing_stereo':values.pop(key)
        elif defect=='mirror_source':
            for name in ["C1'","C3'","C4'"]:
                i=ids.index(name);values[key][i]={'R':'S','S':'R'}[values[key][i]]
        elif defect=='conflicting_stereo':
            values['_chem_comp_atom.stereo_config']=values[key][:];values['_chem_comp_atom.stereo_config'][ids.index("C1'")]='S'
        elif defect=='wrong_frame':
            for name,column in values.items():
                if name.endswith(('.atom_id','.atom_id_1','.atom_id_2')):values[name]=['NX' if x=='N1' else x for x in column]
        source.write_text(_render(values,'DY'))
    monkeypatch.setattr(postmr,'ligand_definition',forbidden)
    with pytest.raises(postmr.PostMRPreparationError):postmr.build_mutation_plan(report,model,construction_sources=choices)


def test_changed_source_during_planning_refuses(inputs,monkeypatch):
    source,model,report=inputs;original=postmr.residue_name
    def changed(*args,**kwargs):
        value=original(*args,**kwargs);source.write_bytes(source.read_bytes()+b'# changed\n');return value
    monkeypatch.setattr(postmr,'residue_name',changed)
    with pytest.raises(postmr.PostMRPreparationError,match='changed'):
        postmr.build_mutation_plan(report,model,construction_sources={'DY':(source,'DT')})


def test_unchanged_residue_does_not_bypass_source_validation(inputs):
    source,model,report=inputs;model.write_text(pdb_record('ATOM',1,"C1'",'DY','A',1)+'END\n')
    assert postmr.build_mutation_plan(report,model,construction_sources={'DY':(source,'DT')})[0].method=='none'
    source.write_text('data_wrong\n_chem_comp.id XXX\n')
    with pytest.raises(postmr.PostMRPreparationError):
        postmr.build_mutation_plan(report,model,construction_sources={'DY':(source,'DT')})


def test_explicit_and_catalogue_targets_keep_separate_parent_choices(inputs, monkeypatch):
    from types import SimpleNamespace
    source, model, report = inputs
    model.write_text(model.read_text().replace('END\n', '') +
        pdb_record('ATOM', 2, "C1'", 'DG', 'A', 2) + 'END\n')
    report['post_mr_plan']['mutations']['A:2'] = {'ligand_code': 'PDU'}
    looked_up = []
    def catalogue(code):
        looked_up.append(code)
        assert code == 'PDU'
        return SimpleNamespace(parent_code='DT', deposition_code='PDU')
    monkeypatch.setattr(postmr, 'ligand_definition', catalogue)
    actions = postmr.build_mutation_plan(report, model, construction_sources={'DY': (source, 'DC')})
    assert looked_up == ['PDU']
    assert [(a.after, a.parent_code, a.deposition_code) for a in actions] == [
        ('DY', 'DC', None), ('PDU', 'DT', 'PDU')]


def test_no_explicit_source_keeps_unknown_target_error(inputs, monkeypatch):
    source, model, report = inputs
    def missing(code):
        raise KeyError(code)
    monkeypatch.setattr(postmr, 'ligand_definition', missing)
    with pytest.raises(postmr.PostMRPreparationError, match='no usable canonical parent'):
        postmr.build_mutation_plan(report, model)
