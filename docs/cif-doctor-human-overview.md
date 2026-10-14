# CIF Doctor: human and manuscript overview

**Implemented scope, 2026-10-14:** offline component/restraint assessment,
report-only PostMR integration, explicit source/candidate comparison and two
bounded preparation recipes, dictionary coordinate-degeneracy checks, and
explicit whole-component numerical candidate generation and a separate native
bundle diagnostic, explicit per-site linked-state preparation and native
qualification checks. The new linked-state diagnostic is software-tested;
its installed Phenix execution remains pending. The [command guide](cif-doctor.md) owns operational
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
operations, with no automatic adoption or PostMR recovery. Their new native
execution remains pending; numerical and stereochemical reviews stay separate.

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
The new native qualification checks still await installed execution. It does not calculate
achieved coordinate geometry or sugar pucker, assess maps, or repair/stitch
fractured assembly arms. Plane-angle discrepancies include raw measurements
and uncertainty-based lower bounds, but a material-strain threshold has not
been calibrated.

The proposed next layers are returned-native qualification and integration of
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
candidate/native-proxy diagnostics; automatic adoption, achieved model geometry
and assembly stitching remain future extensions.
Dictionary coordinate-degeneracy checks and the explicit candidate-generation
scope are included; candidate generation does not add an automatic adoption path.
Explicit generation records installed-tool capability evidence before chemistry.
It requests source-state retention and preserves soft numerical reviews without
granting chemical approval. The v3 diagnostic demonstrated atom/bond/H/formal-charge
retention; omitted metadata and native-link qualification remain explicit.
The separate native diagnostic inventories interpreted atoms/proxies and
parameter handling; it does not add a repair or adoption path.

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
- [NASolve implementation and provenance](cif-doctor.md),
  [scientific audit design](cif-restraint-audit-methods.md) and
  [NARestraints](https://github.com/vecchioni-lab/NARestraints).
