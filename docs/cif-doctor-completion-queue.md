# CIF Doctor completion queue

**Current planning authority, 2026-11-03, after C163.** This queue owns unfinished
CIF Doctor work; the [capability matrix](cif-doctor.md#current-capability-boundary)
owns demonstrated support, and the
[handoff](development-handoff.md) owns the active checkpoint. Historical `next`
fields are evidence-time proposals, not current instructions. Update these stable
job IDs in place when work finishes or priorities change; do not start a second queue.

Audited source: Cedar `a943386dd3a8e27dabeae316d37039d92e1cb9fc`, including
C150 implementation `9bec89f721f69333bbe2d963c7df077d5a0d1ed8`. The review covered
the original blueprint, retained C00–C150 delivery/return documentation, current
contracts, history, both implementation/evidence ledgers and relevant source
callers. A local index hashes 71 document files (7,167,800 bytes) and extracts 286
structured milestone records. This was a documentation and integration audit,
not a rerun of every scientific experiment or a claim that every historical
artifact is available. Unpublished models, logs and data remain outside Git.

## Finish line and ordering

The intended product is a background chemistry engine around ReadySet and
NARestraints: inspect the declared source and actual effective bundle, recover
repairable faults within bounded attempts, qualify the result, retain a proven
usable fallback and hand the selected model/restraints to ordinary refinement.
Routine users should not edit CIFs or choose implementation flags. All ligands
in the selected NAR catalogue remain targets; a family-wide unsupported verdict
is an outstanding support gap, not completion of the generalizer.

A **provisional Cedar integration** can expose a smaller, explicitly described
assessment/reuse/diagnostic capability after its own final integration checks.
It does not require completing every family below, but must not advertise the
unfinished automatic engine. **Automatic-engine completion** additionally needs
ordinary recovery/adoption, representative and held-out chemistry routes, final
consumer qualification and honest coverage/reporting. All-catalogue completion
requires every catalogue entry to be accounted for and unresolved cases retained
as work; it cannot be inferred from a few successful family exemplars.

Q01 is complete at C151 and Q03 diagnostic composition at C153. Remaining priority is **Q04 → Q05 → Q07**, with Q06 qualifying the
actual refinement consumer before Q07 can claim refinement support. Q02 is complete at C161: curated CIF parsing is independent of line wrapping. Q08 diagnoses the known
mixed-scaffold geometry while Q09–Q14 close chemistry and evidence gaps. Q15 and
Q16 close reporting and release. Dependencies below concern completion evidence;
they need not prevent bounded design or fixture preparation. These are **16 work
packages, not an estimate of 16 commits or sessions**. Split a package into
bounded acceptance checkpoints under the same ID when needed.

For every package, retain immutable attempts and exact source/consumer/policy
bindings, add failing-before regressions, run affected tests plus appropriate
focused profiles, and record live versus dry-run evidence. Run full regression
on the final integration state. Relocation claims require the original path to
be unavailable. No package authorizes weakening chemical, NAR or diffraction
acceptance criteria.

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

**Open; active next package. Q03 diagnostic composition is complete; broader state cases depend on Q13.** Connect existing
source-preserving generation, representation policies, graph-selected repairs
and dictionary storage on ordinary cache misses or stale qualifications.
[`cif_postmr_cache`](../src/nasolve/cif_postmr_cache.py) currently reuses a narrow
qualified recipe and intentionally skips explicit representation-policy entries;
it neither generates a missing repair nor proves the ordinary fallback usable.
C153 demonstrates exact-source cache reuse after a bounded PDU timeout; ordinary
orchestration should consult that store before generation. A cache hit supplies
a candidate; it does not replace current source/site/derivative qualification or
a newly applicable graph-repair check. Preserve the failed
attempt and require a dead owned process before any fresh retry. The current
captured derivative adapter now qualifies genuine zero-parallelity contexts at
C154: the preserved exact-source PDU/5PC control passes fresh derivatives and
publication without an added custom request. This is one closed prerequisite,
not completion of Q04. Optional nonbonded-inventory captures still need support;
zero-context geometry trials remain unqualified and must not inherit a legacy
plane-correction proof. C153's declared NAR numerical control is evidence for
its own context, never an automatic workaround for a model with no custom restraints.

C155 closes one shared-resolver preflight gap: invalid snapshot parents now
refuse before cache lookup or acquisition/requalification callbacks. Valid
read-only misses remain non-mutating, and freezing rechecks the destination.
This is not durable reservation, process ownership or automatic recovery; those
acceptance gates remain open under this same package.

C156 closes the explicit source-generator invocation boundary: shared campaign
cleanup handles help/build SIGTERM, interruption and timeout; immutable intent,
child identity and verified-stop records survive partial execution. Read-only
inspection distinguishes old/missing, live, stopped and unknown evidence. Both
phases share one execution budget. Actual 5PC completion and deliberate PDU
timeout pass under Phenix 2.2.1-6174 without promoting chemical usability.

C157 closes the explicit generation-request ownership layer: frozen exact source,
recipe/native pins and attempt allowance; a persistent shared lock; immutable
numbered attempts; and read-only recovery observations. Unsealed attempts require
both coordinator and worker inactivity; publication gaps remain blocked. Explicit
retries preserve partial output and consume a fresh reservation. A real macOS
timezone identity regression is fixed. Separate request directories remain
separate coordination scopes, and the legacy one-shot API remains available.

C158 closes the explicit cache-first generation bridge: a current hit skips
generation, stale consumer evidence requalifies saved copies first, and a miss
performs one owned attempt plus independent chemical/native qualification.
Its distinct recipe maps source authority, dialect, steps and representation
permission; old recipes/producer identities are not silently relabelled. Actual
5PC generation/qualification/reuse and bounded PDU failure pass, with cold cache
reuse after relocation. This is an explicit component API, not ordinary adoption.

C159 closes the explicit retained-candidate bridge on a generation-recipe miss.
An exact-source/authority snapshot with matching representation permission keeps
its original recipe/producer/stopping proof. Current evidence is reused; stale
consumer/policy evidence is requalified on disposable copies. Recorded C153 PDU
and 5PC candidates pass fresh isolated native controls. The old failed PDU request
stays unchanged; no new generation is needed. Current generation-recipe entries
retain precedence. C159 compatibility replay reproduces C153's prepared model,
ordered CIF/PHIL bytes and both graph-repair steps exactly; no new whole-bundle
native or derivative qualification is claimed. This does not scan for candidates or recover from a failed
new qualification by silently trying another source.

C160 provides the maintained prepared-bundle repair executor. C159 acquisition
snapshots enter existing preparation; full native source/site checks, graph stages,
attribution, original/repaired derivatives and C152/C153 selection/publication now
run together. Valid failed improvement records can retain an independently
qualified original. Contradictory evidence and early native-stage failures stop
without a success claim. No graph fault launches no native job and remains a
non-selection, not automatic whole-bundle qualification. No scientific gate or
worker is replaced.

C162 closes the prepared-executor elapsed-allowance sub-gate: an optional
monotonic allowance begins before preflight, caps each worker to whole seconds
remaining, and refuses later work/completion when exhausted. Partial output,
including any late publication, remains intact and grants no retry permission.
Local work and cleanup remain cooperative; this is not whole-acquisition process
ownership or a hard deadline. Default per-phase behavior remains available.

C163 closes prepared-execution native process evidence: capture, derivatives and
attribution use campaign cleanup with durable identities and verified-stop seals.
Read-only inspection checks coordinator/worker inactivity without granting retry;
missing publication and unknown cleanup remain unresolved. Scientific artifacts,
selection and source authority are unchanged.

**Next bounded checkpoint:** wrap prepared execution in a frozen logical request,
persistent lock and finite immutable numbered attempts, using C157's generation
principles and C163's process evidence. Preserve partial outputs and authorize a
fresh attempt only after the previous coordinator and workers are known stopped.
Then establish whole-acquisition coordination around
source discovery, component qualification and prepared-bundle execution. Reuse
campaign/C157 request/attempt/phase identities and preserve every partial result;
own cleanup/recovery and a total budget rather than interpreting the new diagnostic
progress log as a process journal. Then extend deterministic qualified fallback
to early capture failures and no-repair candidates without manufacturing repair
proof or weakening current source/site/derivative gates.
Complete acquisition coordination must cover qualification/source-discovery
ownership and a total budget; C158 owns generation only and accepts a caller-owned
qualification adapter. Keep these explicit sub-gates under Q04 before ordinary
automation. No automatic retry loop or unqualified-source usability is enabled.

Done when cache hit, cache miss, stale consumer, bounded repair failure and no
usable candidate produce deterministic, truthful outcomes. Reuse passing content;
invalidate by source/state/site/order/policy/tool identity, and by coordinates
where relevant. Freeze chosen files into the run. Preserve durable attempt IDs,
process ownership and every partial output; a retry gets a fresh identity only
after the previous process is known dead. Test interruption, overlapping requests,
repeated selection and budget exhaustion. Reuse campaign ownership machinery
where appropriate; do not implement an unbounded repair loop or a second force field.

### Q05 — Ordinary PostMR continuation and immutable adoption

**Open. Depends on Q03/Q04.** Existing ordinary source/cache acquisition and
per-component ReadySet inputs work (C71/C79/C134). Later component-runtime,
whole-furanose, repaired-bundle and captured-geometry APIs remain explicit
components rather than an ordinary PostMR chain. Wire the selected model and
ordered effective restraint bundle through that chain and checkpoint lineage.

Done when recipes/models containing modified components reach final ReadySet
consumption and exact native qualification through ordinary entry points, then
publish one internally consistent selected model/CIF/PHIL/checkpoint. Cover newly
mutated and already-present residues, partial failure, valid fallback, latest
versus selected inspection and replay without historical host paths. Do not mix
an older model with newer dictionaries, rewrite a prior checkpoint, or promote
report-only findings into unreviewed universal gates.

### Q06 — Qualify the actual refinement consumer

**Open; can start independently, required before ordinary-refinement claims.**
C23–C26 identified and bounded a parallelity-gradient accumulation defect.
C147–C150 reuse a NASolve-local corrected evaluator. That proves those diagnostic
jobs; it does not qualify an unmodified ordinary Phenix refinement process.

Record exact installed capabilities/source/version and test the actual supported
refinement path with complete NAR pair/stack restraints. Decide an explicit,
reviewed compatible route or report an unsupported consumer; never silently patch
an installed SDK or drop restraints. Done when the selected repaired bundle is
consumed by ordinary refinement with preserved observations and Free-R authority,
source hands, terminal intent and exact custom membership. A bounded mechanics
success need not solve the test structure, but must establish the advertised
consumer behavior. Document unavailable formal-charge APIs honestly.

### Q07 — One mixed-scaffold ordinary acceptance run

**Open. Depends on Q02–Q06.** Retain all eight original pairs on one scaffold: K:X, D:T, Z:P, B:S, PDU:A,
5PC:G, 5CM:Q and DF:A, with **ATL alongside the existing pairs**, not PDU paired
to ATL.
Use explicit recorded identities (DF is the laboratory alias for A1AAZ), broken
PDU and source-changing DF inputs, and the same generalized recovery rules.
C146–C150 establish connected ATL, exact 201 custom restraints, repaired PDU/5PC
numerics and endpoint mechanics; they do not close ordinary adoption/refinement.

Done when an ordinary invocation acquires or repairs the necessary dictionaries,
qualifies the selected state and produces inspectable refinement artifacts with
all intended pair/stack membership, source centres, phosphate/H state and unaffected
sites checked. Include cache reuse and one changed-source rejection. Report
nonconvergence, residual strain and scientific uncertainty separately. A one-off
runner that chooses its repair from an ATL/PDU name does not satisfy this package.

**Queued closure challenge — held-out mixed modifications (Simon, 2026-11-03):**
After the current Q04 checkpoint, add a separate builder generalization control
before the proposed Cedar integration with main. Mutate **eight residues** into
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
**Queued for closure, not the next test; finish active Q04 work first.**

### Q08 — Explain persistent mixed-pair geometry

**Open; depends on exact source/NAR evidence, not more iteration budget.**
CGY–DX strain recurs from C27/C28 through the C149 endpoint. Compare intended
chemical state and NAR atom roles/targets, actual proxies, dictionary target
compatibility, initial placement and achieved geometry under a fixed objective.
Preserve valid source and negative controls; separate dictionary, construction
and optimizer causes. Do not infer a target error from high residual alone.

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
junctions, exact NAR membership and fresh derivative/geometry checks. Consider
9V9 only after checking its actual source, not from a guessed name/family label.

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

Consolidate the growing handoff/guide/overview chronologies into stable public
methods plus clearly archived evidence, preserving existing anchors, original
verdicts and receipt hashes. Distill durable product architecture before moving
internal deliberation to the private notes repository. Do not copy live-run data
or chat transcripts into the public project. This is the documentation cleanup
already noted after C133, not permission to delete historical evidence.

### Q16 — Final integration, portability and retained-artifact closure

**Open; release gate.** State whether the proposed checkpoint ships bounded
explicit tools or the automatic engine, then review the actual Cedar→pine→main
diff and interactions with the other NARestraints/metal work. Run the unfiltered
full suite on the final combined source, relevant ordinary/native controls and
relocation with original paths unavailable. Exercise macOS/Linux process/path
assumptions for supported environments; record any untested platform explicitly.

The C150 audit recorded 1,662 focused tests + 36 subtests and a C143 full baseline.
The current last full-tested implementation is C160
`d9e481661edcc3a04404df250360b9db63184ae1` (7,740 + 276); C161–C163 have focused
validation only. C163 passes 1,060 workflow tests + 45 subtests. None is a final
merge pass for the subsequent combined integration state. Preserve published evidence and archive
owned runners under the [branch-artifact policy](collaboration.md#branch-artifact-archive-and-merge-cleanup)
before retiring branches/worktrees. Inventory first; do not clean unrelated runs,
old environments or user material. Keep older readers/receipts and documented
migration behavior. This queue does not authorize a merge.

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
from pending ordinary integration. The G1–G6 handoff table remains the programme
summary and maps to this queue; it is not another ordering authority.

Audit by Rowan · Codex desktop. Future contributors should record completion
against the job ID with exact code/evidence and remove only the open status, not
the historical scientific caveat it resolved.
