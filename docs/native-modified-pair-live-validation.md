# Native modified-base pair matrix — live validation ledger

Updated **2026-10-10** from returned user-native terminal output.
**Combined W: PostMR PASS; generic linkage mechanics PASS; custom restraint
coverage recorded; geometry qualification PENDING.** The combined geometry
trial has not yet been run. This updates the earlier
[exact ledger snapshot](history/native-modified-pair-live-validation-2026-10-10-pre-reconciliation.md.txt).
See the [handoff](development-handoff.md) for current priorities.

## What is actually green?

- [x] NARestraints v1.1.3 released/installed, corrected Z:P/K:X roles;
  committed workbook unchanged.
- [x] PR #24 W Saenger overlay and PR #25 pathless viewing merged into Pine.
  Earlier Z:P `run_003/refine-001`: numerical SOLVED and overall user visual PASS.
- [x] Installed IGU/IMC/CGY/DX CCD lookup and isolated Coot construction.
- [x] Frozen combined 42-target preflight, Phaser and PostMR.
- [x] Native interpretation, fresh IMC structural audit and linked diagnostic.
- [x] Exact custom-restraint target/weight coverage and duplicate checks.
- [ ] Effective sugar/glycosidic torsion and phosphate-protonation qualification.
- [ ] New combined geometry/refinement trial, numerical metrics and per-site
  human Coot/.geo review.
- [ ] Fresh ordinary full-auto run without preselected numerical resources
  or ad hoc linkage scripts.
- [ ] Independent source-native P2 and geometry-diverse real P5 gates.

**Evidence boundary:** Phenix **2.2.1-6174**, Coot **1.3.3**, NARestraints
**1.1.3** were used in the native work. The supplied terminal record contains
returned results and receipt paths, not the complete audit JSON/model files;
this documentation pass did not rerun or independently reopen them on the
laptop. Its scripts verify a frozen local Cedar head without printing its SHA.
Remote Cedar `a7edddf` and the earlier `1443979` regression receipt must not be
substituted for that unknown local head.

Real GZ11 observations carry **hypothetical modified target chemistry**.
Software success is not experimental identity validation or deposition approval.
Independent A:T/D:T/B:S/Z:P/K:X datasets remain optional diagnostic controls,
not a replacement for the combined test or an additional mandatory rerun.

## Frozen combined model and receipts

Provenance anchor **LIVE** is the user's `~/NASolve-live-tests` directory.
Combined root **COMBINED** is `LIVE/cedar-combined-w-cb3h3414`;
run **RUN** is `COMBINED/dataset/AutoMR/run_001`;
probe **PROBE** is `RUN/NativeInterpretation/probe-tfv94ryc`.
These are retained evidence locations, not portable executable configuration.
All relative paths below resolve against these explicit anchors.

| Role | W pair sites | Original W geometry | Target component codes | Reviewed recipe |
| --- | --- | --- | --- | --- |
| **D:T** | **A:5 / C:11** | A:T | **1AP / DT** | `D_T`, distinct D-family chemistry |
| **B:S** | **A:6 / C:10** | G:C | **IGU / IMC** | `GC` geometry with B=G-like, S=C-like |
| **Z:P** | **A:12 / B:4** | A:T, in explicit `Std_padd` | **DZ / DP** | `GC` geometry, P=G-like, Z=C-like |
| **K:X** | **A:20 / D:3** | C:G | **CGY / DX** | `GC` geometry, X=G-like, K=C-like |
| Prior 5CM:G context | A:7 / C:9 | C:G | **5CM / DG** | `GC` geometry |
| Prior DF:A context | A:19 / D:4 | T:A | **DF / DA** | `AT` geometry |

This layout has no shared paired-site ownership, but A:5/A:6/A:7
form *adjacent* backbone positions, deliberately stressing simultaneous
restraining and packing. The `GC` and `AT` designations are shared
**restraint geometry templates**, not canonical identity substitutions.
**D:A has no registered recipe**: `D:T` uses 1AP and DT, whereas
`DA` is canonical DNA adenine. The test must never fabricate a
`D:A` pair or write `force = G:C`.

### Frozen targets and native preparation

The candidate layout above was staged and checked, superseding the October 9
“not staged” status. Compiled targets, with source A:19 `(A1AAZ)` prepared as DF:

```text
A: DG DA DG DC 1AP IGU 5CM DC DT DG DT DZ DT DG DG DA DC DA DF CGY DA
B: DC DC DA DP DA DC DA
C: DG DG IMC DT DG DC DT
D: DC DT DX DA DT DG DT
```

- Preflight: **READY_POST_MR_MUTATION**, 42/42 targets, D:1 terminal phosphate.
- Phaser: **MR_SUCCESS**, TFZ **12.9**, LLG **210**; source inputs preserved.
- PostMR: **POSTMR_READY**, 42/42 targets, `mismatches=[]`;
  **17 → 12 retained + 5 replaced** Saenger blocks, **8 explicit pairs**,
  stacking enabled, **13 effective restraint inputs**. All four frozen
  generic dictionary hashes verified. OP3 removed at A:5/6/7/12/19/20,
  B:4, C:10 and D:3 before restraints; none removed after ReadySet;
  D:1 terminal phosphate preserved.
