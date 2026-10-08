# Native modified-base pair matrix — live validation ledger

Updated **2026-10-08**. **Z:P + off-pair 5CM:G/DF:A integration:
SOLVED numerically, user visual PASS.** The *independent five-member native
pair matrix remains NOT RUN*. Upstream **NARestraints v1.1.3 is released**,
but NASolve's Saenger-overlay [PR #24](https://github.com/vecchioni-lab/NASolve/pull/24)
is **not merged into Pine**. This file is the current scientific/evidence
ledger; the detailed original attempt chronology is
[archived](history/native-modified-pair-2026-10-08-pre-consolidation.md).
See the [compact handoff](development-handoff.md) for project-wide priority.

## What is actually green?

| Gate | Current verdict | Evidence / boundary |
| --- | --- | --- |
| NARestraints Z:P + K:X role/stacking fix | **RELEASED v1.1.3** | [Release](https://github.com/vecchioni-lab/NARestraints/releases/tag/v1.1.3), `main a9264f9`, wheel/sdist/SHA256SUMS, CI green Python 3.10/3.12/3.14. Committed `Ligands.xlsx` unchanged. |
| Isolated NASolve PR #24 code | **FULL REGRESSION PASS, not integrated** | 34 focused; 961 full + 224 subtests; user-worktree `../NASolve-saengerfix` with corrected upstream NARestraints. Requires a new **combined Pine** test after PR reconciliation. |
| Native Z:P preparation, modified-W overlay | **PASS** | `run_003` PostMR: 17 original W pairs → 15 unchanged Saenger + 2 explicit modified pairs (5CM:G GC/3 contacts; DF:A AT/2). Z:P atom-role correction separately audited; 42 sequence-family targets, zero mismatches, no `force = G:C`. |
| Native Z:P/W AutoRefine | **SOLVED (numerical)** | New `GZ11_ZP/AutoMR/run_003`, `refine-001`; frozen integrity OK; D:1 phosphate protection retained. No Rwork/Rfree numbers or final `.geo` metrics copied into this ledger. |
| Human Coot review of `run_003` | **INSPECTED_PASS (overall visual only)** | User reported excellent refinement appearance, bonds and planes present and mild tolerable nonideal planarity. Individual-site map/clash/angular statistics and true experimental chemistry remain unverified. |
| `nasolve show` workflow | **USER LIVE PASS** | PR #25 merged at `e8613bf`; user `workspace use` for existing `run_003`, then **bare `./nasolve show` succeeded in Coot**. New-campaign automatic workspace activation has regression, not yet this specific live exercise. |
| Five fresh A:T/D:T/B:S/Z:P/K:X datasets | **NOT STAGED/PLANNED/NATIVELY RUN** | Requires fresh frozen copies, a review of alias/ligand-CIF availability, and sequential isolated stage receipts. |
| Independent source `1W5→DZ`, `1WA→DP` P2 | **SEPARATELY PENDING NATIVE** | This 42-residue synthetic-target W test does not exercise genuine source-code normalization. |
| Prepared nonstandard P5, Registration/Topo/GUI | **SEPARATE WORKSTREAMS** | Their prior evidence and unfinished gates retain exactly their original scope. |

**Chemistry caveat:** real GZ11 diffraction reflections were used with
hypothetical modified target identities. Neither an automated SOLVED result
nor an overall Coot PASS shows the *actual experimental GZ11 crystal* has
Z:P, B:S, K:X, D:T, 5CM or DF, or permits deposition of such a model.

## The next chemistry experiment: five **independent** W datasets

Use the [released NARestraints v1.1.3 staging-only helper](https://github.com/vecchioni-lab/NARestraints/blob/v1.1.3/scripts/stage_nasolve_pair_matrix.py)
(`scripts/stage_nasolve_pair_matrix.py` from a clean v1.1.3 source checkout)
to stage **one fresh root containing five separately named dataset copies**.
**This is not four pairs simultaneously in one crystal.** Each member has the
same real GZ11 MTZ/CIF/summary inputs and W starting model, same reviewed
`w-metal-scaffold` reference, same two *off-pair* modifications, but
its own A:12/B:4 `pair =` target and independent result.

| Member | Ordered requested pair A:12/B:4 | Expected PDB residue codes | Native readiness / rationale |
| --- | --- | --- | --- |
| `A_T_CONTROL` | **A:T** | `DA / DT` | Canonical A:T role control in the *same modified context*; `DA` is canonical DNA adenine, **not** the D-family base. |
| `D_T` | **D:T** | `1AP / DT` | Distinct diaminopurine-like **D:T** template, already workbook-tested. **D:A is not registered**; do not silently substitute it. |
| `B_S` | **B:S** | `IGU / S6G` | Recipe is independently workbook-tested; `IGU.cif` was missing from the last audited NASolve library. |
| `Z_P` | **Z:P** | `DZ / DP` | Upstream role orientation corrected and one standalone native integration run succeeded; new frozen matrix member remains independently unrun. |
| `K_X` | **K:X** | `CGY / DX` | Recipe is workbook-tested; `CGY.cif` and `DX.cif` were missing at last audit. |

Common off-pair sequence requests, retained in **every** member:

```ini
[automr]
mode = standard
frame = W
model = zp_input_W.pdb
sequence_reference = w-metal-scaffold
# pair = <one exact member's ordered recipe>

[sequences]
A = GAGCAG(5CM)CTGTATGGACA(A1AAZ)CA
C = G(DG)CTGCT
```

This yields A:7 5CM / C:9 DG and A:19 reviewed `A1AAZ→DF` /
D:4 DA alongside the single tested A:12/B:4 pair. NARestraints' `GC`
and `AT` descriptions are **geometry templates**, not identity changes.
No default `force = G:C` or automatic dictionary synthesis is authorized.

The helper verifies source hashes, 42-residue W model chain counts
(A=21, B/C/D=7), copies files into
`~/NASolve-live-tests/nar-pair-matrix-*`, writes five `nasolve.txt`
files and `staging-manifest.json`, and reports missing native ligand
dictionaries. **Staging does not plan, launch Phenix or Coot, or certify
component availability.** Recheck the current manifest at execution time;
the previous `IGU/CGY/DX` absence is not a permanent fact of the system.
A missing CIF is a meaningful **BLOCK**, not an invitation to invent a
monomer, quietly change pair identity, or reuse a chemically wrong dictionary.

## Execution gates (run each boundary; keep failures)

1. **Code/dependency preflight:** reconcile and validate NASolve PR #24
   with current Pine and immutable **NARestraints v1.1.3**. From the NASolve
   Python environment record the real `restraints.__file__`, distribution
   version, workbook/hash and NASolve commit; the declared dependency pin
   does not itself upgrade an old `.venv`. No testing through the user's dirty
   `../NARestraints` feature checkout.
2. **Stage, review, then freeze once:** invoke the released staging script
   from a clean source checkout with `--nasolve-root "$PWD"` from the
   original NASolve terminal. Inspect missing `.cif` reports and ordered
   recipes, then `campaign plan --preset 5w6w` on the *new* root with
   explicit frame resource provenance. Confirm immutable input hashes,
   one member per pair, correct sequence-family intent and no `force`
   override. Never modify or reuse the existing Z:P root.
3. **Native one boundary at a time:** preflight → Phaser → PostMR for each
   eligible member, recording TFZ/LLG, actual A:12/B:4 residues,
   off-pair 5CM/G and DF/A identities, named recipe/contact count,
   stacking/plane authority, any missing dictionary, `A1AAZ→DF` audit
   and D:1 phosphate policy. A blocked member stays preserved while
   others may continue; do not mark it PASS.
4. **Conditional AutoSol then AutoRefine only if preparation works.**
   Record actual map provenance, whether phases ran or were skipped,
   numerical Rwork/Rfree, checkpoint, effective PHIL/`.geo`, warnings
   and unchanged Free-R. Every saved attempt remains immutable.
5. **Human Coot/geometry review:** inspect all viable A:12/B:4 contacts,
   A:7/C:9 and A:19/D:4 off-pair restraints, sugar/phosphate, clashes,
   difference maps, stacking and the actual `.geo` angular geometry.
   Record reviewer, date, exact code/input/run/checkpoint and one of
   `INSPECTED_PASS`, `INSPECTED_REVIEW` or `INSPECTED_FAIL`.
   A numerical solver result never writes `user_approved`.

Only **after independent families** are scientifically mapped should an
optional **combined mixed-pair stress model** be proposed. That is a *new*
hypothesis/frozen campaign, with independently reviewed sites and monomers,
not an implicit sixth case or a reinterpretation of these five datasets.

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
  No new native chemistry matrix or experimental verification followed.

**Separate angle research note:** user observed that some displayed
hydrogen-bond contacts looked tilted relative to a wished-for straight
N1/N3–O4/N6 alignment. Later inspect the actual donor–H–acceptor
definitions and hydrogen-bond angular restraints; do **not** blindly impose
a heavy-atom 180° target, exaggerate planarity, or modify the successful
historic `run_003`. This is not a `show` or Z:P role bug.

## Preservation and scope

The user's original NASolve checkout has many **untracked but valuable**
models, runs, patches, and an older virtual environment. Their sibling
`../NARestraints` tree includes **uncommitted `Ligands.xlsx` changes
and an Excel lockfile**. Never reset, clean, stash, checkout into or pip
install/edit over this dirty library tree. Use separate clean worktrees
and process-local imports until reviewed. Existing data and runs must not
be copied into Git or substituted for future test observations.

Separate unresolved questions include I:C, A:G and G:T atom-role geometry,
source P2 `1W5/1WA` conversions, Pine P5 geometry-diverse real models,
Scout and topology/GUI work. They are **not silently closed** by this
five-pair W validation plan. The full original attempt-era diagnostic
transcript, site-resolved SHA and log chronology are preserved in the
[dated history snapshot](history/native-modified-pair-2026-10-08-pre-consolidation.md).
