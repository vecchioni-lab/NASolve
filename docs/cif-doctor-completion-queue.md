# CIF Doctor completion queue

**Current planning authority, 2026-11-11, after C198.** This queue owns unfinished
CIF Doctor work; the [capability matrix](cif-doctor.md#current-capability-boundary)
owns demonstrated support, and the
[handoff](development-handoff.md) owns the active checkpoint. Historical `next`
fields are evidence-time proposals, not current instructions. Update these stable
job IDs in place when work finishes or priorities change; do not start a second queue.

Original C00–C150 audit source: Cedar `a943386dd3a8e27dabeae316d37039d92e1cb9fc`, including
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

## Pipeline position

Current orientation after C198. This table summarizes the acceptance packages
below; update it with those packages rather than creating another backlog.
Q01/Q02 are complete; Q03 is complete within its declared diagnostic scope.

| Package | Position now | Remaining acceptance |
| --- | --- | --- |
| Q04 — recovery engine | Explicit owned chain implemented; package open at ordinary intake | C186–C189 bind required planes, original literal provenance or an existing source-bound C80 artifact, and an already frozen source selection. C190 rejects ungrouped atom alternatives at new context-bound intake/execution while retaining old readback. C195 makes ordinary construction consume verified snapshots; C196 records and binds consumed-source/model/intent evidence through the existing request and recovery. C197 supplies faithful source-bound literal intake without prior native capture. C198 validates actual ordinary Coot/NAR intake and connected repair after correcting complete-model scope; outer publication remains stopped at the 128 MiB evidence limit. Resolve versioned composed-evidence bounds first. Connect ordinary invocation with one modifier owner, then exercise ordinary hit/miss/stale/failure paths. Reuse the existing owner and C21/C80 compilers. |
| Q05 — ordinary adoption | Open | Carry one exact selected model/CIF/PHIL bundle through prepared and newly mutated routes into immutable checkpoints; retain source/producer lineage and selected-versus-latest behavior. |
| Q06 — real refinement consumer | Open; can proceed alongside Q04/Q05 | Qualify actual refinement with complete NAR restraints and Free-R authority. The corrected diagnostic evaluator does not establish ordinary Phenix behavior. |
| Q07 — combined acceptance | Open | Run the original eight pairs with ATL alongside, broken PDU and DF/A1AAZ, plus the separate eight-residue held-out builder challenge. Refinement claims depend on Q06. |
| Q08 — residual geometry | Open diagnosis | Explain persistent CGY–DX strain through source/NAR/native evidence; more optimization alone does not close it. |
| Q09 — L-DNA/fluorinated sugars | Partial evidence; package open | Transfer qualified flanks and stereochemical rules through linked L-FANA/additional bases and a real L-FDNA/ribo-fluoro control into ordinary use. |
| Q10 — PNA | Source operations/networks exist; package open | Qualify connected native state, construction and linked numerics; charged reacting states remain Q13. |
| Q11 — alpha-L-LNA transfer | Isolated 10C evidence; package open | Establish a held-out linked control using the ATL rules, retaining incompatible-host refusal. |
| Q12 — catalogue coverage | Census complete; support map open | Account for every pinned row/code, resolve mappings and retain actionable native/workflow gaps. |
| Q13 — chemical-state authority | Open, applied to affected cases | Resolve source H/charge, phosphate and attachment transitions explicitly; a numerical repair cannot authorize them. |
| Q14 — challenges/calibration | Open, evidence dependent | Recover exact historical challenges where available and establish false-positive controls; unavailable inputs limit their claims. |
| Q15 — user reports/docs | Orientation consolidated; product reporting open | Explain the selected result, remaining questions and exact inspection path in ordinary reports/PDF; complete the larger methods/history consolidation. |
| Q16 — release/integration | Open; C171 note-reporting subtask closed at C185 | Review the combined branch and compatibility scope; run full regression, ordinary/native controls and relocation/platform checks before integration. |

The immediate path is **Q04 intake → Q05 adoption**, with **Q06 consumer
qualification** before Q07 can claim refinement support. Q08–Q14 supply the
case-specific chemistry and coverage evidence, often exercising the same engine.
Q15/Q16 close the chosen release scope. A provisional
integration of honestly described explicit tools can precede all-catalogue
completion, but still requires its integration/release checks. No percentage or
fixed number of commits follows from these package labels.

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

**Open: the explicit engine is implemented; ordinary entry-point integration remains.**
Q03 diagnostic composition is complete. The current acceptance state is below;
the earlier C155–C173 narrative is retained in Git and the detailed
[methods](cif-doctor.md#complete-frozen-dictionary-requests-c171)/
[evidence ledger](cif-linked-native-registration-evidence.json), rather than repeated
as competing next-step instructions here.

| Acceptance boundary | Current evidence and scope |
| --- | --- |
| Frozen source and numerical identity | C155/C158/C159/C168 validate destinations, preserve curated/local/configured-CCD precedence, freeze the complete source set, reuse current exact-source candidates, requalify stale evidence and retain original recipe/producer/representation permission. No live rediscovery during replay or arbitrary source fallback. |
| Durable ownership and recovery | C156/C157/C163–C167 share campaign process cleanup, persistent locks, immutable numbered attempts and exact parent/child identities. Fresh attempts require known-inactive previous owners/workers; unknown publication/cleanup remains blocked. Prior partial outputs never change. |
| Complete bounded request | C169–C171 join exact successful acquisitions, model/sites, ordered PHIL, preparation and repair. Reciprocal parent ownership is durable; persistent component/generation histories prevent resetting attempts. One shared allowance includes final scientific replay/inventory. C184 extends that same owner to selected-runtime continuation, with exact input/owner joins and separately capped evidence partitions. Local work and cleanup remain cooperative, not a hard deadline. |
| Scientific selection and immutable output | C160/C172 share source/site/full-native/derivative checks, selector and publisher. No-graph originals need independent proof. Only qualified selected model/CIF/PHIL bundles publish; negative results can truthfully return no usable bundle. |
| Optional failure and original fallback | C173 binds optional native timeout or complete failed/unsupported worker evidence to the exact known-stopped job, declared inputs and maintained worker. Current consumer and independent original proof remain mandatory. Valid negative attribution/derivative results use the existing selector. Initial failures, malformed/contradictory reports, interruption and unknown cleanup remain blocking. No retry or renewed allowance. |
| One selected component | C174 reuses the same composer/preparer/request for 1–16 selected types. Linked-site synthetic regressions retain all occurrences and ownership. Actual isolated 5PC original/PDU repair controls and cold legacy/new replay pass. C178–C179 subsequently validate the same singleton scope through the separate ReadySet/native adapter. |
| Prepared-model context | C175 derives all selected sites and audited whole-model links from canonical prepared coordinates and frozen terminal/backbone intent, then freezes/rederives the proof. Linked/free-OH synthetic and isolated 5PC/PDU native controls pass. C176 extends the canonical bridge with explicit PHIL ownership; nonstandard backbone adapters remain open. |
| Ordered restraint ownership | C176 binds exact ordered explicit bond/angle/parallelity PHIL to the prepared model and reconstructs it before work. Supplied targets survive; the composer alone emits site modifiers. Maintained mixed-policy compiler output, actual original/repaired PDU/5PC controls and cold legacy replay pass. C186 adds exact plane unions/weights with old v1 replay and actual three-plane W-frame membership. C187 preserves original literal PHIL/native capture and compiler/workbook pins through owned request/result replay. C197 alternatively compiles that literal intent from readable source graphs without a prior capture, explicitly labelling PDB identities and preserving source bytes under the same owner. C188 alternatively retains the existing source-bound compiler artifact, exact source bytes and nonactive orientation evidence under the same owner. C190 requires grouped atom-name alternatives for new derivation/creation/execution, preserving exact historical readback. Actual native 3-versus-85 selection mismatch is reproduced and grouped controls agree. Unsupported PHIL and unowned pre-existing modifiers refuse. |
| Prepared-PostMR source entry | C177 derives both proofs, freezes ordinary source precedence and initializes the same complete request with mandatory qualification defaults. Actual fresh generation, current hit, stale requalification, retained repair, optional-failure fallback, no-usable and exhausted-generation controls pass; cold legacy/new replay passes. C189 also consumes an already frozen source selection with exact component coverage and no rediscovery; actual original/repaired and cold controls pass. This API remains opt-in; C182 derives current consumer/generator settings from the selected installation while preserving explicit source-reader/representation intent. |

**Next bounded checkpoint:** connect the validated prepared intake to ordinary
PostMR orchestration without a second recovery loop or modifier owner. C189 closes
the prepared entry's previously frozen source inlet. C196 now seals ordinary
construction before ReadySet and carries its exact declared producer/model/source
closure through that request. Ordinary invocation and modifier ownership still
need integration. Prefer exercising that
caller over adding another standalone orchestration wrapper. C197 closes supported
literal intake before native capture by sharing the C21 emitter and C80 actual/source
role checks. It preserves original intent and retained planes/edits under a distinct
source-bound policy, with no fabricated native indices. Invalid numerical rows may
remain preserved, but unreadable or inconsistent source graphs refuse. Actual W-frame
output is byte-identical to C187 and realizes all 201 native requests; isolated
original/repaired requests and cold historical/new replay pass. C187's native mode
and C188's existing explicit-source artifact remain exact alternatives; neither
permits re-guessing frozen intent or claiming numerical qualification at intake.

Keep three operational joins explicit: (1) preserve exact source/producer identity
from before construction; (2) let the qualified composer exclusively own site
modifications, instead of also calling legacy `write_linked_profile`; (3) carry the
exact selected model/CIF/PHIL and original intent lineage through ReadySet and a
new immutable checkpoint (Q05). Whole-request replay carries C187 provenance;
standalone selected-runtime export still needs that lineage connection. Reuse the
ordinary full-model C80 compiler for its established explicit route; do not add a
third pairing/stacking compiler. The separate full-model readiness audit selects
19 coordinate-guessed pairs/38 stacks; it must not replace the frozen 20-pair intent
with a new guess. C188 now carries that existing artifact for its explicitly
selected mode and qualifies all 193 requests in actual Phenix. Source authority and
normal native qualification stay mandatory. Native 201-request W-frame and isolated original/
repaired controls qualify C187, not all ordinary source-failure or chemistry cases.
The existing explicit entry already covers source/request assembly, current
installation configuration, original/repaired ReadySet/native selection and fresh
recovery with preserved failures. C184 joins them under one request and bounded
evidence inventory. Reuse that implementation; ordinary caller adoption needs
faithful input/selected-artifact binding, not another retry scheduler. Detailed
milestone evidence remains in the methods and ledger linked above.

The C193 redundancy/orientation check confirmed existing pre/post-Coot source
checks. C195 now makes ordinary Coot/context/restoration consume those verified
mutation snapshots and extends the same final guard to their bytes. Temporary
external-source changes no longer change construction input; changed/missing
snapshots and persistently changed originals refuse before ReadySet. C196 seals
that producer boundary, exposes a run-relative report reference and binds the exact
prepared model, overlapping source bytes and site policy through the existing
complete request. Only declared files are frozen; immutable recovery and cold
readback retain the lineage. This is not chemical qualification or a reconstruction
of every intermediate transformation. Do not add another record/hash wrapper;
the remaining joins are ordinary invocation/single-modifier ownership and Q05 export. The C71 reuse-only cache path, C21/C80 compilers,
C115 diagnostics, C185 failure notes and complete-request process owner remain
shared. Static tests have no shadowed definitions/imported collectable tests;
C134's three identical-text pairs still exercise different readers and remain.

The current [`cif_postmr_cache`](../src/nasolve/cif_postmr_cache.py) remains a narrow
reuse-only adapter and skips explicit representation-policy entries. Ordinary
ReadySet continuation and immutable checkpoint adoption remain **Q05**.

The C174 integration-seam audit narrows the next implementation boundary:

1. C175 closes the canonical no-supplementary-PHIL model/context portion:
   all selected sites, audited links and terminal/backbone intent are frozen and
   rederived. C176 closes exact ordered explicit PHIL membership and composer-only
   modifier ownership. Unsupported legacy inputs still need a faithful adapter. Ordinary
   `declared_site_context` currently records only OP3/passthrough policy; it is
   not a complete source-qualified declaration. Reuse existing readers and fail
   on unavailable intent rather than inferring a supported chemistry.
2. C176 establishes composer-only modifier ownership for explicit inputs.
   Ordinary `write_linked_profile` and the
   qualified composer both emit modifier PHIL; integrating them must not apply
   both to the same site. Preserve NAR targets and keep its stacking/pair edges
   distinct from covalent backbone links. C84's frozen-fixture context helper is
   evidence to reuse carefully, not a generic topology oracle.
3. C177 exercises that bridge through the owned request. Before enabling ordinary
   continuation, preserve the complete selected artifact contract. The newly mutated-model route additionally crosses pre-Coot
   source acquisition and post-construction qualification; retain its source,
   producer and generation-attempt lineage across that boundary under Q05.

C177 is the explicit prepared-model intake using C175/C176 context APIs;
ordinary orchestration and selected-runtime adoption are not enabled defaults.

Prior compiler reuse checked during C185: C21's
[`compile_na_policy`](../src/nasolve/cif_na_policy.py) already translates supported
literal Saenger 19/20 and mapped stack declarations while retaining non-SS lines;
its actual membership controls use captured native identities and existing custom
requests. C80's [`compile_explicit_na_policy`](../src/nasolve/cif_explicit_na_policy.py)
instead binds declared relationships and source roles to PDB record identities.
C176 already accepts the latter's maintained explicit output. Audit/reuse these
before introducing another compiler. Do not fabricate a native capture from PDB
indices, rerun pairing guesses, or discard required frame secondary PHIL merely
to fit the new context grammar. The ordinary bridge still needs its own faithful
input/retained-edit coverage and fresh native membership proof.

Concrete intake gate reproduced with the packaged W frame and NARestraints 1.1.3:
the ordinary builder emits eight bonds, fourteen angles, three parallelities,
three planarities and thirty-eight declared stacks. The complete ordinary input
first refuses the context's disabled-secondary-structure requirement. A separate
parser-only control retaining one exact generated plane also refuses unsupported
planarity grammar. Neither control runs Phenix or judges the chemical state.
Before ordinary adoption, support the required plane union selections and weights
through the existing context/native-binding machinery, preserving old artifact
meaning; then bind the supported literal pair/stack declarations faithfully.
Do not set `planes=False` or discard secondary PHIL to bypass either boundary.
C186 closes the plane-reader portion with native named-atom/weight checks and
legacy/new cold replay. C187 adds the explicit original literal-input bridge,
including strict grouped alternatives and actual native controls. C197 removes the
prior-capture prerequisite for readable source-bound literal graphs through the same
compiler; ordinary orchestration remains open. The C185
refusals above retain their original meaning; exact hashes remain under
`primary_failure_reporting_2026_11_10` / `intake_readiness`. The new evidence is
`planarity_intake_2026_11_10`. Historical v1/v2 selectors retain their recorded grammar for readback. C190
closes the ambiguous-selection intake gap using the existing strict selector: new
context derivation, request creation and fresh execution refuse ungrouped alternatives.
Actual Phenix demonstrates why (3 context atoms versus 85 native atoms per plane);
grouped controls agree. The ordinary bridge still needs independent native
membership and must never borrow PDB record indices as native capture evidence.

The C188 raw public-frame preflight refuses terminal phosphate B:1 without OP3
or a verified incoming O3-prime/P link. C189's prior-work review found the existing
C80 explicitly declared free-five-prime fixture preparation: a fresh diagnostic
copy removes its ten declared terminal atoms and passes context with 38 links.
The raw frame stays unchanged. Reuse this declared fixture operation; do not queue
a duplicate phosphate fix or interpret it as general permission to delete terminal
phosphates. A changed model needs its own compiler/native evidence; C188's 193-request
capture remains exact to the raw frame. Q13 still owns genuinely unresolved source
state transitions, including the previously recorded mixed-source H/charge issues.

C191 then freezes the prepared full-model control (eight DA sites, 38 links,
193 requests) but does not complete full-model execution. Exact-order generation
refuses ten purine order changes. Reusing C117/C118/C135's existing graph-selected
representation policy retains a candidate; both isolated native seeds then hit
C121's known `HOP2!="HOP3"` mapper failure class. Both requests/workers are stopped
and exhausted, with no runtime. This is a canonical negative workflow control,
not modified-ligand coverage or proof that the full-model consumer succeeds.
Keep the scientific refusal. C192 fixes the misleading ownership/completion
wording, names the failed seed and receipt, and preserves successful/failed
historical outcomes through relocation. C193 also exposes C115's existing
`SOURCE_HANDOFF`/`bond_orders` diagnosis at the earlier no-candidate boundary,
without claiming recovery permission or changing any scientific refusal. C194
separates the native mapper, effective-component and terminal-ownership boundaries
with fresh unqualified diagnostics; its Q13 controls do not close this Q04 gate.
Do not restart either request, invent another aromatic policy, or rename/remove
source hydrogens to force acceptance. Cold replay preserves both outcomes.

**Retained limits:** C154 proves genuine zero-parallelity derivatives; it does not
qualify zero-context geometry or optional nonbonded-inventory captures. A required
NAR restraint must never be silently omitted to fit a proven context. Source/state,
site, order, policy/tool identity and coordinates where relevant invalidate reuse.
Current fresh-generation success is contextual: C158 demonstrated 5PC generation,
while C167's fresh 5PC control exhausted an eight-second generation allowance
without retaining a candidate. Its hash-verified receipt and stopped-process seal
show a bounded timeout, not a demonstrated chemistry failure or a contradiction
of C158's success. Neither control establishes universal generation success.
No maximum-size throughput, new family, Linux-native or ordinary refinement claim
follows from these controls. Existing artifact caps and all source-chemistry gates
remain. Q13 owns unresolved chemical states; Q06 the actual refinement consumer;
Q07 mixed/held-out scaffolds; Q16 the eventual full integration regression.

**Done when** ordinary cache hit, miss, stale consumer, bounded repair failure and
no usable candidate produce deterministic truthful outcomes using this engine,
with selected inputs frozen into the run and interruption/overlap/recovery/budget
controls passing. No unbounded repair loop, second force field, in-place retry or
inference that process completion equals chemical usability.

### Q05 — Ordinary PostMR continuation and immutable adoption

**Open. Depends on Q03/Q04.** Existing ordinary source/cache acquisition and
per-component ReadySet inputs work (C71/C79/C134). Later component-runtime,
whole-furanose, repaired-bundle and captured-geometry APIs remain explicit
components rather than an ordinary PostMR chain. Wire the selected model and
ordered effective restraint bundle through that chain and checkpoint lineage.

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
previous outputs; actual fresh recovery and optional repaired fallback pass. Next
integrate the ordinary caller and checkpoint publication.
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

Consolidate the growing handoff/guide/overview chronologies into stable public
methods plus clearly archived evidence, preserving existing anchors, original
verdicts and receipt hashes. Distill durable product architecture before moving
internal deliberation to the private notes repository. Do not copy live-run data
or chat transcripts into the public project. This is the documentation cleanup
already noted after C133, not permission to delete historical evidence.

### Q16 — Final integration, portability and retained-artifact closure

The specific C171 diagnostic-masking follow-up is resolved in
[C185](cif-doctor.md#preserve-primary-failures-during-diagnostic-reporting-c185):
all existing exception-note paths share best-effort handling, and a failed
prepared-repair progress write preserves the original error/timeout. Tests cover
missing/disabled/broken note support and unchanged ownership refusal. These run
on Python 3.12.14, including a relocated checkout; actual Python 3.10 execution
and full platform qualification remain part of the release gate below.


**Open; release gate.** State whether the proposed checkpoint ships bounded
explicit tools or the automatic engine, then review the actual Cedar→pine→main
diff and interactions with the other NARestraints/metal work. Run the unfiltered
full suite on the final combined source, relevant ordinary/native controls and
relocation with original paths unavailable. Exercise macOS/Linux process/path
assumptions for supported environments; record any untested platform explicitly.

The last completed full-tested implementation remains C160
`d9e481661edcc3a04404df250360b9db63184ae1` (7,740 + 276). C169 passes its
focused/native/cold checks; its full run was interrupted at 68%, then explicitly
deferred by Simon. No fresh retry started and no complete full-suite pass is
claimed. Complete regression remains required for the eventual combined
Cedar/pine/main merge candidate. Subsequent checkpoints through C197 retain
focused validation, with native/cold evidence only where explicitly executed.
The latest workflow profile is C197: 2,048 tests + 45 subtests; it is not a full
suite. Preserve published evidence and archive owned
runners under the [branch-artifact policy](collaboration.md#branch-artifact-archive-and-merge-cleanup)
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
