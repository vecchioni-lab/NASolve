# NASolve development handoff — integrated development base

Updated **24 November 2026**. Active integration target: **Alder**. The everyday
Pine and the separate Cedar/Willow branches are not changed by this integration. This base
combines the existing metal feature with the qualified shared chemistry, native
observation and storage owners; it introduces no new scientific policy.

## Current metal-science edge

A01 remains partial; A02 f″ remains gated. The
[constructed-seed receiving comparison](metal-development-handoff.md#a01-constructed-seed-receiving-2026-11-24)
now shows a local crystal connection surviving the same W252 phased refinement:
P–O3′ 1.618→1.615 Å and C3′–O3′ 1.454→1.448 Å, while the original-start control
remains distorted. The seed is separately source/chemistry/output-qualified,
not a converged or selected parent. All 853 other coordinates and B/Q/f′/f″ stay
fixed. Native execution is complete/stopped; 2,204 endpoint, 939 chemistry/source
and 4,718 receiving cold checks pass. Prior iteration-limit/unavailable-audit
verdicts remain intact.

Rwork/Rfree remain high (0.3081/0.3427), with weak/negative local map support.
Do not promote the model or infer f″. The [matched DNA-only XYZ/group-B design](metal-development-handoff.md#a01-dna-only-comparison-design-2026-11-24)
now has 1,240 source/input and 20 source/design checks: 858 DNA atoms and 42 groups,
with Hg XYZ/Q/B/f′/f″ held throughout. Explicit groups and disabled atomic ADP
back-trace are required. Both exact inputs now [pass native initialization](metal-development-handoff.md#a01-dna-initialization-2026-11-24)
through the existing V11 owner (zero cycles; 88 cold checks), with source phases,
flags and fixed Hg observed. A recovered selector-serialization failure remains
preserved. Optimization-stage admission is next; no broader fit has run.
The old whole-model control lacks the join. D7→C8 and coupled metal/base
placement remain distinct.
The report/figure is `ScienceCheckouts/Hazel/2026-11-24_ft-seed-receiving/index.html`.
Exact evidence is under the three `Alder/a01-constructed-seed-*` anchors dated
20261124-01. No additional native work is queued for this comparison.

The [pure helpers](topostitch-feasible-diagnostics.md) at `7c2e1c41` retain 53
focused + 99 adjacent + 53 installed tests and 531 cold replay assertions.
This follow-up changes documentation only; reuse those receipts. No raw science
commit, pruning, runtime/schema/default change or full-suite rerun. The prior
integration checkpoint below does not imply new release qualification.

## Qualified integration checkpoint — test-only amendment

The integrated candidate `1acc7892d2bc19d5572d46f430b27515a7ea6301` combines
Alder `6dc98e28`, Cedar `f83562b0` and the exact W145 adaptation `ae092936`.
The full unfiltered run completed with **1 failed, 12,845 passed, 2 skipped,
298 subtests passed in 4582.29 seconds**. All 1,501 tracked files stayed exact,
the checkout stayed clean and the test process stopped. Preserve this failed
gate; it is not a combined full PASS.

The sole failure is the extra-restraint case of
`test_unsupported_scientific_scope_is_not_dropped`: its supposedly external file
was inside the repository when pytest scratch was located there. The real
resolver correctly accepted that portable reference. Test-only amendment
`834b6b94b3c34d973bfc18142bb9934ed413421c` declares a fixture-local repository
boundary and asserts that the negative input has an absolute reference. The
complete counted-autorefine module passes in both layouts: **35 tests in 48.77 s**
inside a repository and **35 in 26.58 s** outside. Both processes stopped;
source files stayed exact. Runtime behavior and scientific policy are unchanged.

The project cadence was clarified after this afternoon checkpoint: complete
suites for substantial cross-cutting changes, focused checks for bounded fixes.
The cross-cutting runtime already completed its full execution; the follow-up is
only the reviewed fixture correction and documentation. Both subsystem reviewers
accept qualification on the **completed full execution plus focused test-only
amendment**. Runtime, native workers and all package resources remain byte-exact.
This is an explicit development integration decision, **not a fresh all-green
full-suite result**. Preserve the original failed full and both focused receipts.
There is no reason to repeat unchanged scientific/native controls for this fix.

Delivery targets Alder only; Pine and scientific acceptance remain unchanged.
The current decision/delivery records are `qualification-decision.json` and
`delivery.json` under the established Alder artifact anchor
`integration-20261119-01/`. The earlier `plan.json`, held checkpoint bundle and
afternoon report retain their evidence-time state; they do not supersede this
decision. No replacement full suite or scientific refinement is active.

Installed qualification passes for all **344 packaged files**, with the build
source and old installation removed. Old compact FT_Hg/Ag4 records, C406/C407
raw/scalar readbacks and ViewProfile positional compatibility remain exact.
W145 real map-origin reads preserve all 130 source-run files. W145 records map
selection ancestry, not the coordinates that generated a map. The independent
delivery audit passes 402 checks; its documentation-index finding is corrected
here. Willow's later W146 inspection and W147 coefficient-reader/worker patch
remain separately qualified follow-ons, outside this candidate. Reuse them.

Exact full commands, log, XML, source manifest and result remain in `full-suite/`;
the two correction commands/results are in `fixture-correction/`; package
commands and probes are in `installed/`, all beneath the integration anchor.
Tests use `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=src` plus the explicit clean
NARestraints `a9264f9e` source, Python 3.12.14 and pytest 9.2.0. The two skipped
tests require explicit native opt-in. The source/installed gates do not execute
a new scientific Phenix refinement. These records remain distinct from separate
historical Alder and Cedar full passes.

The 22 November A01 final-state, contact-hold and split-base freedom comparisons
are complete. A small shared score improvement does not repair the stretched DF
attachment or inherited internal strain. Straight and bent FT_Hg remain competing
hypotheses; the human endpoint is a comparator, not ground truth. The
[current metal science record](metal-development-handoff.md#a01-current-science-coupled-placement-does-not-survive-open-refinement)
owns exact native evidence and the next internal-geometry retention contract.
A further bounded native diagnostic qualifies simultaneous source-targeted
attachment distance/angle correction under the existing nine first-order holds.
The minimum-motion direction improves geometry but worsens work MLHL; 11 internal
terms stay fixed. This does not rule out other directions or qualify finite
retention/internal repair. **54 derivative checks and 451 independent assertions**
pass, with no new refinement, maps or fitted structure. The handoff records the
report-only serialization correction and inherited console-label erratum.
A01 remains partial and A02 gated. The latest compact report is
`ScienceCheckouts/Hazel/2026-11-22_ft-joint-target/index.html`; earlier model/map
comparisons stay intact, with no generated science committed.

A04's latest bounded prerequisite binds newly admitted preflight/main process
owners to the complete session declaration and unique reservation before launch.
It rejects another identical-input trial's owner while retaining historical
unbound behavior; missing terminal/phase receipts remain held. **137 distinct
focused cases across bounded runs, nine relocated installed tests and four cold
readbacks** pass; **357 package members** match. Only three metal process/session
modules change; scientific/shared process owners are unchanged. The additive
metadata costs 590 bytes in a complete synthetic session. The
[current handoff](metal-development-handoff.md#a04-current-checkpoint-cooperative-storage-reservations)
records the test-only correction, exact commands, compatibility and next recovery
boundary. No migration, recovery, retirement, scientific acceptance or new full
suite is claimed.

A04 also has an additive read-only held-session diagnostic and explicit-path
CLI. It names missing receipts/phases and requires a separate failure pin before
reporting a ready route; no allowance is released. **117 focused / 19 relocated
installed tests** and two cold witnesses pass, with **357 package members** checked.
All prior runtime modules remain unchanged. The [current metal handoff](metal-development-handoff.md#a04-current-checkpoint-cooperative-storage-reservations)
owns exact commands, report and limitations; no unsealed recovery is claimed.

A04's underlying bounded runtime follow-up **`86d34a16`** is pushed on Alder: explicit
settlement now releases unused future allowance for a newly bound, sealed stopped
partial preflight with no main child/review. Files remain. **184 focused / 105
relocated installed tests** pass, with 356 package members checked. Earlier
native-failure formats retain their behavior; old readers refuse the new
preflight kind/version. See the [metal storage handoff](metal-development-handoff.md#a04-current-checkpoint-cooperative-storage-reservations)
for schemas, exact commands, measurements and limits. This focused qualification
does not relabel the preserved integration full-suite result above. Pruning,
scheduling, unsealed recovery and scientific acceptance remain open.

Today's scientific readback and small storage rehearsal are in the
[metal handoff](metal-development-handoff.md). A01 remains partial, A02 gated,
and A04 partial. The afternoon checkout at
`ScienceCheckouts/Hazel/2026-11-19_integration/review.html` beside the repositories
preserves the held stage and scientific tables. Its adjacent `delivery.html`
records the subsequent qualification decision, without rewriting that evidence.
Only owned test scratch may be retired after retaining diagnostic evidence;
scientific inputs, outputs, shared installations and parent checkpoints remain.

The 20 November A01 diagnostics, matched ordinary continuations and explicit
local angular alternative are complete and stopped. The stronger metal-centred
term opens the Hg bridge, but leaves a short Hg–O4 contact and stretched base
attachment, with worse R values than the unchanged continuation. Native delivery
and cold readback pass; no scientific endpoint, default recipe or f″ parent is
accepted. A01 remains partial, A02 gated. The subsequent read-only movement-region
inspector enumerates the explicit whole-residue/metal region, fixed flanks and
crossing captured bonded terms; it does not move coordinates or qualify closure.
The metal handoff owns the new API's focused tests, preserved sandbox-failed
chemistry profile and passing eleven-case process-permission recheck. A subsequent
private 25-case P–O3′ pivot study reuses shared arithmetic and preserves all four
flanking bond lengths, while retained attachment strain and limited donor span
prevent a solution claim. The current editable report is
`ScienceCheckouts/Hazel/2026-11-20_pivot-motion/review.html`; no candidate PDB,
new native fit or modified-metal admission follows. The preceding junction
figure and local-angle maps remain retained. A04's separate modern-parent recovery
proof
now passes 876 cold checks and 16 synthetic refusals with no native calls or
source changes. The subsequent additive parent-layout adapter passes 96 focused tests and an
installed 876-check recovery with all 346 package files exact. Only the new
transport API/schema changes; existing readers/native workers stay unchanged.
Scientific session, full software identity and retirement remain open; the
[storage contract](metal-campaign-storage.md#implemented-fourth-step-explicit-parent-layout-transport)
owns that boundary. No full-suite rerun or new scientific acceptance follows.
A09 remains deferred until after the main A01–A08 build.

## Scientific scope and owners

The additive A04 recorded-result inspector now reads existing input archives with
explicit archive/projection/trial/expected-parent pins and preserves the distinction
between recorded statistics and a fresh native audit. **117 focused tests** pass;
**718 installed assertions** cover exact historical Hg/Ag4 readback and refusal
without original source/data access. All 348 packaged files remain exact. No
persisted schema, native worker, cleanup policy or existing reader changes. The
[storage contract](metal-campaign-storage.md#implemented-result-inspection-from-the-input-archive)
owns the command/evidence and remaining scientific lifecycle boundary.

The parallel A04 recorded-execution proof now cross-binds a saved historical Hg
result, its exact legacy parent and inputs, and its recorded worker/native/resource
identity after relocation. The private read passes 213 assertions and 11 refusals
without a new native call. Complete environment identity, scientific acceptance,
reuse and pruning remain unqualified; see the
[storage contract](metal-campaign-storage.md#recorded-execution-and-parent-cross-binding).
This follow-on changes documentation only and does not repeat runtime tests.

The completed-batch `metal publish-fdp-inputs` path now issues an independently
pinned review receipt with shared parents and exact trial/result identities.
Existing archive/trial formats remain unchanged. Sixteen final focused tests and
installed two-trial synthetic readback cover completion/interruption; no native
fit, cleanup or extra parent replay occurs. See the metal storage contract.

The additive `metal inspect-recorded-fdp` CLI reads one explicitly pinned
historical attempt without original-run/native discovery. It passed 53 focused
tests and relocated installed Hg/Ag₄ readback; schemas/defaults and scientific
acceptance remain unchanged. See the metal handoff and storage contract for
the exact historical-evidence boundary. No full suite or native fit ran.

A later investigator clarification confirms the FT B:7 O3′→B:1 P symmetry
continuation and subsequently the C/D crossover, with A:1–A:21 verified in all
three pinned source stages. D:1 remains terminal. The metal handoff distinguishes this new chemical intent from
coordinate-derived operators and the still-unqualified native symmetry policy.

The independent FT declaration audit preserves all nine current input pins and
identifies B:1/C:8 cross-symmetry connection intent and an ordinary selected
checkpoint as missing admission inputs. It preserves phosphates and all 19 pair
planes; the native inventory is not used to invent intended links. The isolated
W173 synthetic endpoint consumer refuses modified/metal permissions. See the
[metal handoff](metal-development-handoff.md#independent-ft-declarations-and-remaining-symmetry-input)
for the 90 source checks, 13 scoped refusal checks and remaining scientific limits.
This follow-on changes documentation only; no refinement or full suite runs.

The later source-bound symmetry diagnostic supplies exact B:1/C:8 contact
hypotheses and compares selected MR, original PostMR and current coordinates.
It preserves unresolved chemistry, D:1 terminal intent and the absence of an FT
slicing packet. Independent enumeration and an existing non-FT synthetic
continuation reader pass 46 scoped checks; no native work or new engine follows.

The bounded A01 coordination-topology follow-on adds an exact metal declaration
adapter and optional shared-checker input. Ordinary schema-1 calls stay unchanged;
explicit typed calls return schema 2. **309 focused tests** and **269 saved-data
checks** pass, with stopped processes and unchanged scientific inputs. Native
workers/defaults stay unchanged; no new refinement or full-suite result follows.
The FT_Hg control retains all supplied terms and no extra inter-base covalent
bond, but legacy whole-topology authority remains REVIEW. The
[metal handoff](metal-development-handoff.md#a01-current-checkpoint-explicit-coordination-topology)
owns exact commands, source files, schema limits and the next retained-parent
boundary. Generated science and local checkouts remain excluded from Git.

The bounded A04 follow-on `26b0f41c02abb44317f8579e12b6b8782d572e68` adds
only the input-transport adapter, its tests and documentation. Existing runtime
owners/native workers remain unchanged. Its **86 focused tests pass in 51.35 s**;
all tracked files remain exact and the process stops. Source/data relocation is
covered. The source-free relocated installation has **345 exact packaged files**
and reproduces saved FT_Hg/Ag4 inputs plus complete compact records. Original
scientific runs stay unchanged, no native job runs, and temporary views close.
Exact plans/commands/results are under the local Alder artifact anchor at
`input-archive-20261119-01/focused/` and `input-archive-20261119-01/installed/`.
Focused cadence applies to this additive adapter; no new full-suite pass is claimed.
The last complete shared-runtime execution remains the explicitly recorded
`1acc7892` run and its test-only amendment above.

| Scope | Current boundary | Maintained handoff/queue |
| --- | --- | --- |
| Metal geometry | **A01 partial**: FT_Hg source terms reach the native manager, but open XYZ/B geometry is unresolved; A02 stays gated | [Metal handoff](metal-development-handoff.md), [A01–A09 roadmap](metal-development-roadmap.md) |
| Modified-residue construction/refinement | **Q06 open**: PDU/DF geometry survival remains unaccepted; C406 records declared local terms without changing the fit | [Chemistry handoff](chemistry-development-handoff.md), [completion queue](cif-doctor-completion-queue.md) |
| Lean metal storage | **A04 partial**: inventory, compact records and exact input transport exist; explicit parent transport qualified; scientific lifecycle, native regeneration and retirement remain next | [Storage contract](metal-campaign-storage.md) |
| Maps/campaign interaction | Willow retains its separate owner and qualification; no new map-generation or density-fitting policy enters here | [GUI contract](gui.md), [architecture](architecture.md) |

The two subsystem handoffs preserve their evidence-time branch statements and
commands. They are scoped implementation/scientific records, not competing root
integration queues. Update the relevant handoff and milestone together. Use
existing patches/readers before new diagnostics; no repeated weight, derivative
or native sweep is justified merely by this merge.

The A01 follow-up now binds a fresh fixed-coordinate FT_Hg interpretation to
the actual retained endpoint, after proving the old capture has stale XYZ/B.
Phenix 2.2.1-6174 completes in 2.25 s with unchanged inputs; 260 cold checks
retain all supplied contacts. The six-case intake diagnostic preserves canonical
movement restrictions and refuses stale parents, unwanted neighbors and B/Q
changes. Product sources stay exact; whole-parent authority and supported
modified/metal manager retention remain open. The metal handoff owns the numbers,
commands and parallel A04 next step; no new scientific acceptance follows.

## Compatibility and remaining limits

The package includes Cedar replay resources and Alder viewer resources. The
testing contract keeps focused development profiles and requires a full gate for
integration/cross-cutting changes; documentation-only work needs document checks.
Both science-checkout and evidence-retention policies survive unchanged.

Current artifact readers/defaults and fixed native worker bytes are preserved.
No old run is rewritten or admitted, no checkpoint selected and no scientific
data uploaded. New capabilities retain their existing explicit policies and
schema boundaries; integration itself introduces no new artifact schema.
Refine Doctor's declared-site continuation remains a separately qualified gap.
Receiving Pine, a release merge, scientific acceptance and completion of A01–A08
are separate decisions. The matched A01 continuation, donor-span/current-state
objective reviews and explicit angular alternative are complete. The metal
handoff owns the next linked base/metal pose scope and the withheld numerical
profile. No repeated unchanged controls are queued. A04 has explicit parent
transport; scientific session/software identity
and the compact child lifecycle still precede pruning.
