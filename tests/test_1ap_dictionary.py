"""The 1AP override must be a parameterized dictionary, not just a CCD graph."""
from pathlib import Path
from Bio.PDB.MMCIF2Dict import MMCIF2Dict


def test_1ap_has_energy_types_and_numeric_bond_targets():
    path = Path(__file__).parents[1] / 'src/nasolve/data/ligands/1AP.cif'
    data = MMCIF2Dict(str(path))
    assert '_chem_comp_atom.type_energy' in data
    assert '_chem_comp_bond.value_dist' in data
    assert all(t not in {'', '.', '?'} for t in data['_chem_comp_atom.type_energy'])


def test_1ap_source_geometry_is_byte_preserved_from_reviewed_library():
    import hashlib
    from nasolve.curated_ligands import validate_curated_dictionary
    path = Path(__file__).parents[1] / 'src/nasolve/data/ligands/1AP.cif'
    validate_curated_dictionary('1AP', path)
    text = path.read_text()
    text = text[text.index('data_comp_list'):].replace(
        '1AP 1AP "2,6-DIAMINOPURINE NUCLEOTIDE" DNA 36 23 .',
        '1AP 1AP "2,6-DIAMINOPURINE NUCLEOTIDE" NON-POLYMER 36 23 .', 1)
    data = text.encode()
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == '1be06d4bb0848891fd3e7dca22d217dd2ad1b69b'


def test_1ap_validation_rejects_graph_only_or_conflicting_dictionary(tmp_path):
    import pytest
    from nasolve.curated_ligands import validate_curated_dictionary
    source = Path(__file__).parents[1] / 'src/nasolve/data/ligands/1AP.cif'
    for text in [source.read_text().replace('_chem_comp_atom.type_energy', '_chem_comp_atom.not_energy'),
                 source.read_text().replace(' DNA 36 23 .', ' NON-POLYMER 36 23 .'),
                 source.read_text().replace('1AP N1    N NRD6', 'WRG N1    N NRD6')]:
        path = tmp_path / 'bad.cif'
        path.write_text(text)
        with pytest.raises(ValueError):
            validate_curated_dictionary('1AP', path)
