# Fresh mixed-base DNA mechanics test

This test asks whether ordinary NASolve can construct, prepare and refine a
mixed modified-DNA target from explicit sequence intent. It copies real donor
diffraction but assigns hypothetical target chemistry. A successful run tests
software mechanics; R factors cannot validate these invented identities.

## Inputs and pipeline

The fresh canonical W scaffold has 42 DNA residues: A21/B7/C7/D7, with C
numbered 8–14. Complete annotated sequences and an explicit DNA reference
declare every target. The combined layout reproduces the previously reviewed
pair positions without reusing its PostMR coordinates or numerical CIF bundle.

| Family | Sites | Literal target components |
| --- | --- | --- |
| D:T | A:5 / C:11 | 1AP / DT |
| B:S | A:6 / C:10 | IGU / IMC |
| Z:P | A:12 / B:4 | DZ / DP |
| K:X | A:20 / D:3 | CGY / DX |
| Additional context | A:7 / C:9 | 5CM / DG |
| Additional context | A:19 / D:4 | DF / DA |

Lab B:S means IGU:IMC. S6G is a separate thioguanine component. `force` remains
unset; geometry templates do not replace literal chemical identities.

All four declared linear strands start with free 5′ hydroxyls. The committed
`5W6W_noPO4.pdb` still contains P/OP1/OP2 at B:1 and C:8. Preparation removes
only those six coordinate records and their ANISOU/CONECT references in a new
copy, preserves all internal phosphates and retained coordinates, and records
the original/prepared hashes and exact deletions. The explicit empty terminal
phosphate declaration also prevents the ordinary W D:1 phosphate request.

The [schema-2 recipe](recipes/synthetic-dna-combined.toml) freezes full-auto
continuation and **AutoSol disabled**, with the scientific reason retained.
Observed anomalous arrays and nucleotide classification remain unchanged.
Initial refinement and subsequent Doctor branches receive no experimental
phases. The path is preflight → Phaser → PostMR/Coot → ReadySet → AutoRefine,
then bounded Refine Doctor when eligible. CIF Doctor reports sources before
mutation and before ReadySet, and the effective dictionary/model afterward.
Review gates for chemistry, integrity and failed MR remain active.

## One-file laptop shuttle

`scripts/build_synthetic_dna_shuttle.py` builds a standalone Python runner from
the complete NASolve source/package data, NARestraints source and workbook,
committed W templates and this recipe. The runner extracts a hash-verified
runtime into a fresh external session and stages donor files locally. It
does not install packages, patch a checkout, reuse old native results or
include donor diffraction in the downloadable artifact.

Default donor anchor is the known laptop Cedar checkout's
`examples/TestSets/GZ11`, with exact paths `staraniso_alldata-unique.mtz`,
`Data_1_autoPROC_STARANISO_all.cif` and `summary.html`. All three are required
before input allocation. `--repo`, `--donor`, `--mtz`, `--cif`, `--summary`,
`--output-parent`, `--phenix-root` and `--coot` retain explicit-path control;
there is no basename search or automatic donor substitution. `--stage-only`
prepares and freezes the plan without native tools.

The established laptop Python supplies Biopython, NumPy and openpyxl; Python
3.10 additionally needs tomli. Native execution uses the installed Phenix and
Coot. Worker imports resolve the bundled NASolve/NARestraints paths. An
explicit `NASOLVE_NATIVE_ENV_ISOLATION=1` worker opt-in then removes inherited
Python/venv/CCP4 library overrides before native discovery while preserving
Python's already initialized import paths. Default campaign environments are
unchanged. An isolated configuration copies only saved external-tool settings;
the user's workspace pointer and configuration file are preserved.

Outputs include portable `synthetic-inputs.json` artifact references, a frozen
campaign plan, immutable numbered runs/stage receipts, worker logs, Doctor
receipts when reached, and `shuttle_receipt.json`. The final console summary
shows measured MTZ space group and selected model space group when available.
Each invocation allocates a fresh session. Original donor/scaffold files remain
untouched.

## Evidence and limits

Offline regression checks verify all 42 compiled DNA targets, exact pair roles,
free termini, preserved internal coordinates, input hashes, exclusive outputs,
ordinary campaign planning, relocated source-bundled execution, and explicit
AutoSol/phase exclusion. These are input/orchestration tests, not a new native
Phenix/Coot execution. The intended laptop versions are Phenix 2.2.1-6174 and
Coot 1.3.3; actual native versions belong to the new run report.

Fresh IGU/IMC/CGY/DX sources can be graph-only. Ordinary ReadySet numerical
generation and generic linked-site preparation remain unqualified together;
the earlier combined success selected numerical dictionaries and diagnostic
linkage derivatives manually. The new run retains a real blocker and its
evidence if these steps fail. It does not inject previous repaired resources,
automatically adopt Doctor suggestions or claim assembly stitching. High Rwork
or Rfree on deliberately mismatched donor chemistry is not a chemical verdict.

## Adaptable methods wording

We tested modified-nucleotide preparation using a synthetic 42-residue DNA
target containing four noncanonical pair families at predefined sites within
a canonical W search scaffold. Complete sequence annotations specified all
residue identities. Source-preserving preparation removed terminal phosphate
groups at declared free-hydroxyl strand starts. Real donor diffraction was
copied without altering reflection observations or Free-R flags. A frozen
campaign disabled anomalous phasing because the hypothetical model chemistry
did not describe the measured donor. Ordinary PostMR construction and
ReadySet preparation were assessed by CIF Doctor before and after dictionary
generation; eligible outputs proceeded to phase-free refinement and bounded
refinement diagnostics. Input hashes, stage receipts and retained failures
defined the tested scope, separate from experimental identity validation.
