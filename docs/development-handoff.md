# NASolve development handoff — current state

Updated **2026-10-10** from native receipts and checksum-verified geometry/DF
bundles. **Active candidate: `cedar`; integration target: `pine` (draft PR #26),
then `main` (draft PR #23).** The current laptop Cedar checkout is clean at
**`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`**, matching the frozen combined
manifest. Preserve this local unpublished diagnostic head; do not pull or replace
it with a remote head to continue the run. Diagnostic scripts/derivatives are
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
| Combined geometry minimization | **GEOMETRY_MINIMIZATION_COMPLETED_AWAITING_REVIEW**; target fell 97.45%, all 158 chirality signs retained, same manager and original inputs preserved. | User Coot visual PASS recorded for the relaxed model; DP numerical repair/audit and convergence review remain open before a clean rerun. |
| Ordinary/full-auto campaigns | Prior EA/DiU/Q5cm/QiC cohort reached numerical SOLVED with review/provisional distinctions preserved. | This does not prove a fresh arbitrary-component run without a prepared resource bundle. |
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

1. **Retry DP generation with explicit quoting and consumer-parser preflight.**
   The first disposable attempt was **BLOCKED**: AceDRG read 20 atoms/21 bonds
   instead of 35/37 from single-quoted primed IDs, then failed on C5'. Sources
   are unchanged and no candidate exists or was adopted. The corrected v2
   driver checks double-quoted seed round-trip and the installed reader's
   atom/bond/chirality interpretation before generation. Limited offline reader
   replay passed 35/37/4 and mismatch rejection; installed preflight/native retry
   remain pending. Audit any candidate before adoption or a clean rerun. The
   [native ledger](native-modified-pair-live-validation.md#dp-candidate-attempt--blocked-by-seed-parser-disagreement)
   owns the failure evidence. Preserve the user's **visual PASS** for the
   relaxed model separately from open DP numerical repair, convergence and full
   qualification; no MTZ/Free-R or production full-auto result is implied.
2. **Turn demonstrated preparation into ordinary fresh full-auto behavior.**
   The current trial used selected numerical CIFs in a frozen resource bundle
   and ad hoc linked derivatives. Acceptance is a new run from declared
   model/sequence intent and component codes, without per-run source patches
   or a hand-prepared bundle. Cover already-present modified residues as well
   as mutations; distinguish library acquisition/cache, numerical preparation,
   verified polymer context and a small justified override registry. This is
   the product goal, not an achieved result or an unlimited new Cedar gate.
3. **Close the existing bounded Cedar/Pine gates.** Retain the prior P1/P3/P4
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

## Roadmap after the combined geometry test

The October 10 request inserts the **SMILES-assisted CIF audit after the
current combined geometry trial and before Topo slicing / operational Scout**.
This future tool is not a prerequisite for trying that geometry trial or an
additional Cedar/Pine merge gate.

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
  5CM/DF/DP lessons and proposed evidence schema for implementation.
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
