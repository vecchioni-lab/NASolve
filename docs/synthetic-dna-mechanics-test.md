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
The fresh v3 candidate below now preserves the source atom/bond/hydrogen/charge
inventory. Explicit metadata and stereochemical review, linked-site preparation
and native proxy qualification remain separate.

All **22** returned manifest entries were verified. Candidate SHA-256 is
`3049dd5b5d79e2b6961d70a87e8b2c16c793a6078f4122d824697ffda43ed27b`;
[the optimized-state evidence](elbow-optimized-state-evidence.json) records
the exact command, backend, interface result, numeric recovery, chemical
rejection and soft-review findings. Both earlier failure bundles remain
historical evidence.

### Returned v3 candidate: source inventory retained

The fresh probe `cif-generation-probe-zjzm0gk7`, candidate directory
`candidates/cif-generation-zxw2zfpz`, used the required **`--pH=low`** control
with installed-help evidence. Native eLBOW completed at **exit 0** in
**19.958581 seconds**. The candidate and probe statuses are respectively
**CANDIDATE_REVIEW** and **CANDIDATES_AWAITING_REVIEW**. The generator's actual
log reports **RM1/GDIIS**, while its CIF header says **AM1**; preserve that
provenance discrepancy and use the log for the reported execution backend.

The candidate retains all **37 exact atom IDs (23 heavy / 14 H)**, all **39
bond endpoints and normalized orders**, every explicit hydrogen attachment
including **HOP2/HOP3**, and all source formal charges (**total 0**). OP2/OP3
remain formally neutral. **C2–N3 = 1.397 ± 0.030 Å** and **C1′–N9 =
1.458 ± 0.034 Å**. Positive heavy-bond targets span **1.221–1.616 Å**.
No zero target or coincident bonded-heavy-atom defect is reported. This confirms
source-retaining whole-component generation for this exact input, while the
original failed ReadySet run remains unchanged.

Review remains visible. The output omits the source CCD atom CIP/aromatic/
bond-stereo metadata, supplies three signed sugar-chirality restraints and new
partial charges, and labels the component **`non-polymer`** where the source
declares **`DNA LINKING`**. Formal charge preservation does not imply all
metadata survived. The generated coordinate chirality signs match the source
ideal seed under the same atom ordering, but this is not native stereochemical
or polymer-link interpretation. Five **PLANE-01 REVIEW** findings remain soft
diagnostics rather than hard invalidity or instructions to force planar angle
sums. Chemical identity, native proxies and linked-site chemistry are still
unassessed.

All **22** returned manifest entries verify. Candidate SHA-256 is
`23d11d4175fc14d492004ba70a751470c43ca1ce733ca3fcd89d49f82e12cc1c`;
[the source-retention evidence](elbow-source-retention-evidence.json) owns
exact field findings and remaining gates. A separate `(2)` ZIP repeated the
old v2 runtime without `--pH=low`; its rejection is historical evidence, not
a test of v3 preservation.

Nothing has been adopted, linked, refined or scientifically approved. The next
pipeline work is explicit metadata/consumer review and site-specific linkage
preparation, followed by a fresh ReadySet/PostMR/native-proxy check. The
source-generation recovery is now demonstrated for IGU; the one-click mixed
DNA campaign has **not yet completed** through that recovery path.

### 04_Cedar repeat and the next bounded check

The user-live **`04_Cedar`** delivery passed the visible-prefix check in its
filename, build metadata and run receipt. The fresh session
`04_Cedar_cif-generation-probe-r2cunjcc` completed native generation at exit
**0** in **22.019048 seconds**, with the same embedded runtime archive as the
earlier v3 probe. All **22** manifest entries verify. Its candidate remains
**CANDIDATE_REVIEW**: every parsed CIF value and all **37** PDB atom rows match
the earlier source-retaining candidate exactly; file hashes differ because
timestamp text changed. This confirms delivery naming and repeats the same
source-state/numerical result. It adds no new chemical, linked-site or native
reader qualification. The compact repeat record lives in
[the existing source-retention evidence](elbow-source-retention-evidence.json).

