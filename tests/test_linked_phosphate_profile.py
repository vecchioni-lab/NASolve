"""Synthetic, offline regressions for the user-opt-in OP3 contract."""
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from Bio.PDB.MMCIF2Dict import MMCIF2Dict

from nasolve.automr_input import AutoMRInputError, read_intent, resolve_automr_input, format_intent
from nasolve.autorefine import AutoRefineError, validate_refined_model, execute_autorefine
from nasolve.checkpoints import CheckpointError, _initial_restraints, initialize_registry, add_checkpoint, inherited_paths
from nasolve.coot_view import _postmr_dictionaries, _checkpoint_dictionaries, CootViewError
from nasolve.ligand_profiles import (
    MOD_CIF, _blocks, combine_dictionary_inputs, effective_restraints,
    frozen_reference, validate_model_phosphate_policy, write_linked_profile,
)
from nasolve.phosphate import PhosphateError, sanitize_phosphates, audit_phosphates
from nasolve.postmr import PostMRPreparationError, prepare_postmr
from nasolve.run_context import resolve_artifact_path
from .test_phosphate import phosphate, without_extra, atom
from .helpers import make_dataset, make_postmr_report
from .test_autorefine import make_refine_run, make_refine, make_mtz_dump

ROOT = Path(__file__).parents[1]
LIBRARY = ROOT / 'src/nasolve/data/ligands/1AP.cif'


def model(tmp_path, *, terminal=False, extra=True, alias=False, insertion=' '):
    records = phosphate(terminal=terminal, alias=alias, insertion=insertion)
    path = tmp_path / 'model.pdb'
    path.write_text(''.join(records if extra else without_extra(records)))
    return path


def report_for(profile=None, allowed=()):
    return {'post_mr_plan': {'allow_op3_sites': list(allowed)},
            'postmr': {'linked_phosphate_profile': profile,
                       'phosphate_policy': {'mode': 'op3-explicit-opt-in-v1', 'allow_op3_sites': list(allowed)}}}


@pytest.mark.parametrize('alias', [False, True])
def test_internal_cleanup_does_not_change_any_other_atom(tmp_path, alias):
    source = model(tmp_path, alias=alias)
    raw = source.read_bytes()
    target = tmp_path / 'clean.pdb'
    result = sanitize_phosphates(source, target)
    assert result['removed'][0]['site'] == 'A:12'
    assert source.read_bytes() == raw
    assert target.read_text() == ''.join(without_extra(source.read_text().splitlines(keepends=True)))
    assert result['allow_op3_sites'] == []


@pytest.mark.parametrize('alias', [False, True])
def test_unrequested_terminal_is_rejected_not_blindly_deoxygenated(tmp_path, alias):
    source = model(tmp_path, terminal=True, alias=alias)
    raw = source.read_bytes()
    with pytest.raises(PhosphateError, match='unrequested terminal'):
        sanitize_phosphates(source, tmp_path / 'clean.pdb')
    assert source.read_bytes() == raw
    assert not (tmp_path / 'clean.pdb').exists()


@pytest.mark.parametrize('alias', [False, True])
def test_terminal_retention_requires_consent_and_preserves_bytes(tmp_path, alias):
    source = model(tmp_path, terminal=True, alias=alias)
    out = tmp_path / 'clean.pdb'
    audit = sanitize_phosphates(source, out, allow_op3_sites=('A:12',))
    assert audit['retained'][0]['reason'] == 'explicitly-requested-unlinked-phosphate'
    assert out.read_bytes() == source.read_bytes()


@pytest.mark.parametrize('sites,terminal,extra,match', [
    (('A:12',), False, True, 'conflicts'),
    (('A:12',), True, False, 'absent'),
    (('Z:999',), False, True, 'absent'),
    (('A:12', 'A:12'), True, True, 'Duplicate'),
    (True, True, True, 'list'),
    (('all',), True, True, 'Invalid'),
])
def test_consent_is_not_a_geometry_override(tmp_path, sites, terminal, extra, match):
    source = model(tmp_path, terminal=terminal, extra=extra)
    with pytest.raises(PhosphateError, match=match):
        sanitize_phosphates(source, tmp_path / 'clean.pdb', allow_op3_sites=sites)
    assert not (tmp_path / 'clean.pdb').exists()


