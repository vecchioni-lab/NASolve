# Metal campaign storage and recovery plan

Status: **inventory, compact projection, exact inputs and explicit parent transport implemented; scientific retention/regeneration lifecycle pending**; 20 November 2026.
The [post-merge development roadmap](metal-development-roadmap.md) places this
work at **A04**, after single-dataset ligand/open-refinement qualification and
before large f″ campaigns. It is a feature milestone after merge, not a
prerequisite for merging the current experimental implementation.
This document does not enable cleanup or change an existing immutable run.

## Implemented first step: explicit frozen-trial inventory

`nasolve metal inspect-fdp-storage RUN --trial Metal/fdp_001 --trial Metal/fdp_002 --json`
checks the complete manifest envelope and hashes each declared regular file.
It reports logical bytes, unique content bytes, repeated content bytes, named
producer roles and explicit parent references. Every trial must be named; it
neither discovers inputs nor traverses parent trees. The default total sample
budget is 1 GiB, with at most 256 trials, 256 files per trial and a 1 MiB manifest.
`--max-bytes` sets an explicit sample budget. No Phenix/Coot process runs.

This is **payload integrity, not scientific replay**. Use `verify-fdp` for the
full scientific audit. Identical content is not necessarily safe to retire:
all existing manifest promises still apply. Unknown declared native outputs stay
visible as `other_declared_payload`; filename extensions never authorize cleanup.
Counts are logical bytes, not measured physical allocation on compressed,
cloned or hard-linked filesystems. Failed/incomplete trials are refused rather
than silently omitted. Output goes to a new explicit `--output` file outside the
immutable `Metal` tree; input files and manifests remain untouched.

The additive report schema is `metal-fdp-storage-inventory`, version 1. Its
run-anchored file references/checksums and report digest survive relocation.
Parent references are recorded **but their payload is neither counted nor
verified**. The report explicitly denies scientific replay and retirement
permission. This does not replace a run/retention manifest or change its schema.

For a scenario, supply `--forecast FORECAST.json` with all seven integers:

```json
{
  "datasets": 200,
  "trials_per_dataset": 100,
  "protected_bytes_per_dataset": 104857600,
  "concurrent_jobs": 4,
  "scratch_bytes_per_job": 67108864,
  "compaction_overlap_bytes": 536870912,
  "reserve_bytes": 5368709120
}
```

These example allowances are assumptions, **not measured upstream or scratch
usage**. The forecast multiplies the largest sampled current-layout trial by the
requested point count, then adds protected storage, concurrent scratch,
compaction overlap and reserve. It deliberately makes no compact-layout savings
claim, guaranteed upper bound, scheduling decision or actual disk reservation.
A larger reflection set, extra maps, failures or protected nodes can exceed the
scenario; provide allowances for them and calibrate representative samples.
Shared/unique content within the measured sample is exact; forecast reuse across
different datasets is never assumed. Measuring peak native scratch and campaign
budget enforcement remain later executor work.

A read-only three-trial FT_Hg sample on 18 November contains **2,478,875 bytes**,
including **965,109 bytes** of repeated content. Its largest trial is 848,299
bytes: 20,000 such trials alone would consume **16,965,980,000 bytes**, before all
other allowances. This different sample does not replace the larger earlier
examples below. No files were retired and no accepted scientific solution follows.

## Implemented second step: lossless result projection

`nasolve metal project-fdp-records RUN --trial Metal/fdp_001 --trial Metal/fdp_002 --output projection.json`
creates a small view outside the immutable `Metal` tree. It first inventories
the explicit complete trials, then uses the existing full FDP derivation/freeze
replay owner. A second replay and final inventory reject observed source changes
while assembling the view. No native program is executed. The command has no
implicit trial discovery or current-checkpoint selection, and does not change
existing artifacts.

The additive `metal-fdp-compact-projection` v1 report stores shared comparison
bases and executable-input descriptors once, while retaining every attempt,
complete unrounded result summary, occupancy vector and anchored source manifest.
Repeated identical inputs may share a descriptor, but their attempts/results are
never collapsed. Different geometries/experiments keep distinct bases. Input
fingerprints include complete executable input hashes, plan/settings, all model
state through the input model bytes, and the existing recorded native identity.
They describe saved inputs, **not complete environment identity or cache eligibility**.
Existing scan reuse and scientific comparison policies are unchanged.

`nasolve metal verify-fdp-records RUN --projection projection.json` reconstructs
the view from the original complete trial/parent evidence. A recomputed digest
cannot authorize edited numbers, accepted status, cleanup, missing evidence or
expanded scope. Source manifests go through the numbered-trial and 1 MiB manifest
preflight before source reads. Run/dataset/repository references use existing
resolvers; absolute operational references are refused. The file uses canonical
UTF-8 JSON plus a final newline, with exact section byte counts and a whole-report
digest. Display rounding is not stored. The projection is not a new run manifest,
standalone scientific proof, input store, native regeneration recipe or pruning
permission. Its full original result objects include optional diagnostics and
environmental-B provenance; derived count/comparison reports remain separate.

There are at most 128 explicit trials. `--max-bytes` defaults to a 1 GiB **trial
payload preflight** limit and `--max-projection-bytes` to a 16 MiB serialized view
limit. These do not bound the legacy full reader's parent traversal or native
JSON expansion, and do not reserve disk space. Caller limits can restrict
verification; the saved file cannot enlarge them. This is an offline bounded
sample/output view, not the future resource-bounded campaign executor.

Measured old diagnostic samples, fully replayed without new refinement:

| Sample | Original trial payload | Projection | Shared bases | Complete point-record section |
| --- | ---: | ---: | ---: | ---: |
| Three FT_Hg trials | 2,478,875 B | 25,884 B | 1 (14,490 B) | 6,598 B for three attempts |
| Ag4 tetrahedral trial | 1,044,486 B | 54,643 B | 1 (32,329 B) | 20,094 B for one four-site attempt |

The remaining bytes are input descriptors and envelope/encoding overhead.
Projection/section sizes use canonical JSON; source sizes are logical file bytes.
These measurements are not a claim of safe savings:
the original inputs/evidence are still required, upstream parents are excluded
from the source column, and nothing was retired. The four-site record exceeds
the earlier 1–8 KiB design target because complete environmental-B details remain
inline. Future lossless shared-parent factoring must be measured and qualified;
do not forecast the smaller target as achieved. No scientific endpoint is accepted.

Qualification at `e002e2037048a4f5778898c7682174e96da5a01b` includes 6,432 tests and
276 subtests, exact real-data readback through a relocated source-free installed
package (192 unchanged resources), and separate fresh-process source/data
relocation. The [handoff](metal-development-handoff.md) owns commands, limits and receipts.

This closes the **read-only projection substep** of A04. Complete retained-parent
publication, native regeneration, campaign budgets and retirement retain their
own gates. The bounded input-transport substep below now reuses the integrated
storage owner; it does not replace those remaining qualifications.

## Implemented third step: exact input archive transport

The explicit Python API `nasolve.metal.input_archive.pack_fdp_inputs(run, trials,
output)` fully replays each named original trial using the existing compact-view
owner. It then copies the exact recorded executable inputs and complete plans,
retains the full compact projection (including every attempt and result), and
replays the source again before publication. Equal input identities share one
request directory; repeated attempts remain separate records. No input is found
by basename or inferred from nearby folders. Output must be fresh and outside
the source run, and existing files are never replaced.

Packing delegates to Cedar's unchanged checksum-indexed archive owner. The
returned `metal-fdp-input-archive` v1 receipt binds both archive SHA-256 and
projection identity. `expanded_fdp_inputs(archive, archive_sha256,
projection_id=...)` checks those expected identities, projection consistency and
the complete recorded input inventory before yielding a temporary read view.
The view contains `projection.json` and `requests/<input_id>/<original_name>`;
its paths expire on context exit. Captured plans remain data. No execution,
checkpoint selection or original-source lookup occurs during cold expansion.

This is **exact input transport**, not standalone scientific validation. The
original trial and parent evidence are required during packing. The archive
does not retain their complete transitive proof, full software/environment
identity or all native outputs. It therefore grants no reuse, execution or
retirement authority. A successful cold expansion after original test data are
removed establishes byte recovery only; actual Phenix regeneration and safe
scientific-output retirement remain unqualified. Packing remains a Python API; the recorded-result CLI below is read-only.

