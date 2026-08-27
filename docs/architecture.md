# NASolve architecture

NASolve orchestrates external crystallographic programs; it does not reimplement them.

## Runtime precedence

Phenix is resolved in this order:

1. `--phenix-root`
2. `NASOLVE_PHENIX_ROOT`
3. saved user configuration
4. current `PATH`
5. validated installations in standard platform locations
6. a clear request to run `nasolve configure phenix PATH`

When multiple standard installations exist, NASolve selects the highest validated version.
An automatically discovered path is saved and revalidated on use. Each structure-solution report will record the exact
Phenix version and executable paths used.

Coot uses the same pattern independently: a one-run path, `NASOLVE_COOT`,
saved configuration, `PATH`, then bounded standard locations. Validation checks
both `coot --version` and the embedded Python API required by headless mutation.

## AutoMR input contract

`nasolve automr DATASET` uses one shared `nasolve.txt` schema for standard and
nonstandard models. The file records user intent; computed paths, checksums,
model statistics, and resolved ligand codes belong in the run log and JSON
report.

Standard example:

```ini
[automr]
mode = standard
frame = W
pair = D:T
```

Nonstandard example:

```ini
[automr]
mode = nonstandard
model = custom_model.pdb

[sequences]
A = GCGT

[mutations]
A:3 = 5IU
```

If `nasolve.txt` is absent, the command infers a nonstandard run from exactly
one top-level PDB, or takes a standard frame from `-W`, `-3GBI`, or `--frame`.
It then writes the minimal canonical file. Existing input is never overwritten.
CLI frame and pair values override file values and are captured in the frozen
run snapshot.

Current standard models are found in repository `MR_frames/`, through
`NASOLVE_MR_FRAMES`, or with `--frames-dir`. Approved models will later move
into package data for installed releases. `W` and `5W6W` resolve to the same
frame; absence of an explicit standard frame never defaults to W.

The model catalogue is organized by frame and ordered pair:

```text
MR_frames/
├── 5W6W/
│   ├── A_G.pdb
│   ├── C_G.pdb
│   └── D_F.pdb
└── 3GBI/
    └── C_C.pdb
```

Names use `FIRST_SECOND.pdb`, where each component is either a configured alias
or a literal NARestraints ligand code. Selection compares the resolved ligand
codes, not just filename spelling. Thus `D_F.pdb` matches either `D:F` or
`1AP:DF`. The deterministic fallbacks are `5W6W/C_G.pdb` and
`3GBI/C_C.pdb`. An exact pair model needs no pair mutation; a fallback records
the requested post-MR mutation. Missing fallbacks, malformed names, and
duplicate exact matches stop the run. An unrelated catalogue entry with an
unrecognized ligand token is skipped and recorded as a warning; it does not
block a valid requested pair. Requesting that unknown token still fails normal
ligand validation.

Every preflight receives an isolated directory:

```text
DATASET/AutoMR/run_001/
├── nasolve.input.txt
├── automr.log
├── report.json
└── Model/
    ├── input_model.pdb
    └── assessment.json
```

Adding `--execute` continues that same frozen run with an isolated Phaser
directory:

```text
DATASET/AutoMR/run_001/Phaser/
├── phaser.eff
├── phaser.log
├── PHASER.1.pdb
├── PHASER.1.mtz
├── mr_solution.pdb
└── mr_solution.mtz
```

The generated PHIL defines exactly one explicit ensemble named
`nasolve_model`; NASolve does not also use Phaser's `model` shortcut. It sets
`use_hetatm = True` and an explicit model RMSD of 1.0 A for compatibility with
Phenix builds that require either RMSD or fractional identity. It supplies one
NA composition using the model checker's polymer-residue count (`nres`), and
searches for one copy in H3/R3. The guarded
P1 shunt sets both composition and search copies to three. Phaser's original
outputs remain untouched, while stable `mr_solution` copies identify the
result selected for the next layer.

