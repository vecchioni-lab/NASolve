"""Ordinary PostMR preserves construction and ReadySet dictionary inputs.

Toy coordinates and a copying shell executable exercise orchestration only;
actual installed ReadySet/native qualification is recorded separately.
"""
from hashlib import sha256
import json
import shutil
from pathlib import Path

import pytest

from tests.helpers import make_postmr_report, make_ready_set, pdb_record
from tests.test_postmr import make_data_root


def _ordinary_run(tmp_path, monkeypatch, codes, *, numerical_fixture=False):
    import nasolve.postmr as postmr
    import nasolve.cif_postmr_cache as cache

    data = make_data_root(tmp_path)
    for code, bond in [('DF', 'C2 S1'), ('C38', 'C5 I')]:
        (data / 'ligands' / (code + '.cif')).write_text(
            f'data_comp_{code}\nloop_\n_chem_comp_bond.comp_id\n'
            f'_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n{code} {bond}\n#\n')
    first = 'DE' if codes else 'DA'
    second = 'DF' if 'DF' in codes else 'DG'
    source = tmp_path / 'source.pdb'
    model = pdb_record('HETATM' if codes else 'ATOM', 1, 'P', first, 'A', 12)
    model += pdb_record('HETATM' if second == 'DF' else 'ATOM', 2, 'P', second, 'B', 4)
    if 'C38' in codes:
        model += pdb_record('HETATM', 3, 'P', 'C38', 'C', 2)
    source.write_text(model + 'END\n')
    run = tmp_path / 'run'
    make_postmr_report(run, source, first=first, second=second,
                       requested='E:F' if second == 'DF' else 'E:G' if codes else 'A:G')
    before = source.read_bytes()
    injected = {}
    if numerical_fixture:
        # Cache qualification has its own tests. This public-boundary fixture
        # distinguishes the reused numerical input from the ordinary DF source
        # while letting all production acquisition/read checks execute first.
        acquire = cache.prepare_postmr_dictionaries
        read = cache.read_postmr_dictionaries
        def stage(*args, **kwargs):
            report = acquire(*args, **kwargs)
            folder = Path(args[2])
            candidate = folder / 'DE' / 'explicit_numerical_fixture.cif'
            candidate.write_bytes((data / 'ligands/DE.cif').read_bytes()
                                  + b'# EXPLICIT_NUMERICAL_INTEGRATION_FIXTURE\n')
            injected.update(folder=folder, candidate=candidate)
            return report
        def selected(folder):
            loaded = read(folder)
            if Path(folder) == injected.get('folder'):
                loaded['DE']['dictionary'] = injected['candidate']
            return loaded
        monkeypatch.setattr(cache, 'prepare_postmr_dictionaries', stage)
        monkeypatch.setattr(cache, 'read_postmr_dictionaries', selected)
    commands = []
    execute = postmr.subprocess.run
    def observed(command, **kwargs):
        commands.append(list(command))
        return execute(command, **kwargs)
    monkeypatch.setattr(postmr.subprocess, 'run', observed)
    def builder(_model, _pairs, output):
        output.write_text('geometry_restraints.edits {}\n')
    result = postmr.prepare_postmr(run, make_ready_set(tmp_path), data_root=data,
                                   narestraints_builder=builder)
    assert source.read_bytes() == before
    assert result.status == 'POSTMR_READY'
    ready = [cmd for cmd in commands if cmd[0] == str((tmp_path / 'phenix.ready_set').resolve())]
    assert len(ready) == 1
    return run, result, ready[0], data


