# Preparing a Phenix X-ray refinement for wwPDB OneDep

For each entry, take **the coordinate mmCIF and the structure-factor CIF from the same reviewed refinement**. Keep the original observations, their Free-R assignments and the refinement settings available. wwPDB has required PDBx/mmCIF coordinates for new macromolecular crystallography depositions since July 2019. The workflow below was checked with Phenix 2.2.1-6174. [wwPDB format announcement](https://www.wwpdb.org/news/news?year=2019) · [Phenix deposition guide](https://www.phenix-online.org/documentation/overviews/xray-structure-deposition.html)

## Write both files

AutoRefine already requests both CIF outputs. For a standalone `phenix.refine` job, enable model mmCIF and reflection CIF in **Output**. These two settings produce the files listed below.

```text
refinement.output.write_model_cif_file = True
refinement.output.write_reflection_cif_file = True
```

| Example file | What to use |
| --- | --- |
| `refined_001.cif` | Final coordinates, displacement parameters and refinement statistics. |
| `refined_001.reflections.cif` | The primary reflection table, including the Fobs used in refinement, their uncertainties and the free flags. |

The separate `export_final_f_model` option writes an MTZ useful for checking scales. Map coefficients describe density and can include reflections with no measured amplitude. For a new deposition, Phenix also provides `mmtbx.prepare_pdb_deposition` to add the full experimental sequence. [Phenix refinement output settings](https://phenix-online.org/documentation/reference/refinement.html) · [wwPDB file preparation](https://www.wwpdb.org/deposition/preparing-pdbx-mmcif-files)

## Prepare a revision of an existing entry

**Coordinates.** Start from the last reviewed deposition metadata. Match atoms by identity, including model, chain, residue, atom and alternate location. Carry over the actual refined coordinates, occupancies and displacement parameters, plus current `_refine` statistics and resolution-shell tables. Verify the full sample sequences, author-to-label numbering, modified components, assembly operators and TLS groups against the outgoing model. If coordinates moved to a different crystal copy, transform the affected anisotropic tensors and TLS descriptions into that frame.

**Space group.** Preserve the reviewed setting in both files after checking the cell, basis and operators. In the tested trigonal case the deposited Hermann–Mauguin spelling was `H 3`, with the alternate setting written `R 3 :H` in the coordinate CIF. A OneDep filename ending in `_P1` can contain this setting. Read the CIF tags. A genuine change of basis requires corresponding transformations of coordinates, Miller indices and flags.

**Modified residues.** Check the lab alias against the assigned Chemical Component Dictionary (CCD) identity using connectivity, stereochemistry and polymer attachment. Keep the full CCD code consistent across atoms, sequences, links and component definitions. Parse the entire outgoing CIF. In the tested Phenix output two appended local dictionaries repeated tags. The revision used one validated component block per modified residue from the actual refinement inputs. [wwPDB Chemical Component Dictionary](https://www.wwpdb.org/data/ccd)

**Reflections.** The tested STARANISO revisions kept the following order.

1. The matching entry’s primary block header and its experiment, cell and symmetry metadata.
2. The final Phenix `_refln` loop, including `F_meas_au`, `F_meas_sigma_au`, `pdbx_r_free_flag` and `status`. Verify the loop against the native export after writing.
3. The original processing blocks from **that crystal’s** `Data_1_autoPROC_STARANISO_all.cif`, appended once and checked byte for byte. One experiment had three supplemental blocks and another had five. OneDep can rename blocks in its returned SF file. Identify existing supplements by their contents and provenance before appending anything.

## Check diffraction from the outgoing pair

- Match the working and held-out observations to the original refinement input by Miller index, retaining anomalous mate identity where applicable. Check the actual numeric test-flag convention and each assignment. Compare Fobs **and** sigma against the amplitudes used, allowing for a documented common scale. For these files, `o` and `f` marked the working and free observations. Rows with missing measurements could still carry map coefficients.
- First reproduce the reported Rwork and Rfree from each set’s exported Fobs and scaled model amplitudes. Then independently calculate them from the **outgoing coordinates**, measured Fobs and original flags, recomputing scattering, solvent and scales. Record both readings and the settings. The first catches stale statistics or a mixed file pair. The second can catch a model that disagrees with otherwise self-consistent exported columns.

For an initial geometry screen, give CIF Doctor the exact final PDB and
`*_final.geo`. It verifies the lengths and angles at the coordinates in
that file, including modified residues and held atoms. In a five-cycle
metal–DNA example the starting GEO disagreed with the final coordinates.
The final GEO matched 920 within-residue bonds and 1,319 angles. The isolated
metal had no internal angles to measure. Independent wwPDB reference values
and inter-residue links need their own checks. [Command and coverage](cif-doctor.md#checking-bonds-and-angles-in-the-refined-model)

## Check what survives OneDep

When carrying a connection to another crystal copy, decode each partner's
image using the operator IDs declared in that file. For example, `8_465`
applies operator 8 followed by a shift of −1, +1 and 0 unit cells.
The shared Python function `nasolve.cif_deposition_links.resolve_deposition_image`
returns the resulting Gemmi operation. A missing or unrecognized code
leaves the image unresolved. The caller still identifies the atoms and
determines the chemical meaning of their connection.

For a recut nucleic-acid helix, first trace consecutive `label_seq_id` positions within each `label_asym_id`. They should describe the intended ordinary backbone in the stored coordinates. A crystal bond in `_struct_conn` can coexist with an apparent long polymer step when the sequence labels still span the cut. Place the representation boundary at the intended site and keep the sample’s strand sequence and true nick documented.

For each intended crystal phosphodiester identify the O3′ and P partners, their operators and cell translations, the O3′–P length and the angles to OP1 and OP2. An internal phosphate keeps P, OP1 and OP2. Recompute the mate in each entry’s own operator table, even for related crystals. [PDBx/mmCIF connectivity](https://mmcif.wwpdb.org/docs/user-guide/resources/ligands.html)

```sh
nasolve cif-doctor deposition-links upload_coordinates.cif --json
nasolve cif-doctor deposition-links upload_coordinates.cif --processed returned_coordinates.cif --json
```

Compare the **exact upload** to the processed **coordinate** mmCIF from the same OneDep pass. The validation-data CIF contains findings, and the PDF gives their interpretation. In one returned model the ordinary backbone was continuous and the coordinates were preserved, yet two intended 1.61 Å bonds appeared as symmetry clashes after the connection records disappeared. Give biocuration the two atom identities, operators, distances and submitted `_struct_conn` IDs. Check the next returned model and report for the outcome. [Doctor command and exit codes](cif-doctor.md#checking-backbone-continuity-before-deposition) · [OneDep tutorial](https://www.wwpdb.org/deposition/tutorial)

Keep each submitted pair, its checksums, the matching processed coordinates and validation report together by revision. Record which warnings cleared, which need a curator, and which revisions have only local checks. Read the standard polymer geometry table as well as the modified-residue section. A satisfactory diffraction check can accompany local sugar or base outliers.

## What the locked-DNA depositions established

The depositor confirmed that 3LNA (9Z65) passed OneDep on 24 November 2026. The preliminary report has zero standard outliers among 1,348 bonds and 2,065 angles, no chain breaks, and DCC Rwork/Rfree of 0.2008/0.2124. Two expected 1.61 Å symmetry phosphodiesters appear as close contacts. The separate ligand table retains observations on the two locked thymines, including their cage angles. The deposited R factors in the XML and the reported ligand geometry support the phosphate-repaired revision. The later reference-guided cage fit remains a local comparison. The separate 5LNA (9ZS1) return also had zero standard bond-length or bond-angle outliers and no chain breaks.

Three checks from these entries are useful for future modified nucleotides.

1. **Check the dictionary against the written sugar.** For example, ACL was assigned A1C3T. The reported O4′–C1′ distance at the locked cytosine was 1.63 Å. In the repaired, returned 3LNA coordinates it was 1.417 Å. Check the cage stereochemistry, base attachment and both adjacent phosphodiesters with the actual refinement dictionary. Keep an ordinary sugar control and use an independent chemical reference for unusual cage geometry when available.
2. **Check the backbone on both sides of a graft.** Review the incoming and outgoing O3′–P bonds, ester angles, both nonbridging oxygens and their orientation in the local duplex. A phosphate can point inward with plausible individual bond lengths. Fit a small connected backbone region against that crystal’s observations and compare the written polymer links, neighbouring base pairs and stack. A crossover needs its own local directions. A genuine nick retains its declared terminal chemistry.
3. **Check the export independently of the fit.** The two LNA models each had 58 ordinary backbone steps and two declared steps through crystal symmetry. Read each of the latter in its specified image and check sequence continuity after relabelling. Reopen the actual upload pair to verify the original indices and free flags. Compare it to the processed coordinate file and identify any declared links subsequently classified as close contacts. Apply this interpretation only to the named bonded atoms.
