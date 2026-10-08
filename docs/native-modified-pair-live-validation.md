# Native modified-base pair matrix — live validation ledger

Updated **2026-10-08**. **Z:P + off-pair 5CM:G/DF:A integration:
SOLVED numerically, user visual PASS.** User now requests **one combined
D:T+B:S+Z:P+K:X W challenge** before isolated follow-up controls;
this simultaneous native experiment is **NOT RUN**.
Upstream **NARestraints v1.1.3 is released**,
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
| Combined D:T+B:S+Z:P+K:X native W test | **PROPOSED, NOT STAGED/PLANNED/RUN** | One new dataset/model with four separate named pair sites, plus 5CM:G and DF:A. New workbook regression also pending user execution. IGU/CGY/DX dictionaries absent from committed resources. |
| Five independent A:T/D:T/B:S/Z:P/K:X controls | **OPTIONAL DIAGNOSTIC FALLBACK; NOT RUN** | Retain released upstream staging helper for later failure isolation; do not mistake its five datasets for the requested simultaneous test. |
| Independent source `1W5→DZ`, `1WA→DP` P2 | **SEPARATELY PENDING NATIVE** | This 42-residue synthetic-target W test does not exercise genuine source-code normalization. |
| Prepared nonstandard P5, Registration/Topo/GUI | **SEPARATE WORKSTREAMS** | Their prior evidence and unfinished gates retain exactly their original scope. |

**Chemistry caveat:** real GZ11 diffraction reflections were used with
hypothetical modified target identities. Neither an automated SOLVED result
nor an overall Coot PASS shows the *actual experimental GZ11 crystal* has
Z:P, B:S, K:X, D:T, 5CM or DF, or permits deposition of such a model.

## Next chemistry experiment — **one simultaneous four-family W model**

The user explicitly prefers to test **all four named modified-pair families
in the same model**, so their common backbone, stacking, Saenger-template
and effective-dictionary interactions are exercised together. This is a
**single new synthetic-target W dataset**, not four independent 42-residue
models. Retain the original frozen Z:P run untouched.

The proposed pairing layout deliberately uses distinct source W sites
that already have the corresponding canonical geometric class:

| Role | W pair sites | Original W geometry | Target component codes | Reviewed recipe |
| --- | --- | --- | --- | --- |
| **D:T** | **A:5 / C:11** | A:T | **1AP / DT** | `D_T`, distinct D-family chemistry |
| **B:S** | **A:6 / C:10** | G:C | **IGU / S6G** | `GC` geometry with B=G-like, S=C-like |
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

### Proposed 42-site sequence request — review before freezing

This is a **candidate**, derived from the versioned
`w-metal-scaffold` 21/7/7/7 site inventory and the existing
reviewed `A1AAZ→DF` alias. The `pair = Z:P` route used successfully
in `run_003` targets A:12/B:4; the other named pairs and prior off-pair
modifications are supplied as site-specific chain sequence changes.

```ini
[automr]
mode = standard
frame = W
pair = Z:P
model = combined_input_W.pdb
sequence_reference = w-metal-scaffold

[sequences]
A = GAGC(1AP)(IGU)(5CM)CTGTATGGACA(A1AAZ)(CGY)A
C = GG(S6G)TGCT
D = CT(DX)ATGT
```

B remains the referenced canonical sequence until the explicit Z:P
selector prepares B:4=DP. Verify the full compiled targets independently
against the *actual* frozen 42-residue model. The tested Saenger overlay
would see five modified template pairs (D:T, B:S, K:X, 5CM:G, DF:A):
**17 inherited W Saenger blocks → 12 retained + 5 replaced**;
the central Z:P site is already within the frame's ordinary
`Std_padd` input. This exact combined configuration has **not**
yet passed native preflight, PostMR or Phenix refinement.

### Dictionary availability is a hard prerequisite

Actual NASolve Pine source audit on 2026-10-08 confirms packaged
`S6G.cif`, `1AP.cif`, `DZ.cif`, `DP.cif`, `5CM.cif` and
`DF.cif`, but **not `IGU.cif`, `CGY.cif` or `DX.cif`**.
Find or obtain authoritative, checked monomer definitions for these
three codes, verify atom names/coordinates, component group, chemistry
and provenance, and preserve source bytes before making derived
NASolve resources. If unavailable, **BLOCK** the combined native
PostMR attempt with that reason; do not invent molecules, mislabel
canonical ones or count a skipped chemistry case as a pass.

The released upstream
[NARestraints five-case source stager](https://github.com/vecchioni-lab/NARestraints/blob/v1.1.3/scripts/stage_nasolve_pair_matrix.py)
still stages **five separate** W datasets (A:T control, D:T, B:S,
Z:P, K:X), not this simultaneous test. Keep it as an optional
**diagnostic fallback** when an individual pair needs isolation.
Do not point it at the combined root or conflate its manifest with
the requested experiment. A reviewed **new source-only** combined
stager/config and disjoint hashed copies are needed before planning.

## Execution gates — one frozen combined dataset, stage by stage

1. **Integrate the code safely:** the remote PR #24 candidate is reconciled
   to current Pine and has a new workbook-backed **four-family simultaneous**
   helper test, not yet locally executed. Confirm clean NARestraints
   **v1.1.3** imports and workbook SHA, run focused/full NASolve regression
   on the **combined head**, and merge PR #24 only after review/green.
   Do not modify the user's dirty sibling NARestraints workbook.
2. **Source component dictionaries first:** review authoritative
   `IGU`, `CGY`, `DX` monomer CIFs and atom-role compatibility, explicitly
   documenting any missing names/dictionaries. No synthetic source data
   becomes a release resource without scientific provenance.
3. **Stage and freeze *one* combined challenge:** allocate a fresh disjoint
   directory under `~/NASolve-live-tests`, hash/copy the real GZ11
   reflections/CIF/summary and W search model, record the exact above
   sequence request and aliases. Confirm all **42 compiled targets**,
   4 named pair identities at 4 disjoint sites, 2 off-pair contextual
   modifications, 5 Saenger replacements, and D:1 phosphate policy.
   Do not reuse/alter any of `run_001`, `run_002`, `run_003`.
4. **Native stages one at a time:** preflight → Phaser → PostMR →
   conditional AutoSol → AutoRefine if preparation passes. Record exact
   atom contacts and planes/stacking for **all four named families**,
   source/effective dictionaries, Saenger overlay counts, target
   mismatches, TFZ/LLG, Rwork/Rfree, map authority, Free-R and geometry
   warnings. Preserve and diagnose any BLOCKED stage.
5. **Human Coot review:** inspect all six paired sites, nearby backbone,
   phosphate, sugar pucker, angular hydrogen bonds, stacking, difference
   maps, clashes and actual `.geo` output. Record reviewer, date,
   run/checkpoint, selected PHIL and `INSPECTED_PASS`,
   `INSPECTED_REVIEW` or `INSPECTED_FAIL`; `SOLVED` alone never
   grants experimental approval. Follow with **isolated five-member
   controls only when diagnostic resolution demands it**.

**Scientific scope:** this remains a software compatibility test on
unrelated GZ11 diffraction, *not* proof the original crystal contains
the artificially requested bases or permission to deposit the model.

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
