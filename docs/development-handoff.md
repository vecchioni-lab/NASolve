# NASolve development handoff — integrated development base

Updated **20 November 2026**. Active integration target: **Alder**. The everyday
Pine and the separate Cedar/Willow branches are not changed by this integration. This base
combines the existing metal feature with the qualified shared chemistry, native
observation and storage owners; it introduces no new scientific policy.

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
