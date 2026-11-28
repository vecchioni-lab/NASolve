"""Keep the laboratory DY reference reusable without activating a preview as restraints."""
import hashlib
import json
from collections import Counter
from importlib.resources import files

from Bio.PDB.MMCIF2Dict import MMCIF2Dict


def reference():
    root = files('nasolve').joinpath('data/chemical_references')
    metadata = json.loads(root.joinpath('DY.json').read_text())
    path = root.joinpath(metadata['definition']['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata['definition']['sha256']
    return metadata, MMCIF2Dict(str(path))


def test_dy_reference_has_exact_retained_triazole_graph():
    metadata, cif = reference()
    names = cif['_chem_comp_atom.atom_id']
    elements = dict(zip(names, cif['_chem_comp_atom.type_symbol']))
    assert Counter(elements.values()) == {'C': 11, 'H': 13, 'N': 5, 'O': 4}
    assert set(cif['_chem_comp_atom.charge']) == {'0'}
    orders = {frozenset((a,b)): order for a,b,order in zip(
        cif['_chem_comp_bond.atom_id_1'], cif['_chem_comp_bond.atom_id_2'],
        cif['_chem_comp_bond.value_order'])}
    expected = [('N1','C2',1),('C2','N3',1),('N3','C4',2),('C4','C5',1),
        ('C5','C6',2),('C6','N1',1),('C2','O2',2),('C4','N1T',1),
        ('N1T','N2T',1),('N2T','C3T',2),('C3T','N4T',1),('N4T','C5T',2),
        ('C5T','N1T',1),('N1',"C1'",1),("C1'","C2'",1),("C2'","C3'",1),
        ("C3'","C4'",1),("C4'","O4'",1),("O4'","C1'",1),
        ("C4'","C5'",1),("C3'","O3'",1),("C5'","O5'",1)]
    heavy = {edge:order for edge,order in orders.items() if all(elements[n]!='H' for n in edge)}
    assert heavy == {frozenset((a,b)): 'SING' if order==1 else 'DOUB' for a,b,order in expected}
    assert len(orders) == 35
    assert not {'O4', 'C7', 'P', 'OP1', 'OP2', 'OP3'} & set(names)
    assert metadata['identity']['laboratory_code'] == 'DY'


def test_dy_atom_identity_stereo_and_preview_are_consistent():
    metadata, cif = reference()
    names = cif['_chem_comp_atom.atom_id']
    assert len(names) == len(set(names)) == 33
    assert cif['_atom_site.label_atom_id'] == names
    assert set(cif['_atom_site.label_comp_id']) == {'DY'}
    assert set(cif['_chem_comp_atom.comp_id']) == {'DY'}
    assert cif['_chem_comp.id'] == ['DY']
    stereo = {name:state for name,state in zip(names,cif['_chem_comp_atom.pdbx_stereo_config']) if state!='N'}
    assert stereo == {"C1'": 'R', "C3'": 'S', "C4'": 'R'}
    for axis in 'xyz':
        assert cif['_chem_comp_atom.model_Cartn_'+axis] == cif['_atom_site.Cartn_'+axis]
    assert metadata['identity']['isomeric_smiles'] == 'O=c1nc(-n2cncn2)ccn1[C@H]1C[C@H](O)[C@@H](CO)O1'


def test_dy_reference_is_not_a_runtime_dictionary_or_implicit_alias():
    metadata, cif = reference()
    from nasolve.curated_ligands import CURATED_LIGANDS
    from nasolve.residue_aliases import RESIDUE_ALIASES
    assert 'DY' not in CURATED_LIGANDS
    assert 'Y' not in RESIDUE_ALIASES
    assert 'YTR' not in RESIDUE_ALIASES
    assert metadata['qualification']['mutation_enabled'] is False
    assert metadata['qualification']['refinement_restraints'] == 'NOT_QUALIFIED'
    assert not any(k.startswith(('_chem_comp_angle.', '_chem_comp_tor.', '_chem_comp_plane_atom.')) for k in cif)
    assert '_chem_comp_bond.value_dist' not in cif
    assert not metadata['identity']['deposition_code']


def test_dy_reference_is_self_contained_package_data():
    metadata, _ = reference()
    from pathlib import PurePosixPath
    path=PurePosixPath(metadata['definition']['path'])
    assert not path.is_absolute() and '..' not in path.parts and len(path.parts)==1
    assert metadata['definition']['anchor'] == 'nasolve:data/chemical_references'
    serialized=json.dumps(metadata)
    assert '/Users/' not in serialized and '/private/tmp/' not in serialized
    assert metadata['qualification']['chimerax_readback']['exact_named_connectivity'] is True
    assert metadata['qualification']['chimerax_readback']['atoms'] == 33


def test_packaged_preview_enters_existing_generation_adapter_without_ideal_claim():
    from nasolve.cif_generation_input import source_input_files
    from nasolve.cif_stereochemistry_audit import _graph,_values
    from tempfile import TemporaryDirectory
    from pathlib import Path
    source=files('nasolve').joinpath('data/chemical_references/DY.cif');original=source.read_bytes()
    binding,derived=source_input_files(original,'DY');report=json.loads(derived['prepared/preparation.json'])
    assert report['coordinate_origin']=='SOURCE_MODEL_COORDINATES_NOT_INDEPENDENT_IDEAL'
    assert report['source']['sha256']==hashlib.sha256(original).hexdigest()
    with TemporaryDirectory() as temporary:
        path=Path(temporary)/'consumer.cif';path.write_bytes(derived['prepared/consumer.cif'])
        assert _graph(_values(path,'DY'))==_graph(_values(source,'DY'))
    assert source.read_bytes()==original and source_input_files(original,'DY')==(binding,derived)