@pytest.mark.parametrize('codes', [(), ('DE',), ('DE', 'DF'), ('DE', 'DF', 'C38')])
def test_ordinary_readyset_registers_each_selected_component_file(tmp_path, monkeypatch, codes):
    from nasolve.ligand_profiles import dictionary_component_codes
    run, result, command, data = _ordinary_run(tmp_path, monkeypatch, codes)
    inputs = [Path(arg.split('=', 1)[1]) for arg in command
              if arg.startswith('ready_set.input.cif_file_name=')]
    # A copying fake cannot reveal the Phenix parser defect itself; the command
    # contract must register every component independently instead of relying on
    # a multi-component container's parser return type.
    assert [dictionary_component_codes(path) for path in inputs] == [{code} for code in sorted(codes)]
    expected = result.postmr_directory / 'Restraints'
    assert inputs == [expected / (code + '.cif') for code in sorted(codes)]
    assert all(path.read_bytes() == (data / 'ligands' / path.name).read_bytes() for path in inputs)
    source_report = json.loads((expected / 'cif_doctor_source.json').read_bytes())
    assert source_report['readyset_dictionary_input_policy'] == 'per-component-files-v1'
    refs = source_report['readyset_dictionary_inputs']
    assert len(refs) == len(inputs)
    for ref, path in zip(refs, inputs):
        assert ref == {'anchor': 'run', 'relative_path': path.relative_to(run).as_posix(),
                       'sha256': sha256(path.read_bytes()).hexdigest(), 'size': path.stat().st_size}
    combined = source_report['readyset_dictionary_input']
    if codes:
        path = run / combined['relative_path']
        assert dictionary_component_codes(path) == set(codes)
        assert path not in inputs
        assert combined['sha256'] == sha256(path.read_bytes()).hexdigest()
    else:
        assert combined is None
    assert 'ready_set.actions.hydrogens=False' in command
    assert 'ready_set.actions.optimise_ligand_geometry=False' in command


def test_ordinary_handoff_keeps_selected_numerics_and_source_fallback_separate(tmp_path, monkeypatch):
    run, result, command, data = _ordinary_run(tmp_path, monkeypatch, ('DE', 'DF'), numerical_fixture=True)
    inputs = [Path(arg.split('=', 1)[1]) for arg in command
              if arg.startswith('ready_set.input.cif_file_name=')]
    assert [p.name for p in inputs] == ['DE.cif', 'DF.cif']
    assert b'EXPLICIT_NUMERICAL_INTEGRATION_FIXTURE' in inputs[0].read_bytes()
    assert inputs[1].read_bytes() == (data / 'ligands/DF.cif').read_bytes()
    folder = result.postmr_directory / 'Restraints'
    assert (folder / 'source_dictionaries/DE.cif').read_bytes() == (data / 'ligands/DE.cif').read_bytes()
    assert b'EXPLICIT_NUMERICAL_INTEGRATION_FIXTURE' in (folder / 'curated_ligands.cif').read_bytes()
    report = json.loads(result.report_path.read_bytes())
    assert report['readyset']['command'] == command
    assert report['cif_doctor']['dictionary_reuse']['solution_report']['requires_cif_review'] is False



