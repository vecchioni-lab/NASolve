# CIF Doctor completion queue

Updated 27 November 2026, after C632. Use this queue to choose the next experiment, the [handoff](development-handoff.md)
to resume it, and the [capability table](cif-doctor.md#current-capability-boundary) for supported chemistry. The [historical index](history/README.md#november-26-cedar-roadmap-audit) preserves the exact earlier
queue, measurements and decisions.

## Pipeline position

The original aim was to catch discrepancies between the intended molecule, the dictionary
selected after ReadySet, and what Phenix actually refines. The ordinary checked route now
delivers the chosen model and restraints. The main scientific gap is deciding when a
corrected chemical definition gives acceptable geometry in the returned structure. In the
PDU controls, switching the diffraction score reversed the local pull on the methyl tip.
The next transfer check examines the locked-sugar contacts on a separate mixed scaffold. [Original blueprint](https://github.com/vecchioni-lab/NASolve/blob/ef83f1b3741f8de2ad074114183ec243ab9b3d2a/docs/cif-restraint-audit-methods.md).

| Job | In laboratory terms | What still closes it |
| --- | --- | --- |
| **Q04 — prepare safely and recover interrupted work** | Coot builds the requested residues; NARestraints supplies their relationships; Doctor checks the dictionaries and ReadySet result. | Complete for the explicit supported route through C284, including repeated native failure, archived-first continuation and serial coordinator controls. Preserve unknown/failed work; broader default activation, migration and deployment capacity remain Q16. |
| **Q05 — give every program the same chosen result** | Coot inspection and Phenix refinement must receive the same chosen model and chemical/restraint meaning. | Complete for recorded alternatives, selected-model phasing, Coot, cold inspection and the ordinary five-cycle refinement handoff. Actual chemical survival/effective restraint behavior is Q06; no default activation or historical migration. |
| **Q06 — show what survives real refinement** | Inspect the whole substituent, sugar, backbone and pair in the returned Phenix model. | The PDU/5PC terminal targets, neutral DF–adenine chemistry and both registered crystal links reached native refinement. The fixed-state PDU test identified opposing local diffraction forces. Keep B:4 in review at 4.19 Å. Sugar/phosphate tradeoffs and endpoint density remain site-specific. Routine metal donor-state integration is deferred under Q13. |
| **Q07 — prove the pieces work together** | Refine the eight named pairs with ATL alongside, including PDU and DF/A1AAZ. | The known thirteen-change scaffold completed two ordinary five-cycle rounds (C497/C505). Both retained all 38 backbone links, 211 frame restraints, protected phosphate angles and original Free-R flags. Two close ATL contacts remain. The separate closure test uses eight unfamiliar catalogue substitutions, including compatible modified backbones and a chemically specified phosphorothioate where supported. |
| **Q08 — explain stubborn distortions** | Find out why a pair or substituent remains strained. | Separate wrong targets, missing restraints, model geometry and packing; do not just optimize longer. Retain the CGY–DX and PDU questions. |
| **Q09 — preserve the correct sugar hand and fluorine geometry** | Carry the L-DNA, FANA, L-FANA and L-FDNA learning into ordinary model building/refinement. | Use atom connectivity and stereochemistry, not lists of residue names; complete linked and held-out controls. |
| **Q10 — handle PNA as PNA** | Respect its backbone and attachments instead of pretending it has a DNA phosphate. | Validate connected construction, native restraints and numerical behavior. |
| **Q11 — transfer the locked-sugar fixes** | Check another alpha-L-LNA example beyond ATL. | Phenix reads both native junctions for 9V9 and TLN in four-residue tests. Find a source-preserving pose that also holds the pair in the complete duplex, then test it against diffraction. 10C still needs a chemically supported leaving group. |
| **Q12 — know the catalogue's actual coverage** | Account for every NARestraints ligand entry. | Turn the 599-code/618-row census into supported, repairable or specifically unresolved cases. A family example does not prove every member. |
| **Q13 — preserve chemical identity** | Keep hydrogens, charge, phosphates and attachment changes chemically justified. | Resolve ambiguous source states explicitly; a prettier geometry cannot authorize different chemistry. |
| **Q14 — make sure Doctor catches real errors** | Test broken examples and sound examples that should be left alone. | Retain reproducible challenge inputs and false-alarm controls, with unavailable historical inputs stated honestly. |
| **Q15 — tell the scientist what happened** | Explain what was repaired or retained, what remains uncertain and exactly what to inspect. | Refresh the ordinary result report and user PDF. Deliver the shared [regional helix analysis](#regional-helix-analysis-for-publication) before NASolve completion. |
| **Q16 — finish the branch cleanly** | Finish with the AutoPhase naming/compatibility change, then check Cedar as part of NASolve and review integration into pine/main. | Preserve Phenix AutoSol calls and old runs; follow the [machine-readable rename audit](autophase-rename-plan.json), then full regression, representative native/relocation/platform checks, honest release scope and reviewed artifact cleanup. No automatic merge is authorized. |

### The next small steps

1. **Q06, PDU checkpoint.** C590 completed the comparison on the same molecular
   state. In both native five-cycle controls, least squares pulled the B:4 tip inward
   at the cycle boundary and maximum likelihood pulled it outward. A direct scattering
   calculation confirmed both directions. The chemical plane stayed active. Keep the
   qualified parent and mark this site for review. Reopen this experiment if new
   evidence can distinguish a better local model. [Fixed-state evidence](backbone-chemistry.md#two-diffraction-scores-on-the-same-pdu-model).
2. **Q06 into Q07, transfer to an independent case.** Reuse the neutral DF–adenine fit and
   the mixed scaffold's two existing five-cycle rounds. Classify the remaining close ATL
   contacts. C591 can retain every printed pair above an explicit overlap cutoff,
   including a second partner at the same atom. Check the existing mixed-scaffold
   evidence described below. The eight-residue design and its sulfur side are now fixed.
   Three modified riboses kept their hand in a five-cycle coordinate fit. Two completed
   ordinary preparation and refinement from a fresh Phaser run. C616 isolated the
   effect of starting all newly placed base atoms at B = 20 Å². C617 now inherits
   verified starting values during ordinary construction. Two sites passed a fresh
   five-cycle run with three of 50 pair distances still outside three widths.
   Resolve the linked OP2 chemistry separately before promoting the panel.
   C618–C619 completed ordinary three-site construction with and without a saved 6MZ dictionary and checked the five-cycle return. C624 placed the fourth substitution with a different sugar attachment. Five cycles retained its pairing edge, both phosphate links and appropriate ring geometry. Carry the demonstrated choices into ordinary construction and test from a cold start. The source-backed internal sulfur linkage remains a later panel site. The four pseudouridine attachment corrections ship in NARestraints 1.1.4. Record what was constructed, what Phenix kept after
   refinement, and which sites require review. The known 13-change scaffold and the
   unfamiliar panel answer different questions. [Mixed-scaffold criteria](#q07--one-mixed-scaffold-ordinary-acceptance-run).
3. **Join the branches on a returned molecule.** Willow/Pine owns strand identity, residue
   numbering, crystal image and recut equivalence. Cedar owns chemical identity and the
   physical bonds, angles and forces. Alder owns metal coordination intent and protected
   atoms, occupancies, displacement and anomalous-scattering settings. Combine them on one
   declared parent with the same Free-R assignments, density provenance, effective
   dictionaries, ordered restraints and returned atom identities. Check that an unselected
   child reopens after relocation. Source the final diffraction statistics and checkpoint
   from the existing workflow. Keep a hydrogen-bond restraint and a real covalent link
   distinct when writing deposition metadata. [Q06 crystal links](#crystal-phosphates-after-an-asymmetric-unit-recut) · [OneDep verification](pdb-deposition.md).
4. **Q08–Q16, qualify and deliver.** Carry the family-specific evidence forward using
   graph, attachment and stereochemistry. Report each unresolved catalogue case explicitly.
   The regional twist/radius readings belong in the shared post-processing work. Choose the
   supported release scope, complete the compatible AutoPhase rename last, and qualify the
   combined source before merge review. [Transfer gates](#chemistry-transfer-and-coverage-packages) · [Release gates](#q16--final-integration-portability-and-retained-artifact-closure).

Use the same prepared checkpoint, map sampler, protected-atom definitions and reflection
selection wherever the branches ask the same question. A working-only reflection list does
not by itself establish which reflections estimated an upstream map's weights. Record that
provenance before using a density result to choose a pose. Keep negative and ambiguous
results linked to their original experiments.

## Finish line and ordering

CIF Doctor should work quietly behind NASolve: preserve the intended chemistry,
catch bad dictionaries, repair what can be repaired, and give Phenix a model and
restraints that agree. Routine users should not have to edit CIFs. ReadySet and
NARestraints remain the tools that supply chemistry/numerical parameters and the
intended base-pair/stacking restraints; Doctor checks and connects their results.

Q01–Q03 are complete within their recorded diagnostic scope. Q04/Q05 have
completed the supported explicit-route preparation, recovery and chosen-input
handoff acceptance through C284. Q06 is next and must pass before we claim that
the combined chemical examples refine correctly. Q08–Q14 retain the chemistry
learned along the way; they are not a reason to keep rebuilding Q04.

## Q04/Q05 acceptance and supported boundary at C285

**Complete for the explicit checked route and recorded controls.** This closes
preparation/recovery and delivery of the chosen model/restraints; it does not
approve every modified chemistry, enable defaults or authorize a merge. C276's
normal campaign runs preflight, Phaser, Coot/NAR and checked ReadySet. C277/C278
close first-refinement admission and the full-model interpretation setting;
C279 completes AutoSol and five actual refinement cycles, then reads its chosen
endpoint after relocation. Its original Free-R source, seven restraint inputs
and explicit D:1 terminal-phosphate protection remain intact.

| Acceptance | Evidence |
| --- | --- |
| Preserve the intended molecule and independent fallback | Existing C184/C219 complete owner; C244 owned source-supported plane acquisition; C248 mixed child outcomes and uncertain-process refusal; C252 native optional failure followed by fresh success. |
| Recover without overwriting earlier work | C258/C260 interrupted retirement; C274/C275 exact sealed AutoSol save after verified process/group stop; old attempts and newer choices remain intact. |
| Account for repeated failures | C280 executes the second native attempt under unchanged frozen allowance; both unqualified results stay preserved, a third refuses exhausted allowance, and publication/retirement refuse. Moved cold reads retain every original and failed file. |
| Continue after successful working files were archived | C282 executes a second preparation after an archived first, publishes it unselected and retires only eligible new duplicates. All 207 earlier campaign references remain valid; current choice stays postmr. |
| Deliver exactly the chosen result | C251/C252 alternatives; C270–C272 selected-model anomalous comparison/Coot; C276–C279 ordinary preparation through actual first refinement and relocated endpoint inspection. Broader chemistry is Q06. |
| Keep serial campaign bookkeeping practical | C281/C283 run 100 synthetic datasets, preserve 50 failures, prepare 50, and allocate two explicit fresh retries without changing earlier runs. Stage-scoped checks reduce initial hash reads from 651,504 to 13,104. C273/C284 reuse only identical pure calculations within one read. |

**Supported recovery scope.** Use explicit checked PostMR/prepare-run/schema-2
campaign policy, frozen requests and exact numbered results. New attempts require
known-stopped previous ownership and remaining frozen allowance. A qualified
fallback may continue useful work; an unqualified result blocks its dependent
stage, not unrelated campaign datasets. Sealed AutoSol save completion is supported
only after the recorded producer and group are known stopped. No default-route
activation or historical migration follows from these controls.

Pre-seal/unfinished AutoSol work, unknown/shared/foreign groups, missing outer
campaign receipts and old unarchived campaign references are preserved and not
automatically adopted. Standalone AutoSol has no isolated child owner; campaign
supervision remains the supported owned path. These explicit limits remain in
Q16's release decision; do not silently retrofit receipts, retry in place or add a
second process/chemistry owner. Future broader recovery is a separately reviewed
extension, not an excuse to repeat this completed integration.

**Laptop operating envelope.** Keep campaign execution serial and use one expensive
scientific reader at a time. Independent developer Phenix CLI jobs may overlap
when inputs, working/output folders and process records are isolated; coordinate
CPU/RAM and deadlines across agents. This does not enable concurrent campaigns.
Current whole requests measure 35.1 MB for one archived
success, 65.7 MB for two archived successes, and 70.7 MB for two preserved native
failures. A historical unretired PDU two-attempt request retains 315.3 MB. Shared
acquisitions, failures and continuation are included. C282's request falls from
191.9 MB to 65.7 MB; all original/failed science remains local and preserved.

For scale only, 100 copies of the measured one-success or two-failure requests
would be about 3.5 GB or 7.1 GB. These are arithmetic estimates, excluding raw
inputs, other stages and peak native scratch—not a 100-native-dataset experiment
or guaranteed capacity. C281/C283's 100-dataset test uses tiny synthetic stage
outputs. C282's sampled descendant RSS peaks around 635 MB; sampled/shared-page
counts are not an upper memory bound. Retain existing 128 MiB physical replay
expansion limits. No automatic failed-output deletion or new storage allowance.
Explicit campaign retry deliberately creates a new run/request allowance; there
is no fixed campaign-wide retry or byte cap. Deployment capacity remains Q16.

Exact controls and commands live in the existing evidence ledger:
`repeated_failure_resource_acceptance_2026_11_14`,
`retained_first_attempt_native_continuation_2026_11_14`,
`serial_campaign_resource_acceptance_2026_11_14`,
`campaign_stage_integrity_scope_2026_11_14`,
`owner_inspection_numerical_reuse_2026_11_14`, and
`q04_q05_supported_scope_2026_11_14`. C391/8ccec55b's historical full result is
11,983 passed, 2 existing native opt-in skips and 292 subtests. Current qualified
source and pending candidates are recorded once in the maintained handoff; this
historical result is not their qualification. Final combined integration still
needs its own full regression.

Q06 still owns effective native membership, known parallelity-gradient behavior,
scientific targets and achieved geometry. Simon’s report of distorted PDU prompted the matched controls above.
The original collaborator files are parked by agreement. The evidence for Q06
comes from refining the prepared molecule and measuring its final geometry. Keep ordinary bond edits distinct
from additive contact energy over an unchanged native manager: Linden's reported
Willow evidence shows changed exclusions from symmetry distance edits. Willow
W38/W39 are context, not a combined Cedar validation or a phosphodiester-link grant.
**Shared live-policy guard implemented (C331); optional consumers qualified on Willow:**
The opt-in read-only owner now guards complete supported tables, assignments,
exclusion shells, exact symmetry and evaluation settings under the pinned native
API. Actual native tests catch copy loss and permit legitimate movement/reset
rebuilds; installed-package checks include its profile. See the
[guard contract](architecture.md#live-nonbonded-policy-guard-c331) and ledger
`live_nonbonded_policy_guard_2026_11_16`. No ordinary worker/default or chemical
target changes. Linden reports W96/c6549408 qualifies the direct optional caller,
keeping actual flags, source/ASU/bonded owners and original errors. W97 also reports captured-
worker closure/installed relocation qualification; no combined-source merge. This does
not approve native copies, neighbour completeness or Q06 geometry. Return to
automatic request delivery of source-aware proposals and honest remaining-geometry
reporting; preserve C329's corrected-CIF evidence rather than rerunning it without a new hypothesis.

**Source-aware discovery and request delivery (C332/C333):** read-only source/
library discovery identifies supported differing targets; explicitly opted-in
Python preparation now freezes that intent and the exact per-attempt proposals.
It reuses attribution/selection/ReadySet, immutable recovery and v4 storage. Empty,
matching, unsupported and nuclear-reference cases stay honest; no proposal is not
chemical acceptance. Installed PDU delivery/ReadySet and archived cold relocation pass; exact
native/focused/installed validation is in the handoff and existing evidence ledger. No new executor, reference model, ESD change, CLI flag
or ordinary default. Do not rebuild this path to add a residue-specific fix.

**Next Q06 boundary:** report what remains distorted after the chosen dictionaries
reach refinement, preserving the C329 finding that a correct target can coexist
with PDU's residual bend. Reuse its exact model/restraint/force evidence before a
new experiment; distinguish wrong targets, effective restraints and competing
forces. C421 completes the held-out 5PC example. Judge the wider whole-substituent claim using scientifically
justified criteria, not stronger restraints chosen to force a pass. Prior-work check found that `cif_construction_native._triple_readback` already
scopes a declared heavy-atom projection to one native site (introduced at
`94ababa1`, with PDU/5PC/Q17 and duplicate-site controls). C334 replays C329 using the frozen linked B:4 projection instead of the full
runtime CIF: all 22 heavy atoms match, the isolated-versus-linked OP3 warning
clears, and the genuine terminal-side bend remains REVIEW with identical
measurements. All 190 old files are unchanged; no native rerun. C338 completed
ordinary final-refinement reporting through the existing compact
actual-manager observation and projection binding; its separate five-cycle control
still reports the genuine PDU bend as REVIEW. Reuse that completed report, rather
than rebuilding it or pruning atoms to match observations. The new counted route's
whole-model publication binding remains a distinct prerequisite above.
Later ordinary CLI/campaign exposure and default/release scope belong with Q15/Q16; a numerical
repair or delivery pass does not close Q06. See the
[request contract](cif-doctor.md#automatic-bond-discovery-in-fresh-preparation-c333).

**Queued representative-boundary alternative (Linden W79/W80):** W79 reports
that outlier callbacks can mix source and displayed coordinate frames even when
scalar energies agree; W80 qualifies tensor transport in its own Willow controls.
A narrower possible integration is to retain one complete computational native
model and derive the displayed/exported representative only at the workflow
boundary. Require exact per-atom operators/identity and tensor bindings, immutable
source/derived artifacts in checkpoint lineage, and traceable scientific reports.
Manual edits to a derived Coot model need checked inverse mapping; new/deleted or
renamed atoms and changed intent cannot borrow the old map. This is a design
alternative, not an activated route, a standalone recut-PDB qualification or a
solution to missing-link/winding-seam chemistry. Keep its evidence in Willow and
compare it with in-engine adapters before choosing an integration. Do not derail
the current target-repair work or rebuild completed Q04/Q05 owners.

Q07 retains mixed and held-out tests; Q08–Q14 retain chemistry learning, followed
by Q15 reporting and Q16 integration/AutoPhase/release. No automatic merge.

## Integration packages

### Q01 — Compose full native capture and numerical attribution

**Complete at C151: native identity/capture compatibility. Dependencies: none.**
C133–C141 require complete full-model monomer identities for source-qualified
selection. C147–C150 initially rejected this richer capture. C151 validates the
existing full-monomer request/worker/proof, retains it in fresh derivative and
geometry jobs, and requires it in endpoint readback. Maintained attribution now
consumes the same full capture without stripping metadata. Three fresh native
stages preserve all 42 residue identities/865 atoms and C150 numerical inventories;
six-proxy attribution, derivatives and bounded geometry mechanics pass. Legacy,
copied-chain, rehashed tamper and cold-relocation controls pass. No independent
source-chemical approval or automatic selection is claimed; that remains Q03.
See the [C151 contract](cif-doctor.md#full-native-capture-bridge-c151).
Relevant seams: [captured gradients](../src/nasolve/cif_captured_mixed_gradients.py),
[maintained attribution](../src/nasolve/cif_captured_linear_attribution.py) and
[component runtime](../src/nasolve/cif_component_runtime.py).

Acceptance retained: one exact full-model bundle passes captured source/site identity and maintained
repair-attribution replay together, including unchanged sites, ordered CIF/PHIL
inputs and native source pins. Test legacy captures, extra/contradictory monomer
data, copied-chain identities, tampering and cold relocation. Old capture schemas
must retain their existing meaning; no fabricated missing evidence.

### Q02 — Read curated CIF loops independently of line wrapping

**Complete at C161.** C145 exposed a valid projected-DZ dictionary that the
physical-line bond reader rejected. Both curated bond and ideal-coordinate
readers now reuse existing CIF1 block/token parsing, preserve exact identifiers
and coordinate preference, and refuse incomplete/ambiguous/conflicting tables.
All ten curated resources retain topology under token-per-line and mixed-width
layouts; ordinary PostMR fixture preparation accepts wrapped DZ. The exact C145
input now validates all 35 bonds and its C-glycosidic distance, without changing
parent bytes/timestamps. 42 new cases and affected/focused workflow checks pass;
no native run or full regression is claimed. See the
[C161 contract](cif-doctor.md#curated-cif-loop-parsing-c161).

### Q03 — Qualify repaired dictionaries and select a usable bundle

**Complete at C153: diagnostic source/repair selection and publication.**
C152 implements the read-only source/preparation → repair-attribution → derivative
decision. C153 supplies a positive matching native chain and freezes its complete
proof under a distinct public runtime policy. Exact-source saved PDU/5PC candidates
retain phosphate H/charge and sugar configuration. Two complete separated monomers
(77 atoms, one explicit NAR numerical parallelity request) pass source/site/full
native gates, twelve declared-linear torsion omissions, exact attribution and fresh
derivatives. Public API/CLI rederive the repaired choice after relocation without
original inputs, cache, SDK or execution. A separately qualified original remains
the fallback; absent or malformed proof never grants usability.

The demonstrated control is not the 42-residue mixed scaffold, a physical pair,
ordinary refinement or a new experimental phosphate-state choice. The retained C98
source and C151 numerical bases still differ in HOP2/HOP3 and OP2/OP3 charge; Q13
owns explicit authority for that state transition and Q07 its ordinary integration.
No old evidence is upgraded. See the
[C153 contract](cif-doctor.md#source-faithful-repaired-runtime-publication-c153).

Acceptance met for this package: source-qualified repaired dictionaries can be
selected and immutably published with exact source/native/derivative proof,
without adopting an unconverged coordinate trial. Cold native replay, synthetic
fallback/refusal controls, rehashed tampering, altered order/resources, missing
proof and concurrent-source changes are tested. Automatic acquisition is Q04;
ordinary adoption is Q05 and the actual refinement consumer is Q06.

### Q04 — Bounded automatic recovery and durable attempts

**Accepted for the explicit supported route through C284.** C220–C225 provide
preparation, publication and ordinary entry; C244–C249 connect owned plane support;
C258/C260 retain successful evidence; C274–C278 close the exposed caller/recovery
gaps. C280–C284 supply repeated-failure, archived-first continuation and serial
resource controls. The supported boundary above is authoritative. Default
activation has not been authorized and is not silently implied by a native control.
In lab terms: preserve the intended molecule, get a checked model/restraint set,
and resume interrupted preparation without rebuilding or damaging earlier work.

Already implemented and to be reused:

- Coot construction preserves the recorded source and requested sites. The
  prepared model and chemical intent travel together into the request
  ([construction record](cif-doctor.md#ordinary-construction-lineage-and-request-binding-c196)).
  C218 shares this normal construction/NAR route instead of repeating it in a
  diagnostic script. C217 preserves the selected Phenix installation.
- The existing request handles local dictionary reuse, generation when needed,
  native checks, repair and ReadySet. It freezes the source/recipe/tool evidence,
  uses one bounded allowance and preserves every partial output. A fresh attempt
  requires all earlier processes to be known stopped. Unknown ownership blocks
  further work; it is not a chemical verdict.
- The supplied NARestraints relationships, exact selected atoms, weights and input
  order are retained. Source-bound literal intake and an existing compiled policy
  are alternatives through the same compiler/owner, not permission to invent
  another compiler or infer missing pair relationships. Unsupported inputs refuse.
- Optional failure can retain a starting model only after independent checks of
  that model and its matching restraints. Corrupt evidence, initial qualification
  failure or uncertain cleanup never becomes permission to use it.
- C219 executes C218's ordinary PDU request through fresh generation, connected
  repair and ReadySet, and rereads the exact result after relocation without the
  original paths/SDK. This is complete preparation evidence, not diffraction
  refinement. C220 exposes [plain-language commands](cif-doctor.md#checked-preparation-and-honest-recovery-c220)
  for fresh preparation, status, exact result and fresh-attempt continuation.
  It reuses the same reader once, preserves ordered model/CIF/PHIL inputs, and
  checks the expected prior attempt number under the existing lock.

Acceptance evidence is summarized once above. The durable contracts remain:

- Reuse initial/later checkpoint publication and ordinary/schema-2 campaign entry;
  a checked fallback carries its genuine preparation receipt, without fabricated
  ReadySet success. Preserve old request meanings and exact replay.
- Source-supported plane completion reuses the existing generation and repair
  owners, exact child identity and shared allowance. Completed chemical rejection,
  stopped optional failure and uncertain ownership remain distinct. Corrupt or
  unknown evidence never authorizes fallback. Do not infer new chemical authority
  from a native exit code or a prettier model.
- Retire only eligible, independently qualified successful working duplicates
  after exact reread and durable archive/intent. Keep public models, ordered CIF/
  PHIL inputs, shared acquisitions and every failed/active/unknown attempt.
  Historical campaign references to working files require separate migration.
- Reconstruct archived evidence within the existing 128 MiB physical expansion
  and nesting/file limits. Revalidate all history on reads; scope numerical reuse
  to identical input bytes within that read. No persistent scientific trust cache.
- Preserve fresh immutable attempts, frozen allowance and known-stopped ownership.
  C280 refuses a third request attempt; explicit campaign retry instead creates
  a new numbered run with its own request, preserving the old run completely.

Earlier C228–C278 acceptance chronology and measurements remain in Git history,
the methods and exact ledger records; they are not new unfinished tasks.

**Chemical-plane holdover — implementation connected; consumer acceptance is Q06.**
C208–C216's checked plane-completion machinery now has C226 maintained numerical
execution and C227 source-bound composition. C234–C239 now invoke these through
explicit owned support in the same immutable repair request. C242 freezes supplied
completed support in the outer request and passes actual ReadySet/cold readback.
C244 adds explicit automatic acquisition inside the outer request: exact
source/recipe/child identity, one numbered generation attempt per needed type,
shared time/attempt allowances and separately qualified handling of classified
optional failure. Unknown/malformed ownership cannot authorize that fallback.
C245 freezes/forwards the option through prepared/ordinary intake and prepare-run.
C246 connects explicit checked PostMR/campaign entry; C247 carries generation notes
through publication and campaign status. C249 reports scoped explicit selected-CIF
planes without claiming effective native adoption; absent intent keeps its meaning.
Recovery/storage acceptance is recorded above; native consumer chemistry remains Q06.
C248 adds mixed sibling controls: support/rejection in either component, a stopped
interruption retried in a fresh outer attempt, and an unknown partial reservation
that blocks retry while preserving the successful sibling. These pass through
existing production ownership; the generation/repair transport is synthetic.
They do not establish native mixed-chemistry or diffraction-refinement support.
C232 already permits an actual parent grant below the frozen generation maximum.
C240 proves exact launched negative generation; C241 removes the acquisition
recipe-identity mismatch; C243 proves completed source-chemical rejection through
full replay. These readers classify outcomes; C244 invokes the existing owner
and consumes their proofs, which still do not authorize fallback by themselves.
Use that existing owner; do not raise bounds or alter historical requests.
Then demonstrate the resulting restraints in Q06; a flat
starting PDU substituent does not prove that refinement will keep it flat.

**NARestraints stacking and Cedar chemical planes have different jobs.** The
installed NARestraints v1.1.3 (`a9264f9eb4ec6071a4b4cd5356bec2b8b58b5691`),
`restraints/stacking.py` and `restraints/phenix.py`, uses reviewed base-role atom
sets resolved through workbook mappings for modified-base stacking parallelity.
These sets include some mapped exocyclic atoms, not just ring atoms. Canonical
neighbors use Phenix's ordinary stacking path. Keep those reviewed selections;
Cedar's plane completion must not automatically enlarge the stacking selections.

Cedar repairs intramolecular dictionary planes: preserve each existing ring plane
and add only chemically supported missing members, with supplied restraint weights
and the existing source/native/numerical checks. The current rule covers explicit
neutral three-heavy-neighbor carbon with one double and two single bonds; it is
not a universal aromaticity or appendage-flattening rule. Do not flatten flexible
or tetrahedral groups, merge distinct planes, or infer chemical authority from
coordinates alone. The native inventory check must preserve NAR parallelity and
all unrelated restraints while allowing only the declared component-plane change.
See [coverage](../src/nasolve/cif_plane_coverage.py),
[candidate construction](../src/nasolve/cif_plane_candidate.py) and
[native comparison](../src/nasolve/cif_plane_native.py).

An unfamiliar base still needs correctly mapped, present, non-collinear atoms
that represent its intended base plane. NAR's selector requires at least three
mapped names; that count alone does not prove model presence or geometric rank.
Its warning plus generic stacking fallback is not proof of a working modified-base
stack. Retain those checks in Q06/Q07/Q12 rather than making plane repair a second
stacking generator. Existing reviewed atom sets need no automatic expansion just
because Cedar repairs a substituent's chemical restraints.

Known scientific limits stay in the existing jobs: DP correspondence is ambiguous;
nonstandard backbone/site adapters and H/charge/attachment authority need their
own evidence. PDU C5 plane completeness, its numerical target and 5PC source-H
questions are distinct. The full-model controls use different frozen pair/stack
intent and cannot substitute for one another. C191's isolated eight-DA refusal is
not a blanket Phenix/DA verdict; C198/C203/C219 establish other exact contexts.

Detailed C155–C219 evidence and resolved intermediate refusals remain in the
[methods](cif-doctor.md#complete-frozen-dictionary-requests-c171),
[ledger](cif-linked-native-registration-evidence.json) and
[prior queue at its exact commit](https://github.com/vecchioni-lab/NASolve/blob/654328105f193f25011fe927dc1db860cb82bca0/docs/cif-doctor-completion-queue.md#q04--bounded-automatic-recovery-and-durable-attempts).
Do not reopen completed intake/compiler/process work merely because an old note
called it the next step.

### Q05 — Ordinary PostMR continuation and immutable adoption

**Accepted for the explicit route and recorded controls through C284.** C221 checks
the complete restraint set before inspection; C222 opens an exact checked preparation without adoption. C223 now
publishes that exact choice as the initial REVIEW checkpoint, including a verified
fallback. Ordinary inspection, refinement and AutoSol readers validate the saved
producer/compiler/result binding. New manual/refined models preserve its ordered
restraints and checked phosphate connectivity. Malformed entries cannot silently
disappear; movement cannot silently sever a recorded phosphate connection.

Interrupted publication resumes under the existing request lock using the same
sealed receipt and exact attempt; no native rerun, newer-file guess or reselection
occurs. C223's initial schema-3 command was explicit; C224/C225 later connected
that publication to explicitly configured ordinary/campaign preparation. C278 now
has one actual refinement control. These later checks do not retroactively change
old receipt meanings or migrate legacy registries.

**C224:** `postmr --checked-preparation` now composes construction, one existing
owned attempt and exact publication, with honest fallback reporting and one proof
read at publication. Default preparation and campaigns remain unchanged.

**C225:** schema-2 campaigns can freeze `postmr.checked_preparation = true`.
The stage reuses ordinary checked preparation and records its actual ReadySet
outcome and genuine evidence. Campaign retry still starts a fresh run; standalone
recovery does not manufacture an interrupted campaign stage receipt.

C231 verifies that a real new compact request can use the same initial checkpoint
publisher and ordinary inspection/refinement-input readers after relocation.
Synthetic observation/map path fixtures test this handoff, not native MTZ reading
or diffraction refinement. Reuse that result rather than repeating construction.

C250 first protects checked-registry writes against stale snapshots: compare the
sealed registry identity under the existing kernel lock, preserve newer work on
conflict and refresh the live identity after success. This fixes an observed
lost-update risk and supplies the guarded save used by C251 alternatives.

C251 implements explicit later alternatives from the same frozen construction,
with schema-4 receipts and exact Coot/refinement readers. These are not claimed
coordinate descendants of a selected refined model. Interrupted saves preserve
intervening bookmarks/selection, and the sealed observation anchor now survives
dataset renaming. A single history replay supplies all published choices.
C252 executes actual stopped optional generation followed by a fresh successful
attempt, then publishes both choices without replacing the initial one. Relocated
Coot and AutoRefine input reads retain the exact selected model, five PHIL files
and two CIFs. Manual import/explicit selection and repeat publication preserve
the subsequent choice and all preparation files. A second relocation after manual
import also resolves the current child with its historical source path absent.
No native Coot edit or diffraction refinement is claimed; observation/map paths
are synthetic fixtures.
C253 retains the original Phaser model as phasing input and binds anomalous-site
validation to the chosen model's candidates/unit cell. Schema 5 and an immutable
site-reference/result let ordinary phase/map consumers verify that comparison
without changing the initial preparation or later selections. Focused controls
cover alternatives, manual choice, relocation, native failure and conflicting
publication. No automatic campaign continuation or native refinement claim follows.

**Native acceptance:** C270–C272 complete selected-model native AutoSol,
later-selection/relocated inspection and final native Coot loading for the explicit
A:5IU fixture. C273 reduces duplicate numerical work within exact inspection.
C274 closes **explicit completion of a sealed phasing result save**: new checked
launches observe their existing producer/group, bind the completed result and
intended report, and finish only after both are known stopped. A fresh complete
Phenix run, deliberate save interruption, relocation and repeat completion pass;
later selection survives. No new executor, child group or scientific validator.

Remaining recovery scope must stay visible: an interruption before the publication
receipt, unfinished native work, a shared/foreign/unknown group and a missing outer
campaign-stage receipt are not automatically adopted. Direct AutoSol still lacks
standalone isolated child ownership; inherited campaign supervision is unchanged.
Old unowned partial directories remain visible and unadopted. No guessed process
death, in-place native retry or fabricated campaign success. These are the explicit
supported-route exclusions above and Q16 release limits; reuse these owners rather
than starting another recovery stack.
C255 has separately reconciled Alder's exact HL phase-label fix into Cedar, with
unchanged native arguments and a real read of the documented DiU MTZ. This closes
the known phase-label correctness discrepancy on Cedar; C270 now supplies native
selected-model acceptance. The final AutoPhase naming task remains Q16.
For the anomalous-site connection, preserve these distinctions:

- The original Phaser model remains the phasing input; changing it to the
  modified preparation would alter the scientific protocol.
- Candidate heavy-atom coordinates and unit-cell context must come from the exact
  chosen model. Replacing only the model path would leave the old coordinate list.
- Save the chosen checkpoint/model identity and checksums through declared anchors;
  verify them when phases/maps are later consumed. A newly written field that no
  reader checks is not provenance. Preserve legacy meanings and refuse unsupported
  authority rather than silently ignoring it.
- Keep acceptance/review distances, source chemistry and Free-R rules unchanged.
  A later manual/refined descendant needs its own exact-model validation; do not
  relabel it as a fresh preparation from frozen construction.

Reuse the existing request owner and publication path;
do not build another recovery or chemistry framework. Preserve normalization and
anomalous metadata where actually available, without inventing ReadySet success.
Exercise cache reuse, missing/stale entries, repair, usable fallback, unqualified
failure and interruption through the real callers. C225 tests establish campaign
handoff/frozen intent, not fresh native execution of every chemistry outcome.
Reuse the existing constructor/continuation/publisher without rerunning Coot on
partial work. No default activation or broader chemical eligibility follows.

Optional failure should preserve a trustworthy model/restraint set and allow
useful work to continue. If no safe set remains, block only its dependent scientific
step while retaining reporting and recovery. Actual complete-restraint refinement
remains Q06; initial publication does not close that job.


The combined metadata writer now shares C09's native loop policy (C179), with
strict fresh endpoint acceptance and preserved legacy outcomes. C180 extends the
same writer to both partial-filter precedence directions, with actual native
before/after isolation and cold replay. C181 closes the explicit **selected
original/repaired runtime → ReadySet → exact native → public bundle** bridge.
Actual original and C140-restored repaired controls pass. Raw display-padding
mismatch, explicit-H change, missing evidence and timeout retain the exact selected
parent; a pre-repair baseline cannot authorize an endpoint. All historical choices
remain unchanged after relocation.

C182 derives current-installation settings without borrowing old test configuration.
C183 owns one immutable continuation execution and schedules at most one existing
lossless C140 correction, qualified by a fresh native endpoint. All five live controls
and complete cold replays pass. C184 binds it to the existing complete-request owner,
including interrupted/unknown child recovery, shared elapsed allowance and immutable
previous outputs; actual fresh recovery and optional repaired fallback pass.
C223–C225 and C276–C278 subsequently connect ordinary callers/checkpoint publication
and the recorded normal native refinement control. Do not reopen that completed
integration because an earlier milestone called it the next step.
Preserve pre-construction source/producer lineage and exact NAR intent. No second
recovery owner or unqualified pre-repair fallback should be introduced.

Done when recipes/models containing modified components reach final ReadySet
consumption and exact native qualification through ordinary entry points, then
publish one internally consistent selected model/CIF/PHIL/checkpoint. Cover newly
mutated and already-present residues, partial failure, valid fallback, latest
versus selected inspection and replay without historical host paths. Do not mix
an older model with newer dictionaries, rewrite a prior checkpoint, or promote
report-only findings into unreviewed universal gates.

### Q06 — Qualify the actual refinement consumer

The [next comparison](#the-next-small-steps) uses the completed C586–C589 observations. The dated entries below preserve the scope of individual controls. [PDU chemistry and cycle-by-cycle evidence](backbone-chemistry.md#when-the-b4-tip-left-the-ring-plane).

#### Crystal phosphates after an asymmetric-unit recut

**The first ordinary numbered restart is complete (C548).** On a separate copy
of the PDU:PDU run, ordinary AutoRefine fitted the named manual child for five
cycles. The B7 O3′–B1 P bond finished at 1.638 Å in its registered image.
The seven inherited restraints, eight native linkage terms and original
work/free assignments were verified. The fitted child is available for review.
The previous selection and earlier checkpoints were preserved.

**The relocated second fit is complete (C549).** The saved construct
declaration and fresh native capture of refine-006 produced refine-007.
After five cycles the bond measures 1.642 Å, with O3′–P–OP1/OP2 at
104.90°/114.12°. All 124 original free flags survived. The saved-continuation
inspection reads each child's own applied forces and final coordinates.
A missing declaration or a different starting model's receipt stopped before
creating the next round.

**Stress-test the shared method in stages.** Pine records the designed
continuation and its exact crystal operation through a recut. Before any
refinement, check that the new asymmetric unit gives equivalent scattering,
strand chemistry and pair assignments. Willow then fits two registered cuts
together using Cedar's single set of forces per junction and checks them in
a fresh restart. Exercise the existing rotated or screw-related examples,
a cell translation and a displaced starting junction. A true nick stays
open. An ambiguous partner requires review. Check both nonbridging oxygens,
nearby clashes, handedness and the original free set after motion.
Willow's [coordinated roadmap](https://github.com/vecchioni-lab/NASolve/blob/willow/docs/topostitch.md#coordinated-phosphate-recut-follow-up)
owns placement and recutting. Space group alone cannot establish bond intent.

**Check phosphate direction before and after stitching.** The 5LNA
source already had an inward-facing A111→A112 phosphate before the
sequence-contiguous recut. Both newly chosen crystal boundaries pointed
outward. Cedar owns the chemistry reading and a bounded comparison of
alternative backbone poses. Pine/Willow owns the same-image comparison
across a change of representative. Check both ester bonds, local sugar
geometry, nonbridging oxygen directions, clashes and handedness after a
real refinement. Include a true nick, a crossover, a labelled-oxygen
swap and a stereospecific substitution among the controls. A physical
repair and a change of labels require different evidence. [Scientific
scope](backbone-chemistry.md#checking-the-direction-of-a-repaired-phosphate).
Use deposited 5W6W and the six standard W templates as the inward/outward
A12 controls. The archived DF–Hg–DT and PDU:PDU inputs inherited different
poses. Two matched five-cycle metal refinements retained the two opposite
A12 directions. Correcting the local sugar angle also compressed the
neighbouring pair and increased final free R. Keep the outward child as
a comparison. `phosphate-image --duplex-partners` can now measure each
model and named checkpoint. The future automatic intake needs an assigned
continuous duplex arm and a separate chemical and diffraction comparison
before adopting any repaired metal model.

**Read the processed deposition separately.** A returned model preserved all
ordinary steps while omitting the two declared crystal links. Its validation
report assigned those two covalent distances to symmetry contacts. Compare
the uploaded and processed coordinates using the existing deposition reader.
Carry the missing records to biocuration and check the next returned model.
Routine adoption awaits that external outcome and the scientific stress tests.

C573 now reads the written final PDB and the actual Phenix bond and angle
targets for any named residue or the whole model. The PDU test covered
924 bonds and 1,323 angles across 42 residues. An independent FT–Hg fit
exposed a starting-versus-final GEO mix-up and verified the final table
across its 42 nucleotide residues. Empirical wwPDB targets and reslice
correspondence remain separate work. [Native geometry screen](cif-doctor.md#checking-bonds-and-angles-in-the-refined-model)

**Queued for Cedar and Willow · check ordinary DNA geometry before upload.**
Cedar should screen every standard nucleotide in the final coordinate mmCIF,
including atoms held fixed during refinement. Use the applicable wwPDB reference
for bond lengths and angles. Report the residue, atoms, observed value, target,
standard deviation and Z score. Willow should run the same check before and
after reslicing, matching the same physical atoms across crystal copies so an
inherited outlier can be distinguished from one introduced by the move.

The first control is the saved 5LNA OneDep return. Recover its three long sugar
bonds and three angles (two thymine N3–C4–O4 angles and one O5′–C5′–C4′ angle)
across four ordinary residues. The corrected A112 sugar angle should clear.
Use the existing [deposition checks](pdb-deposition.md) for the two genuine
symmetry phosphodiesters. This item is a read-only audit before submission.

Use the passed 3LNA and 5LNA entries as paired controls for this Cedar/Willow
milestone. The [deposition guide](pdb-deposition.md#what-the-locked-dna-depositions-established)
records the observed outcome and the distinction between local candidates and
an identified submission. Extend the same read-only check to modified sites
using their actual component, stereocentres, base attachment, ring closure and
both polymer neighbours. Report standard-library and component-specific
targets separately. Preserve the source and parameters of each target.

The downstream constructor should first try the supplied definition on the
existing scaffold. Where local refinement leaves a cage distorted, compare
a reference-supported connected pose with the unchanged parent. Verify the
two sugar–phosphate joins, chirality, nearby pairs, stacking, displacement
and the same free reflections after releasing any temporary coordinate holds.
Record which improvements survive release. Leave selection with the operator
where the maps allow multiple poses. Willow owns the identity and images
across a recut. Cedar owns the chemistry checks on the written model.

**Alder final-stage reporting holdover (2026-11-17, `ccb5e769`):** a passive exact-
endpoint replay localizes one DF child's final R/B shift inside native
`update_all_scales`. XYZ, occupancy, fp/fdp, phase probabilities and F_mask remain
unchanged; scales/F_calc/B and scaled observations change. The final synchronized
model is not the earlier cycle's printed R/B state. Reuse Hazel's compact staged
receipt before attribution; no isolated backtrace/mask/scaling cause or native bug
is established. Do not alter weights/targets or promote the endpoint to hide it.

**Current consumer route through C307:** `autorefine --checked-plane-forces`
explicitly uses the qualified local Phenix implementation, complete ordered plane
parameters and the existing immutable AutoRefine/checkpoint owners. Actual
zero-cycle model setup precedes refinement and has separate outputs. Corrected
ancestry, including manual children, cannot silently drop the correction. C298
passes five cycles and relocated cold reads; C299 passes actual CLI continuation
for one cycle and relocated inspection of both old/new request formats. No native
code is executed during inspection. All defaults and chemical targets are fixed.

The evidence chain remains in the existing ledger: C286/C287 printed 45 planes
and 58 parallelities; C289 ordinary raw full-objective forces fail 17/20 sampled
directions and correction passes 20/20 at the same score; C291–C294 qualify
five-cycle/fork/replacement-manager mechanics; C296 checks all constructor
parameters; C297 checks exact native source/platform and restores bindings.
C293's diagnostic normalized-score assertion, C298's argument-only preflight
failure and C299's incorrect outer preflight-PDB assertion remain preserved.
The latter happened after a successful CLI refinement; separate readback completed
without rerunning it. None of these observations diagnoses the collaborator's PDU.

C300 carries the explicit choice through schema-2 campaign recipes and Doctor
API/CLI. C301 corrected canonical/modified serial authority; C302 separated owned
repair storage; C303 removed repeated pure validation within a frozen allowance.
C304 then completed A:PDU preparation and five-cycle refinement, and C305 completed
the related G:5PC campaign. Both relocated cold reads pass. All 45 planes and 58
parallelity groups survive with their recorded strengths and all three local sugar
signs are retained. These are mechanics controls on substituted scaffold data, not
modified-crystal structure solutions.

C304's PDU triple bends beyond the unchanged coordinate screen. C306 identifies
wrong-looking adjacent single-bond targets in both controls, including 5PC despite
its scoped triple PASS. C307 adds source-typed comparisons and isolated numerical
candidates; the exact native interpretation of MMFF candidates changes only the
selected distance. The detailed current numerical gap and next experiment are
recorded once in **Pipeline position** above. Reuse those completed construction,
recovery, delivery and force checks; do not start another identical campaign to
rediscover them.

**Historical C317 next step is complete:** C318/C319 qualified final output-state
synchronization; C333 delivers the chosen numerical target through the existing
owners. Do not reopen those tasks. The current Q06 work order is recorded once
under **Pipeline position** above. Remaining bending still requires evidence from
the whole neighborhood and effective refinement forces; a diagnostic PHIL override
or corrected target alone is insufficient. Original selected results and the
PDU:PDU symmetry-linked B:1 case remain separate. No SDK edits, default activation,
broad platform qualification or complete scientific acceptance.

C290 separately checks the current ordinary PDU A:12/B:4 construction against the
original accepted MR. Parent-chi deviations are 0.027°/0.006°, closing this control's
old construction flip. It stops before dictionary repair at the previously known
raw-W B:1 incomplete-phosphate ambiguity. C295 records Simon's correction:
B:1 is intended to continue covalently through symmetry, retaining P/OP1/OP2
without OP3; his earlier free-OH answer is superseded. The nearest observed
candidate in that experiment was B:7 O3′ under `-x+y,-x,z`, 3.34019 Å
in the original/prepared models. Simon subsequently confirmed B:7 and B:1
as the covalent endpoints on the retained central strand. The
[scaffold convention](backbone-chemistry.md#the-central-strand-in-the-5w6w-scaffold)
records that decision and the independent image check. C290 itself made
no atom edit or native link.

**Pine/Cedar convergence (Simon and Linden, 2026-11-14):** Pine owns editable
declared topology beyond the asymmetric unit: atom identities, exact operators
and lattice shifts, continuation versus terminus/nick, uncertainty and edits.
TopoStitch is the front-end preview; Cedar reports whether effective dictionaries
and native restraints enforce that intent. Carry declared intent, coordinate
support and consumer capability separately. Changes/reslicing retain prior choices
and map both endpoints/images explicitly, flagging unresolved mappings instead of
silently dephosphorylating, adding OP3 or guessing a new partner. D:1's existing
complete terminal-phosphate authority remains separate. Reuse W48/W49/W50 owners;
do not create a second Cedar topology registry. This is a planned shared contract,
not implemented symmetry-link support. C111 already demonstrated low-level angle/
plane energy agreement for two image operations, but PHIL exposure, force mapping,
manager integration and nonbonded exclusions remain unqualified. Do not activate
a lone symmetry bond without those surrounding terms. Finish the bounded
native-consumer work; track this integration dependency without silently bypassing
the B:1 guard or reopening the whole symmetry-restraint project.


**Open chemical-survival gate; the explicit consumer mechanics above are already
qualified for the recorded build.** C206 adds an explicit achieved-geometry
requirement: check parent-to-mutant
orientation, local trigonal geometry, retained ring planes and exocyclic coverage,
alongside triple-axis terms. Keep native membership, numerical consistency,
chemical target plausibility and achieved geometry distinct. Its successful
fixed-backbone diagnostic does not close this package.
C23–C26 identified the parallelity-gradient accumulation defect; C147–C150
proved diagnostic corrections, and C291–C300 subsequently qualified the explicit
ordinary route described above. Unmodified/default Phenix is not covered by that
qualified route.

Record exact installed capabilities/source/version and test the actual supported
refinement path with complete NAR pair/stack restraints. Decide an explicit,
reviewed compatible route or report an unsupported consumer; never silently patch
an installed SDK or drop restraints. Done when the selected repaired bundle is
consumed by ordinary refinement with preserved observations and Free-R authority,
source hands, terminal intent and exact custom membership. A bounded mechanics
success need not solve the test structure, but must establish the advertised
consumer behavior. Document unavailable formal-charge APIs honestly.

**Explicit post-refinement survival check (Simon, 2026-11-14):** Simon reports
that an earlier Cedar-built PDU sent to a collaborator looked well formed before
refinement but distorted afterward. The exact files, Cedar revision, native
version, settings and before/after coordinates are not yet identified; this is a
reported downstream failure, not a diagnosed mechanism. Keep it in Q06, then
reuse the control in Q07. Q04/Q05 handoff is already complete for its supported route;
this downstream chemistry question does not reopen it.

Run the actual supported Phenix refinement with the selected complete bundle.
Compare the built model, ReadySet output and final refined model: ring geometry,
C5 trigonal geometry, the ring–C5–propyne plane, propyne internal geometry and
intended glycosidic/base orientation; retain sugar stereochemistry, phosphate
intent, base-pair/stacking membership and Free-R authority. Inspect effective
native proxies/targets/weights as well as final coordinates, so a beautiful input
or a CIF plane listing cannot masquerade as successful restraint application.
Distinguish wrong/missing/dropped restraints, atom-name remapping, weighting,
native-consumer defects and ordinary data-driven movement. Use source connectivity
and geometry rules, with PDU and a held-out related substituent as controls—not a
PDU-name repair switch. Chemical survival across the advertised supported
chemistry remains unproven until these checks pass; completed explicit consumer mechanics alone do not
establish that result. On 19 November Simon chose to test the patch with the
retained matched controls. The original collaborator refinement remains undiagnosed
and is not a closure prerequisite.

### Q07 — One mixed-scaffold ordinary acceptance run

**Open. Depends on Q02–Q06.** Retain all eight original pairs on one scaffold: K:X, D:T, Z:P, B:S, PDU:A,
5PC:G, 5CM:Q and DF:A, with **ATL alongside the existing pairs**, not PDU paired
to ATL.
Use explicit recorded identities (DF is the laboratory alias for A1AAZ), broken
PDU and source-changing DF inputs, and the same generalized recovery rules.
C146–C150 establish connected ATL, exact 201 custom restraints, repaired PDU/5PC
numerics and endpoint mechanics; they do not close ordinary adoption/refinement.
C416 reconfirmed all nine site pairs on one 42-site model and all 201 native
custom restraints by atom identities, targets, weights, origin and multiplicity.
No diffraction data entered that geometry-only calculation, which reached its
iteration budget. Its older PDU attachment target and plane membership differ
from the current ordinary dictionary. Both numerical dictionaries already
contained their respective sugar–base targets before Phenix applied them.
Their heavy-atom connectivity agrees, while the bond orders for P–OP1, P–OP2
and P–OP3 differ between the isolated definitions. The newer dictionary also
has two additional phosphate hydrogens. Read the linked model and declared
end intent before assigning a phosphate state. Retain the mixed recipe and this prior
evidence when qualifying Q07 with current sources. The nonmetal DF:A endpoint
also provides a separate geometry control. Several conditions differ from the
DF–Hg–DT refinement, so the two endpoints cannot isolate the role of mercury.

**First ordinary experiments.** C422 compared all 42 site identifiers with the
current host. The actual catalogue and ordinary input reader resolve all 13
changes. Without ATL, the other 12 plan normally. Neither planning check builds a
model or establishes pair restraints.

1. Reuse the existing W-frame restraints. On the archived model, current
   NARestraints and the ordinary W-frame preparation regenerate all 201 earlier
   requests with the same atoms, targets, weights and multiplicity. They also
   request one shared plane for each of the nine named pairs and the canonical
   A:13/B:3 flank. Appending the old restraints would duplicate the originals.
   C427 subsequently confirmed every request against the native restraints on
   a fresh mixed model, including each plane member and weight. Preserve the ends on that model.
   The archived mixed D:1 has O5′ alone among the phosphate-end atoms. The
   proposed G:5PC fixture explicitly allows OP3 at its phosphorylated D:1.
   Both fixtures have O5′ without P at B:1. The separate symmetry-linked PDU:PDU
   B:1 requires P/OP1/OP2 with no OP3. Preserve each experiment’s own intent.
2. Connect the existing source-bound locked-sugar placement and bridge to the
   ordinary A:11 mutation. Reuse C143’s opposite C3′/C4′ hands as a refusal
   control and C145/C146’s base anchors and two native junctions as positive
   controls. Check all four source hands, both O3′–P lengths, all eight junction
   angles, both ATL:A contacts and unaffected sites. Recompile pair/stack atom
   selections against the constructed model. C149 already measured the two
   junctions at 1.606 and 1.610 Å after geometry-only optimization. It exhausted
   its iteration budget and kept the input selected.
   C425 recovers the measured DP and IMC orientation errors in ordinary Coot.
   C426/C427 built all nine pairs through explicit locked-sugar placement.
   The fresh native manager received both backbone bonds (1.607 Å targets) and
   all eight chemical angles. The outgoing bond and angle begin at 1.839 Å and
   141.55° (119.7° target). The seed assigns B=20 Å² on a 166–320 Å² host
   site. Establish how to carry host displacement through mutation and handle
   the initial strain before ordinary mixed refinement. Keep the seed itself
   as an immutable construction control. C428 found 110 B resets among 132
   coordinate-identical scaffold atoms. C429 tested a host-based alternative
   on a 5PC site whose original base had a single recorded B. Eight of the
   ten generic host bases had nonuniform B values. C433 now transfers measured host B values for
   unchanged sugar and phosphate atoms. A defensible initial B for new base
   atoms on a nonuniform host is still open when the base differs. C465 can
   transfer all nine measured B values across an exactly graph- and role-matched
   base even with a different sugar. The two original ATL junction lengths remain
   1.595 and 1.839 Å. Historical coordinate-only
   restorations keep their recorded interpretation. C318/C319 already handle the separate issue
   of writing consistent B values at the end of native refinement.
3. C430 transferred three ordinary component dictionaries onto the nine-pair
   scaffold with freshly derived site modifications. Phenix applied 1.470 Å
   terminal targets at both PDU and 5PC, and the ordinary DF thione target at
   1.638 Å. All three sites reproduced their ordinary covalent and local plane
   restraints. The ten remaining components in that native comparison still
   use the older definitions. C431 then froze and reopened one pending request
   with all thirteen current sources, every selected site, all 38 backbone
   links and all 211 frame terms. C432 executed it once and stopped at 5CM’s aromatic annotations. C434/C435
   qualified three original exact bond representations and one source-declared
   five-ring beside C=S. C436 then acquired all thirteen in isolation with eight
   matching snapshots reused. Linked preparation stopped at singly bonded
   anionic OP3 in 1AP. C438–C439 qualified this same-ASU leaving group.
   C444–C448 resolved the source-ring plane screen and followed two contrasting
   single-site controls through diffraction refinement. C449 combined all
   thirteen current definitions with the proven numerical repairs. C450 then
   obtained those same three sites' local terms ordinarily on the twelve-component
   DNA route. Seven stages recorded three supported plane changes, two bond-target
   changes and two explicit findings of no supported plane completion.
   Packaging the combined evidence stopped before the ordinary endpoint.

   C455 verified each of those seven transitions, selected the combined
   dictionaries after an independent native derivative check, and reopened the
   compact publication after moving it. C457 qualified the new outer owner
   against the original partial files, known-stopped recovery and fresh completion.
   C458 completed the actual twelve-component ReadySet round trip. C460
   separately reproduced the selected endpoint on relocation; its original
   attempt has a verified failed publication. C461 registered a fresh twelve-change
   parent. C466 completed its five-cycle diffraction child. C463 binds the
   two-ended ATL reaction to the complete request for separately placed atoms.
   C464 and C467 retain the old stopped attempt and its independently relocated
   fallback. C468 completed the fresh request and C471 reopened the new
   named-atom alternative on the exact checked endpoint. C472 tested isolated
   rigid motion and phosphate torsions against both junctions and the two pair
   distances. The outgoing link shortened as the pair contacts worsened.
   C478–C480 tested that neighbouring flexibility with a fresh crystal-image
   contact search. A single extra receiving-phosphate rotation kept the two
   central links at 1.610 and 1.603 Å, retained the source hands and brought
   the paired contacts to 2.873 and 3.171 Å against 2.8 Å. A fresh Phenix
   reading preserved the eight covalent and plane categories, all 211 frame
   requests and the nine measured base B values. The two neighbours were
   allowed to move, so check both outer junctions and all three pairs as well.
   C481 independently recompiled all 211 frame requests on the moved model
   and preserved all 869 named atoms through ReadySet. C483 tested that
   placement against diffraction before changing ordinary construction. All
   four sugar centres survived, both pair contacts shortened and the outgoing
   O3′–P–OP2 angle ended at 112.5° against 108°. Two overlaps exceed 0.4 Å,
   one with the preceding sugar and one within ATL. C494–C497 then built
   all thirteen substitutions through the ordinary owner, checked cache reuse
   and changed-source rejection, and registered a five-cycle child against
   the host observations. The compact ledger records the native pair/stack
   membership, unchanged intensities and flags, four source sugar centres and
   final geometry at PDU, 5PC, DF and ATL. The local contacts and unfamiliar
   eight-residue challenge remain open.

C591 distinguished the local contacts in two different locked-sugar experiments.
The earlier placement control (C483) ended with DG A:10 C2′ close to ATL A:11 O4′,
and an internal ATL C6–C6′ contact. In the registered thirteen-change model (C497),
the two contacts instead involved the preceding sugar **A:10 C2′ to ATL A:11 C6**
(0.572 Å overlap) and the following backbone **ATL A:11 C2′ to A:12 O5′** (0.557 Å).
Both are between neighbors in the same crystal copy. Through the second five-cycle
round, the largest printed overlaps on ATL C6 and C2′ changed to 0.586 and 0.528 Å.
The compact second-round record names the two ATL atoms. It lacks the opposite
endpoints, so those measurements alone cannot show that the partners were identical.
The original temporary model and GEO at the declared C505 location have expired.
The pair distances, both covalent junctions and the four sugar stereocentres
have their own retained measurements.
Use `--contacts-at A:11 --min-contact-overlap 0.4 --json` on the next native
return to save both endpoints, crystal operator and van der Waals reference in a
small record. A new fit is only warranted by a distinct chemical or placement test.

Done when an ordinary invocation acquires or repairs the necessary dictionaries,
qualifies the selected state and produces inspectable refinement artifacts with
all intended pair/stack membership, source centres, phosphate/H state and unaffected
sites checked. Include cache reuse and one changed-source rejection. Report
nonconvergence, residual strain and scientific uncertainty separately. A one-off
runner that chooses its repair from an ATL/PDU name does not satisfy this package.

**Queued closure challenge — held-out mixed modifications (Simon, 2026-11-03):**

C592 fixed the eight sites before construction. Four pairs on the original
42-site W frame are A:4 LCC / C:12 2MG, A:7 5MC / C:9 SJO, A:11 URX /
B:5 6MZ and A:19 UY1 / D:4 AS. LCC has the oxygen-bridged locked sugar.
URX has a different carbon bridge. UY1 is a C-nucleoside. The design asks for
one sulfur on the original D:4 OP2 side and an internal monoanionic linkage
from D:3 O3′. The free AS source is neutral and supplies no absolute phosphorus
stereo assignment. A compatible amide-linked PNA segment remains a separate job.

The ordinary recipe reader accepted all eight codes. NARestraints 1.1.3 wrote
ten Watson–Crick bonds, sixteen angles, four paired-base planes and four
parallel groups. Phenix 2.2.1-6174 bound every selection against the eight
separate source atom inventories. All sixteen flanking backbone links in the
unmodified host measured 1.596–1.629 Å in the same crystal copy. Five sources
matched an existing strict attachment pattern. UY1 exposed the earlier PSU
workbook assumption in this new design. URX's bridge and AS's sulfur remained
outside the ordinary oxygen-phosphate patterns. The default all-eight
construction plan stopped at LCC. The explicit single locked-sugar route has
a separate source-state gate. These results establish that Phenix can resolve the
requested atoms. C623 subsequently identified an incorrect oxygen on UY1.
The eight-site constructed and refined models remain outstanding.

C593 compared the complete named atom and bond graphs in wwPDB and Phenix
2.2.1-6174 for PSU, P2U, B8H and UY1. Each sugar C1′ bonds to C5. NARestraints
had inferred N1 and mapped C1′ to the thymine methyl role. The upstream correction
names both ends separately and keeps N1 in the base. All 614 other records read
back identically. Across the eight separate monomer inventories, native Phenix
bound the same ten bonds, sixteen angles, four planes and four parallel groups.
Only UY1's sugar C1′ left its pair plane and parallel group. Six of the eight
source graphs now match an existing attachment pattern. An old loader paired
with the corrected workbook is reported as an explicit conflict. [Upstream
workbook, loader and exact source comparison](https://github.com/vecchioni-lab/NARestraints/pull/6).

In the four independently admitted substitutions, Coot 1.3.3 first received
C:12 DG → RNA G as the parent for 2MG. It returned success from the mutation
call and then read the residue back as DG. Construction stopped before writing
the model. In a separate D:4-only construction, Coot wrote AS with P–S at
2.130 Å and an internal OP3 at 1.623 Å. The two adjacent O3′–P links changed
from 1.612/1.602 Å to 1.865/1.338 Å. Ordinary phosphate preparation refused
the missing OP2 and produced no prepared model. Retain that check. A valid
return needs the sulfur on the specified side, the linked charge and leaving
group, and acceptable flank geometry. The neutral isolated AS dictionary alone
does not establish those facts. Neither control reached diffraction refinement.

C594 now reports the requested and returned residue when Coot's own script
sees an identity mismatch. An independent C:12-only control gave RNA G
requested and DG returned. The raw sulfur control and ordinary preparation
refusal remain separate. In the C105 archive, 31 of 596 checked component
sources contain a P–S bond. Of those, 22 contain one terminal sulfur, six
two terminal sulfurs and three a sulfur bridge. Another 44 contain sulfur
without a P–S bond. Qualify each source and the intended side of the bond.
Typical phosphodiester OP2 rules cannot select a phosphorothioate configuration.

C595 uses the published NARestraints workbook and loader together. A fresh
Cedar installation follows the latest stable package. The environment check
can compare versions or run offline. Numbered release archives and workbook
fingerprints remain available for historical replay. [NARestraints v1.1.4](https://github.com/vecchioni-lab/NARestraints/releases/tag/v1.1.4).

C596 supplied real G, C and A parents for C:12, A:7 and B:5 on the same
42-site frame. The canonical parents added three correctly oriented 2′ oxygens
and preserved all six neighboring O3′–P distances. Coot subsequently built
2MG, 5MC and 6MZ with an extra OP3 at each site and displaced the flanks.
The ordinary phosphate check refused the result. C597 then matched the native base
orientation to the parent and restored the verified ribose. All six flanking bonds
and all 791 unselected atoms were preserved. The internal OP3 proof passed at all
three sites. C598 used the same rule from a normal input card on a fresh Phaser
solution (TFZ 17.1). All 791 unselected atoms and the six links were preserved.
NARestraints compiled 19 pairs and 38 stacks. The checked request then tried to
interpret those already compiled restraints as new instructions and stopped at
the disabled secondary-structure setting. C599 reused its verified compiler receipt
on a second fresh Phaser solution with the same input card. The checked request
bound the 50 pair bonds, 86 angles and 57 parallelity restraints. The two isolated
2MG models both received Phenix’s native `rna2p` sugar adjustment. Native
interpretation finished, but the isolated exact-target check stopped. Inspect the
installed sugar targets and their active restraints before advancing. The other
five sites still need their own evidence.

C600 compared the same three sites through conventional native Phenix. ReadySet
used its installed 2MG and 5MC entries and wrote a dictionary for 6MZ. The
ordinary generic preparation correctly recorded the two absent output CIFs. A
separate one-cycle coordinate refinement using those named installed entries,
the 6MZ output and the full compiled restraints returned all 859 atoms and the
original hand of all twelve sugar centres. The six links ended at 1.561–1.607 Å.
The B:5 6MZ base rotated 38.6° and one Watson–Crick distance opened to 4.128 Å.
The closest C:12 2MG pair contact shortened to 2.215 Å. Neither result is a
qualified pair. ReadySet called the 6MZ C4′–C3′ sugar bond aromatic and put
nine atoms, including four sugar stereocentres, under a common plane. That plane
was active in the final Phenix geometry file. The starting 6MZ methyl already
pointed away from its Watson–Crick partner. These are hypothetical substitutions
in an existing dataset.

C602 compared each effective plane with the same component's frozen source.
A four-single-bond carbon with a declared R or S hand needs three independently
mapped heavy neighbors in that plane for this warning. Ordinary PostMR quarantines
the generated component when all four plane widths are as tight as the three
bond widths. Wider planes stay visible for review. Replaying ReadySet's three-site
return identified C1′, C2′, C3′ and C4′ of 6MZ, each under a 0.020 Å plane.
The existing source-derived replacement passed this check. This is a check on
restraint targets. Returned coordinates are measured separately. C603 also finds each
aromatic bond incident on the same source-declared tetrahedral carbon. It found
three such sugar bonds, distinct from the legitimate aromatic base. For C2′–C3′,
ReadySet wrote 1.292 Å, but Phenix applied a 1.525 Å target in both one-cycle
runs. The incorrect sugar plane did survive. The independent 6MZ two-seed controls
matched the actual installed pucker table at 11 bonds, 18 angles and six torsions.
All four chiral signs held. Keep the two kinds of disagreement distinct.

C604 adds `nasolve cif-doctor explain-pucker QUALIFICATION` for an already
stopped pair of isolated native reads. It binds the original models, candidate
and consumer, applies only the three numerical change categories in the selected
installation's `rna2p` table, and checks every effective definition and active
restraint again. Across both coordinate seeds, 2MG and 5MC each matched 11 bond,
18 angle and two torsion rows. 6MZ matched 11, 18 and six. This replay leaves the
existing stored verdict intact. The table fingerprint identifies the installation
used for the explanation.

C605 adds `nasolve cif-doctor verify-pucker DEFAULT_JOB NEW_LITERAL_JOB` and
`--replay`. Once the selected installed table explains the ordinary native
adjustment, both original coordinate seeds are run separately with just that
adjustment disabled. Replay verifies the same source, generated dictionary,
consumer, native targets and four records. 2MG, 5MC and 6MZ each passed.
The original qualification and ordinary dictionary-cache rules retain their
prior meaning. The paired proof is currently available for isolated components.

On the 859-atom three-site scaffold the three source-derived dictionaries were
then compared in one-cycle coordinate refinements against the original data
and Free-R flags. Each used the original 19-pair, 38-stack recipe. The existing
Cedar parallelity route also ran its genuine zero-cycle preflight before its
one-cycle fit. Its final table printed 50 distance, 86 angle and 57 parallelity
requests. All twelve sugar hands survived, with six O3′–P lengths of 1.580–1.610 Å.
The 2MG O6 to cytosine N4 contact reached 2.135 Å and the 6MZ N6 to thymine O4
contact 3.906 Å against respective 2.8 Å targets. The stock comparison gave
2.121 and 3.933 Å on the same chemistry. Check the actual returned pair contacts
and carry paired proofs into ordinary acquisition before promoting this route.
The three substitutions are hypothetical on the experimental scaffold.

C606 reopened all 50 supplied distances and 38 ordinary backbone links at entry
and exit. The reported target and width matched in every case. A matched native
five-cycle run from the same start moved 2MG O6···N4 from the one-cycle 2.135 Å
to 2.463 Å, and 6MZ N6···O4 from 3.906 Å to 3.372 Å. Contacts farther than three
restraint widths from target numbered 9 at entry, 8 after one cycle and 1 after
five. This descriptive comparison uses the printed 0.20 Å restraint widths. The
remaining long contact was unmodified DG A:14 N2···DC B:2 O2 at 3.415 Å. Across
the three substitutions all twelve sugar hands remained intact, all six flanks
measured 1.603–1.609 Å at five cycles and the three inter-base plane angles were
6.58–8.36°. The 6MZ glycosidic torsion moved 15.4° from construction. Its
pair remains open for review. Distances can now be inspected in the ordinary
`--refined-links` reader without a separate analysis script or a new ranking rule.

C607 selected the existing internal-sugar reaction directly from the three source
graphs, workbook roles and six declared backbone neighbors. ReadySet chemistry and
manual end declarations retain their existing authorities. A fresh Phenix whole-model
read found each site-specific reaction plus `rna2p`. The effective atom, bond, angle,
torsion, plane and chirality definitions matched the corresponding projected site after
the installed pucker adjustment. The candidate still needs the separate default and
literal evidence throughout acquisition. A relocated request reconstructed its original
pair recipe while the original dataset and installed workbook were inaccessible.

C608 then sent the three projected dictionaries, their three site-specific reaction
dictionaries and their exact residue selections to the same five-cycle refinement.
The Phenix log confirmed each site modification and native pucker. The returned PDB
matched C606 byte for byte. This tests compatibility with the normal linked chemistry
on this scaffold. The three substitutions have no separate measured diffraction.
A new isolated comparison archives the installed pucker table with its hash. The
original two-directory comparisons can still be checked with their selected Phenix.

C609 moved the two native and two literal coordinate reads under the ordinary
acquisition owner. Both 2MG and 5MC acquired usable isolated dictionaries. For 6MZ,
the supported fresh atom-order recovery preserved the 42 source bonds. A single
whole-model request then consumed all three without starting another isolated job.
The 2MG acquisition reopened from 115 distinct local files with its original tree,
store and Phenix installation unavailable. A same-size change to the frozen table
was rejected. The linked comparison still needs to account for the normal pucker
and to distinguish a real heavy-atom plane from a definition left with only three
coordinate atoms. C610 accounted for the latter. H62 was absent from the B:5
coordinates. Phenix requires four modeled atoms for a component planarity force.
The separate 11-atom ring plane and every weight matched. The same native captures
replayed under their original rules, and only that plane verdict changed on fresh
preparation. C611 matched the native sugar-pucker rows at all three sites. The
fresh ordinary request archives one 2,278-byte table for the three sugars, verifies
it against each selected recipe and carries it into each independently readable site.
Only a site with paired isolated evidence and the exact targeted modification followed
by the native `rna2p` receives that comparison. Phenix returned 11 matching bond and
18 angle changes per site and 2, 2 and 6 torsions. All 148 available linked checks
passed. Its three unavailable formal-charge reports remain explicit. Offline readback
touched 423 distinct files and rejected an equal-size table substitution. The first
ordinary execution now receives the same table fingerprint that it froze at intake.

C612 ran ReadySet on the three-site parent and fitted its selected model, combined
component dictionary and original ordered restraints for five coordinate cycles.
The first low-level preflight stopped at a parameter namespace. Passing the same
inputs through the existing AutoRefine parameter adapter succeeded. The returned
859-atom PDB matched the independent C608 five-cycle control byte for byte.
An explicitly selected recovered snapshot supplied 6MZ to preparation. The 6MZ–T
contact remained long at 3.37 Å against 2.80 Å. The three substitutions have
no independent diffraction observations.

C613 started a separate ordinary Phaser → Coot → ReadySet → AutoRefine run for
C:12 2MG and A:7 5MC. It reused the two qualified isolated dictionaries. The
operator supplied only the recipe, input data and search model. All eight sugar
stereocenters and four flanking links survived the five-cycle fit (1.594–1.609 Å).
Phenix printed all 50 requested pair distances and 38 native backbone links.
The ordinary child `refine-001` reached Rwork/Rfree 0.2213/0.2360 on the original
Free-R assignments. Both the model composition and refinement strategies differ
from the three-site control. A separate change to the source C2′ stereo declaration
invalidated the old 6MZ dictionary and its atom-order recovery evidence.

All three modified rings require review before extending this panel. Both trials began
with 2MG N9–C4 at 1.377 Å and 5MC N3–C4 at 1.326 Å. Their printed targets were
1.388 Å (σ 0.031) and 1.352 Å (σ 0.024). The two-site ordinary return reached
1.496 and 1.439 Å. The three-site coordinate-only return reached 1.611 and
1.573 Å. Its 6MZ N9–C4 also reached 1.530 Å against a 1.393 Å target.
Two neighboring ordinary DNA ring bonds stayed within 1.2 restraint widths in
the matched three-site comparisons. Both stock and checked Phenix stretched the
modified rings in the first cycle. Removing the three local pairs’ eight distance
and fourteen angle restraints left the distortions. Removing all 193 supplementary
NARestraints terms also left all three bonds 8.3–14.4 widths long. Conversely,
with the full pairing and stacking set and zero experimental coordinate weight,
all three returned within two widths. Without either contribution, all returned
within 0.6 widths. A positive coordinate weight fixed to one tenth of the stock
one-cycle reference improved all three ring bonds. Two additional complete stock
five-cycle fits compared automatic weighting with that fixed coefficient. Deviations
for 2MG, 5MC and 6MZ changed from 4.9, 3.9 and 2.3 widths to 2.9, 2.9 and 0.9.
Rwork/Rfree changed from 0.2831/0.2652 to 0.2940/0.2767. Both fits used the same
full pairing and stacking restraints and Free-R assignments. This is a tradeoff
on hypothetical substitutions. The printed bond widths for 2MG, 5MC and 6MZ
were 0.031, 0.024 and 0.028 Å. Their ordinary G, C and A comparisons were
0.008, 0.007 and 0.006 Å. These larger uncertainties give the modified bonds
a weaker restoring force for the same displacement. Keep the modified target lengths and original pair and
diffraction weights fixed when testing a chemically justified width. Inspect the
rest of each ring before selecting a change.

C614–C616 kept the three-site coordinates, observations, flags and all 193 supplied
NARestraints terms fixed. Under a common positive diffraction coefficient of 28.65,
tightening one ring bond per base brought those bonds closer to target while the
other ring bonds stretched further. Under ordinary automatic weighting, transferring
the lengths and widths for all 26 ring bonds from the exact modified-component
CCP4 references gave good ring geometry, with Rfree rising from 0.2652 to 0.2759.
The supplied references matched the source atoms, charges, attached hydrogens
and local bond orders across each base ring and its directly attached groups.
[Reference dictionaries at the tested revision](https://github.com/MonomerLibrary/monomers/tree/0af022bf6f7c401d59c7bf106e6709fc5f57c3d4).

The earlier C428–C433 and C511 controls separated scaffold and base displacement.
Here the sugar and phosphate already carried their original B values while the
32 newly placed base atoms all carried Coot's 20 Å². The corresponding host
base medians were 270, 223 and 230 Å². Changing only those 32 starting B fields
and retaining the original chemical dictionaries gave the following five-cycle
stock Phenix 2.2.1-6174 results with automatic coordinate weighting.

| Starting values on the three bases | 2MG N9–C4 (Å) | 5MC N3–C4 (Å) | 6MZ N9–C4 (Å) | Rwork / Rfree |
| --- | ---: | ---: | ---: | --- |
| Coot default | 1.540 | 1.446 | 1.459 | 0.2831 / 0.2652 |
| Each base's host median | 1.428 | 1.373 | 1.378 | 0.2402 / 0.2450 |
| Shared atoms from host, added methyl from its bonded atom | 1.428 | 1.364 | 1.378 | 0.2403 / 0.2423 |

In the last run all 26 source ring bonds stayed within two of their **original**
printed widths. All twelve sugar hands and 38 declared links survived. Three of
50 supplied pair contacts exceeded three widths, compared with one in the control.
Under the same fixed high diffraction coefficient the starting-B change also
reduced distortion, though ring outliers remained. Carry the starting estimate
into a new ordinary run. These substitutions use observations from their unmodified
host. Preserve the independent check of pairing, the source chemistry and the
existing exact-base displacement rule for sugar substitutions.

C617 repeated the ordinary two-site workflow from new Phaser coordinates using
Coot 1.3.3, NARestraints 1.1.4 and Phenix 2.2.1-6174. All 16 ring distances lay
within 1.26 of their original restraint widths after five AutoRefine cycles.
The earlier two-site run stretched 2MG N9–C4 to 1.496 Å and 5MC N3–C4 to
1.439 Å. Their new lengths were 1.427 and 1.366 Å. The same observations and
Free-R flags gave 0.2287/0.2356 for Rwork/Rfree, compared with 0.2213/0.2360.
Three pair distances exceeded three widths (previously two). Both 2′ hydroxyls,
eight sugar hands, four flanking P–O3′ bonds and all 38 printed backbone links
survived. The separate three-site Coot check reproduced all 32 base B fields
from the independent C616 experiment, including the added methyl carbons.
A schema-2 construction record carries and rechecks the per-site starting
values after relocation. Earlier construction records retain their original
interpretation.

C618–C619 carried all three substitutions through ordinary Coot and checked
ReadySet in a new numbered run. A second run withheld the entire 6MZ cache
entry. Its first native builder added O4′–C2. The source-certified recovery
ran once, within the original allowance, and its independently qualified
product matched the warm run. After relocation, the complete record reproduced both stopped child identities
and the original false bond with the old inputs inaccessible. Replay read 309
retained files and started no external program. The prepared model, observations,
five parameter files and four dictionaries matched byte for byte. Five ordinary refinement
cycles on those inputs gave Rwork/Rfree 0.2292/0.2338 and kept all 26 ring bonds
within 1.98 widths. All 38 backbone links and twelve sugar hands survived.
Three of 50 paired distances exceeded three widths. The longest was 3.585 Å
between 2MG C:12 N2 and A:4 DC O2. The restored 6MZ itself paired at 3.472 Å
through B:5 N1 to A:11 DT N3. This establishes three substitutions on the
measured host frame. The other five design sites and the OP2 state still need
work. Phosphate protonation remains with Q13.

C620 tested the two 2′-O-methyl sugars in the fixed design against the
installed Phenix 2.2.1-6174 component sources. SJO attaches the base at N9
and UY1 at C5. Both sources matched the earlier design by checksum. The native
builder added C1′–P at 5.979 Å to SJO and C1′–N1 at 3.728 Å to UY1. The same
source-order recovery used for 6MZ identified each extra bond, preserved all
46 or 38 source bonds respectively, and produced both candidate dictionaries.
Two native coordinate starts for each compound then exposed a second issue.
For SJO both starts chose `rna2p` and matched 11 bonds, 15 angles and six
torsions. For UY1 the source coordinates selected `rna3p` (10/12/6) while the
generated coordinates selected `rna2p` (10/16/6). The installed numerical
tables accounted for every changed target. Check the literal dictionaries
independently, then address placement and both neighbouring links. SJO flags
O1P on a phosphate whose double-bonded oxygen is called O1. The ordinary
constructor protects O1P. For UY1, the true C5 ring attachment has neighbours
C4 and C6, while the host thymine N1 has neighbours C2 and C6. Preserve both
chemical assignments when evaluating a placement.

C621 disabled only Phenix’s sugar-pucker adjustment in four new isolated
native reads. Both starting coordinates of SJO and UY1 then satisfied their
literal dictionaries, including bonds, angles, torsions, planes and chirality.
The four-job comparisons for both compounds replayed with the original
folders and Phenix installation unavailable. Changing one byte in the frozen
`rna3p` table was rejected. The measured UY1 pseudorotation phases were 58.7°
and 63.2°, with amplitudes of 40.2° and 39.3°. Phenix chose different numerical
tables across that modest change. Their choice in an actual polymer remains
an independent measurement.

C623 found that the wrong pseudouridine carbonyl had been selected in the
canonical adenine recipe. In the 6I1V and 6I1W NMR duplexes O2 sits 2.92–2.94 Å
from adenine N6. The 3CGP PSU duplex and the 8PFQ/8PFK N1-methyl analogues
show the same edge. On 84 unchanged 6I1V atoms, Phenix 2.2.1-6174 installed
the former PSU O4 contact at 5.33 Å and the corrected O2 contact at 2.94 Å.
The other three distances, both plane groups and both parallel groups matched.
A graph check recognizes the discrepancy independently of atom names and of
the installed writer. Four revised workbook rows agree when used with the
corrected writer. The other 614 rows retain their values. UY1 and P2U have
the same source connectivity. Their pairing with adenine is a transfer from
PSU and B8H. Build the UY1 site on the same design, check both phosphate
neighbors and the O2 contact, and measure survival in native refinement.
[NARestraints review and primary evidence](https://github.com/vecchioni-lab/NARestraints/pull/8).

C624 placed UY1 at A:19 on the registered three-site parent. The ring anchor, N–H donor and distal carbonyl define a noncollinear frame. A single rotation about C1′–C5 transferred the host sugar–base torsion. The existing phosphate-arm search then restored the two internal links. The explicit construction reproduced all 860 coordinates of an independently built seed and reopened after relocation. Phenix 2.2.1-6174 minimized only the 21 new atoms. Five short contacts, including a 0.63 Å methyl overlap, cleared. The N3–N1 and O2–N6 contacts reached 3.00 and 2.88 Å, the two O3′–P links reached 1.604 and 1.611 Å, and all four sugar stereocenters retained their hand. The control using the original source torsion retained a 2.08 Å clash after the same minimization. These controls used geometry alone. The linked site’s nearest symmetry neighbor was 8.61 Å. The other 839 atoms stayed fixed. Parent diffraction, starting displacement, native pucker choice and ordinary acquisition are separate tests.

C625 then took that four-substitution model through five Phenix diffraction cycles on the unmodified host at 4.017 Å. UY1 N3–adenine N1 ended at 2.929 Å and O2–N6 at 2.830 Å. The two phosphate links measured 1.605 and 1.613 Å. All 22 native UY1 bonds matched the retained source graph, and all 16 sugar hands across the four substitutions survived. The closest other contact to UY1 was 2.68 Å. Three of 50 pair distances elsewhere remained outside three restraint widths. Rwork/Rfree were 0.2334/0.2388. All 2,267 comparable reflection indices and all 125 test assignments matched the three-site run. The model-specific output amplitudes and uncertainties had a uniform 1.00529 scale difference. The native linked sugar used `rna2p` on the seed, locally minimized and refined coordinates, each time recognizing the actual C1′–C5 attachment and A:20 phosphate. The four-site trial directly supplied the source dictionary and initialized UY1 at the host residue’s median B of 228.24 Å². Ordinary four-site acquisition, automatic constructor selection and local clash repair remain open.

C626 found that whole-sugar placement put one-letter atom names too far right in the PDB field. Phenix 2.2.1-6174 looks up the next phosphorus by its exact four columns when it chooses the upstream sugar restraints. A two-nucleotide calibration used one 48° torsion change, keeping O3′–P at 1.622 Å. With the same rotated coordinates, standard spacing gave 3′-endo and the older spacing gave 2′-endo. The O3′ and P perpendicular distances were 2.382 and 3.060 Å. Both readers chose 2′-endo in the unrotated control. Across 450 eligible site/conformer readings on the W controls and public structures, none switched. The fresh four-site constructor preserved all 860 coordinates and all 839 bystander lines. Its predecessor replayed all 24 frozen files after relocation. No earlier scientific result is being reclassified. [PDB coordinate columns](https://www.wwpdb.org/documentation/file-format-content/format33/sect9.html).

C627 applied the existing internal furanose reaction to UY1 between A:18 and A:20. Phenix installed the site reaction plus `rna2p`. It stopped expecting OP3, removed both departing hydroxyl hydrogens, and typed O3′ as a bridging oxygen. The source’s OP2 hydrogen stayed in the dictionary pending Q13. The effective component agreed with every projected row across atoms, bonds, angles, torsions, chirality and planes. All 41 bystander definitions, 38 backbone links, native force parameters and fixed-coordinate energy readings matched the earlier bare-dictionary control. Five identical diffraction cycles returned the same 860 printed coordinates, occupancies, B factors, Rwork/Rfree (0.2334/0.2388) and all 2,267 output observations with the same 125 test flags. The bare dictionary’s missing OP3 warning had been real even though the heavy-atom fit was unchanged. Next, let an ordinary request carry the exact observed pucker tables and linked reaction with a cold, source-verified placement.

C628 bound the four isolated Phenix readings to an explicit dictionary recipe for source-declared linking RNA bearing a neutral 2′-O-methyl group. UY1 needed one source-order recovery and then qualified with 3′-endo and 2′-endo from its two starts. N-linked OMU qualified directly with 2′-endo from both starts. Switching off only the pucker adjustment recovered the complete literal source-compatible targets in both molecules. The fresh UY1 dictionary and the one used in C627 differed only in an eLBOW time comment, with all 49 chemical fields identical. Both six-file snapshots verified after an offline move. SJO still has a DNA-linking source declaration and a protected O1P flagged as leaving. Keep it under review. Next bind the installed site reaction and the specific table actually read in the real four-site model.

C629 carried both pinned tables with the qualified UY1 dictionary, its source reaction and an explicit internal A:19 site. After moving the 25-file preparation, it reopened offline. Two new Phenix reads selected 2′-endo on the linked site. All six effective dictionary categories and all 37 active-geometry checks passed. The sugar matched 10 bond, 16 angle and 6 torsion rows. All 38 strand connections remained. The shared custom-restraint check stopped on six pre-existing D:1 terminal-phosphate `change` edits. All six appear in the native manager once at the requested targets and weights. The checker currently admits `add` actions only. Keep that restriction until the original terminal-protection owner and its observed native forces can be bound together. The 34 missing native formal-charge attributes remain an explicit limitation. The current evidence is at fixed coordinates and inherits the five-cycle comparison from C627. An ordinary four-site run is still due.

C630 exercised normal source selection on the previously fitted four-substitution frame. The fresh and retained UY1 requests both selected the qualified pair of sugar tables. They froze a single correct replacement at A:19, between A:18 and A:20, with 38 declared backbone links across the structure. Three older substitutions kept their own source choices. A new ordinary four-site mutation card then completed Phenix molecular replacement but stopped before Coot at `DT→UY1` because the canonical parent lookup cannot choose a sugar for `2'-OMETHYL`. The direct C625 fit remains valid. Next qualify the whole-sugar constructor on this ordinary frame, including its immediate steric environment. Keep the older three-site ordinary result as the working control.

C631 replaced the default B of 20 Å² for a verified C/N uracil attachment change with the median over the original fully occupied heavy-atom residue. The 20 host atoms at A:19 gave 228.24 Å² for the 21 new atoms, reproducing the hand-prepared start for C625. All 860 coordinates and 839 bystander records stayed fixed. Missing atoms, partial occupancy or unsuitable B values retain the seed and record the reason. Historical seeds still replay.

Changing rigid-fit weights or starting from the source sugar conformer left four or five contacts shorter than 2.2 Å. When Phenix could see only UY1’s dictionary and site reaction it refused 23 untyped atoms at the distant B:5 6MZ. With every modified residue defined, three geometry-only cycles on UY1 alone cleared the five close contacts. All four sugar hands and 22 source bonds survived. The base-pair distances ended at 3.00 and 2.88 Å and the backbone links at 1.604 and 1.611 Å. Two contacts remained 0.42–0.44 Å inside Phenix’s van der Waals distances. Use the complete library and local pair/stack intent when qualifying the ordinary construction. No new diffraction cycles were needed for this comparison.

C632 put the separately constructed, locally fitted four-site model through ReadySet with Phenix 2.2.1-6174 and the NARestraints 1.1.5 candidate. The native reads before and after agreed on all 42 residue assignments, all 38 backbone links and all 193 requested pair and stack restraints. ReadySet reordered records and preserved all 860 named positions, occupancies and B values. Phenix used the linked 2′-endo table at each substituted site. The UY1–adenine contacts in this prepared model measured 3.000 Å (N3–N1) and 2.878 Å (O2–N6).

At those same coordinates, the only differences from the earlier protected C629 geometry terms were six angle restraints at the D:1 terminal phosphate. Preparation used the same six targets with 3° widths. The protected input used 1° widths. All eight families of geometry terms were compared. For the ordinary four-site run, first select and fit the whole sugar from the fresh mutation card, then verify that AutoRefine actually installs those six 1° restraints. The four-site diffraction evidence is still the direct C625/C627 trial. C632 completed preparation only.

C601 found the source-preserving generator had introduced a 5.779 Å bond between
O4′ and ring C2. All 42 source edges were present. The ten bonds of the purine
ring used its already approved aromatic representation. The recovery now checks
those exact observed ring conversions when identifying one additional printed
bond. It reordered complete atom rows in a fresh attempt and generated all 40
source atoms with the original formal charges and single sugar bonds. The
nine-atom sugar plane disappeared. In a matched one-cycle experiment changing
only the 6MZ dictionary, B:5 base rotation decreased from 38.6° to 8.9°. Its two
pair contacts ended at 3.096 and 3.932 Å, versus 3.469 and 4.128 Å with ReadySet.
The shortened 2MG contact persisted. This comparison establishes dictionary
sensitivity. The remaining 6MZ pair contact and ordinary pucker check stay open.

In both isolated 2MG coordinate seeds, all exact candidate checks passed when
only the coordinate-dependent pucker adjustment was disabled. With the usual
Phenix 2.2.1-6174 settings, the 11 bond, 18 angle and two torsion changes matched
its installed `rna2p` table. The four chirality signs and base plane were retained.
Phenix describes those 11 bonds as generic covalent. Preserve the literal source
bond orders, check the separately observed native adjustment, and keep the
ordinary linked-model and refinement checks in place.

After the qualified Q06 consumer is available, add a separate builder generalization
control before the proposed Cedar integration with main. Mutate **eight residues** into
Watson–Crick pairs spanning different base and sugar modifications, including an
LNA:RNA combination and a source-supported PNA combination where its declared
backbone context is compatible. Prefer catalogue ligands not explicitly repaired
in earlier Cedar pushes. Choose exact codes, sequence/sites and existing source
hashes when preparing the experiment; family names alone do not define chemistry.
Use the existing ligand definitions unchanged: this is a builder transfer test,
not a new dictionary-patching exercise or replacement for the original Q07 matrix.

Include a phosphorothioate case if its exact substitution, linkage, source charge
and phosphorus stereochemical intent (or explicitly declared mixture) can be
represented faithfully. Do not infer that state from an ordinary phosphate or
force PNA into a phosphodiester-link contract. Unsupported input/attachment routes
remain recorded coverage gaps and go into their owning queue package.

Acceptance: preserved input/source bytes, intended mutation and unaffected sites,
base/sugar/declared phosphorus stereochemistry, native atom/link/junction coverage,
and exact NAR Watson–Crick pair membership. Separate construction success,
unsupported chemistry, builder defect and dictionary/native-consumer defect;
a failed case is useful evidence, not authority to alter a ligand or weaken a
guard. Inspect geometry/clashes without equating builder success to refinement
or experimental validation. Catalogue/source selection and the compatible
host/segment recipe are preparation gates; Q09–Q13 retain family/state ownership.
**Queued for closure, not the next test. Q04/Q05 supported-route acceptance is now
recorded above; finish the active Q06 chemical-survival control first.**

### DY — Packaged retained-triazole reference and mutation support

**Explicit ordinary construction complete through C366; automatic public mutation
and pairing semantics remain open.** The existing packaged source, composition,
qualified numerical snapshot and per-site end-state projections now pass through
ordinary PostMR before Coot, then into the complete request. No duplicate owner.

| Established boundary | Evidence |
| --- | --- |
| Source identity and response to rotation about the single C4–N1T bond | C339–C342/C350–C351 established the original dictionary’s behavior. C456 tests the chemical preference for near coplanarity. |
| Free-OH/internal construction and ReadySet | C343–C346 established delivery. C456 identified an unintended A:12–B:4 covalent bond in the historical C346 refinement and repeated it with this link excluded. |
| Modified → canonical → modified and retained seed evidence | C347–C349/C353; PDU↔DY via DT with preserved scaffold/chi. |
| Packaged lookup, source composition and acquisition | C354–C356/C364; exact original inputs and existing native evidence retained. |
| Explicit planning, per-site selection and derivation lineage | C358–C359/C362–C365; source and numerical CIF roles independently checked. |
| Ordinary pre-Coot integration | C366; 190 focused and installed checks; exact mixed-end Coot model, cold complete request, preserved prior controls. |

**Ring geometry and chemical links before wider DY use (C456).** Check the
source-declared triazolyl–pyrimidinone and determine whether Phenix actually
restrains twist between its rings. Test the soft eleven-atom plane at a second
site or against experimental DY evidence before selecting its weight by default.
Measure the ring angle and the signed torsion independently so a half-turn
cannot silently exchange the presented nitrogen edge. C502 adds the final
checkpoint bond comparison. It finds the recorded adenine–DY link and accounts
for the 38 backbone and 53 supplied distances in the registered mixed scaffold.
C503 reads both ends of the same round. In the DY control, excluding the
observed N6–C5T pair revealed a second automatic bond to N4T. Excluding
both exact pairs restored all 38 declared links through five cycles.
C505 carries the two-stage check into ordinary checked refinement and numerical
recommendation. A usable result with an unexplained bond remains available
for inspection. General recovery needs explicit noncovalent intent and independently resolved atom
selections, including their effect on symmetry mates. The
[matched experiments](cif-doctor.md#dy-ring-orientation-and-unrequested-interbase-bond-c456)
include negative chemical controls and a ReadySet readback.

Remaining: deliberate automatic public selection/CLI integration, modified-input
canonical-seed forwarding through the ordinary route, and chemically specified
NARestraints pairing if requested. These are not supplied by a covalent-only
control. Do not reopen completed source/projection work or regenerate identical
numerics. Return first to Q06; see the existing methods and evidence ledger for
exact controls, commands and historical failed attempts. C356's machine-readable
audit is prior orientation, with these later completions superseding its queue.

Laboratory **DY** means the retained **4-(1,2,4-triazol-1-yl)-pyrimidin-2-one
beta-D-2-deoxyriboside**: direct pyrimidine C4–triazole N1T, C2=O retained,
no O4 bridge, pyridyl ring, 5-methyl group or triazole displacement. Simon approved
the preview and authorized distributing the reusable definition with NASolve.
The [packaged CIF](../src/nasolve/data/chemical_references/DY.cif) and
[identity/provenance record](../src/nasolve/data/chemical_references/DY.json)
are the starting reference, not qualified refinement targets. Free 3′/5′ OH and
no phosphate describe this reference only. `YTR` remains a historical preview
label; do not silently alias bare `Y`, infer a deposition code, or turn this
free nucleoside into a linked nucleotide without explicit context.

**C339/C340 source and isolated-native steps complete:** the model-coordinate
adapter accepts the packaged preview as a non-independent seed. A separately
versioned source-declared neutral five-membered C/N representation policy now
permits the complete triazole conversion, preserving H/charges/valence and the
single C4–N1T bridge. Historical policies remain unchanged. A fresh owned Phenix
2.2.1-6174 build passes the existing two-seed isolated native qualification and
cold relocation; the original C339 failure remains intact. No mutation alias,
linked context, ReadySet, Coot or refinement approval yet.

**C341 fixed-response control complete:** the exact C340 native manager preserves
rigid inter-ring rotation: all covalent family targets remain unchanged at ±30/90
degrees, with only nonbonded contacts changing. The existing angle restraints
resist junction bending; +5/10/20-degree tilts add about 0.00652/0.10587/1.64511
to the native angle target. No explicit plane change is justified solely by its
absence. Sampled derivatives pass at the initial, 30-degree spin and 10-degree
bend; all static terms stay fixed. This is not a quantum torsion profile, linked
model or refinement-survival approval. Both native attempts are stopped; the
first local harness field-lookup failure is preserved separately.

**C342 source composition complete:** an explicit DNA scaffold supplies the
sugar/phosphate; the free reference supplies its complete base. Both source hashes,
atom origins and configurations are retained. C116 connected whole-row ordering
avoids the observed eLBOW Z-matrix artifact without changing chemistry. A fresh
DY nucleotide build passes all 21 isolated checks; 192 focused and 192 installed
relocated tests pass. The failed lexical-order attempt is preserved. No mutation
alias, linked/terminal approval or model phosphate change follows.

**Historical C343 task (completed through later controls):** source-owned linked/terminal preparation and whole-base mutation gates,
reusing C133–C139 and later construction owners. Verify how the free-nucleoside
reference enters explicit backbone contexts rather than inventing phosphate
chemistry or activating a DY-name workaround. Retain junction survival as a
refinement check; no additional plane or altered angle weights now.

The earlier four-step DY plan is now represented by the completed-boundary table
above: source/representation, linked/terminal preparation, explicit ordinary
construction and the bounded covalent-only control all have recorded evidence.
Do not repeat them while awaiting a broader ChemDraw importer. The remaining
ordinary automatic selection, modified-input seed forwarding, NAR chemical roles
and advertised refinement-survival claims retain their own gates. Source/alias,
linked-context, preparation and process owners remain shared with other ligands.

Use this as a custom-source addition to Q07/Q12/Q14, not a replacement for the
existing mixed scaffold or held-out catalogue challenge. Close the task when an
installed, relocated ordinary mutation consumes the packaged definition and
retains the intended atoms, stereo, ring/junction geometry and honest residual
reviews. Global DY mutation support is **not enabled by C335**.

### Q08 — Explain persistent mixed-pair geometry

**Open; depends on exact source/NAR evidence, not more iteration budget.**
CGY–DX strain recurs from C27/C28 through the C149 endpoint. Compare intended
chemical state and NAR atom roles/targets, actual proxies, dictionary target
compatibility, initial placement and achieved geometry under a fixed objective.
Preserve valid source and negative controls; separate dictionary, construction
and optimizer causes. Do not infer a target error from high residual alone.

**Check trigonal centres after dictionary generation.** Start with the existing
three-neighbour carbon rule from C206/C208 and the C404/C406 native geometry
readback. Identify the centre from elements, bond orders and stereochemistry.
Compare the three bond lengths, the three individual angles and planarity in
the generated CIF, the prepared model, the restraints Phenix actually used
(targets and widths), and the refined coordinates. A flat group can still
have its substituent pointing the wrong way. Allow chemically justified
asymmetry. Ring substitution, formal charge, protonation and metal binding
matter when choosing an independent reference.

Use the [DF sulfur case under Q13](#df-sulfur-geometry) as the first example.
Flag a suspect target separately from a missing restraint or a model that
moved away from a delivered target. Where a saved fit permits it, compare
the local pulls from geometry and working diffraction in the same physical
direction. Automatic repair needs independent support for the intended
chemical state, target and width. Preserve the original definition and
record the candidate and its source. Qualify a repair through actual
refinement and restart, checking neighbouring links and stereochemistry.
Include a held-out, renamed example with a distorted but flat substituent,
a legitimate asymmetric trigonal centre and a tetrahedral control. If the
evidence is insufficient, retain the usable fallback and flag the site for
review. This is queued work. Q06 phosphate restart remains the next gate.

Done when the residual has a documented causal boundary and either a generalized,
source-authorized correction or an explicit scientifically usable/unusable
selection outcome. No restraint deletion, arbitrary softening, hand inversion or
longer run counts as the explanation. This is tool diagnosis, not an obligation
to solve this particular crystal structure before all software can ship.

## Chemistry transfer and coverage packages

### Q09 — Complete L-DNA and fluorinated-sugar workflow transfer

**Open. Depends on Q01/Q03/Q05/Q06 for ordinary completion.** C110's L-3GBI
whole-model recipe and ordinary membership pass are real. C133 later qualifies
source-projected L-DNA flank/terminal definitions. Return to the L-FANA geometry
case with those qualified flanks; the older C130 trial was never thereby rerun.
Then exercise the same graph/element/stereochemistry rules on a genuinely linked
ribo-fluoro/L-FDNA control and additional L-FANA bases as source evidence permits.

Done when all declared centres, base identity, both links and full junction-angle
coverage survive construction, ReadySet, final native qualification and bounded
ordinary refinement. Preserve the all-sequence recipe, explicit enantiomer-source
identity and collision-safe local NAR mapping. Synthetic renamed controls are
transfer regressions, not live L-FDNA support. Resolve the recorded DG native
hydrogen-name mismatch through verified mappings. Do not make “L-FANA” or an atom
spelling the permission to flip a centre, remove OP3 or change phosphate charge.

### Q10 — Finish connected PNA parameterization

**Open. Source network work is complete; native linked state is not.**
C114 supports explicit neutral amide source operations; C117/C118 qualify selected
whole-purine candidates; C119 freezes connected source networks. Implement a
reversible, source-bound native adapter for the final connected reaction state
and qualify actual linked numerics and construction. Pruning isolated monomer
terms is not sufficient evidence of an amide parameterization.

Done when a neutral connected PNA control and a held-out graph traverse exact
reaction/atom ownership, native inventory, derivatives, construction and selected
ordinary use (Q05/Q06), with no phosphate assumptions. Preserve the four unresolved
charged reacting-amine cases for Q13; do not silently neutralize them or claim
that isolated C/A/G controls qualify a PNA polymer.

### Q11 — Held-out linked alpha-L-LNA transfer

**Open. Depends on the existing C143–C150 gates and Q01/Q03.**
10C has a source/native isolated and two-copy numerical control; the separated
copies are not a connected polymer or physical stacking proof. Construct a linked
10C control through graph-derived ports, source-preserving placement, both native
junctions, exact NAR membership and fresh derivative/geometry checks.
9V9 was checked against its actual source in C486/C489. Its flagged OP3 is
a terminal neutral hydroxyl. Standard eLBOW introduced an unlisted sugar
O4′–base C4 bond; the existing C116 row ordering produced an independently
qualified isolated dictionary and retained all four source sugar centres
during base placement. The proposed bridge exceeded the 2 Å base-movement
limit. C490 now binds the successful isolated dictionary to the original
source and the specific failed native attempt. C491–C492 tested both reference
frames. All three host sugar hands match 9V9, yet sugar alignment leaves the
junctions 3.33 and 4.23 Å apart. Transferring the host glycosidic angle before
fitting also exceeded the base-motion limit at all five weights. The next
held-out check is a bounded linked pose that keeps the NARestraints pair and
both backbone bonds. These controls already cover a simple change of frame,
arm weight or host glycosidic angle.

C498 used a fresh TLN mutation card alongside ATL and the held-out 9V9.
All 21 isolated TLN checks passed. Of the existing 27 phosphate-arm fits,
13 preserved the 2 Å base limit for ATL and none did for TLN or 9V9.
Rotating the source-declared sugar–base bond by 30° increments gave a 9V9
pose within the limit, but its two adenine contacts were 4.38/4.42 Å.
NARestraints actually requests 2.8 Å for both contacts in all three cases.
Its sigmas are 0.2 Å for ATL/TLN and 0.4 Å for 9V9. The original host
contacts themselves measure 3.81/3.63 Å. Copying that host shape or
optimizing the two junctions alone leaves poor pairing. Use the existing
three-residue method when testing a candidate and measure both outer
junctions and neighbouring pairs. Keep the 2 Å ordinary limit.

C499 checked the alternate starting models directly in Phenix 2.2.1-6174.
Each four-residue model contained DG–locked sugar–DZ and the opposing
adenine. Phenix recognized the two native phosphate bonds, all eight
flanking angles, and the two supplied NARestraints bond targets with their
actual sigmas. All ten covalent targets and sigmas agreed with the registered
ATL control. All expected heavy atoms were present. TLN and 9V9 needed a
separate 5 Å diagnostic allowance to expose their junctions for this test.
They still exceed the ordinary 2 Å limit. Whole-duplex clashes, stacking,
outer junctions and diffraction remain to be tested for those two residues.

The source flag for 10C names a doubly bonded O3P with no hydrogen. LCA and
LCC flag OP2 while a distinct protonated OP3 remains unflagged. Automatic
construction requests review on all three. ATL, 9V9, LCG and TLN passed this
source flag check. Five other catalogue rows need a different topology.

Done when the held-out code uses the same maintained rules as ATL, including
negative stereochemical and incompatible-host controls, with no code-specific
script branch. Route qualified results through Q05/Q06 before advertising ordinary
support. Preserve the known correct refusal to force incompatible sugar hands
onto a canonical host.

### Q12 — Resolve catalogue mappings and maintain support coverage

**Open; C105 census is complete, catalogue support is not.** The pinned workbook
has 618 rows / 599 codes: 580 unique rows, eight equivalent alias groups and eleven
conflicting groups. Selected CCD graphs exist for 596 codes; DB/DE/DF are absent
from that source, which does not prove global unavailability. Preserve the reviewed
A1AAZ→DF bridge. Missing mapped names (1DP, 8YN, A1AAZ, DX, US3) and missing base
roles (2PR, 5PY, MTU) require explicit source/NAR decisions. A deaza carbon replacing
a requested nitrogen is not just a spelling alias. Missing marker or blank
phosphate cells are not chemical instructions.

Done when every code/row has pinned source availability, unambiguous operational
identity, role mapping, chemistry/linked/native/workflow status and a next action
for each gap. Validate collision-safe local codes against actual resources; a new
fake label cannot repair chemistry. Keep NAR ownership of pair/stack policy.
Attempt all families with actionable evidence and reviewed exceptions where
necessary; do not close the programme by labeling entire difficult families
unsupported. Name the workbook hash/version rather than assuming the installed
NAR package version identifies that workbook.

**Queued after the Q07 mixed-scaffold check — one construction trial for every workbook residue.**
Start from the C105 census, reconcile it to the exact NARestraints workbook shipped at test time,
and reuse earlier native results when the inputs, tool versions and checks match. Give each row a
record and run equivalent aliases once. Conflicting entries keep their separate row identities.

- Start every trial from a fresh copy of a fixed scaffold. Match the listed parent base to its
  site (for example, a C-like residue replaces C), and keep the partner and neighboring links.
  Use the verified L-DNA scaffold when the intended construction requires the opposite hand.
  Check the local sugar stereocentres against the source. Locked, arabino, mixed-handed and
  non-sugar backbones need their own evidence; a letter in a residue name cannot choose the frame.
  Record an ambiguous parent, unavailable frame or conflicting source as its own outcome.
- Ask Coot and Cedar to build the residue through the ordinary route. Read back the actual
  component, atoms, base attachment, sugar hand, base orientation and both backbone connections.
  Preserve explicit terminal-phosphate intent. Record where construction failed, whether a
  supported recovery worked, and which chemical pattern merits a shared repair.
- Select a small set *in advance* across base and sugar families, including a recovered case
  and matching scaffold controls. Run one Phenix cycle with the same observations and original
  Free-R flags. Record which atoms, restraints, links and stereocentres survived. This tests
  refinement behavior on a control scaffold; its diffraction data cannot establish that the
  experimental crystal contained the substitution. Retain compact per-row evidence and
  representative exceptions using the existing receipt and replay machinery.

### Q13 — Close chemical-state and attachment-policy gaps

<a id="df-hg-dt-comparison"></a>

**DF–Hg–DT donor-state evidence (C409).** The intended Hg bridge replaces the
N3 hydrogen on DF at A:12 and DT at B:4. The earlier refinement used two explicit
Hg–N3 restraints and had no H3 coordinate at either site. Both separately named
deprotonated sources passed isolated Phenix dictionary checks. Generation preserved
the declared N3 formal charge of −1 and the three source-relative sugar
configurations. Ordinary source selection retains the neutral parents. The
native monomer reader exposes partial charge only. The existing
ledger entry `declared_metal_donor_state_2026_11_19` binds the neutral parents,
native checks, independent review and site map.

**C410 matched refinement complete.** Hazel ran both five-cycle Phenix refinements
from identical heavy-atom coordinates and reflections. Rowan prepared matched
neutral controls using the generator settings of the deprotonated derivatives.
Both states kept the two Hg contacts, the same weighted base-plane memberships and
the original backbone links. DF's sugar–base distance and ring flatness improved,
while its thiocarbonyl bond moved farther from its own target. Heavy-atom targets
and their uncertainties both changed. The outcome cannot be attributed solely
to removing H or to changing formal charge. The cases remain unselected research
controls. Explicit metal donor-state integration remains a post-build decision.

<a id="df-sulfur-geometry"></a>

**DF sulfur geometry, 22 November.** The matched neutral QF1 targets came
from the Phenix 2.2.1-6174 eLBOW builder. Its N1–C2–S value was 126.83°,
and the metal-pair fit reached 135.32°. The independent, unrestrained crystal
structure of free 2-thiothymine gives 122.57(9)° for N1–C2–S and 122.80(9)°
for N3–C2–S. It has neither the sugar nor the Hg–N3 bond. Use it to flag the
distortion and require evidence for the appropriate donor state before changing
any targets or widths. [Primary structure, Table 1](https://doi.org/10.1107/S010827010201315X)
and [Alder’s source audit](https://github.com/vecchioni-lab/NASolve/blob/Alder/docs/metal-df-c2-angle-audit.md).

The numbered input measured 126.82° and 115.90° at the two sulfur angles.
After five cycles they were 135.32° and 108.70°. At that endpoint, moving
S1 back within the ring plane improved both angle restraints and the total
geometry score locally. Working diffraction favoured the other direction.
Holding the rest of the 5.06 Å DF–Hg–DT fit fixed and restoring the first
angle to 126.83° changed R-work from 0.306622 to 0.306667. The two-angle
penalty fell from 27.04 to 0.23. This isolates one improvement and its cost.
The correct metal-bound targets and their survival during a fresh refinement
remain open. Simon would favour supported local chemistry at this small
R-work cost. This observation is specific to this dataset.

C580 reread the native geometry from nine completed fixed-Hg FT controls.
N1–C2–S1 finished between 126.8° and 128.2° against the same 126.83°
dictionary target in all nine. These fits demonstrate delivery of that
target under the tested conditions. The earlier 135.3° result remains tied
to its separate fit. For a public cross-check, 9E20 is a 4.72 Å DF–Hg–5IU
structure with two Hg sites. The Hg nearer the two N3 atoms is 3.01 and
3.08 Å from them. Both deposited metal-link rows describe O4 contacts
to the other Hg. These coordinates provide a second example of the chemical
environment, with insufficient information to set a precise N3-bound sulfur
angle. [9E20 coordinate deposition](https://www.rcsb.org/structure/9E20)

**C374 DF source-state confirmation:** exact original, numerical, plane-added and
refinement dictionaries retain OP2 charge0/HOP2 and a single P–OP2 bond. Its
1.571 Å target (sigma0.022), versus OP1's1.473 Å (sigma0.012), is source-derived.
Source-preserving internal projection intentionally retains this nonreacting state.
Establish the intended linked phosphate state before any general H/charge/target
transition; coordinate OP3 removal and successful mechanical delivery do not
decide it. This is not a diagnosed cause of DF glycosidic stretching. Reuse the
existing Q13 contract; exact hashes live in `df_retained_phosphate_state_2026_11_17`.

C613 found the same OP2 distinction in internal 2MG, 5MC and 6MZ. Each source
and the ReadySet dictionary retained a neutral OP2 with HOP2 and a single P–OP2
bond. After the explicit OP3 reaction, Phenix still used P–OP2 targets of
1.572–1.581 Å. The three neighboring ordinary DNA controls used 1.480 Å for
both nonbridging bonds. Both five-cycle returns followed the respective targets.
A chemically declared conversion to an internal monoanionic phosphodiester would
need to carry H, charge and numerical targets together. Reuse the existing Q13
source-state work. The present result does not assign a proton from diffraction.

**C265 concrete holdover:** curated 1AP has singly bonded terminal OP3 with charge
−1 and no H. The explicit native backbone rule supports a neutral hydroxyl leaving
group, so it refuses this internal link. General support must identify the source
port by graph/state, preserve nonreacting OP1/OP2 and every retained charge/H,
record the exact leaving-group and total-charge change, and qualify the linked
native dictionary. Do not neutralize the source, bypass the explicit representation
rule or add a 1AP-only exception. C58's earlier unqualified/legacy pathway does not
establish this newer source-bound operation. Keep the refusal until that authority
and native evidence exist. Original acquisition itself passed.


**Open; incremental prerequisite for affected Q04/Q07/Q09/Q10/Q12 cases.**
C152 reconfirms the specific Q03 phosphate-state boundary: retained PDU/5PC
sources and numerical base dictionaries differ in HOP2/HOP3 and OP2/OP3 charge.
Account for the intended state and each source/site operation explicitly; the
linear-torsion omission neither repairs nor authorizes that state transition.
C153 closes Q03 diagnostic composition using exact-source saved candidates in a
separate complete-monomer control. It leaves this mixed-scaffold transition open.
Finish explicit source-preserving H/charge/protonation, atom aliases and attachment
ownership where current DNA/L-DNA or neutral amide contracts do not apply.
Include aliased terminal operations, charged reactive PNA states and a real
3′-phosphate/nonstandard-backbone example before claiming that support.

C191 adds a separate actual consumer failure: its declared neutral-purine DA
candidate is retained, then both isolated seeds assert `HOP2!="HOP3"`. C121
recorded the mapper assertion for DG. Preserve the exact C191 source, policy and
consumer evidence under `full_model_source_owner_2026_11_10`; this is not proof
that the source protonation is wrong, nor the same evidence as C152's source/
candidate state difference. C194's fresh diagnostics isolate a missing HOP2
translation entry, but adding that identity mapping alone exposes a second
failure: loaded DA and effective native Ad differ, leaving HOP2 unexpected and
without an energy type. Phenix's existing explicit per-residue CIF selection then
refuses an O3′–HO3′ terminal bond conflict at both seeds. Preserve strict conflicts
and both negative controls; neither is a qualified workaround. C166 5PC and C172
PDU retain both phosphate H atoms, all 21 conditional checks and exact saved proxy
signatures in the same experiment. Every experimental worker is rejected by
ordinary authentication; no new qualification/runtime is published.

The next native compatibility gate must join exact source-component consumption,
terminal-modifier ownership and observed effective state before versioned worker/
consumer/cache integration. Include mapper source and native-extension pins,
legacy cold replay, both coordinate seeds, current linked sites, unaffected and
held-out controls. Reuse the existing source-state/projection and process owner;
do not create another hydrogen-name classifier or retry scheduler. Standard-name
parser controls are not the Q07 modified-residue challenge. Do not delete or
rename source hydrogens, force an energy type or relax conflict checks merely to
bypass these failures. See the [C194 controls](cif-doctor.md#native-hydrogen-mapping-and-component-ownership-diagnostic-c194).

Done per operation when exact allowed changes have source authority, independent
native effective-state evidence, unaffected-site checks and a held-out graph.
Protect intended terminal phosphate; unwanted internal OP3 is governed by declared
link context, never a blanket add/delete rule. Keep source-relative stereochemistry
and experimental protonation separate from unavailable absolute CIP/charge APIs.
Use reviewed graph/hash/version-scoped exceptions if a native consumer errs;
never let a whitelist waive unrelated chemistry checks. Ask for scientific intent
only after available evidence and proven usable fallbacks cannot settle it.

### Q14 — Recover missing challenges and calibrate scientific findings

**Open; separate tasks with explicit evidence availability.** The original
8RO/DE and failed 1AP artifacts remain unclosed historical-source questions.
Use their exact hashes/graphs if available; do not equate public 8RO with lab DE
or search unrelated unpublished datasets by basename. Public controls cannot
retrospectively establish the cause of an unavailable failed input.

Also qualify finite-width plane/angle decisions and valid alternative torsions/
puckers against legitimate canonical, exterior-planar, unequal-sigma, metal and
improper controls. Preserve the reviewed 5CM correction's exact scope. Done when
repair-triggering classifications have documented false-positive controls and
calibration, while descriptive findings stay descriptive. Missing historical
fixtures may remain explicitly unresolved and limit the corresponding claim;
they should not block unrelated demonstrated chemistry forever.

## Delivery and explicitly separate work

### Q15 — One plain-language result and refreshed user explanation

**Open. Depends on Q05 and the chosen supported scope.** Join recovery, selected
fallback, remaining scientific questions and exact inspection commands into
ordinary reports and the solution PDF. Update the existing user-oriented CIF
Doctor explanation/PDF lineage and [human overview](cif-doctor-human-overview.md)
when the integration actually ships; keep the editable figure consistent.

Done when a student can see what was repaired, what will refine, what remains
uncertain and which exact checkpoint to inspect without reading CIF tables.
Keep selected versus latest explicit and do not call an isolated numerical pass
complete support. A developer review receipt is not mandatory student approval.

The November 26 audit consolidated the handoff and the current work order. Continue distilling the detailed guide/overview chronologies into stable public
methods plus clearly archived evidence, preserving existing anchors, original
verdicts and receipt hashes. Distill durable product architecture before moving
internal deliberation to the private notes repository. Do not copy live-run data
or chat transcripts into the public project. This is the documentation cleanup
already noted after C133, not permission to delete historical evidence.

#### Regional helix analysis for publication

**Open under Q15. Required before NASolve completion.** One offline analysis
should let a scientist measure a declared region in a model and compare the
same region across checkpoints. Willow needs it around a bend or an opening.
Alder needs it around a rotated cluster. Cedar supplies the chemical identity
and ring mapping at modified sites. The [machine-readable milestones](helical-geometry-plan.json)
hold the acceptance checks, publication benchmarks and current discrepancies.

1. **Identify the pairs.** Carry the two strands, residue and crystal-image
   identities, atom choices and region through each comparison.
2. **Measure twist and width.** Report signed **simple** twist per base-pair step.
   Preserve the P–P diameter across each pair and both phosphate-to-axis radii
   at each step in separate columns. A half-diameter is a derived half-span.
   Give the specific reason for an unavailable measurement.
3. **Export the evidence.** Show the steps flanking a modification, the weighted
   regional mean and bp/turn. Export individual rows, checkpoint differences,
   units, weights, coverage and model/method provenance. Qualify the same reader
   on deposited structures and on a genuine before/after bend. A report can
   accompany a solve without running another refinement or selecting a model.

The mmDNA benchmark uses Table S15 for simple twist and Table S17 for P–P
diameter. On 7SDF the first calculation gave 34.57° across the two flanking
steps (published 34.58°) and a P–P diameter of 18.19 Å (published 18.2 Å).
On 7SDG the local twist differed by 1.72°. Keep this comparison open.
On the curved 1TC3 duplex, both local phosphate radii reproduced the 3DNA
manual’s printed values across all 18 steps. The PNAS model’s 1 nm cylinder
radius is an input to its topology calculation. It supplies no experimental
radius target. [mmDNA](https://doi.org/10.1002/adma.202210938) ·
[Tertiary chirality](https://doi.org/10.1073/pnas.2321992121) ·
[Web 3DNA](https://doi.org/10.1093/nar/gkz394) ·
[3DNA radius benchmark](https://web.x3dna.org/public/3dna_old/doc/x3dna_v1.5.pdf)

### Q16 — Final integration, portability and retained-artifact closure

For NASolve completion, verify the [Q15 helix analysis](#regional-helix-analysis-for-publication) and publication export on the integrated build.

The specific C171 diagnostic-masking follow-up is resolved in
[C185](cif-doctor.md#preserve-primary-failures-during-diagnostic-reporting-c185):
all existing exception-note paths share best-effort handling, and a failed
prepared-repair progress write preserves the original error/timeout. Tests cover
missing/disabled/broken note support and unchanged ownership refusal. These run
on Python 3.12.14, including a relocated checkout; actual Python 3.10 execution
and full platform qualification remain part of the release gate below.


**Open; release gate.** Q04/Q05 acceptance is for the explicit serial route, not
default activation or arbitrary native campaign capacity. Review available disk
against whole retained requests, raw inputs, other stages and native scratch;
representative 100-dataset native deployment has not been run. Keep unknown/failed
work, pre-seal AutoSol exclusions, standalone ownership and historical migration
limits visible. State whether the proposed checkpoint ships bounded
explicit tools or the automatic engine, then review the actual Cedar→pine→main
diff and interactions with the other NARestraints/metal work. Run the unfiltered
full suite on the final combined source, relevant ordinary/native controls and
relocation with original paths unavailable. Exercise macOS/Linux process/path
assumptions for supported environments; record any untested platform explicitly.

At integration, keep Willow W35's fallback to the named RMSD header in
the returned Phenix PDB alongside Cedar/Alder's final log-table reader and
Cedar's per-cycle target and weight observations. On the C586 plane-only
return, both sources gave bond RMSD 0.037 Å and angle RMSD 4.408°.
Exercise W35's missing-log case, the preference for a valid final log,
and C589's target-switch case together on the merged reader.

C622 reproduced a Willow restart failure before any new round was reserved.
C607 had extended the live NARestraints reader to accept a frozen workbook.
The older phosphate workers still required the earlier reader bytes. The
installed Cedar package now supplies that exact reader to V10–V12. After
relocation all ten supported worker bundles matched every corresponding byte
from `d3d71cde`. Each phosphate bundle has 20 members, including its entry
and package initializer. Existing checkpoints and live workbook selection keep
their respective rules. Willow owns the actual descendant refinement.

Verify two other shared entry points on the installed integration candidate.
Willow registers five TopoStitch commands in addition to `nasolve`. Exercise those
commands and the existing chemistry entry point from that installation.
For Coot inspection, Alder already carries both Willow's map-origin record and
Cedar's check on the prepared model and dictionaries. Reuse that combined path.
Open a chosen preparation with an inherited map and verify which checkpoint
owns the coordinates, chemical definitions and map. The navigation record can
identify an inherited map even when its coefficient-generation policy is unknown.

Current qualified source and pending full candidates are recorded once in the
maintained [handoff](development-handoff.md); qualification follows the exact
source, not a branch name. Historical C391 `8ccec55b` passed 11,983 tests with two
existing native opt-in skips and 292 subtests in 3196.08 s. W135 independently
sealed 1,413 unchanged tracked files, exact NARestraints `a9264f9e` and stopped
process ownership. Commands, skipped-test reasons and hashes remain in ledger
`full_c391_regression_2026_11_18`. Older C220 green and C222 partial results retain
their original evidence; neither defines the current baseline.
C386's later unfiltered run finishes with 11,873 passed /46 failed /2 skipped
and 281 subtests (3266.71 s). W132 resolves all 46 on the exact source: host
process permissions give 45 passes and one residual; exact byte-identical
NARestraints Git-source metadata resolves the remaining source-bundle test.
No product fix or new skip. Preserve failed full and diagnostic reruns separately;
this does not establish an uninterrupted full pass or qualify later Cedar.
See ledger `full_c386_regression_resolution_2026_11_18` and W132 `5c107fb9`.
C169's interrupted run remains historical non-pass evidence. Final combined
Cedar/pine/main source still needs its own integration regression and native checks.
C220 also retires 89 audited old source-build copies and archives 1,353 older
validation scripts outside the product checkout, with byte verification before
removing redundant originals. Preserve published evidence and archive owned
runners under the [branch-artifact policy](collaboration.md#branch-artifact-archive-and-merge-cleanup)
before retiring branches/worktrees. Inventory first; do not clean unrelated runs,
old environments or user material. Keep older readers/receipts and documented
migration behavior. This queue does not authorize a merge.

#### Final implementation task — call the NASolve workflow AutoPhase

**Queued, not implemented; 2026-11-13.** After the agreed Cedar chemistry,
consumer and reporting work, rename the public NASolve workflow **AutoPhase**,
explicitly described as using **Phenix AutoSol**. This is the last implementation
task in Q16, followed by final combined-source validation and merge review;
it does not interrupt Q04/Q05 or authorize a merge.

The [machine-readable compatibility audit and plan](autophase-rename-plan.json)
pins the four audited branch heads, source boundaries, synthetic check and
acceptance criteria. Add public aliases through the existing implementation;
retain `nasolve autosol`, `phenix.autosol`, native `autosol.*` settings and existing
saved run/campaign identities. No bulk replacement or historical-run migration.
Preserve both Alder's exact HL phase-label fix and Cedar's checked-preparation
validation; recheck branches before implementation and reconcile correctness
separately from naming. An on-disk/schema rename is optional later work.

### Deferred extensions — retained, not hidden release requirements

- **ChemDraw references and restraint bundles:** future input support through an
  explicitly mapped chemical interchange (for example stereochemical SMILES or
  Mol/SDF after actual compatibility research), with graph/source provenance and
  numerical qualification. Drawing-to-model building is a separate workflow.
- **Sticky-end stitching / symmetry geometry:** user-deferred. C111 found distinct
  GC versus AT geometry/plane outcomes. Symmetry-image soft-bond exclusions,
  planes/parallelity gradients and large helix motion need their own design and
  native validation. Never turn complementary overhangs into an undeclared
  covalent pseudolink. Not a CIF Doctor release blocker.
- **Routine metal donor-state handling after NASolve is built.** Revisit whether
  to integrate site-specific donor definitions into normal metal preparation and
  refinement. Use the [DF–Hg–DT comparison](#df-hg-dt-comparison) to judge the
  benefit. The current build and Cedar merge can proceed independently of this feature.
- **Metal-pair GUI and unusual coordination:** coordinate through the existing
  metal-builder/NAR contracts and preserve the other branch's work. Do not infer
  metal valence or repurpose ordinary organic repair rules without authority.
- **Broader Doctor orchestration / guided human decisions:** retain data, Free-R,
  geometry and campaign evidence boundaries. A human decision needs exact inspected
  evidence and selected action before a future automated Doctor can propose it.

## History reconciliation and orphan-work audit

The [native ledger](cif-linked-native-registration-evidence.json),
[implementation map](cif-restraint-doctor-implementation.json),
[runtime contract](cif-doctor.md) and [methods blueprint](cif-restraint-audit-methods.md)
retain original outcomes. A historical “pending” is not reopened if a later record
closes it. Conversely, a later successful isolated control does not close an
unrelated linked or ordinary-workflow gate.

| Delivery range | Reconciled outcome | Current disposition |
| --- | --- | --- |
| Original blueprint / C00–C04 | Initial assessor, bad generated-bond quarantine, installed eLBOW option/source-state retention and reproducible IGU candidate. | Keep original design/failed-input evidence; automatic orchestration is Q04/Q05, missing challenge provenance Q14. |
| C05–C14 | Native modifier registration, singleton component metadata, terminal/outgoing state controls and Phenix CLI compatibility. | Later readbacks supersede early native-pending notes. Source state and unsupported charge readback remain scoped under Q13/Q06. |
| C15–C20 | Endpoint inventory, whole-fragment construction and source-retaining DF; saved-endpoint reload/serialization. | Reuse C18 DF evidence (C98); do not regenerate solely because it is old. Cutoff-created proxies remain distinct from deleted intended restraints. |
| C21–C29 | Exact NAR membership, parallelity derivative diagnosis/correction, bounded geometry and source-state review. | Numerical defect has a bounded diagnostic remedy; ordinary-consumer applicability Q06 and persistent pair strain Q08 remain open. |
| C30–C37 | Source dialect, bond-token, charge/stereo preservation diagnosis and controlled native translation. | Historical “run C33/C37” instructions are superseded, not current queue entries. Their source/chemistry findings remain evidence. |
| C38–C46 | PDU/5PC declared-linear terms, source/ReadySet ownership and exact effective changes. | General repair/attribution now C142/C149/C150; compose source-qualified selection in Q01/Q03. |
| C47–C58 | Generator constructor/stereo/order failures resolved into explicit source-preserving candidates and linked controls. | Temporary native stereo conventions do not permit molecular inversion; final-state extensions Q10/Q13 remain. |
| C59–C70 | Whole-model selection, portable bundle, Coot whole-base transport, frozen dictionary store and source alias route. | Bounded reuse exists; later policy/consumer cases still need Q04/Q05. |
| C71–C79 | Ordinary cache acquisition, truthful ReadySet trace/consumption, bounded transport and per-component ordinary arguments. | Implemented, not orphaned. Do not recreate these mechanisms in a new orchestrator. |
| C80–C95 | Mixed scaffold, source/link recovery, derivative/geometry/torsion work, portable endpoint and public runtime. | Old Mac-pending snapshots are resolved by later return/replay records. Public mechanics do not settle source-DF or final acceptance. |
| C96–C104 | Consolidated readbacks, source DF recovery, PDU derivative/precision diagnosis and exact omission inventory. | Reused by C142/C149/C150; ordinary mixed acceptance Q07 remains. |
| C105–C119 | Catalogue census, graph ports, reciprocal/native links, whole-model L-DNA, symmetry audit, name/H binding and connected PNA source networks. | G1 complete; Q09/Q10/Q12/Q13 retain family/native gaps. Sticky ends explicitly deferred. |
| C120–C133 | FANA source/stereo policies, explicit L-FANA identity, binding/placement, topology/derivatives, bounded geometry and repaired flank definitions. | Return to the actual geometry/workflow with repaired flanks (Q09); no blanket L-FDNA support. |
| C134–C141 | Focused-test policy, ordinary reuse checks, explicit policy storage, full native monomers, ReadySet bundle/serialization and public selected evidence. | Implemented components; missing ordinary composition is Q01/Q03–Q05. |
| C142–C150 | ATL source/native construction, generalized furanose placement, held-out isolated 10C, captured numerics/geometry and maintained linear repair attribution. | Mechanics now pass for the repaired mixed manager; no automatic or scientific adoption. Q01/Q03/Q07/Q08/Q11 remain. |

This audit also corrects stale top-level ledger pointers (C115 “current”, C37
“next”) while preserving their exact old values as historical metadata. The
2026-10-11 methods introduction now distinguishes implemented native diagnostics
from pending ordinary integration. The [original G1–G6 generalizer goals](https://github.com/vecchioni-lab/NASolve/blob/972a822244ad269067f76c2d2ed2f1746aa3196b/docs/development-handoff.md) explain the catalogue census, chemical identity, recovery, native proof, ordinary workflow and coverage. The numbered packages here own the remaining decisions.

Audit by Rowan · Codex desktop. Future contributors should record completion
against the job ID with exact code/evidence and remove only the open status, not
the historical scientific caveat it resolved.
