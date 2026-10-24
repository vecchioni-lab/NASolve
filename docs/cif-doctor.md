# CIF Doctor

## Automatic continuation and student-facing decisions

Students are not asked to inspect CIF bond tables or approve candidate
restraints. NASolve should attempt bounded source-preserving repairs and
optimization, retain the best usable result, and continue solving with explicit
notes when a component does not converge or retains numerical outliers. A
native or partially repaired dictionary is a valid fallback when it remains
usable. Never erase a warning to make that decision look like a scientific PASS.

| Evidence | Decision |
| --- | --- |
| Nonconvergence, residual geometry deviations or different DNA sugar pucker | Retain a usable candidate, continue and report limitations. |
| Stereo or another optional layer not independently assessed | Preserve the unknown result and report it; do not invent a contradiction or require student CIF approval. |
| Demonstrated atom/graph/order/state corruption, stereochemical inversion, nonfinite parameters, missing essential restraints or native inability to interpret the component | Exclude that candidate and try the next usable fallback automatically. |
| No usable candidate after bounded recovery | Stop with the component and concrete missing capability; do not ask the student to adjudicate a CIF. |

A temporary local-template sign warning is not a demonstrated inversion of the
assembled molecule and must not be converted directly into a hard exclusion.

Sugar pucker is conformational freedom; tetrahedral stereochemical inversion is
a different configuration. No stereocentre, including ordinary DNA or bridged
ATL, becomes unconstrained just to obtain convergence. NARestraints pairing and
stacking, curated-source precedence and fixed native target mechanics retain
their authority. Final structural/model validation remains distinct from CIF
inspection.

**Implemented now:** `cif-automatic-usable-fallback-v1` is a pure, tested decision
core consuming verified adapter evidence. It excludes unusable alternatives,
preserves declared source authority, prefers demonstrated stereo preservation
within that authority, and ranks endpoints by energy only under the same frozen
objective. Otherwise declared source order wins. Nonconvergence is a reportable
note, not rejection. Inputs must describe one component and one declared
chemical state; this policy does not infer protonation or repair chemistry.
The decision never changes files, proxies, weights, checkpoint selection or
native mechanics. PostMR adds a plain-language `solution_report` summary to its
existing CIF Doctor receipts without introducing an approval gate.

C55 adds an opt-in isolated native qualification-to-decision adapter for saved
complete candidates. Returned C55 supplies complete native data; corrected v2
saved replay passes all six cases and three decisions. It selects only within that
isolated generated-candidate pool and does not adopt a linked component.
Returned C56 reproduces those passes without new native calls. C57 adds a
source-declared DNA metadata candidate and automatic verified-original fallback
within the same isolated scope. Returned C57 passes all six native equivalence
checks and three selections. Returned C58 passes separate linked-context
controls. Returned C59 qualifies a separate full-scaffold DP bundle and selects
it automatically with notes. Returned C60 retains a usable geometry endpoint
after fresh initial/endpoint derivative checks and exact native readback pass,
while reporting its iteration limit. Returned C61 passes the portable bundle's
15 staged native checks. Returned C62 completes Coot construction but retains
all three raw sites for
unmatched OP3, without exercising rigid base transport. C63 adds ordinary
source-proven internal-phosphate context preparation before that transport,
using the unchanged phosphate sanitizer and immutable raw coordinates. Fresh
controls call the same ordinary API. Automated acquisition/repair adoption,
generic NAR compilation, production checkpoints/refinement and PDF rendering
remain separate; no run or checkpoint is manufactured from diagnostic evidence.

**Still to integrate:** automatic repair/generation on misses, production
qualification, verified effective-bundle adoption and the solution PDF renderer.
The decision core and isolated adapter are not a claim of deployed
end-to-end automatic recovery. The eventual PDF must explain what was tried,
which source/candidate was used, bounded stopping evidence, fallback reasons
and unresolved limitations, with technical receipts retained for developers.
Existing diagnostic `REVIEW`/exit 2 denotes internal evidence, not student CIF
homework; old diagnostic results remain unchanged.

## Persistent local reuse of qualified repairs

**Implemented shared component store/resolver and ordinary PostMR cache
acquisition (C71). Automatic repair on misses and full-run qualification remain
separate.** `nasolve.cif_dictionary_store.resolve_qualified_dictionary`
consults persistent local numerics before its verified acquisition callback.
C66 explicitly exercises this API with the qualified DP/PDU/5PC candidates.
It does not silently enable production repair/adoption or make students save,
select or inspect CIF tables.

The semantic lookup binds exact source bytes and authority, original atom names,
declared elements/orders/formal charges/explicit hydrogens/stereochemistry, the
numerical recipe and generator family. Component code alone is insufficient.
The immutable entry digest also binds exact candidate bytes, the complete
original producer identity, consumer fingerprints, native qualification and
stopping/limitation evidence. Usable nonconverged candidates remain reusable.
Curated and explicit-source precedence is selected upstream and remains part
of the request; a local repair cannot override another source or chemical state.

Changing a consumer, native qualification policy or both Phenix's builder and
consumer retains existing numerics for requalification before regeneration.
An upgraded producer is not recorded as the author of old numerical bytes.
Different numerical recipes/backends create distinct requests. Source/candidate
bindings and current graph/configuration are checked on every entry read;
incomplete, corrupt, failed or symlink-substituted entries cannot become hits.
Publication verifies an owned staging directory and renames it atomically,
without overwriting a historical entry. Cache-write failure still permits a
separately verified, independently frozen run copy.

Base numerics are separate from terminal/linkage modifiers and coordinate-based
evidence. New crystal coordinates do not trigger component optimization. A hit
does not certify a new site, model or installed runtime. C66 inherits verified
Phenix 2.2.1-6174 source fingerprints; it neither reprobes the installed runtime
nor claims a captured energy-library resource-file fingerprint. Current-site
and changed-consumer native qualification remain explicit separate work.

Each run freezes `source.cif`, `dictionary.cif`, `qualification.json`,
`provenance.json` and `manifest.json` beneath an owned `entry/` directory.
`resolution.json` uses the `dictionary_resolution` and `dictionary_entry`
anchors. Its source/parameter/qualification hashes and original stopping notes
remain usable after cache removal, source-capsule loss or relocation. Selection
among matching entries uses the existing usable-candidate policy and stable
entry order, without comparing energies from different objectives.

Default storage is user-local application data outside tracked source trees:
`~/Library/Application Support/NASolve/cif-dictionaries/v1` on macOS,
`${XDG_DATA_HOME:-~/.local/share}/nasolve/cif-dictionaries/v1` on Linux and
`%LOCALAPPDATA%/NASolve/cif-dictionaries/v1` on Windows. `NASOLVE_CIF_STORE`
overrides this path; the C66 diagnostic also accepts `--dictionary-store PATH`.
No new dependency, daemon, network upload or student configuration is required.
Ordinary PostMR now records reuse and preserved limitations in its solution
summary. PDF rendering and full effective-bundle qualification remain separate.

The explicit `--local-dictionary-reuse-only` diagnostic accepts exact C65 and
preserves every parent payload. For each component it tests persistence,
repeat reuse without acquisition, exact bytes/notes, source and authority
mismatches, consumer requalification and frozen snapshots after removal of an
owned cache copy. It never removes user entries. Zero new native, generator,
optimizer, Coot, ReadySet or refinement processes are requested; overall REVIEW
still describes the ordinary-pipeline and scientific boundary.

Returned C66 verifies all **3,659 payloads** and the byte-identical C65
parent and manifest. DP, PDU and 5PC each pass ten reuse controls: their
first qualified dictionaries are saved and repeated requests reuse the exact
bytes without acquisition. Source/authority mismatches are excluded and a
changed consumer requires requalification before generation. Independent
replay reproduces all 30 controls and nine frozen snapshots, including original
stopping/limitation notes, with every subprocess forbidden. Ordinary PostMR
orchestration and the requested eight-pair live run remain separate work.

## Ordinary source and declared-pair preflight

Returned C67 verifies all **3,713 payloads**, including the unchanged C66
parent and manifest. The ordinary source selector passes **15/15 sources**
(six curated, nine installed CCD), and NARestraints compiles **8/8 declared
pairs and 16/16 stacking orientations**. Independent maintained replay
reproduces all 39 source/PHIL files exactly; report differences are limited
to historical source paths. DP/PDU/5PC saved repairs correctly miss because
their raw source bytes/authority differ; all inventoried chemical declarations
match. No repair is substituted by component name.
No native process or adoption occurs; full-run integration remains open.

`--ordinary-acquisition-only` accepts exact returned C66. It replays the
closed saved evidence, selects sources through the same ligand_source API
used by ordinary ligand_dictionary calls, freezes each source and compiles
the eight literal intended pairs without distance guessing or coordinates.
Both stack orientations use the existing NARestraints matrix. Configured
ReadySet paths select installed CCD files; no environment/version subprocess
runs. A saved-repair MISS caused by different source bytes/authority is expected
and never authorizes substitution. All original stopping notes survive.

Returned evidence is ORDINARY_ACQUISITION_CONTROLS_PASS: 15/15 sources,
8/8 pairs and 16/16 stack orientations. Overall REVIEW/exit 2 records the
remaining native integration/scientific scope; it requires no student CIF
approval. ATL remains an independent public source/compiler control.

## Reuse across a verified source projection (Cedar 68)

C68 adds an ordinary-source reuse API without weakening exact cache keys.
It selects the ordinary source first, verifies a saved projection against its
named chemistry and configuration, then requires current isolated native
usability before publishing a new source/authority-bound entry. Numerical bytes,
original producer and stopping notes are retained; repeats reuse them. Failed
candidates retain the selected source for standard preparation. No student
CIF inspection, generation, optimizer or production adoption is introduced.
Returned C68 preserves all 3,766 payloads and the complete C67 parent.
All three source projections pass, but native input/output placement triggers
the preservation guard before any worker launches. Its historical call count
of three records attempts; it supplies no fresh native qualification.
Returned C69 completes all three native reads: 63/63 usability checks and
six fixed repeat evaluations pass. A later reporting call supplies two mutually
exclusive auditor inputs, so source-bound publication/repeats are not selected.
Returned C70 verifies all 4,008 payloads and the complete C69 parent. DP,
PDU and 5PC each publish a qualified source-bound entry and immediately REUSE
the exact numerical bytes. Maintained code reproduces all 63 native checks,
both triple reports and 72 result artifacts; only explicitly nonoperational
source paths rebase. All six frozen copies resolve after original source/cache/
evidence removal with external scientific reads forbidden. Original producer
and stopping notes survive, including PDU nonconvergence. No new native process
runs. Current installation/site/model checks and ordinary PostMR/full-run
integration remain separate; no repeat of this saved cache gate is needed.

C71 connects local reuse to ordinary PostMR. Before ReadySet,
`prepare_postmr_dictionaries` selects and freezes ordinary sources, then checks
eligible source-bound cached numerics. Original sources still drive Coot and
remain in source receipts. The existing normalization/combination and dictionary
precedence receive cached numerical inputs only when their exact source,
authority, supported recipe/backend and current native consumer match.
Fresh version discovery is lazy and runs once per eligible batch; the selected
native dispatcher and all eight recorded API/three energy source hashes must
match inside the configured installation. This is the recorded identity scope,
not an exhaustive compiled-kernel or energy-library-data fingerprint.

Missing, corrupt, unsupported or changed-consumer entries retain ordinary
preparation with notes. Missing curated sources keep their existing refusal.
The cache is read-only and each run freezes independent relative/hash-bound
copies with original producer/stopping evidence. Nonconvergence remains a note;
no student inspects CIFs. PostMR records reuse/fallback and plain-language notes.
This adapter does not generate or optimize a dictionary. Uncached components
continue through the existing preparation path.

Methods: validate indexed entries against the selected source and the existing
isolated qualifier, verify the current recorded consumer identity, use the
existing automatic usable-candidate policy and exact-key resolver, then freeze
source and numerics separately. C71's explicit `--postmr-dictionary-reuse-only`
probe consumes exact returned C70 and calls this same ordinary API. The actual
Mac return verifies all three REUSED cases and POSTMR_CACHE_HANDOFF_PASS: exact
saved numerical bytes pass all 63 checks in three fresh Phenix 2.2.1-6174 native
readbacks. Six fixed energy/gradient evaluations are finite and exactly repeated;
all worker dispatcher/API/energy inventories match the selected recorded consumer.
Existing normalization changes none of the three dictionaries. The combined
31,252-byte ReadySet input reproduces exactly. Both triple/180-degree target
screens pass for PDU/5PC; linear-axis torsions and seed bending remain notes.

All 4,231 payloads, the unchanged C70 parent and 159 runtime members verify.
Reconstructing only NAR dirty-state metadata reproduces the reported runner SHA.
All three independent run copies resolve after original source/cache/evidence
removal with external scientific reads and every subprocess forbidden. Original
producer/stopping notes, including usable PDU nonconvergence, are unchanged.
No ReadySet, Coot, generator or optimizer executes in this probe. The next
boundary is observing ordinary ReadySet consumption/no-regeneration and current
linked/whole-model NARestraints membership. The eight-pair full run, refinement
and solution PDF remain separate. Inspect-only remains a captured-source fallback
check with no current-consumer/cache-hit/native claim. This returned-evidence
update changes no runtime, schema, chemistry, mechanics or dependency.

C72 methods: consume the exact verified C71 capsule and preserve all 4,231
payloads. Separate DP/PDU/5PC controls use the ordinary `_run_readyset` helper
and its unchanged CLI arguments. An optional private execution hook launches
the selected Phenix Python on the dispatcher's verified literal entrypoint as
`__main__`; the shell dispatcher itself is not executed. A process-local profile
observer records selected eLBOW builder/template calls, Python subprocess calls
and effective ReadySet actions. It replaces no native function and overrides no
native argument. Fresh bounded source snapshots and the recorded consumer
identity are verified before/after execution. An absent call is reported only
within this observer scope, never as exhaustive native/optimizer coverage.

The copied heavy seed omits H/D records while retaining exact heavy coordinates.
Require a completed untruncated observation, the requested actions, no observed
builder/template/child calls, unchanged named heavy sites and exact cached
numerics under ordinary parameterized-input precedence. Only then read back
effective terms on the unchanged C71 full-H seed, with current consumer checks,
the existing 21-check qualifier and separate triple screens. The native H sites
are saved control coordinates, not new ReadySet placements. Each of at most
three ReadySet calls is capped at 180 seconds; each fixed readback at 60 seconds.
There are no retries. Failed observations retain verified inputs and notes.

Frozen relative/hash-bound inputs, outputs, worker/spec and source evidence make
the diagnostic auditable. Inspect-only prepares three input controls without
any installed process or cache access. Default ordinary execution, chemical
definitions, target mechanics, native kernels and NARestraints remain unchanged.
No dependency, cache migration or NAR release is needed. Actual Mac consumption,
whole-model links and exact pairing/stacking, the eight-pair full live run,
refinement and solution PDF remain separate; students do not approve CIFs.

Returned C72 verifies all 4,482 payloads, unchanged C71 parent, 160 runtime
members and the reported runner SHA (only NAR dirty-state metadata differs).
The source scanner captured 24 files, including the routing module that imports
`elbow.command_line.builder`, but does not traverse that non-ReadySet module.
The required observer target is absent, so the source guard stops before any
ReadySet or fixed native readback. Preserve the original failure receipt and its
false completion/preservation flags; independent replay verifies the four copied
5PC inputs and complete C71 lineage without changing those recorded flags.

C73 methods: retain the bounded literal-import scan and explicitly freeze each
named observer module that it does not discover. Enforce the same selected-root,
32-file, 1 MiB per-file, 8 MiB total and before/after hash checks. Add explicit
observer-root/source metadata without claiming transitive or native-internal
coverage. The actual captured 24-file layout plus 13 identical prior builder
snapshots reproduces a 25-file source inventory without executing captured code.
A generic indirect-import fixture now covers both no-builder and observed-builder
paths; missing, escaped, oversized and changed sources remain blocked.

Returned C73 verifies 4,830 payloads, the unchanged C72 parent and reported
runner SHA; only recorded NAR dirty-state metadata differs from the clean build.
Three Phenix 2.2.1-6174 ReadySet controls complete with all 25 source proofs,
exact cached effective numerics, unchanged heavy sites and requested effective
actions. Maintained replay reproduces all 24 checks: 21 true and three false
no-subprocess checks. Each untruncated trace records one Popen constructor call,
zero builder/template calls, and no command or caller. The child activity remains
unclassified; no fixed native readback runs. Preserve the original receipt's
generic native_execution label while reading its explicit zero native counter.

C74 methods: observe literal subprocess arguments, executable, shell and cwd
separately, with bounded caller source/function/line metadata. Do not capture the
environment or call conversion methods on opaque values. Preserve bytes as hex
metadata; mark truncated or unsupported parameters explicitly. Cap 64 arguments,
2,048 characters/bytes each, 8,192 total before encoding and 16 caller frames;
retain the 128-event cap. These are constructor-call observations, not a child
completion or exhaustive native-internals proof. No native function or argument
is replaced, and the existing no-child acceptance rule remains unchanged.

Returned C74 verifies all 5,304 payloads, the exact C73 parent, runtime inventory
and reported runner checksum. Each completed control preserves cached numerics
and heavy sites and records the same literal system_profiler hardware query.
The five nearest caller frames lead through libtbx machine-memory introspection
to scitbx neighbor-grid initialization. The remaining import frames are truncated,
but the trace/event/parameter budgets are complete. C74 captures no source for
these three caller modules; its v1 no-child review and zero native-readback count
remain unchanged. Current upstream CCTBX source supports the memory-query purpose,
but does not establish identity with this installed Phenix version.

C75 methods: capture libtbx easy_run/introspection and scitbx cubicle_neighbors
with the same selected-root, 32-file/1 MiB each/8 MiB total and before/after hash
guards. Parse those frozen bytes without executing them. Require the literal
system_profiler program/hardware argument and the native producer, process-wrapper,
memory-constructor and neighbor-grid call structure. Match all five observed
caller paths/functions and call-line spans against this source. Require the exact
recorded shell command and complete literal parameters; deeper import-frame
truncation is permitted only after the complete checked prefix.

V2 keeps the seven other consumption checks and replaces the blanket no-child
guard with no unclassified subprocesses. Preserve every raw event/count; record
known resource queries separately. Extra commands, different programs/arguments,
nonempty loader prefixes, changed callers/sources or incomplete evidence retain
review. Old v1 reports remain readable and retain their original verdicts. No
native function, ordinary argument, numerical dictionary or target changes.

The C75 retry preserves exact C74 and all prior evidence, reuses verified C71
inputs and performs the same three bounded controls. Only passing controls receive
the unchanged fixed native checks on the unchanged full-H seeds. No installation,
generation, optimization or student CIF approval is requested. Returned C75
verifies all 5,949 payloads and the exact C74 parent. All three Phenix 2.2.1-6174
controls pass their eight checks. Each retains zero builder/template calls and
one source-proved resource query with zero unclassified children. Fresh native
readback passes all 63 usability checks and six finite repeated evaluations with
matching consumer identity. The 28-source installed snapshots, classifier and
native qualification replay as data; no captured Python is executed. Original
C73/C74 reviews, nonconvergence and retained torsion/bending notes remain intact.

C76 methods: resolve current-source-bound resources from exact C75 and the full
constructed model/canonical reference from the verified C63/C64 lineage. Reuse
the existing source-qualified site modifiers at DP A:6, 5PC A:7 and PDU A:9.
Require a fixed native readback to pass the unchanged construction qualifier
against the saved canonical reference, with freshly matching dispatcher/version,
eight API and three energy-source fingerprints. No Coot or optimizer is rerun.

Merge only the three prepared base dictionaries for one ordinary whole-model
ReadySet call. The bundle wrapper requires matching declared source/numerical
components and their presence in the model; it uses the same arguments, observer,
resource-query proof and eight consumption checks. A passing result receives one
fixed native readback with unchanged site modifiers and explicit PHILs. Require
all backbone links, exact projected site definitions and every ordered named
proxy/parameter/origin/symmetry/multiplicity in all eight families to survive.
Only display padding in structured identities is normalized. Both fixed reads
retain the existing finite/repeatable energy/gradient checks; no derivative or
scientific geometry verdict is inferred.

Select the checked endpoint only after every gate passes; otherwise retain the
verified constructed start with notes. Unverified starts cannot be selected.
Inspect-only prepares portable inputs and reports NOT_ASSESSED. This is at most
one ReadySet call (180 seconds) and two native reads (60 seconds each), with no
retry, generation or model optimization requested. No cache key/entry, numerical
target, ordinary production behavior or NARestraints policy changes. Pair/stack
guessing stays disabled; the intended eight-pair/16-stacking live-model membership
and full-run qualification remain separate. No student CIF approval is required.

Returned C76: all 6,691 payloads, exact C75 parent, clean runtime inventory and
reported runner identity verify. Native mechanics pass (93 PASS, three unsupported
formal-charge readbacks), including all 38 links and 3,148 unaffected named terms.
ReadySet finishes with unchanged heavy sites and exact cached numerical bytes,
but three builder calls fail the unchanged consumption guard. The verified
constructed model remains selected; the endpoint native readback was not run.
Its original REVIEW and decision are preserved, rather than relabeled as a pass.

C77 methods: freeze each already-prepared DP/PDU/5PC dictionary independently and
require one parameterized component per file, exact declared coverage and a
byte-identical recombination to the original combined dictionary. Supply separate
repeatable CIF arguments to the same ordinary helper. Native actions, observer,
resource-query proof, all eight consumption checks, site modifiers and native
qualifiers stay unchanged. The captured input reader registers one returned mol.id
per file and skips objects without id; together with C75/C76 traces this supports
a combined-container registration mismatch. The native parser return type was
not independently probed. C77 stops during staging; returned C78 establishes the
separate-file route below. At C77 delivery, default production orchestration still
supplied the combined path; C79 changes that narrow handoff.

The v2 report separates intentionally excluded serialized outputs from required
portable files. A v1 reader recognizes only exact matching nested exclusion
metadata for absent opaque payloads; no pickle is loaded. Saved preparation replay
also allows the existing 1e-12 bound for duplicated derived determinant/eigenvalue
notes only. Scientific bytes, parameters, hashes and verdicts stay exact. These
are compatibility and argument-transport changes; cache identity and chemical
mechanics remain unchanged. The same verified-start fallback and bounds apply.

C77 consumer transport failure and C78 methods: the reported macOS trace stops
in `stage_review_members` before the native phase, then its exception handler
repeats the long-path lookup. No C77 ZIP was created. The verified C76 archive
has a 939-byte logical member path; Linux transport checks did not impose the
consumer limit. This is transport evidence, not a new chemistry verdict.

Explicit `cif-review-member-transport-v2` stages all accepted members at bounded
hash-derived object paths. Its checked index binds exact logical names, sizes
and SHA-256 values; readers and archive export preserve every original byte/name
and manifest without materializing the historical path. The cached-model action
uses this layout and a shallow prerequisite view selected through the declared
C29 lineage prefix (1,174 files, maximum relative path 281 bytes). The legacy
v1 layout/backup-name exception remains supported, and scientific references
retain their strict validation. No captured Python or opaque backup is executed.

Bulk preservation validation reads each indexed payload once. Incomplete staging
reports false. Failure reporting prints the original exception first and writes
an owned atomic receipt. If complete collection is unavailable, a reduced-scope
failure ZIP retains the receipt and verified input members directly from memory;
it explicitly excludes uncollected outputs and never claims incomplete staging
was preserved. A ZIP-writing failure leaves the receipt and secondary diagnostic.
C78 repeats C77 on exact C76, retaining the same chemical definitions, separate
CIF arguments, native checks and automatic verified-start fallback. At delivery,
fresh Mac qualification was pending; returned C78 is recorded below. Prior failed
directories and runs stay untouched.

Returned C78 closes the explicit whole-model cached-dictionary/ReadySet gate.
The verified 8,741-payload archive preserves the exact C76 parent and manifest.
Phenix 2.2.1-6174 completes one ReadySet control and two fixed native readbacks.
All eight consumption checks pass with no observed builder/template calls and
one source-verified memory query. Before and after each pass 93 checks with only
three unsupported formal-charge readbacks; all 28 roundtrip checks pass. Exact
cached numerics, heavy coordinates, 38 backbone links and 3,148 unaffected named
restraints survive. The automatic decision selects `readyset_checked_model` with
notes. This evidence qualifies the preserved construction control, not an eight-pair
solution or a diffraction experiment.

C79 ordinary handoff methods: after shared source/cache acquisition and existing
normalization, pass the ordered complete component-file tuple (or no input when
empty) to the existing ordinary ReadySet helper. Include cached, curated and
uncached fallback files; do not reselect sources or infer coverage by filenames.
Keep the combined dictionary for assessment/refinement and its existing
`readyset_dictionary_input` receipt reference. Add ordered checksum-bound
`readyset_dictionary_inputs` references and `per-component-files-v1` policy so
receipts identify the operational arguments. Source authority, cache keys,
normalization, generic numerical-generation checks, effective precedence, native
mechanics and NARestraints are unchanged. Local validation passes 139 focused / 4,408 full tests, including five
fail-before cases and source-removed cold ordinary-route checks; no new native cycle is required only to repeat C78's
qualified argument representation.

C80 provides the separate explicitly mapped eight-pair construction fixture.
It starts from the packaged `MR_frames/5W6W/C_G.pdb`, whose twenty disjoint pairs
come from seventeen literal secondary-structure declarations and the three-pair
central stretch. The eight requested replacements bind sixteen unique internal
sites; twelve modified sites require Coot parent overlap and four canonical
partners already have the requested identity. Full annotated chain sequences and
all source/declaration hashes are frozen. Existing free-five-prime preparation
removes ten declared terminal atoms in a separate input; the public source frame
is preserved. The prior DP:C construction control is not reused as pair intent.

| Requested pair | Exact components | First site | Second site |
| --- | --- | --- | --- |
| K:X | CGY:DX | A:20 | D:3 |
| D:T | 1AP:DT | A:5 | C:11 |
| Z:P | DZ:DP | A:12 | B:4 |
| B:S | IGU:IMC | A:6 | C:10 |
| PDU:A | PDU:DA | D:5 | A:18 |
| 5PC:G | 5PC:DG | A:4 | C:12 |
| 5CM:Q | 5CM:S6G | A:7 | C:9 |
| F:A | DF:DA | A:19 | D:4 |

Methods: freeze the fifteen ordinary selected requested-component sources plus
canonical DC for background roles, preserving ordinary authority and priority.
The exact source copies feed the ordinary `construct_postmr_model` entrypoint for
one Coot construction with a deadline of at most 600 seconds. Ordinary Coot
version and embedded-Python validation probes are recorded separately. First
check global atom composition, metadata, unchanged unselected coordinates and
internal-phosphate context. Ten graph-selected sites use the existing independent
connected-fragment or exact whole-raw-site auditor. S6G at C:9 and DF at A:19 use
exact replays of their existing curated placement rules, frozen-parent scaffolds
and declared substitution bond intent. Their existing parent occupancy/B transfer
is checked by exact replay; rigid preservation of raw curated fragments is not
claimed. A separate identity check covers all sixteen requested sites. Audited
whole-raw-site fallback retains notes, while a failed mixed fixture cannot select
its canonical template as though the requested chemistry were built.

The original C80 mixed-batch regression fixes an ordinary-path serial-authority
error: explicitly mutated curated sites join serial collision repair. That
delivery still excludes them from graph/OP3 context candidates; C81's separately
recorded extension below applies only after the existing source-graph proofs.
Frozen passthrough sites remain excluded and final placement/sanitizer mechanics
are unchanged.

The new explicit-site compiler uses the pinned NARestraints role table and pair
recipes on the actual constructed PDB. It preserves twelve canonical background
pairs and compiles all twenty pairs. It also emits one mapped parallelity for
each of the thirty-eight declared consecutive-chain relationships, following
NARestraints' existing chain-order policy. Chain adjacency is declared topology;
it is not evidence that a physical stack or covalent link has been observed.
All emitted selectors bind to actual PDB atoms and frozen source graph roles.
Request indices are explicitly `PDB_RECORD_ORDER`, not native capture indices.
Native secondary-structure guessing is disabled in the resulting PHIL.

The earlier sixteen stacking orientations are two plane-order compiler controls
per requested pair. C80 writes them as separate files and never concatenates both
orders into the active policy. They are not sixteen physical stacking edges;
including both orders would duplicate restraints. The requested eight pair
recipes emit 38 angle, 22 bond and eight pair-parallelity requests. Native proxy
membership and achieved geometry are still unassessed.

