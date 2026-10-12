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
AutoSol/phase exclusion. These input/orchestration tests are separate from the
returned native run below. The intended laptop versions are Phenix
2.2.1-6174 and Coot 1.3.3; the returned report identifies Phenix 2.2.1 and its
2.2.1-6174 installation path, but contains no new Coot version receipt.

Fresh IGU/IMC/CGY/DX sources can be graph-only. Ordinary ReadySet numerical
generation and generic linked-site preparation remain unqualified together;
the earlier combined success selected numerical dictionaries and diagnostic
linkage derivatives manually. The new run retains a real blocker and its
evidence if these steps fail. It does not inject previous repaired resources,
automatically adopt Doctor suggestions or claim assembly stitching. High Rwork
or Rfree on deliberately mismatched donor chemistry is not a chemical verdict.

### Returned fresh run: a numerical-generation failure

The first fresh run on **2026-10-11** reached **MR_SUCCESS**, TFZ **13.10** and
LLG **196**, in input space group **H 3** (MTZ number 146, R 3 :H). Its session
is `synthetic-dna-mechanics-om4jv7qq`, campaign
`synthetic-dna-combined-2n4kszi5`, run `dataset/AutoMR/run_001`, anchored to the
user's `NASolve-live-tests` directory. The frozen staging receipt contains all
42 DNA targets, free 5′-OH preparation, AutoSol disabled and experimental
phases off. This is a new acquisition test, separate from the earlier combined
trial's TFZ 12.9 and prepared numerical resources.

PostMR stopped when the generated IGU dictionary contained a **C2–N3 bond
target of 0.000 Å with sigma 0.020 Å**. Both atom coordinates in that dictionary
are `(-3.0660, 3.0937, -0.1804)` Å. The graph-only source has distinct supplier
ideal coordinates for those atoms. ReadySet/eLBOW therefore produced numerical
terms with collapsed geometry; this was not merely a raw CCD copied unchanged
into the output. All 35 generated IGU atoms have energy types, with 37 bond
and 65 angle terms. Filling the missing numerical columns succeeded; numerical
validity did not.

Generation also changed the declared phosphate state: source IGU has 37 atoms,
39 bonds and formal charge 0; the output has 35 atoms, 37 bonds and formal
charge −2. HOP2/HOP3 and their bonds disappeared, OP2/OP3 changed from charge
0 to −1, and P–OP1/P–OP2/P–OP3 became delocalized bond-order declarations.
These changes are independent of the zero target. They are not approved
linked-site modifications or a reason to silently choose that protonation
state for every component.