The copied model is checksum-verified, so HETATM records and all other bytes are
preserved. Residues written as HETATM whose residue names occur in the
NARestraints ligand library are counted as modified polymer residues, not as
detached ligands. This keeps chain lengths correct for modified nucleotides
while retaining separate counts for all HETATM atoms and nonpolymer hetero
residues. Full sequences must match the resulting model-chain residue count,
and explicit mutation targets must exist. Mutation precedence is full sequence,
standard pair, then explicit mutation.

### Dataset and symmetry discovery

Dataset discovery accepts the usual autoPROC/STARANISO naming variants rather
than renaming raw inputs. It prefers a unique MTZ whose punctuation-insensitive
name contains both `staraniso` and `alldata`, falling back to the only top-level
MTZ when there is exactly one. Metadata is the unique case-insensitive
`Data_1*.cif`; multiple candidates stop the run.

The symmetry gate applies only to standard W/3GBI recipes. NASolve compares:

1. the MTZ file symbol, number, and matrix symbol reported by
   `phenix.mtz.dump`;
2. every explicit space-group value in `Data_1*.cif`; and
3. only the final (bottom-most) `Spacegroup name` entry in `summary.html`.

Earlier indexing and POINTLESS alternatives in the HTML are ignored. `H 3`,
`H3`, `R 3`, `R3`, and the MTZ matrix form `R 3 :H` are accepted as one
equivalent class and use one MR copy. The exact MTZ label is retained in the
report as a required final-output patch after structure solution. A genuine P1
standard run stops by default; `--allow-p1-standard` records a strong red flag
and plans three MR copies. Other groups and disagreements between authoritative
sources stop the run. Nonstandard mode does not apply this symmetry rule.

## Pipeline gates

1. Validate and freeze AutoMR input and assess the unmodified search model.
2. Run Phaser in an isolated `Phaser/` directory without stripping heteroatoms.
3. Classify the best TFZ: `>= 8.0` pass; `7.0–7.99` review; `< 7.0` fail.
4. `nasolve postmr RUN` applies supported site changes, builds the restraint
   stack, and runs ReadySet with hydrogens disabled.
5. If PostMR finds nucleotide-bound I, Br, or Se, `nasolve autosol RUN` performs
   guarded MR-SAD phasing and validates at least one heavy-atom site against
   the model under crystallographic symmetry.
6. Call `phenix.refine` behind its own validation gate.

The default command still stops after step 1. `nasolve automr ... --execute`
runs step 2 and applies step 3. A passing run exits 0; TFZ 7.0–7.99 is retained
for review and exits 3; failure or missing output exits 4.

## PostMR contract

PostMR is deliberately a separate command so an accepted Phaser result can be
inspected and rerun deterministically before refinement. It refuses to
overwrite an existing `PostMR/` directory. `MR_SUCCESS` is accepted;
`MR_REVIEW` requires an explicit override; other statuses stop.

The W-frame manifest assigns requested pair roles to `A:12` and `B:4`.
Canonical DNA/RNA changes use a generated headless Coot script. Curated
modified nucleotides use a canonical-parent mutation followed by dictionary
monomer construction, overlap, and residue replacement. Coot runs with its
backup directory redirected beneath the run and removes hydrogens before
writing. Full sequences and arbitrary modified-base construction remain closed
gates rather than being silently ignored.

For curated modifications, Coot also writes a canonical-parent snapshot.
NASolve copies the coordinates, occupancies, and B factors of every shared
atom back into the replaced residue and requires the complete sugar/phosphate
atom set to survive. Thus dictionary overlap positions only the new chemistry;
it cannot rotate or curl the existing phosphate. The restoration inventory is
recorded in the run report.

The registry also declares exact parent/target atom substitutions. `DE`, `DF`,
and `S6G` place sulfur along the canonical `C-O` vector, use the transformed
dictionary model only for the reviewed C-S bond length, and inherit occupancy
and B factor from the replaced oxygen. This prevents an otherwise valid Coot
graph overlap from placing the one new sulfur atom on the wrong side of a base.
`C38` and `5IU` use the same guarded construction with parents `DC` and `DT`.
Their iodine is placed along the external bisector defined by the mapped
`C4-C5-C6` ring atoms, using the C-I distance from the dictionary's ideal
coordinate set and the parent `C5` occupancy and B factor. The transformed Coot
monomer is not trusted for the halogen bond length.

