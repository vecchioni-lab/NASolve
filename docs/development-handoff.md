# NASolve development handoff — current state

Updated **2026-10-16** from native receipts, user visual review and verified geometry/DF
bundles. **Active candidate: `cedar`; integration target: `pine` (draft PR #26),
then `main` (draft PR #23).** The current laptop Cedar checkout remains at
**`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`**, with only the explicitly
authorized `src/nasolve/phaser.py` fix modified after the GeoTest rerun.
Its other 45 frozen source hashes, including the distinct curated source,
are preserved. Preserve this local unpublished diagnostic head; do not pull or
replace it with a remote head to continue the run. Diagnostic scripts/derivatives are
not general production support. Earlier wording remains in Git and the
[exact pre-reconciliation backup](history/development-handoff-2026-10-10-pre-reconciliation.md.txt).

## Completed and open work

| Workstream | Verified result | Still open |
| --- | --- | --- |
| NARestraints | **v1.1.3 released and installed** (`a9264f9`); corrected Z:P/K:X roles, unchanged workbook. Docs-only PR #5 merged to main at `ef1a5a1`. | Combined-model geometry qualification belongs to the NASolve native trial. |
| W Saenger overlay / viewing | PR #24 merged at `0017081`; prior Z:P `run_003/refine-001` numerically SOLVED and overall user Coot visual PASS. PR #25 merged at `e8613bf`; bare `show` user-live PASS. | New-campaign automatic workspace activation has regression coverage, not a separate returned live verdict. |
| Cedar source lookup | Installed Phenix CCD lookup for IGU/IMC/CGY/DX and Coot construction verified; symlink duplicates resolved. Nine bundled-source roles audited. | Acquisition, parameter generation and linkage must become a repeatable ordinary workflow; source availability alone does not certify geometry. |
| Combined 42-residue W trial | **Preflight, Phaser and PostMR passed**; 42/42 identities, 12 retained + 5 replaced Saenger blocks, 8 explicit pairs, stacking enabled. | Effective geometry qualification, explicit phosphate-state review, refinement and human review. |
| Generic linkage diagnostic | **GENERIC_LINKAGE_MECHANICS_PASS** with fresh IMC, no missing heavy atoms, preserved links and D:1 terminal phosphate. | Diagnostic-only derivatives, not integrated general PostMR support or chemistry approval. |
| Custom restraint coverage | **21/21 bonds, 34/34 angles, 8/8 planes, 23/23 parallelities** matched; no exact duplicate planes/parallelities or overlap candidates. | Custom proxies remained preserved after native 5CM/DF adoption; coverage is not achieved geometry. |
| Effective 5CM / DF recovery | **REPAIRED_NATIVE_INTERPRETATION_PASS**: corrected 5CM and linked DF adopted in a separate native diagnostic; 42 mappings, DF bonds/chirality, preserved custom/other proxies and unchanged 868-atom model verified. | Separate minimization and user visual review completed; full numerical qualification remains pending. |
| Combined geometry trials | First trial received user Coot visual PASS. The DP-specific trial relieves the N5 conflict (worst 6.15→0.483 sigma); all 158 chirality signs and 38 backbone links survive. User also reports base visual PASS for the exact new model. | Sugars were not assessed by eye; numerical sugar/termination review and full qualification remain open. Convergence is not claimed. |
| Ordinary/full-auto campaigns | Prior EA/DiU/Q5cm/QiC cohort reached numerical SOLVED with review/provisional distinctions preserved. | This does not prove a fresh arbitrary-component run without a prepared resource bundle. |
| CIF Doctor first slice | Offline dictionary and frozen-checkpoint assessment; report-only pre-mutation/pre-ReadySet/effective PostMR receipts; explicit torsion-alternate and hash-scoped historical 5CM preparation. | Native consumer/proxy verification, mapped descriptors, generation/adoption and geometry/stitching remain separate slices. |
| P2 / prepared nonstandard P5 | P2 preparation and nonstandard campaign paths implemented and fixture-tested. | Source-native `1W5→DZ` / `1WA→DP` provenance/refinement; 3–5 real geometry-diverse P5 models. |
| Scout / Topo / GUI | Existing registration/shadow primitives and scoped evidence retained. | Operational Scout and topology surgery remain future work. |

**Latest returned Cedar regression:** `1443979b2308e4a2e507f0859370b44e0e124a86`,
**16 focused + 31 subtests (2.45 s)** and **983 full + 257 subtests
(80.81 s)**, using `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src"`
and `../NASolve/.venv/bin/python -m pytest -q` (focused file:
`tests/test_cedar_ccd_resolver.py`). This receipt does not certify the current
local head or the later diagnostic derivatives. NARestraints installed workbook
SHA-256 remains
`94a66af42081188fd95f3fdcbe04cb01bed8f1826772597272320a8b4c0433b2`.

The October 10 documentation snapshot also passed the isolated Linux suite:
**981 passed, 2 skipped, 257 subtests (29.21 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
This is separate from the laptop receipt and is not native Phenix validation.

## Immediate next work

**Default command passage:** follow the
[Git delivery and terminal handoff contract](collaboration.md#git-delivery-and-terminal-handoffs).
Give one pasteable subshell containing the reviewed fetch, full-SHA detached
worktree, build and run commands joined by `&&`, with explicit quoted paths.
Keep necessary install commands as separate one-liners. This operating
convention belongs in the repo; private personality handoffs remain private.

**Cedar 12 returned and verified (2026-10-16):** all **116 payloads** in
`12_Cedar_q46plqwk_cif_terminal_bundle_review.zip` verify. The runner SHA-256
matches delivery `2144968031c659f69c4d71eb81f1aeb8ef7d79962c45e03daa4bfe2460352845`,
from clean NASolve `e5b1be6198eae73fedbc497d003502bfb31c2247` and NARestraints
`a7b6a0c93365f7a480b7eee9cc4e860b13f702de`. Baseline and candidate native
interpretations completed under Phenix **2.2.1-6174**, both exit 0
(5.651856 s / 1.256861 s). Qualification is **95 PASS, six UNSUPPORTED
formal-charge checks and four REVIEW outgoing-O3′-H checks**; aggregate
**REVIEW**, not complete scientific approval. Offline qualification replay
reproduces all 105 outcomes and evidence after sorting only unavailable-charge
items by atom ID. The [native evidence record](cif-linked-native-registration-evidence.json)
owns the exact hashes, checks and preservation evidence.

The source-bundled probe reuses the
exact Cedar 09 shared-code control and Cedar 11 installed numerical authority.
It verifies all 207/nine payloads, materializes only declared members and
preserves both original ZIPs. `prepare_terminal_component` wraps the existing
linked preparation; only free-OH contexts receive captured native O5′/H atom
operations, bond and angle. Actual-input offline replay produces E:1 with
32 dictionary atoms and leaves the 34-atom A:6 internal plan and shared base
byte-identical. All retained formal charges stay unchanged; the new H formal
charge is `?`, never copied from its native partial charge. No H coordinates
or new numerical targets are invented.

The selected candidate also explicitly reproduces reviewed 5CM output
`61bf14a1…`. Its native projection removes only the declared OP3. Baseline and
candidate use the same 877-atom/43-site coordinate control; no optimization.
New detailed schema-1 fields record neutron bond targets and torsion alternates.
Qualification retains all existing gates and adds exact projected numerical
rows, the corrected 5CM `C2e-nyu0` quartet/340.7°/6.3°/period-1/2.8° alternate
proxy, unchanged unselected definitions and every recorded unaffected native
proxy. The selected Phenix dispatcher, modules and numerical source hashes
must match the Cedar 11 authority before and after execution. Relocation uses
the declared installation anchor, not basename search.

**Read-only review class:** every declared outgoing O3′ endpoint is audited
by element and adjacency. Cedar 12 confirms the prior Cedar 09 findings:
1AP A:5→A:6 `HO31`, 5CM A:7→A:8 `HO3'`, DZ A:12→A:13 `H2` and DP B:4→B:5
`H3`, all on O3′ with OH1 typing. These pre-existing curated reviews are not
silently fixed or hidden by the two selected candidate changes. Native charge
readback and new-H formal charge remain unqualified; `REVIEW`/exit 2 is
retained while these gates remain unresolved, despite successful interpretation.

**Delivery:** `scripts/build_cif_terminal_bundle_probe.py`, pinned
`12_Cedar_probe_build`, same `05_Cedar_narestraints_build`, output
`12_Cedar_probe_cif_terminal_bundle.py`. Use one subshell containing fetch,
pinned detached worktree, build and run joined by `&&`. Explicit archive,
installation, timeout and inspect-only overrides remain available. Preserve
the frozen everyday checkout and all old scripts/worktrees/native sessions.
The returned one-block Git ferry also worked from an unrelated working
directory. No ReadySet retry, model optimization, refinement, adoption or
production PostMR change occurred.

**Next bounded scientific work:** review the four source-traceable internal
O3′-H contexts before preparing any explicit site changes. Native formal-charge
readback and the added H formal charge remain open evidence limits; repeating
an unchanged inventory does not resolve them. Geometry/refinement and human
review remain later gates. No Cedar 13 delivery is queued by this documentation
update.

**Software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,437 tests, two skips and 276 subtests (92.78 s)**. The same command
with `tests/test_cif_terminal_preparation.py tests/test_cif_terminal_qualification.py
tests/test_cif_terminal_bundle_probe.py tests/test_cif_native_validation.py
tests/test_cif_linked_preparation.py tests/test_cif_linked_qualification.py
tests/test_synthetic_dna_shuttle.py` passes **97 tests (6.84 s)**. Nine selected
regressions fail before the new implementation/readback fields exist. New
native tests use explicit fake APIs; transport survives deleted build trees
and poisoned imports. Actual returned-input offline preparation/replay and
prior-native outgoing-H audit are distinct from the completed installed
Cedar 12 execution above. This follow-up changes documentation/evidence only;
JSON, link and figure checks apply, with no runtime/schema migration or new
dependencies. Native payloads stay outside Git; qualification gates are unchanged.

Documentation follow-up verification: all 16 documentation JSON files parse,
116 local links in changed Markdown resolve, and `git diff --check` is clean.
`python docs/figures/build_cif_doctor_overview.py` reproduces the SVG;
its 1200×1190 render is byte-identical to the preceding visual QA image.

**Cedar 11 returned; terminal numerical sources complete (2026-10-15):** all
**nine** payloads in `11_Cedar_ggtpccwv_cif_terminal_review.zip` verify, including
anchored native outputs, repeated receipt content and the exact published
worker/build. The user's runner hash is `9aa0afa3…`, from clean source
`e6ec5d66e283a138c0ac8e9585146e5c994ac243` and the same pinned NARestraints.
The explicit 5CM preparation again reproduces `61bf14a1…` with source/original
09 ZIP preserved. Phenix **2.2.1-6174** resource execution completes at exit
zero in **0.837208 s**; status is `PREPARATION_AND_RESOURCES_REVIEW`.

Native resolution records DG → metadata `Gd`. The unchanged canonical base
has 33 atoms; effective `5*END` has 31: P/OP1/OP2 removed, O5′ changed from
OC2 to OH1, HO5′ added with HOH1 type and the exact installed bond/angle
targets. All unaffected bond/angle/torsion/chirality/plane rows remain equal,
with no dangling references. Both installed sources remain unchanged and
the modification rows exactly match Cedar 10. The compact registration evidence
owns all hashes, counts, exact targets and source/module provenance.

**Scientific interpretation:** both canonical states retain DNA group, but
the effective canonical 5′-OH classification is also `undetermined`. That label
alone cannot distinguish the earlier synthetic modified end from the canonical
control. It does not erase the earlier missing O5′ hydrogen/OH typing, and
no qualification gate changes. Both canonical states lack native formal-charge
readback; recorded partial charges remain distinct. Native metadata atom
counts are retained as returned, not rewritten to imply qualification.

**Next work:** implement an explicit source-traceable modified-terminal
adaptation and validate the revised bundle, including the separate prepared
5CM candidate, before a new bounded geometry trial. No further unchanged source
inventory is needed. No new delivery is queued by this evidence-only update;
no model edits, optimization, ReadySet retry, refinement or adoption ran.
Runtime/schema and dependency behavior are unchanged; the 1,406-test software
receipt below still applies, separately from this actual native return.

**Cedar 10 returned; Cedar 11 canonical lookup retry (2026-10-15):** all
**nine** payloads in `10_Cedar__7ap0ddc_cif_terminal_review.zip` verify. Its
clean NASolve source is `f681b9bd5355905fbee0797302d5984cc40e5d6a`, with the same
clean pinned NARestraints. The runner prepared the exact reviewed 5CM
derivative (`61bf14a1…`) with unchanged source/archive, then used installed
Phenix **2.2.1-6174** to capture the `5*END` fields and source hashes. The resource
worker returned UNSUPPORTED at **Missing canonical monomer: DG** after
**3.726048 s**; the aggregate probe is `NATIVE_RESOURCES_REVIEW`. No canonical
control, terminal adaptation, native 5CM qualification or refinement ran.

The v1 worker incorrectly used direct library lookup for a PDB residue name.
Primary cctbx `server.py` delegates name translation to the installed
`get_comp_comp_id_and_atom_name_interpretation` method; `iotbx.pdb` translates
explicit DG to library GD (and DA/DC/DT to AD/CD/TD). Policy
**`cif-installed-terminal-resources-v2`** now uses that native API with an empty
atom-name list, retaining no coordinate model or local alias table. Additive
schema-1 control evidence records the method, empty input atom list,
interpreted residue name and resolved component ID; provenance also hashes
`iotbx.pdb`. Missing native resolution APIs/components remain unsupported and
retain the already captured modification evidence. All numeric targets,
formal-charge boundaries and existing qualification gates are unchanged.

**Validation:** the new fixture reproduces the untranslated-name failure:
**five failures / seven passes** before the fix. Focused validation is
**55 passed (4.37 s)** using the five terminal/resource/repair/linked/shuttle
test files in the Cedar 10 command below. The full command below passes
**1,406 tests, two skips and 276 subtests (64.49 s)**. These are explicit fake
native API and transport checks, including all four canonical DNA names,
unsupported resolution, preservation and relocation. Corrected installed
canonical-control execution remains pending. The registration evidence owns
the exact returned hashes, source rows' provenance and primary-code references.

**Next delivery:** build the existing terminal probe with explicit
`--delivery-prefix 11_Cedar` and output
`11_Cedar_probe_cif_terminal_review.py`, from pinned `11_Cedar_probe_build` and
the same `05_Cedar_narestraints_build`. It still reads the exact original
Cedar 09 ZIP; no replacement ZIP or new dependency is required. The user
requests one pasteable conditional command block: fetch, add pinned detached
worktree, build, run, joined by `&&` inside a subshell. Stop after any nonzero
status. Preserve the everyday checkout, all old build trees and every native
session. Inspect the returned control before implementing terminal adaptation
or proceeding to a separate bounded geometry trial. No native outputs are
committed; this change includes source/tests/docs and compact evidence only.

**Cedar 10 terminal-source review ready (2026-10-15):** the user requested a
few executable steps and clarified whether the whole run had completed. Only
the native linkage diagnostic has completed; no complete refinement run is
claimed. The next delivery advances the two known dictionary reviews without
rerunning the same linked inventory for an unavailable charge attribute.

`scripts/build_cif_terminal_probe.py` packages
`10_Cedar_probe_cif_terminal_review.py` from pinned source and the same
`05_Cedar_narestraints_build`. It accepts the exact hash-bound returned Cedar
09 capsule, verifies all **207** payloads and snapshots only its explicitly
declared frozen 5CM source. The existing `5cm-reviewed-torsion-v1` recipe
prepares a separate candidate: source `38378c7d…`, output **`61bf14a1…`**.
No selected bundle or old native input is replaced. The actual returned 09
source reproduces the complete reviewed candidate hash in inspect-only replay;
its implemented assessment passes, with native bundle and geometry validation
still NOT_RUN for this preparation.

The new reusable `cif_terminal_resources.inspect_terminal_resources` API
reads explicit native modification IDs (default `5*END`) and applies them only
to an in-memory canonical library control (default DG). It records all native
row fields in atom/bond/angle/torsion/chirality/plane categories, numerical
values, source/module hashes, charge readback and base preservation. No target,
energy type, hydrogen name or formal charge is invented for IGU. This captures
the installed numerical authority needed to complete the terminal treatment;
it is **not** implementation or qualification of that new recipe. Native
source/control errors, unsupported APIs and owned-process timeout remain
explicit. The selected Phenix environment is isolated as in earlier probes.

**Software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,400 tests, two skips and 276 subtests (63.87 s)**. The same command
with `tests/test_cif_terminal_resources.py tests/test_cif_terminal_probe.py
tests/test_cif_doctor_repair.py tests/test_cif_linked_probe.py
tests/test_synthetic_dna_shuttle.py` passes **49 tests (3.64 s)**. New native
tests use explicit fake APIs, including exact target retention, unknown charge,
missing resource and owned timeout. The resource tests fail before the new
module exists and pass afterward. Transport tests delete original build paths,
poison imports and preserve both successful/unsupported review capsules.
Real-09 inspect-only replay verifies exact source/output hashes and preserved
original ZIP; installed resource execution remains **PENDING**. No new
dependencies, production PostMR changes or old qualification-gate changes.

**User delivery:** a pinned `10_Cedar_probe_build`, then the source-bundled
builder/run sequence. The user now explicitly permits a few sequential
commands together. Preserve the frozen everyday NASolve checkout, existing
05–09 trees/runners and every native session. Inspect the new review ZIP before
implementing the terminal recipe or entering a separate bounded geometry trial.
No model interpretation, model optimization, ReadySet retry, diffraction
refinement or adoption is part of Cedar 10. Only code/tests/docs and compact
evidence enter Git; actual source dictionaries/native outputs remain outside it.

**Cedar 09 returned; native metadata recovered (2026-10-15):** all **207**
payloads in `09_Cedar_nn9cyghr_cif_linked_review.zip` verify. Source is clean
NASolve `4f1cde11b540c24adc27c97cb5f891f6710bf17e` with the same pinned clean
NARestraints source. Phenix **2.2.1-6174** completes baseline/linked/control at
exit zero in **2.924922 / 1.354201 / 1.272176 s**. All four linked sites now
have native group and classification **DNA**. Qualification records **29 PASS,
four UNSUPPORTED**: every noncharge check passes, while the installed atom API
has no formal-charge attribute. There is no known-charge contradiction. Keep
the aggregate **REVIEW** and raw charge evidence; do not substitute partial
charges, source values or zero, weaken the gate, or repeat an unchanged native
inventory to seek an attribute absent from this installation.

The linked manager retains 858 atoms, 42 mappings, all **38** declared links,
custom **21 bonds / 34 angles / 8 planes / 23 parallelities**, all 58 native
parallelities and unaffected definitions. The 877-atom/43-residue control has
**10 PASS / two charge UNSUPPORTED**; original atoms, all 42 definitions and
38 links are unchanged. Its E:1 group is DNA but classification is
**undetermined**. The projected E:1 O5′ remains type **O2**, bonded only to C5′
with no explicit O5′ H. This proves selected atom/context isolation under one
code, not complete free-OH end parameterization or general terminal support.
Do not infer that the original four internal sites failed classification.

Read-only arithmetic replay compares **148/148** source/candidate formal charges
with no difference or unavailable source value. All **12** generated ordered
sugar-centre signs match source ideal coordinates; native proxy signs and the
initial model agree under each actual proxy order. The determinant convention
is checked against the primary cctbx chirality implementation. This is
source-coordinate/sign consistency, not independent CIP/R-S assignment or
experimental validation, and it does not satisfy the native charge gate.
Projected plane-angle reviews remain **IGU five / IMC two / CGY five / DX zero**;
their material-strain threshold is uncalibrated. The selected 5CM A:7 still
contains `C4′–O4′–C1′–C2` (`C2e-nyu0`, 340.7 ± 6.3°, period 1). Preserve that
known C2/C2′ defect until an explicit, hash-scoped preparation is reviewed;
do not silently substitute the historical repaired derivative.

The [registration/list-metadata record](cif-linked-native-registration-evidence.json)
owns exact archive/source/API hashes, native counts and these review limits.
**Next work is dictionary chemistry/geometry review:** complete the declared
free-OH terminal treatment through a traceable numerical source, use explicit
reviewed 5CM preparation where its exact source hash permits it, and preserve
charge/protonation and generated metadata reviews before a new bounded geometry
trial. The subsequent Cedar 10 source-resource delivery is described above;
it does not repeat this linked inventory. No ReadySet retry,
minimization, refinement, adoption or gate change occurred. These updates are
documentation/evidence only; the runtime's existing 1,386-test receipt below
and its returned installed execution remain the validation. Original private
payloads and the frozen everyday checkout remain outside Git and unchanged.

**Cedar 08 returned; Cedar 09 component-list retry (2026-10-14):** all 207
payloads in `08_Cedar_g4gzbeeb_cif_linked_review.zip` verify. The runner matches
the expected SHA-256 and clean NASolve `147c1fbaabb41f73f5680852625189b0e1295ca7`,
with the same clean NARestraints `a7b6a0c93365f7a480b7eee9cc4e860b13f702de`.
Phenix **2.2.1-6174** completed baseline, linked and synthetic shared-code
interpretation at exit zero (**2.522322, 1.381361 and 1.412638 s**). Native
modifier registration now matches every requested ID. All four expected atom
sets, H adjacency and energy types agree; no dangling references remain.
All **38 links**, custom **21 bonds / 34 angles / 8 planes / 23 parallelities**,
all 58 native parallelities, unaffected definitions and the original 858 atoms
are preserved. Internal IGU A:6 and free-OH IGU E:1 have distinct selected
definitions in the 877-atom/43-residue control; the original 42 definitions
and 38 links remain unchanged. The control's added residue is synthetic.

The returned status is still **REVIEW**, with two precise limitations:
the native formal-charge attributes are absent, and the declared `_chem_comp`
DNA group was not read. Our singleton `comp_list` writer collapsed its metadata
to scalar fields; native `convert_list_block` only iterates the category loop.
Both loaded base and effective group are null. Native logs nevertheless classify
all 42 residues as DNA: group metadata and interpreted classification are
distinct, and the old worker did not record the latter per site. The old
`effective-site-atoms` check combined matching atoms with the missing group;
there is no observed atom-inventory mismatch.

The writer now retains one-row list metadata as a loop, using the existing CIF
quoting implementation. It adds `component_list_policy =
cif-native-component-list-loop-v1`; detailed native metadata records
classification separately. Qualification reports exact atoms and required DNA
group independently, preserving both gates. Exact returned-input replay keeps
every parsed base/projected dictionary, site plan, modifier and PHIL request
unchanged; only list serialization changes. The
[registration/list-metadata record](cif-linked-native-registration-evidence.json)
owns native hashes/counts, the group blocker, source preservation and replay.
Missing formal charge is still `UNSUPPORTED`; no partial/source/zero substitute
is introduced, and a subsequent REVIEW can persist after the group is corrected.

**Next action:** deliver the clean published source through a pinned detached
`09_Cedar_probe_build`, build `09_Cedar_probe_cif_linked.py` using
`scripts/build_cif_linked_probe.py --delivery-prefix 09_Cedar` and the existing
`05_Cedar_narestraints_build`, then run it against the original checksum-bound
05 capsule. Issue one terminal command at a time. Preserve the frozen everyday
checkout, all 05–08 build trees/runners, native sessions and source models.
Installed list metadata, complete qualification, numerical/stereochemical
review and ordinary fresh full-auto recovery remain open. No ReadySet retry,
model optimization, diffraction refinement or adoption is authorized by this
diagnostic result. Generated private CIFs/coordinates/native receipts stay
outside Git; only code/tests/docs and compact evidence are committed.

**Cedar 09 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,386 tests, two skips and 276 subtests (89.41 s)**. The same command
with `tests/test_cif_linked_preparation.py tests/test_cif_linked_qualification.py
tests/test_cif_linked_probe.py tests/test_cif_native_validation.py` passes
**70 focused tests (4.75 s)**. Four targeted cases fail before the change and
pass after it. Explicit fake native controls reproduce skipped scalar metadata
and retained loop metadata; quoting/multiline values round-trip unchanged.
Exact real-return replay checks every base/projection value and preserved
modifier/PHIL/input bytes. Classification readback is additive to detailed
inventories; basic defaults and schema-1 compatibility remain unchanged.
No new dependencies are added. The editable figure is regenerated/rendered and
visually inspected. These software/replay checks are not installed Phenix
execution of the new metadata layout; that remains the Cedar 09 action.

**Cedar 07 returned; Cedar 08 registration retry (2026-10-14):** all 164
payloads in `07_Cedar_okkb2are_cif_linked_review.zip` verify. Source-retaining
IMC/CGY/DX generation reached `CANDIDATE_REVIEW`; IGU was reused. Detailed
baseline interpretation completed at exit zero (2.896598 s), with 858 atoms,
42 mappings and 38 backbone links. Linked interpretation failed at exit two
(1.082309 s): `Missing CIF modification: data_mod_NASL9809b6bd9c`.
The four modifier files registered `linked_sites`, overwriting that key, rather
than the distinct requested IDs. The
[registration record](cif-linked-native-registration-evidence.json) owns exact
archive/build/reader hashes, failure and replay. No linked qualification or
shared-code control completed; no coordinates or frozen inputs changed.

The writer now emits one native `data_mod_<ID>` block for each requested
modifier, with identical operations and PHIL IDs. Schema-1 preparation adds
`modification_block_policy = cif-native-modification-blocks-v1`. Replaying all
four actual returned candidates preserves each site plan, base dictionary and
PHIL file byte-for-byte while registering four distinct IDs. Reader-contract
tests reproduce the old missing-ID failure and cover multiple same-code end
contexts and cross-component collisions. These tests use explicit fake APIs;
they are not installed Phenix evidence.

The baseline native atom records also have no formal-charge values. New
detailed worker metadata distinguishes missing attributes from null readback;
site qualification records unavailable values as `UNSUPPORTED` separately from
actual charge contradictions (`REVIEW`). Never substitute partial charges or
zero. Source charge preservation remains separate evidence. Other mechanics
checks continue, but missing native charge readback cannot silently qualify.
The native console now prints the failed layer and its recorded error.

**Next:** Git-build and run
`08_Cedar_probe_cif_linked.py` with `--delivery-prefix 08_Cedar`, using the same
pinned NARestraints source. Keep the everyday laptop checkout, Cedar 07 runner,
all native sessions and original model/source inputs intact. The runner remains
an external diagnostic with no ReadySet retry, refinement or adoption. Native
registration, full linked mechanics, the shared-code control, numerical and
generated stereochemical review, and fresh full-auto recovery remain open.
Only code/tests/docs and compact hash/count evidence enter Git.

**Cedar 08 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,380 tests, two skips and 276 subtests (98.88 s)**. Focused
preparation/qualification/shuttle/native-worker checks pass **64 tests (5.38 s)**.
Two registry regressions fail with the old shared block and pass with distinct
blocks. The fake-reader boundary also reproduces the missing-ID failure with
legacy packaging and accepts the exact requested IDs with corrected packaging.
Native charge controls distinguish missing/nonfinite readback from actual
contradictions and retain the partial/formal-charge separation. Exact real
candidate replay checks unchanged base/PHIL/site plans and input preservation.
Existing shuttle relocation tests retire original build paths and poison imports.
The editable figure was regenerated, rendered and visually inspected. New
schema-1 fields are preparation layout provenance and detailed native charge
readback metadata; formal-charge check rows retain explicit unavailable and
contradictory observations. No new dependencies or installed native execution
were added to this validation. Generated coordinates/CIFs/native payloads stay
outside Git. The subsequent installed Cedar 08 result is recorded above.

**Cedar 06 returned; Cedar 07 representation retry (2026-10-14):** all 87
payloads in `06_Cedar_rkmjesl4_cif_linked_review.zip` verify. Native eLBOW
completed source-retaining IMC/CGY/DX generation on Phenix 2.2.1-6174
(RM1/GDIIS); IMC and DX reached `CANDIDATE_REVIEW`. CGY alone was rejected for
six alternating single/double ring orders becoming aromatic types. Every source
ring bond already declares aromaticity; connectivity, hydrogen attachments and
explicit formal charges survived. No new native bundle interpretation ran.
The [source-recovery record](cif-linked-source-recovery-evidence.json) owns
exact archive/source/candidate hashes, commands and offline replay.

Generation-v4 now recognizes only complete isolated source-declared aromatic
six-member alternating neutral C/N rings, with unchanged single bridges and
non-stereogenic ring bonds. Schema-1 inspection adds `bond_representation`;
raw comparison differences, numerical reviews and independent atom/H/charge/
stereo checks remain intact. Native diagnostics retain v3 receipt compatibility
and re-inspect supported v3/v4 candidates. Source-recovery console output names
blocked components and reasons. Offline reanalysis prepares all four returned
candidates with their OP2 H retained and the original model hash unchanged.

**Delivery history:** `07_Cedar_probe_cif_linked.py` was built from the checked Cedar revision with
`scripts/build_cif_linked_probe.py --delivery-prefix 07_Cedar`, using the pinned
NARestraints build source. Use delivery build worktrees and write the runner
into the everyday NASolve directory: macOS refused Python access to Downloads
before the Cedar 06 script could run. Preserve the frozen everyday checkout,
old deliveries and native sessions. These worktrees isolate pinned delivery
sources on the single Cedar development line; audit and retire them after the
linked qualification gate closes. Publish code, test/contract changes and
compact hash/count evidence only; unpublished coordinates, dictionaries and
native payload bytes stay outside Git. Installed Cedar 07 qualification,
numerical/achieved geometry review and full-auto recovery remain pending.

**Cedar 07 retry software validation:**
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q --tb=short`
passes **1,370 tests, two skips and 276 subtests (97.41 s)**. The initial
generator/native/preparation/qualification/shuttle focus passed **192 tests
(38.98 s)**; the final aromatic/orchestration focus passed **36 tests (1.84 s)**.
The two source-declared-ring acceptance regressions fail before the change and
pass after it. Negative controls retain rejection for partial/missing/conflicting
declarations, fused or charged rings, exocyclic and outside-ring changes,
altered H/formal charges/elements and invalid numerical targets. Existing
relocation tests delete original build checkouts and poison normal imports.
The same returned four candidates prepare offline, retaining source-specific
OP2 H. No new Phenix/Coot process ran in this validation environment.
Changed runtime files are `src/nasolve/cif_generation.py` and the linked/native
probe templates; source-bundled transport needs no new dependency. Inspection
schema 1 gains additive representation evidence, generation policy advances to
v4, and the native probe keeps completed v3 receipts readable. Generated
coordinate/CIF/native payloads remain excluded from Git. Descriptors,
machine-readable evidence and the editable figure/caption are updated together.

**Cedar 05 returned; Cedar 06 prepared (2026-10-14):** all 57 payloads in
`05_Cedar_dy4qx3qg_cif_native_review.zip` verify. Native interpretation completed
at exit 0 with 42 mappings, 38 intra-strand O3′–P links and zero coordinate
OP3/O3P. REVIEW is the worker's deliberate successful inventory status. Four
generic monomers still expect isolated OP3. The fresh trial has free 5′-OH
ends A:1/B:1/C:8/D:1; the older W trial's D:1 phosphate consent does not apply.

Source/effective audit also finds lost OP2 H in the CGY/IMC/DX ReadySet
definitions; only IGU's accepted candidate preserves its complete source state.
`06_Cedar_probe_cif_linked.py` therefore reuses existing source-preserving eLBOW
generation for rejected components before per-site preparation. It keeps all
raw inputs, numerical findings, model coordinates and NARestraints parameters.
Opt-in detailed native inventory checks actual monomers, all declared links,
exact custom target/weight coverage and pair/stacking parallelities, plus a
shared-code internal/free-OH IGU control. No runtime is installed on the
laptop, no frozen run is rewritten, and no ReadySet/refinement/adoption starts.

The Cedar 06 native generation return and next retry are recorded above.
Review the next prefixed capsule before considering integration or full-auto retry.
Source-state regeneration, linked mechanics and numerical/achieved geometry
remain separate verdicts. Known 5CM/DP reviews remain visible. Public source,
tests and contract updates belong on Cedar; unpublished input bytes remain
outside Git. Baseline Cedar's complete Linux suite passed 1,308 tests, two
skips and 276 subtests. Final new-suite validation is recorded below after
completion; offline/fake native tests are not installed Phenix evidence.

**Cedar 06 implementation's offline validation:**
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../check-venv/bin/python -m pytest -q`
passed **1,345 tests, two skips and 276 subtests (96.43 s)**. The focused
native/preparation/qualification/shuttle files passed **75 tests (25.07 s)**.
The assembled runner replayed the exact 05 ZIP offline, identifying IGU reuse
and CGY/IMC/DX source-state regeneration requirements. Actual IGU projection
removes OP3/HOP3/HO3′ and retains HOP2. Relocation tests delete both source
checkouts and poison normal imports; input corruption remains a preserved
failure capsule. The editable SVG was regenerated, rendered and inspected.
Regression controls reject changed targets/weights, duplicate planes, lost
links/H, incorrect types/charges, missing mappings and undeclared same-code
end states. The new native worker/detail interface is tested using explicit
fake installed APIs. No new Phenix/Coot execution occurred in this environment.

**Cedar 04 reproduction and Cedar 05 diagnostic (2026-10-12):** the returned
`04_Cedar_r2cunjcc_cif_generation_review.zip` verifies all 22 manifest entries.
The [compact repeat evidence](elbow-source-retention-evidence.json) records
exact parsed CIF/PDB atom-row equality to v3; only generation timestamps differ.
Native eLBOW completed in **22.019048 s**, with source retention and numerical
findings unchanged. The prefix is present in console, receipt, output directory
and review ZIP. This is reproduction and delivery evidence, not native-reader
or linkage qualification.

The new `05_Cedar_probe_cif_native.py` freezes an external diagnostic bundle
from the source-audit runtime stack and prepared model, with the accepted
candidate substituted only in the copied dictionary input list. The prior
generation probe hash-binds the source audit/raw ReadySet baseline and the exact
candidate receipt; explicit caller paths remain operational references.
Parameterized source precedence, torsion normalization and every recorded
ancillary PHIL/EFF/site-modification input are retained. The installation-bound
`phenix.python` worker inventories native readers, effective monomer/missing-atom
mapping and interpreted atom/proxy evidence. Its explicit native-parser PHIL
namespace adapter retains all definitions and rejects unused parameters.
The subsequently returned native inventory is recorded above. Success is REVIEW, with no
model replacement, optimization, ReadySet retry, adoption or certification.
The human descriptor and editable figure/caption reflect this diagnostic scope.
Final offline validation: **16 native-boundary tests pass (1.62 s)** using
explicitly fake installed APIs, **22 shuttle tests pass (9.48 s)** with deleted
source checkouts and poisoned imports, and **19 discovery/CLI tests pass
(0.48 s)**. The established full-suite command passes **1,308 tests, 2 skipped,
276 subtests (54.09 s)** after final mapping/provenance changes. Fake APIs verify
process, hash and reporting boundaries; they are not native Phenix evidence.
The figure was regenerated and rendered for visual QA. New schemas are
schema-1 native inspection/probe receipts and selected-bundle evidence; the
generation policy remains v3. Private crystallographic inputs stay outside Git.

**Native v3 source-state retention and visible ferry IDs (2026-10-12):** the
user returned the 22-file [source-retention capsule](elbow-source-retention-evidence.json).
Installed Phenix 2.2.1-6174 completed RM1/GDIIS generation with `--pH=low` in
**19.958581 seconds**. All 37 atoms, 39 normalized bonds, 14 hydrogen
attachments and zero formal charges are retained, including HOP2/HOP3.
**C2–N3 = 1.397 ± 0.030 Å**. The three sugar centers retain source coordinate
handedness under identical atom order. Five finite PSD plane reviews remain
visible. Candidate status is **CANDIDATE_REVIEW**, not adoption or chemistry
approval: source CIP/aromatic metadata is absent, generated signed chirality is
not equivalent metadata, and the dictionary group remains non-polymer rather
than DNA LINKING. The actual native log names RM1 even though the CIF header
says AM1; preserve both as provenance.

The immediately preceding return was a repeat of v2, with no `--pH=low`; it was
not a failed retention attempt. New ferries use a leading identifier such as
`04_Cedar_probe_cif_generation.py`; sessions and ZIPs carry the same identifier,
and ZIPs add their unique run token near the front. Console and additive schema-1
receipt fields identify the delivery/policy explicitly. The collaboration
contract records the user's preference for visible prefixes and one exact
terminal command. Older runs and explicit output paths remain intact.

Next: qualify an external candidate derivative against the original prepared
model and complete effective bundle, including source-derived DNA metadata,
site-specific internal leaving atoms, true ends/nicks, native parser/proxy
coverage and generic IGU/IMC/CGY/DX linkage. Current production linked profiles
cover only 1AP/DZ/DP/5CM. No old candidate/model is substituted into the fresh
campaign, no checkpoint is selected, and full-auto recovery remains pending
these native checks. Geometry/sticky-end stitching is a separate planned layer.
Validation of the naming/receipt change: **26 focused tests pass (6.36 s)**,
including relocation after deletion of the source checkout, preserved prior
runs, leading ZIP/run identifiers and invalid-prefix refusal. The established
full-suite command passes **1,269 tests, 2 skipped, 276 subtests (42.49 s)**.
The numerical generator policy remains v3; only delivery metadata/names and
console identification changed. Private source/candidate/model payloads stay
outside Git. No native Phenix/Coot invocation ran in this Linux validation.

**Optimized candidate and source-state retention (2026-10-12):** the returned
22-file capsule is checksum-verified in
[the native evidence record](elbow-optimized-state-evidence.json). Installed
Phenix 2.2.1-6174 selected underscored initial-geometry/hydrogen aliases and
completed optimization in **24.107482 seconds**, using **RM1/GDIIS**. IGU's
collapsed C2–N3 target became **1.387 ± 0.029 Å** with distinct coordinates.
The candidate still fails source-state preservation: HOP2/HOP3 were removed,
OP2/OP3 formal charges changed from 0 to −1 and phosphate orders became DELOC.
Four plane-angle reviews have positive-semidefinite Gram matrices and small
0.06–0.13° sum residuals; numerical REVIEW must not be labeled incomplete.

Generation-v3 requires the installed valued `--pH` option and selects `low`
as the generator's exact-input-chemistry mode. It explicitly leaves experimental
pH and intended crystal protonation unassessed. The candidate gate preserves
supported soft numerical reviews, while rejecting invalid/incomplete numerics,
unresolved plane compatibility and chemical-state changes. No source or old
run is overwritten, no individual target is guessed and no candidate is
adopted. The next laptop probe demonstrated source-state retention as recorded
above; native reader/polymer-link qualification and full-auto recovery remain pending.
The requested optimization option and the observed native backend are separate
evidence. Human/manuscript descriptors and the figure caption are current.
Final isolated Linux validation with the established full-suite command passes
**1,264 tests, 2 skipped, 276 subtests (43.26 s)**. Regressions cover exact valued
source-state control negotiation, refusal of missing controls or ignored
hydrogen preservation, complete soft reviews, impossible/missing/nonfinite
plane evidence, missing numerical coverage and collapsed coordinates. Native
source-preserving generation was pending at that validation; no native tool ran
in the Linux check. The subsequently returned native result is recorded above.

**Native generator CLI compatibility (2026-10-11):** the returned 18-file
[capsule](elbow-cli-compatibility-evidence.json) confirms installed Phenix
2.2.1-6174 rejected `--initial-geometry` before reading chemistry (exit 2,
2.071012 seconds). No new candidate was generated; original/frozen source
hashes survived. The wrapper had used a spelling from the documented option
table; the example uses a different alias. Generation-v2 now probes the exact
installed executable's help, negotiates advertised spellings/value semantics,
and refuses missing controls before chemistry. Help and executable hashes are
retained. Probe summaries now distinguish failed/rejected generation from
actual candidates awaiting review. The corrected native retry completed as
recorded above; this first CLI failure supplies no numerical-quality or
chemical-state verdict.
Final isolated Linux validation with the established full-suite command passes
**1,246 tests, 2 skipped, 276 subtests (42.81 s)**. New regressions cover dashed,
underscored and mixed flags, misleading help examples/prefixes, valued versus
switch controls, unsupported controls, help timeout/error and executable races.
The original failed receipt and run stay intact. Generation receipt schema 1 adds installed capability
evidence under policy `cif-independent-elbow-candidate-v2`.

**Fresh ReadySet defect generalized (2026-10-11):** the user returned a
checksum-verified 16-file capsule from the new combined DNA run. Preflight and
Phaser passed: **TFZ 13.10 / LLG 196, H 3**. PostMR correctly blocked IGU,
whose generated C2–N3 target is **0.000 ± 0.020 Å** and whose dictionary C2/N3
coordinates coincide. Other local targets are distorted; source HOP2/HOP3
were omitted and OP2/OP3 formal charges changed. This is actual numerical
generation, not a raw-graph copy. The
[evidence record](igu-readyset-generation-evidence.json) and
[synthetic descriptor](synthetic-dna-mechanics-test.md) preserve exact hashes.

The generalized assessor checks dictionary coordinate degeneracy and PostMR
records a component quarantine with exact atom/target diagnostics. The new
explicit `cif-doctor generate-candidate` API/CLI regenerates a whole component
from frozen chemical input plus complete supplier ideal-coordinate seeds; it
does not patch one bond or borrow MR coordinates/older prepared candidates.
A one-file probe selects invalid generic components and collects native
generation/comparison evidence into a review ZIP without altering the old run.
Native source-state preservation, candidate quality and generic polymer-link
qualification remain pending. Automatic adoption and a full-auto retry are
not claimed complete. Update the human overview/figure with each extension.
Final isolated Linux validation:
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,222 tests, 2 skipped, 276 subtests (43.87 s)**. Nine probe delivery
regressions use invented XRAWR/Q99/Y components, deleted original source
checkouts and poisoned imports; all runtime/source/review-ZIP hashes validate.
The source-bundled inspect-only probe also selects IGU from the real returned
capsule with its original source hashes verified. Native eLBOW optimization and
candidate acceptance were NOT_RUN here. The updated editable figure was
regenerated and rendered for visual QA. Changed runtime files are the assessor,
general candidate module, CLI/optional Phenix discovery and PostMR quarantine;
receipt schema 1 gains explicit dictionary geometry and generation evidence.
Private dictionaries and native outputs remain outside Git.

**Fresh combined DNA mechanics inputs (2026-10-11):** user authorized a new
synthetic K:X/B:S/Z:P/D:T test on copied donor diffraction with AutoSol off.
The [human descriptor and recipe](synthetic-dna-mechanics-test.md) own the exact
42 targets, real free-5′OH preparation, isolated one-file shuttle and limits.
This is an ordinary fresh source-acquisition/ReadySet test; no prior numerical
bundle or relaxed coordinates are substituted. Input preparation and campaign
policy are offline-tested; native laptop execution remains pending. The frozen
Cedar checkout is preserved and no pull is required to use the shuttle.
Final isolated Linux validation:
`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,124 tests, 2 skipped, 276 subtests (38.50 s)**. The nine shuttle
regressions include deleted source checkouts, poisoned laptop imports and exact
module-origin receipts. A separate stage-only check using the real local QiC
donor also produced a valid frozen DISCOVERED plan; no native programs ran.
Only code, the recipe and documentation enter Git. Generated donor copies,
receipts and standalone deliveries stay outside the repository.
The user has also returned a successful laptop execution of the public CCD
shuttle: all 18 source PASS / effective REVIEW / numerical UNASSESSED. That
result confirms the offline audit path, not native dictionary generation.

**Human overview, public ZIP runner and upstream data review (2026-10-11):**
The [human/manuscript descriptor](cif-doctor-human-overview.md) now explains
the implemented algorithm, tools, placement and limits, with an adaptable
methods paragraph and [editable SVG/layout source](figures/README.md).
`AGENTS.md` and the collaboration contract require descriptors and figures to
stay current when features change. No geometry/stitching capability is added.

The single-file `run_cif_doctor_ccd_controls.py` embeds the unchanged assessor
and required reader/normalizer code. SHA-256:
`e1d54f1dab5c5dde733aa65fcf9dd66a82b720b7ee753a9c589cf9946912680e`.
The exact previously delivered public ZIP runs offline with **18 source PASS,
18 effective REVIEW, 36 receipts**, every input unchanged and native tools
NOT_RUN. Graph-only numerical UNASSESSED is expected in source mode; effective
screening does not generate numerical dictionaries or run ReadySet.
The established laptop Python can run this artifact without installing or
pulling NASolve; it creates a fresh output folder beside the ZIP. The frozen
laptop source state remains separate from the published Cedar feature.

Validation with the same isolated environment: **12 shuttle tests pass**,
including exact receipt parity, unsafe/tampered ZIPs, exclusive output and
relocation with the original checkout removed. The complete NASolve command
below now passes **1,090 tests, 2 skipped, 276 subtests (36.37 s)** with the
corrected upstream workbook. Overlay tests explicitly cover both legacy DF
S2 mappings and corrected S1 mappings; the compatibility adapter is retained.

The separately reviewed NARestraints source workbook corrects 5BU/BRU sugar
metadata and abbreviations, DF/S6G mappings and all 129 literal C5 trailing
spaces. Its **138 exact cell changes** are documented in its Markdown/JSON
audit. Workbook SHA-256 after the patch:
`afed0f332c3d70cd14c395005fcbccf38201e2818bb9b765c86decda309707f5`.
All other cell values/types/styles, sheet order/dimensions, and unrelated
uncompressed XLSX parts are preserved. NARestraints passes **42 tests**;
the seven new regressions failed before their corresponding corrections.
This remains unreleased source data; the pinned v1.1.3/laptop installation
has not been updated. PSU's coupled attachment/base-plane issue stays open.
Native interpretation/refinement was not run for these metadata corrections.

Changed files are the overview/figure source and maintenance/index documents,
the shuttle builder/template and tests, and the legacy/corrected overlay test.
Shuttle schema 1 adds artifact-build provenance and output-anchored references;
existing NASolve runtime/checkpoint schemas and frozen runs are unchanged.
The manuscript PDF export, standalone runner and generated audits remain
outside Git; neither private coordinate/reflection data nor the public CCD
payloads are added. The existing native/proxy/geometry follow-up remains open.

**CIF Doctor implementation validation (2026-10-11, isolated Linux):**
Published implementation: Cedar **`8c181c5d47cd987318c48568f13d93ef6bdfbb87`**,
tree-equivalent to local **`105f2bb`** at tested tree
`fbaaab578c4737b35cbfd1fa145f1e153f1b86e0`. Subsequent handoff bookkeeping
does not change that tested runtime. The frozen laptop checkout remains untouched.

`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`
passes **1,077 tests, 2 skipped, 276 subtests (35.06 s)**. The five new Doctor
test files pass **88 tests and 7 subtests (1.05 s)** with the same environment.
Independent review is clear; source and run-adapter regressions exercise
relocation with the original paths removed, immutable selection and input-race
rejection. No native Phenix/Coot execution occurred for this implementation.

The final assessor source SHA-256 is
`7eb53fb2b8c1782fae9f3785a9ae2295baa664982237c01b5a5edf86ec496798`.
Fifty-six source/effective assessments cover **18 public CCDs plus 10 packaged
dictionaries** with every input byte preserved. All public CCDs pass graph
inventory with numerical parameterization unassessed; all need review when
presented as effective numerical dictionaries. The six exact historical
5CM/DF/DP replays preserve their hashes. The standalone comparison additionally
exposes the DF source/generated bond-order, aromatic, hydrogen, charge and
numerical-field differences without declaring which chemistry is correct.
The reviewed historical 5CM preparation reproduces `61bf14a…` exactly.

Changed runtime files are `cif_doctor.py`, `cif_doctor_repair.py`,
`cif_doctor_run.py`, `cli.py` and `postmr.py`; new schema-1 assessment,
comparison and preparation receipts are documented in the runtime guide.
Existing runs and legacy profile scopes need no migration. Public control
provenance is committed; downloaded CCDs and generated audit receipts remain
outside Git. A frozen public-only control capsule preserves 18 CCDs and
36 receipts (SHA-256 `085f4077828d1b5ee6503dfd73dbb9c89a87c7b3fff3779520809e77e67b042b`),
without private models, maps, reflections or diagnostic CIFs. Runtime native
proxy verification and dictionary/coordinate adoption remain open.

**GeoTest orchestration trial wrapped:** the corrected native rerun verifies
six numerically ready refinements, two bounded Doctor reviews and one MR failure.
All nine workers and 14 native refinements completed, the one-file parser fix
was installed with its original backup, and model/data space groups are recorded.
The three candidates blocked by the previous parser now progress past MR.
The user explicitly closes this campaign at its orchestration scope without
further scientific repair; preserve its provisional checkpoints and reviews.
The [guided arm-connection module](construct-registration.md#geotest-guided-arm-connection)
is now bundled into the planned Doctor workflow alongside data/Free-R diagnostics
and the generalized restraint assessor, using Scout/Topo primitives.

1. **CIF Doctor's first implementation slice is complete in this change.**
   User decision **2026-10-11**: build from the saved blueprint, screen source
   dictionaries before PostMR mutations and assess effective files after ReadySet.
   [The runtime guide](cif-doctor.md) owns the new commands and exact scope.
   Assessments are deterministic and read-only, with report-only pipeline hooks.
   Explicit preparation wraps existing supported torsion normalization and the
   exact reviewed historical 5CM correction; it does not adopt a new dictionary.
   The [machine-readable implementation map](cif-restraint-doctor-implementation.json)
   preserves the scientific cases, checks, ReadySet/PostMR placement, repair
   boundaries, cache keys and regression plan. Its runtime-progress section
   distinguishes this initial implementation from future recovery;
   collaboration/personality notes remain outside the repository.
   The 5CM/DF/DP evidence is sufficient to implement the first assessment slice;
   it does not yet establish general automatic repair. This proposed restraint
   doctor is distinct from the existing refinement-strategy `refine-doctor`.
   Public CCD access is verified. Eighteen public source graphs selected
   from NARestraints cover halogens, C-glycosides, L-DNA, missing O3′ and
   diphosphates. The workbook is pairing/target-selection evidence rather than
   a universal chemical authority. Recover and freeze the exact historical
   **8RO/DE and failed 1AP** inputs as additional challenge cases; synthetic
   connectivity regressions must remain labelled as reproductions. Apply the same rules before adding any new
   component-specific exception; include valid controls and retain unsupported
   findings. The [fixture plan](cif-restraint-audit-methods.md#learning-cases-and-future-regression-fixtures)
   distinguishes known defects, source adaptations and unresolved chemistry.
   **Doctor bundle decision, 2026-10-11:** retain the existing refinement/Free-R
   diagnostic module and add the restraint assessor plus model geometry and
   connectivity assessment under one coordinated workflow. The user attributes
   GeoTest's high Rwork to arms fractured at sticky ends; record that diagnosis
   as the motivation for examining the actual model/maps and intended assembly,
   not as a causal proof from Rwork. Check geometry/connectivity before choosing
   further refinement strategies, including numerically ready models. Guided
   stitching requires declared arm pairing, strand routing and symmetry mates;
   preserve true nicks/5′-OH termini and frozen Free-R, create a bounded child
   checkpoint and validate/refine it. The assessor remains the first slice;
   geometry integration is future work, not an additional Cedar/Pine merge gate.
2. **Bound the remaining combined-model numerical review.**
   The [native ledger](native-modified-pair-live-validation.md#dp-geometry-trial--n5-conflict-relieved-review-pending)
   records verified N5 relief and preserved chirality, links and pair coverage;
   modest residual strain remains. The user reports **base visual PASS** for
   the exact new model, with sugars explicitly unassessed by eye. Review the
   remaining sugar torsions and minimizer termination numerically before a
   full-qualification or scientific continuation decision; do not request another sugar
   verdict by eye or infer a dictionary defect from residual strain alone.
   These are bespoke component diagnostics. Park further multi-modified-model
   edits/refinement unless a specific unresolved finding needs fresh evidence.
   The user's optional multi-letter-edit continuation is not a prerequisite
   for starting the assessor, and is not being declared complete. Reuse the
   returned receipts; do not chase zero residual strain or repeat passed trials.
3. **Turn demonstrated preparation into ordinary fresh full-auto behavior.**
   The current trial used selected numerical CIFs in a frozen resource bundle
   and ad hoc linked derivatives. Acceptance is a new run from declared
   model/sequence intent and component codes, without per-run source patches
   or a hand-prepared bundle. Cover already-present modified residues as well
   as mutations; distinguish library acquisition/cache, numerical preparation,
   verified polymer context and a small justified override registry. This is
   the product goal, not an achieved result or an unlimited new Cedar gate.
4. **Close the existing bounded Cedar/Pine gates.** Retain the prior P1/P3/P4
   receipts and fill only missing effective-dictionary, normal-GZ11 and
   user-veto/current-pointer evidence. Source-native P2 and real P5 remain
   separate. Then integrated tests/review P6, Cedar→Pine and Pine→main P7
   with ancestry verification and audited retirement. Do not rerun passed
   cohorts just to refresh documentation.

The [component contract](modified-component-preparation.md) owns source
chemistry and overrides; the [native ledger](native-modified-pair-live-validation.md)
owns exact sites, hashes and returned stage results. **1W5→DZ and 1WA→DP
remain mandatory reviewed transformations; A1AAZ→DF is a label bridge.**
DE geometry remains unresolved. Q is implemented; DQ/S/DS aliases are not.
Lab S/DS means N-linked IMC, not S6G or C-linked hachimoji S. Ordinary
supplier copies must not become permanent exceptions merely because used.

## Optional GeoTest side trial

Requested **2026-10-11** as a separate exploratory run; the restraint-doctor
priority above remains active. The standalone `run_geotest_campaign.py` reads
`examples/GeoTest`, preserves outer design names, and schedules each coordinate
CIF/PDB model against each coherent nested processing set. It declares trust in
supplied coordinates without inventing sequence evidence or requesting sequence
mutations. One whole-model copy and 1.0 Å MR RMSD remain the search hypothesis;
no winning model/processing combination is selected.

**First native ferry verified:** all 192 included files match their recorded
hashes and sizes; 39 large/reflection files were deliberately omitted. The
user's **8/9 good** describes eight placed models, not eight MR gate passes.
The receipts show four `MR_SUCCESS`, two `MR_REVIEW` and three `MR_FAILED`.
These are the original recorded gates; the later selected-model score audit
below identifies why they undercounted good MR candidates:

| Member | TFZ | Verified stopping point |
| --- | ---: | --- |
| X11_12 | — | No MR solution |
| X11_16 | 7.0 | MR REVIEW |
| X11_17 | 8.0 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_18 / dataset1 | 6.0 | MR FAILED, placed model retained |
| X11_18 / dataset2 | 7.2 | MR REVIEW |
| X11_19 | 9.2 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_20 | 15.0 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_22 | 14.9 | MR SUCCESS; PostMR blocked by undeclared terminal OP3 |
| X11_25 | 6.8 | MR FAILED, placed model retained |

The placed-model space groups are **P2₁, P4₃ and P1**; the earlier user shorthand
P2₁2₁2 is not the P2₁ recorded in these files. This ferry used Phenix
**2.2.1-6174**, Coot **1.3.3**, Python **3.12.14** and clean Cedar
`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`. No completed refinement or Doctor
result is established by it.

**Real input preparation, not a repaired status:** the user explicitly clarified
that the strands are linear, with **free 5′ hydroxyls and no terminal phosphates**.
The updated runner copies the originals, validates CIF-to-PDB preservation, then
removes only complete P/OP1/OP2/OP3 groups at the seven declared chain starts.
All nine supplied member models lose exactly **28 atoms each**; O5′ and every
retained atom record remain unchanged. The prepared inputs pass the native
phosphate audit. Ambiguous/incomplete terminal groups block that member; internal
phosphates are not stripped. Preparation records exact deletions, hashes and
before/after audits. No fake sequence, phosphate allowlist or coordinate repair
is used. This corrected search model is the input to a **fresh** native preflight
and Phaser run; the original cohort and its failed receipts remain intact.

**One-launch full auto:** default endpoint is `refine-doctor`, using existing
native stage APIs and bounded policy. Eligible borderline MR continues with its
review warning; failed MR and chemistry/integrity failures remain blocked.
PostMR is followed by AutoSol when anomalous data warrant it, five-cycle
AutoRefine, and Doctor only for eligible `AUTOREFINE_REVIEW` (at most five trials
of three cycles). Unaccepted AutoSol phases are excluded. Verified successful
Doctor recommendations may be selected provisionally, without user approval or
overwriting checkpoint history; ordinary ready refinements need no Doctor trial.
Each member keeps its observations/Free-R and failures do not stop other members.

Every launch creates a fresh `geotest-fullauto-*` directory under the selected
output parent, with a frozen `geotest_recipe.json`, schema-2 adapter receipt,
per-member provenance, summary, compact `GeoTest_review.zip`, and
`View_results.command`. The final menu and double-click launcher open the exact
verified refined checkpoints/models/maps in Coot. Full observations/results stay
local. The single downloadable script is the adapter deliverable; these repo
changes document it and do not patch NASolve runtime or scientific inputs.

Offline validation: **76 tests, 20 subtests passed**, including all nine real
inputs, exact terminal deletions, original preservation, preparation before the
worker, full-auto handoffs, member failure isolation and exact Coot checkpoint
selection. The assembled script loads all embedded modules. An actual X11_20
model also passes real NASolve preflight and PostMR code without sequences,
using explicitly stubbed external MTZ/Phaser/ReadySet programs and fixture
reflections; this is not native execution. The unchanged core suite passes
**981 tests, 2 skipped, 257 subtests (29.58 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
The revised native run has now returned as described below.
This is **not native NASolveCampaign CIF/no-sequence support**. Integrating
declared terminal chemistry and preparation into a native single recipe/button
remains the product follow-up; this side trial does not close the formal blind
baseline, production input-adapter or geometry-qualification gates.

**Returned full-auto native run, 2026-10-11:** `GeoTest_review(1).zip`
(SHA-256 `7fdaeee177c3e3eed63d49fb280bb4314ad05a88f94c3564f78b244291e4b458`)
contains **361 verified files**, with **98 deliberately omitted** large or
reflection files. All originals remain unchanged. The laptop again used clean
Cedar `e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`, Python **3.12.14**,
Phenix **2.2.1-6174** and Coot **1.3.3**. This was a real native execution,
not the earlier stubbed integration check. The user reports success for the
trial's scope, with arm/triangle connectivity requiring further guided work.

| Member | Recorded TFZ: first → 5′-OH run | Selected-model final TFZ-equivalent: first → 5′-OH run | Returned full-auto result |
| --- | ---: | ---: | --- |
| X11_12 | — → 2.9 | no selected model | MR FAILED; no solution |
| X11_16 | 7.0 → 7.4 | 14.0 → 14.5 | AUTOREFINE READY, Rwork/Rfree 0.2940/0.3404 |
| X11_17 | 8.0 → 5.1 | 12.3 → 12.2 | Recorded MR FAILED; refinement not attempted |
| X11_18 / dataset1 | 6.0 → 7.8 | 7.8 → 7.7 | REFINE DOCTOR REVIEW, inspection 0.4691/0.4859 |
| X11_18 / dataset2 | 7.2 → 6.2 | 8.0 → 8.0 | Recorded MR FAILED; refinement not attempted |
| X11_19 | 9.2 → 9.9 | 13.3 → 13.8 | AUTOREFINE READY, 0.2421/0.2890 |
| X11_20 | 15.0 → 15.2 | 17.0 → 16.9 | AUTOREFINE READY, 0.2262/0.2336 |
| X11_22 | 14.9 → 15.2 | 15.2 → 15.3 | AUTOREFINE READY, 0.2647/0.2770 |
| X11_25 | 6.8 → 6.1 | 9.6 → 9.8 | Recorded MR FAILED; refinement not attempted |

All eight native refinement processes exited zero (five ordinary refinements
plus three eligible Doctor trials). Four ready results are `refine-001`.
X11_18/dataset1 remains REVIEW: inspection checkpoint `refine-002`, current
checkpoint `postmr`, no recommendation or provisional selection. Numerical
readiness does not certify intended triangle connectivity. Native reports still
leave bond/angle RMSD summary fields null despite geometry values in the raw
Phenix output; do not infer a clean geometry verdict from those missing fields.
The compact ferry omits MTZs, so reflection/Free-R preservation is supported by
native receipts/audits rather than an independent replay of omitted arrays.

**Apparent MR loss is a score-association defect:** all nine original model,
reflection and metadata hashes, all 46 NASolve source hashes and normalized
Phaser settings match between runs. Search models differ only by the declared
28 terminal-atom removals; every retained atom record is unchanged. The parser
previously took the first TFZ/LLG from each solution-history line. Phaser writes
later `TFZ==` values after orientation refinement; these must be associated with
the selected output model, not maximized across unrelated solutions. See the
[Phenix annotation reference](https://www.phenix-online.org/documentation/reference/phaser.html#annotation).
For X11_17 the selected output records `TFZ=5.1` followed by `TFZ==10.8` and
`TFZ==12.2`; its final LLG is 353, rather than the initially parsed 304.
Both cohorts therefore contain **seven selected models meeting the ≥8 gate,
one borderline model and one no-solution case** when audited by final associated
scores. This is a retrospective evidence assessment, not a rewrite of old
statuses or a claim that the three newly eligible candidates were refined.

**Parser fix validation:** selected-output annotations, final score/LLG
association, matching PDB/MTZ stems, ambiguous/invalid headers and legacy
single-output fallback pass **17 focused tests and 12 subtests**. The complete
suite passes **989 tests, 2 skipped, 269 subtests (32.75 s)** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../docs-check-venv/bin/python -m pytest -q`.
The worker/preflight/full-auto-driver checks also pass **54 tests**. Read-only
parsing of all 16 actual selected PDBs reproduces the table above. The report
adds versioned `score_evidence` and selected-output checksums; existing fields
and TFZ thresholds remain compatible. This initial validation did not rerun
native Phaser or change any old receipt. The subsequent fresh laptop run below
installed the small fix at the recorded diagnostic head; do not pull a different
head over that distinct local state merely to replay these results.

**Authorized laptop rerun shuttle:** the user requests a fresh run with the
corrected parser and space groups in final output. The updated standalone
script accepts `--install-parser-fix`. It verifies the exact 46-source laptop
manifest (including the laptop's distinct `curated_ligands.py`), compiles and
checksums the embedded replacement, backs up original `phaser.py` in the fresh
workspace, preserves permissions and atomically installs only the known parser
update before loading it. Old parser SHA-256 is
`d277a10e4a6c7b843c3e5cd1af4b09dd835872054b7b3cd887f9215177788331`;
replacement SHA-256 is
`18aedbb3b414d2dd86e8c284219ca078e682e08003a8f82637f2b462d23a3570`.
Unknown local edits or compatibility drift stop the update; an exact installed
replacement is an idempotent no-op. This explicitly authorized one-file update
leaves Git dirty at the existing laptop head. Do not replace the whole checkout
or pull remote Cedar over the distinct diagnostic state.

The resulting fresh run retains the prior 5′-OH input policy and full-auto
bounds. Terminal final output, `campaign_summary.csv` and the Coot menu show
the exact displayed checkpoint's space group, falling back to the selected
Phaser model. The checksum-verified input MTZ header is retained separately;
when no model exists its space group is labelled as data-derived. Receipts add
`space_group`, source/artifact/hash provenance and `input_space_group`; absent
metadata remains explicit and cannot alter MR/refinement status.

Validation: **94 adapter tests and 22 subtests pass**. The assembled download
also passes parser installation, original-code backup, actual X11_20 terminal
preparation, source-preserving staging and a second already-fixed launch.
That integration is offline: reflection metadata are fixtures and only the
unavailable laptop-specific curated-source manifest entry is substituted with
the local fixture's hash. That offline check launched no native Phenix process;
the subsequent returned native rerun is verified below.

**Corrected native run and close-out, 2026-10-11:** `GeoTest_review(2).zip`
(SHA-256 `8ef30e37729d74631eae8b91b0ac1d04c52f4879cb5d96c0f9f30addc7c0a9f9`)
contains **462 hash/byte-verified files** and **138 declared compact omissions**.
The runtime reports Python **3.12.14**, Phenix **2.2.1-6174** and discovered
Coot **1.3.3**; the native batch completed in about 13 minutes. All nine workers
exited zero; 44 stage
snapshots, nine final native reports and per-case provenance match the aggregate.
The installer verified 46 source files, preserved the exact old parser backup,
and changed only `phaser.py` to the fixed hash above. Original inputs and all
other source hashes remain unchanged. All nine preparations remove exactly 28
terminal phosphate atom records; every other byte is preserved, including O5′,
and their native frozen search models match the preceding 5′-OH cohort.

| Member | Displayed space group | Final selected TFZ | Returned result | Rwork / Rfree |
| --- | --- | --- | --- | --- |
| X11_12 | P6 (input data only) | — | MR FAILED; no selected model | — |
| X11_16 | P2₁ | 14.5 | AUTOREFINE READY, refine-001 | 0.2940 / 0.3404 |
| X11_17 | P2₁ | 12.2 | AUTOREFINE READY, refine-001 | 0.2165 / 0.3325 |
| X11_18/dataset1 | P2₁ | 7.7 | Doctor REVIEW, inspection refine-002 | 0.4691 / 0.4859 |
| X11_18/dataset2 | P4₃ | 8.0 | Doctor REVIEW, inspection refine-002 | 0.3230 / 0.3418 |
| X11_19 | P4₃ | 13.8 | AUTOREFINE READY, refine-001 | 0.2421 / 0.2890 |
| X11_20 | P1 | 16.9 | AUTOREFINE READY, refine-001 | 0.2262 / 0.2336 |
| X11_22 | P1 | 15.3 | AUTOREFINE READY, refine-001 | 0.2647 / 0.2770 |
| X11_25 | P2₁ | 9.8 | AUTOREFINE READY, refine-001 | 0.2781 / 0.3179 |

All eight selected-model final TFZ/LLG annotations and displayed checkpoint
CRYST1 records match their checksummed provenance. X11_18/dataset2 and X11_19
have selected/refined **P4₃**, while their input headers remain **P4₁**; retain
both values. The user notes that X11_18's alternatives are different space
groups: the P4₃ inspection result has markedly lower Rfree (**0.3418**) than
the P2₁ / `P 1 21 1` result (**0.4859**) and analytically favors P4₃. Record
this as the user's structural interpretation and comparative evidence, without
changing either review/selection status. The two processing datasets have
distinct observation hashes and Free-R populations; this is not a controlled
same-data space-group ranking. Exactly **14 native refinement processes exited zero**: eight
ordinary refinements and six Doctor trials. Every command keeps original
`IMEAN,SIGIMEAN` observations, `FreeR_flag`, test value 0 and `generate=False`;
each of the eight registries retains its member's original observation hash. Both X11_18
cases keep current `postmr`, inspection-only `refine-002`, no recommendation
and no automatic selection. Their audits remain `NOISY` (546/10377 and 223/3937
free groups) with zero detected inconsistent flags and the explicit unavailable
Friedel-mate comparison limitation. Omitted reflection arrays were not replayed.

No infrastructure blocker remains. The user reports campaign success and asks
to wrap without further scientific repair. All members retain provisional,
inspection-required and unapproved status. In particular, X11_17 passes the
current numerical gate despite a **0.116 Rfree−Rwork gap** and **66.93 clashscore**;
the bond/angle RMSD summary limitation and local assembly/geometry issues remain.
These are fixtures for the planned Doctor geometry module, not approval of the
structures. Native campaign input/recipe integration remains separate future
work; this closes the standalone GeoTest orchestration test.

**Guided geometry follow-up:** the user requests geometry assessment and a
Scout-based guided arm/triangle stitcher bundled with Doctor, available after
MR or refinement once intended connections are declared. The
[contract](construct-registration.md#geotest-guided-arm-connection)
and [live-check queue](construct-registration-live-checks.md) retain this as
planned scope. The supplied Coot examples are `Screenshot 2026-10-11 at
13.53.45.png` (SHA-256
`215ae2967cb6fb5225d141636c766102c641bd87cfe000d7280bd246dd12d25f`) and
`Screenshot 2026-10-11 at 13.56.53.png` (SHA-256
`53fbade3270de9c19c9fc107a87d41a2b9cb7ba66836b5dd04a9c1ca3511e59b`).
They show local model/density discrepancies, without identified checkpoint or
residue selection; no atom-level connection is inferred from the pictures.
Original screenshots, coordinate models and reflection data remain outside Git.

## Restraint doctor and subsequent roadmap

The October 11 priority decision advances the **SMILES-assisted CIF/restraint
assessor** to the first implementation slice of the coordinated Doctor workflow
using the completed trials as evidence. Remaining combined-model qualification
stays explicit and may proceed
alongside it. The Doctor geometry/connectivity module will reuse Scout/Topo
primitives for guided repair; broader Topo slicing / operational Scout remains
later work. None becomes an additional Cedar/Pine merge gate.

- **SMILES-assisted CIF audit (planned, not implemented):** assessment first,
  comparing molecular graphs with atom mapping, charge/H/stereochemistry and
  descriptor provenance. Keep self-consistency separate from independent
  chemistry, and graph checks separate from numerical-restraint validation.
  Reviewed transformations such as 1W5→DZ remain explicit. Follow the initial
  assessor with separately tested, policy-bounded generation/validation and
  automatic continuation for ordinary passing cases. Exact reviewed repairs
  need version/hash policies; ambiguous chemistry needs declared intent, not
  an AI guess. Ordinary runs should not require AI or user source patches. The
  detailed [assessor and automation contract](modified-component-preparation.md#proposed-smiles-and-cif-audit)
  owns findings, uncertainty and repair boundaries. The
  [audit methods](cif-restraint-audit-methods.md) capture the reusable checks,
  5CM/DF/DP lessons, 8RO/DE and 1AP challenge cases, and proposed evidence schema
  for implementation. Broader repair requires those checks and negative controls,
  not merely successful regeneration of the three development cases.
- **Blind AlphaFold baseline after bounded Pine close-out:** preserve frozen
  predictions, observations and Free-R; avoid solved outcomes during blind
  candidate selection. Before this trial, add **PDB and coordinate mmCIF input**
  and an explicit **trust-model / no-sequence-file mode**, since supplied
  predictions may have no separate sequences. These are requested adapter
  capabilities, not implemented options. Record sequence as independently
  unverified, skip sequence-driven mutations, and retain ordinary model/MR
  checks. See [model roadmap](campaign-model-roadmap.md) and
  [architecture](architecture.md) for the proposed contract.
- **Campaign input follow-up:** support shared parent-folder models and nested
  processing datasets, including alternative space groups. Inventory/count
  candidates, run selected MR alternatives separately and compare their evidence.
  [Grouped-processing design](campaign-model-roadmap.md#planned-shared-model-folders-and-processing-alternatives)
  records the requested behavior; current flat discovery does not implement it.
- **Then operational Scout / later Topo surgery**, following the existing
  [registration contract](construct-registration.md) and
  [live checks](construct-registration-live-checks.md). The earlier order
  (blind AlphaFold baseline before operational Scout) remains. GUI/Topo Net
  and the metal-restraint builder remain separate later scopes.

## Evidence and preservation

The combined trial uses real GZ11 observations with hypothetical target
modifications: it is a software integration test, not proof of the crystal's
chemistry or deposition approval. Native completion, chemistry, numerical
metrics and human review remain separate verdicts. The earlier Z:P overall
Coot PASS is not a combined-model geometry verdict. The earlier directional
hydrogen-bond question remains parked; never impose an arbitrary heavy-atom
180° target or modify the successful old run to satisfy it.

Follow the [branch/worktree lifecycle](collaboration.md#branch-and-worktree-lifecycle).
One terminal action per user turn for native debugging, then inspect output.
Preserve the original dirty NASolve checkout, unpublished NARestraints
`Ligands.xlsx`/lockfiles, scientific runs, maps and Free-R. October 8–9
completed-worktree cleanup remains recorded in the backup; the private
lab-notes checkout was intentionally retained. Verify current laptop status
before integration; the returned clean Cedar check does not authorize cleaning
other laptop checkouts or changing the unpublished diagnostic head.

**Status ownership:** this handoff = current priorities; native ledger =
exact trial evidence; subsystem docs = durable contracts; history/Git =
earlier decisions. The October 10 reconciliation archives superseded text
before shortening it and keeps chronology out of the active queue.