def test_mixed_same_code_internal_and_requested_terminal_get_distinct_profiles(tmp_path):
    internal = without_extra(phosphate(insertion='B'))
    terminal = phosphate(chain='B', number=1, start=21, shift=20, terminal=True)
    source = tmp_path / 'mixed.pdb'
    source.write_text(''.join([*internal, 'TER\n', *terminal, 'END\n']))
    profile, paths = write_linked_profile(source, tmp_path, allow_op3_sites=('B:1',))
    assert profile['inventory'] == {'A:12B': '1AP', 'B:1': '1AP'}
    assert len(profile['modifications']) == 1
    mod = profile['modifications'][0]
    assert mod['site'] == 'A:12B'
    assert mod['incoming_site'] == 'A:11'
    assert mod['outgoing_site'] == 'A:13'
    assert paths[0].read_text() == MOD_CIF
    phil = paths[1].read_text()
    assert 'refinement.pdb_interpretation.apply_cif_modification' in phil
    assert "chain 'A' and resid 12B and resname 1AP" in phil
    assert "chain 'B'" not in phil
    validate_model_phosphate_policy(source, report_for(profile, ('B:1',)))


@pytest.mark.parametrize('kind', ['incoming', 'outgoing', 'identity', 'op3', 'consent'])
def test_frozen_profile_rejects_changed_models_and_consent(tmp_path, kind):
    source = model(tmp_path, extra=False)
    profile, _ = write_linked_profile(source, tmp_path)
    report = report_for(profile)
    text = source.read_text()
    if kind == 'incoming':
        text = text.replace(phosphate()[0], atom(1, "O3'", 'DT', 'A', 11, (-5, 0, 0), record='ATOM'))
    elif kind == 'outgoing':
        text = text.replace(phosphate()[-1], atom(13, 'P', 'DC', 'A', 13, (15, 0, 0), record='ATOM'))
    elif kind == 'identity':
        text = text.replace('1AP', ' DA')
    elif kind == 'op3':
        text += next(line for line in phosphate() if line[12:16].strip() == 'OP3')
    else:
        report['postmr']['phosphate_policy']['allow_op3_sites'] = ['A:12']
    source.write_text(text)
    with pytest.raises(PhosphateError):
        validate_model_phosphate_policy(source, report)
    with pytest.raises(AutoRefineError, match='phosphate'):
        validate_refined_model(source, report)


def test_no_profile_for_an_unrequested_incomplete_unlinked_phosphate(tmp_path):
    source = model(tmp_path, terminal=True, extra=False)
    with pytest.raises(PhosphateError, match='terminal dictionary profile'):
        write_linked_profile(source, tmp_path)
    assert not (tmp_path / 'linked_phosphate.phil').exists()


def test_unknown_orphan_op3_is_not_an_implicit_exception(tmp_path):
    source = tmp_path / 'orphan.pdb'
    source.write_text(atom(1, 'OP3', 'XYZ', 'Z', 99, (0, 0, 0)))
    with pytest.raises(PhosphateError, match='identifiable nucleotide'):
        audit_phosphates(source)


@pytest.mark.parametrize('value', ['true', '*', 'A:1 or all', 'A:1,', 'A:1,A:1', 'A:01'])
def test_nasolve_txt_rejects_ambiguous_or_unscoped_consent(tmp_path, value):
    cfg = tmp_path / 'nasolve.txt'
    cfg.write_text('[automr]\nallow_op3_sites = ' + value + '\n')
    with pytest.raises(AutoMRInputError):
        read_intent(cfg)


