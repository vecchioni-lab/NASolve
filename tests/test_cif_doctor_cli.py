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
    assess.assert_called_once_with(tmp_path, checkpoint='refine-002', refined_planes=False, refined_links=False,
                                   contact_sites=None, minimum_contact_overlap=None, b_factor_sites=None,
                                   bond_targets=False, template_bonds=False)
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


@pytest.mark.parametrize("mode", ["standalone", "bundle"])
@pytest.mark.parametrize("option", ["--refined-planes", "--refined-links"])
def test_refinement_measurements_need_a_run(tmp_path, capsys, mode, option):
    source = _graph(tmp_path / "source.cif")
    arguments = [str(source)] if mode == "standalone" else ["--bundle", str(tmp_path)]
    assert main(["cif-doctor", "assess", *arguments, option]) == 1
    assert option + " requires --run" in capsys.readouterr().err


def test_nonbonded_contacts_need_a_run(tmp_path, capsys):
    source = _graph(tmp_path / "source.cif")
    assert main(["cif-doctor", "assess", str(source), "--contacts-at", "B:4"]) == 1
    assert "--contacts-at requires --run" in capsys.readouterr().err


def test_contact_overlap_requires_sites_and_names_the_crystal_partner(tmp_path, capsys):
    assert main(["cif-doctor", "assess", "--run", str(tmp_path), "--min-contact-overlap", "0.4"]) == 1
    assert "requires --contacts-at" in capsys.readouterr().err
    row = {"endpoints": [["A:2", "DC", "N4"], ["B:4", "Z99", "N2T"]],
           "overlap_A": .45, "image_of_second_atom": "-x+y,-x,z"}
    audit = {"status": "REVIEW", "refined_contacts": {"status": "OBSERVED", "sites": {},
             "overlap_screen": {"minimum_overlap_A": .4, "contacts": [row]}}}
    with patch("nasolve.cif_doctor_run.assess_run", return_value=audit) as assess:
        assert main(["cif-doctor", "assess", "--run", str(tmp_path), "--contacts-at", "B:4",
                     "--min-contact-overlap", "0.4"]) == 2
    assert assess.call_args.kwargs["minimum_contact_overlap"] == .4
    text = capsys.readouterr().out
    assert "at least 0.4 Å" in text and "A:2 DC N4 to B:4 Z99 N2T (second atom at -x+y,-x,z)" in text


def test_b_factors_require_a_run_and_use_the_selected_sites(tmp_path, capsys):
    source = _graph(tmp_path / "source.cif")
    assert main(["cif-doctor", "assess", str(source), "--b-factors-at", "B:4"]) == 1
    assert "--b-factors-at requires --run" in capsys.readouterr().err
    audit = {"status": "REVIEW", "b_factors": {"sites": {"B:4": {
        "status": "PARTIAL", "component": "X01", "b_change_range_A2": [4.5, 4.6],
        "atoms": {"C": {}, "O": {}, "H": {}}, "matched_atoms": 2, "changed_occupancies": 1},
        "A:2": {"status": "UNASSESSED", "reason": "Requested residue is absent from the model"}}}}
    with patch("nasolve.cif_doctor_run.assess_run", return_value=audit) as assess:
        assert main(["cif-doctor", "assess", "--run", str(tmp_path), "--checkpoint", "refine-001",
                     "--b-factors-at", "B:4", "--b-factors-at", "A:2"]) == 2
    assert assess.call_args.kwargs["b_factor_sites"] == ["B:4", "A:2"]
    text = capsys.readouterr().out
    assert "+4.50 to +4.60 Å² across 2 of 3 atoms" in text and "A:2 B factors are unavailable" in text


def test_contact_sites_are_forwarded_individually_and_report_missing_tables(tmp_path, capsys):
    audit = {"status": "REVIEW", "preflight_contacts": None,
             "refined_contacts": {"status": "UNASSESSED", "reason": "Incomplete printed nonbonded section"}}
    with patch("nasolve.cif_doctor_run.assess_run", return_value=audit) as assess:
        assert main(["cif-doctor", "assess", "--run", str(tmp_path), "--checkpoint", "refine-001",
                     "--contacts-at", "A:2", "--contacts-at", "B:4"]) == 2
    assert assess.call_args.kwargs["contact_sites"] == ["A:2", "B:4"]
    text = capsys.readouterr().out
    assert "Preflight nonbonded geometry is unavailable" in text and "Incomplete printed nonbonded" in text


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
