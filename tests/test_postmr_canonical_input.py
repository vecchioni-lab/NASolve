"""Explicit canonical parents use the ordinary constructor and immutable evidence."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import shutil

import pytest

from nasolve.campaign_records import read_record, write_record
from nasolve.postmr import MutationAction, construct_postmr_model
from nasolve.postmr_canonical_input import (
    REPORT, canonical_input_plan, prepare_canonical_parent_input, read_canonical_parent_input,
)
from tests.test_postmr_canonical_seed import case, selected


def setup(tmp_path):
    model, source, template = case(tmp_path)
    action = MutationAction('A:1', 'PDU', 'ZZZ', 'coot-parent-overlap', parent_code='DT')
    target = tmp_path / 'target.cif'
    target.write_text(source.read_text().replace('PDU', 'ZZZ'))
    return model, source, template, action, target


def test_shared_constructor_delivers_seed_but_keeps_original_context(tmp_path, monkeypatch):
    model, source, template, action, target = setup(tmp_path)
    original = model.read_bytes()
    calls = []
    def coot(native_input, raw, actions, executable, directory, environment, dictionaries, parents, **kwargs):
        calls.append(native_input)
        assert native_input != model and selected(native_input.read_bytes(), 'DT')
        assert actions == (replace(action, before='DT'),)
        assert kwargs == {'timeout_seconds': 13.5}
        assert dictionaries == {'ZZZ': target}
        shutil.copyfile(native_input, parents[action.site])
        raw.write_bytes(original.replace(b'PDU', b'ZZZ'))
        log = directory / 'coot.log'; log.write_text('controlled Coot output\n')
        return directory / 'mutate.py', log
    monkeypatch.setattr('nasolve.postmr._run_coot', coot)
    result = construct_postmr_model(model, (action,), {'ZZZ': target}, tmp_path / 'out/model.pdb',
        coot_executable=tmp_path / 'coot', timeout_seconds=13.5,
        canonical_seed_dictionaries={'A:1': (source, template)})
    assert len(calls) == 1 and model.read_bytes() == original
    assert result['context_receipt']['reference_model_sha256'] == sha256(original).hexdigest()
    assert result['coordinate_restoration']['A:1']['status'] == 'GRAPH_FRAGMENT_RESTORED'
    saved = result['canonical_parent_input']
    assert read_canonical_parent_input(saved['directory']) == saved
    for name, atom in selected(original, 'PDU').items():
        if name in saved['receipt']['steps'][0]['proof']['preserved_scaffold_atoms']:
            assert selected(result['model'].read_bytes(), 'ZZZ')[name]['xyz'] == atom['xyz']


def test_cold_replay_after_original_sources_and_directory_are_gone(tmp_path):
    originals = tmp_path / 'originals'; originals.mkdir()
    model, source, template, action, _ = setup(originals)
    plan = canonical_input_plan((action,), {'A:1': (source, template)})
    saved = prepare_canonical_parent_input(model, plan, tmp_path / 'first')
    receipt = saved['receipt']
    moved = tmp_path / 'moved'; saved['directory'].rename(moved)
    shutil.rmtree(originals)
    before = {p.relative_to(moved): (p.read_bytes(), p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    assert read_canonical_parent_input(moved)['receipt'] == receipt
    assert before == {p.relative_to(moved): (p.read_bytes(), p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    assert str(tmp_path) not in str(receipt)


@pytest.mark.parametrize('defect', ['unknown_site', 'empty', 'wrong_method', 'same_parent', 'passthrough', 'bad_paths'])
def test_bad_explicit_choices_refuse_before_output_or_native_work(tmp_path, monkeypatch, defect):
    model, source, template, action, target = setup(tmp_path)
    options = {'A:1': (source, template)}; passthrough = ()
    if defect == 'unknown_site': options = {'B:9': (source, template)}
    elif defect == 'empty': options = {}
    elif defect == 'wrong_method': action = replace(action, method='coot-mutate-base')
    elif defect == 'same_parent': action = replace(action, before='DT')
    elif defect == 'passthrough': passthrough = ('A:1',)
    else: options = {'A:1': source}
    monkeypatch.setattr('nasolve.postmr._run_coot', lambda *a, **k: pytest.fail('native work started'))
    output = tmp_path / 'out/model.pdb'
    with pytest.raises(ValueError):
        construct_postmr_model(model, (action,), {'ZZZ': target}, output,
            coot_executable=tmp_path / 'coot', canonical_seed_dictionaries=options,
            passthrough_sites=passthrough)
    assert not output.parent.exists()


@pytest.mark.parametrize('defect', ['model', 'proof', 'source', 'anchor', 'escape', 'symlink', 'final_seed'])
def test_cold_replay_rejects_changes_even_with_a_resigned_receipt(tmp_path, defect):
    model, source, template, action, _ = setup(tmp_path)
    saved = prepare_canonical_parent_input(model, canonical_input_plan((action,), {'A:1': (source, template)}), tmp_path/'saved')
    root = saved['directory']; record = read_record(root / REPORT); step = record['steps'][0]
    if defect == 'model': (root / record['model']['path']).write_bytes(b'changed\n')
    elif defect == 'source': (root / step['source']['path']).write_bytes(b'changed\n')
    elif defect == 'proof': step['proof']['chi_after_degrees'] += 1
    elif defect == 'anchor': step['source']['anchor'] = 'absolute'
    elif defect == 'escape': step['source']['path'] = '../source.cif'
    elif defect == 'final_seed': record['model'] = record['input']
    else:
        path = root / step['source']['path']; path.unlink(); path.symlink_to(source)
    write_record(root / REPORT, record, replace=True)
    with pytest.raises((ValueError, RuntimeError)):
        read_canonical_parent_input(root)


def test_failed_native_work_keeps_replayable_parent_and_cannot_retry_in_place(tmp_path, monkeypatch):
    model, source, template, action, target = setup(tmp_path)
    def fails(*args, **kwargs): raise RuntimeError('controlled native failure')
    monkeypatch.setattr('nasolve.postmr._run_coot', fails)
    output = tmp_path / 'out/model.pdb'
    kwargs = dict(coot_executable=tmp_path/'coot', canonical_seed_dictionaries={'A:1': (source, template)})
    with pytest.raises(RuntimeError, match='controlled native failure'):
        construct_postmr_model(model, (action,), {'ZZZ': target}, output, **kwargs)
    root = output.parent / 'Coot/canonical_seeds'
    before = {p: p.read_bytes() for p in root.iterdir()}
    assert read_canonical_parent_input(root)['model'].is_file() and not output.exists()
    with pytest.raises(FileExistsError):
        construct_postmr_model(model, (action,), {'ZZZ': target}, output, **kwargs)
    assert before == {p: p.read_bytes() for p in root.iterdir()}


def test_multiple_sites_share_dictionary_copies_and_follow_action_order(tmp_path):
    model, source, template, action, _ = setup(tmp_path)
    lines = model.read_text().splitlines(keepends=True)
    extra = [l[:6]+f'{int(l[6:11])+1000:5d}'+l[11:21]+'C'+l[22:] for l in lines if l.startswith('HETATM')]
    model.write_text(''.join(lines[:-1]+extra+lines[-1:]))
    other = replace(action, site='C:1')
    saved = prepare_canonical_parent_input(model,
        canonical_input_plan((other,action), {'A:1':(source,template),'C:1':(source,template)}), tmp_path/'saved')
    assert len(list(saved['directory'].glob('dictionary-*.cif'))) == 2
    assert {p.name for p in saved['directory'].glob('*.pdb')} == {'input.pdb', 'canonical.pdb'}
    assert [s['action']['site'] for s in saved['receipt']['steps']] == ['C:1','A:1']
    assert read_canonical_parent_input(saved['directory']) == saved
