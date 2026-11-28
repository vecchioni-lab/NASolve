"""Per-site construction dictionaries cannot leak between same-code residues."""
from pathlib import Path
from unittest.mock import patch
import sys

import pytest

from nasolve import postmr
from nasolve.cif_linked_preparation import component_values, _prune, _render, atom_rows
from tests.test_postmr_conformation import CootDouble


@pytest.fixture
def sources(tmp_path):
    full = tmp_path/'full.cif'
    full.write_bytes((Path(__file__).parent/'fixtures/public_ccd/PDU.cif').read_bytes().replace(b'PDU', b'ZZZ'))
    values = component_values(full, 'ZZZ')
    removed = {'P', 'OP1', 'OP2', 'OP3'}
    for a,b in zip(values['_chem_comp_bond.atom_id_1'], values['_chem_comp_bond.atom_id_2']):
        if a in removed and atom_rows(values)[b]['type_symbol'] in {'H','D'}:removed.add(b)
        if b in removed and atom_rows(values)[a]['type_symbol'] in {'H','D'}:removed.add(a)
    free = tmp_path/'free.cif';free.write_text(_render(_prune(values, removed, outgoing=False), 'ZZZ'))
    actions = tuple(postmr.MutationAction(f'A:{i}', 'DT', 'ZZZ', 'coot-parent-overlap', 'DT') for i in (1,2))
    return full, free, actions


@pytest.mark.parametrize('reversed_order', [False, True])
def test_script_reloads_dictionary_for_every_site_including_default(sources, tmp_path, monkeypatch, reversed_order):
    full, free, actions = sources
    if reversed_order:actions = actions[::-1]
    class Recorder(CootDouble):
        def __init__(self):super().__init__('ZZZ');self.loaded=None;self.built=[]
        def read_cif_dictionary(self, path):self.loaded=Path(path);return 1
        def get_monomer_from_dictionary(self, code, flag):self.built.append(self.loaded);return 1
    fake=Recorder();monkeypatch.setitem(sys.modules, 'coot', fake)
    script=postmr._coot_script(tmp_path/'in.pdb', tmp_path/'out.pdb', actions,
        {'ZZZ':full}, {a.site:tmp_path/(a.site.replace(':','_')+'.pdb') for a in actions},
        site_dictionary_paths={'A:1':free})
    exec(compile(script, '<coot>', 'exec'), {})
    assert fake.built == [free if a.site=='A:1' else full for a in actions]


def test_absent_site_choices_keep_historical_script_exact(sources, tmp_path):
    full, free, actions=sources
    args=(tmp_path/'in', tmp_path/'out', actions, {'ZZZ':full}, {a.site:tmp_path/a.site for a in actions})
    assert postmr._coot_script(*args)==postmr._coot_script(*args,site_dictionary_paths=None)


@pytest.mark.parametrize('defect', ['empty','unknown_site','canonical','curated','wrong_code','missing',
    'symlink','rna','parent','passthrough','nonmapping'])
def test_bad_site_choice_refuses_before_execution_or_output(sources,tmp_path,defect):
    full, free, actions=sources;choices={'A:1':free};extra={}
    if defect=='empty':choices={}
    elif defect=='unknown_site':choices={'A:3':free}
    elif defect=='canonical':actions=(postmr.MutationAction('A:1','DA','DT','coot-mutate-base'),)
    elif defect=='curated':actions=(postmr.MutationAction('A:1','DT','DF','coot-parent-overlap','DT'),)
    elif defect=='wrong_code':free.write_bytes(free.read_bytes().replace(b'ZZZ',b'QQQ'))
    elif defect=='missing':free.unlink()
    elif defect=='symlink':
        alias=tmp_path/'alias.cif';alias.symlink_to(free);choices={'A:1':alias}
    elif defect=='rna':free.write_bytes(free.read_bytes().replace(b'DNA',b'RNA'))
    elif defect=='parent':actions=(postmr.MutationAction('A:1','DA','ZZZ','coot-parent-overlap','DA'),)
    elif defect=='passthrough':extra['passthrough_sites']=('A:1',)
    else:choices=[('A:1',free)]
    model=tmp_path/'model.pdb';model.write_text('END\n');output=tmp_path/'new/model.pdb'
    with patch('nasolve.postmr._run_coot',side_effect=AssertionError('Invalid choice must not execute')):
        with pytest.raises(postmr.PostMRPreparationError):
            postmr.construct_postmr_model(model,actions,{'ZZZ':full},output,
                coot_executable=tmp_path/'coot',site_dictionary_paths=choices,**extra)
    assert not output.parent.exists()


def test_native_wrong_atom_set_and_changed_dictionary_are_rejected(sources,tmp_path):
    from tests.helpers import pdb_record
    full,free,actions=sources
    model=tmp_path/'model.pdb';model.write_text('END\n')
    def wrong(input_model,output_model,*args,**kwargs):
        output_model.write_text(pdb_record('HETATM',1,'P','ZZZ','A',1,element='P')+'END\n')
        return tmp_path/'script',tmp_path/'log'
    with patch('nasolve.postmr._run_coot',side_effect=wrong):
        with pytest.raises(postmr.PostMRPreparationError,match='atom inventory'):
            postmr.construct_postmr_model(model,actions,{'ZZZ':full},tmp_path/'wrong/model.pdb',
                coot_executable=tmp_path/'coot',site_dictionary_paths={'A:1':free})
    assert (tmp_path/'wrong/model_raw.pdb').is_file() and not (tmp_path/'wrong/model.pdb').exists()
    def changed(*args,**kwargs):
        free.write_bytes(free.read_bytes()+b'# changed\n')
        return wrong(*args,**kwargs)
    with patch('nasolve.postmr._run_coot',side_effect=changed):
        with pytest.raises(postmr.PostMRPreparationError,match='changed'):
            postmr.construct_postmr_model(model,actions,{'ZZZ':full},tmp_path/'changed/model.pdb',
                coot_executable=tmp_path/'coot',site_dictionary_paths={'A:1':free})


def test_a_later_site_cannot_rebaseline_an_earlier_changed_dictionary(sources,tmp_path,monkeypatch):
    from nasolve import postmr_conformation
    full,free,actions=sources;real=postmr_conformation.parent_conformation_plan;calls=[]
    def inspect(path,*args):
        result=real(path,*args);calls.append(path)
        if len(calls)==2:free.write_bytes(free.read_bytes()+b'# concurrent edit\n')
        return result
    monkeypatch.setattr(postmr_conformation,'parent_conformation_plan',inspect)
    with pytest.raises(postmr.PostMRPreparationError,match='changed'):
        postmr._construction_site_dictionaries(actions,{'ZZZ':full},{'A:1':free,'A:2':full})


def test_site_dictionary_read_failure_never_builds_a_monomer(sources,tmp_path,monkeypatch):
    full,free,actions=sources
    class Failed(CootDouble):
        def read_cif_dictionary(self,path):return 0 if Path(path)==free else 1
        def get_monomer_from_dictionary(self,*args):raise AssertionError('Cannot build after rejected dictionary')
    monkeypatch.setitem(sys.modules,'coot',Failed('ZZZ'))
    script=postmr._coot_script(tmp_path/'in',tmp_path/'out',actions,{'ZZZ':full},
        {a.site:tmp_path/a.site for a in actions},site_dictionary_paths={'A:1':free})
    with pytest.raises(RuntimeError,match='dictionary for A:1'):exec(compile(script,'<coot>','exec'),{})
