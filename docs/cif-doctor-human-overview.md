# CIF Doctor: human and manuscript overview

**Implemented scope, updated 2026-10-22:** offline component/restraint assessment,
report-only PostMR integration, explicit source/candidate comparison and two
bounded preparation recipes, dictionary coordinate-degeneracy checks, and
explicit whole-component numerical candidate generation and a separate native
bundle diagnostic, explicit per-site linked-state preparation and native
qualification checks, and bounded source-declared aromatic representation
comparison. Cedar 06 completed native candidate generation and stopped at its
CGY representation gate. Cedar 08 completed linked/shared-code native
interpretation with matching site and proxy evidence. Cedar 09 recovers native
DNA metadata at all four linked sites; 29 checks pass and four formal-charge
checks remain unsupported, preserving the REVIEW verdict. Terminal chemistry
and numerical/stereochemical review remain open. The [command guide](cif-doctor.md) owns operational
details; the [implementation map](cif-restraint-doctor-implementation.json)
separates the deployed software from proposed extensions. Update this overview
and its figure whenever the feature's behavior, dependencies or claims change.

## What it does

CIF Doctor checks the instructions that tell crystallographic software how a
modified nucleotide is connected and restrained. Those instructions are stored
in component CIF dictionaries: they name atoms and bonds, and may specify ideal
bond lengths, angles, torsions, chirality and planar groups. A plausible-looking
model can still be restrained by the wrong atom reference or incompatible
targets. CIF Doctor makes these problems visible before the dictionary is used
for model construction and after ReadySet has prepared the refinement inputs.

The output is a reproducible audit with the exact input hashes, software
versions, component inventories, rule identifiers and measurements. The current
PostMR audit hooks record findings without changing coordinates, selecting new
chemistry or adding a readiness gate. Ordinary Coot construction separately uses
the connected-base restoration described below. Researchers can also assess a
frozen checkpoint without altering the run.

## Automatic decisions and reporting

The student-facing contract is automatic recovery and usable fallback, with
plain-language reporting. A bounded optimizer can miss its convergence limit
while leaving a usable dictionary; NASolve should continue and disclose that
limitation. A chemically broken alternative is excluded, and an intact native
or repaired fallback can still be used. DNA pucker changes are permitted;
stereochemical inversion is a distinct chemical change, including for ATL.