def _ordinary_construction_source_case(tmp_path, monkeypatch, change):
    """Toy ordinary orchestration; Coot/ReadySet substitutes prove input transport only."""
    import nasolve.postmr as postmr
    from tests.test_postmr import postmr_model_text, make_data_root, PROTECTED_PARENT_ATOMS
    from tests.helpers import make_postmr_report, make_ready_set, pdb_record
    data = make_data_root(tmp_path)
    selected = data / 'ligands/DE.cif'
    original_bytes = selected.read_bytes()
    model = tmp_path / 'input.pdb'
    scaffold = ''.join(pdb_record('ATOM', i + 1, name, 'DT', 'A', 12,
        x=i * .2, y=float(i % 3), z=float((i // 3) % 3), element=name[0])
        for i, name in enumerate((*PROTECTED_PARENT_ATOMS, 'N1', 'C2', 'O2', 'N3', 'C4', 'O4', 'C5', 'C7', 'C6')))
    model.write_text(scaffold + ''.join(postmr_model_text(first='DT').splitlines(keepends=True)[1:]))
    run = tmp_path / 'run'
    make_postmr_report(run, model)
    observed = []
    snapshot = run / 'PostMR/Coot/source_dictionaries/DE.cif'

    def coot(input_model, output, actions, executable, directory, environment, dictionaries, parents, **kwargs):
        assert len(actions) == 1 and actions[0].after == 'DE'
        assert snapshot.read_bytes() == original_bytes
        if change in {'temporary_original', 'persistent_original'}:
            selected.write_bytes(original_bytes + b'# changed outside construction\n')
        observed.append((dictionaries['DE'], dictionaries['DE'].read_bytes()))
        if change == 'temporary_original':
            selected.write_bytes(original_bytes)
        elif change == 'changed_snapshot':
            snapshot.write_bytes(original_bytes + b'# changed consumed snapshot\n')
        elif change == 'missing_snapshot':
            snapshot.unlink()
        shutil.copyfile(input_model, parents['A:12'])
        mutated = []
        for line in input_model.read_text().splitlines(keepends=True):
            if line.startswith(('ATOM', 'HETATM')) and line[21:22] == 'A' and line[22:26].strip() == '12':
                line = line[:17] + ' DE' + line[20:]
                if line[12:16].strip() == 'O4':
                    line = line[:12] + ' S4 ' + line[16:76] + ' S' + line[78:]
            mutated.append(line)
        output.write_text(''.join(mutated))
        log = directory / 'coot.log'
        log.write_text('CONTROLLED_Coot_INPUT_TRANSPORT_ONLY\n')
        return directory / 'mutate.py', log

    monkeypatch.setattr(postmr, '_run_coot', coot)
    ready_calls = []
    ready = postmr._run_readyset
    def readyset(*args, **kwargs):
        ready_calls.append(True)
        return ready(*args, **kwargs)
    monkeypatch.setattr(postmr, '_run_readyset', readyset)
    def builder(_model, _pairs, output):
        output.write_text('geometry_restraints.edits {}\n')
    def execute():
        return postmr.prepare_postmr(run, make_ready_set(tmp_path), data_root=data,
            coot_executable=tmp_path / 'controlled-coot', narestraints_builder=builder)
    return execute, run, data, model, selected, original_bytes, snapshot, observed, ready_calls


def test_ordinary_construction_consumes_frozen_source_during_original_change(tmp_path, monkeypatch):
    import json
    from nasolve.run_context import resolve_artifact_path
    execute, run, data, model, selected, source_bytes, snapshot, seen, ready_calls = _ordinary_construction_source_case(tmp_path, monkeypatch, 'temporary_original')
    result = execute()
    assert result.status == 'POSTMR_READY' and ready_calls == [True]
    assert seen == [(snapshot, source_bytes)]
    assert selected.read_bytes() == snapshot.read_bytes() == source_bytes
    assessment = json.loads((run / 'PostMR/Restraints/cif_doctor_mutation.json').read_bytes())
    reference, = assessment['inputs']
    assert reference['anchor'] == 'run'
    assert resolve_artifact_path(reference, run) == snapshot
    # Only owned fixture originals are removed. The consumed bytes remain bound.
    shutil.rmtree(data)
    model.unlink()
    relocated = run.rename(tmp_path / 'relocated-run')
    assert not run.exists()
    resolved = resolve_artifact_path(reference, relocated)
    assert resolved == relocated / 'PostMR/Coot/source_dictionaries/DE.cif'
    assert resolved.read_bytes() == source_bytes


@pytest.mark.parametrize('change', ['changed_snapshot', 'missing_snapshot', 'persistent_original'])
def test_ordinary_construction_rejects_changed_input_before_readyset(tmp_path, monkeypatch, change):
    from nasolve.postmr import PostMRPreparationError
    execute, run, data, model, selected, source_bytes, snapshot, seen, ready_calls = _ordinary_construction_source_case(tmp_path, monkeypatch, change)
    with pytest.raises(PostMRPreparationError, match='dictionary|Dictionary'):
        execute()
    assert len(seen) == 1 and ready_calls == []
    assert (run / 'PostMR/Model/after_coot_raw.pdb').is_file()
    assert (run / 'PostMR/Coot/coot.log').is_file()
    assert not (run / 'PostMR/report.json').exists()
    assert json.loads((run / 'report.json').read_bytes())['status'] == 'MR_SUCCESS'
    if change != 'persistent_original':
        assert selected.read_bytes() == source_bytes
    if change == 'changed_snapshot':
        assert snapshot.read_bytes().endswith(b'# changed consumed snapshot\n')