`80_Cedar_probe_mixed_pairs.py` carries an independent frozen runtime and public
frame; it accepts no historical review capsule and reads no donor observations.
Inspect-only mode freezes the plan/sources without Coot. Fresh mode records one
construction and its PDB-selector compiler evidence, not a fabricated MR result
or completed NASolve run. Relative checksum-bound artifacts support independent
readback; existing opaque Coot-backup transport and first-error/failure capsules
preserve diagnostics. ATL remains an independent public source-graph control.
The mixed-context, existing-context and construction regression passes 53 tests
in 2.05 seconds after the new case fails before the serial-authority fix. Combined
focused validation passes 154 tests in 30.71 seconds, followed by one additional
fixture integration test. The four new files contain 68 cases: twenty-one fixture,
thirty-one compiler, twelve delivery and four mixed-context cases. These groups
overlap and their counts are not additive.

Source-removed inspect-only validation passes with 162 frozen runtime members
and fifty capsule payloads, all subprocesses forbidden, a poisoned ambient import
path, aliased temporary directory and macOS path budgets. A standalone reader
passes after the source clones are removed. It uses fifteen exact ordinary C67
component sources and an explicit synthetic nonnative DC fixture; it establishes
transport and plan integrity, not chemical or native SDK qualification. The full
suite passes 4,475 tests, with two skips and 276 subtests, in 420.39 seconds. One
integration test added after collection passes separately in 1.99 seconds, with
no production-code change; these two runs cover all current test cases. Maintained
C76 and prior-lineage replay also pass with every subprocess forbidden and no
captured Python executed. These are the original local-delivery checks. Returned
Mac C80 completes Coot 1.3.3 and verifies all 138 capsule payloads, its frozen
runtime, source/preflight artifacts and all forty-two final site identities.
Maintained replay reproduces the original context receipt and all twelve
restoration-rule outcomes exactly without executing captured Python or a new
external process. The original REVIEW receipt remains unchanged.

The context transaction retains raw coordinates because curated DF A:19 has an
implausibly short raw incoming O3'-P distance in the proof shadow. Eight generic
sites therefore retain their whole raw site; only 5PC A:4 and IGU A:6 exercise
graph transport. Both curated placement rules complete, but DF retains OP3,
which has no frozen-parent counterpart. The independent scaffold guard correctly
stops here. Common DF scaffold coordinates and the entire S6G C:9 scaffold match
their frozen parents exactly. This is an unproved polymer context, not permission
to relax the guard. Constructed twenty-pair policy compilation does not run;
the separate source-only eight-pair/sixteen-orientation preflight does pass.

C81 extends the ordinary context eligibility check to explicit source-validated
curated DNA. Methods: run the same source-connectivity and discarded proper-frame
transport preflight used for supported DNA sites; build a discarded shadow with
only exact frozen-parent scaffold coordinates; let the existing phosphate
sanitizer prove selected internal OP3 removals. Transfer only those exact deletions
and independently authorized selected serial fields to the original raw records.
Retained raw coordinates and metadata stay exact. The unchanged graph transport
and explicit curated final placement rules then run, followed by the unchanged
final sanitizer recheck. Source graph, parent correspondence, inherited CONECT,
unselected identity/coordinates, frozen passthrough and phosphate-intent guards
remain active. A failed proof retains the complete raw context transaction.

The additive `curated_context` receipt uses
`postmr-source-graph-curated-phosphate-context-v1` and binds eligible/candidate
sites to exact source and parent hashes, scaffold atoms and discarded preflight.
It records context scope only; it does not turn curated final placements into
generic rigid-fragment transport. Generic-only and invalid-curated source
receipts keep their existing scope. No component-specific oxygen exception,
source dictionary edit, target change or native-mechanics change is introduced.

The C81 delivery uses the same builder and independent source runtime with
`--delivery-prefix 81_Cedar`, no historical review ZIP and one fresh Coot
construction. Exact saved-C80 replay is private local evidence, not a new public
replay API or fresh native result. Final combined focused validation passes 132
cases in 26.45 seconds, including eight new curated-context cases and seven new
receipt-binding cases. The source/parent/site/candidate/scope checks are independently
audited; tampered declarations are rejected. Original fail-before evidence is
preserved separately from overlapping focused totals.

Current maintained replay on exact saved-C80 bytes proves nine internal OP3
deletions and 267 selected serial repairs, with original sources, raw coordinates
and parent snapshots preserved. All ten graph transports and both existing curated
rules pass the independent mixed audit, with no whole-raw-site fallback. The same
phosphate auditor rechecks all nine final sites and changes no candidate bytes.
All twenty declared pairs, thirty-eight chain-adjacency stacks and sixteen separate
orientation controls compile and pass portable readback. This uses no captured
Python or new Coot/Phenix/ReadySet process and establishes no active native
membership. Source-removed cold replay passes on code checkpoint
`b568129b639aba400680b61b90378f7486f70d8c` using all sixteen exact C80 source
files, including captured background DC. Both build clones are removed before
launch; original repository/archive reads and subprocesses are forbidden, ambient
imports are poisoned, and an aliased temporary path passes macOS byte budgets.
The complete context/restoration/audit/compiler result reproduces, and standalone
policy readback passes after original scientific inputs, candidate and runtime
paths are removed. Everyday edits, configuration and component storage are
preserved. This uses no synthetic DC and provides no fresh SDK qualification.
Maintained C76 and all prior-lineage checks also pass under the current code,
with subprocesses forbidden and original reviews/fallbacks preserved. The full
suite passes 4,491 tests, two skips and 276 subtests in 424.25 seconds. All fifteen
new cases are collected before launch; no supplement is needed. These original
local checks remain separate from the subsequent Mac return.

Returned C81 verifies all 175 payloads and completes Coot 1.3.3. Independent
trusted-source replay reproduces nine OP3 deletions, 267 selected serial repairs,
ten graph transports and both curated rules, with no raw fallback. All forty-two
site identities and the twenty-pair/thirty-eight-stack policy match the declared
fixture; all sixteen plane-order controls remain separate from the active policy.
The final model matches the private saved-data prediction exactly. No ReadySet or
native interpretation ran in C81. Active native dictionary/link/triple-target and
pair/stack membership, ordinary end-to-end execution, observations/refinement,
solution PDF and scientific qualification remain separate. Students do not inspect
or approve CIF tables.

C82 connects that exact construction to the ordinary numerical handoff. Its
independent `build_mixed_native_probe.py` ferry reads the exact verified C81 ZIP
as data, preserves it through indexed transport and materializes a shallow
scientific view. It freezes the constructed model, all sixteen source components
and the active NARestraints PHIL without another Coot process. `--inspect-only`
stages and checks these inputs without discovering or running an external SDK.

Methods: call the existing ordinary ReadySet helper once with separate component
CIF arguments and its unchanged hydrogen/ligand actions. Preserve parameterized
input precedence through the ordinary effective-dictionary selector; source-only
CCD graphs may require native numerical generation. All sixteen still enter
ReadySet; omit only exact single-component, unparameterized canonical CCD graphs
from native dictionary arguments so the installed canonical numerical library
remains authoritative. Never rewrite a mixed container. Retain raw generated output
and per-component source comparisons, including chemical-state differences.
Compare actual native site definitions to the effective inputs; context mismatches
remain review findings, without a site-modifier or DNA-header repair in this slice.
Require unchanged named heavy coordinates and complete modified-component numerics
before at most two fixed native reads: secondary-structure guessing disabled,
then the same inputs plus the exact explicit NAR policy. Resolve that policy's
selections against fresh native atoms; compiler PDB-order indices are never reused.
The existing membership qualifier requires the exact added requests, every
unaffected proxy and no competing native secondary-structure terms. Separate
checks cover the declared backbone links, effective site inventory, finite
parameters/repeated evaluations and PDU/5PC triple targets. The sixteen separate
plane-order controls do not enter the active policy.

ReadySet has a maximum 600-second deadline; each fixed interpretation has at most
60 seconds. This test may generate dictionaries but requests no model optimization,
refinement or checkpoint. Chemical-source changes cannot be hidden by a native
membership pass, and the original constructed model remains available with notes
without a student CIF gate. Native internal operations are not exhaustively
instrumented. Final local validation on code checkpoint
`3aabb468ee668e12db3fa0ef2fd14448ad868f20` passes 188 focused tests and the complete
4,519-test suite (two skips, 276 subtests, 406.52 seconds), with all twenty-eight
new cases collected before launch. Source-removed cold preparation preserves all
sixteen actual C81 sources, the exact constructed model and declared policy;
all 175 parent payloads and its manifest survive, with no captured program
materialized into the scientific view. The prepared reader still passes after
original sources, fixture, session and runtime are removed. Configuration, everyday
edits and component storage remain untouched; simulated macOS path checks pass.
These original packaging/prepared-input and fake-tool checks use no local Phenix
or Coot. The subsequent C82 return and C83 recovery boundary are recorded below.
Returned C82 verifies all 364 payloads and the exact runtime, with ordinary
effective-authority replay matching the saved bytes. Its single Phenix 2.2.1-6174
ReadySet call completes in 65.95 seconds with unchanged named heavy coordinates.
The nested C81 manifest verifies all 175 parent payloads; the original C81 ZIP is
absent from this verification snapshot, so direct original-archive comparison is
not claimed. IGU alone fails numerical capability: its generated C2/N3 coordinates
coincide and the written C2–N3 target is 0.000 Å with 0.020 Å ESD. Source ideal,
source model and constructed distances are 1.327, 1.361 and 1.362 Å respectively.
Other generated IGU bonds stretch to 1.9–2.5 Å. The guard correctly prevents every
fixed native interpretation; the original REVIEW remains immutable. Phosphate
hydrogen/charge changes in generated definitions are separate source-state
findings. The saved evidence does not identify a specific native causal step or
prove a SMILES/seed defect.

C83 tests a separate source-preserving recovery for the saved numerically deficient
component set, currently IGU, through `audit_mixed_recovery` and its source-bundled
`build_mixed_recovery_probe.py` ferry. Read the exact C82 capsule as data, preserve
its full logical members through indexed transport, and use a temporary shallow
scientific view outside the new returned session. Explicit 128 MiB total and
32 MiB member limits accommodate the verified 52.9 MB parent and 20.8 MB receipt;
checksums, safe names and the exact input archive pin remain required.
Selection recomputes hard capability failures from the actual frozen numerical
rows, independent of residue code. Renamed-component, multiple-failure and valid-
bystander regressions protect the same general rule; at most four components
may enter a single bounded recovery. IGU is the observed case, with no exception.

Methods: freshly probe the selected installed Python-library anchor and capture
four complete-builder source modules as hash-bound text. This supplies new
installation evidence, not borrowed historical qualification. Reuse the existing
source-native complete-candidate adapter: the explicit source reader, declared
charge handoff and prepared-object CCTBX route feed the native complete builder
with original source ideal geometry. The source graph, names, charge, protonation
and stereo declarations remain authoritative. The default bounded block is 180
steps with at most 600 seconds per selected component. Retain regular written
outputs and stopping evidence across nonconvergence and worker failure. A usable
candidate is tested at source-seed and generated-output coordinates through the
existing isolated native qualifier, finite repeated evaluations, exact fixed
covalent-proxy comparison and automatic decision-with-notes. Each read has at most
60 seconds; secondary-structure guessing stays disabled. The resource-anchor
probe and generator help/version checks are separate from these fixed reads.

The mixed constructed model and all original dictionaries remain unchanged.
This slice requests no new Coot or ReadySet run, model optimization, linked/full
scaffold substitution, component-store publication, refinement or production
checkpoint. Isolated usability is not full NAR membership or scientific approval;
other C82 source-state reviews remain open. Local focused validation passes 242
tests in 28.86 seconds on code checkpoint
`6b941bcc37a6603ca24ecc3b4245eeeef8c3f7f0`. The frozen full suite passes
4,553 tests, two skips and 276 subtests in 520.98 seconds, including all thirty-four
new recovery/ferry cases. Earlier fail-before runs record eighteen recovery and
ten ferry failures on C82; those are distinct from the expanded final case set.
Source-removed cold preparation/readback passes with 163 frozen runtime members
and a 398-payload capsule preserving all 364 parent payloads exactly. All
subprocesses are forbidden; the standalone reader survives parent/session/runtime
removal.
Configuration, everyday edits and storage are preserved, with 52,410 simulated
macOS path operations bounded at 210 absolute/68 component bytes. These are
packaging and prepared-input checks; the subsequent fresh C83 result and C84
linked-mechanics boundary are recorded below.

Returned C83 verifies all 445 payloads, the exact 163-member runtime and the
complete C82 parent: all 364 payloads plus its manifest remain byte-identical.
Maintained trusted-source replay reproduces the source pins, prepared-object
worker, candidate and isolated decision without executing captured Python.
The Phenix 2.2.1-6174 source-native complete builder finishes in 20.95 seconds
with exit zero and stopping `NOT_REPORTED`. It preserves the neutral source's
37 atoms, 39 bonds, formal charges and finished source-relative sugar
configuration. The recovered C2–N3 target is 1.397 Å / 0.030 Å ESD; the original
zero target remains immutable in C82. Source-seed and generated-output native
reads each pass all twenty-one usability checks and two finite repeated fixed
energy/gradient evaluations, with the same covalent proxies and installed API
sources. Native formal-charge readback remains unsupported. NASolve selects
`source_native_generated` with `CONTINUE_WITH_NOTES`, without student CIF review.
This is isolated usability: the written group is still non-polymer despite native
DNA classification, and A:6 requires explicit source-qualified internal context.
Convergence, independent absolute CIP, other source-state findings and linked
mixed-model membership remain separate.

C84 tests that remaining linked mechanics boundary in a separate bundle. Select
recovered components from the verified isolated choices and actual model sites,
independently of residue name; IGU is the current observed case. Reuse existing
`prepare_linked_component` source-qualified DNA metadata and site-context
preparation. Replace only the selected component definitions in copied mixed
containers, preserving every unselected parsed row and unrelated resource byte.
The exact constructed coordinates, frozen plan and declared NARestraints
pairing/stacking policy remain unchanged. Only recovered-component metadata is
projected; unrelated non-polymer/ligand groups and the existing full-model DNA
classification gate are retained. Overall REVIEW may therefore coexist with
passing specific link/NAR checks. No general header or source-state repair is
claimed. An additive optional `site_projections` argument binds the existing
mixed native qualifier to exact declared site/component projections; calls
without it retain their original behavior. Retained parsed block text is exact
after the existing reader's newline normalization and trailing CR/LF separator
trimming; unselected parsed rows are exact.
Parent report/source hashes bind preserved findings without using derived
floating geometry as a content identity.

Methods: `audit_mixed_linked_recovery` reads the same prepared bundle twice at
fixed coordinates: the baseline disables declared NA additions, and the active
read uses the original NARestraints policy and declared contexts. Native
secondary-structure guessing stays disabled in both. Supported nonbranched
contexts follow frozen declared incoming/outgoing topology and exact terminal
inventory; ambiguous or branched contexts require a wider explicit adapter.
Require exact named native membership/link checks, finite fixed evaluations,
selected modifiers/heavy proxies and linked-phosphate neighbor/angle coverage.
Each interpretation has at most sixty seconds. The existing unsupported-formal-charge allowance is
retained without claiming native charge confirmation. Chemical-state findings
remain visible separately from mechanics. The ferry accepts the exact C83 ZIP,
explicit Phenix root, native deadline and inspect-only mode, with no generation/step flags. Parent transport
retains 128 MiB total / 32 MiB member limits and all original payloads; compact
report references avoid another large receipt copy. Keep the original model and
resources available with notes. This diagnostic requests no Coot, ReadySet, generation,
model optimization, component-store publication, production adoption,
refinement or diffraction input. Local focused validation passes 343 tests in
45.73 seconds across sixteen files on code checkpoint
`2ba5f388405196f550bd98cde7bf64c8ff45748c`. All forty-five new cases (thirty-two
module, thirteen ferry) are frozen before full-suite collection. The full suite
passes 4,598 tests, two skips and 276 subtests in 637.71 seconds, with no source,
script or test changes after the checkpoint and no post-collection supplement. Source-removed cold preparation and standalone readback pass with
164 frozen runtime members and a 543-payload capsule preserving all 445 C83
payloads plus its manifest exactly. The original sixteen sources, nine effective
dictionary files, model, plan and active/disabled policy remain intact. The IGU
internal A:6 projection has 34 atoms/22 heavy atoms, removes only `OP3`, `HOP3`
and `HO3'`, and retains `HOP2`. Source clones are absent and all subprocesses are forbidden.
Configuration, everyday edits and the component store remain unchanged; 88,707
simulated macOS path operations stay within 237 absolute/68 component bytes.
Standalone readback succeeds after parent/archive/session/runtime removal and
explicit retirement of owned temporary views. Private OS instrumentation
disturbed temporary cleanup, so guarded automatic cleanup is not qualified;
no product cleanup defect is inferred. These original prepared-input/fake-tool
checks are not SDK qualification; the actual C84 return and next replay boundary
are recorded below.

The original C84 report contract is
`cif-mixed-linked-component-recovery-v1`, stored in `mixed_linked_recovery.json`
under the `mixed_linked_recovery_directory` anchor. Its portable reader verifies
exact frozen selection, preparation, native input/specification/output and
qualification; a mechanics pass does not adopt the bundle.

Returned C84 verifies all 580 payloads, the exact 164-member runtime and the
complete C83 parent (445 payloads plus its manifest). Both Phenix 2.2.1-6174
fixed reads complete with exit zero in 4.35 and 1.52 seconds, each recording 863
atoms, forty-two sites and two fixed evaluations. The same prepared bundle
preserves the model and sixteen source files. All thirty-eight backbone links,
exact declared NARestraints additions, selected linked projections and active
PDU/5PC triple targets pass. Full membership still records REVIEW on four
baseline/active heavy-coverage and DNA-group gates. Actual native classification
is DNA at all forty-two sites, with no unexpected atoms. The recorded group fields retain six non-polymer
components and one ligand, and ten sites record only OP3 missing against their
effective definitions. Selected IGU A:6 has DNA group/classification and complete
heavy inventory. Keep those existing four verdicts unchanged pending separate
group/context coverage work. The automatic coordinate decision retains the
verified constructed model with notes; no bundle is adopted.

The subsequent report-reader exception is separate. Two UNSUPPORTED
formal-charge evidence lists contain identical complete rows for thirty-four
unique atoms each, but their order changes from the preparation dictionary's
insertion order to JSON's sorted keys. Sixty-six positional differences are
confined to those two `unavailable` lists; all other qualification fields and
verdicts match exactly. Formal-charge readback remains unsupported, with no new
contradiction. Preserve the failed receipt and original REVIEW; do not relax
coverage or DNA-classification gates to repair evidence ordering.

C85 makes that evidence deterministic and replays the saved native work. The
mixed-linked qualification writer orders atom-keyed formal-charge evidence
by atom ID. The shared `site_definition_checks` helper and its other legacy
consumers stay unchanged. A narrow legacy comparison accepts permutations only
in the named formal-charge `unavailable` and `contradictions` evidence lists,
with unique atom IDs and exact complete row types, values, statuses and every
other field/list order. This rule supports valid site identities, including
insertion codes, independently of residue code; it does not sort native proxies,
promote a verdict or make chemistry changes.

Methods: build the existing linked-recovery ferry with `--delivery-prefix
85_Cedar` and run `--saved-native-only` against the exact verified C84 archive.
Preserve the complete parent, including its failed receipt, through indexed
transport. The maintained reader verifies saved preparation, native inputs,
worker/specification/output bindings and qualification using a temporary shallow
view outside the returned session. Emit only a compact `saved_linked_recovery.json`
summary with hash-bound logical report/qualification references under
`preserved_review`; the probe receipt points to that summary under
`probe_directory`. The schema-1 policy is `cif-saved-mixed-linked-recovery-v1`.
Historical native calls remain two and new calls remain zero. No scientific
subtree is copied into the new result, and no new public replay API is added.

C85 requests no SDK discovery, native process, Coot, ReadySet, generation,
coordinate optimization, store write, adoption or refinement. It preserves the
C84 REVIEW and all four hard failures, without a PDU/5PC or broader state/header
fix. Final focused validation passes 395 tests in 26.83 seconds across sixteen
files on `919cd7a96f0609e76e91afaeacba1af24b5e66f6`. All thirty-eight new cases
(twenty module, eighteen ferry) are frozen before full-suite collection. The full
suite passes 4,636 tests, two skips and 276 subtests in 627.18 seconds, with no
source/script/test changes after the checkpoint or post-collection supplement. Independent actual-C84 replay preserves all 132 scientific files,
the original REVIEW and all four gates with zero processes. Source-removed cold
ferry/readback also passes with 164 runtime members and a 584-payload capsule
preserving all 580 C84 payloads plus its manifest exactly. Both historical native
captures remain exact; no SDK is discovered and no process starts. Configuration,
everyday edits and the store remain intact; 78,013 simulated macOS path operations
stay within 220 absolute/68 component bytes. Standalone readback passes after
parent/archive/session/runtime removal and explicit owned-view retirement; guarded
automatic temporary cleanup is not claimed. These original local checks are
preserved; the actual C85 return and source-bound context boundary are below.

Returned C85 verifies all 584 payloads and the exact 580-payload C84 parent plus
its manifest. Saved-summary and scientific-reader replay match exactly with zero
new native calls and two historical calls. All 132 scientific files, original
qualification hash, model and fallback decision remain unchanged. The same four
coverage/written-group gates retain REVIEW; source-state findings and scientific
qualification are not promoted. The saved replay path is now observed on the
user's Mac without SDK execution.

C86 tests only source-declared group metadata and incoming-phosphate context.
Selection follows the exact old native findings and frozen model topology,
independently of residue code: the current fixture selects eleven components,
ten incoming OP3 site modifications and seven group changes. Four canonical
components and the already-qualified IGU context remain unchanged. Require
explicit source DNA declarations and the original strict `source_graph_fragment`
for a complete unbridged deoxy sugar, one base at C1 and ordinary phosphate.
Bind the effective heavy atom names/elements, heavy-atom adjacency and relevant
phosphate endpoints, allowing only the already-recorded source OP3 omission.
These are context-eligibility checks; existing DF aromatic-sugar/six-delocalized-
phosphate findings and all other chemical-state reviews remain recorded.

The separate preparation changes only group metadata to source-declared DNA and
applies site-specific deletion of incoming OP3 plus hydrogens attached to that
atom. `_chem_comp.type`, outgoing O3′ hydrogen/energy type, surviving charges,
bond orders, stereo and all surviving numerical rows remain unchanged. No
whole-component OP3 deletion or broader source-state recipe is introduced.
Preserve all surviving parsed rows and bystanders, the exact constructed
coordinates, plan and original NARestraints policy.

Methods: `audit_mixed_context(linked_parent_directory, phenix, output, *,
timeout_seconds=60)` prepares a new result bound to the exact C84 native/effective
inputs retained inside C85. At most two fresh Phenix reads use the same prepared
bundle with declared NA additions disabled or the original active policy, keeping
native secondary-structure guessing disabled. Compare each new read with its
corresponding saved C84 read: all eight structured named-proxy families must be
exact, with exact structured atom inventories and energy proxy counts. Fixed
same-policy total/category targets and named gradients must satisfy the
established energy-repeat tolerance. These comparisons are at fixed coordinates;
nonbonded pair identities are not independently compared. Apply the existing
strict full qualifier, including backbone links, NAR additions, definitions,
group and coverage gates, without relaxation. Local SDK execution is unavailable;
actual Mac equivalence and mechanics remain unassessed until their native return.

The report is `mixed_context.json`, policy `cif-mixed-linked-context-v1`, under
`mixed_context_directory`. `read_mixed_context(directory, *,
linked_parent_directory)` requires its explicit hash-bound external parent anchor.
The ferry preserves the complete C85 parent once through indexed transport and
materializes only a temporary external C84 view; it does not copy the old 31 MB
scientific subtree into the new result. Status is `PREPARED_ONLY`, `REVIEW` or
`MIXED_CONTEXT_MECHANICS_PASS`. No Coot, ReadySet, generation, optimization, store
write, adoption, refinement or diffraction input is requested. Actual Mac C86
fixed-native checks remain pending; scientific qualification and ordinary
end-to-end solving remain separate.

Final local validation passes 413 focused tests in 31.60 seconds and 4,710 full
tests (two skips, 276 subtests) in 555.57 seconds on
`ffeb6e9f7d7c180985743baf64e99df94284d887`. All seventy-four final new cases
are frozen before full collection, with no later source/script/test changes or
supplement. Generic selection, source/adjacency binding, terminal preservation,
unchanged bystanders, exact row scope and anchored reader controls are covered.
Copied saved-native-record controls accept consistent reindexing/padding and
reject coordinate, target, canceling-category and count changes; these checks
provide no fresh SDK qualification.

Source-removed cold preparation/readback passes with 165 runtime members and a
643-payload capsule preserving all 584 C85 payloads plus its manifest exactly.
The new context data are 452,735 bytes, without a second old scientific subtree;
eleven selected components, seven group changes and ten OP3 site modifications
reproduce with canonical/IGU resources unchanged. SDK/native/other process calls
remain zero. Configuration, everyday edits and store fixtures survive; 112,812
simulated macOS path operations stay within 217 absolute/68 component bytes.
Standalone readback reconstructs its explicit parent from the copied new capsule
after original ZIP/session/runtime removal and explicit owned-view retirement;
guarded automatic temporary cleanup is not claimed. Prepared-input and fake-tool
QA remain separate from installed native execution. These original C86 local
checks are preserved; the subsequent return and C87 boundary are below.

Returned C86 stops at a native modifier grammar boundary before model
interpretation. Its first Phenix 2.2.1-6174 worker exits two while loading the
1AP OP3-only modification; the active read and full qualification do not run.
Biopython's `MMCIFIO` serializes a category containing one row as scalar items.
The native modification reader expects a loop table, so its conversion returns
no table object before `atom_list` access. This is a serialization failure;
it supplies no new verdict on the model's coordinates or restraint parameters.
All 697 payloads and the exact 584-payload C85 parent plus its manifest verify.
The context and parent readers reproduce exactly with zero verification
processes; all 110 context files and the fallback remain unchanged. All ten new
OP3-only modifiers have the same scalar shape. Original C86 local validation
remains unchanged, and the return supplies no new model/energy qualification.

C87 makes the modifier grammar independent of row count. Every nonempty
`_chem_mod_atom` category is written as an explicit `loop_` table, for both
single-row and multiple-row deletions. Keep the same MMCIF value formatter and
require one nonempty rectangular atom-modification category. Parsed rows and
modifier IDs are unchanged.
The shared `_emit`, previous linked preparation, native kernels, source selection,
chemical state and all strict mechanics/qualification gates stay unchanged.
Existing DF source-state findings and the verified fallback remain separate.

Methods: the context writer records `cif-mixed-linked-context-v2` in the existing
schema-1 `mixed_context.json`. The maintained reader accepts v1 and v2 and
regenerates each using its recorded policy. Legacy
`cif-mixed-linked-context-v1` retains its exact scalar serialization and original
failed report bytes; replaying it does not relabel the old attempt as successful.
V2 artifacts require the updated reader; legacy files are not migrated.
The public audit/reader signatures, `mixed_context_directory` local anchor and
required hash-bound `linked_parent_directory` anchor remain unchanged.

Build the existing `scripts/build_mixed_context_probe.py` with explicit
`--delivery-prefix 87_Cedar`; the builder default remains `86_Cedar` for
compatibility. The ferry verifies the exact failed C86 capsule as data through
the v1 reader, preserves every payload once with indexed transport, and prepares
a separate v2 retry. A temporary external C84 view avoids copying the old
scientific subtree. At most two fresh fixed native reads, sixty seconds each,
use the same disabled/original active NARestraints policy and existing native
secondary-structure settings. Require unchanged structured atom/proxy inventories,
fixed-coordinate total/category targets, named gradients and strict full
qualification. Nonbonded pair identities are not independently compared.
No Coot, ReadySet, generation, optimization, cache write, adoption, refinement
or scientific qualification is requested. Actual Mac C87 modifier parsing and
native context qualification remain pending.

Final local validation passes 451 focused tests in 32.33 seconds and 4,748 full
tests (two skips, 276 subtests) in 641.54 seconds on
`b8da8cb21b69087248ddcd9e4c5d0ff40b422ef1`. All thirty-eight final new cases
are frozen before full collection, with no later source/script/test changes or
supplement. Generic single/multiple-row grammar, token formatting, exact legacy
replay, input binding, failure preservation and strict unchanged mechanics are
covered. Initial fail-before subsets remain separate from the final case count.

