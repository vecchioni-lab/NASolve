import coot
dictionary_status = coot.read_cif_dictionary("/Users/karolwoloszyn/Documents/GitHub/NASolve/src/nasolve/data/ligands/S6G.cif")
print('NASOLVE_DICTIONARY', 'S6G', dictionary_status)
if not dictionary_status:
    raise RuntimeError('Coot could not load the S6G dictionary')
dictionary_status = coot.read_cif_dictionary("/Users/karolwoloszyn/Documents/GitHub/NASolve/src/nasolve/data/ligands/C38.cif")
print('NASOLVE_DICTIONARY', 'C38', dictionary_status)
if not dictionary_status:
    raise RuntimeError('Coot could not load the C38 dictionary')
imol = coot.handle_read_draw_molecule("/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/QiC_120325_0513/AutoMR/run_002/PostMR/Model/mr_solution.pdb")
if imol < 0:
    raise RuntimeError('Coot could not read the PostMR model')
status = coot.mutate_base(imol, 'A', 12, '', 'DG')
print('NASOLVE_PARENT_MUTATE', 'A:12', 'DG', status)
if status != 1:
    raise RuntimeError('Coot parent mutation failed at A:12')
coot.write_pdb_file(imol, "/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/QiC_120325_0513/AutoMR/run_002/PostMR/Coot/parent_A_12_DG.pdb")
ligand_imol = coot.get_monomer_from_dictionary('S6G', 0)
print('NASOLVE_MONOMER', 'S6G', ligand_imol)
if ligand_imol < 0:
    raise RuntimeError('Coot could not build S6G from its dictionary')
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
if result_name != 'S6G':
    raise RuntimeError('Coot produced the wrong residue at A:12')
status = coot.mutate_base(imol, 'B', 4, '', 'DC')
print('NASOLVE_PARENT_MUTATE', 'B:4', 'DC', status)
if status != 1:
    raise RuntimeError('Coot parent mutation failed at B:4')
coot.write_pdb_file(imol, "/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/QiC_120325_0513/AutoMR/run_002/PostMR/Coot/parent_B_4_DC.pdb")
ligand_imol = coot.get_monomer_from_dictionary('C38', 0)
print('NASOLVE_MONOMER', 'C38', ligand_imol)
if ligand_imol < 0:
    raise RuntimeError('Coot could not build C38 from its dictionary')
overlap_status = coot.overlap_ligands_py(ligand_imol, imol, 'B', 4)
print('NASOLVE_OVERLAP', 'B:4', overlap_status)
if not overlap_status:
    raise RuntimeError('Coot overlap failed at B:4')
replacement_imol = coot.add_ligand_delete_residue_copy_molecule(ligand_imol, 'A', 1, imol, 'B', 4)
print('NASOLVE_REPLACEMENT', 'B:4', replacement_imol)
if replacement_imol < 0:
    raise RuntimeError('Coot replacement failed at B:4')
imol = replacement_imol
result_name = coot.residue_name(imol, 'B', 4, '')
print('NASOLVE_RESULT', 'B:4', result_name)
if result_name != 'C38':
    raise RuntimeError('Coot produced the wrong residue at B:4')
removed_hydrogens = coot.delete_hydrogen_atoms(imol)
print('NASOLVE_REMOVED_HYDROGENS', removed_hydrogens)
coot.write_pdb_file(imol, "/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/QiC_120325_0513/AutoMR/run_002/PostMR/Model/after_coot_raw.pdb")
coot.coot_no_state_real_exit(0)
