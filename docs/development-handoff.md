# NASolve development handoff — current state

Updated **2026-11-13**, C268 full-model energy/name capture validated; C266 base `6dab315`. Active **cedar**, NASolve-c96.
Simon authorized work through **00:00 Europe/London, 14 November**, no full suite or merge.
Finish Q04/Q05 before Q06. The [queue](cif-doctor-completion-queue.md) owns ordering.

## Latest result — original chemistry survives native input preparation

C263 adds the explicit `cif-source-reader-preparation-v1` recipe. It composes
C30 graph export, C37 reader preservation and C262 complete bond-row ordering
inside the existing generation owner. Original source/authority remain the cache
and qualification basis; separate derived files and actual reader dialect are
bound and rederived on read. Coordinate origin remains explicit. Ordinary intake,
resume, acquisition and plane-support reads retain that choice. Old recipes and
CLI defaults are unchanged; new prepared-input requests need a current reader.

Fresh original-source 1AP and 5IU acquisitions pass isolated native qualification
and relocated read, with original/cache/SDK reads and native launch forbidden.
Phenix 2.2.1-6174, 45.03 seconds whole control, 82.6 MB Python peak. Requests retain
5,056,121 B/82 files and 3,699,998 B/82 files respectively. Original source bytes/
timestamps unchanged. Local root: `263_Cedar_original-source-acquisition-vk0kfckx`;
all jobs stopped, pinned source unchanged. Ignored c263_* runners in everyday checkout.

Keep the scientific distinction: raw 1AP generation remains REJECTED for partial
in-memory purine aromatic representation and legacy unsigned phosphate `both`
omission. The written candidate passes existing original-source reassessment and
independent native qualification. Do not relabel that raw verdict or weaken gates.
C262 fixed the observed unwanted extra P=O by reordering entire source bond rows;
no bonds, charge/H, stereo or coordinates are changed. Native code is untouched.

Focused validation: 333 existing/new checks passed in the first group; four
new tamper-fixture setup errors were corrected. Final targeted group **57 passed**;
ordinary intake/resume/complete owner **159 passed**. Relocated temporary checkout
and request, old temporary paths absent: **1 passed**. Exact commands, hashes and
limits: ledger `original_source_owned_acquisition_2026_11_13`. No full suite.

## C266 — preserve a protected background phosphate

C265 correctly refuses charged 1AP OP3 under the neutral-hydroxyl linking rule;
Q13 records general source-state/linked-native follow-up. No guard is weakened.
C266 uses a declared A:5IU software fixture on the same real observations, keeping
protected D:1 phosphate and free ends A:1/B:1/C:8. Phaser/Coot, isolated acquisition
and generated 5IU plane support pass; combined source-native qualification rejects
the background terminal-phosphate declaration; the existing unsupported native
formal-charge readback remains separately recorded without contradictions. D:1 lies outside replaced
sites, so its frozen ordinary permission never reached the native check.
Root `266_Cedar_selected-autosol-11iw4weh`, 74.69s, all jobs stopped/code unchanged.
No ReadySet, AutoSol or publication. It does not describe donor chemistry.

The fix adds explicit native context v3, derived from audited frozen intent for
unchanged background termini and rechecked on complete-request read. Exact site,
component/outgoing link, unchanged native definition and existing phosphate graph,
coordinate/link/proxy checks are required. No new modifier or chemical edits.
Old v1/v2 unchanged; new context needs current reader and fresh work.
Focused tests: 155 passed + 4 added request/tamper/relocation checks. Affected
owner/bundle/ordinary tests: **201 passed in 304.54s**. Relocated temporary checkout
and request: **1 passed in 2.60s**, both old temporary paths absent. No full suite. C267 (`267_Cedar_selected-autosol-k17oznfd`) is stopped, code unchanged: the
background permission now reaches the check, but canonical Phenix p5*END maps model
OP3 to dictionary O3T. Native source/baseline definitions are identical; the existing
literal phosphate check refuses. C112 already captures actual name bindings; reuse
that helper rather than inventing aliases. Its historical capture excludes energy
augmentation, so qualify an explicit full-model energy+mapping composition before
connecting it. Preserve v1/v2/v3 context meanings and old worker bytes. No native
jobs are currently running. No ReadySet/AutoSol result is claimed.


## Next — finish Q04/Q05 acceptance

1. C267 retries the real-observation chosen-model AutoSol control in a
   fresh owned run. Use ignored c267 worker/driver with the explicit A:5IU control,
   C263 source-input policy and C118 permission. C259's software fixture declares free ends
   A:1/B:1/C:8 while preserving D:1 phosphate; it does not infer DiU chemistry.
2. Verify original-Phaser phasing versus chosen-model site comparison, exact phase
   labels, later-selection preservation and relocated inspection. No synthetic
   reflection substitute. Interrupted AutoSol publication remains preserved but
   not automatically adopted; keep this separate remaining recovery boundary.
3. Reconcile opt-in Q04/Q05 scope and default-route rollout; then Q06 real
   complete-restraint refinement and Q07 combined/held-out chemical controls.
   Q08–Q14 retain chemistry learning; Q15 report/PDF; Q16 final AutoPhase naming,
   full regression and reviewed integration. No merge authorized.

## Completed foundations — reuse

C260 connects existing C258 retirement after new checked publication and before
campaign capture. Optional cleanup failure returns science only after exact reread.
Partial cleanup can finish without breaking new campaign artifact references.
Inspection and historical publication never clean files. Old unarchived campaigns
still referencing working files require separate migration. Failed/uncertain work
and shared acquisitions remain unpacked. Actual C244 copy: 181.6 MB → 33.7 MB,
same model/five PHILs/two CIFs/51 public paths; all original science unchanged.
See `ordinary_campaign_retention_2026_11_13`; do not rebuild storage machinery.
Last full suite **C220/583d30df: 9,178 tests + 276 subtests**.

Linden works independently on Willow/Pine. Existing Cedar parallelity audit and
plane-order correction were pointed out to avoid duplicated Cartesian diagnosis;
new symmetry pullback/closure work remains their separate diagnostic scope.
Protected NASolve-cedar and everyday NASolve/pine data/patches/environments remain
untouched. Continue on NASolve-c96/cedar, no new branch.


## C268 — reuse C112 name bindings without changing mechanics

The explicit full-model/policy/energy/name composition passes 129 focused checks.
Actual Phenix 2.2.1-6174 root `268_Cedar_energy-mapping-w0pqcco7`: 853 atoms,
nine observed aliases, D:1 OP3→O3T. Native energies/gradients/geometry/definitions
exactly match the prior C267 baseline. Relocated no-launch read passes. Native
completed; the original driver then hit a checks-dict/list assertion mistake.
Its failure and immutable worker remain; c268_readback.py separately verifies the
known-stopped output, no repeated native call. Read `readback-summary.json` plus
`driver-result.json`, not the driver's return code alone. All source pins match.
Next: a new explicit terminal context may use these captured names while keeping
v3 literal and preserving all original definition/state checks. No native job active.