def test_op3_request_roundtrips_in_effective_input_and_postmr_plan(tmp_path):
    from nasolve.automr import _post_mr_plan
    dataset = make_dataset(tmp_path / 'data')
    cfg = dataset / 'nasolve.txt'
    cfg.write_text('[automr]\nallow_op3_sites = A:1, B:-3A\n')
    resolved = resolve_automr_input(dataset, read_intent(cfg))
    assert resolved.allow_op3_sites == ('A:1', 'B:-3A')
    cfg.write_text(format_intent(resolved))
    assert read_intent(cfg).allow_op3_sites == resolved.allow_op3_sites
    assert _post_mr_plan(resolved)['allow_op3_sites'] == ['A:1', 'B:-3A']


def test_combine_list_blocks_preserves_both_components(tmp_path):
    output = tmp_path / 'combined.cif'
    combine_dictionary_inputs([LIBRARY, ROOT / 'src/nasolve/data/ligands/DE.cif'], output)
    blocks = _blocks(output)
    assert [b.values['data_'] for b in blocks] == ['comp_list', 'comp_1AP', 'comp_DE']
    assert blocks[0].values['_chem_comp.id'] == ['1AP', 'DE']
    assert blocks[1].values['_chem_comp_bond.value_dist'] == MMCIF2Dict(str(LIBRARY))['_chem_comp_bond.value_dist']
    assert blocks[2].values['_chem_comp_bond.value_dist'] == MMCIF2Dict(str(ROOT / 'src/nasolve/data/ligands/DE.cif'))['_chem_comp_bond.value_dist']


def test_readyset_cannot_replace_1ap_or_swallow_modification(tmp_path):
    reviewed = tmp_path / '1AP.cif'
    shutil.copyfile(LIBRARY, reviewed)
    wrong = tmp_path / 'generated.cif'
    wrong.write_text(LIBRARY.read_text().replace('1.458', '9.999') + '\ndata_addition\n_chem_comp_atom.comp_id NEW\n')
    source = model(tmp_path, extra=False)
    _, modifications = write_linked_profile(source, tmp_path)
    selected, view = effective_restraints([reviewed, *modifications], wrong, tmp_path)
    assert reviewed in selected and all(p in selected for p in modifications)
    supplement = tmp_path / 'readyset_supplement.cif'
    assert '1AP' not in supplement.read_text()
    assert 'NEW' in supplement.read_text()
    assert view == [supplement, reviewed]
    assert '9.999' in wrong.read_text()  # raw evidence is not modified


def test_selected_cif_inputs_and_modification_survive_relocation_and_tamper_is_fatal(tmp_path):
    run = tmp_path / 'dataset/AutoMR/run_001'
    run.mkdir(parents=True)
    source = model(run, extra=False)
    _, mods = write_linked_profile(source, run)
    cif = run / '1AP.cif'
    shutil.copyfile(LIBRARY, cif)
    refs = [frozen_reference(p, run) for p in [cif, *mods]]
    postmr = {'refinement_restraints': refs, 'view_dictionaries': [refs[0]],
              'readyset': {'generated_ligand_cif': '/absent/legacy.cif'}}
    moved = tmp_path / 'moved/AutoMR/run_001'
    shutil.copytree(run, moved)
    shutil.rmtree(tmp_path / 'dataset')
    restored = _initial_restraints(postmr, moved)
    assert {p.name for p in restored} == {'1AP.cif', 'linked_phosphate.cif', 'linked_phosphate.phil'}
    assert _postmr_dictionaries(moved, {'postmr': postmr}) == (moved / '1AP.cif',)
    assert _checkpoint_dictionaries(moved, {'restraints': refs}, 2) == (moved / '1AP.cif',)
    (moved / 'linked_phosphate.cif').write_text('corrupted\n')
    with pytest.raises(CheckpointError):
        _initial_restraints(postmr, moved)


@pytest.mark.parametrize('bad', [[], None, ['old/path.cif'], [{'anchor': 'run', 'relative_path': 'missing.cif'}]])
def test_explicit_restraint_manifest_never_falls_back_when_malformed(tmp_path, bad):
    with pytest.raises(CheckpointError):
        _initial_restraints({'refinement_restraints': bad, 'restraints': []}, tmp_path)


