"""Public assessment/preparation commands preserve scientific inputs."""
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve.cli import main


def _graph(path: Path) -> Path:
    path.write_text('''data_test
loop_
_chem_comp_atom.comp_id
_chem_comp_atom.atom_id
_chem_comp_atom.type_symbol
TST "C5'" C
TST C5 C
loop_
_chem_comp_bond.comp_id
_chem_comp_bond.atom_id_1
_chem_comp_bond.atom_id_2
_chem_comp_bond.value_order
TST "C5'" C5 SING
''')
    return path


def test_assess_json_preserves_source_and_writes_explicit_receipt(tmp_path):
    source = _graph(tmp_path / 'source.cif')
    original = source.read_bytes()
    receipt = tmp_path / 'audit.json'
    with redirect_stdout(io.StringIO()) as stream:
        code = main(['cif-doctor', 'assess', str(source), '--stage', 'source',
                     '--output', str(receipt), '--json'])
    assert code in (0, 2)
    audit = json.loads(stream.getvalue())
    assert audit == json.loads(receipt.read_text())
    assert audit['audit_kind'] == 'cif_restraint_assessment'
    assert audit['inputs'][0]['anchor'] == 'inputs'
    assert audit['inputs'][0]['relative_path'] == 'source.cif'
    assert source.read_bytes() == original


def test_existing_output_is_refused_before_preparation(tmp_path):
    source = _graph(tmp_path / 'source.cif')
    output = tmp_path / 'existing.cif'
    output.write_text('keep')
    with patch('nasolve.cif_doctor_repair.prepare_dictionary') as prepare:
        assert main(['cif-doctor', 'prepare', str(source), '--output', str(output),
                     '--recipe', 'torsion-alternates-v1']) == 1
    prepare.assert_not_called()
    assert output.read_text() == 'keep'


def test_read_only_run_uses_selected_checkpoint_without_runtime_discovery(tmp_path):
    audit = {'audit_kind': 'cif_restraint_assessment', 'status': 'REVIEW',
             'components': [], 'findings': [], 'inputs': []}
    with patch('nasolve.cif_doctor_run.assess_run', return_value=audit) as assess, \
            patch('nasolve.cli.discover_phenix') as discover, \
            redirect_stdout(io.StringIO()) as stream:
        assert main(['cif-doctor', 'assess', '--run', str(tmp_path),
                     '--checkpoint', 'refine-002', '--json']) == 2
    assess.assert_called_once_with(tmp_path, checkpoint='refine-002')
    discover.assert_not_called()
    assert json.loads(stream.getvalue()) == audit


def test_prepare_surfaces_invalid_candidate_without_adoption(tmp_path):
    source = _graph(tmp_path / 'source.cif')
    source.write_text(source.read_text().replace('TST C5 C', 'TST "C5\'" C'))
    output = tmp_path / 'candidate.cif'
    with redirect_stdout(io.StringIO()) as stream:
        assert main(['cif-doctor', 'prepare', str(source), '--output', str(output),
                     '--recipe', 'torsion-alternates-v1']) == 3
    assert 'Assessment: INVALID; adoption: BLOCKED' in stream.getvalue()
    assert output.exists()


def test_compare_reports_explicit_change_without_rewriting_files(tmp_path):
    source = _graph(tmp_path / 'source.cif')
    candidate = tmp_path / 'candidate.cif'
    candidate.write_text(source.read_text().replace(' SING', ' DOUB'))
    original = source.read_bytes(), candidate.read_bytes()
    with redirect_stdout(io.StringIO()) as stream:
        assert main(['cif-doctor', 'compare', str(source), str(candidate), '--json']) == 2
    comparison = json.loads(stream.getvalue())
    assert comparison['status'] == 'REVIEW'
    assert comparison['source_assessment']['inputs'][0]['relative_path'] == 'source.cif'
    assert comparison['effective_assessment']['inputs'][0]['relative_path'] == 'candidate.cif'
    assert comparison['differences']
    assert original == (source.read_bytes(), candidate.read_bytes())


def test_standalone_model_reference_keeps_the_audited_digest(tmp_path):
    source = _graph(tmp_path / 'source.cif')
    model = tmp_path / 'model.pdb'
    model.write_text('original')
    audit = {'audit_kind': 'cif_restraint_assessment', 'status': 'PASS',
             'inputs': [{'name': source.name, 'sha256': 'source-digest'}],
             'model': {'name': model.name, 'sha256': 'audited-model-digest', 'size': 8}}

    def assessed(*args, **kwargs):
        model.write_text('subsequent unrelated edit')
        return audit

    with patch('nasolve.cif_doctor.assess_dictionaries', side_effect=assessed), \
            redirect_stdout(io.StringIO()) as stream:
        assert main(['cif-doctor', 'assess', str(source), '--model', str(model), '--json']) == 0
    reference = json.loads(stream.getvalue())['model_reference']
    assert reference['sha256'] == 'audited-model-digest'
    assert reference['size'] == 8


@pytest.mark.parametrize('arguments', [
    ['cif-doctor', 'assess'],
    ['cif-doctor', 'assess', 'source.cif', '--run', '/a/run'],
    ['cif-doctor', 'assess', 'source.cif', '--checkpoint', 'postmr'],
])
def test_ambiguous_or_missing_input_is_an_error(arguments):
    assert main(arguments) == 1
