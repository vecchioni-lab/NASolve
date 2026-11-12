# CIF Doctor completion queue

**Current work order, 2026-11-12.** This is the one unfinished-work queue. The
[capability table](cif-doctor.md#current-capability-boundary) records demonstrated
support; the [handoff](development-handoff.md) says where work stopped. Old notes
record what was known then. They do not create a second set of instructions.

## Finish line and ordering

CIF Doctor should work quietly behind NASolve: preserve the intended chemistry,
catch bad dictionaries, repair what can be repaired, and give Phenix a model and
restraints that agree. Routine users should not have to edit CIFs. ReadySet and
NARestraints remain the tools that supply chemistry/numerical parameters and the
intended base-pair/stacking restraints; Doctor checks and connects their results.

Q01–Q03 are complete within their recorded diagnostic scope. Q04 is the immediate
work; Q05 carries its result into normal use. Q06 must pass before we claim that
the combined chemical examples refine correctly. Q08–Q14 retain the chemistry
learned along the way; they are not a reason to keep rebuilding Q04.

## Pipeline position

| Job | In laboratory terms | What still closes it |
| --- | --- | --- |
| **Q04 — prepare safely and recover interrupted work** | Coot builds the requested residues; NARestraints supplies their relationships; Doctor checks the dictionaries and ReadySet result. | C220 supplies explicit truthful result/continuation commands; connect their result to default PostMR/campaigns through Q05. C234–C237 connect explicit owned plane support inside the same repair machinery; complete automatic source-support acquisition in the outer request. |
| **Q05 — give every program the same chosen result** | Coot inspection and Phenix refinement must open the same model, CIFs and base-pair restraints. | C223 saves an explicit initial review checkpoint, including a checked fallback, and recovers interrupted publication. C224 connects ordinary PostMR; C225 adds explicit frozen campaign entry. Define later preparation children without replacing earlier choices. |
| **Q06 — show that real refinement reads all the restraints correctly** | Run Phenix with the complete NARestraints input, protected phosphates and correct Free-R flags. | Demonstrate actual refinement, including planes/parallelity. A successful dictionary-reading or energy check is insufficient. |
| **Q07 — prove the pieces work together** | Test K:X, D:T, Z:P, B:S, PDU:A, 5PC:G, 5CM:Q and DF:A with ATL alongside; include broken PDU and DF/A1AAZ. | Complete that combined run and the separate eight-modified-residue challenge using unfamiliar catalogue ligands, including compatible LNA:RNA/PNA combinations and a chemically specified phosphorothioate where supported. |
| **Q08 — explain stubborn distortions** | Find out why a pair or substituent remains strained. | Separate wrong targets, missing restraints, model geometry and packing; do not just optimize longer. Retain the CGY–DX and PDU questions. |
| **Q09 — preserve the correct sugar hand and fluorine geometry** | Carry the L-DNA, FANA, L-FANA and L-FDNA learning into ordinary model building/refinement. | Use atom connectivity and stereochemistry, not lists of residue names; complete linked and held-out controls. |
| **Q10 — handle PNA as PNA** | Respect its backbone and attachments instead of pretending it has a DNA phosphate. | Validate connected construction, native restraints and numerical behavior. |
| **Q11 — transfer the locked-sugar fixes** | Check another alpha-L-LNA example beyond ATL. | Complete linked 10C/held-out validation while rejecting an incompatible scaffold. |
| **Q12 — know the catalogue's actual coverage** | Account for every NARestraints ligand entry. | Turn the 599-code/618-row census into supported, repairable or specifically unresolved cases. A family example does not prove every member. |
| **Q13 — preserve chemical identity** | Keep hydrogens, charge, phosphates and attachment changes chemically justified. | Resolve ambiguous source states explicitly; a prettier geometry cannot authorize different chemistry. |
| **Q14 — make sure Doctor catches real errors** | Test broken examples and sound examples that should be left alone. | Retain reproducible challenge inputs and false-alarm controls, with unavailable historical inputs stated honestly. |
| **Q15 — tell the scientist what happened** | Explain what was repaired or retained, what remains uncertain and exactly what to inspect. | Refresh the ordinary result report and user PDF after the behavior is integrated. |
| **Q16 — finish the branch cleanly** | Check Cedar as part of NASolve, then review the proposed integration into pine/main. | Full regression, representative native/relocation/platform checks, honest release scope and reviewed artifact cleanup. No automatic merge is authorized. |

### The next small steps

1. **Preparation handoff — complete through explicit commands at C220:** show the checked ReadySet model or the
   independently checked starting model, with an honest explanation. Read an
   exact completed attempt without launching anything; continue an interrupted
   request only through the existing owner and a fresh numbered attempt.
2. **Use that exact result throughout normal preparation:** C223 closes explicit
   initial checkpoint publication and normal reads; C224 connects explicit ordinary
   PostMR; C225 freezes explicit campaign entry. Define later preparation children.
   Finish Q04/Q05 before Q06. Keep latest and selected distinct.
3. **Finish general plane repair:** C234–C237 run explicitly supplied owned support
   through the existing repair request, including real success and stopped-native
   fallback. Now obtain/freeze the necessary support through the outer owner, with
   shared deadlines and unchanged storage bounds. Preserve existing ring planes;
   PDU and 5PC are controls, not name-based switches.
4. **Run real refinement, then the combined and unfamiliar-ligand tests.** Use the
   results to close the relevant chemistry jobs, rather than adding a new queue.
5. **Refresh user reporting and review the release.** A smaller provisional
   integration may expose explicitly limited tools before all catalogue entries
   work; it must not advertise an unfinished automatic engine.

C219 already executed the ordinary Coot/NAR-derived request through generation,
repair and ReadySet, and reread the selected result with the original paths and
SDK unavailable. Reuse that evidence. Its PDU C5 still lacks an explicit complete
plane: near-planar coordinates alone do not prove the restraint is adequate.
C207–C216 supply the general mutation/plane checks and PDU/5PC controls; combining
the plane checks into ordinary repair now works for explicitly supplied owned
support. Automatic outer-request acquisition and whole-request storage remain work. DP's ambiguous correspondence,
source-H questions and PDU numerical targets remain visible limits.

These are work packages, not a prediction of session or commit count. Preserve
numbered attempts and all partial outputs; new attempts require proof that old
processes stopped. Preserve scientific acceptance thresholds, terminal-phosphate
intent, Free-R handling and NARestraints ownership. Run focused checks during
work, with the complete suite at cross-cutting changes and integration.

The detailed acceptance criteria below remain authoritative. The original
C00–C150 audit is retained at `a943386dd3a8e27dabeae316d37039d92e1cb9fc`;
its local index covered 71 documents and 286 milestone records. Raw science stays
outside Git. Older C206–C219 planning prose is retained in Git history.

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

**Open overall. C220 supplies the explicit preparation handoff; C223–C224 carry
it into an initial checkpoint and opt-in ordinary PostMR; C225 adds frozen campaign
entry. Default-route enablement and automatic chemical-plane repair remain unfinished.**
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

Remaining acceptance:

1. Reuse C223–C225's initial checkpoint, explicit ordinary PostMR and frozen
   campaign entry. A checked fallback uses its genuine preparation receipt,
   without a fictitious ReadySet-success label or log. Complete later preparation
   children through Q05. Default-route enablement remains an explicit decision.
2. C234–C239 join C226/C227 to the existing prepared repair request, with explicit
   owned support, real success/stopped-native fallback and compact exact proof.
   Next obtain/freeze that support through the complete request's generation owner,
   with durable child identity, shared deadlines and bounded storage. C240 now
   verifies a launched stopped negative generation without admitting partial output;
   C241 preserves its optional recipe flag through existing acquisition identity.
   Reuse these and the existing graph screen/narrow candidate. Do not add another
   executor. Earlier capability failures and zero-exit unqualified builds still
   need an explicit, equally strict fallback classification before broad coverage.
   Preserve existing ring-plane groups; add only source-supported missing members
   with owned generator/native/energy evidence. Do not substitute an entire
   multiple-plane generated CIF. Keep non-PDU controls and ambiguous/tetrahedral
   negatives; restraint membership alone does not establish achieved geometry.
3. Exercise ordinary dictionary reuse, missing/stale entries, successful repair,
   usable fallback, unqualified failure and interruption through those real callers.
   Never run legacy phosphate/site modifiers alongside the same owner’s modifiers.
4. Preserve old request meanings and exact replay, even when a later policy fixes
   an earlier limitation. No in-place retries, automatic source rediscovery,
   renewed attempt allowance or latest-file selection.

5. Keep completed evidence compact enough for 100-dataset campaigns. C228
   deduplicates/compresses publications: the C227 parent falls from 101 MB to 4.9 MB;
   a complete native ReadySet continuation is 43.1 MB including its 6.2 MB result.
   Cold read peaks at 86.5 MB temporary evidence. C229 freezes compact storage in
   new checked requests and forwards it through existing owners; old requests keep
   their layout. C231 executes a fresh complete ordinary-source request: its final
   result is 5.1 MB but the whole request is 134.5 MB. Cold replay and exact initial
   checkpoint handoff pass without scientific duplicates. Next define interruption-safe
   retirement of redundant successful working files only after all owners stop
   and the sealed result verifies. A small publication does not bound a campaign.
   Measure the entire request/continuation/publication footprint; retain exact
   inputs, tool/policy identity, necessary check results and a reproducible trail.
   Prefer deduplication/compression over weaker checking or larger disk allowances.
   Bound temporary expansion, process memory and concurrency as well as persistent
   storage. C230 removes repeat parent qualification; the real read still peaks
   near 684 MB resident memory despite an 86.5 MB temporary evidence footprint.
   C233 changes complete/continuation inventories to hash one file at a time;
   the same C231 whole read falls from 599 to 562 MB resident memory with identical
   results and 69.7 MB temporary evidence. This does not retire working files.
   Do not extrapolate a small archive into permission for 100 concurrent readers.
   C237 avoids a redundant composed-proof working copy; C238 references an already
   frozen native inventory rather than embedding it again. A real owned plane
   repair now retains 134.4 MB including its 4.5 MB publication, versus 195.9 MB
   before those changes, with identical chosen model/restraints. This is a prepared
   repair request, not a new complete outer-request/ReadySet measurement. C239
   refuses oversized combined support before reading more component trees.
   Preserve active/failed recovery evidence until known-stopped retention rules explicitly cover it; never
   silently clean existing scientific runs.

**Q04 holdover — finish chemical-plane repair before claiming closure.**
C208–C216's checked plane-completion machinery now has C226 maintained numerical
execution and C227 source-bound composition. C234–C239 now invoke these through
explicit owned support in the same immutable repair request. Automatic acquisition
by the complete outer request remains: persist exact source/recipe/child identity,
select a numbered stopped attempt, account for shared time and attempt allowances,
and preserve a checked fallback when an optional native attempt is demonstrably
unsuccessful. Unknown/malformed ownership cannot be treated as that fallback.
C232 already permits an actual parent grant below the frozen generation maximum.
C240 proves exact launched negative generation; C241 removes the acquisition
recipe-identity mismatch. Neither invokes automatic outer-request plane generation.
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

**Open. Depends on Q03/Q04.** C221 checks the complete restraint set before
inspection; C222 opens an exact checked preparation without adoption. C223 now
publishes that exact choice as the initial REVIEW checkpoint, including a verified
fallback. Ordinary inspection, refinement and AutoSol readers validate the saved
producer/compiler/result binding. New manual/refined models preserve its ordered
restraints and checked phosphate connectivity. Malformed entries cannot silently
disappear; movement cannot silently sever a recorded phosphate connection.

Interrupted publication resumes under the existing request lock using the same
sealed receipt and exact attempt; no native rerun, newer-file guess or reselection
occurs. Initial schema-3 adoption is explicit, not an automatic campaign behavior
or a claim of real refinement success. Legacy registries are not converted.

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

**Remaining acceptance:** define later preparation-child adoption without changing
an immutable earlier root. Reuse the existing request owner and publication path;
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
C206 adds an explicit achieved-geometry requirement: check parent-to-mutant
orientation, local trigonal geometry, retained ring planes and exocyclic coverage,
alongside triple-axis terms. Keep native membership, numerical consistency,
chemical target plausibility and achieved geometry distinct. Its successful
fixed-backbone diagnostic does not close this package.
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

C220 now passes the full suite: **9,178 tests + 276 subtests**. The exact
source/test/script hashes and command are retained in the C220 evidence record;
no source changed during that run. This replaces C160 as the current full baseline.
C222's full run passed 9,210 tests + 273 subtests and exposed one new optional-view
argument omission in Refine Doctor (three tests + three subtests). That one-line
compatibility fix passes 124 affected tests + 40 subtests; no full rerun, so C220
remains the last completely green full baseline. Subsequent bounded Cedar passes
use focused tests until a meaningful integration checkpoint.
C169's interrupted run remains historical non-pass evidence. Final combined
Cedar/pine/main source still needs its own integration regression and native checks.
C220 also retires 89 audited old source-build copies and archives 1,353 older
validation scripts outside the product checkout, with byte verification before
removing redundant originals. Preserve published evidence and archive owned
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
