"""Candidate discovery is source/library bound, never chemical acceptance."""
from copy import deepcopy
from unittest.mock import patch
import json
import shutil
import pytest
from nasolve import cif_energy_library as m
from nasolve.ligand_profiles import _emit
from nasolve.cif_linear_bond_reference import prepare_linear_bond_candidate, energy_library_linear_reference
from tests.test_cif_energy_library import case, fake_runner
from tests.test_cif_linear_bond_reference import energy_inputs


@pytest.fixture
def captured(tmp_path):
    sdk,consumer,source,library=case(tmp_path)
    root=tmp_path/'capture'
    m.capture_energy_library(sdk,consumer,root,_process_runner=fake_runner(library))
    return sdk,consumer,source,root


@pytest.mark.parametrize('code',['Q17','PDU','ZZ9'])
@pytest.mark.parametrize('target',['1.607','1.364'])
def test_discovery_uses_source_connectivity_and_delivers_existing_explicit_choices(tmp_path,captured,code,target):
    sdk,consumer,_,root=captured
    folder=tmp_path/code;folder.mkdir();source,values,_,_=energy_inputs(folder,code)
    values={k:v for k,v in values.items() if 'cartn' not in k.lower()}
    values['_chem_comp_bond.value_dist'][0]=target;source.write_text(_emit(values))
    original=source.read_bytes();before=m._tree(root)
    with patch('subprocess.Popen',side_effect=AssertionError('No new native execution')):
        plan=m.discover_bond_targets(source,source,code,root,consumer=consumer)
    assert plan['status']=='BOND_TARGET_CANDIDATES' and plan['bond_targets']=={code:[['L','X']]}
    assert len(plan['bonds'])==3
    assert [r['discovery_status'] for r in plan['bonds']].count('UNSUPPORTED_REFERENCE')==2
    assert plan['acceptance_threshold']=='NOT_ASSIGNED' and plan['automatic_adoption'] is False
    assert plan['achieved_geometry']=='NOT_ASSESSED' and plan['new_native_calls']==0
    assert source.read_bytes()==original and m._tree(root)==before
    reference=energy_library_linear_reference(source,source,code,root/'energy-library.cif')
    candidate=tmp_path/(code+'-candidate.cif')
    change=prepare_linear_bond_candidate(source,source,code,reference,candidate,bonds=plan['bond_targets'][code])
    assert len(change['changes'])==1 and change['changes'][0]['reference_equilibrium_angstrom']==1.47


@pytest.mark.parametrize('kind',['matched','nuclear','wrong_types','no_triple'])
def test_no_proposal_is_not_a_chemical_pass(tmp_path,captured,kind):
    _,consumer,source,root=captured
    from nasolve.cif_stereochemistry_audit import _values
    values=_values(source,'Q17')
    if kind=='matched':values['_chem_comp_bond.value_dist'][0]='1.470'
    elif kind=='nuclear':values['_chem_comp_bond.value_dist_nucleus']=['.']*len(values['_chem_comp_bond.atom_id_1'])
    elif kind=='wrong_types':values['_chem_comp_atom.type_energy'][0]='CR6'
    else:values['_chem_comp_bond.value_order']=['SING']*len(values['_chem_comp_bond.atom_id_1'])
    source.write_text(_emit(values));before=source.read_bytes()
    plan=m.discover_bond_targets(source,source,'Q17',root,consumer=consumer)
    assert plan['bond_targets']=={} and plan['status']=='NO_BOND_TARGET_CANDIDATE'
    assert plan['chemical_approval']=='NOT_ASSESSED' and plan['automatic_adoption'] is False
    assert source.read_bytes()==before
    if kind=='nuclear':assert any(r['discovery_status']=='NUCLEAR_TARGET_REQUIRES_QUALIFICATION' for r in plan['bonds'])
    if kind=='matched':assert any(r['discovery_status']=='MATCHES_REFERENCE' for r in plan['bonds'])
    if kind=='no_triple':assert plan['bonds']==[]


@pytest.mark.parametrize('kind',['consumer','library','chemical_graph','malformed_target'])
def test_discovery_does_not_hide_unbound_or_malformed_inputs(tmp_path,captured,kind):
    _,consumer,source,root=captured;dictionary=tmp_path/'dictionary.cif';dictionary.write_bytes(source.read_bytes())
    if kind=='consumer':consumer=deepcopy(consumer);consumer['version']='other'
    elif kind=='library':(root/'energy-library.cif').write_text('data_changed\n')
    elif kind=='chemical_graph':dictionary.write_text(dictionary.read_text().replace('TRIP','DOUB'))
    else:dictionary.write_text(dictionary.read_text().replace('1.607','nan'))
    with pytest.raises(ValueError):m.discover_bond_targets(source,dictionary,'Q17',root,consumer=consumer)


def test_discovery_replays_after_original_inputs_and_sdk_are_gone(tmp_path,captured):
    sdk,consumer,source,root=captured
    before=m.discover_bond_targets(source,source,'Q17',root,consumer=consumer)
    moved=root.rename(tmp_path/'moved');new_source=source.rename(tmp_path/'renamed.cif')
    shutil.rmtree(sdk.root)
    with patch('subprocess.Popen',side_effect=AssertionError('Readback cannot execute')):
        after=m.discover_bond_targets(new_source,new_source,'Q17',moved,consumer=consumer)
    assert before==after
    assert str(tmp_path) not in json.dumps(after)


def test_source_change_during_comparison_refuses(captured,monkeypatch):
    _,consumer,source,root=captured
    from nasolve import cif_linear_bond_reference as reference
    original=reference.compare_linear_bond_reference
    def changed(*args,**kwargs):
        result=original(*args,**kwargs);source.write_text(source.read_text()+'# late change\n');return result
    monkeypatch.setattr(reference,'compare_linear_bond_reference',changed)
    with pytest.raises(ValueError,match='changed'):m.discover_bond_targets(source,source,'Q17',root,consumer=consumer)


def test_unqualified_library_capture_cannot_start_discovery(tmp_path):
    sdk,consumer,source,library=case(tmp_path);root=tmp_path/'failed'
    m.capture_energy_library(sdk,consumer,root,_process_runner=fake_runner(library,'failed'))
    with pytest.raises(ValueError,match='unqualified'):
        m.discover_bond_targets(source,source,'Q17',root,consumer=consumer)


def test_source_size_bound_is_checked_before_parsing(captured,monkeypatch):
    _,consumer,source,root=captured
    monkeypatch.setattr(m,'MAX_SOURCE_BYTES',source.stat().st_size-1)
    with pytest.raises(ValueError,match='source bound'):
        m.discover_bond_targets(source,source,'Q17',root,consumer=consumer)


def test_more_than_64_real_graph_choices_refuses_without_truncation(captured):
    _,consumer,source,root=captured
    from nasolve.cif_stereochemistry_audit import _values
    values=_values(source,'Q17')
    for key,rows in list(values.items()):
        if key.startswith('_chem_comp_'):
            names=key.endswith('.atom_id') or '.atom_id_' in key
            values[key]=[f'S{i}_{name}' if names else name for i in range(65) for name in rows]
    source.write_text(_emit(values));before=source.read_bytes()
    with pytest.raises(ValueError,match='selection bound'):
        m.discover_bond_targets(source,source,'Q17',root,consumer=consumer)
    assert source.read_bytes()==before