The existing shared limits remain: at most 1,024 logical files, 32 MiB per file
and 128 MiB total logical input contents, including the compact projection.
Existing compressed/object/temporary-view limits also apply. An explicit
`max_input_bytes` can lower the logical allowance; it cannot enlarge it, and
cold expansion checks it before allocating temporary files. It is not a smaller
decoder RAM allowance: decompression happens under the shared decoder's separate
bounds before that temporary-filesystem check. Split a larger selection explicitly
rather than raising shared limits. `max_trial_bytes` defaults to the existing
1 GiB trial-payload preflight, and compact metadata
retains its 16 MiB cap. Upstream scientific replay still traverses original
parents and native JSON; these are not total I/O, memory, peak disk or campaign
reservation guarantees. No original scientific run is modified by this adapter.

### Normal CLI inspection of one recorded attempt

`nasolve metal inspect-recorded-fdp` exposes the same maintained recorded-result
reader through the ordinary CLI. Supply `--archive`, `--archive-sha256`,
`--projection-id`, `--trial-id` and `--expected-parent` (a JSON file holding the
exact independently retained `geometry_id`/`xyz_trial_id` and run-anchored
`manifest` object). These identifiers come from the original publication and
selected parent; extracting replacement identities from an untrusted archive
would not establish independent trust. Original parent model files are not opened.

The default display contains site/element, **Q (occ)**, B, fitted f″, expected f″,
Rwork/Rfree and wavelength. `--json` prints the complete API result without
rounding. Output is stdout only; there is no `--output`, implicit run, file search,
native discovery or permanent result-directory creation. Temporary archive views
remain owned and cleaned by the existing bounded transport owner. Parent JSON
is limited to 16 KiB using the existing strict duplicate-key-rejecting reader.
`--max-input-bytes` may tighten the existing archive allowance.

This is historical inspection, not `verify-fdp` or a new scientific audit. Current
parent/native environment verification, reuse, cleanup, automatic selection and
scientific acceptance remain false. A different trial with the same inputs is
still a separate attempt. Existing project/verify/storage commands are unchanged.

The command passed **53 focused tests** (10 new CLI cases plus existing result
inspection and compact-record controls). The normal entrypoint was then tested
from a relocated installed package against the actual saved FT_Hg and Ag₄
archives: exact full results, wrong-parent refusals and preserved partial-archive
refusal, with original source/science reads blocked and no Phenix call. The
**723 installed checks** include package byte checks, not 723 scientific trials.
See local `recorded-cli-20261120-01/{validation.json,installed/result.json}` under
the Alder artifact anchor; no generated science is committed.

### Completed-batch publication and selection receipt

The normal frozen-trial producer already emits an exact parent, trial identity
and result checksum after its freeze audit. The additive
`metal.publication.publish_fdp_inputs(run, trials, archive, output)` now provides
the next explicit handoff: pack a named completed batch through the existing
full-source owner, reopen that exact checksum-pinned archive, and emit a compact
trial/result index with shared parent identities. It adds no source-parent replay
while building the index and does not pack automatically after every trial.

`metal publish-fdp-inputs RUN --trial Metal/fdp_001 --trial Metal/fdp_002
--archive ARCHIVE --output RECEIPT` exposes this producer. Both output paths must
be distinct, fresh and outside the immutable source run. Existing limits remain
1–128 explicit attempts, bounded archive contents and optional tighter
`--max-trial-bytes`/`--max-input-bytes` allowances. There is no implicit discovery.

The new **`metal-fdp-review-publication` v1** receipt contains archive/projection
identities, unique parent records and separate trial/result-record identities.
The existing durable campaign writer supplies `record_sha256`: retain this
identity independently at publication. Archive fsync uses the shared storage
primitive, and the receipt is published last with create-only atomic linking.
The CIF complete-attempt schema/retirement machinery is not applied to metal
trials. Failed source audits and interrupted archive/final-receipt publication
issue no successful selection receipt; incomplete or orphan archives remain
for explicit recovery, and existing outputs are never replaced.

Read with `metal inspect-recorded-fdp --archive ARCHIVE --publication RECEIPT
--publication-id ID --trial-id TRIAL --json`. The publication ID is the producer's
independently retained `record_sha256`, not a newly trusted value extracted from
an unknown receipt. The existing individual archive/projection/parent flags
remain supported and cannot be mixed with receipt selection. Receipt metadata
is capped at 1 MiB. The unchanged recorded-result reader validates the selected
archive/parent/result binding; it does not open the source run or re-audit native
science. No execution, reuse, scientific acceptance or retirement follows.

For a complete comparison, replace `--trial-id TRIAL` with `--all-trials`.
This requires a pinned publication receipt; the legacy individual-pin form stays
single-trial. `inspect_published_fdp_batch` opens one bounded temporary archive
view, applies the unchanged recorded-result checks to each indexed attempt, and
returns the ordered list only after every selection matches. Repeated requests
remain distinct attempts. The JSON list contains the same full inspection
objects as separate calls; text output groups sites under each attempt. No
cached verification, persistent view or new on-disk schema is introduced.
A failed final selection yields no partial result/table, and the archive context
closes before return. Archive expansion occurs once; per-result metadata checks
are still applied for every selection.

**Batch-view qualification:** 51 focused tests pass in 39.05 s, including the
regression that failed before the API existed. A relocated fresh installation
keeps all 349 package members exact and reads the existing three-trial FT_Hg
archive with original access denied. Its 370 checks include package integrity:
one expansion for the successful batch, one for a changed final-record refusal,
and zero for a wrong independent publication pin. Results and parent identities
match the prior independent readback exactly, archive bytes remain unchanged,
and all temporary views/scratch are removed. No native run or full suite occurs.
Exact commands and receipts are in `batch-inspection-20261120-01/{validation.json,
installed-review.json}` under the private Alder artifact anchor.

Final-source evidence: **16 focused tests pass in 10.94 s**, including normal
two-trial production/publication/readback and interrupted archive/receipt checks.
A relocated installed normal-entrypoint control produces two trials with the
existing explicitly synthetic native-result fixture, then reads exact results
after removing the synthetic source run. It retains two attempts and one shared
parent in a **1,538 B receipt** beside a **12,749 B archive**; those are synthetic
fixture sizes, not campaign estimates. Its 728 checks include 349 package members.
Existing packing makes eight source-parent replays for the two trials; index
construction adds zero, cold selection reads zero parents, and this legacy fixture
does not walk a whole checkpoint registry. No modern-parent speedup is claimed.
Local `fdp-publication-20261120-01/validation.json` and `installed/result.json`
record the exact sources/commands. No native fit or full suite ran. A04 remains
partial: protected-parent session execution, exact regeneration, scheduling and
safe retirement remain separate gates.

