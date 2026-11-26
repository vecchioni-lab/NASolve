# CIF Doctor completion queue

Updated 26 November 2026, after C590. Use this queue to choose the next experiment, the [handoff](development-handoff.md)
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
   contacts, then plan the separate eight-residue builder challenge with unchanged source
   dictionaries. Prefer unfamiliar catalogue ligands. Select exact sites and compatible
   sugar/backbone contexts, and include a phosphorothioate if its substitution and
   stereochemistry are specified. Record what was constructed, what Phenix kept after
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

Done when an ordinary invocation acquires or repairs the necessary dictionaries,
qualifies the selected state and produces inspectable refinement artifacts with
all intended pair/stack membership, source centres, phosphate/H state and unaffected
sites checked. Include cache reuse and one changed-source rejection. Report
nonconvergence, residual strain and scientific uncertainty separately. A one-off
runner that chooses its repair from an ATL/PDU name does not satisfy this package.

**Queued closure challenge — held-out mixed modifications (Simon, 2026-11-03):**
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
