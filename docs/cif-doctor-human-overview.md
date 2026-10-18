# CIF Doctor: human and manuscript overview

**Implemented scope, 2026-10-15:** offline component/restraint assessment,
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
PostMR integration records findings without changing coordinates, selecting new
chemistry or adding a readiness gate. Researchers can also assess a frozen
checkpoint without altering the run.

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
implemented; installed native validation is pending.

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
and synthetic transport are verified; installed Phenix execution remains pending.
This is a new explicit objective, with no coordinate editing or minimization.

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
native mechanics check; existing edits survive, with installed validation pending.

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
