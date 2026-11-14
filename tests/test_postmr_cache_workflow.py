"""Qualified storage -> selection -> ordinary PostMR, without replacing cache APIs.

The five-atom component and captured native inventory are explicit synthetic
fixtures, and ReadySet only copies coordinates. This checks integration and
provenance, not the chemical/native validity of a real DE nucleotide.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from tests.helpers import make_postmr_report, make_ready_set
from tests.test_cif_candidate_usability import native_case, component
from tests.test_cif_postmr_cache import API, ENERGY
from tests.test_postmr import make_data_root, postmr_model_text


def environment(tmp_path, monkeypatch):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    from nasolve.cif_dictionary_store import make_dictionary_request, publish_dictionary
    from nasolve.curated_ligands import ligand_source, validate_ligand_dictionary
    import nasolve.phenix_runtime as runtime
    values = component()
    # Give the toy graph the curated validator's literal C4-S4 bond. Neither
    # this graph nor its fake native inventory is evidence for actual DE science.
    for key, column in values.items():
        if 'atom_id' in key:
            values[key] = [{'CTR': 'C4', 'O': 'S4'}.get(v, v) for v in column]
    values['_chem_comp_atom.type_symbol'][1] = 'S'
    values['_chem_comp_atom.type_energy'][1] = 'S'
    source, candidate, model, native = native_case(tmp_path / 'synthetic', values)
    for path in [source, candidate]:
        path.write_bytes(path.read_bytes().replace(b'Q17', b'DE'))
    candidate.write_bytes(candidate.read_bytes() + b'# DISTINCT_QUALIFIED_NUMERICS\n')
    model.write_text(''.join(line[:17] + ' DE' + line[20:] + '\n'
                            if line.startswith(('ATOM  ', 'HETATM')) else line + '\n'
                            for line in model.read_text().splitlines()))
    native = json.loads(json.dumps(native).replace('Q17', 'DE'))
    qualification = qualify_candidate_native(source, candidate, model, 'DE', native)
    assert qualification['native_usable']
    data = make_data_root(tmp_path)
    selected = data / 'ligands/DE.cif'
    selected.write_bytes(source.read_bytes())
    validate_ligand_dictionary('DE', selected)
    root = tmp_path / 'fake-phenix'
    (root / 'bin').mkdir(parents=True)
    ready = make_ready_set(root / 'bin')
    executable = root / 'bin/phenix.python'
    executable.write_bytes(b'EXPLICIT_SYNTHETIC_DISPATCHER_NEVER_EXECUTED\n')
    def refs(names):
        result = []
        for name in names:
            path = root / 'lib/python3.11/site-packages' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('EXPLICIT_SYNTHETIC_API ' + name)
            result.append({'anchor': 'phenix_installation', 'path': path.relative_to(root).as_posix(),
                           'sha256': sha256(path.read_bytes()).hexdigest()})
        return result
    consumer = {'name': 'Phenix/CCTBX', 'version': 'SYNTHETIC_TEST',
                'executable_sha256': sha256(executable.read_bytes()).hexdigest(),
                'api_sources': refs(API), 'energy_sources': refs(ENERGY)}
    installation = SimpleNamespace(root=root, version='SYNTHETIC_TEST',
        executables={'phenix.python': executable, 'phenix.ready_set': ready}, environment={})
    calls = []
    def discovery(path, *, base_environment):
        assert Path(path) == ready and base_environment['NASOLVE_CIF_STORE'] == str(tmp_path / 'store')
        calls.append('configured consumer discovery')
        return installation
    # Only external installation discovery is a fixture; real fingerprint,
    # source, candidate, publication, selection and frozen-reader checks run.
    monkeypatch.setattr(runtime, 'installation_from_candidate', discovery)
    request = make_dictionary_request(selected, 'DE',
        source_authority=ligand_source('DE', data, ready_set_executable=ready).authority,
        recipe={'policy_id': 'cif-source-native-complete-candidate-v1',
                'source_metadata_policy': 'cif-source-declared-dna-metadata-v1', 'single_block_steps': 180},
        generator={'name': 'Phenix eLBOW', 'version': 'SYNTHETIC_TEST'})
    provenance = {'converged': False, 'stopping': 'NOT_CONVERGED_LIMIT',
                  'notes': ['Synthetic usable saved endpoint; iteration limit retained.']}
    entry = publish_dictionary(tmp_path / 'store', request, selected, candidate,
                               qualification, consumer=consumer, provenance=provenance)
    return data, candidate, ready, installation, entry, provenance, calls


@pytest.mark.parametrize('condition', ['reuse', 'changed_consumer', 'changed_source', 'damaged_entry'])
def test_qualified_store_feeds_ordinary_postmr_and_survives_relocation(tmp_path, monkeypatch, condition):
    from nasolve.postmr import prepare_postmr
    from nasolve.cif_postmr_cache import read_postmr_dictionaries
    data, candidate, ready, installation, entry, provenance, calls = environment(tmp_path, monkeypatch)
    source = data / 'ligands/DE.cif'
    if condition == 'changed_consumer':
        installation.executables['phenix.python'].write_bytes(b'NEW_SYNTHETIC_CONSUMER\n')
    elif condition == 'changed_source':
        source.write_bytes(source.read_bytes() + b'# new authoritative source bytes\n')
    elif condition == 'damaged_entry':
        (entry['directory'] / 'dictionary.cif').write_text('DAMAGED')
    store_before = {p.relative_to(tmp_path / 'store'): p.read_bytes()
                    for p in (tmp_path / 'store').rglob('*') if p.is_file()}
    model = tmp_path / 'input.pdb'
    model.write_text(postmr_model_text())
    source_bytes, model_bytes = source.read_bytes(), model.read_bytes()
    run = tmp_path / 'run'
    make_postmr_report(run, model)
    def builder(_model, _pairs, output):
        output.write_text('geometry_restraints.edits {}\n')
    result = prepare_postmr(run, ready, data_root=data, narestraints_builder=builder,
                           environment={**os.environ, 'NASOLVE_CIF_STORE': str(tmp_path / 'store')})
    assert result.status == 'POSTMR_READY'
    report = json.loads(result.report_path.read_text())
    reuse = report['cif_doctor']['dictionary_reuse']
    expected = candidate.read_bytes() if condition == 'reuse' else source_bytes
    folder = result.postmr_directory / 'Restraints'
    assert (folder / 'DE.cif').read_bytes() == expected
    assert (folder / 'source_dictionaries/DE.cif').read_bytes() == source_bytes
    inputs = [Path(x.split('=', 1)[1]) for x in report['readyset']['command']
              if x.startswith('ready_set.input.cif_file_name=')]
    assert inputs == [folder / 'DE.cif'] and inputs[0].read_bytes() == expected
    assert reuse['reused_components'] == (['DE'] if condition == 'reuse' else [])
    frozen = read_postmr_dictionaries(folder / 'dictionary_reuse')['DE']
    if condition == 'reuse':
        assert frozen['numerics']['entry_id'] == entry['entry_id']
        assert frozen['numerics']['provenance'] == provenance
        assert frozen['report']['converged'] is False
        assert 'iteration limit' in ' '.join(reuse['solution_report']['notes']['DE'])
    else:
        assert frozen['numerics'] is None
    assert calls == (['configured consumer discovery'] if condition in {'reuse', 'changed_consumer'} else [])
    assert source.read_bytes() == source_bytes and model.read_bytes() == model_bytes
    assert store_before == {p.relative_to(tmp_path / 'store'): p.read_bytes()
                            for p in (tmp_path / 'store').rglob('*') if p.is_file()}
    # Remove only this test's owned inputs/cache/installation, then move its run.
    for path in [tmp_path / 'store', installation.root, data, tmp_path / 'synthetic']:
        shutil.rmtree(path)
    model.unlink()
    relative = folder.relative_to(run)
    moved = run.rename(tmp_path / 'relocated')
    result = read_postmr_dictionaries(moved / relative / 'dictionary_reuse')['DE']
    assert result['dictionary'].read_bytes() == expected
    assert result['source'].read_bytes() == source_bytes
    assert not run.exists()