def test_postmr_wires_profiles_and_never_promotes_unrequested_terminal(tmp_path):
    original = model(tmp_path, extra=True)
    run = tmp_path / 'dataset/AutoMR/run_001'
    path = make_postmr_report(run, original)
    report = json.loads(path.read_text())
    report['frame'] = None
    report['post_mr_plan'] = {'sequences': {}, 'standard_pair': None, 'mutations': {}}
    path.write_text(json.dumps(report))
    def readyset(command, cwd, **kwargs):
        prepared = Path(command[1])
        (cwd / 'prepared_model.updated.pdb').write_text(prepared.read_text())
        # Pretend ReadySet rewrote 1AP numerical values. They must be excluded.
        (cwd / 'prepared_model.ligands.cif').write_text(LIBRARY.read_text().replace('1.458', '8.888'))
        return SimpleNamespace(returncode=0, stdout='mocked external executable')
    def no_pairs(prepared, compatibility, pair_file, output):
        pair_file.write_text('')
        return {'retained_pair_count': 0, 'retained_pairs': [], 'modified_sites': ['A:12']}
    with patch('nasolve.postmr.subprocess.run', side_effect=readyset):
        result = prepare_postmr(run, tmp_path / 'ready_set', modified_pairs_only=True, modified_pair_builder=no_pairs)
    prepared_report = json.loads(result.report_path.read_text())
    assert prepared_report['phosphate_policy']['allow_op3_sites'] == []
    selected = _initial_restraints(prepared_report, run)
    assert {'1AP.cif', 'linked_phosphate.cif', 'linked_phosphate.phil'} == {p.name for p in selected}
    assert '8.888' not in '\n'.join(p.read_text() for p in selected)
    assert len(prepared_report['linked_phosphate_profile']['modifications']) == 1
    assert original.read_text().count(' OP3 ') == 1
    assert ' OP3 ' not in result.model_path.read_text()


def test_manual_import_rejects_unrequested_op3_before_copy(tmp_path):
    run = make_refine_run(tmp_path)
    source = model(tmp_path, terminal=True)
    with pytest.raises(CheckpointError, match='Manual model phosphate'):
        add_checkpoint(run, name='bad import', model=source)
    assert not (run / 'AutoRefine/Checkpoints').exists()


def profiled_refine_run(tmp_path):
    run = make_refine_run(tmp_path, autosol=False)
    directory = run / 'PostMR/Restraints'
    path = run / 'report.json'
    report = json.loads(path.read_text())
    source = Path(report['postmr']['prepared_model'])
    source.write_text(''.join(without_extra(phosphate())))
    profile, mods = write_linked_profile(source, directory)
    dictionary = directory / '1AP.cif'
    shutil.copyfile(LIBRARY, dictionary)
    restraints = [directory / 'narestraints.phil', dictionary, *mods]
    report['post_mr_plan'] = {'allow_op3_sites': []}
    report['postmr'].update(report_for(profile)['postmr'])
    report['postmr']['mutation_actions'] = [{'site': 'A:12', 'after': '1AP'}]
    report['postmr']['anomalous']['candidates'] = []
    report['postmr']['refinement_restraints'] = [frozen_reference(p, run) for p in restraints]
    report['postmr']['view_dictionaries'] = [frozen_reference(dictionary, run)]
    path.write_text(json.dumps(report))
    return run


