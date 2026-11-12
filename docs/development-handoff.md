# NASolve development handoff — current state

Updated **2026-11-12**, C241. Active branch **cedar**, checkout NASolve-c96.
C234–C239 are committed/pushed as 9f05d60; C240–C241 build on that checkpoint.
Use current HEAD for the final commit identity.
The [queue](cif-doctor-completion-queue.md) owns work order;
[capability limits](cif-doctor.md#current-capability-boundary) remain in force.
Finish Q04/Q05 before Q06. Laboratory language first. No merge authorized.

## Current result

The existing prepared repair request now accepts exact completed owned plane
support. It freezes source/request/attempt identity and all evidence, then runs
linear and plane checks through the same native owner, source/native/derivative
selector and publisher. Ordinary ordered NARestraints inputs remain exact.
No residue-name switch, generator or retry protocol was introduced. Unsupported
completion can retain an already checked route; malformed evidence/unknown work
cannot. The complete outer request does not yet acquire plane support itself.
C240 adds a read-only proof for a launched stopped failed/timed-out generation,
sharing exact source/spec/worker/owner checks. Partial CIF/JSON remains preserved
and unqualified; successful support keeps its stronger checks. This proof alone
authorizes neither fallback nor retry. Actual Phenix timeout (-15) and cold moved
request pass, 22 files / 282,027 bytes unchanged. Earlier capability failures,
prelaunch errors and zero-exit unqualified builds remain outside this narrow proof.
C241 fixes an existing acquisition identity mismatch: its generation-child recipe
now retains the already supported optional multiple_planes flag. No in-place
resealing, new recipe option or relaxed chemical gate.

Actual Phenix 2.2.1-6174 / dispatcher 2.2.1 controls use C231's ordinary PDU/NAR
bundle and exact completed C215 support. Success selects the repaired bundle with
explicit C5 coverage and all five PHILs. A deliberately one-second plane-native
limit stops the worker and selects the independently checked original, honestly
retaining missing C5 coverage. Failure replay rebuilds the narrow candidate from
source/support without Phenix. C236 also fixes the older failure reader's mismatch
with C207's full-model plan, retaining compatibility with selected-only old plans.

Storage: C237 assembles combined proof temporarily, freezes it in publication and
removes that assembly; original/partial worker output remains. C238 references the
already frozen native inventories instead of embedding them in plane-job specs.
The maintained job still checks/compares the full inventories. The fresh successful
request falls from 195.9 MB to 134.4 MB, including a 4.5 MB final result; chosen
model, two CIFs and five PHILs are byte-identical. C239 refuses excessive aggregate
support before reading more components. All existing limits remain unchanged.

Success and timeout requests pass read-only relocation with old request/source/
support paths, SDK and process calls forbidden. They were moved, not copied;
471/310 files preserve bytes/mtimes. C238's subsequent compact success also passes,
471 files unchanged, temporary view removed (53.3 MB), peak read memory 569.3 MB.
This does not establish campaign-scale memory/storage safety. The repair controls
reuse earlier completed generation; C240 alone runs the short deliberate generation
timeout. No Coot or diffraction refinement. All native owners STOPPED; no background job.

## Validation and reviewer handoff

Behavior before: C226/C227 were separate plane proof/selection components;
prepared repair ran only its linear route. After: explicit owned plane support
uses that same request/owner and final selector, including stopped-native fallback.
Changed source: cif_prepared_repair_execution, cif_repair_attempt,
cif_repair_process, cif_prepared_repair_failure, cif_plane_candidate and
cif_captured_plane_attribution; C240–C241 also change cif_plane_generation,
cif_source_representation and cif_acquisition_attempt. The existing workflow
profile includes the new support tests. README/architecture current summaries, methods/overview, queue and ledger
are updated; historical milestone sections retain their original meaning.

Compatibility: optional plane_support in request/execution,
cif-prepared-owned-plane-support-v1, cif-prepared-plane-stage-v1, and optional
compact_inventory=True in plane-job controls. C240 derives a new read-only negative
proof from existing saved records; C241 corrects their recipe comparison without
changing stored schemas. Old absent fields/jobs remain
readable and keep their earlier behavior; old strict readers refuse the new mode.
No migration, old scientific output rewrite, chemical threshold or stacking-policy
change. Source support does not authorize replacing a whole generated CIF.

Focused validation: 320 affected support/execution/failure/request/process/budget/
plane/profile tests; 91 complete-request callers; 117 compact plane-attribution/
execution tests; 62 support/repair-chain cases, all pass. Sets overlap; do not sum
as unique suite coverage. Fail-before controls: missing support, canonical/library
bystanders, retained duplicate assembly, referenced inventory and early aggregate
bounds. Exact commands/results and source pins are in ledger entries
owned_prepared_plane_repair_2026_11_12 and compact_plane_inventory_2026_11_12.
C240: 108 generation/representation tests plus four negative/partial-output cases;
C241: 182 acquisition/generation cases and three exact recipe-choice cases pass.
Additional commands/results and native pins: owned_plane_generation_failure_2026_11_12.
C240's two missing-reader tests and C241's recipe-sealing test fail before fixes.
AST review of 18 changed Python modules finds no shadowed top-level definitions or
imported collectable test functions. This is not a repository-wide redundancy proof.
Changed-file syntax and Git whitespace checks pass.
No full suite this push. Last entirely green full: C220/583d30df, 9,178 tests +
276 subtests. C222's later full failures were fixed with focused checks; no full
revalidation claim. Generated science, logs, source-pin lists and ignored runners
remain outside Git. Locations are anchored in the ledger and capsule metadata.

## Next work — finish Q04/Q05

1. Obtain/freeze source plane support through the existing complete-request
   generation owner, using the current graph screen rather than residue names.
   Bind exact numbered children, shared deadlines and finite attempt allowances;
   retain the independently checked parent on a classified optional failure.
   C240 supplies narrow launched-negative generation evidence; expand any other
   fallback states explicitly, without treating arbitrary exceptions as permission.
   Unknown processes or malformed proof still block retry. Preserve earlier
   request meanings. Explicit prepared repair is integrated and native-tested.
2. Define later preparation-child publication without replacing an immutable
   earlier root or claiming a fresh MR construction descends from a refined model.
   C223–C225 already supply initial checkpoint publication, checked ordinary
   PostMR and explicit frozen campaign entry; do not rebuild those paths.
3. Design explicit interruption-safe retirement of redundant successful working
   files only after every owner stops and a sealed result verifies. Keep exact
   recoverable inputs, tool/policy identities and necessary receipts. No incidental
   cleanup of old/failed science. Measure whole-request disk, temporary disk and
   memory separately; 100 datasets do not mean 100 concurrent readers.

Prior-work audit: C160/C163/C164 own repair/recovery; C207/b45bd645 scopes plans to
all modeled types; C213/C232 bind exact owned generation and actual parent grants;
C226 owns whole-plane mechanics; C227 composes proofs through the existing selector.
C193 supplies failure diagnostics, not recovery authority; C240 reuses the stronger
source/owner readers for negative execution evidence.
C228–C233 supply compact publication, shared parent reads and bounded inventories.
Reuse these rather than introducing parallel machinery.

Q06 real complete-restraint refinement and Q07 combined/held-out chemistry remain
queued after Q04/Q05. NAR's reviewed base-role stacking atoms remain sufficient;
Cedar's substituent chemical planes do not automatically enlarge stacking planes.

## Preserve local evidence

Protected NASolve-cedar remains at e7451eed with local phaser.py/unpublished data.
Everyday NASolve/pine retains its pre-existing untracked science, patches and venv.
Work only in NASolve-c96/cedar. No new branch, cleanup or merge is authorized here.