For W/5W6W, NARestraints consumes the packaged `Std_padd.txt` specification
(`A 11:13` / `B 5:3`) and remains the sole source of stacking restraints. The
portable 5W6W secondary-structure template contains 17 non-overlapping
scaffold base pairs, no stacking pairs, and no historical input paths, cell,
map, output, or GUI settings.

Problematic Phenix components are explicit curated-library entries. User token
`E` maps to the laboratory PDB-compatible `DE`, not official CCD `8RO`, whose
topology describes a different sulfur-ring compound. `F` maps to `DF`, with
official deposition identity `A1AAZ`; `D` maps to official `1AP`; and `Q` maps
to official `S6G` with canonical parent `DG`. The registry
defines canonical parents and required/forbidden sulfur bonds, which are
validated before Coot or ReadySet runs. ReadySet receives the curated CIF,
executes with `actions.hydrogens=False`, and is run with `cwd` set to its own
directory because Phenix 1.20.1 accepts but ignores `input.output_dir`. The
output is rejected if it contains hydrogen coordinates or changes total or
HETATM atom counts.

NARestraints v1.1.1 has a legacy `DF` mapping of canonical `O2` to `S2`; the
A1AAZ-derived component uses `S1`. The PostMR adapter patches a copied residue
record in process memory, restores the builder's original loader in a `finally`
block, and records the correction. The installed workbook is never mutated,
and a future upstream `S1` mapping requires no correction.
The same adapter trims the exact legacy `S6G C5` value `C5 ` to `C5`.

The ReadySet model is scanned by element rather than by a closed residue list.
Iodine, bromine, and selenium in nucleotide-like residues are the initial
anomalous trigger set. The PDB element column is authoritative; a conservative
atom-name fallback is recorded when the column is blank. This allows a new
modified residue to trigger the later AutoSol branch without first adding its
residue code to an AutoSol allowlist.

## AutoSol contract

AutoSol is conditional and deliberately separate from PostMR. It requires a
`POSTMR_READY` report containing one supported heavy-atom element and refuses
to overwrite an existing `AutoSol/` directory. The current trigger elements
are iodine, bromine, and selenium; the element registry is intentionally open
to reviewed additions.

For a standard frame, NASolve copies the adjacent `seq_base.txt` into the run.
For a nonstandard model, complete sequences recorded in the frozen run may be
written to the same input instead. The wavelength is read from `summary.html`,
preferring the high-precision assignment and rejecting inconsistent repeated
values. `phenix.mtz.dump` must confirm a complete anomalous intensity or
amplitude quartet before execution.

The AutoSol request is MR-SAD guided by the original Phaser solution PDB, not
the modified PostMR model. This avoids using the modeled heavy atom to validate
its own anomalous signal. NASolve supplies the heavy-atom element and
wavelength, leaves the number of sites unspecified, uses every logical CPU,
and explicitly sets both `build=False` and
`phase_improve_and_build=False`. After execution it reads `autosol.eff` and
rejects the run unless both build controls remain false, every `sites` value is
unset, and the requested processor count is effective.

Output discovery is content-based. The refinement input must contain a full
Hendrickson-Lattman phase quartet and anomalous observations. The AutoSol HA
PDB is compared with every expected nucleotide heavy atom of the same element.
For H3/R3, matching expands the three point operators, R-centering
translations, and neighboring unit cells; P1 uses lattice translations. The
branch automatically accepts phases when at least one expected atom has a
same-element HA site within 4 A. A nearest site between 4 and 8 A produces an
`AUTOSOL_REVIEW` result and requests inspection. A more distant or absent site,
or an AutoSol execution/output failure, produces `AUTOSOL_WARNING`. Review and
warning outcomes do not block the ordinary MR refinement path, but their phase
files are not automatically approved for use. All sites and match attempts are
retained in the report, while extra unmatched sites do not block this phase of
the pipeline.