- Receipts: `COMBINED/manifest.json`, `RUN/postmr_receipt.json`,
  `RUN/postmr_driver.log`; model `RUN/PostMR/Model/readyset_model.pdb`.
  The source bundle is `COMBINED/resource_bundle/data`.
- Optional local replay fixture `LIVE/fixtures/nasolve-synthetic-combined-w-v1.zip`,
  SHA-256 `9fcd0f70a646045156158a85e4fd7cedff833729bce49a0271502acf48b272a3`,
  preserves the **PostMR baseline only**, not geometry qualification.
  Its prepared dictionaries mean replay is not a fresh acquisition test.

### Dictionary availability is a hard prerequisite

Phenix CCD graph sources are available; IGU/IMC/CGY/DX remain unbundled in
NASolve. The installed sources lack numerical refinement targets. Cedar's
resolver deduplicates symlink aliases and rejects distinct competing sources.
A successful raw lookup alone cannot qualify numerical geometry.

| Code | Installed CCD SHA-256 | Original frozen numerical candidate SHA-256 |
| --- | --- | --- |
| IGU | `1ddaaef74adafd0e989679ec9cf2197d7a8590002c472f8d6b764f52202e3a8f` | `c514301d826d8d98dbe9dfc5aac86f3b9bfbba859c56e9f691a674431f3d9e06` |
| IMC | `c3e62ba98565139cf13b9bcab4a977193f28e2c05e83455ec5fb72721732664c` | `94f0f5a8052a08fedb95e134ba2801416540c4ceb7290024dde84e055db7ffab` |
| CGY | `14a94801736e8a86d9b123e58e1dcef52b3f5e61475b87870f55f181f122466d` | `3c5be2c4660fc99ca5c013d5461d944c040e2fc178360601e46eb367068f9367` |
| DX | `6bcf650c0dabdabc1b95b99354b91cc8f4874f112703f871e85211dd40ea6fb0` | `4384a13bace6c74a1c73cd6c803aa752b412a2e9ce249dfd2bb932e5d5b28450` |

The trial selected parameterized candidates manually before PostMR. ReadySet
completion therefore does **not** establish automatic generation from those
four raw CCDs. Nor does it establish an automatic AceDRG fallback.

### Interpretation and IMC follow-up

`PROBE/native_audit.json`, `combined_W.geo` and `native.log` recorded native
interpretation exit 0, 42 mappings, no unused PHIL or unexpected mappings.
The initial monomer dictionaries still expected OP3 at the four internal generic
sites. Incoming O3'–P links were present (target **1.607 Å**, sigma **0.012 Å**,
observed **1.5955–1.6203 Å**); a link alone did not apply the needed monomer edits.