The subsequent real FT_Hg completed-batch proof reuses that installed wheel and
three existing attempts. Its 134,901 B archive exactly reproduces the independently
pinned earlier archive; the new selection receipt is 1,810 B. Forty-eight checks
recover all inputs, parent identity, full model/reflection arrays and unrounded
results with original reads denied. The original trial inventory (2,478,875 B)
and parent remain unchanged. These sizes exclude complete protected-parent
storage and do not authorize deletion. The historical B=25 Å² poor-fit results
remain diagnostic; no native run, scientific acceptance or schema change occurs.
See `real-publication-20261120-01/review.json` and the
[handoff](metal-development-handoff.md#completed-batch-provenance-handoff).

## Implemented fourth step: explicit parent-layout transport

`nasolve.metal.parent_archive.pack_parent_inputs(layout, output)` retains one
explicit, caller-prepared portable layout as checksum-indexed archive parts and
a `metal-parent-input-archive` v1 manifest. It preserves all declared paths and
bytes, deduplicates equal objects, and uses the existing archive serializer,
decoder and member grammar. It neither discovers scientific dependencies nor
checks their completeness. Unsafe paths are refused; the caller must explicitly
prepare any opaque attachments. No automatic renaming or basename lookup occurs.

`materialized_parent_inputs(directory, manifest_sha256, ...)` yields a temporary
parent root and a transport receipt. It copies out the verified transport view,
closes that view, then allows ordinary scientific readers to open their own
archive scopes. Entry/exit hashes and read-only modes protect against observed
changes; they are not hostile-process isolation. The caller must replay the
appropriate scientific owner. A valid transport receipt never substitutes for
that replay, a trusted software identity or frozen-state validation.

The unchanged global bounds are 1,024 files, 32 MiB per file and 128 MiB logical
contents; each compressed part remains capped at 32 MiB. At most eight explicitly
named parts and 128 MiB total compressed parts are allowed. Metadata is at most
1 MiB. Packing rejects unsupported single-object or archive sizes rather than
relaxing a shared bound. The output must be fresh and separate. Parts are synced
before the manifest is written last. An interrupted partial publication remains
unadoptable and is not silently overwritten; crash recovery and automatic cleanup
of such partial directories are not provided by this API.

The materialization allowance includes retained parts/manifest, transport-copy
overlap and one ordinary reader's full shared temporary allowance. Defaults are
256 MiB per invocation plus 256 MiB free-space reserve. A caller can restrict or
explicitly increase its task allowance without enlarging any archive bounds.
If caller scratch and system temporary storage use different filesystems, each
must have the conservative allowance available. This is a preflight check, not
an atomic space reservation or an overall RAM bound. Concurrent campaign tasks
still need an aggregate reservation owner. Nested parent snapshots in the same
context are refused. Temporary paths expire on normal and exceptional exit.

The adapter changes no existing run/registry/trial schema, checkpoint selection,
native worker, CLI or GUI. Its new transport schema is additive; no migration is
required. It grants no execution, automatic reuse, scientific acceptance or
retirement authority. Complete parent selection, trusted software identity,
compact child audit/regeneration and campaign retirement remain separate gates.

Qualification: **96 focused tests pass in 24.36 s**, including the new lifecycle
regression, source-removed relocation, changed/missing/aliased inputs, budgets,
copy fallback and interrupted publication, plus the directly reused archive and
existing metal input-transport tests. A source-free relocated wheel has **346
exact package files**. The installed adapter recovers the same complete modern
parent through ordinary readers with original science/source reads denied:
**876 cold checks**, one full registry read (**99.78 s**) and subsequent
checkpoint resolutions (**0.031 s**). Four parts occupy **35,687,332 B**;
the manifest is **104,364 B**, and the conservative disk bound is **246,715,191 B**.
All 392 original files remain unchanged; temporary staging/build/install paths
are removed. The original science remains present but blocked during the probe.
No Phenix/Coot call or new scientific acceptance occurs, and the owned process
is verified stopped. No full suite was run.

Exact commands and hashes are under the Alder artifact anchor
`parent-adapter-20261120-01/`: `focused-tests.json`, `installed/result.json`,
`packing.json`, `cold-execution.json` and `snapshot-recovery/cold-review.json`.
The focused command uses `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, Python
3.12.14 and the four named modules in its receipt. An initial wrapper keyword
error was refused before any process spawned and is preserved separately.
Generated bundles, models and reports remain local and excluded from Git.

## Bounded protected-parent and regeneration rehearsal

A 19 November rehearsal extends the earlier input-only archive to the existing
metal-parent readers. Two old diagnostic cases cover a deterministic recipe
geometry and a native XYZ endpoint. Their exact hypotheses, root inputs and
native geometry evidence are retained once. Adding unchanged legacy PostMR
reports permits the ordinary `read_registry`, `resolve_checkpoint` and
`inherited_paths` readers to recover both roots too.

The final archive contains **55 logical files / 4,730,256 bytes** in
**782,402 bytes**. It reuses the unchanged shared archive owner and its bounds.
Cold replay uses the previously qualified relocated installation, after owned
staging removal, with file access to the original science/source trees denied.
Both ordinary roots and metal parents replay exactly. Five missing/changed
metal-dependency checks and two changed root-reflection checks refuse. No source
run is altered or retired. These are legacy roots, not a qualification of modern
checked-preparation ancestry; their original host paths remain provenance and
are resolved through the existing preserved dataset/run layout.

Two subsequent native reproductions use exact recovered executable inputs and
the explicitly reviewed original worker from trusted Git, whose hash matches
the saved trial. The five recorded native source/kernel hashes also match.
Phenix **2.2.1-6174** completes the Hg request in **7.83 s** and the four-Ag request
in **17.15 s**. Both complete unrounded result records match exactly, and frozen
XYZ/Q/ADPs are unchanged. The prior poor-fit and negative-f″ results are reproduced,
not relabelled as good solutions. Each reproduction is a new local research
attempt, with owned/stopped process identity and its original attempt link.

This closes a **two-case recovery feasibility check**, not A04. There is no new
production archive schema, executor, automatic reuse or pruning permission.
Complete software/environment identity and modern checked-root ancestry remain
unqualified. The ordinary parent stays protected as a root, rather than being
silently omitted or copied per point. Keep the recovered-source qualification
nodes; qualify the future lean incremental profile separately. The original
input-archive adapter and historical readers are unchanged.

Exact local receipts under the Alder artifact anchor:
`parent-retention-20261119-02/` (metal-parent replay),
`parent-retention-20261119-03/` (legacy root plus parent replay), and
`fdp-regeneration-20261119-01/` (two native reproductions). The preserved first
staging attempt was refused for an unresolved temporary-directory alias; it
published no archive. No unchanged test suite was repeated for these uses of
existing owners.

## Modern checked-parent dependency boundary

Cedar C414 traces the actual C412 checked-preparation lineage through
`read_registry`, `resolve_checkpoint(refine-003)` and `inherited_paths`.
The returned model, observations and eight restraint/protection inputs are only
ten files. The registry read also opens **290 distinct dataset files totalling
51,430,704 logical bytes**, validating preparation and all three refinement rounds.
Temporary verification leaves zero files. This is an observed dependency lower
bound, not a complete archive manifest: stat/directory/system accesses are not
exhaustively traced, and no metal verifier or root-free relocation was exercised.

That single instrumented registry read takes **88.48 s**, with 1,774 temporary
write-open events and 81,328 temporary read-open events. Open counts are not
bytes transferred or campaign performance estimates. This is parent-intake cost:
the current frozen metal verifier already uses its saved context/source bundle
and does **not** repeat that registry walk per point. The future retained-parent
executor should preserve this boundary, retaining complete parent evidence once
instead of copying or reopening it for every short frozen-f″ point. No measured
per-point speedup or need for a separate validation cache follows.

The next bounded executor design should verify a protected parent once into an
owned immutable view, pin its complete evidence/software identities, and validate
each exact trial request and freeze result against that view. The view has a
bounded lifetime and resource allowance; changed inputs, identity or software
invalidate reuse. A mutable original path or cached “passed” boolean is not a
substitute. Existing readers remain authoritative until this session boundary,
its change/refusal behavior and recovery are qualified. No validation cache or
relaxed reader is implemented by this plan.

Census: `cedar/c414-checked-root-dependencies/classified-census.json` under
`branch-artifacts`, SHA-256
`4391f0d2a20f5f24b004e59f235156cd6f167fc40dfca21086165a2f412627de`.
C401's protected parent and C403's nonstandalone child delta already exist; reuse
their owners and evidence. This census creates no archive and authorizes no pruning.

## Modern-parent recovery proof

The 20 November diagnostic proof recovers C412's complete isolated modern root
through the installed ordinary readers: original PostMR plus three refinement
checkpoints, unchanged selection, exact models/observations/restraints and
ancestry. It retains all **392 original files / 76,570,165 B**, rather than treating
the C414 census as exhaustive. Seven colon-named Coot backups are retained as
exact opaque attachments with an explicit original-name/hash map. Their original
bytes are preserved; they are neither decompressed nor inferred as dependencies.
Scientific operational paths remain unchanged.

The private layout includes its mapping: **393 files / 76,705,767 logical B**,
**247 unique objects / 62,410,176 B**, and **35,686,175 compressed B**. It uses
bounded parts decoded by the unchanged shared archive owner. Each part respects
the original 32 MiB compressed cap and the complete index respects the shared
file/logical/unique-object bounds. This is a diagnostic adapter, not a new public
schema or a reason to enlarge shared caps.

Three useful refusals are preserved: unsafe backup names, the whole archive
exceeding 32 MiB, and ordinary checked intake refusing an already-active outer
working view. The successful lifecycle materializes one protected snapshot,
closes the transport scope, and only then calls the ordinary readers, which own
their separate archive scopes. Read-only modes and full entry/exit hashes detect
observed changes; they are not isolation against same-user chmod or privileged
access. A conservative whole-task disk bound of **246,609,670 B** includes stored
parts, copy overlap and the reader's full temporary allowance, below the declared
256 MiB task budget. This is an explicit calculated bound, not measured peak
physical allocation, RAM usage or a campaign reservation.

Cold recovery passes **876 checks**, with one full registry read (**105.35 s**)
and four subsequent checkpoint resolutions (**0.027 s**). Original science and
source reads are denied; the original files remain physically present and
unchanged. The installed package's 345 files remain pinned. No Phenix/Coot call,
checkpoint selection or scientific acceptance occurs. The owned process stops
and both transport and protected temporary views are removed. Sixteen small
synthetic checks cover changed/missing/escaping parts, complete-index changes,
changed/extra/symlink snapshot inputs and cleanup. They qualify prototype
entry/exit behavior, not per-trial invalidation or crash recovery.

Receipts: `modern-parent-20261120-04/` under the Alder artifact anchor, including
`packing.json`, `snapshot-execution.json`, `snapshot-recovery/cold-review.json`
and `boundary-checks.json`; preceding attempts 01–03 and the first nested-view
failure remain retained. Exact commands are in the execution receipts. Cold read:
Python 3.12.14 `-B runners/A207_cold_snapshot.py`, with the pinned installed package;
boundary checks: `-B runners/A208_parent_boundary_checks.py`. No full suite or
unchanged native refinement was rerun. Generated bundles/reports stay local.

**Next:** the additive parent-layout transport now implements the bounded
lifetime separation above. Qualify trusted software identity and the lean
frozen-child audit/regeneration contract, then add explicit
campaign reservations and crash-safe publication/retirement. Preserve important
geometry parents throughout. No original run is yet eligible for deletion, and
the diagnostic recovery alone does not provide a reusable metal-trial session.

## Software identity: measured boundary and next contract

The current frozen-trial/scan owner already binds the maintained worker, native
version and five source/kernel hashes. Cedar's existing `_native_runtime` adds a
selected 21-module/live-binding profile for its ordinary route, while
`configure_dictionary_engine` pins declared dispatchers/API/prior sources. Reuse
these owners; none is a general inventory of every dependency a frozen fit loads.

A bounded Phenix **2.2.1-6174** import-only probe hashes **1,471 readable files /
357,214,624 B** into a **464,146 B** record in **6.37 s**. One exact historical
Hg request then loads **22 additional modules** and opens **69 external runtime
files**, including chemistry/symmetry resources and Python bytecode caches.
Its observed footprint covers **1,551 readable files / 403,961,691 B** in a
**494,893 B** record. The full old result reproduces exactly, with XYZ/Q/B/f′
frozen; it remains a poor-fit diagnostic, not a newly accepted metal solution.
Q=0.60 and B=25 Å² belong to this historical reproducibility fixture, not today's
open-XYZ/B endpoint or environmental-B recommendation. Its f″=29 e and
Rwork/Rfree≈0.3971/0.4237 are preserved rather than relabelled as valid chemistry.
The measured fit call is **6.24 s**; import/fit/census together take **28.67 s**.
Those are distinct measured stages, not a general per-point performance claim.

Both probes identify **390 loaded macOS image paths without readable backing
files**. The snapshot is therefore explicitly not complete environment identity.
Import-only capture also misses lazy/data-dependent resources. `-B` prevents
bytecode writes but does not itself establish which source/bytecode was read;
actual resource provenance matters. These observations neither diagnose changed
software in the existing runs nor invalidate their retained results.

**Design consequence:** store one bounded software/resource profile per declared
identity, referenced by compact trial rows; never duplicate hundreds of MB of
binaries or a half-MB fingerprint at every point. Separate declared supported
runtime pins, observed runtime resources and unqualified environment components.
Changed/unavailable software must make exact reuse/reproduction unavailable or
produce a separately identified new attempt, without erasing historical stats.
Hashes are provenance/checks, not retained executables or execution authority.
A complete execution/retirement contract still needs explicit scope and negative
controls; do not replace that work with an unrestricted environment crawl.

Local receipts: `software-footprint-20261120-01/` (import-only dry probe) and
`software-footprint-20261120-02/` (one complete native frozen-Hg execution), each
with request, exact command/process, footprint and review. Both owned processes
are stopped; input bytes and original numerical results are unchanged. No shared
runtime/default, native worker or artifact schema was changed for this private
measurement; no unchanged full/focused suite was repeated.

### Recorded execution and parent cross-binding

A separate read-only diagnostic now composes the existing parent/input readers
with one saved completed historical Hg execution. The externally pinned bundle
contains the unchanged shared parent/input archives, original trial and Free-R
audit, trusted historical worker bytes, execution receipt, actual-fit software
profile and full numerical/native result. Captured programs and commands remain
data; none is executed. It contains **14 files / 2,308,435 logical B**, compressed
to **1,265,221 B**. This deliberately includes the existing two-parent archive
unchanged; only the Hg execution is cross-bound here. Production should share
parents and profiles, not copy this diagnostic bundle into each trial.

The cold reader uses the previously qualified relocated installed package, with
its build source and original installation absent. Original science, source and
Phenix reads are denied. After moving the new bundle, the reader closes each
archive transport scope before opening the next. Existing owners recover the
legacy PostMR checkpoint and exact geometry parent, reproduce all nine executable
input files from that parent, and re-audit the frozen XYZ/Q/B/f′ state and complete
result. The historical Hg result remains f″=29 e, Q=0.60, B=25 Å² and
Rwork/Rfree=0.39707/0.42373: a poor-fit recovery fixture, not an accepted solution.

**213 assertions and 11 refusal controls pass in 1.26 s**, with zero new native
calls. Changed parent, worker, native version/kernel, input identity, numerical
result, failed/unfrozen execution, falsely complete environment, injected
retirement permission and a resealed replacement identity are refused. The
cross-binding assertions belong to this private composition; the scientific and
archive reads use maintained owners. This is not an installed reuse validator or
production artifact schema. All temporary views are removed and retained bytes
stay unchanged. Recorded process completion is historical evidence, not a fresh
live process check. Complete environment identity remains false, including the
390 unreadable OS images; no exact-reuse, execution or retirement authority follows.

Receipts under the Alder artifact anchor:
`execution-binding-20261120-02/packing.json` and
`execution-binding-20261120-02/cold-review-03.json`. Bundle SHA-256:
`928570068967ed00630ae2f6973a723d40e252cfce06501a334917a7f3e55f42`.
Binding identity:
`18667e9dae58c1aeb6749a6e870ae17d9bb221bc037273aabefd784b8c06175e`.
The first staging-path refusal and two private cold-harness failures remain
recorded: an active outer archive scope, then a relative cleanup-event path
misclassified under the original working directory. Canonical staging, separate
reader lifetimes and an isolated working directory fix the harness; no owner
guard was weakened. No full suite or native replay was repeated. Exact commands
and source hashes are in the adjacent validation record.

## Implemented result inspection from the input archive

`nasolve.metal.input_archive.inspect_recorded_fdp(archive, archive_sha256,
projection_id=..., trial_id=..., expected_parent=...)` provides a read-only
consumer of the existing v1 input archive. Supply independently retained
archive/projection/trial identities and the exact geometry or XYZ-parent lineage
dictionary. It uses the existing bounded archive reader, checks every recorded
basis/request/attempt relationship and completed review-only result state, then
returns the selected record, shared basis and exact request. A failed sibling
cannot be hidden by selecting a successful row. Identical requests still retain
distinct attempts. No original data discovery or native execution occurs.

The returned status is **`RECORDED_FDP_REVIEW`**. The result was fully replayed
when the projection was published; this inspection does not replay native
evidence, read current parent files or establish present software equivalence.
Accordingly, `native_evidence_replayed` and `current_parent_verified` are false,
and scientific acceptance remains `NOT_ASSESSED`. A mismatched expected parent
is refused; matching that caller-supplied identity is not an independent audit
of a live parent. The external archive/projection pins matter: a self-digest
alone does not authenticate newly fabricated scientific evidence.

This closes the ordinary **recorded-result inspection** seam. It adds no writer,
execution cache, new persisted schema, CLI/GUI action, pruning policy or migration.
Existing pack/expand/full-replay APIs and Cedar complete-attempt rules remain
unchanged. The inspector returns data only, with no temporary path escaping its
scope; all execution/reuse/retirement permissions stay false. An incomplete or
changed archive remains untouched. The later publication batch adapter shares one expansion across named selections;
it is still not a scientific execution session or authority to discard native evidence.

Qualification: **117 focused tests in 34.76 s**, including 17 new cases covering
source removal, repeated attempts, wrong identities/budget, changed internal
links, failed records/siblings, false acceptance and preserved partial archives.
The positive regression first fails because the API is absent. The first test
fixture revision attempted to edit read-only archive copies; its nine fixture
errors are recorded and corrected without changing owner protections.

A fresh wheel preserves all **348 packaged files**. With its build source and
original installation removed, the relocated package reads exact historical
Hg and Ag4 result records, refuses both changed-parent selections and a partial
archive, and preserves all evidence. **718 assertions** pass with original
science/source reads denied, zero native calls and all owned scratch removed.
These are saved Phenix 2.2.1-6174 results; no Phenix/Coot execution or new chemistry
qualification occurs. The incomplete environment caveat remains in force.

Evidence under the Alder artifact anchor: `recorded-inspector-20261120-01/`,
including `execution.json`, `results.xml`, `pytest.log`, and
`installed/{source-manifest.json,package-manifest.json,result.json}`.
The focused command is `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m
pytest -q -p no:cacheprovider tests/test_metal_recorded_fdp.py
tests/test_metal_input_archive.py tests/test_metal_compact.py
tests/test_metal_storage.py tests/test_metal_fdp.py`; the receipt records the
exact interpreter, working directory and XML path. No full suite reran.
Generated science, the private wheel and validation artifacts remain outside Git.

## Governing decision

Retention follows the operation, not a generic per-attempt archive policy.
When XYZ, B and f′ stay fixed, preserve the exact parent once and keep compact
Q/f″ trial records. After the result is audited and durably recorded, redundant
native output may be discarded under the new explicit storage contract. A cheap
rerun can regenerate inspection detail. When coordinates or ADPs move, use the
stronger geometry/refinement evidence and recovery discipline already developed
in Cedar. Do not wrap every frozen f″ point in a 30 MB geometry archive.

A branch point, selected solution, user pin and scientifically important
alternative remain protected throughout exploration. Pruning an incremental
trial removes expendable payload, never its identity, settings, result or parent
relationship. Failed and ambiguous branches remain visible as such.

**Parameter distinction:** ordinary frozen f″ scans fit f″ at declared fixed Q;
an occupancy-fitting stage must declare its own active variables. Both can use
this lean profile if XYZ, all ADPs and f′ remain fixed and that freeze is audited.
Simultaneous Q/f″ fitting needs separate scientific qualification; storage policy
does not introduce it. Any operation that moves XYZ/B uses the geometry profile.

## Reuse the existing owners

Cedar's `cif_runtime_evidence.py` owns checksum-indexed lossless evidence packing;
`cif_complete_attempt_archive.py` owns bounded complete-attempt partitions;
`cif_attempt_retention.py` owns archive preparation and safe duplicate retirement
under locks, stopped-process checks, sealed receipts and ancestry/current-result
protection. These are relevant primitives and invariants, not an f″ retention
contract. Their existing file/member/expansion limits must not be enlarged to fit
one enormous campaign archive. No general campaign garbage collector exists yet.

The first implementation is campaign-local: one protected object store, explicit
references and an owned scratch area. Cross-campaign deduplication and garbage
collection are deferred until ownership, export and reference lifetimes are
qualified. Reuse campaign locking, process ownership and storage primitives;
add a metal task-profile adapter rather than a competing general archive system.
Current Cedar retirement rules stay unchanged, including their failure retention.
The integrated Cedar→Alder base contains these owners and passes installed
readback. The root handoff records its completed full runtime execution plus
reviewed test-only correction and focused qualification. Reuse these owners
rather than copying modules into a parallel metal-owned archive system. The complete-attempt
retention contract does not automatically qualify a frozen-f″ retention profile.

A private installed-package rehearsal uses unchanged `pack_runtime_evidence`
and `expanded_runtime_evidence` for exact declared inputs/plans from three FT_Hg
requests and one Ag4 request. Its 36 files contain 1,274,177 logical bytes
(23 unique objects, 767,728 bytes); the verified archive is 251,197 bytes.
After owned staging removal, every file and the private layout reconstructs
exactly. Original trials and installed files remain unchanged, temporary expansion
is removed and no native program runs.

This is small-sample feasibility, not a product schema, complete parent retention
or deletion authority. Transitive parent/audit evidence and full software/environment
identity are not yet retained. Native regeneration, independent replay after
source retirement, campaign capacity and safe pruning remain unqualified. Receipts
and the preserved first harness correction live under the local Alder artifact
anchor at `input-pack-rehearsal-20261119-01/` and `input-pack-rehearsal-20261119-02/`.

## What survives

| Layer | Durable record | Disposable or bounded cache |
| --- | --- | --- |
| Dataset | Exact observations, Free-R flags, wavelength, phases where used, source identity and checksums | Repeated scratch copies |
| Geometry/B branch | Pristine atom-keyed XYZ/Q/ADP model, dictionaries, recipes, resolved restraints/parameters, B-source/calibration provenance, phase/scattering policy, software identity and essential qualification evidence | Duplicates under the geometry owner's qualified policy |
| Important node | Parent/child links, decision and alternatives, complete usable endpoint, required proof and inspection products | Only explicitly redundant copies; pin protects all required dependencies |
| Frozen f″/Q point | Exact request, per-site fitted values and references, full Q vector or lossless delta, relevant statistics, freeze/audit receipt, failure/convergence status, provenance and timings | Duplicate input/final PDB, native scratch, repeated reflection arrays, redundant logs and recomputable native payload |
| Maps | Source trial/geometry identity, labels, units, thresholds and coefficient policy; summaries stay in the trial record | Small coefficient maps may remain until selection within a byte budget; otherwise regenerate |
| Plot/table index | Rebuildable index over immutable trial records | Replaceable derived caches; never the only scientific record |

The parent includes atom order and complete identity (model, chain, residue,
insertion, alternate state, atom name and symmetry), isotropic/anisotropic ADPs,
normal/anomalous scattering definitions, solvent/model content, reference-table
version, fixed background scatterers and exact effective parameters. Store large
immutable inputs by content once. Save full resolved parameter content once per
unique value, not only a hand-written command or lossy parameter subset.

Each incremental request declares its parent fingerprint, fitted groups, Q/start
values, iteration settings, seeds, B preparation and software/native-kernel
identity. Derive cache identity from all scientific inputs and active policies,
not only metal/position/Q/f″. Different B, surrounding model, flags, phases,
restraints, starts or optimizer settings constitute different requests. A shared
parent plus a lossless, validated atom-keyed delta must recreate the exact input
bytes/state expected by the native call before reuse or execution.

A01 now retains a compact native XYZ/individual-ADP stopping receipt (2,257 bytes
for six calls in a matched native qualification). Keep native errors, limit reasons,
unknown convergence and internal-trial attribution limits in durable summaries;
exit zero is not a substitute. This observation adds no pruning authority. The
full geometry nodes and their inputs remain protected. Separate saved-array scale
controls create no new coordinate runs or maps; they are diagnostics, not frozen
f″ storage qualification or evidence that a large campaign is bounded.

A01's passive weight-selection receipt adds 1,990 bytes for a three-cycle
fixed-weight qualification, or 26,680 bytes for 84 internal XYZ weight trials
across five cycles. It retains scalar metrics, actual masks/fallback and coordinate
fingerprints, without a model per trial. These are measured geometry-diagnostic
records, not a frozen f″ footprint guarantee. The separate 11.85 MB evaluator
trace was a one-off causal diagnostic and is not a routine campaign requirement.
No existing geometry or native output becomes eligible for deletion through this
reporting change.

Keep enough compact results to plot and compare without rerunning: per-site Q,
fitted/expected f″ and ratios, per-element/group signed sums and cancellation,
B/environment identity, relevant R statistics with their stage, convergence and
fit diagnostics, freeze checks, warnings, failure category, timing and selection
reason. Numerical values retain adequate precision; rounded display values are
not the record. Store shared provenance once and reference it from each row.

## Audit and regeneration are different promises

A successful fit is audited while its native evidence is present. Publish and
re-read a compact immutable result before eligible bulky output is retired.
Record the source/result hashes and which checks ran. Preserve an append-only
retention receipt describing exactly what was removed and why.

After intentional native-payload retirement, the reader can verify the compact
record, its parent and retained dependencies; it **cannot independently replay
checks that require deleted native arrays**. Mark that evidence level explicitly.
Do not claim the old full `verify_fdp` audit still passes against missing files.
Retain full native evidence for designated proof/qualification nodes and pinned
controls. If a later decision needs stronger proof, produce a fresh linked fit.
Cheap regeneration is the intended tradeoff for the other frozen trial points.

A cache hit reuses a saved result for the identical request at its recorded
evidence level. Regeneration creates a new attempt linked to the original;
it never overwrites the old values or invents historical evidence. Record
whether it is exact byte reproduction, numerical reproduction within declared
tolerances, a different result or unavailable. Changed software or unavailable
input invalidates automatic reuse. A new result becomes a separate comparison
if its scientific basis differs. Merely having a recipe is not a recoverability
proof, and a typical short f″ runtime is not a universal timing guarantee.

### Fresh frozen-child process ownership

`metal.child_process` now exposes an opt-in fresh **process-only** route through
normal `prepare-fdp-child-process`, `run-fdp-child-process` and
`inspect-fdp-child-process` commands. It pins explicit prepared input bytes, the
maintained worker and an independently supplied protected-parent archive manifest.
The existing `materialized_parent_inputs` owner verifies parent transport before
and after the invocation. The shared `_OwnedProcesses`/`run_owned_command`
lifecycle owns the single `native-fdp` process and its descendants. Saved argv
remain provenance; no stored command or PID is replayed or signalled by inspection.

Prepare a request outside the prepared directory, then explicitly invoke it:

```text
nasolve metal prepare-fdp-child-process PREPARED --parent-manifest-sha256 PARENT_ID --output REQUEST --json
nasolve metal run-fdp-child-process PREPARED --request REQUEST --request-id REQUEST_ID --parent-archive PARENT_ARCHIVE --attempt NEW_ATTEMPT --phenix-root PHENIX_ROOT --timeout 240 --json
nasolve metal inspect-fdp-child-process ATTEMPT --request-id REQUEST_ID --json
```

The producer reserves a fresh attempt, copies exact inputs/worker, and writes
shared process records plus a durable outcome. `COMPLETED` means process exit
and input/parent transport checks, **not** an accepted refinement. Outcomes also
include `FAILED`, `TIMED_OUT`, `INTERRUPTED`, `STOP_UNCERTAIN` and
`REVIEW_REQUIRED`. Timeout records preserve the shared owner's actual termination
code. Partial output is retained. A changed parent after worker exit prevents a
successful outcome. A publication gap remains visible through process inspection.

An optional `--retry-from OLD_ATTEMPT` requires a matching request/parent/worker
and native executable, a sealed verified stop, and a failed/timed-out/interrupted
outcome. It creates a separate fresh attempt linked to the old outcome digest;
the old attempt remains immutable. Completed, live, uncertain, changed-input or
unsealed outcomes are not eligible. Inspection never retries automatically.
This is not an aggregate campaign reservation or a lock against separately
requested fresh parallel invocations.

New persisted contracts are `metal-fdp-child-process-request` v1 (`request_id`),
the shared process-record schema under policy `metal-fdp-child-process-v1`, and
`metal-fdp-child-process-outcome` v1 (durable `record_sha256`). Input names are
explicit and portable within the prepared/child mounts; parent selection uses
its independent manifest digest and explicit archive mount. No basename search,
host-only operational reference, old trial migration or existing-format change
is introduced. Requests allow 3–128 input files, at most 64 MiB total, a 1 MiB
request record and a positive deadline up to 600 s. Parent transport has its
separate declared disk allowance/reserve; native output quota and campaign
reservations are not implemented by this seam.

Qualification: **112 focused tests pass in 28.18 s**, plus one additional
late-parent-change test in 1.34 s on unchanged runtime. The first nine-pass/
one-failure run exposed a missing timeout termination code and is retained in
the validation record; it was fixed. Tests exercise a live child, blocked retry,
actual timeout/descendant shutdown, uncertain-stop refusal, fresh retry, changed
pins/inputs, interrupted outcome publication and relocated readback. A fresh
relocated installation preserves all 350 package members and passes 366 checks
including four simulated-worker invocations through the normal CLI. Build and
original install paths are removed; original product/science reads are denied.
No Phenix/Coot science job or full suite runs. The worker targets Phenix
2.2.1-6174, but these controls use tiny simulated executable/discovery fixtures,
not native crystallographic qualification.

Local evidence: `child-process-20261120-01/{validation.json,installed-review.json,
source-manifest.json,package-manifest.json}` under the private Alder artifact
anchor. The exact focused commands and installed runner are recorded there.
Only `metal/child_process.py`, the CLI and its focused test module change runtime;
shared process/archive owners are unchanged.

**Remaining prerequisite:** the route validates parent **transport identity**,
not scientific parent admission or derivation of the prepared model from that
parent. It does not replay `make_plan`/`audit_result`, publish a compact scientific
result, enforce convergence, grant reuse, or prune outputs. The legacy `fdp`
producer and historical numbered-trial verifier are unchanged. Before using this
seam as the compact f″ executor, connect ordinary parent/input admission, freeze
and reflection audit, durable compact result publication/readback, protections
and reservations. Native acceptance still requires the A01/A02 scientific gates.

### Stopped-child output byte evidence

The existing `metal.storage._snapshot` and `_hash` already provide bounded,
regular-file inventory and change detection. `metal.child_outputs` reuses those
helpers and the campaign create-only record writer, without a second archive or
copy of native payload. This closes the output-byte gap after the process owner;
it does not close scientific admission or accept refinement results.

The explicit Python calls are `freeze_child_outputs(child, request_id=ID,
max_bytes=64*1024*1024)` and `inspect_child_outputs(child, request_id=ID,
output_id=RECORD_SHA256)`. The latter independently pins the receipt. There is no
new CLI command or automatic call from the scientific producer yet.

A receipt requires a `COMPLETED` child with verified shutdown and parent transport.
The job's prepared inputs must still match their pinned bytes. The maintained
worker's `native-result.json.gz`, `final.pdb` and `effective-final.phil` must be
present and nonempty. Presence does **not** establish valid contents: the reader
intentionally performs no gzip, model, reflection or PHIL scientific validation.
Every flat job file, including inputs/logs and additional native output, is hashed.
Missing/extra/changed files, symlinks, directories, nonportable names and inventory
changes during hashing refuse. The child outcome is rechecked before publication.
Failed, timed-out, live or uncertain attempts retain their evidence without this
completed-output receipt. A partial job that exits zero still cannot seal unless
all required output names are present and nonempty.

The optional `outputs.json` record uses `metal-fdp-child-output-evidence` v1:
exact request/outcome hashes, the child anchor plus `native/fdp/job` relative path,
all file SHA-256/size pairs, required names, total bytes and declared byte budget.
It is durable and create-only, followed by exact readback; existing records are
never overwritten. This freezes the **record**, not filesystem permissions.
Subsequent file changes invalidate inspection. A failed post-publication readback
retains the receipt and payload for review, without scientific or cleanup authority.
No old process/trial format changes or migration are required.

Limits are 256 regular files, 64 MiB default inventory budget, an explicitly
selected budget no larger than 1 GiB, and a 1 MiB receipt read limit. This is a
bounded inspection allowance, **not** a native output quota or campaign storage
capacity claim. Unknown nested output layouts require a separate qualified owner.
`scientific_acceptance=NOT_ASSESSED` and `retirement_authorized=false` remain explicit.

Qualification: **47 focused tests pass in 11.95 s** using
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src
/private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider
 tests/test_metal_child_outputs.py tests/test_metal_child_process.py
 tests/test_metal_storage.py`.
They cover actual live/timeout/uncertain process ownership, missing/empty output,
same-size mutations, added/missing files, changed inputs, publication immutability,
late-owner changes, bounded counts/bytes and relocation. A fresh installed probe
passes 374 checks including 351 exact package members, with four simulated native
process invocations. Original build/install paths are removed and original
product/science access is denied. Private evidence is
`child-outputs-20261120-01/{validation.json,installed-review.json}` under the Alder
artifact anchor; `runners/A310_installed_child_outputs.py` reproduces the probe.
Phenix 2.2.1-6174 remains the worker target, but no Phenix/Coot science job or full
suite was run. Generated fixtures, package wheel and reports remain local.

Next connect ordinary parent/input admission and exact typed reader controls to
the scientific launch, then run the unchanged freeze/FreeR/model audit over these
bound bytes and publish/reread the compact scientific result. Willow's W182
reader-control gap is a separate prerequisite, not supplied by this inventory.
Quota/reservation and retirement integration remain open; A04 stays partial.


### Protected parent-to-prepared-input derivation

The explicit read-only `metal.child_inputs.verify_child_inputs` API and
`nasolve metal verify-fdp-child-inputs` command now connect the already pinned
parent archive and prepared request. They reuse ordinary checkpoint resolution,
the exact metal geometry/XYZ reader and the existing `make_plan`/`parameters`
derivation. They do not implement a second environmental-B or refinement policy.

```text
nasolve metal verify-fdp-child-inputs PREPARED --parent-archive PARENT_ARCHIVE --request REQUEST --request-id REQUEST_ID --run-relative DATASET/AutoMR/run_001 --endpoint-relative Metal/xyz_001 --json
```

`--run-relative` is relative to the declared parent layout, and
`--endpoint-relative` is the exact geometry/XYZ directory within that run.
There is no basename discovery. The parent archive digest comes from the
independently pinned child request. Inside its protected temporary view, the
existing metal reader replays the endpoint and hypothesis; the ordinary registry
reader resolves that hypothesis's source checkpoint once. Its model, observations,
ordered restraints and phases must agree with the captured context and resolve
inside the declared parent layout. Frozen report provenance remains historical;
a display-only update to the current report does not change source identity.

The replay derives the model, observations, all ordered resources, parameters,
plan and native arguments and requires exact equality with the request's prepared
input inventory. Native XYZ endpoints require the existing explicit environmental
B policy (including explicit `keep` where intended); the B source is their refined
model. Fixed Q and scientific defaults are unchanged. Changed prepared bytes
cannot pass merely by receiving new hashes. Parent and prepared input changes
are rechecked before a result is returned; temporary views are removed.

The emitted `metal-fdp-child-input-derivation` v1 report carries exact request,
parent, endpoint and context identities, portable parent/run references, source
kind, B policy, Free-R declaration and transport status. `derivation_verified`
and `ordinary_checkpoint_verified` describe those checks only. Declared metadata
and Sasaki references are replayed, not independently reacquired; no new original
Free-R audit, native process, scientific acceptance, automatic reuse or retirement
is authorized. The producer/process/output receipt formats stay unchanged. This
is not a durable multi-point admission session, cached pass, or automatic launch
gate yet; a normal scientific run must compose the remaining owners explicitly.

`--reader-control-policy` currently refuses every non-null value. The declared
`interpretation_controls` role also refuses by presence, even with an empty PHIL
list, in relevant root/source records and their checked-preparation request.
This is a capability guard, not a parser or implementation of Willow W186.
Unsupported controls cannot be silently treated as ordinary restraints here.

The existing input limit (3–128 files, 64 MiB) and parent disk/reserve bounds are
reused. No quota is relaxed. Exact validation commands and package/readback
identities are in the [current handoff](metal-development-handoff.md).
Qualification is 80 focused tests plus two linked-role controls, 364 installed
checks (352 package members), and 389 installed real-input checks with original
sources denied. These counts include checksum assertions, not independent
scientific experiments. Real coverage is a legacy ordinary Hg geometry and Ag4
native XYZ endpoint; broader checked-parent ancestry is not newly qualified.
The archived Ag4 model yields the same base-mean B=188.75 Å²/Q=1 at all four
sites; the Hg control retains its old B=25 Å²/Q=0.60. Poor-fit and negative-f″
results retain their original review state. No new Phenix/Coot calculation occurs.

A separate execution prerequisite was identified during this audit: copying
`_fdp_native.py` alone omits its maintained `fit_diagnostics` sibling and optional
`anomalous_maps`/`map_diagnostics` helpers. The simulated process qualification
did not establish that code closure. Resolve and pin the maintained helper bundle
before attempting genuine native execution through the fresh route. Existing
source-directory execution and historical workers remain unchanged.

### Output-to-scientific-audit handoff: exact remaining boundary

The output receipt establishes bytes and process linkage. The next scientific
caller must supply a separately admitted parent and derived plan/model; it must
not fabricate a legacy numbered-trial manifest or historical process identity.
The component call already exists:

```python
result = audit_result(plan, model_bytes, json.loads(gzip.decompress(native_result_bytes)))
```

It checks effective policy, complete atom/group identity and parameter freedoms,
fixed XYZ/Q/B/U, fixed f′ and background f″, normal scattering-type invariance,
and native before/after reflection indices/Free-R membership. Only common F/σ
rescaling is allowed. Source/kernel fingerprints are required, but their presence
is not independent build qualification. Separate existing caller checks compare
serialized `final.pdb` atoms/state, usable original Free-R evidence, and requested
anomalous map files. `audit_result` does not itself replay parent derivation,
prove original MTZ provenance, validate the final PDB file, or choose a solution.

The exact blocker is ordinary parent-to-prepared-input derivation. The existing
`_input_bundle` obtains checked geometry/XYZ lineage, hypothesis/sites, preview,
model, original observations and ordered resources. `make_plan` then applies the
explicit environmental B policy to the open-refined endpoint, fixed per-trial Q,
wavelength and all-element references; `parameters` produces exact native inputs.
Native XYZ endpoints require an explicit B policy. The fresh route currently
pins prepared bytes and a parent archive independently; that is not proof of this
derivation. Typed reader controls must also reach the exact launch separately
from restraints. A future auditor must use the freshly admitted parent and
original `FreeR_flag` audit rather than borrow a historical recipe parent or its
process identity. `verify_fdp(run, numbered_trial)` remains the unchanged legacy
whole-trial verifier, not an adapter for the fresh process receipt.

The read-only `output-audit-handoff-20261120-01/review.json` trace reuses the earlier
cold component qualification after verifying unchanged auditor modules. It checks
96 receipt/path/checksum assertions against one explicitly selected saved FT_Hg
trial; these are integrity checks, not new fits or independent science experiments.
Historical files remain unchanged, and no process receipt is made for them.
At λ=0.92009 Å, the selected saved trial has Hg Q=0.60, B=25 Å², f′=-8.10018 e,
f″=35.30914 e versus 8.67857 e expected, Rwork=0.397237 and Rfree=0.423648.
This is a low-B poor-fit diagnostic, not an accepted endpoint or evidence for
additional atoms. The stored Free-R receipt is usable but `NOISY`: 82 free groups
among 1,635 independent stored groups, versus 109 free observations among 2,128
anomalous observations in the native capture. These counts describe different
representations. `SA_flag` is present in the data but is not the selected flag.

One new compatibility control proves the distinction: a synthetic completed
child can seal exact bytes containing a +1 Å² native B change, while the unchanged
scientific auditor rejects those same bytes. It passes in 1.46 s with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src
/private/tmp/willow-w94-pivot/env/bin/python -B -m pytest -q -p no:cacheprovider
 tests/test_metal_child_outputs.py::test_exact_output_bytes_do_not_bypass_existing_scientific_freeze_audit`.
Runtime/package code is unchanged from the preceding installed qualification;
no repeated suite, native science or cleanup. The private trace's `review.html`
gives the small science table and exact boundary for the combined report.

### Measured audit-retention boundary on historical FT trials

The three already-published FT_Hg attempts now have a private cold component-audit
rehearsal using the same installed archive and freeze-audit owners. Exact native
arrays, Free-R receipts, final PDBs and original manifests form a 13-path sidecar
with nine distinct objects. After restoring inputs and closing that archive view,
the sidecar opens separately; the unchanged `audit_result` reproduces all three
full-precision stored results. The original serialized-PDB freeze check also
passes. Nineteen controls reject changed XYZ, Q, B, fixed f′, Free-R assignments,
scalar-only pseudo-evidence and an incomplete legacy-trial copy. This is **component
audit replay**, not complete `verify_fdp`, live-parent verification or native
regeneration. No original trial or parent is changed.

The fair compressed baseline uses the same shared archive owner:

| Package for the same three attempts | Measured bytes | Retained evidence scope |
| --- | ---: | --- |
| All 60 original trial files, 37 distinct objects | 620,211 | Complete selected trial files; protected parent remains separate |
| Exact inputs/publication plus selected audit sidecar | 517,639 | Recorded results and the freeze/serialized-model audit components |
| Exact inputs and pinned published results | 136,711 | Historical measurements; no independent replay of omitted native arrays |

Original uncompressed trial files total 2,478,875 B. The selective audit package
saves only 102,572 B (16.5%) relative to the compressed complete-trial baseline.
Do not claim the raw-to-compressed difference as a benefit of evidence retirement.
This sample supports retaining complete shared archives at important/proof nodes,
while cheap ordinary children can explicitly carry the historical-only evidence
level after lifecycle qualification. It does **not** justify a new production
sidecar format by itself. The private sidecar is diagnostic evidence, not a
published schema or permission to remove files.

These historical low-B, poor-fit examples do not qualify A01/A02 or predict a
200-dataset campaign's capacity. Protected parents, complete software identity,
map-bearing cases, peak native scratch and concurrent reservations remain
additional. The temporary full-trial baseline copy/archive is removed after its
receipt; original scientific files remain untouched. Existing immutable trial
formats/readers are unchanged.

Local evidence: `compact-audit-boundary-20261120-01/{review.json,cold-review.json,
full-trial-baseline.json,delivery.json}` and the visually checked
`review.html`/`retention-scopes.svg` under the private Alder artifact anchor.
Read-only runners `A306_compact_audit_boundary.py` and
`A307_full_trial_archive_baseline.py` run with
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/willow-w94-pivot/env/bin/python -B`.
There are 35 transport/source checks and 31 cold checks plus the 19 refusals;
no new Phenix/Coot execution or full suite. Saved native evidence is from
Phenix 2.2.1-6174. The installed wheel is unchanged from the qualified batch reader.

**Next integration boundary:** the legacy frozen producer still uses
`subprocess.run` with a timeout; the separate fresh process-only route above now
exercises the shared lifecycle. A disposable scientific child must connect that
route to ordinary parent/input admission and compact result publication before
retirement is possible; a saved PID or scalar success flag is insufficient.
Keep that new lifecycle separate from historical numbered trial inventories.
Reserve owned scratch, bind a protected parent and exact worker/inputs, audit
while full output exists, durably publish and reread the new compact record,
verify process shutdown and protection/pins, then retire only explicitly owned
new disposable payload. Failures and interrupted publication retain evidence.
Reuse shared locking/record/archive owners; do not apply the CIF complete-attempt
schema to metal trials or claim that the current publication receipt already
implements this lifecycle. Scientific parent and runtime-identity gates remain.

## Retention through the solution tree

Protect dataset roots, geometry/B branch roots, important chemical or metal-count
bifurcations, selected checkpoints, explicit pins and representative alternatives.
Keep their transitive input/evidence dependencies even when another view prunes
the same branch. Descendant f″ points retain compact records; they do not each
need a duplicate pristine model. Immutable geometry parents used for reruns may
never point only into disposable scratch or to an unowned external file.

Maps follow a separate byte budget. Measure coefficient sizes first. Keep small
fdp maps while candidates are being compared when that budget permits; selection
pins the important maps and releases eligible unselected maps. A map shared by
multiple views has one stored payload with explicit references. Model-assisted
ordinary/anomalous maps keep their distinct phase/data provenance. A missing map
means regeneration is needed, not that no density exists.

For frozen trials, routine recoverable failures keep compact input/error/stop
records; unique or unclassified failures retain fuller evidence until reviewed.
Active, interrupted or ownership-uncertain processes cannot be compacted. No
filename extension alone authorizes deletion. Legacy geometry failures retain
their existing Cedar rules; the lean profile does not silently override them.

## Capacity and scheduling

Use bytes, not trial counts, to enforce both a campaign retained-data budget and
a peak workspace budget. Reserve before launching jobs or expanding an archive:

`peak = shared inputs + protected nodes + compact records + map cache + active scratch + compaction overlap + free-space reserve`

Reservations are atomic across concurrent workers. Charge attempts, retries,
map regeneration, evidence packing and export; temporary duplication during
compaction also consumes space. Reconcile reservations against actual usage and
release only after owned processes stop. If the budget cannot be met, stop
scheduling, retain recoverable state and offer a smaller map cache, fewer active
jobs, a larger explicit budget or moving the campaign. Never reclaim protected
inputs to force a run to continue. User-facing controls are campaign space limit,
map retention and pinned solutions; there should be no per-trial cleanup prompt.

A local sample of three existing frozen fits occupies about 1.0–1.17 MB each,
including duplicate inputs/logs. At **200 datasets × 100 total fits per dataset**,
that alone projects to roughly **20–23.4 GB**, before upstream geometry/MR,
failures and working space. This is arithmetic over small examples, not a
native 200-dataset stress test. Exact private inventories are retained with the
handoff, not committed scientific payloads.

A separate completed A01 geometry-control inventory on 17 November finds that
repeated coverage records dominate storage, while its ten map-coefficient files
are comparatively small. This supports storing static policy/inventory content
once per authenticated phase and referencing it from compact observations.
The measured gzip/dedup projection is read-only arithmetic: no archive or cold
recovery qualification, deletion, or permission to prune those geometry nodes
follows. Exact inventories remain in the private review linked by the handoff.

A later bounded map/frame/scaling cohort measures 79,946,678 bytes across 337
files before sealing, including 25,300,254 bytes of exact duplication. Four
coefficient maps total 98,880 bytes. Its passive final-scale observation is
6,118 bytes, but this compact receipt does not replace the protected geometry
inputs, full audits or replay evidence. The earlier 14-map comparison references
existing coefficients without copying them. These distinct inventory boundaries
are recorded locally; no pruning or archive was performed.

A **1–8 KiB compact record per point** is a design target: 20,000 points would
use roughly **20–164 MB**, plus shared inputs, protected geometry/evidence and
maps. It is not an implemented footprint guarantee. Measured anomalous map
coefficients in two samples are **21,420 and 26,100 bytes**: retaining one such
map for every point would add roughly **428–522 MB**. Larger reflection sets and
other map types can be much larger, so retain-by-size with a cap rather than
always-delete or always-keep. Total campaign estimates must include geometry
parents; compact f″ rows do not make upstream refinement archives free.

## Safe implementation order and acceptance

1. **Inventory and estimator:** classify actual files through manifests, measure
   shared/unique bytes and forecast explicit workloads. Read-only sample inventory
   is implemented; native peak scratch measurement remains pending and must be
   supplied as an explicit scenario allowance for now.
2. **Versioned compact frozen records:** the read-only result projection and
   full-source replay, exact input recovery and explicit parent-layout transport
   are implemented. Scientific parent selection, complete execution identity and
   durable compact child publication remain pending. Existing schema-1 runs stay untouched and verifiable.
3. **Bounded executor:** run one cheap f″ child in owned scratch, audit, commit
   and reread the result, then retire only newly declared disposable payload.
   First native control is a qualified single-Hg branch, then mixed Au/Ag/cluster.
4. **Recovery and important-node protection:** retain pins/ancestors/alternatives,
   test map regeneration and identical-request reuse, preserve discrepancies.
5. **Budgeted campaign scheduling:** concurrent reservations, crash-safe cleanup,
   byte-capped map cache and relocatable export; only then enable large fan-out.

A new storage profile requires a new reader/manifest contract. Do not retrofit
it by deleting files promised by old immutable manifests. Optional migration is
an explicit verified conversion into a new record with the old lineage retained.

Before destructive retirement is enabled, tests must cover compact numerical
round-trips, all cache-key changes, altered-parent rejection, cold relocation
with original paths absent, shared references/pins, wrong checksums/symlinks,
process liveness, disk exhaustion, crashes between publication and retirement,
interrupted cleanup, concurrent reservations and bounded archive expansion.
Native rehearsal must delete disposable outputs **from a copied test campaign**,
then regenerate model/maps from retained inputs and compare science with declared
tolerances. Include both matching and divergent reruns. Simulate 200 datasets
and 20,000 compact points with realistic parent sizes and map distributions,
then calibrate with a bounded real panel. Planning alone is not acceptance.
