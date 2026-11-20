# Metal campaign storage and recovery plan

Status: **inventory, compact projection and exact input transport implemented; complete retention/regeneration pending**; 20 November 2026.
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
scientific-output retirement remain unqualified. There is no new CLI/GUI action.

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

**Next:** settle the shared production lifecycle owner, qualify trusted software
identity and the lean frozen-child audit/regeneration contract, then add explicit
campaign reservations and crash-safe publication/retirement. Preserve important
geometry parents throughout. No original run is yet eligible for deletion, and
the diagnostic recovery alone does not provide a reusable metal-trial session.

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
   full-source replay are implemented. Shared retained parents, complete execution
   identity, durable compact publication and lossless native input materialization
   remain pending. Existing schema-1 runs stay untouched and verifiable.
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