The implemented decision core preserves source authority, excludes demonstrated
unusable candidates and compares energy only for the same fixed objective.
Unknown stereo remains unknown. PostMR now stores a concise solution-report
summary alongside its detailed assessment. C55 adds an opt-in isolated native
usability-to-decision adapter; corrected replay now passes its six returned
native cases. Returned C56 verifies that replay. C57 adds source-declared DNA
metadata restoration with automatic fallback to the verified original if its
isolated native comparison fails. All six C57 native comparisons pass and all
three components select the restored header with notes. Returned C58 passes
all three separate short-chain linkage controls. Returned C59 qualifies DP in
the actual full scaffold and selects it with notes. Returned C60 retains a
usable geometry endpoint after fresh derivatives and exact native readback pass,
while reporting nonconvergence. Returned C61 passes all 15 native staged-bundle
checks for that model and its exact restraints. Returned C62 completes Coot
construction but retains three whole raw sites
because of unmatched OP3; rigid base transport is not exercised. C63 prepares
source-proven internal-phosphate context before ordinary connected-base
restoration and tests it through the same API. Unsupported raw sites remain
usable with notes. Automatic production recovery/adoption, generic NAR
compilation, production checkpoints/refinement and PDF rendering remain planned.
Development
diagnostics can retain REVIEW without asking students to inspect CIFs. See the [continuation contract](cif-doctor.md#automatic-continuation-and-student-facing-decisions).

The planned automatic workflow must save usable repairs locally and reuse them
for later matching chemistry. The repaired component dictionary is independent
of a new crystal's coordinates; site modifiers and native compatibility still
need their own checks. Each run retains exact selected bytes and inherited
notes. This persistent store is required integration work, not yet deployed.

## How it works

The assessor parses each CIF data block separately and builds an adjacency graph
from the declared atom and bond tables. Exact atom names remain distinct: `C5`
and `C5'` cannot collapse into one atom. It then applies deterministic checks:

- **Identity and connectivity:** unique atom identifiers, valid references,
  duplicate/conflicting definitions, component-ID agreement, declared bond
  orders and aromatic flags.
- **Numerical restraints:** finite targets and valid uncertainties, missing
  numerical fields, angle paths, proper-torsion paths, supported alternate
  torsions, and chirality-neighbor references.
- **Internal consistency:** whether angle targets at a shared planar center
  can represent planar directions. The test considers both interior and exterior
  angle configurations; adding every angle to 360° is not a universal rule.
- **Dictionary coordinate degeneracy:** exact coincidence of bonded heavy
  atoms in supplied numerical components. This checks dictionary coordinates,
  separately from achieved geometry in the experimental model. It catches a
  collapsed pair even if its bond target has been manually made positive.
- **Optional model correspondence:** a PDB atom inventory retains model,
  chain, residue, insertion-code and alternate-conformer identifiers. This
  detects unknown or duplicated atom identities; it does not calculate the
  model's bond lengths or infer missing site chemistry.

An explicit source/candidate comparison reports changes in atom identity,
connectivity, bond order, aromatic annotation, hydrogen attachment, declared
charges, stereochemistry and numerical restraints. It does not decide which
dictionary is chemically correct. Unspecified charge remains different from
zero, and signed-volume restraints remain distinct from absolute R/S assignment.

Graph information and numerical parameterization are assessed separately. A
valid wwPDB CCD source can describe a molecule without supplying refinement
targets. CIF Doctor records that numerical layer as unassessed in source mode;
the same omission requires review in an effective refinement dictionary.

## Where it sits in NASolve

![CIF Doctor's report-only placement around PostMR and ReadySet](figures/cif-doctor-overview.svg)

| Audit point | What is inspected | Why it matters |
| --- | --- | --- |
| Before a requested Coot mutation | Exact target construction dictionaries, preserved as audit snapshots | Construction should use atom identities and connectivity that have been inspected. |
| Immediately before ReadySet | Frozen source definitions and a separate inventory of the actual normalized runtime inputs and prepared PDB | Preserve source evidence while showing the inputs that will enter preparation. |
| After ReadySet and dictionary selection | The complete selected effective input bundle and final prepared PDB | Audit the files retained for subsequent refinement, including the existing precedence and normalization decisions. |

ReadySet remains the external model-preparation program. NASolve currently
invokes it with hydrogen addition disabled and retains its existing identity,
phosphate, parameterization and dictionary-precedence checks. CIF Doctor wraps
this preparation with evidence; it does not replace ReadySet or its ligand
generation tools. The post-ReadySet assessment describes selected files, not
the native geometry-restraint proxies constructed by Phenix.

## What tools and data it uses

| Tool or resource | Role in this feature |
| --- | --- |
| Python standard library | Graph traversal, numerical consistency calculations, hashing and JSON receipts. |
| Biopython `Bio.PDB.MMCIF2Dict` | Existing NASolve reader parses each supported CIF1 data block. A lexical preflight additionally detects duplicate tags. |
| NASolve dictionary-compatibility adapter | Inventories supported CCP4 alternate-torsion relationships; explicit preparation reuses the established normalizer. |
| NASolve checkpoint and run-context utilities | Resolve declared frozen inputs, verify hashes and retain portable provenance without changing checkpoint selection. |
| Phenix ReadySet and Coot | External PostMR preparation/construction programs surrounding the audit hooks; neither is required for a standalone dictionary assessment. |
| Phenix eLBOW, explicitly requested | Generates a separate numerical candidate from frozen chemical input and independent source ideal coordinates; never adopts it automatically. |
| Installation-bound `phenix.python`, explicitly requested | Uses installed iotbx/libtbx/mmtbx readers and monomer libraries to interpret a copied model/effective dictionary/parameter bundle and inventory the resulting atom/proxy evidence. |
| wwPDB CCD and NARestraints | CCD supplies separate source definitions; the NARestraints workbook supplies pairing roles and test-case selection. Neither is automatically promoted to authority for every chemical state. |

Standalone assessment runs locally and offline. It uses no language model,
chemical-restraint generator or new cheminformatics package. Public CCD
downloads used in testing are separate, frozen inputs; assessment itself does
not fetch a newer dictionary over the network.

Explicit `generate-candidate` is a separate native operation. It freezes the
source, creates an exact-name initial-geometry template from complete supplier
ideal coordinates, checks the installed generator's advertised options, and
requests eLBOW optimization with hydrogen addition off,
source chirality retained and its explicit input-state retention mode selected.
That mode requests retention instead of default acid-hydrogen removal; it is not an
experimental pH claim or a determination of the correct crystal protonation.
The candidate is assessed and compared with the
source, including explicit hydrogen, charge and stereochemical differences.
Missing/unrepresentable seed data, invalid targets or contradictory chemistry
remain rejected or under review. Experimental MR coordinates and previous
prepared numerical dictionaries are not used to invent replacement targets.
Logs, commands, versions, capability evidence and hashes remain in a fresh
candidate folder. A CLI incompatibility is recorded separately from a chemistry
or optimization failure; unsupported required controls stop generation.
The requested optimization option and the backend reported by the native log
are recorded separately, because installed implementations can differ.

The generation-v4 comparison recognizes complete, source-declared aromatic
representations of isolated neutral six-member C/N rings. It requires an
alternating source order pattern, affirmative flags on every ring bond,
unchanged single-bond substituents and no contradictory ring stereochemistry.
This is declaration checking, without aromaticity perception or tautomer
selection. Raw source/candidate differences remain visible and all independent
atom, hydrogen, charge and numerical checks still apply. The returned CGY
candidate supplies the native regression case; [its evidence record](cif-linked-source-recovery-evidence.json)
separates completed eLBOW generation from the pending linked interpretation.

An explicit native bundle diagnostic is the next separate operation. It freezes
the prepared model, selected CIFs and parameter files in an external folder,
then invokes the selected Phenix installation's Python and monomer library.
An opt-in, recorded namespace adapter can remove only the parsed top-level
`refinement` wrapper from NASolve parameter files; all child values and
selections are retained, and unused native parameters are reported. The
diagnostic records installed parsing, interpreted atom identities and geometry
proxy inventories without minimizing or writing replacement coordinates.
Native interpretation may normalize the internal hierarchy; original model
bytes remain separately preserved and hash-bound. Exit-zero interpretation
remains REVIEW and does not certify chemistry, expected links, custom-restraint
coverage or achieved geometry. Unsupported API layers remain visible.

The separate linked-state diagnostic reuses source comparison and candidate
generation before applying declared DNA linkage/end states. It preserves
source-specific OP2 protonation, removes leaving atoms and attached H through
bond-graph adjacency, and writes per-site modifiers rather than changing every
instance of a residue code. An opt-in native inventory records full effective
site definitions and proxy targets/weights. Checks compare exact backbone and
custom pair/stacking coverage, preserve unaffected definitions, and include a
shared-code internal/free-OH control. These are external candidate/diagnostic
operations, with no automatic adoption or PostMR recovery. Cedar 08 completed
their native linked execution, preserving exact site atoms/H/types, backbone
links and requested proxies; numerical and stereochemical reviews stay separate.

Each modifier is serialized in its own native `data_mod_<ID>` block. The
returned Cedar 07 reader registered the previous shared block name rather than
the four requested IDs and stopped before linked interpretation. Exact
returned-input replay verifies corrected registration without altering base
dictionaries, PHIL requests, deletions or site plans. Detailed native inventories
also report formal-charge readback availability: unknown native values remain
unqualified, distinct from an observed charge contradiction. Partial charges
cannot substitute for formal charges. Cedar 08 recovered the requested native
IDs and exposed a second serialization issue: single-row component-list
metadata had collapsed to scalar fields and was skipped by the reader. Native
group is null even though the interpreted classification logs identify DNA.
The writer now preserves the metadata loop; detailed readback records
classification separately, and atom/group checks remain independent required
gates. [The registration evidence](cif-linked-native-registration-evidence.json)
owns the returns, including Cedar 09's successful installed group readback.
All 29 evaluable checks pass while four unavailable charge readbacks keep the
aggregate result REVIEW. The synthetic terminal control has distinct selected
atoms but undetermined native classification and incomplete O5′-OH treatment;
complete terminal support is not established. Corrected group readback does
not certify formal charges, numerical geometry or experimental chemistry.

The source-resource diagnostic explicitly prepares the reviewed 5CM
derivative and records the installed terminal-modification parameters alongside
an in-memory canonical control requested as DG. Native residue-name translation
selects the library identity and records the requested/resolved names. The
native reader's own row fields and
numerical values are preserved with source hashes. These are sources for a
subsequent terminal recipe, with no coordinate model, invented targets or
automatic adoption. Actual returned-source replay reproduces the reviewed
5CM candidate. Cedar 10 also captured the installed terminal modification,
but its direct DG lookup bypassed PDB-to-library name translation and did not
produce the canonical control. Cedar 11 completes installed lookup and the
in-memory control, preserving all unaffected restraint rows. The canonical
5′-OH end also has undetermined classification despite retained DNA group;
that label alone does not establish a modified-end defect. The earlier missing
modified O5′ hydrogen/type treatment and unavailable native formal charges
remain separate limits. Numerical targets and qualification gates are unchanged.

The explicit modified-terminal candidate layer now transfers the captured
native hydroxyl atom types, bond and angle only to a declared free 5′ end.
It preserves the shared dictionary and other site contexts, retains existing
formal charges and marks the added H formal charge unassessed. A separate
bundle trial includes the reviewed 5CM candidate and compares complete projected
native definitions, corrected torsion/alternate proxies, unchanged model atoms,
backbone/custom restraints and all recorded unaffected proxies. Returned
Cedar 12 completes both installed interpretations and records 95 passing
checks. Six formal-charge checks remain unsupported, and a graph audit retains
O3′ hydrogens at four pre-existing internal curated sites for review. The
aggregate verdict remains REVIEW. These deterministic checks do not infer pH,
approve chemistry or minimize/refine a model.

An explicit curated outgoing-oxygen layer now addresses that bounded linkage
motif. It first proves complete source/native row agreement, then removes only
the graph-identified O3′ H/D at a declared outgoing link and uses the captured
canonical OC2 oxygen type. It preserves true free ends, existing modifiers,
all remaining targets and charges, and the coordinate model. Before/after
assessments retain existing source reviews. Cedar 13 prepares these four
candidates from the returned Cedar 12 bundle. Its returned preparation succeeds,
but installation selection stops before native interpretation; Cedar 14 corrects
that launcher default. Both Cedar 14 installed interpretations now complete;
all 141 payloads verify and qualification replay reproduces 138 passing checks
and nine unsupported formal-charge readbacks. All four outgoing-H findings
clear. Captured-baseline replay, exact modifier IDs, projected definitions and
retained definitions/proxies pass. The aggregate stays REVIEW, with charge,
source, numerical, stereochemical and achieved-geometry limits preserved.

The reusable rule selects H/D by element and bond graph at an explicitly
declared link. Tests use synthetic `ZZZ`, misleading names, deuterium and true
free ends, and preserve OP2 H and terminal phosphate. Unknown motifs or missing
authority require review. This supports the declared linkage motif; the
experiment's hash-bound runner and source-specific 5CM correction do not
establish arbitrary-component production support.

A separate captured-geometry diagnostic measures Cartesian simple-bond
distances, angles and ordered chirality volumes against the recorded native
targets. It validates identities, indices and coordinate correspondence before
measuring, retains missing/zero-weight and degenerate cases, and preserves all
source inputs. Its nominal weighted deviations are descriptive rankings; the
capture does not retain all symmetry/slack/top-out conventions needed for
native residuals. Pucker, absolute stereochemistry and other proxy categories
remain unassessed. The explicit Cedar 15 runner performs this review on the
verified Cedar 14 bundle without new native execution or coordinate changes;
successful analysis retains REVIEW. It is separate from production PostMR and
complete geometry qualification.

The returned Cedar 15 capsule verifies all 51 payloads and the preserved native
capture. Its large bond/angle deviations include a DX bond at 5.13 Å against a
1.215 Å target; the declared dictionary coordinates match that target closely.
All 858 atomic identities shared with Cedar 05 retain exactly the same model
coordinates. These comparisons expose existing coordinate distortions and
motivate a construction/atom-correspondence provenance audit. They do not
identify the responsible construction step, justify target retuning or turn
ordered chirality sign agreement into absolute stereochemical approval.

The explicit construction-provenance layer now freezes original stage models
under a reviewed model hash. It parses saved Coot artifact declarations without
executing the script and compares captured intramonomer geometry findings
across exact atom identities in available single-model PDB stages. Missing
stages cannot prove a transition. Same-name parent-coordinate matches are
descriptive evidence rather than a semantic atom map or proof of cause. The
Cedar 16 return verifies all 74 payloads and locates 55 raw→restored crossings.
Controlled replay of the legacy restoration reproduces the entire damaged
restored model byte for byte. This demonstrates that coordinate copying is
the damaging operation for these transitions, without explaining every
pre-existing raw/MR defect or proving source chemistry.

The separate Cedar 17 candidate addresses that mechanism by transporting a
complete connected base fragment from raw Coot into the preserved sugar frame,
using a proper rigid rotation/translation at C1′/O4′/C2′. Connectivity selects
the base and its single C1′ attachment; parent base names supply no coordinates.
The rule requires the complete explicit DNA scaffold and preserves all
backbone/unselected coordinates and metadata. Unsupported graphs and contexts
are refused. DF's effective aromatic sugar bonds remain visible and its site unchanged;
eight supported contexts move 84 base atoms. Captured-proxy prediction changes
bond/angle outlier counts 50/107→34/72, with zero recorded chirality sign
conflicts. This preserves raw fragment geometry within PDB rounding; it does
not optimize or approve it. The runner tests unchanged native definitions,
targets, detailed proxies and exact candidate coordinates using the selected
Phenix installation. Generic regressions, the complete suite and actual-input
relocation pass. Returned Cedar 17 verifies all 129 payloads and 14 native
mechanics checks. Native/predicted measurements agree within computed roundoff.
Intrasite improvements do not establish a sound pairing pose: CGY–DX contacts
include 9.357476 and 6.818964 Å versus 2.8 Å targets, and the latter worsens
from 2.947120 Å. These outcomes remain visible alongside lower total outliers.

Cedar 18 separates effective/source recovery from further coordinate changes.
A graph rule requires an unsupported effective scaffold, an exact recorded
original source hash and a supported source DNA graph. DF's source sugar bonds
are single; its effective aromatic declarations are not copied into the source.
Existing whole-component generation retains source atoms/H/bonds/formal charges
and stereochemistry, then linked/native projection checks run at fixed model
coordinates. Only passing mechanics and the explicit unavailable charge API
can continue to a separate fragment restoration/native check. Definition and
coordinate effects are reported separately; unlike objectives are not ranked
as like-for-like geometry improvements. Returned Cedar 18 verifies independent
generation, 68 passing dictionary checks/one unavailable charge readback and 14
fragment checks. The linked files and nine-atom DF candidate replay byte for byte;
raw base geometry and the unresolved CGY–DX pose remain visible.

A separate Cedar 19 diagnostic reconstructs and exactly matches that captured
manager before one bounded geometry-only L-BFGS trial with fixed definitions.
Native per-term energy and gradients, actual stopping/limits/errors, symmetry
and installed optimizer hashes are recorded. Full-precision endpoints remain
separate from PDB rounding, per-site displacement and a new exact native proxy
postcheck. A target decrease, limit stop or tolerated rounding error cannot
establish convergence or scientific approval. This local trial uses no diffraction
input and makes no automatic choice; source/charge, absolute stereochemistry,
pucker, separate contact/clash inventory, pose and full qualification stay under
review. Returned Cedar 19 completes 500 iterations with fixed constraint
signatures and a lower target, but reaches the cap with its native criterion
false. Serialization then exposes native/PDB atom-order differences. The
corrected serializer uses a checked identity bijection and preserves PDB record
order/metadata. Cedar 20 resumes its saved endpoints without another optimization;
its returned native PDB check preserves identities/definitions and adds five
hydrogen bonds/ten angles as contacts cross an unchanged distance cutoff. The
old exact comparison retains 11 PASS/three REVIEW. A read-only audit explains
that pattern separately from the saved fixed-manager PDB endpoint equivalence;
neither report changes the original checks or claims chemical approval. Explicit
hydrogen-bond membership, convergence, full qualification, production integration
and adoption remain separate.

The accepted project policy makes NARestraints' pair selections, stacking
relationships, mapped base planes and recipe targets authoritative over Phenix's
automatic secondary-structure guesses.
The separate membership compiler reuses NARestraints' recipe and stacking
builders, preserving frozen selection provenance. It compiles declared intent
without rerunning the guesser on moved coordinates. Intended contacts must
survive poor starting geometry, and Phenix inference must not add competing
terms. Run continuity can rescue weak pairing geometry; chemistry, overlap and
achieved-geometry checks remain necessary. The diagnostic compiler is
implemented and passes both returned native membership checks; geometry
qualification remains open.

Stacking reuses the existing NARestraints base-class plane mapping and
neighbour builder. Its canonical native declarations and explicit modified-base
parallelities both carry that policy; suppressing competing inference must
preserve their requested relationships. Unknown-mapping warnings and actual
native coverage remain visible, with stacks distinguished from base-pair planes.

A separate **explicit NARestraints membership diagnostic** now compiles the
remaining generic pair/stack declarations before disabling competing native
secondary-structure construction. Existing explicit modified-base edits and
component modifiers remain intact. It resolves workbook-mapped atoms and planes,
checks duplicate requests, and records the source of each relationship. Cedar
21 applies that same policy to the preserved initial model and saved endpoints,
checking exact native requests, targets/weights and unaffected proxies. The
installed origin registry is recorded rather than assumed. Offline compilation
and synthetic transport are verified. Both returned Phenix 2.2.1-6174 cases pass
14/14 exact membership checks, retaining all 52 explicit bonds, 86 angles, eight
planes and 58 parallelities with no competing SS-origin terms. All captured
static proxy rows remain identical across the saved coordinates.
This is a new explicit objective, with no coordinate editing or minimization.

The separate Cedar 22 diagnostic now tests one bounded geometry trial under
that verified policy. It starts from the saved endpoint, preserves all source
dictionaries and compiled restraint inputs, and checks the exact manager before
optimization. Stopping, gradients, displacement and full-precision versus PDB
rounding evidence stay separate. A fresh native reread must preserve identities,
definitions, all static proxies and the NARestraints policy. The returned trial
passes all 17 native mechanics checks, lowers the objective by 24.26% and stops
with a line-search error at 905 iterations. Three long CGY–DX hydrogen-bond
distances and ten angle outliers remain, with no recorded chirality sign
conflicts. This verifies consumer mechanics through actual coordinate movement;
convergence and complete chemistry/geometry remain under review.

Cedar 23 now prepares a separate numerical check of those saved coordinates.
It compares native gradients with small central energy differences at several
step sizes, alongside category controls, repeated evaluations and the existing
dictionary checks. Exact manager/policy/source matching remains mandatory.
No minimizer runs, coordinates or targets are edited, or model is adopted.
The check can localize sampled numerical inconsistencies; it cannot establish
convergence or chemical correctness. Returned Cedar 23 verifies all inputs
and localizes stable sampled derivative disagreement to native parallelity,
the plane-orientation term used by declared pairing/stacking restraints.
The other six category controls pass every sampled direction at both
precisions. Independent plane-energy/derivative calculations reproduce the
finite differences, while the public CCTBX accumulation-loop bounds reproduce
the saved native gradient to numerical precision. This strongly indicates
omitted second-plane gradient contributions, subsequently reproduced in
the installed Cedar 24 check below. This does not reject the NARestraints
policy or prove the cause of the optimizer stall.

Cedar 24 now supplies a separate installed diagnostic to distinguish an
individual plane derivative from failure to add all atom contributions. It
checks every captured plane at both saved precisions and both plane orders,
with tilted equal/unequal-size controls. It preserves the NARestraints policy
and performs no optimization. The returned audit confirms an installed
accumulation defect: every sampled individual-restraint direction agrees,
while every accumulated order loses second-plane contributions. The same
pattern occurs for tilted controls, independently of residue chemistry.
The installed loop-bound model reproduces the returned accumulation arrays
exactly. Restoring complete contributions in saved data explains all earlier
sampled discrepancies.

Cedar 25 now implements an explicit NASolve-local correction. It keeps the
native energy, replaces only the incomplete plane-gradient contribution with
the complete sum, and leaves all NARestraints selections and chemical targets
fixed. A separate audit freshly compares derivatives with energy differences
at the initial coordinates and both saved endpoints. It checks the same native
sources and mechanics before evaluating; no optimizer runs or installed Phenix
file is edited. Returned Cedar 25 passes both endpoints and retains six
initial-coordinate failures. An independent normal-orientation sign model
reproduces the remaining gradient; four ordinary stacks exercise that branch.
Cedar 26 therefore uses each plane's first-plane derivative by evaluating both
orders. Fresh checks cover every plane, all three coordinate sets and rigidly
rotated controls. Returned Cedar 26 passes all 504 global/category and 1,080
corrected per-plane directions with zero native energy change. This clears the
sampled derivative prerequisite for a separate bounded geometry trial.

Cedar 27 now supplies that trial, restarting from the same original initial
coordinates as the earlier stalled run. The exact qualified correction and
initial gradient must match before optimization. Fresh endpoint derivatives,
stopping evidence and native PDB mechanics are reported independently. The
returned trial passes all 17 mechanics checks and all 336 sampled endpoint
directions. Its target falls 28.72% but reaches the 1,000-iteration limit with
the native criterion false. Accepted steps still lower the target at the end;
Cedar 28 supplies a bounded continuation from saved full precision, after a
fresh match of the entire starting corrected gradient and target.
Returned Cedar 28 passes the same mechanics/derivative checks and decreases
the target another 3.64%. The 2,000 cumulative iterations still end at the
limit; the same strained pair/DP angle remains, and chemical qualification is
open. Cedar 29 supplies a separate graph-selected base-orientation audit to
measure the response of the same fixed objective to temporary rigid-base
rotations. Source/endpoint matching, fresh rotational derivatives, periodic
controls and exact angle/plane context accompany the scan. Returned native
execution passes all 96 sampled rotation directions; no independent coarse
sample improves the objective. Cedar 30 separately prepares a source-graph
numerical candidate for the retained DP conflict. Cedar 30 stops before
generation on external coordinate-tag spelling; Cedar 31 fixes serialization
and adds PDU as a separate public chemistry/policy control. Returned Cedar 31
finds missing DP alias metadata and a distinct PDU optimizer/restart crash,
with no output dictionaries. Cedar 32 adds a general alias-column fallback and
installed-source/read-only input checks. Returned Cedar 32 passes PDU and
identifies DP's broader reader-dialect mismatch. Cedar 33 supplies a checked
format projection and a bounded candidate trial after installed option/source
proof, retaining nonconvergence evidence. Its return separates preparatory DP
chirality failure from a nonconverged PDU dictionary. Cedar 34 audits saved stereo
and printed energy evidence plus isolated native reader controls, without new
generation. Numerical and scientific qualification
remain open; no candidate is applied to a model.
All diagnostic policies are opt-in; production defaults are unchanged.

An [offline ZIP shuttle](cif-doctor.md#offline-runner-for-the-public-control-zip)
packages the exact assessor and required reader code into one Python script.
It verifies the frozen public-control ZIP and writes new audits without an
installed NASolve checkout. Screening the same CCD sources in effective mode
tests numerical completeness; it does not run ReadySet or generate restraints.

## What the findings mean

`PASS` means that the implemented invariants passed. `REVIEW` identifies a
conflict or incomplete evidence requiring interpretation. `INVALID` identifies
a failure of the implemented checks. `UNASSESSED`, `NOT_RUN` and `UNSUPPORTED`
make missing coverage explicit at the relevant assessment layer or finding.
None of these labels alone constitutes chemical or crystallographic approval.

Two explicit preparation recipes can write a new candidate while preserving
the source. One normalizes supported alternate-torsion representations. The
other applies the single reviewed historical 5CM `C2` → `C2'` torsion-reference
correction, only when the source has the exact reviewed SHA-256, then runs the
same normalizer. Preparation records field-level differences and before/after
assessments, refuses existing destinations and does not automatically adopt
the candidate. This is a bounded repair capability, not a general atom-name or
bond-order fixer.

The first implementation has automated regression coverage, frozen public CCD
controls and historical dictionary replays. These establish offline behavior
and input preservation. They are separate from the earlier bespoke native
5CM/DF/DP diagnostics and do not establish a native Phenix/Coot validation of
the new general assessor. Exact counts and hashes belong in the
[development handoff](development-handoff.md) and
[public control manifest](cif-doctor-ccd-controls.json).

The fresh mixed-DNA test supplied a native regression case: IGU's generated
C2–N3 target was zero and both dictionary atoms had identical coordinates;
nearby targets were also distorted. The generalized PostMR guard quarantines
invalid generated generic components and identifies the actual failing atoms.
An explicit regeneration probe completed eLBOW optimization and restored the
C2–N3 target to 1.387 Å. It also exposed a separate default-state change:
phosphate hydrogens disappeared and formal charges changed, so the candidate
was rejected. The v3 native probe then retained all 37 atoms, hydrogen
attachments, bond orders and formal charges using explicit source-state
retention. Its C2–N3 target is 1.397 Å. Five small plane-angle discrepancies
remain REVIEW findings. Source CIP/aromatic metadata is omitted by the generator,
which still labels the candidate non-polymer; native linked-site qualification
remains pending. These limits are recorded without promoting the candidate to
chemical approval. Candidate generation,
source-state preservation and native linked-site qualification are separate
gates; their pending status is recorded in the
[synthetic test descriptor](synthetic-dna-mechanics-test.md).
Shuttle filenames now begin with a short delivery identifier, also printed in
the console and retained in receipts; review ZIPs include the run token near
the front so clipped filenames remain distinguishable.

## Current limits and planned extensions

CIF Doctor inventories declared chemistry; it does not infer valence,
protonation, tautomer choice, absolute stereochemistry or phosphate termination
from a residue label. Explicit diagnostic preparation uses declared linkage
and end states; current production PostMR does not adopt these derivatives.
Installed linked execution is now recorded, with native formal-charge readback
still unsupported. Complete synthetic free-OH end chemistry is not qualified.
The dictionary assessment layer does not calculate
achieved coordinate geometry or sugar pucker, assess maps, or repair/stitch
fractured assembly arms. Plane-angle discrepancies include raw measurements
and uncertainty-based lower bounds, but a material-strain threshold has not
been calibrated.
The separate captured Cartesian diagnostic provides limited coordinate
measurements; it does not complete the broader geometry qualification above.

The proposed next layers are completion of qualification and integration of
the explicit linked-state diagnostic, mapped chemical
descriptors, qualified automatic candidate adoption and model geometry/connectivity
assessment. Guided sticky-end stitching would require declared strand routing,
symmetry and terminal intent, with a new child checkpoint. These are planned
capabilities. The existing `refine-doctor` remains the separate data/Free-R and
refinement-strategy diagnostic tool.

## Methods paragraph for adaptation

> Component dictionaries were assessed using CIF Doctor, a deterministic audit
> layer in NASolve. Supported CIF1 data blocks were parsed with Biopython
> MMCIF2Dict, retaining exact atom identifiers and declared connectivity.
> Checks covered atom and restraint references, duplicate or conflicting
> declarations, numerical completeness, torsion and chirality references, and
> compatibility between angle targets and shared planar groups. PostMR recorded
> audits before requested Coot mutations, immediately before Phenix ReadySet,
> and after selection of the effective refinement dictionary bundle. Receipts
> bound findings to ordered input SHA-256 hashes and software versions.
> Assessment was report-only and did not alter model coordinates or automatically
> replace dictionaries. Native restraint-proxy interpretation, achieved model
> geometry and experimental validation remained outside this assessment layer.

Replace the software-version/commit citation with the exact version used for
the manuscript's runs. Mention preparation recipes only if they were actually
used, naming the recipe and candidate/source hashes. Describe any subsequent
native or experimental validation separately.

## Figure files and caption

The [SVG](figures/cif-doctor-overview.svg) contains editable text and vector
objects. The [Python source](figures/build_cif_doctor_overview.py) regenerates the
layout using the standard library. [Figure editing notes](figures/README.md)
explain export and maintenance.

**Suggested caption:** Placement of CIF Doctor in NASolve's PostMR workflow.
Solid arrows indicate the existing model-preparation path; dashed arrows
indicate read-only audits of exact construction sources, frozen source/runtime
inputs and the selected effective restraint bundle. ReadySet remains the
external preparation program. Hash-bound JSON receipts preserve audit findings
without changing coordinates, dictionary precedence or readiness decisions.
The figure depicts the implemented assessment layer and notes separate linked
candidate/native-proxy diagnostics. A separate fixed-definition geometry trial
records numerical stopping/gradient and PDB round-trip evidence. Native
optimization reaches its explicit limit; saved-endpoint serialization by atom
identity and fresh native proxy generation are assessed separately. A read-only
reload audit keeps conditional-restraint differences visible without passing
the original exact comparison. Automatic adoption, full geometry qualification
and assembly stitching remain future extensions.
Dictionary coordinate-degeneracy checks and the explicit candidate-generation
scope are included; candidate generation does not add an automatic adoption path.
Explicit generation records installed-tool capability evidence before chemistry.
It requests source-state retention and preserves soft numerical reviews without
granting chemical approval. The v3 diagnostic demonstrated atom/bond/H/formal-charge
retention; generation-v4 additionally checks bounded source-declared aromatic
ring representations while preserving raw differences. Omitted metadata and
native-link qualification remain explicit.
Modifiers use exact native block IDs and component-list metadata retains its
loop layout. Native classification is separate from group metadata;
unavailable formal-charge readback is
reported independently and does not become a chemical pass.
Returned Cedar 09 interpretation records 29 evaluable checks passing, with four
charge readbacks unsupported. Source-coordinate sugar-sign agreement and
file-level charge retention are separate from independent stereochemistry,
complete terminal chemistry and achieved model geometry.
An explicit terminal-source review records installed modification parameters,
native canonical-name resolution and a separate reviewed 5CM derivative before
any new terminal adaptation or geometry trial.
The completed installed canonical hydroxyl control preserves unrelated targets;
its undetermined classification is recorded separately from formal-charge
availability and incomplete modified-end treatment.
The subsequent explicit candidate layer uses those captured parameters at one
selected free end. Its completed installed bundle trial verifies exact projected
definitions, reviewed torsion/alternate targets and unaffected native proxies.
Six unavailable charge readbacks and four existing curated O3′-H findings
retain REVIEW. The new H formal charge stays unassessed.
For the separate outgoing-oxygen candidates, complete captured source/native
row comparisons precede graph-selected H/D removal and canonical type transfer.
Source dictionaries and prior modifiers remain unchanged; exact projected
definitions, all unselected definitions, unaffected proxies and modifier IDs are then
checked in a separate native trial. Returned Cedar 14 passes these checks
and clears all four outgoing-H findings; its aggregate REVIEW retains nine
unsupported charge readbacks and separate source/geometry limits. The rule
uses declared links and H/D connectivity, with synthetic-name/free-end
regressions; the experiment remains hash-bound. Existing source reviews are
retained, without inferred targets or pH.
The separate captured Cartesian review measures distances, angles and ordered
volumes from recorded manager sites. Nominal weighted deviations rank the
evidence; missing native conventions and deferred geometry remain unassessed,
and no coordinate repair, target retuning or qualification pass is implied.
Returned source-versus-model and coordinate-lineage comparisons motivate an
earlier construction/atom-correspondence audit. The returned stage evidence
and controlled legacy replay now reproduce the damaging coordinate-copy step
for the captured transitions; other MR/raw/source defects remain unresolved.
An explicit construction-provenance diagnostic can freeze original models and
saved declarations under a reviewed run binding, then compare available stage
coordinates. Missing evidence and correspondence limits remain visible; it
does not execute the saved script or alter the original run.
An explicit attached-fragment candidate retains the reviewed scaffold and uses
the captured graph to select a connected base with one C1′ attachment. Raw
base coordinates move together through right-handed sugar frames. Unsupported
graphs stay unchanged under review. Native comparison requires the same atom
identities, site definitions, custom requests and full proxy targets/weights;
neither descriptive outlier reductions nor successful interpretation approve
complete geometry. The candidate is not integrated into production PostMR.
Returned evidence retains worsened intersite contacts alongside improved
intrasite geometry. A separate source/effective recovery requires exact source
hashes, whole-component generation and linked/native projection gates at fixed
coordinates before a fragment trial; it infers no replacement targets from
residual strain. A further explicit geometry-only trial uses the same native
manager and flags before/after, records numerical stopping/gradient evidence
and preserves full-precision results separately from PDB round-trip checks.
It remains a separate candidate; no scientific/adoption pass follows from a
smaller objective or successful execution. Identity-based serialization
preserves original PDB ordering even when native hierarchy order differs;
verified saved endpoints can continue to a native PDB check without another
minimization. Fresh native managers can activate distance-filtered hydrogen
bonds at changed coordinates. Attribution retains the changed proxy set and
original REVIEW alongside a separate fixed-manager endpoint comparison.
The separate native diagnostic inventories interpreted atoms/proxies and
parameter handling; it does not authorize adoption.
A separate explicit NARestraints pair/stack compiler now precedes a two-coordinate
native mechanics check; existing edits survive and both returned cases pass
exact membership checks. Geometry/convergence qualification remains open.
Cedar 22 extends the fixed-definition engine with opt-in native policy matching
for a separate bounded trial and 17-check native PDB readback. It reuses the
verified compiled inputs rather than selecting contacts again after movement.
Returned native mechanics pass, while the optimizer's line-search error and
remaining pairing/local-angle strain preserve scientific REVIEW.
Cedar 23 adds bounded directional finite differences at saved full-precision
and rounded coordinates, with isolated category, repeat and additivity controls.
It reuses CIF Doctor's planar-angle rule and generic distance-group reporting;
the fixed policy and all exact native gates remain unchanged. Its returned
parallelity mismatch is independently checked using centered scatter matrices,
smallest-eigenvector plane normals and spectral derivatives of
`sum(weight * (1 - abs(dot(n_i, n_j))))` for the captured zero-target,
zero-slack, non-top-out proxies. Both energies agree within 6e-12; selected
central derivatives agree within 1.2e-6. A model of the public CCTBX second-plane
accumulation-loop bounds matches all 2,631 stored gradient components per case
to approximately 1.5e-12 in norm. Installed C++ source identity and native
reproduction are subsequently recorded by Cedar 24. Exact source/blob identities, scope and
limits are in the native ledger; this is numerical evidence, not a new
optimization or chemistry approval. Cedar 24 compares the installed
per-restraint Cartesian derivatives with identity-scattered sums, native
singleton/full containers and the saved manager. Complete repeated arrays,
plane-order invariance, four-step numerical derivatives and tilted equal/unequal
controls retain the distinction between derivative and accumulation errors.
Available installed header/binding sources are captured with checksums while
remaining distinct from binary build provenance. The returned audit verifies
732 payloads and 2,856 finite-difference sample records: all 714 sampled
single-restraint directions pass, and all 238 accumulation orders fail their
second-plane and alternating controls. The installed loop-bound model matches
the accumulation vectors exactly. Algebraically replacing only parallelity
contributions makes all 84 prior full/parallelity directional checks agree
at unchanged energies and coordinates. This explains the sampled mismatch
without validating optimizer convergence or chemical definitions. Cedar 25
implements a local evaluation adapter that subtracts only the native accumulated
parallelity gradient and scatters all original single-restraint contributions
by atom index, including shared atoms. It preserves the unnormalized native
energy and works unchanged when native accumulation already agrees. The new
source-pinned diagnostic repeats the four-step finite differences under the
full objective and seven category controls at initial and both saved coordinate
sets, preserving raw snapshots separately from corrected gradients. Repeat and
additivity checks, exact static constraints and complete plane residual
agreement remain mandatory. Symmetry-bearing planes and special positions are
unsupported. Local tests use independent analytic oracles and explicit native
API fakes. The returned 794-payload audit matches all source/mechanics gates
and completes 4,101 evaluations with zero energy change: 498/504 sampled
directions agree, with six initial-coordinate failures in the full and plane
categories. A model of the header's omitted chain-rule sign after normal
alignment reproduces the stored initial gradient within 3e-12 in norm.
Spectral recombination explains all six failures at unchanged energy samples;
this is offline inference rather than a newly corrected native evaluation.

Cedar 26 takes the native first-plane gradient in the original order and for a
parameter-preserving swapped copy, then scatters both by original atom index.
Every original/copied target and residual is checked; the manager's proxies,
other gradient contributions and full energy remain fixed. Fresh derivative
checks compare original complete and corrected gradients for every plane at
all three coordinate sets in both orders. Equal/unequal tilted controls also
receive a 30-degree rigid rotation, testing energy invariance and covariant
gradient rotation across the native normal-sign branch. The same four-step
criteria and exact source/mechanics gates apply. The returned 857-payload audit
passes every corrected sampled direction while preserving all native complete
gradient failures: eight initial orders and six rotated control orders require
review. The corrected gradient is invariant under order and covariant under
rotation, with zero native energy change. This qualifies sampled derivatives
for the captured supported profile and does not establish chemical correctness.

Cedar 27 passes that evidence explicitly to the bounded geometry engine. It
recomputes the stored derivative comparisons, requires the identical correction
source, and matches the full corrected initial gradient, native sources and
static constraints before native L-BFGS starts. The same initial coordinates,
energy, compiled NARestraints policy and default bounds as Cedar 22 support a
controlled comparison. Accepted-step/stopping evidence and corrected versus raw
gradient norms are preserved. Fresh four-step endpoint checks cover the full
objective and seven category controls at full and PDB-rounded precision. Exact
atom identity mapping preserves noncoordinate PDB records, followed by fresh
17-check fixed-policy native readback. Stopping, derivatives, mechanics and
scientific qualification remain separate outcomes. The returned 980-payload
capsule verifies all 17 native mechanics checks and all 336 sampled endpoint
directions. The target decreases from 3784.7499 to 2697.7623 and the corrected
norm from 1110.5207 to 372.5374, but the native criterion is false after 1,000
iterations / 1,028 calls. The stop remains NOT_CONVERGED_LIMIT. Every accepted
target decreases; the last 100 transitions lower it by 31.2321. The rounded
fixed-manager target/norm are separately 2700.8561 / 905.6215. Three distance
and ten angle outliers remain at nominal deviation at least five, with no
sign conflicts among 158 captured chirality proxies. A future continuation
must start from saved full precision, freshly match the entire corrected
start vector and fixed source/proxy identities, and repeat endpoint derivative
and PDB mechanics checks. Cedar 28 now supplies that opt-in continuation,
with a fresh L-BFGS history and at most 1,000 further iterations / 20,000 calls.
Its worker verifies the original manager before loading the saved native
atom-order coordinates, then matches the complete corrected start vector and
target. Prior/new stopping and cumulative optimizer counts remain separate.
The returned 1,104-payload capsule verifies all 980 prior payloads and their
manifest, all 17 mechanics checks and all 336 sampled endpoint directions.
The new target/norm are 2599.5276 / 144.1650, reductions of 3.64% / 61.30%
from the prior full-precision endpoint. The additional 1,000 iterations / 1,036
calls retain NOT_CONVERGED_LIMIT, with the native criterion false; cumulative
counts are 2,000 / 2,064. All accepted targets decrease, including 8.7054 in
the final 100 iterations. The PDB-rounded target/norm are separately
2602.9712 / 950.9056. Three distance and ten angle outliers persist, with no
recorded chirality sign conflicts. Review the remaining exact terms/source
definitions and numerical tail before choosing another bounded test; no next
delivery is prepared. No target tuning, diffraction refinement or adoption
occurs.

## Temporary base-orientation diagnostic

Cedar 29 asks which fixed restraint families resist or favor a base rotation.
The generic rule selects sites from measured nominal bond/angle outliers and
follows each supported component graph to its single attached base. Proper
rotations around the C1-prime/attachment axis keep the sugar/backbone and all
internal base geometry fixed. Each of nine predefined angles is a separate
temporary energy evaluation; no preferred model is selected or written.

The exact qualified original manager and complete initial/endpoint family
gradients must match before the scan. Full and PDB-rounded endpoints remain
separate. The full native objective and isolated category controls expose
opposing rotational slopes; the slope is the sum of each atom's Cartesian
gradient dotted with its angular displacement tangent. Four fresh numerical
steps test every full-objective angular sample and each family at zero angle.
Repeated baselines, category additivity, 180-degree periodic agreement, rigid
distance preservation and native source/static identity checks retain their
own outcomes. Selected angle rows/types and common planes give the source
context for internal discrepancies that a rigid-base scan cannot repair.

This is a bounded diagnostic: at most six supported groups and 3,000 native
energy evaluations, with a 1,200-second default timeout. A low grid value is
neither an optimum nor a chemically validated candidate. Coupled backbone/base
motions, complete geometry, pucker, charge, absolute stereochemistry and
experimental fit remain separate. The implemented source transport and tests
pass. The returned installed audit verifies all 1,173 payloads and all 96
sampled rotational directions. Every independent coarse grid favors the
starting angle; validated nonzero slopes remain, so no minimum is claimed.
Ordinary PostMR is unchanged.

### Separate numerical recovery from a source contradiction

Cedar 30 addresses the retained DP angle/plane disagreement through independent
whole-component generation. The general selector uses a declared restraint
conflict, with explicit component selection for this reviewed experiment. It
does not derive replacement targets from the distorted model. The exact source
atoms, bond state, explicit H/charges and signed chirality are exported into a
graph-only input; old energy types and numerical targets remain in the frozen
original. Source coordinates supply only naming/starting geometry, with their
origin stated explicitly rather than treated as independent ideal validation.

The existing guarded eLBOW adapter generates a separate numerical dictionary.
Chemical and numerical comparisons against both the graph input and original
source retain every discrepancy; complete formal-charge declarations must
survive. A candidate is not installed or combined with existing modifiers in
this slice. Native proxy qualification, achieved geometry, convergence and
scientific approval remain separate. The Cedar 30 return identifies an input
parser incompatibility before any candidate exists: eLBOW accesses mixed-case
CCD coordinate attributes. Canonical external tag spelling now preserves the
same parsed coordinates/chemistry and is covered at that consumer boundary.
This methods step is reusable for explicitly selected graph-valid source conflicts;
the DP-specific delivery and prior positive bespoke trial are evidence, not a
universal correction rule.

### Additional T-derivative control: PDU

PDU is 5-propynyl-deoxyuridine. The pinned public CCD source preserves its full
C5 substituent, including a carbon-carbon triple bond, and the declared sugar,
H and phosphate state. It is a graph description rather than a complete
numerical refinement dictionary. The existing NARestraints T-role mapping
resolves its AT contact atoms and stacking plane; the C7 role selects C5A.
Source-atom and bidirectional stacking compiler checks pass. The apparent H2
name on the O3-prime hydrogen is handled by connectivity, not a naming guess.

Cedar 31 tests that source independently alongside the DP retry. The public
fixture is a test input, not an installed curated dictionary or a new scaffold
site. Synthetic canonical partner roles test compiler selections only, with
no experimental pairing inference. The installed return reads all 38 PDU
atoms, 39 bonds and the R/S/R sugar centres, then runs RM1/GDIIS. It reports
nonconvergence before failing on an empty XYZ restart file; no numerical
dictionary is produced. This is an execution failure, not a chemical rejection.

Cedar 32 separates the two boundaries. Missing optional alias columns use exact
primary atom IDs as naming metadata, without overwriting declared aliases or
changing chemistry. A separate installed-source capture and read-only input
check records the reader/optimizer contract before another optimization.
Captured code is inspected as text and never executed or patched. A successful
read-only check proves only that CLI input path, not generated geometry, native
interpretation or scientific qualification. The returned check passes PDU; DP
requires legacy restraint-field names to be expressed in the CCD reader dialect.

Cedar 33 adds a separate consumer projection. It translates declared bond
orders/flags and charge aliases, keeps missing atom aromatic/CIP values unknown,
and preserves the signed chiral volumes. PDU's already complete input is byte
identical. A fresh read-only check gates each numerical generation. The captured
optimizer source exposes a failing default macro restart on an empty XYZ file.
An explicit step count bypasses that restart condition; the installed options
parser must confirm one effective 180-step block, with its default tolerance
unchanged. Source/options hashes are checked before and after the trial.

A generated file or zero exit status never establishes convergence. Explicit
nonconvergence is recorded, other unreported stopping stays unreported, and
candidates retain every original-source chemistry/numerical review. No native
dictionary, policy change or scaffold result is adopted by this experiment.

The Cedar 33 return passes both readers, then stops DP in preparatory chirality
handling before optimization. The captured reader assigns every stereo token
other than N to a native chirality marker, including ?. All 35 DP atom tokens
are unknown; the original four signed-volume declarations remain separate.
This is evidence of a transport-semantics problem, not permission to relabel
unknown atoms as nonchiral or infer R/S values from an experimental model.

PDU writes a dictionary after 181 logged evaluations, explicitly without
convergence. Its exact graph, propynyl triple bond and complete formal charges
survive. R/S atom labels disappear, but all three generated signed sugar terms
agree with both the source ideal coordinates and generated coordinates. These
determinants compare handedness in the same ordered atom neighborhoods; they
do not independently assign absolute CIP configurations. The printed energy
trace rises by 40.1883 between rows 146 and 147; endpoint files do not locate a
cause or establish an optimum.

Cedar 34 is a separate read-only stereo diagnostic. It verifies the full return,
replays source/candidate chemical checks and measures signed coordinate volumes
without changing either file. A bounded installed-reader control records actual
atom markers and exercises that reader's own chirals=True constructor, capturing
the three additional molecule/topology/chirality modules as non-importable text. This isolated entry
point is not a replay of the full builder. Native sources, snapshots, dispatcher
and frozen inputs are checked before and after. Constructor exceptions remain
evidence. No whole-molecule trial, dictionary writer, pickle, model change or adoption is
requested. Constructor-local template operations are described below. Missing metadata, absolute stereo, convergence and native dictionary
qualification remain distinct open gates.

Returned Cedar 34 reproduces the DP assertion with all 35 unknown tokens marked
as native chirality; PDU retains its three known markers and completes the
constructor. There is a scope correction: native Chiralise internally calls
ChiralClass.Optimise on local templates. The earlier NOT_RUN flag meant no
explicit whole-molecule trial and did not instrument those internal operations.
No saved source, candidate or crystal model changed.

The original DP source is a monomer restraint dictionary with a comp_list block.
The graph-only export removed that block, which directs the installed dispatcher
into the CCD path. Preserving the source's reader dialect avoids inventing
nonchiral or R/S atom declarations to satisfy that different input contract.
Cedar 35 restores the explicit list layout and exact coordinate aliases in a
separate target-free input; signed volumes and chemical declarations survive.
PDU keeps its original CCD route and byte-identical input. A bounded installed
parser read records the actual format and atom/bond/charge/coordinate inventory,
plus the exact dispatcher and monomer-parser sources. It requests no chiral
constructor or numerical generation. Parser internals are not instrumented;
signed stereo, formal-charge semantics and full generation still need review.
The first audit stops before native parsing at an internal temporary-path guard.
Cedar 36 resolves that owned temporary directory, a portability fix exercised
for both dictionary formats, and retries the same parser checks while retaining
the failed attempt. The chemical definitions and qualification limits are unchanged.
Returned Cedar 36 passes the PDU control. DP reaches the correct reader and
keeps its atoms, coordinates and signed markers, but the monomer parser silently
treats uppercase order tokens as single and does not load its formal charges.
Cedar 37 translates only the declared order vocabulary. It then separately tests
copying the explicit integer charges into the temporary parsed object, after
exact graph/coordinate checks and under pinned native API source proofs. The raw
reader failure stays recorded. Before/after recorded graph and stereo fields
must match, and the existing CCD control requires no charge assignment.
This component-object control requests no optimizer or generation; full native
stereo, generator and scientific qualification remain open.

## Declared triple bonds and installed restraint membership

Returned Cedar 37 confirms the declared-order translation and isolated
source-charge controls. The separate Cedar 38 diagnostic asks whether the
selected installation actually restrains a declared triple bond with an
appropriate length and linear neighbors. Public PDU and 5PC exercise different
atom names (C5A/C5B and C7/C8). The same graph walk selects every triple edge
and its adjacent angles; it contains no PDU-specific chemistry repair.

**Methods.** Freeze the exact predecessor and replay its mechanics and raw/
controlled reader inventories. Capture the selected monomer server's lookup,
resolved component ID, full parameter rows and exact installed CIF bytes. Build
one separate fixed-coordinate control per public source from declared ideal
seeds. Compare native interpretation without an explicit CIF, with the captured
installed CIF, and with the saved PDU candidate. Record active bond/angle
membership, targets, ESDs derived from positive weights, coordinate geometry and
torsions that contain an expected-linear angle. Native secondary-structure
inference is explicitly disabled. Report screening thresholds and all failures;
change no targets, coordinates or production selection.

This checks isolated component mechanics, not the complete ReadySet path.
Source-seed agreement is not independent chemical validation. The saved PDU
candidate has a 1.174 Å triple target and two 180° targets, but its coordinates
bend and six torsions contain the linear axis. It remains nonconverged and
stereochemically unqualified. Those torsions merit review; they are not yet an
established cause of nonconvergence. Two matching 5PC workbook records remain
unresolved, so this control chooses no pairing/stacking policy for 5PC. Returned Cedar 38 finds no component through the default monomer lookup for
either code. The supplied PDU dictionary does install the triple/linear terms;
six torsions remain flagged. The native geometry uses fixed source seeds, so
its straight bonds do not establish a repaired candidate or convergence.
Production defaults and NARestraints pairing/stacking authority stay unchanged.

### Numerical libraries and CCD chemistry are different sources

Cedar 39 separates missing numerical monomer resources from available CCD
chemistry. It reads only exact CCD paths under the already selected Phenix
Python-library anchor. It compares their full declared graph/charge/stereo state
and SMILES descriptor text with the public references; textual equality is not
an independent mapped-SMILES validation. Fresh direct and residue-name monomer
lookups, DG/DC canonical controls and native root paths calibrate the resource
context. Captured Utilities/GeoStd/monomer/CCD helper code and the ReadySet
dispatcher describe available routes without executing those helpers or ReadySet.
Simple installed CCD reads record bond-order/charge/coordinate inventories.
No chemistry, numerical target or experimental model is changed. This source
catalogue informs a later controlled ReadySet test; it does not reproduce one.
Its return verifies both installed CCD declaration/text comparisons and all raw
reader inventories, with four missing direct/wrapped numerical monomer lookups.
DG/DC canonical controls resolve normally.

Cedar 40 follows the hash-matched dispatcher to its literal ReadySet Python
entrypoint and captures bounded first-party import text. A separate fresh native
worker calls only the previously captured CCD filename and SMILES accessors,
recording the actual selected string and matching descriptor metadata. Static
source evidence does not establish an executed ReadySet path, and descriptor
selection does not establish a mapped chemical graph or numerical restraint.
The worker has a 30 s deadline; ReadySet, generation and optimization remain
unrequested. This boundary identifies which implementation must be reviewed
before a controlled reproduction of the reported PDU behavior. The return records
both CACTVS canonical selections and 24 source files. One inspected generation
branch deletes the SMILES and requests the CCD component directly; its executed
selection must be observed separately.

The isolated ReadySet diagnostic runs the original selected Python API on
source-seed heavy-atom PDU/5PC models. Returned Cedar 41 identifies a wrapper
invocation error: leaked ReadySet options stop both nested eLBOW parsers before
numerical generation. Its surviving dictionaries are unchanged source copies,
not evidence of missing generated triple restraints. Cedar 42 passes ReadySet
arguments only through its API and leaves process options empty, matching the
captured native entrypoint. Original builder calls and chemistry stay fixed.
Worker completion, native success and output provenance are reported separately;
failed evidence and exact seed-model/triple-screen replay remain preserved.
The returned C42 test completes both controls and verifies generated/native
triple lengths and linear-angle targets. Its file-input builder route supplies
no SMILES argument. It does not reproduce a missing-triple defect at these
isolated controls; historical behavior and linked-model geometry remain open.

Cedar 43 examines the remaining linear-axis torsions without deleting them.
Three existing heavy-atom proxies per component are rebuilt under the exact
captured manager. Single-restraint/container kernels and six-step central
differences are evaluated at the preserved source seeds and generated full/
rounded coordinates. Plane-normal sines describe conditioning; bent and exact
collinear numerical controls keep a finite zero gradient from being mistaken
for a defined torsion. Original parameter/membership signatures and installed
hashes are checked before and after. The 3,000-pair/180 s bound applies per
component. No optimizer or coordinate-model writer runs. Source phosphate
charge/hydrogen changes and 5PC's separate angle/plane review remain visible;
this is numerical evidence, not a chemistry decision or a repair. Returned C43
passes all sampled derivatives, including 234 independently recomputed
real-coordinate directions, but every selected torsion stays near-collinear.
Large forces grow as the defining atoms approach a straight line; a correctly
calculated derivative can still be poorly conditioned.

Cedar 44 prepares separate test dictionaries. A torsion is selected only when
its graph contains an explicit triple-bond flank whose angle is declared as
180°. Such a straight defining triple has no unique torsion plane. The rule
uses declarations, without fitting to the model or naming PDU/5PC atoms. Six
whole dictionary rows are omitted per control; every other parsed field must
remain identical. Fresh native comparisons must reproduce the original manager
and show only the six planned definition-row and three heavy-proxy omissions.
The strong triple-bond distance and straight-angle restraints stay intact.
This is an opt-in candidate test: no model optimization, charge/stereo repair
or adoption occurs. Returned C44 passes both native comparisons: three active
torsions are removed from each 28-torsion manager, with all unrelated terms and
triple targets intact. All earlier chemical-state and plane reviews stay visible.

Cedar 45 asks what those exact omissions change numerically. Rebuild both saved
managers and evaluate them at identical source, generated full-precision and
rounded coordinates. The difference in total and torsion energy/gradient must
match the sum of the three omitted terms; other families must give the same
values. Repeated evaluations and family sums test consistency. Candidate total
and torsion derivatives are sampled with six finite-difference steps in graph-
selected Cartesian and gradient directions. A lower total gradient is not an
acceptance rule: removing a contribution can expose strain that it previously
cancelled. Both managers retain their exact signatures and source/API hashes.
The audit is bounded to 2,000 evaluations/180 s per control, without optimization,
model output or adoption. Returned C45 passes all 246 derivative arithmetic
directions and confirms that the omitted terms explain the numerical deltas.
PDU passes every strict case. Two 5PC cases retain changing neighbour-count
reviews even though repeated energies and gradients are exactly unchanged.

Cedar 46 tests the cache explanation directly. Record each native energy
object's actual pair list, parameters and individual pair energies/gradients,
checking their sum against the native container calculation. Compare the early
and repeated lists: every added/removed pair must contribute exactly zero, and
shared pairs must keep the same parameters and contributions. Only after the
full/nonbonded lists settle does a separate retry use the unchanged strict
numerical checks, now also tracking pair identities and function parameters.
Original failures remain visible; counts and tolerances are not waived.
Returned C46 passes all six preflights and strict numerical cases. The 48 raw
pair-transition comparisons independently replay: each changed pair contributes
exactly zero energy and force, and shared terms and native sums remain fixed.
All 246 strict derivative directions agree. The pinned worker reports stable
pair identities during temporary perturbations; those perturbed lists are not
retained for independent offline replay. This closes the cache-count question
at the tested coordinates. It does not settle charge/protonation, absolute
stereochemistry, 5PC plane/angle findings or linked-scaffold geometry. No
dictionary/model, state choice or optimizer changes.

Cedar 47 returns to the earlier DP constructor failure. Preserve the correct
source reader and declared graph, record the raw native inventory, then apply
only the already tested source-charge transfer. Promote the parsed component
with the installed class adapter and require its inventory to remain identical.
Invoke the original native chiral constructor on this temporary object, retaining
completion/exception and full after-snapshots. Compare names, elements, orders,
charges, declared markers and nondegenerate source-relative signed volumes.
An explicit “both” sign remains permissive; fixed sugar hands stay protected.
Proper rigid motions are allowed. DP and both public controls share this generic
check. Existing installed sources, inputs and all earlier failures stay pinned.
The constructor may optimize local chiral templates internally, so the receipt
keeps this separate from whole-molecule optimization and full generation. A
handoff pass does not independently assign absolute CIP or settle phosphate,
5PC plane, linked geometry or scientific approval.

The C47 return records three exceptions after the source/charge gates pass.
Our diagnostic missed an installed-reader prerequisite: select the CCTBX
backend before asking for chiral construction. Without it, DP/PDU stop during
chirality setup and 5PC reaches an unavailable legacy optimizer. The failed
local coordinates stay evidence, with no completed-candidate claim. The old
route warning means missing after-format metadata, not a proven reader switch.

C48 supplies the native prerequisite explicitly. Check the selected reader's
source, resolve and capture the actual backend methods, then record both flags
and full molecular inventories around `SetCCTBX(True)`. Refuse any change to
chemistry, coordinates or reader format at that step. Only then call the same
native constructor and apply the existing hand/marker/graph/charge gates.
Replay and preserve all C47 failures, and restart original source bytes rather
than their partial temporary coordinates. This generic control changes no
chemical targets and requires no installed Phenix patch. Corrected native
construction now completes in all three returned cases, with every backend and
chemical-inventory gate passing. The source-relative hand warnings remain:
DP/5PC C1-prime and PDU C1/C3/C4-prime. Stored labels survive while temporary
coordinates disagree. All-neighbor analysis also exposes DP C4-prime and a
mixed-basis 5PC C4-prime finding. These measurements neither assign absolute
CIP independently nor qualify a complete molecule.

C49 observes the local construction rather than choosing a chemistry fix from
an endpoint. Separate fresh native runs compare an unobserved control with an
observed constructor. Selected-source wrappers forward the original calls once
and record complete parent state, local atom order/shared-object evidence,
arguments, returns and exceptions at Z-matrix, local construction, restraint,
CCTBX optimization, tightening and native R/S-return boundaries. They restore
the original methods even on exception and retain existing source/hash checks.
Maintained replay checks the nested ledger and all four neighbor triples plus
the four-neighbor determinant, then identifies the first observed reviewed
boundary. Nested timing alone does not establish a causal defect. Exact fresh
repeat agreement is a separate observation; random state is not reset and
differences remain visible. The six owned workers have 30 s caps; each trace
has at most 256 calls. Returned C49 completes all six constructors: fresh
observed/unobserved endpoints and earlier C48 endpoints match exactly. Hand
warnings remain. DP's native marker fields change while its signed-volume
metadata survives; retain the failed continuity gate. Reviews can clear and
recur as overlapping local templates move shared atoms into temporary frames.
A parent endpoint is therefore not a completed-molecule stereo verdict.

C50 follows coordinates by name through local native read/write order and
actual manager chirality proxy indices. The observer records original vectors,
local indices, native signed volume targets/weights and both-sign flags.
Maintained replay checks exact vector assignment and maps each ordered proxy
basis to source atom names, then compares the source volume with the native
target sign. A separate replay identifies any sorted-index transfer between
final restraint tightening and native R/S inspection and reports local hand
before/after. These are observations before a repair: source warnings, marker
gates, native arguments/targets and NARestraints authority remain fixed.
The same six 30 s workers/256-call bounds apply, with 64-row vector/proxy caps.
Returned C50 passes all vector read/write checks, exact repeats and nine
observed sorted-index transfers. Its local-order interpretation still reviews
one proxy origin per component. Sorting saved names by native index explains
all PDU/5PC source target signs, while DP C1-prime still disagrees. That
reinterpretation is a hypothesis; a proxy offset belongs to a particular
array, not permanently to a name or a local-list position.

C51 therefore records native restraint dictionary atom keys and stored
coordinates alongside the original returned array. Exact alignment with
named keys ordered by native index must prove the restraint basis; duplicate
stored vectors keep the result under review. The actual
local getter order remains separately visible, with the same proxies/targets
mapped in both views. Selected native producer/factory source and methods are
captured; no extra GetRestraints call, kernel edit or coordinate rewrite occurs.
Keep the original hand/metadata findings and fresh controls. Returned C51
verifies six constructors but all nine atom-key inventories are empty: the
observer expected atom objects and the native dictionary uses integer keys.
C52 records those integer keys, existing native link positions and exact
named local indices, honoring unique_index before index. It fingerprints the
selected native key/coordinate methods without calling them again. All
inventories/returned vectors must agree; no native computation is reindexed.
Returned C52 proves all nine bindings and all public-control source target
signs; DP C1-prime retains the opposite target sign. Temporary frame/marker
warnings remain separate from a finished molecule's configuration.

C53 tests the native builder preparation that stores input_xyz before chiral
construction. It calls selected native Setup once, checks exact unchanged
component state and original-coordinate caching, then compares fresh prepared
unobserved/observed constructors. The old unprepared endpoint remains a separate
comparison; an effect of preparation is not observer divergence. Cached values
are recorded again afterward to expose alias/mutation behavior. Original native
kernels, targets and source chemistry stay fixed. This is an isolated setup
control, not a complete builder or independent absolute CIP assignment. Native
C53 evidence now passes all setup/cache checks and nine native-basis target
signs, with exact fresh repeats. DP changes from the unprepared endpoint while
PDU/5PC do not. Temporary hand/marker warnings remain separate.

C54 moves from local templates to complete independent dictionaries. It passes
the source-prepared molecule into the installed full-builder API, whose own
Setup, construction, optimization and writing remain unchanged. One 180-step
block and a 600-second worker deadline bound each component. Written output is
kept across nonconvergence and later exceptions for automatic native usability
and fallback qualification. Finished configuration uses four named neighbors,
so central deformation/pucker is not inversion. Source chemistry, charges and
numerical completeness are still checked. Students do not inspect these CIFs;
production selection/adoption and the solution PDF adapter remain planned.
Returned C54 completes all three builders and preserves charges and all nine
finished source-relative configurations. PDU is nonconverged; DP/5PC stopping is
unreported. DP's raw rejection is one omitted phosphate volume term marked
`both`, which permits either hand; the three fixed sugar definitions match.
That volume term still constrains geometry, so its omission remains explicit.

C55 reuses the saved outputs at source-seed and generated coordinates to test
isolated native usability. Exact effective definitions, complete essential
restraints and fixed covalent targets/weights must survive. The omitted `both`
term requires four active bonds and six angles at its centre. Two fixed native
energy/gradient evaluations per case must be finite and repeatable; their size
is not an acceptance threshold. Six workers have 60-second deadlines, with no
regeneration or optimization. Verified evidence reaches the existing automatic
decision core for this isolated generated-candidate pool only. Nonconvergence
is a note, and unselected generated output leaves production dictionaries
untouched. Returned C55 completes all six native interpretations. Its twelve
recorded energy/gradient evaluations are finite and repeat exactly. The auditor
needs two representation corrections: allow 1e-12 A Cartesian roundtrip error
and recognise period-zero/zero-ESD native constant torsions. Signed torsion
sorting must also transform target and alternate angles. These checks preserve
every native row and keep positive-weight requirements for active restraints.

Corrected v2 replay passes all six cases and retains three isolated candidates
with notes, preserving the original failed records. C56 pins and replays those
saved receipts, source snapshots and data without executing captured Python or
starting Phenix again. This is native usability evidence, not convergence,
linked polymer classification or scientific approval. Students do not inspect
CIFs, and production dictionaries are not replaced by this diagnostic.

**Methods.** Freeze and hash the prior output; compare named chemical graphs,
explicit formal charges, fixed signed definitions and finished four-neighbor
configuration. Keep the old rejection alongside the narrower reassessment.
Interpret each candidate independently at two coordinate sets, pin selected
native energy implementation sources, compare complete effective definitions
and name-normalized covalent proxies, and record two unnormalized energies and
gradients per case. Continue decisions depend on verified usability rather than
convergence. Unsupported native formal-charge access remains unassessed and
never uses partial charge as a replacement. The generated ligand/non-polymer
classification, phosphate state, triple-axis torsions, absolute CIP and linked
scaffold integration remain separate qualifications. No student CIF inspection
or automatic production adoption is involved.

C56 returned all six saved passes and three continue decisions. C57 restores
DNA labels from the source into separate written headers.
Phenix already classified all three components as DNA, even though the files
say ligand/non-polymer. The test asks whether clearer source metadata preserves
the same mechanics; it does not claim that a DNA chain has been linked.

**Methods.** Use only explicit consistent source DNA declarations. Change the
two group/type fields, preserve every other parsed value and both original
files, then reinterpret the same two frozen coordinate sets per component.
Require native DNA metadata, the same fixed covalent restraints, and matching
full targets and named gradients. If either comparison fails, automatically
retain the already-verified original. Software preparation/fallback tests and
relocated actual-C56 replay pass. The six Mac interpretations have now returned
PASS and their twelve finite evaluations repeat exactly; all worker/source and
selection evidence replays from the preserved C57 capsule. No optimization, production adoption or student approval is involved.
Polymer links, nonbonded pair identities and final structure qualification are
separate evidence.

C58 places each qualified component between two explicitly declared DNA
neighbors in a separate three-residue control. Its baseline is the same short
canonical strand. Backbone and flanking coordinates stay fixed; the connected
base is transported rigidly into the sugar frame. The existing graph rule
removes only the incoming OP3 group and outgoing oxygen H, and uses the reviewed
outgoing-oxygen type. The passed isolated evidence is hash-bound before this
preparation; old callers retain their existing source gates.

**Methods.** Reinterpret one canonical and three modified controls under the
same native API/energy policy, with explicit site modifiers and no automatic
secondary-structure guesses. Require both backbone links, unchanged link targets,
all selected projected/heavy-atom restraints and phosphate tetrahedral coverage,
with flanking mechanics preserved. Fixed energies must be finite and repeatable;
no optimization or cross-component energy ranking occurs. Returned C58 passes
all three modified linkage controls after four completed native interpretations
and eight finite, exactly repeated evaluations. Formal-charge readback remains
unsupported without contradictions. These synthetic linkage controls establish
neither full-scaffold adoption nor scientific structure qualification.

C59 tests the new DP dictionary at B:4 in a separate copy of the preserved full
model and NARestraints bundle. This asks whether a usable component can enter
the real model without disturbing its neighbors or designed interactions. The
original bundle remains available automatically if the candidate is unusable.

**Methods.** Keep all 877 atoms and 43 sites at the saved PDB-rounded coordinates.
Replace only the selected dictionary and that site's old modifier requests;
preserve shared definitions and other sites' requests byte for byte. Apply the
qualified source-graph incoming/outgoing preparation. Rebuild and match the
original native manager, then test the candidate, with two fixed evaluations
and a 60-second deadline per worker. Require every one of the 38 backbone links,
unselected definition/proxy and explicit NARestraints pairing/stacking request
to survive, alongside the selected projected restraints and phosphate coverage.
Select the qualified candidate or retain the verified original automatically;
no student CIF decision is introduced. Returned C59 passes the twelve baseline
checks and 67 candidate checks, retaining only unsupported formal-charge
readback, and selects qualified_candidate with notes. Every model identity,
backbone link and designed pairing/stacking request survives. The independently
generated DP angle target is a new fixed definition; fixed-coordinate outlier
counts under different objectives are not an optimization comparison.

C60 performs one bounded geometry-only trial under that replacement manager.
It starts from the verified C59 coordinates and retains them automatically if
the trial is unusable. This allows the workflow to progress without asking a
student to diagnose a bond table or run indefinite continuation cycles.

**Methods.** Audit fresh corrected derivatives at the new initial coordinates.
Carry the established general plane correction proof only when complete
plane/parallelity inventories, atom-name mapping and native API/source pins
match; the replacement covalent manager receives a new constraint signature
and fresh full-objective derivative evidence. Preserve the qualified correction,
native kernels, dictionaries and NARestraints policy. Use the existing geometry
worker, L-BFGS and termination rules for at most 1,000 iterations. Check endpoint
derivatives in full precision and after PDB rounding, exact native readback and
serialization/source hashes. Both full-precision and freshly reread rounded
geometry must have zero fixed-hand sign conflicts; both targets must be no worse
than the new trial's initial target under the same objective. Retain a usable
endpoint or the verified initial model automatically, including when no endpoint
is produced. Nonconvergence, pucker and residual outliers alone do not require
failure or further cycles. Returned C60 passes its initial and two endpoint
sampled derivative cases, all 17 native readback checks and all eight selection
checks. It retains a usable endpoint with notes while preserving the 1,000-step
iteration-limit verdict. The fixed-objective target decreases 6.09% and gradient
norm 96.62%; full-precision and written-PDB values remain separately reported.
Both geometries retain zero fixed-hand conflicts and three bond/nine angle
outlier descriptions. This supports progression without another continuation
cycle; scientific geometry, state/CIP, production adoption and PDF rendering
remain separate.

C61 packages the selected written model and its exact 19 dictionary/14 parameter
resources into a portable runtime bundle. The practical purpose is to let an
ordinary NASolve reader consume the verified resource choice after the original
diagnostic paths disappear, without manufacturing a completed structure run.

**Methods.** Copy exact bytes into a separate manifest-bound bundle, retaining
ordered resources, source hashes, continuation notes and activation evidence.
Every operational path stays relative to the bundle root. The evidence retains
the initial model so the coordinate choice can be reproduced. A generic resolver
checks integrity, then the public `cif-doctor assess --bundle PATH` uses the
existing read-only assessor. Its plain-language solution_report preserves the
selected model, stopping verdict and continuation notes; PDF rendering remains
planned. One separate native readback from this staged
layout must reproduce the qualified rounded manager and explicit NARestraints
policy. Returned C61 passes all 15 fresh native checks and two finite repeatable
evaluations, preserving the exact selected model/19 CIFs/14 PHILs. The ordinary
33-input assessment remains REVIEW with continuation notes. There is no
parameter generation, optimization, new pairing/stacking guess or diffraction/
refinement run. The current bundle summary labels native selection as inherited
VERIFIED_SOURCE_CAPTURE, with native_selection_executed false; old receipts
remain unchanged.

This is a resource/reader bridge toward production and the eight-pair test.
Automatic acquisition/repair, ordinary PostMR adoption, production checkpoints
and PDF rendering remain future work. The capsule lacks observations and an
ordinary PostMR report; neither an AutoMR run nor a checkpoint is fabricated.
Students do not approve CIFs. Curated sources and NARestraints retain their
authority.

C62 fixes ordinary modified-base construction. It prevents the restoration step
from combining part of a parent base with a newly built substituent merely
because atom names match. The complete connected base now moves together while
the intended parent DNA scaffold is restored. The fresh controls call the same
construction API used by ordinary PostMR, rather than replaying an old damaged
model or running another geometry continuation.

**Methods.** Read the explicit source graph, select the heavy base connected only
through C1-prime, and apply a proper rigid transformation between raw Coot and
parent C1-prime/O4-prime/C2-prime frames. Preserve the base's internal geometry
and attachment hand within PDB rounding and restore parent sugar/backbone
coordinates. Canonical mutation backbones and explicit curated substitution/
ring placements retain their previous semantics. Unsupported, ambiguous or
bridged components keep their whole raw Coot site with notes; ATL is an
independent example. No partial base copying or forced bridged-sugar conversion
is used. Returned C62 completes Coot 1.3.3 for DP, PDU and 5PC, but each site
keeps its
whole raw coordinates: the raw OP3 has no parent scaffold match. The fallback
works as intended; this return does not exercise rigid base transport.

C63 supplies the missing internal-phosphate context in ordinary construction.
Use frozen connectivity and atom identities to authorize selected serial
normalization. A discarded shadow places only matched sugar/backbone atoms in
the parent frame so the existing phosphate sanitizer can prove internal OP3
removal. Transfer only the proved deletions to the original raw coordinates,
then move the complete base with the existing proper transform and recheck
phosphates. Shadow coordinates never enter the model. The frozen allowed-OP3
and passthrough policy is unchanged; ambiguous proof retains the whole raw site
with notes. This changes ordinary coordinate preparation, not dictionary
chemistry or native restraint mechanics.

The saved-C62 study proves three deletions and preserves base geometry within
PDB rounding; it is not a fresh Coot result. Returned C63 now independently
completes fresh Coot construction: all three bases are transported, three internal
OP3 atoms are removed under the existing policy and no raw fallback occurs.
The final model retains 854 atoms at 42 sites; 788 unselected atoms retain their
identities, elements and coordinates. C63 tests the same ordinary API
with one fresh process bounded at 600 seconds, plus an independent context
change audit. Completed reports describe observed raw/context composition;
inspect-only remains unobserved. Portable diagnostic-backup mapping preserves
legacy timestamped backup bytes without relaxing scientific paths. ATL remains
public graph/restoration eligibility only, with no fresh Coot outcome claimed.
Observations, ReadySet, generic NAR compilation, repair/adoption, production
checkpoints/refinement and PDF output remain separate integration work before
the planned full eight-pair run. No student CIF decision is added.

C64 checks that exact constructed model in native Phenix before another
production boundary. A canonical reference and the constructed model use the
same secondary-structure-disabled policy, with existing source-qualified site
modifiers for the three internal components. The implementation compares native
backbone links, effective chemical definitions, heavy-atom proxies and active
triple length/linearity terms, then records two fixed evaluations per model.
The different objectives are not compared as an optimization improvement.
The returned workers both complete and retain active PDU/5PC triple targets.
Six reviews come from display-label residue-name padding. C65 compares complete
structured atom identities and every ordered restraint parameter instead: all
3,148 unaffected terms match exactly. Label/index bindings and unique identities
are required before comparison; altered targets, weights, symmetry, origins,
endpoints or multiplicity remain failures. Saved preparations, native workers,
specifications and results are replayed as data with zero new native calls, and
the original REVIEW receipt remains unchanged. Scientific geometry and full-run
integration stay separate. Returned C65 verifies all 3,587 payloads and
independently reproduces 93 passing checks, zero review checks and three
unsupported formal-charge readbacks. Both active triple screens pass.

This readback is bounded to two 60-second workers and changes no model, native
kernel, numerical target or optimizer. Pairing/stacking compilation and ordinary
repair/adoption remain subsequent integration work; no student CIF gate is added.

Methods: preserve the exact Coot-built coordinates and frozen canonical input,
prepare explicit source-graph component modifiers, and interpret both layouts
with Phenix 2.2.1-6174. Compare named native atom identities, canonical backbone
link targets/weights, projected site definitions and active heavy-atom proxies.
Require complete phosphate tetrahedral coverage and finite repeatable native
evaluations. Assess graph-declared triples at the same explicit native site;
keep residual geometry and linear-axis torsion findings separate from numerical
membership. No diffraction or convergence claim follows from this test.

ATL is now a separate public control: its bridged sugar and four declared
stereocentres survive graph assessment and the existing NARestraints T-class
pairing/bidirectional stacking compiler. Its source fixture is hash-pinned;
the workbook already contains alpha-LNA-T. These are source/compiler checks,
without native construction, a forced standard-DNA sugar, or scaffold approval.
The three native baseline components and planned eight-pair live run stay fixed.

Process-local observers forward the original eLBOW
builder/template calls unchanged and record their arguments, call sites,
returned graphs or caught failures. A 180 s deadline bounds generation, followed
by at most 60 s native interpretation per control. Ligand AM1 and final hydrogen
optimization are disabled; native internal template operations may still run.
Any generated dictionary is assessed against the full source, then triple
length/linearity targets, positive weights, membership and torsions are checked
at fixed heavy-atom source seeds. Hydrogen/stereo/charge differences remain
explicit review evidence. No linked model, refinement or adoption is involved.

5PC is already recorded twice in the NARestraints cytosine sheet, with identical
C-like roles. The former review came from the auditor's duplicate guard,
descriptive modification columns and arbitrary synthetic-partner order. The
auditor now accepts equal operational mappings while retaining raw aliases,
excludes explicit annotation columns and prefers a registered canonical partner
for the compiler check. Conflicting or absent atom roles still require review.
This changes the diagnostic, with no NARestraints workbook, recipe or release
change. It does not certify protonation or experimental pairing geometry.

## Primary references

The following documentation was checked on 2026-10-11. Cite the corresponding
software/data publications and exact versions required by the journal; these
links explain each tool's role and are not validation receipts for NASolve.

- [Biopython MMCIF2Dict API](https://biopython.org/docs/latest/api/Bio.PDB.MMCIF2Dict.html).
- [Phenix ReadySet documentation](https://phenix-online.org/documentation/reference/ready_set.html).
- [Phenix eLBOW documentation](https://phenix-online.org/documentation/reference/elbow.html).
- [wwPDB Chemical Component Dictionary](https://www.wwpdb.org/data/ccd);
  Westbrook et al., *The chemical component dictionary: complete descriptions
  of constituent molecules in experimentally determined 3D macromolecules in
  the Protein Data Bank*, DOI [10.1093/bioinformatics/btu789](https://doi.org/10.1093/bioinformatics/btu789).
- [CCTBX geometry-manager API](https://cctbx.github.io/cctbx/cctbx.geometry_restraints.manager.html)
  and [scitbx L-BFGS API](https://cctbx.github.io/scitbx/scitbx.lbfgs.html), checked
  2026-10-17; exact installed optimizer hashes are recorded separately.
- [NASolve implementation and provenance](cif-doctor.md),
  [scientific audit design](cif-restraint-audit-methods.md) and
  [NARestraints](https://github.com/vecchioni-lab/NARestraints).

## Persistent reusable component numerics (Cedar 66)

Repeated crystals should not repeat a successful component repair. The shared
store/resolver saves usable numerical dictionaries locally, including a finite
nonconverged candidate and its original notes, and consults them before another
acquisition callback. Source authority and exact declared chemical state are
preserved. Ordinary PostMR acquisition/adoption orchestration is still separate;
C66 exercises the implemented API explicitly with DP, PDU and 5PC.

The algorithm uses SHA-256 content identities, standard-library JSON/filesystem
operations and the existing usable-candidate policy. A semantic source/recipe/
backend-family lookup is separate from an immutable entry digest containing
candidate bytes, complete original producer and native consumer provenance,
qualification and stopping evidence. Publication uses an owned staging
directory and atomic rename. Current-source/configuration checks and artifact
hashes precede reuse. Source/state mismatch creates another request; a changed
consumer or check policy requalifies saved numerics before regeneration. An
upgraded Phenix builder is not misattributed as the producer of old bytes.

The resolver freezes source, numerics and immutable evidence per run with
relative anchored references. Removing the cache cannot change that run.
Terminal/linkage modifiers and new-model geometry remain separate qualification
layers; cache reuse never certifies a new crystal. C66 uses saved Phenix
2.2.1-6174 evidence without new native processes or an installed energy-library
resource-file qualification. It does not upload chemistry, change native
mechanics or ask students to inspect CIFs.

Methods: accept only complete source/candidate-bound isolated native evidence,
reassess the current declared graph/configuration, look up reusable numerical
bytes, and copy their checksummed source/qualification/provenance into an owned
run snapshot. Preserve nonconvergence and unsupported evidence as notes. Test
source/authority/consumer invalidation and consume relocated snapshots after
removing an owned cache copy. Producer/consumer/check-policy upgrades retain
base numerics for requalification; automatic ordinary-pipeline and PDF consumers
remain to be integrated.

Returned C66 verifies all **3,659 payloads** and the byte-identical C65
parent and manifest. DP, PDU and 5PC each pass ten reuse controls: their
first qualified dictionaries are saved and repeated requests reuse the exact
bytes without acquisition. Source/authority mismatches are excluded and a
changed consumer requires requalification before generation. Independent
replay reproduces all 30 controls and nine frozen snapshots, including original
stopping/limitation notes, with every subprocess forbidden. Ordinary PostMR
orchestration and the requested eight-pair live run remain separate work.

The Mac return preserves PDU's reported nonconvergence and DP/5PC's unknown
convergence evidence. A reuse pass certifies retained isolated numerics and
their provenance; it does not certify a new crystal or installed runtime.

## Ordinary sources and the intended pair matrix (Cedar 67)

Returned C67 verifies all **3,713 payloads**, including the unchanged C66
parent and manifest. The ordinary source selector passes **15/15 sources**
(six curated, nine installed CCD), and NARestraints compiles **8/8 declared
pairs and 16/16 stacking orientations**. Independent maintained replay
reproduces all 39 source/PHIL files exactly; report differences are limited
to historical source paths. DP/PDU/5PC saved repairs correctly miss because
their raw source bytes/authority differ; all inventoried chemical declarations
match. No repair is substituted by component name.
No native process or adoption occurs; full-run integration remains open.

A repair is useful only if it belongs to the chemistry the pipeline actually
selected. C67 therefore asks the ordinary source selector first and preserves
curated priority. It records source/repair differences instead of substituting
a cached component by name. Two compatibility defects are fixed generally:
equivalent descriptive workbook aliases no longer block construction, and
valid native loop metadata no longer fails scalar-only identity validation.

Methods: compare every operational role and sugar/phosphate/attachment context;
reject conflicts; freeze selected source bytes with SHA-256 references; map
NARestraints roles onto those exact atom names; compile each explicitly
requested pair and both stacking orientations using the existing library.
These controls have no observed coordinates or native restraints. The Mac
return establishes ordinary selection from the configured installation and
the exact declared-role compiler behavior. Independent replay uses those
captured source bytes; automatic repair/adoption and current native/site
qualification remain separate integration work. No student inspects CIFs.

## Keeping a repair when source packaging differs (Cedar 68)

C68 adds an ordinary-source reuse API without weakening exact cache keys.
It selects the ordinary source first, verifies a saved projection against its
named chemistry and configuration, then requires current isolated native
usability before publishing a new source/authority-bound entry. Numerical bytes,
original producer and stopping notes are retained; repeats reuse them. Failed
candidates retain the selected source for standard preparation. No student
CIF inspection, generation, optimizer or production adoption is introduced.
Returned C68 preserves all 3,766 payloads and the complete C67 parent.
All three source projections pass, but native input/output placement triggers
the preservation guard before any worker launches. Its historical call count
of three records attempts; it supplies no fresh native qualification.
Returned C69 completes all three native reads: 63/63 usability checks and
six fixed repeat evaluations pass. A later reporting call supplies two mutually
exclusive auditor inputs, so source-bound publication/repeats are not selected.
Returned C70 verifies all 4,008 payloads and the complete C69 parent. DP,
PDU and 5PC each publish a qualified source-bound entry and immediately REUSE
the exact numerical bytes. Maintained code reproduces all 63 native checks,
both triple reports and 72 result artifacts; only explicitly nonoperational
source paths rebase. All six frozen copies resolve after original source/cache/
evidence removal with external scientific reads forbidden. Original producer
and stopping notes survive, including PDU nonconvergence. No new native process
runs. Current installation/site/model checks and ordinary PostMR/full-run
integration remain separate; no repeat of this saved cache gate is needed.

C71 connects local reuse to ordinary PostMR. Before ReadySet,
`prepare_postmr_dictionaries` selects and freezes ordinary sources, then checks
eligible source-bound cached numerics. Original sources still drive Coot and
remain in source receipts. The existing normalization/combination and dictionary
precedence receive cached numerical inputs only when their exact source,
authority, supported recipe/backend and current native consumer match.
Fresh version discovery is lazy and runs once per eligible batch; the selected
native dispatcher and all eight recorded API/three energy source hashes must
match inside the configured installation. This is the recorded identity scope,
not an exhaustive compiled-kernel or energy-library-data fingerprint.

Missing, corrupt, unsupported or changed-consumer entries retain ordinary
preparation with notes. Missing curated sources keep their existing refusal.
The cache is read-only and each run freezes independent relative/hash-bound
copies with original producer/stopping evidence. Nonconvergence remains a note;
no student inspects CIFs. PostMR records reuse/fallback and plain-language notes.
This adapter does not generate or optimize a dictionary. Uncached components
continue through the existing preparation path.

Methods: validate indexed entries against the selected source and the existing
isolated qualifier, verify the current recorded consumer identity, use the
existing automatic usable-candidate policy and exact-key resolver, then freeze
source and numerics separately. C71's explicit `--postmr-dictionary-reuse-only`
probe consumes exact returned C70 and calls this same ordinary API. The actual
Mac return verifies all three REUSED cases and POSTMR_CACHE_HANDOFF_PASS: exact
saved numerical bytes pass all 63 checks in three fresh Phenix 2.2.1-6174 native
readbacks. Six fixed energy/gradient evaluations are finite and exactly repeated;
all worker dispatcher/API/energy inventories match the selected recorded consumer.
Existing normalization changes none of the three dictionaries. The combined
31,252-byte ReadySet input reproduces exactly. Both triple/180-degree target
screens pass for PDU/5PC; linear-axis torsions and seed bending remain notes.

All 4,231 payloads, the unchanged C70 parent and 159 runtime members verify.
Reconstructing only NAR dirty-state metadata reproduces the reported runner SHA.
All three independent run copies resolve after original source/cache/evidence
removal with external scientific reads and every subprocess forbidden. Original
producer/stopping notes, including usable PDU nonconvergence, are unchanged.
No ReadySet, Coot, generator or optimizer executes in this probe. The next
boundary is observing ordinary ReadySet consumption/no-regeneration and current
linked/whole-model NARestraints membership. The eight-pair full run, refinement
and solution PDF remain separate. Inspect-only remains a captured-source fallback
check with no current-consumer/cache-hit/native claim. This returned-evidence
update changes no runtime, schema, chemistry, mechanics or dependency.

C72 methods: consume the exact verified C71 capsule and preserve all 4,231
payloads. Separate DP/PDU/5PC controls use the ordinary `_run_readyset` helper
and its unchanged CLI arguments. An optional private execution hook launches
the selected Phenix Python on the dispatcher's verified literal entrypoint as
`__main__`; the shell dispatcher itself is not executed. A process-local profile
observer records selected eLBOW builder/template calls, Python subprocess calls
and effective ReadySet actions. It replaces no native function and overrides no
native argument. Fresh bounded source snapshots and the recorded consumer
identity are verified before/after execution. An absent call is reported only
within this observer scope, never as exhaustive native/optimizer coverage.

The copied heavy seed omits H/D records while retaining exact heavy coordinates.
Require a completed untruncated observation, the requested actions, no observed
builder/template/child calls, unchanged named heavy sites and exact cached
numerics under ordinary parameterized-input precedence. Only then read back
effective terms on the unchanged C71 full-H seed, with current consumer checks,
the existing 21-check qualifier and separate triple screens. The native H sites
are saved control coordinates, not new ReadySet placements. Each of at most
three ReadySet calls is capped at 180 seconds; each fixed readback at 60 seconds.
There are no retries. Failed observations retain verified inputs and notes.

Frozen relative/hash-bound inputs, outputs, worker/spec and source evidence make
the diagnostic auditable. Inspect-only prepares three input controls without
any installed process or cache access. Default ordinary execution, chemical
definitions, target mechanics, native kernels and NARestraints remain unchanged.
No dependency, cache migration or NAR release is needed. Actual Mac consumption,
whole-model links and exact pairing/stacking, the eight-pair full live run,
refinement and solution PDF remain separate; students do not approve CIFs.

Returned C72 verifies all 4,482 payloads, unchanged C71 parent, 160 runtime
members and the reported runner SHA (only NAR dirty-state metadata differs).
The source scanner captured 24 files, including the routing module that imports
`elbow.command_line.builder`, but does not traverse that non-ReadySet module.
The required observer target is absent, so the source guard stops before any
ReadySet or fixed native readback. Preserve the original failure receipt and its
false completion/preservation flags; independent replay verifies the four copied
5PC inputs and complete C71 lineage without changing those recorded flags.

C73 methods: retain the bounded literal-import scan and explicitly freeze each
named observer module that it does not discover. Enforce the same selected-root,
32-file, 1 MiB per-file, 8 MiB total and before/after hash checks. Add explicit
observer-root/source metadata without claiming transitive or native-internal
coverage. The actual captured 24-file layout plus 13 identical prior builder
snapshots reproduces a 25-file source inventory without executing captured code.
A generic indirect-import fixture now covers both no-builder and observed-builder
paths; missing, escaped, oversized and changed sources remain blocked.

Returned C73 verifies 4,830 payloads, the unchanged C72 parent and reported
runner SHA; only recorded NAR dirty-state metadata differs from the clean build.
Three Phenix 2.2.1-6174 ReadySet controls complete with all 25 source proofs,
exact cached effective numerics, unchanged heavy sites and requested effective
actions. Maintained replay reproduces all 24 checks: 21 true and three false
no-subprocess checks. Each untruncated trace records one Popen constructor call,
zero builder/template calls, and no command or caller. The child activity remains
unclassified; no fixed native readback runs. Preserve the original receipt's
generic native_execution label while reading its explicit zero native counter.

C74 methods: observe literal subprocess arguments, executable, shell and cwd
separately, with bounded caller source/function/line metadata. Do not capture the
environment or call conversion methods on opaque values. Preserve bytes as hex
metadata; mark truncated or unsupported parameters explicitly. Cap 64 arguments,
2,048 characters/bytes each, 8,192 total before encoding and 16 caller frames;
retain the 128-event cap. These are constructor-call observations, not a child
completion or exhaustive native-internals proof. No native function or argument
is replaced, and the existing no-child acceptance rule remains unchanged.

Returned C74 verifies all 5,304 payloads, the exact C73 parent, runtime inventory
and reported runner checksum. Each completed control preserves cached numerics
and heavy sites and records the same literal system_profiler hardware query.
The five nearest caller frames lead through libtbx machine-memory introspection
to scitbx neighbor-grid initialization. The remaining import frames are truncated,
but the trace/event/parameter budgets are complete. C74 captures no source for
these three caller modules; its v1 no-child review and zero native-readback count
remain unchanged. Current upstream CCTBX source supports the memory-query purpose,
but does not establish identity with this installed Phenix version.

C75 methods: capture libtbx easy_run/introspection and scitbx cubicle_neighbors
with the same selected-root, 32-file/1 MiB each/8 MiB total and before/after hash
guards. Parse those frozen bytes without executing them. Require the literal
system_profiler program/hardware argument and the native producer, process-wrapper,
memory-constructor and neighbor-grid call structure. Match all five observed
caller paths/functions and call-line spans against this source. Require the exact
recorded shell command and complete literal parameters; deeper import-frame
truncation is permitted only after the complete checked prefix.

V2 keeps the seven other consumption checks and replaces the blanket no-child
guard with no unclassified subprocesses. Preserve every raw event/count; record
known resource queries separately. Extra commands, different programs/arguments,
nonempty loader prefixes, changed callers/sources or incomplete evidence retain
review. Old v1 reports remain readable and retain their original verdicts. No
native function, ordinary argument, numerical dictionary or target changes.

The C75 retry preserves exact C74 and all prior evidence, reuses verified C71
inputs and performs the same three bounded controls. Only passing controls receive
the unchanged fixed native checks on the unchanged full-H seeds. No installation,
generation, optimization or student CIF approval is requested. Returned C75
verifies all 5,949 payloads and the exact C74 parent. All three Phenix 2.2.1-6174
controls pass their eight checks. Each retains zero builder/template calls and
one source-proved resource query with zero unclassified children. Fresh native
readback passes all 63 usability checks and six finite repeated evaluations with
matching consumer identity. The 28-source installed snapshots, classifier and
native qualification replay as data; no captured Python is executed. Original
C73/C74 reviews, nonconvergence and retained torsion/bending notes remain intact.

C76 methods: resolve current-source-bound resources from exact C75 and the full
constructed model/canonical reference from the verified C63/C64 lineage. Reuse
the existing source-qualified site modifiers at DP A:6, 5PC A:7 and PDU A:9.
Require a fixed native readback to pass the unchanged construction qualifier
against the saved canonical reference, with freshly matching dispatcher/version,
eight API and three energy-source fingerprints. No Coot or optimizer is rerun.

Merge only the three prepared base dictionaries for one ordinary whole-model
ReadySet call. The bundle wrapper requires matching declared source/numerical
components and their presence in the model; it uses the same arguments, observer,
resource-query proof and eight consumption checks. A passing result receives one
fixed native readback with unchanged site modifiers and explicit PHILs. Require
all backbone links, exact projected site definitions and every ordered named
proxy/parameter/origin/symmetry/multiplicity in all eight families to survive.
Only display padding in structured identities is normalized. Both fixed reads
retain the existing finite/repeatable energy/gradient checks; no derivative or
scientific geometry verdict is inferred.

Select the checked endpoint only after every gate passes; otherwise retain the
verified constructed start with notes. Unverified starts cannot be selected.
Inspect-only prepares portable inputs and reports NOT_ASSESSED. This is at most
one ReadySet call (180 seconds) and two native reads (60 seconds each), with no
retry, generation or model optimization requested. No cache key/entry, numerical
target, ordinary production behavior or NARestraints policy changes. Pair/stack
guessing stays disabled; the intended eight-pair/16-stacking live-model membership
and full-run qualification remain separate. No student CIF approval is required.

Returned C76: all 6,691 payloads, exact C75 parent, clean runtime inventory and
reported runner identity verify. Native mechanics pass (93 PASS, three unsupported
formal-charge readbacks), including all 38 links and 3,148 unaffected named terms.
ReadySet finishes with unchanged heavy sites and exact cached numerical bytes,
but three builder calls fail the unchanged consumption guard. The verified
constructed model remains selected; the endpoint native readback was not run.
Its original REVIEW and decision are preserved, rather than relabeled as a pass.

C77 methods: freeze each already-prepared DP/PDU/5PC dictionary independently and
require one parameterized component per file, exact declared coverage and a
byte-identical recombination to the original combined dictionary. Supply separate
repeatable CIF arguments to the same ordinary helper. Native actions, observer,
resource-query proof, all eight consumption checks, site modifiers and native
qualifiers stay unchanged. The captured input reader registers one returned mol.id
per file and skips objects without id; together with C75/C76 traces this supports
a combined-container registration mismatch. The native parser return type was
not independently probed. C77 stops during staging; returned C78 establishes the
separate-file route below. At C77 delivery, default production orchestration still
supplied the combined path; C79 changes that narrow handoff.

The v2 report separates intentionally excluded serialized outputs from required
portable files. A v1 reader recognizes only exact matching nested exclusion
metadata for absent opaque payloads; no pickle is loaded. Saved preparation replay
also allows the existing 1e-12 bound for duplicated derived determinant/eigenvalue
notes only. Scientific bytes, parameters, hashes and verdicts stay exact. These
are compatibility and argument-transport changes; cache identity and chemical
mechanics remain unchanged. The same verified-start fallback and bounds apply.

C77 consumer transport failure and C78 methods: the reported macOS trace stops
in `stage_review_members` before the native phase, then its exception handler
repeats the long-path lookup. No C77 ZIP was created. The verified C76 archive
has a 939-byte logical member path; Linux transport checks did not impose the
consumer limit. This is transport evidence, not a new chemistry verdict.

Explicit `cif-review-member-transport-v2` stages all accepted members at bounded
hash-derived object paths. Its checked index binds exact logical names, sizes
and SHA-256 values; readers and archive export preserve every original byte/name
and manifest without materializing the historical path. The cached-model action
uses this layout and a shallow prerequisite view selected through the declared
C29 lineage prefix (1,174 files, maximum relative path 281 bytes). The legacy
v1 layout/backup-name exception remains supported, and scientific references
retain their strict validation. No captured Python or opaque backup is executed.

Bulk preservation validation reads each indexed payload once. Incomplete staging
reports false. Failure reporting prints the original exception first and writes
an owned atomic receipt. If complete collection is unavailable, a reduced-scope
failure ZIP retains the receipt and verified input members directly from memory;
it explicitly excludes uncollected outputs and never claims incomplete staging
was preserved. A ZIP-writing failure leaves the receipt and secondary diagnostic.
C78 repeats C77 on exact C76, retaining the same chemical definitions, separate
CIF arguments, native checks and automatic verified-start fallback. At delivery,
fresh Mac qualification was pending; returned C78 is recorded below. Prior failed
directories and runs stay untouched.

Returned C78 closes the explicit whole-model cached-dictionary/ReadySet gate.
The verified 8,741-payload archive preserves the exact C76 parent and manifest.
Phenix 2.2.1-6174 completes one ReadySet control and two fixed native readbacks.
All eight consumption checks pass with no observed builder/template calls and
one source-verified memory query. Before and after each pass 93 checks with only
three unsupported formal-charge readbacks; all 28 roundtrip checks pass. Exact
cached numerics, heavy coordinates, 38 backbone links and 3,148 unaffected named
restraints survive. The automatic decision selects `readyset_checked_model` with
notes. This evidence qualifies the preserved construction control, not an eight-pair
solution or a diffraction experiment.

C79 ordinary handoff methods: after shared source/cache acquisition and existing
normalization, pass the ordered complete component-file tuple (or no input when
empty) to the existing ordinary ReadySet helper. Include cached, curated and
uncached fallback files; do not reselect sources or infer coverage by filenames.
Keep the combined dictionary for assessment/refinement and its existing
`readyset_dictionary_input` receipt reference. Add ordered checksum-bound
`readyset_dictionary_inputs` references and `per-component-files-v1` policy so
receipts identify the operational arguments. Source authority, cache keys,
normalization, generic numerical-generation checks, effective precedence, native
mechanics and NARestraints are unchanged. Local validation passes 139 focused / 4,408 full tests, including five
fail-before cases and source-removed cold ordinary-route checks; no new native cycle is required only to repeat C78's
qualified argument representation.

C80 provides the separate explicitly mapped eight-pair construction fixture.
It starts from the packaged `MR_frames/5W6W/C_G.pdb`, whose twenty disjoint pairs
come from seventeen literal secondary-structure declarations and the three-pair
central stretch. The eight requested replacements bind sixteen unique internal
sites; twelve modified sites require Coot parent overlap and four canonical
partners already have the requested identity. Full annotated chain sequences and
all source/declaration hashes are frozen. Existing free-five-prime preparation
removes ten declared terminal atoms in a separate input; the public source frame
is preserved. The prior DP:C construction control is not reused as pair intent.

| Requested pair | Exact components | First site | Second site |
| --- | --- | --- | --- |
| K:X | CGY:DX | A:20 | D:3 |
| D:T | 1AP:DT | A:5 | C:11 |
| Z:P | DZ:DP | A:12 | B:4 |
| B:S | IGU:IMC | A:6 | C:10 |
| PDU:A | PDU:DA | D:5 | A:18 |
| 5PC:G | 5PC:DG | A:4 | C:12 |
| 5CM:Q | 5CM:S6G | A:7 | C:9 |
| F:A | DF:DA | A:19 | D:4 |

Methods: freeze the fifteen ordinary selected requested-component sources plus
canonical DC for background roles, preserving ordinary authority and priority.
The exact source copies feed the ordinary `construct_postmr_model` entrypoint for
one Coot construction with a deadline of at most 600 seconds. Ordinary Coot
version and embedded-Python validation probes are recorded separately. First
check global atom composition, metadata, unchanged unselected coordinates and
internal-phosphate context. Ten graph-selected sites use the existing independent
connected-fragment or exact whole-raw-site auditor. S6G at C:9 and DF at A:19 use
exact replays of their existing curated placement rules, frozen-parent scaffolds
and declared substitution bond intent. Their existing parent occupancy/B transfer
is checked by exact replay; rigid preservation of raw curated fragments is not
claimed. A separate identity check covers all sixteen requested sites. Audited
whole-raw-site fallback retains notes, while a failed mixed fixture cannot select
its canonical template as though the requested chemistry were built.

The mixed-batch context regression fixes a narrow ordinary-path serial-authority
error: explicitly mutated curated sites join serial collision repair without
becoming graph or OP3 candidates. Frozen passthrough sites stay excluded. Graph
eligibility, shadow coordinates, phosphate-deletion proof and the final sanitizer
are unchanged; the fix authorizes serial fields only.

The new explicit-site compiler uses the pinned NARestraints role table and pair
recipes on the actual constructed PDB. It preserves twelve canonical background
pairs and compiles all twenty pairs. It also emits one mapped parallelity for
each of the thirty-eight declared consecutive-chain relationships, following
NARestraints' existing chain-order policy. Chain adjacency is declared topology;
it is not evidence that a physical stack or covalent link has been observed.
All emitted selectors bind to actual PDB atoms and frozen source graph roles.
Request indices are explicitly `PDB_RECORD_ORDER`, not native capture indices.
Native secondary-structure guessing is disabled in the resulting PHIL.

The earlier sixteen stacking orientations are two plane-order compiler controls
per requested pair. C80 writes them as separate files and never concatenates both
orders into the active policy. They are not sixteen physical stacking edges;
including both orders would duplicate restraints. The requested eight pair
recipes emit 38 angle, 22 bond and eight pair-parallelity requests. Native proxy
membership and achieved geometry are still unassessed.

`80_Cedar_probe_mixed_pairs.py` carries an independent frozen runtime and public
frame; it accepts no historical review capsule and reads no donor observations.
Inspect-only mode freezes the plan/sources without Coot. Fresh mode records one
construction and its PDB-selector compiler evidence, not a fabricated MR result
or completed NASolve run. Relative checksum-bound artifacts support independent
readback; existing opaque Coot-backup transport and first-error/failure capsules
preserve diagnostics. ATL remains an independent public source-graph control.
The mixed-context, existing-context and construction regression passes 53 tests
in 2.05 seconds after the new case fails before the serial-authority fix. Combined
focused validation passes 154 tests in 30.71 seconds, followed by one additional
fixture integration test. The four new files contain 68 cases: twenty-one fixture,
thirty-one compiler, twelve delivery and four mixed-context cases. These groups
overlap and their counts are not additive.

Source-removed inspect-only validation passes with 162 frozen runtime members
and fifty capsule payloads, all subprocesses forbidden, a poisoned ambient import
path, aliased temporary directory and macOS path budgets. A standalone reader
passes after the source clones are removed. It uses fifteen exact ordinary C67
component sources and an explicit synthetic nonnative DC fixture; it establishes
transport and plan integrity, not chemical or native SDK qualification. The full
suite passes 4,475 tests, with two skips and 276 subtests, in 420.39 seconds. One
integration test added after collection passes separately in 1.99 seconds, with
no production-code change; these two runs cover all current test cases. Maintained
C76 and prior-lineage replay also pass with every subprocess forbidden and no
captured Python executed. Actual Mac C80 construction, native dictionary/link/
triple-target/pair/stack membership, ordinary end-to-end execution, observations/
refinement, solution PDF and scientific qualification remain separate. Students
do not inspect or approve CIF tables.







Methods: compare all seven inventoried named chemical fields and the repair
recipe/backend; reassess completed source-relative configuration; require
current isolated native qualification; publish a new entry bound to the selected
raw source/authority while crediting the original numerical producer. Keep the
old entry immutable and freeze both provenance records with relative hashes.
A failed or mutating adapter receives disposable inputs and excludes only that
candidate. A changed consumer requalifies saved bytes first. Optional cache-write
failure retains a qualified run copy. An unparameterized fallback source still
requires ordinary preparation; it is not a native-usability verdict.

Local integration uses actual returned source bytes and saved native data:
all 63 checks pass and six qualified/reused results survive source/cache removal
and relocation, with external scientific reads forbidden. This does not claim
fresh Phenix execution. C68 stops before launch; C69 corrects that layout and
completes all three native reads. C70 replays their exact inputs, worker/specs,
outputs and consumer bindings, recomputes the unchanged usability checks and
finishes the source-bound store/repeat stage. Owned source-layout replay uses
the captured C69 bytes/authority, not a new live installation selection. Separate
dictionary/native triple reports preserve torsion and seed-bending findings.
No captured Python or new native process is executed.
Native guessing stays disabled. Native energy resource files are not inventoried;
current linked/model qualification and production PostMR adoption remain open.
