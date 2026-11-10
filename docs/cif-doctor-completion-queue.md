# CIF Doctor completion queue

**Current planning authority, 2026-11-10, after C179.** This queue owns unfinished
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
| Complete bounded request | C169–C171 join exact successful acquisitions, model/sites, ordered PHIL, preparation and repair. Reciprocal parent ownership is durable; persistent component/generation histories prevent resetting attempts. One shared allowance includes final scientific replay/inventory. Local work and cleanup remain cooperative, not a hard deadline. |
| Scientific selection and immutable output | C160/C172 share source/site/full-native/derivative checks, selector and publisher. No-graph originals need independent proof. Only qualified selected model/CIF/PHIL bundles publish; negative results can truthfully return no usable bundle. |
| Optional failure and original fallback | C173 binds optional native timeout or complete failed/unsupported worker evidence to the exact known-stopped job, declared inputs and maintained worker. Current consumer and independent original proof remain mandatory. Valid negative attribution/derivative results use the existing selector. Initial failures, malformed/contradictory reports, interruption and unknown cleanup remain blocking. No retry or renewed allowance. |
| One selected component | C174 reuses the same composer/preparer/request for 1–16 selected types. Linked-site synthetic regressions retain all occurrences and ownership. Actual isolated 5PC original/PDU repair controls and cold legacy/new replay pass. The separate ReadySet round-trip adapter still requires 2–16. |
| Prepared-model context | C175 derives all selected sites and audited whole-model links from canonical prepared coordinates and frozen terminal/backbone intent, then freezes/rederives the proof. Linked/free-OH synthetic and isolated 5PC/PDU native controls pass. C176 extends the canonical bridge with explicit PHIL ownership; nonstandard backbone adapters remain open. |
| Ordered restraint ownership | C176 binds exact ordered explicit bond/angle/parallelity PHIL to the prepared model and reconstructs it before work. Supplied targets survive; the composer alone emits site modifiers. Maintained mixed-policy compiler output, actual original/repaired PDU/5PC controls and cold legacy replay pass. Unsupported PHIL and unowned pre-existing modifiers refuse. |
| Prepared-PostMR source entry | C177 derives both proofs, freezes ordinary source precedence and initializes the same complete request with mandatory qualification defaults. Actual fresh generation, current hit, stale requalification, retained repair, optional-failure fallback, no-usable and exhausted-generation controls pass; cold legacy/new replay passes. This API remains opt-in with explicit native profile/recipe settings. |

**Next bounded checkpoint:** connect the validated prepared-model intake and
selected runtime to ordinary PostMR orchestration, preserving the selected native
profile, pre-construction source/producer lineage and exact NAR compiler intent.
C177 closes source/request assembly and demonstrates the required acquisition
outcomes through that API; it does not enable the ordinary default or checkpoint
adoption. Coordinate the remaining caller integration with Q05. C178 validates singleton consumption/fallback; C179 reuses C09's loop writer at
combination and records its policy, with exact old scalar replay. Actual singleton
ReadySet now passes all eight consumption and 28 endpoint checks, with identical
energy/gradient snapshots; old rejected evidence still remains a fallback. These
prerequisites close no ordinary-adoption or refinement gate. Do not add a second recovery owner.

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
strict fresh endpoint acceptance and preserved legacy outcomes. Audit the remaining
supplement-filter writer before broad ordinary integration: reducing a metadata
list to one row currently uses the generic scalar serializer. Then bind the
**selected original or repaired runtime**, rather than rebuilding from an earlier
prepared dictionary, through ReadySet and final native qualification.

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

Compatibility follow-up found during C171: audit the pre-existing direct
`BaseException.add_note` calls in C164/C167 against the declared Python >=3.10
floor. C171 guards its own note path and tests an exception without note support;
no Python 3.10 interpreter execution is claimed here. Preserve the original
failure when recording cleanup diagnostics fails or notes are unavailable.


**Open; release gate.** State whether the proposed checkpoint ships bounded
explicit tools or the automatic engine, then review the actual Cedar→pine→main
diff and interactions with the other NARestraints/metal work. Run the unfiltered
full suite on the final combined source, relevant ordinary/native controls and
relocation with original paths unavailable. Exercise macOS/Linux process/path
assumptions for supported environments; record any untested platform explicitly.

The C150 audit recorded 1,662 focused tests + 36 subtests and a C143 full baseline.
The last completed full-tested implementation remains C160
`d9e481661edcc3a04404df250360b9db63184ae1` (7,740 + 276). C169 passes its
focused/native/cold checks; its full run was interrupted at 68%, then explicitly
deferred by Simon. No fresh retry started and no complete full-suite pass is
claimed. Complete regression remains required for the eventual combined
Cedar/pine/main merge candidate. C170–C174 also have focused/native/cold validation only,
with no full suite requested. Preserve published evidence and archive owned
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