Source-removed cold preparation/readback passes with 165 runtime members and a
756-payload capsule preserving all 697 C86 payloads plus its manifest exactly.
Its 452,195 bytes of new context data contain ten explicit one-row modifier loops;
base dictionaries, projected definitions, site PHIL, canonical/IGU resources and
the one no-op remain unchanged. No old scientific subtree is duplicated and no
SDK/native/other process starts. Configuration, everyday edits and store fixtures
survive; 141,546 simulated macOS path operations stay within 217 absolute/68
component bytes. Standalone legacy v1 and new v2 readers pass from the copied
new capsule after original ZIP/session/runtime removal and explicit owned-view
retirement; guarded automatic temporary cleanup is not claimed. These are local
grammar/preparation/replay checks, not fresh installed native qualification. These
original local checks remain preserved; the actual C87 return is below.

Returned C87 completes both Phenix 2.2.1-6174 reads with
`MIXED_CONTEXT_MECHANICS_PASS`. All 865 payloads and the complete 697-payload C86
parent plus its manifest verify. The workers exit zero in 3.962889 / 1.460846
seconds, each with 863 atoms, forty-two complete DNA sites and two fixed energy
snapshots. All thirty-four membership checks and all twenty saved-parent
equivalence checks on each side pass. The qualification contains 291 PASS and
24 unsupported formal-charge checks, with no contradiction. Source-state
findings and scientific qualification remain separate; no optimization,
refinement or adoption occurs.

The envelope fails later on check-row order: site-projection insertion order
changes when JSON sorts map keys, moving 132 positions among 315 unique complete
check rows. Every row matches recursively by full check ID, including value
types and nested list order; every other qualification field and the PASS verdict
are identical. Preserve the failed receipt and original report/qualification
bytes. The native-mechanics PASS precedes this replay error. Original C87 local
validation remains unchanged, with the actual return recorded separately.

C88 deterministically orders only the context qualification's top-level check
rows by unique complete ID. The legacy reader accepts a row permutation only
with exactly the same unique IDs, complete typed rows, statuses and other fields.
Nested order remains exact under the existing unchanged C85 atom-keyed formal-
charge evidence rule; C88 adds no nested-list allowance. Duplicate or missing IDs
and changed values/statuses remain rejected; no verdict is promoted. Shared C85 comparison,
other qualification helpers, context policies v1/v2, source chemistry, native
kernels and all scientific gates remain unchanged.

Methods: build the existing `scripts/build_mixed_context_probe.py` with explicit
`--delivery-prefix 88_Cedar` and run `--saved-native-only` on the exact C87
capsule. Builder default 86 remains compatible. The maintained reader reconstructs
temporary external context/linked-parent views and verifies the saved native
inputs, captures, preparation and qualification without SDK discovery or a native
process. Preserve every parent payload once through indexed transport; do not
copy another scientific subtree. Emit only `saved_mixed_context.json`, schema 1,
policy `cif-saved-mixed-context-v1`, with hash-bound logical report/qualification
references under `parent_review`. The receipt references this compact summary
under `probe_directory`; original scientific files remain byte-exact.

The saved summary retains `MIXED_CONTEXT_MECHANICS_PASS`, two historical and zero
new native calls, and the original `CONTINUE_WITH_NOTES` coordinate decision with
`native_usable: true`. Students do not approve CIF tables. Scientific qualification,
source-state findings, formal-charge API limits, ordinary full-run integration
and production adoption remain separate. No Coot, ReadySet, generation,
optimization, store write, refinement or new native qualification is requested.
The actual Mac C88 saved replay is verified below; it requests no new native
qualification.

Final local validation passes 512 focused tests in 25.61 seconds and 4,809 full
tests (two skips, 276 subtests) in 599.28 seconds on
`aaed1955b166c507ba94be8157bf1bc89c69fd6e`. All sixty-one final new cases are
frozen before full collection, with no later source/script/test changes or
supplement. Generic unique-ID order, complete typed rows, missing/duplicate IDs,
nested order, statuses, legacy replay, input binding and failure preservation
are covered. Initial fail-before subsets remain separate from final case counts.

Source-removed cold saved replay passes with 165 runtime members and an
869-payload capsule preserving all 865 C87 payloads plus its manifest exactly.
Its compact summary is 1,088 bytes, with no duplicated scientific subtree.
All 297 scientific/context/parent files remain exact; 315 checks reproduce the
original 291 PASS / 24 unsupported-formal-charge result and mechanics PASS.
SDK discovery, context audit and process calls are forbidden. Configuration,
everyday edits and store fixtures survive; 119,864 simulated macOS path operations
stay within 217 absolute/68 component bytes. The standalone reader reconstructs
its explicit parent from the copied new capsule after original ZIP/session/
runtime removal and explicit owned-view retirement; guarded automatic temporary
cleanup is not claimed. Shared C85 readers remain byte-exact. This validates
saved evidence and packaging, with zero new native qualification.

Returned C88 verifies all 869 payloads plus the outer manifest, including all
866 original C87 members byte-exact. The archive has 870 entries and 121,527,577
uncompressed bytes. Its 1,088-byte summary reproduces exactly, retaining all 315
checks (291 PASS / 24 unsupported formal-charge readbacks), all 297 scientific
context/parent files and the original mechanics PASS. The saved native-call count
is two; new native calls are zero. The maintained explicit-parent reader preserves
`CONTINUE_WITH_NOTES`, native usability and the original failed C87 envelope.
No scientific verdict or student CIF approval is added.

### Fresh initial-only gradients of the exact mixed manager (C89)

The exact mixed manager has 863 atoms, forty-two sites and fifty-eight parallelity
restraints. Earlier geometry/plane qualifications belong to a different
877-atom/forty-three-site manager and cannot be relabeled as proof for this model.
C89 therefore supplies one fresh initial-only audit before a geometry trial;
it does not invent historical endpoints or optimize coordinates.

Methods: verify the exact C88 capsule and its explicit context/linked-parent
anchors, then rebuild and match the saved active C87 manager. Captured programs remain
data and are never imported or executed. Bind the fresh job's native API/source
pins and unchanged correction core before applying the existing
`native-parallelity-both-first-planes-v1` correction with unchanged native energy
and fixed chemical definitions and NARestraints pairing/stacking policy. Use the
existing fixed evaluator, finite-difference category/global gradient audit and
per-plane order audit on all fifty-eight actual restraints, with six fresh
tilted/rotated controls. The single coordinate case is the saved initial state.
Selection of sampled atoms follows numerical/outlier evidence rather than a
component-name exception. Bind the trusted worker, correction core, inputs and
saved numerical evidence in `mixed_initial_gradients.json`, policy
`cif-mixed-initial-native-gradient-v1`; its reader recomputes qualification from
the saved records. Keep external parent references explicit and preserve the
complete parent once through indexed transport, without another scientific-tree
copy or a larger archive bound.

The new `scripts/build_mixed_gradient_probe.py` creates
`89_Cedar_probe_mixed_initial_gradients.py`; `--inspect-only` prepares inputs
without SDK execution, while the fresh audit uses one native worker bounded at
600 seconds. With six sampled atoms, the expected algorithm uses 1,367 whole-
energy evaluations within a 2,000 maximum and 3,328 plane/control evaluation
pairs within a 5,000 maximum; the actual Mac counts and qualification are verified below.
No Coot, ReadySet, dictionary generation, optimizer, store publication, production
adoption, refinement or diffraction run is added. A failed derivative check
retains usable input and notes for the next bounded step; students do not approve
CIF tables. Local focused validation passes 600 tests across twenty-two files
in 83.01 seconds on `cad81fb394433767d270577cfbc923792672c01f`; all 106 final
new cases (61 module / 45 ferry) are frozen before full collection. Initial
fail-before subsets contain four module and four ferry cases, separate from the
final case count. Actual-parent inspect prepares 455,931 bytes and 3,328 plane
pairs with zero SDK calls and all 297 parent scientific files exact. The complete
suite passes 4,915 tests, two skips and 276 subtests in 694.66 seconds at that
checkpoint. No source, script, test or figure changes follow full collection and
there is no later test supplement. Actual Mac C89 derivative qualification passes
as recorded below; source-state findings and scientific qualification remain separate.

Source-removed cold inspect passes at the same checkpoint with 166 runtime members.
The 918-payload capsule preserves every C88 payload and its manifest byte-exact
once, totaling 122,235,229 uncompressed bytes; the largest member is 20,829,148
bytes. Its 484,997 bytes of new data leave 11,982,499 bytes below the unchanged
128 MiB limit. The standalone explicitly anchored reader passes after the owned
source clones, original input copy, session and runtime are removed; all 165
context, 132 linked-parent and 46 new files remain exact. Inspect stays
`PREPARED_ONLY` with zero SDK/discovery/subprocess/captured-code calls. Configuration,
everyday edits and store fixtures remain intact; 164,380 guarded path operations
stay within 232 absolute/68 component bytes. Temporary views are explicitly
retired; guarded automatic cleanup is not claimed. This is preparation/portability
evidence, not a fresh installed derivative result.

Returned C89 passes the fresh installed audit in one Phenix 2.2.1-6174 job
(24.122224 seconds, exit zero). The exact 863-atom/forty-two-site manager matches
the saved inputs. All eight sampled gradient families, repeats, target/gradient
additivity and the captured snapshot pass in 1,367 of 2,000 energy evaluations.
All fifty-eight actual planes pass in both orders, together with six tilted/
rotated controls and three rotation checks, in 3,328 of 5,000 evaluation pairs.
The original native complete-gradient controls retain twelve actual and six toy
review orders; the order-safe correction has none. This verifies the correction
rather than changing targets: native energy remains 27,518.185419949943, with
coordinates, source definitions, source pins and static constraints unchanged.
All 937 payloads and the exact C88 parent verify. The maintained reader replays
qualification with zero new SDK processes; captured programs remain data. These
are sampled numerical results, not convergence, source-state repair or scientific
qualification. Original C89 local validation remains unchanged.

### Bounded geometry from the qualified mixed manager (C90)

C90 supplies one optional geometry-only trial from the exact C89 initial state.
The existing geometry worker, native corrected evaluator, optimizer settings and
atom-identity serializer remain unchanged. A separate precondition adapter verifies
the genuine C89 initial-only proof, source fingerprints, static constraints and
corrected initial target/gradient before optimization; it does not relabel an old
three-coordinate-case qualification. Chemical definitions, weights and the
NARestraints pairing/stacking policy remain fixed, with native secondary-structure
guessing disabled.

Methods: bind C89 through explicit gradient/context/linked-parent anchors; stage
trusted current Git sources and a fresh optimizer history; run one trial bounded
at 1,000 iterations and 600 seconds, with at most 20,000 optimizer calls and the
existing 1e-5 convergence tolerance. Check full-precision and PDB-rounded endpoint
derivatives, serialize by exact atom identity, then interpret the separate PDB
with the same dictionary/PHIL bundle and exact fixed-policy proxy checks. Select
a usable endpoint only when its fixed objective does not worsen and its mechanics
and derivative evidence qualify.
Retain the verified usable initial model automatically when the optional phase
cannot qualify an endpoint. Usable nonconvergence, iteration limits and descriptive
pucker/chirality findings become notes, with no student CIF inspection or approval.
Fixed definitions and mechanically unusable evidence remain strict.

The report is `mixed_geometry_trial.json`, schema 1, policy
`cif-mixed-qualified-geometry-trial-v1`. The builder
`scripts/build_mixed_geometry_probe.py` creates `90_Cedar_probe_mixed_geometry.py`.
`--inspect-only` prepares the trial without SDK execution; a complete diagnostic
allows at most two SDK jobs including native candidate readback, bounded at the
smaller of the requested timeout and sixty seconds. Preserve the
original C89 ZIP byte-exact once as opaque `inputs/parent_review.zip`, rather than
flattening its 128,249,071-byte ancestry again. The exact 10,963,258-byte parent
archive and all its payloads remain available. Only three declared scientific
views are materialized temporarily; captured programs are never executed. The
128 MiB total, 32 MiB member and 1,024-entry outer limits stay unchanged.

Focused local validation passes 917 tests across thirty files in 149.00 seconds
on `f759d4c9561d0af1a82d5f9336eb1fa8496f2fb4`. All 116 final new cases (64
module / 52 ferry) are frozen before complete-suite collection. The original
four-case fail-before subsets remain distinct from final counts. The real C89
prepared trial and maintained reader pass with zero SDK processes, 53 prepared
files and 7,256,286 bytes. The genuine 863-atom precondition adapter passes and
rejects a tampered proof without SDK execution. The complete suite passes 5,031
tests, two skips and 276 subtests in 718.58 seconds at the same frozen checkpoint.
No source, script, test or figure changes follow full collection, and there is no
later test supplement.

Source-removed inspect and standalone readback also pass after removing the
original session, runtime and input archive, with zero SDK/subprocess launches.
The portable runtime has 167 members; the new outer archive has 57 payloads plus
its manifest and 18,257,745 uncompressed bytes. Its largest member is the exact
10,963,258-byte original C89 ZIP, preserved once with all 937 payloads and its
original manifest. New data occupies 7,285,687 bytes, leaving 115,959,983 bytes
under the unchanged 128 MiB limit without duplicating the old scientific tree.
The standalone reader reproduces all 65 gradient, 165 context, 132 parent and 54
new files unchanged. The path guard checks 125,071 operations, with maximum path
and component lengths of 232 and 45 bytes. Authorized edits, user configuration,
the component store and ambient import isolation remain intact. Owned temporary
views are explicitly retired; guarded automatic cleanup is not claimed.

Actual Mac C90 geometry remains pending. No Coot, ReadySet, dictionary generation,
cache publication, production adoption, refinement or ordinary diffraction solve
is added. Source-state findings and scientific qualification remain separate
from optional coordinate usability.













Methods: compare all seven inventoried named chemical fields and the repair
recipe/backend; reassess completed source-relative configuration; require
current isolated native qualification; publish a new entry bound to the selected
raw source/authority while crediting the original numerical producer. Keep the
old entry immutable and freeze both provenance records with relative hashes.
A failed or mutating adapter receives disposable inputs and excludes only that
candidate. A changed consumer requalifies saved bytes first. Optional cache-write
failure retains a qualified run copy. An unparameterized fallback source still
requires ordinary preparation; it is not a native-usability verdict.

Local integration uses actual returned source bytes and saved native data:
all 63 checks pass and six qualified/reused results survive source/cache removal
and relocation, with external scientific reads forbidden. This does not claim
fresh Phenix execution. C68 stops before launch; C69 corrects that layout and
completes all three native reads. C70 replays their exact inputs, worker/specs,
outputs and consumer bindings, recomputes the unchanged usability checks and
finishes the source-bound store/repeat stage. Owned source-layout replay uses
the captured C69 bytes/authority, not a new live installation selection. Separate
dictionary/native triple reports preserve torsion and seed-bending findings.
No captured Python or new native process is executed.
Native guessing stays disabled. Native energy resource files are not inventoried;
current linked/model qualification and production PostMR adoption remain open.

## Generated numerical defects and explicit candidates

The assessor's `cif-doctor-graph-numerics-v2` policy checks exact coincident
bonded heavy atoms in numerical dictionary coordinates. Invalid bond-target
findings include the atom pair. Raw graph sources, absent coordinates and
unsupported representations stay separately unassessed; achieved model
geometry is still NOT_RUN. The new coordinate inventory/verdict is additive
within assessment receipt schema 1.

PostMR's existing generic numerical gate now writes an exclusive
`PostMR/ReadySet/cif_doctor_generation_failure.json` when generated targets are
missing, invalid or have coincident bonded heavy atoms. It reports the actual
component, atom references and reason rather than treating every failure as a
missing dictionary. Curated or explicitly numerical inputs retain their
existing authority over rewritten ReadySet rows. The complete failed component
is quarantined; no individual distance is filled in.

To generate an explicit, independent whole-component candidate:

```bash
./nasolve --phenix-root /path/to/phenix cif-doctor generate-candidate source.cif \
  --code ABC --output-parent /path/to/candidates --timeout-seconds 600 --json
```

This operation alone requires optional `phenix.elbow`, resolved beside the
selected installation's Phaser dispatcher. It preserves the user's saved
configuration/workspace and passes a cleaned native environment copy.
Generation uses the frozen chemical CIF and a naming/initial-geometry PDB
derived only from complete source ideal coordinates and integer formal charges.
The explicit template supports component IDs of up to three characters and
atom names of up to four ASCII characters; missing or unrepresentable data are
reported, never inferred from the fitted model. The generation-v4 adapter first
records a bounded `phenix.elbow --help` check from that exact executable. It
selects supported option spellings and verifies that each required option takes
a value or is a switch as appropriate. Initial geometry and hydrogen controls
may use dashed or underscored aliases; no required control is silently omitted.
Unsupported or failed help checks stop before chemistry with
`UNSUPPORTED_GENERATOR`. Help logs, hashes, selected aliases and executable
identity remain in the receipt. eLBOW then receives explicit optimization,
hydrogen addition disabled, retained chirality and the independent template.
The required valued `--pH` control is set to `low`, the installed generator's
input-chemistry retention mode. This requests preservation of the source state; it
does not assert experimental pH or establish the correct crystal protonation.
Hydrogen addition disabled alone does not prevent eLBOW from removing existing
acid hydrogens. Atom, bond, hydrogen, charge and declared-stereo comparisons
still reject changed chemistry even when the generator exits successfully.
The requested `--opt` option and any backend named in the native log are
separate evidence; the returned Phenix 2.2.1-6174 run used RM1/GDIIS.
The original CIF, failed ReadySet output and prior numerical resources are
never overwritten or used as a source of invented numerical targets.

Generation-v4 also recognizes a bounded bond representation change: an entire
isolated six-member C/N ring can change from alternating single/double orders
to aromatic bond types only when every source ring bond is explicitly aromatic.
Ring atoms must have unchanged elements and explicit zero formal charges;
ring bonds must have no explicit stereochemical declaration beyond `N`.
Every substituent edge must remain a single graph bridge, excluding fused/spiro
rings, chords and exocyclic multiple bonds. Missing/conflicting aromatic flags,
partial conversions, other ring sizes and all unresolved order changes remain
rejected. This checks supplied declarations without inferring aromaticity,
resonance, valence, protonation or tautomer equivalence. Source and candidate
files and numerical targets remain untouched.

Schema-1 `cif_component_generation_inspection` and
`cif_numerical_generation_candidate` receipts record source/candidate
assessments, chemical differences, exact numerical issues, generator command,
version, timeout, output hashes and preservation checks. Exit 0 means
`CANDIDATE_REVIEW`, not chemical approval; rejected/failed candidates exit 2.
Complete numerical candidates may retain soft plane/torsion REVIEW findings;
missing targets, invalid numerics and unresolved plane compatibility remain
rejected. These findings are preserved rather than relabeled as numerical PASS.
The generator does not retry ReadySet, edit a model, adapt polymer links or
adopt a dictionary. Native reader/geometry/proxy verification and any actual
linked-site chemistry remain separate qualification steps.
Inspection receipts add `bond_representation` under
`cif-source-declared-six-member-aromatic-v1`, retaining every raw `bond_orders`
and aromatic-metadata difference in the existing comparison. Representation
evidence does not override independent atom, hydrogen, charge, stereo or
numerical failures. New builds of the native shuttle recognize source-retaining v3/v4
receipts, verify all source/output hashes and re-inspect current dictionaries;
unknown generator policies remain unsupported.

The source-bundled `04_Cedar_probe_cif_generation.py` inspects an existing failed run,
selects invalid non-curated generic components by findings, and invokes this
same candidate API. Its summary distinguishes failed/rejected generation from
an actual candidate awaiting review. It writes a review ZIP into a fresh external session while
preserving the original run. `--inspect-only` skips native generation.
Its delivery prefix appears first in the script/session/review-ZIP name and is
printed with the policy ID. The ZIP additionally includes the session's unique
token near the beginning. Schema-1 metadata and probe receipts retain the same
prefix. Developers can set `--delivery-prefix` when building another delivery;
explicit output paths remain honored. Older runs and shuttles remain readable.

The [optimized native evidence](elbow-optimized-state-evidence.json) records
the restored IGU C2–N3 target (1.387 Å) and the separate rejection for deleted
phosphate hydrogens and altered formal charges. A native retry with explicit
source-state retention was pending at that point; that evidence does not authorize
candidate adoption or a full-auto campaign restart. The subsequent
[source-retention evidence](elbow-source-retention-evidence.json) records a
successful v3 retention attempt with all 37 atoms and unchanged formal charges.
That candidate remains REVIEW pending metadata/native-reader/link qualification.

## Explicit native bundle diagnostic

`05_Cedar_probe_cif_native.py` is a separate diagnostic shuttle. Its default
case uses the returned Cedar 04 generation receipt and the original failed
synthetic run. It rechecks the current candidate, binds its frozen chemistry
to the source audit, and verifies the prepared PDB plus every recorded runtime
CIF/PHIL/EFF. The generation probe also binds the source audit and failed
ReadySet baseline; caller-selected exact paths are checked against those
hashes rather than resolved through historical absolute paths.

The shuttle copies inputs into a fresh external directory, replaces only the
candidate component in that diagnostic input list, and applies the ordinary
parameterized-input precedence and supported torsion normalizer. All recorded
ancillary parameters and reviewed site-modification files are retained.
It does not add generic site modifications or change DNA metadata/protonation.
`--inspect-only` performs this preparation offline without discovering Phenix.
Explicit `--run`, `--candidate-directory`, `--generation-probe`, `--phenix-root`
and `--output-parent` overrides retain their declared checksum boundaries.

Native execution requires optional `phenix.python` beside the selected
installation's Phaser dispatcher. The standalone worker uses installed
iotbx/libtbx/mmtbx readers and monomer/energy libraries. It records effective
monomer metadata, missing-atom mappings where supported, interpreted atom
identities/coordinates, simple/ASU bond endpoints and geometry proxy counts.
Original and copied input bytes are rechecked after execution. Native hierarchy
normalization is recorded separately from preservation of the original model.

The opt-in `refinement-root-to-interpreter-v1` PHIL namespace policy uses the
native parser to remove only a top-level `refinement` wrapper, retaining all
child definitions, value tokens and selections. Canonical derivatives and field
maps are preserved, and unused parameters stop as explicit unsupported evidence.
Geometry edits/removals and scoped CIF modifications use the corresponding
native consumers; no parameter is silently discarded to obtain a clean run.

Schema-1 `cif_native_bundle_inspection` receipts use policy
`cif-native-bundle-inventory-v1`. Successful interpretation returns **REVIEW**,
with native failures, unavailable APIs/fields and missing coverage visible.
Inventory does not certify intended links, custom-restraint coverage, achieved
geometry or scientific validity. The helper runs no optimization, ReadySet,
refinement, candidate adoption or checkpoint selection. A prefixed review ZIP
contains exact diagnostic inputs, canonical parameters, raw logs and receipts;
embedded source runtime and native pickles are excluded. The returned Cedar 05
inventory completed on Phenix 2.2.1-6174: 42 mappings, 38 internal O3′–P links,
zero coordinate OP3/O3P, and four isolated-monomer OP3 expectations. REVIEW
is the worker's successful inventory status; see the [native ledger](native-modified-pair-live-validation.md#cedar-05-return-and-source-state-audit).

## Source-preserving linked-state diagnostic

`06_Cedar_probe_cif_linked.py` takes the exact checksum-bound returned 05 ZIP,
verifies its 57 payloads and writes a fresh external session. It reuses CIF
Doctor's source/candidate comparison and existing eLBOW candidate API before
link adaptation. The selected CGY/IMC/DX ReadySet definitions lost their
source OP2-bound hydrogens; source-preserving whole-component regeneration is
therefore required. The accepted 04 IGU candidate can be reused. Failed or
chemically changed candidates remain separate review evidence, with no
hydrogen insertion or invented numerical targets.

The explicit `cif-source-preserving-linked-sites-v1` preparation API requires
source `DNA LINKING` metadata, a complete source-preserving numerical candidate,
and declared incoming/outgoing and terminal contexts for every same-code model
site. It writes a DNA metadata derivative, graph-selected atom-deletion/O3′-OC2
modifiers, exact site selections, projected dictionaries and assessments.
Incoming and outgoing treatment are independent. Source-specific OP2 H and
formal charge declarations survive; free 5′-OH and explicitly requested
terminal phosphate states remain distinct. Unsupported symmetry, alternate
conformers, insertion codes and experimental backbones stop for review.
Raw source dictionaries and coordinate models remain unchanged.

Native `inventory_detail="linked"` is opt-in and additive to the existing
inventory API. It records effective atom/energy/charge/graph definitions and
individual proxy targets/weights, and resolves explicit geometry edits through
the installed native selector. Qualification checks all 38 declared links,
exact custom proxy coverage, retained pair/stacking parallelities, unchanged
model coordinates/identities and other-component definitions, plus absent
leaving atoms and dangling references. A separate 43-residue control adds a
free-OH IGU while retaining internal IGU under the same component code.

`LINKED_MECHANICS_PASS` describes these checks only. Existing 5CM torsion,
angle/plane and generated stereochemical metadata reviews remain visible;
achieved geometry and experimental protonation remain unqualified. The shuttle
runs no ReadySet retry, diffraction refinement, checkpoint selection or
dictionary adoption. The returned Cedar 06 capsule completed IMC/CGY/DX eLBOW
generation and stopped at `SOURCE_RECOVERY_REVIEW`: only CGY's ring-bond
representation blocked the generation gate. Native bundle interpretation and
the shared-code control did not run. The [source-recovery evidence](cif-linked-source-recovery-evidence.json)
records its 87 verified payloads, exact source/candidate hashes and offline
reanalysis. With generation-v4, all four returned candidates prepare linked
derivatives offline, retaining their OP2 hydrogens. The subsequent delivery used
`--delivery-prefix 07_Cedar` with `scripts/build_cif_linked_probe.py`.
The Cedar 07 return is recorded below; offline tests and fake
native APIs do not establish an installed Phenix pass. Failed source recovery
now prints the component, generation status and recorded rejection reasons.
The older native API defaults and receipts stay compatible.

The returned Cedar 07 capsule passed source recovery and baseline interpretation
(858 atoms, 42 mappings and 38 backbone links), then failed linked interpretation
because the modifier writer used a shared `data_mod_linked_sites` block. The
native reader registered `linked_sites` four times while PHIL requested four
distinct `NASL...` IDs. Preparation now emits one `data_mod_<ID>` block per
requested modifier, including mixed contexts for one component code. Atom-loop
IDs, PHIL requests, base dictionaries, deletions and projected site chemistry
stay identical. Schema-1 preparation adds
`modification_block_policy = cif-native-modification-blocks-v1`.
The [native-registration evidence](cif-linked-native-registration-evidence.json)
records the 164 verified payloads, reader contract and exact offline replay.

The baseline's detailed native atom records also expose no formal-charge values.
The detailed worker records missing attributes separately from null values.
Qualification labels unavailable formal-charge readback `UNSUPPORTED`, preserves
actual charge contradictions as `REVIEW`, and never substitutes partial charges
or a presumed zero. Other site/proxy checks continue; a complete mechanics pass
still requires all checks. Native failures print the relevant baseline/linked
error alongside the preserved receipt.

Cedar 08 completed baseline, linked and shared-code native interpretation on
Phenix 2.2.1-6174. All four effective atom sets, H adjacency and energy types
agree, with 38 preserved backbone links, exact custom proxy coverage and
unchanged original coordinates/other definitions. Complete qualification stays
REVIEW: the installed atom API lacks formal-charge attributes, and scalar
`comp_list` metadata is skipped by the reader, leaving the native group null.
Native logs classify all 42 residues as DNA; classification and group are
separate fields. The original atom check also required DNA group and therefore
reported REVIEW despite matching atom sets.

Preparation now retains the singleton `_chem_comp` row as a loop in base and
projected dictionaries, with schema-1 `component_list_policy =
cif-native-component-list-loop-v1`. Parsed metadata and every atom/restraint
value remain the same, as do modifier/PHIL bytes and site plans. Detailed
metadata adds native `classification`; qualification separates exact atoms
from required DNA group without relaxing either check.

The returned Cedar 09 installed execution recovers DNA group and classification
at all four internal sites. All **29** evaluable qualification checks pass;
the four formal-charge checks are **UNSUPPORTED** because the installed native
atom API lacks that attribute. The aggregate remains REVIEW. Read-only file
comparison confirms 148 unchanged source/candidate formal charges; ordered
signed-volume comparison agrees at all 12 sugar centres against source ideal
coordinates and native proxy order. These are separate evidence, not native
charge readback or independent absolute stereochemistry.

The shared-code control preserves all original atoms, definitions and links;
E:1 has group DNA and classification undetermined. Its O5′ retains source O2
typing with no attached explicit H, so the demonstrated scope is atom/context
isolation, not complete terminal-OH chemistry. The 12 soft plane-angle findings,
omitted generator metadata and retained 5CM C2/C2′ torsion remain visible.
The next phase is explicit dictionary/end-state and geometry review. No runtime
gate was changed to make the returned result pass, and repeating an unchanged
inventory will not resolve unavailable native formal-charge readback.

## Explicit terminal numerical-source review

