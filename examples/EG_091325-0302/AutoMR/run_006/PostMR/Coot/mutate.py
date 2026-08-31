import coot
dictionary_status = coot.read_cif_dictionary("/Users/karolwoloszyn/Documents/GitHub/NASolve/src/nasolve/data/ligands/DE.cif")
print('NASOLVE_DICTIONARY', 'DE', dictionary_status)
if not dictionary_status:
    raise RuntimeError('Coot could not load the DE dictionary')
imol = coot.handle_read_draw_molecule("/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/EG_091325-0302/AutoMR/run_006/PostMR/Model/mr_solution.pdb")
if imol < 0:
    raise RuntimeError('Coot could not read the PostMR model')
status = coot.mutate_base(imol, 'A', 12, '', 'DT')
print('NASOLVE_PARENT_MUTATE', 'A:12', 'DT', status)
if status != 1:
    raise RuntimeError('Coot parent mutation failed at A:12')
coot.write_pdb_file(imol, "/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/EG_091325-0302/AutoMR/run_006/PostMR/Coot/parent_A_12_DT.pdb")
ligand_imol = coot.get_monomer_from_dictionary('DE', 0)
print('NASOLVE_MONOMER', 'DE', ligand_imol)
if ligand_imol < 0:
    raise RuntimeError('Coot could not build DE from its dictionary')
overlap_status = coot.overlap_ligands_py(ligand_imol, imol, 'A', 12)
print('NASOLVE_OVERLAP', 'A:12', overlap_status)
if not overlap_status:
    raise RuntimeError('Coot overlap failed at A:12')
replacement_imol = coot.add_ligand_delete_residue_copy_molecule(ligand_imol, 'A', 1, imol, 'A', 12)
print('NASOLVE_REPLACEMENT', 'A:12', replacement_imol)
if replacement_imol < 0:
    raise RuntimeError('Coot replacement failed at A:12')
imol = replacement_imol
result_name = coot.residue_name(imol, 'A', 12, '')
print('NASOLVE_RESULT', 'A:12', result_name)
if result_name != 'DE':
    raise RuntimeError('Coot produced the wrong residue at A:12')
removed_hydrogens = coot.delete_hydrogen_atoms(imol)
print('NASOLVE_REMOVED_HYDROGENS', removed_hydrogens)
coot.write_pdb_file(imol, "/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/EG_091325-0302/AutoMR/run_006/PostMR/Model/after_coot_raw.pdb")
coot.coot_no_state_real_exit(0)
