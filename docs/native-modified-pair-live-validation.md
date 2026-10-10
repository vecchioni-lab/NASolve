# Native modified-base pair matrix — live validation ledger

Updated **2026-10-10** from returned native output and the supplied, checksum-verified
geometry and DF candidate bundles.
**Combined W: PostMR PASS; generic linkage mechanics PASS; custom restraint
coverage recorded; 5CM/DF defects identified; DF candidate source audit PASS;
corrected native interpretation and geometry qualification PENDING.** The
combined geometry minimization trial has not yet been run. This updates the earlier
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
- [x] Supplied geometry bundle verified against all 23 manifest hashes; active
  5CM and ReadySet DF defects identified.
- [x] Fresh DF generated natively; separate source-graph/numerical-reference audit
  passed, without adopting it into the combined run.
- [ ] Native adoption of the narrow 5CM correction and linked DF candidate.
- [ ] Effective sugar/glycosidic torsion and phosphate-protonation qualification.
- [ ] New combined geometry/refinement trial, numerical metrics and per-site
  human Coot/.geo review.
- [ ] Fresh ordinary full-auto run without preselected numerical resources
  or ad hoc linkage scripts.
- [ ] Independent source-native P2 and geometry-diverse real P5 gates.

**Evidence boundary:** Phenix **2.2.1-6174**, Coot **1.3.3**, NARestraints
**1.1.3** were used in the native work. The later laptop check reports clean
Cedar **`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`**, matching the frozen
combined manifest. This local unpublished head must not be replaced by a remote
head or pulled over merely to continue the diagnostic. Earlier test counts do
not certify its unidentified changes. The supplied bundles were inspected in a
separate analysis environment; that analysis is not a new Phenix execution.

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

### Custom restraint coverage — preserved baseline

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

## Effective-geometry findings and bounded recovery

The supplied `combined_geometry_evidence.zip` has SHA-256
`9aefce71cfe1d2c73c7f86f4379cb1d76dd24410e3f77cbf259338449beae551`;
all **23** manifest entries matched their hashes. It preserves the linked model,
**15 effective inputs**, native audits and `.geo` evidence. It is separate from
the earlier PostMR-only replay fixture and is not committed scientific data.

### 5CM — confirmed active torsion defect

The frozen `inputs/06_07_5CM.cif` has SHA-256
`38378c7df4eef73a0bd2be40059b2c3dd2b98618a4eeb7e91f6ec3427f7e7858`.
Its `C2e-nyu0` term uses **C4' O4' C1' C2**, with base C2 in place of sugar
C2': target **340.7°**, sigma **6.3°**, period **1**. A separate C3e term uses
the correct C2' quartet at **2.8°**, sigma **6.1°**. The wrong quartet is active
in native interpretation with a residual of approximately **481**: this is a
real restraint blocker, not merely starting-model strain. Source-byte equality
recorded on October 9 did not establish correct geometry.

A scratch-only proof changed that one atom reference and then used the existing
CCP4-alternate normalizer. It produced one correct quartet with primary
**340.7°**, alternate **2.8°**, retaining the first-row sigma **6.3°**. No
supplier target was guessed. This derivative has **not yet been adopted or
verified by native Phenix**, and the frozen source remains unchanged.

### DF — generated replacement passed source audit, native adoption pending

The effective ReadySet DF supplement (SHA-256
`b6f935aaef73562d34f500222071fc658dec5b2ddb41ed3b1d88153372170f20`)
contains aromatic sugar typing/bonds, single C4–O4 at **1.384 Å**, single C2–S1
at **1.812 Å**, and no active DF sugar chirality restraints. This is distinct
from the bundled DF/A1AAZ graph source and its valid short-label bridge.

The user generated a new candidate under **DF-CANDIDATE** =
`LIVE/combined-df-candidate-rbb1_cpv`, using the prior IMC environment:
AceDRG **334** (database **12**), RDKit **2026.09.1**, Servalcat **0.4.105**, with `-K -p`.
Generation returned exit **0**; source and prior receipt hashes were unchanged.

| Artifact | SHA-256 |
| --- | --- |
| `DF-CANDIDATE/DF_source_CCD.cif` | `27f83c85e89605b5a0b3b02f062da62d7a348b3b346e5df5774a65c7c143e55e` |
| `DF-CANDIDATE/DF.cif` | `cedfc7099d7679146dc59a46dec655f93c2639e419f5aaec96ec3d02d0a8c293` |
| Supplied `DF_candidate_review.zip` | `fd5ad43b666de68809da684e0acafb2df9bbb8d0353d946ffa9d23acce8bf443` |

Separate analysis passed the source-preservation audit: **36 atoms / 21 heavy /
15 H / 37 bonds**, with unchanged graph, formal charges and bond orders;
**65 angles / 19 torsions** with connected valid references and numerical
values. Sugar centres **C1': R, C3': S, C4': R** retain their source
assignments with matching dictionary signs; P is `both`. The candidate targets
include C1'–C2' **1.522 Å**, C3'–C4' **1.530 Å**, C1'–O4' **1.413 Å**,
double C4=O4 **1.231 Å** and double C2=S1 **1.672 Å**. The generation log's two
`non-ring atom 3 marked aromatic` warnings remain preserved; the final audited graph
has no corresponding defect. Copied descriptors are not independent chemical
validation. This passes the bounded source/numerical audit, **not native
linkage, geometry minimization or scientific approval**.

### Next native boundary

The supplied single-use `combined_repaired_native.py` driver stages this
diagnostic under a new `LIVE/combined-repaired-native-*` directory, preserves
originals, and writes `repaired_native_review.zip` with hashes and effective
geometry details. Its staging and check logic were exercised offline; Phenix
execution and any resulting pass remain pending returned native evidence.
This driver is a diagnostic artifact, not an installed NASolve command.

1. Create a fresh diagnostic copy of the combined model and its **15 inputs**;
   preserve all original hashes. Substitute only the narrow corrected/normalized
   5CM derivative and the new DF candidate for the ReadySet DF supplement.
2. Apply a site-specific DF internal-link modification deleting **OP3, HOP3 and
   HO3'**, set O3' type to **OC2**, and retain the source OP2 hydrogen. Record the
   chemical-state difference: old ReadySet DF assigned OP1 formal charge **−1**,
   whereas the new source has formal charges **0**. This is not a pH correction
   or a silently chosen common phosphate state.
3. Reinterpret natively, then check **42 mappings**, no unexpected identities or
   missing heavy atoms, one correct native 5CM quartet with its alternate, and
   the three DF sugar chirality restraints/new bond targets. Recheck the other
   links, exact custom-restraint coverage and protected D:1 terminal phosphate.
4. Only if those checks support it, run disposable geometry minimization and
   inspect strain, coordinate displacement, chirality, all six paired sites,
   backbone/phosphate, stacking and symmetry contacts. Record failures and
   remaining strain rather than assuming a passing result. The CGY starting
   N1–C2–C1 angle (**1.58°** against **120.86°**) demonstrates severe starting
   strain; that discrepancy alone is not a dictionary defect.

The four earlier generic linked sites retain their mixed source-dependent
phosphate protonation, with no orphan hydrogens and complete incoming links.
Do not invent a uniform protonation/tautomer policy to remove that distinction.
A later refinement and human verdict must name the new model/checkpoint, date
and exact effective restraints; earlier Z:P approval does not transfer.
Production integration and a fresh ordinary full-auto acquisition test remain
separate. The staged audit/automation plan follows this geometry test; see the
[component contract](modified-component-preparation.md#proposed-smiles-and-cif-audit).

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