`scripts/build_cif_terminal_probe.py` builds a source-bundled terminal review
with the existing pinned NARestraints source. The completed Cedar 11 delivery uses
`--delivery-prefix 11_Cedar --output PATH/11_Cedar_probe_cif_terminal_review.py`;
the builder retains its original `10_Cedar` default for compatibility.
The runner reads the exact
returned Cedar 09 review ZIP, verifies its 207 payloads and snapshots the
explicitly declared 5CM source. The existing source/output-hash-scoped
`5cm-reviewed-torsion-v1` recipe produces a new candidate and receipt, without
replacing any run input. `--inspect-only` stops after that offline preparation;
explicit `--review-zip`, `--output-parent`, `--phenix-root` and timeout overrides
remain available. New sessions and review ZIPs retain the leading delivery/run
identifier.

The separate `cif-installed-terminal-resources-v2` API reads requested native
modification IDs and applies them only to a canonical library object in memory.
Default `5*END`/DG records supply installed atom/bond/angle/torsion/chirality/plane
row fields and numerical values, source/module hashes, charge availability and
unchanged canonical base evidence. The native row API supplies its own field
names; missing interfaces/modifications are unsupported, without guessed targets
or charge substitutions. Canonical lookup uses the installed
`get_comp_comp_id_and_atom_name_interpretation` API with an empty atom-name
list: the explicit residue name selects a library identity without supplying
model atoms. Requested code, interpreted residue name, resolved component ID
and the `iotbx.pdb` module hash are recorded additively in schema 1. Native
translation handles PDB names such as DG and library names such as GD; no
NASolve alias table or guessed alternative component is introduced.
No coordinate model is supplied or edited.

All nine payloads in the returned Cedar 10 capsule verify. It prepared the
exact reviewed 5CM candidate and captured installed Phenix 2.2.1-6174 `5*END`
rows and source hashes, then returned `NATIVE_RESOURCES_REVIEW` because its v1
direct DG lookup found no library component. The canonical control and terminal
recipe did not run. The v2 retry addresses this lookup boundary without
changing numerical targets or existing qualification checks.

All nine returned Cedar 11 payloads also verify. Phenix 2.2.1-6174 completed
resource collection at exit zero in 0.837208 s. Requested DG resolves to native
metadata ID `Gd`; the canonical base remains unchanged. Applying `5*END` removes
P/OP1/OP2, changes O5′ to OH1 and adds HO5′ with HOH1 typing. The source supplies
the O5′–HO5′ bond (0.84 ± 0.02 Å; neutron target 1.02 Å) and C5′–O5′–HO5′
angle (120 ± 3°). No unaffected bond/angle/torsion/chirality/plane row changes
and no dangling atom reference remains. Source files are unchanged.

The canonical control retains DNA group but its classification changes from
DNA to `undetermined`. Thus that classification alone does not distinguish the
earlier synthetic modified end from an installed canonical hydroxyl end; it
does not erase the earlier observed missing O5′ hydrogen/type treatment.
Formal-charge readback remains unsupported in both canonical states; partial
charges are not substituted and the earlier native qualification gates remain.

`PREPARATION_AND_RESOURCES_REVIEW` means that the separate preparation and
resource collection completed, not that generic terminal chemistry is qualified.
The exact 09 source reproduces the reviewed 5CM output in offline replay and
both returned Cedar 10/11 preparations. Terminal numerical-source collection
is complete. Complete modified-terminal adaptation,
new native bundle validation, geometry trials, refinement and adoption remain
subsequent operations. No existing native qualification check is relaxed.

## Explicit modified-terminal and revised-bundle validation

`cif_terminal_preparation.prepare_terminal_component` wraps the existing linked
preparation with a captured native numerical authority. It verifies the exact
resource receipt and all anchored outputs, completed canonical control and
source preservation, then adds the native O5′/H atom operations, bond and angle
only at explicitly declared free 5′-OH sites. The shared base and unselected
internal/phosphate contexts stay unchanged. Unknown shapes, naming collisions,
unsupported types and changed authorities are refused. Existing formal charges
are retained; the new H receives `?` because the native source supplies partial
charge only. No H coordinate or replacement numerical target is invented.

`scripts/build_cif_terminal_bundle_probe.py` builds
`12_Cedar_probe_cif_terminal_bundle.py`. It verifies every payload in the exact
returned Cedar 09/11 ZIPs, materializes only declared inputs, reuses the existing
43-site shared-code control and prepares the reviewed 5CM derivative explicitly.
Baseline and candidate use the same model. The selected candidate changes are
IGU E:1 hydroxyl treatment and 5CM A:7 torsion preparation; IGU A:6 stays internal.
The selected installation, captured module/source hashes and dispatcher are
checked before and after native execution through a declared installation
anchor. `--linked-review-zip`, `--terminal-review-zip`, `--output-parent`,
`--phenix-root`, `--timeout-seconds` and `--inspect-only` remain explicit options.

`cif_terminal_qualification` preserves the old linkage/custom-proxy/charge gates
and adds full projected row comparisons, including neutron bond targets and
torsion alternate readback. It requires the corrected 5CM torsion quartet,
primary target, weight, period and alternate in the actual native proxy.
All unselected effective definitions and recorded unaffected proxy rows must
remain equal. No missing native readback becomes a pass.

The whole-bundle outgoing-endpoint audit uses declared links, exact atom types
and graph adjacency, not hydrogen spelling or distances. Read-only replay of
the prior Cedar 09 return identifies retained O3′ H at 1AP A:5, 5CM A:7,
DZ A:12 and DP B:4. These are pre-existing linked-state REVIEW findings;
the Cedar 12 candidate preserves them visibly for subsequent explicit review.
`REVIEW`/exit 2 can therefore remain after successful interpretation, alongside
unavailable formal charges. Returned Cedar 12 verifies all 116 payloads and
completed baseline/candidate interpretation under Phenix 2.2.1-6174 (both
exit 0). The 95 passing checks include projected definitions, the corrected
5CM torsion/alternate proxy, all unselected definitions and unaffected proxies.
Six formal-charge checks remain UNSUPPORTED and the same four outgoing-H checks
remain REVIEW. Offline qualification replay reproduces all 105 outcomes and
evidence after sorting only unavailable-charge items by atom ID; the aggregate
verdict stays REVIEW. Exact receipts are indexed in the
[native evidence record](cif-linked-native-registration-evidence.json).
No model coordinates, ReadySet inputs, refinement checkpoint or production
dictionary are adopted or optimized by this probe.

### Explicit curated outgoing-oxygen candidates

`cif_outgoing_preparation.prepare_outgoing_component` accepts a preserved
curated dictionary, model, explicit same-code site contexts and a successful
captured detailed native receipt. It verifies every anchored native input and
output, the exact model and declared backbone links. Before changing a selected
site, every projected atom, bond, angle, torsion, chirality and plane row must
match the captured native definition under the existing torsion policy.

At an explicitly declared outgoing link, the bounded supported motif is O3′
with C3′ and exactly one graph-identified H/D neighbor, single bonds and OH1
typing. The recorded canonical DNA outgoing control supplies OC2 typing; no
partial charge or numerical target is borrowed. A new per-site modifier removes
that H/D and changes only O3′ typing. Existing modifiers stay in place. The
projection removes H-dependent rows and preserves all remaining values and
formal/partial charges. True free 3′ ends remain untouched. Coordinate-H
deletion, unknown authorities, changed inputs, inconsistent contexts and
unsupported motifs are refused. Sources and the coordinate model are preserved.

This is an explicit diagnostic adaptation of already captured curated inputs,
separate from whole-component generation/quarantine and production PostMR.
Before/after Doctor findings are retained; source REVIEW does not become whole
dictionary approval. No pH, replacement targets or achieved geometry is inferred.

`scripts/build_cif_outgoing_bundle_probe.py` builds
`13_Cedar_probe_cif_outgoing_bundle.py` for the exact Cedar 12 ZIP. All 116
payloads verify before declared native members are materialized. Offline
preparation proves all 24 source/native projection checks and selects 1AP A:5,
5CM A:7, DZ A:12 and DP B:4, using captured canonical DC A:4 as the type authority.
The probe replays the unchanged Cedar 12 baseline, then adds only the four
selected modifiers to the same dictionaries, parameters and 877-atom model.

`cif_outgoing_qualification` retains the terminal qualification checks and adds
full captured-baseline replay and exact prior/new modifier IDs at every site.
It keeps the reviewed 5CM torsion/alternate gate, all 38 outgoing-H audits,
unselected definitions and every recorded unaffected proxy. Installation/module
hashes and frozen inputs are checked before and after. Formal-charge limitations,
existing source reviews and broader geometry/stereochemical review remain separate;
REVIEW/exit 2 can remain after
successful native execution. Explicit input/installation/timeout/inspect-only
options and all previous runs remain available.

Returned Cedar 13 completes all four preparations and preserves every frozen
input, but stops before native interpretation because the omitted
`--phenix-root` became `None`. The corrected Cedar 14 delivery uses the working
versioned default `$HOME/Applications/phenix-2.2.1-6174`. An explicit
`--phenix-root` still selects a relocated installation, which must pass the
same version, dispatcher and source-hash checks. The new CLI regression uses
the real loader and executable discovery with explicit external-program
fixtures. Candidates and scientific qualification gates are unchanged.

Returned Cedar 14 completes both installed Phenix 2.2.1-6174 interpretations,
exit 0. All 141 payloads and anchored native files verify; offline qualification
replay reproduces **138 PASS and nine UNSUPPORTED formal-charge checks** after
sorting only unavailable-charge items by atom ID. All four outgoing-H findings
clear, and all 38 endpoint audits pass. Exact modifier IDs, projected definitions,
captured-baseline replay, unselected definitions, unaffected proxies and the
reviewed 5CM torsion/alternate all pass. Coordinates remain the same 877 atoms
at 43 sites. Aggregate REVIEW preserves unavailable charge evidence and does
not approve existing source reviews, achieved geometry or experimental chemistry.

The correction rule has no component-code or hydrogen-name allowlist. Existing
regressions exercise a synthetic `ZZZ` component with misleading H names and D,
an outgoing site alongside a true free end, OP2 H and retained terminal phosphate.
Unknown motifs, missing contexts, changed authorities and coordinate-H deletion
are refused. This generality covers the explicitly supported OH1 O3′–C3′/H
motif with captured canonical authority. The Cedar probe is deliberately pinned
to reviewed inputs; the hash-scoped historical 5CM correction and future
production integration retain their separate evidence requirements. Exact
returned hashes and software checks are in the
[native evidence record](cif-linked-native-registration-evidence.json).

### Captured Cartesian geometry review

`cif_captured_geometry.review_captured_geometry` is a separate read-only
diagnostic for detailed native inventories. It verifies atom identities,
indices, coordinate correspondence and proxy counts, then reports Cartesian
simple-bond distances, central angles and ordered chirality triple products.
The signed nominal deviation is `(observed - target) * sqrt(weight)`; a recorded
`both_signs` flag compares absolute ordered volume. All original targets and
weights are retained. Missing/negative/zero weights, degenerate measurements,
nonidentity bond symmetry and deferred proxy kinds remain visible.

This is descriptive geometry evidence, **not a native residual calculation or
scientific acceptance gate**. Existing captures omit some symmetry, slack and
top-out conventions; angle/chirality values use recorded Cartesian endpoints
without inferred transforms. Counts at nominal absolute deviations of three
and five are ranking aids. Dihedrals, constant dihedrals, ASU bonds, planes,
parallelities, sugar pucker and independent absolute stereochemistry remain
unassessed. The diagnostic cannot approve source chemistry or replace full
geometry/refinement qualification.

`scripts/build_cif_geometry_review_probe.py` builds the source-bundled
`15_Cedar_probe_cif_geometry_review.py` for the exact verified Cedar 14 ZIP.
It validates all 141 payloads and the captured receipt/report agreement, freezes
all 47 referenced native members and preserves the original archive. It carries
forward the earlier 138 PASS/nine UNSUPPORTED outcomes and existing source
assessments without reevaluating them as new native results. It writes a full
JSON report, short summary, provenance and 51-payload review ZIP in a fresh
directory. Successful review remains REVIEW/exit 2. Explicit archive/output
options remain; no new Phenix/Coot call or package installation is needed.
Actual-input replay and source-isolated relocation pass. Production PostMR,
automatic adoption, model coordinates and prior qualification gates are unchanged.

Returned Cedar 15 verifies all 51 payloads and all 47 byte-identical frozen
native members. Offline replay matches the report except computed-scalar
platform roundoff of at most 7.11e-14; identities, targets, weights, statuses,
ranks and threshold counts agree. It records 50 simple-bond and 107 angle
nominal absolute deviations at least five, with no recorded chirality sign
conflicts. For example, DX D:3 C2–O2 measures 5.129713 Å while its declared
dictionary coordinates measure 1.215504 Å and the native target is 1.215 Å.
The distorted model coordinates are identical at all 858 atomic identities
shared with Cedar 05. This localizes the problem before the later
dictionary diagnostics; the responsible construction step remains unproven.
Review frozen construction/parent-restoration and graph correspondence before
selecting any repair. Full geometry and chemical approval remain separate.

### Original construction-stage provenance

`cif_construction_provenance` snapshots explicit stage artifacts from a declared
run whose prepared-model hash and size match reviewed evidence. The saved Coot
script is parsed with Python AST; it is never executed. Literal references
rebase only through the declared historical run anchor; outside-run paths stay
uncollected. All recorded source/frozen hashes are rechecked after analysis.
Missing stages and receipts remain explicit. Unsafe paths, source symlinks,
changed inputs, duplicate atoms and multiple PDB models are refused.

The audit selects intrasite bond/angle cases at nominal absolute deviation
at least five from the captured geometry report, independent of component code.
Single-model PDB stages must match the exact site, altloc, atom name, component
and element. It records first-observed outliers and adjacent comparable-stage
threshold crossings; a gap cannot prove a transition. Same-name parent
coordinates are compared descriptively (within 0.001 Å after a difference over
0.01 Å), without claiming chemical/graph correspondence. Chronology and observed
coordinate copies do not by themselves establish the responsible algorithm.

`scripts/build_cif_construction_probe.py` builds the explicit Cedar 16 runner
for the exact returned Cedar 15 ZIP and original-run binding. The original run
is read-only; `--run` supports relocation. The runner writes a new frozen
evidence inventory, construction report and review ZIP. It requires Python's
standard library and performs no new Coot/Phenix execution, remapping,
optimization, refinement or adoption. Successful analysis retains REVIEW/exit 2
and root cause NOT_ESTABLISHED. The returned Cedar 16 capsule now verifies all
74 payloads, including 19 recorded original-run artifacts. Offline report
replay confirms 55 raw→restored threshold crossings at eight sites. Replaying
the legacy restoration on frozen inputs reproduces the restored model byte
for byte. Thus the same-name/element copying operation reproducibly damages
these captured geometries; not every MR/raw outlier is attributed to it.
The read-only receipt is preserved without rewriting its causal verdict.

### Separate attached-fragment restoration candidate

`cif_fragment_restoration` constructs an explicit candidate from a reviewed
baseline model, raw Coot coordinates, saved parent controls and captured
effective component graphs. The rule requires the complete explicit DNA
sugar/phosphate graph and a connected heavy-atom base attached only at C1′.
The base is selected by connectivity, with no component-code, glycosidic atom
name or N-versus-C linkage allowlist. It forms right-handed orthonormal frames
at raw and preserved C1′, with O4′ defining the first axis and C2′ the plane,
then transports the complete raw base by a proper rigid rotation/translation.
Parent base coordinates are never copied. All sugar/phosphate and unselected
coordinates, atom identities and noncoordinate PDB fields stay unchanged.
The baseline scaffold must match the exact frozen parent. A distance guard
allows at most 0.002 Å change within the fragment plus C1′ after PDB rounding;
attachment orientation must survive. These are implementation invariants,
not chemistry or achieved-geometry approval.

Unsupported sugar bond types/graphs, multiple attachments, disconnected
fragments, hydrogen-bearing grafts, alternate/insertion contexts, degenerate
frames and ambiguous/mismatched source identities are refused. Every declared
site is assessed; unsupported sites remain explicitly recorded and unchanged
in a partial candidate. The actual input excludes DF A:19 because three sugar
bonds are aromatic. Eight supported contexts transport 84 base atoms. The
largest fragment-distance change is 0.001040 Å. Captured-proxy prediction changes
nominal deviations at least five from 50→34 bonds and 107→72 angles, with zero
recorded chirality sign conflicts. Raw/sugar/source defects remain; no target
is retuned or model optimized.

`scripts/build_cif_fragment_restoration_probe.py` builds the Cedar 17 shuttle.
It verifies the exact Cedar 16 ZIP and every payload, freezes its contents,
and writes eligibility, preparation, predicted geometry and candidate files.
`--inspect-only` skips new native execution. Otherwise, the selected Phenix
version/dispatcher and four API source hashes must match the capture before
and after interpreting the candidate with the unchanged 18 dictionaries and
11 PHIL inputs. Qualification compares every native atom identity, effective
site definition, custom request and detailed proxy/target/weight with the
capture, and checks the exact candidate coordinates. It also records all new
native Cartesian measurements. Prior qualification and source reviews remain
visible, including unavailable formal-charge readbacks. The captured baseline
is not re-executed. No Coot, ReadySet retry, minimization, refinement or adoption
is performed. Successful mechanics retain REVIEW/exit 2.

Generic regressions, the full 1,543-test suite and actual-input deleted-build
transport pass. Returned Cedar 17 verifies all 129 payloads and 14 native
mechanics checks. Preparation replays byte for byte and native geometry
confirms the predicted counts. Intrasite improvements do not prove a sound
pairing pose: CGY–DX contacts include 9.357476 and 6.818964 Å versus 2.8 Å
targets; the latter worsens from 2.947120 Å. This is a
separate C17 diagnostic candidate. C62 later moves connected-base restoration
into ordinary PostMR; C63 adds source-proven internal-phosphate context.

### Effective/source graph recovery

`cif_effective_source_recovery` selects unsupported effective scaffolds only
when the recorded source component/input index and exact SHA-256/size match an
explicit resource inventory, and that source supports the DNA graph. Matching
uses content/hashes, never residue or filename exceptions. Missing, ambiguous,
changed or unsupported sources, incomplete shared-code contexts and prior
modifiers without a composition policy are blocked. Supported effective graphs
do not trigger regeneration. DF's frozen source has single sugar bonds; the
aromatic declarations are in its effective definition.

The Cedar 18 runner reuses whole-component source-preserving eLBOW generation
and explicit linked preparation. A native trial with coordinates held fixed
checks full projections, unaffected definitions/proxies, backbone links, custom
restraints and exact modifiers. Only passing mechanics and the already explicit
unavailable formal-charge readback permit a separate fragment restoration and
second native trial. Charge contradictions and every other review/unsupported
mechanics outcome stop it. Dictionary and coordinate effects have separate
reports; different objectives are not comparable geometry rankings.

`scripts/build_cif_effective_source_recovery_probe.py` builds the exact
Cedar 17 capsule workflow. `--inspect-only` performs source planning;
`--source CODE=/explicit/path` retains a hash-bound override. Existing
Python/Biopython/Phenix with eLBOW suffice. Captured version/dispatcher/four API
hashes are checked and generation capabilities recorded. Originals and prior
reviews survive; successful analysis remains REVIEW/exit 2. Dictionary generation
may optimize its independent component, but model minimization, pairing-pose
adjustment, Coot, ReadySet retry, refinement, integration and adoption do not
run. Generic regressions, 1,568 full tests and actual-input deleted-build
planning pass. Returned Cedar 18 verifies all 252 payloads, source-preserving
generation, 68 PASS/one unavailable charge check and 14 fragment mechanics
checks. Linked files and the nine-atom candidate replay byte for byte; raw
geometry and pairing contacts remain under review.


### Separate fixed-definition geometry trial

`cif_fixed_geometry` reconstructs an explicitly captured manager with the same
model, dictionaries and parameter files, and refuses changed atom coordinates,
identities, site definitions, detailed proxies/custom requests or native APIs
before optimization. One all-coordinate geometry-only scitbx L-BFGS trial uses
that fixed manager with installed flags enabled and normalization false. It
records symmetry, Python/compiled optimizer hashes, static constraint signatures,
per-term native residuals, gradient norms, accepted steps and the actual stopping
log. Default bounds are 500 iterations, 10,000 calls and 1,200 seconds. A cap or
error cannot become a convergence claim; special-position contexts are refused
until an explicit constraint policy exists.

Full-precision endpoints and energy stay separate from the new PDB's 8.3 rounding.
Only coordinate columns change; headers/metadata and source inputs survive.
The runner records per-site displacement and requires the serialized candidate's
new native interpretation to preserve exact identities, effective definitions,
all detailed proxies/counts and custom requests. Cartesian bond/angle/chirality
reviews remain descriptive; native nonbonded energy uses installed symmetry and
exclusions, while a separate contact/clash inventory remains unassessed.

`scripts/build_cif_fixed_geometry_probe.py` builds `19_Cedar_probe_cif_geometry_trial.py`
for the exact verified Cedar 18 capsule. Existing Python and Phenix suffice;
`--inspect-only` tests frozen-input transport without optimization. Source/charge,
independent stereochemistry, sugar pucker, pose, diffraction evidence and full
scientific qualification remain review gates. Native numerical completion alone
cannot authorize selection/adoption. All outcomes stay REVIEW/exit 2; installed
PDB postcheck remains pending. Returned optimization is recorded below. Ordinary
PostMR and earlier runs remain unchanged.


The returned Cedar 19 capsule verifies completed optimization at the explicit
500-iteration limit, **not converged**. Serialization then stopped because native
atom ordering differed from PDB record ordering. The serializer now validates a
one-to-one supported identity map using chain/residue/insertion/alternate/atom
name, plus component/element and original-coordinate guards. It maps final
native endpoints back to the original PDB records without changing record order
or metadata. Missing, duplicate or changed identities remain blocked.

Cedar 20 uses the existing builder with `--delivery-prefix 20_Cedar` and the
runner's explicit `--completed-trial-zip`. This accepts the exact verified
Cedar 19 return and its preserved Cedar 18 baseline, checks saved inputs/manager/
constraint signatures, and resumes serialization/native postcheck from saved
full-precision endpoints. It runs no new optimization and preserves the original
limit/gradient evidence. Offline actual-input replay matches all 877 coordinates;
new installed native postcheck and scientific qualification remain pending.


### Native reload attribution

The returned Cedar 20 serialization is byte-exact. Its fresh native interpretation
preserves identities/definitions and every original proxy, and adds five hydrogen
bonds and ten angles. All five contacts cross the same 3.4 Å native cutoff;
native PHIL input is byte-identical. The exact comparison correctly remains
11 PASS/three REVIEW. This differs from loss of an original restraint or a
changed chemical component.

`cif_native_reload.audit_native_reload` records full proxy multisets and can
attribute only a narrow pattern: explicit caller-supplied origin/cutoff,
unchanged identities/definitions/custom requests, no removed terms, cutoff
crossings and two associated endpoint angles through existing covalent stems.
Other changes stay unexplained. Classification is always REVIEW, not installed-
source causal proof or a waiver of the original exact comparison.
`audit_saved_endpoint_readback` separately checks PDB-precision equivalence to
the saved fixed-manager rounded vector, with explicit native float roundoff and
a historical energy basis. It does not calculate a new fresh-manager energy.

Cedar 20's 877 readback coordinates agree at PDB precision (at most 7.11e-15 Å
float difference); the recorded fixed-manager evaluation and iteration-limit
verdict remain preserved. No additional Mac run is required for that review.
Cedar 21 now verifies explicit fixed hydrogen-bond membership. Input-file
equality alone cannot ensure freshly
generated manager equality; scientific qualification and adoption remain open.

**Accepted pairing and stacking authority:** NARestraints pair selections,
stacking relationships, mapped base planes and recipe targets
supersede Phenix's automatic secondary-structure guesses whenever NARestraints
supplies the pairing or stacking policy. Native interpretation must compile the intended
contacts without competing automatic additions or a distance-based omission of
an intended contact. Phenix remains the native restraint consumer and geometry
measurement engine; this authority does not waive identity, component, covalent
geometry or achieved-geometry checks. A separate diagnostic compiler now prepares explicit membership and
suppression of competing inference; both Cedar 21 native checks pass. Generic
ordinary NARestraints policy compilation remains separate integration work.

The existing NARestraints stacking builder applies its shared base-class plane
mapping to chain neighbours. Canonical stacks use explicitly selected native
`stacking_pair` records; mapped modified stacks use explicit parallelities with
target 0 degrees and sigma 0.027. These are two compilation forms of the same
NARestraints-owned policy. Preserve their requested relationships when suppressing
competing inference. Cedar 21 compiles those declarations to explicit mapped
parallelities before disabling native secondary-structure construction. Unknown
mappings currently retain a generic declaration with a warning; verify actual
native coverage rather than assuming that fallback produced a plane. Track
physical stacks separately from base-pair parallelity/planarity and compare
expected relationships, mapped planes and targets/weights on readback.

The membership design will reuse NARestraints' existing pair guesser and
recipe builder. Its permissive geometry scoring and antiparallel-run rescue
provide pairing hypotheses, while the builder maps selected pairs to explicit
recipe contacts. NASolve already exposes this route through opt-in
`--modified-pairs-only`; that does not establish the origin of Cedar 20's frozen
pair selections. Keep guessed, reviewed/frame-selected and native-generated
membership distinguishable, retain scores/warnings, and compare actual proxies
for missing, extra or overlapping terms before freezing any new trial. A
topological guess or fixed contact set does not certify pairing chemistry;
diagnostic Phenix guesses do not acquire authority by passing a distance cutoff.

### Explicit NARestraints membership diagnostic

`cif_na_policy.compile_na_policy` prepares a separate input bundle from frozen
pair/stack declarations and the existing explicit edits. It reuses NARestraints'
workbook atom mappings, pair recipes and stacking-plane generator; it does not
rescore or discover pairs from the changed coordinates. The bounded first slice
supports unambiguous single-model chain/residue selections, declared Saenger
19/20 pairs matching configured recipes, and mapped stack declarations. Unknown
settings, alternate/insertion contexts, missing atoms or overlapping generated
edits stop before output. All non-SS input lines and original files survive.

**Methods.** The compiler records declaration provenance, resolves recipe atom
selections against captured native identities, emits explicit pair contacts and
mapped parallelities, and rejects duplicate physical requests. Once all declared
generic relationships have explicit representations, a separate final control
disables native secondary-structure construction. Existing modified-base edits,
component modifiers and all dictionary bytes remain. `qualify_na_policy` checks
exact requests/targets/weights, full retained proxy rows and component/identity
invariants using the installed origin registry. New native metadata is opt-in;
the ordinary inventory and pipeline defaults are preserved.

Cedar 21 verifies the exact returned Cedar 20 capsule and applies one policy to
two preserved coordinate sets: the initial model and saved PDB endpoints. This
is an interpretation-only test of membership stability, not another optimization.
Actual-input offline compilation produces 31 new bonds, 52 angles and 35
parallelities for 12 pair and 23 stack declarations, retaining the prior explicit
edits. The returned Phenix 2.2.1-6174 interpretations each pass **14/14 exact
mechanics checks** (6.298652 s and 1.450339 s, exit zero). All 491 payloads and
367 frozen prior payloads verify; the 19 dictionaries, component definitions,
modifiers, 38 backbone links and all captured static proxy rows survive. Both
managers contain 52 explicit bonds, 86 angles, eight planes and 58 parallelities,
with no competing SS-origin terms. The native effective PHIL and eight API
fingerprints match across cases. Compiler replay is byte-exact.

This verifies declared membership at two saved coordinate sets. No new
optimization occurs. The saved endpoint has four bond/ten angle nominal
deviations at least five and no sign conflicts among 158 recorded chirality
proxies; those descriptive counts do not establish geometry or convergence.
The objective differs from Cedar 19/20; historical energies and its iteration
limit are not reclassified. Geometry, source/charge and scientific approval
remain REVIEW, with no production integration or automatic adoption. The next
step is the separate fixed-policy geometry trial described below.

### Geometry trial under the verified NARestraints policy

`scripts/build_cif_na_geometry_probe.py` builds the source-bundled Cedar 22
runner, `22_Cedar_probe_cif_na_geometry.py`. It accepts only the exact verified
491-payload Cedar 21 capsule. Both native membership prerequisites replay
offline, and all previous evidence remains preserved. `--inspect-only` checks
that path without native execution. The installed trial starts from the captured
saved endpoint with its 19 dictionaries and 13 compiled PHIL inputs; it does
not rerun pair guessing, regenerate definitions or recompile policy.