def test_autorefine_doctor_and_manual_children_inherit_after_relocation(tmp_path):
    from nasolve.checkpoints import select_checkpoint, resolve_checkpoint
    from nasolve.refine_doctor import execute_refine_doctor
    run = profiled_refine_run(tmp_path)
    dump = make_mtz_dump(tmp_path)
    first = execute_autorefine(run, make_refine(tmp_path, final_work=.162, final_free=.155), dump,
                              phenix_version='2.2.1-6174')
    assert first.status == 'AUTOREFINE_REVIEW'
    select_checkpoint(run, first.checkpoint_id)
    # Operational references must work after the original dataset has gone.
    moved_dataset = tmp_path / 'elsewhere/dataset'
    shutil.copytree(tmp_path / 'dataset', moved_dataset)
    shutil.rmtree(tmp_path / 'dataset')
    moved_run = moved_dataset / 'AutoMR/run_001'
    doctor = execute_refine_doctor(moved_run, make_refine(tmp_path), dump, phenix_version='2.2.1-6174')
    assert doctor.status == 'REFINE_DOCTOR_RECOMMEND'
    assert doctor.current_checkpoint_preserved
    assert len(doctor.trials) == 1
    _, registry = initialize_registry(moved_run)
    parent = resolve_checkpoint(registry, doctor.recommended_checkpoint)
    paths = inherited_paths(parent, moved_run)
    names = {p.name for p in paths['restraints']}
    assert {'1AP.cif', 'linked_phosphate.cif', 'linked_phosphate.phil', 'narestraints.phil'} == names
    trial = json.loads(doctor.trials[0].report_path.read_text())
    assert {Path(p).name for p in trial['inputs']['restraints']} == names
    assert 'prepared_model.ligands.cif' not in '\n'.join(trial['command'])
    model = paths['model']
    manual = add_checkpoint(moved_run, name='checked manual', model=model, parent=parent['id'])
    _, registry = initialize_registry(moved_run)
    child = resolve_checkpoint(registry, manual.checkpoint_id)
    assert child['restraints'] == parent['restraints']
    assert child['observations'] == parent['observations']
    assert registry['current'] == first.checkpoint_id
    assert _checkpoint_dictionaries(moved_run, child, 2) == (moved_run / 'PostMR/Restraints/1AP.cif',)
    (moved_run / 'PostMR/Restraints/linked_phosphate.phil').write_text('tampered')
    with pytest.raises(CheckpointError, match='changed'):
        inherited_paths(child, moved_run)


def test_refinement_output_with_reintroduced_op3_is_failed_not_selected(tmp_path):
    run = profiled_refine_run(tmp_path)
    executable = make_refine(tmp_path)
    extra = next(line for line in phosphate() if line[12:16].strip() == 'OP3')
    executable.write_text(executable.read_text() + f"\nwith Path('refined_001.pdb').open('a') as out: out.write({extra!r})\n")
    result = execute_autorefine(run, executable, make_mtz_dump(tmp_path), phenix_version='2.2.1-6174')
    assert result.status == 'AUTOREFINE_FAILED'
    assert not result.selected_as_current
    _, registry = initialize_registry(run)
    assert registry['current'] == 'postmr'
    assert registry['checkpoints'][-1]['usable'] is False


def test_cif_multiline_text_cannot_create_fake_data_block(tmp_path):
    path = tmp_path / 'multiline.cif'
    path.write_text('data_first\n_note.description\n;multiline\ndata_not_a_block\n;\n\ndata_second\n_atom.id C\n')
    assert len(_blocks(path)) == 2


def test_duplicate_cif_blocks_are_rejected_not_silently_overwritten(tmp_path):
    path = tmp_path / 'duplicate.cif'
    path.write_text('data_first\n_atom.id C\ndata_first\n_atom.id O\n')
    with pytest.raises(PhosphateError, match='Duplicate'):
        _blocks(path)


def test_explicit_op3_does_not_authorize_a_cyclic_phosphate(tmp_path):
    source = model(tmp_path, terminal=True)
    lines = source.read_text().splitlines(keepends=True)
    lines = [atom(10, "O3'", '1AP', 'A', 12, (-.5, -.8, -1.2))
             if line[12:16].strip() == "O3'" else line for line in lines]
    source.write_text(''.join(lines))
    with pytest.raises(PhosphateError, match='cyclic'):
        sanitize_phosphates(source, tmp_path / 'checked.pdb', allow_op3_sites=('A:12',))


def test_read_only_audit_never_creates_or_rewrites_files(tmp_path):
    source = model(tmp_path, extra=False)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    audit_phosphates(source, inspect_sites=('A:12',))
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