The returned ZIP and all 16 manifest entries were checksum-verified. Exact
hashes, the narrowly observed field changes and the remaining evidence gaps
are recorded in [the machine-readable evidence](igu-readyset-generation-evidence.json)
and [native ledger](native-modified-pair-live-validation.md#fresh-synthetic-dna-run--returned-readyset-blocker).
No AutoSol, AutoRefine or Doctor refinement was reached, and no replacement
dictionary was adopted. The existing rule that preserves explicitly supplied
numerical dictionaries remains correct; ReadySet output is not automatically
authoritative just because it was regenerated.

### General candidate recovery

`src/nasolve/cif_generation.py` provides explicit whole-component candidate
generation and inspection through `inspect_component_generation` and
`generate_elbow_candidate`. The opt-in command is
`cif-doctor generate-candidate SOURCE --code CODE --output-parent PATH --timeout-seconds 600 --json`.
It writes a fresh output directory and never retries or edits the failed
PostMR run.

Chemistry comes from the frozen source graph. Exact source atom names and
complete supplier **ideal** coordinates form a separate initial-geometry and
naming seed. eLBOW is requested to retain chirality, disable automatic hydrogen
addition, and perform optimized generation (`--opt`); the installed backend and
its actual behavior must be read from the native log. The returned optimized
attempt used **Recife Model 1 (RM1)**. Source atom
IDs, elements, bond orders, hydrogens, formal charges and stereochemical
declarations are compared with the candidate. Nonpositive bond targets or
coincident bonded heavy-atom coordinates reject the candidate. Graph/state
differences remain visible for review; a successful native generator exit is
insufficient for adoption. The procedure neither invents a target for the
failed bond nor uses the distorted model as numerical authority.

This layer must distinguish unparameterized sources, generated numerical
defects, intentionally supplied numerical dictionaries and verified internal
versus terminal linkage context. It must preserve original source and failed
outputs, bind evidence by hash, and keep candidate generation separate from
effective-dictionary selection. A fresh native source/ReadySet/PostMR-hook
probe, candidate review and linked-site interpretation remain pending. The
one-click campaign is therefore **not yet fixed or qualified** for this
general source-generation case.

### Returned candidate probe: installed CLI incompatibility

The independent IGU candidate probe has now returned from
`NASolve-live-tests/cif-generation-probe-fp4afs_7`, candidate directory
`candidates/cif-generation-9_t3qtnl`. It preserved the original failed run,
all selected inputs and the frozen **37-atom, formal-charge-0** IGU source.
The independent supplier-ideal naming/geometry seed was written, but native
eLBOW exited **2** after **2.071012 seconds** with
`no such option: --initial-geometry`. No `candidate.cif` was produced. This
is a wrapper/installed-command-line compatibility failure; optimization,
generated numerical quality and new candidate chemistry were **not assessed**.

The returned archive and all **18** manifest entries were verified. The exact
failure, command, source/seed hashes and unassessed layers are recorded in
[the CLI compatibility evidence](elbow-cli-compatibility-evidence.json).
The top-level probe receipt says `CANDIDATES_AWAITING_REVIEW`, but its actual
IGU generation receipt says `FAILED`; the latter and native log define the
outcome. That aggregate-summary bug must be corrected without rewriting the
failed receipt or presenting an absent candidate for review.

The general compatibility correction consults the **installed** eLBOW
`--help` before assembling the command, accepts only advertised option aliases
that preserve the required naming, initial-geometry, hydrogen, chirality and
optimization semantics, and retains the help evidence and exact chosen command.
Missing required capability must stop before generation; it must not silently
drop the independent seed or optimization request. Installed help output was
not included in this first failed bundle. The corrected second attempt below
returned that help and completed native generation; the original failed
ReadySet run remains unchanged.

### Returned optimized candidate: geometry recovered, state rejected

The second independent probe, `cif-generation-probe-le2ki6f4`, confirmed
installed aliases **`--initial_geometry`** and **`--add_hydrogens`**, retained
their help evidence, and ran eLBOW to native **exit 0** in **24.107482 seconds**.
The log identifies **RM1**, not AM1. A whole-component IGU candidate was
produced: **C2–N3 = 1.387 ± 0.029 Å** with distinct atom coordinates;
**C1′–N9 = 1.473 ± 0.035 Å**. All bond targets are positive and the earlier
zero-target/coincident-bonded-atom defect is absent in this new candidate.
These are numerical-generation findings, not chemical or linked-site approval.

The candidate was correctly **REJECTED** for source-state changes: **HOP2/HOP3
were removed**, **37 → 35 atoms**, OP2/OP3 charges **0 → −1**, total formal
charge **0 → −2**, and the three phosphate bond orders became delocalized.
The generator completed while its candidate violated the exact source-state
contract. The old source and failed runs remain preserved; no candidate was
adopted and ReadySet/refinement was not retried.

The inspector also treated four **PLANE-01 REVIEW** findings as an invalid or
incomplete numerical dictionary. Their central-angle deviations from an exact
interior planar branch were only **0.08°, 0.06°, 0.10° and 0.13°**, with
uncorrelated sigma-adjustment lower bounds **0.018, 0.014, 0.021 and 0.030**.
These diagnostics exclude finite plane weights and correlations and have no
calibrated scientific rejection threshold. They must remain review evidence
rather than becoming hard invalidity or an instruction to force every angle
sum to 360°. That gate correction does not approve the changed phosphate state.

Installed help advertises **`--pH=low` to retain exact input chemistry**.
The v3 generator interface requires that source-state-preservation control,
with its installed capability evidence, instead of silently letting eLBOW
deprotonate the input. This is an engine preservation mode, not a selected
experimental pH, a preferred protonation state or a global nucleotide policy.
The next fresh candidate still must pass explicit graph, hydrogen, charge and
stereochemical comparison. Its native execution and all linked-site/native
proxy qualification remain **pending**.

All **22** returned manifest entries were verified. Candidate SHA-256 is
`3049dd5b5d79e2b6961d70a87e8b2c16c793a6078f4122d824697ffda43ed27b`;
[the optimized-state evidence](elbow-optimized-state-evidence.json) records
the exact command, backend, interface result, numeric recovery, chemical
rejection and soft-review findings. Both earlier failure bundles remain
historical evidence.

## Adaptable methods wording

We tested modified-nucleotide preparation using a synthetic 42-residue DNA
target containing four noncanonical pair families at predefined sites within
a canonical W search scaffold. Complete sequence annotations specified all
residue identities. Source-preserving preparation removed terminal phosphate
groups at declared free-hydroxyl strand starts. Real donor diffraction was
copied without altering reflection observations or Free-R flags. A frozen
campaign disabled anomalous phasing because the hypothetical model chemistry
did not describe the measured donor. Ordinary PostMR construction and
ReadySet preparation are assessed by CIF Doctor before and after dictionary
generation; eligible outputs can proceed to phase-free refinement and bounded
refinement diagnostics. The returned first run reached successful molecular
replacement and stopped at a collapsed IGU numerical bond target. Explicit
whole-component regeneration uses source graph and ideal-coordinate seeds,
preserving candidates for numerical, chemical and native review before any
adoption. Input hashes, stage receipts and retained failures define the tested
scope, separate from experimental identity validation.