**Methods.** The existing fixed-definition native engine rebuilds the captured
manager and requires exact initial coordinates, identities, component mappings,
geometry, eight installed API sources and native SS/origin metadata before
calling L-BFGS. The opt-in `policy_inventory=True` leaves the existing default
contract intact. One trial permits at most 1,000 iterations and 20,000 objective
calls, with a default 1,200-second native-phase timeout. Native geometry flags,
symmetry, nonbonded handling and static definitions remain fixed. The receipt
records actual stopping/limit/error evidence, gradients, objective terms and
optimizer source hashes. Full-precision endpoints and PDB-rounded fixed-manager
energies remain separate, alongside coordinate displacements and descriptive
bond/angle/chirality measurements.

Identity-based serialization writes only coordinate columns in a separate PDB.
Native reread uses the same input bytes and opt-in policy inventory.
`qualify_fixed_policy_geometry` retains the 14 existing exact identity,
definition, coordinate, request and static-proxy checks, then requires successful
interpretation, the same explicit policy with no competing SS-origin terms,
and exact installed APIs: 17 checks in this slice. No exact comparison is
relaxed. Dynamic nonbonded neighbours may change with coordinates; they are
reported separately from the static proxy contract.

Actual-input offline prerequisite replay and synthetic worker/transport tests
are distinct from installed native execution. Returned Cedar 22 verifies all
609 payloads and 491 unchanged prior payloads plus their manifest. Phenix
2.2.1-6174 completes the trial in 4.4478 s and reread in 1.737436 s, exit zero;
all 17 exact mechanics checks pass and serialization replays byte for byte.
The fixed-policy objective decreases 24.26% and gradient norm 91.17%, but the
line search reports rounding errors preventing progress at 905 iterations /
970 calls, with a false native criterion: retain NOT_CONVERGED_ERROR.
This precedes PDB serialization. PDB rounding separately changes the recorded
gradient norm from 91.28 to 907.04, so preserve full-precision endpoint evidence.
Nominal distance deviations >=5 decrease four to three, while ten angle
deviations remain and no chirality sign conflicts appear. All three remaining
distance outliers are CGY A:20–DX D:3 hydrogen bonds at 4.34–5.58 Å against
2.8 Å targets; one worsens slightly. Nine angle outliers involve that pair and
one involves DP B:4 N5. Pair pose/intent, local definitions and numerical
line-search/gradient behavior need review before another trial; no target
change or automatic rerun follows from this descriptive evidence alone.
A limit/error remains nonconverged, and meeting a native criterion does not
certify complete geometry, source/charge, pucker, absolute stereochemistry or
experimental fit. Overall REVIEW/exit 2 and no adoption remain deliberate.
Only within-trial energies share this new policy; Cedar 19/20 retain their
historical objective and stopping record. Ordinary PostMR is unchanged.

### Saved native gradient audit

`scripts/build_cif_gradient_audit_probe.py` builds the separate Cedar 23 runner,
`23_Cedar_probe_cif_gradient_audit.py`. It accepts only the verified 609-payload
Cedar 22 capsule, replays its 17-check mechanics and stopping evidence, preserves
all earlier payloads and assesses the same 19 dictionary files with CIF Doctor.
The existing planar-angle rule detects the retained DP N5 conflict; this probe
adds no replacement target. All explicit intersite distance groups are reported
at the saved full-precision coordinates. Six coordinate-probe atoms are selected
from the largest bond/angle nominal deviations, using native indices and labels
with no residue-code or site allowlist.

**Methods.** `cif_gradient_audit.run_native_gradient_audit` rebuilds and exactly
matches the captured initial identities, coordinates, definitions, geometry,
policy/origin metadata and eight installed API sources. The six installed
numerical-source hashes and full static constraint signature must also match
Cedar 22. Saved full-precision and PDB-rounded vectors are evaluated without
optimization. Each case records the full objective plus isolated bond, angle,
dihedral, chirality, planarity, parallelity and nonbonded controls. The controls
change evaluation flags only, with no definition/input edits or adopted model.

Analytical directional derivatives are compared to central energy differences
at steps 1e-3, 1e-4, 1e-5 and 1e-6 Å. Directions include the full gradient,
an alternating global direction, the selected atom axes and each category's
gradient. Every sampled value remains visible; consistency requires agreement
at two consecutive steps within absolute 1e-4 plus relative 1e-4. Separate
repeat/snapshot and additivity checks use absolute 1e-8 / relative 1e-10.
These numerical tolerances do not change native proxy comparisons. The audit
also retains full per-family gradients, local descent profiles, neighbour
counts and captured-versus-rebuilt energy/gradient-norm comparisons. Static
constraints and installed source hashes must remain unchanged afterward.
The cap is 4,000 native energy calls and a default 1,200-second timeout.

This is a bounded diagnostic of sampled numerical consistency. A discrepancy
requires interpretation of step dependence, controls and neighbour behaviour;
it does not by itself identify a Phenix defect. Agreement cannot prove every
gradient component, global convergence, intended pairing chemistry or
experimental fit. No minimization, target retuning, candidate model, diffraction
refinement or adoption occurs.

**Returned Cedar 23 evidence (2026-10-19).** All 670 payloads verify; the
609-payload prior capsule and its manifest remain byte-identical. Phenix
2.2.1-6174 completes 2,734 energy evaluations in 7.8046 s, native exit zero.
Exact manager, API/numerical sources and static constraint signatures match.
In both coordinate cases, parallelity and the full objective fail 18/21
sampled directions; each other category passes 21/21. Baseline repeats,
captured snapshots and additivity agree. The parallelity count remains 58
through its isolated samples. Dynamic nonbonded neighbour counts can vary;
this evidence does not claim exact dynamic neighbour membership.

