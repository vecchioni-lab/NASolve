# Metal campaign storage and recovery plan

Status: **design scoped, implementation pending**; 17 November 2026.
The [post-merge development roadmap](metal-development-roadmap.md) places this
work at **A04**, after single-dataset ligand/open-refinement qualification and
before large f″ campaigns. It is a feature milestone after merge, not a
prerequisite for merging the current experimental implementation.
This document does not enable cleanup or change an existing immutable run.

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
   shared/unique bytes and peak scratch, forecast 200-dataset workloads. Read-only.
2. **Versioned compact frozen records:** shared immutable parent store, complete
   request fingerprints, compact results and declared audit levels; lossless
   input materialization. Existing schema-1 runs remain untouched and verifiable.
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