`PROBE/geometry-followup-dpu8soly/audit.json` exposed an old IMC sugar torsion
using base **C2** instead of **C2'** in `C4' O4' C1' C2` (91.75° deviation),
and active torsion/protonation questions elsewhere. Graph consistency alone
would not catch this numerical-restraint reference error.

Fresh IMC was generated from the frozen source with AceDRG (`-K -p`):
`LIVE/cedar-cgy-acedrg-0bjcghxa/generate-imc-l3c4njhk/IMC.cif`, SHA-256
`2a753de61b9f5264645f7a3934e50baa5c117d7178423dcadbb84462274ab7ca`.
Its `semantic-audit-p5xne9kj/audit.json` reported structural checks true:
**37 atoms / 21 heavy / 38 bonds**, unchanged graph, elements, formal charges
and hydrogen attachments; correct sugar chirality and DNA group; C1'–N1 target
**1.478 Å**, sigma **0.0146 Å**. Large active torsion deviations still require
review. This candidate was substituted only in the later diagnostic derivative.

Two unsuccessful introspection probes are preserved:
`PROBE/phosphate-profile-m4041t96/audit.json` (assumed absent `DEL_OP3`) and
`PROBE/phosphate-inventory-wv8036j4/audit.json` (assumed native `DA` rather
than `Ad`). Corrected `mapping-inventory-8q5j38cb/mapping_audit.json` recorded
**NATIVE_MAPPING_INVENTORY_RECORDED**, with matching baseline counts.
Native canonical mappings are Ad/Gd/Cd/Td; `rna3p` has no attached monomer
modifications. Legacy `NA-STAND` atom names do not match all generic sources.

### Linked diagnostic — mechanics pass, chemistry still pending

**LINKED** is `PROBE/generic-linked-probe-1dp9rx4o`.
`LINKED/linked_audit.json` and `driver.log` report
**GENERIC_LINKAGE_MECHANICS_PASS** with fresh IMC substituted.
Graph-based leaving-atom/H deletion and O3' type `OC2` were verified;
retained dictionary rows otherwise matched exactly, no orphan H or dangling
references remained, no missing heavy atoms were reported, incoming/outgoing
links were preserved and every selected P had four model neighbors.
Original and diagnostic input checksums matched; D:1 remained protected.

| Site / code | Deleted atoms | Retained OP2 hydrogen | Resulting component formal charge |
| --- | --- | --- | --- |
| A:6 IGU | HO3', OP3 | none | −1 |
| C:10 IMC | HO3', HOP3, OP3 | HOP2 | 0 |
| A:20 CGY | H3'2, HO3', OP3 | H1 | 0 |
| D:3 DX | H1, H6, OP3 | H14 | 0 |

Atom names do not determine their attachment: CGY HO3' is OP3-bound;
DX H1 is OP3-bound and H6 O3'-bound. **OP2 protonation was retained from each
chosen source**, not chemically standardized or approved. Formal component
charges here are not comparable to the canonical library's partial charges.

Native proxies: **1015 simple bonds / 0 ASU bonds / 1574 angles /
513 dihedrals / 313 constant dihedrals / 155 chirality /
53 planarity / 58 parallelity**. These totals establish interpretation,
not achieved geometry or general handling of ends/nicks/cyclic/symmetry links.

### Custom restraint coverage — latest returned boundary

`LINKED/geometry-coverage-kczyxyyc/coverage_audit.json` and `coverage.log`
report **CUSTOM_RESTRAINT_COVERAGE_RECORDED**:

| Configured restraint | Matched target and weight |
| --- | --- |
| Bonds | 21 / 21 |
| Angles | 34 / 34 |
| Planarity | 8 / 8 |
| Parallelity | 23 / 23 |

Plane origins: **45 covalent + 8 edits**. Parallelity origins:
**23 edits + 12 base-pair parallelity + 23 base-pair stacking**.
**0 exact duplicate planes, 0 exact duplicate parallelities, 0 parallelity
support-overlap candidates.** Geometry qualification remains **PENDING**.

## Next native boundary

Audit the **effective linked** sugar/glycosidic torsions (atom quartets,
periodicity, active weights, achieved angles) and source-dependent phosphate
protonation; resolve demonstrated defects before a new geometry trial.
Record resulting numerical refinement metrics and all six paired-site,
backbone, phosphate, sugar, stacking, clash/map and .geo observations.
Human verdict must name the new model/checkpoint, date and exact effective
restraints. Earlier Z:P visual approval cannot be transferred to this model.

Production integration and a fresh ordinary full-auto acquisition test remain
separate from these successful diagnostics. The planned SMILES audit follows
this geometry trial; see the [roadmap](development-handoff.md#roadmap-after-the-combined-geometry-test).

## Historical Z:P attempts — preserved, never rerun in place

Frozen root:
`~/NASolve-live-tests/zp-paired-native-oiipj_t2`.

- `attempt_001 / AutoMR/run_001`: Phaser MR_SUCCESS, TFZ **12.9** /
  LLG **210**. NARestraints v1.1.2 assigned Z the G-like GC role and
  failed PostMR: **Z has no mapped N2**. Original log retained.
- `attempt_002 / AutoMR/run_002`: corrected upstream-role candidate;
  native PostMR **READY**, correct `P.N2/Z.O2`, `P.N1/Z.N3`,
  `P.O6/Z.N4` (**3/3**), 42/42 sequence targets, zero mismatches,
  `A1AAZ→DF` reviewed. AutoSol skipped with zero anomalous candidates.
  AutoRefine **BLOCKED before refinement** on W Saenger class 20 at
  DF A:19/DA D:4; class 19 also affected 5CM:G. Do not erase failure.
- `attempt_003 / AutoMR/run_003`: detached NASolve PR #24 candidate
  replaced exactly the two obsolete classes with explicit reviewed
  NARestraints pair geometry, keeping 15 canonical W pairs.
  PostMR/identity/phosphate audits PASS; native Phenix
  **`SOLVED/refine-001`**, frozen integrity OK; user Coot visible
  bonds/planes **INSPECTED_PASS (overall)**. Model/map paths were
  `AutoRefine/round_001/refined_001.pdb` and `refined_001.mtz`.
  This earlier verdict is distinct from the later combined trial below;
  experimental chemistry remains unverified.

**Separate angle research note:** user observed that some displayed
hydrogen-bond contacts looked tilted relative to a wished-for straight
N1/N3–O4/N6 alignment. Later inspect the actual donor–H–acceptor
definitions and hydrogen-bond angular restraints; do **not** blindly impose
a heavy-atom 180° target, exaggerate planarity, or modify the successful
historic `run_003`. This is not a `show` or Z:P role bug.

## Preservation and scope

Preserve original models, raw CIFs, frozen runs, maps, Free-R and failed probes.
Do not commit the user's native data or dirty/unpublished NARestraints workbook.
The mandatory 1W5→DZ/1WA→DP transformations, A1AAZ→DF label bridge and unresolved
DE geometry retain their [component-contract scope](modified-component-preparation.md).
The original independent five-case stager remains available in released
NARestraints for later failure isolation. Source-native P2, real nonstandard P5,
noncanonical I:C/A:G/G:T geometry and operational Scout/Topo remain distinct
unfinished work; neither this combined preparation nor the older Z:P result
closes them.