An independent spectral plane calculation reproduces native energies and
selected central differences. Applying the public CCTBX accumulation-loop
bounds to those analytical plane gradients reproduces every saved parallelity
gradient component to about 1e-12. The public loop accumulates only
`max(0, j_size - i_size)` second-plane contributions. The immutable primary
[source blob](https://api.github.com/repos/cctbx/cctbx_project/git/blobs/25d3a75f20d3611dcb32d919a893bc0beb18e6a0)
and exact derived metrics are recorded in the
[native evidence ledger](cif-linked-native-registration-evidence.json).
This strongly indicates an accumulation defect, while the installed C++ header
identity and isolated native per-proxy reproduction remain unverified. Small
negative-gradient steps still reduce energy; a causal explanation of the
prior line-search failure remains open. The next check isolates that installed
calculation without changing NARestraints selections, planes, targets or weights.
`--inspect-only` performs capsule, distance-group and dictionary checks offline.
The finite-difference method follows the same checking principle used in the
[CCTBX gradient tutorial](https://cci.lbl.gov/docs/cctbx/tuto_rigid_body/);
actual installed source identities remain pinned by the captured hashes.

### Installed per-plane accumulation diagnostic

`scripts/build_cif_parallelity_audit_probe.py` builds Cedar 24,
`24_Cedar_probe_cif_parallelity_audit.py`, from the verified 670-payload
Cedar 23 ZIP. It verifies the nested prior/native evidence, replays Cedar 22's
17 mechanics checks and preserves its stopping classification. It executes no
captured code. `--inspect-only` checks the source-bundled capsule and mechanics
offline. Returned installed execution is recorded below.

**Methods.** The installed worker rebuilds and exactly matches the initial
manager and source/constraint fingerprints. The two newly consumed Python
adapter modules are also fingerprinted before/after evaluation, without claiming
a retrospective Cedar 23 source match. For all 58 captured plane restraints
at both saved precisions, it obtains `parallelity(...).gradients()` and scatters
every first/second-plane contribution by atom identity. Independently, it
calls `parallelity_residual_sum` on a singleton container. Both kernels retain
full gradients, residuals and repeated baselines. Three directions and four
central-difference steps test each original and swapped plane order. Swapping
retains the same identity order and target/weight metadata; it is an isolated
diagnostic control, not a changed NARestraints policy.

Three asymmetric tilted controls use 4/4, 4/6 and 6/4 atoms, also both orders.
At each saved crystal coordinate set, the worker additionally compares manually
scattered gradients, the actual full proxy container, manager evaluation and
every captured Cedar 23 parallelity gradient component. The supported slice is
zero-target, zero-slack, non-top-out, symmetry-free planes; unsupported inputs
fail visibly. Limits are 7,000 single/container evaluation pairs (two residual
kernels per pair), plus two whole-batch comparisons, and 1,200 seconds. The
58-proxy input requires 6,188 pairs. Numerical tolerances match Cedar 23 and
do not change exact native inventory gates.

Available `parallelity.h` and `parallelity_bpl.cpp` bytes are frozen from the
imported geometry-manager package directory, with checksums and explicit missing
status. Header identity alone does not establish the source used to compile
the pinned binary. These controls can isolate an accumulation failure; they
cannot prove why the earlier optimizer stalled or approve chemistry or
convergence. No optimization, native patch, target/weight edits, new crystal
model, diffraction/refinement or adoption occurs. Existing pairing/stacking
authority remains with NARestraints. Exact software checks and source blob IDs
are in the [native ledger](cif-linked-native-registration-evidence.json).

**Returned evidence (2026-10-19).** All 732 payloads and the frozen 670-payload
prior plus manifest verify. Phenix 2.2.1-6174 completes 6,188 evaluation pairs
in 3.483823 s, native exit zero, with unchanged initial manager, native/numerical
source hashes and static constraints. All 17 prerequisite mechanics checks replay.
All 714 sampled single-restraint directions pass; every one of 238 accumulated
orders fails the second-plane and alternating directions. Energies, repeated
arrays and individual-gradient plane-order invariance agree. Accumulated
gradients depend on plane order. For the 4/4 tilted control, the second-plane
gradient norm is 2.21375 individually and zero after accumulation.

Installed header/binding files match the recorded public source blobs. The
second loop adds only `max(0, j_size - i_size)` second-plane contributions.
That model reproduces every per-order accumulation array exactly; the full
manager and full native container reproduce the same incomplete gradient.
The confirmed scope is the installed non-unit-cell path for these supported
proxies and controls. Compiled-source provenance and other versions/overloads
remain separate questions.

Saved-data recombination replaces only the incomplete parallelity gradient
with complete individual-restraint sums. All 84 Cedar 23 full/parallelity
directional checks then agree, explaining the 72 earlier failures at unchanged
energies, coordinates, directions and tolerances. This is algebraic replay,
not a corrected native manager or optimizer run. Cedar 25 implements the
separate correction audit below. The NARestraints policy remains fixed;
convergence and chemistry remain under review. No repeat Cedar 24 is needed.

### Complete native plane accumulation correction

`scripts/build_cif_corrected_gradient_probe.py` builds Cedar 25,
`25_Cedar_probe_cif_corrected_gradient.py`, from the verified 732-payload Cedar 24
return. The explicit NASolve evaluator retains the native unnormalized energy
and full gradient, subtracts the native accumulated parallelity contribution,
and adds every original single-restraint i/j gradient by atom index. Shared
atoms receive all contributions. No proxy reconstruction, target edit, native
file patch or global monkeypatch is involved. Native accumulation that is
already correct is unchanged; symmetry-bearing planes and special positions
are refused. The implementation consumes the original target/slack/top-out
parameters through the native single-restraint kernel; the actual installed
validation remains limited to this capsule's supported planes.

The probe replays the 17 prior mechanics checks and exactly matches the initial
manager, static constraints and pinned native/API/adapter/C++ source identities.
At initial, saved full-precision and PDB-rounded coordinates, it first matches
the old raw full-objective energy and gradient norm. It also matches both saved
complete and incomplete plane arrays. These raw baselines are not requirements
on the corrected gradient norm.

Fresh full-objective and seven category controls use four central-difference
steps, repeated baselines, target/gradient additivity, outlier-selected atom
directions and the existing numerical tolerances. The audit budget is 5,500
evaluations, plus five recorded preflight evaluations. Complete individual and
container plane residuals must agree on every correction-bearing evaluation;
the returned native energy is unchanged. The probe records
`SAMPLED_NATIVE_DERIVATIVES_PASS` or `DERIVATIVE_REVIEW`, while overall status
remains REVIEW/exit 2. Returned Phenix 2.2.1-6174 execution verifies 4,101 audit
evaluations plus five preflight calls with zero energy change. Both endpoints
pass all 168 sampled directions each. The initial case passes 162/168, retaining
three failures each in the full and parallelity categories. Repeats and
additivity pass in every case; the overall correction stays DERIVATIVE_REVIEW.

This is an opt-in diagnostic, with no automatic production integration or
optimization. A native derivative pass is required before a separate bounded
geometry trial; it cannot establish convergence, chemistry or adoption.

### Plane-order correction and rotated controls

The remaining Cedar 25 initial discrepancy is reproduced by an independent
centered-scatter eigensystem calculation and a model of the installed header's
normal-sign handling. The header negates the second raw normal when aligning
the two normals, but continues differentiating through the original second
plane's row vectors. Four captured initial stacks exercise that branch; the
same model reproduces the complete stored gradient within 3e-12 in norm. Both
endpoints have no such normal-sign flips. This is source/model evidence for
the sign error, separately from the installed accumulation defect already
reproduced by Cedar 24. It does not establish the optimizer failure's cause.

`scripts/build_cif_plane_order_probe.py` builds Cedar 26,
`26_Cedar_probe_cif_plane_order.py`, from the verified 794-payload Cedar 25
return. Its explicit evaluator uses the original restraint's first-plane
gradient for i and the swapped native copy's first-plane gradient for j.
The native copy constructor preserves targets, slack, limits, top-out, weight
and origin ID; every field and swapped residual is checked. Copies are used
only for evaluation. All manager membership and native energies stay fixed,
including shared-atom contributions. This avoids second-plane sign handling
without fitting a replacement objective or choosing exceptional sites.

Before fresh numerical checks, the worker matches the same sources/static
constraints, three raw full-objective snapshots and all three captured complete
and incomplete plane arrays. The full-objective/category audit retains its
5,500-call cap, with six recorded preflight evaluations. A separate all-plane
audit checks every one of the 58 proxies at all three coordinate sets, both
orders, three local directions and four numerical step sizes. It retains both
the original complete kernel gradient and the new two-first-plane gradient,
including their repeated arrays and order invariance evidence.

Equal/unequal tilted 4/4, 4/6 and 6/4 controls are repeated after a 30-degree
rigid rotation about x. This changes the raw-normal orientation branch while
preserving physical plane angles. The audit checks energy invariance and
gradient rotation as well as derivatives. Expected work is 9,360 two-kernel
evaluation pairs under a separate 10,000-pair cap, plus the 4,101 global audit
evaluations and six preflight calls. All numerical tolerances are unchanged.
The per-plane audit currently supports zero-target, zero-slack, non-top-out,
symmetry-free proxies, which cover this capsule. Unsupported cases fail
visibly. Returned Cedar 26 verifies all 857 payloads and preserves all 794 prior
payloads plus their manifest. Installed execution completes in 53.402075 s:
all 504 global/category directions and all 1,080 corrected per-plane directions
pass. Native complete gradients fail eight initial orders and six rotated toy
orders, reproducing the predicted sign cases. All corrected order/rotation,
repeat/additivity and energy checks pass; native energy change is zero.
Qualification is SAMPLED_NATIVE_DERIVATIVES_PASS. This remains sampled evidence;
geometry, convergence, chemistry and adoption stay open.

### Bounded geometry trial with qualified corrected gradients

`scripts/build_cif_corrected_geometry_probe.py` builds Cedar 27,
`27_Cedar_probe_cif_corrected_geometry.py`, from the exact verified Cedar 26
return. It replays the 17 native mechanics prerequisites and recomputes all
stored corrected derivative comparisons before native work. The correction
module must match Cedar 26 byte for byte. The native worker pins the same
numerical modules, adapters, C++ sources, definitions, explicit NARestraints
policy and static constraints. Its full corrected initial gradient and energy
must match the qualified snapshot before L-BFGS can start.

The trial restarts from the same original initial coordinates as Cedar 22.
Default limits remain 1,000 iterations, 20,000 objective calls, gradient epsilon
1e-5 and a 1,200 s native timeout. The original unnormalized native energy is
evaluated with the qualified both-first-plane gradient correction; targets,
weights, definitions, proxy membership, symmetry/exclusions and compiled
pairing/stacking intent stay fixed. Native step history, stopping reason,
errors, criterion result and full-precision endpoints are preserved. Raw native
gradient norms are recorded separately from the corrected norms used by the
optimizer. An improvement or native exit zero does not establish convergence.

After the bounded trial, fresh full-objective and seven category controls
check both full-precision and PDB-rounded endpoints using the same four-step
criteria and frozen coordinate probes, with a separate 4,000-evaluation cap.
The existing exact-identity serializer writes a separate candidate while
preserving all other PDB columns. Fresh native interpretation must pass all
17 fixed-policy mechanics checks. Endpoint derivative qualification, stopping
classification and mechanics remain independent, including when any requires
review. No new guessing, policy recompilation, dictionary generation, ReadySet,
diffraction/refinement or adoption occurs. Ordinary PostMR/refinement defaults
and previous runs remain unchanged.

Returned Cedar 27 verifies all **980 payloads**, including 857 unchanged prior
payloads and their manifest. Phenix 2.2.1-6174 (dispatcher 2.2.1) completes the
trial/audit in **75.822869 s** and PDB readback in **1.565038 s**, both exit zero.
All **17 native mechanics checks** and **336 sampled endpoint directions** pass;
independent replay recomputes all 1,344 four-step samples and analytical dot
products. Candidate serialization reproduces byte for byte, including the
157 native/PDB ordering differences resolved by exact identity.

The fixed objective changes **3784.7499458394077 -> 2697.762263611603**, a
**28.72%** decrease, and corrected norm **1110.520668509296 ->
372.53738052839816**. At **1,000 iterations / 1,028 calls** the stop is
**NOT_CONVERGED_LIMIT**, with no recorded optimizer error and the native
criterion false. All accepted targets decrease; iteration 900 to 1000 still
reduces the target by **31.2321**. Corrected norms fluctuate, so a lower target
does not certify proximity to convergence. The PDB-rounded fixed-manager
target **2700.856094619088** and norm **905.6214940891548** remain separate.

Both precisions retain three nominal distance and ten angle deviations at least
five, and zero sign conflicts among 158 captured chirality proxies. All three
distance outliers remain CGY A:20-DX D:3 contacts at **4.42–5.62 Å** against
2.8 A targets; nine angle outliers involve that pair. The retained DP B:4 N5
angle is **127.638 degrees** against 109.471 degrees. No target changes follow
from those residuals alone. A separately bounded continuation from saved full
precision is justified for the next numerical test, after fresh exact
source/start-vector matching and with new endpoint derivative/mechanics gates.
Cedar 28 supplies that continuation below. Rerunning Cedar 27 restarts the
original model. Geometry, convergence, chemistry and adoption remain open.

### Bounded continuation from saved full precision

`scripts/build_cif_geometry_continuation_probe.py` builds Cedar 28,
`28_Cedar_probe_cif_geometry_continuation.py`, from the exact 980-payload Cedar 27
return. Its reusable engine opt-in `continuation` requires the same qualified
correction, complete endpoint derivative proof, prior limit stopping and exact
native source/static identities. The source-bundled inspector preserves all
prior payloads, pins the captured trial worker/verifier bytes, replays the
17 mechanics checks and recomputes the raw prior derivative evidence. Captured
code is retained as evidence and never executed.

The native worker first rebuilds and matches the original manager and qualified
initial snapshot. It then loads the saved full-precision native atom-order
coordinates and requires the same static signature plus a fresh match of the
**entire corrected gradient and target** to Cedar 27. The expected start is
**2697.762263611603 / 372.53738052839816** (target / corrected norm). Rounded,
reordered or altered points cannot pass that gate. The continuation starts
fresh L-BFGS history; it restores coordinates rather than optimizer memory.

One stage permits at most **1,000 further iterations / 20,000 calls**, gradient
epsilon **1e-5** and **1,200 s** native timeout. It retains prior stopping and
reports new stopping and cumulative optimizer counts separately. Native energy
definitions, all 19 CIF/13 PHIL inputs, explicit NARestraints pair/stack policy
and native sources/static proxies stay fixed. Fresh full/rounded endpoint
derivative audits retain the **4,000-evaluation** cap, and candidate
`candidate/continued_geometry_model.pdb` must pass all 17 native PDB mechanics
checks. New-stage displacement is measured from the saved endpoint separately
from serialization displacement relative to the original initial model.

The actual-input offline inspector and synthetic deleted-build transport pass.
Returned Cedar 28 verifies all **1,104 payloads**, including all 980 unchanged
Cedar 27 payloads and their byte-identical manifest. The published runner and
110-member runtime, trusted worker/correction bytes and installed API/numerical/
adapter/C++ identities match. Phenix 2.2.1-6174 (dispatcher 2.2.1) completes the
continuation/audit in **76.066902 s** and PDB readback in **1.692405 s**, both
exit zero. All **17 native mechanics checks** and **336 sampled endpoint
directions** pass. Independent replay recomputes all 1,344 four-step samples
and exact candidate serialization; it executes no captured code.

The fixed target changes **2697.762263611603 -> 2599.5275576416398 (3.64%)**
and corrected gradient norm **372.53738052839816 -> 144.16496914598542
(61.30%)**. The new stage reaches **1,000 iterations / 1,036 calls**, cumulative
**2,000 / 2,064**, with no recorded optimizer error and the native criterion
false. Preserve **NOT_CONVERGED_LIMIT**. All accepted targets decrease; the last
100 iterations reduce it by **8.7054**, while corrected norms fluctuate. Across
both corrected stages, target/norm decreases are **31.32% / 87.02%**. The
PDB-rounded target/norm **2602.971189992592 / 950.90556704461** are separate.

Both precisions retain **three distance / ten angle nominal deviations >=5**
and zero sign conflicts among 158 chirality proxies. The three CGY A:20-DX D:3
contacts remain **4.360-5.583 A** versus 2.8 A; nine angle outliers involve that
pair. DP B:4 C6-N5-C7 remains **127.749 degrees** versus 109.471 degrees.
Angles contribute 1193.6456 and bonds 553.0823 to the unchanged native target;
individual category gradients can cancel and their norms do not add. These
findings require term/source review before selecting another bounded trial or
a separately declared chemical candidate. No next native delivery is prepared.
Existing corrected/uncorrected trial defaults are unchanged; no new package,
target tuning, policy guessing, refinement, scientific approval or adoption is
introduced.

### Fixed-policy base-orientation audit

`scripts/build_cif_base_rotation_probe.py` builds Cedar 29,
`29_Cedar_probe_cif_base_rotation.py`, from the verified 1,104-payload Cedar 28
return. It replays the entire qualified lineage and all 17 prior mechanics
checks before any native work. Exact correction and installed source identities,
the original inventory/static constraints and complete corrected initial vector
must match. Both saved endpoint family targets and entire gradients must then
match before angular evaluations begin.

The reusable planner selects sites from ranked nominal bond/angle outliers
(default absolute threshold five), reusing the supported connected-base graph
and explicit DNA scaffold rule. The base attachment is graph-selected, including
N- and C-linked cases. Unsupported context and any group-limit omissions remain
explicit. For each selected group, proper Rodrigues rotations about the
C1-prime-to-attachment axis preserve the entire scaffold, attachment atom and
all internal base distances. No original or candidate coordinate file changes.

The fixed grid is **-180, -90, -30, -10, 0, 10, 30, 90, 180 degrees**, sampled
independently for each base at full and rounded precision. The full objective
and seven isolated family controls retain native energies and the qualified
plane-gradient evaluator. The analytic rotational slope is
`sum(g_i dot (axis cross (r_i - origin)))`, in target units per radian. Four
central-difference steps **1e-3, 1e-4, 1e-5, 1e-6 radians** check the full slope
at every angle and each family slope at zero angle. The existing absolute-plus-
relative **1e-4** criterion requires two consecutive passing steps.

Receipts retain baseline repeats, target/gradient additivity, +/-180 energy
agreement, fragment-distance invariance and actual neighbour counts. Selected
outlier distances/angles are measured descriptively at every sample. Intrasite
angle contexts retain exact effective target rows, center-atom types and shared
declared planes. Internal base geometry is fixed during rotation; a parameter
conflict therefore cannot be cleared by this scan. Each lowest grid value is
explicitly a diagnostic sample, not a candidate or a minimum.

The default bounds are **six supported groups / 3,000 total energy evaluations /
1,200 s**. All 17 preflight evaluations count toward the energy cap. Offline
replay selects A:20, D:3 and B:4 by the same generic rule, each with 11 base
atoms; it does not hard-code those identities. The actual-input inspector and
synthetic deleted-build source transport pass. **88 focused and 1,902 full tests
pass**, with two full-suite skips and 276 passing subtests. Returned installed
Phenix **2.2.1-6174 / dispatcher 2.2.1** execution verifies all 1,173 payloads
and passes all 96 sampled rotational directions (384 four-step samples), in
31.56962 s and 1,201 total calls. All three independent coarse grids favor
zero degrees at both precisions; nonzero analytic slopes remain. This result
excludes no unsampled/coupled configuration and establishes no minimum. NARestraints intent,
all targets/weights, original runs and production defaults remain fixed. No
optimization, policy recompilation, dictionary generation, installed native
patch, refinement or adoption occurs.

### Source-graph numerical recovery candidates

`scripts/build_cif_numerical_recovery_probe.py` builds Cedar 30 from the verified
Cedar 29 capsule. The reusable planner inspects declared source angle/plane
contradictions on one independent graph-valid component definition, records all
model sites/modifiers, and supports explicit component selection without a
residue allowlist. The reviewed probe selects DP's retained N5 conflict; other
source reviews remain deferred. This is a candidate-only numerical operation.

A separate graph source preserves exact atom identifiers/elements, H/charge,
bond order/aromatic/stereo declarations and signed chirality. It excludes old
numerical targets, energy types, planes and torsions; the complete original and
removed-field inventory remain frozen. Complete source ideal coordinates may
seed naming/initial geometry. If absent, complete declared source atom x/y/z
are accepted only with explicit `SOURCE_DECLARED_COORDINATES_NOT_INDEPENDENT_IDEAL`
provenance. Partial/nonfinite families, missing/ambiguous formal charges, lossy
naming and graph changes refuse. No experimental model supplies target values.

The existing eLBOW-v4 adapter discovers installed help capabilities and retains
its source-state, explicit-H and chirality controls, isolated output, timeout
and raw evidence. It requests generator-internal geometry optimization; it
runs no crystal-model optimization. The output is compared to both graph source
and original numerical dictionary. Existing graph/state/stereo and numerical
rejection gates remain; complete source formal charges must survive exactly,
without partial-charge substitution. `CANDIDATE_REVIEW` still requires native
site/proxy, source/chemical and scientific qualification. Generation failures
and unresolved findings are retained; no angle is retuned to match the model.

The probe verifies the 1,173-payload capsule, exact trusted worker/core/source
identities and full qualified lineage, recomputes all 96 saved rotation
directions and replays all 17 native mechanics prerequisites. Default bounds
are at most three explicitly selected components and 600 seconds each. Actual
input planning and graph preparation pass. Returned Cedar 30 verifies all
1,185 payloads and preserved predecessors, but installed eLBOW stops before
generation on the lower-case coordinate-tag attribute. No dictionary exists
to assess; its zero-review console count is not a numerical pass.
The original 19 CIF/13 PHIL inputs and NARestraints pairing/stacking policy stay
frozen. No new dictionary is applied, no modifier composition is attempted,
and no ReadySet retry, refinement or adoption occurs. Existing production
defaults and dependencies need no migration.

### Canonical coordinate tags and explicit PDU control

Cedar 31 uses the same numerical-recovery builder with
`--delivery-prefix 31_Cedar --component-control PDU`. It accepts the exact
Cedar 30 failure capsule, validates all 1,185 payloads, both generation receipts,
original/graph inputs and the input-parser/no-candidate outcome, then replays
the preserved C29/C28 derivative/mechanics lineage. The corrected graph export
retains normalized internal lookup but emits canonical
`pdbx_model_Cartn_x/y/z_ideal` tags for the installed reader. Coordinate values
and chemical declarations remain unchanged. Receipts state both source and
output coordinate fields. No output dictionary means numerical assessment
NOT_RUN, not a zero-count result.

`--component-control CODE` is an explicit builder option (up to two controls,
three total candidates). It admits only test fixtures listed with exact hashes
and sizes in [the public control catalog](cif-doctor-ccd-controls.json). PDU's
unmodified 9,033-byte public CCD is the requested exception to the original
local-only control collection. It is bundled under `controls/PDU.cif`, never
installed into `nasolve/data/ligands`. The original 18-control ZIP is unchanged.
The runner freezes the source and records graph/stereo/H/charge, mapped roles
and compiler output, then applies the same independent generation/comparison
gates as DP. No experimental model supplies generation targets.

The generic control API uses the actual NARestraints mapping, pair compiler
and stacking matrix on exact source atom identities. PDU has the T role; AT
compiler controls resolve N3-N1 and O4-N6 contacts and two angles, with a pair
parallelity. Both stacking orders resolve its C7 role to C5A. The propynyl
C5A-C5B triple bond and complete 38-atom/39-bond source survive graph export.
The H named H2 is attached to O3-prime, demonstrating why context rules follow
bonds. A synthetic canonical partner exercises the compiler only. These are
not native proxies or achieved pair geometry, and no PDU is inserted into the
frozen scaffold. Returned Cedar 31 preserves all 1,209 payloads and both
failed attempts: DP stops on missing alt_atom_id; PDU reads 38 atoms, 39 bonds
and three R/S/R centres, then fails in the installed optimizer restart path
after nonconvergence, with an empty XYZ intermediate. Neither produces a
dictionary; chemical and numerical generation assessment remain NOT_RUN.

### Installed eLBOW input contract and source evidence

Cedar 32 uses the same builder with --delivery-prefix 32_Cedar and
--component-control PDU, then runs with --native-contract-only against the
exact Cedar 31 ZIP. The new reader verifies its 1,209 payloads, trusted build,
both receipt/artifact sets, exact original/graph copies and distinct failure
evidence. Prior excluded pickle descriptors remain visible without loading
serialized objects. The 17 native mechanics and 96 rotational direction
prerequisites replay; captured Python is never an executable authority.

The graph exporter supplies alt_atom_id from exact primary IDs only when the
whole column is absent. Existing aliases, including unknown tokens, survive.
The additive atom_alias_metadata receipt records the compatibility metadata
separately from unchanged chemical declarations. DP
graph SHA-256 becomes 3cfff153966194861451113747ba8f1ebbd7b47d58c8aa9acfd50ddfcc4783dd;
PDU graph bytes are unchanged. This fallback is independent of component code.

The explicit input-contract mode derives the installed Python-library directory
from the already verified iotbx/phil.py anchor and copies four exact eLBOW
modules: Utilities.py, optimisation_manager.py, command_line/builder.py and
chemistry/any_chemical_format_reader.py. Each must resolve under the selected
installation and be at most 1 MiB. Copies retain original bytes/hashes and
relative installed/snapshot anchors. AST item-attribute accesses are an
inventory, not an inferred universal required schema. Installed and copied
bytes must match before and after the two input checks. No installed code is
modified, and no captured code or pickle is executed. Native source snapshots
stay in the private review capsule and outside Git.

Each input check requires exact installed help support for a read-only flag
and existing state-retention options, then uses source.cif with read-only,
exact ID, a separate output prefix, add_hydrogens=False, pH=low and
chiral=retain. The owned process group is bounded to at most 60 seconds.
Source and frozen source/dispatcher bytes are checked; unexpected optimizer
markers or nonzero execution retain REVIEW. PARSER_READ_ONLY_PASS means only
exit zero under that recognized input path. No numerical generation or
optimizer setting change occurs. Receipts add requested_action,
installed_elbow_contract and native_input_checks; each input-check directory
has a probe_directory relative anchor. native_execution can now record
READ_ONLY_INPUT_CHECKS without claiming native proxy or geometry qualification.

Existing explicit generation remains the default without this new flag.
Production PostMR, curated dictionaries, NARestraints pairing/stacking policy,
scientific gates and dependencies are unchanged. At that delivery, native read-only checks and source capture were pending.
The returned
Cedar 32 capsule verifies all 1,229 payloads and the four exact source snapshots.
PDU completes read-only parsing (exit zero, 1.371951 s); DP stops in 3.551229 s
on absent atom pdbx_aromatic_flag. The captured reader also requires CCD atom
stereo and bond value_order fields, while the preserved DP dictionary declares
legacy bond type/aromatic flags and signed chiral volumes.

### Reader projection and explicit bounded generation

Cedar 33 uses the same builder with --delivery-prefix 33_Cedar and
--component-control PDU. Run against the exact Cedar 32 capsule with
--single-block-steps 180. It verifies the complete installed contract and prior
qualified lineage, retaining the original DP/PDU outcomes and every source.

prepare_elbow_ccd_input writes a separate consumer file. Formal-charge and
aromatic/stereo aliases must agree after normalization. Only declared single,
double and triple orders translate to SING/DOUB/TRIP; unsupported localization
is refused. Atom aromatic/CIP metadata without declarations is ?, never an
inferred N/R/S assignment. All original non-consumer fields, coordinates, H,
bond stereo and signed chiral volumes survive unchanged, and a semantic
round-trip plus raw Doctor comparison is retained. PDU consumer bytes are
unchanged. DP consumer SHA-256 is
6b914d7fed9a98e30ed68b2381507e6d5bb0dc9b351fee48d42ced085c9501fa.

Fresh installed read-only checks gate each component independently. An explicit
step request requires valued option support from exact installed help and the
four unchanged captured reader/optimizer source identities. The installed
manager uses a positive opt_steps value to skip its default later-block XYZ
reload. Before generation, an installation-bound Phenix Python worker calls
only the installed options parser with the intended source/seed/state/step
arguments. It verifies the imported module path/hash, records the module
snapshot, and requires the requested steps and exactly one effective block.
It records the default tolerance without changing it. Installed/captured option
source bytes are checked after the trial too; captured source is never executed.

The reusable single_block_steps argument defaults to None, preserving installed
defaults; explicit integers are bounded to 1--600. This delivery requests one
180-step block and the existing 600-second per-component timeout. Options
interrogation is bounded to 30 seconds and read-only checks to 60 seconds.
Failure of input checks defers that component from generation; failure to prove
the shared block contract stops the unsupported trial. No installed code is
patched, no prior pickle/partial XYZ is reused, and no tolerance is relaxed.

Candidate interpretation remains separate. Record NOT_CONVERGED_REPORTED
when the native log states geometry not converged; otherwise stopping is
NOT_REPORTED. Exit zero, a CIF file or exhaustion of attempt control does not
prove convergence. Candidates pass through the existing complete source, H,
formal-charge, stereo and numerical gates against both consumer and original
definitions. New raw unknown/alias fields remain explicit comparison evidence.
No result is composed with modifiers or adopted; native proxy, achieved geometry
and scientific qualification remain open. There are no new dependencies or
production-default changes.

### Read-only candidate and native-reader stereochemistry

Returned Cedar 33 verifies all 1,288 payloads and the complete 1,229-payload
predecessor. Both read-only inputs pass under Phenix 2.2.1-6174. DP exits one
in preparatory Chiralise/ChiralClass, before any numerical optimization or output
dictionary. The CCD reader assigns every atom token other than N, including ?,
to its native chiral marker. DP has 35 unknown atom tokens and four preserved
signed-volume declarations. No false nonchiral or invented R/S export is used
to bypass this boundary.

PDU generation exits zero after one explicit block, but reports geometry not
converged. Its candidate retains exact graph/order/H and all 38 explicit zero
formal charges, with zero retained plane/angle findings. All three original
R/S labels are omitted. Generated signed volumes agree with source ideal and
generated Cartesian hands; this is a source-relative comparison, not independent
absolute CIP assignment. Its printed 181-row energy table reaches -517.4105 at
row 146, rises to -477.2222 at row 147 and ends at -480.5612. No intermediate
coordinate trajectory is available to explain that rise.

Use the same builder with --delivery-prefix 34_Cedar --component-control PDU,
then run the generated script against the exact Cedar 33 ZIP with
--component DP --stereochemistry-audit-only. This action is mutually exclusive
with generation/read-only-contract actions. It verifies trusted build metadata,
both reader and installed-option proofs, source/consumer/candidate hashes,
generation receipts, explicit stopping and all preserved lineage. Serialized
molecule outputs stay excluded. The saved PDU chemical/numerical assessment is
recomputed from the original source before its stereo audit.

The generic stereo audit compares exact elements/orders/formal charges first.
For each declared R/S centre, it records missing/conflicting labels and every
generated ordered three-neighbor signed term. The centre must have four
declared covalent neighbors. Compute det(a-centre,b-centre,c-centre) in each
complete coordinate family; never mix families or fill missing coordinates.
The 1e-6 cubic-angstrom threshold marks degenerate volumes, not chemical accuracy.
Inversions, flattened or contradictory signed terms reject; absent/unsigned
terms, missing coordinates or omitted labels retain review. Extra generated
centres also retain review. No CIP label is inferred and no term is rewritten.

The installed phase captures Utilities.py, MoleculeClass.py, TopologyMixins.py
and ChiralClass.py under the verified library anchor (1 MiB maximum each).
Snapshots use .py.txt suffixes and the worker removes its evidence directory
from module search paths. Only selected installed module paths execute. A
maximum 30-second worker per
component reads exact source IDs/markers with chirals=False, then separately
exercises the reader's chirals=True entry point. It records constructor exceptions
without promoting them to chemical rejection. This control does not reproduce
the full builder preparation sequence. Installation, snapshot, dispatcher and
input hashes must survive; escaped/changed modules or inventory mismatches refuse.
No whole-molecule trial or dictionary writer is requested. --inspect-only performs just
the offline comparisons. New additive JSON records are source_stereo_inventories,
saved_candidate_stereochemistry, saved_optimizer_trajectories and
installed_chirality_controls. Existing production APIs, dependencies and
NARestraints policy remain unchanged; native stereo execution is pending.

The Cedar 34 return verifies all 1,320 payloads and both captured source sets.
DP retains 35 literal ? native markers and reproduces the same assertion;
PDU's three known markers and constructor pass. Captured TopologyMixins.Chiralise
calls ChiralClass.Optimise, which performs local template minimization and native
RS notation. The old optimization_execution=NOT_RUN and absolute_cip_assignment
flags did not instrument those internals. Preserve those immutable receipts and
apply this narrower interpretation; no whole-molecule dictionary trial ran.
Future constructor receipts label internals uninstrumented and distinguish
independent CIP validation from native constructor operations.

### Preserved source reader dialect

Cedar 37 uses --delivery-prefix 37_Cedar --component-control PDU, then the exact
Cedar 36 ZIP with --component DP --source-dialect-audit-only
--declared-charge-control. It preserves the completed raw reader audit and
failed Cedar 35 preflight, and verifies nested Cedar 34 source/worker/input
hashes, native marker/constructor outcomes and all previous evidence. It also
replays saved PDU comparisons and printed trajectories.

The installed dispatcher classifies any _chem_comp.id file without the literal
data_comp_list marker as chemical components. DP's original monomer dictionary
has that block; its graph export did not. The explicit adapter first recomputes the exact source-derived, target-free
graph and requires byte equality, refusing old targets/types reintroduced by
a caller. It uses parsed source blocks to preserve that reader dialect. It writes one real comp_list loop and
one component definition, restores only source metadata and equal x/y/z aliases
from the complete graph seed, and retains exact chemistry/signed chirality.
No old numerical target or energy type is reintroduced. Reject changed chemical
fields, conflicting aliases, ambiguous components and unsafe outputs. No atom
stereo/aromatic label is inferred. Original source and graph bytes stay frozen.
PDU continues through the existing CCD projection with unchanged consumer bytes.
DP's new consumer SHA-256 is
4648c37ce867cce5a285d5f31a394a334b2cb9e347936511525a947927798bfa.
This opt-in diagnostic does not change the default generator's input policy.
The returned Cedar 35 audit stopped before native parsing because its internal
graph-check temporary path traversed an OS alias. Cedar 36 resolves only the
fresh tool-owned temporary directory before the strict graph writer, so system
temp aliases work without permitting symlinked caller outputs. Regression checks
cover both source dialects and byte-identical consumers. The actual returned
temporary path was not recorded; synthetic alias tests reproduce the error.

The native worker captures selected any_chemical_format_reader.py and
monomer_library_cif_parser.py as .py.txt, removes its evidence directory from
module search paths and checks selected imports/hashes before and after parsing.
It calls the installed dispatcher with simple=True, return_all_restraints=True
and do_not_check_for_smiles=True. Unwrap exactly one molecule when the dispatcher
returns a list; empty/multiple-component returns stay review. The input contains graph and signed declarations,
without numerical targets. A maximum 30-second read per component records actual
dispatch, format, identities, elements, raw atom charge, coordinates and bond
orders. Exceptions remain review evidence. Literal readback disagreement remains
visible, including aromatic representations; no equivalence is guessed here.
The native charge attribute's semantics and signed-stereo interpretation require
the returned parser source, independently of equality checks. No chiral
constructor or whole-molecule optimizer is requested; parser internals remain
uninstrumented. Snapshot/input/dispatcher/source checks surround both controls.
The source_reader_audits receipt and SOURCE_READER_DIALECT_CONTROLS status
are additive. Returned Cedar 36 completes both native reads: PDU passes every
raw check, while DP preserves route, identities, elements and coordinates but
loses five double orders and two declared -1 charges. Its four signed markers
survive; that alone is not a complete native stereo qualification.

The captured monomer parser matches only lowercase order tokens and defaults
other spellings to single. Its atom loop reads no charge field, including
partial_charge. Cedar 37 maps explicit single/double/triple/aromatic/delocalized
orders to that exact vocabulary in the separate consumer input. Original source
and graph bytes stay fixed; chemical comparisons use declared order semantics.
No partial-charge alias is fabricated and no atom stereo label is inferred.

The additional --declared-charge-control action separately exercises explicit
formal charges on the temporary parsed component. The worker snapshots the raw
reader result first. Source-bound Utilities/MoleculeClass captures support the
native integer charge API; input, dispatcher, parser and API hashes are checked
before/after. Exact route, atom identities/elements, bond membership/orders,
coordinates and complete integer charges (absolute per-atom value <=4, matching
the captured Chargise boundary) are preconditions. A conflicting or partially
loaded native charge state blocks assignment. An otherwise zero monomer object
receives the exact source charge map by atom identity plus its sum; an already
correct CCD object is checked without assignment. Recorded coordinates, bonds,
chiral markers and signed markers must stay unchanged. The host independently
rechecks the resulting inventory/total and retains the original raw reader flags.
No chiral constructor, Chargise, perception, optimizer or dictionary writer is
called by the population control; parser internals remain uninstrumented.
SOURCE_READER_AND_DECLARED_CHARGE_CONTROLS describes this explicit request.
Returned Cedar 37 passes the isolated source-charge control for both components.
DP preserves all declared orders, and explicit population changes only OP2/OP3
from zero to source -1 on the temporary object (total -2); PDU already preserves
charges and requires no assignment. Raw DP charge failure stays visible. This
is not native stereo, full generator, achieved-geometry, convergence or
scientific qualification.
No new dependency, policy
guess, model change, refinement or adoption is introduced.


### Installed triple-bond controls

Build Cedar 38 with --delivery-prefix 38_Cedar --component-control PDU
--component-control 5PC; run against the exact Cedar 37 ZIP with --component DP
--triple-bond-audit-only. The mutually exclusive action verifies every C37
payload, source/worker/consumer hash and predecessor gate. It independently
replays both raw and controlled charge inventories. --inspect-only performs
this replay and offline dictionary screening without importing native Phenix.

The public source graph selects every explicit triple edge and all its linear
neighbors. Screening reports unique active distance/angle membership, target,
positive ESD/weight, observed geometry, preserved order and any dihedral whose
consecutive triplet contains an expected-linear angle. Carbon-carbon target
screening uses 1.10–1.30 Å; carbon-nitrogen uses 1.05–1.25 Å. Bond ESD must be
positive and <=0.05 Å. Adjacent angle targets must be 175–180°, with positive
ESD <=5°; measured bending over 5° requires review. These broad, versioned
review thresholds are not generated targets or universal chemical limits.
NIST's [acetylene experimental geometry](https://cccbdb.nist.gov/exp2x.asp?casno=74862&charge=0)
and [HCN geometry](https://cccbdb.nist.gov/expgeom2x.asp?casno=74908) provide
reference examples rather than bounds for every chemical environment. Other
triple-element pairs and unusual connectivity remain unsupported/review.

The installed resource worker binds server/cif_types imports to the selected
Phenix library, captures both APIs as .py.txt and asks only the monomer lookup
for the explicit component. A different resolved ID is unsupported. The exact
source_info file must reside inside the selected installation; freeze its bytes
and record anchored path/hash/size, with checks before/after native controls.
No basename discovery, source download, installed edit or captured-code import
is used. Absent/unsupported resources remain explicit review evidence.

Every native case uses the same separate source-ideal-seed PDB and explicit
secondary_structure.enabled=False. Compare installed lookup without overrides,
explicit captured-CIF replay (when available), and the saved C33 PDU candidate.
The native wrapper allows an empty dictionary list only with the explicit
installed_library_only=True option, rejecting simultaneous explicit overrides.
Full linked inventories retain effective definitions and active proxy details.
Component selection trims native PDB residue-name padding while preserving
literal labels in the captured inventory; two-character codes use the same
graph/proxy checks as three-character controls. No atom or component is renamed.
The report records lookup/snapshot term equality; it does not assume provenance
from equality. Per-resource timeout is <=30 s and per native case <=60 s; owned
process groups terminate on timeout. No generator, optimizer, ReadySet or
refinement runs. This is an isolated component control, not a complete replay
of ReadySet's dictionary precedence or an experimental scaffold qualification.

5PC is a second hash-pinned public graph control with C7/C8 triple names. Its
pinned workbook has two matching records; graph_only_if_ambiguous=True records
that ambiguity without choosing a role record or compiling its NA policy.
Existing controls still require unambiguous records by default. PDU's existing
pair/stack compiler checks remain fixed. No dependency or production default
changes. All results end at REVIEW; no dictionary or model is adopted.


### Installed CCD/source catalogue

Returned Cedar 38 verifies all 1,446 payloads. PDU and 5PC default monomer
lookups return no component; native interpretation stops with 38/39 unknown
energy types. The supplied PDU candidate loads with active 1.174 Å (ESD 0.020 Å)
and two 180° (ESD 3°) terms, plus six linear-axis torsion reviews. These native
controls use source-ideal seeds; the saved generated coordinates remain bent
and nonconverged. This does not identify the full ReadySet resource path.

Build Cedar 39 with --delivery-prefix 39_Cedar --component-control PDU
--component-control 5PC. Run the exact C38 ZIP with --component DP
--installed-source-audit-only. The mutually exclusive action preserves every
predecessor, verifies API/owned-worker/native input/output bytes and retains
failed lookups separately from the supplied dictionary. Independently replay
all prior mechanics, rotations, raw/controlled charge checks, source-seed models,
offline triple screens and captured active native screens. Numeric float replay
uses abs_tol=1e-8 and rel_tol=1e-10 for cross-platform libm rounding; other types,
identities, counts, state, targets beyond tolerance, hashes and bytes are exact.
--inspect-only performs those replays without native execution.

Use the verified library anchor, not a filesystem search or ambient Phenix, to
freeze the exact installed CCD paths
chem_data/chemical_components/<lowercase-initial>/data_<CODE>.cif. This is the
existing NASolve configured-CCD contract. Missing sources remain MISSING;
wrong/ambiguous chemistry remains REVIEW. Compare chemical declarations,
explicit triple edges, source coordinates/stereo and every SMILES descriptor
(type/program/version/text). Text equality/difference is descriptive. No SMILES
parser, graph assignment, target generation or chemical normalization is added.
Numerical parameterization remains a separate assessment.

Bind monomer server/cif_types imports to the selected installation and their
C38 source proofs. On fresh server objects, compare direct component-ID and
residue-name lookups; record root_path/geostd_path, full available component rows
and exact anchored source bytes. DG/DC are separate canonical resolution
controls recording resolved metadata/provenance, without parameter comparison.
Utilities must match its prior verified source. Capture its exact
GeoStd/monomer helper modules, one unambiguous Python layout of
mmtbx.chemical_components, and the selected ReadySet dispatcher as text. No
captured source, route helper or ReadySet dispatcher is executed. Missing
optional helper source layouts are recorded. All paths must remain beneath the
selected installation; source/API/snapshot/dispatcher/reference hashes are
checked before/after. No pickle or network source is consulted.

Installed CCDs with a valid declared graph also pass through the existing simple
native source reader, retaining raw format, atom/bond/charge/coordinate readback
and exact parser snapshots. These are independent of the absent numerical
monomer resources. The catalogue worker and each reader have <=30 s deadlines;
owned process groups terminate on timeout. INSTALLED_MONOMER_CCD_SOURCE_CONTROLS
records the request. No constructor, optimizer, generation, native geometry
trial, experimental model edit, refinement or adoption occurs. Curated
precedence and NARestraints pairing/stacking authority are unchanged, including
5PC's unresolved duplicate records. Complete ReadySet selection, mapped-SMILES,
stereo, numerical and scientific qualification remain open.

Returned Cedar 39 verifies all 1,486 payloads and the trusted clean published
runner. Both installed CCDs preserve public declarations and all SMILES text;
all six raw reader checks pass per component. Both direct/wrapped monomer
lookups are missing, while DG/DC canonical resolution succeeds. CCD numerical
parameters remain UNASSESSED; descriptor graph mapping and ReadySet remain
NOT_RUN. No historical SMILES or floppy-chain cause is established.

Build Cedar 40 with --delivery-prefix 40_Cedar --component-control PDU
--component-control 5PC. Run the exact C39 ZIP with --component DP
--readyset-source-audit-only. The new mutually exclusive action replays all prior
mechanics, rotational, raw/controlled source-reader and triple-proxy evidence,
plus both installed/public CCD comparisons and raw CCD inventories. --inspect-only
performs those checks without native execution.

Resolve exactly one literal $LIBTBX_PREFIX/...py target from the captured,
hash-matched ReadySet dispatcher. The target must stay beneath the selected
Python library. Copy it and bounded literal elbow/mmtbx imports of ReadySet-named
modules as text: at most three levels, 32 files, 1 MiB/file and 8 MiB total.
Direct helper sources are captured without recursive execution. Record missing
literal targets and budget limits; dynamic and complete transitive source
coverage is not claimed. No ReadySet module or captured code is imported.

A separate worker uses selected Phenix Python and the C39-proven
mmtbx.chemical_components module. Verify get_cif_filename against each exact
captured CCD resource before calling get_smiles. Retain the exact selected text
and matching descriptor type/program/version records. SELECTED_DESCRIPTOR_MATCH
means only text membership; graph mapping and numerical targets remain separate.
The worker has a <=30 s deadline and an owned timeout group. All selected API,
dispatcher, resource, reference and snapshot bytes remain checked before/after.
INSTALLED_CCD_DESCRIPTOR_SELECTION_ONLY records this native scope. ReadySet
execution, constructors, generation, optimization and model edits remain
unrequested; no numerical target, NAR policy, production default or adoption
changes. Saved PDU torsion reviews and the two ambiguous 5PC records survive.

Returned Cedar 40 verifies 1,529 payloads and the trusted clean build. Both
native CCD accessors select CACTVS SMILES_CANONICAL text, and 24 static sources
fit the literal-import budget. This is not executed ReadySet provenance. One
captured branch deletes its temporary SMILES and requests chemical_component;
Cedar 41 records the preparatory file-input call, then fails before reaching
that later branch: leaked wrapper PHIL options cause eLBOW's options parser to
raise SystemExit 2. All 1,624 returned payloads verify. Each receipt worker exits
zero after recording the native exception; ReadySet itself does not complete.
Both surviving CIFs exactly match the public CCD sources, without numerical
targets, and native interpretation remains NOT_RUN. Missing terms in these
preparatory copies do not establish a generation defect or historical cause.

The returned Cedar 42 capsule verifies all 1,747 payloads and the clean
published runner. Both file-input eLBOW calls and isolated ReadySet invocations
complete with no SMILES argument. PDU/5PC generated and active native targets
pass: lengths 1.203/1.186 Å with 0.020 Å ESD, and both linear angles 180° with
3° ESD. Native evaluation uses fixed public source seeds, not an optimized
linked model. Six generated/three active heavy-atom linear-axis torsions each,
source-relative chemistry and 5PC's angle/plane review remain open.

Cedar 42 used --readyset-generation-audit-only on the exact C41 ZIP. DP remains a preserved prerequisite; the new
generation cases are PDU/5PC only. --inspect-only replays saved evidence and
writes complete/heavy source-seed controls without native execution.

The selected Phenix interpreter calls the original ReadySet run API under
prior source/hash proofs. The v2 invocation keeps explicit ReadySet API arguments
out of process argv, matching the captured native entrypoint's separation.
Nested builder calls retain their original kwargs and reparse empty process
options. Each observer records argv; the installed options parser is also hash
checked and captured. The exact C41 failure is preserved and its source-copy
triple screens and complete/heavy seed models replay without executing old code. Heavy-atom inputs use hydrogens=False, ligands=True,
optimise_ligand_geometry=False, optimise_final_geometry_of_hydrogens=False,
trust_residue_code_is_chemical_components_code=False, metals=False,
link_to_edits=False and remove_waters=False. The shell dispatcher is not run.
No user CIF/cache is supplied; the ReadySet cache environment variable is
removed and bytecode writes disabled. Internal native template operations can
still optimize geometry and are recorded as NOT_INSTRUMENTED.

Process-local observers record builder/template arguments, caller source/line,
returned graph snapshots or exceptions while forwarding original arguments,
return objects and exceptions. Atomic logs survive a 180 s owned-process-group
timeout. Trace truncation at 64 events remains explicit; nonfinite native values
become trace markers without changing native objects. Preserve process failure,
ReadySet failure, caught builder errors and fallback dictionaries separately.
Select only the exact owned <CODE>.cif. Compare its bytes to the explicit
source and record UNCHANGED_SOURCE_COPY, PARTIAL_OR_UNQUALIFIED_OUTPUT or
COMPLETED_READYSET_OUTPUT. RECORDED means only file presence. Process success
alone or an unchanged source never establishes numerical generation. Native
success plus a changed output still requires independent qualification.
The console prints worker outcome, native outcome/error and file classification
separately. Serialized outputs are never loaded and remain excluded from review
capsules. Malformed, missing and partial candidates
stay review evidence; only completed policy-matched output proceeds to native
interpretation, capped at 60 s per control with SS inference disabled.

Retain raw source/dictionary graph, charge, hydrogen and stereo differences,
plus dictionary and native triple-target/linearity/ESD/membership/torsion screens.
The native model uses fixed source-ideal heavy-atom seeds. Full-reference
hydrogen-inventory differences remain visible even when the selected triple
terms pass. No convergence, all-chemistry, linked-scaffold or adoption approval
is inferred. Production defaults and NARestraints authority stay fixed.

5PC already has two cytosine-sheet records with equal C-like atom roles. The
component-control auditor now compares every operational atom mapping and
base/sugar/phosphate/Saenger/function/sheet/glycosidic context before allowing
equivalent aliases to compile once. All raw records remain in the report;
conflicting records and missing atoms remain blocked/reviewed. Explicit C5-mod
and C7-mod annotation columns are excluded, consistent with upstream mirror
metadata handling. Prefer an available canonical partner from registered
recipes before modified-family synthetic controls: 5PC exercises existing G:C
and both stack orders. No NARestraints table edit, package release or recipe
change is required; the conditional missing-entry case was not present.

Cedar 43 used --torsion-conditioning-audit-only on the exact C42 ZIP. This mutually exclusive action replays the
completed generated/native triple screens and all earlier prerequisites, then
evaluates only existing graph-selected heavy-atom dihedrals. The prior native
inputs are reached through exact reviewed relative anchors and hashes; old
absolute paths are provenance only. Captured code never executes.

The new cif-native-linear-axis-dihedral-conditioning-v1 module rebuilds the
exact captured manager before evaluating selected single-restraint and
singleton-container kernels. All atom/definition/proxy/API/policy inventory
fields match C42, six numerical module/binary hashes are pinned, and special
positions, symmetry-bearing torsions or nondefault limit/top-out/slack functions
are refused. Every original target, weight, periodicity and alternate remains
unchanged. Complete manager signatures and installed hashes are rechecked.

Cases use the saved native source-seed coordinates and generated dictionary
Cartesian coordinates at full precision and separately rounded to 0.001 Å.
Perturbations are temporary numerical evaluations; no model is written. At each
selected four-atom proxy, test all 12 Cartesian directions and the nonzero
single-gradient direction with six central-difference steps (10^-3…10^-8 Å).
Retain every step and require two adjacent agreeing steps per direction for
sampled agreement, with absolute/relative tolerance 10^-4. Record single versus
container energies/gradients, repeats, reversed order and the original function
parameters. Nonfinite values and native exceptions remain explicit JSON evidence.

Normalized cross-product sines describe each defining plane. A minimum sine
below 10^-3 raises descriptive near-collinearity review; this is not a universal
chemical cutoff or a removal policy. Exactly zero plane geometry is undefined,
even if native code returns a finite residual or zero gradient. Independent
nonchemical bent/exact-collinear controls and radius/phase profiles approaching
collinearity inspect this distinction. Bound each component to 3,000 paired
single/container evaluations (at most 6,000 kernels), plus a 180 s owned-process
deadline. Returned C43 completes both controls at 1,603 pairs each. All 234
real-coordinate directional checks independently recompute; every selected
torsion remains near-collinear. The 5PC full-precision maximum single gradient
norm is 578,927.34. Fixed-phase gradients grow approximately as inverse radius
in approach controls, and exact-collinear zero gradients remain undefined.
Correct sampled derivatives do not establish useful conditioning. The
--inspect-only action performs saved-evidence preflight without native kernels.

Retain the raw 0→−2 charge and HOP2/HOP3 loss, omitted R/S declarations,
source-relative stereo rejection and all other numerical findings. Passing
triple targets does not approve those generated changes. No ReadySet, dictionary
generation, optimizer, refinement, restraint removal, adoption or production
default change occurs in this action. Historical floppy-chain causation stays
unestablished.

Cedar 44 used --linear-torsion-candidate-only on the exact C43 ZIP. The exclusive action verifies all 1,794
payloads, replays saved directional arithmetic and preserves the entire prior
lineage without executing captured Python. Reach scientific inputs only via
reviewed relative anchors/checksums.

The cif-declared-linear-torsion-candidate-v1 preparation requires explicit C-C
or C-N triple orders, unique exact 180° flank targets with positive ESDs, and
supported unique consecutive torsion paths/finite parameters. Select rows only
from those declarations, never coordinate thresholds or code/atom-name lists.
Write a separate CIF omitting the six complete selected rows per control.
All other parsed values, including unknown fields, must compare exactly;
unmodified blocks retain original text. Affected blocks may reformat. Invalid
or ambiguous declarations refuse preparation before the candidate is written.
No production repair recipe is added and no source is overwritten.

Fresh original interpretation must match C43 atom/definition/proxy/API/policy
inventories. Candidate interpretation must match an expected inventory formed
only by removing the six effective-definition torsions and three matching active
heavy proxies/counts. Every other field, including charges, stereo, coordinates,
triple bonds, angles, planes and unrelated torsions/proxies, stays exact; any
extra inferred term or changed field remains REVIEW. Native triple-target
screens must still pass and no linear-axis torsion may remain. Each inventory
has a 60 s deadline. Returned C44 completes all four interpretations and passes
both exact comparisons. Active dihedrals change 28→25; the eight constant
dihedrals and every unrelated inventory field remain unchanged. Both native
triple-target screens pass with no remaining linear-axis torsion.

Keep phosphate 0→−2/HOP2/HOP3 differences, omitted R/S metadata and 5PC plane
findings open. This candidate does not select chemistry or prove a lower total
gradient, convergence, historical causation, scaffold suitability or adoption.
No ReadySet, generator, optimizer, model writer, refinement or installed edits
run. Explicit NARestraints pairing/stacking authority is unchanged.

Cedar 45 used --linear-torsion-impact-only on the exact C44 ZIP. Verify all 1,847 payloads and replay the candidate
plan/bytes, exact native delta and dictionary/native triple screens using
current maintained code. Preserve all earlier evidence, including C43 arithmetic,
without executing captured Python. Inputs use reviewed relative anchors/hashes.

The cif-fixed-linear-torsion-numerical-impact-v1 worker rebuilds separate
original and candidate managers under the exact captured C44 inventories. Pin
six numerical module/binary hashes and selected-installation geometry/flex
adapters. Refuse special positions or nonzero parallelity proxies in this
isolated slice; the qualified plane correction remains untouched. Preserve both
complete static signatures and all input/installed hashes before and after.

At the same three saved coordinate cases, record original/candidate full and
seven family-control targets, Cartesian gradients and proxy counts. Repeat all
baselines before and after temporary perturbations. Full/dihedral original-minus-
candidate differences must equal the saved three single-torsion sums, scattered
into full vectors by exact native indices. Bond, angle, chirality, planarity,
parallelity and nonbonded values must remain equal; family sums reproduce each
full target/gradient. Absolute/relative repeat/delta tolerances are 1e-8/1e-10.

For the candidate full and dihedral objectives, sample the 18 Cartesian axes of
the six atoms selected from omitted-proxy endpoints, alternating-global,
nonzero full-gradient and dihedral-gradient directions. Six central steps
(1e-3…1e-8 A) retain raw values and require two adjacent consistent steps with
absolute/relative 1e-4 tolerance; sample proxy counts must equal their baseline.
Cap each control at 2,000 energy evaluations and 180 s. Norm changes are
reported descriptively, not required to decrease. Numerical agreement is not
scientific approval, convergence, historical causation or scaffold validation.
Returned C45 passes all 246 arithmetic directions and numerical-delta checks.
PDU passes every strict case; two 5PC cases retain count-only repeat/combined-FD
review (71→75 and 70→67), with exactly unchanged repeated energies/gradients.
Actual pair identities/contributions remain unrecorded; cache interpretation is
an inference until native proof. Original failures remain preserved. No generator, optimizer,
coordinate model, state selection, installed edit, refinement or adoption runs.

Build Cedar 46 with --delivery-prefix 46_Cedar --component-control PDU
--component-control 5PC and run the exact C45 ZIP with --component DP
--nonbonded-cache-audit-only. Verify all 1,910 payloads and reconstruct the raw
C45 call sequence with maintained code. Recompute every baseline, repeat,
difference and finite-difference comparison, retaining the original count and
combined-direction failures; captured Python never executes.

The cif-native-nonbonded-cache-proof-v1 preflight rebuilds both exact managers
and records two full/family cycles at each saved case. Inspect the actual native
energy object's pair list without another manager lookup that could rebuild it.
Record canonical identities, VDW distances, prolsq parameters, raw cache state,
per-pair native residuals/gradients and a separate native container evaluation.
Require pair sums to reproduce container target/gradient and the manager's
nonbonded target. Shared pair parameters/contributions must remain unchanged;
added/removed pairs require exactly zero residual and all six gradient entries
exactly zero. Missing, duplicate, nonfinite, ASU or nonidentity-symmetry pairs
and unsupported functions refuse qualification. Capture installed manager.py,
energies.py and available nonbonded header/binding text with before/after hashes;
public source is API context, not a substitute for installed evidence.

Require settled full/nonbonded and original/candidate memberships, with unchanged
full targets/gradients. A failed proof blocks the strict retry for that case.
Otherwise rerun the unchanged C45 routine after preflight, retaining its original
count/tolerance/delta/derivative gates, and additionally require stable pair
identities and function parameters through every active evaluation. Preserve
both static signatures, all six pinned numerical sources and selected-root
adapters. Bound each control to 2,000 manager energy calls plus 5,000 single/
container pair kernels and 180 s. Returned C46 verifies all 1,983 payloads
and passes both components in all three saved cases: 1,716 manager calls each,
1,758 pair kernels for 5PC and 1,528 for PDU. Independent offline replay checks
all 48 raw pair-transition proofs, 246 strict derivative directions and the
exact prior capsule. Four added 5PC pairs and three removed pairs have exactly
zero energy and six zero gradient components; shared pairs and native sums stay
unchanged. Both static signatures and all installed/input hashes are preserved.
The pinned worker reports stable membership throughout finite differences;
raw perturbed pair lists are not stored for independent identity replay.
Installed cache source now records the flag/displacement rebuild route and
effective cutoff/buffer state. Historical C45 count failures remain preserved.
Charge/H, stereo, plane/angle and scaffold findings stay open. No chemistry,
restraint, model, optimizer, state choice, installed defaults, NARestraints policy
or adoption changes.

Build Cedar 47 with both public controls and run the exact C46 return using
`--component DP --source-constructor-audit-only`. The return gate verifies all
1,983 payloads, build, worker/helpers, scientific inputs, installed source text
and both static signatures; maintained code recomputes 48 pair proofs and 246
strict derivative directions without executing captured Python. Perturbed
membership remains explicitly scoped to the pinned worker result.

The `cif-source-native-constructor-handoff-v1` worker uses the declared source
reader route for DP, PDU and 5PC. Retain raw reading, apply the checked explicit
source-charge control, promote using native `return_molecule_class(simple=False)`
and require an identical inventory. Call the selected native `Chiralise` with
its default arguments. Retain completion, exceptions and complete after-inventory.
Check exact identities/elements/orders/charges, source R/S and signed metadata,
unaccounted new centres and nondegenerate source-relative coordinate hands,
including applicable declared signs. Explicit `both` remains permissive, while
fixed sugar/R/S hands stay protected. Report coordinate shifts descriptively;
proper rotations/translations do not change a hand. Unknown or incomplete
stereo cannot pass by absence. No absolute CIP is independently assigned.

Pin the prior six reader/charge/chirality modules and newly capture the selected
SimpleMoleculeClass source as text. Verify actual import/method origins and
supported signatures, clear wrapper argv before installed imports, and recheck
all installed/captured/input/dispatcher hashes. Each owned process is capped at
60 s and terminated on timeout/interruption; at most three components run.
The native constructor can optimize local chiral templates internally, which
this audit does not instrument. Whole-molecule optimization, the complete
builder, numerical dictionary generation and scaffold changes are not requested.
Returned C47 verifies all 2,036 payloads and retains three constructor
exceptions. DP/PDU stop with `not chiralised`; 5PC reaches missing legacy
`OptimiseBFGS`. Source graph/charge, promotion and marker gates pass. The probe
omitted native CCTBX selection, which the captured Utilities reader performs
at lines 605–606 immediately before Chiralise. C47's missing after-format on
exception is retained as unreported, not evidence of route mutation.

Build Cedar 48 with both controls and run exact C47 with `--component DP
--source-constructor-backend-audit-only`. The new
`cif-native-chiral-cctbx-preparation-v1` opt-in policy checks that native reader
sequence by AST, resolves bound setter/getter origins and supported signatures,
captures their selected installed source text and rechecks hashes. Record flags,
format and full state before/after `SetCCTBX(True)`; require the true flag and
exactly unchanged chemistry/coordinates before original Chiralise. Preserve
all graph/charge/marker/hand gates, with four additional backend gates. Capture
after-format on exceptions too. The legacy default remains false and old C47
qualifications replay exactly. Each owned process retains its 60 s cap.

Verify/recompute all three original failures and earlier prerequisites before
retrying byte-identical original consumers. Failed C47 coordinates are never
reused. Returned C48 verifies 2,092 payloads and completes all three constructors
under Phenix 2.2.1-6174. All backend/graph/charge/marker/route checks pass;
source-relative hands remain reviewed at DP/5PC C1-prime and PDU C1/C3/C4-prime.
All-basis offline checks add DP C4-prime and a mixed-basis 5PC C4-prime finding.
Preserve original measurements; temporary template orientation is not an
independently assigned absolute CIP or complete-molecule verdict.

Build C49 with both controls; run exact C48 with `--component DP
--source-constructor-trace-audit-only`. The new
`cif-native-chiral-boundary-observation-v1` module compares separate fresh
unobserved/observed native constructors. Pin all original inputs/APIs and
C48's ChiralClass/CCTBXMixins sources. Observe outer/local Chiralise,
GenerateZMatrixClass, GetRestrainedParameters, TightenRestraints, Optimise,
GetRSNotation and OptimiseCCTBX using process-local wrappers forwarding the
original call once. Capture resolved arguments, scalar native R/S returns,
available minimizer error fields, full parent snapshots, local order/index/
coordinates and live parent-object-sharing flags. Restore class methods in
finally and recheck installed sources. No optimizer kernels are instrumented.

Recompute nesting/scope/budget, exact chemical continuity, finite states,
shared-coordinate consistency, restoration and outer endpoints. Compare every
ordered triple of four graph neighbors and their four-neighbor determinant to
the declared source, retaining permissive both. Report preexisting findings,
first observed reviewed boundaries and adjacent changes, not a unique causal
step. Live object identity/forwarding remain pinned-worker evidence; offline
JSON replay cannot independently prove Python object identity. Fresh-repeat
endpoint equality and agreement with C48 are separate from stereochemistry;
random state is not reset, and differences remain REVIEW. Limit six owned
30 s workers and 256 observed calls each. Returned C49 completes six native
constructors and matches all fresh and earlier C48 endpoints exactly. The
original hand warnings remain. DP native chiral markers change while signed
volume metadata survives, so its trace chemical-metadata gate stays REVIEW;
PDU/5PC trace replay passes. First boundary timing does not prove a causal bug.

Build C50 with both controls; run exact C49 with `--component DP
--source-constructor-mapping-audit-only`. The additive
`cif-native-local-coordinate-mapping-v1` policy independently replays all six
prior qualifications, raw trace/source-definition evidence and three fresh/
previous comparisons. Restart original sources and preserve the old failures.
Observe selected native GetCoordinates, SetCoordinates and GetNewManager in
addition to existing hooks. Record original vectors and named local/global
indices, original local order/input volume/equil/marker, and actual native
chirality proxy i_seqs, volume_ideal, weight and both_signs. Original arguments,
returns, kernels and source files are unchanged; methods are restored.

Replay exact getter order and setter writeback with unchanged outside atoms.
Map each actual indexed proxy basis to source names and compare signed source
volume to the native target, retaining both-sign uncertainty. Separately report
the observed sorted-index transfer between final tightening and R/S inspection
and source-relative local hand before/after. Shared parent coordinates can mix
temporary local frames; no completed-molecule or causal-bug claim follows.
Original hand and metadata gates remain active. Six owned 30 s workers, 256
calls/512 boundaries each, and 64 rows per captured vector/proxy list bound
execution. Unsupported native shapes remain REVIEW. Returned C50 passes all
18 getter/nine setter checks, exact fresh/previous comparisons and nine sorted-
index transfer comparisons. Its local-order proxy basis remains reviewed. A
separate sorted-name hypothesis matches all source graphs and PDU/5PC signs,
with DP C1-prime still opposed; it does not prove native array conventions.

Build C51 with PDU/5PC plus independent ATL; run exact C50 using `--component DP
--source-constructor-index-basis-audit-only`. Preserve/replay every prior raw
trace, mapping report, qualification and comparison. The additive
`cif-native-named-restraint-index-basis-v1` observes native dictionary atom keys,
indices, stored coordinates, parent sharing and original returned coordinate/
chirality parameters at existing GetRestrainedParameters exits. Capture and
pin selected RestraintClass.py/geometry_manager.py plus original constructor
sources. Fingerprint the bound GetRestraints and module factory sources;
never call GetRestraints again just for observation.

Prove complete named keys, unique stored vectors and exact alignment with native-
index ordering. Separately retain actual local getter order and proxy/target
interpretations in both arrays. Existing hand/metadata gates and local-order
reports stay active; no evaluation array or target changes. Limit native
dictionaries to 256 entries, sequences to 64 and the original six 30 s workers.

ATL's pinned public source adds a bridged-sugar/four-centre and existing T-class
NARestraints compiler control, with native execution NOT_RUN. Third public
controls are separate read-only sources in this action, outside native cases
and generation. No workbook/release, standard-DNA pucker assumption, scaffold,
recipe or planned eight-pair changes. Native index proof, source charge/H,
absolute stereo, 5PC planes, full generation and scientific approval remain open.

CIF Doctor assesses component dictionaries without changing their chemistry or
the model. It runs offline, using NASolve's existing CIF reader and lightweight
graph and numerical checks. It does not require an LLM, RDKit, a generator or
Phenix. The larger scientific design remains in
[the audit methods](cif-restraint-audit-methods.md) and
[the implementation map](cif-restraint-doctor-implementation.json).
For a plain-language explanation, methods paragraph and editable publication
figure, read [the human/manuscript overview](cif-doctor-human-overview.md).

## Commands

Assess explicit dictionaries, optionally against a PDB atom inventory:

```bash
./nasolve cif-doctor assess /path/to/component.cif --stage source --json
./nasolve cif-doctor assess /path/to/effective.cif --stage effective \
  --model /path/to/model.pdb --output /path/to/new-audit.json
```

Assess the exact frozen bundle at a completed run's selected checkpoint:

```bash
./nasolve cif-doctor assess --run /path/to/AutoMR/run_001 --json
./nasolve cif-doctor assess --run /path/to/AutoMR/run_001 \
  --checkpoint refine-002 --output /path/to/new-audit.json
```

The run adapter reads existing state without creating a checkpoint registry,
changing the selection or rewriting any artifact. It verifies frozen model,
observation and restraint references through the existing run-context resolver.
An explicit checkpoint ID or bookmark takes precedence over the current one.
It never falls back to a similarly named file after an integrity failure.

Compare an explicitly selected source with a same-code candidate:

```bash
./nasolve cif-doctor compare /path/to/source.cif /path/to/candidate.cif --json
```

The comparison records exact atom, bond, aromatic, hydrogen, charge and declared
stereo differences. It reports which fields differ without choosing the correct
chemistry or guessing an alias, tautomer or linked-state transformation. Formal
and partial charge fields remain separate; an unspecified charge is not zero.

Exit codes are `0` for the implemented checks passing, `2` for review/unassessed
evidence, `3` for an invalid assessment and
`1` for an operational error. A passing dictionary check is not scientific
approval, native interpretation or geometry qualification. Missing numerical
restraints in an ordinary CCD construction graph remain explicitly unassessed;
in an effective refinement dictionary they need review.

## Pipeline placement and receipts

New PostMR executions produce three JSON receipts under `PostMR/Restraints`:

- `cif_doctor_mutation.json` when mutation dictionaries are required: exact target construction dictionaries before
  coordinate normalization or Coot mutation, with audit-only source snapshots.
- `cif_doctor_source.json`: frozen source definitions and a separate assessment
  of runtime inputs immediately before ReadySet.
- `cif_doctor_effective.json`: the actual selected effective bundle and final
  ReadySet model, after dictionary precedence/normalization and before readiness.

PostMR reports reference these receipts by anchored path, size and SHA-256 and
retain their summaries. Source and effective dictionaries remain separate;
the source and its derivative are not misreported as simultaneously loaded
competing definitions. Already-present curated modifications enter the source
and effective audits even when no mutation is requested.

This first deployment is report-only. The existing identity, phosphate,
parameterization and precedence checks still own continuation. Audit findings
do not silently change ReadySet inputs, start a repair or add a campaign gate.
Old runs remain unchanged and can be assessed with the command above.

Receipts use schema version 1, `audit_kind` and a versioned policy. They contain
ordered, hash-bound input descriptors, component inventories, stable rule IDs,
raw measurements and explicit unimplemented layers. Run receipts have portable
references; standalone receipts declare their input root for explicit replay.
Native proxies, site-specific link chemistry, sugar-pucker interpretation,
achieved geometry and map support are not certified by a source-file assessment.
Zero-sigma torsion annotations are inventoried under the native inactive-term
convention, with actual proxy activity still unassessed. A `CONST` name alone
does not determine activity. Signed periodicity remains visible rather than
being converted into a guessed sugar-pucker or Gaussian-sigma conclusion.

## Integer-key constructor observation (Cedar 52)

The returned C51 named-index audit verifies 2,395 payloads and six completed
constructors, with fresh/previous endpoint agreement. Its nine atom-key captures
are empty because native RestraintClass stores integer index keys. This is an
observer mismatch and does not establish a molecular stereo failure.

The existing explicit `--source-constructor-index-basis-audit-only` action now
also accepts the exact C51 return. C51 input enables opt-in
`cif-native-integer-restraint-keys-v2`; exact C50 input retains v1 behavior.
Record native integer-coordinate entries, existing link positions and named
local atoms, preferring unique_index over index as the selected source does.
Require complete unique inventory/identity/position agreement, source-proved
key/coordinate methods and exact returned vector alignment. Keep actual local
getter order separately visible; no extra native getter call or computation
rewrite occurs. Original v1 empty-key, hand and marker findings replay unchanged.
Bounds remain six owned 30 s workers/256 calls each, 64-row vectors and 256
restraint entries. ATL stays a separate source/compiler control. Returned C52
passes all nine bindings, all six PDU/5PC source target signs and exact repeats;
DP C1-prime and original temporary hand/marker warnings remain. This does not
establish assembled-molecule inversion or production adoption.

## Native input-coordinate setup (Cedar 53)

The selected eLBOW builder calls native Setup before Chiralise. Setup stores
input_xyz plus serial/input-index metadata; native R/S handling can consult
those original coordinates. C53 tests this preparation in the isolated native
constructor via `--source-constructor-setup-audit-only` on exact C52. It does not
replay all intervening builder chemistry or establish a causal bug.

Capture/pin builder.py and the existing native SimpleMoleculeClass.Setup source.
Recognize unconditional same-object Setup before Chiralise without a molecule
rebind. Call the original zero-argument method once per fresh worker and require
unchanged complete component/format and exact retained input coordinates.
Record cache presence/values/alias context before/after preparation and after
construction. Preserve source/input bytes, native targets/kernels and all old
qualifications. Recompute setup qualification independently from temporary hand,
metadata and index/target-sign evidence; no absolute CIP is claimed.

Separate fresh prepared control/observed workers retain the original constructor
arguments and integer-key observation. Fresh observer agreement remains required
evidence; change against the old unprepared C52 endpoint is reported separately,
not required to be identical. Six owned 30 s workers/256 observed calls remain
the bounds, with ATL still public source/compiler only. Returned C53 passes
all six setup/cache qualifications and fresh comparisons. All nine source target
signs agree in the proved native integer basis. DP changes from the unprepared
endpoint, PDU/5PC do not; temporary hand/DP marker warnings remain. C53 does not
execute full generation or adoption.

## Complete source-native candidates (Cedar 54)

`--source-candidate-generation-only` accepts the exact C53 return, recomputes its
setup/index/trace findings and preserves every earlier capsule. DP, PDU and 5PC
restart from exact source-dialect consumer bytes, not temporary template frames.
The adapter reads the source, transfers only explicit declared charges and
promotes the native object. A pinned existing run API bypasses file reparsing for
that supplied object; native run performs its own Setup and complete builder.

One explicit 180-step installed optimization block and a 600-second owned worker
bound each candidate. The native CCTBX preparation, source-retention selector,
original chiral treatment and unchanged native kernels/tolerances are explicit.
Source coordinates seed naming/initial geometry, not independent validation or
experimental model fitting. A written regular candidate is retained even when
convergence is unreported, the optimizer stops early or a later native call
raises. Logs, hashes and stopping evidence stay distinct from chemical approval;
pickle files are hashed as excluded outputs and never transported or loaded.

Complete output is assessed for graph/elements, hydrogen attachments, explicit
charges, stereo declarations and numerical coverage. Finished source-relative
configuration uses fixed named four-neighbor tetrahedra; central-atom deformation
or pucker alone does not reverse that configuration. Missing/degenerate evidence
remains unassessed, without asking the student to review CIFs. Known chemical
changes/opposite configuration exclude that candidate from later automatic
selection. Native proxy usability, absolute CIP, fallback adoption and solution
PDF rendering remain separate adapters; C54 does not install a dictionary or
change a scaffold. ATL remains a public source/compiler control. Returned C54
completes all three builders on Phenix 2.2.1-6174, preserving explicit charges
and all nine finished source-relative configurations. PDU reports nonconvergence;
DP/5PC stopping is unreported. DP retains four plane/angle findings and its raw
rejection for one omitted phosphate `both` volume term; fixed sugar definitions
match. These results do not certify native proxy usability or linked adoption.

## Saved candidate native usability (Cedar 55)

`--candidate-native-usability-only` accepts exact C54 and replays every retained
source/API/output hash and preceding qualification with maintained code. It
reuses frozen source and generated dictionaries/models without running a builder
or optimizer. Raw legacy inspection and stopping evidence remain unchanged.

The general reassessor distinguishes fixed signed chirality from a source
unoriented `both` volume term. An omission can proceed only when every fixed
hand is intact, no source R/S centre loses its fixed term, explicit charges and
chemistry match, and no actual opposed finished configuration is demonstrated.
This is an explicit mechanical difference, not equivalent restraint mechanics:
all four native bonds and six angles at the omitted centre must remain active.
There is no component-name or phosphorus exception.

**Methods.** At source-seed and generated-output coordinates for each of three
components, interpret the saved dictionary with guessed secondary structure
disabled. Pin the selected flags, energy and manager source files. Require exact
model identities/coordinates, complete monomer mapping, six effective-definition
categories, declared bond orders and active bonds, angles, torsions, planes and
signed chirality. Compare fixed covalent targets/weights by atom name across the
two cases; dynamic nonbonded pair membership is not a covalent signature. Check
two unnormalized native energies/gradients for finite complete values and
repeatability (absolute 1e-8, relative 1e-10). Six workers have 60-second deadlines,
with twelve energy calls total and no magnitude cutoff or objective ranking.

Feed verified qualification to `cif-automatic-usable-fallback-v1` for the isolated
generated-candidate pool. Usable nonconvergence/unknown stopping yields notes;
unusable generated output is unselected while existing production dictionaries
remain intact. This does not prove another fallback usable or stop an ordinary
NASolve run. Native formal-charge access can be unsupported and stays explicit;
a contradictory available formal charge fails. Partial charges do not replace
formal declarations. DP ligand and PDU/5PC non-polymer metadata, triple-axis
torsions, geometry findings and absolute CIP remain recorded boundaries before
linked adoption. Returned C55 supplies six completed native interpretations and
twelve finite, repeatable energy/gradient evaluations. The original auditor's
roundoff/constant-torsion failures remain recorded below. The default native worker is
byte-identical unless the new energy-inventory opt-in is enabled. Students are
not asked to inspect CIFs; production recovery/adoption and PDF rendering remain
separate integration work.


## Corrected saved native usability (Cedar 56)

All 2,760 C55 payloads verify, including the complete C54 parent. Six Phenix
2.2.1-6174 interpretations complete; twelve native energy/gradient evaluations
are finite and repeat exactly. The v1 auditor mistakes 0.89e-15–3.55e-15 A
Cartesian roundtrip differences for model changes, rejects zero-weight native
constant torsions and raises ZeroDivisionError on their declared zero ESD.
These six REVIEW records and three NO_USABLE_DICTIONARY decisions stay intact.

`cif-isolated-candidate-native-usability-v2` corrects the representation checks.
Native/hierarchy arrays must have complete finite 3D coordinates agreeing within
1e-12 A absolute tolerance. Exact atom identities, model/input hashes, effective
definitions, chemical state and actual coordinates are preserved. Every declared
period-zero/zero-ESD row must match the native constant-dihedral container,
zero weight, named atoms and target. Positive-ESD active restraints still require
positive weights; missing terms or unexpected zero-weight rows fail. The 27 DP,
10 5PC and nine PDU constant rows per coordinate set are retained, not deleted.

**Methods.** Canonicalize a torsion by sorting its two outer names and its two
central names independently, reversing the target/alternate angle signs for
each swap. Keep weights, integer periods and container membership fixed. This
matches the signed permutations observed in native proxy sorting; changing only
a target or period still fails. Compare static covalent signatures across both
coordinate cases in the same named basis. This changes audit interpretation,
not CIFs, proxies, target mechanics or native kernels.

Corrected replay passes all six saved cases. DP has the required four bonds and
six angles around its omitted `both` term. All three isolated generated
candidates yield CONTINUE_WITH_NOTES. Nonconvergence, unreported stopping,
geometry findings, unsupported native formal-charge access, absolute CIP,
phosphate state and ligand/non-polymer classification remain separate evidence.
Finite gradients, including large gradients, do not establish convergence or
scientific approval. Energies are not ranked across components or coordinate
cases; linked adoption and production recovery remain separate integration work.

`--saved-native-usability-only` accepts exact C55 and validates preserved native
receipts, unchanged inputs, output hashes, the original native worker/spec and
selected energy source snapshots before maintained-code replay. Captured Python
is never executed. There are no new native calls, generation or optimization.
The pure decision core receives corrected verified evidence within the isolated
generated pool, while old failures remain alongside it. No student CIF approval
or dictionary adoption occurs. Every original capsule remains unchanged.

## Source-declared DNA metadata (Cedar 57)

Returned C56 verifies all 2,774 payloads, six saved usability passes and three
CONTINUE_WITH_NOTES decisions. Its capsule, runtime archive and complete parent
lineage replay without new native calls. The reported runner differs from a
clean build only in NARestraints working-tree metadata; reconstructing that
field reproduces its SHA with equal runtime bytes.

The source declarations identify DP as DNA through its monomer-library group
and PDU/5PC as DNA linking through CCD type. Generated dictionaries instead
write ligand/non-polymer groups and omit type. All six existing native
interpretations already classify the monomers as DNA. This is a written-header
restoration, not a claim that Phenix failed to recognize DNA.

**Methods.** `cif-source-declared-dna-metadata-v1` requires explicit consistent
source declarations and an independently usable saved numerical candidate.
Translate only `_chem_comp.group` to DNA and `_chem_comp.type` to DNA LINKING in
a separate file. Compare every other parsed field exactly, including atom names,
formal charges, coordinates, signed stereo and all numerical rows. Refuse
conflicting/unsupported declarations, existing output and symlink traversal;
hash-preserve both inputs. No component-name or atom-pattern inference applies.

`--source-dna-metadata-only` accepts exact C56 and replays the original verified
decisions before preparing derivatives. Six native workers, each bounded to
60 seconds, reuse the same frozen source-seed/generated model and isolated PHIL.
Pin the selected Phenix 2.2.1-6174 APIs and energy implementation sources.
Require independently usable output, native DNA group/classification, identical
name-normalized fixed covalent proxies and matching full unnormalized target
and named Cartesian gradient at both coordinate sets. Atom reordering is allowed;
identity, coordinate and active-parameter checks remain those of usability v2.
Each worker records two finite repeatable evaluations. This comparison does
not establish nonbonded pair-identity equivalence or construct a polymer link.

The existing decision core prefers a qualified source-metadata candidate. If
preparation or either native comparison fails, it retains the already-qualified
generated dictionary automatically. Missing convergence remains a note; no
student CIF inspection or ordinary pipeline change is introduced. The receipt
adds `source_classification_audit`, field-level preparation and per-coordinate
equivalence/selection evidence with anchored artifacts. Historical failures and
the fallback remain immutable.

Returned C57 verifies all 2,854 payloads and six completed Phenix 2.2.1-6174
workers. All metadata/effective-proxy/full-target/named-gradient comparisons
pass at both coordinate sets; twelve finite evaluations repeat exactly. All
three decisions select source_declared_dna with notes. Maintained code replays
every preparation, worker/spec/input/output receipt and decision without
executing captured Python. The runtime is identical to the clean source build;
only NARestraints dirty-state metadata explains the runner SHA. No generator
or optimizer runs. Actual links/terminal modifiers,
phosphate-state choice, absolute CIP, linear-axis torsions, DP geometry findings,
production adoption and solution PDF integration remain separate qualifications.
Unsupported native formal-charge access remains explicit; partial charge never
substitutes for the unchanged declared CIF formal charges. ATL stays an
independent public/compiler control without native construction.

## Qualified DNA linked controls (Cedar 58)

This diagnostic tests whether independently usable complete candidates retain
their source chemistry and fixed restraints in an actual linked native manager. It prepares separate synthetic three-residue controls, not a new
diffraction model or an adoption into the saved scaffold. The prior isolated
CONTINUE_WITH_NOTES decisions and their qualified fallback remain unchanged.

**Methods.** Select explicit A:1-3 from the hash-bound bundled 5W6W A_T frame.
Keep the two flanking residues and every central sugar/backbone coordinate.
Partition the candidate graph into the supported DNA scaffold and one connected
base attached at C1-prime, then transport the entire base through proper
orthonormal C1-prime/O4-prime/C2-prime frames. Use heavy atoms, omit coordinate
OP3, and declare incoming A:1 to A:2 and outgoing A:2 to A:3 links. The first
end is free 5-prime OH and the last free 3-prime OH. Bridged/ambiguous scaffolds,
missing coordinates, unrequested terminal phosphate and unsupported graph
attachments are refused; ATL stays outside this native control.

`prepare_linked_component(..., native_qualification=...)` is an explicit bridge
from passed isolated usability v2. Bind component, source and candidate hashes,
require every qualification check and repeat the complete source-preserving
candidate assessment. A legacy source DNA group is accepted only through this
bridge. Preserve raw legacy findings, including the phosphate `both` omission,
alongside reassessment. Existing callers keep their original strict type-only
contract. The v2 linked preparation uses the established graph-selected atom
deletions and reviewed OC2 outgoing-oxygen type. Remove incoming OP3 and its
attached H, remove outgoing O3-prime H by connectivity, preserve OP2 H and all
unaffected numerical rows. Native modification IDs remain site-specific.

`--linked-control-only` accepts exact C57 and replays all six returned native
equivalence cases before preparation. One canonical installed-library reference
and three modified controls each have a 60-second native deadline and two fixed
energy/gradient evaluations. Use the existing refinement-root PHIL adapter for
site modifiers; retain the frozen secondary-structure-disabled policy and pin
selected installation APIs/energy sources. No pairing/stacking is guessed in
these unpaired controls; NARestraints remains authoritative for the scaffold.

Require exact model correspondence, the two canonical backbone-link targets
and weights, native DNA metadata, complete heavy-site mappings, exact modifier
membership and every projected definition row. Match active heavy-atom bond,
angle, signed torsion/constant, plane and fixed-hand proxies. Require four
phosphate bonds and all six angles, with the incoming backbone O replacing OP3.
Preserve flanking definitions and every unaffected proxy. Check finite active
parameters, finite repeatable energies/gradients and retained triple targets;
their magnitude does not prove convergence. Missing native formal-charge access
is explicit and never substituted with partial charge; contradictions fail.

Schema-1 `linked_control_audit` records anchored control models, preparations,
canonical/native evidence and qualifications. Generation, optimization, original
model changes, scaffold adoption and production pipeline changes do not occur.
Returned C58 verifies all 2,940 payloads and the complete C57 lineage. One
canonical and three modified Phenix 2.2.1-6174 workers complete; all three
modified cases pass LINKED_CONTROL_MECHANICS_PASS. Their eight total fixed
energy/gradient evaluations are finite and repeat exactly. The only unsupported
check per modified case is native formal-charge readback, with no contradiction.
Achieved geometry, phosphate state, absolute CIP, nonbonded pair identity and
full-scaffold integration remain separate. No student CIF inspection or approval
is required.

## Separate full-scaffold candidate (Cedar 59)

`--scaffold-candidate-only` accepts the exact returned C58 capsule and replays
its linkage qualifications before a separate DP B:4 trial in the preserved full
NARestraints manager. This moves from short synthetic controls to the actual
877-atom/43-site scaffold without optimizing or changing its saved coordinates.
The original bundle remains the automatic fallback.

**Methods.** Assemble the independently qualified source-DNA candidate with the
existing incoming OP3/outgoing-H site preparation. Replace the selected original
component dictionary. Remove only the selected site's old modifier requests,
preserving shared modifier definitions and all unselected PHIL bytes. The shared
NASnoOP3 requests for the other three sites remain intact. Keep the complete
model byte for byte and retain anchored hashes for every original and derivative
resource. Refuse ambiguous resource ownership or incomplete shared-code context.

First reinterpret the original bundle and require the captured native baseline
to match. Then interpret the candidate under the same pinned installation and
explicit NARestraints policy. Both workers have 60-second deadlines and two fixed
energy/gradient evaluations. Require all 38 backbone links and their targets,
all unselected effective definitions and native proxies, and the full custom
pairing/stacking request inventory to survive. Native secondary-structure guesses
remain disabled. Require exact selected projected/heavy restraints, new modifier
membership, phosphate tetrahedral coverage, finite active parameters and finite
repeatable energies/gradients. Formal-charge contradictions fail; unsupported
readback never substitutes partial charges.

A mechanically usable candidate can be selected for this separate diagnostic;
otherwise retain the verified original automatically and report the limitation.
Different dictionary objectives are not ranked by energy. Nonconvergence and
existing geometry findings remain notes. The original run and prior candidates
remain preserved; students do not inspect or approve CIF tables. All 73 new
regressions, 137 focused and 3206 full tests pass, plus actual-return relocated
preparation. Returned C59 verifies all 3,097 payloads and both completed native
workers. Twelve original-baseline checks pass; the candidate records 67 PASS
and one unsupported formal-charge readback, without contradictions or REVIEW
findings. The diagnostic decision selects qualified_candidate with notes.
All 877 atoms, 43 sites, 38 links and the full NARestraints policy survive.
At fixed coordinates, DP C6-N5-C7 changes from a 109.471-degree target to the
independently generated 128.1-degree target. Descriptive outlier counts belong
to their respective objectives and do not establish optimization improvement.
This does not deploy automatic production adoption, select phosphate state,
establish absolute CIP or implement solution PDF rendering.

## Replacement-manager geometry trial (Cedar 60)

`--scaffold-geometry-only` accepts exact C59 and verifies the selected full
bundle before one separate geometry-only trial. The saved C59 PDB-rounded
coordinates and replacement numerical definitions are the starting authority.
This is a new fixed manager, not a continuation of C28's different objective.
The verified initial model remains an automatic fallback.

**Methods.** First run a fresh corrected-gradient audit at the new initial
coordinates. Reuse the previously qualified C26 general plane proof only when
all plane/parallelity inventories, named atom mapping and native API/source pins
match exactly. Derive a new constraint signature from the replacement manager
and require fresh sampled derivatives for the complete new objective. The
cif-replacement-manager-gradient-qualification-v1 adapter binds these separate
proofs without reusing or forging the old covalent manager's qualification.
The qualified local plane correction and native kernels/targets stay fixed.

Use the existing geometry worker, L-BFGS and termination rules, bounded at
1,000 iterations. Keep dictionaries, selected modifiers and explicit NARestraints
pairing/stacking policy fixed throughout; native secondary-structure guessing
remains disabled. Check endpoint derivatives at full precision and after PDB
rounding, and require fresh exact native readback of model identities, chemical
definitions, constraints and policy. Bind exact PDB serialization to the verified
source-model hash. Require zero fixed-hand sign conflicts in both the
full-precision geometry and freshly reread rounded native geometry. Both the
full-precision and serialized endpoint targets must be no worse than the new
trial's initial target under the same fixed objective. Pucker is not inversion.

Schema-1 scaffold_geometry_audit uses cif-qualified-scaffold-geometry-trial-v1;
the existing native trial policy remains
cif-fixed-na-corrected-geometry-trial-v1. The additive
`cif_scaffold_candidate.select_scaffold_geometry` adapter uses
cif-qualified-scaffold-geometry-choice-v1 to select qualified_geometry_endpoint
only when these checks pass. Otherwise, including an absent endpoint, retain
verified_initial_scaffold automatically. Report the native stopping reason,
nonconvergence, pucker and residual geometry as notes; these alone are not
failure conditions.
Do not rank targets across the old and replacement dictionaries or require more
continuation cycles. All 82 new regressions, 235 focused and 3288 full
tests pass, plus actual-C59 relocated replay and bridge validation. Returned
C60 verifies 3,300 payloads and the complete unchanged C59 parent. Fresh initial
and both endpoint sampled derivatives pass; all 17 native readback and eight
selection checks pass. The full-precision target falls 2671.029230 to
2508.431084 (6.09%) and gradient norm 1507.689322 to 50.997383 (96.62%).
The written PDB separately records target 2511.569430 and gradient norm
878.690317. Both have zero sign conflicts among 158 chirality proxies and retain
three bond/nine angle nominal deviations at least five sigma. Preserve
NOT_CONVERGED_LIMIT at 1,000 iterations/1,033 calls; the native criterion is false.
The usable endpoint is selected with notes. No additional geometry continuation
is required. Scientific structure qualification, absolute CIP, phosphate state,
nonbonded pair identity, ordinary production adoption and PDF rendering remain
separate. No student CIF inspection or approval is introduced.

## Portable activated runtime bundle (Cedar 61)

The selected written model and the exact resources that produced its qualified
native manager can now be staged independently of the diagnostic capsule.
`cif_runtime_bundle.prepare_runtime_bundle` writes a separate schema-1
runtime_bundle.json under cif-qualified-runtime-bundle-v1, preserving the exact
model, ordered dictionary/PHIL bytes, source hashes, activation evidence and
continuation notes. The model and resources live within that bundle; every
operational reference is relative to its root and carries a hash and size.
No original resource is overwritten. The evidence directory also retains the
verified initial_model.pdb needed to reproduce the coordinate choice.

`resolve_runtime_bundle` checks schema, anchored paths and integrity, then
returns the selected model and ordered resources. `assess_runtime_bundle`
feeds that inventory to the existing read-only assessor with bundle_context.
Its additive solution_report explains the selected model, inherited stopping
verdict and continuation notes in plain language; PDF rendering stays PLANNED.
The ordinary command is:

```bash
./nasolve cif-doctor assess --bundle /path/to/runtime_bundle.json --json
```

This selects the bundle's model/resources rather than a run/checkpoint. It does
not infer new chemistry, perform native refinement or promote audit findings
into scientific approval. Detailed findings remain developer evidence, without
a student CIF-inspection gate.

**Methods.** `--runtime-bundle-only` accepts exact C60, replays the selected
endpoint, and stages its written PDB plus all 19 CIFs and 14 PHILs. Preserve
resource ordering, inherited decisions/limitations and the fixed NARestraints
policy. Use the ordinary generic loader/assessment path after relocation, with
source directories unavailable. One fresh native interpretation from the staged
layout must match C60's rounded manager: model identities, effective definitions,
all fixed proxy/link inventories, native APIs and explicit pairing/stacking
policy. This cif-runtime-bundle-activation-trial-v1 diagnostic writes
runtime_bundle_audit. All 106 new regressions, 215 focused and 3394 full tests
pass. Returned C61 verifies 3,406 payloads and the unchanged C60 parent; all
15 fresh native readback checks pass, with two finite repeatable evaluations
and unchanged target 2511.569429708212. The exact model/19 CIFs/14 PHILs survive.
Ordinary 33-input assessment remains REVIEW with preserved solution notes;
PDF rendering remains planned.

The activated bundle is an explicit portable resource selection. Automated
source acquisition/repair, fresh NAR compilation, ordinary PostMR adoption,
production checkpoints, diffraction/refinement and PDF rendering remain planned
integration. The source capsule contains no observations or ordinary PostMR
report, so no AutoMR run or checkpoint is fabricated. Curated precedence,
NARestraints authority, ATL independent scope and the eight-pair live-run plan
remain unchanged. No generation or optimization occurs in C61.
The bundle-only summary now states native_selection VERIFIED_SOURCE_CAPTURE
and native_selection_executed false: the public reader inherits/replays verified
evidence rather than performing a new native selection. Historical C61 summary
receipts are preserved with their original NOT_RUN label; compatible replay
does not rewrite them or change the selected model.

## Ordinary PostMR connected-base restoration (Cedar 62)

The restored-parent step in ordinary PostMR now keeps a connected modified base
together. Legacy same-name copying could combine parent base coordinates with
new substituent coordinates, producing the damage reproduced in Cedar 16.
The graph-selected rigid fragment method tested separately in Cedar 17 now runs
in the ordinary construction path. It changes coordinate handling, not source
chemistry, restraint targets or NARestraints policy.

**Methods.** `postmr.construct_postmr_model` is the shared Coot construction API
used by ordinary `prepare_postmr` and the fresh MTZ-free controls. Under
postmr-source-graph-fragment-restoration-v1, select one complete heavy base
fragment from the explicit source graph with a single C1-prime attachment.
Transport all its atoms through the proper raw-to-parent C1-prime/O4-prime/C2-prime
frame transform while restoring the parent DNA sugar/backbone. Preserve raw
base internal geometry and attachment hand within PDB rounding; parent base
names supply no partial coordinate map. Canonical base-mutation backbones and
explicit curated substitution/ring placements retain their documented behavior.

Unsupported, bridged or ambiguous graph/context cases retain their entire raw
Coot site with nonfatal notes. This includes the independent ATL control;
unsupported transport is not an invitation to force a standard DNA sugar into
a bridged component or ask a student to inspect a CIF. Source bytes, curated
precedence, native kernels and the qualified plane correction remain fixed.

`--postmr-construction-only` accepts exact C61. The
`cif_postmr_construction.run_postmr_construction_controls` helper prepares a fresh
MTZ-free, free-5-prime-OH W frame and constructs DP A:6 from DG, PDU A:9 from DT
and 5PC A:7 from DC using verified numerical dictionaries. One Coot construction process
calls the shared ordinary API, with a 600-second bound and no change to ordinary
default timing. ATL remains public graph/production-restoration eligibility
only, because no qualified numerical ATL dictionary is supplied; no fresh
native/Coot ATL result is claimed. Inspect-only prepares models, dictionaries
and the plan without starting Coot. Its ORDINARY_POSTMR_CONSTRUCTION_CONTROLS
action uses the separate cif-postmr-construction-controls-v1 report. All 118
C62 regressions, 257 focused and 3512 full tests pass (two skips,
276 subtests), including strict prior-return replay and relocated transport.
Returned C62 verifies 3,445 payloads and completes one Coot 1.3.3 process. All
three sites retain their whole raw site because OP3 lacks a parent scaffold
match. The 857-atom raw/final models are byte-identical; rigid transport was not
exercised. Scientific geometry and native restraints were not assessed.

**Internal-phosphate context (Cedar 63).** Ordinary construction now runs
postmr-source-graph-internal-phosphate-context-v1 before connected-base
restoration. Establish selected serial authority from exactly inherited frozen
CONECT records and unchanged unselected atom identities/XYZ. In a separate,
discarded shadow, place only graph-matched scaffold atoms in the parent frame.
Run the existing unchanged phosphate sanitizer with frozen allowed-OP3 and
passthrough intent to prove the selected internal OP3 deletions. Transfer only
those deletions and authorized selected serial fields to the original raw
records; never propagate shadow XYZ. Apply the existing proper whole-base
transport and recheck with the unchanged sanitizer. An unsuccessful or
ambiguous proof retains the complete raw context with nonfatal notes. Explicit
curated placements and bridged/unsupported ATL retain their existing treatment.
This is an ordinary default construction fix, not an optional chemistry change.

C63 repeats `--postmr-construction-only` on exact C62 through the same API and
cif-postmr-construction-controls-v1 report, with an additive independent context
delta audit. One fresh Coot construction process remains bounded at 600 seconds. The offline
saved-C62 study proves three OP3 deletions/69 selected serial normalizations and
preserves all three base geometries within 0.0011 A after transport; it is not
a fresh native result. Completed actual_coot_composition reports OBSERVED raw
and context inventories; inspect-only remains NOT_YET_OBSERVED. Old C62
receipts are preserved byte-for-byte. All **140 new regressions**, **290 focused / 3652 full tests** pass
(two skips, 276 subtests; full run 350.46 s). Actual-C62 strict
replay, deleted-build/relocated transport, eight mirrors, 156 links and protected
hash/figure checks pass. All 3,445 source payloads and the everyday edit are
preserved. Returned C63 now closes that fresh Coot construction gate.

Returned C63 verifies all **3,489 payloads**, preserves the complete C62 parent,
and completes Coot 1.3.3 through the ordinary construction API. All three
DP/PDU/5PC sites use proper whole-base restoration, with three proved internal
OP3 deletions, 69 selected serial normalizations and no raw fallback. The final
unchanged phosphate recheck removes nothing. Base geometry changes by at most
0.001041 A, consistent with PDB rounding; this is construction evidence, not a
native-restraint or scientific-geometry verdict.

cif-review-diagnostic-transport-v1 accepts only timestamped opaque Coot backup
`.pdb.gz` names in the declared backup directory as an exception to strict
portable payload names. A checked staging index maps legacy names to safe
hashed object paths while preserving original logical names, gzip bytes and
parent manifests in archives. Newly owned backups use portable timestamp
names with provenance in postmr_construction/diagnostic_transport.json. The
mapping does not execute/decompress backups or relax scientific resource paths.

The controls do not fabricate observations or an AutoMR/PostMR checkpoint, run
ReadySet/Phenix/refinement, optimize a model or compile a new NAR policy.
Automatic acquisition/repair adoption, generic pairing/stacking compilation and
production checkpoint/refinement still precede the full eight-pair live run;
PDF rendering and scientific geometry/state/CIP qualification remain separate.
No student CIF gate is introduced.

## Native readback of ordinary construction (Cedar 64)

C64 `--postmr-construction-native-only` consumes exact C63 evidence and replays
its context, serials, deletions, transform and independent audit through current
maintained code. Captured Python is never executed. Historical C62 raw fallback
and every parent receipt remain unchanged.

`cif-ordinary-construction-native-readback-v1` stages byte-exact canonical and
constructed models with the existing qualified source-graph modifier preparation
for DP A:6, 5PC A:7 and PDU A:9. Explicit incoming/outgoing contexts include
adjacent modified sites. Six CIF inputs and four PHIL inputs preserve the source
numerics; no new numerical generation, charge/protonation selection or coordinate
adjustment occurs. The canonical reference uses installed monomers and the same
secondary-structure-disabled policy. NARestraints remains authoritative; this
construction test does not compile or guess pairing/stacking relationships.

Two Phenix 2.2.1-6174 interpretation workers are bounded at 60 seconds each,
with two fixed energy/gradient evaluations per worker. Require exact written
models, complete effective sites, projected definitions, modifier membership,
heavy-atom covalent proxies, all canonical backbone links and unchanged
unselected definitions/proxies. Each selected incoming phosphate needs four
bonds and six angles. Triple-bond readback uses an explicit heavy-atom site view;
check active length/linearity membership and positive weights. Descriptive
coordinate bending and retained linear-axis torsions remain separate findings.
Unknown formal-charge access stays unsupported; contradictions do not pass.

The report is `construction_native_audit.json`, duplicated in the probe receipt;
all input/output references use the owned construction_native_directory anchor.
A prepared bundle remains usable after relocation without the original capsule.
The two models have different objectives: their energies are not ranked.
Scientific geometry, absolute CIP, general repair/adoption, generic NAR policy
compilation, ReadySet, production checkpoints/refinement and solution PDF
rendering remain separate. ATL remains an independent public/compiler control.
Students never approve CIF tables. The returned Mac workers both complete;
the original six label-padding comparisons retain REVIEW, while active triple
targets and the other evaluable checks pass. The original receipt is preserved.

## Saved construction native replay (Cedar 65)

`--saved-postmr-construction-native-only` accepts the exact C64 capsule. Its
manifest, completed native receipt, unchanged C63 lineage and source-qualified
preparation are verified before maintained code requalifies both saved managers.
The original worker/specification, ordered input roles/bytes, output inventories,
effective results and native implementation fingerprints remain bound as data.
Captured Python is never executed; no Coot or Phenix installation is needed.
Only recomputed descriptive finding eigenvalues/determinants admit a 1e-12
cross-platform roundoff bound; finding identities/verdicts and all other fields
remain exact. CIF, PHIL and model bytes and every native proxy parameter remain
exact; this bound does not apply to restraint or stereochemical targets.

The shared `cif-native-named-proxy-comparison-v1` comparison normalizes padding
in the structured model/chain/residue/insertion/alternate/component/atom fields,
then compares every ordered named endpoint and parameter exactly. Elements
remain part of the signature. Raw labels must first bind to the same capture's
indices; duplicate indices/names, incomplete identities and unbound labels fail.
Manager renumbering does not change identity. No endpoint permutation, alias,
case folding, numerical rounding or target/weight relaxation is introduced.

The C64 return contains **3,148 unaffected terms**: 880 simple bonds, 1,346
angles, 152 chirality, 327 constant torsions, 404 periodic torsions and 39 planes.
Both empty symmetry-bond and parallelity families also compare exactly. Active
PDU/5PC triple lengths and linear-angle weights remain qualified, with three
linear-axis torsions per modified site retained as notes. Formal-charge readback
remains unsupported; scientific geometry/CIP/state approval is separate.

`saved_construction_native_audit.json` adds the corrected mechanics verdict,
per-family missing/extra counts, the original review-check names, anchored
original evidence and `new_native_calls = 0`. Overall diagnostic status remains
REVIEW until full-run/scientific qualification. Every historical payload and the
original C64 qualification remain byte-identical. Automatic acquisition/repair,
generic NAR compilation, production adoption/refinement and PDF integration
remain subsequent work; students never inspect CIF tables.

Returned C65 verifies all **3,587 payloads**, preserves the entire C64
parent and manifest, and reproduces the maintained qualification: **93 PASS,
zero REVIEW, three unsupported formal-charge readbacks**. All eight unaffected
proxy families compare exactly, covering 3,148 restraints. Both active triple
screens pass; three linear-axis torsions per site remain recorded. Independent
replay reproduces the report and prepared scientific bytes with subprocesses
forbidden. No repeat of this construction-native gate is needed.

## Reviewed preparation

Preparation is an explicit derivative write, separate from PostMR adoption:

```bash
./nasolve cif-doctor prepare /path/to/source.cif \
  --recipe torsion-alternates-v1 --output /path/to/new-candidate.cif \
  --report /path/to/new-preparation.json
```

`torsion-alternates-v1` wraps the existing supported CCP4 alternate-torsion
normalizer. It retains the primary row's uncertainty, preserves recognized
alternate targets and leaves unsupported competing terms intact for review.

`5cm-reviewed-torsion-v1` applies only to the exact reviewed historical source
hash `38378c7df4eef73a0bd2be40059b2c3dd2b98618a4eeb7e91f6ec3427f7e7858`.
It changes the single reviewed C2 reference to C2′ in the
C4′–O4′–C1′–C2 torsion, then applies that existing normalizer. Other files,
including another file named `5CM.cif`, are refused. This is not a general
prime-name correction rule.

Both recipes preserve the original bytes, refuse existing destinations and
return hashes, field-level changes and before/after assessment. `PREPARED`
means a candidate file was created; it does not mean native qualification or
automatic adoption. Preparation's exit code follows the candidate assessment;
invalid candidates visibly remain blocked from adoption. The recipes do not edit coordinates, invent protonation or bond
orders, install the diagnostic DF/DP candidates or rewrite a frozen run.

## Offline runner for the public control ZIP

The downloadable `run_cif_doctor_ccd_controls.py` contains the exact reviewed
assessor and its required reader/normalizer code. Run it with Python >=3.10
and Biopython; an existing NASolve virtual environment is sufficient. It
requires neither a NASolve checkout nor network access. Given both downloads
in `~/Downloads`, the established laptop environment can run:

```bash
"$HOME/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python" -B \
  "$HOME/Downloads/run_cif_doctor_ccd_controls.py" \
  "$HOME/Downloads/NASolve_CIF_Doctor_public_CCD_controls_2026-10-11.zip"
```

The runner verifies the frozen ZIP, manifest, all 18 CIFs and embedded runtime,
then creates a unique output folder beside the ZIP. It refuses reused output
folders, leaves the ZIP unchanged and writes `audit_summary.txt`,
`audit_summary.json` and 36 hash-bound receipts. These particular controls
produce **18 source PASS / numerical UNASSESSED and 18 effective REVIEW**:
the same source graphs are screened in two contexts. No numerical dictionary
is generated, and ReadySet/refinement are not run. A completed audit exits zero;
findings are recorded in its report, unlike the single-assessment CLI exit codes.

Developers can regenerate the single-file artifact without an installed NASolve:

```bash
python3 scripts/build_cif_doctor_ccd_shuttle.py \
  --corpus-zip /path/to/public-control.zip --output /path/to/new-runner.py
```

Build/receipt schema 1 pins the exact source hashes and original module paths;
the shared reader definitions are copied unchanged with minimal imports.
The builder refuses existing destinations. The runner's hash belongs to each
delivery receipt, rather than serving as a rolling software version.

## Broader evidence and remaining work

NARestraints' ligand workbook selects test cases and records pairing semantics;
it is not a universal bond-order, protonation or stereochemistry authority.
Official [wwPDB CCD](https://www.wwpdb.org/data/ccd) definitions provide separate
source evidence. Downloads used for development are hash-frozen local inputs;
runtime assessment itself performs no network acquisition.

The first held-out corpus contains 18 public CCD source graphs, with provenance
and workbook row references in [the control manifest](cif-doctor-ccd-controls.json).
It includes halogenated DNA/RNA, C-glycosidic
pseudouridine, L-DNA, a nucleotide lacking O3′, methylated/sulfur components
and diphosphates. These exercise general checks without component-specific
exceptions. Official CCD 8RO remains distinct from the lab's DE identity.

The frozen comparison exposed inconsistent 5BU/BRU sugar-type workbook labels
and a PSU glycosidic-atom loader assumption. The separately reviewed
[NARestraints workbook patch](https://github.com/vecchioni-lab/NARestraints/blob/main/docs/workbook-audit-2026-10-11.md)
corrects the sugar labels/abbreviations, DF/S6G atom mappings and explicitly
authorized C5 whitespace. It does not change the frozen public-control snapshot
or fix PSU's coupled glycosidic/base-plane handling. Released v1.1.3 installations
retain their original workbook until explicitly updated.
The controls also prevent a fixed DNA R/S pattern: substituent changes can
change CIP labels without inverting the sugar. Preserve declared stereo and
perform any future assignment against the actual mapped graph.

Validation for the initial slice: 88 new Doctor tests and seven subtests, plus
the complete 1,077-test suite (two skips, 276 subtests). Frozen public controls
and exact historical replays preserve all input bytes. These are offline tests
and source-file audits, not a returned native Phenix/Coot campaign receipt.

Installed consumer-parser agreement, mapped descriptor chemistry, generator
adapters, effective native proxy receipts and new-checkpoint adoption remain
follow-up work. Geometry/connectivity assessment and guided sticky-end stitching
remain part of the Doctor roadmap, using declared routing and Scout/Topo
primitives while preserving true nicks, terminal intent and frozen Free-R flags.
