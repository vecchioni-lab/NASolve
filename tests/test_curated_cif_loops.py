"""Layout-independent curated readers; source chemistry and coordinates stay exact."""

import pytest

from nasolve.cif_doctor import _cif_tokens
from nasolve.curated_ligands import (
    CURATED_LIGANDS, _dictionary_bonds, dictionary_ideal_bond_length,
    ligand_dictionary, validate_ligand_dictionary,
)
from nasolve.ligand_profiles import _blocks


def rewrap(text, width=1):
    """Change whitespace only, keeping each CIF value and quote boundary."""
    tokens = []
    for value, quoted in _cif_tokens(text):
        if quoted:
            if '\n' in value or ('"' in value and "'" in value):
                tokens.append('\n;' + value + '\n;\n')
            else:
                quote = '"' if '"' not in value else "'"
                tokens.append(quote + value + quote)
        else:
            tokens.append(value)
    # Data-block delimiters must remain on their own physical lines for _blocks.
    lines = []
    pending = []
    for token in tokens:
        if token.lower().startswith('data_'):
            if pending: lines.append(' '.join(pending)); pending = []
            lines.append(token)
        else:
            pending.append(token)
            if len(pending) == width:
                lines.append(' '.join(pending)); pending = []
    if pending: lines.append(' '.join(pending))
    return '\n# whitespace is not a row boundary\n\n'.join(lines) + '\n'


@pytest.mark.parametrize('code', sorted(CURATED_LIGANDS))
@pytest.mark.parametrize('width', [1, 7])
def test_all_curated_sources_keep_topology_across_line_wrapping(tmp_path, code, width):
    source = ligand_dictionary(code); original = source.read_bytes()
    candidate = tmp_path/'wrapped.cif'; candidate.write_text(rewrap(original.decode(), width))
    # Independent existing block parser proves that only presentation changed.
    assert [b.values for b in _blocks(candidate)] == [b.values for b in _blocks(source)]
    assert _dictionary_bonds(candidate) == _dictionary_bonds(source)
    validate_ligand_dictionary(code, candidate)
    assert source.read_bytes() == original


@pytest.mark.parametrize('code,first,second', [('DZ', "C1'", 'C1'), ('DF', 'C2', 'S1'), ('5IU', 'C5', 'I5'), ('5IU', "C5'", 'I5')])
@pytest.mark.parametrize('width', [1, 7])
def test_target_distances_preserve_coordinates_and_prime_names(tmp_path, code, first, second, width):
    source = ligand_dictionary(code); candidate = tmp_path/'wrapped.cif'
    candidate.write_text(rewrap(source.read_text(), width))
    assert dictionary_ideal_bond_length(candidate, first, second) == dictionary_ideal_bond_length(source, first, second)


ATOM = '''loop_
_chem_comp_atom.comp_id
_chem_comp_atom.atom_id
_chem_comp_atom.x
_chem_comp_atom.y
_chem_comp_atom.z
ABC C5 0 0 0
ABC C5' 9 0 0
ABC I5 2 0 0
'''
BOND = '''loop_
_chem_comp_bond.comp_id
_chem_comp_bond.atom_id_1
_chem_comp_bond.atom_id_2
ABC C5 I5
ABC C5' C5
'''


@pytest.mark.parametrize('malformed', [
    BOND + 'ABC C5\n',
    BOND + BOND,
    BOND + 'data_other\n' + BOND,
    BOND.replace('ABC C5\' C5', 'XYZ C5\' C5'),
    BOND.replace('ABC C5\' C5', 'ABC ? C5'),
    BOND.replace('ABC C5\' C5', 'ABC C5 C5'),
])
def test_bond_reader_refuses_partial_ambiguous_or_conflicting_tables(tmp_path, malformed):
    p=tmp_path/'invalid.cif'; p.write_text('data_comp\n'+malformed)
    with pytest.raises(ValueError): _dictionary_bonds(p)


@pytest.mark.parametrize('malformed', [
    ATOM + 'ABC C5 7 0 0\n',
    ATOM + 'ABC X 1 2\n',
    ATOM + ATOM,
    ATOM + 'data_other\n' + ATOM,
    ATOM.replace('ABC I5', 'XYZ I5'),
    ATOM.replace('I5 2', 'I5 nan'),
    ATOM.replace('I5 2', 'I5 inf'),
])
def test_coordinate_reader_refuses_ambiguous_incomplete_or_nonfinite_values(tmp_path, malformed):
    p=tmp_path/'invalid.cif';p.write_text('data_comp\n'+malformed)
    with pytest.raises(ValueError): dictionary_ideal_bond_length(p,'C5','I5')


def test_ideal_coordinates_remain_preferred_without_fallback_on_bad_ideal(tmp_path):
    p=tmp_path/'ideal.cif'
    text='data_comp\nloop_\n_chem_comp_atom.atom_id\n'+''.join('_chem_comp_atom.'+key+'\n' for key in ('x','y','z','pdbx_model_Cartn_x_ideal','pdbx_model_Cartn_y_ideal','pdbx_model_Cartn_z_ideal'))+'C5 0 0 0 1 1 1\nI5 9 0 0 3 1 1\n'
    p.write_text(text)
    assert dictionary_ideal_bond_length(p,'C5','I5') == 2
    p.write_text(text.replace('3 1 1','? 1 1'))
    with pytest.raises(ValueError): dictionary_ideal_bond_length(p,'C5','I5')


def test_declared_component_identity_must_match_curated_request(tmp_path):
    p=tmp_path/'wrong.cif';p.write_text(ligand_dictionary('DF').read_text().replace('DF','XYZ'))
    with pytest.raises(ValueError): validate_ligand_dictionary('DF',p)


def test_normal_postmr_accepts_token_wrapped_dz_source(tmp_path, monkeypatch):
    import shutil
    from nasolve import curated_ligands
    from .test_component_normalization_postmr import test_normal_postmr_keeps_source_and_freezes_target_definition
    data = tmp_path/'ligands'
    shutil.copytree(curated_ligands.ligand_data_directory(), data)
    p = data/'DZ.cif'; p.write_text(rewrap(p.read_text()))
    before = p.read_bytes()
    monkeypatch.setattr(curated_ligands, 'ligand_data_directory', lambda data_root=None: data)
    test_normal_postmr_keeps_source_and_freezes_target_definition(tmp_path, monkeypatch, '1W5', 'DZ', True)
    assert p.read_bytes() == before