The next **`05_Cedar`** diagnostic is implemented to exercise the installed native
CIF reader and model interpretation against an explicitly selected dictionary
bundle, in a fresh directory with original inputs preserved. It will capture
consumer behavior before optimizing coordinates, adapting metadata, rerunning
ReadySet or adopting a dictionary. The returned 05 inventory now completed:
42 mappings, 38 recorded intra-strand links and zero coordinate OP3/O3P,
with four generic monomers still expecting OP3. The [native ledger](native-modified-pair-live-validation.md#cedar-05-return-and-source-state-audit)
records its exact evidence. This is an inventory pass, separate from linkage
and numerical qualification.

### Cedar 06 source-preserving linked-state preparation

The selected CGY/IMC/DX ReadySet definitions lost their frozen source OP2
hydrogens. The new explicit diagnostic first uses existing CIF Doctor
comparison/generation to recover those complete source states; it reuses the
accepted IGU candidate. Per-site linkage preparation then removes only
graph-selected leaving atoms/H, retains OP2 protonation and uses source DNA
metadata. Detailed native checks compare actual monomers, backbone links and
custom pairing/stacking coverage, with a same-code internal/free-OH control.
The source-bundled `06_Cedar_probe_cif_linked.py` reads the exact returned 05
ZIP and writes a new session without changing the original run or laptop
checkout. Its returned generation stage is recorded below. Linked installed
interpretation remains **pending**. The fresh
full-auto acquisition/recovery gate is still open; no dictionary was adopted.

### Cedar 06 return and Cedar 07 representation retry

All 87 payloads in `06_Cedar_rkmjesl4_cif_linked_review.zip` verify against
their manifest. Phenix 2.2.1-6174 eLBOW completed source-retaining RM1/GDIIS
generation for IMC, CGY and DX. IMC and DX reached `CANDIDATE_REVIEW`; the v3
gate rejected CGY solely because six alternating source ring orders became
aromatic types. Every source ring bond already has an affirmative aromatic
flag; exact connectivity, hydrogens and formal charges survived. The source
recovery stop prevented all new native bundle interpretation and the
internal/free-OH control. [The evidence record](cif-linked-source-recovery-evidence.json)
owns exact commands, hashes and measured scope.

Generation-v4 recognizes only complete isolated source-declared alternating
six-member neutral C/N rings, with unchanged single-bond substituents and no
contradictory ring stereochemistry. Raw differences and all independent
rejection checks remain intact. Offline reinspection of the returned candidates
now prepares all four linked derivatives, retaining IGU/IMC HOP2, CGY H1 and
DX H14 on OP2. The original 858-atom model stays byte-identical. The next
Git-built delivery is `07_Cedar_probe_cif_linked.py`; installed interpretation,
scientific qualification and any adoption remain pending.

### Cedar 07 return and Cedar 08 native registration retry

The subsequently returned Cedar 07 capsule passes source recovery and baseline
interpretation but stops before the linked manager: the writer's shared
`data_mod_linked_sites` blocks register a colliding ID, while PHIL requests
distinct site IDs. The corrected writer uses one native block per requested
modifier and preserves every site plan, base dictionary and PHIL request in
exact offline replay. Detailed baseline atom records provide no native formal
charges; missing readback remains explicitly unqualified. The
[registration record](cif-linked-native-registration-evidence.json) owns the
164 verified payloads and replay. The subsequent Cedar 08 result follows.

### Cedar 08 return and Cedar 09 component-list metadata retry

Cedar 08 completes baseline, linked and shared-code native interpretation on
Phenix 2.2.1-6174; all 207 returned payloads verify. Requested modifier IDs,
all four site atom inventories/H adjacency/energy types, 38 backbone links and
exact custom proxy coverage agree. The synthetic free-OH IGU control preserves
the original model and demonstrates distinct internal/end definitions under
one component code. Complete qualification remains REVIEW: scalar component-
list metadata loses the declared native DNA group and formal-charge attributes
are unavailable. Native classification logs still identify DNA.

The corrected serializer retains the singleton metadata loop with unchanged
parsed values, modifier/PHIL bytes and site plans. Detailed native classification
and separate atom/group checks make the evidence boundary explicit. Cedar 09's
returned execution is recorded below. No model optimization or refinement occurred.

### Cedar 09 return: internal mechanics recorded, science reviews retained

All 207 payloads verify. Phenix 2.2.1-6174 recovers DNA group/classification at
the four internal sites: 29 checks pass, while four native formal-charge
readbacks are UNSUPPORTED. All original atoms, 38 links and exact custom
restraints survive. Overall REVIEW is retained without gate changes.

File-level charges agree for all 148 source/candidate atoms. Ordered source,
generated and native sugar-centre signs agree at all 12 centres; independent
absolute stereochemistry remains unassessed. The free-OH E:1 control has
distinct selected atoms but undetermined native classification and incomplete
O5′-OH treatment, so it is not full terminal support. The 12 projected
plane-angle reviews and actual retained 5CM C2/C2′ torsion still require review.
The next phase is dictionary/end-state and geometry review, rather than another
unchanged native inventory. No refinement, adoption or input replacement ran.

### Cedar 10 return and Cedar 11 canonical-control retry

The source-bundled probe verifies the exact returned Cedar 09 capsule,
prepares the existing source-hash-scoped 5CM correction as a separate candidate,
and records installed `5*END` parameters plus a canonical DG control in memory.
No coordinate model is supplied. All nine returned Cedar 10 payloads verify;
the native run reproduced the exact reviewed 5CM output and captured installed
Phenix 2.2.1-6174 `5*END` rows. Its direct DG lookup failed before the canonical
control because the native library uses a translated identity. Cedar 11 uses
the installed residue-name interpreter, records the resolved component ID and
keeps unavailable APIs/components unsupported. All nine returned Cedar 11
payloads verify; installed resource execution succeeds at exit zero in
0.837208 s. The canonical control gains the explicit O5′ hydroxyl hydrogen
and source targets while preserving every unaffected restraint row. Its
classification also becomes undetermined despite DNA group, so that label
alone does not diagnose a modified-end defect. The earlier missing modified
hydroxyl treatment still needs implementation. These resources support subsequent complete O5′-OH treatment
without inventing numerical targets or silently modifying the frozen run.
The probe does not implement/adopt that terminal recipe, perform another linked
inventory or start geometry minimization/refinement.

### Cedar 12 explicit terminal / reviewed 5CM bundle trial

The source-bundled Cedar 12 delivery reads the exact returned Cedar 09/11 capsules,
verifies all 207/nine payloads and reuses only declared input members. It
prepares a source-traceable 5′-OH candidate for the existing isolated IGU E:1
control, leaving internal IGU A:6 and the shared base unchanged. The explicit
5CM recipe reproduces its reviewed hash. The 877-atom, 43-site model is supplied
unchanged to baseline and candidate native interpretation; no coordinates or
H positions are added.

The new preparation uses the installed hydroxyl types and exact 0.84 ± 0.02 Å
bond, 1.02 Å neutron target and 120 ± 3° angle captured in Cedar 11. Existing
formal charges remain unchanged; new H formal charge is unknown, distinct from
native partial charge. Exact projected rows, the corrected 5CM native
torsion/alternate proxy, all 38 backbone links, custom coverage and all recorded
unaffected proxies are checked. Source/module/dispatcher hashes must match
the captured Phenix installation before and after interpretation.

A separate graph audit of declared outgoing links exposes pre-existing O3′ H
at 1AP A:5, 5CM A:7, DZ A:12 and DP B:4 in the prior return. These reviews and
unavailable native formal charge keep scientific qualification distinct from
successful interpreter execution. Returned Cedar 12 verifies all 116 payloads;
both Phenix 2.2.1-6174 interpretations complete with exit 0. Projected definitions,
the corrected 5CM torsion/alternate proxy, unselected definitions and unaffected
proxies pass. Qualification records 95 PASS, six UNSUPPORTED charge checks and
the same four outgoing-H REVIEW checks, retaining aggregate REVIEW. The
[native evidence record](cif-linked-native-registration-evidence.json) owns
exact hashes and replay evidence. No production adoption, optimization or
refinement is part of this trial.

### Cedar 13 explicit outgoing-O3 bundle trial

The source-bundled probe takes the exact returned Cedar 12 ZIP, validates all
116 payloads and materializes only declared native inputs and evidence. Every
curated source projection must match all captured native rows before a selected
change. Four explicit outgoing sites lose only their graph-identified O3′ H:
1AP A:5 `HO31`, 5CM A:7 `HO3'`, DZ A:12 `H2` and DP B:4 `H3`. Projected
dictionary atom counts become 34, 33, 33 and 33. Canonical DC A:4 supplies the
recorded OC2 oxygen type; its charge and targets are not copied.

The existing curated dictionaries, `NASnoOP3`/other modifiers, reviewed 5CM
torsion and IGU terminal/internal treatment are retained. Four additional
site-selected modifiers are interpreted against the same 877-atom, 43-site
model. The new trial requires exact captured-baseline replay, old/new modifier
IDs, projected definitions, 38 links, custom coverage, corrected 5CM proxy and
unselected definitions/unaffected proxies. Frozen inputs and installed source
hashes are checked again after execution. No coordinate edits or new targets
are part of the trial.

Offline preparation passes all 24 source/native comparisons. Existing 1AP/DP
Doctor assessments remain REVIEW. Installed Cedar 13 execution is pending;
formal-charge readback can keep aggregate REVIEW after successful interpretation.
This candidate is not production adoption or geometry/refinement qualification.

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
