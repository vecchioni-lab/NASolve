import coot
dictionary_status = coot.read_cif_dictionary("/Users/karolwoloszyn/Documents/GitHub/NASolve/src/nasolve/data/ligands/DF.cif")
print('NASOLVE_DICTIONARY', 'DF', dictionary_status)
if not dictionary_status:
    raise RuntimeError('Coot could not load the DF dictionary')
dictionary_status = coot.read_cif_dictionary("/Users/karolwoloszyn/Documents/GitHub/NASolve/src/nasolve/data/ligands/1AP.cif")
print('NASOLVE_DICTIONARY', '1AP', dictionary_status)
if not dictionary_status:
    raise RuntimeError('Coot could not load the 1AP dictionary')
imol = coot.handle_read_draw_molecule("/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/FD_dummy/AutoMR/run_002/PostMR/Model/mr_solution.pdb")
if imol < 0:
    raise RuntimeError('Coot could not read the PostMR model')
status = coot.mutate_base(imol, 'A', 12, '', 'DT')
print('NASOLVE_PARENT_MUTATE', 'A:12', 'DT', status)
if status != 1:
    raise RuntimeError('Coot parent mutation failed at A:12')
coot.write_pdb_file(imol, "/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/FD_dummy/AutoMR/run_002/PostMR/Coot/parent_A_12_DT.pdb")
ligand_imol = coot.get_monomer_from_dictionary('DF', 0)
print('NASOLVE_MONOMER', 'DF', ligand_imol)
if ligand_imol < 0:
    raise RuntimeError('Coot could not build DF from its dictionary')
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
if result_name != 'DF':
    raise RuntimeError('Coot produced the wrong residue at A:12')
status = coot.mutate_base(imol, 'B', 4, '', 'DA')
print('NASOLVE_PARENT_MUTATE', 'B:4', 'DA', status)
if status != 1:
    raise RuntimeError('Coot parent mutation failed at B:4')
coot.write_pdb_file(imol, "/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/FD_dummy/AutoMR/run_002/PostMR/Coot/parent_B_4_DA.pdb")
ligand_imol = coot.get_monomer_from_dictionary('1AP', 0)
print('NASOLVE_MONOMER', '1AP', ligand_imol)
if ligand_imol < 0:
    raise RuntimeError('Coot could not build 1AP from its dictionary')
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
if result_name != '1AP':
    raise RuntimeError('Coot produced the wrong residue at B:4')
removed_hydrogens = coot.delete_hydrogen_atoms(imol)
print('NASOLVE_REMOVED_HYDROGENS', removed_hydrogens)
coot.write_pdb_file(imol, "/Users/karolwoloszyn/Documents/GitHub/NASolve/examples/FD_dummy/AutoMR/run_002/PostMR/Model/after_coot_raw.pdb")
coot.coot_no_state_real_exit(0)
